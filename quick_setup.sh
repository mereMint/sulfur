#!/bin/bash
# ============================================================
# Sulfur Bot - Quick Setup Script for Linux/Termux
# ============================================================
# This script automates the entire setup process for first-time users
# Usage: bash quick_setup.sh [--install-dir /path/to/install]
#
# Options:
#   --install-dir DIR   Custom installation directory
#   -h, --help          Show this help message
# ============================================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m'

# Parse command line arguments
INSTALL_DIR=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --install-dir|-d)
            INSTALL_DIR="$2"
            shift 2
            ;;
        -h|--help)
            echo "Sulfur Bot Quick Setup Script"
            echo ""
            echo "Usage: bash quick_setup.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --install-dir DIR   Custom installation directory"
            echo "  -h, --help          Show this help message"
            echo ""
            exit 0
            ;;
        *)
            # Skip unknown options silently for backward compatibility
            shift
            ;;
    esac
done

echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║         Sulfur Bot - Quick Setup Wizard                   ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

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

# Determine installation directory
if [ -n "$INSTALL_DIR" ]; then
    SCRIPT_DIR="$INSTALL_DIR"
    if [ ! -d "$SCRIPT_DIR" ]; then
        echo -e "${YELLOW}Creating installation directory: $SCRIPT_DIR${NC}"
        mkdir -p "$SCRIPT_DIR"
    fi
else
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
cd "$SCRIPT_DIR" || exit 1

echo -e "${GRAY}Installation directory: $SCRIPT_DIR${NC}"
echo ""

# Step 1: Check Prerequisites
echo -e "${YELLOW}Step 1: Checking Prerequisites${NC}"
echo -e "${GRAY}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check Python
echo -e "${CYAN}Checking Python...${NC}"
if command -v $PYTHON_CMD &> /dev/null; then
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
    echo -e "${GREEN}✓ Python found: $PYTHON_VERSION${NC}"
else
    echo -e "${RED}✗ Python not found!${NC}"
    if [ "$IS_TERMUX" = true ]; then
        echo -e "${YELLOW}  Install with: pkg install python${NC}"
    else
        echo -e "${YELLOW}  Install with: sudo apt install python3${NC}"
    fi
    exit 1
fi

# Check Git
echo -e "${CYAN}Checking Git...${NC}"
if command -v git &> /dev/null; then
    GIT_VERSION=$(git --version 2>&1)
    echo -e "${GREEN}✓ Git found: $GIT_VERSION${NC}"
else
    echo -e "${RED}✗ Git not found!${NC}"
    if [ "$IS_TERMUX" = true ]; then
        echo -e "${YELLOW}  Install with: pkg install git${NC}"
    else
        echo -e "${YELLOW}  Install with: sudo apt install git${NC}"
    fi
    exit 1
fi

# Check MySQL/MariaDB
echo -e "${CYAN}Checking MySQL/MariaDB...${NC}"
if pgrep mysqld > /dev/null 2>&1; then
    echo -e "${GREEN}✓ MySQL/MariaDB is running${NC}"
else
    echo -e "${RED}✗ MySQL/MariaDB is not running!${NC}"
    echo ""
    
    if [ "$IS_TERMUX" = true ]; then
        echo -e "${YELLOW}Installing and starting MariaDB...${NC}"
        pkg install mariadb -y
        
        if [ ! -d "$PREFIX/var/lib/mysql" ]; then
            echo -e "${YELLOW}Initializing MySQL...${NC}"
            mysql_install_db
        fi
        
        echo -e "${YELLOW}Starting MySQL with mysqld_safe...${NC}"
        mysqld_safe --datadir=$PREFIX/var/lib/mysql &
        sleep 3
    else
        echo -e "${YELLOW}  Please install and start MariaDB:${NC}"
        echo -e "    sudo apt install mariadb-server mariadb-client"
        echo -e "    sudo systemctl start mariadb"
        exit 1
    fi
    
    # Check again
    if pgrep mysqld > /dev/null 2>&1; then
        echo -e "${GREEN}✓ MySQL/MariaDB started${NC}"
    else
        echo -e "${RED}✗ Failed to start MySQL/MariaDB${NC}"
        exit 1
    fi
fi

echo ""

# Step 2: Check .env file
echo -e "${YELLOW}Step 2: Checking Configuration${NC}"
echo -e "${GRAY}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ ! -f ".env" ]; then
    echo -e "${RED}✗ .env file not found!${NC}"
    echo ""
    echo -e "${YELLOW}Creating .env file from template...${NC}"
    
    cat > .env << 'EOF'
# Discord Bot Configuration
DISCORD_BOT_TOKEN=""

# AI API Keys (at least one required)
GEMINI_API_KEY=""
OPENAI_API_KEY=""

