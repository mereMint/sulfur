"""
Lofi Music Player Module for Sulfur Bot

Provides lofi music streaming capabilities using yt-dlp and Discord voice.
Can be used standalone or integrated with focus timer.
Supports multiple station types, audio mixing, and auto-disconnect.
"""

import asyncio
import random
import discord
from typing import Optional, Dict, List
from modules.logger_utils import bot_logger as logger

# Music stations dictionary - organized by type
# Each station can have alternatives in case the primary URL is unavailable
MUSIC_STATIONS = {
    "lofi": [
        {
            "name": "📚 Beats to Relax/Study",
            "url": "https://www.youtube.com/watch?v=jfKfPfyJRdk",
            "type": "lofi",
            "alternatives": [
                "https://www.youtube.com/watch?v=5qap5aO4i9A",  # lofi hip hop radio
                "https://www.youtube.com/watch?v=lTRiuFIWV54"   # study music
            ]
        },
        {
            "name": "🎧 Beats to Sleep/Chill",
            "url": "https://www.youtube.com/watch?v=rUxyKA_-grg",
            "type": "lofi",
            "alternatives": [
                "https://www.youtube.com/watch?v=DWcJFNfaw9c",  # relaxing music
                "https://www.youtube.com/watch?v=7NOSDKb0HlU"   # chill beats
            ]
        }
    ],
    "nocopyright": [
        {
            "name": "🎵 No Copyright Music",
            "url": "https://www.youtube.com/watch?v=7NOSDKb0HlU",
            "type": "nocopyright",
            "alternatives": [
                "https://www.youtube.com/watch?v=lTRiuFIWV54",
                "https://www.youtube.com/watch?v=K4DyBUG242c"
            ]
        },
        {
            "name": "🎸 Royalty Free Music",
            "url": "https://www.youtube.com/watch?v=lTRiuFIWV54",
            "type": "nocopyright",
            "alternatives": [
                "https://www.youtube.com/watch?v=K4DyBUG242c",
                "https://www.youtube.com/watch?v=7NOSDKb0HlU"
            ]
        }
    ],
    "ambient": [
        {
            "name": "🌧️ Rain Sounds",
            "url": "https://www.youtube.com/watch?v=mPZkdNFkNps",
            "type": "ambient",
            "alternatives": [
                "https://www.youtube.com/watch?v=q76bMs-NwRk",
                "https://www.youtube.com/watch?v=nDq6TstdEi8"
            ]
        },
        {
            "name": "🌊 Ocean Waves",
            "url": "https://www.youtube.com/watch?v=WHPEKLQID4U",
            "type": "ambient",
            "alternatives": [
                "https://www.youtube.com/watch?v=V1bFr2SWP1I",
                "https://www.youtube.com/watch?v=bn9F19Hi1Lk"
            ]
        },
        {
            "name": "🔥 Fireplace Sounds",
            "url": "https://www.youtube.com/watch?v=UgHKb_7884o",
            "type": "ambient",
            "alternatives": [
                "https://www.youtube.com/watch?v=eyU3bRy2x44",
                "https://www.youtube.com/watch?v=L_LUpnjgPso"
            ]
        },
        {
            "name": "☕ Coffee Shop Ambience",
            "url": "https://www.youtube.com/watch?v=h2zkV-l_TbY",
            "type": "ambient",
            "alternatives": [
                "https://www.youtube.com/watch?v=gaJXeMGDCeE",
                "https://www.youtube.com/watch?v=5Qv2Aw0BGww"
            ]
        },
        {
            "name": "🌳 Forest Sounds",
            "url": "https://www.youtube.com/watch?v=eKFTSSKCzWA",
            "type": "ambient",
            "alternatives": [
                "https://www.youtube.com/watch?v=xNN7iTA57jM",
                "https://www.youtube.com/watch?v=d0tU18Ybcvk"
            ]
        }
    ],
    "noise": [
        {
            "name": "⚪ White Noise",
            "url": "https://www.youtube.com/watch?v=nMfPqeZjc2c",
            "type": "noise",
            "alternatives": [
                "https://www.youtube.com/watch?v=wzjWIxXBs_s",
                "https://www.youtube.com/watch?v=ArwcHjmsw3A"
            ]
        },
        {
            "name": "🎀 Pink Noise",
            "url": "https://www.youtube.com/watch?v=ZXtimhT-ff4",
            "type": "noise",
            "alternatives": [
                "https://www.youtube.com/watch?v=YoNhkapEgy8",
                "https://www.youtube.com/watch?v=oWOJfFkym8w"
            ]
        },
        {
            "name": "🟤 Brown Noise",
            "url": "https://www.youtube.com/watch?v=RqzGzwTY-6w",
            "type": "noise",
            "alternatives": [
                "https://www.youtube.com/watch?v=GSaJXDsb3N8",
                "https://www.youtube.com/watch?v=FcWgjCDPiP4"
            ]
        },
        {
            "name": "🌊 Blue Noise",
            "url": "https://www.youtube.com/watch?v=H0JcLOE-pXY",
            "type": "noise",
            "alternatives": [
                "https://www.youtube.com/watch?v=x3SLP4b8H7c",
                "https://www.youtube.com/watch?v=vAupipbJJ2M"
            ]
        },
        {
            "name": "🔇 Grey Noise",
            "url": "https://www.youtube.com/watch?v=_vb4nzF4VFA",
            "type": "noise",
            "alternatives": [
                "https://www.youtube.com/watch?v=1KaOrSuWZeM",
                "https://www.youtube.com/watch?v=9sHfAfbmfiM"
            ]
        }
    ]
}

# Active playback sessions per guild
# Format: {guild_id: {'voice_client': VoiceClient, 'stations': [station_configs], 'auto_disconnect_task': Task, 'queue': list, 'failure_count': int, 'preloaded_song': dict, 'sleep_timer_task': Task}}
active_sessions: Dict[int, dict] = {}

# Sleep timers per guild
# Format: {guild_id: {'task': Task, 'end_time': float, 'duration_minutes': int}}
sleep_timers: Dict[int, dict] = {}

# Preloaded song cache for faster playback
# Format: {song_url: {'audio_url': str, 'title': str, 'artist': str, 'duration': int, 'timestamp': float}}
preload_cache: Dict[str, dict] = {}
PRELOAD_CACHE_MAX_SIZE = 50  # Maximum number of preloaded songs
PRELOAD_CACHE_TTL = 3600  # Cache TTL in seconds (1 hour)

# Maximum consecutive failures before stopping queue
MAX_QUEUE_FAILURES = 3

# Queue building constants
TARGET_QUEUE_SIZE = 80  # Total songs in queue (~4-5 hours of playback)
HISTORY_PERCENTAGE = 0.75  # 75% history, 25% AI
HISTORY_REPEAT_COUNT = 8  # For history-only mode
TOP_SONGS_POOL_SIZE = 5  # Number of top songs to randomly select from for first song
MIN_REPEAT_SPACING = 10  # Minimum songs between playing same song again

