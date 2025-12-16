# 📱 Termux/Android Setup Guide

Complete guide for running Sulfur Bot on Android using Termux.

---

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Database Setup](#database-setup)
- [WireGuard VPN (Non-Rooted)](#wireguard-vpn-non-rooted)
- [Minecraft Server](#minecraft-server)
- [Keeping Termux Running](#keeping-termux-running)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Install Termux

Download Termux from **F-Droid** (recommended):
- [F-Droid Termux](https://f-droid.org/packages/com.termux/)

> ⚠️ **Don't use Play Store version** - it's outdated and unsupported.

### Grant Storage Access

```bash
termux-setup-storage
```
Grant permission when prompted. This allows access to Download folder.

### Update Packages

```bash
pkg update && pkg upgrade -y
```

---

## Installation

> **Note:** This repository is private. You need to authenticate with GitHub and clone it first.

### Quick Install

```bash
# Clone the repository (requires authentication)
git clone https://github.com/mereMint/sulfur.git
cd sulfur

# Run the quick installer
bash scripts/quickinstall.sh
```

### Manual Install

```bash
# Install core packages
pkg install -y git python python-pip mariadb

# Optional packages
pkg install -y ffmpeg opus screen curl wget openssl

# For Minecraft server
pkg install -y openjdk-21

# For WireGuard (key generation only without root)
pkg install -y wireguard-tools

# Clone repository
git clone https://github.com/mereMint/sulfur.git
cd sulfur

# Setup Python environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run setup wizard
python master_setup.py
```

---

## Database Setup

### Initialize MariaDB

```bash
# First-time setup
mysql_install_db

# Start MariaDB
mysqld_safe &
sleep 3

# Secure installation
mysql_secure_installation
```

### Create Database

```bash
mysql -u root -p
```

```sql
CREATE DATABASE sulfur_bot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'sulfur_bot_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON sulfur_bot.* TO 'sulfur_bot_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### Start MariaDB After Reboot

```bash
mysqld_safe &
```

Add to boot script for auto-start (see below).

---

## WireGuard VPN (Non-Rooted)

Since full WireGuard VPN requires root access, we use the **official WireGuard Android app** instead.

### Step 1: Install WireGuard App

Download from:
- [Play Store](https://play.google.com/store/apps/details?id=com.wireguard.android)
- [F-Droid](https://f-droid.org/packages/com.wireguard.android/)

### Step 2: Generate Configuration

In Sulfur Bot (via Discord or command line):

```bash
cd ~/sulfur
source venv/bin/activate
python -c "
import asyncio
from modules import wireguard_manager as wg

async def main():
    result = await wg.add_device_easy('my_phone')
    for step in result.get('steps', []):
        print(step)

asyncio.run(main())
"
```

Or use Discord command:
```
/vpn add_device device_name:my_phone
```

### Step 3: Import in WireGuard App

The configuration is exported to `Download/SulfurVPN/`:

1. Open WireGuard app
2. Tap **+** button
3. Select **Import from file or archive**
4. Navigate to `Download/SulfurVPN/`
5. Select your `.conf` file

Or scan the QR code if one was generated.

### Step 4: Connect

Toggle the switch to connect!

---

## Minecraft Server

### Requirements

- OpenJDK 21: `pkg install openjdk-21`
- Minimum 2GB free RAM
- 5GB+ storage

### Setup

```bash
# Enable in config
python master_setup.py --minecraft
```

Or edit `config/config.json`:
```json
{
  "modules": {
    "minecraft": {
      "enabled": true,
      "server_type": "paper",
      "minecraft_version": "1.21.4",
      "memory_min": "512M",
      "memory_max": "1536M"
    }
  }
}
```

### Performance Tips for Android

1. **Use Paper or Purpur** - Much better performance than Vanilla
2. **Reduce memory allocation** - Leave RAM for Android system
3. **Lower view distance** - Edit `server.properties`:
   ```properties
   view-distance=6
   simulation-distance=4
   ```
4. **Disable unnecessary features** - In `server.properties`:
   ```properties
   spawn-npcs=false
   spawn-monsters=false  # If not needed
   ```

### Limitations

- Limited player count (2-5 recommended)
- May have lag spikes
- Consider using external hosting for larger servers

---

## Keeping Termux Running

### Acquire Wakelock

1. Pull down notification shade
2. Find Termux notification
3. Tap "ACQUIRE WAKELOCK"

### Disable Battery Optimization

1. Open Android Settings
2. Apps → Termux
3. Battery → Unrestricted

### Auto-Start with Termux:Boot

Install Termux:Boot from F-Droid:
- [Termux:Boot](https://f-droid.org/packages/com.termux.boot/)

Create boot script:
```bash
mkdir -p ~/.termux/boot
nano ~/.termux/boot/start-sulfur.sh
```

```bash
#!/data/data/com.termux/files/usr/bin/bash

# Wait for network
sleep 10

# Start MariaDB
mysqld_safe &
sleep 5

# Start Sulfur Bot
cd ~/sulfur
source venv/bin/activate
python bot.py &

# Start web dashboard
python web_dashboard.py &
```

Make executable:
```bash
chmod +x ~/.termux/boot/start-sulfur.sh
```

### Using Screen for Persistence

```bash
# Install screen
pkg install screen

# Start new session
screen -S sulfur

# Run bot
cd ~/sulfur
source venv/bin/activate
python bot.py

# Detach: Press Ctrl+A, then D

# Reattach later
screen -r sulfur
```

---

## Quick Reference

### Start Services

```bash
# Start MariaDB
mysqld_safe &

# Activate environment
cd ~/sulfur
source venv/bin/activate

# Start bot
python bot.py
```

### Useful Commands

| Command | Description |
|---------|-------------|
| `pkg update` | Update packages |
| `mysqld_safe &` | Start database |
| `screen -S name` | Create screen session |
| `screen -r name` | Reattach to session |
| `termux-setup-storage` | Grant storage access |

### File Locations

| Path | Description |
|------|-------------|
| `~/sulfur/` | Main installation |
| `~/sulfur/config/` | Configuration |
| `~/sulfur/logs/` | Log files |
| `/storage/emulated/0/Download/SulfurVPN/` | Exported VPN configs |

---

## Troubleshooting

### "Storage permission denied"

```bash
termux-setup-storage
```
Then grant permission in the popup.

### "MariaDB won't start"

```bash
# Check if already running
ps aux | grep maria

# Kill existing process
pkill mariadb

# Start fresh
mysql_install_db
mysqld_safe &
```

### "Package not found"

```bash
pkg update
pkg upgrade
```

### "Python packages fail to install"

```bash
# Install build dependencies
pkg install python-pip clang make

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Try again
pip install -r requirements.txt
```

### "Out of memory"

- Reduce Minecraft memory settings
- Close other apps
- Disable unused features

### "Bot disconnects when screen locks"

1. Acquire wakelock (notification)
2. Disable battery optimization
3. Use Termux:Boot for auto-restart

---

## See Also

- [Quick Start Guide](QUICKSTART.md)
- [VPN Guide](VPN_GUIDE.md)
- [Minecraft Server](MINECRAFT.md)
- [Main Documentation](../README.md)
