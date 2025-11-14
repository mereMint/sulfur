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

while true; do
    echo "Starting the bot process..."
    # Start the main bot script in the background
    ./start_bot.sh &
    BOT_PID=$!

    echo "Bot is running in the background (PID: $BOT_PID). Checking for updates every 60 seconds."

    # This loop runs as long as the bot process exists
    while kill -0 $BOT_PID 2>/dev/null; do
        sleep 60

        # Fetch the latest changes from the remote repository
        git remote update > /dev/null 2>&1
        STATUS=$(git status -uno)

        if echo "$STATUS" | grep -q "Your branch is behind"; then
            echo "New version found in the repository! Restarting the bot to apply updates..."
            kill $BOT_PID # Stop the bot
            break # Exit the inner loop to allow the outer loop to restart it
        fi
    done

    echo "Bot process stopped. It will be restarted shortly..."
    sleep 5 # Brief pause before restarting
done