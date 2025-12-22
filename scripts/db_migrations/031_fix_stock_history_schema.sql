-- ============================================================================
-- Migration 031: Fix stock_history Schema Inconsistency
-- ============================================================================
-- This migration ensures stock_history table uses stock_id (integer FK)
-- instead of stock_symbol (string FK) for better performance and consistency
-- with migration 019.
-- ============================================================================

-- Drop and recreate stock_history table with correct schema
-- Note: This will lose historical stock price data, but stock prices are
-- ephemeral and regenerated regularly, so this is acceptable.
DROP TABLE IF EXISTS stock_history;

CREATE TABLE IF NOT EXISTS stock_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock_id INT NOT NULL,
    price DECIMAL(18, 8) NOT NULL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (stock_id) REFERENCES stocks(id) ON DELETE CASCADE,
    INDEX idx_stock (stock_id),
    INDEX idx_recorded (recorded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Migration 031 Complete
-- ============================================================================
