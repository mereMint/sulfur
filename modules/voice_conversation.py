"""
Voice Conversation Module - Real-time Voice Call Capabilities
Implements Neuro-sama-like voice interaction including:
- Voice call management
- Text-to-speech (TTS) output
- Text-based interaction during calls (speech-to-text requires additional setup)
- Auto-leave when channel is empty
- Automatic channel cleanup
- Conversation state tracking

NOTE: Discord.py 2.x does not include built-in audio receiving.
For speech-to-text functionality, you have two options:
1. Use text messages in the voice channel (current implementation)
2. Install discord-ext-voice-recv for audio receiving (advanced)
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

# Note: advanced_ai import moved to function to avoid circular dependency
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
EMPTY_CHANNEL_TIMEOUT_SECONDS = 30  # Auto-leave after 30 seconds if no other users


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
        self.temp_channel: Optional[discord.VoiceChannel] = None  # Track if this is a temporary channel
        self.empty_since: Optional[datetime] = None  # Track when channel became empty
        
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now()
        # Reset empty timer when there's activity
        self.empty_since = None
        
    def is_timed_out(self) -> bool:
        """Check if call has timed out."""
        return (datetime.now() - self.last_activity).total_seconds() > VOICE_CALL_TIMEOUT_MINUTES * 60
    
    def is_channel_empty(self) -> bool:
        """Check if channel has no other users (excluding bot)."""
        if not self.channel:
            return True
        # Count non-bot members
        human_members = [m for m in self.channel.members if not m.bot]
        return len(human_members) == 0
    
    def should_leave_empty_channel(self) -> bool:
        """Check if bot should leave due to empty channel."""
        if not self.is_channel_empty():
            self.empty_since = None
            return False
        
        # Start tracking empty time
        if self.empty_since is None:
            self.empty_since = datetime.now()
            return False
        
        # Check if empty for long enough
        empty_duration = (datetime.now() - self.empty_since).total_seconds()
        return empty_duration >= EMPTY_CHANNEL_TIMEOUT_SECONDS
        
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


async def initiate_voice_call(user: discord.Member, config: dict, create_temp_channel: bool = True, invite_users: list = None) -> Optional[VoiceCallState]:
    """
    Initiate a voice call with a user.
    
    Args:
        user: Discord member to call
        config: Bot configuration
        create_temp_channel: Whether to create a temporary channel for the call
        invite_users: List of additional users to invite to the call
        
    Returns:
        VoiceCallState if successful, None otherwise
    """
    # Check if voice calls are enabled
    if not config.get('modules', {}).get('autonomous_behavior', {}).get('allow_voice_calls', False):
        logger.info("Voice calls are disabled in config")
        return None
        
    # Check if user is already in a voice channel (unless we're creating a temp channel)
    if not create_temp_channel and (not user.voice or not user.voice.channel):
        logger.info(f"User {user.name} is not in a voice channel")
        return None
        
    # Check if already in a call with this user
    if user.id in _active_calls:
        logger.info(f"Already in a call with {user.name}")
        return _active_calls[user.id]
        
    try:
        # Check for PyNaCl before attempting to connect
        # Import at module level for reuse
        from modules.voice_tts import PYNACL_AVAILABLE
        
        if not PYNACL_AVAILABLE:
            error_msg = (
                "❌ Sprachanrufe sind aktuell nicht verfügbar.\n\n"
                "**Grund:** PyNaCl library ist nicht installiert.\n"
                "**Lösung:** Der Bot-Administrator muss folgendes ausführen:\n"
                "```\npip install PyNaCl\n```\n"
                "Oder alle Requirements neu installieren:\n"
                "```\npip install -r requirements.txt\n```"
            )
            await user.send(error_msg)
            logger.error("PyNaCl is not installed - cannot use voice features")
            return None
        
        voice_channel = None
        temp_channel_created = False
        
        if create_temp_channel:
            # Create a temporary voice channel for the call
            guild = user.guild
            
            # Find or create a category for temporary channels
            category = discord.utils.get(guild.categories, name="📞 Bot Calls")
            if not category:
                try:
                    category = await guild.create_category("📞 Bot Calls", reason="Temporary voice call channels")
                except discord.Forbidden:
                    logger.warning("Cannot create category, using default location")
                    category = None
            
            # Create the temporary voice channel
            channel_name = f"🤖 Call mit {user.display_name}"
            try:
                voice_channel = await guild.create_voice_channel(
                    name=channel_name,
                    category=category,
                    reason="Temporary bot voice call",
                    user_limit=10  # Limit to prevent abuse
                )
                temp_channel_created = True
                logger.info(f"Created temporary voice channel: {channel_name}")
            except discord.Forbidden:
                logger.error("Cannot create voice channel - missing permissions")
                await user.send("❌ Ich habe keine Berechtigung, einen Voice-Channel zu erstellen.")
                return None
                
            # Send invitation to the primary user
            try:
                invite = await voice_channel.create_invite(
                    max_age=3600,  # 1 hour
                    max_uses=0,  # Unlimited uses
                    reason="Bot voice call invitation"
                )
                
                embed = discord.Embed(
                    title="📞 Sulfur möchte dich anrufen!",
                    description=f"Ich habe einen temporären Voice-Channel für uns erstellt.\n\n"
                                f"**Channel:** {voice_channel.mention}\n"
                                f"**Einladung:** {invite.url}",
                    color=discord.Color.blue()
                )
                embed.add_field(
                    name="ℹ️ Hinweis",
                    value="Der Channel wird automatisch gelöscht, sobald ich gehe.",
                    inline=False
                )
                await user.send(embed=embed)
            except (discord.Forbidden, discord.HTTPException) as dm_error:
                # Fallback to simple message if embed fails
                try:
                    await user.send(f"📞 Sulfur möchte dich anrufen! Tritt dem Channel {voice_channel.mention} bei!")
                except Exception:
                    logger.warning(f"Could not send DM to user {user.name}")
            
            # Send invitations to additional users if specified
            if invite_users:
                for invited_user in invite_users:
                    if invited_user.id == user.id:
                        continue  # Skip the primary user
                    try:
                        invite = await voice_channel.create_invite(
                            max_age=3600,
                            max_uses=0,
                            reason="Bot voice call invitation"
                        )
                        
                        embed = discord.Embed(
                            title="📞 Einladung zu einem Voice-Call!",
                            description=f"Sulfur lädt dich zu einem Call mit {user.display_name} ein.\n\n"
                                        f"**Channel:** {voice_channel.mention}\n"
                                        f"**Einladung:** {invite.url}",
                            color=discord.Color.blue()
                        )
                        await invited_user.send(embed=embed)
                        logger.info(f"Sent call invitation to {invited_user.display_name}")
                    except Exception as e:
                        logger.warning(f"Could not invite user {invited_user.display_name}: {e}")
        else:
            # Use existing channel
            voice_channel = user.voice.channel
            await user.send("📞 Sulfur möchte dich anrufen! Ich werde deinem Voice Channel beitreten...")
        
        # Join voice channel
        voice_client = await voice_channel.connect()
        
        # Create call state
        call_state = VoiceCallState(voice_channel, user)
        call_state.voice_client = voice_client
        call_state.temp_channel = voice_channel if temp_channel_created else None
        _active_calls[user.id] = call_state
        
        logger.info(f"Initiated voice call with {user.name} in channel {voice_channel.name}")
        
        # Wait a moment for the connection to stabilize
        await asyncio.sleep(1)
        
        # Play greeting
        greeting_text = "Hey! Ich bin jetzt im Call. Schreib mir eine Nachricht und ich antworte per Sprache!"
        await speak_in_call(call_state, greeting_text)
        
        # Send text instruction
        try:
            instruction_embed = discord.Embed(
                title="📞 Voice Call aktiv",
                description="Ich bin jetzt im Voice-Channel! Da ich deine Sprache (noch) nicht hören kann, "
                           "**schreib mir einfach Nachrichten in einem Text-Channel** und ich antworte per Sprache.",
                color=discord.Color.green()
            )
            instruction_embed.add_field(
                name="💡 Tipp",
                value="Ich reagiere auf deine Nachrichten mit 🎙️ und antworte dann im Voice-Channel.",
                inline=False
            )
            instruction_embed.add_field(
                name="⏱️ Auto-Leave",
                value=f"Ich verlasse den Channel automatisch nach {EMPTY_CHANNEL_TIMEOUT_SECONDS} Sekunden, "
                      f"wenn niemand mehr da ist.",
                inline=False
            )
            await user.send(embed=instruction_embed)
        except (discord.Forbidden, discord.HTTPException) as e:
            # Fallback to simple message if embed fails or can't send DM
            logger.debug(f"Could not send embed instruction: {e}")
            try:
                await user.send(
                    "📞 Ich bin im Voice-Call! Schreib mir Nachrichten in einem Text-Channel und "
                    "ich antworte per Sprache."
                )
            except (discord.Forbidden, discord.HTTPException):
                # User has DMs disabled - already logged above
                logger.debug(f"Could not send fallback DM to {user.name}")
        
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
        reason: Reason for ending call (normal, timeout, empty_channel, error)
    """
    if user_id not in _active_calls:
        return
        
    call_state = _active_calls[user_id]
    
    try:
        # Play goodbye message (skip if empty channel to avoid delay)
        if reason == "timeout":
            goodbye_text = "Der Call ist jetzt schon ziemlich lange. Ich gehe mal, bis später!"
            await speak_in_call(call_state, goodbye_text)
            await asyncio.sleep(3)
        elif reason == "empty_channel":
            goodbye_text = "Alle sind gegangen. Ich verlasse jetzt auch den Channel."
            await speak_in_call(call_state, goodbye_text)
            await asyncio.sleep(2)
        elif reason == "error":
            goodbye_text = "Es gab einen Fehler. Ich muss leider gehen."
            await speak_in_call(call_state, goodbye_text)
            await asyncio.sleep(2)
        else:
            goodbye_text = "War nett zu quatschen! Bis bald!"
            await speak_in_call(call_state, goodbye_text)
            await asyncio.sleep(3)
        
        # Disconnect
        if call_state.voice_client and call_state.voice_client.is_connected():
            await call_state.voice_client.disconnect()
            logger.info(f"Disconnected from voice channel")
        
        # Delete temporary channel if it was created
        if call_state.temp_channel:
            try:
                logger.info(f"Deleting temporary voice channel: {call_state.temp_channel.name}")
                await call_state.temp_channel.delete(reason=f"Temporary call ended: {reason}")
                logger.info(f"Successfully deleted temporary channel")
            except discord.Forbidden:
                logger.warning(f"No permission to delete temporary channel {call_state.temp_channel.name}")
            except discord.NotFound:
                logger.warning(f"Temporary channel {call_state.temp_channel.name} already deleted")
            except Exception as del_error:
                logger.error(f"Error deleting temporary channel: {del_error}")
            
        # Log call duration
        duration = call_state.get_duration()
        logger.info(f"Ended voice call with user {user_id}, duration: {duration}s, reason: {reason}")
        
        # Store call statistics
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO voice_call_stats (user_id, duration_seconds, reason, started_at)
                    VALUES (%s, %s, %s, %s)
                """, (user_id, duration, reason, call_state.start_time))
                conn.commit()
            finally:
                cursor.close()
                conn.close()
            
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
    # Import here to avoid circular dependency
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
            await asyncio.sleep(10)  # Check every 10 seconds for faster empty channel detection
            
            # Check for timeouts and empty channels
            for user_id, call_state in list(_active_calls.items()):
                try:
                    # Check if channel is empty and should leave
                    if call_state.should_leave_empty_channel():
                        logger.info(f"Voice channel empty for {EMPTY_CHANNEL_TIMEOUT_SECONDS}s, leaving call with user {user_id}")
                        await end_voice_call(user_id, reason="empty_channel")
                        continue
                    
                    # Check for general timeout
                    if call_state.is_timed_out():
                        logger.info(f"Voice call with user {user_id} timed out")
                        await end_voice_call(user_id, reason="timeout")
                except Exception as call_error:
                    # Isolate errors per call to prevent one failing call from stopping the monitor
                    logger.error(f"Error processing call for user {user_id}: {call_error}", exc_info=True)
                    try:
                        # Attempt cleanup for the failed call
                        await end_voice_call(user_id, reason="error")
                    except Exception as cleanup_error:
                        # Last resort: just remove from active calls if cleanup also fails
                        logger.error(f"Failed to cleanup call for user {user_id}: {cleanup_error}")
                        _active_calls.pop(user_id, None)
                    
        except Exception as e:
            logger.error(f"Error in voice call monitor loop: {e}", exc_info=True)
            # Monitor continues even if there's an error


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
    conn = get_db_connection()
    if not conn:
        return {
            'total_calls': 0,
            'total_duration': 0,
            'avg_duration': 0,
            'max_duration': 0,
            'unique_users': 0
        }
    
    cursor = conn.cursor()
    try:
        if user_id:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_calls,
                    SUM(duration_seconds) as total_duration,
                    AVG(duration_seconds) as avg_duration,
                    MAX(duration_seconds) as max_duration
                FROM voice_call_stats
                WHERE user_id = %s
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_calls,
                    SUM(duration_seconds) as total_duration,
                    AVG(duration_seconds) as avg_duration,
                    MAX(duration_seconds) as max_duration,
                    COUNT(DISTINCT user_id) as unique_users
                FROM voice_call_stats
            """)
            
        result = cursor.fetchone()
        
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
                'max_duration': 0,
                'unique_users': 0
            }
    finally:
        cursor.close()
        conn.close()


