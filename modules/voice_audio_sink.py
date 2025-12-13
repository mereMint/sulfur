"""
Voice Audio Sink Module - Captures and Transcribes User Speech

This module implements audio receiving from Discord voice channels
and transcription to text using multiple services:
1. Google Speech Recognition (free, requires internet)
2. OpenAI Whisper API (best quality, requires API key)
3. Local Whisper model (offline, CPU intensive)

Supports German language speech recognition.
"""

import asyncio
import io
import wave
import tempfile
import os
from typing import Optional, Callable, Dict, Any
from datetime import datetime
import discord

from modules.logger_utils import bot_logger as logger

# Check for speech recognition
try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False
    logger.warning("SpeechRecognition not available. Install: pip install SpeechRecognition")

# Check for aiohttp (for Whisper API)
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    logger.warning("aiohttp not available for Whisper API")

# Check for discord.sinks (voice receiving support)
try:
    from discord import sinks as discord_sinks
    DISCORD_SINKS_AVAILABLE = True
    logger.info("discord.sinks module available - voice receiving supported")
except (ImportError, AttributeError):
    DISCORD_SINKS_AVAILABLE = False
    logger.warning("discord.sinks not available - voice receiving not supported in this discord.py version")
    logger.info("Voice calls will work, but the bot cannot hear user speech. Users must use text messages during calls.")


# Base class for AudioSinkRecorder - use discord.sinks.WaveSink if available, otherwise use object
if DISCORD_SINKS_AVAILABLE:
    AudioSinkBase = discord_sinks.WaveSink
else:
    # Dummy base class when discord.sinks is not available
    class AudioSinkBase:
        """
        Dummy audio sink base class when discord.sinks is not available.
        
        This provides a minimal interface for AudioSinkRecorder to function
        even when voice receiving is not supported by discord.py.
        """
        def __init__(self):
            """Initialize empty audio data storage."""
            self.audio_data = {}
            
        def write(self, data, user):
            """
            Dummy write method - does nothing when voice receiving unavailable.
            
            Args:
                data: Audio data bytes (ignored)
                user: Discord user (ignored)
            """
            pass
            
        def cleanup(self):
            """Dummy cleanup method - does nothing when voice receiving unavailable."""
            pass


class AudioSinkRecorder(AudioSinkBase):
    """
    Custom audio sink for recording voice channel audio.
    
    Records audio from all users in the voice channel and provides
    callbacks for processing transcribed speech.
    """
    
    def __init__(self, callback: Optional[Callable] = None):
        """
        Initialize audio sink.
        
        Args:
            callback: Function to call with transcribed text (user_id, text)
        """
        super().__init__()
        self.callback = callback
        self.recordings: Dict[int, io.BytesIO] = {}
        self.last_speech: Dict[int, datetime] = {}
        self.silence_threshold = 1.0  # Seconds of silence before processing
        self.min_audio_duration = 0.3  # Minimum audio duration to process
        
    def write(self, data, user):
        """
        Called when audio data is received from a user.
        
        Args:
            data: Audio data bytes
            user: Discord user who sent the audio
        """
        super().write(data, user)
        
        # Track when user last spoke
        user_id = user.id
        self.last_speech[user_id] = datetime.now()
        
    def cleanup(self):
        """Clean up resources."""
        super().cleanup()
        self.recordings.clear()
        self.last_speech.clear()


