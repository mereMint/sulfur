"""
Sulfur Bot - Word Find Game Module
Daily word guessing game with proximity-based hints.
"""

import discord
import random
import asyncio
import json
import os
from datetime import datetime, timezone, timedelta
from modules.logger_utils import bot_logger as logger
from modules import word_service


# Load word lists from configuration files
def load_word_list_dict(filename):
    """Load word list dictionary from JSON file."""
    try:
        filepath = os.path.join('config', filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading word list from {filename}: {e}")
        return {}


# Load language-specific word lists
WORD_LISTS_DE = load_word_list_dict('word_find_words_de.json')
WORD_LISTS_EN = load_word_list_dict('word_find_words_en.json')

# Fallback hardcoded words in case files don't exist (for backward compatibility)
if not WORD_LISTS_DE:
    logger.warning("Using fallback German word lists")
    WORD_LISTS_DE = {
    'easy': [
        'haus', 'baum', 'hund', 'katze', 'auto', 'buch', 'tisch', 'stuhl', 
        'fenster', 'tür', 'lampe', 'bett', 'küche', 'bad', 'garten', 'blume'
    ],
    'medium': [
        'computer', 'telefon', 'internet', 'tastatur', 'bildschirm', 'musik',
        'freund', 'familie', 'arbeit', 'schule', 'urlaub', 'wetter', 'sonne'
    ],
    'hard': [
        'entwicklung', 'programmieren', 'algorithmus', 'datenbank', 'netzwerk',
        'wissenschaft', 'technologie', 'innovation', 'kreativität', 'philosophie'
    ]
}

if not WORD_LISTS_EN:
    logger.warning("Using fallback English word lists")
    WORD_LISTS_EN = {
        'easy': [
            'house', 'tree', 'dog', 'cat', 'car', 'book', 'table', 'chair',
            'window', 'door', 'lamp', 'bed', 'kitchen', 'bath', 'garden', 'flower'
        ],
        'medium': [
            'computer', 'telephone', 'internet', 'keyboard', 'screen', 'music',
            'friend', 'family', 'work', 'school', 'vacation', 'weather', 'sun'
        ],
        'hard': [
            'development', 'programming', 'algorithm', 'database', 'network',
            'science', 'technology', 'innovation', 'creativity', 'philosophy'
        ]
    }

# Default to German for backward compatibility
WORD_LISTS = WORD_LISTS_DE

logger.info(f"Loaded Word Find word lists: DE={len(WORD_LISTS_DE.get('easy', []))+len(WORD_LISTS_DE.get('medium', []))+len(WORD_LISTS_DE.get('hard', []))} words, EN={len(WORD_LISTS_EN.get('easy', []))+len(WORD_LISTS_EN.get('medium', []))+len(WORD_LISTS_EN.get('hard', []))} words")


def get_word_lists(language='de'):
    """Get Word Find word lists for specified language."""
    if language == 'en':
        word_lists = WORD_LISTS_EN
    else:
        word_lists = WORD_LISTS_DE
    
    # Ensure we have valid words for all difficulties
    if not word_lists or not all(k in word_lists and len(word_lists[k]) > 0 for k in ['easy', 'medium', 'hard']):
        logger.error(f"Invalid or empty word lists for language {language}")
        # Return minimal fallback
        if language == 'en':
            return {
                'easy': ['house', 'tree', 'book', 'chair', 'table'],
                'medium': ['computer', 'internet', 'keyboard', 'monitor'],
                'hard': ['programming', 'technology', 'innovation']
            }
        else:
            return {
                'easy': ['haus', 'baum', 'buch', 'stuhl', 'tisch'],
                'medium': ['computer', 'internet', 'tastatur', 'monitor'],
                'hard': ['programmieren', 'technologie', 'innovation']
            }
    
    return word_lists


def get_valid_word_pool(language='de'):
    """
    Get a comprehensive set of valid words for guess validation.
    Combines all difficulty levels into a single set for validation.
    
    Args:
        language: 'de' or 'en'
    
    Returns:
        Set of valid words (lowercase)
    """
    word_lists = get_word_lists(language)
    
    # Combine all difficulty levels
    all_words = []
    for difficulty in ['easy', 'medium', 'hard']:
        all_words.extend(word_lists.get(difficulty, []))
    
    # Convert to lowercase set for fast lookup
    valid_words = set(word.lower() for word in all_words)
    
    # Try to enhance with word_service fallback words for more validation options
    try:
        if language == 'en':
            additional_words = word_service.get_fallback_english_words(
                count=2000,  # Get a large pool for validation
                min_length=3,
                max_length=20
            )
        else:
            additional_words = word_service.get_fallback_german_words(
                count=2000,
                min_length=3,
                max_length=20
            )
        
        valid_words.update(word.lower() for word in additional_words)
        logger.debug(f"Enhanced Word Find validation pool for {language}: {len(valid_words)} words")
    except Exception as e:
        logger.warning(f"Could not enhance word pool with word_service: {e}")
    
    return valid_words


def is_valid_guess(guess: str, language='de') -> bool:
    """
    Check if a guess is a valid word in the word pool.
    
    Args:
        guess: The word to validate
        language: 'de' or 'en'
    
    Returns:
        True if valid, False otherwise
    """
    if not guess or len(guess) < 2:
        return False
    
    guess_lower = guess.lower().strip()
    valid_pool = get_valid_word_pool(language)
    
    return guess_lower in valid_pool


async def initialize_word_find_table(db_helpers):
    """Initialize the word find game table in the database."""
    try:
        if not db_helpers.db_pool:
            logger.error("Database pool not available")
            return
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            logger.error("Could not get database connection")
            return
        
        cursor = conn.cursor()
        try:
            logger.info("Initializing Word Find tables...")
            
            # Table for daily word
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS word_find_daily (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    word VARCHAR(100) NOT NULL,
                    difficulty VARCHAR(20) NOT NULL,
                    language VARCHAR(2) DEFAULT 'de',
                    date DATE NOT NULL,
                    UNIQUE KEY unique_date_lang (date, language),
                    INDEX idx_date (date),
                    INDEX idx_lang (language)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Table for premium games (separate from daily)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS word_find_premium_games (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    word VARCHAR(100) NOT NULL,
                    difficulty VARCHAR(20) NOT NULL,
                    language VARCHAR(2) DEFAULT 'de',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed BOOLEAN DEFAULT FALSE,
                    won BOOLEAN DEFAULT FALSE,
                    INDEX idx_user_created (user_id, created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Table for user attempts
            # Note: No foreign key constraint on word_id because it references different tables
            # based on game_type (word_find_daily for 'daily', word_find_premium_games for 'premium')
            # Referential integrity is maintained at the application level
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS word_find_attempts (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    word_id INT NOT NULL,
                    guess VARCHAR(100) NOT NULL,
                    similarity_score FLOAT NOT NULL,
                    attempt_number INT NOT NULL,
                    game_type ENUM('daily', 'premium') DEFAULT 'daily',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_user_word_type (user_id, word_id, game_type)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Table for user stats (backwards compatible - supports both old and new schema)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS word_find_stats (
                    user_id BIGINT PRIMARY KEY,
                    total_games INT DEFAULT 0,
                    total_wins INT DEFAULT 0,
                    current_streak INT DEFAULT 0,
                    best_streak INT DEFAULT 0,
                    total_attempts INT DEFAULT 0,
                    daily_games INT DEFAULT 0,
                    daily_wins INT DEFAULT 0,
                    daily_streak INT DEFAULT 0,
                    daily_best_streak INT DEFAULT 0,
                    daily_total_attempts INT DEFAULT 0,
                    premium_games INT DEFAULT 0,
                    premium_wins INT DEFAULT 0,
                    premium_total_attempts INT DEFAULT 0,
                    last_played DATE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            conn.commit()
            logger.info("Word Find tables initialized successfully")
            
            # Verify tables were created
            cursor.execute("SHOW TABLES LIKE 'word_find_%'")
            tables = cursor.fetchall()
            logger.info(f"Verified {len(tables)} Word Find tables exist")
            
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error initializing word find tables: {e}", exc_info=True)


def calculate_word_similarity(word1: str, word2: str, use_context: bool = True) -> float:
    """
    Calculate similarity between two words using multiple metrics.
    Returns a score from 0 to 100.
    
    Args:
        word1: First word to compare
        word2: Second word to compare
        use_context: If True, adds semantic/contextual similarity
    """
    word1 = word1.lower().strip()
    word2 = word2.lower().strip()
    
    if word1 == word2:
        return 100.0
    
    # Length similarity
    max_len = max(len(word1), len(word2))
    min_len = min(len(word1), len(word2))
    length_score = (min_len / max_len) * 15 if max_len > 0 else 0
    
    # Character overlap
    common_chars = sum(min(word1.count(c), word2.count(c)) for c in set(word1 + word2))
    char_score = (common_chars / max(len(word1), len(word2))) * 15
    
    # Levenshtein distance (simplified)
    distance = levenshtein_distance(word1, word2)
    max_distance = max(len(word1), len(word2))
    distance_score = ((max_distance - distance) / max_distance) * 20 if max_distance > 0 else 0
    
    # Common prefix/suffix
    prefix_len = 0
    for i in range(min_len):
        if word1[i] == word2[i]:
            prefix_len += 1
        else:
            break
    
    suffix_len = 0
    for i in range(1, min_len + 1):
        if word1[-i] == word2[-i]:
            suffix_len += 1
        else:
            break
    
    affix_score = ((prefix_len + suffix_len) / max_len) * 10 if max_len > 0 else 0
    
    # Base score from syntactic similarity
    base_score = length_score + char_score + distance_score + affix_score
    
    # Context-aware semantic similarity (up to 40 points bonus)
    if use_context:
        context_score = calculate_semantic_similarity(word1, word2)
        total_score = base_score + context_score
    else:
        total_score = base_score
    
    return min(100.0, total_score)


def calculate_semantic_similarity(word1: str, word2: str) -> float:
    """
    Calculate semantic/contextual similarity between two words.
    Uses predefined semantic relationships and categories.
    Returns a score from 0 to 40.
    """
    # Define semantic categories and relationships
    semantic_groups = {
        # Nature
        'tree': ['forest', 'wood', 'leaf', 'branch', 'oak', 'pine', 'nature', 'park', 'green'],
        'forest': ['tree', 'wood', 'nature', 'wilderness', 'trees', 'woods'],
        'flower': ['garden', 'plant', 'rose', 'bloom', 'petal', 'nature'],
        'garden': ['flower', 'plant', 'nature', 'yard', 'green'],
        
        # Animals
        'dog': ['pet', 'animal', 'puppy', 'canine', 'bark'],
        'cat': ['pet', 'animal', 'kitten', 'feline', 'meow'],
        'bird': ['animal', 'fly', 'wing', 'feather', 'nest'],
        
        # Technology
        'computer': ['technology', 'internet', 'screen', 'keyboard', 'software', 'digital'],
        'internet': ['computer', 'web', 'online', 'network', 'digital'],
        'phone': ['mobile', 'call', 'smartphone', 'technology', 'communication'],
        
        # Buildings/Places
        'house': ['home', 'building', 'residence', 'dwelling', 'apartment'],
        'home': ['house', 'residence', 'dwelling', 'family'],
        'school': ['education', 'learning', 'student', 'teacher', 'class'],
        'office': ['work', 'business', 'desk', 'workplace'],
        
        # German equivalents
        'baum': ['wald', 'holz', 'blatt', 'ast', 'natur', 'park'],
        'wald': ['baum', 'holz', 'natur', 'bäume'],
        'blume': ['garten', 'pflanze', 'rose', 'natur'],
        'garten': ['blume', 'pflanze', 'natur', 'grün'],
        'hund': ['tier', 'haustier', 'welpe'],
        'katze': ['tier', 'haustier', 'kätzchen'],
        'haus': ['heim', 'gebäude', 'wohnung', 'zuhause'],
        'computer': ['technologie', 'internet', 'bildschirm', 'tastatur'],
    }
    
    word1 = word1.lower()
    word2 = word2.lower()
    
    # Direct relationship check
    if word1 in semantic_groups:
        if word2 in semantic_groups[word1]:
            # Strong semantic relationship
            return 40.0
        # Check if they share a common related word
        related1 = set(semantic_groups[word1])
        if word2 in semantic_groups:
            related2 = set(semantic_groups[word2])
            overlap = related1 & related2
            if overlap:
                # Indirect relationship through common concept
                return 25.0
    
    # Check reverse direction
    if word2 in semantic_groups and word1 in semantic_groups[word2]:
        return 40.0
    
    # Check for compound word relationships
    if word1 in word2 or word2 in word1:
        return 20.0
    
    # Check for category similarity based on length and structure
    # Words in similar length ranges might be related
    len_diff = abs(len(word1) - len(word2))
    if len_diff <= 2:
        # Similar length words get a small boost
        return 5.0
    
    return 0.0


def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def _generate_fallback_word(language='de', difficulty=None):
    """
    Generate a fallback word using date-based seed for consistency.
    Used when database is unavailable.
    
    Args:
        language: 'de' or 'en'
        difficulty: 'easy', 'medium', or 'hard' (auto-determined if None)
    
    Returns:
        dict with word data or None
    """
    # Determine difficulty if not provided
    if difficulty is None:
        weekday = datetime.now(timezone.utc).weekday()
        if weekday >= 5:  # Saturday, Sunday
            difficulty = 'hard'
        elif weekday >= 3:  # Thursday, Friday
            difficulty = 'medium'
        else:
            difficulty = 'easy'
    
    word_lists = get_word_lists(language)
    if difficulty not in word_lists or not word_lists[difficulty]:
        logger.error(f"No words available for difficulty {difficulty} in language {language}")
        return None
    
    # Use date-based seed for consistent daily words without database
    today = datetime.now(timezone.utc).date()
    seed = int(today.strftime('%Y%m%d'))
    random.seed(seed)
    word = random.choice(word_lists[difficulty])
    random.seed()  # Reset seed
    
    logger.info(f"Generated fallback Word Find word for {today} ({language}, {difficulty}): {word}")
    return {'id': 0, 'word': word, 'difficulty': difficulty, 'language': language}


async def get_or_create_daily_word(db_helpers, language='de'):
    """Get today's word or create a new one for the specified language."""
    # Fallback: if database is not available, generate word from list
    if not db_helpers or not hasattr(db_helpers, 'db_pool') or not db_helpers.db_pool:
        logger.warning("Database pool not available for Word Find - using fallback mode")
        return _generate_fallback_word(language)
    
    conn = db_helpers.db_pool.get_connection()
    if not conn:
        logger.warning("Could not get database connection for Word Find - using fallback mode")
        return _generate_fallback_word(language)
    
    cursor = conn.cursor(dictionary=True)
    try:
        today = datetime.now(timezone.utc).date()
        
        # Choose difficulty based on day of week (harder on weekends)
        weekday = today.weekday()
        if weekday >= 5:  # Saturday, Sunday
            difficulty = 'hard'
        elif weekday >= 3:  # Thursday, Friday
            difficulty = 'medium'
        else:
            difficulty = 'easy'
        
        # Check if today's word exists for this language
        cursor.execute("""
            SELECT id, word, difficulty, language FROM word_find_daily
            WHERE date = %s AND language = %s
        """, (today, language))
        result = cursor.fetchone()
        
        if result:
            logger.debug(f"Found existing Word Find word for {today} ({language}): {result['word']}")
            return result
        
        # Use curated list to ensure consistency
        logger.info(f"Generating new daily word for Word Find ({language}, {difficulty})")
        word_lists = get_word_lists(language)
        if difficulty not in word_lists or not word_lists[difficulty]:
            logger.error(f"No words available for difficulty {difficulty} in language {language}")
            return None
        
        # Select a random word from the curated list
        word = random.choice(word_lists[difficulty])
        
        cursor.execute("""
            INSERT INTO word_find_daily (word, difficulty, language, date)
            VALUES (%s, %s, %s, %s)
        """, (word, difficulty, language, today))
        
        conn.commit()
        word_id = cursor.lastrowid
        
        logger.info(f"Created new Word Find word for {today} ({language}, {difficulty}): {word}")
        return {'id': word_id, 'word': word, 'difficulty': difficulty, 'language': language}
    except Exception as e:
        logger.error(f"Database error in get_or_create_daily_word: {e}", exc_info=True)
        try:
            conn.rollback()
        except (Exception, AttributeError):
            pass  # Connection may already be closed or invalid
        # Fallback to word list on database error
        logger.warning("Using fallback word generation due to database error")
        return _generate_fallback_word(language)
    finally:
        cursor.close()
        conn.close()





async def get_user_attempts(db_helpers, user_id: int, word_id: int, game_type: str = 'daily'):
    """Get user's attempts for today's word."""
    try:
        if not db_helpers.db_pool:
            return []
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return []
        
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT guess, similarity_score, attempt_number
                FROM word_find_attempts
                WHERE user_id = %s AND word_id = %s AND game_type = %s
                ORDER BY attempt_number ASC
            """, (user_id, word_id, game_type))
            
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error getting user attempts: {e}", exc_info=True)
        return []


async def record_attempt(db_helpers, user_id: int, word_id: int, guess: str, similarity: float, attempt_num: int, game_type: str = 'daily'):
    """Record a guess attempt."""
    try:
        if not db_helpers.db_pool:
            return False
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO word_find_attempts (user_id, word_id, guess, similarity_score, attempt_number, game_type)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (user_id, word_id, guess, similarity, attempt_num, game_type))
            
            conn.commit()
            return True
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error recording attempt: {e}", exc_info=True)
        return False


async def update_user_stats(db_helpers, user_id: int, won: bool, attempts: int, game_type: str = 'daily'):
    """Update user's Word Find statistics (backwards compatible with old schema)."""
    try:
        if not db_helpers.db_pool:
            return
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return
        
        cursor = conn.cursor(dictionary=True)
        try:
            today = datetime.now(timezone.utc).date()
            
            # Get current stats
            cursor.execute("""
                SELECT * FROM word_find_stats WHERE user_id = %s
            """, (user_id,))
            stats = cursor.fetchone()
            
            if game_type == 'daily':
                if stats:
                    # Update existing daily stats
                    new_streak = stats.get('daily_streak', stats.get('current_streak', 0)) + 1 if won else 0
                    new_best_streak = max(stats.get('daily_best_streak', stats.get('best_streak', 0)), new_streak)
                    
                    # Update both old and new columns for backwards compatibility
                    cursor.execute("""
                        UPDATE word_find_stats
                        SET total_games = total_games + 1,
                            total_wins = total_wins + %s,
                            current_streak = %s,
                            best_streak = %s,
                            total_attempts = total_attempts + %s,
                            daily_games = daily_games + 1,
                            daily_wins = daily_wins + %s,
                            daily_streak = %s,
                            daily_best_streak = %s,
                            daily_total_attempts = daily_total_attempts + %s,
                            last_played = %s
                        WHERE user_id = %s
                    """, (1 if won else 0, new_streak, new_best_streak, attempts,
                          1 if won else 0, new_streak, new_best_streak, attempts, today, user_id))
                else:
                    # Create new stats (populate both old and new columns)
                    cursor.execute("""
                        INSERT INTO word_find_stats 
                        (user_id, total_games, total_wins, current_streak, best_streak, total_attempts,
                         daily_games, daily_wins, daily_streak, daily_best_streak, daily_total_attempts, last_played)
                        VALUES (%s, 1, %s, %s, %s, %s, 1, %s, %s, %s, %s, %s)
                    """, (user_id, 1 if won else 0, 1 if won else 0, 1 if won else 0, attempts,
                          1 if won else 0, 1 if won else 0, 1 if won else 0, attempts, today))
            else:  # premium
                if stats:
                    # Update existing premium stats (don't touch old columns for premium games)
                    cursor.execute("""
                        UPDATE word_find_stats
                        SET premium_games = premium_games + 1,
                            premium_wins = premium_wins + %s,
                            premium_total_attempts = premium_total_attempts + %s,
                            last_played = %s
                        WHERE user_id = %s
                    """, (1 if won else 0, attempts, today, user_id))
                else:
                    # Create new stats with premium game
                    cursor.execute("""
                        INSERT INTO word_find_stats 
                        (user_id, premium_games, premium_wins, premium_total_attempts, last_played)
                        VALUES (%s, 1, %s, %s, %s)
                    """, (user_id, 1 if won else 0, attempts, today))
            
            
            conn.commit()
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error updating user stats: {e}", exc_info=True)


async def get_user_stats(db_helpers, user_id: int):
    """Get user's Word Find statistics."""
    try:
        if not db_helpers.db_pool:
            return None
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return None
        
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT * FROM word_find_stats WHERE user_id = %s
            """, (user_id,))
            
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error getting user stats: {e}", exc_info=True)
        return None


async def create_premium_game(db_helpers, user_id: int, language='de'):
    """Create a new premium game for a user."""
    try:
        if not db_helpers.db_pool:
            return None
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return None
        
        cursor = conn.cursor(dictionary=True)
        try:
            # Choose random difficulty and word from language-specific lists
            difficulty = random.choice(['easy', 'medium', 'hard'])
            word_lists = get_word_lists(language)
            if difficulty not in word_lists or not word_lists[difficulty]:
                logger.error(f"No words available for difficulty {difficulty} in language {language}")
                return None
            
            word = random.choice(word_lists[difficulty])
            
            cursor.execute("""
                INSERT INTO word_find_premium_games (user_id, word, difficulty, language)
                VALUES (%s, %s, %s, %s)
            """, (user_id, word, difficulty, language))
            
            conn.commit()
            game_id = cursor.lastrowid
            
            logger.info(f"Created premium Word Find game {game_id} for user {user_id}: {word} ({language}, {difficulty})")
            return {'id': game_id, 'word': word, 'difficulty': difficulty, 'language': language, 'type': 'premium'}
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error creating premium game: {e}", exc_info=True)
        return None


async def complete_premium_game(db_helpers, game_id: int, won: bool):
    """Mark a premium game as completed."""
    try:
        if not db_helpers.db_pool:
            return False
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE word_find_premium_games
                SET completed = TRUE, won = %s
                WHERE id = %s
            """, (won, game_id))
            
            conn.commit()
            return True
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error completing premium game: {e}", exc_info=True)
        return False


def _get_proximity_indicator(score: float) -> tuple:
    """
    Get visual indicators for proximity score.
    
    Returns:
        tuple: (bar_string, temperature_string)
    """
    # Visual bar for score
    bar_length = int(score / 10)
    bar = "🟩" * bar_length + "⬜" * (10 - bar_length)
    
    # Temperature indicator
    if score >= 80:
        temp = "🔥 Sehr heiß!"
    elif score >= 60:
        temp = "🌡️ Heiß!"
    elif score >= 40:
        temp = "🌤️ Warm"
    elif score >= 20:
        temp = "❄️ Kalt"
    else:
        temp = "🧊 Sehr kalt"
    
    return bar, temp


def create_game_embed(word_data: dict, attempts: list, max_attempts: int, user_stats: dict = None, game_type: str = 'daily', theme_id=None):
    """Create the game embed with current progress and theme support."""
    # Extract difficulty first (needed for both color and description)
    difficulty = word_data.get('difficulty', 'medium')
    
    # Import themes here to avoid circular import
    try:
        from modules import themes
        color = themes.get_theme_color(theme_id, 'primary')
    except (ImportError, ModuleNotFoundError, AttributeError) as e:
        # Fallback to difficulty-based colors
        difficulty_colors = {
            'easy': discord.Color.green(),
            'medium': discord.Color.orange(),
            'hard': discord.Color.red()
        }
        color = difficulty_colors.get(difficulty, discord.Color.blue())
    
    title = "🔍 Word Find - Tägliches Wortratespiel" if game_type == 'daily' else "🔍 Word Find - Premium Spiel"
    
    remaining_attempts = max_attempts - len(attempts)
    
    embed = discord.Embed(
        title=title,
        description=f"Errate das Wort! Du hast {max_attempts} Versuche.\n"
                   f"Schwierigkeit: **{difficulty.upper()}**\n"
                   f"Versuche: **{len(attempts)}/{max_attempts}** | Übrig: **{remaining_attempts}** 🎯",
        color=color
    )
    
    # Show ALL attempts in order with proximity scores
    if attempts:
        attempts_text = ""
        # Sort by attempt number to show chronological order
        sorted_attempts = sorted(attempts, key=lambda x: x['attempt_number'])
        
        # Show all attempts (not just top 10)
        for attempt in sorted_attempts:
            score = attempt['similarity_score']
            guess = attempt['guess']
            
            # Get visual indicators
            bar, temp = _get_proximity_indicator(score)
            
            attempts_text += f"`#{attempt['attempt_number']:02d}` **{guess}** - {score:.1f}% {temp}\n{bar}\n"
        
        # Split into multiple fields if too long (Discord has a 1024 char limit per field)
        if len(attempts_text) > 1000:
            # Split attempts into chunks
            attempt_chunks = []
            current_chunk = ""
            for attempt in sorted_attempts:
                score = attempt['similarity_score']
                guess = attempt['guess']
                bar, temp = _get_proximity_indicator(score)
                
                line = f"`#{attempt['attempt_number']:02d}` **{guess}** - {score:.1f}% {temp}\n{bar}\n"
                
                if len(current_chunk) + len(line) > 1000:
                    attempt_chunks.append(current_chunk)
                    current_chunk = line
                else:
                    current_chunk += line
            
            if current_chunk:
                attempt_chunks.append(current_chunk)
            
            # Add multiple fields
            for idx, chunk in enumerate(attempt_chunks):
                field_name = f"📝 Deine Versuche (Teil {idx + 1}/{len(attempt_chunks)})" if len(attempt_chunks) > 1 else f"📝 Deine Versuche"
                embed.add_field(
                    name=field_name,
                    value=chunk,
                    inline=False
                )
        else:
            embed.add_field(
                name=f"📝 Deine Versuche",
                value=attempts_text if attempts_text else "Noch keine Versuche",
                inline=False
            )
    else:
        embed.add_field(
            name=f"📝 Versuche",
            value="Noch keine Versuche. Rate ein Wort!",
            inline=False
        )
    
    # Add user stats if available
    if user_stats:
        if game_type == 'daily':
            total_games = user_stats.get('daily_games', 0)
            total_wins = user_stats.get('daily_wins', 0)
            current_streak = user_stats.get('daily_streak', 0)
            best_streak = user_stats.get('daily_best_streak', 0)
            total_attempts = user_stats.get('daily_total_attempts', 0)
        else:  # premium
            total_games = user_stats.get('premium_games', 0)
            total_wins = user_stats.get('premium_wins', 0)
            current_streak = 0  # No streak for premium games
            best_streak = 0
            total_attempts = user_stats.get('premium_total_attempts', 0)
        
        win_rate = (total_wins / total_games * 100) if total_games > 0 else 0
        avg_attempts = (total_attempts / total_wins) if total_wins > 0 else 0
        
        stats_text = f"Spiele: `{total_games}` | Gewonnen: `{total_wins}` ({win_rate:.1f}%)\n"
        if game_type == 'daily':
            stats_text += f"Streak: `{current_streak}` 🔥 | Best: `{best_streak}`\n"
        if avg_attempts > 0:
            stats_text += f"Ø Versuche pro Sieg: `{avg_attempts:.1f}`"
        
        embed.add_field(name="📊 Deine Statistiken", value=stats_text, inline=False)
    
    embed.set_footer(text="💡 Tipp: Nähere dich dem Wort durch ähnliche Begriffe!")
    
    return embed


def create_share_text(attempts: list, won: bool, game_type: str = 'daily'):
    """Create shareable text for wordfind results (without spoiling the word)."""
    date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    # Sort attempts by attempt number
    sorted_attempts = sorted(attempts, key=lambda x: x['attempt_number'])
    
    # Create emoji representation
    emoji_pattern = ""
    for attempt in sorted_attempts:
        score = attempt['similarity_score']
        if score >= 100:
            emoji_pattern += "🟩"  # Correct
        elif score >= 80:
            emoji_pattern += "🟧"  # Very hot
        elif score >= 60:
            emoji_pattern += "🟨"  # Hot
        elif score >= 40:
            emoji_pattern += "🟦"  # Warm
        elif score >= 20:
            emoji_pattern += "⬜"  # Cold
        else:
            emoji_pattern += "⬛"  # Very cold
    
    game_label = "Tägliches" if game_type == 'daily' else "Premium"
    result = "✅" if won else "❌"
    
    share_text = f"🔍 Word Find {game_label} {date_str}\n"
    share_text += f"{result} {len(attempts)}/20\n\n"
    share_text += f"{emoji_pattern}\n\n"
    share_text += "Spiele mit: /wordfind"
    
    return share_text
