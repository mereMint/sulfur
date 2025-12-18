"""
Minecraft Server Manager Module for Sulfur Bot

Comprehensive Minecraft server management with support for:
- Multiple server types (Vanilla, Paper, Purpur, Fabric)
- Modpack support (Raspberry Flavoured, Melatonin, Homestead)
- Auto-backup system
- Schedule-based operation (always on, 6-22, weekdays, etc.)
- Discord integration for admin commands
- Cross-platform support (Termux, Linux, Windows, Raspberry Pi)
"""

import asyncio
import json
import os
import platform
import shutil
import subprocess
import time
import re
import traceback
import zipfile
import urllib.request
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Tuple, Callable
from collections import deque
from modules.logger_utils import minecraft_logger as logger

# ==============================================================================
# Configuration Constants
# ==============================================================================

MC_SERVER_DIR = "minecraft_server"
MC_BACKUPS_DIR = "minecraft_backups"
MC_MODS_DIR = os.path.join(MC_SERVER_DIR, "mods")
MC_CONFIG_DIR = os.path.join(MC_SERVER_DIR, "config")
MC_WORLDS_DIR = os.path.join(MC_SERVER_DIR, "world")
MC_WORLDS_STORAGE_DIR = "minecraft_worlds"  # Store worlds for different modpacks
MC_PLUGINS_DIR = os.path.join(MC_SERVER_DIR, "plugins")
MC_STATE_FILE = "config/minecraft_state.json"

# Download progress update interval (seconds)
DOWNLOAD_PROGRESS_UPDATE_INTERVAL = 1.0

# Default server configuration
DEFAULT_MC_CONFIG = {
    "enabled": True,
    "server_type": "paper",  # vanilla, paper, purpur, fabric
    "minecraft_version": "1.21.11",  # Updated to latest stable version
    "memory_min": "1G",
    "memory_max": "4G",
    "port": 25565,
    "rcon_port": 25575,
    "rcon_password": None,  # Auto-generated if None
    "motd": "Sulfur Bot Minecraft Server",
    "max_players": 20,
    "online_mode": True,  # Require valid Minecraft accounts
    "difficulty": "normal",
    "gamemode": "survival",
    "pvp": True,
    "spawn_protection": 0,
    "whitelist": True,
    
    # Schedule configuration
    "schedule": {
        "mode": "always",  # always, timed, weekdays_only, weekends_only, custom
        "start_hour": 6,
        "end_hour": 22,
        "weekday_hours": {"start": 6, "end": 22},  # Mon-Fri
        "weekend_hours": {"start": 0, "end": 24},  # Sat-Sun (24h)
        "custom_schedule": {}  # Day-specific overrides
    },
    
    # Performance mods (for Paper/Purpur/Fabric)
    "performance_mods": {
        "enabled": True,
        "mods": [
            "lithium",      # General optimization
            "starlight",    # Lighting optimization (Fabric only, Paper has this built-in)
            "ferritecore",  # Memory optimization
            "spark",        # Profiler and performance monitor
        ]
    },
    
    # Optional mods
    "optional_mods": {
        "simple_voice_chat": {
            "enabled": False,
            "requires_client_mod": True
        }
    },
    
    # Modpack configuration
    "modpack": {
        "enabled": False,
        "name": None,  # raspberry_flavoured, melatonin, homestead
        "version": None
    },
    
    # Backup configuration
    "backups": {
        "enabled": True,
        "interval_hours": 6,
        "max_backups": 10,
        "include_mods": False,
        "include_configs": True
    },
    
    # Auto-restart on crash
    "auto_restart": True,
    "restart_delay_seconds": 30,
    
    # Shutdown notification
    "shutdown_warning_minutes": [5, 1],  # Warn at 5 min and 1 min before shutdown
    
    # Boot with bot
    "boot_with_bot": True
}

# Server type download URLs (placeholders - real URLs fetched dynamically)
SERVER_TYPES = {
    "vanilla": {
        "name": "Vanilla",
        "description": "Official Minecraft server",
        "api_url": "https://launchermeta.mojang.com/mc/game/version_manifest.json"
    },
    "paper": {
        "name": "PaperMC",
        "description": "High-performance Spigot fork",
        "api_url": "https://api.papermc.io/v2/projects/paper"
    },
    "purpur": {
        "name": "Purpur",
        "description": "Feature-rich Paper fork",
        "api_url": "https://api.purpurmc.org/v2/purpur"
    },
    "fabric": {
        "name": "Fabric",
        "description": "Lightweight modding framework",
        "api_url": "https://meta.fabricmc.net/v2/versions",
        "installer_url": "https://maven.fabricmc.net/net/fabricmc/fabric-installer/latest/fabric-installer.jar"
    }
}

# Supported modpacks - Download from Modrinth or CurseForge
# These are pre-built modpacks that will be downloaded and auto-synced to clients
MODPACKS = {
    "melatonin": {
        "name": "Melatonin",
        "description": "Maximum performance and chill vibes - optimized for low-end hardware",
        "source": "modrinth",
        "modrinth_id": "melatonin",  # https://modrinth.com/modpack/melatonin
        "curseforge_id": None,
        "server_type": "fabric",
        "world_folder": "world_melatonin",
        "config_overrides": {
            "view-distance": 8,
            "simulation-distance": 6
        }
    },
    "raspberry_flavoured": {
        "name": "Raspberry Flavoured",
        "description": "Lightweight vanilla+ experience with quality of life improvements",
        "source": "curseforge",
        "modrinth_id": None,
        "curseforge_id": "raspberry-flavoured",  # https://www.curseforge.com/minecraft/modpacks/raspberry-flavoured
        "curseforge_project_id": 857292,  # Numeric project ID for API
        "server_type": "fabric",
        "world_folder": "world_raspberry_flavoured",
        "config_overrides": {}
    },
    "homestead": {
        "name": "Homestead Cozy",
        "description": "Cozy survival and building focused - farms, decoration, and exploration",
        "source": "curseforge",
        "modrinth_id": None,
        "curseforge_id": "homestead-cozy",  # https://www.curseforge.com/minecraft/modpacks/homestead-cozy
        "curseforge_project_id": 916222,  # Numeric project ID for API
        "server_type": "fabric",
        "world_folder": "world_homestead",
        "config_overrides": {}
    },
    "vanilla": {
        "name": "Vanilla",
        "description": "Pure Minecraft experience with no mods",
        "source": None,
        "modrinth_id": None,
        "curseforge_id": None,
        "server_type": "vanilla",
        "world_folder": "world",
        "config_overrides": {}
    }
}

# Performance mods by server type
PERFORMANCE_MODS = {
    "fabric": [
        {"name": "lithium", "modrinth_id": "gvQqBUqZ"},
        {"name": "ferritecore", "modrinth_id": "uXXizFIs"},
        {"name": "starlight", "modrinth_id": "H8CaAYZC"},
        {"name": "krypton", "modrinth_id": "fQEb0iXm"},
        {"name": "c2me", "modrinth_id": "VSNURh3q"},
        {"name": "spark", "modrinth_id": "l6YH9Als"}
    ],
    "paper": [
        # Paper has many optimizations built-in
        {"name": "spark", "url": "https://spark.lucko.me/download"}
    ],
    "purpur": [
        # Purpur includes Paper optimizations plus more
        {"name": "spark", "url": "https://spark.lucko.me/download"}
    ]
}

# Voice chat mod configuration
VOICE_CHAT_MODS = {
    "simple_voice_chat": {
        "name": "Simple Voice Chat",
        "modrinth_id": "9eGKb6K1",
        "description": "Proximity voice chat for Minecraft",
        "config_file": "voicechat/voicechat-server.properties",
        "default_config": {
            "port": 24454,
            "bind_address": "",
            "max_voice_distance": 48.0,
            "crouch_distance_multiplier": 1.0,
            "whisper_distance_multiplier": 0.5,
            "codec": "OPUS",
            "mtu_size": 1024,
            "keep_alive": 1000,
            "enable_groups": True,
            "voice_host": "",
            "allow_recording": True,
            "spectator_interaction": False,
            "spectator_player_possession": False,
            "force_voice_chat": False,
            "login_timeout": 10000,
            "broadcast_range": -1.0
        },
        "required_client_mod": True
    }
}

# AutoModpack configuration - Automatically syncs mods between server and clients
AUTOMODPACK_CONFIG = {
    "name": "AutoModpack",
    "modrinth_id": "k68glP2e",  # AutoModpack on Modrinth
    "description": "Automatically syncs server mods to clients - no manual installation needed",
    "config_dir": "automodpack",
    "server_config_file": "automodpack/automodpack-server.json",
    "default_server_config": {
        "modpackName": "Sulfur Server Modpack",
        "modpackHost": "",  # Will be auto-configured with server IP
        "hostPort": 30037,  # Default AutoModpack port
        "hostIp": "0.0.0.0",
        "syncedFiles": [
            "/mods/",
            "/config/"
        ],
        "excludeSyncedFiles": [
            "*.txt",
            "*.log"
        ],
        "optionalMods": [],
        "autoExcludeServerMods": True,
        "velocityMode": False,
        "reverseProxy": False,
        "selfUpdater": True,
        "acceptedLoaders": ["fabric", "quilt"],
        "restartScript": "./start.sh",
        "generateModpackOnStart": True
    },
    "required_client_mod": True,
    "beginner_friendly": True
}

# Modrinth API base URL
MODRINTH_API = "https://api.modrinth.com/v2"

# ==============================================================================
# Global State
# ==============================================================================

# Server process reference
_server_process: Optional[asyncio.subprocess.Process] = None
_console_buffer: deque = deque(maxlen=1000)  # Last 1000 console lines
_server_state: Dict = {}
_player_list: List[str] = []
_shutdown_task: Optional[asyncio.Task] = None
_backup_task: Optional[asyncio.Task] = None
_schedule_task: Optional[asyncio.Task] = None
_restart_flag: bool = False
_console_callbacks: List[Callable] = []


# ==============================================================================
# Platform Detection
# ==============================================================================

def _get_platform() -> str:
    """Detect the current platform for platform-specific operations."""
    system = platform.system().lower()
    
    # Check for Termux (Android)
    if os.path.exists('/data/data/com.termux'):
        return 'termux'
    
    # Check for Raspberry Pi
    if system == 'linux':
        try:
            with open('/proc/cpuinfo', 'r') as f:
                if 'Raspberry Pi' in f.read():
                    return 'raspberrypi'
        except (IOError, OSError):
            pass
        return 'linux'
    
    if system == 'windows':
        return 'windows'
    
    return system


def _get_java_path() -> Optional[str]:
    """Get the path to the Java executable."""
    # Check for JAVA_HOME
    java_home = os.environ.get('JAVA_HOME')
    if java_home:
        if platform.system() == 'Windows':
            java_path = os.path.join(java_home, 'bin', 'java.exe')
        else:
            java_path = os.path.join(java_home, 'bin', 'java')
        if os.path.exists(java_path):
            return java_path
    
    # Check PATH
    java_path = shutil.which('java')
    if java_path:
        return java_path
    
    # Platform-specific fallbacks
    plat = _get_platform()
    
    if plat == 'termux':
        # Termux: check common install location
        termux_java = '/data/data/com.termux/files/usr/bin/java'
        if os.path.exists(termux_java):
            return termux_java
    
    elif plat == 'windows':
        # Windows: check common install locations
        common_paths = [
            r'C:\Program Files\Java\jdk-21\bin\java.exe',
            r'C:\Program Files\Java\jdk-17\bin\java.exe',
            r'C:\Program Files\Eclipse Adoptium\jdk-21.*\bin\java.exe',
            r'C:\Program Files\Eclipse Adoptium\jdk-17.*\bin\java.exe',
        ]
        for path_pattern in common_paths:
            import glob
            matches = glob.glob(path_pattern)
            if matches:
                return matches[0]
    
    return None


