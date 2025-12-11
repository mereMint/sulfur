# Deployment Checklist for Autonomous Features

## Pre-Deployment Verification

### ✅ Code Compilation
- [x] `modules/autonomous_behavior.py` compiles without errors
- [x] `modules/focus_timer.py` compiles without errors  
- [x] `modules/voice_tts.py` compiles without errors
- [x] `modules/bot_mind.py` compiles without errors
- [x] `bot.py` compiles without errors
- [x] `config/config.json` is valid JSON

### ✅ Dependencies
- [x] `edge-tts` added to requirements.txt
- [ ] `edge-tts` installed on production: `pip install edge-tts`
- [ ] `ffmpeg` installed on system (for voice TTS)

### ✅ Database Migration
- [x] Migration file created: `scripts/db_migrations/011_autonomous_features.sql`
- [ ] Migration applied on production database
- [ ] Tables verified:
  - [ ] `user_autonomous_settings`
  - [ ] `focus_sessions`
  - [ ] `focus_distractions`
  - [ ] `bot_autonomous_actions`
  - [ ] `voice_conversations`
  - [ ] `voice_messages`
  - [ ] `user_memory_enhanced`
  - [ ] `temp_dm_access`
  - [ ] `bot_mind_state`

### ✅ Configuration
- [x] `autonomous_behavior` section added to config.json
- [x] `focus_timer` section added to config.json
- [x] `voice_tts` section added to config.json
- [x] All config values have sensible defaults

### ✅ Module Imports
- [x] `bot_mind` imported in bot.py
- [x] `autonomous_behavior` imported in bot.py
- [x] `focus_timer` imported in bot.py
- [x] `voice_tts` imported in bot.py
- [x] `json` imported in autonomous_behavior.py
- [x] `discord` imported in bot_mind.py

### ✅ Background Tasks
- [x] `autonomous_messaging_task` defined
- [x] `autonomous_messaging_task` started in on_ready
- [x] `cleanup_temp_dm_access` defined
- [x] `cleanup_temp_dm_access` started in on_ready
- [x] All tasks have `before_loop` decorators

### ✅ Code Quality
- [x] No syntax errors in any Python files
- [x] All imports are at top of files
- [x] Proper error handling throughout
- [x] Task references stored to prevent GC
- [x] Temporary file cleanup implemented

## Deployment Steps

### 1. Backup Current State
```bash
# Backup database
mysqldump -u sulfur_bot_user -p sulfur_bot > backup_before_autonomous_features.sql

# Backup config
cp config/config.json config/config.json.backup
```

### 2. Update Code
```bash
# Pull latest changes
git pull origin copilot/enhance-bot-autonomy-features

# Or merge if on main branch
git merge copilot/enhance-bot-autonomy-features
```

### 3. Install Dependencies
```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# OR
.\venv\Scripts\Activate.ps1  # Windows

# Install new dependencies
pip install edge-tts

# Verify ffmpeg is installed
ffmpeg -version
# If not installed:
# Linux: sudo apt-get install ffmpeg
# Mac: brew install ffmpeg
# Windows: Download from https://ffmpeg.org/
```

### 4. Apply Database Migration
```bash
# Apply migration
mysql -u sulfur_bot_user -p sulfur_bot < scripts/db_migrations/011_autonomous_features.sql

# Verify tables created
mysql -u sulfur_bot_user -p sulfur_bot -e "SHOW TABLES LIKE '%autonomous%'; SHOW TABLES LIKE 'focus_%'; SHOW TABLES LIKE 'temp_dm_access'; SHOW TABLES LIKE 'bot_mind_state';"
```

### 5. Restart Bot
```bash
# Stop bot (if running)
# Use the stop flag if using maintain_bot script
touch stop.flag

# Or kill process
# ps aux | grep bot.py
# kill <PID>

# Start bot
python3 bot.py
# OR use the maintenance script
./maintain_bot.sh
```

## Post-Deployment Verification

### Test Commands
1. **Settings Command**
   ```
   /settings feature:view
   ```
   Expected: Shows current autonomous settings

2. **Focus Timer**
   ```
   /focus preset:sprint
   ```
   Expected: Starts 15-minute timer

3. **Focus Stats**
   ```
   /focusstats
   ```
   Expected: Shows "No sessions" if first time

4. **DM Access Test**
   - Try DMing bot without DM Access feature
   - Expected: See message about needing DM Access
   - Wait for autonomous message (may take up to 2 hours)
   - Expected: Can reply for 1 hour

### Check Logs
```bash
# Check for errors in latest log
tail -f logs/session_*.log | grep -E "ERROR|WARNING"

# Check if background tasks started
grep "autonomous_messaging_task" logs/session_*.log
grep "cleanup_temp_dm_access" logs/session_*.log
```