# Album search constants
MAX_INDIVIDUAL_SONG_DURATION = 1800  # 30 minutes - songs longer than this are likely full albums
SKIP_KEYWORDS = ['compilation', 'reaction', 'cover', 'tutorial', 'review', 
                 'karaoke', 'instrumental', 'remix', 'mashup', 'live at']

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
                info = await asyncio.to_thread(ydl.extract_info, stations[0]['url'], False)
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
            info = await asyncio.to_thread(ydl.extract_info, stations[0]['url'], False)
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


async def check_station_availability(station: dict) -> bool:
    """
    Check if a music station URL is available and working.
    
    Args:
        station: Station dictionary with 'url'
    
    Returns:
        True if available, False otherwise
    """
    try:
        import yt_dlp
        
        # Quick check without downloading
        ydl_options = {**YDL_OPTIONS, 'skip_download': True, 'quiet': True}
        
        with yt_dlp.YoutubeDL(ydl_options) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, station['url'], False)
            audio_url = extract_audio_url(info)
            
            if audio_url:
                logger.debug(f"Station available: {station.get('name', station['url'])}")
                return True
            else:
                logger.warning(f"Station unavailable: {station.get('name', station['url'])}")
                return False
                
    except Exception as e:
        logger.warning(f"Station check failed for {station.get('name', station['url'])}: {e}")
        return False


async def get_working_station(station: dict) -> Optional[dict]:
    """
    Get a working station URL, checking alternatives if primary fails.
    
    Args:
        station: Station dictionary with 'url' and optional 'alternatives'
    
    Returns:
        Station dict with working URL, or None if none work
    """
    try:
        # Try primary URL first
        if await check_station_availability(station):
            return station
        
        # Try alternatives if available
        alternatives = station.get('alternatives', [])
        if alternatives:
            logger.info(f"Primary URL failed, trying {len(alternatives)} alternatives")
            
            for i, alt_url in enumerate(alternatives, 1):
                alt_station = {**station, 'url': alt_url}
                if await check_station_availability(alt_station):
                    logger.info(f"Alternative {i} works: {alt_url}")
                    return alt_station
        
        logger.error(f"No working URL found for station: {station.get('name')}")
        return None
        
    except Exception as e:
        logger.error(f"Error getting working station: {e}")
        return None


async def play_station(voice_client: discord.VoiceClient, station: dict, volume: float = 1.0) -> bool:
    """
    Play a single music station in a voice channel.
    Automatically tries alternatives if primary URL fails.
    
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
        
        # Get working station (tries alternatives if needed)
        working_station = await get_working_station(station)
        if not working_station:
            logger.error(f"No working URL for station: {station.get('name')}")
            return False
        
        # Extract audio URL using yt-dlp
        logger.info(f"Extracting stream URL: {working_station['url']}")
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, working_station['url'], False)
            audio_url = extract_audio_url(info)
        
        if not audio_url:
            logger.error(f"Could not extract audio URL from: {working_station['url']}")
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


async def get_ai_curated_songs(user_id: int, username: str, count: int = 25) -> Optional[List[dict]]:
    """
    Get AI-curated song recommendations based on user's listening history.
    Uses AI API to analyze taste profile and generate personalized recommendations.
    
    Args:
        user_id: Discord user ID
        username: Discord username for personalization
        count: Number of songs to recommend (default: 25)
    
    Returns:
        List of song dictionaries with title and artist, or None
    """
    try:
        from modules.db_helpers import get_unified_music_history
        from modules.api_helpers import get_ai_response_with_model
        import json
        import os
        
        # Get user's listening history
        history = await get_unified_music_history(user_id, limit=50)
        
        if not history or len(history) == 0:
            logger.info(f"No music history found for user {username}")
            return None
        
        # Build context for AI from listening history
        history_context = []
        for i, song in enumerate(history[:20], 1):  # Use top 20 most played
            history_context.append(f"{i}. {song['title']} by {song['artist']} (played {song['play_count']} times)")
        
        history_text = "\n".join(history_context)
        
        # Create prompt for AI - improved for better accuracy
        prompt = f"""Based on {username}'s music listening history, recommend {count} songs that match their taste profile.

Their top songs (sorted by play count):
{history_text}

Analyze their music taste and recommend {count} NEW songs (NOT already in their history) that they would enjoy. 

IMPORTANT REQUIREMENTS:
1. Recommend songs from similar genres and related artists
2. Choose well-known, popular songs that are easily findable on YouTube
3. Use EXACT official song titles and artist names (no typos or variations)
4. NO remixes, covers, live versions, or acoustic versions
5. NO compilation videos, mashups, or medleys
6. Songs should be 2-7 minutes long (typical song length)
7. Prefer songs from established artists
8. Do NOT recommend songs already in their listening history above

Return ONLY a JSON array with this exact format (no other text, no markdown):
[
  {{"title": "Exact Song Title", "artist": "Exact Artist Name"}},
  ...
]

Double-check that titles and artist names are spelled correctly for YouTube search accuracy."""
        
        # Get AI recommendations
        # Load config to pass to API
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        gemini_key = os.getenv('GEMINI_API_KEY', '')
        openai_key = os.getenv('OPENAI_API_KEY', '')
        
        # Use utility model for recommendations
        model_name = config.get('api', {}).get('gemini', {}).get('utility_model', 'gemini-2.5-flash')
        
        response, error = await get_ai_response_with_model(
            prompt=prompt,
            model_name=model_name,
            config=config,
            gemini_key=gemini_key,
            openai_key=openai_key,
            temperature=0.8  # Slightly higher for creativity
        )
        
        if error or not response:
            logger.error(f"AI curation failed: {error}")
            return None
        
        # Parse AI response
        try:
            # Try to extract JSON from response
            response = response.strip()
            
            # Handle markdown code blocks if present
            if response.startswith('```'):
                response = response.split('```')[1]
                if response.startswith('json'):
                    response = response[4:]
                response = response.strip()
            
            songs = json.loads(response)
            
            if not isinstance(songs, list):
                logger.error("AI response is not a list")
                return None
            
            # Validate and clean recommendations
            curated_songs = []
            for song in songs[:count]:  # Limit to requested count
                if isinstance(song, dict) and 'title' in song and 'artist' in song:
                    curated_songs.append({
                        'title': song['title'].strip(),
                        'artist': song['artist'].strip(),
                        'url': None  # Will be searched on YouTube
                    })
            
            if len(curated_songs) > 0:
                logger.info(f"AI curated {len(curated_songs)} songs for {username}")
                return curated_songs
            else:
                logger.warning("No valid songs in AI response")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.debug(f"AI response was: {response[:500]}")
            return None
        
    except Exception as e:
        logger.error(f"Error getting AI curated songs: {e}", exc_info=True)
        return None



async def search_youtube_song(song_title: str, artist: str, filter_shorts: bool = True) -> Optional[str]:
    """
    Search for a song on YouTube and return the video URL.
    Filters out shorts and non-music content by default.
    
    Args:
        song_title: Song title
        artist: Artist name
        filter_shorts: If True, excludes videos under 2 minutes (likely shorts)
    
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
        
        # Add music-specific keywords to improve search quality
        # Prioritize official audio, lyrics videos, and music over random content
        search_query = f"{safe_artist} {safe_title} official audio lyrics music"
        search_url = f"ytsearch5:{search_query}"  # Get top 5 results to filter
        
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, search_url, False)
            
            # Extract URL from search result
            if info and 'entries' in info and info['entries']:
                # Filter and select best match
                for video_info in info['entries']:
                    if not video_info:
                        continue
                    
                    video_id = video_info.get('id')
                    duration = video_info.get('duration', 0)
                    title = video_info.get('title', '').lower()
                    
                    # Skip if no video ID
                    if not video_id:
                        continue
                    
                    # Filter out shorts (videos under 2 minutes = 120 seconds)
                    if filter_shorts and duration and duration < 120:
                        logger.debug(f"Skipping short video: {title} ({duration}s)")
                        continue
                    
                    # Prefer videos with music-related keywords
                    music_keywords = ['official', 'audio', 'lyrics', 'music', 'video']
                    has_music_keyword = any(keyword in title for keyword in music_keywords)
                    
                    # Skip videos that are clearly not music (compilations, shorts, etc.)
                    bad_keywords = ['#shorts', 'compilation', 'reaction', 'tutorial', 'how to']
                    has_bad_keyword = any(keyword in title for keyword in bad_keywords)
                    
                    if has_bad_keyword:
                        logger.debug(f"Skipping non-music video: {title}")
                        continue
                    
                    # Accept this video
                    logger.info(f"Selected video: {title} ({duration}s)")
                    return f"https://www.youtube.com/watch?v={video_id}"
                
                # If no good match found after filtering, return first result
                if info['entries']:
                    video_id = info['entries'][0].get('id')
                    if video_id:
                        logger.warning(f"No ideal match found, using first result")
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
            info = await asyncio.to_thread(ydl.extract_info, video_url, False)
            
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
                    
                    search_info = await asyncio.to_thread(ydl.extract_info, search_url, False)
                    
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


