# Neurodivergence Bot Documentation

## Overview

Neurodivergence is a feature-rich Discord bot built with Python using the `discord.py` library. The bot provides a wide array of functionality including AI interactions, image generation, utility commands, moderation tools, and fun features. The bot uses a modular cog-based architecture for easy extensibility.

## Architecture

### Core Components

- **Main Bot (`bot.py`)**: The core bot class that handles initialization, logging, command processing, and cog loading
- **Cogs System**: Modular command groups organized by functionality
- **Logging**: Dual logging system (console with colors, file logging)
- **Status Rotation**: Dynamic status messages that rotate every minute

### Bot Features

- **Command Prefix**: Mentions (responds when mentioned)
- **Hybrid Commands**: Supports both slash commands and traditional text commands
- **Automatic Cog Loading**: Automatically loads all Python files from the `cogs/` directory
- **Error Handling**: Comprehensive error handling with user-friendly messages
- **Command Logging**: Logs all command executions to both console and Discord channel

## Cogs and Commands

### 1. General (`cogs/general.py`)

**Commands:**
- `cmds` - Lists all available commands organized by category

### 2. AI (`cogs/ai.py`)

AI-powered features using Google Gemini API and LM Studio.

**Commands:**
- `gemini [prompt]` - Chat with Google Gemini AI. Supports image attachments and uses channel history for context
- `wizard [prompt]` - Chat with Wizard Vicuna AI (via LM Studio hosts)
- `sd [prompt] [neg_prompt] [cfg] [steps] [sampler] [restore_faces]` - Generate images using Stable Diffusion via Automatic1111 WebUI

**Features:**
- **Auto-Response**: Automatically responds when "neuro" or "neurodivergence" is mentioned in messages
- **Personality**: Responds as "Neuro" - an aggressively happy, useless character with broken English, ALL CAPS, and excessive emojis
- **Multi-key Support**: Rotates through multiple Gemini API keys to handle rate limits
- **Attachment Processing**: Supports images, videos, audio, and PDF attachments
- **Channel History**: Uses recent channel history for context-aware responses

### 3. Utility (`cogs/utility.py`)

Australian-focused utility commands for real-world information.

**Commands:**
- `weather [town] [state]` - Get weather information from BOM (Bureau of Meteorology) for Australian locations
- `pl [query] [suburb] [state]` - Person Lookup - find contact details for people in Australia
- `fuel [town] [state]` - Get fuel prices for Australian locations
- `openports [ip]` - Check open ports on a host using Shodan InternetDB
- `rego [plate]` - Check vehicle registration details (South Australia)
- `geowifi [bssid] [ssid]` - Retrieve geolocation information for WiFi networks
- `ppsearch [phone_number]` - Reverse search phone numbers to check if they're payphones

### 4. Fun (`cogs/fun.py`)

Entertainment and random content commands.

**Commands:**
- `wanted` - Retrieve a random wanted person image from Crime Stoppers SA
- `cctv` - Get a random insecure CCTV camera stream
- `redorblack` - Use quantum random number generator to decide red or black

### 5. Moderation (`cogs/moderation.py`)

Server moderation tools.

**Commands:**
- `purge [amount]` - Delete a specified number of messages (requires Manage Messages permission)
- `preemptban [user_id] [reason]` - Pre-emptively ban a user before they join (requires Ban Members permission)
- `archive [limit]` - Archive channel messages to a text file (requires Manage Messages permission)

### 6. Become (`cogs/become.py`)

Language translation feature that translates all bot responses in a channel.

**Commands:**
- `become [language]` - Make the bot respond in a specific language in the current channel
- `becomelist` - List all available languages

**Supported Languages:**
Over 50 languages including Arabic, Chinese, French, German, Japanese, Spanish, and many more. Each language has a flag emoji marker.

**How it works:**
- When activated in a channel, all bot messages are automatically translated
- Works with both text messages and embeds
- Can be disabled by using `become neuro`

### 7. Owner (`cogs/owner.py`)

Bot owner-only commands for management.

**Commands:**
- `sync [scope]` - Synchronize slash commands (global or guild)
- `unsync [scope]` - Unsync slash commands (global or guild)
- `load [cog]` - Load a cog dynamically
- `unload [cog]` - Unload a cog dynamically
- `reload [cog]` - Reload a cog dynamically

### 8. Sidepipe (`cogs/sidepipe.py`)

Server-specific cog for The Sidepipe Discord server (included for reference).

**Commands:**
- `cctvselfie [camera]` - Take a selfie using CCTV cameras (requires Home Assistant integration)

**Note:** This cog is server-specific and should be removed or modified for your own instance.

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TOKEN` | Yes | Discord bot token from Discord Developer Portal |
| `GEMINI_KEYS` | Yes* | JSON array of Google Gemini API keys: `["key1", "key2"]` |
| `AUTO1111_HOSTS` | No | JSON array of Automatic1111 WebUI hosts: `["http://host1:7860"]` |
| `LMS_HOSTS` | No | JSON array of LM Studio hosts: `["http://host1:1234"]` |
| `LOGGING_CHANNEL` | No | Discord channel ID for command logging |
| `STATUSES` | No | JSON array of status messages to rotate: `["status1", "status2"]` |
| `GEOWIFI_URL` | No | URL for GeoWifi API instance |
| `HTTP_PROXY` | No | HTTP proxy URL for web requests |
| `LIBRETRANSLATE_URL` | No | LibreTranslate API URL (defaults to `http://localhost:5000`) |
| `HASS_URL` | No | Home Assistant URL (for Sidepipe cog) |
| `HASS_TOKEN` | No | Home Assistant API token (for Sidepipe cog) |

