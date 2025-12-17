"""
WireGuard VPN Manager Module for Sulfur Bot

Provides WireGuard VPN configuration and management for remote access to the bot.
Supports multiple platforms: Termux/Android, Linux, Windows, and Raspberry Pi.

For non-rooted Termux/Android devices, this module generates configuration files
that can be imported into the official WireGuard Android app.
"""

import asyncio
import os
import platform
import subprocess
import shutil
import json
import base64
from typing import Optional, Dict, Tuple, List
from modules.logger_utils import vpn_logger as logger

# WireGuard configuration defaults
WG_INTERFACE = "wg0"
WG_PORT = 51820
WG_CONFIG_DIR = "config/wireguard"
WG_EXPORT_DIR = "config/wireguard/export"  # For exporting configs to Android app

# Path where Termux can share files with Android
TERMUX_SHARED_DIR = "/storage/emulated/0/Download/SulfurVPN"


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
    peers: list = None,
    network_interface: str = None
) -> str:
    """
    Generate a WireGuard server configuration.
    
    Args:
        server_private_key: The server's private key
        server_address: The server's VPN address (e.g., "10.0.0.1/24")
        listen_port: The UDP port to listen on
        peers: List of peer configurations
        network_interface: Network interface for NAT (auto-detected if None)
        
    Returns:
        WireGuard configuration file content
    """
    # Auto-detect network interface if not specified
    if not network_interface:
        network_interface = _detect_default_interface()
    
    plat = _get_platform()
    
    # Build PostUp and PostDown commands for full tunnel support
    if plat == 'windows':
        # Windows handles routing differently
        post_up = "# Windows: NAT is handled by the WireGuard service"
        post_down = "# Windows: Cleanup handled automatically"
    elif plat == 'termux':
        # Termux without root - limited functionality
        post_up = "# Termux: Full routing requires root access"
        post_down = "# Termux: See docs/TERMUX.md for non-root VPN setup"
    else:
        # Linux/Raspberry Pi - Full NAT support for routing all traffic
        # Extract the network portion from server_address for restrictive rules
        vpn_network = server_address.rsplit('.', 1)[0] + '.0/24'  # e.g., 10.0.0.0/24
        
        post_up = f"""# Enable IP forwarding and NAT for full tunnel mode
PostUp = sysctl -w net.ipv4.ip_forward=1
PostUp = sysctl -w net.ipv6.conf.all.forwarding=1 2>/dev/null || true
PostUp = iptables -t nat -A POSTROUTING -s {vpn_network} -o {network_interface} -j MASQUERADE
PostUp = iptables -A FORWARD -i %i -s {vpn_network} -j ACCEPT
PostUp = iptables -A FORWARD -o %i -d {vpn_network} -j ACCEPT
PostUp = ip6tables -t nat -A POSTROUTING -o {network_interface} -j MASQUERADE 2>/dev/null || true"""
        
        post_down = f"""# Cleanup NAT rules
PostDown = iptables -t nat -D POSTROUTING -s {vpn_network} -o {network_interface} -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -s {vpn_network} -j ACCEPT
PostDown = iptables -D FORWARD -o %i -d {vpn_network} -j ACCEPT
PostDown = ip6tables -t nat -D POSTROUTING -o {network_interface} -j MASQUERADE 2>/dev/null || true
PostDown = sysctl -w net.ipv4.ip_forward=0 || true"""
    
    config = f"""[Interface]
# Sulfur Bot WireGuard Server
# Full Tunnel Mode - All client traffic routed through VPN
PrivateKey = {server_private_key}
Address = {server_address}
ListenPort = {listen_port}

{post_up}

{post_down}
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


def _detect_default_interface() -> str:
    """
    Detect the default network interface for routing.
    
    Returns:
        Interface name (e.g., 'eth0', 'wlan0', 'enp0s3')
    """
    plat = _get_platform()
    
    if plat == 'windows':
        return 'Ethernet'  # Windows uses different naming
    
    try:
        # Try to get the default route interface
        result = subprocess.run(
            ['ip', 'route', 'show', 'default'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 and result.stdout:
            # Parse: "default via X.X.X.X dev eth0 ..."
            parts = result.stdout.split()
            if 'dev' in parts:
                dev_index = parts.index('dev')
                if dev_index + 1 < len(parts):
                    return parts[dev_index + 1]
    except Exception:
        pass
    
    # Fallback to common interface names
    common_interfaces = ['eth0', 'wlan0', 'enp0s3', 'ens3', 'eno1']
    for iface in common_interfaces:
        if os.path.exists(f'/sys/class/net/{iface}'):
            return iface
    
    # Last resort
    return 'eth0'


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


# ==============================================================================
# Non-Rooted Termux/Android Support
# ==============================================================================

def is_termux_non_rooted() -> bool:
    """
    Check if running on Termux without root access.
    
    Returns:
        True if on non-rooted Termux
    """
    if _get_platform() != 'termux':
        return False
    
    # Check if we have root access
    try:
        result = subprocess.run(['su', '-c', 'id'], capture_output=True, timeout=5)
        return result.returncode != 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return True


def ensure_export_dir() -> str:
    """
    Ensure the export directory exists for Android-accessible configs.
    Creates both the local export dir and the shared storage directory.
    
    Returns:
        Path to the export directory
    """
    os.makedirs(WG_EXPORT_DIR, exist_ok=True)
    
    # On Termux, also create the shared storage directory
    if _get_platform() == 'termux':
        try:
            os.makedirs(TERMUX_SHARED_DIR, exist_ok=True)
        except (PermissionError, OSError) as e:
            logger.warning(f"Could not create shared directory: {e}")
            logger.info("Run 'termux-setup-storage' to enable storage access")
    
    return WG_EXPORT_DIR


def export_config_for_android(config_content: str, client_name: str) -> Dict:
    """
    Export a WireGuard configuration file to a location accessible by the
    WireGuard Android app. Also generates a QR code if possible.
    
    Args:
        config_content: The WireGuard configuration content
        client_name: The client name for the file
        
    Returns:
        Dictionary with export paths and QR code data
    """
    result = {
        'success': False,
        'config_path': None,
        'shared_path': None,
        'qr_code': None,
        'instructions': []
    }
    
    ensure_export_dir()
    
    safe_name = "".join(c for c in client_name if c.isalnum() or c in '-_').lower()
    filename = f"sulfur_vpn_{safe_name}.conf"
    
    # Save to export directory
    export_path = os.path.join(WG_EXPORT_DIR, filename)
    try:
        with open(export_path, 'w') as f:
            f.write(config_content)
        os.chmod(export_path, 0o600)
        result['config_path'] = export_path
        result['success'] = True
    except Exception as e:
        logger.error(f"Failed to save export config: {e}")
        result['error'] = str(e)
        return result
    
    # On Termux, also save to shared storage for easy import
    if _get_platform() == 'termux':
        try:
            shared_path = os.path.join(TERMUX_SHARED_DIR, filename)
            os.makedirs(TERMUX_SHARED_DIR, exist_ok=True)
            with open(shared_path, 'w') as f:
                f.write(config_content)
            result['shared_path'] = shared_path
            result['instructions'].append(
                f"📁 Config exported to Downloads/SulfurVPN/{filename}"
            )
            result['instructions'].append(
                "📱 Open WireGuard app → + button → Import from file or archive"
            )
            result['instructions'].append(
                "📂 Navigate to Download/SulfurVPN and select the config file"
            )
        except (PermissionError, OSError) as e:
            logger.warning(f"Could not save to shared storage: {e}")
            result['instructions'].append(
                "⚠️ Run 'termux-setup-storage' to enable file sharing"
            )
    
    # Try to generate QR code
    qr_code = generate_config_qr_code(config_content)
    if qr_code:
        result['qr_code'] = qr_code
        result['instructions'].append(
            "📱 Or scan QR code with WireGuard app → + → Create from QR code"
        )
    
    return result


def generate_config_qr_code(config_content: str) -> Optional[str]:
    """
    Generate a QR code from WireGuard configuration for easy mobile import.
    
    Args:
        config_content: The WireGuard configuration content
        
    Returns:
        Base64-encoded PNG image data, or None if qrcode module not available
    """
    try:
        import qrcode
        from io import BytesIO
        
        # Create QR code
        qr = qrcode.QRCode(
            version=None,  # Auto-size
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4
        )
        qr.add_data(config_content)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return img_data
        
    except ImportError:
        logger.debug("qrcode module not installed, skipping QR generation")
        return None
    except Exception as e:
        logger.error(f"Error generating QR code: {e}")
        return None


def save_qr_code_to_file(qr_data: str, filename: str) -> Optional[str]:
    """
    Save a base64-encoded QR code image to a file.
    
    Args:
        qr_data: Base64-encoded PNG image data
        filename: Output filename
        
    Returns:
        Path to the saved file, or None on failure
    """
    if not qr_data:
        return None
    
    ensure_export_dir()
    
    output_path = os.path.join(WG_EXPORT_DIR, filename)
    
    try:
        img_data = base64.b64decode(qr_data)
        with open(output_path, 'wb') as f:
            f.write(img_data)
        
        # Also save to shared storage on Termux
        if _get_platform() == 'termux':
            try:
                shared_path = os.path.join(TERMUX_SHARED_DIR, filename)
                with open(shared_path, 'wb') as f:
                    f.write(img_data)
                return shared_path
            except (PermissionError, OSError):
                pass
        
        return output_path
        
    except Exception as e:
        logger.error(f"Failed to save QR code: {e}")
        return None


async def add_device_easy(
    device_name: str,
    server_config_path: str = None
) -> Dict:
    """
    Easy device addition workflow for beginners.
    Automatically generates keys, assigns IP, creates config, and exports for import.
    
    Args:
        device_name: Friendly name for the device (e.g., "my_phone")
        server_config_path: Path to existing server config (optional)
        
    Returns:
        Dictionary with all necessary information to set up the device
    """
    result = {
        'success': False,
        'device_name': device_name,
        'steps': []
    }
    
    # Load or create VPN configuration
    vpn_config_path = os.path.join(WG_CONFIG_DIR, 'vpn_config.json')
    vpn_config = {}
    
    if os.path.exists(vpn_config_path):
        try:
            with open(vpn_config_path, 'r') as f:
                vpn_config = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    
    if vpn_config.get('role') != 'server':
        result['error'] = 'VPN server not configured. Run setup first.'
        result['steps'].append("❌ No server configuration found")
        result['steps'].append("📋 Run 'python master_setup.py --vpn' to set up the server")
        return result
    
    # Get server details
    server_endpoint = vpn_config.get('endpoint', 'your-server:51820')
    server_port = vpn_config.get('port', WG_PORT)
    server_address_network = vpn_config.get('address', '10.0.0.1/24')
    
    # Load server public key
    server_public_key = vpn_config.get('public_key')
    if not server_public_key:
        result['error'] = 'Server public key not found'
        return result
    
    # Calculate next available client IP
    peers = vpn_config.get('peers', [])
    base_ip = server_address_network.split('/')[0]  # e.g., "10.0.0.1"
    ip_parts = base_ip.split('.')
    next_ip_num = 2 + len(peers)  # Start from .2, increment for each peer
    client_ip = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.{next_ip_num}/32"
    
    result['steps'].append(f"🔢 Assigned IP address: {client_ip}")
    
    # Generate client keys
    if not is_wireguard_installed():
        result['error'] = 'WireGuard tools not installed'
        result['steps'].append("❌ WireGuard not installed")
        result['steps'].append(get_installation_instructions())
        return result
    
    try:
        private_key, public_key = generate_keypair()
        result['steps'].append("🔑 Generated encryption keys")
    except Exception as e:
        result['error'] = f'Failed to generate keys: {e}'
        return result
    
    # Create client configuration
    config = generate_client_config(
        client_private_key=private_key,
        client_address=client_ip,
        server_public_key=server_public_key,
        server_endpoint=f"{server_endpoint}"
    )
    
    result['steps'].append("📝 Created VPN configuration")
    
    # Save config
    safe_name = "".join(c for c in device_name if c.isalnum() or c in '-_').lower()
    config_path = save_config(config, f"client_{safe_name}.conf")
    result['config_path'] = config_path
    
    # Export for Android/mobile
    export_result = export_config_for_android(config, device_name)
    result['export'] = export_result
    result['steps'].extend(export_result.get('instructions', []))
    
    if export_result.get('qr_code'):
        qr_filename = f"vpn_qr_{safe_name}.png"
        qr_path = save_qr_code_to_file(export_result['qr_code'], qr_filename)
        if qr_path:
            result['qr_code_path'] = qr_path
            result['steps'].append(f"📷 QR code saved to {qr_path}")
    
    # Add peer to server config
    new_peer = {
        'name': device_name,
        'public_key': public_key,
        'allowed_ips': client_ip
    }
    peers.append(new_peer)
    vpn_config['peers'] = peers
    
    try:
        with open(vpn_config_path, 'w') as f:
            json.dump(vpn_config, f, indent=2)
        result['steps'].append("✅ Device added to VPN configuration")
    except Exception as e:
        logger.error(f"Failed to update VPN config: {e}")
    
    # Update server config file
    await update_server_config_with_peer(new_peer)
    
    result['success'] = True
    result['client_ip'] = client_ip
    result['public_key'] = public_key
    result['config_content'] = config
    
    # Add final instructions
    result['steps'].append("")
    result['steps'].append("📱 **To connect your device:**")
    result['steps'].append("1. Install WireGuard app from your app store")
    result['steps'].append("2. Import the configuration file or scan the QR code")
    result['steps'].append("3. Toggle the VPN connection on")
    
    return result


async def update_server_config_with_peer(peer: Dict) -> bool:
    """
    Update the server's WireGuard configuration file to include a new peer.
    
    Args:
        peer: Dictionary with peer info (name, public_key, allowed_ips)
        
    Returns:
        True if successful
    """
    server_config_path = os.path.join(WG_CONFIG_DIR, f"{WG_INTERFACE}.conf")
    
    if not os.path.exists(server_config_path):
        logger.warning("Server config not found, cannot add peer")
        return False
    
    try:
        with open(server_config_path, 'r') as f:
            config_content = f.read()
        
        # Append new peer section
        peer_section = f"""
