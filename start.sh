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

# Check if MySQL/MariaDB is running
echo -e "${YELLOW}Checking MySQL/MariaDB status...${NC}"
if pgrep -x mysqld > /dev/null 2>&1 || pgrep -x mariadbd > /dev/null 2>&1; then
    echo -e "${GREEN}✓ MySQL/MariaDB is running${NC}"
else
    echo -e "${RED}✗ MySQL/MariaDB is not running${NC}"
    echo ""
    echo -e "${YELLOW}Attempting to start MySQL/MariaDB...${NC}"
    
    if [ "$IS_TERMUX" = true ]; then
        if command -v mysqld_safe > /dev/null 2>&1; then
            echo -e "${CYAN}  Starting MariaDB in Termux...${NC}"
            mysqld_safe &
            sleep 3
            if pgrep -x mysqld > /dev/null 2>&1 || pgrep -x mariadbd > /dev/null 2>&1; then
                echo -e "${GREEN}✓ MariaDB started successfully${NC}"
            else
                echo -e "${YELLOW}⚠ MariaDB may not have started${NC}"
                echo -e "${GRAY}  Try: mysqld_safe &${NC}"
            fi
        else
            echo -e "${YELLOW}⚠ MariaDB not installed in Termux${NC}"
            echo -e "${GRAY}  Install with: pkg install mariadb${NC}"
            echo -e "${GRAY}  Then run: mysql_install_db${NC}"
            read -r -p "Press Enter to continue anyway or Ctrl+C to exit"
        fi
    else
        # Try to start MySQL service on Linux
        if command -v systemctl > /dev/null 2>&1; then
            echo -e "${CYAN}  Attempting to start MySQL service...${NC}"
            sudo systemctl start mysql 2>/dev/null || sudo systemctl start mariadb 2>/dev/null
            sleep 3
            if pgrep -x mysqld > /dev/null 2>&1 || pgrep -x mariadbd > /dev/null 2>&1; then
                echo -e "${GREEN}✓ MySQL service started${NC}"
            else
                echo -e "${YELLOW}⚠ Could not start MySQL service${NC}"
                echo -e "${GRAY}  Try manually: sudo systemctl start mysql${NC}"
                read -r -p "Press Enter to continue anyway or Ctrl+C to exit"
            fi
        else
            echo -e "${YELLOW}⚠ Could not auto-start MySQL${NC}"
            echo -e "${GRAY}  Please start MySQL manually and run this script again${NC}"
            read -r -p "Press Enter to continue anyway or Ctrl+C to exit"
        fi
    fi
fi
echo ""

# ============================================================================
# Auto-install Java (Latest Version)
# ============================================================================
echo -e "${YELLOW}Checking Java installation...${NC}"
if command -v java &> /dev/null; then
    JAVA_VERSION=$(java -version 2>&1 | head -n 1)
    echo -e "${GREEN}✓ Java found: $JAVA_VERSION${NC}"
else
    echo -e "${YELLOW}Java not found. Installing...${NC}"
    
    if [ "$IS_TERMUX" = true ]; then
        pkg install -y openjdk-17
    else
        if command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y default-jre default-jdk
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y java-latest-openjdk
        elif command -v pacman &> /dev/null; then
            sudo pacman -Sy --noconfirm jre-openjdk jdk-openjdk
        elif command -v yum &> /dev/null; then
            sudo yum install -y java-latest-openjdk
        else
            echo -e "${YELLOW}⚠ Unable to install Java automatically. Please install manually.${NC}"
        fi
    fi
    
    if command -v java &> /dev/null; then
        echo -e "${GREEN}✓ Java installed successfully${NC}"
    else
        echo -e "${YELLOW}⚠ Java installation may have failed${NC}"
    fi
fi
echo ""

# ============================================================================
# Auto-install FFmpeg
# ============================================================================
echo -e "${YELLOW}Checking FFmpeg installation...${NC}"
if command -v ffmpeg &> /dev/null; then
    FFMPEG_VERSION=$(ffmpeg -version 2>&1 | head -n 1)
    echo -e "${GREEN}✓ FFmpeg found: $FFMPEG_VERSION${NC}"
else
    echo -e "${YELLOW}FFmpeg not found. Installing...${NC}"
    
    if [ "$IS_TERMUX" = true ]; then
        pkg install -y ffmpeg
    else
        if command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y ffmpeg
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y ffmpeg
        elif command -v pacman &> /dev/null; then
            sudo pacman -Sy --noconfirm ffmpeg
        elif command -v yum &> /dev/null; then
            sudo yum install -y ffmpeg
        else
            echo -e "${YELLOW}⚠ Unable to install FFmpeg automatically. Please install manually.${NC}"
        fi
    fi
    
    if command -v ffmpeg &> /dev/null; then
        echo -e "${GREEN}✓ FFmpeg installed successfully${NC}"
    else
        echo -e "${YELLOW}⚠ FFmpeg installation may have failed${NC}"
    fi
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
    
    # Check for system dependencies on Termux before creating venv
    if [ "$IS_TERMUX" = true ]; then
        echo -e "${YELLOW}Checking system dependencies...${NC}"
        
        # System packages needed for PyNaCl (voice support)
        SYSTEM_DEPS=("libsodium" "clang")
        MISSING_PKGS=()
        
        # Check each required package
        for pkg in "${SYSTEM_DEPS[@]}"; do
            if ! pkg list-installed 2>/dev/null | grep -q "^${pkg}"; then
                MISSING_PKGS+=("$pkg")
            fi
        done
        
        if [ ${#MISSING_PKGS[@]} -gt 0 ]; then
            echo -e "${YELLOW}Installing required system packages: ${MISSING_PKGS[*]}${NC}"
            echo -e "${CYAN}This is needed for PyNaCl (voice support)${NC}"
            pkg install -y "${MISSING_PKGS[@]}"
            echo -e "${GREEN}✓ System packages installed${NC}"
            echo ""
        else
            echo -e "${GREEN}✓ All system packages are installed${NC}"
            echo ""
        fi
    fi
    
    if $PYTHON_CMD -m venv venv 2>/dev/null; then
        echo -e "${GREEN}✓ Virtual environment created${NC}"
        
        source venv/bin/activate
        echo -e "${GREEN}✓ Virtual environment activated${NC}"
        
        echo ""
        echo -e "${YELLOW}Installing dependencies...${NC}"
        $PYTHON_CMD -m pip install --upgrade pip
        # Set SODIUM_INSTALL=system to use system libsodium for PyNaCl
        export SODIUM_INSTALL=system
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
