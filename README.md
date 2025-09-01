# Discord Channel Reset Bot

A Discord bot that automatically resets daily chat channels at a specified time each day.

## Features

- Automatically deletes and recreates a text channel (`daily-chat`) at a scheduled time
- Automatically deletes and recreates a voice channel (`daily-yap`) in the Voice Channels category
- Configurable reset time (currently set to 4:30 AM)
- Simple logging for monitoring bot activity

## Setup

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env` file with your Discord bot token:
   ```
   DISCORD_BOT_TOKEN=your_bot_token_here
   ```

3. Update the configuration in `bot.py`:
   - Set your server ID in `GUILD_ID`
   - Adjust `RESET_HOUR` and `RESET_MINUTE` as needed
   - Modify channel names if desired

4. Run the bot:
   ```bash
   python3 bot.py
   ```

## Configuration

- `GUILD_ID`: Your Discord server ID
- `TEXT_CHANNEL_NAME`: Name of the text channel to reset (default: "daily-chat")
- `VOICE_CHANNEL_NAME`: Name of the voice channel to reset (default: "daily-yap")
- `RESET_HOUR`: Hour to reset channels (24-hour format)
- `RESET_MINUTE`: Minute to reset channels

## Requirements

- Python 3.7+
- discord.py
- python-dotenv

## Bot Permissions

The bot needs the following permissions:
- Manage Channels
- View Channels
- Connect (for voice channels)
