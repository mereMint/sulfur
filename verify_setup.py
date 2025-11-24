#!/usr/bin/env python3
"""
Sulfur Bot - Setup Verification Script

This script verifies that the bot is properly set up and all required
database tables and data exist.

Run this after bot startup to verify everything is initialized correctly.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Add the parent directory to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

from modules import db_helpers
from modules.logger_utils import bot_logger as logger


async def verify_database_connection():
    """Verify database connection is working."""
    try:
        DB_HOST = os.environ.get("DB_HOST", "localhost")
        DB_USER = os.environ.get("DB_USER", "sulfur_bot_user")
        DB_PASS = os.environ.get("DB_PASS", "")
        DB_NAME = os.environ.get("DB_NAME", "sulfur_bot")
        
        print(f"[1/6] Testing database connection to {DB_HOST}:{DB_NAME}...")
        db_helpers.init_db_pool(DB_HOST, DB_USER, DB_PASS, DB_NAME)
        
        if not db_helpers.db_pool:
            print("❌ FAILED: Database pool not initialized")
            return False
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            print("❌ FAILED: Could not get database connection")
            return False
        
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        conn.close()
        
        print("✅ PASSED: Database connection successful")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Database connection error: {e}")
        return False


async def verify_critical_tables():
    """Verify all critical database tables exist."""
    try:
        print("\n[2/6] Checking critical database tables...")
        
        conn = db_helpers.db_pool.get_connection()
        cursor = conn.cursor()
        
        # Critical tables that should exist
        critical_tables = [
            # Word Find
            'word_find_daily', 'word_find_attempts', 'word_find_stats', 'word_find_premium_games',
            # RPG
            'rpg_players', 'rpg_items', 'rpg_monsters', 'rpg_inventory', 'rpg_equipped', 'rpg_daily_shop',
            # Economy
            'user_stats', 'transaction_history',
            # AI
            'ai_model_usage',
            # Games
            'wordle_games', 'detective_user_stats'
        ]
        
        cursor.execute("SHOW TABLES")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        missing_tables = [t for t in critical_tables if t not in existing_tables]
        
        cursor.close()
        conn.close()
        
        if missing_tables:
            print(f"❌ FAILED: Missing {len(missing_tables)} critical tables:")
            for table in missing_tables:
                print(f"   - {table}")
            print("\n💡 Solution: Restart the bot to initialize missing tables")
            return False
        
        print(f"✅ PASSED: All {len(critical_tables)} critical tables exist")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Table verification error: {e}")
        return False


async def verify_rpg_data():
    """Verify RPG items and monsters are initialized."""
    try:
        print("\n[3/6] Checking RPG data initialization...")
        
        conn = db_helpers.db_pool.get_connection()
        cursor = conn.cursor()
        
        # Check items
        cursor.execute("SELECT COUNT(*) FROM rpg_items WHERE created_by IS NULL")
        item_count = cursor.fetchone()[0]
        
        # Check monsters
        cursor.execute("SELECT COUNT(*) FROM rpg_monsters")
        monster_count = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        issues = []
        
        if item_count < 100:
            issues.append(f"Only {item_count} default items (expected 100+)")
        
        if monster_count < 20:
            issues.append(f"Only {monster_count} monsters (expected 20+)")
        
        if issues:
            print(f"❌ FAILED: RPG data incomplete:")
            for issue in issues:
                print(f"   - {issue}")
            print("\n💡 Solution: Restart the bot to reinitialize RPG data")
            return False
        
        print(f"✅ PASSED: RPG data initialized ({item_count} items, {monster_count} monsters)")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: RPG data verification error: {e}")
        return False


async def verify_word_find_tables():
    """Verify Word Find tables have correct structure."""
    try:
        print("\n[4/6] Checking Word Find table structure...")
        
        conn = db_helpers.db_pool.get_connection()
        cursor = conn.cursor()
        
        # Verify word_find_attempts has the game_type column
        cursor.execute("SHOW COLUMNS FROM word_find_attempts LIKE 'game_type'")
        has_game_type = cursor.fetchone() is not None
        
        cursor.close()
        conn.close()
        
        if not has_game_type:
            print("❌ FAILED: word_find_attempts missing 'game_type' column")
            print("\n💡 Solution: Run database migration or restart bot")
            return False
        
        print("✅ PASSED: Word Find tables have correct structure")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Word Find table verification error: {e}")
        return False


async def verify_environment_variables():
    """Verify required environment variables are set."""
    try:
        print("\n[5/6] Checking environment variables...")
        
        required_vars = {
            'DISCORD_BOT_TOKEN': 'Discord bot token',
            'DB_HOST': 'Database host',
            'DB_USER': 'Database user',
            'DB_PASS': 'Database password',
            'DB_NAME': 'Database name',
        }
        
        optional_vars = {
            'GEMINI_API_KEY': 'Gemini API key (for AI features)',
            'OPENAI_API_KEY': 'OpenAI API key (optional)',
        }
        
        missing = []
        for var, desc in required_vars.items():
            if var not in os.environ:
                missing.append(f"{var} ({desc})")
        
        if missing:
            print("❌ FAILED: Missing required environment variables:")
            for var in missing:
                print(f"   - {var}")
            print("\n💡 Solution: Set these in your .env file")
            return False
        
        # Check optional
        optional_missing = []
        for var, desc in optional_vars.items():
            if var not in os.environ:
                optional_missing.append(f"{var} ({desc})")
        
        if optional_missing:
            print("⚠️  WARNING: Missing optional environment variables:")
            for var in optional_missing:
                print(f"   - {var}")
        
        print("✅ PASSED: All required environment variables are set")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Environment variable check error: {e}")
        return False


async def verify_file_structure():
    """Verify required files and directories exist."""
    try:
        print("\n[6/6] Checking file structure...")
        
        required_items = {
            'directories': ['config', 'modules', 'web', 'logs'],
            'files': ['bot.py', 'web_dashboard.py', 'config/config.json']
        }
        
        missing = []
        
        for directory in required_items['directories']:
            if not os.path.isdir(directory):
                missing.append(f"Directory: {directory}")
        
        for file in required_items['files']:
            if not os.path.isfile(file):
                missing.append(f"File: {file}")
        
        if missing:
            print("❌ FAILED: Missing required files/directories:")
            for item in missing:
                print(f"   - {item}")
            return False
        
        print("✅ PASSED: All required files and directories exist")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: File structure check error: {e}")
        return False


async def main():
    """Run all verification checks."""
    print("=" * 60)
    print("Sulfur Bot - Setup Verification")
    print("=" * 60)
    
    results = []
    
    # Run checks
    results.append(await verify_environment_variables())
    results.append(await verify_file_structure())
    results.append(await verify_database_connection())
    results.append(await verify_critical_tables())
    results.append(await verify_word_find_tables())
    results.append(await verify_rpg_data())
    
    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ ALL CHECKS PASSED ({passed}/{total})")
        print("\nYour bot is properly configured and ready to run!")
        print("\nNext steps:")
        print("  1. Start the bot: python bot.py")
        print("  2. Start the web dashboard: python web_dashboard.py")
        print("  3. Access dashboard at: http://localhost:5000")
        return 0
    else:
        print(f"❌ SOME CHECKS FAILED ({passed}/{total} passed)")
        print("\nPlease fix the issues above before running the bot.")
        print("\nCommon solutions:")
        print("  - Restart the bot to reinitialize data")
        print("  - Check your .env file for missing variables")
        print("  - Verify MySQL/MariaDB is running")
        return 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
