-- ============================================================================
-- Migration 021: Consolidate User and Game Tables
-- ============================================================================
-- This migration improves the database schema by:
-- 1. Creating a unified user_profiles view for better data aggregation
-- 2. Adding indexes to improve query performance
-- 3. NOT deleting any existing tables to preserve compatibility
-- ============================================================================

-- ============================================================================
-- Part 1: Create a unified view for user profiles
-- This combines data from players, user_customization, user_economy, and user_stats
-- ============================================================================

DROP VIEW IF EXISTS v_user_profiles;

CREATE VIEW v_user_profiles AS
SELECT 
    p.discord_id AS user_id,
    p.display_name,
    p.level,
    p.xp,
    p.wins,
    p.losses,
    p.balance,
    p.last_seen,
    p.last_activity_name,
    p.relationship_summary,
    p.game_history,
    -- Customization settings
    COALESCE(uc.equipped_color, '#00ff41') AS equipped_color,
    COALESCE(uc.embed_color, '#00ff41') AS embed_color,
    COALESCE(uc.profile_background, 'default') AS profile_background,
    COALESCE(uc.language, 'de') AS language,
    -- Economy data
    COALESCE(ue.last_daily_claim, NULL) AS last_daily_claim,
    COALESCE(ue.total_earned, 0) AS total_earned,
    COALESCE(ue.total_spent, 0) AS total_spent,
    -- Aggregated stats for current month
    COALESCE(us_current.messages_sent, 0) AS messages_this_month,
    COALESCE(us_current.voice_minutes, 0) AS voice_minutes_this_month,
    COALESCE(us_current.games_played, 0) AS games_played_this_month,
    COALESCE(us_current.games_won, 0) AS games_won_this_month,
    COALESCE(us_current.total_bet, 0) AS total_bet_this_month,
    COALESCE(us_current.total_won, 0) AS total_won_this_month,
    -- Autonomous settings
    COALESCE(uas.allow_autonomous_messages, TRUE) AS allow_autonomous_messages,
    COALESCE(uas.allow_autonomous_calls, TRUE) AS allow_autonomous_calls,
    uas.last_autonomous_contact,
    -- Total messages and voice time (all time)
    COALESCE(us_total.total_messages, 0) AS total_messages,
    COALESCE(us_total.total_voice_minutes, 0) AS total_voice_minutes,
    -- Feature unlocks count
    COALESCE(fu_count.unlock_count, 0) AS premium_features_unlocked,
    -- Wrapped registration status
    CASE WHEN wr.user_id IS NOT NULL AND wr.opted_out = FALSE THEN TRUE ELSE FALSE END AS wrapped_registered
FROM players p
LEFT JOIN user_customization uc ON p.discord_id = uc.user_id
LEFT JOIN user_economy ue ON p.discord_id = ue.user_id
LEFT JOIN user_autonomous_settings uas ON p.discord_id = uas.user_id
LEFT JOIN wrapped_registrations wr ON p.discord_id = wr.user_id
-- Current month stats
LEFT JOIN user_stats us_current ON p.discord_id = us_current.user_id 
    AND us_current.stat_period = DATE_FORMAT(CURRENT_DATE, '%Y-%m')
-- Aggregated all-time stats
LEFT JOIN (
    SELECT user_id, 
           SUM(messages_sent) AS total_messages, 
           SUM(voice_minutes) AS total_voice_minutes
    FROM user_stats
    GROUP BY user_id
) us_total ON p.discord_id = us_total.user_id
-- Feature unlock count
LEFT JOIN (
    SELECT user_id, COUNT(*) AS unlock_count
    FROM feature_unlocks
    GROUP BY user_id
) fu_count ON p.discord_id = fu_count.user_id;


-- ============================================================================
-- Part 2: Create a unified view for game statistics per user
-- This combines data from all individual game tables
-- ============================================================================

DROP VIEW IF EXISTS v_user_game_stats;

