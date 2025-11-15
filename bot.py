import asyncio
import json
import discord
import random
import os
import subprocess
from collections import deque
import re
from datetime import datetime, timedelta, timezone

# --- NEW: Library Version Check ---
# This code requires discord.py version 2.0 or higher for slash commands.
if discord.__version__.split('.')[0] < '2':
    print("Error: Your discord.py version is too old.")
    print(f"You have version {discord.__version__}, but this bot requires version 2.0.0 or higher.")
    print("Please update it by running: pip install -U discord.py")
    exit()

# --- NEW: Load environment variables from .env file ---
from dotenv import load_dotenv
load_dotenv()

from discord import app_commands
from discord.ext import tasks
from werwolf import WerwolfGame, FakeUser
from api_helpers import get_chat_response, get_relationship_summary_from_api, get_wrapped_summary_from_api

# --- CONFIGURATION ---


# !! WARNING: This is the "easy" way, NOT the "safe" way. !!
# !! DO NOT SHARE THIS FILE WITH YOUR KEYS IN IT. !!

# 1. SET these as environment variables
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "").strip().strip('"').strip("'")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# --- NEW: Database Configuration ---
# Set these as environment variables for security, or hardcode for testing.
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_USER = os.environ.get("DB_USER", "sulfur_bot_user")
DB_PASS = os.environ.get("DB_PASS", "") # No password is set for this user
DB_NAME = os.environ.get("DB_NAME", "sulfur_bot")

# --- REFACTORED: Add a more robust token check with diagnostics ---
if not DISCORD_BOT_TOKEN:
    print("Error: DISCORD_BOT_TOKEN environment variable is not set.")
    print("Please ensure your '.env' file exists in the same directory as the bot and contains the line:")
    print('DISCORD_BOT_TOKEN="YOUR_BOT_TOKEN_HERE"')
    exit()

# --- NEW: Diagnostic check to ensure the token looks valid ---
token_parts = DISCORD_BOT_TOKEN.split('.')
if len(token_parts) != 3:
    print("Error: The DISCORD_BOT_TOKEN appears to be malformed.")
    print(f"  -> Sanitized Token Preview: {DISCORD_BOT_TOKEN[:5]}...{DISCORD_BOT_TOKEN[-5:]}")
    print("A valid token should have three parts separated by dots. Please get a new token from the Discord Developer Portal.")
    exit()

# --- REFACTORED: Check for API keys based on provider ---
def check_api_keys(cfg):
    """Checks if the required API key for the selected provider is set."""
    provider = cfg.get('api', {}).get('provider')
    if provider == 'gemini' and not GEMINI_API_KEY:
        return "Error: API provider is 'gemini' but GEMINI_API_KEY is not set."
    if provider == 'openai' and not OPENAI_API_KEY:
        return "Error: API provider is 'openai' but OPENAI_API_KEY is not set."
    return None

# --- NEW: Load Configuration from JSON ---
def load_config():
    """Loads settings from config.json and the system prompt."""
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)

        prompt_file = config.get("bot", {}).get("system_prompt_file", "system_prompt.txt")
        with open(prompt_file, "r", encoding="utf-8") as f:
            config["bot"]["system_prompt"] = f.read()
            
        return config
    except FileNotFoundError as e:
        print(f"FATAL: Configuration file not found: {e.filename}. Please ensure 'config.json' and the prompt file exist.")
        exit()
    except json.JSONDecodeError:
        print("FATAL: 'config.json' is malformed. Please check the JSON syntax.")
        exit()

def save_config(new_config):
    """Saves the provided configuration dictionary back to config.json."""
    # We don't want to save the full system prompt back into the file
    config_to_save = new_config.copy()
    if 'bot' in config_to_save and 'system_prompt' in config_to_save['bot']:
        del config_to_save['bot']['system_prompt']
        
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(config_to_save, f, indent=2)

config = load_config()

# --- REFACTORED: Validate API keys after loading config ---
key_error = check_api_keys(config)
if key_error:
    print(key_error)
    exit()

# --- DISCORD BOT SETUP ---

# You gotta enable "Intents" for the bot in the Discord Dev Portal
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True  # Lets it read the message
intents.guilds = True           # Needs this for channel context
intents.voice_states = True      # To track who joins/leaves VCs
intents.members = True           # To get the full member list for presence updates
intents.presences = True         # To get member status (online, idle, etc.)

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# --- NEW: Werwolf Game State ---
# This will store active games, mapping a channel ID to a WerwolfGame object.
active_werwolf_games = {}

# --- NEW: Import and initialize DB helpers ---
from db_helpers import init_db_pool, initialize_database, get_leaderboard, add_xp, get_player_rank, get_level_leaderboard, save_message_to_history, get_chat_history, get_relationship_summary, update_relationship_summary, save_bulk_history, clear_channel_history, update_user_presence, add_balance, update_spotify_history, get_all_managed_channels, remove_managed_channel, get_managed_channel_config, update_managed_channel_config, log_message_stat, log_vc_minutes, get_wrapped_stats_for_period, get_user_wrapped_stats, log_stat_increment, get_spotify_history, get_player_profile, cleanup_custom_status_entries, log_mention_reply, log_vc_session, get_wrapped_extra_stats, get_gemini_usage, increment_gemini_usage, get_xp_for_level
import db_helpers
db_helpers.init_db_pool(DB_HOST, DB_USER, DB_PASS, DB_NAME)
from level_system import grant_xp
# --- NEW: Import Voice Manager ---
import voice_manager
# --- NEW: Import Economy ---
from economy import calculate_level_up_bonus

# --- MODIFIED: Pass client to DB initialization ---
db_helpers.initialize_database()

# --- NEW: Gemini API Usage Tracking (DB Version) ---
GEMINI_DAILY_LIMIT = 250 # Daily call limit for Gemini

async def get_current_provider(config_obj):
    """
    Checks Gemini API usage and returns the appropriate provider ('gemini' or 'openai').
    If the Gemini daily limit is reached, it will switch to 'openai' for the rest of the day.
    """
    provider = config_obj['api']['provider']
    # --- FIX: Only check Gemini usage if the provider is set to 'gemini' ---
    if provider == 'gemini':
        usage = await db_helpers.get_gemini_usage()
        # If the limit is reached, switch to openai for this call.
        return 'openai' if usage >= GEMINI_DAILY_LIMIT else 'gemini'
    # If the provider is 'openai' or anything else, just use that.
    return provider

# --- NEW: In-memory cache to prevent duplicate Spotify logging ---
last_spotify_log = {}
# --- NEW: In-memory cache for tracking Spotify listening start times ---
spotify_start_times = {}
# --- NEW: In-memory cache to handle Spotify pause/resume ---
spotify_pause_cache = {}
# --- NEW: In-memory cache for tracking game session start times ---
game_start_times = {}
# --- NEW: In-memory cache for tracking active voice channel users for XP ---
active_vc_users = {}
# --- NEW: In-memory cache for tracking voice session start times ---
vc_session_starts = {}

# --- NEW: Bot Start Time for Uptime Command ---
BOT_START_TIME = datetime.now(timezone.utc)


@client.event
async def on_error(event, *args, **kwargs):
    """
    Global event handler for unhandled exceptions in other event listeners (e.g., on_message).
    """
    import sys
    import traceback
    print(f"Unhandled exception in event '{event}':", file=sys.stderr)
    traceback.print_exc()
    # --- NEW: Set status to idle on unhandled error ---
    await client.change_presence(
        status=discord.Status.idle,
        activity=discord.Activity(type=discord.ActivityType.watching, name="on an error...")
    )