async def preload_song(song: dict) -> bool:
    """
    Preload a song by extracting its audio URL and caching it.
    
    Args:
        song: Song dictionary with 'url' or 'title'/'artist'
    
    Returns:
        True if preloaded successfully, False otherwise
    """
    try:
        import yt_dlp
        import time
        
        # Get song URL if needed
        song_url = song.get('url')
        if not song_url:
            if 'title' in song and 'artist' in song:
                song_url = await search_youtube_song(song['title'], song['artist'])
                if not song_url:
                    return False
                song['url'] = song_url
            else:
                return False
        
        # Check if already in cache and not expired
        if song_url in preload_cache:
            cached = preload_cache[song_url]
            if time.time() - cached.get('timestamp', 0) < PRELOAD_CACHE_TTL:
                logger.debug(f"Song already in preload cache: {song.get('title', song_url)}")
                return True
        
        # Extract audio URL
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, song_url, False)
            audio_url = extract_audio_url(info)
            
            if not audio_url:
                return False
            
            # Cache the preloaded song data
            preload_cache[song_url] = {
                'audio_url': audio_url,
                'title': info.get('title', song.get('title', 'Unknown')),
                'artist': info.get('uploader', song.get('artist', 'Unknown')),
                'duration': info.get('duration', 0),
                'timestamp': time.time()
            }
            
            # Manage cache size
            if len(preload_cache) > PRELOAD_CACHE_MAX_SIZE:
                # Remove oldest entries
                sorted_cache = sorted(preload_cache.items(), key=lambda x: x[1]['timestamp'])
                for url, _ in sorted_cache[:10]:  # Remove 10 oldest
                    del preload_cache[url]
            
            logger.info(f"Preloaded song: {preload_cache[song_url]['title']}")
            return True
            
    except Exception as e:
        logger.error(f"Error preloading song: {e}")
        return False


async def preload_next_songs(guild_id: int, count: int = 2):
    """
    Preload the next songs in the queue for faster playback.
    
    Args:
        guild_id: Guild ID
        count: Number of songs to preload (default: 2)
    """
    try:
        if guild_id not in active_sessions:
            return
        
        queue = active_sessions[guild_id].get('queue', [])
        if not queue:
            return
        
        # Preload next songs asynchronously (don't wait)
        for song in queue[:count]:
            asyncio.create_task(preload_song(song))
        
        logger.debug(f"Started preloading {min(count, len(queue))} songs for guild {guild_id}")
        
    except Exception as e:
        logger.error(f"Error preloading next songs: {e}")


async def preload_all_stations() -> int:
    """
    Preload all music stations for faster playback.
    Should be called at bot startup.
    
    Returns:
        Number of stations successfully preloaded
    """
    preloaded = 0
    logger.info("Starting to preload all music stations...")
    
    try:
        import yt_dlp
        import time
        
        all_stations = get_all_stations()
        
        for station in all_stations:
            try:
                station_url = station.get('url')
                if not station_url:
                    continue
                
                # Skip if already cached
                if station_url in preload_cache:
                    cached = preload_cache[station_url]
                    if time.time() - cached.get('timestamp', 0) < PRELOAD_CACHE_TTL:
                        preloaded += 1
                        continue
                
                # Extract audio URL
                with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                    info = await asyncio.to_thread(ydl.extract_info, station_url, False)
                    audio_url = extract_audio_url(info)
                    
                    if audio_url:
                        preload_cache[station_url] = {
                            'audio_url': audio_url,
                            'title': info.get('title', station.get('name', 'Unknown')),
                            'artist': info.get('uploader', 'Unknown'),
                            'duration': info.get('duration', 0),
                            'timestamp': time.time()
                        }
                        preloaded += 1
                        logger.debug(f"Preloaded station: {station.get('name', station_url)}")
                
                # Small delay to not overwhelm YouTube
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.warning(f"Failed to preload station {station.get('name', 'Unknown')}: {e}")
                continue
        
        logger.info(f"Preloaded {preloaded}/{len(all_stations)} music stations")
        return preloaded
        
    except Exception as e:
        logger.error(f"Error preloading stations: {e}")
        return preloaded


