# Sulfur Bot Startup and Maintenance Guide

## Overview

The Sulfur Bot system consists of three main components that work together:
1. **Bot** (`bot.py`) - The Discord bot
2. **Web Dashboard** (`web_dashboard.py`) - Flask web interface for monitoring and control
3. **Maintenance Watcher** (`maintain_bot.ps1` or `maintain_bot.sh`) - Supervises the bot and handles updates

## Prerequisites

### Windows (PowerShell)
- PowerShell 5.1 or higher
- Python 3.10+
- MySQL/MariaDB server running on localhost
- `.env` file with required environment variables:
  - `DISCORD_BOT_TOKEN`
  - `GEMINI_API_KEY` (or `OPENAI_API_KEY`)
  - `DB_HOST` (default: localhost)
  - `DB_USER` (default: sulfur_bot_user)
  - `DB_PASS` (default: empty)
  - `DB_NAME` (default: sulfur_bot)

### Linux/Termux
- Bash shell
- Python 3.10+
- MySQL/MariaDB server
- Same `.env` file as above

## Startup Procedures

### Windows (Recommended Method)

1. **Open PowerShell as Administrator**
   ```powershell
   cd c:\sulfur
   .\maintain_bot.ps1
   ```

2. **Expected Output:**
   - "--- Sulfur Bot Maintenance Watcher ---"
   - "Checking Python virtual environment..."
   - "Starting the Web Dashboard..."
   - "Web Dashboard is online and ready."
   - "Starting the bot process..."
   - "Bot is running..."

3. **Web Dashboard Access:**
   - Open `http://localhost:5000` in your browser
   - Monitor logs in real-time
   - Control the bot through the interface

4. **Graceful Shutdown:**
   - Press 'Q' in the maintenance watcher window
   - Or click "Stop Bot" in the web dashboard
   - The system will clean up and save the database

### Linux/Termux

1. **Make the script executable:**
   ```bash
   chmod +x maintain_bot.sh
   ```

2. **Run the watcher:**
   ```bash
   ./maintain_bot.sh
   ```

3. **Expected Output:**
   - Same as Windows version
   - Logs saved to `logs/session_YYYY-MM-DD_HH-MM-SS.log`

## Startup Sequence Details

### Phase 1: Environment Setup
- Python virtual environment validation
- Dependency installation from `requirements.txt`
- Database connection pool initialization
- Configuration file loading

### Phase 2: Database Initialization
- Database connection testing
- Required tables creation (if not exists)
- Schema validation
- Connection pool ready for use

### Phase 3: Web Dashboard Startup
- Flask app initialization
- Database pool connection for web dashboard
- Port 5000 binding
- Log streaming thread startup
- Validation: Checking for HTTP 200 response on http://localhost:5000

### Phase 4: Bot Startup
- Discord token validation
- API provider (Gemini/OpenAI) validation
- Config loading from `config.json`
- Bot event listeners registration
- Discord connection establishment
- Background tasks initialization

### Phase 5: Monitoring Loop
- Checking for git repository updates every 60 seconds
- Web dashboard health checks
- Database synchronization
- Log streaming to dashboard

## Common Issues and Fixes

### Issue: "Python virtual environment not found"
**Solution:**
- Ensure Python is installed and in PATH
- Run from the sulfur directory
- Delete `venv/` folder and let the script recreate it

### Issue: "Database pool failed to initialize"
**Solution:**
- Verify MySQL/MariaDB is running
- Check `.env` file credentials
- Ensure database `sulfur_bot` exists
- Verify user `sulfur_bot_user` has proper permissions

### Issue: "Web Dashboard did not become available"
**Solution:**
- Check if port 5000 is in use: `netstat -ano | findstr :5000`
- Kill process using port 5000 or change configuration
- Verify Flask and related packages installed: `pip install -r requirements.txt`

### Issue: "DISCORD_BOT_TOKEN is not set"
**Solution:**
- Verify `.env` file exists in the sulfur directory
- Format must be: `DISCORD_BOT_TOKEN="YOUR_TOKEN_HERE"`
- No equals sign in the token itself
- Token should have three parts separated by dots

