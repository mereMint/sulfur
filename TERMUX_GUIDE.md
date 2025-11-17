# Sulfur Bot - Termux Installation Guide

Complete guide for running Sulfur Discord bot on Android using Termux.

## Prerequisites

1. **Termux App** (Download from F-Droid, NOT Play Store)
   - F-Droid: https://f-droid.org/en/packages/com.termux/
   - Play Store version is outdated and incompatible

2. **Optional but Recommended:**
   - **Termux:Boot** - Auto-start bot on device boot
   - **Termux:API** - Access Android system features
   - **Termux:Widget** - Quick launch shortcuts

## Quick Installation

### Method 1: Automated Setup (Recommended)

**Option A: One-Line Command (Easiest)**

Copy and paste this ENTIRE line as ONE command:

```bash
pkg update && pkg install -y git && git clone https://github.com/mereMint/sulfur.git sulfur && cd sulfur && bash termux_quickstart.sh
```

**Option B: Step-by-Step**

If you prefer to see each step:

```bash
# Step 1: Update and install git
pkg update && pkg install -y git

# Step 2: Clone the repository
git clone https://github.com/mereMint/sulfur.git sulfur

# Step 3: Enter the directory and run setup
cd sulfur
bash termux_quickstart.sh
```

**Note**: The initial clone uses HTTPS (public access). The script will set up SSH authentication for future git operations.

**Alternative**: If you already have the repository:
```bash
cd sulfur  # or cd ~/sulfur
bash termux_quickstart.sh
```

This script will:
- ✅ Update Termux packages
- ✅ Install Python, MariaDB, Git, SSH
- ✅ Setup and start MariaDB database
- ✅ Create database and user
- ✅ Clone the repository
- ✅ Generate SSH key for GitHub (optional)
- ✅ Setup Python virtual environment
- ✅ Install all dependencies
- ✅ Configure .env file interactively
- ✅ Initialize database tables
- ✅ Create startup helper script

### Method 2: Manual Installation

If you prefer to do it step-by-step:

#### 1. Update Termux
```bash
pkg update && pkg upgrade
```

#### 2. Install Required Packages
```bash
pkg install -y python git mariadb openssh nano wget curl
```

#### 3. Setup MariaDB
```bash
# Initialize database
mysql_install_db

# Start MariaDB
mysqld_safe &

# Wait a few seconds
sleep 10

# Create database and user
# Note: Use 'mariadb' command on Termux, not 'mysql'
mariadb -u root <<EOF
CREATE DATABASE IF NOT EXISTS sulfur_bot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'sulfur_bot_user'@'localhost';
GRANT ALL PRIVILEGES ON sulfur_bot.* TO 'sulfur_bot_user'@'localhost';
FLUSH PRIVILEGES;
EOF
```

#### 4. Clone Repository
```bash
cd ~
git clone https://github.com/mereMint/sulfur.git
cd sulfur
```

#### 5. Setup Python Environment
```bash
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### 6. Configure Environment
```bash
# Create .env file
nano .env

# Add your tokens (without quotes):
# DISCORD_BOT_TOKEN=your_token_here
# GEMINI_API_KEY=your_key_here
# OPENAI_API_KEY=your_key_here
# DB_HOST=localhost
# DB_USER=sulfur_bot_user
# DB_PASS=
# DB_NAME=sulfur_bot
```

#### 7. Initialize Database
```bash
mariadb -u sulfur_bot_user sulfur_bot < setup_database.sql
```

#### 8. Test Setup
```bash
python test_setup.py
```

## Starting the Bot

### Using the Helper Script
```bash
cd ~/sulfur
./start_sulfur.sh
```

### Manual Start
```bash
cd ~/sulfur
source venv/bin/activate

# Make sure MariaDB is running
pgrep mysqld || mysqld_safe &

