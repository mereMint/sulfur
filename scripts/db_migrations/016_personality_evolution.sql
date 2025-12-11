-- Migration 016: Personality Evolution System
-- Adds support for AI personality learning and evolution based on interactions

-- Personality evolution tracking
CREATE TABLE IF NOT EXISTS personality_evolution (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trait_name VARCHAR(50) NOT NULL,
    trait_value FLOAT NOT NULL,
    reason TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_trait (trait_name),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Interaction learning history
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

-- Memory consolidation (long-term semantic memory)
CREATE TABLE IF NOT EXISTS semantic_memory (
    id INT AUTO_INCREMENT PRIMARY KEY,
    memory_type VARCHAR(50) NOT NULL, -- 'fact', 'preference', 'relationship', 'event', 'insight'
    memory_content TEXT NOT NULL,
    importance FLOAT DEFAULT 0.5, -- 0.0 to 1.0
    context JSON NULL, -- Additional context data
    access_count INT DEFAULT 0, -- How often this memory was accessed
    last_accessed TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_memory_type (memory_type),
    INDEX idx_importance (importance),
    INDEX idx_access_count (access_count),
    INDEX idx_last_accessed (last_accessed)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Reflection sessions (bot's self-analysis)
CREATE TABLE IF NOT EXISTS reflection_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    reflection_content TEXT NOT NULL, -- What the bot reflected on
    insights_generated JSON NULL, -- Key insights from reflection
    personality_adjustments JSON NULL, -- Any personality changes made
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Conversation quality feedback (implicit learning from user reactions)
CREATE TABLE IF NOT EXISTS conversation_feedback (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    message_id BIGINT NOT NULL, -- Discord message ID
    feedback_type VARCHAR(50) NOT NULL, -- 'reaction', 'reply', 'ignore', 'continuation'
    feedback_value INT DEFAULT 0, -- Positive/negative score
    context JSON NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    INDEX idx_feedback_type (feedback_type),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert initial personality traits from bot_mind.py defaults
INSERT IGNORE INTO personality_evolution (trait_name, trait_value, reason) VALUES
('sarcasm', 0.7, 'Initial default value'),
('curiosity', 0.8, 'Initial default value'),
('helpfulness', 0.6, 'Initial default value'),
('mischief', 0.5, 'Initial default value'),
('judgment', 0.9, 'Initial default value'),
('creativity', 0.7, 'Initial default value'),
('empathy', 0.4, 'Initial default value'),
('playfulness', 0.8, 'Initial default value');
