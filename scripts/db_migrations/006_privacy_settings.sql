-- ============================================================
-- Privacy Settings Migration
-- ============================================================
-- Adds privacy settings for users to opt-out of data collection
-- Run: mysql -u sulfur_bot_user -p sulfur_bot < 006_privacy_settings.sql
-- ============================================================

USE sulfur_bot;

-- Create privacy settings table
CREATE TABLE IF NOT EXISTS user_privacy_settings (
    user_id BIGINT PRIMARY KEY,
    data_collection_enabled BOOLEAN DEFAULT FALSE,  -- Off by default as per requirements
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_data_collection (data_collection_enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Add privacy flag to existing stats tables for quick checks
-- These are redundant but helpful for performance
ALTER TABLE user_stats 
    ADD COLUMN IF NOT EXISTS privacy_opt_in BOOLEAN DEFAULT FALSE;

-- Log the migration
INSERT INTO migration_log (migration_name, applied_at) 
VALUES ('006_privacy_settings', NOW())
ON DUPLICATE KEY UPDATE applied_at = NOW();

SELECT 'Privacy settings migration completed successfully' AS status;
