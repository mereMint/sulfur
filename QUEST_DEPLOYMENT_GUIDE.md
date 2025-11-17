# Quest System - Quick Deployment Guide

## TL;DR - What Was Done

✅ Added 3 slash commands: `/quests`, `/questclaim`, `/monthly`
✅ Integrated automatic quest progress tracking for 4 event types
✅ Complete reward system with daily bonuses and monthly milestones
✅ Production-ready code, tested and validated
✅ Comprehensive documentation created

## Deployment Steps

### 1. Pre-Deployment Checklist

```bash
# Ensure database migration is applied
python apply_migration.py scripts/db_migrations/003_economy_and_shop.sql

# Verify config has quest settings
grep -A 10 "quests" config/config.json

# Check for syntax errors
python -m py_compile bot.py
```

### 2. Deploy Bot

```bash
# Pull latest changes
git pull origin copilot/add-slash-commands-and-tracking

# Restart bot (choose your method)
# Option A: Use maintenance script
./maintain_bot.sh  # Linux/Termux
# OR
.\maintain_bot.ps1  # Windows PowerShell

# Option B: Manual restart
python bot.py
```

### 3. Verify Deployment

In Discord, test these commands:

```
/quests           # Should generate 3 quests
/monthly          # Should show monthly progress
/questclaim       # Should respond (even if no quests to claim)
```

### 4. Quick Test

1. Send 5 messages in chat
2. Run `/quests` - verify message quest progress increased
3. React to a message 3 times
4. Run `/quests` - verify reaction quest progress increased

## Commands for Users

### `/quests`
Shows your daily quests with progress bars.
Example output:
```
📋 Daily Quests - YourName
Complete all 3 quests for a bonus reward!

💬 Quest 1: Send Messages
Progress: 25/50
Status: ██████░░░░ 50%
Reward: 200 🪙

Quest-Fortschritt: 1/3 abgeschlossen
```

### `/questclaim`
Claims rewards for completed quests.
Example output:
```
✅ Quest-Belohnungen eingesammelt!
Du hast 2 Quest(s) abgeschlossen!

Belohnung: +500 🪙

🎉 Tagesbonus!
Alle Quests abgeschlossen! +500 🪙 Bonus!
```

### `/monthly`
Shows monthly quest completion progress.
Example output:
```
📅 Monthly Quest Progress - YourName
Completed 8/30 days this month

Progress: ████████░░░░░░░░░░░░ 27%

Milestones:
✅ 7 Days - Weekly Warrior: 1000 🪙
🔒 14 Days - Fortnight Champion: 2500 🪙
🔒 21 Days - Three-Week Legend: 5000 🪙
🔒 30 Days - Monthly Master: 10000 🪙
```

## Quest Types

1. **💬 Messages** - Send 50 messages (200 coins)
2. **🎤 Voice Chat** - Be in voice chat for 30 minutes (250 coins)
3. **👍 Reactions** - React to 20 messages (150 coins)
4. **🎮 Games** - Play games for 15 minutes (300 coins)

## Rewards

- **Individual quests**: 150-300 coins each
- **Daily completion bonus**: +500 coins (when all 3 done)
- **Monthly milestones**:
  - 7 days: +1000 coins
  - 14 days: +2500 coins
  - 21 days: +5000 coins
  - 30 days: +10000 coins

## Automatic Features

✅ **Daily Reset**: Midnight UTC (configurable)
✅ **Quest Generation**: Automatic on first `/quests` use
✅ **Progress Tracking**: Silent, no DM spam
✅ **Milestone Grants**: Automatic when claiming after reaching threshold

## Troubleshooting

### Quests not showing?
```bash
# Check database tables exist
mysql -u sulfur_bot_user -p sulfur_bot -e "SHOW TABLES LIKE '%quest%';"

# Should show:
# daily_quests
# daily_quest_completions
# monthly_milestones
```

### Progress not updating?
- Check bot logs for errors
- Verify event handlers are running (no errors in console)
- Make sure action counts (e.g., user is unmuted in VC)

### Can't claim rewards?
- Quest must be 100% complete
- Reward can only be claimed once
- Check `/quests` to see if already claimed (shows "✅ Claimed")

## Configuration

Edit `config/config.json` to customize:

```json
"quests": {
  "enabled": true,                    // Enable/disable quest system
  "daily_reset_hour": 0,             // UTC hour for daily reset (0-23)
  "quest_types": {
    "messages": {
      "target": 50,                   // How many messages to complete quest
      "reward": 200                   // Coin reward for completing
    },
    "vc_minutes": {
      "target": 30,                   // Minutes in voice chat
      "reward": 250
    },
    "reactions": {
      "target": 20,                   // Number of reactions
      "reward": 150
    },
    "game_minutes": {
      "target": 15,                   // Minutes playing games
      "reward": 300
    }
  }
}
```

## Testing Checklist

Quick validation after deployment:

- [ ] `/quests` generates 3 quests
- [ ] Sending messages updates message quest
- [ ] Joining VC updates VC quest (after 1 minute)
- [ ] Adding reactions updates reaction quest
- [ ] Playing games updates game quest (after stopping game)
- [ ] `/questclaim` works for completed quests
- [ ] Daily bonus granted when all 3 quests complete
- [ ] `/monthly` shows current month progress
- [ ] Balance increases after claiming rewards

## Monitoring

Watch bot logs for:
- Quest generation logs
- Progress update logs
- Reward claim logs
- Any errors in quest tracking

Common log messages:
```
[INFO] Generated 3 daily quests for user 123456789
[INFO] Quest messages completed for user 123456789
[INFO] Granted daily completion bonus of 500 to user 123456789
[INFO] Granted Weekly Warrior milestone (7 days) reward of 1000 to user 123456789
```

## Documentation Links

- **Full Testing Guide**: `QUEST_TESTING_GUIDE.md`
- **Implementation Details**: `QUEST_IMPLEMENTATION_SUMMARY.md`
- **Config Reference**: `config/config.json`

## Support

If you encounter issues:
1. Check bot logs for errors
2. Verify database migration was applied
3. Review configuration settings
4. Consult troubleshooting section in `QUEST_TESTING_GUIDE.md`

## Summary

✅ **Status**: Production-ready, fully tested code
✅ **Security**: No vulnerabilities found (CodeQL scan)
✅ **Performance**: Optimized, minimal overhead
✅ **Documentation**: Complete guides provided

**Ready to ship!** 🚀
