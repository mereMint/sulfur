"""
Sulfur Bot - Word Find Game Module
Daily word guessing game with proximity-based hints.
Words are now organized by themes for better semantic relationships.
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


def load_themed_word_lists(filename):
    """Load themed word lists from JSON file."""
    try:
        filepath = os.path.join('config', filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('themes', [])
    except Exception as e:
        logger.error(f"Error loading themed word list from {filename}: {e}")
        return []


# Load themed word lists (new context-based system)
THEMED_WORDS_DE = load_themed_word_lists('word_find_themes_de.json')
THEMED_WORDS_EN = load_themed_word_lists('word_find_themes_en.json')

# Create lookup dictionaries for themes
THEMES_BY_ID_DE = {theme['id']: theme for theme in THEMED_WORDS_DE}
THEMES_BY_ID_EN = {theme['id']: theme for theme in THEMED_WORDS_EN}

# Also load old word lists for backward compatibility
WORD_LISTS_DE = load_word_list_dict('word_find_words_de.json')
WORD_LISTS_EN = load_word_list_dict('word_find_words_en.json')

# Fallback hardcoded themes in case files don't exist
if not THEMED_WORDS_DE:
    logger.warning("Using fallback German themed word lists")
    THEMED_WORDS_DE = [
        {
            "id": "ozean",
            "name": "Ozean & Meer",
            "difficulty": "easy",
            "words": ["meer", "welle", "strand", "fisch", "schiff", "ozean", "wasser", "boot", "sand", "muschel"]
        },
        {
            "id": "wald",
            "name": "Wald & Natur",
            "difficulty": "easy",
            "words": ["wald", "baum", "blatt", "pilz", "fuchs", "reh", "eiche", "moos", "vogel", "nest"]
        },
        {
            "id": "technik",
            "name": "Technologie",
            "difficulty": "medium",
            "words": ["computer", "internet", "tastatur", "maus", "bildschirm", "handy", "laptop", "software", "app", "email"]
        },
        {
            "id": "wissenschaft",
            "name": "Wissenschaft",
            "difficulty": "hard",
            "words": ["wissenschaft", "forschung", "experiment", "labor", "theorie", "hypothese", "beweis", "analyse", "daten", "studie"]
        }
    ]
    THEMES_BY_ID_DE = {theme['id']: theme for theme in THEMED_WORDS_DE}

if not THEMED_WORDS_EN:
    logger.warning("Using fallback English themed word lists")
    THEMED_WORDS_EN = [
        {
            "id": "ocean",
            "name": "Ocean & Sea",
            "difficulty": "easy",
            "words": ["sea", "wave", "beach", "fish", "ship", "ocean", "water", "boat", "sand", "shell"]
        },
        {
            "id": "forest",
            "name": "Forest & Nature",
            "difficulty": "easy",
            "words": ["forest", "tree", "leaf", "mushroom", "fox", "deer", "oak", "moss", "bird", "nest"]
        },
        {
            "id": "technology",
            "name": "Technology",
            "difficulty": "medium",
            "words": ["computer", "internet", "keyboard", "mouse", "screen", "phone", "laptop", "software", "app", "email"]
        },
        {
            "id": "science",
            "name": "Science",
            "difficulty": "hard",
            "words": ["science", "research", "experiment", "laboratory", "theory", "hypothesis", "proof", "analysis", "data", "study"]
        }
    ]
    THEMES_BY_ID_EN = {theme['id']: theme for theme in THEMED_WORDS_EN}

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

# Log loaded themes count
de_theme_count = len(THEMED_WORDS_DE)
en_theme_count = len(THEMED_WORDS_EN)
de_word_count = sum(len(t.get('words', [])) for t in THEMED_WORDS_DE)
en_word_count = sum(len(t.get('words', [])) for t in THEMED_WORDS_EN)
logger.info(f"Loaded Word Find themed lists: DE={de_theme_count} themes ({de_word_count} words), EN={en_theme_count} themes ({en_word_count} words)")


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


def get_themed_word_lists(language='de'):
    """Get themed word lists for specified language."""
    if language == 'en':
        return THEMED_WORDS_EN
    else:
        return THEMED_WORDS_DE


def get_theme_by_id(theme_id: str, language='de'):
    """Get a specific theme by its ID."""
    if language == 'en':
        return THEMES_BY_ID_EN.get(theme_id)
    else:
        return THEMES_BY_ID_DE.get(theme_id)


def get_themes_by_difficulty(difficulty: str, language='de'):
    """Get all themes of a given difficulty level."""
    themes = get_themed_word_lists(language)
    return [t for t in themes if t.get('difficulty') == difficulty]


def get_random_theme(difficulty: str = None, language='de'):
    """
    Get a random theme, optionally filtered by difficulty.
    
    Args:
        difficulty: 'easy', 'medium', 'hard', or None for any
        language: 'de' or 'en'
    
    Returns:
        A theme dict with id, name, difficulty, and words
    """
    themes = get_themed_word_lists(language)
    
    if difficulty:
        themes = [t for t in themes if t.get('difficulty') == difficulty]
    
    if not themes:
        # Fallback to all themes if no themes match difficulty
        themes = get_themed_word_lists(language)
    
    if not themes:
        # Ultimate fallback
        logger.error(f"No themes available for language {language}")
        return None
    
    return random.choice(themes)


def get_theme_words(theme_id: str, language='de') -> list:
    """Get all words for a specific theme."""
    theme = get_theme_by_id(theme_id, language)
    if theme:
        return theme.get('words', [])
    return []


def get_all_themed_words(language='de') -> set:
    """Get all words from all themes as a set for validation."""
    themes = get_themed_word_lists(language)
    all_words = set()
    for theme in themes:
        for word in theme.get('words', []):
            all_words.add(word.lower())
    return all_words


def get_valid_word_pool(language='de'):
    """
    Get a comprehensive set of valid words for guess validation.
    Combines all themed words and old difficulty levels into a single set for validation.
    
    Args:
        language: 'de' or 'en'
    
    Returns:
        Set of valid words (lowercase)
    """
    # Start with all themed words (primary source)
    valid_words = get_all_themed_words(language)
    
    # Also add words from old difficulty-based lists for backward compatibility
    word_lists = get_word_lists(language)
    for difficulty in ['easy', 'medium', 'hard']:
        for word in word_lists.get(difficulty, []):
            valid_words.add(word.lower())
    
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
            
            # First, check for and fix schema conflicts (from old migration 010)
            # Check if word_find_daily exists with wrong schema
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'word_find_daily' 
                AND COLUMN_NAME = 'puzzle_date'
            """)
            result = cursor.fetchone()
            has_wrong_schema = result and result[0] > 0
            
            if has_wrong_schema:
                logger.warning("Detected word_find_daily table with incorrect schema - fixing...")
                cursor.execute("DROP TABLE IF EXISTS word_find_daily")
                logger.info("Dropped incorrect word_find_daily table")
            
            # Also drop other incorrectly named/structured tables if they exist
            # These tables were created by buggy migration 010 and should never exist
            cursor.execute("DROP TABLE IF EXISTS word_find_user_progress")
            logger.debug("Cleaned up word_find_user_progress if it existed")
            cursor.execute("DROP TABLE IF EXISTS word_find_user_stats")  # Wrong name, should be word_find_stats
            logger.debug("Cleaned up word_find_user_stats if it existed")
            
            # Check if word_find_attempts exists but is missing the game_type column
            # This can happen if the table was created by an old version of the code
            # First check if table exists to avoid unnecessary work
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'word_find_attempts'
            """)
            result = cursor.fetchone()
            attempts_table_exists = result and result[0] > 0
            
            if attempts_table_exists:
                # Table exists, check if it has the game_type column
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = DATABASE()
                    AND TABLE_NAME = 'word_find_attempts' 
                    AND COLUMN_NAME = 'game_type'
                """)
                result = cursor.fetchone()
                has_game_type = result and result[0] > 0
                
                # If table exists but missing game_type column, drop and recreate
                if not has_game_type:
                    logger.warning("Detected word_find_attempts table missing game_type column - fixing...")
                    cursor.execute("DROP TABLE IF EXISTS word_find_attempts")
                    logger.info("Dropped word_find_attempts table to recreate with correct schema")
            
            # Table for daily word
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS word_find_daily (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    word VARCHAR(100) NOT NULL,
                    difficulty VARCHAR(20) NOT NULL,
                    language VARCHAR(2) DEFAULT 'de',
                    theme_id VARCHAR(50) DEFAULT NULL,
                    date DATE NOT NULL,
                    UNIQUE KEY unique_date_lang (date, language),
                    INDEX idx_date (date),
                    INDEX idx_lang (language),
                    INDEX idx_theme (theme_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Add theme_id column to existing tables if it doesn't exist
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'word_find_daily' 
                AND COLUMN_NAME = 'theme_id'
            """)
            result = cursor.fetchone()
            if result and result[0] == 0:
                logger.info("Adding theme_id column to word_find_daily table...")
                cursor.execute("ALTER TABLE word_find_daily ADD COLUMN theme_id VARCHAR(50) DEFAULT NULL")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_theme ON word_find_daily (theme_id)")
            
            # Table for premium games (separate from daily)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS word_find_premium_games (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    word VARCHAR(100) NOT NULL,
                    difficulty VARCHAR(20) NOT NULL,
                    language VARCHAR(2) DEFAULT 'de',
                    theme_id VARCHAR(50) DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed BOOLEAN DEFAULT FALSE,
                    won BOOLEAN DEFAULT FALSE,
                    INDEX idx_user_created (user_id, created_at),
                    INDEX idx_theme (theme_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Add theme_id column to premium games if it doesn't exist
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'word_find_premium_games' 
                AND COLUMN_NAME = 'theme_id'
            """)
            result = cursor.fetchone()
            if result and result[0] == 0:
                logger.info("Adding theme_id column to word_find_premium_games table...")
                cursor.execute("ALTER TABLE word_find_premium_games ADD COLUMN theme_id VARCHAR(50) DEFAULT NULL")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_theme ON word_find_premium_games (theme_id)")
            
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


def calculate_word_similarity(word1: str, word2: str, use_context: bool = True, theme_id: str = None, language: str = 'de') -> float:
    """
    Calculate similarity between two words using multiple metrics.
    Returns a score from 0 to 100.
    
    Args:
        word1: First word to compare (the guess)
        word2: Second word to compare (the target)
        use_context: If True, adds semantic/contextual similarity
        theme_id: Optional theme ID for enhanced context-based scoring
        language: Language code ('de' or 'en')
    """
    word1 = word1.lower().strip()
    word2 = word2.lower().strip()
    
    if word1 == word2:
        return 100.0
    
    # Length similarity
    max_len = max(len(word1), len(word2))
    min_len = min(len(word1), len(word2))
    length_score = (min_len / max_len) * 10 if max_len > 0 else 0
    
    # Character overlap
    common_chars = sum(min(word1.count(c), word2.count(c)) for c in set(word1 + word2))
    char_score = (common_chars / max(len(word1), len(word2))) * 10
    
    # Levenshtein distance (simplified)
    distance = levenshtein_distance(word1, word2)
    max_distance = max(len(word1), len(word2))
    distance_score = ((max_distance - distance) / max_distance) * 15 if max_distance > 0 else 0
    
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
    
    affix_score = ((prefix_len + suffix_len) / max_len) * 5 if max_len > 0 else 0
    
    # Base score from syntactic similarity (up to ~40 points)
    base_score = length_score + char_score + distance_score + affix_score
    
    # Context-aware semantic similarity (up to 60 points bonus for themed words)
    context_score = 0.0
    if use_context:
        # First, check if the guess is in the same theme as the target (big bonus!)
        if theme_id:
            context_score = calculate_theme_similarity(word1, word2, theme_id, language)
        
        # If no theme match or low theme score, fall back to general semantic similarity
        if context_score < 20:
            general_context = calculate_semantic_similarity(word1, word2)
            context_score = max(context_score, general_context)
    
    total_score = base_score + context_score
    
    return min(99.9, total_score)  # Cap at 99.9, only exact match gets 100


def calculate_theme_similarity(word1: str, word2: str, theme_id: str, language: str = 'de') -> float:
    """
    Calculate similarity between two words based on theme membership.
    Words in the same theme get a high similarity bonus.
    
    Args:
        word1: First word (the guess)
        word2: Second word (the target)
        theme_id: The theme ID to check
        language: Language code
    
    Returns:
        A score from 0 to 60 based on theme relationship
    """
    theme = get_theme_by_id(theme_id, language)
    if not theme:
        return 0.0
    
    theme_words = set(w.lower() for w in theme.get('words', []))
    word1_lower = word1.lower()
    word2_lower = word2.lower()
    
    # Both words are in the same theme - give a big bonus!
    if word1_lower in theme_words and word2_lower in theme_words:
        # Calculate position-based bonus (words closer together in the list are more related)
        words_list = [w.lower() for w in theme.get('words', [])]
        try:
            pos1 = words_list.index(word1_lower)
            pos2 = words_list.index(word2_lower)
            distance = abs(pos1 - pos2)
            max_distance = len(words_list) - 1
            
            # Base theme bonus for being in the same theme
            theme_bonus = 40.0
            
            # Additional bonus based on position proximity (up to 20 more points)
            if max_distance > 0:
                position_bonus = ((max_distance - distance) / max_distance) * 20
            else:
                position_bonus = 20.0
            
            return theme_bonus + position_bonus
        except ValueError:
            # Word not found in list, but is in theme set
            return 40.0
    
    # Guess is in the theme but target might be too (fallback)
    if word1_lower in theme_words:
        return 25.0  # Good guess, in the right theme
    
    return 0.0


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
    Uses themed word lists for better context-based gameplay.
    Used when database is unavailable.
    
    Args:
        language: 'de' or 'en'
        difficulty: 'easy', 'medium', or 'hard' (auto-determined if None)
    
    Returns:
        dict with word data including theme_id, or None
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
    
    # Use date-based seed for consistent daily words without database
    today = datetime.now(timezone.utc).date()
    seed = int(today.strftime('%Y%m%d'))
    random.seed(seed)
    
    # Try to get a themed word first (preferred)
    theme = get_random_theme(difficulty, language)
    
    if theme and theme.get('words'):
        word = random.choice(theme['words'])
        theme_id = theme['id']
        random.seed()  # Reset seed
        
        logger.info(f"Generated fallback Word Find word for {today} ({language}, {difficulty}, theme={theme_id}): {word}")
        return {
            'id': 0,
            'word': word,
            'difficulty': difficulty,
            'language': language,
            'theme_id': theme_id,
            'theme_name': theme.get('name', '')
        }
    
    # Fallback to old word lists if no themed words available
    word_lists = get_word_lists(language)
    if difficulty not in word_lists or not word_lists[difficulty]:
        logger.error(f"No words available for difficulty {difficulty} in language {language}")
        random.seed()  # Reset seed
        return None
    
    word = random.choice(word_lists[difficulty])
    random.seed()  # Reset seed
    
    logger.info(f"Generated fallback Word Find word for {today} ({language}, {difficulty}): {word}")
    return {'id': 0, 'word': word, 'difficulty': difficulty, 'language': language, 'theme_id': None}


async def get_or_create_daily_word(db_helpers, language='de'):
    """
    Get today's word or create a new one for the specified language.
    Uses themed word lists for context-based gameplay.
    """
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
            SELECT id, word, difficulty, language, theme_id FROM word_find_daily
            WHERE date = %s AND language = %s
        """, (today, language))
        result = cursor.fetchone()
        
        if result:
            # Add theme_name if we have a theme_id
            if result.get('theme_id'):
                theme = get_theme_by_id(result['theme_id'], language)
                if theme:
                    result['theme_name'] = theme.get('name', '')
            logger.debug(f"Found existing Word Find word for {today} ({language}): {result['word']}")
            return result
        
        # Generate new daily word using themed lists
        logger.info(f"Generating new daily word for Word Find ({language}, {difficulty})")
        
        # Get a random theme for this difficulty
        theme = get_random_theme(difficulty, language)
        
        if theme and theme.get('words'):
            word = random.choice(theme['words'])
            theme_id = theme['id']
            theme_name = theme.get('name', '')
        else:
            # Fallback to old word lists if no themed words available
            word_lists = get_word_lists(language)
            if difficulty not in word_lists or not word_lists[difficulty]:
                logger.error(f"No words available for difficulty {difficulty} in language {language}")
                return None
            word = random.choice(word_lists[difficulty])
            theme_id = None
            theme_name = None
        
        # Insert with theme_id
        cursor.execute("""
            INSERT INTO word_find_daily (word, difficulty, language, theme_id, date)
            VALUES (%s, %s, %s, %s, %s)
        """, (word, difficulty, language, theme_id, today))
        
        conn.commit()
        word_id = cursor.lastrowid
        
        logger.info(f"Created new Word Find word for {today} ({language}, {difficulty}, theme={theme_id}): {word}")
        return {
            'id': word_id,
            'word': word,
            'difficulty': difficulty,
            'language': language,
            'theme_id': theme_id,
            'theme_name': theme_name
        }
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
            logger.error("Cannot record attempt: Database pool not available")
            return False
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            logger.error("Cannot record attempt: Could not get database connection")
            return False
        
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO word_find_attempts (user_id, word_id, guess, similarity_score, attempt_number, game_type)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (user_id, word_id, guess, similarity, attempt_num, game_type))
            
            conn.commit()
            logger.debug(f"Recorded attempt for user {user_id}: guess='{guess}', similarity={similarity:.1f}%, attempt={attempt_num}, game_type={game_type}")
            return True
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error recording attempt for user {user_id}: {e}", exc_info=True)
        logger.error(f"  - word_id: {word_id}, guess: '{guess}', similarity: {similarity}, attempt_num: {attempt_num}, game_type: {game_type}")
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
    """Create a new premium game for a user using themed words."""
    try:
        if not db_helpers.db_pool:
            return None
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return None
        
        cursor = conn.cursor(dictionary=True)
        try:
            # Choose random difficulty
            difficulty = random.choice(['easy', 'medium', 'hard'])
            
            # Get a random theme for this difficulty
            theme = get_random_theme(difficulty, language)
            
            if theme and theme.get('words'):
                word = random.choice(theme['words'])
                theme_id = theme['id']
                theme_name = theme.get('name', '')
            else:
                # Fallback to old word lists
                word_lists = get_word_lists(language)
                if difficulty not in word_lists or not word_lists[difficulty]:
                    logger.error(f"No words available for difficulty {difficulty} in language {language}")
                    return None
                word = random.choice(word_lists[difficulty])
                theme_id = None
                theme_name = None
            
            cursor.execute("""
                INSERT INTO word_find_premium_games (user_id, word, difficulty, language, theme_id)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, word, difficulty, language, theme_id))
            
            conn.commit()
            game_id = cursor.lastrowid
            
            logger.info(f"Created premium Word Find game {game_id} for user {user_id}: {word} ({language}, {difficulty}, theme={theme_id})")
            return {
                'id': game_id,
                'word': word,
                'difficulty': difficulty,
                'language': language,
                'theme_id': theme_id,
                'theme_name': theme_name,
                'type': 'premium'
            }
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


