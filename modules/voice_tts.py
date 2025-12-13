"""
Voice TTS and Transcription Module for Sulfur Bot

Handles text-to-speech in voice channels and speech-to-text transcription.
Uses edge-tts for TTS (free) and plans for Whisper API for transcription.
"""

import asyncio
import tempfile
import os
import shutil
import socket
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
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
    import nacl  # Note: PyNaCl package imports as 'nacl'
    PYNACL_AVAILABLE = True
except ImportError:
    PYNACL_AVAILABLE = False
    logger.warning("PyNaCl not available. Install with: pip install PyNaCl")

# Check for SpeechRecognition (optional for STT)
try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False
    logger.info("SpeechRecognition not available (optional). Install with: pip install SpeechRecognition")


# Sulfur's voice configuration
SULFUR_VOICE = "de-DE-KillianNeural"  # Male German voice with personality
SULFUR_VOICE_ALT = "de-DE-ConradNeural"  # Alternative voice

# Voice settings
VOICE_RATE = "+0%"  # Normal speed
VOICE_PITCH = "+0Hz"  # Normal pitch

# Retry configuration for TTS
TTS_MAX_RETRIES = 3  # Maximum number of retry attempts
TTS_RETRY_DELAY = 1.0  # Initial retry delay in seconds (exponential backoff)

# Circuit breaker configuration
CIRCUIT_BREAKER_THRESHOLD = 5  # Number of consecutive failures before opening circuit
CIRCUIT_BREAKER_TIMEOUT = 300  # Seconds to wait before trying again (5 minutes)

# Edge TTS service configuration
EDGE_TTS_HOST = 'speech.platform.bing.com'  # Microsoft Edge TTS service host
EDGE_TTS_PORT = 443  # HTTPS port for Edge TTS service

# TTS Service health tracking (circuit breaker pattern)
class TTSServiceHealth:
    """
    Tracks TTS service health to avoid repeated attempts when service is down.
    
    Implements a three-state circuit breaker:
    - CLOSED: Normal operation, requests are allowed
    - OPEN: Service is failing, requests are blocked
    - HALF_OPEN: Testing if service recovered, one request allowed
    """
    def __init__(self):
        self.consecutive_failures = 0
        self.last_failure_time: Optional[datetime] = None
        self.circuit_open = False
        self.half_open = False  # Explicit half-open state
        self.last_success_time: Optional[datetime] = None
        
    def record_success(self):
        """Record successful TTS generation. Closes circuit completely."""
        self.consecutive_failures = 0
        self.circuit_open = False
        self.half_open = False
        self.last_success_time = datetime.now()
        logger.debug("TTS service health: Circuit closed, service is working")
        
    def record_failure(self):
        """Record failed TTS generation."""
        self.consecutive_failures += 1
        self.last_failure_time = datetime.now()
        
        # If we were in half-open state and failed, immediately re-open circuit
        if self.half_open:
            self.circuit_open = True
            self.half_open = False
            logger.warning("TTS service still failing, circuit re-opened immediately")
            return
        
        # Otherwise, check if we've reached the threshold to open circuit
        if self.consecutive_failures >= CIRCUIT_BREAKER_THRESHOLD:
            self.circuit_open = True
            self.half_open = False
            logger.warning(
                f"TTS service circuit breaker opened after {self.consecutive_failures} consecutive failures. "
                f"Will wait {CIRCUIT_BREAKER_TIMEOUT}s before retrying."
            )
        else:
            logger.debug(f"TTS service health: {self.consecutive_failures}/{CIRCUIT_BREAKER_THRESHOLD} failures")
    
    def is_circuit_open(self) -> bool:
        """Check if circuit breaker is open (service unavailable)."""
        if not self.circuit_open:
            return False
            
        # Check if enough time has passed to try again (transition to half-open)
        if self.last_failure_time:
            time_since_failure = (datetime.now() - self.last_failure_time).total_seconds()
            if time_since_failure >= CIRCUIT_BREAKER_TIMEOUT:
                logger.info(f"TTS circuit breaker timeout expired ({CIRCUIT_BREAKER_TIMEOUT}s), entering half-open state")
                # Transition to half-open: Allow one retry attempt
                self.circuit_open = False
                self.half_open = True
                return False
        
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """Get current service health status."""
        # Determine state string for clarity
        if self.circuit_open:
            state = "OPEN"
        elif self.half_open:
            state = "HALF_OPEN"
        else:
            state = "CLOSED"
        
        return {
            'state': state,
            'circuit_open': self.circuit_open,
            'half_open': self.half_open,
            'consecutive_failures': self.consecutive_failures,
            'last_failure': self.last_failure_time,
            'last_success': self.last_success_time,
        }
    
    def reset(self):
        """
        Reset the circuit breaker to initial state.
        Should only be called by admins when they know the service is back up.
        """
        self.consecutive_failures = 0
        self.last_failure_time = None
        self.circuit_open = False
        self.half_open = False
        logger.info("TTS service health reset to initial state")

