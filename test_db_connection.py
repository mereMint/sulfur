import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

try:
    conn = mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'sulfur_bot_user'),
        password=os.getenv('DB_PASS', ''),
        database=os.getenv('DB_NAME', 'sulfur_bot')
    )
    
    print("✅ Database connection successful!")
    
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    
    print(f"\n📊 Found {len(tables)} tables:")
    for table in tables:
        print(f"  - {table[0]}")
    
    # Check for new economy tables
    table_names = [t[0] for t in tables]
    new_tables = [
        'user_economy', 'feature_unlocks', 'shop_purchases', 
        'daily_quests', 'daily_quest_completions', 'monthly_milestones',
        'gambling_stats', 'transaction_history', 'color_roles', 'chat_bounties'
    ]
    
    missing_tables = [t for t in new_tables if t not in table_names]
    
    if missing_tables:
        print(f"\n⚠️  Missing economy tables (need migration):")
        for table in missing_tables:
            print(f"  - {table}")
        print("\n💡 Run: python apply_migration.py")
    else:
        print("\n✅ All economy tables exist! Ready to test.")
    
    cursor.close()
    conn.close()
    
except mysql.connector.Error as err:
    print(f"❌ Database connection failed: {err}")
    print("\n📝 Possible solutions:")
    print("  1. Check if MySQL service is running: Get-Service MySQL84")
    print("  2. Verify .env credentials match MySQL user")
    print("  3. Create database and user (see MYSQL_SETUP.md)")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
