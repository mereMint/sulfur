-- ============================================================
-- Migration: Add missing abilities column to rpg_monsters table
-- ============================================================
-- Description: Adds abilities JSON column to rpg_monsters if it doesn't exist
-- This migration is BACKWARDS COMPATIBLE - existing data is preserved
-- ============================================================

DELIMITER $$

DROP PROCEDURE IF EXISTS add_rpg_monsters_abilities_column$$
CREATE PROCEDURE add_rpg_monsters_abilities_column()
BEGIN
    -- Check if rpg_monsters table exists first
    IF EXISTS (
        SELECT * FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'rpg_monsters'
    ) THEN
        -- Add abilities column if it doesn't exist
        IF NOT EXISTS (
            SELECT * FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'rpg_monsters' 
            AND COLUMN_NAME = 'abilities'
        ) THEN
            ALTER TABLE rpg_monsters 
            ADD COLUMN abilities JSON;
        END IF;
    END IF;
END$$

DELIMITER ;

-- Execute the procedure
CALL add_rpg_monsters_abilities_column();

-- Drop the procedure after use
DROP PROCEDURE IF EXISTS add_rpg_monsters_abilities_column;

-- Migration completed successfully
