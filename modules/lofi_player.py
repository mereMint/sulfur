"""
Lofi Music Player Module for Sulfur Bot

Provides lofi music streaming capabilities using yt-dlp and Discord voice.
Can be used standalone or integrated with focus timer.
"""

import asyncio
import discord
from typing import Optional
from modules.logger_utils import bot_logger as logger

# Lofi music playlists/streams (YouTube)
LOFI_STREAMS = [
    "https://www.youtube.com/watch?v=jfKfPfyJRdk",  # lofi hip hop radio 📚 - beats to relax/study to
    "https://www.youtube.com/watch?v=5qap5aO4i9A",  # lofi hip hop radio 🎧 - beats to sleep/chill to
]

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


async def play_lofi(voice_client: discord.VoiceClient, stream_index: int = 0) -> bool:
    """
    Play lofi music stream in a voice channel.
    
    Args:
        voice_client: Connected Discord voice client
        stream_index: Index of lofi stream to play (0 or 1)
    
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
        
        # Get stream URL
        stream_url = LOFI_STREAMS[stream_index % len(LOFI_STREAMS)]
        
        # Extract audio URL using yt-dlp
        logger.info(f"Extracting lofi stream URL: {stream_url}")
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(stream_url, download=False)
            audio_url = info['url']
        
        # Create audio source
        audio_source = discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS)
        
        # Play audio
        voice_client.play(
            audio_source,
            after=lambda e: logger.error(f"Lofi playback error: {e}") if e else None
        )
        
        logger.info(f"Started lofi music playback: {info.get('title', 'Unknown')}")
        return True
        
    except ImportError:
        logger.error("yt-dlp not installed. Install with: pip install yt-dlp")
        return False
    except Exception as e:
        logger.error(f"Error playing lofi music: {e}", exc_info=True)
        return False


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
            logger.info("Stopped lofi music playback")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error stopping lofi music: {e}")
        return False


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
                return channel.guild.voice_client
            else:
                # Move to the new channel
                await channel.guild.voice_client.move_to(channel)
                return channel.guild.voice_client
        
        # Connect to channel
        voice_client = await channel.connect()
        logger.info(f"Joined voice channel: {channel.name}")
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
        
        if voice_client.is_connected():
            await voice_client.disconnect()
            logger.info("Left voice channel")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error leaving voice channel: {e}")
        return False
