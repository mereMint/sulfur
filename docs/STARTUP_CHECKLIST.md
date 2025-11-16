# Sulfur Bot - Pre-Startup Checklist

Use this checklist before starting the bot system.

## Environment Verification

- [ ] Python 3.10+ installed
  - Test: Open terminal and run `python --version`
  - Should show version 3.10 or higher

- [ ] Python in PATH
  - Test: Run `python -c "print('Python works')"` should output "Python works"
  - If not, add Python to system PATH

- [ ] Git installed
  - Test: Run `git --version`
  - Should show version 2.0 or higher

- [ ] MySQL/MariaDB running
  - Test: Check system services or processes
  - Windows: `tasklist | findstr mysqld`
  - Linux: `pgrep mysqld`
  - Termux: `pgrep mariadbd`
  - Should show at least one mysqld/mariadbd process

## Configuration Files

- [ ] `.env` file exists in `c:\sulfur\`
  - Contains: `DISCORD_BOT_TOKEN`, `GEMINI_API_KEY` or `OPENAI_API_KEY`
  - Variables are in format: `KEY="VALUE"`

- [ ] `config.json` valid JSON
  - Test: Online JSON validator or `python -m json.tool config.json`
  - Should parse without errors

- [ ] `system_prompt.txt` exists
  - Location: `c:\sulfur\system_prompt.txt`
  - Non-empty text file

- [ ] `requirements.txt` unchanged
  - Contains minimum packages:
    - discord.py
    - mysql-connector-python
    - Flask
    - Flask-SocketIO
    - waitress
    - python-dotenv

## Database Setup

- [ ] MySQL/MariaDB user `sulfur_bot_user` exists
  - Windows/Linux: `mysql -u sulfur_bot_user -h localhost`
  - Termux: `mariadb -u sulfur_bot_user -h localhost`
  - Should connect (may not have permissions yet)

- [ ] Database `sulfur_bot` exists
  - Windows/Linux: `mysql -u root -p` then `SHOW DATABASES;`
  - Termux: `mariadb -u root` then `SHOW DATABASES;`
  - Should list "sulfur_bot"

- [ ] User has proper permissions
  - Test: Connect as `sulfur_bot_user` and run `USE sulfur_bot;`
  - Should not raise permission errors

## Discord Bot Setup

- [ ] Bot token is valid
  - Test: Token format should be `XXX.XXX.XXX` (three parts with dots)
  - Should be long alphanumeric string

- [ ] Bot has required permissions
  - In Discord Developer Portal, check:
    - [ ] Read Messages/View Channels
    - [ ] Send Messages
    - [ ] Manage Channels
    - [ ] Manage Roles
    - [ ] Voice State
    - [ ] Connect to Voice
    - [ ] Speak
    - [ ] Mute/Unmute Members
    - [ ] Move Members

- [ ] Bot token NOT accidentally committed
  - Test: `git status` should not show `.env` in changes
  - Should see `.env` in `.gitignore`

## Ports and Network

- [ ] Port 5000 is available (Web Dashboard)
  - Test: Try `telnet localhost 5000` or similar
  - Should fail to connect (port is free)

- [ ] Port 3306 is open (MySQL)
  - Test: Check MySQL is listening on all interfaces
  - Or verify firewall allows localhost:3306

- [ ] Internet connection working
  - Test: `ping google.com` should show response
  - Needed for Discord connection and git updates

## Directory Structure

- [ ] All Python files present
  ```
  ✓ bot.py
  ✓ web_dashboard.py
  ✓ db_helpers.py
  ✓ voice_manager.py
  ✓ level_system.py
  ✓ economy.py
  ✓ werwolf.py
  ✓ api_helpers.py
  ✓ controls.py
  ✓ fake_user.py
  ```

- [ ] All startup scripts present
  ```
  ✓ maintain_bot.ps1 (Windows)
  ✓ start_bot.ps1 (Windows)
  ✓ maintain_bot.sh (Linux)
  ✓ start_bot.sh (Linux)
  ✓ bootstrapper.ps1
  ✓ bootstrapper.sh
  ✓ shared_functions.ps1
  ✓ shared_functions.sh
  ```

- [ ] All template files present
  ```
  ✓ index.html
  ✓ config.html
  ✓ database.html
  ✓ ai_usage.html
  ✓ layout.html
  ```

- [ ] Logs and backups directories exist
  ```
  ✓ logs/ (can be empty initially)
  ✓ backups/ (can be empty initially)
  ```

## Virtual Environment

- [ ] Python virtual environment set up
  - Location: `c:\sulfur\venv\`
  - Can be recreated automatically if missing
  - Contains all dependencies from `requirements.txt`

- [ ] All dependencies installed
  - Test: Run `.\venv\Scripts\python.exe -m pip list`
  - Should show all required packages
  - Minimum: discord.py, mysql-connector-python, Flask, waitress

## Final Checks Before Starting

1. [ ] Database is running and accessible
2. [ ] All config files are valid JSON
3. [ ] `.env` file has all required keys
4. [ ] Discord bot token is valid and has required permissions
5. [ ] No other services using ports 5000, 3306
6. [ ] Git repository is initialized (`.git/` folder exists)
7. [ ] Test MySQL/MariaDB connection:
   ```
   # Windows/Linux
   mysql -u sulfur_bot_user -h localhost -e "SELECT 1;"
   
   # Termux
   mariadb -u sulfur_bot_user -h localhost -e "SELECT 1;"
   ```
   Should return "1" without errors

## Ready to Start?

If all items are checked, proceed with:

**Windows:**
```powershell
cd c:\sulfur
.\maintain_bot.ps1
```

**Linux:**
```bash
cd /path/to/sulfur
chmod +x *.sh
./maintain_bot.sh
```

## Startup Should Produce

1. "Checking Python virtual environment..."
2. "Installing/updating Python dependencies..."
3. "Python environment is ready."
4. "Starting the Web Dashboard..."
5. "Web Dashboard is online and ready."
6. "Starting the bot process..."
7. "Bot is running..." with Process ID

## If Startup Fails

Check in this order:
1. Review error message in terminal
2. Check `logs/maintenance_*.log`, `logs/bot_*.log`, or `logs/*_web.log`
3. Verify MySQL is actually running
4. Verify `.env` file format (no quotes around values)
5. Check Discord token validity
6. Verify port 5000 is free: `netstat -ano | findstr :5000`

---

**Last Updated:** November 16, 2025
**Bot Version:** Latest main branch
**Status:** Ready for startup
