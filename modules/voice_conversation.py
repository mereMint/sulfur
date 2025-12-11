"""
Voice Conversation Module - Real-time Voice Call Capabilities
Implements Neuro-sama-like voice interaction including:
- Voice call management
- Real-time transcription (Whisper)
- Voice-to-text-to-AI-to-TTS pipeline
- Voice activity detection
- Conversation state tracking
"""

import asyncio
import tempfile
import os
import wave
import io
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from collections import deque
import discord
from discord import FFmpegPCMAudio

from modules.logger_utils import bot_logger as logger
from modules.db_helpers import get_db_connection
from modules.voice_tts import text_to_speech, EDGE_TTS_AVAILABLE

# Try to import speech recognition libraries
try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False
    logger.warning("speech_recognition not available. Install with: pip install SpeechRecognition")

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False


# --- Configuration Constants ---
VOICE_CALL_TIMEOUT_MINUTES = 30  # Auto-disconnect after 30 minutes
SILENCE_TIMEOUT_SECONDS = 10  # Consider speech ended after 10s silence
MAX_RECORDING_DURATION = 30  # Maximum seconds per recording chunk
TRANSCRIPTION_CONFIDENCE_THRESHOLD = 0.5  # Minimum confidence for transcription


class VoiceCallState:
    """Manages state for an active voice call."""
    
    def __init__(self, channel: discord.VoiceChannel, user: discord.Member):
        self.channel = channel
        self.user = user
        self.start_time = datetime.now()
        self.last_activity = datetime.now()
        self.conversation_history = deque(maxlen=20)
        self.is_speaking = False
        self.voice_client: Optional[discord.VoiceClient] = None
        self.transcription_queue = asyncio.Queue()
        self.response_queue = asyncio.Queue()
        
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now()
        
    def is_timed_out(self) -> bool:
        """Check if call has timed out."""
        return (datetime.now() - self.last_activity).total_seconds() > VOICE_CALL_TIMEOUT_MINUTES * 60
        
    def get_duration(self) -> int:
        """Get call duration in seconds."""
        return int((datetime.now() - self.start_time).total_seconds())
        
    def add_to_history(self, speaker: str, text: str):
        """Add utterance to conversation history."""
        self.conversation_history.append({
            'speaker': speaker,
            'text': text,
            'timestamp': datetime.now().isoformat()
        })


# --- Global state ---
_active_calls: Dict[int, VoiceCallState] = {}  # user_id -> VoiceCallState


async def initiate_voice_call(user: discord.Member, config: dict) -> Optional[VoiceCallState]:
    """
    Initiate a voice call with a user.
    
    Args:
        user: Discord member to call
        config: Bot configuration
        
    Returns:
        VoiceCallState if successful, None otherwise
    """
    # Check if voice calls are enabled
    if not config.get('modules', {}).get('autonomous_behavior', {}).get('allow_voice_calls', False):
        logger.info("Voice calls are disabled in config")
        return None
        
    # Check if user is already in a voice channel
    if not user.voice or not user.voice.channel:
        logger.info(f"User {user.name} is not in a voice channel")
        return None
        
    voice_channel = user.voice.channel
    
    # Check if already in a call with this user
    if user.id in _active_calls:
        logger.info(f"Already in a call with {user.name}")
        return _active_calls[user.id]
        
    try:
        # Send notification
        await user.send("📞 Sulfur möchte dich anrufen! Ich werde deinem Voice Channel beitreten...")
        
        # Join voice channel
        voice_client = await voice_channel.connect()
        
        # Create call state
        call_state = VoiceCallState(voice_channel, user)
        call_state.voice_client = voice_client
        _active_calls[user.id] = call_state
        
        logger.info(f"Initiated voice call with {user.name} in channel {voice_channel.name}")
        
        # Play greeting
        greeting_text = "Hey! Ich bin jetzt im Call. Lass uns quatschen!"
        await speak_in_call(call_state, greeting_text)
        
        return call_state
        
    except discord.Forbidden:
        logger.warning(f"No permission to join voice channel {voice_channel.name}")
        await user.send("❌ Ich habe keine Berechtigung, deinem Voice Channel beizutreten.")
        return None
    except Exception as e:
        logger.error(f"Error initiating voice call: {e}", exc_info=True)
        await user.send(f"❌ Fehler beim Beitreten des Voice Channels: {e}")
        return None


