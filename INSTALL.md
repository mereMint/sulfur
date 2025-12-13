# 📦 Installation Guide - Sulfur Discord Bot

> **⚠️ IMPORTANT:** This bot uses `discord.py`, NOT `py-cord`. If you have `py-cord` installed, you must uninstall it first. See [PYCORD_MIGRATION_GUIDE.md](PYCORD_MIGRATION_GUIDE.md) for details.

Choose your platform and follow the easiest installation method for you!

---

## 🗺️ Quick Navigation

| Platform | Easiest Method | Time Required |
|----------|----------------|---------------|
| 🪟 **Windows** | Installation Wizard | 5-10 minutes |
| 🐧 **Linux** | Quick Setup Script | 5-10 minutes |
| 📱 **Android/Termux** | One-Command Install | 10-15 minutes |

---

## 🪟 Windows Installation

### Method 1: Automated Wizard (Recommended ⭐)

**Best for beginners!** Handles everything automatically.

1. **Clone the repository:**
   ```powershell
   git clone https://github.com/mereMint/sulfur.git
   cd sulfur
   ```

2. **Run the wizard:**
   - Double-click `INSTALL.bat`, **OR**
   - Run in PowerShell: `.\install_wizard.ps1`

3. **Follow the prompts**

The wizard will:
- ✅ Check & install prerequisites
- ✅ Guide you through API key setup
- ✅ Configure everything automatically
- ✅ Test your installation
- ✅ Create desktop shortcuts

**📖 Detailed Guide:** [INSTALL_WINDOWS.md](INSTALL_WINDOWS.md)

### Method 2: Manual Installation

For advanced users who prefer manual configuration.

