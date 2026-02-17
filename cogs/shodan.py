import base64
import io
import os
import random
from typing import Any, Dict, Optional, Tuple, List

import aiohttp
import discord
from discord.ext import commands

SHODAN_SEARCH_URL = "https://api.shodan.io/shodan/host/search"
SHODAN_HOST_URL = "https://www.shodan.io/host"

def _safe_join(items, limit: int = 3) -> str:
    if not items:
        return "N/A"
    if isinstance(items, (list, tuple)):
        trimmed = [str(x) for x in items if x is not None and str(x).strip()]
        if not trimmed:
            return "N/A"
        if len(trimmed) > limit:
            return ", ".join(trimmed[:limit]) + f" (+{len(trimmed) - limit} more)"
        return ", ".join(trimmed)
    return str(items)

def _extract_screenshot(match: Dict[str, Any]) -> Optional[Tuple[bytes, str]]:
    """
    Shodan can include screenshots as base64 in `match["screenshot"]["data"]`.
    Returns (bytes, ext) or None.
    """
    screenshot = match.get("screenshot")
    if not isinstance(screenshot, dict):
        return None
    data_b64 = screenshot.get("data")
    if not data_b64:
        return None
    mime = screenshot.get("mime") or "image/jpeg"
    ext = mime.split("/")[-1].lower()
    try:
        return base64.b64decode(data_b64), ext
    except Exception:
        return None

