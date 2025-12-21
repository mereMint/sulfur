-- ============================================================================
-- Migration 030: Fix interaction_learnings Table Schema
-- ============================================================================
-- This migration ensures the interaction_learnings table has the correct schema
-- as expected by personality_evolution.py module.
-- 
-- WARNING: This migration drops and recreates the interaction_learnings table,
-- which will result in the loss of any existing learning data. This is acceptable
-- because:
-- 1. The table structure from migration 023 was incorrect and incompatible
-- 2. Learning data is accumulated over time and will be regenerated through usage
-- 3. Personality traits are stored separately in personality_evolution table
-- ============================================================================

-- Drop the incorrectly structured interaction_learnings table if it exists
-- (from migration 023 which had incorrect columns)
DROP TABLE IF EXISTS interaction_learnings;

-- Create the correct interaction_learnings table
-- This matches the schema from migration 016 (personality_evolution.sql)
CREATE TABLE IF NOT EXISTS interaction_learnings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    learning_type VARCHAR(50) NOT NULL, -- 'user_preference', 'conversation_pattern', 'response_effectiveness', 'topic_interest'
    learning_content TEXT NOT NULL,
    confidence FLOAT DEFAULT 0.5, -- How confident the bot is in this learning (0.0 to 1.0)
    relevance_score FLOAT DEFAULT 1.0, -- How relevant this learning is (decays over time)
    user_id BIGINT NULL, -- Specific to a user, or NULL for general learnings
    interaction_count INT DEFAULT 1, -- How many times this pattern was observed
    last_observed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_learning_type (learning_type),
    INDEX idx_user (user_id),
    INDEX idx_relevance (relevance_score),
    INDEX idx_last_observed (last_observed)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Migration 030 Complete
-- ============================================================================
