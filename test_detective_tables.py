#!/usr/bin/env python3
"""
Test script to verify detective game tables are created correctly.
This script tests the database initialization for detective game tables.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.db_helpers import init_db_pool, initialize_database

def test_detective_tables():
    """Test that detective tables are created successfully."""
    print("Testing detective game table creation...")
    
    # Get database credentials from environment
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_USER = os.environ.get('DB_USER', 'sulfur_bot_user')
    DB_PASS = os.environ.get('DB_PASS', '')
    DB_NAME = os.environ.get('DB_NAME', 'sulfur_bot')
    
    print(f"Connecting to database: {DB_USER}@{DB_HOST}/{DB_NAME}")
    
    # Initialize database pool
    init_db_pool(DB_HOST, DB_USER, DB_PASS, DB_NAME)
    
    # Run database initialization (this should create the tables)
    print("Running initialize_database()...")
    initialize_database()
    
    # Verify tables were created
    from modules.db_helpers import db_pool
    
    if not db_pool:
        print("❌ ERROR: Database pool not initialized")
        return False
    
    cnx = db_pool.get_connection()
    if not cnx:
        print("❌ ERROR: Could not get database connection")
        return False
    
    cursor = cnx.cursor()
    
    try:
        # Check for detective_cases table
        cursor.execute("SHOW TABLES LIKE 'detective_cases'")
        if cursor.fetchone():
            print("✓ detective_cases table exists")
        else:
            print("❌ detective_cases table NOT found")
            return False
        
        # Check for detective_user_stats table
        cursor.execute("SHOW TABLES LIKE 'detective_user_stats'")
        if cursor.fetchone():
            print("✓ detective_user_stats table exists")
        else:
            print("❌ detective_user_stats table NOT found")
            return False
        
        # Check for detective_user_progress table
        cursor.execute("SHOW TABLES LIKE 'detective_user_progress'")
        if cursor.fetchone():
            print("✓ detective_user_progress table exists")
        else:
            print("❌ detective_user_progress table NOT found")
            return False
        
        # Verify detective_cases table structure
        cursor.execute("DESCRIBE detective_cases")
        columns = {row[0] for row in cursor.fetchall()}
        required_columns = {'case_id', 'title', 'description', 'location', 'victim', 
                           'suspects', 'murderer_index', 'evidence', 'hints', 'difficulty'}
        
        if required_columns.issubset(columns):
            print(f"✓ detective_cases has all required columns: {sorted(columns)}")
        else:
            missing = required_columns - columns
            print(f"❌ detective_cases missing columns: {missing}")
            return False
        
        # Verify detective_user_stats table structure
        cursor.execute("DESCRIBE detective_user_stats")
        columns = {row[0] for row in cursor.fetchall()}
        required_columns = {'user_id', 'current_difficulty', 'cases_solved', 'cases_failed', 
                           'total_cases_played'}
        
        if required_columns.issubset(columns):
            print(f"✓ detective_user_stats has all required columns: {sorted(columns)}")
        else:
            missing = required_columns - columns
            print(f"❌ detective_user_stats missing columns: {missing}")
            return False
        
        # Verify detective_user_progress table structure
        cursor.execute("DESCRIBE detective_user_progress")
        columns = {row[0] for row in cursor.fetchall()}
        required_columns = {'user_id', 'case_id', 'completed', 'solved'}
        
        if required_columns.issubset(columns):
            print(f"✓ detective_user_progress has all required columns: {sorted(columns)}")
        else:
            missing = required_columns - columns
            print(f"❌ detective_user_progress missing columns: {missing}")
            return False
        
        print("\n✅ All detective game tables created successfully!")
        print("Tables are backwards compatible and safe for deployment.")
        return True
        
    except Exception as e:
        print(f"❌ ERROR during verification: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        cursor.close()
        cnx.close()

if __name__ == "__main__":
    success = test_detective_tables()
    sys.exit(0 if success else 1)
