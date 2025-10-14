import os
import discord
from discord.ext import commands, tasks
from discord import app_commands
import datetime
import pytz
import json
import asyncio
import aiohttp
import mimetypes
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Bot setup - message content intent needed to read pin content
intents = discord.Intents.default()
intents.message_content = True  # Required to read message content for pins
bot = commands.Bot(command_prefix="!", intents=intents)

# Configuration
GUILD_ID = None  # Set to None for global commands, or specify server ID for faster sync
TIMEZONE = "America/Los_Angeles"  # Change this to your timezone
SCHEDULES_FILE = "schedules.json"
PINS_DATA_DIR = "pins_data"  # Directory to store pin JSON files
ATTACHMENTS_DIR = "pins_data/attachments"  # Directory to store downloaded attachments

# Pin saving configuration - only save pins from this server (set to None to save from all servers)
PINS_ENABLED_SERVER_ID = int(os.getenv("PINS_ENABLED_SERVER_ID")) if os.getenv("PINS_ENABLED_SERVER_ID") else None

# Dictionary to store scheduled resets: {channel_name: [{'hour': X, 'minute': Y, 'type': 'text/voice', 'category': 'category_name', 'last_reset': 'YYYY-MM-DD-HH:MM'}]}
scheduled_resets = {}

def load_schedules():
    """Load scheduled resets from file"""
    global scheduled_resets
    try:
        with open(SCHEDULES_FILE, 'r') as f:
            data = json.load(f)
        
        # Migrate old format to new format if needed
        migrated = {}
        for channel_name, schedule_data in data.items():
            if isinstance(schedule_data, dict) and 'hour' in schedule_data:
                # Old format: single schedule per channel
                migrated[channel_name] = [schedule_data]
            elif isinstance(schedule_data, list):
                # New format: list of schedules per channel
                migrated[channel_name] = schedule_data
            else:
                # Invalid format, skip
                print(f"Skipping invalid schedule data for {channel_name}")
                continue
        
        scheduled_resets = migrated
        total_schedules = sum(len(schedules) for schedules in scheduled_resets.values())
        print(f"Loaded {total_schedules} scheduled resets across {len(scheduled_resets)} channels")
        
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

