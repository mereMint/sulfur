# Detective Game Database Tables - Implementation Summary

## Overview
This fix addresses the issue where the /detective command wasn't showing different cases because the required database tables were not being created automatically.

## Problem
- The detective game module (`modules/detective_game.py`) expects three database tables to exist
- These tables were not included in the `initialize_database()` function
- Users experienced the same case repeatedly because the system couldn't track progress or retrieve stored cases

## Solution
Added three tables to the automatic database initialization in `modules/db_helpers.py`:

### 1. detective_cases
Stores AI-generated murder mystery cases
```sql
CREATE TABLE IF NOT EXISTS detective_cases (
    case_id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    location VARCHAR(255) NOT NULL,
    victim VARCHAR(255) NOT NULL,
    suspects JSON NOT NULL,
    murderer_index INT NOT NULL,
    evidence JSON NOT NULL,
    hints JSON NOT NULL,
    difficulty INT NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_difficulty (difficulty)
)
```

### 2. detective_user_stats
Tracks user difficulty levels and overall statistics
```sql
CREATE TABLE IF NOT EXISTS detective_user_stats (
    user_id BIGINT PRIMARY KEY,
    current_difficulty INT NOT NULL DEFAULT 1,
    cases_solved INT NOT NULL DEFAULT 0,
    cases_failed INT NOT NULL DEFAULT 0,
    total_cases_played INT NOT NULL DEFAULT 0,
    last_played_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
)
```

### 3. detective_user_progress
Tracks which cases each user has started/completed
```sql
CREATE TABLE IF NOT EXISTS detective_user_progress (
    user_id BIGINT NOT NULL,
    case_id INT NOT NULL,
    completed BOOLEAN NOT NULL DEFAULT FALSE,
    solved BOOLEAN NOT NULL DEFAULT FALSE,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    PRIMARY KEY (user_id, case_id),
    INDEX idx_user_completed (user_id, completed),
    FOREIGN KEY (case_id) REFERENCES detective_cases(case_id) ON DELETE CASCADE
)
```

## Automatic Initialization Points
The database tables are now automatically created/updated at three key points:

1. **Bot Startup** - `bot.py` line 271
   - When the bot starts, it calls `initialize_database()`
   - This ensures fresh deployments have all tables

2. **Git Updates (Linux/Termux)** - `maintain_bot.sh` lines 609-637
   - After pulling updates, the script runs `initialize_database()`
   - Python code executed inline to apply schema changes

3. **Git Updates (Windows)** - `maintain_bot.ps1` lines 940-973
   - After pulling updates, the script runs `initialize_database()`
   - PowerShell executes Python code to apply schema changes

## Safety Features

### Backwards Compatibility
✅ All tables use `CREATE TABLE IF NOT EXISTS`
- Won't error on existing deployments
- Can be run multiple times safely
- No risk of data loss

### Data Integrity
✅ Foreign key constraints with CASCADE delete
- If a case is deleted, user progress for that case is also deleted
- Maintains referential integrity

### No Breaking Changes
✅ Only adds tables, never removes or modifies existing ones
✅ No migration required for existing installations
✅ Existing functionality remains unchanged

## Testing Verification
A test script `test_detective_tables.py` has been created to verify:
- All three tables are created successfully
- All required columns exist in each table
- Table structures match the queries in `detective_game.py`
- The initialization is idempotent (can be run multiple times)

## Expected Behavior After Deployment

### First Time Users
1. Bot starts and creates all tables automatically
2. User runs `/detective` command
3. System generates a new case and saves it to database
4. User can play through multiple different cases

### Existing Installations
1. Next update pulls these changes
2. `maintain_bot` scripts automatically run `initialize_database()`
3. New tables are created without affecting existing data
4. `/detective` command now works with multiple cases

### Future Updates
Any new tables added to `initialize_database()` will be automatically:
- Created on bot startup
- Applied when updates are pulled via maintain_bot
- Safe to deploy without manual intervention

## Files Modified
- `modules/db_helpers.py` - Added 45 lines for detective tables
- `test_detective_tables.py` - Created new test script (131 lines)

## Security Review
✅ CodeQL scan passed with 0 alerts
✅ No SQL injection vulnerabilities (uses parameterized queries)
✅ Proper foreign key constraints
✅ No sensitive data exposure

## Deployment Instructions
No special deployment steps required! The changes are automatically applied when:
1. The bot is restarted, OR
2. Updates are pulled via maintain_bot scripts

Simply merge and deploy as normal.
