# Migration 011: Fix Word Find Schema Conflict

## Problem

Migration 010 (`010_add_missing_game_tables.sql`) incorrectly defined the Word Find database tables with a schema that conflicts with the actual implementation in `modules/word_find.py`.

### Incorrect Schema (from migration 010):
```sql
word_find_daily (
    id, puzzle_date, grid, words, difficulty, language, created_at
)

word_find_user_stats (
    user_id, total_completed, current_streak, longest_streak, ...
)

word_find_user_progress (
    user_id, puzzle_date, words_found, completed, ...
)
```

### Correct Schema (from modules/word_find.py):
```sql
word_find_daily (
    id, word, difficulty, language, date
)

word_find_stats (
    user_id, total_games, daily_games, premium_games, ...
)

word_find_attempts (
    user_id, word_id, guess, similarity_score, attempt_number, game_type
)

word_find_premium_games (
    user_id, word, difficulty, language, completed, won
)
```

## Symptoms

When users try to play Word Find, they get this error:
```
❌ Fehler beim Speichern des Versuchs. Bitte kontaktiere einen Administrator.
Hinweis: Möglicherweise fehlen Datenbank-Migrationen.
```

This happens because:
1. The code tries to INSERT into `word_find_daily` with columns `(word, difficulty, language, date)`
2. But migration 010 created the table with columns `(puzzle_date, grid, words, difficulty, language, created_at)`
3. The column mismatch causes the INSERT to fail
4. The attempt recording fails and shows the error message

## Solution

This migration:
1. Detects if the wrong schema exists (by checking for `puzzle_date` column)
2. Drops the incorrectly created tables if they exist
3. Creates the correct tables with the proper schema
4. Is safe to run multiple times (idempotent)

## How to Apply

```bash
# Linux/Mac/Termux
mysql -u sulfur_bot_user -p sulfur_bot < scripts/db_migrations/011_fix_word_find_schema_conflict.sql

# Windows PowerShell
Get-Content scripts/db_migrations/011_fix_word_find_schema_conflict.sql | mysql -u sulfur_bot_user -p sulfur_bot
```

Or use the migration script:
```bash
python apply_migration.py scripts/db_migrations/011_fix_word_find_schema_conflict.sql
```

## Related Files

- `modules/word_find.py` - Contains correct table schema in `initialize_word_find_table()`
- `scripts/db_migrations/007_word_find_premium_update.sql` - Added premium game support
- `scripts/db_migrations/009_add_language_to_word_find_daily.sql` - Added language support
- `scripts/db_migrations/010_add_missing_game_tables.sql` - Fixed to not recreate Word Find tables

## Testing

After applying this migration, verify:
```sql
-- Check table structure
DESCRIBE word_find_daily;
-- Should show: id, word, difficulty, language, date

DESCRIBE word_find_attempts;
-- Should show: id, user_id, word_id, guess, similarity_score, attempt_number, game_type, created_at

DESCRIBE word_find_stats;
-- Should show: user_id, total_games, daily_games, premium_games, etc.

-- Test Word Find game
-- Run /wordfind in Discord and make a guess
-- Should not show error message anymore
```
