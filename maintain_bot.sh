#!/bin/bash
# This script acts as a watcher to maintain the Sulfur bot on Linux/Termux.
# It starts the bot and then checks for updates from the Git repository.
# If updates are found, it automatically pulls them and restarts the bot.

# To run it:
# 1. Make it executable: chmod +x maintain_bot.sh
# 2. Run the script: ./maintain_bot.sh

echo "--- Sulfur Bot Maintenance Watcher (Linux/Termux) ---"

# Ensure we are in the script's directory
cd "$(dirname "$0")"

while true; do
    echo "Starting the bot process..."
    # --- FIX: Ensure the startup script is executable before running it ---
    echo "Ensuring startup script is executable..."
    chmod +x ./start_bot.sh

    # Start the main bot script (which handles setup) in the background
    ./start_bot.sh &
    # Get the Process ID (PID) of the backgrounded bot process
    BOT_PID=$!

    echo "Bot is running in the background (PID: $BOT_PID). Checking for updates every 60 seconds."

    # Loop to check for updates as long as the bot process is running
    while kill -0 $BOT_PID 2>/dev/null; do
        sleep 60
        
        # --- NEW: Log the time of the update check ---
        date -u --iso-8601=seconds > last_check.txt

        # Fetch the latest changes from the remote repository
        git remote update > /dev/null 2>&1
        STATUS=$(git status -uno)

        if [[ "$STATUS" == *"Your branch is behind"* ]]; then
            echo "New version found in the repository! Restarting the bot to apply updates..."
            # Create the flag file to signal the bot to go idle
            touch update_pending.flag
            # Gracefully stop the bot
            kill $BOT_PID
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