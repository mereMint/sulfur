-- ============================================================================
-- Sulfur Bot - User Boosts Table Migration
-- Version: 021
-- Description: Adds a table to track active user boosts (e.g., XP boosts).
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_boosts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    boost_type VARCHAR(50) NOT NULL,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_active (user_id, is_active),
    INDEX idx_end_time (end_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

COMMIT;
