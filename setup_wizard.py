"""
Interactive MySQL Setup Wizard for Sulfur Bot
Handles multiple scenarios and provides step-by-step guidance
"""

import sys
import os
from getpass import getpass

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

print_header("SULFUR BOT - MYSQL SETUP WIZARD")

print("This wizard will help you set up the MySQL database for Sulfur Bot.")
print()
print("Current requirements:")
print("  • Database: sulfur_bot")
print("  • User: sulfur_bot_user")
print("  • Password: (empty)")
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

try:
    cursor = root_conn.cursor()
    
    # Create database
    print("Creating database 'sulfur_bot'...", end=" ")
    cursor.execute("CREATE DATABASE IF NOT EXISTS sulfur_bot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    print("✅")
    
    # Drop old user
    print("Removing old user if exists...", end=" ")
    cursor.execute("DROP USER IF EXISTS 'sulfur_bot_user'@'localhost'")
    print("✅")
    
    # Create user
    print("Creating user 'sulfur_bot_user'...", end=" ")
    try:
        cursor.execute("CREATE USER 'sulfur_bot_user'@'localhost' IDENTIFIED BY ''")
        print("✅")
    except mysql.connector.Error as err:
        # Try alternative authentication methods
        if "plugin" in str(err).lower():
            print()
            print("  ⚠️  Authentication plugin issue, trying alternative method...")
            cursor.execute("CREATE USER 'sulfur_bot_user'@'localhost' IDENTIFIED WITH mysql_native_password BY ''")
            print("  ✅ User created with alternative method")
        else:
            raise
    
    # Grant privileges
    print("Granting privileges...", end=" ")
    cursor.execute("GRANT ALL PRIVILEGES ON sulfur_bot.* TO 'sulfur_bot_user'@'localhost'")
    cursor.execute("FLUSH PRIVILEGES")
    print("✅")
    
    cursor.close()
    root_conn.close()
    
    print_section("Step 3: Verifying Setup")
    
    # Test connection as bot user
    print("Testing bot user connection...", end=" ")
    try:
        test_conn = mysql.connector.connect(
            host='localhost',
            user='sulfur_bot_user',
            password='',
            database='sulfur_bot'
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
    print("  Database: sulfur_bot")
    print("  User: sulfur_bot_user")  
    print("  Password: (empty)")
    print("  Host: localhost")
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
