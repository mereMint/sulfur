#!/usr/bin/env python3
"""
Sulfur Bot - Master Setup Wizard

Comprehensive installation wizard for:
- Bot dependencies and configuration
- WireGuard VPN setup
- Minecraft server download and configuration

Supports: Termux/Android, Linux, Windows, Raspberry Pi
"""

import os
import sys
import platform
import subprocess
import json
import shutil
import time
import urllib.request
from typing import Optional, Tuple, List
from getpass import getpass

# ==============================================================================
# Colors and Formatting (cross-platform)
# ==============================================================================

# Database startup timing constants (in seconds)
DB_STARTUP_WAIT = 3          # Wait time after starting database server
DB_CONNECTION_TIMEOUT = 2    # Timeout for connection attempts

class Colors:
    """ANSI color codes for terminal output."""
    
    # Check if colors are supported
    _supports_color = (
        hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
        and os.environ.get('TERM', '') != 'dumb'
        and platform.system() != 'Windows'  # Windows needs special handling
    )
    
    # Enable colors on Windows 10+
    if platform.system() == 'Windows':
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            _supports_color = True
        except Exception:
            _supports_color = False
    
    if _supports_color:
        RESET = '\033[0m'
        BOLD = '\033[1m'
        RED = '\033[91m'
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        BLUE = '\033[94m'
        CYAN = '\033[96m'
        MAGENTA = '\033[95m'
    else:
        RESET = BOLD = RED = GREEN = YELLOW = BLUE = CYAN = MAGENTA = ''


def print_header(text: str):
    """Print a header with decorative borders."""
    width = 70
    print()
    print(f"{Colors.CYAN}{'═' * width}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(width)}{Colors.RESET}")
    print(f"{Colors.CYAN}{'═' * width}{Colors.RESET}")
    print()


def print_section(text: str):
    """Print a section header."""
    print(f"\n{Colors.BLUE}{'─' * 60}{Colors.RESET}")
    print(f"  {Colors.BOLD}{text}{Colors.RESET}")
    print(f"{Colors.BLUE}{'─' * 60}{Colors.RESET}")


def print_success(text: str):
    """Print a success message."""
    print(f"  {Colors.GREEN}✅ {text}{Colors.RESET}")


def print_error(text: str):
    """Print an error message."""
    print(f"  {Colors.RED}❌ {text}{Colors.RESET}")


def print_warning(text: str):
    """Print a warning message."""
    print(f"  {Colors.YELLOW}⚠️  {text}{Colors.RESET}")


def print_info(text: str):
    """Print an info message."""
    print(f"  {Colors.CYAN}ℹ️  {text}{Colors.RESET}")


def print_step(text: str):
    """Print a step indicator."""
    print(f"  {Colors.MAGENTA}→{Colors.RESET} {text}")


def ask_yes_no(prompt: str, default: bool = True) -> bool:
    """Ask a yes/no question."""
    suffix = " [Y/n]: " if default else " [y/N]: "
    response = input(f"{prompt}{suffix}").strip().lower()
    
    if not response:
        return default
    
    return response in ('y', 'yes', 'ja', 'j')


def ask_choice(prompt: str, options: List[str], default: int = 0) -> int:
    """Ask the user to choose from a list of options."""
    print(f"\n{prompt}")
    for i, option in enumerate(options):
        marker = f"{Colors.GREEN}→{Colors.RESET}" if i == default else " "
        print(f"  {marker} [{i + 1}] {option}")
    
    while True:
        try:
            response = input(f"\nEnter choice [1-{len(options)}] (default: {default + 1}): ").strip()
            if not response:
                return default
            choice = int(response) - 1
            if 0 <= choice < len(options):
                return choice
            print_error(f"Please enter a number between 1 and {len(options)}")
        except ValueError:
            print_error("Please enter a valid number")


# ==============================================================================
# Platform Detection
# ==============================================================================

def detect_platform() -> str:
    """Detect the current platform."""
    system = platform.system().lower()
    
    # Check for Termux (Android)
    if os.path.exists('/data/data/com.termux'):
        return 'termux'
    
    # Check for WSL
    if system == 'linux' and 'microsoft' in platform.uname().release.lower():
        return 'wsl'
    
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
    
    if system == 'darwin':
        return 'macos'
    
    return system


def get_platform_name(plat: str) -> str:
    """Get a human-readable platform name."""
    names = {
        'termux': 'Termux (Android)',
        'linux': 'Linux',
        'windows': 'Windows',
        'raspberrypi': 'Raspberry Pi',
        'wsl': 'Windows Subsystem for Linux',
        'macos': 'macOS'
    }
    return names.get(plat, plat.title())


def run_command(cmd: List[str], capture: bool = False, shell: bool = False, quiet: bool = False) -> Tuple[int, str, str]:
    """
    Run a command and return the result.
    
    Args:
        cmd: Command and arguments as a list
        capture: Legacy parameter (now always captures unless quiet=True)
        shell: If True, run command through shell
        quiet: If True, suppress all output (no stdout/stderr capture)
    
    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    try:
        if shell and isinstance(cmd, list):
            cmd = ' '.join(cmd)
        
        stdout = subprocess.DEVNULL if quiet else subprocess.PIPE
        stderr = subprocess.DEVNULL if quiet else subprocess.PIPE
        
        result = subprocess.run(
            cmd,
            stdout=stdout,
            stderr=stderr,
            text=True,
            shell=shell
        )
        return result.returncode, result.stdout if not quiet else '', result.stderr if not quiet else ''
    except FileNotFoundError:
        return 1, '', '' if quiet else f'Command not found: {cmd[0] if isinstance(cmd, list) else cmd}'
    except Exception as e:
        return 1, '', '' if quiet else str(e)


# ==============================================================================
# Dependency Checks
# ==============================================================================

def check_python_version() -> Tuple[bool, str]:
    """Check if Python version meets requirements."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        return False, f"Python {version.major}.{version.minor} found. Python 3.8+ required."
    return True, f"Python {version.major}.{version.minor}.{version.micro}"


def check_pip() -> Tuple[bool, str]:
    """Check if pip is installed."""
    code, out, _ = run_command([sys.executable, '-m', 'pip', '--version'])
    if code == 0:
        return True, out.strip()
    return False, "pip not found"


def check_git() -> Tuple[bool, str]:
    """Check if git is installed."""
    code, out, _ = run_command(['git', '--version'])
    if code == 0:
        return True, out.strip()
    return False, "git not found"


def check_mysql() -> Tuple[bool, str]:
    """Check if MySQL/MariaDB is installed."""
    # Try mysql command
    code, out, _ = run_command(['mysql', '--version'])
    if code == 0:
        return True, out.strip()
    
    # Try mariadb command
    code, out, _ = run_command(['mariadb', '--version'])
    if code == 0:
        return True, out.strip()
    
    return False, "MySQL/MariaDB not found"


def check_java() -> Tuple[bool, str]:
    """Check if Java is installed."""
    code, out, err = run_command(['java', '-version'])
    # Java outputs version to stderr
    version_text = err if err else out
    
    if code == 0:
        import re
        match = re.search(r'version "([^"]+)"', version_text)
        if match:
            return True, f"Java {match.group(1)}"
        match = re.search(r'openjdk (\d+)', version_text, re.IGNORECASE)
        if match:
            return True, f"Java {match.group(1)}"
        return True, "Java installed"
    
    return False, "Java not found"


def check_wireguard() -> Tuple[bool, str]:
    """Check if WireGuard is installed."""
    wg_path = shutil.which('wg')
    if wg_path:
        code, out, _ = run_command(['wg', '--version'])
        return True, out.strip() if code == 0 else "WireGuard installed"
    return False, "WireGuard not found"


# ==============================================================================
# Installation Functions
# ==============================================================================

