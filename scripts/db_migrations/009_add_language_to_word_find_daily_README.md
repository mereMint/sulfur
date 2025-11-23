# Word Find Database Migration 009

## Purpose

This migration adds the `language` column to the `word_find_daily` and `word_find_premium_games` tables to support multi-language daily words (German and English). It also ensures the `game_type` column exists in `word_find_attempts` table (redundant with migration 007, but included for completeness).

## Affected Tables

1. **word_find_daily**
   - Adds `language` column (VARCHAR(2), default 'de')
   - Adds index on `language` column
   - Updates existing records to have default language 'de'
   - Adds unique constraint `unique_date_lang (date, language)` if not exists

2. **word_find_premium_games**
   - Adds `language` column (VARCHAR(2), default 'de')
   - Updates existing records to have default language 'de'

3. **word_find_attempts** (redundant with migration 007)
   - Ensures `game_type` column exists
   - Ensures index `idx_user_word_type` exists

## Issues Fixed

### Issue 1: Database Error - Unknown Column 'language'
**Error Message:**
```
[ERROR] Database error in get_or_create_daily_word: 1054 (42S22): Unknown column 'language' in 'SELECT'
```

**Cause:** The `word_find_daily` table was created before language support was added. The code tries to SELECT the `language` column but it doesn't exist in older installations.

**Fix:** This migration adds the `language` column with a default value of 'de' (German).

### Issue 2: Word Find Attempts Not Showing
**Symptom:** After guessing words, the game shows "Noch keine Versuche" (No attempts yet) even though attempts were made.

**Cause:** The `word_find_attempts` table might be missing the `game_type` column, causing INSERT operations to fail silently.

**Fix:** This migration ensures the `game_type` column exists (also handled in migration 007, but included here for completeness).

## How to Apply

### Option 1: Using mysql command line
```bash
mysql -u sulfur_bot_user -p sulfur_bot < scripts/db_migrations/009_add_language_to_word_find_daily.sql
```

### Option 2: Using apply_migration.py (if available)
```bash
python apply_migration.py scripts/db_migrations/009_add_language_to_word_find_daily.sql
```

### Option 3: Manual application via MySQL client
1. Connect to your database:
   ```bash
   mysql -u sulfur_bot_user -p sulfur_bot
   ```
2. Source the migration file:
   ```sql
   source /path/to/scripts/db_migrations/009_add_language_to_word_find_daily.sql;
   ```

## Verification

After applying the migration, verify the changes:

```sql
-- Check word_find_daily table structure
DESCRIBE word_find_daily;

-- Check word_find_premium_games table structure
DESCRIBE word_find_premium_games;

-- Check word_find_attempts table structure
DESCRIBE word_find_attempts;

-- Verify language column exists and has default value
SELECT COLUMN_NAME, COLUMN_DEFAULT, IS_NULLABLE 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = 'sulfur_bot' 
  AND TABLE_NAME = 'word_find_daily' 
  AND COLUMN_NAME = 'language';
```

## Backwards Compatibility

✅ **This migration is fully backwards compatible:**
- Existing data is preserved
- All existing records get default language 'de' (German)
- The unique constraint is updated to include language, allowing one daily word per language
- No data loss or breaking changes

## Rollback (if needed)

If you need to rollback this migration:

```sql
-- Remove language column from word_find_daily
ALTER TABLE word_find_daily DROP COLUMN language;

-- Remove language column from word_find_premium_games
ALTER TABLE word_find_premium_games DROP COLUMN language;

-- Remove language index
ALTER TABLE word_find_daily DROP INDEX idx_lang;

-- Note: This will lose any language-specific data if you've been using the feature
```

**⚠️ Warning:** Only rollback if absolutely necessary, as it will remove language support functionality.

## Notes

- The migration uses `IF NOT EXISTS` checks to prevent errors if columns already exist
- Default language is set to 'de' (German) for backwards compatibility
- The migration is idempotent - it can be run multiple times safely
- Migration 007 should ideally be applied before this one, but this migration includes its critical changes for redundancy
