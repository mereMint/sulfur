"""
Sulfur Bot - Songle (Guess the Song) Game Module
A daily song guessing game where players listen to audio clips and guess the song.
"""

import discord
import random
import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from modules.logger_utils import bot_logger as logger

# Active games per user
active_songle_games: Dict[int, 'SongleGame'] = {}

# Daily play tracking
daily_plays: Dict[str, Dict[int, int]] = {}  # {date_str: {user_id: play_count}}

# Audio URL cache
_audio_url_cache: Dict[int, str] = {}  # {song_id: youtube_url}

# Cache for daily song
_daily_song_cache: Dict[str, dict] = {}
_last_cache_date: Optional[str] = None

# Song database - popular songs with metadata
# In production, this would come from a database or music API
SONG_DATABASE = [
    {
        'id': 1,
        'title': 'Blinding Lights',
        'artist': 'The Weeknd',
        'year': 2019,
        'genre': 'Synth-pop',
        'album': 'After Hours',
        'preview_url': None  # Would contain actual audio URL
    },
    {
        'id': 2,
        'title': 'Shape of You',
        'artist': 'Ed Sheeran',
        'year': 2017,
        'genre': 'Pop',
        'album': '÷ (Divide)',
        'preview_url': None
    },
    {
        'id': 3,
        'title': 'Bad Guy',
        'artist': 'Billie Eilish',
        'year': 2019,
        'genre': 'Electropop',
        'album': 'When We All Fall Asleep, Where Do We Go?',
        'preview_url': None
    },
    {
        'id': 4,
        'title': 'Uptown Funk',
        'artist': 'Mark Ronson ft. Bruno Mars',
        'year': 2014,
        'genre': 'Funk',
        'album': 'Uptown Special',
        'preview_url': None
    },
    {
        'id': 5,
        'title': 'Rolling in the Deep',
        'artist': 'Adele',
        'year': 2010,
        'genre': 'Soul',
        'album': '21',
        'preview_url': None
    },
    {
        'id': 6,
        'title': 'Bohemian Rhapsody',
        'artist': 'Queen',
        'year': 1975,
        'genre': 'Rock',
        'album': 'A Night at the Opera',
        'preview_url': None
    },
    {
        'id': 7,
        'title': 'Smells Like Teen Spirit',
        'artist': 'Nirvana',
        'year': 1991,
        'genre': 'Grunge',
        'album': 'Nevermind',
        'preview_url': None
    },
    {
        'id': 8,
        'title': 'Billie Jean',
        'artist': 'Michael Jackson',
        'year': 1982,
        'genre': 'Pop',
        'album': 'Thriller',
        'preview_url': None
    },
    {
        'id': 9,
        'title': 'Sweet Child O\' Mine',
        'artist': 'Guns N\' Roses',
        'year': 1987,
        'genre': 'Rock',
        'album': 'Appetite for Destruction',
        'preview_url': None
    },
    {
        'id': 10,
        'title': 'Lose Yourself',
        'artist': 'Eminem',
        'year': 2002,
        'genre': 'Hip Hop',
        'album': '8 Mile Soundtrack',
        'preview_url': None
    },
    {
        'id': 11,
        'title': 'Despacito',
        'artist': 'Luis Fonsi ft. Daddy Yankee',
        'year': 2017,
        'genre': 'Reggaeton',
        'album': 'Vida',
        'preview_url': None
    },
    {
        'id': 12,
        'title': 'Old Town Road',
        'artist': 'Lil Nas X',
        'year': 2019,
        'genre': 'Country Rap',
        'album': '7 EP',
        'preview_url': None
    },
    {
        'id': 13,
        'title': 'Thriller',
        'artist': 'Michael Jackson',
        'year': 1982,
        'genre': 'Pop',
        'album': 'Thriller',
        'preview_url': None
    },
    {
        'id': 14,
        'title': 'Hotel California',
        'artist': 'Eagles',
        'year': 1977,
        'genre': 'Rock',
        'album': 'Hotel California',
        'preview_url': None
    },
    {
        'id': 15,
        'title': 'Gangnam Style',
        'artist': 'PSY',
        'year': 2012,
        'genre': 'K-Pop',
        'album': 'PSY 6 (Six Rules), Part 1',
        'preview_url': None
    }
]

# Clip durations for each attempt
CLIP_DURATIONS = [3, 5, 10, 20, 40]  # seconds


