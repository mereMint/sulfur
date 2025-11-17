"""
Simple MySQL Database Setup for Sulfur Bot
Creates database and user directly using Python
"""

import mysql.connector
import sys
import os

print("=" * 60)
print("SULFUR BOT - MYSQL DATABASE SETUP")
print("=" * 60)
print()

# Get root password
print("Enter MySQL root password (press Enter if no password):")
root_password = input("> ").strip()

print()
print("Connecting to MySQL...")

try:
    # Connect as root
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password=root_password
    )
    
    print("✅ Connected to MySQL as root")
    
    cursor = conn.cursor()
    
    # Create database
    print("\n📦 Creating database 'sulfur_bot'...")
    cursor.execute("CREATE DATABASE IF NOT EXISTS sulfur_bot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    print("✅ Database created")
    
    # Drop old user if exists (to fix authentication issues)
    print("\n👤 Setting up user 'sulfur_bot_user'...")
    cursor.execute("DROP USER IF EXISTS 'sulfur_bot_user'@'localhost'")
    
    # Create user with no password (matching .env)
    cursor.execute("CREATE USER 'sulfur_bot_user'@'localhost' IDENTIFIED BY ''")
    print("✅ User created")
    
    # Grant privileges
    print("\n🔐 Granting privileges...")
    cursor.execute("GRANT ALL PRIVILEGES ON sulfur_bot.* TO 'sulfur_bot_user'@'localhost'")
    cursor.execute("FLUSH PRIVILEGES")
    print("✅ Privileges granted")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ SETUP COMPLETE!")
    print("=" * 60)
    print()
    print("Database: sulfur_bot")
    print("User: sulfur_bot_user")
    print("Password: (none)")
    print()
    print("Next steps:")
    print("  1. python apply_migration.py")
    print("  2. python check_status.py")
    print("  3. python bot.py")
    print()
    
except mysql.connector.Error as err:
    print(f"\n❌ MySQL Error: {err}")
    print()
    
    if err.errno == 1045:
        print("💡 Incorrect root password. Try again with the correct password.")
    elif err.errno == 2003:
        print("💡 Cannot connect to MySQL server.")
        print("   Check if MySQL is running: Get-Service MySQL84")
    else:
        print("💡 Check error message above for details")
    
    sys.exit(1)
    
except Exception as e:
    print(f"\n❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
