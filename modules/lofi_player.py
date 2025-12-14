"""
Lofi Music Player Module for Sulfur Bot

Provides lofi music streaming capabilities using yt-dlp and Discord voice.
Can be used standalone or integrated with focus timer.
Supports multiple station types, audio mixing, and auto-disconnect.
"""

import asyncio
import discord
from typing import Optional, Dict, List
from modules.logger_utils import bot_logger as logger

# Music stations dictionary - organized by type
MUSIC_STATIONS = {
    "lofi": [
        {
            "name": "📚 Beats to Relax/Study",
            "url": "https://www.youtube.com/watch?v=jfKfPfyJRdk",
            "type": "lofi"
        },
        {
            "name": "🎧 Beats to Sleep/Chill",
            "url": "https://www.youtube.com/watch?v=rUxyKA_-grg",
            "type": "lofi"
        }
    ],
    "nocopyright": [
        {
            "name": "🎵 No Copyright Music",
            "url": "https://www.youtube.com/watch?v=7NOSDKb0HlU",
            "type": "nocopyright"
        },
        {
            "name": "🎸 Royalty Free Music",
            "url": "https://www.youtube.com/watch?v=lTRiuFIWV54",
            "type": "nocopyright"
        }
    ],
    "ambient": [
        {
            "name": "🌧️ Rain Sounds",
            "url": "https://www.youtube.com/watch?v=mPZkdNFkNps",
            "type": "ambient"
        },
        {
            "name": "🌊 Ocean Waves",
            "url": "https://www.youtube.com/watch?v=WHPEKLQID4U",
            "type": "ambient"
        },
        {
            "name": "🔥 Fireplace Sounds",
            "url": "https://www.youtube.com/watch?v=UgHKb_7884o",
            "type": "ambient"
        },
        {
            "name": "☕ Coffee Shop Ambience",
            "url": "https://www.youtube.com/watch?v=h2zkV-l_TbY",
            "type": "ambient"
        },
        {
            "name": "🌳 Forest Sounds",
            "url": "https://www.youtube.com/watch?v=eKFTSSKCzWA",
            "type": "ambient"
        }
    ],
    "noise": [
        {
            "name": "⚪ White Noise",
            "url": "https://www.youtube.com/watch?v=nMfPqeZjc2c",
            "type": "noise"
        },
        {
            "name": "🎀 Pink Noise",
            "url": "https://www.youtube.com/watch?v=ZXtimhT-ff4",
            "type": "noise"
        },
        {
            "name": "🟤 Brown Noise",
            "url": "https://www.youtube.com/watch?v=RqzGzwTY-6w",
            "type": "noise"
        },
        {
            "name": "🌊 Blue Noise",
            "url": "https://www.youtube.com/watch?v=H0JcLOE-pXY",
            "type": "noise"
        },
        {
            "name": "🔇 Grey Noise",
            "url": "https://www.youtube.com/watch?v=_vb4nzF4VFA",
            "type": "noise"
        }
    ]
}

# Active playback sessions per guild
# Format: {guild_id: {'voice_client': VoiceClient, 'stations': [station_configs], 'auto_disconnect_task': Task, 'queue': list, 'failure_count': int}}
active_sessions: Dict[int, dict] = {}

# Maximum consecutive failures before stopping queue
MAX_QUEUE_FAILURES = 3

# FFmpeg options for streaming
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

# yt-dlp options
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}


def get_all_stations() -> List[dict]:
    """Get a flattened list of all available stations."""
    stations = []
    for station_type, station_list in MUSIC_STATIONS.items():
        stations.extend(station_list)
    return stations


def get_stations_by_type(station_type: str) -> List[dict]:
    """Get stations by type (lofi, nocopyright, ambient)."""
    return MUSIC_STATIONS.get(station_type, [])


def find_station_by_name(name: str) -> Optional[dict]:
    """Find a station by its name."""
    for stations in MUSIC_STATIONS.values():
        for station in stations:
            if station['name'] == name:
                return station
    return None


