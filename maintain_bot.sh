#!/bin/bash

# This script acts as a watcher to maintain the Sulfur bot in a Termux environment.
# It starts the bot and then checks for updates from the Git repository.
# If updates are found, it automatically restarts the bot.
#
# --- How to Stop ---
# To gracefully shut down the bot and this script, press the 'Q' key.
# The script will stop the bot, perform a final database commit if needed, and then exit.
#

# --- How to run it ---
# 1. Make sure this script is executable: chmod +x maintain_bot.sh
# 2. Run the script with: ./maintain_bot.sh

echo "--- Sulfur Bot Maintenance Watcher (Termux Version) ---"
echo -e "\033[0;33mPress 'Q' at any time to gracefully shut down the bot and exit.\033[0m"

# Define the file to watch for database changes
DB_SYNC_FILE="database_sync.sql"

# --- NEW: Start the Web Dashboard in the background ---
echo "Starting the Web Dashboard..."
pip install -r requirements.txt &>/dev/null
python -u web_dashboard.py &
WEB_PID=$!
echo "Web Dashboard is running at http://localhost:5000 (PID: $WEB_PID)"


# Function to check for and commit database changes
commit_db_changes() {
    # Check if the sync file has any changes staged or unstaged
    if git status --porcelain | grep -q "$DB_SYNC_FILE"; then
        echo -e "\033[0;36mDatabase changes detected. Committing and pushing...\033[0m"
        git add "$DB_SYNC_FILE"
        git commit -m "chore: Sync database schema"
        git push
    fi
}

while true; do
    echo "Starting the bot process..."
    # Start the main bot script in the background
    ./start_bot.sh &
    
    # Get the Process ID (PID) of the background job
    BOT_PID=$!

    echo "Bot is running in the background (PID: $BOT_PID). Checking for updates..."

    # Loop while the bot process is still running
    # `kill -0` checks if a process with the given PID exists
    while kill -0 "$BOT_PID" 2>/dev/null; do
        # Check for shutdown key press without blocking
        # -t 0.1: timeout of 0.1s, -N 1: read 1 char
        if read -t 0.1 -N 1 key; then
            if [[ "$key" == "q" || "$key" == "Q" ]]; then
                echo -e "\033[0;33mShutdown key ('Q') pressed. Stopping bot and exiting...\033[0m"
                kill "$BOT_PID"
                wait "$BOT_PID" 2>/dev/null # Wait for the process to terminate

                echo "Performing final database check..."
                commit_db_changes

                echo "Shutdown complete."
                kill "$WEB_PID" # Stop the web dashboard
                exit 0
            fi
        fi

        # --- NEW: Check for control flags from web dashboard ---
        if [ -f "stop.flag" ]; then
            echo -e "\033[0;33mStop signal received from web dashboard. Shutting down...\033[0m"
            kill "$BOT_PID"
            wait "$BOT_PID" 2>/dev/null
            rm -f "stop.flag"
            commit_db_changes
            kill "$WEB_PID" # Stop the web dashboard
            exit 0
        fi
        if [ -f "restart.flag" ]; then
            echo -e "\033[0;33mRestart signal received from web dashboard. Restarting bot...\033[0m"
            rm -f "restart.flag"
            # Force the update check to succeed, triggering a restart
            git remote update &>/dev/null
            break # Break inner loop to force restart
        fi

        sleep 15

        # Log the time of the update check
        date -u +"%Y-%m-%dT%H:%M:%SZ" > last_check.txt

        # Fetch the latest changes from the remote repository
        git remote update &>/dev/null
        
        # Check if the local branch is behind the remote
        if git status -uno | grep -q "Your branch is behind"; then
            echo "New version found in the repository! Restarting the bot to apply updates..."
            # Create the flag file to signal the bot to go idle
            touch update_pending.flag
            kill "$BOT_PID" # Stop the bot
            wait "$BOT_PID" 2>/dev/null # Wait for the process to terminate

            commit_db_changes

            # --- NEW: Check if the watcher script itself is being updated ---
            git fetch &>/dev/null
            watcher_updated=false
            if git diff --name-only HEAD...origin/main | grep -q "maintain_bot.sh"; then
                watcher_updated=true
            fi

            echo "Pulling latest changes from git..."
            git pull
            
            if [ "$watcher_updated" = true ]; then
                echo -e "\033[0;35mWatcher script has been updated! Rebooting the entire watcher system...\033[0m"
                kill "$WEB_PID"
                # Execute the bootstrapper, which will then start the new watcher.
                exec ./bootstrapper.sh
            fi

            # Log the time of the successful update
            date -u +"%Y-%m-%dT%H:%M:%SZ" > last_update.txt
            rm -f update_pending.flag # Clean up the flag
            break # Exit the inner loop to allow the outer loop to restart it
        fi
    done

    echo "Bot process stopped. It will be restarted shortly..."
    sleep 5 # Brief pause before restarting
done