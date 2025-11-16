#!/bin/bash

# This script sets the necessary environment variables and starts the Sulfur bot on Linux/Termux.
# It is intended to be called by maintain_bot.sh.

# --- Set the working directory to the script's location ---
cd "$(dirname "$0")"

# --- Import shared functions ---
source ./shared_functions.sh

# --- Database connection details ---
# These should be set in your .env file, but we provide defaults
DB_NAME=${DB_NAME:-"sulfur_bot"}
DB_USER=${DB_USER:-"sulfur_bot_user"}

# --- Check for Python executable before proceeding ---
if ! command -v python &> /dev/null; then
    echo -e "\033[0;31m--------------------------------------------------------\033[0m"
    echo -e "\03f[0;31mError: 'python' command not found.\033[0m"
    echo -e "\033[0;33mPlease ensure Python is installed in Termux (pkg install python).\033[0m"
    read -p "Press Enter to exit."
    exit 1
fi

# --- Setup and use a Python Virtual Environment ---
PYTHON_EXECUTABLE=$(ensure_venv)

# --- Check if MariaDB (MySQL) is running ---
if ! pgrep -x "mysqld" > /dev/null; then
    echo "MariaDB not running. Starting it now..."
    # This is the standard command to start the MariaDB server in Termux
    if command -v mysqld_safe &> /dev/null; then
        mysqld_safe -u root &
    else
        echo "WARNING: mysqld_safe not found. Attempting to start MySQL..."
        mysqld -u root &
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
mysqldump --user="$DB_USER" --host=localhost --default-character-set=utf8mb4 "$DB_NAME" > "$BACKUP_FILE"
echo "Backup created successfully at $BACKUP_FILE"

# --- Clean up old backups (older than 7 days) ---
echo "Cleaning up old backups (older than 7 days)..."
find "$BACKUP_DIR" -name "*.sql" -type f -mtime +7 -print -delete
echo "Cleanup complete."

echo "Starting the bot... (Press CTRL+C to stop if running manually)"
# The -u flag forces python's output to be unbuffered.
"$PYTHON_EXECUTABLE" -u -X utf8 bot.py