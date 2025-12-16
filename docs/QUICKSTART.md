# 🚀 Quick Start Guide

Get Sulfur Bot running in under 5 minutes!

---

## Prerequisites

> **⚠️ This is a private repository** - You need SSH key or GitHub token to clone it.

### Setup GitHub Authentication

Choose one method:

#### Option 1: SSH Key (Recommended)

```bash
# 1. Generate SSH key
ssh-keygen -t ed25519 -C "your_email@example.com"

# 2. Start SSH agent and add key
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519

# 3. Copy public key
cat ~/.ssh/id_ed25519.pub

# 4. Add to GitHub: https://github.com/settings/keys
# 5. Test connection
ssh -T git@github.com
```

#### Option 2: Personal Access Token

1. Generate token at: https://github.com/settings/tokens
2. Select scope: `repo` (full control of private repositories)
3. Use when cloning or configure credential helper

---

## Quick Install

### Step 1: Clone Repository

**With SSH (recommended):**
```bash
git clone git@github.com:mereMint/sulfur.git
cd sulfur
```

**With HTTPS:**
```bash
git clone https://github.com/mereMint/sulfur.git
cd sulfur
# You'll be prompted for username and token/password
```

### Step 2: Run Quick Installer

**Linux / macOS / Termux:**
```bash
bash scripts/quickinstall.sh
```

**Windows (PowerShell as Administrator):**
```powershell
.\scripts\quickinstall.ps1
```

The quick installer will automatically:
- ✅ Install all dependencies
- ✅ Set up Python environment
- ✅ Configure the database
- ✅ Run the interactive setup wizard

---

## Alternative: Manual Setup

If you prefer to run platform-specific installers:

**Linux:**
```bash
./scripts/install_linux.sh
```

**Windows:**
```powershell
.\scripts\install_windows.ps1
```

**Termux:**
```bash
./scripts/install_termux.sh
```

### Step 3: Configure

Create a `.env` file:
```bash
cp .env.example .env
nano .env  # or notepad .env on Windows
```

Add your credentials:
```env
DISCORD_BOT_TOKEN=your_token_here
DB_HOST=localhost
DB_USER=sulfur_bot_user
DB_PASS=your_password
DB_NAME=sulfur_bot
GEMINI_API_KEY=your_gemini_key
```

### Step 4: Run Setup Wizard

```bash
source venv/bin/activate  # Windows: .\venv\Scripts\Activate.ps1
python master_setup.py
```

### Step 5: Start the Bot

```bash
python bot.py
```

---

## Getting Required Credentials

### Discord Bot Token

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Go to "Bot" section
4. Click "Add Bot"
5. Copy the token
6. Enable these intents:
   - ✅ Presence Intent
   - ✅ Server Members Intent
   - ✅ Message Content Intent

### Invite Bot to Server

Replace `YOUR_CLIENT_ID`:
```
https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=8&scope=bot%20applications.commands
```

### Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create API key
3. Copy to `.env`

---

## Verify Installation

1. **Bot is online?** Check Discord for green status
2. **Dashboard works?** Visit http://localhost:5000
3. **Commands work?** Try `/help` in Discord

---

## Next Steps

- 📖 Read the [full documentation](../README.md)
- 🔐 Set up [VPN access](VPN_GUIDE.md)
- 🎮 Configure [Minecraft server](MINECRAFT.md)
- 🎵 Explore [Music Player](MUSIC_PLAYER.md)

---

## Common Issues

### "Token is invalid"
- Regenerate token in Discord Developer Portal
- Make sure no extra spaces in `.env`

### "Cannot connect to database"
- Start MySQL: `sudo systemctl start mysql`
- Termux: `mysqld_safe &`

### "Module not found"
- Activate venv: `source venv/bin/activate`
- Install deps: `pip install -r requirements.txt`

---

## Support

- 📚 [Full Wiki](WIKI.md)
- 🔧 [Troubleshooting](TROUBLESHOOTING.md)
- ❓ [FAQ](FAQ.md)
- 🐛 [Report Issues](https://github.com/mereMint/sulfur/issues)
