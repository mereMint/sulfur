# Sulfur Bot - Complete Setup Guide

> **⚡ Quick Start Available!**  
> For the easiest installation experience, use our automated wizards:
> - **Windows**: Run `INSTALL.bat` or see [INSTALL_WINDOWS.md](INSTALL_WINDOWS.md)
> - **Linux**: Run `./quick_setup.sh` or see [QUICKSTART.md](QUICKSTART.md)
> - **Termux**: Run `bash termux_quickstart.sh` or see [TERMUX_GUIDE.md](TERMUX_GUIDE.md)
>
> This manual guide is for advanced users who prefer manual configuration.

This guide will help you set up the Sulfur Discord bot on both **Windows** and **Termux/Linux**.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Windows Setup](#windows-setup)
3. [Termux Setup](#termux-setup)
4. [Linux Setup](#linux-setup)
5. [Configuration](#configuration)
6. [Running the Bot](#running-the-bot)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### All Platforms

- **Python 3.8+**
- **MySQL/MariaDB** database server
- **Git** (for auto-updates)
- **Discord Bot Token** (from [Discord Developer Portal](https://discord.com/developers/applications))
- **Gemini API Key** (from [Google AI Studio](https://aistudio.google.com/)) OR **OpenAI API Key** (from [OpenAI Platform](https://platform.openai.com/))

---

## Windows Setup

### Step 1: Install Prerequisites

1. **Install Python 3.8+**
   - Download from [python.org](https://www.python.org/downloads/)
   - During installation, check **"Add Python to PATH"**

2. **Install MySQL**
   - Option A: Download [XAMPP](https://www.apachefriends.org/) (easiest - includes MySQL)
   - Option B: Download [MySQL Community Server](https://dev.mysql.com/downloads/mysql/)
   - Start MySQL server (via XAMPP Control Panel or Windows Services)

3. **Install Git**
   - Download from [git-scm.com](https://git-scm.com/download/win)

### Step 2: Clone the Repository

Open PowerShell and run:

```powershell
cd C:\
git clone https://github.com/mereMint/sulfur.git
cd sulfur
```

### Step 3: Set Up Environment Variables

1. Copy `.env.example` to `.env` (if it exists) or edit the existing `.env` file
2. Fill in your credentials:

```env
DISCORD_BOT_TOKEN="your_discord_bot_token_here"
GEMINI_API_KEY="your_gemini_api_key_here"
DB_HOST="localhost"
DB_USER="sulfur_bot_user"
DB_PASS=""
DB_NAME="sulfur_bot"
```

### Step 4: Set Up Database

Run the setup script:

```powershell
.\setup_mysql.ps1
```

This will:
- Check if MySQL is running
- Find the MySQL executable
- Create the database and user
- Test the connection

When prompted, enter your MySQL **root password**.

### Step 5: Install Python Dependencies

```powershell
# Create virtual environment (optional but recommended)
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### Step 6: Test Setup

```powershell
python test_setup.py
```

This will verify:
- Environment variables
- Configuration files
- Database connection
- API connectivity

### Step 7: Run the Bot

```powershell
# Option 1: Simple start (recommended for first-time users)
.\start.ps1

# Option 2: Direct maintenance script
.\maintain_bot.ps1

# Option 3: Double-click start.bat
```

The bot will:
- Start automatically
- Auto-restart on crashes
- Check for updates every minute
- Auto-commit changes every 5 minutes
- Auto-backup database every 30 minutes
- Start web dashboard at http://localhost:5000

---

## Termux Setup

### Step 1: Install Prerequisites

Open Termux and run:

```bash
# Update packages
pkg update && pkg upgrade -y

# Install required packages
pkg install -y python git mariadb

# Initialize MariaDB
mysql_install_db

# Start MariaDB
mysqld_safe --datadir=$PREFIX/var/lib/mysql &

# Wait for MariaDB to start
sleep 5
```

### Step 2: Secure MariaDB (Optional)

```bash
# Set root password (optional)
mysql -u root
```

In MySQL:
```sql
ALTER USER 'root'@'localhost' IDENTIFIED BY '';
FLUSH PRIVILEGES;
EXIT;
```

### Step 3: Clone the Repository

```bash
cd ~
git clone https://github.com/mereMint/sulfur.git
cd sulfur
```

### Step 4: Set Up Environment Variables

Edit the `.env` file:

```bash
nano .env
```

Fill in your credentials:
```env
DISCORD_BOT_TOKEN="your_discord_bot_token_here"
GEMINI_API_KEY="your_gemini_api_key_here"
DB_HOST="localhost"
DB_USER="sulfur_bot_user"
DB_PASS=""
DB_NAME="sulfur_bot"
```

Press `Ctrl+X`, then `Y`, then `Enter` to save.

### Step 5: Set Up Database

Make the script executable and run it:

```bash
chmod +x setup_mysql.sh
bash setup_mysql.sh
```

When prompted for password, just press `Enter` (default is no password).

### Step 6: Install Python Dependencies

```bash
# Create virtual environment (optional)
python -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 7: Test Setup

```bash
python test_setup.py
```

### Step 8: Run the Bot

```bash
# Make start script executable
chmod +x start.sh

# Run the bot
bash start.sh

# Or directly:
./start.sh
```

---

## Linux Setup

### Step 1: Install Prerequisites

```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git mariadb-server mariadb-client

# Start MariaDB
sudo systemctl start mariadb
sudo systemctl enable mariadb

# Fedora/RHEL
sudo dnf install -y python3 python3-pip git mariadb-server mariadb
sudo systemctl start mariadb
sudo systemctl enable mariadb

# Arch Linux
sudo pacman -Syu python python-pip git mariadb
sudo systemctl start mariadb
sudo systemctl enable mariadb
```

### Step 2: Secure MariaDB (Recommended)

```bash
sudo mysql_secure_installation
```

### Step 3-8: Follow Termux Steps

The remaining steps are identical to Termux, except:
- Use `python3` instead of `python`
- Use `pip3` instead of `pip`
- You may need `sudo` for some commands

---

## Configuration

### Bot Configuration

Edit `config/config.json`:

```json
{
  "api": {
    "provider": "gemini",
    "gemini_model": "gemini-2.5-flash",
    "openai_model": "gpt-4o-mini"
  },
  "bot": {
    "names": ["sulfur", "bot"],
    "personality": "friendly and helpful"
  }
}
```

### System Prompt

Edit `config/system_prompt.txt` to customize the bot's personality.

---

## Running the Bot

### Starting the Bot

**Windows:**
```powershell
.\start.ps1
```

**Linux/Termux:**
```bash
./start.sh
```

### Monitoring

- **Web Dashboard:** http://localhost:5000
- **Logs:** Check `logs/` directory
- **Status:** Check `config/bot_status.json`

### Control Flags

Create these files to control the bot:

- **Restart:** `echo $null > restart.flag` (Windows) or `touch restart.flag` (Linux)
- **Stop:** `echo $null > stop.flag` (Windows) or `touch stop.flag` (Linux)

Or press `Q` in the maintenance console to gracefully shutdown.

---

## Troubleshooting

### Database Connection Failed

**Error:** `Access denied for user 'sulfur_bot_user'@'localhost'`

**Solution:**
1. Ensure MySQL is running: `Get-Process mysqld` (Windows) or `pgrep mysqld` (Linux)
2. Re-run setup script: `.\setup_mysql.ps1` or `bash setup_mysql.sh`
3. Manually create user:
   ```sql
   mysql -u root -p
   CREATE USER 'sulfur_bot_user'@'localhost' IDENTIFIED BY '';
   GRANT ALL PRIVILEGES ON sulfur_bot.* TO 'sulfur_bot_user'@'localhost';
   FLUSH PRIVILEGES;
   ```

### Discord Bot Not Responding

**Possible Causes:**
1. Invalid bot token
2. Bot not invited to server
3. Missing permissions

**Solution:**
1. Verify token in `.env` file
2. Invite bot with this URL (replace CLIENT_ID):
   ```
   https://discord.com/api/oauth2/authorize?client_id=CLIENT_ID&permissions=8&scope=bot%20applications.commands
   ```
3. Check bot has required permissions in Discord server settings

### API Errors

**Error:** `API key invalid`

**Solution:**
1. Verify API keys in `.env` file
2. Ensure no extra spaces or quotes
3. Check API key is valid on respective platform (Google AI Studio or OpenAI Platform)

### Port 5000 Already in Use

**Solution:**
Edit `web_dashboard.py` and change port:
```python
socketio.run(app, host='0.0.0.0', port=5001)  # Changed from 5000
```

### Script Execution Policy Error (Windows)

**Error:** `cannot be loaded because running scripts is disabled`

**Solution:**
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

### Permission Denied (Linux/Termux)

**Solution:**
```bash
chmod +x *.sh
chmod +x setup_mysql.sh start.sh maintain_bot.sh
```

### MySQL Not Found in Termux

**Solution:**
```bash
pkg install mariadb
mysql_install_db
mysqld_safe --datadir=$PREFIX/var/lib/mysql &
```

### Virtual Environment Issues

**Windows:**
```powershell
python -m venv venv --clear
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Linux/Termux:**
```bash
python3 -m venv venv --clear
source venv/bin/activate
pip install -r requirements.txt
```

---

## Quick Reference

### Windows Commands
```powershell
# Setup
.\setup_mysql.ps1
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python test_setup.py

# Run
.\start.ps1

# Control
echo $null > restart.flag  # Restart bot
echo $null > stop.flag     # Stop bot
```

### Linux/Termux Commands
```bash
# Setup
bash setup_mysql.sh
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python test_setup.py

# Run
bash start.sh

# Control
touch restart.flag  # Restart bot
touch stop.flag     # Stop bot
```

---

## Getting Help

1. Check logs in `logs/` directory
2. Run `python test_setup.py` to diagnose issues
3. Visit web dashboard at http://localhost:5000
4. Check [GitHub Issues](https://github.com/mereMint/sulfur/issues)
5. Read project documentation in `docs/` directory

---

## Next Steps

After setup:
1. Customize bot personality in `config/system_prompt.txt`
2. Configure features in `config/config.json`
3. Invite bot to your Discord server
4. Monitor via web dashboard at http://localhost:5000
5. Check `TODO.md` for planned features

---

**Happy botting! 🎉**
