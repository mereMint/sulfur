#!/bin/bash
# ==============================================================================
# Sulfur Bot - Secure Database Setup Script
# ==============================================================================
# This script automatically sets up MariaDB/MySQL with strong security:
# - Generates cryptographically secure passwords (48 characters)
# - Creates database and user with proper permissions
# - Stores credentials securely in config/database.json (0600 permissions)
# - Prevents race conditions with file locking
# - Idempotent: can be run multiple times safely
# ==============================================================================

set -e  # Exit on any error
set -u  # Exit on undefined variable

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_DIR="$PROJECT_ROOT/config"
CONFIG_FILE="$CONFIG_DIR/database.json"
LOCK_FILE="/tmp/sulfur_db_setup.lock"
PID_FILE="/tmp/sulfur_mariadb.pid"

# Database defaults (can be overridden by environment)
DB_NAME="${DB_NAME:-sulfur_bot}"
DB_USER="${DB_USER:-sulfur_bot_user}"
DB_HOST="${DB_HOST:-localhost}"

# Detect environment
if [ -n "${TERMUX_VERSION:-}" ] || [ -d "/data/data/com.termux" ]; then
    IS_TERMUX=true
    PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
    MYSQL_DATADIR="$PREFIX/var/lib/mysql"
    MYSQL_SOCKET="$PREFIX/var/run/mysqld/mysqld.sock"
else
    IS_TERMUX=false
    MYSQL_DATADIR="/var/lib/mysql"
    MYSQL_SOCKET="/var/run/mysqld/mysqld.sock"
fi

# ==============================================================================
# Utility Functions
# ==============================================================================

log_info() {
    echo -e "${NC}[INFO] $1${NC}"
}

log_success() {
    echo -e "${GREEN}[✓] $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}[!] $1${NC}"
}

log_error() {
    echo -e "${RED}[✗] $1${NC}"
}

log_step() {
    echo -e "${CYAN}[→] $1${NC}"
}

# ==============================================================================
# Locking Mechanism
# ==============================================================================

acquire_lock() {
    # Simple PID-based locking (more portable than flock with file descriptors)
    if [ -f "$LOCK_FILE" ]; then
        local lock_pid
        lock_pid=$(cat "$LOCK_FILE" 2>/dev/null || echo "")

        if [ -n "$lock_pid" ] && kill -0 "$lock_pid" 2>/dev/null; then
            log_error "Another instance of this script is already running (PID: $lock_pid)"
            log_info "If you're sure no other instance is running, remove: $LOCK_FILE"
            exit 1
        else
            # Stale lock file, remove it
            rm -f "$LOCK_FILE" 2>/dev/null || true
        fi
    fi

    # Create lock file with our PID
    echo $$ > "$LOCK_FILE" 2>/dev/null || {
        log_error "Cannot create lock file: $LOCK_FILE"
        log_info "Check permissions on /tmp directory"
        exit 1
    }

    log_success "Acquired setup lock"
}

release_lock() {
    # Only remove lock file if it contains our PID
    if [ -f "$LOCK_FILE" ]; then
        local lock_pid
        lock_pid=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
        if [ "$lock_pid" = "$$" ]; then
            rm -f "$LOCK_FILE" 2>/dev/null || true
        fi
    fi
}

# Trap to ensure lock is released on exit
trap release_lock EXIT INT TERM

# ==============================================================================
# Password Generation
# ==============================================================================

generate_secure_password() {
    # Generate 48-character cryptographically secure password
    # Use openssl if available, otherwise /dev/urandom
    local password=""
    
    if command -v openssl >/dev/null 2>&1; then
        # Generate 48 bytes and base64 encode (results in 64 chars, we'll use 48)
        password=$(openssl rand -base64 48 | tr -d '\n' | cut -c1-48)
    elif [ -f /dev/urandom ]; then
        # Fallback to /dev/urandom
        password=$(tr -dc 'A-Za-z0-9!@#$%^&*()_+=-' < /dev/urandom | head -c 48)
    else
        log_error "Cannot generate secure password: openssl and /dev/urandom unavailable"
        exit 1
    fi
    
    # Ensure password is not empty
    if [ -z "$password" ]; then
        log_error "Failed to generate password"
        exit 1
    fi
    
    echo "$password"
}

# ==============================================================================
# Process Checking
# ==============================================================================

