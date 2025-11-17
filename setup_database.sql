-- ============================================================
-- Sulfur Bot - Database Setup Script
-- ============================================================
-- Run this in MySQL to create the database and user:
-- mysql -u root -p < setup_database.sql
-- ============================================================

-- Create database with UTF8MB4 support (for emojis and special characters)
CREATE DATABASE IF NOT EXISTS sulfur_bot 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

-- Create user without password (local development)
-- For production, use a strong password: IDENTIFIED BY 'your_secure_password'
CREATE USER IF NOT EXISTS 'sulfur_bot_user'@'localhost' IDENTIFIED BY '';

-- Grant all privileges on the sulfur_bot database
GRANT ALL PRIVILEGES ON sulfur_bot.* TO 'sulfur_bot_user'@'localhost';

-- Apply changes
FLUSH PRIVILEGES;

-- Show databases to confirm
SHOW DATABASES LIKE 'sulfur_bot';

-- Show user privileges
SHOW GRANTS FOR 'sulfur_bot_user'@'localhost';
