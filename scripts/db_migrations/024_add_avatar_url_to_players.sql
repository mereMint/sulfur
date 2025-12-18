-- ============================================================================
-- Migration 024: Add avatar_url column to players table
-- ============================================================================
-- This migration adds Discord avatar URL storage for user profiles on the web dashboard

-- Add avatar_url column to players table if it doesn't exist
SET @exist_avatar := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'players'
    AND COLUMN_NAME = 'avatar_url');

SET @sql_avatar := IF(@exist_avatar = 0,
    'ALTER TABLE players ADD COLUMN avatar_url VARCHAR(500) DEFAULT NULL',
    'SELECT "avatar_url column already exists"');

PREPARE stmt_avatar FROM @sql_avatar;
EXECUTE stmt_avatar;
DEALLOCATE PREPARE stmt_avatar;

-- ============================================================================
-- Migration 024 Complete
-- ============================================================================