async def get_album_info(album_name: str, artist: str = None) -> Optional[dict]:
    """
    Get album information and track list from YouTube/Music.
    
    Tries multiple strategies to find individual tracks:
    1. Search for playlist/album with chapters
    2. Search for individual songs from the album
    3. Fall back to single video only if no tracks found
    
    Args:
        album_name: Name of the album
        artist: Optional artist name for better search
    
    Returns:
        Dictionary with album info and tracks, or None
    """
    try:
        import yt_dlp
        
        tracks = []
        album_artist = artist or 'Unknown'
        album_thumbnail = ''
        album_url = ''
        album_duration = 0
        
        # Strategy 1: Try to find YouTube Music playlist or album video with chapters
        search_query = f"{artist} {album_name} full album" if artist else f"{album_name} full album"
        search_url = f"ytsearch1:{search_query}"
        
        ydl_options = {**YDL_OPTIONS, 'extract_flat': False}
        
        with yt_dlp.YoutubeDL(ydl_options) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, search_url, False)
            
            if info and 'entries' in info and info['entries']:
                album_video = info['entries'][0]
                album_url = album_video.get('webpage_url', '')
                album_thumbnail = album_video.get('thumbnail', '')
                album_duration = album_video.get('duration', 0)
                album_artist = artist or album_video.get('uploader', 'Unknown')
                
                # Check if video has chapters - use them as tracks
                if 'chapters' in album_video and album_video['chapters']:
                    for i, chapter in enumerate(album_video['chapters'], 1):
                        track_title = chapter.get('title', f'Track {i}')
                        tracks.append({
                            'track_number': i,
                            'title': sanitize_song_title(track_title),
                            'artist': album_artist,
                            'album': album_name,
                            'start_time': chapter.get('start_time', 0),
                            'end_time': chapter.get('end_time', 0),
                            'url': album_url
                        })
                    logger.info(f"Found {len(tracks)} tracks from chapters for album: {album_name}")
        
        # Strategy 2: If no chapters found, search for individual songs
        if not tracks:
            logger.info(f"No chapters found, searching for individual songs for album: {album_name}")
            
            # Search for multiple songs from the album
            if artist:
                # Try searching for "[artist] [album_name] songs" to get a playlist-like result
                search_queries = [
                    f"{artist} {album_name}",
                    f"{artist} {album_name} songs"
                ]
            else:
                search_queries = [
                    f"{album_name}",
                    f"{album_name} songs"
                ]
            
            # Search for up to 15 individual songs
            ydl_options_flat = {**YDL_OPTIONS, 'extract_flat': True}
            
            with yt_dlp.YoutubeDL(ydl_options_flat) as ydl:
                search_url = f"ytsearch15:{search_queries[0]}"
                info = await asyncio.to_thread(ydl.extract_info, search_url, False)
                
                if info and 'entries' in info and info['entries']:
                    seen_titles = set()
                    
                    for i, entry in enumerate(info['entries'], 1):
                        if not entry:
                            continue
                        
                        video_id = entry.get('id')
                        video_title = entry.get('title', '')
                        video_uploader = entry.get('uploader', '')
                        duration = entry.get('duration', 0)
                        
                        if not video_id:
                            continue
                        
                        # Filter out videos that don't seem related
                        video_title_lower = video_title.lower()
                        
                        # Skip if it looks like a full album video (too long or has "full album" in title)
                        if duration and duration > MAX_INDIVIDUAL_SONG_DURATION:
                            if 'full album' in video_title_lower or 'full ep' in video_title_lower:
                                continue
                        
                        # Skip compilations, reactions, covers, etc.
                        if any(keyword in video_title_lower for keyword in SKIP_KEYWORDS):
                            continue
                        
                        # Create a normalized title for deduplication
                        normalized_title = sanitize_song_title(video_title).lower()
                        
                        if normalized_title in seen_titles:
                            continue
                        seen_titles.add(normalized_title)
                        
                        # Get clean song title
                        clean_title = sanitize_song_title(video_title)
                        
                        tracks.append({
                            'track_number': len(tracks) + 1,
                            'title': clean_title,
                            'artist': artist or video_uploader or album_artist,
                            'album': album_name,
                            'start_time': 0,
                            'end_time': 0,
                            'url': f"https://www.youtube.com/watch?v={video_id}"
                        })
                        
                        # Limit to 12 tracks for individual song searches
                        if len(tracks) >= 12:
                            break
                    
                    logger.info(f"Found {len(tracks)} individual song results for album: {album_name}")
        
        # Strategy 3: If still no tracks, fall back to single video (last resort)
        if not tracks and album_url:
            logger.warning(f"No individual tracks found, using single video for album: {album_name}")
            with yt_dlp.YoutubeDL(ydl_options) as ydl:
                info = await asyncio.to_thread(ydl.extract_info, search_url, False)
                if info and 'entries' in info and info['entries']:
                    album_video = info['entries'][0]
                    tracks.append({
                        'track_number': 1,
                        'title': sanitize_song_title(album_video.get('title', album_name)),
                        'artist': album_artist,
                        'album': album_name,
                        'start_time': 0,
                        'end_time': album_video.get('duration', 0),
                        'url': album_url
                    })
        
        if not tracks:
            return None
        
        album_info = {
            'album_name': album_name,
            'artist': album_artist,
            'tracks': tracks,
            'total_tracks': len(tracks),
            'url': album_url,
            'thumbnail': album_thumbnail,
            'duration': album_duration
        }
        
        logger.info(f"Retrieved album info: {album_name} with {len(tracks)} tracks")
        return album_info
        
    except Exception as e:
        logger.error(f"Error getting album info: {e}")
        return None


