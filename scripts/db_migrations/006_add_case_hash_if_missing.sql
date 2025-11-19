-- ============================================================
-- Add case_hash column to detective_cases if missing
-- ============================================================
-- This migration safely adds the case_hash column to existing
-- detective_cases tables that were created before this column
-- was added to the base schema.
-- ============================================================

DELIMITER $$

DROP PROCEDURE IF EXISTS add_case_hash_if_missing$$
CREATE PROCEDURE add_case_hash_if_missing()
BEGIN
    IF NOT EXISTS (
        SELECT * FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() 
        AND TABLE_NAME = 'detective_cases' 
        AND COLUMN_NAME = 'case_hash'
    ) THEN
        ALTER TABLE detective_cases 
        ADD COLUMN case_hash VARCHAR(64) UNIQUE COMMENT 'SHA256 hash for uniqueness checking',
        ADD INDEX idx_case_hash (case_hash);
    END IF;
END$$

DELIMITER ;

-- Execute the procedure
CALL add_case_hash_if_missing();

-- Drop the procedure after use
DROP PROCEDURE IF EXISTS add_case_hash_if_missing;
