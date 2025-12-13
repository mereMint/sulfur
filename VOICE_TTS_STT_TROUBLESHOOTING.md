# Voice TTS/STT Troubleshooting Guide

## Problem: "NoAudioReceived" errors and voice not working

This guide helps you diagnose and fix issues with the bot's voice features (TTS and STT).

---

## Understanding the Issue

The bot's voice functionality has two parts:

1. **TTS (Text-to-Speech)**: Bot speaking responses in voice channels
   - Requires: `edge-tts` package and internet connection
   - Service: Microsoft Edge TTS

2. **STT (Speech-to-Text)**: Bot hearing and understanding your voice
   - Requires: `py-cord` (not standard discord.py) + `SpeechRecognition`
   - Fallback: Text messages during voice calls

---

## Quick Diagnosis

### Step 1: Check if dependencies are installed

```bash
# Check Python packages
pip list | grep -E "edge-tts|discord|py-cord|SpeechRecognition"

# Expected output for working setup:
# edge-tts           7.2.x
# py-cord            2.x.x    (with voice support)
# SpeechRecognition  3.x.x
#
# Note: You should have EITHER discord.py OR py-cord, not both
# For STT (speech-to-text), you MUST use py-cord
```

### Step 2: Test TTS connectivity

Use the built-in test command:
```
/admin test_tts
```

This command will:
- Check all dependencies
- Test connection to Edge TTS service
- Provide specific troubleshooting steps if it fails

---

## Issue 1: TTS Not Working (NoAudioReceived Errors)

### Symptoms
```
[WARNING] NoAudioReceived error on attempt 1/3 with voice de-DE-KillianNeural
[ERROR] Failed to generate TTS audio after all retries
```

### Possible Causes

1. **edge-tts not installed**
   ```bash
   # Install it
   pip install edge-tts
   ```

2. **Edge TTS service unreachable**
   - The Microsoft Edge TTS service might be temporarily down
   - Your network might block Microsoft services
   - VPN/proxy interference

3. **Firewall blocking access**
   - Check if `speech.platform.bing.com` is accessible
   - Try from a different network

4. **Rate limiting**
   - Too many TTS requests in a short time
   - Wait 5-10 minutes and try again

### Troubleshooting Steps

#### 1. Verify Internet Connectivity
```bash
# Basic connectivity
ping 8.8.8.8

# DNS resolution
ping speech.platform.bing.com
```

If ping works but TTS doesn't, it's likely a firewall or service issue.

#### 2. Test edge-tts directly

```python
# Run this Python script to test edge-tts
import asyncio
import edge_tts
import tempfile
import os

async def test():
    temp = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
    temp_file = temp.name
    temp.close()
    
    communicate = edge_tts.Communicate(
        text='Test auf Deutsch',
        voice='de-DE-KillianNeural'
    )
    
    await asyncio.wait_for(communicate.save(temp_file), timeout=15.0)
    
    if os.path.exists(temp_file):
        size = os.path.getsize(temp_file)
        print(f'✓ TTS works - generated {size} bytes')
        os.remove(temp_file)
        return True
    else:
        print('✗ TTS failed - no audio generated')
        return False

asyncio.run(test())
```

#### 3. Check for VPN/Proxy Issues
```bash
# Temporarily disable VPN
# Try TTS again

# If it works without VPN, your VPN might block Microsoft services
```

#### 4. Try Different Network
```bash
# Switch between WiFi and mobile data
# Some ISPs/organizations block Microsoft TTS services
```

#### 5. Check Service Status
- Edge TTS service might be experiencing an outage
- Check Microsoft service status pages
- Try again after 30 minutes

### Solutions

**Solution A: Install edge-tts**
```bash
cd ~/sulfur
source venv/bin/activate  # Linux/Termux
# OR
.\venv\Scripts\Activate.ps1  # Windows

pip install edge-tts
```