@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Handles errors from the command tree globally."""
    if isinstance(error, app_commands.CommandNotFound):
        # This can happen if a user tries to use a command that was recently removed.
        # The command might still be cached on their Discord client.
        message = (
            "Huch, dieser Befehl ist veraltet. Dein Discord hat noch die alte Version gespeichert. **Bitte versuche, die Discord-App vollständig zu schließen und neu zu starten**, um die Befehlsliste zu aktualisieren.",
        )
    elif isinstance(error, app_commands.TransformerError):
        # NEW: Handle cases where a user provides invalid input for an argument (e.g., text for a user mention)
        message = (
            f"Ich konnte die Eingabe '{error.value}' nicht verstehen. Bitte wähle die Option (z.B. den Benutzer) direkt aus der Liste aus, die Discord vorschlägt.",
        )
    elif isinstance(error, app_commands.CheckFailure):
        # This is a generic catch-all for when a command's check fails.
        # The custom checks like `check_channel_owner` already send their own specific messages.
        # This will primarily catch failures from `is_admin_or_authorised`.
        message = "Dir fehlt die Berechtigung, diesen Befehl zu verwenden. Du musst entweder ein Admin sein oder die 'authorised' Rolle haben."
    elif isinstance(error, app_commands.BotMissingPermissions):
        # The bot lacks permissions to perform an action (e.g., create channels, send messages).
        missing_perms = ", ".join(error.missing_permissions)
        message = f"Ich kann das nicht tun, weil mir die folgenden Berechtigungen fehlen: `{missing_perms}`. Bitte gib mir die nötigen Rechte, du Noob. :erm:"
    elif isinstance(error, app_commands.CommandOnCooldown):
        # The user is spamming a command.
        message = f"Chill mal, du kannst diesen Befehl erst in **{error.retry_after:.1f} Sekunden** wieder benutzen."
    else:
        # For other errors, log them to the console.
        print(f"Unhandled exception in command tree: {error}")
        message = "Ups, da ist etwas schiefgelaufen. Wahrscheinlich deine Schuld. :dono:"
        # --- NEW: Set status to idle on unhandled command error ---
        await client.change_presence(
            status=discord.Status.idle,
            activity=discord.Activity(type=discord.ActivityType.watching, name="on an error...")
        )

    # --- FIX: Use followup if interaction is already acknowledged ---
    try:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
    except discord.errors.HTTPException as e:
        # This can happen if the original interaction token expires or is invalid.
        print(f"Failed to send error message for interaction {interaction.id}: {e}")

async def split_message(text, limit=2000):
    """
    Splits a long message into chunks for Discord.
    """
    chunks = []
    current_chunk = ""
    for line in text.split('\n'):
        if len(current_chunk) + len(line) + 1 > limit:
            chunks.append(current_chunk)
            current_chunk = line
        else:
            current_chunk += '\n' + line
    chunks.append(current_chunk.strip()) # Add the last chunk
    return chunks

async def replace_emoji_tags(text, client):
    """
    Replaces :emoji_name: style tags with the actual Discord emoji object
    from any server the bot is in.
    """
    # Find all :emoji_name: tags in the text
    emoji_tags = re.findall(r':(\w+):', text)
    if not emoji_tags:
        return text

    # Create a global mapping of all available emoji names to their string representation
    emoji_map = {}
    for emoji in client.emojis:
        if emoji.name not in emoji_map:
            emoji_map[emoji.name] = str(emoji)

    # Replace the tags found in the message
    for tag in set(emoji_tags): # Use set to avoid replacing the same tag multiple times
        if tag in emoji_map:
            text = text.replace(f":{tag}:", emoji_map[tag])
    return text

def get_embed_color(config_obj):
    """Helper function to parse the hex color from config into a discord.Color object."""
    hex_color = config_obj.get('bot', {}).get('embed_color', '#7289DA') # Default to blurple
    return discord.Color(int(hex_color.lstrip('#'), 16))

@client.event
async def on_ready():
    """Fires when the bot logs in."""
    # --- NEW: Scan for existing Spotify sessions on startup ---
    print("Scanning for active Spotify sessions on startup...")
    initial_spotify_logs = 0
    for guild in client.guilds:
        for member in guild.members:
            if member.bot: continue
            # Find Spotify activity
            spotify_activity = next((activity for activity in member.activities if isinstance(activity, discord.Spotify)), None)
            if spotify_activity:
                # --- REFACTORED: Use a single user_id key for all caches ---
                song_tuple = (spotify_activity.title, spotify_activity.artist)
                # --- FIX: Check pause cache on startup ---
                if member.id not in spotify_pause_cache:
                    await db_helpers.update_spotify_history(client, member.id, member.display_name, song_tuple[0], song_tuple[1])
                
                last_spotify_log[member.id] = song_tuple
                spotify_start_times[member.id] = (song_tuple, datetime.now(timezone.utc))
                spotify_pause_cache.pop(member.id, None) # Clear pause cache
                initial_spotify_logs += 1
    if initial_spotify_logs > 0:
        print(f"  -> Found and started tracking {initial_spotify_logs} active Spotify session(s).")


    # --- NEW: Unmute all users on startup ---
    # This handles cases where the bot crashed and left users muted/deafened.
    print("Checking for users left muted from a previous session...")
    unmuted_count = 0
    for guild in client.guilds:
        for vc in guild.voice_channels:
            for member in vc.members:
                # Check if the member is server-muted or server-deafened
                if member.voice and (member.voice.mute or member.voice.deaf):
                    try:
                        await member.edit(mute=False, deafen=False, reason="Bot restart cleanup")
                        print(f"  -> Unmuted {member.display_name} in '{guild.name}'.")
                        unmuted_count += 1
                    except (discord.Forbidden, discord.HTTPException) as e:
                        print(f"  -> Failed to unmute {member.display_name}: {e}")
    if unmuted_count > 0:
        print(f"Cleanup complete. Unmuted {unmuted_count} user(s).")

    # --- NEW: Run one-time cleanup for old database entries ---
    print("Running one-time database cleanup tasks...")
    await db_helpers.cleanup_custom_status_entries()

    # --- NEW: Clean up leftover game channels on restart ---
    print("Checking for leftover game channels...")
    for guild in client.guilds:
        for category in guild.categories:
            if category.name == "🐺 WERWOLF SPIEL 🐺":
                print(f"Found leftover category in '{guild.name}'. Cleaning up...")
                for channel in category.channels:
                    try:
                        await channel.delete(reason="Bot restart cleanup")
                    except (discord.Forbidden, discord.NotFound):
                        pass # Ignore if we can't delete or it's already gone
                try:
                    await category.delete(reason="Bot restart cleanup")
                except (discord.Forbidden, discord.NotFound):
                    pass
    # --- NEW: Create 'authorised' role on boot ---
    print("Checking for 'authorised' role in guilds...")
    for guild in client.guilds:
        if not discord.utils.get(guild.roles, name=config['bot']['authorised_role']):
            try:
                await guild.create_role(name=config['bot']['authorised_role'], reason="Rolle für Bot-Admin-Befehle")
                print(f"Rolle 'authorised' im Server '{guild.name}' erstellt.")
            except discord.Forbidden:
                print(f"Konnte Rolle '{config['bot']['authorised_role']}' in '{guild.name}' nicht erstellen. Fehlende Berechtigung 'Rollen verwalten'.")

    # --- NEW: Clean up orphaned voice channels on restart ---
    print("Checking for orphaned voice channels...")
    managed_channel_ids = await db_helpers.get_all_managed_channels()
    if managed_channel_ids:
        for channel_id in managed_channel_ids:
            channel = client.get_channel(channel_id)
            if not channel:
                # Channel doesn't exist on Discord, remove from DB
                await db_helpers.remove_managed_channel(channel_id)
                print(f"Removed non-existent channel {channel_id} from database.")
            elif isinstance(channel, discord.VoiceChannel) and len(channel.members) == 0:
                # Channel exists but is empty, delete it
                try:
                    await channel.delete(reason="Bot restart cleanup (empty channel)")
                    await db_helpers.remove_managed_channel(channel_id) # Also remove from DB
                    print(f"Cleaned up empty orphaned channel: {channel.name} ({channel_id})")
                except (discord.Forbidden, discord.NotFound):
                    await db_helpers.remove_managed_channel(channel_id) # Still remove from DB if delete fails
    synced = await tree.sync()
    # --- NEW: Start the background task for voice XP ---
    if not grant_voice_xp.is_running():
        grant_voice_xp.start()
    # --- NEW: Start the background task for presence updates ---
    if not update_presence_task.is_running():
        update_presence_task.start()
    # --- NEW: Start the background task for Wrapped event management ---
    if not manage_wrapped_event.is_running():
        manage_wrapped_event.start()
    # --- NEW: Start the background task for empty channel cleanup ---
    if not cleanup_empty_channels.is_running():
        cleanup_empty_channels.start()
    

    print(f"Synced {len(synced)} global commands.")

    print(f'Ayo, the bot is logged in and ready, fam! ({client.user})')
    print('Let\'s chat.')

@tasks.loop(minutes=15)
async def update_presence_task():
    """A background task that periodically updates the bot's presence to watch a random user."""
    update_presence_task.change_interval(minutes=config['bot']['presence']['update_interval_minutes'])

    if not client.guilds:
        return

    # --- NEW: Check if an update is pending ---
    if os.path.exists("update_pending.flag"):
        await client.change_presence(
            status=discord.Status.idle, # Set status to Idle
            activity=discord.Activity(type=discord.ActivityType.watching, name="auf ein Update...")
        )
        return # Skip the normal presence update

    # --- REFACTORED: Find an online user and set a cool presence ---
    all_members = []
    # Get all non-bot members from all guilds
    for guild in client.guilds:
        all_members.extend([m for m in guild.members if not m.bot])

    random.shuffle(all_members)

    for member_candidate in all_members:
        try:
            # Fetch the member again to get the most up-to-date status
            # We fetch the member to ensure they still exist in the guild.
            fresh_member = await member_candidate.guild.fetch_member(member_candidate.id) 
            if fresh_member:
                # Found a valid user (online or offline), now set the cool presence
                templates = config['bot']['presence']['activity_templates']
                template = random.choice(templates)
                activity_name = template.format(user=fresh_member.display_name)
                
                print(f"  -> Presence update: {activity_name}")
                await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=activity_name))
                return  # Success, exit the task for this run
        except (discord.NotFound, discord.HTTPException):
            continue  # Member left or another issue, try next candidate

    # Fallback if no human members were found at all.
    print("  -> Presence update: No human members found. Using fallback.")
    fallback_activity = config.get('bot', {}).get('presence', {}).get('fallback_activity', "euch beim AFK sein zu")
    await client.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(type=discord.ActivityType.watching, name=fallback_activity)
    )

@update_presence_task.before_loop
async def before_update_presence_task():
    await client.wait_until_ready()

# --- NEW: Periodic Channel Cleanup Task ---
@tasks.loop(hours=1)
async def cleanup_empty_channels():
    """Periodically finds and deletes empty, managed voice channels."""
    print("Running periodic cleanup of empty voice channels...")
    managed_channel_ids = await db_helpers.get_all_managed_channels()
    deleted_count = 0
    if not managed_channel_ids:
        print("  -> No managed channels found in the database.")
        return

    for channel_id in managed_channel_ids:
        channel = client.get_channel(channel_id)
        if channel and isinstance(channel, discord.VoiceChannel) and not channel.members:
            try:
                await channel.delete(reason="Periodic cleanup of empty channel")
                await db_helpers.remove_managed_channel(channel_id, keep_owner_record=True)
                print(f"  -> Cleaned up empty channel: {channel.name} ({channel_id})")
                deleted_count += 1
            except (discord.Forbidden, discord.NotFound):
                # If we can't delete, at least remove it from our active list
                await db_helpers.remove_managed_channel(channel_id, keep_owner_record=True)
    if deleted_count > 0:
        print(f"Periodic cleanup finished. Deleted {deleted_count} empty channel(s).")

@client.event
async def on_presence_update(before, after):
    """Fires when a member's status, activity, etc. changes. Used for tracking."""
    # Ignore bots
    if after.bot:
        return
        
    # --- NEW: Ignore presence updates from offline users to reduce noise ---
    if after.status == discord.Status.offline and before.status == discord.Status.offline:
        return

    # --- NEW: Spotify Listening Time Tracking ---
    now = datetime.now(timezone.utc)
    # --- REFACTORED: Use a single user_id key to centralize tracking across all servers ---
    user_id = after.id

    # Check if a song was playing and has now stopped/changed
    if user_id in spotify_start_times:
        logged_song, start_time = spotify_start_times[user_id]
        after_spotify = next((act for act in after.activities if isinstance(act, discord.Spotify)), None)
        
        # Condition for song stopping: no spotify activity OR a different song is playing
        if not after_spotify or (after_spotify.title, after_spotify.artist) != logged_song:
            print(f"  -> [Spotify] Song stopped/changed for {after.display_name} (ID: {user_id}).")
            # --- NEW: Handle pause case ---
            if not after_spotify:
                print(f"    - Paused '{logged_song[0]}'. Caching session.")
                spotify_pause_cache[user_id] = (logged_song, start_time)
                del spotify_start_times[user_id] # Stop the active timer
                return # Exit early, don't log duration yet
            duration_seconds = (now - start_time).total_seconds()
            # Only log if they listened for a meaningful amount of time (e.g., > 30 seconds)
            # The check `if user_id in spotify_start_times` prevents logging duration multiple times from different server events.
            if duration_seconds > 30 and user_id in spotify_start_times:
                duration_minutes = duration_seconds / 60.0
                stat_period = now.strftime('%Y-%m')
                # Use a generic function to increment the JSON value
                await db_helpers.log_stat_increment(user_id, stat_period, 'spotify_minutes', key=f"{logged_song[0]} by {logged_song[1]}", amount=duration_minutes)
                print(f"    - Logged {duration_minutes:.2f} mins for '{logged_song[0]}'.")
                # Remove the entry immediately after logging to prevent duplicates.
                del spotify_start_times[user_id]

    # Check if a new song has started
    after_spotify = next((act for act in after.activities if isinstance(act, discord.Spotify)), None)
    if after_spotify:
        # --- NEW: Handle resume case ---
        resumed_song = (after_spotify.title, after_spotify.artist)
        if user_id in spotify_pause_cache and spotify_pause_cache[user_id][0] == resumed_song:
            print(f"  -> [Spotify] Resumed '{resumed_song[0]}' for {after.display_name}. Restarting timer.")
            spotify_start_times[user_id] = spotify_pause_cache.pop(user_id) # Restore timer from cache
        elif user_id not in spotify_start_times:
             print(f"  -> [Spotify] New song session started for {after.display_name} (ID: {user_id}): '{after_spotify.title}'. Starting timer.")
             spotify_start_times[user_id] = (resumed_song, now)

    # --- NEW: Game Session Tracking ---
    before_game = next((act for act in before.activities if isinstance(act, discord.Game)), None)
    after_game = next((act for act in after.activities if isinstance(act, discord.Game)), None)

    # Case 1: Game has stopped or changed
    if before_game and (not after_game or after_game.name != before_game.name):
        if user_id in game_start_times and game_start_times[user_id][0] == before_game.name:
            _, start_time = game_start_times.pop(user_id)
            duration_seconds = (now - start_time).total_seconds()
            # Only log sessions longer than a minute to filter out quick restarts/alt-tabs
            if duration_seconds > 60:
                duration_minutes = duration_seconds / 60.0
                stat_period = now.strftime('%Y-%m')
                await db_helpers.log_game_session(user_id, stat_period, before_game.name, duration_minutes)
            print(f"  -> [Game] Session ended for {after.display_name}: '{before_game.name}' after {duration_seconds/60.0:.1f} minutes.")

    # Case 2: A new game has started
    if after_game and (not before_game or before_game.name != after_game.name):
        if user_id not in game_start_times:
            game_start_times[user_id] = (after_game.name, now)
            print(f"  -> [Game] Session started for {after.display_name}: '{after_game.name}'.")

    # We only care about changes in status or activity
    if before.status == after.status and before.activity == after.activity:
        return

    # --- NEW: Spotify Tracking ---
    # --- FIX: Use in-memory cache to prevent duplicate song logging ---
    if isinstance(after.activity, discord.Spotify):
        current_song = (after.activity.title, after.activity.artist)
        last_logged_song_for_user = last_spotify_log.get(user_id)
        
        if current_song != last_logged_song_for_user:
            print(f"  -> [Spotify] New unique song detected for {after.display_name} (ID: {user_id}). Incrementing play count.")
            spotify_pause_cache.pop(user_id, None) # Clear pause cache on new song
            await db_helpers.update_spotify_history(
                client=client, # Pass client for logging
                user_id=after.id,
                display_name=after.display_name,
                song_title=after.activity.title,
                song_artist=after.activity.artist
            )
            last_spotify_log[user_id] = current_song

    activity_name = None
    if after.activity:
        # For games, streaming, etc., it has a name. For custom status, it's in 'state'.
        activity_name = after.activity.name or after.activity.state
    
    # --- NEW: Prioritize non-custom activities ---
    # Find the most "important" activity to log.
    # Order of importance: Game > Spotify > Other Activity > Custom Status
    primary_activity = next((act for act in after.activities if isinstance(act, discord.Game)), None)
    if not primary_activity:
        primary_activity = next((act for act in after.activities if isinstance(act, discord.Spotify)), None)
    if not primary_activity:
        primary_activity = next((act for act in after.activities if not isinstance(act, discord.CustomActivity)), None)
    if not primary_activity:
        primary_activity = next((act for act in after.activities if isinstance(act, discord.CustomActivity)), None)

    # Update the database with the new presence info
    await db_helpers.update_user_presence(
        user_id=after.id,
        display_name=after.display_name,
        status=str(after.status),
        activity_name=primary_activity.name if primary_activity and hasattr(primary_activity, 'name') else (primary_activity.state if primary_activity and hasattr(primary_activity, 'state') else None)
    )

    # --- NEW: Log generic activity for Wrapped ---
    # This logs any activity that isn't a game or Spotify.
    generic_activity = next((act for act in after.activities if not isinstance(act, (discord.Game, discord.Spotify, discord.CustomActivity))), None)
    if generic_activity and generic_activity.name:
        # We only care if the activity has changed to avoid spamming the DB.
        # Also, ensure the activity name is not something generic we want to ignore.
        before_generic_activity = next((act for act in before.activities if not isinstance(act, (discord.Game, discord.Spotify, discord.CustomActivity))), None)
        if not before_generic_activity or before_generic_activity.name != generic_activity.name:
            stat_period = now.strftime('%Y-%m')
            await db_helpers.log_stat_increment(
                user_id=user_id,
                stat_period=stat_period,
                column_name='activity_usage',
                key=generic_activity.name
            )


