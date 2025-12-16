#!/bin/bash
# ==============================================================================
# Sulfur Bot - Termux (Android) Installation Script
# ==============================================================================
# This script installs all dependencies for Sulfur Bot on Termux/Android
# including optional Minecraft server support.
# Note: WireGuard VPN on Termux requires root access for full functionality.
# ==============================================================================

set -e

# Detect if stdin is a terminal (interactive mode)
if [ -t 0 ]; then
    INTERACTIVE=true
else
    INTERACTIVE=false
    echo "Note: Running in non-interactive mode"
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║              SULFUR BOT - TERMUX INSTALLER                       ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if running in Termux
if [ ! -d "/data/data/com.termux" ]; then
    echo -e "${RED}❌ This script is designed for Termux on Android.${NC}"
    echo -e "${YELLOW}For Linux, use: ./scripts/install_linux.sh${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Detected: Termux on Android${NC}"

# Check for storage permission
check_storage() {
    if [ ! -d "$HOME/storage" ]; then
        echo -e "${YELLOW}⚠️  Storage access not configured${NC}"
        echo -e "${CYAN}Running termux-setup-storage...${NC}"
        termux-setup-storage
        echo -e "${GREEN}Please grant storage permission when prompted.${NC}"
        sleep 2
    fi
}

# Update packages
update_packages() {
    echo -e "\n${BLUE}📦 Updating package lists...${NC}"
    pkg update -y
    pkg upgrade -y
}

# Install Python
install_python() {
    echo -e "\n${BLUE}🐍 Checking Python installation...${NC}"
    
    if command -v python &> /dev/null; then
        PYTHON_VERSION=$(python --version 2>&1)
        echo -e "${GREEN}✅ $PYTHON_VERSION found${NC}"
    else
        echo -e "${YELLOW}Installing Python...${NC}"
        pkg install -y python
    fi
    
    # Install pip if not present
    if ! command -v pip &> /dev/null; then
        echo -e "${YELLOW}Installing pip...${NC}"
        pkg install -y python-pip
    fi
}

# Install Git
install_git() {
    echo -e "\n${BLUE}📚 Checking Git installation...${NC}"
    
    if command -v git &> /dev/null; then
        GIT_VERSION=$(git --version)
        echo -e "${GREEN}✅ $GIT_VERSION${NC}"
    else
        echo -e "${YELLOW}Installing Git...${NC}"
        pkg install -y git
    fi
}

# Install MariaDB
install_database() {
    echo -e "\n${BLUE}🗄️  Checking database installation...${NC}"
    
    if command -v mysql &> /dev/null || command -v mariadb &> /dev/null; then
        echo -e "${GREEN}✅ MariaDB found${NC}"
    else
        echo -e "${YELLOW}Installing MariaDB...${NC}"
        pkg install -y mariadb
        
        echo -e "${CYAN}Initializing MariaDB...${NC}"
        mysql_install_db
    fi
    
    # Check if MariaDB is running
    if ! pgrep -x "mariadbd" > /dev/null; then
        echo -e "${YELLOW}Starting MariaDB...${NC}"
        mysqld_safe &
        sleep 3
    fi
    
    echo -e "${GREEN}✅ MariaDB is running${NC}"
    echo -e "${CYAN}Note: Start MariaDB after reboot with: mysqld_safe &${NC}"
}

# Install Java (for Minecraft server)
install_java() {
    echo -e "\n${BLUE}☕ Checking Java installation...${NC}"
    
    if command -v java &> /dev/null; then
        JAVA_VERSION=$(java -version 2>&1 | head -n 1)
        echo -e "${GREEN}✅ Java found: $JAVA_VERSION${NC}"
    else
        if [ "$INTERACTIVE" = true ]; then
            read -p "Install OpenJDK 21 for Minecraft server? [Y/n]: " install_java_choice
        else
            install_java_choice="n"
            echo -e "${YELLOW}⏭️  Skipping Java installation (non-interactive mode)${NC}"
        fi
        if [[ "$install_java_choice" != "n" && "$install_java_choice" != "N" ]]; then
            echo -e "${YELLOW}Installing OpenJDK 21...${NC}"
            pkg install -y openjdk-21
        fi
    fi
}

# Install WireGuard (limited functionality without root)
install_wireguard() {
    echo -e "\n${BLUE}🔐 WireGuard on Termux...${NC}"
    
    if command -v wg &> /dev/null; then
        echo -e "${GREEN}✅ WireGuard tools found${NC}"
    else
        if [ "$INTERACTIVE" = true ]; then
            read -p "Install WireGuard tools? (Note: Full VPN requires root) [y/N]: " install_wg_choice
        else
            install_wg_choice="n"
            echo -e "${YELLOW}⏭️  Skipping WireGuard installation (non-interactive mode)${NC}"
        fi
        if [[ "$install_wg_choice" == "y" || "$install_wg_choice" == "Y" ]]; then
            echo -e "${YELLOW}Installing WireGuard tools...${NC}"
            pkg install -y wireguard-tools
            
            echo -e "${YELLOW}⚠️  Note: Full WireGuard VPN functionality requires root access.${NC}"
            echo -e "${YELLOW}   For rooted devices, you can use the kernel module.${NC}"
            echo -e "${YELLOW}   For non-rooted, consider using the WireGuard Android app instead.${NC}"
        fi
    fi
}

# Install additional dependencies
install_dependencies() {
    echo -e "\n${BLUE}📦 Installing additional dependencies...${NC}"
    
    pkg install -y \
        ffmpeg \
        libffi \
        opus \
        screen \
        curl \
        wget \
        openssl
    
    echo -e "${GREEN}✅ Dependencies installed${NC}"
}

