# 🪟 Windows Installation Guide - Sulfur Discord Bot

## ⚡ Quick Start (Recommended)

The easiest way to install Sulfur Bot on Windows is using the **Installation Wizard**:

### Option 1: Double-Click Install (Easiest!)

1. **Download** or clone this repository
2. **Double-click** `INSTALL.bat` in the folder
3. **Follow the wizard** - it will guide you through everything!

### Option 2: PowerShell Install

1. Open PowerShell in the bot folder (Shift + Right-click → "Open PowerShell window here")
2. Run:
   ```powershell
   .\install_wizard.ps1
   ```
3. Follow the interactive prompts

---

## 🎯 What the Wizard Does

The installation wizard automates the entire setup process:

### ✓ Step 1: Prerequisite Check
- Detects **Python 3.8+** installation
- Verifies **Git** is installed
- Checks for **MySQL/MariaDB**
- Provides download links if anything is missing
- Offers to start MySQL if it's installed but not running

### ✓ Step 2: Bot Configuration
- Creates `.env` configuration file
- Walks you through getting:
  - Discord Bot Token (with links to developer portal)
  - Gemini API Key (free tier available)
  - OpenAI API Key (optional, paid)
- Sets up database credentials
- Configures bot prefix and owner ID

### ✓ Step 3: Database Setup
- Runs the MySQL setup wizard
- Creates database and user
- Applies migrations
- Tests database connectivity

### ✓ Step 4: Dependency Installation
- Creates Python virtual environment
- Installs all required packages
- Upgrades pip
- Verifies installation

### ✓ Step 5: Setup Testing
- Runs comprehensive setup verification
- Tests database connection
- Validates API keys
- Checks configuration files

### ✓ Step 6: Shortcuts & Convenience
- Creates desktop shortcuts:
  - "Start Sulfur Bot" - Launch the bot
  - "Sulfur Web Dashboard" - Open dashboard in browser
  - "Sulfur Bot Folder" - Quick access to installation
- Offers to start the bot immediately

---

## 📋 Prerequisites

Before running the wizard, you should have:

### Required
- **Windows 10 or 11** (64-bit recommended)
- **Internet connection** (for downloading dependencies and API access)