@tasks.loop(minutes=1)
async def grant_voice_xp():
    """A background task that grants XP to users in voice channels every minute.
    This is now highly efficient as it only iterates over users currently in a VC."""
    # Create a copy of the user IDs to prevent issues if the set changes during iteration
    users_to_process = list(active_vc_users.keys())
    
    for user_id in users_to_process:
        member = active_vc_users.get(user_id)
        if not member: continue

        stat_period = datetime.now(timezone.utc).strftime('%Y-%m')
        new_level = await db_helpers.add_xp(member.id, member.display_name, config['modules']['leveling']['xp_per_minute_in_vc'])
        await db_helpers.log_vc_minutes(member.id, 1, stat_period) # Log 1 minute for Wrapped
        if new_level:
            bonus = calculate_level_up_bonus(new_level, config)
            await db_helpers.add_balance(member.id, member.display_name, bonus, config, stat_period)
            # --- FIX: Send level-up notifications via DM and only for special levels ---
            if new_level % config['modules']['leveling']['vc_level_up_notification_interval'] == 0:
                try:
                    await member.send(f"GG! Du bist durch deine Aktivität im Voice-Chat jetzt Level **{new_level}**! :YESS:\n"
                                     f"Du erhältst **{bonus}** Währung als Belohnung!")
                except discord.Forbidden:
                    print(f"Could not send voice level up DM to {member.name} (DMs likely closed).")

@grant_voice_xp.before_loop
async def before_grant_voice_xp():
    """Ensures the bot is fully logged in before the task starts."""
    await client.wait_until_ready()

# --- NEW: Wrapped Event Management ---

def _calculate_wrapped_dates(config):
    """Helper function to calculate the dates for the next Wrapped event."""
    now = datetime.now(timezone.utc)
    
    # Calculate the first day of the *next* month for scheduling.
    first_day_of_current_month = now.replace(day=1)
    first_day_of_next_month = (first_day_of_current_month + timedelta(days=32)).replace(day=1)

    # Decide on a release date: a random day in the second week of the month.
    release_day = random.randint(config['modules']['wrapped']['release_day_min'], config['modules']['wrapped']['release_day_max'])
    release_date = first_day_of_next_month.replace(day=release_day, hour=18, minute=0, second=0) # 6 PM UTC

    # The day to create the event is one week before the release.
    event_creation_date = release_date - timedelta(days=7)
    event_name = f"Sulfur Wrapped {now.strftime('%B %Y')}"
    
    return {
        "event_name": event_name, "event_creation_date": event_creation_date, "release_date": release_date, "stat_period": now.strftime('%Y-%m')
    }

# --- NEW: Helper for Prime Time titles ---
def get_prime_time_title(hour):
    """Assigns a title based on the user's most active hour."""
    if hour is None:
        return "👻 Server-Geist"
    if 0 <= hour <= 5: return "🦉 Nachteule"
    if 6 <= hour <= 10: return "☀️ Früher Vogel"
    if 11 <= hour <= 13: return "🥪 Lunch-Lurker"
    if 14 <= hour <= 17: return "💼 Feierabend-Genießer"
    if 18 <= hour <= 21: return "🌙 Abend-Poster"
    if 22 <= hour <= 23: return "🦉 Nachteule"
    return "👻 Server-Geist"


@tasks.loop(hours=24)
async def manage_wrapped_event():
    """
    Manages the creation of the 'Wrapped' event and the distribution of stats.
    Runs once a day.
    """
    now = datetime.now(timezone.utc)
    # For simplicity, we'll use the first guild the bot is in.
    if not client.guilds:
        return
    
    # --- REFACTORED: Use helper to get dates ---
    dates = _calculate_wrapped_dates(config)
    event_name = dates["event_name"]
    event_creation_date = dates["event_creation_date"]
    release_date = dates["release_date"]
    
    # Check if an event for this period already exists
    # We check across all guilds the bot is in to avoid creating duplicates
    all_events = [e for guild in client.guilds for e in guild.scheduled_events]
    event_exists = any(event.name == event_name for event in all_events)

    # If it's the right day to create the event and it doesn't exist yet
    if now.day == event_creation_date.day and not event_exists:
        print(f"Creating Scheduled Event for '{event_name}'...")
        # --- FIX: Loop through all guilds to create the event ---
        for guild in client.guilds:
            try:
                await guild.create_scheduled_event(
                    name=event_name,
                    description=f"Dein persönlicher Server-Rückblick für **{now.strftime('%B')}**! Die Ergebnisse werden am Event-Tag per DM verschickt.",
                    start_time=release_date,
                    end_time=release_date + timedelta(hours=1),
                    entity_type=discord.EntityType.external,
                    location="In deinen DMs!",
                    privacy_level=discord.PrivacyLevel.guild_only,
                    reason="Automated monthly Wrapped event creation."
                )
                print(f"Event created successfully in '{guild.name}'.")
            except Exception as e:
                print(f"Failed to create scheduled event in '{guild.name}': {e}")

    # --- 2. Wrapped Distribution ---
    # Check if today is the release day for the PREVIOUS month's data.
    first_day_of_current_month = now.replace(day=1)
    last_month_first_day = (first_day_of_current_month - timedelta(days=1)).replace(day=1)
    # The release day is based on the *current* month's second week, but for *last* month's data.
    # --- FIX: To ensure consistency, we must recalculate the release date for the *previous* month's cycle. ---
    # We use the first day of the *current* month to determine the release window for *last* month's data.
    last_month_release_day = random.randint(config['modules']['wrapped']['release_day_min'], config['modules']['wrapped']['release_day_max'])
    last_month_release_date = first_day_of_current_month.replace(day=last_month_release_day, hour=18, minute=0, second=0)
    last_month_stat_period = last_month_first_day.strftime('%Y-%m')

    # --- FIX: Check the full date, not just the day number ---
    if now.year == last_month_release_date.year and now.month == last_month_release_date.month and now.day == last_month_release_date.day:
        print(f"Distributing Wrapped for period {last_month_stat_period}...")
        stats = await db_helpers.get_wrapped_stats_for_period(last_month_stat_period)

        # --- NEW: Pre-calculate ranks ---
        total_users = len(stats)
        if total_users == 0:
            print(f"No stats found for period {last_month_stat_period}. Skipping distribution.")
            return

        # Create sorted lists for ranking

        for user_stats in stats:
            await _generate_and_send_wrapped_for_user(
                user_stats=user_stats,
                stat_period_date=last_month_first_day,
                all_stats_for_period=stats,
                total_users=total_users,
                server_averages=await _calculate_server_averages(stats)
            )

async def _calculate_server_averages(all_stats):
    """Helper to calculate average stats for the server."""
    total_users = len(all_stats)
    if total_users == 0:
        return {'avg_messages': 0, 'avg_vc_minutes': 0}

    total_messages = sum(s.get('message_count', 0) for s in all_stats)
    total_vc_minutes = sum(s.get('minutes_in_vc', 0) for s in all_stats)

    return {
        'avg_messages': total_messages / total_users,
        'avg_vc_minutes': total_vc_minutes / total_users
    }

@manage_wrapped_event.before_loop
async def before_manage_wrapped_event():
    await client.wait_until_ready()

# --- REFACTORED: Multi-step view for sharing the Wrapped summary ---
class ShareView(discord.ui.View):
    def __init__(self, embed_to_share: discord.Embed, user: discord.User):
        super().__init__(timeout=180)
        self.embed_to_share = embed_to_share
        self.user = user
        self.selected_guild = None
        self.mutual_guilds = [g for g in user.mutual_guilds if g.get_member(client.user.id)]
        self.setup_view()

    def setup_view(self):
        """Dynamically sets up the view based on the current state (guild or channel selection)."""
        self.clear_items()
        if self.selected_guild:
            # Step 2: Show channel select for the chosen guild
            # --- REFACTORED: Use a regular Select to show only writable channels ---
            member = self.selected_guild.get_member(self.user.id)
            bot_member = self.selected_guild.me
            
            # Filter channels where both the user and the bot can send messages
            channel_options = []
            for channel in self.selected_guild.text_channels:
                if channel.permissions_for(member).send_messages and channel.permissions_for(bot_member).send_messages:
                    channel_options.append(discord.SelectOption(label=f"#{channel.name}", value=str(channel.id)))
            
            if channel_options:
                self.add_item(discord.ui.Select(
                    placeholder=f"Wähle einen Kanal in '{self.selected_guild.name}'...",
                    options=channel_options[:25], # Max 25 options per select menu
                    custom_id="share_channel_select"
                ))

        elif len(self.mutual_guilds) > 1:
            # Step 1: Show guild select
            options = [discord.SelectOption(label=g.name, value=str(g.id)) for g in self.mutual_guilds]
            self.add_item(discord.ui.Select(
                placeholder="Wähle einen Server zum Teilen...",
                options=options,
                custom_id="share_guild_select"
            ))
        elif len(self.mutual_guilds) == 1:
            # Skip Step 1 if only one mutual guild
            self.selected_guild = self.mutual_guilds[0]
            self.setup_view()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.data['custom_id'] == 'share_guild_select':
            guild_id = int(interaction.data['values'][0])
            self.selected_guild = client.get_guild(guild_id)
            self.setup_view()
            await interaction.response.edit_message(content="Wähle nun den Kanal:", view=self)
            return False # Stop further processing for this interaction

        if interaction.data['custom_id'] == 'share_channel_select':
            channel_id = int(interaction.data['values'][0])
            target_channel = self.selected_guild.get_channel(channel_id)
            if not target_channel or not target_channel.permissions_for(self.selected_guild.me).send_messages:
                await interaction.response.send_message("Ich kann in diesem Kanal nichts posten. Berechtigungen prüfen!", ephemeral=True)
                return False

            self.embed_to_share.title = f"{self.user.display_name}'s Wrapped"
            await target_channel.send(embed=self.embed_to_share)
            await interaction.response.edit_message(content=f"Seite wurde in {target_channel.mention} geteilt!", view=None)
            self.stop()
            return False
        return True

# --- NEW: View for paginating the Wrapped DM ---
class WrappedView(discord.ui.View):
    def __init__(self, pages: list, user: discord.User, timeout=300):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.user = user
        self.current_page = 0
        self.message = None

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page -= 1
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = False
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page += 1
        self.next_button.disabled = self.current_page == len(self.pages) - 1
        self.previous_button.disabled = False
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    @discord.ui.button(label="Teilen", style=discord.ButtonStyle.green, emoji="🔗")
    async def share_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Sends a message with a channel select menu to share the summary."""
        current_page_embed = self.pages[self.current_page]
        share_view = ShareView(current_page_embed, self.user)
        
        initial_content = "Wähle einen Server zum Teilen:"
        if len(share_view.mutual_guilds) <= 1:
            initial_content = "Wähle einen Kanal zum Teilen:"

        await interaction.response.send_message(
            initial_content,
            view=share_view,
            ephemeral=True
        )

    async def send_initial_message(self):
        """Sends the first page to the user's DMs."""
        self.previous_button.disabled = True
        self.next_button.disabled = len(self.pages) <= 1
        self.message = await self.user.send(embed=self.pages[0], view=self)

