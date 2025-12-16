"""
WireGuard VPN Manager Module for Sulfur Bot

Provides WireGuard VPN configuration and management for remote access to the bot.
Supports multiple platforms: Termux/Android, Linux, Windows, and Raspberry Pi.
"""

import asyncio
import os
import platform
import subprocess
import shutil
from typing import Optional, Dict, Tuple
from modules.logger_utils import bot_logger as logger

# WireGuard configuration defaults
WG_INTERFACE = "wg0"
WG_PORT = 51820
WG_CONFIG_DIR = "config/wireguard"


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


def is_wireguard_installed() -> bool:
    """Check if WireGuard is installed on the system."""
    plat = _get_platform()
    
    if plat == 'windows':
        # Check Windows installation
        wg_path = shutil.which('wg.exe')
        if wg_path:
            return True
        # Check default install location
        default_paths = [
            r'C:\Program Files\WireGuard\wg.exe',
            r'C:\Program Files (x86)\WireGuard\wg.exe'
        ]
        return any(os.path.exists(p) for p in default_paths)
    else:
        # Unix-like systems
        return shutil.which('wg') is not None


def get_wg_binary_path() -> Optional[str]:
    """Get the path to the WireGuard binary."""
    plat = _get_platform()
    
    if plat == 'windows':
        wg_path = shutil.which('wg.exe')
        if wg_path:
            return wg_path
        default_paths = [
            r'C:\Program Files\WireGuard\wg.exe',
            r'C:\Program Files (x86)\WireGuard\wg.exe'
        ]
        for path in default_paths:
            if os.path.exists(path):
                return path
        return None
    else:
        return shutil.which('wg')


def generate_keypair() -> Tuple[str, str]:
    """
    Generate a WireGuard private and public key pair.
    
    Returns:
        Tuple of (private_key, public_key)
    """
    wg_path = get_wg_binary_path()
    if not wg_path:
        raise RuntimeError("WireGuard is not installed")
    
    plat = _get_platform()
    
    try:
        if plat == 'windows':
            # Windows: use wg.exe genkey and wg.exe pubkey
            result = subprocess.run([wg_path, 'genkey'], capture_output=True, text=True, check=True)
            private_key = result.stdout.strip()
            
            result = subprocess.run([wg_path, 'pubkey'], input=private_key, capture_output=True, text=True, check=True)
            public_key = result.stdout.strip()
        else:
            # Unix: use wg genkey and wg pubkey
            result = subprocess.run(['wg', 'genkey'], capture_output=True, text=True, check=True)
            private_key = result.stdout.strip()
            
            result = subprocess.run(['wg', 'pubkey'], input=private_key, capture_output=True, text=True, check=True)
            public_key = result.stdout.strip()
        
        return private_key, public_key
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to generate WireGuard keypair: {e}")
        raise RuntimeError(f"Failed to generate keypair: {e.stderr}")


def generate_server_config(
    server_private_key: str,
    server_address: str = "10.0.0.1/24",
    listen_port: int = WG_PORT,
    peers: list = None
) -> str:
    """
    Generate a WireGuard server configuration.
    
    Args:
        server_private_key: The server's private key
        server_address: The server's VPN address (e.g., "10.0.0.1/24")
        listen_port: The UDP port to listen on
        peers: List of peer configurations
        
    Returns:
        WireGuard configuration file content
    """
    config = f"""[Interface]
# Sulfur Bot WireGuard Server
PrivateKey = {server_private_key}
Address = {server_address}
ListenPort = {listen_port}

# Enable IP forwarding for routing
PostUp = sysctl -w net.ipv4.ip_forward=1 || echo "IP forwarding may need manual configuration"
PostDown = sysctl -w net.ipv4.ip_forward=0 || true
"""
    
    if peers:
        for peer in peers:
            config += f"""
[Peer]
# {peer.get('name', 'Unknown Peer')}
PublicKey = {peer['public_key']}
AllowedIPs = {peer.get('allowed_ips', '10.0.0.2/32')}
"""
            if peer.get('preshared_key'):
                config += f"PresharedKey = {peer['preshared_key']}\n"
    
    return config


