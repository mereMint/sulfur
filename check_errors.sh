#!/bin/bash
# Automated error checking script for Sulfur Discord Bot
# Run this before starting the bot to catch potential issues

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

echo ""
echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}  Sulfur Bot - Error Detection System     ${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""

ERROR_COUNT=0
WARNING_COUNT=0

# Detect Python command
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${RED}✗ Python not found!${NC}"
    exit 1
fi

# === 1. Check Python Syntax ===
echo -e "${YELLOW}[1/7] Checking Python syntax...${NC}"
SYNTAX_ERRORS=()
mapfile -t PY_FILES < <(find . -name "*.py" -type f ! -path "*/venv/*" ! -path "*/__pycache__/*" ! -path "*/.git/*" ! -path "*/backups/*")
TOTAL=${#PY_FILES[@]}
CURRENT=0

echo -e "${GRAY}  Found $TOTAL Python files to check...${NC}"

for file in "${PY_FILES[@]}"; do
    ((CURRENT++))
    echo -ne "\r${GRAY}  Checking file $CURRENT/$TOTAL : $(basename "$file")...${NC}"
    if ! $PYTHON_CMD -m py_compile "$file" 2>/dev/null; then
        echo ""
        echo -e "${RED}  ✗ Syntax error in: $(basename "$file")${NC}"
        SYNTAX_ERRORS+=("$(basename "$file")")
        ((ERROR_COUNT++))
    fi
done
echo ""

if [ ${#SYNTAX_ERRORS[@]} -eq 0 ]; then
    echo -e "${GREEN}  ✓ No syntax errors detected${NC}"
else
    echo -e "${RED}  ✗ Syntax errors in:${NC}"
    for err in "${SYNTAX_ERRORS[@]}"; do
        echo -e "${RED}    - $err${NC}"
    done
fi

# === 2. Check Critical Files Exist ===
echo ""
echo -e "${YELLOW}[2/7] Checking required files...${NC}"
REQUIRED_FILES=(
    "bot.py"
    "config/config.json"
    "config/system_prompt.txt"
    ".env"
    "requirements.txt"
    "modules/db_helpers.py"
    "modules/api_helpers.py"
    "web_dashboard.py"
)

MISSING_FILES=()
for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        MISSING_FILES+=("$file")
        ((ERROR_COUNT++))
    fi
done

if [ ${#MISSING_FILES[@]} -eq 0 ]; then
    echo -e "${GREEN}  ✓ All required files present${NC}"
else
    echo -e "${RED}  ✗ Missing files:${NC}"
    for file in "${MISSING_FILES[@]}"; do
        echo -e "${RED}    - $file${NC}"
    done
fi

# === 3. Check Config JSON Validity ===
echo ""
echo -e "${YELLOW}[3/7] Validating config.json...${NC}"
if [ -f "config/config.json" ]; then
    CONFIG_CHECK=$($PYTHON_CMD -c "import json; json.load(open('config/config.json')); print('OK')" 2>&1)
    if [[ "$CONFIG_CHECK" == "OK" ]]; then
        echo -e "${GREEN}  ✓ Config JSON is valid${NC}"
        
        # Check for required config sections
        REQUIRED_SECTIONS=("bot" "api" "database" "modules")
        MISSING_SECTIONS=()
        
        for section in "${REQUIRED_SECTIONS[@]}"; do
            if ! $PYTHON_CMD -c "import json; cfg=json.load(open('config/config.json')); exit(0 if '$section' in cfg else 1)" 2>/dev/null; then
                MISSING_SECTIONS+=("$section")
                ((WARNING_COUNT++))
            fi
        done
        
        if [ ${#MISSING_SECTIONS[@]} -gt 0 ]; then
            echo -e "${YELLOW}  ⚠ Missing config sections:${NC}"
            for section in "${MISSING_SECTIONS[@]}"; do
                echo -e "${YELLOW}    - $section${NC}"
            done
        fi
    else
        echo -e "${RED}  ✗ Config JSON is malformed${NC}"
        echo -e "${RED}    $CONFIG_CHECK${NC}"
        ((ERROR_COUNT++))
    fi
else
    echo -e "${RED}  ✗ config/config.json not found${NC}"
    ((ERROR_COUNT++))
fi

# === 4. Check Environment Variables ===
echo ""
echo -e "${YELLOW}[4/7] Checking environment variables...${NC}"
if [ -f ".env" ]; then
    ENV_ISSUES=()
    
    # Check for DISCORD_BOT_TOKEN
    if ! grep -q "^DISCORD_BOT_TOKEN=" .env; then
        ENV_ISSUES+=("DISCORD_BOT_TOKEN not found")
        ((ERROR_COUNT++))
    else
        TOKEN=$(grep "^DISCORD_BOT_TOKEN=" .env | cut -d= -f2- | tr -d '"' | tr -d "'" | xargs)
        if [ -z "$TOKEN" ]; then
            ENV_ISSUES+=("DISCORD_BOT_TOKEN is empty")
            ((ERROR_COUNT++))
        elif [ "$TOKEN" = "your_discord_bot_token_here" ]; then
            ENV_ISSUES+=("DISCORD_BOT_TOKEN is still placeholder value")
            ((ERROR_COUNT++))
        fi
    fi
    
    # Check for API keys
    if ! grep -q "^GEMINI_API_KEY=" .env && ! grep -q "^OPENAI_API_KEY=" .env; then
        ENV_ISSUES+=("No AI API keys configured (need GEMINI_API_KEY or OPENAI_API_KEY)")
        ((WARNING_COUNT++))
    fi
    
    if [ ${#ENV_ISSUES[@]} -eq 0 ]; then
        echo -e "${GREEN}  ✓ Environment variables look good${NC}"
    else
        echo -e "${RED}  ✗ Environment issues:${NC}"
        for issue in "${ENV_ISSUES[@]}"; do
            echo -e "${RED}    - $issue${NC}"
        done
    fi
else
    echo -e "${RED}  ✗ .env file not found${NC}"
    echo -e "${GRAY}    Copy .env.example to .env and fill in your values${NC}"
    ((ERROR_COUNT++))
fi

# === 5. Check MySQL/MariaDB Connection ===
echo ""
echo -e "${YELLOW}[5/7] Checking database connection...${NC}"
if command -v mysql &> /dev/null || command -v mariadb &> /dev/null; then
    DB_CMD="mysql"
    if command -v mariadb &> /dev/null; then
        DB_CMD="mariadb"
    fi
    
    # Check if MySQL is running
    if pgrep -x mysqld > /dev/null 2>&1 || pgrep -x mariadbd > /dev/null 2>&1; then
        echo -e "${GREEN}  ✓ MySQL/MariaDB is running${NC}"
        
        # Try to connect (requires .env)
        if [ -f ".env" ]; then
            DB_USER=$(grep "^DB_USER=" .env | cut -d= -f2- | tr -d '"' | tr -d "'" | xargs)
            DB_PASS=$(grep "^DB_PASS=" .env | cut -d= -f2- | tr -d '"' | tr -d "'" | xargs)
            DB_NAME=$(grep "^DB_NAME=" .env | cut -d= -f2- | tr -d '"' | tr -d "'" | xargs)
            
            if [ -n "$DB_USER" ] && [ -n "$DB_NAME" ]; then
                if [ -z "$DB_PASS" ]; then
                    TEST_CONN=$($DB_CMD -u "$DB_USER" -e "SELECT 1;" "$DB_NAME" 2>&1)
                else
                    TEST_CONN=$($DB_CMD -u "$DB_USER" -p"$DB_PASS" -e "SELECT 1;" "$DB_NAME" 2>&1)
                fi
                
                if [ $? -eq 0 ]; then
                    echo -e "${GREEN}  ✓ Database connection successful${NC}"
                else
                    echo -e "${YELLOW}  ⚠ Could not connect to database${NC}"
                    echo -e "${GRAY}    Make sure database and user exist${NC}"
                    ((WARNING_COUNT++))
                fi
            fi
        fi
    else
        echo -e "${YELLOW}  ⚠ MySQL/MariaDB is not running${NC}"
        echo -e "${GRAY}    Start it with: sudo systemctl start mysql (or mariadb)${NC}"
        echo -e "${GRAY}    Or on Termux: mysqld_safe &${NC}"
        ((WARNING_COUNT++))
    fi
else
    echo -e "${YELLOW}  ⚠ MySQL/MariaDB not installed${NC}"
    ((WARNING_COUNT++))
fi

# === 6. Check Dependencies ===
echo ""
echo -e "${YELLOW}[6/7] Checking Python dependencies...${NC}"
if [ -f "requirements.txt" ]; then
    MISSING_DEPS=()
    while IFS= read -r dep; do
        # Skip empty lines and comments
        [[ -z "$dep" || "$dep" =~ ^# ]] && continue
        
        # Extract package name (before any ==, >=, etc.)
        pkg_name=$(echo "$dep" | sed 's/[>=<].*//' | xargs)
        
        if ! $PYTHON_CMD -c "import importlib.util; exit(0 if importlib.util.find_spec('${pkg_name//-/_}') else 1)" 2>/dev/null; then
            MISSING_DEPS+=("$pkg_name")
        fi
    done < requirements.txt
    
    if [ ${#MISSING_DEPS[@]} -eq 0 ]; then
        echo -e "${GREEN}  ✓ All dependencies installed${NC}"
    else
        echo -e "${YELLOW}  ⚠ Missing dependencies (run: pip install -r requirements.txt):${NC}"
        for dep in "${MISSING_DEPS[@]}"; do
            echo -e "${YELLOW}    - $dep${NC}"
        done
        ((WARNING_COUNT++))
    fi
else
    echo -e "${RED}  ✗ requirements.txt not found${NC}"
    ((ERROR_COUNT++))
fi

# === 7. Check Git Repository Status ===
echo ""
echo -e "${YELLOW}[7/7] Checking Git repository status...${NC}"
if [ -d ".git" ]; then
    # Check if .env is in .gitignore
    if grep -q "^\.env$" .gitignore 2>/dev/null; then
        echo -e "${GREEN}  ✓ .env is in .gitignore${NC}"
    else
        echo -e "${YELLOW}  ⚠ .env should be in .gitignore to avoid committing secrets${NC}"
        ((WARNING_COUNT++))
    fi
    
    # Check if .env is tracked
    if git ls-files --error-unmatch .env > /dev/null 2>&1; then
        echo -e "${RED}  ✗ CRITICAL: .env file is tracked in git!${NC}"
        echo -e "${RED}    Run: git rm --cached .env${NC}"
        ((ERROR_COUNT++))
    fi
else
    echo -e "${GRAY}  ℹ Not a git repository (that's okay)${NC}"
fi

# === Summary ===
echo ""
echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}  Summary${NC}"
echo -e "${CYAN}============================================${NC}"

if [ $ERROR_COUNT -eq 0 ] && [ $WARNING_COUNT -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed! Bot is ready to start.${NC}"
    exit 0
elif [ $ERROR_COUNT -eq 0 ]; then
    echo -e "${YELLOW}⚠ $WARNING_COUNT warning(s) found (bot may still work)${NC}"
    exit 0
else
    echo -e "${RED}✗ $ERROR_COUNT error(s) and $WARNING_COUNT warning(s) found${NC}"
    echo -e "${RED}Please fix the errors before starting the bot.${NC}"
    exit 1
fi