async def create_mixed_audio_source(stations: List[dict], volumes: Optional[List[float]] = None):
    """
    Create a mixed audio source from multiple stations using FFmpeg filters.
    
    NOTE: Multi-station mixing is currently experimental and may not work properly
    with all audio sources. Single station playback is fully supported.
    
    Args:
        stations: List of station dictionaries with 'url' and 'name'
        volumes: Optional list of volume levels (0.0-1.0) for each station
    
    Returns:
        FFmpeg audio source with mixed audio, or None on error
    """
    try:
        import yt_dlp
        
        if not stations:
            return None
        
        # If no volumes specified, use equal volume for all
        if not volumes:
            volumes = [1.0 / len(stations)] * len(stations)
        
        # Ensure volumes list matches stations list
        if len(volumes) < len(stations):
            volumes.extend([1.0 / len(stations)] * (len(stations) - len(volumes)))
        
        # For single station, no mixing needed - fully supported
        if len(stations) == 1:
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(stations[0]['url'], download=False)
                audio_url = extract_audio_url(info)
            
            if not audio_url:
                logger.error(f"Could not extract audio URL from: {stations[0]['url']}")
                return None
            
            # Apply volume filter
            volume_filter = f'volume={volumes[0]}'
            ffmpeg_options = {
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                'options': f'-vn -af "{volume_filter}"'
            }
            return discord.FFmpegPCMAudio(audio_url, **ffmpeg_options)
        
        # For multiple stations, we need to mix them
        # NOTE: This is experimental and requires proper FFmpeg multi-input support
        # TODO: Implement proper multi-source mixing with discord.py's FFmpeg support
        # Current limitation: discord.FFmpegPCMAudio only accepts single URL
        logger.warning("Multi-station mixing is experimental and may not work properly")
        
        # For now, just play the first station with a warning
        # A proper implementation would require custom FFmpeg piping
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(stations[0]['url'], download=False)
            audio_url = extract_audio_url(info)
        
        if not audio_url:
            logger.error(f"Could not extract audio URL from: {stations[0]['url']}")
            return None
        
        volume_filter = f'volume={volumes[0]}'
        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': f'-vn -af "{volume_filter}"'
        }
        return discord.FFmpegPCMAudio(audio_url, **ffmpeg_options)
        
    except Exception as e:
        logger.error(f"Error creating mixed audio source: {e}", exc_info=True)
        return None


def extract_audio_url(info: dict) -> Optional[str]:
    """
    Extract audio URL from yt-dlp info dict.
    Handles various response formats (direct URL, entries, formats).
    
    Args:
        info: Dictionary returned by yt-dlp extract_info()
    
    Returns:
        Audio URL string or None if not found
    """
    if not info:
        return None
    
    # Direct URL (most common for single videos/streams)
    if 'url' in info:
        return info['url']
    
    # For playlists or search results with entries
    if 'entries' in info and info['entries']:
        # Get first entry
        first_entry = info['entries'][0]
        if 'url' in first_entry:
            return first_entry['url']
        # Try formats in first entry
        if 'formats' in first_entry and first_entry['formats']:
            # Get best audio format
            for fmt in reversed(first_entry['formats']):
                if fmt.get('acodec') != 'none' and 'url' in fmt:
                    return fmt['url']
    
    # Try formats array directly
    if 'formats' in info and info['formats']:
        # Get best audio format
        for fmt in reversed(info['formats']):
            if fmt.get('acodec') != 'none' and 'url' in fmt:
                return fmt['url']
    
    # Try requested formats
    if 'requested_formats' in info:
        for fmt in info['requested_formats']:
            if fmt.get('acodec') != 'none' and 'url' in fmt:
                return fmt['url']
    
    return None


async def play_station(voice_client: discord.VoiceClient, station: dict, volume: float = 1.0) -> bool:
    """
    Play a single music station in a voice channel.
    
    Args:
        voice_client: Connected Discord voice client
        station: Station dictionary with 'url' and 'name'
        volume: Volume level (0.0-1.0)
    
    Returns:
        True if playback started successfully, False otherwise
    """
    try:
        import yt_dlp
        
        if not voice_client or not voice_client.is_connected():
            logger.error("Voice client not connected")
            return False
        
        # Stop any currently playing audio
        if voice_client.is_playing():
            voice_client.stop()
        
        # Extract audio URL using yt-dlp
        logger.info(f"Extracting stream URL: {station['url']}")
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(station['url'], download=False)
            audio_url = extract_audio_url(info)
        
        if not audio_url:
            logger.error(f"Could not extract audio URL from: {station['url']}")
            return False
        
        # Create audio source with volume control
        volume_filter = f'volume={volume}'
        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': f'-vn -af "{volume_filter}"'
        }
        audio_source = discord.FFmpegPCMAudio(audio_url, **ffmpeg_options)
        
        # Play audio
        voice_client.play(
            audio_source,
            after=lambda e: logger.error(f"Playback error: {e}") if e else None
        )
        
        logger.info(f"Started playback: {station['name']}")
        return True
        
    except ImportError:
        logger.error("yt-dlp not installed. Install with: pip install yt-dlp")
        return False
    except Exception as e:
        logger.error(f"Error playing station: {e}", exc_info=True)
        return False


