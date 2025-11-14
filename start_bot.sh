#!/bin/bash

# This script sets the necessary environment variables and starts the Sulfur bot on Linux/macOS.
# To run it:
# 1. Make it executable: chmod +x ./start_bot.sh
# 2. Run the script with: ./start_bot.sh

# --- NEW: Setup Logging ---
LOG_DIR="logs"
if [ ! -d "$LOG_DIR" ]; then
    mkdir -p "$LOG_DIR"
    echo "Created logs directory at $LOG_DIR"
fi

LOG_TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_FILE="${LOG_DIR}/startup_log_${LOG_TIMESTAMP}.log"

# This function will be executed when the script is stopped (e.g., with CTRL+C)
cleanup() {
    echo "Script stopped. Log file is at: $LOG_FILE"
    # Add any other cleanup here, like stopping mysql if it was started by the script.
}
trap cleanup EXIT

echo "Logging this session to: $LOG_FILE"

# The 'exec > >(tee -a "$LOG_FILE") 2>&1' part redirects all subsequent
# standard output and standard error to both the console and the log file.
exec > >(tee -a "$LOG_FILE") 2>&1

echo "Setting environment variables for the bot..."
export DISCORD_BOT_TOKEN="MTQzODU5NTUzNjE1MTM4MDAxOA.GwuLkF.NYHg6QXtQfhGIPK6SRA8TxDo4-wOtJrTzn00EU"
export GEMINI_API_KEY="AIzaSyD7h08ULN7KXhYCFFiIa6MPEbN_TnL5COU"
export OPENAI_API_KEY="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" # <-- ADD YOUR OPENAI KEY HERE

echo "Checking for updates from the repository..."
echo "  -> Stashing local changes to avoid conflicts..."
git stash
echo "  -> Pulling latest version from the repository..."
git pull
echo "  -> Re-applying stashed local changes..."
git stash pop
echo "Update check complete."

# --- NEW: Check if MySQL is already running ---
if ! pgrep -x "mysqld" > /dev/null
then
    echo "MySQL not running. Starting server..."
    mysqld_safe -u root &
    sleep 5 # Give it a moment to start
fi

echo "Backing up the database..."
BACKUP_DIR="backups"
DB_NAME="sulfur_bot"
DB_USER="sulfur_bot_user"

# Create backup directory if it doesn't exist
if [ ! -d "$BACKUP_DIR" ]; then
    mkdir -p "$BACKUP_DIR"
fi

TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_backup_${TIMESTAMP}.sql"

# Note: This assumes mysqldump is in the system's PATH and MySQL is running.
mysqldump --user=$DB_USER --host=localhost $DB_NAME > "$BACKUP_FILE"
echo "Backup created successfully at $BACKUP_FILE"

# --- NEW: Clean up old backups ---
echo "Cleaning up old backups (older than 7 days)..."
# The 'find' command searches for .sql files older than 7 days and deletes them.
find "$BACKUP_DIR" -type f -name "*.sql" -mtime +7 -print -delete
echo "Cleanup complete."

echo "Starting the bot... (Press CTRL+C to stop)"
python3 ./bot.py