# Voice System Setup Guide

## Overview

The Sulfur bot includes voice call capabilities with Text-to-Speech (TTS) and Speech-to-Text (STT) functionality. This guide covers setup, troubleshooting, and platform-specific requirements.

## Requirements

### Core Dependencies (Required for TTS)

1. **py-cord[voice]** - Discord library with voice receiving support
   - Install: `pip install py-cord[voice]`
   - Replaces standard discord.py
   - Includes voice receiving with discord.sinks
   - See [PYCORD_MIGRATION_GUIDE.md](PYCORD_MIGRATION_GUIDE.md) for migration help

2. **edge-tts** - Free Microsoft Edge TTS service
   - Install: `pip install edge-tts`
   - Used for generating speech from text

3. **PyNaCl** - Voice encryption library
   - Install: `pip install PyNaCl`
   - Termux requires: `pkg install libsodium clang` first
   - Required for Discord voice connections

4. **FFmpeg** - Audio processing tool
   - **Termux**: `pkg install ffmpeg`
   - **Linux**: `sudo apt install ffmpeg`
   - **Windows**: Download from https://ffmpeg.org/download.html
   - Required for playing audio in Discord voice channels

### Optional Dependencies (For STT)

5. **SpeechRecognition** - Local speech recognition
   - Install: `pip install SpeechRecognition`
   - Provides Google Speech Recognition API (free but requires internet)
   - Optional: Use Whisper API with OpenAI key for better quality

## Platform-Specific Setup

### Termux (Android)

The `termux_quickstart.sh` script now automatically installs all required dependencies:

```bash
cd ~/sulfur
bash termux_quickstart.sh
```

This will install:
- ffmpeg (for audio playback)
- libsodium and clang (for PyNaCl)
- All Python packages including edge-tts and SpeechRecognition

#### Manual Installation (if needed)

```bash
# Install system packages
pkg update
pkg install -y ffmpeg libsodium clang

# Install Python packages
cd ~/sulfur
source venv/bin/activate
pip install -r requirements.txt
```

### Linux/WSL

```bash
# Install FFmpeg
sudo apt update
sudo apt install -y ffmpeg

# Install Python packages
cd ~/sulfur
source venv/bin/activate
pip install -r requirements.txt
```

### Windows

1. **Install FFmpeg**:
   - Download from https://ffmpeg.org/download.html
   - Extract to `C:\ffmpeg`
   - Add `C:\ffmpeg\bin` to system PATH

2. **Install Python packages**:
   ```powershell
   cd sulfur
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

## Verifying Installation

### Check Dependencies on Bot Startup

When the bot starts, it will automatically check and log all voice dependencies:

```
Checking voice system dependencies...
=== Voice System Dependency Check ===
  edge-tts (TTS):            ✓ Available
  FFmpeg (Audio playback):   ✓ Available
  PyNaCl (Voice encryption): ✓ Available
  SpeechRecognition (STT):   ✓ Available
=====================================
  ✓ Voice system is ready!
  -> Testing TTS connectivity...
  ✓ TTS connectivity test passed!
```

### Manual Dependency Check

```bash
# Check FFmpeg
which ffmpeg  # Linux/Termux
where ffmpeg  # Windows

# Check Python packages
pip list | grep -E "edge-tts|PyNaCl|SpeechRecognition"
```

### Test TTS Functionality

```python
# Quick test script
python -c "
import asyncio
from modules.voice_tts import text_to_speech, check_voice_dependencies

# Check dependencies
deps = check_voice_dependencies()
print('Dependencies:', deps)

# Test TTS
async def test():
    audio_file = await text_to_speech('Hello, this is a test')
    if audio_file:
        print(f'✓ TTS working! Generated: {audio_file}')
    else:
        print('✗ TTS failed')