def get_java_version() -> Optional[str]:
    """Get the installed Java version."""
    java_path = _get_java_path()
    if not java_path:
        return None
    
    try:
        result = subprocess.run(
            [java_path, '-version'],
            capture_output=True,
            text=True
        )
        # Java outputs version to stderr
        output = result.stderr
        
        # Parse version string
        match = re.search(r'version "([^"]+)"', output)
        if match:
            return match.group(1)
        
        # Alternative format
        match = re.search(r'openjdk (\d+)', output, re.IGNORECASE)
        if match:
            return match.group(1)
        
    except Exception as e:
        logger.error(f"Error getting Java version: {e}")
    
    return None


async def install_java_21() -> Tuple[bool, str]:
    """
    Automatically install Java 21 based on the detected platform.
    
    Returns:
        Tuple of (success, message)
    """
    plat = _get_platform()
    
    logger.info(f"Attempting automatic Java 21 installation for platform: {plat}")
    
    try:
        if plat == 'termux':
            # Termux installation
            process = await asyncio.create_subprocess_exec(
                'pkg', 'install', '-y', 'openjdk-21',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                return True, "Java 21 installed successfully via pkg"
            else:
                return False, f"pkg install failed: {stderr.decode()}"
                
        elif plat in ['linux', 'raspberrypi', 'wsl']:
            # Try apt-get first (Debian/Ubuntu)
            try:
                # Update package list
                update_proc = await asyncio.create_subprocess_exec(
                    'sudo', 'apt-get', 'update', '-qq',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await update_proc.communicate()
                
                # Install Java 21
                install_proc = await asyncio.create_subprocess_exec(
                    'sudo', 'apt-get', 'install', '-y', 'openjdk-21-jre-headless',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await install_proc.communicate()
                
                if install_proc.returncode == 0:
                    return True, "Java 21 installed successfully via apt-get"
                    
                # If openjdk-21 not available, try alternative package
                install_proc2 = await asyncio.create_subprocess_exec(
                    'sudo', 'apt-get', 'install', '-y', 'openjdk-21-jdk',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout2, stderr2 = await install_proc2.communicate()
                
                if install_proc2.returncode == 0:
                    return True, "Java 21 JDK installed successfully via apt-get"
                    
            except FileNotFoundError:
                pass  # apt-get not available
            
            # Try dnf (Fedora/RHEL)
            try:
                install_proc = await asyncio.create_subprocess_exec(
                    'sudo', 'dnf', 'install', '-y', 'java-21-openjdk-headless',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await install_proc.communicate()
                
                if install_proc.returncode == 0:
                    return True, "Java 21 installed successfully via dnf"
            except FileNotFoundError:
                pass  # dnf not available
            
            # Try pacman (Arch Linux)
            try:
                install_proc = await asyncio.create_subprocess_exec(
                    'sudo', 'pacman', '-S', '--noconfirm', 'jre21-openjdk-headless',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await install_proc.communicate()
                
                if install_proc.returncode == 0:
                    return True, "Java 21 installed successfully via pacman"
            except FileNotFoundError:
                pass  # pacman not available
            
            return False, "Could not install Java 21 automatically. Please install manually."
            
        elif plat == 'macos':
            # Try Homebrew
            try:
                install_proc = await asyncio.create_subprocess_exec(
                    'brew', 'install', 'openjdk@21',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await install_proc.communicate()
                
                if install_proc.returncode == 0:
                    # Create symlink
                    link_proc = await asyncio.create_subprocess_exec(
                        'sudo', 'ln', '-sfn', 
                        '/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk',
                        '/Library/Java/JavaVirtualMachines/openjdk-21.jdk',
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    await link_proc.communicate()
                    return True, "Java 21 installed successfully via Homebrew"
                else:
                    return False, f"Homebrew install failed: {stderr.decode()}"
            except FileNotFoundError:
                return False, "Homebrew not found. Please install Java 21 manually."
                
        elif plat == 'windows':
            return False, "Automatic Java installation not supported on Windows. Please download from https://adoptium.net/"
        
        return False, f"Automatic Java installation not supported for platform: {plat}"
        
    except Exception as e:
        logger.error(f"Error installing Java 21: {e}")
        return False, f"Installation error: {str(e)}"


def check_java_requirements() -> Tuple[bool, str]:
    """
    Check if Java meets the requirements for Minecraft.
    
    Returns:
        Tuple of (meets_requirements, message)
    """
    java_version = get_java_version()
    
    if not java_version:
        plat = _get_platform()
        install_cmd = {
            'termux': 'pkg install openjdk-21',
            'linux': 'sudo apt install openjdk-21-jdk',
            'raspberrypi': 'sudo apt install openjdk-21-jdk',
            'windows': 'Download from https://adoptium.net/'
        }
        return False, f"Java not found. Install with: {install_cmd.get(plat, 'Install Java 21')}"
    
    # Parse major version
    major_version = 0
    version_parts = java_version.split('.')
    if version_parts:
        try:
            # Handle both "21" and "21.0.1" formats
            major_version = int(version_parts[0])
        except ValueError:
            try:
                major_version = int(java_version.split('.')[0].split('-')[0])
            except ValueError:
                pass
    
    # Minecraft 1.20.5+ requires Java 21
    if major_version < 17:
        return False, f"Java {java_version} found, but Java 17+ is required. Java 21 recommended."
    
    if major_version < 21:
        return True, f"Java {java_version} found. Java 21 recommended for best performance."
    
    return True, f"Java {java_version} found. All requirements met."


# ==============================================================================
# State Management
# ==============================================================================

def load_state() -> Dict:
    """Load the server state from disk."""
    global _server_state
    
    if os.path.exists(MC_STATE_FILE):
        try:
            with open(MC_STATE_FILE, 'r') as f:
                _server_state = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading Minecraft state: {e}")
            _server_state = {}
    else:
        _server_state = {}
    
    return _server_state


def save_state():
    """Save the server state to disk."""
    try:
        os.makedirs(os.path.dirname(MC_STATE_FILE), exist_ok=True)
        with open(MC_STATE_FILE, 'w') as f:
            json.dump(_server_state, f, indent=2)
    except IOError as e:
        logger.error(f"Error saving Minecraft state: {e}")


def get_config(bot_config: Dict) -> Dict:
    """Get the Minecraft server configuration from the bot config."""
    mc_config = bot_config.get('modules', {}).get('minecraft', {})
    
    # Merge with defaults
    config = DEFAULT_MC_CONFIG.copy()
    config.update(mc_config)
    
    return config


def update_state(key: str, value):
    """Update a state value and save to disk."""
    _server_state[key] = value
    save_state()


# ==============================================================================
# Server Jar Management
# ==============================================================================

async def download_file(url: str, dest_path: str, progress_callback: Callable = None) -> bool:
    """
    Download a file from a URL.
    
    Args:
        url: The URL to download from
        dest_path: The destination file path
        progress_callback: Optional callback for progress updates.
                          Called with (downloaded_bytes, total_bytes, speed_bps, percent)
        
    Returns:
        True if download was successful
    """
    try:
        logger.info(f"Downloading {url} to {dest_path}")
        
        # Use aiohttp for async download if available
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Download failed with status {response.status}")
                        return False
                    
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    start_time = time.time()
                    
                    with open(dest_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                            downloaded += len(chunk)
                            if progress_callback and total_size > 0:
                                elapsed = time.time() - start_time
                                speed = downloaded / elapsed if elapsed > 0 else 0
                                percent = (downloaded / total_size) * 100
                                progress_callback(downloaded, total_size, speed, percent)
            return True
        except ImportError:
            # Fallback to urllib (sync) with progress callback support
            def _download():
                start_time = time.time()
                # Track last update time for throttling progress updates
                last_update_time = 0.0
                
                def reporthook(block_num, block_size, total_size):
                    """Progress hook for urllib.request.urlretrieve"""
                    nonlocal last_update_time
                    
                    if progress_callback and total_size > 0:
                        downloaded = block_num * block_size
                        # Clamp downloaded to total_size to avoid over 100%
                        downloaded = min(downloaded, total_size)
                        
                        # Throttle updates to avoid excessive callbacks
                        current_time = time.time()
                        if current_time - last_update_time >= DOWNLOAD_PROGRESS_UPDATE_INTERVAL or downloaded >= total_size:
                            last_update_time = current_time
                            elapsed = current_time - start_time
                            speed = downloaded / elapsed if elapsed > 0 else 0
                            percent = (downloaded / total_size) * 100
                            progress_callback(downloaded, total_size, speed, percent)
                
                urllib.request.urlretrieve(url, dest_path, reporthook=reporthook)
            
            await asyncio.get_event_loop().run_in_executor(None, _download)
            return True
        
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        return False


async def get_vanilla_server_url(version: str) -> Optional[str]:
    """Get the download URL for a vanilla Minecraft server."""
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            # Get version manifest
            async with session.get(SERVER_TYPES['vanilla']['api_url']) as response:
                if response.status != 200:
                    return None
                manifest = await response.json()
            
            # Find the version
            version_info = None
            for v in manifest.get('versions', []):
                if v['id'] == version:
                    version_info = v
                    break
            
            if not version_info:
                logger.error(f"Minecraft version {version} not found")
                return None
            
            # Get version details
            async with session.get(version_info['url']) as response:
                if response.status != 200:
                    return None
                version_data = await response.json()
            
            # Get server download URL
            server_info = version_data.get('downloads', {}).get('server', {})
            return server_info.get('url')
            
    except Exception as e:
        logger.error(f"Error getting vanilla server URL: {e}")
        return None


async def get_paper_server_url(version: str) -> Optional[str]:
    """Get the download URL for a PaperMC server."""
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            # Get available versions
            async with session.get(f"{SERVER_TYPES['paper']['api_url']}/versions/{version}") as response:
                if response.status != 200:
                    logger.error(f"PaperMC version {version} not found")
                    return None
                version_data = await response.json()
            
            # Get the latest build
            builds = version_data.get('builds', [])
            if not builds:
                return None
            
            latest_build = max(builds)
            
            # Get build info
            async with session.get(
                f"{SERVER_TYPES['paper']['api_url']}/versions/{version}/builds/{latest_build}"
            ) as response:
                if response.status != 200:
                    return None
                build_data = await response.json()
            
            # Get download filename
            downloads = build_data.get('downloads', {})
            application = downloads.get('application', {})
            filename = application.get('name')
            
            if not filename:
                return None
            
            return f"{SERVER_TYPES['paper']['api_url']}/versions/{version}/builds/{latest_build}/downloads/{filename}"
            
    except Exception as e:
        logger.error(f"Error getting PaperMC server URL: {e}")
        return None


async def get_purpur_server_url(version: str) -> Optional[str]:
    """Get the download URL for a Purpur server."""
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            # Get latest build for version
            async with session.get(f"{SERVER_TYPES['purpur']['api_url']}/{version}") as response:
                if response.status != 200:
                    logger.error(f"Purpur version {version} not found")
                    return None
                version_data = await response.json()
            
            builds = version_data.get('builds', {})
            if not builds.get('all'):
                return None
            
            latest_build = builds['latest']
            
            return f"{SERVER_TYPES['purpur']['api_url']}/{version}/{latest_build}/download"
            
    except Exception as e:
        logger.error(f"Error getting Purpur server URL: {e}")
        return None


async def download_server_jar(server_type: str, version: str, progress_callback: Callable = None) -> Tuple[bool, str]:
    """
    Download the server JAR file.
    
    Args:
        server_type: The server type (vanilla, paper, purpur, fabric)
        version: The Minecraft version
        progress_callback: Optional callback for progress updates
        
    Returns:
        Tuple of (success, path_or_error_message)
    """
    # Validate version format to prevent command injection
    # Minecraft versions follow patterns like: 1.21.4, 1.20.4, 24w14a (snapshots)
    import re
    version_pattern = re.compile(r'^[0-9]{1,2}\.[0-9]{1,2}(\.[0-9]{1,2})?(-[a-zA-Z0-9]+)?$|^[0-9]{2}w[0-9]{2}[a-z]$')
    if not version_pattern.match(version):
        return False, f"Invalid version format: {version}. Expected format like '1.21.4' or '24w14a'"
    
    # Validate server type
    valid_server_types = ['vanilla', 'paper', 'purpur', 'fabric']
    if server_type not in valid_server_types:
        return False, f"Invalid server type: {server_type}. Must be one of: {', '.join(valid_server_types)}"
    
    os.makedirs(MC_SERVER_DIR, exist_ok=True)
    
    jar_path = os.path.join(MC_SERVER_DIR, "server.jar")
    
    # Get download URL based on server type
    download_url = None
    
    if server_type == 'vanilla':
        download_url = await get_vanilla_server_url(version)
    elif server_type == 'paper':
        download_url = await get_paper_server_url(version)
    elif server_type == 'purpur':
        download_url = await get_purpur_server_url(version)
    elif server_type == 'fabric':
        # Fabric requires the installer
        return await setup_fabric_server(version)
    else:
        return False, f"Unknown server type: {server_type}"
    
    if not download_url:
        return False, f"Could not find download URL for {server_type} {version}"
    
    success = await download_file(download_url, jar_path, progress_callback)
    
    if success:
        logger.info(f"Downloaded {server_type} server {version} to {jar_path}")
        update_state('server_jar_type', server_type)
        update_state('server_version', version)
        update_state('server_jar_path', jar_path)
        return True, jar_path
    else:
        return False, "Failed to download server JAR"


async def setup_fabric_server(version: str) -> Tuple[bool, str]:
    """
    Set up a Fabric server.
    
    Args:
        version: The Minecraft version
        
    Returns:
        Tuple of (success, message)
    """
    os.makedirs(MC_SERVER_DIR, exist_ok=True)
    
    installer_path = os.path.join(MC_SERVER_DIR, "fabric-installer.jar")
    
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            # Get latest installer version
            async with session.get("https://meta.fabricmc.net/v2/versions/installer") as response:
                if response.status != 200:
                    return False, "Could not get Fabric installer info"
                installer_info = await response.json()
            
            if not installer_info:
                return False, "No Fabric installer found"
            
            latest_installer = installer_info[0]
            installer_url = latest_installer['url']
            
            # Download installer
            success = await download_file(installer_url, installer_path)
            if not success:
                return False, "Failed to download Fabric installer"
            
            # Run installer
            java_path = _get_java_path()
            if not java_path:
                return False, "Java not found"
            
            # Run Fabric installer
            result = subprocess.run(
                [java_path, '-jar', installer_path, 'server', '-mcversion', version, '-downloadMinecraft'],
                cwd=MC_SERVER_DIR,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return False, f"Fabric installation failed: {result.stderr}"
            
            update_state('server_jar_type', 'fabric')
            update_state('server_version', version)
            
            # Find the generated start script or jar
            # Fabric creates a fabric-server-launch.jar or server.jar
            jar_path = os.path.join(MC_SERVER_DIR, "fabric-server-launch.jar")
            if not os.path.exists(jar_path):
                jar_path = os.path.join(MC_SERVER_DIR, "server.jar")
            
            update_state('server_jar_path', jar_path)
            
            return True, f"Fabric server {version} installed successfully"
            
    except Exception as e:
        logger.error(f"Error setting up Fabric server: {e}")
        return False, str(e)


# ==============================================================================
# Mod Management
# ==============================================================================

async def get_mod_download_url(modrinth_id: str, minecraft_version: str, loader: str = "fabric") -> Optional[Dict]:
    """
    Get the download URL for a mod from Modrinth.
    
    Args:
        modrinth_id: The Modrinth project ID
        minecraft_version: The Minecraft version
        loader: The mod loader (fabric, forge, etc.)
        
    Returns:
        Dictionary with download info, or None if not found
    """
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            # Get project versions
            url = f"{MODRINTH_API}/project/{modrinth_id}/version"
            params = {
                "game_versions": f'["{minecraft_version}"]',
                "loaders": f'["{loader}"]'
            }
            
            headers = {
                "User-Agent": "SulfurBot/1.0 (github.com/mereMint/sulfur)"
            }
            
            async with session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    logger.warning(f"Modrinth API returned {response.status} for {modrinth_id}")
                    return None
                
                versions = await response.json()
            
            if not versions:
                logger.warning(f"No compatible version found for {modrinth_id} on MC {minecraft_version}")
                return None
            
            # Get the latest compatible version
            latest = versions[0]
            files = latest.get('files', [])
            
            if not files:
                return None
            
            # Find the primary file
            primary_file = next((f for f in files if f.get('primary', False)), files[0])
            
            return {
                'name': latest.get('name', modrinth_id),
                'version': latest.get('version_number'),
                'url': primary_file.get('url'),
                'filename': primary_file.get('filename'),
                'sha512': primary_file.get('hashes', {}).get('sha512')
            }
            
    except Exception as e:
        logger.error(f"Error getting mod download URL for {modrinth_id}: {e}")
        return None


async def download_mod(mod_info: Dict, progress_callback: Callable = None) -> Tuple[bool, str]:
    """
    Download a mod to the mods directory.
    
    Args:
        mod_info: Dictionary with mod download info
        progress_callback: Optional callback for progress updates
        
    Returns:
        Tuple of (success, path_or_error)
    """
    os.makedirs(MC_MODS_DIR, exist_ok=True)
    
    url = mod_info.get('url')
    filename = mod_info.get('filename', 'mod.jar')
    
    if not url:
        return False, "No download URL provided"
    
    dest_path = os.path.join(MC_MODS_DIR, filename)
    
    # Check if already downloaded
    if os.path.exists(dest_path):
        # Verify hash if available (using buffered reading for large files)
        expected_hash = mod_info.get('sha512')
        if expected_hash:
            sha512_hash = hashlib.sha512()
            with open(dest_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    sha512_hash.update(chunk)
            if sha512_hash.hexdigest() == expected_hash:
                logger.info(f"Mod {filename} already downloaded and verified")
                return True, dest_path
        else:
            logger.info(f"Mod {filename} already exists, skipping download")
            return True, dest_path
    
    success = await download_file(url, dest_path, progress_callback)
    
    if success:
        logger.info(f"Downloaded mod: {filename}")
        return True, dest_path
    else:
        return False, f"Failed to download {filename}"


async def download_performance_mods(minecraft_version: str, server_type: str = "fabric") -> List[Dict]:
    """
    Download all performance mods for the given server type.
    
    Args:
        minecraft_version: The Minecraft version
        server_type: The server type (fabric, paper, purpur)
        
    Returns:
        List of results for each mod
    """
    results = []
    mods = PERFORMANCE_MODS.get(server_type, [])
    
    for mod in mods:
        result = {
            'name': mod['name'],
            'success': False
        }
        
        if 'modrinth_id' in mod:
            mod_info = await get_mod_download_url(mod['modrinth_id'], minecraft_version, server_type)
            if mod_info:
                success, path = await download_mod(mod_info)
                result['success'] = success
                result['path'] = path if success else None
                result['error'] = path if not success else None
            else:
                result['error'] = 'Could not find compatible version'
        elif 'url' in mod:
            # Direct download URL
            mod_info = {
                'url': mod['url'],
                'filename': f"{mod['name']}.jar"
            }
            success, path = await download_mod(mod_info)
            result['success'] = success
            result['path'] = path if success else None
            result['error'] = path if not success else None
        
        results.append(result)
    
    return results


async def download_voice_chat_mod(minecraft_version: str, server_type: str = "fabric") -> Dict:
    """
    Download and configure the Simple Voice Chat mod.
    
    Args:
        minecraft_version: The Minecraft version
        server_type: The server type
        
    Returns:
        Result dictionary
    """
    result = {
        'success': False,
        'mod_downloaded': False,
        'config_created': False
    }
    
    voice_mod = VOICE_CHAT_MODS.get('simple_voice_chat')
    if not voice_mod:
        result['error'] = 'Voice chat mod configuration not found'
        return result
    
    # Download the mod
    mod_info = await get_mod_download_url(voice_mod['modrinth_id'], minecraft_version, server_type)
    if not mod_info:
        result['error'] = f'Could not find Simple Voice Chat for MC {minecraft_version}'
        return result
    
    success, path = await download_mod(mod_info)
    result['mod_downloaded'] = success
    
    if not success:
        result['error'] = f'Failed to download mod: {path}'
        return result
    
    result['mod_path'] = path
    
    # Create default configuration
    config_created = await configure_voice_chat_mod()
    result['config_created'] = config_created
    result['success'] = True
    
    return result


async def configure_voice_chat_mod(custom_config: Dict = None) -> bool:
    """
    Configure the Simple Voice Chat mod with default or custom settings.
    
    Args:
        custom_config: Optional custom configuration to merge with defaults
        
    Returns:
        True if configuration was created successfully
    """
    voice_mod = VOICE_CHAT_MODS.get('simple_voice_chat')
    if not voice_mod:
        return False
    
    # Ensure config directory exists
    voicechat_config_dir = os.path.join(MC_SERVER_DIR, "config", "voicechat")
    os.makedirs(voicechat_config_dir, exist_ok=True)
    
    config_path = os.path.join(MC_SERVER_DIR, voice_mod['config_file'])
    
    # Merge custom config with defaults
    config = voice_mod['default_config'].copy()
    if custom_config:
        config.update(custom_config)
    
    try:
        # Write as properties file
        with open(config_path, 'w') as f:
            f.write("# Simple Voice Chat Server Configuration\n")
            f.write("# Auto-generated by Sulfur Bot\n\n")
            
            for key, value in config.items():
                if isinstance(value, bool):
                    value = str(value).lower()
                elif isinstance(value, float):
                    value = str(value)
                f.write(f"{key}={value}\n")
        
        logger.info(f"Created voice chat configuration at {config_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create voice chat config: {e}")
        return False


async def check_for_mod_updates(minecraft_version: str, server_type: str = "fabric") -> List[Dict]:
    """
    Check for updates to installed mods.
    
    Args:
        minecraft_version: The Minecraft version
        server_type: The server type
        
    Returns:
        List of mods with available updates
    """
    updates = []
    
    if not os.path.exists(MC_MODS_DIR):
        return updates
    
    # Get installed mods
    installed_mods = []
    for filename in os.listdir(MC_MODS_DIR):
        if filename.endswith('.jar'):
            installed_mods.append(filename)
    
    # Check performance mods
    for mod in PERFORMANCE_MODS.get(server_type, []):
        if 'modrinth_id' in mod:
            latest = await get_mod_download_url(mod['modrinth_id'], minecraft_version, server_type)
            if latest:
                # Check if we have a different version installed
                current_file = None
                for installed in installed_mods:
                    if mod['name'].lower() in installed.lower():
                        current_file = installed
                        break
                
                if current_file and current_file != latest.get('filename'):
                    updates.append({
                        'name': mod['name'],
                        'current_file': current_file,
                        'new_version': latest.get('version'),
                        'new_filename': latest.get('filename'),
                        'download_url': latest.get('url')
                    })
    
    return updates


async def update_all_mods(minecraft_version: str, server_type: str = "fabric") -> Dict:
    """
    Update all installed mods to their latest versions.
    
    Args:
        minecraft_version: The Minecraft version
        server_type: The server type
        
    Returns:
        Dictionary with update results
    """
    result = {
        'checked': 0,
        'updated': 0,
        'failed': 0,
        'details': []
    }
    
    updates = await check_for_mod_updates(minecraft_version, server_type)
    result['checked'] = len(updates)
    
    for update in updates:
        detail = {
            'name': update['name'],
            'success': False
        }
        
        try:
            # Remove old version
            old_path = os.path.join(MC_MODS_DIR, update['current_file'])
            if os.path.exists(old_path):
                os.remove(old_path)
            
            # Download new version
            mod_info = {
                'url': update['download_url'],
                'filename': update['new_filename']
            }
            success, path = await download_mod(mod_info)
            
            detail['success'] = success
            if success:
                result['updated'] += 1
                detail['new_version'] = update['new_version']
            else:
                result['failed'] += 1
                detail['error'] = path
                
        except Exception as e:
            result['failed'] += 1
            detail['error'] = str(e)
        
        result['details'].append(detail)
    
    return result


async def download_automodpack(minecraft_version: str, server_type: str = "fabric") -> Dict:
    """
    Download and configure AutoModpack for automatic mod syncing.
    
    AutoModpack automatically syncs server mods to clients when they connect,
    eliminating the need for manual mod installation.
    
    Args:
        minecraft_version: The Minecraft version
        server_type: The server type
        
    Returns:
        Result dictionary
    """
    result = {
        'success': False,
        'mod_downloaded': False,
        'config_created': False
    }
    
    # Download the mod
    mod_info = await get_mod_download_url(AUTOMODPACK_CONFIG['modrinth_id'], minecraft_version, server_type)
    if not mod_info:
        result['error'] = f'Could not find AutoModpack for MC {minecraft_version}'
        return result
    
    success, path = await download_mod(mod_info)
    result['mod_downloaded'] = success
    
    if not success:
        result['error'] = f'Failed to download AutoModpack: {path}'
        return result
    
    result['mod_path'] = path
    
    # Create configuration
    config_created = await configure_automodpack()
    result['config_created'] = config_created
    result['success'] = True
    
    return result


async def configure_automodpack(server_ip: str = None, modpack_name: str = None) -> bool:
    """
    Configure AutoModpack with optimal settings for beginner-friendly mod syncing.
    
    Args:
        server_ip: The server's public IP (auto-detected if None)
        modpack_name: Name for the modpack
        
    Returns:
        True if configuration was created successfully
    """
    # Ensure config directory exists
    automodpack_config_dir = os.path.join(MC_SERVER_DIR, "automodpack")
    os.makedirs(automodpack_config_dir, exist_ok=True)
    
    config_path = os.path.join(MC_SERVER_DIR, AUTOMODPACK_CONFIG['server_config_file'])
    
    # Build configuration
    config = AUTOMODPACK_CONFIG['default_server_config'].copy()
    
    if modpack_name:
        config['modpackName'] = modpack_name
    
    if server_ip:
        config['modpackHost'] = server_ip
    
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Created AutoModpack configuration at {config_path}")
        
        # Also create a client instruction file for users
        await create_automodpack_client_instructions()
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to create AutoModpack config: {e}")
        return False


async def create_automodpack_client_instructions() -> bool:
    """
    Create a README file with instructions for clients on how to use AutoModpack.
    
    Returns:
        True if file was created
    """
    instructions_path = os.path.join(MC_SERVER_DIR, "CLIENT_SETUP_INSTRUCTIONS.md")
    
    instructions = """# 🎮 How to Join the Server

## One-Time Setup (Super Easy!)

### Step 1: Install Fabric Loader
1. Go to https://fabricmc.net/use/installer/
2. Download and run the installer
3. Select your Minecraft version and click "Install"

### Step 2: Install AutoModpack (Client)
1. Download AutoModpack from: https://modrinth.com/mod/automodpack
2. Put the .jar file in your `.minecraft/mods/` folder
   - Windows: `%appdata%\\.minecraft\\mods\\`
   - Mac: `~/Library/Application Support/minecraft/mods/`
   - Linux: `~/.minecraft/mods/`

### Step 3: Launch and Connect
1. Open Minecraft with the Fabric profile
2. Add this server to your server list
3. Connect to the server

**That's it!** AutoModpack will automatically download all required mods.

## What Happens Automatically

When you connect:
1. ✅ AutoModpack detects the server's modpack
2. ✅ Downloads all required mods automatically
3. ✅ Configures everything for you
4. ✅ You're ready to play!

## Troubleshooting

### "Mods failed to download"
- Check your internet connection
- Try connecting again

### "Version mismatch"
- Make sure you have the correct Minecraft version
- Update AutoModpack to the latest version

### Need Help?
Ask in Discord or contact the server admin!
"""
    
    try:
        with open(instructions_path, 'w') as f:
            f.write(instructions)
        logger.info(f"Created client instructions at {instructions_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to create client instructions: {e}")
        return False


async def setup_mods_on_install(config: Dict) -> Dict:
    """
    Download and configure all mods during initial setup.
    
    Args:
        config: Minecraft configuration
        
    Returns:
        Setup result dictionary
    """
    result = {
        'success': True,
        'performance_mods': [],
        'voice_chat': None,
        'automodpack': None,
        'errors': []
    }
    
    server_type = config.get('server_type', 'fabric')
    minecraft_version = config.get('minecraft_version', '1.21.4')
    
    # AutoModpack is enabled by default for beginner-friendly experience
    # It automatically syncs mods to clients when they connect
    automodpack_enabled = config.get('optional_mods', {}).get('automodpack', {}).get('enabled', True)
    
    if automodpack_enabled and server_type == 'fabric':
        logger.info("Setting up AutoModpack for automatic mod syncing...")
        automodpack_result = await download_automodpack(minecraft_version, server_type)
        result['automodpack'] = automodpack_result
        
        if automodpack_result.get('success'):
            logger.info("✅ AutoModpack configured - clients will auto-download mods!")
        else:
            result['errors'].append(f"AutoModpack setup failed: {automodpack_result.get('error')}")
    
    # Download performance mods if enabled
    if config.get('performance_mods', {}).get('enabled', True):
        logger.info("Downloading performance mods...")
        perf_results = await download_performance_mods(minecraft_version, server_type)
        result['performance_mods'] = perf_results
        
        failed = [r for r in perf_results if not r['success']]
        if failed:
            result['errors'].extend([f"Failed to download {r['name']}: {r.get('error')}" for r in failed])
    
    # Set up voice chat if enabled
    if config.get('optional_mods', {}).get('simple_voice_chat', {}).get('enabled', False):
        logger.info("Setting up voice chat mod...")
        voice_result = await download_voice_chat_mod(minecraft_version, server_type)
        result['voice_chat'] = voice_result
        
        if not voice_result.get('success'):
            result['errors'].append(f"Voice chat setup failed: {voice_result.get('error')}")
    
    if result['errors']:
        result['success'] = False
    
    return result


# ==============================================================================
# Modpack Management
# ==============================================================================

def get_available_modpacks() -> Dict:
    """
    Get all available modpacks with their information.
    
    Returns:
        Dictionary of modpack configurations
    """
    return MODPACKS.copy()


def get_current_modpack() -> Optional[str]:
    """
    Get the currently active modpack.
    
    Returns:
        Modpack name or None if vanilla
    """
    return _server_state.get('current_modpack', 'vanilla')


async def save_current_world(modpack_name: str = None) -> Tuple[bool, str]:
    """
    Save the current world to the worlds storage directory.
    
    Args:
        modpack_name: The modpack name to save as (uses current if None)
        
    Returns:
        Tuple of (success, message)
    """
    if modpack_name is None:
        modpack_name = get_current_modpack() or 'vanilla'
    
    # Ensure worlds storage directory exists
    os.makedirs(MC_WORLDS_STORAGE_DIR, exist_ok=True)
    
    # Get the world folder for this modpack
    modpack_config = MODPACKS.get(modpack_name, MODPACKS.get('vanilla'))
    world_folder_name = modpack_config.get('world_folder', 'world')
    
    # Source world directories
    source_worlds = []
    for world_dir in ['world', 'world_nether', 'world_the_end']:
        source_path = os.path.join(MC_SERVER_DIR, world_dir)
        if os.path.exists(source_path):
            source_worlds.append((world_dir, source_path))
    
    if not source_worlds:
        return True, "No world to save"
    
    # Destination directory
    dest_base = os.path.join(MC_WORLDS_STORAGE_DIR, modpack_name)
    os.makedirs(dest_base, exist_ok=True)
    
    try:
        for world_dir, source_path in source_worlds:
            dest_path = os.path.join(dest_base, world_dir)
            
            # Remove existing backup if present
            if os.path.exists(dest_path):
                shutil.rmtree(dest_path)
            
            # Copy world to storage
            shutil.copytree(source_path, dest_path)
            logger.info(f"Saved {world_dir} to {dest_path}")
        
        # Record save time
        state_file = os.path.join(dest_base, 'world_state.json')
        with open(state_file, 'w') as f:
            json.dump({
                'modpack': modpack_name,
                'saved_at': datetime.now(timezone.utc).isoformat(),
                'worlds': [w[0] for w in source_worlds]
            }, f, indent=2)
        
        return True, f"World saved for modpack '{modpack_name}'"
        
    except Exception as e:
        logger.error(f"Failed to save world: {e}")
        return False, str(e)


async def load_world_for_modpack(modpack_name: str) -> Tuple[bool, str]:
    """
    Load a saved world for a specific modpack.
    
    Args:
        modpack_name: The modpack to load world for
        
    Returns:
        Tuple of (success, message)
    """
    saved_world_path = os.path.join(MC_WORLDS_STORAGE_DIR, modpack_name)
    
    if not os.path.exists(saved_world_path):
        return False, f"No saved world found for '{modpack_name}'"
    
    try:
        # Get list of saved worlds
        state_file = os.path.join(saved_world_path, 'world_state.json')
        if os.path.exists(state_file):
            with open(state_file, 'r') as f:
                state = json.load(f)
            world_dirs = state.get('worlds', ['world'])
        else:
            world_dirs = ['world', 'world_nether', 'world_the_end']
        
        # Copy worlds to server directory
        for world_dir in world_dirs:
            source_path = os.path.join(saved_world_path, world_dir)
            dest_path = os.path.join(MC_SERVER_DIR, world_dir)
            
            if os.path.exists(source_path):
                # Remove current world
                if os.path.exists(dest_path):
                    shutil.rmtree(dest_path)
                
                # Copy saved world
                shutil.copytree(source_path, dest_path)
                logger.info(f"Loaded {world_dir} from {source_path}")
        
        return True, f"World loaded for modpack '{modpack_name}'"
        
    except Exception as e:
        logger.error(f"Failed to load world: {e}")
        return False, str(e)


def has_saved_world(modpack_name: str) -> bool:
    """
    Check if there's a saved world for a modpack.
    
    Args:
        modpack_name: The modpack name
        
    Returns:
        True if a saved world exists
    """
    saved_world_path = os.path.join(MC_WORLDS_STORAGE_DIR, modpack_name)
    return os.path.exists(saved_world_path) and os.path.isdir(saved_world_path)


async def clear_current_mods() -> bool:
    """
    Remove all mods from the mods directory.
    
    Returns:
        True if successful
    """
    if not os.path.exists(MC_MODS_DIR):
        return True
    
    try:
        for filename in os.listdir(MC_MODS_DIR):
            if filename.endswith('.jar'):
                file_path = os.path.join(MC_MODS_DIR, filename)
                os.remove(file_path)
                logger.info(f"Removed mod: {filename}")
        return True
    except Exception as e:
        logger.error(f"Failed to clear mods: {e}")
        return False


async def install_modpack(modpack_name: str, minecraft_version: str = None) -> Dict:
    """
    Install a modpack by downloading it from Modrinth or CurseForge.
    
    Args:
        modpack_name: The modpack to install
        minecraft_version: The Minecraft version (auto-detected from modpack if None)
        
    Returns:
        Result dictionary
    """
    result = {
        'success': False,
        'modpack': modpack_name,
        'source': None,
        'version': None,
        'files_installed': [],
        'errors': []
    }
    
    modpack = MODPACKS.get(modpack_name)
    if not modpack:
        logger.error(f"Unknown modpack: {modpack_name}")
        result['errors'].append(f"Unknown modpack: {modpack_name}")
        return result
    
    if modpack_name == 'vanilla':
        logger.info("Vanilla modpack selected - no mods to install")
        result['success'] = True
        result['source'] = 'vanilla'
        return result
    
    source = modpack.get('source')
    logger.info(f"Installing modpack '{modpack['name']}' from {source}...")
    
    # Ensure directories exist
    os.makedirs(MC_MODS_DIR, exist_ok=True)
    os.makedirs(MC_CONFIG_DIR, exist_ok=True)
    
    try:
        if source == 'modrinth':
            result = await download_modpack_from_modrinth(modpack, minecraft_version, result)
        elif source == 'curseforge':
            result = await download_modpack_from_curseforge(modpack, minecraft_version, result)
        else:
            result['errors'].append(f"Unknown modpack source: {source}")
            return result
        
        if result['success']:
            # Update state
            update_state('current_modpack', modpack_name)
            update_state('modpack_installed_at', datetime.now(timezone.utc).isoformat())
            update_state('modpack_version', result.get('version'))
            logger.info(f"✅ Successfully installed modpack '{modpack['name']}'")
        
    except Exception as e:
        logger.error(f"Failed to install modpack '{modpack_name}': {e}")
        result['errors'].append(str(e))
    
    return result


async def download_modpack_from_modrinth(modpack: Dict, minecraft_version: str, result: Dict) -> Dict:
    """
    Download a modpack from Modrinth.
    
    Args:
        modpack: Modpack configuration
        minecraft_version: Target Minecraft version (optional)
        result: Result dictionary to update
        
    Returns:
        Updated result dictionary
    """
    modrinth_id = modpack.get('modrinth_id')
    if not modrinth_id:
        result['errors'].append("No Modrinth ID configured for this modpack")
        return result
    
    result['source'] = 'modrinth'
    
    try:
        import aiohttp
        
        headers = {
            "User-Agent": "SulfurBot/1.0 (github.com/mereMint/sulfur)"
        }
        
        async with aiohttp.ClientSession() as session:
            # Get project info
            logger.info(f"Fetching modpack info from Modrinth: {modrinth_id}")
            project_url = f"{MODRINTH_API}/project/{modrinth_id}"
            
            async with session.get(project_url, headers=headers) as response:
                if response.status != 200:
                    result['errors'].append(f"Modrinth API error: {response.status}")
                    logger.error(f"Modrinth API returned {response.status} for {modrinth_id}")
                    return result
                project_data = await response.json()
            
            logger.info(f"Found modpack: {project_data.get('title')}")
            
            # Get versions
            versions_url = f"{MODRINTH_API}/project/{modrinth_id}/version"
            params = {"loaders": '["fabric"]'}
            if minecraft_version:
                params["game_versions"] = f'["{minecraft_version}"]'
            
            async with session.get(versions_url, params=params, headers=headers) as response:
                if response.status != 200:
                    result['errors'].append(f"Failed to get modpack versions: {response.status}")
                    return result
                versions = await response.json()
            
            if not versions:
                logger.warning(f"No compatible versions found, trying without version filter")
                # Try without version filter
                async with session.get(versions_url, headers=headers) as response:
                    versions = await response.json()
            
            if not versions:
                result['errors'].append("No versions found for this modpack")
                return result
            
            # Get latest version
            latest = versions[0]
            result['version'] = latest.get('version_number')
            logger.info(f"Latest version: {result['version']} for MC {latest.get('game_versions', [])}")
            
            # Download the modpack mrpack file
            files = latest.get('files', [])
            mrpack_file = next((f for f in files if f.get('filename', '').endswith('.mrpack')), None)
            
            if not mrpack_file:
                result['errors'].append("No .mrpack file found in modpack")
                return result
            
            mrpack_url = mrpack_file.get('url')
            mrpack_filename = mrpack_file.get('filename')
            
            logger.info(f"Downloading modpack: {mrpack_filename}")
            
            # Download mrpack file
            mrpack_path = os.path.join(MC_SERVER_DIR, mrpack_filename)
            async with session.get(mrpack_url, headers=headers) as response:
                if response.status != 200:
                    result['errors'].append(f"Failed to download modpack: {response.status}")
                    return result
                
                with open(mrpack_path, 'wb') as f:
                    f.write(await response.read())
            
            logger.info(f"Downloaded modpack to {mrpack_path}")
            
            # Extract and install modpack
            install_success = await extract_and_install_mrpack(mrpack_path, result)
            
            if install_success:
                result['success'] = True
            
            # Clean up mrpack file
            if os.path.exists(mrpack_path):
                os.remove(mrpack_path)
            
    except ImportError:
        error_msg = "aiohttp library is required for modpack downloads. Install with: pip install aiohttp"
        result['errors'].append(error_msg)
        logger.error(error_msg)
    except Exception as e:
        result['errors'].append(f"Error downloading from Modrinth: {e}")
        logger.error(f"Error downloading from Modrinth: {e}")
    
    return result


async def download_modpack_from_curseforge(modpack: Dict, minecraft_version: str, result: Dict) -> Dict:
    """
    Download a modpack from CurseForge.
    
    Note: CurseForge requires an API key for direct downloads. 
    We'll provide instructions for manual download or use alternative methods.
    
    Args:
        modpack: Modpack configuration
        minecraft_version: Target Minecraft version (optional)
        result: Result dictionary to update
        
    Returns:
        Updated result dictionary
    """
    curseforge_id = modpack.get('curseforge_id')
    project_id = modpack.get('curseforge_project_id')
    
    if not curseforge_id:
        result['errors'].append("No CurseForge ID configured for this modpack")
        return result
    
    result['source'] = 'curseforge'
    
    # CurseForge API requires an API key
    cf_api_key = os.environ.get('CURSEFORGE_API_KEY')
    
    if not cf_api_key:
        logger.warning("No CurseForge API key found, providing manual download instructions")
        manual_url = f"https://www.curseforge.com/minecraft/modpacks/{curseforge_id}/files"
        result['errors'].append(
            f"CurseForge requires an API key for automatic download. "
            f"Get one at https://console.curseforge.com/ and add CURSEFORGE_API_KEY to .env, "
            f"or download manually from: {manual_url}"
        )
        result['manual_download_url'] = manual_url
        return result
    
    try:
        import aiohttp
        
        headers = {
            "Accept": "application/json",
            "x-api-key": cf_api_key
        }
        
        async with aiohttp.ClientSession() as session:
            # Get mod files
            logger.info(f"Fetching modpack info from CurseForge: {project_id}")
            files_url = f"https://api.curseforge.com/v1/mods/{project_id}/files"
            
            async with session.get(files_url, headers=headers) as response:
                if response.status != 200:
                    result['errors'].append(f"CurseForge API error: {response.status}")
                    logger.error(f"CurseForge API returned {response.status}")
                    return result
                data = await response.json()
            
            files = data.get('data', [])
            if not files:
                result['errors'].append("No files found for this modpack")
                return result
            
            # Filter for server pack if available, otherwise get latest
            server_files = [f for f in files if 'server' in f.get('fileName', '').lower()]
            target_file = server_files[0] if server_files else files[0]
            
            result['version'] = target_file.get('displayName', target_file.get('fileName'))
            logger.info(f"Latest version: {result['version']}")
            
            download_url = target_file.get('downloadUrl')
            if not download_url:
                # CurseForge sometimes doesn't provide direct download URL
                file_id = target_file.get('id')
                result['errors'].append(
                    f"Direct download not available. Please download manually from: "
                    f"https://www.curseforge.com/minecraft/modpacks/{curseforge_id}/files/{file_id}"
                )
                result['manual_download_url'] = f"https://www.curseforge.com/minecraft/modpacks/{curseforge_id}/files/{file_id}"
                return result
            
            filename = target_file.get('fileName')
            logger.info(f"Downloading modpack: {filename}")
            
            # Download file
            modpack_path = os.path.join(MC_SERVER_DIR, filename)
            async with session.get(download_url, headers=headers) as response:
                if response.status != 200:
                    result['errors'].append(f"Failed to download: {response.status}")
                    return result
                
                with open(modpack_path, 'wb') as f:
                    f.write(await response.read())
            
            logger.info(f"Downloaded modpack to {modpack_path}")
            
            # Extract modpack
            if filename.endswith('.zip'):
                install_success = await extract_modpack_zip(modpack_path, result)
            else:
                result['errors'].append(f"Unknown file format: {filename}")
                return result
            
            if install_success:
                result['success'] = True
            
            # Clean up
            if os.path.exists(modpack_path):
                os.remove(modpack_path)
            
    except ImportError:
        error_msg = "aiohttp library is required for modpack downloads. Install with: pip install aiohttp"
        result['errors'].append(error_msg)
        logger.error(error_msg)
    except Exception as e:
        result['errors'].append(f"Error downloading from CurseForge: {e}")
        logger.error(f"Error downloading from CurseForge: {e}")
    
    return result


async def extract_and_install_mrpack(mrpack_path: str, result: Dict) -> bool:
    """
    Extract and install a Modrinth modpack (.mrpack file).
    
    Args:
        mrpack_path: Path to the .mrpack file
        result: Result dictionary to update
        
    Returns:
        True if successful
    """
    import zipfile
    
    try:
        logger.info(f"Extracting modpack from {mrpack_path}")
        
        with zipfile.ZipFile(mrpack_path, 'r') as zf:
            # Read modrinth.index.json
            try:
                index_data = json.loads(zf.read('modrinth.index.json'))
            except KeyError:
                result['errors'].append("Invalid mrpack: missing modrinth.index.json")
                return False
            
            logger.info(f"Modpack: {index_data.get('name')} v{index_data.get('versionId')}")
            
            # Extract overrides (configs, etc.)
            for item in zf.namelist():
                if item.startswith('overrides/') or item.startswith('server-overrides/'):
                    # Remove the prefix
                    if item.startswith('overrides/'):
                        dest_path = item[len('overrides/'):]
                    else:
                        dest_path = item[len('server-overrides/'):]
                    
                    if dest_path:
                        full_dest = os.path.join(MC_SERVER_DIR, dest_path)
                        
                        if item.endswith('/'):
                            os.makedirs(full_dest, exist_ok=True)
                        else:
                            os.makedirs(os.path.dirname(full_dest), exist_ok=True)
                            with open(full_dest, 'wb') as f:
                                f.write(zf.read(item))
                            result['files_installed'].append(dest_path)
                            logger.debug(f"Extracted: {dest_path}")
            
            # Download mods from files list
            files = index_data.get('files', [])
            logger.info(f"Downloading {len(files)} mod files...")
            
            import aiohttp
            headers = {"User-Agent": "SulfurBot/1.0 (github.com/mereMint/sulfur)"}
            
            async with aiohttp.ClientSession() as session:
                for file_info in files:
                    file_path = file_info.get('path', '')
                    downloads = file_info.get('downloads', [])
                    
                    if not downloads:
                        logger.warning(f"No download URL for {file_path}")
                        continue
                    
                    download_url = downloads[0]
                    full_path = os.path.join(MC_SERVER_DIR, file_path)
                    
                    # Create directory if needed
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    
                    # Download file
                    try:
                        async with session.get(download_url, headers=headers) as response:
                            if response.status == 200:
                                with open(full_path, 'wb') as f:
                                    f.write(await response.read())
                                result['files_installed'].append(file_path)
                                logger.info(f"Downloaded: {os.path.basename(file_path)}")
                            else:
                                logger.warning(f"Failed to download {file_path}: {response.status}")
                    except Exception as e:
                        logger.error(f"Error downloading {file_path}: {e}")
        
        logger.info(f"Installed {len(result['files_installed'])} files from modpack")
        return True
        
    except Exception as e:
        result['errors'].append(f"Failed to extract modpack: {e}")
        logger.error(f"Failed to extract modpack: {e}")
        return False


async def extract_modpack_zip(zip_path: str, result: Dict) -> bool:
    """
    Extract a standard modpack zip file.
    
    Args:
        zip_path: Path to the zip file
        result: Result dictionary to update
        
    Returns:
        True if successful
    """
    import zipfile
    
    try:
        logger.info(f"Extracting modpack from {zip_path}")
        
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # Extract all files to server directory
            for item in zf.namelist():
                # Skip directories
                if item.endswith('/'):
                    continue
                
                full_dest = os.path.join(MC_SERVER_DIR, item)
                os.makedirs(os.path.dirname(full_dest), exist_ok=True)
                
                with open(full_dest, 'wb') as f:
                    f.write(zf.read(item))
                
                result['files_installed'].append(item)
                logger.debug(f"Extracted: {item}")
        
        logger.info(f"Extracted {len(result['files_installed'])} files from modpack")
        return True
        
    except Exception as e:
        result['errors'].append(f"Failed to extract modpack: {e}")
        logger.error(f"Failed to extract modpack: {e}")
        return False


async def switch_modpack(
    new_modpack: str,
    config: Dict,
    save_current: bool = True
) -> Dict:
    """
    Switch from current modpack to a new one, handling world saves.
    
    Args:
        new_modpack: The modpack to switch to
        config: Minecraft configuration
        save_current: Whether to save the current world before switching
        
    Returns:
        Result dictionary with switch status
    """
    result = {
        'success': False,
        'previous_modpack': get_current_modpack(),
        'new_modpack': new_modpack,
        'world_saved': False,
        'world_loaded': False,
        'world_generated': False,
        'mods_installed': False,
        'steps': [],
        'errors': []
    }
    
    # Validate new modpack
    if new_modpack not in MODPACKS:
        result['errors'].append(f"Unknown modpack: {new_modpack}")
        return result
    
    current_modpack = get_current_modpack()
    
    # Check if server is running
    if is_server_running():
        result['errors'].append("Cannot switch modpacks while server is running. Stop the server first.")
        return result
    
    result['steps'].append(f"Switching from '{current_modpack}' to '{new_modpack}'...")
    
    # Step 1: Save current world
    if save_current and current_modpack:
        result['steps'].append(f"Saving current world for '{current_modpack}'...")
        success, msg = await save_current_world(current_modpack)
        result['world_saved'] = success
        if success:
            result['steps'].append(f"✅ {msg}")
        else:
            result['steps'].append(f"⚠️ Could not save world: {msg}")
    
    # Step 2: Clear current mods
    result['steps'].append("Removing current mods...")
    await clear_current_mods()
    result['steps'].append("✅ Mods cleared")
    
    # Step 3: Load or generate world for new modpack
    if has_saved_world(new_modpack):
        result['steps'].append(f"Loading saved world for '{new_modpack}'...")
        success, msg = await load_world_for_modpack(new_modpack)
        result['world_loaded'] = success
        if success:
            result['steps'].append(f"✅ {msg}")
        else:
            result['steps'].append(f"⚠️ {msg}")
    else:
        result['steps'].append(f"No saved world for '{new_modpack}', will generate new world on first start")
        result['world_generated'] = True
        
        # Clear existing world to trigger new world generation
        for world_dir in ['world', 'world_nether', 'world_the_end']:
            world_path = os.path.join(MC_SERVER_DIR, world_dir)
            if os.path.exists(world_path):
                shutil.rmtree(world_path)
                result['steps'].append(f"  Removed {world_dir}")
    
    # Step 4: Install new modpack (if not vanilla)
    new_modpack_config = MODPACKS.get(new_modpack)
    if new_modpack != 'vanilla' and new_modpack_config.get('source'):
        result['steps'].append(f"Downloading and installing modpack '{new_modpack}'...")
        
        minecraft_version = config.get('minecraft_version')
        install_result = await install_modpack(new_modpack, minecraft_version)
        
        result['mods_installed'] = install_result.get('success', False)
        result['mods_details'] = {
            'files_installed': install_result.get('files_installed', []),
            'version': install_result.get('version'),
            'source': install_result.get('source')
        }
        
        if result['mods_installed']:
            files_count = len(install_result.get('files_installed', []))
            result['steps'].append(f"✅ Installed modpack ({files_count} files)")
            logger.info(f"Modpack installed successfully: {files_count} files")
        else:
            result['steps'].append(f"⚠️ Modpack installation had issues")
            result['errors'].extend(install_result.get('errors', []))
            for error in install_result.get('errors', []):
                logger.error(f"Modpack error: {error}")
        
        # Step 5: Install AutoModpack for mod syncing (if not already in modpack)
        if not any('automodpack' in f.lower() for f in install_result.get('files_installed', [])):
            result['steps'].append("Setting up AutoModpack for automatic mod syncing...")
            automodpack_result = await download_automodpack(minecraft_version or '1.21.4', 'fabric')
            if automodpack_result.get('success'):
                result['steps'].append("✅ AutoModpack configured - clients will auto-download mods!")
                logger.info("AutoModpack configured successfully")
            else:
                result['steps'].append(f"⚠️ AutoModpack setup failed: {automodpack_result.get('error')}")
                logger.warning(f"AutoModpack setup failed: {automodpack_result.get('error')}")
    else:
        result['steps'].append("Vanilla mode - no mods to install")
        result['mods_installed'] = True
        logger.info("Switched to vanilla mode")
    
    # Step 6: Apply modpack config overrides
    config_overrides = new_modpack_config.get('config_overrides', {})
    if config_overrides:
        result['steps'].append("Applying modpack configuration overrides...")
        # Apply to server.properties
        await apply_server_properties(config_overrides)
        result['steps'].append("✅ Configuration applied")
    
    # Update state
    update_state('current_modpack', new_modpack)
    update_state('modpack_switched_at', datetime.now(timezone.utc).isoformat())
    
    result['success'] = True
    result['steps'].append(f"✅ Successfully switched to '{new_modpack}'!")
    result['steps'].append("Start the server to begin playing")
    
    return result


async def apply_server_properties(overrides: Dict) -> bool:
    """
    Apply configuration overrides to server.properties.
    
    Args:
        overrides: Dictionary of property overrides
        
    Returns:
        True if successful
    """
    properties_path = os.path.join(MC_SERVER_DIR, 'server.properties')
    
    if not os.path.exists(properties_path):
        return False
    
    try:
        # Read current properties
        with open(properties_path, 'r') as f:
            lines = f.readlines()
        
        # Apply overrides
        new_lines = []
        applied = set()
        
        for line in lines:
            if '=' in line and not line.strip().startswith('#'):
                key = line.split('=')[0].strip()
                if key in overrides:
                    new_lines.append(f"{key}={overrides[key]}\n")
                    applied.add(key)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        
        # Add any overrides that weren't in the file
        for key, value in overrides.items():
            if key not in applied:
                new_lines.append(f"{key}={value}\n")
        
        # Write back
        with open(properties_path, 'w') as f:
            f.writelines(new_lines)
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to apply server properties: {e}")
        return False


def list_saved_worlds() -> List[Dict]:
    """
    List all saved worlds for different modpacks.
    
    Returns:
        List of world information dictionaries
    """
    worlds = []
    
    if not os.path.exists(MC_WORLDS_STORAGE_DIR):
        return worlds
    
    for modpack_name in os.listdir(MC_WORLDS_STORAGE_DIR):
        modpack_path = os.path.join(MC_WORLDS_STORAGE_DIR, modpack_name)
        
        if not os.path.isdir(modpack_path):
            continue
        
        world_info = {
            'modpack': modpack_name,
            'display_name': MODPACKS.get(modpack_name, {}).get('name', modpack_name),
            'path': modpack_path,
            'saved_at': None,
            'size_mb': 0
        }
        
        # Get state info
        state_file = os.path.join(modpack_path, 'world_state.json')
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                world_info['saved_at'] = state.get('saved_at')
            except (json.JSONDecodeError, IOError):
                pass
        
        # Calculate size
        total_size = 0
        for root, dirs, files in os.walk(modpack_path):
            for f in files:
                total_size += os.path.getsize(os.path.join(root, f))
        world_info['size_mb'] = round(total_size / 1024 / 1024, 2)
        
        worlds.append(world_info)
    
    return worlds

def is_server_running() -> bool:
    """Check if the Minecraft server is currently running."""
    global _server_process
    
    if _server_process is None:
        return False
    
    return _server_process.returncode is None


async def start_server(config: Dict) -> Tuple[bool, str]:
    """
    Start the Minecraft server.
    
    Args:
        config: The Minecraft configuration
        
    Returns:
        Tuple of (success, message)
    """
    global _server_process, _console_buffer
    
    if is_server_running():
        return False, "Server is already running"
    
    # Check Java - auto-install if not found
    java_ok, java_msg = check_java_requirements()
    if not java_ok:
        logger.info(f"Java check failed: {java_msg}")
        logger.info("Attempting automatic Java 21 installation...")
        
        # Try to install Java automatically
        install_ok, install_msg = await install_java_21()
        if install_ok:
            logger.info(f"Java installation successful: {install_msg}")
            # Re-check Java after installation
            java_ok, java_msg = check_java_requirements()
            if not java_ok:
                return False, f"Java installation succeeded but still not working: {java_msg}"
        else:
            logger.error(f"Automatic Java installation failed: {install_msg}")
            return False, f"Java not available and auto-install failed: {install_msg}. {java_msg}"
    
    java_path = _get_java_path()
    
    # Get server configuration
    server_type = config.get('server_type', 'paper')
    minecraft_version = config.get('minecraft_version', '1.21.4')
    
    # Check for server JAR
    jar_path = _server_state.get('server_jar_path', os.path.join(MC_SERVER_DIR, "server.jar"))
    
    # Check if we need to download the server JAR
    need_download = False
    if not os.path.exists(jar_path):
        logger.info(f"Server JAR not found at {jar_path}, will download")
        need_download = True
    else:
        # Check if version matches - download if version mismatch
        stored_version = _server_state.get('server_version')
        stored_type = _server_state.get('server_jar_type')
        
        if stored_version != minecraft_version or stored_type != server_type:
            logger.info(f"Server version mismatch: {stored_type}/{stored_version} -> {server_type}/{minecraft_version}")
            need_download = True
    
    # Auto-download server JAR if needed
    if need_download:
        logger.info(f"Downloading {server_type} server {minecraft_version}...")
        success, result = await download_server_jar(server_type, minecraft_version)
        if not success:
            return False, f"Failed to download server JAR: {result}"
        jar_path = result
        logger.info(f"Server JAR downloaded to {jar_path}")
    
    # Create eula.txt if it doesn't exist
    eula_path = os.path.join(MC_SERVER_DIR, "eula.txt")
    if not os.path.exists(eula_path):
        with open(eula_path, 'w') as f:
            f.write("# By using this software, you agree to the Minecraft EULA\n")
            f.write("# https://www.minecraft.net/en-us/eula\n")
            f.write("eula=true\n")
        logger.info("Created eula.txt (EULA accepted)")
    
    # Build Java command
    memory_min = config.get('memory_min', '1G')
    memory_max = config.get('memory_max', '4G')
    
    java_args = [
        java_path,
        f'-Xms{memory_min}',
        f'-Xmx{memory_max}',
        '-XX:+UseG1GC',
        '-XX:+ParallelRefProcEnabled',
        '-XX:MaxGCPauseMillis=200',
        '-XX:+UnlockExperimentalVMOptions',
        '-XX:+DisableExplicitGC',
        '-XX:+AlwaysPreTouch',
        '-XX:G1NewSizePercent=30',
        '-XX:G1MaxNewSizePercent=40',
        '-XX:G1HeapRegionSize=8M',
        '-XX:G1ReservePercent=20',
        '-XX:G1HeapWastePercent=5',
        '-XX:G1MixedGCCountTarget=4',
        '-XX:InitiatingHeapOccupancyPercent=15',
        '-XX:G1MixedGCLiveThresholdPercent=90',
        '-XX:G1RSetUpdatingPauseTimePercent=5',
        '-XX:SurvivorRatio=32',
        '-XX:+PerfDisableSharedMem',
        '-XX:MaxTenuringThreshold=1',
        '-Dusing.aikars.flags=https://mcflags.emc.gs',
        '-Daikars.new.flags=true',
        '-jar', os.path.basename(jar_path),
        'nogui'
    ]
    
    # Start the server process
    try:
        _console_buffer.clear()
        
        # Log the command being executed
        logger.info(f"Starting Minecraft server with command:")
        logger.info(f"  Java: {java_path}")
        logger.info(f"  Memory: {memory_min} - {memory_max}")
        logger.info(f"  JAR: {os.path.basename(jar_path)} (full path: {jar_path})")
        logger.info(f"  Working directory: {MC_SERVER_DIR}")
        
        # Verify JAR file exists
        if not os.path.exists(jar_path):
            error_msg = f"Server JAR file not found: {jar_path}"
            logger.error(error_msg)
            return False, error_msg
        
        # Verify working directory exists
        if not os.path.exists(MC_SERVER_DIR):
            error_msg = f"Server directory not found: {MC_SERVER_DIR}"
            logger.error(error_msg)
            return False, error_msg
        
        _server_process = await asyncio.create_subprocess_exec(
            *java_args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=MC_SERVER_DIR
        )
        
        # Start console reader task
        asyncio.create_task(_read_console_output())
        
        update_state('started_at', datetime.now(timezone.utc).isoformat())
        update_state('status', 'starting')
        update_state('memory_min', memory_min)
        update_state('memory_max', memory_max)
        
        logger.info(f"Minecraft server started with PID {_server_process.pid}")
        
        return True, f"Server started with PID {_server_process.pid}"
        
    except FileNotFoundError as e:
        error_msg = f"Java executable not found: {e}"
        logger.error(error_msg)
        return False, error_msg
    except PermissionError as e:
        error_msg = f"Permission denied when starting server: {e}"
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        logger.error(f"Failed to start Minecraft server: {e}")
        logger.error(traceback.format_exc())
        return False, str(e)


async def stop_server(notify_players: bool = True, reason: str = "Server shutdown") -> Tuple[bool, str]:
    """
    Stop the Minecraft server gracefully.
    
    Args:
        notify_players: Whether to notify players before shutdown
        reason: The reason for shutdown
        
    Returns:
        Tuple of (success, message)
    """
    global _server_process
    
    if not is_server_running():
        return False, "Server is not running"
    
    try:
        # Notify players
        if notify_players:
            await send_command(f"say §c[Server] §f{reason}")
            await asyncio.sleep(2)
        
        # Send stop command
        await send_command("stop")
        
        # Wait for server to stop gracefully
        try:
            await asyncio.wait_for(_server_process.wait(), timeout=30)
        except asyncio.TimeoutError:
            # Force kill if it doesn't stop
            _server_process.kill()
            await _server_process.wait()
        
        update_state('status', 'stopped')
        update_state('stopped_at', datetime.now(timezone.utc).isoformat())
        
        _server_process = None
        
        return True, "Server stopped successfully"
        
    except Exception as e:
        logger.error(f"Error stopping server: {e}")
        return False, str(e)


async def restart_server(config: Dict, notify_players: bool = True) -> Tuple[bool, str]:
    """
    Restart the Minecraft server.
    
    Args:
        config: The Minecraft configuration
        notify_players: Whether to notify players before restart
        
    Returns:
        Tuple of (success, message)
    """
    if is_server_running():
        success, msg = await stop_server(notify_players, "Server restarting...")
        if not success:
            return False, f"Failed to stop server: {msg}"
        
        await asyncio.sleep(config.get('restart_delay_seconds', 30))
    
    return await start_server(config)


async def send_command(command: str) -> bool:
    """
    Send a command to the Minecraft server console.
    
    Args:
        command: The command to send (without leading /)
        
    Returns:
        True if command was sent successfully
    """
    global _server_process
    
    if not is_server_running():
        return False
    
    try:
        _server_process.stdin.write(f"{command}\n".encode())
        await _server_process.stdin.drain()
        return True
    except Exception as e:
        logger.error(f"Error sending command: {e}")
        return False


async def _read_console_output():
    """Read and buffer console output from the server."""
    global _server_process, _console_buffer
    
    logger.info("Started reading Minecraft server console output")
    
    while is_server_running():
        try:
            line = await _server_process.stdout.readline()
            if not line:
                logger.warning("Console output stream ended (empty line received)")
                break
            
            decoded_line = line.decode('utf-8', errors='replace').strip()
            if decoded_line:
                timestamp = datetime.now(timezone.utc).strftime('%H:%M:%S')
                formatted_line = f"[{timestamp}] {decoded_line}"
                _console_buffer.append(formatted_line)
                
                # Log all console output to the minecraft log file
                logger.info(f"[Console] {decoded_line}")
                
                # Parse server events
                await _parse_console_line(decoded_line)
                
                # Notify callbacks
                for callback in _console_callbacks:
                    try:
                        await callback(decoded_line)
                    except Exception as e:
                        logger.error(f"Console callback error: {e}")
                        
        except Exception as e:
            if is_server_running():
                logger.error(f"Error reading console: {e}")
            break
    
    # Server stopped
    logger.info("Minecraft server console output ended")
    update_state('status', 'stopped')


async def _parse_console_line(line: str):
    """Parse console lines for events like player joins/leaves."""
    global _player_list
    
    # Player joined
    join_match = re.search(r'(\w+) joined the game', line)
    if join_match:
        player = join_match.group(1)
        if player not in _player_list:
            _player_list.append(player)
        update_state('player_count', len(_player_list))
        logger.info(f"Player {player} joined. Total: {len(_player_list)}")
        return
    
    # Player left
    leave_match = re.search(r'(\w+) left the game', line)
    if leave_match:
        player = leave_match.group(1)
        if player in _player_list:
            _player_list.remove(player)
        update_state('player_count', len(_player_list))
        logger.info(f"Player {player} left. Total: {len(_player_list)}")
        return
    
    # Server done loading
    if 'Done' in line and 'For help' in line:
        update_state('status', 'running')
        logger.info("Minecraft server finished loading")
        return
    
    # Server stopped
    if 'Stopping server' in line:
        update_state('status', 'stopping')
        return


def get_console_output(lines: int = 50) -> List[str]:
    """
    Get recent console output.
    
    Args:
        lines: Number of lines to return
        
    Returns:
        List of console lines
    """
    return list(_console_buffer)[-lines:]


def get_player_count() -> int:
    """Get the current player count."""
    return len(_player_list)


def get_player_list() -> List[str]:
    """Get the list of online players."""
    return _player_list.copy()


def register_console_callback(callback: Callable):
    """Register a callback for console output."""
    _console_callbacks.append(callback)


def unregister_console_callback(callback: Callable):
    """Unregister a console callback."""
    if callback in _console_callbacks:
        _console_callbacks.remove(callback)


# ==============================================================================
# Schedule Management
# ==============================================================================

def should_server_be_running(config: Dict) -> bool:
    """
    Check if the server should be running based on the schedule.
    
    Args:
        config: The Minecraft configuration
        
    Returns:
        True if the server should be running
    """
    if not config.get('enabled', True):
        return False
    
    schedule = config.get('schedule', {})
    mode = schedule.get('mode', 'always')
    
    if mode == 'always':
        return True
    
    now = datetime.now(timezone.utc)
    current_hour = now.hour
    weekday = now.weekday()  # 0 = Monday, 6 = Sunday
    is_weekend = weekday >= 5
    
    if mode == 'timed':
        start_hour = schedule.get('start_hour', 6)
        end_hour = schedule.get('end_hour', 22)
        return start_hour <= current_hour < end_hour
    
    elif mode == 'weekdays_only':
        if is_weekend:
            return False
        weekday_hours = schedule.get('weekday_hours', {})
        start_hour = weekday_hours.get('start', 6)
        end_hour = weekday_hours.get('end', 22)
        return start_hour <= current_hour < end_hour
    
    elif mode == 'weekends_only':
        if not is_weekend:
            return False
        weekend_hours = schedule.get('weekend_hours', {})
        start_hour = weekend_hours.get('start', 0)
        end_hour = weekend_hours.get('end', 24)
        return start_hour <= current_hour < end_hour
    
    elif mode == 'custom':
        custom = schedule.get('custom_schedule', {})
        day_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        day_schedule = custom.get(day_names[weekday], {})
        
        if not day_schedule.get('enabled', True):
            return False
        
        start_hour = day_schedule.get('start', 0)
        end_hour = day_schedule.get('end', 24)
        return start_hour <= current_hour < end_hour
    
    return True


async def schedule_manager_task(config: Dict, get_config_func: Callable):
    """
    Background task that manages the server schedule.
    
    Args:
        config: Initial Minecraft configuration
        get_config_func: Function to get updated config
    """
    global _shutdown_task
    
    while True:
        try:
            # Get fresh config
            current_config = get_config_func()
            mc_config = get_config(current_config)
            
            should_run = should_server_be_running(mc_config)
            currently_running = is_server_running()
            
            if should_run and not currently_running:
                # Start the server
                logger.info("Schedule: Starting server")
                await start_server(mc_config)
                
            elif not should_run and currently_running:
                # Schedule shutdown with warnings
                if _shutdown_task is None or _shutdown_task.done():
                    _shutdown_task = asyncio.create_task(
                        _scheduled_shutdown(mc_config)
                    )
            
            await asyncio.sleep(60)  # Check every minute
            
        except Exception as e:
            logger.error(f"Schedule manager error: {e}")
            await asyncio.sleep(60)


async def _scheduled_shutdown(config: Dict):
    """Handle a scheduled shutdown with player warnings."""
    warning_minutes = config.get('shutdown_warning_minutes', [5, 1])
    
    # Sort warnings in descending order
    warning_minutes = sorted(warning_minutes, reverse=True)
    
    for minutes in warning_minutes:
        if is_server_running():
            await send_command(f"say §c[Server] §fServer wird in {minutes} Minute(n) heruntergefahren!")
            await asyncio.sleep(60)  # Wait 1 minute between warnings
    
    # Final shutdown
    if is_server_running():
        await stop_server(True, "Geplante Wartung. Bis bald!")


# ==============================================================================
# Backup System
# ==============================================================================

async def create_backup(include_mods: bool = False, include_configs: bool = True) -> Tuple[bool, str]:
    """
    Create a backup of the server.
    
    Args:
        include_mods: Whether to include mods in the backup
        include_configs: Whether to include configs in the backup
        
    Returns:
        Tuple of (success, backup_path_or_error)
    """
    os.makedirs(MC_BACKUPS_DIR, exist_ok=True)
    
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    backup_name = f"minecraft_backup_{timestamp}.zip"
    backup_path = os.path.join(MC_BACKUPS_DIR, backup_name)
    
    try:
        # Warn players about backup
        if is_server_running():
            await send_command("say §6[Server] §fBackup wird erstellt, kurze Pause möglich...")
            await send_command("save-all")
            await asyncio.sleep(5)  # Wait for save
        
        # Create backup
        def _create_backup():
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Always backup world
                world_dir = os.path.join(MC_SERVER_DIR, "world")
                if os.path.exists(world_dir):
                    for root, dirs, files in os.walk(world_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, MC_SERVER_DIR)
                            zipf.write(file_path, arcname)
                
                # Backup configs
                if include_configs:
                    config_paths = [
                        os.path.join(MC_SERVER_DIR, "server.properties"),
                        os.path.join(MC_SERVER_DIR, "whitelist.json"),
                        os.path.join(MC_SERVER_DIR, "ops.json"),
                        os.path.join(MC_SERVER_DIR, "banned-players.json"),
                        os.path.join(MC_SERVER_DIR, "banned-ips.json")
                    ]
                    for config_path in config_paths:
                        if os.path.exists(config_path):
                            zipf.write(config_path, os.path.relpath(config_path, MC_SERVER_DIR))
                
                # Backup mods
                if include_mods and os.path.exists(MC_MODS_DIR):
                    for root, dirs, files in os.walk(MC_MODS_DIR):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, MC_SERVER_DIR)
                            zipf.write(file_path, arcname)
        
        # Run backup in executor to avoid blocking
        await asyncio.get_event_loop().run_in_executor(None, _create_backup)
        
        # Update state
        backup_size = os.path.getsize(backup_path)
        update_state('last_backup', {
            'path': backup_path,
            'timestamp': timestamp,
            'size_bytes': backup_size
        })
        
        logger.info(f"Created backup: {backup_path} ({backup_size / 1024 / 1024:.1f} MB)")
        
        if is_server_running():
            await send_command("say §a[Server] §fBackup erfolgreich erstellt!")
        
        return True, backup_path
        
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        return False, str(e)


async def restore_backup(backup_path: str) -> Tuple[bool, str]:
    """
    Restore a backup.
    
    Args:
        backup_path: Path to the backup zip file
        
    Returns:
        Tuple of (success, message)
    """
    if not os.path.exists(backup_path):
        return False, f"Backup not found: {backup_path}"
    
    if is_server_running():
        return False, "Stop the server before restoring a backup"
    
    try:
        def _restore():
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                zipf.extractall(MC_SERVER_DIR)
        
        await asyncio.get_event_loop().run_in_executor(None, _restore)
        
        logger.info(f"Restored backup from {backup_path}")
        return True, "Backup restored successfully"
        
    except Exception as e:
        logger.error(f"Restore failed: {e}")
        return False, str(e)


def list_backups() -> List[Dict]:
    """
    List all available backups.
    
    Returns:
        List of backup information dictionaries
    """
    backups = []
    
    if not os.path.exists(MC_BACKUPS_DIR):
        return backups
    
    for filename in os.listdir(MC_BACKUPS_DIR):
        if filename.endswith('.zip') and filename.startswith('minecraft_backup_'):
            backup_path = os.path.join(MC_BACKUPS_DIR, filename)
            stat = os.stat(backup_path)
            
            backups.append({
                'filename': filename,
                'path': backup_path,
                'size_bytes': stat.st_size,
                'size_mb': round(stat.st_size / 1024 / 1024, 2),
                'created': datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
            })
    
    # Sort by creation time, newest first
    backups.sort(key=lambda x: x['created'], reverse=True)
    
    return backups


async def cleanup_old_backups(max_backups: int = 10):
    """
    Remove old backups, keeping only the most recent ones.
    
    Args:
        max_backups: Maximum number of backups to keep
    """
    backups = list_backups()
    
    if len(backups) <= max_backups:
        return
    
    # Delete oldest backups
    for backup in backups[max_backups:]:
        try:
            os.remove(backup['path'])
            logger.info(f"Deleted old backup: {backup['filename']}")
        except Exception as e:
            logger.error(f"Failed to delete backup {backup['filename']}: {e}")


async def backup_manager_task(config: Dict):
    """Background task that manages automatic backups."""
    while True:
        try:
            backup_config = config.get('backups', {})
            
            if not backup_config.get('enabled', True):
                await asyncio.sleep(3600)  # Check again in 1 hour
                continue
            
            interval_hours = backup_config.get('interval_hours', 6)
            
            # Wait for interval
            await asyncio.sleep(interval_hours * 3600)
            
            # Create backup if server is running
            if is_server_running():
                success, result = await create_backup(
                    include_mods=backup_config.get('include_mods', False),
                    include_configs=backup_config.get('include_configs', True)
                )
                
                if success:
                    # Cleanup old backups
                    await cleanup_old_backups(backup_config.get('max_backups', 10))
            
        except Exception as e:
            logger.error(f"Backup manager error: {e}")
            await asyncio.sleep(3600)


# ==============================================================================
# Whitelist Management
# ==============================================================================

def get_whitelist() -> List[Dict]:
    """Get the server whitelist."""
    whitelist_path = os.path.join(MC_SERVER_DIR, "whitelist.json")
    
    if not os.path.exists(whitelist_path):
        return []
    
    try:
        with open(whitelist_path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


async def get_minecraft_uuid(username: str) -> Optional[str]:
    """
    Get the UUID for a Minecraft username from Mojang API.
    
    Args:
        username: The Minecraft username
        
    Returns:
        UUID string with dashes, or None if not found
    """
    
    def format_uuid(uuid_no_dashes: str) -> str:
        """Format a 32-char UUID string with dashes."""
        return f"{uuid_no_dashes[:8]}-{uuid_no_dashes[8:12]}-{uuid_no_dashes[12:16]}-{uuid_no_dashes[16:20]}-{uuid_no_dashes[20:]}"
    
    try:
        import aiohttp
        url = f"https://api.mojang.com/users/profiles/minecraft/{username}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    uuid_no_dashes = data.get('id', '')
                    if uuid_no_dashes and len(uuid_no_dashes) == 32:
                        return format_uuid(uuid_no_dashes)
                elif response.status == 404:
                    logger.warning(f"Minecraft username '{username}' not found in Mojang API")
                else:
                    logger.error(f"Mojang API error: {response.status}")
    except ImportError:
        # Fallback to urllib if aiohttp not available
        try:
            url = f"https://api.mojang.com/users/profiles/minecraft/{username}"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    uuid_no_dashes = data.get('id', '')
                    if uuid_no_dashes and len(uuid_no_dashes) == 32:
                        return format_uuid(uuid_no_dashes)
        except Exception as e:
            logger.error(f"Error fetching UUID with urllib: {e}")
    except Exception as e:
        logger.error(f"Error fetching UUID for {username}: {e}")
    
    return None


async def add_to_whitelist(minecraft_username: str) -> Tuple[bool, str]:
    """
    Add a player to the whitelist.
    
    Args:
        minecraft_username: The player's Minecraft username
        
    Returns:
        Tuple of (success, message)
    """
    if is_server_running():
        # Use server command
        await send_command(f"whitelist add {minecraft_username}")
        return True, f"Added {minecraft_username} to whitelist"
    else:
        # Manually edit whitelist.json
        whitelist_path = os.path.join(MC_SERVER_DIR, "whitelist.json")
        
        whitelist = get_whitelist()
        
        # Check if already whitelisted
        for entry in whitelist:
            if entry.get('name', '').lower() == minecraft_username.lower():
                return False, f"{minecraft_username} is already whitelisted"
        
        # Fetch UUID from Mojang API
        player_uuid = await get_minecraft_uuid(minecraft_username)
        
        if not player_uuid:
            return False, f"Could not find Minecraft account for '{minecraft_username}'. Make sure the username is correct and the player has a valid Minecraft account."
        
        # Add to whitelist with proper UUID
        whitelist.append({
            "name": minecraft_username,
            "uuid": player_uuid
        })
        
        try:
            with open(whitelist_path, 'w') as f:
                json.dump(whitelist, f, indent=2)
            logger.info(f"Added {minecraft_username} (UUID: {player_uuid}) to whitelist")
            return True, f"Added {minecraft_username} to whitelist"
        except IOError as e:
            return False, f"Failed to update whitelist: {e}"


async def remove_from_whitelist(minecraft_username: str) -> Tuple[bool, str]:
    """
    Remove a player from the whitelist.
    
    Args:
        minecraft_username: The player's Minecraft username
        
    Returns:
        Tuple of (success, message)
    """
    if is_server_running():
        await send_command(f"whitelist remove {minecraft_username}")
        return True, f"Removed {minecraft_username} from whitelist"
    else:
        whitelist_path = os.path.join(MC_SERVER_DIR, "whitelist.json")
        whitelist = get_whitelist()
        
        original_len = len(whitelist)
        whitelist = [e for e in whitelist if e.get('name', '').lower() != minecraft_username.lower()]
        
        if len(whitelist) == original_len:
            return False, f"{minecraft_username} is not whitelisted"
        
        try:
            with open(whitelist_path, 'w') as f:
                json.dump(whitelist, f, indent=2)
            return True, f"Removed {minecraft_username} from whitelist"
        except IOError as e:
            return False, f"Failed to update whitelist: {e}"


# ==============================================================================
# World Management
# ==============================================================================

def list_worlds() -> List[Dict]:
    """List all worlds in the server directory."""
    worlds = []
    
    # Check for main world directories
    world_names = ['world', 'world_nether', 'world_the_end']
    
    for world_name in world_names:
        world_path = os.path.join(MC_SERVER_DIR, world_name)
        if os.path.exists(world_path) and os.path.isdir(world_path):
            # Calculate size
            total_size = 0
            for root, dirs, files in os.walk(world_path):
                for f in files:
                    total_size += os.path.getsize(os.path.join(root, f))
            
            worlds.append({
                'name': world_name,
                'path': world_path,
                'size_bytes': total_size,
                'size_mb': round(total_size / 1024 / 1024, 2)
            })
    
    return worlds


async def delete_world(world_name: str, create_backup: bool = True) -> Tuple[bool, str]:
    """
    Delete a world.
    
    Args:
        world_name: The name of the world to delete
        create_backup: Whether to create a backup first
        
    Returns:
        Tuple of (success, message)
    """
    if is_server_running():
        return False, "Stop the server before deleting worlds"
    
    world_path = os.path.join(MC_SERVER_DIR, world_name)
    
    if not os.path.exists(world_path):
        return False, f"World '{world_name}' not found"
    
    try:
        if create_backup:
            success, backup_result = await create_backup(include_mods=False, include_configs=False)
            if not success:
                return False, f"Failed to create backup before deletion: {backup_result}"
        
        # Delete the world directory
        shutil.rmtree(world_path)
        
        logger.info(f"Deleted world: {world_name}")
        return True, f"World '{world_name}' deleted successfully"
        
    except Exception as e:
        logger.error(f"Failed to delete world: {e}")
        return False, str(e)


# ==============================================================================
# Server Status
# ==============================================================================

def get_server_status() -> Dict:
    """Get comprehensive server status information."""
    status = {
        'running': is_server_running(),
        'pid': _server_process.pid if _server_process else None,
        'player_count': get_player_count(),
        'players': get_player_list(),
        'uptime': None,
        'memory_usage': None,
        'memory_min': _server_state.get('memory_min', '1G'),
        'memory_max': _server_state.get('memory_max', '4G'),
        'server_type': _server_state.get('server_jar_type'),
        'version': _server_state.get('server_version'),
        'last_backup': _server_state.get('last_backup'),
        'status': _server_state.get('status', 'unknown')
    }
    
    # Calculate uptime
    started_at = _server_state.get('started_at')
    if started_at and is_server_running():
        try:
            start_time = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
            uptime = datetime.now(timezone.utc) - start_time
            status['uptime'] = str(uptime).split('.')[0]  # Remove microseconds
        except (ValueError, TypeError):
            pass
    
    return status


def get_installation_status() -> Dict:
    """Get installation status information."""
    java_ok, java_msg = check_java_requirements()
    
    jar_exists = os.path.exists(_server_state.get('server_jar_path', os.path.join(MC_SERVER_DIR, "server.jar")))
    
    return {
        'java_installed': java_ok,
        'java_message': java_msg,
        'java_version': get_java_version(),
        'server_jar_exists': jar_exists,
        'server_type': _server_state.get('server_jar_type'),
        'server_version': _server_state.get('server_version'),
        'server_directory': MC_SERVER_DIR,
        'platform': _get_platform()
    }


# ==============================================================================
# Database Tables Initialization
# ==============================================================================

async def initialize_minecraft_tables(db_helpers):
    """
    Initialize database tables for Minecraft server management.
    
    Args:
        db_helpers: The database helpers module
    """
    if not db_helpers.db_pool:
        logger.warning("Database pool not available, skipping Minecraft table init")
        return
    
    conn = None
    cursor = None
    
    try:
        conn = db_helpers.get_db_connection()
        if not conn:
            return
        
        cursor = conn.cursor()
        
        # Create minecraft_join_requests table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS minecraft_join_requests (
                id INT AUTO_INCREMENT PRIMARY KEY,
                discord_user_id BIGINT NOT NULL,
                minecraft_username VARCHAR(32) NOT NULL,
                status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
                requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP NULL,
                processed_by BIGINT NULL,
                notes TEXT,
                INDEX idx_discord_user (discord_user_id),
                INDEX idx_status (status),
                UNIQUE KEY unique_discord_mc (discord_user_id, minecraft_username)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # Create minecraft_players table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS minecraft_players (
                id INT AUTO_INCREMENT PRIMARY KEY,
                discord_user_id BIGINT NOT NULL UNIQUE,
                minecraft_username VARCHAR(32) NOT NULL,
                minecraft_uuid VARCHAR(36),
                whitelisted BOOLEAN DEFAULT FALSE,
                first_joined TIMESTAMP NULL,
                last_seen TIMESTAMP NULL,
                play_time_minutes INT DEFAULT 0,
                INDEX idx_discord (discord_user_id),
                INDEX idx_mc_username (minecraft_username)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # Create minecraft_server_logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS minecraft_server_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                event_type ENUM('start', 'stop', 'crash', 'restart', 'backup', 'player_join', 'player_leave') NOT NULL,
                event_data JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_type (event_type),
                INDEX idx_created (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        conn.commit()
        logger.info("Minecraft database tables initialized")
        
    except Exception as e:
        logger.error(f"Error initializing Minecraft tables: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ==============================================================================
# Module Initialization
# ==============================================================================

# Load state on module import
load_state()
