# Migration 012: Add Missing Columns to rpg_items Table

## Purpose
This migration adds missing columns to the `rpg_items` table that are referenced in the RPG system code but were not present in older database installations.

## Issue Fixed
Error when generating daily shop:
```
[2025-11-24 21:10:08] [Bot] [ERROR] Error getting daily shop items: 1054 (42S22): Unknown column 'is_quest_item' in 'WHERE'
```

## Changes Made
Adds the following columns to the `rpg_items` table if they don't exist:
1. `is_quest_item` (BOOLEAN, DEFAULT FALSE) - Marks items that are quest-specific
2. `is_sellable` (BOOLEAN, DEFAULT TRUE) - Indicates if item can be sold
3. `is_usable` (BOOLEAN, DEFAULT TRUE) - Indicates if item can be used
4. `quest_id` (VARCHAR(100), NULL) - Links item to specific quest

Also adds an index on `is_quest_item` for query performance.

## Backwards Compatibility
✅ **FULLY BACKWARDS COMPATIBLE**

- Uses conditional `ALTER TABLE` statements that check if columns exist before adding them
- Sets safe defaults for all new columns (FALSE for is_quest_item, TRUE for is_sellable/is_usable)
- Existing items will get default values automatically
- No data loss or modification to existing records

## How to Apply

### Method 1: Using MySQL Command Line (Recommended)
```bash
mysql -u sulfur_bot_user -p sulfur_bot < scripts/db_migrations/012_add_rpg_items_columns.sql
```

### Method 2: Manual Application (via MySQL client)
```sql
USE sulfur_bot;
SOURCE scripts/db_migrations/012_add_rpg_items_columns.sql;
```

### Method 3: Using apply_migration.py
Note: This migration uses stored procedures with DELIMITER changes. The apply_migration.py script may not handle this correctly. Use Method 1 or 2 instead.

## Verification

After applying the migration, verify the columns exist:

```sql
DESCRIBE rpg_items;
```

Expected output should include:
- `is_quest_item` | tinyint(1) | NO | | 0
- `is_sellable` | tinyint(1) | NO | | 1
- `is_usable` | tinyint(1) | NO | | 1
- `quest_id` | varchar(100) | YES | | NULL

## Testing

The daily shop generation should work without errors:
1. Wait for next daily shop generation (happens automatically)
2. Or trigger manually if testing

The error `Unknown column 'is_quest_item' in 'WHERE'` should be resolved.

## Rollback

If needed, columns can be removed (though not recommended):

```sql
ALTER TABLE rpg_items DROP COLUMN is_quest_item;
ALTER TABLE rpg_items DROP COLUMN is_sellable;
ALTER TABLE rpg_items DROP COLUMN is_usable;
ALTER TABLE rpg_items DROP COLUMN quest_id;
ALTER TABLE rpg_items DROP INDEX idx_quest;
```

⚠️ **WARNING**: Do not rollback if items have been created with quest-specific flags set.

## Related Files
- `modules/rpg_system.py` - Uses these columns in various functions
- Line 967: Table creation includes these columns
- Line 2404, 2414: Queries filter by `is_quest_item`
- Line 1643: Insert statement includes these columns

## Date
2025-11-24

## Author
GitHub Copilot Agent