def _get_proximity_indicator(score: float, strings: dict = None) -> tuple:
    """
    Get visual indicators for proximity score.
    
    Args:
        score: Similarity score (0-100)
        strings: Optional localization strings dict
    
    Returns:
        tuple: (bar_string, temperature_string)
    """
    # Visual bar for score
    bar_length = int(score / 10)
    bar = "🟩" * bar_length + "⬜" * (10 - bar_length)
    
    # Temperature indicator with localization
    if strings:
        if score >= 80:
            temp = strings.get('very_hot', "🔥 Sehr heiß!")
        elif score >= 60:
            temp = strings.get('hot', "🌡️ Heiß!")
        elif score >= 40:
            temp = strings.get('warm', "🌤️ Warm")
        elif score >= 20:
            temp = strings.get('cold', "❄️ Kalt")
        else:
            temp = strings.get('very_cold', "🧊 Sehr kalt")
    else:
        # Default German for backward compatibility
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


def _get_language_indicator(language: str) -> tuple:
    """
    Get visual language indicator with flag emoji and language name.
    
    Args:
        language: 'de' or 'en'
    
    Returns:
        tuple: (flag_emoji, language_name)
    """
    if language == 'en':
        return "🇬🇧", "English"
    else:
        return "🇩🇪", "Deutsch"


