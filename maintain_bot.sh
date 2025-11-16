#!/bin/bash
#
# This script acts as a watcher to maintain the Sulfur bot on Linux/Termux.
# To run it:
# 1. Make it executable: chmod +x maintain_bot.sh
# 2. Run the script with: ./maintain_bot.sh

echo "--- Sulfur Bot Maintenance Watcher ---"
echo "Press 'Q' at any time to gracefully shut down the bot and exit."

# --- Import shared functions ---
cd "$(dirname "$0")"
source ./scripts/shared_functions.sh

# --- NEW: Centralized Logging Setup ---
LOG_DIR="logs"
mkdir -p "$LOG_DIR"
LOG_TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_FILE="$LOG_DIR/session_${LOG_TIMESTAMP}.log"

echo "Logging this session to: $LOG_FILE" | tee -a "$LOG_FILE"
# --- Ensure Python environment is ready ---
echo "Checking Python virtual environment..."
VENV_PYTHON=$(ensure_venv)
if [ $? -ne 0 ]; then
    echo "Failed to set up Python environment. Exiting."
    exit 1
fi
echo "Python environment is ready."

DB_SYNC_FILE="config/database_sync.sql"

# --- NEW: Declare PIDs globally for the trap ---
STATUS_FILE="config/bot_status.json"
WEB_DASHBOARD_PID=""
BOT_PID=""

# --- Function to start and verify the Web Dashboard ---
function start_web_dashboard {
    echo "Starting the Web Dashboard..."
    # Start in the background, get its PID, and append logs to the central log file.
    "$VENV_PYTHON" -u web/web_dashboard.py >> "$LOG_FILE" 2>&1 &
    WEB_DASHBOARD_PID=$!
    echo "Web Dashboard process started (PID: $WEB_DASHBOARD_PID)"

    echo "Waiting for the Web Dashboard to become available on http://localhost:5000..."
    for i in {1..15}; do
        # Check if the process is still running
        if ! ps -p $WEB_DASHBOARD_PID > /dev/null; then
            echo "ERROR: Web Dashboard process terminated unexpectedly during startup. Check log for errors."
            return 1
        fi
        # Check if the port is open
        if curl --output /dev/null --silent --head --fail http://localhost:5000 2>/dev/null; then
            echo "Web Dashboard is online and ready."
            return 0
        fi
        sleep 1
    done

    echo "ERROR: Web Dashboard did not become available. Shutting down."
    kill -9 $WEB_DASHBOARD_PID 2>/dev/null
    return 1
}

# --- NEW: Trap for graceful shutdown on CTRL+C or script termination ---
function cleanup {
    echo -e "\nCaught exit signal. Shutting down all child processes..."
    # --- NEW: Perform final DB export on shutdown ---
    if [ ! -z "$DB_NAME" ] && [ ! -z "$DB_USER" ]; then
        echo "Exporting database to $DB_SYNC_FILE for synchronization..."
        mysqldump --user="$DB_USER" --host=localhost --default-character-set=utf8mb4 "$DB_NAME" > "$DB_SYNC_FILE" 2>/dev/null
        echo "Database export complete."
    fi

    echo '{"status": "Shutdown"}' > "$STATUS_FILE"
    # Kill the bot process if it's running
    if [ -n "$BOT_PID" ] && ps -p $BOT_PID > /dev/null; then
        echo "Stopping Bot (PID: $BOT_PID)..."
        kill -9 $BOT_PID
    fi
    # Kill the web dashboard process if it's running
    if [ -n "$WEB_DASHBOARD_PID" ] && ps -p $WEB_DASHBOARD_PID > /dev/null; then
        echo "Stopping Web Dashboard (PID: $WEB_DASHBOARD_PID)..."
        kill -9 $WEB_DASHBOARD_PID
    fi
    echo "Cleanup complete. Exiting."
}
trap cleanup SIGINT SIGTERM EXIT

# --- Start the Web Dashboard for the first time ---
start_web_dashboard
if [ $? -ne 0 ]; then
    echo "Failed to start the Web Dashboard. Exiting."
    exit 1
fi
# --- Main loop ---
while true; do
    echo '{"status": "Starting..."}' > "$STATUS_FILE"
    echo "Starting the bot process..."
    # --- REFACTORED: Start the script and then find the actual Python child process ---
    # Start the startup script in the background
    ./scripts/start_bot.sh >> "$LOG_FILE" 2>&1 &
    START_SCRIPT_PID=$!

    # Wait for the startup script to launch the python process and then find it.
    BOT_PID=""
    for i in {1..10}; do
        # Find a python process that is a child of our startup script
        BOT_PID=$(pgrep -P $START_SCRIPT_PID -f "python -u -X utf8 bot.py")
        if [ -n "$BOT_PID" ]; then
            break
        fi
        sleep 1
    done

    # Now that we have the real bot PID, we can monitor it.
    echo "{\"status\": \"Running\", \"pid\": \"$BOT_PID\"}" > "$STATUS_FILE"
    echo "Bot is running (PID: $BOT_PID). Checking for updates every 60 seconds."

    # Inner loop to monitor the running bot
    while ps -p $BOT_PID > /dev/null; do
        # Check for shutdown key press (non-blocking read)
        read -t 1 -n 1 key
        if [[ $key == "q" || $key == "Q" ]]; then
            echo "Shutdown key ('Q') pressed. Stopping bot and exiting..."
            kill -9 $BOT_PID
            sleep 2 # Give it a moment for the exit trap to run

            # Final DB commit
            if [[ -n $(git status --porcelain "$DB_SYNC_FILE") ]]; then
                echo "Final database changes detected. Committing and pushing..."
                git add "$DB_SYNC_FILE"
                git commit -m "chore: Sync database schema on shutdown"
                git push
            fi
            
            echo "Shutdown complete."
            # The trap will handle killing the web dashboard
            exit 0
        fi

        # Check for control flags
        if [ -f "stop.flag" ]; then
            echo "Stop signal received. Shutting down..."
            rm -f "stop.flag"
            # The exit command will trigger the 'trap cleanup' function
            exit 0
        fi
        if [ -f "restart.flag" ]; then
            echo "Restart signal received. Restarting bot..."
            rm -f "restart.flag"
            kill $BOT_PID # This will break the inner loop and trigger a restart
        fi

        # Check for git updates every 60 seconds
        # --- NEW: Perform git operations here, not in start_bot.sh ---
        git remote update
        STATUS=$(git status -uno)

        if [[ "$STATUS" == *"Your branch is behind"* ]]; then
            echo '{"status": "Updating..."}' > "$STATUS_FILE"
            echo "New version found! Restarting the bot to apply updates..."
            
            # Commit DB changes before pulling
            echo "Exporting database before update..."
            mysqldump --user="$DB_USER" --host=localhost --default-character-set=utf8mb4 "$DB_NAME" > "$DB_SYNC_FILE"
            if [[ -n $(git status --porcelain "$DB_SYNC_FILE") ]]; then
                git add "$DB_SYNC_FILE"
                git commit -m "chore: Sync database schema before update"
                git push
            fi

            git pull
            kill -9 $BOT_PID
            sleep 2
            break # Exit inner loop to restart
        fi

        sleep 59 # Sleep for the rest of the minute
    done

    echo '{"status": "Stopped"}' > "$STATUS_FILE"
    echo "Bot process stopped. It will be restarted shortly..."
    sleep 5
done