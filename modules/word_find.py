"""
Sulfur Bot - Word Find Game Module
Daily word guessing game with proximity-based hints.
"""

import discord
import random
import asyncio
from datetime import datetime, timezone, timedelta
from modules.logger_utils import bot_logger as logger


# Word lists for different difficulty levels
WORD_LISTS = {
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
            # Table for daily word
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS word_find_daily (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    word VARCHAR(100) NOT NULL,
                    difficulty VARCHAR(20) NOT NULL,
                    date DATE NOT NULL UNIQUE,
                    INDEX idx_date (date)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Table for premium games (separate from daily)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS word_find_premium_games (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    word VARCHAR(100) NOT NULL,
                    difficulty VARCHAR(20) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed BOOLEAN DEFAULT FALSE,
                    won BOOLEAN DEFAULT FALSE,
                    INDEX idx_user_created (user_id, created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Table for user attempts
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
            
            # Table for user stats
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS word_find_stats (
                    user_id BIGINT PRIMARY KEY,
                    total_games INT DEFAULT 0,
                    total_wins INT DEFAULT 0,
                    current_streak INT DEFAULT 0,
                    best_streak INT DEFAULT 0,
                    total_attempts INT DEFAULT 0,
                    last_played DATE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            conn.commit()
            logger.info("Word Find tables initialized")
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error initializing word find tables: {e}", exc_info=True)


def calculate_word_similarity(word1: str, word2: str) -> float:
    """
    Calculate similarity between two words using multiple metrics.
    Returns a score from 0 to 100.
    """
    word1 = word1.lower().strip()
    word2 = word2.lower().strip()
    
    if word1 == word2:
        return 100.0
    
    # Length similarity
    max_len = max(len(word1), len(word2))
    min_len = min(len(word1), len(word2))
    length_score = (min_len / max_len) * 25 if max_len > 0 else 0
    
    # Character overlap
    common_chars = sum(min(word1.count(c), word2.count(c)) for c in set(word1 + word2))
    char_score = (common_chars / max(len(word1), len(word2))) * 25
    
    # Levenshtein distance (simplified)
    distance = levenshtein_distance(word1, word2)
    max_distance = max(len(word1), len(word2))
    distance_score = ((max_distance - distance) / max_distance) * 30 if max_distance > 0 else 0
    
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
    
    affix_score = ((prefix_len + suffix_len) / max_len) * 20 if max_len > 0 else 0
    
    total_score = length_score + char_score + distance_score + affix_score
    return min(100.0, total_score)


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


async def get_or_create_daily_word(db_helpers):
    """Get today's word or create a new one."""
    try:
        if not db_helpers.db_pool:
            return None
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return None
        
        cursor = conn.cursor(dictionary=True)
        try:
            today = datetime.now(timezone.utc).date()
            
            # Check if today's word exists
            cursor.execute("""
                SELECT id, word, difficulty FROM word_find_daily
                WHERE date = %s
            """, (today,))
            result = cursor.fetchone()
            
            if result:
                return result
            
            # Create new daily word
            # Choose difficulty based on day of week (harder on weekends)
            weekday = datetime.now(timezone.utc).weekday()
            if weekday >= 5:  # Saturday, Sunday
                difficulty = 'hard'
            elif weekday >= 3:  # Thursday, Friday
                difficulty = 'medium'
            else:
                difficulty = 'easy'
            
            word = random.choice(WORD_LISTS[difficulty])
            
            cursor.execute("""
                INSERT INTO word_find_daily (word, difficulty, date)
                VALUES (%s, %s, %s)
            """, (word, difficulty, today))
            
            conn.commit()
            word_id = cursor.lastrowid
            
            return {'id': word_id, 'word': word, 'difficulty': difficulty}
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error getting/creating daily word: {e}", exc_info=True)
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
                SELECT guess, similarity_score, attempt_number
                FROM word_find_attempts
                WHERE user_id = %s AND word_id = %s
                ORDER BY similarity_score DESC
            """, (user_id, word_id))
            
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error getting user attempts: {e}", exc_info=True)
        return []


async def record_attempt(db_helpers, user_id: int, word_id: int, guess: str, similarity: float, attempt_num: int):
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
                INSERT INTO word_find_attempts (user_id, word_id, guess, similarity_score, attempt_number)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, word_id, guess, similarity, attempt_num))
            
            conn.commit()
            return True
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error recording attempt: {e}", exc_info=True)
        return False


async def update_user_stats(db_helpers, user_id: int, won: bool, attempts: int):
    """Update user's Word Find statistics."""
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
            
            if stats:
                # Update existing stats
                new_streak = stats['current_streak'] + 1 if won else 0
                new_best_streak = max(stats['best_streak'], new_streak)
                
                cursor.execute("""
                    UPDATE word_find_stats
                    SET total_games = total_games + 1,
                        total_wins = total_wins + %s,
                        current_streak = %s,
                        best_streak = %s,
                        total_attempts = total_attempts + %s,
                        last_played = %s
                    WHERE user_id = %s
                """, (1 if won else 0, new_streak, new_best_streak, attempts, today, user_id))
            else:
                # Create new stats
                cursor.execute("""
                    INSERT INTO word_find_stats (user_id, total_games, total_wins, current_streak, best_streak, total_attempts, last_played)
                    VALUES (%s, 1, %s, %s, %s, %s, %s)
                """, (user_id, 1 if won else 0, 1 if won else 0, 1 if won else 0, attempts, today))
            
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


async def create_premium_game(db_helpers, user_id: int):
    """Create a new premium game for a user."""
    try:
        if not db_helpers.db_pool:
            return None
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return None
        
        cursor = conn.cursor(dictionary=True)
        try:
            # Choose random difficulty and word
            difficulty = random.choice(['easy', 'medium', 'hard'])
            word = random.choice(WORD_LISTS[difficulty])
            
            cursor.execute("""
                INSERT INTO word_find_premium_games (user_id, word, difficulty)
                VALUES (%s, %s, %s)
            """, (user_id, word, difficulty))
            
            conn.commit()
            game_id = cursor.lastrowid
            
            return {'id': game_id, 'word': word, 'difficulty': difficulty, 'type': 'premium'}
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error creating premium game: {e}", exc_info=True)
        return None


async def get_user_attempts_by_type(db_helpers, user_id: int, word_id: int, game_type: str):
    """Get user's attempts for a specific game (daily or premium)."""
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
                ORDER BY similarity_score DESC
            """, (user_id, word_id, game_type))
            
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error getting user attempts by type: {e}", exc_info=True)
        return []


async def record_attempt_with_type(db_helpers, user_id: int, word_id: int, guess: str, similarity: float, attempt_num: int, game_type: str):
    """Record a guess attempt with game type."""
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
        logger.error(f"Error recording attempt with type: {e}", exc_info=True)
        return False


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


def create_game_embed(word_data: dict, attempts: list, max_attempts: int, user_stats: dict = None, game_type: str = 'daily'):
    """Create the game embed with current progress."""
    difficulty_colors = {
        'easy': discord.Color.green(),
        'medium': discord.Color.orange(),
        'hard': discord.Color.red()
    }
    
    difficulty = word_data.get('difficulty', 'medium')
    color = difficulty_colors.get(difficulty, discord.Color.blue())
    
    title = "🔍 Word Find - Tägliches Wortratespiel" if game_type == 'daily' else "🔍 Word Find - Premium Spiel"
    
    embed = discord.Embed(
        title=title,
        description=f"Errate das Wort! Du hast {max_attempts} Versuche.\n"
                   f"Schwierigkeit: **{difficulty.upper()}**",
        color=color
    )
    
    # Show attempts with proximity scores
    if attempts:
        attempts_text = ""
        sorted_attempts = sorted(attempts, key=lambda x: x['similarity_score'], reverse=True)
        
        for i, attempt in enumerate(sorted_attempts[:10], 1):  # Show top 10
            score = attempt['similarity_score']
            guess = attempt['guess']
            
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
            
            attempts_text += f"`#{attempt['attempt_number']:02d}` **{guess}** - {score:.1f}% {temp}\n{bar}\n\n"
        
        embed.add_field(
            name=f"📝 Deine Versuche ({len(attempts)}/{max_attempts})",
            value=attempts_text if attempts_text else "Noch keine Versuche",
            inline=False
        )
    else:
        embed.add_field(
            name=f"📝 Versuche ({len(attempts)}/{max_attempts})",
            value="Noch keine Versuche. Rate ein Wort!",
            inline=False
        )
    
    # Add user stats if available
    if user_stats:
        win_rate = (user_stats['total_wins'] / user_stats['total_games'] * 100) if user_stats['total_games'] > 0 else 0
        avg_attempts = (user_stats['total_attempts'] / user_stats['total_wins']) if user_stats['total_wins'] > 0 else 0
        
        stats_text = f"Spiele: `{user_stats['total_games']}` | Gewonnen: `{user_stats['total_wins']}` ({win_rate:.1f}%)\n"
        stats_text += f"Streak: `{user_stats['current_streak']}` 🔥 | Best: `{user_stats['best_streak']}`\n"
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
