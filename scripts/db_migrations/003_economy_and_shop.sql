-- ============================================================================
-- Sulfur Bot - Economy & Shop System Database Migration
-- Version: 003
-- Description: Adds tables for economy features, shop purchases, and games
-- ============================================================================

-- User Economy Table (for tracking daily rewards, etc.)
CREATE TABLE IF NOT EXISTS user_economy (
    user_id BIGINT PRIMARY KEY,
    last_daily_claim DATETIME,
    total_earned BIGINT DEFAULT 0,
    total_spent BIGINT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Feature Unlocks Table
CREATE TABLE IF NOT EXISTS feature_unlocks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    feature_name VARCHAR(100) NOT NULL,
    purchased_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_user_feature (user_id, feature_name),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Shop Purchases Table (for tracking all purchases)
CREATE TABLE IF NOT EXISTS shop_purchases (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    item_type VARCHAR(50) NOT NULL,
    item_name VARCHAR(255) NOT NULL,
    price INT NOT NULL,
    purchased_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_item_type (item_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Daily Quests Table
CREATE TABLE IF NOT EXISTS daily_quests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    quest_date DATE NOT NULL,
    quest_type VARCHAR(50) NOT NULL,
    target_value INT NOT NULL,
    current_progress INT DEFAULT 0,
    completed BOOLEAN DEFAULT FALSE,
    reward_claimed BOOLEAN DEFAULT FALSE,
    UNIQUE KEY unique_user_quest_date (user_id, quest_date, quest_type),
    INDEX idx_user_date (user_id, quest_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Gambling Statistics Table
CREATE TABLE IF NOT EXISTS gambling_stats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    game_type VARCHAR(50) NOT NULL,
    total_games INT DEFAULT 0,
    total_wagered BIGINT DEFAULT 0,
    total_won BIGINT DEFAULT 0,
    total_lost BIGINT DEFAULT 0,
    biggest_win INT DEFAULT 0,
    biggest_loss INT DEFAULT 0,
    last_played DATETIME,
    UNIQUE KEY unique_user_game (user_id, game_type),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Transaction History Table
CREATE TABLE IF NOT EXISTS transaction_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    transaction_type VARCHAR(50) NOT NULL,
    amount INT NOT NULL,
    balance_after INT NOT NULL,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Color Roles Table (tracking purchased color roles)
CREATE TABLE IF NOT EXISTS color_roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    color_hex VARCHAR(7) NOT NULL,
    tier VARCHAR(20) NOT NULL,
    purchased_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_user_guild (user_id, guild_id),
    INDEX idx_role_id (role_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Chat Revival / Bounties Table
CREATE TABLE IF NOT EXISTS chat_bounties (
    id INT AUTO_INCREMENT PRIMARY KEY,
    channel_id BIGINT NOT NULL,
    bounty_type VARCHAR(50) NOT NULL,
    reward_amount INT NOT NULL,
    expires_at DATETIME NOT NULL,
    completed_by BIGINT,
    completed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_channel_id (channel_id),
    INDEX idx_expires_at (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Views for convenient queries
-- ============================================================================

-- View: User Economy Summary
CREATE OR REPLACE VIEW v_user_economy_summary AS
SELECT 
    us.user_id,
    us.display_name,
    us.balance,
    ue.total_earned,
    ue.total_spent,
    ue.last_daily_claim,
    (SELECT COUNT(*) FROM feature_unlocks WHERE user_id = us.user_id) as unlocked_features,
    (SELECT COUNT(*) FROM shop_purchases WHERE user_id = us.user_id) as total_purchases
FROM user_stats us
LEFT JOIN user_economy ue ON us.user_id = ue.user_id
WHERE us.stat_period = DATE_FORMAT(NOW(), '%Y-%m');

-- View: Gambling Statistics Summary
CREATE OR REPLACE VIEW v_gambling_summary AS
SELECT 
    user_id,
    SUM(total_games) as total_games,
    SUM(total_wagered) as total_wagered,
    SUM(total_won) as total_won,
    SUM(total_lost) as total_lost,
    MAX(biggest_win) as biggest_win,
    MAX(biggest_loss) as biggest_loss,
    (SUM(total_won) - SUM(total_lost)) as net_profit
FROM gambling_stats
GROUP BY user_id;

-- ============================================================================
-- MONTHLY QUEST TRACKING
-- ============================================================================

-- Table: Daily Quest Completions (tracks bonus claims)
CREATE TABLE IF NOT EXISTS daily_quest_completions (
    user_id BIGINT UNSIGNED NOT NULL,
    completion_date DATE NOT NULL,
    bonus_claimed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, completion_date),
    INDEX idx_completion_date (completion_date),
    INDEX idx_user_completions (user_id, completion_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: Monthly Milestones (tracks monthly achievement rewards)
CREATE TABLE IF NOT EXISTS monthly_milestones (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL,
    month_key VARCHAR(7) NOT NULL COMMENT 'Format: YYYY-MM',
    milestone_day INT NOT NULL COMMENT '7, 14, 21, or 30 days',
    reward_amount INT NOT NULL,
    claimed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_month (user_id, month_key),
    UNIQUE KEY unique_user_milestone (user_id, month_key, milestone_day)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Indexes for performance
-- ============================================================================

-- Add index to user_stats for balance queries if not exists
CREATE INDEX IF NOT EXISTS idx_user_stats_balance ON user_stats(stat_period, balance DESC);

-- Add index for quest queries
CREATE INDEX IF NOT EXISTS idx_daily_quests_completion ON daily_quests(user_id, quest_date, completed);

-- ============================================================================
-- Migration complete
-- ============================================================================
