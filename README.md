# 🤖 Sulfur Discord Bot

A feature-rich Discord bot with AI capabilities, economy system, mini-games, WireGuard VPN management, and comprehensive management tools.

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![discord.py](https://img.shields.io/badge/discord.py-2.4+-blue.svg)](https://github.com/Rapptz/discord.py)

---

## ⚡ Highlights

- 🎮 **Complete Game Suite** - Werwolf, Blackjack, Roulette, Mines, Tower, Russian Roulette, Detective
- 💰 **Full Economy System** - Virtual currency, shop, daily rewards, quests, stock market
- 🤖 **Advanced AI** - Multi-model support (Gemini, OpenAI), vision capabilities
- 🎵 **Music & Sounds Player** - Stream lofi, ambient sounds, no-copyright music, and Spotify-based mixes
- 📊 **Web Dashboard** - Real-time monitoring, AI usage tracking, database management
- 🔐 **WireGuard VPN** - Secure remote access with cross-platform support
- 🔧 **Zero Maintenance** - Auto-updates, auto-backups, self-healing scripts
- 📱 **Cross-Platform** - Windows, Linux, Android/Termux, Raspberry Pi support

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
- 🔐 **VPN** - WireGuard VPN status and management
- ⚙️ **Other** - News, Privacy, Wrapped statistics

---

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Detailed Installation Guide](#-detailed-installation-guide)
- [WireGuard VPN Setup](#-wireguard-vpn-setup-in-depth-tutorial)
- [Features](#-features)
- [Configuration](#%EF%B8%8F-configuration)
- [Running the Bot](#-running-the-bot)
- [Web Dashboard](#-web-dashboard)
- [Troubleshooting](#-common-issues)

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

## 📖 Detailed Installation Guide

This section provides step-by-step instructions for installing Sulfur Bot on different platforms. Choose your platform below.

### 🪟 Windows - Complete Installation

#### Step 1: Install Prerequisites

**Option A: Using the Automated Installer (Recommended)**

Run as Administrator in PowerShell:
```powershell
# Navigate to the sulfur directory
cd sulfur

# Run the Windows installer script
.\scripts\install_windows.ps1
```

The installer will automatically:
- Install Chocolatey package manager (if not present)
- Install Python 3.8+
- Install Git
- Install MySQL
- Install Java (optional, for Minecraft server)
- Install WireGuard (optional)
- Install FFmpeg (for voice features)
- Set up the Python virtual environment
- Install all Python dependencies

**Option B: Manual Installation**

1. **Install Python 3.8+**
   - Download from [python.org](https://www.python.org/downloads/)
   - ✅ Check "Add Python to PATH" during installation
   - Verify: `python --version`

2. **Install MySQL**
   - Download MySQL Installer from [dev.mysql.com](https://dev.mysql.com/downloads/installer/)
   - Run the installer and select "MySQL Server" and "MySQL Workbench"
   - Set a root password during setup
   - Verify: `mysql --version`

3. **Install Git**
   - Download from [git-scm.com](https://git-scm.com/download/win)
   - Use default installation options
   - Verify: `git --version`

4. **Install FFmpeg (for voice/music features)**
   - Download from [ffmpeg.org](https://ffmpeg.org/download.html) or use Chocolatey:
     ```powershell
     choco install ffmpeg
     ```

5. **Clone and Setup**
   ```powershell
   git clone https://github.com/mereMint/sulfur.git
   cd sulfur
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

#### Step 2: Configure the Bot

1. Create `.env` file:
   ```powershell
   copy .env.example .env
   notepad .env
   ```

2. Fill in your configuration (see [Configuration](#%EF%B8%8F-configuration) section)

#### Step 3: Run Setup Wizard

```powershell
python master_setup.py
```

This interactive wizard will:
- Verify all dependencies
- Set up the database
- Configure WireGuard VPN (optional)
- Create necessary configuration files

---

### 🐧 Linux - Complete Installation

#### Step 1: Install Prerequisites

**Option A: Using the Automated Installer (Recommended)**

```bash
# Clone the repository first
git clone https://github.com/mereMint/sulfur.git
cd sulfur

# Run the Linux installer script
chmod +x scripts/install_linux.sh
./scripts/install_linux.sh
```

The installer supports:
- Debian/Ubuntu (apt)
- Fedora/RHEL (dnf)
- Arch Linux (pacman)
- Raspberry Pi OS

**Option B: Manual Installation (Debian/Ubuntu)**

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python
sudo apt install -y python3 python3-pip python3-venv

# Install MariaDB
sudo apt install -y mariadb-server mariadb-client
sudo systemctl start mariadb
sudo systemctl enable mariadb

# Install Git and other dependencies
sudo apt install -y git ffmpeg libffi-dev libnacl-dev libopus0 screen

# Clone and setup
git clone https://github.com/mereMint/sulfur.git
cd sulfur
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Step 2: Secure MySQL/MariaDB

```bash
sudo mysql_secure_installation
```

Follow the prompts to:
- Set root password
- Remove anonymous users
- Disallow root login remotely
- Remove test database

#### Step 3: Create Database and User

```bash
sudo mysql -u root -p
```

```sql
CREATE DATABASE sulfur_bot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'sulfur_bot_user'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON sulfur_bot.* TO 'sulfur_bot_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

#### Step 4: Configure and Run

```bash
# Create .env file
cp .env.example .env
nano .env  # Fill in your configuration

# Run setup wizard
source venv/bin/activate
python master_setup.py

# Start the bot
python bot.py
```

#### Step 5: Create Systemd Service (Optional)

For auto-start on boot:

```bash
sudo tee /etc/systemd/system/sulfur-bot.service > /dev/null << EOF
[Unit]
Description=Sulfur Discord Bot
After=network.target mariadb.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/venv/bin/python $(pwd)/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable sulfur-bot
sudo systemctl start sulfur-bot
```

---

### 📱 Termux/Android - Complete Installation

#### Step 1: Prepare Termux

1. **Install Termux** from [F-Droid](https://f-droid.org/packages/com.termux/) (recommended over Play Store)

2. **Grant Storage Permission**
   ```bash
   termux-setup-storage
   ```
   Grant the permission when prompted.

3. **Update Packages**
   ```bash
   pkg update && pkg upgrade -y
   ```

#### Step 2: Install Dependencies

**Option A: Using the Automated Installer (Recommended)**

```bash
# Clone the repository
pkg install -y git
git clone https://github.com/mereMint/sulfur.git
cd sulfur

# Run the Termux installer script
chmod +x scripts/install_termux.sh
./scripts/install_termux.sh
```

**Option B: Manual Installation**

```bash
# Install core packages
pkg install -y python python-pip git mariadb

# Install optional packages
pkg install -y ffmpeg libffi opus screen curl wget openssl

# For Minecraft server (optional)
pkg install -y openjdk-21

# For WireGuard (limited without root)
pkg install -y wireguard-tools
```

#### Step 3: Initialize and Start MariaDB

```bash
# Initialize the database
mysql_install_db

# Start MariaDB (run this after every Termux restart)
mysqld_safe &

# Wait for it to start
sleep 3

# Secure the installation
mysql_secure_installation
```

#### Step 4: Create Database

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

#### Step 5: Setup Python Environment

```bash
cd sulfur
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### Step 6: Configure and Run

```bash
# Create .env file
cp .env.example .env
nano .env  # Fill in your configuration

# Run setup wizard
python master_setup.py

# Start the bot
python bot.py
```

#### Termux Tips

- **Keep Termux Running**: Pull down notification shade and tap "Acquire wakelock"
- **Disable Battery Optimization**: Settings > Apps > Termux > Battery > Unrestricted
- **Auto-Start on Boot**: Install [Termux:Boot](https://f-droid.org/packages/com.termux.boot/) from F-Droid
- **Start MariaDB After Reboot**: `mysqld_safe &`

---

### 🍓 Raspberry Pi - Complete Installation

Follow the Linux installation guide above. Additional notes for Raspberry Pi:

```bash
# Install WireGuard with kernel module
sudo apt install -y wireguard
sudo modprobe wireguard

# For better performance, consider using a 64-bit OS
# Raspberry Pi OS Lite (64-bit) is recommended

# Increase swap if needed (for large Python packages)
sudo dphys-swapfile swapoff
sudo sed -i 's/CONF_SWAPSIZE=100/CONF_SWAPSIZE=1024/' /etc/dphys-swapfile
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

---

## 🔐 WireGuard VPN Setup (In-Depth Tutorial)

WireGuard is a modern, high-performance VPN protocol that Sulfur Bot uses to provide secure remote access to the bot's web dashboard and services. This section provides a comprehensive guide to setting up WireGuard on all supported platforms.

### What is WireGuard?

WireGuard is a lightweight VPN that:
- Uses state-of-the-art cryptography
- Has a minimal attack surface (~4,000 lines of code)
- Provides better performance than OpenVPN or IPSec
- Is built into the Linux kernel (5.6+)

### When Do You Need WireGuard?

You need WireGuard if you want to:
- Access your Sulfur Bot's web dashboard from outside your local network
- Securely manage your bot remotely
- Connect multiple devices to your bot server
- Use your bot server as a VPN exit point

### Architecture Overview

```
┌─────────────────┐         ┌─────────────────────┐
│   Your Phone    │         │    Sulfur Bot       │
│   or Computer   │◄───────►│    Server           │
│   (VPN Client)  │ WireGuard│    (VPN Server)    │
│   10.0.0.2/32   │ Tunnel   │    10.0.0.1/24     │
└─────────────────┘  :51820  └─────────────────────┘
                     (UDP)
```

---

### 🪟 WireGuard on Windows

#### Step 1: Install WireGuard

**Option A: Using Chocolatey (Recommended)**
```powershell
# Run as Administrator
choco install wireguard -y
```

**Option B: Manual Installation**
1. Download the installer from [wireguard.com/install](https://www.wireguard.com/install/)
2. Run the installer
3. Restart your computer if prompted

#### Step 2: Verify Installation

```powershell
# Check if WireGuard is installed
wg --version
# Should output: wireguard-tools v1.x.x
```

#### Step 3: Configure WireGuard via Sulfur Bot

Run the master setup wizard:
```powershell
.\venv\Scripts\Activate.ps1
python master_setup.py
```

Select "WireGuard VPN" when prompted and choose your role:
- **Server**: If this machine will accept VPN connections
- **Client**: If this machine will connect to a VPN server

#### Step 4: Server Setup (Windows)

If setting up as a server:

1. **Enter your public IP or domain name** - This is how clients will connect to you
   - Find your public IP: Visit [whatismyip.com](https://www.whatismyip.com/)
   - Or use a dynamic DNS service like [noip.com](https://www.noip.com/)

2. **Configure your VPN network**:
   - Default: `10.0.0.1/24` (server will be 10.0.0.1)
   - Clients will get 10.0.0.2, 10.0.0.3, etc.

3. **Set the port**:
   - Default: `51820` (UDP)
   - Make sure to forward this port on your router!

4. **Port Forwarding on Router**:
   - Log into your router (usually 192.168.1.1 or 192.168.0.1)
   - Find "Port Forwarding" or "NAT" settings
   - Forward UDP port 51820 to your server's local IP

#### Step 5: Client Setup (Windows)

If setting up as a client:

1. **Get server information** from your server admin:
   - Server public key
   - Server endpoint (IP:port)
   - Your assigned VPN IP address

2. **Enter the configuration** in the setup wizard

3. **Import the configuration**:
   - Open WireGuard application
   - Click "Import tunnel(s) from file"
   - Select `config/wireguard/client_*.conf`

4. **Activate the tunnel**:
   - Click "Activate" in the WireGuard app

---

### 🐧 WireGuard on Linux

#### Step 1: Install WireGuard

**Debian/Ubuntu:**
```bash
sudo apt update
sudo apt install -y wireguard wireguard-tools
```

**Fedora:**
```bash
sudo dnf install -y wireguard-tools
```

**Arch Linux:**
```bash
sudo pacman -S wireguard-tools
```

#### Step 2: Verify Installation

```bash
# Check installation
wg --version

# Check if kernel module is loaded
lsmod | grep wireguard

# Load module if needed
sudo modprobe wireguard
```

#### Step 3: Server Setup (Linux)

##### 3.1: Generate Server Keys

```bash
# Create config directory
sudo mkdir -p /etc/wireguard
cd /etc/wireguard

# Generate private key
wg genkey | sudo tee server_private.key
sudo chmod 600 server_private.key

# Generate public key from private key
sudo cat server_private.key | wg pubkey | sudo tee server_public.key
```

##### 3.2: Create Server Configuration

```bash
sudo nano /etc/wireguard/wg0.conf
```

Add the following configuration:

```ini
[Interface]
# Sulfur Bot WireGuard Server
PrivateKey = YOUR_SERVER_PRIVATE_KEY_HERE
Address = 10.0.0.1/24
ListenPort = 51820

# Enable IP forwarding when interface is up
PostUp = sysctl -w net.ipv4.ip_forward=1
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT
PostUp = iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT
PostDown = iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

# Add peers below (one [Peer] section for each client)
```

Replace:
- `YOUR_SERVER_PRIVATE_KEY_HERE` (the entire placeholder) with contents of `server_private.key`
- `eth0` with your actual network interface name (check with `ip link`)

##### 3.3: Set Permissions

```bash
sudo chmod 600 /etc/wireguard/wg0.conf
```

##### 3.4: Enable IP Forwarding Permanently

```bash
# Enable IP forwarding
echo "net.ipv4.ip_forward=1" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

##### 3.5: Configure Firewall

```bash
# Allow WireGuard port
sudo ufw allow 51820/udp

# Allow forwarding
sudo ufw route allow in on wg0 out on eth0
```

##### 3.6: Start WireGuard

```bash
# Start the interface
sudo wg-quick up wg0

# Enable on boot
sudo systemctl enable wg-quick@wg0
```

#### Step 4: Adding Clients (Linux Server)

For each client device:

##### 4.1: Generate Client Keys

```bash
# On the server or client machine
wg genkey | tee client1_private.key
cat client1_private.key | wg pubkey | tee client1_public.key
```

##### 4.2: Add Client to Server Config

```bash
sudo nano /etc/wireguard/wg0.conf
```

Add at the end:

```ini
[Peer]
# Client 1 - Phone
PublicKey = CLIENT_PUBLIC_KEY_HERE
AllowedIPs = 10.0.0.2/32
```

##### 4.3: Create Client Configuration File

Create `client1.conf`:

```ini
[Interface]
PrivateKey = CLIENT_PRIVATE_KEY_HERE
Address = 10.0.0.2/32
DNS = 1.1.1.1, 8.8.8.8

[Peer]
PublicKey = SERVER_PUBLIC_KEY_HERE
Endpoint = your-server-ip:51820
# Route all traffic through VPN (full tunnel)
# For security, you may prefer to only route the VPN subnet: AllowedIPs = 10.0.0.0/24
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25
```

> ⚠️ **Security Note**: Setting `AllowedIPs = 0.0.0.0/0, ::/0` routes ALL traffic through the VPN server. This means the VPN server can see all your internet traffic. Only use this if you trust the server. For accessing only the bot's web dashboard, use `AllowedIPs = 10.0.0.0/24` instead.

##### 4.4: Reload Server Config

```bash
sudo wg-quick down wg0 && sudo wg-quick up wg0
# Or without downtime:
sudo wg syncconf wg0 <(wg-quick strip wg0)
```

#### Step 5: Check Status

```bash
# View WireGuard status
sudo wg show

# View interface status
sudo wg show wg0

# Check if tunnel is working
ping 10.0.0.1  # From client
ping 10.0.0.2  # From server
```

---

### 📱 WireGuard on Termux/Android

> ⚠️ **Important**: Full WireGuard VPN functionality on Termux requires **root access**. For non-rooted devices, use the official WireGuard Android app instead.

#### Option A: WireGuard Android App (Recommended for Non-Root)

1. **Install the App**:
   - Download [WireGuard from Play Store](https://play.google.com/store/apps/details?id=com.wireguard.android)
   - Or from [F-Droid](https://f-droid.org/packages/com.wireguard.android/)

2. **Import Configuration**:
   - Get your client configuration file from the server admin
   - In the app, tap "+" and select "Import from file or archive"
   - Select your `.conf` file

3. **Connect**:
   - Toggle the switch to enable the VPN

#### Option B: Termux with Root Access

```bash
# Update packages
pkg update && pkg upgrade -y

# Install WireGuard tools
pkg install wireguard-tools

# Create config directory
mkdir -p ~/config/wireguard

# Create your client configuration
nano ~/config/wireguard/wg0.conf
```

Add your client configuration (same format as Linux client).

```bash
# Bring up the tunnel (requires root)
sudo wg-quick up ~/config/wireguard/wg0.conf

# Check status
sudo wg show
```

#### Option C: Generate Keys in Termux (for Server Admin)

Even without root, you can use Termux to generate WireGuard keys:

```bash
# Install WireGuard tools
pkg install wireguard-tools

# Generate keypair
wg genkey | tee privatekey | wg pubkey > publickey

# View the keys
echo "Private Key: $(cat privatekey)"
echo "Public Key: $(cat publickey)"
```

Send the public key to your server admin to add you as a peer.

---

### 🍓 WireGuard on Raspberry Pi

Raspberry Pi works like a standard Linux system, but with some specific optimizations.

#### Step 1: Install WireGuard

```bash
sudo apt update
sudo apt install -y wireguard wireguard-tools

# Load the kernel module
sudo modprobe wireguard

# Verify
wg --version
lsmod | grep wireguard
```

#### Step 2: Generate Keys

```bash
cd /etc/wireguard
wg genkey | sudo tee privatekey | wg pubkey | sudo tee publickey
sudo chmod 600 privatekey
```

#### Step 3: Create Configuration

```bash
sudo nano /etc/wireguard/wg0.conf
```

Server configuration (same as Linux above).

#### Step 4: Start and Enable

```bash
# Start WireGuard
sudo wg-quick up wg0

# Enable on boot
sudo systemctl enable wg-quick@wg0

# Check status
sudo wg show
```

#### Raspberry Pi Specific Notes

- **Performance**: WireGuard runs well even on Raspberry Pi Zero
- **Power**: Consider using a good power supply for stable operation
- **Cooling**: If running 24/7, passive cooling is recommended for Pi 4

---

### 🔧 Troubleshooting WireGuard

#### Common Issues

**1. Connection Refused / Timeout**
```bash
# Check if WireGuard is running
sudo wg show

# Check if port is open
sudo netstat -ulnp | grep 51820

# Check firewall
sudo ufw status
sudo iptables -L -n
```

**2. No Internet Through VPN**
```bash
# Check IP forwarding
cat /proc/sys/net/ipv4/ip_forward  # Should be 1

# Check NAT rules
sudo iptables -t nat -L POSTROUTING

# Check DNS
nslookup google.com
```

**3. Handshake Issues**
```bash
# Check if keys match
sudo wg show  # Look at "latest handshake"

# If no handshake, verify:
# - Server is reachable (try ping)
# - Port is forwarded correctly
# - Keys are correct (public/private not swapped)
```

**4. Windows: WireGuard Service Won't Start**
```powershell
# Run as Administrator
net stop WireGuardTunnel$wg0
net start WireGuardTunnel$wg0

# Or restart the WireGuard service
Restart-Service WireGuardManager
```

#### Debugging Commands

```bash
# Linux - Watch WireGuard logs
sudo journalctl -fu wg-quick@wg0

# Show detailed interface info
sudo wg show wg0

# Monitor traffic
sudo tcpdump -i wg0

# Check routing
ip route show
```

---

### 🔒 Security Best Practices

1. **Keep private keys secure**
   - Never share your private key
   - Use file permissions (chmod 600)
   - Store backups encrypted

2. **Use strong DNS**
   - Consider using DNS over HTTPS
   - Use reputable DNS providers (1.1.1.1, 8.8.8.8, 9.9.9.9)

3. **Regularly rotate keys**
   - Generate new keys every 6-12 months
   - Remove unused client configurations

4. **Monitor connections**
   - Check `sudo wg show` regularly
   - Look for unknown peers or unusual traffic

5. **Firewall the server**
   - Only allow necessary ports
   - Use fail2ban for SSH protection
   - Consider rate limiting

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
