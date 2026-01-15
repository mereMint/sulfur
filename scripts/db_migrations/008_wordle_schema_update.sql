-- Migration: Add language and game_type support to Wordle tables
-- Description: Updates wordle tables to support multi-language and premium games
-- This migration is BACKWARDS COMPATIBLE - existing data is preserved

-- ============================================================================
-- STEP 0: Ensure wordle_daily table exists
-- ============================================================================
-- The wordle_daily table is normally created by modules/wordle.py
-- but we need to ensure it exists before we can modify it

CREATE TABLE IF NOT EXISTS wordle_daily (
    id INT AUTO_INCREMENT PRIMARY KEY,
    word VARCHAR(5) NOT NULL,
    date DATE NOT NULL,
    UNIQUE KEY unique_date (date),
    INDEX idx_date (date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- STEP 1: Add language column to wordle_daily if it doesn't exist
-- ============================================================================
-- Add language column to wordle_daily if it doesn't exist
-- Default 'de' ensures all existing words are treated as German (backwards compatible)
SET @db_name = DATABASE();
SET @table_name = 'wordle_daily';
SET @column_name = 'language';

-- Check if column exists before adding
SET @query = IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE TABLE_SCHEMA = @db_name 
     AND TABLE_NAME = @table_name 
     AND COLUMN_NAME = @column_name) = 0,
    'ALTER TABLE wordle_daily ADD COLUMN language VARCHAR(2) DEFAULT ''de'' AFTER word',
    'SELECT ''Column language already exists in wordle_daily'' AS message'
);

PREPARE stmt FROM @query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add index for language if not exists
SET @index_name = 'idx_lang';
SET @query = IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS 
     WHERE TABLE_SCHEMA = @db_name 
     AND TABLE_NAME = @table_name 
     AND INDEX_NAME = @index_name) = 0,
    'ALTER TABLE wordle_daily ADD INDEX idx_lang (language)',
    'SELECT ''Index idx_lang already exists in wordle_daily'' AS message'
);

PREPARE stmt FROM @query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Update unique key to include language if needed
-- First, check if the old unique key exists and drop it
SET @query = IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS 
     WHERE TABLE_SCHEMA = @db_name 
     AND TABLE_NAME = @table_name 
     AND INDEX_NAME = 'date' 
     AND NON_UNIQUE = 0) > 0,
    'ALTER TABLE wordle_daily DROP INDEX date',
    'SELECT ''Old date unique key does not exist'' AS message'
);

PREPARE stmt FROM @query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add new composite unique key for date and language
SET @index_name = 'unique_date_lang';
SET @query = IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS 
     WHERE TABLE_SCHEMA = @db_name 
     AND TABLE_NAME = @table_name 
     AND INDEX_NAME = @index_name) = 0,
    'ALTER TABLE wordle_daily ADD UNIQUE KEY unique_date_lang (date, language)',
    'SELECT ''Unique key unique_date_lang already exists in wordle_daily'' AS message'
);

PREPARE stmt FROM @query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- ============================================================================
-- STEP 2: Ensure wordle_attempts table exists
-- ============================================================================
CREATE TABLE IF NOT EXISTS wordle_attempts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    word_id INT NOT NULL,
    guess VARCHAR(5) NOT NULL,
    attempt_number INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_word (user_id, word_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Add game_type column to wordle_attempts if it doesn't exist
-- Default 'daily' ensures all existing attempts are treated as daily games
SET @table_name = 'wordle_attempts';
SET @column_name = 'game_type';

SET @query = IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE TABLE_SCHEMA = @db_name 
     AND TABLE_NAME = @table_name 
     AND COLUMN_NAME = @column_name) = 0,
    'ALTER TABLE wordle_attempts ADD COLUMN game_type ENUM(''daily'', ''premium'') DEFAULT ''daily'' AFTER attempt_number',
    'SELECT ''Column game_type already exists in wordle_attempts'' AS message'
);

PREPARE stmt FROM @query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add index for game_type queries if not exists
SET @index_name = 'idx_user_word_type';
SET @query = IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS 
     WHERE TABLE_SCHEMA = @db_name 
     AND TABLE_NAME = @table_name 
     AND INDEX_NAME = @index_name) = 0,
    'ALTER TABLE wordle_attempts ADD INDEX idx_user_word_type (user_id, word_id, game_type)',
    'SELECT ''Index idx_user_word_type already exists in wordle_attempts'' AS message'
);

PREPARE stmt FROM @query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Create wordle_premium_games table if it doesn't exist
CREATE TABLE IF NOT EXISTS wordle_premium_games (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    word VARCHAR(5) NOT NULL,
    language VARCHAR(2) DEFAULT 'de',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed BOOLEAN DEFAULT FALSE,
    won BOOLEAN DEFAULT FALSE,
    INDEX idx_user_created (user_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Migration completed successfully
-- Note: This migration is fully backwards compatible
-- All existing wordle_daily words will default to German ('de')
-- All existing wordle_attempts will default to 'daily' game type
