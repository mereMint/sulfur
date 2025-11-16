-- Migration: Add Wrapped Opt-In System
-- Date: 2025-11-16
-- Description: Creates table to track users who want to receive Wrapped summaries

CREATE TABLE IF NOT EXISTS wrapped_registrations (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    opted_out BOOLEAN DEFAULT FALSE,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_opted_out (opted_out),
    INDEX idx_registered_at (registered_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Note: Users must explicitly opt-in to receive Wrapped summaries
-- By default, no users are registered (empty table)