### Issue: Bot crashes during startup
**Solution:**
- Check the bot window log output
- Review `logs/session_*.log` for error details
- Verify all required Discord permissions on the bot token
- Ensure `config.json` has valid JSON syntax

## Monitoring

### Web Dashboard Features
1. **Log Viewer** - Real-time log streaming
2. **Bot Status** - Current process status and PID
3. **Database Viewer** - View recent database entries
4. **AI Usage** - Monitor API usage and token counts
5. **Config Editor** - Edit `config.json` in real-time
6. **Control Buttons**:
   - **Restart Bot** - Restart the bot process
   - **Sync Database** - Commit and push database changes
   - **Update Bot** - Pull latest changes from git
   - **Stop Bot** - Gracefully shut down everything

### Log Files
- Location: `logs/session_YYYY-MM-DD_HH-MM-SS.log`
- Combined output from maintenance watcher, web dashboard, and bot
- Accessible in real-time from web dashboard

### Status File
- Location: `bot_status.json`
- Current status: "Running", "Starting", "Updating", "Stopped", "Shutdown"
- Contains bot process ID when running

## Database Backups

### Automatic Backups
- Created before bot startup
- Located in `backups/` folder
- Format: `sulfur_bot_backup_YYYY-MM-DD_HH-MM-SS.sql`
- Retention: 7 days (automatic cleanup)

### Manual Database Export
- Stop the maintenance watcher (press 'Q')
- Manually run: `mysqldump --user=sulfur_bot_user --host=localhost sulfur_bot > backup.sql`

## Environment Variables (.env)

Required variables:

```
DISCORD_BOT_TOKEN="your_bot_token_here"
GEMINI_API_KEY="your_gemini_key_here"
OPENAI_API_KEY="your_openai_key_here"
DB_HOST="localhost"
DB_USER="sulfur_bot_user"
DB_PASS=""
DB_NAME="sulfur_bot"
```

## Configuration (config.json)

Key sections:
- **bot** - Bot name, prefix, colors, system prompt file
- **api** - Current provider (gemini/openai), model settings, timeouts
- **modules** - Feature configurations:
  - **leveling** - XP rates and cooldowns
  - **economy** - Starting balance, bonuses
  - **voice_manager** - Join-to-create settings
  - **werwolf** - Game configuration
  - **wrapped** - Annual statistics feature

## Troubleshooting Commands

### Check Python Environment
```powershell
# Windows
python --version
pip list
```

```bash
# Linux/Termux
python3 --version
pip3 list
```

### Check MySQL Status
```powershell
# Windows
Get-Process mysqld
```

```bash
# Linux
pgrep mysqld
```

### Check Port Usage
```powershell
# Windows
netstat -ano | findstr :5000
netstat -ano | findstr :3306
```

```bash
# Linux
lsof -i :5000
lsof -i :3306
```

### View Recent Logs
```powershell
# Windows
Get-Content .\logs\session_*.log -Tail 100
```

```bash
# Linux
tail -100 logs/session_*.log
```

## Auto-Update Behavior

The maintenance watcher automatically:
1. Checks for git updates every 60 seconds
2. Creates a database backup before pulling
3. Detects if the watcher script itself was updated
4. If updated: stops bot → pulls changes → restarts via bootstrapper
5. Commits database schema changes before updates

## Control Flags

The maintenance watcher watches for these files:
- `restart.flag` - Restart the bot
- `stop.flag` - Stop everything and exit
- `update_pending.flag` - Indicates update in progress

These are typically created by the web dashboard API.

## Support

For issues:
1. Check the log files in the `logs/` directory
2. Verify all `.env` variables are set correctly
3. Ensure database and Discord token are valid
4. Review error messages for specific guidance
5. Check `CONFIG_DOCUMENTATION.md` for config options

## Performance Notes

- Web dashboard uses ~50-100 MB memory
- Bot uses ~200-300 MB memory depending on guild count
- Database connection pool: 5 concurrent connections
- Log streaming: Real-time via WebSocket
- Background tasks: Update checks every 60 seconds, XP every minute, wrapped checks daily
