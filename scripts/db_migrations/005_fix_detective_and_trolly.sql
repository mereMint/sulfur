-- ============================================================
-- Fix Detective Game and Add Trolly Problem Tables
-- ============================================================
-- This migration:
-- 1. Adds case_hash to detective_cases for uniqueness checking
-- 2. Adds cases_at_current_difficulty to detective_user_stats
-- 3. Creates trolly_problems table to store generated problems
-- 4. Adds scenario_hash to trolly_problems for uniqueness
-- ============================================================

-- Use a stored procedure to safely add columns
DELIMITER $$

-- Procedure to add case_hash column to detective_cases
DROP PROCEDURE IF EXISTS add_case_hash_column$$
CREATE PROCEDURE add_case_hash_column()
BEGIN
    IF NOT EXISTS (
        SELECT * FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() 
        AND TABLE_NAME = 'detective_cases' 
        AND COLUMN_NAME = 'case_hash'
    ) THEN
        ALTER TABLE detective_cases 
        ADD COLUMN case_hash VARCHAR(64) UNIQUE COMMENT 'SHA256 hash for uniqueness checking',
        ADD INDEX idx_case_hash (case_hash);
    END IF;
END$$

-- Procedure to add cases_at_current_difficulty column
DROP PROCEDURE IF EXISTS add_difficulty_progress_column$$
CREATE PROCEDURE add_difficulty_progress_column()
BEGIN
    IF NOT EXISTS (
        SELECT * FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() 
        AND TABLE_NAME = 'detective_user_stats' 
        AND COLUMN_NAME = 'cases_at_current_difficulty'
    ) THEN
        ALTER TABLE detective_user_stats 
        ADD COLUMN cases_at_current_difficulty INT NOT NULL DEFAULT 0 COMMENT 'Cases solved at current difficulty level';
    END IF;
END$$

-- Procedure to add problem_id column to trolly_responses
DROP PROCEDURE IF EXISTS add_problem_id_column$$
CREATE PROCEDURE add_problem_id_column()
BEGIN
    IF NOT EXISTS (
        SELECT * FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() 
        AND TABLE_NAME = 'trolly_responses' 
        AND COLUMN_NAME = 'problem_id'
    ) THEN
        ALTER TABLE trolly_responses 
        ADD COLUMN problem_id INT NULL COMMENT 'References trolly_problems table',
        ADD INDEX idx_problem_id (problem_id);
    END IF;
END$$

DELIMITER ;

-- Execute the procedures
CALL add_case_hash_column();
CALL add_difficulty_progress_column();
CALL add_problem_id_column();

-- Drop the procedures after use
DROP PROCEDURE IF EXISTS add_case_hash_column;
DROP PROCEDURE IF EXISTS add_difficulty_progress_column;
DROP PROCEDURE IF EXISTS add_problem_id_column;

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

-- Note: We don't add a foreign key constraint because existing responses may not have a problem_id
