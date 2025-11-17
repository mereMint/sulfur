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
- **Werwolf Game**: Multiplayer werewolf game with dynamic voice channels
- **Mini-games**: Various interactive games for server engagement

### 🤖 AI Capabilities
- **Multi-Model Support**: Gemini (2.0-flash-exp, 1.5-pro, 2.5-flash) and OpenAI (GPT-4o, GPT-4-turbo)
- **AI Vision**: Image analysis and understanding
- **Conversation Follow-up**: Remembers context within 2-minute windows
- **Smart Emoji Analysis**: AI-powered custom emoji descriptions

### 📊 Management & Analytics
- **Web Dashboard**: Real-time bot monitoring at http://localhost:5000
- **AI Usage Tracking**: Monitor token usage and costs across all models
- **Wrapped Statistics**: Discord Wrapped-style yearly summaries
- **Auto-backup**: Database backups every 30 minutes

### 🔧 Automation
- **Auto-update**: Checks for updates every minute
- **Auto-commit**: Commits database changes every 5 minutes
- **Auto-restart**: Gracefully restarts on updates
- **24/7 Operation**: Self-healing maintenance scripts

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

## 💿 Installation

## ⚡ Quick Start

### Windows (PowerShell)

```powershell
# 1) Clone and enter the repo
git clone https://github.com/mereMint/sulfur.git; cd sulfur

# 2) Create venv + install deps
python -m venv venv; .\venv\Scripts\Activate.ps1; pip install -r requirements.txt

# 3) Run the maintenance system (starts bot + web dashboard)
./maintain_bot.ps1
```

Open http://localhost:5000 for the dashboard. Press Q in the maintenance window to shut down cleanly.

### Termux/Linux (bash)

```bash
# 1) Clone and enter the repo
git clone https://github.com/mereMint/sulfur.git && cd sulfur

# 2) Create venv + install deps
python -m venv venv && source venv/bin/activate && pip install -r requirements.txt

# 3) Start (wrapper runs the maintenance script)
chmod +x start.sh maintain_bot.sh && ./start.sh
```

Dashboard: http://localhost:5000 (served by Waitress). Stop with Ctrl+C or create `stop.flag`.

### Windows Installation

#### Step 1: Install Prerequisites

