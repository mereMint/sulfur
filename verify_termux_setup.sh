#!/data/data/com.termux/files/usr/bin/bash
# Termux Installation Verification Script
# Run this after termux_quickstart.sh to verify everything is set up correctly

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   Sulfur Bot - Termux Installation Verification           ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

ERRORS=0
WARNINGS=0

# Function to check command
check_command() {
    if command -v "$1" &> /dev/null; then
        echo -e "${GREEN}[✓]${NC} $2 is installed"
        return 0
    else
        echo -e "${RED}[✗]${NC} $2 is NOT installed"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

# Function to check process
check_process() {
    if pgrep -x "$1" > /dev/null; then
        echo -e "${GREEN}[✓]${NC} $2 is running (PID: $(pgrep -x "$1"))"
        return 0
    else
        echo -e "${RED}[✗]${NC} $2 is NOT running"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

# Function to check file
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}[✓]${NC} $2 exists"
        return 0
    else
        echo -e "${RED}[✗]${NC} $2 does NOT exist"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

# Function to check directory
check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}[✓]${NC} $2 exists"
        return 0
    else
        echo -e "${RED}[✗]${NC} $2 does NOT exist"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

echo -e "${YELLOW}Checking Required Commands...${NC}"
check_command python "Python"
check_command git "Git"
check_command mysql "MySQL/MariaDB client"
check_command mysqld "MySQL/MariaDB server"
check_command ssh "OpenSSH"
echo ""

echo -e "${YELLOW}Checking Running Processes...${NC}"
if ! check_process mysqld; then
    check_process mariadbd  # Try alternate name
fi
echo ""

echo -e "${YELLOW}Checking Repository...${NC}"
REPO_DIR="$HOME/sulfur"
check_dir "$REPO_DIR" "Repository directory ($REPO_DIR)"
if [ -d "$REPO_DIR" ]; then
    cd "$REPO_DIR"
    check_file "bot.py" "Main bot file"
    check_file "web_dashboard.py" "Web dashboard"
    check_file "requirements.txt" "Requirements file"
    check_file ".env" "Environment configuration"
    check_dir "modules" "Modules directory"
    check_dir "config" "Config directory"
fi
echo ""

echo -e "${YELLOW}Checking Python Environment...${NC}"
if [ -d "$REPO_DIR/venv" ]; then
    check_dir "$REPO_DIR/venv" "Virtual environment"
    
    # Activate and check packages
    source "$REPO_DIR/venv/bin/activate"
    
    # Check key packages
    if python -c "import discord" 2>/dev/null; then
        echo -e "${GREEN}[✓]${NC} discord.py is installed"
    else
        echo -e "${RED}[✗]${NC} discord.py is NOT installed"
        ERRORS=$((ERRORS + 1))
    fi
    
    if python -c "import flask" 2>/dev/null; then
        echo -e "${GREEN}[✓]${NC} Flask is installed"
    else
        echo -e "${RED}[✗]${NC} Flask is NOT installed"
        ERRORS=$((ERRORS + 1))
    fi
    
    if python -c "import mysql.connector" 2>/dev/null; then
        echo -e "${GREEN}[✓]${NC} mysql-connector-python is installed"
    else
        echo -e "${RED}[✗]${NC} mysql-connector-python is NOT installed"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "${RED}[✗]${NC} Virtual environment not found"
    ERRORS=$((ERRORS + 1))
fi
echo ""

echo -e "${YELLOW}Checking Database...${NC}"
MYSQL_CMD="mysql"
if command -v mariadb &> /dev/null; then
    MYSQL_CMD="mariadb"
fi

