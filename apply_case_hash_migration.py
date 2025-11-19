#!/usr/bin/env python3
"""
Apply database migration to add case_hash column to detective_cases table.
This script safely adds the column if it doesn't exist.
"""

import mysql.connector
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def apply_case_hash_migration():
    """Apply the case_hash migration to the database."""
    try:
        # Connect to database
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'sulfur_bot_user'),
            password=os.getenv('DB_PASS', ''),
            database=os.getenv('DB_NAME', 'sulfur_bot'),
            charset='utf8mb4',
            collation='utf8mb4_unicode_ci'
        )
        
        cursor = connection.cursor()
        
        # Check if column exists
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'detective_cases' 
            AND COLUMN_NAME = 'case_hash'
        """)
        
        exists = cursor.fetchone()[0] > 0
        
        if exists:
            print("✓ case_hash column already exists in detective_cases table")
        else:
            print("Adding case_hash column to detective_cases table...")
            cursor.execute("""
                ALTER TABLE detective_cases 
                ADD COLUMN case_hash VARCHAR(64) UNIQUE COMMENT 'SHA256 hash for uniqueness checking',
                ADD INDEX idx_case_hash (case_hash)
            """)
            connection.commit()
            print("✓ Successfully added case_hash column to detective_cases table")
        
        cursor.close()
        connection.close()
        return True
        
    except mysql.connector.Error as err:
        print(f"✗ Database error: {err}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Detective Game Case Hash Migration")
    print("=" * 60)
    
    success = apply_case_hash_migration()
    
    if success:
        print("\n✓ Migration completed successfully")
    else:
        print("\n✗ Migration failed - please check errors above")
        exit(1)