**Solution B: Network Issues**
- Disable VPN/proxy temporarily
- Switch to a different network
- Check firewall settings
- Contact your network admin if on corporate network

**Solution C: Wait for Service**
- Edge TTS service might be temporarily down
- Wait 30-60 minutes and try again
- Check if others report similar issues

---

## Issue 2: STT Not Working (Bot Can't Hear You)

### Symptoms
```
Bot says: "Schreib mir eine Nachricht und ich antworte per Sprache!"
Bot doesn't respond when you speak
```

### Root Cause

**Standard discord.py does NOT support voice receiving!**

The `discord.py` library version 2.x does not include the `discord.sinks` module needed for receiving audio from voice channels.

### Solution: Use py-cord

**Py-cord** is a fork of discord.py that includes voice receiving support.

#### Installation Steps

```bash
cd ~/sulfur
source venv/bin/activate  # Linux/Termux
# OR
.\venv\Scripts\Activate.ps1  # Windows

# Uninstall discord.py first
pip uninstall discord.py

# Install py-cord with voice support
pip install "py-cord[voice]>=2.6.0"

# Install speech recognition
pip install SpeechRecognition

# Restart the bot
```

#### Verify Installation

```python
# Check if py-cord is installed correctly
python3 -c "from discord import sinks; print('✓ Voice receiving supported!')"
```

If this works, the bot will now be able to hear and transcribe your speech!

### Alternative: Use Text Messages

If you don't want to install py-cord, you can still use voice calls:

1. Bot joins voice channel and speaks via TTS
2. You type messages in a text channel
3. Bot responds via voice

The bot will automatically detect that voice receiving is not available and fall back to text mode.

---

## Issue 3: Both TTS and STT Not Working

### Checklist

1. **Install all dependencies**
   ```bash
   pip install edge-tts SpeechRecognition "py-cord[voice]"
   ```

2. **Install FFmpeg** (required for audio playback)
   ```bash
   # Termux
   pkg install ffmpeg
   
   # Linux
   sudo apt install ffmpeg
   
   # Windows
   # Download from https://ffmpeg.org/download.html
   # Add to PATH
   ```

3. **Install PyNaCl** (required for Discord voice)
   ```bash
   # Termux (special steps)
   pkg install libsodium clang
   export SODIUM_INSTALL=system
   pip install PyNaCl
   
   # Linux/Windows
   pip install PyNaCl
   ```

4. **Restart the bot**
   ```bash
   # Kill current bot process
   # Start bot again
   python bot.py
   # Or use maintenance script
   bash maintain_bot.sh
   ```

5. **Check bot startup logs**
   ```bash
   tail -f logs/session_*.log | grep -E "Voice|TTS|STT"
   ```

   Look for:
   ```
   === Voice System Dependency Check ===
     edge-tts (TTS):            ✓ Available
     FFmpeg (Audio playback):   ✓ Available
     PyNaCl (Voice encryption): ✓ Available
     SpeechRecognition (STT):   ✓ Available
   =====================================
     ✓ Voice system is ready!
   
   === Voice Receiving System Check ===
     SpeechRecognition (STT):   ✓ Available
     aiohttp (Whisper API):     ✓ Available
     Discord Voice Receiving:   ✓ Supported
   =====================================
     ✓ Voice receiving (STT) is supported!
   ```

---

## Whisper API (Optional, for Better STT Quality)

For the best speech recognition quality, use OpenAI's Whisper API:

1. Get an OpenAI API key from https://platform.openai.com/
2. Add to `.env`:
   ```
   OPENAI_API_KEY=sk-your-key-here
   ```
3. Restart the bot

The bot will automatically use Whisper for transcription if the key is available.
Falls back to Google Speech Recognition if not.

---

## Platform-Specific Notes

### Termux (Android)

```bash
# Install system packages first
pkg update
pkg install -y ffmpeg libsodium clang python

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install Python packages
export SODIUM_INSTALL=system
pip install edge-tts SpeechRecognition PyNaCl "py-cord[voice]"

# Run bot
python bot.py
```

