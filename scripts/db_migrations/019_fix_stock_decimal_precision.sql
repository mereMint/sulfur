-- Migration 019: Fix stock market decimal precision for crypto prices
-- This migration updates the stocks, user_portfolios, and stock_history tables
-- to use DECIMAL(18, 8) for prices to handle crypto with small values (e.g., SHIB at 0.000025)

-- Create stocks table if it doesn't exist (with correct precision from the start)
CREATE TABLE IF NOT EXISTS stocks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    current_price DECIMAL(18, 8) NOT NULL DEFAULT 100.00000000,
    previous_price DECIMAL(18, 8) NOT NULL DEFAULT 100.00000000,
    trend DECIMAL(6, 5) DEFAULT 0.00000,
    game_influence_factor DECIMAL(6, 5) DEFAULT 0.00000,
    sector VARCHAR(50) DEFAULT 'general',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_symbol (symbol),
    INDEX idx_sector (sector)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create user_portfolios table if it doesn't exist
CREATE TABLE IF NOT EXISTS user_portfolios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL,
    stock_id INT NOT NULL,
    shares DECIMAL(18, 8) NOT NULL DEFAULT 0,
    avg_buy_price DECIMAL(18, 8) NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_user_stock (user_id, stock_id),
    INDEX idx_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create stock_history table if it doesn't exist
CREATE TABLE IF NOT EXISTS stock_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock_id INT NOT NULL,
    price DECIMAL(18, 8) NOT NULL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_stock (stock_id),
    INDEX idx_recorded (recorded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- End of migration