CREATE VIEW v_user_game_stats AS
SELECT 
    user_id,
    -- Blackjack stats
    bj.blackjack_games,
    bj.blackjack_wins,
    bj.blackjack_total_bet,
    bj.blackjack_total_won,
    -- Roulette stats
    rl.roulette_games,
    rl.roulette_wins,
    rl.roulette_total_bet,
    rl.roulette_total_won,
    -- Mines stats
    mn.mines_games,
    mn.mines_wins,
    mn.mines_total_bet,
    mn.mines_total_won,
    -- Tower stats
    tw.tower_games,
    tw.tower_wins,
    tw.tower_total_bet,
    tw.tower_total_won,
    -- Russian roulette stats
    rr.rr_games,
    rr.rr_survived,
    rr.rr_total_entry,
    rr.rr_total_won,
    -- Detective stats
    dt.detective_solved,
    dt.detective_failed,
    dt.detective_total_played,
    dt.detective_current_difficulty
FROM (SELECT DISTINCT user_id FROM gambling_stats UNION SELECT DISTINCT user_id FROM detective_user_stats) all_users
LEFT JOIN (
    SELECT user_id,
           COUNT(*) AS blackjack_games,
           SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) AS blackjack_wins,
           SUM(bet_amount) AS blackjack_total_bet,
           SUM(payout) AS blackjack_total_won
    FROM blackjack_games
    GROUP BY user_id
) bj ON all_users.user_id = bj.user_id
LEFT JOIN (
    SELECT user_id,
           COUNT(*) AS roulette_games,
           SUM(CASE WHEN won = TRUE THEN 1 ELSE 0 END) AS roulette_wins,
           SUM(bet_amount) AS roulette_total_bet,
           SUM(payout) AS roulette_total_won
    FROM roulette_games
    GROUP BY user_id
) rl ON all_users.user_id = rl.user_id
LEFT JOIN (
    SELECT user_id,
           COUNT(*) AS mines_games,
           SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) AS mines_wins,
           SUM(bet_amount) AS mines_total_bet,
           SUM(payout) AS mines_total_won
    FROM mines_games
    GROUP BY user_id
) mn ON all_users.user_id = mn.user_id
LEFT JOIN (
    SELECT user_id,
           COUNT(*) AS tower_games,
           SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) AS tower_wins,
           SUM(bet_amount) AS tower_total_bet,
           SUM(payout) AS tower_total_won
    FROM tower_games
    GROUP BY user_id
) tw ON all_users.user_id = tw.user_id
LEFT JOIN (
    SELECT user_id,
           COUNT(*) AS rr_games,
           SUM(CASE WHEN survived = TRUE THEN 1 ELSE 0 END) AS rr_survived,
           SUM(entry_fee) AS rr_total_entry,
           SUM(payout) AS rr_total_won
    FROM russian_roulette_games
    GROUP BY user_id
) rr ON all_users.user_id = rr.user_id
LEFT JOIN (
    SELECT user_id,
           cases_solved AS detective_solved,
           cases_failed AS detective_failed,
           total_cases_played AS detective_total_played,
           current_difficulty AS detective_current_difficulty
    FROM detective_user_stats
) dt ON all_users.user_id = dt.user_id;


-- ============================================================================
-- Part 3: Create a unified view for music activity per user
-- ============================================================================

DROP VIEW IF EXISTS v_user_music_stats;

CREATE VIEW v_user_music_stats AS
SELECT 
    user_id,
    COUNT(*) AS total_songs_played,
    COUNT(DISTINCT song_artist) AS unique_artists,
    COUNT(DISTINCT song_title) AS unique_songs,
    MAX(played_at) AS last_played,
    -- Most played song
    (SELECT CONCAT(song_title, ' by ', song_artist) 
     FROM music_history mh2 
     WHERE mh2.user_id = mh.user_id 
     GROUP BY song_title, song_artist 
     ORDER BY COUNT(*) DESC 
     LIMIT 1) AS most_played_song,
    -- Most played artist
    (SELECT song_artist 
     FROM music_history mh3 
     WHERE mh3.user_id = mh.user_id 
     GROUP BY song_artist 
     ORDER BY COUNT(*) DESC 
     LIMIT 1) AS most_played_artist
