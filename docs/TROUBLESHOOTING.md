# 🔧 Troubleshooting Guide

Solutions for common issues with Sulfur Bot.

---

## 📋 Table of Contents

- [Installation Issues](#installation-issues)
- [Bot Startup Issues](#bot-startup-issues)
- [Database Issues](#database-issues)
- [Discord Issues](#discord-issues)
- [VPN Issues](#vpn-issues)
- [Minecraft Issues](#minecraft-issues)
- [Music Player Issues](#music-player-issues)
- [Platform-Specific Issues](#platform-specific-issues)

---

## Installation Issues

### "Permission denied (publickey)" or "Authentication failed"

**Cause:** You don't have SSH key set up or GitHub authentication configured for this private repository.

**Solution - Setup SSH Key:**

1. **Generate SSH key:**
   ```bash
   ssh-keygen -t ed25519 -C "your_email@example.com"
   # Press Enter to accept default location (~/.ssh/id_ed25519)
   # Optionally set a passphrase for extra security
   ```

2. **Start SSH agent and add key:**
   ```bash
   eval "$(ssh-agent -s)"
   ssh-add ~/.ssh/id_ed25519
   ```

3. **Copy your public key:**
   ```bash
   cat ~/.ssh/id_ed25519.pub
   # Copy the entire output
   ```

4. **Add to GitHub:**
   - Go to [GitHub Settings → SSH Keys](https://github.com/settings/keys)
   - Click "New SSH key"
   - Give it a title (e.g., "My Laptop")
   - Paste your public key
   - Click "Add SSH key"

5. **Test the connection:**
   ```bash
   ssh -T git@github.com
   # Expected: "Hi username! You've successfully authenticated..."
   ```

6. **Clone with SSH URL:**
   ```bash
   git clone git@github.com:mereMint/sulfur.git
   ```

**Alternative - Use Personal Access Token:**

1. Generate token: [GitHub Settings → Personal Access Tokens](https://github.com/settings/tokens)
2. Select scope: `repo` (full control of private repositories)
3. Clone with token:
   ```bash
   git clone https://YOUR_TOKEN@github.com/mereMint/sulfur.git
   ```

**Termux-Specific:** If SSH is not installed:
```bash
pkg install openssh
ssh -V  # Verify installation
```

**Linux-Specific:** If SSH is not installed:
```bash
# Debian/Ubuntu
sudo apt install openssh-client

# Fedora/RHEL
sudo dnf install openssh-clients

# Arch Linux
sudo pacman -S openssh
```

### "ssh: command not found"

**Termux:**
```bash
pkg install openssh
```

**Linux:**
```bash
# Debian/Ubuntu
sudo apt install openssh-client

# Fedora/RHEL
sudo dnf install openssh-clients

# Arch Linux  
sudo pacman -S openssh
```

Verify installation:
```bash
ssh -V
ssh-keygen -V
```

### "404: Not Found" when running one-command install

**Error Message:**
```
irm : 404: Not Found
curl: (22) The requested URL returned error: 404
```

**Cause:** This repository is private. Raw GitHub URLs (`raw.githubusercontent.com`) don't work with private repositories because they require public access.

**Solution:**
1. Clone the repository first (requires GitHub authentication):
   ```bash
   git clone https://github.com/mereMint/sulfur.git
   cd sulfur
   ```

2. Then run the installer locally:
   ```bash
   # Linux/macOS/Termux
   bash scripts/quickinstall.sh
   
   # Windows (PowerShell)
   .\scripts\quickinstall.ps1
   ```

**Note:** The one-command install method (`irm ... | iex` or `curl ... | bash`) only works for public repositories.

### "Python not found"

**Windows:**
1. Download Python from [python.org](https://python.org)
2. Check "Add Python to PATH" during installation
3. Restart PowerShell

**Linux:**
```bash
sudo apt install python3 python3-pip python3-venv
```

**Termux:**
```bash
pkg install python python-pip
```

### "pip: command not found"

```bash
# Linux
python3 -m ensurepip --upgrade

# Termux
pkg install python-pip
```

### "Module not found" errors

```bash
# Make sure venv is activated
source venv/bin/activate  # Linux/Termux
.\venv\Scripts\Activate.ps1  # Windows

# Reinstall requirements
pip install -r requirements.txt --force-reinstall
```

### "Permission denied"

**Linux/Termux:**
```bash
chmod +x scripts/*.sh
```

**Windows:** Run PowerShell as Administrator

---

## Bot Startup Issues

### "Invalid token"

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Select your application → Bot
3. Click "Reset Token"
4. Copy new token to `.env`
5. Make sure no extra spaces or quotes

### "Intents not enabled"

1. Discord Developer Portal → Your Application → Bot
2. Enable:
   - ✅ Presence Intent
   - ✅ Server Members Intent
   - ✅ Message Content Intent
3. Save changes
4. Restart bot

### "Cannot import module"

```bash
# Check you're in the right directory
pwd  # Should show .../sulfur

# Activate virtual environment
source venv/bin/activate

# Verify installation
pip list | grep discord
```

### Bot starts but doesn't respond

1. Check bot is invited with correct permissions
2. Verify slash commands are synced (wait up to 1 hour)
3. Check logs for errors:
   ```bash
   cat logs/session_*.log | tail -100
   ```

---

## Database Issues

### "Can't connect to MySQL server"

**Check if running:**
```bash
# Linux
sudo systemctl status mysql
sudo systemctl start mysql

# Termux
ps aux | grep maria
mysqld_safe &
```

**Check credentials:**
```bash
mysql -u sulfur_bot_user -p
# Enter password from .env
```

### "Access denied for user"

1. Connect as root:
   ```bash
   sudo mysql -u root -p
   ```

2. Reset user password:
   ```sql
   ALTER USER 'sulfur_bot_user'@'localhost' IDENTIFIED BY 'new_password';
   FLUSH PRIVILEGES;
   ```

3. Update `.env` with new password

### "Database doesn't exist"

```sql
CREATE DATABASE sulfur_bot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON sulfur_bot.* TO 'sulfur_bot_user'@'localhost';
FLUSH PRIVILEGES;
```

### "Table doesn't exist"

The bot auto-creates tables. If issues persist:
```bash
python setup_database.py
```

---

## Discord Issues

### Slash commands not appearing

1. Wait up to 1 hour for global sync
2. Re-invite bot with updated permissions:
   ```
   https://discord.com/api/oauth2/authorize?client_id=YOUR_ID&permissions=8&scope=bot%20applications.commands
   ```

3. Manually sync:
   ```python
   # In bot.py, add temporarily:
   await bot.tree.sync()
   ```

### "Missing Permissions"

Ensure bot has these permissions:
- Send Messages
- Embed Links
- Attach Files
- Use External Emojis
- Connect (for voice)
- Speak (for voice)

### "Unknown Interaction"

Response took too long. The bot has 3 seconds to respond.

Check:
- Database connection speed
- API response times
- Server load

---

## VPN Issues

### "WireGuard not installed"

**Linux:**
```bash
sudo apt install wireguard wireguard-tools
```

**Termux:**
```bash
pkg install wireguard-tools
```

**Windows:**
Download from [wireguard.com](https://www.wireguard.com/install/)

### "Connection timeout"

1. Check port forwarding (UDP 51820)
2. Verify server is running:
   ```bash
   sudo wg show
   ```
3. Check firewall:
   ```bash
   sudo ufw allow 51820/udp
   ```

### "Handshake failed"

- Verify public/private keys not swapped
- Check endpoint is reachable
- Ensure clocks are synchronized

### Android: Can't find config file

```bash
# Grant storage access
termux-setup-storage

# Check file exists
ls /storage/emulated/0/Download/SulfurVPN/
```

---

## Minecraft Issues

### "Java not found"

**Linux:**
```bash
sudo apt install openjdk-21-jdk
```

**Termux:**
```bash
pkg install openjdk-21
```

**Windows:**
Download from [adoptium.net](https://adoptium.net/)

### "Java version too old"

Minecraft 1.20.5+ requires Java 21+:
```bash
java -version  # Check version
```

### Server won't start

1. Check EULA is accepted:
   ```bash
   cat minecraft_server/eula.txt
   # Should show: eula=true
   ```

2. Check logs:
   ```bash
   cat minecraft_server/logs/latest.log
   ```

3. Verify port not in use:
   ```bash
   netstat -tlnp | grep 25565
   ```

### Can't connect to server

1. Port forwarding: Forward TCP 25565
2. Firewall: `sudo ufw allow 25565/tcp`
3. Whitelist: Add yourself with `/mcwhitelist add Username`

### Voice chat not working

1. Forward UDP 24454
2. Install client mod
3. Check config:
   ```bash
   cat minecraft_server/config/voicechat/voicechat-server.properties
   ```

---

## Music Player Issues

### "FFmpeg not found"

**Linux:**
```bash
sudo apt install ffmpeg
```

**Termux:**
```bash
pkg install ffmpeg
```

**Windows:**
```powershell
choco install ffmpeg
```

### "yt-dlp not found"

```bash
pip install yt-dlp --upgrade
```

### No audio playing

1. Check bot is in voice channel
2. Verify FFmpeg installation
3. Check yt-dlp version:
   ```bash
   yt-dlp --version
   pip install yt-dlp --upgrade
   ```

### Stream keeps stopping

YouTube may block requests. Solutions:
1. Update yt-dlp: `pip install yt-dlp --upgrade`
2. Use different streams
3. Check network stability

---

## Platform-Specific Issues

### Windows: SSH key setup

**Option 1: Using Git Bash (Recommended)**
```bash
# Run in Git Bash
ssh-keygen -t ed25519 -C "your_email@example.com"
cat ~/.ssh/id_ed25519.pub
ssh -T git@github.com
```

**Option 2: Using PowerShell**
```powershell
# Check if OpenSSH is available
Get-Command ssh

# Generate key
ssh-keygen -t ed25519 -C "your_email@example.com"

# View public key
Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub

# Test connection
ssh -T git@github.com
```

**Option 3: GitHub Desktop**
- Install [GitHub Desktop](https://desktop.github.com/)
- Sign in with GitHub account
- Clone from File → Clone Repository

### Windows: PowerShell execution policy

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Windows: Long path names

```powershell
# Run as Administrator
reg add "HKLM\SYSTEM\CurrentControlSet\Control\FileSystem" /v LongPathsEnabled /t REG_DWORD /d 1 /f
```

### Linux: Permission denied on port

Ports below 1024 require root. Use higher ports or:
```bash
sudo setcap 'cap_net_bind_service=+ep' $(which python3)
```

### Linux: SSH key permissions

If SSH complains about key permissions:
```bash
chmod 700 ~/.ssh
chmod 600 ~/.ssh/id_ed25519
chmod 644 ~/.ssh/id_ed25519.pub
chmod 644 ~/.ssh/known_hosts
```

### Linux: Git asks for password repeatedly

Configure credential helper:
```bash
# Cache credentials for 1 hour
git config --global credential.helper 'cache --timeout=3600'

# Or use SSH instead of HTTPS
git remote set-url origin git@github.com:mereMint/sulfur.git
```

### Termux: SSH key issues

**Problem: SSH agent not starting**
```bash
# Install and start SSH agent
pkg install openssh
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
```

**Problem: Permission denied for SSH key**
```bash
# Fix permissions
chmod 700 ~/.ssh
chmod 600 ~/.ssh/id_ed25519
chmod 644 ~/.ssh/id_ed25519.pub
```

**Problem: Can't copy SSH key**
```bash
# Method 1: Use termux-clipboard-set (requires Termux:API)
cat ~/.ssh/id_ed25519.pub | termux-clipboard-set

# Method 2: Display and manually copy
cat ~/.ssh/id_ed25519.pub
# Long-press to select, then copy

# Method 3: Save to shared storage
cat ~/.ssh/id_ed25519.pub > /sdcard/ssh_key.txt
```

### Termux: Bot stops when screen locks

1. Acquire wakelock (from notification)
2. Disable battery optimization
3. Use screen: `screen -S sulfur`

### Termux: "storage not found"

```bash
termux-setup-storage
# Grant permission in popup
# Then restart Termux
```

### Raspberry Pi: Out of memory

1. Increase swap:
   ```bash
   sudo dphys-swapfile swapoff
   sudo nano /etc/dphys-swapfile
   # Set CONF_SWAPSIZE=1024
   sudo dphys-swapfile setup
   sudo dphys-swapfile swapon
   ```

2. Reduce memory usage in configs

---

## Getting Help

### Gather Information

Before asking for help, collect:

```bash
# Python version
python --version

# OS info
uname -a  # Linux/Termux
winver    # Windows

# Error logs
cat logs/session_*.log | tail -200
```

### Check Logs

```bash
# Recent bot logs
ls -la logs/

# View latest log
cat logs/session_LATEST.log
```

### Report Issues

Open an issue on [GitHub](https://github.com/mereMint/sulfur/issues) with:
1. Platform and version
2. Steps to reproduce
3. Error messages
4. Log excerpts

---

## See Also

- [Quick Start](QUICKSTART.md)
- [FAQ](FAQ.md)
- [Platform Guides](WIKI.md#platform-specific-guides)
