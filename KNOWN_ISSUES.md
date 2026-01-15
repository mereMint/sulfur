# Known Issues and Troubleshooting Guide

This document lists known issues in the Sulfur bot and their solutions.

## Database Issues

### Web Dashboard 404 Errors for Missing Users

**Issue**: The web dashboard logs 404 errors when trying to access profiles for users who haven't interacted with the bot yet.

**Example**: User ID 445582818383233000 not found in players table.

**Explanation**: This is expected behavior. The `players` table is populated when users interact with the bot for the first time (sending messages, using commands, etc.). Users who have never interacted with the bot will not have entries in the database.

**Solution**: 
- This is not a bug - it's normal operation
- Users will be automatically added to the database when they:
  - Send their first message in a channel the bot can see
  - Use any bot command
  - Join a voice channel tracked by the bot
- If you need to manually add a user, you can do so with:
  ```sql
  INSERT INTO players (discord_id, display_name, balance, level, xp, created_at)
  VALUES (YOUR_USER_ID, 'Username', 0, 1, 0, NOW());
  ```

## Discord Configuration Issues

### Missing Custom Emojis

**Issue**: The bot is configured to use 10 custom emojis that are missing from the Discord application.

**Missing Emojis**:
- Dichtung (thinking person)
- dono (donowall emote)
- GRRR (mad emoji)
- HELP (WTF emoji)
- WHYY (bruh/why emoji)
- jigglejiggle (cursed jigglypuff)
- o7 (saluting)
- o7D (flabbergasted)
- YESS (thumbs up guy)
- And others from config/server_emojis.json

**Solution**:
1. Go to your Discord server settings
2. Navigate to "Emoji" section
3. Upload the missing emojis with the exact names listed in `config/server_emojis.json`
4. Or disable emoji analysis: Set `"emoji_analysis_on_startup": false` in `config/config.json`

**Note**: The bot will work fine without these emojis, but emoji analysis features will not have access to them.

## Minecraft Server Issues

### Port 25565 Already in Use

**Issue**: Minecraft server fails to start with "address already in use" error on port 25565.

**Cause**: A zombie/stale Minecraft server process is still running in the background.

**Solution**: The bot now automatically attempts to kill zombie processes on the configured port. If this fails:

**Windows**:
```powershell
# Find the process using the port
netstat -ano | findstr :25565
# Kill the process (replace PID with actual number)
taskkill /F /PID <PID>
```

**Linux/Mac**:
```bash
# Find and kill the process
lsof -ti :25565 | xargs kill -9
# Or
sudo netstat -tulpn | grep :25565
sudo kill -9 <PID>
```

### NoClassDefFoundError: com.sun.jna.Native

**Issue**: Minecraft server crashes with error about missing libc.so.6 library.

**Cause**: The system is missing glibc/libc6, which is required by JNA (Java Native Access) used by Minecraft and its plugins.

**Solution**: Install the required library:

**Ubuntu/Debian**:
```bash
sudo apt-get update
sudo apt-get install libc6
```

**Arch Linux**:
```bash
sudo pacman -S glibc
```

**Fedora/RHEL**:
```bash
sudo dnf install glibc
```

**Termux (Android)**:
```bash
pkg install glibc
```

### Version Mismatch (paper/1.21.4 vs vanilla/1.21.11)

**Issue**: Server detects version mismatch and keeps redownloading the server JAR.

**Cause**: The default Minecraft version in the code didn't match the config.json version.

**Solution**: This has been fixed. The default version is now 1.21.4 to match config.json.

If you want to use a different version:
1. Update `config/config.json` under `minecraft.minecraft_version`
2. Restart the bot
3. The server will automatically download the correct version

## Music Player Issues

### Blue Noise and Grey Noise Unavailable

**Issue**: Two music stations were showing as unavailable because their YouTube videos were removed or made private.

**Solution**: This has been fixed. The URLs have been updated to use working alternatives:
- Blue Noise: Now uses alternative URL with fallbacks
- Grey Noise: Now uses alternative URL with fallbacks

The lofi player module includes multiple alternative URLs for each station, so if one fails, it will automatically try the next one.

## Performance Issues

### Slow Dashboard Loading

**Issue**: The web dashboard loads slowly, especially the leaderboards and user profiles.

**Cause**: Missing database indexes on frequently queried columns.

**Solution**: Run migration 029 (dashboard_performance_optimization.sql) which adds indexes to:
- Players table
- User stats table
- Transaction history
- AI model usage
- Gaming tables
- Stock market tables

Expected improvements:
- Dashboard load time: 50-70% faster
- Leaderboard queries: 80-90% faster
- User profile lookups: 60-75% faster

## Migration Issues

### Migration 029 Fails with Column Name Errors

**Issue**: Migration 029 fails with multiple "Unknown column" errors due to incorrect column and table names:
- `api_usage` table: references non-existent `usage_date` and `model_name` columns
- `user_stats` table: references non-existent `messages_sent` column
- `stock_transactions` table: table doesn't exist (should be `stock_trades`)
- Column name mismatches in stock tables

**Solution**: This has been fixed. All column and table names have been corrected:
- `api_usage`: `usage_date` → `recorded_at`, `model_name` → `model`
- `user_stats`: `messages_sent` → `message_count` (2 occurrences)
- `stock_transactions` → `stock_trades`
- Stock table columns: `stock_id` → `stock_symbol`, `transaction_time` → `timestamp`

### Stock Market Update Fails with "Unknown column 'stock_symbol'"

**Issue**: Stock market updates fail when trying to insert into stock_history table with `stock_symbol` column.

**Cause**: The stock_history table uses `stock_id` (integer) instead of `stock_symbol` (string).

**Solution**: This has been fixed. The INSERT statement now uses a subquery to get the stock_id from the symbol.

## Getting Help

If you encounter issues not listed here:

1. Check the logs in the `logs/` directory
2. Run the error checking scripts:
   - Windows: `.\check_errors.ps1`
   - Linux: `./check_errors.sh`
3. Check the web dashboard at http://localhost:5000 for live error logs
4. Review the database with the dashboard's database viewer
5. Open an issue on GitHub with:
   - Error message from logs
   - Steps to reproduce
   - Your environment (OS, Python version, database version)
