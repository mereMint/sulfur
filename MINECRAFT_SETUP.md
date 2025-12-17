# Minecraft Server Integration Guide

This guide explains how to set up and use the Minecraft server integration with the Sulfur Discord bot.

## Features

- **Web Dashboard Control**: Start, stop, and monitor your Minecraft server from http://localhost:5000/minecraft
- **Auto-Start on Boot**: Automatically start the Minecraft server when the bot starts (configurable)
- **Multiple Server Types**: Support for Vanilla, Paper, Purpur, and Fabric servers
- **Backup Management**: Automatic world backups with one-click restore
- **Console Access**: Real-time server console with command execution
- **Player Tracking**: See who's online and monitor server stats
- **Whitelist Management**: Easy whitelist control through the dashboard

## Requirements

### System Requirements

- **Java**: Java 21+ (for Minecraft 1.21+) or Java 17+ (for older versions)
- **RAM**: At least 2GB free RAM (4GB+ recommended)
- **Storage**: 2-5GB for server files, mods, and worlds
- **Network**: Port 25565 (default) must be available

### Platform Support

- ✅ **Linux** (Ubuntu, Debian, Arch, etc.)
- ✅ **Windows** (10/11)
- ✅ **Termux** (Android)
- ✅ **macOS**
- ✅ **Raspberry Pi** (with at least 2GB RAM)

## Installation

### 1. Enable Minecraft Feature

Edit `config/config.json` to enable the Minecraft feature:

```json
{
  "features": {
    "minecraft_server": true
  },
  "modules": {
    "minecraft": {
      "enabled": true,
      "server_type": "paper",
      "minecraft_version": "1.21.11",
      "memory_min": "1G",
      "memory_max": "4G",
      "port": 25565,
      "max_players": 20,
      "whitelist": true,
      "boot_with_bot": true
    }
  }
}
```

#### Configuration Options

- **enabled**: Enable/disable the Minecraft module
- **server_type**: `vanilla`, `paper`, `purpur`, or `fabric`
- **minecraft_version**: e.g., `1.21.11`, `1.20.6`
- **memory_min/max**: RAM allocation (e.g., `1G`, `2G`, `4G`)
- **port**: Server port (default: 25565)
- **max_players**: Maximum player count
- **whitelist**: Enable whitelist mode
- **boot_with_bot**: Auto-start server when bot starts

### 2. Install Java

#### Linux/Termux
```bash
# Ubuntu/Debian
sudo apt install openjdk-21-jre-headless

# Arch Linux
sudo pacman -S jre-openjdk

# Termux
pkg install openjdk-21
```

#### Windows
Download from: https://adoptium.net/

#### macOS
```bash
brew install openjdk@21
```

### 3. Download Server JAR

The server JAR will be downloaded automatically on first start, or you can use the web dashboard:

1. Go to http://localhost:5000/minecraft
2. Navigate to the "Configuration" tab
3. Click "Download/Update Server" button

Or manually via Discord commands (if enabled):
```
/minecraft setup server_type:paper version:1.21.11
```

## Usage

### Web Dashboard

Access the Minecraft dashboard at: **http://localhost:5000/minecraft**

#### Main Features

- **Server Control**: Start/Stop/Restart buttons at the top
- **Live Console**: Real-time server output with command input
- **Player List**: See who's online with player count
- **Server Stats**: Uptime, memory usage, TPS, version
- **Quick Actions**: Backup, whitelist management, scheduling

#### Tabs

1. **Worlds**: View and manage world folders
2. **Backups**: Create and restore backups
3. **Mods & Plugins**: Enable/disable mods (for Fabric servers)
4. **Configuration**: Server settings and memory allocation
5. **Whitelist**: Add/remove players from whitelist

### Auto-Start Configuration

The Minecraft server will automatically start with the bot if:

1. `features.minecraft_server` is `true`
2. `modules.minecraft.boot_with_bot` is `true`

#### Disable Auto-Start

Set `boot_with_bot` to `false` in config.json:

```json
{
  "modules": {
    "minecraft": {
      "boot_with_bot": false
    }
  }
}
```

Then restart the maintenance script.

### Manual Control

#### Linux/Termux
```bash
# Start bot with Minecraft auto-start
./maintain_bot.sh

# Start bot without auto-start (temporary)
# Edit config.json first to set boot_with_bot: false
```

#### Windows
```powershell
# Start bot with Minecraft auto-start
.\maintain_bot.ps1

# Start bot without auto-start (temporary)
# Edit config.json first to set boot_with_bot: false
```

## Database Setup

The Minecraft integration requires MySQL or MariaDB for tracking server state and player data.

### Install Database Server

Both **MySQL** and **MariaDB** are supported interchangeably.

#### Linux
```bash
# Install MariaDB (recommended)
sudo apt install mariadb-server mariadb-client

# Or MySQL
sudo apt install mysql-server mysql-client

# Start the service
sudo systemctl start mariadb
sudo systemctl enable mariadb
```

#### Termux
```bash
# Install MariaDB
pkg install mariadb

# Initialize database
mysql_install_db

# Start server
mysqld_safe --datadir=$PREFIX/var/lib/mysql &
```

#### Windows
Download and install:
- **MariaDB**: https://mariadb.org/download/
- **MySQL**: https://dev.mysql.com/downloads/installer/

Or use XAMPP which includes MariaDB.

#### macOS
```bash
# Install MariaDB
brew install mariadb

# Start service
brew services start mariadb
```

### Setup Database

Run the setup script to create the database and user:

#### Linux/Termux
```bash
./setup_mysql.sh
```

#### Windows
```powershell
.\setup_mysql.ps1
```