async def add_album_to_queue(guild_id: int, album_name: str, artist: str = None) -> int:
    """
    Add all tracks from an album to the queue.
    
    Args:
        guild_id: Guild ID
        album_name: Name of the album
        artist: Optional artist name
    
    Returns:
        Number of tracks added to queue
    """
    try:
        # Get album info
        album_info = await get_album_info(album_name, artist)
        
        if not album_info or not album_info['tracks']:
            logger.warning(f"No tracks found for album: {album_name}")
            return 0
        
        # Add each track to queue
        added_count = 0
        for track in album_info['tracks']:
            # Add track as a song with album metadata
            song = {
                'title': track['title'],
                'artist': track['artist'],
                'album': track['album'],
                'track_number': track['track_number'],
                'url': track['url'],
                'start_time': track.get('start_time', 0),
                'end_time': track.get('end_time', 0)
            }
            
            # Add to queue with duplicate checking
            if add_to_queue(guild_id, song, check_duplicates=True) > 0:
                added_count += 1
        
        logger.info(f"Added {added_count} tracks from album '{album_name}' to queue")
        return added_count
        
    except Exception as e:
        logger.error(f"Error adding album to queue: {e}")
        return 0


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
        import time
        
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
        
        # Check if song is in preload cache
        song_url = song['url']
        audio_url = None
        
        if song_url in preload_cache:
            cached = preload_cache[song_url]
            # Check if cache is still valid
            if time.time() - cached.get('timestamp', 0) < PRELOAD_CACHE_TTL:
                audio_url = cached['audio_url']
                if 'title' not in song:
                    song['title'] = cached['title']
                if 'artist' not in song:
                    song['artist'] = cached['artist']
                logger.info(f"Using preloaded audio for: {song.get('title', 'Unknown')}")
            else:
                # Cache expired, remove it
                del preload_cache[song_url]
        
        # If not in cache, extract audio URL
        if not audio_url:
            logger.info(f"Extracting audio URL for: {song.get('title', song_url)}")
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                info = await asyncio.to_thread(ydl.extract_info, song_url, False)
                audio_url = extract_audio_url(info)
            
            # Extract song info if not provided
            if 'title' not in song and info:
                song['title'] = info.get('title', 'Unknown')
            if 'artist' not in song and info:
                song['artist'] = info.get('uploader', 'Unknown')
        
        if not audio_url:
            logger.error(f"Could not extract audio URL from: {song['url']}")
            return False
        
        # Store in active session
        if guild_id not in active_sessions:
            active_sessions[guild_id] = {}
        
        # Only generate related songs if no queue exists
        # This allows pre-built queues (like Spotify mix) to be preserved
        if 'queue' not in active_sessions[guild_id] or not active_sessions[guild_id]['queue']:
            # Get related songs for queue (vary the selection)
            related_songs = await get_related_songs(song['url'], count=10)
            # Shuffle related songs for variety
            random.shuffle(related_songs)
            active_sessions[guild_id]['queue'] = related_songs
        # If queue already exists, keep it (don't overwrite)
        active_sessions[guild_id]['current_song'] = song
        active_sessions[guild_id]['volume'] = volume
        active_sessions[guild_id]['failure_count'] = 0  # Reset failure count on success
        active_sessions[guild_id]['user_id'] = user_id  # Track user for history
        
        # Store event loop reference for callback thread
        try:
            loop = asyncio.get_running_loop()
            active_sessions[guild_id]['event_loop'] = loop
            active_sessions[guild_id]['song_start_time'] = loop.time()  # Track start time
        except RuntimeError:
            # Fallback if no running loop
            active_sessions[guild_id]['event_loop'] = asyncio.get_event_loop()
            active_sessions[guild_id]['song_start_time'] = active_sessions[guild_id]['event_loop'].time()
        
        # Track in music history
        if user_id:
            from modules.db_helpers import add_music_history
            # Determine source - check if this is an AI-curated song
            source = song.get('source', 'bot')
            await add_music_history(
                user_id=user_id,
                song_title=song.get('title', 'Unknown'),
                song_artist=song.get('artist', 'Unknown'),
                song_url=song.get('url'),
                source=source,  # Will be 'ai' for AI-curated songs
                album=song.get('album')
            )
        
        # Create audio source with volume control and optional timestamp handling for album tracks
        volume_filter = f'volume={volume}'
        
        # Handle album tracks with start/end timestamps (sanitize and validate inputs)
        before_options = '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
        MAX_TIMESTAMP = 86400  # 24 hours max to prevent resource exhaustion
        
        if 'start_time' in song and isinstance(song['start_time'], (int, float)) and song['start_time'] > 0:
            # Ensure start_time is a valid number within reasonable bounds
            start_time = min(float(song['start_time']), MAX_TIMESTAMP)
            before_options += f" -ss {start_time}"
            logger.info(f"Starting playback from {start_time}s for track: {song.get('title', 'Unknown')}")
        
        ffmpeg_options_dict = {
            'before_options': before_options,
            'options': f'-vn -af "{volume_filter}"'
        }
        
        # Add duration limit if end_time is specified (for album tracks)
        if ('end_time' in song and isinstance(song['end_time'], (int, float)) and 
            'start_time' in song and isinstance(song['start_time'], (int, float)) and 
            song['end_time'] > song['start_time']):
            # Sanitize duration calculation with bounds checking
            duration = min(float(song['end_time']) - float(song['start_time']), MAX_TIMESTAMP)
            ffmpeg_options_dict['options'] = f'-vn -t {duration} -af "{volume_filter}"'
            logger.info(f"Limiting playback duration to {duration}s for track: {song.get('title', 'Unknown')}")
        
        audio_source = discord.FFmpegPCMAudio(audio_url, **ffmpeg_options_dict)
        
        # Define after callback to play next song
        def after_callback(error):
            if error:
                logger.error(f"Playback error: {error}")
                # Increment failure count on error
                if guild_id in active_sessions:
                    active_sessions[guild_id]['failure_count'] = active_sessions[guild_id].get('failure_count', 0) + 1
            
            # Schedule next song using asyncio (whether error or not)
            try:
                # Use stored event loop instead of get_event_loop()
                if guild_id in active_sessions and 'event_loop' in active_sessions[guild_id]:
                    loop = active_sessions[guild_id]['event_loop']
                    
                    # Calculate duration and track listening time
                    if 'song_start_time' in active_sessions[guild_id]:
                        duration_seconds = int(loop.time() - active_sessions[guild_id]['song_start_time'])
                        if duration_seconds > 0:
                            duration_minutes = duration_seconds / 60.0
                            logger.debug(f"Song played for {duration_seconds} seconds ({duration_minutes:.2f} minutes)")
                            
                            # Track listening time for all users in the voice channel
                            current_song = active_sessions[guild_id].get('current_song')
                            if current_song and voice_client:
                                song_title = current_song.get('title', 'Unknown')
                                song_artist = current_song.get('artist', 'Unknown')
                                # Schedule async tracking task
                                asyncio.run_coroutine_threadsafe(
                                    track_listening_time(
                                        voice_client, 
                                        guild_id, 
                                        song_title, 
                                        song_artist, 
                                        duration_minutes
                                    ),
                                    loop
                                )
                    
                    # Play next song
                    asyncio.run_coroutine_threadsafe(
                        play_next_in_queue(voice_client, guild_id),
                        loop
                    )
                else:
                    logger.warning(f"No event loop stored for guild {guild_id}, cannot schedule next song")
            except Exception as e:
                logger.error(f"Error scheduling next song: {e}")
        
        # Play audio with callback
        voice_client.play(audio_source, after=after_callback)
        
        # Start preloading next songs in queue (async, don't wait)
        asyncio.create_task(preload_next_songs(guild_id, count=2))
        
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
        user_id = active_sessions[guild_id].get('user_id')  # Get user_id from session
        
        if not queue:
            logger.info("Queue empty, stopping playback")
            return False
        
        # Shuffle remaining queue for variety after each song
        # Keep the immediate next song (first in queue) stable, shuffle the rest
        if len(queue) > 1:
            # Keep first song, shuffle the rest
            first_song = queue[0]
            remaining = queue[1:]
            random.shuffle(remaining)
            queue = [first_song] + remaining
            active_sessions[guild_id]['queue'] = queue
        
        # Get next song (pop from front)
        next_song = queue.pop(0)
        
        # Play it - but check if voice client is still connected
        if not voice_client or not voice_client.is_connected():
            logger.info("Voice client disconnected, stopping playback")
            return False
        
        # Play with queue system, passing user_id to maintain history tracking
        success = await play_song_with_queue(voice_client, next_song, guild_id, volume, user_id)
        
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


def get_queue_preview(guild_id: int, count: int = 3) -> List[dict]:
    """
    Get the next N songs in the queue without removing them.
    
    Args:
        guild_id: Guild ID
        count: Number of songs to preview (default: 3)
    
    Returns:
        List of song dictionaries from the queue
    """
    try:
        if guild_id not in active_sessions or 'queue' not in active_sessions[guild_id]:
            return []
        
        queue = active_sessions[guild_id]['queue']
        
        # Return up to 'count' songs from the queue
        return queue[:count]
        
    except Exception as e:
        logger.error(f"Error getting queue preview: {e}", exc_info=True)
        return []