# Global service health tracker
_tts_service_health = TTSServiceHealth()


# --- Network Diagnostics ---

async def check_network_connectivity() -> Dict[str, Any]:
    """
    Perform basic network connectivity checks using async operations.
    
    Returns:
        Dictionary with connectivity test results
    """
    results = {
        'dns_resolution': False,
        'tcp_connection': False,
        'edge_tts_host': EDGE_TTS_HOST,
        'edge_tts_port': EDGE_TTS_PORT,
        'error': None
    }
    
    try:
        # Test DNS resolution using asyncio (non-blocking)
        try:
            # Use get_running_loop() which is the modern approach
            loop = asyncio.get_running_loop()
            # getaddrinfo returns address info, which confirms DNS resolution
            await loop.getaddrinfo(EDGE_TTS_HOST, EDGE_TTS_PORT, family=socket.AF_INET)
            results['dns_resolution'] = True
            logger.debug(f"DNS resolution successful for {EDGE_TTS_HOST}")
        except socket.gaierror as dns_error:
            results['error'] = f"DNS resolution failed: {dns_error}"
            logger.warning(results['error'])
            return results
        
        # Test TCP connection using asyncio (non-blocking)
        try:
            # open_connection is async and non-blocking
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(EDGE_TTS_HOST, EDGE_TTS_PORT),
                timeout=5.0
            )
            results['tcp_connection'] = True
            logger.debug(f"TCP connection successful to {EDGE_TTS_HOST}:{EDGE_TTS_PORT}")
            
            # Close the connection properly
            writer.close()
            await writer.wait_closed()
            
        except asyncio.TimeoutError:
            results['error'] = "TCP connection timed out"
            logger.warning(results['error'])
            return results
        except (socket.error, OSError) as conn_error:
            results['error'] = f"TCP connection failed: {conn_error}"
            logger.warning(results['error'])
            return results
            
    except Exception as e:
        results['error'] = f"Network check failed: {e}"
        logger.error(results['error'])
    
    return results


async def diagnose_tts_failure() -> str:
    """
    Run diagnostics to identify TTS failure cause.
    
    Returns:
        Diagnostic message string
    """
    diagnostics = []
    
    # Check if edge-tts is available
    if not EDGE_TTS_AVAILABLE:
        diagnostics.append("❌ edge-tts library is not installed")
        diagnostics.append("   Install with: pip install edge-tts")
        return "\n".join(diagnostics)
    
    # Check network connectivity
    network_status = await check_network_connectivity()
    
    if not network_status['dns_resolution']:
        diagnostics.append(f"❌ DNS resolution failed for {network_status['edge_tts_host']}")
        diagnostics.append("   Possible causes:")
        diagnostics.append("   - No internet connection")
        diagnostics.append("   - DNS server issues")
        diagnostics.append("   - Network firewall blocking DNS")
        diagnostics.append(f"   Error: {network_status.get('error', 'Unknown')}")
    elif not network_status['tcp_connection']:
        diagnostics.append(f"❌ Cannot connect to {network_status['edge_tts_host']}:443")
        diagnostics.append("   Possible causes:")
        diagnostics.append("   - Firewall blocking HTTPS connections")
        diagnostics.append("   - Proxy configuration required")
        diagnostics.append("   - Microsoft services blocked in your region")
        diagnostics.append(f"   Error: {network_status.get('error', 'Unknown')}")
    else:
        diagnostics.append(f"✓ Network connectivity to {network_status['edge_tts_host']} is working")
        diagnostics.append("   The issue may be:")
        diagnostics.append("   - Temporary service outage")
        diagnostics.append("   - Rate limiting by Microsoft")
        diagnostics.append("   - SSL/TLS certificate issues")
    
    # Check circuit breaker status
    health_status = _tts_service_health.get_status()
    state = health_status.get('state', 'UNKNOWN')
    if state != 'CLOSED':
        diagnostics.append(f"⚠️  TTS circuit breaker is {state}")
        diagnostics.append(f"   Failed {health_status['consecutive_failures']} times consecutively")
        if health_status['last_failure']:
            diagnostics.append(f"   Last failure: {health_status['last_failure'].strftime('%Y-%m-%d %H:%M:%S')}")
        if state == 'HALF_OPEN':
            diagnostics.append("   Currently testing if service has recovered")
    
    return "\n".join(diagnostics)