async def _generate_and_send_wrapped_for_user(user_stats, stat_period_date, all_stats_for_period, total_users, server_averages):
    """Helper function to generate and DM the Wrapped story to a single user."""
    user_id = user_stats['user_id']
    user = None
    try:
        # Use fetch_user to guarantee we can find the user, even if not cached.
        user = await client.fetch_user(int(user_id))
    except discord.NotFound:
        print(f"  - Skipping user ID {user_id}: User could not be found (account may be deleted).")
        return

    print(f"  - [Wrapped] Generating for {user.name} ({user.id})...")
    
    pages = [] # This will hold all the embed pages for the story
    color = get_embed_color(config)

    # Find favorite channel
    fav_channel_id = None
    if user_stats.get('channel_usage'):
        print("    - [Wrapped] Calculating favorite channel...")
        channel_usage = json.loads(user_stats['channel_usage'])
        if channel_usage:
            fav_channel_id = max(channel_usage, key=channel_usage.get)

    # --- NEW: Fetch all the new Wrapped stats in one go ---
    extra_stats = await get_wrapped_extra_stats(user.id, stat_period_date.strftime('%Y-%m'))

    # --- Page 1: Intro & Prime Time ---
    intro_embed = discord.Embed(
        title=f"Dein {stat_period_date.strftime('%B')} Wrapped ist da, {user.display_name}!",
        description="Bist du bereit, in deine Stats einzutauchen und zu sehen, ob du ein No-Lifer bist? Los geht's!",
        color=color
    )
    intro_embed.set_thumbnail(url=user.display_avatar.url)
    # Add Prime Time title to the intro page
    prime_time_title = get_prime_time_title(extra_stats.get('prime_time_hour'))
    intro_embed.add_field(name="Dein Titel diesen Monat", value=f"## {prime_time_title}", inline=False)
    intro_embed.set_footer(text="Basiert auf deiner aktivsten Zeit im Chat.")
    pages.append(intro_embed)

    # --- Page 2: Server Bestie ---
    bestie_embed = discord.Embed(title="Deine engsten Kontakte", color=color)
    bestie_id = extra_stats.get("server_bestie_id")
    if bestie_id:
        try:
            bestie_user = await client.fetch_user(int(bestie_id))
            bestie_embed.description = f"Diesen Monat warst du unzertrennlich mit...\n\n## {bestie_user.mention}"
            bestie_embed.set_thumbnail(url=bestie_user.display_avatar.url)
        except discord.NotFound:
            bestie_embed.description = await replace_emoji_tags("Dein Server-Bestie scheint ein Geist zu sein... oder hat den Server verlassen. :dono:", client)
    else:
        bestie_embed.description = await replace_emoji_tags("Du bist diesen Monat eher ein Einzelgänger gewesen und hast niemanden oft erwähnt oder auf ihn geantwortet. :gege:", client)
    bestie_embed.set_footer(text="Basiert darauf, wen du am häufigsten erwähnst oder wem du antwortest.")
    pages.append(bestie_embed)

    # --- Page 3: Message & Emoji Stats ---
    message_ranks = {user['user_id']: rank for rank, user in enumerate(sorted(all_stats_for_period, key=lambda x: x.get('message_count', 0), reverse=True))}
    message_rank_text = _get_percentile_rank(user.id, message_ranks, total_users)
    msg_embed = discord.Embed(title="Du und der Chat", color=color)
    msg_embed.add_field(name="Deine Nachrichten", value=f"## `{user_stats.get('message_count', 0)}`", inline=True)
    msg_embed.add_field(name="Server-Durchschnitt", value=f"## `{int(server_averages['avg_messages'])}`", inline=True)
    msg_embed.add_field(name="Dein Rang", value=f"Du gehörst zu den **{message_rank_text}** der aktivsten Chatter!", inline=False)

    # Add Top 3 Emojis to this page
    if user_stats.get('emoji_usage'):
        emoji_usage = json.loads(user_stats['emoji_usage'])
        sorted_emojis = sorted(emoji_usage.items(), key=lambda item: item[1], reverse=True)
        top_emojis_text = ""
        for i, (emoji_name, count) in enumerate(sorted_emojis[:3]):
            emoji_obj = discord.utils.get(client.emojis, name=emoji_name)
            emoji_display = str(emoji_obj) if emoji_obj else f"`:{emoji_name}:`"
            top_emojis_text += f"**{i+1}.** {emoji_display} (`{count}x`)\n"
        if top_emojis_text:
            msg_embed.add_field(name="Deine Lieblings-Emojis", value=top_emojis_text, inline=False)
    pages.append(msg_embed)

    # --- Page 4: Voice Channel Stats ---
    vc_ranks = {user['user_id']: rank for rank, user in enumerate(sorted(all_stats_for_period, key=lambda x: x.get('minutes_in_vc', 0), reverse=True))}
    vc_rank_text = _get_percentile_rank(user.id, vc_ranks, total_users)
    vc_hours = user_stats.get('minutes_in_vc', 0) / 60
    vc_embed = discord.Embed(title="Deine Voice-Chat Story", color=color)
    vc_embed.add_field(name="Deine VC-Stunden", value=f"## `{vc_hours:.2f}`", inline=True)
    vc_embed.add_field(name="Server-Durchschnitt", value=f"## `{server_averages['avg_vc_minutes'] / 60:.2f}`", inline=True)
    vc_embed.add_field(name="Dein Rang", value=f"Du warst in den **{vc_rank_text}** der größten Quasselstrippen!", inline=False)

    # Add new VC stats to this page
    longest_session_seconds = extra_stats.get("longest_vc_session_seconds", 0)
    longest_session_str = str(timedelta(seconds=longest_session_seconds)).split('.')[0] # Format as H:MM:SS
    vc_embed.add_field(name="Längste Session", value=f"`{longest_session_str}`", inline=True)
    vc_embed.add_field(name="Erstellte VCs", value=f"`{extra_stats.get('temp_vcs_created', 0)}`", inline=True)
    pages.append(vc_embed)

    # --- Page 5: Top Channel & Activity ---
    activity_embed = discord.Embed(title="Deine digitalen Hangouts", color=color)
    # Top Channel
    if user_stats.get('channel_usage'):
        channel_usage = json.loads(user_stats['channel_usage'])
        if channel_usage:
            fav_channel_id = max(channel_usage, key=channel_usage.get)
            fav_channel_obj = client.get_channel(int(fav_channel_id))
            activity_embed.add_field(name="Dein Lieblingskanal", value=f"Du hast die meiste Zeit in {fav_channel_obj.mention if fav_channel_obj else 'einem unbekannten Kanal'} verbracht.", inline=False)

    # Top Activity
    if user_stats.get('activity_usage'):
        activity_usage = json.loads(user_stats['activity_usage'])
        filtered_activities = {k: v for k, v in activity_usage.items() if k.lower() not in ['custom status', 'spotify']}
        if filtered_activities:
            fav_activity = max(filtered_activities, key=filtered_activities.get)
            activity_embed.add_field(name="Deine Top-Aktivität", value=f"Abgesehen von Discord warst du am häufigsten in **{fav_activity}** unterwegs.", inline=False)
    
    if activity_embed.fields: # Only add the page if it has content
        pages.append(activity_embed)

    # --- Page 6: Game Wrapped Page ---
    if user_stats.get('game_usage'):
        monthly_game_stats = json.loads(user_stats['game_usage'])
        if monthly_game_stats:
            # Find favorite game by total minutes this month
            fav_game_name = max(monthly_game_stats, key=lambda g: monthly_game_stats[g]['total_minutes'])
            fav_game_data = monthly_game_stats[fav_game_name]
            user_minutes = fav_game_data['total_minutes']

            # Calculate server average and leaderboard for this specific game
            other_players_minutes = []
            leaderboard_data = []
            for stats in all_stats_for_period:
                if stats.get('game_usage'):
                    period_game_stats = json.loads(stats['game_usage'])
                    if fav_game_name in period_game_stats:
                        player_minutes = period_game_stats[fav_game_name]['total_minutes']
                        other_players_minutes.append(player_minutes)
                        leaderboard_data.append({'user_id': stats['user_id'], 'minutes': player_minutes})
            
            server_avg_minutes = sum(other_players_minutes) / len(other_players_minutes) if other_players_minutes else 0
            
            # Build leaderboard
            leaderboard_data.sort(key=lambda x: x['minutes'], reverse=True)
            leaderboard_text = ""
            for i, data in enumerate(leaderboard_data[:3]): # Top 3
                player_user = client.get_user(data['user_id'])
                player_name = player_user.display_name if player_user else f"User {data['user_id']}"
                leaderboard_text += f"**{i+1}.** {player_name} - *{data['minutes']:.0f} Min.*\n"

            game_embed = discord.Embed(title=f"Dein Lieblingsspiel: {fav_game_name}", color=color)
            game_embed.add_field(name="Deine Spielzeit (diesen Monat)", value=f"## `{user_minutes:.0f}`\n*Minuten*", inline=True)
            game_embed.add_field(name="Server-Durchschnitt", value=f"## `{server_avg_minutes:.0f}`\n*Minuten*", inline=True)
            
            if leaderboard_text:
                game_embed.add_field(name=f"Leaderboard für {fav_game_name}", value=leaderboard_text, inline=False)
            
            game_embed.set_footer(text="Verglichen mit anderen Spielern dieses Spiels auf dem Server.")
            pages.append(game_embed)

    # --- Page 7: Spotify Wrapped Page ---
    if user_stats.get('spotify_minutes'):
        spotify_minutes_data = json.loads(user_stats['spotify_minutes'])
        if spotify_minutes_data: # Check if the JSON object is not empty
            total_minutes = sum(spotify_minutes_data.values())
            
            # Sort songs by listening time
            sorted_songs = sorted(spotify_minutes_data.items(), key=lambda item: item[1], reverse=True)
            
            top_songs_text = ""
            for i, (song, minutes) in enumerate(sorted_songs[:5]):
                top_songs_text += f"**{i+1}.** `{song}` - *{minutes:.0f} Minuten*\n"

            if top_songs_text:
                spotify_embed = discord.Embed(title="Dein Spotify-Rückblick", color=discord.Color.green())
                spotify_embed.add_field(name="Gesamte Hörzeit", value=f"Du hast diesen Monat insgesamt **{total_minutes:.0f} Minuten** Musik gehört.", inline=False)
                spotify_embed.add_field(name="Deine Top 5 Songs (nach Hörzeit)", value=top_songs_text, inline=False)
                spotify_embed.set_footer(text="Basiert auf der Zeit, die du Songs über Discord gehört hast.")
                pages.append(spotify_embed)

    # --- Final Page: Gemini Summary ---
    # --- REFACTORED: Conditionally build the stats dictionary for the AI ---
    gemini_stats = {
        "message_count": user_stats.get('message_count', 0), "avg_message_count": server_averages['avg_messages'],
        "vc_hours": vc_hours, "avg_vc_hours": server_averages['avg_vc_minutes'] / 60,
        "message_rank_text": message_rank_text, "vc_rank_text": vc_rank_text
    }
    # Add activity if it exists
    if 'activity_embed' in locals() and activity_embed.fields:
        field_value = activity_embed.fields[-1].value # Assumes activity is the last field
        match = re.search(r'\*\*(.*?)\*\*', field_value)
        if match:
            gemini_stats["fav_activity"] = match.group(1)
    # Add top game if it exists
    if 'fav_game_name' in locals():
        gemini_stats["top_game"] = fav_game_name
    # Add top song if it exists
    if 'sorted_songs' in locals() and sorted_songs:
        gemini_stats["top_song"] = sorted_songs[0][0]

    summary_text, _ = await get_wrapped_summary_from_api(user.display_name, gemini_stats, config, GEMINI_API_KEY, OPENAI_API_KEY)
    print(f"    - [Wrapped] Generated Gemini summary for {user.name}.")
    summary_embed = discord.Embed(title="Mein Urteil über dich", description=f"## _{await replace_emoji_tags(summary_text, client)}_", color=color)
    summary_embed.set_footer(text="Nächstes Mal gibst du dir mehr Mühe, ja? :erm:")
    pages.append(summary_embed)

    # --- FIX: Make exception handling more specific to DM failures ---
    # The API call now has its own robust error handling, so we only need to catch
    # errors related to sending the message to the user.
    view = WrappedView(pages, user)
    try:
        await view.send_initial_message()
        print(f"  - [Wrapped] Successfully sent DM to {user.name}.")
    except (discord.Forbidden, discord.HTTPException) as e:
        print(f"  - [Wrapped] FAILED to DM {user.name} (DMs likely closed or another Discord error occurred): {e}")

