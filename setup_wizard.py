"""
Interactive MySQL Setup Wizard for Sulfur Bot
Handles multiple scenarios and provides step-by-step guidance

Supports custom database configuration via .env file or command line arguments.
"""

import sys
import os
import subprocess
import shutil
from getpass import getpass

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available, will use defaults

try:
    import mysql.connector
except ModuleNotFoundError:
    print("\n" + "=" * 60)
    print("ERROR: mysql-connector-python not installed".center(60))
    print("=" * 60 + "\n")
    print("The mysql-connector-python package is required to run this script.")
    print()
    print("To install it, run:")
    print("  pip install mysql-connector-python")
    print()
    print("Or install all dependencies:")
    print("  pip install -r requirements.txt")
    print()
    print("If running through install_wizard.ps1, this should not happen.")
    print("Please ensure dependencies are installed before database setup.")
    print()
    sys.exit(1)

def print_header(text):
    print("\n" + "=" * 60)
    print(text.center(60))
    print("=" * 60 + "\n")

def print_section(text):
    print(f"\n{'─' * 60}")
    print(f"  {text}")
    print('─' * 60)

def validate_identifier(name, identifier_type="identifier"):
    """
    Validate a MySQL identifier (database name, username, hostname).
    Returns True if valid, raises ValueError if invalid.
    
    MySQL identifiers can contain:
    - Letters (a-z, A-Z)
    - Digits (0-9)
    - Underscores (_)
    - Dollar signs ($)
    
    For safety, we restrict to alphanumeric and underscore only.
    """
    import re
    if not name:
        raise ValueError(f"{identifier_type} cannot be empty")
    if len(name) > 64:  # MySQL max identifier length
        raise ValueError(f"{identifier_type} cannot exceed 64 characters")
    if not re.match(r'^[a-zA-Z0-9_]+$', name):
        raise ValueError(f"{identifier_type} can only contain letters, numbers, and underscores")
    return True

def validate_hostname(host):
    """
    Validate a hostname for MySQL connection.
    Allows localhost, IP addresses, and domain names.
    """
    import re
    if not host:
        raise ValueError("Hostname cannot be empty")
    # Allow localhost, IP addresses, and simple hostnames
    if host == 'localhost' or host == '127.0.0.1':
        return True
    # Simple hostname/IP validation
    if re.match(r'^[a-zA-Z0-9._-]+$', host):
        return True
    raise ValueError(f"Invalid hostname format: {host}")

# Get database configuration from environment or use defaults
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_USER = os.environ.get('DB_USER', 'sulfur_bot_user')
DB_PASS = os.environ.get('DB_PASS', '')
DB_NAME = os.environ.get('DB_NAME', 'sulfur_bot')
MYSQL_ROOT_PASSWORD = os.environ.get('MYSQL_ROOT_PASSWORD', '')  # Optional: provide to auto-provision

# Quick mode: if DB already works with provided credentials, skip setup
def quick_db_check():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS if DB_PASS else None,
            database=DB_NAME
        )
        conn.close()
        return True
    except Exception:
        return False


def auto_provision_with_root(root_password: str):
    """Create DB and user automatically using provided root password."""
    conn = mysql.connector.connect(host='localhost', user='root', password=root_password)
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cursor.execute(f"DROP USER IF EXISTS '{DB_USER}'@'{DB_HOST}'")
    if DB_PASS:
        cursor.execute(f"CREATE USER '{DB_USER}'@'{DB_HOST}' IDENTIFIED BY %s", (DB_PASS,))
    else:
        cursor.execute(f"CREATE USER '{DB_USER}'@'{DB_HOST}' IDENTIFIED BY ''")
    cursor.execute(f"GRANT ALL PRIVILEGES ON `{DB_NAME}`.* TO '{DB_USER}'@'{DB_HOST}'")
    cursor.execute("FLUSH PRIVILEGES")
    conn.commit()
    cursor.close()
    conn.close()
    return True


