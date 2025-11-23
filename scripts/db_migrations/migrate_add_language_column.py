#!/usr/bin/env python3
"""
Migration script to add language column to user_customization table if it doesn't exist.
This fixes the error: Unknown column 'language' in 'SELECT'
"""

import mysql.connector
import os
import sys
from dotenv import load_dotenv

def main():
    # Load environment variables
    load_dotenv()
    
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_USER = os.getenv('DB_USER', 'sulfur_bot_user')
    DB_PASS = os.getenv('DB_PASS', '')
    DB_NAME = os.getenv('DB_NAME', 'sulfur_bot')
    
    print(f"Connecting to database {DB_NAME} on {DB_HOST}...")
    
    try:
        # Connect to database
        cnx = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME
        )
        cursor = cnx.cursor()
        
        # Check if user_customization table exists
        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.tables 
            WHERE table_schema = %s
            AND table_name = 'user_customization'
        """, (DB_NAME,))
        
        table_exists = cursor.fetchone()[0] > 0
        
        if not table_exists:
            print("Table user_customization does not exist. Creating it...")
            cursor.execute("""
                CREATE TABLE user_customization (
                    user_id BIGINT PRIMARY KEY,
                    equipped_color VARCHAR(7),
                    embed_color VARCHAR(7),
                    profile_background VARCHAR(255),
                    language VARCHAR(2) DEFAULT 'de',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            cnx.commit()
            print("✓ Table user_customization created successfully")
        else:
            # Check if language column exists
            cursor.execute("""
                SELECT COUNT(*)
                FROM information_schema.columns 
                WHERE table_schema = %s
                AND table_name = 'user_customization'
                AND column_name = 'language'
            """, (DB_NAME,))
            
            column_exists = cursor.fetchone()[0] > 0
            
            if column_exists:
                print("✓ Column 'language' already exists in user_customization table")
            else:
                print("Column 'language' missing. Adding it now...")
                cursor.execute("""
                    ALTER TABLE user_customization 
                    ADD COLUMN language VARCHAR(2) DEFAULT 'de' 
                    AFTER profile_background
                """)
                cnx.commit()
                print("✓ Column 'language' added successfully to user_customization table")
        
        cursor.close()
        cnx.close()
        print("\n✓ Migration completed successfully")
        return 0
        
    except mysql.connector.Error as err:
        print(f"✗ Database error: {err}")
        return 1
    except Exception as e:
        print(f"✗ Error: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