def _get_percentile_rank(user_id, rank_map, total_users):
    """Helper function to calculate a user's percentile rank from a sorted list."""
    if total_users < 2: return "Top 100%" # Avoid division by zero
    try:
        # The rank map gives us the 0-indexed rank directly
        user_rank = rank_map.get(user_id, total_users - 1)
        # --- FIX: Correctly calculate the percentile ---
        # This now represents the percentage of users you are ranked higher than.
        percentile = ((total_users - 1 - user_rank) / (total_users - 1)) * 100

        # --- NEW: Use ranks from config file ---
        ranks = config['modules']['wrapped']['percentile_ranks']
        # We sort the keys numerically to ensure correct order, ignoring 'default'.
        sorted_thresholds = sorted([int(k) for k in ranks.keys() if k.isdigit()])

        for threshold in sorted(ranks.keys(), key=lambda x: int(x) if x.isdigit() else 999, reverse=True):
            if threshold.isdigit() and percentile >= (100 - int(threshold)):
                return ranks[str(threshold)]
        
        return ranks.get("default", "N/A")
    except StopIteration:
        return "N/A"

@client.event
async def on_voice_state_update(member, before, after):
    """Handles players joining/leaving Werwolf lobby channels."""
    # --- NEW: Efficiently track users in voice channels for XP gain ---
    if not member.bot:
        # User is in a VC and not deafened -> add to XP list
        if after.channel and not after.deaf:
            active_vc_users[member.id] = member
        # User left VC or got deafened -> remove from XP list
        elif (not after.channel or after.deaf) and member.id in active_vc_users:
            del active_vc_users[member.id]
        
        # --- NEW: Track longest voice session ---
        now = discord.utils.utcnow()
        # User joins a VC
        if not before.channel and after.channel:
            vc_session_starts[member.id] = now
        # User leaves a VC
        elif before.channel and not after.channel:
            if member.id in vc_session_starts:
                start_time = vc_session_starts.pop(member.id)
                duration_seconds = (now - start_time).total_seconds()
                # Only log sessions longer than a minute
                if duration_seconds > 60:
                    await db_helpers.log_vc_session(member.id, member.guild.id, int(duration_seconds), now)



    # --- NEW: Handle "Join to Create" logic first, passing config ---
    await voice_manager.handle_voice_state_update(member, before, after, config)

    # Ignore bots
    if member.bot:
        return

    # --- Werwolf Game Logic ---

    # Find the game associated with the voice channel
    game = None
    vc_id = None
    if after.channel:
        vc_id = after.channel.id
    elif before.channel:
        vc_id = before.channel.id

    # --- FIX: Do not run Werwolf cleanup logic if the user is just moving between channels ---
    # The "Join to Create" feature moves users, which can trigger this incorrectly.
    # We only care about true disconnects (leaving all VCs).
    is_true_disconnect = before.channel and not after.channel

    # --- NEW: End game if VC becomes empty ---
    # A user truly disconnected from a channel (not just muted/deafened)
    if is_true_disconnect:
        # Check if the channel that became empty was a game channel
        for game_channel_id, game_instance in list(active_werwolf_games.items()):
            game_vc = game_instance.discussion_vc or game_instance.lobby_vc
            if not game_vc: continue # Skip if the game has no VC
            # Check if the channel matches and is now empty of human players
            human_members = [m for m in game_vc.members if not m.bot] if game_vc else []
            if game_vc and game_vc.id == before.channel.id and not human_members:
                # --- FIX: Check if channel exists before sending message ---
                if game_instance.game_channel and client.get_channel(game_instance.game_channel.id):
                    try:
                        await game_instance.game_channel.send("Alle Spieler haben den Voice-Channel verlassen. Das Spiel wird beendet.")
                    except discord.NotFound:
                        pass # Channel was deleted in the meantime
                await game_instance.end_game(None)
                del active_werwolf_games[game_channel_id]

    for g in active_werwolf_games.values():
        if g.lobby_vc and g.lobby_vc.id == vc_id:
            game = g
            break
    
    if not game:
        return

    # Player joins the lobby
    if game.phase == "joining" and game.join_message:
        player_joined = after.channel == game.lobby_vc and before.channel != game.lobby_vc
        player_left = before.channel == game.lobby_vc and after.channel != game.lobby_vc

        if player_joined:
            game.add_player(member)
        elif player_left:
            game.remove_player(member)

        if player_joined or player_left:
            try:
                # --- NEW: Update the join embed instead of sending new messages ---
                original_embed = game.join_message.embeds[0]
                player_list = game.get_player_list()
                field_value = "\n".join(player_list) if player_list else "Noch keine Spieler."
                
                # Find and update the 'Spieler' field, or add it if it doesn't exist.
                original_embed.set_field_at(1, name=f"Spieler ({len(player_list)})", value=field_value, inline=False)
                
                await game.join_message.edit(embed=original_embed)
            except (discord.NotFound, IndexError, AttributeError):
                pass # Ignore if message is gone or embed is malformed

# --- NEW: WERWOLF SLASH COMMANDS ---

# Create a command group for Werwolf. This allows us to add/remove all ww commands at once.
ww_group = app_commands.Group(name="ww", description="Startet und steuert ein Werwolf-Spiel.")

# --- NEW: Add the ww_group to the main tree so it's always available ---
tree.add_command(ww_group)

# --- NEW: Voice Channel Commands ---
voice_group = app_commands.Group(
    name="voice",
    description="Befehle zur Verwaltung von Sprachkanälen."
)

# --- NEW: Custom check for admin commands ---
def is_admin_or_authorised(interaction: discord.Interaction) -> bool:
    """Checks if the user is an admin or has the 'authorised' role."""
    if interaction.user.guild_permissions.administrator:
        return True
    authorised_role = discord.utils.get(interaction.user.roles, name=config['bot']['authorised_role'])
    return authorised_role is not None

@voice_group.command(name="setup", description="Richtet das 'Beitreten zum Erstellen'-Feature für Sprachkanäle ein.")
@app_commands.default_permissions(administrator=True)
@app_commands.check(is_admin_or_authorised)
async def voice_setup(interaction: discord.Interaction):
    """Sets up the 'Join to Create' voice channel."""
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    # Check if the channel already exists
    existing_channel = discord.utils.get(guild.voice_channels, name=config['modules']['voice_manager']['join_to_create_channel_name'])
    if existing_channel:
        await interaction.followup.send(f"The 'Join to Create' feature is already set up in {existing_channel.mention}!")
        return

    try:
        # Find or create a category for dynamic channels
        category_name = config['modules']['voice_manager']['dynamic_channel_category_name']
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            category = await guild.create_category(category_name, reason="Setup for dynamic voice channels")

        # Create the 'Join to Create' channel
        join_channel = await guild.create_voice_channel(name=config['modules']['voice_manager']['join_to_create_channel_name'], category=category, reason="Bot setup for 'Join to Create' feature")
        await interaction.followup.send(f"Successfully set up the 'Join to Create' feature! Users can now join {join_channel.mention} to create their own voice channels.")
    except discord.Forbidden:
        await interaction.followup.send("Error: The bot lacks the necessary permissions (Manage Channels) to perform this setup.")

@voice_group.command(name="clearall", description="[Admin-Gefahr!] Löscht ALLE Sprachkanäle auf dem Server.")
@app_commands.default_permissions(administrator=True)
@app_commands.check(is_admin_or_authorised)
async def voice_clearall(interaction: discord.Interaction):
    """Deletes ALL voice channels on the server, regardless of DB state."""
    await interaction.response.defer(ephemeral=True)
    
    guild = interaction.guild
    voice_channels_to_delete = guild.voice_channels
    if not voice_channels_to_delete:
        await interaction.followup.send("Keine Sprachkanäle zum Löschen gefunden.")
        return

    deleted_count = 0
    for channel in voice_channels_to_delete:
        try:
            await channel.delete(reason="Admin Massenlöschung")
            deleted_count += 1
        except Exception as e:
            print(f"Konnte Channel {channel.name} nicht löschen: {e}")
    
    await interaction.followup.send(f"{deleted_count} Sprachkanäle wurden erfolgreich gelöscht.")

# --- NEW: Voice Channel Config Commands ---
config_group = app_commands.Group(name="config", parent=voice_group, description="Konfiguriere deinen persönlichen Sprachkanal.")

async def check_channel_owner(interaction: discord.Interaction) -> bool:
    """A check to ensure the user is in their own managed channel."""
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("Du musst in einem Voice Channel sein, um diesen Befehl zu nutzen.", ephemeral=True)
        return False

    vc_id = interaction.user.voice.channel.id
    channel_config = await db_helpers.get_managed_channel_config(vc_id)
    if not channel_config:
        await interaction.response.send_message("Dieser Befehl funktioniert nur in einem dynamisch erstellten Voice Channel.", ephemeral=True)
        return False

    if channel_config['owner_id'] != interaction.user.id:
        await interaction.response.send_message("Nur der Besitzer des Channels kann diesen Befehl verwenden.", ephemeral=True)
        return False

    return channel_config # Return the config to avoid fetching it again

@config_group.command(name="name", description="Benennt deinen Voice Channel um.")
@app_commands.describe(new_name="Der neue Name für deinen Channel.")
async def voice_config_name(interaction: discord.Interaction, new_name: str):
    if not await check_channel_owner(interaction): return
    await interaction.response.defer(ephemeral=True)
    try:
        await interaction.user.voice.channel.edit(name=new_name, reason=f"Owner changed name.")
        await interaction.followup.send(f"Channel-Name wurde zu '{new_name}' geändert.")
    except Exception as e:
        await interaction.followup.send(f"Fehler beim Umbenennen des Channels: {e}")

@config_group.command(name="limit", description="Setzt ein Benutzerlimit für deinen Channel.")
@app_commands.describe(limit="Die maximale Anzahl an Benutzern (0 für unbegrenzt).")
async def voice_config_limit(interaction: discord.Interaction, limit: app_commands.Range[int, 0, 99]):
    if not (await check_channel_owner(interaction)): return
    await interaction.response.defer(ephemeral=True)
    try:
        await interaction.user.voice.channel.edit(user_limit=limit, reason=f"Owner set limit.")
        await interaction.followup.send(f"Benutzerlimit wurde auf {limit if limit > 0 else 'unbegrenzt'} gesetzt.")
    except Exception as e:
        await interaction.followup.send(f"Fehler beim Setzen des Limits: {e}")

@config_group.command(name="lock", description="Macht deinen Channel privat.")
async def voice_config_lock(interaction: discord.Interaction):
    channel_config = await check_channel_owner(interaction)
    if not channel_config: return
    await interaction.response.defer(ephemeral=True)
    vc_id = interaction.user.voice.channel.id
    allowed_users = set(channel_config.get('allowed_users', [channel_config['owner_id']]))
    await db_helpers.update_managed_channel_config(vc_id, is_private=True, allowed_users=allowed_users)
    await interaction.followup.send("Dein Channel ist jetzt privat. Nur eingeladene Benutzer können beitreten. Benutze `/voice config permit`, um jemanden einzuladen.")

@config_group.command(name="unlock", description="Macht deinen Channel wieder öffentlich.")
async def voice_config_unlock(interaction: discord.Interaction):
    channel_config = await check_channel_owner(interaction)
    if not channel_config: return
    await interaction.response.defer(ephemeral=True)
    vc_id = interaction.user.voice.channel.id
    allowed_users = set(channel_config.get('allowed_users', [channel_config['owner_id']]))
    await db_helpers.update_managed_channel_config(vc_id, is_private=False, allowed_users=allowed_users)
    await interaction.followup.send("Dein Channel ist jetzt wieder öffentlich.")

