#!/bin/bash

# This script sets the necessary environment variables and starts the Sulfur bot on Linux/macOS.
# To run it:
# 1. Make it executable: chmod +x ./start_bot.sh
# 2. Run the script with: ./start_bot.sh

# --- FIX: Set the working directory to the script's location ---
# This ensures that relative paths for files like .env and bot.py work correctly.
cd "$(dirname "$0")"

# --- NEW: Load environment variables from .env file ---
# This makes the script runnable on its own, without relying on the parent.
if [ -f .env ]; then
    echo "Loading environment variables from .env file..."
    set -a # automatically export all variables
    source .env
    set +a # stop automatically exporting
fi

# --- NEW: Setup Logging ---
LOG_DIR="logs"
if [ ! -d "$LOG_DIR" ]; then
    mkdir -p "$LOG_DIR"
    echo "Created logs directory at $LOG_DIR"
fi

LOG_TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_FILE="${LOG_DIR}/startup_log_${LOG_TIMESTAMP}.log"

# --- NEW: Define database connection details at the top ---
SYNC_FILE="database_sync.sql"
DB_NAME="sulfur_bot"
DB_USER="sulfur_bot_user"

# --- NEW: Define sync file ---
SYNC_FILE="database_sync.sql"

# This function will be executed when the script is stopped (e.g., with CTRL+C)
cleanup() {
    echo "Script stopped. Log file is at: $LOG_FILE"
    # --- NEW: Export database on exit for synchronization ---
    echo "Exporting database to $SYNC_FILE for synchronization..."
    mariadb-dump --user=$DB_USER --host=localhost --default-character-set=utf8mb4 $DB_NAME > "$SYNC_FILE"
    echo "Database export complete. Remember to commit and push '$SYNC_FILE' if you want to sync this state." | tee -a "$LOG_FILE"
}
trap cleanup EXIT

echo "Logging this session to: $LOG_FILE"

echo "Checking for updates from the repository..."
echo "  -> Stashing local changes to avoid conflicts..."
git stash > /dev/null 2>&1
# --- NEW: Get the commit hash before pulling ---
OLD_HEAD=$(git rev-parse HEAD)
echo "  -> Pulling latest version from the repository..."
git pull > /dev/null 2>&1
# --- NEW: Get the commit hash after pulling ---
NEW_HEAD=$(git rev-parse HEAD)
echo "  -> Re-applying stashed local changes..."
git stash pop > /dev/null 2>&1
echo "Update check complete."

# --- NEW: Install/update Python dependencies ---
echo "Installing/updating Python dependencies from requirements.txt..."
python3 -m pip install -r requirements.txt
echo "Dependencies are up to date."

# --- NEW: Check if the sync file was updated and import it ---
if [ "$OLD_HEAD" != "$NEW_HEAD" ] && git diff --name-only "$OLD_HEAD" "$NEW_HEAD" | grep -q "$SYNC_FILE"; then
    echo "Database sync file has been updated. Importing new data..."
    mariadb --user="$DB_USER" --host=localhost --default-character-set=utf8mb4 "$DB_NAME" < "$SYNC_FILE"
    echo "Database import complete."
fi

# --- NEW: Ensure maintenance scripts are always executable after a pull ---
echo "Ensuring core scripts are executable..."
chmod +x ./maintain_bot.sh
chmod +x ./maintain_bot.ps1

# --- REFACTORED: Check if MariaDB/MySQL is running and start if necessary ---
if ! pgrep -x "mysqld" > /dev/null; then
    echo "MariaDB/MySQL server not detected."
    # Check if we are in Termux by looking for its specific directory structure
    if [[ -d "/data/data/com.termux/files/usr" ]]; then
        echo "Termux environment detected. Starting server with 'mysqld_safe'..."
        mysqld_safe --user=root --datadir=/data/data/com.termux/files/usr/var/lib/mysql &
        sleep 5 # Give it a moment to start
    fi
fi

echo "Backing up the database..."
BACKUP_DIR="backups"

# Create backup directory if it doesn't exist
if [ ! -d "$BACKUP_DIR" ]; then
    mkdir -p "$BACKUP_DIR"
fi

TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_backup_${TIMESTAMP}.sql"

# Use mariadb-dump on Termux/Linux systems
mariadb-dump --user="$DB_USER" --host=localhost --default-character-set=utf8mb4 "$DB_NAME" > "$BACKUP_FILE"
echo "Backup created successfully at $BACKUP_FILE"

# --- NEW: Clean up old backups ---
echo "Cleaning up old backups (older than 7 days)..."
# The 'find' command searches for .sql files older than 7 days and deletes them.
find "$BACKUP_DIR" -type f -name "*.sql" -mtime +7 -print -delete
echo "Cleanup complete."

echo "Starting the bot... (Press CTRL+C to stop)"
# --- FIX: Pipe the bot's output to tee for reliable logging in tmux ---
# This sends all output (stdout and stderr) from the Python script to the tee command,
# which then writes it to both the console (the tmux pane) and the log file.
python3 -u bot.py 2>&1 | tee -a "$LOG_FILE"

# --- NEW: Pause on error to allow copying logs ---
exit_code=${PIPESTATUS[0]} # Get the exit code of the python script, not tee
if [ $exit_code -ne 0 ]; then
    echo "--------------------------------------------------------"
    echo "The bot process exited with an error (Exit Code: $exit_code)."
    echo "The script is paused. Press Enter to close this window."
    read
fi