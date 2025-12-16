"""
Database Setup Wizard for Sulfur Bot

This script is a wrapper around the secure database setup script.
It provides a simple interface for setting up the database with strong security.

For advanced users, you can directly run:
    bash scripts/setup_database_secure.sh
"""

import sys
import os
import subprocess
from pathlib import Path

def print_header(text):
    print("\n" + "=" * 60)
    print(text.center(60))
    print("=" * 60 + "\n")

def print_error(text):
    print(f"❌ ERROR: {text}")

def print_success(text):
    print(f"✅ {text}")

def print_info(text):
    print(f"ℹ️  {text}")

print_header("SULFUR BOT - DATABASE SETUP WIZARD")

print("This wizard will set up your database with:")
print("  • Cryptographically secure passwords (48+ characters)")
print("  • Proper security hardening")
print("  • Automatic user and database creation")
print("  • Secure configuration storage")
print()

# Check if we're in the project root
if not os.path.exists('bot.py'):
    print_error("This script must be run from the project root directory")
    print_info("Please cd to the project directory and run again")
    sys.exit(1)

# Check if database is already configured
if os.path.exists('config/database.json'):
    print_info("Database configuration already exists: config/database.json")
    response = input("\nReconfigure database? (y/N): ").strip().lower()
    if response != 'y':
        print_info("Keeping existing configuration")
        sys.exit(0)
    
    print_info("Removing old configuration...")
    os.remove('config/database.json')

# Run the secure setup script
print()
print_info("Starting secure database setup...")
print()

secure_setup_script = Path('scripts/setup_database_secure.sh')

if not secure_setup_script.exists():
    print_error("Secure setup script not found: scripts/setup_database_secure.sh")
    print_info("The script may have been moved or deleted")
    sys.exit(1)

try:
    # Run the secure setup script
    result = subprocess.run(
        ['bash', str(secure_setup_script)],
        cwd=os.getcwd()
    )
    
    if result.returncode == 0:
        print()
        print_success("Database setup complete!")
        print()
        print_info("Next steps:")
        print("  1. Run migrations: python apply_migration.py --all")
        print("  2. Start the bot:  python bot.py")
        print()
        sys.exit(0)
    else:
        print()
        print_error("Database setup failed")
        print_info("Check the error messages above for details")
        sys.exit(1)

except FileNotFoundError:
    print_error("bash command not found")
    print_info("This script requires bash to run")
    print_info("On Windows, use Git Bash or WSL")
    sys.exit(1)
except KeyboardInterrupt:
    print()
    print_info("Setup cancelled by user")
    sys.exit(1)
except Exception as e:
    print_error(f"Unexpected error: {e}")
    sys.exit(1)
