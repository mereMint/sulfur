#!/usr/bin/env python3
"""
Sulfur Bot - Installation Verification Script
Checks for common installation issues and provides fix suggestions
"""

import sys
import os
import subprocess
import importlib.util

# ANSI color codes
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
CYAN = '\033[0;36m'
NC = '\033[0m'  # No Color
BOLD = '\033[1m'

def print_header(text):
    print(f"\n{CYAN}{BOLD}{'=' * 70}{NC}")
    print(f"{CYAN}{BOLD}{text:^70}{NC}")
    print(f"{CYAN}{BOLD}{'=' * 70}{NC}\n")

def print_success(text):
    print(f"{GREEN}✓ {text}{NC}")

def print_error(text):
    print(f"{RED}✗ {text}{NC}")

def print_warning(text):
    print(f"{YELLOW}⚠ {text}{NC}")

def print_info(text):
    print(f"{BLUE}ℹ {text}{NC}")

def check_python_version():
    """Check if Python version is 3.8 or higher"""
    print_header("Python Version Check")
    
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    
    if version.major >= 3 and version.minor >= 8:
        print_success(f"Python {version_str} (✓ >= 3.8)")
        return True
    else:
        print_error(f"Python {version_str} (✗ < 3.8)")
        print_info("Please upgrade to Python 3.8 or higher")
        return False

def check_virtual_environment():
    """Check if running in a virtual environment"""
    print_header("Virtual Environment Check")
    
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    
    if in_venv:
        print_success("Running in virtual environment")
        print_info(f"Virtual env: {sys.prefix}")
        return True
    else:
        print_warning("Not running in virtual environment")
        print_info("It's recommended to use a virtual environment:")
        print_info("  python -m venv venv")
        print_info("  source venv/bin/activate  # Linux/Mac/Termux")
        print_info("  .\\venv\\Scripts\\Activate.ps1  # Windows")
        return False

def check_package(package_name, import_name=None):
    """Check if a Python package is installed"""
    if import_name is None:
        import_name = package_name
    
    try:
        spec = importlib.util.find_spec(import_name)
        if spec is not None:
            return True
    except (ImportError, ModuleNotFoundError):
        pass
    return False

def check_required_packages():
    """Check if all required packages are installed"""
    print_header("Required Python Packages")
    
    packages = [
        ("discord.py", "discord", "pip install discord.py[voice]"),
        ("PyNaCl (voice)", "nacl", "See PYNACL_TERMUX_FIX.md for Termux"),
        ("mysql-connector-python", "mysql.connector", "pip install mysql-connector-python"),
        ("aiohttp", "aiohttp", "pip install aiohttp"),
        ("python-dotenv", "dotenv", "pip install python-dotenv"),
        ("Flask", "flask", "pip install Flask"),
        ("Flask-SocketIO", "flask_socketio", "pip install Flask-SocketIO"),
        ("waitress", "waitress", "pip install waitress"),
        ("psutil", "psutil", "pip install psutil"),
        ("yt-dlp", "yt_dlp", "pip install yt-dlp"),
    ]
    
    all_installed = True
    for display_name, import_name, install_cmd in packages:
        if check_package(import_name):
            print_success(f"{display_name}")
        else:
            print_error(f"{display_name} - NOT INSTALLED")
            print_info(f"  Install: {install_cmd}")
            all_installed = False
    
    return all_installed

def check_pynacl_specifically():
    """Special check for PyNaCl on Termux"""
    print_header("PyNaCl Voice Support Check")
    
    try:
        import nacl
        from nacl import signing
        
        # Try to use it
        signing.SigningKey.generate()
        print_success("PyNaCl is installed and working correctly")
        
        # Check if we're on Termux
        if os.path.exists("/data/data/com.termux"):
            print_info("Running on Termux - using system libsodium")
        
        return True
    except ImportError:
        print_error("PyNaCl is not installed")
        
        if os.path.exists("/data/data/com.termux"):
            print_warning("You're on Termux! PyNaCl requires special installation:")
            print_info("See PYNACL_TERMUX_FIX.md for detailed instructions")
            print_info("Quick fix:")
            print_info("  pkg install build-essential binutils pkg-config libsodium clang")
            print_info("  export SODIUM_INSTALL=system")
            print_info("  pip install --upgrade pip wheel setuptools")
            print_info("  pip install PyNaCl")
        else:
            print_info("Install: pip install PyNaCl")
        
        return False
    except Exception as e:
        print_error(f"PyNaCl is installed but not working: {e}")
        return False

