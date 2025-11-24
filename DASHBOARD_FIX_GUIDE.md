# Web Dashboard Fix - User Guide

## What Was Fixed

This update resolves all the database errors you were seeing in the web dashboard console. The errors included:

### Before (Errors You Were Seeing)
```
[2025-11-24 01:36:58,674] [WebDashboard] [ERROR] Error getting economy stats: 
1054 (42S22): Unknown column 'display_name' in 'SELECT'

[2025-11-24 01:36:58,665] [WebDashboard] [WARNING] Query failed: 
SELECT COUNT(*) as total_games FROM werwolf_user_stats... 
Error: 1146 (42S02): Table 'sulfur_bot.werwolf_user_stats' doesn't exist
```

### After (What You'll See Now)
- ✅ No more SQL errors in the console
- ✅ Economy stats page loads correctly
- ✅ Stock market data displays properly
- ✅ Game statistics show gracefully (even if tables don't exist yet)
- ✅ Dashboard works even with partial database setup

## What Changed

### 1. Database Schema Updates
The `user_stats` table now includes:
- `display_name` column (for showing usernames in leaderboards)
- `username` column (for additional user identification)

**Migration**: When you restart the bot, these columns will be automatically added to existing tables. No manual intervention needed!

### 2. Fixed Table References
- Economy stats now correctly uses `transaction_history` table
- All queries handle missing tables gracefully without crashing

### 3. Improved Query Logic
- JOINs now properly handle the composite primary key in user_stats
- Queries filter by current month to avoid duplicate user entries
- Safe query wrappers prevent crashes when features aren't fully set up

### 4. Better Error Handling
- Missing tables log warnings but don't crash the dashboard
- Missing columns fall back to simpler queries
- Empty results return empty arrays instead of errors

## What to Do Next

### 1. Update Your Installation
```bash
git pull
```

### 2. Restart the Bot
The database migration will run automatically on startup:
```bash
# Stop the bot if running
./maintain_bot.sh stop  # or maintain_bot.ps1 stop on Windows

# Start it again
./maintain_bot.sh  # or maintain_bot.ps1 on Windows
```

### 3. Check the Web Dashboard
Visit http://localhost:5000 (or your configured port) and verify:
- Economy page loads without errors
- Stock market page shows data (if you have stocks)
- Game statistics display (may show 0 if no games played yet)
- Console shows no SQL errors

## Expected Behavior

### Economy Dashboard
- Shows total coins, users with coins, and average balance
- Displays richest users (if any user has coins)
- Shows recent transactions (if transaction_history has data)
- Gracefully handles empty data

### Stock Market
- Lists all stocks (if stocks table exists and has data)
- Shows top stock holders (if anyone owns stocks)
- Returns empty arrays if features not used yet

### Game Statistics
- Shows counts for various games
- Returns 0 for games that haven't been played
- No errors even if game tables don't exist
- Logs warnings (not errors) for missing tables

## Troubleshooting

### If You Still See Errors

1. **Check database connection**
   ```bash
   # Verify database credentials in .env
   DB_HOST=localhost
   DB_USER=sulfur_bot_user
   DB_PASS=your_password
   DB_NAME=sulfur_bot
   ```

2. **Verify database is running**
   ```bash
   # Linux/Mac
   sudo systemctl status mysql
   
   # Termux
   mysqld_safe &
   ```

3. **Check migration ran successfully**
   Look for this in the bot startup logs:
   ```
   [Database] Adding display_name column to user_stats table
   [Database] Adding username column to user_stats table
   ```

### Known Limitations

1. **Streak tracking**: Detective game streaks show as 0 because streak tracking isn't implemented yet (this is expected)

2. **Some game tables don't exist**: If you haven't played certain games, their tables won't exist. This is fine - the dashboard handles it gracefully.

3. **Transaction history**: If you haven't used economy features that create transaction_history records, this section will be empty (expected).

## Questions?

If you encounter any issues:
1. Check the bot's console/log output for specific errors
2. Verify all migrations completed successfully
3. Ensure database credentials are correct in .env
4. Try restarting the bot and web dashboard

The dashboard should now work smoothly without the SQL errors you were experiencing!
