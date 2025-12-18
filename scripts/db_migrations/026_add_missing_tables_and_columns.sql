-- ============================================================================
-- Migration 026: Add Missing Tables and Columns
-- ============================================================================
-- This migration adds tables and columns that are referenced by code but
-- were missing from the database schema.
-- ============================================================================

-- ============================================================================
-- PART 1: Create stock_trades Table
-- ============================================================================
-- This table is queried by the dashboard (web_dashboard.py) for stock trading stats
-- but was missing from the database schema.

CREATE TABLE IF NOT EXISTS stock_trades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    stock_symbol VARCHAR(10) NOT NULL,
    quantity INT NOT NULL,
    price_per_share DECIMAL(18, 8) NOT NULL,
    trade_type ENUM('buy', 'sell') NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_stock_symbol (stock_symbol),
    INDEX idx_timestamp (timestamp),
    INDEX idx_trade_type (trade_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- PART 2: Add 'won' Column to sport_bets Table
-- ============================================================================
-- The sport_bets table was missing a 'won' column that queries are looking for.
-- We use the same safe procedure pattern as other migrations.

DELIMITER $$

DROP PROCEDURE IF EXISTS add_column_if_not_exists_026$$
CREATE PROCEDURE add_column_if_not_exists_026(
    IN p_table_name VARCHAR(64),
    IN p_column_name VARCHAR(64),
    IN p_column_definition VARCHAR(255)
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

-- Add 'won' column to sport_bets if it doesn't exist
CALL add_column_if_not_exists_026('sport_bets', 'won', 'BOOLEAN DEFAULT NULL');

-- Cleanup helper procedure
DROP PROCEDURE IF EXISTS add_column_if_not_exists_026;

-- ============================================================================
-- Migration 026 Complete
-- ============================================================================
