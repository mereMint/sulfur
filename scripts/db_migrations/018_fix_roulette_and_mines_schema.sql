-- Migration: Fix roulette_games and mines_games table schemas
-- 
-- Issue 1: roulette_games table was created by migration 010 with 'winning_number' column,
--          but db_helpers.log_roulette_game expects 'result_number' column.
-- Issue 2: mines_games table was created by migration 010 without 'multiplier' column,
--          but db_helpers.log_mines_game expects 'multiplier' column.
--
-- This migration adds the missing columns and copies data where applicable.

DELIMITER $$

-- ============================================================================
-- Fix roulette_games: Add result_number column
-- ============================================================================

DROP PROCEDURE IF EXISTS fix_roulette_schema$$

CREATE PROCEDURE fix_roulette_schema()
BEGIN
    DECLARE result_number_exists INT DEFAULT 0;
    DECLARE winning_number_exists INT DEFAULT 0;
    DECLARE won_exists INT DEFAULT 0;
    DECLARE payout_exists INT DEFAULT 0;
    
    -- Check if result_number exists
    SELECT COUNT(*) INTO result_number_exists
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'roulette_games'
      AND COLUMN_NAME = 'result_number';
    
    -- Check if winning_number exists (old column from migration 010)
    SELECT COUNT(*) INTO winning_number_exists
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'roulette_games'
      AND COLUMN_NAME = 'winning_number';
    
    -- Check if won column exists
    SELECT COUNT(*) INTO won_exists
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'roulette_games'
      AND COLUMN_NAME = 'won';
      
    -- Check if payout column exists
    SELECT COUNT(*) INTO payout_exists
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'roulette_games'
      AND COLUMN_NAME = 'payout';
    
    -- Add result_number column if it doesn't exist
    IF result_number_exists = 0 THEN
        ALTER TABLE roulette_games ADD COLUMN result_number INT NOT NULL DEFAULT 0 AFTER bet_value;
    END IF;
    
    -- Copy data from winning_number to result_number if winning_number exists
    IF winning_number_exists = 1 AND result_number_exists = 0 THEN
        UPDATE roulette_games SET result_number = COALESCE(winning_number, 0);
    END IF;
    
    -- Add won column if it doesn't exist
    IF won_exists = 0 THEN
        ALTER TABLE roulette_games ADD COLUMN won BOOLEAN NOT NULL DEFAULT FALSE AFTER result_number;
    END IF;
    
    -- Add payout column if it doesn't exist
    IF payout_exists = 0 THEN
        ALTER TABLE roulette_games ADD COLUMN payout BIGINT NOT NULL DEFAULT 0 AFTER won;
        -- Copy data from won_amount if it exists
        IF EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS 
                   WHERE TABLE_SCHEMA = DATABASE() 
                   AND TABLE_NAME = 'roulette_games' 
                   AND COLUMN_NAME = 'won_amount') THEN
            UPDATE roulette_games SET payout = COALESCE(won_amount, 0);
        END IF;
    END IF;
    
    -- Drop the old winning_number column if it exists
    IF winning_number_exists = 1 THEN
        ALTER TABLE roulette_games DROP COLUMN winning_number;
    END IF;
    
    -- Drop the old won_amount column if it exists
    IF EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS 
               WHERE TABLE_SCHEMA = DATABASE() 
               AND TABLE_NAME = 'roulette_games' 
               AND COLUMN_NAME = 'won_amount') THEN
        ALTER TABLE roulette_games DROP COLUMN won_amount;
    END IF;
END$$

-- ============================================================================
-- Fix mines_games: Add multiplier column  
-- ============================================================================

DROP PROCEDURE IF EXISTS fix_mines_schema$$

CREATE PROCEDURE fix_mines_schema()
BEGIN
    DECLARE multiplier_exists INT DEFAULT 0;
    DECLARE payout_exists INT DEFAULT 0;
    
    -- Check if multiplier exists
    SELECT COUNT(*) INTO multiplier_exists
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'mines_games'
      AND COLUMN_NAME = 'multiplier';
    
    -- Check if payout column exists
    SELECT COUNT(*) INTO payout_exists
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'mines_games'
      AND COLUMN_NAME = 'payout';
    
    -- Add multiplier column if it doesn't exist
    IF multiplier_exists = 0 THEN
        ALTER TABLE mines_games ADD COLUMN multiplier DECIMAL(10, 2) NOT NULL DEFAULT 1.0 AFTER result;
    END IF;
    
    -- Add payout column if it doesn't exist
    IF payout_exists = 0 THEN
        ALTER TABLE mines_games ADD COLUMN payout BIGINT NOT NULL DEFAULT 0 AFTER multiplier;
        -- Copy data from won_amount if it exists
        IF EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS 
                   WHERE TABLE_SCHEMA = DATABASE() 
                   AND TABLE_NAME = 'mines_games' 
                   AND COLUMN_NAME = 'won_amount') THEN
            UPDATE mines_games SET payout = COALESCE(won_amount, 0);
        END IF;
    END IF;
    
    -- Drop the old won_amount column if it exists
    IF EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS 
               WHERE TABLE_SCHEMA = DATABASE() 
               AND TABLE_NAME = 'mines_games' 
               AND COLUMN_NAME = 'won_amount') THEN
        ALTER TABLE mines_games DROP COLUMN won_amount;
    END IF;
END$$

DELIMITER ;

-- Execute the procedures
CALL fix_roulette_schema();
CALL fix_mines_schema();

-- Clean up
DROP PROCEDURE IF EXISTS fix_roulette_schema;
DROP PROCEDURE IF EXISTS fix_mines_schema;

-- ============================================================================
-- End of Migration
-- ============================================================================
