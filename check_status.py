"""
Sulfur Bot - System Status Check
Validates all components before testing
"""

import sys
import os
from pathlib import Path

print("=" * 60)
print("SULFUR BOT - SYSTEM STATUS CHECK")
print("=" * 60)
print()

status = {
    'modules': True,
    'config': True,
    'database': False,
    'migration': True
}

# Check 1: Module Files
print("📦 MODULE FILES")
print("-" * 60)
modules_to_check = [
    'modules/economy.py',
    'modules/shop.py',
    'modules/games.py',
    'modules/quests.py',
    'modules/db_helpers.py'
]

for module in modules_to_check:
    exists = Path(module).exists()
    status_icon = "✅" if exists else "❌"
    print(f"{status_icon} {module}")
    if not exists:
        status['modules'] = False

# Check module syntax
print("\n🔍 SYNTAX VALIDATION")
print("-" * 60)
for module in modules_to_check:
    if Path(module).exists():
        module_name = module.replace('/', '.').replace('\\', '.').replace('.py', '')
        try:
            __import__(module_name)
            print(f"✅ {module} - No syntax errors")
        except SyntaxError as e:
            print(f"❌ {module} - Syntax error: {e}")
            status['modules'] = False
        except Exception as e:
            print(f"⚠️  {module} - Import warning: {e}")

# Check 2: Configuration
print("\n⚙️  CONFIGURATION")
print("-" * 60)
import json
try:
    with open('config/config.json') as f:
        config = json.load(f)
    print("✅ config.json valid")
    
    economy = config.get('modules', {}).get('economy', {})
    print(f"✅ Economy configured: {economy.get('currency_name', 'Coins')}")
    print(f"✅ Quest types: {len(economy.get('quests', {}).get('quest_types', {}))}")
    print(f"✅ Shop items: {len(economy.get('shop', {}).get('color_roles', {}))} tiers")
    print(f"✅ Games: {len(economy.get('games', {}))}")
except Exception as e:
    print(f"❌ config.json error: {e}")
    status['config'] = False

# Check 3: Database Connection
print("\n🗄️  DATABASE")
print("-" * 60)
try:
    import mysql.connector
    from dotenv import load_dotenv
    load_dotenv()
    
    conn = mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'sulfur_bot_user'),
        password=os.getenv('DB_PASS', ''),
        database=os.getenv('DB_NAME', 'sulfur_bot')
    )
    print("✅ Database connection successful")
    
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES")
    tables = [t[0] for t in cursor.fetchall()]
    
    # Check for economy tables
    required_tables = [
        'user_economy', 'feature_unlocks', 'shop_purchases',
        'daily_quests', 'daily_quest_completions', 'monthly_milestones',
        'gambling_stats', 'transaction_history', 'color_roles'
    ]
    
    missing = [t for t in required_tables if t not in tables]
    
    if missing:
        print(f"⚠️  Missing tables ({len(missing)}):")
        for t in missing:
            print(f"   - {t}")
        print("💡 Run: python apply_migration.py")
        status['database'] = False
    else:
        print(f"✅ All economy tables exist ({len(required_tables)} tables)")
        status['database'] = True
    
    cursor.close()
    conn.close()
    
except mysql.connector.Error as e:
    print(f"❌ Database connection failed: {e}")
    print("💡 Run: setup_mysql_admin.ps1 (as Administrator)")
    status['database'] = False
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    status['database'] = False

# Check 4: Migration File
print("\n📄 MIGRATION FILE")
print("-" * 60)
migration_file = Path('scripts/db_migrations/003_economy_and_shop.sql')
if migration_file.exists():
    print(f"✅ {migration_file}")
    print(f"   Size: {migration_file.stat().st_size} bytes")
else:
    print(f"❌ {migration_file} not found")
    status['migration'] = False

# Check 5: Documentation
print("\n📚 DOCUMENTATION")
print("-" * 60)
docs = [
    'TESTING_GUIDE.md',
    'IMPLEMENTATION_SUMMARY.md',
    'MYSQL_SETUP.md'
]
for doc in docs:
    exists = Path(doc).exists()
    status_icon = "✅" if exists else "❌"
    print(f"{status_icon} {doc}")

# Summary
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)

all_ready = all(status.values())

if all_ready:
    print("✅ ALL SYSTEMS READY!")
    print("\nNext steps:")
    print("  1. Add slash commands to bot.py (see TESTING_GUIDE.md)")
    print("  2. python bot.py")
    print("  3. Test features in Discord")
else:
    print("⚠️  SOME ISSUES DETECTED")
    print("\nAction required:")
    
    if not status['database']:
        print("  🔧 Database: Run setup_mysql_admin.ps1 as Administrator")
        print("              Then run: python apply_migration.py")
    
    if not status['modules']:
        print("  🔧 Modules: Check syntax errors above")
    
    if not status['config']:
        print("  🔧 Config: Fix config.json errors")
    
    if not status['migration']:
        print("  🔧 Migration: Ensure migration file exists")

print("\n" + "=" * 60)
sys.exit(0 if all_ready else 1)
