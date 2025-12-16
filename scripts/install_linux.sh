#!/bin/bash
# ==============================================================================
# Sulfur Bot - Linux/Raspberry Pi Installation Script
# ==============================================================================
# This script installs all dependencies for Sulfur Bot on Linux/Raspberry Pi
# including optional WireGuard VPN and Minecraft server support.
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
echo "║           SULFUR BOT - LINUX/RASPBERRY PI INSTALLER              ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${YELLOW}⚠️  Running as root. It's recommended to run as a regular user with sudo.${NC}"
fi

# Detect distribution
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
        DISTRO_VERSION=$VERSION_ID
    elif [ -f /etc/lsb-release ]; then
        . /etc/lsb-release
        DISTRO=$DISTRIB_ID
        DISTRO_VERSION=$DISTRIB_RELEASE
    else
        DISTRO="unknown"
    fi
    
    # Check for Raspberry Pi
    if [ -f /proc/cpuinfo ] && grep -q "Raspberry Pi" /proc/cpuinfo; then
        IS_RASPBERRY_PI=true
        echo -e "${GREEN}✅ Detected: Raspberry Pi running $DISTRO${NC}"
    else
        IS_RASPBERRY_PI=false
        echo -e "${GREEN}✅ Detected: $DISTRO Linux${NC}"
    fi
}

# Update package manager
update_packages() {
    echo -e "\n${BLUE}📦 Updating package lists...${NC}"
    echo -e "${CYAN}  This may take a moment. Progress will be shown below.${NC}"
    echo ""
    
    if command -v apt-get &> /dev/null; then
        sudo apt-get update 2>&1 | while read line; do
            echo -e "  ${CYAN}→${NC} $line"
        done
    elif command -v dnf &> /dev/null; then
        sudo dnf check-update 2>&1 | head -20 | while read line; do
            echo -e "  ${CYAN}→${NC} $line"
        done || true
    elif command -v pacman &> /dev/null; then
        sudo pacman -Sy --noconfirm 2>&1 | while read line; do
            echo -e "  ${CYAN}→${NC} $line"
        done
    fi
    echo ""
}

# Install Python
install_python() {
    echo -e "\n${BLUE}🐍 Checking Python installation...${NC}"
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
        echo -e "${GREEN}✅ Python $PYTHON_VERSION found${NC}"
    else
        echo -e "${YELLOW}Installing Python 3...${NC}"
        echo -e "${CYAN}  Progress will be shown below.${NC}"
        echo ""
        
        if command -v apt-get &> /dev/null; then
            sudo apt-get install -y python3 python3-pip python3-venv 2>&1 | grep -E "(Unpacking|Setting up|is already)" | while read line; do
                echo -e "  ${CYAN}→${NC} $line"
            done
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y python3 python3-pip 2>&1 | grep -E "(Installing|Upgrading)" | while read line; do
                echo -e "  ${CYAN}→${NC} $line"
            done
        elif command -v pacman &> /dev/null; then
            sudo pacman -S --noconfirm python python-pip 2>&1 | while read line; do
                echo -e "  ${CYAN}→${NC} $line"
            done
        fi
    fi
    
    # Ensure pip is installed
    if ! command -v pip3 &> /dev/null; then
        echo -e "${YELLOW}Installing pip...${NC}"
        python3 -m ensurepip --upgrade || sudo apt-get install -y python3-pip
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
        
        if command -v apt-get &> /dev/null; then
            sudo apt-get install -y git
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y git
        elif command -v pacman &> /dev/null; then
            sudo pacman -S --noconfirm git
        fi
    fi
}

# Install MariaDB/MySQL
install_database() {
    echo -e "\n${BLUE}🗄️  Checking database installation...${NC}"
    
    if command -v mysql &> /dev/null || command -v mariadb &> /dev/null; then
        echo -e "${GREEN}✅ MySQL/MariaDB found${NC}"
    else
        echo -e "${YELLOW}Installing MariaDB...${NC}"
        echo -e "${CYAN}  This may take a few minutes. Progress will be shown below.${NC}"
        echo ""
        
        if command -v apt-get &> /dev/null; then
            sudo apt-get install -y mariadb-server mariadb-client 2>&1 | grep -E "(Unpacking|Setting up|is already|Selecting)" | while read line; do
                echo -e "  ${CYAN}→${NC} $line"
            done
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y mariadb-server mariadb 2>&1 | grep -E "(Installing|Upgrading|Complete)" | while read line; do
                echo -e "  ${CYAN}→${NC} $line"
            done
        elif command -v pacman &> /dev/null; then
            sudo pacman -S --noconfirm mariadb 2>&1 | while read line; do
                echo -e "  ${CYAN}→${NC} $line"
            done
        fi
        
        echo ""
        echo -e "${CYAN}Starting MariaDB service...${NC}"
        # Start and enable MariaDB
        sudo systemctl start mariadb || sudo systemctl start mysql
        sudo systemctl enable mariadb || sudo systemctl enable mysql
    fi
}

