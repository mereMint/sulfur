#!/bin/bash
# ==============================================================================
# Sulfur Bot - Enhanced Maintenance Script for Termux/Linux
# ==============================================================================
# Features:
# - Auto-start bot and web dashboard
# - Check for updates every minute
# - Auto-commit database changes every 5 minutes
# - Auto-backup database every 30 minutes
# - Auto-restart on updates
# - Self-update capability
# - Graceful shutdown with Ctrl+C
# ==============================================================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
MAGENTA='\033[0;35m'
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

# CLI flags
for arg in "$@"; do
    case "$arg" in
        --no-backup|-n)
            SKIP_BACKUP=true
            shift
            ;;
    esac
done

# Counters
CHECK_COUNTER=0
CRASH_COUNT=0
QUICK_CRASH_SECONDS=10
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

# Database credentials
DB_USER="${DB_USER:-sulfur_bot_user}"
DB_NAME="${DB_NAME:-sulfur_bot}"

# ==============================================================================
# Logging Functions
# ==============================================================================

log_message() {
    local color=$1
    local prefix=$2
    local message=$3
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    
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
    
    # Stop web dashboard
    if [ -f "$WEB_PID_FILE" ]; then
        WEB_PID=$(cat "$WEB_PID_FILE")
        if kill -0 "$WEB_PID" 2>/dev/null; then
            log_web "Stopping web dashboard (PID: $WEB_PID)..."
            kill "$WEB_PID" 2>/dev/null
            sleep 2
            kill -9 "$WEB_PID" 2>/dev/null
        fi
        rm -f "$WEB_PID_FILE"
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

backup_database() {
    log_db "Creating database backup..."
    
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
    
    # Try backup with password from environment or without password
    if [ -n "$DB_PASS" ]; then
        # Use password if set
        if $dump_cmd -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" > "$backup_file" 2>>"$MAIN_LOG"; then
            log_success "Database backup created: $(basename "$backup_file")"
        else
            log_error "Database backup failed with password"
            return 1
        fi
    else
        # Try without password (for users with no password like sulfur_bot_user)
        if $dump_cmd -u "$DB_USER" "$DB_NAME" > "$backup_file" 2>>"$MAIN_LOG"; then
            log_success "Database backup created: $(basename "$backup_file")"
        else
            # If that fails, try using defaults-file for debian-sys-maint
            if [ -f "/etc/mysql/debian.cnf" ] && $dump_cmd --defaults-file=/etc/mysql/debian.cnf "$DB_NAME" > "$backup_file" 2>>"$MAIN_LOG"; then
                log_success "Database backup created using debian.cnf: $(basename "$backup_file")"
            else
                log_error "Database backup failed (tried no password and debian.cnf)"
                return 1
            fi
        fi
    fi
    
    # Keep only last 10 backups
    local backup_count=$(ls -1 "$BACKUP_DIR"/*.sql 2>/dev/null | wc -l)
    if [ "$backup_count" -gt 10 ]; then
        ls -1t "$BACKUP_DIR"/*.sql | tail -n +11 | xargs rm -f
        log_warning "Cleaned up old backups (kept last 10)"
    fi
    
    return 0
}

# ==============================================================================
# Git Functions
# ==============================================================================

git_commit() {
    local message=${1:-"chore: Auto-commit from maintenance script"}
    
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
        log_warning "Updates available!"
        return 0
    else
        return 1
    fi
}

apply_updates() {
    log_update "Applying updates..."
    
    update_status "Updating..."
    
    # Commit any pending changes first
    git_commit "chore: Auto-commit before update"
    
    # Check if this script is being updated
    git fetch &>>"$MAIN_LOG"
    CHANGED_FILES=$(git diff --name-only HEAD...origin/main)
    
    if echo "$CHANGED_FILES" | grep -q "maintain_bot.sh"; then
        log_update "Maintenance script will be updated - restarting..."
        
        git pull >>"$MAIN_LOG" 2>&1
        
        # Restart this script
        exec "$0" "$@"
    fi
    
    # Normal update
    git pull >>"$MAIN_LOG" 2>&1
    
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

    # Install requirements if discord.py is missing
    if ! $venv_python -c 'import discord' >/dev/null 2>&1; then
        log_warning "discord.py not found in venv; installing requirements..."
        if ! $venv_pip install -r requirements.txt >>"$MAIN_LOG" 2>&1; then
            log_warning "First install attempt failed; retrying without cache..."
            if ! $venv_pip install -r requirements.txt --no-cache-dir >>"$MAIN_LOG" 2>&1; then
                log_error "Failed to install Python dependencies"
                return 1
            fi
        fi
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
    read -r _
done

# Ensure venv/deps before starting services
if ! ensure_python_env; then
    log_error "Cannot start without required Python packages"
    log_warning "Common fixes for Termux:"
    log_warning "  1. Ensure you have enough storage space"
    log_warning "  2. Try: pkg install python python-pip"
    log_warning "  3. Check the error messages above for specific issues"
    log_warning "Full log available at: $MAIN_LOG"
    exit 1
fi

# Start web dashboard
start_web_dashboard || log_warning "Web Dashboard failed to start, continuing anyway..."

# Main loop
while true; do
    # Start bot with retry logic
    cleanup_orphans
    
    local start_attempts=0
    local max_start_attempts=3
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
                        # Increased to 8 seconds for Termux compatibility
                        restart_delay=8
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
    if [ -f "$BOT_LOG" ]; then
        # If the log file last modified time is recent, we can approximate runtime
        : # placeholder; we track time implicitly by sleeping 1s in loop
    fi

    # Use a timestamp file to measure run duration
    : "${BOT_START_TIME:=$(date +%s)}"
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
        read -r _
        CRASH_COUNT=0
        # Re-run preflight before restarting
        until preflight_check; do
            log_warning "Fix the issues above (edit .env), then press Enter to retry..."
            read -r _
        done
    fi

    log_warning "Bot stopped, restarting in 5 seconds..."
    sleep 5
    BOT_START_TIME=$(date +%s)
done
