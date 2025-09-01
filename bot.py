import os
import discord
from discord.ext import commands, tasks
import datetime
import pytz
import json
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Bot setup
intents = discord.Intents.default()
intents.message_content = True  # Required to read message content for commands
bot = commands.Bot(command_prefix="!", intents=intents)

# Configuration
GUILD_ID = 1411611160263790626  # replace with your server ID
TIMEZONE = "America/Los_Angeles"  # Change this to your timezone
SCHEDULES_FILE = "schedules.json"

# Dictionary to store scheduled resets: {channel_name: {'hour': X, 'minute': Y, 'type': 'text/voice', 'category': 'category_name', 'last_reset': 'YYYY-MM-DD'}}
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
        print("No scheduled resets configured. Use !schedule_reset to add some!")
    
    reset_scheduler.start()

@bot.event
async def on_message(message):
    """Handle bot mentions for commands"""
    # Don't respond to our own messages
    if message.author == bot.user:
        return
    
    # Check if bot is mentioned
    if bot.user.mentioned_in(message):
        content = message.content.replace(f'<@{bot.user.id}>', '').replace(f'<@!{bot.user.id}>', '').strip()
        
        # If it's just a mention without a command, show help
        if not content:
            embed = discord.Embed(title="👋 Hi there!", color=0x00ff00)
            embed.add_field(
                name="Quick Commands",
                value="`@resploot schedule_reset daily-chat text 10:42`\n`@resploot list_schedules`\n`@resploot help_reset`",
                inline=False
            )
            await message.reply(embed=embed)
            return
        
        # Parse the command manually
        parts = content.split()
        if not parts:
            return
            
        command = parts[0].lower()
        
        # Handle schedule_reset specially for mentions
        if command == 'schedule_reset' and len(parts) >= 4:
            channel_name = parts[1]
            channel_type = parts[2]
            time = parts[3]
            category = ' '.join(parts[4:]) if len(parts) > 4 else None
            
            # Remove quotes from category if present
            if category and category.startswith('"') and category.endswith('"'):
                category = category[1:-1]
            
            # Create a fake context for the command
            ctx = await bot.get_context(message)
            await schedule_reset_command(ctx, channel_name, channel_type, time, category)
            return
    
    # Process normal commands
    await bot.process_commands(message)

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

@bot.command(name='ping')
async def ping_command(ctx):
    """Simple ping command to test if bot is responding"""
    await ctx.send("🏓 Pong! Bot is online and ready!")

@bot.command(name='schedule_reset')
async def schedule_reset_command(ctx, channel_name: str, channel_type: str, time: str, category: str = None):
    """
    Schedule a daily reset for a channel
    Usage: !schedule_reset <channel_name> <text|voice> <time> [category]
    Usage: @resploot schedule_reset <channel_name> <text|voice> <time> [category]
    Example: !schedule_reset daily-chat text 04:30
    Example: !schedule_reset daily-yap voice 10:42 "Voice Channels"
    """
    # Parse time in HH:MM format
    try:
        if ':' in time:
            hour_str, minute_str = time.split(':')
            hour = int(hour_str)
            minute = int(minute_str)
        else:
            # Fallback for old format (just hour)
            hour = int(time)
            minute = 0
    except ValueError:
        await ctx.send("❌ Invalid time format. Use HH:MM (e.g., 10:42 or 04:30)")
        return
    
    # Validate inputs
    if channel_type.lower() not in ['text', 'voice']:
        await ctx.send("❌ Channel type must be 'text' or 'voice'")
        return
    
    if not (0 <= hour <= 23):
        await ctx.send("❌ Hour must be between 0 and 23")
        return
    
    if not (0 <= minute <= 59):
        await ctx.send("❌ Minute must be between 0 and 59")
        return
    
    # Clean channel name (remove # if present)
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
    await ctx.send(f"✅ Scheduled daily reset for **{channel_name}** ({channel_type}){category_text} at **{hour:02d}:{minute:02d}** {TIMEZONE}")
    print(f"Scheduled reset added by {ctx.author}: {channel_name} at {hour:02d}:{minute:02d}")

@bot.command(name='list_schedules')
async def list_schedules_command(ctx):
    """List all scheduled resets"""
    if not scheduled_resets:
        await ctx.send("📅 No scheduled resets configured yet. Use `!schedule_reset` to add some!")
        return
    
    embed = discord.Embed(title="📅 Scheduled Channel Resets", color=0x00ff00)
    
    for channel_name, schedule in scheduled_resets.items():
        category_text = f" → {schedule['category']}" if schedule['category'] else ""
        last_reset = schedule.get('last_reset', 'Never')
        
        embed.add_field(
            name=f"#{channel_name} ({schedule['type']})",
            value=f"**Time:** {schedule['hour']:02d}:{schedule['minute']:02d} {TIMEZONE}\n**Category:** {schedule['category'] or 'Default'}\n**Last Reset:** {last_reset}",
            inline=True
        )
    
    await ctx.send(embed=embed)

