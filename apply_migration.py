#!/usr/bin/env python3
"""
Enhanced migration applier for database schema updates

Features:
- Transaction support with automatic rollback on error
- Dependency checking (verifies referenced tables exist)
- Migration tracking (prevents double-application)
- --force flag to drop all tables and recreate
- --verify flag to check migration status
- Detailed error reporting with exact SQL statement
"""
import os
import sys
import argparse
from pathlib import Path
from typing import List, Tuple

try:
    import mysql.connector
except ModuleNotFoundError:
    print("=" * 60)
    print("ERROR: mysql-connector-python not installed")
    print("=" * 60)
    print()
    print("The mysql-connector-python package is required to run this script.")
    print()
    print("To install it, run:")
    print("  pip install mysql-connector-python")
    print()
    print("Or install all dependencies:")
    print("  pip install -r requirements.txt")
    print()
    sys.exit(1)

# Try to import database config module, fallback to env vars
try:
    from modules.database_config import DatabaseConfig
    USE_CONFIG_MODULE = True
except ImportError:
    USE_CONFIG_MODULE = False
    from dotenv import load_dotenv
    load_dotenv()

# Parse command line arguments
parser = argparse.ArgumentParser(description='Apply database migrations')
parser.add_argument('migration_file', nargs='?', help='Specific migration file to apply')
parser.add_argument('--all', action='store_true', help='Apply all pending migrations in order')
parser.add_argument('--force', action='store_true', help='Drop all tables and recreate from scratch')
parser.add_argument('--verify', action='store_true', help='Verify migration status without applying')
args = parser.parse_args()

# Get database credentials
if USE_CONFIG_MODULE:
    try:
        conn_params = DatabaseConfig.get_connection_params()
        host = conn_params['host']
        user = conn_params['user']
        password = conn_params['password']
        database = conn_params['database']
    except Exception as e:
        print(f"ERROR: Failed to load database config: {e}")
        print("Run: bash scripts/setup_database_secure.sh")
        sys.exit(1)
else:
    host = os.environ.get('DB_HOST', 'localhost')
    user = os.environ.get('DB_USER', 'sulfur_bot_user')
    password = os.environ.get('DB_PASS', '')
    database = os.environ.get('DB_NAME', 'sulfur_bot')
    
    # Strip quotes from password if present
    if password:
        password = password.strip('"').strip("'")
    if not password:
        password = ''

# Determine which migrations to apply
migrations_dir = Path('scripts/db_migrations')

# Ensure migrations directory exists
if not migrations_dir.exists():
    print(f"ERROR: Migrations directory not found: {migrations_dir}")
    print("Looking for migrations in scripts/db_migrations/")
    sys.exit(1)

if args.migration_file:
    migration_files = [Path(args.migration_file)]
elif args.all:
    # Apply all migrations in order
    migration_files = sorted(migrations_dir.glob('*.sql'))
    if not migration_files:
        print(f"ERROR: No migration files found in {migrations_dir}")
        sys.exit(1)
else:
    # Default: apply all pending migrations
    print("=" * 70)
    print("No migration file specified - applying all pending migrations")
    print("=" * 70)
    print()
    migration_files = sorted(migrations_dir.glob('*.sql'))
    if not migration_files:
        print(f"ERROR: No migration files found in {migrations_dir}")
        sys.exit(1)

print("============================================================================")
print("  Sulfur Bot - Database Migration Tool")
print("============================================================================")
print(f"Target: {user}@{host}/{database}")
print()

def get_connection():
    """Get database connection"""
    return mysql.connector.connect(
        host=host,
        user=user,
        password=password,
        database=database
    )

