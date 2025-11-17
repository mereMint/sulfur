#!/bin/bash
# ==============================================================================
# Sulfur Bot - Simple Starter Script
# ==============================================================================
# This script makes it easy to start the bot with one command.
# Usage: ./start.sh or bash start.sh
# ==============================================================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║             Sulfur Discord Bot - Starter                  ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# Detect environment
if [ -n "$TERMUX_VERSION" ]; then
    IS_TERMUX=true
    PYTHON_CMD="python"
    echo -e "${CYAN}Detected: Termux${NC}"
else
    IS_TERMUX=false
    PYTHON_CMD="python3"
    echo -e "${CYAN}Detected: Linux${NC}"
fi
echo ""

# Check for virtual environment
if [ -f "venv/bin/activate" ]; then
    echo -e "${YELLOW}Activating virtual environment...${NC}"
    source venv/bin/activate
    echo -e "${GREEN}✓ Virtual environment activated${NC}"
    echo ""
elif [ ! -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating one...${NC}"
    echo -e "${CYAN}This may take a few minutes...${NC}"
    echo ""
    
    if $PYTHON_CMD -m venv venv 2>/dev/null; then
        echo -e "${GREEN}✓ Virtual environment created${NC}"
        
        source venv/bin/activate
        echo -e "${GREEN}✓ Virtual environment activated${NC}"
        
        echo ""
        echo -e "${YELLOW}Installing dependencies...${NC}"
        $PYTHON_CMD -m pip install --upgrade pip
        pip install -r requirements.txt
        echo -e "${GREEN}✓ Dependencies installed${NC}"
        echo ""
    else
        echo -e "${YELLOW}⚠ Failed to create virtual environment${NC}"
        echo -e "${CYAN}Continuing without virtual environment...${NC}"
        echo ""
    fi
fi

# Make maintenance script executable
chmod +x maintain_bot.sh 2>/dev/null

echo -e "${CYAN}Starting maintenance script...${NC}"
echo ""

# Start the maintenance script
./maintain_bot.sh
