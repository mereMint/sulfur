-- Migration: Add missing columns to rpg_items table
-- Description: Adds is_quest_item, is_sellable, is_usable, and quest_id columns to rpg_items
-- This migration is BACKWARDS COMPATIBLE - existing data is preserved

-- Add is_quest_item column to rpg_items if it doesn't exist
SET @db_name = DATABASE();
SET @table_name = 'rpg_items';
SET @column_name = 'is_quest_item';

-- Check if column exists before adding
SET @query = IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE TABLE_SCHEMA = @db_name 
     AND TABLE_NAME = @table_name 
     AND COLUMN_NAME = @column_name) = 0,
    'ALTER TABLE rpg_items ADD COLUMN is_quest_item BOOLEAN DEFAULT FALSE AFTER created_by',
    'SELECT ''Column is_quest_item already exists'' AS message'
);

PREPARE stmt FROM @query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add is_sellable column to rpg_items if it doesn't exist
SET @column_name = 'is_sellable';

SET @query = IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE TABLE_SCHEMA = @db_name 
     AND TABLE_NAME = @table_name 
     AND COLUMN_NAME = @column_name) = 0,
    'ALTER TABLE rpg_items ADD COLUMN is_sellable BOOLEAN DEFAULT TRUE AFTER is_quest_item',
    'SELECT ''Column is_sellable already exists'' AS message'
);

PREPARE stmt FROM @query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add is_usable column to rpg_items if it doesn't exist
SET @column_name = 'is_usable';

SET @query = IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE TABLE_SCHEMA = @db_name 
     AND TABLE_NAME = @table_name 
     AND COLUMN_NAME = @column_name) = 0,
    'ALTER TABLE rpg_items ADD COLUMN is_usable BOOLEAN DEFAULT TRUE AFTER is_sellable',
    'SELECT ''Column is_usable already exists'' AS message'
);

PREPARE stmt FROM @query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add quest_id column to rpg_items if it doesn't exist
SET @column_name = 'quest_id';

SET @query = IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE TABLE_SCHEMA = @db_name 
     AND TABLE_NAME = @table_name 
     AND COLUMN_NAME = @column_name) = 0,
    'ALTER TABLE rpg_items ADD COLUMN quest_id VARCHAR(100) NULL AFTER is_usable',
    'SELECT ''Column quest_id already exists'' AS message'
);

PREPARE stmt FROM @query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add index for is_quest_item if it doesn't exist
SET @index_name = 'idx_quest';
SET @query = IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS 
     WHERE TABLE_SCHEMA = @db_name 
     AND TABLE_NAME = @table_name 
     AND INDEX_NAME = @index_name) = 0,
    'ALTER TABLE rpg_items ADD INDEX idx_quest (is_quest_item)',
    'SELECT ''Index idx_quest already exists'' AS message'
);

PREPARE stmt FROM @query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Migration completed successfully