async def play_mixed_stations(voice_client: discord.VoiceClient, stations: List[dict], volumes: Optional[List[float]] = None) -> bool:
    """
    Play multiple stations mixed together.
    
    Args:
        voice_client: Connected Discord voice client
        stations: List of station dictionaries
        volumes: Optional list of volume levels for each station
    
    Returns:
        True if playback started successfully, False otherwise
    """
    try:
        if not voice_client or not voice_client.is_connected():
            logger.error("Voice client not connected")
            return False
        
        # Stop any currently playing audio
        if voice_client.is_playing():
            voice_client.stop()
        
        # Create mixed audio source
        audio_source = await create_mixed_audio_source(stations, volumes)
        
        if not audio_source:
            logger.error("Failed to create mixed audio source")
            return False
        
        # Play mixed audio
        voice_client.play(
            audio_source,
            after=lambda e: logger.error(f"Mixed playback error: {e}") if e else None
        )
        
        station_names = ', '.join([s['name'] for s in stations])
        logger.info(f"Started mixed playback: {station_names}")
        return True
        
    except Exception as e:
        logger.error(f"Error playing mixed stations: {e}", exc_info=True)
        return False


async def play_lofi(voice_client: discord.VoiceClient, stream_index: int = 0) -> bool:
    """
    Play lofi music stream in a voice channel (backward compatibility).
    
    Args:
        voice_client: Connected Discord voice client
        stream_index: Index of lofi stream to play (0 or 1)
    
    Returns:
        True if playback started successfully, False otherwise
    """
    lofi_stations = get_stations_by_type("lofi")
    if not lofi_stations:
        return False
    
    station = lofi_stations[stream_index % len(lofi_stations)]
    return await play_station(voice_client, station)


async def stop_lofi(voice_client: discord.VoiceClient) -> bool:
    """
    Stop lofi music playback.
    
    Args:
        voice_client: Connected Discord voice client
    
    Returns:
        True if stopped successfully, False otherwise
    """
    try:
        if not voice_client or not voice_client.is_connected():
            return False
        
        if voice_client.is_playing():
            voice_client.stop()
            logger.info("Stopped music playback")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error stopping music: {e}")
        return False


async def check_voice_channel_empty(voice_client: discord.VoiceClient) -> bool:
    """
    Check if the bot is alone in the voice channel (excluding bots).
    
    Args:
        voice_client: Connected Discord voice client
    
    Returns:
        True if alone, False otherwise
    """
    if not voice_client or not voice_client.is_connected() or not voice_client.channel:
        return True
    
    # Count human members
    human_members = [m for m in voice_client.channel.members if not m.bot]
    return len(human_members) == 0


async def auto_disconnect_check(guild_id: int, voice_client: discord.VoiceClient):
    """
    Background task to check if bot should auto-disconnect from empty voice channel.
    Waits 2 minutes before disconnecting to avoid rapid join/leave cycles.
    
    Args:
        guild_id: Guild ID for tracking
        voice_client: Voice client to monitor
    """
    try:
        # Wait 2 minutes before checking
        await asyncio.sleep(120)
        
        # Check if still alone
        if await check_voice_channel_empty(voice_client):
            logger.info(f"Auto-disconnecting from empty voice channel in guild {guild_id}")
            await stop_lofi(voice_client)
            await leave_voice_channel(voice_client)
            
            # Clean up session tracking
            if guild_id in active_sessions:
                del active_sessions[guild_id]
        
    except Exception as e:
        logger.error(f"Error in auto-disconnect check: {e}", exc_info=True)


