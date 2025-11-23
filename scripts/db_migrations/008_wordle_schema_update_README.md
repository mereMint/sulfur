# Wordle Schema Update Migration

## Purpose

This migration fixes database schema issues in the Wordle game module by adding missing columns that are required by the current code.

## What This Migration Does

1. **Adds `language` column to `wordle_daily` table**
   - Type: `VARCHAR(2)` 
   - Default: `'de'` (German)
   - Enables multi-language support for daily Wordle words
   - All existing words will default to German for backwards compatibility

2. **Adds `game_type` column to `wordle_attempts` table**
   - Type: `ENUM('daily', 'premium')`
   - Default: `'daily'`
   - Enables tracking of daily vs. premium game attempts
   - All existing attempts will default to 'daily' type

3. **Creates `wordle_premium_games` table** (if not exists)
   - Stores premium game instances separate from daily games
   - Tracks completion status and win/loss

4. **Adds necessary indexes**
   - `idx_lang` on `wordle_daily.language`
   - `idx_user_word_type` on `wordle_attempts(user_id, word_id, game_type)`
   - `unique_date_lang` composite unique key on `wordle_daily(date, language)`

## How to Apply

### Option 1: Using the Python migration script (Recommended)

```bash
python3 apply_migration.py scripts/db_migrations/008_wordle_schema_update.sql
```

### Option 2: Using MySQL command line

```bash
mysql -u sulfur_bot_user -p sulfur_bot < scripts/db_migrations/008_wordle_schema_update.sql
```

### Option 3: Using MySQL Workbench or other GUI tools

1. Open the SQL file in your MySQL client
2. Connect to the `sulfur_bot` database
3. Execute the entire script

## Backwards Compatibility

✅ **This migration is fully backwards compatible**

- All existing data is preserved
- Default values ensure old records work with new schema
- No data loss or modification of existing records
- The bot will work with both old and new schemas

## Errors Fixed

This migration fixes the following errors:

```
[ERROR] Database error in get_or_create_daily_word: 1054 (42S22): Unknown column 'language' in 'SELECT'
[ERROR] Error getting user Wordle attempts: 1054 (42S22): Unknown column 'game_type' in 'WHERE'
```

## Verification

After applying the migration, verify it worked:

```sql
-- Check wordle_daily table structure
DESCRIBE wordle_daily;

-- Check wordle_attempts table structure  
DESCRIBE wordle_attempts;

-- Check wordle_premium_games table exists
SHOW TABLES LIKE 'wordle_premium_games';
```

Expected results:
- `wordle_daily` should have a `language` column
- `wordle_attempts` should have a `game_type` column
- `wordle_premium_games` table should exist

## Rollback

If you need to rollback this migration (not recommended):

```sql
-- Remove added columns (will lose language and game_type data)
ALTER TABLE wordle_daily DROP COLUMN language;
ALTER TABLE wordle_daily DROP INDEX idx_lang;
ALTER TABLE wordle_daily DROP INDEX unique_date_lang;
ALTER TABLE wordle_attempts DROP COLUMN game_type;
ALTER TABLE wordle_attempts DROP INDEX idx_user_word_type;
DROP TABLE wordle_premium_games;
```

## Notes

- The migration uses conditional logic to check if columns/indexes exist before adding them
- Safe to run multiple times - idempotent operation
- No downtime required - changes are non-breaking
