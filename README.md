# 🤖 Sulfur Discord Bot

A feature-rich Discord bot with AI capabilities, economy system, mini-games, and comprehensive management tools.

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![discord.py](https://img.shields.io/badge/discord.py-2.4+-blue.svg)](https://github.com/Rapptz/discord.py)

---

## ⚡ Highlights

- 🎮 **Complete Game Suite** - Werwolf, Blackjack, Roulette, Mines, Tower, Russian Roulette, Detective
- 💰 **Full Economy System** - Virtual currency, shop, daily rewards, quests, stock market
- 🤖 **Advanced AI** - Multi-model support (Gemini, OpenAI), vision capabilities
- 🎵 **Music & Sounds Player** - Stream lofi, ambient sounds, no-copyright music, and Spotify-based mixes
- 📊 **Web Dashboard** - Real-time monitoring, AI usage tracking, database management
- 🔧 **Zero Maintenance** - Auto-updates, auto-backups, self-healing scripts
- 📱 **Cross-Platform** - Windows, Linux, Android/Termux support

---

## 🎯 Commands

Use `/help` in Discord to see all available commands organized by category:
- 🎮 **Games** - Blackjack, Roulette, Mines, Tower, Detective, Russian Roulette, Trolly
- 💰 **Economy** - Daily rewards, Shop, Quests, Stock market, Transactions
- 📊 **Profile & Stats** - Profile, Leaderboards (Level, Money, Werwolf, Games), Summary, Spotify stats
- 🎭 **Werwolf** - Multiplayer werewolf game with voice channels
- 🎤 **Voice** - Join-to-create voice channels with custom settings
- 🎵 **Music & Sounds** - Stream lofi, ambient sounds, no-copyright music, and personalized Spotify mixes
- ⏱️ **Focus Timer** - Pomodoro and custom timers with activity monitoring
- ⚙️ **Other** - News, Privacy, Wrapped statistics

---

## 📋 Quick Start

### 🪟 Windows

1. Clone the repository:
   ```powershell
   git clone https://github.com/mereMint/sulfur.git
   cd sulfur
   ```

2. Install Python 3.8+ and MySQL

3. Install dependencies:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

4. Create `.env` file (see Configuration below)

5. Run the bot:
   ```powershell
   python bot.py
   ```

### 🐧 Linux

```bash
git clone https://github.com/mereMint/sulfur.git
cd sulfur
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Create .env file
python bot.py
```

### 📱 Termux/Android

```bash
pkg update && pkg install -y git python mysql
git clone https://github.com/mereMint/sulfur.git
cd sulfur
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Create .env file and start MySQL
python bot.py
```

---

## 🌟 Features

### 🎮 Games & Entertainment
- **Werwolf** - Multiplayer werewolf game with voice channels (Amor, Der Weiße, and classic roles)
- **Gambling** - Blackjack, Roulette, Mines, Tower of Treasure, Russian Roulette
- **Detective** - AI-generated murder mysteries with encrypted puzzles
- **Trolly** - Moral dilemma challenges
- **Daily Quests** - Earn rewards through activities

### 💰 Economy System
- **Virtual Currency** - Earn coins through activities and quests
- **Shop System** - Custom color roles, feature unlocks, purchase history
- **Stock Market** - Trade 10+ stocks with realistic price simulation
- **Daily Rewards** - Claim daily coins (resets every 24 hours)
- **Leaderboards** - Track top earners, active members, Werwolf champions, and most games played

### 🤖 AI Capabilities
- **Multi-Model Support** - Gemini and OpenAI models
- **AI Vision** - Image analysis and understanding
- **Conversation Context** - Natural follow-up conversations
- **Smart Emoji Analysis** - AI-powered custom emoji descriptions

### 🎵 Music & Sounds Player
- **Multiple Station Types** - Lofi beats, ambient sounds, no-copyright music
- **9+ Stations** - Rain, ocean, fireplace, coffee shop ambience, and more
- **Spotify Integration** - Personalized stations based on your listening history
- **Auto-Disconnect** - Bot automatically leaves when alone (after 2 minutes)
- **Ephemeral Controls** - Clean interface with private command responses
- **Focus Integration** - Perfect companion for focus timer sessions
- **Simple Commands** - Use `/music` for all audio needs

See [`docs/MUSIC_PLAYER.md`](docs/MUSIC_PLAYER.md) for detailed usage and features.

### ⏱️ Focus Timer
- **Pomodoro Presets** - Short, Long, Ultra, and Sprint sessions
- **Custom Duration** - Set your own focus time
- **Activity Monitoring** - Track distractions during focus sessions
- **Statistics** - View your focus history and success rate

### 📊 Management & Analytics
- **Web Dashboard** - Real-time bot monitoring at http://localhost:5000
- **AI Usage Tracking** - Monitor token usage and costs
- **Transaction Logging** - Full audit trail for economy operations
- **Wrapped Statistics** - Discord Wrapped-style yearly summaries
- **Level System** - XP tracking and automatic role assignment

---

## 📦 Prerequisites

- **Python** 3.8 or higher
- **MySQL/MariaDB** - Latest stable version
- **Discord Bot Token** - From [Discord Developer Portal](https://discord.com/developers/applications)
- **API Keys** - Google Gemini API key (OpenAI optional)
- **FFmpeg** - For voice/music features (optional)

---

## ⚙️ Configuration

### Discord Bot Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a "New Application"
3. Go to "Bot" section and click "Add Bot"
4. Enable these **Privileged Gateway Intents**:
   - ✅ Presence Intent
   - ✅ Server Members Intent
   - ✅ Message Content Intent
5. Copy the bot token

### Invite Bot to Server

Replace `YOUR_CLIENT_ID` with your application's Client ID:
```
https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=8&scope=bot%20applications.commands
```

### Environment Variables

Create a `.env` file with:
```bash
DISCORD_BOT_TOKEN=your_bot_token_here
DB_HOST=localhost
DB_USER=sulfur_bot_user
DB_PASS=your_password_here
DB_NAME=sulfur_bot
GEMINI_API_KEY=your_gemini_key_here
OPENAI_API_KEY=your_openai_key_here  # Optional
```

---

## 🚀 Running the Bot

### Windows
```powershell
# Start with auto-restart (recommended)
.\maintain_bot.ps1

# Or manual start
python bot.py
```

### Linux/Termux
```bash
# Simple start
./start.sh

# Background with screen
screen -S sulfur ./start.sh
# Detach: Ctrl+A, then D
```

---

## 🌐 Web Dashboard

Access at **http://localhost:5000**

Features:
- 📊 Live statistics and uptime
- 📝 Real-time color-coded logs
- 🎮 Bot controls (start/stop/restart)
- 🤖 AI usage tracking and cost monitoring
- 💾 Database viewer

---

## 🔧 Maintenance Features

- **Auto-Update** - Checks for updates every 60 seconds
- **Auto-Commit** - Commits changes every 5 minutes
- **Auto-Backup** - Database backups every 30 minutes (keeps last 10)
- **Control Flags**:
  - `restart.flag` - Gracefully restart bot
  - `stop.flag` - Gracefully stop bot

---

## 🔍 Common Issues

### Bot Won't Start

**Database connection error:**
```bash
# Check MySQL is running
# Windows: Services > MySQL
# Linux: sudo systemctl status mysql
# Termux: ps aux | grep mariadb
```

**Invalid Discord token:**
- Regenerate token in Discord Developer Portal
- Update `DISCORD_BOT_TOKEN` in `.env`

**Module not found:**
```bash
# Activate virtual environment
# Windows: .\venv\Scripts\Activate.ps1
# Linux: source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Music Player Not Working

**FFmpeg not found:**
```bash
# Windows: Download from https://ffmpeg.org/download.html
# Linux: sudo apt-get install ffmpeg
# macOS: brew install ffmpeg
# Termux: pkg install ffmpeg
```

**yt-dlp not installed:**
```bash
pip install yt-dlp
```

---

## 🤝 Contributing

Contributions welcome! Please fork the repository and submit a pull request.

---

## 📄 License

This project is licensed under the MIT License.

---

**Made with ❤️ for the Discord community**