@config_group.command(name="permit", description="Erlaubt einem Benutzer, deinem privaten Channel beizutreten.")
@app_commands.describe(user="Der Benutzer, dem du den Zutritt erlauben möchtest.")
async def voice_config_permit(interaction: discord.Interaction, user: discord.Member):
    channel_config = await check_channel_owner(interaction)
    if not channel_config: return
    await interaction.response.defer(ephemeral=True)
    vc_id = interaction.user.voice.channel.id

    if not channel_config['is_private']:
        await interaction.followup.send("Dieser Befehl funktioniert nur, wenn dein Channel privat ist. Benutze zuerst `/voice config lock`.")
        return

    allowed_users = set(channel_config.get('allowed_users', [channel_config['owner_id']]))
    if user.id in allowed_users:
        await interaction.followup.send(f"{user.display_name} hat bereits Zutritt.")
        return

    allowed_users.add(user.id)
    await db_helpers.update_managed_channel_config(vc_id, is_private=True, allowed_users=allowed_users)
    await interaction.followup.send(f"{user.display_name} kann deinem Channel jetzt beitreten.")

@config_group.command(name="unpermit", description="Entfernt die Zutrittserlaubnis für einen Benutzer.")
@app_commands.describe(user="Der Benutzer, dem du den Zutritt entziehen möchtest.")
async def voice_config_unpermit(interaction: discord.Interaction, user: discord.Member):
    channel_config = await check_channel_owner(interaction)
    if not channel_config: return
    await interaction.response.defer(ephemeral=True)
    vc_id = interaction.user.voice.channel.id
    owner_id = channel_config['owner_id']

    if user.id == owner_id:
        await interaction.followup.send("Du kannst dir nicht selbst den Zutritt entziehen.")
        return

    allowed_users = set(channel_config.get('allowed_users', [owner_id]))
    if user.id not in allowed_users:
        await interaction.followup.send(f"{user.display_name} hatte keinen Zutritt zu deinem Channel.")
        return

    allowed_users.remove(user.id)
    await db_helpers.update_managed_channel_config(vc_id, is_private=channel_config['is_private'], allowed_users=allowed_users)
    await interaction.followup.send(f"{user.display_name} wurde der Zutritt entzogen.")

    # Kick the user if they are currently in the channel
    if user.voice and user.voice.channel.id == vc_id:
        try:
            await user.move_to(None, reason="Permission removed by owner")
        except Exception as e:
            print(f"Could not kick user after unpermit: {e}")

# --- NEW: Custom check for admin commands ---
def is_admin_or_authorised(interaction: discord.Interaction) -> bool:
    """Checks if the user is an admin or has the 'authorised' role."""
    if interaction.user.guild_permissions.administrator:
        return True
    authorised_role = discord.utils.get(interaction.user.roles, name=config['bot']['authorised_role'])
    return authorised_role is not None