def _get_localized_strings(language: str) -> dict:
    """
    Get localized UI strings for the game embed.
    
    Args:
        language: 'de' or 'en'
    
    Returns:
        dict with localized strings
    """
    if language == 'en':
        return {
            'daily_game': 'Daily Word Game',
            'premium_game': 'Premium Game',
            'guess_word': 'Guess the word! You have {max_attempts} attempts.',
            'language': 'Language',
            'difficulty': 'Difficulty',
            'attempts': 'Attempts',
            'remaining': 'Left',
            'your_attempts': 'Your Attempts',
            'your_attempts_part': 'Your Attempts (Part {idx}/{total})',
            'no_attempts': 'No attempts yet. Guess a word!',
            'your_stats': 'Your Statistics',
            'games': 'Games',
            'won': 'Won',
            'streak': 'Streak',
            'best': 'Best',
            'avg_attempts': 'Ø Attempts per Win',
            'tip': "💡 Tip: Get closer to the word through similar terms!",
            'very_hot': '🔥 Very hot!',
            'hot': '🌡️ Hot!',
            'warm': '🌤️ Warm',
            'cold': '❄️ Cold',
            'very_cold': '🧊 Very cold',
        }
    else:
        return {
            'daily_game': 'Tägliches Wortratespiel',
            'premium_game': 'Premium Spiel',
            'guess_word': 'Errate das Wort! Du hast {max_attempts} Versuche.',
            'language': 'Sprache',
            'difficulty': 'Schwierigkeit',
            'attempts': 'Versuche',
            'remaining': 'Übrig',
            'your_attempts': 'Deine Versuche',
            'your_attempts_part': 'Deine Versuche (Teil {idx}/{total})',
            'no_attempts': 'Noch keine Versuche. Rate ein Wort!',
            'your_stats': 'Deine Statistiken',
            'games': 'Spiele',
            'won': 'Gewonnen',
            'streak': 'Streak',
            'best': 'Best',
            'avg_attempts': 'Ø Versuche pro Sieg',
            'tip': "💡 Tipp: Nähere dich dem Wort durch ähnliche Begriffe!",
            'very_hot': '🔥 Sehr heiß!',
            'hot': '🌡️ Heiß!',
            'warm': '🌤️ Warm',
            'cold': '❄️ Kalt',
            'very_cold': '🧊 Sehr kalt',
        }


