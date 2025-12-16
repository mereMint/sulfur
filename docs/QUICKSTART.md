# 🚀 Quick Start Guide

Get Sulfur Bot running in under 5 minutes!

---

## One-Command Install

### Linux / macOS / Termux
```bash
curl -sSL https://raw.githubusercontent.com/mereMint/sulfur/main/scripts/quickinstall.sh | bash
```

### Windows (PowerShell as Administrator)
```powershell
irm https://raw.githubusercontent.com/mereMint/sulfur/main/scripts/quickinstall.ps1 | iex
```

---

## Manual Quick Start

### Step 1: Clone Repository

```bash
git clone https://github.com/mereMint/sulfur.git
cd sulfur
```

### Step 2: Run Platform Installer

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
