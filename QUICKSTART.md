# 🚀 Quick Start Guide

Choose your platform and get started in minutes!

---

## 🪟 Windows - Automated Setup (Easiest)

### Option 1: One-Click Setup
1. **Right-click** `quick_setup.ps1` → **Run with PowerShell**
2. Follow the wizard prompts
3. Done! 🎉

### Option 2: Manual Setup
```powershell
# 1. Setup database
.\setup_mysql.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Test setup
python test_setup.py

# 4. Start bot
.\start.ps1
# Or double-click: start.bat
```

---

## 🐧 Linux/Termux - Automated Setup (Easiest)

### Option 1: One-Command Setup
```bash
chmod +x quick_setup.sh
bash quick_setup.sh
```

### Option 2: Manual Setup
```bash
# 1. Setup database
chmod +x setup_mysql.sh
bash setup_mysql.sh

# 2. Install dependencies
pip install -r requirements.txt

# 3. Test setup
python test_setup.py

# 4. Start bot
chmod +x start.sh
bash start.sh
```

---

## 📋 Prerequisites

Before running setup, you need:

### Windows
- **Python 3.8+** from [python.org](https://www.python.org/downloads/) ✅ Check "Add to PATH"
- **XAMPP** from [apachefriends.org](https://www.apachefriends.org/) (for MySQL)
- **Git** from [git-scm.com](https://git-scm.com/download/win)

### Linux
```bash
sudo apt update
sudo apt install python3 python3-pip git mariadb-server
sudo systemctl start mariadb
```

### Termux
```bash
pkg update && pkg upgrade
pkg install python git mariadb
mysql_install_db
mysqld_safe --datadir=$PREFIX/var/lib/mysql &
```

---

## 🔑 Required Credentials

You'll be prompted for these during setup:

### 1. Discord Bot Token
- Go to https://discord.com/developers/applications
- Click "New Application" → "Bot" → "Add Bot"
- Copy token
- Enable all 3 Privileged Gateway Intents

### 2. AI API Key (Choose One or Both)
**Gemini (Recommended - Free):**
- Go to https://aistudio.google.com/
- Click "Get API key" → Create new key
- Copy key

**OpenAI (Optional - Paid):**
- Go to https://platform.openai.com/
- Create account → API Keys → Create new secret key
- Copy key

---

## 📝 Manual Configuration

If you prefer to edit `.env` manually:

```env
DISCORD_BOT_TOKEN="your_token_here"
GEMINI_API_KEY="your_gemini_key_here"
DB_HOST="localhost"
DB_USER="sulfur_bot_user"
DB_PASS=""
DB_NAME="sulfur_bot"
```

---

## ✅ Verify Setup

Run the test script:
```bash
python test_setup.py
```

This checks:
- ✓ Environment variables
- ✓ Configuration files
- ✓ Database connection
- ✓ API connectivity

---

## 🚀 Running the Bot

### Windows
- **Double-click** `start.bat`
- Or run `.\start.ps1` in PowerShell

### Linux/Termux
```bash
./start.sh
```

The bot will:
- ✓ Auto-restart on crashes
- ✓ Check for updates every minute
- ✓ Auto-backup database every 30 minutes
- ✓ Auto-commit changes every 5 minutes
- ✓ Start web dashboard at http://localhost:5000

---

## 🌐 Web Dashboard

Access at: **http://localhost:5000**

Features:
- Live logs
- AI usage statistics
- Database viewer
- Configuration editor

---

## 📱 Termux-Specific Tips

### Background Execution
Use `tmux` to keep bot running:
```bash
pkg install tmux
tmux new -s sulfur
bash start.sh
# Detach: Ctrl+B then D
# Reattach: tmux attach -t sulfur
```

### Access Dashboard
- **From Android**: http://localhost:5000
- **From other devices**: http://YOUR_ANDROID_IP:5000

### Keep MariaDB Running
```bash
# Check status
pgrep mysqld

# Restart if needed
mysqld_safe --datadir=$PREFIX/var/lib/mysql &
```

---

## 🎮 Invite Bot to Discord Server

1. Get your Application ID from https://discord.com/developers/applications
2. Replace `YOUR_CLIENT_ID` in this URL:
   ```
   https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=8&scope=bot%20applications.commands
   ```
3. Open the URL and select your server

---

## 🔧 Control Commands

### Windows PowerShell
```powershell
# Restart bot
echo $null > restart.flag

# Stop bot
echo $null > stop.flag

# Or press 'Q' in maintenance console
```

### Linux/Termux
```bash
# Restart bot
touch restart.flag

# Stop bot
touch stop.flag

# Or press Ctrl+C in console
```

---

## 🆘 Common Issues

### "MySQL/MariaDB not running"
**Windows**: Start MySQL via XAMPP Control Panel  
**Linux**: `sudo systemctl start mariadb`  
**Termux**: `mysqld_safe --datadir=$PREFIX/var/lib/mysql &`

### "DISCORD_BOT_TOKEN not set"
Edit `.env` file and add your Discord bot token (no extra quotes/spaces)

### "Script execution policy error" (Windows)
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

### "Permission denied" (Linux/Termux)
```bash
chmod +x *.sh
```

### "Module not found"
Activate virtual environment:
- **Windows**: `.\venv\Scripts\Activate.ps1`
- **Linux/Termux**: `source venv/bin/activate`

### Bot stops when terminal closes (Termux)
Use `tmux` (see Termux-Specific Tips above)

---

## 📚 Next Steps

1. Customize bot personality: `config/system_prompt.txt`
2. Configure settings: `config/config.json`
3. Try commands: `!help` in Discord
4. Check AI usage: http://localhost:5000/ai_dashboard
5. Read full setup guide: `SETUP_GUIDE.md`
6. Explore features: `README.md`
7. Check planned features: `TODO.md`

---

## 🔗 Useful Links

- **Full Setup Guide**: `SETUP_GUIDE.md`
- **Troubleshooting**: `SETUP_GUIDE.md#troubleshooting`
- **Project Structure**: `PROJECT_STRUCTURE.md`
- **Discord Developer Portal**: https://discord.com/developers/applications
- **Google AI Studio**: https://aistudio.google.com/

---

**Happy botting! 🤖✨**

*Need help? Check `SETUP_GUIDE.md` or create an issue on GitHub!*
