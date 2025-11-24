# Migration 010: Add Missing Game Tables

## Overview
This migration adds database tables for various game types that are referenced by the web dashboard but were not created in the initial schema.

## Problem Solved
The web dashboard was showing errors for missing tables:
- `werwolf_user_stats` - Table 'sulfur_bot.werwolf_user_stats' doesn't exist
- `detective_games` - Table 'sulfur_bot.detective_games' doesn't exist
- `wordle_games` - Table 'sulfur_bot.wordle_games' doesn't exist
- `blackjack_games` - Table 'sulfur_bot.blackjack_games' doesn't exist
- `roulette_games` - Table 'sulfur_bot.roulette_games' doesn't exist
- `mines_games` - Table 'sulfur_bot.mines_games' doesn't exist
- `horse_racing_games` - Table 'sulfur_bot.horse_racing_games' doesn't exist
- `trolly_problem_choices` - Table 'sulfur_bot.trolly_problem_choices' doesn't exist

## Tables Created

### Game Statistics Tables

1. **werwolf_user_stats** - Tracks Werwolf game participation and statistics
   - Stores per-user stats: total games, wins, losses, role counts
   - Tracks which roles users have played (werewolf, villager, seer, doctor)

2. **wordle_games** - Wordle game tracking
   - Tracks individual game attempts, words, completion status
   - Stores guesses as JSON for replay capability

3. **blackjack_games** - Blackjack game history
   - Stores bet amounts, results, hands (as JSON)
   - Tracks winnings and game outcomes

4. **roulette_games** - Roulette game history
   - Stores bet types, bet values, winning numbers
   - Tracks winnings per game

5. **mines_games** - Minesweeper game history
   - Stores grid configuration, tiles revealed
   - Tracks wins/losses and cash out amounts

6. **russian_roulette_games** - Russian Roulette game history
   - Stores chamber positions, survival status
   - Tracks winnings for survivors

7. **horse_racing_games** - Horse racing game history
   - Stores horse selections, winning horse
   - Tracks bet amounts and winnings

8. **gambling_stats** - Aggregate gambling statistics per user/game type
   - Stores total games, wagered, won, lost
   - Tracks biggest wins and losses

### Word Find Tables

9. **word_find_daily** - Daily word find puzzle storage
   - Stores puzzle grids and word lists as JSON
   - Supports multiple languages (de/en)

10. **word_find_user_progress** - User progress on word find puzzles
    - Tracks found words, completion status, times
    - Links to daily puzzles by date

11. **word_find_user_stats** - User statistics for word find
    - Stores streak data, average/best times
    - Tracks total completed puzzles

### Compatibility Views

12. **trolly_problem_choices** (VIEW) - Alias for `trolly_responses` table
    - Provides backward compatibility with web dashboard
    - Maps to existing `trolly_responses` table

13. **detective_games** (VIEW) - Alias for `detective_cases` table
    - Provides backward compatibility with web dashboard
    - Maps to existing `detective_cases` table

## Automatic Application

This migration is automatically applied when:

1. **Bot Startup** - The maintain_bot scripts call `apply_pending_migrations()` before starting the bot
2. **After Git Updates** - When updates are pulled, migrations are applied automatically

No manual intervention is required!

## Testing

Run the validation test to verify the migration:

```bash
python3 test_migration_010.py
```

This will check:
- Migration file syntax and structure
- Presence of all expected tables and views
- Migration system configuration in maintain_bot scripts

## Technical Details

- All tables use `InnoDB` engine for ACID compliance
- Character set: `utf8mb4` with `utf8mb4_unicode_ci` collation for full emoji support
- Appropriate indexes added for common query patterns
- Views created using `CREATE OR REPLACE` for idempotency
- Tables created using `IF NOT EXISTS` for safe re-running

## Rollback

If needed, this migration can be rolled back by:

1. Dropping the created tables: `DROP TABLE IF EXISTS <table_name>`
2. Dropping the created views: `DROP VIEW IF EXISTS <view_name>`
3. Removing the migration record: `DELETE FROM schema_migrations WHERE migration_name = '010_add_missing_game_tables.sql'`

However, this should **not** be necessary as the migration uses `IF NOT EXISTS` and `CREATE OR REPLACE` for safe execution.
