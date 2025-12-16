#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# Sulfur Bot - Complete Termux Quick Start Script
# ============================================================
# This script automates EVERYTHING needed to run the bot on Termux
#
# IMPORTANT: This repo is PRIVATE - you need credentials or SSH!
# 
# For private repo access, use one of these methods:
#
# METHOD 1: Fork the repo and use your fork:
#   pkg update && pkg install -y git && git clone --depth 1 https://github.com/YOUR_USERNAME/sulfur.git sulfur && cd sulfur && bash termux_quickstart.sh
#
# METHOD 2: Use Personal Access Token:
#   When git asks for password, use a token from https://github.com/settings/tokens
#
# METHOD 3: Already have the repo cloned?
#   cd sulfur && bash termux_quickstart.sh
#
# Usage: bash termux_quickstart.sh [--install-dir /path/to/install]
#
# Options:
#   --install-dir DIR   Custom installation directory (default: ~/sulfur)
#   -h, --help          Show this help message

# Note: We don't use 'set -e' because some commands may have warnings
# that shouldn't stop the script (like apt warnings)

# Parse command line arguments
CUSTOM_INSTALL_DIR=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --install-dir|-d)
            CUSTOM_INSTALL_DIR="$2"
            shift 2
            ;;
        -h|--help)
            echo "Sulfur Bot Termux Quick Start Script"
            echo ""
            echo "Usage: bash termux_quickstart.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --install-dir DIR   Custom installation directory (default: ~/sulfur)"
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

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Functions
ask_yes_no() {
    local prompt="$1"
    local default_choice="$2" # y or n
    local choice
    while true; do
        read -r -p "$prompt [y/n] " choice
        choice=${choice:-$default_choice}
        case "$choice" in
            [Yy]) return 0 ;;
            [Nn]) return 1 ;;
            *) echo "Please enter y or n." ;;
        esac
    done
}

print_divider() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

show_public_key_block() {
    local key_path="$1"
    print_divider
    echo -e "${MAGENTA}Your SSH public key (copy and add to GitHub):${NC}"
    echo ""
    if [ -f "${key_path}.pub" ]; then
        cat "${key_path}.pub"
        echo ""
        if command -v termux-clipboard-set >/dev/null 2>&1; then
            cat "${key_path}.pub" | termux-clipboard-set && echo -e "${GREEN}[✓]${NC} Copied to clipboard"
        fi
    else
        echo -e "${RED}[✗]${NC} Public key not found at ${key_path}.pub"
    fi
    print_divider
}

ssh_setup_wizard() {
    echo ""
    print_divider
    echo -e "${BLUE}SSH Setup Wizard${NC}"
    print_divider

    # Ensure OpenSSH is installed
    if ! command -v ssh >/dev/null 2>&1; then
        print_info "Installing OpenSSH (required for GitHub SSH)..."
        pkg install -y openssh || true
    fi

    SSH_KEY_PATH="$HOME/.ssh/id_ed25519"
    mkdir -p "$HOME/.ssh"

    if [ ! -f "$SSH_KEY_PATH" ]; then
        echo -e "${YELLOW}No SSH key found at ${SSH_KEY_PATH}.${NC}"
        read -r -p "Enter your GitHub email for the key: " GITHUB_EMAIL
        if [ -z "$GITHUB_EMAIL" ]; then
            GITHUB_EMAIL="termux-$(date +%Y%m%d)@local"
        fi
        print_info "Generating SSH key (ed25519)..."
        ssh-keygen -t ed25519 -C "$GITHUB_EMAIL" -f "$SSH_KEY_PATH" -N "" || true
        print_success "SSH key generated!"
    else
        print_success "SSH key already exists at $SSH_KEY_PATH"
    fi

    # Show key and guide user
    show_public_key_block "$SSH_KEY_PATH"
    echo -e "Add this key at: ${GREEN}https://github.com/settings/keys${NC} (New SSH key)"

    # Ask for username if missing, we'll reuse later for clone
    if [ -z "$GITHUB_USER" ]; then
        read -r -p "Your GitHub username (for SSH clone): " GITHUB_USER
    fi

    # Verification loop
    SSH_READY=false
    for attempt in 1 2 3; do
        echo -e "${CYAN}[Attempt $attempt/3] Testing SSH connection to GitHub...${NC}"
        # Suppress host key prompt by auto-accepting in first try
        ssh -o StrictHostKeyChecking=accept-new -T git@github.com 2>&1 | grep -qi "successfully authenticated"
        if [ $? -eq 0 ]; then
            print_success "SSH authentication with GitHub works!"
            SSH_READY=true
            break
        else
            print_warning "SSH test failed. Make sure the key is added to your GitHub account."
            show_public_key_block "$SSH_KEY_PATH"
            if ! ask_yes_no "Open the GitHub keys page on another device and add the key, then retry?" y; then
                break
            fi
        fi
    done

    if [ "$SSH_READY" != true ]; then
        print_warning "SSH not ready. You can still proceed using HTTPS + Personal Access Token."
        if ask_yes_no "Proceed with HTTPS clone (will prompt for PAT)?" y; then
            export SSH_READY=false
        else
            print_error "Cannot proceed without SSH or HTTPS credentials. Exiting."
            exit 1
        fi
    else
        export SSH_READY=true
    fi
}
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

