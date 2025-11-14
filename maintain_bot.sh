#!/bin/bash

# This script acts as a watcher to maintain the Sulfur bot on Linux/Termux.
# It starts the bot and then checks for updates from the Git repository every minute.
# If updates are found, it automatically restarts the bot.

# To run it:
# 1. Make it executable: chmod +x ./maintain_bot.sh
# 2. Run it inside a tmux session for it to run in the background:
#    - tmux new -s sulfur
#    - ./maintain_bot.sh
#    - Detach from tmux with CTRL+B, then D.

echo "--- Sulfur Bot Maintenance Watcher ---"

# Check if we are running inside a tmux session
if [ -z "$TMUX" ]; then
    echo "Error: This script must be run inside a tmux session."
    echo "Start tmux with 'tmux new -s sulfur' and then run this script."
    exit 1
fi

while true; do
    echo "Starting the bot process..."
    # Create a new horizontal pane and run the bot start script in it.
    # The bot will run in the foreground of that new pane.
    tmux split-window -h "./start_bot.sh"
    
    # Give it a moment to start and get the PID of the python process.
    sleep 2
    BOT_PID=$(pgrep -f "python3 ./bot.py")

    echo "Bot is running in the background (PID: $BOT_PID). Checking for updates every 60 seconds."
    # This function will be called to clean up the bot and any child processes.
    cleanup() {
        echo "Stopping bot process (PID: $BOT_PID) and its children..."
        # Kill the entire process group to stop start_bot.sh and any child processes (like mysqld_safe).
        # The '-' before the PID is crucial for killing the group.
        if kill -0 $BOT_PID 2>/dev/null; then
            kill -- -$BOT_PID
            # Also close the tmux pane where the bot was running.
            tmux kill-pane -t bottom-right
        fi
        echo "Cleanup complete."
    }

    # This loop runs as long as the bot process exists
    while kill -0 $BOT_PID 2>/dev/null; do
        sleep 60

        # Fetch the latest changes from the remote repository
        git remote update > /dev/null 2>&1
        STATUS=$(git status -uno)

        if echo "$STATUS" | grep -q "Your branch is behind"; then
            echo "New version found in the repository! Restarting the bot to apply updates..."
            cleanup # Stop the bot and its children
            break # Exit the inner loop to allow the outer loop to restart it
        fi
    done

    # If the loop exits because the bot crashed, ensure cleanup is still performed.
    cleanup
    echo "Bot process stopped. It will be restarted in 5 seconds... (Press CTRL+C to stop the watcher)"
    sleep 5 # Brief pause before restarting
done