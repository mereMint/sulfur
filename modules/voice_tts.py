"""
Voice TTS and Transcription Module for Sulfur Bot

Handles text-to-speech in voice channels and speech-to-text transcription.
Uses edge-tts for TTS (free) and plans for Whisper API for transcription.
"""

import asyncio
import tempfile
import os
import shutil
from typing import Optional, Dict, List, Any
import discord
from discord import FFmpegPCMAudio

from modules.logger_utils import bot_logger as logger
from modules.db_helpers import get_db_connection

# We'll use edge-tts for free TTS
# Import will be done dynamically to handle missing dependencies gracefully
try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False
    logger.warning("edge-tts not available. Install with: pip install edge-tts")

# Check for PyNaCl (required for voice)
try:
    import nacl
    PYNACL_AVAILABLE = True
except ImportError:
    PYNACL_AVAILABLE = False
    logger.warning("PyNaCl not available. Install with: pip install PyNaCl")


# Sulfur's voice configuration
SULFUR_VOICE = "de-DE-KillianNeural"  # Male German voice with personality
SULFUR_VOICE_ALT = "de-DE-ConradNeural"  # Alternative voice

# Voice settings
VOICE_RATE = "+0%"  # Normal speed
VOICE_PITCH = "+0Hz"  # Normal pitch


# --- TTS Functions ---

async def text_to_speech(text: str, output_file: Optional[str] = None) -> Optional[str]:
    """
    Convert text to speech using edge-tts.
    
    Args:
        text: Text to convert to speech
        output_file: Optional output file path. If None, creates temp file.
    
    Returns:
        Path to the audio file, or None if failed
    """
    if not EDGE_TTS_AVAILABLE:
        logger.error("edge-tts is not available")
        return None
    
    try:
        # Create temp file if output not specified
        if output_file is None:
            # Use NamedTemporaryFile for safer temp file handling
            temp_file = tempfile.NamedTemporaryFile(
                suffix='.mp3', 
                prefix='sulfur_tts_', 
                delete=False
            )
            output_file = temp_file.name
            temp_file.close()
        
        # Generate TTS
        communicate = edge_tts.Communicate(
            text=text,
            voice=SULFUR_VOICE,
            rate=VOICE_RATE,
            pitch=VOICE_PITCH
        )
        
        await communicate.save(output_file)
        logger.debug(f"Generated TTS audio: {output_file}")
        return output_file
    except Exception as e:
        logger.error(f"Error generating TTS: {e}")
        return None


async def cleanup_audio_file(file_path: str):
    """Clean up temporary audio file."""
    try:
        if file_path and os.path.exists(file_path):
            await asyncio.sleep(1)  # Wait a bit to ensure playback is done
            os.remove(file_path)
            logger.debug(f"Cleaned up audio file: {file_path}")
    except Exception as e:
        logger.error(f"Error cleaning up audio file {file_path}: {e}")


# --- Voice Channel Management ---

async def join_voice_channel(channel: discord.VoiceChannel) -> Optional[discord.VoiceClient]:
    """Join a voice channel."""
    try:
        # Check for PyNaCl
        if not PYNACL_AVAILABLE:
            logger.error("PyNaCl library is not installed. Voice features require PyNaCl.")
            raise RuntimeError(
                "PyNaCl library needed in order to use voice. "
                "Install it with: pip install PyNaCl"
            )
        
        if channel.guild.voice_client:
            # Already connected, move to new channel
            await channel.guild.voice_client.move_to(channel)
            return channel.guild.voice_client
        else:
            # Connect to channel
            voice_client = await channel.connect()
            logger.info(f"Joined voice channel: {channel.name}")
            return voice_client
    except RuntimeError as re:
        # Re-raise PyNaCl errors with clear message
        logger.error(f"Voice dependency error: {re}")
        raise
    except Exception as e:
        logger.error(f"Error joining voice channel: {e}")
        return None


async def leave_voice_channel(voice_client: discord.VoiceClient):
    """Leave voice channel and cleanup."""
    try:
        if voice_client and voice_client.is_connected():
            await voice_client.disconnect()
            logger.info("Left voice channel")
    except Exception as e:
        logger.error(f"Error leaving voice channel: {e}")


async def speak_in_channel(
    voice_client: discord.VoiceClient,
    text: str,
    wait_for_completion: bool = True
) -> bool:
    """
    Speak text in a voice channel.
    
    Args:
        voice_client: Active voice client connection
        text: Text to speak
        wait_for_completion: Whether to wait for speech to complete
    
    Returns:
        True if successful, False otherwise
    """
    try:
        if not voice_client or not voice_client.is_connected():
            logger.error("Voice client not connected")
            return False
        
        # Stop current playback if any
        if voice_client.is_playing():
            voice_client.stop()
        
        # Generate TTS audio
        audio_file = await text_to_speech(text)
        if not audio_file:
            return False
        
        # Play audio with error handling
        try:
            audio_source = FFmpegPCMAudio(audio_file)
            voice_client.play(audio_source)
        except Exception as audio_error:
            logger.error(f"Error playing audio: {audio_error}")
            await cleanup_audio_file(audio_file)
            return False
        
        logger.info(f"Speaking in voice channel: {text[:50]}...")
        
        # Wait for playback to complete
        if wait_for_completion:
            while voice_client.is_playing():
                await asyncio.sleep(0.1)
            
            # Cleanup audio file
            await cleanup_audio_file(audio_file)
        else:
            # Schedule cleanup for later
            asyncio.create_task(cleanup_audio_file(audio_file))
        
        return True
    except Exception as e:
        logger.error(f"Error speaking in channel: {e}")
        return False