*GEMINI_KEYS is required for AI features but the bot can run without it (AI commands will fail)

### Dependencies

The bot requires the following Python packages (see `requirements.txt`):
- `discord.py` - Discord API wrapper
- `aiohttp` - Async HTTP client
- `beautifulsoup4` - HTML parsing
- `pillow` - Image processing

## Deployment

### Docker Deployment

The bot is designed to run in Docker containers:

1. **Build the image:**
   ```bash
   docker build -t neurodivergence:latest .
   ```

2. **Run the container:**
   ```bash
   docker run -d \
     -e TOKEN=your_discord_token \
     -e GEMINI_KEYS='["key1", "key2"]' \
     -e AUTO1111_HOSTS='["http://host1:7860"]' \
     -e LMS_HOSTS='["http://host1:1234"]' \
     -e LOGGING_CHANNEL=0123456789012345678 \
     -e STATUSES='["Status 1", "Status 2"]' \
     -e GEOWIFI_URL=http://127.0.0.1:5000/geowifi \
     -e HTTP_PROXY=http://100.65.0.1:8888 \
     --restart unless-stopped \
     neurodivergence:latest
   ```

### Local Development

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set environment variables (use `.env` file or export them)

3. Run the bot:
   ```bash
   python bot.py
   ```

## Logging

The bot implements a dual logging system:

1. **Console Logging**: Color-coded logs with timestamps
   - DEBUG: Gray
   - INFO: Blue
   - WARNING: Yellow
   - ERROR: Red
   - CRITICAL: Red (bold)

2. **File Logging**: Plain text logs saved to `discord.log`

3. **Discord Logging**: Command executions logged to a Discord channel (if `LOGGING_CHANNEL` is set)

## Error Handling

The bot includes comprehensive error handling:

- **Command Cooldowns**: Shows remaining time when rate-limited
- **Permission Errors**: Clear messages for missing permissions
- **Missing Arguments**: Helpful error messages for incomplete commands
- **Owner-only Commands**: Logs unauthorized attempts
- **API Failures**: Graceful fallbacks for external service failures

## Extending the Bot

### Adding a New Cog

1. Create a new file in the `cogs/` directory (e.g., `cogs/myfeature.py`)

2. Use this template:
   ```python
   import discord
   from discord.ext import commands
   from discord.ext.commands import Context

   class MyFeature(commands.Cog, name="myfeature"):
       def __init__(self, bot) -> None:
           self.bot = bot

       @commands.hybrid_command(
           name="mycommand",
           description="Description of my command",
       )
       async def mycommand(self, ctx):
           await ctx.reply("Hello!")

   async def setup(bot) -> None:
       await bot.add_cog(MyFeature(bot))
   ```

3. The bot will automatically load it on startup

### Bot Intents

The bot uses the following Discord intents:
- Default intents (guilds, members, messages, etc.)
- Message content intent (required for message content access)

Make sure these are enabled in your Discord Developer Portal.

## Technical Details

### Command Processing

- Commands can be triggered via mentions or slash commands
- The bot ignores its own messages and other bots
- Commands are processed asynchronously

### Status Rotation

- Status messages rotate every minute
- Randomly selected from the `STATUSES` environment variable
- Uses Discord's CustomActivity feature

### API Key Rotation

For Gemini API:
- Automatically rotates through multiple API keys
- Handles rate limits (429 errors) by trying next key
- Returns error messages if all keys are exhausted

### Host Failover

For services with multiple hosts (AUTO1111_HOSTS, LMS_HOSTS):
- Randomly shuffles hosts for load balancing
- Tries each host until one succeeds
- Shows error if all hosts are offline

## Security Considerations

- Bot token should never be committed to version control
- API keys should be kept secure
- The `sidepipe.py` cog contains server-specific functionality and should be reviewed/removed
- Some commands access external APIs and websites - ensure proper error handling
- Moderation commands require appropriate Discord permissions

## Troubleshooting

### Bot doesn't respond to commands
- Check that the bot has proper permissions in the server
- Verify message content intent is enabled
- Check logs for error messages

### AI commands fail
- Verify `GEMINI_KEYS` is set correctly (JSON array format)
- Check API key validity and quotas
- Review error messages in logs

### Image generation fails
- Ensure `AUTO1111_HOSTS` is set and hosts are accessible
- Verify Automatic1111 WebUI is running and accessible
- Check network connectivity

### Translation doesn't work
- Verify `LIBRETRANSLATE_URL` is set correctly
- Ensure LibreTranslate service is running
- Check that the language is supported

## License

See the repository for license information.

## Contributing

This bot was created as a learning project. Feel free to fork and modify for your own use!
