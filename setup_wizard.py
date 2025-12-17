"""
Database Setup Wizard for Sulfur Bot

This wizard provides multiple methods for setting up the database:
1. Automated Python Setup (Recommended) - Fully automated, cross-platform
2. Secure Bash Setup - For Linux/Termux with advanced security options

For advanced users, you can directly run:
    python scripts/setup_database_auto.py
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

def print_step(text):
    print(f"▶️  {text}")

print_header("SULFUR BOT - DATABASE SETUP WIZARD")

print("This wizard will set up your database with:")
print("  • Cryptographically secure passwords (48+ characters)")
print("  • Proper security hardening")
print("  • Automatic user and database creation")
print("  • Automatic migration execution")
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

# Choose setup method
print()
print_header("SETUP METHOD SELECTION")
print("Choose your preferred database setup method:")
print()
print("1. Automated Python Setup (RECOMMENDED)")
print("   • Fully automated, cross-platform")
print("   • Auto-detects MySQL/MariaDB configuration")
print("   • Starts database server if needed")
print("   • Works on Windows, Linux, and Termux")
print("   • Runs all migrations automatically")
print()
print("2. Secure Bash Setup")
print("   • Requires bash shell (Linux/Termux/WSL)")
print("   • Advanced security configuration options")
print("   • Manual migration execution required")
print()

choice = input("Enter your choice (1 or 2, default: 1): ").strip()
if not choice:
    choice = "1"

if choice == "1":
    # Run automated Python setup
    print()
    print_step("Starting automated Python setup...")
    print()
    
    auto_setup_script = Path('scripts/setup_database_auto.py')
    
    if not auto_setup_script.exists():
        print_error("Automated setup script not found: scripts/setup_database_auto.py")
        print_info("The script may have been moved or deleted")
        sys.exit(1)
    
    try:
        # Run the automated setup script
        result = subprocess.run(
            [sys.executable, str(auto_setup_script)],
            cwd=os.getcwd()
        )
        
        if result.returncode == 0:
            print()
            print_success("Database setup complete!")
            print()
            print_info("Next steps:")
            print("  1. Start the bot:  python bot.py")
            print("  2. Access dashboard: http://localhost:5000")
            print()
            sys.exit(0)
        else:
            print()
            print_error("Database setup failed")
            print_info("Check the error messages above for details")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print()
        print_info("Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)

elif choice == "2":
    # Run secure bash setup
    print()
    print_step("Starting secure bash setup...")
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
        print_info("On Windows, use Git Bash or WSL, or choose option 1 (Automated Python Setup)")
        sys.exit(1)
    except KeyboardInterrupt:
        print()
        print_info("Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)

else:
    print_error("Invalid choice. Please enter 1 or 2.")
    sys.exit(1)
