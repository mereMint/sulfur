import mysql.connector
import json
from mysql.connector import errorcode, pooling
import time
import logging
import functools

# Setup logging
logger = logging.getLogger('Database')
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s'))
    logger.addHandler(handler)

# This file handles all database interactions for the bot.

db_pool = None

def db_operation(operation_name):
    """Decorator for database operations with automatic error handling and logging"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                logger.debug(f"[DB Operation] {operation_name} - Starting")
                result = await func(*args, **kwargs)
                logger.debug(f"[DB Operation] {operation_name} - Completed successfully")
                return result
            except mysql.connector.Error as err:
                logger.error(f"[DB Operation] {operation_name} - MySQL Error: {err}")
                logger.error(f"Error code: {err.errno}, SQLState: {err.sqlstate if hasattr(err, 'sqlstate') else 'N/A'}")
                return None
            except Exception as e:
                logger.error(f"[DB Operation] {operation_name} - Unexpected error: {e}")
                import traceback
                logger.error(traceback.format_exc())
                return None
        return wrapper
    return decorator

def get_xp_for_level(level):
    """Calculates the total XP needed to reach the next level."""
    # A common formula that increases with each level: 5 * (lvl^2) + 50 * lvl + 100
    return 5 * (level ** 2) + (50 * level) + 100


def init_db_pool(host, user, password, database):
    """Initializes the database connection pool."""
    global db_pool
    try:
        logger.info(f"Initializing connection pool: {user}@{host}/{database}")
        db_config = {
            'host': host, 
            'user': user, 
            'password': password, 
            'database': database,
            'autocommit': False,
            'pool_reset_session': True
        }
        db_pool = pooling.MySQLConnectionPool(
            pool_name="sulfur_pool", 
            pool_size=5, 
            **db_config
        )
        logger.info("Database connection pool initialized successfully")
    except mysql.connector.Error as err:
        logger.error(f"FATAL: Could not initialize database pool: {err}")
        logger.error(f"Error code: {err.errno}, Message: {err.msg}")
        db_pool = None
    except Exception as err:
        logger.error(f"FATAL: Unexpected error during database pool initialization: {err}")
        import traceback
        logger.error(traceback.format_exc())
        db_pool = None

def get_db_connection():
    """Establishes a connection to the database, with retries."""
    # This function is now only used for the initial table creation.
    # All other functions get a connection directly from the pool.
    if db_pool:
        try:
            return db_pool.get_connection()
        except mysql.connector.Error as err:
            logger.error(f"Failed to get connection from pool: {err}")
            return None
    else:
        logger.warning("Database pool not initialized, cannot get connection")
        return None

def initialize_database():
    """Creates the necessary tables if they don't exist."""
    cnx = get_db_connection()
    if not cnx:
        logger.error("Could not connect to DB for initialization. Database tables will not be created.")
        return

    cursor = cnx.cursor()
    logger.info("Starting database initialization...")
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                discord_id BIGINT PRIMARY KEY,
                display_name VARCHAR(255) NOT NULL,
                wins INT DEFAULT 0 NOT NULL,
                losses INT DEFAULT 0 NOT NULL,
                level INT DEFAULT 1 NOT NULL,
                xp INT DEFAULT 0 NOT NULL
            )
        """)
        # --- NEW: Add relationship summary column and chat history table ---
        cursor.execute("""
            ALTER TABLE players
            ADD COLUMN IF NOT EXISTS relationship_summary TEXT;
        """)
        # --- NEW: Add columns for presence tracking ---
        cursor.execute("""
            ALTER TABLE players
            ADD COLUMN IF NOT EXISTS last_seen TIMESTAMP NULL DEFAULT NULL,
            ADD COLUMN IF NOT EXISTS last_activity_name VARCHAR(255) NULL DEFAULT NULL;
        """)
        # --- NEW: Add columns for economy and spotify tracking ---
        cursor.execute("""
            ALTER TABLE players
            ADD COLUMN IF NOT EXISTS balance BIGINT DEFAULT 1000 NOT NULL;
        """)
        cursor.execute("""
            ALTER TABLE players
            ADD COLUMN IF NOT EXISTS spotify_history JSON NULL;
        """)
        # --- NEW: Add game_history column for persistent game stats ---
        cursor.execute("""
            ALTER TABLE players
            ADD COLUMN IF NOT EXISTS game_history JSON NULL;
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                channel_id BIGINT NOT NULL,
                role VARCHAR(10) NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # --- NEW: Table for managing voice channels ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS managed_voice_channels (
                owner_id BIGINT NOT NULL,
                guild_id BIGINT NOT NULL,
                channel_id BIGINT NULL,
                is_private BOOLEAN DEFAULT FALSE NOT NULL,
                allowed_users JSON,
                channel_name VARCHAR(100) NULL,
                user_limit INT DEFAULT 0,
                PRIMARY KEY (owner_id, guild_id),
                UNIQUE (channel_id)
            )
        """)
        # --- FIX: Migration for multi-guild support ---
        cursor.execute("SHOW COLUMNS FROM managed_voice_channels LIKE 'guild_id'")
        if not cursor.fetchone():
            print("Applying migration for multi-guild voice channels...")
            cursor.execute("ALTER TABLE managed_voice_channels DROP PRIMARY KEY, ADD COLUMN guild_id BIGINT NOT NULL FIRST, ADD PRIMARY KEY (owner_id, guild_id)")
            print("Migration complete.")

        # Ensure other columns for custom channel settings exist
        cursor.execute("""
            ALTER TABLE managed_voice_channels
            ADD COLUMN IF NOT EXISTS channel_name VARCHAR(100) NULL,
            ADD COLUMN IF NOT EXISTS user_limit INT DEFAULT 0;
        """)
        # --- NEW: Table for "Wrapped" monthly stats ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_monthly_stats (
                user_id BIGINT NOT NULL,
                stat_period VARCHAR(7) NOT NULL, -- e.g., '2024-11'
                message_count INT DEFAULT 0 NOT NULL,
                minutes_in_vc INT DEFAULT 0 NOT NULL,
                money_earned BIGINT DEFAULT 0 NOT NULL,
                channel_usage JSON, -- {'channel_id': count}
                emoji_usage JSON, -- {'emoji_name': count}
                activity_usage JSON, -- {'activity_name': count}
                PRIMARY KEY (user_id, stat_period)
            )
        """)
        # --- FIX: Add missing sulf_interactions column ---
        cursor.execute("""
            ALTER TABLE user_monthly_stats
            ADD COLUMN IF NOT EXISTS sulf_interactions INT DEFAULT 0 NOT NULL;
        """)
        # --- FIX: Add missing activity_usage column for Wrapped stats ---
        cursor.execute("""
            ALTER TABLE user_monthly_stats
            ADD COLUMN IF NOT EXISTS activity_usage JSON;
        """)
        # --- NEW: Add game_usage column for Wrapped stats ---
        cursor.execute("""
            ALTER TABLE user_monthly_stats
            ADD COLUMN IF NOT EXISTS game_usage JSON;
        """)
        # --- NEW: Add spotify_minutes column for Wrapped stats ---
        cursor.execute("""
            ALTER TABLE user_monthly_stats
            ADD COLUMN IF NOT EXISTS spotify_minutes JSON;
        """)
        # --- NEW: Table for Werwolf bot names ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS werwolf_bot_names (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE
            )
        """)
        # --- NEW: Tables for enhanced Wrapped stats ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS message_activity (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                guild_id BIGINT NOT NULL,
                mentioned_user_id BIGINT,
                replied_to_user_id BIGINT,
                message_timestamp DATETIME NOT NULL,
                INDEX(user_id, guild_id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS temp_vc_creations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                guild_id BIGINT NOT NULL,
                creation_timestamp DATETIME NOT NULL,
                INDEX(user_id, guild_id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS voice_sessions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                guild_id BIGINT NOT NULL,
                duration_seconds INT NOT NULL,
                session_end_timestamp DATETIME NOT NULL,
                INDEX(user_id, guild_id)
            )
        """)
        # --- REFACTORED: Table for detailed API usage tracking (per model) ---
        # Drop the old simple table if it exists to replace it with the new one.
        cursor.execute("DROP TABLE IF EXISTS api_usage;")
        cursor.execute("""
            CREATE TABLE api_usage (
                id INT AUTO_INCREMENT PRIMARY KEY,
                usage_date DATE NOT NULL,
                model_name VARCHAR(100) NOT NULL,
                call_count INT DEFAULT 0 NOT NULL,
                input_tokens INT DEFAULT 0 NOT NULL,
                output_tokens INT DEFAULT 0 NOT NULL,
                UNIQUE KEY `daily_model_usage` (`usage_date`, `model_name`)
            )
        """)
        cursor.execute("DROP EVENT IF EXISTS reset_daily_api_usage;") # Remove old event

        logger.info("Database tables checked/created successfully")
    except mysql.connector.Error as err:
        logger.error(f"Failed creating/modifying tables: {err}")
        logger.error(f"Error code: {err.errno}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        cursor.close()
        cnx.close()

# --- NEW: API Usage Tracking Functions ---

@db_operation("log_api_usage")
async def log_api_usage(model_name, input_tokens, output_tokens):
    """Logs the usage of an AI model, including token counts."""
    if not db_pool:
        logger.warning("Database pool not available, skipping API usage logging")
        return
        
    cnx = db_pool.get_connection()
    if not cnx: 
        return
    cursor = cnx.cursor()
    try:
        query = """
            INSERT INTO api_usage (usage_date, model_name, call_count, input_tokens, output_tokens)
            VALUES (CURDATE(), %s, 1, %s, %s)
            ON DUPLICATE KEY UPDATE
                call_count = call_count + 1,
                input_tokens = input_tokens + VALUES(input_tokens),
                output_tokens = output_tokens + VALUES(output_tokens);
        """
        cursor.execute(query, (model_name, input_tokens, output_tokens))
        cnx.commit()
        logger.debug(f"Logged API usage: {model_name} - IN:{input_tokens} OUT:{output_tokens}")
    finally:
        cursor.close()
        cnx.close()

# --- NEW: DB functions for enhanced Wrapped stats ---

@db_operation("log_mention_reply")
async def log_mention_reply(user_id, guild_id, mentioned_id, replied_id, timestamp):
    """Logs a mention or reply for Server Bestie stats."""
    if not mentioned_id and not replied_id:
        return
    if not db_pool:
        return
        
    cnx = db_pool.get_connection()
    if not cnx: return
    cursor = cnx.cursor()
    try:
        query = "INSERT INTO message_activity (user_id, guild_id, mentioned_user_id, replied_to_user_id, message_timestamp) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(query, (user_id, guild_id, mentioned_id, replied_id, timestamp))
        cnx.commit()
        logger.debug(f"Logged mention/reply: user {user_id} -> mentioned:{mentioned_id} replied:{replied_id}")
    finally:
        cursor.close()
        cnx.close()

@db_operation("log_temp_vc_creation")
async def log_temp_vc_creation(user_id, guild_id, timestamp):
    """Logs when a user creates a temporary voice channel."""
    if not db_pool:
        return
        
    cnx = db_pool.get_connection()
    if not cnx: return
    cursor = cnx.cursor()
    try:
        query = "INSERT INTO temp_vc_creations (user_id, guild_id, creation_timestamp) VALUES (%s, %s, %s)"
        cursor.execute(query, (user_id, guild_id, timestamp))
        cnx.commit()
        logger.debug(f"Logged temp VC creation for user {user_id}")
    finally:
        cursor.close()
        cnx.close()

@db_operation("log_vc_session")
async def log_vc_session(user_id, guild_id, duration_seconds, timestamp):
    """Logs a completed voice channel session duration."""
    if not db_pool:
        return
        
    cnx = db_pool.get_connection()
    if not cnx: return
    cursor = cnx.cursor()
    try:
        query = "INSERT INTO voice_sessions (user_id, guild_id, duration_seconds, session_end_timestamp) VALUES (%s, %s, %s, %s)"
        cursor.execute(query, (user_id, guild_id, duration_seconds, timestamp))
        cnx.commit()
        logger.debug(f"Logged VC session: user {user_id}, duration {duration_seconds}s")
    finally:
        cursor.close()
        cnx.close()

async def cleanup_custom_status_entries():
    """
    A one-time cleanup function to remove 'Custom Status' entries from JSON columns.
    This is useful after changing logging logic to clean up old, irrelevant data.
    """
    cnx = db_pool.get_connection()
    if not cnx:
        print("DB Cleanup: Could not connect to database.")
        return

    cursor = cnx.cursor(dictionary=True)
    try:
        # We'll check a sample of rows first to see if cleanup is likely needed.
        cursor.execute("SELECT user_id, stat_period, activity_usage, game_usage FROM user_monthly_stats WHERE activity_usage LIKE '%Custom Status%' OR game_usage LIKE '%Custom Status%' LIMIT 5")
        if not cursor.fetchall():
            print("DB Cleanup: No 'Custom Status' entries found. Skipping cleanup.")
            return

        print("DB Cleanup: Found 'Custom Status' entries. Starting cleanup process...")
        # This query removes the 'Custom Status' key from the JSON object if it exists.
        # It needs to be run for both activity_usage and game_usage columns.
        cursor.execute("UPDATE user_monthly_stats SET activity_usage = JSON_REMOVE(activity_usage, '$.\"Custom Status\"') WHERE JSON_CONTAINS_PATH(activity_usage, 'one', '$.\"Custom Status\"') = 1;")
        activity_rows = cursor.rowcount
        cursor.execute("UPDATE user_monthly_stats SET game_usage = JSON_REMOVE(game_usage, '$.\"Custom Status\"') WHERE JSON_CONTAINS_PATH(game_usage, 'one', '$.\"Custom Status\"') = 1;")
        game_rows = cursor.rowcount
        
        if activity_rows > 0 or game_rows > 0:
            cnx.commit()
            print(f"DB Cleanup: Successfully removed 'Custom Status' from {activity_rows} activity entries and {game_rows} game entries.")
        else:
            print("DB Cleanup: No rows needed updating.")

    except mysql.connector.Error as err:
        print(f"DB Cleanup Error: {err}")
    finally:
        cursor.close()
        cnx.close()

# --- NEW: Voice Channel Management DB Functions ---

async def get_owned_channel(owner_id, guild_id):
    """Fetches the channel ID owned by a user, if any."""
    cnx = db_pool.get_connection()
    if not cnx: return None
    cursor = cnx.cursor(dictionary=True)
    try:
        cursor.execute("SELECT channel_id FROM managed_voice_channels WHERE owner_id = %s AND guild_id = %s", (owner_id, guild_id))
        result = cursor.fetchone()
        return result['channel_id'] if result else None
    finally:
        cursor.close()
        cnx.close()

async def add_managed_channel(channel_id, owner_id, guild_id):
    """Adds a new managed channel to the database."""
    cnx = db_pool.get_connection()
    if not cnx: return
    cursor = cnx.cursor()
    try:
        # --- REFACTORED: Use INSERT...ON DUPLICATE KEY UPDATE to handle both new and returning users ---
        query = "INSERT INTO managed_voice_channels (owner_id, guild_id, channel_id) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE channel_id = VALUES(channel_id)"
        cursor.execute(query, (owner_id, guild_id, channel_id))
        cnx.commit()
    finally:
        cursor.close()
        cnx.close()

async def remove_managed_channel(channel_id, keep_owner_record=False):
    """
    Removes a managed channel from the database.
    If keep_owner_record is True, it sets channel_id to NULL instead of deleting the row,
    preserving the owner's settings.
    """
    cnx = db_pool.get_connection()
    if not cnx: return
    cursor = cnx.cursor()
    try:
        if keep_owner_record:
            # Set channel_id to NULL to show it's inactive but keep settings
            cursor.execute("UPDATE managed_voice_channels SET channel_id = NULL WHERE channel_id = %s", (channel_id,))
        else:
            # Permanently delete the record
            cursor.execute("DELETE FROM managed_voice_channels WHERE channel_id = %s", (channel_id,))
        cnx.commit()
    finally:
        cursor.close()
        cnx.close()

async def get_managed_channel_config(id, by_owner=False):
    """
    Retrieves the configuration for a managed channel.
    Can fetch by channel_id or owner_id.
    """
    cnx = db_pool.get_connection()
    if not cnx: return None
    cursor = cnx.cursor(dictionary=True)
    try:
        if by_owner: # by_owner now expects a tuple (owner_id, guild_id)
            # --- FIX: Use both owner_id and guild_id from the tuple for the lookup ---
            cursor.execute("SELECT * FROM managed_voice_channels WHERE owner_id = %s AND guild_id = %s", id)
        else:
            cursor.execute("SELECT * FROM managed_voice_channels WHERE channel_id = %s", (id,))
        result = cursor.fetchone()
        if result and result.get('allowed_users'):
            # Convert JSON string back to a Python list
            result['allowed_users'] = json.loads(result['allowed_users'])
        return result
    finally:
        cursor.close()
        cnx.close()

async def update_managed_channel_config(id, by_owner=False, is_private=None, allowed_users=None, name=None, limit=None):
    """Updates the configuration of a managed channel."""
    cnx = db_pool.get_connection()
    if not cnx: return
    cursor = cnx.cursor()
    try:
        updates, params = [], []
        if is_private is not None:
            updates.append("is_private = %s")
            params.append(is_private)
        if allowed_users is not None:
            updates.append("allowed_users = %s")
            params.append(json.dumps(list(allowed_users)))
        # --- FIX: Only update name/limit if they are provided and not empty/zero ---
        if name:
            updates.append("channel_name = %s")
            params.append(name)
        if limit is not None and limit >= 0:
            updates.append("user_limit = %s")
            params.append(limit)
        
        if not updates: return

        if by_owner: # by_owner now expects a tuple (owner_id, guild_id)
            # --- FIX: Use both owner_id and guild_id from the tuple for the update ---
            query = f"UPDATE managed_voice_channels SET {', '.join(updates)} WHERE owner_id = %s AND guild_id = %s"
            params.extend(id) # Add the (owner_id, guild_id) tuple to the parameters
        else:
            query = f"UPDATE managed_voice_channels SET {', '.join(updates)} WHERE channel_id = %s"
            params.append(id)
            
        cursor.execute(query, tuple(params))
        cnx.commit()
    finally:
        cursor.close()
        cnx.close()

async def get_all_managed_channels():
    """Fetches all managed channel IDs from the database for cleanup."""
    cnx = db_pool.get_connection()
    if not cnx: return []
    cursor = cnx.cursor(dictionary=True)
    try:
        cursor.execute("SELECT channel_id FROM managed_voice_channels WHERE channel_id IS NOT NULL")
        results = cursor.fetchall()
        return [row['channel_id'] for row in results]
    finally:
        cursor.close()
        cnx.close()

# --- NEW: Chat History and Relationship Functions ---

async def save_message_to_history(channel_id, role, content):
    """Saves a single message to the chat history table."""
    cnx = db_pool.get_connection()
    if not cnx:
        return

    cursor = cnx.cursor()
    try:
        query = "INSERT INTO chat_history (channel_id, role, content) VALUES (%s, %s, %s)"
        cursor.execute(query, (channel_id, role, content))
        cnx.commit()
    except mysql.connector.Error as err:
        print(f"Error saving chat history: {err}")
    finally:
        cursor.close()
        cnx.close()

async def save_bulk_history(channel_id, messages):
    """Saves a batch of messages to the chat history table."""
    if not messages:
        return

    cnx = db_pool.get_connection()
    if not cnx:
        return

    cursor = cnx.cursor()
    try:
        # Prepare data for executemany: list of tuples
        data_to_insert = [(channel_id, msg['role'], msg['content']) for msg in messages]
        query = "INSERT INTO chat_history (channel_id, role, content) VALUES (%s, %s, %s)"
        cursor.executemany(query, data_to_insert)
        cnx.commit()
        print(f"Successfully saved {cursor.rowcount} messages to history for channel {channel_id}.")
    except mysql.connector.Error as err:
        print(f"Error in save_bulk_history: {err}")
    finally:
        cursor.close()
        cnx.close()

async def clear_channel_history(channel_id):
    """Deletes all chat history for a specific channel."""
    cnx = db_pool.get_connection()
    if not cnx:
        return 0, "Database connection failed."

    cursor = cnx.cursor()
    try:
        query = "DELETE FROM chat_history WHERE channel_id = %s"
        cursor.execute(query, (channel_id,))
        deleted_rows = cursor.rowcount
        cnx.commit()
        return deleted_rows, None
    except mysql.connector.Error as err:
        print(f"Error clearing channel history: {err}")
        return 0, f"An SQL error occurred: {err}"
    finally:
        cursor.close()
        cnx.close()

async def get_chat_history(channel_id, limit):
    """Retrieves the last N messages for a channel from the database."""
    cnx = db_pool.get_connection()
    if not cnx:
        return []

    cursor = cnx.cursor(dictionary=True)
    history = []
    try:
        query = """
            SELECT role, content AS text FROM (
                SELECT role, content, created_at
                FROM chat_history
                WHERE channel_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            ) sub
            ORDER BY created_at ASC;
        """
        cursor.execute(query, (channel_id, limit))
        results = cursor.fetchall()
        # Format for Gemini API: {"role": "user", "parts": [{"text": "Hello"}]}
        for row in results:
            history.append({"role": row['role'], "parts": [{"text": row['text']}]})
        return history
    except mysql.connector.Error as err:
        print(f"Error getting chat history: {err}")
        return []
    finally:
        cursor.close()
        cnx.close()

async def get_relationship_summary(user_id):
    """Gets the current relationship summary for a user."""
    cnx = db_pool.get_connection()
    if not cnx: return None
    cursor = cnx.cursor(dictionary=True)
    try:
        cursor.execute("SELECT relationship_summary FROM players WHERE discord_id = %s", (user_id,))
        result = cursor.fetchone()
        return result['relationship_summary'] if result else None
    finally:
        cursor.close()
        cnx.close()

async def update_relationship_summary(user_id, summary):
    """Updates the relationship summary for a user."""
    cnx = db_pool.get_connection()
    if not cnx: return
    cursor = cnx.cursor()
    try:
        cursor.execute("UPDATE players SET relationship_summary = %s WHERE discord_id = %s", (summary, user_id))
        cnx.commit()
    finally:
        cursor.close()
        cnx.close()

# --- NEW: Werwolf Bot Name Functions ---

async def get_bot_name_pool_count():
    """Counts how many unused bot names are in the database."""
    cnx = db_pool.get_connection()
    if not cnx: return 0
    cursor = cnx.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM werwolf_bot_names")
        result = cursor.fetchone()
        return result[0] if result else 0
    finally:
        cursor.close()
        cnx.close()

async def add_bot_names_to_pool(names):
    """Adds a list of new bot names to the pool, ignoring duplicates."""
    if not names: return
    cnx = db_pool.get_connection()
    if not cnx: return
    cursor = cnx.cursor()
    try:
        # Use INSERT IGNORE to prevent errors on duplicate names
        query = "INSERT IGNORE INTO werwolf_bot_names (name) VALUES (%s)"
        data_to_insert = [(name,) for name in names]
        cursor.executemany(query, data_to_insert)
        cnx.commit()
        print(f"Added {cursor.rowcount} new names to the Werwolf bot name pool.")
    finally:
        cursor.close()
        cnx.close()

async def get_and_remove_bot_names(count):
    """Atomically fetches and removes a number of random names from the pool."""
    cnx = db_pool.get_connection()
    if not cnx: return []
    cursor = cnx.cursor(dictionary=True)
    names = []
    try:
        # This is a common pattern for an atomic "pop" from a DB table.
        cursor.execute("SELECT id, name FROM werwolf_bot_names ORDER BY RAND() LIMIT %s FOR UPDATE", (count,))
        rows = cursor.fetchall()
        if rows:
            names = [row['name'] for row in rows]
            ids_to_delete = [row['id'] for row in rows]
            cursor.execute("DELETE FROM werwolf_bot_names WHERE id IN ({})".format(','.join(['%s'] * len(ids_to_delete))), ids_to_delete)
        cnx.commit()
        return names
    finally:
        cursor.close()
        cnx.close()

async def update_player_stats(player_id, display_name, won_game):
    """Updates a player's win/loss record in the database."""
    cnx = db_pool.get_connection()
    if not cnx:
        return

    cursor = cnx.cursor()
    try:
        # Use INSERT ... ON DUPLICATE KEY UPDATE to either create or update the player
        if won_game:
            query = """
                INSERT INTO players (discord_id, display_name, wins)
                VALUES (%s, %s, 1)
                ON DUPLICATE KEY UPDATE display_name = VALUES(display_name), wins = wins + 1;
            """
        else:
            query = """
                INSERT INTO players (discord_id, display_name, losses)
                VALUES (%s, %s, 1)
                ON DUPLICATE KEY UPDATE display_name = VALUES(display_name), losses = losses + 1;
            """
        cursor.execute(query, (player_id, display_name))
        cnx.commit()
    except mysql.connector.Error as err:
        print(f"Error updating player stats: {err}")
    finally:
        cursor.close()
        cnx.close()

async def update_user_presence(user_id, display_name, status, activity_name):
    """Updates a user's presence information in the database."""
    cnx = db_pool.get_connection()
    if not cnx:
        return

    cursor = cnx.cursor()
    try:
        # Use INSERT ... ON DUPLICATE KEY UPDATE to create or update the player
        # Only update last_seen if the status is not offline.
        query = """
            INSERT INTO players (discord_id, display_name, last_seen, last_activity_name)
            VALUES (%s, %s, CASE WHEN %s != 'offline' THEN CURRENT_TIMESTAMP ELSE NULL END, %s)
            ON DUPLICATE KEY UPDATE
                display_name = VALUES(display_name),
                last_seen = CASE WHEN %s != 'offline' THEN CURRENT_TIMESTAMP ELSE players.last_seen END,
                last_activity_name = VALUES(last_activity_name);
        """
        cursor.execute(query, (user_id, display_name, status, activity_name, status))
        cnx.commit()
    finally:
        cursor.close()
        cnx.close()

@db_operation("add_balance")
async def add_balance(user_id, display_name, amount_to_add, config, stat_period=None):
    """Adds an amount to a user's balance, creating the user if they don't exist."""
    if not db_pool:
        logger.warning("Database pool not available, skipping balance addition")
        return
        
    cnx = db_pool.get_connection()
    if not cnx:
        return

    cursor = cnx.cursor()
    try:
        starting_balance = config['modules']['economy']['starting_balance']
        query = """
            INSERT INTO players (discord_id, display_name, balance) VALUES (%s, %s, %s + %s)
            ON DUPLICATE KEY UPDATE
                balance = balance + %s, display_name = VALUES(display_name);
        """
        cursor.execute(query, (user_id, display_name, starting_balance, amount_to_add, amount_to_add))
        cnx.commit()

        # --- NEW: Log money earned for Wrapped ---
        if stat_period:
            stat_query = """
                INSERT INTO user_monthly_stats (user_id, stat_period, money_earned)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE money_earned = money_earned + VALUES(money_earned);
            """
            cursor.execute(stat_query, (user_id, stat_period, amount_to_add))
            cnx.commit()
            
        logger.debug(f"Added {amount_to_add} balance to user {user_id}")
    finally:
        cursor.close()
        cnx.close()

async def update_spotify_history(client, user_id: int, display_name: str, song_title: str, song_artist: str):
    """
    Increments the play count for a song in a user's persistent Spotify history.
    The history is stored as a JSON object mapping 'song by artist' to a play count.
    """
    cnx = db_pool.get_connection()
    if not cnx: return

    print(f"    - [DB] Updating spotify_history for {display_name} ({user_id}) with song: '{song_title}'")
    cursor = cnx.cursor()
    song_key = f"{song_title} by {song_artist}"
    try:
        # --- REFACTORED: Use a more robust transaction to handle all cases. ---
        # Step 1: Ensure the player exists.
        cursor.execute(
            "INSERT INTO players (discord_id, display_name) VALUES (%s, %s) ON DUPLICATE KEY UPDATE display_name = VALUES(display_name)",
            (user_id, display_name)
        )

        # Step 2: Atomically increment the count for the song in the JSON object.
        # This correctly handles cases where spotify_history is NULL or the song key doesn't exist yet.
        update_query = """
            UPDATE players
            SET spotify_history = JSON_SET(
                COALESCE(spotify_history, '{}'),
                CONCAT('$."', %s, '"'),
                COALESCE(JSON_UNQUOTE(JSON_EXTRACT(spotify_history, CONCAT('$."', %s, '"'))), 0) + 1
            )
            WHERE discord_id = %s;
        """
        cursor.execute(update_query, (song_key, song_key, user_id))
        cnx.commit()
    finally:
        cursor.close()
        cnx.close()

async def log_game_session(user_id, stat_period, game_name, duration_minutes):
    """
    Logs a completed game session, updating both monthly and all-time stats.
    """
    cnx = db_pool.get_connection()
    if not cnx: return
    cursor = cnx.cursor()
    try:
        # --- Update Monthly Stats (user_monthly_stats table) ---
        # This query increments the play count and total minutes for the game in the current month.
        monthly_query = """
            INSERT INTO user_monthly_stats (user_id, stat_period, game_usage)
            VALUES (%s, %s, JSON_OBJECT(%s, JSON_OBJECT('play_count', 1, 'total_minutes', %s)))
            ON DUPLICATE KEY UPDATE
                game_usage = JSON_SET(
                    COALESCE(game_usage, '{}'),
                    CONCAT('$."', %s, '".play_count'), COALESCE(JSON_UNQUOTE(JSON_EXTRACT(game_usage, CONCAT('$."', %s, '".play_count'))), 0) + 1,
                    CONCAT('$."', %s, '".total_minutes'), COALESCE(JSON_UNQUOTE(JSON_EXTRACT(game_usage, CONCAT('$."', %s, '".total_minutes'))), 0) + %s
                );
        """
        cursor.execute(monthly_query, (user_id, stat_period, game_name, duration_minutes, game_name, game_name, game_name, game_name, duration_minutes))

        # --- Update All-Time Stats (players table) ---
        # This query increments the total sessions and total minutes ever played for the game.
        all_time_query = """
            UPDATE players
            SET game_history = JSON_SET(
                COALESCE(game_history, '{}'),
                CONCAT('$."', %s, '".total_sessions_ever'), COALESCE(JSON_UNQUOTE(JSON_EXTRACT(game_history, CONCAT('$."', %s, '".total_sessions_ever'))), 0) + 1,
                CONCAT('$."', %s, '".total_minutes_ever'), COALESCE(JSON_UNQUOTE(JSON_EXTRACT(game_history, CONCAT('$."', %s, '".total_minutes_ever'))), 0) + %s
            )
            WHERE discord_id = %s;
        """
        # We also need to ensure the player exists in the players table first.
        cursor.execute("INSERT INTO players (discord_id, display_name) VALUES (%s, %s) ON DUPLICATE KEY UPDATE display_name=VALUES(display_name)", (user_id, "Player"))
        cursor.execute(all_time_query, (game_name, game_name, game_name, game_name, duration_minutes, user_id))

        cnx.commit()
        print(f"    - [DB] Logged game session for {user_id}: {duration_minutes:.2f} mins of '{game_name}'")
    except mysql.connector.Error as err:
        print(f"Error in log_game_session: {err}")
    finally:
        cursor.close()
        cnx.close()

# --- NEW: "Wrapped" Feature DB Functions ---

async def log_message_stat(user_id, channel_id, emoji_list, stat_period):
    """Logs message count, channel usage, and emoji usage for the Wrapped feature."""
    # This function is now optimized to perform all logging in a single query.
    cnx = db_pool.get_connection()
    if not cnx: return

    cursor = cnx.cursor()
    try:
        # Build the dynamic part of the query for emoji usage
        emoji_updates = []
        params = []
        for emoji_name in emoji_list:
            # MariaDB requires quoting numeric-like keys in JSON paths.
            # We use CONCAT to build the path safely with parameter binding.
            emoji_updates.append("""
                emoji_usage = JSON_SET(
                    COALESCE(emoji_usage, '{}'),
                    CONCAT('$.', %s),
                    COALESCE(JSON_UNQUOTE(JSON_EXTRACT(emoji_usage, CONCAT('$.', %s))), 0) + 1
                )
            """)
            params.extend([emoji_name, emoji_name])

        emoji_sql_part = ", " + ", ".join(emoji_updates) if emoji_updates else ""

        query = f"""
            INSERT INTO user_monthly_stats (user_id, stat_period, message_count, channel_usage, emoji_usage)
            VALUES (%s, %s, 1, JSON_OBJECT(%s, 1), %s)
            ON DUPLICATE KEY UPDATE
                message_count = message_count + 1,
                channel_usage = JSON_SET(COALESCE(channel_usage, '{{}}'), CONCAT('$.', %s), COALESCE(JSON_UNQUOTE(JSON_EXTRACT(channel_usage, CONCAT('$.', %s))), 0) + 1)
                {emoji_sql_part};
        """
        initial_emoji_json = json.dumps({emoji: 1 for emoji in emoji_list})
        final_params = (user_id, stat_period, str(channel_id), initial_emoji_json, str(channel_id), str(channel_id)) + tuple(params)
        cursor.execute(query, final_params)
        cnx.commit()
    except mysql.connector.Error as err:
        print(f"Error in log_message_stat: {err}")
    finally:
        cursor.close()
        cnx.close()

async def log_vc_minutes(user_id, minutes_to_add, stat_period):
    """Logs minutes spent in a voice channel."""
    cnx = db_pool.get_connection()
    if not cnx: return
    cursor = cnx.cursor()
    try:
        query = """
            INSERT INTO user_monthly_stats (user_id, stat_period, minutes_in_vc) VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE minutes_in_vc = minutes_in_vc + VALUES(minutes_in_vc);
        """
        cursor.execute(query, (user_id, stat_period, minutes_to_add))
        cnx.commit()
    except mysql.connector.Error as err:
        print(f"Error in log_vc_minutes: {err}")
    finally:
        cursor.close()
        cnx.close()

async def log_stat_increment(user_id, stat_period, column_name, key=None, amount=1):
    """A generic function to increment a stat or a key within a JSON column."""
    cnx = db_pool.get_connection()
    if not cnx: return
    cursor = cnx.cursor()
    try:
        if key: # It's a JSON column
            # Safely construct the JSON path using CONCAT
            # --- FIX: Correctly use the 'amount' parameter for both INSERT and UPDATE ---
            query = f"""
                INSERT INTO user_monthly_stats (user_id, stat_period, {column_name}) VALUES (%s, %s, JSON_OBJECT(%s, %s))
                ON DUPLICATE KEY UPDATE {column_name} = JSON_SET(COALESCE({column_name}, '{{}}'), CONCAT('$.', %s), COALESCE(JSON_UNQUOTE(JSON_EXTRACT({column_name}, CONCAT('$.', %s))), 0) + %s);
            """
            params = (user_id, stat_period, key, amount, key, key, amount)
        else: # It's a simple INT column
            query = f"INSERT INTO user_monthly_stats (user_id, stat_period, {column_name}) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE {column_name} = {column_name} + %s;"
            params = (user_id, stat_period, amount, amount)
        cursor.execute(query, params)
        cnx.commit()
    except mysql.connector.Error as err:
        print(f"Error in log_stat_increment for column '{column_name}': {err}")
    finally:
        cursor.close()
        cnx.close()

async def get_wrapped_stats_for_period(stat_period):
    """Fetches all user stats for a given Wrapped period."""
    cnx = db_pool.get_connection()
    if not cnx: return []
    cursor = cnx.cursor(dictionary=True)
    try:
        query = "SELECT * FROM user_monthly_stats WHERE stat_period = %s"
        cursor.execute(query, (stat_period,))
        return cursor.fetchall()
    finally:
        cursor.close()
        cnx.close()

async def get_spotify_history(user_id):
    """Fetches the full Spotify history for a user."""
    cnx = db_pool.get_connection()
    if not cnx: return None
    cursor = cnx.cursor(dictionary=True)
    try:
        cursor.execute("SELECT spotify_history FROM players WHERE discord_id = %s", (user_id,))
        result = cursor.fetchone()
        print(f"    [DB] get_spotify_history for {user_id}: Raw result = {result}")
        if result and result.get('spotify_history'):
            return json.loads(result['spotify_history'])
        print(f"    [DB] get_spotify_history for {user_id}: No valid history found in result.")
        return None
    except mysql.connector.Error as err:
        print(f"Error fetching spotify history: {err}")
        return None
    finally:
        cursor.close()
        cnx.close()

@db_operation("add_xp")
async def add_xp(user_id, display_name, xp_to_add):
    """Adds XP to a user and handles level ups."""
    if not db_pool:
        logger.warning("Database pool not available, skipping XP addition")
        return None
        
    cnx = db_pool.get_connection()
    if not cnx:
        return None

    cursor = cnx.cursor(dictionary=True)
    new_level = None
    try:
        # Add XP and create player if they don't exist
        query = """
            INSERT INTO players (discord_id, display_name, xp)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE display_name = VALUES(display_name), xp = xp + VALUES(xp);
        """
        cursor.execute(query, (user_id, display_name, xp_to_add))

        # Get current level and XP
        cursor.execute("SELECT level, xp FROM players WHERE discord_id = %s", (user_id,))
        player = cursor.fetchone()

        if player:
            current_level = player['level']
            current_xp = player['xp']
            xp_needed = get_xp_for_level(current_level)

            # Check for level up
            if current_xp >= xp_needed:
                new_level = current_level + 1
                remaining_xp = current_xp - xp_needed
                cursor.execute(
                    "UPDATE players SET level = %s, xp = %s WHERE discord_id = %s",
                    (new_level, remaining_xp, user_id)
                )

        cnx.commit()
        logger.debug(f"Added {xp_to_add} XP to user {user_id}. New level: {new_level}" if new_level else f"Added {xp_to_add} XP to user {user_id}")
        return new_level
    finally:
        cursor.close()
        cnx.close()

@db_operation("get_player_rank")
async def get_player_rank(user_id):
    """Fetches a player's level, xp, and global rank."""
    if not db_pool:
        return None, "Konnte keine Verbindung zur Datenbank herstellen."
        
    cnx = db_pool.get_connection()
    if not cnx:
        return None, "Konnte keine Verbindung zur Datenbank herstellen."

    cursor = cnx.cursor(dictionary=True)
    try:
        # Find the rank of the user
        # --- FIX: Also select wins and losses for the /rank command ---
        query = """
            SELECT p.discord_id, p.display_name, p.level, p.xp, p.wins, p.losses,
                   (SELECT COUNT(*) + 1 FROM players AS r WHERE r.level > p.level OR (r.level = p.level AND r.xp > p.xp)) AS `rank`
            FROM players AS p
            WHERE p.discord_id = %s;
        """
        cursor.execute(query, (user_id,))
        result = cursor.fetchone()
        logger.debug(f"Fetched rank for user {user_id}: {result['rank'] if result else 'Not found'}")
        return result, None
    finally:
        cursor.close()
        cnx.close()

@db_operation("get_level_leaderboard")
async def get_level_leaderboard():
    """Fetches the top 10 players by level and XP."""
    if not db_pool:
        logger.warning("Database pool not available")
        return []
        
    cnx = db_pool.get_connection()
    if not cnx:
        return None, "Konnte keine Verbindung zur Datenbank herstellen."

    cursor = cnx.cursor(dictionary=True)
    try:
        query = "SELECT display_name, level, xp FROM players ORDER BY level DESC, xp DESC LIMIT 10"
        cursor.execute(query)
        results = cursor.fetchall()
        return results, None
    except mysql.connector.Error as err:
        print(f"Error fetching level leaderboard: {err}")
        return None, "Fehler beim Abrufen des Leaderboards."
    finally:
        cursor.close()
        cnx.close()

async def get_player_profile(user_id):
    """Fetches all relevant stats for a user's profile."""
    cnx = db_pool.get_connection()
    if not cnx:
        return None, "Database connection failed."

    cursor = cnx.cursor(dictionary=True)
    try:
        # This query joins the player's main stats with their rank calculation.
        query = """
            SELECT p.*,
                   (SELECT COUNT(*) + 1 FROM players AS r WHERE r.level > p.level OR (r.level = p.level AND r.xp > p.xp)) AS `rank`
            FROM players AS p
            WHERE p.discord_id = %s;
        """
        cursor.execute(query, (user_id,))
        result = cursor.fetchone()
        return result, None
    except mysql.connector.Error as err:
        print(f"Error fetching player profile: {err}")
        return None, "An error occurred while fetching the profile."
    finally:
        cursor.close()
        cnx.close()

async def get_leaderboard():
    """Fetches the top 10 players by wins."""
    cnx = db_pool.get_connection()
    if not cnx:
        return None, "Konnte keine Verbindung zur Datenbank herstellen."

    cursor = cnx.cursor(dictionary=True)
    try:
        query = "SELECT display_name, wins, losses FROM players ORDER BY wins DESC LIMIT 10"
        cursor.execute(query)
        results = cursor.fetchall()
        return results, None
    except mysql.connector.Error as err:
        print(f"Error fetching leaderboard: {err}")
        return None, "Fehler beim Abrufen des Leaderboards."
    finally:
        cursor.close()
        cnx.close()

async def get_user_wrapped_stats(user_id, stat_period):
    """Fetches the Wrapped stats for a single user for a given period."""
    cnx = db_pool.get_connection()
    if not cnx: return None
    cursor = cnx.cursor(dictionary=True)
    try:
        query = "SELECT * FROM user_monthly_stats WHERE user_id = %s AND stat_period = %s"
        cursor.execute(query, (user_id, stat_period))
        return cursor.fetchone()
    except mysql.connector.Error as err:
        print(f"Error in get_user_wrapped_stats: {err}")
        return None
    finally:
        cursor.close()
        cnx.close()

async def get_wrapped_extra_stats(user_id, stat_period):
    """
    Fetches the new Wrapped stats (Bestie, Prime Time, VC stats) for a user.
    """
    cnx = db_pool.get_connection()
    if not cnx: return None
    cursor = cnx.cursor(dictionary=True)
    
    start_date = f"{stat_period}-01"
    # A bit of a hack to get the end date of the month
    from datetime import datetime, timedelta
    next_month = (datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=32)).replace(day=1)
    end_date = (next_month - timedelta(days=1)).strftime("%Y-%m-%d")

    stats = {
        "server_bestie_id": None,
        "prime_time_hour": None,
        "temp_vcs_created": 0,
        "longest_vc_session_seconds": 0
    }

    try:
        # 1. Server Bestie
        # This query combines mentions and replies, groups them, and finds the top one.
        bestie_query = """
            SELECT bestie_id, COUNT(*) as interaction_count FROM (
                SELECT mentioned_user_id as bestie_id FROM message_activity WHERE user_id = %s AND mentioned_user_id IS NOT NULL AND DATE(message_timestamp) BETWEEN %s AND %s
                UNION ALL
                SELECT replied_to_user_id as bestie_id FROM message_activity WHERE user_id = %s AND replied_to_user_id IS NOT NULL AND DATE(message_timestamp) BETWEEN %s AND %s
            ) as interactions
            GROUP BY bestie_id ORDER BY interaction_count DESC LIMIT 1;
        """
        cursor.execute(bestie_query, (user_id, start_date, end_date, user_id, start_date, end_date))
        bestie_result = cursor.fetchone()
        if bestie_result:
            stats["server_bestie_id"] = bestie_result['bestie_id']

        # 2. Prime Time
        prime_time_query = "SELECT HOUR(message_timestamp) as hour, COUNT(*) as count FROM message_activity WHERE user_id = %s AND DATE(message_timestamp) BETWEEN %s AND %s GROUP BY hour ORDER BY count DESC LIMIT 1;"
        cursor.execute(prime_time_query, (user_id, start_date, end_date))
        prime_time_result = cursor.fetchone()
        if prime_time_result:
            stats["prime_time_hour"] = prime_time_result['hour']

        # 3. Temp VCs Created
        temp_vc_query = "SELECT COUNT(*) as count FROM temp_vc_creations WHERE user_id = %s AND DATE(creation_timestamp) BETWEEN %s AND %s;"
        cursor.execute(temp_vc_query, (user_id, start_date, end_date))
        temp_vc_result = cursor.fetchone()
        if temp_vc_result:
            stats["temp_vcs_created"] = temp_vc_result['count']

        # 4. Longest VC Session
        longest_session_query = "SELECT MAX(duration_seconds) as longest_session FROM voice_sessions WHERE user_id = %s AND DATE(session_end_timestamp) BETWEEN %s AND %s;"
        cursor.execute(longest_session_query, (user_id, start_date, end_date))
        longest_session_result = cursor.fetchone()
        if longest_session_result and longest_session_result['longest_session']:
            stats["longest_vc_session_seconds"] = longest_session_result['longest_session']

        return stats
    except mysql.connector.Error as err:
        print(f"Error in get_wrapped_extra_stats: {err}")
        return stats # Return default stats on error
    finally:
        cursor.close()
        cnx.close()