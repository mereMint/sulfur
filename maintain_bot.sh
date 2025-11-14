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

# --- NEW: Add a 'logs' command to view the latest log file ---
if [ "$1" == "logs" ]; then
    LOG_DIR="logs"
    if [ ! -d "$LOG_DIR" ]; then
        echo "Log directory '$LOG_DIR' not found."
        exit 1
    fi
    LATEST_LOG=$(ls -t "$LOG_DIR"/startup_log_*.log 2>/dev/null | head -n 1)
    if [ -z "$LATEST_LOG" ]; then
        echo "No log files found in '$LOG_DIR'."
        exit 1
    fi
    echo "Showing latest log file: $LATEST_LOG"
    less -R "$LATEST_LOG"
    exit 0
fi

# --- NEW: Create the bot pane once and get its ID ---
# --- FIX: Ensure start_bot.sh is executable before running ---
chmod +x ./start_bot.sh

echo "Creating a dedicated pane for the bot's output..."
# The -P flag prints the new pane's info, and -F gets just the ID.
# The pane will initially run the start script.
BOT_PANE_ID=$(tmux split-window -h -P -F "#{pane_id}" "./start_bot.sh")


while true; do
    # Give it a moment to start and get the PID of the python process.
    sleep 2
    BOT_PID=$(pgrep -f "python3 ./bot.py")

    if [ -z "$BOT_PID" ]; then
        echo "Warning: Could not find bot PID. It might have crashed on startup. Will try restarting..."
    else
        echo "Bot is running in pane $BOT_PANE_ID (PID: $BOT_PID). Checking for updates every 30 seconds."
    fi

    # This function will be called to clean up the bot and any child processes.
    cleanup() {
        echo "Restarting bot process in pane $BOT_PANE_ID..."
        # The 'respawn-pane' command kills the old process and starts a new one in the same pane.
        # --- FIX: Ensure start_bot.sh is executable before respawning ---
        chmod +x ./start_bot.sh
        # The -k flag ensures the old command is killed before respawning.
        tmux respawn-pane -k -t "$BOT_PANE_ID" "./start_bot.sh"
        # Remove the flag file so the new instance starts with a clean status
        rm -f update_pending.flag
        echo "Cleanup complete."
    }

    # This loop runs as long as the bot process exists
    while kill -0 $BOT_PID 2>/dev/null; do
        sleep 30

        # Fetch the latest changes from the remote repository
        git remote update > /dev/null 2>&1
        STATUS=$(git status -uno)

        if echo "$STATUS" | grep -q "Your branch is behind"; then
            echo "New version found in the repository! Restarting the bot to apply updates..."
            # Create the flag file to signal the bot to go idle
            touch update_pending.flag
            cleanup # This now respawns the bot in the same pane
            break # Exit the inner loop to allow the outer loop to restart it
        fi
    done

    # If the loop exits because the bot crashed, ensure cleanup is still performed.
    cleanup
    echo "Bot process stopped or crashed. Restarting it in 5 seconds... (Press CTRL+C to stop the watcher)"
    sleep 5 # Brief pause before restarting
done