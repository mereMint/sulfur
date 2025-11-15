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
echo "Bot started in pane ${BOT_PANE_ID}. Watcher is active."

while true; do
    echo "Checking for updates..."

    # Fetch the latest changes from the remote repository
    git remote update > /dev/null 2>&1
    STATUS=$(git status -uno)

    if echo "$STATUS" | grep -q "Your branch is behind"; then
        echo "New version found! Restarting the bot to apply updates..."
        # The 'respawn-pane' command kills the old process and starts a new one.
        # The -k flag ensures the old command is killed before respawning.
        chmod +x ./start_bot.sh
        tmux respawn-pane -k -t "$BOT_PANE_ID" "./start_bot.sh"
        echo "Bot is restarting with the new version."
        # Wait a bit longer after a restart to avoid spamming git
        sleep 60
    elif ! tmux list-panes -F "#{pane_id}" | grep -q "^${BOT_PANE_ID}$"; then
        echo "Error: Bot pane ${BOT_PANE_ID} not found. It was likely closed manually."
        echo "Exiting watcher. Restart the script to create a new bot session."
        exit 1
    fi
    
    # Check every 60 seconds
    sleep 60
done