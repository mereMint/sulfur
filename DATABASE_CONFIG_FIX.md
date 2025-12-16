# Database Configuration Fix - Empty Username Error

## Problem

Users were experiencing database connection errors with empty usernames in their MariaDB logs:

```
Access denied for user ''@'localhost' to database 'sulfur_bot'
```

This error occurred when the bot tried to connect to the database with an empty username, even though the default value was supposed to be `sulfur_bot_user`.

## Root Cause

The issue was caused by how Python's `os.environ.get()` function handles empty string values from the `.env` file:

1. **The Problem Pattern:**
   ```python
   # In .env file:
   DB_USER=""
   
   # After load_dotenv():
   os.environ["DB_USER"] = ""  # Key exists with empty value
   
   # In bot.py:
   DB_USER = os.environ.get("DB_USER", "sulfur_bot_user")
   # Result: "" (NOT "sulfur_bot_user")
   # The default is NOT used because the key exists!
   ```

2. **Why This Happened:**
   - Some setup scripts created `.env` files with quoted empty strings: `DB_USER=""`
   - When `load_dotenv()` parsed this, it set the environment variable to an empty string
   - `os.environ.get(key, default)` only returns the default if the key is **missing**
   - If the key exists (even with an empty value), it returns that empty value
   - The bot then tried to connect with username `""` instead of the default

## The Fix

We implemented a multi-layered solution:

### 1. Defensive Credential Loading (bot.py, setup_wizard.py)

Changed from:
```python
DB_USER = os.environ.get("DB_USER", "sulfur_bot_user")
```

To:
```python
DB_USER = os.environ.get("DB_USER", "sulfur_bot_user").strip() or "sulfur_bot_user"
```

**How this works:**
- `.strip()` removes whitespace
- `or "default"` uses the default if the result is empty/falsy
- This handles both missing keys AND empty values

### 2. Early Validation (bot.py, db_helpers.py)

Added validation that exits with a helpful error message if credentials are empty:

```python
if not DB_USER or DB_USER == "":
    logger.critical("DB_USER is not set or is empty in .env file!")
    # ... helpful error message ...
    exit(1)
```

### 3. Fixed Setup Scripts (quick_setup.sh, quick_setup.ps1)

**Before:**
```bash
DB_HOST="localhost"
DB_USER="sulfur_bot_user"
DB_PASS=""
DB_NAME="sulfur_bot"
```

**After:**
```bash
# No quotes unless the value contains spaces
DB_HOST=localhost
DB_USER=sulfur_bot_user
DB_PASS=
DB_NAME=sulfur_bot
```

**Why:** When using quotes in `.env` files, some values may include the quotes as part of the string. For database credentials that don't contain spaces, quotes are unnecessary and can cause issues.

### 4. Improved Documentation (.env.example)

Added warnings in the `.env.example` file:

```bash
# Database Configuration
# IMPORTANT: Do not use quotes around these values unless they contain spaces
# DO NOT use empty quotes like DB_USER="" - either set a value or leave as:
DB_USER=sulfur_bot_user
```

## How to Fix Existing Installations

If you're experiencing this error, follow these steps:

### Quick Fix

1. Open your `.env` file
2. Find the database configuration section
3. Ensure it looks like this (no quotes, no empty values):
   ```bash
   DB_HOST=localhost
   DB_USER=sulfur_bot_user
   DB_PASS=
   DB_NAME=sulfur_bot
   ```
4. Save and restart the bot

### Complete Fix

If the issue persists:

1. **Delete the old .env file:**
   ```bash
   rm .env
   ```

2. **Copy from the example:**
   ```bash
   cp .env.example .env
   ```

3. **Edit the new .env file and fill in your credentials:**
   ```bash
   nano .env
   # or
   vi .env
   ```

4. **Ensure database credentials are set correctly:**
   - `DB_USER=sulfur_bot_user` (no quotes)
   - `DB_NAME=sulfur_bot` (no quotes)
   - `DB_PASS=` can be empty (that's OK for passwordless MySQL users)

5. **Save and restart the bot**

## Prevention

The bot now validates credentials on startup and will show a clear error message if:
- DB_USER is empty or missing
- DB_NAME is empty or missing
- The .env file hasn't been properly configured

Example error message:
```
======================================================================
ERROR: Database Configuration Error
======================================================================

DB_USER environment variable is not set or is empty.

To fix this issue:
1. Open your .env file
2. Ensure DB_USER is set to a valid username:
   DB_USER=sulfur_bot_user
3. Do NOT use empty quotes: DB_USER="" or DB_USER=''
4. Do NOT leave it blank: DB_USER=

If you don't have a .env file, copy from .env.example:
   cp .env.example .env
   # Then edit .env with your credentials

======================================================================
```

## Technical Details

### Why Empty Password is OK, But Empty Username is Not

- **MySQL/MariaDB** allows passwordless authentication for local connections
- This is configured with: `DB_PASS=` (empty value)
- However, a **username is always required** for authentication
- An empty username `DB_USER=` would try to connect as user `""`, which will always fail

### Environment Variable Behavior

```python
import os

# Case 1: Key doesn't exist
os.environ.get("MISSING_KEY", "default")  # Returns: "default"

# Case 2: Key exists with empty value
os.environ["EMPTY_KEY"] = ""
os.environ.get("EMPTY_KEY", "default")  # Returns: "" (NOT "default")

# Case 3: Our fix
os.environ["EMPTY_KEY"] = ""
os.environ.get("EMPTY_KEY", "default").strip() or "default"  # Returns: "default"
```

## Related Files

The following files were modified to implement this fix:

1. `bot.py` - Added credential validation and defensive loading
2. `modules/db_helpers.py` - Added validation in `init_db_pool()`
3. `setup_wizard.py` - Added defensive loading and validation
4. `master_setup.py` - Added prompts for all DB credentials
5. `.env.example` - Added documentation and warnings
6. `quick_setup.sh` - Removed quotes from DB credentials
7. `quick_setup.ps1` - Removed quotes from DB credentials

## Testing

To test if your configuration is correct:

```bash
# Check if .env file exists and has correct format
cat .env | grep "^DB_"

# Expected output (values without quotes):
DB_HOST=localhost
DB_USER=sulfur_bot_user
DB_PASS=
DB_NAME=sulfur_bot

# Start the bot - it will validate credentials on startup
python bot.py
```

If configuration is correct, you'll see:
```
[INFO] Initializing connection pool: sulfur_bot_user@localhost/sulfur_bot
[INFO] Database connection pool initialized successfully
```

If configuration is wrong, you'll see a detailed error message with fix instructions.

## Summary

- **Problem:** Empty username in database connection due to `.env` file having `DB_USER=""`
- **Root Cause:** `os.environ.get()` returns empty string instead of default when key exists
- **Solution:** Use `.strip() or "default"` pattern + validation + fixed setup scripts
- **Prevention:** Clear error messages + improved documentation + better defaults
