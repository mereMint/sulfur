-- Migration: Fix Sport Team Short Name Column Length
-- Description: Increases VARCHAR length for home_team_short and away_team_short from 8 to 16 characters
--              to accommodate longer team abbreviations from OpenLigaDB API

-- Alter sport_matches table to increase column length
ALTER TABLE sport_matches 
    MODIFY COLUMN home_team_short VARCHAR(16),
    MODIFY COLUMN away_team_short VARCHAR(16);