# Football Data API (for Sport Betting - Optional)
# Get from: https://www.football-data.org/client/register
# Enables: Champions League, Premier League, La Liga, Serie A, FIFA World Cup
FOOTBALL_DATA_API_KEY=""

# Database Configuration
DB_HOST="localhost"
DB_USER="sulfur_bot_user"
DB_PASS=""
DB_NAME="sulfur_bot"

# Bot Settings (Optional)
BOT_PREFIX="!"
EOF
    
    echo -e "${GREEN}✓ Created .env template${NC}"
    echo ""
    echo -e "${YELLOW}⚠ IMPORTANT: You need to fill in the .env file with your credentials!${NC}"
    echo ""
    echo -e "${CYAN}Required:${NC}"
    echo -e "  1. DISCORD_BOT_TOKEN - Get from: https://discord.com/developers/applications"
    echo -e "  2. GEMINI_API_KEY - Get from: https://aistudio.google.com/"
    echo -e "     OR OPENAI_API_KEY - Get from: https://platform.openai.com/"
    echo ""
    echo -e "${CYAN}Optional (for Sport Betting):${NC}"
    echo -e "  3. FOOTBALL_DATA_API_KEY - Get from: https://www.football-data.org/"
    echo -e "     Enables: Champions League, Premier League, La Liga, Serie A, FIFA World Cup"
    echo ""
    
    # Try to open in editor
    if command -v nano &> /dev/null; then
        echo -e "${YELLOW}Opening .env in nano...${NC}"
        echo -e "${GRAY}(Press Ctrl+X, then Y, then Enter to save)${NC}"
        sleep 2
        nano .env
    elif command -v vi &> /dev/null; then
        echo -e "${YELLOW}Opening .env in vi...${NC}"
        echo -e "${GRAY}(Press i to edit, Esc then :wq to save)${NC}"
        sleep 2
        vi .env
    else
        echo -e "${YELLOW}Please edit .env file manually:${NC}"
        echo -e "  nano .env"
        echo ""
        read -p "Press Enter when done..."
    fi
fi

# Verify .env has required fields
echo -e "${CYAN}Verifying .env configuration...${NC}"
HAS_DISCORD_TOKEN=$(grep -E -c 'DISCORD_BOT_TOKEN=".+"' .env 2>/dev/null || echo 0)
HAS_GEMINI_KEY=$(grep -E -c 'GEMINI_API_KEY=".+"' .env 2>/dev/null || echo 0)
HAS_OPENAI_KEY=$(grep -E -c 'OPENAI_API_KEY=".+"' .env 2>/dev/null || echo 0)

if [ "$HAS_DISCORD_TOKEN" -eq 0 ]; then
    echo -e "${RED}✗ DISCORD_BOT_TOKEN not set in .env${NC}"
    echo -e "${YELLOW}  Get your token from: https://discord.com/developers/applications${NC}"
    exit 1
fi

if [ "$HAS_GEMINI_KEY" -eq 0 ] && [ "$HAS_OPENAI_KEY" -eq 0 ]; then
    echo -e "${RED}✗ No AI API key set in .env${NC}"
    echo -e "${YELLOW}  You need either GEMINI_API_KEY or OPENAI_API_KEY${NC}"
    echo -e "${YELLOW}  Gemini: https://aistudio.google.com/${NC}"
    echo -e "${YELLOW}  OpenAI: https://platform.openai.com/${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Configuration looks good${NC}"
echo ""

# Step 3: Set up virtual environment
echo -e "${YELLOW}Step 3: Setting Up Python Virtual Environment${NC}"
echo -e "${GRAY}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check if venv module is available
if ! $PYTHON_CMD -m venv --help >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠ Python venv module not available. Installing...${NC}"
    
    # Detect Linux distribution
    if [ -f /etc/debian_version ]; then
        # Debian/Ubuntu
        PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
        echo -e "${CYAN}Attempting to install python${PYTHON_VERSION}-venv...${NC}"
        if command -v sudo &> /dev/null; then
            sudo apt-get update -qq && sudo apt-get install -y python${PYTHON_VERSION}-venv python3-venv 2>/dev/null || {
                echo -e "${RED}✗ Failed to install venv package${NC}"
                echo -e "${YELLOW}Please install manually: sudo apt install python3-venv${NC}"
                exit 1
            }
        else
            echo -e "${RED}✗ sudo not available. Please install venv manually: apt install python3-venv${NC}"
            exit 1
        fi
    elif [ -f /etc/redhat-release ]; then
        # RHEL/CentOS/Fedora
        echo -e "${CYAN}Attempting to install python3-venv...${NC}"
        if command -v sudo &> /dev/null; then
            sudo dnf install -y python3-venv 2>/dev/null || sudo yum install -y python3-venv 2>/dev/null || {
                echo -e "${RED}✗ Failed to install venv package${NC}"
                echo -e "${YELLOW}Please install manually: sudo dnf install python3-venv${NC}"
                exit 1
            }
        else
            echo -e "${RED}✗ sudo not available. Please install venv manually: dnf install python3-venv${NC}"
            exit 1
        fi
    elif [ -f /etc/arch-release ]; then
        # Arch Linux
        echo -e "${CYAN}Attempting to install python...${NC}"
        if command -v sudo &> /dev/null; then
            sudo pacman -S --noconfirm python 2>/dev/null || {
                echo -e "${RED}✗ Failed to install venv package${NC}"
                echo -e "${YELLOW}Please install manually: sudo pacman -S python${NC}"
                exit 1
            }
        else
            echo -e "${RED}✗ sudo not available. Please install venv manually: pacman -S python${NC}"
            exit 1
        fi
    else
        echo -e "${RED}✗ Could not detect your Linux distribution${NC}"
        echo -e "${YELLOW}Please install python3-venv for your system and try again${NC}"
        exit 1
    fi
