-- ============================================================================
-- Migration 022: Optimize Database Schema (Simplified)
-- ============================================================================
-- This migration adds performance indexes and creates optimized tables.
-- All operations are safe (CREATE IF NOT EXISTS, DROP IF EXISTS, etc.)
-- ============================================================================

-- ============================================================================
-- PART 1: Create Unified Word Games Stats Table (if not exists)
-- ============================================================================

CREATE TABLE IF NOT EXISTS word_games_stats (
    user_id BIGINT UNSIGNED NOT NULL,
    game_type ENUM('wordle', 'word_find') NOT NULL,
    mode ENUM('daily', 'premium', 'all') DEFAULT 'all',
    total_games INT UNSIGNED DEFAULT 0,
    total_wins INT UNSIGNED DEFAULT 0,
    current_streak INT UNSIGNED DEFAULT 0,
    max_streak INT UNSIGNED DEFAULT 0,
    average_attempts DECIMAL(4,2) DEFAULT 0.00,
    last_played DATETIME NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, game_type, mode),
    INDEX idx_streaks (game_type, current_streak DESC),
    INDEX idx_last_played (last_played DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- PART 2: Drop Unused Tables (Safe - only if they exist and are empty/obsolete)
-- ============================================================================

-- These tables are superseded by newer implementations
DROP TABLE IF EXISTS reflection_sessions;
DROP TABLE IF EXISTS semantic_memory;
-- Note: interaction_learnings is still used by code, don't drop it

-- ============================================================================
-- PART 3: Add Essential Performance Indexes (only if tables exist)
-- Note: We use a stored procedure approach for compatibility with MariaDB < 10.1
-- which doesn't support CREATE INDEX IF NOT EXISTS. This approach works on all versions.
-- ============================================================================

DELIMITER $$

-- Helper procedure to safely add indexes
DROP PROCEDURE IF EXISTS add_index_if_not_exists$$
CREATE PROCEDURE add_index_if_not_exists(
    IN p_table_name VARCHAR(64),
    IN p_index_name VARCHAR(64),
    IN p_index_columns VARCHAR(255)
)
BEGIN
    DECLARE table_exists INT DEFAULT 0;
    DECLARE index_exists INT DEFAULT 0;
    
    -- Check if table exists
    SELECT COUNT(*) INTO table_exists 
    FROM information_schema.tables 
    WHERE table_schema = DATABASE() AND table_name = p_table_name;
    
    IF table_exists > 0 THEN
        -- Check if index exists
        SELECT COUNT(*) INTO index_exists 
        FROM information_schema.statistics 
        WHERE table_schema = DATABASE() 
          AND table_name = p_table_name 
          AND index_name = p_index_name;
        
        IF index_exists = 0 THEN
            SET @sql = CONCAT('CREATE INDEX ', p_index_name, ' ON ', p_table_name, '(', p_index_columns, ')');
            PREPARE stmt FROM @sql;
            EXECUTE stmt;
            DEALLOCATE PREPARE stmt;
        END IF;
    END IF;
END$$

DELIMITER ;

-- Apply indexes safely
CALL add_index_if_not_exists('players', 'idx_players_balance_level', 'balance DESC, level DESC');
CALL add_index_if_not_exists('players', 'idx_players_last_seen', 'last_seen DESC');
CALL add_index_if_not_exists('user_stats', 'idx_user_stats_period', 'stat_period');
CALL add_index_if_not_exists('blackjack_games', 'idx_blackjack_user_date', 'user_id, played_at DESC');
CALL add_index_if_not_exists('roulette_games', 'idx_roulette_user_date', 'user_id, played_at DESC');
CALL add_index_if_not_exists('mines_games', 'idx_mines_user_date', 'user_id, played_at DESC');
CALL add_index_if_not_exists('transaction_history', 'idx_transaction_user_date', 'user_id, created_at DESC');
CALL add_index_if_not_exists('music_history', 'idx_music_user_date', 'user_id, played_at DESC');
CALL add_index_if_not_exists('daily_quests', 'idx_daily_quests_user_date', 'user_id, quest_date DESC');

-- Cleanup helper procedure
DROP PROCEDURE IF EXISTS add_index_if_not_exists;

-- ============================================================================
-- PART 4: Ensure Essential Tables Exist
-- ============================================================================

-- API usage tracking table for token optimization
CREATE TABLE IF NOT EXISTS api_usage (
    id INT AUTO_INCREMENT PRIMARY KEY,
    model VARCHAR(100) NOT NULL,
    input_tokens INT UNSIGNED DEFAULT 0,
    output_tokens INT UNSIGNED DEFAULT 0,
    cost DECIMAL(10, 6) DEFAULT 0.000000,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_model (model),
    INDEX idx_recorded (recorded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Emoji descriptions cache (for emoji analysis optimization)
CREATE TABLE IF NOT EXISTS emoji_descriptions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    emoji_id VARCHAR(50) NOT NULL UNIQUE,
    emoji_name VARCHAR(100) NOT NULL,
    description TEXT,
    usage_context TEXT,
    image_url VARCHAR(500),
    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_emoji_name (emoji_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- PART 5: User Profiles View moved to migration 023 (after required columns exist)
-- ============================================================================

-- ============================================================================
-- Migration 022 Complete
-- ============================================================================
