"""
Sulfur Bot - Anidle Game Module
An anime guessing game similar to Wordle.
Players guess an anime and receive feedback on how their guess compares to the target.
"""

# Standard library imports
import asyncio
import json
import random
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any

# Third-party imports
import aiohttp
import discord

# Local imports
from modules.logger_utils import bot_logger as logger

# Jikan API (MyAnimeList unofficial API) - free, no auth required
JIKAN_API_BASE = "https://api.jikan.moe/v4"

# Rate limiting for Jikan API (3 requests per second, but we use 1 per second for safety)
_api_rate_limiter = asyncio.Lock()
_last_api_call: float = 0.0
API_RATE_LIMIT_SECONDS = 1.0  # Minimum seconds between API calls

# Retry configuration
MAX_API_RETRIES = 3
RETRY_BACKOFF_BASE = 2.0  # Exponential backoff base in seconds

# Cache for daily anime
_daily_anime_cache: Dict[str, dict] = {}
_last_cache_date: Optional[str] = None

# Cache for anime lookups (to reduce API calls)
_anime_cache: Dict[int, dict] = {}  # {mal_id: anime_data}
_anime_cache_ttl: Dict[int, float] = {}  # {mal_id: timestamp}
ANIME_CACHE_TTL = 3600  # Cache anime data for 1 hour

# Active games per user
active_anidle_games: Dict[int, 'AnidleGame'] = {}

# Daily play tracking
daily_plays: Dict[str, Dict[int, int]] = {}  # {date_str: {user_id: play_count}}


async def _rate_limited_api_call(url: str, params: dict = None, timeout: int = 15) -> Optional[dict]:
    """
    Make a rate-limited API call to Jikan with retry logic.
    
    Args:
        url: API endpoint URL
        params: Query parameters
        timeout: Request timeout in seconds
    
    Returns:
        API response data or None on failure
    """
    global _last_api_call
    
    for attempt in range(MAX_API_RETRIES):
        try:
            async with _api_rate_limiter:
                # Ensure minimum time between API calls
                now = time.time()
                time_since_last = now - _last_api_call
                if time_since_last < API_RATE_LIMIT_SECONDS:
                    await asyncio.sleep(API_RATE_LIMIT_SECONDS - time_since_last)
                
                _last_api_call = time.time()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    elif response.status == 429:
                        # Rate limited - wait longer before retry
                        retry_after = int(response.headers.get('Retry-After', 5))
                        logger.warning(f"Jikan API rate limited, waiting {retry_after}s (attempt {attempt + 1}/{MAX_API_RETRIES})")
                        await asyncio.sleep(retry_after)
                        continue
                    elif response.status >= 500:
                        # Server error - retry with backoff
                        wait_time = RETRY_BACKOFF_BASE ** attempt
                        logger.warning(f"Jikan API server error {response.status}, retrying in {wait_time}s (attempt {attempt + 1}/{MAX_API_RETRIES})")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.warning(f"Jikan API returned status {response.status} for {url}")
                        return None
                        
        except asyncio.TimeoutError:
            wait_time = RETRY_BACKOFF_BASE ** attempt
            logger.warning(f"Jikan API timeout, retrying in {wait_time}s (attempt {attempt + 1}/{MAX_API_RETRIES})")
            await asyncio.sleep(wait_time)
        except aiohttp.ClientError as e:
            wait_time = RETRY_BACKOFF_BASE ** attempt
            logger.warning(f"Jikan API client error: {e}, retrying in {wait_time}s (attempt {attempt + 1}/{MAX_API_RETRIES})")
            await asyncio.sleep(wait_time)
        except Exception as e:
            logger.error(f"Unexpected error calling Jikan API: {e}")
            return None
    
    logger.error(f"Jikan API call failed after {MAX_API_RETRIES} attempts: {url}")
    return None


