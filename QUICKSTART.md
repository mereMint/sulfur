# 🚀 Quick Start Guide

> **⚠️ IMPORTANT:** This bot requires `discord.py` (NOT `py-cord`). The installation scripts will install the correct version automatically from `requirements.txt`.

Get your Sulfur Discord Bot running in minutes! Choose your platform below.

---

## 📋 Before You Start

You'll need these credentials (get them while the bot installs):

1. **Discord Bot Token**
   - Visit [Discord Developer Portal](https://discord.com/developers/applications)
   - Create app → Bot → Copy token
   - ⚠️ Enable all 3 Privileged Gateway Intents

2. **AI API Key** (pick one or both)
   - **Gemini** (Free tier): [Google AI Studio](https://aistudio.google.com/apikey)
   - **OpenAI** (Paid): [OpenAI Platform](https://platform.openai.com/api-keys)

---

## 🗺️ Choose Your Installation Path

```
┌─────────────────────────────────────────────────────────┐
│         What platform are you using?                     │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  🪟 Windows        🐧 Linux         📱 Android/Termux   │
│     ↓                  ↓                    ↓             │
│  Use Wizard        Quick Setup         One Command       │
│  (Easiest!)        Script              Install           │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

---

## 🪟 Windows - Automated Wizard (Recommended)

**Perfect for beginners!** Everything is automated.

### Step 1: Get the Code
```powershell
# Open PowerShell and run:
git clone https://github.com/mereMint/sulfur.git
cd sulfur
```

### Step 2: Run the Installation Wizard
**Choose one method:**
- **Easiest**: Double-click `INSTALL.bat`
- **PowerShell**: Run `.\install_wizard.ps1`

### Step 3: Follow the Wizard
The wizard will automatically:
- ✅ Check & install prerequisites (Python, Git, MySQL)
- ✅ Help you obtain API keys with direct links
- ✅ Configure your .env file interactively
- ✅ Set up database (creates DB, user, tables)
- ✅ Install Python dependencies
- ✅ Test everything to ensure it works
- ✅ Create desktop shortcuts for easy access

### Step 4: You're Done! 🎉
- Bot starts automatically or use desktop shortcut
- Dashboard: http://localhost:5000
- See [INSTALL_WINDOWS.md](INSTALL_WINDOWS.md) for troubleshooting

**Total time:** 5-10 minutes (depending on download speed)

---

## 🐧 Linux - Quick Setup Script

**Fast automated setup for Linux users.**

### One-Command Install
```bash
# Clone and run setup
git clone https://github.com/mereMint/sulfur.git
cd sulfur
chmod +x quick_setup.sh
./quick_setup.sh
```

The script handles:
- ✅ Prerequisite checking
- ✅ Database setup
- ✅ Dependency installation
- ✅ Interactive configuration

**Start the bot:**
```bash
./start.sh
```

**Dashboard:** http://localhost:5000

---

## 📱 Android/Termux - One Command Install

**The easiest way to run on Android!**

### Single Command Setup
```bash
pkg update && pkg install -y git && \
git clone https://github.com/mereMint/sulfur.git sulfur && \
cd sulfur && bash termux_quickstart.sh
```

**What this does:**
- ✅ Installs all packages (Python, MariaDB, Git)
- ✅ Sets up and starts database
- ✅ Configures SSH keys (optional)
- ✅ Creates virtual environment
- ✅ Installs dependencies
- ✅ Walks you through .env setup
- ✅ Verifies complete installation

**Start the bot:**
```bash
./start_sulfur.sh
```

**Dashboard:**
- From Android: http://localhost:5000
- From other devices: http://YOUR_ANDROID_IP:5000

**Run in background:**
```bash
pkg install tmux
tmux new -s sulfur
./start_sulfur.sh
# Detach: Ctrl+B then D
# Reattach: tmux attach -t sulfur
```

---

## ⚡ What You Get

After installation, your bot includes:

### 🎮 Games & Fun
- 🐺 Werwolf multiplayer game
- 🃏 Blackjack, 🎰 Roulette, 💣 Mines, 🔫 Russian Roulette
- 📋 Daily quests with rewards

### 💰 Economy System
- Virtual currency and daily rewards
- Color role shop (Basic/Premium/Legendary)
- Feature unlocks and leaderboards

### 🤖 AI Features
- Multi-model support (Gemini, OpenAI, GPT-5)
- Image analysis (AI vision)
- Smart conversation with context memory
- Custom emoji descriptions

### 📊 Management
- Web dashboard at http://localhost:5000
- AI usage tracking & cost monitoring
- Auto-backups every 30 minutes
- Auto-updates & self-healing

---

## 🎯 First Steps After Installation

1. **Invite Bot to Your Server**
   ```
   https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=8&scope=bot%20applications.commands
   ```
   Get YOUR_CLIENT_ID from Discord Developer Portal

2. **Try Some Commands**
   - `/help` - See all commands
   - `/balance` - Check your coins
   - `/quests` - View daily quests
   - `/shop` - Browse the shop

3. **Customize Your Bot**
   - Edit `config/system_prompt.txt` for personality
   - Edit `config/config.json` for settings
   - Visit http://localhost:5000 for web dashboard

4. **Monitor Your Bot**
   - Check logs in `logs/` folder
   - Use web dashboard for real-time stats
   - View AI usage at http://localhost:5000/ai_dashboard

---

## 🆘 Quick Troubleshooting

### Bot Won't Start

**"MySQL connection failed"**
```bash
# Windows: Check Services → MySQL → Start
# Linux: sudo systemctl start mariadb
# Termux: mariadbd-safe --datadir=$PREFIX/var/lib/mysql &
```

**"Invalid Discord token"**
- Check `.env` file for correct token
- No extra spaces or quotes
- Regenerate token if needed

**"Module not found"**
```bash
# Windows
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Linux/Termux
source venv/bin/activate
pip install -r requirements.txt
```

### Dashboard Won't Load

**Port 5000 in use:**
```bash
# Check what's using it
# Windows: netstat -ano | findstr :5000
# Linux: lsof -i :5000

# Change port in web_dashboard.py if needed
```

### Permission Issues (Linux/Termux)
```bash
chmod +x *.sh
```

---

## 📚 Additional Resources

- **Full Installation Guides:**
  - [Windows Detailed Guide](INSTALL_WINDOWS.md)
  - [Termux Guide](TERMUX_GUIDE.md)
  - [Main README](README.md)

- **Configuration:**
  - [Setup Guide](SETUP_GUIDE.md)

- **Features & Roadmap:**
  - [TODO List](TODO.md)
  - [Changelog](CHANGELOG.md)

- **Support:**
  - Check GitHub Issues
  - Read troubleshooting sections
  - Review log files in `logs/`

---

## 🎨 Customization Quick Tips

**Change Bot Personality:**
```bash
# Edit system prompt
nano config/system_prompt.txt  # Linux/Termux
notepad config\system_prompt.txt  # Windows
```

**Change AI Model:**
```json
// Edit config/config.json
{
  "api": {
    "provider": "gemini",  // or "openai"
    "gemini_model": "gemini-2.5-flash",
    "openai_model": "gpt-4o"
  }
}
```

**Enable/Disable Features:**
Edit `config/config.json` and adjust feature flags.

---

## 🔄 Keeping Your Bot Updated

The bot updates automatically every minute when running with the maintenance script!

**Manual update:**
```bash
git pull
pip install -r requirements.txt
```

**Database migrations:**
```bash
# Check scripts/db_migrations/ for new migrations
mysql -u sulfur_bot_user -p sulfur_bot < scripts/db_migrations/XXX_migration.sql
```

---

**Happy Botting! 🤖✨**

*Installation takes 5-15 minutes depending on your internet speed and platform.*
