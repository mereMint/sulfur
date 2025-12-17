-- Migration 020: Remove any foreign key constraints from word_find_attempts
-- This fixes error 1452 (foreign key constraint fails) by removing any existing FK constraints
-- The word_find_attempts table references different tables based on game_type
-- so referential integrity is maintained at the application level

-- Check if table exists before trying to drop foreign keys
SET @db_name = DATABASE();
SET @table_exists = (
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.TABLES 
    WHERE TABLE_SCHEMA = @db_name 
    AND TABLE_NAME = 'word_find_attempts'
);

-- Only drop foreign keys if table exists
SET @drop_fk_query = IF(
    @table_exists > 0,
    'CALL drop_word_find_fk()',
    'SELECT ''Table word_find_attempts does not exist, skipping FK removal'' AS message'
);

-- Drop foreign key constraint if it exists
-- MySQL doesn't support DROP CONSTRAINT IF EXISTS, so we use a procedure

DELIMITER $$

DROP PROCEDURE IF EXISTS drop_word_find_fk$$
CREATE PROCEDURE drop_word_find_fk()
BEGIN
    DECLARE fk_name VARCHAR(255);
    DECLARE done INT DEFAULT FALSE;
    DECLARE table_exists INT DEFAULT 0;
    DECLARE fk_cursor CURSOR FOR
        SELECT CONSTRAINT_NAME 
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'word_find_attempts'
        AND REFERENCED_TABLE_NAME IS NOT NULL;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;
    
    -- Check if table exists
    SELECT COUNT(*) INTO table_exists
    FROM INFORMATION_SCHEMA.TABLES 
    WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'word_find_attempts';
    
    -- Only proceed if table exists
    IF table_exists > 0 THEN
        OPEN fk_cursor;
        
        read_loop: LOOP
            FETCH fk_cursor INTO fk_name;
            IF done THEN
                LEAVE read_loop;
            END IF;
            
            SET @sql = CONCAT('ALTER TABLE word_find_attempts DROP FOREIGN KEY ', fk_name);
            PREPARE stmt FROM @sql;
            EXECUTE stmt;
            DEALLOCATE PREPARE stmt;
        END LOOP;
        
        CLOSE fk_cursor;
    END IF;
END$$

DELIMITER ;

-- Execute the procedure only if table exists
CALL drop_word_find_fk();

-- Drop the procedure after use
DROP PROCEDURE IF EXISTS drop_word_find_fk;

-- End of migration