async def initialize_songle_tables(db_helpers):
    """Initialize the Songle game tables in the database."""
    try:
        if not db_helpers.db_pool:
            logger.error("Database pool not available for Songle initialization")
            return
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            logger.error("Could not get database connection for Songle")
            return
        
        cursor = conn.cursor()
        try:
            # Table for daily song
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS songle_daily (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    song_id INT NOT NULL,
                    song_data JSON NOT NULL,
                    date DATE NOT NULL,
                    UNIQUE KEY unique_date (date),
                    INDEX idx_date (date)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Table for user games/stats
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS songle_games (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    song_id INT NOT NULL,
                    game_type ENUM('daily', 'premium') DEFAULT 'daily',
                    guesses INT DEFAULT 0,
                    won BOOLEAN DEFAULT FALSE,
                    completed BOOLEAN DEFAULT FALSE,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP NULL,
                    INDEX idx_user_id (user_id),
                    INDEX idx_date (started_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            conn.commit()
            logger.info("Songle tables initialized successfully")
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error initializing Songle tables: {e}", exc_info=True)


async def save_daily_song_to_db(db_helpers, song: dict) -> bool:
    """Save today's daily song to the database."""
    try:
        if not db_helpers.db_pool:
            return False
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        try:
            today = datetime.now(timezone.utc).date()
            song_id = song.get('id')
            song_json = json.dumps(song, ensure_ascii=False)
            
            cursor.execute("""
                INSERT INTO songle_daily (song_id, song_data, date)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    song_id = VALUES(song_id),
                    song_data = VALUES(song_data)
            """, (song_id, song_json, today))
            
            conn.commit()
            logger.info(f"Saved daily song to database: {song.get('title')} by {song.get('artist')}")
            return True
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error saving daily song to database: {e}", exc_info=True)
        return False


async def get_daily_song_from_db(db_helpers) -> Optional[dict]:
    """Get today's daily song from the database."""
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
                SELECT song_data FROM songle_daily WHERE date = %s
            """, (today,))
            
            row = cursor.fetchone()
            if row and row.get('song_data'):
                song_data = row['song_data']
                if isinstance(song_data, str):
                    return json.loads(song_data)
                return song_data
            
            return None
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error getting daily song from database: {e}", exc_info=True)
        return None


async def record_songle_game(db_helpers, user_id: int, song_id: int, guesses: int, won: bool, game_type: str = 'daily'):
    """Record a completed Songle game to the database."""
    try:
        if not db_helpers.db_pool:
            return False
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO songle_games (user_id, song_id, game_type, guesses, won, completed, completed_at)
                VALUES (%s, %s, %s, %s, %s, TRUE, NOW())
            """, (user_id, song_id, game_type, guesses, won))
            
            conn.commit()
            logger.info(f"Recorded Songle game for user {user_id}: {'won' if won else 'lost'} in {guesses} guesses")
            return True
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error recording Songle game: {e}", exc_info=True)
        return False


class SongleGame:
    """Handles a Songle game instance."""
    
    MAX_GUESSES = 5
    
    def __init__(self, player_id: int, target_song: dict, is_premium: bool = False):
        self.player_id = player_id
        self.target_song = target_song
        self.is_premium = is_premium
        self.guesses: List[dict] = []
        self.is_active = True
        self.won = False
        self.started_at = datetime.now(timezone.utc)
    
    @property
    def attempts(self) -> int:
        return len(self.guesses)
    
    @property
    def remaining_guesses(self) -> int:
        return self.MAX_GUESSES - self.attempts
    
    @property
    def current_clip_duration(self) -> int:
        """Get the clip duration for the current attempt."""
        if self.attempts >= len(CLIP_DURATIONS):
            return CLIP_DURATIONS[-1]
        return CLIP_DURATIONS[self.attempts]
    
    def get_hints_for_attempt(self) -> List[str]:
        """Get hints that should be revealed based on current attempt count."""
        hints = []
        
        # More hints with each attempt
        if self.attempts >= 1:
            hints.append(f"Year: {self.target_song['year']}")
        if self.attempts >= 2:
            hints.append(f"Genre: {self.target_song['genre']}")
        if self.attempts >= 3:
            hints.append(f"Album: {self.target_song['album']}")
        if self.attempts >= 4:
            # First letter of artist
            first_letter = self.target_song['artist'][0]
            hints.append(f"Artist starts with: {first_letter}")
        
        return hints
    
    def check_guess(self, guess: str) -> dict:
        """Check if the guess is correct."""
        if not self.is_active:
            return {'error': 'Game is not active'}
        
        if self.attempts >= self.MAX_GUESSES:
            self.is_active = False
            return {'error': 'No more guesses remaining'}
        
        # Normalize strings for comparison
        guess_lower = guess.lower().strip()
        title_lower = self.target_song['title'].lower()
        artist_lower = self.target_song['artist'].lower()
        
        # Check for matches
        title_match = guess_lower in title_lower or title_lower in guess_lower
        artist_match = guess_lower in artist_lower or artist_lower in guess_lower
        
        # Exact match or close enough
        is_correct = title_match or (guess_lower == title_lower) or (
            # Check if they guessed "artist - title" format
            f"{artist_lower} - {title_lower}" in guess_lower or
            f"{title_lower} - {artist_lower}" in guess_lower or
            f"{title_lower} by {artist_lower}" in guess_lower
        )
        
        result = {
            'guess': guess,
            'is_correct': is_correct,
            'attempt': self.attempts + 1
        }
        
        self.guesses.append(result)
        
        if is_correct:
            self.won = True
            self.is_active = False
        elif self.attempts >= self.MAX_GUESSES:
            self.is_active = False
        
        return result
    
    def create_embed(self, last_result: Optional[dict] = None, embed_color: int = 0x00ff41) -> discord.Embed:
        """Create an embed showing the current game state."""
        embed = discord.Embed(
            title="Songle - Guess the Song",
            color=embed_color
        )
        
        if self.won:
            embed.color = 0x00ff00
            embed.description = f"Correct! You got it in {self.attempts} attempt(s)!"
            embed.add_field(
                name="The Song",
                value=f"**{self.target_song['title']}** by {self.target_song['artist']}",
                inline=False
            )
        elif not self.is_active:
            embed.color = 0xff0000
            embed.description = "Game Over!"
            embed.add_field(
                name="The Song Was",
                value=f"**{self.target_song['title']}** by {self.target_song['artist']}",
                inline=False
            )
        else:
            embed.description = f"🎵 Guess the song using the hints below!\nAttempt {self.attempts + 1}/{self.MAX_GUESSES}"
            
            # Audio preview info
            clip_duration = self.current_clip_duration
            embed.add_field(
                name="🔊 Audio Preview",
                value=f"Click the **Listen** button to hear a {clip_duration}s clip!\nJoin a voice channel first.",
                inline=False
            )
            
            # Show hints
            hints = self.get_hints_for_attempt()
            if hints:
                embed.add_field(
                    name="💡 Hints",
                    value="\n".join(hints),
                    inline=False
                )
            
            embed.add_field(
                name="Remaining Guesses",
                value=str(self.remaining_guesses),
                inline=True
            )
            
            # Show previous guesses
            if self.guesses:
                guess_text = "\n".join([
                    f"{i+1}. {g['guess']} - [X]" 
                    for i, g in enumerate(self.guesses)
                ])
                embed.add_field(
                    name="Previous Guesses",
                    value=guess_text,
                    inline=False
                )
        
        embed.set_footer(text="Use /songle guess <song name> to guess | /songle skip to skip")
        
        return embed


async def get_daily_song(db_helpers=None) -> dict:
    """Get today's daily song challenge. Uses database for persistence."""
    global _daily_song_cache, _last_cache_date
    
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    # Check memory cache first
    if _last_cache_date == today and today in _daily_song_cache:
        logger.debug(f"Returning cached daily song for {today}")
        return _daily_song_cache[today]
    
    # Try to get from database
    if db_helpers:
        song = await get_daily_song_from_db(db_helpers)
        if song:
            logger.info(f"Loaded daily song from database: {song.get('title')}")
            _daily_song_cache = {today: song}
            _last_cache_date = today
            return song
    
    # Generate new daily song if not in database
    # Use the day as seed for reproducible daily song
    random.seed(today)
    song = random.choice(SONG_DATABASE)
    random.seed()  # Reset seed
    
    _daily_song_cache = {today: song}
    _last_cache_date = today
    
    # Save to database for persistence
    if db_helpers:
        await save_daily_song_to_db(db_helpers, song)
    
    logger.info(f"Generated new daily song: {song.get('title')} by {song.get('artist')}")
    return song


def can_play_daily(user_id: int, is_premium: bool = False) -> tuple[bool, str]:
    """Check if user can play today's daily challenge."""
    if is_premium:
        return True, "Premium user - unlimited plays"
    
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    if today not in daily_plays:
        daily_plays[today] = {}
    
    plays = daily_plays[today].get(user_id, 0)
    
    if plays >= 1:
        return False, "You've already played today's Songle challenge. Get Premium for unlimited plays!"
    
    return True, ""


def record_daily_play(user_id: int):
    """Record that a user played the daily challenge."""
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    if today not in daily_plays:
        daily_plays[today] = {}
    
    daily_plays[today][user_id] = daily_plays[today].get(user_id, 0) + 1


def search_songs(query: str) -> List[dict]:
    """Search for songs matching the query."""
    query_lower = query.lower()
    results = []
    
    for song in SONG_DATABASE:
        if (query_lower in song['title'].lower() or 
            query_lower in song['artist'].lower()):
            results.append(song)
    
    return results[:5]  # Limit results


async def get_song_youtube_url(song: dict) -> Optional[str]:
    """
    Get a YouTube URL for a song to play as audio.
    Uses lofi_player's YouTube search functionality.
    
    Args:
        song: Song dictionary with 'title' and 'artist'
    
    Returns:
        YouTube URL or None if not found
    """
    try:
        from modules import lofi_player
        
        song_id = song.get('id')
        
        # Check cache first
        if song_id and song_id in _audio_url_cache:
            return _audio_url_cache[song_id]
        
        # Search YouTube for the song
        url = await lofi_player.search_youtube_song(
            song['title'], 
            song['artist'],
            filter_shorts=True,
            skip_remixes=True
        )
        
        # Cache the result
        if url and song_id:
            _audio_url_cache[song_id] = url
        
        return url
        
    except Exception as e:
        logger.error(f"Error getting YouTube URL for song: {e}")
        return None


async def play_song_clip(
    voice_client,
    song: dict,
    duration_seconds: int = 5,
    guild_id: int = None
) -> bool:
    """
    Play a short clip of a song in a voice channel.
    
    Args:
        voice_client: Discord voice client (connected)
        song: Song dictionary with 'title' and 'artist'
        duration_seconds: How many seconds of the song to play
        guild_id: Guild ID for session tracking
    
    Returns:
        True if clip played successfully, False otherwise
    """
    try:
        from modules import lofi_player
        
        if not voice_client or not voice_client.is_connected():
            logger.warning("Voice client not connected for Songle clip")
            return False
        
        # Get YouTube URL for the song
        url = await get_song_youtube_url(song)
        if not url:
            logger.warning(f"Could not find YouTube URL for: {song.get('title')} by {song.get('artist')}")
            return False
        
        # Create song dict for lofi_player
        song_data = {
            'title': song.get('title', 'Unknown'),
            'artist': song.get('artist', 'Unknown'),
            'url': url,
            'source': 'songle'
        }
        
        # Stop any current playback
        if voice_client.is_playing():
            voice_client.stop()
            await asyncio.sleep(0.2)
        
        # Play the song clip (will be stopped after duration_seconds)
        import yt_dlp
        
        with yt_dlp.YoutubeDL(lofi_player.YDL_OPTIONS) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, url, download=False)
            audio_url = lofi_player.extract_audio_url(info)
            
            if not audio_url:
                logger.error("Could not extract audio URL for Songle clip")
                return False
        
        # Create audio source
        audio_source = discord.FFmpegPCMAudio(audio_url, **lofi_player.FFMPEG_OPTIONS)
        
        # Play the clip
        voice_client.play(audio_source)
        
        # Wait for the clip duration, then stop
        await asyncio.sleep(duration_seconds)
        
        if voice_client.is_playing():
            voice_client.stop()
        
        logger.info(f"Played {duration_seconds}s clip of: {song.get('title')}")
        return True
        
    except ImportError as e:
        logger.error(f"yt-dlp not installed for Songle clips: {e}")
        return False
    except Exception as e:
        logger.error(f"Error playing Songle clip: {e}", exc_info=True)
        return False


async def join_and_play_clip(
    interaction,
    song: dict,
    duration_seconds: int = 5
) -> tuple:
    """
    Join the user's voice channel and play a song clip.
    
    Args:
        interaction: Discord interaction (for getting user's voice channel)
        song: Song dictionary with 'title' and 'artist'
        duration_seconds: How many seconds of the song to play
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        from modules import lofi_player
        
        # Check if user is in a voice channel
        if not interaction.user.voice or not interaction.user.voice.channel:
            return (False, "You need to be in a voice channel to hear the clip!")
        
        voice_channel = interaction.user.voice.channel
        
        # Join the voice channel
        voice_client = await lofi_player.join_voice_channel(voice_channel)
        if not voice_client:
            return (False, "Could not join your voice channel. Check my permissions!")
        
        # Play the clip
        success = await play_song_clip(
            voice_client,
            song,
            duration_seconds,
            interaction.guild.id
        )
        
        if success:
            return (True, f"Playing {duration_seconds}s clip...")
        else:
            return (False, "Could not play the audio clip. The song might not be available on YouTube.")
        
    except Exception as e:
        logger.error(f"Error in join_and_play_clip: {e}", exc_info=True)
        return (False, f"Error: {str(e)}")
