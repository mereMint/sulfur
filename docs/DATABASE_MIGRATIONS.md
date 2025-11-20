# Database Migration System

## Overview

The Sulfur bot now includes an automatic database migration system that tracks and applies schema changes automatically. This ensures that the database is always up to date with the latest schema requirements.

## How It Works

### Migration Tracking

The system uses a `schema_migrations` table to track which migrations have been applied:

```sql
CREATE TABLE schema_migrations (
    migration_name VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_applied_at (applied_at)
)
```

### Automatic Application

Migrations are automatically applied:
1. **On bot startup** - When bot.py starts
2. **On maintenance script startup** - When maintain_bot.sh/ps1 runs
3. **After git updates** - When the maintenance script pulls new code

### Migration Discovery

The system looks for SQL files in `scripts/db_migrations/` and applies them in alphabetical order. Each migration file is tracked by its complete filename.

## Creating Migrations

### Naming Convention

Migration files should follow this naming pattern:
```
NNN_descriptive_name.sql
```

Where `NNN` is a sequential number (e.g., `001`, `002`, `003`).

### Migration File Format

Migrations should use standard MySQL syntax. For conditional schema changes (like adding a column only if it doesn't exist), use stored procedures:

```sql
-- Example: Adding a column conditionally
DELIMITER $$

DROP PROCEDURE IF EXISTS add_my_column$$
CREATE PROCEDURE add_my_column()
BEGIN
    IF NOT EXISTS (
        SELECT * FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() 
        AND TABLE_NAME = 'my_table' 
        AND COLUMN_NAME = 'my_column'
    ) THEN
        ALTER TABLE my_table 
        ADD COLUMN my_column VARCHAR(255) NOT NULL;
    END IF;
END$$

DELIMITER ;

-- Execute the procedure
CALL add_my_column();

-- Clean up
DROP PROCEDURE IF EXISTS add_my_column;
```

### Best Practices

1. **Use `CREATE TABLE IF NOT EXISTS`** for new tables
2. **Use stored procedures** for conditional ALTER TABLE statements
3. **Don't use database-specific `USE` statements** - the migration system already connects to the correct database
4. **Make migrations idempotent** - safe to run multiple times
5. **Test migrations** on a development database before deploying

### What to Avoid

❌ **Don't use:**
- `USE database_name;` - The system already selects the correct database
- `ADD COLUMN IF NOT EXISTS` - This is not standard MySQL syntax
- Hard-coded database names in queries
- References to `migration_log` table (use `schema_migrations` instead)

✅ **Do use:**
- `CREATE TABLE IF NOT EXISTS`
- Stored procedures for conditional schema changes
- `DATABASE()` function to reference the current database
- Comments to document what the migration does

## Migration Examples

### Simple Table Creation

```sql
-- Create a new table
CREATE TABLE IF NOT EXISTS my_new_table (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### Adding Columns Conditionally

```sql
-- Add a column if it doesn't exist
DELIMITER $$

DROP PROCEDURE IF EXISTS add_status_column$$
CREATE PROCEDURE add_status_column()
BEGIN
    IF NOT EXISTS (
        SELECT * FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() 
        AND TABLE_NAME = 'users' 
        AND COLUMN_NAME = 'status'
    ) THEN
        ALTER TABLE users 
        ADD COLUMN status VARCHAR(50) DEFAULT 'active';
    END IF;
END$$

DELIMITER ;

CALL add_status_column();
DROP PROCEDURE IF EXISTS add_status_column;
```

### Multiple Operations

```sql
-- Migration with multiple operations
-- Create table
CREATE TABLE IF NOT EXISTS settings (
    setting_key VARCHAR(100) PRIMARY KEY,
    setting_value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Add column to existing table
DELIMITER $$

DROP PROCEDURE IF EXISTS add_enabled_column$$
CREATE PROCEDURE add_enabled_column()
BEGIN
    IF NOT EXISTS (
        SELECT * FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() 
        AND TABLE_NAME = 'features' 
        AND COLUMN_NAME = 'enabled'
    ) THEN
        ALTER TABLE features 
        ADD COLUMN enabled BOOLEAN DEFAULT TRUE;
    END IF;
END$$

DELIMITER ;

CALL add_enabled_column();
DROP PROCEDURE IF EXISTS add_enabled_column;

-- Add index
CREATE INDEX IF NOT EXISTS idx_created_at ON logs(created_at);
```

## Testing Migrations

Use the provided test script to verify migrations work correctly:

```bash
# Run the migration test
python3 test_migration_system.py
```

This will:
1. Connect to the database
2. Initialize base tables
3. Create the migrations tracking table
4. List previously applied migrations
5. Apply any pending migrations
6. Test idempotency by running again
7. Display final migration status

## Manual Migration Management

### Check Applied Migrations

```sql
SELECT migration_name, applied_at 
FROM schema_migrations 
ORDER BY applied_at DESC;
```

### Mark a Migration as Applied (without running it)

```sql
INSERT INTO schema_migrations (migration_name) 
VALUES ('001_my_migration.sql');
```

### Remove a Migration Record (to re-run it)

```sql
DELETE FROM schema_migrations 
WHERE migration_name = '001_my_migration.sql';
```

⚠️ **Warning:** Only remove migration records if you're certain the migration needs to be re-run or was marked incorrectly.

## Troubleshooting

### Migration Failed with "already exists" error

This is normal and expected for idempotent migrations. The system automatically skips these errors.

### Migration Failed with other error

1. Check the migration SQL syntax
2. Ensure stored procedures are properly formatted
3. Verify table/column names are correct
4. Review the error message in the maintenance log

### Migration Applied but Not Working

1. Check if the table/column actually exists in the database
2. Verify the migration completed without errors
3. Check the `schema_migrations` table to confirm it was marked as applied

### Need to Re-run a Migration

1. Delete the entry from `schema_migrations`:
   ```sql
   DELETE FROM schema_migrations WHERE migration_name = 'NNN_migration_name.sql';
   ```
2. Restart the bot or maintenance script

## Architecture

### Components

1. **`modules/db_helpers.py`**
   - `create_migrations_table()` - Creates tracking table
   - `get_applied_migrations()` - Returns list of applied migrations
   - `mark_migration_applied()` - Records a migration as applied
   - `apply_sql_migration()` - Applies a single migration file
   - `apply_pending_migrations()` - Main function to discover and apply migrations

2. **`maintain_bot.sh` / `maintain_bot.ps1`**
   - Calls migration system on startup
   - Calls migration system after git updates

3. **`bot.py`**
   - Calls migration system on bot startup

### Flow

```
Bot/Script Startup
    ↓
Initialize Database Pool
    ↓
Create Base Tables (initialize_database)
    ↓
Create Migrations Tracking Table
    ↓
Discover Migration Files
    ↓
Check Applied Migrations
    ↓
Apply Pending Migrations (in order)
    ↓
Mark Each as Applied
    ↓
Continue Bot Startup
```

## Benefits

✅ **Automatic** - No manual intervention needed
✅ **Tracked** - Always know which migrations have been applied
✅ **Safe** - Idempotent migrations won't cause errors if re-run
✅ **Ordered** - Migrations apply in alphabetical order
✅ **Logged** - Full logging of migration activity
✅ **Backwards Compatible** - Works with existing database setup

## Future Enhancements

Potential improvements for the future:
- Migration rollback support
- Migration dry-run mode
- Migration validation before applying
- Web dashboard for migration status
- Migration dependency tracking
