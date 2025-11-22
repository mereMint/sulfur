"""
Sulfur Bot - Wordle Game Module
Classic Wordle game with 5-letter word guessing.
"""

import discord
import random
import json
import os
from datetime import datetime, timezone, timedelta
from modules.logger_utils import bot_logger as logger
from modules import word_service


# Load word lists from configuration files
def load_word_list(filename):
    """Load word list from JSON file."""
    try:
        filepath = os.path.join('config', filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading word list from {filename}: {e}")
        return []


# Load language-specific word lists
WORDLE_WORDS_DE = load_word_list('wordle_words_de.json')
WORDLE_WORDS_EN = load_word_list('wordle_words_en.json')

# Fallback hardcoded words in case files don't exist (for backward compatibility)
if not WORDLE_WORDS_DE:
    logger.warning("Using fallback German word list")
    WORDLE_WORDS_DE = [
    'apfel', 'bauer', 'brief', 'brust', 'dampf', 'decke', 'draht', 'eisen', 'engel', 'ernte',
    'essen', 'fahne', 'feuer', 'fisch', 'fluss', 'forst', 'frost', 'gabel', 'geist', 'hafen',
    'hagel', 'haken', 'halle', 'hirte', 'hitze', 'honig', 'hotel', 'insel', 'kabel', 'kampf',
    'kanal', 'kanne', 'karte', 'kasse', 'kette', 'klang', 'kleid', 'klein', 'knopf', 'kraft',
    'kranz', 'kreis', 'kreuz', 'krieg', 'krone', 'kugel', 'kunst', 'laden', 'lampe', 'lanze',
    'leder', 'leine', 'licht', 'lippe', 'liste', 'macht', 'maler', 'markt', 'maske', 'masse',
    'mauer', 'menge', 'milch', 'motor', 'musik', 'nabel', 'nacht', 'nadel', 'nagel', 'narbe',
    'nebel', 'orden', 'pfeil', 'pferd', 'pflug', 'platz', 'punkt', 'rasen', 'rasse', 'rauch',
    'recht', 'regal', 'regen', 'reich', 'reihe', 'reise', 'riese', 'sache', 'samen', 'scham',
    'schar', 'schuh', 'segel', 'segen', 'seide', 'seife', 'seite', 'sense', 'sonne', 'sorge',
    'spalt', 'spatz', 'speck', 'spiel', 'sporn', 'staat', 'stadt', 'stahl', 'stamm', 'stand',
    'staub', 'stein', 'stern', 'stich', 'stier', 'stirn', 'stock', 'stoff', 'stolz', 'strom',
    'stube', 'stuck', 'stufe', 'stuhl', 'sturm', 'stutz', 'sucht', 'sumpf', 'tafel', 'tanne',
    'tasse', 'taube', 'teich', 'thron', 'tinte', 'tisch', 'titel', 'trank', 'traum', 'treib',
    'treue', 'trieb', 'tritt', 'tropf', 'trost', 'truhe', 'trupp', 'unruh', 'vater', 'vogel',
    'wache', 'wachs', 'waffe', 'wagen', 'wange', 'wanne', 'watte', 'weber', 'weide', 'weihe',
    'weise', 'welle', 'wesen', 'weste', 'wicht', 'wiege', 'wiese', 'wille', 'wisch', 'witwe',
    'wolke', 'wolle', 'wonne', 'wucht', 'wunde', 'zange', 'zeche', 'zeile', 'ziege', 'zuber',
    'zucht', 'zunge', 'zwang', 'zweck', 'zweig', 'zwerg', 'zwirn',
]

if not WORDLE_WORDS_EN:
    logger.warning("Using fallback English word list")
    WORDLE_WORDS_EN = [
    'about', 'above', 'abuse', 'adapt', 'admit', 'adopt', 'adult', 'after', 'again', 'agent',
    'agree', 'ahead', 'alarm', 'album', 'alert', 'alien', 'align', 'alike', 'alive', 'allow',
    'alone', 'along', 'alter', 'among', 'angel', 'anger', 'angle', 'angry', 'apart', 'apple',
    'apply', 'arena', 'argue', 'arise', 'array', 'aside', 'asset', 'audio', 'avoid', 'awake',
    'award', 'aware', 'badly', 'baker', 'bases', 'basic', 'basin', 'basis', 'beach', 'began',
    'begin', 'begun', 'being', 'below', 'bench', 'billy', 'birth', 'black', 'blade', 'blame',
    'blank', 'blind', 'block', 'blood', 'board', 'boost', 'booth', 'bound', 'brain', 'brand',
    'brave', 'bread', 'break', 'breed', 'brief', 'bring', 'broad', 'broke', 'brown', 'build',
    'built', 'buyer', 'cable', 'calif', 'carry', 'catch', 'cause', 'chain', 'chair', 'chart',
    'chase', 'cheap', 'check', 'chest', 'chief', 'child', 'china', 'chose', 'civil', 'claim',
    'class', 'clean', 'clear', 'click', 'clock', 'close', 'coach', 'coast', 'could', 'count',
    'court', 'cover', 'crack', 'craft', 'crash', 'crazy', 'cream', 'crime', 'cross', 'crowd',
    'crown', 'crude', 'curve', 'cycle', 'daily', 'dance', 'dated', 'dealt', 'death', 'debut',
    'delay', 'depth', 'doing', 'doubt', 'dozen', 'draft', 'drama', 'drank', 'drawn', 'dream',
    'dress', 'drill', 'drink', 'drive', 'driven', 'drove', 'dying', 'eager', 'early', 'earth',
    'eight', 'elite', 'empty', 'enemy', 'enjoy', 'enter', 'entry', 'equal', 'error', 'event',
    'every', 'exact', 'exist', 'extra', 'faith', 'false', 'fault', 'fiber', 'field', 'fifth',
    'fifty', 'fight', 'final', 'first', 'fixed', 'flash', 'fleet', 'floor', 'fluid', 'focus',
    'force', 'forth', 'forty', 'forum', 'found', 'frame', 'frank', 'fraud', 'fresh', 'front',
    'fruit', 'fully', 'funny', 'giant', 'given', 'glass', 'globe', 'going', 'grace', 'grade',
    'grand', 'grant', 'grass', 'great', 'green', 'gross', 'group', 'grown', 'guard', 'guess',
    'guest', 'guide', 'happy', 'harry', 'heart', 'heavy', 'hence', 'henry', 'horse', 'hotel',
    'house', 'human', 'ideal', 'image', 'imply', 'index', 'inner', 'input', 'issue', 'japan',
    'jimmy', 'joint', 'jones', 'judge', 'known', 'label', 'large', 'laser', 'later', 'laugh',
    'layer', 'learn', 'lease', 'least', 'leave', 'legal', 'lemon', 'level', 'lewis', 'light',
    'limit', 'links', 'lives', 'local', 'logic', 'loose', 'lower', 'lucky', 'lunch', 'lying',
    'magic', 'major', 'maker', 'march', 'maria', 'match', 'maybe', 'mayor', 'meant', 'media',
    'metal', 'might', 'minor', 'minus', 'mixed', 'model', 'money', 'month', 'moral', 'motor',
    'mount', 'mouse', 'mouth', 'movie', 'music', 'needs', 'never', 'newly', 'night', 'noise',
    'north', 'noted', 'novel', 'nurse', 'occur', 'ocean', 'offer', 'often', 'order', 'other',
    'ought', 'paint', 'panel', 'paper', 'party', 'peace', 'peter', 'phase', 'phone', 'photo',
    'piece', 'pilot', 'pitch', 'place', 'plain', 'plane', 'plant', 'plate', 'point', 'pound',
    'power', 'press', 'price', 'pride', 'prime', 'print', 'prior', 'prize', 'proof', 'proud',
    'prove', 'queen', 'quick', 'quiet', 'quite', 'radio', 'raise', 'range', 'rapid', 'ratio',
    'reach', 'ready', 'refer', 'right', 'rival', 'river', 'robin', 'roger', 'roman', 'rough',
    'round', 'route', 'royal', 'rural', 'scale', 'scene', 'scope', 'score', 'sense', 'serve',
    'seven', 'shall', 'shape', 'share', 'sharp', 'sheet', 'shelf', 'shell', 'shift', 'shine',
    'shirt', 'shock', 'shoot', 'short', 'shown', 'sight', 'since', 'sixth', 'sixty', 'sized',
    'skill', 'sleep', 'slide', 'small', 'smart', 'smile', 'smith', 'smoke', 'solid', 'solve',
    'sorry', 'sound', 'south', 'space', 'spare', 'speak', 'speed', 'spend', 'spent', 'split',
    'spoke', 'sport', 'staff', 'stage', 'stake', 'stand', 'start', 'state', 'steam', 'steel',
    'stick', 'still', 'stock', 'stone', 'stood', 'store', 'storm', 'story', 'strip', 'stuck',
    'study', 'stuff', 'style', 'sugar', 'suite', 'super', 'sweet', 'table', 'taken', 'taste',
    'taxes', 'teach', 'terry', 'texas', 'thank', 'theft', 'their', 'theme', 'there', 'these',
    'thick', 'thing', 'think', 'third', 'those', 'three', 'threw', 'throw', 'tight', 'times',
    'title', 'today', 'topic', 'total', 'touch', 'tough', 'tower', 'track', 'trade', 'train',
    'treat', 'trend', 'trial', 'tribe', 'tried', 'tries', 'truck', 'truly', 'trust', 'truth',
    'twice', 'under', 'undue', 'union', 'unity', 'until', 'upper', 'urban', 'usage', 'usual',
    'valid', 'value', 'video', 'virus', 'visit', 'vital', 'vocal', 'voice', 'waste', 'watch',
    'water', 'wheel', 'where', 'which', 'while', 'white', 'whole', 'whose', 'woman', 'women',
    'world', 'worry', 'worse', 'worst', 'worth', 'would', 'wound', 'write', 'wrong', 'wrote',
    'young', 'youth',
]

# Default to German for backward compatibility
WORDLE_WORDS = WORDLE_WORDS_DE

logger.info(f"Loaded {len(WORDLE_WORDS_DE)} German words and {len(WORDLE_WORDS_EN)} English words for Wordle")

# Convert to sets for O(1) lookup performance
WORDLE_WORDS_DE_SET = set(WORDLE_WORDS_DE)
WORDLE_WORDS_EN_SET = set(WORDLE_WORDS_EN)


def get_wordle_words(language='de'):
    """Get Wordle word set for specified language (optimized for fast lookups)."""
    if language == 'en':
        return WORDLE_WORDS_EN_SET
    return WORDLE_WORDS_DE_SET


def get_wordle_words_list(language='de'):
    """Get Wordle word list for specified language (for selecting words)."""
    if language == 'en':
        return WORDLE_WORDS_EN
    return WORDLE_WORDS_DE


async def initialize_wordle_table(db_helpers):
    """Initialize the Wordle game table in the database."""
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
            # Table for daily word
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS wordle_daily (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    word VARCHAR(5) NOT NULL,
                    language VARCHAR(2) DEFAULT 'de',
                    date DATE NOT NULL,
                    UNIQUE KEY unique_date_lang (date, language),
                    INDEX idx_date (date),
                    INDEX idx_lang (language)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Table for user attempts
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS wordle_attempts (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    word_id INT NOT NULL,
                    guess VARCHAR(5) NOT NULL,
                    attempt_number INT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_user_word (user_id, word_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Table for user stats
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS wordle_stats (
                    user_id BIGINT PRIMARY KEY,
                    total_games INT DEFAULT 0,
                    total_wins INT DEFAULT 0,
                    current_streak INT DEFAULT 0,
                    best_streak INT DEFAULT 0,
                    guess_distribution JSON,
                    last_played DATE,
                    INDEX idx_last_played (last_played)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            conn.commit()
            logger.info("Wordle tables initialized successfully")
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error initializing Wordle tables: {e}", exc_info=True)


async def get_or_create_daily_word(db_helpers, language='de'):
    """Get or create today's Wordle word for the specified language."""
    try:
        if not db_helpers.db_pool:
            logger.error("Database pool not available for Wordle")
            return None
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            logger.error("Could not get database connection for Wordle")
            return None
        
        cursor = conn.cursor(dictionary=True)
        try:
            today = datetime.now(timezone.utc).date()
            
            # Check if today's word exists for this language
            cursor.execute("""
                SELECT id, word, language FROM wordle_daily
                WHERE date = %s AND language = %s
            """, (today, language))
            result = cursor.fetchone()
            
            if result:
                logger.debug(f"Found existing Wordle word for {today} ({language}): {result['word']}")
                return result
            
            # Create new daily word using word service (external API or fallback)
            logger.info(f"Fetching new daily word for Wordle ({language})")
            try:
                words = await word_service.get_random_words(1, language=language, min_length=5, max_length=5)
                if words and len(words) > 0:
                    word = words[0]
                else:
                    # Fallback to hardcoded list if service fails
                    logger.warning("Word service failed, using hardcoded list for Wordle")
                    word_list = get_wordle_words_list(language)
                    word = random.choice(word_list)
            except Exception as e:
                logger.error(f"Error fetching word from service: {e}")
                word_list = get_wordle_words_list(language)
                word = random.choice(word_list)
            
            cursor.execute("""
                INSERT INTO wordle_daily (word, language, date)
                VALUES (%s, %s, %s)
            """, (word, language, today))
            
            conn.commit()
            word_id = cursor.lastrowid
            
            logger.info(f"Created new Wordle word for {today} ({language}): {word}")
            return {'id': word_id, 'word': word, 'language': language}
        except Exception as e:
            logger.error(f"Database error in get_or_create_daily_word: {e}", exc_info=True)
            try:
                conn.rollback()
            except:
                pass  # Connection may already be closed or invalid
            return None
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error getting/creating daily Wordle word: {e}", exc_info=True)
        return None


async def get_user_attempts(db_helpers, user_id: int, word_id: int):
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
                SELECT guess, attempt_number
                FROM wordle_attempts
                WHERE user_id = %s AND word_id = %s
                ORDER BY attempt_number ASC
            """, (user_id, word_id))
            
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error getting user Wordle attempts: {e}", exc_info=True)
        return []


async def record_attempt(db_helpers, user_id: int, word_id: int, guess: str, attempt_num: int):
    """Record a Wordle guess attempt."""
    try:
        if not db_helpers.db_pool:
            return False
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO wordle_attempts (user_id, word_id, guess, attempt_number)
                VALUES (%s, %s, %s, %s)
            """, (user_id, word_id, guess, attempt_num))
            
            conn.commit()
            return True
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error recording Wordle attempt: {e}", exc_info=True)
        return False


async def update_user_stats(db_helpers, user_id: int, won: bool, attempts: int):
    """Update user's Wordle statistics."""
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
                SELECT * FROM wordle_stats WHERE user_id = %s
            """, (user_id,))
            stats = cursor.fetchone()
            
            if stats:
                # Parse guess distribution
                guess_dist = json.loads(stats.get('guess_distribution', '{}')) if stats.get('guess_distribution') else {}
                
                # Update distribution if won
                if won:
                    guess_dist[str(attempts)] = guess_dist.get(str(attempts), 0) + 1
                
                new_streak = stats['current_streak'] + 1 if won else 0
                new_best_streak = max(stats['best_streak'], new_streak)
                
                cursor.execute("""
                    UPDATE wordle_stats
                    SET total_games = total_games + 1,
                        total_wins = total_wins + %s,
                        current_streak = %s,
                        best_streak = %s,
                        guess_distribution = %s,
                        last_played = %s
                    WHERE user_id = %s
                """, (1 if won else 0, new_streak, new_best_streak, json.dumps(guess_dist), today, user_id))
            else:
                # Create new stats
                guess_dist = {str(attempts): 1} if won else {}
                
                cursor.execute("""
                    INSERT INTO wordle_stats 
                    (user_id, total_games, total_wins, current_streak, best_streak, guess_distribution, last_played)
                    VALUES (%s, 1, %s, %s, %s, %s, %s)
                """, (user_id, 1 if won else 0, 1 if won else 0, 1 if won else 0, json.dumps(guess_dist), today))
            
            conn.commit()
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error updating Wordle stats: {e}", exc_info=True)


async def get_user_stats(db_helpers, user_id: int):
    """Get user's Wordle statistics."""
    try:
        if not db_helpers.db_pool:
            return None
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return None
        
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT * FROM wordle_stats WHERE user_id = %s
            """, (user_id,))
            
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error getting Wordle stats: {e}", exc_info=True)
        return None


def check_guess(guess: str, correct_word: str):
    """
    Check a Wordle guess and return color-coded result.
    
    Returns:
        List of tuples (letter, status) where status is:
        - 'correct': letter in correct position (green)
        - 'present': letter in word but wrong position (yellow)
        - 'absent': letter not in word (gray)
    """
    result = []
    correct_letters = list(correct_word.lower())
    guess_letters = list(guess.lower())
    
    # Track used letters
    used_positions = set()
    
    # First pass: mark correct positions
    for i, letter in enumerate(guess_letters):
        if letter == correct_letters[i]:
            result.append((letter, 'correct'))
            used_positions.add(i)
        else:
            result.append((letter, None))  # Placeholder
    
    # Second pass: mark present/absent
    for i, (letter, status) in enumerate(result):
        if status == 'correct':
            continue
        
        # Check if letter exists in word at different position
        found = False
        for j, correct_letter in enumerate(correct_letters):
            if j not in used_positions and letter == correct_letter:
                result[i] = (letter, 'present')
                used_positions.add(j)
                found = True
                break
        
        if not found:
            result[i] = (letter, 'absent')
    
    return result


def create_game_embed(word_data: dict, attempts: list, user_stats: dict = None, is_game_over: bool = False, won: bool = False, theme_id=None):
    """Create the game embed with current progress and theme support."""
    # Import themes here to avoid circular import
    try:
        from modules import themes
        color = themes.get_theme_color(theme_id, 'success' if won else ('danger' if is_game_over else 'primary'))
    except (ImportError, ModuleNotFoundError, AttributeError) as e:
        color = discord.Color.green() if won else (discord.Color.red() if is_game_over else discord.Color.blue())
    
    embed = discord.Embed(
        title="🎮 Wordle - Tägliches Wortratespiel",
        description="Errate das 5-Buchstaben Wort in 6 Versuchen!",
        color=color
    )
    
    # Show attempts with color coding
    if attempts:
        attempts_text = ""
        for attempt in attempts:
            guess = attempt['guess']
            result = check_guess(guess, word_data['word'])
            
            # Create visual representation
            row = ""
            for letter, status in result:
                if status == 'correct':
                    row += f"🟩"  # Green
                elif status == 'present':
                    row += f"🟨"  # Yellow
                else:
                    row += f"⬜"  # Gray
            
            attempts_text += f"`{guess.upper()}` {row}\n"
        
        # Add remaining empty rows
        for i in range(6 - len(attempts)):
            attempts_text += "`.....` ⬜⬜⬜⬜⬜\n"
        
        embed.add_field(
            name=f"📝 Versuche ({len(attempts)}/6)",
            value=attempts_text,
            inline=False
        )
    else:
        empty_rows = "\n".join(["`.....` ⬜⬜⬜⬜⬜"] * 6)
        embed.add_field(
            name="📝 Versuche (0/6)",
            value=empty_rows,
            inline=False
        )
    
    # Add user stats if available
    if user_stats:
        total_games = user_stats.get('total_games', 0)
        total_wins = user_stats.get('total_wins', 0)
        current_streak = user_stats.get('current_streak', 0)
        best_streak = user_stats.get('best_streak', 0)
        
        win_rate = (total_wins / total_games * 100) if total_games > 0 else 0
        
        stats_text = f"Spiele: `{total_games}` | Gewonnen: `{total_wins}` ({win_rate:.1f}%)\n"
        stats_text += f"Streak: `{current_streak}` 🔥 | Best: `{best_streak}`"
        
        embed.add_field(name="📊 Deine Statistiken", value=stats_text, inline=False)
    
    embed.set_footer(text="💡 Grüne Quadrate = richtiger Buchstabe, richtige Position | Gelb = richtiger Buchstabe, falsche Position")
    
    return embed


def create_share_text(attempts: list, correct_word: str, won: bool):
    """Create shareable text for Wordle results with accurate colored squares."""
    share_lines = [f"Wordle {datetime.now(timezone.utc).date()} {len(attempts)}/6"]
    share_lines.append("")
    
    for attempt in attempts:
        guess = attempt.get('guess', '')
        result = check_guess(guess, correct_word)
        
        line = ""
        for letter, status in result:
            if status == 'correct':
                line += "🟩"
            elif status == 'present':
                line += "🟨"
            else:
                line += "⬜"
        share_lines.append(line)
    
    return "\n".join(share_lines)