### Linux/WSL

```bash
# Install FFmpeg
sudo apt update
sudo apt install -y ffmpeg

# Install Python packages
cd ~/sulfur
source venv/bin/activate
pip install edge-tts SpeechRecognition "py-cord[voice]"
```

### Windows

1. Install FFmpeg:
   - Download from https://ffmpeg.org/download.html
   - Extract to `C:\ffmpeg`
   - Add `C:\ffmpeg\bin` to system PATH

2. Install Python packages:
   ```powershell
   cd sulfur
   .\venv\Scripts\Activate.ps1
   pip install edge-tts SpeechRecognition "py-cord[voice]"
   ```

---

## Using the Bot's Diagnostic Commands

### `/admin test_tts`
Tests TTS functionality and connectivity.

**Example output (working):**
```
✅ TTS Test Erfolgreich
✓ TTS-Service ist erreichbar und funktioniert
✓ Audio wurde erfolgreich generiert
✓ Voice-Funktionen sollten funktionieren
```

**Example output (not working):**
```
❌ TTS Test Fehlgeschlagen
Der Edge TTS Service ist nicht erreichbar oder antwortet nicht.

Mögliche Ursachen:
• Edge TTS Service ist down
• Firewall blockiert Zugriff
• VPN/Proxy Probleme
```

### `/admin debug_voice`
Shows active voice calls and statistics.

---

## Summary: What You Need

### For TTS (Bot Speaking)
- ✅ `edge-tts` package
- ✅ Internet connection
- ✅ Access to `speech.platform.bing.com`
- ✅ FFmpeg installed
- ✅ PyNaCl installed

### For STT (Bot Hearing)
- ✅ `py-cord[voice]` (not discord.py)
- ✅ `SpeechRecognition` package
- ✅ FFmpeg installed
- ✅ PyNaCl installed
- ⚠️ Optional: OpenAI API key for Whisper

### For Text Fallback (No STT)
- ✅ Just TTS requirements
- ℹ️ Bot joins voice and speaks
- ℹ️ You type messages
- ℹ️ Bot responds via voice

---

## Still Having Issues?

1. **Collect diagnostic info**:
   ```bash
   python -V
   pip list | grep -E "discord|edge|speech"
   which ffmpeg
   tail -n 100 logs/session_*.log
   ```

2. **Run the test command**:
   ```
   /admin test_tts
   ```

3. **Check bot startup output** for dependency warnings

4. **Try the manual Python test** (see "Test edge-tts directly" above)

5. **Check if you're using py-cord**:
   ```python
   python -c "from discord import sinks; print('Using py-cord')" 2>&1
   ```

6. **Report the issue** with:
   - Bot startup logs
   - Output of diagnostic commands
   - Your platform (Termux/Linux/Windows)
   - Network environment (home/corporate/VPN)

---

## Quick Reference

| Issue | Cause | Solution |
|-------|-------|----------|
| NoAudioReceived | edge-tts not installed | `pip install edge-tts` |
| NoAudioReceived | Service unreachable | Check network/VPN/firewall |
| NoAudioReceived | Rate limiting | Wait 10 minutes |
| Bot can't hear | Using discord.py | Install py-cord instead |
| No audio playback | FFmpeg missing | Install FFmpeg |
| Voice connection fails | PyNaCl missing | Install PyNaCl |
| Poor STT quality | Using Google STT | Add OPENAI_API_KEY for Whisper |

---

## Additional Resources

- **Voice System Guide**: See `VOICE_SYSTEM_GUIDE.md`
- **TTS/STT Implementation**: See `TTS_STT_IMPLEMENTATION_SUMMARY.md`
- **Py-cord Migration**: See `PYCORD_MIGRATION_GUIDE.md`
- **Termux Setup**: See `TERMUX_GUIDE.md`

---

*Last updated: 2025-12-13*
