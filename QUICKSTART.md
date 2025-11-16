# 🚀 Quick Start Guide

This is a simplified guide to get the bot running as fast as possible.

## Windows (5 minutes)

### 1. Install Requirements
- Python from python.org ✅ Check "Add to PATH"
- XAMPP from apachefriends.org
- Git from git-scm.com

### 2. Setup
```powershell
# Clone repo
cd C:\
git clone https://github.com/yourusername/sulfur.git
cd sulfur

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 3. Database
Start XAMPP → Start MySQL → Open phpMyAdmin:
```sql
CREATE DATABASE sulfur_bot;
CREATE USER 'sulfur_bot_user'@'localhost' IDENTIFIED BY 'password123';
GRANT ALL PRIVILEGES ON sulfur_bot.* TO 'sulfur_bot_user'@'localhost';
```

Import: `config\sulfur_bot_schema.sql`

### 4. Configure
Create `.env` file:
```env
DISCORD_TOKEN=your_bot_token_here
DB_HOST=localhost
DB_USER=sulfur_bot_user
DB_PASSWORD=password123
DB_NAME=sulfur_bot
GEMINI_API_KEY=your_gemini_key_here
OPENAI_API_KEY=your_openai_key_here
```

### 5. Run
```powershell
.\maintain_bot.ps1
```

Done! Dashboard: http://localhost:5000

---

## Termux (5 minutes)

### 1. Install Termux
Download from F-Droid (NOT Google Play - Play Store version is outdated and unsupported)

### 2. Setup
```bash
# Update packages
pkg update && pkg upgrade

# Install requirements (including openssh for git)
pkg install python git mariadb openssh

# (Optional) Setup SSH for git
ssh-keygen -t ed25519 -C "your_email@example.com"
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
cat ~/.ssh/id_ed25519.pub
# Add the output to GitHub: Settings → SSH and GPG keys

# Start MariaDB (not mysql - mysql is deprecated)
mariadb-install-db
mariadbd-safe --datadir=$PREFIX/var/lib/mysql &
sleep 15  # Wait for MariaDB to start

# Clone repo (use SSH if you set up keys)
cd ~
git clone git@github.com:yourusername/sulfur.git
# Or use HTTPS: git clone https://github.com/yourusername/sulfur.git
cd sulfur

# Install dependencies
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Database
```bash
# Connect to MariaDB (use 'mariadb' not 'mysql')
mariadb -u root
```

In MariaDB:
```sql
CREATE DATABASE sulfur_bot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'sulfur_bot_user'@'localhost' IDENTIFIED BY 'password123';
GRANT ALL PRIVILEGES ON sulfur_bot.* TO 'sulfur_bot_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

**Note:** For no password setup, use `IDENTIFIED BY ''` and set `DB_PASSWORD=` in .env

### 4. Configure
```bash
nano .env
```

Paste (long-press):
```env
DISCORD_TOKEN=your_bot_token_here
DB_HOST=localhost
DB_USER=sulfur_bot_user
DB_PASSWORD=password123
DB_NAME=sulfur_bot
GEMINI_API_KEY=your_gemini_key_here
OPENAI_API_KEY=your_openai_key_here
```

Save: Ctrl+O, Enter, Ctrl+X

### 5. Run
```bash
chmod +x start.sh maintain_bot.sh
./start.sh
```

Done! 

**Access Web Dashboard:**
- From Android: Open browser and go to `http://localhost:5000`
- From other devices on same network: `http://YOUR_ANDROID_IP:5000`

**Tip:** Use `tmux` to run in background (already installed):
```bash
tmux new -s sulfur
./start.sh
# Detach: Ctrl+B, then D
# Reattach: tmux attach -t sulfur
```

**Alternative:** Use `screen`:
```bash
pkg install screen
screen -S sulfur ./start.sh
# Detach: Ctrl+A, then D
# Reattach: screen -r sulfur
```

---

## Getting API Keys

### Discord Bot Token
1. Go to https://discord.com/developers/applications
2. Click "New Application"
3. Go to "Bot" → "Add Bot"
4. Copy token
5. Enable all 3 Privileged Gateway Intents

### Gemini API Key
1. Go to https://aistudio.google.com/
2. Click "Get API key"
3. Create new key or use existing
4. Copy key

### OpenAI API Key (Optional)
1. Go to https://platform.openai.com/
2. Create account
3. Go to API Keys
4. Create new secret key
5. Copy key

---

## Inviting Bot to Server

Replace `YOUR_CLIENT_ID` with your Application ID from Discord Developer Portal:

```
https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=8&scope=bot%20applications.commands
```

---

## Common Issues

**"Module not found"**
→ Activate virtual environment first

**"Can't connect to database"**
→ Make sure MariaDB is running: `ps aux | grep mariadb`
→ Restart if needed: `mariadbd-safe --datadir=$PREFIX/var/lib/mysql &`

**"Invalid token"**
→ Check .env file for typos

**Bot stops when I close terminal (Termux)**
→ Use `tmux` or `screen` (see Termux section above)

**"mysql: Deprecated program name" error**
→ Use `mariadb` command instead of `mysql`

---

## What's Next?

- Visit web dashboard: http://localhost:5000
- Try commands: `!help`
- Check AI usage: http://localhost:5000/ai_dashboard
- Read full README.md for all features

---

**Need Help?** Check README.md or create an issue on GitHub!
