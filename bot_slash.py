import os
import discord
from discord.ext import commands, tasks
from discord import app_commands
import datetime
import pytz
import json
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Bot setup - no message content intent needed for slash commands
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Configuration
GUILD_ID = 1411611160263790626  # replace with your server ID
TIMEZONE = "America/Los_Angeles"  # Change this to your timezone
SCHEDULES_FILE = "schedules.json"

# Dictionary to store scheduled resets
scheduled_resets = {}

def load_schedules():
    """Load scheduled resets from file"""
    global scheduled_resets
    try:
        with open(SCHEDULES_FILE, 'r') as f:
            scheduled_resets = json.load(f)
        print(f"Loaded {len(scheduled_resets)} scheduled resets")
    except FileNotFoundError:
        scheduled_resets = {}
        print("No schedules file found, starting with empty schedules")
    except json.JSONDecodeError:
        scheduled_resets = {}
        print("Invalid schedules file, starting with empty schedules")

def save_schedules():
    """Save scheduled resets to file"""
    try:
        with open(SCHEDULES_FILE, 'w') as f:
            json.dump(scheduled_resets, f, indent=2)
    except Exception as e:
        print(f"Error saving schedules: {e}")

@bot.event
async def on_ready():
    tz = pytz.timezone(TIMEZONE)
    now = datetime.datetime.now(tz)
    
    print(f"Bot is online as {bot.user}")
    print(f"Current server time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    # Load scheduled resets
    load_schedules()
    
    if scheduled_resets:
        print(f"Active schedules:")
        for channel_name, schedule in scheduled_resets.items():
            print(f"  - {channel_name} ({schedule['type']}): {schedule['hour']:02d}:{schedule['minute']:02d}")
    else:
        print("No scheduled resets configured. Use /schedule_reset to add some!")
    
    # Sync slash commands
    try:
        guild = discord.Object(id=GUILD_ID)
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        print(f"Synced {len(synced)} slash commands to guild")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    
    reset_scheduler.start()

@tasks.loop(minutes=1)
async def reset_scheduler():
    """Check all scheduled resets and execute them if it's time"""
    tz = pytz.timezone(TIMEZONE)
    now = datetime.datetime.now(tz)
    current_date = now.strftime('%Y-%m-%d')
    
    # Log current time every hour for debugging
    if now.minute == 0:
        print(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return
    
    # Check each scheduled reset
    for channel_name, schedule in scheduled_resets.items():
        # Check if it's time to reset and we haven't reset today
        if (now.hour == schedule['hour'] and 
            now.minute == schedule['minute'] and 
            schedule.get('last_reset') != current_date):
            
            print(f"Starting scheduled reset for {channel_name} at {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            
            try:
                await reset_channel_by_name(guild, channel_name, schedule)
                
                # Update last reset date
                schedule['last_reset'] = current_date
                save_schedules()
                
                print(f"Reset completed for {channel_name}")
                
            except Exception as e:
                print(f"Error during scheduled reset of {channel_name}: {e}")

async def reset_channel_by_name(guild, channel_name, schedule):
    """Reset a specific channel based on its schedule configuration"""
    channel_type = schedule['type']
    category_name = schedule.get('category')
    
    # Find the category if specified
    category = None
    if category_name:
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            print(f"Warning: Category '{category_name}' not found for {channel_name}")
    
    # Find and delete the existing channel
    channel = discord.utils.get(guild.channels, name=channel_name)
    if channel:
        await channel.delete()
        print(f"Deleted {channel_type} channel: {channel_name}")
    
    # Create new channel based on type
    if channel_type == 'text':
        new_channel = await guild.create_text_channel(channel_name, category=category)
    elif channel_type == 'voice':
        new_channel = await guild.create_voice_channel(channel_name, category=category)
    else:
        raise ValueError(f"Invalid channel type: {channel_type}")
    
    print(f"Created {channel_type} channel: {channel_name}")
    return new_channel

# SLASH COMMANDS

@bot.tree.command(name="ping", description="Test if the bot is online")
async def ping_slash(interaction: discord.Interaction):
    """Simple ping command to test if bot is responding"""
    await interaction.response.send_message("🏓 Pong! Bot is online and ready!")

@bot.tree.command(name="schedule_reset", description="Schedule a daily reset for a channel")
@app_commands.describe(
    channel_name="Name of the channel to reset (without #)",
    channel_type="Type of channel",
    time="Time in HH:MM format (e.g., 10:42, 04:30)", 
    category="Category to place the channel in (optional)"
)
@app_commands.choices(channel_type=[
    discord.app_commands.Choice(name="Text Channel", value="text"),
    discord.app_commands.Choice(name="Voice Channel", value="voice")
])
async def schedule_reset_slash(interaction: discord.Interaction, channel_name: str, channel_type: str, time: str, category: str = None):
    """Schedule a daily reset for a channel"""
    # Parse time in HH:MM format
    try:
        if ':' in time:
            hour_str, minute_str = time.split(':')
            hour = int(hour_str)
            minute = int(minute_str)
        else:
            hour = int(time)
            minute = 0
    except ValueError:
        await interaction.response.send_message("❌ Invalid time format. Use HH:MM (e.g., 10:42 or 04:30)", ephemeral=True)
        return
    
    # Validate inputs
    if not (0 <= hour <= 23):
        await interaction.response.send_message("❌ Hour must be between 0 and 23", ephemeral=True)
        return
    
    if not (0 <= minute <= 59):
        await interaction.response.send_message("❌ Minute must be between 0 and 59", ephemeral=True)
        return
    
    # Clean channel name
    if channel_name.startswith('#'):
        channel_name = channel_name[1:]
    
    # Store the schedule
    scheduled_resets[channel_name] = {
        'type': channel_type.lower(),
        'hour': hour,
        'minute': minute,
        'category': category,
        'last_reset': None
    }
    
    save_schedules()
    
    category_text = f" in category '{category}'" if category else ""
    await interaction.response.send_message(f"✅ Scheduled daily reset for **{channel_name}** ({channel_type}){category_text} at **{hour:02d}:{minute:02d}** {TIMEZONE}")
    print(f"Scheduled reset added by {interaction.user}: {channel_name} at {hour:02d}:{minute:02d}")

@bot.tree.command(name="list_schedules", description="Show all scheduled channel resets")
async def list_schedules_slash(interaction: discord.Interaction):
    """List all scheduled resets"""
    if not scheduled_resets:
        await interaction.response.send_message("📅 No scheduled resets configured yet. Use `/schedule_reset` to add some!", ephemeral=True)
        return
    
    embed = discord.Embed(title="📅 Scheduled Channel Resets", color=0x00ff00)
    
    for channel_name, schedule in scheduled_resets.items():
        last_reset = schedule.get('last_reset', 'Never')
        
        embed.add_field(
            name=f"#{channel_name} ({schedule['type']})",
            value=f"**Time:** {schedule['hour']:02d}:{schedule['minute']:02d} {TIMEZONE}\n**Category:** {schedule['category'] or 'Default'}\n**Last Reset:** {last_reset}",
            inline=True
        )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="remove_schedule", description="Remove a scheduled reset")
@app_commands.describe(channel_name="Name of the channel to remove from schedule")
async def remove_schedule_slash(interaction: discord.Interaction, channel_name: str):
    """Remove a scheduled reset"""
    # Clean channel name
    if channel_name.startswith('#'):
        channel_name = channel_name[1:]
    
    if channel_name not in scheduled_resets:
        await interaction.response.send_message(f"❌ No scheduled reset found for **{channel_name}**", ephemeral=True)
        return
    
    del scheduled_resets[channel_name]
    save_schedules()
    
    await interaction.response.send_message(f"✅ Removed scheduled reset for **{channel_name}**")
    print(f"Schedule removed by {interaction.user}: {channel_name}")

@bot.tree.command(name="reset_now", description="Manually trigger a channel reset")
@app_commands.describe(channel_name="Name of the channel to reset")
async def reset_now_slash(interaction: discord.Interaction, channel_name: str):
    """Manually trigger a channel reset"""
    # Clean channel name
    if channel_name.startswith('#'):
        channel_name = channel_name[1:]
    
    if channel_name not in scheduled_resets:
        channels = ", ".join([f"#{name}" for name in scheduled_resets.keys()])
        await interaction.response.send_message(f"❌ **{channel_name}** is not scheduled. Available: {channels}", ephemeral=True)
        return
    
    await interaction.response.send_message(f"🔄 Triggering manual reset for **{channel_name}**...")
    
    try:
        guild = bot.get_guild(GUILD_ID)
        if not guild:
            await interaction.edit_original_response(content="❌ Guild not found!")
            return
        
        schedule = scheduled_resets[channel_name]
        await reset_channel_by_name(guild, channel_name, schedule)
        
        # Update last reset date
        tz = pytz.timezone(TIMEZONE)
        now = datetime.datetime.now(tz)
        schedule['last_reset'] = now.strftime('%Y-%m-%d')
        save_schedules()
        
        await interaction.edit_original_response(content=f"✅ **{channel_name}** has been reset successfully!")
        print(f"Manual reset triggered by {interaction.user}: {channel_name}")
        
    except Exception as e:
        await interaction.edit_original_response(content=f"❌ Error during reset: {e}")
        print(f"Error during manual reset of {channel_name}: {e}")

@bot.tree.command(name="next_reset", description="Show when the next reset will occur")
@app_commands.describe(channel_name="Name of specific channel (optional)")
async def next_reset_slash(interaction: discord.Interaction, channel_name: str = None):
    """Show when the next reset will occur for a channel or all channels"""
    tz = pytz.timezone(TIMEZONE)
    now = datetime.datetime.now(tz)
    
    if channel_name:
        # Clean channel name
        if channel_name.startswith('#'):
            channel_name = channel_name[1:]
        
        if channel_name not in scheduled_resets:
            await interaction.response.send_message(f"❌ **{channel_name}** is not scheduled.", ephemeral=True)
            return
        
        schedule = scheduled_resets[channel_name]
        today_reset = now.replace(hour=schedule['hour'], minute=schedule['minute'], second=0, microsecond=0)
        
        if now >= today_reset:
            next_reset = today_reset + datetime.timedelta(days=1)
        else:
            next_reset = today_reset
        
        await interaction.response.send_message(f"⏰ Next reset for **{channel_name}**: {next_reset.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    else:
        if not scheduled_resets:
            await interaction.response.send_message("📅 No scheduled resets configured.", ephemeral=True)
            return
        
        embed = discord.Embed(title="⏰ Next Reset Times", color=0x0099ff)
        
        for channel_name, schedule in scheduled_resets.items():
            today_reset = now.replace(hour=schedule['hour'], minute=schedule['minute'], second=0, microsecond=0)
            
            if now >= today_reset:
                next_reset = today_reset + datetime.timedelta(days=1)
            else:
                next_reset = today_reset
            
            embed.add_field(
                name=f"#{channel_name}",
                value=next_reset.strftime('%m/%d %H:%M'),
                inline=True
            )
        
        await interaction.response.send_message(embed=embed)

@bot.tree.command(name="help", description="Show help for all commands")
async def help_slash(interaction: discord.Interaction):
    """Show help for reset commands"""
    embed = discord.Embed(title="🔄 Channel Reset Bot - Slash Commands", color=0x00ff00)
    
    embed.add_field(
        name="/schedule_reset",
        value="Schedule a daily reset for a channel\n**Example:** `/schedule_reset daily-chat text 10:42`\n**With category:** Add category name in the category field",
        inline=False
    )
    
    embed.add_field(
        name="Other Commands",
        value="`/list_schedules` - Show all scheduled resets\n"
              "`/remove_schedule` - Remove a schedule\n"
              "`/reset_now` - Manual reset\n"
              "`/next_reset` - Show next reset times\n"
              "`/ping` - Test if bot is online",
        inline=False
    )
    
    embed.add_field(
        name="Time Format",
        value="Use 24-hour format: `04:30`, `10:42`, `23:30`",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Start the bot
bot.run(TOKEN)
