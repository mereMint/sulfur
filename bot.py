import asyncio
import json
import discord
import random
import os
import subprocess
import socket
import signal
import sys
from collections import deque
import re
from datetime import datetime, timedelta, timezone

# --- NEW: Import structured logging ---
from modules.logger_utils import bot_logger as logger

# --- NEW: Library Version Check ---
# This code requires discord.py version 2.0 or higher for slash commands.
try:
    version_parts = tuple(int(x) for x in discord.__version__.split('.'))
    if version_parts[0] < 2:
        logger.error(f"discord.py version {discord.__version__} is too old. Requires 2.0.0+")
        print("Error: Your discord.py version is too old.")
        print(f"You have version {discord.__version__}, but this bot requires version 2.0.0 or higher.")
        print("Please update it by running: pip install -U discord.py")
        exit()
except (ValueError, IndexError) as e:
    logger.error(f"Could not parse discord.py version: {discord.__version__}")
    print(f"Warning: Could not verify discord.py version ({discord.__version__}). Proceeding anyway...")
    print("If you encounter issues, ensure you have discord.py 2.0.0 or higher installed.")

# --- NEW: Load environment variables from .env file ---
from dotenv import load_dotenv
load_dotenv()

from discord import app_commands
from discord.ext import tasks
from modules.werwolf import WerwolfGame
from modules.api_helpers import get_chat_response, get_relationship_summary_from_api, get_wrapped_summary_from_api, get_game_details_from_api
from modules import api_helpers
from modules.bot_enhancements import (
    handle_image_attachment,
    handle_unknown_emojis_in_message,
    enhance_prompt_with_context,
    save_ai_conversation,
    track_api_call,
    initialize_emoji_system,
)
from discord.ext import tasks as _tasks  # separate alias for new periodic cleanup

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
    logger.critical("DISCORD_BOT_TOKEN environment variable is not set")
    print("Error: DISCORD_BOT_TOKEN environment variable is not set.")
    print("Please ensure your '.env' file exists in the same directory as the bot and contains the line:")
    print('DISCORD_BOT_TOKEN="YOUR_BOT_TOKEN_HERE"')
    exit()

# --- NEW: Diagnostic check to ensure the token looks valid ---
token_parts = DISCORD_BOT_TOKEN.split('.')
if len(token_parts) != 3:
    logger.critical(f"DISCORD_BOT_TOKEN appears malformed (parts: {len(token_parts)})")
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
        with open("config/config.json", "r", encoding="utf-8") as f:
            config = json.load(f)

        prompt_file = config.get("bot", {}).get("system_prompt_file", "config/system_prompt.txt")
        with open(prompt_file, "r", encoding="utf-8") as f:
            config["bot"]["system_prompt"] = f.read()
            
        return config
    except FileNotFoundError as e:
        logger.critical(f"Configuration file not found: {e.filename}")
        print(f"FATAL: Configuration file not found: {e.filename}. Please ensure 'config.json' and the prompt file exist.")
        exit()
    except json.JSONDecodeError as e:
        logger.critical(f"Malformed config.json: {e}")
        print("FATAL: 'config.json' is malformed. Please check the JSON syntax.")
        exit()

def save_config(new_config):
    """Saves the provided configuration dictionary back to config.json."""
    # We don't want to save the full system prompt back into the file
    config_to_save = new_config.copy()
    if 'bot' in config_to_save and 'system_prompt' in config_to_save['bot']:
        del config_to_save['bot']['system_prompt']
        
    with open("config/config.json", "w", encoding="utf-8") as f:
        json.dump(config_to_save, f, indent=2)

config = load_config()

# --- REFACTORED: Validate API keys after loading config ---
key_error = check_api_keys(config)
if key_error:
    logger.critical(f"API key validation failed: {key_error}")
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

# --- INSTANCE GUARD & MESSAGE DEDUPLICATION ---
# Prevent multi-process duplicate replies and duplicate history inserts.
# We create a lightweight lock file with the primary process PID.
INSTANCE_LOCK_FILE = "bot_instance.lock"
SECONDARY_INSTANCE = False

current_pid = os.getpid()
logger.info(f"Bot starting with PID {current_pid}")
print(f"[GUARD] Bot starting with PID {current_pid}")

try:
    if os.path.exists(INSTANCE_LOCK_FILE):
        try:
            with open(INSTANCE_LOCK_FILE, 'r', encoding='utf-8') as f:
                existing_pid_line = f.readline().strip()
                existing_pid = int(existing_pid_line) if existing_pid_line.isdigit() else None
            
            logger.info(f"Found lock file with PID {existing_pid}")
            print(f"[GUARD] Found existing lock file with PID {existing_pid}")
            
            if existing_pid and existing_pid != current_pid:
                # Check if the process is actually still running
                process_exists = False
                try:
                    # Try to send signal 0 to check if process exists (works on Unix and Windows)
                    if sys.platform == "win32":
                        # On Windows, use tasklist to check if PID exists
                        import subprocess
                        result = subprocess.run(['tasklist', '/FI', f'PID eq {existing_pid}'], 
                                               capture_output=True, text=True, timeout=5)
                        process_exists = str(existing_pid) in result.stdout
                        logger.debug(f"Windows process check for PID {existing_pid}: {process_exists}")
                    else:
                        # On Unix, use os.kill with signal 0
                        try:
                            os.kill(existing_pid, 0)
                            process_exists = True
                            logger.debug(f"Unix process check for PID {existing_pid}: exists")
                        except OSError:
                            process_exists = False
                            logger.debug(f"Unix process check for PID {existing_pid}: does not exist")
                except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
                    # Process doesn't exist or error checking
                    process_exists = False
                    logger.debug(f"Error checking process {existing_pid}: {e}")
                
                if process_exists:
                    SECONDARY_INSTANCE = True
                    logger.warning(f"Another instance is running (PID {existing_pid}), this will be a secondary instance")
                    print(f"[GUARD] Another instance detected (PID {existing_pid}). This is a SECONDARY instance and will NOT process messages.")
                else:
                    # Stale lock file, we become primary
                    SECONDARY_INSTANCE = False
                    logger.info(f"Stale lock file found (PID {existing_pid} no longer running), claiming primary instance")
                    print(f"[GUARD] Stale lock file found - PID {existing_pid} is not running. This will be the PRIMARY instance.")
            elif existing_pid == current_pid:
                # Lock file has our own PID (shouldn't happen but handle it)
                SECONDARY_INSTANCE = False
                logger.warning(f"Lock file contains our own PID {current_pid}, assuming primary")
                print(f"[GUARD] Lock file has our own PID - claiming PRIMARY instance")
            else:
                # Invalid PID in lock file
                SECONDARY_INSTANCE = False
                logger.warning(f"Invalid PID in lock file: {existing_pid_line}, assuming primary")
                print(f"[GUARD] Invalid PID in lock file - claiming PRIMARY instance")
        except Exception as e:
            # If we cannot read/parse we assume primary ownership
            SECONDARY_INSTANCE = False
            logger.warning(f"Failed to read lock file: {e}, assuming primary ownership")
            print(f"[GUARD] Error reading lock file: {e} - claiming PRIMARY instance")
    else:
        logger.info("No existing lock file found")
        print("[GUARD] No existing lock file - will be PRIMARY instance")
    
    if not SECONDARY_INSTANCE:
        # Remove old lock file if it exists
        if os.path.exists(INSTANCE_LOCK_FILE):
            os.remove(INSTANCE_LOCK_FILE)
            logger.info("Removed old lock file")
        
        # Create new lock file with our PID
        with open(INSTANCE_LOCK_FILE, 'w', encoding='utf-8') as f:
            f.write(str(current_pid))
        logger.info(f"Created lock file with PID {current_pid} - this is the PRIMARY instance")
        print(f"[GUARD] Created lock file with PID {current_pid} - this is the PRIMARY instance")
    else:
        logger.warning("Running as SECONDARY instance - will not process messages")
        print("[GUARD] Running as SECONDARY instance - will NOT process messages")
        
except Exception as e:
    logger.error(f"Lock file handling failed: {e}, assuming primary ownership")
    print(f"[GUARD] Lock file error: {e} - defaulting to PRIMARY instance")
    SECONDARY_INSTANCE = False
    # Try to create lock file anyway
    try:
        with open(INSTANCE_LOCK_FILE, 'w', encoding='utf-8') as f:
            f.write(str(current_pid))
    except:
        pass

# In-memory caches for duplicate suppression
last_processed_message_ids = deque(maxlen=500)
recent_user_message_cache = {}  # (user_id, content) -> timestamp

# --- NEW: Import and initialize DB helpers ---
from modules.db_helpers import init_db_pool, initialize_database, get_leaderboard, add_xp, get_player_rank, get_level_leaderboard, save_message_to_history, get_chat_history, get_relationship_summary, update_relationship_summary, save_bulk_history, clear_channel_history, update_user_presence, add_balance, update_spotify_history, get_all_managed_channels, remove_managed_channel, get_managed_channel_config, update_managed_channel_config, log_message_stat, log_vc_minutes, get_wrapped_stats_for_period, get_user_wrapped_stats, log_stat_increment, get_spotify_history, get_player_profile, cleanup_custom_status_entries, log_mention_reply, log_vc_session, get_wrapped_extra_stats, get_xp_for_level, register_for_wrapped, unregister_from_wrapped, is_registered_for_wrapped, get_wrapped_registrations
import modules.db_helpers as db_helpers
db_helpers.init_db_pool(DB_HOST, DB_USER, DB_PASS, DB_NAME)
from modules.level_system import grant_xp
# --- NEW: Import Voice Manager ---
import modules.voice_manager as voice_manager
# --- NEW: Import Economy ---
from modules.economy import calculate_level_up_bonus
# --- NEW: Import Quest System ---
import modules.quests as quests

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
    # --- REFACTORED: Use the new detailed api_usage table ---
    if provider == 'gemini':
        # --- FIX: Properly handle DB pool being None ---
        if not db_helpers.db_pool:
            logger.warning("Database pool not available, returning configured provider")
            return provider
        
        try:
            cnx = db_helpers.db_pool.get_connection()
            if not cnx: 
                logger.warning("Could not get DB connection, returning configured provider")
                return provider
            
            cursor = cnx.cursor(dictionary=True)
            usage = 0
            try:
                # Sum up all calls for models starting with 'gemini' for today
                cursor.execute("SELECT SUM(call_count) as total_calls FROM api_usage WHERE usage_date = CURDATE() AND model_name LIKE 'gemini%%'")
                result = cursor.fetchone()
                usage = result['total_calls'] if result and result['total_calls'] else 0
            finally:
                cursor.close()
                cnx.close()
            # If the limit is reached, switch to openai for this call.
            return 'openai' if usage >= GEMINI_DAILY_LIMIT else 'gemini'
        except Exception as e:
            logger.error(f"Error checking Gemini usage: {e}")
            return provider
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
        logger.error(f"Unhandled exception in command tree: {error}", exc_info=error)
        print(f"Unhandled exception in command tree: {error}")
        message = "Ups, da ist etwas schiefgelaufen. Wahrscheinlich deine Schuld. :dono:"
        # --- NEW: Set status to idle on unhandled command error ---
        await client.change_presence(
            status=discord.Status.idle, # Set status to Idle
            activity=None # Clear the activity
        )

    # --- FIX: Use followup if interaction is already acknowledged ---
    try:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
    except discord.errors.HTTPException as e:
        # This can happen if the original interaction token expires or is invalid.
        logger.warning(f"Failed to send error message for interaction {interaction.id}: {e}")
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

def sanitize_malformed_emojis(text):
    """
    Fixes malformed emoji patterns that the AI might generate.
    Handles both static (<:name:id>) and animated (<a:name:id>) emojis.
    Examples: 
      - <<:name:id>id> -> <:name:id>
      - <<a:name:id>id> -> <a:name:id>
      - `<:name:id>` -> <:name:id> (removes inline code backticks, preserves code blocks)
      - `:emoji:` -> :emoji: (removes backticks from short format too)
    """
    # Fix pattern like <<:emoji_name:emoji_id>emoji_id> or <<a:emoji_name:emoji_id>emoji_id>
    text = re.sub(r'<<(a?):(\w+):(\d+)>\3>', r'<\1:\2:\3>', text)
    # Fix pattern like <<:emoji_name:emoji_id>> or <<a:emoji_name:emoji_id>>
    text = re.sub(r'<<(a?):(\w+):(\d+)>>', r'<\1:\2:\3>', text)
    # Fix pattern like <:emoji_name:emoji_id>emoji_id or <a:emoji_name:emoji_id>emoji_id (trailing ID)
    text = re.sub(r'<(a?):(\w+):(\d+)>\3', r'<\1:\2:\3>', text)
    # Remove single backticks around full emoji format (inline code), but not triple backticks (code blocks)
    # Use negative lookbehind and lookahead to avoid matching triple backticks
    text = re.sub(r'(?<!`)`<(a?):(\w+):(\d+)>`(?!`)', r'<\1:\2:\3>', text)
    # Remove single backticks around short emoji format too
    text = re.sub(r'(?<!`)`:(\w+):`(?!`)', r':\1:', text)
    return text

async def replace_emoji_tags(text, client):
    """
    Replaces :emoji_name: tags and converts <:emoji_name:emoji_id> to :emoji_name: format.
    Prioritizes application emojis (bot's own emojis) over server emojis.
    """
    # First, sanitize any malformed emoji patterns
    text = sanitize_malformed_emojis(text)
    
    # Find all :emoji_name: tags in the text
    emoji_tags = re.findall(r':(\w+):', text)
    # Also find <:emoji_name:emoji_id> tags
    full_emoji_tags = re.findall(r'<:(\w+):(\d+)>', text)
    
    if not emoji_tags and not full_emoji_tags:
        return text

    # Create a global mapping of all available emoji names
    # First, add server emojis
    emoji_map = {}
    for emoji in client.emojis:
        # Store both exact match and lowercase version for case-insensitive matching
        if emoji.name not in emoji_map:
            emoji_map[emoji.name] = emoji.name
        emoji_map[emoji.name.lower()] = emoji.name
    
    # Then, prioritize application emojis (they will override server emojis with the same name)
    try:
        app_emojis = await client.fetch_application_emojis()
        for emoji in app_emojis:
            emoji_map[emoji.name] = emoji.name
            emoji_map[emoji.name.lower()] = emoji.name
    except Exception as e:
        logger.debug(f"Could not fetch application emojis for replacement: {e}")

    # Replace :emoji_name: tags with case-insensitive matching (keep in short format)
    replaced_count = 0
    for tag in set(emoji_tags):  # Use set to avoid replacing the same tag multiple times
        # Try exact match first, then lowercase
        if tag in emoji_map:
            # Already in correct format, just validate it exists
            replaced_count += 1
        elif tag.lower() in emoji_map:
            # Replace with the correct case
            text = text.replace(f":{tag}:", f":{emoji_map[tag.lower()]}:")
            replaced_count += 1
        else:
            # Log emojis that couldn't be found
            logger.debug(f"Emoji not found: :{tag}:")
    
    if replaced_count > 0:
        logger.debug(f"Validated {replaced_count} emoji tags")
    
    # Convert <:emoji_name:emoji_id> and <a:emoji_name:emoji_id> to :emoji_name: format
    # This ensures emojis are displayed in their short form without the ID
    text = re.sub(r'<a?:(\w+):\d+>', r':\1:', text)
    
    return text

def get_embed_color(config_obj):
    """Helper function to parse the hex color from config into a discord.Color object."""
    hex_color = config_obj.get('bot', {}).get('embed_color', '#7289DA') # Default to blurple
    return discord.Color(int(hex_color.lstrip('#'), 16))


async def get_user_embed_color(user_id, config_obj):
    """
    Get the embed color for a specific user.
    Uses the user's equipped color if they have one, otherwise uses the default.
    """
    # Try to get user's equipped color
    equipped_color = await db_helpers.get_user_equipped_color(user_id)
    
    if equipped_color:
        try:
            # Convert hex color to discord.Color
            return discord.Color(int(equipped_color.lstrip('#'), 16))
        except (ValueError, AttributeError):
            # If color is invalid, fall back to default
            pass
    
    # Fall back to default config color
    return get_embed_color(config_obj)


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
    # Also sync per-guild for immediate availability of new commands
    try:
        for guild in client.guilds:
            try:
                await tree.sync(guild=guild)
            except Exception as e:
                print(f"Guild sync failed for {guild.name}: {e}")
    except Exception as e:
        print(f"Bulk guild sync failed: {e}")
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
    # Start periodic Werwolf category cleanup
    if not cleanup_werwolf_categories.is_running():
        cleanup_werwolf_categories.start()
    

    print(f"Synced {len(synced)} global commands.")

    logger.info(f"Bot logged in as {client.user} - Ready to serve!")
    logger.info(f"Synced {len(synced)} global commands")
    logger.info(f"Connected to {len(client.guilds)} guild(s)")
    print(f'Ayo, the bot is logged in and ready, fam! ({client.user})')
    print('Let\'s chat.')
    
    # --- NEW: Generate daily quests for all users on startup ---
    print("Generating daily quests for all users...")
    quest_generation_count = 0
    try:
        # Get all unique user IDs from the database
        if db_helpers.db_pool:
            cnx = db_helpers.db_pool.get_connection()
            if cnx:
                cursor = cnx.cursor(dictionary=True)
                try:
                    # Get all users who have activity in the last 30 days
                    cursor.execute("""
                        SELECT DISTINCT user_id FROM user_stats 
                        WHERE stat_period >= DATE_FORMAT(DATE_SUB(NOW(), INTERVAL 30 DAY), '%Y-%m')
                    """)
                    users = cursor.fetchall()
                    
                    for user_row in users:
                        user_id = user_row['user_id']
                        # Generate quests for this user
                        quest_list = await quests.generate_daily_quests(db_helpers, user_id, config)
                        if quest_list:
                            quest_generation_count += 1
                    
                    print(f"  -> Generated quests for {quest_generation_count} user(s)")
                finally:
                    cursor.close()
                    cnx.close()
    except Exception as e:
        logger.error(f"Error generating startup quests: {e}", exc_info=True)
        print(f"  -> Error generating quests: {e}")

    # --- NEW: Initialize Emoji System and enrich system prompt (optional) ---
    try:
        emoji_context = await initialize_emoji_system(client, config, GEMINI_API_KEY, OPENAI_API_KEY)
        if emoji_context:
            # Append emoji context to system prompt for richer replies
            config['bot']['system_prompt'] = (config['bot']['system_prompt'] or '') + "\n\n" + emoji_context
    except Exception as e:
        print(f"[Startup] Emoji system init failed: {e}")

    # --- NEW: Start periodic cleanup for old conversation contexts ---
    if not periodic_cleanup.is_running():
        periodic_cleanup.start()
    
    # --- NEW: Start periodic application emoji check ---
    if not check_application_emojis.is_running():
        check_application_emojis.start()

