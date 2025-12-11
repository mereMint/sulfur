-- Migration 011: Autonomous Bot Features
-- Adds support for user preferences, focus sessions, and autonomous interactions

-- User preferences for autonomous features
CREATE TABLE IF NOT EXISTS user_autonomous_settings (
    user_id BIGINT PRIMARY KEY,
    allow_autonomous_messages BOOLEAN DEFAULT TRUE,
    allow_autonomous_calls BOOLEAN DEFAULT TRUE,
    last_autonomous_contact TIMESTAMP NULL,
    autonomous_contact_frequency VARCHAR(20) DEFAULT 'normal', -- 'low', 'normal', 'high', 'none'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_last_contact (last_autonomous_contact),
    INDEX idx_frequency (autonomous_contact_frequency)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Focus sessions tracking
CREATE TABLE IF NOT EXISTS focus_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    session_type VARCHAR(20) NOT NULL, -- 'pomodoro', 'custom'
    duration_minutes INT NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NULL,
    completed BOOLEAN DEFAULT FALSE,
    distractions_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_active (user_id, completed),
    INDEX idx_end_time (end_time),
    INDEX idx_guild (guild_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Focus session distractions log
CREATE TABLE IF NOT EXISTS focus_distractions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id INT NOT NULL,
    user_id BIGINT NOT NULL,
    distraction_type VARCHAR(50) NOT NULL, -- 'message', 'game', 'video', 'other'
    distraction_details TEXT NULL,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES focus_sessions(id) ON DELETE CASCADE,
    INDEX idx_session (session_id),
    INDEX idx_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Bot autonomous actions log (for tracking and learning)
CREATE TABLE IF NOT EXISTS bot_autonomous_actions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    action_type VARCHAR(50) NOT NULL, -- 'dm_message', 'voice_call', 'focus_reminder'
    target_user_id BIGINT NOT NULL,
    guild_id BIGINT NULL,
    action_reason TEXT NULL,
    context_data JSON NULL,
    success BOOLEAN DEFAULT TRUE,
    user_response BOOLEAN NULL, -- Did user respond?
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (target_user_id),
    INDEX idx_action_type (action_type),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Voice conversation transcripts
CREATE TABLE IF NOT EXISTS voice_conversations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    session_start TIMESTAMP NOT NULL,
    session_end TIMESTAMP NULL,
    initiated_by VARCHAR(20) NOT NULL, -- 'bot', 'user'
    participant_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_guild (guild_id),
    INDEX idx_session (session_start, session_end)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Individual voice messages in conversations
CREATE TABLE IF NOT EXISTS voice_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    conversation_id INT NOT NULL,
    user_id BIGINT NOT NULL,
    speaker_name VARCHAR(255) NOT NULL,
    transcript TEXT NOT NULL,
    confidence FLOAT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES voice_conversations(id) ON DELETE CASCADE,
    INDEX idx_conversation (conversation_id),
    INDEX idx_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Enhanced user memory for autonomous decision making
CREATE TABLE IF NOT EXISTS user_memory_enhanced (
    user_id BIGINT PRIMARY KEY,
    interests JSON NULL, -- Array of interests extracted from conversations
    usual_active_times JSON NULL, -- When user is typically online
    response_patterns JSON NULL, -- How user typically responds
    conversation_topics JSON NULL, -- Recent conversation topics
    last_significant_interaction TIMESTAMP NULL,
    interaction_frequency FLOAT DEFAULT 0.0, -- Messages per day average
    preferred_contact_method VARCHAR(20) DEFAULT 'text', -- 'text', 'voice', 'either'
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_last_interaction (last_significant_interaction)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Temporary DM access bypass (when bot autonomously messages a user)
CREATE TABLE IF NOT EXISTS temp_dm_access (
    user_id BIGINT PRIMARY KEY,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    granted_by VARCHAR(20) DEFAULT 'autonomous_message',
    INDEX idx_expires (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Default settings for existing users
-- This will only run if the 'users' or 'user_stats' table exists
-- If neither exists, the settings will be created on first user interaction
INSERT IGNORE INTO user_autonomous_settings (user_id, allow_autonomous_messages, allow_autonomous_calls)
SELECT DISTINCT user_id, TRUE, TRUE FROM user_stats WHERE user_id IS NOT NULL
ON DUPLICATE KEY UPDATE user_id = user_id;
