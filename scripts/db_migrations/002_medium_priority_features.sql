-- Database migration for medium priority features
-- Run date: 2025-11-16

-- Wrapped opt-in tracking
CREATE TABLE IF NOT EXISTS wrapped_registrations (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    opted_out BOOLEAN DEFAULT FALSE,
    INDEX idx_opted_out (opted_out)
);

-- Emoji descriptions cache
CREATE TABLE IF NOT EXISTS emoji_descriptions (
    emoji_id VARCHAR(100) PRIMARY KEY,
    emoji_name VARCHAR(100),
    description TEXT,
    usage_context TEXT,
    image_url TEXT,
    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_analyzed_at (analyzed_at)
);

-- Conversation context tracking
CREATE TABLE IF NOT EXISTS conversation_context (
    user_id BIGINT,
    channel_id BIGINT,
    last_bot_message_at TIMESTAMP,
    last_user_message TEXT,
    last_bot_response TEXT,
    context_data JSON,
    PRIMARY KEY (user_id, channel_id),
    INDEX idx_last_message (last_bot_message_at)
);

-- AI model usage tracking (enhanced)
CREATE TABLE IF NOT EXISTS ai_model_usage (
    id INT AUTO_INCREMENT PRIMARY KEY,
    model_name VARCHAR(100),
    feature VARCHAR(50),
    call_count INT DEFAULT 0,
    input_tokens INT DEFAULT 0,
    output_tokens INT DEFAULT 0,
    total_cost DECIMAL(10, 4) DEFAULT 0.0000,
    usage_date DATE,
    UNIQUE KEY unique_model_date (model_name, feature, usage_date),
    INDEX idx_usage_date (usage_date)
);
