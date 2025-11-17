# 🚀 Sulfur Bot - Quick Start Card

## Windows Installation (Easiest Method)

### 1️⃣ Download or Clone
```
git clone https://github.com/mereMint/sulfur.git
cd sulfur
```

### 2️⃣ Run Installation Wizard
**Double-click:** `INSTALL.bat`

**OR in PowerShell:**
```powershell
.\install_wizard.ps1
```

### 3️⃣ Follow the Wizard
The wizard will guide you through:
- ✅ Installing prerequisites
- ✅ Getting API keys
- ✅ Configuring settings
- ✅ Setting up database
- ✅ Installing dependencies
- ✅ Testing everything

### 4️⃣ Start the Bot
**Desktop shortcut:** "Start Sulfur Bot"

**OR manually:**
```powershell
.\start.ps1
```

---

## 📝 What You'll Need

### Required Before Starting
- **Discord Bot Token**
  - Get from: https://discord.com/developers/applications
  - Create app → Bot → Reset Token → Copy
  - Enable: Message Content, Server Members, Presence Intents

- **Gemini API Key** (Free tier available)
  - Get from: https://aistudio.google.com/apikey
  - Click "Create API Key" → Copy

- **OR OpenAI API Key** (Paid)
  - Get from: https://platform.openai.com/api-keys

### Installed by Wizard (if missing)
- Python 3.8+
- Git
- MySQL/MariaDB or XAMPP

---

## 🎯 Quick Commands

### Start Bot
```powershell
.\start.ps1
```

### View Dashboard
Open browser to: **http://localhost:5000**

### Stop Bot
Press **Q** in the bot window

### Update Bot
The bot auto-updates! Or manually:
```powershell
git pull
```

### Restart Bot
Create file: `restart.flag`

---

## 🆘 Common Issues

### "Python not found"
→ Install Python from python.org
→ Check "Add Python to PATH"!

### "MySQL connection failed"
→ Start MySQL (XAMPP Control Panel)
→ Or: Run `services.msc` → Start MySQL

### "Cannot run scripts"
→ Run as Administrator:
```powershell
Set-ExecutionPolicy RemoteSigned
```

### "Port 5000 in use"
→ Change port in web_dashboard.py
→ Or close other apps using port 5000

---

## 📚 Documentation

- **Detailed Guide:** INSTALL_WINDOWS.md
- **Full README:** README.md
- **Troubleshooting:** README.md → Troubleshooting section

---

## ⚡ Installation Wizard Features

✅ **Prerequisite Detection**
- Auto-detects Python, Git, MySQL
- Provides download links
- Starts MySQL if installed

✅ **Interactive Configuration**
- Walks through .env setup
- Opens API key pages
- Validates all inputs

✅ **Automated Setup**
- Creates virtual environment
- Installs dependencies
- Sets up database
- Runs migrations

✅ **Verification**
- Tests database connection
- Validates API keys
- Checks configuration

✅ **Convenience**
- Creates desktop shortcuts
- Offers to start bot immediately
- Color-coded feedback

---

## 🎮 After Installation

1. **Invite Bot to Server**
   - Discord Developer Portal
   - OAuth2 → URL Generator
   - Scopes: bot, applications.commands
   - Permissions: Administrator

2. **Customize Bot**
   - Edit: config\system_prompt.txt
   - Edit: config\config.json

3. **Monitor Bot**
   - Dashboard: http://localhost:5000
   - Logs: logs\ folder

---

## 💡 Pro Tips

- Use desktop shortcuts for easy access
- Web dashboard shows real-time logs
- Bot auto-updates every minute
- Database auto-backs up every 30 min
- Press Q to gracefully shutdown

---

**Made with ❤️ for the Discord community**

For more help, see INSTALL_WINDOWS.md or open an issue on GitHub!