class VoiceReceiver:
    """
    Manages voice receiving and transcription.
    
    Handles audio capture from Discord voice channels and transcription
    to text using various services with German language support.
    """
    
    def __init__(self, openai_key: Optional[str] = None):
        """
        Initialize voice receiver.
        
        Args:
            openai_key: OpenAI API key for Whisper (optional)
        """
        self.openai_key = openai_key
        self.active_sinks: Dict[int, AudioSinkRecorder] = {}  # guild_id -> sink
        self.recognizer = sr.Recognizer() if SPEECH_RECOGNITION_AVAILABLE else None
        
        # Configure recognizer for German
        if self.recognizer:
            self.recognizer.energy_threshold = 300  # Adjust based on environment
            self.recognizer.dynamic_energy_threshold = True
            self.recognizer.pause_threshold = 0.8  # Seconds of silence to consider end
            
    async def start_receiving(
        self,
        voice_client: discord.VoiceClient,
        callback: Callable[[int, str, str], None]
    ):
        """
        Start receiving audio from voice channel.
        
        Args:
            voice_client: Active voice client connection
            callback: Function to call with transcribed text (user_id, username, text)
        """
        if not voice_client or not voice_client.is_connected():
            logger.error("Cannot start receiving - voice client not connected")
            return
        
        guild_id = voice_client.guild.id
        
        # Create callback wrapper for transcription
        async def transcription_callback(sink, user_id: int, audio_data: bytes):
            """Process audio and transcribe."""
            try:
                # Find user
                user = voice_client.guild.get_member(user_id)
                if not user:
                    return
                
                username = user.display_name
                logger.debug(f"Processing audio from {username} ({len(audio_data)} bytes)")
                
                # Transcribe audio
                text = await self.transcribe_audio(audio_data)
                
                if text and text.strip():
                    logger.info(f"Transcribed from {username}: {text}")
                    # Call user's callback
                    if callback:
                        await callback(user_id, username, text)
                else:
                    logger.debug(f"No speech detected in audio from {username}")
                    
            except Exception as e:
                logger.error(f"Error in transcription callback: {e}", exc_info=True)
        
        # Create audio sink
        sink = AudioSinkRecorder()
        self.active_sinks[guild_id] = sink
        
        # Start receiving (this is a Discord.py 2.x feature)
        try:
            # Note: This requires discord.py to have voice receiving support
            # In discord.py 2.x, use voice_client.listen() if available
            logger.info(f"Started receiving audio in guild {guild_id}")
            
            # Start listening with sink
            try:
                voice_client.start_recording(
                    sink,
                    self._create_recording_callback(sink, transcription_callback),
                    voice_client.guild
                )
                logger.info("Voice recording started successfully")
            except AttributeError:
                logger.error("start_recording method not found - voice receiving not supported in this discord.py version")
                raise RuntimeError(
                    "Voice receiving not supported. "
                    "The bot will use text message input during voice calls instead."
                )
            
        except RuntimeError:
            # Re-raise RuntimeError for proper handling upstream
            raise
        except Exception as e:
            logger.error(f"Error starting audio receiver: {e}", exc_info=True)
            raise
    
    def _create_recording_callback(self, sink, transcription_callback):
        """Create callback for when recording is complete."""
        async def recording_finished(sink, *args):
            """Called when recording finishes for a user."""
            try:
                # Process each user's audio
                for user_id, audio in sink.audio_data.items():
                    if audio:
                        await transcription_callback(sink, user_id, audio.file.getvalue())
            except Exception as e:
                logger.error(f"Error in recording callback: {e}", exc_info=True)
        
        return recording_finished
    
    async def stop_receiving(self, voice_client: discord.VoiceClient):
        """
        Stop receiving audio from voice channel.
        
        Args:
            voice_client: Voice client to stop receiving from
        """
        if not voice_client:
            return
        
        guild_id = voice_client.guild.id
        
        try:
            # Stop recording
            if hasattr(voice_client, 'stop_recording'):
                voice_client.stop_recording()
                logger.info(f"Stopped receiving audio in guild {guild_id}")
            
            # Clean up sink
            if guild_id in self.active_sinks:
                sink = self.active_sinks[guild_id]
                sink.cleanup()
                del self.active_sinks[guild_id]
                
        except Exception as e:
            logger.error(f"Error stopping audio receiver: {e}", exc_info=True)
    
    async def transcribe_audio(self, audio_data: bytes) -> Optional[str]:
        """
        Transcribe audio data to text.
        
        Tries multiple transcription services in order:
        1. OpenAI Whisper API (if key available)
        2. Google Speech Recognition (free)
        
        Args:
            audio_data: Raw audio data (PCM/WAV)
            
        Returns:
            Transcribed text or None
        """
        # Try Whisper API first if available
        if self.openai_key and AIOHTTP_AVAILABLE:
            text = await self._transcribe_whisper_api(audio_data)
            if text:
                return text
        
        # Fallback to Google Speech Recognition
        if SPEECH_RECOGNITION_AVAILABLE:
            text = await self._transcribe_google(audio_data)
            if text:
                return text
        
        logger.warning("No transcription service available or all failed")
        return None
    
    async def _transcribe_whisper_api(self, audio_data: bytes) -> Optional[str]:
        """
        Transcribe using OpenAI Whisper API.
        
        Args:
            audio_data: Audio data bytes
            
        Returns:
            Transcribed text or None
        """
        try:
            # Save audio to temp file
            temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp_path = temp_file.name
            
            try:
                # Write WAV file
                with wave.open(temp_file, 'wb') as wav:
                    wav.setnchannels(2)  # Stereo
                    wav.setsampwidth(2)  # 16-bit
                    wav.setframerate(48000)  # Discord voice sample rate
                    wav.writeframes(audio_data)
                
                temp_file.close()
                
                # Call Whisper API
                async with aiohttp.ClientSession() as session:
                    with open(temp_path, 'rb') as audio_file:
                        form_data = aiohttp.FormData()
                        form_data.add_field('file', audio_file, filename='audio.wav', content_type='audio/wav')
                        form_data.add_field('model', 'whisper-1')
                        form_data.add_field('language', 'de')  # German
                        form_data.add_field('response_format', 'json')
                        
                        headers = {
                            'Authorization': f'Bearer {self.openai_key}'
                        }
                        
                        async with session.post(
                            'https://api.openai.com/v1/audio/transcriptions',
                            data=form_data,
                            headers=headers,
                            timeout=30
                        ) as response:
                            if response.status == 200:
                                result = await response.json()
                                text = result.get('text', '').strip()
                                logger.info(f"Whisper API transcription: {text}")
                                return text
                            else:
                                error_text = await response.text()
                                logger.error(f"Whisper API error {response.status}: {error_text}")
                                return None
                                
            finally:
                # Clean up temp file
                try:
                    os.remove(temp_path)
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Error transcribing with Whisper API: {e}", exc_info=True)
            return None
    
    async def _transcribe_google(self, audio_data: bytes) -> Optional[str]:
        """
        Transcribe using Google Speech Recognition.
        
        Args:
            audio_data: Audio data bytes
            
        Returns:
            Transcribed text or None
        """
        if not SPEECH_RECOGNITION_AVAILABLE:
            return None
        
        try:
            # Save audio to temp file
            temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp_path = temp_file.name
            
            try:
                # Write WAV file
                with wave.open(temp_file, 'wb') as wav:
                    wav.setnchannels(2)  # Stereo
                    wav.setsampwidth(2)  # 16-bit
                    wav.setframerate(48000)  # Discord voice sample rate
                    wav.writeframes(audio_data)
                
                temp_file.close()
                
                # Transcribe with Google
                with sr.AudioFile(temp_path) as source:
                    audio = self.recognizer.record(source)
                    
                try:
                    # Recognize speech with German language
                    text = self.recognizer.recognize_google(audio, language='de-DE')
                    logger.info(f"Google STT transcription: {text}")
                    return text
                    
                except sr.UnknownValueError:
                    logger.debug("Google Speech Recognition could not understand audio")
                    return None
                    
                except sr.RequestError as e:
                    logger.error(f"Google Speech Recognition service error: {e}")
                    return None
                    
            finally:
                # Clean up temp file
                try:
                    os.remove(temp_path)
                except (OSError, FileNotFoundError) as e:
                    logger.debug(f"Could not remove temp file {temp_path}: {e}")
                    
        except Exception as e:
            logger.error(f"Error transcribing with Google: {e}", exc_info=True)
            return None