def create_game_embed(word_data: dict, attempts: list, max_attempts: int, user_stats: dict = None, game_type: str = 'daily', theme_id=None):
    """Create the game embed with current progress and theme support."""
    # Extract difficulty first (needed for both color and description)
    difficulty = word_data.get('difficulty', 'medium')
    
    # Extract language for visual indicator and localization
    language = word_data.get('language', 'de')
    flag, lang_name = _get_language_indicator(language)
    strings = _get_localized_strings(language)
    
    # Get theme information from word_data if available
    game_theme_id = word_data.get('theme_id') or theme_id
    theme_name = word_data.get('theme_name', '')
    
    # If we have a theme_id but no name, try to get it
    if game_theme_id and not theme_name:
        theme = get_theme_by_id(game_theme_id, language)
        if theme:
            theme_name = theme.get('name', '')
    
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
    
    game_type_label = strings['daily_game'] if game_type == 'daily' else strings['premium_game']
    title = f"🔍 Word Find {flag} - {game_type_label}"
    
    remaining_attempts = max_attempts - len(attempts)
    
    # Build description with theme hint if available
    description_lines = [
        strings['guess_word'].format(max_attempts=max_attempts),
        f"{strings['language']}: **{flag} {lang_name}** | {strings['difficulty']}: **{difficulty.upper()}**",
        f"{strings['attempts']}: **{len(attempts)}/{max_attempts}** | {strings['remaining']}: **{remaining_attempts}** 🎯"
    ]
    
    # Add theme hint - this is the key feature for context-based guessing!
    if theme_name:
        if language == 'en':
            description_lines.append(f"\n💡 **Hint:** The word belongs to the theme **\"{theme_name}\"**")
        else:
            description_lines.append(f"\n💡 **Hinweis:** Das Wort gehört zum Thema **\"{theme_name}\"**")
    
    embed = discord.Embed(
        title=title,
        description="\n".join(description_lines),
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
            
            # Get visual indicators with localized temperature strings
            bar, temp = _get_proximity_indicator(score, strings)
            
            attempts_text += f"`#{attempt['attempt_number']:02d}` **{guess}** - {score:.1f}% {temp}\n{bar}\n"
        
        # Split into multiple fields if too long (Discord has a 1024 char limit per field)
        if len(attempts_text) > 1000:
            # Split attempts into chunks
            attempt_chunks = []
            current_chunk = ""
            for attempt in sorted_attempts:
                score = attempt['similarity_score']
                guess = attempt['guess']
                bar, temp = _get_proximity_indicator(score, strings)
                
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
                field_name = f"📝 {strings['your_attempts_part'].format(idx=idx + 1, total=len(attempt_chunks))}" if len(attempt_chunks) > 1 else f"📝 {strings['your_attempts']}"
                embed.add_field(
                    name=field_name,
                    value=chunk,
                    inline=False
                )
        else:
            embed.add_field(
                name=f"📝 {strings['your_attempts']}",
                value=attempts_text if attempts_text else strings['no_attempts'],
                inline=False
            )
    else:
        embed.add_field(
            name=f"📝 {strings['attempts']}",
            value=strings['no_attempts'],
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
        
        stats_text = f"{strings['games']}: `{total_games}` | {strings['won']}: `{total_wins}` ({win_rate:.1f}%)\n"
        if game_type == 'daily':
            stats_text += f"{strings['streak']}: `{current_streak}` 🔥 | {strings['best']}: `{best_streak}`\n"
        if avg_attempts > 0:
            stats_text += f"{strings['avg_attempts']}: `{avg_attempts:.1f}`"
        
        embed.add_field(name=f"📊 {strings['your_stats']}", value=stats_text, inline=False)
    
    embed.set_footer(text=strings['tip'])
    
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
