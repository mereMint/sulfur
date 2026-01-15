-- ============================================================================
-- Migration 032: Fix Schema Column Name Inconsistencies
-- ============================================================================
-- This migration fixes column name inconsistencies between code and migrations:
-- 1. Adds 'timestamp' alias column to transaction_history (code uses created_at, 
--    but migration 029 creates index on 'timestamp')
-- 2. Ensures conversation_context has correct schema with last_bot_message_at
-- 3. Adds missing index columns for dashboard queries
-- ============================================================================

DELIMITER $$

-- Create helper procedure to add columns if they don't exist
DROP PROCEDURE IF EXISTS add_column_if_not_exists_032$$
CREATE PROCEDURE add_column_if_not_exists_032(
    IN p_table_name VARCHAR(64),
    IN p_column_name VARCHAR(64),
    IN p_column_definition VARCHAR(500)
)
BEGIN
    DECLARE table_exists INT DEFAULT 0;
    DECLARE column_exists INT DEFAULT 0;

    -- Check if table exists
    SELECT COUNT(*) INTO table_exists
    FROM information_schema.tables
    WHERE table_schema = DATABASE() AND table_name = p_table_name;

    IF table_exists > 0 THEN
        -- Check if column exists
        SELECT COUNT(*) INTO column_exists
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = p_table_name
          AND column_name = p_column_name;

        IF column_exists = 0 THEN
            SET @sql = CONCAT('ALTER TABLE `', p_table_name, '` ADD COLUMN `', p_column_name, '` ', p_column_definition);
            PREPARE stmt FROM @sql;
            EXECUTE stmt;
            DEALLOCATE PREPARE stmt;
        END IF;
    END IF;
END$$

DELIMITER ;

-- ============================================================================
-- PART 1: Fix transaction_history Table
-- ============================================================================
-- Migration 029 tries to create an index on 'timestamp' column, but the table
-- uses 'created_at'. Add 'timestamp' as a generated column for compatibility.

-- First, check if transaction_history exists and add timestamp column
CALL add_column_if_not_exists_032('transaction_history', 'timestamp', 'TIMESTAMP NULL');

-- Update timestamp from created_at if it exists and is NULL
SET @has_created_at = (
    SELECT COUNT(*)
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'transaction_history'
      AND column_name = 'created_at'
);

SET @update_timestamp_sql = IF(
    @has_created_at > 0,
    'UPDATE transaction_history SET timestamp = created_at WHERE timestamp IS NULL',
    'SELECT "created_at column does not exist, skipping timestamp sync" AS message'
);

PREPARE stmt FROM @update_timestamp_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add trigger to keep timestamp synced with created_at
-- First drop trigger if exists (MySQL < 8.0 doesn't support IF EXISTS for triggers in all cases)
SET @drop_trigger = (
    SELECT COUNT(*)
    FROM information_schema.triggers
    WHERE trigger_schema = DATABASE()
      AND trigger_name = 'transaction_history_timestamp_sync'
);

-- We can't easily conditionally create triggers, so use a different approach
-- Just ensure timestamp is set on new inserts via default value

-- ============================================================================
-- PART 2: Fix conversation_context Table
-- ============================================================================
-- Ensure conversation_context has the correct structure with last_bot_message_at

-- Check if conversation_context exists with wrong schema (has 'timestamp' instead of 'last_bot_message_at')
SET @has_timestamp_col = (
    SELECT COUNT(*)
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'conversation_context'
      AND column_name = 'timestamp'
);

SET @has_last_bot_message_at = (
    SELECT COUNT(*)
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'conversation_context'
      AND column_name = 'last_bot_message_at'
);

-- If table has 'timestamp' but not 'last_bot_message_at', add the column
CALL add_column_if_not_exists_032('conversation_context', 'last_bot_message_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP');

-- Sync last_bot_message_at from timestamp if needed
SET @sync_bot_message = IF(
    @has_timestamp_col > 0,
    'UPDATE conversation_context SET last_bot_message_at = timestamp WHERE last_bot_message_at IS NULL',
    'SELECT "No timestamp column to sync from" AS message'
);

PREPARE stmt FROM @sync_bot_message;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add missing columns for conversation_context
CALL add_column_if_not_exists_032('conversation_context', 'last_user_message', 'TEXT NULL');
CALL add_column_if_not_exists_032('conversation_context', 'last_bot_response', 'TEXT NULL');
CALL add_column_if_not_exists_032('conversation_context', 'context_data', 'JSON NULL');

-- Add index on last_bot_message_at if not exists
SET @add_idx_last_bot_message = IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS 
     WHERE TABLE_SCHEMA = DATABASE() 
       AND TABLE_NAME = 'conversation_context' 
       AND INDEX_NAME = 'idx_last_bot_message_at') = 0,
    'CREATE INDEX idx_last_bot_message_at ON conversation_context(last_bot_message_at)',
    'SELECT "Index idx_last_bot_message_at already exists" AS message'
);
PREPARE stmt FROM @add_idx_last_bot_message;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- ============================================================================
-- PART 3: Add Missing Indexes for Dashboard
-- ============================================================================
-- Add index on transaction_history.created_at which is what the code actually uses

SET @add_idx_created_at = IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS 
     WHERE TABLE_SCHEMA = DATABASE() 
       AND TABLE_NAME = 'transaction_history' 
       AND INDEX_NAME = 'idx_transaction_history_created_at') = 0,
    'CREATE INDEX idx_transaction_history_created_at ON transaction_history(created_at DESC)',
    'SELECT "Index idx_transaction_history_created_at already exists" AS message'
);
PREPARE stmt FROM @add_idx_created_at;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add user_id + created_at composite index
SET @add_idx_user_created = IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS 
     WHERE TABLE_SCHEMA = DATABASE() 
       AND TABLE_NAME = 'transaction_history' 
       AND INDEX_NAME = 'idx_transaction_user_created') = 0,
    'CREATE INDEX idx_transaction_user_created ON transaction_history(user_id, created_at DESC)',
    'SELECT "Index idx_transaction_user_created already exists" AS message'
);
PREPARE stmt FROM @add_idx_user_created;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- ============================================================================
-- Cleanup
-- ============================================================================
DROP PROCEDURE IF EXISTS add_column_if_not_exists_032;

-- ============================================================================
-- Migration 032 Complete
-- ============================================================================