def install_all_system_dependencies(plat: str) -> bool:
    """
    Install ALL system dependencies for the current platform.
    
    This function ensures a complete, automatic installation of all required
    system packages so users don't have to troubleshoot or manually install anything.
    
    Args:
        plat: The detected platform (termux, linux, raspberrypi, windows, macos, wsl)
        
    Returns:
        True if all dependencies were installed successfully
    """
    print_section("Installing System Dependencies")
    print_info("Installing all required system packages automatically...")
    print_info("This may take a few minutes. Please wait...")
    
    success = True
    
    if plat == 'termux':
        # Termux - comprehensive package list for all features
        print_step("Installing Termux packages...")
        packages = [
            # Build essentials
            'binutils', 'clang', 'make', 'cmake', 'pkg-config', 
            # Python and development
            'python', 'python-pip', 'rust',  # Rust for some Python packages
            # Crypto and networking
            'libffi', 'openssl', 'libsodium',  # For PyNaCl
            # Database
            'mariadb',
            # VPN
            'wireguard-tools',
            # Java for Minecraft
            'openjdk-17',
            # Utilities
            'git', 'curl', 'wget', 'unzip', 'tar',
            # Networking tools
            'net-tools', 'iproute2',
        ]
        
        # Update package list first
        print_info("Updating package repository...")
        run_command(['pkg', 'update', '-y'], quiet=True)
        run_command(['pkg', 'upgrade', '-y'], quiet=True)
        
        for package in packages:
            print_info(f"  Installing {package}...")
            code, out, err = run_command(['pkg', 'install', '-y', package], quiet=True)
            if code != 0:
                print_warning(f"  Could not install {package} (may not be needed)")
        
        print_success("Termux system packages installed")
        
    elif plat in ['linux', 'raspberrypi', 'wsl']:
        # Debian/Ubuntu-based systems
        print_step("Installing Linux packages via apt...")
        
        packages = [
            # Build essentials
            'build-essential', 'python3-dev', 'libffi-dev',
            # Crypto
            'libsodium-dev', 'libssl-dev',
            # Database
            'mariadb-server', 'mariadb-client', 'libmariadb-dev',
            # VPN
            'wireguard', 'wireguard-tools',
            # Java for Minecraft
            'openjdk-21-jre-headless',
            # Utilities
            'git', 'curl', 'wget', 'unzip',
            # Networking
            'net-tools', 'iptables',
        ]
        
        # Update package list
        print_info("Updating package repository...")
        run_command(['sudo', 'apt', 'update'], quiet=True)
        
        # Install packages in one command for efficiency
        print_info("Installing packages (this may take a while)...")
        code, out, err = run_command(
            ['sudo', 'apt', 'install', '-y'] + packages,
            quiet=True
        )
        
        if code != 0:
            # Try installing packages one by one as fallback
            print_warning("Bulk install failed, trying individual packages...")
            for package in packages:
                print_info(f"  Installing {package}...")
                run_command(['sudo', 'apt', 'install', '-y', package], quiet=True)
        
        print_success("Linux system packages installed")
        
    elif plat == 'macos':
        # macOS via Homebrew
        print_step("Installing macOS packages via Homebrew...")
        
        if not shutil.which('brew'):
            print_warning("Homebrew not found. Installing Homebrew first...")
            code, out, err = run_command([
                '/bin/bash', '-c', 
                '$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)'
            ])
            if code != 0:
                print_error("Failed to install Homebrew. Please install manually from https://brew.sh/")
                return False
        
        packages = [
            'python', 'libffi', 'libsodium', 'openssl',
            'mariadb', 'wireguard-tools', 'openjdk@21',
            'git', 'curl', 'wget'
        ]
        
        for package in packages:
            print_info(f"  Installing {package}...")
            run_command(['brew', 'install', package], quiet=True)
        
        print_success("macOS packages installed")
        
    elif plat == 'windows':
        # Windows - provide instructions and attempt winget
        print_step("Setting up Windows dependencies...")
        
        # Try using winget if available
        if shutil.which('winget'):
            print_info("Using Windows Package Manager (winget)...")
            
            winget_packages = [
                'Python.Python.3.12',
                'MariaDB.Server',
                'WireGuard.WireGuard',
                'EclipseAdoptium.Temurin.21.JRE',
                'Git.Git',
            ]
            
            for package in winget_packages:
                print_info(f"  Installing {package}...")
                run_command(['winget', 'install', '--accept-package-agreements', '--accept-source-agreements', '-e', '--id', package], quiet=True)
            
            print_success("Windows packages installed via winget")
        else:
            print_warning("Windows Package Manager (winget) not found")
            print_info("Please install the following manually:")
            print_info("  - Python 3.12+: https://python.org/downloads/")
            print_info("  - MariaDB: https://mariadb.org/download/")
            print_info("  - WireGuard: https://wireguard.com/install/")
            print_info("  - Java 21: https://adoptium.net/")
            success = False
    
    return success


def install_termux_build_deps() -> bool:
    """
    Install build dependencies required for compiling Python packages on Termux.
    
    This is needed for packages like PyNaCl that require native compilation.
    The main issue is that the linker (ld) is not installed by default.
    """
    print_step("Installing Termux build dependencies...")
    
    # Install build essentials including binutils (provides ld linker)
    # Also include libsodium for PyNaCl pre-built binaries
    packages = [
        'binutils', 'clang', 'make', 'cmake', 'pkg-config', 
        'libffi', 'openssl', 'libsodium', 'rust', 'python-pip'
    ]
    
    # Update package list first
    run_command(['pkg', 'update', '-y'], quiet=True)
    
    for package in packages:
        print_info(f"Installing {package}...")
        code, out, err = run_command(['pkg', 'install', '-y', package], quiet=True)
        if code != 0:
            print_warning(f"Failed to install {package}: {err}")
    
    print_success("Build dependencies installed")
    return True