async def end_voice_call(user_id: int, reason: str = "normal"):
    """
    End a voice call.
    
    Args:
        user_id: Discord user ID
        reason: Reason for ending call (normal, timeout, error)
    """
    if user_id not in _active_calls:
        return
        
    call_state = _active_calls[user_id]
    
    try:
        # Play goodbye message
        if reason == "timeout":
            goodbye_text = "Der Call ist jetzt schon ziemlich lange. Ich gehe mal, bis später!"
        elif reason == "error":
            goodbye_text = "Es gab einen Fehler. Ich muss leider gehen."
        else:
            goodbye_text = "War nett zu quatschen! Bis bald!"
            
        await speak_in_call(call_state, goodbye_text)
        
        # Wait for goodbye to finish
        await asyncio.sleep(3)
        
        # Disconnect
        if call_state.voice_client and call_state.voice_client.is_connected():
            await call_state.voice_client.disconnect()
            
        # Log call duration
        duration = call_state.get_duration()
        logger.info(f"Ended voice call with user {user_id}, duration: {duration}s, reason: {reason}")
        
        # Store call statistics
        async with get_db_connection() as (conn, cursor):
            await cursor.execute("""
                INSERT INTO voice_call_stats (user_id, duration_seconds, reason, started_at)
                VALUES (%s, %s, %s, %s)
            """, (user_id, duration, reason, call_state.start_time))
            await conn.commit()
            
    except Exception as e:
        logger.error(f"Error ending voice call: {e}", exc_info=True)
    finally:
        # Remove from active calls
        del _active_calls[user_id]


async def speak_in_call(call_state: VoiceCallState, text: str):
    """
    Speak text in a voice call using TTS.
    
    Args:
        call_state: Current voice call state
        text: Text to speak
    """
    if not EDGE_TTS_AVAILABLE:
        logger.warning("TTS not available, cannot speak")
        return
        
    if not call_state.voice_client or not call_state.voice_client.is_connected():
        logger.warning("Voice client not connected")
        return
        
    try:
        # Generate TTS audio
        audio_file = await text_to_speech(text)
        
        if not audio_file or not os.path.exists(audio_file):
            logger.error("Failed to generate TTS audio")
            return
            
        # Add to conversation history
        call_state.add_to_history("Sulfur", text)
        call_state.update_activity()
        
        # Play audio
        audio_source = FFmpegPCMAudio(audio_file)
        
        # Wait if already playing
        while call_state.voice_client.is_playing():
            await asyncio.sleep(0.1)
            
        call_state.voice_client.play(audio_source)
        
        # Wait for playback to finish
        while call_state.voice_client.is_playing():
            await asyncio.sleep(0.1)
            
        # Clean up temp file
        try:
            os.remove(audio_file)
        except:
            pass
            
        logger.debug(f"Spoke in call: {text[:50]}...")
        
    except Exception as e:
        logger.error(f"Error speaking in call: {e}", exc_info=True)