# Install Java (for Minecraft server)
install_java() {
    echo -e "\n${BLUE}☕ Checking Java installation...${NC}"
    
    if command -v java &> /dev/null; then
        JAVA_VERSION=$(java -version 2>&1 | head -n 1)
        echo -e "${GREEN}✅ Java found: $JAVA_VERSION${NC}"
        
        # Check Java version
        JAVA_MAJOR=$(java -version 2>&1 | grep -oP 'version "?\K\d+' | head -1)
        if [ "$JAVA_MAJOR" -lt 17 ]; then
            echo -e "${YELLOW}⚠️  Java $JAVA_MAJOR found but Java 17+ recommended${NC}"
            
            if [ "$INTERACTIVE" = true ]; then
                read -p "Install Java 21? [Y/n]: " install_java_choice
            else
                install_java_choice="n"
                echo -e "${YELLOW}⏭️  Skipping Java 21 installation (non-interactive mode)${NC}"
            fi
            
            if [[ "$install_java_choice" != "n" && "$install_java_choice" != "N" ]]; then
                install_java_21
            fi
        fi
    else
        if [ "$INTERACTIVE" = true ]; then
            read -p "Install Java 21 for Minecraft server? [Y/n]: " install_java_choice
        else
            install_java_choice="n"
            echo -e "${YELLOW}⏭️  Skipping Java installation (non-interactive mode)${NC}"
        fi
        if [[ "$install_java_choice" != "n" && "$install_java_choice" != "N" ]]; then
            install_java_21
        fi
    fi
}

install_java_21() {
    echo -e "${YELLOW}Installing OpenJDK 21...${NC}"
    
    if command -v apt-get &> /dev/null; then
        # Check if openjdk-21 is available
        if apt-cache show openjdk-21-jdk &> /dev/null; then
            sudo apt-get install -y openjdk-21-jdk
        else
            # Use Adoptium repository for older distributions
            echo -e "${YELLOW}Adding Adoptium repository...${NC}"
            wget -qO - https://packages.adoptium.net/artifactory/api/gpg/key/public | sudo apt-key add -
            echo "deb https://packages.adoptium.net/artifactory/deb $(lsb_release -sc) main" | sudo tee /etc/apt/sources.list.d/adoptium.list
            sudo apt-get update
            sudo apt-get install -y temurin-21-jdk
        fi
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y java-21-openjdk java-21-openjdk-devel
    elif command -v pacman &> /dev/null; then
        sudo pacman -S --noconfirm jdk21-openjdk
    fi
}

# Install WireGuard
install_wireguard() {
    echo -e "\n${BLUE}🔐 Checking WireGuard installation...${NC}"
    
    if command -v wg &> /dev/null; then
        echo -e "${GREEN}✅ WireGuard found${NC}"
    else
        if [ "$INTERACTIVE" = true ]; then
            read -p "Install WireGuard VPN? [y/N]: " install_wg_choice
        else
            install_wg_choice="n"
            echo -e "${YELLOW}⏭️  Skipping WireGuard installation (non-interactive mode)${NC}"
        fi
        
        if [[ "$install_wg_choice" == "y" || "$install_wg_choice" == "Y" ]]; then
            echo -e "${YELLOW}Installing WireGuard...${NC}"
            
            if command -v apt-get &> /dev/null; then
                sudo apt-get install -y wireguard wireguard-tools
            elif command -v dnf &> /dev/null; then
                sudo dnf install -y wireguard-tools
            elif command -v pacman &> /dev/null; then
                sudo pacman -S --noconfirm wireguard-tools
            fi
            
            # Load WireGuard kernel module
            sudo modprobe wireguard 2>/dev/null || true
        fi
    fi
}

# Install additional dependencies
install_dependencies() {
    echo -e "\n${BLUE}📦 Installing additional dependencies...${NC}"
    
    if command -v apt-get &> /dev/null; then
        sudo apt-get install -y \
            ffmpeg \
            libffi-dev \
            libnacl-dev \
            libopus0 \
            opus-tools \
            screen \
            curl \
            wget
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y \
            ffmpeg \
            libffi-devel \
            opus \
            screen \
            curl \
            wget
    elif command -v pacman &> /dev/null; then
        sudo pacman -S --noconfirm \
            ffmpeg \
            libffi \
            opus \
            screen \
            curl \
            wget
    fi
}