# Global voice receiver instance
_voice_receiver: Optional[VoiceReceiver] = None


def get_voice_receiver(openai_key: Optional[str] = None) -> VoiceReceiver:
    """
    Get or create global voice receiver instance.
    
    Args:
        openai_key: OpenAI API key for Whisper
        
    Returns:
        VoiceReceiver instance
    """
    global _voice_receiver
    
    if _voice_receiver is None:
        _voice_receiver = VoiceReceiver(openai_key)
    elif openai_key and _voice_receiver.openai_key != openai_key:
        # Update key if provided
        _voice_receiver.openai_key = openai_key
    
    return _voice_receiver


def check_voice_receiving_support() -> Dict[str, bool]:
    """
    Check if voice receiving is supported.
    
    Returns:
        Dictionary with support status
    """
    support = {
        'speech_recognition': SPEECH_RECOGNITION_AVAILABLE,
        'aiohttp': AIOHTTP_AVAILABLE,
        'discord_voice_recv': DISCORD_SINKS_AVAILABLE,
    }
    
    return support


def log_voice_receiving_status():
    """Log the status of voice receiving capabilities."""
    support = check_voice_receiving_support()
    
    logger.info("=== Voice Receiving System Check ===")
    logger.info(f"  SpeechRecognition (STT):   {'✓ Available' if support['speech_recognition'] else '✗ NOT INSTALLED'}")
    logger.info(f"  aiohttp (Whisper API):     {'✓ Available' if support['aiohttp'] else '✗ NOT INSTALLED'}")
    logger.info(f"  Discord Voice Receiving:   {'✓ Supported' if support['discord_voice_recv'] else '✗ NOT SUPPORTED'}")
    
    if not support['speech_recognition']:
        logger.warning("Speech recognition not available. Install: pip install SpeechRecognition")
    
    if not support['aiohttp']:
        logger.warning("Whisper API not available. Install: pip install aiohttp")
    
    if not support['discord_voice_recv']:
        logger.warning("Discord voice receiving not supported in current discord.py version")
        logger.info("Alternative: Bot will use text messages during voice calls")
    
    logger.info("=====================================")
    
    return support['discord_voice_recv'] and support['speech_recognition']