[Peer]
# {peer.get('name', 'Unknown Peer')}
PublicKey = {peer['public_key']}
AllowedIPs = {peer.get('allowed_ips', '10.0.0.2/32')}
"""
        
        config_content += peer_section
        
        with open(server_config_path, 'w') as f:
            f.write(config_content)
        
        logger.info(f"Added peer {peer.get('name')} to server config")
        
        # If server is running, reload the config
        if is_wireguard_installed():
            plat = _get_platform()
            if plat not in ['termux', 'windows']:
                # Try to reload without restart
                try:
                    proc = await asyncio.create_subprocess_exec(
                        'wg', 'syncconf', WG_INTERFACE, server_config_path,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    await proc.communicate()
                    logger.info("Reloaded WireGuard configuration")
                except Exception as e:
                    logger.debug(f"Could not hot-reload config: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to update server config: {e}")
        return False


def list_configured_devices() -> List[Dict]:
    """
    List all configured VPN devices/peers.
    
    Returns:
        List of device dictionaries
    """
    vpn_config_path = os.path.join(WG_CONFIG_DIR, 'vpn_config.json')
    
    if not os.path.exists(vpn_config_path):
        return []
    
    try:
        with open(vpn_config_path, 'r') as f:
            vpn_config = json.load(f)
        return vpn_config.get('peers', [])
    except (json.JSONDecodeError, IOError):
        return []


def get_termux_wireguard_instructions() -> str:
    """
    Get detailed instructions for setting up WireGuard on non-rooted Termux.
    
    Returns:
        Formatted instruction string
    """
    return """