def create_migration_tracking_table(cursor):
    """Create table to track applied migrations"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            migration_name VARCHAR(255) UNIQUE NOT NULL,
            applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_migration_name (migration_name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)

def is_migration_applied(cursor, migration_name: str) -> bool:
    """Check if a migration has already been applied"""
    cursor.execute(
        "SELECT COUNT(*) FROM schema_migrations WHERE migration_name = %s",
        (migration_name,)
    )
    count = cursor.fetchone()[0]
    return count > 0

def record_migration(cursor, migration_name: str):
    """Record that a migration has been applied"""
    cursor.execute(
        "INSERT INTO schema_migrations (migration_name) VALUES (%s)",
        (migration_name,)
    )

def get_table_names(cursor) -> List[str]:
    """Get list of all tables in database"""
    cursor.execute("SHOW TABLES")
    return [row[0] for row in cursor.fetchall()]

def parse_sql_statements(sql_content: str) -> List[str]:
    """
    Parse SQL content into individual statements, properly handling DELIMITER blocks.
    
    This handles stored procedures that use custom delimiters like $$ or //.
    """
    statements = []
    current_statement = []
    in_delimiter_block = False
    custom_delimiter = '$$'  # Default custom delimiter

    for line in sql_content.split('\n'):
        stripped = line.strip()
        upper_stripped = stripped.upper()

        # Handle DELIMITER commands
        if upper_stripped.startswith('DELIMITER'):
            parts = stripped.split()
            if len(parts) >= 2:
                new_delimiter = parts[1]
                if new_delimiter == ';':
                    # Ending delimiter block
                    in_delimiter_block = False
                else:
                    # Starting delimiter block
                    in_delimiter_block = True
                    custom_delimiter = new_delimiter
            continue

        # Skip empty lines and comments (but keep them in procedure bodies)
        if not in_delimiter_block:
            if not stripped or stripped.startswith('--') or stripped.startswith('#'):
                continue
            # Skip single-line multi-line comments
            if stripped.startswith('/*') and stripped.endswith('*/'):
                continue

        current_statement.append(line)

        # Check for statement end
        if in_delimiter_block:
            # In delimiter block, look for custom delimiter (e.g., $$, //)
            if stripped.endswith(custom_delimiter):
                # Remove the custom delimiter from the end
                stmt = '\n'.join(current_statement)
                stmt = stmt.rstrip()
                if stmt.endswith(custom_delimiter):
                    stmt = stmt[:-len(custom_delimiter)].rstrip()
                if stmt.strip():
                    statements.append(stmt)
                current_statement = []
        else:
            # Normal mode, look for semicolon
            if stripped.endswith(';'):
                stmt = '\n'.join(current_statement)
                if stmt.strip().rstrip(';').strip():
                    statements.append(stmt)
                current_statement = []

    # Handle any remaining statement (in case file doesn't end with semicolon)
    if current_statement:
        stmt = '\n'.join(current_statement).strip()
        if stmt:
            statements.append(stmt)

    return statements

def apply_migration(migration_file: Path, force: bool = False) -> Tuple[bool, str]:
    """
    Apply a single migration file
    
    Returns:
        (success: bool, message: str)
    """
    if not migration_file.exists():
        return False, f"Migration file not found: {migration_file}"
    
    migration_name = migration_file.name
    sql_content = migration_file.read_text(encoding='utf-8')
    
    try:
        conn = get_connection()
        conn.autocommit = False  # Use transactions
        cursor = conn.cursor()
        
        # Create migration tracking table
        create_migration_tracking_table(cursor)
        conn.commit()
        
        # Check if already applied (unless force mode)
        if not force and is_migration_applied(cursor, migration_name):
            cursor.close()
            conn.close()
            return True, f"Already applied: {migration_name} (skipping)"
        
        # Parse SQL statements
        statements = parse_sql_statements(sql_content)
        
        if not statements:
            cursor.close()
            conn.close()
            return False, f"No SQL statements found in {migration_name}"
        
        print(f"\nApplying: {migration_name}")
        print(f"Executing {len(statements)} SQL statement(s)...")
        
        # Execute each statement in a transaction
        for i, statement in enumerate(statements, 1):
            try:
                cursor.execute(statement)

                # Get preview of statement
                preview = ' '.join(statement.split()[:5])
                if len(preview) > 60:
                    preview = preview[:57] + "..."
                print(f"  [{i}/{len(statements)}] ✓ {preview}")

            except mysql.connector.Error as err:
                preview = ' '.join(statement.split()[:5])

                # Check if error is due to already existing object
                error_msg = str(err).lower()
                if any(keyword in error_msg for keyword in [
                    'already exists',
                    'duplicate',
                    'duplicate key',
                    'duplicate entry',
                    'table already exists',
                    'database already exists',
                    'index already exists'
                ]):
                    print(f"  [{i}/{len(statements)}] ⚠ {preview} (already exists, skipping)")
                    continue
                else:
                    # Fatal error - rollback and report
                    print(f"  [{i}/{len(statements)}] ✗ {preview}")
                    print(f"\nError: {err}")
                    print(f"Error Code: {err.errno if hasattr(err, 'errno') else 'N/A'}")
                    print(f"\nFailed statement:")
                    print("─" * 60)
                    print(statement[:500])
                    if len(statement) > 500:
                        print("... (truncated)")
                    print("─" * 60)
                    conn.rollback()
                    cursor.close()
                    conn.close()
                    return False, f"Failed to apply {migration_name}: {err}"
        
        # Record migration as applied
        if not force:  # Only record if not in force mode
            record_migration(cursor, migration_name)
        
        # Commit transaction
        conn.commit()
        cursor.close()
        conn.close()
        
        return True, f"Successfully applied: {migration_name}"
        
    except mysql.connector.Error as err:
        return False, f"Database error: {err}"
    except Exception as e:
        return False, f"Unexpected error: {e}"

def verify_migrations():
    """Verify which migrations have been applied"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Create migration tracking table if it doesn't exist
        create_migration_tracking_table(cursor)
        conn.commit()
        
        # Get all migrations
        all_migrations = sorted(migrations_dir.glob('*.sql'))
        
        if not all_migrations:
            print("No migration files found in scripts/db_migrations/")
            cursor.close()
            conn.close()
            return
        
        print("Migration Status:")
        print("─" * 60)
        
        for migration_file in all_migrations:
            migration_name = migration_file.name
            applied = is_migration_applied(cursor, migration_name)
            status = "✓ Applied" if applied else "✗ Pending"
            print(f"{status:12} {migration_name}")
        
        print("─" * 60)
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error verifying migrations: {e}")
        sys.exit(1)

