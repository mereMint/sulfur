-- ============================================================================
-- Migration 023: Fix Schema Drift
-- ============================================================================
-- This migration ensures all required columns exist in tables that may have
-- been created with older schemas. Uses stored procedures for safe column
-- addition (only adds if column doesn't exist).
-- ============================================================================

DELIMITER $$

-- Helper procedure to safely add a column if it doesn't exist
DROP PROCEDURE IF EXISTS add_column_if_not_exists$$
CREATE PROCEDURE add_column_if_not_exists(
    IN p_table_name VARCHAR(64),
    IN p_column_name VARCHAR(64),
    IN p_column_definition VARCHAR(255)
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
-- Fix user_stats table: Ensure all required columns exist
-- ============================================================================

CALL add_column_if_not_exists('user_stats', 'display_name', 'VARCHAR(255) NOT NULL DEFAULT \'Unknown\'');
CALL add_column_if_not_exists('user_stats', 'username', 'VARCHAR(255) NULL');
CALL add_column_if_not_exists('user_stats', 'messages_sent', 'INT NOT NULL DEFAULT 0');
CALL add_column_if_not_exists('user_stats', 'voice_minutes', 'INT NOT NULL DEFAULT 0');
CALL add_column_if_not_exists('user_stats', 'quests_completed', 'INT NOT NULL DEFAULT 0');
CALL add_column_if_not_exists('user_stats', 'games_played', 'INT NOT NULL DEFAULT 0');
CALL add_column_if_not_exists('user_stats', 'games_won', 'INT NOT NULL DEFAULT 0');
CALL add_column_if_not_exists('user_stats', 'total_bet', 'INT NOT NULL DEFAULT 0');
CALL add_column_if_not_exists('user_stats', 'total_won', 'INT NOT NULL DEFAULT 0');
CALL add_column_if_not_exists('user_stats', 'updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP');

-- ============================================================================
-- Fix blackjack_games table: Ensure payout column exists
-- ============================================================================

CALL add_column_if_not_exists('blackjack_games', 'payout', 'BIGINT NOT NULL DEFAULT 0');
CALL add_column_if_not_exists('blackjack_games', 'played_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP');

-- ============================================================================
-- Fix roulette_games table: Ensure payout column exists
-- ============================================================================

CALL add_column_if_not_exists('roulette_games', 'payout', 'BIGINT NOT NULL DEFAULT 0');
CALL add_column_if_not_exists('roulette_games', 'played_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP');

-- ============================================================================
-- Fix mines_games table: Ensure payout and played_at columns exist
-- ============================================================================

CALL add_column_if_not_exists('mines_games', 'payout', 'BIGINT NOT NULL DEFAULT 0');
CALL add_column_if_not_exists('mines_games', 'played_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP');
CALL add_column_if_not_exists('mines_games', 'revealed_count', 'INT NOT NULL DEFAULT 0');

-- ============================================================================
-- Create interaction_learnings table if it doesn't exist (referenced in code)
-- ============================================================================

CREATE TABLE IF NOT EXISTS interaction_learnings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    interaction_type VARCHAR(100) NOT NULL,
    context TEXT,
    response_quality DECIMAL(3,2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_type (interaction_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Fix stocks table: Add category column if missing (referenced in code)
-- ============================================================================

CALL add_column_if_not_exists('stocks', 'category', 'VARCHAR(20) DEFAULT \'general\'');

-- ============================================================================
-- PART 6: Create Consolidated User Profiles View (moved from migration 022)
-- ============================================================================
-- This view provides a unified view of user data for the dashboard
-- Must be created AFTER messages_sent and voice_minutes columns are added above

CREATE OR REPLACE VIEW v_user_profiles AS
SELECT
    p.discord_id as user_id,
    p.display_name,
    COALESCE(p.level, 0) as level,
    COALESCE(p.xp, 0) as xp,
    COALESCE(p.balance, 0) as balance,
    p.last_seen,
    COALESCE(uc.equipped_color, '#00ff41') as equipped_color,
    COALESCE(uc.language, 'de') as language,
    (SELECT COUNT(*) FROM feature_unlocks fu WHERE fu.user_id = p.discord_id) as premium_features_unlocked,
    (SELECT COALESCE(SUM(us.messages_sent), 0) FROM user_stats us WHERE us.user_id = p.discord_id) as total_messages,
    (SELECT COALESCE(SUM(us.voice_minutes), 0) FROM user_stats us WHERE us.user_id = p.discord_id) as total_voice_minutes,
    (SELECT COUNT(*) FROM music_history mh WHERE mh.user_id = p.discord_id) as songs_played
FROM players p
LEFT JOIN user_customization uc ON p.discord_id = uc.user_id;

-- ============================================================================
-- Cleanup helper procedure
-- ============================================================================

DROP PROCEDURE IF EXISTS add_column_if_not_exists;

-- ============================================================================
-- Migration 023 Complete
-- ============================================================================
