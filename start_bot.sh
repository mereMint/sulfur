#!/bin/bash

# This script sets the necessary environment variables and starts the Sulfur bot in Termux.
# To run it:
# 1. Make sure this script is executable: chmod +x start_bot.sh
# 2. Run the script with: ./start_bot.sh

# --- Set the working directory to the script's location ---
cd "$(dirname "$0")"

# --- Load environment variables from .env file ---
if [ -f .env ]; then
  # A safer way to load .env files in bash
  set -o allexport
  source .env
  set +o allexport
fi

# --- Setup Logging ---
LOG_DIR="logs"
mkdir -p "$LOG_DIR"

LOG_TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_FILE="${LOG_DIR}/bot_session_${LOG_TIMESTAMP}.log"

echo "Logging this session to: $LOG_FILE"

# --- Database connection details ---
# These should be set in your .env file, but we provide defaults
DB_NAME=${DB_NAME:-"sulfur_bot"}
DB_USER=${DB_USER:-"sulfur_bot_user"}

# --- Register an action to export the database on script exit ---
SYNC_FILE="database_sync.sql"

cleanup() {
    echo "Exporting database to $SYNC_FILE for synchronization..."
    # In Termux, mysqldump is directly available if mariadb is installed
    mysqldump --user="$DB_USER" --host=localhost --default-character-set=utf8mb4 "$DB_NAME" > "$SYNC_FILE"
    echo "Database export complete."
}
trap cleanup EXIT

echo "Checking for updates from the repository..."
echo "  -> Stashing local changes to avoid conflicts..."
git stash > /dev/null

echo "  -> Pulling latest version from the repository..."
git pull
if [ $? -ne 0 ]; then
    echo -e "\033[0;31m--------------------------------------------------------\033[0m"
    echo -e "\033[0;31mError: 'git pull' failed. The script cannot continue.\033[0m"
    echo -e "\033[0;33mPlease check your internet connection and git status, then try again.\033[0m"
    read -p "Press Enter to exit."
    exit 1
fi

echo "  -> Re-applying stashed local changes..."
git stash pop > /dev/null
echo "Update check complete."

# --- Check for Python executable before proceeding ---
if ! command -v python &> /dev/null; then
    echo -e "\033[0;31m--------------------------------------------------------\033[0m"
    echo -e "\03f[0;31mError: 'python' command not found.\033[0m"
    echo -e "\033[0;33mPlease ensure Python is installed in Termux (pkg install python).\033[0m"
    read -p "Press Enter to exit."
    exit 1
fi

# --- Install/update Python dependencies ---
echo "Installing/updating Python dependencies from requirements.txt..."
pip install -r requirements.txt
echo "Dependencies are up to date."

# --- Check if MariaDB (MySQL) is running ---
if ! pgrep -x "mysqld" > /dev/null; then
    echo "MariaDB not running. Starting it now..."
    # This is the standard command to start the MariaDB server in Termux
    mysqld_safe -u root &
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
# `tee` splits the output to both the console and the log file.
python -u -X utf8 bot.py 2>&1 | tee -a "$LOG_FILE"