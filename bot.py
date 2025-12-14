import asyncio
import json
import discord
import random
import os
import subprocess
import socket
import signal
import sys
import math
from collections import deque
import re
from datetime import datetime, timedelta, timezone
from typing import Optional
import aiohttp

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

# --- NEW: Voice Dependencies Check ---
# Check for PyNaCl (required for voice) and provide helpful error message
try:
    import nacl
    VOICE_SUPPORTED = True
except ImportError:
    VOICE_SUPPORTED = False
    logger.warning("PyNaCl not installed - voice features will be disabled")
    print("⚠️  WARNING: PyNaCl is not installed. Voice features will not work.")
    print("To enable voice features, install PyNaCl by running:")
    print("  pip install PyNaCl")
    print("Or reinstall all requirements:")
    print("  pip install -r requirements.txt")
    print("")

# --- NEW: Load environment variables from .env file ---
from dotenv import load_dotenv
load_dotenv()

# --- NEW: Check for py-cord vs discord.py compatibility ---
# This bot requires discord.py, not py-cord, because it uses app_commands
try:
    from discord import app_commands
except ImportError as e:
    # Check if py-cord is installed instead of discord.py
    try:
        import discord
        # If discord is importable but app_commands is not, likely py-cord
        if hasattr(discord, 'commands') and not hasattr(discord, 'app_commands'):
            try:
                logger.critical("py-cord detected instead of discord.py - app_commands not available")
            except NameError:
                pass  # Logger may not be available yet
            print("\n" + "="*70)
            print("ERROR: Import Error - Wrong Discord Library Installed")
            print("="*70)
            print("")
            print("This bot requires 'discord.py' but you have 'py-cord' installed.")
            print("py-cord uses a different API (discord.commands instead of app_commands).")
            print("")
            print("To fix this issue:")
            print("")
            print("1. Uninstall both libraries (to ensure clean state):")
            print("   pip uninstall -y py-cord discord.py")
            print("")
            print("2. Reinstall the correct library from requirements.txt:")
            print("   pip install -r requirements.txt")
            print("")
            print("3. Restart the bot")
            print("")
            print("See PYCORD_MIGRATION_GUIDE.md for more information.")
            print("="*70)
            exit(1)
        else:
            # Some other import error
            raise e
    except ImportError:
        # discord module itself is not available
        try:
            logger.critical("discord module not found")
        except NameError:
            pass  # Logger may not be available yet
        print("\n" + "="*70)
        print("ERROR: Discord Library Not Installed")
        print("="*70)
        print("")
        print("The discord library is not installed.")
        print("")
        print("To fix this issue:")
        print("   pip install -r requirements.txt")
        print("")
        print("="*70)
        exit(1)
from discord.ext import tasks
from modules.werwolf import WerwolfGame
from modules.api_helpers import get_chat_response, get_relationship_summary_from_api, get_wrapped_summary_from_api, get_game_details_from_api
from modules import api_helpers
from modules import stock_market  # NEW: Stock market system
from modules import news  # NEW: News system
from modules import word_find  # NEW: Word Find game
from modules import quests  # NEW: Quest system for tracking
from modules import wordle  # NEW: Wordle game
from modules import themes  # NEW: Theme system
from modules import horse_racing  # NEW: Horse racing game
from modules import rpg_system  # NEW: RPG system
from modules import sport_betting  # NEW: Sport betting system
from modules import sport_betting_ui_v2 as sport_betting_ui  # NEW: Sport betting UI components (v2)
from modules import focus_timer  # NEW: Focus timer with activity monitoring
from modules import lofi_player  # NEW: Lofi music player
from modules import personality_evolution  # NEW: Personality evolution and learning system
from modules import advanced_ai  # NEW: Advanced AI reasoning and intelligence
from modules.bot_enhancements import (
    handle_image_attachment,
    handle_unknown_emojis_in_message,
    enhance_prompt_with_context,
    save_ai_conversation,
    track_api_call,
    initialize_emoji_system,
    is_contextual_conversation,
    get_enriched_user_context,
)
from discord.ext import tasks as _tasks  # separate alias for new periodic cleanup

# --- CONFIGURATION ---


# !! WARNING: This is the "easy" way, NOT the "safe" way. !!
# !! DO NOT SHARE THIS FILE WITH YOUR KEYS IN IT. !!

# 1. SET these as environment variables
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "").strip().strip('"').strip("'")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
FOOTBALL_DATA_API_KEY = os.environ.get("FOOTBALL_DATA_API_KEY")  # Football-Data.org API key

# --- NEW: Database Configuration ---
# Set these as environment variables for security, or hardcode for testing.
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_USER = os.environ.get("DB_USER", "sulfur_bot_user")
DB_PASS = os.environ.get("DB_PASS", "") # No password is set for this user
DB_NAME = os.environ.get("DB_NAME", "sulfur_bot")

# --- Constants ---
# Discord message length limit is 2000 chars, we reserve some space for formatting
DISCORD_ERROR_MESSAGE_MAX_LENGTH = 1850
# Discord HTTP error code for maximum emoji limit
MAX_EMOJI_LIMIT_ERROR_CODE = 30008

# Dynamic accuracy check for AI responses - prevents hallucinations
ACCURACY_CHECK_TEMPLATE = "ACCURACY CHECK: You are currently responding to '{user_name}'. Check the message history carefully - each message shows who said what. ONLY reference things that are explicitly visible in the provided conversation history. Do NOT make assumptions about what was said or done."

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
    except (IOError, OSError) as e:
        logger.warning(f"Could not create lock file: {e}")

# In-memory caches for duplicate suppression
last_processed_message_ids = deque(maxlen=500)
recent_user_message_cache = {}  # (user_id, content) -> timestamp

# --- NEW: Import and initialize DB helpers ---
from modules.db_helpers import init_db_pool, initialize_database, apply_pending_migrations, get_leaderboard, add_xp, get_player_rank, get_level_leaderboard, save_message_to_history, get_chat_history, get_relationship_summary, update_relationship_summary, save_bulk_history, clear_channel_history, update_user_presence, add_balance, update_spotify_history, get_all_managed_channels, remove_managed_channel, get_managed_channel_config, update_managed_channel_config, log_message_stat, log_vc_minutes, get_wrapped_stats_for_period, get_user_wrapped_stats, log_stat_increment, get_spotify_history, get_player_profile, cleanup_custom_status_entries, log_mention_reply, log_vc_session, get_wrapped_extra_stats, get_xp_for_level, register_for_wrapped, unregister_from_wrapped, is_registered_for_wrapped, get_wrapped_registrations, get_money_leaderboard, get_games_leaderboard
import modules.db_helpers as db_helpers

# Initialize database pool with error handling and retry logic
db_init_success = False
db_init_max_retries = 3
db_init_retry_delay = 5

for db_attempt in range(1, db_init_max_retries + 1):
    try:
        logger.info(f"Initializing database pool (attempt {db_attempt}/{db_init_max_retries})...")
        print(f"Initializing database pool (attempt {db_attempt}/{db_init_max_retries})...")
        
        if db_helpers.init_db_pool(DB_HOST, DB_USER, DB_PASS, DB_NAME):
            logger.info("Database pool initialized successfully")
            print("Database pool initialized successfully")
            db_init_success = True
            break
        else:
            logger.warning(f"Database pool initialization failed (attempt {db_attempt}/{db_init_max_retries})")
            print(f"WARNING: Database pool initialization failed (attempt {db_attempt}/{db_init_max_retries})")
            
            if db_attempt < db_init_max_retries:
                wait_time = db_init_retry_delay * db_attempt
                logger.info(f"Retrying in {wait_time} seconds...")
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                
    except Exception as e:
        logger.error(f"Failed to initialize database pool (attempt {db_attempt}/{db_init_max_retries}): {e}")
        print(f"ERROR: Failed to initialize database pool (attempt {db_attempt}/{db_init_max_retries}): {e}")
        
        if db_attempt < db_init_max_retries:
            wait_time = db_init_retry_delay * db_attempt
            logger.info(f"Retrying in {wait_time} seconds...")
            print(f"Retrying in {wait_time} seconds...")
            time.sleep(wait_time)

if not db_init_success:
    logger.error("CRITICAL: Failed to initialize database pool after all retries")
    print("=" * 70)
    print("CRITICAL: Failed to initialize database pool after all retries")
    print("=" * 70)
    print("The bot will continue to run but database features will not work.")
    print("Please check:")
    print("  1. MySQL/MariaDB is running")
    print("  2. Database credentials in .env file are correct")
    print("  3. Database 'sulfur_bot' exists")
    print("  4. Network connectivity to database server")
    print("=" * 70)

from modules.level_system import grant_xp
# --- NEW: Import Voice Manager ---
import modules.voice_manager as voice_manager
# --- NEW: Import Economy ---
from modules.economy import calculate_level_up_bonus
# --- NEW: Import Quest System ---
import modules.quests as quests

# --- MODIFIED: Initialize database and apply migrations with better error handling ---
if db_init_success:
    table_init_success = False
    table_init_max_retries = 3
    
    for table_attempt in range(1, table_init_max_retries + 1):
        try:
            logger.info(f"Initializing database tables (attempt {table_attempt}/{table_init_max_retries})...")
            print(f"Initializing database tables (attempt {table_attempt}/{table_init_max_retries})...")
            
            if db_helpers.initialize_database():
                logger.info("Database tables initialized")
                print("Database tables initialized")
                table_init_success = True
                break
            else:
                logger.warning(f"Database table initialization failed (attempt {table_attempt}/{table_init_max_retries})")
                print(f"WARNING: Database table initialization failed (attempt {table_attempt}/{table_init_max_retries})")
                
                if table_attempt < table_init_max_retries:
                    wait_time = 5 * table_attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    print(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    
        except Exception as e:
            logger.error(f"Failed to initialize database tables (attempt {table_attempt}/{table_init_max_retries}): {e}")
            print(f"WARNING: Failed to initialize database tables (attempt {table_attempt}/{table_init_max_retries}): {e}")
            
            if table_attempt < table_init_max_retries:
                wait_time = 5 * table_attempt
                logger.info(f"Retrying in {wait_time} seconds...")
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
    
    if not table_init_success:
        logger.error("WARNING: Failed to initialize database tables after all retries")
        print("WARNING: Failed to initialize database tables after all retries")
        print("The bot will continue to run but may experience issues with database features.")
else:
    logger.warning("Skipping database table initialization (pool not initialized)")
    print("Skipping database table initialization (pool not initialized)")

# Apply pending migrations with error handling
if db_init_success:
    try:
        applied_count, errors = db_helpers.apply_pending_migrations()
        if applied_count > 0:
            logger.info(f"Applied {applied_count} database migrations")
            print(f"Applied {applied_count} database migrations")
        if errors:
            logger.warning(f"{len(errors)} migration errors occurred")
            print(f"WARNING: {len(errors)} migration errors occurred:")
            for error in errors:
                logger.warning(f"Migration error: {error}")
                print(f"  - {error}")
        else:
            logger.info("All database migrations are up to date")
            print("All database migrations are up to date")
    except Exception as e:
        logger.error(f"Failed to apply database migrations: {e}")
        print(f"WARNING: Failed to apply database migrations: {e}")
        print("The bot will continue to run but database schema may be outdated.")
else:
    logger.warning("Skipping database migrations (pool not initialized)")
    print("Skipping database migrations (pool not initialized)")

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
    except discord.errors.NotFound as e:
        # This can happen if the original interaction token expires (after 3 seconds for initial response, 15 minutes for followup).
        # This is normal and expected for slow operations, so only log as debug
        if "Unknown interaction" in str(e):
            logger.debug(f"Interaction {interaction.id} expired before error message could be sent")
        else:
            logger.warning(f"Failed to send error message for interaction {interaction.id}: {e}")
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
    Supports emoji names that start with numbers (e.g., 7161joecool, 4352_DiCaprioLaugh).
    Examples: 
      - <<:name:id>id> -> <:name:id>
      - <<a:name:id>id> -> <a:name:id>
      - `<:name:id>` -> <:name:id> (removes inline code backticks, preserves code blocks)
      - `:emoji:` -> :emoji: (removes backticks from short format too)
    """
    # --- FIX: Handle None input gracefully ---
    if text is None:
        return ""
    
    # Fix pattern like <<:emoji_name:emoji_id>emoji_id> or <<a:emoji_name:emoji_id>emoji_id>
    # Updated to support emoji names starting with numbers ([\w]+)
    text = re.sub(r'<<(a?):([\w]+):(\d+)>\3>', r'<\1:\2:\3>', text)
    # Fix pattern like <<:emoji_name:emoji_id>> or <<a:emoji_name:emoji_id>>
    text = re.sub(r'<<(a?):([\w]+):(\d+)>>', r'<\1:\2:\3>', text)
    # Fix pattern like <:emoji_name:emoji_id>emoji_id or <a:emoji_name:emoji_id>emoji_id (trailing ID)
    text = re.sub(r'<(a?):([\w]+):(\d+)>\3', r'<\1:\2:\3>', text)
    # Remove single backticks around full emoji format (inline code), but not triple backticks (code blocks)
    # Use negative lookbehind and lookahead to avoid matching triple backticks
    text = re.sub(r'(?<!`)`<(a?):([\w]+):(\d+)>`(?!`)', r'<\1:\2:\3>', text)
    # Remove single backticks around short emoji format too (supports numbers at start)
    text = re.sub(r'(?<!`)`:(\w+):`(?!`)', r':\1:', text)
    return text

async def auto_download_emoji(emoji_name, guild, client):
    """
    Attempts to download a missing emoji from a guild and add it to the bot's application emojis.
    
    Args:
        emoji_name: Name of the emoji to find and download
        guild: Guild context to search for the emoji
        client: Discord client instance
    
    Returns:
        The emoji object if successfully added, None otherwise
    """
    try:
        # First, try to find the emoji in the guild
        emoji_obj = None
        if guild:
            emoji_obj = discord.utils.get(guild.emojis, name=emoji_name)
        
        if not emoji_obj:
            logger.debug(f"Emoji '{emoji_name}' not found in guild, cannot auto-download")
            return None
        
        # Check if we already have this emoji as an application emoji
        try:
            app_emojis = await client.fetch_application_emojis()
            for app_emoji in app_emojis:
                if app_emoji.name == emoji_name:
                    logger.debug(f"Emoji '{emoji_name}' already exists as application emoji")
                    return app_emoji
        except Exception as e:
            logger.warning(f"Could not fetch application emojis: {e}")
            return None
        
        # Download the emoji image
        emoji_url = str(emoji_obj.url)
        async with aiohttp.ClientSession() as session:
            async with session.get(emoji_url) as response:
                if response.status != 200:
                    logger.warning(f"Failed to download emoji '{emoji_name}' from {emoji_url}, status: {response.status}")
                    return None
                
                emoji_bytes = await response.read()
        
        # Upload to application emojis
        new_emoji = await client.create_application_emoji(
            name=emoji_name,
            image=emoji_bytes
        )
        
        logger.info(f"Successfully auto-downloaded and added emoji '{emoji_name}' to application emojis")
        print(f"[Emoji] Auto-downloaded '{emoji_name}' to bot's emoji bank")
        return new_emoji
        
    except discord.HTTPException as e:
        if e.code == MAX_EMOJI_LIMIT_ERROR_CODE:  # Maximum number of emojis reached
            logger.warning(f"Cannot add emoji '{emoji_name}': Maximum emoji limit reached")
        else:
            logger.error(f"HTTP error auto-downloading emoji '{emoji_name}': {e}")
        return None
    except Exception as e:
        logger.error(f"Error auto-downloading emoji '{emoji_name}': {e}", exc_info=True)
        return None

async def replace_emoji_tags(text, client, guild=None):
    """
    Replaces :emoji_name: tags with full Discord emoji format <:emoji_name:emoji_id>.
    Keeps existing full format emojis unchanged.
    Prioritizes application emojis (bot's own emojis) over server emojis.
    
    Args:
        text: The text containing emoji tags to replace
        client: The Discord client instance
        guild: Optional guild context. If provided, only uses emojis from this guild + application emojis.
               If None (DM context), only uses application emojis.
    
    This prevents the bot from using emojis from other servers that users cannot see.
    """
    # --- FIX: Handle None input gracefully ---
    if text is None:
        return ""
    
    # First, sanitize any malformed emoji patterns
    text = sanitize_malformed_emojis(text)
    
    # Full format emojis are already correct - don't modify them
    # We only need to convert short format :emoji_name: to full format <:emoji_name:emoji_id>
    
    # Find all :emoji_name: tags that are NOT already in full format
    # Use negative lookbehind to exclude <:name: and <a:name:
    emoji_tags = re.findall(r'(?<!<)(?<!<a):(\w+):', text)
    
    if not emoji_tags:
        return text

    # Build a mapping of emoji names to emoji objects
    # This allows us to get the full emoji format with ID
    emoji_map = {}
    
    # Only add server emojis if a guild context is provided
    if guild:
        for emoji in guild.emojis:
            # Store with exact name and lowercase for case-insensitive matching
            if emoji.name not in emoji_map:
                emoji_map[emoji.name] = emoji
            emoji_map[emoji.name.lower()] = emoji
    
    # Always prioritize application emojis (they work everywhere - DMs and all servers)
    try:
        app_emojis = await client.fetch_application_emojis()
        for emoji in app_emojis:
            emoji_map[emoji.name] = emoji
            emoji_map[emoji.name.lower()] = emoji
    except Exception as e:
        logger.debug(f"Could not fetch application emojis for replacement: {e}")

    # Convert :emoji_name: to full format <:emoji_name:emoji_id>
    replaced_count = 0
    auto_downloaded_count = 0
    for tag in set(emoji_tags):  # Use set to avoid processing duplicates
        emoji_obj = None
        
        # Try exact match first, then lowercase
        if tag in emoji_map:
            emoji_obj = emoji_map[tag]
        elif tag.lower() in emoji_map:
            emoji_obj = emoji_map[tag.lower()]
        
        # If emoji not found and we have a guild context, try to auto-download
        if not emoji_obj and guild:
            try:
                emoji_obj = await auto_download_emoji(tag, guild, client)
                if emoji_obj:
                    auto_downloaded_count += 1
                    # Add to map for future use in this same text
                    emoji_map[emoji_obj.name] = emoji_obj
                    emoji_map[emoji_obj.name.lower()] = emoji_obj
            except Exception as e:
                logger.debug(f"Auto-download failed for emoji '{tag}': {e}")
        
        if emoji_obj:
            # Replace :emoji_name: with full format <:emoji_name:emoji_id> or <a:emoji_name:emoji_id>
            # Check if emoji is animated
            old_format = f":{tag}:"
            if hasattr(emoji_obj, 'animated') and emoji_obj.animated:
                new_format = f"<a:{emoji_obj.name}:{emoji_obj.id}>"
            else:
                new_format = f"<:{emoji_obj.name}:{emoji_obj.id}>"
            text = text.replace(old_format, new_format)
            replaced_count += 1
        else:
            # Log emojis that couldn't be found
            logger.debug(f"Emoji not found: :{tag}:")
    
    if replaced_count > 0:
        logger.debug(f"Converted {replaced_count} emoji tags to full format")
    if auto_downloaded_count > 0:
        logger.info(f"Auto-downloaded {auto_downloaded_count} missing emojis")
    
    return text

def get_embed_color(config_obj):
    """Helper function to parse the hex color from config into a discord.Color object."""
    hex_color = config_obj.get('bot', {}).get('embed_color', '#7289DA') # Default to blurple
    return discord.Color(int(hex_color.lstrip('#'), 16))


def get_nested_config(config_obj, *keys, default=None):
    """
    Safely get a value from nested config dictionaries.
    
    Args:
        config_obj: The config dictionary
        *keys: Path to the nested value (e.g., 'modules', 'economy', 'currency_symbol')
        default: Default value if key path doesn't exist
    
    Returns:
        The value at the nested path or the default value
    
    Example:
        currency = get_nested_config(config, 'modules', 'economy', 'currency_symbol', default='💰')
    """
    # Sentinel value to distinguish missing keys from actual values
    _MISSING = object()
    
    result = config_obj
    for key in keys:
        if isinstance(result, dict):
            result = result.get(key, _MISSING)
            if result is _MISSING:
                return default
        else:
            return default
    return result


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
    
    # --- NEW: Initialize stock market ---
    print("Initializing stock market...")
    await stock_market.initialize_stocks(db_helpers)
    print("Stock market ready!")
    
    # --- NEW: Initialize news system ---
    print("Initializing news system...")
    await news.initialize_news_table(db_helpers)
    print("News system ready!")
    
    # --- NEW: Initialize word find system ---
    print("Initializing word find system...")
    await word_find.initialize_word_find_table(db_helpers)
    print("Word find system ready!")
    
    # --- NEW: Initialize wordle system ---
    print("Initializing wordle system...")
    await wordle.initialize_wordle_table(db_helpers)
    print("Wordle system ready!")
    
    # --- NEW: Initialize theme system ---
    print("Initializing theme system...")
    await themes.initialize_themes_table(db_helpers)
    print("Theme system ready!")
    
    # --- NEW: Initialize horse racing system ---
    print("Initializing horse racing system...")
    await horse_racing.initialize_horse_racing_table(db_helpers)
    print("Horse racing system ready!")
    
    # --- NEW: Initialize RPG system ---
    print("Initializing RPG system...")
    await rpg_system.initialize_rpg_tables(db_helpers)
    await rpg_system.initialize_default_monsters(db_helpers)
    await rpg_system.initialize_shop_items(db_helpers)
    print("RPG system ready!")
    
    # --- NEW: Initialize Sport Betting system ---
    print("Initializing sport betting system...")
    await sport_betting.initialize_sport_betting_tables(db_helpers)
    # Configure Football-Data.org API provider if key is available
    if FOOTBALL_DATA_API_KEY:
        sport_betting.APIProviderFactory.configure("football_data", FOOTBALL_DATA_API_KEY)
        print("Football-Data.org API configured (Champions League, Premier League, World Cup available)")
    else:
        print("Football-Data.org API key not set - only free leagues available")
    # Sync matches from free APIs (OpenLigaDB - no API key required)
    try:
        for league_id in sport_betting.FREE_LEAGUES:
            await sport_betting.sync_league_matches(db_helpers, league_id)
    except Exception as e:
        logger.warning(f"Could not sync sport betting matches on startup: {e}")
    print("Sport betting system ready!")

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
    
    if VOICE_SUPPORTED:
        print("  🎙️  All voice features are ready!")
    else:
        print("  ⚠️  Some voice features may not work correctly")
    
    # --- NEW: Start the background task for voice XP ---
    if not grant_voice_xp.is_running():
        grant_voice_xp.start()
    # --- NEW: Start the background task for presence updates ---
    if not update_presence_task.is_running():
        update_presence_task.start()
    
    # --- NEW: Start personality evolution tasks ---
    if not personality_maintenance_task.is_running():
        personality_maintenance_task.start()
        print("  -> Personality maintenance task started")
    
    if not reflection_task.is_running():
        reflection_task.start()
        print("  -> Daily reflection task started")
    
    # --- NEW: Start the background task for Wrapped event management ---
    if not manage_wrapped_event.is_running():
        manage_wrapped_event.start()
    # --- NEW: Start the background task for empty channel cleanup ---
    if not cleanup_empty_channels.is_running():
        cleanup_empty_channels.start()
    # Start periodic Werwolf category cleanup
    if not cleanup_werwolf_categories.is_running():
        cleanup_werwolf_categories.start()
    
    # --- NEW: Start periodic stock market update ---
    if not update_stock_market.is_running():
        update_stock_market.start()
    
    # --- NEW: Start periodic news generation ---
    if not generate_news.is_running():
        generate_news.start()
    

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
    
    # --- NEW: Start sport betting notifications task ---
    if not sport_betting_notifications_task.is_running():
        sport_betting_notifications_task.start()
        print("  -> Sport betting notifications task started")
    
    # --- NEW: Start sport betting sync and settle task ---
    if not sport_betting_sync_and_settle_task.is_running():
        sport_betting_sync_and_settle_task.start()
        print("  -> Sport betting sync and settle task started")
    

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

# --- NEW: Periodic stock market update ---
@_tasks.loop(minutes=30)
async def update_stock_market():
    """Update stock prices every 30 minutes."""
    try:
        await stock_market.update_stock_prices(db_helpers)
        logger.info("Stock market prices updated")
    except Exception as e:
        logger.error(f"Error updating stock market: {e}", exc_info=True)


# --- NEW: Periodic news generation ---
@_tasks.loop(hours=6)
async def generate_news():
    """Generate news articles every 6 hours."""
    try:
        await news.generate_news_article(db_helpers, api_helpers, config, GEMINI_API_KEY, OPENAI_API_KEY)
        logger.info("News article generated")
    except Exception as e:
        logger.error(f"Error generating news: {e}", exc_info=True)


@update_presence_task.before_loop
async def before_update_presence_task():
    await client.wait_until_ready()

# --- NEW: Autonomous messaging task ---
# Track the last user who was DMed to avoid DMing the same person twice in a row.
# NOTE: Using module-level variable for simplicity. This state is intentionally NOT persisted
# across bot restarts - it's acceptable to potentially DM the same user after a restart.
last_autonomous_dm_user_id = None

# --- NEW: Personality Evolution Maintenance Task ---
@_tasks.loop(hours=6)
async def personality_maintenance_task():
    """Perform periodic personality maintenance and learning decay."""
    try:
        await personality_evolution.perform_personality_maintenance()
        logger.info("Personality maintenance completed")
    except Exception as e:
        logger.error(f"Error in personality maintenance: {e}", exc_info=True)

@personality_maintenance_task.before_loop
async def before_personality_maintenance_task():
    await client.wait_until_ready()

# --- NEW: Reflection Session Task ---
@_tasks.loop(hours=24)
async def reflection_task():
    """Perform daily reflection on bot's personality and interactions."""
    try:
        reflection_summary = await personality_evolution.perform_reflection(get_chat_response)
        if reflection_summary:
            logger.info(f"Reflection completed: {reflection_summary[:100]}...")
    except Exception as e:
        logger.error(f"Error in reflection task: {e}", exc_info=True)

@reflection_task.before_loop
async def before_reflection_task():
    await client.wait_until_ready()
    # Wait a bit before first reflection (let bot gather some data)
    await asyncio.sleep(3600)  # 1 hour

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


async def flush_active_game_time(user_id: int):
    """
    Helper function to flush active game time for quest tracking.
    This is called when a user checks their quests to ensure current game sessions are counted.
    
    Args:
        user_id: The Discord user ID to flush game time for
    
    Returns:
        int: Number of quest minutes logged (rounded up), or 0 if no active session or session < 30s
    
    Note: The timer is reset after flushing to prevent double-counting when the game stops
    or when flush is called again. The time between flushes continues to be tracked normally.
    """
    try:
        if user_id not in game_start_times:
            return 0
        
        game_name, start_time = game_start_times[user_id]
        now = datetime.now(timezone.utc)
        duration_seconds = (now - start_time).total_seconds()
        
        # Only count sessions longer than 30 seconds
        if duration_seconds > 30:
            duration_minutes = duration_seconds / 60.0
            stat_period = now.strftime('%Y-%m')
            
            # Log the game session
            await db_helpers.log_game_session(user_id, stat_period, game_name, duration_minutes)
            
            # Update quest progress
            quest_minutes = math.ceil(duration_minutes)
            await quests.update_quest_progress(db_helpers, user_id, 'game_minutes', quest_minutes, config)
            
            # Reset the start time to now to prevent double-counting
            # The next flush or game stop will only count time from this point forward
            game_start_times[user_id] = (game_name, now)
            
            logger.debug(f"Flushed {duration_minutes:.1f} minutes of {game_name} for user {user_id}")
            return quest_minutes
        
        return 0
    except Exception as e:
        logger.error(f"Error flushing active game time for user {user_id}: {e}", exc_info=True)
        return 0


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
                 
            # --- NEW: Track Spotify activity for bot mind ---
            try:
                duration = (now - spotify_start_times.get(user_id, (None, now))[1]).total_seconds()
                bot_mind.bot_mind.observe_user_activity(
                    user_id,
                    after.display_name,
                    'spotify',
                    {
                        'song': after_spotify.title,
                        'artist': after_spotify.artist,
                        'duration': duration
                    }
                )
            except (AttributeError, Exception) as e:
                logger.debug(f"Could not track Spotify for bot mind: {e}")

        # --- NEW: Game Session Tracking ---
        before_game = next((act for act in before.activities if isinstance(act, discord.Game)), None)
        after_game = next((act for act in after.activities if isinstance(act, discord.Game)), None)

        # Case 1: Game has stopped or changed
        if before_game and (not after_game or after_game.name != before_game.name):
            if user_id in game_start_times and game_start_times[user_id][0] == before_game.name:
                _, start_time = game_start_times.pop(user_id)
                duration_seconds = (now - start_time).total_seconds()
                # Only log sessions longer than 30 seconds to filter out very quick restarts/alt-tabs
                # Reduced from 60 seconds to be more forgiving for quest tracking
                if duration_seconds > 30:
                    duration_minutes = duration_seconds / 60.0
                    stat_period = now.strftime('%Y-%m')
                    await db_helpers.log_game_session(user_id, stat_period, before_game.name, duration_minutes)
                    
                    # --- NEW: Track game minutes for quest progress ---
                    try:
                        import math
                        # Round up to ensure partial minutes count (e.g., 1.5 minutes counts as 2)
                        # This is more player-friendly for quest tracking
                        quest_minutes = math.ceil(duration_minutes)
                        quest_completed, _ = await quests.update_quest_progress(db_helpers, user_id, 'game_minutes', quest_minutes, config)
                        # Quest completion notifications will be sent when user checks /quests or uses /questclaim
                    except Exception as e:
                        logger.error(f"Error updating game quest progress for user {user_id}: {e}", exc_info=True)
                
                print(f"  -> [Game] Session ended for {after.display_name}: '{before_game.name}' after {duration_seconds/60.0:.1f} minutes.")

        # Case 2: A new game has started
        if after_game and (not before_game or before_game.name != after_game.name):
            if user_id not in game_start_times:
                game_start_times[user_id] = (after_game.name, now)
                print(f"  -> [Game] Session started for {after.display_name}: '{after_game.name}'.")
                
                # --- NEW: Track game activity for bot mind ---
                try:
                    bot_mind.bot_mind.observe_user_activity(
                        user_id,
                        after.display_name,
                        'game',
                        {
                            'name': after_game.name,
                            'duration': 0  # Just started
                        }
                    )
                except (AttributeError, Exception) as e:
                    logger.debug(f"Could not track game for bot mind: {e}")
                
                # --- NEW: Focus timer distraction detection for games ---
                try:
                    is_distraction = await focus_timer.detect_game_activity(user_id, after_game.name)
                    if is_distraction:
                        # Send warning DM
                        try:
                            await after.send(
                                f"⚠️ **Focus-Modus aktiv!** Du hast gerade '{after_game.name}' gestartet, aber du solltest fokussiert arbeiten! 🎯",
                                delete_after=15
                            )
                        except discord.Forbidden:
                            pass  # Can't send DM
                except Exception as e:
                    logger.error(f"Error in focus timer game detection: {e}")
        
        # Update game duration tracking for bot mind
        if after_game and user_id in game_start_times:
            try:
                duration = (now - game_start_times[user_id][1]).total_seconds()
                bot_mind.bot_mind.observe_user_activity(
                    user_id,
                    after.display_name,
                    'game',
                    {
                        'name': after_game.name,
                        'duration': duration
                    }
                )
            except (AttributeError, Exception) as e:
                logger.debug(f"Could not update game duration for bot mind: {e}")

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

        # --- NEW: Prioritize non-custom activities and track by type ---
        # Find the most "important" activity to log.
        # Order of importance: Game > Streaming > Watching > Listening (Spotify) > Other Activity > Custom Status
        primary_activity = next((act for act in after.activities if isinstance(act, discord.Game)), None)
        activity_type = "playing"
        
        if not primary_activity:
            # Check for streaming
            primary_activity = next((act for act in after.activities if isinstance(act, discord.Streaming)), None)
            if primary_activity:
                activity_type = "streaming"
                
                # --- NEW: Focus timer distraction detection for streaming ---
                try:
                    is_distraction = await focus_timer.detect_media_activity(
                        user_id, 
                        primary_activity.name if hasattr(primary_activity, 'name') else "Stream",
                        is_music=False
                    )
                    if is_distraction:
                        try:
                            await after.send(
                                "⚠️ **Focus-Modus aktiv!** Du streamst gerade, aber du solltest fokussiert arbeiten! 🎯",
                                delete_after=15
                            )
                        except discord.Forbidden:
                            pass
                except Exception as e:
                    logger.error(f"Error in focus timer streaming detection: {e}")
        
        if not primary_activity:
            # Check for Spotify
            primary_activity = next((act for act in after.activities if isinstance(act, discord.Spotify)), None)
            if primary_activity:
                activity_type = "listening"
        
        if not primary_activity:
            # Check for other activities (watching, etc.)
            primary_activity = next((act for act in after.activities if not isinstance(act, discord.CustomActivity)), None)
            if primary_activity:
                # Determine activity type from discord.ActivityType
                if hasattr(primary_activity, 'type'):
                    if primary_activity.type == discord.ActivityType.watching:
                        activity_type = "watching"
                    elif primary_activity.type == discord.ActivityType.listening:
                        activity_type = "listening"
                    elif primary_activity.type == discord.ActivityType.streaming:
                        activity_type = "streaming"
                    elif primary_activity.type == discord.ActivityType.playing:
                        activity_type = "playing"
                    else:
                        activity_type = "other"
                else:
                    activity_type = "other"
        
        if not primary_activity:
            primary_activity = next((act for act in after.activities if isinstance(act, discord.CustomActivity)), None)
            activity_type = "custom"

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
                    quest_completed, _ = await quests.update_quest_progress(db_helpers, member.id, 'vc_minutes', 1, config)
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

# --- NEW: Scheduled Event Handlers for Wrapped Registration ---
@client.event
async def on_scheduled_event_user_add(event: discord.ScheduledEvent, user: discord.User):
    """
    Fires when a user clicks 'Interested' on a scheduled event.
    Automatically registers them for Wrapped if it's a Wrapped event.
    """
    try:
        # Check if this is a Wrapped event by looking for "Wrapped" in the name
        if "Wrapped" not in event.name:
            return
        
        # Skip bots
        if user.bot:
            return
        
        # Register the user for Wrapped
        success = await db_helpers.register_for_wrapped(user.id, user.display_name)
        
        if success:
            logger.info(f"[Wrapped] Auto-registered {user.display_name} ({user.id}) via event interest")
            print(f"[Wrapped] ✅ Auto-registered {user.display_name} for Wrapped via event '{event.name}'")
            
            # Send a friendly DM to confirm registration
            try:
                embed = discord.Embed(
                    title="🎉 Du bist dabei!",
                    description=f"Du hast Interesse an **{event.name}** gezeigt und bist jetzt automatisch für monatliche Wrapped-Zusammenfassungen registriert!",
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="📊 Was erwartet dich?",
                    value="• Personalisierte Monats-Statistiken\n"
                          "• Deine Top-Aktivitäten & Favoriten\n"
                          "• Server-Bestie & Vergleiche\n"
                          "• Spotify & Gaming-Rückblick",
                    inline=False
                )
                embed.add_field(
                    name="📅 Wann kommt das Wrapped?",
                    value="Deine persönliche Zusammenfassung wird in der zweiten Woche des nächsten Monats per DM verschickt!",
                    inline=False
                )
                embed.set_footer(text="💡 Tipp: Du kannst dich jederzeit mit /wrapped abmelden oder erneut auf 'Interessiert' klicken um abzumelden.")
                embed.set_thumbnail(url=user.display_avatar.url)
                await user.send(embed=embed)
            except (discord.Forbidden, discord.HTTPException) as dm_error:
                logger.debug(f"Could not DM {user.display_name} about Wrapped registration: {dm_error}")
    except Exception as e:
        logger.error(f"Error in on_scheduled_event_user_add: {e}", exc_info=True)


@client.event
async def on_scheduled_event_user_remove(event: discord.ScheduledEvent, user: discord.User):
    """
    Fires when a user removes their 'Interested' status from a scheduled event.
    Automatically unregisters them from Wrapped if it's a Wrapped event.
    """
    try:
        # Check if this is a Wrapped event
        if "Wrapped" not in event.name:
            return
        
        # Skip bots
        if user.bot:
            return
        
        # Unregister the user from Wrapped
        success = await db_helpers.unregister_from_wrapped(user.id)
        
        if success:
            logger.info(f"[Wrapped] Auto-unregistered {user.display_name} ({user.id}) via event interest removal")
            print(f"[Wrapped] ❌ Auto-unregistered {user.display_name} from Wrapped via event '{event.name}'")
            
            # Send a friendly DM to confirm unregistration
            try:
                embed = discord.Embed(
                    title="👋 Bis zum nächsten Mal!",
                    description=f"Du hast dein Interesse an **{event.name}** entfernt und erhältst keine Wrapped-Zusammenfassungen mehr.",
                    color=discord.Color.orange()
                )
                embed.add_field(
                    name="🔄 Möchtest du dich wieder anmelden?",
                    value="• Klicke erneut auf 'Interessiert' beim nächsten Wrapped-Event\n"
                          "• Oder nutze `/wrapped`",
                    inline=False
                )
                embed.set_footer(text="Wir freuen uns, dich bald wieder zu sehen!")
                await user.send(embed=embed)
            except (discord.Forbidden, discord.HTTPException) as dm_error:
                logger.debug(f"Could not DM {user.display_name} about Wrapped unregistration: {dm_error}")
    except Exception as e:
        logger.error(f"Error in on_scheduled_event_user_remove: {e}", exc_info=True)


@client.event
async def on_member_join(member: discord.Member):
    """
    Fires when a new member joins a server.
    Assigns the configured join role if set.
    """
    try:
        # Skip bots
        if member.bot:
            return
        
        # Get join role from config
        join_role_name = config.get('bot', {}).get('join_role', '').strip()
        
        # If no join role is configured, do nothing
        if not join_role_name:
            logger.debug(f"No join role configured, skipping role assignment for {member.display_name}")
            return
        
        # Find the role in the guild
        join_role = discord.utils.get(member.guild.roles, name=join_role_name)
        
        if not join_role:
            logger.warning(f"Join role '{join_role_name}' not found in guild '{member.guild.name}'")
            return
        
        # Assign the role
        try:
            await member.add_roles(join_role, reason="Automatic role assignment on join")
            logger.info(f"[Join] Assigned role '{join_role_name}' to {member.display_name} in '{member.guild.name}'")
            print(f"[Join] ✅ Assigned role '{join_role_name}' to {member.display_name}")
        except discord.Forbidden:
            logger.error(f"[Join] Missing permissions to assign role '{join_role_name}' in '{member.guild.name}'")
            print(f"[Join] ❌ Missing permissions to assign role '{join_role_name}'")
        except discord.HTTPException as e:
            logger.error(f"[Join] HTTP error assigning role: {e}")
            print(f"[Join] ❌ Error assigning role: {e}")
            
    except Exception as e:
        logger.error(f"Error in on_member_join: {e}", exc_info=True)


def _calculate_wrapped_dates(config, target_month=None):
    """
    Helper function to calculate the dates for the Wrapped event.
    Uses deterministic random based on month/year to ensure consistency.
    
    Args:
        config: Bot configuration
        target_month: datetime object for which month to calculate (defaults to next month)
    """
    now = datetime.now(timezone.utc)
    
    # Calculate the first day of the *next* month for scheduling.
    first_day_of_current_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    first_day_of_next_month = (first_day_of_current_month + timedelta(days=32)).replace(day=1)
    
    # Determine which month we're calculating for
    if target_month is None:
        target_month = first_day_of_next_month
    
    # Use deterministic random based on month and year for consistency
    # Create a local Random instance to avoid thread safety issues
    # Format with zero-padding for consistency
    seed_str = f"{target_month.year:04d}-{target_month.month:02d}"
    local_random = random.Random(seed_str)
    release_day = local_random.randint(config['modules']['wrapped']['release_day_min'], config['modules']['wrapped']['release_day_max'])
    
    release_date = target_month.replace(day=release_day, hour=18, minute=0, second=0, microsecond=0) # 6 PM UTC

    # The day to create the event is one week before the release.
    event_creation_date = release_date - timedelta(days=7)
    
    # Event name includes the PREVIOUS month (the month being wrapped)
    stat_period_date = (target_month - timedelta(days=1)).replace(day=1)
    event_name = f"Sulfur Wrapped {stat_period_date.strftime('%B %Y')}"
    stat_period = stat_period_date.strftime('%Y-%m')
    
    return {
        "event_name": event_name,
        "event_creation_date": event_creation_date,
        "release_date": release_date,
        "stat_period": stat_period,
        "stat_period_date": stat_period_date
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
        
        # --- 1. Event Creation for NEXT month's wrapped ---
        # Calculate dates for next month's wrapped event
        dates = _calculate_wrapped_dates(config)
        event_name = dates["event_name"]
        event_creation_date = dates["event_creation_date"]
        release_date = dates["release_date"]
        
        # Check if an event for this period already exists
        # We check across all guilds the bot is in to avoid creating duplicates
        all_events = [e for guild in client.guilds for e in guild.scheduled_events]
        event_exists = any(event.name == event_name for event in all_events)

        # If it's the right day to create the event and it doesn't exist yet
        # Check full date (year, month, day) not just day number
        if (now.year == event_creation_date.year and 
            now.month == event_creation_date.month and 
            now.day == event_creation_date.day and 
            not event_exists):
            print(f"Creating Scheduled Event for '{event_name}'...")
            # --- FIX: Loop through all guilds to create the event ---
            for guild in client.guilds:
                try:
                    await guild.create_scheduled_event(
                        name=event_name,
                        description=f"Dein persönlicher Server-Rückblick für **{dates['stat_period_date'].strftime('%B %Y')}**! Die Ergebnisse werden am Event-Tag per DM verschickt.",
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

        # --- 2. Wrapped Distribution for CURRENT month ---
        # Calculate dates for current month's wrapped (last month's stats)
        first_day_of_current_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        current_month_dates = _calculate_wrapped_dates(config, target_month=first_day_of_current_month)
        current_release_date = current_month_dates["release_date"]
        current_stat_period = current_month_dates["stat_period"]
        current_stat_period_date = current_month_dates["stat_period_date"]
        current_event_name = current_month_dates["event_name"]

        # Check if today is the release day - use full date comparison
        if (now.year == current_release_date.year and 
            now.month == current_release_date.month and 
            now.day == current_release_date.day and
            now.hour >= current_release_date.hour):  # Only trigger at or after 6 PM UTC
            
            print(f"Distributing Wrapped for period {current_stat_period}...")
            stats = await db_helpers.get_wrapped_stats_for_period(current_stat_period)

            # --- NEW: Get list of registered users ---
            registered_users = await db_helpers.get_wrapped_registrations()
            if not registered_users:
                print(f"No users registered for Wrapped. Skipping distribution.")
                # Still delete events even if no users registered
            else:
                # --- NEW: Pre-calculate ranks ---
                total_users = len(stats)
                if total_users > 0:
                    # Pre-calculate server averages once for all users
                    server_averages = await _calculate_server_averages(stats)
                    
                    for user_stats in stats:
                        user_id = user_stats.get('user_id')
                        if user_id not in registered_users:
                            continue  # Skip users who haven't opted in
                        
                        # --- FIX: Wrap individual user processing in try-except to prevent one failure from stopping all users ---
                        # We catch broad Exception intentionally here for fault tolerance - we want to continue
                        # processing other users even if one fails unexpectedly. All errors are logged with full traceback.
                        try:
                            await _generate_and_send_wrapped_for_user(
                                user_stats=user_stats,
                                stat_period_date=current_stat_period_date,
                                all_stats_for_period=stats,
                                total_users=total_users,
                                server_averages=server_averages
                            )
                        except Exception as user_error:
                            logger.error(f"Error generating Wrapped for user {user_id}: {user_error}", exc_info=True)
                            print(f"  - [Wrapped] ERROR for user {user_id}: {user_error}")
                else:
                    print(f"No stats found for period {current_stat_period}. Skipping distribution.")
            
            # --- 3. Delete wrapped events after distribution ---
            print(f"Deleting wrapped events for '{current_event_name}'...")
            events_deleted = 0
            for guild in client.guilds:
                for event in guild.scheduled_events:
                    if event.name == current_event_name:
                        try:
                            await event.delete(reason="Wrapped has been distributed")
                            print(f"  -> Deleted event in '{guild.name}'")
                            events_deleted += 1
                        except Exception as e:
                            print(f"  -> Failed to delete event in '{guild.name}': {e}")
            
            if events_deleted > 0:
                print(f"Deleted {events_deleted} wrapped event(s)")
            else:
                print(f"No events found to delete for '{current_event_name}'")
                
    except Exception as e:
        logger.error(f"Error in manage_wrapped_event task: {e}", exc_info=True)
        print(f"[Wrapped Event Task] Error: {e}")


@tasks.loop(minutes=10)
async def sport_betting_notifications_task():
    """
    Background task to notify users about their bets before matches start.
    Runs every 10 minutes and checks for matches starting within 30 minutes.
    """
    try:
        if not client.guilds:
            return
        
        # Get bets that need notification (matches starting within 30 minutes)
        bets_to_notify = await sport_betting.get_bets_to_notify(db_helpers, minutes_before=30)
        
        if not bets_to_notify:
            return
        
        logger.info(f"Found {len(bets_to_notify)} bets to notify")
        
        # Group bets by user
        user_bets = {}
        for bet in bets_to_notify:
            user_id = bet["user_id"]
            if user_id not in user_bets:
                user_bets[user_id] = []
            user_bets[user_id].append(bet)
        
        # Send notifications to each user
        notified_bet_ids = []
        for user_id, bets in user_bets.items():
            try:
                user = await client.fetch_user(user_id)
                if not user:
                    continue
                
                # Create notification embed
                embed = discord.Embed(
                    title="⚽ Spielerinnerung!",
                    description="Deine Wetten starten bald!",
                    color=discord.Color.gold()
                )
                
                for bet in bets[:5]:  # Max 5 bets per notification
                    home_team = bet.get("home_team", "Heim")
                    away_team = bet.get("away_team", "Auswärts")
                    match_time = bet.get("match_time")
                    bet_outcome = bet.get("bet_outcome", "")
                    odds = bet.get("odds_at_bet", 1.0)
                    potential_payout = bet.get("potential_payout", 0)
                    
                    outcome_names = {
                        "home": f"🏠 {home_team}",
                        "draw": "🤝 Remis",
                        "away": f"✈️ {away_team}",
                        "over": "⬆️ Über",
                        "under": "⬇️ Unter",
                        "yes": "✅ Ja",
                        "no": "❌ Nein",
                    }
                    
                    # Handle time formatting
                    if isinstance(match_time, str):
                        try:
                            match_time = datetime.fromisoformat(match_time.replace("Z", "+00:00"))
                        except ValueError:
                            pass
                    
                    time_str = match_time.strftime("%H:%M") if isinstance(match_time, datetime) else "bald"
                    
                    embed.add_field(
                        name=f"⚽ {home_team} vs {away_team}",
                        value=(
                            f"🎯 Dein Tipp: **{outcome_names.get(bet_outcome, bet_outcome)}**\n"
                            f"📊 Quote: **{odds:.2f}x** | 💎 Gewinn: **{potential_payout}** 🪙\n"
                            f"⏰ Start: **{time_str} Uhr**"
                        ),
                        inline=False
                    )
                    
                    notified_bet_ids.append(bet["bet_id"])
                
                if len(bets) > 5:
                    embed.set_footer(text=f"Und {len(bets) - 5} weitere Wetten...")
                else:
                    embed.set_footer(text="Viel Glück! 🍀")
                
                # Send DM to user
                try:
                    await user.send(embed=embed)
                    logger.info(f"Sent betting notification to user {user_id}")
                except discord.Forbidden:
                    logger.warning(f"Could not send DM to user {user_id} (DMs disabled)")
                except Exception as e:
                    logger.warning(f"Failed to send notification to user {user_id}: {e}")
                    
            except discord.NotFound:
                logger.warning(f"User {user_id} not found")
            except Exception as e:
                logger.error(f"Error notifying user {user_id}: {e}")
        
        # Mark bets as notified
        if notified_bet_ids:
            await sport_betting.mark_bets_notified(db_helpers, notified_bet_ids)
            logger.info(f"Marked {len(notified_bet_ids)} bets as notified")
            
    except Exception as e:
        logger.error(f"Error in sport_betting_notifications_task: {e}", exc_info=True)


@sport_betting_notifications_task.before_loop
async def before_sport_betting_notifications():
    await client.wait_until_ready()


@tasks.loop(minutes=5)
async def sport_betting_sync_and_settle_task():
    """
    Background task to sync match data and settle bets.
    Runs every 5 minutes to:
    1. Sync match data from API for free leagues
    2. Check for finished matches and update their status
    3. Settle bets for finished matches
    4. Send DM notifications to users about their bet results
    """
    try:
        if not client.guilds:
            return
        
        logger.debug("Running sport betting sync and settle task")
        
        # Step 1: Sync match data from free leagues
        total_synced = 0
        
        for league_id in sport_betting.FREE_LEAGUES:
            try:
                synced = await sport_betting.sync_league_matches(db_helpers, league_id)
                total_synced += synced
            except Exception as e:
                logger.warning(f"Could not sync {league_id}: {e}")
        
        if total_synced > 0:
            logger.info(f"Sport betting: Synced {total_synced} matches")
        
        # Step 2: Get matches that need to be checked for results
        matches_to_check = await sport_betting.get_matches_to_check(db_helpers)
        
        if not matches_to_check:
            return
        
        logger.info(f"Sport betting: Found {len(matches_to_check)} matches to check for results")
        
        # Step 3: Check each match and settle bets
        all_settled_bets = []
        
        for match in matches_to_check:
            match_id = match.get("match_id")
            league_id = match.get("league_id", "bl1")
            
            # Try to get updated match info from API
            league_config = sport_betting.LEAGUES.get(league_id)
            if not league_config:
                continue
            
            provider = sport_betting.APIProviderFactory.get_provider(league_config["provider"])
            
            try:
                # Check if provider supports get_match method
                if not hasattr(provider, 'get_match'):
                    logger.debug(f"Provider {league_config['provider']} does not support get_match")
                    continue
                
                # Get the match from API
                updated_match = await provider.get_match(match_id)
                
                if updated_match and updated_match.get("status") == sport_betting.MatchStatus.FINISHED:
                    home_score = updated_match.get("home_score", 0)
                    away_score = updated_match.get("away_score", 0)
                    
                    # Settle bets and get details for notifications
                    settled_bets = await sport_betting.settle_match_bets_with_details(
                        db_helpers, match_id, home_score, away_score
                    )
                    
                    if settled_bets:
                        all_settled_bets.extend(settled_bets)
                        logger.info(f"Settled {len(settled_bets)} bets for match {match_id}")
                        
            except AttributeError as e:
                logger.debug(f"Provider method not available for match {match_id}: {e}")
                continue
            except Exception as e:
                logger.warning(f"Error checking match {match_id}: {e}")
                continue
        
        # Step 4: Send DM notifications to users about their settled bets
        if all_settled_bets:
            # Group by user
            user_bets = {}
            for bet in all_settled_bets:
                user_id = bet["user_id"]
                if user_id not in user_bets:
                    user_bets[user_id] = []
                user_bets[user_id].append(bet)
            
            for user_id, bets in user_bets.items():
                try:
                    user = await client.fetch_user(user_id)
                    if not user:
                        continue
                    
                    # Calculate totals
                    total_won = sum(b["actual_payout"] for b in bets if b["status"] == "won")
                    total_lost = sum(b["bet_amount"] for b in bets if b["status"] == "lost")
                    wins = len([b for b in bets if b["status"] == "won"])
                    losses = len([b for b in bets if b["status"] == "lost"])
                    
                    # Determine embed color based on results
                    if total_won > total_lost:
                        color = discord.Color.green()
                        title_emoji = "🎉"
                    elif total_won < total_lost:
                        color = discord.Color.red()
                        title_emoji = "😢"
                    else:
                        color = discord.Color.gold()
                        title_emoji = "⚽"
                    
                    embed = discord.Embed(
                        title=f"{title_emoji} Wettergebnisse!",
                        description=f"Deine Wetten wurden ausgewertet!\n**{wins}** Gewonnen | **{losses}** Verloren",
                        color=color
                    )
                    
                    # Add each bet result (max 5)
                    for bet in bets[:5]:
                        home_team = bet.get("home_team", "Heim")
                        away_team = bet.get("away_team", "Auswärts")
                        home_score = bet.get("home_score", 0)
                        away_score = bet.get("away_score", 0)
                        bet_outcome = bet.get("bet_outcome", "")
                        status = bet.get("status", "")
                        bet_amount = bet.get("bet_amount", 0)
                        actual_payout = bet.get("actual_payout", 0)
                        odds = bet.get("odds_at_bet", 1.0)
                        
                        outcome_names = {
                            "home": f"🏠 {home_team}",
                            "draw": "🤝 Remis",
                            "away": f"✈️ {away_team}",
                            "over": "⬆️ Über",
                            "under": "⬇️ Unter",
                            "yes": "✅ Ja",
                            "no": "❌ Nein",
                        }
                        
                        status_emoji = "✅" if status == "won" else "❌"
                        result_text = f"+{actual_payout} 🪙" if status == "won" else f"-{bet_amount} 🪙"
                        
                        embed.add_field(
                            name=f"{status_emoji} {home_team} {home_score}:{away_score} {away_team}",
                            value=(
                                f"🎯 Dein Tipp: **{outcome_names.get(bet_outcome, bet_outcome)}**\n"
                                f"📊 Quote: **{odds:.2f}x** | 💰 {result_text}"
                            ),
                            inline=False
                        )
                    
                    if len(bets) > 5:
                        embed.set_footer(text=f"Und {len(bets) - 5} weitere Wetten...")
                    else:
                        # Add total summary
                        net = total_won - total_lost
                        net_text = f"+{net}" if net >= 0 else str(net)
                        embed.set_footer(text=f"Gesamtbilanz: {net_text} 🪙")
                    
                    # Send DM
                    try:
                        await user.send(embed=embed)
                        logger.info(f"Sent bet results notification to user {user_id}")
                        
                        # Credit winnings to user balance
                        if total_won > 0:
                            stat_period = datetime.now(timezone.utc).strftime('%Y-%m')
                            await db_helpers.add_balance(user_id, user.display_name, total_won, config, stat_period)
                            logger.info(f"Credited {total_won} coins to user {user_id}")
                            
                    except discord.Forbidden:
                        logger.warning(f"Could not send DM to user {user_id} (DMs disabled)")
                    except Exception as e:
                        logger.warning(f"Failed to send notification to user {user_id}: {e}")
                        
                except discord.NotFound:
                    logger.warning(f"User {user_id} not found")
                except Exception as e:
                    logger.error(f"Error notifying user {user_id} about bet results: {e}")
            
            logger.info(f"Sport betting: Processed {len(all_settled_bets)} settled bets for {len(user_bets)} users")
            
    except Exception as e:
        logger.error(f"Error in sport_betting_sync_and_settle_task: {e}", exc_info=True)


@sport_betting_sync_and_settle_task.before_loop
async def before_sport_betting_sync_and_settle():
    await client.wait_until_ready()


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
    """Enhanced paginated view for Wrapped summaries with visual improvements."""
    
    # Page icons for different sections
    PAGE_ICONS = ["🎭", "👥", "💬", "🎤", "📍", "🎮", "🎵", "📋", "🔍", "🛍️", "✨"]
    
    def __init__(self, pages: list, user: discord.User, timeout=604800):  # 7 days
        super().__init__(timeout=timeout)
        self.pages = pages
        self.user = user
        self.current_page = 0
        self.message = None
        self._update_buttons()
    
    def _get_page_indicator(self):
        """Returns a visual page indicator string."""
        indicators = []
        for i in range(len(self.pages)):
            if i == self.current_page:
                indicators.append("●")  # Current page
            else:
                indicators.append("○")  # Other pages
        return " ".join(indicators)
    
    def _update_buttons(self):
        """Updates button states and labels based on current page."""
        # Update previous button
        self.previous_button.disabled = self.current_page == 0
        self.previous_button.label = "◀ Zurück"
        
        # Update page indicator button
        page_icon = self.PAGE_ICONS[self.current_page % len(self.PAGE_ICONS)]
        self.page_indicator.label = f"{page_icon} {self.current_page + 1}/{len(self.pages)}"
        
        # Update next button
        self.next_button.disabled = self.current_page >= len(self.pages) - 1
        self.next_button.label = "Weiter ▶"
    
    # Footer separator constant
    FOOTER_SEPARATOR = "━━━━━━━━━━━━━━━"
    
    def _update_embed_footer(self, embed: discord.Embed):
        """Adds visual page indicator to embed footer."""
        page_dots = self._get_page_indicator()
        original_footer = embed.footer.text if embed.footer and embed.footer.text else ""
        
        # Add separator if there's existing footer text
        if original_footer:
            new_footer = f"{original_footer}\n{self.FOOTER_SEPARATOR}\n{page_dots}"
        else:
            new_footer = page_dots
        
        embed.set_footer(text=new_footer)
        return embed

    @discord.ui.button(label="◀ Zurück", style=discord.ButtonStyle.secondary, row=0)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = max(0, self.current_page - 1)
        self._update_buttons()
        embed = self._update_embed_footer(self.pages[self.current_page].copy())
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="1/1", style=discord.ButtonStyle.secondary, disabled=True, row=0)
    async def page_indicator(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Non-interactive page indicator button."""
        pass

    @discord.ui.button(label="Weiter ▶", style=discord.ButtonStyle.primary, row=0)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = min(len(self.pages) - 1, self.current_page + 1)
        self._update_buttons()
        embed = self._update_embed_footer(self.pages[self.current_page].copy())
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Zum Anfang", style=discord.ButtonStyle.secondary, emoji="⏮️", row=1)
    async def first_page_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Jump to the first page."""
        self.current_page = 0
        self._update_buttons()
        embed = self._update_embed_footer(self.pages[self.current_page].copy())
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Zum Ende", style=discord.ButtonStyle.secondary, emoji="⏭️", row=1)
    async def last_page_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Jump to the last page."""
        self.current_page = len(self.pages) - 1
        self._update_buttons()
        embed = self._update_embed_footer(self.pages[self.current_page].copy())
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Teilen", style=discord.ButtonStyle.green, emoji="🔗", row=1)
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
        """Sends the first page to the user's DMs with enhanced styling."""
        self._update_buttons()
        first_embed = self._update_embed_footer(self.pages[0].copy())
        self.message = await self.user.send(embed=first_embed, view=self)

async def _generate_and_send_wrapped_for_user(
    user_stats: dict,
    stat_period_date: datetime,
    all_stats_for_period: list,
    total_users: int,
    server_averages: dict,
    raise_on_dm_failure: bool = False
) -> None:
    """Helper function to generate and DM the Wrapped story to a single user.
    
    Args:
        user_stats: Stats for the user (dict from database)
        stat_period_date: Date of the period being wrapped
        all_stats_for_period: All stats for ranking calculations (list of dicts)
        total_users: Total number of users in the period
        server_averages: Server-wide averages (dict with avg_messages, avg_vc_minutes)
        raise_on_dm_failure: If True, re-raises exceptions when DM fails (for admin previews)
    """
    user_id = user_stats['user_id']
    user = None
    guild = None
    try:
        # Use fetch_user to guarantee we can find the user, even if not cached.
        user = await client.fetch_user(int(user_id))
        
        # Try to get a guild context for emoji auto-download
        # Get the first mutual guild between the bot and the user
        for mutual_guild in client.guilds:
            member = mutual_guild.get_member(user.id)
            if member:
                guild = mutual_guild
                break
    except discord.NotFound:
        print(f"  - Skipping user ID {user_id}: User could not be found (account may be deleted).")
        return

    print(f"  - [Wrapped] Generating for {user.name} ({user.id})...")
    if guild:
        print(f"    - [Wrapped] Using guild context: {guild.name} for emoji auto-download")
    
    pages = [] # This will hold all the embed pages for the story
    base_color = get_embed_color(config)
    
    # Define themed colors for different pages (more visually appealing)
    WRAPPED_COLORS = {
        'intro': discord.Color.from_rgb(88, 101, 242),    # Discord blurple
        'bestie': discord.Color.from_rgb(255, 121, 198),  # Pink
        'messages': discord.Color.from_rgb(87, 242, 135), # Green
        'voice': discord.Color.from_rgb(254, 231, 92),    # Yellow
        'activity': discord.Color.from_rgb(235, 69, 158), # Magenta
        'game': discord.Color.from_rgb(88, 101, 242),     # Blurple
        'spotify': discord.Color.from_rgb(30, 215, 96),   # Spotify green
        'quests': discord.Color.from_rgb(255, 163, 26),   # Orange
        'detective': discord.Color.from_rgb(47, 49, 54),  # Dark
        'shop': discord.Color.from_rgb(255, 215, 0),      # Gold
        'summary': discord.Color.from_rgb(114, 137, 218), # Light blurple
    }

    # Find favorite channel
    fav_channel_id = None
    if user_stats.get('channel_usage'):
        print("    - [Wrapped] Calculating favorite channel...")
        channel_usage = json.loads(user_stats['channel_usage'])
        if channel_usage:
            fav_channel_id = max(channel_usage, key=channel_usage.get)

    # --- NEW: Fetch all the new Wrapped stats in one go ---
    extra_stats = await get_wrapped_extra_stats(user.id, stat_period_date.strftime('%Y-%m'))
    
    # --- Calculate fun facts for the intro ---
    total_messages = user_stats.get('message_count', 0)
    total_vc_minutes = user_stats.get('minutes_in_vc', 0)
    words_typed = total_messages * 15  # Rough estimate: 15 words per message
    
    # Calculate activity score for achievements
    activity_score = total_messages + (total_vc_minutes * 2)

    # --- Page 1: Enhanced Intro & Prime Time ---
    intro_embed = discord.Embed(
        title=f"🎉 {stat_period_date.strftime('%B')} Wrapped",
        description=f"### Willkommen zurück, **{user.display_name}**!\n\n"
                    f"Dein persönlicher Rückblick auf den **{stat_period_date.strftime('%B %Y')}** ist da. "
                    f"Lass uns gemeinsam schauen, was du so getrieben hast! 👀",
        color=WRAPPED_COLORS['intro']
    )
    intro_embed.set_thumbnail(url=user.display_avatar.url)
    
    # Add Prime Time title with enhanced visuals
    prime_time_title = get_prime_time_title(extra_stats.get('prime_time_hour'))
    prime_time_hour = extra_stats.get('prime_time_hour')
    if prime_time_hour is not None:
        time_str = f"{prime_time_hour}:00 - {(prime_time_hour + 1) % 24}:00 Uhr"
    else:
        time_str = "Keine Daten"
    
    intro_embed.add_field(
        name="🏅 Dein Titel diesen Monat",
        value=f"## {prime_time_title}\n*Aktivste Zeit: {time_str}*",
        inline=False
    )
    
    # Add quick stats summary
    intro_embed.add_field(
        name="📊 Schnellübersicht",
        value=f"```\n"
              f"📝 Nachrichten:  {total_messages:,}\n"
              f"🎤 VC-Minuten:   {int(total_vc_minutes):,}\n"
              f"✍️ ~Wörter:      {words_typed:,}\n"
              f"```",
        inline=True
    )
    
    # Add achievement badges based on activity
    badges = []
    if total_messages >= 500:
        badges.append("💬 Vielschreiber")
    if total_vc_minutes >= 600:  # 10 hours
        badges.append("🎧 VC-König")
    if extra_stats.get('quests_completed', 0) >= 20:
        badges.append("📋 Quest-Master")
    if extra_stats.get('games_played', 0) >= 50:
        badges.append("🎰 Gambler")
    if extra_stats.get('detective_cases_solved', 0) >= 5:
        badges.append("🔍 Sherlock")
        
    if badges:
        intro_embed.add_field(
            name="🏆 Verdiente Abzeichen",
            value=" ".join(badges),
            inline=True
        )
    
    intro_embed.set_image(url=get_nested_config(config, 'modules', 'wrapped', 'intro_gif_url', default=''))
    pages.append(intro_embed)

    # --- Page 2: Server Bestie with enhanced styling ---
    bestie_embed = discord.Embed(
        title="👥 Deine Server-Connections",
        color=WRAPPED_COLORS['bestie']
    )
    bestie_id = extra_stats.get("server_bestie_id")
    if bestie_id:
        try:
            bestie_user = await client.fetch_user(int(bestie_id))
            bestie_embed.description = (
                f"💕 Diesen Monat warst du unzertrennlich mit...\n\n"
                f"## 🤝 {bestie_user.mention}\n\n"
                f"*Ihr scheint euch echt gut zu verstehen!*"
            )
            bestie_embed.set_thumbnail(url=bestie_user.display_avatar.url)
            
            # Add a fun relationship fact
            bestie_embed.add_field(
                name="💡 Fun Fact",
                value=random.choice([
                    "Habt ihr euch mal auf einen Kaffee verabredet?",
                    "Vielleicht solltet ihr mal zusammen zocken!",
                    "Beste Freunde im Making!",
                    "Bromance/Womance des Monats?",
                    "Die nächste iconic duo?"
                ]),
                inline=False
            )
        except discord.NotFound:
            bestie_embed.description = await replace_emoji_tags(
                "👻 Dein Server-Bestie scheint ein Geist zu sein...\n\n"
                "*Oder hat den Server verlassen.* :dono:",
                client, guild
            )
    else:
        bestie_embed.description = await replace_emoji_tags(
            "🐺 Du warst diesen Monat eher ein **einsamer Wolf**.\n\n"
            "*Keine regelmäßigen Erwähnungen oder Antworten gefunden.*\n\n"
            "Vielleicht nächsten Monat? :gege:",
            client, guild
        )
        bestie_embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/862039818399481876.png")
    
    bestie_embed.set_footer(text="Basiert auf Erwähnungen und Reply-Patterns")
    pages.append(bestie_embed)

    # --- Page 3: Enhanced Message & Emoji Stats ---
    message_ranks = {user['user_id']: rank for rank, user in enumerate(sorted(all_stats_for_period, key=lambda x: x.get('message_count', 0), reverse=True))}
    message_rank_text = _get_percentile_rank(user.id, message_ranks, total_users)
    
    # Calculate comparison with average
    avg_messages = int(server_averages['avg_messages'])
    message_diff = total_messages - avg_messages
    diff_text = f"+{message_diff}" if message_diff >= 0 else str(message_diff)
    diff_emoji = "📈" if message_diff >= 0 else "📉"
    
    msg_embed = discord.Embed(
        title="💬 Du und der Chat",
        description=f"*So viel hast du diesen Monat gechattet...*",
        color=WRAPPED_COLORS['messages']
    )
    
    msg_embed.add_field(
        name="📝 Deine Nachrichten",
        value=f"## `{total_messages:,}`",
        inline=True
    )
    msg_embed.add_field(
        name="📊 Server-Durchschnitt",
        value=f"## `{avg_messages:,}`",
        inline=True
    )
    msg_embed.add_field(
        name=f"{diff_emoji} Vergleich",
        value=f"## `{diff_text}`",
        inline=True
    )
    msg_embed.add_field(
        name="🏆 Dein Rang",
        value=f"Du gehörst zu den **{message_rank_text}** der aktivsten Chatter!",
        inline=False
    )

    # Add Top 3 Emojis with enhanced styling
    if user_stats.get('emoji_usage'):
        emoji_usage = json.loads(user_stats['emoji_usage'])
        sorted_emojis = sorted(emoji_usage.items(), key=lambda item: item[1], reverse=True)
        if sorted_emojis:
            emoji_lines = []
            medals = ["🥇", "🥈", "🥉"]
            for i, (emoji_name, count) in enumerate(sorted_emojis[:3]):
                emoji_obj = discord.utils.get(client.emojis, name=emoji_name)
                emoji_display = str(emoji_obj) if emoji_obj else f"`:{emoji_name}:`"
                medal = medals[i] if i < len(medals) else f"**{i+1}.**"
                emoji_lines.append(f"{medal} {emoji_display} × **{count}**")
            
            msg_embed.add_field(
                name="😀 Deine Top-Emojis",
                value="\n".join(emoji_lines),
                inline=False
            )
    pages.append(msg_embed)

    # --- Page 4: Enhanced Voice Channel Stats ---
    vc_ranks = {user['user_id']: rank for rank, user in enumerate(sorted(all_stats_for_period, key=lambda x: x.get('minutes_in_vc', 0), reverse=True))}
    vc_rank_text = _get_percentile_rank(user.id, vc_ranks, total_users)
    vc_hours = total_vc_minutes / 60
    avg_vc_hours = server_averages['avg_vc_minutes'] / 60
    
    vc_embed = discord.Embed(
        title="🎤 Deine Voice-Chat Story",
        description="*Wie viel Zeit hast du im VC verbracht?*",
        color=WRAPPED_COLORS['voice']
    )
    
    # Calculate fun conversions
    vc_movies = vc_hours / 2  # Average movie length: 2 hours
    vc_songs = vc_hours * 20  # Average song: 3 min
    
    vc_embed.add_field(
        name="⏱️ Deine VC-Zeit",
        value=f"## `{vc_hours:.1f}` Stunden\n*({int(total_vc_minutes)} Minuten)*",
        inline=True
    )
    vc_embed.add_field(
        name="📊 Server-Durchschnitt",
        value=f"## `{avg_vc_hours:.1f}` Stunden",
        inline=True
    )
    vc_embed.add_field(
        name="🏆 Dein Rang",
        value=f"Du warst in den **{vc_rank_text}** der größten Quasselstrippen!",
        inline=False
    )

    # Add VC stats with enhanced visuals
    longest_session_seconds = extra_stats.get("longest_vc_session_seconds", 0)
    # Format duration properly without microseconds
    hours, remainder = divmod(int(longest_session_seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    longest_session_str = f"{hours}:{minutes:02d}:{seconds:02d}"
    
    vc_embed.add_field(
        name="⏳ Längste Session",
        value=f"`{longest_session_str}`",
        inline=True
    )
    vc_embed.add_field(
        name="➕ Erstellte VCs",
        value=f"`{extra_stats.get('temp_vcs_created', 0)}`",
        inline=True
    )
    
    # Fun fact about VC time
    if vc_hours >= 1:
        vc_embed.add_field(
            name="🎬 Das sind...",
            value=f"~**{vc_movies:.0f}** Filme oder ~**{int(vc_songs)}** Songs!",
            inline=True
        )
    
    pages.append(vc_embed)

    # --- Page 5: Enhanced Top Channel & Activity ---
    activity_embed = discord.Embed(
        title="📍 Deine digitalen Hangouts",
        description="*Wo hast du dich am liebsten aufgehalten?*",
        color=WRAPPED_COLORS['activity']
    )
    
    # Top Channel with enhanced display
    if user_stats.get('channel_usage'):
        channel_usage = json.loads(user_stats['channel_usage'])
        if channel_usage:
            # Get top 3 channels
            sorted_channels = sorted(channel_usage.items(), key=lambda x: x[1], reverse=True)[:3]
            channel_lines = []
            medals = ["🥇", "🥈", "🥉"]
            
            for i, (ch_id, count) in enumerate(sorted_channels):
                channel_obj = client.get_channel(int(ch_id))
                channel_name = channel_obj.mention if channel_obj else f"*Gelöschter Kanal*"
                medal = medals[i] if i < len(medals) else f"**{i+1}.**"
                channel_lines.append(f"{medal} {channel_name}")
            
            activity_embed.add_field(
                name="🏠 Deine Lieblingskanäle",
                value="\n".join(channel_lines),
                inline=False
            )

    # Top Activities with enhanced display
    if user_stats.get('activity_usage'):
        activity_usage = json.loads(user_stats['activity_usage'])
        filtered_activities = {k: v for k, v in activity_usage.items() if k.lower() not in ['custom status', 'spotify']}
        if filtered_activities:
            sorted_activities = sorted(filtered_activities.items(), key=lambda x: x[1], reverse=True)[:3]
            activity_lines = []
            for i, (act_name, minutes) in enumerate(sorted_activities):
                medal = medals[i] if i < len(medals) else f"**{i+1}.**"
                hours = minutes / 60
                activity_lines.append(f"{medal} **{act_name}** - *{hours:.1f}h*")
            
            activity_embed.add_field(
                name="🎮 Top Aktivitäten",
                value="\n".join(activity_lines),
                inline=False
            )
    
    if activity_embed.fields:
        pages.append(activity_embed)

    # --- Page 6: Enhanced Game Wrapped Page ---
    if user_stats.get('game_usage'):
        monthly_game_stats = json.loads(user_stats['game_usage'])
        if monthly_game_stats:
            # Find favorite game by total minutes this month
            fav_game_name = max(monthly_game_stats, key=lambda g: monthly_game_stats[g]['total_minutes'])
            fav_game_data = monthly_game_stats[fav_game_name]
            user_minutes = fav_game_data['total_minutes']
            user_hours = user_minutes / 60

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
            
            # Build leaderboard with enhanced visuals
            leaderboard_data.sort(key=lambda x: x['minutes'], reverse=True)
            leaderboard_lines = []
            medals = ["🥇", "🥈", "🥉"]
            for i, data in enumerate(leaderboard_data[:3]):
                player_user = client.get_user(data['user_id'])
                player_name = player_user.display_name if player_user else f"User {data['user_id']}"
                medal = medals[i] if i < len(medals) else f"**{i+1}.**"
                hours = data['minutes'] / 60
                leaderboard_lines.append(f"{medal} **{player_name}** - *{hours:.1f}h*")

            game_embed = discord.Embed(
                title=f"🎮 Dein Lieblingsspiel",
                description=f"## {fav_game_name}\n*Dein meistgespieltes Spiel diesen Monat*",
                color=WRAPPED_COLORS['game']
            )
            game_embed.add_field(
                name="⏱️ Deine Spielzeit",
                value=f"## `{user_hours:.1f}` Stunden\n*({int(user_minutes)} Minuten)*",
                inline=True
            )
            game_embed.add_field(
                name="📊 Server-Durchschnitt",
                value=f"## `{server_avg_minutes / 60:.1f}` Stunden",
                inline=True
            )
            
            if leaderboard_lines:
                game_embed.add_field(
                    name=f"🏆 Top-Spieler",
                    value="\n".join(leaderboard_lines),
                    inline=False
                )
            
            # Calculate user's rank
            user_rank = next((i+1 for i, d in enumerate(leaderboard_data) if d['user_id'] == user.id), None)
            if user_rank:
                rank_emoji = medals[user_rank-1] if user_rank <= 3 else "🎖️"
                game_embed.add_field(
                    name="📍 Dein Rang",
                    value=f"{rank_emoji} **Platz {user_rank}** von {len(leaderboard_data)} Spielern",
                    inline=False
                )
            
            # Fetch game image from the API
            api_response, _ = await get_game_details_from_api([fav_game_name], config, GEMINI_API_KEY, OPENAI_API_KEY)
            game_image_url = api_response.get(fav_game_name, {}).get('image') if api_response else None
            
            if game_image_url:
                game_embed.set_thumbnail(url=game_image_url)

            game_embed.set_footer(text="Verglichen mit anderen Spielern dieses Spiels auf dem Server.")
            pages.append(game_embed)

    # --- Page 7: Enhanced Spotify Wrapped Page ---
    if user_stats.get('spotify_minutes'):
        spotify_minutes_data = json.loads(user_stats['spotify_minutes'])
        if spotify_minutes_data:
            total_minutes = sum(spotify_minutes_data.values())
            total_hours = total_minutes / 60
            
            # Sort songs by listening time
            sorted_songs = sorted(spotify_minutes_data.items(), key=lambda item: item[1], reverse=True)
            
            # Build top songs with enhanced styling
            song_lines = []
            medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
            for i, (song, minutes) in enumerate(sorted_songs[:5]):
                medal = medals[i] if i < len(medals) else f"**{i+1}.**"
                song_lines.append(f"{medal} `{song}` - *{minutes:.0f} Min.*")

            # Calculate Top Artists
            artist_minutes = {}
            for song_key, minutes in spotify_minutes_data.items():
                try:
                    artist = song_key.split(' by ')[1]
                    artist_minutes[artist] = artist_minutes.get(artist, 0) + minutes
                except IndexError:
                    continue
            
            sorted_artists = sorted(artist_minutes.items(), key=lambda item: item[1], reverse=True)
            artist_lines = []
            for i, (artist, minutes) in enumerate(sorted_artists[:5]):
                medal = medals[i] if i < len(medals) else f"**{i+1}.**"
                artist_lines.append(f"{medal} **{artist}** - *{minutes:.0f} Min.*")

            if song_lines:
                spotify_embed = discord.Embed(
                    title="🎵 Dein Spotify-Rückblick",
                    description="*Was lief diesen Monat in deiner Playlist?*",
                    color=WRAPPED_COLORS['spotify']
                )
                
                # Total listening time with fun comparison
                songs_listened = total_minutes / 3.5  # Average song ~3.5 min
                spotify_embed.add_field(
                    name="⏱️ Gesamte Hörzeit",
                    value=f"## `{total_hours:.1f}` Stunden\n*~{int(songs_listened)} Songs*",
                    inline=False
                )
                
                spotify_embed.add_field(
                    name="🎶 Deine Top 5 Songs",
                    value="\n".join(song_lines),
                    inline=False
                )
                
                if artist_lines:
                    spotify_embed.add_field(
                        name="🎤 Deine Top 5 Künstler",
                        value="\n".join(artist_lines),
                        inline=False
                    )
                
                # Add fun music fact
                if sorted_artists:
                    top_artist = sorted_artists[0][0]
                    spotify_embed.set_footer(text=f"Du bist wohl ein großer {top_artist}-Fan! 🎧")
                
                pages.append(spotify_embed)

    # --- Enhanced Quest & Game Stats Page ---
    if extra_stats.get('quests_completed', 0) > 0 or extra_stats.get('games_played', 0) > 0:
        quest_game_embed = discord.Embed(
            title="📋 Quests & Gambling",
            description="*Deine Bot-Aktivitäten im Überblick*",
            color=WRAPPED_COLORS['quests']
        )
        
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
            
            currency = get_nested_config(config, 'modules', 'economy', 'currency_symbol', default='💰')
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

    # --- Enhanced Detective Game Stats Page ---
    if extra_stats.get('detective_total_cases', 0) > 0:
        detective_embed = discord.Embed(
            title="🔍 Detective Game Rückblick",
            description="*Deine Ermittlungen diesen Monat*",
            color=WRAPPED_COLORS['detective']
        )
        
        cases_solved = extra_stats.get('detective_cases_solved', 0)
        cases_failed = extra_stats.get('detective_cases_failed', 0)
        total_cases = extra_stats.get('detective_total_cases', 0)
        solve_rate = (cases_solved / total_cases * 100) if total_cases > 0 else 0
        
        detective_embed.add_field(
            name="📊 Fallübersicht",
            value=f"```\n"
                  f"📁 Bearbeitet:   {total_cases}\n"
                  f"✅ Gelöst:       {cases_solved}\n"
                  f"❌ Gescheitert:  {cases_failed}\n"
                  f"📈 Quote:        {solve_rate:.0f}%\n"
                  f"```",
            inline=False
        )
        
        # Add rating with visual progress bar (clamped to prevent overflow)
        progress_filled = min(int(solve_rate / 10), 10)
        progress_bar = "█" * progress_filled + "░" * (10 - progress_filled)
        detective_embed.add_field(
            name="📉 Erfolgsbalken",
            value=f"`[{progress_bar}]` {solve_rate:.0f}%",
            inline=False
        )
        
        # Add rating based on solve rate
        if solve_rate >= 80:
            rating = "🏆 **Meisterdetektiv!**\n*Du bist ein wahrer Sherlock Holmes!*"
        elif solve_rate >= 60:
            rating = "🎖️ **Erfahrener Ermittler!**\n*Solide Arbeit, Watson wäre stolz!*"
        elif solve_rate >= 40:
            rating = "🔍 **Kompetenter Detective!**\n*Auf dem richtigen Weg!*"
        else:
            rating = "📝 **Noch in Ausbildung!**\n*Übung macht den Meister!*"
        
        detective_embed.add_field(name="🎭 Dein Rang", value=rating, inline=False)
        detective_embed.set_footer(text="Jeder gelöste Fall bringt dich näher zur nächsten Schwierigkeitsstufe!")
        pages.append(detective_embed)
    
    # --- Enhanced Shop & Purchases Page ---
    if extra_stats.get('total_purchases', 0) > 0:
        shop_embed = discord.Embed(
            title="🛍️ Shopping Rückblick",
            description="*Deine Einkäufe diesen Monat*",
            color=WRAPPED_COLORS['shop']
        )
        
        total_purchases = extra_stats.get('total_purchases', 0)
        most_bought = extra_stats.get('most_bought_item')
        most_bought_count = extra_stats.get('most_bought_item_count', 0)
        
        shop_embed.add_field(
            name="🧾 Gesamte Käufe",
            value=f"## `{total_purchases}`",
            inline=True
        )
        
        if most_bought:
            shop_embed.add_field(
                name="⭐ Favorit",
                value=f"**{most_bought}**\n*({most_bought_count}x gekauft)*",
                inline=True
            )
        
        # Add shopping personality
        if total_purchases >= 20:
            personality = "💸 **Shopping-Süchtiger!**\nDu liebst es einzukaufen!"
        elif total_purchases >= 10:
            personality = "🛒 **Fleißiger Käufer!**\nDu weißt, was du willst!"
        else:
            personality = "💰 **Sparfuchs!**\nDu gibst dein Geld mit Bedacht aus!"
        
        shop_embed.add_field(
            name="🎭 Dein Shopping-Typ",
            value=personality,
            inline=False
        )
        
        shop_embed.set_footer(text="Schau im /shop vorbei für neue Items!")
        pages.append(shop_embed)

    # --- Enhanced Final Page: AI Summary ---
    gemini_stats = {
        "message_count": total_messages, 
        "avg_message_count": server_averages['avg_messages'],
        "vc_hours": vc_hours, 
        "avg_vc_hours": server_averages['avg_vc_minutes'] / 60,
        "message_rank_text": message_rank_text, 
        "vc_rank_text": vc_rank_text
    }
    
    # Add activity if it exists
    if 'activity_embed' in locals() and activity_embed.fields:
        field_value = activity_embed.fields[-1].value
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
    
    # Replace emoji tags in the summary text
    summary_text_formatted = await replace_emoji_tags(summary_text, client, guild)
    
    summary_embed = discord.Embed(
        title="✨ Mein Urteil über dich",
        description=f"*Was die KI über deinen Monat zu sagen hat...*\n\n"
                    f"## _{summary_text_formatted}_",
        color=WRAPPED_COLORS['summary']
    )
    summary_embed.set_thumbnail(url=user.display_avatar.url)
    
    # Add a closing message
    summary_embed.add_field(
        name="🎬 Das war's!",
        value=f"Danke fürs Durchschauen, **{user.display_name}**!\n\n"
              f"*Wir sehen uns nächsten Monat mit neuen Stats!* 👋",
        inline=False
    )
    summary_embed.set_footer(text="Teile deine Lieblings-Seite mit dem 🔗 Button!")
    pages.append(summary_embed)

    # Send the wrapped to the user
    view = WrappedView(pages, user)
    try:
        await view.send_initial_message()
        print(f"  - [Wrapped] Successfully sent DM to {user.name}.")
    except (discord.Forbidden, discord.HTTPException) as e:
        print(f"  - [Wrapped] FAILED to DM {user.name} (DMs likely closed or another Discord error occurred): {e}")
        # Re-raise the exception only in admin preview context so caller knows it failed
        if raise_on_dm_failure:
            raise

def _get_percentile_rank(user_id, rank_map, total_users):
    """Helper function to calculate a user's percentile rank from a sorted list."""
    if total_users < 2: return "Top 100%" # Avoid division by zero
    try:
        # The rank map gives us the 0-indexed rank directly
        user_rank = rank_map.get(user_id, total_users - 1)
        # --- FIX: Correctly calculate the percentile ---
        # This now represents the percentage of users you are ranked higher than.
        percentile = ((total_users - 1 - user_rank) / (total_users - 1)) * 100

        # --- NEW: Use ranks from config file with defensive access ---
        ranks = config.get('modules', {}).get('wrapped', {}).get('percentile_ranks', {})
        if not ranks:
            return "N/A"
        
        # We sort the keys numerically to ensure correct order, ignoring 'default'.
        sorted_thresholds = sorted([int(k) for k in ranks.keys() if k.isdigit()])

        for threshold in sorted(ranks.keys(), key=lambda x: int(x) if x.isdigit() else 999, reverse=True):
            if threshold.isdigit() and percentile >= (100 - int(threshold)):
                return ranks[str(threshold)]
        
        return ranks.get("default", "N/A")
    except (KeyError, ValueError, TypeError) as e:
        logger.debug(f"Error calculating percentile rank: {e}")
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
        
        # --- NEW: Track voice activity for bot mind ---
        now = discord.utils.utcnow()
        
        # Track voice call sessions
        if after.channel:
            # User is in voice
            duration = 0
            if member.id in vc_session_starts:
                duration = (now - vc_session_starts[member.id]).total_seconds() / 60  # minutes
            
            # Check if user is alone
            alone = len([m for m in after.channel.members if not m.bot]) == 1
            
            try:
                bot_mind.bot_mind.observe_user_activity(
                    member.id,
                    member.display_name,
                    'voice',
                    {
                        'in_call': True,
                        'channel_name': after.channel.name,
                        'alone': alone,
                        'duration': duration,
                        'members': len(after.channel.members) - 1  # Exclude bot if present
                    }
                )
            except (AttributeError, Exception) as e:
                logger.debug(f"Could not track voice for bot mind: {e}")
        elif before.channel:
            # User left voice
            try:
                bot_mind.bot_mind.observe_user_activity(
                    member.id,
                    member.display_name,
                    'voice',
                    {
                        'in_call': False
                    }
                )
            except (AttributeError, Exception) as e:
                logger.debug(f"Could not track voice leave for bot mind: {e}")
        
        # --- NEW: Track longest voice session ---
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

    # --- NEW: Handle music player auto-disconnect ---
    # Check if bot's voice client needs to handle empty channel
    if member.guild.voice_client:
        await lofi_player.on_voice_state_update_handler(member.guild.voice_client, member.guild.id)

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
        
        try:
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
            # Set raise_on_dm_failure=True so we get error details for the admin
            await _generate_and_send_wrapped_for_user(
                user_stats=target_user_stats,
                stat_period_date=last_month_first_day,
                all_stats_for_period=all_stats,
                total_users=len(all_stats),
                server_averages=await _calculate_server_averages(all_stats),
                raise_on_dm_failure=True
            )

            await interaction.followup.send(f"Eine 'Wrapped'-Vorschau für `{stat_period}` wurde an {user.mention} gesendet.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error in view_wrapped command: {e}", exc_info=True)
            # Show the actual error to the admin
            error_details = f"{type(e).__name__}: {str(e)}"
            # Truncate error details if too long while preserving markdown structure
            if len(error_details) > DISCORD_ERROR_MESSAGE_MAX_LENGTH:
                error_details = error_details[:DISCORD_ERROR_MESSAGE_MAX_LENGTH] + "... (truncated)"
            error_msg = f"❌ Fehler beim Generieren der Wrapped-Vorschau:\n```python\n{error_details}\n```"
            await interaction.followup.send(error_msg, ephemeral=True)

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

    @app_commands.command(name="emojis", description="Zeigt alle Application Emojis und ihren Status an.")
    async def emojis(self, interaction: discord.Interaction):
        """Shows all application emojis and their configuration status."""
        await interaction.response.defer(ephemeral=True)
        
        # Constants for display limits
        MAX_EMOJI_DISPLAY = 10
        
        try:
            # Fetch application emojis
            app_emojis = await client.fetch_application_emojis()
            
            # Load configured emojis
            emoji_config_path = os.path.join("config", "server_emojis.json")
            configured_emojis = {}
            if os.path.exists(emoji_config_path):
                with open(emoji_config_path, 'r', encoding='utf-8') as f:
                    emoji_config = json.load(f)
                    configured_emojis = emoji_config.get('emojis', {})
            
            # Create embed
            embed = discord.Embed(
                title="🎭 Application Emojis",
                description=f"Der Bot hat **{len(app_emojis)}** Application Emojis (Limit: 50)",
                color=get_embed_color(config)
            )
            
            if app_emojis:
                # Check which are configured
                app_emoji_names = {e.name for e in app_emojis}
                configured_found = [name for name in configured_emojis.keys() if name in app_emoji_names]
                configured_missing = [name for name in configured_emojis.keys() if name not in app_emoji_names]
                
                # Show configured emojis that exist
                if configured_found:
                    emoji_list = []
                    for name in configured_found[:MAX_EMOJI_DISPLAY]:
                        emoji_obj = next((e for e in app_emojis if e.name == name), None)
                        if emoji_obj:
                            emoji_type = "🎬" if emoji_obj.animated else "🖼️"
                            emoji_list.append(f"{emoji_type} `:{name}:` - {configured_emojis[name].get('description', 'N/A')}")
                    
                    more_text = f"\n*...und {len(configured_found) - MAX_EMOJI_DISPLAY} weitere*" if len(configured_found) > MAX_EMOJI_DISPLAY else ""
                    embed.add_field(
                        name=f"✅ Konfigurierte Emojis ({len(configured_found)})",
                        value="\n".join(emoji_list) + more_text,
                        inline=False
                    )
                
                # Show missing configured emojis
                if configured_missing:
                    missing_list = ", ".join([f"`:{name}:`" for name in configured_missing[:MAX_EMOJI_DISPLAY]])
                    if len(configured_missing) > MAX_EMOJI_DISPLAY:
                        missing_list += f" *...und {len(configured_missing) - MAX_EMOJI_DISPLAY} weitere*"
                    embed.add_field(
                        name=f"⚠️ Fehlende Konfigurierte Emojis ({len(configured_missing)})",
                        value=f"{missing_list}\n\n*Diese müssen als Application Emojis hochgeladen werden!*",
                        inline=False
                    )
                
                # Show unconfigured application emojis
                unconfigured = [e for e in app_emojis if e.name not in configured_emojis]
                if unconfigured:
                    unconfigured_list = []
                    for emoji in unconfigured[:MAX_EMOJI_DISPLAY]:
                        emoji_type = "🎬" if emoji.animated else "🖼️"
                        unconfigured_list.append(f"{emoji_type} `:{emoji.name}:`")
                    
                    more_text = f"\n*...und {len(unconfigured) - MAX_EMOJI_DISPLAY} weitere*" if len(unconfigured) > MAX_EMOJI_DISPLAY else ""
                    embed.add_field(
                        name=f"📦 Unkonfigurierte Emojis ({len(unconfigured)})",
                        value="\n".join(unconfigured_list) + more_text,
                        inline=False
                    )
                
                embed.set_footer(text="Tipp: Verwende das Diagnostic-Script 'check_application_emojis.py' für detaillierte Informationen")
            else:
                embed.add_field(
                    name="❌ Keine Application Emojis",
                    value="Der Bot hat keine Application Emojis.\n"
                          "Emojis müssen im Discord Developer Portal hochgeladen werden:\n"
                          "https://discord.com/developers/applications",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in emojis command: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Fehler beim Abrufen der Emojis: `{e}`")

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


# --- REFACTORED: Admin AI/Mind Management Commands Group ---
@app_commands.check(is_admin_or_authorised)
class AdminAIGroup(app_commands.Group):
    """Admin-Befehle für KI- und Mind-Verwaltung."""

    @app_commands.command(name="mind", description="[Debug] Zeigt den aktuellen mentalen Zustand des Bots an.")
    async def mind(self, interaction: discord.Interaction):
        """Displays the bot's current mental state (mood, activity, thoughts)."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            mind_state = bot_mind.get_mind_state_api()
            
            embed = discord.Embed(
                title="🧠 Bot Mind Status",
                description=bot_mind.get_state_summary(),
                color=get_embed_color(config)
            )
            
            # Mood and Activity
            embed.add_field(
                name="Current Mood", 
                value=f"**{mind_state['mood'].title()}**\n_{bot_mind.get_mood_description()}_", 
                inline=True
            )
            embed.add_field(
                name="Current Activity", 
                value=f"**{mind_state['activity'].title()}**\n_{bot_mind.get_activity_description()}_", 
                inline=True
            )
            
            # Energy and Boredom
            energy_bar = '█' * int(mind_state['energy_level'] * 10) + '░' * (10 - int(mind_state['energy_level'] * 10))
            boredom_bar = '█' * int(mind_state['boredom_level'] * 10) + '░' * (10 - int(mind_state['boredom_level'] * 10))
            embed.add_field(
                name="Energy & Boredom",
                value=f"⚡ Energy: `{energy_bar}` {mind_state['energy_level']:.1%}\n😴 Boredom: `{boredom_bar}` {mind_state['boredom_level']:.1%}",
                inline=False
            )
            
            # Current Thought
            embed.add_field(
                name="💭 Current Thought",
                value=f"_{mind_state['current_thought']}_",
                inline=False
            )
            
            # Personality Traits
            traits_str = "\n".join([f"**{k.title()}**: {v:.1%}" for k, v in mind_state['personality_traits'].items()])
            embed.add_field(
                name="Personality Traits",
                value=traits_str,
                inline=False
            )
            
            # Recent Interests
            if mind_state.get('interests'):
                interests_str = ", ".join(mind_state['interests'][-5:])
                embed.add_field(
                    name="Recent Interests",
                    value=interests_str if interests_str else "None yet",
                    inline=False
                )
            
            embed.set_footer(text=f"Last thought at: {mind_state['last_thought_time']}")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in mind command: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Error viewing mind state: {e}")

    @app_commands.command(name="mind_history", description="[Debug] Zeigt die letzten Gedanken des Bots an.")
    @app_commands.describe(limit="Anzahl der anzuzeigenden Gedanken (max 20)")
    async def mind_history(self, interaction: discord.Interaction, limit: int = 10):
        """Displays the bot's recent thought history."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            limit = min(max(1, limit), 20)  # Clamp between 1 and 20
            mind_state = bot_mind.get_mind_state_api()
            thoughts = mind_state.get('recent_thoughts', [])
            
            if not thoughts:
                await interaction.followup.send("No thoughts recorded yet.")
                return
            
            embed = discord.Embed(
                title="🧠 Recent Thoughts",
                description=f"Last {min(limit, len(thoughts))} thoughts",
                color=get_embed_color(config)
            )
            
            for i, thought_data in enumerate(thoughts[-limit:], 1):
                thought = thought_data.get('thought', 'Unknown')
                mood = thought_data.get('mood', 'unknown')
                timestamp = thought_data.get('time', 'Unknown')
                
                # Parse timestamp for better display
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(timestamp)
                    time_str = dt.strftime('%H:%M:%S')
                except:
                    time_str = timestamp
                
                embed.add_field(
                    name=f"{i}. {mood.title()} @ {time_str}",
                    value=f"_{thought}_",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in mind_history command: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Error viewing thought history: {e}")

    @app_commands.command(name="mind_set", description="[Debug] Setzt den mentalen Zustand des Bots manuell.")
    @app_commands.describe(
        mood="Die neue Stimmung",
        activity="Die neue Aktivität"
    )
    @app_commands.choices(mood=[
        app_commands.Choice(name="Happy", value="happy"),
        app_commands.Choice(name="Excited", value="excited"),
        app_commands.Choice(name="Curious", value="curious"),
        app_commands.Choice(name="Neutral", value="neutral"),
        app_commands.Choice(name="Bored", value="bored"),
        app_commands.Choice(name="Confused", value="confused"),
        app_commands.Choice(name="Sarcastic", value="sarcastic"),
        app_commands.Choice(name="Mischievous", value="mischievous"),
        app_commands.Choice(name="Contemplative", value="contemplative"),
    ])
    @app_commands.choices(activity=[
        app_commands.Choice(name="Idle", value="idle"),
        app_commands.Choice(name="Observing", value="observing"),
        app_commands.Choice(name="Thinking", value="thinking"),
        app_commands.Choice(name="Chatting", value="chatting"),
        app_commands.Choice(name="Planning", value="planning"),
        app_commands.Choice(name="Learning", value="learning"),
        app_commands.Choice(name="Scheming", value="scheming"),
        app_commands.Choice(name="Daydreaming", value="daydreaming"),
    ])
    async def mind_set(self, interaction: discord.Interaction, mood: str = None, activity: str = None):
        """Manually sets the bot's mood and/or activity for testing."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            changes = []
            
            if mood:
                bot_mind.bot_mind.update_mood(bot_mind.Mood(mood), f"Manually set by admin {interaction.user.name}")
                changes.append(f"Mood → **{mood.title()}**")
            
            if activity:
                bot_mind.bot_mind.update_activity(bot_mind.Activity(activity))
                changes.append(f"Activity → **{activity.title()}**")
            
            if not changes:
                await interaction.followup.send("❌ No changes specified. Please provide at least one parameter.")
                return
            
            changes_str = "\n".join(changes)
            await interaction.followup.send(f"✅ Mind state updated:\n{changes_str}")
            logger.info(f"Admin {interaction.user.name} updated mind state: {changes_str}")
            
        except Exception as e:
            logger.error(f"Error in mind_set command: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Error setting mind state: {e}")

    @app_commands.command(name="context", description="[Debug] Zeigt den Konversationskontext für einen Kanal an.")
    @app_commands.describe(channel="Der Kanal (optional, Standard: aktueller Kanal)")
    async def context(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        """Displays the conversation context for a channel."""
        await interaction.response.defer(ephemeral=True)
        
        target_channel = channel or interaction.channel
        
        try:
            context_messages = await db_helpers.get_conversation_context(target_channel.id)
            
            if not context_messages:
                await interaction.followup.send(f"No conversation context found for {target_channel.mention}.")
                return
            
            embed = discord.Embed(
                title=f"💬 Conversation Context: #{target_channel.name}",
                description=f"Last {len(context_messages)} messages in context window",
                color=get_embed_color(config)
            )
            
            # Group by role
            user_msgs = [m for m in context_messages if m['role'] == 'user']
            bot_msgs = [m for m in context_messages if m['role'] == 'model']
            
            embed.add_field(
                name="Statistics",
                value=f"**User Messages**: {len(user_msgs)}\n**Bot Messages**: {len(bot_msgs)}\n**Total**: {len(context_messages)}",
                inline=False
            )
            
            # Show last few messages
            last_msgs = context_messages[-5:]
            msgs_preview = []
            for msg in last_msgs:
                role_icon = "🤖" if msg['role'] == 'model' else "👤"
                content = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
                msgs_preview.append(f"{role_icon} {content}")
            
            if msgs_preview:
                embed.add_field(
                    name="Recent Messages",
                    value="\n".join(msgs_preview),
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in context command: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Error viewing context: {e}")

    @app_commands.command(name="test_ai", description="[Debug] Testet die KI-Antwort mit einem benutzerdefinierten Prompt.")
    @app_commands.describe(prompt="Der Test-Prompt")
    async def test_ai(self, interaction: discord.Interaction, prompt: str):
        """Tests AI response with a custom prompt."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Call AI with test prompt
            response = await get_chat_response(
                prompt=prompt,
                user_id=interaction.user.id,
                username=interaction.user.display_name,
                config=config,
                gemini_key=GEMINI_API_KEY,
                openai_key=OPENAI_API_KEY
            )
            
            if not response:
                await interaction.followup.send("❌ AI returned no response.")
                return
            
            # Get current provider
            current_provider = await get_current_provider(config)
            model_name = config['api'][current_provider]['model'] if current_provider == 'gemini' else config['api'][current_provider]['chat_model']
            
            embed = discord.Embed(
                title="🤖 AI Test Response",
                description=response[:4000],  # Discord embed description limit
                color=get_embed_color(config)
            )
            embed.add_field(name="Provider", value=current_provider.title(), inline=True)
            embed.add_field(name="Model", value=f"`{model_name}`", inline=True)
            embed.add_field(name="Prompt Length", value=f"{len(prompt)} chars", inline=True)
            embed.set_footer(text=f"Response length: {len(response)} chars")
            
            await interaction.followup.send(embed=embed)
            logger.info(f"Admin {interaction.user.name} tested AI with prompt: {prompt[:50]}...")
            
        except Exception as e:
            logger.error(f"Error in test_ai command: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Error testing AI: {e}")

    @app_commands.command(name="observations", description="[Debug] Zeigt die letzten Beobachtungen des Bots an.")
    @app_commands.describe(limit="Anzahl der anzuzeigenden Beobachtungen (max 15)")
    async def observations(self, interaction: discord.Interaction, limit: int = 10):
        """Displays the bot's recent observations."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            limit = min(max(1, limit), 15)
            mind_state = bot_mind.get_mind_state_api()
            observations = mind_state.get('recent_observations', [])
            
            if not observations:
                await interaction.followup.send("No observations recorded yet.")
                return
            
            embed = discord.Embed(
                title="👁️ Recent Observations",
                description=f"Last {min(limit, len(observations))} observations",
                color=get_embed_color(config)
            )
            
            for i, obs_data in enumerate(observations[-limit:], 1):
                observation = obs_data.get('observation', 'Unknown')
                timestamp = obs_data.get('time', 'Unknown')
                
                # Parse timestamp for better display
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(timestamp)
                    time_str = dt.strftime('%H:%M:%S')
                except:
                    time_str = timestamp
                
                embed.add_field(
                    name=f"{i}. @ {time_str}",
                    value=observation,
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in observations command: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Error viewing observations: {e}")

    @app_commands.command(name="trigger_thought", description="[Debug] Erzwingt, dass der Bot einen neuen Gedanken generiert.")
    async def trigger_thought(self, interaction: discord.Interaction):
        """Forces the bot to generate a new thought."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Gather context
            online_count = sum(1 for guild in client.guilds for member in guild.members 
                              if not member.bot and member.status != discord.Status.offline)
            
            context = {
                'online_users': online_count,
                'recent_activity': 'active' if online_count > 5 else 'quiet'
            }
            
            # Generate thought using bot_mind module with correct parameters
            thought = await bot_mind.generate_random_thought(context, get_chat_response, config, GEMINI_API_KEY, OPENAI_API_KEY)
            bot_mind.bot_mind.think(thought)
            
            embed = discord.Embed(
                title="💭 New Thought Generated",
                description=f"_{thought}_",
                color=get_embed_color(config)
            )
            embed.add_field(name="Current Mood", value=bot_mind.bot_mind.current_mood.value.title(), inline=True)
            embed.add_field(name="Online Users", value=str(online_count), inline=True)
            
            await interaction.followup.send(embed=embed)
            logger.info(f"Admin {interaction.user.name} triggered thought generation")
            
        except Exception as e:
            logger.error(f"Error in trigger_thought command: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Error generating thought: {e}")

    @app_commands.command(name="interests", description="[Debug] Zeigt und verwaltet die Interessen des Bots.")
    @app_commands.describe(
        action="Was möchtest du tun?",
        interest="Das Interesse (für add/remove)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="View All", value="view"),
        app_commands.Choice(name="Add Interest", value="add"),
        app_commands.Choice(name="Remove Interest", value="remove"),
        app_commands.Choice(name="Clear All", value="clear"),
    ])
    async def interests(self, interaction: discord.Interaction, action: str, interest: str = None):
        """Manages the bot's interests."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            if action == "view":
                mind_state = bot_mind.get_mind_state_api()
                interests_list = mind_state.get('interests', [])
                
                if not interests_list:
                    await interaction.followup.send("Bot has no interests yet.")
                    return
                
                embed = discord.Embed(
                    title="🎯 Bot Interests",
                    description=f"Total: {len(interests_list)} interests",
                    color=get_embed_color(config)
                )
                
                # Show interests in batches
                interests_str = ", ".join(interests_list[-30:])  # Last 30
                embed.add_field(
                    name="Recent Interests",
                    value=interests_str if interests_str else "None",
                    inline=False
                )
                
                await interaction.followup.send(embed=embed)
                
            elif action == "add":
                if not interest:
                    await interaction.followup.send("❌ Please specify an interest to add.")
                    return
                
                bot_mind.bot_mind.add_interest(interest)
                await interaction.followup.send(f"✅ Added interest: **{interest}**")
                logger.info(f"Admin {interaction.user.name} added interest: {interest}")
                
            elif action == "remove":
                if not interest:
                    await interaction.followup.send("❌ Please specify an interest to remove.")
                    return
                
                if interest in bot_mind.bot_mind.interests:
                    bot_mind.bot_mind.interests.remove(interest)
                    await interaction.followup.send(f"✅ Removed interest: **{interest}**")
                    logger.info(f"Admin {interaction.user.name} removed interest: {interest}")
                else:
                    await interaction.followup.send(f"❌ Interest **{interest}** not found.")
                    
            elif action == "clear":
                count = len(bot_mind.bot_mind.interests)
                bot_mind.bot_mind.interests = []
                await interaction.followup.send(f"✅ Cleared {count} interests.")
                logger.info(f"Admin {interaction.user.name} cleared all interests")
            
        except Exception as e:
            logger.error(f"Error in interests command: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Error managing interests: {e}")

    @app_commands.command(name="autonomous_status", description="[Debug] Zeigt den Status des autonomen Verhaltens an.")
    async def autonomous_status(self, interaction: discord.Interaction):
        """Displays autonomous behavior status."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get stats from database
            conn = db_helpers.get_db_connection()
            if not conn:
                await interaction.followup.send("❌ Error: Could not connect to database")
                return
            
            cursor = conn.cursor()
            try:
                # Count recent autonomous actions
                cursor.execute("""
                    SELECT action_type, COUNT(*) as count, 
                           SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful
                    FROM bot_autonomous_actions
                    WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                    GROUP BY action_type
                """)
                action_stats = cursor.fetchall()
                
                # Count users who opted out
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM user_autonomous_settings
                    WHERE allow_autonomous_messages = FALSE OR allow_autonomous_calls = FALSE
                """)
                opted_out_result = cursor.fetchone()
                opted_out = opted_out_result[0] if opted_out_result else 0
            finally:
                cursor.close()
                conn.close()
            
            embed = discord.Embed(
                title="🤖 Autonomous Behavior Status",
                description="Statistics from the last 7 days",
                color=get_embed_color(config)
            )
            
            if action_stats:
                for action_type, count, successful in action_stats:
                    success_rate = (successful / count * 100) if count > 0 else 0
                    embed.add_field(
                        name=f"{action_type.replace('_', ' ').title()}",
                        value=f"**Total**: {count}\n**Successful**: {successful} ({success_rate:.1f}%)",
                        inline=True
                    )
            else:
                embed.add_field(
                    name="No Actions",
                    value="No autonomous actions recorded in the last 7 days.",
                    inline=False
                )
            
            embed.add_field(
                name="User Settings",
                value=f"**Users who opted out**: {opted_out}",
                inline=False
            )
            
            # Add mind state info
            embed.add_field(
                name="Current Mind State",
                value=f"**Boredom**: {bot_mind.bot_mind.boredom_level:.1%} (triggers autonomous behavior when high)",
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in autonomous_status command: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Error viewing autonomous status: {e}")

    @app_commands.command(name="debug_ai_reasoning", description="[Debug] Zeigt den Denkprozess der KI für eine Anfrage an.")
    @app_commands.describe(prompt="Die Anfrage zum Analysieren")
    async def debug_ai_reasoning(self, interaction: discord.Interaction, prompt: str):
        """Shows AI reasoning process for a query."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            from modules.advanced_ai import get_advanced_ai_response, get_reasoning_breakdown
            
            # Get AI response with reasoning
            response, error, metadata = await get_advanced_ai_response(
                prompt=prompt,
                user_id=interaction.user.id,
                channel_id=interaction.channel_id,
                username=interaction.user.display_name,
                config=config,
                gemini_key=GEMINI_API_KEY,
                openai_key=OPENAI_API_KEY,
                system_prompt=config['bot']['system_prompt'],
                use_cache=False  # Don't use cache for debugging
            )
            
            if error:
                await interaction.followup.send(f"❌ Error: {error}")
                return
                
            # Get reasoning breakdown
            breakdown = await get_reasoning_breakdown(prompt, response, metadata)
            
            embed = discord.Embed(
                title="🧠 AI Reasoning Breakdown",
                description=breakdown,
                color=get_embed_color(config)
            )
            
            # Add response preview
            response_preview = response[:500] + "..." if len(response) > 500 else response
            embed.add_field(
                name="Generated Response",
                value=response_preview,
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
            logger.info(f"Admin {interaction.user.name} debugged AI reasoning")
            
        except Exception as e:
            logger.error(f"Error in debug_ai_reasoning command: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Error: {e}")

    @app_commands.command(name="debug_tokens", description="[Debug] Zeigt Token-Nutzung und Budgets an.")
    async def debug_tokens(self, interaction: discord.Interaction):
        """Shows detailed token usage statistics."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            from modules.advanced_ai import get_context_manager
            
            # Get context manager for this channel
            context_mgr = get_context_manager(interaction.channel_id)
            
            # Calculate current token usage
            current_tokens = context_mgr.get_current_token_count()
            context_size = len(context_mgr.context_window)
            compressed_count = len(context_mgr.compressed_summaries)
            
            # Get API usage from database
            async with db_helpers.get_db_connection() as (conn, cursor):
                # Last 24 hours usage
                await cursor.execute("""
                    SELECT 
                        model_name,
                        SUM(input_tokens) as total_input,
                        SUM(output_tokens) as total_output,
                        COUNT(*) as call_count
                    FROM api_usage_log
                    WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                    GROUP BY model_name
                    ORDER BY total_input + total_output DESC
                """)
                usage_stats = await cursor.fetchall()
            
            embed = discord.Embed(
                title="🔢 Token Usage & Budget",
                description=f"Current Channel: <#{interaction.channel_id}>",
                color=get_embed_color(config)
            )
            
            # Current context
            token_bar = '█' * int(current_tokens / context_mgr.token_budget * 20)
            token_bar += '░' * (20 - len(token_bar))
            embed.add_field(
                name="Current Context",
                value=f"`{token_bar}` {current_tokens}/{context_mgr.token_budget} tokens\n"
                      f"**Messages**: {context_size}\n"
                      f"**Compressed Summaries**: {compressed_count}",
                inline=False
            )
            
            # API usage (last 24h)
            if usage_stats:
                usage_text = []
                total_input = 0
                total_output = 0
                for model, inp, out, count in usage_stats:
                    total_input += inp
                    total_output += out
                    usage_text.append(f"**{model}**: {count} calls\n  ↓ {inp:,} in / ↑ {out:,} out")
                
                embed.add_field(
                    name="API Usage (Last 24h)",
                    value="\n".join(usage_text[:3]),  # Top 3 models
                    inline=False
                )
                
                embed.add_field(
                    name="Total (24h)",
                    value=f"**Input**: {total_input:,} tokens\n**Output**: {total_output:,} tokens\n**Total**: {total_input + total_output:,} tokens",
                    inline=False
                )
            else:
                embed.add_field(
                    name="API Usage (Last 24h)",
                    value="No usage recorded",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
            logger.info(f"Admin {interaction.user.name} viewed token debug info")
            
        except Exception as e:
            logger.error(f"Error in debug_tokens command: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Error: {e}")


    @app_commands.command(name="debug_memory", description="[Debug] Zeigt den Speicherzustand des Bots an.")
    async def debug_memory(self, interaction: discord.Interaction):
        """Shows bot memory state."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            from modules.advanced_ai import get_context_manager, _response_cache
            
            # Get context for this channel
            context_mgr = get_context_manager(interaction.channel_id)
            
            # Get cache statistics
            cache_size = len(_response_cache.cache)
            
            # Get database statistics
            conn = db_helpers.get_db_connection()
            if conn:
                cursor = conn.cursor()
                try:
                    # Recent conversations
                    cursor.execute("""
                        SELECT COUNT(DISTINCT channel_id) as channels,
                               COUNT(*) as messages
                        FROM conversation_context
                        WHERE created_at >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
                    """)
                    recent_conv = cursor.fetchone()
                    
                    # Personality evolution
                    cursor.execute("""
                        SELECT COUNT(*) as evolution_events
                        FROM personality_evolution
                        WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                    """)
                    personality_changes = cursor.fetchone()
                    
                    # Learning entries
                    cursor.execute("""
                        SELECT COUNT(*) as learnings,
                               AVG(confidence) as avg_confidence
                        FROM interaction_learnings
                        WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                    """)
                    learning_stats = cursor.fetchone()
                finally:
                    cursor.close()
                    conn.close()
            else:
                recent_conv = (0, 0)
                personality_changes = (0,)
                learning_stats = (0, 0.0)
            
            embed = discord.Embed(
                title="🧠 Bot Memory State",
                description="Current memory and learning status",
                color=get_embed_color(config)
            )
            
            # Context window
            embed.add_field(
                name="Context Window (This Channel)",
                value=f"**Messages**: {len(context_mgr.context_window)}/{context_mgr.context_window.maxlen}\n"
                      f"**Compressed Summaries**: {len(context_mgr.compressed_summaries)}\n"
                      f"**Estimated Tokens**: {context_mgr.get_current_token_count()}",
                inline=True
            )
            
            # Response cache
            embed.add_field(
                name="Response Cache",
                value=f"**Cached Responses**: {cache_size}/100\n"
                      f"**Cache Hits**: Token savings enabled",
                inline=True
            )
            
            # Recent activity
            channels = recent_conv[0] if recent_conv else 0
            messages = recent_conv[1] if recent_conv else 0
            embed.add_field(
                name="Recent Activity (1h)",
                value=f"**Active Channels**: {channels}\n"
                      f"**Conversations**: {messages}",
                inline=True
            )
            
            # Learning
            learnings = learning_stats[0] if learning_stats else 0
            avg_conf = learning_stats[1] if learning_stats and learning_stats[1] else 0
            embed.add_field(
                name="Learning (7 days)",
                value=f"**New Learnings**: {learnings}\n"
                      f"**Avg Confidence**: {avg_conf:.1%}",
                inline=True
            )
            
            # Personality evolution
            evolutions = personality_changes[0] if personality_changes else 0
            embed.add_field(
                name="Personality Evolution (7 days)",
                value=f"**Evolution Events**: {evolutions}",
                inline=True
            )
            
            await interaction.followup.send(embed=embed)
            logger.info(f"Admin {interaction.user.name} viewed memory debug info")
            
        except Exception as e:
            logger.error(f"Error in debug_memory command: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Error: {e}")

    @app_commands.command(name="clear_context", description="[Debug] Löscht den Kontext für einen Kanal.")
    @app_commands.describe(channel="Der Kanal (optional, Standard: aktueller Kanal)")
    async def clear_context(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        """Clears context for a channel."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            from modules.advanced_ai import clear_context
            
            target_channel = channel or interaction.channel
            await clear_context(target_channel.id)
            
            await interaction.followup.send(f"✅ Context für <#{target_channel.id}> gelöscht.")
            logger.info(f"Admin {interaction.user.name} cleared context for channel {target_channel.id}")
            
        except Exception as e:
            logger.error(f"Error in clear_context command: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Error: {e}")


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
async def profile(interaction: discord.Interaction, user: discord.User = None):
    """Displays a user's profile with various stats."""
    target_user = user or interaction.user
    
    # Try to defer, but handle if interaction already expired
    try:
        await interaction.response.defer(ephemeral=False) # Use ephemeral=False if the response should be public
    except discord.errors.NotFound:
        logger.warning(f"Profile command interaction {interaction.id} already expired before defer")
        return

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
    
    # Check if user is boosting the server (only available in guilds)
    is_boosting = False
    if hasattr(target_user, 'premium_since') and target_user.premium_since is not None:
        is_boosting = True
    boost_status = "💎 Boostet den Server!" if is_boosting else "Kein Boost"
    
    embed.add_field(name="🎨 Farbe", value=f"`{color_display}`", inline=True)
    embed.add_field(name="🚀 Server Boost", value=f"{boost_status}", inline=True)

    # Show purchased items/features - dynamically fetch all features
    all_features = await db_helpers.get_user_features(target_user.id)
    
    # Feature name mapping with icons
    feature_names = {
        'dm_access': '✉️ DM Access',
        'casino': '🎰 Casino Access',
        'detective': '🔍 Detective Game',
        'trolly': '🚃 Trolly Problem',
        'unlimited_word_find': '📝 Unlimited Word Find',
        'unlimited_wordle': '🎯 Unlimited Wordle',
        'rpg_access': '⚔️ RPG System Access',
        'werwolf_special_roles': '🐺 Werwolf Special Roles',
        'custom_status': '💬 Custom Status',
        'werwolf_role_seherin': '🔮 Werwolf: Seherin',
        'werwolf_role_hexe': '🧪 Werwolf: Hexe',
        'werwolf_role_dönerstopfer': '🌯 Werwolf: Dönerstopfer',
        'werwolf_role_jäger': '🏹 Werwolf: Jäger'
    }
    
    features = []
    for feature in all_features:
        display_name = feature_names.get(feature, feature)
        features.append(display_name)
    
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
    
    @discord.ui.button(label="🔍 Detective Stats", style=discord.ButtonStyle.secondary, row=0)
    async def detective_stats_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        embed = await self._create_detective_stats_embed()
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="📝 Word Find Stats", style=discord.ButtonStyle.secondary, row=1)
    async def wordfind_stats_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        embed = await self._create_wordfind_stats_embed()
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
    
    async def _create_detective_stats_embed(self):
        """Create embed with Detective game stats."""
        try:
            stats = await detective_game.get_user_detective_stats(db_helpers, self.user.id)
            
            if not stats:
                return discord.Embed(
                    title="Fehler",
                    description="Konnte Detective-Statistiken nicht laden.",
                    color=discord.Color.red()
                )
            
            embed = discord.Embed(
                title=f"🔍 Detective Stats - {self.user.display_name}",
                description="Deine Mordfall-Ermittlungen",
                color=discord.Color.dark_blue()
            )
            embed.set_thumbnail(url=self.user.display_avatar.url)
            
            # Difficulty and Progress
            difficulty = stats['current_difficulty']
            difficulty_stars = "⭐" * difficulty
            embed.add_field(
                name="Aktueller Schwierigkeitsgrad",
                value=f"{difficulty_stars} **Stufe {difficulty}/5**",
                inline=False
            )
            
            # Progress to next difficulty
            progress = stats['progress_to_next_difficulty']
            if difficulty < 5:
                progress_bar_length = 10
                filled = min(progress, 10)
                bar = '█' * filled + '░' * (progress_bar_length - filled)
                embed.add_field(
                    name="Fortschritt zur nächsten Stufe",
                    value=f"`{bar}` **{progress}/10** Fälle gelöst",
                    inline=False
                )
            else:
                embed.add_field(
                    name="🏆 Maximale Stufe erreicht!",
                    value="Du bist ein Meisterdetektiv!",
                    inline=False
                )
            
            # Case statistics
            total_cases = stats['total_cases_played']
            cases_solved = stats['cases_solved']
            cases_failed = stats['cases_failed']
            solve_rate = stats['solve_rate']
            
            embed.add_field(name="Fälle gesamt", value=f"`{total_cases}`", inline=True)
            embed.add_field(name="Gelöst", value=f"✅ `{cases_solved}`", inline=True)
            embed.add_field(name="Gescheitert", value=f"❌ `{cases_failed}`", inline=True)
            
            # Solve rate bar
            bar_length = 20
            filled = int((solve_rate / 100) * bar_length)
            bar = '█' * filled + '░' * (bar_length - filled)
            
            # Determine rating based on solve rate
            if solve_rate >= 80:
                rating = "🏆 Meisterdetektiv"
            elif solve_rate >= 60:
                rating = "🎖️ Erfahrener Ermittler"
            elif solve_rate >= 40:
                rating = "🔍 Kompetenter Detective"
            elif solve_rate >= 20:
                rating = "📝 Anfänger-Ermittler"
            else:
                rating = "🤔 Braucht mehr Übung"
            
            embed.add_field(
                name=f"Lösungsrate: {solve_rate:.1f}%",
                value=f"`{bar}`\n{rating}",
                inline=False
            )
            
            # Last played
            if stats['last_played_at']:
                last_played = stats['last_played_at']
                embed.set_footer(text=f"Zuletzt gespielt: {last_played.strftime('%d.%m.%Y %H:%M')}")
            else:
                embed.set_footer(text="Noch keinen Fall gespielt!")
            
            return embed
            
        except Exception as e:
            logger.error(f"Error creating detective stats embed: {e}", exc_info=True)
            return discord.Embed(
                title="Fehler",
                description=f"Fehler beim Laden der Detective-Statistiken: {str(e)}",
                color=discord.Color.red()
            )
    
    async def _create_wordfind_stats_embed(self):
        """Create embed with Word Find game stats."""
        try:
            stats = await word_find.get_user_stats(db_helpers, self.user.id)
            
            if not stats:
                return discord.Embed(
                    title=f"📝 Word Find Stats - {self.user.display_name}",
                    description="Noch keine Word Find Spiele gespielt!",
                    color=discord.Color.blue()
                )
            
            embed = discord.Embed(
                title=f"📝 Word Find Stats - {self.user.display_name}",
                description="Deine Word Find Statistiken",
                color=discord.Color.blue()
            )
            embed.set_thumbnail(url=self.user.display_avatar.url)
            
            # Daily game stats (use new columns if available, fall back to old)
            daily_games = stats.get('daily_games') or stats.get('total_games', 0)
            daily_wins = stats.get('daily_wins') or stats.get('total_wins', 0)
            daily_attempts = stats.get('daily_total_attempts') or stats.get('total_attempts', 0)
            daily_streak = stats.get('daily_streak') or stats.get('current_streak', 0)
            daily_best_streak = stats.get('daily_best_streak') or stats.get('best_streak', 0)
            
            # Premium game stats (new columns only)
            premium_games = stats.get('premium_games', 0)
            premium_wins = stats.get('premium_wins', 0)
            premium_attempts = stats.get('premium_total_attempts', 0)
            
            # Calculate daily stats
            daily_win_rate = (daily_wins / daily_games * 100) if daily_games > 0 else 0
            daily_avg_attempts = (daily_attempts / daily_wins) if daily_wins > 0 else 0
            
            # Daily stats section
            if daily_games > 0:
                embed.add_field(
                    name="📅 Tägliche Spiele",
                    value=f"Spiele: `{daily_games}` | Siege: `{daily_wins}` | Rate: `{daily_win_rate:.1f}%`\n"
                          f"Streak: 🔥 `{daily_streak}` | Best: ⭐ `{daily_best_streak}`\n"
                          f"Ø Versuche: `{daily_avg_attempts:.1f}`",
                    inline=False
                )
                
                # Daily win rate progress bar
                bar_length = 20
                filled = int((daily_win_rate / 100) * bar_length)
                bar = '█' * filled + '░' * (bar_length - filled)
                
                # Rating based on daily win rate
                if daily_win_rate >= 80:
                    rating = "🏆 Wortmeister"
                elif daily_win_rate >= 60:
                    rating = "🎖️ Wortexperte"
                elif daily_win_rate >= 40:
                    rating = "📖 Wortkenner"
                elif daily_win_rate >= 20:
                    rating = "📝 Anfänger"
                else:
                    rating = "🤔 Übe weiter!"
                
                embed.add_field(
                    name=f"Daily Erfolgsrate: {daily_win_rate:.1f}%",
                    value=f"`{bar}`\n{rating}",
                    inline=False
                )
            
            # Premium stats section (only show if user has played premium games)
            if premium_games > 0:
                premium_win_rate = (premium_wins / premium_games * 100) if premium_games > 0 else 0
                premium_avg_attempts = (premium_attempts / premium_wins) if premium_wins > 0 else 0
                
                embed.add_field(
                    name="💎 Premium Spiele",
                    value=f"Spiele: `{premium_games}` | Siege: `{premium_wins}` | Rate: `{premium_win_rate:.1f}%`\n"
                          f"Ø Versuche: `{premium_avg_attempts:.1f}`",
                    inline=False
                )
                
                # Premium win rate progress bar
                bar_length = 20
                filled = int((premium_win_rate / 100) * bar_length)
                bar = '█' * filled + '░' * (bar_length - filled)
                
                embed.add_field(
                    name=f"Premium Erfolgsrate: {premium_win_rate:.1f}%",
                    value=f"`{bar}`",
                    inline=False
                )
            
            # Last played
            if stats.get('last_played'):
                last_played = stats['last_played']
                embed.set_footer(text=f"Zuletzt gespielt: {last_played.strftime('%Y-%m-%d')}")
            else:
                embed.set_footer(text="Noch nie gespielt!")
            
            return embed
            
        except Exception as e:
            logger.error(f"Error creating word find stats embed: {e}", exc_info=True)
            return discord.Embed(
                title="Fehler",
                description=f"Fehler beim Laden der Word Find Statistiken: {str(e)}",
                color=discord.Color.red()
            )



# --- RPG System Commands ---

@tree.command(name="rpg", description="Zeige dein RPG-Profil und Optionen")
async def rpg_command(interaction: discord.Interaction):
    """Display RPG profile and options."""
    try:
        await interaction.response.defer(ephemeral=True)
        
        user_id = interaction.user.id
        
        # Get user's theme for theming
        user_theme = await themes.get_user_theme(db_helpers, user_id)
        
        # Check if user has RPG access
        has_rpg_access = await db_helpers.has_feature_unlock(user_id, 'rpg_access')
        
        if not has_rpg_access:
            # User doesn't have RPG access - show purchase prompt
            embed = discord.Embed(
                title="⚔️ RPG System - Zugriff erforderlich",
                description="Du benötigst Zugriff auf das RPG-System, um diese Funktion zu nutzen!\n\n"
                           "Das RPG-System bietet:\n"
                           "🗡️ Epische Kämpfe gegen Monster\n"
                           "📊 Charakterentwicklung mit Skills\n"
                           "🎒 Inventar und Ausrüstung\n"
                           "🏪 Shop mit Waffen und Items\n"
                           "🌍 Verschiedene Welten zum Erkunden\n\n"
                           "Kaufe den Zugang im Shop!",
                color=themes.get_theme_color(user_theme, 'danger') if user_theme else discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        player = await rpg_system.get_player_profile(db_helpers, user_id)
        
        if not player:
            await interaction.followup.send("❌ Fehler beim Laden deines Profils.")
            return
        
        # Get skill tree bonuses
        skill_tree_bonuses = await rpg_system.calculate_skill_tree_bonuses(db_helpers, user_id)
        
        # Create profile embed with theme support
        embed = discord.Embed(
            title=f"⚔️ RPG Profil - {interaction.user.display_name}",
            description=f"**Level {player['level']}** | Welt: {rpg_system.WORLDS[player['world']]['name']}",
            color=themes.get_theme_color(user_theme, 'primary') if user_theme else discord.Color.purple()
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
        # Format stats with bonus display if applicable
        def format_stat(base, bonus, emoji, name):
            if bonus > 0:
                return f"{emoji} {name}: {base} (+{bonus}) = **{base + bonus}**"
            return f"{emoji} {name}: {base}"
        
        # Stats
        stats_text = f"❤️ HP: {player['health']}/{player['max_health']}\n"
        stats_text += format_stat(player['strength'], skill_tree_bonuses.get('strength', 0), "⚔️", "Stärke") + "\n"
        stats_text += format_stat(player['dexterity'], skill_tree_bonuses.get('dexterity', 0), "🎯", "Geschick") + "\n"
        stats_text += format_stat(player['defense'], skill_tree_bonuses.get('defense', 0), "🛡️", "Verteidigung") + "\n"
        stats_text += format_stat(player['speed'], skill_tree_bonuses.get('speed', 0), "⚡", "Geschwindigkeit")
        
        embed.add_field(
            name="📊 Attribute",
            value=stats_text,
            inline=True
        )
        
        # Progression
        xp_needed = rpg_system.calculate_xp_for_level(player['level'] + 1)
        xp_progress = player['xp']
        progress_pct = (xp_progress / xp_needed) * 100 if xp_needed > 0 else 100
        
        embed.add_field(
            name="📈 Fortschritt",
            value=f"XP: {xp_progress}/{xp_needed}\n"
                  f"Fortschritt: {progress_pct:.1f}%\n"
                  f"💎 Skillpunkte: {player['skill_points']}\n"
                  f"💰 Gold: {player['gold']}",
            inline=True
        )
        
        # Actions
        embed.add_field(
            name="🎮 Verfügbare Aktionen",
            value="Wähle eine Aktion aus den Buttons unten!",
            inline=False
        )
        
        embed.set_footer(text="Nutze die Buttons um dein Abenteuer zu beginnen!")
        
        # Create view with action buttons
        view = RPGMenuView(user_id, player)
        await interaction.followup.send(embed=embed, view=view)
        
    except Exception as e:
        logger.error(f"Error in RPG command: {e}", exc_info=True)
        await interaction.followup.send(f"❌ Ein Fehler ist aufgetreten: {e}")


class RPGMenuView(discord.ui.View):
    """Interactive menu view for RPG actions."""
    
    def __init__(self, user_id: int, player: dict):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.player = player
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Dies ist nicht dein Menü!", ephemeral=True)
            return False
        return True
    
    @discord.ui.button(label="🗡️ Abenteuer", style=discord.ButtonStyle.danger, row=0)
    async def adventure_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Start an adventure encounter (combat or event)."""
        await interaction.response.defer()
        
        try:
            # Start adventure
            result, error, encounter_type = await rpg_system.start_adventure(db_helpers, self.user_id)
            
            if error:
                await interaction.followup.send(f"❌ {error}", ephemeral=True)
                return
            
            if not result:
                await interaction.followup.send("❌ Kein Abenteuer gefunden.", ephemeral=True)
                return
            
            # Handle based on encounter type
            if encounter_type == 'combat':
                monster = result
                # Create combat embed
                embed = discord.Embed(
                    title=f"⚔️ Wilde Begegnung!",
                    description=f"Ein wilder **{monster['name']}** (Level {monster['level']}) erscheint!",
                    color=discord.Color.red()
                )
                
                # Monster stats
                embed.add_field(
                    name=f"🐉 {monster['name']}",
                    value=f"❤️ HP: {monster['health']}\n"
                          f"⚔️ Angriff: {monster['strength']}\n"
                          f"🛡️ Verteidigung: {monster['defense']}\n"
                          f"⚡ Geschwindigkeit: {monster['speed']}",
                    inline=True
                )
                
                # Rewards
                embed.add_field(
                    name="🎁 Belohnungen",
                    value=f"💰 {monster['gold_reward']} Gold\n"
                          f"⭐ {monster['xp_reward']} XP",
                    inline=True
                )
                
                embed.set_footer(text="Wähle deine Aktion!")
                
                # Get equipped skills for combat
                equipped = await rpg_system.get_equipped_items(db_helpers, self.user_id)
                equipped_skills = []
                if equipped:
                    if equipped.get('skill1_id'):
                        skill1 = await rpg_system.get_item_by_id(db_helpers, equipped['skill1_id'])
                        if skill1:
                            equipped_skills.append(skill1)
                    if equipped.get('skill2_id'):
                        skill2 = await rpg_system.get_item_by_id(db_helpers, equipped['skill2_id'])
                        if skill2:
                            equipped_skills.append(skill2)
                
                # Create combat view with equipped skills
                view = RPGCombatView(self.user_id, monster, equipped_skills)
                await interaction.followup.send(embed=embed, view=view, ephemeral=True)
                
            elif encounter_type == 'event':
                event = result
                # Create event embed
                embed = discord.Embed(
                    title=event['title'],
                    description=event['description'],
                    color=discord.Color.blue()
                )
                
                # Show rewards
                rewards = []
                if 'gold_reward' in event:
                    rewards.append(f"💰 {event['gold_reward']} Gold")
                if 'xp_reward' in event:
                    rewards.append(f"⭐ {event['xp_reward']} XP")
                if 'heal_amount' in event and event['heal_amount'] > 0:
                    rewards.append(f"❤️ +{event['heal_amount']} HP")
                
                if rewards:
                    embed.add_field(name="🎁 Belohnungen", value="\n".join(rewards), inline=False)
                
                embed.set_footer(text="Klicke auf den Button um die Belohnungen zu erhalten!")
                
                # Create event view and update the original message
                view = RPGEventView(self.user_id, event)
                await interaction.edit_original_response(embed=embed, view=view)
            
        except Exception as e:
            logger.error(f"Error in adventure button: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Ein Fehler ist aufgetreten: {e}", ephemeral=True)
    
    @discord.ui.button(label="🏪 Shop", style=discord.ButtonStyle.success, row=0)
    async def shop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open the RPG shop."""
        await interaction.response.defer()
        
        try:
            # Get available items
            items = await rpg_system.get_shop_items(db_helpers, self.player['level'])
            
            if not items:
                await interaction.followup.send("❌ Keine Items verfügbar.", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="🏪 RPG Shop",
                description=f"Dein Gold: **{self.player['gold']}** 💰",
                color=discord.Color.gold()
            )
            
            for item in items[:10]:  # Show max 10 items
                rarity_color = rpg_system.RARITY_COLORS.get(item['rarity'], discord.Color.light_grey())
                embed.add_field(
                    name=f"{item['name']} ({item['rarity'].capitalize()})",
                    value=f"💰 Preis: {item['price']}\n"
                          f"📝 {item['description'][:50]}...\n"
                          f"⚔️ Schaden: {item.get('damage', 0)}",
                    inline=True
                )
            
            embed.set_footer(text="Wähle ein Item zum Kaufen!")
            
            view = RPGShopView(self.user_id, items, self.player['gold'])
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in shop button: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Ein Fehler ist aufgetreten: {e}", ephemeral=True)
    
    @discord.ui.button(label="⛩️ Tempel", style=discord.ButtonStyle.primary, row=0)
    async def temple_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open the temple for healing and blessings."""
        await interaction.response.defer()
        
        try:
            embed = discord.Embed(
                title="⛩️ Tempel der Heilung",
                description="Willkommen im heiligen Tempel!",
                color=discord.Color.from_rgb(255, 215, 0)
            )
            
            # Calculate healing cost
            missing_hp = self.player['max_health'] - self.player['health']
            heal_cost = int(missing_hp * 0.5)  # 0.5 gold per HP
            
            if missing_hp > 0:
                embed.add_field(
                    name="💚 Heilung",
                    value=f"Fehlende HP: {missing_hp}\n"
                          f"Kosten: {heal_cost} Gold",
                    inline=True
                )
            else:
                embed.add_field(
                    name="💚 Heilung",
                    value="Du bist bereits vollständig geheilt!",
                    inline=True
                )
            
            # Blessing options
            embed.add_field(
                name="✨ Segen",
                value="🔮 Temporärer XP-Boost: 100 Gold\n"
                      "⚔️ Temporärer Stärke-Boost: 150 Gold\n"
                      "🛡️ Temporärer Verteidigungs-Boost: 150 Gold",
                inline=False
            )
            
            embed.set_footer(text=f"Dein Gold: {self.player['gold']} 💰")
            
            view = RPGTempleView(self.user_id, self.player, missing_hp, heal_cost)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in temple button: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Ein Fehler ist aufgetreten: {e}", ephemeral=True)
    
    @discord.ui.button(label="🎒 Inventar", style=discord.ButtonStyle.secondary, row=1)
    async def inventory_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open player inventory."""
        await interaction.response.defer()
        
        try:
            # Get player inventory and equipped items
            inventory = await rpg_system.get_player_inventory(db_helpers, self.user_id)
            equipped = await rpg_system.get_equipped_items(db_helpers, self.user_id)
            
            embed = discord.Embed(
                title="🎒 Dein Inventar",
                description=f"Level {self.player['level']} | Gold: {self.player['gold']} 💰",
                color=discord.Color.blue()
            )
            
            # Show equipped items
            equipped_text = ""
            if equipped.get('weapon_id'):
                weapon = await rpg_system.get_item_by_id(db_helpers, equipped['weapon_id'])
                if weapon:
                    equipped_text += f"⚔️ Waffe: **{weapon['name']}** (Schaden: {weapon['damage']})\n"
            else:
                equipped_text += "⚔️ Waffe: *Keine*\n"
            
            if equipped.get('skill1_id'):
                skill1 = await rpg_system.get_item_by_id(db_helpers, equipped['skill1_id'])
                if skill1:
                    equipped_text += f"🔮 Skill 1: **{skill1['name']}**\n"
            else:
                equipped_text += "🔮 Skill 1: *Keine*\n"
            
            if equipped.get('skill2_id'):
                skill2 = await rpg_system.get_item_by_id(db_helpers, equipped['skill2_id'])
                if skill2:
                    equipped_text += f"🔮 Skill 2: **{skill2['name']}**\n"
            else:
                equipped_text += "🔮 Skill 2: *Keine*\n"
            
            embed.add_field(name="📦 Ausgerüstet", value=equipped_text, inline=False)
            
            # Show inventory items
            if inventory:
                inv_text = ""
                for item in inventory[:15]:  # Show max 15 items
                    inv_text += f"• {item['name']} ({item['type']}) x{item['quantity']}\n"
                embed.add_field(name="🎁 Items", value=inv_text or "*Leer*", inline=False)
            else:
                embed.add_field(name="🎁 Items", value="*Leer*", inline=False)
            
            embed.set_footer(text="Wähle ein Item zum Ausrüsten!")
            
            view = RPGInventoryView(self.user_id, inventory, equipped)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in inventory button: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Ein Fehler ist aufgetreten: {e}", ephemeral=True)
    
    @discord.ui.button(label="🌳 Skill-Baum", style=discord.ButtonStyle.primary, row=1)
    async def skill_tree_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open skill tree."""
        await interaction.response.defer()
        
        try:
            # Get unlocked skills
            unlocked_skills = await rpg_system.get_unlocked_skills(db_helpers, self.user_id)
            
            embed = discord.Embed(
                title="🌳 Skill-Baum",
                description=f"**Skillpunkte verfügbar: {self.player['skill_points']}**\n\n"
                           f"Wähle einen Pfad, um Skills freizuschalten!",
                color=discord.Color.purple()
            )
            
            # Show available paths
            for path_key, path_data in rpg_system.SKILL_TREE.items():
                unlocked_count = len(unlocked_skills.get(path_key, []))
                total_count = len(path_data['skills'])
                
                path_text = f"{path_data['emoji']} **{path_data['name']}**\n"
                path_text += f"{path_data['description']}\n"
                path_text += f"Fortschritt: {unlocked_count}/{total_count} Skills"
                
                embed.add_field(name="\u200b", value=path_text, inline=False)
            
            embed.set_footer(text="Skillpunkte erhältst du beim Level-Aufstieg!")
            
            view = RPGSkillTreeView(self.user_id, self.player['skill_points'], unlocked_skills)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in skill tree button: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Ein Fehler ist aufgetreten: {e}", ephemeral=True)



@tree.command(name="adventure", description="Gehe auf ein Abenteuer und kämpfe gegen Monster!")
async def adventure_command(interaction: discord.Interaction):
    """Start an adventure encounter."""
    await interaction.response.defer()
    
    try:
        user_id = interaction.user.id
        
        # Start adventure
        result, error, encounter_type = await rpg_system.start_adventure(db_helpers, user_id)
        
        if error:
            await interaction.followup.send(f"❌ {error}")
            return
        
        if not result:
            await interaction.followup.send("❌ Keine Begegnung gefunden.")
            return
        
        # Handle non-combat events
        if encounter_type == 'event':
            event = result
            # Create event embed
            embed = discord.Embed(
                title=event['title'],
                description=event['description'],
                color=discord.Color.blue()
            )
            
            # Show rewards
            rewards = []
            if 'gold_reward' in event:
                rewards.append(f"💰 {event['gold_reward']} Gold")
            if 'xp_reward' in event:
                rewards.append(f"⭐ {event['xp_reward']} XP")
            if 'heal_amount' in event and event['heal_amount'] > 0:
                rewards.append(f"❤️ +{event['heal_amount']} HP")
            
            if rewards:
                embed.add_field(name="🎁 Belohnungen", value="\n".join(rewards), inline=False)
            
            embed.set_footer(text="Klicke auf den Button um die Belohnungen zu erhalten!")
            
            # Create event view
            view = RPGEventView(user_id, event)
            await interaction.followup.send(embed=embed, view=view)
            return
        
        # Handle combat encounters
        monster = result
        
        # Initialize default monsters if needed
        await rpg_system.initialize_default_monsters(db_helpers)
        
        # Create combat embed
        embed = discord.Embed(
            title=f"⚔️ Wilde Begegnung!",
            description=f"Ein wilder **{monster['name']}** (Level {monster['level']}) erscheint!",
            color=discord.Color.red()
        )
        
        # Monster stats
        embed.add_field(
            name=f"🐉 {monster['name']}",
            value=f"❤️ HP: {monster['health']}\n"
                  f"⚔️ Angriff: {monster['strength']}\n"
                  f"🛡️ Verteidigung: {monster['defense']}\n"
                  f"⚡ Geschwindigkeit: {monster['speed']}",
            inline=True
        )
        
        # Rewards
        embed.add_field(
            name="🎁 Belohnungen",
            value=f"💰 {monster['gold_reward']} Gold\n"
                  f"⭐ {monster['xp_reward']} XP",
            inline=True
        )
        
        embed.set_footer(text="Wähle deine Aktion!")
        
        # Get equipped skills for combat
        equipped = await rpg_system.get_equipped_items(db_helpers, user_id)
        equipped_skills = []
        if equipped:
            if equipped.get('skill1_id'):
                skill1 = await rpg_system.get_item_by_id(db_helpers, equipped['skill1_id'])
                if skill1:
                    equipped_skills.append(skill1)
            if equipped.get('skill2_id'):
                skill2 = await rpg_system.get_item_by_id(db_helpers, equipped['skill2_id'])
                if skill2:
                    equipped_skills.append(skill2)
        
        # Create combat view with equipped skills
        view = RPGCombatView(user_id, monster, equipped_skills)
        await interaction.followup.send(embed=embed, view=view)
        
    except Exception as e:
        logger.error(f"Error in adventure command: {e}", exc_info=True)
        await interaction.followup.send(f"❌ Ein Fehler ist aufgetreten: {e}")




class RPGItemCreationModal(discord.ui.Modal, title="RPG Item Erstellen"):
    """Modal for creating custom RPG items with better UX."""
    
    item_name = discord.ui.TextInput(
        label="Item Name",
        placeholder="z.B. Feuerschwert",
        required=True,
        max_length=100
    )
    
    item_description = discord.ui.TextInput(
        label="Beschreibung",
        placeholder="Beschreibe das Item...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500
    )
    
    item_damage = discord.ui.TextInput(
        label="Schaden (0 für nicht-Waffen)",
        placeholder="z.B. 25",
        required=False,
        default="0"
    )
    
    item_price = discord.ui.TextInput(
        label="Preis (Gold)",
        placeholder="z.B. 500",
        required=True
    )
    
    item_effects = discord.ui.TextInput(
        label="Effekte (JSON Format, optional)",
        placeholder='z.B. {"status": "burn", "duration": 3, "damage_bonus": 10}',
        style=discord.TextStyle.paragraph,
        required=False
    )
    
    def __init__(self, item_type: str, rarity: str, required_level: int, creator_id: int):
        super().__init__()
        self.item_type = item_type
        self.rarity = rarity
        self.required_level = required_level
        self.creator_id = creator_id
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle the modal submission."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Parse damage
            damage = int(self.item_damage.value) if self.item_damage.value else 0
            
            # Parse price
            price = int(self.item_price.value)
            
            # Parse effects (if provided)
            effects = None
            if self.item_effects.value:
                try:
                    effects = json.loads(self.item_effects.value)
                except json.JSONDecodeError:
                    await interaction.followup.send("❌ Ungültiges JSON Format für Effekte!", ephemeral=True)
                    return
            
            # Create item with effects
            success, item_id = await rpg_system.create_custom_item(
                db_helpers,
                name=self.item_name.value,
                item_type=self.item_type,
                rarity=self.rarity,
                description=self.item_description.value,
                damage=damage,
                price=price,
                required_level=self.required_level,
                created_by=self.creator_id,
                effects=effects
            )
            
            if success:
                rarity_color = rpg_system.RARITY_COLORS.get(self.rarity, discord.Color.light_grey())
                embed = discord.Embed(
                    title="✅ Item erfolgreich erstellt!",
                    description=f"**{self.item_name.value}** wurde zum RPG System hinzugefügt!",
                    color=rarity_color
                )
                embed.add_field(name="Typ", value=self.item_type, inline=True)
                embed.add_field(name="Seltenheit", value=self.rarity.capitalize(), inline=True)
                embed.add_field(name="Level", value=str(self.required_level), inline=True)
                embed.add_field(name="Preis", value=f"{price} Gold", inline=True)
                embed.add_field(name="Schaden", value=str(damage), inline=True)
                embed.add_field(name="Item ID", value=str(item_id), inline=True)
                embed.add_field(name="Beschreibung", value=self.item_description.value, inline=False)
                
                if effects:
                    effects_str = json.dumps(effects, indent=2)
                    embed.add_field(name="Effekte", value=f"```json\n{effects_str}\n```", inline=False)
                
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(f"❌ Fehler beim Erstellen: {item_id}", ephemeral=True)
                
        except ValueError as e:
            await interaction.followup.send(f"❌ Ungültige Eingabe: {e}", ephemeral=True)
        except Exception as e:
            logger.error(f"Error in item creation modal: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Ein Fehler ist aufgetreten: {e}", ephemeral=True)


@tree.command(name="rpgadmin", description="Admin: Erstelle benutzerdefinierte Items und Loot")
@app_commands.describe(
    item_type="Typ des Items",
    rarity="Seltenheit",
    required_level="Benötigtes Level (Standard: 1)"
)
@app_commands.choices(item_type=[
    app_commands.Choice(name="Waffe", value="weapon"),
    app_commands.Choice(name="Skill/Zauber", value="skill"),
    app_commands.Choice(name="Verbrauchsgegenstand", value="consumable"),
])
@app_commands.choices(rarity=[
    app_commands.Choice(name="Gewöhnlich", value="common"),
    app_commands.Choice(name="Ungewöhnlich", value="uncommon"),
    app_commands.Choice(name="Selten", value="rare"),
    app_commands.Choice(name="Episch", value="epic"),
    app_commands.Choice(name="Legendär", value="legendary"),
])
async def rpg_admin_command(
    interaction: discord.Interaction,
    item_type: app_commands.Choice[str],
    rarity: app_commands.Choice[str],
    required_level: int = 1
):
    """Admin command to create custom RPG items using a modal."""
    # Check if user is admin
    is_admin = interaction.user.guild_permissions.administrator or interaction.user.id == int(os.getenv("OWNER_ID", 0))
    
    if not is_admin:
        await interaction.response.send_message("❌ Nur Admins können diesen Befehl verwenden!", ephemeral=True)
        return
    
    # Show modal for item details
    modal = RPGItemCreationModal(
        item_type=item_type.value,
        rarity=rarity.value,
        required_level=required_level,
        creator_id=interaction.user.id
    )
    await interaction.response.send_modal(modal)


class RPGContinueAdventureView(discord.ui.View):
    """View shown after winning a combat to allow continuing the adventure."""
    
    def __init__(self, user_id: int):
        super().__init__(timeout=180)  # 3 minute timeout
        self.user_id = user_id
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Dies ist nicht dein Abenteuer!", ephemeral=True)
            return False
        return True
    
    @discord.ui.button(label="⚔️ Weiter abenteuern", style=discord.ButtonStyle.success, emoji="🎮")
    async def continue_adventure_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Continue adventuring immediately after winning."""
        try:
            await interaction.response.defer()
        except discord.errors.NotFound:
            logger.warning("Continue adventure button interaction expired")
            return
        
        try:
            # Start another adventure with continue_chain=True to skip cooldown
            result, error, encounter_type = await rpg_system.start_adventure(db_helpers, self.user_id, continue_chain=True)
            
            if error:
                await interaction.followup.send(f"❌ {error}", ephemeral=True)
                return
            
            if encounter_type == 'combat':
                # Create combat embed
                embed = discord.Embed(
                    title=f"⚔️ Wilder {result['name']} erscheint!",
                    description=f"Ein **Level {result['level']}** Monster blockiert deinen Weg!",
                    color=discord.Color.red()
                )
                
                embed.add_field(
                    name="👹 Monster Stats",
                    value=f"❤️ HP: {result['health']}\n"
                          f"⚔️ Angriff: {result['strength']}\n"
                          f"🛡️ Verteidigung: {result['defense']}\n"
                          f"⚡ Geschwindigkeit: {result['speed']}",
                    inline=True
                )
                
                # Show monster abilities if any
                if result.get('abilities') and len(result['abilities']) > 0:
                    abilities_text = ""
                    for ability_key in result['abilities'][:3]:  # Show up to 3 abilities
                        if ability_key in rpg_system.MONSTER_ABILITIES:
                            ability = rpg_system.MONSTER_ABILITIES[ability_key]
                            abilities_text += f"{ability['emoji']} **{ability['name']}**: {ability['description']}\n"
                    
                    if abilities_text:
                        embed.add_field(
                            name="✨ Spezialfähigkeiten",
                            value=abilities_text,
                            inline=False
                        )
                
                embed.add_field(
                    name="🎁 Belohnungen",
                    value=f"💰 {result['gold_reward']} Gold\n⭐ {result['xp_reward']} XP",
                    inline=True
                )
                
                embed.set_footer(text="🎮 Rogue-like Adventure: Besiege Monster hintereinander für maximale Belohnungen!")
                
                # Get equipped skills for combat
                equipped = await rpg_system.get_equipped_items(db_helpers, self.user_id)
                equipped_skills = []
                if equipped:
                    if equipped.get('skill1_id'):
                        skill1 = await rpg_system.get_item_by_id(db_helpers, equipped['skill1_id'])
                        if skill1:
                            equipped_skills.append(skill1)
                    if equipped.get('skill2_id'):
                        skill2 = await rpg_system.get_item_by_id(db_helpers, equipped['skill2_id'])
                        if skill2:
                            equipped_skills.append(skill2)
                
                # Create combat view with equipped skills
                view = RPGCombatView(self.user_id, result, equipped_skills)
                await interaction.edit_original_response(embed=embed, view=view)
                
            elif encounter_type == 'event':
                # Create event embed
                embed = discord.Embed(
                    title=result['title'],
                    description=result['description'],
                    color=discord.Color.blue()
                )
                
                # Show rewards
                rewards_text = ""
                if 'gold_reward' in result:
                    rewards_text += f"💰 {result['gold_reward']} Gold\n"
                if 'xp_reward' in result:
                    rewards_text += f"⭐ {result['xp_reward']} XP\n"
                if 'heal_amount' in result and result['heal_amount'] > 0:
                    rewards_text += f"❤️ {result['heal_amount']} HP wiederhergestellt\n"
                
                if rewards_text:
                    embed.add_field(name="🎁 Belohnungen", value=rewards_text, inline=False)
                
                embed.set_footer(text="🎮 Rogue-like Adventure: Sammle Belohnungen und setze dein Abenteuer fort!")
                
                # Create event view
                view = RPGEventView(self.user_id, result)
                await interaction.edit_original_response(embed=embed, view=view)
            
            self.stop()
            
        except Exception as e:
            logger.error(f"Error continuing adventure: {e}", exc_info=True)
            try:
                await interaction.followup.send(f"❌ Fehler beim Fortsetzen des Abenteuers: {e}", ephemeral=True)
            except Exception:
                pass
    
    @discord.ui.button(label="🏠 Zurück zum Dorf", style=discord.ButtonStyle.secondary)
    async def return_to_village_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Return to the village (stop adventuring)."""
        try:
            await interaction.response.defer()
        except discord.errors.NotFound:
            logger.warning("Return to village button interaction expired")
            return
        
        embed = discord.Embed(
            title="🏠 Zurück im Dorf",
            description="Du kehrst siegreich ins Dorf zurück und ruhst dich aus.",
            color=discord.Color.blue()
        )
        
        embed.set_footer(text="Nutze /rpg um dein Profil anzuzeigen oder /adventure um wieder loszuziehen!")
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        try:
            await interaction.edit_original_response(embed=embed, view=None)
        except Exception as e:
            logger.error(f"Error returning to village: {e}")
        
        self.stop()


class RPGCombatView(discord.ui.View):
    """Interactive combat view for RPG battles with strategic combat and enhanced features."""
    
    def __init__(self, user_id: int, monster: dict, equipped_skills: list = None):
        super().__init__(timeout=300)  # 5 minute timeout
        self.user_id = user_id
        self.monster = monster
        self.monster_max_health = monster['health']  # Store original max health
        self.turn_count = 0
        self.equipped_skills = equipped_skills or []
        
        # Import combat enhancements
        from modules import rpg_combat_enhancements as combat_fx
        self.combat_fx = combat_fx
        
        # Enhanced combat state for tracking status effects and new mechanics
        self.combat_state = combat_fx.create_enhanced_combat_state()
        
        # Add skill buttons dynamically
        self._add_skill_buttons()
    
    def _add_skill_buttons(self):
        """Add buttons for equipped skills."""
        # Skill buttons should be added after Attack but before Run
        # We'll add them in the button row
        if self.equipped_skills:
            for idx, skill in enumerate(self.equipped_skills):
                if skill and idx < 2:  # Max 2 skills (skill1 and skill2)
                    # Create skill button with callback factory to properly capture loop variables
                    skill_button = discord.ui.Button(
                        label=f"✨ {skill['name'][:20]}", 
                        style=discord.ButtonStyle.primary,
                        custom_id=f"skill_{idx}",
                        row=1  # Put skills in second row
                    )
                    
                    # Use factory function to create callback with properly captured variables
                    skill_button.callback = self._create_skill_callback(skill, idx)
                    self.add_item(skill_button)
    
    def _create_skill_callback(self, skill_data: dict, skill_idx: int):
        """Factory function to create skill callback with captured variables."""
        async def callback(interaction: discord.Interaction):
            await self._use_skill(interaction, skill_data, skill_idx)
        return callback
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Dies ist nicht dein Kampf!", ephemeral=True)
            return False
        return True
    
    async def _use_skill(self, interaction: discord.Interaction, skill: dict, skill_idx: int):
        """Use an equipped skill in combat."""
        try:
            await interaction.response.defer()
        except discord.errors.NotFound:
            logger.warning("Skill button interaction expired")
            return
        
        try:
            # Process combat turn with skill and combat state
            result = await rpg_system.process_combat_turn(
                db_helpers, 
                self.user_id, 
                self.monster, 
                'skill',
                skill_data=skill,
                combat_state=self.combat_state
            )
            
            if 'error' in result:
                await interaction.followup.send(f"❌ Fehler: {result['error']}")
                return
            
            # Update combat state from result
            if 'combat_state' in result:
                self.combat_state = result['combat_state']
            
            # Update monster health
            self.monster['health'] = result['monster_health']
            self.turn_count += 1
            
            # Get player data
            player = await rpg_system.get_player_profile(db_helpers, self.user_id)
            
            # Create result embed with combat log
            embed = discord.Embed(
                title=f"⚔️ Kampfrunde {self.turn_count}",
                description="\n".join(result['messages']),
                color=discord.Color.purple() if result.get('player_won') else discord.Color.blue()
            )
            
            # Add health bars
            player_health_pct = (result['player_health'] / player['max_health']) * 100 if player else 0
            monster_health_pct = (result['monster_health'] / self.monster_max_health) * 100 if self.monster_max_health > 0 else 0
            
            player_bar = self._create_health_bar(player_health_pct)
            monster_bar = self._create_health_bar(monster_health_pct)
            
            embed.add_field(
                name="❤️ Deine HP",
                value=f"{player_bar} {result['player_health']}/{player['max_health']}",
                inline=True
            )
            
            if not result['combat_over']:
                embed.add_field(
                    name=f"🐉 {self.monster['name']} HP",
                    value=f"{monster_bar} {result['monster_health']}/{self.monster_max_health}",
                    inline=True
                )
            
            # Show active status effects
            status_text = self._get_status_effects_display()
            if status_text:
                embed.add_field(
                    name="📊 Status",
                    value=status_text,
                    inline=False
                )
            
            # Check if combat is over
            if result['combat_over']:
                # Disable all buttons
                for item in self.children:
                    item.disabled = True
                
                if result['player_won']:
                    embed.color = discord.Color.green()
                    if result.get('rewards'):
                        rewards = result['rewards']
                        embed.add_field(
                            name="🎉 Sieg!",
                            value=f"**+{rewards['gold']} Gold**\n**+{rewards['xp']} XP**",
                            inline=False
                        )
                        if rewards.get('leveled_up'):
                            embed.add_field(
                                name="🎊 Level Up!",
                                value=f"Du bist jetzt **Level {rewards['new_level']}**!",
                                inline=False
                            )
                    
                    # Show continue adventuring button
                    continue_view = RPGContinueAdventureView(self.user_id)
                    await interaction.edit_original_response(embed=embed, view=continue_view)
                else:
                    embed.color = discord.Color.dark_red()
                    embed.set_footer(text="Du wurdest mit halber HP ins Dorf zurückgebracht.")
                    await interaction.edit_original_response(embed=embed, view=None)
                
                self.stop()
            else:
                # Update attack button based on rage status
                self._update_attack_button()
                await interaction.edit_original_response(embed=embed, view=self)
            
        except Exception as e:
            logger.error(f"Error using skill in combat: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Fehler: {e}")
    
    def _get_status_effects_display(self) -> str:
        """Get formatted display of active status effects and combat momentum."""
        lines = []
        
        # Player effects
        player_effects = self.combat_state.get('player_effects', {})
        if player_effects:
            player_status = []
            for effect_key, data in player_effects.items():
                effect = rpg_system.STATUS_EFFECTS.get(effect_key)
                if effect:
                    stacks = data.get('stacks', 1)
                    duration = data.get('duration', 0)
                    stack_text = f"x{stacks}" if stacks > 1 else ""
                    player_status.append(f"{effect['emoji']}{stack_text}({duration})")
            if player_status:
                lines.append(f"👤 Du: {' '.join(player_status)}")
        
        # Monster effects
        monster_effects = self.combat_state.get('monster_effects', {})
        if monster_effects:
            monster_status = []
            for effect_key, data in monster_effects.items():
                effect = rpg_system.STATUS_EFFECTS.get(effect_key)
                if effect:
                    stacks = data.get('stacks', 1)
                    duration = data.get('duration', 0)
                    stack_text = f"x{stacks}" if stacks > 1 else ""
                    monster_status.append(f"{effect['emoji']}{stack_text}({duration})")
            if monster_status:
                lines.append(f"🐉 Gegner: {' '.join(monster_status)}")
        
        # Add momentum/combo display using combat enhancements
        momentum_display = self.combat_fx.get_momentum_display(
            self.combat_state.get('combo_count', 0),
            self.combat_state.get('player_rage', 0)
        )
        if momentum_display:
            lines.append(f"\n{momentum_display}")
        
        # Monster enrage indicator
        if self.combat_state.get('monster_enraged'):
            lines.append(f"⚠️ **{self.monster['name']} ist wütend!**")
        
        return "\n".join(lines) if lines else ""
    
    def _create_health_bar(self, percentage: float) -> str:
        """Create an enhanced visual health bar with color-coded segments."""
        bar_length = 10
        percentage = max(0, min(100, percentage))
        filled = int(bar_length * (percentage / 100))
        empty = bar_length - filled
        
        # Choose colors based on health percentage
        if percentage > 70:
            bar_char = "🟩"
        elif percentage > 40:
            bar_char = "🟨"
        elif percentage > 20:
            bar_char = "🟧"
        else:
            bar_char = "🟥"
        
        health_bar = bar_char * filled + "⬛" * empty
        
        # Add pulsing effect indicator for low health
        if percentage <= 20:
            health_bar = f"[{health_bar}] ⚠️"
        else:
            health_bar = f"[{health_bar}]"
        
        return health_bar
    
    def _update_attack_button(self):
        """Update attack button label based on rage status."""
        for item in self.children:
            if isinstance(item, discord.ui.Button) and item.custom_id == "attack_button":
                rage = self.combat_state.get('player_rage', 0)
                if rage >= 100:
                    item.label = "🔥💢 WUTANGRIFF! 💢🔥"
                    item.style = discord.ButtonStyle.success
                else:
                    item.label = "⚔️ Angreifen"
                    item.style = discord.ButtonStyle.danger
                break
    
    @discord.ui.button(label="⚔️ Angreifen", style=discord.ButtonStyle.danger, custom_id="attack_button")
    async def attack_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Attack the monster."""
        try:
            await interaction.response.defer()
        except discord.errors.NotFound:
            # Interaction has expired (likely old message)
            logger.warning("Attack button interaction expired")
            return
        
        try:
            # Process combat turn with combat state
            result = await rpg_system.process_combat_turn(
                db_helpers, 
                self.user_id, 
                self.monster, 
                'attack',
                combat_state=self.combat_state
            )
            
            if 'error' in result:
                await interaction.followup.send(f"❌ Fehler: {result['error']}")
                return
            
            # Update combat state from result
            if 'combat_state' in result:
                self.combat_state = result['combat_state']
            
            # Update monster health to track current state
            self.monster['health'] = result['monster_health']
            
            self.turn_count += 1
            
            # Get player data for display
            player = await rpg_system.get_player_profile(db_helpers, self.user_id)
            
            # Create result embed with combat log
            embed = discord.Embed(
                title=f"⚔️ Kampfrunde {self.turn_count}",
                description="\n".join(result['messages']),
                color=discord.Color.gold() if result.get('player_won') else discord.Color.orange()
            )
            
            # Add health bars
            player_health_pct = (result['player_health'] / player['max_health']) * 100 if player else 0
            monster_health_pct = (result['monster_health'] / self.monster_max_health) * 100 if self.monster_max_health > 0 else 0
            
            player_bar = self._create_health_bar(player_health_pct)
            monster_bar = self._create_health_bar(monster_health_pct)
            
            embed.add_field(
                name="❤️ Deine HP",
                value=f"{player_bar} {result['player_health']}/{player['max_health']}",
                inline=True
            )
            
            if not result['combat_over']:
                embed.add_field(
                    name=f"🐉 {self.monster['name']} HP",
                    value=f"{monster_bar} {result['monster_health']}/{self.monster_max_health}",
                    inline=True
                )
            
            # Show active status effects
            status_text = self._get_status_effects_display()
            if status_text:
                embed.add_field(
                    name="📊 Status",
                    value=status_text,
                    inline=False
                )
            
            # Check if combat is over
            if result['combat_over']:
                # Disable all buttons
                for item in self.children:
                    item.disabled = True
                
                if result['player_won']:
                    embed.color = discord.Color.green()
                    if result.get('rewards'):
                        rewards = result['rewards']
                        embed.add_field(
                            name="🎉 Sieg!",
                            value=f"**+{rewards['gold']} Gold**\n**+{rewards['xp']} XP**",
                            inline=False
                        )
                        if rewards.get('leveled_up'):
                            embed.add_field(
                                name="🎊 Level Up!",
                                value=f"Du bist jetzt **Level {rewards['new_level']}**!",
                                inline=False
                            )
                    
                    # Show continue adventuring button for rogue-like experience
                    continue_view = RPGContinueAdventureView(self.user_id)
                    await interaction.edit_original_response(embed=embed, view=continue_view)
                else:
                    embed.color = discord.Color.dark_red()
                    embed.set_footer(text="Du wurdest mit halber HP ins Dorf zurückgebracht.")
                    await interaction.edit_original_response(embed=embed, view=None)
                
                self.stop()
            else:
                # Update attack button based on rage status
                self._update_attack_button()
                await interaction.edit_original_response(embed=embed, view=self)
            
        except Exception as e:
            logger.error(f"Error in combat: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Fehler: {e}")
    
    @discord.ui.button(label="🏃 Fliehen", style=discord.ButtonStyle.secondary)
    async def run_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Try to run from combat."""
        try:
            await interaction.response.defer()
        except discord.errors.NotFound:
            # Interaction has expired (likely old message)
            logger.warning("Run button interaction expired")
            return
        
        try:
            result = await rpg_system.process_combat_turn(
                db_helpers, 
                self.user_id, 
                self.monster, 
                'run',
                combat_state=self.combat_state
            )
            
            if 'error' in result:
                await interaction.followup.send(f"❌ Fehler: {result['error']}")
                return
            
            # Update combat state from result
            if 'combat_state' in result:
                self.combat_state = result['combat_state']
            
            # Update monster health to track current state
            if 'monster_health' in result:
                self.monster['health'] = result['monster_health']
            
            embed = discord.Embed(
                title="🏃 Fluchtversuch",
                description="\n".join(result['messages']),
                color=discord.Color.blue() if result['combat_over'] else discord.Color.orange()
            )
            
            if result['combat_over']:
                # Successfully fled
                for item in self.children:
                    item.disabled = True
                self.stop()
                await interaction.edit_original_response(embed=embed, view=None)
            else:
                # Failed to flee, show updated health
                player = await rpg_system.get_player_profile(db_helpers, self.user_id)
                health_pct = (result['player_health'] / player['max_health']) * 100
                health_bar = self._create_health_bar(health_pct)
                
                embed.add_field(
                    name="❤️ Deine HP",
                    value=f"{health_bar} {result['player_health']}/{player['max_health']}",
                    inline=False
                )
                
                # Show active status effects
                status_text = self._get_status_effects_display()
                if status_text:
                    embed.add_field(
                        name="📊 Status",
                        value=status_text,
                        inline=False
                    )
                
                if result['player_health'] <= 0:
                    for item in self.children:
                        item.disabled = True
                    self.stop()
                    embed.color = discord.Color.dark_red()
                
                await interaction.edit_original_response(embed=embed, view=self if result['player_health'] > 0 else None)
            
        except Exception as e:
            logger.error(f"Error running from combat: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Fehler: {e}")
    
    @discord.ui.button(label="🛡️ Verteidigen", style=discord.ButtonStyle.primary)
    async def defend_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Take a defensive stance to reduce incoming damage."""
        try:
            await interaction.response.defer()
        except discord.errors.NotFound:
            logger.warning("Defend button interaction expired")
            return
        
        try:
            result = await rpg_system.process_combat_turn(
                db_helpers, 
                self.user_id, 
                self.monster, 
                'defend',
                combat_state=self.combat_state
            )
            
            if 'error' in result:
                await interaction.followup.send(f"❌ Fehler: {result['error']}")
                return
            
            # Update combat state from result
            if 'combat_state' in result:
                self.combat_state = result['combat_state']
            
            # Update monster health to track current state
            if 'monster_health' in result:
                self.monster['health'] = result['monster_health']
            
            self.turn_count += 1
            
            player = await rpg_system.get_player_profile(db_helpers, self.user_id)
            
            embed = discord.Embed(
                title=f"🛡️ Kampfrunde {self.turn_count} - Verteidigung",
                description="\n".join(result['messages']),
                color=discord.Color.blue()
            )
            
            # Add health bars
            player_health_pct = (result['player_health'] / player['max_health']) * 100 if player else 0
            monster_health_pct = (result['monster_health'] / self.monster_max_health) * 100 if self.monster_max_health > 0 else 0
            
            player_bar = self._create_health_bar(player_health_pct)
            monster_bar = self._create_health_bar(monster_health_pct)
            
            embed.add_field(
                name="❤️ Deine HP",
                value=f"{player_bar} {result['player_health']}/{player['max_health']}",
                inline=True
            )
            
            if not result['combat_over']:
                embed.add_field(
                    name=f"🐉 {self.monster['name']} HP",
                    value=f"{monster_bar} {result['monster_health']}/{self.monster_max_health}",
                    inline=True
                )
            
            # Show active status effects
            status_text = self._get_status_effects_display()
            if status_text:
                embed.add_field(
                    name="📊 Status",
                    value=status_text,
                    inline=False
                )
            
            if result['combat_over']:
                for item in self.children:
                    item.disabled = True
                
                if result['player_won']:
                    embed.color = discord.Color.green()
                    if result.get('rewards'):
                        rewards = result['rewards']
                        embed.add_field(
                            name="🎉 Sieg!",
                            value=f"**+{rewards['gold']} Gold**\n**+{rewards['xp']} XP**",
                            inline=False
                        )
                    continue_view = RPGContinueAdventureView(self.user_id)
                    await interaction.edit_original_response(embed=embed, view=continue_view)
                else:
                    embed.color = discord.Color.dark_red()
                    embed.set_footer(text="Du wurdest mit halber HP ins Dorf zurückgebracht.")
                    await interaction.edit_original_response(embed=embed, view=None)
                
                self.stop()
            else:
                # Update attack button based on rage status (defending builds rage!)
                self._update_attack_button()
                await interaction.edit_original_response(embed=embed, view=self)
            
        except Exception as e:
            logger.error(f"Error defending in combat: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Fehler: {e}")


class RPGEventView(discord.ui.View):
    """View for non-combat adventure events."""
    
    def __init__(self, user_id: int, event: dict):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.event = event
        self.claimed = False  # Track if rewards were already claimed
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Dies ist nicht dein Abenteuer!", ephemeral=True)
            return False
        return True
    
    @discord.ui.button(label="✅ Belohnungen einsammeln", style=discord.ButtonStyle.success)
    async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Claim event rewards."""
        # Prevent double-claiming
        if self.claimed:
            try:
                await interaction.response.send_message("❌ Du hast die Belohnungen bereits eingesammelt!", ephemeral=True)
            except discord.errors.NotFound:
                pass
            return
        
        try:
            await interaction.response.defer()
        except discord.errors.NotFound:
            # Interaction has expired
            logger.warning("Claim button interaction expired")
            return
        
        try:
            # Claim rewards
            success, message = await rpg_system.claim_adventure_event(db_helpers, self.user_id, self.event)
            
            if success:
                self.claimed = True
                embed = discord.Embed(
                    title="✅ Belohnungen erhalten!",
                    description=message,
                    color=discord.Color.green()
                )
                
                # Show what was claimed
                rewards = []
                if 'gold_reward' in self.event:
                    rewards.append(f"💰 +{self.event['gold_reward']} Gold")
                if 'xp_reward' in self.event:
                    rewards.append(f"⭐ +{self.event['xp_reward']} XP")
                if 'heal_amount' in self.event and self.event['heal_amount'] > 0:
                    rewards.append(f"❤️ +{self.event['heal_amount']} HP geheilt")
                
                if rewards:
                    embed.add_field(name="Erhalten:", value="\n".join(rewards), inline=False)
                
                # Check for level up
                if self.event.get('leveled_up') and self.event.get('new_level'):
                    embed.add_field(
                        name="🎊 Level Up!",
                        value=f"Du bist jetzt **Level {self.event.get('new_level')}**!",
                        inline=False
                    )
                
                # Disable claim button
                for item in self.children:
                    item.disabled = True
                
                # Check if event allows continuing adventure
                if self.event.get('can_continue', False):
                    embed.set_footer(text="🎮 Du kannst weiter abenteuern!")
                    continue_view = RPGContinueAdventureView(self.user_id)
                    await interaction.edit_original_response(embed=embed, view=continue_view)
                else:
                    embed.set_footer(text="Nutze /rpg um weiterzuspielen!")
                    await interaction.edit_original_response(embed=embed, view=None)
                
                self.stop()
            else:
                await interaction.followup.send(f"❌ {message}", ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error claiming event rewards: {e}", exc_info=True)
            try:
                await interaction.followup.send("❌ Fehler beim Einsammeln der Belohnungen.", ephemeral=True)
            except Exception:
                pass


# Damage type emoji mapping (used in format_item_details)
DAMAGE_TYPE_EMOJIS = {
    'physical': '⚔️',
    'fire': '🔥',
    'ice': '❄️',
    'lightning': '⚡',
    'poison': '🧪',
    'dark': '🌑',
    'light': '✨',
    'magic': '🔮',
    'wind': '💨',
    'earth': '🪨',
    'water': '💧'
}


def format_item_details(item: dict) -> discord.Embed:
    """
    Format detailed item information for purchase confirmation.
    Shows stats, effects, and status effects in a comprehensive embed.
    
    Args:
        item: Item dictionary from database
    
    Returns:
        Discord embed with detailed item information
    """
    # Get rarity color
    rarity_color = rpg_system.RARITY_COLORS.get(item.get('rarity', 'common'), discord.Color.light_grey())
    
    # Rarity emoji mapping
    rarity_emojis = {
        'common': '⬜',
        'uncommon': '🟩',
        'rare': '🟦',
        'epic': '🟪',
        'legendary': '🟨'
    }
    rarity_emoji = rarity_emojis.get(item.get('rarity', 'common'), '⬜')
    
    # Type emoji mapping
    type_emojis = {
        'weapon': '⚔️',
        'skill': '🔮',
        'consumable': '🧪',
        'material': '📦'
    }
    type_emoji = type_emojis.get(item.get('type', 'weapon'), '📦')
    
    # Create embed
    embed = discord.Embed(
        title=f"{type_emoji} {item['name']}",
        description=item.get('description', 'Keine Beschreibung verfügbar.'),
        color=rarity_color
    )
    
    # Basic info
    embed.add_field(
        name="📋 Grundinfo",
        value=f"{rarity_emoji} **Seltenheit:** {item.get('rarity', 'common').capitalize()}\n"
              f"📁 **Typ:** {item.get('type', 'Unbekannt').capitalize()}\n"
              f"📊 **Min. Level:** {item.get('required_level', 1)}",
        inline=True
    )
    
    # Stats section (for weapons)
    if item.get('type') == 'weapon':
        damage = item.get('damage', 0)
        damage_type = item.get('damage_type', 'physical')
        dmg_emoji = DAMAGE_TYPE_EMOJIS.get(damage_type, '⚔️')
        
        embed.add_field(
            name="⚔️ Kampfwerte",
            value=f"💥 **Schaden:** {damage}\n"
                  f"{dmg_emoji} **Schadenstyp:** {damage_type.capitalize()}",
            inline=True
        )
    
    # Stats section (for skills with damage)
    elif item.get('type') == 'skill' and item.get('damage'):
        damage = item.get('damage', 0)
        damage_type = item.get('damage_type', 'magic')
        dmg_emoji = DAMAGE_TYPE_EMOJIS.get(damage_type, '🔮')
        
        embed.add_field(
            name="🔮 Skill-Werte",
            value=f"💥 **Schaden:** {damage}\n"
                  f"{dmg_emoji} **Element:** {damage_type.capitalize()}",
            inline=True
        )
    
    # Parse and display effects
    effects_text = ""
    effects = item.get('effects')
    if effects:
        try:
            # Parse effects if it's a JSON string
            if isinstance(effects, str):
                effects_dict = json.loads(effects)
            else:
                effects_dict = effects
            
            # Map effect keys to readable descriptions
            effect_descriptions = {
                # Healing effects
                'heal': ('💚', 'Heilt', 'HP'),
                'regen': ('💚', 'Regeneration', 'Runden'),
                'heal_per_turn': ('💚', 'Heilung/Runde', 'HP'),
                
                # Buff effects
                'shield': ('🛡️', 'Schild', 'Runden'),
                'defense_bonus': ('🛡️', 'Verteidigung +', ''),
                'speed_boost': ('⚡', 'Geschwindigkeit', 'Runden'),
                'attack_boost': ('⚔️', 'Angriff', 'Runden'),
                'damage_bonus': ('💥', 'Schadensbonus', '%'),
                'crit_boost': ('🎯', 'Krit-Chance', 'Runden'),
                'accuracy_boost': ('🎯', 'Trefferchance', 'Runden'),
                'dodge_boost': ('💨', 'Ausweichen', 'Runden'),
                'all_stats_boost': ('📊', 'Alle Stats', 'Runden'),
                'stat_bonus': ('📊', 'Stat-Bonus', '%'),
                
                # Debuff/Status effects
                'burn': ('🔥', 'Verbrennung', '% Chance'),
                'freeze': ('❄️', 'Einfrieren', '% Chance'),
                'poison': ('🧪', 'Vergiftung', '% Chance'),
                'static': ('⚡', 'Lähmung', '% Chance'),
                'darkness': ('🌑', 'Blenden', '% Chance'),
                'light': ('✨', 'Licht', '% Chance'),
                'slow': ('🐌', 'Verlangsamung', '% Chance'),
                'weaken': ('💔', 'Schwächung', 'Runden'),
                'attack_reduction': ('⬇️', 'Angriffsred.', '%'),
                'curse': ('☠️', 'Fluch', 'Runden'),
                'all_stats_reduction': ('⬇️', 'Stats-Red.', '%'),
                'paralyze': ('🔌', 'Paralyse', '% Chance'),
                'stun': ('💫', 'Betäubung', 'Runden'),
                'static': ('⚡', 'Statisch', '% Chance'),
                'lifesteal': ('🧛', 'Lebensentzug', '%'),
                
                # Special effects
                'ironSkin': ('🛡️', 'Eisenhaut', 'Runden'),
                'mana_shield': ('🔮', 'Mana-Schild', 'Runden'),
                'magic_defense': ('🔮', 'Mag. Vert. +', ''),
                'invulnerable': ('✨', 'Unverwundbar', 'Runden'),
                'reflect': ('🪞', 'Reflektion', 'Runden'),
                'reflect_damage': ('🪞', 'Refl. Schaden', '%'),
                'rage': ('😡', 'Wut', 'Runden'),
                'escape': ('🏃', 'Flucht', '% Chance'),
                'time_stop': ('⏰', 'Zeitstopp', 'Runden'),
                'extra_turn': ('➡️', 'Extra-Runde', ''),
                'mana_drain': ('🔮', 'Mana-Entzug', '%'),
                'counter': ('↩️', 'Konter', 'Runden'),
                'counter_damage': ('↩️', 'Konter-Schaden', '%'),
                'double_attack': ('⚔️', 'Doppelschlag', 'Runden'),
                'triple_attack': ('⚔️', 'Dreifachschlag', ''),
            }
            
            for effect_key, effect_value in effects_dict.items():
                if effect_key in effect_descriptions:
                    emoji, name, unit = effect_descriptions[effect_key]
                    # Format value based on type
                    if isinstance(effect_value, bool):
                        value_str = "Ja" if effect_value else "Nein"
                    elif isinstance(effect_value, float) and effect_value <= 1 and '%' in unit:
                        value_str = f"{int(effect_value * 100)}"
                    else:
                        value_str = str(effect_value)
                    
                    effects_text += f"{emoji} **{name}:** {value_str}{' ' + unit if unit else ''}\n"
                else:
                    # Unknown effect, display raw
                    effects_text += f"🔹 **{effect_key}:** {effect_value}\n"
            
        except (json.JSONDecodeError, TypeError) as e:
            logger.debug(f"Could not parse effects: {effects}, error: {e}")
            effects_text = "Keine speziellen Effekte."
    
    if effects_text:
        embed.add_field(
            name="✨ Effekte & Status",
            value=effects_text[:1024] if len(effects_text) > 1024 else effects_text,  # Discord limit
            inline=False
        )
    
    # Price field
    embed.add_field(
        name="💰 Preis",
        value=f"**{item.get('price', 0)} Gold**",
        inline=True
    )
    
    embed.set_footer(text="Möchtest du dieses Item kaufen?")
    
    return embed


class RPGShopConfirmView(discord.ui.View):
    """Confirmation view for RPG shop purchases."""
    
    def __init__(self, user_id: int, item: dict, items: list, player_gold: int):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.item = item
        self.items = items
        self.player_gold = player_gold
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Dies ist nicht dein Kauf!", ephemeral=True)
            return False
        return True
    
    @discord.ui.button(label="✅ Kaufen", style=discord.ButtonStyle.success, row=0)
    async def confirm_purchase(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm the purchase."""
        await interaction.response.defer()
        
        try:
            # Perform the actual purchase
            success, message = await rpg_system.purchase_item(db_helpers, self.user_id, self.item['id'])
            
            if success:
                # Create success embed with item details
                rarity_color = rpg_system.RARITY_COLORS.get(self.item.get('rarity', 'common'), discord.Color.green())
                embed = discord.Embed(
                    title="✅ Kauf erfolgreich!",
                    description=f"Du hast **{self.item['name']}** für **{self.item['price']} Gold** gekauft!",
                    color=rarity_color
                )
                
                # Add brief item info
                if self.item.get('type') == 'weapon':
                    embed.add_field(
                        name="⚔️ Waffe erhalten",
                        value=f"💥 Schaden: {self.item.get('damage', 0)}\n"
                              f"📁 Typ: {self.item.get('damage_type', 'physical').capitalize()}",
                        inline=True
                    )
                elif self.item.get('type') == 'skill':
                    skill_info = f"🔮 Skill erhalten"
                    if self.item.get('damage'):
                        embed.add_field(
                            name=skill_info,
                            value=f"💥 Schaden: {self.item.get('damage', 0)}\n"
                                  f"📁 Element: {self.item.get('damage_type', 'magic').capitalize()}",
                            inline=True
                        )
                    else:
                        embed.add_field(
                            name=skill_info,
                            value="Rüste den Skill im Inventar aus!",
                            inline=True
                        )
                
                embed.set_footer(text="Nutze /rpg um dein Inventar anzuzeigen!")
                
                # Disable buttons after purchase
                for child in self.children:
                    child.disabled = True
                
                await interaction.edit_original_response(embed=embed, view=self)
            else:
                await interaction.followup.send(f"❌ {message}", ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error confirming purchase: {e}", exc_info=True)
            await interaction.followup.send("❌ Fehler beim Kauf.", ephemeral=True)
    
    @discord.ui.button(label="❌ Abbrechen", style=discord.ButtonStyle.danger, row=0)
    async def cancel_purchase(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel the purchase and return to shop."""
        await interaction.response.defer()
        
        try:
            # Get fresh player data
            player = await rpg_system.get_player_profile(db_helpers, self.user_id)
            if not player:
                await interaction.followup.send("❌ Fehler beim Laden deines Profils.", ephemeral=True)
                return
            
            # Rebuild shop embed
            embed = discord.Embed(
                title="🏪 RPG Shop",
                description=f"Dein Gold: **{player['gold']}** 💰\n\nWähle ein Item, um Details anzuzeigen.",
                color=discord.Color.gold()
            )
            
            for item in self.items[:10]:  # Show max 10 items
                rarity_emoji = {'common': '⬜', 'uncommon': '🟩', 'rare': '🟦', 'epic': '🟪', 'legendary': '🟨'}
                r_emoji = rarity_emoji.get(item['rarity'], '⬜')
                embed.add_field(
                    name=f"{r_emoji} {item['name']}",
                    value=f"💰 {item['price']} Gold | ⚔️ {item.get('damage', '-')}",
                    inline=True
                )
            
            embed.set_footer(text="Wähle ein Item für Details!")
            
            # Return to shop view
            view = RPGShopView(self.user_id, self.items, player['gold'])
            await interaction.edit_original_response(embed=embed, view=view)
            
        except Exception as e:
            logger.error(f"Error canceling purchase: {e}", exc_info=True)
            await interaction.followup.send("❌ Fehler beim Abbrechen.", ephemeral=True)


class RPGShopView(discord.ui.View):
    """View for RPG shop item selection."""
    
    def __init__(self, user_id: int, items: list, player_gold: int):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.items = items
        self.player_gold = player_gold
        
        # Add select menu for items
        options = []
        for i, item in enumerate(items[:25]):  # Max 25 options
            options.append(discord.SelectOption(
                label=f"{item['name']} ({item['price']} Gold)",
                description=f"{item['type']} - {item['rarity']}",
                value=str(item['id'])
            ))
        
        if options:
            select = discord.ui.Select(
                placeholder="Wähle ein Item zum Kaufen...",
                options=options,
                row=0
            )
            select.callback = self.item_selected
            self.add_item(select)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Dies ist nicht dein Shop!", ephemeral=True)
            return False
        return True
    
    async def item_selected(self, interaction: discord.Interaction):
        """Handle item selection - show confirmation with details."""
        await interaction.response.defer()
        
        try:
            item_id = int(interaction.data['values'][0])
            item = next((i for i in self.items if i['id'] == item_id), None)
            
            if not item:
                await interaction.followup.send("❌ Item nicht gefunden.", ephemeral=True)
                return
            
            # Show item details with confirmation buttons
            embed = format_item_details(item)
            
            # Add player's gold info to the embed
            can_afford = self.player_gold >= item.get('price', 0)
            if can_afford:
                embed.add_field(
                    name="💳 Dein Gold",
                    value=f"**{self.player_gold}** 💰 ✅",
                    inline=True
                )
            else:
                embed.add_field(
                    name="💳 Dein Gold",
                    value=f"**{self.player_gold}** 💰 ❌\n*Nicht genug Gold!*",
                    inline=True
                )
            
            # Create confirmation view
            view = RPGShopConfirmView(self.user_id, item, self.items, self.player_gold)
            await interaction.edit_original_response(embed=embed, view=view)
                
        except Exception as e:
            logger.error(f"Error showing item details: {e}", exc_info=True)
            await interaction.followup.send("❌ Fehler beim Laden der Item-Details.", ephemeral=True)
    
    @discord.ui.button(label="🔙 Zurück", style=discord.ButtonStyle.secondary, row=1)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Return to main RPG menu."""
        await interaction.response.defer()
        
        try:
            # Get fresh player data
            player = await rpg_system.get_player_profile(db_helpers, self.user_id)
            if not player:
                await interaction.followup.send("❌ Fehler beim Laden deines Profils.", ephemeral=True)
                return
            
            # Create main RPG menu embed
            embed = discord.Embed(
                title=f"⚔️ RPG Profil - {interaction.user.display_name}",
                description=f"**Level {player['level']}** | Welt: {rpg_system.WORLDS[player['world']]['name']}",
                color=discord.Color.purple()
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            
            # Stats
            embed.add_field(
                name="📊 Attribute",
                value=f"❤️ HP: {player['health']}/{player['max_health']}\n"
                      f"⚔️ Stärke: {player['strength']}\n"
                      f"🎯 Geschick: {player['dexterity']}\n"
                      f"🛡️ Verteidigung: {player['defense']}\n"
                      f"⚡ Geschwindigkeit: {player['speed']}",
                inline=True
            )
            
            # Progression
            xp_needed = rpg_system.calculate_xp_for_level(player['level'] + 1)
            xp_progress = player['xp']
            progress_pct = (xp_progress / xp_needed) * 100 if xp_needed > 0 else 100
            
            embed.add_field(
                name="📈 Fortschritt",
                value=f"XP: {xp_progress}/{xp_needed}\n"
                      f"Fortschritt: {progress_pct:.1f}%\n"
                      f"💎 Skillpunkte: {player['skill_points']}\n"
                      f"💰 Gold: {player['gold']}",
                inline=True
            )
            
            embed.add_field(
                name="🎮 Verfügbare Aktionen",
                value="Wähle eine Aktion aus den Buttons unten!",
                inline=False
            )
            
            embed.set_footer(text="Nutze die Buttons um dein Abenteuer zu beginnen!")
            
            # Return to main menu view
            view = RPGMenuView(self.user_id, player)
            await interaction.edit_original_response(embed=embed, view=view)
            
        except Exception as e:
            logger.error(f"Error returning to RPG menu: {e}", exc_info=True)
            await interaction.followup.send("❌ Fehler beim Zurückkehren.", ephemeral=True)


class RPGTempleView(discord.ui.View):
    """View for temple healing and blessings."""
    
    def __init__(self, user_id: int, player: dict, missing_hp: int, heal_cost: int):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.player = player
        self.missing_hp = missing_hp
        self.heal_cost = heal_cost
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Dies ist nicht dein Tempel!", ephemeral=True)
            return False
        return True
    
    @discord.ui.button(label="💚 Heilen", style=discord.ButtonStyle.success)
    async def heal_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Heal the player."""
        await interaction.response.defer()
        
        try:
            if self.missing_hp <= 0:
                await interaction.followup.send("❌ Du bist bereits vollständig geheilt!", ephemeral=True)
                return
            
            if self.player['gold'] < self.heal_cost:
                await interaction.followup.send(f"❌ Nicht genug Gold! Du brauchst {self.heal_cost} Gold.", ephemeral=True)
                return
            
            # Heal player
            success = await rpg_system.heal_player(db_helpers, self.user_id, self.heal_cost)
            
            if success:
                embed = discord.Embed(
                    title="💚 Geheilt!",
                    description=f"Du wurdest vollständig geheilt!\nKosten: {self.heal_cost} Gold",
                    color=discord.Color.green()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send("❌ Heilung fehlgeschlagen.", ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error healing player: {e}", exc_info=True)
            await interaction.followup.send("❌ Fehler bei der Heilung.", ephemeral=True)
    
    @discord.ui.button(label="🔮 XP Segen", style=discord.ButtonStyle.primary, row=0)
    async def xp_blessing_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Give XP blessing."""
        await interaction.response.defer()
        
        try:
            cost = 100
            if self.player['gold'] < cost:
                await interaction.followup.send(f"❌ Nicht genug Gold! Du brauchst {cost} Gold.", ephemeral=True)
                return
            
            # Apply blessing
            success = await rpg_system.apply_blessing(db_helpers, self.user_id, 'xp_boost', cost)
            
            if success:
                embed = discord.Embed(
                    title="✨ Segen erhalten!",
                    description="XP-Boost für 1 Stunde aktiv! (+50% XP)",
                    color=discord.Color.gold()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send("❌ Segen fehlgeschlagen.", ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error applying blessing: {e}", exc_info=True)
            await interaction.followup.send("❌ Fehler beim Segen.", ephemeral=True)
    
    @discord.ui.button(label="🔋 Skills aufladen", style=discord.ButtonStyle.success, row=0)
    async def recharge_skills_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Recharge all skill uses."""
        await interaction.response.defer()
        
        try:
            recharge_cost = 50  # Base cost to recharge skills
            
            if self.player['gold'] < recharge_cost:
                await interaction.followup.send(f"❌ Nicht genug Gold! Du brauchst {recharge_cost} Gold.", ephemeral=True)
                return
            
            success, message = await rpg_system.recharge_skills(db_helpers, self.user_id, recharge_cost)
            
            if success:
                embed = discord.Embed(
                    title="🔋 Skills aufgeladen!",
                    description=f"{message}\nKosten: {recharge_cost} Gold",
                    color=discord.Color.green()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(f"❌ {message}", ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error recharging skills: {e}", exc_info=True)
            await interaction.followup.send("❌ Fehler beim Aufladen.", ephemeral=True)
    
    @discord.ui.button(label="💎 Skillpunkte zurücksetzen", style=discord.ButtonStyle.primary, row=1)
    async def respec_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Reset skill points and redistribute stats."""
        await interaction.response.defer()
        
        try:
            # Calculate total stats invested (beyond base for each stat)
            total_invested = (
                (self.player['strength'] - rpg_system.BASE_STAT_VALUE) +
                (self.player['dexterity'] - rpg_system.BASE_STAT_VALUE) +
                (self.player['defense'] - rpg_system.BASE_STAT_VALUE) +
                (self.player['speed'] - rpg_system.BASE_STAT_VALUE)
            )
            
            if total_invested <= 0:
                await interaction.followup.send("❌ Du hast keine Skillpunkte ausgegeben!", ephemeral=True)
                return
            
            # Cost for respec (using game constant)
            respec_cost = total_invested * rpg_system.RESPEC_COST_PER_POINT
            
            if self.player['gold'] < respec_cost:
                await interaction.followup.send(
                    f"❌ Nicht genug Gold! Du brauchst {respec_cost} Gold für {total_invested} Skillpunkte.",
                    ephemeral=True
                )
                return
            
            # Reset stats to base and return skill points
            success = await rpg_system.reset_skill_points(db_helpers, self.user_id, respec_cost)
            
            if success:
                embed = discord.Embed(
                    title="💎 Skillpunkte zurückgesetzt!",
                    description=f"Alle Attribute wurden auf {rpg_system.BASE_STAT_VALUE} zurückgesetzt.\n"
                                f"Du hast {total_invested} Skillpunkte zurückerhalten!\n"
                                f"Kosten: {respec_cost} Gold",
                    color=discord.Color.blue()
                )
                embed.add_field(
                    name="ℹ️ Info",
                    value="Öffne dein RPG-Profil mit `/rpg` und nutze die Stats-Buttons um deine Punkte neu zu verteilen!",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send("❌ Zurücksetzen fehlgeschlagen.", ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error resetting skill points: {e}", exc_info=True)
            await interaction.followup.send("❌ Fehler beim Zurücksetzen.", ephemeral=True)
    
    @discord.ui.button(label="🌳 Skill-Baum", style=discord.ButtonStyle.primary, row=2)
    async def skill_tree_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open skill tree from temple."""
        await interaction.response.defer()
        
        try:
            # Get unlocked skills
            unlocked_skills = await rpg_system.get_unlocked_skills(db_helpers, self.user_id)
            
            embed = discord.Embed(
                title="🌳 Skill-Baum im Tempel",
                description=f"**Skillpunkte verfügbar: {self.player['skill_points']}**\n\n"
                           f"Wähle einen Pfad, um Skills freizuschalten!\n"
                           f"💡 Du erhältst Skillpunkte beim Level-Aufstieg.",
                color=discord.Color.purple()
            )
            
            # Show available paths
            for path_key, path_data in rpg_system.SKILL_TREE.items():
                unlocked_count = len(unlocked_skills.get(path_key, []))
                total_count = len(path_data['skills'])
                
                path_text = f"{path_data['emoji']} **{path_data['name']}**\n"
                path_text += f"{path_data['description']}\n"
                path_text += f"Fortschritt: {unlocked_count}/{total_count} Skills"
                
                embed.add_field(name="\u200b", value=path_text, inline=False)
            
            embed.set_footer(text="🔍 Nutze die Suchfunktion um schnell Skills zu finden!")
            
            view = RPGTempleSkillTreeView(self.user_id, self.player['skill_points'], unlocked_skills)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error opening skill tree from temple: {e}", exc_info=True)
            await interaction.followup.send("❌ Fehler beim Öffnen des Skill-Baums.", ephemeral=True)
    
    @discord.ui.button(label="🔙 Zurück", style=discord.ButtonStyle.secondary, row=2)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Return to main RPG menu."""
        await interaction.response.defer()
        
        try:
            # Get fresh player data
            player = await rpg_system.get_player_profile(db_helpers, self.user_id)
            if not player:
                await interaction.followup.send("❌ Fehler beim Laden deines Profils.", ephemeral=True)
                return
            
            # Create main RPG menu embed
            embed = discord.Embed(
                title=f"⚔️ RPG Profil - {interaction.user.display_name}",
                description=f"**Level {player['level']}** | Welt: {rpg_system.WORLDS[player['world']]['name']}",
                color=discord.Color.purple()
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            
            # Stats
            embed.add_field(
                name="📊 Attribute",
                value=f"❤️ HP: {player['health']}/{player['max_health']}\n"
                      f"⚔️ Stärke: {player['strength']}\n"
                      f"🎯 Geschick: {player['dexterity']}\n"
                      f"🛡️ Verteidigung: {player['defense']}\n"
                      f"⚡ Geschwindigkeit: {player['speed']}",
                inline=True
            )
            
            # Progression
            xp_needed = rpg_system.calculate_xp_for_level(player['level'] + 1)
            xp_progress = player['xp']
            progress_pct = (xp_progress / xp_needed) * 100 if xp_needed > 0 else 100
            
            embed.add_field(
                name="📈 Fortschritt",
                value=f"XP: {xp_progress}/{xp_needed}\n"
                      f"Fortschritt: {progress_pct:.1f}%\n"
                      f"💎 Skillpunkte: {player['skill_points']}\n"
                      f"💰 Gold: {player['gold']}",
                inline=True
            )
            
            embed.add_field(
                name="🎮 Verfügbare Aktionen",
                value="Wähle eine Aktion aus den Buttons unten!",
                inline=False
            )
            
            embed.set_footer(text="Nutze die Buttons um dein Abenteuer zu beginnen!")
            
            # Return to main menu view
            view = RPGMenuView(self.user_id, player)
            await interaction.edit_original_response(embed=embed, view=view)
            
        except Exception as e:
            logger.error(f"Error returning to RPG menu: {e}", exc_info=True)
            await interaction.followup.send("❌ Fehler beim Zurückkehren.", ephemeral=True)


class RPGInventoryView(discord.ui.View):
    """View for inventory management and equipment."""
    
    def __init__(self, user_id: int, inventory: list, equipped: dict):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.inventory = inventory or []
        self.equipped = equipped
        
        # Add select menu for weapons
        weapon_options = []
        for item in [i for i in self.inventory if i.get('type') == 'weapon'][:25]:
            weapon_options.append(discord.SelectOption(
                label=item['name'],
                description=f"Schaden: {item.get('damage', 0)}",
                value=str(item['item_id'])  # Use item_id, not id
            ))
        
        if weapon_options:
            weapon_select = discord.ui.Select(
                placeholder="Waffe ausrüsten...",
                options=weapon_options,
                row=0
            )
            weapon_select.callback = self.equip_weapon
            self.add_item(weapon_select)
        
        # Get skill items from inventory
        skill_items = [i for i in self.inventory if i.get('type') == 'skill'][:25]
        
        # Add select menu for Skill Slot 1
        if skill_items:
            skill1_options = []
            for item in skill_items:
                skill1_options.append(discord.SelectOption(
                    label=item['name'],
                    description=f"Typ: Skill",
                    value=str(item['item_id'])
                ))
            
            skill1_select = discord.ui.Select(
                placeholder="🔮 Skill 1 ausrüsten...",
                options=skill1_options,
                row=1
            )
            skill1_select.callback = self.equip_skill_slot1
            self.add_item(skill1_select)
        
        # Add select menu for Skill Slot 2
        if skill_items:
            skill2_options = []
            for item in skill_items:
                skill2_options.append(discord.SelectOption(
                    label=item['name'],
                    description=f"Typ: Skill",
                    value=str(item['item_id'])
                ))
            
            skill2_select = discord.ui.Select(
                placeholder="🔮 Skill 2 ausrüsten...",
                options=skill2_options,
                row=2
            )
            skill2_select.callback = self.equip_skill_slot2
            self.add_item(skill2_select)
        
        # Add select menu for selling items (exclude quest items)
        sellable_items = [i for i in self.inventory if not i.get('is_quest_item', False) and i.get('type') != 'quest_item'][:25]
        sell_options = []
        for item in sellable_items:
            sell_price = int(item.get('price', 0) * 0.5)
            sell_options.append(discord.SelectOption(
                label=f"🪙 {item['name']}",
                description=f"Verkaufen für {sell_price} Gold (x{item.get('quantity', 1)})",
                value=str(item['item_id'])
            ))
        
        if sell_options:
            sell_select = discord.ui.Select(
                placeholder="💰 Item verkaufen...",
                options=sell_options,
                row=3
            )
            sell_select.callback = self.sell_item
            self.add_item(sell_select)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Dies ist nicht dein Inventar!", ephemeral=True)
            return False
        return True
    
    async def equip_weapon(self, interaction: discord.Interaction):
        """Equip a weapon."""
        await interaction.response.defer()
        
        try:
            item_id = int(interaction.data['values'][0])
            success = await rpg_system.equip_item(db_helpers, self.user_id, item_id, 'weapon')
            
            if success:
                await interaction.followup.send("✅ Waffe ausgerüstet!", ephemeral=True)
            else:
                await interaction.followup.send("❌ Konnte Waffe nicht ausrüsten.", ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error equipping weapon: {e}", exc_info=True)
            await interaction.followup.send("❌ Fehler beim Ausrüsten.", ephemeral=True)
    
    async def equip_skill_slot1(self, interaction: discord.Interaction):
        """Equip a skill to slot 1."""
        await interaction.response.defer()
        
        try:
            item_id = int(interaction.data['values'][0])
            success = await rpg_system.equip_item(db_helpers, self.user_id, item_id, 'skill', slot=1)
            
            if success:
                await interaction.followup.send("✅ Skill in Slot 1 ausgerüstet!", ephemeral=True)
            else:
                await interaction.followup.send("❌ Konnte Skill nicht ausrüsten.", ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error equipping skill to slot 1: {e}", exc_info=True)
            await interaction.followup.send("❌ Fehler beim Ausrüsten.", ephemeral=True)
    
    async def equip_skill_slot2(self, interaction: discord.Interaction):
        """Equip a skill to slot 2."""
        await interaction.response.defer()
        
        try:
            item_id = int(interaction.data['values'][0])
            success = await rpg_system.equip_item(db_helpers, self.user_id, item_id, 'skill', slot=2)
            
            if success:
                await interaction.followup.send("✅ Skill in Slot 2 ausgerüstet!", ephemeral=True)
            else:
                await interaction.followup.send("❌ Konnte Skill nicht ausrüsten.", ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error equipping skill to slot 2: {e}", exc_info=True)
            await interaction.followup.send("❌ Fehler beim Ausrüsten.", ephemeral=True)
    
    async def sell_item(self, interaction: discord.Interaction):
        """Sell an item from inventory."""
        await interaction.response.defer()
        
        try:
            item_id = int(interaction.data['values'][0])
            success, message = await rpg_system.sell_item(db_helpers, self.user_id, item_id, 1)
            
            if success:
                embed = discord.Embed(
                    title="💰 Item verkauft!",
                    description=message,
                    color=discord.Color.gold()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(f"❌ {message}", ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error selling item: {e}", exc_info=True)
            await interaction.followup.send("❌ Fehler beim Verkaufen.", ephemeral=True)
    
    @discord.ui.button(label="🔙 Zurück", style=discord.ButtonStyle.secondary, row=4)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Return to main RPG menu."""
        await interaction.response.defer()
        
        try:
            # Get fresh player data
            player = await rpg_system.get_player_profile(db_helpers, self.user_id)
            if not player:
                await interaction.followup.send("❌ Fehler beim Laden deines Profils.", ephemeral=True)
                return
            
            # Create main RPG menu embed
            embed = discord.Embed(
                title=f"⚔️ RPG Profil - {interaction.user.display_name}",
                description=f"**Level {player['level']}** | Welt: {rpg_system.WORLDS[player['world']]['name']}",
                color=discord.Color.purple()
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            
            # Stats
            embed.add_field(
                name="📊 Attribute",
                value=f"❤️ HP: {player['health']}/{player['max_health']}\n"
                      f"⚔️ Stärke: {player['strength']}\n"
                      f"🎯 Geschick: {player['dexterity']}\n"
                      f"🛡️ Verteidigung: {player['defense']}\n"
                      f"⚡ Geschwindigkeit: {player['speed']}",
                inline=True
            )
            
            # Progression
            xp_needed = rpg_system.calculate_xp_for_level(player['level'] + 1)
            xp_progress = player['xp']
            progress_pct = (xp_progress / xp_needed) * 100 if xp_needed > 0 else 100
            
            embed.add_field(
                name="📈 Fortschritt",
                value=f"XP: {xp_progress}/{xp_needed}\n"
                      f"Fortschritt: {progress_pct:.1f}%\n"
                      f"💎 Skillpunkte: {player['skill_points']}\n"
                      f"💰 Gold: {player['gold']}",
                inline=True
            )
            
            embed.add_field(
                name="🎮 Verfügbare Aktionen",
                value="Wähle eine Aktion aus den Buttons unten!",
                inline=False
            )
            
            embed.set_footer(text="Nutze die Buttons um dein Abenteuer zu beginnen!")
            
            # Return to main menu view
            view = RPGMenuView(self.user_id, player)
            await interaction.edit_original_response(embed=embed, view=view)
            
        except Exception as e:
            logger.error(f"Error returning to RPG menu: {e}", exc_info=True)
            await interaction.followup.send("❌ Fehler beim Zurückkehren.", ephemeral=True)


class RPGTempleSkillTreeView(discord.ui.View):
    """Skill tree view from the temple with search functionality."""
    
    def __init__(self, user_id: int, skill_points: int, unlocked_skills: dict):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.skill_points = skill_points
        self.unlocked_skills = unlocked_skills
        
        # Add select menu for skill paths
        path_options = []
        for path_key, path_data in rpg_system.SKILL_TREE.items():
            unlocked_count = len(unlocked_skills.get(path_key, []))
            total_count = len(path_data['skills'])
            
            path_options.append(discord.SelectOption(
                label=path_data['name'],
                description=f"{path_data['description'][:50]}... ({unlocked_count}/{total_count})",
                value=path_key,
                emoji=path_data['emoji']
            ))
        
        if path_options:
            path_select = discord.ui.Select(
                placeholder="Wähle einen Pfad...",
                options=path_options,
                row=0
            )
            path_select.callback = self.view_path
            self.add_item(path_select)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Dies ist nicht dein Skill-Baum!", ephemeral=True)
            return False
        return True
    
    async def view_path(self, interaction: discord.Interaction):
        """View skills in a specific path."""
        await interaction.response.defer()
        
        try:
            path_key = interaction.data['values'][0]
            path_data = rpg_system.SKILL_TREE[path_key]
            
            embed = discord.Embed(
                title=f"{path_data['emoji']} {path_data['name']}",
                description=f"{path_data['description']}\n\n**Skillpunkte verfügbar: {self.skill_points}**",
                color=discord.Color.purple()
            )
            
            # Show all skills in path
            unlocked_in_path = self.unlocked_skills.get(path_key, [])
            
            for skill_key, skill_data in path_data['skills'].items():
                is_unlocked = skill_key in unlocked_in_path
                can_unlock = skill_data['requires'] is None or skill_data['requires'] in unlocked_in_path
                
                status = "✅" if is_unlocked else ("🔓" if can_unlock and self.skill_points >= skill_data['cost'] else "🔒")
                
                skill_text = f"{status} **{skill_data['name']}** ({skill_data['type']})\n"
                skill_text += f"📝 {skill_data['description']}\n"
                skill_text += f"💎 Kosten: {skill_data['cost']} Skillpunkte"
                
                if skill_data['requires']:
                    required_skill = path_data['skills'][skill_data['requires']]
                    skill_text += f"\n🔗 Benötigt: {required_skill['name']}"
                
                embed.add_field(name="\u200b", value=skill_text, inline=False)
            
            embed.set_footer(text="Wähle einen Skill zum Freischalten!")
            
            # Create view for unlocking skills
            view = RPGSkillUnlockView(self.user_id, path_key, self.skill_points, unlocked_in_path)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error viewing skill path: {e}", exc_info=True)
            await interaction.followup.send("❌ Fehler beim Anzeigen des Pfads.", ephemeral=True)
    
    @discord.ui.button(label="🔍 Skill suchen", style=discord.ButtonStyle.primary, row=1)
    async def search_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open skill search modal."""
        modal = SkillSearchModal(self.user_id, self.skill_points, self.unlocked_skills)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="🔄 Skill-Baum zurücksetzen", style=discord.ButtonStyle.danger, row=1)
    async def reset_tree_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Reset the entire skill tree."""
        await interaction.response.defer()
        
        try:
            # Calculate refund
            total_spent = 0
            for path_key, skills in self.unlocked_skills.items():
                for skill_key in skills:
                    if path_key in rpg_system.SKILL_TREE and skill_key in rpg_system.SKILL_TREE[path_key]['skills']:
                        total_spent += rpg_system.SKILL_TREE[path_key]['skills'][skill_key]['cost']
            
            if total_spent == 0:
                await interaction.followup.send("❌ Du hast noch keine Skills freigeschaltet!", ephemeral=True)
                return
            
            # Cost for reset
            reset_cost = total_spent * 50  # 50 gold per skill point
            
            # Get player to check gold
            player = await rpg_system.get_player_profile(db_helpers, self.user_id)
            if not player or player['gold'] < reset_cost:
                await interaction.followup.send(
                    f"❌ Nicht genug Gold! Du brauchst {reset_cost} Gold um {total_spent} Skillpunkte zurückzusetzen.",
                    ephemeral=True
                )
                return
            
            # Reset skill tree
            success, message = await rpg_system.reset_skill_tree(db_helpers, self.user_id, reset_cost)
            
            if success:
                embed = discord.Embed(
                    title="🔄 Skill-Baum zurückgesetzt!",
                    description=f"{message}\n\nKosten: {reset_cost} Gold",
                    color=discord.Color.blue()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(f"❌ {message}", ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error resetting skill tree: {e}", exc_info=True)
            await interaction.followup.send("❌ Fehler beim Zurücksetzen.", ephemeral=True)


class SkillSearchModal(discord.ui.Modal, title="Skill suchen"):
    """Modal for searching skills by name."""
    
    search_input = discord.ui.TextInput(
        label="Skill-Name",
        placeholder="Gib den Namen des Skills ein...",
        min_length=2,
        max_length=50,
        required=True
    )
    
    def __init__(self, user_id: int, skill_points: int, unlocked_skills: dict):
        super().__init__()
        self.user_id = user_id
        self.skill_points = skill_points
        self.unlocked_skills = unlocked_skills
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        try:
            search_term = self.search_input.value.lower().strip()
            
            # Search through all skills
            found_skills = []
            for path_key, path_data in rpg_system.SKILL_TREE.items():
                for skill_key, skill_data in path_data['skills'].items():
                    if search_term in skill_data['name'].lower() or search_term in skill_data['description'].lower():
                        is_unlocked = skill_key in self.unlocked_skills.get(path_key, [])
                        can_unlock = skill_data['requires'] is None or skill_data['requires'] in self.unlocked_skills.get(path_key, [])
                        
                        found_skills.append({
                            'path_key': path_key,
                            'path_name': path_data['name'],
                            'path_emoji': path_data['emoji'],
                            'skill_key': skill_key,
                            'skill_data': skill_data,
                            'is_unlocked': is_unlocked,
                            'can_unlock': can_unlock
                        })
            
            if not found_skills:
                await interaction.followup.send(
                    f"❌ Keine Skills mit '{search_term}' gefunden.",
                    ephemeral=True
                )
                return
            
            # Create result embed
            embed = discord.Embed(
                title=f"🔍 Suchergebnisse: '{search_term}'",
                description=f"Gefunden: {len(found_skills)} Skill(s)\n**Verfügbare Skillpunkte: {self.skill_points}**",
                color=discord.Color.blue()
            )
            
            for skill in found_skills[:10]:  # Limit to 10 results
                status = "✅" if skill['is_unlocked'] else ("🔓" if skill['can_unlock'] and self.skill_points >= skill['skill_data']['cost'] else "🔒")
                
                skill_text = f"{status} **{skill['skill_data']['name']}** ({skill['skill_data']['type']})\n"
                skill_text += f"📝 {skill['skill_data']['description']}\n"
                skill_text += f"💎 Kosten: {skill['skill_data']['cost']} Skillpunkte\n"
                skill_text += f"🌳 Pfad: {skill['path_emoji']} {skill['path_name']}"
                
                if skill['skill_data']['requires']:
                    req_skill = rpg_system.SKILL_TREE[skill['path_key']]['skills'][skill['skill_data']['requires']]
                    skill_text += f"\n🔗 Benötigt: {req_skill['name']}"
                
                embed.add_field(name="\u200b", value=skill_text, inline=False)
            
            if len(found_skills) > 10:
                embed.set_footer(text=f"Zeige 10 von {len(found_skills)} Ergebnissen")
            
            # Create view with unlock options
            view = SkillSearchResultView(self.user_id, found_skills, self.skill_points, self.unlocked_skills)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error searching skills: {e}", exc_info=True)
            await interaction.followup.send("❌ Fehler bei der Suche.", ephemeral=True)


class SkillSearchResultView(discord.ui.View):
    """View for skill search results with unlock options."""
    
    def __init__(self, user_id: int, found_skills: list, skill_points: int, unlocked_skills: dict):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.found_skills = found_skills
        self.skill_points = skill_points
        
        # Add select menu for unlockable skills from search results
        skill_options = []
        for skill in found_skills[:25]:  # Discord limit
            if not skill['is_unlocked'] and skill['can_unlock'] and skill_points >= skill['skill_data']['cost']:
                skill_options.append(discord.SelectOption(
                    label=skill['skill_data']['name'],
                    description=f"{skill['path_name']} - {skill['skill_data']['cost']} SP",
                    value=f"{skill['path_key']}:{skill['skill_key']}",
                    emoji=skill['path_emoji']
                ))
        
        if skill_options:
            skill_select = discord.ui.Select(
                placeholder="Skill freischalten...",
                options=skill_options,
                row=0
            )
            skill_select.callback = self.unlock_skill
            self.add_item(skill_select)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Dies ist nicht deine Suche!", ephemeral=True)
            return False
        return True
    
    async def unlock_skill(self, interaction: discord.Interaction):
        """Unlock a skill from search results."""
        await interaction.response.defer()
        
        try:
            path_key, skill_key = interaction.data['values'][0].split(':')
            success, message = await rpg_system.unlock_skill(db_helpers, self.user_id, path_key, skill_key)
            
            if success:
                await interaction.followup.send(f"✅ {message}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ {message}", ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error unlocking skill from search: {e}", exc_info=True)
            await interaction.followup.send("❌ Fehler beim Freischalten.", ephemeral=True)


class RPGSkillTreeView(discord.ui.View):
    """View for skill tree management."""
    
    def __init__(self, user_id: int, skill_points: int, unlocked_skills: dict):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.skill_points = skill_points
        self.unlocked_skills = unlocked_skills
        
        # Add select menu for skill paths
        path_options = []
        for path_key, path_data in rpg_system.SKILL_TREE.items():
            unlocked_count = len(unlocked_skills.get(path_key, []))
            total_count = len(path_data['skills'])
            
            path_options.append(discord.SelectOption(
                label=path_data['name'],
                description=f"{path_data['description'][:50]}... ({unlocked_count}/{total_count})",
                value=path_key,
                emoji=path_data['emoji']
            ))
        
        if path_options:
            path_select = discord.ui.Select(
                placeholder="Wähle einen Pfad...",
                options=path_options,
                row=0
            )
            path_select.callback = self.view_path
            self.add_item(path_select)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Dies ist nicht dein Skill-Baum!", ephemeral=True)
            return False
        return True
    
    async def view_path(self, interaction: discord.Interaction):
        """View skills in a specific path."""
        await interaction.response.defer()
        
        try:
            path_key = interaction.data['values'][0]
            path_data = rpg_system.SKILL_TREE[path_key]
            
            embed = discord.Embed(
                title=f"{path_data['emoji']} {path_data['name']}",
                description=f"{path_data['description']}\n\n**Skillpunkte verfügbar: {self.skill_points}**",
                color=discord.Color.purple()
            )
            
            # Show all skills in path
            unlocked_in_path = self.unlocked_skills.get(path_key, [])
            
            for skill_key, skill_data in path_data['skills'].items():
                is_unlocked = skill_key in unlocked_in_path
                can_unlock = skill_data['requires'] is None or skill_data['requires'] in unlocked_in_path
                
                status = "✅" if is_unlocked else ("🔓" if can_unlock and self.skill_points >= skill_data['cost'] else "🔒")
                
                skill_text = f"{status} **{skill_data['name']}** ({skill_data['type']})\n"
                skill_text += f"📝 {skill_data['description']}\n"
                skill_text += f"💎 Kosten: {skill_data['cost']} Skillpunkte"
                
                if skill_data['requires']:
                    required_skill = path_data['skills'][skill_data['requires']]
                    skill_text += f"\n🔗 Benötigt: {required_skill['name']}"
                
                embed.add_field(name="\u200b", value=skill_text, inline=False)
            
            embed.set_footer(text="Wähle einen Skill zum Freischalten!")
            
            # Create view for unlocking skills
            view = RPGSkillUnlockView(self.user_id, path_key, self.skill_points, unlocked_in_path)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error viewing skill path: {e}", exc_info=True)
            await interaction.followup.send("❌ Fehler beim Anzeigen des Pfads.", ephemeral=True)
    
    @discord.ui.button(label="🔙 Zurück", style=discord.ButtonStyle.secondary, row=1)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Return to main RPG menu."""
        await interaction.response.defer()
        
        try:
            # Get fresh player data
            player = await rpg_system.get_player_profile(db_helpers, self.user_id)
            if not player:
                await interaction.followup.send("❌ Fehler beim Laden deines Profils.", ephemeral=True)
                return
            
            # Create main RPG menu embed
            embed = discord.Embed(
                title=f"⚔️ RPG Profil - {interaction.user.display_name}",
                description=f"**Level {player['level']}** | Welt: {rpg_system.WORLDS[player['world']]['name']}",
                color=discord.Color.purple()
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            
            # Stats
            embed.add_field(
                name="📊 Attribute",
                value=f"❤️ HP: {player['health']}/{player['max_health']}\n"
                      f"⚔️ Stärke: {player['strength']}\n"
                      f"🎯 Geschick: {player['dexterity']}\n"
                      f"🛡️ Verteidigung: {player['defense']}\n"
                      f"⚡ Geschwindigkeit: {player['speed']}",
                inline=True
            )
            
            # Progression
            xp_needed = rpg_system.calculate_xp_for_level(player['level'] + 1)
            xp_progress = player['xp']
            progress_pct = (xp_progress / xp_needed) * 100 if xp_needed > 0 else 100
            
            embed.add_field(
                name="📈 Fortschritt",
                value=f"XP: {xp_progress}/{xp_needed}\n"
                      f"Fortschritt: {progress_pct:.1f}%\n"
                      f"💎 Skillpunkte: {player['skill_points']}\n"
                      f"💰 Gold: {player['gold']}",
                inline=True
            )
            
            embed.add_field(
                name="🎮 Verfügbare Aktionen",
                value="Wähle eine Aktion aus den Buttons unten!",
                inline=False
            )
            
            embed.set_footer(text="Nutze die Buttons um dein Abenteuer zu beginnen!")
            
            # Return to main menu view
            view = RPGMenuView(self.user_id, player)
            await interaction.edit_original_response(embed=embed, view=view)
            
        except Exception as e:
            logger.error(f"Error returning to RPG menu: {e}", exc_info=True)
            await interaction.followup.send("❌ Fehler beim Zurückkehren.", ephemeral=True)


class RPGSkillUnlockView(discord.ui.View):
    """View for unlocking specific skills."""
    
    def __init__(self, user_id: int, path_key: str, skill_points: int, unlocked_in_path: list):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.path_key = path_key
        self.skill_points = skill_points
        
        # Add select menu for unlockable skills
        path_data = rpg_system.SKILL_TREE[path_key]
        skill_options = []
        
        for skill_key, skill_data in path_data['skills'].items():
            is_unlocked = skill_key in unlocked_in_path
            can_unlock = skill_data['requires'] is None or skill_data['requires'] in unlocked_in_path
            
            # Only show skills that can be unlocked
            if not is_unlocked and can_unlock and skill_points >= skill_data['cost']:
                skill_options.append(discord.SelectOption(
                    label=skill_data['name'],
                    description=f"Kosten: {skill_data['cost']} SP - {skill_data['description'][:30]}...",
                    value=skill_key
                ))
        
        if skill_options:
            skill_select = discord.ui.Select(
                placeholder="Skill freischalten...",
                options=skill_options,
                row=0
            )
            skill_select.callback = self.unlock_skill
            self.add_item(skill_select)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Dies ist nicht dein Skill-Baum!", ephemeral=True)
            return False
        return True
    
    async def unlock_skill(self, interaction: discord.Interaction):
        """Unlock a skill."""
        await interaction.response.defer()
        
        try:
            skill_key = interaction.data['values'][0]
            success, message = await rpg_system.unlock_skill(db_helpers, self.user_id, self.path_key, skill_key)
            
            if success:
                await interaction.followup.send(f"✅ {message}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ {message}", ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error unlocking skill: {e}", exc_info=True)
            await interaction.followup.send("❌ Fehler beim Freischalten.", ephemeral=True)


# --- Leaderboard Helper Constants and Functions ---
MAX_LEADERBOARD_NAME_LENGTH = 18
MAX_WERWOLF_NAME_LENGTH = 16

def truncate_name(name: str, max_length: int) -> str:
    """Truncate a name if it exceeds max_length, adding ellipsis."""
    if len(name) > max_length:
        return name[:max_length - 3] + "..."
    return name


class LeaderboardPageView(discord.ui.View):
    """View for paginated leaderboard with different categories."""
    
    def __init__(self, config: dict):
        super().__init__(timeout=180)
        self.config = config
    
    @discord.ui.button(label="💰 Money Leaderboard", style=discord.ButtonStyle.success)
    async def money_leaderboard_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        embed = await self._create_money_leaderboard_embed()
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="🐺 Werwolf Leaderboard", style=discord.ButtonStyle.secondary)
    async def werwolf_leaderboard_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        embed = await self._create_werwolf_leaderboard_embed()
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="🎮 Games Played", style=discord.ButtonStyle.primary)
    async def games_leaderboard_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        embed = await self._create_games_leaderboard_embed()
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def _create_money_leaderboard_embed(self):
        """Create embed with money leaderboard."""
        leaderboard, error = await db_helpers.get_money_leaderboard()
        
        if error:
            return discord.Embed(
                title="Fehler",
                description=f"Fehler beim Laden: {error}",
                color=discord.Color.red()
            )
        
        if not leaderboard:
            return discord.Embed(
                title="💰 Money Leaderboard",
                description="Noch niemand hat Geld gesammelt. Zeit zum Verdienen!",
                color=get_embed_color(self.config)
            )
        
        currency = self.config.get('modules', {}).get('economy', {}).get('currency_symbol', '💵')
        
        embed = discord.Embed(
            title="💰 Money Leaderboard",
            description="*Top Spieler nach Kontostand*",
            color=get_embed_color(self.config)
        )
        
        # Create compact leaderboard with medal emojis
        leaderboard_text = ""
        for i, player in enumerate(leaderboard):
            rank = i + 1
            
            # Medal emojis for top 3
            if rank == 1:
                rank_display = "🥇"
            elif rank == 2:
                rank_display = "🥈"
            elif rank == 3:
                rank_display = "🥉"
            else:
                rank_display = f"`{rank:>2}.`"
            
            balance = player['balance']
            name = truncate_name(player['display_name'], MAX_LEADERBOARD_NAME_LENGTH)
            
            leaderboard_text += f"{rank_display} **{name}** • `{balance:,}` {currency}\n"
        
        embed.add_field(name="🏦 Rankings", value=leaderboard_text, inline=False)
        embed.set_footer(text="💡 Verdiene Coins durch Daily, Quests und Mini-Games!")
        
        return embed
    
    async def _create_games_leaderboard_embed(self):
        """Create embed with games played leaderboard."""
        leaderboard, error = await db_helpers.get_games_leaderboard()
        
        if error:
            return discord.Embed(
                title="Fehler",
                description=f"Fehler beim Laden: {error}",
                color=discord.Color.red()
            )
        
        if not leaderboard:
            return discord.Embed(
                title="🎮 Games Played Leaderboard",
                description="Noch niemand hat Spiele gespielt!",
                color=get_embed_color(self.config)
            )
        
        embed = discord.Embed(
            title="🎮 Games Played Leaderboard",
            description="*Top Spieler nach Gesamtspielen*",
            color=get_embed_color(self.config)
        )
        
        # Create compact leaderboard with medal emojis
        leaderboard_text = ""
        for i, player in enumerate(leaderboard):
            rank = i + 1
            
            # Medal emojis for top 3
            if rank == 1:
                rank_display = "🥇"
            elif rank == 2:
                rank_display = "🥈"
            elif rank == 3:
                rank_display = "🥉"
            else:
                rank_display = f"`{rank:>2}.`"
            
            total_games = player['total_games']
            wins = player['wins']
            losses = player['losses']
            win_rate = (wins / total_games * 100) if total_games > 0 else 0
            name = truncate_name(player['display_name'], MAX_LEADERBOARD_NAME_LENGTH)
            
            leaderboard_text += f"{rank_display} **{name}** • `{total_games}` Spiele • `{win_rate:.0f}%` WR\n"
        
        embed.add_field(name="🎯 Rankings", value=leaderboard_text, inline=False)
        embed.set_footer(text="WR = Win Rate • Spiele mehr um aufzusteigen!")
        
        return embed
    
    async def _create_werwolf_leaderboard_embed(self):
        """Create embed with Werwolf leaderboard."""
        leaderboard, error = await db_helpers.get_leaderboard()
        
        if error:
            return discord.Embed(
                title="Fehler",
                description=f"Fehler beim Laden: {error}",
                color=discord.Color.red()
            )
        
        if not leaderboard:
            return discord.Embed(
                title="🐺 Werwolf Leaderboard",
                description="Es gibt noch keine Statistiken. Spielt erst mal eine Runde!",
                color=get_embed_color(self.config)
            )
        
        embed = discord.Embed(
            title="🐺 Werwolf Leaderboard",
            description="*Top Werwolf-Spieler nach Siegen*",
            color=get_embed_color(self.config)
        )
        
        # Create compact leaderboard with medal emojis
        leaderboard_text = ""
        for i, player in enumerate(leaderboard):
            rank = i + 1
            
            # Medal emojis for top 3
            if rank == 1:
                rank_display = "🥇"
            elif rank == 2:
                rank_display = "🥈"
            elif rank == 3:
                rank_display = "🥉"
            else:
                rank_display = f"`{rank:>2}.`"
            
            wins = player['wins']
            losses = player['losses']
            total_games = wins + losses
            win_rate = (wins / total_games * 100) if total_games > 0 else 0
            name = truncate_name(player['display_name'], MAX_WERWOLF_NAME_LENGTH)
            
            leaderboard_text += f"{rank_display} **{name}** • `{wins}W-{losses}L` • `{win_rate:.0f}%`\n"
        
        embed.add_field(name="🎯 Rankings", value=leaderboard_text, inline=False)
        embed.set_footer(text="W/L = Win/Loss Ratio • Werde Champion!")
        
        return embed


@tree.command(name="leaderboard", description="Zeigt das globale Level-Leaderboard an.")
async def leaderboard(interaction: discord.Interaction):
    """Displays the global level leaderboard with pagination for different stats."""
    await interaction.response.defer()

    leaderboard_data, error = await db_helpers.get_level_leaderboard()

    if error:
        await interaction.followup.send(error, ephemeral=True)
        return

    if not leaderboard_data:
        await interaction.followup.send("Noch niemand hat XP gesammelt. Schreibt ein paar Nachrichten!", ephemeral=True)
        return

    # Create a more compact and visually pleasing embed
    embed = discord.Embed(
        title="🏆 Globales Leaderboard",
        description="*Die aktivsten Server-Mitglieder*",
        color=get_embed_color(config)
    )
    
    # Create compact leaderboard with medal emojis for top 3
    leaderboard_text = ""
    for i, player in enumerate(leaderboard_data):
        rank = i + 1
        
        # Medal emojis for top 3
        if rank == 1:
            rank_display = "🥇"
        elif rank == 2:
            rank_display = "🥈"
        elif rank == 3:
            rank_display = "🥉"
        else:
            rank_display = f"`{rank:>2}.`"
        
        # Format level and XP compactly
        level = player['level']
        xp = player['xp']
        name = truncate_name(player['display_name'], MAX_LEADERBOARD_NAME_LENGTH)
        
        leaderboard_text += f"{rank_display} **{name}** • Lvl `{level}` • `{xp:,}` XP\n"

    embed.add_field(name="📊 Level Rankings", value=leaderboard_text, inline=False)
    
    # Add footer with helpful info
    embed.set_footer(text="💡 Nutze die Buttons unten für weitere Leaderboards")
    
    # Add view for switching to other leaderboards
    view = LeaderboardPageView(config)
    await interaction.followup.send(embed=embed, view=view)

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




# --- Wrapped Registration View for Interactive Registration ---
class WrappedRegistrationView(discord.ui.View):
    """Interactive view for Wrapped registration with toggle functionality."""
    
    def __init__(self, user: discord.User, is_registered: bool):
        super().__init__(timeout=300)
        self.user = user
        self.is_registered = is_registered
        self._update_button()
    
    def _update_button(self):
        """Update the button based on registration status."""
        if self.is_registered:
            self.toggle_button.label = "🔕 Abmelden"
            self.toggle_button.style = discord.ButtonStyle.danger
            self.toggle_button.emoji = None
        else:
            self.toggle_button.label = "🔔 Anmelden"
            self.toggle_button.style = discord.ButtonStyle.success
            self.toggle_button.emoji = None
    
    def _create_embed(self):
        """Create the status embed based on current registration state."""
        if self.is_registered:
            embed = discord.Embed(
                title="📊 Dein Wrapped Status",
                description="✅ Du bist **registriert**!\n\nDu erhältst jeden Monat deine persönliche Zusammenfassung.",
                color=discord.Color.green()
            )
            embed.add_field(
                name="📅 Nächste Wrapped",
                value="Wird in der 2. Woche des nächsten Monats versendet",
                inline=False
            )
            embed.add_field(
                name="💡 Tipp",
                value="Du kannst dich auch über das Wrapped-Event (Interessiert) an-/abmelden!",
                inline=False
            )
            embed.set_footer(text="Klicke den Button unten um dich abzumelden")
        else:
            embed = discord.Embed(
                title="📊 Dein Wrapped Status",
                description="❌ Du bist **nicht registriert**.\n\nMelde dich an um jeden Monat deine persönliche Zusammenfassung zu erhalten!",
                color=discord.Color.red()
            )
            embed.add_field(
                name="🎁 Was bekommst du?",
                value="```\n"
                      "📊 Nachrichten & Emoji-Stats\n"
                      "🎤 Voice-Chat Statistiken\n"
                      "🎵 Spotify Rückblick\n"
                      "👥 Server-Bestie\n"
                      "🎮 Gaming & Aktivitäten\n"
                      "📋 Quest & Gambling Stats\n"
                      "✨ Personalisierte AI-Analyse\n"
                      "```",
                inline=False
            )
            embed.add_field(
                name="💡 Tipp",
                value="Du kannst dich auch über das Wrapped-Event (Interessiert) anmelden!",
                inline=False
            )
            embed.set_footer(text="Klicke den Button unten um dich anzumelden")
        
        embed.set_thumbnail(url=self.user.display_avatar.url)
        return embed
    
    @discord.ui.button(label="🔔 Anmelden", style=discord.ButtonStyle.success)
    async def toggle_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Toggle registration status."""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("Das ist nicht dein Menü!", ephemeral=True)
            return
        
        if self.is_registered:
            # Unregister
            success = await db_helpers.unregister_from_wrapped(self.user.id)
            if success:
                self.is_registered = False
                self._update_button()
                await interaction.response.edit_message(embed=self._create_embed(), view=self)
            else:
                await interaction.response.send_message("❌ Fehler beim Abmelden.", ephemeral=True)
        else:
            # Register
            success = await db_helpers.register_for_wrapped(self.user.id, self.user.display_name)
            if success:
                self.is_registered = True
                self._update_button()
                await interaction.response.edit_message(embed=self._create_embed(), view=self)
            else:
                await interaction.response.send_message("❌ Fehler beim Anmelden.", ephemeral=True)


# --- NEW: Wrapped Registration Commands ---

@tree.command(name="wrapped", description="Zeige deinen Wrapped-Status an und verwalte deine Registrierung.")
async def wrapped_command(interaction: discord.Interaction):
    """Shows Wrapped status with interactive registration toggle."""
    await interaction.response.defer(ephemeral=True)
    
    is_registered = await db_helpers.is_registered_for_wrapped(interaction.user.id)
    view = WrappedRegistrationView(interaction.user, is_registered)
    
    await interaction.followup.send(embed=view._create_embed(), view=view, ephemeral=True)

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
    embed.add_field(name="Automatischer Start", value="Das Spiel startet in **60 Sekunden**.")
    embed.add_field(name="Spieler (1)", value=author.display_name, inline=False)
    embed.set_footer(text="Wer nicht beitritt, ist ein Werwolf! Nur der Starter kann das Spiel vorzeitig beginnen.")
    
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

    # --- NEW: Role Selection UI ---
    # Get available roles for the game starter
    from modules.werwolf import get_available_werwolf_roles, WerwolfRoleSelectionView
    
    available_roles = await get_available_werwolf_roles(author.id, db_helpers)
    
    # Only show role selection if user has unlocked special roles
    if available_roles:
        # Create role selection embed
        embed = discord.Embed(
            title="🐺 Werwolf Rollen-Auswahl",
            description="Wähle, welche Rollen in diesem Spiel verfügbar sein sollen.\n"
                       "Grüne Buttons = Ausgewählt | Graue Buttons = Nicht ausgewählt",
            color=discord.Color.blue()
        )
        
        # List available roles
        role_list = "\n".join([f"✅ {role}" for role in available_roles])
        embed.add_field(
            name=f"Verfügbare Rollen ({len(available_roles)})",
            value=role_list,
            inline=False
        )
        
        embed.set_footer(text="Werwölfe und Dorfbewohner sind immer dabei! • Zeitlimit: 2 Minuten")
        
        # Create and send the role selection view
        role_view = WerwolfRoleSelectionView(author.id, available_roles, game)
        role_message = await game.game_channel.send(embed=embed, view=role_view)
        role_view.message = role_message
        
        # Wait for user to make selection or timeout
        await role_view.wait()
        
        # Check if cancelled
        if role_view.selected_roles is None:
            await game.game_channel.send("Spielstart wurde abgebrochen.")
            await game.end_game(config)
            del active_werwolf_games[game_text_channel.id]
            return
        
        # Use the selected roles
        selected_roles = role_view.selected_roles
    else:
        # No special roles unlocked - inform user
        info_embed = discord.Embed(
            title="ℹ️ Keine speziellen Rollen",
            description="Du hast noch keine speziellen Rollen freigeschaltet!\n"
                       "Das Spiel wird nur mit **Werwölfen** und **Dorfbewohnern** gespielt.",
            color=discord.Color.gold()
        )
        info_embed.add_field(
            name="Rollen freischalten",
            value="Besuche den Shop mit `/shop`, um spezielle Rollen zu kaufen!",
            inline=False
        )
        await game.game_channel.send(embed=info_embed)
        # Set selected_roles to empty set (no special roles)
        selected_roles = set()

    # Automatically start the game
    # Bot filling logic is now handled inside start_game
    try:
        error_message = await game.start_game(config, GEMINI_API_KEY, OPENAI_API_KEY, db_helpers, ziel_spieler, selected_roles)
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
        name="💘 Amor",
        value="**Team:** Dorfbewohner\n**Fähigkeit:** Wählt in der ersten Nacht zwei Spieler, die sich ineinander verlieben. Stirbt einer, stirbt auch der andere.\n**Aktionen:** `love <name1> <name2>` per DM an den Bot\n**Verfügbar:** Ab 8 Spielern",
        inline=False
    )
    
    roles_embed.add_field(
        name="⚪ Der Weiße",
        value="**Team:** Dorfbewohner\n**Fähigkeit:** Kann einen Werwolf-Angriff überleben. ACHTUNG: Wird er gelyncht, verlieren alle Dorfbewohner ihre Spezialfähigkeiten!\n**Aktionen:** Passiv\n**Verfügbar:** Ab 10 Spielern",
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
tree.add_command(AdminAIGroup(name="adminai"))

# --- NEW: Help Command with Pagination ---
class HelpView(discord.ui.View):
    """Paginated help menu showing categorized commands."""
    
    def __init__(self, user: discord.User, is_admin: bool):
        super().__init__(timeout=180)
        self.user = user
        self.is_admin = is_admin
        self.current_page = 0
        
        # Define command categories
        self.categories = {
            "🎮 Games": [
                ("blackjack", "Spiele Blackjack mit Einsatz"),
                ("roulette", "Spiele Roulette - setze auf Zahlen oder Farben"),
                ("mines", "Spiele Mines - vermeide die Bomben"),
                ("tower", "Spiele Tower of Treasure - klettere den Turm hinauf"),
                ("rr", "Spiele Russian Roulette - hohes Risiko, hohe Belohnung"),
                ("detective", "Löse einen KI-generierten Mordfall"),
                ("trolly", "Stelle dich einem moralischen Dilemma"),
                ("wordfind", "Errate das tägliche Wort mit Nähehinweisen"),
            ],
            "💰 Economy": [
                ("daily", "Hole deine tägliche Belohnung ab"),
                ("shop", "Öffne den Shop - kaufe Farbrollen und mehr"),
                ("transactions", "Zeige deine letzten Transaktionen an"),
                ("quests", "Zeige deine täglichen Quests und Fortschritt"),
                ("stock", "Öffne den Aktienmarkt - kaufe und verkaufe Aktien"),
            ],
            "📊 Profile & Stats": [
                ("profile", "Zeige dein Profil oder das eines anderen Benutzers"),
                ("leaderboard", "Zeige globale Leaderboards (Level, Money, Werwolf, Games)"),
                ("summary", "Zeige Sulfurs Meinung über einen Benutzer"),
                ("spotify", "Zeige deine Spotify-Statistiken"),
            ],
            "🎭 Werwolf": [
                ("ww start", "Starte ein neues Werwolf-Spiel"),
                ("ww rules", "Zeige die Werwolf-Spielregeln und Rollen"),
            ],
            "🎤 Voice": [
                ("voice setup", "Richte 'Join to Create' Voice-Kanäle ein"),
                ("voice config name", "Benenne deinen Voice-Channel um"),
                ("voice config limit", "Setze ein Benutzerlimit für deinen Channel"),
                ("voice config lock", "Mache deinen Channel privat"),
                ("voice config unlock", "Mache deinen Channel wieder öffentlich"),
                ("voice config permit", "Erlaube einem Benutzer Zugriff auf deinen Channel"),
                ("voice config unpermit", "Entferne Zugriff für einen Benutzer"),
            ],
            "⚙️ Other": [
                ("news", "Zeige die neuesten Server-Nachrichten"),
                ("privacy", "Verwalte deine Datenschutz-Einstellungen"),
                ("wrapped", "📊 Zeige deinen Wrapped-Status und verwalte deine Registrierung"),
            ],
        }
        
        # Add admin commands if user is admin
        if self.is_admin:
            self.categories["🔧 Admin"] = [
                ("admin view_wrapped", "Zeige eine Wrapped-Vorschau für einen Benutzer"),
                ("admin reload_config", "Lade die Konfiguration neu"),
                ("admin status", "Zeige den Bot-Status"),
                ("admin dashboard", "Zeige das Admin-Dashboard"),
                ("admin emojis", "Verwalte Server-Emojis"),
            ]
            self.categories["🤖 Admin AI"] = [
                ("adminai mind", "Zeige den mentalen Zustand des Bots"),
                ("adminai context", "Zeige den Konversationskontext"),
                ("adminai test_ai", "Teste die KI-Antwort"),
                ("adminai observations", "Zeige Bot-Beobachtungen"),
                ("adminai autonomous_status", "Zeige autonomen Status"),
            ]
        
        self.pages = list(self.categories.keys())
        self.update_buttons()
    
    def create_embed(self):
        """Create embed for current page."""
        category_name = self.pages[self.current_page]
        commands = self.categories[category_name]
        
        embed = discord.Embed(
            title=f"📖 Sulfur Bot - Help",
            description=f"**{category_name}**\n\nSeite {self.current_page + 1}/{len(self.pages)}",
            color=discord.Color.blue()
        )
        
        for cmd_name, cmd_desc in commands:
            embed.add_field(
                name=f"/{cmd_name}",
                value=cmd_desc,
                inline=False
            )
        
        embed.set_footer(text="Verwende die Buttons unten, um durch die Kategorien zu navigieren.")
        return embed
    
    def update_buttons(self):
        """Update button states based on current page."""
        self.previous_button.disabled = (self.current_page == 0)
        self.next_button.disabled = (self.current_page == len(self.pages) - 1)
    
    @discord.ui.button(label="◀️ Zurück", style=discord.ButtonStyle.gray)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to previous page."""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("Nur der Benutzer, der den Help-Befehl ausgeführt hat, kann die Seiten wechseln.", ephemeral=True)
            return
        
        self.current_page = max(0, self.current_page - 1)
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)
    
    @discord.ui.button(label="Weiter ▶️", style=discord.ButtonStyle.gray)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to next page."""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("Nur der Benutzer, der den Help-Befehl ausgeführt hat, kann die Seiten wechseln.", ephemeral=True)
            return
        
        self.current_page = min(len(self.pages) - 1, self.current_page + 1)
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)
    
    @discord.ui.button(label="❌ Schließen", style=discord.ButtonStyle.red)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Close the help menu."""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("Nur der Benutzer, der den Help-Befehl ausgeführt hat, kann das Menü schließen.", ephemeral=True)
            return
        
        await interaction.response.edit_message(content="Help-Menü geschlossen.", embed=None, view=None)
        self.stop()

@tree.command(name="help", description="Zeigt alle verfügbaren Bot-Befehle an.")
async def help_command(interaction: discord.Interaction):
    """Display paginated help menu with all commands."""
    # Check if user is admin
    is_admin = interaction.user.guild_permissions.administrator or interaction.user.id == int(os.getenv("OWNER_ID", 0))
    
    view = HelpView(interaction.user, is_admin)
    embed = view.create_embed()
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# --- NEW: Shop Commands ---
from modules import shop as shop_module

@tree.command(name="shop", description="Öffne den Shop.")
async def shop_main(interaction: discord.Interaction):
    """Unified shop view with interactive purchase."""
    await interaction.response.defer(ephemeral=True)
    
    try:
        user_id = interaction.user.id
        
        # Get user's theme for theming
        user_theme = await themes.get_user_theme(db_helpers, user_id)
        
        # Show shop with interactive buttons
        view = ShopBuyView(interaction.user, config)
        embed = discord.Embed(
            title="🛒 Shop",
            description="Willkommen im Shop! Wähle eine Kategorie aus:",
            color=themes.get_theme_color(user_theme, 'primary') if user_theme else discord.Color.blue()
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
            'casino': {
                'name': '🎰 Casino',
                'desc': 'Spiele Blackjack, Roulette, Mines und Russian Roulette!'
            },
            'detective': {
                'name': '🔍 Detective Game',
                'desc': 'Löse spannende Kriminalfälle!'
            },
            'trolly': {
                'name': '🚃 Trolly Problem',
                'desc': 'Stelle dich moralischen Dilemmata!'
            },
            'unlimited_word_find': {
                'name': '📝 Unlimited Word Find',
                'desc': 'Spiele Word Find ohne tägliches Limit!'
            },
            'unlimited_wordle': {
                'name': '🎮 Unlimited Wordle',
                'desc': 'Spiele Wordle ohne tägliches Limit!'
            },
            'rpg_access': {
                'name': '⚔️ RPG System Access',
                'desc': 'Zugriff auf das vollständige RPG-System mit Abenteuern!'
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
    
    @discord.ui.button(label="🎨 Themes", style=discord.ButtonStyle.primary, row=1)
    async def themes_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show theme options."""
        await interaction.response.defer()
        
        # Get user's owned and equipped themes
        owned_themes = await themes.get_user_owned_themes(db_helpers, self.member.id)
        equipped_theme = await themes.get_user_theme(db_helpers, self.member.id)
        
        view = ThemeSelectView(self.member, owned_themes, equipped_theme)
        embed = discord.Embed(
            title="🎨 Themes",
            description="Passe das Aussehen von Spielen und Befehlen an!\n\n"
                       "Themes ändern Farben, Emojis und das gesamte Erscheinungsbild.",
            color=discord.Color.purple()
        )
        
        currency = self.config['modules']['economy']['currency_symbol']
        
        # Show all available themes
        for theme_id, theme_data in themes.THEMES.items():
            owned = theme_id in owned_themes
            equipped = theme_id == equipped_theme
            status = "✅ Ausgerüstet" if equipped else ("✓ Besessen" if owned else f"{theme_data['price']} {currency}")
            
            embed.add_field(
                name=f"{theme_data['emoji']} {theme_data['name']} - {status}",
                value=theme_data['description'],
                inline=False
            )
        
        if equipped_theme:
            theme_name = themes.THEMES[equipped_theme]['name']
            embed.set_footer(text=f"Aktuell ausgerüstet: {theme_name}")
        else:
            embed.set_footer(text="Kein Theme ausgerüstet (Standard-Ansicht)")
        
        await interaction.edit_original_response(embed=embed, view=view)
    
    @discord.ui.button(label="🐺 Werwolf Rollen", style=discord.ButtonStyle.red, row=1)
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
            },
            'amor': {
                'name': '💘 Amor',
                'desc': 'Verliebe zwei Spieler - sie gewinnen oder verlieren zusammen'
            },
            'der_weisse': {
                'name': '⚪ Der Weiße',
                'desc': 'Überlebe einen Werwolf-Angriff'
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
    
    @discord.ui.button(label="📦 Bundles", style=discord.ButtonStyle.success, row=2)
    async def bundles_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show bundle options."""
        await interaction.response.defer()
        
        view = BundleSelectView(self.member, self.config)
        embed = discord.Embed(
            title="📦 Bundles - Spare Geld!",
            description="Kaufe mehrere Features zusammen und spare!",
            color=discord.Color.gold()
        )
        
        currency = self.config['modules']['economy']['currency_symbol']
        bundles = self.config['modules']['economy']['shop']['bundles']
        
        for bundle_id, bundle_data in bundles.items():
            bundle_name = bundle_data['name']
            bundle_desc = bundle_data['description']
            bundle_price = bundle_data['price']
            bundle_discount = bundle_data.get('discount', 0)
            
            # Calculate original price
            original_price = bundle_price + bundle_discount
            
            embed.add_field(
                name=f"{bundle_name} - {bundle_price} {currency}",
                value=f"{bundle_desc}\n"
                      f"~~{original_price} {currency}~~ → **{bundle_price} {currency}**\n"
                      f"💰 Spare {bundle_discount} {currency}!",
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
            'casino': {
                'name': 'Casino',
                'description': 'Spiele Blackjack, Roulette & mehr'
            },
            'detective': {
                'name': 'Detective Game',
                'description': 'Löse spannende Kriminalfälle'
            },
            'trolly': {
                'name': 'Trolly Problem',
                'description': 'Moralische Dilemmata'
            },
            'unlimited_word_find': {
                'name': '📝 Unlimited Word Find',
                'description': 'Unbegrenztes Word Find Spiel'
            },
            'unlimited_wordle': {
                'name': '🎯 Unlimited Wordle',
                'description': 'Unbegrenztes Wordle Spiel'
            },
            'rpg_access': {
                'name': '⚔️ RPG System Access',
                'description': 'Zugriff auf das vollständige RPG-System mit Abenteuern, Kämpfen und Items'
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


class ThemeSelectView(discord.ui.View):
    """View for selecting themes to purchase or equip."""
    
    def __init__(self, member: discord.Member, owned_themes: list, equipped_theme: str = None):
        super().__init__(timeout=180)
        self.member = member
        self.owned_themes = owned_themes
        self.equipped_theme = equipped_theme
        
        # Create select menu for themes
        options = []
        for theme_id, theme_data in themes.THEMES.items():
            owned = theme_id in owned_themes
            equipped = theme_id == equipped_theme
            
            if equipped:
                status = "✅ Ausgerüstet"
            elif owned:
                status = "✓ Besessen"
            else:
                status = f"{theme_data['price']} 🪙"
            
            options.append(
                discord.SelectOption(
                    label=f"{theme_data['name']} - {status}",
                    value=theme_id,
                    description=theme_data['description'][:100],
                    emoji=theme_data['emoji']
                )
            )
        
        # Add option to unequip theme
        if equipped_theme:
            options.append(
                discord.SelectOption(
                    label="Standard (Theme entfernen)",
                    value="unequip",
                    description="Zurück zur Standard-Ansicht",
                    emoji="❌"
                )
            )
        
        select = discord.ui.Select(placeholder="Wähle ein Theme...", options=options)
        select.callback = self.on_theme_select
        self.add_item(select)
    
    @discord.ui.button(label="🔍 Vorschau", style=discord.ButtonStyle.secondary, row=1)
    async def preview_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show preview of all themes."""
        await interaction.response.defer(ephemeral=True)
        
        # Create preview embed
        embed = discord.Embed(
            title="🎨 Theme Vorschau",
            description="Hier ist eine Vorschau aller verfügbaren Themes:",
            color=discord.Color.blue()
        )
        
        for theme_id, theme_data in themes.THEMES.items():
            owned = theme_id in self.owned_themes
            equipped = theme_id == self.equipped_theme
            currency = config['modules']['economy']['currency_symbol']
            
            if equipped:
                status = "✅ Ausgerüstet"
            elif owned:
                status = "✓ Besessen"
            else:
                status = f"💰 {theme_data['price']} {currency}"
            
            # Create a preview with theme colors and assets
            preview_text = (
                f"**{status}**\n"
                f"*{theme_data['description']}*\n\n"
                f"**Spiel-Assets:**\n"
                f"• Turm: {theme_data['game_assets']['tower_name']}\n"
                f"• Mines Sicher: {theme_data['game_assets']['mines_safe']}\n"
                f"• Mines Aufgedeckt: {theme_data['game_assets']['mines_revealed']}\n"
                f"• Mines Bombe: {theme_data['game_assets']['mines_bomb']}\n"
                f"• Roulette: {theme_data['game_assets']['roulette_wheel']}\n"
                f"• Profil: {theme_data['game_assets']['profile_accent']}"
            )
            
            embed.add_field(
                name=f"{theme_data['emoji']} {theme_data['name']}",
                value=preview_text,
                inline=False
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.member.id:
            await interaction.response.send_message("Du kannst diese Auswahl nicht bedienen.", ephemeral=True)
            return False
        return True
    
    async def on_theme_select(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        theme_id = interaction.data['values'][0]
        currency = config['modules']['economy']['currency_symbol']
        
        # Handle unequip
        if theme_id == "unequip":
            success, message = await themes.equip_theme(db_helpers, self.member.id, None)
            if success:
                embed = discord.Embed(
                    title="❌ Theme entfernt",
                    description="Du verwendest jetzt die Standard-Ansicht.",
                    color=discord.Color.blue()
                )
            else:
                embed = discord.Embed(
                    title="❌ Fehler",
                    description=message,
                    color=discord.Color.red()
                )
            await interaction.edit_original_response(embed=embed, view=None)
            return
        
        # Check if already owned
        if theme_id in self.owned_themes:
            # Equip the theme
            success, message = await themes.equip_theme(db_helpers, self.member.id, theme_id)
            if success:
                theme_data = themes.THEMES[theme_id]
                embed = discord.Embed(
                    title=f"{theme_data['emoji']} Theme ausgerüstet!",
                    description=f"Du verwendest jetzt das **{theme_data['name']}** Theme!",
                    color=themes.get_theme_color(theme_id, 'success')
                )
                embed.add_field(
                    name="Vorschau",
                    value=f"**Farben:** Angepasst an {theme_data['name']}\n"
                          f"**Turm:** {theme_data['game_assets']['tower_name']}\n"
                          f"**Mines:** {theme_data['game_assets']['mines_safe']} {theme_data['game_assets']['mines_revealed']} {theme_data['game_assets']['mines_bomb']}",
                    inline=False
                )
            else:
                embed = discord.Embed(
                    title="❌ Fehler",
                    description=message,
                    color=discord.Color.red()
                )
            await interaction.edit_original_response(embed=embed, view=None)
            return
        
        # Purchase theme
        theme_data = themes.THEMES[theme_id]
        price = theme_data['price']
        
        # Check balance
        balance = await db_helpers.get_balance(self.member.id)
        if balance < price:
            embed = discord.Embed(
                title="❌ Nicht genug Guthaben",
                description=f"Du hast {balance} {currency}, brauchst aber {price} {currency}.",
                color=discord.Color.red()
            )
            await interaction.edit_original_response(embed=embed, view=None)
            return
        
        # Purchase
        success, message = await themes.purchase_theme(db_helpers, self.member.id, theme_id)
        
        if success:
            # Deduct from balance
            stat_period = datetime.now(timezone.utc).strftime('%Y-%m')
            await db_helpers.add_balance(
                self.member.id,
                self.member.display_name,
                -price,
                config,
                stat_period
            )
            
            new_balance = await db_helpers.get_balance(self.member.id)
            
            # Log transaction
            await db_helpers.log_transaction(
                self.member.id,
                'shop_purchase',
                -price,
                new_balance,
                f"Purchased theme: {theme_data['name']}"
            )
            
            # Auto-equip after purchase
            await themes.equip_theme(db_helpers, self.member.id, theme_id)
            
            embed = discord.Embed(
                title=f"✅ {theme_data['emoji']} Theme gekauft!",
                description=f"Du hast das **{theme_data['name']}** Theme gekauft und ausgerüstet!",
                color=themes.get_theme_color(theme_id, 'success')
            )
            embed.add_field(
                name="Kosten",
                value=f"{price} {currency}",
                inline=True
            )
            embed.add_field(
                name="Neues Guthaben",
                value=f"{new_balance} {currency}",
                inline=True
            )
            embed.add_field(
                name="Vorschau",
                value=f"**Farben:** Angepasst an {theme_data['name']}\n"
                      f"**Turm:** {theme_data['game_assets']['tower_name']}\n"
                      f"**Mines:** {theme_data['game_assets']['mines_safe']} {theme_data['game_assets']['mines_revealed']} {theme_data['game_assets']['mines_bomb']}",
                inline=False
            )
        else:
            embed = discord.Embed(
                title="❌ Kauf fehlgeschlagen",
                description=message,
                color=discord.Color.red()
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


class BundleSelectView(discord.ui.View):
    """View for selecting bundles to purchase."""
    
    def __init__(self, member: discord.Member, config: dict):
        super().__init__(timeout=120)
        self.member = member
        self.config = config
        
        # Create select menu for bundles
        options = []
        bundles = config['modules']['economy']['shop']['bundles']
        currency = config['modules']['economy']['currency_symbol']
        
        for bundle_id, bundle_data in bundles.items():
            bundle_name = bundle_data['name']
            bundle_desc = bundle_data['description']
            bundle_price = bundle_data['price']
            bundle_discount = bundle_data.get('discount', 0)
            
            options.append(
                discord.SelectOption(
                    label=bundle_name,
                    value=bundle_id,
                    description=f"{bundle_price} {currency} - Spare {bundle_discount} {currency}!"[:100]
                )
            )
        
        select = discord.ui.Select(placeholder="Wähle ein Bundle...", options=options)
        select.callback = self.on_bundle_select
        self.add_item(select)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.member.id:
            await interaction.response.send_message("Du kannst diese Auswahl nicht bedienen.", ephemeral=True)
            return False
        return True
    
    async def on_bundle_select(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        bundle_id = interaction.data['values'][0]
        bundle_data = self.config['modules']['economy']['shop']['bundles'][bundle_id]
        bundle_name = bundle_data['name']
        bundle_price = bundle_data['price']
        bundle_features = bundle_data['features']
        currency = self.config['modules']['economy']['currency_symbol']
        
        try:
            # Check if user already owns any of the features
            owned_features = []
            for feature in bundle_features:
                if await db_helpers.has_feature_unlock(self.member.id, feature):
                    owned_features.append(feature)
            
            if owned_features:
                embed = discord.Embed(
                    title="❌ Bundle nicht verfügbar",
                    description=f"Du besitzt bereits einige Features aus diesem Bundle: {', '.join(owned_features)}",
                    color=discord.Color.red()
                )
                await interaction.edit_original_response(embed=embed, view=None)
                return
            
            # Check balance
            stat_period = datetime.now(timezone.utc).strftime('%Y-%m')
            balance = await db_helpers.get_balance(self.member.id)
            
            if balance < bundle_price:
                embed = discord.Embed(
                    title="❌ Kauf fehlgeschlagen",
                    description=f"Nicht genug Geld! Du benötigst {bundle_price} {currency}, hast aber nur {balance} {currency}.",
                    color=discord.Color.red()
                )
                await interaction.edit_original_response(embed=embed, view=None)
                return
            
            # Purchase all features in the bundle
            new_balance = await db_helpers.add_balance(self.member.id, self.member.display_name, -bundle_price, self.config, stat_period)
            await db_helpers.log_transaction(
                self.member.id,
                'shop_purchase',
                -bundle_price,
                new_balance,
                f"Purchased bundle: {bundle_name}"
            )
            
            # Grant all features
            for feature in bundle_features:
                await db_helpers.add_feature_unlock(self.member.id, feature)
            
            features_list = "\n".join([f"• {feature}" for feature in bundle_features])
            embed = discord.Embed(
                title="✅ Bundle gekauft!",
                description=f"Du hast das **{bundle_name}** Bundle erfolgreich gekauft!\n\n"
                           f"Freigeschaltete Features:\n{features_list}",
                color=discord.Color.green()
            )
            embed.add_field(
                name="💰 Neues Guthaben",
                value=f"{new_balance:.2f} {currency}",
                inline=False
            )
            
            await interaction.edit_original_response(embed=embed, view=None)
        except Exception as e:
            logger.error(f"Error purchasing bundle: {e}", exc_info=True)
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
        color_names_map = {
            'basic': colors.get('basic_color_names', []),
            'premium': colors.get('premium_color_names', []),
            'legendary': colors.get('legendary_color_names', [])
        }
        
        available_colors = color_map.get(tier, [])
        color_names = color_names_map.get(tier, [])
        
        options = []
        for idx, hex_color in enumerate(available_colors[:25], start=1):
            # Get color name if available, otherwise use hex
            color_name = color_names[idx-1] if idx-1 < len(color_names) else hex_color
            options.append(discord.SelectOption(
                label=f"{color_name}",
                description=hex_color,
                value=hex_color
            ))

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
        
        user_id = interaction.user.id
        
        # Get user's theme for theming
        user_theme = await themes.get_user_theme(db_helpers, user_id)
        
        success, amount, message = await grant_daily_reward(
            db_helpers,
            user_id,
            interaction.user.display_name,
            config
        )
        
        if success:
            embed = discord.Embed(
                title="🎁 Tägliche Belohnung!",
                description=message,
                color=themes.get_theme_color(user_theme, 'success') if user_theme else discord.Color.green()
            )
            new_balance = await db_helpers.get_balance(user_id)
            currency = config['modules']['economy']['currency_symbol']
            embed.add_field(name="Neues Guthaben", value=f"{new_balance} {currency}", inline=True)
        else:
            embed = discord.Embed(
                title="⏰ Bereits abgeholt",
                description=message,
                color=themes.get_theme_color(user_theme, 'warning') if user_theme else discord.Color.orange()
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
            # Extract values from dictionary (get_transaction_history returns dicts)
            trans_type = trans['transaction_type']
            amount = int(trans['amount'])
            balance_after = int(trans['balance_after'])
            description = trans['description']
            created_at = trans['created_at']
            
            # Get emoji based on transaction type
            type_emojis = {
                'stock_buy': '📉',
                'stock_sell': '📈',
                'daily_reward': '🎁',
                'quest_reward': '✅',
                'level_reward': '⬆️',
                'gambling': '🎰',
                'transfer': '💸',
                'purchase': '🛒',
                'shop_purchase': '🛒',
                'boost': '⚡',
                'role_purchase': '🎨'
            }
            emoji = type_emojis.get(trans_type, '💰')
            
            # Format amount with sign and color coding
            amount_str = f"+{amount}" if amount > 0 else str(amount)
            
            # Format timestamp
            timestamp = created_at.strftime("%d.%m.%Y %H:%M")
            
            # Create field with enhanced formatting
            trans_name = trans_type.replace('_', ' ').title()
            field_name = f"{emoji} {trans_name} - {timestamp}"
            field_value = f"**{amount_str} {currency}** → Guthaben: {balance_after} {currency}"
            if description:
                field_value += f"\n_{description}_"
            
            embed.add_field(name=field_name, value=field_value, inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        logger.error(f"Error viewing transactions: {e}", exc_info=True)
        await interaction.followup.send(f"Fehler beim Laden der Transaktionen: {str(e)}", ephemeral=True)


@tree.command(name="send", description="Sende Geld an einen anderen Benutzer.")
@app_commands.describe(
    user="Der Benutzer, dem du Geld senden möchtest",
    amount="Der Betrag, den du senden möchtest"
)
async def send_money(interaction: discord.Interaction, user: discord.Member, amount: int):
    """Send money to another user."""
    await interaction.response.defer(ephemeral=True)
    
    try:
        from modules.economy import transfer_currency
        
        # Validation
        if user.bot:
            await interaction.followup.send("❌ Du kannst Bots kein Geld senden!", ephemeral=True)
            return
        
        if amount <= 0:
            await interaction.followup.send("❌ Der Betrag muss positiv sein!", ephemeral=True)
            return
        
        if user.id == interaction.user.id:
            await interaction.followup.send("❌ Du kannst dir selbst kein Geld senden!", ephemeral=True)
            return
        
        # Get current balance
        balance = await db_helpers.get_balance(interaction.user.id)
        currency = config['modules']['economy']['currency_symbol']
        
        if balance < amount:
            await interaction.followup.send(
                f"❌ Nicht genug Guthaben! Du hast {balance} {currency}, brauchst aber {amount} {currency}.",
                ephemeral=True
            )
            return
        
        # Perform transfer
        success, message = await transfer_currency(
            db_helpers,
            interaction.user.id,
            user.id,
            amount,
            interaction.user.display_name,
            user.display_name,
            config
        )
        
        if success:
            # Log transactions for both users
            new_balance = await db_helpers.get_balance(interaction.user.id)
            await db_helpers.log_transaction(
                interaction.user.id,
                'transfer',
                -amount,
                new_balance,
                f"Sent to {user.display_name}"
            )
            
            recipient_balance = await db_helpers.get_balance(user.id)
            await db_helpers.log_transaction(
                user.id,
                'transfer',
                amount,
                recipient_balance,
                f"Received from {interaction.user.display_name}"
            )
            
            # Create success embed
            embed = discord.Embed(
                title="💸 Geld gesendet!",
                description=f"Du hast {amount} {currency} an {user.mention} gesendet!",
                color=discord.Color.green()
            )
            embed.add_field(name="Neues Guthaben", value=f"{new_balance} {currency}", inline=True)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Try to notify recipient (if DM access is enabled)
            try:
                has_dm_access = await db_helpers.has_feature_unlock(user.id, 'dm_access')
                if has_dm_access:
                    recipient_embed = discord.Embed(
                        title="💰 Geld erhalten!",
                        description=f"{interaction.user.display_name} hat dir {amount} {currency} gesendet!",
                        color=discord.Color.gold()
                    )
                    recipient_embed.add_field(name="Neues Guthaben", value=f"{recipient_balance} {currency}", inline=True)
                    await user.send(embed=recipient_embed)
            except:
                pass  # Silently fail if we can't send DM
        else:
            await interaction.followup.send(f"❌ {message}", ephemeral=True)
            
    except Exception as e:
        logger.error(f"Error sending money: {e}", exc_info=True)
        await interaction.followup.send(f"❌ Fehler beim Senden: {str(e)}", ephemeral=True)


@tree.command(name="news", description="Zeige die neuesten Nachrichten vom Server.")
@app_commands.describe(limit="Anzahl der anzuzeigenden Artikel (Standard: 5)")
async def view_news(interaction: discord.Interaction, limit: int = 5):
    """View latest news articles with pagination."""
    await interaction.response.defer(ephemeral=True)
    
    if limit < 1 or limit > 5:
        await interaction.followup.send("Limit muss zwischen 1 und 5 liegen.", ephemeral=True)
        return
    
    try:
        articles = await news.get_latest_news(db_helpers, limit)
        
        if not articles:
            await interaction.followup.send("Noch keine Nachrichten verfügbar.", ephemeral=True)
            return
        
        # Update quest progress for checking news
        await quests.update_quest_progress(db_helpers, interaction.user.id, 'check_news', 1, config)
        
        # Use pagination view for better user experience
        view = news.NewsPaginationView(articles, interaction.user.id)
        embed = view.get_current_embed()
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error viewing news: {e}", exc_info=True)
        await interaction.followup.send(f"Fehler beim Laden der Nachrichten: {str(e)}", ephemeral=True)


@tree.command(name="sportnews", description="📰 Sport News - Fußball, F1 & MotoGP Nachrichten!")
async def view_sports_news(interaction: discord.Interaction):
    """View sports news with multi-sport tabs."""
    await interaction.response.defer(ephemeral=True)
    
    try:
        # Get sports data
        if not db_helpers.db_pool:
            await interaction.followup.send("Datenbank nicht verfügbar.", ephemeral=True)
            return
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            await interaction.followup.send("Datenbankverbindung fehlgeschlagen.", ephemeral=True)
            return
        
        cursor = conn.cursor(dictionary=True)
        try:
            sports_data = await news.gather_sports_news_data(db_helpers, cursor)
        finally:
            cursor.close()
            conn.close()
        
        # Get sports news articles
        articles = await news.get_sports_news(db_helpers, limit=5)
        
        # Create the sports news view
        view = news.SportsNewsPaginationView(db_helpers, interaction.user.id, sports_data, articles)
        embed = view.get_current_embed()
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        
        # Update quest progress
        await quests.update_quest_progress(db_helpers, interaction.user.id, 'check_news', 1, config)
        
    except Exception as e:
        logger.error(f"Error viewing sports news: {e}", exc_info=True)
        await interaction.followup.send(f"Fehler beim Laden der Sport-Nachrichten: {str(e)}", ephemeral=True)


# Shop commands registered above


# ============================================================================
# STOCK MARKET SYSTEM SLASH COMMANDS
# ============================================================================

class StockMarketMainView(discord.ui.View):
    """Main stock market view with navigation."""
    
    def __init__(self, user: discord.Member):
        super().__init__(timeout=180)
        self.user = user
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("Du kannst diese Auswahl nicht bedienen.", ephemeral=True)
            return False
        return True
    
    @discord.ui.button(label="📊 Top Aktien", style=discord.ButtonStyle.primary, row=0)
    async def top_stocks_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        # Get top 10 stocks
        top_stocks = await stock_market.get_top_stocks(db_helpers, limit=10)
        
        embed = discord.Embed(
            title="📊 Top 10 Aktien",
            description="Die besten und schlechtesten Performer (sortiert nach Änderung)",
            color=discord.Color.blue()
        )
        
        if not top_stocks:
            embed.description = "Keine Aktien verfügbar."
        else:
            for i, stock in enumerate(top_stocks, 1):
                symbol, name, current_price, previous_price, change_pct, volume = stock
                emoji = stock_market.get_stock_emoji(float(change_pct))
                price_str = stock_market.format_price(float(current_price))
                prev_str = stock_market.format_price(float(previous_price))
                
                # Add trend arrow
                trend = "⬆️" if change_pct > 0 else "⬇️" if change_pct < 0 else "➖"
                
                field_value = f"{trend} **{prev_str}** → **{price_str}**\n"
                field_value += f"Änderung: {emoji} **{change_pct:+.2f}%**\n"
                field_value += f"Volumen heute: **{volume}** Aktien"
                
                embed.add_field(
                    name=f"{i}. {symbol} - {name}",
                    value=field_value,
                    inline=True if i % 2 == 1 else False
                )
        
        embed.set_footer(text="🔄 Preise aktualisieren sich alle 30 Minuten")
        await interaction.edit_original_response(embed=embed, view=self)
    
    @discord.ui.button(label="💼 Mein Portfolio", style=discord.ButtonStyle.success, row=0)
    async def portfolio_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        # Update quest progress for checking portfolio
        await quests.update_quest_progress(db_helpers, interaction.user.id, 'check_portfolio', 1, config)
        
        # Get user's portfolio
        portfolio = await stock_market.get_user_portfolio(db_helpers, self.user.id)
        currency = config['modules']['economy']['currency_symbol']
        
        embed = discord.Embed(
            title="💼 Dein Portfolio",
            description="Deine Aktienbestände",
            color=discord.Color.green()
        )
        
        if not portfolio:
            embed.description = "Du besitzt noch keine Aktien."
        else:
            total_value = 0
            total_investment = 0
            
            for stock in portfolio:
                symbol, name, shares, avg_buy, current_price, gain_pct, current_value = stock
                shares = int(shares)
                avg_buy = float(avg_buy)
                current_price = float(current_price)
                gain_pct = float(gain_pct)
                current_value = float(current_value)
                
                total_value += current_value
                investment = shares * avg_buy
                total_investment += investment
                
                emoji = "📈" if gain_pct > 0 else "📉" if gain_pct < 0 else "➖"
                
                field_value = f"**{shares} Aktien**\n"
                field_value += f"Kaufpreis Ø: {stock_market.format_price(avg_buy)}\n"
                field_value += f"Aktuell: {stock_market.format_price(current_price)}\n"
                field_value += f"Wert: **{current_value:.2f} {currency}**\n"
                field_value += f"Gewinn/Verlust: {emoji} **{gain_pct:+.2f}%**"
                
                embed.add_field(
                    name=f"{symbol} - {name}",
                    value=field_value,
                    inline=True
                )
            
            # Add summary at the top
            total_gain_pct = ((total_value - total_investment) / total_investment * 100) if total_investment > 0 else 0
            summary_emoji = "📈" if total_gain_pct > 0 else "📉" if total_gain_pct < 0 else "➖"
            
            embed.insert_field_at(
                0,
                name="📊 Gesamt",
                value=f"Portfoliowert: **{total_value:.2f} {currency}**\n"
                      f"Investiert: {total_investment:.2f} {currency}\n"
                      f"Gewinn/Verlust: {summary_emoji} **{total_gain_pct:+.2f}%**",
                inline=False
            )
        
        await interaction.edit_original_response(embed=embed, view=self)
    
    @discord.ui.button(label="🏪 Börse", style=discord.ButtonStyle.secondary, row=1)
    async def exchange_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        # Show stock exchange view
        view = StockExchangeView(self.user)
        await view.show_exchange(interaction)
    
    @discord.ui.button(label="📊 Marktaktivität", style=discord.ButtonStyle.secondary, row=1)
    async def market_activity_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        # Get recent trades
        recent_trades = await stock_market.get_recent_trades(db_helpers, limit=15)
        
        embed = discord.Embed(
            title="📊 Marktaktivität",
            description="Letzte Transaktionen an der Börse",
            color=discord.Color.purple()
        )
        
        if not recent_trades:
            embed.description = "Noch keine Handelsaktivität."
        else:
            activity_text = ""
            for trade in recent_trades[:15]:
                trans_type, description, created_at, volume = trade
                
                # Parse time
                time_str = created_at.strftime("%H:%M")
                
                # Emoji based on type
                emoji = "🟢" if trans_type == "stock_buy" else "🔴"
                
                # Extract stock symbol from description
                if description:
                    activity_text += f"{emoji} `{time_str}` {description}\n"
            
            if activity_text:
                embed.description = activity_text
        
        embed.set_footer(text="Live Marktdaten • Aktualisiert in Echtzeit")
        
        await interaction.edit_original_response(embed=embed, view=self)


class StockExchangeView(discord.ui.View):
    """Stock exchange for buying and selling."""
    
    def __init__(self, user: discord.Member):
        super().__init__(timeout=180)
        self.user = user
        self.selected_stock = None
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("Du kannst diese Auswahl nicht bedienen.", ephemeral=True)
            return False
        return True
    
    async def show_exchange(self, interaction: discord.Interaction):
        """Show the stock exchange."""
        # Get all stocks from database
        all_stocks = await stock_market.get_all_stocks(db_helpers, limit=25)
        
        if all_stocks:
            # Add dropdown with stocks from database
            dropdown = StockSelectDropdown(self, all_stocks)
            self.add_item(dropdown)
        
        embed = discord.Embed(
            title="🏪 Börse",
            description="Wähle eine Aktie aus, um zu handeln.",
            color=discord.Color.gold()
        )
        
        # Get top stocks for display
        top_stocks = await stock_market.get_top_stocks(db_helpers, limit=10)
        
        if top_stocks:
            stock_list = ""
            for symbol, name, current_price, previous_price, change_pct, volume in top_stocks:
                emoji = stock_market.get_stock_emoji(float(change_pct))
                price_str = stock_market.format_price(float(current_price))
                stock_list += f"{emoji} **{symbol}** - {price_str} ({change_pct:+.2f}%)\n"
            
            embed.add_field(
                name="Verfügbare Aktien",
                value=stock_list,
                inline=False
            )
        
        await interaction.edit_original_response(embed=embed, view=self)
    
    async def show_stock_detail(self, interaction: discord.Interaction, stock_symbol: str):
        """Show details for a specific stock."""
        stock = await stock_market.get_stock(db_helpers, stock_symbol)
        
        if not stock:
            await interaction.response.send_message("Aktie nicht gefunden!", ephemeral=True)
            return
        
        symbol, name, category, current_price, previous_price, trend, volume, last_update = stock
        current_price = float(current_price)
        previous_price = float(previous_price)
        change_pct = ((current_price - previous_price) / previous_price * 100) if previous_price > 0 else 0
        
        emoji = stock_market.get_stock_emoji(change_pct)
        price_str = stock_market.format_price(current_price)
        currency = config['modules']['economy']['currency_symbol']
        
        # Get user's holdings
        portfolio = await stock_market.get_user_portfolio(db_helpers, self.user.id)
        user_shares = 0
        for p_stock in portfolio:
            if p_stock[0] == symbol:
                user_shares = int(p_stock[2])
                break
        
        embed = discord.Embed(
            title=f"{emoji} {symbol} - {name}",
            description=f"Kategorie: {category.title()}",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="💰 Aktueller Preis",
            value=f"**{price_str}**",
            inline=True
        )
        
        embed.add_field(
            name="📊 Änderung",
            value=f"**{change_pct:+.2f}%**",
            inline=True
        )
        
        embed.add_field(
            name="📈 Volumen",
            value=f"{volume}",
            inline=True
        )
        
        if user_shares > 0:
            embed.add_field(
                name="💼 Deine Aktien",
                value=f"**{user_shares} Stück**",
                inline=True
            )
        
        # Get user balance
        balance = await db_helpers.get_balance(self.user.id)
        max_buyable = int(balance / current_price) if current_price > 0 else 0
        
        embed.add_field(
            name="💵 Dein Guthaben",
            value=f"{balance:.2f} {currency}\n(Maximal {max_buyable} Aktien)",
            inline=False
        )
        
        # Create buy/sell buttons
        view = StockTradeView(self.user, symbol, current_price, user_shares)
        
        await interaction.edit_original_response(embed=embed, view=view)


class StockSelectDropdown(discord.ui.Select):
    """Dropdown for selecting stocks."""
    
    def __init__(self, parent_view: StockExchangeView, stocks: list):
        self.parent_view = parent_view
        
        # Create options from database stocks
        options = []
        for stock in stocks:
            symbol, name, category = stock
            options.append(
                discord.SelectOption(
                    label=symbol, 
                    description=f"{name} ({category})"[:100],  # Discord limit
                    value=symbol
                )
            )
        
        super().__init__(
            placeholder="Wähle eine Aktie...",
            options=options,
            row=0
        )
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        selected = self.values[0]
        self.parent_view.selected_stock = selected
        await self.parent_view.show_stock_detail(interaction, selected)


class StockTradeView(discord.ui.View):
    """View for trading a specific stock."""
    
    def __init__(self, user: discord.Member, symbol: str, price: float, owned_shares: int):
        super().__init__(timeout=180)
        self.user = user
        self.symbol = symbol
        self.price = price
        self.owned_shares = owned_shares
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("Du kannst diese Auswahl nicht bedienen.", ephemeral=True)
            return False
        return True
    
    @discord.ui.button(label="Kaufen 1", style=discord.ButtonStyle.success, custom_id="buy_1", row=0)
    async def buy_1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.execute_trade(interaction, 'buy', 1)
    
    @discord.ui.button(label="Kaufen 5", style=discord.ButtonStyle.success, custom_id="buy_5", row=0)
    async def buy_5(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.execute_trade(interaction, 'buy', 5)
    
    @discord.ui.button(label="Kaufen 10", style=discord.ButtonStyle.success, custom_id="buy_10", row=0)
    async def buy_10(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.execute_trade(interaction, 'buy', 10)
    
    @discord.ui.button(label="Verkaufen 1", style=discord.ButtonStyle.danger, custom_id="sell_1", row=1, disabled=None)
    async def sell_1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.execute_trade(interaction, 'sell', 1)
    
    @discord.ui.button(label="Verkaufen 5", style=discord.ButtonStyle.danger, custom_id="sell_5", row=1)
    async def sell_5(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.execute_trade(interaction, 'sell', 5)
    
    @discord.ui.button(label="Verkaufen Alle", style=discord.ButtonStyle.danger, custom_id="sell_all", row=1)
    async def sell_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.execute_trade(interaction, 'sell', self.owned_shares)
    
    @discord.ui.button(label="◀️ Zurück", style=discord.ButtonStyle.secondary, row=2)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        view = StockExchangeView(self.user)
        await view.show_exchange(interaction)
    
    async def execute_trade(self, interaction: discord.Interaction, action: str, shares: int):
        """Execute a buy or sell trade."""
        await interaction.response.defer()
        
        if shares <= 0:
            await interaction.followup.send("Ungültige Anzahl!", ephemeral=True)
            return
        
        currency = config['modules']['economy']['currency_symbol']
        
        if action == 'buy':
            success, message = await stock_market.buy_stock(
                db_helpers, 
                self.user.id, 
                self.symbol, 
                shares,
                None  # Currency system handled internally
            )
        else:  # sell
            if shares > self.owned_shares:
                await interaction.followup.send(f"Du besitzt nur {self.owned_shares} Aktien!", ephemeral=True)
                return
            
            success, message = await stock_market.sell_stock(
                db_helpers,
                self.user.id,
                self.symbol,
                shares
            )
        
        if success:
            embed = discord.Embed(
                title="✅ Transaktion erfolgreich",
                description=message,
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="❌ Transaktion fehlgeschlagen",
                description=message,
                color=discord.Color.red()
            )
        
        # Get updated balance
        balance = await db_helpers.get_balance(self.user.id)
        embed.add_field(
            name="💰 Neues Guthaben",
            value=f"{balance:.2f} {currency}",
            inline=False
        )
        
        await interaction.edit_original_response(embed=embed, view=None)


@tree.command(name="stock", description="Öffne den Aktienmarkt.")
async def stock_market_command(interaction: discord.Interaction):
    """Open the stock market interface."""
    await interaction.response.defer(ephemeral=True)
    
    try:
        view = StockMarketMainView(interaction.user)
        currency = config['modules']['economy']['currency_symbol']
        
        # Get market overview for live data
        market_overview = await stock_market.get_market_overview(db_helpers)
        
        embed = discord.Embed(
            title="📈 Sulfur Aktienmarkt",
            description="**Willkommen an der Börse!**\n\n"
                       "Hier kannst du in verschiedene Unternehmen investieren und dein Vermögen vermehren. "
                       "Die Kurse ändern sich alle 30 Minuten basierend auf Markttrends und Aktivitäten im Server!",
            color=discord.Color.gold()
        )
        
        # Add live market stats
        if market_overview:
            avg_change_emoji = "📈" if market_overview['avg_change'] > 0 else "📉" if market_overview['avg_change'] < 0 else "➖"
            embed.add_field(
                name="🌍 Live Marktdaten",
                value=f"**Aktien:** {market_overview['total_stocks']} | "
                      f"**24h Trades:** {market_overview['trades_24h']}\n"
                      f"**Ø Veränderung:** {avg_change_emoji} {market_overview['avg_change']:+.2f}% | "
                      f"**Volumen:** {market_overview['total_volume']}",
                inline=False
            )
        
        # Add stock categories info
        embed.add_field(
            name="📊 Aktienkategorien",
            value="🔷 **Tech** - Hohe Volatilität, starke Trends\n"
                  "💎 **Blue Chip** - Stabil, geringe Schwankungen\n"
                  "🪙 **Crypto** - Sehr volatil, schwache Trends\n"
                  "🎲 **Meme** - Extreme Volatilität, unvorhersehbar\n"
                  "🛢️ **Commodity** - Mittlere Volatilität, stabile Trends\n"
                  "💼 **Fund** - Sehr stabil, sichere Investition",
            inline=False
        )
        
        # Add special stocks info
        embed.add_field(
            name="⭐ Besondere Aktien",
            value="🐺 **WOLF** - Werwolf Inc (beeinflusst durch Werwolf-Spiele)\n"
                  "⚡ **BOOST** - Boost Corp (beeinflusst durch Boost-Käufe)\n"
                  "🎨 **COLOR** - Color Dynamics (beeinflusst durch Farbrollen-Käufe)\n"
                  "🎰 **GAMBL** - Gambling Industries (beeinflusst durch Casino-Aktivität)",
            inline=False
        )
        
        # Show current balance
        balance = await db_helpers.get_balance(interaction.user.id)
        embed.add_field(
            name="💰 Dein Guthaben",
            value=f"**{balance:.2f} {currency}**",
            inline=True
        )
        
        # Show portfolio value
        portfolio = await stock_market.get_user_portfolio(db_helpers, interaction.user.id)
        portfolio_value = sum(float(stock[6]) for stock in portfolio) if portfolio else 0
        embed.add_field(
            name="💼 Portfoliowert",
            value=f"**{portfolio_value:.2f} {currency}**",
            inline=True
        )
        
        # Show total net worth
        net_worth = balance + portfolio_value
        embed.add_field(
            name="💎 Gesamtvermögen",
            value=f"**{net_worth:.2f} {currency}**",
            inline=True
        )
        
        embed.set_footer(text="Nutze die Buttons unten um zu navigieren • Preise aktualisieren sich alle 30 Minuten")
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error opening stock market: {e}", exc_info=True)
        await interaction.followup.send(f"Fehler beim Öffnen des Aktienmarkts: {str(e)}", ephemeral=True)


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
            # Flush any active game time before showing quests
            await flush_active_game_time(self.user_id)
            
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
            # Flush any active game time before claiming rewards
            await flush_active_game_time(self.user_id)
            
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
            total_xp = 0
            claimed_count = 0
            
            for quest in unclaimed_quests:
                success, reward, xp, message = await quests.claim_quest_reward(
                    db_helpers,
                    self.user_id,
                    interaction.user.display_name,
                    quest['id'],
                    self.config
                )
                
                if success:
                    total_reward += reward
                    total_xp += xp
                    claimed_count += 1
            
            currency = self.config['modules']['economy']['currency_symbol']
            
            if claimed_count > 0:
                embed = discord.Embed(
                    title="✅ Quest-Belohnungen eingesammelt!",
                    description=f"Du hast {claimed_count} Quest(s) abgeschlossen!",
                    color=discord.Color.green()
                )
                
                reward_text = f"**+{total_reward} {currency}**"
                if total_xp > 0:
                    reward_text += f"\n**+{total_xp} XP**"
                
                embed.add_field(
                    name="Belohnung",
                    value=reward_text,
                    inline=False
                )
                
                # Check if all quests are now completed and claimed
                all_completed, completed_count, total_count = await quests.check_all_quests_completed(db_helpers, self.user_id)
                
                if all_completed:
                    # Grant daily completion bonus
                    bonus_success, bonus_amount, bonus_xp = await quests.grant_daily_completion_bonus(
                        db_helpers,
                        self.user_id,
                        interaction.user.display_name,
                        self.config
                    )
                    
                    if bonus_success:
                        bonus_text = f"**+{bonus_amount} {currency}**"
                        if bonus_xp > 0:
                            bonus_text += f"\n**+{bonus_xp} XP**"
                        
                        embed.add_field(
                            name="🎉 Tagesbonus!",
                            value=f"Alle Quests abgeschlossen!\n{bonus_text}",
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
        user_id = interaction.user.id
        
        # Get user's theme
        user_theme = await themes.get_user_theme(db_helpers, user_id)
        
        # Create menu view
        view = QuestMenuView(user_id, config)
        
        # Create initial embed with theme support
        embed = discord.Embed(
            title="📋 Quest-Menü",
            description="Wähle eine Option aus dem Menü:",
            color=themes.get_theme_color(user_theme, 'primary') if user_theme else discord.Color.blue()
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


# REMOVED: /questclaim command - functionality exists as a button in /quests command

# REMOVED: /monthly command - functionality exists as a button in /quests command

# --- Game Commands & UI ---
from modules.games import BlackjackGame, RouletteGame, MinesGame, RussianRouletteGame, TowerOfTreasureGame

# Active game states
active_blackjack_games = {}
active_mines_games = {}
active_rr_games = {}
active_tower_games = {}
active_horse_races = {}  # {channel_id: HorseRace instance}
race_counter = 0  # Global race ID counter


class BlackjackView(discord.ui.View):
    """UI view for Blackjack game with Hit/Stand buttons."""
    
    def __init__(self, game: BlackjackGame, user_id: int, theme_id=None):
        super().__init__(timeout=120)
        self.game = game
        self.user_id = user_id
        self.theme_id = theme_id
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Das ist nicht dein Spiel!", ephemeral=True)
            return False
        return True
    
    @discord.ui.button(label="Hit", style=discord.ButtonStyle.primary, emoji="🃏")
    async def hit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        # Show card drawing animation
        import asyncio
        temp_embed = discord.Embed(
            title="🃏 Blackjack",
            description="Ziehe eine Karte... 🎴",
            color=themes.get_theme_color(self.theme_id, 'primary') if self.theme_id else discord.Color.blurple()
        )
        await interaction.edit_original_response(embed=temp_embed, view=self)
        await asyncio.sleep(0.6)
        
        self.game.hit()
        
        if not self.game.is_active:
            # Game ended (bust)
            await self._finish_game(interaction)
        else:
            # Update the embed
            embed = self.game.create_embed(theme_id=self.theme_id)
            await interaction.edit_original_response(embed=embed, view=self)
    
    @discord.ui.button(label="Stand", style=discord.ButtonStyle.success, emoji="✋")
    async def stand_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        self.game.stand()
        await self._finish_game(interaction)
    
    async def _finish_game(self, interaction: discord.Interaction):
        """Finishes the game and shows results."""
        result, multiplier = self.game.get_result()
        embed = self.game.create_embed(show_dealer_card=True, theme_id=self.theme_id)
        
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
        
        # --- NEW: Influence GAMBL stock based on result ---
        try:
            won = result in ['win', 'blackjack']
            payout = int(self.game.bet * multiplier) if won else 0
            await stock_market.record_gambling_activity(db_helpers, self.game.bet, won, payout)
        except Exception as e:
            logger.error(f"Failed to record gambling stock influence: {e}")
        
        # --- NEW: Log game to database for tracking ---
        try:
            won = result in ['win', 'blackjack']
            payout = int(self.game.bet * multiplier) if won else 0
            
            # Log to blackjack_games table
            await db_helpers.log_blackjack_game(
                self.user_id, 
                self.game.bet, 
                result, 
                payout
            )
            
            # Update gambling_stats
            await db_helpers.update_gambling_stats(
                self.user_id,
                'blackjack',
                self.game.bet,
                payout
            )
            
            # Update user_stats for monthly tracking
            await db_helpers.update_user_game_stats(
                self.user_id,
                interaction.user.display_name,
                won,
                self.game.bet,
                payout
            )
        except Exception as e:
            logger.error(f"Failed to log blackjack game stats: {e}")
        
        # Add result field with enhanced formatting and theme colors
        result_text = ""
        if result == 'blackjack':
            result_text = f"🎉 **BLACKJACK!** 🎉\n"
            result_text += f"Perfekte 21! Du gewinnst **{int(self.game.bet * multiplier)} {currency}**!"
            embed.add_field(name="🏆 Ergebnis", value=result_text, inline=False)
            embed.color = themes.get_theme_color(self.theme_id, 'success') if self.theme_id else discord.Color.gold()
        elif result == 'win':
            result_text = f"✅ **Gewonnen!** ✅\n"
            result_text += f"Du schlägst den Dealer! Gewinn: **{int(self.game.bet * multiplier)} {currency}**"
            embed.add_field(name="🏆 Ergebnis", value=result_text, inline=False)
            embed.color = themes.get_theme_color(self.theme_id, 'success') if self.theme_id else discord.Color.green()
        elif result == 'lose':
            result_text = f"❌ **Verloren!** ❌\n"
            result_text += f"Der Dealer gewinnt. Verlust: **-{self.game.bet} {currency}**"
            embed.add_field(name="💸 Ergebnis", value=result_text, inline=False)
            embed.color = themes.get_theme_color(self.theme_id, 'danger') if self.theme_id else discord.Color.red()
        else:  # push
            result_text = f"🤝 **Unentschieden!** 🤝\n"
            result_text += f"Beide haben den gleichen Wert. Einsatz zurück: **{self.game.bet} {currency}**"
            embed.add_field(name="⚖️ Ergebnis", value=result_text, inline=False)
            embed.color = themes.get_theme_color(self.theme_id, 'primary') if self.theme_id else discord.Color.blue()
        
        # Add balance info
        balance_change = winnings
        if balance_change > 0:
            embed.add_field(name="💰 Guthaben", value=f"{new_balance} {currency} (+{balance_change})", inline=True)
        elif balance_change < 0:
            embed.add_field(name="💰 Guthaben", value=f"{new_balance} {currency} ({balance_change})", inline=True)
        else:
            embed.add_field(name="💰 Guthaben", value=f"{new_balance} {currency}", inline=True)
        
        # Add tip/footer
        if result == 'blackjack':
            embed.set_footer(text="🎊 Glückwunsch zum Blackjack! 2.5x Auszahlung!")
        elif result == 'win':
            embed.set_footer(text="🎉 Gut gespielt! Weiter so!")
        elif result == 'lose':
            embed.set_footer(text="Versuch es nochmal! Das nächste Spiel wird besser!")
        else:
            embed.set_footer(text="Knapp! Beim nächsten Mal vielleicht mehr Glück!")
        
        # Create share button view with theme support
        share_view = GamblingShareView(
            game_type="blackjack",
            result_data={
                'result': result,
                'net_result': winnings,
                'bet': self.game.bet,
                'balance': new_balance
            },
            user_id=self.user_id,
            theme_id=self.theme_id
        )
        
        await interaction.edit_original_response(embed=embed, view=share_view)
        
        # Remove from active games
        if self.user_id in active_blackjack_games:
            del active_blackjack_games[self.user_id]
        
        self.stop()


class MinesView(discord.ui.View):
    """UI view for Mines game with grid buttons."""
    
    def __init__(self, game: MinesGame, user_id: int, theme_id=None):
        super().__init__(timeout=300)
        self.game = game
        self.user_id = user_id
        self.theme_id = theme_id
        self._build_grid()
    
    def _build_grid(self):
        """Builds the button grid for the mines game."""
        # Discord allows max 5 rows with 5 buttons each (25 total)
        # Limit grid to 4x4 (16 buttons) to leave room for cashout button
        
        actual_grid_size = min(self.game.grid_size, 4)
        
        # Add all grid cells as buttons
        for row in range(actual_grid_size):
            for col in range(actual_grid_size):
                button = discord.ui.Button(
                    label="⬜",
                    style=discord.ButtonStyle.secondary,
                    custom_id=f"mine_{row}_{col}",
                    row=row
                )
                button.callback = self._create_callback(row, col)
                self.add_item(button)
        
        # Add cashout button on the row after the grid
        cashout_button = discord.ui.Button(
            label="💎 Cash Out",
            style=discord.ButtonStyle.success,
            custom_id="cashout",
            row=actual_grid_size
        )
        cashout_button.callback = self._cashout_callback
        self.add_item(cashout_button)
    
    def _create_callback(self, row: int, col: int):
        """Creates a callback for a grid button with reveal animation."""
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("Das ist nicht dein Spiel!", ephemeral=True)
                return
            
            await interaction.response.defer()
            
            # Show revealing animation
            import asyncio
            for item in self.children:
                if hasattr(item, 'custom_id') and item.custom_id == f"mine_{row}_{col}":
                    item.label = "❓"
                    item.style = discord.ButtonStyle.primary
                    break
            
            temp_embed = self.game.create_embed(theme_id=self.theme_id)
            await interaction.edit_original_response(embed=temp_embed, view=self)
            await asyncio.sleep(0.4)
            
            continue_game, hit_mine, multiplier = self.game.reveal(row, col)
            
            # Update button appearance
            for item in self.children:
                if hasattr(item, 'custom_id') and item.custom_id == f"mine_{row}_{col}":
                    if hit_mine:
                        item.label = themes.get_theme_asset(self.theme_id, 'mines_bomb')
                        item.style = discord.ButtonStyle.danger
                    else:
                        item.label = themes.get_theme_asset(self.theme_id, 'mines_revealed')
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
                embed = self.game.create_embed(theme_id=self.theme_id)
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
            
            # --- NEW: Influence GAMBL stock ---
            try:
                won = profit > 0
                await stock_market.record_gambling_activity(db_helpers, self.game.bet, won, winnings)
            except Exception as e:
                logger.error(f"Failed to record gambling stock influence: {e}")
            
            # --- NEW: Log game to database for tracking ---
            try:
                await db_helpers.log_mines_game(
                    self.user_id,
                    self.game.bet,
                    self.game.grid_size,
                    self.game.mine_count,
                    self.game.revealed_count,
                    'cashout',
                    multiplier,
                    winnings
                )
                
                await db_helpers.update_gambling_stats(
                    self.user_id,
                    'mines',
                    self.game.bet,
                    winnings
                )
                
                await db_helpers.update_user_game_stats(
                    self.user_id,
                    interaction.user.display_name,
                    profit > 0,
                    self.game.bet,
                    winnings
                )
            except Exception as e:
                logger.error(f"Failed to log mines game stats: {e}")
            
            currency = config['modules']['economy']['currency_symbol']
            embed = self.game.create_embed(theme_id=self.theme_id)
            embed.color = themes.get_theme_color(self.theme_id, 'success')
            
            cashout_text = f"✅ **Erfolgreich ausgezahlt!** ✅\n"
            cashout_text += f"Aufgedeckte Felder: **{self.game.revealed_count}**\n"
            cashout_text += f"Multiplikator: **{multiplier:.2f}x**\n"
            cashout_text += f"Gewinn: **+{profit} {currency}**"
            
            embed.add_field(
                name="💰 Auszahlung",
                value=cashout_text,
                inline=False
            )
            embed.add_field(name="💰 Guthaben", value=f"{new_balance} {currency}", inline=True)
            embed.set_footer(text="Gut gespielt! Du hast rechtzeitig ausgezahlt!")
            
            # Disable all buttons
            for item in self.children:
                item.disabled = True
            
            # Add share button with theme support
            share_view = GamblingShareView(
                game_type="mines",
                result_data={
                    'revealed_count': self.game.revealed_count,
                    'multiplier': multiplier,
                    'profit': profit,
                    'balance': new_balance
                },
                user_id=self.user_id,
                theme_id=self.theme_id
            )
            
            await interaction.edit_original_response(embed=embed, view=share_view)
            
            # Remove from active games
            if self.user_id in active_mines_games:
                del active_mines_games[self.user_id]
            
            self.stop()
    
    async def _end_game(self, interaction: discord.Interaction, lost: bool):
        """Ends the game and shows results."""
        currency = config['modules']['economy']['currency_symbol']
        embed = self.game.create_embed(show_mines=True, theme_id=self.theme_id)
        
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
            
            # --- NEW: Influence GAMBL stock ---
            try:
                await stock_market.record_gambling_activity(db_helpers, self.game.bet, False, 0)
            except Exception as e:
                logger.error(f"Failed to record gambling stock influence: {e}")
            
            # --- NEW: Log game to database for tracking ---
            try:
                await db_helpers.log_mines_game(
                    self.user_id,
                    self.game.bet,
                    self.game.grid_size,
                    self.game.mine_count,
                    self.game.revealed_count,
                    'lost',
                    0,
                    0
                )
                
                await db_helpers.update_gambling_stats(
                    self.user_id,
                    'mines',
                    self.game.bet,
                    0
                )
                
                await db_helpers.update_user_game_stats(
                    self.user_id,
                    interaction.user.display_name,
                    False,
                    self.game.bet,
                    0
                )
            except Exception as e:
                logger.error(f"Failed to log mines game stats: {e}")
            
            embed.color = discord.Color.red()
            result_text = f"💥 **BOOM!** 💥\n"
            result_text += f"Du hast eine Mine getroffen!\n"
            result_text += f"Verlust: **-{self.game.bet} {currency}**"
            embed.add_field(
                name="💸 Spielende",
                value=result_text,
                inline=False
            )
            embed.add_field(name="💰 Guthaben", value=f"{new_balance} {currency}", inline=True)
            embed.set_footer(text="Beim nächsten Mal vorsichtiger sein!")
            
            # Add share button for loss with theme support
            share_view = GamblingShareView(
                game_type="mines",
                result_data={
                    'revealed_count': self.game.revealed_count,
                    'multiplier': 0,
                    'profit': -self.game.bet,
                    'balance': new_balance
                },
                user_id=self.user_id,
                theme_id=self.theme_id
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
            
            # --- NEW: Influence GAMBL stock ---
            try:
                await stock_market.record_gambling_activity(db_helpers, self.game.bet, True, int(self.game.bet * self.game.get_current_multiplier()))
            except Exception as e:
                logger.error(f"Failed to record gambling stock influence: {e}")
            
            embed.color = discord.Color.gold()
            result_text = f"🎉 **PERFEKT!** 🎉\n"
            result_text += f"Alle sicheren Felder aufgedeckt!\n"
            result_text += f"Gewinn: **+{profit} {currency}** ({self.game.get_current_multiplier()}x)"
            embed.add_field(
                name="🏆 Spielende",
                value=result_text,
                inline=False
            )
            embed.add_field(name="💰 Guthaben", value=f"{new_balance} {currency}", inline=True)
            embed.set_footer(text="🎊 Glückwunsch! Perfekt gespielt!")
            
            # Add share button for win with theme support
            share_view = GamblingShareView(
                game_type="mines",
                result_data={
                    'revealed_count': self.game.revealed_count,
                    'multiplier': self.game.get_current_multiplier(),
                    'profit': profit,
                    'balance': new_balance
                },
                user_id=self.user_id,
                theme_id=self.theme_id
            )
        
        # Disable all buttons and reveal all mines
        for item in self.children:
            item.disabled = True
        
        # Use share view if available, otherwise use self
        final_view = share_view if 'share_view' in locals() else self
        await interaction.edit_original_response(embed=embed, view=final_view)
        
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
    
    # Check if user has casino access
    has_casino = await db_helpers.has_feature_unlock(user_id, 'casino')
    if not has_casino:
        currency = config['modules']['economy']['currency_symbol']
        price = config['modules']['economy']['shop']['features'].get('casino', 500)
        await interaction.followup.send(
            f"🎰 Du benötigst **Casino Access**, um Blackjack zu spielen!\n"
            f"Kaufe es im Shop für {price} {currency} mit `/shopbuy`",
            ephemeral=True
        )
        return
    
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
    
    # Get user's theme
    user_theme = await themes.get_user_theme(db_helpers, user_id)
    
    # Create view with theme support
    view = BlackjackView(game, user_id, user_theme)
    embed = game.create_embed(theme_id=user_theme)
    
    await interaction.followup.send(embed=embed, view=view, ephemeral=True)


# --- Gambling Share Button View ---

class GamblingShareView(discord.ui.View):
    """View with share button for gambling results."""
    
    def __init__(self, game_type: str, result_data: dict, user_id: int, theme_id=None):
        super().__init__(timeout=300)
        self.game_type = game_type
        self.result_data = result_data
        self.user_id = user_id
        self.theme_id = theme_id
    
    @discord.ui.button(label="Ergebnis teilen", style=discord.ButtonStyle.primary, emoji="📢")
    async def share_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Share gambling result publicly."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Das ist nicht dein Ergebnis!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Create public embed based on game type
        currency = config['modules']['economy']['currency_symbol']
        
        if self.game_type == "roulette":
            data = self.result_data
            result_number = data['result_number']
            net_result = data['net_result']
            
            # Determine color emoji and embed color (with theme support)
            if result_number == 0:
                result_emoji = "🟢"
                color = themes.get_theme_color(self.theme_id, 'success') if self.theme_id else discord.Color.green()
            elif result_number in RouletteGame.RED:
                result_emoji = "🔴"
                if net_result > 0:
                    color = themes.get_theme_color(self.theme_id, 'success') if self.theme_id else discord.Color.gold()
                else:
                    color = themes.get_theme_color(self.theme_id, 'danger') if self.theme_id else discord.Color.red()
            else:
                result_emoji = "⚫"
                if net_result > 0:
                    color = themes.get_theme_color(self.theme_id, 'success') if self.theme_id else discord.Color.gold()
                else:
                    color = themes.get_theme_color(self.theme_id, 'warning') if self.theme_id else discord.Color.dark_grey()
            
            if net_result > 0:
                title = "🎉 Roulette Gewinn!"
                description = f"{interaction.user.mention} hat **+{net_result} {currency}** gewonnen!"
            elif net_result < 0:
                title = "💸 Roulette Verlust"
                description = f"{interaction.user.mention} hat **{net_result} {currency}** verloren."
            else:
                title = "🤝 Roulette Break Even"
                description = f"{interaction.user.mention} ist Break Even gegangen!"
            
            embed = discord.Embed(
                title=title,
                description=description,
                color=color
            )
            
            embed.add_field(
                name="🎯 Gewinnende Zahl",
                value=f"{result_emoji} **{result_number}**",
                inline=True
            )
            
            embed.add_field(
                name="💰 Nettoergebnis",
                value=f"**{'+' if net_result >= 0 else ''}{net_result} {currency}**",
                inline=True
            )
            
            embed.set_footer(text=f"Gespielt von {interaction.user.display_name}")
            
        elif self.game_type == "blackjack":
            data = self.result_data
            result = data['result']
            net_result = data['net_result']
            
            if result == 'blackjack':
                title = "🃏 BLACKJACK! 21!"
                color = themes.get_theme_color(self.theme_id, 'success') if self.theme_id else discord.Color.gold()
            elif result == 'win':
                title = "✅ Blackjack Gewinn!"
                color = themes.get_theme_color(self.theme_id, 'success') if self.theme_id else discord.Color.green()
            elif result == 'lose':
                title = "❌ Blackjack Verlust"
                color = themes.get_theme_color(self.theme_id, 'danger') if self.theme_id else discord.Color.red()
            else:
                title = "🤝 Blackjack Push"
                color = themes.get_theme_color(self.theme_id, 'primary') if self.theme_id else discord.Color.blue()
            
            description = f"{interaction.user.mention} hat **{'+' if net_result >= 0 else ''}{net_result} {currency}** {'gewonnen' if net_result > 0 else 'verloren'}!"
            
            embed = discord.Embed(title=title, description=description, color=color)
            embed.add_field(name="💰 Ergebnis", value=f"**{'+' if net_result >= 0 else ''}{net_result} {currency}**", inline=True)
            embed.set_footer(text=f"Gespielt von {interaction.user.display_name}")
        
        elif self.game_type == "mines":
            data = self.result_data
            profit = data.get('profit', 0)
            multiplier = data.get('multiplier', 0)
            revealed_count = data.get('revealed_count', 0)
            
            # Get themed mines asset
            mines_emoji = themes.get_theme_asset(self.theme_id, 'mines_revealed') if self.theme_id else '💎'
            
            if profit > 0:
                title = f"{mines_emoji} Mines Gewinn!"
                description = f"{interaction.user.mention} hat **+{profit} {currency}** gewonnen!"
                color = themes.get_theme_color(self.theme_id, 'success') if self.theme_id else discord.Color.green()
            elif profit < 0:
                title = "💥 Mines Verlust"
                description = f"{interaction.user.mention} hat eine Mine getroffen!"
                color = themes.get_theme_color(self.theme_id, 'danger') if self.theme_id else discord.Color.red()
            else:
                title = f"{mines_emoji} Mines Spiel"
                description = f"{interaction.user.mention} hat Mines gespielt!"
                color = themes.get_theme_color(self.theme_id, 'primary') if self.theme_id else discord.Color.blue()
            
            embed = discord.Embed(title=title, description=description, color=color)
            
            embed.add_field(
                name="📊 Statistik",
                value=f"Aufgedeckt: **{revealed_count}** Felder\nMultiplikator: **{multiplier:.2f}x**",
                inline=True
            )
            
            embed.add_field(
                name="💰 Ergebnis",
                value=f"**{'+' if profit >= 0 else ''}{profit} {currency}**",
                inline=True
            )
            
            embed.set_footer(text=f"Gespielt von {interaction.user.display_name}")
        
        elif self.game_type == "tower":
            data = self.result_data
            profit = data.get('profit', 0)
            floor = data.get('floor', 0)
            max_floors = data.get('max_floors', 10)
            difficulty = data.get('difficulty', 1)
            
            # Get themed tower name
            tower_name = themes.get_theme_asset(self.theme_id, 'tower_name') if self.theme_id else '🗼 Tower'
            
            if profit > 0:
                title = f"{tower_name} Gewinn!"
                description = f"{interaction.user.mention} hat **+{profit} {currency}** gewonnen!"
                color = themes.get_theme_color(self.theme_id, 'success') if self.theme_id else discord.Color.gold()
            elif profit < 0:
                title = "💥 Tower Verlust"
                description = f"{interaction.user.mention} ist im Tower gestürzt!"
                color = themes.get_theme_color(self.theme_id, 'danger') if self.theme_id else discord.Color.red()
            else:
                title = f"{tower_name} Spiel"
                description = f"{interaction.user.mention} hat Tower gespielt!"
                color = themes.get_theme_color(self.theme_id, 'primary') if self.theme_id else discord.Color.blue()
            
            embed = discord.Embed(title=title, description=description, color=color)
            
            difficulty_emoji = '⭐' * difficulty
            embed.add_field(
                name="📊 Statistik",
                value=f"Etage: **{floor}/{max_floors}**\nSchwierigkeit: {difficulty_emoji}",
                inline=True
            )
            
            embed.add_field(
                name="💰 Ergebnis",
                value=f"**{'+' if profit >= 0 else ''}{profit} {currency}**",
                inline=True
            )
            
            embed.set_footer(text=f"Gespielt von {interaction.user.display_name}")
        
        else:
            # Generic share
            net_result = self.result_data.get('profit', self.result_data.get('net_result', 0))
            title = f"🎰 {self.game_type.capitalize()} Ergebnis"
            description = f"{interaction.user.mention} hat **{'+' if net_result >= 0 else ''}{net_result} {currency}** {'gewonnen' if net_result > 0 else 'verloren'}!"
            if net_result > 0:
                color = themes.get_theme_color(self.theme_id, 'success') if self.theme_id else discord.Color.gold()
            else:
                color = themes.get_theme_color(self.theme_id, 'danger') if self.theme_id else discord.Color.red()
            
            embed = discord.Embed(title=title, description=description, color=color)
            embed.set_footer(text=f"Gespielt von {interaction.user.display_name}")
        
        # Send to channel
        await interaction.channel.send(embed=embed)
        
        # Disable share button after sharing
        button.disabled = True
        button.label = "Geteilt! ✅"
        await interaction.edit_original_response(view=self)


class RouletteView(discord.ui.View):
    """Interactive view for Roulette with dropdown menus."""
    
    def __init__(self, user_id: int, bet_amount: int, theme_id=None):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.bet_amount = bet_amount
        self.bets = []  # List of (bet_type, bet_value) tuples
        self.theme_id = theme_id
        
        # Add bet type dropdown
        self.add_item(RouletteBetTypeSelect(self))
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Das ist nicht dein Spiel!", ephemeral=True)
            return False
        return True
    
    @discord.ui.button(label="🎰 Rad drehen", style=discord.ButtonStyle.success, row=2)
    async def spin_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Spin the roulette wheel with animation."""
        await interaction.response.defer()
        
        if not self.bets:
            await interaction.followup.send("❌ Wähle mindestens eine Wette aus!", ephemeral=True)
            return
        
        # Create animation frames
        import asyncio
        
        # Get themed roulette wheel emoji
        roulette_emoji = themes.get_theme_asset(self.theme_id, 'roulette_wheel') if self.theme_id else '🎰'
        
        # Show spinning animation
        spin_frames = [
            f"{roulette_emoji} Das Rad dreht sich... ⚪",
            f"{roulette_emoji} Das Rad dreht sich... 🔴",
            f"{roulette_emoji} Das Rad dreht sich... ⚫",
            f"{roulette_emoji} Das Rad dreht sich... 🔴",
            f"{roulette_emoji} Das Rad dreht sich... ⚪",
        ]
        
        embed = discord.Embed(
            title=f"{roulette_emoji} Roulette",
            description=spin_frames[0],
            color=themes.get_theme_color(self.theme_id, 'primary') if self.theme_id else discord.Color.blurple()
        )
        await interaction.edit_original_response(embed=embed, view=None)
        
        # Animate spinning
        for i, frame in enumerate(spin_frames[1:], 1):
            await asyncio.sleep(0.5)
            embed.description = frame
            try:
                await interaction.edit_original_response(embed=embed)
            except discord.HTTPException:
                pass  # Interaction might have timed out or been deleted
        
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
                # Calculate GROSS payout (total amount won including original bet)
                payout = self.bet_amount * multiplier
                total_winnings += payout
                profit = payout - self.bet_amount  # NET profit for this bet
                bet_results.append(f"✅ {bet_value}: +{profit} 🪙 ({multiplier}x)")
            else:
                bet_results.append(f"❌ {bet_value}: -{self.bet_amount} 🪙")
        
        # Calculate net result
        total_bet_amount = self.bet_amount * len(self.bets)
        net_result = total_winnings - total_bet_amount
        
        # Update balance
        stat_period = datetime.now(timezone.utc).strftime('%Y-%m')
        await db_helpers.add_balance(
            self.user_id,
            interaction.user.display_name,
            net_result,
            config,
            stat_period
        )
        
        # Get new balance
        new_balance = await db_helpers.get_balance(self.user_id)
        
        # Log transaction
        await db_helpers.log_transaction(
            self.user_id,
            'roulette',
            net_result,
            new_balance,
            f"Bets: {len(self.bets)}, Result: {result_number}"
        )
        
        # --- NEW: Influence GAMBL stock based on result ---
        try:
            won = net_result > 0
            await stock_market.record_gambling_activity(db_helpers, total_bet_amount, won, total_winnings)
        except Exception as e:
            logger.error(f"Failed to record gambling stock influence: {e}")
        
        # --- NEW: Log roulette games to database for tracking ---
        try:
            for bet_type, bet_value in self.bets:
                won, multiplier = RouletteGame.check_bet(result_number, bet_type, bet_value)
                payout = self.bet_amount * multiplier if won else 0
                
                await db_helpers.log_roulette_game(
                    self.user_id,
                    self.bet_amount,
                    bet_type,
                    bet_value,
                    result_number,
                    won,
                    payout
                )
            
            await db_helpers.update_gambling_stats(
                self.user_id,
                'roulette',
                total_bet_amount,
                total_winnings
            )
            
            await db_helpers.update_user_game_stats(
                self.user_id,
                interaction.user.display_name,
                net_result > 0,
                total_bet_amount,
                total_winnings
            )
        except Exception as e:
            logger.error(f"Failed to log roulette game stats: {e}")
        
        # Create result embed with enhanced visuals and theme support
        currency = config['modules']['economy']['currency_symbol']
        roulette_emoji = themes.get_theme_asset(self.theme_id, 'roulette_wheel') if self.theme_id else '🎰'
        
        # Determine result emoji and color for embed
        if result_number == 0:
            result_emoji = "🟢"
            embed_color = themes.get_theme_color(self.theme_id, 'success') if self.theme_id else discord.Color.green()
        elif result_number in RouletteGame.RED:
            result_emoji = "🔴"
            if total_winnings <= 0:
                embed_color = themes.get_theme_color(self.theme_id, 'danger') if self.theme_id else discord.Color.red()
            else:
                embed_color = themes.get_theme_color(self.theme_id, 'success') if self.theme_id else discord.Color.gold()
        else:
            result_emoji = "⚫"
            if total_winnings <= 0:
                embed_color = themes.get_theme_color(self.theme_id, 'warning') if self.theme_id else discord.Color.dark_grey()
            else:
                embed_color = themes.get_theme_color(self.theme_id, 'success') if self.theme_id else discord.Color.gold()
        
        embed = discord.Embed(
            title=f"{roulette_emoji} Roulette - Ergebnis",
            description=f"Das Rad hat sich gedreht...",
            color=embed_color
        )
        
        # Visual wheel representation (show result and surrounding numbers)
        wheel_display = self._create_wheel_display(result_number)
        embed.add_field(name="🎡 Rad", value=wheel_display, inline=False)
        
        # Show result prominently
        embed.add_field(
            name="🎯 Gewinnende Zahl",
            value=f"# {result_emoji} **{result_number}** {result_emoji}",
            inline=False
        )
        
        # Show bet results with better formatting
        bet_results_text = ""
        
        for bet_type, bet_value in self.bets:
            won, multiplier = RouletteGame.check_bet(result_number, bet_type, bet_value)
            
            if won:
                profit = self.bet_amount * multiplier - self.bet_amount
                bet_results_text += f"✅ **{bet_value}**: +{profit} {currency} ({multiplier}x)\n"
            else:
                bet_results_text += f"❌ **{bet_value}**: -{self.bet_amount} {currency}\n"
        
        embed.add_field(name="📊 Deine Wetten", value=bet_results_text, inline=False)
        
        # Show summary
        summary_text = f"**Einsatz:** {total_bet_amount} {currency}\n"
        summary_text += f"**Gewonnen:** {total_winnings} {currency}\n"
        
        if net_result > 0:
            summary_text += f"**Gewinn:** +{net_result} {currency} 🎉"
        elif net_result < 0:
            summary_text += f"**Verlust:** {net_result} {currency} 💸"
        else:
            summary_text += f"**Break Even** 🤝"
        
        embed.add_field(name="💰 Zusammenfassung", value=summary_text, inline=False)
        embed.add_field(name="Guthaben", value=f"{new_balance} {currency}", inline=True)
        
        # Add footer with tip
        if net_result > 0:
            embed.set_footer(text="🎊 Herzlichen Glückwunsch zum Gewinn!")
        else:
            embed.set_footer(text="Viel Glück beim nächsten Mal!")
        
        # Create share button view with theme support
        share_view = GamblingShareView(
            game_type="roulette",
            result_data={
                'result_number': result_number,
                'bets': self.bets,
                'bet_amount': self.bet_amount,
                'total_winnings': total_winnings,
                'net_result': net_result,
                'balance': new_balance
            },
            user_id=self.user_id,
            theme_id=self.theme_id
        )
        
        await interaction.edit_original_response(embed=embed, view=share_view)
        self.stop()
    
    def _create_wheel_display(self, result: int):
        """Creates a visual representation of the roulette wheel showing the result."""
        # Create a simple display showing result and 2 numbers on each side
        wheel_numbers = list(range(37))
        result_index = wheel_numbers.index(result)
        
        # Get surrounding numbers (circular)
        display_numbers = []
        for i in range(-2, 3):
            idx = (result_index + i) % len(wheel_numbers)
            display_numbers.append(wheel_numbers[idx])
        
        # Create display
        display = ""
        for i, num in enumerate(display_numbers):
            if num == result:
                # Highlight the result
                if num == 0:
                    display += f"**[🟢 {num}]** "
                elif num in RouletteGame.RED:
                    display += f"**[🔴 {num}]** "
                else:
                    display += f"**[⚫ {num}]** "
            else:
                # Show surrounding numbers
                if num == 0:
                    display += f"🟢{num} "
                elif num in RouletteGame.RED:
                    display += f"🔴{num} "
                else:
                    display += f"⚫{num} "
        
        return display


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
    
    # Check if user has casino access
    has_casino = await db_helpers.has_feature_unlock(user_id, 'casino')
    if not has_casino:
        currency = config['modules']['economy']['currency_symbol']
        price = config['modules']['economy']['shop']['features'].get('casino', 500)
        await interaction.followup.send(
            f"🎰 Du benötigst **Casino Access**, um Roulette zu spielen!\n"
            f"Kaufe es im Shop für {price} {currency} mit `/shopbuy`",
            ephemeral=True
        )
        return
    
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
    
    # Get user's theme
    user_theme = await themes.get_user_theme(db_helpers, user_id)
    
    # Create view with theme support
    view = RouletteView(user_id, bet, user_theme)
    
    # Get themed roulette wheel emoji
    roulette_emoji = themes.get_theme_asset(user_theme, 'roulette_wheel') if user_theme else '🎰'
    
    embed = discord.Embed(
        title=f"{roulette_emoji} Roulette",
        description="Wähle deine Wette(n) aus dem Dropdown-Menü. Du kannst bis zu 2 Wetten gleichzeitig platzieren!",
        color=themes.get_theme_color(user_theme, 'primary') if user_theme else discord.Color.blue()
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
        # Try to defer, but handle if interaction already expired
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.NotFound:
            logger.warning(f"Mines command interaction {interaction.id} already expired before defer")
            return
        
        user_id = interaction.user.id
        
        # Check if user has casino access
        has_casino = await db_helpers.has_feature_unlock(user_id, 'casino')
        if not has_casino:
            currency = config['modules']['economy']['currency_symbol']
            price = config['modules']['economy']['shop']['features'].get('casino', 500)
            await interaction.followup.send(
                f"🎰 Du benötigst **Casino Access**, um Mines zu spielen!\n"
                f"Kaufe es im Shop für {price} {currency} mit `/shopbuy`",
                ephemeral=True
            )
            return
        
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
        
        # Get user's theme
        user_theme = await themes.get_user_theme(db_helpers, user_id)
        
        # Create view
        view = MinesView(game, user_id, user_theme)
        embed = game.create_embed(theme_id=user_theme)
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
        except discord.HTTPException:
            pass  # Interaction might already have been responded to


class TowerOfTreasureView(discord.ui.View):
    """UI view for Tower of Treasure game with column buttons."""
    
    def __init__(self, game: TowerOfTreasureGame, user_id: int, theme_id=None):
        super().__init__(timeout=300)
        self.game = game
        self.user_id = user_id
        self.theme_id = theme_id
        self._build_buttons()
    
    def _build_buttons(self):
        """Builds clearer, numbered column buttons for the game."""
        # Add 4 column buttons with just numbers for clarity
        for col in range(4):
            button = discord.ui.Button(
                label=f"{col + 1}",
                style=discord.ButtonStyle.primary,
                custom_id=f"tower_col_{col}"
            )
            button.callback = self._create_column_callback(col)
            self.add_item(button)
        
        # Add cashout button on new row
        cashout_button = discord.ui.Button(
            label="Auszahlen",
            style=discord.ButtonStyle.success,
            custom_id="tower_cashout",
            emoji="💰",
            row=1
        )
        cashout_button.callback = self._cashout_callback
        self.add_item(cashout_button)
    
    def _create_column_callback(self, column: int):
        """Creates a callback for a column button with climbing animation."""
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("Das ist nicht dein Spiel!", ephemeral=True)
                return
            
            await interaction.response.defer()
            
            # Show climbing animation
            import asyncio
            
            # Get tower name from theme
            tower_name = themes.get_theme_asset(self.theme_id, 'tower_name') if self.theme_id else "🗼 Tower of Treasure"
            
            temp_embed = discord.Embed(
                title=tower_name,
                description=f"Klettere Säule {column + 1}... 🧗",
                color=themes.get_theme_color(self.theme_id, 'primary') if self.theme_id else discord.Color.gold()
            )
            await interaction.edit_original_response(embed=temp_embed, view=self)
            await asyncio.sleep(0.5)
            
            alive, reached_top, reward = self.game.choose_column(column)
            
            if not alive:
                # Hit a bomb - game over
                await self._finish_game(interaction, won=False, reward=0, message="💥 Du hast eine Bombe getroffen!")
            elif reached_top:
                # Reached the top!
                await self._finish_game(interaction, won=True, reward=reward, message="🎉 Du hast die Spitze erreicht!")
            else:
                # Continue climbing
                embed = self.game.create_embed(theme_id=self.theme_id)
                await interaction.edit_original_response(embed=embed, view=self)
        
        return callback
    
    async def _cashout_callback(self, interaction: discord.Interaction):
        """Handles cash out button."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Das ist nicht dein Spiel!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        reward, multiplier = self.game.cashout()
        
        if reward > 0:
            await self._finish_game(interaction, won=True, reward=reward, message=f"💰 Du hast ausgezahlt! Multiplier: {multiplier:.2f}x")
        else:
            await interaction.edit_original_response(
                content="❌ Du kannst nicht auszahlen, wenn du noch auf dem ersten Stock bist!",
                view=self
            )
    
    async def _finish_game(self, interaction: discord.Interaction, won: bool, reward: int, message: str):
        """Finishes the game and shows results with full tower visualization."""
        embed = self.game.create_embed(show_bombs=True, show_full_tower=True, theme_id=self.theme_id)
        
        currency = config['modules']['economy']['currency_symbol']
        
        # Calculate winnings (reward already includes the bet)
        winnings = reward - self.game.bet
        
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
            'tower_of_treasure',
            winnings,
            new_balance,
            f"Tower game: Floor {self.game.current_floor}/{self.game.max_floors}"
        )
        
        # Influence GAMBL stock
        try:
            payout = reward if won else 0
            await stock_market.record_gambling_activity(db_helpers, self.game.bet, won, payout)
        except Exception as e:
            logger.error(f"Failed to record gambling stock influence: {e}")
        
        # Add result field
        if won:
            embed.add_field(
                name="✅ Gewonnen!",
                value=f"{message}\n**Gewinn: +{winnings} {currency}**",
                inline=False
            )
            embed.color = themes.get_theme_color(self.theme_id, 'success') if self.theme_id else discord.Color.green()
        else:
            embed.add_field(
                name="❌ Verloren!",
                value=f"{message}\n**Verlust: -{self.game.bet} {currency}**",
                inline=False
            )
            embed.color = themes.get_theme_color(self.theme_id, 'danger') if self.theme_id else discord.Color.red()
        
        embed.add_field(name="Neues Guthaben", value=f"{new_balance} {currency}", inline=True)
        
        # Create share view with theme support
        share_view = GamblingShareView(
            game_type="tower",
            result_data={
                'profit': winnings,
                'floor': self.game.current_floor,
                'max_floors': self.game.max_floors,
                'difficulty': self.game.difficulty,
                'balance': new_balance
            },
            user_id=self.user_id,
            theme_id=self.theme_id
        )
        
        await interaction.edit_original_response(embed=embed, view=share_view)
        
        # Remove from active games
        if self.user_id in active_tower_games:
            del active_tower_games[self.user_id]
        
        self.stop()


# --- Horse Racing Game ---

@tree.command(name="horserace", description="Starte ein Pferderennen!")
@app_commands.describe(
    horses="Anzahl der Pferde (2-6, Standard: 6)"
)
async def horserace(interaction: discord.Interaction, horses: int = 6):
    """Start a horse racing game in the current channel."""
    await interaction.response.defer()
    
    try:
        global race_counter
        
        # Update quest progress for watching horses
        await quests.update_quest_progress(db_helpers, interaction.user.id, 'watch_horses', 1, config)
        
        # Check if user has casino access
        user_id = interaction.user.id
        has_casino = await db_helpers.has_feature_unlock(user_id, 'casino')
        if not has_casino:
            currency = config['modules']['economy']['currency_symbol']
            price = config['modules']['economy']['shop']['features'].get('casino', 500)
            await interaction.followup.send(
                f"🐎 Du benötigst **Casino Access**, um Pferderennen zu spielen!\n"
                f"Kaufe es im Shop für {price} {currency} mit `/shop`"
            )
            return
        
        channel_id = interaction.channel_id
        
        # Check if there's already an active race in this channel
        if channel_id in active_horse_races:
            await interaction.followup.send(
                "⚠️ Es läuft bereits ein Rennen in diesem Kanal! Bitte warte, bis es beendet ist."
            )
            return
        
        # Validate horse count
        horses = min(max(horses, 2), 6)
        
        # Create race
        race_counter += 1
        race = horse_racing.HorseRace(race_counter, horses)
        active_horse_races[channel_id] = race
        
        # Add simulated bets to make the pool more interesting
        race.add_simulated_bets()
        
        # Create betting embed
        embed = discord.Embed(
            title="🐎 Pferderennen gestartet!",
            description=f"**Rennen #{race.race_id}**\n\n"
                       f"Platziere deine Wetten! Das Rennen startet in 60 Sekunden.\n"
                       f"Verwende die Buttons unten, um auf ein Pferd zu wetten!\n\n"
                       f"💡 **Tipp:** Die Quoten aktualisieren sich während der Wettphase!",
            color=discord.Color.gold()
        )
        
        # Show horses
        for i, horse in enumerate(race.horses):
            embed.add_field(
                name=f"{horse['emoji']} {horse['name']}",
                value=f"Quote: {race.get_odds(i):.2f}x",
                inline=True
            )
        
        currency = config['modules']['economy']['currency_symbol']
        embed.add_field(
            name="💰 Wie wetten?",
            value=f"Klicke auf einen Button und gib deinen Einsatz ein ({currency})",
            inline=False
        )
        
        # Create betting view
        view = HorseRaceBettingView(race, config)
        message = await interaction.followup.send(embed=embed, view=view)
        
        # Wait for betting period with odds updates every 10 seconds
        for i in range(6):  # 6 iterations = 60 seconds
            await asyncio.sleep(10)
            
            # Calculate remaining time
            remaining_seconds = 60 - ((i + 1) * 10)
            
            # Don't update if time is up
            if remaining_seconds <= 0:
                break
            
            # Update odds display
            embed.clear_fields()
            for j, horse in enumerate(race.horses):
                total_bet_on_horse = sum(
                    bet['amount'] for bet in race.bets.values()
                    if bet['horse_index'] == j
                )
                embed.add_field(
                    name=f"{horse['emoji']} {horse['name']}",
                    value=f"Quote: {race.get_odds(j):.2f}x\nWetten: {total_bet_on_horse} {currency}",
                    inline=True
                )
            
            embed.add_field(
                name="💰 Wie wetten?",
                value=f"Klicke auf einen Button und gib deinen Einsatz ein ({currency})\n⏰ Noch **{remaining_seconds} Sekunden**!",
                inline=False
            )
            
            try:
                await message.edit(embed=embed, view=view)
            except:
                pass  # Message might have been deleted
        
        # Close betting
        race.is_betting_open = False
        
        # Check if there are any bets
        if not race.bets:
            await message.edit(content="⚠️ Keine Wetten platziert. Das Rennen wurde abgebrochen.", embed=None, view=None)
            del active_horse_races[channel_id]
            return
        
        # Update embed to show betting is closed
        view.stop()
        for item in view.children:
            item.disabled = True
        
        embed.title = "🐎 Rennen läuft!"
        embed.description = f"**Rennen #{race.race_id}**\n\nDie Wetten sind geschlossen! Das Rennen beginnt..."
        embed.clear_fields()
        
        for i, horse in enumerate(race.horses):
            total_bet_on_horse = sum(
                bet['amount'] for bet in race.bets.values()
                if bet['horse_index'] == i
            )
            embed.add_field(
                name=f"{horse['emoji']} {horse['name']}",
                value=f"Wetten: {total_bet_on_horse} {currency}\nQuote: {race.get_odds(i):.2f}x",
                inline=True
            )
        
        await message.edit(embed=embed, view=view)
        
        # Animate the race
        for frame in range(horse_racing.ANIMATION_FRAMES):
            await asyncio.sleep(horse_racing.FRAME_DELAY)
            
            # Simulate race progress
            for i in range(race.horses_count):
                if not race.finished[i]:
                    move = random.randint(0, 3)
                    race.positions[i] += move
                    
                    if race.positions[i] >= horse_racing.RACE_LENGTH:
                        race.positions[i] = horse_racing.RACE_LENGTH
                        race.finished[i] = True
                        if i not in race.finish_order:
                            race.finish_order.append(i)
            
            # Update visual
            visual = race.get_race_visual()
            embed.description = f"**Rennen #{race.race_id}**\n\n```\n{visual}\n```"
            
            try:
                await message.edit(embed=embed)
            except:
                pass  # Message might have been deleted
            
            # Check if all horses finished
            if all(race.finished):
                break
        
        # Ensure all horses have finished
        while not all(race.finished):
            for i in range(race.horses_count):
                if not race.finished[i]:
                    race.finished[i] = True
                    race.finish_order.append(i)
        
        # Calculate payouts
        payouts = race.calculate_payouts()
        
        # Update balances and save results
        for user_id, payout in payouts.items():
            bet_amount = race.bets[user_id]['amount']
            
            # Deduct original bet
            await db_helpers.add_balance(user_id, -bet_amount, "Horse Race Bet")
            
            # Add payout if won
            if payout > 0:
                await db_helpers.add_balance(user_id, payout, f"Horse Race Win (Rennen #{race.race_id})")
        
        # Save to database
        await horse_racing.save_race_result(db_helpers, race, payouts)
        
        # Show results
        winner_index = race.finish_order[0]
        winner_horse = race.horses[winner_index]
        
        result_embed = discord.Embed(
            title="🏁 Rennen beendet!",
            description=f"**Rennen #{race.race_id}**\n\n"
                       f"**Gewinner:** {winner_horse['emoji']} **{winner_horse['name']}**!",
            color=winner_horse['color']
        )
        
        # Show final standings
        standings = ""
        for place, idx in enumerate(race.finish_order, 1):
            horse = race.horses[idx]
            standings += f"{place}. {horse['emoji']} {horse['name']}\n"
        
        result_embed.add_field(
            name="📊 Endergebnis",
            value=standings,
            inline=False
        )
        
        # Show special abilities triggered
        ability_summary = race.get_ability_summary()
        if ability_summary and "No special abilities" not in ability_summary:
            result_embed.add_field(
                name="⚡ Spezialfähigkeiten",
                value=ability_summary,
                inline=False
            )
        
        # Show winner payouts
        winner_list = []
        loser_list = []
        
        for uid, payout in payouts.items():
            try:
                user = await client.fetch_user(uid)
                bet_amount = race.bets[uid]['amount']
                
                if payout > 0:
                    profit = payout - bet_amount
                    winner_list.append(f"• {user.mention}: +{profit} {currency} (Quote: {race.get_odds(winner_index):.2f}x)")
                else:
                    loser_list.append(f"• {user.mention}: -{bet_amount} {currency}")
            except:
                pass
        
        if winner_list:
            result_embed.add_field(
                name="🎉 Gewinner",
                value="\n".join(winner_list) if winner_list else "Niemand",
                inline=False
            )
        
        if loser_list:
            # Truncate at complete entries to avoid breaking Discord formatting
            loser_text = "\n".join(loser_list)
            if len(loser_text) > 1024:
                # Find last complete entry that fits
                truncated = []
                current_length = 0
                for entry in loser_list:
                    if current_length + len(entry) + 1 > 1024:  # +1 for newline
                        break
                    truncated.append(entry)
                    current_length += len(entry) + 1
                loser_text = "\n".join(truncated)
                if len(loser_list) - len(truncated) > 0:
                    loser_text += f"\n... und {len(loser_list) - len(truncated)} weitere"
            
            result_embed.add_field(
                name="😢 Verloren",
                value=loser_text if loser_text else "Niemand",
                inline=False
            )
        
        await message.edit(embed=result_embed, view=None)
        
        # Clean up
        del active_horse_races[channel_id]
        
    except Exception as e:
        logger.error(f"Error in horse race command: {e}", exc_info=True)
        await interaction.followup.send(f"Ein Fehler ist aufgetreten: {e}")
        
        # Clean up on error
        if channel_id in active_horse_races:
            del active_horse_races[channel_id]


class HorseRaceBettingView(discord.ui.View):
    """View for placing bets on horses."""
    
    def __init__(self, race: horse_racing.HorseRace, config: dict):
        super().__init__(timeout=60)
        self.race = race
        self.config = config
        
        # Create button for each horse
        for i, horse in enumerate(race.horses):
            button = discord.ui.Button(
                label=f"{horse['emoji']} {horse['name']}",
                style=discord.ButtonStyle.primary,
                custom_id=f"horse_{i}"
            )
            button.callback = self.create_bet_callback(i)
            self.add_item(button)
    
    def create_bet_callback(self, horse_index: int):
        """Create callback for betting on a specific horse."""
        async def callback(interaction: discord.Interaction):
            # Show modal for bet amount
            modal = HorseRaceBetModal(self.race, horse_index, self.config)
            await interaction.response.send_modal(modal)
        return callback


class HorseRaceBetModal(discord.ui.Modal, title="Platziere deine Wette"):
    """Modal for entering bet amount."""
    
    def __init__(self, race: horse_racing.HorseRace, horse_index: int, config: dict):
        super().__init__()
        self.race = race
        self.horse_index = horse_index
        self.config = config
        
        horse = race.horses[horse_index]
        self.title = f"Wette auf {horse['name']}"
        
        # Bet amount input
        self.bet_input = discord.ui.TextInput(
            label="Einsatz",
            placeholder="Gib deinen Einsatz ein...",
            required=True,
            max_length=10
        )
        self.add_item(self.bet_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            bet_amount = int(self.bet_input.value)
            
            if bet_amount <= 0:
                await interaction.response.send_message(
                    "❌ Der Einsatz muss positiv sein!",
                    ephemeral=True
                )
                return
            
            # Check balance
            user_id = interaction.user.id
            balance = await db_helpers.get_balance(user_id)
            
            if balance < bet_amount:
                currency = self.config['modules']['economy']['currency_symbol']
                await interaction.response.send_message(
                    f"❌ Nicht genug Guthaben! Du hast {balance} {currency}.",
                    ephemeral=True
                )
                return
            
            # Place bet
            success, message = self.race.place_bet(user_id, self.horse_index, bet_amount)
            
            if success:
                horse = self.race.horses[self.horse_index]
                odds = self.race.get_odds(self.horse_index)
                currency = self.config['modules']['economy']['currency_symbol']
                
                await interaction.response.send_message(
                    f"✅ Wette platziert!\n"
                    f"**Pferd:** {horse['emoji']} {horse['name']}\n"
                    f"**Einsatz:** {bet_amount} {currency}\n"
                    f"**Aktuelle Quote:** {odds:.2f}x\n"
                    f"**Möglicher Gewinn:** {int(bet_amount * odds)} {currency}",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"❌ {message}",
                    ephemeral=True
                )
        
        except ValueError:
            await interaction.response.send_message(
                "❌ Ungültiger Einsatz! Gib eine Zahl ein.",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error placing bet: {e}", exc_info=True)
            await interaction.response.send_message(
                f"❌ Ein Fehler ist aufgetreten: {e}",
                ephemeral=True
            )


@tree.command(name="tower", description="Spiele Tower of Treasure - Klettere den Turm hinauf!")
@app_commands.describe(
    bet="Dein Einsatz",
    difficulty="Schwierigkeit (1=Einfach, 2=Mittel, 3=Schwer, 4=Extrem)"
)
@app_commands.choices(difficulty=[
    app_commands.Choice(name="⭐ Einfach (3 sichere, 1 Bombe)", value=1),
    app_commands.Choice(name="⭐⭐ Mittel (2 sichere, 2 Bomben)", value=2),
    app_commands.Choice(name="⭐⭐⭐ Schwer (1 sicher, 3 Bomben)", value=3),
    app_commands.Choice(name="⭐⭐⭐⭐ Extrem (0-1 sicher, 3-4 Bomben)", value=4)
])
async def tower(interaction: discord.Interaction, bet: int, difficulty: int = 1):
    """Start a Tower of Treasure game."""
    try:
        await interaction.response.defer(ephemeral=True)
        
        user_id = interaction.user.id
        
        # Check if user has casino access
        has_casino = await db_helpers.has_feature_unlock(user_id, 'casino')
        if not has_casino:
            currency = config['modules']['economy']['currency_symbol']
            price = config['modules']['economy']['shop']['features'].get('casino', 500)
            await interaction.followup.send(
                f"🎰 Du benötigst **Casino Access**, um Tower of Treasure zu spielen!\n"
                f"Kaufe es im Shop für {price} {currency} mit `/shopbuy`",
                ephemeral=True
            )
            return
        
        # Check if user already has an active game
        if user_id in active_tower_games:
            await interaction.followup.send("Du hast bereits ein aktives Tower-Spiel!", ephemeral=True)
            return
        
        # Validate bet amount
        min_bet = config['modules']['economy']['games']['tower_of_treasure']['min_bet']
        max_bet = config['modules']['economy']['games']['tower_of_treasure']['max_bet']
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
            logger.error(f"Error getting balance for user {user_id} in tower command: {e}")
            await interaction.followup.send(
                "❌ Fehler beim Abrufen deines Guthabens.",
                ephemeral=True
            )
            return
        
        if balance < bet:
            await interaction.followup.send(
                f"Nicht genug Guthaben! Du hast {balance} {currency}, brauchst aber {bet} {currency}.",
                ephemeral=True
            )
            return
        
        # Deduct bet
        stat_period = datetime.now(timezone.utc).strftime('%Y-%m')
        await db_helpers.add_balance(
            user_id,
            interaction.user.display_name,
            -bet,
            config,
            stat_period
        )
        
        new_balance = await db_helpers.get_balance(user_id)
        
        # Log transaction
        await db_helpers.log_transaction(
            user_id,
            'tower_of_treasure',
            -bet,
            new_balance,
            f"Tower game started (difficulty {difficulty})"
        )
        
        # Create game
        max_floors = config['modules']['economy']['games']['tower_of_treasure']['max_floors']
        game = TowerOfTreasureGame(user_id, bet, difficulty, max_floors)
        
        # Store in active games
        active_tower_games[user_id] = game
        
        # Get user's theme
        user_theme = await themes.get_user_theme(db_helpers, user_id)
        
        # Create view
        view = TowerOfTreasureView(game, user_id, user_theme)
        
        # Create embed
        embed = game.create_embed(theme_id=user_theme)
        embed.set_footer(text=f"Guthaben: {new_balance} {currency}")
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error in tower command: {e}", exc_info=True)
        try:
            await interaction.followup.send(
                "❌ Ein Fehler ist aufgetreten. Bitte versuche es später erneut.",
                ephemeral=True
            )
        except discord.HTTPException:
            pass  # Interaction might have timed out or been deleted


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
        
        # Show cylinder spin animation
        import asyncio
        temp_embed = discord.Embed(
            title="🔫 Russian Roulette",
            description="Der Zylinder dreht sich... 🔄",
            color=discord.Color.orange()
        )
        await interaction.edit_original_response(embed=temp_embed, view=self)
        await asyncio.sleep(0.8)
        
        # Show aiming animation
        temp_embed.description = "Abzug wird gezogen... 😰"
        await interaction.edit_original_response(embed=temp_embed, view=self)
        await asyncio.sleep(0.5)
        
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
            
            # --- NEW: Log game to database for tracking ---
            try:
                await db_helpers.log_russian_roulette_game(
                    self.user_id,
                    self.entry_fee,
                    self.game.current_shot - 1,  # shots survived
                    False,  # survived
                    0  # payout
                )
                
                await db_helpers.update_gambling_stats(
                    self.user_id,
                    'russian_roulette',
                    self.entry_fee,
                    0
                )
                
                await db_helpers.update_user_game_stats(
                    self.user_id,
                    interaction.user.display_name,
                    False,
                    self.entry_fee,
                    0
                )
            except Exception as e:
                logger.error(f"Failed to log russian roulette game stats: {e}")
            
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
            
            # --- NEW: Log game to database for tracking ---
            try:
                await db_helpers.log_russian_roulette_game(
                    self.user_id,
                    self.entry_fee,
                    6,  # shots survived
                    True,  # survived
                    reward  # payout
                )
                
                await db_helpers.update_gambling_stats(
                    self.user_id,
                    'russian_roulette',
                    self.entry_fee,
                    reward
                )
                
                await db_helpers.update_user_game_stats(
                    self.user_id,
                    interaction.user.display_name,
                    True,
                    self.entry_fee,
                    reward
                )
            except Exception as e:
                logger.error(f"Failed to log russian roulette game stats: {e}")
            
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
            
            # --- NEW: Log game to database for tracking ---
            try:
                await db_helpers.log_russian_roulette_game(
                    self.user_id,
                    self.entry_fee,
                    self.game.current_shot,  # shots survived
                    True,  # survived
                    reward  # payout
                )
                
                await db_helpers.update_gambling_stats(
                    self.user_id,
                    'russian_roulette',
                    self.entry_fee,
                    reward
                )
                
                await db_helpers.update_user_game_stats(
                    self.user_id,
                    interaction.user.display_name,
                    True,
                    self.entry_fee,
                    reward
                )
            except Exception as e:
                logger.error(f"Failed to log russian roulette game stats: {e}")
            
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
from modules import trolly_problem

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
    
    async def on_timeout(self):
        """Handle view timeout - clear the active game."""
        if self.user_id in active_detective_games:
            del active_detective_games[self.user_id]
            logger.info(f"Detective game timed out for user {self.user_id}, cleared active game")
    
    def create_case_embed(self):
        """Create the main case embed."""
        difficulty = getattr(self.case, 'difficulty', 1)
        
        embed = discord.Embed(
            title=f"🔍 {self.case.case_title}",
            description=self.case.case_description,
            color=discord.Color.dark_blue()
        )
        
        # Show difficulty level
        difficulty_emoji = "⭐" * difficulty
        embed.add_field(
            name="🎯 Schwierigkeitsgrad",
            value=f"{difficulty_emoji} (Stufe {difficulty}/5)",
            inline=False
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
        
        # Evidence - hide some based on difficulty
        if self.case.evidence:
            if difficulty <= 2:
                # Easy/Medium: Show all evidence
                evidence_text = "\n".join(self.case.evidence)
            else:
                # Hard: Show only first evidence, rest needs investigation
                visible_count = max(1, len(self.case.evidence) - (difficulty - 2))
                evidence_text = "\n".join(self.case.evidence[:visible_count])
                if visible_count < len(self.case.evidence):
                    evidence_text += f"\n\n*🔒 {len(self.case.evidence) - visible_count} weitere Beweise müssen untersucht werden*"
            
            embed.add_field(
                name="🔬 Beweise",
                value=evidence_text,
                inline=False
            )
        
        # Hints - hide based on difficulty
        if hasattr(self.case, 'hints') and self.case.hints:
            if difficulty <= 1:
                # Easy: Show all hints clearly
                hints_text = "\n".join(self.case.hints)
            elif difficulty <= 3:
                # Medium: Show hints but hint they're cryptic
                hints_text = "\n".join(self.case.hints)
            else:
                # Hard: Show only first hint
                hints_text = self.case.hints[0] if self.case.hints else "Keine Hinweise verfügbar"
                if len(self.case.hints) > 1:
                    hints_text += f"\n\n*🔒 {len(self.case.hints) - 1} weitere Hinweise durch Untersuchung aufdecken*"
            
            embed.add_field(
                name="💡 Hinweise",
                value=hints_text,
                inline=False
            )
        
        # Suspects list - show only basic info
        suspects_list = "\n".join([
            f"{i+1}. **{s['name']}** - {s['occupation']}"
            for i, s in enumerate(self.case.suspects)
        ])
        
        # Show investigation progress
        if self.investigated_suspects:
            investigated_names = [self.case.suspects[i]['name'] for i in self.investigated_suspects]
            suspects_list += f"\n\n✅ Untersucht: {', '.join(investigated_names)}"
        
        embed.add_field(
            name="👥 Verdächtige",
            value=suspects_list,
            inline=False
        )
        
        embed.set_footer(text="🔍 Untersuche die Verdächtigen um mehr Informationen zu erhalten!")
        
        return embed
    
    def create_suspect_embed(self, suspect_index: int):
        """Create embed showing suspect details."""
        suspect = self.case.get_suspect(suspect_index)
        if not suspect:
            return None
        
        difficulty = getattr(self.case, 'difficulty', 1)
        
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
        
        # Reveal additional evidence/hints when investigating (for higher difficulties)
        if difficulty >= 3 and len(self.investigated_suspects) > 0:
            # Reveal hidden evidence after investigating suspects
            evidence_count = len(self.case.evidence)
            visible_count = max(1, evidence_count - (difficulty - 2))
            
            if len(self.investigated_suspects) >= 2 and evidence_count > visible_count:
                extra_evidence_idx = visible_count + len(self.investigated_suspects) - 2
                if extra_evidence_idx < evidence_count:
                    embed.add_field(
                        name="🔬 Neuer Beweis entdeckt!",
                        value=self.case.evidence[extra_evidence_idx],
                        inline=False
                    )
        
        # Show hint unlock progress
        num_investigated = len(self.investigated_suspects)
        if difficulty >= 4 and num_investigated >= 2 and len(self.case.hints) > 1:
            hint_idx = min(num_investigated - 1, len(self.case.hints) - 1)
            if hint_idx < len(self.case.hints):
                embed.add_field(
                    name="💡 Hinweis aufgedeckt!",
                    value=self.case.hints[hint_idx],
                    inline=False
                )
        
        investigations_left = 4 - num_investigated
        if investigations_left > 0:
            embed.set_footer(text=f"Untersuche weitere {investigations_left} Verdächtige für mehr Hinweise!")
        else:
            embed.set_footer(text="Alle Verdächtigen untersucht. Zeit für eine Anklage!")
        
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
        
        # Mark case as completed in database
        if self.case.case_id:
            await detective_game.mark_case_completed(db_helpers, interaction.user.id, self.case.case_id, is_correct)
        
        # Update user stats and difficulty
        await detective_game.update_user_stats(db_helpers, interaction.user.id, is_correct)
        
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
            
            # Get user's new difficulty level
            new_difficulty = await detective_game.get_user_difficulty(db_helpers, interaction.user.id)
            
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
            if new_difficulty > self.case.difficulty:
                embed.add_field(
                    name="🎯 Schwierigkeitsgrad erhöht!",
                    value=f"Deine Fähigkeiten verbessern sich! Nächster Fall: Stufe {new_difficulty}/5",
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
        
        # Check if user has detective access
        has_detective = await db_helpers.has_feature_unlock(user_id, 'detective')
        if not has_detective:
            currency = config['modules']['economy']['currency_symbol']
            price = config['modules']['economy']['shop']['features'].get('detective', 1000)
            await interaction.followup.send(
                f"🔍 Du benötigst **Detective Game Access**, um Fälle zu lösen!\n"
                f"Kaufe es im Shop für {price} {currency} mit `/shopbuy`",
                ephemeral=True
            )
            return
        
        # Check if user already has an active game
        if user_id in active_detective_games:
            await interaction.followup.send("Du hast bereits einen aktiven Fall!", ephemeral=True)
            return
        
        # Get or generate a case for the user
        case = await detective_game.get_or_generate_case(
            db_helpers,
            api_helpers,
            config,
            GEMINI_API_KEY,
            OPENAI_API_KEY,
            user_id
        )
        
        # Mark case as started if it has an ID
        if case.case_id:
            await detective_game.mark_case_started(db_helpers, user_id, case.case_id)
        
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


# --- Trolly Problem Game View ---

class TrollyProblemView(discord.ui.View):
    """UI view for Trolly Problem dilemmas."""
    
    def __init__(self, problem: trolly_problem.TrollyProblem, user_id: int, user_name: str):
        super().__init__(timeout=180)  # 3 minutes to decide
        self.problem = problem
        self.user_id = user_id
        self.user_name = user_name
        self.choice_made = False
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Das ist nicht dein Dilemma!", ephemeral=True)
            return False
        return True
    
    @discord.ui.button(label="Option A", style=discord.ButtonStyle.danger, emoji="🅰️")
    async def option_a_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_choice(interaction, 'a')
    
    @discord.ui.button(label="Option B", style=discord.ButtonStyle.primary, emoji="🅱️")
    async def option_b_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_choice(interaction, 'b')
    
    async def _handle_choice(self, interaction: discord.Interaction, choice: str):
        """Handle user's choice."""
        if self.choice_made:
            await interaction.response.send_message("Du hast bereits gewählt!", ephemeral=True)
            return
        
        self.choice_made = True
        await interaction.response.defer()
        
        # Save the response
        await trolly_problem.save_trolly_response(
            db_helpers,
            self.user_id,
            self.user_name,
            self.problem.problem_id,
            choice,
            self.problem.scenario
        )
        
        # Create result embed
        chosen_option = self.problem.option_a if choice == 'a' else self.problem.option_b
        other_option = self.problem.option_b if choice == 'a' else self.problem.option_a
        
        embed = discord.Embed(
            title="⚖️ Deine Wahl wurde registriert",
            description=f"Du hast gewählt: **Option {choice.upper()}**",
            color=discord.Color.dark_red() if choice == 'a' else discord.Color.blue()
        )
        
        embed.add_field(
            name="Deine Entscheidung",
            value=chosen_option,
            inline=False
        )
        
        embed.add_field(
            name="Du hast abgelehnt",
            value=other_option,
            inline=False
        )
        
        # Get global statistics for this problem if it has an ID
        if self.problem.problem_id:
            problem_stats = await trolly_problem.get_problem_statistics(db_helpers, self.problem.problem_id)
            if problem_stats and problem_stats['total_responses'] > 0:
                # Create a visual bar for the percentages
                percent_a = problem_stats['percent_a']
                percent_b = problem_stats['percent_b']
                
                # Create progress bars
                bar_length = 20
                filled_a = int((percent_a / 100) * bar_length)
                filled_b = int((percent_b / 100) * bar_length)
                bar_a = '█' * filled_a + '░' * (bar_length - filled_a)
                bar_b = '█' * filled_b + '░' * (bar_length - filled_b)
                
                embed.add_field(
                    name="🌍 Wie haben andere entschieden?",
                    value=f"**Option A**: {percent_a}% ({problem_stats['chose_a']} Spieler)\n"
                          f"`{bar_a}`\n\n"
                          f"**Option B**: {percent_b}% ({problem_stats['chose_b']} Spieler)\n"
                          f"`{bar_b}`",
                    inline=False
                )
        
        # Get user stats
        stats = await trolly_problem.get_user_trolly_stats(db_helpers, self.user_id)
        if stats and stats['total_responses'] > 1:
            embed.add_field(
                name="📊 Deine Trolly-Statistiken",
                value=f"Gesamt beantwortet: `{stats['total_responses']}`\n"
                      f"Option A gewählt: `{stats['chose_a']}`\n"
                      f"Option B gewählt: `{stats['chose_b']}`",
                inline=False
            )
        
        embed.set_footer(text="Es gibt keine richtige Antwort. Oder vielleicht doch? 🤔")
        
        # Disable buttons
        for item in self.children:
            item.disabled = True
        
        await interaction.edit_original_response(embed=embed, view=self)


@tree.command(name="trolly", description="Stelle dich einem moralischen Dilemma!")
async def trolly(interaction: discord.Interaction):
    """Present user with a personalized trolley problem."""
    await interaction.response.defer(ephemeral=True)
    
    try:
        user_id = interaction.user.id
        display_name = interaction.user.display_name
        
        # Check if user has trolly access
        has_trolly = await db_helpers.has_feature_unlock(user_id, 'trolly')
        if not has_trolly:
            currency = config['modules']['economy']['currency_symbol']
            price = config['modules']['economy']['shop']['features'].get('trolly', 250)
            await interaction.followup.send(
                f"🚃 Du benötigst **Trolly Problem Access**, um dieses Feature zu nutzen!\n"
                f"Kaufe es im Shop für {price} {currency} mit `/shopbuy`",
                ephemeral=True
            )
            return
        
        # Gather user data for personalization
        user_data = await trolly_problem.gather_user_data_for_trolly(
            db_helpers,
            user_id,
            display_name
        )
        
        # Fetch server bestie name if we have an ID
        if user_data.get('server_bestie_id'):
            try:
                bestie = await client.fetch_user(int(user_data['server_bestie_id']))
                user_data['server_bestie'] = bestie.display_name
            except (discord.HTTPException, discord.NotFound, ValueError):
                pass  # User not found or invalid ID
        
        # Get or generate the trolly problem (from database or AI)
        problem = await trolly_problem.get_or_generate_trolly_problem(
            db_helpers,
            api_helpers,
            config,
            GEMINI_API_KEY,
            OPENAI_API_KEY,
            user_id,
            user_data
        )
        
        # Create embed
        embed = discord.Embed(
            title="⚖️ Das Trolly-Problem",
            description=problem.scenario,
            color=discord.Color.dark_purple()
        )
        
        embed.add_field(
            name="🅰️ Option A",
            value=problem.option_a,
            inline=False
        )
        
        embed.add_field(
            name="🅱️ Option B",
            value=problem.option_b,
            inline=False
        )
        
        if problem.personalization_level == "personalized":
            embed.set_footer(text="✨ Dieses Dilemma wurde basierend auf deinen Daten personalisiert!")
        else:
            embed.set_footer(text="💡 Spiele mehr, um personalisierte Dilemmata zu erhalten!")
        
        # Create view
        view = TrollyProblemView(problem, user_id, display_name)
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error in trolly command: {e}", exc_info=True)
        await interaction.followup.send(
            f"❌ Fehler beim Generieren des Trolly-Problems: {str(e)}",
            ephemeral=True
        )


# --- Word Find Game View ---

class WordFindView(discord.ui.View):
    """UI view for Word Find game with guess input."""
    
    def __init__(self, user_id: int, word_data: dict, max_attempts: int, has_premium: bool = False, game_type: str = 'daily', theme_id=None):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.word_data = word_data
        self.max_attempts = max_attempts
        self.has_premium = has_premium
        self.game_type = game_type
        self.theme_id = theme_id
    
    @discord.ui.button(label="Wort raten", style=discord.ButtonStyle.primary, emoji="🔍")
    async def guess_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle guess button click."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Das ist nicht dein Spiel!", ephemeral=True)
            return
        
        # Create modal for input
        modal = WordGuessModal(self.user_id, self.word_data, self.max_attempts, self.has_premium, self.game_type, self.theme_id)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Aufgeben", style=discord.ButtonStyle.danger, emoji="❌")
    async def give_up_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle give up button."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Das ist nicht dein Spiel!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Show the correct word
        correct_word = self.word_data['word']
        
        embed = discord.Embed(
            title="❌ Aufgegeben!",
            description=f"Das gesuchte Wort war: **{correct_word.upper()}**",
            color=discord.Color.red()
        )
        
        # Update stats (loss)
        await word_find.update_user_stats(db_helpers, self.user_id, False, self.max_attempts, self.game_type)
        
        # Mark premium game as completed if applicable
        if self.game_type == 'premium':
            await word_find.complete_premium_game(db_helpers, self.word_data['id'], False)
        
        # Get stats
        user_stats = await word_find.get_user_stats(db_helpers, self.user_id)
        if user_stats:
            embed.add_field(
                name="📊 Deine Statistiken",
                value=f"Spiele: `{user_stats['total_games']}` | Gewonnen: `{user_stats['total_wins']}`\n"
                      f"Streak verloren! 💔",
                inline=False
            )
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        await interaction.edit_original_response(embed=embed, view=self)


class WordFindCompletedView(discord.ui.View):
    """UI view for completed Word Find game with share and new game options."""
    
    def __init__(self, user_id: int, attempts: list, won: bool, has_premium: bool = False, game_type: str = 'daily'):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.attempts = attempts
        self.won = won
        self.has_premium = has_premium
        self.game_type = game_type
        
        # Only show new game button for premium users on daily games
        if not has_premium or game_type != 'daily':
            self.remove_item(self.new_game_button)
    
    @discord.ui.button(label="Teilen", style=discord.ButtonStyle.success, emoji="📤", row=0)
    async def share_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle share button click."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Das ist nicht dein Spiel!", ephemeral=True)
            return
        
        # Create shareable text
        share_text = word_find.create_share_text(self.attempts, self.won, self.game_type)
        
        await interaction.response.send_message(
            f"Teile dein Ergebnis:\n\n```\n{share_text}\n```",
            ephemeral=True
        )
    
    @discord.ui.button(label="Neues Spiel", style=discord.ButtonStyle.primary, emoji="🎮", row=0)
    async def new_game_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle new game button click (premium only)."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Das ist nicht dein Spiel!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Get user's language preference
        user_lang = await db_helpers.get_user_language(self.user_id)
        
        # Create new premium game
        premium_game = await word_find.create_premium_game(db_helpers, self.user_id, user_lang)
        
        if not premium_game:
            await interaction.followup.send("❌ Fehler beim Erstellen eines neuen Spiels.", ephemeral=True)
            return
        
        # Get user stats
        user_stats = await word_find.get_user_stats(db_helpers, self.user_id)
        
        # Get user's theme
        user_theme = await themes.get_user_theme(db_helpers, self.user_id)
        
        # Create new game embed
        embed = word_find.create_game_embed(premium_game, [], 20, user_stats, 'premium', user_theme)
        embed.set_footer(text="💎 Premium Spiel - Du hast 20 Versuche!")
        
        # Create view for new game
        view = WordFindView(self.user_id, premium_game, 20, self.has_premium, 'premium', user_theme)
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


class WordGuessModal(discord.ui.Modal, title="Rate das Wort"):
    """Modal for entering word guess."""
    
    guess_input = discord.ui.TextInput(
        label="Dein Ratewort",
        placeholder="Gib dein Wort ein...",
        min_length=2,
        max_length=50,
        required=True
    )
    
    def __init__(self, user_id: int, word_data: dict, max_attempts: int, has_premium: bool, game_type: str = 'daily', theme_id=None):
        super().__init__()
        self.user_id = user_id
        self.word_data = word_data
        self.max_attempts = max_attempts
        self.has_premium = has_premium
        self.game_type = game_type
        self.theme_id = theme_id
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle word guess submission."""
        try:
            await interaction.response.defer(ephemeral=True)
            
            guess = self.guess_input.value.lower().strip()
            correct_word = self.word_data['word'].lower()
            word_id = self.word_data['id']
            
            # Get user's language preference
            user_lang = self.word_data.get('language', 'de')
            
            # Validate that the guess is a real word from the word pool
            if not word_find.is_valid_guess(guess, user_lang):
                await interaction.followup.send(
                    "❌ Dieses Wort ist nicht im Wortpool! Bitte gib ein gültiges Wort ein.",
                    ephemeral=True
                )
                return
            
            # Get current attempts based on game type
            attempts = await word_find.get_user_attempts(db_helpers, self.user_id, word_id, self.game_type)
            
            attempt_num = len(attempts) + 1
            
            # Check if already guessed this word
            if any(a['guess'].lower() == guess for a in attempts):
                await interaction.followup.send("Du hast dieses Wort bereits geraten!", ephemeral=True)
                return
            
            # Check if max attempts reached
            if attempt_num > self.max_attempts:
                await interaction.followup.send("Du hast alle Versuche aufgebraucht!", ephemeral=True)
                return
            
            # Calculate similarity with theme context for better semantic matching
            theme_id = self.word_data.get('theme_id')
            similarity = word_find.calculate_word_similarity(guess, correct_word, use_context=True, theme_id=theme_id, language=user_lang)
            
            # Record attempt with game type
            record_success = await word_find.record_attempt(db_helpers, self.user_id, word_id, guess, similarity, attempt_num, self.game_type)
            
            # Track if we're in fallback mode (database save failed)
            db_save_failed = not record_success
            
            # Update quest progress for attempting daily word find (on first attempt only)
            if self.game_type == 'daily' and attempt_num == 1:
                await quests.update_quest_progress(db_helpers, self.user_id, 'daily_word_attempt', 1, config)
            
            # Check if correct
            if guess == correct_word:
                # Win!
                # Calculate rewards based on attempts (fewer attempts = better rewards)
                base_xp = 40
                base_money = 20
                bonus_multiplier = max(1.0, (self.max_attempts - attempt_num + 1) / self.max_attempts)
                xp_reward = int(base_xp * bonus_multiplier)
                money_reward = int(base_money * bonus_multiplier)
                
                # Give XP reward
                await db_helpers.add_xp(self.user_id, interaction.user.display_name, xp_reward)
                
                # Give money reward
                await db_helpers.add_balance(self.user_id, interaction.user.display_name, money_reward, config)
                
                embed = discord.Embed(
                    title="🎉 Glückwunsch!",
                    description=f"Du hast das Wort **{correct_word.upper()}** in {attempt_num} Versuchen erraten!\n\n"
                               f"**Belohnungen:**\n"
                               f"🎯 +{xp_reward} XP\n"
                               f"💰 +{money_reward} {config['modules']['economy']['currency_symbol']}",
                    color=discord.Color.gold()
                )
                
                # Update stats (only if database save succeeded to maintain consistency)
                if not db_save_failed:
                    await word_find.update_user_stats(db_helpers, self.user_id, True, attempt_num, self.game_type)
                
                # Quest tracking is done on first attempt (not on completion) - see line 10638
                
                # Mark premium game as completed if applicable (only if database save succeeded)
                if self.game_type == 'premium' and not db_save_failed:
                    await word_find.complete_premium_game(db_helpers, word_id, True)
                
                # Get updated stats and attempts for sharing
                user_stats = await word_find.get_user_stats(db_helpers, self.user_id)
                all_attempts = await word_find.get_user_attempts(db_helpers, self.user_id, word_id, self.game_type)
                
                # If database save failed, add the winning attempt manually
                if db_save_failed:
                    fallback_attempt = {
                        'guess': guess,
                        'similarity_score': similarity,  # Use calculated similarity for consistency
                        'attempt_number': attempt_num
                    }
                    all_attempts.append(fallback_attempt)
                
                if user_stats:
                    embed.add_field(
                        name="📊 Deine Statistiken",
                        value=f"Spiele: `{user_stats['total_games']}` | Gewonnen: `{user_stats['total_wins']}`\n"
                              f"Streak: `{user_stats['current_streak']}` 🔥 | Best: `{user_stats['best_streak']}`",
                        inline=False
                    )
                
                # Show completed view with share button (and new game button for premium users)
                view = WordFindCompletedView(self.user_id, all_attempts, True, self.has_premium, self.game_type)
                
                # Send result as new message with error handling for Discord errors
                try:
                    await interaction.followup.send(embed=embed, view=view, ephemeral=True)
                except (discord.errors.NotFound, discord.errors.HTTPException) as e:
                    # Could not send message - interaction may have expired or other Discord error
                    # The win is already recorded in the database, so just log this
                    logger.warning(f"WordFind win: Could not send result message: {e}")
            else:
                # Wrong guess - update display with new attempt
                attempts = await word_find.get_user_attempts(db_helpers, self.user_id, word_id, self.game_type)
                
                # If database save failed, add the current attempt manually so it shows in the embed
                if db_save_failed:
                    # Create a fallback attempt entry to display
                    fallback_attempt = {
                        'guess': guess,
                        'similarity_score': similarity,
                        'attempt_number': attempt_num
                    }
                    attempts.append(fallback_attempt)
                
                user_stats = await word_find.get_user_stats(db_helpers, self.user_id)
                
                embed = word_find.create_game_embed(self.word_data, attempts, self.max_attempts, user_stats, self.game_type, self.theme_id)
                
                # Add a warning if database save failed
                if db_save_failed:
                    embed.add_field(
                        name="⚠️ Hinweis",
                        value="Der Versuch konnte nicht gespeichert werden. Dein Fortschritt wird möglicherweise nicht gespeichert.",
                        inline=False
                    )
                
                # Check if max attempts reached
                if attempt_num >= self.max_attempts:
                    embed.title = "❌ Keine Versuche mehr!"
                    embed.description = f"Das gesuchte Wort war: **{correct_word.upper()}**"
                    embed.color = discord.Color.red()
                    
                    # Update stats (loss) - only if database save succeeded to maintain consistency
                    if not db_save_failed:
                        await word_find.update_user_stats(db_helpers, self.user_id, False, attempt_num, self.game_type)
                    
                    # Mark premium game as completed if applicable (only if database save succeeded)
                    if self.game_type == 'premium' and not db_save_failed:
                        await word_find.complete_premium_game(db_helpers, word_id, False)
                    
                    # Show completed view with share button (and new game button for premium users)
                    view = WordFindCompletedView(self.user_id, attempts, False, self.has_premium, self.game_type)
                    
                    # Send result as new message with error handling for Discord errors
                    try:
                        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
                    except (discord.errors.NotFound, discord.errors.HTTPException) as e:
                        # Could not send message - interaction may have expired or other Discord error
                        # The loss is already recorded in the database, so just log this
                        logger.warning(f"WordFind loss: Could not send result message: {e}")
                else:
                    # Create new view for continuing the game
                    view = WordFindView(self.user_id, self.word_data, self.max_attempts, self.has_premium, self.game_type, self.theme_id)
                    
                    # Send updated game state with feedback
                    similarity_pct = f"{similarity:.1f}%"
                    temp = "🔥 Sehr heiß!" if similarity >= 80 else "🌡️ Heiß!" if similarity >= 60 else "🌤️ Warm" if similarity >= 40 else "❄️ Kalt" if similarity >= 20 else "🧊 Sehr kalt"
                    
                    embed.add_field(
                        name="💡 Letzter Versuch",
                        value=f"**{guess}** - {similarity_pct} {temp}",
                        inline=False
                    )
                    
                    # Send with error handling for Discord errors
                    try:
                        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
                    except (discord.errors.NotFound, discord.errors.HTTPException) as e:
                        # Could not send message - interaction may have expired or other Discord error
                        # The guess is already recorded in the database, so just log this
                        logger.warning(f"WordFind guess: Could not send updated game message: {e}")
        except Exception as e:
            logger.error(f"Error in WordGuessModal.on_submit: {e}", exc_info=True)
            try:
                await interaction.followup.send(
                    "❌ Ein Fehler ist aufgetreten. Bitte versuche es erneut.",
                    ephemeral=True
                )
            except:
                pass


# --- Wordle Command and Views ---

@tree.command(name="wordle", description="Spiele Wordle - Errate das 5-Buchstaben Wort!")
async def wordle_command(interaction: discord.Interaction):
    """Play the daily Wordle game."""
    await interaction.response.defer(ephemeral=True)
    
    try:
        user_id = interaction.user.id
        
        # Check if user has premium access
        has_premium = await db_helpers.has_feature_unlock(user_id, 'unlimited_wordle')
        
        # Get user's language preference
        user_lang = await db_helpers.get_user_language(user_id)
        
        # Get today's word for user's language
        word_data = await wordle.get_or_create_daily_word(db_helpers, user_lang)
        
        if not word_data:
            await interaction.followup.send("❌ Fehler beim Laden des heutigen Wortes.", ephemeral=True)
            return
        
        # Get user's attempts for today
        attempts = await wordle.get_user_attempts(db_helpers, user_id, word_data['id'], 'daily')
        max_attempts = 6
        
        # Check if already completed today (guessed correctly)
        if any(a['guess'].lower() == word_data['word'].lower() for a in attempts):
            user_stats = await wordle.get_user_stats(db_helpers, user_id)
            
            # Get user's theme
            user_theme = await themes.get_user_theme(db_helpers, user_id)
            
            embed = discord.Embed(
                title="✅ Bereits abgeschlossen!",
                description=f"Du hast das heutige Wort **{word_data['word'].upper()}** bereits erraten!",
                color=discord.Color.green()
            )
            
            if user_stats:
                total_games = user_stats.get('total_games', 0)
                total_wins = user_stats.get('total_wins', 0)
                current_streak = user_stats.get('current_streak', 0)
                best_streak = user_stats.get('best_streak', 0)
                win_rate = (total_wins / total_games * 100) if total_games > 0 else 0
                
                embed.add_field(
                    name="📊 Deine Statistiken",
                    value=f"Spiele: `{total_games}` | Gewonnen: `{total_wins}` ({win_rate:.1f}%)\n"
                          f"Streak: `{current_streak}` 🔥 | Best: `{best_streak}`",
                    inline=False
                )
            
            if has_premium:
                embed.add_field(
                    name="💎 Premium Vorteil",
                    value="Als Premium-Nutzer kannst du zusätzliche Spiele spielen!",
                    inline=False
                )
            
            # Show share button and new game button for premium users
            view = WordleCompletedView(user_id, attempts, True, word_data, has_premium, 'daily')
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            return
        
        # Check if max attempts reached
        if len(attempts) >= max_attempts:
            correct_word = word_data['word']
            user_stats = await wordle.get_user_stats(db_helpers, user_id)
            
            # Get user's theme
            user_theme = await themes.get_user_theme(db_helpers, user_id)
            
            embed = discord.Embed(
                title="❌ Keine Versuche mehr!",
                description=f"Das gesuchte Wort war: **{correct_word.upper()}**",
                color=discord.Color.red()
            )
            
            if user_stats:
                total_games = user_stats.get('total_games', 0)
                total_wins = user_stats.get('total_wins', 0)
                win_rate = (total_wins / total_games * 100) if total_games > 0 else 0
                
                embed.add_field(
                    name="📊 Deine Statistiken",
                    value=f"Spiele: `{total_games}` | Gewonnen: `{total_wins}` ({win_rate:.1f}%)",
                    inline=False
                )
            
            if has_premium:
                embed.add_field(
                    name="💎 Premium Vorteil",
                    value="Als Premium-Nutzer kannst du zusätzliche Spiele spielen!",
                    inline=False
                )
            else:
                embed.add_field(
                    name="💡 Tipp",
                    value=f"Kaufe **Unlimited Wordle** im Shop für zusätzliche Spiele!",
                    inline=False
                )
            
            # Show share button and new game button for premium users
            view = WordleCompletedView(user_id, attempts, False, word_data, has_premium, 'daily')
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            return
        
        # Get user stats
        user_stats = await wordle.get_user_stats(db_helpers, user_id)
        
        # Get user's theme
        user_theme = await themes.get_user_theme(db_helpers, user_id)
        
        # Create game embed
        embed = wordle.create_game_embed(word_data, attempts, user_stats, False, False, 'daily', user_theme)
        
        if has_premium:
            embed.set_footer(text="💎 Premium: Nach dem Abschluss kannst du neue Spiele starten!")
        
        # Create view with guess button
        view = WordleView(user_id, word_data, max_attempts, user_theme, has_premium, 'daily')
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error in wordle command: {e}", exc_info=True)
        await interaction.followup.send(
            f"❌ Fehler beim Starten des Spiels: {str(e)}",
            ephemeral=True
        )


class WordleView(discord.ui.View):
    """UI view for Wordle game with guess input."""
    
    def __init__(self, user_id: int, word_data: dict, max_attempts: int, theme_id=None, has_premium: bool = False, game_type: str = 'daily'):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.word_data = word_data
        self.max_attempts = max_attempts
        self.theme_id = theme_id
        self.has_premium = has_premium
        self.game_type = game_type
    
    @discord.ui.button(label="Wort raten", style=discord.ButtonStyle.primary, emoji="🔍")
    async def guess_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle guess button click."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Das ist nicht dein Spiel!", ephemeral=True)
            return
        
        # Create modal for input
        modal = WordleGuessModal(self.user_id, self.word_data, self.max_attempts, self.theme_id, self.has_premium, self.game_type)
        await interaction.response.send_modal(modal)


class WordleCompletedView(discord.ui.View):
    """UI view for completed Wordle game with share and new game options."""
    
    def __init__(self, user_id: int, attempts: list, won: bool, word_data: dict = None, has_premium: bool = False, game_type: str = 'daily'):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.attempts = attempts
        self.won = won
        self.word_data = word_data
        self.has_premium = has_premium
        self.game_type = game_type
        
        # Only show new game button for premium users on daily games
        if not has_premium or game_type != 'daily':
            self.remove_item(self.new_game_button)
    
    @discord.ui.button(label="Teilen", style=discord.ButtonStyle.success, emoji="📤", row=0)
    async def share_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle share button click."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Das ist nicht dein Spiel!", ephemeral=True)
            return
        
        # Create shareable text with accurate colors
        if self.word_data:
            share_text = wordle.create_share_text(self.attempts, self.word_data['word'], self.won)
        else:
            # Fallback if word_data not provided
            share_text = f"Wordle {datetime.now(timezone.utc).date()} {len(self.attempts)}/6\n\n"
            for attempt in self.attempts:
                share_text += "🟩🟨⬜⬜⬜\n"
        
        await interaction.response.send_message(
            f"Teile dein Ergebnis:\n\n```\n{share_text}\n```",
            ephemeral=True
        )
    
    @discord.ui.button(label="Neues Spiel", style=discord.ButtonStyle.primary, emoji="🎮", row=0)
    async def new_game_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle new game button click (premium only)."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Das ist nicht dein Spiel!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Get user's language preference
        user_lang = await db_helpers.get_user_language(self.user_id)
        
        # Create new premium game
        premium_game = await wordle.create_premium_game(db_helpers, self.user_id, user_lang)
        
        if not premium_game:
            await interaction.followup.send("❌ Fehler beim Erstellen eines neuen Spiels.", ephemeral=True)
            return
        
        # Get user stats
        user_stats = await wordle.get_user_stats(db_helpers, self.user_id)
        
        # Get user's theme
        user_theme = await themes.get_user_theme(db_helpers, self.user_id)
        
        # Create new game embed
        embed = wordle.create_game_embed(premium_game, [], user_stats, False, False, 'premium', user_theme)
        embed.set_footer(text="💎 Premium Spiel - Du hast 6 Versuche!")
        
        # Create view for new game
        view = WordleView(self.user_id, premium_game, 6, user_theme, True, 'premium')
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


class WordleGuessModal(discord.ui.Modal, title="Rate das Wort"):
    """Modal for entering Wordle guess."""
    
    guess_input = discord.ui.TextInput(
        label="Dein 5-Buchstaben Wort",
        placeholder="Gib dein Wort ein (genau 5 Buchstaben)...",
        min_length=5,
        max_length=5,
        required=True
    )
    
    def __init__(self, user_id: int, word_data: dict, max_attempts: int, theme_id=None, has_premium: bool = False, game_type: str = 'daily'):
        super().__init__()
        self.user_id = user_id
        self.word_data = word_data
        self.max_attempts = max_attempts
        self.theme_id = theme_id
        self.has_premium = has_premium
        self.game_type = game_type
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        guess = self.guess_input.value.lower().strip()
        correct_word = self.word_data['word'].lower()
        word_id = self.word_data['id']
        word_language = self.word_data.get('language', 'de')  # Default to German for backward compatibility
        
        # Validate guess (must be 5 letters, only letters)
        if len(guess) != 5 or not guess.isalpha():
            await interaction.followup.send("❌ Dein Wort muss genau 5 Buchstaben enthalten (nur Buchstaben erlaubt)!", ephemeral=True)
            return
        
        # Validate that the guess is a valid word from the appropriate language word list
        valid_words = wordle.get_wordle_words(word_language)
        if guess not in valid_words:
            error_msg = "❌ This word is not in the word list! Try another English word." if word_language == 'en' else "❌ Dieses Wort ist nicht in der Wortliste! Versuche ein anderes deutsches Wort."
            await interaction.followup.send(error_msg, ephemeral=True)
            return
        
        # Get current attempts based on game type
        attempts = await wordle.get_user_attempts(db_helpers, self.user_id, word_id, self.game_type)
        attempt_num = len(attempts) + 1
        
        # Check if already guessed this word
        if any(a['guess'].lower() == guess for a in attempts):
            await interaction.followup.send("Du hast dieses Wort bereits geraten!", ephemeral=True)
            return
        
        # Check if max attempts reached
        if attempt_num > self.max_attempts:
            await interaction.followup.send("Du hast alle Versuche aufgebraucht!", ephemeral=True)
            return
        
        # Record attempt with game type
        await wordle.record_attempt(db_helpers, self.user_id, word_id, guess, attempt_num, self.game_type)
        
        # Check if correct
        if guess == correct_word:
            # Win!
            # Calculate rewards based on attempts (fewer attempts = better rewards)
            base_xp = 50
            base_money = 25
            bonus_multiplier = max(1.0, (self.max_attempts - attempt_num + 1) / self.max_attempts)
            xp_reward = int(base_xp * bonus_multiplier)
            money_reward = int(base_money * bonus_multiplier)
            
            # Give XP reward
            await db_helpers.add_xp(self.user_id, interaction.user.display_name, xp_reward)
            
            # Give money reward
            await db_helpers.add_balance(self.user_id, interaction.user.display_name, money_reward, config)
            
            embed = discord.Embed(
                title="🎉 Glückwunsch!",
                description=f"Du hast das Wort **{correct_word.upper()}** in {attempt_num} Versuchen erraten!\n\n"
                           f"**Belohnungen:**\n"
                           f"🎯 +{xp_reward} XP\n"
                           f"💰 +{money_reward} {config['modules']['economy']['currency_symbol']}",
                color=discord.Color.gold()
            )
            
            # Update stats
            await wordle.update_user_stats(db_helpers, self.user_id, True, attempt_num)
            
            # Update quest progress for daily games only
            if self.game_type == 'daily':
                await quests.update_quest_progress(db_helpers, self.user_id, 'daily_wordle', 1, config)
            
            # Mark premium game as completed if applicable
            if self.game_type == 'premium':
                await wordle.complete_premium_game(db_helpers, word_id, True)
            
            # Get updated stats and attempts for sharing
            user_stats = await wordle.get_user_stats(db_helpers, self.user_id)
            all_attempts = await wordle.get_user_attempts(db_helpers, self.user_id, word_id, self.game_type)
            
            if user_stats:
                total_games = user_stats.get('total_games', 0)
                total_wins = user_stats.get('total_wins', 0)
                current_streak = user_stats.get('current_streak', 0)
                best_streak = user_stats.get('best_streak', 0)
                win_rate = (total_wins / total_games * 100) if total_games > 0 else 0
                
                embed.add_field(
                    name="📊 Deine Statistiken",
                    value=f"Spiele: `{total_games}` | Gewonnen: `{total_wins}` ({win_rate:.1f}%)\n"
                          f"Streak: `{current_streak}` 🔥 | Best: `{best_streak}`",
                    inline=False
                )
            
            # Show completed view with share button and new game for premium
            view = WordleCompletedView(self.user_id, all_attempts, True, self.word_data, self.has_premium, self.game_type)
            await interaction.edit_original_response(embed=embed, view=view)
        else:
            # Update display with new attempt
            attempts = await wordle.get_user_attempts(db_helpers, self.user_id, word_id, self.game_type)
            user_stats = await wordle.get_user_stats(db_helpers, self.user_id)
            
            # Check if max attempts reached
            if attempt_num >= self.max_attempts:
                embed = wordle.create_game_embed(self.word_data, attempts, user_stats, is_game_over=True, won=False, game_type=self.game_type, theme_id=self.theme_id)
                embed.title = "❌ Keine Versuche mehr!"
                embed.description = f"Das gesuchte Wort war: **{correct_word.upper()}**"
                
                # Update stats (loss)
                await wordle.update_user_stats(db_helpers, self.user_id, False, attempt_num)
                
                # Mark premium game as completed if applicable
                if self.game_type == 'premium':
                    await wordle.complete_premium_game(db_helpers, word_id, False)
                
                # Show completed view with share button and new game for premium
                view = WordleCompletedView(self.user_id, attempts, False, self.word_data, self.has_premium, self.game_type)
                await interaction.edit_original_response(embed=embed, view=view)
            else:
                embed = wordle.create_game_embed(self.word_data, attempts, user_stats, game_type=self.game_type, theme_id=self.theme_id)
                view = WordleView(self.user_id, self.word_data, self.max_attempts, self.theme_id, self.has_premium, self.game_type)
                await interaction.edit_original_response(embed=embed, view=view)



@tree.command(name="wordfind", description="Spiele Word Find - Errate das tägliche Wort!")
async def word_find_command(interaction: discord.Interaction):
    """Play the daily Word Find game."""
    await interaction.response.defer(ephemeral=True)
    
    try:
        user_id = interaction.user.id
        
        # Get user's language preference
        user_lang = await db_helpers.get_user_language(user_id)
        
        # Get today's word for user's language
        word_data = await word_find.get_or_create_daily_word(db_helpers, user_lang)
        
        if not word_data:
            await interaction.followup.send("❌ Fehler beim Laden des heutigen Wortes.", ephemeral=True)
            return
        
        # Check if user has premium access
        has_premium = await db_helpers.has_feature_unlock(user_id, 'unlimited_word_find')
        
        # Get user's attempts for today (always 20 max for both free and premium)
        attempts = await word_find.get_user_attempts(db_helpers, user_id, word_data['id'], 'daily')
        max_attempts = 20
        
        # Check if already completed today (guessed correctly)
        if any(a['similarity_score'] >= 100.0 for a in attempts):
            user_stats = await word_find.get_user_stats(db_helpers, user_id)
            
            embed = discord.Embed(
                title="✅ Bereits abgeschlossen!",
                description="Du hast das heutige Wort bereits erraten!",
                color=discord.Color.green()
            )
            
            if user_stats:
                embed.add_field(
                    name="📊 Deine Statistiken",
                    value=f"Spiele: `{user_stats['total_games']}` | Gewonnen: `{user_stats['total_wins']}`\n"
                          f"Streak: `{user_stats['current_streak']}` 🔥 | Best: `{user_stats['best_streak']}`",
                    inline=False
                )
            
            # Show share button and new game button for premium users
            view = WordFindCompletedView(user_id, attempts, True, has_premium, 'daily')
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            return
        
        # Check if max attempts reached
        if len(attempts) >= max_attempts:
            correct_word = word_data['word']
            user_stats = await word_find.get_user_stats(db_helpers, user_id)
            
            embed = discord.Embed(
                title="❌ Keine Versuche mehr!",
                description=f"Das gesuchte Wort war: **{correct_word.upper()}**",
                color=discord.Color.red()
            )
            
            if user_stats:
                embed.add_field(
                    name="📊 Deine Statistiken",
                    value=f"Spiele: `{user_stats['total_games']}` | Gewonnen: `{user_stats['total_wins']}`",
                    inline=False
                )
            
            if has_premium:
                embed.add_field(
                    name="💎 Premium Vorteil",
                    value="Als Premium-Nutzer kannst du zusätzliche Spiele spielen!",
                    inline=False
                )
            else:
                embed.add_field(
                    name="💡 Tipp",
                    value=f"Kaufe **Unlimited Word Find** im Shop für zusätzliche Spiele!",
                    inline=False
                )
            
            # Show share button and new game button for premium users
            view = WordFindCompletedView(user_id, attempts, False, has_premium, 'daily')
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            return
        
        # Get user stats
        user_stats = await word_find.get_user_stats(db_helpers, user_id)
        
        # Get user's theme
        user_theme = await themes.get_user_theme(db_helpers, user_id)
        
        # Create game embed
        embed = word_find.create_game_embed(word_data, attempts, max_attempts, user_stats, 'daily', user_theme)
        
        if has_premium:
            embed.set_footer(text="💎 Premium: Nach dem Abschluss kannst du neue Spiele starten!")
        
        # Create view with guess button
        view = WordFindView(user_id, word_data, max_attempts, has_premium, 'daily', user_theme)
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error in word find command: {e}", exc_info=True)
        await interaction.followup.send(
            f"❌ Fehler beim Starten des Spiels: {str(e)}",
            ephemeral=True
        )


# --- Language Command ---

@tree.command(name="language", description="Ändere deine Spielsprache / Change your game language")
@app_commands.describe(lang="Choose your language / Wähle deine Sprache")
@app_commands.choices(lang=[
    app_commands.Choice(name="🇩🇪 Deutsch (German)", value="de"),
    app_commands.Choice(name="🇬🇧 English", value="en")
])
async def language_command(interaction: discord.Interaction, lang: app_commands.Choice[str]):
    """Change language preference for Wordle and Word Find games."""
    await interaction.response.defer(ephemeral=True)
    
    try:
        user_id = interaction.user.id
        language = lang.value
        
        # Set the user's language preference
        success = await db_helpers.set_user_language(user_id, language)
        
        if success:
            if language == 'de':
                embed = discord.Embed(
                    title="🇩🇪 Sprache geändert",
                    description="Deine Spielsprache wurde auf **Deutsch** gesetzt!\n\n"
                               "Diese Einstellung gilt für:\n"
                               "• Wordle\n"
                               "• Word Find",
                    color=discord.Color.green()
                )
            else:  # en
                embed = discord.Embed(
                    title="🇬🇧 Language Changed",
                    description="Your game language has been set to **English**!\n\n"
                               "This setting applies to:\n"
                               "• Wordle\n"
                               "• Word Find",
                    color=discord.Color.green()
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(
                "❌ Fehler beim Speichern der Spracheinstellung.\n"
                "❌ Error saving language preference.",
                ephemeral=True
            )
    
    except Exception as e:
        logger.error(f"Error in language command: {e}", exc_info=True)
        await interaction.followup.send(
            f"❌ Ein Fehler ist aufgetreten / An error occurred: {str(e)}",
            ephemeral=True
        )


@tree.command(name="privacy", description="Verwalte deine Datenschutz-Einstellungen")
@app_commands.describe(option="Wähle 'on' um Datensammlung zu aktivieren, 'off' um sie zu deaktivieren")
@app_commands.choices(option=[
    app_commands.Choice(name="Datensammlung aktivieren (on)", value="on"),
    app_commands.Choice(name="Datensammlung deaktivieren (off)", value="off")
])
async def privacy(interaction: discord.Interaction, option: app_commands.Choice[str]):
    """Manage user privacy settings for data collection."""
    await interaction.response.defer(ephemeral=True)
    
    try:
        user_id = interaction.user.id
        enabled = (option.value == "on")
        
        # Update privacy settings in database
        if not db_helpers.db_pool:
            await interaction.followup.send(
                "❌ Datenbankverbindung nicht verfügbar.",
                ephemeral=True
            )
            return
        
        cnx = db_helpers.db_pool.get_connection()
        if not cnx:
            await interaction.followup.send(
                "❌ Konnte keine Datenbankverbindung herstellen.",
                ephemeral=True
            )
            return
        
        cursor = cnx.cursor()
        try:
            # Insert or update privacy settings
            cursor.execute(
                """
                INSERT INTO user_privacy_settings (user_id, data_collection_enabled)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE 
                    data_collection_enabled = %s,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (user_id, enabled, enabled)
            )
            
            # Also update the redundant flag in user_stats for performance
            cursor.execute(
                """
                UPDATE user_stats 
                SET privacy_opt_in = %s
                WHERE user_id = %s
                """,
                (enabled, user_id)
            )
            
            cnx.commit()
            
            # Create response embed
            embed = discord.Embed(
                title="🔒 Datenschutz-Einstellungen aktualisiert",
                color=discord.Color.green() if enabled else discord.Color.blue()
            )
            
            if enabled:
                embed.description = (
                    "✅ **Datensammlung aktiviert**\n\n"
                    "Deine Spiel- und Aktivitätsdaten werden jetzt gesammelt, um:\n"
                    "• Personalisierte Spielerlebnisse zu bieten\n"
                    "• Statistiken und Fortschritt zu tracken\n"
                    "• Bestenlisten und Vergleiche zu ermöglichen\n\n"
                    "Du kannst dies jederzeit mit `/privacy off` deaktivieren."
                )
            else:
                embed.description = (
                    "🔒 **Datensammlung deaktiviert**\n\n"
                    "Deine zukünftigen Aktivitäten werden nicht mehr gesammelt.\n\n"
                    "**Hinweis:** Bereits gesammelte Daten bleiben erhalten.\n"
                    "Um alle deine Daten zu löschen, nutze das Web-Dashboard oder kontaktiere einen Administrator.\n\n"
                    "Du kannst die Datensammlung jederzeit mit `/privacy on` wieder aktivieren."
                )
            
            embed.set_footer(text="Deine Privatsphäre ist uns wichtig! 🔐")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"Privacy settings updated for user {user_id}: data_collection={enabled}")
            
        finally:
            cursor.close()
            cnx.close()
            
    except Exception as e:
        logger.error(f"Error updating privacy settings: {e}", exc_info=True)
        await interaction.followup.send(
            f"❌ Fehler beim Aktualisieren der Datenschutz-Einstellungen: {str(e)}",
            ephemeral=True
        )


@tree.command(name="settings", description="Verwalte deine Einstellungen für autonome Bot-Funktionen")
@app_commands.describe(
    feature="Welche Funktion möchtest du konfigurieren?",
    enabled="Aktivieren oder deaktivieren?"
)
@app_commands.choices(feature=[
    app_commands.Choice(name="Autonome Nachrichten vom Bot", value="messages"),
    app_commands.Choice(name="Autonome Anrufe vom Bot", value="calls"),
    app_commands.Choice(name="Einstellungen anzeigen", value="view")
])
@app_commands.choices(enabled=[
    app_commands.Choice(name="Aktivieren", value="on"),
    app_commands.Choice(name="Deaktivieren", value="off")
])
async def settings(
    interaction: discord.Interaction, 
    feature: app_commands.Choice[str],
    enabled: app_commands.Choice[str] = None
):
    """Manage user settings for autonomous bot features."""
    from modules import autonomous_behavior
    
    await interaction.response.defer(ephemeral=True)
    
    try:
        user_id = interaction.user.id
        
        if feature.value == "view":
            # Show current settings
            settings_data = await autonomous_behavior.get_user_autonomous_settings(user_id)
            
            embed = discord.Embed(
                title="⚙️ Deine Bot-Einstellungen",
                color=discord.Color.blue(),
                description="Hier sind deine aktuellen Einstellungen für autonome Bot-Funktionen:"
            )
            
            # Messages setting
            msg_status = "✅ Aktiviert" if settings_data['allow_messages'] else "❌ Deaktiviert"
            embed.add_field(
                name="📨 Autonome Nachrichten",
                value=f"{msg_status}\n*Der Bot kann dich anschreiben, wenn er mit dir reden möchte*",
                inline=False
            )
            
            # Calls setting
            call_status = "✅ Aktiviert" if settings_data['allow_calls'] else "❌ Deaktiviert"
            embed.add_field(
                name="📞 Autonome Anrufe",
                value=f"{call_status}\n*Der Bot kann dich in Voice-Channels anrufen*",
                inline=False
            )
            
            # Frequency
            freq_map = {
                'low': '🔵 Niedrig (alle 3 Tage)',
                'normal': '🟢 Normal (täglich)',
                'high': '🟡 Hoch (alle 8 Stunden)',
                'none': '⚫ Nie'
            }
            embed.add_field(
                name="📊 Kontakt-Häufigkeit",
                value=freq_map.get(settings_data['frequency'], 'Normal'),
                inline=False
            )
            
            # Last contact
            if settings_data['last_contact']:
                last_contact_str = settings_data['last_contact'].strftime("%d.%m.%Y %H:%M")
                embed.add_field(
                    name="🕐 Letzter autonomer Kontakt",
                    value=last_contact_str,
                    inline=False
                )
            
            embed.set_footer(text="Ändere Einstellungen mit /settings <feature> <on/off>")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Update settings
        if enabled is None:
            await interaction.followup.send(
                "❌ Bitte wähle 'Aktivieren' oder 'Deaktivieren'",
                ephemeral=True
            )
            return
        
        is_enabled = (enabled.value == "on")
        
        success = False
        if feature.value == "messages":
            success = await autonomous_behavior.update_user_autonomous_settings(
                user_id, allow_messages=is_enabled
            )
            feature_name = "Autonome Nachrichten"
        elif feature.value == "calls":
            success = await autonomous_behavior.update_user_autonomous_settings(
                user_id, allow_calls=is_enabled
            )
            feature_name = "Autonome Anrufe"
        
        if success:
            status = "aktiviert" if is_enabled else "deaktiviert"
            embed = discord.Embed(
                title="✅ Einstellungen aktualisiert",
                description=f"**{feature_name}** wurden {status}.",
                color=discord.Color.green() if is_enabled else discord.Color.blue()
            )
            
            if not is_enabled and feature.value == "messages":
                embed.add_field(
                    name="ℹ️ Info",
                    value="Der Bot wird dich nicht mehr eigenständig anschreiben.",
                    inline=False
                )
            elif not is_enabled and feature.value == "calls":
                embed.add_field(
                    name="ℹ️ Info",
                    value="Der Bot wird dich nicht mehr in Voice-Channels anrufen.",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"Settings updated for user {user_id}: {feature.value}={is_enabled}")
        else:
            await interaction.followup.send(
                "❌ Fehler beim Aktualisieren der Einstellungen.",
                ephemeral=True
            )
            
    except Exception as e:
        logger.error(f"Error in settings command: {e}", exc_info=True)
        await interaction.followup.send(
            f"❌ Fehler: {str(e)}",
            ephemeral=True
        )


@tree.command(name="setjoinrole", description="[Admin] Setze eine Rolle, die neue Mitglieder automatisch erhalten")
@app_commands.describe(role="Die Rolle, die neue Mitglieder erhalten sollen (oder leer lassen zum Deaktivieren)")
@app_commands.default_permissions(administrator=True)
@app_commands.check(is_admin_or_authorised)
async def setjoinrole(interaction: discord.Interaction, role: discord.Role = None):
    """Set or clear the auto-assign role for new members."""
    await interaction.response.defer(ephemeral=True)
    
    try:
        global config
        
        if role is None:
            # Clear the join role
            config['bot']['join_role'] = ""
            save_config(config)
            
            embed = discord.Embed(
                title="✅ Join-Rolle deaktiviert",
                description="Neue Mitglieder erhalten keine automatische Rolle mehr.",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed)
            logger.info(f"[Admin] Join role disabled by {interaction.user.display_name}")
        else:
            # Set the join role
            config['bot']['join_role'] = role.name
            save_config(config)
            
            embed = discord.Embed(
                title="✅ Join-Rolle konfiguriert",
                description=f"Neue Mitglieder erhalten automatisch die Rolle {role.mention}",
                color=discord.Color.green()
            )
            embed.add_field(
                name="ℹ️ Hinweis",
                value="Der Bot benötigt die Berechtigung 'Rollen verwalten' und die Bot-Rolle muss höher als die Join-Rolle sein.",
                inline=False
            )
            await interaction.followup.send(embed=embed)
            logger.info(f"[Admin] Join role set to '{role.name}' by {interaction.user.display_name}")
            
    except Exception as e:
        logger.error(f"Error in setjoinrole command: {e}", exc_info=True)
        await interaction.followup.send(
            f"❌ Fehler beim Setzen der Join-Rolle: {str(e)}",
            ephemeral=True
        )


@tree.command(name="focus", description="Starte einen Focus-Timer (Pomodoro oder Custom)")
@app_commands.describe(
    preset="Wähle einen Pomodoro-Preset oder 'custom' für eigene Zeit",
    minutes="Eigene Dauer in Minuten (nur bei 'custom')"
)
@app_commands.choices(preset=[
    app_commands.Choice(name="🍅 Kurz (25min Arbeit, 5min Pause)", value="short"),
    app_commands.Choice(name="🍅 Lang (50min Arbeit, 10min Pause)", value="long"),
    app_commands.Choice(name="🍅 Ultra (90min Arbeit, 15min Pause)", value="ultra"),
    app_commands.Choice(name="🍅 Sprint (15min Arbeit, 3min Pause)", value="sprint"),
    app_commands.Choice(name="⏱️ Eigene Zeit", value="custom"),
    app_commands.Choice(name="❌ Timer beenden", value="stop")
])
async def focus(
    interaction: discord.Interaction,
    preset: app_commands.Choice[str],
    minutes: int = None
):
    """Start a focus timer with activity monitoring."""
    from modules import focus_timer
    
    await interaction.response.defer(ephemeral=True)
    
    try:
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else 0
        
        # Check for stop command
        if preset.value == "stop":
            active_session = await focus_timer.get_active_session(user_id)
            if not active_session:
                await interaction.followup.send(
                    "❌ Du hast keinen aktiven Focus-Timer.",
                    ephemeral=True
                )
                return
            
            # End the session
            completed = await focus_timer.end_focus_session(user_id, completed=False)
            
            if completed:
                stats = active_session
                duration = (datetime.now() - stats['start_time']).seconds // 60
                
                embed = discord.Embed(
                    title="⏹️ Focus-Timer beendet",
                    color=discord.Color.orange(),
                    description=f"Du warst **{duration} Minuten** im Focus-Modus."
                )
                embed.add_field(
                    name="📊 Statistiken",
                    value=f"Ablenkungen: {stats['distractions']}",
                    inline=False
                )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(
                    "❌ Fehler beim Beenden des Timers.",
                    ephemeral=True
                )
            return
        
        # Check if user already has an active session
        active_session = await focus_timer.get_active_session(user_id)
        if active_session:
            time_left = (active_session['end_time'] - datetime.now()).seconds // 60
            await interaction.followup.send(
                f"⏱️ Du hast bereits einen aktiven Focus-Timer!\n"
                f"Noch **{time_left} Minuten** verbleibend.\n"
                f"Beende ihn mit `/focus preset:stop`",
                ephemeral=True
            )
            return
        
        # Determine duration
        if preset.value == "custom":
            if minutes is None or minutes <= 0:
                await interaction.followup.send(
                    "❌ Bitte gib eine gültige Dauer in Minuten an.",
                    ephemeral=True
                )
                return
            duration = minutes
            session_type = "custom"
            preset_name = f"{minutes} Minuten"
        else:
            preset_data = focus_timer.get_pomodoro_preset(preset.value)
            if not preset_data:
                await interaction.followup.send(
                    "❌ Ungültiger Preset.",
                    ephemeral=True
                )
                return
            duration = preset_data['work']
            session_type = "pomodoro"
            preset_name = preset_data['name']
        
        # Start the session
        session_id = await focus_timer.start_focus_session(
            user_id, guild_id, session_type, duration
        )
        
        if session_id:
            embed = discord.Embed(
                title="🎯 Focus-Timer gestartet!",
                color=discord.Color.green(),
                description=f"**{preset_name}** - {duration} Minuten"
            )
            embed.add_field(
                name="📱 Aktivitäts-Monitoring",
                value=(
                    "Der Bot überwacht jetzt deine Aktivitäten:\n"
                    "• 💬 Nachrichten in Channels\n"
                    "• 🎮 Spiele (außer Musik)\n"
                    "• 📺 Videos/Streams\n\n"
                    "Bei Ablenkungen wirst du benachrichtigt!"
                ),
                inline=False
            )
            embed.add_field(
                name="⏰ Timer-Ende",
                value=f"Timer endet um <t:{int((datetime.now() + timedelta(minutes=duration)).timestamp())}:t>",
                inline=False
            )
            embed.add_field(
                name="🎵 Musik & Sounds",
                value="Tipp: Nutze `/music action:Start` für Hintergrundmusik und Ambient-Sounds!",
                inline=False
            )
            embed.set_footer(text="Beende den Timer mit /focus preset:stop")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"Focus session started for user {user_id}: {duration} minutes")
            
            # Schedule timer completion notification
            # Store task reference to prevent garbage collection
            task = asyncio.create_task(
                focus_timer_completion_handler(interaction.user, session_id, duration)
            )
            # Add task to a set to prevent GC (will be cleaned up on completion)
            if not hasattr(client, '_focus_timer_tasks'):
                client._focus_timer_tasks = set()
            client._focus_timer_tasks.add(task)
            task.add_done_callback(client._focus_timer_tasks.discard)
        else:
            await interaction.followup.send(
                "❌ Fehler beim Starten des Timers.",
                ephemeral=True
            )
            
    except Exception as e:
        logger.error(f"Error in focus command: {e}", exc_info=True)
        await interaction.followup.send(
            f"❌ Fehler: {str(e)}",
            ephemeral=True
        )


async def focus_timer_completion_handler(user: discord.User, session_id: int, duration_minutes: int):
    """Handle focus timer completion notification."""
    from modules import focus_timer
    
    try:
        # Wait for timer to complete
        await asyncio.sleep(duration_minutes * 60)
        
        # Check if session is still active
        active_session = await focus_timer.get_active_session(user.id)
        if not active_session or active_session['session_id'] != session_id:
            return  # Session was already stopped
        
        # End the session as completed
        await focus_timer.end_focus_session(user.id, completed=True)
        
        # Get session stats
        stats = active_session
        
        # Create completion message
        embed = discord.Embed(
            title="✅ Focus-Timer abgeschlossen!",
            color=discord.Color.green(),
            description=f"Gut gemacht! Du hast **{duration_minutes} Minuten** fokussiert gearbeitet."
        )
        embed.add_field(
            name="📊 Statistiken",
            value=f"Ablenkungen: {stats['distractions']}",
            inline=False
        )
        
        # Try to send DM
        try:
            await user.send(embed=embed)
            logger.info(f"Sent focus completion DM to user {user.id}")
        except discord.Forbidden:
            logger.warning(f"Cannot send DM to user {user.id}")
        
    except Exception as e:
        logger.error(f"Error in focus timer completion handler: {e}", exc_info=True)


@tree.command(name="focusstats", description="Zeige deine Focus-Timer Statistiken an")
@app_commands.describe(days="Zeitraum in Tagen (Standard: 7)")
async def focusstats(interaction: discord.Interaction, days: int = 7):
    """Show focus timer statistics for a user."""
    from modules import focus_timer
    
    await interaction.response.defer(ephemeral=True)
    
    try:
        user_id = interaction.user.id
        
        # Validate days
        if days < 1 or days > 365:
            await interaction.followup.send(
                "❌ Bitte wähle einen Zeitraum zwischen 1 und 365 Tagen.",
                ephemeral=True
            )
            return
        
        # Get stats
        stats = await focus_timer.get_user_focus_stats(user_id, days)
        
        if stats['total_sessions'] == 0:
            await interaction.followup.send(
                f"📊 Du hast in den letzten {days} Tagen keine Focus-Sessions gestartet.",
                ephemeral=True
            )
            return
        
        # Calculate additional stats
        avg_duration = stats['total_minutes'] / stats['total_sessions'] if stats['total_sessions'] > 0 else 0
        avg_distractions = stats['total_distractions'] / stats['total_sessions'] if stats['total_sessions'] > 0 else 0
        
        # Create embed
        embed = discord.Embed(
            title="📊 Focus-Timer Statistiken",
            description=f"Statistiken der letzten **{days} Tage**",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="🎯 Sessions",
            value=f"Gesamt: **{stats['total_sessions']}**\n"
                  f"Abgeschlossen: **{stats['completed_sessions']}**\n"
                  f"Erfolgsrate: **{stats['completion_rate']:.1f}%**",
            inline=True
        )
        
        embed.add_field(
            name="⏱️ Zeit",
            value=f"Gesamt: **{stats['total_minutes']} Min**\n"
                  f"Durchschnitt: **{avg_duration:.1f} Min**\n"
                  f"Stunden: **{stats['total_minutes'] / 60:.1f}h**",
            inline=True
        )
        
        embed.add_field(
            name="⚠️ Ablenkungen",
            value=f"Gesamt: **{stats['total_distractions']}**\n"
                  f"Pro Session: **{avg_distractions:.1f}**",
            inline=True
        )
        
        # Get current active session
        active_session = await focus_timer.get_active_session(user_id)
        if active_session:
            time_left = (active_session['end_time'] - datetime.now()).seconds // 60
            embed.add_field(
                name="🔴 Aktive Session",
                value=f"Noch **{time_left} Minuten** verbleibend",
                inline=False
            )
        
        embed.set_footer(text="Starte eine neue Session mit /focus")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error in focusstats command: {e}", exc_info=True)
        await interaction.followup.send(
            f"❌ Fehler beim Abrufen der Statistiken: {str(e)}",
            ephemeral=True
        )


# ============================================================================
# Music Player Views - Modern UI Components
# ============================================================================

# UI timeout constant (5 minutes)
MUSIC_VIEW_TIMEOUT = 300

# Station display mapping (used across multiple views)
STATION_DISPLAY = {
    "lofi": "🎧 Lofi Beats",
    "nocopyright": "🎵 No Copyright",
    "ambient": "🌧️ Ambient Sounds",
    "noise": "⚪ Noise Station",
    "spotify_mix": "✨ Spotify Mix",
    "custom": "🎼 Custom Song"
}

async def get_current_song_embed(guild_id: int, user_id: int, voice_client) -> Optional[discord.Embed]:
    """
    Helper function to create an embed with current song information.
    
    Args:
        guild_id: Guild ID
        user_id: User ID for theme colors
        voice_client: Voice client to check playback status
    
    Returns:
        Discord embed with current song info, or None if no song playing
    """
    if guild_id not in lofi_player.active_sessions or 'current_song' not in lofi_player.active_sessions[guild_id]:
        return None
    
    current_song = lofi_player.active_sessions[guild_id]['current_song']
    queue = lofi_player.active_sessions[guild_id].get('queue', [])
    
    # Get user's custom embed color
    embed_color = discord.Color.blue()
    try:
        from modules.themes import get_user_theme, get_theme_color
        theme = await get_user_theme(db_helpers, user_id)
        embed_color = get_theme_color(theme, 'primary') if theme else discord.Color.blue()
    except (ImportError, AttributeError, Exception) as e:
        logger.debug(f"Could not load user theme: {e}")
        pass
    
    # Create embed
    embed = discord.Embed(
        title="🎵 Jetzt läuft",
        color=embed_color
    )
    
    # Add current song info
    song_title = current_song.get('title', 'Unbekannt')
    song_artist = current_song.get('artist', 'Unbekannt')
    song_url = current_song.get('url', '')
    station_type = current_song.get('type', 'custom')
    
    # Get station name
    station_name = STATION_DISPLAY.get(station_type, '🎵 Music')
    
    if song_url:
        embed.add_field(
            name="🎧 Song",
            value=f"**{song_title}**\nby {song_artist}\n[Link]({song_url})",
            inline=False
        )
    else:
        embed.add_field(
            name="🎧 Song",
            value=f"**{song_title}**\nby {song_artist}",
            inline=False
        )
    
    # Add station type
    embed.add_field(
        name="📻 Station",
        value=station_name,
        inline=True
    )
    
    # Add queue info
    embed.add_field(
        name="📋 In der Warteschlange",
        value=f"**{len(queue)}** Songs",
        inline=True
    )
    
    # Add voice channel info
    if voice_client and voice_client.channel:
        embed.add_field(
            name="📍 Voice Channel",
            value=f"**{voice_client.channel.name}**",
            inline=True
        )
    
    embed.set_footer(text="Nutze die Buttons unten zur Steuerung")
    
    return embed

class MusicStationSelect(discord.ui.Select):
    """Select menu for choosing music stations."""
    
    def __init__(self, station_type: str = "all"):
        self.station_type = station_type
        
        # Build options based on type
        options = []
        
        if station_type == "all" or station_type == "lofi":
            lofi_stations = lofi_player.get_stations_by_type("lofi")
            for i, station in enumerate(lofi_stations):
                options.append(discord.SelectOption(
                    label=station['name'],
                    value=f"lofi_{i}",
                    description="Lofi Beats zum Entspannen",
                    emoji="🎧"
                ))
        
        if station_type == "all" or station_type == "nocopyright":
            nc_stations = lofi_player.get_stations_by_type("nocopyright")
            for i, station in enumerate(nc_stations):
                options.append(discord.SelectOption(
                    label=station['name'],
                    value=f"nocopyright_{i}",
                    description="Keine Copyright-Probleme",
                    emoji="🎵"
                ))
        
        if station_type == "all" or station_type == "ambient":
            ambient_stations = lofi_player.get_stations_by_type("ambient")
            for i, station in enumerate(ambient_stations):
                options.append(discord.SelectOption(
                    label=station['name'],
                    value=f"ambient_{i}",
                    description="Natürliche Klangkulissen",
                    emoji="🌧️"
                ))
        
        if station_type == "all" or station_type == "noise":
            noise_stations = lofi_player.get_stations_by_type("noise")
            for i, station in enumerate(noise_stations):
                options.append(discord.SelectOption(
                    label=station['name'],
                    value=f"noise_{i}",
                    description="Noise für Fokus & Entspannung",
                    emoji="⚪"
                ))
        
        # Add Spotify option
        if station_type == "all" or station_type == "spotify":
            options.append(discord.SelectOption(
                label="🎧 Mein Spotify Mix",
                value="spotify_mix",
                description="Basierend auf deiner Hörhistorie",
                emoji="✨"
            ))
        
        # Limit to 25 options (Discord limit)
        options = options[:25]
        
        super().__init__(
            placeholder="🎵 Wähle eine Station...",
            options=options,
            min_values=1,
            max_values=1
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Handle station selection."""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # Get user's voice channel
            if not interaction.user.voice or not interaction.user.voice.channel:
                embed = discord.Embed(
                    title="❌ Nicht in Voice-Channel",
                    description="Du musst in einem Voice-Channel sein!",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            voice_channel = interaction.user.voice.channel
            
            # Join voice channel
            voice_client = await lofi_player.join_voice_channel(voice_channel)
            
            if not voice_client:
                embed = discord.Embed(
                    title="❌ Verbindungsfehler",
                    description="Konnte dem Voice-Channel nicht beitreten!",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Parse selection
            selection = self.values[0]
            
            # Get user's custom embed color
            from modules.themes import get_user_theme, get_theme_color
            theme = await get_user_theme(db_helpers, interaction.user.id)
            embed_color = get_theme_color(theme, 'primary') if theme else discord.Color.blue()
            
            if selection == "spotify_mix":
                # Start Spotify queue
                success = await lofi_player.start_spotify_queue(
                    voice_client,
                    interaction.user.id,
                    interaction.guild.id
                )
                
                if success:
                    # Get current song and queue preview
                    current_song = lofi_player.get_current_song(interaction.guild.id)
                    queue_preview = lofi_player.get_queue_preview(interaction.guild.id, count=3)
                    
                    embed = discord.Embed(
                        title="🎧 Spotify Mix gestartet!",
                        description="## Deine personalisierte Playlist\n*Basierend auf deiner Hörhistorie*",
                        color=embed_color
                    )
                    embed.add_field(
                        name="📍 Voice Channel",
                        value=f"**{voice_channel.name}**",
                        inline=True
                    )
                    embed.add_field(
                        name="🎼 Modus",
                        value="**Auto-Queue**\n*Spielt automatisch weiter*",
                        inline=True
                    )
                    embed.add_field(
                        name="👤 Gestartet von",
                        value=f"**{interaction.user.display_name}**",
                        inline=True
                    )
                    
                    # Show currently playing song
                    if current_song:
                        current_title = current_song.get('title', 'Unknown')
                        current_artist = current_song.get('artist', 'Unknown')
                        embed.add_field(
                            name="🎵 Spielt gerade",
                            value=f"**{current_title}**\n*{current_artist}*",
                            inline=False
                        )
                    
                    # Show next 3 songs in queue
                    if queue_preview:
                        queue_text = ""
                        for i, song in enumerate(queue_preview, 1):
                            song_title = song.get('title', 'Unknown')
                            song_artist = song.get('artist', 'Unknown')
                            queue_text += f"**{i}.** {song_title}\n   *{song_artist}*\n"
                        
                        embed.add_field(
                            name="⏭️ Als Nächstes",
                            value=queue_text.strip(),
                            inline=False
                        )
                    
                    embed.set_thumbnail(url=interaction.user.display_avatar.url)
                    await interaction.followup.send(embed=embed, ephemeral=True)
                else:
                    embed = discord.Embed(
                        title="📊 Keine Spotify-History",
                        description="Ich konnte keine Spotify-Hördaten finden!",
                        color=discord.Color.orange()
                    )
                    embed.add_field(
                        name="💡 Tipp",
                        value="Höre Musik auf Spotify mit Discord geöffnet, dann versuche es erneut!",
                        inline=False
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                # Parse station type and index
                parts = selection.split('_')
                if len(parts) == 2:
                    station_type_value, index_str = parts
                    station_index = int(index_str)
                    
                    stations = lofi_player.get_stations_by_type(station_type_value)
                    if stations and station_index < len(stations):
                        station = stations[station_index]
                        
                        # Play station
                        success = await lofi_player.play_station(voice_client, station)
                        
                        if success:
                            # Get emoji based on type
                            type_emojis = {
                                "lofi": "🎧",
                                "nocopyright": "🎵",
                                "ambient": "🌧️",
                                "noise": "⚪"
                            }
                            station_emoji = type_emojis.get(station_type_value, "🎵")
                            
                            embed = discord.Embed(
                                title=f"{station_emoji} Jetzt läuft",
                                description=f"## {station['name']}\n*Genieße deine Musik!*",
                                color=embed_color
                            )
                            embed.add_field(
                                name="📍 Voice Channel",
                                value=f"**{voice_channel.name}**",
                                inline=True
                            )
                            embed.add_field(
                                name="👤 Gestartet von",
                                value=f"**{interaction.user.display_name}**",
                                inline=True
                            )
                            embed.set_thumbnail(url=interaction.user.display_avatar.url)
                            await interaction.followup.send(embed=embed, ephemeral=True)
                        else:
                            embed = discord.Embed(
                                title="❌ Playback-Fehler",
                                description="Die Musik konnte nicht gestartet werden!",
                                color=discord.Color.red()
                            )
                            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in station select callback: {e}", exc_info=True)
            embed = discord.Embed(
                title="❌ Fehler",
                description=f"Es ist ein Fehler aufgetreten: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)


class MusicControlView(discord.ui.View):
    """View with buttons for music controls."""
    
    def __init__(self):
        super().__init__(timeout=MUSIC_VIEW_TIMEOUT)
        
    @discord.ui.button(label="Browse Stations", style=discord.ButtonStyle.primary, emoji="📋")
    async def browse_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show station browser."""
        view = MusicStationView()
        
        embed_color = discord.Color.blue()
        try:
            from modules.themes import get_user_theme, get_theme_color
            theme = await get_user_theme(db_helpers, interaction.user.id)
            embed_color = get_theme_color(theme, 'primary') if theme else discord.Color.blue()
        except:
            pass
        
        embed = discord.Embed(
            title="🎵 Music Player",
            description="## Wähle deine Musik\n*Wähle aus dem Menü unten*",
            color=embed_color
        )
        embed.set_footer(text="Auto-disconnect nach 2 Min. wenn alleine")
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="Now Playing", style=discord.ButtonStyle.secondary, emoji="🎵")
    async def now_playing_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show currently playing song and update the embed."""
        await interaction.response.defer(ephemeral=True)
        
        guild_id = interaction.guild.id
        voice_client = interaction.guild.voice_client
        
        if not voice_client or not voice_client.is_connected():
            embed = discord.Embed(
                title="❌ Nicht verbunden",
                description="Der Bot spielt gerade keine Musik!",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        if not voice_client.is_playing():
            embed = discord.Embed(
                title="❌ Keine Wiedergabe",
                description="Es läuft gerade keine Musik!",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Use helper function to get current song embed
        embed = await get_current_song_embed(guild_id, interaction.user.id, voice_client)
        
        if embed:
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            # Create a new view with playback controls
            view = PlaybackControlView()
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        else:
            embed = discord.Embed(
                title="ℹ️ Keine Song-Info",
                description="Es konnte keine Information über den aktuellen Song gefunden werden.",
                color=discord.Color.blue()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="Stop", style=discord.ButtonStyle.danger, emoji="⏹️")
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Stop music playback."""
        await interaction.response.defer(ephemeral=True)
        
        voice_client = interaction.guild.voice_client
        
        if not voice_client or not voice_client.is_connected():
            embed = discord.Embed(
                title="ℹ️ Nicht verbunden",
                description="Der Bot ist in keinem Voice-Channel!",
                color=discord.Color.blue()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        channel_name = voice_client.channel.name if voice_client.channel else "Unknown"
        
        await lofi_player.stop_lofi(voice_client)
        await lofi_player.leave_voice_channel(voice_client)
        
        embed = discord.Embed(
            title="⏹️ Musik gestoppt",
            description=f"## Playback beendet\n*Bis zum nächsten Mal!*",
            color=discord.Color.green()
        )
        embed.add_field(
            name="📍 Verlassener Channel",
            value=f"**{channel_name}**",
            inline=True
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


class PlaybackControlView(discord.ui.View):
    """View with playback control buttons (skip, pause/resume)."""
    
    def __init__(self, paused: bool = False):
        super().__init__(timeout=MUSIC_VIEW_TIMEOUT)
        # Dynamically set pause/resume button based on state
        self.paused = paused
        
        # Add skip button
        skip_button = discord.ui.Button(
            label="Skip",
            style=discord.ButtonStyle.primary,
            emoji="⏭️",
            custom_id="skip_btn"
        )
        skip_button.callback = self.skip_callback
        self.add_item(skip_button)
        
        # Add pause/resume button with dynamic label
        pause_button = discord.ui.Button(
            label="Resume" if paused else "Pause",
            style=discord.ButtonStyle.secondary,
            emoji="▶️" if paused else "⏸️",
            custom_id="pause_btn"
        )
        pause_button.callback = self.pause_callback
        self.add_item(pause_button)
        
        # Add refresh button
        refresh_button = discord.ui.Button(
            label="Refresh",
            style=discord.ButtonStyle.success,
            emoji="🔄",
            custom_id="refresh_btn"
        )
        refresh_button.callback = self.refresh_callback
        self.add_item(refresh_button)
    
    async def skip_callback(self, interaction: discord.Interaction):
        """Skip the current song."""
        await interaction.response.defer(ephemeral=True)
        
        guild_id = interaction.guild.id
        voice_client = interaction.guild.voice_client
        
        if not voice_client or not voice_client.is_connected():
            embed = discord.Embed(
                title="❌ Nicht verbunden",
                description="Der Bot spielt gerade keine Musik!",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        if not voice_client.is_playing():
            embed = discord.Embed(
                title="❌ Keine Wiedergabe",
                description="Es läuft gerade keine Musik!",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Stop current song (this will trigger the after_callback to play next)
        voice_client.stop()
        
        embed = discord.Embed(
            title="⏭️ Song übersprungen",
            description="Nächster Song wird geladen...",
            color=discord.Color.blue()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def pause_callback(self, interaction: discord.Interaction):
        """Pause or resume playback."""
        await interaction.response.defer(ephemeral=True)
        
        voice_client = interaction.guild.voice_client
        
        if not voice_client or not voice_client.is_connected():
            embed = discord.Embed(
                title="❌ Nicht verbunden",
                description="Der Bot spielt gerade keine Musik!",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        if voice_client.is_playing():
            voice_client.pause()
            embed = discord.Embed(
                title="⏸️ Pausiert",
                description="Musik wurde pausiert. Nutze den Button erneut zum Fortsetzen.",
                color=discord.Color.blue()
            )
            # Create new view with updated button
            view = PlaybackControlView(paused=True)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        elif voice_client.is_paused():
            voice_client.resume()
            embed = discord.Embed(
                title="▶️ Fortgesetzt",
                description="Musik wird fortgesetzt.",
                color=discord.Color.green()
            )
            # Create new view with play button
            view = PlaybackControlView(paused=False)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        else:
            embed = discord.Embed(
                title="❌ Keine Wiedergabe",
                description="Es läuft gerade keine Musik!",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def refresh_callback(self, interaction: discord.Interaction):
        """Refresh and show current song info."""
        await interaction.response.defer(ephemeral=True)
        
        guild_id = interaction.guild.id
        voice_client = interaction.guild.voice_client
        
        if not voice_client or not voice_client.is_connected():
            embed = discord.Embed(
                title="❌ Nicht verbunden",
                description="Der Bot spielt gerade keine Musik!",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        if not voice_client.is_playing() and not voice_client.is_paused():
            embed = discord.Embed(
                title="❌ Keine Wiedergabe",
                description="Es läuft gerade keine Musik!",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Use helper function to get current song embed
        embed = await get_current_song_embed(guild_id, interaction.user.id, voice_client)
        
        if embed:
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            # Update with same view (check if paused)
            view = PlaybackControlView(paused=voice_client.is_paused())
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        else:
            embed = discord.Embed(
                title="ℹ️ Keine Song-Info",
                description="Es konnte keine Information über den aktuellen Song gefunden werden.",
                color=discord.Color.blue()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)


class MusicStationView(discord.ui.View):
    """View with select menu for choosing stations."""
    
    def __init__(self):
        super().__init__(timeout=MUSIC_VIEW_TIMEOUT)
        self.add_item(MusicStationSelect("all"))


@tree.command(name="music", description="🎵 Spiele Musik oder Ambient-Sounds im Voice-Channel")
async def music(interaction: discord.Interaction):
    """Play music with modern interactive UI."""
    try:
        # Get user's custom embed color
        embed_color = await get_user_embed_color(interaction.user.id, config)
        
        # Create the modern UI view
        view = MusicControlView()
        
        embed = discord.Embed(
            title="🎵 Music Player",
            description="## Willkommen beim Music Player!\n"
                       "*Wähle unten eine Aktion aus*",
            color=embed_color
        )
        
        # Add feature info
        embed.add_field(
            name="🎧 Verfügbare Stationen",
            value="• **Lofi Beats** - Zum Lernen & Entspannen\n"
                  "• **No Copyright Music** - Stream-sicher\n"
                  "• **Ambient Sounds** - Natürliche Klänge\n"
                  "• **Noise Stations** - White, Pink, Brown Noise\n"
                  "• **Spotify Mix** - Deine persönliche Playlist",
            inline=False
        )
        
        embed.add_field(
            name="✨ Features",
            value="• **Auto-Queue** für Spotify Mix\n"
                  "• **Auto-Disconnect** nach 2 Min. Inaktivität\n"
                  "• **Song Recommendations** aus ähnlicher Musik",
            inline=False
        )
        
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(
            text=f"Angefordert von {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error in music command: {e}", exc_info=True)
        embed = discord.Embed(
            title="❌ Fehler",
            description=f"Es ist ein Fehler aufgetreten: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name="musicadd", description="➕ Füge einen Song zur Warteschlange hinzu")
@app_commands.describe(song_query="Song-Name oder YouTube-URL")
async def music_add(interaction: discord.Interaction, song_query: str):
    """Add a custom song to the queue."""
    await interaction.response.defer(ephemeral=True)
    
    try:
        # Check if user is in voice channel
        if not interaction.user.voice or not interaction.user.voice.channel:
            embed = discord.Embed(
                title="❌ Nicht in Voice-Channel",
                description="Du musst in einem Voice-Channel sein!",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        voice_channel = interaction.user.voice.channel
        guild_id = interaction.guild.id
        
        # Get or create voice client
        voice_client = interaction.guild.voice_client
        if not voice_client or not voice_client.is_connected():
            voice_client = await lofi_player.join_voice_channel(voice_channel)
            if not voice_client:
                embed = discord.Embed(
                    title="❌ Verbindungsfehler",
                    description="Konnte dem Voice-Channel nicht beitreten!",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
        
        # Parse song query
        song = {}
        if song_query.startswith('http'):
            # It's a URL
            song['url'] = song_query
        else:
            # It's a search query - try to parse as "artist - title" or just search
            if ' - ' in song_query:
                parts = song_query.split(' - ', 1)
                song['artist'] = parts[0].strip()
                song['title'] = parts[1].strip()
            else:
                # Search YouTube directly
                song['url'] = f"ytsearch:{song_query}"
        
        # If no active queue, start playing this song
        if guild_id not in lofi_player.active_sessions or not lofi_player.active_sessions[guild_id].get('queue'):
            success = await lofi_player.play_song_with_queue(
                voice_client, 
                song, 
                guild_id, 
                volume=1.0,
                user_id=interaction.user.id
            )
            
            if success:
                # Get current song and queue preview
                current_song = lofi_player.get_current_song(guild_id)
                queue_preview = lofi_player.get_queue_preview(guild_id, count=3)
                
                embed = discord.Embed(
                    title="▶️ Jetzt läuft",
                    description="Song wird abgespielt...",
                    color=discord.Color.green()
                )
                
                # Show currently playing song
                if current_song:
                    current_title = current_song.get('title', 'Unknown')
                    current_artist = current_song.get('artist', 'Unknown')
                    embed.add_field(
                        name="🎵 Song",
                        value=f"**{current_title}**\n*{current_artist}*",
                        inline=False
                    )
                
                # Show next 3 songs in queue
                if queue_preview:
                    queue_text = ""
                    for i, next_song in enumerate(queue_preview, 1):
                        song_title = next_song.get('title', 'Unknown')
                        song_artist = next_song.get('artist', 'Unknown')
                        queue_text += f"**{i}.** {song_title}\n   *{song_artist}*\n"
                    
                    embed.add_field(
                        name="⏭️ Als Nächstes",
                        value=queue_text.strip(),
                        inline=False
                    )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                embed = discord.Embed(
                    title="❌ Fehler",
                    description="Song konnte nicht abgespielt werden!",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            # Add to existing queue
            lofi_player.active_sessions[guild_id]['queue'].append(song)
            queue_pos = len(lofi_player.active_sessions[guild_id]['queue'])
            
            embed = discord.Embed(
                title="✅ Zur Warteschlange hinzugefügt",
                description=f"**Position in Queue:** {queue_pos}",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
    except Exception as e:
        logger.error(f"Error in musicadd command: {e}", exc_info=True)
        embed = discord.Embed(
            title="❌ Fehler",
            description=f"Es ist ein Fehler aufgetreten: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


@tree.command(name="musicqueue", description="📋 Zeige die aktuelle Musik-Warteschlange")
async def music_queue(interaction: discord.Interaction):
    """Show the current music queue."""
    await interaction.response.defer(ephemeral=True)
    
    try:
        guild_id = interaction.guild.id
        
        # Check if there's an active session
        if guild_id not in lofi_player.active_sessions:
            embed = discord.Embed(
                title="📋 Warteschlange",
                description="Keine aktive Musik-Session!",
                color=discord.Color.orange()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Get current song and queue
        current_song = lofi_player.get_current_song(guild_id)
        queue_preview = lofi_player.get_queue_preview(guild_id, count=10)  # Show up to 10
        
        embed = discord.Embed(
            title="📋 Musik-Warteschlange",
            color=discord.Color.blue()
        )
        
        # Show currently playing song
        if current_song:
            current_title = current_song.get('title', 'Unknown')
            current_artist = current_song.get('artist', 'Unknown')
            embed.add_field(
                name="🎵 Spielt gerade",
                value=f"**{current_title}**\n*{current_artist}*",
                inline=False
            )
        else:
            embed.add_field(
                name="🎵 Spielt gerade",
                value="*Nichts*",
                inline=False
            )
        
        # Show queue
        if queue_preview and len(queue_preview) > 0:
            queue_text = ""
            for i, song in enumerate(queue_preview, 1):
                song_title = song.get('title', 'Unknown')
                song_artist = song.get('artist', 'Unknown')
                queue_text += f"**{i}.** {song_title}\n   *{song_artist}*\n"
            
            embed.add_field(
                name=f"⏭️ Als Nächstes ({len(queue_preview)} Songs)",
                value=queue_text.strip(),
                inline=False
            )
            
            # Show total queue size if there are more
            total_queue = len(lofi_player.active_sessions[guild_id].get('queue', []))
            if total_queue > len(queue_preview):
                embed.set_footer(text=f"... und {total_queue - len(queue_preview)} weitere Songs")
        else:
            embed.add_field(
                name="⏭️ Als Nächstes",
                value="*Queue ist leer*",
                inline=False
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error in musicqueue command: {e}", exc_info=True)
        embed = discord.Embed(
            title="❌ Fehler",
            description=f"Es ist ein Fehler aufgetreten: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


@tree.command(name="rr", description="Spiele Russian Roulette!")
@app_commands.describe(bet="Einsatz (optional, Standard: 100)")
async def russian_roulette(interaction: discord.Interaction, bet: int = None):
    """Play Russian Roulette."""
    await interaction.response.defer(ephemeral=True)
    
    user_id = interaction.user.id
    
    # Check if user has casino access
    has_casino = await db_helpers.has_feature_unlock(user_id, 'casino')
    if not has_casino:
        currency = config['modules']['economy']['currency_symbol']
        price = config['modules']['economy']['shop']['features'].get('casino', 500)
        await interaction.followup.send(
            f"🎰 Du benötigst **Casino Access**, um Russian Roulette zu spielen!\n"
            f"Kaufe es im Shop für {price} {currency} mit `/shopbuy`",
            ephemeral=True
        )
        return
    
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


# --- NEW: Reaction tracking for learning ---
@client.event
async def on_reaction_add(reaction, user):
    """Track reactions to bot messages for learning."""
    if user.bot:
        return
    
    # Check if this is a reaction to a bot message
    if reaction.message.author.id == client.user.id:
        try:
            # Map emoji to feedback value
            feedback_value = 0
            if str(reaction.emoji) in ['👍', '❤️', '🔥', '😂', '🎉']:
                feedback_value = 1  # Positive
            elif str(reaction.emoji) in ['👎', '😐', '😒', '🙄']:
                feedback_value = -1  # Negative
            
            # Record feedback
            await personality_evolution.record_conversation_feedback(
                user_id=user.id,
                message_id=reaction.message.id,
                feedback_type='reaction',
                feedback_value=feedback_value
            )
            
            # Learn from the reaction
            # Get the user's message if this was a reply, otherwise use empty string
            user_message = ""
            if reaction.message.reference and reaction.message.reference.resolved:
                user_message = reaction.message.reference.resolved.content
            
            # Always learn from reactions, even without original context
            if reaction.message.content:
                await personality_evolution.learn_from_interaction(
                    user_id=user.id,
                    message=user_message,  # May be empty if not a reply
                    bot_response=reaction.message.content,
                    user_reaction=str(reaction.emoji)
                )
            
        except Exception as e:
            logger.debug(f"Could not record reaction feedback: {e}")


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
        
        # --- NEW: Track ALL messages for server activity (not just bot interactions) ---
        if message.guild:
            try:
                bot_mind.bot_mind.update_server_activity(message.guild.id)
                logger.debug(f"[MIND] Tracked activity in server {message.guild.name}")
            except AttributeError as ae:
                logger.debug(f"[MIND] Bot mind module not available: {ae}")
        
        # --- NEW: Passive observation and thinking about messages ---
        # The bot observes messages even when not mentioned to build context and awareness
        if message.guild and not message.content.startswith('/'):
            try:
                observer = passive_observer.get_passive_observer()
                thought = await observer.observe_message(message, bot_mind, config)
                if thought:
                    logger.info(f"[PASSIVE] Bot thought: {thought}")
            except Exception as e:
                logger.debug(f"[PASSIVE] Observation error: {e}")
        
        # --- NEW: Focus timer activity detection ---
        try:
            is_distraction = await focus_timer.detect_message_activity(
                message.author.id, 
                "DM" if isinstance(message.channel, discord.DMChannel) else "server"
            )
            if is_distraction:
                # Send a gentle reminder
                try:
                    await message.author.send(
                        "⚠️ **Focus-Modus aktiv!** Du solltest gerade fokussiert arbeiten. 🎯",
                        delete_after=10
                    )
                except discord.Forbidden:
                    pass  # Can't send DM
        except Exception as e:
            logger.error(f"Error in focus timer detection: {e}")
    
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
            emoji_context = await handle_unknown_emojis_in_message(message, config, GEMINI_API_KEY, OPENAI_API_KEY, client)
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
            final_response = await replace_emoji_tags(response_text, client, message.guild)
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

            # --- NEW: Learn from this interaction for personality evolution ---
            try:
                await personality_evolution.learn_from_interaction(
                    user_id=message.author.id,
                    message=message.content,
                    bot_response=final_response
                )
                logger.debug(f"[CHATBOT] Recorded learning from interaction with {message.author.name}")
            except Exception as e:
                logger.warning(f"[CHATBOT] Could not record learning: {e}")

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
        dynamic_system_prompt = config['bot']['system_prompt']
        
        # Add language reminder to prevent language slips
        dynamic_system_prompt += "\n\nREMINDER: Antworte IMMER auf Deutsch!"
        
        # Add accuracy enforcement for current conversation using constant template
        dynamic_system_prompt += "\n\n" + ACCURACY_CHECK_TEMPLATE.format(user_name=message.author.display_name)
        
        # --- ENHANCED: Add evolved personality context for smarter AI responses ---
        try:
            personality_context = await personality_evolution.get_personality_context_for_prompt()
            if personality_context:
                dynamic_system_prompt += f"\n\n{personality_context}"
                logger.debug("Added evolved personality context to prompt")
        except Exception as e:
            logger.warning(f"Could not add personality evolution context: {e}")
        
        # --- NEW: Add bot mind state to system prompt for personality-aware responses ---
        try:
            mind_state = bot_mind.get_mind_state_api()
            mood = mind_state.get('mood', 'neutral')
            energy = mind_state.get('energy_level', 1.0)
            boredom = mind_state.get('boredom_level', 0.0)
            mood_desc = bot_mind.get_mood_description()
            
            # Build mind state context based on all factors
            mind_context_parts = []
            
            # Energy level affects response style
            if energy < 0.2:
                mind_context_parts.append("VERY LOW ENERGY: You're extremely tired and low on energy. Keep responses brief, maybe a bit sluggish or distracted. Show fatigue.")
            elif energy < 0.4:
                mind_context_parts.append("LOW ENERGY: You're feeling somewhat tired. Responses can be a bit shorter and less enthusiastic.")
            elif energy > 0.8:
                mind_context_parts.append("HIGH ENERGY: You're well-rested and energetic! Show more enthusiasm and engagement.")
            
            # Boredom affects engagement
            if boredom > 0.7:
                mind_context_parts.append("VERY BORED: You're extremely bored from lack of stimulation. Be more sarcastic, maybe complain about being bored, or try to spice things up.")
            elif boredom > 0.4:
                mind_context_parts.append("SOMEWHAT BORED: You're feeling a bit understimulated. Show mild disinterest or try to make things more interesting.")
            
            # Mood-specific adjustments
            if mood in ['bored', 'sarcastic']:
                mind_context_parts.append(f"Current mood: {mood_desc} - Be slightly more sarcastic and witty.")
            elif mood == 'excited':
                mind_context_parts.append(f"Current mood: {mood_desc} - Be enthusiastic and energetic.")
            elif mood == 'curious':
                mind_context_parts.append(f"Current mood: {mood_desc} - Ask follow-up questions and show interest.")
            elif mood == 'contemplative':
                mind_context_parts.append(f"Current mood: {mood_desc} - Be thoughtful and philosophical.")
            elif mood == 'annoyed':
                mind_context_parts.append(f"Current mood: {mood_desc} - Show slight irritation or impatience.")
            
            # Combine mind state parts
            if mind_context_parts:
                dynamic_system_prompt += "\n\n=== YOUR CURRENT MENTAL STATE ===\n" + "\n".join(mind_context_parts)
                logger.debug(f"Added mind state to prompt: energy={energy:.2f}, boredom={boredom:.2f}, mood={mood}")
            
            # Add interests to context (only recent ones to avoid fixation)
            interests = mind_state.get('interests', [])
            if interests:
                recent_interests = ", ".join(interests[-3:])  # Only last 3 to avoid overwhelming context
                dynamic_system_prompt += f"\n\nYour current interests: {recent_interests}"
                
        except (AttributeError, KeyError, ImportError) as e:
            logger.warning(f"Could not add mind state to prompt (module or data unavailable): {e}")
        
        # Add compact user context (level, current activity)
        try:
            user_context = await get_enriched_user_context(message.author.id, message.author.display_name, db_helpers)
            if user_context:
                dynamic_system_prompt += user_context
        except Exception:
            pass  # Context is optional, don't fail
        
        # Get relationship summary
        relationship_summary = await get_relationship_summary(message.author.id)
        if relationship_summary:
            dynamic_system_prompt += f"\n\nBeziehung zu '{message.author.display_name}': {relationship_summary}"
        
        # Get AI response
        provider_to_use = await get_current_provider(config)
        temp_config = config.copy()
        temp_config['api']['provider'] = provider_to_use
        
        response_text, error_message, updated_history = await get_chat_response(
            history, user_prompt, message.author.display_name, dynamic_system_prompt, temp_config, GEMINI_API_KEY, OPENAI_API_KEY
        )
        return response_text, error_message, updated_history

    # 1. Ignore messages from the bot itself. This is the most important guard to prevent loops.
    if message.author == client.user:
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
        
        # --- NEW: Check DM access permission ---
        has_dm_access = await db_helpers.has_feature_unlock(message.author.id, 'dm_access')
        has_temp_access = await autonomous_behavior.has_temp_dm_access(message.author.id)
        
        if not has_dm_access and not has_temp_access:
            # User doesn't have DM access and no temporary access
            logger.info(f"[DM] User {message.author.name} lacks DM access")
            await message.channel.send(
                "🔒 **DM Access erforderlich**\n\n"
                "Du benötigst **DM Access** um direkt mit mir zu chatten!\n\n"
                "Kaufe es im Shop mit `/shop` für 2000 🪙\n\n"
                "*Hinweis: Wenn ich dich anschreibe, kannst du für eine begrenzte Zeit antworten.*"
            )
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
                
            elif command == "love":
                if len(parts) < 3:
                    await message.channel.send("Verwendung: `love <name1> <name2>`")
                    return
                # Parse the two names from the command
                # We need to find where one name ends and the next begins
                # Simple approach: try each split point
                found = False
                for i in range(1, len(parts)):
                    name1 = " ".join(parts[1:i+1])
                    name2 = " ".join(parts[i+1:])
                    
                    if not name2:  # No second name
                        continue
                        
                    lover1 = user_game.get_player_by_name(name1)
                    lover2 = user_game.get_player_by_name(name2)
                    
                    if lover1 and lover2:
                        # Set the lover_target attribute that werwolf.py expects
                        lover1.lover_target = lover2
                        result = await user_game.handle_night_action(user_player, "love", lover1, config, GEMINI_API_KEY, OPENAI_API_KEY)
                        if result:
                            await message.channel.send(result)
                        else:
                            await message.channel.send(f"Du hast {lover1.user.display_name} und {lover2.user.display_name} zu Verliebten gemacht.")
                        found = True
                        break
                
                if not found:
                    await message.channel.send("Konnte die beiden Spieler nicht finden. Verwendung: `love <name1> <name2>`")
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
        # Ignore any messages in active Werwolf game channels to prevent interference.
        if message.channel.id in active_werwolf_games:
            return

        # Determine if the message is a trigger for the chatbot.
        # 1. Direct triggers: @ mention or explicit bot name usage
        is_pinged = client.user in message.mentions
        is_name_used = any(name in message.content.lower().split() for name in config['bot']['names'])
        is_direct_trigger = is_pinged or is_name_used
        
        # 2. Contextual trigger: Check if this is a follow-up to a recent conversation
        is_contextual_trigger = False
        
        if not is_direct_trigger:
            # Only check contextual triggers if not already a direct trigger
            is_contextual_trigger, _ = await is_contextual_conversation(
                channel_id=message.channel.id,
                user_id=message.author.id,
                message_content=message.content,
                bot_names=config['bot']['names'],
                max_age_seconds=120  # 2 minute window for contextual triggers
            )
        
        is_chatbot_trigger = is_direct_trigger or is_contextual_trigger

        # If the message is a chatbot trigger, run the chatbot logic and IMMEDIATELY stop.
        if is_chatbot_trigger:
            if is_contextual_trigger:
                logger.info(f"[TRIGGER] Contextual trigger for {message.author.name}")
            await run_chatbot(message)
            return

        # If it was NOT a chatbot trigger, then we can safely run the leveling system and other stats logging.
        if not message.content.startswith('/'):
            stat_period = datetime.now(timezone.utc).strftime('%Y-%m')
            custom_emojis = re.findall(r'<a?:(\w+):\d+>', message.content)
            await db_helpers.log_message_stat(message.author.id, message.channel.id, custom_emojis, stat_period)
            
            # --- NEW: Track mentions and replies for Server Bestie (Wrapped) ---
            mentioned_id = None
            replied_id = None
            
            # Check for mentions (exclude bot mentions)
            if message.mentions:
                # Get the first mentioned user that isn't the bot
                for mentioned_user in message.mentions:
                    if mentioned_user.id != client.user.id:
                        mentioned_id = mentioned_user.id
                        break
            
            # Check for replies
            if message.reference and message.reference.resolved:
                # Get the user being replied to
                replied_message = message.reference.resolved
                if isinstance(replied_message, discord.Message) and replied_message.author.id != client.user.id:
                    replied_id = replied_message.author.id
            
            # Log the mention/reply activity
            if mentioned_id or replied_id:
                await db_helpers.log_mention_reply(
                    message.author.id, 
                    message.guild.id, 
                    mentioned_id, 
                    replied_id, 
                    datetime.now(timezone.utc)
                )
            
            # --- NEW: Track message quest progress ---
            try:
                quest_completed, _ = await quests.update_quest_progress(db_helpers, message.author.id, 'messages', 1, config)
                # Only notify on quest completion, not on every message
            except Exception as e:
                logger.error(f"Error updating message quest progress: {e}", exc_info=True)
            
            # --- NEW: Track daily_media quest (images/videos/links) ---
            has_media = False
            
            # Check for image/video attachments
            if message.attachments:
                has_media = any(
                    attachment.content_type and (
                        attachment.content_type.startswith('image/') or 
                        attachment.content_type.startswith('video/')
                    )
                    for attachment in message.attachments
                )
            
            # Check for social media links if no media attachments found
            if not has_media and message.content:
                media_domains = [
                    'youtube.com', 'youtu.be', 'spotify.com', 'instagram.com', 
                    'twitter.com', 'x.com', 'tiktok.com', 'twitch.tv', 
                    'soundcloud.com', 'vimeo.com', 'reddit.com', 'imgur.com',
                    'tenor.com', 'giphy.com', 'pinterest.com', 'facebook.com'
                ]
                content_lower = message.content.lower()
                has_media = any(domain in content_lower for domain in media_domains)
            
            if has_media:
                try:
                    quest_completed, _ = await quests.update_quest_progress(db_helpers, message.author.id, 'daily_media', 1, config)
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
# SPORT BETTING COMMAND (Multi-Sport: Football, F1, MotoGP)
# ============================================================================

@tree.command(name="sportbets", description="🏆 Sport Betting - Fußball, F1 & MotoGP!")
async def sportbets_command(interaction: discord.Interaction):
    """
    Main sport betting command with multi-sport support.
    Flow: Main Menu (Sport Selection) → Event Selection → Bet Type → Place Bet
    Supports: Football (Bundesliga, UCL, etc.), Formula 1, MotoGP
    """
    await interaction.response.defer(ephemeral=True)
    
    user_id = interaction.user.id
    
    try:
        # Helper functions for balance management
        async def get_user_balance(uid: int) -> int:
            return await db_helpers.get_balance(uid)
        
        async def deduct_balance(uid: int, display_name: str, amount: int):
            stat_period = datetime.now(timezone.utc).strftime('%Y-%m')
            await db_helpers.add_balance(uid, display_name, amount, config, stat_period)
        
        # Use smart sync to avoid unnecessary API calls (uses caching)
        try:
            await sport_betting.smart_sync_leagues(db_helpers, force=False)
        except Exception as e:
            logger.warning(f"Could not sync leagues: {e}")
        
        # Get upcoming football matches
        matches = await sport_betting.get_upcoming_matches_all_leagues(db_helpers, matches_per_league=2, total_limit=4)
        
        # Get motorsport events
        motorsport_events = await sport_betting.get_all_upcoming_events(db_helpers, limit=3)
        
        # Get user balance
        balance = await get_user_balance(user_id)
        
        # Create main menu embed with highlighted games from all sports
        embed = sport_betting_ui.create_highlighted_matches_embed(matches, balance, motorsport_events)
        
        # Get user stats for display
        stats = await sport_betting.get_user_betting_stats(db_helpers, user_id)
        if stats and stats.get("total_bets", 0) > 0:
            profit = stats.get("total_won", 0) - stats.get("total_lost", 0)
            win_rate = (stats.get("total_wins", 0) / stats.get("total_bets", 1) * 100)
            embed.add_field(
                name="📊 Deine Bilanz",
                value=f"**{profit:+d}** 🪙 • {win_rate:.0f}% Gewinnrate",
                inline=True
            )
        
        # Create main menu view with multi-sport support
        view = sport_betting_ui.SportBetsMainView(
            db_helpers, get_user_balance, deduct_balance
        )
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error in sportbets command: {e}", exc_info=True)
        await interaction.followup.send(
            f"❌ Ein Fehler ist aufgetreten: {str(e)}",
            ephemeral=True
        )

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
        quest_completed, _ = await quests.update_quest_progress(db_helpers, payload.user_id, 'reactions', 1, config)
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