-- Migration: Add language column to user_customization table if it doesn't exist
-- This fixes the error: Unknown column 'language' in 'SELECT'
-- Date: 2025-11-23

-- Use a stored procedure to check if column exists before adding it
DELIMITER //

CREATE PROCEDURE add_language_column_if_not_exists()
BEGIN
    -- Check if the column exists
    IF NOT EXISTS (
        SELECT * FROM information_schema.columns 
        WHERE table_schema = DATABASE()
        AND table_name = 'user_customization'
        AND column_name = 'language'
    ) THEN
        -- Add the column if it doesn't exist
        ALTER TABLE user_customization 
        ADD COLUMN language VARCHAR(2) DEFAULT 'de' 
        AFTER profile_background;
    END IF;
END//

DELIMITER ;

-- Execute the procedure
CALL add_language_column_if_not_exists();

-- Drop the procedure after use
DROP PROCEDURE add_language_column_if_not_exists;
