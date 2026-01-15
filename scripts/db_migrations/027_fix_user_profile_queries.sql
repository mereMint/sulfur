-- ============================================================================
-- Migration 027: Fix User Profile Database Schema Issues
-- ============================================================================
-- This migration fixes the database schema issues causing user profile errors:
-- 1. Adds missing columns to stock_trades table (action, symbol, traded_at)
-- 2. Adds missing 'won' column to mines_games table
-- 3. Adds missing 'payout' column to mines_games table
-- 4. Adds missing 'shots_survived' column to russian_roulette_games table
-- ============================================================================

DELIMITER $$

-- Create helper procedure to add columns if they don't exist
DROP PROCEDURE IF EXISTS add_column_if_not_exists_027$$
CREATE PROCEDURE add_column_if_not_exists_027(
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
-- PART 1: Fix stock_trades Table
-- ============================================================================
-- The web_dashboard.py queries expect 'action', 'symbol', and 'traded_at' columns
-- but migration 026 created 'trade_type', 'stock_symbol', and 'timestamp' instead
--
-- NOTE: We intentionally create duplicate columns for backward compatibility.
-- This allows the system to work with both old and new code versions during
-- deployment. In a future migration, we can consolidate these columns once
-- all instances are updated.
--
-- Alternative approaches considered:
-- 1. Database views: Would require changes to all queries and ORM mappings
-- 2. Update all queries: Risky in a live system with multiple components
-- 3. Column rename: Could break existing code that uses old column names
--
-- Current approach (duplicate columns) provides:
-- - Zero downtime deployment
-- - Gradual migration path
-- - Easy rollback if needed
-- - No breaking changes to existing code

-- Add 'action' column (alias for trade_type)
CALL add_column_if_not_exists_027('stock_trades', 'action', 'VARCHAR(10) NULL');

-- Add 'symbol' column (alias for stock_symbol)
CALL add_column_if_not_exists_027('stock_trades', 'symbol', 'VARCHAR(10) NULL');

-- Add 'traded_at' column (alias for timestamp)
CALL add_column_if_not_exists_027('stock_trades', 'traded_at', 'TIMESTAMP NULL DEFAULT NULL');

-- Add indexes on new columns for better query performance (before UPDATE)
-- Use dynamic SQL to avoid errors if indexes already exist
SET @create_idx_action = IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS 
     WHERE TABLE_SCHEMA = DATABASE() 
       AND TABLE_NAME = 'stock_trades' 
       AND INDEX_NAME = 'idx_stock_trades_action') = 0,
    'CREATE INDEX idx_stock_trades_action ON stock_trades(action)',
    'SELECT "Index idx_stock_trades_action already exists" AS message'
);
PREPARE stmt FROM @create_idx_action;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @create_idx_symbol = IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS 
     WHERE TABLE_SCHEMA = DATABASE() 
       AND TABLE_NAME = 'stock_trades' 
       AND INDEX_NAME = 'idx_stock_trades_symbol') = 0,
    'CREATE INDEX idx_stock_trades_symbol ON stock_trades(symbol)',
    'SELECT "Index idx_stock_trades_symbol already exists" AS message'
);
PREPARE stmt FROM @create_idx_symbol;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @create_idx_traded_at = IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS 
     WHERE TABLE_SCHEMA = DATABASE() 
       AND TABLE_NAME = 'stock_trades' 
       AND INDEX_NAME = 'idx_stock_trades_traded_at') = 0,
    'CREATE INDEX idx_stock_trades_traded_at ON stock_trades(traded_at)',
    'SELECT "Index idx_stock_trades_traded_at already exists" AS message'
);
PREPARE stmt FROM @create_idx_traded_at;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Update existing data to populate the new columns
-- This is safe because we have indexes and use NULL checks
UPDATE stock_trades 
SET action = trade_type, 
    symbol = stock_symbol,
    traded_at = timestamp
WHERE action IS NULL OR symbol IS NULL OR traded_at IS NULL;

-- ============================================================================
-- PART 2: Fix mines_games Table
-- ============================================================================
-- Add 'won' column (boolean) - can be derived from result column
CALL add_column_if_not_exists_027('mines_games', 'won', 'BOOLEAN NULL');

-- Add 'payout' column - can be derived from won_amount
CALL add_column_if_not_exists_027('mines_games', 'payout', 'BIGINT NULL DEFAULT 0');

-- Update existing data
-- First update 'won' column based on result
UPDATE mines_games 
SET won = (result = 'win' OR result = 'won' OR result = 'cashed_out')
WHERE won IS NULL;

-- Update 'payout' column from won_amount ONLY if won_amount column exists
-- Check for won_amount column and copy data if available
SET @won_amount_exists = (
    SELECT COUNT(*) 
    FROM information_schema.columns 
    WHERE table_schema = DATABASE() 
      AND table_name = 'mines_games' 
      AND column_name = 'won_amount'
);

-- If won_amount exists, copy the data
SET @update_payout_sql = IF(
    @won_amount_exists > 0,
    'UPDATE mines_games SET payout = COALESCE(won_amount, 0) WHERE payout IS NULL OR payout = 0',
    'SELECT "won_amount column does not exist, skipping payout update" AS message'
);

PREPARE update_payout_stmt FROM @update_payout_sql;
EXECUTE update_payout_stmt;
DEALLOCATE PREPARE update_payout_stmt;

-- ============================================================================
-- PART 3: Fix russian_roulette_games Table
-- ============================================================================
-- Add 'shots_survived' column
CALL add_column_if_not_exists_027('russian_roulette_games', 'shots_survived', 'INT NULL DEFAULT 0');

-- Update existing data - if survived, assume at least 1 shot
UPDATE russian_roulette_games 
SET shots_survived = CASE WHEN survived = 1 THEN 1 ELSE 0 END
WHERE shots_survived IS NULL OR shots_survived = 0;

-- ============================================================================
-- Cleanup
-- ============================================================================
DROP PROCEDURE IF EXISTS add_column_if_not_exists_027;

-- ============================================================================
-- Migration 027 Complete
-- ============================================================================