**📖 See:** [SETUP_GUIDE.md - Windows Setup](SETUP_GUIDE.md#windows-setup)

---

## 🐧 Linux Installation

### Method 1: Quick Setup Script (Recommended ⭐)

```bash
git clone https://github.com/mereMint/sulfur.git
cd sulfur
chmod +x quick_setup.sh
./quick_setup.sh
```

The script handles prerequisites, database setup, and configuration.

### Method 2: Manual Installation

For advanced users who prefer step-by-step configuration.

**📖 See:** [SETUP_GUIDE.md - Linux Setup](SETUP_GUIDE.md#linux-setup)

---

## 📱 Android/Termux Installation

### Method 1: One-Command Install (Recommended ⭐)

```bash
pkg update && pkg install -y git && \
git clone https://github.com/mereMint/sulfur.git sulfur && \
cd sulfur && bash termux_quickstart.sh
```

This automated script:
- ✅ Installs all packages (Python, MariaDB, Git)
- ✅ Sets up database
- ✅ Configures environment
- ✅ Installs dependencies
- ✅ Verifies installation

**📖 Detailed Guide:** [TERMUX_GUIDE.md](TERMUX_GUIDE.md)

### Method 2: Manual Installation

**📖 See:** [SETUP_GUIDE.md - Termux Setup](SETUP_GUIDE.md#termux-setup)

---

## 📋 Before You Install

You'll need these credentials (get them during installation):

### 1. Discord Bot Token
- Visit: [Discord Developer Portal](https://discord.com/developers/applications)
- Create Application → Bot → Copy Token
- ⚠️ **Important:** Enable all 3 Privileged Gateway Intents

### 2. AI API Key (Choose One or Both)

**Gemini (Free Tier Available):**
- Visit: [Google AI Studio](https://aistudio.google.com/apikey)
- Create API Key → Copy

**OpenAI (Paid Service):**
- Visit: [OpenAI Platform](https://platform.openai.com/api-keys)
- Create Secret Key → Copy

---

## 🎁 What You Get After Installation

### 🎮 Games & Entertainment
- 🐺 **Werwolf** - Multiplayer game with voice channels
- 🃏 **Casino Games** - Blackjack, Roulette, Russian Roulette, Mines
- 📋 **Daily Quests** - Complete challenges for rewards

### 💰 Economy & Rewards
- Virtual currency system
- Shop with color roles (Basic/Premium/Legendary)
- Daily rewards and leaderboards
- Feature unlocks

### 🤖 AI Capabilities
- Multi-model support (Gemini, OpenAI, GPT-5)
- Image analysis and vision
- Conversation context memory
- Smart emoji descriptions

### 📊 Management Tools
- Web dashboard (http://localhost:5000)
- AI usage tracking and cost monitoring
- Auto-backups every 30 minutes
- Auto-updates every minute
- Transaction logging

---

## 🚀 After Installation

### Start the Bot

**Windows:**
```powershell
.\start.ps1
# Or double-click: start.bat
```

**Linux:**
```bash
./start.sh
```

**Termux:**
```bash
./start_sulfur.sh

# For background operation:
tmux new -s sulfur
./start_sulfur.sh
# Detach: Ctrl+B then D
```

### Access Web Dashboard

Open your browser to: **http://localhost:5000**

Features:
- Live logs and monitoring
- AI usage statistics
- Database viewer
- Configuration editor

### Invite Bot to Server

1. Get your Client ID from [Discord Developer Portal](https://discord.com/developers/applications)
2. Use this URL (replace `YOUR_CLIENT_ID`):
   ```
   https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=8&scope=bot%20applications.commands
   ```

### Try Some Commands

- `/help` - See all commands
- `/balance` - Check your coins
- `/quests` - View daily quests
- `/shop` - Browse the shop
- `/blackjack` - Play blackjack
- Mention the bot to chat with AI!

---

## 🆘 Common Issues

### "MySQL connection failed"
**Fix:** Start MySQL/MariaDB
- Windows: XAMPP Control Panel → Start MySQL
- Linux: `sudo systemctl start mariadb`
- Termux: `mariadbd-safe --datadir=$PREFIX/var/lib/mysql &`

### "Discord token invalid"
**Fix:** Check `.env` file
- Ensure no extra spaces or quotes
- Regenerate token if needed

### "Module not found"
**Fix:** Activate virtual environment
```bash
# Windows
.\venv\Scripts\Activate.ps1

# Linux/Termux
source venv/bin/activate

# Then reinstall
pip install -r requirements.txt
```

### "Port 5000 in use"
**Fix:** Change port in `web_dashboard.py` or stop the conflicting process

### "Permission denied" (Linux/Termux)
**Fix:** Make scripts executable
```bash
chmod +x *.sh
```

**📖 More Troubleshooting:** See platform-specific guides linked above

---

## 📚 Additional Resources

### Documentation
- [README.md](README.md) - Complete feature overview
- [QUICKSTART.md](QUICKSTART.md) - Quick start guide
- [TODO.md](TODO.md) - Feature roadmap
- [CHANGELOG.md](CHANGELOG.md) - Recent changes

### Platform-Specific Guides
- [INSTALL_WINDOWS.md](INSTALL_WINDOWS.md) - Windows detailed guide
- [TERMUX_GUIDE.md](TERMUX_GUIDE.md) - Termux/Android guide
- [SETUP_GUIDE.md](SETUP_GUIDE.md) - Manual setup for all platforms

### Configuration
- [config/system_prompt.txt](config/system_prompt.txt) - Bot personality
- [config/config.json](config/config.json) - Bot settings

---

## 🎯 Next Steps

After installation:

1. ✅ Invite bot to your Discord server
2. ✅ Try basic commands (`/help`, `/balance`)
3. ✅ Customize bot personality in `config/system_prompt.txt`
4. ✅ Configure settings in `config/config.json`
5. ✅ Monitor via web dashboard
6. ✅ Check AI usage at http://localhost:5000/ai_dashboard
7. ✅ Read about planned features in [TODO.md](TODO.md)

---

**Made with ❤️ for the Discord community**

*Installation typically takes 5-15 minutes depending on your platform and internet speed.*
