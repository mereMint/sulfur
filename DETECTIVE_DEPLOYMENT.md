# Detective Game Enhancement - Deployment Guide

## Pre-Deployment Checklist

- [ ] Review all changes in this PR
- [ ] Ensure database backup is recent
- [ ] Verify bot is not running during migration
- [ ] Check MySQL/MariaDB is running

## Deployment Steps

### 1. Stop the Bot

```bash
# If using maintain_bot script, create stop flag
touch stop.flag

# Or manually kill the process
pkill -f "python.*bot.py"
```

### 2. Backup Database (Recommended)

```bash
# Create backup
mysqldump -u sulfur_bot_user -p sulfur_bot > backup_before_detective_$(date +%Y%m%d_%H%M%S).sql

# Or use the bot's backup script if available
python -c "from modules.db_helpers import *; backup_database()"
```

### 3. Pull Latest Changes

```bash
git pull origin copilot/fix-case-generation-issue
```

### 4. Apply Database Migration

**Option A: Using Python Script** (Recommended)
```bash
python apply_migration.py scripts/db_migrations/004_detective_game_cases.sql
```

**Option B: Using MySQL Command Line**
```bash
mysql -u sulfur_bot_user -p sulfur_bot < scripts/db_migrations/004_detective_game_cases.sql
```

**Option C: Manual SQL**
```bash
mysql -u sulfur_bot_user -p sulfur_bot

# Then paste the contents of 004_detective_game_cases.sql
```

### 5. Verify Migration

```bash
# Connect to MySQL
mysql -u sulfur_bot_user -p sulfur_bot

# Check tables exist
SHOW TABLES LIKE 'detective%';

# Expected output:
# +--------------------------------+
# | Tables_in_sulfur_bot           |
# +--------------------------------+
# | detective_cases                |
# | detective_user_progress        |
# | detective_user_stats           |
# +--------------------------------+

# Check table structures
DESCRIBE detective_cases;
DESCRIBE detective_user_progress;
DESCRIBE detective_user_stats;

# Exit MySQL
exit;
```

### 6. Start the Bot

```bash
# If using maintain_bot script
./maintain_bot.sh  # Linux/Termux
# or
./maintain_bot.ps1  # Windows PowerShell

# Or manually
python bot.py
```

### 7. Test in Discord

1. Run `/detective` command
2. Verify a case appears with difficulty indicator
3. Investigate suspects
4. Make an accusation
5. Run `/detective` again - should see difficulty or a different case

## Verification Tests

### Basic Functionality
```
✓ /detective command works
✓ Case displays with difficulty level
✓ Suspect investigation buttons work
✓ Accusation system works
✓ Rewards are granted correctly
```

### Database Checks
```bash
# Check if cases are being saved
mysql -u sulfur_bot_user -p sulfur_bot -e "SELECT COUNT(*) FROM detective_cases;"

# Check if user stats are being tracked
mysql -u sulfur_bot_user -p sulfur_bot -e "SELECT * FROM detective_user_stats;"

# Check if progress is being recorded
mysql -u sulfur_bot_user -p sulfur_bot -e "SELECT * FROM detective_user_progress;"
```

### Difficulty Progression Test
1. Solve a case correctly
2. Run `/detective` again
3. Check if difficulty increased:
   ```sql
   SELECT user_id, current_difficulty, cases_solved 
   FROM detective_user_stats 
   WHERE user_id = YOUR_DISCORD_ID;
   ```

## Rollback Plan (If Needed)

### If Issues Occur

1. **Stop the bot**
   ```bash
   touch stop.flag
   # or
   pkill -f "python.*bot.py"
   ```

2. **Restore database backup**
   ```bash
   mysql -u sulfur_bot_user -p sulfur_bot < backup_before_detective_TIMESTAMP.sql
   ```

3. **Revert code changes**
   ```bash
   git checkout main
   # or previous working commit
   git checkout PREVIOUS_COMMIT_HASH
   ```

4. **Restart bot**
   ```bash
   python bot.py
   ```

### Known Issues and Solutions

**Issue: "Table already exists" error**
- **Cause**: Migration already applied
- **Solution**: Safe to ignore, tables use `IF NOT EXISTS`

**Issue: Foreign key constraint fails**
- **Cause**: MySQL version or configuration issue
- **Solution**: Check if InnoDB is enabled:
  ```sql
  SHOW ENGINES;
  ```

**Issue: JSON column not supported**
- **Cause**: Old MySQL version (< 5.7)
- **Solution**: Upgrade MySQL or modify migration to use TEXT columns

**Issue: Bot can't connect to database**
- **Cause**: Migration locked the database
- **Solution**: Restart MySQL service:
  ```bash
  sudo systemctl restart mysql  # Linux
  # or
  net stop mysql && net start mysql  # Windows
  ```

## Post-Deployment Monitoring

### First 24 Hours
- Monitor bot logs for errors
- Check database table sizes:
  ```sql
  SELECT 
    table_name,
    table_rows,
    ROUND(((data_length + index_length) / 1024 / 1024), 2) AS "Size (MB)"
  FROM information_schema.TABLES 
  WHERE table_schema = 'sulfur_bot' 
  AND table_name LIKE 'detective%';
  ```

### First Week
- Monitor case generation rate
- Check difficulty progression statistics:
  ```sql
  SELECT 
    current_difficulty,
    COUNT(*) as user_count,
    AVG(cases_solved) as avg_solved
  FROM detective_user_stats 
  GROUP BY current_difficulty;
  ```

- Review case reuse rate:
  ```sql
  SELECT 
    c.difficulty,
    COUNT(DISTINCT c.case_id) as total_cases,
    COUNT(p.case_id) as times_played
  FROM detective_cases c
  LEFT JOIN detective_user_progress p ON c.case_id = p.case_id
  GROUP BY c.difficulty;
  ```

## Success Metrics

After 1 week, check:
- [ ] No database errors in logs
- [ ] Cases are being saved and reused
- [ ] Users are progressing in difficulty
- [ ] No performance degradation
- [ ] Positive user feedback

## Support

If you encounter issues:
1. Check bot logs: `logs/session_*.log`
2. Check this issue/PR for updates
3. Review DETECTIVE_SECURITY_REVIEW.md for known issues
4. Contact bot maintainer with:
   - Error messages from logs
   - Database state (query results)
   - Steps to reproduce issue

## Cleanup (Optional)

After successful deployment for 1+ week:

### Remove old test files (if desired)
```bash
# Keep these for documentation:
# - test_detective_game.py
# - test_detective_enhancements.py
# - DETECTIVE_ENHANCEMENTS.md
# - DETECTIVE_SECURITY_REVIEW.md
```

### Archive old backups
```bash
# Move old backups to archive folder
mkdir -p backups/archive
mv backups/backup_before_detective_*.sql backups/archive/
```

## Next Steps

After successful deployment:
1. Monitor user engagement with detective feature
2. Collect feedback on difficulty levels
3. Consider implementing suggested future enhancements:
   - Difficulty-based rewards
   - Case categories
   - Leaderboards
   - Custom cases

---

**Last Updated**: 2025-11-18
**Migration Version**: 004
**Estimated Downtime**: < 2 minutes
**Risk Level**: Low (idempotent migration, backwards compatible)
