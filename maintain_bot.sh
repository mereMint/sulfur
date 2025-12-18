#!/bin/bash
# ==============================================================================
# Sulfur Bot - Enhanced Maintenance Script for Termux/Linux
# ==============================================================================
# Features:
# - Auto-start bot and web dashboard
# - Check for updates every minute
# - Auto-backup database every 30 minutes
# - Auto-restart on updates
# - Self-update capability
# - Graceful shutdown with Ctrl+C
#
# PUBLIC REPO MODE (Default):
# - SKIP_COMMIT=true (no auto-commits)
# - Local changes are DISCARDED on updates
# - Always uses remote files (git reset --hard)
# - No merge conflicts
#
# To enable legacy commit mode: run with --enable-commit flag
# ==============================================================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0;m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

LOG_DIR="$SCRIPT_DIR/logs"
CONFIG_DIR="$SCRIPT_DIR/config"
BACKUP_DIR="$SCRIPT_DIR/backups"
STATUS_FILE="$CONFIG_DIR/bot_status.json"

# Create directories
mkdir -p "$LOG_DIR" "$CONFIG_DIR" "$BACKUP_DIR"

# Log files
LOG_TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
MAIN_LOG="$LOG_DIR/maintenance_${LOG_TIMESTAMP}.log"
BOT_LOG="$LOG_DIR/bot_${LOG_TIMESTAMP}.log"
WEB_LOG="$LOG_DIR/web_${LOG_TIMESTAMP}.log"

# PID files
BOT_PID_FILE="$CONFIG_DIR/bot.pid"
WEB_PID_FILE="$CONFIG_DIR/web.pid"

# Intervals (in seconds)
CHECK_INTERVAL=60      # Check for updates every 60 seconds
COMMIT_INTERVAL=300    # Auto-commit every 5 minutes
BACKUP_INTERVAL=1800   # Backup every 30 minutes

# Flags
SKIP_BACKUP=${SKIP_BACKUP:-false}
SKIP_COMMIT=${SKIP_COMMIT:-true}  # Default to true - bot should only pull, not commit/push

# CLI flags
for arg in "$@"; do
    case "$arg" in
        --no-backup|-n)
            SKIP_BACKUP=true
            shift
            ;;
        --enable-commit)
            SKIP_COMMIT=false
            shift
            ;;
    esac
done

# Counters
CHECK_COUNTER=0
CRASH_COUNT=0
QUICK_CRASH_SECONDS=10

# Update loop prevention
LAST_PULLED_COMMIT=""
UPDATE_LOOP_COUNT=0
MAX_UPDATE_LOOP_COUNT=3  # Prevent more than 3 updates in quick succession
UPDATE_LOOP_RESET_SECONDS=300  # Reset loop counter after 5 minutes
LAST_UPDATE_TIME=0
CRASH_THRESHOLD=5

# Web dashboard restart tracking
WEB_RESTART_COUNT=0
WEB_RESTART_THRESHOLD=3
WEB_RESTART_COOLDOWN=30  # seconds between restart attempts
LAST_WEB_RESTART=0

# Detect environment
if [ -n "$TERMUX_VERSION" ]; then
    IS_TERMUX=true
    PYTHON_CMD="python"
else
    IS_TERMUX=false
    PYTHON_CMD="${PYTHON_CMD:-python3}"
fi

