#!/bin/bash

# This is a simple bootstrapper script for Termux/Linux.
# Its only purpose is to restart the main maintain_bot.sh script after it has updated itself.

# Wait for the old watcher process to exit completely.
sleep 3

echo "Bootstrapper: Finalizing update with remote files..."

# For public repos: Reset to remote files to ensure clean state
git fetch origin 2>&1 | grep -v "^From" || true
git reset --hard origin/main 2>/dev/null || git reset --hard origin/master 2>/dev/null || true

echo "Bootstrapper: Restarting the updated maintenance watcher..."

# Execute the new version of the maintenance script, replacing the current process.
exec ./maintain_bot.sh