class RetryShodanButton(discord.ui.View):
    def __init__(
        self,
        user: discord.User,
        city: str,
        screenshot_matches: List[Dict[str, Any]],
        already_used_indices: Optional[List[int]] = None,
        timeout: float = 60.0,
    ):
        super().__init__(timeout=timeout)
        self.requester_id = getattr(user, 'id', None)
        self.city = city
        self.screenshot_matches = screenshot_matches
        self.already_used_indices = already_used_indices or []
        self.current_ip = None  # Will hold the IP of the *most recent* shown result

    def _add_shodan_button(self, initial_ip=None):
        # Remove all existing link buttons, then add the new one for the current IP
        for child in list(self.children):
            if isinstance(child, discord.ui.Button) and child.style == discord.ButtonStyle.link:
                self.remove_item(child)

        ip = initial_ip or self.current_ip
        if ip and ip != "N/A":
            shodan_url = f"{SHODAN_HOST_URL}/{ip}"
            self.add_item(discord.ui.Button(label="Open in Shodan", url=shodan_url, style=discord.ButtonStyle.link))

    async def disable_all(self):
        for child in self.children:
            if isinstance(child, discord.ui.Button) and not (child.style == discord.ButtonStyle.link):
                child.disabled = True

    async def generate_embed_and_file(self, random_index=None):
        matches = self.screenshot_matches
        total = len(matches)
        available_indices = list(set(range(total)) - set(self.already_used_indices))
        if not available_indices:
            embed = discord.Embed(
                title="Shodan",
                description="No more unique results left for retry.",
            )
            return embed, None, None
        if random_index is None:
            idx = random.choice(available_indices)
        else:
            idx = random_index
        match = matches[idx]
        extracted = _extract_screenshot(match)
        if not extracted:
            embed = discord.Embed(
                title="Shodan",
                description="Failed to decode screenshot.",
            )
            return embed, None, None
        image_bytes, ext = extracted
        filename = f"shodan_{self.city.lower().replace(' ', '_')}.{ext}"
        file = discord.File(io.BytesIO(image_bytes), filename=filename)

        ip = match.get("ip_str") or "N/A"
        port = match.get("port") or "N/A"
        org = match.get("org") or match.get("isp") or "N/A"
        asn = match.get("asn") or "N/A"
        hostnames = _safe_join(match.get("hostnames"))
        domains = _safe_join(match.get("domains"))
        product = match.get("product") or "N/A"
        transport = match.get("transport") or "N/A"
        timestamp = match.get("timestamp") or "N/A"

        location = match.get("location") if isinstance(match.get("location"), dict) else {}
        country = (location.get("country_name") or location.get("country_code") or "N/A") if location else "N/A"
        region = (location.get("region_code") or location.get("region_name") or "N/A") if location else "N/A"

        embed = discord.Embed(
            title=f"Shodan screenshot — {self.city}",
            description=f'Query: `city:"{self.city}" has_screenshot:true`',
        )
        embed.add_field(name="IP:Port", value=f"`{ip}:{port}`", inline=True)
        embed.add_field(name="Org/ISP", value=str(org), inline=True)
        if asn and asn != "N/A":
            mxtoolbox_url = f"https://mxtoolbox.com/SuperTool.aspx?action=asn%3a{asn}&run=toolpage"
            asn_value = f"[{asn}]({mxtoolbox_url})"
        else:
            asn_value = "N/A"
        embed.add_field(name="ASN", value=asn_value, inline=True)
        embed.add_field(name="Country/Region", value=f"{country} / {region}", inline=True)
        embed.add_field(name="Product", value=str(product), inline=True)
        embed.add_field(name="Transport", value=str(transport), inline=True)
        embed.add_field(name="Hostnames", value=hostnames, inline=False)
        embed.add_field(name="Domains", value=domains, inline=False)
        embed.set_footer(text=f"Seen: {timestamp}")
        embed.set_image(url=f"attachment://{filename}")

        # Fix: Always ensure only one Open in Shodan button (and it's up-to-date)
        self.current_ip = ip if ip and ip != "N/A" else None
        self._add_shodan_button(initial_ip=self.current_ip)

        return embed, file, idx

    @discord.ui.button(label="Retry", style=discord.ButtonStyle.primary, custom_id="shodan_retry")
    async def retry(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Only the original requester can use this button
        if self.requester_id is not None and interaction.user.id != self.requester_id:
            await interaction.response.send_message(
                "Only the original requester can use this button.", ephemeral=True
            )
            return

        # Make sure the already_used_indices includes the current result to avoid reshowing it due to speed-clicking
        if hasattr(self, "current_ip") and self.current_ip is not None:
            # Try to append the index of the current_ip in our matches to already_used_indices
            for idx, match in enumerate(self.screenshot_matches):
                if match.get("ip_str") == self.current_ip and idx not in self.already_used_indices:
                    self.already_used_indices.append(idx)
                    break

        embed, file, idx = await self.generate_embed_and_file()
        # If nothing available, disable all buttons and update
        if file is None:
            await self.disable_all()
            await interaction.response.edit_message(embed=embed, view=self, attachments=[])
            return

        # When using the Retry button, always append the new index of the result we show.
        self.already_used_indices.append(idx)

        # Refresh the "Open in Shodan" button to update for the new IP
        self._add_shodan_button(initial_ip=self.current_ip)

        await interaction.response.edit_message(embed=embed, view=self, attachments=[file])

    async def on_timeout(self):
        await self.disable_all()
        try:
            pass
        except Exception:
            pass

class Shodan(commands.Cog, name="shodan"):
    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.hybrid_command(
        name="shodan",
        description='Search Shodan for a city screenshot (query: city:"<city>" has_screenshot:true)',
    )
    async def shodan(self, ctx, city: str = ""):
        key = os.getenv("SHODAN_KEY")
        if not key:
            embed = discord.Embed(
                title="Shodan",
                description="`SHODAN_KEY` is not set on this bot.",
            )
            await ctx.reply(embed=embed)
            return

        city = (city or "").strip()
        if not city:
            embed = discord.Embed(
                title="Shodan",
                description="Please provide a city name. Example: `/shodan Adelaide`",
            )
            await ctx.reply(embed=embed)
            return

        query = f'city:"{city}" has_screenshot:true'
        embed = discord.Embed(title="Shodan", description=f"Searching: `{query}`\nPlease wait...")
        msg = await ctx.reply(embed=embed)

        params = {
            "key": key,
            "query": query,
            "limit": 100,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(SHODAN_SEARCH_URL, params=params) as resp:
                    if resp.status != 200:
                        try:
                            err = await resp.json()
                            err_msg = err.get("error") or err.get("message") or str(err)
                        except Exception:
                            err_msg = await resp.text()
                        embed = discord.Embed(
                            title="Shodan",
                            description=f"Error from Shodan: `{resp.status}`\n{err_msg}",
                        )
                        await msg.edit(embed=embed)
                        return
                    payload = await resp.json()
        except Exception as e:
            embed = discord.Embed(title="Shodan", description=f"Request failed: `{type(e).__name__}`")
            await msg.edit(embed=embed)
            return

        matches = payload.get("matches") if isinstance(payload, dict) else None
        if not isinstance(matches, list) or not matches:
            embed = discord.Embed(title="Shodan", description="No results.")
            await msg.edit(embed=embed)
            return

        screenshot_matches = [m for m in matches if _extract_screenshot(m)]
        if not screenshot_matches:
            embed = discord.Embed(
                title="Shodan",
                description="Results found, but none included screenshot data.",
            )
            await msg.edit(embed=embed)
            return

        idx = random.randrange(len(screenshot_matches))
        match = screenshot_matches[idx]
        extracted = _extract_screenshot(match)
        if not extracted:
            embed = discord.Embed(
                title="Shodan",
                description="Failed to decode screenshot.",
            )
            await msg.edit(embed=embed)
            return

        image_bytes, ext = extracted
        filename = f"shodan_{city.lower().replace(' ', '_')}.{ext}"
        file = discord.File(io.BytesIO(image_bytes), filename=filename)

        ip = match.get("ip_str") or "N/A"
        port = match.get("port") or "N/A"
        org = match.get("org") or match.get("isp") or "N/A"
        asn = match.get("asn") or "N/A"
        hostnames = _safe_join(match.get("hostnames"))
        domains = _safe_join(match.get("domains"))
        product = match.get("product") or "N/A"
        transport = match.get("transport") or "N/A"
        timestamp = match.get("timestamp") or "N/A"

        location = match.get("location") if isinstance(match.get("location"), dict) else {}
        country = (location.get("country_name") or location.get("country_code") or "N/A") if location else "N/A"
        region = (location.get("region_code") or location.get("region_name") or "N/A") if location else "N/A"

        embed = discord.Embed(
            title=f"Shodan screenshot — {city}",
            description=f'Query: `city:"{city}" has_screenshot:true`',
        )
        embed.add_field(name="IP:Port", value=f"`{ip}:{port}`", inline=True)
        embed.add_field(name="Org/ISP", value=str(org), inline=True)
        asn_link = f"https://mxtoolbox.com/SuperTool.aspx?action=asn%3a{asn}&run=toolpage" if asn != "N/A" else None
        if asn_link:
            embed.add_field(name="ASN", value=f"[{asn}]({asn_link})", inline=True)
        else:
            embed.add_field(name="ASN", value=str(asn), inline=True)
        embed.add_field(name="Country/Region", value=f"{country} / {region}", inline=True)
        embed.add_field(name="Product", value=str(product), inline=True)
        embed.add_field(name="Transport", value=str(transport), inline=True)
        embed.add_field(name="Hostnames", value=hostnames, inline=False)
        embed.add_field(name="Domains", value=domains, inline=False)
        embed.set_footer(text=f"Seen: {timestamp}")
        embed.set_image(url=f"attachment://{filename}")

        shodan_url = None
        if ip and ip != "N/A":
            shodan_url = f"{SHODAN_HOST_URL}/{ip}"

        view = RetryShodanButton(
            user=getattr(ctx, "author", getattr(ctx, "user", None)),
            city=city,
            screenshot_matches=screenshot_matches,
            already_used_indices=[idx],
        )
        # Add the link button for the initial IP (done internally now by RetryShodanButton's logic)
        view._add_shodan_button(initial_ip=ip)

        try:
            await msg.delete()
        except Exception:
            pass
        await ctx.reply(embed=embed, file=file, view=view)
    
    @commands.hybrid_command(
        name="shodan_query",
        description="Search Shodan with a custom query, requires has_screenshot:true in the query."
    )
    async def shodan_query(self, ctx, *, query: str = ""):
        key = os.getenv("SHODAN_KEY")
        if not key:
            embed = discord.Embed(
                title="Shodan",
                description="`SHODAN_KEY` is not set on this bot.",
            )
            await ctx.reply(embed=embed)
            return

        query = (query or "").strip()
        if not query:
            embed = discord.Embed(
                title="Shodan",
                description="Please provide a query string. Example: `/shodan_query org:\"Amazon\" has_screenshot:true`",
            )
            await ctx.reply(embed=embed)
            return

        # Optionally ensure has_screenshot:true is in the query
        if "has_screenshot:true" not in query:
            embed = discord.Embed(
                title="Shodan",
                description="Your query must include `has_screenshot:true` to return screenshot results.",
            )
            await ctx.reply(embed=embed)
            return

        embed = discord.Embed(title="Shodan", description=f"Searching: `{query}`\nPlease wait...")
        msg = await ctx.reply(embed=embed)

        params = {
            "key": key,
            "query": query,
            "limit": 100,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(SHODAN_SEARCH_URL, params=params) as resp:
                    if resp.status != 200:
                        try:
                            err = await resp.json()
                            err_msg = err.get("error") or err.get("message") or str(err)
                        except Exception:
                            err_msg = await resp.text()
                        embed = discord.Embed(
                            title="Shodan",
                            description=f"Error from Shodan: `{resp.status}`\n{err_msg}",
                        )
                        await msg.edit(embed=embed)
                        return
                    payload = await resp.json()
        except Exception as e:
            embed = discord.Embed(title="Shodan", description=f"Request failed: `{type(e).__name__}`")
            await msg.edit(embed=embed)
            return

        matches = payload.get("matches") if isinstance(payload, dict) else None
        if not isinstance(matches, list) or not matches:
            embed = discord.Embed(title="Shodan", description="No results.")
            await msg.edit(embed=embed)
            return

        screenshot_matches = [m for m in matches if _extract_screenshot(m)]
        if not screenshot_matches:
            embed = discord.Embed(
                title="Shodan",
                description="Results found, but none included screenshot data.",
            )
            await msg.edit(embed=embed)
            return

        idx = random.randrange(len(screenshot_matches))
        match = screenshot_matches[idx]
        extracted = _extract_screenshot(match)
        if not extracted:
            embed = discord.Embed(
                title="Shodan",
                description="Failed to decode screenshot.",
            )
            await msg.edit(embed=embed)
            return

        image_bytes, ext = extracted
        # Try to guess a city or org for filename, fallback to generic
        hint = match.get('city') or match.get('org') or "custom"
        filename = f"shodan_{str(hint).lower().replace(' ', '_')}.{ext}"
        file = discord.File(io.BytesIO(image_bytes), filename=filename)

        ip = match.get("ip_str") or "N/A"
        port = match.get("port") or "N/A"
        org = match.get("org") or match.get("isp") or "N/A"
        asn = match.get("asn") or "N/A"
        hostnames = _safe_join(match.get("hostnames"))
        domains = _safe_join(match.get("domains"))
        product = match.get("product") or "N/A"
        transport = match.get("transport") or "N/A"
        timestamp = match.get("timestamp") or "N/A"

        location = match.get("location") if isinstance(match.get("location"), dict) else {}
        country = (location.get("country_name") or location.get("country_code") or "N/A") if location else "N/A"
        region = (location.get("region_code") or location.get("region_name") or "N/A") if location else "N/A"

        embed = discord.Embed(
            title=f'Shodan screenshot — Custom Query',
            description=f"Query: `{query}`",
        )
        embed.add_field(name="IP:Port", value=f"`{ip}:{port}`", inline=True)
        embed.add_field(name="Org/ISP", value=str(org), inline=True)
        asn_link = f"https://mxtoolbox.com/SuperTool.aspx?action=asn%3a{asn}&run=toolpage" if asn != "N/A" else None
        if asn_link:
            embed.add_field(name="ASN", value=f"[{asn}]({asn_link})", inline=True)
        else:
            embed.add_field(name="ASN", value=str(asn), inline=True)
        embed.add_field(name="Country/Region", value=f"{country} / {region}", inline=True)
        embed.add_field(name="Product", value=str(product), inline=True)
        embed.add_field(name="Transport", value=str(transport), inline=True)
        embed.add_field(name="Hostnames", value=hostnames, inline=False)
        embed.add_field(name="Domains", value=domains, inline=False)
        embed.set_footer(text=f"Seen: {timestamp}")
        embed.set_image(url=f"attachment://{filename}")

        shodan_url = None
        if ip and ip != "N/A":
            shodan_url = f"{SHODAN_HOST_URL}/{ip}"

        # Use the RetryShodanButton as above, but set city=hint just for filename context
        view = RetryShodanButton(
            user=getattr(ctx, "author", getattr(ctx, "user", None)),
            city=hint if hint else "Custom",
            screenshot_matches=screenshot_matches,
            already_used_indices=[idx],
        )
        # Add the link button for the initial IP (done internally now by RetryShodanButton's logic)
        view._add_shodan_button(initial_ip=ip)

        try:
            await msg.delete()
        except Exception:
            pass
        await ctx.reply(embed=embed, file=file, view=view)

async def setup(bot) -> None:
    await bot.add_cog(Shodan(bot))