# Setup Python virtual environment
setup_venv() {
    echo -e "\n${BLUE}🐍 Setting up Python virtual environment...${NC}"
    
    # Get the repository root directory (parent of scripts directory)
    REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    cd "$REPO_DIR"
    
    # Check if venv module is available
    if ! python3 -m venv --help >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠ Python venv module not available. Installing...${NC}"
        
        # Detect Linux distribution
        if [ -f /etc/debian_version ]; then
            # Debian/Ubuntu
            PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
            echo -e "${BLUE}Installing python${PYTHON_VERSION}-venv...${NC}"
            if command -v sudo &> /dev/null; then
                sudo apt-get update -qq && sudo apt-get install -y python${PYTHON_VERSION}-venv python3-venv 2>/dev/null || {
                    echo -e "${RED}✗ Failed to install venv package${NC}"
                    echo -e "${YELLOW}Please install manually: sudo apt install python3-venv${NC}"
                    exit 1
                }
            fi
        elif [ -f /etc/redhat-release ]; then
            # RHEL/CentOS/Fedora
            echo -e "${BLUE}Installing python3-venv...${NC}"
            if command -v sudo &> /dev/null; then
                sudo dnf install -y python3-venv 2>/dev/null || sudo yum install -y python3-venv 2>/dev/null || {
                    echo -e "${RED}✗ Failed to install venv package${NC}"
                    exit 1
                }
            fi
        elif [ -f /etc/arch-release ]; then
            # Arch Linux
            echo -e "${BLUE}Installing python...${NC}"
            if command -v sudo &> /dev/null; then
                sudo pacman -S --noconfirm python 2>/dev/null || {
                    echo -e "${RED}✗ Failed to install venv package${NC}"
                    exit 1
                }
            fi
        fi
    fi
    
    if [ ! -d "$REPO_DIR/venv" ]; then
        if ! python3 -m venv "$REPO_DIR/venv"; then
            echo -e "${RED}✗ Failed to create virtual environment${NC}"
            exit 1
        fi
        echo -e "${GREEN}✅ Virtual environment created${NC}"
    else
        echo -e "${GREEN}✅ Virtual environment already exists${NC}"
    fi
    
    # Activate and install dependencies
    source "$REPO_DIR/venv/bin/activate"
    
    echo -e "${YELLOW}Installing Python dependencies...${NC}"
    pip install --upgrade pip
    pip install -r "$REPO_DIR/requirements.txt"
    
    echo -e "${GREEN}✅ Python dependencies installed${NC}"
}

# Run the master setup wizard
run_setup_wizard() {
    # Get the repository root directory
    REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    
    echo -e "\n${BLUE}🧙 Running setup wizard...${NC}"
    
    source "$REPO_DIR/venv/bin/activate"
    cd "$REPO_DIR"
    python3 master_setup.py
}

# Create systemd service (optional)
create_systemd_service() {
    # Get the repository root directory
    REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    
    if [ "$INTERACTIVE" = true ]; then
        read -p "Create systemd service for auto-start? [y/N]: " create_service
    else
        create_service="n"
        echo -e "${YELLOW}⏭️  Skipping systemd service creation (non-interactive mode)${NC}"
    fi
    
    if [[ "$create_service" == "y" || "$create_service" == "Y" ]]; then
        CURRENT_USER=$(whoami)
        
        sudo tee /etc/systemd/system/sulfur-bot.service > /dev/null << EOF
[Unit]
Description=Sulfur Discord Bot
After=network.target mariadb.service

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$REPO_DIR
ExecStart=$REPO_DIR/venv/bin/python $REPO_DIR/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
        
        sudo systemctl daemon-reload
        sudo systemctl enable sulfur-bot
        
        echo -e "${GREEN}✅ Systemd service created${NC}"
        echo -e "${CYAN}Start with: sudo systemctl start sulfur-bot${NC}"
        echo -e "${CYAN}View logs: sudo journalctl -u sulfur-bot -f${NC}"
    fi
}

# Main installation flow
main() {
    detect_distro
    update_packages
    install_python
    install_git
    install_database
    install_java
    install_wireguard
    install_dependencies
    setup_venv
    
    echo -e "\n${GREEN}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ Installation complete!${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
    
    REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    
    if [ "$INTERACTIVE" = true ]; then
        read -p "Run the setup wizard now? [Y/n]: " run_wizard
    else
        run_wizard="n"
        echo -e "${YELLOW}⏭️  Skipping setup wizard (non-interactive mode)${NC}"
        echo -e "${CYAN}Run later with: cd $REPO_DIR && source venv/bin/activate && python3 master_setup.py${NC}"
    fi
    if [[ "$run_wizard" != "n" && "$run_wizard" != "N" ]]; then
        run_setup_wizard
    fi
    
    create_systemd_service
    
    echo -e "\n${CYAN}Next steps:${NC}"
    echo "  1. Change to bot directory: cd $REPO_DIR"
    echo "  2. Activate the virtual environment: source venv/bin/activate"
    echo "  3. Run the setup wizard: python master_setup.py"
    echo "  4. Start the bot: python bot.py"
    echo "  5. Access the dashboard: http://localhost:5000"
}

# Run main
main
