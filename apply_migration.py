#!/usr/bin/env python3
"""One-time migration applier for database schema updates"""
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

# Allow specifying migration file via command line
if len(sys.argv) > 1:
    migration_file = Path(sys.argv[1])
else:
    migration_file = Path('scripts/db_migrations/003_economy_and_shop.sql')

print(f'Applying migration: {migration_file}')
print(f'Target: {user}@{host}/{database}')

if not migration_file.exists():
    print(f'ERROR: Migration file not found: {migration_file}')
    sys.exit(1)

sql_content = migration_file.read_text(encoding='utf-8')

try:
    conn = mysql.connector.connect(
        host=host,
        user=user,
        password=password,
        database=database
    )
    conn.autocommit = False  # Use transactions for safety
    cursor = conn.cursor()
    
    # Split and execute each statement separately
    statements = [s.strip() for s in sql_content.split(';') if s.strip() and not s.strip().startswith('--')]
    
    print(f'Executing {len(statements)} SQL statements...')
    for i, statement in enumerate(statements, 1):
        try:
            cursor.execute(statement)
            print(f'  [{i}/{len(statements)}] ✓')
        except mysql.connector.Error as err:
            print(f'  [{i}/{len(statements)}] ✗ Error: {err}')
            if 'already exists' not in str(err).lower():
                raise
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print('✓ Migration applied successfully!')
    sys.exit(0)
    
except mysql.connector.Error as err:
    print(f'✗ MySQL Error: {err}')
    if conn:
        conn.rollback()
    sys.exit(1)
except Exception as e:
    print(f'✗ Unexpected error: {e}')
    if conn:
        conn.rollback()
    import traceback
    traceback.print_exc()
    sys.exit(1)
