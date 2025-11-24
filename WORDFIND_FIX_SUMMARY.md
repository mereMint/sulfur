# Word Find Database Fix Summary

## Problem
Word Find game showed this error when users tried to make guesses:
```
❌ Fehler beim Speichern des Versuchs. Bitte kontaktiere einen Administrator.
Hinweis: Möglicherweise fehlen Datenbank-Migrationen.
```

## Root Cause
Migration 010 (`010_add_missing_game_tables.sql`) incorrectly defined Word Find database tables with a schema that conflicts with the actual implementation in `modules/word_find.py`.

### The Conflict
**Migration 010 created (WRONG):**
```sql
word_find_daily (
    id INT,
    puzzle_date DATE,      -- ❌ Wrong column name
    grid JSON,             -- ❌ Wrong column
    words JSON,            -- ❌ Wrong column
    difficulty INT,
    language VARCHAR(2),
    created_at TIMESTAMP
)
```

**Code expected (CORRECT):**
```sql
word_find_daily (
    id INT,
    word VARCHAR(100),     -- ✅ Correct
    difficulty VARCHAR(20),-- ✅ Correct
    language VARCHAR(2),   -- ✅ Correct
    date DATE              -- ✅ Correct
)
```

### Why This Caused Errors
When a user made a guess in Word Find:
1. Code tries: `INSERT INTO word_find_daily (word, difficulty, language, date) VALUES (...)`
2. Database has: columns `(id, puzzle_date, grid, words, difficulty, language, created_at)`
3. SQL Error: Column 'word' doesn't exist
4. `record_attempt()` returns `False`
5. User sees error message

## Solution

### Part 1: Fixed Migration 010
**File:** `scripts/db_migrations/010_add_missing_game_tables.sql`

**Changes:**
- Removed incorrect Word Find table definitions
- Added comment explaining Word Find tables are managed elsewhere
- Preserved all other game tables (Werwolf, Wordle, Casino games, etc.)

### Part 2: Created Migration 011
**File:** `scripts/db_migrations/011_fix_word_find_schema_conflict.sql`

**Purpose:** Fix databases where migration 010 was already applied

**What it does:**
1. Detects if wrong schema exists (checks for `puzzle_date` column)
2. Drops incorrectly created tables:
   - `word_find_daily` (if has wrong schema)
   - `word_find_user_progress` (unused table)
   - `word_find_user_stats` (wrong name, should be `word_find_stats`)
3. Creates correct tables with proper schema:
   - `word_find_daily` (word, difficulty, language, date)
   - `word_find_attempts` (user_id, word_id, guess, similarity_score, attempt_number, game_type)
   - `word_find_stats` (user_id, total_games, daily_games, premium_games, ...)
   - `word_find_premium_games` (user_id, word, difficulty, language, ...)

**Safety:**
- Idempotent (safe to run multiple times)
- Only drops tables with wrong schema
- Uses `IF NOT EXISTS` for all CREATE TABLE statements
- Preserves existing correct data

## How to Apply the Fix

### For New Installations
Just install normally - migration 010 is now fixed and won't create conflicts.

### For Existing Installations with the Bug
Apply migration 011:

```bash
# Using apply_migration.py (recommended)
python apply_migration.py scripts/db_migrations/011_fix_word_find_schema_conflict.sql

# Or using MySQL directly (Linux/Mac/Termux)
mysql -u sulfur_bot_user -p sulfur_bot < scripts/db_migrations/011_fix_word_find_schema_conflict.sql

# Or using PowerShell (Windows)
Get-Content scripts/db_migrations/011_fix_word_find_schema_conflict.sql | mysql -u sulfur_bot_user -p sulfur_bot
```

## Verification

### Check Table Schema
```sql
DESCRIBE word_find_daily;
-- Should show: id, word, difficulty, language, date

DESCRIBE word_find_attempts;
-- Should show: id, user_id, word_id, guess, similarity_score, attempt_number, game_type, created_at
```

### Test the Game
1. Run `/wordfind` in Discord
2. Make a guess
3. Should NOT show error message anymore
4. Should show proximity score and save the attempt

## Files Changed

1. **scripts/db_migrations/010_add_missing_game_tables.sql**
   - Removed conflicting Word Find table definitions
   - Added explanatory comment

2. **scripts/db_migrations/011_fix_word_find_schema_conflict.sql** (NEW)
   - Migration to fix affected databases

3. **scripts/db_migrations/011_fix_word_find_schema_conflict_README.md** (NEW)
   - Detailed documentation for migration 011

## Related Migrations

- **007_word_find_premium_update.sql**: Added premium game support (correct schema)
- **009_add_language_to_word_find_daily.sql**: Added language support (correct schema)
- **010_add_missing_game_tables.sql**: Now fixed to not conflict with Word Find

## Testing Performed

✓ Validated SQL syntax of migration 011
✓ Compared schemas between code and migration
✓ Verified migration 010 no longer creates conflicting tables
✓ Verified migration 011 correctly identifies and fixes wrong schemas
✓ Checked all CREATE TABLE statements match code expectations

## Impact

- **Severity:** High - Game was completely broken for affected users
- **Users Affected:** Anyone who applied migration 010
- **Data Loss:** None - migration 011 drops empty/incorrect tables only
- **Backward Compatibility:** Full - works with all previous migrations
