#!/bin/bash
# ============================================================
# Sulfur Bot - MySQL Setup Helper for Termux/Linux
# ============================================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║         Sulfur Bot - MySQL Setup Helper                   ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Detect environment
if [ -n "$TERMUX_VERSION" ]; then
    IS_TERMUX=true
    echo -e "${CYAN}Detected: Termux${NC}"
else
    IS_TERMUX=false
    echo -e "${CYAN}Detected: Linux${NC}"
fi

# Check if MySQL/MariaDB is running
echo -e "${YELLOW}Checking MySQL/MariaDB status...${NC}"

if pgrep mysqld > /dev/null 2>&1; then
    echo -e "${GREEN}✓ MySQL/MariaDB is running${NC}"
else
    echo -e "${RED}✗ MySQL/MariaDB is not running!${NC}"
    echo ""
    echo -e "${YELLOW}Starting MySQL/MariaDB...${NC}"
    
    if [ "$IS_TERMUX" = true ]; then
        # Termux
        if [ ! -d "$PREFIX/var/lib/mysql" ]; then
            echo -e "${YELLOW}Initializing MySQL...${NC}"
            mysql_install_db
        fi
        
        echo -e "${YELLOW}Starting MySQL with mysqld_safe...${NC}"
        mysqld_safe --datadir=$PREFIX/var/lib/mysql &
        sleep 3
    else
        # Linux
        if command -v systemctl &> /dev/null; then
            sudo systemctl start mysql || sudo systemctl start mariadb
        else
            sudo service mysql start || sudo service mariadb start
        fi
    fi
    
    # Check again
    sleep 2
    if pgrep mysqld > /dev/null 2>&1; then
        echo -e "${GREEN}✓ MySQL/MariaDB started successfully${NC}"
    else
        echo -e "${RED}✗ Failed to start MySQL/MariaDB${NC}"
        echo -e "${YELLOW}Please start it manually and run this script again${NC}"
        exit 1
    fi
fi

# Run setup
echo ""
echo -e "${YELLOW}Running database setup script...${NC}"
echo -e "${CYAN}You will be prompted for the MySQL root password.${NC}"
echo -e "${CYAN}(In Termux, the default is usually empty - just press Enter)${NC}"
echo ""

if mysql -u root -p < setup_database.sql; then
    echo ""
    echo -e "${GREEN}✓ Database setup complete!${NC}"
    echo ""
    echo -e "${CYAN}Database credentials:${NC}"
    echo -e "  Host: localhost"
    echo -e "  User: sulfur_bot_user"
    echo -e "  Password: (empty)"
    echo -e "  Database: sulfur_bot"
    echo ""
    echo -e "${YELLOW}These are already configured in your .env file.${NC}"
else
    echo ""
    echo -e "${RED}✗ Setup failed. Please check the error messages above.${NC}"
    exit 1
fi

# Test connection
echo ""
echo -e "${YELLOW}Testing connection...${NC}"

if mysql -u sulfur_bot_user sulfur_bot -e "SELECT 'Connection successful!' AS status;" 2>/dev/null; then
    echo -e "${GREEN}✓ Connection test passed!${NC}"
    echo ""
    echo -e "${CYAN}Next steps:${NC}"
    echo -e "1. Install dependencies: pip install -r requirements.txt"
    echo -e "2. Run setup test: python test_setup.py"
    echo -e "3. Start the bot: ./start.sh"
else
    echo -e "${RED}✗ Connection test failed${NC}"
    exit 1
fi

echo ""
