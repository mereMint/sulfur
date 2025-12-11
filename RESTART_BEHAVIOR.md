# What Happens When Bot Restarts - Detailed Explanation

This document explains exactly what will happen when you restart the Sulfur bot after deploying the autonomous features.

## Prerequisites

Before restarting, ensure:
1. ✅ Database migration applied: `scripts/db_migrations/011_autonomous_features.sql`
2. ✅ Dependencies installed: `pip install edge-tts`
3. ✅ FFmpeg installed (optional, for voice features): `ffmpeg -version`

## Startup Sequence

### 1. Environment & Config Loading (0-2 seconds)

```
[STARTUP] Loading environment variables from .env
[STARTUP] Loading configuration from config/config.json
[STARTUP] Validating API keys (Gemini/OpenAI)
[STARTUP] Checking Discord bot token
```

**What's checked:**
- `DISCORD_BOT_TOKEN` exists and is valid format
- API keys present based on provider setting
- Config JSON is valid and has all required sections

**New config sections loaded:**
- `autonomous_behavior` - Controls autonomous messaging
- `focus_timer` - Focus session settings
- `voice_tts` - Voice TTS configuration

### 2. Module Imports (2-5 seconds)

```
[IMPORT] Importing discord.py and core libraries
[IMPORT] Importing database helpers
[IMPORT] Importing game modules (werwolf, rpg, etc.)
[IMPORT] Importing NEW autonomous_behavior module
[IMPORT] Importing NEW focus_timer module
[IMPORT] Importing NEW voice_tts module
[IMPORT] Importing NEW bot_mind module
```

**What can fail:**
- `ModuleNotFoundError: No module named 'edge_tts'`
  - **Solution:** Run `pip install edge-tts`
- Database connection errors
  - **Solution:** Check MySQL is running and credentials are correct

### 3. Database Initialization (5-10 seconds)

```
[DATABASE] Initializing connection pool (size: 10)
[DATABASE] Creating missing tables if any
[DATABASE] Applying pending migrations
[DATABASE] Migration 011: autonomous_features.sql
```

**New tables created (if migration run):**
- `user_autonomous_settings` - User preferences
- `focus_sessions` - Focus timer sessions
- `focus_distractions` - Distraction logs
- `bot_autonomous_actions` - Autonomous action log
- `voice_conversations` - Voice session tracking
- `voice_messages` - Voice transcripts
- `user_memory_enhanced` - Enhanced user memory
- `temp_dm_access` - Temporary DM access grants
- `bot_mind_state` - Bot consciousness snapshots

**What's inserted:**
- Default autonomous settings for existing users (from user_stats)

### 4. Discord Client Connection (10-15 seconds)

```
[DISCORD] Connecting to Discord gateway
[DISCORD] Bot logged in as: Sulfur#XXXX
[DISCORD] Connected to X guild(s)
```

### 5. Command Registration (15-20 seconds)

```
[COMMANDS] Registering slash commands globally
[COMMANDS] Registered: /settings (NEW)
[COMMANDS] Registered: /focus (NEW)
[COMMANDS] Registered: /focusstats (NEW)
[COMMANDS] Registered: /help, /profile, /shop, etc. (existing)
[COMMANDS] Synced XX global commands
```

**New commands available:**
- `/settings` - Manage autonomous bot preferences
- `/focus` - Start/stop focus timer
- `/focusstats` - View focus statistics

### 6. Background Tasks Start (20-25 seconds)

```
[TASKS] Starting grant_voice_xp task (every 1 minute)
[TASKS] Starting update_presence_task (every 15 minutes)
[TASKS] Starting autonomous_messaging_task (NEW - every 2 hours)
[TASKS] Starting cleanup_temp_dm_access (NEW - every 1 hour)
[TASKS] Starting manage_wrapped_event task
[TASKS] Starting cleanup_empty_channels task
[TASKS] Starting update_stock_market task (every 30 minutes)
[TASKS] Starting generate_news task (every 6 hours)
```

**New background tasks:**

#### autonomous_messaging_task (Every 2 hours)
- Checks 5 random online users
- Evaluates if bot should message them
- Respects user preferences and cooldowns (1 hour minimum)
- Generates AI conversation starters
- Sends DM and grants 1-hour temporary DM access
- Logs all actions to database

