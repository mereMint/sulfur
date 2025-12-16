# 🔐 VPN Setup Guide

This guide explains how to set up WireGuard VPN with Sulfur Bot for secure remote access.

## 📋 Table of Contents

- [Overview](#overview)
- [Full Tunnel Mode](#full-tunnel-mode)
- [Requirements](#requirements)
- [Server Setup](#server-setup)
- [Adding Devices](#adding-devices)
- [Platform-Specific Setup](#platform-specific-setup)
  - [Windows](#windows)
  - [Linux](#linux)
  - [Android (Non-Rooted)](#android-non-rooted)
  - [iOS](#ios)
  - [Termux](#termux)
  - [Raspberry Pi](#raspberry-pi)
- [Troubleshooting](#troubleshooting)

---

## Overview

WireGuard is a modern VPN protocol that provides:
- ✅ Excellent performance
- ✅ Strong encryption
- ✅ Simple configuration
- ✅ Cross-platform support

Sulfur Bot uses WireGuard to allow secure remote access to:
- Web dashboard (http://localhost:5000)
- Discord bot management
- Minecraft server (if configured)
- **All internet traffic** (full tunnel mode)

### Architecture

```
┌─────────────────┐         ┌─────────────────────┐         ┌──────────────┐
│   Your Device   │         │    Sulfur Bot       │         │   Internet   │
│   (VPN Client)  │◄───────►│    Server           │◄───────►│              │
│   10.0.0.2/32   │ WireGuard│    (VPN Server)    │   NAT   │              │
└─────────────────┘  :51820  │    10.0.0.1/24     │         └──────────────┘
                     (UDP)   └─────────────────────┘
```

---

## Full Tunnel Mode

By default, Sulfur Bot configures WireGuard in **full tunnel mode**, meaning:

- ✅ **All your internet traffic** goes through the VPN
- ✅ Your public IP appears as the VPN server's IP
- ✅ Traffic is encrypted end-to-end
- ✅ Protection on public WiFi networks

### How It Works

1. **Client connects** to VPN server
2. **All traffic** (not just local) is routed through the tunnel
3. **Server performs NAT** (masquerading) to forward traffic to the internet
4. **Responses come back** through the VPN tunnel

### Configuration

Client config uses:
```ini
AllowedIPs = 0.0.0.0/0, ::/0
```
This routes ALL IPv4 and IPv6 traffic through the VPN.

Server config includes:
```ini
PostUp = iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
```
This enables NAT for outbound internet access.

### Security & Privacy Considerations

⚠️ **Important**: When using full tunnel mode, understand these implications:

| Consideration | Details |
|---------------|---------|
| **Traffic Visibility** | The VPN server operator can see all your internet traffic |
| **Data Retention** | Consider what logs the server keeps (Sulfur Bot logs connections) |
| **Trust** | Only use with servers you personally control or fully trust |
| **Speed** | Your connection speed is limited by the server's internet |
| **Location** | Your apparent location is the server's location |

**Best Practices:**
1. **Self-host only** - Run the VPN server on hardware you control
2. **Keep server secure** - Regular updates, strong passwords, firewall
3. **Limit access** - Only add devices you own to the VPN
4. **Monitor connections** - Check `wg show` regularly for unknown peers
5. **Rotate keys** - Regenerate keys periodically (every 6-12 months)

**What Sulfur Bot logs:**
- Connection events (connect/disconnect times)
- Peer public keys
- No traffic content is logged

---

## Requirements

### Server (where Sulfur Bot runs)
- WireGuard installed
- Port 51820 UDP forwarded on router
- Static IP or dynamic DNS

### Clients (your devices)
- WireGuard app installed
- Configuration file from server

---

## Server Setup

### Quick Setup

1. Run the master setup wizard:
   ```bash
   python master_setup.py --vpn
   ```

2. Choose **Server** when prompted

3. Enter your public IP or domain name

4. Configure port forwarding:
   - Log into your router
   - Forward UDP port 51820 to your server's local IP

### Manual Setup

1. **Install WireGuard**

   ```bash
   # Linux/Ubuntu
   sudo apt install wireguard
   
   # Fedora
   sudo dnf install wireguard-tools
   
   # Termux
   pkg install wireguard-tools
   ```

2. **Generate server keys**
   ```bash
   cd config/wireguard
   wg genkey | tee server_private.key | wg pubkey > server_public.key
   chmod 600 server_private.key
   ```

3. **Create server configuration**
   ```bash
   nano config/wireguard/wg0.conf
   ```

   ```ini
   [Interface]
   PrivateKey = YOUR_SERVER_PRIVATE_KEY
   Address = 10.0.0.1/24
   ListenPort = 51820
   
   # Enable IP forwarding
   PostUp = sysctl -w net.ipv4.ip_forward=1
   ```

4. **Start the VPN**
   ```bash
   sudo wg-quick up config/wireguard/wg0.conf
   ```

---

## Adding Devices

### Easy Method (Recommended)

Use the Discord command:
```
/vpn add_device device_name:my_phone
```

This automatically:
1. ✅ Generates encryption keys
2. ✅ Assigns an IP address
3. ✅ Creates configuration file
4. ✅ Exports to Downloads (on Termux)
5. ✅ Generates QR code

### Manual Method

1. **Generate client keys**
   ```bash
   wg genkey | tee client_private.key | wg pubkey > client_public.key
   ```

2. **Create client configuration**
   ```ini
   [Interface]
   PrivateKey = CLIENT_PRIVATE_KEY
   Address = 10.0.0.2/32
   DNS = 1.1.1.1
   
   [Peer]
   PublicKey = SERVER_PUBLIC_KEY
   Endpoint = your-server:51820
   AllowedIPs = 0.0.0.0/0
   PersistentKeepalive = 25
   ```

3. **Add client to server**
   
   Add to `wg0.conf`:
   ```ini
   [Peer]
   PublicKey = CLIENT_PUBLIC_KEY
   AllowedIPs = 10.0.0.2/32
   ```

4. **Reload server config**
   ```bash
   wg syncconf wg0 <(wg-quick strip wg0)
   ```

---

## Platform-Specific Setup

### Windows

1. **Install WireGuard**
   - Download from [wireguard.com](https://www.wireguard.com/install/)
   - Or via Chocolatey: `choco install wireguard`

2. **Import configuration**
   - Open WireGuard application
   - Click "Import tunnel(s) from file"
   - Select your `.conf` file

3. **Connect**
   - Click "Activate"

### Linux

1. **Install WireGuard**
   ```bash
   sudo apt install wireguard
   ```

2. **Copy configuration**
   ```bash
   sudo cp client.conf /etc/wireguard/wg0.conf
   sudo chmod 600 /etc/wireguard/wg0.conf
   ```

3. **Connect**
   ```bash
   sudo wg-quick up wg0
   ```

4. **Auto-start on boot**
   ```bash
   sudo systemctl enable wg-quick@wg0
   ```

### Android (Non-Rooted)

Since Android doesn't allow kernel-level VPN without root, we use the official WireGuard app.

#### Step 1: Install WireGuard App

Download from:
- [Google Play Store](https://play.google.com/store/apps/details?id=com.wireguard.android)
- [F-Droid](https://f-droid.org/packages/com.wireguard.android/)

#### Step 2: Get Your Configuration

**Option A: Use Discord Command (Easiest)**
```
/vpn add_device device_name:my_phone
```

The bot will:
- Create your configuration
- Export it to `Download/SulfurVPN/` folder
- Generate a QR code

**Option B: Transfer Configuration File**
- Copy the `.conf` file to your phone
- Use any file transfer method (email, cloud, USB)

#### Step 3: Import Configuration

**From QR Code:**
1. Open WireGuard app
2. Tap **+** button
3. Select **Create from QR code**
4. Scan the QR code displayed by the bot

**From File:**
1. Open WireGuard app
2. Tap **+** button
3. Select **Import from file or archive**
4. Navigate to `Download/SulfurVPN/`
5. Select your configuration file

#### Step 4: Connect

1. Toggle the switch next to your VPN profile
2. Accept the VPN permission request
3. You're connected! 🎉

### iOS

1. **Install WireGuard**
   - Download from [App Store](https://apps.apple.com/us/app/wireguard/id1441195209)

2. **Import configuration**
   - Get QR code from `/vpn add_device` command
   - Tap **+** → **Create from QR code**
   - Or transfer `.conf` file via AirDrop/iCloud

3. **Connect**
   - Toggle the switch

### Termux

#### With Root Access

```bash
# Install WireGuard tools
pkg install wireguard-tools

# Copy configuration
cp client.conf ~/config/wireguard/wg0.conf

# Connect (requires root)
sudo wg-quick up ~/config/wireguard/wg0.conf
```

#### Without Root Access

Since full WireGuard requires root on Android, use the WireGuard app instead:

1. **Generate configuration in Termux**
   ```bash
   cd sulfur
   source venv/bin/activate
   python -c "
   from modules import wireguard_manager as wg
   result = await wg.add_device_easy('my_phone')
   print('Configuration exported to:', result.get('export', {}).get('shared_path'))
   "
   ```

2. **Import in WireGuard app**
   - The configuration is exported to `Download/SulfurVPN/`
   - Open WireGuard app → **+** → **Import from file**

3. **Enable storage access if needed**
   ```bash
   termux-setup-storage
   ```

### Raspberry Pi

Same as Linux, but ensure kernel module is loaded:

```bash
# Install WireGuard
sudo apt install wireguard

# Load kernel module
sudo modprobe wireguard

# Verify
lsmod | grep wireguard
```

---

## Managing Devices

### List Connected Devices

```
/vpn status
```

Or via command line:
```bash
sudo wg show
```

### Remove a Device

1. Edit server configuration
2. Remove the `[Peer]` section for that device
3. Reload: `sudo wg syncconf wg0 <(wg-quick strip wg0)`

---

## Security Best Practices

1. **Keep private keys secure**
   - Never share your private key
   - Use file permissions (chmod 600)

2. **Use strong DNS**
   - 1.1.1.1 (Cloudflare)
   - 8.8.8.8 (Google)
   - 9.9.9.9 (Quad9)

3. **Rotate keys periodically**
   - Regenerate keys every 6-12 months
   - Remove unused clients

4. **Monitor connections**
   - Check `wg show` regularly
   - Look for unknown peers

---

## Troubleshooting

### Connection Timeout

**Check:**
- Port 51820 is forwarded on router
- Server WireGuard is running
- Firewall allows UDP 51820

```bash
# Check if WireGuard is running
sudo wg show

# Check if port is listening
sudo netstat -ulnp | grep 51820
```

### Handshake Issues

If "latest handshake" never appears:

1. Verify keys are correct (public/private not swapped)
2. Check endpoint is reachable
3. Verify firewall rules

### No Internet When Connected

This typically means NAT/masquerading is not configured properly on the server.

**Check server NAT rules:**
```bash
sudo iptables -t nat -L POSTROUTING
# Should show MASQUERADE rule for your network interface
```

**Verify IP forwarding:**
```bash
cat /proc/sys/net/ipv4/ip_forward
# Should return 1
```

**Fix NAT manually:**
```bash
# Enable IP forwarding
sudo sysctl -w net.ipv4.ip_forward=1

# Add NAT rule (replace eth0 with your interface)
sudo iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
sudo iptables -A FORWARD -i wg0 -j ACCEPT
sudo iptables -A FORWARD -o wg0 -j ACCEPT
```

**Make permanent:**
```bash
# Save iptables rules
sudo apt install iptables-persistent
sudo netfilter-persistent save

# Enable IP forwarding permanently
echo "net.ipv4.ip_forward=1" | sudo tee -a /etc/sysctl.conf
```

### Can't Access Dashboard

After connecting to VPN:
- Dashboard is at: `http://10.0.0.1:5000`
- Replace `10.0.0.1` with your server's VPN IP

---

## Quick Reference

### Common Commands

| Command | Description |
|---------|-------------|
| `/vpn status` | Check VPN status |
| `/vpn add_device name` | Add new device |
| `sudo wg show` | Show WireGuard status |
| `sudo wg-quick up wg0` | Start VPN |
| `sudo wg-quick down wg0` | Stop VPN |

### Default Ports

| Service | Port | Protocol |
|---------|------|----------|
| WireGuard | 51820 | UDP |
| Web Dashboard | 5000 | TCP |
| Minecraft | 25565 | TCP |
| Voice Chat | 24454 | UDP |

---

## See Also

- [Main Documentation](../README.md)
- [Termux Setup](TERMUX.md)
- [Web Dashboard](WEB_DASHBOARD.md)
