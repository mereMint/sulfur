#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# Sulfur Bot - Complete Termux Quick Start Script
# ============================================================
# This script automates EVERYTHING needed to run the bot on Termux
# Usage: bash termux_quickstart.sh

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║  Sulfur Bot - Complete Termux Installation & Setup        ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_info() {
    echo -e "${CYAN}[i]${NC} $1"
}

# Check if running in Termux
if [ -z "$TERMUX_VERSION" ]; then
    print_error "This script is designed for Termux only!"
    print_info "For Linux/WSL, use quick_setup.sh instead."
    exit 1
fi

print_header

# ============================================================
# STEP 0: Setup Termux Storage (Important!)
# ============================================================
print_step "Step 0: Setting up Termux storage access..."
echo ""

if [ ! -d "$HOME/storage" ]; then
    print_info "Requesting storage permissions..."
    print_warning "Please ALLOW storage access when prompted!"
    termux-setup-storage
    sleep 2
    if [ -d "$HOME/storage" ]; then
        print_success "Storage access granted!"
    else
        print_warning "Storage access not granted - you can run 'termux-setup-storage' later"
    fi
else
    print_success "Storage access already configured"
fi

echo ""

# ============================================================
# STEP 1: Update Termux Packages
# ============================================================
print_step "Step 1: Updating Termux packages..."
echo ""

print_info "Updating package lists..."
pkg update -y

print_info "Upgrading installed packages..."
pkg upgrade -y

print_success "Termux packages updated!"
echo ""

# ============================================================
# STEP 2: Install Required Packages
# ============================================================
print_step "Step 2: Installing required packages..."
echo ""

REQUIRED_PACKAGES=(
    "python"
    "git"
    "mariadb"
    "openssh"
    "nano"
    "wget"
    "curl"
)

print_info "Installing all required packages (this may take a few minutes)..."
pkg install -y python git mariadb openssh nano wget curl

for package in "${REQUIRED_PACKAGES[@]}"; do
    if command -v "$package" &> /dev/null || pkg list-installed 2>/dev/null | grep -q "^${package}"; then
        print_success "$package is installed"
    else
        print_warning "$package may not be installed correctly"
    fi
done

echo ""

# ============================================================
# STEP 3: Setup MariaDB
# ============================================================
print_step "Step 3: Setting up MariaDB database..."
echo ""

# Check if MariaDB is initialized
if [ ! -d "$PREFIX/var/lib/mysql/mysql" ]; then
    print_info "Initializing MariaDB..."
    mysql_install_db
    print_success "MariaDB initialized!"
else
    print_success "MariaDB already initialized"
fi

# Start MariaDB
print_info "Starting MariaDB server..."
if pgrep -x mysqld > /dev/null || pgrep -x mariadbd > /dev/null; then
    print_success "MariaDB is already running"
else
    # Start in background
    print_info "This may take 10-15 seconds..."
    mysqld_safe --datadir=$PREFIX/var/lib/mysql > /dev/null 2>&1 &
    
    # Wait up to 15 seconds for MariaDB to start
    for i in {1..15}; do
        if pgrep -x mysqld > /dev/null || pgrep -x mariadbd > /dev/null; then
            print_success "MariaDB started after $i seconds!"
            break
        fi
        sleep 1
    done
fi

# Verify MariaDB is running
if pgrep -x mysqld > /dev/null || pgrep -x mariadbd > /dev/null; then
    print_success "MariaDB is running (PID: $(pgrep -x mysqld || pgrep -x mariadbd))"
else
    print_error "Failed to start MariaDB!"
    print_info "Try running manually: mysqld_safe --datadir=\$PREFIX/var/lib/mysql &"
    print_info "Then wait 10 seconds and run this script again."
    exit 1
fi

echo ""

# ============================================================
# STEP 4: Setup Database & User
# ============================================================
print_step "Step 4: Creating database and user..."
echo ""

# Use mysql client (or mariadb client)
MYSQL_CMD="mysql"
if command -v mariadb &> /dev/null; then
    MYSQL_CMD="mariadb"
fi

# Wait a bit more to ensure MariaDB is fully ready
sleep 2

print_info "Creating database 'sulfur_bot'..."
if $MYSQL_CMD -u root <<EOF 2>/dev/null
CREATE DATABASE IF NOT EXISTS sulfur_bot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EOF
then
    print_success "Database created!"
