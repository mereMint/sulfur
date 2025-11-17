# Quick Setup Guide

## Current Status ✓

Your configuration has been verified. Here's what you need to do:

### ✅ Already Complete
- ✓ `.env` file exists with all required API keys
- ✓ `config/config.json` is valid
- ✓ `config/system_prompt.txt` exists
- ✓ Discord bot token is set
- ✓ Gemini API key is set
- ✓ OpenAI API key is set

### ⚠️ Needs Action

#### 1. Install MySQL/MariaDB

**Windows:**
- Download and install [MySQL](https://dev.mysql.com/downloads/installer/) or [XAMPP](https://www.apachefriends.org/)
- Start MySQL service from Services or XAMPP Control Panel

**Termux:**
```bash
pkg install mariadb
mysql_install_db
mysqld_safe &
```

**Linux:**
```bash
sudo apt install mysql-server  # or mariadb-server
sudo systemctl start mysql
```

#### 2. Run Database Setup

**Windows PowerShell:**
```powershell
.\setup_mysql.ps1
```

**Termux/Linux:**
```bash
chmod +x setup_mysql.sh
./setup_mysql.sh
```

This will:
- Create the `sulfur_bot` database
- Create the `sulfur_bot_user` user
- Grant appropriate privileges
- Test the connection

#### 3. Install Python Dependencies

```bash
# Activate virtual environment (if using one)
# Windows: .\venv\Scripts\Activate.ps1
# Linux/Termux: source venv/bin/activate

pip install -r requirements.txt
```

This installs:
- discord.py (Discord API)
- mysql-connector-python (Database)
- google-generativeai (Gemini AI)
- openai (OpenAI API)
- Flask + Flask-SocketIO + waitress (Web dashboard)
- python-dotenv (Environment variables)
- aiohttp (Async HTTP)

#### 4. Verify Setup

Run the test script to verify everything is working:

```bash
python test_setup.py
```

This checks:
- Environment variables
- Configuration files
- Database connectivity
- API connectivity (Gemini & OpenAI)

#### 5. Start the Bot

**Windows:**
```powershell
.\maintain_bot.ps1
```

**Termux/Linux:**
```bash
./start.sh
```

The maintenance script will:
- Start the web dashboard on http://localhost:5000
- Start the Discord bot
- Auto-update from git every minute
- Auto-commit changes every 5 minutes
- Auto-backup database every 30 minutes

## Troubleshooting

### MySQL Connection Issues

**Error: Can't connect to MySQL server**
- Check if MySQL is running: `Get-Process mysqld` (Windows) or `pgrep mysqld` (Linux)
- Verify credentials in `.env` file match your MySQL setup
- Try connecting manually: `mysql -u sulfur_bot_user sulfur_bot`

**Error: Access denied**
- Run the database setup script again: `.\setup_mysql.ps1` or `./setup_mysql.sh`
- Check if user exists: `mysql -u root -p -e "SELECT User, Host FROM mysql.user WHERE User='sulfur_bot_user';"`

### API Issues

**Gemini API not working**
- Verify API key at: https://aistudio.google.com/
- Check if you have API quota remaining
- Test with: `python -c "import google.generativeai as genai; genai.configure(api_key='YOUR_KEY'); print('OK')"`

**OpenAI API not working**
- Verify API key at: https://platform.openai.com/api-keys
- Check billing and usage limits
- Test with: `python -c "from openai import OpenAI; client = OpenAI(api_key='YOUR_KEY'); print('OK')"`

### Web Dashboard Not Starting

**Port 5000 already in use:**
```powershell
# Windows - Find what's using port 5000
netstat -ano | findstr :5000

# Linux/Termux
lsof -i :5000
```

To change the port, edit `web_dashboard.py`:
```python
serve(socketio.WSGIApp(app), host='0.0.0.0', port=5001)  # Change 5000 to 5001
```

### Bot Won't Connect to Discord

**Invalid token error:**
1. Go to https://discord.com/developers/applications
2. Select your application
3. Go to "Bot" tab
4. Click "Reset Token"
5. Update `DISCORD_BOT_TOKEN` in `.env` file

**Missing intents:**
1. Go to Discord Developer Portal
2. Bot → Privileged Gateway Intents
3. Enable:
   - Presence Intent
   - Server Members Intent
   - Message Content Intent

## Files Created

This setup created:
- `test_setup.py` - Comprehensive setup verification script
- `setup_database.sql` - SQL script to create database and user
- `setup_mysql.ps1` - Automated MySQL setup for Windows
- `setup_mysql.sh` - Automated MySQL setup for Termux/Linux
- `SETUP.md` - This file

## Next Steps After Setup

1. Invite your bot to a Discord server
2. Configure server-specific settings via slash commands
3. Access web dashboard at http://localhost:5000
4. Check logs in `logs/` directory
5. Monitor database in web dashboard

## Support

For issues:
1. Run `python test_setup.py` to diagnose
2. Check `logs/` for error messages
3. Verify `.env` configuration
4. See main `README.md` for detailed documentation