def start_auto_disconnect_check(guild_id: int, voice_client: discord.VoiceClient):
    """
    Start an auto-disconnect check task for a guild.
    
    Args:
        guild_id: Guild ID
        voice_client: Voice client to monitor
    """
    # Cancel existing task if any
    if guild_id in active_sessions and 'auto_disconnect_task' in active_sessions[guild_id]:
        task = active_sessions[guild_id]['auto_disconnect_task']
        if task and not task.done():
            task.cancel()
    
    # Start new task
    task = asyncio.create_task(auto_disconnect_check(guild_id, voice_client))
    
    if guild_id not in active_sessions:
        active_sessions[guild_id] = {}
    active_sessions[guild_id]['auto_disconnect_task'] = task
    active_sessions[guild_id]['voice_client'] = voice_client


def cancel_auto_disconnect(guild_id: int):
    """
    Cancel auto-disconnect task for a guild (when someone joins).
    
    Args:
        guild_id: Guild ID
    """
    if guild_id in active_sessions and 'auto_disconnect_task' in active_sessions[guild_id]:
        task = active_sessions[guild_id]['auto_disconnect_task']
        if task and not task.done():
            task.cancel()
        active_sessions[guild_id]['auto_disconnect_task'] = None


def should_auto_disconnect(voice_client: discord.VoiceClient) -> bool:
    """
    Check if bot should start auto-disconnect timer.
    
    Note: This function is synchronous and returns a bool.
    For async checking, use check_voice_channel_empty() directly.
    
    Args:
        voice_client: Voice client to check
    
    Returns:
        True if should start disconnect timer (basic check)
    """
    if not voice_client or not voice_client.is_connected():
        return False
    
    # Basic synchronous check - for full check use check_voice_channel_empty()
    if not voice_client.channel:
        return True
    
    # Count human members synchronously
    human_members = [m for m in voice_client.channel.members if not m.bot]
    return len(human_members) == 0


async def join_voice_channel(channel: discord.VoiceChannel) -> Optional[discord.VoiceClient]:
    """
    Join a voice channel.
    
    Args:
        channel: Voice channel to join
    
    Returns:
        VoiceClient if successful, None otherwise
    """
    try:
        # Check if already connected to this channel
        if channel.guild.voice_client:
            if channel.guild.voice_client.channel.id == channel.id:
                # Already in this channel - cancel auto-disconnect if active
                cancel_auto_disconnect(channel.guild.id)
                return channel.guild.voice_client
            else:
                # Move to the new channel
                await channel.guild.voice_client.move_to(channel)
                cancel_auto_disconnect(channel.guild.id)
                return channel.guild.voice_client
        
        # Connect to channel
        voice_client = await channel.connect()
        logger.info(f"Joined voice channel: {channel.name}")
        
        # Check if should start auto-disconnect
        if await check_voice_channel_empty(voice_client):
            start_auto_disconnect_check(channel.guild.id, voice_client)
        
        return voice_client
        
    except discord.ClientException as e:
        logger.error(f"Already connected to a voice channel: {e}")
        return channel.guild.voice_client
    except discord.opus.OpusNotLoaded:
        logger.error("Opus library not loaded - voice features unavailable")
        return None
    except Exception as e:
        logger.error(f"Error joining voice channel: {e}", exc_info=True)
        return None


async def leave_voice_channel(voice_client: discord.VoiceClient) -> bool:
    """
    Leave a voice channel.
    
    Args:
        voice_client: Connected Discord voice client
    
    Returns:
        True if left successfully, False otherwise
    """
    try:
        if not voice_client:
            return False
        
        guild_id = voice_client.guild.id if voice_client.guild else None
        
        if voice_client.is_connected():
            await voice_client.disconnect()
            logger.info("Left voice channel")
            
            # Clean up session tracking
            if guild_id and guild_id in active_sessions:
                # Cancel auto-disconnect task
                cancel_auto_disconnect(guild_id)
                del active_sessions[guild_id]
            
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error leaving voice channel: {e}")
        return False