FROM music_history mh
GROUP BY user_id;


-- ============================================================================
-- Part 4: Add performance indexes for frequently queried columns
-- ============================================================================

-- Index on players for common lookups
CREATE INDEX IF NOT EXISTS idx_players_level_xp ON players(level DESC, xp DESC);
CREATE INDEX IF NOT EXISTS idx_players_balance ON players(balance DESC);
CREATE INDEX IF NOT EXISTS idx_players_last_seen ON players(last_seen DESC);

-- Index on user_stats for monthly aggregations
CREATE INDEX IF NOT EXISTS idx_user_stats_user_period ON user_stats(user_id, stat_period);

-- Index on music_history for user lookups
CREATE INDEX IF NOT EXISTS idx_music_history_user_played ON music_history(user_id, played_at DESC);

-- Index on transaction_history for user lookups
CREATE INDEX IF NOT EXISTS idx_transaction_history_user_date ON transaction_history(user_id, created_at DESC);


-- ============================================================================
-- Part 5: Create summary stats table for dashboard (materialized view alternative)
-- This is updated periodically and used for fast dashboard queries
-- ============================================================================

CREATE TABLE IF NOT EXISTS dashboard_summary_stats (
    stat_key VARCHAR(100) PRIMARY KEY,
    stat_value BIGINT DEFAULT 0,
    stat_text TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_updated_at (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Initialize with some common stats
INSERT INTO dashboard_summary_stats (stat_key, stat_value, stat_text) VALUES
    ('total_users', 0, NULL),
    ('active_users_7d', 0, NULL),
    ('total_messages', 0, NULL),
    ('total_voice_minutes', 0, NULL),
    ('total_games_played', 0, NULL),
    ('total_economy_value', 0, NULL)
ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP;


-- ============================================================================
-- Part 6: Create stored procedure to update dashboard summary stats
-- ============================================================================

DROP PROCEDURE IF EXISTS update_dashboard_stats;

DELIMITER //
CREATE PROCEDURE update_dashboard_stats()
BEGIN
    -- Total users
    INSERT INTO dashboard_summary_stats (stat_key, stat_value)
    SELECT 'total_users', COUNT(*) FROM players
    ON DUPLICATE KEY UPDATE stat_value = VALUES(stat_value);
    
    -- Active users in last 7 days
    INSERT INTO dashboard_summary_stats (stat_key, stat_value)
    SELECT 'active_users_7d', COUNT(*) FROM players 
    WHERE last_seen >= DATE_SUB(NOW(), INTERVAL 7 DAY)
    ON DUPLICATE KEY UPDATE stat_value = VALUES(stat_value);
    
    -- Total messages (all time)
    INSERT INTO dashboard_summary_stats (stat_key, stat_value)
    SELECT 'total_messages', COALESCE(SUM(messages_sent), 0) FROM user_stats
    ON DUPLICATE KEY UPDATE stat_value = VALUES(stat_value);
    
    -- Total voice minutes (all time)
    INSERT INTO dashboard_summary_stats (stat_key, stat_value)
    SELECT 'total_voice_minutes', COALESCE(SUM(voice_minutes), 0) FROM user_stats
    ON DUPLICATE KEY UPDATE stat_value = VALUES(stat_value);
    
    -- Total games played (all time)
    INSERT INTO dashboard_summary_stats (stat_key, stat_value)
    SELECT 'total_games_played', COALESCE(SUM(games_played), 0) FROM user_stats
    ON DUPLICATE KEY UPDATE stat_value = VALUES(stat_value);
    
    -- Total economy value (sum of all balances)
    INSERT INTO dashboard_summary_stats (stat_key, stat_value)
    SELECT 'total_economy_value', COALESCE(SUM(balance), 0) FROM players
    ON DUPLICATE KEY UPDATE stat_value = VALUES(stat_value);
END //
DELIMITER ;

-- Run the procedure once to initialize
CALL update_dashboard_stats();