# Safe function to load database credentials from .env file
# Only loads specific known-safe variables to prevent injection
load_db_credentials() {
    if [ ! -f ".env" ]; then
        return 1
    fi

    # Read each line and only export known database variables
    # This is safer than using export $(grep ... | xargs)
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        [[ "$key" =~ ^[[:space:]]*# ]] && continue
        [[ -z "$key" ]] && continue

        # Remove leading/trailing whitespace from key
        key=$(echo "$key" | tr -d '[:space:]')

        # Only process known database variables
        case "$key" in
            DB_HOST|DB_USER|DB_PASS|DB_NAME)
                # Remove surrounding quotes from value
                value="${value#\"}"
                value="${value%\"}"
                value="${value#\'}"
                value="${value%\'}"
                # Remove trailing whitespace
                value="${value%"${value##*[![:space:]]}"}"
                # Export the variable
                export "$key=$value"
                ;;
        esac
    done < ".env"
    return 0
}

# Load database credentials from .env if available
load_db_credentials

# Database credentials (use values from .env or defaults)
DB_USER="${DB_USER:-sulfur_bot_user}"
DB_NAME="${DB_NAME:-sulfur_bot}"
DB_PASS="${DB_PASS:-}"
DB_HOST="${DB_HOST:-localhost}"

# Termux system dependencies for PyNaCl (voice support)
TERMUX_SYSTEM_DEPS=("libsodium" "clang")

# ==============================================================================
# Logging Functions
# ==============================================================================

log_message() {
    local color=$1
    local prefix=$2
    local message=$3
    local timestamp
    timestamp=$(date +"%Y-%m-%d %H:%M:%S")

    echo -e "${color}[${timestamp}] ${prefix}${message}${NC}" | tee -a "$MAIN_LOG"
}

log_info() { log_message "$NC" "" "$1"; }
log_success() { log_message "$GREEN" "[✓] " "$1"; }
log_warning() { log_message "$YELLOW" "[!] " "$1"; }
log_error() { log_message "$RED" "[✗] " "$1"; }
log_git() { log_message "$CYAN" "[GIT] " "$1"; }
log_db() { log_message "$CYAN" "[DB] " "$1"; }
log_bot() { log_message "$GREEN" "[BOT] " "$1"; }
log_web() { log_message "$CYAN" "[WEB] " "$1"; }
log_update() { log_message "$YELLOW" "[UPDATE] " "$1"; }
log_java() { log_message "$CYAN" "[JAVA] " "$1"; }

# ==============================================================================
# Java Installation Functions
# ==============================================================================

check_and_install_java_21() {
    log_java "Checking Java 21 for Minecraft support..."
    
    # Check if Java is already installed with version 21+
    if command -v java &> /dev/null; then
        local java_version
        java_version=$(java -version 2>&1 | grep -oP 'version "?\K\d+' | head -1 || echo "0")
        if [ "$java_version" -ge 21 ] 2>/dev/null; then
            log_success "Java $java_version is installed"
            return 0
        else
            log_warning "Java $java_version found, upgrading to Java 21..."
        fi
    else
        log_java "Java not found, installing Java 21..."
    fi
    
    # Install Java 21 based on platform
    if [ "$IS_TERMUX" = true ]; then
        pkg install -y openjdk-21 >>"$MAIN_LOG" 2>&1 && {
            log_success "Java 21 installed via pkg"
            return 0
        }
    elif command -v apt-get &> /dev/null; then
        sudo apt-get update -qq >>"$MAIN_LOG" 2>&1
        sudo apt-get install -y openjdk-21-jre-headless >>"$MAIN_LOG" 2>&1 || \
        sudo apt-get install -y openjdk-21-jdk >>"$MAIN_LOG" 2>&1 && {
            log_success "Java 21 installed via apt"
            return 0
        }
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y java-21-openjdk-headless >>"$MAIN_LOG" 2>&1 && {
            log_success "Java 21 installed via dnf"
            return 0
        }
    elif command -v pacman &> /dev/null; then
        sudo pacman -S --noconfirm jre21-openjdk-headless >>"$MAIN_LOG" 2>&1 && {
            log_success "Java 21 installed via pacman"
            return 0
        }
    elif command -v brew &> /dev/null; then
        brew install openjdk@21 >>"$MAIN_LOG" 2>&1 && {
            log_success "Java 21 installed via Homebrew"
            return 0
        }
    fi
    
    log_warning "Could not auto-install Java 21"
    return 1
}

# ==============================================================================
# Status Functions
# ==============================================================================

update_status() {
    local status=$1
    local pid=${2:-0}

    cat > "$STATUS_FILE" <<EOF
{
  "status": "$status",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "pid": $pid
}
EOF
}

# ==============================================================================
# Cleanup Functions
# ==============================================================================

cleanup() {
    log_warning "Cleaning up..."

    # Stop bot gracefully
    if [ -f "$BOT_PID_FILE" ]; then
        BOT_PID=$(cat "$BOT_PID_FILE")
        if kill -0 "$BOT_PID" 2>/dev/null; then
            log_bot "Sending graceful shutdown signal to bot (PID: $BOT_PID)..."
            # Send SIGTERM for graceful shutdown
            kill -TERM "$BOT_PID" 2>/dev/null

            # Wait up to 5 seconds for graceful shutdown
            for i in {1..5}; do
                if ! kill -0 "$BOT_PID" 2>/dev/null; then
                    log_success "Bot shut down gracefully"
                    break
                fi
                sleep 1
            done

            # Force kill if still running
            if kill -0 "$BOT_PID" 2>/dev/null; then
                log_warning "Force stopping bot..."
                kill -9 "$BOT_PID" 2>/dev/null
            fi
        fi
        rm -f "$BOT_PID_FILE"
    fi

    # Also search for any bot.py processes that might have escaped
    if command -v pgrep >/dev/null 2>&1; then
        local bot_pids
        bot_pids=$(pgrep -f "python.*bot\.py" || true)
        if [ -n "$bot_pids" ]; then
            log_warning "Found orphaned bot processes: $bot_pids"
            for pid in $bot_pids; do
                log_info "  Killing bot PID: $pid"
                kill -9 "$pid" 2>/dev/null || true
            done
        fi
    fi

    # Stop web dashboard
    if [ -f "$WEB_PID_FILE" ]; then
        local web_pid
        web_pid=$(cat "$WEB_PID_FILE" 2>/dev/null)
        if [ -n "$web_pid" ] && kill -0 "$web_pid" 2>/dev/null; then
            log_web "Stopping web dashboard (PID: $web_pid)..."
            kill -TERM "$web_pid" 2>/dev/null
            sleep 2
            # Force kill if still running
            if kill -0 "$web_pid" 2>/dev/null; then
                kill -9 "$web_pid" 2>/dev/null
            fi
        fi
        rm -f "$WEB_PID_FILE"
    fi

    # Also search for any web_dashboard.py processes that might have escaped
    if command -v pgrep >/dev/null 2>&1; then
        local web_pids
        web_pids=$(pgrep -f "python.*web_dashboard\.py" || true)
        if [ -n "$web_pids" ]; then
            log_warning "Found orphaned web dashboard processes: $web_pids"
            for pid in $web_pids; do
                log_info "  Killing web dashboard PID: $pid"
                kill -9 "$pid" 2>/dev/null || true
            done
        fi
    fi

    # Final backup and commit
    if [ "$SKIP_BACKUP" != true ]; then
        backup_database
    else
        log_db "Skipping final backup due to SKIP_BACKUP=true"
    fi
    git_commit "chore: Auto-commit on shutdown"

    update_status "Shutdown"
    log_success "Cleanup complete"
    exit 0
}

# Set trap for Ctrl+C
trap cleanup SIGINT SIGTERM

# Kill orphaned python processes that originated in this project dir
cleanup_orphans() {
    log_warning "Searching for orphaned Python processes..."

    # Wait for any pending PID file writes to complete
    sleep 0.5

    # Get current bot and web PIDs to exclude them
    local exclude_pids=""
    if [ -f "$BOT_PID_FILE" ]; then
        exclude_pids="$(cat "$BOT_PID_FILE" 2>/dev/null)"
    fi
    if [ -f "$WEB_PID_FILE" ]; then
        local web_pid=$(cat "$WEB_PID_FILE" 2>/dev/null)
        if [ -n "$web_pid" ]; then
            exclude_pids="$exclude_pids $web_pid"
        fi
    fi

    if command -v pgrep >/dev/null 2>&1; then
        # Match processes with this script directory in the command line
        local pids
        pids=$(pgrep -f "python.*${SCRIPT_DIR}" || true)
        if [ -n "$pids" ]; then
            # Filter out current bot and web dashboard PIDs
            local pids_to_kill=""
            for pid in $pids; do
                local should_kill=true
                for exclude_pid in $exclude_pids; do
                    if [ "$pid" = "$exclude_pid" ]; then
                        should_kill=false
                        break
                    fi
                done
                if [ "$should_kill" = true ]; then
                    pids_to_kill="$pids_to_kill $pid"
                fi
            done

            if [ -n "$pids_to_kill" ]; then
                log_warning "Killing orphaned PIDs:$pids_to_kill"
                # shellcheck disable=SC2086
                kill -9 $pids_to_kill 2>/dev/null || true
            else
                log_info "No orphaned Python processes found (excluding current bot/web)"
            fi
        else
            log_info "No orphaned Python processes found"
        fi
    else
        # Fallback using ps/grep/awk
        local pids
        pids=$(ps aux | grep -E "python.*${SCRIPT_DIR}" | grep -v grep | awk '{print $2}')
        if [ -n "$pids" ]; then
            # Filter out current bot and web dashboard PIDs
            local pids_to_kill=""
            for pid in $pids; do
                local should_kill=true
                for exclude_pid in $exclude_pids; do
                    if [ "$pid" = "$exclude_pid" ]; then
                        should_kill=false
                        break
                    fi
                done
                if [ "$should_kill" = true ]; then
                    pids_to_kill="$pids_to_kill $pid"
                fi
            done

            if [ -n "$pids_to_kill" ]; then
                log_warning "Killing orphaned PIDs:$pids_to_kill"
                # shellcheck disable=SC2086
                kill -9 $pids_to_kill 2>/dev/null || true
            else
                log_info "No orphaned Python processes found (excluding current bot/web)"
            fi
        else
            log_info "No orphaned Python processes found"
        fi
    fi
}

# ==============================================================================
# Database Functions
# ==============================================================================

# Database lock file for preventing race conditions
# Use project directory for lock file to avoid /tmp permission issues (especially on Termux)
DB_LOCK_FILE="$CONFIG_DIR/.db_start.lock"

# Acquire database startup lock
acquire_db_lock() {
    # Clean up stale lock file if it exists and is older than 60 seconds
    # This handles cases where the lock file was left behind by a crashed process
    if [ -f "$DB_LOCK_FILE" ]; then
        local current_time
        current_time=$(date +%s)
        local lock_mtime
        local lock_age=0

        if [ "$(uname)" = "Darwin" ]; then
            # macOS
            lock_mtime=$(stat -f %m "$DB_LOCK_FILE" 2>/dev/null)
        else
            # Linux/Termux
            lock_mtime=$(stat -c %Y "$DB_LOCK_FILE" 2>/dev/null)
        fi

        # Only calculate age if we successfully got the mtime
        if [ -n "$lock_mtime" ] && [ "$lock_mtime" -gt 0 ] 2>/dev/null; then
            lock_age=$((current_time - lock_mtime))
        fi

        if [ "$lock_age" -gt 60 ]; then
            log_warning "Removing stale database lock file (age: ${lock_age}s)"
            rm -f "$DB_LOCK_FILE" 2>/dev/null || true
        fi
    fi

    # Try to open file descriptor for lock file
    # Redirect stderr to suppress error messages on failure
    if ! exec 201>"$DB_LOCK_FILE" 2>/dev/null; then
        log_warning "Cannot create lock file: $DB_LOCK_FILE"
        # If we can't create the lock file, try to proceed anyway
        # This is safer than blocking indefinitely
        return 0
    fi

    if ! flock -n 201 2>/dev/null; then
        return 1
    fi
    return 0
}

# Release database startup lock
release_db_lock() {
    flock -u 201 2>/dev/null || true
    exec 201>&- 2>/dev/null || true  # Close the file descriptor
    rm -f "$DB_LOCK_FILE" 2>/dev/null || true
}

# Check if the database process (mysqld/mariadbd) is running
is_database_process_running() {
    # Check by exact process name first
    if pgrep -x mysqld > /dev/null 2>&1 || pgrep -x mariadbd > /dev/null 2>&1; then
        return 0
    fi
    # Also check by partial match (catches mariadbd, mysqld variants)
    if pgrep -f "mariadbd" > /dev/null 2>&1 || pgrep -f "mysqld" > /dev/null 2>&1; then
        return 0
    fi
    # Check if port 3306 is in use (most reliable method)
    if command -v ss > /dev/null 2>&1; then
        if ss -tlnp 2>/dev/null | grep -q ":3306 "; then
            return 0
        fi
    elif command -v netstat > /dev/null 2>&1; then
        if netstat -tlnp 2>/dev/null | grep -q ":3306 "; then
            return 0
        fi
    fi
    return 1
}

# Get the MySQL/MariaDB client command
get_mysql_client() {
    if command -v mariadb &> /dev/null; then
        echo "mariadb"
    elif command -v mysql &> /dev/null; then
        echo "mysql"
    else
        echo ""
    fi
}

check_database_server() {
    log_db "Checking database server status..."

    # Try to connect to MySQL/MariaDB to verify it's running
    local mysql_cmd
    mysql_cmd=$(get_mysql_client)
    if [ -z "$mysql_cmd" ]; then
        log_error "MySQL/MariaDB client not found"
        return 1
    fi

    # First, check if the database process is running at all
    if ! is_database_process_running; then
        log_warning "Database server process is not running"
        return 1
    fi

    # Test connection - try multiple methods in order of preference
    # 1. Try with bot user and password (if password is set)
    if [ -n "$DB_PASS" ] && [ "$(echo "$DB_PASS" | tr -d ' ')" != "" ]; then
        if $mysql_cmd -u "$DB_USER" -p"$DB_PASS" -e "SELECT 1;" &>/dev/null; then
            log_success "Database server is running and accessible (authenticated)"
            return 0
        fi
    fi

    # 2. Try with bot user without password (common in Termux setup)
    if $mysql_cmd -u "$DB_USER" -e "SELECT 1;" &>/dev/null; then
        log_success "Database server is running and accessible (bot user, no password)"
        return 0
    fi

    # 3. Try with root user without password (Termux default)
    if [ "$IS_TERMUX" = true ]; then
        if $mysql_cmd -u root -e "SELECT 1;" &>/dev/null; then
            log_success "Database server is running and accessible (root, no password)"
            return 0
        fi
    fi

    # 4. If process is running but we can't connect, it might still be initializing
    if is_database_process_running; then
        log_warning "Database process is running but not accepting connections yet"
        return 1
    fi

    log_warning "Database server is not accessible"
    return 1
}

start_database_server() {
    log_db "Attempting to start database server..."

    # Acquire lock to prevent race conditions
    if ! acquire_db_lock; then
        log_warning "Another process is already starting the database, waiting..."
        local wait_count=0
        while [ $wait_count -lt 10 ] && ! acquire_db_lock; do
            sleep 1
            wait_count=$((wait_count + 1))
        done

        if ! acquire_db_lock; then
            log_warning "Could not acquire database startup lock after 10s"
            # Check if database is now running (the other process may have started it)
            if is_database_process_running; then
                log_success "Database is now running (started by another process)"
                return 0
            fi
            return 1
        fi
    fi

    # Double-check database is not already running (race condition prevention)
    if is_database_process_running; then
        log_success "Database process is already running"
        release_db_lock
        return 0
    fi

    # Check which init system is in use
    if [ "$IS_TERMUX" != true ] && command -v systemctl &> /dev/null; then
        # systemd (non-Termux Linux)
        if systemctl is-active --quiet mysql; then
            log_success "MySQL service is already running"
            release_db_lock
            return 0
        elif systemctl is-active --quiet mariadb; then
            log_success "MariaDB service is already running"
            release_db_lock
            return 0
        fi

        # Try to start MySQL
        if systemctl list-unit-files mysql.service &>/dev/null; then
            log_db "Starting MySQL via systemctl..."
            if sudo systemctl start mysql 2>>"$MAIN_LOG"; then
                sleep 2
                if systemctl is-active --quiet mysql; then
                    log_success "MySQL service started successfully"
                    release_db_lock
                    return 0
                fi
            fi
        fi

        # Try to start MariaDB
        if systemctl list-unit-files mariadb.service &>/dev/null; then
            log_db "Starting MariaDB via systemctl..."
            if sudo systemctl start mariadb 2>>"$MAIN_LOG"; then
                sleep 2
                if systemctl is-active --quiet mariadb; then
                    log_success "MariaDB service started successfully"
                    release_db_lock
                    return 0
                fi
            fi
        fi
    elif [ "$IS_TERMUX" != true ] && command -v service &> /dev/null; then
        # SysV init (non-Termux Linux)
        log_db "Starting MySQL via service..."
        if sudo service mysql start 2>>"$MAIN_LOG"; then
            sleep 2
            log_success "MySQL service started"
            release_db_lock
            return 0
        fi
    fi

    # Termux-specific method (or fallback for other environments)
    if [ "$IS_TERMUX" = true ]; then
        log_db "Attempting Termux-specific database start..."

        # Ensure PREFIX is set (Termux environment variable)
        if [ -z "$PREFIX" ]; then
            log_warning "PREFIX not set, trying default Termux path..."
            PREFIX="/data/data/com.termux/files/usr"
        fi

        # Check if datadir exists and is initialized
        local datadir="$PREFIX/var/lib/mysql"
        local socket_file="$datadir/mysql.sock"
        local aria_log="$datadir/aria_log_control"
        log_info "Using datadir: $datadir"

        # Create datadir if it doesn't exist
        if [ ! -d "$datadir" ]; then
            log_info "Creating datadir: $datadir"
            mkdir -p "$datadir" 2>>"$MAIN_LOG" || {
                log_error "Failed to create datadir: $datadir"
                release_db_lock
                return 1
            }
        fi

        # TERMUX FIX: Check if port 3306 is in use but database check failed
        # This catches zombie processes that hold the port
        local port_in_use=false
        if command -v ss > /dev/null 2>&1; then
            if ss -tlnp 2>/dev/null | grep -q ":3306 "; then
                port_in_use=true
            fi
        fi

        if [ "$port_in_use" = true ]; then
            log_warning "Port 3306 is in use but database check failed - zombie process detected"
            log_info "Killing zombie MariaDB/MySQL processes..."

            # Kill all mariadbd/mysqld processes
            pkill -9 -f "mariadbd" 2>/dev/null || true
            pkill -9 -f "mysqld" 2>/dev/null || true

            # Wait for port to be released
            sleep 3

            # Verify port is now free
            if command -v ss > /dev/null 2>&1; then
                if ss -tlnp 2>/dev/null | grep -q ":3306 "; then
                    log_warning "Port 3306 still in use after killing processes, waiting longer..."
                    sleep 5
                else
                    log_success "Port 3306 is now free"
                fi
            fi
        fi

        # TERMUX FIX: Clean up stale socket file that can prevent startup
        if [ -e "$socket_file" ]; then
            if ! is_database_process_running; then
                log_warning "Found stale socket file, removing: $socket_file"
                rm -f "$socket_file" 2>/dev/null || true
            fi
        fi

        # TERMUX FIX: Clean up stale aria log control file that can cause crashes
        # This file can become corrupted after an unclean shutdown
        if [ -f "$aria_log" ]; then
            if ! is_database_process_running; then
                log_warning "Found aria_log_control file, may cause issues after unclean shutdown"
                log_info "Backing up and removing aria_log files to allow recovery..."
                # Back up the aria files first
                mkdir -p "$BACKUP_DIR/aria_backup_$(date +%Y%m%d_%H%M%S)" 2>/dev/null || true
                cp "$datadir"/aria_log* "$BACKUP_DIR/aria_backup_$(date +%Y%m%d_%H%M%S)/" 2>/dev/null || true
                # Remove aria log files to allow clean start
                rm -f "$datadir"/aria_log* 2>/dev/null || true
                log_success "Aria log files cleaned up"
            fi
        fi

        # TERMUX FIX: Check for and remove stale PID file
        local pid_file="$datadir/$(hostname).pid"
        if [ -f "$pid_file" ]; then
            local old_pid=$(cat "$pid_file" 2>/dev/null)
            if [ -n "$old_pid" ] && ! kill -0 "$old_pid" 2>/dev/null; then
                log_warning "Found stale PID file, removing: $pid_file"
                rm -f "$pid_file" 2>/dev/null || true
            fi
        fi

        # TERMUX FIX: Check for ib_logfile corruption (common after unclean shutdown)
        local ib_logfile0="$datadir/ib_logfile0"
        if [ -f "$ib_logfile0" ]; then
            # Check if file is zero-sized (corrupted)
            local ib_size=$(stat -c%s "$ib_logfile0" 2>/dev/null || echo "0")
            if [ "$ib_size" = "0" ]; then
                log_warning "Found corrupted ib_logfile (zero size), removing..."
                rm -f "$datadir"/ib_logfile* 2>/dev/null || true
            fi
        fi

        if [ ! -d "$datadir/mysql" ]; then
            log_warning "Database not initialized. Running mysql_install_db..."
            if command -v mariadb-install-db &> /dev/null; then
                log_info "Running: mariadb-install-db --datadir=$datadir"
                if ! mariadb-install-db --datadir="$datadir" 2>>"$MAIN_LOG"; then
                    log_warning "mariadb-install-db returned non-zero, checking if it worked anyway..."
                fi
            elif command -v mysql_install_db &> /dev/null; then
                log_info "Running: mysql_install_db --datadir=$datadir"
                if ! mysql_install_db --datadir="$datadir" 2>>"$MAIN_LOG"; then
                    log_warning "mysql_install_db returned non-zero, checking if it worked anyway..."
                fi
            else
                log_error "No database initialization command found (mariadb-install-db or mysql_install_db)"
                log_warning "Install MariaDB: pkg install mariadb"
                release_db_lock
                return 1
            fi
            sleep 3

            # Verify initialization succeeded
            if [ ! -d "$datadir/mysql" ]; then
                log_error "Database initialization failed - $datadir/mysql does not exist"
                log_warning "Try manually: mariadb-install-db --datadir=$datadir"
                release_db_lock
                return 1
            fi
            log_success "Database initialized successfully"
        fi

        # Start the database server
        local db_started=false
        local db_error_file="$LOG_DIR/mariadb_startup_error_$$.log"

        # Try mariadbd-safe first (newer Termux MariaDB)
        if command -v mariadbd-safe &> /dev/null; then
            log_db "Starting mariadbd-safe in background..."
            log_info "Command: mariadbd-safe --datadir=$datadir --skip-grant-tables"

            # Use nohup and capture stderr separately for better error diagnosis
            # --skip-grant-tables helps on first start or after recovery
            nohup mariadbd-safe --datadir="$datadir" >"$db_error_file" 2>&1 &
            local db_pid=$!
            log_info "MariaDB starting with PID: $db_pid"

            # Wait a moment and verify the process started (give it more time on Termux)
            sleep 5
            if kill -0 "$db_pid" 2>/dev/null || is_database_process_running; then
                log_success "MariaDB process started"
                db_started=true
                # Append any startup messages to main log
                cat "$db_error_file" >> "$MAIN_LOG" 2>/dev/null || true
            else
                log_warning "mariadbd-safe process died immediately"
                # Show the actual error from MariaDB
                if [ -s "$db_error_file" ]; then
                    log_error "MariaDB startup error:"
                    cat "$db_error_file" | head -50 | sed 's/^/  | /' | tee -a "$MAIN_LOG"
                fi

                # Check MariaDB's own error log
                local mariadb_err="$datadir/$(hostname).err"
                if [ -f "$mariadb_err" ]; then
                    log_error "MariaDB error log (last 30 lines):"
                    tail -30 "$mariadb_err" | sed 's/^/  | /' | tee -a "$MAIN_LOG"
                fi
            fi
        fi

        # Fallback to mysqld_safe for older installations
        if [ "$db_started" = false ] && command -v mysqld_safe &> /dev/null; then
            log_db "Starting mysqld_safe in background (fallback)..."
            log_info "Command: mysqld_safe --datadir=$datadir"

            nohup mysqld_safe --datadir="$datadir" >"$db_error_file" 2>&1 &
            local db_pid=$!
            log_info "MySQL starting with PID: $db_pid"

            # Wait a moment and verify the process started
            sleep 5
            if kill -0 "$db_pid" 2>/dev/null || is_database_process_running; then
                log_success "MySQL process started"
                db_started=true
                cat "$db_error_file" >> "$MAIN_LOG" 2>/dev/null || true
            else
                log_warning "mysqld_safe process died immediately"
                if [ -s "$db_error_file" ]; then
                    log_error "MySQL startup error:"
                    cat "$db_error_file" | head -30 | sed 's/^/  | /' | tee -a "$MAIN_LOG"
                fi
            fi
        fi

        # Try direct mariadbd as last resort (without safe wrapper)
        if [ "$db_started" = false ] && command -v mariadbd &> /dev/null; then
            log_db "Trying direct mariadbd start (last resort)..."
            log_info "Command: mariadbd --user=$(whoami) --datadir=$datadir --socket=$socket_file"

            nohup mariadbd --user="$(whoami)" --datadir="$datadir" --socket="$socket_file" >"$db_error_file" 2>&1 &
            local db_pid=$!
            log_info "MariaDB direct starting with PID: $db_pid"

            sleep 5
            if kill -0 "$db_pid" 2>/dev/null || is_database_process_running; then
                log_success "MariaDB (direct) process started"
                db_started=true
                cat "$db_error_file" >> "$MAIN_LOG" 2>/dev/null || true
            else
                log_warning "Direct mariadbd also failed"
                if [ -s "$db_error_file" ]; then
                    log_error "MariaDB direct startup error:"
                    cat "$db_error_file" | head -30 | sed 's/^/  | /' | tee -a "$MAIN_LOG"
                fi
            fi
        fi

        # Clean up error file
        rm -f "$db_error_file" 2>/dev/null || true

        # Check if any database binary is available
        if [ "$db_started" = false ]; then
            if ! command -v mariadbd-safe &> /dev/null && ! command -v mysqld_safe &> /dev/null && ! command -v mariadbd &> /dev/null; then
                log_error "No database server found (mariadbd-safe, mysqld_safe, or mariadbd)"
                log_warning "Install MariaDB on Termux: pkg install mariadb"
            else
                # Database binary exists but won't start - provide recovery guidance
                log_error "Database exists but won't start. Common fixes:"
                log_info "  1. Check disk space: df -h"
                log_info "  2. Force recovery: mariadbd-safe --innodb-force-recovery=1 &"
                log_info "  3. Reset database: rm -rf $datadir && mariadb-install-db"
                log_info "  4. Check permissions: ls -la $datadir"

                # Check MariaDB's own error log one more time
                local mariadb_err="$datadir/$(hostname).err"
                if [ -f "$mariadb_err" ]; then
                    log_warning "Full MariaDB error log path: $mariadb_err"
                    log_warning "View it with: cat $mariadb_err"
                fi
            fi
        fi

        release_db_lock

        if [ "$db_started" = true ]; then
            log_info "Database starting, waiting for readiness..."
            return 0  # Let caller wait for full readiness
        else
            log_error "Failed to start database server on Termux"
            log_warning "Try manually: mariadbd-safe &"
            log_warning "Or check logs: tail -100 $MAIN_LOG"
            log_warning "MariaDB error log: cat $datadir/$(hostname).err"
            return 1
        fi
    fi

    release_db_lock
    log_error "Failed to start database server"
    log_warning "Please start the database server manually:"
    log_info "  - Systemd: sudo systemctl start mysql (or mariadb)"
    log_info "  - SysV: sudo service mysql start"
    log_info "  - Termux: mariadbd-safe &  (or mysqld_safe &)"
    return 1
}

# Initialize the database user and grants if they don't exist
# This is especially important for Termux where the user might not have been created
ensure_database_user() {
    log_db "Ensuring database user exists..."

    local mysql_cmd
    mysql_cmd=$(get_mysql_client)
    if [ -z "$mysql_cmd" ]; then
        log_warning "MySQL/MariaDB client not found, skipping user creation"
        return 1
    fi

    # Reload credentials from .env if available
    load_db_credentials

    local db_user="${DB_USER:-sulfur_bot_user}"
    local db_name="${DB_NAME:-sulfur_bot}"
    local db_pass="${DB_PASS:-}"

    # Try to connect as root (no password - Termux default)
    local can_connect_root=false
    if $mysql_cmd -u root -e "SELECT 1;" &>/dev/null; then
        can_connect_root=true
    fi

    if [ "$can_connect_root" = true ]; then
        log_info "Connected as root, checking database and user..."

        # Create database if it doesn't exist
        if ! $mysql_cmd -u root -e "USE $db_name;" &>/dev/null; then
            log_info "Creating database '$db_name'..."
            $mysql_cmd -u root -e "CREATE DATABASE IF NOT EXISTS $db_name CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>>"$MAIN_LOG"
        fi

        # Create user if it doesn't exist (with or without password based on DB_PASS)
        if [ -n "$db_pass" ] && [ "$(echo "$db_pass" | tr -d ' ')" != "" ]; then
            log_info "Creating user '$db_user' with password..."
            $mysql_cmd -u root -e "CREATE USER IF NOT EXISTS '$db_user'@'localhost' IDENTIFIED BY '$db_pass';" 2>>"$MAIN_LOG" || true
            $mysql_cmd -u root -e "ALTER USER '$db_user'@'localhost' IDENTIFIED BY '$db_pass';" 2>>"$MAIN_LOG" || true
        else
            log_info "Creating user '$db_user' without password..."
            $mysql_cmd -u root -e "CREATE USER IF NOT EXISTS '$db_user'@'localhost';" 2>>"$MAIN_LOG" || true
        fi

        # Grant privileges
        log_info "Granting privileges to '$db_user' on '$db_name'..."
        $mysql_cmd -u root -e "GRANT ALL PRIVILEGES ON $db_name.* TO '$db_user'@'localhost';" 2>>"$MAIN_LOG" || true
        $mysql_cmd -u root -e "FLUSH PRIVILEGES;" 2>>"$MAIN_LOG" || true

        log_success "Database user '$db_user' is ready"
        return 0
    else
        log_warning "Cannot connect as root to create user. User must already exist."
        return 1
    fi
}

ensure_database_running() {
    log_db "Ensuring database server is running..."

    # First check if it's already running and accessible
    if check_database_server; then
        return 0
    fi

    # If not accessible, try to start it
    log_warning "Database server is not accessible, attempting to start..."
    start_database_server

    # Wait for database to become ready (up to 30 seconds)
    local max_wait=30
    local wait_count=0

    log_info "Waiting up to ${max_wait}s for database to become ready..."

    while [ $wait_count -lt $max_wait ]; do
        sleep 1
        wait_count=$((wait_count + 1))

        # Check if process is running
        if ! is_database_process_running; then
            # Process died, try to restart
            log_warning "Database process not running, attempting restart..."
            start_database_server
            continue
        fi

        # Check if we can connect
        if check_database_server; then
            log_success "Database server started and verified (after ${wait_count}s)"

            # Ensure the bot user exists
            ensure_database_user

            return 0
        fi

        # Show progress every 5 seconds
        if [ $((wait_count % 5)) -eq 0 ]; then
            log_info "Still waiting for database... (${wait_count}/${max_wait}s)"
        fi
    done

    # Final check
    if check_database_server; then
        log_success "Database server is now accessible"
        ensure_database_user
        return 0
    fi

    log_error "Could not ensure database server is running after ${max_wait}s"
    log_warning "Bot may experience database connection issues"
    log_info "Try starting the database manually:"
    if [ "$IS_TERMUX" = true ]; then
        log_info "  mysqld_safe &  # or mariadbd-safe &"
        log_info "  sleep 10"
        log_info "  Then restart the bot"
    else
        log_info "  sudo systemctl start mysql  # or mariadb"
    fi
    return 1
}

backup_database() {
    log_db "Creating database backup..."

    # First, check if database is actually accessible
    if ! check_database_server; then
        log_warning "Database server not accessible, skipping backup"
        return 1
    fi

    # Check for mariadb-dump (Termux/newer MariaDB) or mysqldump
    local dump_cmd=""
    if command -v mariadb-dump &> /dev/null; then
        dump_cmd="mariadb-dump"
    elif command -v mysqldump &> /dev/null; then
        dump_cmd="mysqldump"
    else
        log_warning "Neither mariadb-dump nor mysqldump found, skipping backup"
        return 1
    fi

    local backup_file="$BACKUP_DIR/sulfur_bot_backup_$(date +"%Y-%m-%d_%H-%M-%S").sql"
    local backup_success=false

    # Reload credentials from .env if available
    load_db_credentials

    local db_user="${DB_USER:-sulfur_bot_user}"
    local db_name="${DB_NAME:-sulfur_bot}"
    local db_pass="${DB_PASS:-}"

    # Check if password is actually set (not empty or just whitespace)
    local password_set=false
    if [ -n "$db_pass" ] && [ "$(echo "$db_pass" | tr -d ' ')" != "" ]; then
        password_set=true
    fi

    # Try multiple backup methods in order of preference

    # Method 1: Bot user with password
    if [ "$password_set" = true ]; then
        log_db "Trying backup with bot user and password..."
        if $dump_cmd -u "$db_user" -p"$db_pass" "$db_name" > "$backup_file" 2>>"$MAIN_LOG"; then
            log_success "Database backup created: $(basename "$backup_file")"
            backup_success=true
        else
            log_warning "Backup with password failed"
        fi
    fi

    # Method 2: Bot user without password (common in Termux)
    if [ "$backup_success" = false ]; then
        log_db "Trying backup with bot user (no password)..."
        if $dump_cmd -u "$db_user" "$db_name" > "$backup_file" 2>>"$MAIN_LOG"; then
            log_success "Database backup created: $(basename "$backup_file")"
            backup_success=true
        else
            log_warning "Backup with bot user (no password) failed"
        fi
    fi

    # Method 3: Root user without password (Termux default)
    if [ "$backup_success" = false ] && [ "$IS_TERMUX" = true ]; then
        log_db "Trying backup with root user (Termux default)..."
        if $dump_cmd -u root "$db_name" > "$backup_file" 2>>"$MAIN_LOG"; then
            log_success "Database backup created with root: $(basename "$backup_file")"
            backup_success=true
        else
            log_warning "Backup with root user failed"
        fi
    fi

    # Method 4: debian.cnf (Linux systems)
    if [ "$backup_success" = false ] && [ -f "/etc/mysql/debian.cnf" ]; then
        log_db "Trying backup with debian.cnf..."
        if $dump_cmd --defaults-file=/etc/mysql/debian.cnf "$db_name" > "$backup_file" 2>>"$MAIN_LOG"; then
            log_success "Database backup created using debian.cnf: $(basename "$backup_file")"
            backup_success=true
        else
            log_warning "Backup with debian.cnf failed"
        fi
    fi

    # Check if backup was successful
    if [ "$backup_success" = false ]; then
        log_error "Database backup failed with all methods"
        log_info "The bot will continue, but automatic backups are not working."
        log_info "To fix this, ensure the database user has proper permissions:"
        if [ "$IS_TERMUX" = true ]; then
            log_info "  mariadb -u root -e \"GRANT ALL ON sulfur_bot.* TO 'sulfur_bot_user'@'localhost'; FLUSH PRIVILEGES;\""
        else
            log_info "  mysql -u root -p -e \"GRANT ALL ON sulfur_bot.* TO 'sulfur_bot_user'@'localhost'; FLUSH PRIVILEGES;\""
        fi
        # Remove empty backup file
        rm -f "$backup_file" 2>/dev/null
        return 1
    fi

    # Verify backup file is not empty
    if [ ! -s "$backup_file" ]; then
        log_warning "Backup file is empty, removing..."
        rm -f "$backup_file"
        return 1
    fi

    # Keep only last 10 backups
    local backup_count
    backup_count=$(ls -1 "$BACKUP_DIR"/*.sql 2>/dev/null | wc -l)
    if [ "$backup_count" -gt 10 ]; then
        ls -1t "$BACKUP_DIR"/*.sql | tail -n +11 | xargs rm -f
        log_info "Cleaned up old backups (kept last 10)"
    fi

    return 0
}

# ==============================================================================
# Database Migration Functions
# ==============================================================================

# Helper function to run a MySQL query with proper credentials
run_mysql_query() {
    local query="$1"
    local mysql_cmd
    mysql_cmd=$(get_mysql_client)

    if [ -z "$mysql_cmd" ]; then
        return 1
    fi

    # Reload credentials from .env if available
    load_db_credentials

    local db_user="${DB_USER:-sulfur_bot_user}"
    local db_name="${DB_NAME:-sulfur_bot}"
    local db_pass="${DB_PASS:-}"

    # Check if password is set
    local password_set=false
    if [ -n "$db_pass" ] && [ "$(echo "$db_pass" | tr -d ' ')" != "" ]; then
        password_set=true
    fi

    # Try bot user with password
    if [ "$password_set" = true ]; then
        if echo "$query" | $mysql_cmd -u "$db_user" -p"$db_pass" "$db_name" 2>>"$MAIN_LOG"; then
            return 0
        fi
    fi

    # Try bot user without password
    if echo "$query" | $mysql_cmd -u "$db_user" "$db_name" 2>>"$MAIN_LOG"; then
        return 0
    fi

    # Try root (Termux default)
    if [ "$IS_TERMUX" = true ]; then
        if echo "$query" | $mysql_cmd -u root "$db_name" 2>>"$MAIN_LOG"; then
            return 0
        fi
    fi

    return 1
}

# Helper function to run a MySQL query and return the result
run_mysql_query_result() {
    local query="$1"
    local mysql_cmd
    mysql_cmd=$(get_mysql_client)

    if [ -z "$mysql_cmd" ]; then
        echo ""
        return 1
    fi

    # Reload credentials from .env if available
    load_db_credentials

    local db_user="${DB_USER:-sulfur_bot_user}"
    local db_name="${DB_NAME:-sulfur_bot}"
    local db_pass="${DB_PASS:-}"

    # Check if password is set
    local password_set=false
    if [ -n "$db_pass" ] && [ "$(echo "$db_pass" | tr -d ' ')" != "" ]; then
        password_set=true
    fi

    # Try bot user with password
    if [ "$password_set" = true ]; then
        local result
        result=$($mysql_cmd -u "$db_user" -p"$db_pass" "$db_name" -sN -e "$query" 2>>"$MAIN_LOG")
        if [ $? -eq 0 ]; then
            echo "$result"
            return 0
        fi
    fi

    # Try bot user without password
    local result
    result=$($mysql_cmd -u "$db_user" "$db_name" -sN -e "$query" 2>>"$MAIN_LOG")
    if [ $? -eq 0 ]; then
        echo "$result"
        return 0
    fi

    # Try root (Termux default)
    if [ "$IS_TERMUX" = true ]; then
        result=$($mysql_cmd -u root "$db_name" -sN -e "$query" 2>>"$MAIN_LOG")
        if [ $? -eq 0 ]; then
            echo "$result"
            return 0
        fi
    fi

    echo ""
    return 1
}

# Helper function to run a SQL file
run_mysql_file() {
    local sql_file="$1"
    local mysql_cmd
    mysql_cmd=$(get_mysql_client)

    if [ -z "$mysql_cmd" ]; then
        return 1
    fi

    # Reload credentials from .env if available
    load_db_credentials

    local db_user="${DB_USER:-sulfur_bot_user}"
    local db_name="${DB_NAME:-sulfur_bot}"
    local db_pass="${DB_PASS:-}"

    # Check if password is set
    local password_set=false
    if [ -n "$db_pass" ] && [ "$(echo "$db_pass" | tr -d ' ')" != "" ]; then
        password_set=true
    fi

    # Try bot user with password
    if [ "$password_set" = true ]; then
        if $mysql_cmd -u "$db_user" -p"$db_pass" "$db_name" < "$sql_file" 2>>"$MAIN_LOG"; then
            return 0
        fi
    fi

    # Try bot user without password
    if $mysql_cmd -u "$db_user" "$db_name" < "$sql_file" 2>>"$MAIN_LOG"; then
        return 0
    fi

    # Try root (Termux default)
    if [ "$IS_TERMUX" = true ]; then
        if $mysql_cmd -u root "$db_name" < "$sql_file" 2>>"$MAIN_LOG"; then
            return 0
        fi
    fi

    return 1
}

run_database_migrations() {
    log_db "Checking for pending database migrations..."

    # Check if migrations directory exists
    if [ ! -d "scripts/db_migrations" ]; then
        log_info "No migrations directory found, skipping"
        return 0
    fi

    # Get MySQL command
    local mysql_cmd
    mysql_cmd=$(get_mysql_client)
    if [ -z "$mysql_cmd" ]; then
        log_error "MySQL/MariaDB client not found, cannot run migrations"
        return 1
    fi

    # Create migration tracking table if it doesn't exist
    local create_tracking_table="
    CREATE TABLE IF NOT EXISTS schema_migrations (
        id INT AUTO_INCREMENT PRIMARY KEY,
        migration_name VARCHAR(255) UNIQUE NOT NULL,
        applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_migration_name (migration_name)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;"

    run_mysql_query "$create_tracking_table"

    # Find all .sql migration files
    local migrations_run=0
    for migration_file in scripts/db_migrations/*.sql; do
        if [ -f "$migration_file" ]; then
            local migration_name
            migration_name=$(basename "$migration_file")

            # Check if migration already applied
            local check_query="SELECT COUNT(*) FROM schema_migrations WHERE migration_name = '$migration_name'"
            local already_applied
            already_applied=$(run_mysql_query_result "$check_query")

            if [ "$already_applied" = "0" ]; then
                log_db "Applying migration: $migration_name"

                # Run the migration
                if run_mysql_file "$migration_file"; then
                    # Mark as applied
                    run_mysql_query "INSERT INTO schema_migrations (migration_name) VALUES ('$migration_name')"
                    log_success "Migration applied: $migration_name"
                    migrations_run=$((migrations_run + 1))
                else
                    log_error "Failed to apply migration: $migration_name"
                    log_warning "Check logs for details"
                fi
            fi
        fi
    done

    if [ $migrations_run -eq 0 ]; then
        log_info "No pending migrations found"
    else
        log_success "Applied $migrations_run migration(s)"
    fi

    return 0
}

install_optional_dependencies() {
    log_info "Checking optional dependencies for advanced features..."

    # Find Python
    local python_exe="$PYTHON_CMD"
    local pip_exe="$PYTHON_CMD -m pip"

    if [ -f "venv/bin/python" ]; then
        python_exe="venv/bin/python"
        pip_exe="$python_exe -m pip"
    fi

    # Check for edge-tts (voice TTS)
    if ! $python_exe -c "import edge_tts" &>/dev/null; then
        log_warning "edge-tts not installed (optional for voice features)"
        log_info "Installing edge-tts for voice TTS support..."
        if $pip_exe install edge-tts >>"$MAIN_LOG" 2>&1; then
            log_success "edge-tts installed successfully"
        else
            log_warning "Failed to install edge-tts (optional, voice TTS won't work)"
        fi
    else
        log_success "edge-tts is installed"
    fi

    # Check for SpeechRecognition (voice transcription)
    if ! $python_exe -c "import speech_recognition" &>/dev/null; then
        log_warning "SpeechRecognition not installed (optional for voice features)"
        log_info "Installing SpeechRecognition for voice transcription..."
        if $pip_exe install SpeechRecognition >>"$MAIN_LOG" 2>&1; then
            log_success "SpeechRecognition installed successfully"
        else
            log_warning "Failed to install SpeechRecognition (optional, voice transcription won't work)"
        fi
    else
        log_success "SpeechRecognition is installed"
    fi

    log_info "Optional dependencies check complete"
}

# ==============================================================================
# Git Functions
# ==============================================================================

git_commit() {
    local message=${1:-"chore: Auto-commit from maintenance script"}

    # Skip commit if SKIP_COMMIT is enabled (default)
    if [ "$SKIP_COMMIT" = true ]; then
        log_git "Auto-commit disabled (SKIP_COMMIT=true). Bot should only pull from main."
        return 1
    fi

    log_git "Checking for changes to commit..."

    # Check if git user is configured
    local git_user=$(git config user.name 2>/dev/null || true)
    local git_email=$(git config user.email 2>/dev/null || true)

    if [ -z "$git_user" ] || [ -z "$git_email" ]; then
        log_warning "Git user not configured, setting default values..."
        git config user.name "Sulfur Bot Maintenance" 2>>"$MAIN_LOG" || true
        git config user.email "sulfur-bot@localhost" 2>>"$MAIN_LOG" || true
    fi

    # Check if there are any changes (excluding .gitignore'd files)
    local status_output
    status_output=$(git status --porcelain 2>&1)

    if [ -z "$status_output" ]; then
        log_git "No changes to commit (all changes are in .gitignore)"
        return 1
    fi

    # Show what will be committed (for debugging on Termux)
    log_warning "Changes detected, files to commit:"
    echo "$status_output" | head -10 | sed 's/^/  | /' | tee -a "$MAIN_LOG"
    if [ $(echo "$status_output" | wc -l) -gt 10 ]; then
        log_info "  ... and $(( $(echo "$status_output" | wc -l) - 10 )) more file(s)"
    fi

    # Stage all changes (respects .gitignore)
    if ! git add -A 2>>"$MAIN_LOG"; then
        log_error "Git add failed - check permissions and .gitignore"
        log_warning "Git add output:"
        git add -A 2>&1 | tail -5 | sed 's/^/  | /' | tee -a "$MAIN_LOG"
        return 1
    fi

    # Verify something was actually staged
    local staged_files
    staged_files=$(git diff --cached --name-only 2>&1)

    if [ -z "$staged_files" ]; then
        log_git "No files staged for commit (all changes are in .gitignore)"
        log_info "Note: Logs, backups, and runtime files are excluded per .gitignore"
        return 1
    fi

    log_info "Staged files for commit:"
    echo "$staged_files" | head -10 | sed 's/^/  | /' | tee -a "$MAIN_LOG"

    # Commit changes
    if ! git commit -m "$message" >>"$MAIN_LOG" 2>&1; then
        log_error "Git commit failed"
        git status 2>&1 | tail -10 | sed 's/^/  | /' | tee -a "$MAIN_LOG"
        return 1
    fi

    log_success "Changes committed locally"

    # Try to push changes
    if git push >>"$MAIN_LOG" 2>&1; then
        log_success "Changes pushed to remote"
        return 0
    else
        log_warning "Git push failed - commits are local only"
        log_warning "Reason: Network issue, credentials, or remote repository access"
        log_info "To manually push: git push"

        # Show push error details for debugging (especially useful on Termux)
        local push_error
        push_error=$(git push 2>&1 | head -5)
        if [ -n "$push_error" ]; then
            log_info "Push error details:"
            echo "$push_error" | sed 's/^/  | /' | tee -a "$MAIN_LOG"
        fi

        return 0  # Return success since commit succeeded, even if push failed
    fi
}

check_for_updates() {
    log_update "Checking for updates..."

    git remote update &>>"$MAIN_LOG"

    LOCAL=$(git rev-parse @)
    REMOTE=$(git rev-parse @{u})

    if [ "$LOCAL" != "$REMOTE" ]; then
        # Check for update loop prevention
        local current_time
        current_time=$(date +%s)
        local time_since_update=$((current_time - LAST_UPDATE_TIME))

        # Reset loop counter if enough time has passed
        if [ "$time_since_update" -gt "$UPDATE_LOOP_RESET_SECONDS" ]; then
            UPDATE_LOOP_COUNT=0
        fi

        # Check if we're in an update loop
        if [ "$UPDATE_LOOP_COUNT" -ge "$MAX_UPDATE_LOOP_COUNT" ]; then
            log_warning "Update loop detected! Skipping update to prevent infinite loop."
            log_warning "Last $MAX_UPDATE_LOOP_COUNT updates happened within $UPDATE_LOOP_RESET_SECONDS seconds."
            log_warning "Waiting for loop reset period to pass..."
            return 1
        fi

        # Check if we've already pulled this commit
        if [ "$REMOTE" = "$LAST_PULLED_COMMIT" ]; then
            log_warning "Already pulled commit $REMOTE, skipping to prevent loop"
            return 1
        fi

        log_warning "Updates available!"
        return 0
    else
        return 1
    fi
}

apply_updates() {
    log_update "Applying updates..."

    update_status "Updating..."

    # Track update loop prevention
    UPDATE_LOOP_COUNT=$((UPDATE_LOOP_COUNT + 1))
    LAST_UPDATE_TIME=$(date +%s)

    # For public repos: Reset local changes instead of committing
    # This prevents merge conflicts and ensures we always use remote files
    if [ "$SKIP_COMMIT" = true ]; then
        # Check if there are local changes
        if ! git diff-index --quiet HEAD -- 2>/dev/null; then
            log_warning "Local changes detected - stashing them before update"
            log_info "Changes will be discarded to use remote files (public repo mode)"

            # Show what's being reset
            git status --short 2>&1 | head -5 | sed 's/^/  | /' | tee -a "$MAIN_LOG"

            # Reset to match remote exactly
            git fetch origin >>"$MAIN_LOG" 2>&1
            git reset --hard origin/main >>"$MAIN_LOG" 2>&1 || git reset --hard origin/master >>"$MAIN_LOG" 2>&1

            log_success "Local changes discarded - using remote files"
        fi
    else
        # Legacy mode: Commit local changes before update (only if explicitly enabled)
        git_commit "chore: Auto-commit before update"
    fi

    # Check if this script is being updated
    git fetch &>>"$MAIN_LOG"
    CHANGED_FILES=$(git diff --name-only HEAD...origin/main 2>/dev/null || git diff --name-only HEAD...origin/master 2>/dev/null || echo "")

    # Track the commit we're about to pull
    local REMOTE_COMMIT
    REMOTE_COMMIT=$(git rev-parse @{u} 2>/dev/null)

    if echo "$CHANGED_FILES" | grep -q "maintain_bot.sh"; then
        log_update "Maintenance script will be updated - restarting..."

        # For public repos, use hard reset to always match remote
        if [ "$SKIP_COMMIT" = true ]; then
            git reset --hard "$REMOTE_COMMIT" >>"$MAIN_LOG" 2>&1
        else
            # Legacy mode with rebase/merge
            if ! git pull --rebase >>"$MAIN_LOG" 2>&1; then
                log_warning "Rebase failed, trying merge with --no-ff..."
                git rebase --abort >>"$MAIN_LOG" 2>&1 || true
                if ! git pull --no-rebase >>"$MAIN_LOG" 2>&1; then
                    log_warning "Standard merge failed, trying --no-ff merge..."
                    git merge --no-ff origin/main >>"$MAIN_LOG" 2>&1 || git merge --no-ff origin/master >>"$MAIN_LOG" 2>&1 || true
                fi
            fi
        fi

        # Track the pulled commit
        LAST_PULLED_COMMIT="$REMOTE_COMMIT"

        # Restart this script
        exec "$0" "$@"
    fi

    # Normal update - use hard reset for public repos to avoid merge conflicts
    if [ "$SKIP_COMMIT" = true ]; then
        # Always use remote files - no merge conflicts
        git reset --hard "$REMOTE_COMMIT" >>"$MAIN_LOG" 2>&1
        log_update "Files updated to remote version (hard reset)"
    else
        # Legacy mode: Use rebase to avoid merge conflicts when local commits exist
        if ! git pull --rebase >>"$MAIN_LOG" 2>&1; then
            log_warning "Rebase failed, trying merge with --no-ff..."
            git rebase --abort >>"$MAIN_LOG" 2>&1 || true
            if ! git pull --no-rebase >>"$MAIN_LOG" 2>&1; then
                log_warning "Standard merge failed, trying explicit --no-ff merge..."
                if ! git merge --no-ff origin/main >>"$MAIN_LOG" 2>&1; then
                    if ! git merge --no-ff origin/master >>"$MAIN_LOG" 2>&1; then
                        log_error "All merge strategies failed - manual intervention may be required"
                        log_warning "Continuing with current code..."
                    fi
                fi
            fi
        fi
    fi

    # Track the pulled commit to prevent update loops
    LAST_PULLED_COMMIT=$(git rev-parse @ 2>/dev/null)
    if [ -n "$LAST_PULLED_COMMIT" ]; then
        log_update "Updated to commit: ${LAST_PULLED_COMMIT:0:8}"
    else
        log_update "Updated to latest commit"
    fi

    # Update Python dependencies after code update
    log_update "Updating Python dependencies..."

    # Check and install system dependencies first (Termux only)
    if [ "$IS_TERMUX" = true ]; then
        log_update "Checking system dependencies..."
        ensure_system_dependencies
    fi
    
    # Check and install Java 21 for Minecraft support
    check_and_install_java_21 || true

    local python_exe="$PYTHON_CMD"
    if [ -f "venv/bin/python" ]; then
        python_exe="venv/bin/python"
    fi

    local venv_pip="venv/bin/pip"
    if [ -f "$venv_pip" ]; then
        # Update pip first
        $python_exe -m pip install --upgrade pip >>"$MAIN_LOG" 2>&1 || true

        # Set SODIUM_INSTALL=system to use system libsodium for PyNaCl
        # This prevents build failures on Termux where bundled libsodium configure fails
        export SODIUM_INSTALL=system

        # Install/update requirements
        if $venv_pip install -r requirements.txt >>"$MAIN_LOG" 2>&1; then
            log_success "Dependencies updated successfully"

            # Update marker file
            local req_hash=$(md5sum requirements.txt 2>/dev/null | awk '{print $1}' || echo "unknown")
            echo "$req_hash" > ".last_requirements_install"
        else
            log_warning "Dependencies update failed; retrying without cache..."
            if $venv_pip install -r requirements.txt --no-cache-dir >>"$MAIN_LOG" 2>&1; then
                log_success "Dependencies updated successfully (no cache)"
                local req_hash=$(md5sum requirements.txt 2>/dev/null | awk '{print $1}' || echo "unknown")
                echo "$req_hash" > ".last_requirements_install"
            else
                log_error "Failed to update dependencies"
                log_warning "Bot may experience import errors"
                log_info "If PyNaCl fails on Termux, install: pkg install ${TERMUX_SYSTEM_DEPS[*]}"
            fi
        fi
    else
        log_warning "venv/bin/pip not found, skipping dependency update"
    fi

    # Initialize/update database tables after pulling updates
    log_update "Updating database tables and applying migrations..."

    # Run database initialization and apply migrations with retry
    local db_attempt=1
    local db_max_attempts=5
    local db_success=false

    while [ $db_attempt -le $db_max_attempts ]; do
        log_update "Database update attempt $db_attempt/$db_max_attempts..."

        # Calculate adaptive wait time
        local wait_time=$((5 * db_attempt))

        if "$python_exe" -c "
from modules.db_helpers import init_db_pool, initialize_database, apply_pending_migrations
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

try:
    load_dotenv()
    
    # Priority: 1) database.json (created by setup wizard), 2) environment variables
    db_config_file = Path('config/database.json')
    if db_config_file.exists():
        # Load from database.json
        try:
            with open(db_config_file, 'r') as f:
                db_config = json.load(f)
            DB_HOST = db_config.get('host', 'localhost')
            DB_USER = db_config.get('user', 'sulfur_bot_user')
            DB_PASS = db_config.get('password', '')
            DB_NAME = db_config.get('database', 'sulfur_bot')
            print(f'Loaded database config from database.json')
        except Exception as e:
            print(f'Warning: Failed to load database.json: {e}, falling back to environment variables')
            # Fall back to environment variables
            DB_HOST = os.environ.get('DB_HOST', 'localhost')
            DB_USER = os.environ.get('DB_USER', 'sulfur_bot_user')
            DB_PASS = os.environ.get('DB_PASS', '')
            DB_NAME = os.environ.get('DB_NAME', 'sulfur_bot')
    else:
        # Load from environment variables
        DB_HOST = os.environ.get('DB_HOST', 'localhost')
        DB_USER = os.environ.get('DB_USER', 'sulfur_bot_user')
        DB_PASS = os.environ.get('DB_PASS', '')
        DB_NAME = os.environ.get('DB_NAME', 'sulfur_bot')

    # Initialize database pool with retry logic
    print(f'Initializing database pool: {DB_USER}@{DB_HOST}/{DB_NAME}')
    if not init_db_pool(DB_HOST, DB_USER, DB_PASS, DB_NAME):
        print('ERROR: Failed to initialize database pool')
        sys.exit(1)
    print('Database pool initialized')

    # Create base tables with retry logic
    print('Initializing database tables...')
    if not initialize_database():
        print('ERROR: Failed to initialize database tables')
        sys.exit(1)
    print('Database tables initialized successfully')

    # Apply any pending migrations
    print('Checking for pending migrations...')
    applied_count, errors = apply_pending_migrations()
    if applied_count > 0:
        print(f'Applied {applied_count} new database migrations')
    if errors:
        print(f'WARNING: {len(errors)} migration errors occurred')
        for error in errors:
            print(f'  - {error}')
        # Don't exit on migration errors, just warn
        print('Continuing despite migration errors...')
    else:
        print('All database migrations up to date')

    sys.exit(0)
except Exception as e:
    print(f'ERROR: Database update failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
" >>"$MAIN_LOG" 2>&1; then
            log_success "Database tables and migrations updated successfully"
            db_success=true
            break
        else
            log_warning "Database update attempt $db_attempt failed"

            # Show last few lines of error from log
            if [ -f "$MAIN_LOG" ]; then
                log_warning "Last error from database update:"
                tail -n 5 "$MAIN_LOG" | sed 's/^/  | /' | tee -a "$MAIN_LOG"
            fi

            if [ $db_attempt -lt $db_max_attempts ]; then
                log_info "Retrying in $wait_time seconds..."
                sleep $wait_time
            fi
        fi

        db_attempt=$((db_attempt + 1))
    done

    if [ "$db_success" = false ]; then
        log_error "Database update failed after $db_max_attempts attempts"
        log_warning "Bot may experience database issues. Check $MAIN_LOG for details"
    fi

    log_success "Update complete"
    date -u +"%Y-%m-%dT%H:%M:%SZ" > "last_update.txt"
}

# ==============================================================================
# Process Management
# ==============================================================================

show_port_info() {
    local port=$1
    log_info "Checking port $port status..."

    # Show which processes are using the port
    if command -v lsof >/dev/null 2>&1; then
        local port_info=$(lsof -i:$port 2>/dev/null)
        if [ -n "$port_info" ]; then
            log_warning "Processes using port $port:"
            echo "$port_info" | sed 's/^/  | /' | tee -a "$MAIN_LOG"
        fi
    elif command -v ss >/dev/null 2>&1; then
        local port_info=$(ss -tlnp 2>/dev/null | grep ":$port ")
        if [ -n "$port_info" ]; then
            log_warning "Processes using port $port:"
            echo "$port_info" | sed 's/^/  | /' | tee -a "$MAIN_LOG"
        fi
    elif command -v netstat >/dev/null 2>&1; then
        local port_info=$(netstat -tulnp 2>/dev/null | grep ":$port ")
        if [ -n "$port_info" ]; then
            log_warning "Processes using port $port:"
            echo "$port_info" | sed 's/^/  | /' | tee -a "$MAIN_LOG"
        fi
    fi

    # Also show if port is in TIME_WAIT state
    if command -v ss >/dev/null 2>&1; then
        local timewait=$(ss -tan 2>/dev/null | grep ":$port " | grep TIME-WAIT)
        if [ -n "$timewait" ]; then
            log_info "Port $port has connections in TIME-WAIT state"
        fi
    fi
}

check_port_available() {
    local port=$1

    # Check if port is in use using multiple methods
    # Method 1: Try using lsof (if available)
    if command -v lsof >/dev/null 2>&1; then
        if lsof -ti:$port >/dev/null 2>&1; then
            return 1  # Port is in use
        fi
    fi

    # Method 2: Try using netstat (if available)
    if command -v netstat >/dev/null 2>&1; then
        if netstat -tuln 2>/dev/null | grep -q ":$port "; then
            return 1  # Port is in use
        fi
    fi

    # Method 3: Try using ss (if available, more common on modern Linux)
    if command -v ss >/dev/null 2>&1; then
        if ss -tuln 2>/dev/null | grep -q ":$port "; then
            return 1  # Port is in use
        fi
    fi

    # Method 4: Try to connect to the port (last resort)
    if command -v nc >/dev/null 2>&1; then
        if nc -z 127.0.0.1 $port 2>/dev/null; then
            return 1  # Port is in use
        fi
    fi

    return 0  # Port is available
}

free_port() {
    local port=$1
    local max_attempts=${2:-3}
    local attempt=1

    log_warning "Attempting to free port $port..."

    while [ $attempt -le $max_attempts ]; do
        local pids=""

        # Try to find PIDs using the port
        if command -v lsof >/dev/null 2>&1; then
            pids=$(lsof -ti:$port 2>/dev/null)
        elif command -v fuser >/dev/null 2>&1; then
            pids=$(fuser $port/tcp 2>/dev/null | sed 's/^ *//')
        fi

        if [ -n "$pids" ]; then
            if [ $attempt -eq 1 ]; then
                log_warning "Found processes using port $port: $pids"
                # Show detailed info on first attempt
                show_port_info $port
            else
                log_warning "Attempt $attempt/$max_attempts: Processes still on port $port: $pids"
            fi

            for pid in $pids; do
                # Get process command for better logging
                local proc_cmd=""
                if [ -f "/proc/$pid/cmdline" ]; then
                    proc_cmd=$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null | cut -c1-60)
                elif command -v ps >/dev/null 2>&1; then
                    proc_cmd=$(ps -p $pid -o comm= 2>/dev/null)
                fi

                if [ -n "$proc_cmd" ]; then
                    log_info "  PID $pid: $proc_cmd"
                fi

                # If this PID matches our web dashboard PID file, clean up the stale PID file
                if [ -f "$WEB_PID_FILE" ] && [ "$(cat "$WEB_PID_FILE" 2>/dev/null)" = "$pid" ]; then
                    log_warning "  PID $pid matches web dashboard PID file - cleaning up stale reference"
                    rm -f "$WEB_PID_FILE"
                fi

                # Try graceful shutdown first on first attempt, force kill on retries
                if kill -0 "$pid" 2>/dev/null; then
                    if [ $attempt -eq 1 ]; then
                        log_info "  Sending TERM signal to PID $pid..."
                        kill -TERM "$pid" 2>/dev/null

                        # Wait up to 3 seconds for graceful shutdown
                        local wait_count=0
                        while [ $wait_count -lt 3 ]; do
                            if ! kill -0 "$pid" 2>/dev/null; then
                                log_success "  Process $pid terminated gracefully"
                                break
                            fi
                            sleep 1
                            wait_count=$((wait_count + 1))
                        done
                    fi

                    # Force kill if still running or on retry attempts
                    if kill -0 "$pid" 2>/dev/null; then
                        log_warning "  Force killing PID $pid..."
                        kill -9 "$pid" 2>/dev/null
                        sleep 1
                    fi
                fi
            done

            # Wait for port to be released (exponential backoff)
            local wait_time=$((2 * attempt))
            log_info "Waiting ${wait_time}s for port to be released..."
            sleep $wait_time

            # Check if port is now free
            if check_port_available $port; then
                log_success "Port $port is now available"
                return 0
            fi

            # Not free yet, try again
            attempt=$((attempt + 1))
        else
            # No PIDs found, but port might be in TIME_WAIT state
            if ! check_port_available $port; then
                log_warning "No processes found using port $port, but port still reports as in use"
                log_info "Port might be in TIME-WAIT state, waiting..."
                sleep $((2 * attempt))

                # Check again after waiting
                if check_port_available $port; then
                    log_success "Port $port is now available"
                    return 0
                fi
                attempt=$((attempt + 1))
            else
                log_success "Port $port is available"
                return 0
            fi
        fi
    done

    # Failed after all attempts
    log_error "Failed to free port $port after $max_attempts attempts"
    show_port_info $port
    return 1
}

start_web_dashboard() {
    log_web "Starting Web Dashboard..."

    # Always clean up any stale PID file first
    if [ -f "$WEB_PID_FILE" ]; then
        local old_pid=$(cat "$WEB_PID_FILE" 2>/dev/null)
        if [ -n "$old_pid" ] && ! kill -0 "$old_pid" 2>/dev/null; then
            log_warning "Removing stale web dashboard PID file (PID $old_pid is not running)"
            rm -f "$WEB_PID_FILE"
        fi
    fi

    # Check if there are active processes using port 5000 (not just TIME_WAIT)
    local port_pids=""
    if command -v lsof >/dev/null 2>&1; then
        port_pids=$(lsof -ti:5000 2>/dev/null)
    elif command -v fuser >/dev/null 2>&1; then
        port_pids=$(fuser 5000/tcp 2>/dev/null | sed 's/^ *//')
    fi

    if [ -n "$port_pids" ]; then
        log_warning "Port 5000 is in use by process(es): $port_pids"
        show_port_info 5000

        # Try to free the port with up to 3 attempts
        if ! free_port 5000 3; then
            log_error "Failed to free port 5000 after multiple attempts."
            log_warning "Waiting additional 5 seconds for port to release naturally..."
            sleep 5
            log_warning "Web Dashboard has retry logic and will attempt to start anyway..."
            log_warning "If startup fails, manual intervention may be required:"
            log_warning "  1. Find processes: lsof -ti:5000 or fuser 5000/tcp or ss -tlnp | grep :5000"
            log_warning "  2. Kill process: kill -9 <PID>"
            # Don't return 1 here - let the web dashboard's retry logic handle it
        else
            # Port was freed successfully, wait a moment for OS to fully release it
            log_info "Port freed, waiting 3 seconds for OS to complete cleanup..."
            sleep 3
        fi
    else
        # Port might be in TIME_WAIT, but web dashboard can handle that with SO_REUSEADDR
        if ! check_port_available 5000; then
            log_info "Port 5000 may be in TIME_WAIT state (no active process detected)"
            log_info "Web Dashboard will use SO_REUSEADDR to bind anyway"
        else
            log_success "Port 5000 is available"
        fi
    fi

    # Find Python
    local python_exe="$PYTHON_CMD"
    if [ -f "venv/bin/python" ]; then
        python_exe="venv/bin/python"
    fi

    # Quick validation - check if Flask is importable
    if ! "$python_exe" -c "import flask, flask_socketio" 2>/dev/null; then
        log_warning "Flask dependencies not installed, attempting to install..."

        # Try to install Flask dependencies
        local pip_exe="$python_exe"
        if [ -f "venv/bin/pip" ]; then
            pip_exe="venv/bin/pip"
        else
            pip_exe="$python_exe -m pip"
        fi

        # Capture output for better error visibility
        local pip_output_file="/tmp/sulfur_web_pip_install_$$.log"
        if $pip_exe install -r requirements.txt >"$pip_output_file" 2>&1; then
            rm -f "$pip_output_file"
            log_success "Flask dependencies installed successfully"
        else
            log_error "Failed to install Flask dependencies"
            log_warning "Last 10 lines of pip install output:"
            tail -n 10 "$pip_output_file" | sed 's/^/  | /'
            rm -f "$pip_output_file"
            log_warning "Web Dashboard cannot start without Flask and Flask-SocketIO"
            log_warning "Try manually: $python_exe -m pip install Flask Flask-SocketIO waitress"
            return 1
        fi

        # Verify installation
        if ! "$python_exe" -c "import flask, flask_socketio" 2>/dev/null; then
            log_error "Flask dependencies still not available after installation"
            log_warning "Try manually: $python_exe -m pip install Flask Flask-SocketIO waitress"
            return 1
        fi
    fi

    # Verify web_dashboard.py exists
    if [ ! -f "web_dashboard.py" ]; then
        log_error "web_dashboard.py not found in current directory"
        return 1
    fi

    # Start web dashboard in background
    log_info "Starting web dashboard process..."
    nohup "$python_exe" -u web_dashboard.py >> "$WEB_LOG" 2>&1 &
    local web_pid=$!

    # Verify process started
    if [ -z "$web_pid" ]; then
        log_error "Failed to get web dashboard PID"
        return 1
    fi

    # Wait a moment and verify process didn't die immediately
    sleep 1
    if ! kill -0 "$web_pid" 2>/dev/null; then
        log_error "Web dashboard process died immediately after startup"
        log_warning "Check web log for errors: tail -n 50 $WEB_LOG"
        return 1
    fi

    echo "$web_pid" > "$WEB_PID_FILE"
    log_info "Web dashboard process started with PID: $web_pid"

    # Wait for it to start
    local retries=0
    local max_retries=15

    while [ $retries -lt $max_retries ]; do
        sleep 2

        # Prefer an HTTP HEAD check with a short timeout; fall back to nc
        if curl -sf --max-time 2 -I http://127.0.0.1:5000 >/dev/null 2>&1 \
           || nc -z 127.0.0.1 5000 2>/dev/null; then
            log_success "Web Dashboard running at http://localhost:5000 (PID: $web_pid)"

            # Show network access info for Termux users
            if [ "$IS_TERMUX" = true ]; then
                # Try to get local IP address
                local local_ip=""
                if command -v ip >/dev/null 2>&1; then
                    local_ip=$(ip -4 addr show 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v '127.0.0.1' | head -n1)
                elif command -v ifconfig >/dev/null 2>&1; then
                    # Fallback to ifconfig for Termux
                    local_ip=$(ifconfig 2>/dev/null | grep -oP 'inet\s+\K[\d.]+' | grep -v '127.0.0.1' | head -n1)
                fi
                if [ -n "$local_ip" ]; then
                    log_info "Access from network: http://${local_ip}:5000"
                fi
            fi

            WEB_RESTART_COUNT=0  # Reset counter on successful start
            return 0
        fi

        # Check if process is still alive
        if ! kill -0 "$web_pid" 2>/dev/null; then
            log_error "Web Dashboard process died during startup (PID: $web_pid)"

            # Check if it was due to port conflict
            if [ -f "$WEB_LOG" ]; then
                if grep -q "Port 5000 is already in use" "$WEB_LOG" 2>/dev/null || \
                   grep -q "Address already in use" "$WEB_LOG" 2>/dev/null; then
                    log_error "Port 5000 conflict detected - this indicates a race condition or port cleanup failure"
                    show_port_info 5000

                    log_warning "Last 20 lines from web dashboard log:"
                    tail -n 20 "$WEB_LOG" | sed 's/^/  | /' | tee -a "$MAIN_LOG"
                else
                    log_warning "Last 10 lines from web dashboard log:"
                    tail -n 10 "$WEB_LOG" | sed 's/^/  | /' | tee -a "$MAIN_LOG"
                fi
            fi

            rm -f "$WEB_PID_FILE"
            return 1
        fi

        retries=$((retries + 1))
        log_info "Waiting for web dashboard to respond... (attempt $retries/$max_retries)"
    done

    log_warning "Web Dashboard start timeout - process running but not responding on port 5000"
    log_warning "Process PID: $web_pid, Check $WEB_LOG for details"

    # Check if port is actually listening
    if check_port_available 5000; then
        log_error "Port 5000 is not being listened on by the web dashboard process"
        show_port_info 5000
    else
        log_info "Port 5000 appears to be in use, but not responding to HTTP requests"
    fi

    return 1
}

start_bot() {
    log_bot "Starting bot..."

    update_status "Starting..."

    # Find Python
    local python_exe="$PYTHON_CMD"
    if [ -f "venv/bin/python" ]; then
        python_exe="venv/bin/python"
    fi

    # Verify bot.py exists
    if [ ! -f "bot.py" ]; then
        log_error "bot.py not found in current directory"
        return 1
    fi

    # Start bot in background
    nohup "$python_exe" -u bot.py >> "$BOT_LOG" 2>&1 &
    local bot_pid=$!

    # Verify process started
    if [ -z "$bot_pid" ]; then
        log_error "Failed to get bot PID"
        return 1
    fi

    # Wait a moment and verify process is still running
    sleep 1
    if ! kill -0 "$bot_pid" 2>/dev/null; then
        log_error "Bot process died immediately after startup"
        log_warning "Check bot log for errors: tail -n 50 $BOT_LOG"
        return 1
    fi

    echo "$bot_pid" > "$BOT_PID_FILE"
    update_status "Running" "$bot_pid"
    log_success "Bot started (PID: $bot_pid)"
    return 0
}

stop_bot() {
    if [ -f "$BOT_PID_FILE" ]; then
        local bot_pid=$(cat "$BOT_PID_FILE")
        if kill -0 "$bot_pid" 2>/dev/null; then
            log_bot "Sending graceful shutdown signal..."
            # Send SIGTERM for graceful shutdown
            kill -TERM "$bot_pid" 2>/dev/null

            # Wait up to 5 seconds for graceful shutdown
            for i in {1..5}; do
                if ! kill -0 "$bot_pid" 2>/dev/null; then
                    log_success "Bot shut down gracefully"
                    break
                fi
                sleep 1
            done

            # Force kill if still running
            if kill -0 "$bot_pid" 2>/dev/null; then
                log_warning "Force stopping bot..."
                kill -9 "$bot_pid" 2>/dev/null
            fi
        fi
        rm -f "$BOT_PID_FILE"
    fi
}

# ==============================================================================
# Main Loop
# ==============================================================================

echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║       Sulfur Discord Bot - Maintenance System v2.0        ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
log_warning "Press Ctrl+C at any time to gracefully shutdown"
echo ""

# Environment info
if [ "$IS_TERMUX" = true ]; then
    log_info "Running on Termux"
    log_info "Logs: $LOG_DIR/maintenance_${LOG_TIMESTAMP}.log"
    log_info "To view logs: tail -f $LOG_DIR/maintenance_*.log"
    echo ""
else
    log_info "Running on Linux"
fi

# Initial backup
if [ "$SKIP_BACKUP" != true ]; then
    backup_database
else
    log_db "Skipping initial backup due to SKIP_BACKUP=true"
fi

# Prune old logs (keep last 20 per type)
find "$LOG_DIR" -type f -name 'maintenance_*.log' | sort -r | tail -n +21 | xargs -r rm -f
find "$LOG_DIR" -type f -name 'bot_*.log' | sort -r | tail -n +21 | xargs -r rm -f
find "$LOG_DIR" -type f -name 'web_*.log' | sort -r | tail -n +21 | xargs -r rm -f

# Preflight check for token to avoid restart loops
preflight_check() {
    if [ ! -f ".env" ]; then
        log_error ".env file not found in project root"
        return 1
    fi
    # Extract token (handles quoted/unquoted)
    local raw_line
    raw_line=$(grep -E '^\s*DISCORD_BOT_TOKEN\s*=' .env | head -n1)
    if [ -z "$raw_line" ]; then
        log_error "DISCORD_BOT_TOKEN not found in .env"
        return 1
    fi
    local token
    token=$(echo "$raw_line" | sed -E "s/^[^=]*=\s*//; s/^\"|\"$//g; s/^'|'\$//g")
    if [ -z "$token" ]; then
        log_error "DISCORD_BOT_TOKEN is empty"
        return 1
    fi
    # Validate dot parts (expect 3)
    local part_count
    part_count=$(echo "$token" | awk -F'.' '{print NF}')
    if [ "$part_count" -ne 3 ]; then
        log_error "DISCORD_BOT_TOKEN appears malformed (expected 3 parts)"
        return 1
    fi
    return 0
}

# Check and warn about optional API keys
check_optional_api_keys() {
    log_info "Checking optional API keys..."

    local warnings=0

    # Check for GEMINI_API_KEY or OPENAI_API_KEY (at least one is needed for AI)
    local gemini_key openai_key
    gemini_key=$(grep -E '^\s*GEMINI_API_KEY\s*=' .env 2>/dev/null | head -n1 | sed -E "s/^[^=]*=\s*//; s/^\"|\"$//g; s/^'|'\$//g")
    openai_key=$(grep -E '^\s*OPENAI_API_KEY\s*=' .env 2>/dev/null | head -n1 | sed -E "s/^[^=]*=\s*//; s/^\"|\"$//g; s/^'|'\$//g")

    if [ -z "$gemini_key" ] || [ "$gemini_key" = "your_gemini_api_key_here" ]; then
        if [ -z "$openai_key" ] || [ "$openai_key" = "your_openai_api_key_here" ]; then
            log_warning "No AI API key configured (GEMINI_API_KEY or OPENAI_API_KEY)"
            log_warning "AI chat features will not work without an API key"
            log_info "  Get a free Gemini key: https://aistudio.google.com/apikey"
            warnings=$((warnings + 1))
        fi
    fi

    # Check for LASTFM_API_KEY (optional, for enhanced music features)
    local lastfm_key
    lastfm_key=$(grep -E '^\s*LASTFM_API_KEY\s*=' .env 2>/dev/null | head -n1 | sed -E "s/^[^=]*=\s*//; s/^\"|\"$//g; s/^'|'\$//g")

    if [ -z "$lastfm_key" ] || [ "$lastfm_key" = "your_lastfm_api_key_here" ]; then
        log_info "LASTFM_API_KEY not configured (optional)"
        log_info "  Last.fm API enhances music recommendations and Songle song variety"
        log_info "  Get a free key: https://www.last.fm/api/account/create"
    else
        log_success "LASTFM_API_KEY is configured"
    fi

    # Check for FOOTBALL_DATA_API_KEY (optional, for sports betting)
    local football_key
    football_key=$(grep -E '^\s*FOOTBALL_DATA_API_KEY\s*=' .env 2>/dev/null | head -n1 | sed -E "s/^[^=]*=\s*//; s/^\"|\"$//g; s/^'|'\$//g")

    if [ -z "$football_key" ] || [ "$football_key" = "your_football_data_api_key_here" ]; then
        log_info "FOOTBALL_DATA_API_KEY not configured (optional)"
        log_info "  Required for international league betting (Premier League, La Liga, etc.)"
        log_info "  German leagues work without this key (via OpenLigaDB)"
    else
        log_success "FOOTBALL_DATA_API_KEY is configured"
    fi

    if [ $warnings -gt 0 ]; then
        log_warning "Some features may be limited. Configure API keys in .env or via the web dashboard"
        log_info "Web dashboard: http://localhost:5000/api_keys"
    fi

    return 0
}

# Ensure system dependencies are installed (Termux-specific)
ensure_system_dependencies() {
    # Only run on Termux
    if [ "$IS_TERMUX" != true ]; then
        return 0
    fi

    log_info "Checking system dependencies for Termux..."

    # Use the global constant for required packages
    local missing_packages=()

    # Check each package
    for pkg in "${TERMUX_SYSTEM_DEPS[@]}"; do
        if ! pkg list-installed 2>/dev/null | grep -q "^${pkg}"; then
            missing_packages+=("$pkg")
            log_warning "System package '$pkg' is not installed"
        fi
    done

    # Install missing packages
    if [ ${#missing_packages[@]} -gt 0 ]; then
        log_info "Installing missing system packages: ${missing_packages[*]}"
        log_info "This is required for PyNaCl (voice support) to build successfully"

        # Try to install packages
        if pkg install -y "${missing_packages[@]}" >>"$MAIN_LOG" 2>&1; then
            log_success "System packages installed successfully"
        else
            log_warning "Failed to install some system packages"
            log_warning "PyNaCl may fail to build without these dependencies"
            log_info "You can manually install them: pkg install ${missing_packages[*]}"
        fi
    else
        log_success "All required system packages are installed"
    fi

    return 0
}

# Ensure venv and dependencies are present
ensure_python_env() {
    log_info "Ensuring Python virtual environment and dependencies..."

    # Prefer project venv
    if [ ! -f "venv/bin/python" ]; then
        log_warning "Virtual environment not found; creating venv..."
        if ! $PYTHON_CMD -m venv venv >>"$MAIN_LOG" 2>&1; then
            log_error "Failed to create virtual environment"
            return 1
        fi
        log_success "Virtual environment created"
    fi

    local venv_python="venv/bin/python"
    local venv_pip="venv/bin/pip"

    # Upgrade pip to avoid common install issues
    $venv_python -m pip install --upgrade pip >>"$MAIN_LOG" 2>&1 || true

    # Always check and install/update requirements to catch new dependencies
    log_info "Checking and updating Python dependencies..."

    # Create a marker file to track last requirements check
    local req_marker=".last_requirements_install"
    local req_hash=$(md5sum requirements.txt 2>/dev/null | awk '{print $1}' || echo "unknown")
    local need_install=false

    # Check if requirements.txt changed or marker doesn't exist
    if [ ! -f "$req_marker" ]; then
        need_install=true
    else
        local last_hash=$(cat "$req_marker" 2>/dev/null || echo "")
        if [ "$req_hash" != "$last_hash" ]; then
            log_info "requirements.txt has changed, updating dependencies..."
            need_install=true
        fi
    fi

    # Also check if discord.py is missing (critical dependency)
    if ! $venv_python -c 'import discord' >/dev/null 2>&1; then
        log_warning "discord.py not found in venv; installing requirements..."
        need_install=true
    fi

    # Install/update if needed
    if [ "$need_install" = true ]; then
        log_info "Installing Python dependencies from requirements.txt..."

        # Set SODIUM_INSTALL=system to use system libsodium for PyNaCl
        export SODIUM_INSTALL=system

        # Try normal install first
        if $venv_pip install -r requirements.txt >>"$MAIN_LOG" 2>&1; then
            log_success "Dependencies installed successfully"
            echo "$req_hash" > "$req_marker"
        else
            log_warning "First install attempt failed; retrying without cache..."
            if $venv_pip install -r requirements.txt --no-cache-dir >>"$MAIN_LOG" 2>&1; then
                log_success "Dependencies installed successfully (no cache)"
                echo "$req_hash" > "$req_marker"
            else
                log_error "Failed to install Python dependencies after retry"
                log_warning "Trying individual critical packages..."

                # Try to install critical packages individually
                for pkg in "discord.py" "Flask" "Flask-SocketIO" "edge-tts" "mysql-connector-python"; do
                    if ! $venv_pip install "$pkg" >>"$MAIN_LOG" 2>&1; then
                        log_error "Failed to install $pkg"
                    else
                        log_success "Installed $pkg"
                    fi
                done

                # Don't save marker if installation failed
                return 1
            fi
        fi
    else
        log_success "Python dependencies are up to date"
    fi

    # Final verification - check for all required packages
    local missing_packages=""

    # Check for discord.py (required for bot)
    if ! $venv_python -c 'import discord' >/dev/null 2>&1; then
        missing_packages="${missing_packages}discord.py "
    fi

    # Check for Flask dependencies (required for web dashboard)
    if ! $venv_python -c 'import flask' >/dev/null 2>&1; then
        missing_packages="${missing_packages}Flask "
    fi

    if ! $venv_python -c 'import flask_socketio' >/dev/null 2>&1; then
        missing_packages="${missing_packages}Flask-SocketIO "
    fi

    if [ -n "$missing_packages" ]; then
        log_error "Missing required packages: $missing_packages"
        log_warning "Attempting to install missing packages..."

        # Set SODIUM_INSTALL=system to use system libsodium for PyNaCl
        export SODIUM_INSTALL=system

        # Capture pip output for better error visibility
        local pip_output_file="/tmp/sulfur_pip_install_$$.log"
        if ! $venv_pip install -r requirements.txt >"$pip_output_file" 2>&1; then
            log_error "Failed to install dependencies"
            log_warning "Last 15 lines of pip install output:"
            tail -n 15 "$pip_output_file" | sed 's/^/  | /' | tee -a "$MAIN_LOG"
            rm -f "$pip_output_file"
            log_warning "Full log available at: $MAIN_LOG"
            return 1
        fi
        rm -f "$pip_output_file"

        # Verify again after installation
        if ! $venv_python -c 'import discord, flask, flask_socketio' >/dev/null 2>&1; then
            log_error "Package installation failed. Manual intervention required."
            log_warning "Try manually: $venv_pip install -r requirements.txt"
            return 1
        fi
    fi

    log_success "Python environment ready (all required packages installed)"
    return 0
}

# Ensure preflight passes before starting
until preflight_check; do
    log_warning "Fix the issues above (edit .env), then press Enter to retry..."
    read -r _ || { log_error "Cannot read input in non-interactive mode"; sleep 60; }
done

# Check optional API keys and show warnings (non-blocking)
check_optional_api_keys

# Ensure system dependencies are installed (Termux only)
ensure_system_dependencies

# Ensure venv/deps before starting services
if ! ensure_python_env; then
    log_error "Cannot start without required Python packages"
    log_warning "Common fixes for Termux:"
    log_warning "  1. Ensure you have enough storage space"
    log_warning "  2. Try: pkg install python python-pip libsodium clang"
    log_warning "  3. Check the error messages above for specific issues"
    log_warning "Full log available at: $MAIN_LOG"
    exit 1
fi

# Ensure database server is running
ensure_database_running || log_warning "Database server check failed, continuing anyway..."

# Run database initialization and migrations on startup
initialize_database_with_retry() {
    local max_retries=5
    local attempt=1

    log_info "Initializing database and applying migrations..."

    local python_exe="$PYTHON_CMD"
    if [ -f "venv/bin/python" ]; then
        python_exe="venv/bin/python"
    fi

    while [ $attempt -le $max_retries ]; do
        log_info "Database initialization attempt $attempt/$max_retries..."

        # Calculate adaptive wait time (exponential backoff)
        local wait_time=$((5 * attempt))

        if "$python_exe" -c "
from modules.db_helpers import init_db_pool, initialize_database, apply_pending_migrations
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

try:
    load_dotenv()
    
    # Priority: 1) database.json (created by setup wizard), 2) environment variables
    db_config_file = Path('config/database.json')
    if db_config_file.exists():
        # Load from database.json
        try:
            with open(db_config_file, 'r') as f:
                db_config = json.load(f)
            DB_HOST = db_config.get('host', 'localhost')
            DB_USER = db_config.get('user', 'sulfur_bot_user')
            DB_PASS = db_config.get('password', '')
            DB_NAME = db_config.get('database', 'sulfur_bot')
            print(f'Loaded database config from database.json')
        except Exception as e:
            print(f'Warning: Failed to load database.json: {e}, falling back to environment variables')
            # Fall back to environment variables
            DB_HOST = os.environ.get('DB_HOST', 'localhost')
            DB_USER = os.environ.get('DB_USER', 'sulfur_bot_user')
            DB_PASS = os.environ.get('DB_PASS', '')
            DB_NAME = os.environ.get('DB_NAME', 'sulfur_bot')
    else:
        # Load from environment variables
        DB_HOST = os.environ.get('DB_HOST', 'localhost')
        DB_USER = os.environ.get('DB_USER', 'sulfur_bot_user')
        DB_PASS = os.environ.get('DB_PASS', '')
        DB_NAME = os.environ.get('DB_NAME', 'sulfur_bot')

    # Initialize database pool with retry logic
    print(f'Attempting to initialize database pool: {DB_USER}@{DB_HOST}/{DB_NAME}')
    if not init_db_pool(DB_HOST, DB_USER, DB_PASS, DB_NAME):
        print('ERROR: Failed to initialize database pool')
        sys.exit(1)
    print('Database pool initialized successfully')

    # Create base tables with retry logic
    print('Attempting to initialize database tables...')
    if not initialize_database():
        print('ERROR: Failed to initialize database tables')
        sys.exit(1)
    print('Database tables initialized successfully')

    # Apply any pending migrations
    print('Checking for pending migrations...')
    applied_count, errors = apply_pending_migrations()
    if applied_count > 0:
        print(f'Applied {applied_count} new database migrations')
    if errors:
        print(f'WARNING: {len(errors)} migration errors occurred')
        for error in errors:
            print(f'  - {error}')
        # Don't exit on migration errors, just warn
        print('Continuing despite migration errors...')
    else:
        print('All database migrations up to date')

    sys.exit(0)
except Exception as e:
    print(f'ERROR: Database initialization failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
" >>"$MAIN_LOG" 2>&1; then
            log_success "Database ready - tables and migrations up to date"
            return 0
        else
            log_warning "Database initialization attempt $attempt failed"

            # Show last few lines of error from log
            if [ -f "$MAIN_LOG" ]; then
                log_warning "Last error from database initialization:"
                tail -n 5 "$MAIN_LOG" | sed 's/^/  | /' | tee -a "$MAIN_LOG"
            fi

            if [ $attempt -lt $max_retries ]; then
                log_info "Retrying in $wait_time seconds..."
                sleep $wait_time
            fi
        fi

        attempt=$((attempt + 1))
    done

    log_error "Database initialization failed after $max_retries attempts"
    log_error "This indicates a serious problem with the database connection or configuration"
    log_warning "Bot will start anyway, but database features will be unavailable"
    log_warning "Check the following:"
    log_info "  1. Database server is running: systemctl status mysql (or mariadb)"
    log_info "  2. Database credentials in .env are correct"
    log_info "  3. Database 'sulfur_bot' exists"
    log_info "  4. User 'sulfur_bot_user' has proper permissions"
    log_warning "Full log available at: $MAIN_LOG"
    return 1
}

initialize_database_with_retry

# Run additional database migrations (for advanced AI features)
run_database_migrations

# Install optional dependencies for advanced features (voice, etc.)
install_optional_dependencies

# Start web dashboard
start_web_dashboard || log_warning "Web Dashboard failed to start, continuing anyway..."

# ==============================================================================
# Minecraft Server Auto-Start Function
# ==============================================================================

start_minecraft_server() {
    log_info "Checking Minecraft server auto-start configuration..."

    # Find Python
    local python_exe="$PYTHON_CMD"
    if [ -f "venv/bin/python" ]; then
        python_exe="venv/bin/python"
    fi

    # Check if Minecraft is enabled and boot_with_bot is true
    if ! $python_exe -c "
import json
import sys
try:
    with open('config/config.json', 'r') as f:
        config = json.load(f)

    # Check if minecraft feature is enabled
    minecraft_enabled = config.get('features', {}).get('minecraft_server', False)

    # Check if boot_with_bot is enabled in minecraft config
    boot_with_bot = config.get('modules', {}).get('minecraft', {}).get('boot_with_bot', False)

    if minecraft_enabled and boot_with_bot:
        sys.exit(0)  # Start server
    else:
        sys.exit(1)  # Don't start server
except Exception as e:
    print(f'Error checking config: {e}')
    sys.exit(1)
" 2>>"$MAIN_LOG"; then
        log_info "Minecraft server auto-start is enabled"
        log_info "Starting Minecraft server..."

        # Start server using Python module
        if $python_exe -c "
import asyncio
import json
import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Import minecraft module
try:
    from modules import minecraft_server as mc
    from modules.logger_utils import bot_logger as logger
except ImportError as e:
    print(f'ERROR: Failed to import minecraft_server module: {e}')
    sys.exit(1)

async def start_mc_server():
    try:
        # Load config
        with open('config/config.json', 'r') as f:
            config = json.load(f)

        mc_config = config.get('modules', {}).get('minecraft', {})

        # Check if server is already running
        if mc.is_server_running():
            print('Minecraft server is already running')
            return True

        # Start the server
        print('Starting Minecraft server...')
        success, message = await mc.start_server(mc_config)

        if success:
            print(f'Minecraft server started successfully: {message}')
            return True
        else:
            print(f'Failed to start Minecraft server: {message}')
            return False

    except Exception as e:
        print(f'ERROR: Failed to start Minecraft server: {e}')
        import traceback
        traceback.print_exc()
        return False

# Run the async function
try:
    result = asyncio.run(start_mc_server())
    sys.exit(0 if result else 1)
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
" 2>>"$MAIN_LOG"; then
            log_success "Minecraft server started successfully"
        else
            log_warning "Failed to start Minecraft server (check logs for details)"
            log_info "You can start it manually via the web dashboard at http://localhost:5000/minecraft"
        fi
    else
        log_info "Minecraft server auto-start is disabled (feature not enabled or boot_with_bot=false)"
        log_info "Enable it in config.json: features.minecraft_server=true and modules.minecraft.boot_with_bot=true"
    fi
}

# Start Minecraft server if configured
start_minecraft_server || log_info "Minecraft server auto-start skipped"

# Main loop
while true; do
    # Start bot with retry logic
    cleanup_orphans

    # Initialize bot start time for crash detection
    BOT_START_TIME=$(date +%s)

    start_attempts=0
    max_start_attempts=3
    while [ $start_attempts -lt $max_start_attempts ]; do
        if start_bot; then
            break
        fi

        start_attempts=$((start_attempts + 1))
        if [ $start_attempts -lt $max_start_attempts ]; then
            log_warning "Bot start attempt $start_attempts failed, retrying in 10 seconds..."
            sleep 10
        else
            log_error "Bot failed to start after $max_start_attempts attempts"
            log_error "Check logs and fix errors before restarting: $BOT_LOG"
            log_warning "Sleeping 60 seconds before retry..."
            sleep 60
        fi
    done

    # Monitor bot
    while true; do
        sleep 1
        CHECK_COUNTER=$((CHECK_COUNTER + 1))

        # Check if bot is still running
        if [ -f "$BOT_PID_FILE" ]; then
            BOT_PID=$(cat "$BOT_PID_FILE" 2>/dev/null)
            if [ -z "$BOT_PID" ]; then
                log_warning "PID file empty or corrupted"
                break
            fi
            if ! kill -0 "$BOT_PID" 2>/dev/null; then
                log_warning "Bot stopped unexpectedly"
                break
            fi
        else
            log_warning "PID file disappeared"
            break
        fi

        # Check for control flags
        if [ -f "stop.flag" ]; then
            log_warning "Stop flag detected"
            rm -f "stop.flag"
            cleanup
        fi

        if [ -f "restart.flag" ]; then
            log_warning "Restart flag detected"
            rm -f "restart.flag"
            stop_bot
            break
        fi

        # Periodic tasks
        if [ $((CHECK_COUNTER % COMMIT_INTERVAL)) -eq 0 ]; then
            git_commit "chore: Auto-commit database changes"
        fi

        if [ $((CHECK_COUNTER % BACKUP_INTERVAL)) -eq 0 ]; then
            if [ "$SKIP_BACKUP" != true ]; then
                backup_database
            else
                log_db "Skipping scheduled backup due to SKIP_BACKUP=true"
            fi
        fi

        if [ $((CHECK_COUNTER % CHECK_INTERVAL)) -eq 0 ]; then
            date -u +"%Y-%m-%dT%H:%M:%SZ" > "last_check.txt"

            if check_for_updates; then
                log_warning "Stopping bot for update..."
                stop_bot
                apply_updates
                break
            fi
        fi

        # Check web dashboard with cooldown and retry limit
        if [ -f "$WEB_PID_FILE" ]; then
            WEB_PID=$(cat "$WEB_PID_FILE")
            if ! kill -0 "$WEB_PID" 2>/dev/null; then
                # Web dashboard has stopped
                current_time=$(date +%s)
                time_since_last_restart=$((current_time - LAST_WEB_RESTART))

                # Check if we've hit the restart threshold
                if [ $WEB_RESTART_COUNT -ge $WEB_RESTART_THRESHOLD ]; then
                    if [ $time_since_last_restart -lt 300 ]; then
                        # Multiple restarts in 5 minutes - something is wrong
                        log_error "Web Dashboard has crashed $WEB_RESTART_COUNT times. Giving up on auto-restart."
                        log_warning "Please check $WEB_LOG for errors and fix the issue manually."
                        log_warning "You can try restarting it with: ./maintain_bot.sh"
                        rm -f "$WEB_PID_FILE"
                        WEB_RESTART_COUNT=$((WEB_RESTART_COUNT + 1))  # Increment to prevent further attempts
                    else
                        # It's been a while, reset the counter and try again
                        log_warning "Resetting web dashboard restart counter (last restart was ${time_since_last_restart}s ago)"
                        WEB_RESTART_COUNT=0
                    fi
                fi

                # Only try to restart if under threshold and cooldown has passed
                if [ $WEB_RESTART_COUNT -lt $WEB_RESTART_THRESHOLD ]; then
                    if [ $time_since_last_restart -ge $WEB_RESTART_COOLDOWN ]; then
                        log_warning "Web Dashboard stopped, restarting... (attempt $((WEB_RESTART_COUNT + 1))/$WEB_RESTART_THRESHOLD)"

                        # Clean up stale PID file before restart attempt
                        rm -f "$WEB_PID_FILE"

                        # Show the last error from web log before restarting
                        if [ -f "$WEB_LOG" ] && [ $WEB_RESTART_COUNT -gt 0 ]; then
                            log_warning "Last error from Web Dashboard log:"
                            tail -n 20 "$WEB_LOG" | grep -i -E "error|exception|traceback|failed|port.*in use" | tail -n 5 | sed 's/^/  | /' | tee -a "$MAIN_LOG"
                        fi

                        # CRITICAL: Add delay before restart to let port fully release
                        # This is especially important on Termux where socket cleanup is slower
                        # Adaptive delay based on environment
                        if [ "$IS_TERMUX" = true ]; then
                            restart_delay=12  # Longer for Termux (slower socket cleanup)
                        else
                            restart_delay=6   # Shorter for regular Linux
                        fi
                        log_info "Waiting ${restart_delay}s for port cleanup before restart..."
                        sleep $restart_delay

                        LAST_WEB_RESTART=$current_time
                        WEB_RESTART_COUNT=$((WEB_RESTART_COUNT + 1))

                        if start_web_dashboard; then
                            log_success "Web Dashboard restarted successfully"
                        else
                            log_error "Failed to restart Web Dashboard"
                            # Show more detailed error info
                            if [ -f "$WEB_LOG" ]; then
                                log_warning "Recent Web Dashboard log output:"
                                tail -n 30 "$WEB_LOG" | sed 's/^/  | /' | tee -a "$MAIN_LOG"
                            fi
                        fi
                    else
                        wait_time=$((WEB_RESTART_COOLDOWN - time_since_last_restart))
                        log_warning "Web Dashboard stopped, but waiting ${wait_time}s before retry (cooldown period)"
                    fi
                fi
            fi
        fi
    done

    update_status "Stopped"

    # Crash-loop detection: if bot exits within QUICK_CRASH_SECONDS, increment; else reset
    BOT_STOP_TIME=$(date +%s)
    RUN_SECONDS=$((BOT_STOP_TIME - BOT_START_TIME))
    if [ "$RUN_SECONDS" -lt "$QUICK_CRASH_SECONDS" ]; then
        CRASH_COUNT=$((CRASH_COUNT + 1))
    else
        CRASH_COUNT=0
    fi

    if [ "$CRASH_COUNT" -ge "$CRASH_THRESHOLD" ]; then
        log_error "Bot is crashing quickly ($CRASH_COUNT times). Pausing restarts."
        if [ -f "$BOT_LOG" ]; then
            log_warning "Last 50 lines from bot log:"
            tail -n 50 "$BOT_LOG" || true
        fi
        log_warning "Fix configuration (e.g., token in .env), then press Enter to retry."
        read -r _ || { log_error "Cannot read input in non-interactive mode"; sleep 60; }
        CRASH_COUNT=0
        # Re-run preflight before restarting
        until preflight_check; do
            log_warning "Fix the issues above (edit .env), then press Enter to retry..."
            read -r _ || { log_error "Cannot read input in non-interactive mode"; sleep 60; }
        done
    fi

    log_warning "Bot stopped, restarting in 5 seconds..."
    sleep 5
done
