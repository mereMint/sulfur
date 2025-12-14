-- Migration: Fix mines_games table schema - add revealed_count column
-- 
-- Issue: The mines_games table was created by migration 010 with a column named
-- 'tiles_revealed', but the code (db_helpers.log_mines_game) expects a column
-- named 'revealed_count'. This causes MySQL error 1054 (Unknown column).
--
-- Solution: Add the revealed_count column if it doesn't exist, and copy data
-- from tiles_revealed if that column exists.

-- Step 1: Check if revealed_count column exists, if not, add it
-- Using a procedure to handle conditional DDL

DELIMITER $$

-- Drop procedure if exists to make migration idempotent
DROP PROCEDURE IF EXISTS add_revealed_count_to_mines_games$$

CREATE PROCEDURE add_revealed_count_to_mines_games()
BEGIN
    DECLARE column_exists INT DEFAULT 0;
    DECLARE tiles_revealed_exists INT DEFAULT 0;
    
    -- Check if revealed_count already exists
    SELECT COUNT(*) INTO column_exists
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'mines_games'
      AND COLUMN_NAME = 'revealed_count';
    
    -- Check if tiles_revealed exists (old column name from migration 010)
    SELECT COUNT(*) INTO tiles_revealed_exists
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'mines_games'
      AND COLUMN_NAME = 'tiles_revealed';
    
    -- If revealed_count doesn't exist, add it
    IF column_exists = 0 THEN
        ALTER TABLE mines_games ADD COLUMN revealed_count INT NOT NULL DEFAULT 0 AFTER mine_count;
    END IF;
    
    -- If tiles_revealed exists, copy data to revealed_count and drop old column
    -- This handles both cases: new column just added OR column already existed
    IF tiles_revealed_exists = 1 THEN
        -- Copy data from old column to new column
        -- Uses COALESCE to handle any potential NULL values gracefully
        UPDATE mines_games SET revealed_count = COALESCE(tiles_revealed, 0);
        
        -- Drop the old column after data is copied
        ALTER TABLE mines_games DROP COLUMN tiles_revealed;
    END IF;
END$$

DELIMITER ;

-- Execute the procedure
CALL add_revealed_count_to_mines_games();

-- Clean up
DROP PROCEDURE IF EXISTS add_revealed_count_to_mines_games;

-- ============================================================================
-- End of Migration
-- ============================================================================
