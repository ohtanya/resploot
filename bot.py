import os
import discord
from discord.ext import commands, tasks
import datetime
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Bot setup
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Configuration
GUILD_ID = 1411611160263790626  # replace with your server ID
TEXT_CHANNEL_NAME = "daily-chat"    # name of the text channel to reset
VOICE_CHANNEL_NAME = "daily-yap"    # name of the voice channel to reset
RESET_HOUR = 4                 # 24h format
RESET_MINUTE = 30

@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}")
    reset_channel.start()

@tasks.loop(minutes=1)
async def reset_channel():
    now = datetime.datetime.now()
    if now.hour == RESET_HOUR and now.minute == RESET_MINUTE:
        guild = bot.get_guild(GUILD_ID)
        if not guild:
            print("Guild not found!")
            return
        
        # Find the "Voice Channels" category
        voice_category = discord.utils.get(guild.categories, name="Voice Channels")
        
        # Delete and recreate the text channel
        text_channel = discord.utils.get(guild.channels, name=TEXT_CHANNEL_NAME)
        if text_channel:
            await text_channel.delete()
            print(f"Deleted text channel: {TEXT_CHANNEL_NAME}")
        
        # Create a new text channel
        await guild.create_text_channel(TEXT_CHANNEL_NAME)
        print(f"Created text channel: {TEXT_CHANNEL_NAME}")
        
        # Delete and recreate the voice channel
        voice_channel = discord.utils.get(guild.channels, name=VOICE_CHANNEL_NAME)
        if voice_channel:
            await voice_channel.delete()
            print(f"Deleted voice channel: {VOICE_CHANNEL_NAME}")
        
        # Create a new voice channel in the Voice Channels category
        await guild.create_voice_channel(VOICE_CHANNEL_NAME, category=voice_category)
        print(f"Created voice channel: {VOICE_CHANNEL_NAME}")

# Start the bot
bot.run(TOKEN)
