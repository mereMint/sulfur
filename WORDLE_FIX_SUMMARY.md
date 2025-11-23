# Wordle Database Schema Fix - Summary

## Issue Description

The Wordle game module was failing with database errors:
```
[ERROR] Database error in get_or_create_daily_word: 1054 (42S22): Unknown column 'language' in 'SELECT'
[ERROR] Error getting user Wordle attempts: 1054 (42S22): Unknown column 'game_type' in 'WHERE'
```

## Root Cause

The `wordle_daily` and `wordle_attempts` tables were created before the code was updated to support:
- Multi-language functionality (English and German)
- Premium game types (daily vs. premium games)

The code in `modules/wordle.py` expects these columns to exist, but they were missing from the database schema.

## Solution

A backwards-compatible database migration has been created to add the missing columns and tables:

**File**: `scripts/db_migrations/008_wordle_schema_update.sql`

### What the Migration Does

1. **Adds `language` column to `wordle_daily` table**
   - Allows storing daily words in different languages
   - Defaults to 'de' (German) for backwards compatibility
   - Updates unique constraint to `(date, language)` for multi-language support

2. **Adds `game_type` column to `wordle_attempts` table**  
   - Distinguishes between daily and premium game attempts
   - Defaults to 'daily' for backwards compatibility
   - Adds index for efficient querying

3. **Creates `wordle_premium_games` table**
   - Stores premium game instances
   - Tracks completion status and outcomes

4. **Adds performance indexes**
   - `idx_lang` on `wordle_daily.language`
   - `idx_user_word_type` on `wordle_attempts(user_id, word_id, game_type)`

## How to Apply the Fix

### Method 1: Using Python Script (Recommended)

```bash
cd /home/runner/work/sulfur/sulfur
python3 apply_migration.py scripts/db_migrations/008_wordle_schema_update.sql
```

### Method 2: Using MySQL Command Line

```bash
mysql -u sulfur_bot_user -p sulfur_bot < scripts/db_migrations/008_wordle_schema_update.sql
```

### Method 3: Using MySQL Workbench

1. Open `scripts/db_migrations/008_wordle_schema_update.sql` in MySQL Workbench
2. Connect to the `sulfur_bot` database
3. Execute the entire script

## Verification

After applying the migration, verify it worked:

```sql
-- Check wordle_daily has language column
DESCRIBE wordle_daily;

-- Check wordle_attempts has game_type column  
DESCRIBE wordle_attempts;

-- Check wordle_premium_games exists
SHOW TABLES LIKE 'wordle_premium_games';
```

Or run this verification script:
```bash
mysql -u sulfur_bot_user -p sulfur_bot -e "
SELECT 
  COLUMN_NAME, 
  DATA_TYPE, 
  COLUMN_DEFAULT
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = 'sulfur_bot' 
  AND TABLE_NAME = 'wordle_daily' 
  AND COLUMN_NAME = 'language';
"
```

Expected output should show the `language` column exists.

## Backwards Compatibility

✅ **Fully backwards compatible**

- All existing data is preserved
- Default values ('de' for language, 'daily' for game_type) ensure old records work
- No breaking changes to existing functionality
- Migration is idempotent - safe to run multiple times

## Impact

After applying this migration:
- ✅ Wordle daily games will work correctly
- ✅ Multi-language support will be enabled
- ✅ Premium Wordle games will be supported
- ✅ No data loss or corruption
- ✅ All existing statistics and progress preserved

## Word Find Status

**Note**: Word Find already has a similar migration in place (`007_word_find_premium_update.sql`) that should have been applied. If Word Find is also showing errors, ensure migration 007 has been applied.

## Technical Details

### Files Modified/Created
- ✅ `scripts/db_migrations/008_wordle_schema_update.sql` - Migration script
- ✅ `scripts/db_migrations/008_wordle_schema_update_README.md` - Detailed documentation

### Files Analyzed (No Changes Needed)
- ✅ `modules/wordle.py` - Already contains correct SQL queries
- ✅ `modules/word_find.py` - Already has proper schema support

## Next Steps

1. **Apply the migration** using one of the methods above
2. **Verify the migration** using the verification queries
3. **Test Wordle functionality** by running a game
4. **Monitor logs** to ensure no more schema errors

## Support

For detailed documentation, see:
- `scripts/db_migrations/008_wordle_schema_update_README.md`

For rollback procedures (if needed), see the README.
