#!/bin/bash

# This script sets the necessary environment variables and starts the Sulfur bot on Linux/Termux.
# It is intended to be called by maintain_bot.sh.

LOG_FILE="$1"
# --- Set the working directory to project root (parent of scripts) ---
SCRIPT_DIR="$(dirname "$0")"
cd "$SCRIPT_DIR/.." || exit 1

# --- Import shared functions ---
source ./scripts/shared_functions.sh

# --- Database connection details ---
# These should be set in your .env file, but we provide defaults
DB_NAME=${DB_NAME:-"sulfur_bot"}
DB_USER=${DB_USER:-"sulfur_bot_user"}

# --- Check for Python executable before proceeding ---
if ! command -v python &> /dev/null; then
    echo -e "\033[0;31m--------------------------------------------------------\033[0m"
    echo -e "\033[0;31mError: 'python' command not found.\033[0m"
    echo -e "\033[0;33mPlease ensure Python is installed in Termux (pkg install python).\033[0m"
    read -r -p "Press Enter to exit."
    exit 1
fi

# --- Setup and use a Python Virtual Environment ---
PYTHON_EXECUTABLE=$(ensure_venv)

# --- Check if MariaDB (MySQL) is running ---
if ! pgrep -x "mysqld\|mariadbd" > /dev/null; then
    echo "MariaDB not running. Starting it now..."
    # Prefer mariadb commands in Termux, fall back to mysql commands
    if command -v mariadbd-safe &> /dev/null; then
        mariadbd-safe --datadir="$PREFIX/var/lib/mysql" &
    elif command -v mysqld_safe &> /dev/null; then
        mysqld_safe -u root &
    else
        echo "WARNING: Neither mariadbd-safe nor mysqld_safe found. Attempting to start MariaDB..."
        if command -v mariadbd &> /dev/null; then
            mariadbd -u root &
        else
            mysqld -u root &
        fi
    fi
else
    echo "MariaDB server is already running."
fi
sleep 5 # Give the database a moment to initialize

echo "Backing up the database..."
BACKUP_DIR="backups"
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_backup_${TIMESTAMP}.sql"

# Use mariadb-dump if available (Termux), otherwise mysqldump
if command -v mariadb-dump &> /dev/null; then
    mariadb-dump --user="$DB_USER" --host=localhost --default-character-set=utf8mb4 "$DB_NAME" > "$BACKUP_FILE"
else
    mysqldump --user="$DB_USER" --host=localhost --default-character-set=utf8mb4 "$DB_NAME" > "$BACKUP_FILE"
fi
echo "Backup created successfully at $BACKUP_FILE"

# --- Clean up old backups (older than 7 days) ---
echo "Cleaning up old backups (older than 7 days)..."
find "$BACKUP_DIR" -name "*.sql" -type f -mtime +7 -print -delete
echo "Cleanup complete."

echo "Starting the bot... (Press CTRL+C to stop if running manually)"
if [ -z "$LOG_FILE" ]; then
    TS=$(date +"%Y-%m-%d_%H-%M-%S")
    mkdir -p logs
    LOG_FILE="logs/bot_session_${TS}.log"
fi
echo "Bot output redirected to: $LOG_FILE"
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8
"$PYTHON_EXECUTABLE" -u -X utf8 bot.py >> "$LOG_FILE" 2>&1