async def on_voice_state_update_handler(voice_client: discord.VoiceClient, guild_id: int):
    """
    Handler to be called when voice state updates occur.
    Manages auto-disconnect logic.
    
    Args:
        voice_client: Voice client that may need checking
        guild_id: Guild ID
    """
    if not voice_client or not voice_client.is_connected():
        return
    
    # Check if alone
    if await check_voice_channel_empty(voice_client):
        # Start auto-disconnect timer if not already running
        if guild_id not in active_sessions or 'auto_disconnect_task' not in active_sessions[guild_id] or \
           active_sessions[guild_id]['auto_disconnect_task'] is None or \
           active_sessions[guild_id]['auto_disconnect_task'].done():
            start_auto_disconnect_check(guild_id, voice_client)
    else:
        # Someone is here, cancel auto-disconnect
        cancel_auto_disconnect(guild_id)


async def generate_spotify_mix_station(user_id: int, username: str) -> Optional[dict]:
    """
    Generate a personalized station based on user's unified listening history.
    Creates a YouTube search URL based on most played artists/songs.
    Now uses both bot playback history and Spotify history for better variety.
    
    Args:
        user_id: Discord user ID
        username: Discord username
    
    Returns:
        Station dictionary or None if no history available
    """
    try:
        # Import db_helpers to get unified history
        from modules.db_helpers import get_unified_music_history
        
        # Get user's unified music history
        history = await get_unified_music_history(user_id, limit=50)
        
        if not history or len(history) == 0:
            logger.info(f"No music history found for user {username}")
            return None
        
        # Get top songs (already sorted by play count)
        top_songs = history[:5]  # Get top 5 most played songs
        
        # Create a search query from top songs
        if top_songs:
            # Use the most played song
            top_song = top_songs[0]
            song_title = top_song['title']
            artist = top_song['artist']
            
            # Create a YouTube search URL
            # We'll use a playlist search for similar music
            search_query = f"{artist} {song_title}"
            search_url = f"ytsearch:{search_query} mix playlist"
            
            station = {
                "name": f"🎧 {username}'s Mix",
                "url": search_url,
                "type": "spotify_mix",
                "based_on": f"{song_title} by {artist}"
            }
            
            logger.info(f"Generated mix station for {username} based on: {song_title} by {artist}")
            return station
        
        return None
        
    except Exception as e:
        logger.error(f"Error generating mix station: {e}", exc_info=True)
        return None


async def get_spotify_recently_played(user_id: int) -> Optional[List[dict]]:
    """
    Get recently played songs from user's unified music history.
    Uses both bot playback and Spotify history for better variety.
    
    Args:
        user_id: Discord user ID
    
    Returns:
        List of song dictionaries with title and artist, or None
    """
    try:
        from modules.db_helpers import get_unified_music_history
        
        history = await get_unified_music_history(user_id, limit=50)
        if not history:
            return None
        
        # Already sorted by play count, take top songs
        songs = []
        for entry in history[:10]:  # Get top 10
            songs.append({
                "title": entry['title'],
                "artist": entry['artist'],
                "url": entry.get('url'),  # May be None
                "play_count": entry['play_count']
            })
        
        return songs if songs else None
        
    except Exception as e:
        logger.error(f"Error getting recently played: {e}", exc_info=True)
        return None


async def search_youtube_song(song_title: str, artist: str) -> Optional[str]:
    """
    Search for a song on YouTube and return the video URL.
    
    Args:
        song_title: Song title
        artist: Artist name
    
    Returns:
        YouTube video URL or None
    """
    try:
        import yt_dlp
        from urllib.parse import quote
        
        # Use URL encoding instead of regex to preserve more characters
        # This handles special characters safely while keeping apostrophes, etc.
        safe_artist = artist.strip()
        safe_title = song_title.strip()
        
        # Limit length to prevent extremely long queries
        safe_artist = safe_artist[:100]
        safe_title = safe_title[:100]
        
        search_query = f"{safe_artist} {safe_title}"
        search_url = f"ytsearch1:{search_query}"  # ytsearch1 returns only first result
        
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(search_url, download=False)
            
            # Extract URL from search result
            if info and 'entries' in info and info['entries']:
                video_info = info['entries'][0]
                video_id = video_info.get('id')
                if video_id:
                    return f"https://www.youtube.com/watch?v={video_id}"
        
        return None
        
    except Exception as e:
        logger.error(f"Error searching YouTube for {artist} - {song_title}: {e}")
        return None