#### cleanup_temp_dm_access (Every hour)
- Removes expired temporary DM access entries
- Keeps database clean
- Logs cleanup operations

### 7. Bot Mind Initialization (25-30 seconds)

```
[BOT_MIND] Initializing bot consciousness system
[BOT_MIND] Loading previous mind state from database
[BOT_MIND] Mood: neutral, Activity: idle
[BOT_MIND] Thought: "Just started up... wondering what chaos awaits."
```

**Mind state:**
- Loads last saved state (if exists)
- Or initializes fresh with neutral mood
- Starts with empty observation list
- Personality traits set to defaults

### 8. Ready State (30 seconds)

```
[READY] Bot is online and ready!
[READY] All systems operational
[READY] Waiting for commands and events...
```

## What Happens Next

### Immediate (First Hour)

**1. Bot responds to pings/commands (immediately)**
```
User: /settings feature:view
Bot: [Shows current autonomous settings]
```

**2. Bot monitors activity (continuously)**
- Messages tracked for focus timer distractions
- Games/streaming detected for focus warnings
- User presence updates logged
- Server activity observed by bot mind

**3. First background task runs (within 1 hour)**
```
[TASK] cleanup_temp_dm_access: Cleaned up 0 expired entries
```

### Within 2 Hours

**4. First autonomous messaging check**
```
[AUTONOMOUS] Running autonomous messaging check...
[AUTONOMOUS] Checking 5 random online users
[AUTONOMOUS] User Alice: allow_messages=True, last_contact=None
[AUTONOMOUS] Generating conversation starter for Alice...
[AUTONOMOUS] AI Generated: "Hey Alice, I noticed you were talking about..."
[AUTONOMOUS] Sending DM to Alice
[AUTONOMOUS] Granted 1-hour temporary DM access to Alice
[AUTONOMOUS] Logged action: dm_message, target=Alice, success=True
```

**What user sees:**
- Alice receives DM from bot with natural message
- Alice can reply for 1 hour without needing DM Access premium
- After 1 hour, temp access expires, premium required

### When User Uses Features

**5. User starts focus timer**
```
User: /focus preset:short
Bot: 🎯 Focus-Timer gestartet! (25 minutes)
[FOCUS] Session 123 started for UserID 456
[FOCUS] Monitoring activity: messages, games, streaming
```

**If user gets distracted:**
```
[FOCUS] Distraction detected: UserID 456 sent message
[FOCUS] Logged distraction: type=message
[DM] Sending reminder to user
User receives: "⚠️ Focus-Modus aktiv! Du solltest gerade fokussiert arbeiten. 🎯"
```

**After timer completes:**
```
[FOCUS] Session 123 completed
[FOCUS] Duration: 25 minutes, Distractions: 2
[DM] Sending completion notification
User receives: "✅ Focus-Timer abgeschlossen! Gut gemacht! 📊 Ablenkungen: 2"
```

**6. User checks settings**
```
User: /settings feature:view
Bot: Shows embed with:
  - Autonomous Messages: ✅ Aktiviert
  - Autonomous Calls: ✅ Aktiviert
  - Contact Frequency: 🟢 Normal (täglich)
  - Last Contact: Never / [timestamp]
```

**7. User tries DM without premium**
```
User: [Sends DM to bot]
Bot: [Checks has_feature_unlock('dm_access')] -> False
Bot: [Checks has_temp_dm_access(user_id)] -> False
Bot: "🔒 DM Access erforderlich - Du benötigst DM Access..."
```

**8. After bot autonomously messages user**
```
Bot: [Sends autonomous DM to user]
Bot: [Grants temp_dm_access for 1 hour]
User: [Sends DM reply]
Bot: [Checks has_temp_dm_access(user_id)] -> True
Bot: [Processes message and responds normally]
```

### Continuous Operations

**9. Bot mind updates (periodically)**
```
[BOT_MIND] Observing: high_activity in server
[BOT_MIND] Mood changed: neutral -> excited (Lots happening)
[BOT_MIND] Thought generated: "Everyone's really chatty today..."
[BOT_MIND] Energy: 0.95, Boredom: 0.2
```

