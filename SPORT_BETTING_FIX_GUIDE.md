# Sport Betting Team Short Name Fix

## Problem Description

The bot was experiencing database errors when trying to insert match data:

```
Error updating match: 1406 (22001): Data too long for column 'home_team_short' at row 1
Error updating match: 1406 (22001): Data too long for column 'away_team_short' at row 1
```

### Root Cause

- The `home_team_short` and `away_team_short` columns in the `sport_matches` table were defined as `VARCHAR(8)`
- The OpenLigaDB API provides a `shortName` field that can exceed 8 characters
- The code was using these values directly without truncation, causing database insertion failures

## Solution

### 1. Database Schema Changes

The column length has been increased from `VARCHAR(8)` to `VARCHAR(16)` to accommodate longer team abbreviations.

### 2. Code Changes

Added truncation logic to ensure team short names never exceed 16 characters:

- **OpenLigaDB API** (lines 795-799 in `sport_betting.py`):
  - Added `[:16]` truncation after retrieving `shortName`
  
- **Football-Data.org API** (lines 1208-1209 in `sport_betting.py`):
  - Added `[:16]` truncation as a safety measure
  
- **F1/MotoGP**: Already truncated to 3 characters, no changes needed

## Applying the Fix

### For New Installations

No action needed - the correct schema is included in the base migration file `014_add_sport_betting_tables.sql`.

### For Existing Installations

Apply the migration to update your database:

```bash
# Option 1: Using MySQL command line
mysql -u sulfur_bot_user -p sulfur_bot < scripts/db_migrations/015_fix_team_short_column_length.sql

# Option 2: Using the apply_migration.py script
python3 apply_migration.py scripts/db_migrations/015_fix_team_short_column_length.sql
```

### Verification

After applying the migration, verify the column types:

```sql
DESCRIBE sport_matches;
```

You should see:
```
home_team_short    | VARCHAR(16) | YES  |     | NULL    |       |
away_team_short    | VARCHAR(16) | YES  |     | NULL    |       |
```

## Testing

A test script is provided to verify the truncation logic:

```bash
python3 test_team_short_truncation.py
```

Expected output:
```
✓ All tests PASSED!

The fix correctly:
  1. Truncates team short names to 16 characters
  2. Handles empty/missing values with fallback
  3. Ensures all values fit in VARCHAR(16) column
```

## Files Changed

1. **modules/sport_betting.py**
   - Updated CREATE TABLE statement (line ~1954-1955)
   - Added truncation logic for OpenLigaDB (lines ~798-799)
   - Added truncation logic for Football-Data.org (lines ~1208-1209)

2. **scripts/db_migrations/014_add_sport_betting_tables.sql**
   - Updated base schema from VARCHAR(8) to VARCHAR(16)

3. **scripts/db_migrations/015_fix_team_short_column_length.sql**
   - New migration file to alter existing tables

## Impact

- **Backward Compatible**: Existing data with short names < 8 characters is unaffected
- **Forward Compatible**: New data with long names (8-16 chars) will now be accepted
- **Safe Truncation**: Data exceeding 16 characters is truncated rather than rejected
- **No Data Loss**: Only affects display names, not critical match data

## Additional Notes

- The 16-character limit should be sufficient for most team abbreviations
- The fallback logic creates 3-character abbreviations from full team names if no short name is provided
- F1 and MotoGP already use 3-character codes, so they are unaffected by this issue
