-- Migration: Add premium game support to Word Find
-- Description: Updates word_find tables to support premium games and game types
-- This migration is BACKWARDS COMPATIBLE - existing data is preserved

-- Create premium games table
CREATE TABLE IF NOT EXISTS word_find_premium_games (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    word VARCHAR(100) NOT NULL,
    difficulty VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed BOOLEAN DEFAULT FALSE,
    won BOOLEAN DEFAULT FALSE,
    INDEX idx_user_created (user_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Add game_type column to word_find_attempts if it doesn't exist
-- Default 'daily' ensures all existing attempts are treated as daily games
SET @db_name = DATABASE();
SET @table_name = 'word_find_attempts';
SET @column_name = 'game_type';

-- Check if table exists first (may not exist yet - created in migration 011b)
SET @table_exists = (
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.TABLES 
    WHERE TABLE_SCHEMA = @db_name 
    AND TABLE_NAME = @table_name
);

-- Only add column if table exists AND column doesn't exist
SET @query = IF(
    @table_exists > 0 AND (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE TABLE_SCHEMA = @db_name 
     AND TABLE_NAME = @table_name 
     AND COLUMN_NAME = @column_name) = 0,
    'ALTER TABLE word_find_attempts ADD COLUMN game_type ENUM(''daily'', ''premium'') DEFAULT ''daily'' AFTER attempt_number',
    'SELECT ''Table word_find_attempts does not exist or column game_type already exists'' AS message'
);

PREPARE stmt FROM @query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add index for game_type queries if table and column exist
SET @index_name = 'idx_user_word_type';
SET @query = IF(
    @table_exists > 0 AND (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS 
     WHERE TABLE_SCHEMA = @db_name 
     AND TABLE_NAME = @table_name 
     AND INDEX_NAME = @index_name) = 0,
    'ALTER TABLE word_find_attempts ADD INDEX idx_user_word_type (user_id, word_id, game_type)',
    'SELECT ''Table word_find_attempts does not exist or index idx_user_word_type already exists'' AS message'
);

PREPARE stmt FROM @query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add new columns to word_find_stats for separate daily/premium tracking
-- BACKWARDS COMPATIBLE: Keep old columns and add new ones
SET @table_name = 'word_find_stats';

-- Check if word_find_stats table exists
SET @stats_table_exists = (
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.TABLES 
    WHERE TABLE_SCHEMA = @db_name 
    AND TABLE_NAME = @table_name
);

-- Add daily_games column
SET @column_name = 'daily_games';
SET @query = IF(
    @stats_table_exists > 0 AND (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE TABLE_SCHEMA = @db_name 
     AND TABLE_NAME = @table_name 
     AND COLUMN_NAME = @column_name) = 0,
    'ALTER TABLE word_find_stats ADD COLUMN daily_games INT DEFAULT 0 AFTER user_id',
    'SELECT ''Table word_find_stats does not exist or column daily_games already exists'' AS message'
);
PREPARE stmt FROM @query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add daily_wins column
SET @column_name = 'daily_wins';
SET @query = IF(
    @stats_table_exists > 0 AND (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE TABLE_SCHEMA = @db_name 
     AND TABLE_NAME = @table_name 
     AND COLUMN_NAME = @column_name) = 0,
    'ALTER TABLE word_find_stats ADD COLUMN daily_wins INT DEFAULT 0',
    'SELECT ''Table word_find_stats does not exist or column daily_wins already exists'' AS message'
);
PREPARE stmt FROM @query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add daily_streak column
SET @column_name = 'daily_streak';
SET @query = IF(
    @stats_table_exists > 0 AND (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE TABLE_SCHEMA = @db_name 
     AND TABLE_NAME = @table_name 
     AND COLUMN_NAME = @column_name) = 0,
    'ALTER TABLE word_find_stats ADD COLUMN daily_streak INT DEFAULT 0',
    'SELECT ''Table word_find_stats does not exist or column daily_streak already exists'' AS message'
);
PREPARE stmt FROM @query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add daily_best_streak column
SET @column_name = 'daily_best_streak';
SET @query = IF(
    @stats_table_exists > 0 AND (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE TABLE_SCHEMA = @db_name 
     AND TABLE_NAME = @table_name 
     AND COLUMN_NAME = @column_name) = 0,
    'ALTER TABLE word_find_stats ADD COLUMN daily_best_streak INT DEFAULT 0',
    'SELECT ''Table word_find_stats does not exist or column daily_best_streak already exists'' AS message'
);
PREPARE stmt FROM @query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add daily_total_attempts column
SET @column_name = 'daily_total_attempts';
SET @query = IF(
    @stats_table_exists > 0 AND (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE TABLE_SCHEMA = @db_name 
     AND TABLE_NAME = @table_name 
     AND COLUMN_NAME = @column_name) = 0,
    'ALTER TABLE word_find_stats ADD COLUMN daily_total_attempts INT DEFAULT 0',
    'SELECT ''Table word_find_stats does not exist or column daily_total_attempts already exists'' AS message'
);
PREPARE stmt FROM @query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add premium_games column
SET @column_name = 'premium_games';
SET @query = IF(
    @stats_table_exists > 0 AND (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE TABLE_SCHEMA = @db_name 
     AND TABLE_NAME = @table_name 
     AND COLUMN_NAME = @column_name) = 0,
    'ALTER TABLE word_find_stats ADD COLUMN premium_games INT DEFAULT 0',
    'SELECT ''Table word_find_stats does not exist or column premium_games already exists'' AS message'
);
PREPARE stmt FROM @query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add premium_wins column
SET @column_name = 'premium_wins';
SET @query = IF(
    @stats_table_exists > 0 AND (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE TABLE_SCHEMA = @db_name 
     AND TABLE_NAME = @table_name 
     AND COLUMN_NAME = @column_name) = 0,
    'ALTER TABLE word_find_stats ADD COLUMN premium_wins INT DEFAULT 0',
    'SELECT ''Table word_find_stats does not exist or column premium_wins already exists'' AS message'
);
PREPARE stmt FROM @query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add premium_total_attempts column
SET @column_name = 'premium_total_attempts';
SET @query = IF(
    @stats_table_exists > 0 AND (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE TABLE_SCHEMA = @db_name 
     AND TABLE_NAME = @table_name 
     AND COLUMN_NAME = @column_name) = 0,
    'ALTER TABLE word_find_stats ADD COLUMN premium_total_attempts INT DEFAULT 0',
    'SELECT ''Table word_find_stats does not exist or column premium_total_attempts already exists'' AS message'
);
PREPARE stmt FROM @query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Migrate existing data from old columns to new daily columns (only if table exists)
-- This preserves all existing statistics
SET @update_query = IF(
    @stats_table_exists > 0,
    'UPDATE word_find_stats 
     SET daily_games = COALESCE(total_games, 0),
         daily_wins = COALESCE(total_wins, 0),
         daily_streak = COALESCE(current_streak, 0),
         daily_best_streak = COALESCE(best_streak, 0),
         daily_total_attempts = COALESCE(total_attempts, 0)
     WHERE daily_games = 0 AND total_games > 0',
    'SELECT ''Table word_find_stats does not exist, skipping data migration'' AS message'
);

PREPARE stmt FROM @update_query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Migration completed successfully
-- Note: Old columns (total_games, total_wins, etc.) are kept for backwards compatibility
-- They will continue to work with the get_user_stats function