is_mariadb_running() {
    # Check if MariaDB/MySQL is running using multiple methods
    
    # Method 1: Check PID file
    if [ -f "$PID_FILE" ]; then
        local pid
        pid=$(cat "$PID_FILE" 2>/dev/null || echo "")
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
    fi
    
    # Method 2: Check by process name
    if pgrep -x "mariadbd" >/dev/null 2>&1 || pgrep -x "mysqld" >/dev/null 2>&1; then
        return 0
    fi
    
    # Method 3: Check if port 3306 is listening
    if command -v nc >/dev/null 2>&1; then
        if nc -z localhost 3306 2>/dev/null; then
            return 0
        fi
    elif command -v ss >/dev/null 2>&1; then
        if ss -tlnp 2>/dev/null | grep -q ":3306 "; then
            return 0
        fi
    fi
    
    return 1
}

can_connect_to_mysql() {
    # Try to connect to MySQL/MariaDB server
    local mysql_cmd
    
    if command -v mariadb >/dev/null 2>&1; then
        mysql_cmd="mariadb"
    elif command -v mysql >/dev/null 2>&1; then
        mysql_cmd="mysql"
    else
        return 1
    fi
    
    # Try connecting as root without password (common on fresh installs)
    if $mysql_cmd -u root -e "SELECT 1;" >/dev/null 2>&1; then
        return 0
    fi
    
    return 1
}

# ==============================================================================
# Database Server Management
# ==============================================================================

initialize_mariadb_datadir() {
    if [ "$IS_TERMUX" != true ]; then
        return 0
    fi
    
    log_step "Checking MariaDB data directory..."
    
    if [ -d "$MYSQL_DATADIR/mysql" ]; then
        log_success "MariaDB data directory already initialized"
        return 0
    fi
    
    log_step "Initializing MariaDB data directory (first-time setup)..."
    
    if command -v mariadb-install-db >/dev/null 2>&1; then
        mariadb-install-db --datadir="$MYSQL_DATADIR" 2>&1 | grep -v "^$"
    elif command -v mysql_install_db >/dev/null 2>&1; then
        mysql_install_db --datadir="$MYSQL_DATADIR" 2>&1 | grep -v "^$"
    else
        log_error "Cannot find mariadb-install-db or mysql_install_db"
        return 1
    fi
    
    log_success "MariaDB data directory initialized"
    return 0
}

stop_mariadb_gracefully() {
    log_step "Stopping existing MariaDB instance gracefully..."
    
    local pid=""
    if [ -f "$PID_FILE" ]; then
        pid=$(cat "$PID_FILE" 2>/dev/null || echo "")
    fi
    
    if [ -z "$pid" ]; then
        # Try to find PID by process name
        pid=$(pgrep -x "mariadbd" 2>/dev/null || pgrep -x "mysqld" 2>/dev/null || echo "")
    fi
    
    if [ -n "$pid" ]; then
        log_info "Sending TERM signal to PID $pid..."
        kill -TERM "$pid" 2>/dev/null || true
        
        # Wait up to 10 seconds for graceful shutdown
        local count=0
        while [ $count -lt 10 ]; do
            if ! kill -0 "$pid" 2>/dev/null; then
                log_success "MariaDB stopped gracefully"
                return 0
            fi
            sleep 1
            count=$((count + 1))
        done
        
        # Force kill if still running
        log_warning "Forcing shutdown..."
        kill -9 "$pid" 2>/dev/null || true
        sleep 2
    fi
    
    return 0
}

start_mariadb() {
    log_step "Starting MariaDB server..."
    
    # Double-check not running (prevent race condition)
    if is_mariadb_running; then
        log_success "MariaDB is already running"
        return 0
    fi
    
    if [ "$IS_TERMUX" = true ]; then
        # Termux: use mariadbd-safe or mysqld_safe
        if command -v mariadbd-safe >/dev/null 2>&1; then
            nohup mariadbd-safe --datadir="$MYSQL_DATADIR" \
                                --pid-file="$PID_FILE" \
                                --socket="$MYSQL_SOCKET" \
                                >/dev/null 2>&1 &
        elif command -v mysqld_safe >/dev/null 2>&1; then
            nohup mysqld_safe --datadir="$MYSQL_DATADIR" \
                              --pid-file="$PID_FILE" \
                              --socket="$MYSQL_SOCKET" \
                              >/dev/null 2>&1 &
        else
            log_error "Cannot find mariadbd-safe or mysqld_safe"
            return 1
        fi
    else
        # Linux: try systemctl, then service
        if command -v systemctl >/dev/null 2>&1; then
            if systemctl list-unit-files mariadb.service >/dev/null 2>&1; then
                sudo systemctl start mariadb 2>/dev/null || true
            elif systemctl list-unit-files mysql.service >/dev/null 2>&1; then
                sudo systemctl start mysql 2>/dev/null || true
            fi
        elif command -v service >/dev/null 2>&1; then
            sudo service mariadb start 2>/dev/null || sudo service mysql start 2>/dev/null || true
        fi
    fi
    
    # Wait for MariaDB to become ready (up to 30 seconds)
    log_step "Waiting for MariaDB to become ready (up to 30 seconds)..."
    local count=0
    while [ $count -lt 30 ]; do
        if can_connect_to_mysql; then
            log_success "MariaDB is ready (took ${count}s)"
            return 0
        fi
        sleep 1
        count=$((count + 1))
        
        # Show progress every 5 seconds
        if [ $((count % 5)) -eq 0 ]; then
            log_info "Still waiting... (${count}/30s)"
        fi
    done
    
    log_error "MariaDB did not become ready within 30 seconds"
    return 1
}