# Start bot with auto-restart
bash maintain_bot.sh
```

## Important Termux-Specific Notes

### Keep Termux Running

Termux must stay active for the bot to work. To prevent Android from killing it:

1. **Acquire Wake Lock:**
   - Long-press Termux notification
   - Tap "Acquire Wake Lock"
   - This prevents CPU sleep while running

2. **Disable Battery Optimization:**
   - Settings → Apps → Termux
   - Battery → Unrestricted

3. **Keep Screen Off:**
   - Termux can run with screen off if Wake Lock is active
   - Just don't swipe away the notification

### Auto-Start on Boot

Using **Termux:Boot** app:

1. Install Termux:Boot from F-Droid
2. Create startup script:
```bash
mkdir -p ~/.termux/boot
nano ~/.termux/boot/sulfur.sh
```

3. Add this content:
```bash
#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock

# Start MariaDB
mysqld_safe &
sleep 5

# Start bot
cd ~/sulfur
source venv/bin/activate
bash maintain_bot.sh > ~/sulfur/logs/boot_$(date +%Y%m%d_%H%M%S).log 2>&1 &
```

4. Make it executable:
```bash
chmod +x ~/.termux/boot/sulfur.sh
```

### Access Web Dashboard

#### From the same device:
```
http://localhost:5000
```

#### From another device on same WiFi:

1. Find your phone's IP address:
```bash
ifconfig wlan0 | grep inet
# Or use Termux:API
termux-wifi-connectioninfo | grep ip
```

2. Access from browser on other device:
```
http://YOUR_PHONE_IP:5000
```

Example: `http://192.168.1.100:5000`

## Maintenance Commands

### Check if Bot is Running
```bash
pgrep -af python | grep bot.py
```

### Check if MariaDB is Running
```bash
pgrep -x mysqld || pgrep -x mariadbd
```

### Start MariaDB Manually
```bash
mysqld_safe --datadir=$PREFIX/var/lib/mysql &
```

### Stop the Bot
```bash
# Method 1: Press Q in the terminal
# Method 2: Create stop flag
touch ~/sulfur/stop.flag

# Method 3: Kill process
pkill -f bot.py
```

### View Logs
```bash
cd ~/sulfur/logs
ls -lt  # List logs by date
tail -f session_*.log  # View live logs
```

### Update Bot
```bash
cd ~/sulfur
git pull
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

### Database Backup
```bash
cd ~/sulfur/backups
mysqldump -u sulfur_bot_user sulfur_bot > backup_$(date +%Y%m%d_%H%M%S).sql
```

## Troubleshooting

### Installation Asks for GitHub Username/Password

**Problem**: When running the installation command, git asks for username and password during clone.

**Cause**: You ran the commands separately instead of as one line with `&&`.

**Solution**: Copy and paste the ENTIRE installation command as ONE line:
```bash
pkg update && pkg install -y git && git clone https://github.com/mereMint/sulfur.git sulfur && cd sulfur && bash termux_quickstart.sh
```

The `&&` ensures each command only runs if the previous one succeeded. Running them separately breaks the flow.

### MariaDB Won't Start

```bash
# Check if already running
pgrep mysqld