### The Wizard Will Help Install
- **Python 3.8+** - [Download](https://www.python.org/downloads/)
  - ⚠️ **Important**: Check "Add Python to PATH" during installation!
- **Git** - [Download](https://git-scm.com/download/win)
- **MySQL/MariaDB** - Choose one:
  - [XAMPP](https://www.apachefriends.org/) (Easiest - includes MySQL)
  - [MySQL Server](https://dev.mysql.com/downloads/installer/)
  - [MariaDB](https://mariadb.org/download/)

### You'll Need to Obtain
- **Discord Bot Token** - [Get it here](https://discord.com/developers/applications)
- **Gemini API Key** (free tier available) - [Get it here](https://aistudio.google.com/apikey)
- **OpenAI API Key** (optional, paid) - [Get it here](https://platform.openai.com/api-keys)

---

## 🎮 Getting Your Bot Token & API Keys

### Discord Bot Token

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **"New Application"** or select existing one
3. Go to **"Bot"** section in the sidebar
4. Click **"Reset Token"** → Copy the token
5. ⚠️ **Important**: Enable these **Privileged Gateway Intents**:
   - ✅ Message Content Intent
   - ✅ Server Members Intent
   - ✅ Presence Intent

### Gemini API Key (Free Tier Available)

1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Sign in with your Google account
3. Click **"Create API Key"**
4. Copy the key

**Benefits:**
- Free tier with generous limits
- Latest AI models (Gemini 2.0, 2.5-flash)
- Vision capabilities included

### OpenAI API Key (Optional)

1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Sign in or create an account
3. Click **"Create new secret key"**
4. Copy the key
5. ⚠️ Add payment method (required for API access)

**Note:** At least one AI API key (Gemini or OpenAI) is required.

---

## 🚀 Using the Installation Wizard

### Interactive Prompts

The wizard uses color-coded messages:

- 🟦 **Blue Headers** - Section titles
- 🟩 **Green ✓** - Success messages
- 🟨 **Yellow ⚠** - Warnings (usually okay to continue)
- 🟥 **Red ✗** - Errors (need attention)
- ⬜ **White ℹ** - Information

### Example Walkthrough

```
╔════════════════════════════════════════════════════════════╗
║  Welcome to Sulfur Discord Bot Setup Wizard                ║
╚════════════════════════════════════════════════════════════╝

This wizard will guide you through setting up the Sulfur Discord Bot.
The process includes:

  1. Checking and installing prerequisites
  2. Configuring your bot settings
  3. Setting up the database
  4. Installing dependencies
  5. Testing the setup
  6. Creating shortcuts for easy access

Estimated time: 10-15 minutes (depending on download speeds)

Ready to begin? [Y/n]: y

▶ Checking Python...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✓ Python 3.11 detected - Compatible

▶ Checking Git...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✓ Git detected - git version 2.42.0

...
```

### Wizard Commands

During setup, you'll answer questions like:

- **Y/n** - Yes is default (press Enter or type Y)
- **y/N** - No is default (type Y to confirm)
- Text input - Type your answer and press Enter

### Skipping Steps

You can skip certain steps if needed:

```powershell
# Skip prerequisite checks (if you know they're met)
.\install_wizard.ps1 -SkipPrerequisites

# Skip database setup (if already configured)
.\install_wizard.ps1 -SkipDatabase

# Skip dependency installation (if already installed)
.\install_wizard.ps1 -SkipDependencies

# Combine multiple skips
.\install_wizard.ps1 -SkipPrerequisites -SkipDependencies
```

---

## 🔧 Manual Installation (Advanced)

If you prefer manual setup or the wizard encounters issues:

### 1. Install Prerequisites

Download and install:
- Python 3.8+ (check "Add to PATH")
- Git
- MySQL/MariaDB or XAMPP

### 2. Clone Repository

```powershell
git clone https://github.com/mereMint/sulfur.git
cd sulfur
```

### 3. Configure Environment

Copy `.env.example` to `.env` and edit:

```powershell
Copy-Item .env.example .env
notepad .env
```

Fill in your tokens and keys.

### 4. Setup Database

```powershell
# Start MySQL (if using XAMPP, start from control panel)

# Run setup wizard
python setup_wizard.py

# Apply migrations
python apply_migration.py
```

### 5. Install Dependencies

```powershell
# Create virtual environment
python -m venv venv

# Activate it
.\venv\Scripts\Activate.ps1

# Install packages
pip install -r requirements.txt
```

### 6. Test Setup

```powershell
python test_setup.py
```

### 7. Start Bot

```powershell
.\start.ps1
```

---

## 🆘 Troubleshooting

### "Python not found"

**Solution:**
1. Download Python from [python.org](https://www.python.org/downloads/)
2. During installation, **check "Add Python to PATH"**
3. Restart your terminal/PowerShell
4. Run the wizard again

### "MySQL connection failed"

**Solutions:**
1. **Check if MySQL is running:**
   - XAMPP: Open control panel, click "Start" next to MySQL
   - Service: Run `services.msc` → Find MySQL → Start
   
2. **Verify credentials:**
   - Default user: `sulfur_bot_user`
   - Default password: (empty)
   - Default database: `sulfur_bot`

3. **Reset database:**
   ```powershell
   python setup_wizard.py
   ```

### "Cannot run scripts" (Execution Policy Error)

**Solution:**
```powershell
# Open PowerShell as Administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Or run with bypass flag:
powershell -ExecutionPolicy Bypass -File .\install_wizard.ps1
```

### "Git not recognized"

**Solution:**
1. Install Git from [git-scm.com](https://git-scm.com/download/win)
2. Use default settings during installation
3. Restart your terminal
4. Run the wizard again

### "Port 5000 already in use"

**Solution:**
1. Find what's using port 5000:
   ```powershell
   netstat -ano | findstr :5000
   ```
2. Kill the process or change the bot's port in `web_dashboard.py`

### Wizard crashes or freezes

**Solutions:**
1. Close and restart PowerShell
2. Try manual installation instead
3. Run with specific skips:
   ```powershell
   .\install_wizard.ps1 -SkipPrerequisites
   ```

---

## 📝 After Installation

### Starting the Bot

**Desktop Shortcut:**
- Double-click "Start Sulfur Bot" on your desktop

**Manual Start:**
```powershell
.\start.ps1
```

**Alternative:**
```powershell
.\start.bat
```

### Accessing Web Dashboard

Once the bot is running:
- Click "Sulfur Web Dashboard" shortcut, or
- Open browser to: http://localhost:5000

### Inviting to Discord Server

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Select your application
3. Go to **OAuth2** → **URL Generator**
4. Select scopes: **bot**, **applications.commands**
5. Select permissions: **Administrator** (or specific ones)
6. Copy the generated URL and open it in your browser
7. Select your server and authorize

### Customizing the Bot

**Bot Personality:**
- Edit `config\system_prompt.txt`

**Bot Settings:**
- Edit `config\config.json`

**Environment Variables:**
- Edit `.env` file

### Updating the Bot

The maintenance system auto-updates, or manually:
```powershell
git pull
pip install -r requirements.txt
```

---

## 🎓 Additional Resources

### Documentation
- **Main README:** [README.md](README.md)
- **Setup Guide:** [SETUP.md](SETUP.md)
- **Quick Start:** [QUICKSTART.md](QUICKSTART.md)
- **Troubleshooting:** Main README troubleshooting section

### Support
- **GitHub Issues:** Report bugs or request features
- **Discord:** (Add your Discord server link)

### Advanced Topics
- **Termux Installation:** [TERMUX_GUIDE.md](TERMUX_GUIDE.md)
- **Linux Installation:** See README.md
- **Database Migrations:** `scripts/db_migrations/`
- **Configuration Reference:** [docs/CONFIG_DOCUMENTATION.md](docs/CONFIG_DOCUMENTATION.md)

---

## ✅ Installation Checklist

Use this to track your progress:

- [ ] Downloaded/cloned repository
- [ ] Installed Python 3.8+
- [ ] Installed Git
- [ ] Installed MySQL/MariaDB or XAMPP
- [ ] Obtained Discord Bot Token
- [ ] Obtained Gemini or OpenAI API Key
- [ ] Ran installation wizard (INSTALL.bat)
- [ ] Configured .env file
- [ ] Set up database
- [ ] Installed dependencies
- [ ] Tested setup (all checks passed)
- [ ] Created desktop shortcuts
- [ ] Started the bot successfully
- [ ] Invited bot to Discord server
- [ ] Verified bot is online in server
- [ ] Accessed web dashboard
- [ ] Customized bot personality (optional)

---

## 🎉 You're All Set!

Your Sulfur Discord Bot is now installed and ready to use!

**Quick Commands:**
- Start bot: Double-click desktop shortcut or run `.\start.ps1`
- View dashboard: http://localhost:5000
- Check logs: Look in `logs/` folder
- Stop bot: Press Q in maintenance window or create `stop.flag` file

**Need Help?**
- Check [troubleshooting section](#-troubleshooting)
- Review [main README](README.md)
- Open a GitHub issue

Enjoy your bot! 🤖✨
