#!/bin/bash

# This script acts as a watcher to maintain the Sulfur bot on Linux/Termux.
# To run it:
# 1. Make it executable: chmod +x maintain_bot.sh
# 2. Run the script with: ./maintain_bot.sh

echo "--- Sulfur Bot Maintenance Watcher ---"
echo "Press 'Q' at any time to gracefully shut down the bot and exit."

# --- Import shared functions ---
cd "$(dirname "$0")"
source ./shared_functions.sh

# --- Ensure Python environment is ready ---
echo "Checking Python virtual environment..."
VENV_PYTHON=$(ensure_venv)
echo "Python environment is ready."

DB_SYNC_FILE="database_sync.sql"

# --- Function to start and verify the Web Dashboard ---
function start_web_dashboard {
    echo "Starting the Web Dashboard..."
    # Start in the background and get its PID
    "$VENV_PYTHON" -u web_dashboard.py &> web_dashboard.log &
    WEB_DASHBOARD_PID=$!
    echo "Web Dashboard process started (PID: $WEB_DASHBOARD_PID)"

    echo "Waiting for the Web Dashboard to become available on http://localhost:5000..."
    for i in {1..15}; do
        # Check if the process is still running
        if ! ps -p $WEB_DASHBOARD_PID > /dev/null; then
            echo "Web Dashboard process terminated unexpectedly during startup. Check web_dashboard.log for errors."
            return 1
        fi
        # Check if the port is open
        if curl --output /dev/null --silent --head --fail http://localhost:5000; then
            echo "Web Dashboard is online and ready."
            return 0
        fi
        sleep 1
    done

    echo "Error: Web Dashboard did not become available. Shutting down."
    kill -9 $WEB_DASHBOARD_PID
    return 1
}

# --- Start the Web Dashboard for the first time ---
start_web_dashboard
if [ $? -ne 0 ]; then
    echo "Failed to start the Web Dashboard. Exiting."
    exit 1
fi

# --- Main loop ---
while true; do
    echo "Starting the bot process..."
    # Start the main bot script in the background
    ./start_bot.sh &
    BOT_PID=$!

    echo "Bot is running (PID: $BOT_PID). Checking for updates every 60 seconds."

    # Inner loop to monitor the running bot
    while ps -p $BOT_PID > /dev/null; do
        # Check for shutdown key press (non-blocking read)
        read -t 1 -n 1 key
        if [[ $key == "q" || $key == "Q" ]]; then
            echo "Shutdown key ('Q') pressed. Stopping bot and exiting..."
            kill $BOT_PID
            sleep 2 # Give it a moment for the exit trap to run

            # Final DB commit
            if [[ -n $(git status --porcelain "$DB_SYNC_FILE") ]]; then
                echo "Final database changes detected. Committing and pushing..."
                git add "$DB_SYNC_FILE"
                git commit -m "chore: Sync database schema on shutdown"
                git push
            fi
            
            echo "Shutdown complete."
            kill -9 $WEB_DASHBOARD_PID
            exit 0
        fi

        # Check for control flags
        if [ -f "stop.flag" ]; then
            echo "Stop signal received. Shutting down..."
            rm -f "stop.flag"
            kill $BOT_PID
            # Trigger the shutdown sequence by sending 'q' to ourselves
            echo "q" | ./maintain_bot.sh &> /dev/null
            exit 0
        fi
        if [ -f "restart.flag" ]; then
            echo "Restart signal received. Restarting bot..."
            rm -f "restart.flag"
            kill $BOT_PID # This will break the inner loop and trigger a restart
        fi

        # Check for git updates every 60 seconds
        git remote update
        STATUS=$(git status -uno)

        if [[ "$STATUS" == *"Your branch is behind"* ]]; then
            echo "New version found! Restarting the bot to apply updates..."
            touch "update_pending.flag"
            kill $BOT_PID
            sleep 2
            # The start_bot.sh script handles the pre-pull commit via its exit trap
            rm -f "update_pending.flag"
            break # Exit inner loop to restart
        fi

        sleep 59 # Sleep for the rest of the minute
    done

    echo "Bot process stopped. It will be restarted shortly..."
    sleep 5
done