asyncio.run(test())
"
```

## Troubleshooting

### TTS: "NoAudioReceived" Errors

**Symptoms:**
```
[WARNING] NoAudioReceived error on attempt 1/3 with voice de-DE-KillianNeural
[ERROR] Failed to generate TTS audio after all retries
```

**Causes and Solutions:**

1. **Network Issues**
   - edge-tts requires internet access to Microsoft's TTS service
   - Test connectivity: `ping 8.8.8.8`
   - Try different network (WiFi ↔ Mobile Data)

2. **Firewall/VPN Blocking**
   - Some networks block TTS services
   - Disable VPN temporarily to test
   - Check if your organization/ISP blocks Microsoft services

3. **edge-tts Not Installed**
   ```bash
   pip install edge-tts
   ```

4. **Service Timeout**
   - The bot now uses 15-second timeout with retries
   - If still failing, your network may be too slow
   - Check logs for: `TTS save operation timed out after 15s`

### Voice Playback: No Audio in Discord

**Symptoms:**
- TTS generates audio files successfully
- Bot joins voice channel
- No audio plays in Discord

**Solutions:**

1. **FFmpeg Not Installed**
   ```bash
   # Termux
   pkg install ffmpeg
   
   # Linux
   sudo apt install ffmpeg
   
   # Verify
   ffmpeg -version
   ```

2. **FFmpeg Not in PATH** (Windows)
   - Add FFmpeg `bin` directory to system PATH
   - Restart terminal/bot after adding to PATH

3. **Bot Missing Voice Permissions**
   - Ensure bot has "Connect" and "Speak" permissions
   - Re-invite bot with proper permissions if needed

### Voice Connection: PyNaCl Errors

**Symptoms:**
```
[ERROR] PyNaCl library is not installed
RuntimeError: PyNaCl library needed in order to use voice
```

**Solutions:**

1. **Termux**: Install dependencies first
   ```bash
   pkg install libsodium clang
   export SODIUM_INSTALL=system
   pip install PyNaCl
   ```

2. **Linux/Windows**:
   ```bash
   pip install PyNaCl
   ```

3. **Verify Installation**:
   ```python
   python -c "import nacl; print('✓ PyNaCl installed')"
   ```

### STT: Transcription Not Working

**Solution as of Latest Update:**
The bot now uses **py-cord** which includes built-in voice receiving support!

**How It Works:**
1. Bot joins voice channel
2. Bot speaks responses using TTS
3. **Bot can now hear you speak** - Real-time audio capture
4. Bot transcribes your speech using:
   - Google Speech Recognition (free, requires internet)
   - OpenAI Whisper API (best quality, requires API key in .env)
5. Bot responds via voice TTS

**Setup Requirements:**
- Install py-cord: `pip install py-cord[voice]` (done automatically with requirements.txt)
- Optional: Add `OPENAI_API_KEY` to `.env` for Whisper transcription
- Ensure FFmpeg and PyNaCl are installed

**Verification:**
Check bot startup logs for:
```
Discord Voice Receiving:   ✓ Supported
```

If you see `✗ NOT SUPPORTED`, run:
```bash
pip uninstall discord.py
pip install py-cord[voice]
```

See [PYCORD_MIGRATION_GUIDE.md](PYCORD_MIGRATION_GUIDE.md) for detailed instructions.

**Fallback Mode:**
If py-cord is not installed, the bot falls back to text message input:
- Bot joins voice channel and speaks
- You type messages in a text channel
- Bot adds 🎙️ reaction and responds via voice

## Voice Call Features

### Starting a Voice Call

**Admin Command:**
```
/admin force_voice_call @user [create_channel:True]
```

Options:
- `create_channel: True` - Creates a temporary voice channel (default)
- `create_channel: False` - Joins user's current voice channel

### During a Call

1. **Bot speaks greeting** when it joins
2. **Send text messages** in any channel - bot responds via voice
3. **Bot leaves automatically** after 30 seconds if channel is empty
4. **Manual end**: Bot will cleanup temporary channels

### Voice Call Stats

```
/admin voice_debug
```

Shows:
- Active calls
- Call durations
- Participants
- Total call statistics

## Configuration

### TTS Voice Settings

Edit `modules/voice_tts.py`:

```python
SULFUR_VOICE = "de-DE-KillianNeural"  # Primary voice
SULFUR_VOICE_ALT = "de-DE-ConradNeural"  # Fallback voice
VOICE_RATE = "+0%"  # Speech speed: -50% to +100%
VOICE_PITCH = "+0Hz"  # Voice pitch: -50Hz to +50Hz
```

### Retry Configuration

```python
TTS_MAX_RETRIES = 3  # Number of retry attempts
TTS_RETRY_DELAY = 1.0  # Initial delay (exponential backoff)
```

### Voice Activity Detection (VAD)

Edit `modules/voice_conversation.py`:

```python
VAD_ENABLED = True  # Enable VAD
VAD_ENERGY_THRESHOLD = 300  # Minimum audio energy
VAD_SILENCE_DURATION = 1.0  # Silence before speech end
```

## Network Requirements

### Required Domains

The bot needs access to:
- `speech.platform.bing.com` - Microsoft Edge TTS
- `generativelanguage.googleapis.com` - Gemini AI (for responses)
- `api.openai.com` - OpenAI (if using Whisper STT)

### Bandwidth

- **TTS**: ~5-10 KB per spoken sentence
- **STT**: ~50-100 KB per second of audio (if implemented)
- Minimal bandwidth required for basic operation

### Latency

- TTS generation: 1-5 seconds typical
- Voice response: 2-7 seconds total (AI + TTS)
- Lower latency with good connection

## Best Practices

### For Termux Users

1. **Keep device charged** - Voice features use CPU
2. **Stable WiFi** - Mobile data may be unreliable
3. **Acquire wake lock** - Long-press Termux notification
4. **Disable battery optimization** - For Termux app
5. **Monitor logs** - Check for TTS errors: `tail -f logs/session_*.log`

### For All Users

1. **Test TTS on startup** - Check logs for connectivity test results
2. **Monitor network** - TTS requires stable internet
3. **Use text fallback** - Bot sends text DM if TTS fails
4. **Check dependencies** - Run `bash verify_termux_setup.sh` (Termux)

## Advanced: Voice Receiving Setup

### Using Py-Cord (Recommended)

Py-cord includes built-in voice receiving - just install it and it works!

```bash
# Uninstall discord.py first
pip uninstall discord.py

