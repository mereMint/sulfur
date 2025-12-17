-- Migration: Fix Word Find Schema Conflicts from Migration 010
-- Description: Removes incorrect word_find tables created by migration 010
--              and ensures the correct schema exists as defined in modules/word_find.py
-- This migration is SAFE - it only affects incorrectly created tables

-- ============================================================================
-- Step 1: Check and remove conflicting word_find_daily table
-- ============================================================================
-- Migration 010 incorrectly created word_find_daily with columns:
--   (puzzle_date, grid, words)
-- The correct schema has columns:
--   (word, difficulty, language, date)

SET @db_name = DATABASE();

-- Check if the table exists with the WRONG schema (has 'puzzle_date' column)
SET @has_wrong_schema = (
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = @db_name 
    AND TABLE_NAME = 'word_find_daily' 
    AND COLUMN_NAME = 'puzzle_date'
);

-- If wrong schema exists, drop the table so it can be recreated correctly
SET @drop_query = IF(
    @has_wrong_schema > 0,
    'DROP TABLE IF EXISTS word_find_daily',
    'DO 0'
);

PREPARE stmt FROM @drop_query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Also check for and drop word_find_user_progress (not used by actual code)
DROP TABLE IF EXISTS word_find_user_progress;

-- Check if word_find_user_stats exists (wrong table name, should be word_find_stats)
SET @has_user_stats = (
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.TABLES 
    WHERE TABLE_SCHEMA = @db_name 
    AND TABLE_NAME = 'word_find_user_stats'
);

-- Drop it if it exists (the correct table is word_find_stats)
SET @drop_user_stats = IF(
    @has_user_stats > 0,
    'DROP TABLE IF EXISTS word_find_user_stats',
    'DO 0'
);

PREPARE stmt FROM @drop_user_stats;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- ============================================================================
-- Step 2: Create correct word_find tables (from modules/word_find.py)
-- ============================================================================

-- Table for daily word
CREATE TABLE IF NOT EXISTS word_find_daily (
    id INT AUTO_INCREMENT PRIMARY KEY,
    word VARCHAR(100) NOT NULL,
    difficulty VARCHAR(20) NOT NULL,
    language VARCHAR(2) DEFAULT 'de',
    date DATE NOT NULL,
    UNIQUE KEY unique_date_lang (date, language),
    INDEX idx_date (date),
    INDEX idx_lang (language)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table for premium games (separate from daily)
CREATE TABLE IF NOT EXISTS word_find_premium_games (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    word VARCHAR(100) NOT NULL,
    difficulty VARCHAR(20) NOT NULL,
    language VARCHAR(2) DEFAULT 'de',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed BOOLEAN DEFAULT FALSE,
    won BOOLEAN DEFAULT FALSE,
    INDEX idx_user_created (user_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table for user attempts
CREATE TABLE IF NOT EXISTS word_find_attempts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    word_id INT NOT NULL,
    guess VARCHAR(100) NOT NULL,
    similarity_score FLOAT NOT NULL,
    attempt_number INT NOT NULL,
    game_type ENUM('daily', 'premium') DEFAULT 'daily',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_word_type (user_id, word_id, game_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table for user stats (backwards compatible - supports both old and new schema)
CREATE TABLE IF NOT EXISTS word_find_stats (
    user_id BIGINT PRIMARY KEY,
    total_games INT DEFAULT 0,
    total_wins INT DEFAULT 0,
    current_streak INT DEFAULT 0,
    best_streak INT DEFAULT 0,
    total_attempts INT DEFAULT 0,
    daily_games INT DEFAULT 0,
    daily_wins INT DEFAULT 0,
    daily_streak INT DEFAULT 0,
    daily_best_streak INT DEFAULT 0,
    daily_total_attempts INT DEFAULT 0,
    premium_games INT DEFAULT 0,
    premium_wins INT DEFAULT 0,
    premium_total_attempts INT DEFAULT 0,
    last_played DATE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Migration completed successfully
-- ============================================================================
SELECT 'Migration 011: Fixed word_find schema conflicts successfully' AS status;
