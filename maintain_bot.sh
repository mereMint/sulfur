#!/bin/bash
# This script acts as a watcher to maintain the Sulfur bot on Linux/Termux.
# It starts the bot and then checks for updates from the Git repository.
# If updates are found, it automatically pulls them and restarts the bot.

# To run it:
# 1. Make it executable: chmod +x maintain_bot.sh
# 2. Run the script: ./maintain_bot.sh

echo "--- Sulfur Bot Maintenance Watcher (Linux/Termux) ---"

# --- NEW: Lock file to prevent multiple instances ---
LOCKFILE="/tmp/sulfur_maintainer.lock"

if [ -e "$LOCKFILE" ]; then
    # Lockfile exists, check if the process is still running
    PID=$(cat "$LOCKFILE")
    if kill -0 "$PID" > /dev/null 2>&1; then
        echo "Maintainer script is already running with PID $PID. Exiting."
        exit 1
    else
        # The process is not running, so the lock file is stale. Remove it.
        echo "Found stale lock file. Removing it."
        rm -f "$LOCKFILE"
    fi
fi

echo $$ > "$LOCKFILE"
trap 'rm -f "$LOCKFILE"' EXIT INT TERM

# --- FIX: Load environment variables from .env file ---
# This is crucial for the cleanup trap in start_bot.sh to have DB credentials
# when this maintenance script kills the child process for a restart.
if [ -f .env ]; then
    set -a # automatically export all variables
    source .env
    set +a # stop automatically exporting
fi

# Ensure we are in the script's directory
cd "$(dirname "$0")"

while true; do
    echo "Starting the bot process..."
    # --- FIX: Ensure the startup script is executable before running it ---
    echo "Ensuring startup script is executable..."
    chmod +x ./start_bot.sh

    # --- FIX: Use setsid to run the bot in a new process group ---
    # This allows us to reliably kill the entire process tree (start_bot.sh and python)
    # without affecting the maintainer script itself.
    setsid ./start_bot.sh &
    # Get the Process Group ID (PGID), which is the same as the PID of the setsid process leader.
    # We will use this to kill the entire group later.
    BOT_PID=$!

    echo "Bot is running in the background (PID: $BOT_PID). Checking for updates every 60 seconds."

    # Loop to check for updates as long as the bot process is running
    while kill -0 $BOT_PID 2>/dev/null; do
        sleep 60
        
        # --- NEW: Log the time of the update check ---
        date -u --iso-8601=seconds > last_check.txt

        # --- NEW: Check for local changes, commit, and push them ---
        # Stash any untracked files to not interfere with git status
        git stash push -u -q
        # --- FIX: Only commit changes to the database sync file ---
        if ! git diff --quiet --exit-code HEAD -- database_sync.sql; then
            echo "Local changes to database_sync.sql detected. Committing and pushing..."
            git add database_sync.sql
            git commit -m "Auto-commit: Update database sync or other tracked files"
            git push
        fi
        git stash pop -q # Unstash the untracked files

        # Fetch the latest changes from the remote repository
        git remote update > /dev/null 2>&1
        STATUS=$(git status -uno)

        if [[ "$STATUS" == *"Your branch is behind"* ]]; then
            echo "New version found in the repository! Restarting the bot to apply updates..."
            # Create the flag file to signal the bot to go idle
            touch update_pending.flag
            # --- FIX: Kill the entire process group to prevent orphaned python processes ---
            # The negative sign before $BOT_PID is crucial. It tells `kill` to target the
            # entire process group, not just the single parent process.
            kill -- -$BOT_PID
            wait $BOT_PID 2>/dev/null # Wait for the process to terminate
            echo "Pulling latest changes from git..."
            git pull
            # --- NEW: Log the time of the successful update ---
            date -u --iso-8601=seconds > last_update.txt
            rm -f update_pending.flag # Clean up the flag
            break # Exit the inner loop to allow the outer loop to restart it
        fi
    done

    echo "Bot process stopped. It will be restarted shortly..."
    sleep 5 # Brief pause before restarting
done