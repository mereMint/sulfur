-- ============================================================
-- Migration: Add missing columns to rpg_items table
-- ============================================================
-- Description: Adds is_quest_item, is_sellable, is_usable, and quest_id columns to rpg_items
-- This migration is BACKWARDS COMPATIBLE - existing data is preserved
-- ============================================================

DELIMITER $$

DROP PROCEDURE IF EXISTS add_rpg_items_columns$$
CREATE PROCEDURE add_rpg_items_columns()
BEGIN
    -- Check if rpg_items table exists first
    IF EXISTS (
        SELECT * FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'rpg_items'
    ) THEN
        -- Add is_quest_item column if it doesn't exist
        IF NOT EXISTS (
            SELECT * FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'rpg_items' 
            AND COLUMN_NAME = 'is_quest_item'
        ) THEN
            ALTER TABLE rpg_items 
            ADD COLUMN is_quest_item BOOLEAN DEFAULT FALSE AFTER created_by;
        END IF;
        
        -- Add is_sellable column if it doesn't exist
        IF NOT EXISTS (
            SELECT * FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'rpg_items' 
            AND COLUMN_NAME = 'is_sellable'
        ) THEN
            ALTER TABLE rpg_items 
            ADD COLUMN is_sellable BOOLEAN DEFAULT TRUE AFTER is_quest_item;
        END IF;
        
        -- Add is_usable column if it doesn't exist
        IF NOT EXISTS (
            SELECT * FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'rpg_items' 
            AND COLUMN_NAME = 'is_usable'
        ) THEN
            ALTER TABLE rpg_items 
            ADD COLUMN is_usable BOOLEAN DEFAULT TRUE AFTER is_sellable;
        END IF;
        
        -- Add quest_id column if it doesn't exist
        IF NOT EXISTS (
            SELECT * FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'rpg_items' 
            AND COLUMN_NAME = 'quest_id'
        ) THEN
            ALTER TABLE rpg_items 
            ADD COLUMN quest_id VARCHAR(100) NULL AFTER is_usable;
        END IF;
        
        -- Add index for is_quest_item if it doesn't exist
        IF NOT EXISTS (
            SELECT * FROM information_schema.STATISTICS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'rpg_items' 
            AND INDEX_NAME = 'idx_quest'
        ) THEN
            ALTER TABLE rpg_items 
            ADD INDEX idx_quest (is_quest_item);
        END IF;
    END IF;
END$$

DELIMITER ;

-- Execute the procedure
CALL add_rpg_items_columns();

-- Drop the procedure after use
DROP PROCEDURE IF EXISTS add_rpg_items_columns;

-- Migration completed successfully
