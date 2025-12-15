"""
Sulfur Bot - Anidle Game Module
An anime guessing game similar to Wordle.
Players guess an anime and receive feedback on how their guess compares to the target.
"""

import discord
import random
import aiohttp
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from modules.logger_utils import bot_logger as logger

# Jikan API (MyAnimeList unofficial API) - free, no auth required
JIKAN_API_BASE = "https://api.jikan.moe/v4"

# Cache for daily anime
_daily_anime_cache: Dict[str, dict] = {}
_last_cache_date: Optional[str] = None

# Active games per user
active_anidle_games: Dict[int, 'AnidleGame'] = {}

# Daily play tracking
daily_plays: Dict[str, Dict[int, int]] = {}  # {date_str: {user_id: play_count}}


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
    """Search for anime by name using Jikan API."""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{JIKAN_API_BASE}/anime"
            params = {'q': query, 'limit': 5, 'sfw': 'true'}
            async with session.get(url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('data', [])
                else:
                    logger.warning(f"Jikan API returned status {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Error searching anime: {e}")
        return None


async def get_anime_by_id(mal_id: int) -> Optional[dict]:
    """Get full anime details by MAL ID."""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{JIKAN_API_BASE}/anime/{mal_id}/full"
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('data')
                else:
                    logger.warning(f"Jikan API returned status {response.status} for anime {mal_id}")
                    return None
    except Exception as e:
        logger.error(f"Error getting anime {mal_id}: {e}")
        return None


async def get_random_anime() -> Optional[dict]:
    """Get a random popular anime for the daily game."""
    try:
        async with aiohttp.ClientSession() as session:
            # Get top anime to ensure we pick something recognizable
            url = f"{JIKAN_API_BASE}/top/anime"
            params = {'limit': 100, 'filter': 'bypopularity'}
            async with session.get(url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    anime_list = data.get('data', [])
                    if anime_list:
                        chosen = random.choice(anime_list)
                        # Get full details
                        return await get_anime_by_id(chosen['mal_id'])
                return None
    except Exception as e:
        logger.error(f"Error getting random anime: {e}")
        return None


async def get_daily_anime() -> Optional[dict]:
    """Get today's daily anime challenge."""
    global _daily_anime_cache, _last_cache_date
    
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    if _last_cache_date == today and today in _daily_anime_cache:
        return _daily_anime_cache[today]
    
    # Generate new daily anime
    anime = await get_random_anime()
    if anime:
        _daily_anime_cache = {today: anime}  # Only keep today's
        _last_cache_date = today
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