# --- TTS Functions ---

async def text_to_speech(text: str, output_file: Optional[str] = None) -> Optional[str]:
    """
    Convert text to speech using edge-tts with retry mechanism.
    
    Implements exponential backoff retry logic and fallback to alternative voice
    to handle intermittent network issues and service unavailability.
    Includes circuit breaker pattern to avoid repeated failures when service is down.
    
    Args:
        text: Text to convert to speech
        output_file: Optional output file path. If None, creates temp file.
    
    Returns:
        Path to the audio file, or None if failed after all retries
    """
    # Check circuit breaker first
    if _tts_service_health.is_circuit_open():
        logger.warning("TTS circuit breaker is OPEN - service is unavailable, skipping TTS attempt")
        logger.warning(f"Circuit will reset after {CIRCUIT_BREAKER_TIMEOUT}s timeout")
        return None
    
    if not EDGE_TTS_AVAILABLE:
        logger.error("edge-tts is not available - cannot generate TTS audio")
        logger.error("Install edge-tts with: pip install edge-tts")
        logger.error("For Termux: pip install edge-tts (inside virtual environment)")
        return None
    
    # Validate input text
    if not text or not isinstance(text, str):
        logger.error("TTS text is None or not a string")
        return None
    
    # Strip whitespace and check if text is empty
    text_stripped = text.strip()
    if not text_stripped:
        logger.error("TTS text is empty or contains only whitespace")
        return None
    
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
    
    # Try with primary voice, then fallback voice with retries
    voices_to_try = [SULFUR_VOICE, SULFUR_VOICE_ALT]
    
    for voice_index, voice in enumerate(voices_to_try):
        for attempt in range(TTS_MAX_RETRIES):
            try:
                # Log attempt info
                if attempt > 0:
                    logger.info(f"TTS retry attempt {attempt + 1}/{TTS_MAX_RETRIES} with voice {voice}")
                else:
                    logger.debug(f"Generating TTS for text: {text_stripped[:50]}... (voice: {voice})")
                
                # Generate TTS with validated text
                communicate = edge_tts.Communicate(
                    text=text_stripped,
                    voice=voice,
                    rate=VOICE_RATE,
                    pitch=VOICE_PITCH
                )
                
                # Use longer timeout for edge-tts save operation
                try:
                    await asyncio.wait_for(communicate.save(output_file), timeout=15.0)
                except asyncio.TimeoutError:
                    logger.warning(f"TTS save operation timed out after 15s on attempt {attempt + 1}/{TTS_MAX_RETRIES}")
                    # Clean up any partial file
                    if output_file and os.path.exists(output_file):
                        try:
                            os.remove(output_file)
                        except (OSError, FileNotFoundError):
                            pass
                    # Try next attempt
                    if attempt < TTS_MAX_RETRIES - 1:
                        retry_delay = TTS_RETRY_DELAY * (2 ** attempt)
                        logger.info(f"Waiting {retry_delay}s before retry...")
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        # All retries with this voice exhausted
                        logger.warning(f"All {TTS_MAX_RETRIES} retries failed with voice {voice} due to timeouts")
                        # Break to try next voice (failure recorded only after all voices exhausted)
                        break
                
                # Verify the file was created and has content
                if not os.path.exists(output_file):
                    logger.warning(f"TTS file was not created: {output_file}")
                    # Try next attempt or next voice
                    continue
                
                file_size = os.path.getsize(output_file)
                if file_size == 0:
                    logger.warning(f"TTS file is empty: {output_file}")
                    try:
                        os.remove(output_file)
                    except (OSError, FileNotFoundError):
                        pass
                    # Try next attempt or next voice
                    continue
                
                # Success!
                if voice_index > 0 or attempt > 0:
                    logger.info(f"TTS succeeded with voice {voice} on attempt {attempt + 1}")
                logger.debug(f"Generated TTS audio: {output_file} ({file_size} bytes)")
                
                # Record success in circuit breaker
                _tts_service_health.record_success()
                
                return output_file
                
            except edge_tts.exceptions.NoAudioReceived as e:
                # Specific handling for NoAudioReceived error
                logger.warning(f"NoAudioReceived error on attempt {attempt + 1}/{TTS_MAX_RETRIES} with voice {voice}: {e}")
                logger.warning("This may indicate: 1) Network issues, 2) Edge TTS service unavailable, 3) Invalid voice name")
                
                # Clean up any partial file
                if output_file and os.path.exists(output_file):
                    try:
                        os.remove(output_file)
                    except (OSError, FileNotFoundError):
                        pass
                
                # If not the last retry, wait before retrying (exponential backoff)
                if attempt < TTS_MAX_RETRIES - 1:
                    retry_delay = TTS_RETRY_DELAY * (2 ** attempt)  # 1s, 2s, 4s
                    logger.info(f"Waiting {retry_delay}s before retry...")
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    # Last retry with this voice failed
                    logger.warning(f"All {TTS_MAX_RETRIES} retries failed with voice {voice}")
                    break
                    
            except Exception as e:
                # Other unexpected errors (including if NoAudioReceived doesn't exist in edge-tts version)
                error_type = type(e).__name__
                
                # Check if this is a NoAudioReceived error by name (for compatibility)
                is_no_audio = (error_type == "NoAudioReceived" or 
                              "NoAudioReceived" in str(type(e)) or
                              "no audio" in str(e).lower())
                
                if is_no_audio:
                    logger.warning(f"NoAudioReceived error on attempt {attempt + 1}/{TTS_MAX_RETRIES} with voice {voice}: {e}")
                    logger.warning("This may indicate: 1) Network issues, 2) Edge TTS service unavailable, 3) Invalid voice name")
                else:
                    logger.error(f"Unexpected error generating TTS ({error_type}) on attempt {attempt + 1}: {e}")
                
                # Clean up partial file if it exists
                if output_file and os.path.exists(output_file):
                    try:
                        os.remove(output_file)
                    except (OSError, FileNotFoundError):
                        pass
                
                # Use exponential backoff for all errors on retries
                if attempt < TTS_MAX_RETRIES - 1:
                    retry_delay = TTS_RETRY_DELAY * (2 ** attempt)  # 1s, 2s, 4s
                    logger.info(f"Waiting {retry_delay}s before retry...")
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    # Last retry with this voice failed
                    logger.warning(f"All {TTS_MAX_RETRIES} retries failed with voice {voice}")
                    break
    
    # All retries and fallback voices exhausted
    # Record failure in circuit breaker
    _tts_service_health.record_failure()
    
    logger.error("Failed to generate TTS audio after all retries and fallback voices")
    logger.error(f"TTS parameters - Voices tried: {voices_to_try}, Rate: {VOICE_RATE}, Pitch: {VOICE_PITCH}")
    logger.error(f"Text length: {len(text_stripped)} characters")
    logger.error(f"Text preview: {text_stripped[:100]}")
    
    # Run diagnostics to help identify the issue
    logger.error("Running TTS diagnostics...")
    diagnostic_msg = await diagnose_tts_failure()
    for line in diagnostic_msg.split('\n'):
        logger.error(f"  {line}")
    
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
    audio_file = None
    try:
        if not voice_client or not voice_client.is_connected():
            logger.error("Voice client not connected")
            return False
        
        # Validate text before attempting TTS
        if not text or not text.strip():
            logger.error("Cannot speak empty or whitespace-only text")
            return False
        
        # Stop current playback if any
        if voice_client.is_playing():
            voice_client.stop()
        
        # Generate TTS audio
        audio_file = await text_to_speech(text)
        if not audio_file:
            logger.error("Failed to generate TTS audio file")
            return False
        
        # Play audio with error handling
        try:
            # FFmpeg options for better MP3 support
            ffmpeg_options = {
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                'options': '-vn'  # No video
            }
            audio_source = FFmpegPCMAudio(audio_file, **ffmpeg_options)
        except Exception as ffmpeg_error:
            logger.error(f"Error creating FFmpeg audio source: {ffmpeg_error}", exc_info=True)
            await cleanup_audio_file(audio_file)
            return False
        
        # Error callback for playback
        playback_error = {'error': None}
        def after_callback(error):
            if error:
                playback_error['error'] = error
                logger.error(f"Playback error: {error}")
        
        voice_client.play(audio_source, after=after_callback)
        
        logger.info(f"Speaking in voice channel: {text[:50]}...")
        
        # Wait for playback to complete
        if wait_for_completion:
            while voice_client.is_playing():
                await asyncio.sleep(0.1)
            
            # Check for playback errors
            if playback_error['error']:
                logger.error(f"Audio playback failed: {playback_error['error']}")
                return False
            
            # Cleanup audio file
            await cleanup_audio_file(audio_file)
        else:
            # Schedule cleanup for later
            asyncio.create_task(cleanup_audio_file(audio_file))
        
        return True
    except Exception as e:
        logger.error(f"Error speaking in channel: {e}", exc_info=True)
        if audio_file:
            try:
                os.remove(audio_file)
            except (OSError, FileNotFoundError) as cleanup_error:
                logger.debug(f"Could not remove audio file: {cleanup_error}")
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
        'pynacl': PYNACL_AVAILABLE,
        'speech_recognition': SPEECH_RECOGNITION_AVAILABLE,
    }
    
    # Check for ffmpeg
    dependencies['ffmpeg'] = shutil.which('ffmpeg') is not None
    
    return dependencies