# ==============================================================================
# Security Hardening
# ==============================================================================

secure_mysql_installation() {
    log_step "Applying security hardening..."
    
    local mysql_cmd
    if command -v mariadb >/dev/null 2>&1; then
        mysql_cmd="mariadb"
    else
        mysql_cmd="mysql"
    fi
    
    # Remove anonymous users
    log_info "Removing anonymous users..."
    $mysql_cmd -u root <<EOF 2>/dev/null || true
DELETE FROM mysql.user WHERE User='';
EOF
    
    # Remove test database
    log_info "Removing test database..."
    $mysql_cmd -u root <<EOF 2>/dev/null || true
DROP DATABASE IF EXISTS test;
DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';
EOF
    
    # Disable remote root login
    log_info "Disabling remote root login..."
    $mysql_cmd -u root <<EOF 2>/dev/null || true
DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');
EOF
    
    # Flush privileges
    $mysql_cmd -u root -e "FLUSH PRIVILEGES;" 2>/dev/null || true
    
    log_success "Security hardening applied"
}

# ==============================================================================
# Database and User Creation
# ==============================================================================

create_database_and_user() {
    local db_password="$1"
    local root_password="${2:-}"
    
    log_step "Creating database and user..."
    
    local mysql_cmd
    if command -v mariadb >/dev/null 2>&1; then
        mysql_cmd="mariadb"
    else
        mysql_cmd="mysql"
    fi
    
    # Prepare root connection arguments
    local root_args="-u root"
    if [ -n "$root_password" ]; then
        root_args="$root_args -p$root_password"
    fi
    
    # Create database
    log_info "Creating database '$DB_NAME'..."
    $mysql_cmd $root_args <<EOF
CREATE DATABASE IF NOT EXISTS \`$DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EOF
    
    # Drop existing user if exists
    log_info "Removing old user '$DB_USER' if exists..."
    $mysql_cmd $root_args <<EOF 2>/dev/null || true
DROP USER IF EXISTS '$DB_USER'@'$DB_HOST';
EOF
    
    # Create new user with password
    log_info "Creating user '$DB_USER' with secure password..."
    $mysql_cmd $root_args <<EOF
CREATE USER '$DB_USER'@'$DB_HOST' IDENTIFIED BY '$db_password';
GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'$DB_HOST';
FLUSH PRIVILEGES;
EOF
    
    log_success "Database and user created successfully"
}

# ==============================================================================
# Configuration File Management
# ==============================================================================

save_config() {
    local db_password="$1"
    local root_password="${2:-}"
    
    log_step "Saving configuration to $CONFIG_FILE..."
    
    # Create config directory if it doesn't exist
    mkdir -p "$CONFIG_DIR"
    
    # Create JSON configuration
    cat > "$CONFIG_FILE" <<EOF
{
  "host": "$DB_HOST",
  "user": "$DB_USER",
  "password": "$db_password",
  "database": "$DB_NAME",
  "socket": "$MYSQL_SOCKET",
  "charset": "utf8mb4"
}
EOF
    
    # Set secure permissions (owner read/write only)
    chmod 600 "$CONFIG_FILE"
    
    # Verify permissions
    local perms
    perms=$(stat -c '%a' "$CONFIG_FILE" 2>/dev/null || stat -f '%A' "$CONFIG_FILE" 2>/dev/null)
    if [ "$perms" != "600" ]; then
        log_warning "Could not set permissions to 600, got: $perms"
    else
        log_success "Configuration saved with secure permissions (600)"
    fi
}

# ==============================================================================
# Verification
# ==============================================================================

verify_setup() {
    log_step "Verifying database setup..."
    
    local mysql_cmd
    if command -v mariadb >/dev/null 2>&1; then
        mysql_cmd="mariadb"
    else
        mysql_cmd="mysql"
    fi
    
    # Load config
    if [ ! -f "$CONFIG_FILE" ]; then
        log_error "Config file not found: $CONFIG_FILE"
        return 1
    fi
    
    # Extract password from JSON (simple grep approach)
    local test_password
    test_password=$(grep '"password"' "$CONFIG_FILE" | cut -d'"' -f4)
    
    # Try to connect as bot user
    if $mysql_cmd -u "$DB_USER" -p"$test_password" -h "$DB_HOST" -e "USE \`$DB_NAME\`; SELECT 1;" >/dev/null 2>&1; then
        log_success "Database connection verified"
        return 0
    else
        log_error "Failed to connect with bot user credentials"
        return 1
    fi
}

# ==============================================================================
# Rollback on Failure
# ==============================================================================

rollback() {
    log_warning "Rolling back changes..."
    
    if [ -f "$CONFIG_FILE" ]; then
        log_info "Removing config file..."
        rm -f "$CONFIG_FILE"
    fi
    
    # Note: We don't drop the database or user automatically
    # as they might have been created in a previous run
    log_warning "Database and user were NOT removed (manual cleanup required if desired)"
}

# ==============================================================================
# Main Execution
# ==============================================================================

main() {
    echo "============================================================================"
    echo "  Sulfur Bot - Secure Database Setup"
    echo "============================================================================"
    echo ""
    
    # Acquire lock to prevent parallel execution
    acquire_lock
    
    # Check if already configured
    if [ -f "$CONFIG_FILE" ]; then
        log_info "Configuration file already exists: $CONFIG_FILE"
        
        # Verify it still works
        if verify_setup; then
            log_success "Database is already configured and working!"
            echo ""
            echo "To reconfigure, delete $CONFIG_FILE and run this script again."
            exit 0
        else
            log_warning "Existing configuration is not working, reconfiguring..."
            rm -f "$CONFIG_FILE"
        fi
    fi
    
    # Step 1: Initialize MariaDB data directory (Termux only)
    if ! initialize_mariadb_datadir; then
        log_error "Failed to initialize MariaDB data directory"
        exit 1
    fi
    
    # Step 2: Ensure MariaDB is running
    if ! is_mariadb_running; then
        if ! start_mariadb; then
            log_error "Failed to start MariaDB"
            echo ""
            echo "Please start MariaDB manually and run this script again:"
            if [ "$IS_TERMUX" = true ]; then
                echo "  mariadbd-safe --datadir=$MYSQL_DATADIR &"
            else
                echo "  sudo systemctl start mariadb  # or mysql"
            fi
            exit 1
        fi
    else
        log_success "MariaDB is already running"
    fi
    
    # Step 3: Wait a bit more to ensure server is ready
    sleep 2
    
    # Step 4: Apply security hardening
    secure_mysql_installation
    
    # Step 5: Generate secure password
    log_step "Generating secure password..."
    DB_PASSWORD=$(generate_secure_password)
    log_success "Secure password generated (48 characters)"
    
    # Step 6: Create database and user
    if ! create_database_and_user "$DB_PASSWORD"; then
        log_error "Failed to create database and user"
        rollback
        exit 1
    fi
    
    # Step 7: Save configuration
    if ! save_config "$DB_PASSWORD"; then
        log_error "Failed to save configuration"
        rollback
        exit 1
    fi
    
    # Step 8: Verify setup
    if ! verify_setup; then
        log_error "Setup verification failed"
        rollback
        exit 1
    fi
    
    # Success!
    echo ""
    echo "============================================================================"
    echo "  ✓ Database Setup Complete!"
    echo "============================================================================"
    echo ""
    echo "Configuration:"
    echo "  Database: $DB_NAME"
    echo "  User:     $DB_USER"
    echo "  Host:     $DB_HOST"
    echo "  Password: (stored securely in $CONFIG_FILE)"
    echo ""
    echo "Next steps:"
    echo "  1. Run migrations: python apply_migration.py"
    echo "  2. Start bot:      python bot.py"
    echo ""
}

# Run main function
main
