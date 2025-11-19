-- ============================================================
-- Detective Game Cases and Progress Tables
-- ============================================================
-- This migration adds tables to store detective game cases
-- and track user progress with difficulty progression
-- ============================================================

-- Table to store generated detective cases
CREATE TABLE IF NOT EXISTS detective_cases (
    case_id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    location VARCHAR(255) NOT NULL,
    victim VARCHAR(255) NOT NULL,
    suspects JSON NOT NULL COMMENT 'Array of suspect objects',
    murderer_index INT NOT NULL,
    evidence JSON NOT NULL COMMENT 'Array of evidence items',
    hints JSON NOT NULL COMMENT 'Array of hint strings',
    difficulty INT NOT NULL DEFAULT 1 COMMENT 'Difficulty level (1-5)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_difficulty (difficulty),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table to track user progress and completions
CREATE TABLE IF NOT EXISTS detective_user_progress (
    user_id BIGINT UNSIGNED NOT NULL,
    case_id INT NOT NULL,
    completed BOOLEAN DEFAULT FALSE,
    solved BOOLEAN DEFAULT FALSE COMMENT 'Whether they correctly identified the murderer',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    PRIMARY KEY (user_id, case_id),
    FOREIGN KEY (case_id) REFERENCES detective_cases(case_id) ON DELETE CASCADE,
    INDEX idx_user_completed (user_id, completed),
    INDEX idx_user_solved (user_id, solved)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table to track user's current difficulty level
CREATE TABLE IF NOT EXISTS detective_user_stats (
    user_id BIGINT UNSIGNED PRIMARY KEY,
    current_difficulty INT NOT NULL DEFAULT 1 COMMENT 'Current difficulty level (1-5)',
    cases_solved INT NOT NULL DEFAULT 0,
    cases_failed INT NOT NULL DEFAULT 0,
    total_cases_played INT NOT NULL DEFAULT 0,
    last_played_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_difficulty (current_difficulty)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
