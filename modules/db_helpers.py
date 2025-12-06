import mysql.connector
import json
from mysql.connector import errorcode, pooling
from decimal import Decimal
import time
import logging
import functools
import traceback

# Setup logging
logger = logging.getLogger('Database')
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s'))
    logger.addHandler(handler)

# This file handles all database interactions for the bot.

db_pool = None

def convert_decimals(obj):
    """
    Recursively converts Decimal objects to int or float for JSON serialization.
    
    Args:
        obj: Any Python object (dict, list, Decimal, etc.)
    
    Returns:
        The same object with all Decimal values converted to int or float
    """
    if isinstance(obj, Decimal):
        # Convert to int if it's a whole number, otherwise float
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    elif isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_decimals(item) for item in obj)
    else:
        return obj

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
            'pool_reset_session': True,
            'get_warnings': True,
            'raise_on_warnings': False
        }
        db_pool = pooling.MySQLConnectionPool(
            pool_name="sulfur_pool", 
            pool_size=10,  # Increased from 5 to 10 to handle concurrent operations like detective game
            **db_config
        )
        logger.info("Database connection pool initialized successfully (size: 10)")
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
        max_retries = 3
        retry_delay = 0.1  # 100ms
        for attempt in range(max_retries):
            try:
                return db_pool.get_connection()
            except mysql.connector.errors.PoolError as err:
                if "Failed getting connection; pool exhausted" in str(err):
                    if attempt < max_retries - 1:
                        logger.warning(f"Pool exhausted, retry {attempt + 1}/{max_retries} after {retry_delay}s")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        logger.error(f"Failed to get connection from pool after {max_retries} retries: pool exhausted")
                        return None
                else:
                    logger.error(f"Failed to get connection from pool: {err}")
                    return None
            except mysql.connector.Error as err:
                logger.error(f"Failed to get connection from pool: {err}")
                return None
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
        # Check and add columns only if they don't exist (MySQL doesn't support IF NOT EXISTS for ALTER TABLE ADD COLUMN)
        cursor.execute("SHOW COLUMNS FROM players LIKE 'relationship_summary'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE players ADD COLUMN relationship_summary TEXT")
        
        # --- NEW: Add columns for presence tracking ---
        cursor.execute("SHOW COLUMNS FROM players LIKE 'last_seen'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE players ADD COLUMN last_seen TIMESTAMP NULL DEFAULT NULL, ADD COLUMN last_activity_name VARCHAR(255) NULL DEFAULT NULL")
        
        # --- NEW: Add columns for economy and spotify tracking ---
        cursor.execute("SHOW COLUMNS FROM players LIKE 'balance'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE players ADD COLUMN balance BIGINT DEFAULT 1000 NOT NULL")
        
        cursor.execute("SHOW COLUMNS FROM players LIKE 'spotify_history'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE players ADD COLUMN spotify_history JSON NULL")
        
        # --- NEW: Add game_history column for persistent game stats ---
        cursor.execute("SHOW COLUMNS FROM players LIKE 'game_history'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE players ADD COLUMN game_history JSON NULL")
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
        cursor.execute("SHOW COLUMNS FROM managed_voice_channels LIKE 'channel_name'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE managed_voice_channels ADD COLUMN channel_name VARCHAR(100) NULL, ADD COLUMN user_limit INT DEFAULT 0")
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
        cursor.execute("SHOW COLUMNS FROM user_monthly_stats LIKE 'sulf_interactions'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE user_monthly_stats ADD COLUMN sulf_interactions INT DEFAULT 0 NOT NULL")
        
        # --- FIX: Add missing activity_usage column for Wrapped stats ---
        cursor.execute("SHOW COLUMNS FROM user_monthly_stats LIKE 'activity_usage'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE user_monthly_stats ADD COLUMN activity_usage JSON")
        
        # --- NEW: Add game_usage column for Wrapped stats ---
        cursor.execute("SHOW COLUMNS FROM user_monthly_stats LIKE 'game_usage'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE user_monthly_stats ADD COLUMN game_usage JSON")
        
        # --- NEW: Add spotify_minutes column for Wrapped stats ---
        cursor.execute("SHOW COLUMNS FROM user_monthly_stats LIKE 'spotify_minutes'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE user_monthly_stats ADD COLUMN spotify_minutes JSON")
        # --- NEW: Table for Werwolf bot names ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS werwolf_bot_names (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE
            )
        """)
        # --- NEW: Feature unlocks and simple economy tracking tables (used by shop) ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feature_unlocks (
                user_id BIGINT NOT NULL,
                feature_name VARCHAR(64) NOT NULL,
                purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, feature_name)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transaction_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                transaction_type VARCHAR(32) NOT NULL,
                amount BIGINT NOT NULL,
                balance_after BIGINT NOT NULL,
                description VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        
        # --- NEW: Conversation Context Table ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_context (
                user_id BIGINT NOT NULL,
                channel_id BIGINT NOT NULL,
                last_bot_message_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_user_message TEXT,
                last_bot_response TEXT,
                PRIMARY KEY (user_id, channel_id),
                INDEX(last_bot_message_at)
            )
        """)
        
        # --- NEW: AI Model Usage Tracking Table ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_model_usage (
                id INT AUTO_INCREMENT PRIMARY KEY,
                model_name VARCHAR(100) NOT NULL,
                feature VARCHAR(100) NOT NULL,
                call_count INT DEFAULT 0 NOT NULL,
                input_tokens INT DEFAULT 0 NOT NULL,
                output_tokens INT DEFAULT 0 NOT NULL,
                total_cost DECIMAL(10, 6) DEFAULT 0.0 NOT NULL,
                usage_date DATE NOT NULL,
                UNIQUE KEY `daily_model_feature_usage` (`usage_date`, `model_name`, `feature`)
            )
        """)
        
        # --- NEW: Emoji Descriptions Table ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS emoji_descriptions (
                emoji_id BIGINT PRIMARY KEY,
                emoji_name VARCHAR(255) NOT NULL,
                description TEXT,
                usage_context TEXT,
                image_url TEXT,
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # --- NEW: Wrapped Registrations Table ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wrapped_registrations (
                user_id BIGINT PRIMARY KEY,
                username VARCHAR(255),
                opted_out BOOLEAN DEFAULT FALSE NOT NULL,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        
        # --- NEW: User Customization Table for equipped colors and profile settings ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_customization (
                user_id BIGINT PRIMARY KEY,
                equipped_color VARCHAR(7),
                embed_color VARCHAR(7),
                profile_background VARCHAR(255),
                language VARCHAR(2) DEFAULT 'de',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        
        # Add language column if it doesn't exist (for tables created before this column was added)
        cursor.execute("SHOW COLUMNS FROM user_customization LIKE 'language'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE user_customization ADD COLUMN language VARCHAR(2) DEFAULT 'de'")
        
        # --- NEW: Quest System Tables ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_quests (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                quest_date DATE NOT NULL,
                quest_type VARCHAR(50) NOT NULL,
                target_value INT NOT NULL,
                current_progress INT NOT NULL DEFAULT 0,
                completed BOOLEAN NOT NULL DEFAULT FALSE,
                reward_claimed BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_user_date (user_id, quest_date),
                INDEX idx_user_type_date (user_id, quest_type, quest_date)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_economy (
                user_id BIGINT PRIMARY KEY,
                last_daily_claim TIMESTAMP NULL,
                total_earned BIGINT NOT NULL DEFAULT 0,
                total_spent BIGINT NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_stats (
                user_id BIGINT NOT NULL,
                display_name VARCHAR(255) NOT NULL,
                username VARCHAR(255) NULL,
                stat_period VARCHAR(7) NOT NULL,
                balance BIGINT NOT NULL DEFAULT 0,
                messages_sent INT NOT NULL DEFAULT 0,
                voice_minutes INT NOT NULL DEFAULT 0,
                quests_completed INT NOT NULL DEFAULT 0,
                games_played INT NOT NULL DEFAULT 0,
                games_won INT NOT NULL DEFAULT 0,
                total_bet INT NOT NULL DEFAULT 0,
                total_won INT NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, stat_period),
                INDEX idx_period (stat_period)
            )
        """)
        
        # Add display_name and username columns if they don't exist (for existing tables)
        cursor.execute("SHOW COLUMNS FROM user_stats LIKE 'display_name'")
        if not cursor.fetchone():
            logger.info("Adding display_name column to user_stats table")
            cursor.execute("ALTER TABLE user_stats ADD COLUMN display_name VARCHAR(255) NOT NULL DEFAULT 'Unknown' AFTER user_id")
        
        cursor.execute("SHOW COLUMNS FROM user_stats LIKE 'username'")
        if not cursor.fetchone():
            logger.info("Adding username column to user_stats table")
            cursor.execute("ALTER TABLE user_stats ADD COLUMN username VARCHAR(255) NULL AFTER display_name")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS monthly_quest_completion (
                user_id BIGINT NOT NULL,
                completion_date DATE NOT NULL,
                bonus_claimed BOOLEAN NOT NULL DEFAULT FALSE,
                PRIMARY KEY (user_id, completion_date),
                INDEX idx_user_month (user_id, completion_date)
            )
        """)
        
        # --- NEW: Detective Game Tables ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS detective_cases (
                case_id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                description TEXT NOT NULL,
                location VARCHAR(255) NOT NULL,
                victim VARCHAR(255) NOT NULL,
                suspects JSON NOT NULL,
                murderer_index INT NOT NULL,
                evidence JSON NOT NULL,
                hints JSON NOT NULL,
                difficulty INT NOT NULL DEFAULT 1,
                case_hash VARCHAR(64) NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_difficulty (difficulty),
                INDEX idx_case_hash (case_hash)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS detective_user_stats (
                user_id BIGINT PRIMARY KEY,
                current_difficulty INT NOT NULL DEFAULT 1,
                cases_solved INT NOT NULL DEFAULT 0,
                cases_failed INT NOT NULL DEFAULT 0,
                total_cases_played INT NOT NULL DEFAULT 0,
                cases_at_current_difficulty INT NOT NULL DEFAULT 0,
                last_played_at TIMESTAMP NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS detective_user_progress (
                user_id BIGINT NOT NULL,
                case_id INT NOT NULL,
                completed BOOLEAN NOT NULL DEFAULT FALSE,
                solved BOOLEAN NOT NULL DEFAULT FALSE,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP NULL,
                PRIMARY KEY (user_id, case_id),
                INDEX idx_user_completed (user_id, completed),
                FOREIGN KEY (case_id) REFERENCES detective_cases(case_id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trolly_responses (
                response_id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                display_name VARCHAR(255) NOT NULL,
                problem_id INT NULL,
                scenario_summary VARCHAR(255) NOT NULL,
                chosen_option CHAR(1) NOT NULL,
                responded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_user_id (user_id),
                INDEX idx_problem_id (problem_id),
                INDEX idx_responded_at (responded_at)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trolly_problems (
                problem_id INT AUTO_INCREMENT PRIMARY KEY,
                scenario TEXT NOT NULL,
                option_a VARCHAR(255) NOT NULL,
                option_b VARCHAR(255) NOT NULL,
                scenario_hash VARCHAR(64) UNIQUE,
                times_presented INT NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used_at TIMESTAMP NULL,
                INDEX idx_scenario_hash (scenario_hash),
                INDEX idx_times_presented (times_presented),
                INDEX idx_last_used (last_used_at)
            )
        """)
        
        # Add problem_id column to trolly_responses if it doesn't exist
        cursor.execute("SHOW COLUMNS FROM trolly_responses LIKE 'problem_id'")
        if not cursor.fetchone():
            logger.info("Adding problem_id column to trolly_responses table")
            cursor.execute("ALTER TABLE trolly_responses ADD COLUMN problem_id INT NULL AFTER display_name")
            cursor.execute("ALTER TABLE trolly_responses ADD INDEX idx_problem_id (problem_id)")
        
        # --- NEW: Gambling Stats Table ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gambling_stats (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                game_type VARCHAR(50) NOT NULL,
                total_games INT NOT NULL DEFAULT 0,
                total_wagered BIGINT NOT NULL DEFAULT 0,
                total_won BIGINT NOT NULL DEFAULT 0,
                total_lost BIGINT NOT NULL DEFAULT 0,
                biggest_win BIGINT NOT NULL DEFAULT 0,
                biggest_loss BIGINT NOT NULL DEFAULT 0,
                last_played TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY user_game (user_id, game_type),
                INDEX idx_user_id (user_id),
                INDEX idx_game_type (game_type)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # --- NEW: Game Tracking Tables for Casino Games ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS blackjack_games (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                bet_amount BIGINT NOT NULL,
                result VARCHAR(20) NOT NULL,
                payout BIGINT NOT NULL DEFAULT 0,
                player_hand TEXT,
                dealer_hand TEXT,
                played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_user_id (user_id),
                INDEX idx_played_at (played_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS roulette_games (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                bet_amount BIGINT NOT NULL,
                bet_type VARCHAR(50) NOT NULL,
                bet_value VARCHAR(50),
                result_number INT NOT NULL,
                won BOOLEAN NOT NULL DEFAULT FALSE,
                payout BIGINT NOT NULL DEFAULT 0,
                played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_user_id (user_id),
                INDEX idx_played_at (played_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mines_games (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                bet_amount BIGINT NOT NULL,
                grid_size INT NOT NULL DEFAULT 5,
                mine_count INT NOT NULL DEFAULT 5,
                revealed_count INT NOT NULL DEFAULT 0,
                result VARCHAR(20) NOT NULL,
                multiplier DECIMAL(10, 2) NOT NULL DEFAULT 1.0,
                payout BIGINT NOT NULL DEFAULT 0,
                played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_user_id (user_id),
                INDEX idx_played_at (played_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tower_games (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                bet_amount BIGINT NOT NULL,
                difficulty INT NOT NULL DEFAULT 1,
                floors_climbed INT NOT NULL DEFAULT 0,
                max_floors INT NOT NULL DEFAULT 10,
                result VARCHAR(20) NOT NULL,
                payout BIGINT NOT NULL DEFAULT 0,
                played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_user_id (user_id),
                INDEX idx_played_at (played_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS russian_roulette_games (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                entry_fee BIGINT NOT NULL,
                shots_survived INT NOT NULL DEFAULT 0,
                survived BOOLEAN NOT NULL DEFAULT FALSE,
                payout BIGINT NOT NULL DEFAULT 0,
                played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_user_id (user_id),
                INDEX idx_played_at (played_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # --- NEW: Horse Racing Games Table (unified naming) ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS horse_racing_games (
                id INT AUTO_INCREMENT PRIMARY KEY,
                race_id INT NOT NULL,
                winner_horse_index INT NOT NULL,
                winner_name VARCHAR(50) NOT NULL,
                total_bets INT DEFAULT 0,
                total_pool BIGINT DEFAULT 0,
                num_bettors INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_created (created_at),
                INDEX idx_race_id (race_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        cnx.commit()

        logger.info("Database tables checked/created successfully")
    except mysql.connector.Error as err:
        logger.error(f"Failed creating/modifying tables: {err}")
        logger.error(f"Error code: {err.errno}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        cursor.close()
        cnx.close()

# --- NEW: Database Migration System ---

def create_migrations_table():
    """Creates the schema_migrations table to track applied migrations."""
    cnx = get_db_connection()
    if not cnx:
        logger.error("Could not connect to DB to create migrations table")
        return False
    
    cursor = cnx.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                migration_name VARCHAR(255) PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_applied_at (applied_at)
            )
        """)
        cnx.commit()
        logger.info("Schema migrations tracking table ready")
        return True
    except mysql.connector.Error as err:
        logger.error(f"Failed to create schema_migrations table: {err}")
        return False
    finally:
        cursor.close()
        cnx.close()

def get_applied_migrations():
    """Returns a set of migration names that have already been applied."""
    cnx = get_db_connection()
    if not cnx:
        logger.warning("Could not connect to DB to check applied migrations")
        return set()
    
    cursor = cnx.cursor()
    try:
        cursor.execute("SELECT migration_name FROM schema_migrations")
        applied = {row[0] for row in cursor.fetchall()}
        return applied
    except mysql.connector.Error as err:
        # Table might not exist yet
        logger.debug(f"Could not query schema_migrations (might not exist yet): {err}")
        return set()
    finally:
        cursor.close()
        cnx.close()

def mark_migration_applied(migration_name):
    """Marks a migration as applied in the schema_migrations table."""
    cnx = get_db_connection()
    if not cnx:
        logger.error(f"Could not connect to DB to mark migration {migration_name} as applied")
        return False
    
    cursor = cnx.cursor()
    try:
        cursor.execute(
            "INSERT INTO schema_migrations (migration_name) VALUES (%s) ON DUPLICATE KEY UPDATE applied_at = CURRENT_TIMESTAMP",
            (migration_name,)
        )
        cnx.commit()
        logger.info(f"Marked migration '{migration_name}' as applied")
        return True
    except mysql.connector.Error as err:
        logger.error(f"Failed to mark migration {migration_name} as applied: {err}")
        return False
    finally:
        cursor.close()
        cnx.close()

def apply_sql_migration(migration_file_path):
    """
    Applies a SQL migration file to the database.
    Returns (success: bool, error_message: str or None)
    """
    import os
    
    if not os.path.exists(migration_file_path):
        return False, f"Migration file not found: {migration_file_path}"
    
    try:
        with open(migration_file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
    except Exception as e:
        return False, f"Failed to read migration file: {e}"
    
    cnx = get_db_connection()
    if not cnx:
        return False, "Could not connect to database"
    
    cursor = cnx.cursor()
    
    # Parse SQL into statements
    statements = []
    current_statement = []
    in_delimiter = False
    current_delimiter = ';'
    custom_delimiter = None
    
    for line in sql_content.split('\n'):
        stripped = line.strip()
        
        # Handle DELIMITER changes (supports $$, //, and other custom delimiters)
        if stripped.upper().startswith('DELIMITER'):
            parts = stripped.split()
            if len(parts) >= 2:
                new_delimiter = parts[1]
                if new_delimiter == ';':
                    in_delimiter = False
                    current_delimiter = ';'
                    custom_delimiter = None
                else:
                    # Support any custom delimiter ($$, //, etc.)
                    in_delimiter = True
                    current_delimiter = new_delimiter
                    custom_delimiter = new_delimiter
            continue
        
        # Skip empty lines and comments
        if not stripped or stripped.startswith('--'):
            continue
        
        current_statement.append(line)
        
        # Check for statement end
        if in_delimiter and custom_delimiter and stripped.endswith(custom_delimiter):
            stmt = '\n'.join(current_statement).rstrip(custom_delimiter).strip()
            if stmt:
                statements.append(stmt)
            current_statement = []
        elif not in_delimiter and stripped.endswith(';'):
            stmt = '\n'.join(current_statement).rstrip(';').strip()
            if stmt:
                statements.append(stmt)
            current_statement = []
    
    # Idempotent error patterns to ignore - migrations should be re-runnable
    IDEMPOTENT_ERROR_PATTERNS = [
        'already exists',
        'duplicate',
        'does not exist'
    ]
    
    # Execute statements
    try:
        logger.info(f"Executing {len(statements)} SQL statements from migration")
        for i, statement in enumerate(statements, 1):
            try:
                cursor.execute(statement)
                # Consume any results to avoid "Unread result found" error
                # This is necessary when EXECUTE stmt runs a SELECT statement
                # Check if the cursor has results using with_rows property
                if cursor.with_rows:
                    cursor.fetchall()
                # Get preview of statement for logging
                preview = ' '.join(statement.split()[:5])
                logger.debug(f"  [{i}/{len(statements)}] ✓ {preview}...")
            except mysql.connector.Error as err:
                preview = ' '.join(statement.split()[:5])
                error_msg = str(err).lower()
                # Check if this is an idempotent error that can be safely ignored
                is_idempotent = any(pattern in error_msg for pattern in IDEMPOTENT_ERROR_PATTERNS)
                if is_idempotent:
                    logger.debug(f"  [{i}/{len(statements)}] ⚠ {preview}... (idempotent, skipping)")
                else:
                    logger.error(f"  [{i}/{len(statements)}] ✗ {preview}... Error: {err}")
                    raise
        
        cnx.commit()
        logger.info("Migration applied successfully")
        return True, None
        
    except mysql.connector.Error as err:
        cnx.rollback()
        error_msg = f"Migration failed with MySQL error: {err}"
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        cnx.rollback()
        error_msg = f"Migration failed with unexpected error: {e}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return False, error_msg
    finally:
        cursor.close()
        cnx.close()

def apply_pending_migrations(migrations_dir="scripts/db_migrations"):
    """
    Discovers and applies all pending SQL migrations from the migrations directory.
    Returns (total_applied: int, errors: list)
    """
    import os
    import glob
    
    logger.info("Checking for pending database migrations...")
    
    # Ensure migrations tracking table exists
    if not create_migrations_table():
        logger.error("Failed to create migrations tracking table")
        return 0, ["Failed to create migrations tracking table"]
    
    # Get already applied migrations
    applied_migrations = get_applied_migrations()
    logger.info(f"Found {len(applied_migrations)} previously applied migrations")
    
    # Find all .sql files in the migrations directory
    if not os.path.exists(migrations_dir):
        logger.warning(f"Migrations directory not found: {migrations_dir}")
        return 0, []
    
    migration_files = sorted(glob.glob(os.path.join(migrations_dir, "*.sql")))
    logger.info(f"Found {len(migration_files)} migration files in {migrations_dir}")
    
    total_applied = 0
    errors = []
    
    for migration_path in migration_files:
        migration_name = os.path.basename(migration_path)
        
        if migration_name in applied_migrations:
            logger.debug(f"Skipping already applied migration: {migration_name}")
            continue
        
        logger.info(f"Applying migration: {migration_name}")
        success, error_msg = apply_sql_migration(migration_path)
        
        if success:
            # Mark as applied
            if mark_migration_applied(migration_name):
                total_applied += 1
                logger.info(f"✓ Successfully applied migration: {migration_name}")
            else:
                error_msg = f"Migration applied but failed to mark as completed: {migration_name}"
                logger.error(error_msg)
                errors.append(error_msg)
        else:
            error_msg = f"Failed to apply migration {migration_name}: {error_msg}"
            logger.error(error_msg)
            errors.append(error_msg)
    
    if total_applied > 0:
        logger.info(f"✓ Applied {total_applied} new migrations successfully")
    else:
        logger.info("No new migrations to apply")
    
    if errors:
        logger.warning(f"Encountered {len(errors)} errors during migration")
    
    return total_applied, errors

# --- NEW: API Usage Tracking Functions ---

@db_operation("log_api_usage")
async def log_api_usage(model_name, input_tokens, output_tokens):
    """Logs the usage of an AI model, including token counts."""
    if not db_pool:
        logger.warning("Database pool not available, skipping API usage logging")
        return
    
    # Use get_db_connection which has retry logic for pool exhaustion
    cnx = get_db_connection()
    if not cnx: 
        logger.warning("Could not get database connection for API usage logging")
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

# --- NEW: Helpers for Werwolf provider selection ---
async def get_gemini_usage():
    """Returns today's total Gemini API call count across all Gemini models."""
    if not db_pool:
        return 0
    cnx = db_pool.get_connection()
    if not cnx:
        return 0
    cursor = cnx.cursor(dictionary=True)
    try:
        cursor.execute("SELECT SUM(call_count) AS total_calls FROM api_usage WHERE usage_date = CURDATE() AND model_name LIKE 'gemini%' ")
        row = cursor.fetchone()
        return int(row["total_calls"]) if row and row["total_calls"] else 0
    finally:
        cursor.close()
        cnx.close()

async def increment_gemini_usage():
    """Increments a synthetic Gemini usage counter row for generic Gemini usage."""
    # Reuse log_api_usage with a synthetic model name that matches LIKE 'gemini%'
    await log_api_usage("gemini-generic", 0, 0)

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
    if not db_pool:
        logger.warning("Database pool not available, skipping cleanup")
        return
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
        logger.error(f"DB Cleanup Error: {err}")
        logger.error(traceback.format_exc())
    finally:
        cursor.close()
        cnx.close()

# --- NEW: Conversation Context + AI Usage (Medium Priority Features) ---

@db_operation("save_conversation_context")
async def save_conversation_context(user_id: int, channel_id: int, last_user_message: str, last_bot_response: str):
    """Upserts the latest conversation context for a user/channel pair."""
    if not db_pool:
        return
    cnx = db_pool.get_connection()
    if not cnx:
        return
    cursor = cnx.cursor()
    try:
        query = (
            """
            INSERT INTO conversation_context (user_id, channel_id, last_bot_message_at, last_user_message, last_bot_response)
            VALUES (%s, %s, NOW(), %s, %s)
            ON DUPLICATE KEY UPDATE
                last_bot_message_at = VALUES(last_bot_message_at),
                last_user_message = VALUES(last_user_message),
                last_bot_response = VALUES(last_bot_response)
            """
        )
        cursor.execute(query, (user_id, channel_id, last_user_message, last_bot_response))
        cnx.commit()
    finally:
        cursor.close()
        cnx.close()

@db_operation("get_conversation_context")
async def get_conversation_context(user_id: int, channel_id: int):
    """Returns the most recent conversation context and seconds since last bot message."""
    if not db_pool:
        return None
    cnx = db_pool.get_connection()
    if not cnx:
        return None
    cursor = cnx.cursor(dictionary=True)
    try:
        query = (
            """
            SELECT last_user_message, last_bot_response,
                   TIMESTAMPDIFF(SECOND, last_bot_message_at, NOW()) AS seconds_ago
            FROM conversation_context
            WHERE user_id = %s AND channel_id = %s
            """
        )
        cursor.execute(query, (user_id, channel_id))
        row = cursor.fetchone()
        return row
    finally:
        cursor.close()
        cnx.close()


@db_operation("get_channel_conversation_context")
async def get_channel_conversation_context(channel_id: int, max_age_seconds: int = 300):
    """
    Returns the most recent conversation context for any user in the channel.
    Used to detect if the bot was recently talking to someone and should respond to follow-ups.
    
    Args:
        channel_id: The Discord channel ID
        max_age_seconds: Maximum age of context to consider (default 5 minutes)
    
    Returns:
        dict with user_id, last_user_message, last_bot_response, seconds_ago or None
    """
    if not db_pool:
        return None
    cnx = db_pool.get_connection()
    if not cnx:
        return None
    cursor = cnx.cursor(dictionary=True)
    try:
        query = """
            SELECT user_id, last_user_message, last_bot_response,
                   TIMESTAMPDIFF(SECOND, last_bot_message_at, NOW()) AS seconds_ago
            FROM conversation_context
            WHERE channel_id = %s AND last_bot_message_at > (NOW() - INTERVAL %s SECOND)
            ORDER BY last_bot_message_at DESC
            LIMIT 1
        """
        cursor.execute(query, (channel_id, max_age_seconds))
        row = cursor.fetchone()
        return row
    finally:
        cursor.close()
        cnx.close()

@db_operation("clear_old_conversation_contexts")
async def clear_old_conversation_contexts(retention_minutes: int = 1440):
    """Deletes conversation contexts older than the given retention window (default: 24h)."""
    if not db_pool:
        return 0
    cnx = db_pool.get_connection()
    if not cnx:
        return 0
    cursor = cnx.cursor()
    try:
        query = "DELETE FROM conversation_context WHERE last_bot_message_at < (NOW() - INTERVAL %s MINUTE)"
        cursor.execute(query, (retention_minutes,))
        deleted = cursor.rowcount
        cnx.commit()
        return deleted
    finally:
        cursor.close()
        cnx.close()

@db_operation("track_ai_model_usage")
async def track_ai_model_usage(model_name: str, feature: str, input_tokens: int = 0, output_tokens: int = 0, total_cost: float = 0.0):
    """Tracks AI usage per model/feature/day in ai_model_usage table."""
    if not db_pool:
        return
    cnx = db_pool.get_connection()
    if not cnx:
        return
    cursor = cnx.cursor()
    try:
        query = (
            """
            INSERT INTO ai_model_usage (model_name, feature, call_count, input_tokens, output_tokens, total_cost, usage_date)
            VALUES (%s, %s, 1, %s, %s, %s, CURDATE())
            ON DUPLICATE KEY UPDATE
                call_count = call_count + 1,
                input_tokens = input_tokens + VALUES(input_tokens),
                output_tokens = output_tokens + VALUES(output_tokens),
                total_cost = total_cost + VALUES(total_cost)
            """
        )
        cursor.execute(query, (model_name, feature, input_tokens, output_tokens, total_cost))
        cnx.commit()
    finally:
        cursor.close()
        cnx.close()

@db_operation("get_ai_usage_stats")
async def get_ai_usage_stats(days: int = 30):
    """Aggregates AI usage over the last N days by model and feature."""
    if not db_pool:
        return []
    cnx = db_pool.get_connection()
    if not cnx:
        return []
    cursor = cnx.cursor(dictionary=True)
    try:
        query = (
            """
            SELECT model_name,
                   feature,
                   SUM(call_count) AS total_calls,
                   SUM(input_tokens) AS total_input_tokens,
                   SUM(output_tokens) AS total_output_tokens,
                   SUM(total_cost) AS total_cost,
                   MIN(usage_date) AS first_use,
                   MAX(usage_date) AS last_use
            FROM ai_model_usage
            WHERE usage_date >= (CURDATE() - INTERVAL %s DAY)
            GROUP BY model_name, feature
            ORDER BY total_calls DESC
            """
        )
        cursor.execute(query, (days,))
        rows = cursor.fetchall() or []
        # Convert Decimal values for JSON serialization
        return [convert_decimals(row) for row in rows]
    finally:
        cursor.close()
        cnx.close()

# --- NEW: Voice Channel Management DB Functions ---

async def get_owned_channel(owner_id, guild_id):
    """Fetches the channel ID owned by a user, if any."""
    if not db_pool:
        logger.warning("Database pool not available, cannot get owned channel")
        return None
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
    if not db_pool:
        logger.warning("Database pool not available, cannot add managed channel")
        return
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
    if not db_pool:
        logger.warning("Database pool not available, cannot remove managed channel")
        return
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
    if not db_pool:
        logger.warning("Database pool not available, cannot get managed channel config")
        return None
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
    if not db_pool:
        logger.warning("Database pool not available, cannot update managed channel config")
        return
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
    if not db_pool:
        logger.warning("Database pool not available, cannot get managed channels")
        return []
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
    if not db_pool:
        logger.warning("Database pool not available, cannot save message to history")
        return
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

    if not db_pool:
        logger.warning("Database pool not available, cannot save bulk history")
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
    if not db_pool:
        logger.warning("Database pool not available, cannot clear channel history")
        return 0, "Database pool not available."
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
    if not db_pool:
        logger.warning("Database pool not available, cannot get chat history")
        return []
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
    if not db_pool:
        logger.warning("Database pool not available, cannot get relationship summary")
        return None
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
    if not db_pool:
        logger.warning("Database pool not available, cannot update relationship summary")
        return
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
    if not db_pool:
        logger.warning("Database pool not available, cannot get bot name pool count")
        return 0
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
    if not db_pool:
        logger.warning("Database pool not available, cannot add bot names to pool")
        return
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
    if not db_pool:
        logger.warning("Database pool not available, cannot get bot names")
        return []
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
    if not db_pool:
        logger.warning("Database pool not available, cannot update player stats")
        return
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
    if not db_pool:
        logger.warning("Database pool not available, cannot update user presence")
        return
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

# --- NEW: Balance helpers for shop/commands ---
async def get_balance(user_id):
    """Returns current balance for a user, creating the player if necessary."""
    if not db_pool:
        return 0
    cnx = db_pool.get_connection()
    if not cnx:
        return 0
    cursor = cnx.cursor(dictionary=True)
    try:
        cursor.execute("SELECT balance FROM players WHERE discord_id = %s", (user_id,))
        row = cursor.fetchone()
        return int(row["balance"]) if row and row.get("balance") is not None else 0
    finally:
        cursor.close()
        cnx.close()

async def update_spotify_history(client, user_id: int, display_name: str, song_title: str, song_artist: str):
    """
    Increments the play count for a song in a user's persistent Spotify history.
    The history is stored as a JSON object mapping 'song by artist' to a play count.
    """
    if not db_pool:
        logger.warning("Database pool not available, cannot update Spotify history")
        return
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
    if not db_pool:
        logger.warning("Database pool not available, cannot log game session")
        return
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
    if not db_pool:
        logger.warning("Database pool not available, cannot log message stat")
        return
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
    if not db_pool:
        logger.warning("Database pool not available, cannot log VC minutes")
        return
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
    if not db_pool:
        logger.warning("Database pool not available, cannot log stat increment")
        return
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
    if not db_pool:
        logger.warning("Database pool not available, cannot get wrapped stats")
        return []
    cnx = db_pool.get_connection()
    if not cnx: return []
    cursor = cnx.cursor(dictionary=True)
    try:
        query = "SELECT * FROM user_monthly_stats WHERE stat_period = %s"
        cursor.execute(query, (stat_period,))
        results = cursor.fetchall()
        # Convert Decimal values to int/float for JSON serialization
        return [convert_decimals(row) for row in results]
    finally:
        cursor.close()
        cnx.close()

async def get_spotify_history(user_id):
    """Fetches the full Spotify history for a user."""
    if not db_pool:
        logger.warning("Database pool not available, cannot get Spotify history")
        return None
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
    if not db_pool:
        logger.warning("Database pool not available, cannot get player profile")
        return None, "Database pool not available."
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
    if not db_pool:
        logger.warning("Database pool not available, cannot get leaderboard")
        return None, "Database pool not available."
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

async def get_money_leaderboard():
    """Fetches the top 10 players by balance."""
    if not db_pool:
        logger.warning("Database pool not available, cannot get money leaderboard")
        return None, "Database pool not available."
    cnx = db_pool.get_connection()
    if not cnx:
        return None, "Konnte keine Verbindung zur Datenbank herstellen."

    cursor = cnx.cursor(dictionary=True)
    try:
        query = "SELECT display_name, balance FROM players ORDER BY balance DESC LIMIT 10"
        cursor.execute(query)
        results = cursor.fetchall()
        return results, None
    except mysql.connector.Error as err:
        print(f"Error fetching money leaderboard: {err}")
        return None, "Fehler beim Abrufen des Leaderboards."
    finally:
        cursor.close()
        cnx.close()

async def get_games_leaderboard():
    """Fetches the top 10 players by total games played (wins + losses)."""
    if not db_pool:
        logger.warning("Database pool not available, cannot get games leaderboard")
        return None, "Database pool not available."
    cnx = db_pool.get_connection()
    if not cnx:
        return None, "Konnte keine Verbindung zur Datenbank herstellen."

    cursor = cnx.cursor(dictionary=True)
    try:
        query = """
            SELECT display_name, wins, losses, (wins + losses) as total_games 
            FROM players 
            WHERE (wins + losses) > 0
            ORDER BY total_games DESC 
            LIMIT 10
        """
        cursor.execute(query)
        results = cursor.fetchall()
        return results, None
    except mysql.connector.Error as err:
        print(f"Error fetching games leaderboard: {err}")
        return None, "Fehler beim Abrufen des Leaderboards."
    finally:
        cursor.close()
        cnx.close()

async def get_user_wrapped_stats(user_id, stat_period):
    """Fetches the Wrapped stats for a single user for a given period."""
    if not db_pool:
        logger.warning("Database pool not available, cannot get user wrapped stats")
        return None
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
    Fetches comprehensive Wrapped stats for a user including detective, quests, games, shop purchases, etc.
    Always returns a dict with default values if database is unavailable.
    """
    # Define default stats first so we can return them if database is unavailable
    stats = {
        "server_bestie_id": None,
        "prime_time_hour": None,
        "temp_vcs_created": 0,
        "longest_vc_session_seconds": 0,
        "quests_completed": 0,
        "total_quest_days": 0,
        "games_played": 0,
        "games_won": 0,
        "total_bet": 0,
        "total_won": 0,
        "detective_cases_solved": 0,
        "detective_cases_failed": 0,
        "detective_total_cases": 0,
        "most_bought_item": None,
        "most_bought_item_count": 0,
        "least_bought_item": None,
        "least_bought_item_count": 0,
        "total_purchases": 0
    }

    if not db_pool:
        logger.warning("Database pool not available, cannot get wrapped extra stats")
        return stats
    cnx = db_pool.get_connection()
    if not cnx:
        logger.warning("Database connection failed, cannot get wrapped extra stats")
        return stats
    cursor = cnx.cursor(dictionary=True)
    
    start_date = f"{stat_period}-01"
    # A bit of a hack to get the end date of the month
    from datetime import datetime, timedelta
    next_month = (datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=32)).replace(day=1)
    end_date = (next_month - timedelta(days=1)).strftime("%Y-%m-%d")

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

        # 5. Quest Stats
        # Get completed quests count
        quest_count_query = "SELECT COUNT(*) as count FROM daily_quests WHERE user_id = %s AND quest_date BETWEEN %s AND %s AND completed = TRUE;"
        cursor.execute(quest_count_query, (user_id, start_date, end_date))
        quest_count_result = cursor.fetchone()
        if quest_count_result:
            stats["quests_completed"] = quest_count_result['count']
        
        # Get days where all quests were completed (from monthly_quest_completion)
        quest_days_query = "SELECT COUNT(*) as count FROM monthly_quest_completion WHERE user_id = %s AND completion_date BETWEEN %s AND %s;"
        cursor.execute(quest_days_query, (user_id, start_date, end_date))
        quest_days_result = cursor.fetchone()
        if quest_days_result:
            stats["total_quest_days"] = quest_days_result['count']

        # 6. Game Stats (from user_stats table)
        game_stats_query = """
            SELECT 
                COALESCE(SUM(games_played), 0) as games_played,
                COALESCE(SUM(games_won), 0) as games_won,
                COALESCE(SUM(total_bet), 0) as total_bet,
                COALESCE(SUM(total_won), 0) as total_won
            FROM user_stats 
            WHERE user_id = %s AND stat_period = %s;
        """
        cursor.execute(game_stats_query, (user_id, stat_period))
        game_stats_result = cursor.fetchone()
        if game_stats_result:
            # Convert entire result using utility function for consistency
            converted = convert_decimals(game_stats_result)
            stats["games_played"] = converted['games_played'] or 0
            stats["games_won"] = converted['games_won'] or 0
            stats["total_bet"] = converted['total_bet'] or 0
            stats["total_won"] = converted['total_won'] or 0

        # 7. Detective Game Stats
        detective_stats_query = """
            SELECT 
                COUNT(CASE WHEN p.completed = TRUE AND p.solved = TRUE THEN 1 END) as cases_solved,
                COUNT(CASE WHEN p.completed = TRUE AND p.solved = FALSE THEN 1 END) as cases_failed,
                COUNT(*) as total_cases
            FROM detective_user_progress p
            WHERE p.user_id = %s 
            AND DATE(p.completed_at) BETWEEN %s AND %s
        """
        cursor.execute(detective_stats_query, (user_id, start_date, end_date))
        detective_result = cursor.fetchone()
        if detective_result:
            stats["detective_cases_solved"] = detective_result['cases_solved'] or 0
            stats["detective_cases_failed"] = detective_result['cases_failed'] or 0
            stats["detective_total_cases"] = detective_result['total_cases'] or 0

        # 8. Shop Purchase Stats
        # Get most and least bought items
        purchase_stats_query = """
            SELECT 
                item_name,
                COUNT(*) as purchase_count
            FROM shop_purchases
            WHERE user_id = %s 
            AND DATE(purchased_at) BETWEEN %s AND %s
            GROUP BY item_name
            ORDER BY purchase_count DESC
        """
        cursor.execute(purchase_stats_query, (user_id, start_date, end_date))
        purchase_results = cursor.fetchall()
        
        if purchase_results:
            stats["total_purchases"] = sum(p['purchase_count'] for p in purchase_results)
            stats["most_bought_item"] = purchase_results[0]['item_name']
            stats["most_bought_item_count"] = purchase_results[0]['purchase_count']
            
            if len(purchase_results) > 1:
                # Get least bought (last in sorted list)
                stats["least_bought_item"] = purchase_results[-1]['item_name']
                stats["least_bought_item_count"] = purchase_results[-1]['purchase_count']

        return stats
    except mysql.connector.Error as err:
        print(f"Error in get_wrapped_extra_stats: {err}")
        return stats # Return default stats on error
    finally:
        cursor.close()
        cnx.close()

# --- Wrapped Opt-In System ---

@db_operation("Register for Wrapped")
async def register_for_wrapped(user_id, username):
    """Registers a user to receive Wrapped summaries."""
    if not db_pool:
        return False
    
    cnx = db_pool.get_connection()
    cursor = cnx.cursor()
    try:
        query = """
            INSERT INTO wrapped_registrations (user_id, username, opted_out)
            VALUES (%s, %s, FALSE)
            ON DUPLICATE KEY UPDATE
                username = VALUES(username),
                opted_out = FALSE,
                last_updated = CURRENT_TIMESTAMP
        """
        cursor.execute(query, (user_id, username))
        cnx.commit()
        return True
    except mysql.connector.Error as err:
        print(f"Error in register_for_wrapped: {err}")
        return False
    finally:
        cursor.close()
        cnx.close()

@db_operation("Unregister from Wrapped")
async def unregister_from_wrapped(user_id):
    """Opts a user out of receiving Wrapped summaries."""
    if not db_pool:
        return False
    
    cnx = db_pool.get_connection()
    cursor = cnx.cursor()
    try:
        # Only UPDATE existing records - don't INSERT new ones
        query = """
            UPDATE wrapped_registrations
            SET opted_out = TRUE, last_updated = CURRENT_TIMESTAMP
            WHERE user_id = %s
        """
        cursor.execute(query, (user_id,))
        cnx.commit()
        # Return True if a record was updated, otherwise the user wasn't registered
        return cursor.rowcount > 0
    except mysql.connector.Error as err:
        print(f"Error in unregister_from_wrapped: {err}")
        return False
    finally:
        cursor.close()
        cnx.close()

@db_operation("Check Wrapped Registration")
async def is_registered_for_wrapped(user_id):
    """Checks if a user is registered for Wrapped and hasn't opted out."""
    if not db_pool:
        return False
    
    cnx = db_pool.get_connection()
    cursor = cnx.cursor(dictionary=True)
    try:
        query = "SELECT opted_out FROM wrapped_registrations WHERE user_id = %s"
        cursor.execute(query, (user_id,))
        result = cursor.fetchone()
        
        if not result:
            return False  # Not registered at all
        
        return not result['opted_out']  # Registered and not opted out
    except mysql.connector.Error as err:
        print(f"Error in is_registered_for_wrapped: {err}")
        return False
    finally:
        cursor.close()
        cnx.close()

@db_operation("Get All Wrapped Registrations")
async def get_wrapped_registrations():
    """Returns all user IDs who are registered for Wrapped and haven't opted out."""
    if not db_pool:
        return []
    
    cnx = db_pool.get_connection()
    cursor = cnx.cursor(dictionary=True)
    try:
        query = "SELECT user_id, username FROM wrapped_registrations WHERE opted_out = FALSE"
        cursor.execute(query)
        results = cursor.fetchall()
        return [row['user_id'] for row in results]
    except mysql.connector.Error as err:
        print(f"Error in get_wrapped_registrations: {err}")
        return []
    finally:
        cursor.close()
        cnx.close()


# --- Emoji Descriptions System ---

@db_operation("Save Emoji Description")
async def save_emoji_description(emoji_id, emoji_name, description, usage_context, image_url):
    """Saves an emoji description to the database."""
    if not db_pool:
        return False
    
    cnx = db_pool.get_connection()
    cursor = cnx.cursor()
    try:
        query = """
            INSERT INTO emoji_descriptions (emoji_id, emoji_name, description, usage_context, image_url, analyzed_at)
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON DUPLICATE KEY UPDATE
                emoji_name = VALUES(emoji_name),
                description = VALUES(description),
                usage_context = VALUES(usage_context),
                image_url = VALUES(image_url),
                analyzed_at = CURRENT_TIMESTAMP
        """
        cursor.execute(query, (emoji_id, emoji_name, description, usage_context, image_url))
        cnx.commit()
        return True
    except mysql.connector.Error as err:
        print(f"Error in save_emoji_description: {err}")
        return False
    finally:
        cursor.close()
        cnx.close()

@db_operation("Get All Emoji Descriptions")
async def get_all_emoji_descriptions():
    """Retrieves all emoji descriptions from the database."""
    if not db_pool:
        return []
    
    cnx = db_pool.get_connection()
    cursor = cnx.cursor(dictionary=True)
    try:
        query = "SELECT emoji_id, emoji_name, description, usage_context FROM emoji_descriptions ORDER BY emoji_name"
        cursor.execute(query)
        return cursor.fetchall()
    except mysql.connector.Error as err:
        print(f"Error in get_all_emoji_descriptions: {err}")
        return []
    finally:
        cursor.close()
        cnx.close()

@db_operation("Get Emoji Description")
async def get_emoji_description(emoji_id):
    """Retrieves a specific emoji description."""
    if not db_pool:
        return None
    
    cnx = db_pool.get_connection()
    cursor = cnx.cursor(dictionary=True)
    try:
        query = "SELECT * FROM emoji_descriptions WHERE emoji_id = %s"
        cursor.execute(query, (emoji_id,))
        return cursor.fetchone()
    except mysql.connector.Error as err:
        print(f"Error in get_emoji_description: {err}")
        return None
    finally:
        cursor.close()
        cnx.close()


# --- Conversation Context System ---

@db_operation("Save Conversation Context")
async def save_conversation_context(user_id, channel_id, last_user_message, last_bot_response):
    """Saves conversation context for follow-up detection."""
    if not db_pool:
        return False
    
    cnx = db_pool.get_connection()
    cursor = cnx.cursor()
    try:
        query = """
            INSERT INTO conversation_context (user_id, channel_id, last_bot_message_at, last_user_message, last_bot_response)
            VALUES (%s, %s, CURRENT_TIMESTAMP, %s, %s)
            ON DUPLICATE KEY UPDATE
                last_bot_message_at = CURRENT_TIMESTAMP,
                last_user_message = VALUES(last_user_message),
                last_bot_response = VALUES(last_bot_response)
        """
        cursor.execute(query, (user_id, channel_id, last_user_message, last_bot_response))
        cnx.commit()
        return True
    except mysql.connector.Error as err:
        print(f"Error in save_conversation_context: {err}")
        return False
    finally:
        cursor.close()
        cnx.close()

@db_operation("Get Conversation Context")
async def get_conversation_context(user_id, channel_id):
    """Retrieves conversation context if it's within 2 minutes."""
    if not db_pool:
        return None
    
    cnx = db_pool.get_connection()
    cursor = cnx.cursor(dictionary=True)
    try:
        query = """
            SELECT last_user_message, last_bot_response, 
                   TIMESTAMPDIFF(SECOND, last_bot_message_at, NOW()) as seconds_ago
            FROM conversation_context 
            WHERE user_id = %s AND channel_id = %s
            AND TIMESTAMPDIFF(SECOND, last_bot_message_at, NOW()) <= 120
        """
        cursor.execute(query, (user_id, channel_id))
        return cursor.fetchone()
    except mysql.connector.Error as err:
        print(f"Error in get_conversation_context: {err}")
        return None
    finally:
        cursor.close()
        cnx.close()

@db_operation("Clear Old Conversation Contexts")
async def clear_old_conversation_contexts():
    """Clears conversation contexts older than 5 minutes."""
    if not db_pool:
        return False
    
    cnx = db_pool.get_connection()
    cursor = cnx.cursor()
    try:
        query = "DELETE FROM conversation_context WHERE TIMESTAMPDIFF(MINUTE, last_bot_message_at, NOW()) > 5"
        cursor.execute(query)
        cnx.commit()
        return True
    except mysql.connector.Error as err:
        print(f"Error in clear_old_conversation_contexts: {err}")
        return False
    finally:
        cursor.close()
        cnx.close()


# --- AI Model Usage Tracking ---

@db_operation("Track AI Model Usage")
async def track_ai_model_usage(model_name, feature, input_tokens, output_tokens, cost=0.0):
    """Tracks AI model usage for analytics."""
    if not db_pool:
        return False
    
    cnx = db_pool.get_connection()
    cursor = cnx.cursor()
    try:
        query = """
            INSERT INTO ai_model_usage (model_name, feature, call_count, input_tokens, output_tokens, total_cost, usage_date)
            VALUES (%s, %s, 1, %s, %s, %s, CURDATE())
            ON DUPLICATE KEY UPDATE
                call_count = call_count + 1,
                input_tokens = input_tokens + VALUES(input_tokens),
                output_tokens = output_tokens + VALUES(output_tokens),
                total_cost = total_cost + VALUES(total_cost)
        """
        cursor.execute(query, (model_name, feature, input_tokens, output_tokens, cost))
        cnx.commit()
        return True
    except mysql.connector.Error as err:
        print(f"Error in track_ai_model_usage: {err}")
        return False
    finally:
        cursor.close()
        cnx.close()

@db_operation("Get AI Usage Stats")
async def get_ai_usage_stats(days=30):
    """Retrieves AI usage statistics for the specified number of days."""
    if not db_pool:
        return []
    
    cnx = db_pool.get_connection()
    cursor = cnx.cursor(dictionary=True)
    try:
        query = """
            SELECT model_name, feature, SUM(call_count) as total_calls,
                   SUM(input_tokens) as total_input_tokens,
                   SUM(output_tokens) as total_output_tokens,
                   SUM(total_cost) as total_cost,
                   MIN(usage_date) as first_use,
                   MAX(usage_date) as last_use
            FROM ai_model_usage
            WHERE usage_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
            GROUP BY model_name, feature
            ORDER BY total_calls DESC
        """
        cursor.execute(query, (days,))
        rows = cursor.fetchall()
        # Convert Decimal values for JSON serialization
        return [convert_decimals(row) for row in rows]
    except mysql.connector.Error as err:
        print(f"Error in get_ai_usage_stats: {err}")
        return []
    finally:
        cursor.close()
        cnx.close()


# ============================================================================
# Economy & Shop Functions
# ============================================================================

@db_operation("Has Feature Unlock")
async def has_feature_unlock(user_id, feature_name):
    """Checks if a user has unlocked a specific feature."""
    if not db_pool:
        return False
    cnx = db_pool.get_connection()
    if not cnx:
        return False
    cursor = cnx.cursor()
    try:
        cursor.execute("SELECT 1 FROM feature_unlocks WHERE user_id = %s AND feature_name = %s", (user_id, feature_name))
        return cursor.fetchone() is not None
    finally:
        cursor.close()
        cnx.close()


@db_operation("Add Feature Unlock")
async def add_feature_unlock(user_id, feature_name):
    """Adds a feature unlock for a user."""
    if not db_pool:
        return False
    cnx = db_pool.get_connection()
    if not cnx:
        return False
    cursor = cnx.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO feature_unlocks (user_id, feature_name)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE purchased_at = CURRENT_TIMESTAMP
            """,
            (user_id, feature_name)
        )
        cnx.commit()
        return True
    finally:
        cursor.close()
        cnx.close()


@db_operation("Get User Features")
async def get_user_features(user_id):
    """Gets all unlocked features for a user."""
    if not db_pool:
        return []
    
    cnx = db_pool.get_connection()
    if not cnx:
        return []
    
    cursor = cnx.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT feature_name, purchased_at FROM feature_unlocks WHERE user_id = %s",
            (user_id,)
        )
        results = cursor.fetchall()
        return [r['feature_name'] for r in results]
    finally:
        cursor.close()
        cnx.close()


@db_operation("Log Shop Purchase")
async def log_shop_purchase(user_id, item_type, item_name, price):
    """Logs a shop purchase (optional; safe no-op if table missing)."""
    if not db_pool:
        return False
    cnx = db_pool.get_connection()
    if not cnx:
        return False
    cursor = cnx.cursor()
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS shop_purchases (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                item_type VARCHAR(32) NOT NULL,
                item_name VARCHAR(128) NOT NULL,
                price BIGINT NOT NULL,
                purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            INSERT INTO shop_purchases (user_id, item_type, item_name, price)
            VALUES (%s, %s, %s, %s)
            """,
            (user_id, item_type, item_name, price)
        )
        cnx.commit()
        return True
    finally:
        cursor.close()
        cnx.close()


@db_operation("Get Purchase History")
async def get_purchase_history(user_id, limit=10):
    """Gets purchase history for a user."""
    if not db_pool:
        return []
    
    cnx = db_pool.get_connection()
    if not cnx:
        return []
    
    cursor = cnx.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT item_type, item_name, price, purchased_at
            FROM shop_purchases
            WHERE user_id = %s
            ORDER BY purchased_at DESC
            LIMIT %s
            """,
            (user_id, limit)
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        cnx.close()


@db_operation("Update Gambling Stats")
async def update_gambling_stats(user_id, game_type, wagered, won_amount):
    """Updates gambling statistics for a user."""
    if not db_pool:
        return False
    
    profit = won_amount - wagered
    
    cnx = db_pool.get_connection()
    if not cnx:
        return False
    
    cursor = cnx.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO gambling_stats (user_id, game_type, total_games, total_wagered, total_won, total_lost, biggest_win, biggest_loss, last_played)
            VALUES (%s, %s, 1, %s, %s, %s, %s, %s, NOW())
            ON DUPLICATE KEY UPDATE
                total_games = total_games + 1,
                total_wagered = total_wagered + %s,
                total_won = total_won + %s,
                total_lost = total_lost + %s,
                biggest_win = GREATEST(biggest_win, %s),
                biggest_loss = GREATEST(biggest_loss, %s),
                last_played = NOW()
            """,
            # INSERT params (7): user_id, game_type, wagered, won_amount, lost_amount, biggest_win, biggest_loss
            # UPDATE params (5): wagered, won_amount, lost_amount, biggest_win, biggest_loss
            (user_id, game_type, 
             wagered,
             won_amount if profit > 0 else 0, 
             abs(profit) if profit < 0 else 0,
             profit if profit > 0 else 0,
             abs(profit) if profit < 0 else 0,
             # UPDATE params below
             wagered, 
             won_amount if profit > 0 else 0,
             abs(profit) if profit < 0 else 0,
             profit if profit > 0 else 0,
             abs(profit) if profit < 0 else 0)
        )
        cnx.commit()
        return True
    finally:
        cursor.close()
        cnx.close()


@db_operation("Get Gambling Stats")
async def get_gambling_stats(user_id, game_type=None):
    """Gets gambling statistics for a user."""
    if not db_pool:
        return None
    
    cnx = db_pool.get_connection()
    if not cnx:
        return None
    
    cursor = cnx.cursor(dictionary=True)
    try:
        if game_type:
            cursor.execute(
                """
                SELECT * FROM gambling_stats
                WHERE user_id = %s AND game_type = %s
                """,
                (user_id, game_type)
            )
        else:
            cursor.execute(
                """
                SELECT * FROM gambling_stats
                WHERE user_id = %s
                """,
                (user_id,)
            )
        
        results = cursor.fetchall()
        return results if results else None
    finally:
        cursor.close()
        cnx.close()


@db_operation("Log Blackjack Game")
async def log_blackjack_game(user_id, bet_amount, result, payout, player_hand=None, dealer_hand=None):
    """Logs a blackjack game to the database."""
    if not db_pool:
        return False
    
    cnx = db_pool.get_connection()
    if not cnx:
        return False
    
    cursor = cnx.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO blackjack_games (user_id, bet_amount, result, payout, player_hand, dealer_hand)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (user_id, bet_amount, result, payout, player_hand, dealer_hand)
        )
        cnx.commit()
        return True
    except Exception as e:
        logger.error(f"Error logging blackjack game: {e}")
        return False
    finally:
        cursor.close()
        cnx.close()


@db_operation("Log Roulette Game")
async def log_roulette_game(user_id, bet_amount, bet_type, bet_value, result_number, won, payout):
    """Logs a roulette game to the database."""
    if not db_pool:
        return False
    
    cnx = db_pool.get_connection()
    if not cnx:
        return False
    
    cursor = cnx.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO roulette_games (user_id, bet_amount, bet_type, bet_value, result_number, won, payout)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (user_id, bet_amount, bet_type, str(bet_value), result_number, won, payout)
        )
        cnx.commit()
        return True
    except Exception as e:
        logger.error(f"Error logging roulette game: {e}")
        return False
    finally:
        cursor.close()
        cnx.close()


@db_operation("Log Mines Game")
async def log_mines_game(user_id, bet_amount, grid_size, mine_count, revealed_count, result, multiplier, payout):
    """Logs a mines game to the database."""
    if not db_pool:
        return False
    
    cnx = db_pool.get_connection()
    if not cnx:
        return False
    
    cursor = cnx.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO mines_games (user_id, bet_amount, grid_size, mine_count, revealed_count, result, multiplier, payout)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (user_id, bet_amount, grid_size, mine_count, revealed_count, result, multiplier, payout)
        )
        cnx.commit()
        return True
    except Exception as e:
        logger.error(f"Error logging mines game: {e}")
        return False
    finally:
        cursor.close()
        cnx.close()


@db_operation("Log Tower Game")
async def log_tower_game(user_id, bet_amount, difficulty, floors_climbed, max_floors, result, payout):
    """Logs a tower of treasure game to the database."""
    if not db_pool:
        return False
    
    cnx = db_pool.get_connection()
    if not cnx:
        return False
    
    cursor = cnx.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO tower_games (user_id, bet_amount, difficulty, floors_climbed, max_floors, result, payout)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (user_id, bet_amount, difficulty, floors_climbed, max_floors, result, payout)
        )
        cnx.commit()
        return True
    except Exception as e:
        logger.error(f"Error logging tower game: {e}")
        return False
    finally:
        cursor.close()
        cnx.close()


@db_operation("Log Russian Roulette Game")
async def log_russian_roulette_game(user_id, entry_fee, shots_survived, survived, payout):
    """Logs a russian roulette game to the database."""
    if not db_pool:
        return False
    
    cnx = db_pool.get_connection()
    if not cnx:
        return False
    
    cursor = cnx.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO russian_roulette_games (user_id, entry_fee, shots_survived, survived, payout)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (user_id, entry_fee, shots_survived, survived, payout)
        )
        cnx.commit()
        return True
    except Exception as e:
        logger.error(f"Error logging russian roulette game: {e}")
        return False
    finally:
        cursor.close()
        cnx.close()


@db_operation("Log Horse Racing Game")
async def log_horse_racing_game(race_id, winner_horse_index, winner_name, total_bets, total_pool, num_bettors):
    """Logs a horse racing game to the database."""
    if not db_pool:
        return False
    
    cnx = db_pool.get_connection()
    if not cnx:
        return False
    
    cursor = cnx.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO horse_racing_games (race_id, winner_horse_index, winner_name, total_bets, total_pool, num_bettors)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (race_id, winner_horse_index, winner_name, total_bets, total_pool, num_bettors)
        )
        cnx.commit()
        return True
    except Exception as e:
        logger.error(f"Error logging horse racing game: {e}")
        return False
    finally:
        cursor.close()
        cnx.close()


@db_operation("Update User Game Stats")
async def update_user_game_stats(user_id, display_name, won, bet_amount, won_amount):
    """Updates the user_stats table with game data for the current month."""
    if not db_pool:
        return False
    
    from datetime import datetime, timezone
    stat_period = datetime.now(timezone.utc).strftime('%Y-%m')
    
    cnx = db_pool.get_connection()
    if not cnx:
        return False
    
    cursor = cnx.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO user_stats (user_id, display_name, stat_period, games_played, games_won, total_bet, total_won)
            VALUES (%s, %s, %s, 1, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                games_played = games_played + 1,
                games_won = games_won + %s,
                total_bet = total_bet + %s,
                total_won = total_won + %s,
                display_name = VALUES(display_name),
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, display_name, stat_period, 
             1 if won else 0, bet_amount, won_amount,
             1 if won else 0, bet_amount, won_amount)
        )
        cnx.commit()
        return True
    except Exception as e:
        logger.error(f"Error updating user game stats: {e}")
        return False
    finally:
        cursor.close()
        cnx.close()


@db_operation("Log Transaction")
async def log_transaction(user_id, transaction_type, amount, balance_after, description=None):
    """Logs a transaction to history."""
    if not db_pool:
        return False
    
    cnx = db_pool.get_connection()
    if not cnx:
        return False
    
    cursor = cnx.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO transaction_history (user_id, transaction_type, amount, balance_after, description)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (user_id, transaction_type, amount, balance_after, description)
        )
        cnx.commit()
        return True
    finally:
        cursor.close()
        cnx.close()


