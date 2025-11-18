#!/data/data/com.termux/files/usr/bin/bash
# Quick start script for Sulfur bot

cd ~/sulfur

# Start MariaDB if not running
if ! pgrep -x mysqld > /dev/null && ! pgrep -x mariadbd > /dev/null; then
    echo "Starting MariaDB..."
    mysqld_safe &
    sleep 5
    echo "MariaDB started"
fi

# Activate virtual environment
source venv/bin/activate

# Run the bot with maintenance script
bash maintain_bot.sh
