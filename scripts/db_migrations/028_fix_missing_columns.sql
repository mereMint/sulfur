-- ============================================================================
-- Migration 028: Fix Missing Database Columns
-- ============================================================================
-- This migration fixes the remaining database schema issues:
-- 1. Adds 'category' column to stocks table (code uses 'category' but table has 'sector')
-- 2. Adds 'game_mines' table (referenced in dashboard but missing)
-- 3. Fixes cleanup script errors with last_bot_message_at
-- ============================================================================

DELIMITER $$

-- Create helper procedure to add columns if they don't exist
DROP PROCEDURE IF EXISTS add_column_if_not_exists_028$$
CREATE PROCEDURE add_column_if_not_exists_028(
    IN p_table_name VARCHAR(64),
    IN p_column_name VARCHAR(64),
    IN p_column_definition VARCHAR(500)
)
BEGIN
    DECLARE table_exists INT DEFAULT 0;
    DECLARE column_exists INT DEFAULT 0;

    -- Check if table exists
    SELECT COUNT(*) INTO table_exists
    FROM information_schema.tables
    WHERE table_schema = DATABASE() AND table_name = p_table_name;

    IF table_exists > 0 THEN
        -- Check if column exists
        SELECT COUNT(*) INTO column_exists
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = p_table_name
          AND column_name = p_column_name;

        IF column_exists = 0 THEN
            SET @sql = CONCAT('ALTER TABLE `', p_table_name, '` ADD COLUMN `', p_column_name, '` ', p_column_definition);
            PREPARE stmt FROM @sql;
            EXECUTE stmt;
            DEALLOCATE PREPARE stmt;
        END IF;
    END IF;
END$$

DELIMITER ;

-- ============================================================================
-- PART 1: Fix stocks Table - Add 'category' Column
-- ============================================================================
-- The code uses 'category' but migration 019 created the table with 'sector'.
-- We'll add 'category' and sync it with 'sector' for backward compatibility.

CALL add_column_if_not_exists_028('stocks', 'category', 'VARCHAR(20) DEFAULT NULL');

-- Add index on category for better query performance
-- Use dynamic SQL to avoid errors if index already exists
SET @create_idx_category = IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS 
     WHERE TABLE_SCHEMA = DATABASE() 
       AND TABLE_NAME = 'stocks' 
       AND INDEX_NAME = 'idx_stocks_category') = 0,
    'CREATE INDEX idx_stocks_category ON stocks(category)',
    'SELECT "Index idx_stocks_category already exists" AS message'
);
PREPARE stmt FROM @create_idx_category;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Sync category from sector if category is NULL
UPDATE stocks
SET category = sector
WHERE category IS NULL;

-- ============================================================================
-- PART 2: Add Additional Stock Columns
-- ============================================================================
-- Add columns that are referenced by the code but may be missing

CALL add_column_if_not_exists_028('stocks', 'volume_today', 'INT DEFAULT 0');
CALL add_column_if_not_exists_028('stocks', 'last_update', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP');
CALL add_column_if_not_exists_028('stocks', 'game_influence_factor', 'DECIMAL(6, 5) DEFAULT 0.00000');

-- ============================================================================
-- PART 3: Create game_mines Table Alias
-- ============================================================================
-- The dashboard queries reference both 'mines_games' and 'game_mines'.
-- Create a view for backward compatibility.

-- Drop the view if it exists first
DROP VIEW IF EXISTS game_mines;

-- Create the view
CREATE VIEW game_mines AS
SELECT
    id,
    user_id,
    bet_amount,
    mine_count,
    revealed_count,
    result,
    multiplier,
    payout,
    won,
    played_at
FROM mines_games;

-- ============================================================================
-- PART 4: Ensure conversation_context Exists
-- ============================================================================
-- The cleanup script references the conversation_context table.
-- This should exist from migration 002, but we'll ensure it's there.

CREATE TABLE IF NOT EXISTS conversation_context (
    user_id BIGINT,
    channel_id BIGINT,
    last_bot_message_at TIMESTAMP,
    last_user_message TEXT,
    last_bot_response TEXT,
    context_data JSON,
    PRIMARY KEY (user_id, channel_id),
    INDEX idx_last_message (last_bot_message_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Cleanup
-- ============================================================================
DROP PROCEDURE IF EXISTS add_column_if_not_exists_028;

-- ============================================================================
-- Migration 028 Complete
-- ============================================================================