def check_env_file():
    """Check if .env file exists and is configured"""
    print_header("Environment Configuration Check")
    
    if not os.path.exists(".env"):
        print_error(".env file not found")
        print_info("Create .env file with:")
        print_info("  DISCORD_BOT_TOKEN=your_token_here")
        print_info("  GEMINI_API_KEY=your_key_here")
        print_info("  DB_HOST=localhost")
        print_info("  DB_USER=sulfur_bot_user")
        print_info("  DB_NAME=sulfur_bot")
        print_info("")
        print_info("Or copy from example: cp .env.example .env")
        return False
    
    print_success(".env file exists")
    
    # Check if it has critical variables
    with open(".env", "r") as f:
        content = f.read()
    
    required_vars = ["DISCORD_BOT_TOKEN", "DB_HOST", "DB_USER", "DB_NAME"]
    missing = []
    
    for var in required_vars:
        if var not in content:
            missing.append(var)
    
    if missing:
        print_warning(f"Missing variables: {', '.join(missing)}")
        return False
    else:
        print_success("All required variables present")
        return True

def check_config_files():
    """Check if required config files exist"""
    print_header("Configuration Files Check")
    
    files = [
        ("config/config.json", "Bot configuration"),
        ("config/system_prompt.txt", "AI system prompt"),
        ("requirements.txt", "Python dependencies"),
    ]
    
    all_exist = True
    for filepath, description in files:
        if os.path.exists(filepath):
            print_success(f"{filepath} - {description}")
        else:
            print_error(f"{filepath} - MISSING ({description})")
            all_exist = False
    
    return all_exist

def check_termux_specific():
    """Check Termux-specific requirements"""
    if not os.path.exists("/data/data/com.termux"):
        return True  # Not on Termux, skip
    
    print_header("Termux-Specific Checks")
    
    # Check for required system packages
    packages = [
        "build-essential",
        "binutils", 
        "pkg-config",
        "libsodium",
        "clang",
        "python",
        "git",
        "mariadb",
    ]
    
    print_info("Checking Termux packages...")
    all_installed = True
    
    # Get installed packages once
    result = subprocess.run(
        ["pkg", "list-installed"],
        capture_output=True,
        text=True
    )
    installed_packages = result.stdout
    
    for pkg in packages:
        if pkg in installed_packages:
            print_success(f"{pkg}")
        else:
            print_error(f"{pkg} - NOT INSTALLED")
            all_installed = False
    
    if not all_installed:
        print_info("\nInstall missing packages:")
        print_info("  pkg install " + " ".join(packages))
    
    # Check SODIUM_INSTALL variable
    if "SODIUM_INSTALL" in os.environ:
        if os.environ["SODIUM_INSTALL"] == "system":
            print_success("SODIUM_INSTALL=system is set")
        else:
            print_warning(f"SODIUM_INSTALL={os.environ['SODIUM_INSTALL']} (should be 'system')")
    else:
        print_warning("SODIUM_INSTALL not set")
        print_info("  export SODIUM_INSTALL=system")
    
    return all_installed

def main():
    print(f"\n{BOLD}{CYAN}╔══════════════════════════════════════════════════════════════════╗{NC}")
    print(f"{BOLD}{CYAN}║       SULFUR BOT - INSTALLATION VERIFICATION SCRIPT              ║{NC}")
    print(f"{BOLD}{CYAN}╚══════════════════════════════════════════════════════════════════╝{NC}")
    
    results = {
        "Python Version": check_python_version(),
        "Virtual Environment": check_virtual_environment(),
        "Required Packages": check_required_packages(),
        "PyNaCl Voice Support": check_pynacl_specifically(),
        "Environment File": check_env_file(),
        "Config Files": check_config_files(),
    }
    
    # Termux-specific checks
    if os.path.exists("/data/data/com.termux"):
        results["Termux Packages"] = check_termux_specific()
    
    # Summary
    print_header("VERIFICATION SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for check, result in results.items():
        if result:
            print_success(f"{check}")
        else:
            print_error(f"{check}")
    
    print(f"\n{BOLD}Score: {passed}/{total} checks passed{NC}\n")
    
    if passed == total:
        print_success("✓ All checks passed! Your installation looks good.")
        print_info("\nNext steps:")
        print_info("  1. Configure your .env file with your Discord token")
        print_info("  2. Start MariaDB: mysqld_safe & (Termux) or systemctl start mariadb (Linux)")
        print_info("  3. Run the bot: python bot.py")
    else:
        print_warning("⚠ Some checks failed. Please fix the issues above.")
        print_info("\nFor help with common errors, see:")
        print_info("  - INSTALLATION_ERROR_FIXES.md")
        print_info("  - PYNACL_TERMUX_FIX.md (for Termux)")
    
    print("")
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