async def download_attachment(session, attachment, timestamp, guild_id):
    """Download an attachment and save it locally"""
    try:
        # Create attachments directory if it doesn't exist
        os.makedirs(ATTACHMENTS_DIR, exist_ok=True)
        
        # Parse the URL to get file extension
        parsed_url = urlparse(attachment.url)
        original_filename = attachment.filename
        
        # Create a safe filename with timestamp to avoid collisions
        safe_filename = f"{timestamp}_{attachment.id}_{original_filename}"
        local_path = os.path.join(ATTACHMENTS_DIR, safe_filename)
        
        # Download the file
        async with session.get(attachment.url) as response:
            if response.status == 200:
                with open(local_path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(8192):
                        f.write(chunk)
                
                print(f"Downloaded attachment: {safe_filename}")
                return {
                    "filename": original_filename,
                    "local_path": local_path,
                    "local_filename": safe_filename,
                    "url": attachment.url,
                    "original_url": attachment.url,
                    "size": attachment.size,
                    "content_type": attachment.content_type,
                    "downloaded": True
                }
            else:
                print(f"Failed to download attachment {original_filename}: HTTP {response.status}")
                return {
                    "filename": original_filename,
                    "url": attachment.url,
                    "original_url": attachment.url,
                    "size": attachment.size,
                    "content_type": attachment.content_type,
                    "downloaded": False,
                    "error": f"HTTP {response.status}"
                }
                
    except Exception as e:
        print(f"Error downloading attachment {attachment.filename}: {e}")
        return {
            "filename": attachment.filename,
            "url": attachment.url,
            "original_url": attachment.url,
            "size": attachment.size,
            "content_type": attachment.content_type,
            "downloaded": False,
            "error": str(e)
        }

async def save_pins_to_json(channel_name, pins, guild):
    """Save pinned messages to JSON file"""
    try:
        # Create pins data directory if it doesn't exist
        os.makedirs(PINS_DATA_DIR, exist_ok=True)
        
        # Prepare pins data with server information
        pins_data = {
            "guild_id": guild.id,
            "guild_name": guild.name,
            "channel_name": channel_name,
            "reset_timestamp": datetime.datetime.now().isoformat(),
            "pin_count": len(pins),
            "pins": []
        }
        
        # Extract data from each pin and download attachments
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30, connect=10)  # 30s total, 10s connect timeout
        ) as session:
            for pin in reversed(pins):  # Reverse to keep chronological order
                try:
                    # Debug: Print pin information
                    print(f"Processing pin {pin.id}")
                    print(f"  Content: '{pin.content}' (length: {len(pin.content)})")
                    print(f"  Author: {pin.author.display_name}")
                    print(f"  Attachments: {len(pin.attachments)}")
                    print(f"  Embeds: {len(pin.embeds)}")
                    
                    # Download attachments with robust error handling
                    attachment_data = []
                    if pin.attachments:
                        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        for att in pin.attachments:
                            print(f"  Downloading attachment: {att.filename}")
                            try:
                                # Download with individual timeout per attachment
                                attachment_info = await asyncio.wait_for(
                                    download_attachment(session, att, timestamp, guild.id),
                                    timeout=20.0  # 20 second timeout per attachment
                                )
                                attachment_data.append(attachment_info)
                                print(f"  ✓ Downloaded: {att.filename}")
                            except asyncio.TimeoutError:
                                print(f"  ⚠ Timeout downloading {att.filename}, continuing...")
                                attachment_data.append({
                                    "filename": att.filename,
                                    "url": att.url,
                                    "original_url": att.url,
                                    "size": att.size,
                                    "content_type": att.content_type,
                                    "downloaded": False,
                                    "error": "Download timeout"
                                })
                            except Exception as e:
                                print(f"  ✗ Error downloading {att.filename}: {e}")
                                attachment_data.append({
                                    "filename": att.filename,
                                    "url": att.url,
                                    "original_url": att.url,
                                    "size": att.size,
                                    "content_type": att.content_type,
                                    "downloaded": False,
                                    "error": str(e)
                                })
                    
                    pin_data = {
                        "id": pin.id,
                        "author": {
                            "name": pin.author.display_name,
                            "username": str(pin.author),
                            "id": pin.author.id,
                            "avatar_url": str(pin.author.display_avatar.url) if pin.author.display_avatar else None
                        },
                        "content": pin.content,
                        "created_at": pin.created_at.isoformat(),
                        "jump_url": pin.jump_url,
                        "attachments": attachment_data,
                        "embeds": [embed.to_dict() for embed in pin.embeds] if pin.embeds else [],
                        "reactions": [
                            {
                                "emoji": str(reaction.emoji),
                                "count": reaction.count
                            }
                            for reaction in pin.reactions
                        ] if pin.reactions else []
                    }
                    pins_data["pins"].append(pin_data)
                except Exception as e:
                    print(f"Error processing pin {pin.id}: {e}")
        
        # Save to file with timestamp in filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{channel_name}_{timestamp}.json"
        filepath = os.path.join(PINS_DATA_DIR, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(pins_data, f, indent=2, ensure_ascii=False)
        
        print(f"Saved {len(pins)} pins to {filepath}")
        return filepath
        
    except Exception as e:
        print(f"Error saving pins to JSON: {e}")
        return None

@bot.event
async def on_ready():
    tz = pytz.timezone(TIMEZONE)
    now = datetime.datetime.now(tz)
    
    print(f"Bot is online as {bot.user}")
    print(f"Current server time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    # Show timezone info for debugging
    server_time = datetime.datetime.now()
    print(f"VPS local time: {server_time.strftime('%Y-%m-%d %H:%M:%S')} (no timezone)")
    print(f"Bot timezone: {TIMEZONE}")
    print(f"Bot time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    # Load scheduled resets
    load_schedules()
    
    if scheduled_resets:
        print(f"Active schedules:")
        for channel_name, schedules in scheduled_resets.items():
            for i, schedule in enumerate(schedules):
                schedule_id = f"{i+1}" if len(schedules) > 1 else ""
                print(f"  - {channel_name}{schedule_id} ({schedule['type']}): {schedule['hour']:02d}:{schedule['minute']:02d}")
    else:
        print("No scheduled resets configured. Use /schedule_reset to add some!")
    
    # Sync slash commands
    try:
        if GUILD_ID:
            # Sync to specific guild (faster)
            guild = discord.Object(id=GUILD_ID)
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            print(f"Synced {len(synced)} slash commands to guild {GUILD_ID}")
        else:
            # Sync globally (takes up to 1 hour to propagate)
            synced = await bot.tree.sync()
            print(f"Synced {len(synced)} slash commands globally")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    
    reset_scheduler.start()

@tasks.loop(minutes=1)
async def reset_scheduler():
    """Check all scheduled resets and execute them if it's time"""
    tz = pytz.timezone(TIMEZONE)
    now = datetime.datetime.now(tz)
    current_date = now.strftime('%Y-%m-%d')
    
    # Log current time every 10 minutes for debugging
    if now.minute % 10 == 0:
        server_local = datetime.datetime.now()
        print(f"[SCHEDULER] Bot time ({TIMEZONE}): {now.strftime('%Y-%m-%d %H:%M:%S %Z')} | VPS local: {server_local.strftime('%H:%M:%S')} | Checking {len(scheduled_resets)} channel schedules")
    
    # Check if we have any schedules at all
    if not scheduled_resets:
        if now.minute == 0:  # Log once per hour
            print(f"[SCHEDULER] No schedules configured. Use /schedule_reset to add some!")
        return
    
    # Check all guilds the bot is in
    for guild in bot.guilds:
        # Check each scheduled reset
        for channel_name, schedules in scheduled_resets.items():
            for schedule_index, schedule in enumerate(schedules):
                # Check if it's time to reset and we haven't reset at this specific time today
                schedule_key = f"{current_date}-{schedule['hour']:02d}:{schedule['minute']:02d}"
                
                # Debug: Log when we're close to a scheduled time
                time_until = (schedule['hour'] * 60 + schedule['minute']) - (now.hour * 60 + now.minute)
                if time_until <= 2 and time_until >= 0:  # Within 2 minutes
                    print(f"[SCHEDULER] Approaching reset time for {channel_name} in {time_until} minutes")
                
                if (now.hour == schedule['hour'] and 
                    now.minute == schedule['minute'] and 
                    schedule.get('last_reset') != schedule_key):
                    
                    print(f"[SCHEDULER] ⏰ TRIGGERING scheduled reset for {channel_name} (schedule {schedule_index+1}) in {guild.name} at {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                    
                    try:
                        await reset_channel_by_name(guild, channel_name, schedule)
                        
                        # Update last reset date with specific time
                        schedule['last_reset'] = schedule_key
                        save_schedules()
                        
                        print(f"[SCHEDULER] ✅ Reset completed for {channel_name} in {guild.name}")
                        
                    except Exception as e:
                        print(f"[SCHEDULER] ❌ Error during scheduled reset of {channel_name} in {guild.name}: {e}")
                        import traceback
                        traceback.print_exc()

async def _delete_message_after_delay(message, delay_seconds):
    """Helper function to delete a message after a delay"""
    await asyncio.sleep(delay_seconds)
    try:
        await message.delete()
    except (discord.NotFound, discord.Forbidden):
        # Message already deleted or no permission
        pass

async def _delete_interaction_after_delay(interaction, delay_seconds):
    """Helper function to delete an interaction response after a delay"""
    await asyncio.sleep(delay_seconds)
    try:
        await interaction.delete_original_response()
    except (discord.NotFound, discord.Forbidden):
        # Message already deleted or no permission
        pass

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
    
    # Find the existing channel
    channel = discord.utils.get(guild.channels, name=channel_name)
    if channel:
        await reset_channel_with_preservation(channel, category, channel_type)
        print(f"Reset {channel_type} channel: {channel_name}")
    else:
        # Create new channel if it doesn't exist
        if channel_type == 'text':
            new_channel = await guild.create_text_channel(channel_name, category=category)
        elif channel_type == 'voice':
            new_channel = await guild.create_voice_channel(channel_name, category=category)
        else:
            raise ValueError(f"Invalid channel type: {channel_type}")
        print(f"Created {channel_type} channel: {channel_name}")

async def reset_channel_with_preservation(channel, category=None, channel_type='text'):
    """Reset a channel while preserving pinned messages"""
    
    # FOR FAST RESETS: Use archive method (move pins to separate channel, then recreate)
    # Set to False to use slow method (delete messages one by one)
    USE_FAST_ARCHIVE_METHOD = True
    
    # Only text channels can have messages to delete
    if channel_type != 'text' or not hasattr(channel, 'history'):
        # For voice channels, still use the old method (delete/recreate)
        channel_name = channel.name
        channel_category = category or channel.category
        channel_position = channel.position
        overwrites = channel.overwrites
        
        await channel.delete()
        
        new_channel = await channel.guild.create_voice_channel(
            name=channel_name,
            category=channel_category,
            position=channel_position,
            overwrites=overwrites
        )
        return new_channel
    
    # For text channels, choose fast or slow method
    if USE_FAST_ARCHIVE_METHOD:
        # FAST METHOD: Archive pins to separate channel, then recreate main channel
        guild = channel.guild
        channel_name = channel.name
        archive_name = "book-bot-pinned"
        
        try:
            # Get pinned messages and extract ALL content BEFORE deleting channel
            pins = []
            async for pin in channel.pins():
                pins.append(pin)
            pinned_count = len(pins)
            archived_count = 0
            
            if pinned_count > 0:
                # Save pins to JSON file for web interface (only for authorized server)
                json_file = None
                if PINS_ENABLED_SERVER_ID is None or guild.id == PINS_ENABLED_SERVER_ID:
                    try:
                        json_file = await save_pins_to_json(channel_name, pins, guild)
                        print(f"✅ Pins saved to web interface for server: {guild.name}")
                    except Exception as e:
                        print(f"Error saving pins to JSON: {e}")
                else:
                    print(f"📝 Pin saving disabled for server: {guild.name} (ID: {guild.id})")
                
                # Find or create archive channel BEFORE deleting the main channel
                archive_channel = discord.utils.get(guild.text_channels, name=archive_name)
                if not archive_channel:
                    archive_channel = await guild.create_text_channel(
                        archive_name, 
                        category=category or channel.category,
                        topic=f"📌 Archived pins from #{channel_name}"
                    )
                    print(f"Created archive channel: {archive_name}")
                
                # Add separator
                separator_embed = discord.Embed(
                    title=f"📌 Pins from #{channel_name}",
                    description=f"Reset: <t:{int(datetime.datetime.now().timestamp())}:F>",
                    color=0x99ccff
                )
                await archive_channel.send(embed=separator_embed)
                
                # Forward all pinned messages to archive channel (preserves everything!)
                for pin in reversed(pins):  # Reverse to keep chronological order
                    try:
                        # Forward the message - this preserves all content, embeds, attachments
                        await pin.forward(archive_channel)
                        archived_count += 1
                        print(f"Forwarded pin {pin.id} to archive")
                    except Exception as e:
                        print(f"Error forwarding pin {pin.id}: {e}")
                
                print(f"Forwarded {archived_count}/{pinned_count} pins to archive")
                if json_file:
                    print(f"Also saved pins to JSON: {json_file}")
            
            # Store channel properties
            channel_category = category or channel.category
            channel_position = channel.position
            channel_topic = getattr(channel, 'topic', None)
            channel_slowmode = getattr(channel, 'slowmode_delay', 0)
            overwrites = channel.overwrites
            
            # Delete and recreate channel (FAST!)
            await channel.delete()
            new_channel = await guild.create_text_channel(
                name=channel_name,
                category=channel_category,
                position=channel_position,
                topic=channel_topic,
                slowmode_delay=channel_slowmode,
                overwrites=overwrites
            )
            
            # Success message
            embed = discord.Embed(
                title="✅ Channel Reset Complete",
                description=f"**#{channel_name}** has been cleared successfully!\n\n📊 **Stats:**\n- Messages cleared: All\n- Pins archived: {archived_count}\n- Archive channel: #{archive_name}",
                color=0x00ff00
            )
            embed.set_footer(text=f"Reset completed at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            await new_channel.send(embed=embed)
            
            print(f"Fast reset completed for {channel_name}")
            return new_channel
            
        except Exception as e:
            print(f"Error during fast reset: {e}")
            # Fall back to slow method if fast method fails
            pass
    
    # SLOW METHOD: Delete messages but keep pins (original method)
    # For text channels, delete messages but keep pins
    deleted_count = 0
    pinned_messages = set()
    
    try:
        # Get all pinned messages first
        pins = []
        async for pin in channel.pins():
            pins.append(pin)
        pinned_messages = {pin.id for pin in pins}
        print(f"Found {len(pinned_messages)} pinned messages to preserve")
        
        # Delete messages in batches, skipping pinned ones
        async for message in channel.history(limit=None, oldest_first=False):
            if message.id not in pinned_messages:
                try:
                    await message.delete()
                    deleted_count += 1
                    
                    # Add small delay to avoid rate limits
                    if deleted_count % 10 == 0:
                        await asyncio.sleep(0.1)
                        
                except discord.NotFound:
                    # Message already deleted, continue
                    pass
                except discord.Forbidden:
                    print(f"No permission to delete message {message.id}")
                except Exception as e:
                    print(f"Error deleting message {message.id}: {e}")
        
        print(f"Deleted {deleted_count} messages, preserved {len(pinned_messages)} pinned messages")
        
        # Send a reset notification
        embed = discord.Embed(
            title="🔄 Channel Reset Complete",
            description=f"Deleted {deleted_count} messages\n� Preserved {len(pinned_messages)} pinned messages",
            color=0x00ff00,
            timestamp=datetime.datetime.now()
        )
        reset_message = await channel.send(embed=embed)
        
        # Delete the reset notification after 30 seconds
        asyncio.create_task(_delete_message_after_delay(reset_message, 30))
        
    except Exception as e:
        print(f"Error during message deletion: {e}")
        # Fall back to recreating the channel if message deletion fails
        return await reset_channel_by_recreation(channel, category, channel_type)
    
    return channel

async def reset_channel_by_recreation(channel, category=None, channel_type='text'):
    """Fallback method: Reset channel by deleting and recreating it"""
    channel_name = channel.name
    channel_category = category or channel.category
    channel_position = channel.position
    channel_topic = getattr(channel, 'topic', None)
    channel_slowmode = getattr(channel, 'slowmode_delay', 0)
    overwrites = channel.overwrites
    
    # Delete the channel
    await channel.delete()
    
    # Recreate the channel with same properties
    if channel_type == 'text':
        new_channel = await channel.guild.create_text_channel(
            name=channel_name,
            category=channel_category,
            position=channel_position,
            topic=channel_topic,
            slowmode_delay=channel_slowmode,
            overwrites=overwrites
        )
    elif channel_type == 'voice':
        new_channel = await channel.guild.create_voice_channel(
            name=channel_name,
            category=channel_category,
            position=channel_position,
            overwrites=overwrites
        )
    else:
        raise ValueError(f"Invalid channel type: {channel_type}")
    
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
    time="Time in HH:MM format - 24hr (14:30) or 12hr with AM/PM (2:30 PM)", 
    category="Category to place the channel in (optional)"
)
@app_commands.choices(channel_type=[
    discord.app_commands.Choice(name="Text Channel", value="text"),
    discord.app_commands.Choice(name="Voice Channel", value="voice")
])
async def schedule_reset_slash(interaction: discord.Interaction, channel_name: str, channel_type: str, time: str, category: str = None):
    """Schedule a daily reset for a channel"""
    # Parse time in HH:MM format (supports both 12hr and 24hr)
    try:
        time = time.strip().upper()  # Normalize input
        
        # Check for AM/PM format
        if 'AM' in time or 'PM' in time:
            # 12-hour format
            is_pm = 'PM' in time
            time_part = time.replace('AM', '').replace('PM', '').strip()
            
            if ':' in time_part:
                hour_str, minute_str = time_part.split(':')
                hour = int(hour_str)
                minute = int(minute_str)
            else:
                hour = int(time_part)
                minute = 0
            
            # Convert to 24-hour format
            if is_pm and hour != 12:
                hour += 12
            elif not is_pm and hour == 12:
                hour = 0
                
        else:
            # 24-hour format
            if ':' in time:
                hour_str, minute_str = time.split(':')
                hour = int(hour_str)
                minute = int(minute_str)
            else:
                hour = int(time)
                minute = 0
                
    except ValueError:
        await interaction.response.send_message("❌ Invalid time format. Use:\n• 24-hour: `14:30` or `2:30`\n• 12-hour: `2:30 PM` or `10:00 AM`", ephemeral=True)
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
    
    # Create new schedule entry
    new_schedule = {
        'type': channel_type.lower(),
        'hour': hour,
        'minute': minute,
        'category': category,
        'last_reset': None
    }
    
    # Add to existing schedules for this channel or create new list
    if channel_name not in scheduled_resets:
        scheduled_resets[channel_name] = []
    
    scheduled_resets[channel_name].append(new_schedule)
    save_schedules()
    
    schedule_count = len(scheduled_resets[channel_name])
    category_text = f" in category '{category}'" if category else ""
    await interaction.response.send_message(
        f"✅ Added schedule #{schedule_count} for **{channel_name}** ({channel_type}){category_text} at **{hour:02d}:{minute:02d}** {TIMEZONE}\n"
        f"This channel now has {schedule_count} reset(s) per day."
    )
    print(f"Scheduled reset added by {interaction.user}: {channel_name} at {hour:02d}:{minute:02d} (#{schedule_count})")

@bot.tree.command(name="list_schedules", description="Show all scheduled channel resets")
async def list_schedules_slash(interaction: discord.Interaction):
    """List all scheduled resets"""
    if not scheduled_resets:
        await interaction.response.send_message("📅 No scheduled resets configured yet. Use `/schedule_reset` to add some!", ephemeral=True)
        return
    
    embed = discord.Embed(title="📅 Scheduled Channel Resets", color=0x00ff00)
    
    for channel_name, schedules in scheduled_resets.items():
        if len(schedules) == 1:
            # Single schedule - keep simple format
            schedule = schedules[0]
            last_reset = schedule.get('last_reset', 'Never')
            if last_reset and '-' in last_reset and last_reset.count('-') >= 3:
                # New format: YYYY-MM-DD-HH:MM
                last_reset = last_reset.split('-', 3)[-1] if len(last_reset.split('-', 3)) > 3 else last_reset
            
            embed.add_field(
                name=f"#{channel_name} ({schedule['type']})",
                value=f"**Time:** {schedule['hour']:02d}:{schedule['minute']:02d} {TIMEZONE}\n**Category:** {schedule['category'] or 'Default'}\n**Last Reset:** {last_reset}",
                inline=True
            )
        else:
            # Multiple schedules - show all times
            times = []
            for i, schedule in enumerate(schedules):
                times.append(f"{i+1}. {schedule['hour']:02d}:{schedule['minute']:02d}")
            
            embed.add_field(
                name=f"#{channel_name} ({schedules[0]['type']}) - {len(schedules)} resets",
                value=f"**Times:** {', '.join(times)}\n**Category:** {schedules[0]['category'] or 'Default'}",
                inline=True
            )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="remove_schedule", description="Remove scheduled resets for a channel")
@app_commands.describe(
    channel_name="Name of the channel to remove from schedule",
    schedule_index="Schedule number to remove (leave empty to remove all schedules for this channel)"
)
async def remove_schedule_slash(interaction: discord.Interaction, channel_name: str, schedule_index: int = None):
    """Remove a scheduled reset or all schedules for a channel"""
    # Clean channel name
    if channel_name.startswith('#'):
        channel_name = channel_name[1:]
    
    if channel_name not in scheduled_resets:
        await interaction.response.send_message(f"❌ No scheduled resets found for **{channel_name}**", ephemeral=True)
        return
    
    schedules = scheduled_resets[channel_name]
    
    if schedule_index is None:
        # Remove all schedules for this channel
        del scheduled_resets[channel_name]
        save_schedules()
        await interaction.response.send_message(f"✅ Removed all {len(schedules)} scheduled reset(s) for **{channel_name}**")
        print(f"All schedules removed by {interaction.user}: {channel_name}")
    else:
        # Remove specific schedule by index
        if schedule_index < 1 or schedule_index > len(schedules):
            await interaction.response.send_message(f"❌ Invalid schedule number. **{channel_name}** has {len(schedules)} schedule(s) (1-{len(schedules)})", ephemeral=True)
            return
        
        removed_schedule = schedules.pop(schedule_index - 1)  # Convert to 0-based index
        
        if not schedules:  # If no schedules left, remove the channel entirely
            del scheduled_resets[channel_name]
        
        save_schedules()
        
        time_str = f"{removed_schedule['hour']:02d}:{removed_schedule['minute']:02d}"
        remaining = len(schedules) if schedules else 0
        
        if remaining > 0:
            await interaction.response.send_message(f"✅ Removed schedule #{schedule_index} ({time_str}) for **{channel_name}**. {remaining} schedule(s) remaining.")
        else:
            await interaction.response.send_message(f"✅ Removed schedule #{schedule_index} ({time_str}) for **{channel_name}**. No schedules remaining.")
        
        print(f"Schedule #{schedule_index} removed by {interaction.user}: {channel_name} at {time_str}")

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
        guild = interaction.guild
        if not guild:
            await interaction.edit_original_response(content="❌ Guild not found!")
            return
        
        # Use the first schedule for channel properties (type, category)
        # All schedules for a channel should have the same type and category
        schedule = scheduled_resets[channel_name][0]
        await reset_channel_by_name(guild, channel_name, schedule)
        
        # Update last reset date for all schedules of this channel
        tz = pytz.timezone(TIMEZONE)
        now = datetime.datetime.now(tz)
        reset_key = f"{now.strftime('%Y-%m-%d')}-MANUAL"
        
        for schedule in scheduled_resets[channel_name]:
            schedule['last_reset'] = reset_key
        save_schedules()
        
        schedule_count = len(scheduled_resets[channel_name])
        await interaction.edit_original_response(content=f"✅ **{channel_name}** has been reset successfully! ({schedule_count} schedule(s) updated)")
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
        
        schedules = scheduled_resets[channel_name]
        embed = discord.Embed(title=f"⏰ Next Reset Times for #{channel_name}", color=0x0099ff)
        
        next_resets = []
        for i, schedule in enumerate(schedules):
            today_reset = now.replace(hour=schedule['hour'], minute=schedule['minute'], second=0, microsecond=0)
            
            if now >= today_reset:
                next_reset = today_reset + datetime.timedelta(days=1)
            else:
                next_reset = today_reset
            
            schedule_num = f"#{i+1}" if len(schedules) > 1 else ""
            next_resets.append((next_reset, f"Schedule {schedule_num}".strip()))
        
        # Sort by next reset time
        next_resets.sort(key=lambda x: x[0])
        
        for next_reset, label in next_resets:
            embed.add_field(
                name=label,
                value=next_reset.strftime('%Y-%m-%d %H:%M:%S %Z'),
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    else:
        if not scheduled_resets:
            await interaction.response.send_message("📅 No scheduled resets configured.", ephemeral=True)
            return
        
        embed = discord.Embed(title="⏰ Next Reset Times", color=0x0099ff)
        
        for channel_name, schedules in scheduled_resets.items():
            if len(schedules) == 1:
                # Single schedule
                schedule = schedules[0]
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
            else:
                # Multiple schedules - show next one
                next_resets = []
                for schedule in schedules:
                    today_reset = now.replace(hour=schedule['hour'], minute=schedule['minute'], second=0, microsecond=0)
                    
                    if now >= today_reset:
                        next_reset = today_reset + datetime.timedelta(days=1)
                    else:
                        next_reset = today_reset
                    
                    next_resets.append(next_reset)
                
                # Show the earliest next reset
                earliest = min(next_resets)
                embed.add_field(
                    name=f"#{channel_name} ({len(schedules)} resets)",
                    value=earliest.strftime('%m/%d %H:%M'),
                    inline=True
                )
        
        await interaction.response.send_message(embed=embed)

@bot.tree.command(name="resploot-clear", description="Delete all messages except pinned ones in current channel")
@app_commands.describe(
    confirm="Type 'yes' to confirm deletion of all non-pinned messages"
)
async def clear_channel_slash(interaction: discord.Interaction, confirm: str):
    """Clear all chat history in the current channel"""
    
    # Safety check - require explicit confirmation
    if confirm.lower() != "yes":
        await interaction.response.send_message(
            "⚠️ **Are you sure?** This will delete ALL non-pinned messages in this channel!\n"
            "📌 Pinned messages will be preserved.\n"
            "To confirm, use: `/resploot-clear confirm:yes`",
            ephemeral=True
        )
        return
    
    # Check if user has manage messages permission
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("❌ You need 'Manage Messages' permission to use this command.", ephemeral=True)
        return
    
    await interaction.response.send_message("🧹 Starting to clear all messages in this channel...", ephemeral=True)
    
    try:
        channel = interaction.channel
        
        # Count total messages first
        total_count = 0
        pinned_count = 0
        async for message in channel.history(limit=None):
            total_count += 1
        
        # Count pinned messages
        pins = []
        async for pin in channel.pins():
            pins.append(pin)
        pinned_count = len(pins)
        messages_to_delete = total_count - pinned_count
        
        if total_count == 0:
            await interaction.edit_original_response(content="✅ Channel is already empty!")
            asyncio.create_task(_delete_interaction_after_delay(interaction, 30))
            return
        
        if messages_to_delete == 0:
            await interaction.edit_original_response(content="✅ Channel only contains pinned messages!")
            asyncio.create_task(_delete_interaction_after_delay(interaction, 30))
            return
        
        # Confirm we're about to delete messages
        progress_message = await interaction.edit_original_response(
            content=f"🧹 Found {total_count} total messages ({pinned_count} pinned). "
                   f"Deleting {messages_to_delete} messages while preserving pins..."
        )
        
        # Use our new preservation function that keeps the channel
        await reset_channel_with_preservation(channel)
        
        # Delete the progress message after 30 seconds
        asyncio.create_task(_delete_interaction_after_delay(interaction, 30))
        
        print(f"Channel cleared by {interaction.user}: #{channel.name} ({messages_to_delete} messages deleted, {pinned_count} pins preserved)")
        
    except discord.Forbidden:
        await interaction.edit_original_response(content="❌ I don't have permission to delete/create channels in this server.")
        asyncio.create_task(_delete_interaction_after_delay(interaction, 30))
    except Exception as e:
        await interaction.edit_original_response(content=f"❌ Error clearing channel: {e}")
        asyncio.create_task(_delete_interaction_after_delay(interaction, 30))
        print(f"Error during channel clear: {e}")

@bot.tree.command(name="help", description="Show help for all commands")
async def help_slash(interaction: discord.Interaction):
    """Show help for reset commands"""
    embed = discord.Embed(title="🔄 Channel Reset Bot - Multiple Schedules Support", color=0x00ff00)
    
    embed.add_field(
        name="/schedule_reset",
        value="Schedule a daily reset for a channel\n**Examples:** \n• `/schedule_reset daily-chat text 10:42 AM`\n• `/schedule_reset daily-chat text 22:30` (24hr)\n• `/schedule_reset daily-chat text 2:30 PM`\n**Multiple times:** Add as many schedules as you want per channel!\n**With category:** Add category name in the category field",
        inline=False
    )
    
    embed.add_field(
        name="Managing Schedules",
        value="`/list_schedules` - Show all scheduled resets\n"
              "`/remove_schedule channel_name` - Remove ALL schedules for channel\n"
              "`/remove_schedule channel_name schedule_index:2` - Remove specific schedule #2\n"
              "`/next_reset` - Show next reset times for all channels\n"
              "`/next_reset channel_name` - Show all upcoming resets for specific channel",
        inline=False
    )
    
    embed.add_field(
        name="Other Commands",
        value="`/reset_now channel_name` - Manual reset\n"
              "`/resploot-clear confirm:yes` - Clear ALL messages (preserves pinned)\n"
              "`/ping` - Test if bot is online",
        inline=False
    )
    
    embed.add_field(
        name="✨ Features",
        value="• **Multiple resets per day** per channel\n"
              "• **Smart schedule management** - remove specific schedules by number\n"
              "• **Pinned message preservation** - important messages are saved during resets\n"
              "• **Enhanced displays** - see all times at once\n"
              "• **Automatic migration** - old single schedules still work",
        inline=False
    )
    
    embed.add_field(
        name="Time Format",
        value="Use 24-hour format: `04:30`, `10:42`, `16:20`, `23:30`",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Start the bot
bot.run(TOKEN)
