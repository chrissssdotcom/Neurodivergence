import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context
import aiohttp
import os

libretranslate_url = os.environ.get("LIBRETRANSLATE_URL", "http://localhost:5000")

MODES = {
    "chinese": {"target": "zh", "marker": " 🇨🇳"},
    "japanese": {"target": "ja", "marker": " 🇯🇵"},
}

ALL_MARKERS = [m["marker"] for m in MODES.values()]

class Morph(commands.Cog, name="morph"):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.morphed_channels = {}

    async def translate(self, text, target):
        if not text:
            return text
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{libretranslate_url}/translate", json={
                "q": text,
                "source": "en",
                "target": target,
            }) as response:
                if response.status != 200:
                    return text
                data = await response.json()
                return data.get("translatedText", text)

    async def translate_embed(self, embed, mode):
        marker = MODES[mode]["marker"]
        target = MODES[mode]["target"]
        new_embed = discord.Embed(
            title=await self.translate(embed.title, target) if embed.title else embed.title,
            description=(await self.translate(embed.description, target) + marker) if embed.description else embed.description,
            color=embed.color,
        )
        for field in embed.fields:
            new_embed.add_field(
                name=await self.translate(field.name, target),
                value=await self.translate(field.value, target),
                inline=field.inline,
            )
        return new_embed

    def is_already_translated(self, message):
        for marker in ALL_MARKERS:
            if message.content and message.content.endswith(marker):
                return True
            for embed in message.embeds:
                if embed.description and embed.description.endswith(marker):
                    return True
        return False

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author != self.bot.user:
            return
        if message.channel.id not in self.morphed_channels:
            return
        if self.is_already_translated(message):
            return
        await self.translate_message(message)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if after.author != self.bot.user:
            return
        if after.channel.id not in self.morphed_channels:
            return
        if self.is_already_translated(after):
            return
        await self.translate_message(after)

    async def translate_message(self, message):
        try:
            mode = self.morphed_channels[message.channel.id]
            marker = MODES[mode]["marker"]
            target = MODES[mode]["target"]
            new_content = None
            if message.content:
                new_content = await self.translate(message.content, target) + marker
            new_embeds = [await self.translate_embed(e, mode) for e in message.embeds] if message.embeds else []
            await message.edit(content=new_content, embeds=new_embeds or [])
        except Exception:
            pass

    @commands.hybrid_command(
        name="morph",
        description="morph the bot's language in this channel",
    )
    @app_commands.choices(mode=[
        app_commands.Choice(name="Chinese 🇨🇳", value="chinese"),
        app_commands.Choice(name="Japanese 🇯🇵", value="japanese"),
        app_commands.Choice(name="Neuro (default)", value="neuro"),
    ])
    async def morph(self, ctx, mode: str):
        if mode == "neuro":
            self.morphed_channels.pop(ctx.channel.id, None)
            embed = discord.Embed(title="morph OFF", description="back to normal neuro brain")
            await ctx.reply(embed=embed)
        elif mode in MODES:
            self.morphed_channels[ctx.channel.id] = mode
            marker = MODES[mode]["marker"]
            embed = discord.Embed(title=f"morph → {mode}{marker}", description=f"all bot responses in this channel will now be {mode}")
            await ctx.reply(embed=embed)
        else:
            embed = discord.Embed(title="morph failed", description="pick chinese, japanese, or neuro dummy")
            await ctx.reply(embed=embed)

async def setup(bot) -> None:
    await bot.add_cog(Morph(bot))
