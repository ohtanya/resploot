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
GUILD_ID = None  # Set to None for global commands, or specify server ID for faster sync
TIMEZONE = "America/Los_Angeles"  # Change this to your timezone
SCHEDULES_FILE = "schedules.json"

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
    
    # Log current time every hour for debugging
    if now.minute == 0:
        print(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    # Check all guilds the bot is in
    for guild in bot.guilds:
        # Check each scheduled reset
        for channel_name, schedules in scheduled_resets.items():
            for schedule_index, schedule in enumerate(schedules):
                # Check if it's time to reset and we haven't reset at this specific time today
                schedule_key = f"{current_date}-{schedule['hour']:02d}:{schedule['minute']:02d}"
                if (now.hour == schedule['hour'] and 
                    now.minute == schedule['minute'] and 
                    schedule.get('last_reset') != schedule_key):
                    
                    print(f"Starting scheduled reset for {channel_name} (schedule {schedule_index+1}) in {guild.name} at {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                    
                    try:
                        await reset_channel_by_name(guild, channel_name, schedule)
                        
                        # Update last reset date with specific time
                        schedule['last_reset'] = schedule_key
                        save_schedules()
                        
                        print(f"Reset completed for {channel_name} in {guild.name}")
                        
                    except Exception as e:
                        print(f"Error during scheduled reset of {channel_name} in {guild.name}: {e}")

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
    pinned_messages = []
    
    # Only text channels can have pinned messages
    if hasattr(channel, 'pins') and channel_type == 'text':
        try:
            # Get all pinned messages
            pins = await channel.pins()
            for pin in pins:
                # Store message data for recreation
                pinned_messages.append({
                    'content': pin.content,
                    'author': pin.author,
                    'embeds': pin.embeds,
                    'attachments': [att.url for att in pin.attachments] if pin.attachments else [],
                    'created_at': pin.created_at
                })
            print(f"Found {len(pinned_messages)} pinned messages to preserve")
        except Exception as e:
            print(f"Error retrieving pinned messages: {e}")
    
    # Store channel properties
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
        
        # Restore pinned messages
        if pinned_messages:
            await new_channel.send("📌 **Restored Pinned Messages:**")
            restored_count = 0
            for msg_data in reversed(pinned_messages):  # Reverse to maintain chronological order
                try:
                    # Create embed for the preserved message
                    embed = discord.Embed(
                        description=msg_data['content'] or "*[No text content]*",
                        color=0x99ccff,
                        timestamp=msg_data['created_at']
                    )
                    embed.set_author(
                        name=msg_data['author'].display_name,
                        icon_url=msg_data['author'].display_avatar.url
                    )
                    embed.set_footer(text="📌 Originally pinned")
                    
                    # Add embeds from original message
                    content_parts = []
                    if msg_data['attachments']:
                        content_parts.append(f"🔗 **Attachments:** {', '.join(msg_data['attachments'])}")
                    
                    content = '\n'.join(content_parts) if content_parts else None
                    
                    restored_msg = await new_channel.send(content=content, embed=embed)
                    await restored_msg.pin()
                    restored_count += 1
                    
                except Exception as e:
                    print(f"Error restoring pinned message: {e}")
            
            if restored_count > 0:
                print(f"Restored {restored_count} pinned messages")
    
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

@bot.tree.command(name="resploot-clear", description="Clear all messages in current channel (preserves pinned messages)")
@app_commands.describe(
    confirm="Type 'yes' to confirm deletion of all messages in this channel"
)
async def clear_channel_slash(interaction: discord.Interaction, confirm: str):
    """Clear all chat history in the current channel"""
    
    # Safety check - require explicit confirmation
    if confirm.lower() != "yes":
        await interaction.response.send_message(
            "⚠️ **Are you sure?** This will delete ALL messages in this channel!\n"
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
        
        # Count messages first
        message_count = 0
        async for _ in channel.history(limit=None):
            message_count += 1
        
        if message_count == 0:
            await interaction.edit_original_response(content="✅ Channel is already empty!")
            return
        
        # Confirm we're about to delete messages
        await interaction.edit_original_response(content=f"🧹 Found {message_count} messages. Clearing channel and preserving pinned messages...")
        
        # Use our new preservation function
        await reset_channel_with_preservation(channel)
        
        # The function recreates the channel, so we need to find the new one
        new_channel = discord.utils.get(interaction.guild.channels, name=channel.name)
        if new_channel:
            # Send confirmation in the new channel
            embed = discord.Embed(
                title="🧹 Channel Cleared!", 
                description=f"Deleted {message_count} messages and recreated the channel.\n📌 Pinned messages have been preserved.",
                color=0x00ff00
            )
            embed.add_field(
                name="Cleared by", 
                value=interaction.user.mention, 
                inline=True
            )
            embed.add_field(
                name="Time", 
                value=f"<t:{int(datetime.datetime.now().timestamp())}:F>", 
                inline=True
            )
            
            await new_channel.send(embed=embed)
        
        print(f"Channel cleared by {interaction.user}: #{channel.name} ({message_count} messages)")
        
    except discord.Forbidden:
        await interaction.edit_original_response(content="❌ I don't have permission to delete/create channels in this server.")
    except Exception as e:
        await interaction.edit_original_response(content=f"❌ Error clearing channel: {e}")
        print(f"Error during channel clear: {e}")

@bot.tree.command(name="help", description="Show help for all commands")
async def help_slash(interaction: discord.Interaction):
    """Show help for reset commands"""
    embed = discord.Embed(title="🔄 Channel Reset Bot - Multiple Schedules Support", color=0x00ff00)
    
    embed.add_field(
        name="/schedule_reset",
        value="Schedule a daily reset for a channel\n**Example:** `/schedule_reset daily-chat text 10:42`\n**Multiple times:** Add as many schedules as you want per channel!\n**With category:** Add category name in the category field",
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