# If not, try:
pkill -9 mysqld  # Kill any stuck processes
rm -f $PREFIX/var/lib/mysql/*.pid  # Remove PID files
mysqld_safe &
```

### Permission Denied Errors

```bash
# Fix Termux permissions
termux-setup-storage

# Fix script permissions
chmod +x *.sh
chmod +x ~/.termux/boot/*.sh
```

### Bot Crashes on Import Errors

```bash
# Reinstall dependencies
cd ~/sulfur
source venv/bin/activate
pip install -r requirements.txt --force-reinstall
```

### Database Connection Failed

```bash
# Check MariaDB status
pgrep mariadbd || echo "MariaDB not running"

# Test connection
mariadb -u sulfur_bot_user sulfur_bot -e "SELECT 1;"

# Check .env file
cat .env | grep DB_
```

### Out of Memory

Termux apps share Android's memory limits. If you get OOM errors:

1. Close other apps
2. Restart Termux
3. Use a lighter AI model (gemini-2.5-flash instead of 1.5-pro)
4. Reduce `conversation_context_window` in config.json

### SSH Key Issues

```bash
# Generate new key
ssh-keygen -t ed25519 -C "your_email@example.com"

# Copy public key
cat ~/.ssh/id_ed25519.pub

# Test GitHub connection
ssh -T git@github.com
```

## Performance Tips

### Optimize Memory Usage

Edit `config/config.json`:
```json
{
  "api": {
    "gemini_model": "gemini-2.5-flash",  // Use lighter model
    "conversation_context_window": 120   // Reduce from 300
  }
}
```

### Reduce Database Size

```bash
# Clean old conversation context
cd ~/sulfur
source venv/bin/activate
python -c "
from modules.db_helpers import get_db_connection
import asyncio

async def cleanup():
    async with get_db_connection() as (conn, cursor):
        # Delete conversations older than 7 days
        await cursor.execute(
            'DELETE FROM conversation_context WHERE timestamp < NOW() - INTERVAL 7 DAY'
        )
        await conn.commit()
        print('Cleaned old conversations')

asyncio.run(cleanup())
"
```

### Background Execution

Use `nohup` to run in background and close Termux:

```bash
cd ~/sulfur
source venv/bin/activate
nohup bash maintain_bot.sh > logs/nohup.log 2>&1 &
```

## Advanced Configuration

### Custom Startup Script

Create `~/start_bot_custom.sh`:
```bash
#!/data/data/com.termux/files/usr/bin/bash

# Custom environment variables
export PYTHONUNBUFFERED=1

# Start MariaDB with custom settings
mysqld_safe \
    --innodb-buffer-pool-size=128M &

# Wait for database
sleep 5

# Activate environment
cd ~/sulfur
source venv/bin/activate

# Run bot with custom options
python bot.py --log-level DEBUG
```

### Notification on Crash

Install Termux:API and add to maintain_bot.sh:
```bash
# Add after bot crashes
termux-notification --title "Sulfur Bot" --content "Bot crashed, restarting..."
```

## Useful Termux Commands

```bash
# Storage access
termux-setup-storage

# Show WiFi info
termux-wifi-connectioninfo

# Battery status
termux-battery-status

# Send notification
termux-notification --title "Bot" --content "Started!"

# Vibrate on events
termux-vibrate -d 200

# Text-to-speech
termux-tts-speak "Bot is online"
```

## Resources

- **Termux Wiki**: https://wiki.termux.com
- **Discord.py Docs**: https://discordpy.readthedocs.io
- **Bot Documentation**: See `docs/` folder
- **Project Structure**: See `PROJECT_STRUCTURE.md`

## Quick Reference Card

```
╔══════════════════════════════════════════════════════════╗
║  SULFUR BOT - TERMUX QUICK REFERENCE                    ║
╠══════════════════════════════════════════════════════════╣
║  Start Bot:        cd ~/sulfur && ./start_sulfur.sh     ║
║  Stop Bot:         Press Q or touch stop.flag            ║
║  View Logs:        tail -f ~/sulfur/logs/session_*.log  ║
║  Web Dashboard:    http://localhost:5000                 ║
║  Start MariaDB:    mysqld_safe &                        ║
║  Update Bot:       cd ~/sulfur && git pull               ║
║  Restart:          touch ~/sulfur/restart.flag           ║
║  Check Status:     pgrep -af bot.py                      ║
╚══════════════════════════════════════════════════════════╝
```

## Support

- Check logs in `~/sulfur/logs/`
- Review `docs/ERROR_CHECKING_GUIDE.md`
- Check bot status in web dashboard
- Review config at `http://localhost:5000/config`

Happy botting on Android! 🤖📱