def log_voice_system_status():
    """Log the status of all voice system dependencies."""
    deps = check_voice_dependencies()
    
    logger.info("=== Voice System Dependency Check ===")
    logger.info(f"  edge-tts (TTS):            {'✓ Available' if deps['edge_tts'] else '✗ NOT INSTALLED'}")
    logger.info(f"  FFmpeg (Audio playback):   {'✓ Available' if deps['ffmpeg'] else '✗ NOT INSTALLED'}")
    logger.info(f"  PyNaCl (Voice encryption): {'✓ Available' if deps['pynacl'] else '✗ NOT INSTALLED'}")
    logger.info(f"  SpeechRecognition (STT):   {'✓ Available' if deps['speech_recognition'] else '✗ NOT INSTALLED (optional)'}")
    
    if not deps['edge_tts']:
        logger.warning("TTS will NOT work without edge-tts. Install: pip install edge-tts")
    
    if not deps['ffmpeg']:
        logger.warning("Voice playback will NOT work without FFmpeg.")
        logger.warning("For Termux: pkg install ffmpeg")
        logger.warning("For Linux: sudo apt install ffmpeg")
        logger.warning("For Windows: Download from https://ffmpeg.org/download.html")
    
    if not deps['pynacl']:
        logger.warning("Voice features will NOT work without PyNaCl.")
        logger.warning("For Termux: pkg install libsodium clang && pip install PyNaCl")
        logger.warning("For Linux/Windows: pip install PyNaCl")
    
    logger.info("=====================================")
    
    # Return True if core dependencies are available
    return deps['edge_tts'] and deps['ffmpeg'] and deps['pynacl']