async def get_related_songs(video_url: str, count: int = 5) -> List[dict]:
    """
    Get related/recommended songs from a YouTube video.
    Uses yt-dlp to extract related videos as recommendations.
    
    Args:
        video_url: YouTube video URL
        count: Number of related songs to get
    
    Returns:
        List of song dictionaries with title and url
    """
    try:
        import yt_dlp
        
        # Use modified options to get related videos
        ydl_options = {**YDL_OPTIONS, 'extract_flat': True}
        
        with yt_dlp.YoutubeDL(ydl_options) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            related_songs = []
            
            # Try to get related videos from various fields
            # Note: YouTube API changes may affect availability
            if info:
                # Method 1: Check for related videos in info
                # This may not always be available depending on yt-dlp version
                
                # Method 2: Use search with similar query
                title = info.get('title', '')
                uploader = info.get('uploader', '')
                
                if title:
                    # Search for similar songs
                    search_query = f"{title} {uploader} similar"
                    search_url = f"ytsearch{count}:{search_query}"
                    
                    search_info = ydl.extract_info(search_url, download=False)
                    
                    if search_info and 'entries' in search_info:
                        for entry in search_info['entries'][:count]:
                            if entry and entry.get('id'):
                                related_songs.append({
                                    'title': entry.get('title', 'Unknown'),
                                    'url': f"https://www.youtube.com/watch?v={entry['id']}",
                                    'artist': entry.get('uploader', 'Unknown')
                                })
            
            return related_songs
        
    except Exception as e:
        logger.error(f"Error getting related songs: {e}")
        return []


async def play_song_with_queue(
    voice_client: discord.VoiceClient,
    song: dict,
    guild_id: int,
    volume: float = 1.0,
    user_id: int = None
) -> bool:
    """
    Play a song and set up queue to play next song when finished.
    Tracks song playback in music history.
    
    Args:
        voice_client: Connected Discord voice client
        song: Song dictionary with 'url' or 'title'/'artist'
        guild_id: Guild ID for session tracking
        volume: Volume level (0.0-1.0)
        user_id: Optional Discord user ID for history tracking
    
    Returns:
        True if playback started successfully, False otherwise
    """
    try:
        import yt_dlp
        
        if not voice_client or not voice_client.is_connected():
            logger.error("Voice client not connected")
            return False
        
        # Stop any currently playing audio
        if voice_client.is_playing():
            voice_client.stop()
        
        # Get song URL if we have title/artist instead
        if 'url' not in song or not song['url']:
            if 'title' in song and 'artist' in song:
                song_url = await search_youtube_song(song['title'], song['artist'])
                if not song_url:
                    logger.error(f"Could not find song: {song['artist']} - {song['title']}")
                    return False
                song['url'] = song_url
            else:
                logger.error("Song missing URL and title/artist")
                return False
        
        # Extract audio URL using yt-dlp
        logger.info(f"Extracting audio URL for: {song.get('title', song['url'])}")
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(song['url'], download=False)
            audio_url = extract_audio_url(info)
            
            # Extract song info if not provided
            if 'title' not in song and info:
                song['title'] = info.get('title', 'Unknown')
            if 'artist' not in song and info:
                song['artist'] = info.get('uploader', 'Unknown')
        
        if not audio_url:
            logger.error(f"Could not extract audio URL from: {song['url']}")
            return False
        
        # Get related songs for queue (vary the selection)
        related_songs = await get_related_songs(song['url'], count=10)
        
        # Store in active session
        if guild_id not in active_sessions:
            active_sessions[guild_id] = {}
        
        # Shuffle related songs for variety
        import random
        random.shuffle(related_songs)
        
        active_sessions[guild_id]['queue'] = related_songs
        active_sessions[guild_id]['current_song'] = song
        active_sessions[guild_id]['volume'] = volume
        active_sessions[guild_id]['failure_count'] = 0  # Reset failure count on success
        active_sessions[guild_id]['user_id'] = user_id  # Track user for history
        active_sessions[guild_id]['song_start_time'] = asyncio.get_event_loop().time()  # Track start time
        
        # Track in music history
        if user_id:
            from modules.db_helpers import add_music_history
            await add_music_history(
                user_id=user_id,
                song_title=song.get('title', 'Unknown'),
                song_artist=song.get('artist', 'Unknown'),
                song_url=song.get('url'),
                source='bot'
            )
        
        # Create audio source with volume control
        volume_filter = f'volume={volume}'
        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': f'-vn -af "{volume_filter}"'
        }
        audio_source = discord.FFmpegPCMAudio(audio_url, **ffmpeg_options)
        
        # Define after callback to play next song
        def after_callback(error):
            if error:
                logger.error(f"Playback error: {error}")
                # Increment failure count on error
                if guild_id in active_sessions:
                    active_sessions[guild_id]['failure_count'] = active_sessions[guild_id].get('failure_count', 0) + 1
            
            # Schedule next song using asyncio (whether error or not)
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                
                # Calculate duration if tracking
                if guild_id in active_sessions and 'song_start_time' in active_sessions[guild_id]:
                    duration = int(loop.time() - active_sessions[guild_id]['song_start_time'])
                    # Update music history with duration if we have user_id
                    if user_id and duration > 0:
                        # We can't easily update the last entry, so we'll just log it
                        logger.debug(f"Song played for {duration} seconds")
                
                # Play next song
                asyncio.run_coroutine_threadsafe(
                    play_next_in_queue(voice_client, guild_id),
                    loop
                )
            except Exception as e:
                logger.error(f"Error scheduling next song: {e}")
        
        # Play audio with callback
        voice_client.play(audio_source, after=after_callback)
        
        logger.info(f"Started playback: {song.get('title', 'Unknown')} by {song.get('artist', 'Unknown')}")
        return True
        
    except ImportError:
        logger.error("yt-dlp not installed. Install with: pip install yt-dlp")
        return False
    except Exception as e:
        logger.error(f"Error playing song with queue: {e}", exc_info=True)
        return False


