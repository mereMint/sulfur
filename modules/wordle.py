"""
Sulfur Bot - Wordle Game Module
Classic Wordle game with 5-letter word guessing.
"""

import discord
import random
import json
from datetime import datetime, timezone, timedelta
from modules.logger_utils import bot_logger as logger


# 5-letter German words for Wordle
WORDLE_WORDS = [
    'apfel', 'bauer', 'baum', 'brief', 'brot', 'brust', 'dach', 'dank', 'dampf',
    'decke', 'dienst', 'dorf', 'draht', 'dunkel', 'eisen', 'engel', 'ernte', 'essen',
    'fabrik', 'fahne', 'feld', 'feuer', 'fisch', 'flagge', 'fluss', 'forst', 'frost',
    'gabel', 'gans', 'garten', 'geist', 'geld', 'glas', 'glocke', 'glut', 'gold',
    'graben', 'gras', 'grenze', 'gruppe', 'gurt', 'haar', 'hafen', 'hagel', 'haken',
    'halle', 'hals', 'hammer', 'handel', 'haus', 'heer', 'helm', 'hemd', 'herd',
    'herr', 'himmel', 'hirte', 'hitze', 'holz', 'honig', 'horn', 'hotel', 'huhn',
    'hund', 'insel', 'jagd', 'kabel', 'kamm', 'kampf', 'kanal', 'kanne', 'karte',
    'kasse', 'keller', 'kern', 'kette', 'kind', 'kirche', 'klang', 'klasse', 'kleid',
    'klein', 'klippe', 'knochen', 'knopf', 'kohl', 'korb', 'kraft', 'kranz', 'kreis',
    'kreuz', 'krieg', 'krone', 'kugel', 'kunst', 'kurs', 'laden', 'lampe', 'land',
    'lanze', 'laub', 'laut', 'leder', 'leer', 'leib', 'leim', 'leine', 'leiter',
    'licht', 'lied', 'lippe', 'liste', 'loch', 'lohn', 'luft', 'lust', 'macht',
    'magd', 'mahl', 'maler', 'mann', 'mantel', 'markt', 'maske', 'masse', 'mauer',
    'meer', 'mehl', 'meister', 'menge', 'mensch', 'messer', 'metall', 'milch', 'mond',
    'moos', 'motor', 'mund', 'musik', 'mutter', 'nabel', 'nacht', 'nadel', 'nagel',
    'name', 'narbe', 'nase', 'nebel', 'nest', 'netz', 'nord', 'ofen', 'orden',
    'palast', 'papier', 'park', 'pfad', 'pfeife', 'pfeil', 'pferd', 'pflanze', 'pflug',
    'platz', 'pulver', 'punkt', 'quelle', 'rabe', 'rad', 'rahmen', 'rand', 'rasen',
    'rasse', 'rauch', 'raum', 'rebe', 'recht', 'regal', 'regen', 'reich', 'reihe',
    'reise', 'reiter', 'rest', 'riese', 'rind', 'ring', 'ritter', 'rock', 'rohr',
    'rose', 'rost', 'rucken', 'ruhm', 'saal', 'saat', 'sache', 'saft', 'sage',
    'salz', 'samen', 'samt', 'sand', 'sarg', 'satz', 'saum', 'schacht', 'schale',
    'schall', 'scham', 'schanze', 'schar', 'schatz', 'schein', 'schenkel', 'schicht',
    'schiff', 'schild', 'schlaf', 'schlag', 'schlange', 'schloss', 'schlot', 'schlucht',
    'schluss', 'schmerz', 'schnee', 'scholle', 'schopf', 'schoss', 'schrank', 'schrift',
    'schritt', 'schuh', 'schuld', 'schule', 'schuppe', 'schuss', 'schutz', 'schwamm',
    'schwan', 'schwanz', 'schwarz', 'schwein', 'schwert', 'see', 'segel', 'segen',
    'seide', 'seife', 'seil', 'seite', 'sense', 'sieb', 'siegel', 'sieg', 'sold',
    'sonne', 'sorge', 'spalt', 'spange', 'spanne', 'spatz', 'speck', 'speise', 'spiegel',
    'spiel', 'spinne', 'spitze', 'sporn', 'sprache', 'sprung', 'spur', 'staat', 'stab',
    'stadt', 'stahl', 'stamm', 'stand', 'stange', 'stapel', 'staub', 'steg', 'stein',
    'stelle', 'stern', 'steuer', 'stich', 'stiefel', 'stier', 'stimme', 'stirn', 'stock',
    'stoff', 'stolz', 'strand', 'strasse', 'strauch', 'streit', 'strich', 'strick', 'strom',
    'stube', 'stuck', 'stufe', 'stuhl', 'stunde', 'sturm', 'stutz', 'sucht', 'sumpf',
    'tanz', 'tasche', 'tafel', 'takt', 'tanne', 'tasse', 'taube', 'tausch', 'teich',
    'teil', 'teller', 'tempel', 'teppich', 'thron', 'tier', 'tinte', 'tisch', 'titel',
    'tochter', 'topf', 'torf', 'tracht', 'trank', 'traube', 'traum', 'treib', 'treue',
    'trieb', 'tritt', 'trog', 'tropf', 'trost', 'truhe', 'trupp', 'tuch', 'tugend',
    'turm', 'tür', 'ufer', 'ungluck', 'unrecht', 'unruh', 'vater', 'veilchen', 'vieh',
    'vogel', 'volk', 'wabe', 'wache', 'wachs', 'waffe', 'wagen', 'wahl', 'wahn',
    'wald', 'wall', 'wand', 'wange', 'wanne', 'ware', 'wart', 'wasser', 'watte',
    'weber', 'wecken', 'wehr', 'weib', 'weide', 'weihe', 'wein', 'weise', 'weizen',
    'welle', 'welt', 'werk', 'wert', 'wesen', 'weste', 'wetter', 'wicht', 'wiege',
    'wiese', 'wille', 'wind', 'winkel', 'winter', 'wipfel', 'wirbel', 'wirt', 'wisch',
    'wissen', 'witwe', 'witz', 'woge', 'wohl', 'wolf', 'wolke', 'wolle', 'wonne',
    'wort', 'wucht', 'wunde', 'wunsch', 'wurf', 'wurm', 'wurzel', 'wust', 'wut',
    'zahl', 'zahn', 'zange', 'zank', 'zaum', 'zaun', 'zeche', 'zehe', 'zeichen',
    'zeiger', 'zeile', 'zeit', 'zelt', 'ziege', 'ziegel', 'ziel', 'zierde', 'ziffer',
    'zins', 'zipfel', 'zirkel', 'zither', 'zoll', 'zopf', 'zorn', 'zuber', 'zucht',
    'zucker', 'zug', 'zunge', 'zwang', 'zweck', 'zweig', 'zwerg', 'zwilling',
    'zwirn'
]


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
                    date DATE NOT NULL UNIQUE,
                    INDEX idx_date (date)
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


async def get_or_create_daily_word(db_helpers):
    """Get or create today's Wordle word."""
    try:
        if not db_helpers.db_pool:
            logger.error("Database pool not available")
            return None
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            logger.error("Could not get database connection")
            return None
        
        cursor = conn.cursor(dictionary=True)
        try:
            today = datetime.now(timezone.utc).date()
            
            # Check if today's word exists
            cursor.execute("""
                SELECT id, word FROM wordle_daily
                WHERE date = %s
            """, (today,))
            result = cursor.fetchone()
            
            if result:
                return result
            
            # Create new daily word
            word = random.choice(WORDLE_WORDS)
            
            cursor.execute("""
                INSERT INTO wordle_daily (word, date)
                VALUES (%s, %s)
            """, (word, today))
            
            conn.commit()
            word_id = cursor.lastrowid
            
            return {'id': word_id, 'word': word}
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