async def transcribe_audio_whisper(audio_file_path: str, openai_key: str) -> Optional[str]:
    """
    Transcribe audio using OpenAI Whisper API.
    
    Args:
        audio_file_path: Path to audio file
        openai_key: OpenAI API key
        
    Returns:
        Transcribed text or None
    """
    if not AIOHTTP_AVAILABLE or not openai_key:
        return None
        
    try:
        async with aiohttp.ClientSession() as session:
            # Prepare multipart form data
            with open(audio_file_path, 'rb') as audio_file:
                form_data = aiohttp.FormData()
                form_data.add_field('file', audio_file, filename='audio.wav', content_type='audio/wav')
                form_data.add_field('model', 'whisper-1')
                form_data.add_field('language', 'de')  # German
                
                headers = {
                    'Authorization': f'Bearer {openai_key}'
                }
                
                async with session.post(
                    'https://api.openai.com/v1/audio/transcriptions',
                    data=form_data,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        text = result.get('text', '')
                        logger.info(f"Whisper transcription: {text}")
                        return text
                    else:
                        error_text = await response.text()
                        logger.error(f"Whisper API error {response.status}: {error_text}")
                        return None
                        
    except Exception as e:
        logger.error(f"Error transcribing with Whisper: {e}", exc_info=True)
        return None


async def transcribe_audio_local(audio_file_path: str) -> Optional[str]:
    """
    Transcribe audio using local speech recognition (Google).
    
    Args:
        audio_file_path: Path to audio file
        
    Returns:
        Transcribed text or None
    """
    if not SPEECH_RECOGNITION_AVAILABLE:
        return None
        
    try:
        recognizer = sr.Recognizer()
        
        with sr.AudioFile(audio_file_path) as source:
            audio_data = recognizer.record(source)
            
        # Try Google Speech Recognition (free but requires internet)
        try:
            text = recognizer.recognize_google(audio_data, language='de-DE')
            logger.info(f"Local transcription: {text}")
            return text
        except sr.UnknownValueError:
            logger.debug("Speech not recognized")
            return None
        except sr.RequestError as e:
            logger.error(f"Speech recognition service error: {e}")
            return None
            
    except Exception as e:
        logger.error(f"Error in local transcription: {e}", exc_info=True)
        return None


async def process_voice_input(
    call_state: VoiceCallState,
    audio_data: bytes,
    config: dict,
    openai_key: Optional[str] = None
) -> Optional[str]:
    """
    Process voice input from user.
    
    Args:
        call_state: Current call state
        audio_data: Raw audio data
        config: Bot configuration
        openai_key: OpenAI API key for Whisper
        
    Returns:
        Transcribed text or None
    """
    # Save audio to temporary file
    temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    temp_path = temp_file.name
    
    try:
        # Write audio data
        temp_file.write(audio_data)
        temp_file.close()
        
        # Try Whisper API first if available
        text = None
        if openai_key:
            text = await transcribe_audio_whisper(temp_path, openai_key)
            
        # Fallback to local recognition
        if not text:
            text = await transcribe_audio_local(temp_path)
            
        if text:
            # Add to conversation history
            call_state.add_to_history(call_state.user.display_name, text)
            call_state.update_activity()
            logger.info(f"Transcribed user speech: {text}")
            
        return text
        
    finally:
        # Clean up temp file
        try:
            os.remove(temp_path)
        except:
            pass


async def handle_voice_conversation(
    call_state: VoiceCallState,
    user_text: str,
    config: dict,
    gemini_key: str,
    openai_key: str,
    system_prompt: str
):
    """
    Handle a voice conversation turn.
    
    Args:
        call_state: Current call state
        user_text: Transcribed user speech
        config: Bot configuration
        gemini_key: Gemini API key
        openai_key: OpenAI API key
        system_prompt: System prompt for AI
    """
    from modules.advanced_ai import get_advanced_ai_response
    
    try:
        # Get AI response
        response, error, metadata = await get_advanced_ai_response(
            prompt=user_text,
            user_id=call_state.user.id,
            channel_id=call_state.channel.id,
            username=call_state.user.display_name,
            config=config,
            gemini_key=gemini_key,
            openai_key=openai_key,
            system_prompt=system_prompt,
            use_cache=True
        )
        
        if response and not error:
            # Speak the response
            await speak_in_call(call_state, response)
        else:
            logger.error(f"AI error in voice call: {error}")
            await speak_in_call(call_state, "Sorry, ich hatte einen Fehler. Kannst du das wiederholen?")
            
    except Exception as e:
        logger.error(f"Error handling voice conversation: {e}", exc_info=True)


async def monitor_voice_calls():
    """Background task to monitor active voice calls."""
    while True:
        try:
            await asyncio.sleep(30)  # Check every 30 seconds
            
            # Check for timeouts
            for user_id, call_state in list(_active_calls.items()):
                if call_state.is_timed_out():
                    logger.info(f"Voice call with user {user_id} timed out")
                    await end_voice_call(user_id, reason="timeout")
                    
        except Exception as e:
            logger.error(f"Error in voice call monitor: {e}", exc_info=True)


def get_active_call(user_id: int) -> Optional[VoiceCallState]:
    """Get active call state for a user."""
    return _active_calls.get(user_id)


def get_all_active_calls() -> List[VoiceCallState]:
    """Get all active calls."""
    return list(_active_calls.values())


async def get_voice_call_stats(user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Get voice call statistics.
    
    Args:
        user_id: Optional user ID to filter stats
        
    Returns:
        Dictionary with call statistics
    """
    async with get_db_connection() as (conn, cursor):
        if user_id:
            await cursor.execute("""
                SELECT 
                    COUNT(*) as total_calls,
                    SUM(duration_seconds) as total_duration,
                    AVG(duration_seconds) as avg_duration,
                    MAX(duration_seconds) as max_duration
                FROM voice_call_stats
                WHERE user_id = %s
            """, (user_id,))
        else:
            await cursor.execute("""
                SELECT 
                    COUNT(*) as total_calls,
                    SUM(duration_seconds) as total_duration,
                    AVG(duration_seconds) as avg_duration,
                    MAX(duration_seconds) as max_duration,
                    COUNT(DISTINCT user_id) as unique_users
                FROM voice_call_stats
            """)
            
        result = await cursor.fetchone()
        
        if result:
            stats = {
                'total_calls': result[0] or 0,
                'total_duration': result[1] or 0,
                'avg_duration': result[2] or 0,
                'max_duration': result[3] or 0
            }
            if not user_id and len(result) > 4:
                stats['unique_users'] = result[4] or 0
            return stats
        else:
            return {
                'total_calls': 0,
                'total_duration': 0,
                'avg_duration': 0,
                'max_duration': 0
            }
