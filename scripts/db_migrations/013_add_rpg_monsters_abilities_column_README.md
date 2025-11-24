# Migration 013: Add RPG Monsters Abilities Column

## Purpose
This migration adds the `abilities` JSON column to the `rpg_monsters` table if it doesn't already exist.

## Problem This Fixes
When the RPG system tries to seed monsters into the database, it fails with the error:
```
Unknown column 'abilities' in 'INSERT INTO'
```

This happens because:
1. The `rpg_monsters` table was created before the `abilities` column was added to the schema
2. The `CREATE TABLE IF NOT EXISTS` statement doesn't modify existing tables
3. The monster seeding code tries to insert data with the `abilities` column

## Changes Made
- Adds `abilities` column (JSON type) to `rpg_monsters` table if it doesn't exist

## Backwards Compatibility
This migration is backwards compatible:
- Uses `IF NOT EXISTS` check so it's safe to run multiple times
- Does not modify or delete any existing data
- Does not require any data migration (new column allows NULL values)

## After Migration
After this migration is applied, the RPG system will be able to:
- Insert new monsters with abilities
- Query monster abilities during combat
- Load monster data from the database properly

## Manual Application
If needed, you can apply this migration manually:
```sql
ALTER TABLE rpg_monsters ADD COLUMN abilities JSON;
```

Or run the full migration script:
```bash
mysql -u sulfur_bot_user -p sulfur_bot < scripts/db_migrations/013_add_rpg_monsters_abilities_column.sql
```