# Setup Python virtual environment
setup_venv() {
    echo -e "\n${BLUE}🐍 Setting up Python virtual environment...${NC}"
    
    if [ ! -d "venv" ]; then
        python -m venv venv
        echo -e "${GREEN}✅ Virtual environment created${NC}"
    else
        echo -e "${GREEN}✅ Virtual environment already exists${NC}"
    fi
    
    # Activate and install dependencies
    source venv/bin/activate
    
    echo -e "${YELLOW}Installing Python dependencies...${NC}"
    pip install --upgrade pip
    
    # Special handling for Termux - some packages need special flags
    pip install wheel setuptools
    
    # Install requirements (skip packages that fail on Termux)
    pip install -r requirements.txt || {
        echo -e "${YELLOW}Some packages may have failed. Installing core packages...${NC}"
        pip install "discord.py[voice]>=2.4.0,<2.7.0" mysql-connector-python aiohttp python-dotenv Flask Flask-SocketIO waitress psutil yt-dlp
    }
    
    echo -e "${GREEN}✅ Python dependencies installed${NC}"
}

# Create startup script
create_startup_script() {
    echo -e "\n${BLUE}📝 Creating startup script...${NC}"
    
    cat > start_sulfur.sh << 'EOF'
#!/bin/bash
# Sulfur Bot Startup Script for Termux

# Start MariaDB if not running
if ! pgrep -x "mariadbd" > /dev/null; then
    echo "Starting MariaDB..."
    mysqld_safe &
    sleep 3
fi

# Activate virtual environment
source venv/bin/activate

# Start the bot
python bot.py
EOF
    
    chmod +x start_sulfur.sh
    echo -e "${GREEN}✅ Created start_sulfur.sh${NC}"
}

# Create boot script for Termux:Boot
create_boot_script() {
    if [ "$INTERACTIVE" = true ]; then
        read -p "Create auto-start script for Termux:Boot? [y/N]: " create_boot
    else
        create_boot="n"
        echo -e "${YELLOW}⏭️  Skipping boot script creation (non-interactive mode)${NC}"
    fi
    
    if [[ "$create_boot" == "y" || "$create_boot" == "Y" ]]; then
        BOOT_DIR="$HOME/.termux/boot"
        mkdir -p "$BOOT_DIR"
        
        CURRENT_DIR=$(pwd)
        
        cat > "$BOOT_DIR/start-sulfur-bot.sh" << EOF
#!/data/data/com.termux/files/usr/bin/bash
# Wait for network
sleep 10

# Start MariaDB
mysqld_safe &
sleep 5

# Start Sulfur Bot
cd "$CURRENT_DIR"
source venv/bin/activate
python bot.py &

# Start web dashboard
python web_dashboard.py &
EOF
        
        chmod +x "$BOOT_DIR/start-sulfur-bot.sh"
        
        echo -e "${GREEN}✅ Created Termux:Boot startup script${NC}"
        echo -e "${CYAN}Install Termux:Boot from F-Droid for auto-start functionality.${NC}"
    fi
}

# Run the master setup wizard
run_setup_wizard() {
    echo -e "\n${BLUE}🧙 Running setup wizard...${NC}"
    
    source venv/bin/activate
    python master_setup.py
}

# Termux-specific optimizations
termux_optimizations() {
    echo -e "\n${BLUE}⚡ Applying Termux optimizations...${NC}"
    
    # Disable battery optimization prompt
    echo -e "${CYAN}For best performance, disable battery optimization for Termux:${NC}"
    echo "  Settings > Apps > Termux > Battery > Unrestricted"
    
    # Acquire wake lock capability
    echo -e "${CYAN}To keep Termux running in background:${NC}"
    echo "  - Pull down notification shade"
    echo "  - Tap 'Acquire wakelock' in Termux notification"
    
    # Set up proper terminal
    if [ ! -f "$HOME/.termux/termux.properties" ]; then
        mkdir -p "$HOME/.termux"
        cat > "$HOME/.termux/termux.properties" << 'EOF'
# Termux properties for Sulfur Bot
allow-external-apps = true
EOF
    fi
}

# Main installation flow
main() {
    check_storage
    update_packages
    install_python
    install_git
    install_database
    install_java
    install_wireguard
    install_dependencies
    setup_venv
    create_startup_script
    termux_optimizations
    
    echo -e "\n${GREEN}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ Installation complete!${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
    
    if [ "$INTERACTIVE" = true ]; then
        read -p "Run the setup wizard now? [Y/n]: " run_wizard
    else
        run_wizard="n"
        echo -e "${YELLOW}⏭️  Skipping setup wizard (non-interactive mode)${NC}"
    fi
    if [[ "$run_wizard" != "n" && "$run_wizard" != "N" ]]; then
        run_setup_wizard
    fi
    
    create_boot_script
    
    echo -e "\n${CYAN}Quick Start:${NC}"
    echo "  1. Start the bot: ./start_sulfur.sh"
    echo "  2. Or manually:"
    echo "     - Start MariaDB: mysqld_safe &"
    echo "     - Activate venv: source venv/bin/activate"
    echo "     - Run bot: python bot.py"
    echo ""
    echo -e "${CYAN}Web Dashboard:${NC} http://localhost:5000"
    echo ""
    echo -e "${YELLOW}⚠️  Remember to:${NC}"
    echo "  - Disable battery optimization for Termux"
    echo "  - Acquire wakelock to keep Termux running"
}

# Run main
main