@db_operation("Get Transaction History")
async def get_transaction_history(user_id, limit=20):
    """Gets transaction history for a user."""
    if not db_pool:
        return []
    
    cnx = db_pool.get_connection()
    if not cnx:
        return []
    
    cursor = cnx.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT transaction_type, amount, balance_after, description, created_at
            FROM transaction_history
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (user_id, limit)
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        cnx.close()


# --- User Customization Functions ---

@db_operation("Get User Equipped Color")
async def get_user_equipped_color(user_id):
    """Gets the user's equipped color."""
    if not db_pool:
        return None
    
    cnx = db_pool.get_connection()
    if not cnx:
        return None
    
    cursor = cnx.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT equipped_color FROM user_customization WHERE user_id = %s",
            (user_id,)
        )
        result = cursor.fetchone()
        return result['equipped_color'] if result else None
    finally:
        cursor.close()
        cnx.close()


@db_operation("Set User Equipped Color")
async def set_user_equipped_color(user_id, color):
    """Sets the user's equipped color."""
    if not db_pool:
        return False
    
    cnx = db_pool.get_connection()
    if not cnx:
        return False
    
    cursor = cnx.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO user_customization (user_id, equipped_color)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE equipped_color = %s
            """,
            (user_id, color, color)
        )
        cnx.commit()
        return True
    finally:
        cursor.close()
        cnx.close()


@db_operation("Get User Customization")
async def get_user_customization(user_id):
    """Gets all customization settings for a user."""
    if not db_pool:
        return None
    
    cnx = db_pool.get_connection()
    if not cnx:
        return None
    
    cursor = cnx.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT * FROM user_customization WHERE user_id = %s",
            (user_id,)
        )
        return cursor.fetchone()
    finally:
        cursor.close()
        cnx.close()


@db_operation("Set User Language")
async def set_user_language(user_id, language):
    """Sets the user's preferred language for games (de or en)."""
    if not db_pool:
        return False
    
    cnx = db_pool.get_connection()
    if not cnx:
        return False
    
    cursor = cnx.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO user_customization (user_id, language)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE language = %s
            """,
            (user_id, language, language)
        )
        cnx.commit()
        return True
    except Exception as e:
        logger.error(f"Error setting user language: {e}", exc_info=True)
        return False
    finally:
        cursor.close()
        cnx.close()


@db_operation("Get User Language")
async def get_user_language(user_id):
    """Gets the user's preferred language (defaults to 'de')."""
    if not db_pool:
        return 'de'
    
    cnx = db_pool.get_connection()
    if not cnx:
        return 'de'
    
    cursor = cnx.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT language FROM user_customization WHERE user_id = %s",
            (user_id,)
        )
        result = cursor.fetchone()
        return result['language'] if result and result.get('language') else 'de'
    except Exception as e:
        logger.error(f"Error getting user language: {e}", exc_info=True)
        return 'de'
    finally:
        cursor.close()
        cnx.close()