@tasks.loop(minutes=15)
async def update_presence_task():
    """A background task that periodically updates the bot's presence to watch a random user."""
    try:
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

        # --- REFACTORED: More efficient way to find a random user ---
        # 1. Get all non-bot members from all guilds the bot is in.
        all_online_members = []
        for guild in client.guilds:
            all_online_members.extend([m for m in guild.members if not m.bot and m.status != discord.Status.offline])

        # 2. If we found any online members, pick one at random.
        if all_online_members:
            member_to_watch = random.choice(all_online_members)
            templates = config['bot']['presence']['activity_templates']
            template = random.choice(templates)
            activity_name = template.format(user=member_to_watch.display_name)

            logger.debug(f"Presence update: {activity_name}")
            print(f"  -> Presence update: {activity_name}")
            await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=activity_name))
            return # Success, exit the task for this run

        # Fallback if no human members were found at all.
        logger.debug("Presence update: No human members found. Using fallback.")
        print("  -> Presence update: No human members found. Using fallback.")
        fallback_activity = config.get('bot', {}).get('presence', {}).get('fallback_activity', "euch beim AFK sein zu")
        await client.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(type=discord.ActivityType.watching, name=fallback_activity)
        )
    except Exception as e:
        logger.error(f"Error in presence update task: {e}", exc_info=True)
        print(f"  -> Error updating presence: {e}")

# --- NEW: Periodic cleanup of old conversation contexts ---
@_tasks.loop(minutes=10)
async def periodic_cleanup():
    try:
        from modules.bot_enhancements import cleanup_task as _cleanup
        await _cleanup(client)
    except Exception as e:
        logger.error(f"Error in periodic cleanup: {e}", exc_info=True)
        print(f"[Periodic Cleanup] Error: {e}")

@update_presence_task.before_loop
async def before_update_presence_task():
    await client.wait_until_ready()

# --- NEW: Periodic Channel Cleanup Task ---
@tasks.loop(hours=1)
async def cleanup_empty_channels():
    """Periodically finds and deletes empty, managed voice channels."""
    try:
        print("Running periodic cleanup of empty voice channels...")
        managed_channel_ids = await db_helpers.get_all_managed_channels()
        deleted_count = 0
        orphaned_count = 0
        if not managed_channel_ids:
            print("  -> No managed channels found in the database.")
            return

        for channel_id in managed_channel_ids:
            try:
                channel = client.get_channel(channel_id)
                if not channel:
                    # Channel doesn't exist in Discord anymore (manually deleted)
                    await db_helpers.remove_managed_channel(channel_id, keep_owner_record=True)
                    print(f"  -> Cleaned up orphaned DB record for channel {channel_id}")
                    orphaned_count += 1
                elif isinstance(channel, discord.VoiceChannel) and not channel.members:
                    # Channel exists but is empty
                    try:
                        await channel.delete(reason="Periodic cleanup of empty channel")
                        await db_helpers.remove_managed_channel(channel_id, keep_owner_record=True)
                        print(f"  -> Cleaned up empty channel: {channel.name} ({channel_id})")
                        deleted_count += 1
                    except (discord.Forbidden, discord.NotFound):
                        # If we can't delete, at least remove it from our active list
                        await db_helpers.remove_managed_channel(channel_id, keep_owner_record=True)
            except Exception as e:
                logger.error(f"Error cleaning up channel {channel_id}: {e}")
                continue
                
        if deleted_count > 0 or orphaned_count > 0:
            print(f"Periodic cleanup finished. Deleted {deleted_count} empty channel(s), cleaned {orphaned_count} orphaned DB record(s).")
    except Exception as e:
        logger.error(f"Error in cleanup_empty_channels task: {e}", exc_info=True)
        print(f"[Channel Cleanup Task] Error: {e}")

@tasks.loop(hours=1)
async def cleanup_werwolf_categories():
    """Finds and deletes stale Werwolf categories and channels if no active game references them."""
    try:
        category_name = config['modules']['werwolf']['game_category_name']
        for guild in client.guilds:
            for category in guild.categories:
                if category.name != category_name:
                    continue
                # Determine if any active game still uses channels within this category
                category_channel_ids = {ch.id for ch in category.channels}
                in_use = False
                for game in active_werwolf_games.values():
                    chans = [getattr(game, 'game_channel', None), getattr(game, 'lobby_vc', None), getattr(game, 'discussion_vc', None)]
                    for ch in chans:
                        if ch and ch.id in category_channel_ids:
                            in_use = True
                            break
                    if in_use:
                        break

                if in_use:
                    continue

                # If no use: delete empty channels then category
                try:
                    for ch in list(category.channels):
                        # If it's a voice channel, ensure it's empty
                        if isinstance(ch, discord.VoiceChannel) and ch.members:
                            # Skip categories with occupied voice channels
                            break
                        try:
                            await ch.delete(reason="Periodic Werwolf cleanup (stale)")
                        except Exception:
                            pass
                    else:
                        # Only reached if we did not break (no occupied voice channels)
                        try:
                            await category.delete(reason="Periodic Werwolf cleanup (stale category)")
                        except Exception:
                            pass
                except Exception:
                    pass
    except Exception as e:
        logger.error(f"Error in cleanup_werwolf_categories task: {e}")


# --- NEW: Periodic Application Emoji Check ---
@tasks.loop(hours=6)
async def check_application_emojis():
    """Periodically checks for new application emojis and analyzes them."""
    try:
        print("[Emoji System] Checking for new application emojis...")
        from modules.emoji_manager import analyze_application_emojis
        await analyze_application_emojis(client, config, GEMINI_API_KEY, OPENAI_API_KEY)
        print("[Emoji System] Application emoji check complete.")
    except Exception as e:
        logger.error(f"Error in check_application_emojis task: {e}", exc_info=True)
        print(f"[Emoji System] Error checking application emojis: {e}")


@check_application_emojis.before_loop
async def before_check_application_emojis():
    await client.wait_until_ready()


@client.event
async def on_presence_update(before, after):
    """Fires when a member's status, activity, etc. changes. Used for tracking."""
    try:
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

        before_spotify = next((act for act in before.activities if isinstance(act, discord.Spotify)), None)
        after_spotify = next((act for act in after.activities if isinstance(act, discord.Spotify)), None)

        # Case 1: Song has stopped (or changed)
        if before_spotify and (not after_spotify or after_spotify.track_id != before_spotify.track_id):
            if user_id in spotify_start_times:
                logged_song, start_time = spotify_start_times.pop(user_id)
                duration_seconds = (now - start_time).total_seconds()
                # Only log if they listened for a meaningful amount of time (e.g., > 30s)
                if duration_seconds > 30:
                    duration_minutes = duration_seconds / 60.0
                    stat_period = now.strftime('%Y-%m')
                    await db_helpers.log_stat_increment(user_id, stat_period, 'spotify_minutes', key=f"{logged_song[0]} by {logged_song[1]}", amount=duration_minutes)
                    print(f"    - Logged {duration_minutes:.2f} mins for '{logged_song[0]}'.")

                # If the song just stopped (not changed), cache it for potential resume
                if not after_spotify:
                    print(f"    - Paused '{logged_song[0]}'. Caching session.")
                    spotify_pause_cache[user_id] = (logged_song, start_time)

        # Case 2: Song has started (or resumed)
        if after_spotify:
            resumed_song = (after_spotify.title, after_spotify.artist)
            # Check if it's a resume from pause
            if user_id in spotify_pause_cache and spotify_pause_cache[user_id][0] == resumed_song:
                print(f"  -> [Spotify] Resumed '{resumed_song[0]}' for {after.display_name}. Restarting timer.")
                spotify_start_times[user_id] = spotify_pause_cache.pop(user_id) # Restore timer from cache
            # Check if it's a brand new song session
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
                    
                    # --- NEW: Track game minutes for quest progress ---
                    try:
                        quest_completed, _ = await quests.update_quest_progress(db_helpers, user_id, 'game_minutes', int(duration_minutes))
                        # Quest completion notifications will be sent when user checks /quests or uses /questclaim
                    except Exception as e:
                        logger.error(f"Error updating game quest progress for user {user_id}: {e}", exc_info=True)
                
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
    except Exception as e:
        logger.error(f"Error in on_presence_update: {e}", exc_info=True)
        # Don't print to console as this could spam too much


@tasks.loop(minutes=1)
async def grant_voice_xp():
    """A background task that grants XP to users in voice channels every minute.
    This is now highly efficient as it only iterates over users currently in a VC."""
    try:
        # Create a copy of the user IDs to prevent issues if the set changes during iteration
        users_to_process = list(active_vc_users.keys())
        
        for user_id in users_to_process:
            member = active_vc_users.get(user_id)
            if not member: continue

            try:
                stat_period = datetime.now(timezone.utc).strftime('%Y-%m')
                new_level = await db_helpers.add_xp(member.id, member.display_name, config['modules']['leveling']['xp_per_minute_in_vc'])
                await db_helpers.log_vc_minutes(member.id, 1, stat_period) # Log 1 minute for Wrapped
                
                # --- NEW: Track VC minutes for quest progress ---
                try:
                    quest_completed, _ = await quests.update_quest_progress(db_helpers, member.id, 'vc_minutes', 1)
                    # Quest completion notifications will be sent when user checks /quests or uses /questclaim
                except Exception as e:
                    logger.error(f"Error updating VC quest progress for user {user_id}: {e}", exc_info=True)
                
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
            except Exception as e:
                logger.error(f"Error granting voice XP to user {user_id}: {e}")
                continue
    except Exception as e:
        logger.error(f"Error in grant_voice_xp task: {e}", exc_info=True)
        print(f"[Voice XP Task] Error: {e}")

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
    try:
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

            # --- NEW: Get list of registered users ---
            registered_users = await db_helpers.get_wrapped_registrations()
            if not registered_users:
                print(f"No users registered for Wrapped. Skipping distribution.")
                return

            # --- NEW: Pre-calculate ranks ---
            total_users = len(stats)
            if total_users == 0:
                print(f"No stats found for period {last_month_stat_period}. Skipping distribution.")
                return

            # Create sorted lists for ranking

            # --- NEW: Only send to registered users ---
            for user_stats in stats:
                user_id = user_stats.get('user_id')
                if user_id not in registered_users:
                    continue  # Skip users who haven't opted in
                
                await _generate_and_send_wrapped_for_user(
                    user_stats=user_stats,
                    stat_period_date=last_month_first_day,
                    all_stats_for_period=stats,
                    total_users=total_users,
                    server_averages=await _calculate_server_averages(stats)
                )
    except Exception as e:
        logger.error(f"Error in manage_wrapped_event task: {e}", exc_info=True)
        print(f"[Wrapped Event Task] Error: {e}")

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
            
            # --- FIX: Fetch game image from the API ---
            # This defines the 'api_response' variable that was previously missing.
            api_response, _ = await get_game_details_from_api([fav_game_name], config, GEMINI_API_KEY, OPENAI_API_KEY)
            game_image_url = api_response.get(fav_game_name, {}).get('image') if api_response else None
            
            if game_image_url:
                game_embed.set_thumbnail(url=game_image_url)


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

            # --- NEW: Calculate Top Artists for Wrapped ---
            artist_minutes = {}
            for song_key, minutes in spotify_minutes_data.items():
                try:
                    artist = song_key.split(' by ')[1]
                    artist_minutes[artist] = artist_minutes.get(artist, 0) + minutes
                except IndexError:
                    continue # Skip malformed song keys
            
            sorted_artists = sorted(artist_minutes.items(), key=lambda item: item[1], reverse=True)
            top_artists_text = ""
            for i, (artist, minutes) in enumerate(sorted_artists[:5]):
                top_artists_text += f"**{i+1}.** `{artist}` - *{minutes:.0f} Minuten*\n"

            if top_songs_text:
                spotify_embed = discord.Embed(title="Dein Spotify-Rückblick", color=discord.Color.green())
                spotify_embed.add_field(name="Gesamte Hörzeit", value=f"Du hast diesen Monat insgesamt **{total_minutes:.0f} Minuten** Musik gehört.", inline=False)
                spotify_embed.add_field(name="Deine Top 5 Songs (nach Hörzeit)", value=top_songs_text, inline=False)
                if top_artists_text:
                    spotify_embed.add_field(name="Deine Top 5 Künstler (nach Hörzeit)", value=top_artists_text, inline=False)
                spotify_embed.set_footer(text="Basiert auf der Zeit, die du Songs über Discord gehört hast.")
                pages.append(spotify_embed)

    # --- NEW Page: Quest & Game Stats ---
    if extra_stats.get('quests_completed', 0) > 0 or extra_stats.get('games_played', 0) > 0:
        quest_game_embed = discord.Embed(title="Quests & Gambling", color=color)
        
        # Quest stats
        if extra_stats.get('quests_completed', 0) > 0:
            quest_text = f"**Abgeschlossene Quests:** {extra_stats.get('quests_completed', 0)}\n"
            quest_text += f"**Tage mit allen Quests:** {extra_stats.get('total_quest_days', 0)}\n"
            
            if extra_stats.get('total_quest_days', 0) > 0:
                completion_rate = (extra_stats.get('total_quest_days', 0) / 30) * 100
                if completion_rate >= 90:
                    quest_text += "\n🏆 **Quest-Master!** Du hast fast jeden Tag alle Quests abgeschlossen!"
                elif completion_rate >= 50:
                    quest_text += "\n⭐ **Fleißiger Quester!** Du bleibst dran!"
                else:
                    quest_text += "\n💪 **Guter Start!** Weiter so!"
            
            quest_game_embed.add_field(name="📋 Quest-Fortschritt", value=quest_text, inline=False)
        
        # Game stats
        if extra_stats.get('games_played', 0) > 0:
            games_played = extra_stats.get('games_played', 0)
            games_won = extra_stats.get('games_won', 0)
            total_bet = extra_stats.get('total_bet', 0)
            total_won = extra_stats.get('total_won', 0)
            
            win_rate = (games_won / games_played * 100) if games_played > 0 else 0
            net_profit = total_won - total_bet
            
            currency = config['modules']['economy']['currency_symbol']
            game_text = f"**Spiele gespielt:** {games_played}\n"
            game_text += f"**Spiele gewonnen:** {games_won}\n"
            game_text += f"**Gewinnrate:** {win_rate:.1f}%\n\n"
            game_text += f"**Gesamt gewettet:** {total_bet} {currency}\n"
            game_text += f"**Gesamt gewonnen:** {total_won} {currency}\n"
            
            if net_profit > 0:
                game_text += f"**Netto-Gewinn:** +{net_profit} {currency} 💰"
            elif net_profit < 0:
                game_text += f"**Netto-Verlust:** {net_profit} {currency} 📉"
            else:
                game_text += f"**Ausgeglichen** ⚖️"
            
            quest_game_embed.add_field(name="🎰 Gambling Stats", value=game_text, inline=False)
        
        quest_game_embed.set_footer(text="Quests & Mini-Games - Deine Aktivität im Bot")
        pages.append(quest_game_embed)

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
    # Add quest/game stats if they exist
    if extra_stats.get('quests_completed', 0) > 0:
        gemini_stats["quests_completed"] = extra_stats.get('quests_completed', 0)
        gemini_stats["quest_days"] = extra_stats.get('total_quest_days', 0)
    if extra_stats.get('games_played', 0) > 0:
        gemini_stats["games_played"] = extra_stats.get('games_played', 0)
        gemini_stats["win_rate"] = (extra_stats.get('games_won', 0) / extra_stats.get('games_played', 1) * 100)

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