1. **Install Python**
   - Download from [python.org](https://www.python.org/downloads/)
   - ✅ Check "Add Python to PATH" during installation
   - Verify: Open PowerShell and run `python --version`

2. **Install MySQL**
   - Option A: [MySQL Server](https://dev.mysql.com/downloads/installer/)
   - Option B: [XAMPP](https://www.apachefriends.org/) (easier for beginners)
   - During setup, remember your root password

3. **Install Git**
   - Download from [git-scm.com](https://git-scm.com/download/win)
   - Use default settings during installation
   - Verify: `git --version`

#### Step 2: Clone Repository

```powershell
cd C:\
git clone https://github.com/mereMint/sulfur.git
cd sulfur
```

#### Step 3: Setup Database

1. **Start MySQL** (if using XAMPP, start from control panel)

2. **Create Database User**
```sql
-- Open MySQL command line or phpMyAdmin
CREATE DATABASE sulfur_bot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER 'sulfur_bot_user'@'localhost' IDENTIFIED BY 'your_secure_password';

GRANT ALL PRIVILEGES ON sulfur_bot.* TO 'sulfur_bot_user'@'localhost';

FLUSH PRIVILEGES;
```

3. **Initialize Database Schema**
```powershell
# No manual schema file needed — tables are created automatically on first run.
# Optional: if you have an existing backup, you can import it:
mysql -u sulfur_bot_user -p sulfur_bot < backups\latest_backup.sql

# Optional: apply specific migrations later if needed:
# mysql -u sulfur_bot_user -p sulfur_bot < scripts\db_migrations\002_medium_priority_features.sql
```

#### Step 4: Configure Environment

1. **Create `.env` file** in the project root (or copy from `.env.example`):
```env
# Discord Bot Token (from https://discord.com/developers/applications)
DISCORD_BOT_TOKEN=your_discord_bot_token_here

# Database Configuration
DB_HOST=localhost
DB_USER=sulfur_bot_user
DB_PASS=your_secure_password
DB_NAME=sulfur_bot

# AI API Keys
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Bot Configuration
BOT_PREFIX=!
OWNER_ID=your_discord_user_id
```

2. **Get Your Discord User ID**
   - Enable Developer Mode in Discord (Settings > Advanced > Developer Mode)
   - Right-click your username > Copy ID

#### Step 5: Install Python Dependencies

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

#### Step 6: First Run Test

```powershell
# Test bot startup
python bot.py
```

If you see "Bot is ready!" in the console, press Ctrl+C and proceed to start the maintenance script (it will handle 24/7 operation).

#### Step 7: Start Maintenance System

```powershell
# Run the maintenance script (handles auto-restart, updates, backups)
.\maintain_bot.ps1
```

The script will:
- ✅ Start the web dashboard at http://localhost:5000
- ✅ Start the bot
- ✅ Check for updates every minute
- ✅ Auto-commit changes every 5 minutes
- ✅ Backup database every 30 minutes
- ✅ Auto-restart on updates

Press **Q** to gracefully shutdown.

---

### Termux/Android Installation

> **🚀 NEW: One-Command Setup!** Skip manual steps with our automated installer:
> ```bash
> pkg install -y wget && wget https://raw.githubusercontent.com/mereMint/sulfur/main/termux_quickstart.sh && bash termux_quickstart.sh
> ```
> **📖 For detailed Termux guide, see [TERMUX_GUIDE.md](TERMUX_GUIDE.md)**

#### Manual Installation

#### Step 1: Install Termux

1. **Download Termux** from [F-Droid](https://f-droid.org/en/packages/com.termux/) (NOT Google Play)
2. Open Termux

#### Step 2: Install Prerequisites

```bash
# Update package list
pkg update && pkg upgrade

# Install required packages
pkg install python git mariadb tmux openssh

# Verify installations
python --version
git --version
mariadb --version
```

#### Step 3: Setup Git SSH Keys (for pushing to GitHub)

```bash
# Generate SSH key (press Enter to accept defaults)
ssh-keygen -t ed25519 -C "your_email@example.com"

# Start SSH agent
eval "$(ssh-agent -s)"

# Add your SSH key
ssh-add ~/.ssh/id_ed25519

# Display your public key
cat ~/.ssh/id_ed25519.pub

# Copy the output and add it to GitHub:
# Go to GitHub → Settings → SSH and GPG keys → New SSH key
# Paste the key and save

# Test SSH connection
ssh -T git@github.com
```

#### Step 4: Setup MariaDB

```bash
# Initialize MariaDB
mariadb-install-db

# Start MariaDB server
mariadbd-safe --datadir=$PREFIX/var/lib/mysql &

# Wait a few seconds, then press Enter to get prompt back

# IMPORTANT: Check if MariaDB socket is running
ls -la $PREFIX/var/run/mysqld.sock 2>/dev/null || echo "Socket not found - MariaDB may still be starting"

# Wait for MariaDB to fully start (usually takes 10-15 seconds)
sleep 10
```

#### Step 5: Clone Repository

```bash
# Navigate to home directory
cd ~

# Clone repository (use SSH if you added SSH keys, or HTTPS)
git clone git@github.com:yourusername/sulfur.git
# Or use HTTPS: git clone https://github.com/yourusername/sulfur.git
cd sulfur
```

#### Step 6: Setup Database

```bash
# Login to MariaDB (use 'mariadb' command, not 'mysql')
# Note: On first login, there may be no password set (just press Enter)
mariadb -u root -p

# In MariaDB prompt:
CREATE DATABASE sulfur_bot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER 'sulfur_bot_user'@'localhost' IDENTIFIED BY 'your_secure_password';

GRANT ALL PRIVILEGES ON sulfur_bot.* TO 'sulfur_bot_user'@'localhost';

FLUSH PRIVILEGES;

EXIT;

# Note: If you prefer no password for local development:
# CREATE USER 'sulfur_bot_user'@'localhost' IDENTIFIED BY '';
# Then set DB_PASS='' in your .env file

# Initialize schema (auto-created on first run)
# No manual schema import required.
# Optional: import an existing backup instead:
# mariadb -u sulfur_bot_user -p sulfur_bot < backups/latest_backup.sql
```

#### Step 7: Configure Environment

```bash
# Create .env file
nano .env
```

Add the following (paste by long-pressing):
```env
DISCORD_BOT_TOKEN=your_discord_bot_token_here
DB_HOST=localhost
DB_USER=sulfur_bot_user
DB_PASS=your_secure_password
DB_NAME=sulfur_bot
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
BOT_PREFIX=!
OWNER_ID=your_discord_user_id
```

**Important:** Set `DB_PASS` to match what you used in Step 6. If you chose no password, use `DB_PASS=`

Save with **Ctrl+O**, **Enter**, then **Ctrl+X**

#### Step 8: Install Python Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### Step 9: Start Bot and Web Dashboard

```bash
# Make scripts executable
chmod +x start.sh maintain_bot.sh

# Start the bot
./start.sh
```

That's it! The bot is now running on your Android device.

#### Step 10: Access Web Dashboard

The web dashboard runs on port 5000. To access it:

**From the same Android device:**
- Open a browser on your Android device
- Navigate to: `http://localhost:5000` or `http://127.0.0.1:5000`

**From another device on the same network:**
- Find your Android device's IP address: `ifconfig` or `ip addr show`
- On the other device, navigate to: `http://YOUR_ANDROID_IP:5000`
- Example: `http://192.168.1.100:5000`

**Troubleshooting Dashboard Access:**
- If the dashboard doesn't load, ensure the web_dashboard.py is binding to `0.0.0.0` instead of `localhost`
- Check that port 5000 is not blocked by any firewall

**Tips for Termux:**
- Keep Termux running in the background (use Termux:Boot for auto-start)
- Use Termux:Widget to add start/stop shortcuts to home screen
- Press **Ctrl+C** to stop the bot gracefully
- To run in background (tmux): Already installed in Step 2, use:
   - `tmux new -s sulfur`
   - `./start.sh`
   - Detach: `Ctrl+B`, then `D`; Reattach: `tmux attach -t sulfur`
- Alternative (screen): Install `screen` with `pkg install screen`, then `screen ./start.sh`

---

### Linux Installation

#### Step 1: Install Prerequisites

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip python3-venv git mysql-server

# Fedora/RHEL
sudo dnf install python3 python3-pip git mariadb-server

# Arch Linux
sudo pacman -S python python-pip git mariadb

# Start MySQL
sudo systemctl start mysql
sudo systemctl enable mysql
```

#### Step 2: Setup Database

```bash
# Secure MySQL installation
sudo mysql_secure_installation

# Login to MySQL
sudo mysql

# Create database and user
CREATE DATABASE sulfur_bot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER 'sulfur_bot_user'@'localhost' IDENTIFIED BY 'your_secure_password';

GRANT ALL PRIVILEGES ON sulfur_bot.* TO 'sulfur_bot_user'@'localhost';

FLUSH PRIVILEGES;

EXIT;

# Initialize schema (auto-created on first run)
# No manual schema import required.
# Optional: import an existing backup instead:
# mysql -u sulfur_bot_user -p sulfur_bot < backups/latest_backup.sql
```

#### Step 3: Clone and Configure

```bash
# Clone repository
cd /opt  # or wherever you want to install
sudo git clone https://github.com/yourusername/sulfur.git
cd sulfur

# Create .env file
sudo nano .env
```

Add configuration (same as Termux section above)

#### Step 4: Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv

# Activate
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### Step 5: Start Bot

```bash
# Make scripts executable
chmod +x start.sh maintain_bot.sh

# Start
./start.sh
```

**Optional: Create systemd service for auto-start**

```bash
sudo nano /etc/systemd/system/sulfur-bot.service
```

Add:
```ini
[Unit]
Description=Sulfur Discord Bot
After=network.target mysql.service

[Service]
Type=simple
User=your_username
WorkingDirectory=/opt/sulfur
ExecStart=/opt/sulfur/start.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable sulfur-bot
sudo systemctl start sulfur-bot

# Check status
sudo systemctl status sulfur-bot
```

---

### One-Command Termux Setup

🚀 **The Fastest Way to Get Started on Android!**

Our automated Termux setup script handles **everything** in one command:

```bash
pkg install -y wget && wget https://raw.githubusercontent.com/mereMint/sulfur/main/termux_quickstart.sh && bash termux_quickstart.sh
```

**What it does:**
- ✅ Updates Termux packages
- ✅ Installs Python, MariaDB, Git, OpenSSH
- ✅ Initializes and starts MariaDB
- ✅ Creates database and user
- ✅ Clones the repository
- ✅ Generates SSH key (optional)
- ✅ Sets up Python virtual environment
- ✅ Installs all dependencies
- ✅ Configures `.env` interactively
- ✅ Initializes database tables
- ✅ Creates startup helper script
- ✅ Runs setup verification

**After installation:**
```bash
cd ~/sulfur
./start_sulfur.sh
```

📖 **For detailed Termux documentation:** See [TERMUX_GUIDE.md](TERMUX_GUIDE.md)

---

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
- 🤖 **AI Dashboard**: Token usage tracking across all models (7-day, 30-day, all-time)
- 💰 **Cost Monitoring**: Estimated API costs

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

- `restart.flag` - Gracefully restart bot
- `stop.flag` - Gracefully stop bot and maintenance script

```powershell
# Windows - Restart bot
New-Item -ItemType File -Name "restart.flag"

# Termux/Linux - Restart bot
touch restart.flag
```

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
