-- Migration 019: Fix stock market decimal precision for crypto prices
-- This migration updates the stocks, user_portfolios, and stock_history tables
-- to use DECIMAL(18, 8) for prices to handle crypto with small values (e.g., SHIB at 0.000025)

-- Update stocks table
ALTER TABLE stocks 
    MODIFY COLUMN current_price DECIMAL(18, 8) NOT NULL,
    MODIFY COLUMN previous_price DECIMAL(18, 8) NOT NULL,
    MODIFY COLUMN trend DECIMAL(6, 5) DEFAULT 0,
    MODIFY COLUMN game_influence_factor DECIMAL(6, 5) DEFAULT 0;

-- Update user_portfolios table
ALTER TABLE user_portfolios 
    MODIFY COLUMN avg_buy_price DECIMAL(18, 8) NOT NULL;

-- Update stock_history table
ALTER TABLE stock_history 
    MODIFY COLUMN price DECIMAL(18, 8) NOT NULL;

-- End of migration
