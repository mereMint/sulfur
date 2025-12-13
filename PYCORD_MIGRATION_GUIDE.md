# Py-Cord Migration Guide for Voice Receiving

## What Changed?

To enable **voice receiving** (so the bot can hear you in voice calls), we've switched from `discord.py` to `py-cord`, which is a feature-rich fork that includes built-in voice receiving support.

## Why Py-Cord?

- **Voice Receiving**: Built-in `discord.sinks` module for capturing user audio
- **API Compatible**: Same API as discord.py, minimal code changes needed
- **Active Development**: Well-maintained fork with regular updates
- **Additional Features**: Includes many enhancements over standard discord.py

## Installation

### Automatic Installation (Recommended)

The bot will automatically install py-cord when you run:

```bash
pip install -r requirements.txt
```

### Manual Installation

If you need to manually switch from discord.py to py-cord:

```bash
# Uninstall discord.py first
pip uninstall discord.py

# Install py-cord with voice support
pip install py-cord[voice]
```

### Platform-Specific Instructions

#### **Linux / WSL**

```bash
cd ~/sulfur
source venv/bin/activate
pip uninstall -y discord.py
pip install -r requirements.txt
```

#### **Windows**

```powershell
cd sulfur
.\venv\Scripts\Activate.ps1
pip uninstall -y discord.py
pip install -r requirements.txt
```

#### **Termux (Android)**

```bash
cd ~/sulfur
source venv/bin/activate
pip uninstall -y discord.py
pip install -r requirements.txt
```

**Note**: On Termux, ensure you have `libsodium` and `ffmpeg` installed first:
```bash
pkg install libsodium ffmpeg clang
export SODIUM_INSTALL=system
```

## Verification

After installation, verify py-cord is installed:

```bash
python3 -c "import discord; print(f'discord version: {discord.__version__}')"
```

You should see a version number like `2.x.x` (py-cord uses similar versioning).

Check for voice receiving support:

```bash
python3 -c "from discord import sinks; print('✓ Voice receiving supported!')"
```

If this works without error, voice receiving is ready!

## What's New?

### Voice Receiving Features

Once py-cord is installed, the bot can now:

1. **Hear users in voice calls** - Real-time audio capture
2. **Transcribe speech** - Convert speech to text using:
   - Google Speech Recognition (free)
   - OpenAI Whisper API (best quality, requires API key)
3. **Voice conversations** - Fully voice-based interaction
4. **Speaker detection** - Identify who is speaking

### Updated Greeting

When you join a voice call, the bot will now say:

> "Hey! Ich bin jetzt im Call. Ich kann deine Sprache hören - sprich einfach los!"

Instead of asking you to type messages!

## Backwards Compatibility

### If Py-Cord Installation Fails

The bot will automatically fall back to text-based input during voice calls:

- Bot still joins voice channel
- Bot still speaks via TTS
- You type messages in a text channel
- Bot responds via voice

### Existing Features

All existing features remain unchanged:
- Text commands work exactly the same
- TTS (text-to-speech) works the same
- Database, games, economy - no changes
- Configuration stays the same

## Troubleshooting

### Error: "ModuleNotFoundError: No module named 'discord'"

This means neither discord.py nor py-cord is installed.

**Solution:**
```bash
pip install -r requirements.txt
```

### Error: "ImportError: cannot import name 'sinks' from 'discord'"

This means standard discord.py is installed instead of py-cord.

**Solution:**
```bash
pip uninstall discord.py
pip install py-cord[voice]
```

### Voice Receiving Still Not Working

**Check installation:**
```bash
# Should NOT find discord.py
pip list | grep discord.py

# Should find py-cord
pip list | grep py-cord
```

**Check for discord.sinks:**
```python
python3 -c "from discord import sinks; print('OK')"
```

**Check bot logs:**
```bash
grep "Voice Receiving System Check" logs/session_*.log
```

Look for:
```
Discord Voice Receiving:   ✓ Supported
```

### FFmpeg or PyNaCl Errors

