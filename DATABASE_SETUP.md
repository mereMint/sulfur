# Database Setup Guide

This guide explains how to set up the database for Sulfur Bot with multiple options to suit your needs.

## Quick Start (Recommended)

### Interactive Setup Wizard

The **easiest** way to set up the database with guided options:

```bash
python setup_wizard.py
```

This wizard provides:
- 📋 Interactive menu to choose setup method
- 🔧 Automated Python Setup (Recommended) - Fully automated, cross-platform
- 🔐 Secure Bash Setup - Advanced security options for production
- ✓ Automatic migration execution
- ✓ Clear progress feedback

### Direct Automated Setup

For a completely automated setup without prompts:

```bash
python scripts/setup_database_auto.py
```

This automated script will:
- ✓ Check if MySQL/MariaDB is running (and start it if needed)
- ✓ Create the database with UTF-8 support
- ✓ Create a user with a secure 48-character password
- ✓ Save credentials securely to `config/database.json` (600 permissions)
- ✓ Run all database migrations automatically
- ✓ Verify the connection works

**No manual configuration required!**

---

## Alternative Setup Methods

### Option 1: Secure Bash Script (Linux/Mac/Termux)

For production environments where you want full control:

```bash
bash scripts/setup_database_secure.sh
```

**Features:**
- Generates cryptographically secure passwords
- Uses file locking to prevent race conditions
- Idempotent (can be run multiple times safely)
- Automatic MariaDB server detection and startup

**After running:**
```bash
python apply_migration.py --all
```

### Option 2: Simple Python Script (No Password)

For development or testing:

```bash
python setup_database.py
python apply_migration.py --all
```

⚠️ **Warning:** Creates a user with no password. Not recommended for production.

---

## Database Configuration File

All setup methods create `config/database.json`:

```json
{
  "host": "localhost",
  "user": "sulfur_bot_user",
  "password": "<secure-password>",
  "database": "sulfur_bot",
  "socket": "/var/run/mysqld/mysqld.sock",
  "charset": "utf8mb4"
}
```

**Security:**
- File permissions: `600` (owner read/write only)
- Password: 48-character cryptographically secure random string
- Never committed to git (in `.gitignore`)

---

## Migration System

### Viewing Migration Status

Check which migrations have been applied:

```bash
python apply_migration.py --verify
```

### Applying Specific Migrations

Apply a single migration:

```bash
python apply_migration.py scripts/db_migrations/001_base_user_stats.sql
```

Apply all pending migrations:

```bash
python apply_migration.py --all
```

### Force Rebuild (Drops All Tables)

⚠️ **WARNING:** This deletes ALL data!

```bash
python apply_migration.py --force --all
```

---

## Troubleshooting

### "Permission denied" on lock file

**Cause:** `/tmp` directory permissions or file descriptor issues.

**Fix:** The lock mechanism has been updated to use PID-based locking instead of file descriptors. Update your `setup_database_secure.sh` script.

### "MariaDB did not become ready"

**Cause:** MySQL/MariaDB is not installed or failed to start.

**Fix:**

**Ubuntu/Debian:**
```bash
sudo apt-get install mariadb-server mariadb-client
sudo systemctl start mariadb
```

**Termux:**
```bash
pkg install mariadb
mariadb-install-db
mariadbd-safe &
```

**Windows:**
```powershell
net start MySQL
```

### "Database user cannot connect"

**Cause:** User credentials mismatch or user doesn't exist.

**Fix:**
1. Delete the config file: `rm config/database.json`
2. Re-run setup: `python scripts/setup_database_auto.py`

### "Migration already applied"

**Not an error!** Migrations are tracked in the `schema_migrations` table to prevent double-application. This is normal and safe.

### Empty password in environment

If using `.env` file, make sure `DB_PASS=` is empty (not quoted):

```bash
# ✓ Correct
DB_PASS=

# ✗ Wrong
DB_PASS=""
DB_PASS=''
```

---

## Database Schema

The bot uses these main tables:

### Core Tables
- `players` - Main user profile (level, XP, balance)
- `user_stats` - Monthly statistics (messages, voice, games)
- `user_economy` - Economy transactions
- `user_customization` - User preferences (colors, language)

### Game Tables
- `blackjack_games`, `roulette_games`, `mines_games`, `tower_games`
- `russian_roulette_games`
- `detective_user_stats`, `detective_cases`
- `wordle_games`, `word_find_daily`, `word_find_games`

### Other Tables
- `music_history` - Music playback tracking
- `transaction_history` - Economy transactions
- `wrapped_registrations` - Year-end wrapped feature
- `schema_migrations` - Migration tracking

### Views
- `v_user_profiles` - Unified user data view
- `v_user_game_stats` - Game statistics per user
- `v_user_music_stats` - Music activity per user

---

## Advanced Configuration

### Custom Database Name

Set environment variables before running setup:

```bash
export DB_NAME=my_bot_database
export DB_USER=my_bot_user
export DB_HOST=localhost
python scripts/setup_database_auto.py
```

### Remote Database

1. Set `DB_HOST` to the remote server IP
2. Ensure MySQL allows remote connections
3. Run setup script

### Using `.env` File

Create `.env` file (copy from `.env.example`):

```bash
DB_HOST=localhost
DB_USER=sulfur_bot_user
DB_PASS=your_password_here
DB_NAME=sulfur_bot
```

**Note:** The automatic setup script generates and saves the password automatically, so you don't need to set `DB_PASS` manually.

---

## Automatic Setup on Bot Startup

The bot will automatically check if the database is configured when it starts. If not, it will show helpful instructions.

To enable automatic setup on first run, modify `bot.py` to use:

```python
from modules.database_auto_init import ensure_database_ready

# At bot startup
ensure_database_ready(auto_setup=True)  # Will run setup if needed
```

---

## Security Best Practices

1. ✓ **Use the automated setup** - Generates secure passwords automatically
2. ✓ **Never commit** `config/database.json` to git
3. ✓ **Use strong passwords** - 48+ character random passwords
4. ✓ **Restrict file permissions** - 600 for config files
5. ✓ **Regular backups** - Backup your database regularly
6. ✓ **Update regularly** - Keep MySQL/MariaDB updated

---

## Getting Help

If you encounter issues:

1. Check this guide first
2. Look at error messages carefully
3. Verify MySQL/MariaDB is running: `systemctl status mariadb`
4. Check config file exists: `ls -la config/database.json`
5. Test connection: `python -c "from modules.database_config import DatabaseConfig; print(DatabaseConfig.load())"`

---

## Summary

**For most users:**
```bash
python scripts/setup_database_auto.py
python bot.py
```

That's it! 🚀
