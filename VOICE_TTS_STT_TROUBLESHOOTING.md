# Voice TTS/STT Troubleshooting Guide

## Problem: "NoAudioReceived" errors and voice features not working

This guide helps you diagnose and fix issues with the bot's voice features.

---

## Understanding Voice Capabilities

### What Works with discord.py (Current Setup)

The bot uses **discord.py 2.4+** which supports:

✅ **TTS (Text-to-Speech)**: Bot can speak in voice channels
- Uses Microsoft Edge TTS service (free)
- Works perfectly with discord.py

❌ **STT (Speech-to-Text)**: Bot CANNOT hear you speak
- discord.py does NOT include voice receiving (`discord.sinks`)
- Only available in py-cord, which breaks the bot
- **Solution**: Use text messages during voice calls

### Why Not Use Py-Cord?

**Py-cord is incompatible with this bot.**

- This bot uses `discord.app_commands` for slash commands
- Py-cord uses `discord.commands` instead (different API)
- Installing py-cord will break all slash commands
- The bot explicitly checks for and rejects py-cord

### How Voice Calls Work

**With discord.py (Current Setup):**
1. Bot joins voice channel ✅
2. Bot speaks via TTS ✅
3. You type messages in text channel 💬
4. Bot responds via voice TTS ✅

This is the **intended workflow** and is fully supported.

---

## Quick Diagnosis

### Step 1: Check if dependencies are installed

```bash
# Check Python packages
pip list | grep -E "edge-tts|discord|SpeechRecognition"

# Expected output for working TTS:
# discord.py         2.6.x
# edge-tts           7.2.x
# PyNaCl             1.5.x
#
# Note: You should have discord.py, NOT py-cord
# SpeechRecognition is not used with discord.py
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

## Issue 1: TTS Not Working (NoAudioReceived Errors)

### Checklist

1. **Install all dependencies**
   ```bash
   pip install edge-tts PyNaCl
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

3. **Ensure discord.py is installed (NOT py-cord)**
   ```bash
   # Check current installation
   pip show discord.py
   
   # If py-cord is installed, uninstall and reinstall
   pip uninstall -y py-cord discord.py
   pip install -r requirements.txt
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
   tail -f logs/session_*.log | grep -E "Voice|TTS"
   ```

   Look for:
   ```
   === Voice System Dependency Check ===
     edge-tts (TTS):            ✓ Available
     FFmpeg (Audio playback):   ✓ Available
     PyNaCl (Voice encryption): ✓ Available
   =====================================
     ✓ Voice system is ready!
   ```

---

## Important: Bot Cannot Hear You Speak

**This is expected behavior with discord.py!**

The bot uses discord.py which does NOT support voice receiving. When you're in a voice call:

1. ✅ Bot can **speak** (TTS works)
2. ❌ Bot **cannot hear** you (STT not available)
3. 💬 **Solution**: Type messages in any text channel

### Why Can't the Bot Use STT?

- Voice receiving requires `discord.sinks` module
- This is only available in **py-cord**, not discord.py
- But py-cord is **incompatible** with this bot's slash command system
- Installing py-cord will break the entire bot

### How to Interact During Voice Calls

**Correct Way:**
1. Start voice call: `/admin force_voice_call @user`
2. Bot joins and speaks: "Schreib mir eine Nachricht..."
3. Type your message in **any text channel**
4. Bot responds via voice TTS

**Not Possible:**
- Speaking into your microphone
- Bot transcribing your voice
- Real-time voice conversation

This limitation is by design because the bot prioritizes compatibility with discord.py's slash command system over voice receiving features.

---

## FAQ: Why These Limitations?

**Q: Can't you just add py-cord support?**  
A: No. The bot uses `discord.app_commands` for all slash commands. Py-cord uses a different system (`discord.commands`). Converting the entire bot would require rewriting thousands of lines of code.

**Q: Why not support both discord.py and py-cord?**  
A: They use incompatible APIs for commands. You can only use one at a time. This bot chose discord.py for stability and broader compatibility.

**Q: Will STT ever be added?**  
A: Only if discord.py adds voice receiving support, or if the bot is completely rewritten for py-cord (unlikely).

**Q: Is the text fallback solution good enough?**  
A: Yes! Many users successfully use voice calls with text input. The bot still speaks naturally via TTS.

---

## Whisper API (Not Applicable with discord.py)

~~For the best speech recognition quality, use OpenAI's Whisper API~~

**Note**: Whisper API is only useful if the bot can receive audio, which requires py-cord. Since this bot uses discord.py, Whisper API cannot be used for voice calls.

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

# Install Python packages (discord.py, NOT py-cord)
export SODIUM_INSTALL=system
pip install -r requirements.txt

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
pip install -r requirements.txt
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
   pip install -r requirements.txt
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

### For TTS (Bot Speaking) - ✅ Fully Supported
- ✅ `edge-tts` package
- ✅ `discord.py[voice]` (from requirements.txt)
- ✅ Internet connection
- ✅ Access to `speech.platform.bing.com`
- ✅ FFmpeg installed
- ✅ PyNaCl installed

### For STT (Bot Hearing) - ❌ Not Available
- ❌ Not possible with discord.py
- ❌ Would require py-cord (which breaks the bot)
- ✅ **Text message fallback works perfectly**

### For Voice Calls (Current Setup)
- ✅ Bot joins voice channel
- ✅ Bot speaks via TTS
- ✅ You type messages in text channels
- ✅ Bot responds via voice TTS
- ❌ Bot cannot hear you speak (use text instead)

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

5. **Check if you're using discord.py (not py-cord)**:
   ```bash
   pip show discord.py
   # Should show discord.py, NOT py-cord
   
   # If py-cord is installed:
   pip uninstall -y py-cord discord.py
   pip install -r requirements.txt
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
| Bot can't hear | Using discord.py | **Expected behavior** - use text messages |
| Bot crashes on startup | py-cord installed | Uninstall py-cord, install discord.py |
| No audio playback | FFmpeg missing | Install FFmpeg |
| Voice connection fails | PyNaCl missing | Install PyNaCl |
| Import error | Mixed discord.py/py-cord | `pip uninstall -y discord.py py-cord && pip install -r requirements.txt` |

---

## Additional Resources

- **Voice System Guide**: See `VOICE_SYSTEM_GUIDE.md`
- **TTS/STT Implementation**: See `TTS_STT_IMPLEMENTATION_SUMMARY.md`
- **Py-cord Migration**: See `PYCORD_MIGRATION_GUIDE.md`
- **Termux Setup**: See `TERMUX_GUIDE.md`

---

*Last updated: 2025-12-13*