else
    print_warning "Database may already exist or there was an issue"
fi

print_info "Creating user 'sulfur_bot_user'..."
if $MYSQL_CMD -u root <<EOF 2>/dev/null
CREATE USER IF NOT EXISTS 'sulfur_bot_user'@'localhost';
GRANT ALL PRIVILEGES ON sulfur_bot.* TO 'sulfur_bot_user'@'localhost';
FLUSH PRIVILEGES;
EOF
then
    print_success "User created with full permissions!"
else
    print_warning "User may already exist or there was an issue"
    print_info "Attempting to grant permissions anyway..."
    $MYSQL_CMD -u root <<EOF 2>/dev/null
GRANT ALL PRIVILEGES ON sulfur_bot.* TO 'sulfur_bot_user'@'localhost';
FLUSH PRIVILEGES;
EOF
fi

# Verify database connection
if $MYSQL_CMD -u sulfur_bot_user -e "USE sulfur_bot; SELECT 1;" >/dev/null 2>&1; then
    print_success "Database connection verified!"
else
    print_error "Cannot connect to database as sulfur_bot_user"
    print_info "The bot may still work, but check database configuration"
fi

echo ""

# ============================================================
# STEP 5: Clone/Update Repository
# ============================================================
print_step "Step 5: Setting up bot repository..."
echo ""

REPO_DIR="$HOME/sulfur"

if [ -d "$REPO_DIR/.git" ]; then
    print_warning "Repository already exists at $REPO_DIR"
    read -p "Do you want to update it? (y/n): " UPDATE_REPO
    if [[ "$UPDATE_REPO" =~ ^[Yy]$ ]]; then
        cd "$REPO_DIR"
        print_info "Pulling latest changes..."
        git pull
        print_success "Repository updated!"
    else
        print_info "Keeping existing repository"
        cd "$REPO_DIR"
    fi
elif [ -d "$REPO_DIR" ]; then
    print_warning "Directory $REPO_DIR exists but is not a git repository"
    read -p "Remove it and clone fresh? (y/n): " REMOVE_DIR
    if [[ "$REMOVE_DIR" =~ ^[Yy]$ ]]; then
        rm -rf "$REPO_DIR"
        print_info "Cloning repository..."
        read -p "Enter your GitHub username (or press Enter for 'mereMint'): " GITHUB_USER
        GITHUB_USER="${GITHUB_USER:-mereMint}"
        
        if git clone "https://github.com/$GITHUB_USER/sulfur.git" "$REPO_DIR"; then
            print_success "Repository cloned to $REPO_DIR"
        else
            print_error "Failed to clone repository!"
            print_info "Check your internet connection and GitHub username"
            exit 1
        fi
    else
        print_info "Using existing directory"
        cd "$REPO_DIR"
    fi
else
    print_info "Cloning repository..."
    read -p "Enter your GitHub username (or press Enter for 'mereMint'): " GITHUB_USER
    GITHUB_USER="${GITHUB_USER:-mereMint}"
    
    if git clone "https://github.com/$GITHUB_USER/sulfur.git" "$REPO_DIR"; then
        print_success "Repository cloned to $REPO_DIR"
    else
        print_error "Failed to clone repository!"
        print_info "Check your internet connection and GitHub username"
        exit 1
    fi
fi

cd "$REPO_DIR"
echo ""

# ============================================================
# STEP 6: Setup SSH Key for Git (Optional)
# ============================================================
print_step "Step 6: Setting up SSH key for GitHub..."
echo ""

SSH_KEY_PATH="$HOME/.ssh/id_ed25519"

if [ -f "$SSH_KEY_PATH" ]; then
    print_success "SSH key already exists at $SSH_KEY_PATH"