def install_python_dependencies() -> bool:
    """Install Python dependencies from requirements.txt."""
    print_step("Installing Python dependencies...")
    
    if not os.path.exists('requirements.txt'):
        print_error("requirements.txt not found")
        return False
    
    plat = detect_platform()
    
    # Install system build dependencies first based on platform
    if plat == 'termux':
        print_info("Termux detected - installing build dependencies first...")
        install_termux_build_deps()
    elif plat in ['linux', 'raspberrypi', 'wsl']:
        # Ensure build tools are available
        print_info("Ensuring build tools are available...")
        run_command(['sudo', 'apt', 'install', '-y', 'build-essential', 'python3-dev', 'libffi-dev', 'libsodium-dev'], quiet=True)
    
    # Upgrade pip first
    print_info("Upgrading pip...")
    run_command([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'], quiet=True)
    
    # Install dependencies
    code, out, err = run_command([
        sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt', '--upgrade'
    ])
    
    if code == 0:
        print_success("Python dependencies installed")
        return True
    else:
        print_error(f"Failed to install dependencies: {err}")
        
        # Automatic retry with additional packages
        print_info("Attempting automatic fix...")
        
        if plat == 'termux':
            # Install libsodium and retry
            run_command(['pkg', 'install', '-y', 'libsodium'], quiet=True)
        elif plat in ['linux', 'raspberrypi', 'wsl']:
            run_command(['sudo', 'apt', 'install', '-y', 'libsodium-dev', 'libssl-dev'], quiet=True)
        elif plat == 'macos':
            run_command(['brew', 'install', 'libsodium'], quiet=True)
        
        # Retry installation
        print_info("Retrying dependency installation...")
        code, out, err = run_command([
            sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt', '--upgrade'
        ])
        
        if code == 0:
            print_success("Python dependencies installed after automatic fix")
            return True
        
        print_error("Installation still failed after automatic fix")
        return False


def get_mysql_install_command(plat: str) -> str:
    """Get the MySQL installation command for the platform."""
    commands = {
        'termux': 'pkg install mariadb',
        'linux': 'sudo apt install mariadb-server mariadb-client',
        'raspberrypi': 'sudo apt install mariadb-server mariadb-client',
        'windows': 'Download from https://dev.mysql.com/downloads/installer/',
        'wsl': 'sudo apt install mariadb-server mariadb-client',
        'macos': 'brew install mariadb'
    }
    return commands.get(plat, 'Install MySQL or MariaDB manually')


def install_mysql_mariadb(plat: str) -> bool:
    """Install MySQL/MariaDB on the current platform."""
    print_step("Installing MySQL/MariaDB...")
    
    if plat == 'termux':
        # Termux installation
        print_info("Installing MariaDB via pkg...")
        code, out, err = run_command(['pkg', 'install', '-y', 'mariadb'])
        
        if code == 0:
            print_success("MariaDB installed successfully")
            
            # Initialize database if needed
            datadir = os.path.expandvars('$PREFIX/var/lib/mysql')
            if not os.path.exists(datadir) or not os.listdir(datadir):
                print_step("Initializing MariaDB database...")
                code, out, err = run_command(['mysql_install_db'])
                if code == 0:
                    print_success("MariaDB initialized")
                else:
                    print_warning(f"Database initialization may have issues: {err}")
            
            return True
        else:
            print_error(f"Installation failed: {err}")
            return False
    
    elif plat in ['linux', 'raspberrypi', 'wsl']:
        # Debian/Ubuntu-based installation
        print_info("Installing MariaDB via apt...")
        
        # Check if we have sudo
        if os.getuid() != 0:
            print_info("This requires sudo privileges...")
        
        # Update package list
        print_step("Updating package list...")
        code, out, err = run_command(['sudo', 'apt', 'update'])
        if code != 0:
            print_warning("Failed to update package list")
        
        # Install MariaDB
        code, out, err = run_command([
            'sudo', 'apt', 'install', '-y', 
            'mariadb-server', 'mariadb-client'
        ])
        
        if code == 0:
            print_success("MariaDB installed successfully")
            return True
        else:
            print_error(f"Installation failed: {err}")
            print_info("You may need to install manually with: sudo apt install mariadb-server")
            return False
    
    elif plat == 'macos':
        # macOS installation via Homebrew
        print_info("Installing MariaDB via Homebrew...")
        
        # Check if brew is installed
        if not shutil.which('brew'):
            print_error("Homebrew not found. Please install from https://brew.sh/")
            return False
        
        code, out, err = run_command(['brew', 'install', 'mariadb'])
        
        if code == 0:
            print_success("MariaDB installed successfully")
            return True
        else:
            print_error(f"Installation failed: {err}")
            return False
    
    elif plat == 'windows':
        # Windows - provide instructions
        print_warning("Automatic installation not supported on Windows")
        print_info("Please install MariaDB or MySQL manually:")
        print_info("  Option 1: Download MariaDB from https://mariadb.org/download/")
        print_info("  Option 2: Download MySQL from https://dev.mysql.com/downloads/installer/")
        print_info("  Option 3: Install XAMPP which includes MariaDB")
        print_info("")
        print_info("After installation, re-run this setup script.")
        return False
    
    else:
        print_warning(f"Automatic installation not supported for platform: {plat}")
        print_info(f"Please install manually: {get_mysql_install_command(plat)}")
        return False


def ensure_mysql_running(plat: str) -> bool:
    """Ensure MySQL/MariaDB server is running."""
    print_step("Checking if MySQL/MariaDB server is running...")
    
    # Check if server is running by trying to connect
    def is_server_running():
        # Try connecting with mysql command
        code, _, _ = run_command(['mysql', '-u', 'root', '-e', 'SELECT 1'], quiet=True)
        if code == 0:
            return True
        
        # Try with mariadb command
        code, _, _ = run_command(['mariadb', '-u', 'root', '-e', 'SELECT 1'], quiet=True)
        if code == 0:
            return True
        
        # Try connecting to port 3306
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('localhost', 3306))
            sock.close()
            return result == 0
        except:
            return False
    
    if is_server_running():
        print_success("MySQL/MariaDB server is running")
        return True
    
    print_warning("MySQL/MariaDB server is not running")
    print_step("Attempting to start server...")
    
    if plat == 'termux':
        # Termux - use mysqld_safe
        print_info("Starting MariaDB with mysqld_safe...")
        
        # Check if already running
        code, out, _ = run_command(['pgrep', 'mysqld'], quiet=True)
        if code == 0:
            print_success("MariaDB is already running")
            return True
        
        # Start in background
        datadir = os.path.expandvars('$PREFIX/var/lib/mysql')
        code, out, err = run_command([
            'mysqld_safe', 
            f'--datadir={datadir}',
            '&'
        ], quiet=True)
        
        # Wait a moment for server to start
        print_info("Waiting for server to start...")
        time.sleep(DB_STARTUP_WAIT)
        
        if is_server_running():
            print_success("MariaDB started successfully")
            print_info("To start on boot: Add 'mysqld_safe &' to your startup script")
            return True
        else:
            print_error("Failed to start MariaDB")
            print_info("Try manually: mysqld_safe --datadir=$PREFIX/var/lib/mysql &")
            return False
    
    elif plat in ['linux', 'raspberrypi', 'wsl']:
        # Linux - use systemctl or service
        
        # Try systemctl (systemd)
        if shutil.which('systemctl'):
            print_info("Starting MariaDB via systemctl...")
            
            # Try mariadb.service first
            code, _, _ = run_command(['sudo', 'systemctl', 'start', 'mariadb'], quiet=True)
            if code == 0:
                time.sleep(DB_CONNECTION_TIMEOUT)
                if is_server_running():
                    print_success("MariaDB started successfully")
                    
                    # Enable on boot
                    run_command(['sudo', 'systemctl', 'enable', 'mariadb'], quiet=True)
                    print_info("MariaDB enabled to start on boot")
                    return True
            
            # Try mysql.service
            code, _, _ = run_command(['sudo', 'systemctl', 'start', 'mysql'], quiet=True)
            if code == 0:
                time.sleep(DB_CONNECTION_TIMEOUT)
                if is_server_running():
                    print_success("MySQL started successfully")
                    
                    # Enable on boot
                    run_command(['sudo', 'systemctl', 'enable', 'mysql'], quiet=True)
                    print_info("MySQL enabled to start on boot")
                    return True
        
        # Try service command (SysV init)
        elif shutil.which('service'):
            print_info("Starting MySQL via service...")
            code, _, _ = run_command(['sudo', 'service', 'mysql', 'start'], quiet=True)
            if code == 0:
                time.sleep(DB_CONNECTION_TIMEOUT)
                if is_server_running():
                    print_success("MySQL started successfully")
                    return True
            
            code, _, _ = run_command(['sudo', 'service', 'mariadb', 'start'], quiet=True)
            if code == 0:
                time.sleep(DB_CONNECTION_TIMEOUT)
                if is_server_running():
                    print_success("MariaDB started successfully")
                    return True
        
        print_error("Failed to start database server")
        print_info("Try manually: sudo systemctl start mariadb")
        return False
    
    elif plat == 'macos':
        # macOS - use brew services
        print_info("Starting MariaDB via Homebrew services...")
        
        code, _, _ = run_command(['brew', 'services', 'start', 'mariadb'])
        if code == 0:
            time.sleep(DB_CONNECTION_TIMEOUT)
            if is_server_running():
                print_success("MariaDB started successfully")
                print_info("MariaDB will start automatically on boot")
                return True
        
        print_error("Failed to start MariaDB")
        print_info("Try manually: brew services start mariadb")
        return False
    
    elif plat == 'windows':
        # Windows - use net start or services
        print_info("Starting MySQL/MariaDB service...")
        
        # Try MariaDB service
        code, _, _ = run_command(['net', 'start', 'MariaDB'], quiet=True)
        if code == 0:
            time.sleep(DB_CONNECTION_TIMEOUT)
            if is_server_running():
                print_success("MariaDB started successfully")
                return True
        
        # Try MySQL service
        code, _, _ = run_command(['net', 'start', 'MySQL'], quiet=True)
        if code == 0:
            time.sleep(DB_CONNECTION_TIMEOUT)
            if is_server_running():
                print_success("MySQL started successfully")
                return True
        
        print_error("Failed to start database service")
        print_info("Please start MySQL/MariaDB manually:")
        print_info("  - Open Services (services.msc)")
        print_info("  - Find MySQL or MariaDB service")
        print_info("  - Right-click and select Start")
        print_info("  - Set to Automatic startup")
        return False
    
    else:
        print_warning(f"Automatic startup not supported for platform: {plat}")
        return False


def get_java_install_command(plat: str) -> str:
    """Get the Java installation command for the platform."""
    commands = {
        'termux': 'pkg install openjdk-21',
        'linux': 'sudo apt install openjdk-21-jdk',
        'raspberrypi': 'sudo apt install openjdk-21-jdk',
        'windows': 'Download from https://adoptium.net/',
        'wsl': 'sudo apt install openjdk-21-jdk',
        'macos': 'brew install openjdk@21'
    }
    return commands.get(plat, 'Install Java 21 manually')


def get_wireguard_install_command(plat: str) -> str:
    """Get the WireGuard installation command for the platform."""
    commands = {
        'termux': 'pkg install wireguard-tools',
        'linux': 'sudo apt install wireguard',
        'raspberrypi': 'sudo apt install wireguard',
        'windows': 'Download from https://www.wireguard.com/install/',
        'wsl': 'sudo apt install wireguard-tools',
        'macos': 'brew install wireguard-tools'
    }
    return commands.get(plat, 'Install WireGuard manually')


# ==============================================================================
# Configuration Setup
# ==============================================================================

def setup_env_file() -> bool:
    """Create or update the .env file."""
    print_section("Environment Configuration")
    
    env_path = '.env'
    env_example = '.env.example'
    
    # Load existing values if .env exists
    existing = {}
    if os.path.exists(env_path):
        print_info("Existing .env file found")
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    existing[key.strip()] = value.strip().strip('"').strip("'")
        
        if not ask_yes_no("Do you want to reconfigure?", default=False):
            print_info("Keeping existing configuration")
            return True
    
    # Copy from example if it exists and no .env
    elif os.path.exists(env_example):
        shutil.copy(env_example, env_path)
        print_info("Created .env from .env.example")
    
    print("\nPlease provide the following configuration values:")
    print("(Press Enter to keep existing value or use default)\n")
    
    config = {}
    
    # Discord Bot Token - REQUIRED
    config['DISCORD_BOT_TOKEN'] = ''
    current = existing.get('DISCORD_BOT_TOKEN', '')
    masked = f"{current[:10]}..." if len(current) > 10 else "(not set)"
    
    while not config['DISCORD_BOT_TOKEN']:
        token = input(f"Discord Bot Token [{masked}]: ").strip()
        if token:
            config['DISCORD_BOT_TOKEN'] = token
        elif current:
            config['DISCORD_BOT_TOKEN'] = current
        else:
            print_warning("Discord Bot Token is required! (Press Ctrl+C to cancel)")
    config['DB_NAME'] = input(f"Database Name [{existing.get('DB_NAME', 'sulfur_bot')}]: ").strip() or existing.get('DB_NAME', 'sulfur_bot')
    
    # AI API Keys
    print("\n--- AI API Keys (at least one required) ---")
    
    current = existing.get('GEMINI_API_KEY', '')
    masked = f"{current[:10]}..." if len(current) > 10 else "(not set)"
    gemini_key = input(f"Gemini API Key [{masked}]: ").strip()
    config['GEMINI_API_KEY'] = gemini_key if gemini_key else current
    
    current = existing.get('OPENAI_API_KEY', '')
    masked = f"{current[:10]}..." if len(current) > 10 else "(not set)"
    openai_key = input(f"OpenAI API Key [{masked}]: ").strip()
    config['OPENAI_API_KEY'] = openai_key if openai_key else current
    
    # Optional keys
    print("\n--- Optional API Keys ---")
    
    current = existing.get('LASTFM_API_KEY', '')
    masked = f"{current[:10]}..." if len(current) > 10 else "(not set)"
    lastfm_key = input(f"Last.fm API Key [{masked}]: ").strip()
    config['LASTFM_API_KEY'] = lastfm_key if lastfm_key else current
    
    current = existing.get('FOOTBALL_DATA_API_KEY', '')
    masked = f"{current[:10]}..." if len(current) > 10 else "(not set)"
    football_key = input(f"Football-Data.org API Key [{masked}]: ").strip()
    config['FOOTBALL_DATA_API_KEY'] = football_key if football_key else current
    
    # Write .env file
    try:
        with open(env_path, 'w') as f:
            f.write("# Sulfur Bot Configuration\n")
            f.write("# Generated by setup wizard\n\n")
            
            f.write("# Discord\n")
            f.write(f'DISCORD_BOT_TOKEN="{config.get("DISCORD_BOT_TOKEN", "")}"\n\n')
            
            f.write("# Database\n")
            f.write(f'DB_HOST={config.get("DB_HOST", "localhost")}\n')
            f.write(f'DB_USER={config.get("DB_USER", "sulfur_bot_user")}\n')
            f.write(f'DB_PASS={config.get("DB_PASS", "")}\n')
            f.write(f'DB_NAME={config.get("DB_NAME", "sulfur_bot")}\n\n')
            
            f.write("# AI APIs\n")
            f.write(f'GEMINI_API_KEY={config.get("GEMINI_API_KEY", "")}\n')
            f.write(f'OPENAI_API_KEY={config.get("OPENAI_API_KEY", "")}\n\n')
            
            f.write("# Optional APIs\n")
            f.write(f'LASTFM_API_KEY={config.get("LASTFM_API_KEY", "")}\n')
            f.write(f'FOOTBALL_DATA_API_KEY={config.get("FOOTBALL_DATA_API_KEY", "")}\n')
        
        print_success("Configuration saved to .env")
        return True
        
    except Exception as e:
        print_error(f"Failed to save configuration: {e}")
        return False


# ==============================================================================
# Minecraft Server Setup
# ==============================================================================

def setup_minecraft_server(plat: str) -> bool:
    """Set up the Minecraft server."""
    print_section("Minecraft Server Setup")
    
    # Check Java
    java_ok, java_msg = check_java()
    if not java_ok:
        print_warning(f"Java not found. Minecraft requires Java 21.")
        print_info(f"Install command: {get_java_install_command(plat)}")
        
        if not ask_yes_no("Continue anyway?", default=False):
            return False
    else:
        print_success(java_msg)
    
    # Choose server type or modpack
    print("\n--- Server Type / Modpack Selection ---")
    print("Choose between a standard server or a pre-configured modpack:")
    
    setup_options = [
        "Standard Server (Choose server type manually)",
        "🍓 Raspberry Flavoured - CurseForge (Vanilla+ with QoL)",
        "😴 Melatonin - Modrinth (Maximum performance)",
        "🏠 Homestead Cozy - CurseForge (Farms, building, decoration)"
    ]
    
    setup_choice = ask_choice("Select setup type:", setup_options, default=0)
    
    selected_modpack = None
    server_type = 'paper'
    mc_version = '1.21.4'
    
    if setup_choice == 0:
        # Standard server selection
        server_types = [
            "PaperMC (Recommended - High performance, plugin support)",
            "Purpur (Paper fork with extra features)",
            "Vanilla (Official Minecraft server)",
            "Fabric (Lightweight modding platform)"
        ]
        
        choice = ask_choice("Select server type:", server_types, default=0)
        server_type = ['paper', 'purpur', 'vanilla', 'fabric'][choice]
        
        # Choose Minecraft version
        print("\nEnter Minecraft version (e.g., 1.21.4, 1.20.4):")
        mc_version = input("Version [1.21.4]: ").strip() or "1.21.4"
    else:
        # Modpack selected
        modpack_map = {
            1: 'raspberry_flavoured',
            2: 'melatonin', 
            3: 'homestead'
        }
        selected_modpack = modpack_map.get(setup_choice)
        server_type = 'fabric'  # All modpacks use Fabric
        
        modpack_sources = {
            'raspberry_flavoured': 'CurseForge',
            'melatonin': 'Modrinth',
            'homestead': 'CurseForge'
        }
        
        print_success(f"Selected modpack: {selected_modpack.replace('_', ' ').title()}")
        print_info(f"Source: {modpack_sources.get(selected_modpack, 'Unknown')}")
        print_info("Server type: Fabric (required for modpacks)")
        print()
        print("📦 Modpack will be downloaded from:")
        
        modpack_urls = {
            'raspberry_flavoured': "  https://www.curseforge.com/minecraft/modpacks/raspberry-flavoured",
            'melatonin': "  https://modrinth.com/modpack/melatonin",
            'homestead': "  https://www.curseforge.com/minecraft/modpacks/homestead-cozy"
        }
        
        print(modpack_urls.get(selected_modpack, ""))
        print()
        
        if modpack_sources.get(selected_modpack) == 'CurseForge':
            print_warning("CurseForge modpacks require an API key for automatic download.")
            print_info("Set CURSEFORGE_API_KEY in .env or download manually.")
        
        print()
        print_info("✨ AutoModpack will sync all mods to players automatically!")
        print_info("   Players only need Fabric + AutoModpack to join.")
    
    # Memory allocation
    print("\n--- Memory Configuration ---")
    print("Recommended RAM allocation:")
    print("  - Raspberry Pi: 1G-2G")
    print("  - Desktop/Server: 4G-8G")
    print("  - Termux: 1G-2G")
    
    mem_min = input("Minimum RAM [1G]: ").strip() or "1G"
    mem_max = input("Maximum RAM [4G]: ").strip() or "4G"
    
    # Schedule configuration
    print("\n--- Server Schedule ---")
    schedule_options = [
        "Always on (24/7)",
        "Timed (e.g., 6:00-22:00 daily)",
        "Weekdays only (with time limits)",
        "Weekends only",
        "Custom schedule"
    ]
    
    schedule_choice = ask_choice("Select schedule mode:", schedule_options, default=0)
    schedule_mode = ['always', 'timed', 'weekdays_only', 'weekends_only', 'custom'][schedule_choice]
    
    schedule_config = {"mode": schedule_mode}
    
    if schedule_mode == 'timed':
        start_hour = input("Start hour [6]: ").strip() or "6"
        end_hour = input("End hour [22]: ").strip() or "22"
        schedule_config['start_hour'] = int(start_hour)
        schedule_config['end_hour'] = int(end_hour)
    
    # Mods configuration
    print("\n--- Mods Configuration ---")
    
    install_perf_mods = False
    install_voice_chat = False
    install_automodpack = False
    
    if server_type in ['fabric', 'paper', 'purpur']:
        install_perf_mods = ask_yes_no("Install performance optimization mods?", default=True)
        if install_perf_mods:
            print_info("Will install: Lithium, Ferritecore, Spark, etc.")
    
    # Skip these prompts if modpack is selected (they're already configured)
    if selected_modpack:
        install_automodpack = True  # Always enable for modpacks
        install_voice_chat = ask_yes_no("Enable Simple Voice Chat for proximity voice?", default=True)
        if install_voice_chat:
            print_info("Voice chat will be auto-installed with the modpack")
    elif server_type == 'fabric':
        print("\n--- AutoModpack (Recommended) ---")
        print("AutoModpack automatically syncs mods to players when they connect.")
        print("✅ Players only need to install AutoModpack once - no manual mod setup!")
        print("✅ Great for beginners - seamless installation experience")
        install_automodpack = ask_yes_no("Enable AutoModpack for automatic mod syncing?", default=True)
        if install_automodpack:
            print_success("AutoModpack will be configured automatically")
            print_info("Players will auto-download all server mods on first connect")
        
        print("\n--- Voice Chat ---")
        print("Simple Voice Chat allows proximity voice communication in-game.")
        print("⚠️  Players will need to install the client mod to use voice chat.")
        if install_automodpack:
            print_info("(AutoModpack will auto-install this for players too!)")
        install_voice_chat = ask_yes_no("Enable Simple Voice Chat mod?", default=False)
        if install_voice_chat:
            print_info("Voice chat will be configured on port 24454 (UDP)")
            print_info("Remember to forward this port on your router!")
    
    # Update config.json
    config_path = 'config/config.json'
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
        else:
            config = {}
        
        if 'modules' not in config:
            config['modules'] = {}
        
        # Build modpack config
        modpack_config = {
            "enabled": selected_modpack is not None,
            "name": selected_modpack,
            "auto_install": True
        }
        
        config['modules']['minecraft'] = {
            "enabled": True,
            "server_type": server_type,
            "minecraft_version": mc_version,
            "memory_min": mem_min,
            "memory_max": mem_max,
            "port": 25565,
            "motd": f"Sulfur Bot - {selected_modpack.replace('_', ' ').title() if selected_modpack else 'Minecraft'} Server",
            "max_players": 20,
            "online_mode": True,
            "whitelist": True,
            "schedule": schedule_config,
            "boot_with_bot": True,
            "modpack": modpack_config,
            "performance_mods": {
                "enabled": install_perf_mods and not selected_modpack  # Modpacks include their own
            },
            "optional_mods": {
                "automodpack": {
                    "enabled": install_automodpack,
                    "beginner_friendly": True
                },
                "simple_voice_chat": {
                    "enabled": install_voice_chat,
                    "requires_client_mod": True
                }
            },
            "backups": {
                "enabled": True,
                "interval_hours": 6,
                "max_backups": 10
            }
        }
        
        # Add to features
        if 'features' not in config:
            config['features'] = {}
        config['features']['minecraft_server'] = True
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print_success("Minecraft configuration saved to config.json")
        
    except Exception as e:
        print_error(f"Failed to update config: {e}")
        return False
    
    # Download server JAR
    if ask_yes_no("Download Minecraft server now?"):
        print_step("This will be done when the bot starts or via the web dashboard.")
        print_info("You can also run: python -c \"from modules import minecraft_server; ...\"")
    
    print_success("Minecraft server configured")
    return True


# ==============================================================================
# WireGuard VPN Setup
# ==============================================================================

def setup_wireguard_vpn_automatic(plat: str) -> dict:
    """
    Automatically set up WireGuard VPN server with zero user input.
    
    This function:
    - Generates server keys automatically
    - Detects local IP for endpoint
    - Configures NAT and routing
    - Creates ready-to-use configuration
    
    Returns:
        dict with setup result and configuration details
    """
    result = {
        'success': False,
        'endpoint': None,
        'port': 51820,
        'server_address': '10.0.0.1/24',
        'server_public_key': None,
        'config_path': None,
        'error': None
    }
    
    print_step("Setting up WireGuard VPN automatically...")
    
    # Check if WireGuard is installed
    wg_ok, wg_msg = check_wireguard()
    if not wg_ok:
        print_info("WireGuard not installed. Installing now...")
        if plat == 'termux':
            run_command(['pkg', 'install', '-y', 'wireguard-tools'], quiet=True)
        elif plat in ['linux', 'raspberrypi', 'wsl']:
            run_command(['sudo', 'apt', 'install', '-y', 'wireguard', 'wireguard-tools'], quiet=True)
        elif plat == 'macos':
            run_command(['brew', 'install', 'wireguard-tools'], quiet=True)
        
        # Re-check
        wg_ok, wg_msg = check_wireguard()
        if not wg_ok:
            result['error'] = "Failed to install WireGuard"
            return result
    
    print_success("WireGuard available")
    
    # Auto-detect local IP using context manager for proper resource management
    local_ip = None
    try:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
    except Exception:
        pass
    
    if not local_ip:
        local_ip = "127.0.0.1"
        print_warning("Could not detect local IP, using localhost")
    else:
        print_success(f"Detected local IP: {local_ip}")
    
    result['endpoint'] = local_ip
    
    # Create config directory
    os.makedirs('config/wireguard', exist_ok=True)
    
    # Generate server keys
    print_step("Generating server encryption keys...")
    try:
        if shutil.which('wg'):
            # Generate private key
            priv_result = subprocess.run(['wg', 'genkey'], capture_output=True, text=True)
            if priv_result.returncode != 0:
                result['error'] = f"Failed to generate private key: {priv_result.stderr}"
                return result
            private_key = priv_result.stdout.strip()
            
            if not private_key:
                result['error'] = "Generated private key is empty"
                return result
            
            # Generate public key
            pub_result = subprocess.run(['wg', 'pubkey'], input=private_key, capture_output=True, text=True)
            if pub_result.returncode != 0:
                result['error'] = f"Failed to generate public key: {pub_result.stderr}"
                return result
            public_key = pub_result.stdout.strip()
            
            if not public_key:
                result['error'] = "Generated public key is empty"
                return result
            
            result['server_public_key'] = public_key
            print_success("Server keys generated")
        else:
            result['error'] = "WireGuard tools not found in PATH"
            return result
    except Exception as e:
        result['error'] = f"Failed to generate keys: {e}"
        return result
    
    # Detect network interface for NAT dynamically
    net_interface = None
    try:
        if plat in ['linux', 'raspberrypi', 'wsl']:
            # Get default route interface
            route_result = subprocess.run(['ip', 'route', 'show', 'default'], capture_output=True, text=True)
            if route_result.returncode == 0:
                parts = route_result.stdout.split()
                if 'dev' in parts:
                    dev_index = parts.index('dev')
                    if dev_index + 1 < len(parts):
                        net_interface = parts[dev_index + 1]
        elif plat == 'termux':
            # Try to detect active interface on Android
            route_result = subprocess.run(['ip', 'route', 'show', 'default'], capture_output=True, text=True)
            if route_result.returncode == 0:
                parts = route_result.stdout.split()
                if 'dev' in parts:
                    dev_index = parts.index('dev')
                    if dev_index + 1 < len(parts):
                        net_interface = parts[dev_index + 1]
            if not net_interface:
                net_interface = 'wlan0'  # Fallback for Android
        elif plat == 'macos':
            # Try to detect active interface on macOS
            route_result = subprocess.run(['route', '-n', 'get', 'default'], capture_output=True, text=True)
            if route_result.returncode == 0:
                for line in route_result.stdout.split('\n'):
                    if 'interface:' in line:
                        net_interface = line.split(':')[1].strip()
                        break
            if not net_interface:
                net_interface = 'en0'  # Fallback for macOS
    except Exception:
        net_interface = 'eth0'  # Fallback
    
    print_info(f"Using network interface: {net_interface or 'auto'}")
    
    # Create server configuration
    vpn_network = '10.0.0.0/24'
    server_address = '10.0.0.1/24'
    listen_port = 51820
    
    if plat in ['linux', 'raspberrypi', 'wsl'] and net_interface:
        server_config_content = f"""[Interface]
PrivateKey = {private_key}
Address = {server_address}
ListenPort = {listen_port}
SaveConfig = false

# NAT and forwarding for VPN clients
PostUp = sysctl -w net.ipv4.ip_forward=1
PostUp = iptables -t nat -A POSTROUTING -s {vpn_network} -o {net_interface} -j MASQUERADE
PostUp = iptables -A FORWARD -i %i -j ACCEPT
PostUp = iptables -A FORWARD -o %i -j ACCEPT

PostDown = iptables -t nat -D POSTROUTING -s {vpn_network} -o {net_interface} -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT
PostDown = iptables -D FORWARD -o %i -j ACCEPT

# Peers will be added automatically when users connect
"""
    else:
        # Simplified config for other platforms
        server_config_content = f"""[Interface]
PrivateKey = {private_key}
Address = {server_address}
ListenPort = {listen_port}

# Peers will be added automatically when users connect
"""
    
    # Save server config
    server_conf_path = 'config/wireguard/wg0.conf'
    with open(server_conf_path, 'w') as f:
        f.write(server_config_content)
    os.chmod(server_conf_path, 0o600)  # Secure permissions
    
    result['config_path'] = server_conf_path
    print_success(f"Server config saved to {server_conf_path}")
    
    # Save JSON config for the bot
    vpn_config = {
        "role": "server",
        "endpoint": f"{local_ip}:{listen_port}",
        "address": server_address,
        "port": listen_port,
        "public_key": public_key,
        "private_key": private_key,  # Note: Protected by file permissions (0o600). For production, consider additional encryption.
        "network_interface": net_interface,
        "peers": [],
        "auto_configured": True,
        "setup_date": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Save config with secure permissions
    vpn_config_path = 'config/wireguard/vpn_config.json'
    with open(vpn_config_path, 'w') as f:
        json.dump(vpn_config, f, indent=2)
    os.chmod(vpn_config_path, 0o600)  # Only owner can read/write
    print_info("VPN config saved with secure permissions (owner-only access)")
    
    # Try to start the VPN interface
    if plat in ['linux', 'raspberrypi']:
        print_step("Starting VPN interface...")
        
        # Copy config to system location
        code, _, _ = run_command(['sudo', 'cp', server_conf_path, '/etc/wireguard/wg0.conf'], quiet=True)
        if code == 0:
            run_command(['sudo', 'chmod', '600', '/etc/wireguard/wg0.conf'], quiet=True)
            
            # Enable and start
            run_command(['sudo', 'systemctl', 'enable', 'wg-quick@wg0'], quiet=True)
            code, _, err = run_command(['sudo', 'wg-quick', 'up', 'wg0'], quiet=True)
            
            if code == 0:
                print_success("VPN interface started and enabled on boot")
            else:
                print_warning("Could not start VPN interface automatically")
                print_info("Start manually with: sudo wg-quick up wg0")
    
    elif plat == 'termux':
        # Termux-specific: VPN server runs on device, clients connect via WireGuard Android app
        print_step("Configuring for Termux (non-rooted mode)...")
        print()
        print_info("📱 VPN on Termux (Non-Rooted Android):")
        print("   Since Termux doesn't have root access, the VPN server configuration")
        print("   has been saved for use with external VPN tools.")
        print()
        print_info("   For connecting OTHER devices to this server:")
        print("   1. Install WireGuard app on the device you want to connect")
        print("   2. Use /vpn addclient <device_name> in Discord")
        print("   3. Scan the QR code or import the config file")
        print()
        print_info("   Config saved to: config/wireguard/")
        print()
        
        # Export info file for easy reference
        try:
            info_file = 'config/wireguard/server_info.txt'
            with open(info_file, 'w') as f:
                f.write("=== Sulfur Bot VPN Server Info ===\n\n")
                f.write(f"Server IP: {local_ip}\n")
                f.write(f"Port: {listen_port} (UDP)\n")
                f.write(f"Public Key: {public_key}\n")
                f.write(f"\nSetup Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("\n--- How to Connect Devices ---\n")
                f.write("1. Use /vpn addclient <device_name> in Discord\n")
                f.write("2. Scan the QR code with WireGuard app\n")
                f.write("   OR import the config file from Downloads/SulfurVPN/\n")
                f.write("\n--- For Remote Access ---\n")
                f.write(f"Forward UDP port {listen_port} on your router to {local_ip}\n")
            print_success(f"Server info saved to {info_file}")
        except Exception as e:
            print_warning(f"Could not save server info file: {e}")
    
    result['success'] = True
    
    print()
    print_success("VPN Server configured automatically!")
    print()
    print_info("📋 VPN Connection Details:")
    print(f"   Server IP: {local_ip}")
    print(f"   Port: {listen_port} (UDP)")
    print(f"   Public Key: {public_key[:20]}...")
    print()
    print_info("💡 To connect devices:")
    print("   1. Use /vpn addclient <device_name> in Discord")
    print("   2. The bot will generate a config/QR code for your device")
    print("   3. Import into WireGuard app on your phone/computer")
    print()
    print_info("🌐 For remote access (outside your network):")
    print(f"   Forward UDP port {listen_port} on your router to {local_ip}")
    
    return result


def setup_wireguard_vpn(plat: str) -> bool:
    """Set up WireGuard VPN."""
    print_section("WireGuard VPN Setup")
    
    # Check WireGuard
    wg_ok, wg_msg = check_wireguard()
    if not wg_ok:
        print_warning("WireGuard not found")
        print_info(f"Install command: {get_wireguard_install_command(plat)}")
        
        # Try to install automatically
        print_info("Attempting automatic installation...")
        if plat == 'termux':
            run_command(['pkg', 'install', '-y', 'wireguard-tools'], quiet=True)
        elif plat in ['linux', 'raspberrypi', 'wsl']:
            run_command(['sudo', 'apt', 'install', '-y', 'wireguard', 'wireguard-tools'], quiet=True)
        elif plat == 'macos':
            run_command(['brew', 'install', 'wireguard-tools'], quiet=True)
        
        wg_ok, wg_msg = check_wireguard()
        if not wg_ok:
            print_warning("Could not install WireGuard automatically")
            if not ask_yes_no("Continue anyway?", default=False):
                return False
    else:
        print_success(wg_msg)
    
    # VPN role selection
    print("\n--- VPN Setup Mode ---")
    role_options = [
        "Automatic Setup (recommended - fully automatic server configuration)",
        "Manual Server Setup (enter details manually)",
        "Client Setup (connect to an existing VPN server)",
        "Skip VPN setup for now"
    ]
    
    role_choice = ask_choice("Select setup mode:", role_options, default=0)
    
    if role_choice == 3:
        print_info("VPN setup skipped")
        return True
    
    # Create config directory
    os.makedirs('config/wireguard', exist_ok=True)
    
    if role_choice == 0:
        # Fully automatic setup
        result = setup_wireguard_vpn_automatic(plat)
        return result['success']
    
    elif role_choice == 1:
        # Server setup
        print("\n--- VPN Server Configuration ---")
        
        # Try to auto-detect local network IP
        local_ip = None
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            pass
        
        # Get server endpoint
        print("\nEnter your server's endpoint (how clients will connect to you):")
        print_info("Options:")
        print("  1. Your public IP (if you have port forwarding set up)")
        print("  2. Your local network IP (for LAN-only access)")
        print("  3. A DDNS hostname (e.g., myserver.duckdns.org)")
        print()
        
        if local_ip:
            print_success(f"Detected local IP: {local_ip}")
            print_info(f"Use this for LAN-only access, or enter your public IP/domain for remote access")
        
        print()
        endpoint = input(f"Endpoint [{local_ip or 'your.domain.com'}]: ").strip()
        
        if not endpoint:
            if local_ip:
                endpoint = local_ip
                print_info(f"Using local IP: {endpoint} (LAN access only)")
            else:
                print_error("Endpoint is required for server setup")
                return False
        
        # VPN network
        vpn_network = input("VPN Network [10.0.0.1/24]: ").strip() or "10.0.0.1/24"
        vpn_port = input("VPN Port [51820]: ").strip() or "51820"
        
        # Save server config
        server_config = {
            "role": "server",
            "endpoint": f"{endpoint}:{vpn_port}",
            "address": vpn_network,
            "port": int(vpn_port),
            "peers": [],
            "auto_detected_ip": local_ip
        }
        
        with open('config/wireguard/vpn_config.json', 'w') as f:
            json.dump(server_config, f, indent=2)
        
        print_success("VPN server configuration saved")
        print_info("Generate keys and config by running the bot and using /vpn setup")
        
        # Helpful tips
        if local_ip and endpoint == local_ip:
            print()
            print_info("💡 For remote access (outside your local network):")
            print("   1. Set up port forwarding on your router (port 51820 UDP)")
            print("   2. Use a DDNS service like DuckDNS or No-IP")
            print("   3. Update the endpoint in config/wireguard/vpn_config.json")
        
    else:
        # Client setup
        print("\n--- VPN Client Configuration ---")
        print("You'll need the following from your VPN server admin:")
        print("  - Server public key")
        print("  - Server endpoint (IP:port)")
        print("  - Your assigned VPN IP address")
        
        server_pubkey = input("Server Public Key: ").strip()
        server_endpoint = input("Server Endpoint (IP:port): ").strip()
        client_address = input("Your VPN Address [10.0.0.2/32]: ").strip() or "10.0.0.2/32"
        
        if not server_pubkey or not server_endpoint:
            print_error("Server public key and endpoint are required")
            return False
        
        # Save client config
        client_config = {
            "role": "client",
            "server_public_key": server_pubkey,
            "server_endpoint": server_endpoint,
            "address": client_address
        }
        
        with open('config/wireguard/vpn_config.json', 'w') as f:
            json.dump(client_config, f, indent=2)
        
        print_success("VPN client configuration saved")
        print_info("Generate your keypair by running the bot")
    
    return True


# ==============================================================================
# Database Setup
# ==============================================================================

def list_database_backups() -> List[str]:
    """List available database backup files."""
    backup_dir = 'backups'
    if not os.path.exists(backup_dir):
        return []
    
    backups = []
    for filename in os.listdir(backup_dir):
        if filename.endswith('.sql'):
            backups.append(os.path.join(backup_dir, filename))
    
    # Sort by modification time, newest first
    backups.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    return backups


def export_database(db_host: str, db_user: str, db_pass: str, db_name: str, output_path: str) -> Tuple[bool, str]:
    """
    Export the database to a SQL file.
    
    Returns:
        Tuple of (success, message)
    """
    try:
        cmd = ['mysqldump', '-h', db_host, '-u', db_user]
        if db_pass:
            cmd.append(f'-p{db_pass}')
        else:
            cmd.append('--skip-password')
        cmd.append(db_name)
        
        code, stdout, stderr = run_command(cmd)
        
        if code == 0:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(stdout)
            return True, f"Database exported to {output_path}"
        else:
            return False, f"Export failed: {stderr}"
            
    except Exception as e:
        return False, str(e)


def import_database(db_host: str, db_user: str, db_pass: str, db_name: str, input_path: str) -> Tuple[bool, str]:
    """
    Import a database from a SQL file.
    
    Returns:
        Tuple of (success, message)
    """
    if not os.path.exists(input_path):
        return False, f"File not found: {input_path}"
    
    try:
        # Read SQL file
        with open(input_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        cmd = ['mysql', '-h', db_host, '-u', db_user]
        if db_pass:
            cmd.append(f'-p{db_pass}')
        cmd.append(db_name)
        
        # Run with SQL input (subprocess already imported at module level)
        result = subprocess.run(cmd, input=sql_content, capture_output=True, text=True)
        
        if result.returncode == 0:
            return True, "Database imported successfully"
        else:
            return False, f"Import failed: {result.stderr}"
            
    except Exception as e:
        return False, str(e)


def setup_database(plat: str) -> bool:
    """Set up the database with import/export options."""
    print_section("Database Setup")
    
    # Check MySQL
    mysql_ok, mysql_msg = check_mysql()
    if not mysql_ok:
        print_warning("MySQL/MariaDB not found")
        print_info(f"Install command: {get_mysql_install_command(plat)}")
        
        # Offer to install automatically
        if ask_yes_no("Would you like to install MySQL/MariaDB now?", default=True):
            print_step("Installing MySQL/MariaDB...")
            if install_mysql_mariadb(plat):
                print_success("MySQL/MariaDB installed successfully")
                # Re-check after installation
                mysql_ok, mysql_msg = check_mysql()
                if mysql_ok:
                    print_success(mysql_msg)
            else:
                print_error("Failed to install MySQL/MariaDB")
                print_info("Please install manually and re-run setup")
                return False
        else:
            if not ask_yes_no("Continue with database setup anyway?", default=False):
                return False
    else:
        print_success(mysql_msg)
    
    # Ensure database server is running
    if not ensure_mysql_running(plat):
        print_warning("Database server may not be running")
        print_info("Bot will attempt to connect, but may experience issues")
    
    # Check for existing backups
    backups = list_database_backups()
    
    # Database setup options
    print("\n--- Database Options ---")
    db_options = [
        "Create new empty database",
        "Import from existing backup file",
        "Skip database setup"
    ]
    
    if backups:
        print(f"\n{Colors.CYAN}Found {len(backups)} existing backup(s){Colors.RESET}")
    
    choice = ask_choice("Select database setup option:", db_options, default=0)
    
    if choice == 2:
        print_info("Database setup skipped")
        return True
    
    # Run the MySQL setup wizard first to create database and user
    print_step("Running MySQL setup wizard...")
    code, out, err = run_command([sys.executable, 'setup_wizard.py'])
    
    # Always show the output from setup_wizard for debugging
    if out:
        print(out)
    if err:
        print(f"{Colors.YELLOW}{err}{Colors.RESET}")
    
    if code != 0:
        print_warning("Database setup wizard encountered an error")
        print_info("Please review the error messages above")
        print_info("You can run 'python setup_wizard.py' manually later to retry")
        print_info("Make sure MySQL is installed and running before retrying")
        
        if not ask_yes_no("Continue anyway?", default=False):
            return False
    else:
        print_success("Database setup wizard completed successfully")
    
    # If importing, do the import
    if choice == 1:
        print_section("Import Database")
        
        if backups:
            print("\nAvailable backups:")
            for i, backup in enumerate(backups[:10]):
                filename = os.path.basename(backup)
                size_mb = os.path.getsize(backup) / 1024 / 1024
                mtime = time.strftime('%Y-%m-%d %H:%M', time.localtime(os.path.getmtime(backup)))
                print(f"  [{i + 1}] {filename} ({size_mb:.1f} MB) - {mtime}")
            
            backup_choice = input(f"\nSelect backup [1-{min(len(backups), 10)}] or enter path: ").strip()
            
            if backup_choice.isdigit():
                idx = int(backup_choice) - 1
                if 0 <= idx < len(backups):
                    backup_path = backups[idx]
                else:
                    print_error("Invalid selection")
                    return False
            elif os.path.exists(backup_choice):
                backup_path = backup_choice
            else:
                print_error(f"File not found: {backup_choice}")
                return False
        else:
            backup_path = input("Enter path to SQL backup file: ").strip()
            if not os.path.exists(backup_path):
                print_error(f"File not found: {backup_path}")
                return False
        
        # Load database credentials
        db_host = os.environ.get('DB_HOST', 'localhost')
        db_user = os.environ.get('DB_USER', 'sulfur_bot_user')
        db_pass = os.environ.get('DB_PASS', '')
        db_name = os.environ.get('DB_NAME', 'sulfur_bot')
        
        print_step(f"Importing from {os.path.basename(backup_path)}...")
        success, message = import_database(db_host, db_user, db_pass, db_name, backup_path)
        
        if success:
            print_success(message)
        else:
            print_error(message)
            return False
    
    # Offer to create a backup of the current state
    if ask_yes_no("\nCreate a backup of the current database?", default=True):
        os.makedirs('backups', exist_ok=True)
        
        db_host = os.environ.get('DB_HOST', 'localhost')
        db_user = os.environ.get('DB_USER', 'sulfur_bot_user')
        db_pass = os.environ.get('DB_PASS', '')
        db_name = os.environ.get('DB_NAME', 'sulfur_bot')
        
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        backup_path = f"backups/database_backup_{timestamp}.sql"
        
        print_step(f"Creating backup: {backup_path}")
        success, message = export_database(db_host, db_user, db_pass, db_name, backup_path)
        
        if success:
            print_success(message)
        else:
            print_warning(f"Backup failed: {message}")
    
    return True


# ==============================================================================
# Main Setup Wizard
# ==============================================================================

def run_full_setup():
    """Run the complete setup wizard."""
    print_header("SULFUR BOT - MASTER SETUP WIZARD")
    
    # Detect platform
    plat = detect_platform()
    print(f"Detected Platform: {Colors.BOLD}{get_platform_name(plat)}{Colors.RESET}")
    
    # Check Python
    py_ok, py_msg = check_python_version()
    if not py_ok:
        print_error(py_msg)
        sys.exit(1)
    print_success(f"Python: {py_msg}")
    
    # Choose setup mode
    print_section("Setup Mode")
    print("How would you like to proceed?\n")
    
    mode_options = [
        "Full Automatic Setup (recommended - installs everything automatically)",
        "Interactive Setup (choose individual components)",
        "Quick Setup (bot only, minimal questions)"
    ]
    
    mode_choice = ask_choice("Select setup mode:", mode_options, default=0)
    
    if mode_choice == 0:
        # Full automatic setup - install everything with minimal user input
        print_section("Full Automatic Setup")
        print_info("This will install all system dependencies, set up the database,")
        print_info("configure VPN, and prepare everything for you automatically.")
        print()
        
        if not ask_yes_no("Proceed with full automatic setup?", default=True):
            print_info("Setup cancelled")
            return
        
        # Step 1: Install all system dependencies
        print_section("Step 1: System Dependencies")
        install_all_system_dependencies(plat)
        
        # Step 2: Python dependencies
        print_section("Step 2: Python Dependencies")
        install_python_dependencies()
        
        # Step 3: Environment file
        print_section("Step 3: Configuration")
        setup_env_file()
        
        # Step 4: Database
        print_section("Step 4: Database Setup")
        setup_database(plat)
        
        # Step 5: VPN (automatic)
        print_section("Step 5: VPN Setup")
        vpn_result = setup_wireguard_vpn_automatic(plat)
        
        # Step 6: Ask about Minecraft
        print_section("Step 6: Minecraft Server (Optional)")
        if ask_yes_no("Set up Minecraft server?", default=False):
            setup_minecraft_server(plat)
        
        # Summary
        print_header("SETUP COMPLETE")
        print_success("All components have been set up automatically!")
        print()
        print("Your Sulfur Bot is ready to use:")
        print()
        print("  🤖 Start the bot:")
        print("     python bot.py")
        print()
        print("  🌐 Web Dashboard:")
        print("     http://localhost:5000")
        print()
        if vpn_result.get('success'):
            print("  🔐 VPN Access:")
            print(f"     Server: {vpn_result.get('endpoint')}:{vpn_result.get('port')}")
            print("     Use /vpn addclient in Discord to add devices")
            print()
        print("  💬 Discord Commands:")
        print("     /help - Show all commands")
        print("     /admin - Admin panel")
        print()
        return
    
    elif mode_choice == 2:
        # Quick setup - just bot dependencies
        print_section("Quick Setup")
        
        # Install system dependencies
        install_all_system_dependencies(plat)
        
        # Python dependencies
        install_python_dependencies()
        
        # Basic env setup
        setup_env_file()
        
        # Database
        setup_database(plat)
        
        print_header("QUICK SETUP COMPLETE")
        print("Start the bot with: python bot.py")
        return
    
    # Interactive setup (original flow)
    print_section("Setup Options")
    print("What would you like to set up?\n")
    
    setup_options = [
        ("System Dependencies (All build tools & packages)", True),
        ("Bot Dependencies & Configuration", True),
        ("Database (MySQL/MariaDB)", True),
        ("WireGuard VPN", True),
        ("Minecraft Server", False)
    ]
    
    selected = []
    for option, default in setup_options:
        if ask_yes_no(f"Set up {option}?", default=default):
            selected.append(option)
    
    if not selected:
        print_warning("No options selected. Exiting.")
        return
    
    print(f"\nSelected: {', '.join(selected)}")
    if not ask_yes_no("\nProceed with setup?"):
        print_info("Setup cancelled")
        return
    
    # Run selected setups
    success_count = 0
    
    if "System Dependencies (All build tools & packages)" in selected:
        print_section("Step 1: System Dependencies")
        if install_all_system_dependencies(plat):
            success_count += 1
    
    if "Bot Dependencies & Configuration" in selected:
        print_section("Step 2: Bot Dependencies")
        
        # Check dependencies
        pip_ok, pip_msg = check_pip()
        if pip_ok:
            print_success(f"pip: {pip_msg}")
            if install_python_dependencies():
                success_count += 1
        else:
            print_error(pip_msg)
        
        # Setup .env
        if setup_env_file():
            success_count += 1
    
    if "Database (MySQL/MariaDB)" in selected:
        if setup_database(plat):
            success_count += 1
    
    if "WireGuard VPN" in selected:
        if setup_wireguard_vpn(plat):
            success_count += 1
    
    if "Minecraft Server" in selected:
        if setup_minecraft_server(plat):
            success_count += 1
    
    # Summary
    print_header("SETUP COMPLETE")
    
    print(f"Completed {success_count}/{len(selected)} setup tasks\n")
    
    print("Next steps:")
    print("  1. Review and update config/config.json if needed")
    print("  2. Start the bot: python bot.py")
    print("  3. Access web dashboard: http://localhost:5000")
    print()
    
    if "Minecraft Server" in selected:
        print("Minecraft Server:")
        print("  - Server will download on first start")
        print("  - Use /mcstart and /mcstop in Discord (admin only)")
        print("  - Access Minecraft dashboard in web UI")
        print()
    
    if "WireGuard VPN" in selected:
        print("WireGuard VPN:")
        print("  - Complete setup via Discord commands")
        print("  - Use /vpn status to check connection")
        print()


def run_quick_check():
    """Run a quick system check without full setup."""
    print_header("SULFUR BOT - SYSTEM CHECK")
    
    plat = detect_platform()
    print(f"Platform: {get_platform_name(plat)}\n")
    
    checks = [
        ("Python", check_python_version),
        ("pip", check_pip),
        ("Git", check_git),
        ("MySQL/MariaDB", check_mysql),
        ("Java", check_java),
        ("WireGuard", check_wireguard)
    ]
    
    print("Checking system dependencies:\n")
    
    for name, check_func in checks:
        ok, msg = check_func()
        if ok:
            print_success(f"{name}: {msg}")
        else:
            print_warning(f"{name}: {msg}")
    
    # Check for config files
    print("\nChecking configuration files:\n")
    
    config_files = [
        ('.env', 'Environment configuration'),
        ('config/config.json', 'Bot configuration'),
        ('config/system_prompt.txt', 'AI system prompt'),
        ('config/wireguard/vpn_config.json', 'VPN configuration'),
    ]
    
    for path, desc in config_files:
        if os.path.exists(path):
            print_success(f"{desc}: {path}")
        else:
            print_warning(f"{desc}: {path} (not found)")


# ==============================================================================
# Entry Point
# ==============================================================================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Sulfur Bot Setup Wizard')
    parser.add_argument('--check', action='store_true', help='Run system check only')
    parser.add_argument('--minecraft', action='store_true', help='Set up Minecraft server only')
    parser.add_argument('--vpn', action='store_true', help='Set up VPN only')
    parser.add_argument('--database', action='store_true', help='Set up database only')
    parser.add_argument('--config', action='store_true', help='Set up configuration only')
    
    args = parser.parse_args()
    
    try:
        if args.check:
            run_quick_check()
        elif args.minecraft:
            plat = detect_platform()
            setup_minecraft_server(plat)
        elif args.vpn:
            plat = detect_platform()
            setup_wireguard_vpn(plat)
        elif args.database:
            plat = detect_platform()
            setup_database(plat)
        elif args.config:
            setup_env_file()
        else:
            run_full_setup()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user")
        sys.exit(0)
    except Exception as e:
        print_error(f"Setup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
