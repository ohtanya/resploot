# Discord Channel Reset Bot

A Discord bot that automatically resets daily chat channels at a specified time each day.

## Features

- Automatically deletes and recreates a text channel (`daily-chat`) at a scheduled time
- Automatically deletes and recreates a voice channel (`daily-yap`) in the Voice Channels category
- Configurable reset time (currently set to 4:30 AM)
- Simple logging for monitoring bot activity
- PM2 process management for production deployment

## Local Development

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

## Production Deployment (VPS with PM2)

1. Run the deployment script on your VPS:
   ```bash
   curl -sSL https://raw.githubusercontent.com/ohtanya/resploot/main/deploy.sh | bash
   ```

2. Set up your environment:
   ```bash
   cd discord-bot
   cp .env.example .env
   nano .env  # Add your Discord bot token
   ```

3. Start with PM2:
   ```bash
   pm2 start ecosystem.config.json
   pm2 save
   pm2 startup  # Follow the instructions to enable auto-start
   ```

## PM2 Management Commands

- `pm2 status` - View running processes
- `pm2 logs discord-bot` - View logs in real-time
- `pm2 restart discord-bot` - Restart the bot
- `pm2 stop discord-bot` - Stop the bot
- `pm2 delete discord-bot` - Remove from PM2

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
- PM2 (for production deployment)

## Bot Permissions

The bot needs the following permissions:
- Manage Channels
- View Channels
- Connect (for voice channels)