def generate_client_config(
    client_private_key: str,
    client_address: str,
    server_public_key: str,
    server_endpoint: str,
    dns: str = "1.1.1.1, 8.8.8.8"
) -> str:
    """
    Generate a WireGuard client configuration.
    
    Args:
        client_private_key: The client's private key
        client_address: The client's VPN address (e.g., "10.0.0.2/32")
        server_public_key: The server's public key
        server_endpoint: The server's public endpoint (e.g., "example.com:51820")
        dns: DNS servers to use when connected
        
    Returns:
        WireGuard configuration file content
    """
    config = f"""[Interface]
# Sulfur Bot WireGuard Client
PrivateKey = {client_private_key}
Address = {client_address}
DNS = {dns}

[Peer]
PublicKey = {server_public_key}
Endpoint = {server_endpoint}
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25
"""
    return config


async def get_interface_status(interface: str = WG_INTERFACE) -> Dict:
    """
    Get the status of a WireGuard interface.
    
    Returns:
        Dictionary with interface status information
    """
    result = {
        'exists': False,
        'active': False,
        'public_key': None,
        'listen_port': None,
        'peers': [],
        'error': None
    }
    
    if not is_wireguard_installed():
        result['error'] = 'WireGuard is not installed'
        return result
    
    plat = _get_platform()
    
    try:
        if plat == 'windows':
            # Windows: use wg show
            wg_path = get_wg_binary_path()
            proc = await asyncio.create_subprocess_exec(
                wg_path, 'show', interface,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
        else:
            proc = await asyncio.create_subprocess_exec(
                'wg', 'show', interface,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
        
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            if b'not found' in stderr or b'does not exist' in stderr:
                result['error'] = 'Interface does not exist'
            else:
                result['error'] = stderr.decode().strip()
            return result
        
        result['exists'] = True
        result['active'] = True
        
        # Parse output
        output = stdout.decode()
        current_peer = None
        
        for line in output.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('interface:'):
                continue
            elif line.startswith('public key:'):
                result['public_key'] = line.split(':', 1)[1].strip()
            elif line.startswith('listening port:'):
                result['listen_port'] = int(line.split(':', 1)[1].strip())
            elif line.startswith('peer:'):
                if current_peer:
                    result['peers'].append(current_peer)
                current_peer = {
                    'public_key': line.split(':', 1)[1].strip(),
                    'endpoint': None,
                    'allowed_ips': None,
                    'latest_handshake': None,
                    'transfer_rx': 0,
                    'transfer_tx': 0
                }
            elif current_peer:
                if line.startswith('endpoint:'):
                    current_peer['endpoint'] = line.split(':', 1)[1].strip()
                elif line.startswith('allowed ips:'):
                    current_peer['allowed_ips'] = line.split(':', 1)[1].strip()
                elif line.startswith('latest handshake:'):
                    current_peer['latest_handshake'] = line.split(':', 1)[1].strip()
                elif line.startswith('transfer:'):
                    transfer = line.split(':', 1)[1].strip()
                    # Parse transfer: X received, Y sent
                    parts = transfer.split(',')
                    if len(parts) >= 2:
                        current_peer['transfer_rx'] = parts[0].replace('received', '').strip()
                        current_peer['transfer_tx'] = parts[1].replace('sent', '').strip()
        
        if current_peer:
            result['peers'].append(current_peer)
        
    except Exception as e:
        logger.error(f"Error getting WireGuard status: {e}")
        result['error'] = str(e)
    
    return result


async def start_interface(interface: str = WG_INTERFACE) -> Tuple[bool, str]:
    """
    Start a WireGuard interface.
    
    Returns:
        Tuple of (success, message)
    """
    plat = _get_platform()
    
    try:
        if plat == 'windows':
            # Windows: use wireguard.exe /installtunnelservice
            wg_path = get_wg_binary_path()
            if wg_path:
                wg_dir = os.path.dirname(wg_path)
                wireguard_exe = os.path.join(wg_dir, 'wireguard.exe')
                config_path = os.path.join(WG_CONFIG_DIR, f'{interface}.conf')
                
                if not os.path.exists(config_path):
                    return False, f"Configuration file not found: {config_path}"
                
                proc = await asyncio.create_subprocess_exec(
                    wireguard_exe, '/installtunnelservice', config_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                _, stderr = await proc.communicate()
                
                if proc.returncode != 0:
                    return False, stderr.decode()
                return True, "Interface started successfully"
        
        elif plat == 'termux':
            # Termux: requires root or special setup
            config_path = os.path.join(WG_CONFIG_DIR, f'{interface}.conf')
            
            if not os.path.exists(config_path):
                return False, f"Configuration file not found: {config_path}"
            
            # Try wg-quick first
            proc = await asyncio.create_subprocess_exec(
                'wg-quick', 'up', config_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                return False, f"Failed to start interface: {stderr.decode()}"
            return True, "Interface started successfully"
        
        else:
            # Linux/Raspberry Pi: use wg-quick or systemctl
            # Try wg-quick first
            proc = await asyncio.create_subprocess_exec(
                'wg-quick', 'up', interface,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await proc.communicate()
            
            if proc.returncode == 0:
                return True, "Interface started successfully"
            
            # Fallback to systemctl
            proc = await asyncio.create_subprocess_exec(
                'systemctl', 'start', f'wg-quick@{interface}',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                return False, f"Failed to start interface: {stderr.decode()}"
            return True, "Interface started successfully"
            
    except FileNotFoundError as e:
        return False, f"WireGuard tools not found: {e}"
    except Exception as e:
        logger.error(f"Error starting WireGuard interface: {e}")
        return False, str(e)


async def stop_interface(interface: str = WG_INTERFACE) -> Tuple[bool, str]:
    """
    Stop a WireGuard interface.
    
    Returns:
        Tuple of (success, message)
    """
    plat = _get_platform()
    
    try:
        if plat == 'windows':
            wg_path = get_wg_binary_path()
            if wg_path:
                wg_dir = os.path.dirname(wg_path)
                wireguard_exe = os.path.join(wg_dir, 'wireguard.exe')
                
                proc = await asyncio.create_subprocess_exec(
                    wireguard_exe, '/uninstalltunnelservice', interface,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                _, stderr = await proc.communicate()
                
                if proc.returncode != 0:
                    return False, stderr.decode()
                return True, "Interface stopped successfully"
        
        elif plat == 'termux':
            config_path = os.path.join(WG_CONFIG_DIR, f'{interface}.conf')
            
            proc = await asyncio.create_subprocess_exec(
                'wg-quick', 'down', config_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                return False, f"Failed to stop interface: {stderr.decode()}"
            return True, "Interface stopped successfully"
        
        else:
            # Linux/Raspberry Pi
            proc = await asyncio.create_subprocess_exec(
                'wg-quick', 'down', interface,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await proc.communicate()
            
            if proc.returncode == 0:
                return True, "Interface stopped successfully"
            
            # Fallback to systemctl
            proc = await asyncio.create_subprocess_exec(
                'systemctl', 'stop', f'wg-quick@{interface}',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                return False, f"Failed to stop interface: {stderr.decode()}"
            return True, "Interface stopped successfully"
            
    except FileNotFoundError as e:
        return False, f"WireGuard tools not found: {e}"
    except Exception as e:
        logger.error(f"Error stopping WireGuard interface: {e}")
        return False, str(e)


def get_installation_instructions() -> str:
    """Get platform-specific WireGuard installation instructions."""
    plat = _get_platform()
    
    instructions = {
        'windows': """
**Windows Installation:**
1. Download WireGuard from https://www.wireguard.com/install/
2. Run the installer
3. Restart the bot after installation
""",
        'linux': """
**Linux Installation:**
```bash
# Debian/Ubuntu
sudo apt update && sudo apt install wireguard

# Fedora
sudo dnf install wireguard-tools

# Arch Linux
sudo pacman -S wireguard-tools
```
""",
        'termux': """
**Termux Installation:**
```bash
# Update packages
pkg update && pkg upgrade

# Install WireGuard tools
pkg install wireguard-tools

# Note: Full WireGuard VPN requires root access on Android
```
""",
        'raspberrypi': """
**Raspberry Pi Installation:**
```bash
sudo apt update && sudo apt install wireguard

# Enable kernel module
sudo modprobe wireguard
```
"""
    }
    
    return instructions.get(plat, instructions['linux'])


def ensure_config_dir():
    """Ensure the WireGuard configuration directory exists."""
    os.makedirs(WG_CONFIG_DIR, exist_ok=True)


def save_config(config_content: str, filename: str = f"{WG_INTERFACE}.conf") -> str:
    """
    Save a WireGuard configuration file.
    
    Args:
        config_content: The configuration file content
        filename: The filename (default: wg0.conf)
        
    Returns:
        The full path to the saved configuration file
    """
    ensure_config_dir()
    config_path = os.path.join(WG_CONFIG_DIR, filename)
    
    with open(config_path, 'w') as f:
        f.write(config_content)
    
    # Set secure permissions on Unix
    if platform.system() != 'Windows':
        os.chmod(config_path, 0o600)
    
    logger.info(f"Saved WireGuard configuration to {config_path}")
    return config_path


async def setup_wireguard_server(
    server_endpoint: str,
    server_address: str = "10.0.0.1/24",
    listen_port: int = WG_PORT
) -> Dict:
    """
    Set up a WireGuard server configuration.
    
    Args:
        server_endpoint: The server's public endpoint (hostname or IP)
        server_address: The server's VPN address
        listen_port: The UDP port to listen on
        
    Returns:
        Dictionary with server configuration details
    """
    if not is_wireguard_installed():
        return {
            'success': False,
            'error': 'WireGuard is not installed',
            'instructions': get_installation_instructions()
        }
    
    try:
        # Generate server keys
        private_key, public_key = generate_keypair()
        
        # Generate server configuration
        config = generate_server_config(
            server_private_key=private_key,
            server_address=server_address,
            listen_port=listen_port
        )
        
        # Save configuration
        config_path = save_config(config)
        
        return {
            'success': True,
            'public_key': public_key,
            'config_path': config_path,
            'endpoint': f"{server_endpoint}:{listen_port}",
            'address': server_address,
            'message': 'WireGuard server configuration created successfully'
        }
        
    except Exception as e:
        logger.error(f"Error setting up WireGuard server: {e}")
        return {
            'success': False,
            'error': str(e)
        }


async def add_client(
    client_name: str,
    client_address: str,
    server_public_key: str,
    server_endpoint: str
) -> Dict:
    """
    Add a new client to the WireGuard VPN.
    
    Args:
        client_name: A friendly name for the client
        client_address: The client's VPN address (e.g., "10.0.0.2/32")
        server_public_key: The server's public key
        server_endpoint: The server's endpoint (e.g., "example.com:51820")
        
    Returns:
        Dictionary with client configuration details
    """
    if not is_wireguard_installed():
        return {
            'success': False,
            'error': 'WireGuard is not installed'
        }
    
    try:
        # Generate client keys
        private_key, public_key = generate_keypair()
        
        # Generate client configuration
        config = generate_client_config(
            client_private_key=private_key,
            client_address=client_address,
            server_public_key=server_public_key,
            server_endpoint=server_endpoint
        )
        
        # Save client configuration
        safe_name = "".join(c for c in client_name if c.isalnum() or c in '-_').lower()
        config_path = save_config(config, f"client_{safe_name}.conf")
        
        return {
            'success': True,
            'client_name': client_name,
            'public_key': public_key,
            'private_key': private_key,  # Client needs this
            'address': client_address,
            'config_path': config_path,
            'config_content': config,  # For easy copy/paste
            'message': f'Client configuration for {client_name} created successfully'
        }
        
    except Exception as e:
        logger.error(f"Error adding WireGuard client: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def get_vpn_status_embed_data() -> Dict:
    """
    Get VPN status information formatted for a Discord embed.
    
    Returns:
        Dictionary with status information for embed fields
    """
    is_installed = is_wireguard_installed()
    plat = _get_platform()
    
    return {
        'installed': is_installed,
        'platform': plat,
        'config_dir': WG_CONFIG_DIR,
        'default_port': WG_PORT,
        'interface': WG_INTERFACE
    }