### Verify Database
```sql
-- Check if settings table has data
SELECT COUNT(*) FROM user_autonomous_settings;

-- Check if temp_dm_access table exists
DESCRIBE temp_dm_access;

-- Check if bot_mind_state table exists
DESCRIBE bot_mind_state;

-- Check focus sessions (should be empty initially)
SELECT COUNT(*) FROM focus_sessions;
```

### Monitor First Hour
- [ ] No error messages in logs
- [ ] Bot responds to commands
- [ ] Background tasks run without errors
- [ ] Database connections stable
- [ ] Memory usage normal

## Rollback Plan

If issues occur:

### 1. Quick Rollback (Code Only)
```bash
# Stop bot
touch stop.flag

# Revert to previous version
git checkout main  # or previous stable branch

# Restart bot
./maintain_bot.sh
```

### 2. Full Rollback (Database + Code)
```bash
# Stop bot
touch stop.flag

# Restore database
mysql -u sulfur_bot_user -p sulfur_bot < backup_before_autonomous_features.sql

# Revert config
cp config/config.json.backup config/config.json

# Revert code
git checkout main

# Restart bot
./maintain_bot.sh
```

## Known Issues & Resolutions

### Issue: "edge-tts not available"
**Resolution:** Install edge-tts: `pip install edge-tts`

### Issue: "FFmpeg not found"
**Resolution:** 
- Linux: `sudo apt-get install ffmpeg`
- Windows: Download from https://ffmpeg.org/
- Mac: `brew install ffmpeg`

### Issue: "Table doesn't exist"
**Resolution:** Reapply migration: `mysql -u sulfur_bot_user -p sulfur_bot < scripts/db_migrations/011_autonomous_features.sql`

### Issue: Background tasks not starting
**Resolution:** Check logs for `before_loop` errors. Ensure `client.wait_until_ready()` completes.

### Issue: DM Access check fails
**Resolution:** Verify `has_feature_unlock` function exists in db_helpers.py

### Issue: "Cannot import bot_mind"
**Resolution:** Verify bot_mind.py is in modules/ directory and has correct syntax

## Performance Monitoring

### Metrics to Watch
- Database query time (should be < 100ms for most queries)
- Memory usage (watch for leaks in focus_timer active_sessions)
- CPU usage during AI thought generation
- Autonomous message success rate
- Focus timer completion rate

### Logging
All new features log to standard bot logger:
- `INFO` for normal operations
- `WARNING` for non-critical issues  
- `ERROR` for failures
- `DEBUG` for detailed tracing

## Feature Flags (Emergency Disable)

If a feature causes issues, disable in config.json:

```json
{
  "modules": {
    "autonomous_behavior": {
      "enabled": false  // Disable autonomous messaging
    },
    "focus_timer": {
      "enabled": false  // Disable focus timer
    },
    "voice_tts": {
      "enabled": false  // Disable voice TTS
    }
  }
}
```

Restart bot after config changes.

## Success Criteria

✅ Bot starts without errors
✅ All slash commands register successfully
✅ Database migrations applied
✅ Background tasks running
✅ No memory leaks after 24 hours
✅ Users can use /settings command
✅ Users can use /focus command
✅ Autonomous messaging works (within 2-4 hours)
✅ Temporary DM access grants on autonomous message
✅ Focus timer detects distractions
✅ All features respect user privacy settings

## Timeline

- **T+0**: Deploy code and apply migrations
- **T+5min**: Verify bot starts and commands work
- **T+1hour**: Check background tasks ran
- **T+2hours**: Verify first autonomous message sent
- **T+24hours**: Monitor stability and performance
- **T+7days**: Collect user feedback and iterate

## Support Contacts

- Bot logs: `logs/session_*.log`
- Database: MySQL on `DB_HOST` from .env
- Documentation: `docs/AUTONOMOUS_FEATURES.md`
- Issue tracking: GitHub repository

## Final Checks Before Go-Live

- [ ] All code reviewed and approved
- [ ] Database backup completed
- [ ] Dependencies installed
- [ ] Migration tested on staging (if available)
- [ ] Rollback plan documented and understood
- [ ] Team notified of deployment
- [ ] Monitoring systems ready
- [ ] Documentation updated
- [ ] User announcement prepared (optional)

---

**Date**: _____________
**Deployed by**: _____________
**Version**: copilot/enhance-bot-autonomy-features
**Status**: ⬜ PENDING / ⬜ IN PROGRESS / ⬜ COMPLETE / ⬜ ROLLED BACK
