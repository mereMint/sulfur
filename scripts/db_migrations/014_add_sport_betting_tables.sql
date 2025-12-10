-- Migration: Add Sport Betting Tables
-- Description: Creates tables for the sport betting system including matches, bets, stats, and bet pools

-- Table for cached matches from football APIs
CREATE TABLE IF NOT EXISTS sport_matches (
    match_id VARCHAR(64) PRIMARY KEY,
    league_id VARCHAR(32) NOT NULL,
    provider VARCHAR(32) NOT NULL,
    home_team VARCHAR(128) NOT NULL,
    away_team VARCHAR(128) NOT NULL,
    home_team_short VARCHAR(16),
    away_team_short VARCHAR(16),
    home_score INT DEFAULT 0,
    away_score INT DEFAULT 0,
    status VARCHAR(32) NOT NULL DEFAULT 'scheduled',
    match_time DATETIME NOT NULL,
    matchday INT DEFAULT 1,
    odds_home DECIMAL(5,2) DEFAULT 2.00,
    odds_draw DECIMAL(5,2) DEFAULT 3.50,
    odds_away DECIMAL(5,2) DEFAULT 3.00,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_league (league_id),
    INDEX idx_status (status),
    INDEX idx_match_time (match_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table for user bets
CREATE TABLE IF NOT EXISTS sport_bets (
    bet_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    match_id VARCHAR(64) NOT NULL,
    bet_type VARCHAR(32) NOT NULL,
    bet_outcome VARCHAR(32) NOT NULL,
    bet_amount BIGINT NOT NULL,
    odds_at_bet DECIMAL(5,2) NOT NULL,
    potential_payout BIGINT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    actual_payout BIGINT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    settled_at TIMESTAMP NULL,
    INDEX idx_user (user_id),
    INDEX idx_match (match_id),
    INDEX idx_status (status),
    INDEX idx_created (created_at),
    FOREIGN KEY (match_id) REFERENCES sport_matches(match_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table for user betting statistics
CREATE TABLE IF NOT EXISTS sport_betting_stats (
    user_id BIGINT PRIMARY KEY,
    total_bets INT DEFAULT 0,
    total_wins INT DEFAULT 0,
    total_losses INT DEFAULT 0,
    total_wagered BIGINT DEFAULT 0,
    total_won BIGINT DEFAULT 0,
    total_lost BIGINT DEFAULT 0,
    biggest_win BIGINT DEFAULT 0,
    current_streak INT DEFAULT 0,
    best_streak INT DEFAULT 0,
    favorite_league VARCHAR(32),
    last_bet_at TIMESTAMP NULL,
    INDEX idx_wins (total_wins),
    INDEX idx_wagered (total_wagered)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table for match bet pools (for dynamic odds calculation)
CREATE TABLE IF NOT EXISTS sport_bet_pools (
    match_id VARCHAR(64) PRIMARY KEY,
    pool_home BIGINT DEFAULT 0,
    pool_draw BIGINT DEFAULT 0,
    pool_away BIGINT DEFAULT 0,
    total_bettors INT DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (match_id) REFERENCES sport_matches(match_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