else
    read -p "Do you want to generate an SSH key for GitHub? (y/n): " GEN_SSH
    if [[ "$GEN_SSH" =~ ^[Yy]$ ]]; then
        print_info "Generating SSH key..."
        read -p "Enter your GitHub email: " GITHUB_EMAIL
        
        ssh-keygen -t ed25519 -C "$GITHUB_EMAIL" -f "$SSH_KEY_PATH" -N ""
        
        print_success "SSH key generated!"
        print_info "Your public key:"
        echo ""
        cat "${SSH_KEY_PATH}.pub"
        echo ""
        print_warning "IMPORTANT: Add this key to GitHub:"
        print_info "1. Go to https://github.com/settings/keys"
        print_info "2. Click 'New SSH key'"
        print_info "3. Paste the key shown above"
        print_info "4. Give it a name like 'Termux - $(date +%Y-%m-%d)'"
        echo ""
        read -p "Press Enter when you've added the key to GitHub..."
        
        # Test SSH connection
        print_info "Testing SSH connection to GitHub..."
        if ssh -T git@github.com 2>&1 | grep -q "successfully authenticated"; then
            print_success "SSH connection successful!"
            
            # Update remote to use SSH
            print_info "Updating git remote to use SSH..."
            git remote set-url origin "git@github.com:$GITHUB_USER/sulfur.git"
            print_success "Git remote updated to use SSH!"
        else
            print_warning "SSH test failed, but you can configure it later"
        fi
    else
        print_info "Skipping SSH key generation"
    fi
fi

echo ""

# ============================================================
# STEP 7: Setup Python Virtual Environment
# ============================================================
print_step "Step 7: Setting up Python virtual environment..."
echo ""

if [ -d "venv" ]; then
    print_success "Virtual environment already exists"
else
    print_info "Creating virtual environment..."
    python -m venv venv
    print_success "Virtual environment created!"
fi

print_info "Activating virtual environment..."
source venv/bin/activate

echo ""

# ============================================================
# STEP 8: Install Python Dependencies
# ============================================================
print_step "Step 8: Installing Python dependencies..."
echo ""

print_info "Upgrading pip..."
pip install --upgrade pip --quiet

print_info "Installing required packages (this may take several minutes)..."
print_warning "Don't worry if you see warnings about 'legacy setup.py install' - this is normal"
echo ""

if pip install -r requirements.txt; then
    print_success "All Python dependencies installed!"
else
    print_error "Some packages failed to install"
    print_info "Trying again with --no-cache-dir flag..."
    pip install -r requirements.txt --no-cache-dir
fi

echo ""

# ============================================================
# STEP 9: Configure Environment Variables
# ============================================================
print_step "Step 9: Configuring environment variables..."
echo ""

if [ -f ".env" ]; then
    print_warning ".env file already exists"
    read -p "Do you want to reconfigure it? (y/n): " RECONFIG_ENV
    if [[ ! "$RECONFIG_ENV" =~ ^[Yy]$ ]]; then
        print_info "Keeping existing .env file"
        ENV_EXISTS=1
    fi
fi

if [ -z "$ENV_EXISTS" ]; then
    print_info "Creating .env file..."
    
    # Discord Token
    echo -e "${YELLOW}Enter your Discord Bot Token:${NC}"
    read -p "> " DISCORD_TOKEN
    
    # Gemini API Key
    echo -e "${YELLOW}Enter your Gemini API Key (or press Enter to skip):${NC}"
    read -p "> " GEMINI_KEY
    
    # OpenAI API Key
    echo -e "${YELLOW}Enter your OpenAI API Key (or press Enter to skip):${NC}"
    read -p "> " OPENAI_KEY
    
    # Create .env file (without quotes around values to avoid escaping issues)
    cat > .env <<EOF
# Discord Bot Token
DISCORD_BOT_TOKEN=${DISCORD_TOKEN}

# AI API Keys
GEMINI_API_KEY=${GEMINI_KEY}
OPENAI_API_KEY=${OPENAI_KEY}

# Database Configuration
DB_HOST=localhost
DB_USER=sulfur_bot_user
DB_PASS=
DB_NAME=sulfur_bot

# Optional Settings
# BOT_PREFIX=!
# OWNER_ID=your_discord_user_id
EOF
    
    print_success ".env file created!"
fi

echo ""

# ============================================================
# STEP 10: Initialize Database Tables
# ============================================================
print_step "Step 10: Initializing database tables..."
echo ""

if [ -f "setup_database.sql" ]; then
    print_info "Running database setup script..."
    if $MYSQL_CMD -u sulfur_bot_user sulfur_bot < setup_database.sql 2>/dev/null; then
        print_success "Database tables created!"
    else
        print_warning "Database setup had some issues, but tables may already exist"
        print_info "The bot will create any missing tables on first run"
    fi
else
    print_warning "setup_database.sql not found"
    print_info "Running Python setup script instead..."
    if [ -f "setup_database.py" ]; then
        python setup_database.py 2>/dev/null || print_info "Tables will be created on first bot run"
    else
        print_info "Database tables will be created on first bot run"
    fi
