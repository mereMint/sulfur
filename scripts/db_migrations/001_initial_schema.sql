-- ============================================================================
-- Sulfur Bot - Initial Database Schema
-- Version: 001
-- Description: Creates base tables for user statistics and core features
-- ============================================================================

-- User Statistics Table (base table for tracking user activity)
CREATE TABLE IF NOT EXISTS user_stats (
    user_id BIGINT UNSIGNED NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    stat_period VARCHAR(7) NOT NULL COMMENT 'YYYY-MM format for monthly stats',
    message_count INT UNSIGNED DEFAULT 0,
    total_reactions INT UNSIGNED DEFAULT 0,
    conversation_count INT UNSIGNED DEFAULT 0,
    balance INT DEFAULT 0,
    last_daily_claim TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, stat_period),
    INDEX idx_user_id (user_id),
    INDEX idx_stat_period (stat_period),
    INDEX idx_balance (balance DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Conversation Context Table (for AI chat context)
CREATE TABLE IF NOT EXISTS conversation_context (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    message_content TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_channel (user_id, channel_id),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- User Relationships Table (for tracking user interactions)
CREATE TABLE IF NOT EXISTS user_relationships (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    other_user_id BIGINT NOT NULL,
    interaction_count INT DEFAULT 0,
    last_interaction DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_relationship (user_id, other_user_id),
    INDEX idx_user (user_id),
    INDEX idx_interaction (last_interaction)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Migration complete
-- ============================================================================
