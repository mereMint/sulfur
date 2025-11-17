-- Create base user_stats table if missing
CREATE TABLE IF NOT EXISTS user_stats (
    user_id BIGINT UNSIGNED NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    stat_period VARCHAR(7) NOT NULL COMMENT 'YYYY-MM format',
    message_count INT UNSIGNED DEFAULT 0,
    total_reactions INT UNSIGNED DEFAULT 0,
    conversation_count INT UNSIGNED DEFAULT 0,
    balance INT DEFAULT 0,
    last_daily_claim TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, stat_period),
    INDEX idx_user_id (user_id),
    INDEX idx_stat_period (stat_period)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
