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
import zipfile
import urllib.request
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Tuple, Callable
from collections import deque
from modules.logger_utils import bot_logger as logger

# ==============================================================================
# Configuration Constants
# ==============================================================================

MC_SERVER_DIR = "minecraft_server"
MC_BACKUPS_DIR = "minecraft_backups"
MC_MODS_DIR = os.path.join(MC_SERVER_DIR, "mods")
MC_CONFIG_DIR = os.path.join(MC_SERVER_DIR, "config")
MC_WORLDS_DIR = os.path.join(MC_SERVER_DIR, "world")
MC_PLUGINS_DIR = os.path.join(MC_SERVER_DIR, "plugins")
MC_STATE_FILE = "config/minecraft_state.json"

# Default server configuration
DEFAULT_MC_CONFIG = {
    "enabled": True,
    "server_type": "paper",  # vanilla, paper, purpur, fabric
    "minecraft_version": "1.21.4",
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

# Supported modpacks
MODPACKS = {
    "raspberry_flavoured": {
        "name": "Raspberry Flavoured",
        "description": "Lightweight vanilla+ experience",
        "server_type": "fabric",
        "modrinth_id": None,  # If available on Modrinth
        "curseforge_id": None  # If available on CurseForge
    },
    "melatonin": {
        "name": "Melatonin",
        "description": "Performance-focused modpack",
        "server_type": "fabric",
        "modrinth_id": None,
        "curseforge_id": None
    },
    "homestead": {
        "name": "Homestead",
        "description": "Survival and building focused",
        "server_type": "fabric",
        "modrinth_id": None,
        "curseforge_id": None
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
        progress_callback: Optional callback for progress updates
        
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
                    
                    with open(dest_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                            downloaded += len(chunk)
                            if progress_callback and total_size > 0:
                                progress_callback(downloaded / total_size)
            return True
        except ImportError:
            # Fallback to urllib (sync)
            def _download():
                urllib.request.urlretrieve(url, dest_path)
            
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
# Server Process Management
# ==============================================================================

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
    
    # Check Java
    java_ok, java_msg = check_java_requirements()
    if not java_ok:
        return False, java_msg
    
    java_path = _get_java_path()
    
    # Check for server JAR
    jar_path = _server_state.get('server_jar_path', os.path.join(MC_SERVER_DIR, "server.jar"))
    
    if not os.path.exists(jar_path):
        return False, f"Server JAR not found at {jar_path}. Run setup first."
    
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
        '-jar', jar_path,
        'nogui'
    ]
    
    # Start the server process
    try:
        _console_buffer.clear()
        
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
        
        logger.info(f"Minecraft server started with PID {_server_process.pid}")
        
        return True, f"Server started with PID {_server_process.pid}"
        
    except Exception as e:
        logger.error(f"Failed to start Minecraft server: {e}")
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
    
    while is_server_running():
        try:
            line = await _server_process.stdout.readline()
            if not line:
                break
            
            decoded_line = line.decode('utf-8', errors='replace').strip()
            if decoded_line:
                timestamp = datetime.now(timezone.utc).strftime('%H:%M:%S')
                _console_buffer.append(f"[{timestamp}] {decoded_line}")
                
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
        
        # Add to whitelist (we'd need UUID lookup for proper entry)
        whitelist.append({
            "name": minecraft_username,
            "uuid": ""  # UUID would need to be fetched from Mojang API
        })
        
        try:
            with open(whitelist_path, 'w') as f:
                json.dump(whitelist, f, indent=2)
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
