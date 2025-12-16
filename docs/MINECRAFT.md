# 🎮 Minecraft Server Guide

This guide covers setting up and managing a Minecraft server with Sulfur Bot, including modpack installation and voice chat configuration.

## 📋 Table of Contents

- [Overview](#overview)
- [Requirements](#requirements)
- [Installation](#installation)
- [Server Types](#server-types)
- [AutoModpack (Beginner Friendly)](#automodpack-beginner-friendly)
- [Mods & Modpacks](#mods--modpacks)
- [Voice Chat Setup](#voice-chat-setup)
- [Server Management](#server-management)
- [Backups](#backups)
- [Troubleshooting](#troubleshooting)

---

## Overview

Sulfur Bot includes full Minecraft server management with:

- ✅ Multiple server types (Paper, Purpur, Fabric, Vanilla)
- ✅ **AutoModpack** - Automatic mod syncing for players (no manual installation!)
- ✅ Automatic mod downloads from Modrinth
- ✅ Simple Voice Chat integration
- ✅ Performance optimization mods
- ✅ Scheduled operation (6am-10pm, weekends, etc.)
- ✅ Automatic backups
- ✅ Discord integration for commands

---

## Requirements

### Minimum Requirements

| Component | Requirement |
|-----------|-------------|
| Java | 21+ (for MC 1.20.5+) |
| RAM | 2GB minimum, 4GB+ recommended |
| Storage | 5GB+ |
| Network | Port 25565 open |

### Platform-Specific

**Termux/Android:**
- Works but limited RAM may affect performance
- Consider using a lightweight server (Purpur)

**Raspberry Pi:**
- Pi 4 with 4GB+ recommended
- Use 64-bit OS for best performance

---

## Installation

### Quick Setup

1. Run the setup wizard:
   ```bash
   python master_setup.py --minecraft
   ```

2. Choose your setup type:
   - **Standard Server** - Choose server type (Paper, Purpur, Vanilla, Fabric)
   - **🍓 Raspberry Flavoured** - Vanilla+ with quality of life improvements
   - **😴 Melatonin** - Maximum performance, minimal mods
   - **🏠 Homestead** - Cozy survival with farms, building, decoration

3. Configure memory and schedule

4. Start playing!

### Pre-Configured Modpacks

Modpacks are downloaded directly from Modrinth or CurseForge - always getting the latest version!

| Modpack | Source | Description | Best For |
|---------|--------|-------------|----------|
| 🍓 **Raspberry Flavoured** | [CurseForge](https://www.curseforge.com/minecraft/modpacks/raspberry-flavoured) | Vanilla+ with QoL improvements | Enhanced vanilla experience |
| 😴 **Melatonin** | [Modrinth](https://modrinth.com/modpack/melatonin) | Maximum FPS, performance optimized | Low-end hardware |
| 🏠 **Homestead Cozy** | [CurseForge](https://www.curseforge.com/minecraft/modpacks/homestead-cozy) | Farming, building, cozy vibes | Builders, farmers |

All modpacks include:
- ✅ AutoModpack (players auto-download mods)
- ✅ Automatic updates to latest version
- ✅ World save/restore when switching

### CurseForge API Key

For CurseForge modpacks (Raspberry Flavoured, Homestead), you need an API key:

1. Get a key from [CurseForge Console](https://console.curseforge.com/)
2. Add to your `.env` file:
   ```
   CURSEFORGE_API_KEY=your_key_here
   ```

Without an API key, you'll need to download CurseForge modpacks manually.

### Manual Setup

1. **Configure in config.json**
   ```json
   {
     "modules": {
       "minecraft": {
         "enabled": true,
         "server_type": "fabric",
         "modpack": {
           "enabled": true,
           "name": "melatonin",
           "auto_install": true
         }
       }
     }
   }
   ```

2. **Download server**
   Use Discord command: `/mcsetup`

3. **Accept EULA**
   The bot automatically accepts the Minecraft EULA on first start.

---

## Switching Modpacks

You can switch between modpacks at any time. The system automatically:
1. ✅ Saves your current world
2. ✅ Clears existing mods
3. ✅ Loads saved world for new modpack (or generates new)
4. ✅ Installs new modpack mods
5. ✅ Configures AutoModpack

### Via Discord
```
/mcmodpack switch modpack:homestead
```

### Via Command Line
```python
from modules.minecraft_server import switch_modpack
result = await switch_modpack('homestead', config)
```

### World Management

Each modpack has its own world save:
- `minecraft_worlds/vanilla/` - Vanilla world
- `minecraft_worlds/raspberry_flavoured/` - Raspberry Flavoured world
- `minecraft_worlds/melatonin/` - Melatonin world
- `minecraft_worlds/homestead/` - Homestead world

Switching modpacks automatically swaps worlds!

---

## Server Types

### Paper (Recommended)
- High performance
- Plugin support
- Built-in optimizations
- Great for survival servers

### Purpur
- Paper fork with extra features
- Even more configuration options
- Gameplay tweaks available

### Fabric
- Lightweight mod loader
- Performance mods available
- Client-side mod compatibility

### Vanilla
- Official Minecraft server
- No modifications
- Purest experience

---

## AutoModpack (Beginner Friendly)

**AutoModpack** is the easiest way to manage mods for your players. When enabled, players automatically download all server mods when they connect - no manual installation required!

### How It Works

```
┌──────────────────┐         ┌──────────────────┐
│   Player joins   │         │     Server       │
│   with only      │────────►│   with mods      │
│   AutoModpack    │         │                  │
└──────────────────┘         └──────────────────┘
         │                            │
         │     AutoModpack syncs      │
         │◄───────────────────────────│
         │        all mods            │
         ▼                            
┌──────────────────┐
│  Player ready!   │
│  All mods        │
│  installed       │
└──────────────────┘
```

### Benefits

| Feature | Benefit |
|---------|---------|
| ✅ Automatic | No manual mod installation |
| ✅ Always in sync | Server updates = client updates |
| ✅ Easy for beginners | Players only install one mod |
| ✅ Works with all mods | Including voice chat |

### Player Setup (One-Time)

Players only need to do this once:

1. **Install Fabric Loader**
   - Download from [fabricmc.net](https://fabricmc.net/use/installer/)

2. **Install AutoModpack**
   - Download from [Modrinth](https://modrinth.com/mod/automodpack)
   - Put in `.minecraft/mods/` folder

3. **Connect to server**
   - AutoModpack does the rest!

### Server Configuration

AutoModpack is **enabled by default** when using Fabric server type.

```json
{
  "optional_mods": {
    "automodpack": {
      "enabled": true,
      "beginner_friendly": true
    }
  }
}
```

### Advanced Configuration

Edit `minecraft_server/automodpack/automodpack-server.json`:

```json
{
  "modpackName": "My Server Modpack",
  "hostPort": 30037,
  "syncedFiles": ["/mods/", "/config/"],
  "excludeSyncedFiles": ["*.txt", "*.log"],
  "generateModpackOnStart": true
}
```

### Port Forwarding

AutoModpack uses port **30037 TCP** by default. Forward this port if players connect from outside your network.

---

## Mods & Modpacks

### Performance Mods

The bot can automatically download performance mods:

| Mod | Purpose |
|-----|---------|
| Lithium | General optimization |
| Ferritecore | Memory optimization |
| Starlight | Lighting optimization |
| Krypton | Network optimization |
| C2ME | Chunk generation |
| Spark | Performance profiler |

**Enable automatic installation:**
```json
{
  "performance_mods": {
    "enabled": true
  }
}
```

### Installing Mods

Use Discord command:
```
/mcmods install mod_name:lithium
```

Or automatically during setup:
```python
from modules.minecraft_server import download_performance_mods
await download_performance_mods("1.21.4", "fabric")
```

### Updating Mods

Check for updates:
```
/mcmods check_updates
```

Update all mods:
```
/mcmods update_all
```

---

## Voice Chat Setup

### Simple Voice Chat

Sulfur Bot includes automatic configuration for [Simple Voice Chat](https://modrinth.com/plugin/simple-voice-chat), a proximity voice chat mod.

### Automatic Setup

1. Enable in config:
   ```json
   {
     "optional_mods": {
       "simple_voice_chat": {
         "enabled": true
       }
     }
   }
   ```

2. The bot will:
   - Download the server mod
   - Create optimal configuration
   - Configure the voice port

### Voice Chat Settings

Default configuration (auto-generated):

| Setting | Default | Description |
|---------|---------|-------------|
| port | 24454 | Voice chat UDP port |
| max_voice_distance | 48 | Hearing range in blocks |
| whisper_distance_multiplier | 0.5 | Whisper range |
| crouch_distance_multiplier | 1.0 | Crouch modifier |
| codec | OPUS | Audio codec |

### Port Forwarding

**Important:** Forward UDP port 24454 for voice chat to work externally.

### Client Setup

Players need to install the Simple Voice Chat mod on their client:
- [Modrinth](https://modrinth.com/plugin/simple-voice-chat)
- [CurseForge](https://www.curseforge.com/minecraft/mc-mods/simple-voice-chat)

---

## Server Management

### Discord Commands

| Command | Description |
|---------|-------------|
| `/mcstart` | Start the server |
| `/mcstop` | Stop the server |
| `/mcrestart` | Restart the server |
| `/mcstatus` | Show server status |
| `/mcconsole [command]` | Send console command |
| `/mcwhitelist add [player]` | Add to whitelist |
| `/mcplayers` | List online players |

### Schedule Configuration

Configure when the server runs:

```json
{
  "schedule": {
    "mode": "timed",
    "start_hour": 6,
    "end_hour": 22
  }
}
```

**Available modes:**
- `always` - 24/7 operation
- `timed` - Specific hours daily
- `weekdays_only` - Mon-Fri with hours
- `weekends_only` - Sat-Sun with hours
- `custom` - Per-day configuration

### Whitelist Management

Enable whitelist:
```json
{
  "whitelist": true
}
```

Add players:
```
/mcwhitelist add PlayerName
```

---

## Backups

### Automatic Backups

Enabled by default:
```json
{
  "backups": {
    "enabled": true,
    "interval_hours": 6,
    "max_backups": 10,
    "include_configs": true
  }
}
```

### Manual Backup

```
/mcbackup create
```

### Restore Backup

```
/mcbackup restore backup_2024xxxx.zip
```

### Backup Contents

- World files (`world/`, `world_nether/`, `world_the_end/`)
- Server configs (`server.properties`, `whitelist.json`)
- Optionally: mods and plugin configs

---

## Web Dashboard Integration

Access Minecraft controls at `http://localhost:5000/minecraft`:

- Real-time console output
- Player list
- Start/Stop/Restart buttons
- Backup management
- Mod updates

---

## Performance Tips

### Memory Allocation

**Termux (Android):**
```json
{
  "memory_min": "512M",
  "memory_max": "1536M"
}
```

**Raspberry Pi 4:**
```json
{
  "memory_min": "1G",
  "memory_max": "2G"
}
```

**Desktop/Server:**
```json
{
  "memory_min": "2G",
  "memory_max": "8G"
}
```

### Aikar's Flags

The bot automatically uses [Aikar's optimized JVM flags](https://aikar.co/2018/07/02/tuning-the-jvm-g1gc-garbage-collector-flags-for-minecraft/) for best performance.

### View Distance

For low-power devices, reduce view distance in `server.properties`:
```properties
view-distance=8
simulation-distance=6
```

---

## Troubleshooting

### Server Won't Start

**Check Java version:**
```bash
java -version
```
Must be Java 21+ for MC 1.20.5+

**Check memory:**
Ensure you have enough free RAM

**Check logs:**
```bash
cat minecraft_server/logs/latest.log
```

### Can't Connect

**Port not open:**
- Forward port 25565 TCP on router
- Check firewall: `sudo ufw allow 25565/tcp`

**Whitelist:**
Make sure you're on the whitelist

### Voice Chat Not Working

**Port 24454:**
- Forward UDP port 24454
- Check `config/voicechat/voicechat-server.properties`

**Client mod:**
- Ensure client has Simple Voice Chat installed
- Version must match server

### Performance Issues

1. Use Paper/Purpur instead of Vanilla
2. Install performance mods
3. Reduce view distance
4. Close unused applications

---

## File Locations

| File/Directory | Purpose |
|----------------|---------|
| `minecraft_server/` | Main server directory |
| `minecraft_server/mods/` | Server mods |
| `minecraft_server/world/` | World data |
| `minecraft_server/server.properties` | Server config |
| `minecraft_backups/` | Backup files |
| `config/minecraft_state.json` | Bot state |

---

## See Also

- [Main Documentation](../README.md)
- [VPN Guide](VPN_GUIDE.md) - For remote access
- [Termux Setup](TERMUX.md) - For Android hosting