def get_current_song(guild_id: int) -> Optional[dict]:
    """
    Get the currently playing song.
    
    Args:
        guild_id: Guild ID
    
    Returns:
        Current song dictionary or None
    """
    try:
        if guild_id not in active_sessions or 'current_song' not in active_sessions[guild_id]:
            return None
        
        return active_sessions[guild_id]['current_song']
        
    except Exception as e:
        logger.error(f"Error getting current song: {e}", exc_info=True)
        return None


def get_queue_length(guild_id: int) -> int:
    """
    Get the length of the current queue.
    
    Args:
        guild_id: Guild ID
    
    Returns:
        Number of songs in queue, or 0 if no queue exists
    """
    try:
        if guild_id not in active_sessions or 'queue' not in active_sessions[guild_id]:
            return 0
        
        return len(active_sessions[guild_id]['queue'])
        
    except Exception as e:
        logger.error(f"Error getting queue length: {e}", exc_info=True)
        return 0


def add_to_queue(guild_id: int, song: dict, check_duplicates: bool = True) -> int:
    """
    Add a song to the queue with optional duplicate checking.
    Also checks against the currently playing song to prevent immediate repeats.
    
    Args:
        guild_id: Guild ID
        song: Song dictionary to add
        check_duplicates: If True, prevents adding duplicate songs
    
    Returns:
        Position in queue (1-indexed), or 0 if failed or duplicate
    """
    try:
        if guild_id not in active_sessions:
            active_sessions[guild_id] = {}
        
        if 'queue' not in active_sessions[guild_id]:
            active_sessions[guild_id]['queue'] = []
        
        # Check for duplicates if enabled
        if check_duplicates:
            queue = active_sessions[guild_id]['queue']
            song_title = song.get('title', '').lower().strip()
            song_artist = song.get('artist', '').lower().strip()
            
            # First check if song matches currently playing song
            current_song = active_sessions[guild_id].get('current_song')
            if current_song:
                current_title = current_song.get('title', '').lower().strip()
                current_artist = current_song.get('artist', '').lower().strip()
                if song_title and current_title and song_title == current_title:
                    if not song_artist or not current_artist or song_artist == current_artist:
                        logger.debug(f"Skipping song that's currently playing: {song.get('title')} by {song.get('artist')}")
                        return 0
            
            # Check if song is already in queue (case-insensitive comparison)
            for existing_song in queue:
                existing_title = existing_song.get('title', '').lower().strip()
                existing_artist = existing_song.get('artist', '').lower().strip()
                
                # Consider it a duplicate if title matches and artist matches (or both empty)
                if song_title and existing_title and song_title == existing_title:
                    if not song_artist or not existing_artist or song_artist == existing_artist:
                        logger.debug(f"Skipping duplicate song in queue: {song.get('title')} by {song.get('artist')}")
                        return 0  # Return 0 to indicate duplicate (not added)
        
        active_sessions[guild_id]['queue'].append(song)
        return len(active_sessions[guild_id]['queue'])
        
    except Exception as e:
        logger.error(f"Error adding to queue: {e}", exc_info=True)
        return 0


def clear_queue(guild_id: int) -> int:
    """
    Clear all songs from the queue.
    
    Args:
        guild_id: Guild ID
    
    Returns:
        Number of songs that were in the queue before clearing
    """
    try:
        if guild_id not in active_sessions or 'queue' not in active_sessions[guild_id]:
            return 0
        
        queue_length = len(active_sessions[guild_id]['queue'])
        active_sessions[guild_id]['queue'] = []
        
        logger.info(f"Cleared queue for guild {guild_id}: {queue_length} songs removed")
        return queue_length
        
    except Exception as e:
        logger.error(f"Error clearing queue: {e}", exc_info=True)
        return 0


def sanitize_song_title(title: str) -> str:
    """
    Sanitize song title by removing common YouTube artifacts.
    
    Args:
        title: Raw song title from YouTube
    
    Returns:
        Cleaned song title
    """
    if not title:
        return "Unknown"
    
    # Remove common patterns
    patterns_to_remove = [
        r'\(Official\s+Audio\)',
        r'\(Official\s+Video\)',
        r'\(Official\s+Music\s+Video\)',
        r'\[Official\s+Audio\]',
        r'\[Official\s+Video\]',
        r'\[Official\s+Music\s+Video\]',
        r'\(Lyrics?\)',
        r'\[Lyrics?\]',
        r'\(HD\)',
        r'\[HD\]',
        r'\(4K\)',
        r'\[4K\]',
        r'\(Visualizer\)',
        r'\[Visualizer\]',
        r'\(Lyric\s+Video\)',
        r'\[Lyric\s+Video\]',
        r'\(Music\s+Video\)',
        r'\[Music\s+Video\]',
        r'\(Audio\)',
        r'\[Audio\]',
        r'\(Explicit\)',
        r'\[Explicit\]',
        r'ft\.\s+.*$',  # Remove featuring artists at end
        r'feat\.\s+.*$',
        r'\|.*$',  # Remove anything after pipe
        r'-\s+Topic$',  # Remove "- Topic" at end
    ]
    
    import re
    cleaned = title
    for pattern in patterns_to_remove:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    
    # Clean up extra whitespace
    cleaned = ' '.join(cleaned.split())
    
    return cleaned.strip() if cleaned.strip() else title


