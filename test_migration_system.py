#!/usr/bin/env python3
"""
Test script to verify the database migration system works correctly.
This script tests:
1. Migration tracking table creation
2. Detection of pending migrations
3. Application of migrations
4. Idempotency (re-running doesn't cause errors)
"""

import os
import sys
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.db_helpers import (
    init_db_pool,
    initialize_database,
    create_migrations_table,
    get_applied_migrations,
    apply_pending_migrations
)

def main():
    print("=" * 60)
    print("Database Migration System Test")
    print("=" * 60)
    
    # Load environment variables
    load_dotenv()
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_USER = os.environ.get('DB_USER', 'sulfur_bot_user')
    DB_PASS = os.environ.get('DB_PASS', '')
    DB_NAME = os.environ.get('DB_NAME', 'sulfur_bot')
    
    print(f"\n1. Connecting to database: {DB_USER}@{DB_HOST}/{DB_NAME}")
    init_db_pool(DB_HOST, DB_USER, DB_PASS, DB_NAME)
    
    print("\n2. Initializing base database tables...")
    initialize_database()
    print("   ✓ Base tables initialized")
    
    print("\n3. Creating migrations tracking table...")
    if create_migrations_table():
        print("   ✓ Migrations tracking table ready")
    else:
        print("   ✗ Failed to create migrations tracking table")
        return 1
    
    print("\n4. Checking applied migrations...")
    applied = get_applied_migrations()
    print(f"   Found {len(applied)} previously applied migrations:")
    if applied:
        for migration in sorted(applied):
            print(f"     - {migration}")
    else:
        print("     (none)")
    
    print("\n5. Applying pending migrations...")
    applied_count, errors = apply_pending_migrations()
    
    if errors:
        print(f"\n   ✗ Encountered {len(errors)} errors:")
        for error in errors:
            print(f"     - {error}")
        return 1
    
    if applied_count > 0:
        print(f"   ✓ Successfully applied {applied_count} new migrations")
    else:
        print("   ✓ No new migrations to apply (all up to date)")
    
    print("\n6. Testing idempotency (running again)...")
    applied_count2, errors2 = apply_pending_migrations()
    
    if errors2:
        print(f"   ✗ Idempotency test failed with {len(errors2)} errors:")
        for error in errors2:
            print(f"     - {error}")
        return 1
    
    if applied_count2 == 0:
        print("   ✓ Idempotency test passed (no migrations re-applied)")
    else:
        print(f"   ⚠ Warning: {applied_count2} migrations re-applied (should be 0)")
    
    print("\n7. Final check of applied migrations...")
    applied_final = get_applied_migrations()
    print(f"   Total migrations applied: {len(applied_final)}")
    for migration in sorted(applied_final):
        print(f"     - {migration}")
    
    print("\n" + "=" * 60)
    print("✓ Migration system test completed successfully!")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\n✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