# --- REFACTORED: Admin Commands using a class-based approach ---
@app_commands.check(is_admin_or_authorised)
class AdminGroup(app_commands.Group):
    """Admin-Befehle zur Verwaltung des Bots."""

    @app_commands.command(name="view_wrapped", description="Zeigt eine Vorschau des 'Wrapped' für einen Benutzer an.")
    @app_commands.describe(user="Der Benutzer, dessen Wrapped du ansehen möchtest.")
    async def view_wrapped(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(ephemeral=True)
        
        # --- FIX: Generate the preview for the PREVIOUS month, just like the real event ---
        # This ensures the data is complete and the preview is accurate.
        now = datetime.now(timezone.utc)
        first_day_of_current_month = now.replace(day=1)
        last_month_first_day = (first_day_of_current_month - timedelta(days=1)).replace(day=1)
        stat_period = last_month_first_day.strftime('%Y-%m')
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
            stat_period_date=last_month_first_day,
            all_stats_for_period=all_stats,
            total_users=len(all_stats),
            server_averages=await _calculate_server_averages(all_stats)
        )

        await interaction.followup.send(f"Eine 'Wrapped'-Vorschau für `{stat_period}` wurde an {user.mention} gesendet.", ephemeral=True)

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
        
        # --- FIX: Get Gemini usage from the new detailed table ---
        cnx = db_helpers.db_pool.get_connection()
        gemini_usage = 0
        if cnx:
            cursor = cnx.cursor(dictionary=True)
            try:
                cursor.execute("SELECT SUM(call_count) as total_calls FROM api_usage WHERE usage_date = CURDATE() AND model_name LIKE 'gemini%%'")
                result = cursor.fetchone()
                gemini_usage = result['total_calls'] if result and result['total_calls'] else 0
            finally:
                cursor.close()
                cnx.close()

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

    @app_commands.command(name="deletememory", description="Löscht das 'Gedächtnis' (Beziehungszusammenfassung) des Bots über einen Benutzer.")
    @app_commands.describe(user="Der Benutzer, dessen Gedächtnis gelöscht werden soll.")
    async def deletememory(self, interaction: discord.Interaction, user: discord.Member):
        """Deletes the bot's relationship summary for a specific user."""
        await interaction.response.defer(ephemeral=True)

        try:
            # Setting the summary to NULL in the database effectively deletes it.
            await db_helpers.update_relationship_summary(user.id, None)
            await interaction.followup.send(f"✅ Das Gedächtnis über {user.mention} wurde erfolgreich gelöscht.")
            print(f"--- Admin {interaction.user.name} deleted memory for user {user.name} ({user.id}) ---")
        except Exception as e:
            await interaction.followup.send(f"❌ Fehler beim Löschen des Gedächtnisses: `{e}`")
            print(f"--- Error in /admin deletememory for user {user.id}: {e} ---")

    @app_commands.command(name="dashboard", description="Zeigt den Link zum Web-Dashboard an.")
    async def dashboard(self, interaction: discord.Interaction):
        """Sends the link to the web dashboard, making it accessible on the local network."""
        await interaction.response.defer(ephemeral=True)

        try:
            # Get the local IP address of the machine running the bot
            hostname = socket.gethostname()
            # This gets the primary local IP address
            local_ip = socket.gethostbyname(hostname)
            dashboard_url = f"http://{local_ip}:5000"
            
            message = (
                f"Du kannst das Web-Dashboard hier aufrufen:\n"
                f"**{dashboard_url}**\n\n"
                f"*Hinweis: Dies funktioniert nur, wenn du dich im selben Netzwerk wie der Bot befindest.*"
            )
            await interaction.followup.send(message)

        except Exception as e:
            # Fallback to localhost if IP detection fails for any reason
            dashboard_url = "http://localhost:5000"
            message = f"Konnte die lokale IP-Adresse nicht automatisch ermitteln. Versuche, das Dashboard über den Host-PC hier aufzurufen:\n**{dashboard_url}**\n\n*Fehler: {e}*"
            await interaction.followup.send(message)

    @app_commands.command(name="killvoice", description="[Admin-Gefahr!] Löscht ALLE Sprachkanäle auf dem Server.")
    async def killvoice(self, interaction: discord.Interaction):
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

    @app_commands.command(name="addcurrency", description="[Test] Füge einem Benutzer Währung hinzu.")
    @app_commands.describe(
        user="Der Benutzer, der Währung erhalten soll",
        amount="Menge der Währung (kann negativ sein)"
    )
    async def addcurrency(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        """Adds currency to a user's balance for testing purposes."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            stat_period = datetime.now(timezone.utc).strftime('%Y-%m')
            await db_helpers.add_balance(
                user.id,
                user.display_name,
                amount,
                config,
                stat_period
            )
            
            new_balance = await db_helpers.get_balance(user.id)
            currency = config['modules']['economy']['currency_symbol']
            
            await interaction.followup.send(
                f"✅ {user.mention} erhielt **{amount} {currency}**\n"
                f"Neues Guthaben: **{new_balance} {currency}**"
            )
            
            logger.info(f"Admin {interaction.user.name} added {amount} currency to {user.name}")
            
        except Exception as e:
            logger.error(f"Error in addcurrency command: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Fehler beim Hinzufügen von Währung: {e}")


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
            # Gemini Models
            discord.SelectOption(label="Gemini 2.5 Pro (Most Capable)", value="gemini:gemini-2.5-pro", emoji="💎"),
            discord.SelectOption(label="Gemini 2.5 Flash (Schnell & Modern)", value="gemini:gemini-2.5-flash", emoji="⚡"),
            discord.SelectOption(label="Gemini 2.0 Flash Exp (Experimental)", value="gemini:gemini-2.0-flash-exp", emoji="🧪"),
            discord.SelectOption(label="Gemini 1.5 Pro (Stabil)", value="gemini:gemini-1.5-pro", emoji="🏆"),
            # OpenAI Models
            discord.SelectOption(label="GPT-5 Nano (Newest Nano)", value="openai:gpt-5-nano", emoji="🆕"),
            discord.SelectOption(label="GPT-5 Mini (Newest Mini)", value="openai:gpt-5-mini", emoji="✨"),
            discord.SelectOption(label="GPT-4.1 Nano (Efficient)", value="openai:gpt-4.1-nano", emoji="⚙️"),
            discord.SelectOption(label="GPT-4o Mini (Schnell)", value="openai:gpt-4o-mini", emoji="🚀"),
            discord.SelectOption(label="GPT-4o (Leistungsstark)", value="openai:gpt-4o", emoji="🧠"),
            discord.SelectOption(label="GPT-4 Turbo", value="openai:gpt-4-turbo", emoji="💨"),
            discord.SelectOption(label="O1 (Reasoning)", value="openai:o1", emoji="🤔"),
            discord.SelectOption(label="O1 Mini", value="openai:o1-mini", emoji="💭"),
            discord.SelectOption(label="O3 Mini", value="openai:o3-mini", emoji="🎯"),
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

# REMOVED: /rank command - functionality integrated into /profile command

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

    # Get user's equipped color or default
    embed_color = await get_user_embed_color(target_user.id, config)

    embed = discord.Embed(
        title=f"Profil von {target_user.display_name}",
        color=embed_color
    )
    embed.set_thumbnail(url=target_user.display_avatar.url)

    # Leveling and Economy
    level = profile_data.get('level', 1)
    xp = profile_data.get('xp', 0)
    xp_for_next_level = get_xp_for_level(level)
    
    # Create a progress bar
    progress = int((xp / xp_for_next_level) * 20) # 20 characters for the bar
    progress_bar = '█' * progress + '░' * (20 - progress)
    
    embed.add_field(name="Level", value=f"**{level}**", inline=True)
    embed.add_field(name="Guthaben", value=f"**{profile_data.get('balance', 0)}** 🪙", inline=True)
    embed.add_field(name="Globaler Rang", value=f"**#{profile_data.get('rank', 'N/A')}**", inline=True)
    embed.add_field(name="XP Fortschritt", value=f"`{xp} / {xp_for_next_level} XP`\n`{progress_bar}`", inline=False)

    # Get equipped color display
    equipped_color = await db_helpers.get_user_equipped_color(target_user.id)
    color_display = equipped_color if equipped_color else "Keine Farbe ausgerüstet"
    embed.add_field(name="🎨 Farbe", value=f"`{color_display}`", inline=True)

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

    # Show purchased items/features
    has_dm = await db_helpers.has_feature_unlock(target_user.id, 'dm_access')
    has_games = await db_helpers.has_feature_unlock(target_user.id, 'games_access')
    
    # Check for individual Werwolf roles
    has_seherin = await db_helpers.has_feature_unlock(target_user.id, 'werwolf_role_seherin')
    has_hexe = await db_helpers.has_feature_unlock(target_user.id, 'werwolf_role_hexe')
    has_dönerstopfer = await db_helpers.has_feature_unlock(target_user.id, 'werwolf_role_dönerstopfer')
    has_jäger = await db_helpers.has_feature_unlock(target_user.id, 'werwolf_role_jäger')
    
    features = []
    if has_dm: features.append("✉️ DM Access")
    if has_games: features.append("🎮 Games Access")
    
    werwolf_roles = []
    if has_seherin: werwolf_roles.append("🔮 Seherin")
    if has_hexe: werwolf_roles.append("🧪 Hexe")
    if has_dönerstopfer: werwolf_roles.append("🌯 Dönerstopfer")
    if has_jäger: werwolf_roles.append("🏹 Jäger")
    
    if werwolf_roles:
        features.append(f"🐺 Werwolf: {', '.join(werwolf_roles)}")
    
    features_text = "\n".join(features) if features else "*Keine Features freigeschaltet.*"
    embed.add_field(name="🎯 Freigeschaltene Features", value=features_text, inline=False)

    # Add pagination view for game stats
    view = ProfilePageView(target_user, config)
    await interaction.followup.send(embed=embed, view=view)


class ProfilePageView(discord.ui.View):
    """View for paginated profile with game stats."""
    
    def __init__(self, user: discord.Member, config: dict):
        super().__init__(timeout=180)
        self.user = user
        self.config = config
    
    @discord.ui.button(label="🐺 Werwolf Stats", style=discord.ButtonStyle.secondary, row=0)
    async def werwolf_stats_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        embed = await self._create_werwolf_stats_embed()
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="🎮 Game Stats", style=discord.ButtonStyle.secondary, row=0)
    async def game_stats_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        embed = await self._create_game_stats_embed()
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def _create_werwolf_stats_embed(self):
        """Create embed with Werwolf-specific stats."""
        profile_data, error = await db_helpers.get_player_profile(self.user.id)
        
        if error or not profile_data:
            return discord.Embed(
                title="Keine Daten",
                description="Keine Werwolf-Statistiken verfügbar.",
                color=discord.Color.red()
            )
        
        wins = profile_data.get('wins', 0)
        losses = profile_data.get('losses', 0)
        total_games = wins + losses
        win_rate = (wins / total_games * 100) if total_games > 0 else 0
        
        embed = discord.Embed(
            title=f"🐺 Werwolf Stats - {self.user.display_name}",
            color=discord.Color.dark_red()
        )
        embed.set_thumbnail(url=self.user.display_avatar.url)
        
        embed.add_field(name="Spiele gesamt", value=f"`{total_games}`", inline=True)
        embed.add_field(name="Siege", value=f"`{wins}`", inline=True)
        embed.add_field(name="Niederlagen", value=f"`{losses}`", inline=True)
        embed.add_field(name="Win-Rate", value=f"`{win_rate:.1f}%`", inline=True)
        
        # Progress bar for win rate
        bar_length = 20
        filled = int((win_rate / 100) * bar_length)
        bar = '█' * filled + '░' * (bar_length - filled)
        embed.add_field(name="Win-Rate Fortschritt", value=f"`{bar}`", inline=False)
        
        return embed
    
    async def _create_game_stats_embed(self):
        """Create embed with all game stats (Blackjack, Roulette, Mines, Detective, etc.)."""
        try:
            if not db_helpers.db_pool:
                return discord.Embed(
                    title="Fehler",
                    description="Datenbankverbindung nicht verfügbar.",
                    color=discord.Color.red()
                )
            
            cnx = db_helpers.db_pool.get_connection()
            if not cnx:
                return discord.Embed(
                    title="Fehler",
                    description="Datenbankverbindung fehlgeschlagen.",
                    color=discord.Color.red()
                )
            
            cursor = cnx.cursor(dictionary=True)
            try:
                stat_period = datetime.now(timezone.utc).strftime('%Y-%m')
                cursor.execute(
                    """
                    SELECT games_played, games_won, total_bet, total_won
                    FROM user_stats
                    WHERE user_id = %s AND stat_period = %s
                    """,
                    (self.user.id, stat_period)
                )
                stats = cursor.fetchone()
                
                if not stats:
                    embed = discord.Embed(
                        title=f"🎮 Game Stats - {self.user.display_name}",
                        description="Noch keine Spiele gespielt diesen Monat!",
                        color=discord.Color.blue()
                    )
                    embed.set_thumbnail(url=self.user.display_avatar.url)
                    return embed
                
                games_played = stats['games_played'] or 0
                games_won = stats['games_won'] or 0
                total_bet = stats['total_bet'] or 0
                total_won = stats['total_won'] or 0
                
                win_rate = (games_won / games_played * 100) if games_played > 0 else 0
                net_profit = total_won - total_bet
                
                embed = discord.Embed(
                    title=f"🎮 Game Stats - {self.user.display_name}",
                    description=f"Statistiken für {stat_period}",
                    color=discord.Color.blue()
                )
                embed.set_thumbnail(url=self.user.display_avatar.url)
                
                embed.add_field(name="Spiele gespielt", value=f"`{games_played}`", inline=True)
                embed.add_field(name="Spiele gewonnen", value=f"`{games_won}`", inline=True)
                embed.add_field(name="Win-Rate", value=f"`{win_rate:.1f}%`", inline=True)
                
                currency = self.config['modules']['economy']['currency_symbol']
                embed.add_field(name="Gesamt eingesetzt", value=f"`{total_bet}` {currency}", inline=True)
                embed.add_field(name="Gesamt gewonnen", value=f"`{total_won}` {currency}", inline=True)
                
                profit_color = "🟢" if net_profit >= 0 else "🔴"
                embed.add_field(
                    name="Nettogewinn",
                    value=f"{profit_color} `{net_profit:+d}` {currency}",
                    inline=True
                )
                
                # Win rate progress bar
                bar_length = 20
                filled = int((win_rate / 100) * bar_length)
                bar = '█' * filled + '░' * (bar_length - filled)
                embed.add_field(name="Win-Rate Fortschritt", value=f"`{bar}`", inline=False)
                
                return embed
                
            finally:
                cursor.close()
                cnx.close()
                
        except Exception as e:
            logger.error(f"Error creating game stats embed: {e}", exc_info=True)
            return discord.Embed(
                title="Fehler",
                description=f"Fehler beim Laden der Statistiken: {str(e)}",
                color=discord.Color.red()
            )

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
    # --- FIX: Populate the top artists text ---
    top_artists_text = ""
    for i, (artist, count) in enumerate(artist_counts.most_common(5)):
        top_artists_text += f"**{i+1}.** {artist} (`{count}x`)\n"
    if top_artists_text:
        embed.add_field(name="Top 5 Künstler (All-Time)", value=top_artists_text, inline=False)

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

# --- NEW: Wrapped Registration Commands ---

@tree.command(name="wrapped-register", description="Registriere dich für monatliche Wrapped-Zusammenfassungen.")
async def wrapped_register(interaction: discord.Interaction):
    """Allows users to opt-in to receive Wrapped summaries."""
    await interaction.response.defer(ephemeral=True)
    
    success = await db_helpers.register_for_wrapped(interaction.user.id, interaction.user.display_name)
    
    if success:
        embed = discord.Embed(
            title="✅ Erfolgreich registriert!",
            description="Du wirst ab jetzt monatlich deine persönliche Wrapped-Zusammenfassung per DM erhalten!",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Was ist Wrapped?",
            value="Jeden Monat bekommst du eine personalisierte Zusammenfassung deiner Server-Aktivität:\n"
                  "📊 Nachrichten & Reaktionen\n"
                  "🎤 Voice-Channel Zeit\n"
                  "🎵 Spotify-Statistiken\n"
                  "👥 Server-Bestie & mehr!",
            inline=False
        )
        embed.set_footer(text="Du kannst dich jederzeit mit /wrapped-unregister abmelden.")
        await interaction.followup.send(embed=embed, ephemeral=True)
    else:
        await interaction.followup.send("❌ Ein Fehler ist aufgetreten. Bitte versuche es später erneut.", ephemeral=True)

@tree.command(name="wrapped-unregister", description="Melde dich von den Wrapped-Zusammenfassungen ab.")
async def wrapped_unregister(interaction: discord.Interaction):
    """Allows users to opt-out of receiving Wrapped summaries."""
    await interaction.response.defer(ephemeral=True)
    
    success = await db_helpers.unregister_from_wrapped(interaction.user.id)
    
    if success:
        embed = discord.Embed(
            title="✅ Erfolgreich abgemeldet",
            description="Du wirst keine Wrapped-Zusammenfassungen mehr erhalten.",
            color=discord.Color.orange()
        )
        embed.set_footer(text="Du kannst dich jederzeit wieder mit /wrapped-register anmelden.")
        await interaction.followup.send(embed=embed, ephemeral=True)
    else:
        await interaction.followup.send("❌ Ein Fehler ist aufgetreten. Bitte versuche es später erneut.", ephemeral=True)

@tree.command(name="wrapped-status", description="Überprüfe deinen Wrapped-Registrierungsstatus.")
async def wrapped_status(interaction: discord.Interaction):
    """Shows the user's current Wrapped registration status."""
    await interaction.response.defer(ephemeral=True)
    
    is_registered = await db_helpers.is_registered_for_wrapped(interaction.user.id)
    
    if is_registered:
        embed = discord.Embed(
            title="📊 Wrapped Status",
            description="✅ Du bist **registriert** und wirst Wrapped-Zusammenfassungen erhalten.",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Nächste Wrapped",
            value="Die nächste Zusammenfassung wird in der zweiten Woche des nächsten Monats versendet.",
            inline=False
        )
    else:
        embed = discord.Embed(
            title="📊 Wrapped Status",
            description="❌ Du bist **nicht registriert** und wirst keine Wrapped-Zusammenfassungen erhalten.",
            color=discord.Color.red()
        )
        embed.add_field(
            name="Jetzt registrieren?",
            value="Nutze `/wrapped-register` um dich anzumelden!",
            inline=False
        )
    
    await interaction.followup.send(embed=embed, ephemeral=True)

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

    game = WerwolfGame(game_text_channel, author, original_channel, bot_client=client)
    game.lobby_vc = lobby_vc
    game.category = category
    game.join_message = None # Initialize join_message attribute

    active_werwolf_games[game_text_channel.id] = game
    
    # --- FIX: Add the starter to the game immediately ---
    game.add_player(author)
    
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

    # --- FIX: Add all members currently in the lobby VC to ensure accurate count ---
    if lobby_vc:
        for member in lobby_vc.members:
            if not member.bot and member.id not in game.players:
                game.add_player(member)
    
    # --- FIX: Check if we have enough players (at least 1) ---
    # The game can run with 1 player + bots if configured
    if len(game.players) < 1:
        await game.game_channel.send("Niemand ist beigetreten. Das Spiel wird abgebrochen und die Channels werden aufgeräumt.")
        await game.end_game(config) # Pass config for cleanup
        del active_werwolf_games[game_text_channel.id]
        return

    # Automatically start the game
    # Bot filling logic is now handled inside start_game
    try:
        error_message = await game.start_game(config, GEMINI_API_KEY, OPENAI_API_KEY, db_helpers, ziel_spieler)
        if error_message:
            await game.game_channel.send(error_message)
            del active_werwolf_games[game_text_channel.id]
            await game.lobby_vc.delete(reason="Fehler beim Spielstart")
    except Exception as e:
        # Ensure cleanup on unexpected errors during start
        try:
            await game.game_channel.send(f"Spielstart fehlgeschlagen: {e}. Räume Kanäle auf...")
        except Exception:
            pass
        try:
            await game.end_game(config)
        except Exception:
            pass
        active_werwolf_games.pop(game_text_channel.id, None)

@ww_group.command(name="rules", description="Zeigt die Werwolf-Spielregeln und Rollenbeschreibungen an.")
async def ww_rules(interaction: discord.Interaction):
    """Displays Werwolf game rules and role descriptions."""
    await interaction.response.defer(ephemeral=True)
    
    # Get user's equipped color or default
    embed_color = await get_user_embed_color(interaction.user.id, config)
    
    # Main rules embed
    rules_embed = discord.Embed(
        title="🐺 Werwolf - Spielregeln",
        description="Ein klassisches Deduktionsspiel, in dem Dorfbewohner gegen Werwölfe antreten!",
        color=embed_color
    )
    
    rules_embed.add_field(
        name="📖 Spielablauf",
        value=(
            "**Nachtphase:** Werwölfe wählen ein Opfer. Spezielle Rollen führen ihre Aktionen aus.\n"
            "**Tagesphase:** Das Dorf wacht auf und erfährt, wer gestorben ist. Dann wird abgestimmt, wen man lynchen möchte.\n"
            "Das Spiel endet, wenn entweder alle Werwölfe oder alle Dorfbewohner eliminiert sind."
        ),
        inline=False
    )
    
    rules_embed.add_field(
        name="🎯 Siegbedingungen",
        value=(
            "**Dorfbewohner gewinnen:** Wenn alle Werwölfe eliminiert wurden.\n"
            "**Werwölfe gewinnen:** Wenn sie mindestens so viele Spieler sind wie die Dorfbewohner."
        ),
        inline=False
    )
    
    # Role descriptions embed
    roles_embed = discord.Embed(
        title="🎭 Rollenbeschreibungen",
        color=embed_color
    )
    
    roles_embed.add_field(
        name="🐺 Werwolf",
        value="**Team:** Werwölfe\n**Fähigkeit:** Wählt jede Nacht ein Opfer zum Töten.\n**Aktionen:** `kill <name>` per DM an den Bot",
        inline=False
    )
    
    roles_embed.add_field(
        name="🔮 Seherin",
        value="**Team:** Dorfbewohner\n**Fähigkeit:** Kann jede Nacht die Rolle eines Spielers erfahren.\n**Aktionen:** `see <name>` per DM an den Bot",
        inline=False
    )
    
    roles_embed.add_field(
        name="🧪 Hexe",
        value="**Team:** Dorfbewohner\n**Fähigkeit:** Hat einen Heiltrank (einmalig) und einen Gifttrank (einmalig).\n**Aktionen:** `heal` oder `poison <name>` per DM an den Bot",
        inline=False
    )
    
    roles_embed.add_field(
        name="🥙 Dönerstopfer",
        value="**Team:** Dorfbewohner\n**Fähigkeit:** Kann jede Nacht einen Spieler stumm schalten.\n**Aktionen:** `mute <name>` per DM an den Bot",
        inline=False
    )
    
    roles_embed.add_field(
        name="🏹 Jäger",
        value="**Team:** Dorfbewohner\n**Fähigkeit:** Stirbt der Jäger, darf er noch eine Person mit in den Tod nehmen.\n**Aktionen:** Automatisch beim Tod - du wirst per DM nach deinem Ziel gefragt",
        inline=False
    )
    
    roles_embed.add_field(
        name="👤 Dorfbewohner",
        value="**Team:** Dorfbewohner\n**Fähigkeit:** Keine besonderen Fähigkeiten.\n**Aufgabe:** Diskutiere und stimme ab, um die Werwölfe zu finden!",
        inline=False
    )
    
    # Tips embed
    tips_embed = discord.Embed(
        title="💡 Tipps",
        color=embed_color
    )
    
    tips_embed.add_field(
        name="Für Dorfbewohner",
        value="• Achte auf Widersprüche in Aussagen\n• Nutze Informationen der Seherin weise\n• Koordiniere dich mit anderen Dorfbewohnern",
        inline=True
    )
    
    tips_embed.add_field(
        name="Für Werwölfe",
        value="• Bleibt als Team koordiniert\n• Tarnt euch als normale Dorfbewohner\n• Lenkt Verdacht auf andere",
        inline=True
    )
    
    await interaction.followup.send(embeds=[rules_embed, roles_embed, tips_embed], ephemeral=True)

# --- NEW: Add the voice command group to the tree ---
tree.add_command(voice_group)

# --- NEW: Add the admin command group to the tree ---
tree.add_command(AdminGroup(name="admin"))

# --- NEW: Shop Commands ---
from modules import shop as shop_module

@tree.command(name="shop", description="Öffne den Shop.")
async def shop_main(interaction: discord.Interaction):
    """Unified shop view with interactive purchase."""
    await interaction.response.defer(ephemeral=True)
    
    try:
        # Show shop with interactive buttons
        view = ShopBuyView(interaction.user, config)
        embed = discord.Embed(
            title="🛒 Shop",
            description="Willkommen im Shop! Wähle eine Kategorie aus:",
            color=discord.Color.blue()
        )
        
        currency = config['modules']['economy']['currency_symbol']
        
        # Add info about color roles
        embed.add_field(
            name="🎨 Farbrollen",
            value=f"Kaufe dir eine eigene Farbrollel!\nPreise: Basic ({config['modules']['economy']['shop']['color_roles']['prices']['basic']} {currency}), Premium ({config['modules']['economy']['shop']['color_roles']['prices']['premium']} {currency}), Legendary ({config['modules']['economy']['shop']['color_roles']['prices']['legendary']} {currency})",
            inline=False
        )
        
        # Add info about features
        embed.add_field(
            name="✨ Features",
            value="Schalte spezielle Features frei!",
            inline=False
        )
        
        # Show current balance
        balance = await db_helpers.get_balance(interaction.user.id)
        embed.add_field(
            name="💰 Dein Guthaben",
            value=f"{balance} {currency}",
            inline=False
        )
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    except Exception as e:
        logger.error(f"Error in shop command: {e}", exc_info=True)
        await interaction.followup.send(f"Fehler beim Anzeigen des Shops: {e}", ephemeral=True)


# Remove old /shopbuy command - it's now integrated into /shop


class ShopBuyView(discord.ui.View):
    """Interactive shop purchase interface."""
    
    def __init__(self, member: discord.Member, config: dict):
        super().__init__(timeout=180)
        self.member = member
        self.config = config
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.member.id:
            await interaction.response.send_message("Du kannst diese Auswahl nicht bedienen.", ephemeral=True)
            return False
        return True
    
    @discord.ui.button(label="🎨 Farbrollen", style=discord.ButtonStyle.primary)
    async def color_roles_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show color role options."""
        await interaction.response.defer()
        
        # Create a new view for color tier selection
        view = ColorTierSelectView(self.member, self.config)
        embed = discord.Embed(
            title="🎨 Farbrollen",
            description="Wähle eine Kategorie:",
            color=discord.Color.blue()
        )
        
        currency = self.config['modules']['economy']['currency_symbol']
        prices = self.config['modules']['economy']['shop']['color_roles']['prices']
        
        embed.add_field(name="Basic", value=f"{prices['basic']} {currency}", inline=True)
        embed.add_field(name="Premium", value=f"{prices['premium']} {currency}", inline=True)
        embed.add_field(name="Legendary", value=f"{prices['legendary']} {currency}", inline=True)
        
        await interaction.edit_original_response(embed=embed, view=view)
    
    @discord.ui.button(label="✨ Features", style=discord.ButtonStyle.success)
    async def features_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show feature unlock options."""
        await interaction.response.defer()
        
        view = FeatureSelectView(self.member, self.config)
        embed = discord.Embed(
            title="✨ Feature Unlocks",
            description="Schalte spezielle Features frei!",
            color=discord.Color.green()
        )
        
        currency = self.config['modules']['economy']['currency_symbol']
        features = self.config['modules']['economy']['shop']['features']
        
        # Define detailed feature descriptions
        feature_details = {
            'dm_access': {
                'name': '💬 DM Access',
                'desc': 'Der Bot kann dir private Nachrichten senden.'
            },
            'games_access': {
                'name': '🎮 Games Access',
                'desc': 'Spiele Blackjack, Roulette, Mines und Russian Roulette!'
            }
        }
        
        for feature, price in features.items():
            details = feature_details.get(feature, {'name': feature, 'desc': 'Feature unlock'})
            embed.add_field(
                name=f"{details['name']} - {price} {currency}",
                value=details['desc'],
                inline=False
            )
        
        await interaction.edit_original_response(embed=embed, view=view)
    
    @discord.ui.button(label="⚡ Boosts", style=discord.ButtonStyle.blurple)
    async def boosts_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show temporary boost options."""
        await interaction.response.defer()
        
        view = BoostSelectView(self.member, self.config)
        embed = discord.Embed(
            title="⚡ Temporary Boosts",
            description="Kaufe temporäre Boosts um schneller voranzukommen!",
            color=discord.Color.purple()
        )
        
        currency = self.config['modules']['economy']['currency_symbol']
        boosts = self.config['modules']['economy']['shop']['boosts']
        
        # Define boost descriptions
        boost_details = {
            'xp_boost_1h': {
                'name': '⚡ XP Boost (1 Stunde)',
                'desc': '2x XP für alle Aktivitäten für 1 Stunde'
            },
            'xp_boost_24h': {
                'name': '⚡⚡ XP Boost (24 Stunden)',
                'desc': '2x XP für alle Aktivitäten für 24 Stunden'
            },
            'gambling_multiplier_1h': {
                'name': '🎰 Gambling Boost (1 Stunde)',
                'desc': '1.5x Gewinnmultiplikator für alle Spiele für 1 Stunde'
            },
            'gambling_multiplier_24h': {
                'name': '🎰🎰 Gambling Boost (24 Stunden)',
                'desc': '1.5x Gewinnmultiplikator für alle Spiele für 24 Stunden'
            }
        }
        
        for boost, price in boosts.items():
            details = boost_details.get(boost, {'name': boost, 'desc': 'Temporary boost'})
            embed.add_field(
                name=f"{details['name']} - {price} {currency}",
                value=details['desc'],
                inline=False
            )
        
        await interaction.edit_original_response(embed=embed, view=view)
    
    @discord.ui.button(label="🐺 Werwolf Rollen", style=discord.ButtonStyle.red)
    async def werwolf_roles_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show Werwolf role unlock options."""
        await interaction.response.defer()
        
        view = WerwolfRoleSelectView(self.member, self.config)
        embed = discord.Embed(
            title="🐺 Werwolf Rollen",
            description="Schalte spezielle Rollen für das Werwolf-Spiel frei!",
            color=discord.Color.dark_red()
        )
        
        currency = self.config['modules']['economy']['currency_symbol']
        roles = self.config['modules']['economy']['shop']['werwolf_roles']
        
        # Define role descriptions
        role_details = {
            'seherin': {
                'name': '🔮 Seherin',
                'desc': 'Erfahre jede Nacht die Rolle eines Spielers'
            },
            'hexe': {
                'name': '🧪 Hexe',
                'desc': 'Heile oder vergifte Spieler während der Nacht'
            },
            'dönerstopfer': {
                'name': '🌯 Dönerstopfer',
                'desc': 'Mute einen Spieler während der Diskussion'
            },
            'jäger': {
                'name': '🏹 Jäger',
                'desc': 'Nimm beim Tod einen Spieler mit ins Grab'
            }
        }
        
        for role, price in roles.items():
            details = role_details.get(role, {'name': role, 'desc': 'Werwolf role'})
            embed.add_field(
                name=f"{details['name']} - {price} {currency}",
                value=details['desc'],
                inline=False
            )
        
        await interaction.edit_original_response(embed=embed, view=view)


class ColorTierSelectView(discord.ui.View):
    """View for selecting color tier."""
    
    def __init__(self, member: discord.Member, config: dict):
        super().__init__(timeout=120)
        self.member = member
        self.config = config
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.member.id:
            await interaction.response.send_message("Du kannst diese Auswahl nicht bedienen.", ephemeral=True)
            return False
        return True
    
    @discord.ui.button(label="Basic", style=discord.ButtonStyle.secondary)
    async def basic_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show_colors(interaction, "basic")
    
    @discord.ui.button(label="Premium", style=discord.ButtonStyle.primary)
    async def premium_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show_colors(interaction, "premium")
    
    @discord.ui.button(label="Legendary", style=discord.ButtonStyle.success)
    async def legendary_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show_colors(interaction, "legendary")
    
    async def _show_colors(self, interaction: discord.Interaction, tier: str):
        await interaction.response.defer()
        view = ColorSelectView(tier, self.config, self.member)
        embed = shop_module.create_color_selection_embed(tier, self.config)
        await interaction.edit_original_response(embed=embed, view=view)


class FeatureSelectView(discord.ui.View):
    """View for selecting features to purchase."""
    
    def __init__(self, member: discord.Member, config: dict):
        super().__init__(timeout=120)
        self.member = member
        self.config = config
        
        # Create select menu for features
        options = []
        features = config['modules']['economy']['shop']['features']
        feature_info = {
            'dm_access': {
                'name': 'DM Access',
                'description': 'Erlaube dem Bot, dir DMs zu senden'
            },
            'games_access': {
                'name': 'Games Access',
                'description': 'Spiele Blackjack, Roulette & mehr'
            }
        }
        
        for feature, price in features.items():
            info = feature_info.get(feature, {'name': feature, 'description': ''})
            currency = config['modules']['economy']['currency_symbol']
            options.append(
                discord.SelectOption(
                    label=info['name'],
                    value=feature,
                    description=f"{price} {currency} - {info['description']}"[:100]  # Discord has a 100 char limit
                )
            )
        
        select = discord.ui.Select(placeholder="Wähle ein Feature...", options=options)
        select.callback = self.on_feature_select
        self.add_item(select)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.member.id:
            await interaction.response.send_message("Du kannst diese Auswahl nicht bedienen.", ephemeral=True)
            return False
        return True
    
    async def on_feature_select(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        feature = interaction.data['values'][0]
        price = self.config['modules']['economy']['shop']['features'][feature]
        
        try:
            success, message = await shop_module.purchase_feature(
                db_helpers,
                self.member,
                feature,
                price,
                self.config
            )
            
            if success:
                embed = discord.Embed(
                    title="✅ Kauf erfolgreich!",
                    description=message,
                    color=discord.Color.green()
                )
            else:
                embed = discord.Embed(
                    title="❌ Kauf fehlgeschlagen",
                    description=message,
                    color=discord.Color.red()
                )
            
            await interaction.edit_original_response(embed=embed, view=None)
        except Exception as e:
            logger.error(f"Error purchasing feature: {e}", exc_info=True)
            await interaction.followup.send(f"Fehler beim Kauf: {str(e)}", ephemeral=True)


class BoostSelectView(discord.ui.View):
    """View for selecting boosts to purchase."""
    
    def __init__(self, member: discord.Member, config: dict):
        super().__init__(timeout=120)
        self.member = member
        self.config = config
        
        # Create select menu for boosts
        options = []
        boosts = config['modules']['economy']['shop']['boosts']
        boost_info = {
            'xp_boost_1h': {
                'name': 'XP Boost 1h',
                'description': '2x XP für 1 Stunde'
            },
            'xp_boost_24h': {
                'name': 'XP Boost 24h',
                'description': '2x XP für 24 Stunden'
            },
            'gambling_multiplier_1h': {
                'name': 'Gambling Boost 1h',
                'description': '1.5x Gewinnmultiplikator für 1 Stunde'
            },
            'gambling_multiplier_24h': {
                'name': 'Gambling Boost 24h',
                'description': '1.5x Gewinnmultiplikator für 24 Stunden'
            }
        }
        
        for boost, price in boosts.items():
            info = boost_info.get(boost, {'name': boost, 'description': ''})
            currency = config['modules']['economy']['currency_symbol']
            options.append(
                discord.SelectOption(
                    label=info['name'],
                    value=boost,
                    description=f"{price} {currency} - {info['description']}"[:100]
                )
            )
        
        select = discord.ui.Select(placeholder="Wähle einen Boost...", options=options)
        select.callback = self.on_boost_select
        self.add_item(select)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.member.id:
            await interaction.response.send_message("Du kannst diese Auswahl nicht bedienen.", ephemeral=True)
            return False
        return True
    
    async def on_boost_select(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        boost = interaction.data['values'][0]
        price = self.config['modules']['economy']['shop']['boosts'][boost]
        
        # TODO: Implement boost purchase logic in shop module
        # For now, show a placeholder message
        embed = discord.Embed(
            title="🚧 Coming Soon",
            description=f"Boost-System wird bald implementiert!\nGewählter Boost: {boost}",
            color=discord.Color.orange()
        )
        
        await interaction.edit_original_response(embed=embed, view=None)


class WerwolfRoleSelectView(discord.ui.View):
    """View for selecting Werwolf roles to purchase."""
    
    def __init__(self, member: discord.Member, config: dict):
        super().__init__(timeout=120)
        self.member = member
        self.config = config
        
        # Create select menu for Werwolf roles
        options = []
        roles = config['modules']['economy']['shop']['werwolf_roles']
        role_info = {
            'seherin': {
                'name': 'Seherin',
                'description': 'Erfahre jede Nacht eine Rolle'
            },
            'hexe': {
                'name': 'Hexe',
                'description': 'Heile oder vergifte Spieler'
            },
            'dönerstopfer': {
                'name': 'Dönerstopfer',
                'description': 'Mute einen Spieler'
            },
            'jäger': {
                'name': 'Jäger',
                'description': 'Nimm jemanden mit ins Grab'
            }
        }
        
        for role, price in roles.items():
            info = role_info.get(role, {'name': role, 'description': ''})
            currency = config['modules']['economy']['currency_symbol']
            options.append(
                discord.SelectOption(
                    label=info['name'],
                    value=role,
                    description=f"{price} {currency} - {info['description']}"[:100]
                )
            )
        
        select = discord.ui.Select(placeholder="Wähle eine Rolle...", options=options)
        select.callback = self.on_role_select
        self.add_item(select)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.member.id:
            await interaction.response.send_message("Du kannst diese Auswahl nicht bedienen.", ephemeral=True)
            return False
        return True
    
    async def on_role_select(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        role = interaction.data['values'][0]
        price = self.config['modules']['economy']['shop']['werwolf_roles'][role]
        
        try:
            # Purchase the role as a feature unlock with special naming
            feature_name = f'werwolf_role_{role}'
            success, message = await shop_module.purchase_feature(
                db_helpers,
                self.member,
                feature_name,
                price,
                self.config
            )
            
            if success:
                embed = discord.Embed(
                    title="✅ Kauf erfolgreich!",
                    description=f"Du hast die Rolle **{role.capitalize()}** freigeschaltet!\nDiese Rolle ist nun im Werwolf-Spiel für dich verfügbar.",
                    color=discord.Color.green()
                )
            else:
                embed = discord.Embed(
                    title="❌ Kauf fehlgeschlagen",
                    description=message,
                    color=discord.Color.red()
                )
            
            await interaction.edit_original_response(embed=embed, view=None)
        except Exception as e:
            logger.error(f"Error purchasing Werwolf role: {e}", exc_info=True)
            await interaction.followup.send(f"Fehler beim Kauf: {str(e)}", ephemeral=True)


class ColorSelectView(discord.ui.View):
    def __init__(self, tier: str, config: dict, member: discord.Member):
        super().__init__(timeout=60)
        self.tier = tier
        self.config = config
        self.member = member
        colors = config['modules']['economy']['shop']['color_roles']
        color_map = {
            'basic': colors['basic_colors'],
            'premium': colors['premium_colors'],
            'legendary': colors['legendary_colors']
        }
        options = []
        for idx, hex_color in enumerate(color_map.get(tier, [])[:25], start=1):
            options.append(discord.SelectOption(label=f"{idx}. {hex_color}", value=hex_color))

        # Create the select menu with the callback
        select = discord.ui.Select(placeholder="Wähle eine Farbe...", options=options)
        select.callback = self.on_color_select
        self.add_item(select)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Only the invoker can interact
        if interaction.user.id != self.member.id:
            await interaction.response.send_message("Du kannst diese Auswahl nicht bedienen.", ephemeral=True)
            return False
        return True

    async def on_color_select(self, interaction: discord.Interaction):
        # Get the select component that triggered this
        select = [item for item in self.children if isinstance(item, discord.ui.Select)][0]
        await interaction.response.defer(ephemeral=True)
        hex_color = select.values[0]
        prices = self.config['modules']['economy']['shop']['color_roles']['prices']
        price = prices.get(self.tier, 0)
        success, message, role = await shop_module.purchase_color_role(db_helpers, interaction.user, hex_color, self.tier, price, self.config)
        await interaction.followup.send(message, ephemeral=True)
        self.stop()



# REMOVED: /balance command - functionality integrated into /profile command

@tree.command(name="daily", description="Hole deine tägliche Belohnung ab.")
async def daily(interaction: discord.Interaction):
    """Claim daily reward."""
    await interaction.response.defer(ephemeral=True)
    
    try:
        from modules.economy import grant_daily_reward
        
        success, amount, message = await grant_daily_reward(
            db_helpers,
            interaction.user.id,
            interaction.user.display_name,
            config
        )
        
        if success:
            embed = discord.Embed(
                title="🎁 Tägliche Belohnung!",
                description=message,
                color=discord.Color.green()
            )
            new_balance = await db_helpers.get_balance(interaction.user.id)
            currency = config['modules']['economy']['currency_symbol']
            embed.add_field(name="Neues Guthaben", value=f"{new_balance} {currency}", inline=True)
        else:
            embed = discord.Embed(
                title="⏰ Bereits abgeholt",
                description=message,
                color=discord.Color.orange()
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        logger.error(f"Error claiming daily reward: {e}", exc_info=True)
        await interaction.followup.send(f"Fehler beim Abholen der Belohnung: {str(e)}", ephemeral=True)


@tree.command(name="transactions", description="Zeigt deine letzten Transaktionen an.")
@app_commands.describe(limit="Anzahl der anzuzeigenden Transaktionen (Standard: 10)")
async def view_transactions(interaction: discord.Interaction, limit: int = 10):
    """View transaction history."""
    await interaction.response.defer(ephemeral=True)
    
    if limit < 1 or limit > 50:
        await interaction.followup.send("Limit muss zwischen 1 und 50 liegen.", ephemeral=True)
        return
    
    try:
        transactions = await db_helpers.get_transaction_history(interaction.user.id, limit)
        
        if not transactions:
            await interaction.followup.send("Keine Transaktionen gefunden.", ephemeral=True)
            return
        
        currency = config['modules']['economy']['currency_symbol']
        embed = discord.Embed(
            title=f"💳 Transaktionsverlauf",
            description=f"Deine letzten {len(transactions)} Transaktionen",
            color=discord.Color.blue()
        )
        
        for trans in transactions:
            trans_type, amount, balance_after, description, created_at = trans
            
            # Format amount with sign
            amount_str = f"+{amount}" if amount > 0 else str(amount)
            
            # Format timestamp
            timestamp = created_at.strftime("%d.%m.%Y %H:%M")
            
            # Create field
            field_name = f"{trans_type} - {timestamp}"
            field_value = f"**{amount_str} {currency}** → Guthaben: {balance_after} {currency}"
            if description:
                field_value += f"\n_{description}_"
            
            embed.add_field(name=field_name, value=field_value, inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        logger.error(f"Error viewing transactions: {e}", exc_info=True)
        await interaction.followup.send(f"Fehler beim Laden der Transaktionen: {str(e)}", ephemeral=True)

# Shop commands registered above


# ============================================================================
# QUEST SYSTEM SLASH COMMANDS
# ============================================================================

class QuestMenuView(discord.ui.View):
    """Interactive menu for viewing quest progress."""
    
    def __init__(self, user_id: int, config: dict):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.config = config
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Du kannst dieses Menü nicht bedienen.", ephemeral=True)
            return False
        return True
    
    @discord.ui.button(label="📋 Tägliche Quests", style=discord.ButtonStyle.primary, row=0)
    async def daily_quests_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show daily quests."""
        await interaction.response.defer()
        
        try:
            # Generate quests for today if they don't exist
            quest_list = await quests.generate_daily_quests(db_helpers, self.user_id, self.config)
            
            if not quest_list:
                # If generation failed, try to fetch existing quests
                quest_list = await quests.get_user_quests(db_helpers, self.user_id, self.config)
            
            if not quest_list:
                await interaction.followup.send("❌ Fehler beim Laden der Quests.", ephemeral=True)
                return
            
            # Create embed showing quests
            embed = quests.create_quests_embed(quest_list, interaction.user.display_name, self.config)
            
            # Check if all quests are completed
            all_completed, completed_count, total_count = await quests.check_all_quests_completed(db_helpers, self.user_id)
            
            if all_completed:
                embed.set_footer(text="✅ Alle Quests abgeschlossen! Klicke auf 'Belohnungen abholen' um sie einzusammeln.")
            else:
                embed.set_footer(text=f"Quest-Fortschritt: {completed_count}/{total_count} abgeschlossen")
            
            await interaction.edit_original_response(embed=embed, view=self)
        except Exception as e:
            logger.error(f"Error in daily quests button: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Fehler: {str(e)}", ephemeral=True)
    
    @discord.ui.button(label="📊 Monatlicher Fortschritt", style=discord.ButtonStyle.secondary, row=0)
    async def monthly_progress_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show monthly progress."""
        await interaction.response.defer()
        
        try:
            completion_days, total_days = await quests.get_monthly_completion_count(db_helpers, self.user_id)
            embed = quests.create_monthly_progress_embed(completion_days, total_days, interaction.user.display_name, self.config)
            await interaction.edit_original_response(embed=embed, view=self)
        except Exception as e:
            logger.error(f"Error in monthly progress button: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Fehler: {str(e)}", ephemeral=True)
    
    @discord.ui.button(label="💰 Belohnungen abholen", style=discord.ButtonStyle.success, row=1)
    async def claim_rewards_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Claim completed quest rewards."""
        await interaction.response.defer()
        
        try:
            # Get user's quests
            quest_list = await quests.get_user_quests(db_helpers, self.user_id, self.config)
            
            if not quest_list:
                await interaction.followup.send("❌ Du hast heute noch keine Quests.", ephemeral=True)
                return
            
            # Find completed but unclaimed quests
            unclaimed_quests = [q for q in quest_list if q['completed'] and not q.get('reward_claimed', False)]
            
            if not unclaimed_quests:
                await interaction.followup.send("❌ Du hast keine abgeschlossenen Quests zum Einsammeln.", ephemeral=True)
                return
            
            # Claim all unclaimed quests
            total_reward = 0
            claimed_count = 0
            
            for quest in unclaimed_quests:
                success, reward, message = await quests.claim_quest_reward(
                    db_helpers,
                    self.user_id,
                    interaction.user.display_name,
                    quest['id'],
                    self.config
                )
                
                if success:
                    total_reward += reward
                    claimed_count += 1
            
            currency = self.config['modules']['economy']['currency_symbol']
            
            if claimed_count > 0:
                embed = discord.Embed(
                    title="✅ Quest-Belohnungen eingesammelt!",
                    description=f"Du hast {claimed_count} Quest(s) abgeschlossen!",
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="Belohnung",
                    value=f"**+{total_reward} {currency}**",
                    inline=False
                )
                
                # Check if all quests are now completed and claimed
                all_completed, completed_count, total_count = await quests.check_all_quests_completed(db_helpers, self.user_id)
                
                if all_completed:
                    # Grant daily completion bonus
                    bonus_success, bonus_amount = await quests.grant_daily_completion_bonus(
                        db_helpers,
                        self.user_id,
                        interaction.user.display_name,
                        self.config
                    )
                    
                    if bonus_success:
                        embed.add_field(
                            name="🎉 Tagesbonus!",
                            value=f"Alle Quests abgeschlossen! **+{bonus_amount} {currency}** Bonus!",
                            inline=False
                        )
                        total_reward += bonus_amount
                        
                        # Check for monthly milestone
                        completion_days, total_days = await quests.get_monthly_completion_count(db_helpers, self.user_id)
                        milestone_reached, milestone_reward, milestone_name = await quests.grant_monthly_milestone_reward(
                            db_helpers,
                            self.user_id,
                            interaction.user.display_name,
                            completion_days,
                            self.config
                        )
                        
                        if milestone_reached:
                            embed.add_field(
                                name=f"🏆 Monatlicher Meilenstein erreicht!",
                                value=f"**{milestone_name}** ({completion_days} Tage)\n**+{milestone_reward} {currency}**",
                                inline=False
                            )
                
                await interaction.edit_original_response(embed=embed, view=self)
            else:
                await interaction.followup.send("❌ Keine Belohnungen konnten eingesammelt werden.", ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in claim rewards button: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Fehler: {str(e)}", ephemeral=True)

@tree.command(name="quests", description="Zeigt deine täglichen Quests an.")
async def view_quests(interaction: discord.Interaction):
    """Display the interactive quest menu."""
    await interaction.response.defer(ephemeral=True)
    
    try:
        # Create menu view
        view = QuestMenuView(interaction.user.id, config)
        
        # Create initial embed
        embed = discord.Embed(
            title="📋 Quest-Menü",
            description="Wähle eine Option aus dem Menü:",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📋 Tägliche Quests",
            value="Zeigt deine heutigen Quests und deren Fortschritt",
            inline=False
        )
        embed.add_field(
            name="📊 Monatlicher Fortschritt",
            value="Zeigt wie viele Tage du diesen Monat Quests abgeschlossen hast",
            inline=False
        )
        embed.add_field(
            name="💰 Belohnungen abholen",
            value="Sammle Belohnungen für abgeschlossene Quests ein",
            inline=False
        )
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error in /quests command: {e}", exc_info=True)
        await interaction.followup.send(f"❌ Fehler beim Laden der Quests: {str(e)}", ephemeral=True)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error in /quests command: {e}", exc_info=True)
        await interaction.followup.send(f"❌ Fehler beim Laden der Quests: {str(e)}", ephemeral=True)


# REMOVED: /questclaim command - functionality exists as a button in /quests command

# REMOVED: /monthly command - functionality exists as a button in /quests command

# --- Game Commands & UI ---
from modules.games import BlackjackGame, RouletteGame, MinesGame, RussianRouletteGame

# Active game states
active_blackjack_games = {}
active_mines_games = {}
active_rr_games = {}


class BlackjackView(discord.ui.View):
    """UI view for Blackjack game with Hit/Stand buttons."""
    
    def __init__(self, game: BlackjackGame, user_id: int):
        super().__init__(timeout=120)
        self.game = game
        self.user_id = user_id
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Das ist nicht dein Spiel!", ephemeral=True)
            return False
        return True
    
    @discord.ui.button(label="Hit", style=discord.ButtonStyle.primary, emoji="🃏")
    async def hit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        self.game.hit()
        
        if not self.game.is_active:
            # Game ended (bust)
            await self._finish_game(interaction)
        else:
            # Update the embed
            embed = self.game.create_embed()
            await interaction.edit_original_response(embed=embed, view=self)
    
    @discord.ui.button(label="Stand", style=discord.ButtonStyle.success, emoji="✋")
    async def stand_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        self.game.stand()
        await self._finish_game(interaction)
    
    async def _finish_game(self, interaction: discord.Interaction):
        """Finishes the game and shows results."""
        result, multiplier = self.game.get_result()
        embed = self.game.create_embed(show_dealer_card=True)
        
        currency = config['modules']['economy']['currency_symbol']
        
        # Calculate winnings
        winnings = int(self.game.bet * multiplier) - self.game.bet
        
        # Update balance
        stat_period = datetime.now(timezone.utc).strftime('%Y-%m')
        await db_helpers.add_balance(
            self.user_id,
            interaction.user.display_name,
            winnings,
            config,
            stat_period
        )
        
        # Get new balance
        new_balance = await db_helpers.get_balance(self.user_id)
        
        # Log transaction
        await db_helpers.log_transaction(
            self.user_id,
            'blackjack',
            winnings,
            new_balance,
            f"Blackjack result: {result}"
        )
        
        # Add result field
        if result == 'blackjack':
            embed.add_field(name="🎉 BLACKJACK!", value=f"Du gewinnst **{int(self.game.bet * multiplier)} {currency}**!", inline=False)
            embed.color = discord.Color.gold()
        elif result == 'win':
            embed.add_field(name="✅ Gewonnen!", value=f"Du gewinnst **{int(self.game.bet * multiplier)} {currency}**!", inline=False)
            embed.color = discord.Color.green()
        elif result == 'lose':
            embed.add_field(name="❌ Verloren!", value=f"Du verlierst **{self.game.bet} {currency}**.", inline=False)
            embed.color = discord.Color.red()
        else:  # push
            embed.add_field(name="🤝 Unentschieden!", value=f"Du bekommst deinen Einsatz zurück: **{self.game.bet} {currency}**", inline=False)
            embed.color = discord.Color.blue()
        
        embed.add_field(name="Neues Guthaben", value=f"{new_balance} {currency}", inline=True)
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        await interaction.edit_original_response(embed=embed, view=self)
        
        # Remove from active games
        if self.user_id in active_blackjack_games:
            del active_blackjack_games[self.user_id]
        
        self.stop()


class MinesView(discord.ui.View):
    """UI view for Mines game with grid buttons."""
    
    def __init__(self, game: MinesGame, user_id: int):
        super().__init__(timeout=300)
        self.game = game
        self.user_id = user_id
        self._build_grid()
    
    def _build_grid(self):
        """Builds the button grid for the mines game."""
        # Discord allows max 5 rows with 5 buttons each (25 total)
        # We need room for the cashout button, so use 4x5 grid (20 cells + 5 buttons in last row)
        
        # Calculate actual grid size to fit Discord limits
        # With cashout button, we can have max 24 grid cells (4 rows of 5, last row has 4 cells + cashout)
        actual_grid_size = min(self.game.grid_size, 5)
        
        button_count = 0
        for row in range(actual_grid_size):
            row_buttons = 0
            for col in range(actual_grid_size):
                # On the last row, leave space for cashout button
                if row == actual_grid_size - 1 and col == actual_grid_size - 1:
                    break  # Skip last cell to make room for cashout
                    
                button = discord.ui.Button(
                    label="⬜",
                    style=discord.ButtonStyle.secondary,
                    custom_id=f"mine_{row}_{col}",
                    row=row
                )
                button.callback = self._create_callback(row, col)
                self.add_item(button)
                button_count += 1
                row_buttons += 1
        
        # Add cashout button in the last row
        cashout_button = discord.ui.Button(
            label="💰 Cash Out",
            style=discord.ButtonStyle.success,
            custom_id="cashout",
            row=actual_grid_size - 1  # Last row
        )
        cashout_button.callback = self._cashout_callback
        self.add_item(cashout_button)
    
    def _create_callback(self, row: int, col: int):
        """Creates a callback for a grid button."""
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("Das ist nicht dein Spiel!", ephemeral=True)
                return
            
            await interaction.response.defer()
            
            continue_game, hit_mine, multiplier = self.game.reveal(row, col)
            
            # Update button appearance
            for item in self.children:
                if hasattr(item, 'custom_id') and item.custom_id == f"mine_{row}_{col}":
                    if hit_mine:
                        item.label = "💣"
                        item.style = discord.ButtonStyle.danger
                    else:
                        item.label = "💎"
                        item.style = discord.ButtonStyle.success
                    item.disabled = True
                    break
            
            if hit_mine:
                # Game over - hit a mine
                await self._end_game(interaction, lost=True)
            elif not continue_game:
                # All safe cells revealed
                await self._end_game(interaction, lost=False)
            else:
                # Update embed and continue
                embed = self.game.create_embed()
                await interaction.edit_original_response(embed=embed, view=self)
        
        return callback
    
    async def _cashout_callback(self, interaction: discord.Interaction):
        """Handles the cashout button."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Das ist nicht dein Spiel!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        winnings, multiplier = self.game.cashout()
        
        if winnings > 0:
            # Update balance
            stat_period = datetime.now(timezone.utc).strftime('%Y-%m')
            profit = winnings - self.game.bet
            await db_helpers.add_balance(
                self.user_id,
                interaction.user.display_name,
                profit,
                config,
                stat_period
            )
            
            # Get new balance
            new_balance = await db_helpers.get_balance(self.user_id)
            
            # Log transaction
            await db_helpers.log_transaction(
                self.user_id,
                'mines',
                profit,
                new_balance,
                f"Mines cashout at {multiplier}x"
            )
            
            currency = config['modules']['economy']['currency_symbol']
            embed = self.game.create_embed()
            embed.color = discord.Color.green()
            embed.add_field(
                name="💰 Ausgezahlt!",
                value=f"Gewinn: **{profit} {currency}** ({multiplier}x)\nNeues Guthaben: {new_balance} {currency}",
                inline=False
            )
            
            # Disable all buttons
            for item in self.children:
                item.disabled = True
            
            await interaction.edit_original_response(embed=embed, view=self)
            
            # Remove from active games
            if self.user_id in active_mines_games:
                del active_mines_games[self.user_id]
            
            self.stop()
    
    async def _end_game(self, interaction: discord.Interaction, lost: bool):
        """Ends the game and shows results."""
        currency = config['modules']['economy']['currency_symbol']
        embed = self.game.create_embed(show_mines=True)
        
        if lost:
            # Lost - deduct bet
            stat_period = datetime.now(timezone.utc).strftime('%Y-%m')
            await db_helpers.add_balance(
                self.user_id,
                interaction.user.display_name,
                -self.game.bet,
                config,
                stat_period
            )
            
            # Get new balance
            new_balance = await db_helpers.get_balance(self.user_id)
            
            # Log transaction
            await db_helpers.log_transaction(
                self.user_id,
                'mines',
                -self.game.bet,
                new_balance,
                "Hit a mine"
            )
            
            embed.color = discord.Color.red()
            embed.add_field(
                name="💥 Mine getroffen!",
                value=f"Verlust: **{self.game.bet} {currency}**\nNeues Guthaben: {new_balance} {currency}",
                inline=False
            )
        else:
            # Won - all safe cells revealed
            winnings = int(self.game.bet * self.game.get_current_multiplier())
            profit = winnings - self.game.bet
            
            stat_period = datetime.now(timezone.utc).strftime('%Y-%m')
            await db_helpers.add_balance(
                self.user_id,
                interaction.user.display_name,
                profit,
                config,
                stat_period
            )
            
            # Get new balance
            new_balance = await db_helpers.get_balance(self.user_id)
            
            # Log transaction
            await db_helpers.log_transaction(
                self.user_id,
                'mines',
                profit,
                new_balance,
                f"Completed all safe cells at {self.game.get_current_multiplier()}x"
            )
            
            embed.color = discord.Color.gold()
            embed.add_field(
                name="🎉 Alle sicheren Felder aufgedeckt!",
                value=f"Gewinn: **{profit} {currency}** ({self.game.get_current_multiplier()}x)\nNeues Guthaben: {new_balance} {currency}",
                inline=False
            )
        
        # Disable all buttons and reveal all mines
        for item in self.children:
            item.disabled = True
        
        await interaction.edit_original_response(embed=embed, view=self)
        
        # Remove from active games
        if self.user_id in active_mines_games:
            del active_mines_games[self.user_id]
        
        self.stop()


@tree.command(name="blackjack", description="Spiele Blackjack!")
@app_commands.describe(bet="Dein Einsatz")
async def blackjack(interaction: discord.Interaction, bet: int):
    """Start a Blackjack game."""
    await interaction.response.defer(ephemeral=True)
    
    user_id = interaction.user.id
    
    # Check if user already has an active game
    if user_id in active_blackjack_games:
        await interaction.followup.send("Du hast bereits ein aktives Blackjack-Spiel!", ephemeral=True)
        return
    
    # Validate bet amount
    min_bet = config['modules']['economy']['games']['blackjack']['min_bet']
    max_bet = config['modules']['economy']['games']['blackjack']['max_bet']
    
    if bet < min_bet or bet > max_bet:
        currency = config['modules']['economy']['currency_symbol']
        await interaction.followup.send(
            f"Ungültiger Einsatz! Minimum: {min_bet} {currency}, Maximum: {max_bet} {currency}",
            ephemeral=True
        )
        return
    
    # Check balance
    balance = await db_helpers.get_balance(user_id)
    if balance < bet:
        currency = config['modules']['economy']['currency_symbol']
        await interaction.followup.send(
            f"Nicht genug Guthaben! Du hast {balance} {currency}, brauchst aber {bet} {currency}.",
            ephemeral=True
        )
        return
    
    # Create game
    game = BlackjackGame(user_id, bet)
    active_blackjack_games[user_id] = game
    
    # Create view
    view = BlackjackView(game, user_id)
    embed = game.create_embed()
    
    await interaction.followup.send(embed=embed, view=view, ephemeral=True)


class RouletteView(discord.ui.View):
    """Interactive view for Roulette with dropdown menus."""
    
    def __init__(self, user_id: int, bet_amount: int):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.bet_amount = bet_amount
        self.bets = []  # List of (bet_type, bet_value) tuples
        
        # Add bet type dropdown
        self.add_item(RouletteBetTypeSelect(self))
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Das ist nicht dein Spiel!", ephemeral=True)
            return False
        return True
    
    @discord.ui.button(label="🎰 Rad drehen", style=discord.ButtonStyle.success, row=2)
    async def spin_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Spin the roulette wheel."""
        await interaction.response.defer()
        
        if not self.bets:
            await interaction.followup.send("❌ Wähle mindestens eine Wette aus!", ephemeral=True)
            return
        
        # Spin the wheel
        result_number = RouletteGame.spin()
        
        # Determine color
        if result_number == 0:
            result_color = "🟢 Grün"
        elif result_number in RouletteGame.RED:
            result_color = "🔴 Rot"
        else:
            result_color = "⚫ Schwarz"
        
        # Calculate winnings for all bets
        total_winnings = 0
        bet_results = []
        
        for bet_type, bet_value in self.bets:
            won, multiplier = RouletteGame.check_bet(result_number, bet_type, bet_value)
            
            if won:
                winnings = self.bet_amount * multiplier - self.bet_amount
                total_winnings += winnings
                bet_results.append(f"✅ {bet_value}: +{winnings} 🪙 ({multiplier}x)")
            else:
                bet_results.append(f"❌ {bet_value}: -{self.bet_amount} 🪙")
        
        # Update balance
        stat_period = datetime.now(timezone.utc).strftime('%Y-%m')
        await db_helpers.add_balance(
            self.user_id,
            interaction.user.display_name,
            total_winnings - (self.bet_amount * len(self.bets)),
            config,
            stat_period
        )
        
        # Get new balance
        new_balance = await db_helpers.get_balance(self.user_id)
        
        # Log transaction
        await db_helpers.log_transaction(
            self.user_id,
            'roulette',
            total_winnings - (self.bet_amount * len(self.bets)),
            new_balance,
            f"Bets: {len(self.bets)}, Result: {result_number}"
        )
        
        # Create result embed
        currency = config['modules']['economy']['currency_symbol']
        embed = discord.Embed(
            title="🎰 Roulette",
            color=discord.Color.green() if total_winnings > 0 else discord.Color.red()
        )
        
        embed.add_field(name="Ergebnis", value=f"**{result_number}** {result_color}", inline=False)
        embed.add_field(name="Deine Wetten", value="\n".join(bet_results), inline=False)
        embed.add_field(
            name="Gesamteinsatz",
            value=f"{self.bet_amount * len(self.bets)} {currency}",
            inline=True
        )
        embed.add_field(
            name="Gesamt-Ergebnis",
            value=f"**{total_winnings - (self.bet_amount * len(self.bets))} {currency}**",
            inline=True
        )
        embed.add_field(name="Neues Guthaben", value=f"{new_balance} {currency}", inline=True)
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        await interaction.edit_original_response(embed=embed, view=self)
        self.stop()


class RouletteBetTypeSelect(discord.ui.Select):
    """Dropdown for selecting bet type."""
    
    def __init__(self, parent_view):
        self.parent_view = parent_view
        
        options = [
            discord.SelectOption(label="🔴 Rot", value="red", description="Setze auf rote Zahlen (2x)"),
            discord.SelectOption(label="⚫ Schwarz", value="black", description="Setze auf schwarze Zahlen (2x)"),
            discord.SelectOption(label="🔢 Ungerade", value="odd", description="Setze auf ungerade Zahlen (2x)"),
            discord.SelectOption(label="🔢 Gerade", value="even", description="Setze auf gerade Zahlen (2x)"),
            discord.SelectOption(label="⬆️ Hoch (19-36)", value="high", description="Zahlen von 19-36 (2x)"),
            discord.SelectOption(label="⬇️ Niedrig (1-18)", value="low", description="Zahlen von 1-18 (2x)"),
            discord.SelectOption(label="🎯 Einzelne Zahl", value="number", description="Wähle eine Zahl 0-36 (35x)")
        ]
        
        super().__init__(
            placeholder="Wähle deine Wette(n)...",
            min_values=1,
            max_values=2,  # Allow up to 2 simultaneous bets
            options=options,
            row=0
        )
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Clear previous bets
        self.parent_view.bets = []
        
        for selection in self.values:
            if selection == "number":
                # For number bets, show a number selector
                await self._show_number_selector(interaction)
                return
            else:
                # For other bets, map them directly
                bet_type_map = {
                    'red': ('color', 'red'),
                    'black': ('color', 'black'),
                    'odd': ('odd_even', 'odd'),
                    'even': ('odd_even', 'even'),
                    'high': ('high_low', 'high'),
                    'low': ('high_low', 'low')
                }
                
                if selection in bet_type_map:
                    self.parent_view.bets.append(bet_type_map[selection])
        
        # Update embed
        embed = discord.Embed(
            title="🎰 Roulette",
            description="Wette ausgewählt! Klicke auf 'Rad drehen' um zu spielen.",
            color=discord.Color.blue()
        )
        
        currency = config['modules']['economy']['currency_symbol']
        bet_descriptions = []
        for bet_type, bet_value in self.parent_view.bets:
            bet_descriptions.append(f"• {bet_value}")
        
        embed.add_field(
            name="Deine Wetten",
            value="\n".join(bet_descriptions),
            inline=False
        )
        embed.add_field(
            name="Einsatz pro Wette",
            value=f"{self.parent_view.bet_amount} {currency}",
            inline=True
        )
        embed.add_field(
            name="Gesamteinsatz",
            value=f"{self.parent_view.bet_amount * len(self.parent_view.bets)} {currency}",
            inline=True
        )
        
        await interaction.edit_original_response(embed=embed, view=self.parent_view)
    
    async def _show_number_selector(self, interaction: discord.Interaction):
        """Show a number selector for specific number bets."""
        # Create a modal for number input
        modal = RouletteNumberModal(self.parent_view)
        await interaction.response.send_modal(modal)


class RouletteNumberModal(discord.ui.Modal, title="Wähle eine Zahl"):
    """Modal for entering a specific number bet."""
    
    number_input = discord.ui.TextInput(
        label="Zahl (0-36)",
        placeholder="Gib eine Zahl zwischen 0 und 36 ein",
        required=True,
        max_length=2
    )
    
    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            number = int(self.number_input.value)
            if number < 0 or number > 36:
                await interaction.response.send_message("❌ Zahl muss zwischen 0 und 36 liegen!", ephemeral=True)
                return
            
            # Add number bet
            self.parent_view.bets = [('number', number)]
            
            # Update embed
            embed = discord.Embed(
                title="🎰 Roulette",
                description="Wette ausgewählt! Klicke auf 'Rad drehen' um zu spielen.",
                color=discord.Color.blue()
            )
            
            currency = config['modules']['economy']['currency_symbol']
            embed.add_field(
                name="Deine Wette",
                value=f"🎯 Zahl {number} (35x Multiplikator)",
                inline=False
            )
            embed.add_field(
                name="Einsatz",
                value=f"{self.parent_view.bet_amount} {currency}",
                inline=True
            )
            
            await interaction.response.edit_message(embed=embed, view=self.parent_view)
            
        except ValueError:
            await interaction.response.send_message("❌ Ungültige Zahl!", ephemeral=True)


@tree.command(name="roulette", description="Spiele Roulette!")
@app_commands.describe(bet="Dein Einsatz pro Wette")
async def roulette(interaction: discord.Interaction, bet: int):
    """Play Roulette with interactive bet selection."""
    await interaction.response.defer(ephemeral=True)
    
    user_id = interaction.user.id
    
    # Validate bet amount
    min_bet = config['modules']['economy']['games']['roulette']['min_bet']
    max_bet = config['modules']['economy']['games']['roulette']['max_bet']
    currency = config['modules']['economy']['currency_symbol']
    
    if bet < min_bet or bet > max_bet:
        await interaction.followup.send(
            f"Ungültiger Einsatz! Minimum: {min_bet} {currency}, Maximum: {max_bet} {currency}",
            ephemeral=True
        )
        return
    
    # Check balance (max 2 bets, so check for 2x bet amount)
    balance = await db_helpers.get_balance(user_id)
    if balance < bet * 2:
        await interaction.followup.send(
            f"Nicht genug Guthaben! Du hast {balance} {currency}, brauchst aber mindestens {bet * 2} {currency} für 2 Wetten.",
            ephemeral=True
        )
        return
    
    # Create view
    view = RouletteView(user_id, bet)
    
    embed = discord.Embed(
        title="🎰 Roulette",
        description="Wähle deine Wette(n) aus dem Dropdown-Menü. Du kannst bis zu 2 Wetten gleichzeitig platzieren!",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="💡 Tipp",
        value="Du kannst mehrere Wetten gleichzeitig platzieren, z.B. Rot + Gerade!",
        inline=False
    )
    embed.add_field(
        name="Einsatz pro Wette",
        value=f"{bet} {currency}",
        inline=True
    )
    
    await interaction.followup.send(embed=embed, view=view, ephemeral=True)





@tree.command(name="mines", description="Spiele Mines!")
@app_commands.describe(bet="Dein Einsatz")
async def mines(interaction: discord.Interaction, bet: int):
    """Start a Mines game."""
    try:
        await interaction.response.defer(ephemeral=True)
        
        user_id = interaction.user.id
        
        # Check if user already has an active game
        if user_id in active_mines_games:
            await interaction.followup.send("Du hast bereits ein aktives Mines-Spiel!", ephemeral=True)
            return
        
        # Validate bet amount
        min_bet = config['modules']['economy']['games']['mines']['min_bet']
        max_bet = config['modules']['economy']['games']['mines']['max_bet']
        currency = config['modules']['economy']['currency_symbol']
        
        if bet < min_bet or bet > max_bet:
            await interaction.followup.send(
                f"Ungültiger Einsatz! Minimum: {min_bet} {currency}, Maximum: {max_bet} {currency}",
                ephemeral=True
            )
            return
        
        # Check balance
        try:
            balance = await db_helpers.get_balance(user_id)
        except Exception as e:
            logger.error(f"Error getting balance for user {user_id} in mines command: {e}")
            await interaction.followup.send(
                "Ein Fehler ist beim Abrufen deines Guthabens aufgetreten. Bitte versuche es später erneut.",
                ephemeral=True
            )
            return
            
        if balance < bet:
            await interaction.followup.send(
                f"Nicht genug Guthaben! Du hast {balance} {currency}, brauchst aber {bet} {currency}.",
                ephemeral=True
            )
            return
        
        # Create game
        grid_size = config['modules']['economy']['games']['mines']['grid_size']
        mine_count = config['modules']['economy']['games']['mines']['mine_count']
        game = MinesGame(user_id, bet, grid_size, mine_count)
        active_mines_games[user_id] = game
        
        # Create view
        view = MinesView(game, user_id)
        embed = game.create_embed()
        embed.add_field(
            name="ℹ️ Anleitung",
            value="Klicke auf Felder um sie aufzudecken. Vermeide die Minen! Cash out jederzeit für den aktuellen Multiplikator.",
            inline=False
        )
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    except Exception as e:
        logger.error(f"Unexpected error in mines command: {e}", exc_info=True)
        try:
            await interaction.followup.send(
                "Ein unerwarteter Fehler ist aufgetreten. Bitte versuche es später erneut.",
                ephemeral=True
            )
        except:
            pass  # Interaction might already have been responded to


class RussianRouletteView(discord.ui.View):
    """UI view for Russian Roulette game with Shoot and Cash Out buttons."""
    
    def __init__(self, game: RussianRouletteGame, user_id: int, entry_fee: int):
        super().__init__(timeout=180)
        self.game = game
        self.user_id = user_id
        self.entry_fee = entry_fee
        self.results = []
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Das ist nicht dein Spiel!", ephemeral=True)
            return False
        return True
    
    @discord.ui.button(label="🔫 Shoot", style=discord.ButtonStyle.danger)
    async def shoot_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        alive, won, reward = self.game.pull_trigger()
        
        if not alive:
            # Player died
            self.results.append(f"**Schuss {self.game.current_shot}:** 💀 BANG!")
            await self._end_game(interaction, died=True)
        elif won:
            # Player survived all 6 shots
            self.results.append(f"**Schuss {self.game.current_shot}:** ✅ Click...")
            await self._end_game(interaction, died=False, survived_all=True, reward=reward)
        else:
            # Continue game
            self.results.append(f"**Schuss {self.game.current_shot}:** ✅ Click...")
            
            # Calculate progressive multiplier
            multiplier = 1.0 + (self.game.current_shot / 6.0) * 1.5
            potential_win = int(self.entry_fee * multiplier)
            
            embed = self._create_embed(potential_win)
            await interaction.edit_original_response(embed=embed, view=self)
    
    @discord.ui.button(label="💰 Cash Out", style=discord.ButtonStyle.success)
    async def cashout_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        # Calculate cashout amount
        multiplier = 1.0 + (self.game.current_shot / 6.0) * 1.5
        winnings = int(self.entry_fee * multiplier)
        
        await self._end_game(interaction, died=False, cashed_out=True, reward=winnings)
    
    def _create_embed(self, potential_win: int):
        """Creates the game embed."""
        currency = config['modules']['economy']['currency_symbol']
        embed = discord.Embed(
            title="🔫 Russian Roulette",
            description="Ziehst du den Abzug oder nimmst du das Geld?",
            color=discord.Color.orange()
        )
        
        embed.add_field(name="Einsatz", value=f"{self.entry_fee} {currency}", inline=True)
        embed.add_field(name="Schüsse abgefeuert", value=f"{self.game.current_shot}/6", inline=True)
        embed.add_field(name="Aktueller Gewinn", value=f"{potential_win} {currency}", inline=True)
        
        if self.results:
            embed.add_field(name="Ergebnis", value="\n".join(self.results), inline=False)
        
        return embed
    
    async def _end_game(self, interaction: discord.Interaction, died: bool = False, survived_all: bool = False, cashed_out: bool = False, reward: int = 0):
        """Ends the game and shows results."""
        currency = config['modules']['economy']['currency_symbol']
        stat_period = datetime.now(timezone.utc).strftime('%Y-%m')
        
        if died:
            # Player died - lost entry fee (already deducted)
            embed = self._create_embed(0)
            embed.color = discord.Color.red()
            embed.add_field(name="Ergebnis", value="\n".join(self.results), inline=False)
            
            new_balance = await db_helpers.get_balance(self.user_id)
            
            # Log transaction
            await db_helpers.log_transaction(
                self.user_id,
                'russian_roulette',
                -self.entry_fee,
                new_balance,
                f"Died on shot {self.game.current_shot}"
            )
            
            embed.add_field(
                name="❌ Du bist tot!",
                value=f"Verlust: **{self.entry_fee} {currency}**\nNeues Guthaben: {new_balance} {currency}",
                inline=False
            )
        elif survived_all:
            # Survived all 6 shots
            embed = self._create_embed(reward)
            embed.color = discord.Color.gold()
            embed.add_field(name="Ergebnis", value="\n".join(self.results), inline=False)
            
            # Award winnings
            await db_helpers.add_balance(
                self.user_id,
                interaction.user.display_name,
                reward,
                config,
                stat_period
            )
            
            new_balance = await db_helpers.get_balance(self.user_id)
            
            # Log transaction
            await db_helpers.log_transaction(
                self.user_id,
                'russian_roulette',
                reward - self.entry_fee,
                new_balance,
                "Survived all 6 shots"
            )
            
            embed.add_field(
                name="🎉 Du hast überlebt!",
                value=f"Gewinn: **{reward} {currency}**\nNeues Guthaben: {new_balance} {currency}",
                inline=False
            )
        elif cashed_out:
            # Cashed out early
            embed = self._create_embed(reward)
            embed.color = discord.Color.green()
            
            # Award winnings
            profit = reward - self.entry_fee
            await db_helpers.add_balance(
                self.user_id,
                interaction.user.display_name,
                reward,
                config,
                stat_period
            )
            
            new_balance = await db_helpers.get_balance(self.user_id)
            
            # Log transaction
            await db_helpers.log_transaction(
                self.user_id,
                'russian_roulette',
                profit,
                new_balance,
                f"Cashed out after {self.game.current_shot} shots"
            )
            
            embed.add_field(
                name="💰 Ausgezahlt!",
                value=f"Gewinn: **{profit} {currency}**\nNeues Guthaben: {new_balance} {currency}",
                inline=False
            )
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        await interaction.edit_original_response(embed=embed, view=self)
        
        # Remove from active games
        if self.user_id in active_rr_games:
            del active_rr_games[self.user_id]
        
        self.stop()


# --- Detective Game ---
from modules import detective_game

# Active detective games
active_detective_games = {}


class DetectiveGameView(discord.ui.View):
    """UI view for Detective/Murder Mystery game."""
    
    def __init__(self, case: detective_game.MurderCase, user_id: int):
        super().__init__(timeout=300)  # 5 minutes to solve
        self.case = case
        self.user_id = user_id
        self.investigated_suspects = set()
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Das ist nicht dein Fall!", ephemeral=True)
            return False
        return True
    
    def create_case_embed(self):
        """Create the main case embed."""
        embed = discord.Embed(
            title=f"🔍 {self.case.case_title}",
            description=self.case.case_description,
            color=discord.Color.dark_blue()
        )
        
        embed.add_field(
            name="📍 Tatort",
            value=self.case.location,
            inline=False
        )
        
        embed.add_field(
            name="💀 Opfer",
            value=self.case.victim,
            inline=False
        )
        
        # Evidence
        if self.case.evidence:
            evidence_text = "\n".join(self.case.evidence)
            embed.add_field(
                name="🔬 Beweise",
                value=evidence_text,
                inline=False
            )
        
        # Hints (codes/clues)
        if hasattr(self.case, 'hints') and self.case.hints:
            hints_text = "\n".join(self.case.hints)
            embed.add_field(
                name="💡 Hinweise",
                value=hints_text,
                inline=False
            )
        
        # Suspects list
        suspects_list = "\n".join([
            f"{i+1}. **{s['name']}** - {s['occupation']}"
            for i, s in enumerate(self.case.suspects)
        ])
        embed.add_field(
            name="👥 Verdächtige",
            value=suspects_list,
            inline=False
        )
        
        embed.set_footer(text="🔍 Untersuche die Verdächtigen und wähle dann den Mörder aus!")
        
        return embed
    
    def create_suspect_embed(self, suspect_index: int):
        """Create embed showing suspect details."""
        suspect = self.case.get_suspect(suspect_index)
        if not suspect:
            return None
        
        embed = discord.Embed(
            title=f"🔍 Untersuchung: {suspect['name']}",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="💼 Beruf", value=suspect['occupation'], inline=True)
        embed.add_field(name="⏰ Alibi", value=suspect['alibi'], inline=True)
        embed.add_field(name="❗ Motiv", value=suspect['motive'], inline=False)
        embed.add_field(
            name="🔎 Verdächtige Details",
            value=suspect['suspicious_details'],
            inline=False
        )
        
        embed.set_footer(text="Zurück zum Fall, um weitere Verdächtige zu untersuchen!")
        
        return embed
    
    @discord.ui.button(label="🔍 Verdächtige 1", style=discord.ButtonStyle.secondary, row=0)
    async def suspect1_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._investigate_suspect(interaction, 0)
    
    @discord.ui.button(label="🔍 Verdächtige 2", style=discord.ButtonStyle.secondary, row=0)
    async def suspect2_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._investigate_suspect(interaction, 1)
    
    @discord.ui.button(label="🔍 Verdächtige 3", style=discord.ButtonStyle.secondary, row=0)
    async def suspect3_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._investigate_suspect(interaction, 2)
    
    @discord.ui.button(label="🔍 Verdächtige 4", style=discord.ButtonStyle.secondary, row=0)
    async def suspect4_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._investigate_suspect(interaction, 3)
    
    async def _investigate_suspect(self, interaction: discord.Interaction, suspect_index: int):
        """Show details about a specific suspect."""
        await interaction.response.defer()
        
        self.investigated_suspects.add(suspect_index)
        embed = self.create_suspect_embed(suspect_index)
        
        # Create a back button view
        back_view = DetectiveBackView(self)
        await interaction.followup.send(embed=embed, view=back_view, ephemeral=True)
    
    @discord.ui.button(label="👈 Zurück zum Fall", style=discord.ButtonStyle.primary, row=1)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Return to main case view."""
        await interaction.response.defer()
        embed = self.create_case_embed()
        await interaction.edit_original_response(embed=embed, view=self)
    
    @discord.ui.button(label="⚖️ Mörder auswählen", style=discord.ButtonStyle.danger, row=1)
    async def accuse_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open suspect selection for accusation."""
        await interaction.response.defer()
        
        # Create accusation view
        accuse_view = DetectiveAccusationView(self.case, self.user_id)
        
        embed = discord.Embed(
            title="⚖️ Wer ist der Mörder?",
            description="Wähle den Verdächtigen aus, den du für schuldig hältst!",
            color=discord.Color.red()
        )
        
        suspects_list = "\n".join([
            f"{i+1}. **{s['name']}** - {s['occupation']}"
            for i, s in enumerate(self.case.suspects)
        ])
        embed.add_field(
            name="Verdächtige",
            value=suspects_list,
            inline=False
        )
        
        await interaction.edit_original_response(embed=embed, view=accuse_view)


class DetectiveBackView(discord.ui.View):
    """Simple view with just a back button."""
    
    def __init__(self, main_view: DetectiveGameView):
        super().__init__(timeout=60)
        self.main_view = main_view
    
    @discord.ui.button(label="👈 Zurück", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        # This just dismisses the suspect detail message
        await interaction.delete_original_response()


class DetectiveAccusationView(discord.ui.View):
    """View for selecting the murderer."""
    
    def __init__(self, case: detective_game.MurderCase, user_id: int):
        super().__init__(timeout=60)
        self.case = case
        self.user_id = user_id
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Das ist nicht dein Fall!", ephemeral=True)
            return False
        return True
    
    @discord.ui.button(label="1", style=discord.ButtonStyle.danger, row=0)
    async def suspect1_accuse(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._make_accusation(interaction, 0)
    
    @discord.ui.button(label="2", style=discord.ButtonStyle.danger, row=0)
    async def suspect2_accuse(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._make_accusation(interaction, 1)
    
    @discord.ui.button(label="3", style=discord.ButtonStyle.danger, row=0)
    async def suspect3_accuse(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._make_accusation(interaction, 2)
    
    @discord.ui.button(label="4", style=discord.ButtonStyle.danger, row=0)
    async def suspect4_accuse(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._make_accusation(interaction, 3)
    
    async def _make_accusation(self, interaction: discord.Interaction, suspect_index: int):
        """Process the player's accusation."""
        await interaction.response.defer()
        
        suspect = self.case.get_suspect(suspect_index)
        is_correct = self.case.is_correct_murderer(suspect_index)
        actual_murderer = self.case.get_suspect(self.case.murderer_index)
        
        currency = config['modules']['economy']['currency_symbol']
        
        if is_correct:
            # Player won!
            reward = config['modules']['economy']['games']['detective']['reward_correct']
            
            await detective_game.grant_reward(
                db_helpers,
                interaction.user.id,
                interaction.user.display_name,
                reward,
                config
            )
            
            await detective_game.log_game_result(
                db_helpers,
                interaction.user.id,
                interaction.user.display_name,
                True
            )
            
            embed = discord.Embed(
                title="✅ Fall gelöst!",
                description=f"**{suspect['name']}** war tatsächlich der Mörder! Du hast den Fall brillant gelöst!",
                color=discord.Color.green()
            )
            embed.add_field(
                name="💰 Belohnung",
                value=f"+{reward} {currency}",
                inline=False
            )
            embed.set_footer(text="Gut gemacht, Detektiv!")
        else:
            # Player lost
            await detective_game.log_game_result(
                db_helpers,
                interaction.user.id,
                interaction.user.display_name,
                False
            )
            
            embed = discord.Embed(
                title="❌ Falsche Anschuldigung!",
                description=f"**{suspect['name']}** war nicht der Mörder...\n\nDer wahre Mörder war **{actual_murderer['name']}**!",
                color=discord.Color.red()
            )
            embed.set_footer(text="Beim nächsten Mal hast du mehr Glück!")
        
        # Clean up active game
        if interaction.user.id in active_detective_games:
            del active_detective_games[interaction.user.id]
        
        await interaction.edit_original_response(embed=embed, view=None)
        self.stop()


@tree.command(name="detective", description="Löse einen Mordfall!")
async def detective(interaction: discord.Interaction):
    """Start a detective murder mystery game."""
    await interaction.response.defer(ephemeral=True)
    
    try:
        user_id = interaction.user.id
        
        # Check if user already has an active game
        if user_id in active_detective_games:
            await interaction.followup.send("Du hast bereits einen aktiven Fall!", ephemeral=True)
            return
        
        # Generate a murder case
        case = await detective_game.generate_murder_case(
            api_helpers,
            config,
            GEMINI_API_KEY,
            OPENAI_API_KEY
        )
        
        # Create game view
        view = DetectiveGameView(case, user_id)
        embed = view.create_case_embed()
        
        # Store active game
        active_detective_games[user_id] = {
            'case': case,
            'view': view,
            'started_at': datetime.now(timezone.utc)
        }
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error starting detective game: {e}", exc_info=True)
        await interaction.followup.send(
            f"❌ Fehler beim Starten des Detektiv-Spiels: {str(e)}",
            ephemeral=True
        )


@tree.command(name="rr", description="Spiele Russian Roulette!")
@app_commands.describe(bet="Einsatz (optional, Standard: 100)")
async def russian_roulette(interaction: discord.Interaction, bet: int = None):
    """Play Russian Roulette."""
    await interaction.response.defer(ephemeral=True)
    
    user_id = interaction.user.id
    
    # Check if user already has an active game
    if user_id in active_rr_games:
        await interaction.followup.send("Du hast bereits ein aktives Russian Roulette Spiel!", ephemeral=True)
        return
    
    default_entry_fee = config['modules']['economy']['games']['russian_roulette']['entry_fee']
    
    # Use custom bet if provided, otherwise use default
    if bet is not None:
        # Validate bet amount
        min_bet = 10
        max_bet = 1000
        if bet < min_bet:
            await interaction.followup.send(
                f"Einsatz zu niedrig! Mindestens {min_bet} {config['modules']['economy']['currency_symbol']} erforderlich.",
                ephemeral=True
            )
            return
        if bet > max_bet:
            await interaction.followup.send(
                f"Einsatz zu hoch! Maximal {max_bet} {config['modules']['economy']['currency_symbol']} erlaubt.",
                ephemeral=True
            )
            return
        entry_fee = bet
    else:
        entry_fee = default_entry_fee
    
    reward_multiplier = config['modules']['economy']['games']['russian_roulette']['reward_multiplier']
    currency = config['modules']['economy']['currency_symbol']
    
    # Check balance
    balance = await db_helpers.get_balance(user_id)
    if balance < entry_fee:
        await interaction.followup.send(
            f"Nicht genug Guthaben! Du brauchst {entry_fee} {currency} zum Spielen.",
            ephemeral=True
        )
        return
    
    # Deduct entry fee
    stat_period = datetime.now(timezone.utc).strftime('%Y-%m')
    await db_helpers.add_balance(
        user_id,
        interaction.user.display_name,
        -entry_fee,
        config,
        stat_period
    )
    
    # Create game
    game = RussianRouletteGame(user_id, entry_fee, reward_multiplier)
    active_rr_games[user_id] = game
    
    # Create view
    view = RussianRouletteView(game, user_id, entry_fee)
    embed = view._create_embed(entry_fee)
    embed.add_field(
        name="ℹ️ Anleitung",
        value="Klicke auf 🔫 Shoot um zu schießen oder auf 💰 Cash Out um auszuzahlen.\nJeder Schuss erhöht deinen potenziellen Gewinn, aber ein Fehlschuss bedeutet den Tod!",
        inline=False
    )
    
    await interaction.followup.send(embed=embed, view=view, ephemeral=True)


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
    # --- ENHANCED DEBUG: Log all incoming messages with more detail ---
    if not message.author.bot and message.content:
        logger.debug(f"[MSG] From: {message.author.name} ({message.author.id}) | Channel: {message.channel} | Content: {message.content[:50]}")
        print(f"[MSG] Received from {message.author.name} in {message.channel}: '{message.content[:50]}...'")
    
    # --- MULTI-INSTANCE GUARD ---
    if SECONDARY_INSTANCE:
        logger.warning(f"[GUARD] SECONDARY_INSTANCE=True, ignoring message from {message.author.name}")
        print(f"[GUARD] SECONDARY_INSTANCE is True - this is a secondary instance, not processing message")
        return  # Secondary instance does not process messages to avoid duplicate replies

    # --- HARD DEDUPLICATION BY MESSAGE ID ---
    if message.id in last_processed_message_ids:
        logger.debug(f"[DEDUP] Duplicate message ID {message.id}, ignoring")
        print(f"[DEDUP] Duplicate message ID detected, skipping")
        return
    last_processed_message_ids.append(message.id)

    # --- SOFT DEDUPLICATION BY (author, content, short time window) ---
    if not message.author.bot:
        key = (message.author.id, message.content.strip())
        # FIX: Use timezone-aware datetime instead of deprecated utcnow()
        now_ts = datetime.now(timezone.utc).timestamp()
        prev_ts = recent_user_message_cache.get(key)
        if prev_ts and (now_ts - prev_ts) < 3:  # Ignore repeats within 3 seconds
            logger.debug(f"[DEDUP] Recent duplicate from {message.author.name}, ignoring (within 3s)")
            print(f"[DEDUP] Duplicate message from {message.author.name} within 3 seconds, skipping")
            return
        recent_user_message_cache[key] = now_ts
    async def run_chatbot(message):
        """Handles the core logic of fetching and sending an AI response."""
        channel_name = f"DM with {message.author.name}" if isinstance(message.channel, discord.DMChannel) else f"#{message.channel.name}"
        logger.info(f"[CHATBOT] Triggered by {message.author.name} in {channel_name}")
        print(f"[CHATBOT] === Starting chatbot handler for {message.author.name} in {channel_name} ===")
        print(f"[CHATBOT] Message content: '{message.content}'")
        
        if not isinstance(message.channel, discord.DMChannel):
            stat_period = datetime.now(timezone.utc).strftime('%Y-%m')
            await log_stat_increment(message.author.id, stat_period, 'sulf_interactions')
        user_prompt = message.content.replace(f"<@{client.user.id}>", "").strip()
        logger.debug(f"[CHATBOT] User prompt after cleanup: '{user_prompt}'")
        print(f"[CHATBOT] Cleaned user prompt: '{user_prompt}'")

        # --- NEW: Vision/image attachment handling ---
        try:
            image_context = await handle_image_attachment(message, config, GEMINI_API_KEY, OPENAI_API_KEY)
            if image_context:
                user_prompt = f"{image_context}\n{user_prompt}".strip()
                logger.debug(f"[CHATBOT] Added image context to prompt")
                print(f"[CHATBOT] Image context added")
        except Exception as _e:
            logger.warning(f"[CHATBOT] Vision error: {_e}")
            print(f"[CHATBOT] [Vision] Skipping image analysis due to error: {_e}")

        # --- NEW: Unknown emoji detection and analysis ---
        try:
            emoji_context = await handle_unknown_emojis_in_message(message, config, GEMINI_API_KEY, OPENAI_API_KEY)
            if emoji_context:
                user_prompt = f"{emoji_context}\n{user_prompt}".strip()
                logger.debug(f"[CHATBOT] Added emoji context to prompt")
                print(f"[CHATBOT] Emoji context added")
        except Exception as _e:
            logger.warning(f"[CHATBOT] Emoji analysis error: {_e}")
            print(f"[CHATBOT] [Emoji] Skipping emoji analysis due to error: {_e}")

        # --- NEW: Add short-term conversation context (2-minute window) ---
        try:
            user_prompt, _ = await enhance_prompt_with_context(message.author.id, message.channel.id, user_prompt)
            logger.debug(f"[CHATBOT] Context enhanced")
            print(f"[CHATBOT] Conversation context enhanced")
        except Exception as _e:
            logger.warning(f"[CHATBOT] Context enhancement error: {_e}")
            print(f"[CHATBOT] [Context] Could not enhance prompt: {_e}")
            
        if not user_prompt:
            logger.info(f"[CHATBOT] Empty prompt after processing, sending empty ping response")
            print(f"[CHATBOT] Empty prompt - sending empty ping response")
            await message.channel.send(config['bot']['chat']['empty_ping_response'])
            return
            
        logger.debug(f"[CHATBOT] Fetching chat history")
        print(f"[CHATBOT] Fetching chat history...")
        history = await get_chat_history(message.channel.id, config['bot']['chat']['max_history_messages'])
        logger.debug(f"[CHATBOT] History fetched: {len(history)} messages")
        print(f"[CHATBOT] Got {len(history)} messages from history")

        # --- FIX: Revert to using the 'typing' context manager which works for DMs and Guilds. ---
        # The asyncio.wait_for will prevent the rate-limiting issue by timing out the AI call.
        try:
            logger.debug(f"[CHATBOT] Starting typing indicator and AI call")
            print(f"[CHATBOT] Calling AI API...")
            async with message.channel.typing():
                # Wait for the AI response, but with a timeout.
                response_text, error_message, updated_history = await asyncio.wait_for(
                    _get_ai_response(history, message, user_prompt),
                    timeout=config.get('api', {}).get('timeout', 30)
                )
            logger.debug(f"[CHATBOT] AI response received: error={error_message is not None}")
            print(f"[CHATBOT] AI call completed - got {'error' if error_message else 'response'}")
        except asyncio.TimeoutError:
            timeout_val = config.get('api', {}).get('timeout', 30)
            logger.error(f"[CHATBOT] AI response timed out after {timeout_val}s")
            print(f"[CHATBOT] [AI] Response for channel {message.channel.id} timed out after {timeout_val} seconds.")
            error_message = "Die Anfrage hat zu lange gedauert. Versuche es später erneut."
            response_text, updated_history = None, None

        if error_message:
            logger.warning(f"[CHATBOT] Sending error message to user: {error_message}")
            print(f"[CHATBOT] Sending error to user: {error_message}")
            await message.channel.send(f"{message.author.mention} {error_message}")
            return

        # --- REFACTORED: Save history and send response after getting it ---
        if response_text:
            logger.info(f"[CHATBOT] Got response, saving to history and sending")
            print(f"[CHATBOT] Response received - saving and sending...")
            print(f"[CHATBOT] Response preview: '{response_text[:100]}...'")
            
            try:
                if len(updated_history) >= 2:
                    # --- FIX: Use updated_history to get the correct user message ---
                    user_message_content = updated_history[-2]['parts'][0]['text']
                    logger.debug(f"[CHATBOT] Saving user message to history")
                    print(f"[CHATBOT] Saving user message to history...")
                    await save_message_to_history(message.channel.id, "user", user_message_content)
                
                logger.debug(f"[CHATBOT] Saving bot response to history")
                print(f"[CHATBOT] Saving bot response to history...")
                await save_message_to_history(message.channel.id, "model", response_text)
                print(f"[CHATBOT] Successfully saved messages to history")
            except Exception as e:
                logger.error(f"[CHATBOT] Failed to save to history: {e}", exc_info=True)
                print(f"[CHATBOT] Error saving to history: {e}")
                # Continue anyway - we still want to send the response

            # --- NEW: Persist conversation snippet for quick follow-up ---
            try:
                await save_ai_conversation(message.author.id, message.channel.id, message.content, response_text)
            except Exception as _e:
                logger.warning(f"[CHATBOT] Conversation save failed: {_e}")
                print(f"[CHATBOT] [Conversation] Save failed: {_e}")

            update_interval = config['bot']['chat']['relationship_update_interval'] * 2
            if len(updated_history) > 0 and len(updated_history) % update_interval == 0:
                logger.debug(f"[CHATBOT] Updating relationship summary for {message.author.name}")
                print(f"[CHATBOT] Updating relationship summary for {message.author.name}.")
                provider_to_use_summary = await get_current_provider(config)
                if provider_to_use_summary == 'gemini':
                    await db_helpers.increment_gemini_usage()
                temp_config_summary = config.copy()
                temp_config_summary['api']['provider'] = provider_to_use_summary
                new_summary, _ = await get_relationship_summary_from_api(updated_history, message.author.display_name, await get_relationship_summary(message.author.id), temp_config_summary, GEMINI_API_KEY, OPENAI_API_KEY)
                if new_summary:
                    await update_relationship_summary(message.author.id, new_summary)

            logger.debug(f"[CHATBOT] Processing emoji tags in response")
            print(f"[CHATBOT] Processing emoji tags...")
            final_response = await replace_emoji_tags(response_text, client)
            logger.info(f"[CHATBOT] Sending response to {message.author.name}")
            print(f"[CHATBOT] Sending response chunks to channel...")
            
            chunks_sent = 0
            for chunk in await split_message(final_response):
                if chunk:
                    try:
                        await message.channel.send(chunk)
                        chunks_sent += 1
                        logger.debug(f"[CHATBOT] Sent chunk {chunks_sent} of {len(chunk)} chars")
                        print(f"[CHATBOT] Sent chunk {chunks_sent} ({len(chunk)} chars)")
                    except Exception as e:
                        logger.error(f"[CHATBOT] Failed to send chunk: {e}", exc_info=True)
                        print(f"[CHATBOT] Error sending chunk: {e}")
                        
            print(f"[CHATBOT] === Response sent successfully to {message.author.name} ({chunks_sent} chunks) ===")
            logger.info(f"[CHATBOT] Sent {chunks_sent} message chunks to {message.author.name}")

            # --- NEW: Track AI usage (model + feature) ---
            try:
                provider_used = await get_current_provider(config)
                if provider_used == 'gemini':
                    model_name = config.get('api', {}).get('gemini', {}).get('model', 'gemini')
                else:
                    model_name = config.get('api', {}).get('openai', {}).get('chat_model', 'openai')
                await track_api_call(model_name, feature="chat", input_tokens=0, output_tokens=0)
            except Exception as _e:
                logger.warning(f"[CHATBOT] AI usage tracking failed: {_e}")
                print(f"[CHATBOT] [AI Usage] Tracking failed: {_e}")

    async def _get_ai_response(history, message, user_prompt):
        """Helper function to encapsulate the API call logic."""
        logger.debug(f"[AI] Fetching relationship summary for {message.author.name}")
        print(f"[AI] Getting relationship summary...")
        relationship_summary = await get_relationship_summary(message.author.id)
        dynamic_system_prompt = config['bot']['system_prompt']
        
        # Add language reminder to prevent language slips
        dynamic_system_prompt += "\n\nREMINDER: Antworte IMMER auf Deutsch! Bleibe in der deutschen Sprache!"
        
        if relationship_summary:
            logger.debug(f"[AI] Adding relationship context to system prompt")
            print(f"[AI] Relationship summary found, adding to prompt")
            dynamic_system_prompt += f"\n\nZusätzlicher Kontext über deine Beziehung zu '{message.author.display_name}': {relationship_summary}"
        
        # --- NEW: Add detailed logging for AI calls ---
        provider_to_use = await get_current_provider(config)
        logger.info(f"[AI] Using provider '{provider_to_use}' for user '{message.author.display_name}'")
        print(f"[AI] Calling provider '{provider_to_use}' for user '{message.author.display_name}'...")
        temp_config = config.copy()
        temp_config['api']['provider'] = provider_to_use
        
        logger.debug(f"[AI] Making API call to {provider_to_use}")
        print(f"[AI] Making API request...")
        response_text, error_message, updated_history = await get_chat_response(
            history, user_prompt, message.author.display_name, dynamic_system_prompt, temp_config, GEMINI_API_KEY, OPENAI_API_KEY
        )
        logger.info(f"[AI] Response from '{provider_to_use}': {'ERROR' if error_message else 'SUCCESS'}")
        print(f"[AI] Received response from '{provider_to_use}'. Error: {error_message is not None}")
        if error_message:
            logger.error(f"[AI] Error message: {error_message}")
            print(f"[AI] Error details: {error_message}")
        return response_text, error_message, updated_history

    # 1. Ignore messages from the bot itself. This is the most important guard to prevent loops.
    if message.author == client.user:
        logger.debug(f"[FILTER] Ignoring message from bot itself")
        print(f"[FILTER] Message from bot itself, skipping")
        return

    # 2. Handle Direct Messages.
    if isinstance(message.channel, discord.DMChannel):
        logger.info(f"[DM] Received DM from {message.author.name}: {message.content[:50]}")
        print(f"[DM] Processing DM from {message.author.name}")
        
        # --- FIX: Ignore DMs from the bot itself (e.g., level-up notifications) ---
        if message.author == client.user:
            logger.debug(f"[FILTER] Ignoring DM from bot itself")
            return
        
        # --- FIX: Check if the user is in an active Werwolf game and handle game commands ---
        # Find if this user is a player in any active game
        user_game = None
        user_player = None
        for game in active_werwolf_games.values():
            if message.author.id in game.players:
                user_game = game
                user_player = game.players[message.author.id]
                break
        
        if user_game and user_player:
            logger.info(f"[WERWOLF DM] User {message.author.name} is in an active Werwolf game")
            print(f"[WERWOLF DM] Processing Werwolf command from {message.author.name}")
            
            # Parse the command
            content = message.content.strip().lower()
            parts = content.split()
            
            if not parts:
                await message.channel.send("Bitte gib einen gültigen Befehl ein.")
                return
            
            command = parts[0]
            
            # Handle Werwolf night actions
            if command == "kill":
                if len(parts) < 2:
                    await message.channel.send("Verwendung: `kill <name>`")
                    return
                target_name = " ".join(parts[1:])
                target_player = user_game.get_player_by_name(target_name)
                if not target_player:
                    await message.channel.send(f"Spieler '{target_name}' nicht gefunden oder bereits tot.")
                    return
                result = await user_game.handle_night_action(user_player, "kill", target_player, config, GEMINI_API_KEY, OPENAI_API_KEY)
                if result:
                    await message.channel.send(result)
                return
                
            elif command == "see":
                if len(parts) < 2:
                    await message.channel.send("Verwendung: `see <name>`")
                    return
                target_name = " ".join(parts[1:])
                target_player = user_game.get_player_by_name(target_name)
                if not target_player:
                    await message.channel.send(f"Spieler '{target_name}' nicht gefunden oder bereits tot.")
                    return
                result = await user_game.handle_night_action(user_player, "see", target_player, config, GEMINI_API_KEY, OPENAI_API_KEY)
                if result:
                    await message.channel.send(result)
                return
                
            elif command == "heal":
                result = await user_game.handle_night_action(user_player, "heal", None, config, GEMINI_API_KEY, OPENAI_API_KEY)
                if result:
                    await message.channel.send(result)
                else:
                    await message.channel.send("Du hast deinen Heiltrank benutzt.")
                return
                
            elif command == "poison":
                if len(parts) < 2:
                    await message.channel.send("Verwendung: `poison <name>`")
                    return
                target_name = " ".join(parts[1:])
                target_player = user_game.get_player_by_name(target_name)
                if not target_player:
                    await message.channel.send(f"Spieler '{target_name}' nicht gefunden oder bereits tot.")
                    return
                result = await user_game.handle_night_action(user_player, "poison", target_player, config, GEMINI_API_KEY, OPENAI_API_KEY)
                if result:
                    await message.channel.send(result)
                else:
                    await message.channel.send(f"Du hast {target_player.user.display_name} vergiftet.")
                return
                
            elif command == "mute":
                if len(parts) < 2:
                    await message.channel.send("Verwendung: `mute <name>`")
                    return
                target_name = " ".join(parts[1:])
                target_player = user_game.get_player_by_name(target_name)
                if not target_player:
                    await message.channel.send(f"Spieler '{target_name}' nicht gefunden oder bereits tot.")
                    return
                result = await user_game.handle_night_action(user_player, "mute", target_player, config, GEMINI_API_KEY, OPENAI_API_KEY)
                if result:
                    await message.channel.send(result)
                else:
                    await message.channel.send(f"Du wirst {target_player.user.display_name} morgen das Maul stopfen.")
                return
            
            # If we get here, it's not a recognized game command, treat as chatbot
            logger.info(f"[DM] Unrecognized Werwolf command, treating as chatbot message")
            print(f"[DM] Not a Werwolf command, running chatbot handler")
        
        # If it's not a game command, treat it as a chatbot message.
        logger.info(f"[DM] Triggering chatbot for DM from {message.author.name}")
        print(f"[DM] Running chatbot handler for DM")
        await run_chatbot(message)
        return

    # 3. Handle messages in Guild Text Channels.
    if isinstance(message.channel, discord.TextChannel):
        logger.debug(f"[GUILD] Processing guild message from {message.author.name}")
        print(f"[GUILD] Guild message from {message.author.name} in #{message.channel.name}")
        
        # Ignore any messages in active Werwolf game channels to prevent interference.
        if message.channel.id in active_werwolf_games:
            logger.debug(f"[FILTER] Ignoring message in Werwolf game channel")
            print(f"[FILTER] Message in Werwolf game channel, skipping")
            return

        # Determine if the message is a trigger for the chatbot.
        is_pinged = client.user in message.mentions
        message_lower = message.content.lower()
        is_name_used = any(name in message.content.lower().split() for name in config['bot']['names'])
        is_chatbot_trigger = is_pinged or is_name_used
        
        # Enhanced logging for trigger detection
        logger.debug(f"[TRIGGER] is_pinged={is_pinged}, is_name_used={is_name_used}, trigger={is_chatbot_trigger}")
        logger.debug(f"[TRIGGER] Bot names in config: {config['bot']['names']}")
        logger.debug(f"[TRIGGER] Message words: {message.content.lower().split()}")
        print(f"[TRIGGER] Chatbot trigger check: pinged={is_pinged}, name_used={is_name_used}, final={is_chatbot_trigger}")

        # --- CRITICAL FIX: Prioritize the chatbot trigger. ---
        # If the message is a chatbot trigger, run the chatbot logic and IMMEDIATELY stop.
        # This prevents the leveling system from also running and sending a DM that would re-trigger the bot.
        if is_chatbot_trigger:
            logger.info(f"[TRIGGER] Chatbot triggered by {message.author.name}")
            print(f"[TRIGGER] Chatbot TRIGGERED - running chatbot handler")
            await run_chatbot(message)
            return
        else:
            logger.debug(f"[TRIGGER] Chatbot NOT triggered - message will be processed for XP only")
            print(f"[TRIGGER] Chatbot NOT triggered - continuing to XP processing")

        # If it was NOT a chatbot trigger, then we can safely run the leveling system and other stats logging.
        if not message.content.startswith('/'):
            # --- FIX: Correct the typo from 'custom_emojies' to 'custom_emojis' ---
            stat_period = datetime.now(timezone.utc).strftime('%Y-%m')
            custom_emojis = re.findall(r'<a?:(\w+):\d+>', message.content)
            await db_helpers.log_message_stat(message.author.id, message.channel.id, custom_emojis, stat_period)
            
            # --- NEW: Track message quest progress ---
            try:
                quest_completed, _ = await quests.update_quest_progress(db_helpers, message.author.id, 'messages', 1)
                # Only notify on quest completion, not on every message
            except Exception as e:
                logger.error(f"Error updating message quest progress: {e}", exc_info=True)
            
            # --- NEW: Track daily_media quest (images/videos) ---
            if message.attachments:
                has_media = any(
                    attachment.content_type and (
                        attachment.content_type.startswith('image/') or 
                        attachment.content_type.startswith('video/')
                    )
                    for attachment in message.attachments
                )
                if has_media:
                    try:
                        quest_completed, _ = await quests.update_quest_progress(db_helpers, message.author.id, 'daily_media', 1)
                    except Exception as e:
                        logger.error(f"Error updating daily_media quest progress: {e}", exc_info=True)

            new_level = await grant_xp(message.author.id, message.author.display_name, db_helpers.add_xp, config)
            if new_level:
                bonus = calculate_level_up_bonus(new_level, config)
                await db_helpers.add_balance(message.author.id, message.author.display_name, bonus, config, stat_period)
                try:
                    await message.author.send(
                        f"GG! Du bist durch das Schreiben von Nachrichten jetzt Level **{new_level}**! :YESS:\n"
                        f"Du erhältst **{bonus}** Währung als Belohnung!"
                    )
                except discord.Forbidden:
                    print(f"Could not send level up DM to {message.author.name} (DMs likely closed).")
        
        # After all possible actions for a guild message are done, we exit.
        return

    # 4. Fallback for any other channel types (e.g., threads) to prevent any processing.
    return


# ============================================================================
# REACTION EVENT HANDLERS - Quest Progress Tracking
# ============================================================================

@client.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    """Track reactions for quest progress."""
    # Ignore bot reactions
    if payload.user_id == client.user.id:
        return
    
    # Ignore reactions from bots
    try:
        user = await client.fetch_user(payload.user_id)
        if user.bot:
            return
    except discord.DiscordException as e:
        logger.warning(f"Could not fetch user {payload.user_id}: {e}")
        return
    
    # Track reaction quest progress
    try:
        quest_completed, _ = await quests.update_quest_progress(db_helpers, payload.user_id, 'reactions', 1)
        # Quest completion notifications will be sent when user checks /quests or uses /questclaim
    except Exception as e:
        logger.error(f"Error updating reaction quest progress: {e}", exc_info=True)


# --- GRACEFUL SHUTDOWN HANDLER ---
async def graceful_shutdown(signal_name=None):
    """Handle graceful shutdown of the bot."""
    if signal_name:
        logger.info(f"Received {signal_name}, shutting down gracefully...")
        print(f"\n[Shutdown] Received {signal_name}, shutting down gracefully...")
    else:
        logger.info("Shutting down gracefully...")
        print("\n[Shutdown] Shutting down gracefully...")
    
    try:
        # Set status to offline/invisible
        logger.info("Setting Discord status to offline...")
        print("[Shutdown] Setting Discord status to offline...")
        await client.change_presence(status=discord.Status.offline)
        await asyncio.sleep(1)  # Give Discord time to update the status
        
        # Close the bot connection
        logger.info("Closing Discord connection...")
        print("[Shutdown] Closing Discord connection...")
        await client.close()
        
        # Clean up lock file
        if not SECONDARY_INSTANCE and os.path.exists(INSTANCE_LOCK_FILE):
            try:
                os.remove(INSTANCE_LOCK_FILE)
                logger.info("Removed instance lock file")
                print("[Shutdown] Removed instance lock file")
            except Exception as e:
                logger.warning(f"Failed to remove lock file: {e}")
                print(f"[Shutdown] Warning: Failed to remove lock file: {e}")
        
        logger.info("Bot shutdown complete.")
        print("[Shutdown] Bot shutdown complete.")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
        print(f"[Shutdown] Error during shutdown: {e}")

def signal_handler(sig, frame):
    """Handle SIGINT and SIGTERM signals."""
    signal_name = 'SIGINT' if sig == signal.SIGINT else 'SIGTERM'
    print(f"\n[Signal] Received {signal_name}")
    
    # Schedule the graceful shutdown
    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.create_task(graceful_shutdown(signal_name))
    else:
        asyncio.run(graceful_shutdown(signal_name))

# --- RUN THE BOT ---
if __name__ == "__main__":
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        client.run(DISCORD_BOT_TOKEN)
    except KeyboardInterrupt:
        print("\n[Shutdown] KeyboardInterrupt received.")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        print(f"\n[Shutdown] Fatal error: {e}")
    finally:
        # Ensure we always try to set status to offline
        if not client.is_closed():
            try:
                asyncio.run(graceful_shutdown())
            except Exception as e:
                logger.error(f"Error during final shutdown: {e}")
        
        # Clean up lock file if we haven't already
        if not SECONDARY_INSTANCE and os.path.exists(INSTANCE_LOCK_FILE):
            try:
                os.remove(INSTANCE_LOCK_FILE)
                print("[Shutdown] Cleaned up lock file")
            except Exception as e:
                print(f"[Shutdown] Warning: Failed to remove lock file: {e}")