async def start_spotify_queue(
    voice_client: discord.VoiceClient,
    user_id: int,
    guild_id: int,
    volume: float = 1.0
) -> bool:
    """
    Start playing from user's Spotify recently played with automatic queue.
    Now enhanced with AI curation - plays mostly from history with AI-curated songs mixed in.
    
    Strategy:
    - 70-80% songs from user's actual listening history
    - 20-30% AI-curated songs based on taste profile
    - AI generates 25 recommendations that are interleaved with history
    - Ensures no duplicate songs in the queue
    
    Args:
        voice_client: Connected Discord voice client
        user_id: Discord user ID
        guild_id: Guild ID
        volume: Volume level (0.0-1.0)
    
    Returns:
        True if started successfully, False otherwise
    """
    try:
        # Get user's listening history
        recent_songs = await get_spotify_recently_played(user_id)
        
        if not recent_songs:
            logger.info(f"No Spotify history for user {user_id}")
            return False
        
        # Get AI-curated recommendations (25 songs)
        # Get username for AI personalization
        try:
            # Try to get username from voice client
            if voice_client and voice_client.guild:
                member = voice_client.guild.get_member(user_id)
                username = member.display_name if member else f"User {user_id}"
            else:
                username = f"User {user_id}"
        except:
            username = f"User {user_id}"
        
        ai_curated_songs = await get_ai_curated_songs(user_id, username, count=25)
        
        # Build queue with mixed strategy
        queue = []
        seen_songs = set()  # Track seen songs to prevent duplicates
        
        # Helper function to check for duplicates
        def is_duplicate(song, seen):
            song_key = f"{song.get('title', '').lower().strip()}|{song.get('artist', '').lower().strip()}"
            if song_key in seen:
                return True
            seen.add(song_key)
            return False
        
        # Start with a random song from top songs instead of always the same one
        # This provides variety while still favoring popular tracks
        if recent_songs:
            first_song = random.choice(recent_songs[:min(TOP_SONGS_POOL_SIZE, len(recent_songs))]).copy()
            is_duplicate(first_song, seen_songs)  # Add to seen set
        else:
            logger.error("No recent songs available for user")
            return False
        
        # Create extended history pool (repeat top songs for better ratio)
        history_pool = []
        for song in recent_songs:
            history_pool.append(song.copy())
        
        # Add top 5 songs again for higher play probability (but only if not creating immediate duplicates)
        if len(recent_songs) >= 5:
            for song in recent_songs[:5]:
                history_pool.append(song.copy())
        
        random.shuffle(history_pool)
        
        # Build mixed queue (70-80% history, 20-30% AI)
        if ai_curated_songs and len(ai_curated_songs) > 0:
            # Calculate targets based on constants
            target_history = int(TARGET_QUEUE_SIZE * HISTORY_PERCENTAGE)  # 60
            target_ai = TARGET_QUEUE_SIZE - target_history  # 20
            
            # Create history queue with duplicate prevention
            history_queue = []
            for song in history_pool:
                if len(history_queue) >= target_history:
                    break
                if not is_duplicate(song, seen_songs):
                    history_queue.append(song.copy())
            
            # If we need more songs, repeat the cycle with minimum spacing between repeats
            if len(history_pool) > 0 and len(history_queue) < target_history:
                cycles = 0
                max_cycles = 20  # Prevent infinite loop
                while len(history_queue) < target_history and cycles < max_cycles:
                    shuffled_pool = history_pool.copy()
                    random.shuffle(shuffled_pool)
                    for song in shuffled_pool:
                        if len(history_queue) >= target_history:
                            break
                        song_key = f"{song.get('title', '').lower().strip()}|{song.get('artist', '').lower().strip()}"
                        # Check if this song was added too recently
                        can_add = True
                        for i in range(1, min(MIN_REPEAT_SPACING + 1, len(history_queue) + 1)):
                            if i > len(history_queue):
                                break
                            recent_song = history_queue[-i]
                            recent_key = f"{recent_song.get('title', '').lower().strip()}|{recent_song.get('artist', '').lower().strip()}"
                            if song_key == recent_key:
                                can_add = False
                                break
                        if can_add:
                            history_queue.append(song.copy())
                    cycles += 1
            
            # Prepare AI queue with duplicate checking
            ai_queue = []
            for song in ai_curated_songs:
                if not is_duplicate(song, seen_songs):
                    song_copy = song.copy()
                    song_copy['source'] = 'ai'  # Mark as AI-curated for tracking
                    ai_queue.append(song_copy)
            
            random.shuffle(ai_queue)
            
            # Interleave: 3-4 history songs, then 1 AI song
            ai_index = 0
            for i, song in enumerate(history_queue):
                queue.append(song)
                # After every 4 history songs, add 1 AI song
                if (i + 1) % 4 == 0 and ai_index < len(ai_queue):
                    queue.append(ai_queue[ai_index])
                    ai_index += 1
            
            # Add remaining AI songs at the end if any
            while ai_index < len(ai_queue):
                queue.append(ai_queue[ai_index])
                ai_index += 1
            
            logger.info(f"Built queue: {len(history_queue)} history + {len(ai_queue)} AI = {len(queue)} total songs (with spacing)")
        else:
            # No AI curation available, use only history with proper spacing
            logger.info("AI curation not available, using history only")
            cycles = 0
            max_cycles = 20  # Prevent infinite loop
            while len(queue) < TARGET_QUEUE_SIZE and cycles < max_cycles:
                shuffled_pool = history_pool.copy()
                random.shuffle(shuffled_pool)
                for song in shuffled_pool:
                    if len(queue) >= TARGET_QUEUE_SIZE:
                        break
                    song_key = f"{song.get('title', '').lower().strip()}|{song.get('artist', '').lower().strip()}"
                    # Check if this song was added too recently
                    can_add = True
                    for i in range(1, min(MIN_REPEAT_SPACING + 1, len(queue) + 1)):
                        if i > len(queue):
                            break
                        recent_song = queue[-i]
                        recent_key = f"{recent_song.get('title', '').lower().strip()}|{recent_song.get('artist', '').lower().strip()}"
                        if song_key == recent_key:
                            can_add = False
                            break
                    if can_add:
                        queue.append(song.copy())
                cycles += 1
        
        # Play first song with queue, passing user_id for tracking
        success = await play_song_with_queue(voice_client, first_song, guild_id, volume, user_id)
        
        if success and guild_id in active_sessions:
            # Replace the auto-generated queue with our curated queue
            active_sessions[guild_id]['queue'] = queue
            logger.info(f"Started Spotify mix queue with {len(queue)} songs")
        
        return success
        
    except Exception as e:
        logger.error(f"Error starting Spotify queue: {e}", exc_info=True)
        return False


