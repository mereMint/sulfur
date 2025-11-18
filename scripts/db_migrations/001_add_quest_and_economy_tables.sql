-- ============================================================
-- Migration: Add Quest System and Economy Tables
-- Date: 2025-11-18
-- Description: Creates tables for daily quests, user economy, and user stats
-- ============================================================

-- Table for tracking daily quests
CREATE TABLE IF NOT EXISTS daily_quests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    quest_date DATE NOT NULL,
    quest_type VARCHAR(50) NOT NULL,
    target_value INT NOT NULL,
    current_progress INT NOT NULL DEFAULT 0,
    completed BOOLEAN NOT NULL DEFAULT FALSE,
    reward_claimed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_date (user_id, quest_date),
    INDEX idx_user_type_date (user_id, quest_type, quest_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table for user economy data (daily rewards, etc.)
CREATE TABLE IF NOT EXISTS user_economy (
    user_id BIGINT PRIMARY KEY,
    last_daily_claim TIMESTAMP NULL,
    total_earned BIGINT NOT NULL DEFAULT 0,
    total_spent BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table for user stats by period (monthly tracking)
CREATE TABLE IF NOT EXISTS user_stats (
    user_id BIGINT NOT NULL,
    stat_period VARCHAR(7) NOT NULL,  -- Format: YYYY-MM
    balance BIGINT NOT NULL DEFAULT 0,
    messages_sent INT NOT NULL DEFAULT 0,
    voice_minutes INT NOT NULL DEFAULT 0,
    quests_completed INT NOT NULL DEFAULT 0,
    games_played INT NOT NULL DEFAULT 0,
    games_won INT NOT NULL DEFAULT 0,
    total_bet INT NOT NULL DEFAULT 0,
    total_won INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, stat_period),
    INDEX idx_period (stat_period)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table for monthly quest completion tracking
CREATE TABLE IF NOT EXISTS monthly_quest_completion (
    user_id BIGINT NOT NULL,
    completion_date DATE NOT NULL,
    bonus_claimed BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (user_id, completion_date),
    INDEX idx_user_month (user_id, completion_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Update ai_model_usage table if it doesn't have cost column
ALTER TABLE ai_model_usage
ADD COLUMN IF NOT EXISTS cost_usd DECIMAL(10, 6) DEFAULT 0 AFTER output_tokens;

COMMIT;