Voice receiving also requires:
- **FFmpeg** - For audio processing
- **PyNaCl** - For voice encryption

See [VOICE_SYSTEM_GUIDE.md](VOICE_SYSTEM_GUIDE.md) for installation instructions.

## Technical Details

### What Changed in Code?

**requirements.txt:**
```diff
- discord.py
+ py-cord[voice]
```

**What Stayed the Same:**
- All `discord.*` imports work identically
- `discord.Client`, `discord.Bot`, `discord.Cog` unchanged
- Slash commands and interactions work the same
- All Discord API methods have the same signatures

**What's New:**
- `discord.sinks` module now available
- `voice_client.start_recording()` method available
- `voice_client.stop_recording()` method available
- Better voice feature support

### Python API

The switch is transparent to most code:

```python
import discord  # Works with both discord.py and py-cord

# All standard discord.py code works
client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix="!")

# Py-cord adds these:
from discord import sinks  # New: Voice receiving
voice_client.start_recording(sink, callback)  # New: Start capturing audio
```

## Migration Checklist

- [ ] Backup your `.env` file
- [ ] Backup your database (optional but recommended)
- [ ] Uninstall discord.py: `pip uninstall discord.py`
- [ ] Install requirements: `pip install -r requirements.txt`
- [ ] Verify py-cord installed: `pip list | grep py-cord`
- [ ] Check for discord.sinks: `python3 -c "from discord import sinks"`
- [ ] Start bot and check logs for "Voice Receiving System Check"
- [ ] Test voice call: `/admin force_voice_call @user`
- [ ] Verify bot can hear you (check logs for "Transcribed from...")

## Support

### Bot Startup Checks

The bot automatically checks voice receiving support on startup:

```
=== Voice Receiving System Check ===
  SpeechRecognition (STT):   ✓ Available
  aiohttp (Whisper API):     ✓ Available
  Discord Voice Receiving:   ✓ Supported
=====================================
```

If you see `✗ NOT SUPPORTED` for "Discord Voice Receiving", py-cord is not properly installed.

### Getting Help

If you're still having issues:

1. **Collect system info:**
   ```bash
   python3 --version
   pip list | grep -E "discord|py-cord"
   which ffmpeg
   ```

2. **Check bot startup logs:**
   ```bash
   tail -n 100 logs/session_*.log | grep -E "Voice|discord"
   ```

3. **Test voice receiving:**
   ```bash
   python3 -c "from modules.voice_audio_sink import check_voice_receiving_support; print(check_voice_receiving_support())"
   ```

Include all output when asking for help!

## References

- **Py-Cord GitHub**: https://github.com/Pycord-Development/pycord
- **Py-Cord Documentation**: https://docs.pycord.dev/
- **Voice Guide**: [VOICE_SYSTEM_GUIDE.md](VOICE_SYSTEM_GUIDE.md)
- **Discord API**: https://discord.com/developers/docs

## FAQ

**Q: Will this break my existing bot?**  
A: No, py-cord is API-compatible with discord.py. Existing commands, events, and features work identically.

**Q: Can I still use discord.py?**  
A: Yes, but voice receiving won't work. The bot will fall back to text-based input during calls.

**Q: Do I need to change my code?**  
A: No code changes needed if you're just using the bot. The switch is transparent.

**Q: What about performance?**  
A: Py-cord has similar performance to discord.py. Voice receiving adds minimal overhead.

**Q: Is py-cord stable?**  
A: Yes, py-cord is widely used and well-maintained. Many bots use it in production.

**Q: Can I switch back to discord.py?**  
A: Yes, but you'll lose voice receiving. Just `pip install discord.py` and remove py-cord.

## Summary

✅ **Recommended**: Use py-cord for full voice receiving support  
✅ **Easy Migration**: Just update requirements.txt and reinstall  
✅ **Backwards Compatible**: All existing features still work  
✅ **New Features**: Bot can now hear you in voice calls!  
✅ **Fallback Support**: Works without py-cord (text-based only)

The migration is simple, safe, and enables powerful new voice features! 🎙️
