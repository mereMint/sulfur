-- Database migrations for advanced AI and voice call features
-- Run this script to add necessary tables

-- Voice call statistics table
CREATE TABLE IF NOT EXISTS voice_call_stats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    duration_seconds INT NOT NULL DEFAULT 0,
    reason VARCHAR(50) DEFAULT 'normal',
    started_at DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Enhanced AI usage logging (if not exists)
CREATE TABLE IF NOT EXISTS api_usage_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    input_tokens INT NOT NULL DEFAULT 0,
    output_tokens INT NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_model (model_name),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Conversation context table (enhanced)
CREATE TABLE IF NOT EXISTS conversation_context (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    message_content TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_channel (user_id, channel_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Personality evolution tracking
CREATE TABLE IF NOT EXISTS personality_evolution (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trait_name VARCHAR(50) NOT NULL,
    trait_value FLOAT NOT NULL,
    reason TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_trait (trait_name),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Interaction learnings
CREATE TABLE IF NOT EXISTS interaction_learnings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    learning_type VARCHAR(100) NOT NULL,
    learning_content TEXT NOT NULL,
    user_id BIGINT NULL,
    confidence FLOAT DEFAULT 0.5,
    interaction_count INT DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_type (learning_type),
    INDEX idx_user (user_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Bot autonomous actions tracking
CREATE TABLE IF NOT EXISTS bot_autonomous_actions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    action_type VARCHAR(50) NOT NULL,
    target_user_id BIGINT,
    success BOOLEAN DEFAULT TRUE,
    details TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_action_type (action_type),
    INDEX idx_user (target_user_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- User autonomous settings
CREATE TABLE IF NOT EXISTS user_autonomous_settings (
    user_id BIGINT PRIMARY KEY,
    allow_autonomous_messages BOOLEAN DEFAULT TRUE,
    allow_autonomous_calls BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Add indexes for better performance
ALTER TABLE api_usage_log ADD INDEX IF NOT EXISTS idx_model_created (model_name, created_at);
ALTER TABLE conversation_context ADD INDEX IF NOT EXISTS idx_channel_created (channel_id, created_at);
ALTER TABLE personality_evolution ADD INDEX IF NOT EXISTS idx_trait_created (trait_name, created_at);

-- Display success message
SELECT 'Advanced AI and Voice Call tables created successfully!' as Status;
