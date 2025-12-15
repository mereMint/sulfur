"""
Sulfur Bot - Songle (Guess the Song) Game Module
A daily song guessing game where players listen to audio clips and guess the song.
"""

import discord
import random
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from modules.logger_utils import bot_logger as logger

# Active games per user
active_songle_games: Dict[int, 'SongleGame'] = {}

# Daily play tracking
daily_plays: Dict[str, Dict[int, int]] = {}  # {date_str: {user_id: play_count}}

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
            embed.description = f"Listen to the clip and guess the song!\nAttempt {self.attempts + 1}/{self.MAX_GUESSES}"
            
            # Show clip duration info
            embed.add_field(
                name="Current Clip",
                value=f"{self.current_clip_duration} seconds",
                inline=True
            )
            
            embed.add_field(
                name="Remaining Guesses",
                value=str(self.remaining_guesses),
                inline=True
            )
            
            # Show hints
            hints = self.get_hints_for_attempt()
            if hints:
                embed.add_field(
                    name="Hints",
                    value="\n".join(hints),
                    inline=False
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


def get_daily_song() -> dict:
    """Get today's daily song challenge."""
    global _daily_song_cache, _last_cache_date
    
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    if _last_cache_date == today and today in _daily_song_cache:
        return _daily_song_cache[today]
    
    # Use the day as seed for reproducible daily song
    random.seed(today)
    song = random.choice(SONG_DATABASE)
    random.seed()  # Reset seed
    
    _daily_song_cache = {today: song}
    _last_cache_date = today
    
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