async def initialize_anidle_tables(db_helpers):
    """Initialize the Anidle game tables in the database."""
    try:
        if not db_helpers.db_pool:
            logger.error("Database pool not available for Anidle initialization")
            return
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            logger.error("Could not get database connection for Anidle")
            return
        
        cursor = conn.cursor()
        try:
            # Table for daily anime
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS anidle_daily (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    mal_id INT NOT NULL,
                    anime_data JSON NOT NULL,
                    date DATE NOT NULL,
                    UNIQUE KEY unique_date (date),
                    INDEX idx_date (date),
                    INDEX idx_mal_id (mal_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Table for user games/stats
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS anidle_games (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    mal_id INT NOT NULL,
                    game_type ENUM('daily', 'premium') DEFAULT 'daily',
                    guesses INT DEFAULT 0,
                    won BOOLEAN DEFAULT FALSE,
                    completed BOOLEAN DEFAULT FALSE,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP NULL,
                    INDEX idx_user_id (user_id),
                    INDEX idx_date (started_at),
                    INDEX idx_user_game (user_id, game_type, started_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            conn.commit()
            logger.info("Anidle tables initialized successfully")
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error initializing Anidle tables: {e}", exc_info=True)


async def save_daily_anime_to_db(db_helpers, anime: dict) -> bool:
    """Save today's daily anime to the database."""
    try:
        if not db_helpers.db_pool:
            return False
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        try:
            today = datetime.now(timezone.utc).date()
            mal_id = anime.get('mal_id')
            anime_json = json.dumps(anime, ensure_ascii=False)
            
            cursor.execute("""
                INSERT INTO anidle_daily (mal_id, anime_data, date)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    mal_id = VALUES(mal_id),
                    anime_data = VALUES(anime_data)
            """, (mal_id, anime_json, today))
            
            conn.commit()
            logger.info(f"Saved daily anime to database: {anime.get('title')} (MAL ID: {mal_id})")
            return True
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error saving daily anime to database: {e}", exc_info=True)
        return False


async def get_daily_anime_from_db(db_helpers) -> Optional[dict]:
    """Get today's daily anime from the database."""
    try:
        if not db_helpers.db_pool:
            return None
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return None
        
        cursor = conn.cursor(dictionary=True)
        try:
            today = datetime.now(timezone.utc).date()
            
            cursor.execute("""
                SELECT anime_data FROM anidle_daily WHERE date = %s
            """, (today,))
            
            row = cursor.fetchone()
            if row and row.get('anime_data'):
                anime_data = row['anime_data']
                if isinstance(anime_data, str):
                    return json.loads(anime_data)
                return anime_data
            
            return None
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error getting daily anime from database: {e}", exc_info=True)
        return None


async def record_anidle_game(db_helpers, user_id: int, mal_id: int, guesses: int, won: bool, game_type: str = 'daily'):
    """Record a completed Anidle game to the database."""
    try:
        if not db_helpers.db_pool:
            return False
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO anidle_games (user_id, mal_id, game_type, guesses, won, completed, completed_at)
                VALUES (%s, %s, %s, %s, %s, TRUE, NOW())
            """, (user_id, mal_id, game_type, guesses, won))
            
            conn.commit()
            logger.info(f"Recorded Anidle game for user {user_id}: {'won' if won else 'lost'} in {guesses} guesses")
            return True
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error recording Anidle game: {e}", exc_info=True)
        return False


class AnidleGame:
    """Handles an Anidle game instance."""
    
    MAX_GUESSES = 20
    HINT_COVER_AT = 10
    HINT_SYNOPSIS_AT = 15
    HINT_CHARACTER_AT = 20
    
    def __init__(self, player_id: int, target_anime: dict, is_premium: bool = False):
        self.player_id = player_id
        self.target_anime = target_anime
        self.is_premium = is_premium
        self.guesses: List[dict] = []
        self.is_active = True
        self.won = False
        self.started_at = datetime.now(timezone.utc)
        self.hints_shown = set()  # Track which hints have been shown
    
    @property
    def attempts(self) -> int:
        return len(self.guesses)
    
    @property
    def remaining_guesses(self) -> int:
        return self.MAX_GUESSES - self.attempts
    
    def get_target_info(self) -> dict:
        """Get relevant target anime information for comparison."""
        return {
            'title': self.target_anime.get('title', 'Unknown'),
            'title_english': self.target_anime.get('title_english') or self.target_anime.get('title', 'Unknown'),
            'year': self.target_anime.get('year') or (self.target_anime.get('aired', {}).get('prop', {}).get('from', {}).get('year')),
            'genres': [g.get('name', '') for g in self.target_anime.get('genres', [])],
            'themes': [t.get('name', '') for t in self.target_anime.get('themes', [])],
            'studios': [s.get('name', '') for s in self.target_anime.get('studios', [])],
            'source': self.target_anime.get('source', 'Unknown'),
            'score': self.target_anime.get('score', 0) or 0,
            'mal_id': self.target_anime.get('mal_id'),
            'image_url': self.target_anime.get('images', {}).get('jpg', {}).get('large_image_url') or 
                         self.target_anime.get('images', {}).get('jpg', {}).get('image_url'),
            'synopsis': self.target_anime.get('synopsis', 'No synopsis available.'),
        }
    
    def compare_guess(self, guessed_anime: dict) -> dict:
        """Compare guessed anime with target and return comparison results."""
        target = self.get_target_info()
        guess_info = {
            'title': guessed_anime.get('title', 'Unknown'),
            'title_english': guessed_anime.get('title_english') or guessed_anime.get('title', 'Unknown'),
            'year': guessed_anime.get('year') or (guessed_anime.get('aired', {}).get('prop', {}).get('from', {}).get('year')),
            'genres': [g.get('name', '') for g in guessed_anime.get('genres', [])],
            'themes': [t.get('name', '') for t in guessed_anime.get('themes', [])],
            'studios': [s.get('name', '') for s in guessed_anime.get('studios', [])],
            'source': guessed_anime.get('source', 'Unknown'),
            'score': guessed_anime.get('score', 0) or 0,
            'mal_id': guessed_anime.get('mal_id'),
            'image_url': guessed_anime.get('images', {}).get('jpg', {}).get('image_url'),
        }
        
        # Compare each field
        comparison = {
            'title': guess_info['title'],
            'title_english': guess_info['title_english'],
            'mal_id': guess_info['mal_id'],
            'image_url': guess_info['image_url'],
            'is_correct': guess_info['mal_id'] == target['mal_id'],
            'year': {
                'value': guess_info['year'],
                'status': 'correct' if guess_info['year'] == target['year'] else 
                          ('higher' if (guess_info['year'] or 0) < (target['year'] or 0) else 'lower')
            },
            'genres': {
                'value': guess_info['genres'],
                'matches': [g for g in guess_info['genres'] if g in target['genres']],
                'status': 'correct' if set(guess_info['genres']) == set(target['genres']) else
                          ('partial' if any(g in target['genres'] for g in guess_info['genres']) else 'wrong')
            },
            'themes': {
                'value': guess_info['themes'],
                'matches': [t for t in guess_info['themes'] if t in target['themes']],
                'status': 'correct' if set(guess_info['themes']) == set(target['themes']) else
                          ('partial' if any(t in target['themes'] for t in guess_info['themes']) else 'wrong')
            },
            'studios': {
                'value': guess_info['studios'],
                'matches': [s for s in guess_info['studios'] if s in target['studios']],
                'status': 'correct' if set(guess_info['studios']) == set(target['studios']) else
                          ('partial' if any(s in target['studios'] for s in guess_info['studios']) else 'wrong')
            },
            'source': {
                'value': guess_info['source'],
                'status': 'correct' if guess_info['source'] == target['source'] else 'wrong'
            },
            'score': {
                'value': guess_info['score'],
                'status': 'correct' if abs((guess_info['score'] or 0) - (target['score'] or 0)) < 0.1 else
                          ('higher' if (guess_info['score'] or 0) < (target['score'] or 0) else 'lower')
            }
        }
        
        return comparison
    
    def make_guess(self, guessed_anime: dict) -> dict:
        """Process a guess and return results."""
        if not self.is_active:
            return {'error': 'Game is not active'}
        
        if self.attempts >= self.MAX_GUESSES:
            self.is_active = False
            return {'error': 'No more guesses remaining'}
        
        comparison = self.compare_guess(guessed_anime)
        self.guesses.append(comparison)
        
        if comparison['is_correct']:
            self.won = True
            self.is_active = False
        elif self.attempts >= self.MAX_GUESSES:
            self.is_active = False
        
        return comparison
    
    def should_show_hint(self, hint_type: str) -> bool:
        """Check if a hint should be shown based on attempts."""
        if hint_type in self.hints_shown:
            return False
        
        if hint_type == 'cover' and self.attempts >= self.HINT_COVER_AT:
            self.hints_shown.add('cover')
            return True
        elif hint_type == 'synopsis' and self.attempts >= self.HINT_SYNOPSIS_AT:
            self.hints_shown.add('synopsis')
            return True
        elif hint_type == 'character' and self.attempts >= self.HINT_CHARACTER_AT:
            self.hints_shown.add('character')
            return True
        
        return False
    
    def create_embed(self, last_guess: Optional[dict] = None, embed_color: int = 0x00ff41) -> discord.Embed:
        """Create an embed showing the current game state."""
        embed = discord.Embed(
            title="Anidle - Anime Guessing Game",
            description=f"Guess the anime! Attempt {self.attempts}/{self.MAX_GUESSES}",
            color=embed_color
        )
        
        if last_guess:
            # Show last guess results
            year_emoji = self._get_status_emoji(last_guess['year']['status'])
            genre_emoji = self._get_status_emoji(last_guess['genres']['status'])
            theme_emoji = self._get_status_emoji(last_guess['themes']['status'])
            studio_emoji = self._get_status_emoji(last_guess['studios']['status'])
            source_emoji = self._get_status_emoji(last_guess['source']['status'])
            score_emoji = self._get_status_emoji(last_guess['score']['status'])
            
            guess_text = f"**{last_guess['title']}**\n"
            guess_text += f"{year_emoji} Year: {last_guess['year']['value'] or '?'}"
            if last_guess['year']['status'] != 'correct':
                guess_text += f" (Target is {'higher' if last_guess['year']['status'] == 'higher' else 'lower'})"
            guess_text += f"\n{genre_emoji} Genres: {', '.join(last_guess['genres']['value'][:3]) or 'None'}"
            if last_guess['genres']['matches']:
                guess_text += f" (Matches: {', '.join(last_guess['genres']['matches'])})"
            guess_text += f"\n{theme_emoji} Themes: {', '.join(last_guess['themes']['value'][:3]) or 'None'}"
            guess_text += f"\n{studio_emoji} Studio: {', '.join(last_guess['studios']['value']) or 'Unknown'}"
            guess_text += f"\n{source_emoji} Source: {last_guess['source']['value']}"
            guess_text += f"\n{score_emoji} Score: {last_guess['score']['value'] or '?'}"
            
            embed.add_field(name="Last Guess", value=guess_text, inline=False)
            
            if last_guess.get('image_url'):
                embed.set_thumbnail(url=last_guess['image_url'])
        
        # Show hints based on progress
        hints = []
        if 'cover' in self.hints_shown:
            hints.append("Cover image available (blurred)")
        if 'synopsis' in self.hints_shown:
            target = self.get_target_info()
            synopsis = target['synopsis'][:200] + '...' if len(target['synopsis']) > 200 else target['synopsis']
            hints.append(f"Synopsis: {synopsis}")
        if 'character' in self.hints_shown:
            hints.append("Main character hint available")
        
        if hints:
            embed.add_field(name="Hints", value="\n".join(hints), inline=False)
        else:
            next_hint = ""
            if self.attempts < self.HINT_COVER_AT:
                next_hint = f"Cover hint at {self.HINT_COVER_AT} guesses"
            elif self.attempts < self.HINT_SYNOPSIS_AT:
                next_hint = f"Synopsis hint at {self.HINT_SYNOPSIS_AT} guesses"
            elif self.attempts < self.HINT_CHARACTER_AT:
                next_hint = f"Character hint at {self.HINT_CHARACTER_AT} guesses"
            if next_hint:
                embed.add_field(name="Next Hint", value=next_hint, inline=False)
        
        # Status
        if self.won:
            embed.color = 0x00ff00
            embed.add_field(name="Result", value=f"Correct! You got it in {self.attempts} attempts!", inline=False)
            target = self.get_target_info()
            if target['image_url']:
                embed.set_image(url=target['image_url'])
        elif not self.is_active:
            embed.color = 0xff0000
            target = self.get_target_info()
            embed.add_field(name="Result", value=f"Game Over! The anime was: **{target['title']}**", inline=False)
            if target['image_url']:
                embed.set_image(url=target['image_url'])
        
        embed.set_footer(text="Use /anidle guess <anime name> to guess | /anidle paytable for hints info")
        
        return embed
    
    def _get_status_emoji(self, status: str) -> str:
        """Get emoji for status. Using text-based indicators."""
        if status == 'correct':
            return '[OK]'
        elif status == 'partial':
            return '[~]'
        elif status == 'higher':
            return '[UP]'
        elif status == 'lower':
            return '[DN]'
        else:
            return '[X]'


async def search_anime(query: str) -> Optional[List[dict]]:
    """Search for anime by name using Jikan API with rate limiting."""
    try:
        url = f"{JIKAN_API_BASE}/anime"
        params = {'q': query, 'limit': 5, 'sfw': 'true'}
        data = await _rate_limited_api_call(url, params)
        if data:
            return data.get('data', [])
        return None
    except Exception as e:
        logger.error(f"Error searching anime: {e}")
        return None


async def get_anime_by_id(mal_id: int) -> Optional[dict]:
    """Get full anime details by MAL ID with caching and rate limiting."""
    try:
        # Check cache first
        if mal_id in _anime_cache:
            cache_time = _anime_cache_ttl.get(mal_id, 0)
            if time.time() - cache_time < ANIME_CACHE_TTL:
                logger.debug(f"Returning cached anime data for MAL ID {mal_id}")
                return _anime_cache[mal_id]
        
        url = f"{JIKAN_API_BASE}/anime/{mal_id}/full"
        data = await _rate_limited_api_call(url)
        if data:
            anime = data.get('data')
            if anime:
                # Cache the result
                _anime_cache[mal_id] = anime
                _anime_cache_ttl[mal_id] = time.time()
            return anime
        return None
    except Exception as e:
        logger.error(f"Error getting anime {mal_id}: {e}")
        return None


async def get_random_anime() -> Optional[dict]:
    """
    Get a random anime for the daily game with rate limiting.
    
    Filters:
    - Only first seasons (no sequels like "Season 2", "Part 2", etc.)
    - Must have a score (to ensure quality)
    - Prefers anime with good popularity
    """
    try:
        # Sequel indicators to filter out
        sequel_patterns = [
            'season 2', 'season 3', 'season 4', 'season 5', 'season 6',
            's2', 's3', 's4', 's5', 's6',
            'part 2', 'part 3', 'part 4', 'part ii', 'part iii', 'part iv',
            '2nd season', '3rd season', '4th season', '5th season',
            'second season', 'third season', 'fourth season', 'fifth season',
            'final season', 'the final', 
            'cour 2', 'cour 3',
            ': ii', ': iii', ': iv', ' ii', ' iii', ' iv',
            '2nd cour', '3rd cour',
            'shippuden',  # Naruto sequel
            'brotherhood',  # FMA sequel (though it's also a remake)
            'z',  # Dragon Ball Z (sequel indicator when at end of title)
            'gt', 'super',  # Dragon Ball sequels
            'next generations',  # Boruto
            'continue', 'continuation',
        ]
        
        def is_first_season(anime_data: dict) -> bool:
            """Check if anime is likely a first season."""
            title = anime_data.get('title', '').lower()
            title_english = (anime_data.get('title_english') or '').lower()
            
            # Check main title and English title for sequel patterns
            for pattern in sequel_patterns:
                if pattern in title or pattern in title_english:
                    # Special case: "z" only counts if at end of title or before colon
                    if pattern == 'z':
                        if title.endswith(' z') or ' z:' in title or ' z -' in title:
                            return False
                    elif pattern in ['gt', 'super']:
                        # Only count if it's Dragon Ball related
                        if 'dragon ball' in title:
                            return False
                    else:
                        return False
            
            # Check if it's explicitly marked as a sequel in the API data
            # Jikan provides 'relations' which can indicate if it's a sequel
            # For simplicity, we'll rely on title patterns
            
            return True
        
        # Strategy: Get anime from multiple random pages to get variety
        # Use different search approaches for diversity
        strategies = [
            # Get popular anime (broader range)
            {'url': f"{JIKAN_API_BASE}/top/anime", 'params': {'limit': 25, 'page': random.randint(1, 10), 'filter': 'bypopularity'}},
            # Get by score
            {'url': f"{JIKAN_API_BASE}/top/anime", 'params': {'limit': 25, 'page': random.randint(1, 8), 'filter': 'score'}},
            # Get airing anime that completed
            {'url': f"{JIKAN_API_BASE}/anime", 'params': {'limit': 25, 'page': random.randint(1, 20), 'status': 'complete', 'min_score': 6, 'order_by': 'score', 'sort': 'desc'}},
            # Search with random letter + min score
            {'url': f"{JIKAN_API_BASE}/anime", 'params': {'limit': 25, 'letter': random.choice('abcdefghijklmnopqrstuvwxyz'), 'min_score': 6, 'order_by': 'popularity'}},
        ]
        
        # Try up to 3 strategies to find a good anime
        random.shuffle(strategies)
        
        for strategy in strategies[:3]:
            data = await _rate_limited_api_call(strategy['url'], strategy['params'])
            if not data:
                continue
                
            anime_list = data.get('data', [])
            if not anime_list:
                continue
            
            # Filter for first seasons only
            first_season_anime = [a for a in anime_list if is_first_season(a)]
            
            if first_season_anime:
                # Pick a random one from filtered list
                chosen = random.choice(first_season_anime)
                logger.info(f"Selected anime: {chosen.get('title')} (MAL ID: {chosen.get('mal_id')})")
                
                # Get full details (also rate limited)
                full_anime = await get_anime_by_id(chosen['mal_id'])
                if full_anime:
                    return full_anime
        
        # Fallback: If all strategies fail, try a simple top anime search
        logger.warning("All random strategies failed, falling back to top anime")
        url = f"{JIKAN_API_BASE}/top/anime"
        params = {'limit': 50, 'filter': 'bypopularity'}
        data = await _rate_limited_api_call(url, params)
        if data:
            anime_list = data.get('data', [])
            first_season_anime = [a for a in anime_list if is_first_season(a)]
            if first_season_anime:
                chosen = random.choice(first_season_anime)
                return await get_anime_by_id(chosen['mal_id'])
        
        return None
    except Exception as e:
        logger.error(f"Error getting random anime: {e}")
        return None


async def get_daily_anime(db_helpers=None) -> Optional[dict]:
    """Get today's daily anime challenge. Uses database for persistence."""
    global _daily_anime_cache, _last_cache_date
    
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    # Check memory cache first
    if _last_cache_date == today and today in _daily_anime_cache:
        logger.debug(f"Returning cached daily anime for {today}")
        return _daily_anime_cache[today]
    
    # Try to get from database
    if db_helpers:
        anime = await get_daily_anime_from_db(db_helpers)
        if anime:
            logger.info(f"Loaded daily anime from database: {anime.get('title')}")
            _daily_anime_cache = {today: anime}
            _last_cache_date = today
            return anime
    
    # Generate new daily anime if not in database
    anime = await get_random_anime()
    if anime:
        _daily_anime_cache = {today: anime}
        _last_cache_date = today
        
        # Save to database for persistence
        if db_helpers:
            await save_daily_anime_to_db(db_helpers, anime)
        
        logger.info(f"Generated new daily anime: {anime.get('title')}")
        return anime
    
    return None


def can_play_daily(user_id: int, is_premium: bool = False) -> tuple[bool, str]:
    """Check if user can play today's daily challenge."""
    if is_premium:
        return True, "Premium user - unlimited plays"
    
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    if today not in daily_plays:
        daily_plays[today] = {}
    
    plays = daily_plays[today].get(user_id, 0)
    
    if plays >= 1:
        return False, "You've already played today's daily challenge. Get Premium for unlimited plays!"
    
    return True, ""


def record_daily_play(user_id: int):
    """Record that a user played the daily challenge."""
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    if today not in daily_plays:
        daily_plays[today] = {}
    
    daily_plays[today][user_id] = daily_plays[today].get(user_id, 0) + 1
