#!/bin/bash

# This is a simple bootstrapper script for Termux.
# Its only purpose is to restart the main maintain_bot.sh script after it has updated itself.

# Wait for the old watcher process to exit completely.
sleep 3

echo "Bootstrapper: Restarting the updated maintenance watcher..."

# Execute the new version of the maintenance script, replacing the current process.
exec ./maintain_bot.sh