# ---------- MariaDB helpers ----------
_db_client() {
    if command -v mariadb >/dev/null 2>&1; then
        echo mariadb
    else
        echo mysql
    fi
}

_db_is_running() {
    # Prefer pgrep if available
    if command -v pgrep >/dev/null 2>&1; then
        pgrep -x mysqld >/dev/null 2>&1 || pgrep -x mariadbd >/dev/null 2>&1
        return $?
    fi
    # Fallback to ps/grep (avoid matching the grep process)
    ps aux 2>/dev/null | grep -E "[m]ysqld|[m]ariadbd" >/dev/null 2>&1
}

_db_is_ready() {
    local client
    client=$(_db_client)
    # Try a simple ping via SQL
    ${client} -u root -e "SELECT 1" >/dev/null 2>&1
}

_db_start_if_needed() {
    if _db_is_ready; then
        return 0
    fi
    if _db_is_running; then
        # Running but not ready yet; continue to wait in caller
        return 1
    fi
    mysqld_safe >/dev/null 2>&1 &
    return 2
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
if ! pkg update -y; then
    print_warning "Package update had some warnings, but continuing..."
fi

print_info "Upgrading installed packages..."
if ! pkg upgrade -y; then
    print_warning "Package upgrade had some warnings, but continuing..."
fi

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
    "libsodium"
    "clang"
    "ffmpeg"
)

print_info "Installing required packages: ${REQUIRED_PACKAGES[*]}"
print_info "Note: libsodium and clang are needed for PyNaCl voice support"
print_info "Note: ffmpeg is required for Discord voice channel audio playback"
pkg install -y "${REQUIRED_PACKAGES[@]}"

for package in "${REQUIRED_PACKAGES[@]}"; do
    if command -v "$package" &> /dev/null || pkg list-installed 2>/dev/null | grep -q "^${package}"; then
        print_success "$package is installed"
    else
        print_warning "$package may not be installed correctly"
    fi
done

echo ""

# ============================================================
# STEP 3: SSH Setup Wizard (Interactive)
# ============================================================
print_step "Step 3: Launching SSH setup wizard..."
echo ""
ssh_setup_wizard
echo ""

# ============================================================
# STEP 4: Setup MariaDB
# ============================================================
print_step "Step 4: Setting up MariaDB database..."
echo ""

# Check if MariaDB is initialized
if [ ! -d "$PREFIX/var/lib/mysql/mysql" ]; then
    print_info "Initializing MariaDB..."
    mysql_install_db
    print_success "MariaDB initialized!"
else
    print_success "MariaDB already initialized"
fi

print_info "Ensuring MariaDB server is running..."

start_status=1
_db_start_if_needed
start_rc=$?
case $start_rc in
  0)
    print_success "MariaDB is running and ready"
    ;;
  1)
    print_info "MariaDB process detected; waiting for readiness..."
    ;;
  2)
    print_info "Started MariaDB; waiting for readiness..."
    ;;
esac

# Wait up to 30 seconds for readiness
ready=0
for i in $(seq 1 30); do
    if _db_is_ready; then
        ready=1
        print_success "MariaDB is ready (after ${i}s)"
        break
    fi
    sleep 1
done

if [ $ready -ne 1 ]; then
    if _db_is_running; then
        print_warning "MariaDB process is running but not ready yet."
    else
        print_error "Failed to start MariaDB process."
    fi
    print_info "You can start it manually: mysqld_safe &"
    print_info "Then wait ~10-20 seconds and re-run this script."
    exit 1
fi

echo ""

# ============================================================
# STEP 4: Setup Database & User
# ============================================================
print_step "Step 4: Creating database and user..."
echo ""

# Use mysql client (or mariadb client)
MYSQL_CMD=$(_db_client)

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
# STEP 5: SSH Setup Summary
# ============================================================
print_step "Step 5: SSH setup summary..."
echo ""
if [ "$SSH_READY" = true ]; then
    print_success "SSH to GitHub is configured and working."
else
    print_warning "Proceeding without SSH; HTTPS clone will prompt for a Personal Access Token."
fi
if [ -z "$GITHUB_USER" ]; then
    read -r -p "Your GitHub username (for clone): " GITHUB_USER
fi
echo ""

# ============================================================
# STEP 6: Clone/Update Repository
# ============================================================
print_step "Step 6: Setting up bot repository..."
echo ""

# Check if we're already in the sulfur directory
if [ -f "bot.py" ] && [ -f "web_dashboard.py" ]; then
    REPO_DIR="$(pwd)"
    print_success "Already in repository directory: $REPO_DIR"
    print_info "Skipping clone step"