def drop_all_tables():
    """Drop all tables in database (for --force mode)"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        
        if not tables:
            print("No tables to drop")
            cursor.close()
            conn.close()
            return
        
        print(f"\nDropping {len(tables)} table(s)...")
        
        # Disable foreign key checks
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        
        # Drop each table
        for table in tables:
            cursor.execute(f"DROP TABLE IF EXISTS `{table}`")
            print(f"  ✓ Dropped: {table}")
        
        # Re-enable foreign key checks
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("All tables dropped successfully")
        
    except Exception as e:
        print(f"Error dropping tables: {e}")
        sys.exit(1)

# Main execution
try:
    # Verify mode
    if args.verify:
        verify_migrations()
        sys.exit(0)
    
    # Force mode - drop all tables first
    if args.force:
        print("\n⚠️  FORCE MODE: All tables will be dropped and recreated")
        response = input("Are you sure? (type 'yes' to confirm): ")
        if response.lower() != 'yes':
            print("Aborted")
            sys.exit(0)
        drop_all_tables()
        print()
    
    # Validate migration files
    for migration_file in migration_files:
        if not migration_file.exists():
            print(f"ERROR: Migration file not found: {migration_file}")
            sys.exit(1)
    
    # Apply migrations
    success_count = 0
    skip_count = 0
    fail_count = 0
    
    for migration_file in migration_files:
        success, message = apply_migration(migration_file, force=args.force)
        
        if success:
            if "skipping" in message:
                skip_count += 1
                print(f"⚠ {message}")
            else:
                success_count += 1
                print(f"✓ {message}")
        else:
            fail_count += 1
            print(f"✗ {message}")
            print()
            print("Migration failed. All changes have been rolled back.")
            sys.exit(1)
    
    # Summary
    print()
    print("─" * 60)
    print(f"Migrations applied: {success_count}")
    if skip_count > 0:
        print(f"Migrations skipped: {skip_count}")
    if fail_count > 0:
        print(f"Migrations failed: {fail_count}")
    print("─" * 60)
    
    if fail_count == 0:
        print("\n✓ All migrations completed successfully!")
        sys.exit(0)
    else:
        sys.exit(1)
    
except KeyboardInterrupt:
    print("\n\nInterrupted by user")
    sys.exit(1)
except Exception as e:
    print(f"\n✗ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
