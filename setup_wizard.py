"""
Interactive MySQL Setup Wizard for Sulfur Bot
Handles multiple scenarios and provides step-by-step guidance

Supports custom database configuration via .env file or command line arguments.
"""

import sys
import os
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

# Try different scenarios
scenarios = [
    ("root with no password", "root", ""),
    ("root with password (will prompt)", "root", None),
]

connected = False
root_conn = None

for scenario_name, user, password in scenarios:
    if password is None:
        print(f"Trying: {scenario_name}")
        password = getpass(f"Enter MySQL root password: ")
    else:
        print(f"Trying: {scenario_name}...", end=" ")
    
    try:
        root_conn = mysql.connector.connect(
            host='localhost',
            user=user,
            password=password
        )
        print("✅ Connected!")
        connected = True
        break
    except mysql.connector.Error as err:
        if password == "":
            print("❌ Failed")
        else:
            print(f"❌ Failed: {err}")
        continue

if not connected:
    print_section("❌ Cannot Connect to MySQL")
    print()
    print("Possible issues:")
    print("  1. MySQL service not running")
    print("     Fix: Get-Service MySQL84")
    print("           Start-Service MySQL84")
    print()
    print("  2. Root password unknown")
    print("     Fix: See MYSQL_PASSWORD_RESET.md for reset instructions")
    print()
    print("  3. MySQL not installed properly")
    print("     Fix: Reinstall MySQL (see MYSQL_SETUP.md)")
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
        test_conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME
        )
        test_conn.close()
        print("✅")
    except mysql.connector.Error as err:
        print(f"❌ {err}")
        print()
        print("Setup completed but connection test failed.")
        print("You may need to adjust authentication settings.")
        sys.exit(1)
    
    print_header("✅ SETUP SUCCESSFUL!")
    
    print("Database is ready for use!")
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
    print("  3. Add slash commands to bot.py (see TESTING_GUIDE.md)")
    print("  4. python bot.py                (start the bot)")
    print()
    
except mysql.connector.Error as err:
    print(f"\n❌ MySQL Error: {err}")
    print()
    print("Setup failed. Please check the error message above.")
    print("For help, see MYSQL_SETUP.md or MYSQL_PASSWORD_RESET.md")
    sys.exit(1)

except Exception as e:
    print(f"\n❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