async def test_tts_connectivity() -> bool:
    """
    Test if edge-tts service is accessible and working.
    Runs network diagnostics if test fails.
    
    Returns:
        True if TTS is working, False otherwise
    """
    if not EDGE_TTS_AVAILABLE:
        logger.warning("edge-tts is not installed")
        return False
    
    # First, run network diagnostics
    logger.info("Testing TTS service connectivity...")
    network_status = await check_network_connectivity()
    
    if not network_status['dns_resolution']:
        logger.error("TTS connectivity test failed: DNS resolution failed")
        logger.error(f"Error: {network_status.get('error', 'Unknown')}")
        return False
    
    if not network_status['tcp_connection']:
        logger.error("TTS connectivity test failed: Cannot connect to edge-tts service")
        logger.error(f"Error: {network_status.get('error', 'Unknown')}")
        return False
    
    logger.info("Network connectivity OK, testing actual TTS generation...")
    
    # Try to generate a very short test audio
    test_text = "Test"
    temp_file = tempfile.NamedTemporaryFile(suffix='.mp3', prefix='tts_test_', delete=False)
    test_file = temp_file.name
    temp_file.close()
    
    try:
        # Try to communicate with edge-tts service
        communicate = edge_tts.Communicate(
            text=test_text,
            voice=SULFUR_VOICE
        )
        
        # Set a timeout for the test
        await asyncio.wait_for(communicate.save(test_file), timeout=10.0)
        
        # Check if file was created and has content
        if os.path.exists(test_file) and os.path.getsize(test_file) > 0:
            logger.info("✓ TTS connectivity test passed - service is working")
            _tts_service_health.record_success()
            return True
        else:
            logger.warning("TTS connectivity test failed - no audio generated")
            _tts_service_health.record_failure()
            return False
            
    except asyncio.TimeoutError:
        logger.warning("TTS connectivity test timed out - edge-tts service may be unreachable")
        _tts_service_health.record_failure()
        return False
    except Exception as e:
        logger.warning(f"TTS connectivity test failed: {e}")
        _tts_service_health.record_failure()
        return False
    finally:
        # Always clean up test file
        try:
            if os.path.exists(test_file):
                os.remove(test_file)
        except (OSError, FileNotFoundError):
            pass


def get_tts_service_health() -> Dict[str, Any]:
    """
    Get the current TTS service health status.
    
    Returns:
        Dictionary with service health information
    """
    return _tts_service_health.get_status()


def reset_tts_circuit_breaker():
    """
    Manually reset the TTS circuit breaker.
    Should only be called by admins when they know the service is back up.
    """
    _tts_service_health.reset()
    logger.info("TTS circuit breaker manually reset by admin")
