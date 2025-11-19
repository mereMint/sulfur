-- ============================================================
-- Fix Detective Game and Add Trolly Problem Tables
-- ============================================================
-- This migration:
-- 1. Adds case_hash to detective_cases for uniqueness checking
-- 2. Adds cases_at_current_difficulty to detective_user_stats
-- 3. Creates trolly_problems table to store generated problems
-- 4. Adds scenario_hash to trolly_problems for uniqueness
-- ============================================================

-- Add case_hash column to detective_cases if it doesn't exist
ALTER TABLE detective_cases 
ADD COLUMN IF NOT EXISTS case_hash VARCHAR(64) UNIQUE COMMENT 'SHA256 hash for uniqueness checking',
ADD INDEX IF NOT EXISTS idx_case_hash (case_hash);

-- Add cases_at_current_difficulty column to detective_user_stats if it doesn't exist
ALTER TABLE detective_user_stats 
ADD COLUMN IF NOT EXISTS cases_at_current_difficulty INT NOT NULL DEFAULT 0 COMMENT 'Cases solved at current difficulty level';

-- Table to store generated trolly problems for reuse
CREATE TABLE IF NOT EXISTS trolly_problems (
    problem_id INT AUTO_INCREMENT PRIMARY KEY,
    scenario TEXT NOT NULL COMMENT 'The trolly problem scenario',
    option_a VARCHAR(255) NOT NULL COMMENT 'First choice option',
    option_b VARCHAR(255) NOT NULL COMMENT 'Second choice option',
    scenario_hash VARCHAR(64) UNIQUE COMMENT 'SHA256 hash for uniqueness checking',
    times_presented INT NOT NULL DEFAULT 0 COMMENT 'How many times this problem has been shown',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP NULL,
    INDEX idx_scenario_hash (scenario_hash),
    INDEX idx_times_presented (times_presented),
    INDEX idx_last_used (last_used_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Update existing trolly_responses to add problem_id foreign key
ALTER TABLE trolly_responses 
ADD COLUMN IF NOT EXISTS problem_id INT NULL COMMENT 'References trolly_problems table',
ADD INDEX IF NOT EXISTS idx_problem_id (problem_id);

-- Note: We don't add a foreign key constraint because existing responses may not have a problem_id
