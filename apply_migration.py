#!/usr/bin/env python3
"""One-time migration applier for 002_medium_priority_features.sql"""
import os
import sys
import mysql.connector
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

host = os.environ.get('DB_HOST', 'localhost')
user = os.environ.get('DB_USER', 'sulfur_bot_user')
password = os.environ.get('DB_PASS', '')
database = os.environ.get('DB_NAME', 'sulfur_bot')

migration_file = Path('scripts/db_migrations/002_medium_priority_features.sql')

print(f'Applying migration: {migration_file}')
print(f'Target: {user}@{host}/{database}')

if not migration_file.exists():
    print('ERROR: Migration file not found!')
    sys.exit(1)

sql_content = migration_file.read_text(encoding='utf-8')

try:
    conn = mysql.connector.connect(
        host=host,
        user=user,
        password=password,
        database=database
    )
    conn.autocommit = True
    cursor = conn.cursor()
    
    # Split and execute each statement separately
    statements = [s.strip() for s in sql_content.split(';') if s.strip()]
    for statement in statements:
        cursor.execute(statement)
    
    cursor.close()
    conn.close()
    
    print('✓ Migration applied successfully!')
    sys.exit(0)
    
except mysql.connector.Error as err:
    print(f'✗ MySQL Error: {err}')
    sys.exit(1)
except Exception as e:
    print(f'✗ Unexpected error: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
