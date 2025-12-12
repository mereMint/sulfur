# Quick Start Guide - Autonomous Behavior Fix

## What Was Fixed

1. **Bot Startup Error** - Fixed `IndentationError` in `voice_conversation.py` line 527
2. **Autonomous Actions** - Now trigger based on bot's boredom level
3. **Database Connections** - Verified all connections are properly managed

## Testing the Bot

### 1. Start the Bot

```bash
python3 bot.py
```

The bot should start without the IndentationError.

### 2. Monitor Autonomous Behavior

Watch the logs for autonomous messaging activity:

```bash
tail -f logs/session_*.log | grep -i "autonomous\|boredom"
```

### 3. Check Bot's Boredom Level

In Discord, use the command:
```
/botmind status
```

Look for the "Boredom" meter in the response.

### 4. Expected Behavior

#### When Server is Quiet (< 3 users online):
- Bot's boredom increases by 0.05 every 30 minutes
- When boredom reaches 0.3 or higher, autonomous messaging activates
- Bot will attempt to message online users

#### When Autonomous Message Succeeds:
- Bot sends a DM to a user
- Boredom decreases by 0.2
- Prevents immediate repeated messaging

#### Log Examples:

**Low Boredom (Skipping):**
```
Skipping autonomous messaging - boredom level 0.15 below threshold 0.30
```

**High Boredom (Checking Users):**
```
Bot boredom level 0.45 above threshold 0.30, checking for users to message
Autonomously messaging user: JohnDoe
Successfully sent autonomous message to JohnDoe
Reduced boredom by 0.2 after autonomous message (new level: 0.25)
```

## Configuration

### Adjust Boredom Threshold

Edit `config/config.json`:

```json
{
  "modules": {
    "autonomous_behavior": {
      "boredom_threshold": 0.3
    }
  }
}
```

**Values:**
- `0.0` - Always attempt autonomous messaging (not recommended)
- `0.3` - Default, moderate boredom
- `0.5` - Only when quite bored
- `0.7` - Only when very bored
- `1.0` - Never (bot would need maximum boredom)

### Other Settings

```json
{
  "modules": {
    "autonomous_behavior": {
      "enabled": true,                    // Master switch
      "min_dm_cooldown_hours": 1,        // Minimum time between ANY contact
      "min_cooldown_hours": 24,          // Cooldown per user
      "temp_dm_access_hours": 1,         // How long users can reply
      "boredom_threshold": 0.3           // Boredom trigger level
    }
  }
}
```

## Troubleshooting

### Bot Still Won't Start

1. Check for other syntax errors:
   ```bash
   python3 -m py_compile bot.py
   ```

2. Check module imports:
   ```bash
   python3 -c "import modules.voice_conversation"
   ```

### Autonomous Actions Not Triggering

1. **Check if boredom is high enough:**
   ```
   /botmind status
   ```
   Boredom must be >= 0.3 (or your configured threshold)

2. **Check server activity:**
   - Bot boredom increases when < 3 users online
   - With 3+ users online, boredom actually decreases

3. **Check cooldowns:**
   - Users must not have been contacted in the last 24 hours
   - Minimum 1 hour between ANY autonomous contact

4. **Check user status:**
   - Users must be online (not offline)
   - Users must have autonomous messaging enabled

### Database Connection Issues

All database connections are properly managed. If you see connection errors:

1. Verify MySQL is running
2. Check `.env` file has correct credentials
3. Check connection pool settings in `db_helpers.py`

## Files Modified

- `modules/voice_conversation.py` - Fixed IndentationError
- `bot.py` - Added boredom-based triggering
- `config/config.json` - Added boredom_threshold setting

## Need More Help?

See the full documentation: `FIX_SUMMARY_AUTONOMOUS_BOREDOM.md`
