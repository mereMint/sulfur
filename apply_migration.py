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

# Strip quotes from password if present
if password:
    password = password.strip('"').strip("'")
if not password:
    password = ''

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
    
    # Execute statements one by one
    statements = []
    current_statement = []
    
    for line in sql_content.split('\n'):
        line = line.strip()
        # Skip comments and empty lines
        if not line or line.startswith('--'):
            continue
        current_statement.append(line)
        if line.endswith(';'):
            stmt = ' '.join(current_statement)
            if stmt.strip(';').strip():
                statements.append(stmt)
            current_statement = []
    
    print(f'Executing {len(statements)} SQL statements...')
    for i, statement in enumerate(statements, 1):
        try:
            cursor.execute(statement)
            # Get first few words for display
            preview = ' '.join(statement.split()[:3])
            print(f'  [{i}/{len(statements)}] ✓ {preview}...')
        except mysql.connector.Error as err:
            preview = ' '.join(statement.split()[:3])
            if 'already exists' in str(err).lower() or 'duplicate' in str(err).lower():
                print(f'  [{i}/{len(statements)}] ⚠ {preview}... (already exists, skipping)')
            else:
                print(f'  [{i}/{len(statements)}] ✗ {preview}... Error: {err}')
                raise
    
    conn.commit()
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
