-- Migration: Add language column to word_find_daily table
-- Description: Adds language column to support multi-language daily words
-- This migration is BACKWARDS COMPATIBLE - existing data is preserved

-- Add language column to word_find_daily if it doesn't exist
-- Note: Column is added AFTER 'difficulty' for logical grouping.
-- This requires the 'difficulty' column to exist (which it should from table creation).
SET @db_name = DATABASE();
SET @table_name = 'word_find_daily';
SET @column_name = 'language';

-- Check if column exists before adding
SET @query = IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE TABLE_SCHEMA = @db_name 
     AND TABLE_NAME = @table_name 
     AND COLUMN_NAME = @column_name) = 0,
    'ALTER TABLE word_find_daily ADD COLUMN language VARCHAR(2) DEFAULT ''de'' AFTER difficulty',
    'SELECT ''Column language already exists in word_find_daily'' AS message'
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
    'ALTER TABLE word_find_daily ADD INDEX idx_lang (language)',
    'SELECT ''Index idx_lang already exists in word_find_daily'' AS message'
);

PREPARE stmt FROM @query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Update existing records to have default language 'de'
UPDATE word_find_daily 
SET language = 'de' 
WHERE language IS NULL OR language = '';

-- Check if unique constraint exists and recreate it with language
SET @constraint_name = 'unique_date_lang';
SET @query = IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS 
     WHERE TABLE_SCHEMA = @db_name 
     AND TABLE_NAME = @table_name 
     AND CONSTRAINT_NAME = @constraint_name) = 0,
    'ALTER TABLE word_find_daily ADD UNIQUE KEY unique_date_lang (date, language)',
    'SELECT ''Constraint unique_date_lang already exists in word_find_daily'' AS message'
);

PREPARE stmt FROM @query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add language column to word_find_premium_games if it doesn't exist
SET @table_name = 'word_find_premium_games';

SET @query = IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE TABLE_SCHEMA = @db_name 
     AND TABLE_NAME = @table_name 
     AND COLUMN_NAME = @column_name) = 0,
    'ALTER TABLE word_find_premium_games ADD COLUMN language VARCHAR(2) DEFAULT ''de'' AFTER difficulty',
    'SELECT ''Column language already exists in word_find_premium_games'' AS message'
);

PREPARE stmt FROM @query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Update existing premium game records to have default language 'de'
UPDATE word_find_premium_games 
SET language = 'de' 
WHERE language IS NULL OR language = '';

-- Ensure game_type column exists in word_find_attempts (from migration 007)
-- This is included here for completeness in case migration 007 was not run
SET @table_name = 'word_find_attempts';
SET @column_name = 'game_type';

-- Check if table exists first (may not exist yet - created in migration 011b)
SET @attempts_table_exists = (
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.TABLES 
    WHERE TABLE_SCHEMA = @db_name 
    AND TABLE_NAME = @table_name
);

SET @query = IF(
    @attempts_table_exists > 0 AND (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE TABLE_SCHEMA = @db_name 
     AND TABLE_NAME = @table_name 
     AND COLUMN_NAME = @column_name) = 0,
    'ALTER TABLE word_find_attempts ADD COLUMN game_type ENUM(''daily'', ''premium'') DEFAULT ''daily'' AFTER attempt_number',
    'SELECT ''Table word_find_attempts does not exist or column game_type already exists'' AS message'
);

PREPARE stmt FROM @query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add index for game_type queries if table exists
SET @index_name = 'idx_user_word_type';
SET @query = IF(
    @attempts_table_exists > 0 AND (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS 
     WHERE TABLE_SCHEMA = @db_name 
     AND TABLE_NAME = @table_name 
     AND INDEX_NAME = @index_name) = 0,
    'ALTER TABLE word_find_attempts ADD INDEX idx_user_word_type (user_id, word_id, game_type)',
    'SELECT ''Table word_find_attempts does not exist or index idx_user_word_type already exists'' AS message'
);

PREPARE stmt FROM @query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Migration completed successfully
SELECT 'Migration 009: Language and game_type columns added to word_find tables successfully' AS status;