## 📱 WireGuard VPN on Non-Rooted Android (Termux)

Since full WireGuard kernel integration requires root access, we use the official 
WireGuard Android app to handle VPN connections.

### Step 1: Install the WireGuard Android App
Download from:
- [Google Play Store](https://play.google.com/store/apps/details?id=com.wireguard.android)
- [F-Droid](https://f-droid.org/packages/com.wireguard.android/)

### Step 2: Generate Your VPN Configuration
In Sulfur Bot, run:
```
/vpn add_device device_name:my_phone
```

This will:
1. Generate encryption keys for your device
2. Create a configuration file
3. Export it to your Downloads folder
4. Generate a QR code for easy import

### Step 3: Import Configuration

**Option A: File Import**
1. Open WireGuard app
2. Tap the + button
3. Select "Import from file or archive"
4. Navigate to Download/SulfurVPN/
5. Select your configuration file

**Option B: QR Code (Easiest)**
1. Open WireGuard app
2. Tap the + button
3. Select "Create from QR code"
4. Scan the QR code displayed by the bot

### Step 4: Connect
1. Toggle the switch next to your VPN profile
2. Accept the VPN permission request
3. You're connected! 🎉

### Troubleshooting

**Can't find the config file?**
Run in Termux: `termux-setup-storage`
Grant storage permission when prompted.

**Connection times out?**
- Check if the server is running and port 51820 is forwarded
- Verify your internet connection
- Make sure the server's public IP hasn't changed

**No internet when connected?**
This is normal if your VPN is configured for split tunneling.
To route all traffic through VPN, ensure AllowedIPs = 0.0.0.0/0
"""


def get_quick_setup_guide() -> str:
    """
    Get a quick setup guide for VPN configuration.
    
    Returns:
        Markdown-formatted quick setup guide
    """
    return """
## 🚀 Quick VPN Setup Guide

### For the Server (where Sulfur Bot runs):
1. Run the setup wizard: `python master_setup.py --vpn`
2. Choose "Server" when prompted
3. Enter your public IP or domain name
4. Port forward UDP 51820 on your router

### For Client Devices:
1. Use the `/vpn add_device` command in Discord
2. Follow the instructions to import the config
3. Connect and enjoy secure access!

### Adding a New Device (Easy Way):
```
/vpn add_device device_name:my_laptop
```

This automatically:
✅ Generates unique encryption keys
✅ Assigns an IP address  
✅ Creates the configuration file
✅ Exports for easy import
✅ Generates a QR code (for mobile)
"""