fi

if [ ! -d "venv" ]; then
    echo -e "${CYAN}Creating virtual environment...${NC}"
    if $PYTHON_CMD -m venv venv; then
        echo -e "${GREEN}✓ Virtual environment created${NC}"
    else
        echo -e "${RED}✗ Failed to create virtual environment${NC}"
        echo -e "${YELLOW}Please try installing python3-venv manually and running this script again${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}"
fi

echo -e "${CYAN}Activating virtual environment...${NC}"
source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"
echo ""

# Step 4: Install dependencies
echo -e "${YELLOW}Step 4: Installing Python Dependencies${NC}"
echo -e "${GRAY}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${CYAN}Upgrading pip...${NC}"
$PYTHON_CMD -m pip install --upgrade pip --quiet

echo -e "${CYAN}Installing dependencies from requirements.txt...${NC}"
echo -e "${GRAY}(This may take a few minutes...)${NC}"
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ All dependencies installed${NC}"
else
    echo -e "${RED}✗ Failed to install some dependencies${NC}"
    echo -e "${YELLOW}  Please check the error messages above${NC}"
    exit 1
fi

echo ""

# Step 5: Set up database
echo -e "${YELLOW}Step 5: Setting Up Database${NC}"
echo -e "${GRAY}━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${CYAN}Running database setup script...${NC}"
chmod +x setup_mysql.sh
bash setup_mysql.sh

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Database setup failed${NC}"
    exit 1
fi

echo ""

# Step 6: Run tests
echo -e "${YELLOW}Step 6: Testing Setup${NC}"
echo -e "${GRAY}━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${CYAN}Running setup verification...${NC}"
if [ -f "verify_setup.py" ]; then
    $PYTHON_CMD verify_setup.py
else
    echo -e "${YELLOW}⚠ verify_setup.py not found, skipping verification${NC}"
fi

echo ""

# Step 7: Final instructions
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    Setup Complete! 🎉                      ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${CYAN}Next Steps:${NC}"
echo -e "${NC}1. Customize bot personality:${NC}"
echo -e "${GRAY}   - Edit config/system_prompt.txt${NC}"
echo ""
echo -e "${NC}2. Configure bot settings:${NC}"
echo -e "${GRAY}   - Edit config/config.json${NC}"
echo ""
echo -e "${NC}3. Invite bot to your Discord server:${NC}"
echo -e "${GRAY}   - Go to: https://discord.com/developers/applications${NC}"
echo -e "${GRAY}   - Select your application → OAuth2 → URL Generator${NC}"
echo -e "${GRAY}   - Select scopes: bot, applications.commands${NC}"
echo -e "${GRAY}   - Select permissions: Administrator (or specific permissions)${NC}"
echo -e "${GRAY}   - Copy and open the generated URL${NC}"
echo ""
echo -e "${NC}4. Start the bot:${NC}"
echo -e "${GRAY}   - Run: bash start.sh${NC}"
echo -e "${GRAY}   - Or: ./start.sh${NC}"
echo ""
echo -e "${CYAN}Web Dashboard will be available at: http://localhost:5000${NC}"
echo ""

read -p "Would you like to start the bot now? (y/n) " start
if [ "$start" = "y" ] || [ "$start" = "Y" ]; then
    echo ""
    echo -e "${CYAN}Starting bot...${NC}"
    chmod +x start.sh
    bash start.sh
else
    echo ""
    echo -e "${YELLOW}You can start the bot later by running: bash start.sh${NC}"
    echo ""
fi
