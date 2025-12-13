-- ============================================================
-- Sulfur Bot - Database Cleanup Script
-- Remove Voice Call and Autonomous Behavior Tables
-- ============================================================
-- 
-- This script removes database tables that are no longer needed
-- after removing voice call and autonomous behavior features.
-- 
-- IMPORTANT: Make a backup before running this script!
-- 
-- Usage:
--   mysql -u sulfur_bot_user -p sulfur_bot < cleanup_autonomous_voice_tables.sql
-- 
-- ============================================================

USE sulfur_bot;

-- Voice Call Related Tables
-- These tables stored voice session data and conversation transcripts

DROP TABLE IF EXISTS voice_messages;
DROP TABLE IF EXISTS voice_conversations;
DROP TABLE IF EXISTS voice_sessions;

-- Autonomous Behavior Related Tables
-- These tables managed bot's autonomous messaging and user interaction

DROP TABLE IF EXISTS temp_dm_access;
DROP TABLE IF EXISTS bot_autonomous_actions;
DROP TABLE IF EXISTS user_autonomous_settings;
DROP TABLE IF EXISTS bot_mind_state;

-- Note: managed_voice_channels table is kept as it's used for
-- join-to-create voice channels (Werwolf and general voice channel management)

-- ============================================================
-- Verification Query
-- Run this to verify tables were dropped successfully:
-- ============================================================
-- 
-- SHOW TABLES LIKE '%voice%';
-- SHOW TABLES LIKE '%autonomous%';
-- SHOW TABLES LIKE '%bot_mind%';
-- SHOW TABLES LIKE '%temp_dm%';
-- 
-- These queries should return no results for dropped tables.
-- 
-- ============================================================
