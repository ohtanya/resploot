import os
import discord
from discord.ext import commands, tasks
import datetime
import pytz
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Bot setup
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Track last reset date to avoid multiple resets per day
last_reset_date = None

# Configuration
GUILD_ID = 1411611160263790626  # replace with your server ID
TEXT_CHANNEL_NAME = "daily-chat"    # name of the text channel to reset
VOICE_CHANNEL_NAME = "daily-yap"    # name of the voice channel to reset
RESET_HOUR = 4                 # 24h format
RESET_MINUTE = 30
TIMEZONE = "America/Los_Angeles"  # Change this to your timezone

@bot.event
async def on_ready():
    tz = pytz.timezone(TIMEZONE)
    now = datetime.datetime.now(tz)
    
    print(f"Bot is online as {bot.user}")
    print(f"Current server time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Daily reset scheduled for: {RESET_HOUR:02d}:{RESET_MINUTE:02d} {TIMEZONE}")
    
    # Calculate next reset time
    today_reset = now.replace(hour=RESET_HOUR, minute=RESET_MINUTE, second=0, microsecond=0)
    if now >= today_reset:
        next_reset = today_reset + datetime.timedelta(days=1)
    else:
        next_reset = today_reset
    
    print(f"Next reset: {next_reset.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    reset_channel.start()

@tasks.loop(minutes=1)
async def reset_channel():
    global last_reset_date
    
    # Get current time in specified timezone
    tz = pytz.timezone(TIMEZONE)
    now = datetime.datetime.now(tz)
    current_date = now.date()
    
    # Log current time every hour for debugging
    if now.minute == 0:
        print(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    # Check if it's time to reset and we haven't reset today
    if (now.hour == RESET_HOUR and now.minute == RESET_MINUTE and 
        last_reset_date != current_date):
        
        print(f"Starting channel reset at {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        guild = bot.get_guild(GUILD_ID)
        if not guild:
            print("Guild not found!")
            return
        
        try:
            # Find the "Voice Channels" category
            voice_category = discord.utils.get(guild.categories, name="Voice Channels")
            
            # Delete and recreate the text channel
            text_channel = discord.utils.get(guild.channels, name=TEXT_CHANNEL_NAME)
            if text_channel:
                await text_channel.delete()
                print(f"Deleted text channel: {TEXT_CHANNEL_NAME}")
            
            # Create a new text channel
            new_text_channel = await guild.create_text_channel(TEXT_CHANNEL_NAME)
            print(f"Created text channel: {TEXT_CHANNEL_NAME}")
            
            # Delete and recreate the voice channel
            voice_channel = discord.utils.get(guild.channels, name=VOICE_CHANNEL_NAME)
            if voice_channel:
                await voice_channel.delete()
                print(f"Deleted voice channel: {VOICE_CHANNEL_NAME}")
            
            # Create a new voice channel in the Voice Channels category
            new_voice_channel = await guild.create_voice_channel(VOICE_CHANNEL_NAME, category=voice_category)
            print(f"Created voice channel: {VOICE_CHANNEL_NAME}")
            
            # Update last reset date
            last_reset_date = current_date
            print(f"Channel reset completed successfully at {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            
        except Exception as e:
            print(f"Error during channel reset: {e}")
    
    # Log next reset time once per day at startup or after reset
    elif now.hour == RESET_HOUR and now.minute == RESET_MINUTE + 1:
        next_reset = now.replace(hour=RESET_HOUR, minute=RESET_MINUTE) + datetime.timedelta(days=1)
        print(f"Next reset scheduled for: {next_reset.strftime('%Y-%m-%d %H:%M:%S %Z')}")

@bot.command(name='reset_now')
async def reset_now_command(ctx):
    """Manual command to trigger channel reset (admin only)"""
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("You need administrator permissions to use this command.")
        return
    
    await ctx.send("Triggering manual channel reset...")
    
    try:
        guild = bot.get_guild(GUILD_ID)
        if not guild:
            await ctx.send("Guild not found!")
            return
        
        # Find the "Voice Channels" category
        voice_category = discord.utils.get(guild.categories, name="Voice Channels")
        
        # Delete and recreate the text channel
        text_channel = discord.utils.get(guild.channels, name=TEXT_CHANNEL_NAME)
        if text_channel:
            await text_channel.delete()
        
        # Create a new text channel
        await guild.create_text_channel(TEXT_CHANNEL_NAME)
        
        # Delete and recreate the voice channel
        voice_channel = discord.utils.get(guild.channels, name=VOICE_CHANNEL_NAME)
        if voice_channel:
            await voice_channel.delete()
        
        # Create a new voice channel in the Voice Channels category
        await guild.create_voice_channel(VOICE_CHANNEL_NAME, category=voice_category)
        
        await ctx.send("✅ Channels have been reset successfully!")
        print(f"Manual reset triggered by {ctx.author}")
        
    except Exception as e:
        await ctx.send(f"❌ Error during reset: {e}")
        print(f"Error during manual reset: {e}")

@bot.command(name='next_reset')
async def next_reset_command(ctx):
    """Show when the next automatic reset will occur"""
    tz = pytz.timezone(TIMEZONE)
    now = datetime.datetime.now(tz)
    
    today_reset = now.replace(hour=RESET_HOUR, minute=RESET_MINUTE, second=0, microsecond=0)
    if now >= today_reset:
        next_reset = today_reset + datetime.timedelta(days=1)
    else:
        next_reset = today_reset
    
    await ctx.send(f"Next automatic reset: {next_reset.strftime('%Y-%m-%d %H:%M:%S %Z')}")

# Start the bot
bot.run(TOKEN)