else
    # Use custom install directory if provided, otherwise default to ~/sulfur
    if [ -n "$CUSTOM_INSTALL_DIR" ]; then
        REPO_DIR="$CUSTOM_INSTALL_DIR"
        print_info "Using custom installation directory: $REPO_DIR"
    else
        REPO_DIR="$HOME/sulfur"
    fi

    # Get GitHub username if not set
    if [ -z "$GITHUB_USER" ]; then
        read -p "Enter your GitHub username (or press Enter for 'mereMint'): " GITHUB_USER
        GITHUB_USER="${GITHUB_USER:-mereMint}"
    fi

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
            if [ "$SSH_READY" = true ]; then
                print_info "Cloning repository via SSH..."
                CLONE_URL="git@github.com:$GITHUB_USER/sulfur.git"
            else
                print_info "Cloning repository via HTTPS (will prompt for Personal Access Token)..."
                CLONE_URL="https://github.com/$GITHUB_USER/sulfur.git"
            fi
            
            if git clone "$CLONE_URL" "$REPO_DIR"; then
                print_success "Repository cloned to $REPO_DIR"
            else
                print_error "Failed to clone repository!"
                if [ "$SSH_READY" = true ]; then
                    print_info "Make sure your SSH key is added to GitHub"
                    print_info "Test with: ssh -T git@github.com"
                else
                    print_info "If prompted, use your GitHub Personal Access Token as password"
                    print_info "Create one at: https://github.com/settings/tokens (classic, repo scope)"
                fi
                exit 1
            fi
        else
            print_info "Using existing directory"
            cd "$REPO_DIR"
        fi
    else
        # Create parent directory if needed
        mkdir -p "$(dirname "$REPO_DIR")"
        
        if [ "$SSH_READY" = true ]; then
            print_info "Cloning repository via SSH..."
            CLONE_URL="git@github.com:$GITHUB_USER/sulfur.git"
        else
            print_info "Cloning repository via HTTPS (will prompt for Personal Access Token)..."
            CLONE_URL="https://github.com/$GITHUB_USER/sulfur.git"
        fi
        
        if git clone "$CLONE_URL" "$REPO_DIR"; then
            print_success "Repository cloned to $REPO_DIR"
        else
            print_error "Failed to clone repository!"
            if [ "$SSH_READY" = true ]; then
                print_info "Make sure your SSH key is added to GitHub"
                print_info "Test with: ssh -T git@github.com"
            else
                print_info "If prompted, use your GitHub Personal Access Token as password"
                print_info "Create one at: https://github.com/settings/tokens (classic, repo scope)"
            fi
            exit 1
        fi
    fi
    
    cd "$REPO_DIR"
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
print_info "PyNaCl will use the system libsodium library we installed earlier"
echo ""

# Set SODIUM_INSTALL=system to use system libsodium instead of building from source
# This prevents PyNaCl build failures on Termux where the bundled libsodium configure fails
export SODIUM_INSTALL=system

if pip install -r requirements.txt; then
    print_success "All Python dependencies installed!"
else
    print_error "Some packages failed to install"
    print_info "Trying again with --no-cache-dir flag..."
    if pip install -r requirements.txt --no-cache-dir; then
        print_success "Dependencies installed successfully on retry!"
    else
        print_error "Installation failed. Continuing with setup..."
        print_warning "Some features may not work without all dependencies"
    fi
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
    
    # Football-Data.org API Key
    echo -e "${YELLOW}Enter your Football-Data.org API Key (or press Enter to skip):${NC}"
    echo -e "${CYAN}  Free tier available at: https://www.football-data.org/client/register${NC}"
    echo -e "${CYAN}  Enables: Champions League, Premier League, La Liga, Serie A, FIFA World Cup${NC}"
    read -p "> " FOOTBALL_DATA_KEY
    
    # Create .env file (without quotes around values to avoid escaping issues)
    cat > .env <<EOF
# Discord Bot Token
DISCORD_BOT_TOKEN=${DISCORD_TOKEN}

# AI API Keys
GEMINI_API_KEY=${GEMINI_KEY}
OPENAI_API_KEY=${OPENAI_KEY}

# Football Data API (for Sport Betting)
# Enables: Champions League, Premier League, La Liga, Serie A, FIFA World Cup
FOOTBALL_DATA_API_KEY=${FOOTBALL_DATA_KEY}

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

cat > start_sulfur.sh <<'SCRIPT_EOF'
#!/data/data/com.termux/files/usr/bin/bash
# Quick start script for Sulfur bot

cd ~/sulfur

# Start MariaDB if not running
if ! pgrep -x mysqld > /dev/null && ! pgrep -x mariadbd > /dev/null; then
    echo "Starting MariaDB..."
    mysqld_safe &
    sleep 5
    echo "MariaDB started"
fi

# Activate virtual environment
source venv/bin/activate

# Run the bot with maintenance script
bash maintain_bot.sh
SCRIPT_EOF

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
echo -e "     • Start manually: ${GREEN}mysqld_safe &${NC}"
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