fi

echo ""

# ============================================================
# STEP 11: Run Tests
# ============================================================
print_step "Step 11: Running setup verification..."
echo ""

if [ -f "verify_termux_setup.sh" ]; then
    print_info "Running Termux-specific verification..."
    chmod +x verify_termux_setup.sh
    if bash verify_termux_setup.sh; then
        print_success "Verification passed!"
    else
        print_warning "Some verification checks failed - review above"
        print_info "You can still try to run the bot"
    fi
elif [ -f "test_setup.py" ]; then
    print_info "Running Python setup verification..."
    if python test_setup.py; then
        print_success "Verification passed!"
    else
        print_warning "Some verification checks failed - review above"
        print_info "You can still try to run the bot"
    fi
else
    print_warning "No verification script found, skipping tests"
    print_info "You can run 'python test_setup.py' later to verify"
fi

echo ""

# ============================================================
# STEP 12: Create Startup Script
# ============================================================
print_step "Step 12: Creating startup helper..."
echo ""

cat > start_sulfur.sh <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
# Quick start script for Sulfur bot

cd ~/sulfur

# Start MariaDB if not running
if ! pgrep -x mysqld > /dev/null && ! pgrep -x mariadbd > /dev/null; then
    echo "Starting MariaDB..."
    mysqld_safe --datadir=$PREFIX/var/lib/mysql &
    sleep 3
fi

# Activate virtual environment
source venv/bin/activate

# Run the bot with maintenance script
bash maintain_bot.sh
EOF

chmod +x start_sulfur.sh

print_success "Created start_sulfur.sh helper script!"
echo ""

# ============================================================
# FINAL SUMMARY
# ============================================================
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                  INSTALLATION COMPLETE! 🎉                 ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${CYAN}Quick Start Guide:${NC}"
echo ""
echo -e "1. ${YELLOW}To start the bot:${NC}"
echo -e "   ${GREEN}cd ~/sulfur && ./start_sulfur.sh${NC}"
echo ""
echo -e "2. ${YELLOW}Or manually:${NC}"
echo -e "   ${GREEN}cd ~/sulfur${NC}"
echo -e "   ${GREEN}source venv/bin/activate${NC}"
echo -e "   ${GREEN}bash maintain_bot.sh${NC}"
echo ""
echo -e "3. ${YELLOW}Access Web Dashboard:${NC}"
echo -e "   ${GREEN}http://localhost:5000${NC}"
echo -e "   (Or from another device on same network: http://YOUR_PHONE_IP:5000)"
echo ""
echo -e "4. ${YELLOW}Stop the bot:${NC}"
echo -e "   ${GREEN}Press 'Q' in the terminal${NC}"
echo -e "   ${GREEN}Or create a stop flag: touch ~/sulfur/stop.flag${NC}"
echo ""

print_info "Repository location: $REPO_DIR"
print_info "Virtual environment: $REPO_DIR/venv"
print_info "Database: sulfur_bot (user: sulfur_bot_user, no password)"

echo ""
print_warning "IMPORTANT REMINDERS:"
echo -e "  ${YELLOW}1. Keep Termux Running:${NC}"
echo -e "     • Long-press Termux notification → 'Acquire Wake Lock'"
echo -e "     • Settings → Apps → Termux → Battery → Unrestricted"
echo -e ""
echo -e "  ${YELLOW}2. MariaDB Management:${NC}"
echo -e "     • MariaDB must be running before starting the bot"
echo -e "     • Start manually: ${GREEN}mysqld_safe --datadir=\$PREFIX/var/lib/mysql &${NC}"
echo -e "     • Check if running: ${GREEN}pgrep mysqld${NC}"
echo -e ""
echo -e "  ${YELLOW}3. Auto-Start on Boot:${NC}"
echo -e "     • Install Termux:Boot from F-Droid"
echo -e "     • See TERMUX_GUIDE.md for setup instructions"

echo ""
echo -e "${CYAN}Need help?${NC}"
echo -e "  • Check ${GREEN}README.md${NC} for detailed documentation"
echo -e "  • See ${GREEN}TERMUX_GUIDE.md${NC} for Termux-specific guide"
echo -e "  • Run ${GREEN}bash verify_termux_setup.sh${NC} to verify setup"
echo -e "  • Visit the web dashboard for live monitoring"

echo ""
echo -e "${GREEN}Happy botting! 🤖${NC}"