# --- REFACTORED: Admin Commands using a class-based approach ---
@app_commands.check(is_admin_or_authorised)
class AdminGroup(app_commands.Group):
    """Admin-Befehle zur Verwaltung des Bots."""

    @app_commands.command(name="view_wrapped", description="Zeigt eine Vorschau des 'Wrapped' für einen Benutzer an.")
    @app_commands.describe(user="Der Benutzer, dessen Wrapped du ansehen möchtest.")
    async def view_wrapped(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(ephemeral=True)
        
        # For the admin preview, we generate the Wrapped for the CURRENT month
        now = datetime.now(timezone.utc)
        stat_period = now.strftime('%Y-%m')
        
        # We need all stats for the period to calculate ranks
        all_stats = await db_helpers.get_wrapped_stats_for_period(stat_period)
        if not all_stats:
            await interaction.followup.send(f"Keine 'Wrapped'-Daten für den Zeitraum `{stat_period}` gefunden.", ephemeral=True)
            return
            
        # Find the target user's stats
        target_user_stats = next((s for s in all_stats if s['user_id'] == user.id), None)
        if not target_user_stats:
            await interaction.followup.send(f"Keine 'Wrapped'-Daten für {user.display_name} im Zeitraum `{stat_period}` gefunden.", ephemeral=True)
            return

        # --- FIX: Pass the correct arguments to the helper function ---
        # The helper function now calculates ranks internally.
        await _generate_and_send_wrapped_for_user(
            user_stats=target_user_stats,
            stat_period_date=now,
            all_stats_for_period=all_stats,
            total_users=len(all_stats),
            server_averages=await _calculate_server_averages(all_stats)
        )

        await interaction.followup.send(f"Eine 'Wrapped'-Vorschau für den aktuellen Monat wurde an {user.mention} gesendet.", ephemeral=True)

    @app_commands.command(name="reload_config", description="Lädt die config.json und die System-Prompt-Datei neu.")
    async def reload_config(self, interaction: discord.Interaction):
        """Hot-reloads the configuration files."""
        await interaction.response.defer(ephemeral=True)
        print("--- Admin triggered config reload ---")
        global config
        try:
            new_config = load_config()
            config = new_config
            # Restart presence task to apply new interval immediately
            update_presence_task.restart()
            await interaction.followup.send("✅ Konfiguration wurde erfolgreich neu geladen.")
        except Exception as e:
            await interaction.followup.send(f"❌ Fehler beim Neuladen der Konfiguration: `{e}`")

    @app_commands.command(name="view_dates", description="Zeigt die berechneten Daten für das nächste 'Wrapped'-Event an.")
    async def view_dates(self, interaction: discord.Interaction):
        """Displays the calculated dates for the next Wrapped event."""
        await interaction.response.defer(ephemeral=True)
        
        dates = _calculate_wrapped_dates(config)
        
        embed = discord.Embed(
            title="📅 Nächster Wrapped-Zeitplan",
            description="Dies sind die berechneten Daten für die nächste 'Wrapped'-Runde.",
            color=get_embed_color(config)
        )
        embed.add_field(name="Statistik-Zeitraum", value=f"`{dates['stat_period']}`", inline=False)
        embed.add_field(name="Event-Erstellung am", value=f"<t:{int(dates['event_creation_date'].timestamp())}:F>", inline=False)
        embed.add_field(name="Veröffentlichung der DMs am", value=f"<t:{int(dates['release_date'].timestamp())}:F>", inline=False)
        
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="view_event", description="Erstellt ein Test-Event, um das Aussehen des 'Wrapped'-Events zu prüfen.")
    async def view_event(self, interaction: discord.Interaction):
        """Creates a mock scheduled event in the current server to preview its appearance."""
        await interaction.response.defer(ephemeral=True)
        dates = _calculate_wrapped_dates(config)
        try:
            await interaction.guild.create_scheduled_event(
                name=f"[TEST] {dates['event_name']}",
                description=f"Dein persönlicher Server-Rückblick für **{datetime.now(timezone.utc).strftime('%B')}**! Die Ergebnisse werden am Event-Tag per DM verschickt.",
                start_time=dates['release_date'],
                end_time=dates['release_date'] + timedelta(hours=1),
                entity_type=discord.EntityType.external,
                location="In deinen DMs!",
                privacy_level=discord.PrivacyLevel.guild_only
            )
            await interaction.followup.send("✅ Test-Event wurde erfolgreich in diesem Server erstellt.")
        except Exception as e:
            await interaction.followup.send(f"❌ Fehler beim Erstellen des Test-Events: `{e}`")

    @app_commands.command(name="save_history", description="Speichert den Chatverlauf dieses Kanals manuell in der Datenbank.")
    @app_commands.describe(limit="Die Anzahl der zu speichernden Nachrichten (Standard: 100).")
    async def save_history(self, interaction: discord.Interaction, limit: int = 100):
        """Fetches and saves a channel's message history to the database."""
        await interaction.response.defer(ephemeral=True)

        messages_to_save = []
        try:
            # Fetch messages from the channel history
            async for message in interaction.channel.history(limit=limit):
                # Ignore messages from bots unless it's our own bot
                if message.author.bot and message.author.id != client.user.id:
                    continue

                # --- NEW: Filter out non-conversational messages ---
                # Ignore slash commands
                if message.content.startswith('/'):
                    continue
                # Ignore messages with embeds, as they are usually game/bot notifications
                if message.embeds:
                    continue

                role = "model" if message.author.id == client.user.id else "user"
                content = message.content
                if role == "user":
                    content = f"User '{message.author.display_name}' said: {message.content}"

                messages_to_save.append({'role': role, 'content': content})

            # Reverse the list so they are in chronological order for saving
            messages_to_save.reverse()
            await db_helpers.save_bulk_history(interaction.channel.id, messages_to_save)
            await interaction.followup.send(f"Successfully processed and saved {len(messages_to_save)} messages from this channel's history.")
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {e}")

    @app_commands.command(name="clear_history", description="Löscht den gesamten gespeicherten Chatverlauf für diesen Kanal.")
    async def clear_history(self, interaction: discord.Interaction):
        """Deletes all chat history for the current channel from the database."""
        await interaction.response.defer(ephemeral=True)
        deleted_count, error = await db_helpers.clear_channel_history(interaction.channel.id)
        if error:
            await interaction.followup.send(f"An error occurred: {error}")
        else:
            await interaction.followup.send(f"Successfully deleted {deleted_count} messages from this channel's history.")

    @app_commands.command(name="ai_dashboard", description="Zeigt den aktuellen Status und die Nutzung der KI-API an.")
    async def ai_dashboard(self, interaction: discord.Interaction):
        """Displays the current AI provider status and Gemini usage."""
        await interaction.response.defer(ephemeral=True)

        # Determine the current provider
        current_provider = await get_current_provider(config)
        
        # Get Gemini usage from the database
        gemini_usage = await db_helpers.get_gemini_usage()

        # Create the progress bar
        progress = int((gemini_usage / GEMINI_DAILY_LIMIT) * 20) # 20 characters for the bar
        progress_bar = '█' * progress + '░' * (20 - progress)

        # Determine status and color
        if current_provider == 'gemini':
            model_in_use = config['api']['gemini']['model']
            status_text = "Aktiv"
            embed_color = discord.Color.green()
        else:
            model_in_use = config['api']['openai']['chat_model']
            # Check if this is a fallback or the primary choice
            if config['api']['provider'] == 'gemini':
                status_text = "Fallback (Limit erreicht)"
            else:
                status_text = "Aktiv"
            embed_color = discord.Color.red()

        embed = discord.Embed(
            title="🤖 AI API Dashboard",
            description="Status des aktuell genutzten Sprachmodells.",
            color=get_embed_color(config)
        )
        embed.add_field(name="Aktiver Provider", value=f"**`{current_provider.capitalize()}`**", inline=False)
        embed.add_field(name="Aktives Modell", value=f"`{model_in_use}`", inline=True)
        embed.add_field(name="Provider-Status", value=status_text, inline=True)
        embed.add_field(name=f"Gemini-Nutzung (Heute)", value=f"`{gemini_usage} / {GEMINI_DAILY_LIMIT}` Aufrufe\n`{progress_bar}`", inline=False)
        embed.set_footer(text="Der Zähler wird täglich um 00:00 UTC zurückgesetzt.")
        
        # --- NEW: Add a view with a model selector ---
        view = AIDashboardView()
        await interaction.followup.send(embed=embed, view=view)

    @app_commands.command(name="status", description="Zeigt den Uptime- und Versionsstatus des Bots an.")
    async def status(self, interaction: discord.Interaction):
        """Displays bot uptime, version, and update status."""
        await interaction.response.defer(ephemeral=True)

        # 1. Uptime
        uptime_delta = datetime.now(timezone.utc) - BOT_START_TIME
        days, remainder = divmod(uptime_delta.total_seconds(), 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s"

        # 2. Git Commit Hash
        try:
            commit_hash = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode('utf-8').strip()
            version_str = f"`{commit_hash}`"
        except (subprocess.CalledProcessError, FileNotFoundError):
            version_str = "N/A (Git nicht gefunden)"

        # 3. Last Update Time
        try:
            with open("last_update.txt", "r") as f:
                last_update_iso = f.read().strip()
                last_update_dt = datetime.fromisoformat(last_update_iso)
                last_update_str = f"<t:{int(last_update_dt.timestamp())}:R>"
        except (FileNotFoundError, ValueError):
            last_update_str = "Noch nie"

        # 4. Last Update Check Time
        try:
            with open("last_check.txt", "r") as f:
                last_check_iso = f.read().strip()
                last_check_dt = datetime.fromisoformat(last_check_iso)
                last_check_str = f"<t:{int(last_check_dt.timestamp())}:R>"
        except (FileNotFoundError, ValueError):
            last_check_str = "Noch nie"

        embed = discord.Embed(
            title="⚙️ Bot Status",
            color=get_embed_color(config)
        )
        embed.add_field(name="Uptime", value=uptime_str, inline=True)
        embed.add_field(name="Aktuelle Version", value=version_str, inline=True)
        embed.add_field(
            name="Update-Informationen",
            value=(
                f"**Letztes Update:** {last_update_str}\n"
                f"**Letzter Check:** {last_check_str}"
            ),
            inline=False
        )
        embed.set_footer(text=f"Gestartet am: {BOT_START_TIME.strftime('%Y-%m-%d %H:%M:%S UTC')}")

        await interaction.followup.send(embed=embed)


# --- NEW: View for the AI Dashboard ---
class AIDashboardView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # Persistent view

    async def _update_dashboard(self, interaction: discord.Interaction):
        """Helper function to regenerate and edit the dashboard message."""
        # This is a simplified version of the ai_dashboard command's logic
        # It's necessary to regenerate the embed after a change.
        # We create a temporary AdminGroup instance to call the method.
        temp_admin_group = AdminGroup()
        await temp_admin_group.ai_dashboard(interaction)

    @discord.ui.select(
        placeholder="Wähle ein neues KI-Modell...",
        options=[
            discord.SelectOption(label="Gemini 2.5 Flash (Schnell & Modern)", value="gemini:gemini-2.5-flash", emoji="⚡"),
            discord.SelectOption(label="Gemini 1.0 Pro (Stabil)", value="gemini:gemini-1.0-pro", emoji="💎"),
            discord.SelectOption(label="OpenAI GPT-4o Mini (Schnell)", value="openai:gpt-4o-mini", emoji="🚀"),
            discord.SelectOption(label="OpenAI GPT-4o (Leistungsstark)", value="openai:gpt-4o", emoji="🧠"),
        ]
    )
    async def model_select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Handles the model selection."""
        # Defer the response to prevent "interaction failed"
        await interaction.response.defer()

        global config
        provider, model_name = select.values[0].split(':')

        if provider == 'gemini':
            config['api']['gemini']['model'] = model_name
            config['api']['provider'] = 'gemini' # Switch active provider to Gemini
        elif provider == 'openai':
            config['api']['openai']['chat_model'] = model_name
            config['api']['provider'] = 'openai' # Switch active provider to OpenAI

        # Save the changes to the config.json file
        save_config(config)
        
        # Reload the config in memory to be safe
        config = load_config()

        # Create a new embed with the updated info and edit the original message
        # We can reuse the logic from the ai_dashboard command itself.
        # To do this, we create a temporary instance of the AdminGroup and call the method.
        # This is a bit of a workaround but keeps the embed logic in one place.
        temp_admin_group = AdminGroup()
        # We need to "re-call" the command logic to generate the new embed.
        # The original interaction object is used to edit the existing message.
        await temp_admin_group.ai_dashboard(interaction)

@tree.command(name="summary", description="Zeigt Sulfurs Meinung über einen Benutzer an.")
@app_commands.describe(user="Der Benutzer, dessen Zusammenfassung du sehen möchtest (optional).")
async def summary(interaction: discord.Interaction, user: discord.Member = None):
    """Displays the bot's relationship summary for a user."""
    target_user = user or interaction.user
    await interaction.response.defer(ephemeral=True)

    summary_text = await db_helpers.get_relationship_summary(target_user.id)

    if not summary_text:
        await interaction.followup.send(f"Ich hab mir über {target_user.display_name} noch keine richtige Meinung gebildet. Wir sollten mehr quatschen.")
        return

    embed = discord.Embed(
        title=f"Meine Meinung zu {target_user.display_name}", 
        description=f"_{summary_text}_",
        color=get_embed_color(config)
    )
    await interaction.followup.send(embed=embed)

@tree.command(name="rank", description="Überprüfe deinen oder den Rang eines anderen Benutzers.")
@app_commands.describe(user="Der Benutzer, dessen Rang du sehen möchtest (optional).")
async def rank(interaction: discord.Interaction, user: discord.Member = None):
    """Displays the level and rank of a user."""
    target_user = user or interaction.user
    await interaction.response.defer()

    player_stats, error = await db_helpers.get_player_rank(target_user.id)

    if error:
        await interaction.followup.send(error, ephemeral=True)
        return

    if not player_stats:
        await interaction.followup.send(f"{target_user.display_name} hat noch keine Nachrichten geschrieben und daher keinen Rang.", ephemeral=True)
        return

    level = player_stats['level'] or 1
    xp = player_stats['xp']
    rank = player_stats['rank']
    xp_for_next_level = get_xp_for_level(level)
    wins = player_stats.get('wins', 0)
    losses = player_stats.get('losses', 0)
    
    # Create a progress bar
    progress = int((xp / xp_for_next_level) * 20) # 20 characters for the bar
    progress_bar = '█' * progress + '░' * (20 - progress)

    embed = discord.Embed(color=get_embed_color(config))
    embed.set_author(name=f"Rang von {target_user.display_name}", icon_url=target_user.display_avatar.url) 
    embed.add_field(name="Level", value=f"```{level}```", inline=True) 
    embed.add_field(name="Global Rang", value=f"```#{rank}```", inline=True) 
    embed.add_field(name="Fortschritt", value=f"`{xp} / {xp_for_next_level} XP`\n`{progress_bar}`", inline=False) 

    await interaction.followup.send(embed=embed)

@tree.command(name="profile", description="Zeigt dein Profil oder das eines anderen Benutzers an.")
@app_commands.describe(user="Der Benutzer, dessen Profil du sehen möchtest (optional).")
async def profile(interaction: discord.Interaction, user: discord.Member = None):
    """Displays a user's profile with various stats."""
    target_user = user or interaction.user
    await interaction.response.defer(ephemeral=False) # Use ephemeral=False if the response should be public

    profile_data, error = await db_helpers.get_player_profile(target_user.id)

    if error:
        await interaction.followup.send(error, ephemeral=True)
        return

    if not profile_data:
        await interaction.followup.send(f"{target_user.display_name} hat noch keine Aktivitäten gezeigt und daher kein Profil.", ephemeral=True)
        return

    embed = discord.Embed(
        title=f"Profil von {target_user.display_name}",
        color=get_embed_color(config)
    )
    embed.set_thumbnail(url=target_user.display_avatar.url)

    # Leveling and Economy
    embed.add_field(name="Level", value=f"**{profile_data.get('level', 1)}**", inline=True)
    embed.add_field(name="Guthaben", value=f"**{profile_data.get('balance', 0)}** 🪙", inline=True)
    embed.add_field(name="Globaler Rang", value=f"**#{profile_data.get('rank', 'N/A')}**", inline=True)

    # Werwolf Stats
    wins = profile_data.get('wins', 0)
    losses = profile_data.get('losses', 0)
    total_games = wins + losses
    win_rate = (wins / total_games * 100) if total_games > 0 else 0
    embed.add_field(
        name="🐺 Werwolf Stats",
        value=f"Siege: `{wins}`\nNiederlagen: `{losses}`\nWin-Rate: `{win_rate:.1f}%`",
        inline=False
    )

    # Placeholder for items
    embed.add_field(name="🎒 Inventar", value="*Keine Items im Inventar.*", inline=False)

    await interaction.followup.send(embed=embed)

@tree.command(name="leaderboard", description="Zeigt das globale Level-Leaderboard an.")
async def leaderboard(interaction: discord.Interaction):
    """Displays the global level leaderboard."""
    await interaction.response.defer()

    leaderboard_data, error = await db_helpers.get_level_leaderboard()

    if error:
        await interaction.followup.send(error, ephemeral=True)
        return

    if not leaderboard_data:
        await interaction.followup.send("Noch niemand hat XP gesammelt. Schreibt ein paar Nachrichten!", ephemeral=True)
        return

    embed = discord.Embed(title="🏆 Globales Leaderboard 🏆", description="Die aktivsten Mitglieder", color=get_embed_color(config))
    
    leaderboard_text = ""
    for i, player in enumerate(leaderboard_data):
        leaderboard_text += f"**{i + 1}. {player['display_name']}** - Level {player['level']} ({player['xp']} XP)\n"

    embed.add_field(name="Top 10", value=leaderboard_text, inline=False)
    await interaction.followup.send(embed=embed)

@tree.command(name="spotify", description="Zeigt deine Spotify-Statistiken an.")
@app_commands.describe(user="Der Benutzer, dessen Statistiken du sehen möchtest (optional).")
async def spotify_stats(interaction: discord.Interaction, user: discord.Member = None):
    """Displays a user's Spotify listening stats."""
    target_user = user or interaction.user
    print(f"--- /spotify command triggered for {target_user.display_name} (ID: {target_user.id}) ---")
    await interaction.response.defer()

    # --- FIX: The spotify history is in the 'players' table, not user_monthly_stats ---
    history = await db_helpers.get_spotify_history(target_user.id)
    print(f"  -> Fetched history from DB: {history}")

    if not history:
        print("  -> No history found, sending 'cringe' message.")
        await interaction.followup.send(f"{target_user.display_name} hat noch keine Spotify-Daten oder hört keine Musik. Cringe.", ephemeral=True)
        return

    # --- NEW: Get total listening time for the month ---
    stat_period = datetime.now(timezone.utc).strftime('%Y-%m')
    user_stats = await db_helpers.get_user_wrapped_stats(target_user.id, stat_period)
    total_minutes = 0

    # Calculate top songs and artists
    from collections import Counter
    song_counts = Counter(history)
    artist_counts = Counter()

    embed = discord.Embed(
        title=f"Spotify Stats für {target_user.display_name}",
        color=discord.Color.green()
    )
    embed.set_thumbnail(url=target_user.display_avatar.url)

    # Current song
    current_spotify = next((activity for activity in target_user.activities if isinstance(activity, discord.Spotify)), None)
    if current_spotify:
        # --- NEW: Add album art ---
        if current_spotify.album_cover_url:
            embed.set_thumbnail(url=current_spotify.album_cover_url)
        else:
            embed.set_thumbnail(url=target_user.display_avatar.url)

        embed.add_field(
            name="🎶 Aktueller Song",
            value=f"**{current_spotify.title}**\nvon {current_spotify.artist}",
            inline=False
        )

    # Top 5 Songs
    top_songs_text = ""
    # --- FIX: Update to work with new {song: count} data structure ---
    for i, (song_key, count) in enumerate(song_counts.most_common(5)):
        top_songs_text += f"**{i+1}.** {song_key} (`{count}x`)\n"
        # Also populate artist_counts from the song key
        try:
            artist = song_key.split(' by ')[1]
            artist_counts[artist] += count
        except IndexError:
            pass # Ignore if the key is malformed
    if top_songs_text:
        embed.add_field(name="Top 5 Songs (All-Time)", value=top_songs_text, inline=False)

    # Top 5 Artists
    top_artists_text = ""
    if top_artists_text:
        embed.add_field(name="Top 5 Künstler (letzte 10)", value=top_artists_text, inline=False)

    # --- NEW: Add total listening time ---
    if user_stats and user_stats.get('spotify_minutes'):
        spotify_minutes_data = json.loads(user_stats['spotify_minutes'])
        total_minutes = sum(spotify_minutes_data.values())
        embed.add_field(name="Hörzeit diesen Monat", value=f"Du hast diesen Monat insgesamt **{total_minutes:.0f} Minuten** Musik gehört.", inline=False)


    # Footer
    embed.set_footer(text=f"Insgesamt {len(song_counts)} einzigartige Songs getrackt.")

    await interaction.followup.send(embed=embed)





@tree.command(name="stats", description="Zeigt die Werwolf-Statistiken und das Leaderboard an.")
async def stats(interaction: discord.Interaction):
    """Displays the Werwolf leaderboard."""
    await interaction.response.defer()

    leaderboard, error = await db_helpers.get_leaderboard()

    if error:
        await interaction.followup.send(error, ephemeral=True)
        return

    if not leaderboard:
        await interaction.followup.send("Es gibt noch keine Statistiken. Spielt erst mal eine Runde!", ephemeral=True)
        return

    embed = discord.Embed(title="🐺 Werwolf Leaderboard 🐺", description="Die Top-Spieler mit den meisten Siegen.", color=get_embed_color(config))

    leaderboard_text = ""
    for i, player in enumerate(leaderboard):
        rank = i + 1
        win_loss_ratio = player['wins'] / (player['wins'] + player['losses']) if (player['wins'] + player['losses']) > 0 else 0
        leaderboard_text += f"**{rank}. {player['display_name']}**\n"
        leaderboard_text += f"   Wins: `{player['wins']}` | Losses: `{player['losses']}` | W/L Ratio: `{win_loss_ratio:.2f}`\n"

    embed.add_field(name="Rangliste", value=leaderboard_text, inline=False)
    embed.set_footer(text="Wer hier nicht oben steht, ist ein Noob :xdx:")
    await interaction.followup.send(embed=embed)

@ww_group.command(name="start", description="Startet ein neues Werwolf-Spiel.")
@app_commands.describe(
    ziel_spieler="Die Ziel-Spieleranzahl. Bots füllen auf, wenn angegeben."
)
async def ww_start(interaction: discord.Interaction, ziel_spieler: int = None):
    """Handles the start of a Werwolf game."""
    channel_id = interaction.channel.id
    game = active_werwolf_games.get(channel_id)
    author = interaction.user

    if game:
        await interaction.response.send_message("In diesem Channel wurde bereits ein Spiel gestartet. Schau in die Kategorie '🐺 WERWOLF SPIEL 🐺'.", ephemeral=True)
        return
    
    await interaction.response.defer() # Defer while we create channels

    original_channel = interaction.channel # Store the channel where the command was used
    # --- NEW: Create dedicated category and channels ---
    try:
        guild = interaction.guild
        # Create a category for the game
        category = await guild.create_category(config['modules']['werwolf']['game_category_name'])

        # --- NEW: Set permissions to make the channel read-only for players ---
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(send_messages=False, read_messages=True),
            client.user: discord.PermissionOverwrite(send_messages=True) # Ensure the bot can write
        }
        # Create the text and voice channels inside the category
        game_text_channel = await category.create_text_channel("🐺-werwolf-chat", overwrites=overwrites)
        lobby_vc = await category.create_voice_channel(name="🐺 Werwolf Lobby", reason="Neues Werwolf-Spiel")
    except Exception as e:
        await interaction.followup.send(f"Konnte die Spiel-Channels nicht erstellen. Berechtigungen prüfen? Fehler: {e}", ephemeral=True)
        return

    game = WerwolfGame(game_text_channel, author, original_channel)
    game.lobby_vc = lobby_vc
    game.category = category
    game.join_message = None # Initialize join_message attribute

    active_werwolf_games[game_text_channel.id] = game
    # Send the ephemeral message to the command user
    await interaction.followup.send(f"Ein Werwolf-Spiel wurde in der Kategorie **{category.name}** erstellt! Schau in den Channel {game_text_channel.mention}.", ephemeral=True)
    # Send the public join message and store it for later deletion
    embed = discord.Embed(
        title="🐺 Ein neues Werwolf-Spiel wurde gestartet! 🐺",
        description=f"Tretet dem Voice-Channel **`{lobby_vc.name}`** bei, um mitzuspielen!",
        color=get_embed_color(config)
    )
    embed.add_field(name="Automatischer Start", value="Das Spiel startet in **15 Sekunden**.")
    embed.add_field(name="Spieler (1)", value=author.display_name, inline=False)
    embed.set_footer(text="Wer nicht beitritt, ist ein Werwolf!")
    
    # Create the view and send the initial message
    join_duration = config['modules']['werwolf']['join_phase_duration_seconds']
    view = WerwolfJoinView(game, join_duration)
    join_message = await game_text_channel.send(embed=embed, view=view)
    game.join_message = join_message

    # Start the countdown and wait for either the timer to finish or the button to be pressed
    countdown_task = asyncio.create_task(view.run_countdown())
    try:
        await asyncio.wait_for(view.start_now_event.wait(), timeout=join_duration)
    except asyncio.TimeoutError:
        pass # Timer finished normally
    finally:
        countdown_task.cancel()

    if game_text_channel.id not in active_werwolf_games:
        return # Game was cancelled

    # --- FIX: Check if anyone OTHER than the starter joined ---
    # If only the starter is in the game, cancel it and clean up.
    if len(game.players) <= 1:
        await game.game_channel.send("Niemand ist beigetreten. Das Spiel wird abgebrochen und die Channels werden aufgeräumt.")
        await game.end_game(None) # End game without a winner
        del active_werwolf_games[game_text_channel.id]
        return

    # Automatically start the game
    # Bot filling logic is now handled inside start_game
    error_message = await game.start_game(config, GEMINI_API_KEY, OPENAI_API_KEY, db_helpers, ziel_spieler)
    if error_message:
        await game.game_channel.send(error_message)
        del active_werwolf_games[game_text_channel.id]
        await game.lobby_vc.delete(reason="Fehler beim Spielstart")