@bot.command(name='remove_schedule')
async def remove_schedule_command(ctx, channel_name: str):
    """
    Remove a scheduled reset
    Usage: !remove_schedule <channel_name>
    Example: !remove_schedule daily-chat
    """
    # Clean channel name
    if channel_name.startswith('#'):
        channel_name = channel_name[1:]
    
    if channel_name not in scheduled_resets:
        await ctx.send(f"❌ No scheduled reset found for **{channel_name}**")
        return
    
    del scheduled_resets[channel_name]
    save_schedules()
    
    await ctx.send(f"✅ Removed scheduled reset for **{channel_name}**")
    print(f"Schedule removed by {ctx.author}: {channel_name}")

@bot.command(name='reset_now')
async def reset_now_command(ctx, channel_name: str = None):
    """
    Manually trigger a channel reset
    Usage: !reset_now [channel_name]
    If no channel name is provided, shows available scheduled channels
    """
    if not channel_name:
        if not scheduled_resets:
            await ctx.send("❌ No scheduled resets configured. Use `!schedule_reset` first!")
            return
        
        channel_list = ", ".join([f"#{name}" for name in scheduled_resets.keys()])
        await ctx.send(f"Available channels: {channel_list}\nUsage: `!reset_now <channel_name>`")
        return
    
    # Clean channel name
    if channel_name.startswith('#'):
        channel_name = channel_name[1:]
    
    if channel_name not in scheduled_resets:
        await ctx.send(f"❌ **{channel_name}** is not in the scheduled resets. Use `!list_schedules` to see available channels.")
        return
    
    await ctx.send(f"🔄 Triggering manual reset for **{channel_name}**...")
    
    try:
        guild = bot.get_guild(GUILD_ID)
        if not guild:
            await ctx.send("❌ Guild not found!")
            return
        
        schedule = scheduled_resets[channel_name]
        await reset_channel_by_name(guild, channel_name, schedule)
        
        # Update last reset date
        tz = pytz.timezone(TIMEZONE)
        now = datetime.datetime.now(tz)
        schedule['last_reset'] = now.strftime('%Y-%m-%d')
        save_schedules()
        
        await ctx.send(f"✅ **{channel_name}** has been reset successfully!")
        print(f"Manual reset triggered by {ctx.author}: {channel_name}")
        
    except Exception as e:
        await ctx.send(f"❌ Error during reset: {e}")
        print(f"Error during manual reset of {channel_name}: {e}")

@bot.command(name='next_reset')
async def next_reset_command(ctx, channel_name: str = None):
    """
    Show when the next reset will occur for a channel or all channels
    Usage: !next_reset [channel_name]
    """
    tz = pytz.timezone(TIMEZONE)
    now = datetime.datetime.now(tz)
    
    if channel_name:
        # Clean channel name
        if channel_name.startswith('#'):
            channel_name = channel_name[1:]
        
        if channel_name not in scheduled_resets:
            await ctx.send(f"❌ **{channel_name}** is not in the scheduled resets.")
            return
        
        schedule = scheduled_resets[channel_name]
        today_reset = now.replace(hour=schedule['hour'], minute=schedule['minute'], second=0, microsecond=0)
        
        if now >= today_reset:
            next_reset = today_reset + datetime.timedelta(days=1)
        else:
            next_reset = today_reset
        
        await ctx.send(f"⏰ Next reset for **{channel_name}**: {next_reset.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    else:
        if not scheduled_resets:
            await ctx.send("📅 No scheduled resets configured.")
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
        
        await ctx.send(embed=embed)

@bot.command(name='help_reset')
async def help_reset_command(ctx):
    """Show help for reset commands"""
    embed = discord.Embed(title="🔄 Channel Reset Bot Commands", color=0x00ff00)
    
    embed.add_field(
        name="Schedule Reset",
        value="**Command:** `!schedule_reset` or `@resploot schedule_reset`\n"
              "**Usage:** `schedule_reset daily-chat text 10:42`\n"
              "**With category:** `schedule_reset daily-yap voice 04:30 \"Voice Channels\"`\n"
              "**Time format:** HH:MM (24-hour)",
        inline=False
    )
    
    embed.add_field(
        name="Other Commands",
        value="`!list_schedules` - Show all scheduled resets\n"
              "`!remove_schedule daily-chat` - Remove a schedule\n"
              "`!reset_now daily-chat` - Manual reset\n"
              "`!next_reset` - Show next reset times\n"
              "`!ping` - Test if bot is online",
        inline=False
    )
    
    embed.add_field(
        name="Bot Mention Examples",
        value="`@resploot schedule_reset morning-coffee text 07:00`\n"
              "`@resploot list_schedules`\n"
              "`@resploot` (for quick help)",
        inline=False
    )
    
    await ctx.send(embed=embed)

# Start the bot
bot.run(TOKEN)
