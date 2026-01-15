-- ============================================================================
-- Migration 033: Fix Russian Roulette Games Schema
-- ============================================================================
-- This migration ensures russian_roulette_games table has a 'payout' column
-- to match the dashboard queries that expect it.
-- ============================================================================

DELIMITER $$

-- Create helper procedure to add columns if they don't exist
DROP PROCEDURE IF EXISTS add_column_if_not_exists_033$$
CREATE PROCEDURE add_column_if_not_exists_033(
    IN p_table_name VARCHAR(64),
    IN p_column_name VARCHAR(64),
    IN p_column_definition VARCHAR(500)
)
BEGIN
    DECLARE table_exists INT DEFAULT 0;
    DECLARE column_exists INT DEFAULT 0;

    -- Check if table exists
    SELECT COUNT(*) INTO table_exists
    FROM information_schema.tables
    WHERE table_schema = DATABASE() AND table_name = p_table_name;

    IF table_exists > 0 THEN
        -- Check if column exists
        SELECT COUNT(*) INTO column_exists
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = p_table_name
          AND column_name = p_column_name;

        IF column_exists = 0 THEN
            SET @sql = CONCAT('ALTER TABLE `', p_table_name, '` ADD COLUMN `', p_column_name, '` ', p_column_definition);
            PREPARE stmt FROM @sql;
            EXECUTE stmt;
            DEALLOCATE PREPARE stmt;
        END IF;
    END IF;
END$$

DELIMITER ;

-- ============================================================================
-- PART 1: Add payout column to russian_roulette_games
-- ============================================================================

-- Add payout column if it doesn't exist
CALL add_column_if_not_exists_033('russian_roulette_games', 'payout', 'BIGINT NOT NULL DEFAULT 0');

-- Sync payout from won_amount if won_amount exists
-- Only update rows where payout is NULL (to avoid overwriting legitimate zero values)
SET @has_won_amount = (
    SELECT COUNT(*)
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'russian_roulette_games'
      AND column_name = 'won_amount'
);

SET @sync_payout = IF(
    @has_won_amount > 0,
    'UPDATE russian_roulette_games SET payout = COALESCE(won_amount, 0) WHERE payout IS NULL',
    'SELECT "won_amount column does not exist, payout column already used" AS message'
);

PREPARE stmt FROM @sync_payout;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- ============================================================================
-- Cleanup
-- ============================================================================
DROP PROCEDURE IF EXISTS add_column_if_not_exists_033;

-- ============================================================================
-- Migration 033 Complete
-- ============================================================================
