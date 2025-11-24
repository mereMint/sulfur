-- Migration: Add missing game statistics tables
-- This migration adds tables for various game types that are referenced by the web dashboard
-- but were not created in the initial schema.

-- ============================================================================
-- Werwolf Game Stats
-- ============================================================================
CREATE TABLE IF NOT EXISTS werwolf_user_stats (
    user_id BIGINT NOT NULL,
    total_games INT DEFAULT 0 NOT NULL,
    games_won INT DEFAULT 0 NOT NULL,
    games_lost INT DEFAULT 0 NOT NULL,
    times_werewolf INT DEFAULT 0 NOT NULL,
    times_villager INT DEFAULT 0 NOT NULL,
    times_seer INT DEFAULT 0 NOT NULL,
    times_doctor INT DEFAULT 0 NOT NULL,
    last_played_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id),
    INDEX idx_total_games (total_games),
    INDEX idx_last_played (last_played_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Wordle Game Stats
-- ============================================================================
CREATE TABLE IF NOT EXISTS wordle_games (
    game_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    word VARCHAR(10) NOT NULL,
    attempts INT NOT NULL,
    completed BOOLEAN DEFAULT FALSE NOT NULL,
    won BOOLEAN DEFAULT FALSE NOT NULL,
    guesses JSON NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    INDEX idx_user_id (user_id),
    INDEX idx_completed (completed),
    INDEX idx_won (won)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Casino Games Stats
-- ============================================================================

-- Blackjack
CREATE TABLE IF NOT EXISTS blackjack_games (
    game_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    bet_amount BIGINT NOT NULL,
    won_amount BIGINT DEFAULT 0 NOT NULL,
    player_hand JSON NOT NULL,
    dealer_hand JSON NOT NULL,
    result VARCHAR(20) NOT NULL,
    played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_played_at (played_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Roulette
CREATE TABLE IF NOT EXISTS roulette_games (
    game_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    bet_amount BIGINT NOT NULL,
    bet_type VARCHAR(20) NOT NULL,
    bet_value VARCHAR(20) NOT NULL,
    winning_number INT NOT NULL,
    won_amount BIGINT DEFAULT 0 NOT NULL,
    played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_played_at (played_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Mines (Minesweeper)
CREATE TABLE IF NOT EXISTS mines_games (
    game_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    bet_amount BIGINT NOT NULL,
    grid_size INT DEFAULT 5 NOT NULL,
    mine_count INT DEFAULT 3 NOT NULL,
    tiles_revealed INT DEFAULT 0 NOT NULL,
    won_amount BIGINT DEFAULT 0 NOT NULL,
    result VARCHAR(20) NOT NULL,
    played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_played_at (played_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Russian Roulette
CREATE TABLE IF NOT EXISTS russian_roulette_games (
    game_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    bet_amount BIGINT NOT NULL,
    chamber_position INT NOT NULL,
    survived BOOLEAN NOT NULL,
    won_amount BIGINT DEFAULT 0 NOT NULL,
    played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_played_at (played_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Horse Racing
CREATE TABLE IF NOT EXISTS horse_racing_games (
    game_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    bet_amount BIGINT NOT NULL,
    horse_number INT NOT NULL,
    winning_horse INT NOT NULL,
    won_amount BIGINT DEFAULT 0 NOT NULL,
    played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_played_at (played_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Trolly Problem Choices (alias for compatibility)
-- ============================================================================
-- Note: The actual table is `trolly_responses` created in db_helpers.py
-- This creates an alias/view for web dashboard compatibility
CREATE OR REPLACE VIEW trolly_problem_choices AS
SELECT 
    response_id as id,
    user_id,
    problem_id,
    scenario_summary,
    chosen_option,
    responded_at
FROM trolly_responses;

-- ============================================================================
-- Detective Games (alias for compatibility)
-- ============================================================================
-- Note: The actual table is `detective_cases` created in db_helpers.py
-- This creates an alias/view for web dashboard compatibility
CREATE OR REPLACE VIEW detective_games AS
SELECT 
    case_id as game_id,
    title,
    description,
    difficulty,
    created_at
FROM detective_cases;

-- ============================================================================
-- Word Find Tables
-- ============================================================================
CREATE TABLE IF NOT EXISTS word_find_daily (
    id INT AUTO_INCREMENT PRIMARY KEY,
    puzzle_date DATE NOT NULL UNIQUE,
    grid JSON NOT NULL,
    words JSON NOT NULL,
    difficulty INT DEFAULT 1 NOT NULL,
    language VARCHAR(2) DEFAULT 'de' NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_date (puzzle_date),
    INDEX idx_language (language)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS word_find_user_progress (
    user_id BIGINT NOT NULL,
    puzzle_date DATE NOT NULL,
    words_found JSON NULL,
    completed BOOLEAN DEFAULT FALSE NOT NULL,
    completion_time INT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    PRIMARY KEY (user_id, puzzle_date),
    INDEX idx_user_id (user_id),
    INDEX idx_completed (completed)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS word_find_user_stats (
    user_id BIGINT PRIMARY KEY,
    total_completed INT DEFAULT 0 NOT NULL,
    current_streak INT DEFAULT 0 NOT NULL,
    longest_streak INT DEFAULT 0 NOT NULL,
    average_time INT NULL,
    best_time INT NULL,
    last_played_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Gambling Stats Table (if not exists)
-- ============================================================================
CREATE TABLE IF NOT EXISTS gambling_stats (
    user_id BIGINT NOT NULL,
    game_type VARCHAR(50) NOT NULL,
    total_games INT DEFAULT 0 NOT NULL,
    total_wagered BIGINT DEFAULT 0 NOT NULL,
    total_won BIGINT DEFAULT 0 NOT NULL,
    total_lost BIGINT DEFAULT 0 NOT NULL,
    biggest_win BIGINT DEFAULT 0 NOT NULL,
    biggest_loss BIGINT DEFAULT 0 NOT NULL,
    last_played TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, game_type),
    INDEX idx_user_id (user_id),
    INDEX idx_game_type (game_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- End of Migration
-- ============================================================================