**10. Presence updates (every 15 minutes)**
```
[PRESENCE] Updating bot status
[PRESENCE] Random user selected: Bob
[PRESENCE] Activity: Watching "stalkt Bob"
```

## Error Handling

All new features have comprehensive error handling:

### If edge-tts not installed:
```
[WARNING] edge-tts not available. Install with: pip install edge-tts
[INFO] Voice TTS features disabled until edge-tts installed
```
**Bot continues without voice features**

### If ffmpeg not installed:
```
[WARNING] FFmpeg not found for audio playback
[INFO] Voice TTS will not work without ffmpeg
```
**Bot continues, voice features fail gracefully**

### If database connection fails:
```
[ERROR] Database connection failed
[ERROR] Retrying connection...
[ERROR] Using fallback behavior for autonomous features
```
**Bot continues with reduced functionality**

### If AI API fails:
```
[ERROR] AI API timeout or error
[WARNING] Using fallback conversation starters
```
**Bot uses predefined messages instead**

## Feature Flags

If any feature causes issues, disable in config:

```json
{
  "modules": {
    "autonomous_behavior": {
      "enabled": false  // ← Disables autonomous messaging
    },
    "focus_timer": {
      "enabled": false  // ← Disables focus timer
    }
  }
}
```

Then restart bot - features will be skipped.

## Memory & Performance

### Memory Usage
- **Focus Sessions**: In-memory dict, cleaned on completion
- **Bot Mind**: Single instance, ~10KB
- **Temp DM Access**: Database only, cleaned hourly
- **Expected increase**: ~50-100MB total

### Database Growth
- **focus_sessions**: ~1KB per session
- **bot_autonomous_actions**: ~0.5KB per action
- **temp_dm_access**: ~0.2KB per entry (auto-cleaned)
- **Expected growth**: ~10-50MB per month

### CPU Usage
- **Autonomous messaging**: Spike every 2 hours (~2-5 seconds)
- **Focus monitoring**: Negligible (event-driven)
- **Mind updates**: Minimal (low frequency)
- **Expected increase**: <5% average

## Monitoring Commands

Check if everything is working:

```bash
# Check logs for errors
tail -f logs/session_*.log | grep ERROR

# Check if tasks are running
grep "autonomous_messaging_task" logs/session_*.log
grep "cleanup_temp_dm_access" logs/session_*.log

# Check database tables exist
mysql -u sulfur_bot_user -p sulfur_bot -e "SHOW TABLES LIKE '%autonomous%';"

# Check for active focus sessions
mysql -u sulfur_bot_user -p sulfur_bot -e "SELECT * FROM focus_sessions WHERE completed=0;"
```

## What Won't Happen

❌ Bot won't spam users - 1 hour minimum cooldown enforced
❌ Bot won't message users who disabled autonomous messages
❌ Bot won't break existing features - all changes are additive
❌ Bot won't require users to have DM Access if bot messages them first
❌ Bot won't lose data on restart - all state persists in database
❌ Bot won't crash if optional dependencies missing - graceful degradation

## Summary Checklist

When bot restarts, these things happen automatically:

✅ Config loads new sections with defaults
✅ New modules import successfully
✅ Database migration applies (creates 9 tables)
✅ 3 new commands register (/settings, /focus, /focusstats)
✅ 2 new background tasks start (autonomous messaging, cleanup)
✅ Bot mind initializes with personality
✅ All existing features continue working
✅ Error handling prevents crashes
✅ Logging tracks all new operations

**Result: Bot works correctly with zero manual intervention after restart.**

## Getting Help

If something doesn't work:

1. **Check logs**: `logs/session_*.log`
2. **Verify tables**: `SHOW TABLES;` in MySQL
3. **Test commands**: Try `/settings feature:view`
4. **Check config**: Ensure JSON is valid
5. **Review checklist**: `DEPLOYMENT_CHECKLIST.md`
6. **Read docs**: `docs/AUTONOMOUS_FEATURES.md`

## Next Steps After Restart

1. Test `/settings` command
2. Test `/focus` command
3. Wait for first autonomous message (up to 2 hours)
4. Monitor logs for errors
5. Check database for data accumulation
6. Collect user feedback
7. Iterate and improve
