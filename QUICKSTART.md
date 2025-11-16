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
Download from F-Droid (NOT Google Play)

### 2. Setup
```bash
# Update packages
pkg update && pkg upgrade

# Install requirements
pkg install python git mariadb

# Start MySQL
mysql_install_db
mysqld_safe &

# Clone repo
cd ~
git clone https://github.com/yourusername/sulfur.git
cd sulfur

# Install dependencies
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Database
```bash
mysql -u root -p
```

In MySQL:
```sql
CREATE DATABASE sulfur_bot;
CREATE USER 'sulfur_bot_user'@'localhost' IDENTIFIED BY 'password123';
GRANT ALL PRIVILEGES ON sulfur_bot.* TO 'sulfur_bot_user'@'localhost';
EXIT;
```

Import schema:
```bash
mysql -u sulfur_bot_user -p sulfur_bot < config/sulfur_bot_schema.sql
```

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
chmod +x start.sh
./start.sh
```

Done!

**Tip:** Use `screen` to run in background:
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
→ Make sure MySQL is running

**"Invalid token"**
→ Check .env file for typos

**Bot stops when I close terminal (Termux)**
→ Use `screen` (see Termux section)

---

## What's Next?

- Visit web dashboard: http://localhost:5000
- Try commands: `!help`
- Check AI usage: http://localhost:5000/ai_dashboard
- Read full README.md for all features

---

**Need Help?** Check README.md or create an issue on GitHub!