async def track_listening_time(voice_client: discord.VoiceClient, guild_id: int, song_title: str = None, song_artist: str = None, duration_minutes: float = 0.0):
    """
    Track listening time for all users in the voice channel.
    
    Args:
        voice_client: Connected voice client
        guild_id: Guild ID
        song_title: Optional song title
        song_artist: Optional song artist
        duration_minutes: Duration in minutes
    """
    try:
        if not voice_client or not voice_client.is_connected() or not voice_client.channel:
            return
        
        from modules.db_helpers import get_db_connection
        
        # Get all human members in the voice channel
        listeners = [m for m in voice_client.channel.members if not m.bot]
        
        if not listeners:
            return
        
        # Record listening time for each user
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                for member in listeners:
                    try:
                        cursor.execute("""
                            INSERT INTO listening_time 
                            (user_id, guild_id, channel_id, listened_at, duration_minutes, song_title, song_artist)
                            VALUES (%s, %s, %s, NOW(), %s, %s, %s)
                        """, (
                            member.id,
                            guild_id,
                            voice_client.channel.id,
                            duration_minutes,
                            song_title,
                            song_artist
                        ))
                    except Exception as e:
                        logger.error(f"Error tracking listening time for user {member.id}: {e}")
                
                conn.commit()
                logger.debug(f"Tracked listening time for {len(listeners)} users")
        except Exception as e:
            logger.error(f"Error in database operations: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
            
    except Exception as e:
        logger.error(f"Error in track_listening_time: {e}", exc_info=True)


async def get_user_listening_stats(user_id: int) -> dict:
    """
    Get comprehensive listening statistics for a user.
    Combines bot playback history and Spotify history.
    
    Args:
        user_id: Discord user ID
    
    Returns:
        Dictionary with listening stats
    """
    try:
        from modules.db_helpers import get_db_connection, get_unified_music_history
        
        stats = {
            'total_songs': 0,
            'total_listening_time_minutes': 0,
            'favorite_songs': [],
            'favorite_artists': [],
            'recent_songs': [],
            'top_genres': []
        }
        
        # Get unified music history
        history = await get_unified_music_history(user_id, limit=100)
        if history:
            stats['total_songs'] = len(history)
            stats['favorite_songs'] = history[:10]  # Top 10
            
            # Calculate favorite artists
            artist_counts = {}
            for song in history:
                artist = song.get('artist', 'Unknown')
                if artist and artist != 'Unknown':
                    artist_counts[artist] = artist_counts.get(artist, 0) + song.get('play_count', 1)
            
            stats['favorite_artists'] = [
                {'artist': artist, 'play_count': count}
                for artist, count in sorted(artist_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            ]
        
        # Get total listening time from listening_time table
        conn = None
        cursor = None
        try:
            from modules.db_helpers import get_db_connection
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("""
                    SELECT COALESCE(SUM(duration_minutes), 0) as total_minutes
                    FROM listening_time
                    WHERE user_id = %s
                """, (user_id,))
                result = cursor.fetchone()
                if result:
                    stats['total_listening_time_minutes'] = int(result.get('total_minutes', 0) or 0)
        except Exception as e:
            logger.error(f"Error fetching listening time: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting user listening stats: {e}", exc_info=True)
        return stats


async def set_sleep_timer(guild_id: int, minutes: int) -> bool:
    """
    Set a sleep timer to automatically disconnect after specified minutes.
    
    Args:
        guild_id: Guild ID
        minutes: Number of minutes until disconnect
    
    Returns:
        True if timer was set successfully, False otherwise
    """
    try:
        # Cancel existing timer if any
        await cancel_sleep_timer(guild_id)
        
        # Check if bot is currently playing in this guild
        if guild_id not in active_sessions:
            logger.warning(f"Cannot set sleep timer - no active session for guild {guild_id}")
            return False
        
        async def sleep_timer_task():
            """Task that waits and then disconnects."""
            try:
                await asyncio.sleep(minutes * 60)
                logger.info(f"Sleep timer expired for guild {guild_id}, disconnecting...")
                
                # Stop playback and disconnect
                if guild_id in active_sessions:
                    voice_client = active_sessions[guild_id].get('voice_client')
                    if voice_client and voice_client.is_connected():
                        await voice_client.disconnect()
                        logger.info(f"Disconnected from guild {guild_id} due to sleep timer")
                    
                    # Clean up session
                    active_sessions.pop(guild_id, None)
                
                # Remove timer reference
                sleep_timers.pop(guild_id, None)
                
            except asyncio.CancelledError:
                logger.info(f"Sleep timer cancelled for guild {guild_id}")
            except Exception as e:
                logger.error(f"Error in sleep timer task: {e}", exc_info=True)
        
        # Create and store the task
        task = asyncio.create_task(sleep_timer_task())
        import time
        end_time = time.time() + (minutes * 60)
        
        sleep_timers[guild_id] = {
            'task': task,
            'end_time': end_time,
            'duration_minutes': minutes
        }
        
        logger.info(f"Sleep timer set for {minutes} minutes in guild {guild_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error setting sleep timer: {e}", exc_info=True)
        return False


async def cancel_sleep_timer(guild_id: int) -> bool:
    """
    Cancel an active sleep timer.
    
    Args:
        guild_id: Guild ID
    
    Returns:
        True if timer was cancelled, False if no timer was active
    """
    try:
        if guild_id not in sleep_timers:
            return False
        
        # Cancel the task
        timer_info = sleep_timers[guild_id]
        if 'task' in timer_info and not timer_info['task'].done():
            timer_info['task'].cancel()
        
        # Remove from dictionary
        sleep_timers.pop(guild_id, None)
        
        logger.info(f"Sleep timer cancelled for guild {guild_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error cancelling sleep timer: {e}", exc_info=True)
        return False


def get_sleep_timer_status(guild_id: int) -> Optional[dict]:
    """
    Get the status of a sleep timer.
    
    Args:
        guild_id: Guild ID
    
    Returns:
        Dictionary with timer info or None if no timer active
    """
    try:
        if guild_id not in sleep_timers:
            return None
        
        import time
        timer_info = sleep_timers[guild_id]
        remaining_seconds = max(0, int(timer_info['end_time'] - time.time()))
        
        return {
            'active': True,
            'duration_minutes': timer_info['duration_minutes'],
            'remaining_seconds': remaining_seconds,
            'remaining_minutes': round(remaining_seconds / 60, 1)
        }
        
    except Exception as e:
        logger.error(f"Error getting sleep timer status: {e}", exc_info=True)
        return None


async def update_persistent_now_playing(guild_id: int, channel, bot_user):
    """
    Update or create a persistent 'now playing' message in the channel.
    Edits the same message instead of creating new ones.
    
    Args:
        guild_id: Guild ID
        channel: Text channel to send/edit message in
        bot_user: Bot user object for embed thumbnail
    
    Returns:
        Message object if successful, None otherwise
    """
    try:
        import discord
        
        if guild_id not in active_sessions:
            return None
        
        session = active_sessions[guild_id]
        current_song = session.get('current_song')
        
        if not current_song:
            return None
        
        # Get or create persistent message reference
        persistent_msg = session.get('persistent_now_playing_msg')
        
        # Create embed
        embed = discord.Embed(
            title="🎵 Now Playing",
            color=discord.Color.blue()
        )
        
        song_title = current_song.get('title', 'Unknown')
        song_artist = current_song.get('artist', 'Unknown')
        song_url = current_song.get('url', '')
        song_source = current_song.get('source', '')
        
        # Add AI indicator
        if song_source == 'ai':
            song_title = f"🤖 {song_title}"
        
        if song_url:
            embed.add_field(
                name="🎧 Song",
                value=f"**{song_title}**\nby {song_artist}\n[Link]({song_url})",
                inline=False
            )
        else:
            embed.add_field(
                name="🎧 Song",
                value=f"**{song_title}**\nby {song_artist}",
                inline=False
            )
        
        # Add queue info
        queue = session.get('queue', [])
        embed.add_field(
            name="📋 Queue",
            value=f"{len(queue)} songs remaining",
            inline=True
        )
        
        # Add voice client info
        voice_client = session.get('voice_client')
        if voice_client and voice_client.channel:
            embed.add_field(
                name="📍 Channel",
                value=voice_client.channel.name,
                inline=True
            )
        
        embed.set_footer(text="Updates automatically • Use /music for controls")
        embed.set_thumbnail(url=bot_user.display_avatar.url if bot_user else None)
        
        # Try to edit existing message, or create new one
        if persistent_msg:
            try:
                # Try to fetch and edit the message
                msg = await channel.fetch_message(persistent_msg['message_id'])
                await msg.edit(embed=embed)
                logger.debug(f"Updated persistent now playing message in guild {guild_id}")
                return msg
            except (discord.NotFound, discord.HTTPException) as e:
                logger.debug(f"Could not edit persistent message, creating new one: {e}")
                # Message was deleted or error, create new one
                persistent_msg = None
        
        # Create new message if no persistent one exists
        if not persistent_msg:
            msg = await channel.send(embed=embed)
            session['persistent_now_playing_msg'] = {
                'message_id': msg.id,
                'channel_id': channel.id
            }
            logger.debug(f"Created persistent now playing message in guild {guild_id}")
            return msg
        
    except Exception as e:
        logger.error(f"Error updating persistent now playing: {e}", exc_info=True)
        return None
