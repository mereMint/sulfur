#!/bin/bash
# ==============================================================================
# Sulfur Bot - Simple Starter Script
# ==============================================================================
# This script makes it easy to start the bot with one command.
# Usage: ./start.sh
# ==============================================================================

echo "╔════════════════════════════════════════════════════════════╗"
echo "║             Sulfur Discord Bot - Startup                  ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Make maintenance script executable
chmod +x maintain_bot.sh

# Start the maintenance script
./maintain_bot.sh
