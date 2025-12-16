-- ============================================================
-- Sulfur Bot - Database Setup Script
-- ============================================================
-- Run this in MySQL to create the database and user:
-- mysql -u root -p < setup_database.sql
-- ============================================================
-- 
-- CUSTOMIZATION:
-- You can change the database name, username, and password by
-- modifying the variables below, or by setting them in your .env file:
--   DB_NAME=sulfur_bot
--   DB_USER=sulfur_bot_user
--   DB_PASS=your_password (or leave empty)
--   DB_HOST=localhost
-- ============================================================

-- Create database with UTF8MB4 support (for emojis and special characters)
-- Default database name: sulfur_bot
-- To use a different name, replace 'sulfur_bot' with your preferred name
CREATE DATABASE IF NOT EXISTS sulfur_bot 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

-- Create user without password (local development)
-- For production, use a strong password: IDENTIFIED BY 'your_secure_password'
-- Default user: sulfur_bot_user
-- To use a different user, replace 'sulfur_bot_user' with your preferred username
CREATE USER IF NOT EXISTS 'sulfur_bot_user'@'localhost' IDENTIFIED BY '';

-- Grant all privileges on the sulfur_bot database to the bot user
-- If you changed the database or user name above, update these lines too
GRANT ALL PRIVILEGES ON sulfur_bot.* TO 'sulfur_bot_user'@'localhost';

-- Apply changes
FLUSH PRIVILEGES;

-- Show databases to confirm
SHOW DATABASES LIKE 'sulfur_bot';

-- Show user privileges
SHOW GRANTS FOR 'sulfur_bot_user'@'localhost';