async def play_next_in_queue(voice_client: discord.VoiceClient, guild_id: int) -> bool:
    """
    Play the next song in the queue.
    
    Args:
        voice_client: Connected Discord voice client
        guild_id: Guild ID
    
    Returns:
        True if next song started, False otherwise
    """
    try:
        if guild_id not in active_sessions or 'queue' not in active_sessions[guild_id]:
            logger.info("No queue found, stopping playback")
            return False
        
        # Check failure count to prevent infinite recursion
        failure_count = active_sessions[guild_id].get('failure_count', 0)
        if failure_count >= MAX_QUEUE_FAILURES:
            logger.warning(f"Reached maximum failures ({MAX_QUEUE_FAILURES}), stopping queue")
            return False
        
        queue = active_sessions[guild_id]['queue']
        volume = active_sessions[guild_id].get('volume', 1.0)
        
        if not queue:
            logger.info("Queue empty, stopping playback")
            return False
        
        # Get next song (pop from front)
        next_song = queue.pop(0)
        
        # Play it - but check if voice client is still connected
        if not voice_client or not voice_client.is_connected():
            logger.info("Voice client disconnected, stopping playback")
            return False
        
        # Play with queue system
        success = await play_song_with_queue(voice_client, next_song, guild_id, volume)
        
        if not success:
            logger.warning(f"Failed to play next song, incrementing failure count")
            # Increment failure count and try next song
            active_sessions[guild_id]['failure_count'] = failure_count + 1
            
            # If there are more songs in queue, try the next one
            if queue:
                return await play_next_in_queue(voice_client, guild_id)
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error playing next in queue: {e}", exc_info=True)
        return False


async def start_spotify_queue(
    voice_client: discord.VoiceClient,
    user_id: int,
    guild_id: int,
    volume: float = 1.0
) -> bool:
    """
    Start playing from user's Spotify recently played with automatic queue.
    
    Args:
        voice_client: Connected Discord voice client
        user_id: Discord user ID
        guild_id: Guild ID
        volume: Volume level (0.0-1.0)
    
    Returns:
        True if started successfully, False otherwise
    """
    try:
        # Get recently played songs
        recent_songs = await get_spotify_recently_played(user_id)
        
        if not recent_songs:
            logger.info(f"No Spotify history for user {user_id}")
            return False
        
        # Start with most played song
        first_song = recent_songs[0]
        
        # Play it with queue, passing user_id for tracking
        return await play_song_with_queue(voice_client, first_song, guild_id, volume, user_id)
        
    except Exception as e:
        logger.error(f"Error starting Spotify queue: {e}", exc_info=True)
        return False