# Install py-cord with voice support
pip install py-cord[voice]

# Or use requirements.txt (already updated)
pip install -r requirements.txt
```

**Verification:**
```python
python3 -c "from discord import sinks; print('✓ Voice receiving supported!')"
```

**What It Enables:**
- Real-time audio capture from voice channels
- Automatic voice activity detection
- Built-in audio sinks (WaveSink, MP3Sink, etc.)
- Speaker identification support

### Whisper API Transcription

Already implemented in code - just add your OpenAI key:

```python
# Set in .env
OPENAI_API_KEY=sk-...

# Bot will automatically use Whisper for transcription
# if py-cord is installed
```

**Transcription Priority:**
1. OpenAI Whisper API (best quality, if key provided)
2. Google Speech Recognition (free, fallback)

### Troubleshooting Voice Receiving

**Check if py-cord is installed:**
```bash
pip list | grep py-cord
# Should show: py-cord  x.x.x
```

**Check for discord.py (should NOT be installed):**
```bash
pip list | grep discord.py
# Should be empty
```

**Test voice receiving support:**
```python
python3 -c "
from modules.voice_audio_sink import check_voice_receiving_support
support = check_voice_receiving_support()
print(f'Voice Receiving: {support}')
"
```

**Check bot logs on startup:**
```bash
grep "Voice Receiving System Check" logs/session_*.log
```

Should show:
```
Discord Voice Receiving:   ✓ Supported
```

See [PYCORD_MIGRATION_GUIDE.md](PYCORD_MIGRATION_GUIDE.md) for complete migration instructions.

## Logs and Debugging

### Voice System Logs

```bash
# Watch voice-related logs
tail -f logs/session_*.log | grep -E "\[Voice\]|\[TTS\]|\[STT\]"

# Check TTS errors
grep "NoAudioReceived\|TTS.*failed" logs/session_*.log

# Check voice dependencies
grep "Voice System Dependency" logs/session_*.log
```

### Debug Mode

Enable detailed logging in `bot.py`:

```python
logger.setLevel(logging.DEBUG)
```

This shows:
- Every TTS attempt
- Full error traces
- Network requests
- Audio file details

## FAQ

**Q: Why can't the bot hear me?**  
A: You need py-cord installed for voice receiving. Run: `pip uninstall discord.py && pip install py-cord[voice]`. The bot will automatically detect py-cord and enable voice receiving. See [PYCORD_MIGRATION_GUIDE.md](PYCORD_MIGRATION_GUIDE.md) for details.

**Q: TTS fails with "NoAudioReceived" - what to do?**  
A: This usually means network issues or edge-tts service unavailable. Check internet, try different network, wait a few minutes and retry.

**Q: Does voice work offline?**  
A: No, both TTS (edge-tts) and AI responses require internet. Local TTS could be added as a future feature.

**Q: Can I change the voice?**  
A: Yes, edit `SULFUR_VOICE` in `modules/voice_tts.py`. Use `/admin test_voices` to list available voices (if implemented).

**Q: Why is TTS slow?**  
A: TTS generation takes 1-5 seconds depending on text length and network speed. The bot uses retries with exponential backoff which can add delays.

**Q: Voice features not working on Termux?**  
A: Run `bash verify_termux_setup.sh` and check that FFmpeg, edge-tts, PyNaCl, and py-cord are all installed.

**Q: What's the difference between discord.py and py-cord?**  
A: Py-cord is a fork of discord.py with additional features, including built-in voice receiving. They're API-compatible, so switching is seamless.

## Support

If voice features still don't work after following this guide:

1. **Collect diagnostic info**:
   ```bash
   # System info
   python -V
   uname -m  # or systeminfo on Windows
   
   # Check dependencies
   which ffmpeg
   pip list | grep -E "edge-tts|PyNaCl|SpeechRecognition"
   
   # Recent logs
   tail -n 100 logs/session_*.log
   ```

2. **Run test script**:
   ```bash
   python -c "from modules.voice_tts import check_voice_dependencies, log_voice_system_status; print(check_voice_dependencies()); log_voice_system_status()"
   ```

3. **Check bot startup logs** for voice system check results

4. **Test TTS manually**:
   ```bash
   python -c "import asyncio; from modules.voice_tts import text_to_speech; asyncio.run(text_to_speech('test'))"
   ```

Include all output when asking for help!
