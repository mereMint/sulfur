# Termux Bot Not Replying - Troubleshooting Guide

## Quick Diagnostics

Run these commands on your Termux device to diagnose the issue:

```bash
cd ~/sulfur

# 1. Check if bot is running
pgrep -af python | grep bot.py

# 2. Check recent bot logs (last 100 lines)
tail -n 100 logs/bot_*.log | tail -n 100

# 3. Check if Discord token is valid
grep DISCORD_BOT_TOKEN .env

# 4. Check if MariaDB is running
pgrep -x mysqld || pgrep -x mariadbd

# 5. Test database connection
mariadb -u sulfur_bot_user sulfur_bot -e "SELECT 1;"

# 6. Check Python environment
source venv/bin/activate
python -c "import discord; print(f'discord.py version: {discord.__version__}')"

# 7. Check API keys
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('GEMINI_API_KEY:', 'SET' if os.getenv('GEMINI_API_KEY') else 'MISSING')"
```

## Common Issues & Solutions

### 1. Bot Shows Online But Doesn't Respond

**Symptoms:**
- Bot is online in Discord
- Mentions don't trigger responses
- No errors in logs

**Possible Causes:**

#### A. Message Content Intent Not Enabled
**Check Discord Developer Portal:**
1. Go to https://discord.com/developers/applications
2. Select your bot
3. Navigate to "Bot" section
4. Scroll to "Privileged Gateway Intents"
5. Enable **"Message Content Intent"** ✅
6. Save changes
7. Restart bot: `touch ~/sulfur/restart.flag`

#### B. Bot Names Not Configured
**Check config:**
```bash
cat config/config.json | grep -A 5 '"names"'
```

Should show:
```json
"names": [
  "sulf",
  "sulfur"
]
```

**Test trigger:**
- Mention bot: `@YourBot hello`
- Use name: `sulf hello` or `sulfur hello`

#### C. AI API Keys Missing or Invalid
**Check .env file:**
```bash
grep -E "GEMINI_API_KEY|OPENAI_API_KEY" .env
```

**Test API manually:**
```bash
source venv/bin/activate
python test_setup.py
```

Look for:
```
Testing Gemini API...
✓ Gemini API working
```

If API test fails:
- Verify key at https://aistudio.google.com/
- Check quota/billing at https://console.cloud.google.com/
- Ensure "Generative Language API" is enabled

### 2. Bot Crashes or Restart Loops

**Check crash logs:**
```bash
tail -n 200 logs/bot_*.log | grep -i "error\|traceback"
```

**Common errors:**

#### "ModuleNotFoundError: No module named 'discord'"
```bash
cd ~/sulfur
source venv/bin/activate
pip install -r requirements.txt
```

#### "Access denied for user 'sulfur_bot_user'"
```bash
mariadb -u root
CREATE USER IF NOT EXISTS 'sulfur_bot_user'@'localhost';
GRANT ALL PRIVILEGES ON sulfur_bot.* TO 'sulfur_bot_user'@'localhost';
FLUSH PRIVILEGES;
exit
```

#### "Can't connect to local MySQL server"
```bash
# Start MariaDB
mysqld_safe &
sleep 10

# Verify running
pgrep mysqld
```

### 3. Intents/Permission Errors

**Check bot logs for:**
```
discord.errors.Forbidden
discord.errors.HTTPException: 403
Intents are being requested that have not been enabled
```

**Solution:**
1. Enable intents in Discord Developer Portal (see 1.A above)
2. Check bot has proper role permissions in server
3. Ensure bot was invited with correct scopes

**Re-invite bot with correct permissions:**
```
https://discord.com/api/oauth2/authorize?client_id=YOUR_BOT_CLIENT_ID&permissions=8&scope=bot%20applications.commands
```
Replace `YOUR_BOT_CLIENT_ID` with your bot's client ID.

### 4. Database Connection Issues

**Test connection:**
```bash
cd ~/sulfur
source venv/bin/activate
python test_db_connection.py
```

**If fails:**
```bash
# Check MariaDB status
pgrep mysqld || echo "MariaDB not running"

# Start if stopped
mysqld_safe &
sleep 10

# Verify database exists
mariadb -u root -e "SHOW DATABASES;" | grep sulfur_bot

# Create if missing
mariadb -u root -e "CREATE DATABASE IF NOT EXISTS sulfur_bot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

### 5. Secondary Instance Blocking

**Symptoms:** Bot file says "SECONDARY_INSTANCE" in logs

**Check for lock file:**
```bash
cat ~/sulfur/bot_instance.lock
```

**Remove stale lock:**
```bash
rm -f ~/sulfur/bot_instance.lock
touch ~/sulfur/restart.flag
```

### 6. Environment Variables Not Loaded

**Check .env exists and is readable:**
```bash
ls -la ~/sulfur/.env
cat ~/sulfur/.env | grep DISCORD_BOT_TOKEN
```

**Verify format (no quotes around values):**
```bash
# CORRECT:
DISCORD_BOT_TOKEN=MTQzODU5NTUzNjE1MTM4MDAxOA.GExample.Token