# Check if we can connect
if $MYSQL_CMD -u sulfur_bot_user -e "SELECT 1;" sulfur_bot &>/dev/null; then
    echo -e "${GREEN}[✓]${NC} Database connection successful"
    
    # Check for tables
    TABLE_COUNT=$($MYSQL_CMD -u sulfur_bot_user -s -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'sulfur_bot';" 2>/dev/null)
    if [ "$TABLE_COUNT" -gt 0 ]; then
        echo -e "${GREEN}[✓]${NC} Database has $TABLE_COUNT tables"
    else
        echo -e "${YELLOW}[!]${NC} Database has no tables (run setup_database.sql)"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo -e "${RED}[✗]${NC} Cannot connect to database"
    ERRORS=$((ERRORS + 1))
fi
echo ""

echo -e "${YELLOW}Checking Configuration...${NC}"
if [ -f "$REPO_DIR/.env" ]; then
    # Check for required variables
    if grep -q "DISCORD_BOT_TOKEN=" "$REPO_DIR/.env" && ! grep -q 'DISCORD_BOT_TOKEN="your_discord_bot_token_here"' "$REPO_DIR/.env"; then
        echo -e "${GREEN}[✓]${NC} Discord token is configured"
    else
        echo -e "${RED}[✗]${NC} Discord token is NOT configured"
        ERRORS=$((ERRORS + 1))
    fi
    
    if grep -q "GEMINI_API_KEY=" "$REPO_DIR/.env" && ! grep -q 'GEMINI_API_KEY="your_gemini_api_key_here"' "$REPO_DIR/.env"; then
        echo -e "${GREEN}[✓]${NC} Gemini API key is configured"
    else
        echo -e "${YELLOW}[!]${NC} Gemini API key may not be configured"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo -e "${RED}[✗]${NC} .env file not found"
    ERRORS=$((ERRORS + 1))
fi
echo ""

echo -e "${YELLOW}Checking Scripts...${NC}"
check_file "$REPO_DIR/maintain_bot.sh" "Maintenance script"
check_file "$REPO_DIR/start_sulfur.sh" "Startup helper script"

if [ -f "$REPO_DIR/start_sulfur.sh" ]; then
    if [ -x "$REPO_DIR/start_sulfur.sh" ]; then
        echo -e "${GREEN}[✓]${NC} start_sulfur.sh is executable"
    else
        echo -e "${YELLOW}[!]${NC} start_sulfur.sh is not executable (run: chmod +x start_sulfur.sh)"
        WARNINGS=$((WARNINGS + 1))
    fi
fi
echo ""

echo -e "${YELLOW}Checking Termux-Specific...${NC}"
if [ -d "$HOME/storage" ]; then
    echo -e "${GREEN}[✓]${NC} Termux storage access configured"
else
    echo -e "${YELLOW}[!]${NC} Termux storage not configured (run: termux-setup-storage)"
    WARNINGS=$((WARNINGS + 1))
fi

# Check SSH key
if [ -f "$HOME/.ssh/id_ed25519" ]; then
    echo -e "${GREEN}[✓]${NC} SSH key exists"
else
    echo -e "${YELLOW}[!]${NC} No SSH key found (optional)"
fi
echo ""

# Final Summary
echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                    VERIFICATION SUMMARY                    ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ Perfect! Everything is set up correctly!${NC}"
    echo ""
    echo -e "${CYAN}You're ready to start the bot:${NC}"
    echo -e "  ${GREEN}cd ~/sulfur && ./start_sulfur.sh${NC}"
    echo ""
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ Setup is complete with $WARNINGS warning(s)${NC}"
    echo ""
    echo -e "${CYAN}You can start the bot, but review the warnings above.${NC}"
    echo -e "  ${GREEN}cd ~/sulfur && ./start_sulfur.sh${NC}"
    echo ""
else
    echo -e "${RED}✗ Found $ERRORS error(s) and $WARNINGS warning(s)${NC}"
    echo ""
    echo -e "${YELLOW}Please fix the errors above before starting the bot.${NC}"
    echo ""
    echo -e "${CYAN}Common fixes:${NC}"
    echo -e "  • Start MariaDB: ${GREEN}mysqld_safe --datadir=\$PREFIX/var/lib/mysql &${NC}"
    echo -e "  • Install packages: ${GREEN}pip install -r requirements.txt${NC}"
    echo -e "  • Configure .env: ${GREEN}nano .env${NC}"
    echo -e "  • Run database setup: ${GREEN}mysql -u sulfur_bot_user sulfur_bot < setup_database.sql${NC}"
    echo ""
fi

# Show quick commands
echo -e "${CYAN}Quick Commands:${NC}"
echo -e "  View logs:       ${GREEN}tail -f ~/sulfur/logs/session_*.log${NC}"
echo -e "  Web dashboard:   ${GREEN}http://localhost:5000${NC}"
echo -e "  Stop bot:        ${GREEN}Press Q or touch ~/sulfur/stop.flag${NC}"
echo -e "  Restart bot:     ${GREEN}touch ~/sulfur/restart.flag${NC}"
echo ""

exit $ERRORS
