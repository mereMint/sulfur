-- ============================================================================
-- Migration 025: Add minecraft_players table for player tracking
-- ============================================================================
-- This migration creates a table to track Minecraft player statistics
-- including playtime, sessions, and activity

-- Create minecraft_players table if it doesn't exist
CREATE TABLE IF NOT EXISTS minecraft_players (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(32) NOT NULL UNIQUE,
    uuid VARCHAR(36) NULL,
    discord_id BIGINT UNSIGNED NULL,
    playtime_minutes INT UNSIGNED DEFAULT 0,
    sessions INT UNSIGNED DEFAULT 0,
    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_session_start DATETIME NULL,
    is_online BOOLEAN DEFAULT FALSE,
    peak_concurrent INT UNSIGNED DEFAULT 1,
    INDEX idx_username (username),
    INDEX idx_discord_id (discord_id),
    INDEX idx_last_seen (last_seen DESC),
    INDEX idx_playtime (playtime_minutes DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create minecraft_sessions table for detailed session tracking
CREATE TABLE IF NOT EXISTS minecraft_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    player_id INT NOT NULL,
    session_start DATETIME NOT NULL,
    session_end DATETIME NULL,
    duration_minutes INT UNSIGNED DEFAULT 0,
    FOREIGN KEY (player_id) REFERENCES minecraft_players(id) ON DELETE CASCADE,
    INDEX idx_player_id (player_id),
    INDEX idx_session_start (session_start DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Migration 025 Complete
-- ============================================================================