async def handle_text_in_voice_call(
    message: discord.Message,
    config: dict,
    gemini_key: str,
    openai_key: str,
    system_prompt: str
) -> bool:
    """
    Handle text messages sent during an active voice call.
    This serves as a workaround for the lack of audio receiving in discord.py.
    
    Args:
        message: Discord message
        config: Bot configuration
        gemini_key: Gemini API key
        openai_key: OpenAI API key
        system_prompt: System prompt for AI
        
    Returns:
        True if message was handled in a voice call context, False otherwise
    """
    # Check if user is in an active call
    call_state = get_active_call(message.author.id)
    if not call_state:
        return False
    
    # Check if message is in the same guild as the call (skip DM channels)
    if isinstance(message.channel, discord.DMChannel):
        return False
    
    if message.channel.guild != call_state.channel.guild:
        return False
    
    try:
        # Log the text input
        user_text = message.content
        logger.info(f"Text message in voice call from {message.author.display_name}: {user_text}")
        
        # Add to conversation history
        call_state.add_to_history(message.author.display_name, user_text)
        call_state.update_activity()
        
        # React to show message was received
        try:
            await message.add_reaction("🎙️")
        except discord.NotFound:
            logger.debug(f"Message {message.id} was deleted before reaction could be added")
        except (discord.Forbidden, discord.HTTPException) as e:
            logger.debug(f"Could not add reaction to message: {e}")
        
        # Get AI response and speak it
        await handle_voice_conversation(
            call_state,
            user_text,
            config,
            gemini_key,
            openai_key,
            system_prompt
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Error handling text in voice call: {e}", exc_info=True)
        return False
