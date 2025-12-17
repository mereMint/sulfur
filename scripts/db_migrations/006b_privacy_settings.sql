-- ============================================================
-- Privacy Settings Migration
-- ============================================================
-- Adds privacy settings for users to opt-out of data collection
-- ============================================================

-- Create privacy settings table
CREATE TABLE IF NOT EXISTS user_privacy_settings (
    user_id BIGINT PRIMARY KEY,
    data_collection_enabled BOOLEAN DEFAULT FALSE,  -- Off by default as per requirements
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_data_collection (data_collection_enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Add privacy flag to existing stats tables for quick checks
-- Use a stored procedure to safely add the column
DELIMITER $$

DROP PROCEDURE IF EXISTS add_privacy_opt_in_column$$
CREATE PROCEDURE add_privacy_opt_in_column()
BEGIN
    -- Check if user_stats table exists first
    IF EXISTS (
        SELECT * FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'user_stats'
    ) THEN
        -- Add privacy_opt_in column if it doesn't exist
        IF NOT EXISTS (
            SELECT * FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'user_stats' 
            AND COLUMN_NAME = 'privacy_opt_in'
        ) THEN
            ALTER TABLE user_stats 
            ADD COLUMN privacy_opt_in BOOLEAN DEFAULT FALSE;
        END IF;
    END IF;
END$$

DELIMITER ;

-- Execute the procedure
CALL add_privacy_opt_in_column();

-- Drop the procedure after use
DROP PROCEDURE IF EXISTS add_privacy_opt_in_column;
