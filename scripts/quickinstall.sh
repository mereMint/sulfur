#!/bin/bash
# ==============================================================================
# Sulfur Bot - One-Command Quick Installer
# ==============================================================================
# Run this script with:
#   curl -sSL https://raw.githubusercontent.com/mereMint/sulfur/main/scripts/quickinstall.sh | bash
# Or:
#   wget -qO- https://raw.githubusercontent.com/mereMint/sulfur/main/scripts/quickinstall.sh | bash
# ==============================================================================

set -e

# Detect if stdin is a pipe (script is being piped from curl/wget)
if [ -t 0 ]; then
    INTERACTIVE=true
else
    INTERACTIVE=false
    echo "Note: Running in non-interactive mode (piped from curl/wget)"
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Banner
echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                                                                  ║"
echo "║      ███████╗██╗   ██╗██╗     ███████╗██╗   ██╗██████╗          ║"
echo "║      ██╔════╝██║   ██║██║     ██╔════╝██║   ██║██╔══██╗         ║"
echo "║      ███████╗██║   ██║██║     █████╗  ██║   ██║██████╔╝         ║"
echo "║      ╚════██║██║   ██║██║     ██╔══╝  ██║   ██║██╔══██╗         ║"
echo "║      ███████║╚██████╔╝███████╗██║     ╚██████╔╝██║  ██║         ║"
echo "║      ╚══════╝ ╚═════╝ ╚══════╝╚═╝      ╚═════╝ ╚═╝  ╚═╝         ║"
echo "║                                                                  ║"
echo "║              🤖 Discord Bot Quick Installer                      ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Detect platform
detect_platform() {
    # Check for Termux
    if [ -d "/data/data/com.termux" ]; then
        echo "termux"
        return
    fi
    
    # Check for WSL
    if grep -qi microsoft /proc/version 2>/dev/null; then
        echo "wsl"
        return
    fi
    
    # Check for Raspberry Pi
    if grep -qi "raspberry pi" /proc/cpuinfo 2>/dev/null; then
        echo "raspberrypi"
        return
    fi
    
    # Standard Linux
    if [ "$(uname)" = "Linux" ]; then
        echo "linux"
        return
    fi
    
    # macOS
    if [ "$(uname)" = "Darwin" ]; then
        echo "macos"
        return
    fi
    
    echo "unknown"
}

PLATFORM=$(detect_platform)
echo -e "${GREEN}✅ Detected platform: ${BOLD}${PLATFORM}${NC}"
echo ""

# Installation directory
INSTALL_DIR="${HOME}/sulfur"

# Check for required commands
check_requirements() {
    local missing=()
    
    if ! command -v git &> /dev/null; then
        missing+=("git")
    fi
    
    if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
        missing+=("python3")
    fi
    
    if [ ${#missing[@]} -gt 0 ]; then
        echo -e "${YELLOW}⚠️  Missing required packages: ${missing[*]}${NC}"
        echo ""
        install_packages "${missing[@]}"
    fi
}

# Install packages based on platform
install_packages() {
    local packages=("$@")
    
    case $PLATFORM in
        termux)
            pkg update -y
            pkg install -y "${packages[@]}"
            ;;
        linux|raspberrypi|wsl)
            if command -v apt-get &> /dev/null; then
                sudo apt-get update
                sudo apt-get install -y "${packages[@]}"
            elif command -v dnf &> /dev/null; then
                sudo dnf install -y "${packages[@]}"
            elif command -v pacman &> /dev/null; then
                sudo pacman -S --noconfirm "${packages[@]}"
            else
                echo -e "${RED}❌ Could not detect package manager${NC}"
                exit 1
            fi
            ;;
        macos)
            if command -v brew &> /dev/null; then
                brew install "${packages[@]}"
            else
                echo -e "${YELLOW}Installing Homebrew...${NC}"
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
                brew install "${packages[@]}"
            fi
            ;;
        *)
            echo -e "${RED}❌ Unsupported platform for automatic installation${NC}"
            echo "Please install manually: ${packages[*]}"
            exit 1
            ;;
    esac
}