def run_simple_command(cmd):
    """Run a simple shell command and return (code, stdout, stderr)."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except FileNotFoundError:
        return 127, '', 'command not found'
    except Exception as e:
        return 1, '', str(e)


def mysql_installed():
    """Check if mysql/mariadb client/server binaries exist."""
    return any(shutil.which(cmd) for cmd in ["mysql", "mariadb", "mysqld", "mariadbd"])


def install_mysql_if_missing():
    """Attempt to install MySQL/MariaDB using common package managers."""
    if mysql_installed():
        return True
    # Termux
    if shutil.which("pkg"):
        print("Attempting install via 'pkg install mariadb'...")
        code, out, err = run_simple_command(["pkg", "install", "mariadb", "-y"])
        if code == 0:
            return True
        print(f"Install failed: {err or out}")
        return False
    # Debian/Ubuntu
    if shutil.which("apt-get") or shutil.which("apt"):
        print("Attempting install via apt (mariadb-server mariadb-client)...")
        code, out, err = run_simple_command(["sudo", "apt-get", "update"])
        if code != 0:
            print(f"apt-get update failed: {err or out}")
            return False
        code, out, err = run_simple_command(["sudo", "apt-get", "install", "-y", "mariadb-server", "mariadb-client"])
        if code == 0:
            return True
        print(f"apt-get install failed: {err or out}")
        return False
    # Homebrew
    if shutil.which("brew"):
        print("Attempting install via brew install mariadb...")
        code, out, err = run_simple_command(["brew", "install", "mariadb"])
        if code == 0:
            return True
        print(f"brew install failed: {err or out}")
        return False
    print("No supported package manager found for auto-install. Please install MySQL/MariaDB manually.")
    return False


def mysql_server_reachable():
    """Best-effort reachability check; access denied still means reachable."""
    checks = [
        ["mysqladmin", "ping", "-uroot", "--connect-timeout=2"],
        ["mariadb-admin", "ping", "-uroot", "--connect-timeout=2"],
    ]
    for cmd in checks:
        code, _, _ = run_simple_command(cmd)
        if code in (0, 1):  # 1 can be "access denied" but server is up
            return True
    return False


def try_start_mysql_service():
    """Try to start MySQL/MariaDB using common service commands."""
    start_cmds = [
        ["sudo", "systemctl", "start", "mysql"],
        ["sudo", "systemctl", "start", "mariadb"],
        ["sudo", "service", "mysql", "start"],
        ["sudo", "service", "mariadb", "start"],
    ]
    for cmd in start_cmds:
        code, out, err = run_simple_command(cmd)
        if code == 0:
            return True, "".join([out, err]).strip()
    return False, ""

# Validate configuration to prevent SQL injection
try:
    validate_hostname(DB_HOST)
    validate_identifier(DB_USER, "Database user")
    validate_identifier(DB_NAME, "Database name")
    # Password doesn't need identifier validation, but we'll escape it properly when used
except ValueError as e:
    print(f"\n❌ Configuration Error: {e}")
    print("\nPlease check your .env file for invalid characters.")
    print("Database name and user can only contain letters, numbers, and underscores.")
    sys.exit(1)

print_header("SULFUR BOT - MYSQL SETUP WIZARD")

print("This wizard will help you set up the MySQL database for Sulfur Bot.")
print()
# Ensure MySQL/MariaDB is available; auto-install when possible
if not mysql_installed():
    print("MySQL/MariaDB not detected on this system.")
    choice = input("Attempt automatic installation? [Y/n]: ").strip().lower()
    if choice in ("", "y", "yes"):
        if install_mysql_if_missing():
            print("✅ Installation attempt finished.")
            started, _ = try_start_mysql_service()
            if started:
                print("✅ MySQL service start attempted.")
        else:
            print("❌ Automatic installation failed. Please install MySQL/MariaDB manually and rerun.")
            sys.exit(1)
    else:
        print("Installation skipped. Please install MySQL/MariaDB and rerun this wizard.")
        sys.exit(1)

# If service still not reachable, try to start it
if not mysql_server_reachable():
    started, _ = try_start_mysql_service()
    if started:
        print("✅ Attempted to start MySQL service.")
    else:
        print("⚠️  Could not verify MySQL service. Continuing to connection checks...")

if quick_db_check():
    print("Detected existing working database connection with provided credentials.")
    print("Skipping setup and exiting successfully.")
    sys.exit(0)

# Fast-path auto provision if MYSQL_ROOT_PASSWORD is provided (non-empty)
if MYSQL_ROOT_PASSWORD:
    try:
        print("Attempting automatic database provisioning using MYSQL_ROOT_PASSWORD...")
        if auto_provision_with_root(MYSQL_ROOT_PASSWORD):
            if quick_db_check():
                print("Auto-provision successful. Exiting.")
                sys.exit(0)
    except mysql.connector.Error as err:
        print(f"Auto-provision failed: {err}")
    except Exception as e:
        print(f"Auto-provision unexpected error: {e}")

print("Current configuration (from .env or defaults):")
print(f"  • Database Host: {DB_HOST}")
print(f"  • Database Name: {DB_NAME}")
print(f"  • Database User: {DB_USER}")
print(f"  • Password: {'(set)' if DB_PASS else '(empty)'}")
print()
print("You can customize these values by editing the .env file.")
print()

# Check if MySQL is accessible
print_section("Step 1: Testing MySQL Connection")

print("Attempting to connect to MySQL...")
print()

# Best-effort auto-start if server is unreachable
if not mysql_server_reachable():
    print("MySQL server does not appear to be reachable.")
    if input("Attempt to start MySQL automatically? [y/N]: ").strip().lower() == 'y':
        started, msg = try_start_mysql_service()
        if started:
            print("✅ Attempted to start MySQL service")
        else:
            print("⚠️  Could not start MySQL automatically. Please start it manually.")
    else:
        print("Skipping automatic start; will try to connect anyway.")
    print()

connected = False
root_conn = None
last_error = None
max_attempts = 3

for attempt in range(1, max_attempts + 1):
    if attempt == 1:
        print("Trying: root with no password...", end=" ")
        password = ""
    else:
        print(f"Trying: root with password (attempt {attempt}/{max_attempts})")
        password = getpass("Enter MySQL root password: ")
    
    try:
        root_conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password=password
        )
        print("✅ Connected!")
        connected = True
        break
    except mysql.connector.Error as err:
        last_error = err
        if err.errno == 2003:
            # Connection refused - server is not running
            print(f"❌ Failed: {err}")
            print()
            print("⚠️  MySQL server is not running or not accepting connections.")
            print("   Please start the server first and try again.")
            break  # Exit loop immediately, don't ask for more passwords
        elif err.errno == 1045:
            print("❌ Access denied")
            if attempt < max_attempts:
                print("Please try again with the correct root password.")
        else:
            print(f"❌ Failed: {err}")
            if attempt < max_attempts:
                print("Please try again with the correct root password.")
        continue

if not connected:
    print_section("❌ Cannot Connect to MySQL")
    print()
    
    # Provide targeted guidance based on error type
    if last_error and last_error.errno == 2003:
        # Connection refused - server not running
        print("MySQL server is not running or not accepting connections.")
        print()
        print("Please start the MySQL/MariaDB server first:")
        print()
        print("  • Windows:")
        print("    Get-Service MySQL84  # Check status")
        print("    Start-Service MySQL84  # Start the service")
        print()
        print("  • Linux (systemd):")
        print("    sudo systemctl status mysql")
        print("    sudo systemctl start mysql  # or mariadb")
        print()
        print("  • Termux (Android):")
        print("    mysqld_safe --datadir=$PREFIX/var/lib/mysql &")
        print("    # Wait a few seconds for it to start")
        print()
        print("  • macOS (Homebrew):")
        print("    brew services start mariadb")
        print()
    elif last_error and last_error.errno == 1045:
        # Access denied - authentication issue
        print("Could not authenticate with MySQL as root.")
        print()
        print("Possible solutions:")
        print()
        print("  1. Incorrect root password")
        print("     → Run this wizard again with the correct password")
        print()
        print("  2. Reset the root password:")
        print("     → See: MYSQL_PASSWORD_RESET.md (Windows)")
        print("     → Or run: sudo mysql -u root")
        print("     → Then: ALTER USER 'root'@'localhost' IDENTIFIED BY 'newpassword';")
        print()
    else:
        # Other errors
        print("Could not connect to MySQL as root. Possible issues:")
        print()
        print("  1. MySQL service not running")
        print("     → Check if MySQL is running:")
        print("       - Windows: Get-Service MySQL84")
        print("       - Linux:   sudo systemctl status mysql")
        print("       - Fix:     Start-Service MySQL84  /  sudo systemctl start mysql")
        print()
        print("  2. Incorrect root password")
        print("     → If you forgot the root password, reset it:")
        print("       - See: MYSQL_PASSWORD_RESET.md  (Windows)")
        print("       - Or run: sudo mysql -u root")
        print("       - Then: ALTER USER 'root'@'localhost' IDENTIFIED BY 'newpassword';")
        print()
        print("  3. MySQL not installed properly")
        print("     → Reinstall MySQL (see INSTALLATION_GUIDE.md)")
        print()
    
    if last_error:
        print(f"Technical details: {last_error}")
    print()
    sys.exit(1)

# Now set up the database
print_section("Step 2: Creating Database and User")

def escape_password(password):
    """
    Escape special characters in password for MySQL.
    Note: For user creation, we need to escape single quotes and backslashes properly.
    MySQL string literal escaping requires: ' -> '' and \\ -> \\\\
    """
    if not password:
        return ''
    # Escape backslashes first (they escape other characters)
    password = password.replace('\\', '\\\\')
    # Then escape single quotes by doubling them (MySQL standard escaping)
    password = password.replace("'", "''")
    return password

try:
    cursor = root_conn.cursor()
    
    # Create database with configurable name
    # DB_NAME is already validated to contain only safe characters
    print(f"Creating database '{DB_NAME}'...", end=" ")
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    print("✅")
    
    # Drop old user
    # DB_USER and DB_HOST are already validated
    print(f"Removing old user '{DB_USER}' if exists...", end=" ")
    cursor.execute(f"DROP USER IF EXISTS '{DB_USER}'@'{DB_HOST}'")
    print("✅")
    
    # Create user with configurable name and password
    # Password is escaped to handle special characters safely
    escaped_pass = escape_password(DB_PASS)
    
    print(f"Creating user '{DB_USER}'...", end=" ")
    try:
        if DB_PASS:
            cursor.execute(f"CREATE USER '{DB_USER}'@'{DB_HOST}' IDENTIFIED BY '{escaped_pass}'")
        else:
            cursor.execute(f"CREATE USER '{DB_USER}'@'{DB_HOST}' IDENTIFIED BY ''")
        print("✅")
    except mysql.connector.Error as err:
        # Try alternative authentication methods
        if "plugin" in str(err).lower():
            print()
            print("  ⚠️  Authentication plugin issue, trying alternative method...")
            if DB_PASS:
                cursor.execute(f"CREATE USER '{DB_USER}'@'{DB_HOST}' IDENTIFIED WITH mysql_native_password BY '{escaped_pass}'")
            else:
                cursor.execute(f"CREATE USER '{DB_USER}'@'{DB_HOST}' IDENTIFIED WITH mysql_native_password BY ''")
            print("  ✅ User created with alternative method")
        else:
            raise
    
    # Grant privileges
    print("Granting privileges...", end=" ")
    cursor.execute(f"GRANT ALL PRIVILEGES ON `{DB_NAME}`.* TO '{DB_USER}'@'{DB_HOST}'")
    cursor.execute("FLUSH PRIVILEGES")
    print("✅")
    
    cursor.close()
    root_conn.close()
    
    print_section("Step 3: Verifying Setup")
    
    # Test connection as bot user
    print("Testing bot user connection...", end=" ")
    try:
        # Try with the password from the config
        test_conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS if DB_PASS else None,
            database=DB_NAME
        )
        test_conn.close()
        print("✅")
    except mysql.connector.Error as err:
        print(f"⚠️ ")
        print()
        print("Warning: Connection test failed, but database may have been created successfully.")
        print(f"Error: {err}")
        print()
        print("This could happen if:")
        print("  • The MySQL server needs a moment to initialize")
        print("  • The password authentication method differs")
        print("  • The user permissions weren't applied yet")
        print()
        print("Continuing anyway - the database should still work.")
        print("If you experience connection issues later, you can:")
        print("  1. Run this script again manually: python setup_wizard.py")
        print("  2. Check MySQL logs for authentication errors")
        print("  3. Verify the bot user was created: mysql -u root -p")
        print("     Then run: SELECT user, host FROM mysql.user WHERE user='sulfur_bot_user';")
        print()
    
    print_header("✅ SETUP COMPLETED!")
    
    print("Database setup complete!")
    print()
    print("Configuration:")
    print(f"  Database: {DB_NAME}")
    print(f"  User: {DB_USER}")  
    print(f"  Password: {'(set)' if DB_PASS else '(empty)'}")
    print(f"  Host: {DB_HOST}")
    print()
    print("Next steps:")
    print("  1. python apply_migration.py    (creates tables)")
    print("  2. python check_status.py       (verify everything)")
    print("  3. python bot.py                (start the bot)")
    print()
    
except mysql.connector.Error as err:
    print(f"\n❌ MySQL Error: {err.errno} - {err.msg}")
    print()
    print("Database setup failed. Please check the error message above.")
    print()
    
    if err.errno == 1045:
        print("💡 Error 1045: Access denied")
        print("   This usually means the root password is incorrect.")
        print("   Try again with the correct password.")
    elif err.errno == 1007:
        print("💡 Error 1007: Database already exists")
        print("   The database was already created. This is normal if you're")
        print("   running setup_wizard.py again.")
    elif err.errno == 1317:
        print("💡 Error 1317: Query execution was interrupted")
        print("   The MySQL server interrupted the query.")
        print("   This might happen if the server is shutting down.")
    else:
        print("For help:")
        print("  • Windows: See MYSQL_SETUP.md or MYSQL_PASSWORD_RESET.md")
        print("  • Linux:   Check MySQL logs: journalctl -u mysql -n 50")
        print("  • Termux:  Make sure MySQL is running: mysqld_safe &")
    
    print()
    print("You can try running this script again later.")
    sys.exit(1)

except Exception as e:
    print(f"\n❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
    print()
    print("An unexpected error occurred. Please check the details above.")
    sys.exit(1)