# --- Voice Call Initiation ---

async def initiate_voice_call(
    bot: discord.Client,
    user: discord.Member,
    initial_message: str,
    timeout_seconds: int = 300
) -> Optional[int]:
    """
    Initiate an autonomous voice call with a user.
    
    Args:
        bot: Discord bot client
        user: User to call
        initial_message: First message to speak
        timeout_seconds: How long to wait for user to join
    
    Returns:
        Conversation ID if successful, None otherwise
    """
    try:
        # Find user's voice state
        if not user.voice or not user.voice.channel:
            logger.info(f"User {user.display_name} not in voice channel, cannot call")
            return None
        
        channel = user.voice.channel
        
        # Join the channel
        voice_client = await join_voice_channel(channel)
        if not voice_client:
            return None
        
        # Log conversation start
        conversation_id = await start_voice_conversation(
            guild_id=channel.guild.id,
            channel_id=channel.id,
            initiated_by='bot',
            participant_count=len(channel.members)
        )
        
        # Speak initial message
        await asyncio.sleep(1)  # Brief pause after joining
        await speak_in_channel(voice_client, initial_message)
        
        logger.info(f"Initiated voice call with {user.display_name} in {channel.name}")
        return conversation_id
    except Exception as e:
        logger.error(f"Error initiating voice call: {e}")
        return None


# --- Voice Conversation Logging ---

async def start_voice_conversation(
    guild_id: int,
    channel_id: int,
    initiated_by: str,
    participant_count: int
) -> Optional[int]:
    """Start logging a voice conversation."""
    try:
        conn = get_db_connection()
        if not conn:
            logger.error("Failed to get database connection for starting voice conversation")
            return None
        
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO voice_conversations
                (guild_id, channel_id, session_start, initiated_by, participant_count)
                VALUES (%s, %s, CURRENT_TIMESTAMP, %s, %s)
            """, (guild_id, channel_id, initiated_by, participant_count))
            conn.commit()
            return cursor.lastrowid
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error starting voice conversation log: {e}")
        return None


async def end_voice_conversation(conversation_id: int):
    """End a voice conversation log."""
    try:
        conn = get_db_connection()
        if not conn:
            logger.error("Failed to get database connection for ending voice conversation")
            return
        
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE voice_conversations
                SET session_end = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (conversation_id,))
            conn.commit()
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error ending voice conversation: {e}")


async def log_voice_message(
    conversation_id: int,
    user_id: int,
    speaker_name: str,
    transcript: str,
    confidence: Optional[float] = None
):
    """Log a voice message transcript."""
    try:
        conn = get_db_connection()
        if not conn:
            logger.error("Failed to get database connection for logging voice message")
            return
        
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO voice_messages
                (conversation_id, user_id, speaker_name, transcript, confidence)
                VALUES (%s, %s, %s, %s, %s)
            """, (conversation_id, user_id, speaker_name, transcript, confidence))
            conn.commit()
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error logging voice message: {e}")


# --- Transcription (Placeholder for future implementation) ---

async def transcribe_audio(audio_data: bytes) -> Optional[Dict[str, Any]]:
    """
    Transcribe audio to text.
    
    This is a placeholder for future implementation with Whisper API or similar.
    
    Args:
        audio_data: Raw audio data to transcribe
    
    Returns:
        Dictionary with 'text', 'confidence', and 'speaker' if available
    """
    # TODO: Implement with Whisper API or similar service
    logger.warning("Audio transcription not yet implemented")
    return None


async def identify_speaker(audio_data: bytes, known_speakers: List[int]) -> Optional[int]:
    """
    Identify speaker from audio.
    
    Placeholder for future speaker identification implementation.
    
    Args:
        audio_data: Raw audio data
        known_speakers: List of known user IDs in channel
    
    Returns:
        User ID of identified speaker, or None
    """
    # TODO: Implement speaker identification
    logger.warning("Speaker identification not yet implemented")
    return None


# --- Available Voices ---

async def list_available_voices(language: str = "de") -> List[Dict[str, str]]:
    """List available TTS voices for a language."""
    if not EDGE_TTS_AVAILABLE:
        return []
    
    try:
        voices = await edge_tts.list_voices()
        filtered = [
            {
                'name': v['ShortName'],
                'gender': v['Gender'],
                'locale': v['Locale']
            }
            for v in voices
            if v['Locale'].startswith(language)
        ]
        return filtered
    except Exception as e:
        logger.error(f"Error listing voices: {e}")
        return []


# --- Voice Quality Check ---

def check_voice_dependencies() -> Dict[str, bool]:
    """Check if voice dependencies are available."""
    dependencies = {
        'edge_tts': EDGE_TTS_AVAILABLE,
        'ffmpeg': False,  # Will be checked dynamically
    }
    
    # Check for ffmpeg
    dependencies['ffmpeg'] = shutil.which('ffmpeg') is not None
    
    return dependencies