# Clone or update repository
setup_repository() {
    if [ -d "$INSTALL_DIR" ]; then
        echo -e "${BLUE}📁 Sulfur directory already exists${NC}"
        
        if [ "$INTERACTIVE" = true ]; then
            echo -n "   Update to latest version? [Y/n]: "
            read -r update_choice
        else
            update_choice="y"
            echo "   Updating to latest version (non-interactive mode)"
        fi
        
        if [ "$update_choice" != "n" ] && [ "$update_choice" != "N" ]; then
            echo -e "${BLUE}📥 Updating repository...${NC}"
            cd "$INSTALL_DIR"
            
            # Reset any local changes to always use remote files (public repo)
            echo "   Discarding local changes (using remote files)..."
            git fetch origin
            git reset --hard origin/main || git reset --hard origin/master
            
            echo -e "${GREEN}✅ Updated to latest version${NC}"
        fi
    else
        echo -e "${BLUE}📥 Cloning Sulfur Bot repository...${NC}"
        git clone https://github.com/mereMint/sulfur.git "$INSTALL_DIR"
    fi
    
    cd "$INSTALL_DIR"
}

# Setup Python virtual environment
setup_python() {
    echo -e "${BLUE}🐍 Setting up Python environment...${NC}"
    
    # Determine python command
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    else
        PYTHON_CMD="python"
    fi
    
    # Create virtual environment
    if [ ! -d "venv" ]; then
        $PYTHON_CMD -m venv venv
        echo -e "${GREEN}✅ Virtual environment created${NC}"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install dependencies
    echo -e "${BLUE}📦 Installing dependencies...${NC}"
    pip install -r requirements.txt
    
    echo -e "${GREEN}✅ Python dependencies installed${NC}"
}

# Run platform-specific installer
run_installer() {
    case $PLATFORM in
        termux)
            if [ -f "scripts/install_termux.sh" ]; then
                chmod +x scripts/install_termux.sh
                ./scripts/install_termux.sh
            fi
            ;;
        linux|raspberrypi|wsl)
            if [ -f "scripts/install_linux.sh" ]; then
                chmod +x scripts/install_linux.sh
                ./scripts/install_linux.sh
            fi
            ;;
        *)
            # Just use the basic setup
            setup_python
            ;;
    esac
}

# Interactive setup
interactive_setup() {
    echo ""
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}                    📝 Configuration${NC}"
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    if [ "$INTERACTIVE" = true ]; then
        echo -n "Run the interactive setup wizard? [Y/n]: "
        read -r run_wizard
    else
        run_wizard="n"
        echo "Skipping interactive setup wizard (non-interactive mode)"
    fi
    
    if [ "$run_wizard" != "n" ] && [ "$run_wizard" != "N" ]; then
        source venv/bin/activate
        python master_setup.py
    else
        echo ""
        echo -e "${CYAN}You can run the setup wizard later with:${NC}"
        echo "  cd $INSTALL_DIR"
        echo "  source venv/bin/activate"
        echo "  python master_setup.py"
    fi
}

# Print final instructions
print_final_instructions() {
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}${BOLD}            ✅ Installation Complete!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${CYAN}📍 Installation directory: ${BOLD}$INSTALL_DIR${NC}"
    echo ""
    echo -e "${CYAN}🚀 To start the bot:${NC}"
    echo "   cd $INSTALL_DIR"
    echo "   source venv/bin/activate"
    echo "   python bot.py"
    echo ""
    echo -e "${CYAN}🌐 Web Dashboard:${NC} http://localhost:5000"
    echo ""
    echo -e "${CYAN}📚 Documentation:${NC}"
    echo "   - README.md"
    echo "   - docs/WIKI.md"
    echo "   - docs/VPN_GUIDE.md"
    echo ""
    echo -e "${YELLOW}💡 Quick Tips:${NC}"
    echo "   - Create a .env file with your Discord token"
    echo "   - Start MySQL/MariaDB before running the bot"
    echo "   - Use /help in Discord to see all commands"
    echo ""
}

# Main installation flow
main() {
    echo -e "${BLUE}🔍 Checking requirements...${NC}"
    check_requirements
    
    echo ""
    echo -e "${BLUE}📁 Setting up repository...${NC}"
    setup_repository
    
    echo ""
    
    # Check if this is a fresh install or update
    if [ -f "venv/bin/activate" ]; then
        echo -e "${GREEN}✅ Existing installation found${NC}"
        
        if [ "$INTERACTIVE" = true ]; then
            echo -n "   Run full installer again? [y/N]: "
            read -r full_install
        else
            full_install="n"
            echo "   Updating dependencies only (non-interactive mode)"
        fi
        
        if [ "$full_install" = "y" ] || [ "$full_install" = "Y" ]; then
            run_installer
        else
            # Just update dependencies
            source venv/bin/activate
            pip install -r requirements.txt --upgrade
        fi
    else
        run_installer
    fi
    
    interactive_setup
    print_final_instructions
}

# Run main
main