# WRONG (don't use quotes):
DISCORD_BOT_TOKEN="MTQzODU5NTUzNjE1MTM4MDAxOA.GExample.Token"
```

**If wrong format:**
```bash
nano ~/sulfur/.env
# Remove quotes, save (Ctrl+O, Enter, Ctrl+X)
touch ~/sulfur/restart.flag
```

## Enable Debug Logging

Add verbose logging temporarily:

```bash
cd ~/sulfur
source venv/bin/activate

# Edit bot.py to add debug prints
nano bot.py
```

Add at the top of `on_message` function (around line 2566):
```python
async def on_message(message):
    """Fires on every message in any channel the bot can see."""
    print(f"[DEBUG] Received message from {message.author.name}: {message.content[:50]}")
    
    # ... rest of function
```

Add in `run_chatbot` (around line 2590):
```python
async def run_chatbot(message):
    """Handles the core logic of fetching and sending an AI response."""
    print(f"[DEBUG] Chatbot triggered by {message.author.name}")
    print(f"[DEBUG] User prompt: {message.content}")
    # ... rest of function
```

Restart bot and watch logs:
```bash
tail -f logs/bot_*.log
```

## Test Bot Response Manually

```bash
cd ~/sulfur
source venv/bin/activate

# Test AI API directly
python -c "
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

from modules.api_helpers import get_chat_response

async def test():
    config = {
        'api': {'provider': 'gemini', 'timeout': 30},
        'bot': {'system_prompt': 'You are a helpful bot.'}
    }
    gemini_key = os.getenv('GEMINI_API_KEY')
    history = []
    response, error, _ = await get_chat_response(
        history, 'Hello', 'TestUser', 
        'You are a helpful bot.', config, gemini_key, None
    )
    print(f'Response: {response}')
    print(f'Error: {error}')

asyncio.run(test())
"
```

Expected output:
```
Response: Hello! How can I help you today?
Error: None
```

## Check Maintenance Script

The `maintain_bot.sh` might have issues:

```bash
# Check if maintainer is running
pgrep -af maintain_bot.sh

# Stop maintainer
pkill -f maintain_bot.sh

# Start bot directly for testing
cd ~/sulfur
source venv/bin/activate
python bot.py
```

Watch output directly to see errors immediately.

## Verify All Components

Run the verification script:
```bash
cd ~/sulfur
bash verify_termux_setup.sh
```

Look for any `✗` marks and fix those issues first.

## Complete Reset (Last Resort)

If nothing works, clean reinstall:

```bash
# Stop everything
pkill -f bot.py
pkill -f maintain_bot.sh
pkill -f mysqld

# Backup .env
cp ~/sulfur/.env ~/sulfur_env_backup

# Remove and reclone
cd ~
rm -rf sulfur
git clone https://github.com/YOUR_USERNAME/sulfur.git
cd sulfur

# Restore .env
cp ~/sulfur_env_backup .env

# Run quickstart
bash termux_quickstart.sh
```

## Get Help

When asking for help, provide:

```bash
cd ~/sulfur

# 1. Python version
python -V

# 2. Termux version
echo $TERMUX_VERSION

# 3. Architecture
uname -m

# 4. Last 100 log lines
tail -n 100 logs/bot_*.log

# 5. Process status
pgrep -af python
pgrep -x mysqld || pgrep -x mariadbd

# 6. Package versions
source venv/bin/activate
pip list | grep -E "discord|flask|aiohttp|mysql"

# 7. Verification result
bash verify_termux_setup.sh 2>&1
```

Share all this output when requesting support.

## Quick Fixes Checklist

- [ ] Message Content Intent enabled in Discord Developer Portal
- [ ] Bot invited with correct permissions/scopes
- [ ] `.env` file has valid Discord token (no quotes)
- [ ] `.env` file has valid Gemini API key
- [ ] MariaDB is running (`pgrep mysqld`)
- [ ] Database `sulfur_bot` exists
- [ ] Virtual environment activated (`source venv/bin/activate`)
- [ ] All packages installed (`pip install -r requirements.txt`)
- [ ] No stale lock file (`rm -f bot_instance.lock`)
- [ ] Config has bot names (`"sulf", "sulfur"`)
- [ ] Wake lock acquired (long-press Termux notification)
- [ ] Latest code pulled (`git pull`)
- [ ] Bot process is actually running (`pgrep -af bot.py`)
