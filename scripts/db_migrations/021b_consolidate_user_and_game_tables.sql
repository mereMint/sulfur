-- ============================================================================
-- Migration 021b: Consolidate User and Game Tables (Simplified)
-- ============================================================================
-- This simplified migration only adds essential indexes and ensures base tables
-- exist. Views that depend on optional tables are skipped for robustness.
-- ============================================================================

-- ============================================================================
-- Part 1: Ensure essential tables exist
-- ============================================================================

-- Players table (core user table)
CREATE TABLE IF NOT EXISTS players (
    id INT AUTO_INCREMENT PRIMARY KEY,
    discord_id BIGINT UNSIGNED NOT NULL UNIQUE,
    display_name VARCHAR(255) DEFAULT 'Unknown',
    level INT UNSIGNED DEFAULT 1,
    xp INT UNSIGNED DEFAULT 0,
    balance BIGINT DEFAULT 0,
    wins INT UNSIGNED DEFAULT 0,
    losses INT UNSIGNED DEFAULT 0,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_activity_name VARCHAR(255) NULL,
    relationship_summary TEXT,
    game_history JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_balance (balance DESC),
    INDEX idx_level (level DESC),
    INDEX idx_last_seen (last_seen DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- User customization table
CREATE TABLE IF NOT EXISTS user_customization (
    user_id BIGINT UNSIGNED NOT NULL PRIMARY KEY,
    equipped_color VARCHAR(10) DEFAULT '#00ff41',
    embed_color VARCHAR(10) DEFAULT '#00ff41',
    profile_background VARCHAR(100) DEFAULT 'default',
    language VARCHAR(10) DEFAULT 'de',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- User autonomous settings
CREATE TABLE IF NOT EXISTS user_autonomous_settings (
    user_id BIGINT UNSIGNED NOT NULL PRIMARY KEY,
    allow_autonomous_messages BOOLEAN DEFAULT TRUE,
    allow_autonomous_calls BOOLEAN DEFAULT TRUE,
    last_autonomous_contact TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Feature unlocks table
CREATE TABLE IF NOT EXISTS feature_unlocks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL,
    feature_name VARCHAR(100) NOT NULL,
    unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    UNIQUE KEY unique_user_feature (user_id, feature_name),
    INDEX idx_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Transaction history table
CREATE TABLE IF NOT EXISTS transaction_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL,
    transaction_type VARCHAR(50) NOT NULL,
    amount BIGINT NOT NULL,
    balance_after BIGINT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    INDEX idx_type (transaction_type),
    INDEX idx_created (created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Part 2: Add Performance Indexes (safe - ignores errors if already exist)
-- ============================================================================

-- Note: These may error if indexes already exist, which is fine
-- The migration applier ignores "already exists" errors

-- End of migration