The script will:
1. Check if MySQL/MariaDB is running
2. Create the `sulfur_bot` database
3. Create the `sulfur_bot_user` user
4. Apply necessary permissions
5. Test the connection

## Troubleshooting

### Minecraft Server Won't Start

**Check Java Installation**
```bash
# Linux/Termux/macOS
java -version

# Should show Java 17+ or Java 21+
```

**Check Server JAR**
- Ensure `minecraft_server/server.jar` exists
- If not, download it via the web dashboard

**Check Memory Settings**
- Ensure your system has enough free RAM
- Reduce `memory_max` in config if needed

**Check Logs**
```bash
# View Minecraft server logs
tail -f minecraft_server/logs/latest.log

# View bot maintenance logs
tail -f logs/maintenance_*.log
```

### Database Connection Issues

**Check Database Server**
```bash
# Linux
sudo systemctl status mariadb

# Termux
pgrep mysqld
```

**Test Connection**
```bash
# Test with mysql client
mysql -u sulfur_bot_user sulfur_bot

# Or mariadb client
mariadb -u sulfur_bot_user sulfur_bot
```

**Reset Database User**
```bash
# Linux (as root)
sudo mysql

# Termux/macOS
mysql

# In MySQL prompt
DROP USER IF EXISTS 'sulfur_bot_user'@'localhost';
CREATE USER 'sulfur_bot_user'@'localhost' IDENTIFIED BY '';
GRANT ALL PRIVILEGES ON sulfur_bot.* TO 'sulfur_bot_user'@'localhost';
FLUSH PRIVILEGES;
```

### Port 25565 Already in Use

**Find Process Using Port**
```bash
# Linux/macOS
lsof -i:25565

# Windows
netstat -ano | findstr :25565
```

**Kill Process**
```bash
# Linux/macOS
kill -9 <PID>

# Windows (as Administrator)
taskkill /PID <PID> /F
```

**Or Change Port**

Edit config.json:
```json
{
  "modules": {
    "minecraft": {
      "port": 25566
    }
  }
}
```

### Web Dashboard Not Showing Minecraft Link

1. Ensure you're using the latest version of the code
2. Clear browser cache (Ctrl+F5 / Cmd+Shift+R)
3. Check that layout.html has the Minecraft navigation link
4. Restart the web dashboard

### Auto-Start Not Working

**Check Configuration**
```bash
# View current config
cat config/config.json | grep -A 5 minecraft
```

Should show:
```json
"features": {
  "minecraft_server": true
}
"modules": {
  "minecraft": {
    "boot_with_bot": true
  }
}
```

**Check Logs**
```bash
# View maintenance logs for Minecraft startup messages
tail -f logs/maintenance_*.log | grep -i minecraft
```

Look for messages like:
- "Checking Minecraft server auto-start configuration..."
- "Minecraft server auto-start is enabled"
- "Starting Minecraft server..."

## Platform-Specific Notes

### Termux (Android)

- Use `mysqld_safe` to start MariaDB: `mysqld_safe &`
- Ensure you have enough storage space (at least 3GB free)
- Keep the device plugged in (server is resource-intensive)
- Use Wake Lock app to prevent device sleep
- Performance may vary depending on device specs

### Raspberry Pi

- Use at least Raspberry Pi 4 with 4GB+ RAM
- Consider using lightweight server type like Paper
- Reduce memory allocation if needed: `memory_max: "2G"`
- Use SD card with good write speed or USB boot
- Monitor temperature to avoid thermal throttling

### Windows

- Run PowerShell as Administrator for port operations
- Add firewall exception for port 25565
- Use XAMPP for easy MariaDB setup
- Performance is generally good on modern hardware

## Advanced Configuration

### Schedule-Based Operation

Configure the server to only run during specific hours:

```json
{
  "modules": {
    "minecraft": {
      "schedule": {
        "mode": "timed",
        "start_hour": 6,
        "end_hour": 22
      }
    }
  }
}
```

**Schedule Modes:**
- `always`: 24/7 operation
- `timed`: Specific hours (uses `start_hour` and `end_hour`)
- `weekdays_only`: Monday-Friday only
- `weekends_only`: Saturday-Sunday only
- `custom`: Day-specific schedules

### Automatic Backups

Configure automatic world backups:

```json
{
  "modules": {
    "minecraft": {
      "backups": {
        "enabled": true,
        "interval_hours": 6,
        "max_backups": 10
      }
    }
  }
}
```

### Performance Optimization

For better performance, adjust JVM flags in the config:

```json
{
  "modules": {
    "minecraft": {
      "memory_min": "2G",
      "memory_max": "4G",
      "performance_mods": {
        "enabled": true,
        "mods": ["lithium", "ferritecore", "spark"]
      }
    }
  }
}
```

## Security Best Practices

1. **Enable Whitelist**: Set `"whitelist": true` in config
2. **Use Strong Passwords**: For database and RCON (if enabled)
3. **Firewall Rules**: Only open port 25565 to trusted IPs
4. **Regular Backups**: Enable automatic backups
5. **Keep Updated**: Update server JAR regularly
6. **Monitor Logs**: Check for suspicious activity

## Getting Help

- **Documentation**: See `docs/MINECRAFT.md` for more details
- **Logs**: Check `logs/maintenance_*.log` and `minecraft_server/logs/`
- **Web Dashboard**: http://localhost:5000/minecraft for visual interface
- **GitHub Issues**: Report bugs at the repository

## Credits

- **Sulfur Bot**: Discord bot with Minecraft integration
- **Paper**: High-performance Minecraft server (https://papermc.io/)
- **Purpur**: Extended Paper fork (https://purpurmc.org/)
- **Fabric**: Modding platform (https://fabricmc.net/)
