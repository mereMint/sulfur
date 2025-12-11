# Sulfur Bot - Quick Start Guide

## 🚀 Installation (3 Steps)

```bash
# 1. Install voice dependency
pip install edge-tts

# 2. Apply database migration
mysql -u sulfur_bot_user -p sulfur_bot < scripts/db_migrations/011_autonomous_features.sql

# 3. Start bot with auto-maintenance
./maintain_bot.sh
```

**That's it!** Everything else is automatic.

## ⚡ Quick Reference

### User Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/settings` | Manage bot preferences | `/settings feature:view` |
| `/focus` | Start focus timer | `/focus preset:short` |
| `/focusstats` | View focus statistics | `/focusstats days:7` |

### Admin Commands

**Usage:** `/admin action:[choice] channel:[voice] message:[text]`

| Action | What It Does | Required Fields |
|--------|--------------|-----------------|
| 🔊 Join Voice Channel | Bot joins and announces | `channel` |
| 🔇 Leave Voice Channel | Bot leaves voice | - |
| 🗣️ Speak in Voice | Bot speaks message | `message` |
| 🧪 Test Database | Tests DB connection | - |
| 🧠 Show Bot Mind | Shows bot's thoughts | - |
| 📊 System Status | Shows health metrics | - |
| 🔄 Reload Config | Reloads config.json | - |
| 🗑️ Clear Cache | Clears memory caches | - |

**Examples:**
```
/admin action:"Join Voice Channel" channel:General
/admin action:"Speak in Voice" message:"Hello everyone!"
/admin action:"System Status"
/admin action:"Show Bot Mind"
```

## 🤖 Features

### Autonomous Behavior
- **Messaging:** Bot messages users every ~2 hours (respects preferences)
- **DM Access:** Grants 1-hour temp access when bot messages you
- **Memory:** Tracks interests, topics, active times
- **Mind:** Has mood, thoughts, personality (like Neuro-sama)

### Focus Timer
- **Presets:** Short (25m), Long (50m), Ultra (90m), Sprint (15m)
- **Monitoring:** Detects messages, games, streaming
- **Alerts:** Sends reminders when distracted
- **Stats:** Track completion rate, time, distractions

### Voice Integration
- **TTS:** German voice (Killian Neural)
- **Join/Leave:** Admin can control voice presence
- **Speak:** Bot can announce messages
- **No API Key:** Uses free edge-tts

## 🔧 Maintenance Script Features

### Automatic (No Manual Work)
- ✅ Checks for updates every 60 seconds
- ✅ Auto-pulls code changes
- ✅ Auto-installs dependencies
- ✅ Auto-applies migrations
- ✅ Auto-restarts on updates
- ✅ Auto-backups database (every 30 min)
- ✅ Never fails (retry logic everywhere)

### Control Flags
```bash
# Graceful restart
touch restart.flag

# Graceful shutdown
touch stop.flag
```

## 📊 Monitoring

### Check System Health
```bash
# View logs
tail -f logs/maintenance_*.log
tail -f logs/bot_*.log

# Check bot is running
ps aux | grep bot.py

# Check database
mysql -u sulfur_bot_user -p sulfur_bot -e "SHOW TABLES;"
```

### Discord Commands
```
/admin action:"System Status"    # CPU, memory, uptime
/admin action:"Test Database"    # Connection and tables
/admin action:"Show Bot Mind"    # Bot's current state
```

## 🐛 Troubleshooting

### Bot Won't Start
```bash
# Check logs
tail -n 50 logs/bot_*.log

# Check dependencies
pip list | grep discord
pip list | grep edge-tts

# Test manually
python3 bot.py
```

### Voice Not Working
```bash
# Check edge-tts installed
pip show edge-tts

# Check ffmpeg installed
ffmpeg -version

# If missing:
pip install edge-tts
sudo apt-get install ffmpeg  # Linux
brew install ffmpeg          # Mac
```

### Database Errors
```bash
# Check MySQL running
systemctl status mysql

# Test connection
mysql -u sulfur_bot_user -p sulfur_bot -e "SELECT 1;"

# Reapply migration
mysql -u sulfur_bot_user -p sulfur_bot < scripts/db_migrations/011_autonomous_features.sql
```

### Dependencies Out of Date
```bash
# Force reinstall
pip install -r requirements.txt --force-reinstall

# Or delete marker and restart
rm .last_requirements_install
./maintain_bot.sh
```

## 📁 Important Files

| File/Directory | Purpose |
|----------------|---------|
| `.env` | API keys and credentials |
| `config/config.json` | Bot configuration |
| `logs/` | All log files |
| `backups/` | Database backups |
| `scripts/db_migrations/` | Database migrations |

## 🔐 Security

### Admin Access
- Server administrators
- Bot owner (OWNER_ID in .env)
- All admin responses are ephemeral

### User Privacy
- Users control if bot can message them
- Users control if bot can call them
- Temporary DM access expires automatically
- All preferences stored in database

## 🎯 Quick Checks

### Everything Working?
1. `/admin action:"System Status"` - Check health
2. `/admin action:"Test Database"` - Check DB
3. `/admin action:"Show Bot Mind"` - Check AI
4. `/focus preset:sprint` - Test focus timer
5. `/settings feature:view` - Test user prefs

### After Updates
1. Script auto-pulls code ✅
2. Script auto-installs deps ✅
3. Script auto-applies migrations ✅
4. Script auto-restarts bot ✅
5. No manual steps needed ✅

## 📚 Full Documentation

- `DEPLOYMENT_CHECKLIST.md` - Detailed deployment steps
- `RESTART_BEHAVIOR.md` - What happens on restart
- `docs/AUTONOMOUS_FEATURES.md` - Complete feature guide
- `IMPLEMENTATION_COMPLETE.txt` - Implementation summary

## 💡 Tips

1. **Let it run:** The script handles everything automatically
2. **Check logs:** When in doubt, check `logs/` directory
3. **Use admin commands:** They're there to help debug
4. **Trust the process:** Retry logic makes it resilient
5. **Read the logs:** They're verbose for a reason

## 🎉 You're Done!

The bot is now:
- ✅ Fully autonomous
- ✅ Self-maintaining
- ✅ Auto-updating
- ✅ Production-ready

**Enjoy your AI bot with a mind of its own!**

---

**Need Help?**
- Check `docs/AUTONOMOUS_FEATURES.md` for detailed explanations
- Review logs in `logs/` directory
- Use `/admin` commands to inspect system
- Check database with provided SQL queries
