# 🤖 Sulfur Discord Bot

A feature-rich Discord bot with AI capabilities, mini-games, and comprehensive management tools.

## 📋 Table of Contents

- [Features](#-features)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
  - [Windows Installation](#windows-installation)
  - [Termux/Android Installation](#termuxandroid-installation)
  - [Linux Installation](#linux-installation)
  - [One-Command Termux Setup](#one-command-termux-setup)
- [Configuration](#-configuration)
- [Running the Bot](#-running-the-bot)
- [Web Dashboard](#-web-dashboard)
- [Maintenance Features](#-maintenance-features)
- [Troubleshooting](#-troubleshooting)
- [FAQ](#-faq)
- [Project Structure](#-project-structure)

## 🌟 Features

### 🎮 Games & Entertainment
- **Werwolf Game**: Multiplayer werewolf game with dynamic voice channels and multiple roles
- **Gambling Games**: 
  - 🃏 Blackjack - Classic card game with hit/stand mechanics
  - 🎰 Roulette - Number, color, and betting options
  - 🔫 Russian Roulette - High-risk, high-reward challenge
  - 💣 Mines - Grid-based multiplier game
- **Daily Quests**: Earn rewards by completing daily challenges (messages, voice time, reactions, gaming)
- **Voice Manager**: Advanced voice channel management and tracking

### 💰 Economy System
- **Virtual Currency**: Earn coins through activities and complete quests
- **Shop System**: 
  - 🎨 Custom color roles (Basic, Premium, Legendary tiers)
  - 🔓 Feature unlocks (DM access, games, special permissions)
  - 📊 Purchase history and transaction tracking
- **Daily Rewards**: Claim daily coins and bonuses
- **Leaderboards**: Track top earners and active members
- **Monthly Milestones**: Bonus rewards for consistent participation

### 🤖 AI Capabilities
- **Multi-Model Support**: Gemini (2.0-flash-exp, 1.5-pro, 2.5-flash), OpenAI (GPT-4o, GPT-4-turbo, GPT-5)
- **AI Vision**: Image analysis and understanding with vision models
- **Conversation Follow-up**: Remembers context within 2-minute windows for natural conversations
- **Smart Emoji Analysis**: AI-powered custom emoji descriptions and contextual usage

### 📊 Management & Analytics
- **Web Dashboard**: Real-time bot monitoring at http://localhost:5000
- **AI Usage Tracking**: Monitor token usage and costs across all models with grouped totals by model and feature
- **Transaction Logging**: Full audit trail for all economy operations (shop purchases, daily rewards, gambling)
- **Wrapped Statistics**: Discord Wrapped-style yearly summaries with opt-in system
- **Auto-backup**: Database backups every 30 minutes
- **Level System**: XP tracking and automatic role assignment

### 🔧 Automation
- **Auto-update**: Checks for updates every minute
- **Auto-commit**: Commits database changes every 5 minutes
- **Auto-restart**: Gracefully restarts on updates
- **24/7 Operation**: Self-healing maintenance scripts with comprehensive logging

## 📦 Prerequisites

### All Platforms
- **Python**: 3.8 or higher
- **MySQL/MariaDB**: Latest stable version
- **Git**: For version control and auto-updates
- **Discord Bot Token**: From [Discord Developer Portal](https://discord.com/developers/applications)
- **API Keys**: 
  - Google Gemini API key (from [Google AI Studio](https://aistudio.google.com/))
  - OpenAI API key (optional, from [OpenAI Platform](https://platform.openai.com/))

### Windows Specific
- Windows 10 or 11
- PowerShell 5.1 or later (comes with Windows)
- MySQL Server or XAMPP/WAMP

### Termux/Android Specific
- Android 7.0 or higher
- Termux app from F-Droid (NOT Google Play - the Play Store version is outdated)
- Termux packages: `python`, `git`, `mariadb`, `openssh` (or remote MySQL access)

### Linux Specific
- Ubuntu 20.04+ / Debian 10+ / Other modern Linux distribution
- Bash shell

## ⚡ Quick Start - Get Running in 5 Minutes!

> **Choose your platform** and follow the automated setup - no technical knowledge required!

### 🪟 Windows - One-Click Installation (Recommended)

**The easiest way to get started!** Our installation wizard handles everything automatically:

1. **Clone the repository:**
   ```powershell
   git clone https://github.com/mereMint/sulfur.git
   cd sulfur
   ```

2. **Run the wizard:**
   - **Double-click** `INSTALL.bat` (easiest!)
   - Or run in PowerShell: `.\install_wizard.ps1`

3. **Follow the prompts** - The wizard will:
   - ✅ Check & install prerequisites (Python, Git, MySQL)
   - ✅ Help you get Discord Bot Token & API keys
   - ✅ Configure everything automatically (.env, database, dependencies)
   - ✅ Test your setup to ensure everything works
   - ✅ Create desktop shortcuts for easy access
   - ✅ Offer to start the bot immediately

**That's it!** 🎉 Your bot will be running in minutes.

**📖 Need help?** See [INSTALL_WINDOWS.md](INSTALL_WINDOWS.md) for detailed instructions and troubleshooting.

---

### 🐧 Linux - Automated Setup

Quick and easy command-line setup:

```bash
# Clone the repository
git clone https://github.com/mereMint/sulfur.git
cd sulfur

# Run the quick setup script
chmod +x quick_setup.sh
./quick_setup.sh
```

The script handles: Prerequisites ✓ Database ✓ Dependencies ✓ Configuration ✓

---

### 📱 Termux/Android - One-Command Setup

**Run everything in one command!**

```bash
pkg update && pkg install -y git && \
git clone https://github.com/mereMint/sulfur.git sulfur && \
cd sulfur && bash termux_quickstart.sh
```

The automated script will:
- ✅ Install all required packages (Python, MariaDB, Git)
- ✅ Set up and start MariaDB database
- ✅ Configure SSH keys (optional)
- ✅ Create virtual environment and install dependencies
- ✅ Guide you through .env configuration
- ✅ Create startup shortcuts
- ✅ Verify the complete setup

**📖 Detailed Termux Guide:** See [TERMUX_GUIDE.md](TERMUX_GUIDE.md)

---

## 💿 Manual Installation

<details>
<summary><b>🪟 Windows Manual Setup</b> (Click to expand)</summary>

### Prerequisites
1. **Install Python 3.8+** from [python.org](https://www.python.org/downloads/) (✅ Check "Add to PATH")
2. **Install MySQL** - Choose one:
   - [XAMPP](https://www.apachefriends.org/) (Recommended for beginners)
   - [MySQL Server](https://dev.mysql.com/downloads/installer/)
3. **Install Git** from [git-scm.com](https://git-scm.com/download/win)

### Setup Steps

```powershell
# 1. Clone repository
git clone https://github.com/mereMint/sulfur.git
cd sulfur

# 2. Create database (in MySQL command line or phpMyAdmin)
CREATE DATABASE sulfur_bot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'sulfur_bot_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON sulfur_bot.* TO 'sulfur_bot_user'@'localhost';
FLUSH PRIVILEGES;

# 3. Configure environment
Copy-Item .env.example .env
notepad .env  # Add your Discord token, API keys, and database password

# 4. Install dependencies
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 5. Start the bot
.\start.ps1
```

**Access Dashboard:** http://localhost:5000

</details>

<details>
<summary><b>🐧 Linux Manual Setup</b> (Click to expand)</summary>

### Prerequisites

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install -y python3 python3-pip python3-venv git mariadb-server

# Fedora/RHEL
sudo dnf install -y python3 python3-pip git mariadb-server

# Start MariaDB
sudo systemctl start mariadb && sudo systemctl enable mariadb
```

### Setup Steps

```bash
# 1. Clone repository
git clone https://github.com/mereMint/sulfur.git
cd sulfur

# 2. Create database
sudo mysql
# Then in MySQL:
CREATE DATABASE sulfur_bot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'sulfur_bot_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON sulfur_bot.* TO 'sulfur_bot_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;

# 3. Configure environment
cp .env.example .env
nano .env  # Add your tokens and keys

# 4. Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 5. Start the bot
chmod +x start.sh
./start.sh
```

**Access Dashboard:** http://localhost:5000

</details>

<details>
<summary><b>📱 Termux Manual Setup</b> (Click to expand)</summary>

### Prerequisites

```bash
# Update and install packages
pkg update && pkg upgrade -y
pkg install -y python git mariadb

# Initialize and start MariaDB
mariadb-install-db
mariadbd-safe --datadir=$PREFIX/var/lib/mysql &
sleep 10  # Wait for MariaDB to start
```

### Setup Steps

```bash
# 1. Clone repository
git clone https://github.com/mereMint/sulfur.git
cd sulfur

# 2. Create database
mariadb -u root
# Then in MariaDB:
CREATE DATABASE sulfur_bot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'sulfur_bot_user'@'localhost' IDENTIFIED BY '';
GRANT ALL PRIVILEGES ON sulfur_bot.* TO 'sulfur_bot_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;

# 3. Configure environment
cp .env.example .env
nano .env  # Add your tokens (Ctrl+O to save, Ctrl+X to exit)

# 4. Install dependencies
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 5. Start the bot
chmod +x start.sh
./start.sh
```

**Access Dashboard:** 
- From Android: http://localhost:5000
- From other devices: http://YOUR_ANDROID_IP:5000

**Keep running in background:**
```bash
pkg install tmux
tmux new -s sulfur
./start.sh
# Detach: Ctrl+B then D
# Reattach: tmux attach -t sulfur
```

</details>

## ⚙️ Configuration

### Discord Bot Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Go to "Bot" section
4. Click "Add Bot"
5. **Enable these Privileged Gateway Intents:**
   - ✅ Presence Intent
   - ✅ Server Members Intent
   - ✅ Message Content Intent
6. Copy the bot token and add to `.env`

### Invite Bot to Server

Use this URL (replace YOUR_CLIENT_ID):
```
https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=8&scope=bot%20applications.commands
```

Get Client ID from: Discord Developer Portal > Your App > General Information

### Environment Variables Reference

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `DISCORD_BOT_TOKEN` | ✅ Yes | Bot token from Discord | `YOUR_BOT_TOKEN_HERE` |
| `DB_HOST` | ✅ Yes | MySQL host | `localhost` |
| `DB_USER` | ✅ Yes | MySQL username | `sulfur_bot_user` |
| `DB_PASS` | ✅ Yes | MySQL password | `your_secure_password` |
| `DB_NAME` | ✅ Yes | Database name | `sulfur_bot` |
| `GEMINI_API_KEY` | ✅ Yes | Google Gemini API key | `YOUR_GEMINI_KEY_HERE` |
| `OPENAI_API_KEY` | ⚠️ Optional | OpenAI API key | `YOUR_OPENAI_KEY_HERE` |
| `BOT_PREFIX` | ⚠️ Optional | Command prefix | `!` (default) |
| `OWNER_ID` | ⚠️ Optional | Your Discord user ID | `123456789012345678` |

---

## 🚀 Running the Bot

### Windows

```powershell
# Start with maintenance system (recommended)
.\maintain_bot.ps1

# Or start manually (for testing)
python bot.py
```

### Termux/Linux

```bash
# Simple start (recommended)
./start.sh

# Or use maintenance script directly
./maintain_bot.sh

# Run in background with screen
screen -S sulfur ./start.sh
# Detach: Ctrl+A, then D
# Reattach: screen -r sulfur
```

---

## 🌐 Web Dashboard

The web dashboard provides real-time monitoring and control.

**Access:** http://localhost:5000 (served by Waitress on port 5000)

### Features:
- 📊 **Live Statistics**: Server count, uptime, command usage
- 📝 **Real-time Logs**: Color-coded console output
- 🎮 **Bot Controls**: Start, stop, restart buttons
- 🤖 **AI Dashboard**: Token usage tracking with grouping by model and feature (7-day, 30-day, all-time)
- 💰 **Cost Monitoring**: Estimated API costs by model with totals
- 🛒 **Shop Commands**: `/shop view`, `/shop buy`, `/shop buy_color`, `/transactions`

### Dashboard Pages:
- `/` - Main dashboard with live log stream
- `/config` - Edit `config.json` safely
- `/database` - Quick database viewer (read-only)
- `/ai_usage` - JSON API for usage data
- `/ai_dashboard` - AI usage analytics view

---

## 🔧 Maintenance Features

### Auto-Update System

The maintenance scripts check for updates every 60 seconds:

1. Commits any local changes
2. Pulls latest code from repository
3. Restarts bot automatically
4. If maintenance script itself updates, entire system restarts

**Manual Update:**
```powershell
# Windows
git pull

# Termux/Linux
git pull
```

### Auto-Commit System

Every 5 minutes, the script:
1. Checks for uncommitted changes
2. Commits changes with timestamp
3. Pushes to remote repository

**Manual Commit:**
```powershell
# Windows
git add -A
git commit -m "Manual commit"
git push

# Termux/Linux
git add -A
git commit -m "Manual commit"
git push
```

### Auto-Backup System

Every 30 minutes:
1. Creates MySQL dump
2. Saves to `backups/` folder
3. Keeps only last 10 backups

**Manual Backup:**
```powershell
# Windows
mysqldump -u sulfur_bot_user -p sulfur_bot > backups\manual_backup.sql

# Termux/Linux
mariadb-dump -u sulfur_bot_user -p sulfur_bot > backups/manual_backup.sql
```

### Control Flags

Create these files in the root directory to control the bot:

- `restart.flag` - Gracefully restart bot (closes file handles, kills process, restarts)
- `stop.flag` - Gracefully stop bot and maintenance script (database backup, cleanup, exit)

```powershell
# Windows - Restart bot
New-Item -ItemType File -Path "C:\sulfur\restart.flag" -Force

# Windows - Stop bot
New-Item -ItemType File -Path "C:\sulfur\stop.flag" -Force

# Termux/Linux - Restart bot
touch ~/sulfur/restart.flag

# Termux/Linux - Stop bot
touch ~/sulfur/stop.flag
```

**Windows Enhancements** (Latest Version):
- Uses .NET Process for robust start/stop/cleanup
- Closes file handles before killing process (prevents orphaned handles)
- Detects and kills orphaned Python processes from this directory
- Improved error reporting with stack traces

**Termux/Linux Enhancements** (Latest Version):
- `--no-backup` or `-n` flag to skip database backups
- Orphaned Python process cleanup on startup
- Log pruning (keeps last 20 maintenance, bot, and web logs)
- Example: `./maintain_bot.sh --no-backup`

---

## 🔍 Troubleshooting

### Bot Won't Start

**Problem:** "Could not connect to database"
```
Solution:
1. Check if MySQL is running:
   Windows: Services > MySQL
   Linux: sudo systemctl status mysql/mariadb
   Termux: ps aux | grep mariadb

2. Verify credentials in .env file
3. Test connection: 
   Windows/Linux: mysql -u sulfur_bot_user -p
   Termux: mariadb -u sulfur_bot_user -p
```

**Problem:** "Invalid Discord token"
```
Solution:
1. Regenerate token in Discord Developer Portal
2. Update DISCORD_BOT_TOKEN in .env
3. Ensure no extra spaces or quotes
```

**Problem:** "Module not found"
```
Solution:
1. Activate virtual environment:
   Windows: .\venv\Scripts\Activate.ps1
   Termux/Linux: source venv/bin/activate

2. Reinstall dependencies:
   pip install -r requirements.txt
```

### Database Issues

**Problem:** "Table doesn't exist"
```
Solution:
Run the database migration:
mysql -u sulfur_bot_user -p sulfur_bot < scripts/db_migrations/002_medium_priority_features.sql
```

**Problem:** "Too many connections"
```
Solution:
Edit MySQL config to increase max_connections:

Windows: C:\ProgramData\MySQL\MySQL Server X.X\my.ini
Linux: /etc/mysql/my.cnf

Add:
[mysqld]
max_connections = 200

Restart MySQL
```

### Web Dashboard Issues

**Problem:** "Dashboard won't load"
```
Solution:
1. Check if port 5000 is available:
   Windows: netstat -ano | findstr :5000
   Linux: lsof -i :5000

2. Change port in `web_dashboard.py` (Waitress):
   from waitress import serve
   serve(socketio.WSGIApp(app), host='0.0.0.0', port=5001)
```

**Problem:** "Logs not showing"
```
Solution:
1. Check logs directory exists
2. Verify web_dashboard has write permissions
3. Restart web dashboard
```

### Termux Specific Issues

**Problem:** "Permission denied" when starting bot
```
Solution:
chmod +x start.sh maintain_bot.sh
```

**Problem:** Bot stops when Termux closes
```
Solution:
Install Termux:Boot app or use screen:

pkg install screen
screen -S sulfur ./start.sh
# Detach with Ctrl+A, D
```

**Problem:** "Cannot connect to localhost MySQL" or "Can't connect to local server through socket"
```
Solution:
1. The error message mentioning 'mysql' is because it's deprecated. Use 'mariadb' instead.
2. Start MariaDB: mariadbd-safe --datadir=$PREFIX/var/lib/mysql &
3. Wait 10-15 seconds for it to fully start
4. Check if running: ps aux | grep mariadb
5. Test connection: mariadb -u root -p
6. If socket error persists, check: ls -la $PREFIX/var/run/mysqld.sock
```

**Problem:** "mysql: Deprecated program name"
```
Solution:
Replace all 'mysql' commands with 'mariadb':
- Instead of: mysql -u root -p
- Use: mariadb -u root -p
- Instead of: mysqldump
- Use: mariadb-dump
```

**Problem:** "ERROR 2002 (HY000): Can't connect to local server through socket"
```
Solution:
1. This usually means MariaDB isn't running or hasn't finished starting
2. Start MariaDB: mariadbd-safe --datadir=$PREFIX/var/lib/mysql &
3. Wait 15 seconds: sleep 15
4. Check if socket exists: ls -la $PREFIX/var/run/mysqld.sock
5. If no socket, check logs: cat $PREFIX/var/lib/mysql/*.err
6. Try connecting: mariadb -u root
```

**Problem:** Web dashboard not accessible from browser
```
Solution:
1. Check if the dashboard is running: ps aux | grep web_dashboard
2. Find your device IP: ifconfig or ip addr show
3. Access via: http://YOUR_IP:5000
4. If still not working, ensure web_dashboard.py uses host='0.0.0.0' not 'localhost'
```

### Common Issues (Fixed in Latest Version)

**Problem:** "Database backup failed" in maintenance script logs
```
Cause: The script couldn't find mysqldump/mariadb-dump or authentication failed
Solution (Already Fixed):
- The maintain_bot.sh script now tries multiple methods:
  1. Using DB_PASS from .env if set
  2. No password authentication (for passwordless users)
  3. Falls back to /etc/mysql/debian.cnf if available
- Ensure your .env has the correct DB_PASS value or leave it empty if no password
```

**Problem:** "Web Dashboard failed to start" - SocketIO.WSGIApp error
```
Cause: Flask-SocketIO API changed in newer versions
Solution (Already Fixed):
- Updated web_dashboard.py to use socketio.run() instead of socketio.WSGIApp()
- The dashboard now starts correctly with Werkzeug dev server
```

**Problem:** Bot doesn't react to messages
```
Cause: Bot needs to be mentioned or its name used in messages
Solution:
1. Mention the bot: @BotName hello
2. Use bot name in message: "sulfur what's up?"
3. Check config/config.json for configured bot names
4. Ensure intents are enabled in Discord Developer Portal:
   - MESSAGE CONTENT INTENT must be enabled
   - Server Members Intent
   - Presence Intent
```

**Problem:** "/rank command can't connect to database" or similar DB errors
```
Cause: Missing database tables (conversation_context, ai_model_usage, etc.)
Solution (Already Fixed):
- Run the bot once - it will auto-create all required tables
- Or manually: python3 -c "from modules import db_helpers; db_helpers.init_db_pool('localhost', 'sulfur_bot_user', '', 'sulfur_bot'); db_helpers.initialize_database()"
- All tables including conversation_context, ai_model_usage, emoji_descriptions, and wrapped_registrations are now created automatically
```

**Problem:** "ADD COLUMN IF NOT EXISTS" SQL syntax errors
```
Cause: MySQL doesn't support this syntax
Solution (Already Fixed):
- Updated db_helpers.py to check if columns exist before adding them
- Uses "SHOW COLUMNS FROM table LIKE 'column'" pattern
```

**Problem:** Git commit fails in maintenance script
```
Cause: Git not configured or no push permissions
Solution:
1. Configure git: 
   git config --global user.email "you@example.com"
   git config --global user.name "Your Name"
2. For Termux: Set up SSH keys (see Installation section)
3. For testing: The script continues even if git fails
```

---

## ❓ FAQ

### General Questions

**Q: Can I run this bot 24/7?**
A: Yes! The maintenance scripts are designed for 24/7 operation with auto-restart on crashes.

**Q: How much does it cost to run?**
A: Free for hosting (if you run it yourself). API costs vary:
- Gemini: Free tier available, then $0.00025/1K tokens
- OpenAI GPT-4: $0.03/1K input tokens, $0.06/1K output tokens

**Q: Can I use this bot in multiple servers?**
A: Yes, one bot instance can serve unlimited servers.

**Q: Is this bot open source?**
A: Yes, you can modify and customize it as needed.

### Technical Questions

**Q: Can I use PostgreSQL instead of MySQL?**
A: Not without modifications. The bot uses MySQL-specific syntax.

**Q: Can I run the bot without the web dashboard?**
A: Yes, just start with `python bot.py` instead of the maintenance script.

**Q: How do I backup my data?**
A: Automatic backups run every 30 minutes. Manual: 
- Windows: `mysqldump -u sulfur_bot_user -p sulfur_bot > backup.sql`
- Termux/Linux: `mariadb-dump -u sulfur_bot_user -p sulfur_bot > backup.sql`

**Q: Can I use only Gemini or only OpenAI?**
A: Yes, just don't set the API key for the one you don't want to use.

### Feature Questions

**Q: How do I disable auto-updates?**
A: Comment out the update check in maintain_bot.ps1/sh (lines with `Test-ForUpdates` or `check_for_updates`)

**Q: How do I change auto-commit frequency?**
A: Edit `$commitInterval` (PowerShell) or `COMMIT_INTERVAL` (bash) in the maintenance script

**Q: Can I add custom commands?**
A: Yes! Add them to `modules/` and import in `bot.py`

---

## 📁 Project Structure

```
sulfur/
├── bot.py                     # Main bot file
├── web_dashboard.py           # Web dashboard server (Waitress + Flask-SocketIO)
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables (create this)
│
├── config/                    # Configuration files
│   ├── bot_status.json        # Real-time bot status (written by maintenance script)
│   └── database_sync.sql      # Auto-generated DB sync (if used)
│
├── web/                       # Web dashboard templates
│   ├── index.html             # Main dashboard
│   ├── layout.html            # Shared layout
│   ├── config.html            # Config editor
│   ├── database.html          # Database viewer
│   ├── ai_dashboard.html      # AI stats page
│   └── ...
│
├── modules/                   # Bot modules
│   ├── api_helpers.py         # AI API integration
│   ├── db_helpers.py          # Database functions
│   ├── emoji_manager.py       # Emoji analysis system
│   ├── werwolf.py             # Werwolf game
│   └── ...
│
├── scripts/                   # Utility scripts
│   ├── db_migrations/         # Database migrations
│   ├── check_errors.ps1       # Pre-flight checks
│   └── ...
│
├── logs/                      # Log files (auto-generated)
│   ├── maintenance_*.log      # Maintenance script logs
│   ├── bot_*.log              # Bot runtime logs
│   └── maintenance_*_web.log  # Web dashboard logs
│
├── backups/                   # Database backups (auto-generated)
│   └── sulfur_bot_backup_*.sql
│
├── docs/                      # Documentation
│   ├── IMPLEMENTATION_SUMMARY.md
│   └── MEDIUM_PRIORITY_FEATURES.md
│
└── maintain_bot.ps1 / .sh     # Maintenance scripts
   start.sh                   # Simple startup script
   TODO.md                    # Feature roadmap
   README.md                  # This file
```

---

## 🎯 Next Steps

After installation:

1. **Test Commands**: Join your server and try `!help`
2. **Configure Permissions**: Set up role-based access
3. **Enable Features**: Check TODO.md for available features
4. **Monitor Dashboard**: Visit http://localhost:5000 (status from `config/bot_status.json`)
5. **Join Support Server**: (Add your Discord server invite)

---

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## 📄 License

This project is licensed under the MIT License.

---

## 🆘 Support

- **Issues**: GitHub Issues
- **Discord**: (Add your Discord server link)
- **Email**: (Add your contact email)

---

## 🎉 Credits

- **Discord.py**: Amazing Discord library
- **Google Gemini**: AI capabilities
- **OpenAI**: GPT models
- **All Contributors**: Thank you!

---

**Made with ❤️ for the Discord community**