# --- NEW: Add the voice command group to the tree ---
tree.add_command(voice_group)

# --- NEW: Add the admin command group to the tree ---
tree.add_command(AdminGroup(name="admin"))

class WerwolfJoinView(discord.ui.View):
    """A view for the Werwolf join phase, including a start button and countdown."""
    def __init__(self, game, duration):
        super().__init__(timeout=duration + 5) # Timeout slightly longer than the join phase
        self.game = game
        self.duration = duration
        self.start_now_event = asyncio.Event()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Only the game starter can press the "Start Now" button
        if interaction.data['custom_id'] == 'ww_start_now':
            if interaction.user.id != self.game.starter.id:
                await interaction.response.send_message("Nur der Ersteller des Spiels kann das Spiel sofort starten.", ephemeral=True)
                return False
        return True

    @discord.ui.button(label="Sofort starten", style=discord.ButtonStyle.success, custom_id="ww_start_now")
    async def start_now(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.disabled = True
        button.label = "Spiel startet..."
        await interaction.response.edit_message(view=self)
        self.start_now_event.set() # Signal the main task to stop waiting

    async def run_countdown(self):
        """Updates the join embed with a countdown timer."""
        while self.duration > 0:
            embed = self.game.join_message.embeds[0]
            embed.set_field_at(0, name="Automatischer Start", value=f"Das Spiel startet in **{self.duration} Sekunden**.")
            try:
                await self.game.join_message.edit(embed=embed)
            except discord.NotFound:
                return # Message was deleted, stop countdown
            
            await asyncio.sleep(min(5, self.duration)) # Update every 5 seconds or less
            self.duration -= 5

@client.event
async def on_message(message):
    """Fires on every message in any channel the bot can see."""
    if message.author == client.user:
        return

    # --- REFACTORED: Handle DMs first and exit ---
    if isinstance(message.channel, discord.DMChannel):
        # Check for Werwolf DM commands
        for game in active_werwolf_games.values():
            if message.author.id in game.players:
                author_player = game.players[message.author.id]
                if game.phase == "night" and author_player.is_alive:
                    parts = message.content.lower().split()
                    command = parts[0]
                    target_player = None
                    if len(parts) > 1:
                        target_name = " ".join(parts[1:])
                        target_player = game.get_player_by_name(target_name)
                        if not target_player:
                            await message.author.send(f"Ich konnte den Spieler '{target_name}' nicht finden.")
                            return
                    
                    if command in ["kill", "see", "poison", "mute", "heal"]:
                        error_message = await game.handle_night_action(author_player, command, target_player, config, GEMINI_API_KEY, OPENAI_API_KEY)
                        if error_message:
                            await message.author.send(error_message)
                        # Confirmation is sent from handle_night_action, so we just return.
                        return

        # If it's not a Werwolf command, treat it as a regular chatbot DM
        is_chatbot_trigger = True
    
    # --- REFACTORED: Handle Guild messages ---
    elif isinstance(message.channel, discord.TextChannel):
        # Ignore messages in active Werwolf game channels
        if message.channel.id in active_werwolf_games:
            game = active_werwolf_games.get(message.channel.id)
            if game and game.phase != "joining":
                if game.werwolf_thread and message.channel.id == game.werwolf_thread.id:
                    return
                return

        # Check if the message is a chatbot trigger
        is_pinged = client.user in message.mentions
        message_lower = message.content.lower()
        is_name_used = any(name in message_lower.split() for name in config['bot']['names'])
        is_chatbot_trigger = is_pinged or is_name_used

        # --- Leveling System ---
        if not message.content.startswith('/'):
            stat_period = datetime.now(timezone.utc).strftime('%Y-%m')
            custom_emojis = re.findall(r'<a?:(\w+):\d+>', message.content)
            await db_helpers.log_message_stat(message.author.id, message.channel.id, custom_emojies, stat_period)

            mentioned_id = message.mentions[0].id if message.mentions and not message.mentions[0].bot else None
            replied_id = None
            if message.reference and isinstance(message.reference.resolved, discord.Message):
                if message.reference.resolved.author.id != client.user.id:
                    replied_id = message.reference.resolved.author.id
            await db_helpers.log_mention_reply(message.author.id, message.guild.id, mentioned_id, replied_id, message.created_at)

            new_level = await grant_xp(message.author.id, message.author.display_name, db_helpers.add_xp, config)
            if new_level:
                bonus = calculate_level_up_bonus(new_level, config)
                await db_helpers.add_balance(message.author.id, message.author.display_name, bonus, config, stat_period)
                try:
                    await message.author.send(f"GG! Du bist durch das Schreiben von Nachrichten jetzt Level **{new_level}**! :YESS:\n"
                                              f"Du erhältst **{bonus}** Währung als Belohnung!")
                except discord.Forbidden:
                    print(f"Could not send level up DM to {message.author.name} (DMs likely closed).")

        # If it's not a chatbot trigger, we are done with this message.
        if not is_chatbot_trigger:
            return
    else:
        # Not a DM or a TextChannel, ignore.
        return

    # --- REFACTORED: Centralized Chatbot Logic ---
    # This part is now only reached if is_chatbot_trigger is True.
    print(f"Chatbot triggered by {message.author.name} in channel #{message.channel.name}.")
    
    if not isinstance(message.channel, discord.DMChannel):
        stat_period = datetime.now(timezone.utc).strftime('%Y-%m')
        await db_helpers.log_stat_increment(message.author.id, stat_period, 'sulf_interactions')

    user_prompt = message.content.replace(f"<@{client.user.id}>", "").strip()

    if not user_prompt:
        await message.channel.send(config['bot']['chat']['empty_ping_response'])
        return
    
    history = await db_helpers.get_chat_history(message.channel.id, config['bot']['chat']['max_history_messages'])

    async with message.channel.typing():
        relationship_summary = await db_helpers.get_relationship_summary(message.author.id)
        dynamic_system_prompt = config['bot']['system_prompt']
        if relationship_summary:
            dynamic_system_prompt += f"\n\nZusätzlicher Kontext über deine Beziehung zu '{message.author.display_name}': {relationship_summary}"

        provider_to_use = await get_current_provider(config)
        if provider_to_use == 'gemini':
            await db_helpers.increment_gemini_usage()
        
        temp_config = config.copy()
        temp_config['api']['provider'] = provider_to_use
        response_text, error_message = await get_chat_response(history, user_prompt, message.author.display_name, dynamic_system_prompt, temp_config, GEMINI_API_KEY, OPENAI_API_KEY)

        if error_message:
            await message.channel.send(f"{message.author.mention} {error_message}")
            return

        if len(history) >= 2:
            user_message_content = history[-2]['parts'][0]['text']
            await db_helpers.save_message_to_history(message.channel.id, "user", user_message_content)
        await db_helpers.save_message_to_history(message.channel.id, "model", response_text)

        update_interval = config['bot']['chat']['relationship_update_interval'] * 2
        if len(history) > 0 and len(history) % update_interval == 0:
            print(f"Updating relationship summary for {message.author.name}.")
            provider_to_use_summary = await get_current_provider(config)
            if provider_to_use_summary == 'gemini':
                await db_helpers.increment_gemini_usage()
            temp_config_summary = config.copy()
            temp_config_summary['api']['provider'] = provider_to_use_summary
            new_summary, _ = await get_relationship_summary_from_api(history, message.author.display_name, relationship_summary, temp_config_summary, GEMINI_API_KEY, OPENAI_API_KEY)
            if new_summary:
                await db_helpers.update_relationship_summary(message.author.id, new_summary)

        final_response = await replace_emoji_tags(response_text, client)
        for chunk in await split_message(final_response):
            if chunk: await message.channel.send(chunk)

# --- RUN THE BOT ---
if __name__ == "__main__":
    client.run(DISCORD_BOT_TOKEN)