# Minecraft Server Troubleshooting Guide

This guide helps resolve common Minecraft server issues with the Sulfur Bot.

## Table of Contents
1. [Server Won't Start](#server-wont-start)
2. [Can't Connect to Server](#cant-connect-to-server)
3. [Console Not Showing Output](#console-not-showing-output)
4. [Auto-Start Not Working](#auto-start-not-working)
5. [Dashboard Not Updating](#dashboard-not-updating)

---

## Server Won't Start

### Check Java Installation
```bash
java -version
```
You need Java 21+ for Minecraft 1.21.11.

### "class file version 65.0" Error (Java Version Mismatch)
If you see an error like:
```
UnsupportedClassVersionError: class file version 65.0
```
This means you have an older Java version (17 or lower) but need Java 21.

**Solution - Install Java 21:**

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install openjdk-21-jre-headless

# Fedora/RHEL
sudo dnf install java-21-openjdk-headless

# Arch Linux
sudo pacman -S jre21-openjdk-headless

# macOS (with Homebrew)
brew install openjdk@21

# Windows
# Download from: https://adoptium.net/temurin/releases/?version=21
```

**After installing Java 21, update the Minecraft startup script:**

The bot should automatically detect Java 21 if it's installed. If not, set the `JAVA_HOME` environment variable:
```bash
export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64  # Linux
# Then restart the bot
```

### Check Server Logs
1. Go to web dashboard: `http://localhost:5000/minecraft`
2. Check console output for errors
3. Or check logs directly: `minecraft_server/logs/latest.log`

### Common Issues
- **EULA not accepted**: Should be automatic, but check `minecraft_server/eula.txt`
- **Port already in use**: Another server using port 25565
- **Insufficient memory**: Increase `memory_max` in config
- **Missing server JAR**: Download failed, try manual download

---

## Can't Connect to Server

This is the most common issue! Follow these steps:

### 1. Verify Server is Running
```bash
# Check if server process is running
ps aux | grep java | grep minecraft

# Or check dashboard status
```

### 2. Check Server Port
**Default port**: 25565

```bash
# Test if port is listening
netstat -tuln | grep 25565
# Or
ss -tuln | grep 25565
```

### 3. Firewall Configuration

#### Windows
1. Open Windows Defender Firewall
2. Allow port 25565 TCP/UDP
3. Or temporarily disable firewall to test

#### Linux
```bash
# UFW
sudo ufw allow 25565/tcp
sudo ufw allow 25565/udp

# iptables
sudo iptables -A INPUT -p tcp --dport 25565 -j ACCEPT
sudo iptables -A INPUT -p udp --dport 25565 -j ACCEPT
```

#### Termux (Android)
- Termux doesn't have firewall by default
- Check if Android has any firewall apps installed

### 4. Router Port Forwarding

If connecting from outside your local network:

1. Log into your router (usually `192.168.1.1` or `192.168.0.1`)
2. Find "Port Forwarding" or "Virtual Server"
3. Forward port 25565 TCP/UDP to your server's local IP
4. Example:
   - External Port: 25565
   - Internal Port: 25565
   - Internal IP: 192.168.1.100 (your server's IP)
   - Protocol: TCP+UDP

### 5. Check Whitelist

The whitelist is enabled by default. To add players:

#### Via Dashboard
1. Go to `http://localhost:5000/minecraft`
2. Click "Add to Whitelist"
3. Enter Minecraft username (exact spelling!)

#### Via Console
```
whitelist add YourMinecraftUsername
```

#### Via Config
1. Stop server
2. Edit `minecraft_server/whitelist.json`
3. Add entry (need UUID):
```json
[
  {
    "uuid": "player-uuid-here",
    "name": "PlayerName"
  }
]
```
4. Start server

#### Disable Whitelist (for testing)
In server console:
```
whitelist off
```

### 6. Server Properties

Check `minecraft_server/server.properties`:
```properties
# Should be false for LAN, true for public servers
online-mode=false

# Should match your config
server-port=25565

# Whitelist status
white-list=true
enforce-whitelist=false
```

### 7. Connection Testing

#### Local Network
```
minecraft server IP: <your-local-ip>:25565
```

To find your local IP:
- Windows: `ipconfig`
- Linux/Mac: `ifconfig` or `ip addr`
- Discord: `/admin dashboard` (shows local IP)

#### Public Server
```
minecraft server IP: <your-public-ip>:25565
```

To find your public IP:
- Visit: https://whatismyip.com
- Or use: `curl ifconfig.me`

---

## Console Not Showing Output

### Dashboard Console
1. Check WebSocket connection (F12 console in browser)
2. Should see: "WebSocket connected"
3. Reload page to reconnect

### Server Logs
If dashboard console is empty but server is running:
1. Check `minecraft_server/logs/latest.log` directly
2. Server might be starting slowly
3. Wait 30-60 seconds for initialization

### Common Issues
- **Browser cache**: Clear cache and reload (Ctrl+Shift+R)
- **WebSocket blocked**: Check browser console for errors
- **Server not started**: Click "Start Server" button

---

## Auto-Start Not Working

### Configuration Check
1. Open `config/config.json`
2. Verify settings:
```json
{
  "features": {
    "minecraft_server": true
  },
  "modules": {
    "minecraft": {
      "enabled": true,
      "boot_with_bot": true,
      "schedule": {
        "mode": "always"
      }
    }
  }
}
```

### Schedule Modes
- `always`: Server runs 24/7 (what you want)
- `timed`: Server runs during specific hours
- `weekdays_only`: Weekdays only
- `weekends_only`: Weekends only
- `custom`: Custom schedule per day

### Verify Auto-Start
When maintain script starts, look for:
```
[INFO] Checking Minecraft server auto-start configuration...
[INFO] Minecraft server auto-start is enabled
[INFO] Starting Minecraft server...
```

If you see "auto-start is disabled", check your config.

---

## Dashboard Not Updating

### Status Updates
The dashboard auto-refreshes every 5 seconds.

### Force Refresh
- Click browser refresh (F5)
- Or close and reopen dashboard page

### WebSocket Issues
1. Open browser console (F12)
2. Look for WebSocket errors
3. Verify: `ws://localhost:5000/socket.io/`

### Server Issues
If dashboard shows "Loading..." forever:
1. Check web dashboard is running:
   ```bash
   ps aux | grep web_dashboard
   ```
2. Check port 5000 is listening:
   ```bash
   netstat -tuln | grep 5000
   ```
3. Restart maintain script

---

## Advanced Troubleshooting

### Memory Issues
If server crashes with OutOfMemoryError:
```json
{
  "minecraft": {
    "memory_min": "2G",
    "memory_max": "4G"
  }
}
```
Both values should be set appropriately for your system.

### Java Version
Different Minecraft versions need different Java versions:
- Minecraft 1.21.x: Java 21+
- Minecraft 1.20.x: Java 17+
- Minecraft 1.18-1.19: Java 17+
- Minecraft 1.17: Java 16+

### Server Type Comparison
- **Vanilla**: Official Mojang server, stable
- **Paper**: Optimized, better performance, plugin support
- **Purpur**: Fork of Paper with more features
- **Fabric**: Modding platform, mod support

### Database Issues
If dashboard shows database errors:
```bash
# Check MySQL/MariaDB is running
systemctl status mysql
# Or
systemctl status mariadb

# Restart if needed
systemctl restart mysql
```

---

## Getting Help

### Log Files
When asking for help, provide:
1. `logs/maintenance_*.log` - Maintain script logs
2. `logs/bot_*.log` - Bot logs
3. `minecraft_server/logs/latest.log` - Server logs
4. Your config (redact sensitive info)

### Discord Support
Use `/admin dashboard` to get dashboard URL with local IP.

### GitHub Issues
Report bugs at: https://github.com/mereMint/sulfur/issues

Include:
- OS (Windows/Linux/Termux)
- Minecraft version
- Server type (vanilla/paper/etc)
- Error messages
- What you've tried

---

## Quick Fixes Checklist

- [ ] Server is running (check dashboard)
- [ ] Port 25565 is open (firewall)
- [ ] Whitelist is configured correctly
- [ ] Using correct IP address
- [ ] Java is installed and correct version
- [ ] config.json has correct settings
- [ ] No other server using port 25565
- [ ] Router port forwarding (if needed)
- [ ] Dashboard shows "Online" status
- [ ] Console shows server output

---

## Configuration Examples

### 24/7 Public Server
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
      "memory_min": "2G",
      "memory_max": "4G",
      "port": 25565,
      "max_players": 20,
      "boot_with_bot": true,
      "whitelist": true,
      "schedule": {
        "mode": "always"
      }
    }
  }
}
```

### Timed Server (9 AM - 10 PM)
```json
{
  "modules": {
    "minecraft": {
      "schedule": {
        "mode": "timed",
        "start_hour": 9,
        "end_hour": 22
      }
    }
  }
}
```

### Weekend-Only Server
```json
{
  "modules": {
    "minecraft": {
      "schedule": {
        "mode": "weekends_only",
        "weekend_hours": {
          "start": 0,
          "end": 24
        }
      }
    }
  }
}
```

---

## Performance Optimization

### Memory Tuning
```json
{
  "minecraft": {
    "memory_min": "2G",    // Minimum heap
    "memory_max": "4G"     // Maximum heap
  }
}
```

**Guidelines:**
- 1-5 players: 2G min, 3G max
- 5-10 players: 3G min, 4G max  
- 10-20 players: 4G min, 6G max
- 20+ players: 6G min, 8G max

### Server Types Performance
Best to worst performance:
1. **Paper** - Best optimization, recommended
2. **Purpur** - Good optimization + extra features
3. **Vanilla** - Official, acceptable performance
4. **Fabric** - Depends on mods installed

---

## Security Best Practices

1. **Always use whitelist** for public servers
2. **Keep server updated** to latest version
3. **Use strong RCON password** if enabled
4. **Don't expose bot token** in logs
5. **Monitor player activity** via dashboard
6. **Regular backups** (automatic every 30min)
7. **Firewall rules** - only allow necessary ports

---

Last updated: 2024-12-17
