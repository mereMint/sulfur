"""
Last.fm API Integration Module for Sulfur Bot

Provides Last.fm API integration for:
- Track search and metadata retrieval
- Album tracklist retrieval
- Similar tracks and artist discovery
- Random song selection based on user listening history
- Top tracks by genre/tag
"""

import aiohttp
import asyncio
import os
import random
from typing import Optional, List, Dict, Any
from modules.logger_utils import bot_logger as logger

# Last.fm API configuration
LASTFM_API_BASE_URL = "https://ws.audioscrobbler.com/2.0/"

# Cache for API responses to reduce API calls
# Each cache entry is a tuple of (timestamp, data)
_track_cache: Dict[str, tuple] = {}
_album_cache: Dict[str, tuple] = {}
_similar_tracks_cache: Dict[str, tuple] = {}
CACHE_MAX_SIZE = 500
CACHE_TTL_SECONDS = 3600  # 1 hour


def _get_cached(cache: dict, key: str) -> Optional[Any]:
    """Get an item from cache if it exists and hasn't expired."""
    import time
    if key in cache:
        timestamp, data = cache[key]
        if time.time() - timestamp < CACHE_TTL_SECONDS:
            return data
        else:
            # Expired, remove from cache
            del cache[key]
    return None


def _set_cached(cache: dict, key: str, data: Any) -> None:
    """Set an item in cache with current timestamp, evicting old entries if needed."""
    import time
    
    # Evict oldest entries if cache is full
    if len(cache) >= CACHE_MAX_SIZE:
        # Remove 10% of oldest entries
        entries_to_remove = max(1, CACHE_MAX_SIZE // 10)
        sorted_keys = sorted(cache.keys(), key=lambda k: cache[k][0])
        for old_key in sorted_keys[:entries_to_remove]:
            del cache[old_key]
    
    cache[key] = (time.time(), data)


def get_lastfm_api_key() -> Optional[str]:
    """
    Get the Last.fm API key from environment variables.
    
    Returns:
        Last.fm API key or None if not configured
    """
    return os.environ.get('LASTFM_API_KEY', '').strip() or None


def is_lastfm_configured() -> bool:
    """
    Check if Last.fm API is properly configured.
    
    Returns:
        True if Last.fm API key is configured, False otherwise
    """
    api_key = get_lastfm_api_key()
    return api_key is not None and len(api_key) > 10


async def _make_api_request(params: Dict[str, str], timeout: int = 15) -> Optional[dict]:
    """
    Make a request to the Last.fm API.
    
    Args:
        params: API parameters (method will be added)
        timeout: Request timeout in seconds
    
    Returns:
        API response as dict or None on error
    """
    api_key = get_lastfm_api_key()
    if not api_key:
        logger.warning("Last.fm API key not configured")
        return None
    
    # Add common parameters
    params['api_key'] = api_key
    params['format'] = 'json'
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(LASTFM_API_BASE_URL, params=params, timeout=timeout) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Check for API errors
                    if 'error' in data:
                        error_code = data.get('error', 0)
                        error_msg = data.get('message', 'Unknown error')
                        logger.warning(f"Last.fm API error {error_code}: {error_msg}")
                        return None
                    
                    return data
                else:
                    error_text = await response.text()
                    logger.error(f"Last.fm API HTTP {response.status}: {error_text[:200]}")
                    return None
                    
    except asyncio.TimeoutError:
        logger.warning(f"Last.fm API request timed out after {timeout}s")
        return None
    except aiohttp.ClientError as e:
        logger.error(f"Last.fm API network error: {e}")
        return None
    except Exception as e:
        logger.error(f"Last.fm API error: {e}", exc_info=True)
        return None


async def search_track(track_name: str, artist: str = None, limit: int = 5) -> List[dict]:
    """
    Search for tracks on Last.fm.
    
    Args:
        track_name: Track name to search for
        artist: Optional artist name to narrow search
        limit: Maximum number of results
    
    Returns:
        List of track dictionaries with title, artist, url, etc.
    """
    if not is_lastfm_configured():
        return []
    
    # Build search query
    query = f"{artist} - {track_name}" if artist else track_name
    
    params = {
        'method': 'track.search',
        'track': query,
        'limit': str(limit)
    }
    
    data = await _make_api_request(params)
    if not data:
        return []
    
    try:
        tracks = data.get('results', {}).get('trackmatches', {}).get('track', [])
        
        # Normalize to list (Last.fm returns single item as dict)
        if isinstance(tracks, dict):
            tracks = [tracks]
        
        results = []
        for track in tracks[:limit]:
            results.append({
                'title': track.get('name', 'Unknown'),
                'artist': track.get('artist', 'Unknown'),
                'url': track.get('url'),
                'listeners': int(track.get('listeners', 0)) if track.get('listeners') else 0,
                'source': 'lastfm'
            })
        
        logger.info(f"Last.fm: Found {len(results)} tracks for query '{query}'")
        return results
        
    except Exception as e:
        logger.error(f"Error parsing Last.fm track search: {e}")
        return []


async def get_track_info(track_name: str, artist: str) -> Optional[dict]:
    """
    Get detailed information about a specific track.
    
    Args:
        track_name: Track name
        artist: Artist name
    
    Returns:
        Track info dictionary or None
    """
    if not is_lastfm_configured():
        return None
    
    cache_key = f"{artist}|{track_name}".lower()
    cached = _get_cached(_track_cache, cache_key)
    if cached is not None:
        return cached
    
    params = {
        'method': 'track.getInfo',
        'track': track_name,
        'artist': artist
    }
    
    data = await _make_api_request(params)
    if not data:
        return None
    
    try:
        track = data.get('track', {})
        
        result = {
            'title': track.get('name', track_name),
            'artist': track.get('artist', {}).get('name', artist),
            'album': track.get('album', {}).get('title'),
            'duration': int(track.get('duration', 0)) // 1000 if track.get('duration') else None,
            'listeners': int(track.get('listeners', 0)) if track.get('listeners') else 0,
            'playcount': int(track.get('playcount', 0)) if track.get('playcount') else 0,
            'url': track.get('url'),
            'tags': [tag.get('name') for tag in track.get('toptags', {}).get('tag', [])],
            'source': 'lastfm'
        }
        
        # Cache the result
        _set_cached(_track_cache, cache_key, result)
        
        return result
        
    except Exception as e:
        logger.error(f"Error parsing Last.fm track info: {e}")
        return None


async def get_album_tracks(album_name: str, artist: str) -> List[dict]:
    """
    Get the tracklist for an album from Last.fm.
    
    Args:
        album_name: Album name
        artist: Artist name
    
    Returns:
        List of track dictionaries with title, artist, duration, track_number
    """
    if not is_lastfm_configured():
        return []
    
    cache_key = f"{artist}|{album_name}".lower()
    cached = _get_cached(_album_cache, cache_key)
    if cached is not None:
        return cached.get('tracks', [])
    
    params = {
        'method': 'album.getInfo',
        'album': album_name,
        'artist': artist
    }
    
    data = await _make_api_request(params)
    if not data:
        return []
    
    try:
        album = data.get('album', {})
        tracks_data = album.get('tracks', {}).get('track', [])
        
        # Normalize to list
        if isinstance(tracks_data, dict):
            tracks_data = [tracks_data]
        
        tracks = []
        for i, track in enumerate(tracks_data):
            tracks.append({
                'title': track.get('name', f'Track {i+1}'),
                'artist': track.get('artist', {}).get('name', artist) if isinstance(track.get('artist'), dict) else artist,
                'album': album.get('name', album_name),
                'duration': int(track.get('duration', 0)) if track.get('duration') else None,
                'track_number': int(track.get('@attr', {}).get('rank', i+1)) if track.get('@attr') else i+1,
                'url': track.get('url'),
                'source': 'lastfm'
            })
        
        # Cache the result
        _set_cached(_album_cache, cache_key, {
            'name': album.get('name'),
            'artist': artist,
            'tracks': tracks
        })
        
        logger.info(f"Last.fm: Found {len(tracks)} tracks for album '{album_name}' by '{artist}'")
        return tracks
        
    except Exception as e:
        logger.error(f"Error parsing Last.fm album tracks: {e}")
        return []


async def get_similar_tracks(track_name: str, artist: str, limit: int = 20) -> List[dict]:
    """
    Get tracks similar to a given track.
    Perfect for generating personalized recommendations.
    
    Args:
        track_name: Track name
        artist: Artist name
        limit: Maximum number of similar tracks
    
    Returns:
        List of similar track dictionaries
    """
    if not is_lastfm_configured():
        return []
    
    cache_key = f"{artist}|{track_name}".lower()
    cached = _get_cached(_similar_tracks_cache, cache_key)
    if cached is not None:
        return cached[:limit]
    
    params = {
        'method': 'track.getSimilar',
        'track': track_name,
        'artist': artist,
        'limit': str(limit)
    }
    
    data = await _make_api_request(params)
    if not data:
        return []
    
    try:
        similar_tracks = data.get('similartracks', {}).get('track', [])
        
        # Normalize to list
        if isinstance(similar_tracks, dict):
            similar_tracks = [similar_tracks]
        
        results = []
        for track in similar_tracks[:limit]:
            results.append({
                'title': track.get('name', 'Unknown'),
                'artist': track.get('artist', {}).get('name', 'Unknown') if isinstance(track.get('artist'), dict) else track.get('artist', 'Unknown'),
                'match': float(track.get('match', 0)),
                'playcount': int(track.get('playcount', 0)) if track.get('playcount') else 0,
                'url': track.get('url'),
                'source': 'lastfm'
            })
        
        # Cache the result
        _set_cached(_similar_tracks_cache, cache_key, results)
        
        logger.info(f"Last.fm: Found {len(results)} similar tracks to '{track_name}' by '{artist}'")
        return results
        
    except Exception as e:
        logger.error(f"Error parsing Last.fm similar tracks: {e}")
        return []


async def get_top_tracks_by_tag(tag: str, limit: int = 50) -> List[dict]:
    """
    Get top tracks for a specific tag/genre.
    Useful for discovering songs by genre.
    
    Args:
        tag: Genre/tag name (e.g., "rock", "pop", "hip-hop")
        limit: Maximum number of tracks
    
    Returns:
        List of track dictionaries
    """
    if not is_lastfm_configured():
        return []
    
    params = {
        'method': 'tag.getTopTracks',
        'tag': tag,
        'limit': str(limit)
    }
    
    data = await _make_api_request(params)
    if not data:
        return []
    
    try:
        tracks = data.get('tracks', {}).get('track', [])
        
        # Normalize to list
        if isinstance(tracks, dict):
            tracks = [tracks]
        
        results = []
        for track in tracks[:limit]:
            results.append({
                'title': track.get('name', 'Unknown'),
                'artist': track.get('artist', {}).get('name', 'Unknown') if isinstance(track.get('artist'), dict) else track.get('artist', 'Unknown'),
                'duration': int(track.get('duration', 0)) if track.get('duration') else None,
                'url': track.get('url'),
                'tag': tag,
                'source': 'lastfm'
            })
        
        logger.info(f"Last.fm: Found {len(results)} top tracks for tag '{tag}'")
        return results
        
    except Exception as e:
        logger.error(f"Error parsing Last.fm top tracks by tag: {e}")
        return []


async def get_similar_artists(artist: str, limit: int = 10) -> List[dict]:
    """
    Get artists similar to a given artist.
    
    Args:
        artist: Artist name
        limit: Maximum number of similar artists
    
    Returns:
        List of similar artist dictionaries
    """
    if not is_lastfm_configured():
        return []
    
    params = {
        'method': 'artist.getSimilar',
        'artist': artist,
        'limit': str(limit)
    }
    
    data = await _make_api_request(params)
    if not data:
        return []
    
    try:
        similar_artists = data.get('similarartists', {}).get('artist', [])
        
        # Normalize to list
        if isinstance(similar_artists, dict):
            similar_artists = [similar_artists]
        
        results = []
        for art in similar_artists[:limit]:
            results.append({
                'name': art.get('name', 'Unknown'),
                'match': float(art.get('match', 0)),
                'url': art.get('url'),
                'source': 'lastfm'
            })
        
        return results
        
    except Exception as e:
        logger.error(f"Error parsing Last.fm similar artists: {e}")
        return []


async def get_artist_top_tracks(artist: str, limit: int = 10) -> List[dict]:
    """
    Get top tracks for an artist.
    
    Args:
        artist: Artist name
        limit: Maximum number of tracks
    
    Returns:
        List of track dictionaries
    """
    if not is_lastfm_configured():
        return []
    
    params = {
        'method': 'artist.getTopTracks',
        'artist': artist,
        'limit': str(limit)
    }
    
    data = await _make_api_request(params)
    if not data:
        return []
    
    try:
        tracks = data.get('toptracks', {}).get('track', [])
        
        # Normalize to list
        if isinstance(tracks, dict):
            tracks = [tracks]
        
        results = []
        for track in tracks[:limit]:
            results.append({
                'title': track.get('name', 'Unknown'),
                'artist': track.get('artist', {}).get('name', artist) if isinstance(track.get('artist'), dict) else artist,
                'playcount': int(track.get('playcount', 0)) if track.get('playcount') else 0,
                'listeners': int(track.get('listeners', 0)) if track.get('listeners') else 0,
                'url': track.get('url'),
                'source': 'lastfm'
            })
        
        return results
        
    except Exception as e:
        logger.error(f"Error parsing Last.fm artist top tracks: {e}")
        return []


async def get_chart_top_tracks(limit: int = 50) -> List[dict]:
    """
    Get global chart top tracks.
    
    Args:
        limit: Maximum number of tracks
    
    Returns:
        List of track dictionaries
    """
    if not is_lastfm_configured():
        return []
    
    params = {
        'method': 'chart.getTopTracks',
        'limit': str(limit)
    }
    
    data = await _make_api_request(params)
    if not data:
        return []
    
    try:
        tracks = data.get('tracks', {}).get('track', [])
        
        # Normalize to list
        if isinstance(tracks, dict):
            tracks = [tracks]
        
        results = []
        for track in tracks[:limit]:
            results.append({
                'title': track.get('name', 'Unknown'),
                'artist': track.get('artist', {}).get('name', 'Unknown') if isinstance(track.get('artist'), dict) else track.get('artist', 'Unknown'),
                'playcount': int(track.get('playcount', 0)) if track.get('playcount') else 0,
                'listeners': int(track.get('listeners', 0)) if track.get('listeners') else 0,
                'url': track.get('url'),
                'source': 'lastfm'
            })
        
        logger.info(f"Last.fm: Got {len(results)} chart top tracks")
        return results
        
    except Exception as e:
        logger.error(f"Error parsing Last.fm chart top tracks: {e}")
        return []


async def get_personalized_recommendations(
    user_history: List[dict],
    count: int = 25,
    diversity_factor: float = 0.3
) -> List[dict]:
    """
    Generate personalized song recommendations based on user's listening history.
    Uses Last.fm similar tracks and artist top tracks for discovery.
    
    Args:
        user_history: List of song dicts with 'title' and 'artist' keys
        count: Number of recommendations to generate
        diversity_factor: 0.0-1.0 - higher means more diverse (less similar)
    
    Returns:
        List of recommended track dictionaries
    """
    if not is_lastfm_configured():
        logger.info("Last.fm not configured, falling back to empty recommendations")
        return []
    
    if not user_history:
        # If no history, return chart top tracks
        return await get_chart_top_tracks(limit=count)
    
    recommendations = []
    seen_tracks = set()
    
    # Add user's history tracks to seen set to avoid recommending what they already know
    for song in user_history:
        key = f"{song.get('artist', '').lower()}|{song.get('title', '').lower()}"
        seen_tracks.add(key)
    
    # Strategy 1: Get similar tracks for top songs (60% of recommendations)
    similar_count = int(count * 0.6)
    top_songs = user_history[:min(5, len(user_history))]  # Use top 5 most played
    
    for song in top_songs:
        if len(recommendations) >= similar_count:
            break
        
        similar = await get_similar_tracks(song.get('title', ''), song.get('artist', ''), limit=10)
        
        for track in similar:
            if len(recommendations) >= similar_count:
                break
            
            key = f"{track.get('artist', '').lower()}|{track.get('title', '').lower()}"
            if key not in seen_tracks:
                seen_tracks.add(key)
                recommendations.append(track)
    
    # Strategy 2: Get top tracks from similar artists (25% of recommendations)
    artist_count = int(count * 0.25)
    top_artists = list(set(song.get('artist', '') for song in user_history[:10]))[:3]
    
    for artist in top_artists:
        if len(recommendations) >= similar_count + artist_count:
            break
        
        # Get similar artists
        similar_artists = await get_similar_artists(artist, limit=3)
        
        for similar_artist in similar_artists:
            if len(recommendations) >= similar_count + artist_count:
                break
            
            # Get top tracks from similar artist
            artist_tracks = await get_artist_top_tracks(similar_artist.get('name', ''), limit=5)
            
            for track in artist_tracks:
                if len(recommendations) >= similar_count + artist_count:
                    break
                
                key = f"{track.get('artist', '').lower()}|{track.get('title', '').lower()}"
                if key not in seen_tracks:
                    seen_tracks.add(key)
                    recommendations.append(track)
    
    # Strategy 3: Add some chart top tracks for diversity (15% of recommendations)
    chart_count = count - len(recommendations)
    if chart_count > 0:
        chart_tracks = await get_chart_top_tracks(limit=chart_count * 2)
        
        for track in chart_tracks:
            if len(recommendations) >= count:
                break
            
            key = f"{track.get('artist', '').lower()}|{track.get('title', '').lower()}"
            if key not in seen_tracks:
                seen_tracks.add(key)
                recommendations.append(track)
    
    # Shuffle to mix different sources
    if diversity_factor > 0:
        # Shuffle with some randomness based on diversity factor
        random.shuffle(recommendations)
    
    logger.info(f"Last.fm: Generated {len(recommendations)} personalized recommendations")
    return recommendations[:count]


async def get_random_songs_for_songle(count: int = 50, genres: List[str] = None) -> List[dict]:
    """
    Get random songs suitable for the Songle game.
    Uses Last.fm top tracks by genre/tag for variety.
    
    Genres can be configured in config/config.json under modules.music.songle_genres.
    
    Args:
        count: Number of songs to retrieve
        genres: Optional list of genres to sample from. If None, uses config or defaults.
    
    Returns:
        List of song dictionaries with title, artist, genre
    """
    if not is_lastfm_configured():
        logger.info("Last.fm not configured for Songle random songs")
        return []
    
    # Load genres from config if not provided
    if genres is None:
        try:
            import json
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'config.json')
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                genres = config.get('modules', {}).get('music', {}).get('songle_genres', None)
        except Exception as e:
            logger.debug(f"Could not load genres from config: {e}")
    
    # Default genres for variety (fallback if config not available)
    default_genres = [
        'pop', 'rock', 'hip-hop', 'electronic', 'indie', 'rnb',
        'alternative', 'dance', 'metal', 'jazz', 'classical',
        'country', 'folk', 'blues', 'reggae', 'punk', 'soul'
    ]
    
    genres = genres or default_genres
    songs = []
    seen_songs = set()
    
    # Get songs from multiple genres for variety
    songs_per_genre = max(1, count // len(genres))
    
    for genre in genres:
        if len(songs) >= count:
            break
        
        genre_tracks = await get_top_tracks_by_tag(genre, limit=songs_per_genre * 2)
        
        for track in genre_tracks:
            if len(songs) >= count:
                break
            
            key = f"{track.get('artist', '').lower()}|{track.get('title', '').lower()}"
            if key not in seen_songs:
                seen_songs.add(key)
                songs.append({
                    'title': track.get('title'),
                    'artist': track.get('artist'),
                    'genre': genre.title(),
                    'year': None,  # Last.fm doesn't provide year in this endpoint
                    'album': None,
                    'source': 'lastfm'
                })
    
    # Shuffle for randomness
    random.shuffle(songs)
    
    logger.info(f"Last.fm: Got {len(songs)} random songs for Songle from {len(genres)} genres")
    return songs[:count]


def clear_cache():
    """Clear all Last.fm API caches."""
    global _track_cache, _album_cache, _similar_tracks_cache
    _track_cache.clear()
    _album_cache.clear()
    _similar_tracks_cache.clear()
    logger.info("Last.fm API cache cleared")
