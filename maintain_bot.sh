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

# Counters
CHECK_COUNTER=0

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
    
    # Stop bot
    if [ -f "$BOT_PID_FILE" ]; then
        BOT_PID=$(cat "$BOT_PID_FILE")
        if kill -0 "$BOT_PID" 2>/dev/null; then
            log_bot "Stopping bot (PID: $BOT_PID)..."
            kill "$BOT_PID" 2>/dev/null
            sleep 2
            kill -9 "$BOT_PID" 2>/dev/null
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
    backup_database
    git_commit "chore: Auto-commit on shutdown"
    
    update_status "Shutdown"
    log_success "Cleanup complete"
    exit 0
}

# Set trap for Ctrl+C
trap cleanup SIGINT SIGTERM

# ==============================================================================
# Database Functions
# ==============================================================================

backup_database() {
    log_db "Creating database backup..."
    
    if ! command -v mysqldump &> /dev/null; then
        log_warning "mysqldump not found, skipping backup"
        return 1
    fi
    
    local backup_file="$BACKUP_DIR/sulfur_bot_backup_$(date +"%Y-%m-%d_%H-%M-%S").sql"
    
    if mysqldump -u "$DB_USER" "$DB_NAME" > "$backup_file" 2>>"$MAIN_LOG"; then
        log_success "Database backup created: $(basename "$backup_file")"
        
        # Keep only last 10 backups
        local backup_count=$(ls -1 "$BACKUP_DIR"/*.sql 2>/dev/null | wc -l)
        if [ "$backup_count" -gt 10 ]; then
            ls -1t "$BACKUP_DIR"/*.sql | tail -n +11 | xargs rm -f
            log_warning "Cleaned up old backups (kept last 10)"
        fi
        
        return 0
    else
        log_error "Database backup failed"
        return 1
    fi
}

# ==============================================================================
# Git Functions
# ==============================================================================

git_commit() {
    local message=${1:-"chore: Auto-commit from maintenance script"}
    
    log_git "Checking for changes to commit..."
    
    # Check if there are any changes
    if [ -z "$(git status --porcelain)" ]; then
        log_git "No changes to commit"
        return 1
    fi
    
    log_warning "Changes detected, committing..."
    
    git add -A 2>>"$MAIN_LOG"
    if git commit -m "$message" >>"$MAIN_LOG" 2>&1; then
        if git push >>"$MAIN_LOG" 2>&1; then
            log_success "Changes committed and pushed"
            return 0
        else
            log_error "Git push failed"
            return 1
        fi
    else
        log_error "Git commit failed"
        return 1
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

start_web_dashboard() {
    log_web "Starting Web Dashboard..."
    
    # Find Python
    local python_exe="$PYTHON_CMD"
    if [ -f "venv/bin/python" ]; then
        python_exe="venv/bin/python"
    fi
    
    # Start web dashboard in background
    nohup "$python_exe" -u web_dashboard.py >> "$WEB_LOG" 2>&1 &
    local web_pid=$!
    echo "$web_pid" > "$WEB_PID_FILE"
    
    # Wait for it to start
    local retries=0
    local max_retries=15
    
    while [ $retries -lt $max_retries ]; do
        sleep 2

        # Prefer an HTTP HEAD check with a short timeout; fall back to nc
        if curl -sf --max-time 2 -I http://127.0.0.1:5000 >/dev/null 2>&1 \
           || nc -z 127.0.0.1 5000 2>/dev/null; then
            log_success "Web Dashboard running at http://localhost:5000 (PID: $web_pid)"
            return 0
        fi
        
        if ! kill -0 "$web_pid" 2>/dev/null; then
            log_error "Web Dashboard failed to start"
            rm -f "$WEB_PID_FILE"
            return 1
        fi
        
        retries=$((retries + 1))
    done
    
    log_warning "Web Dashboard start timeout"
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
    
    # Start bot in background
    nohup "$python_exe" -u bot.py >> "$BOT_LOG" 2>&1 &
    local bot_pid=$!
    echo "$bot_pid" > "$BOT_PID_FILE"
    
    update_status "Running" "$bot_pid"
    log_success "Bot started (PID: $bot_pid)"
}

stop_bot() {
    if [ -f "$BOT_PID_FILE" ]; then
        local bot_pid=$(cat "$BOT_PID_FILE")
        if kill -0 "$bot_pid" 2>/dev/null; then
            log_bot "Stopping bot..."
            kill "$bot_pid" 2>/dev/null
            sleep 2
            kill -9 "$bot_pid" 2>/dev/null
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
else
    log_info "Running on Linux"
fi

# Initial backup
backup_database

# Start web dashboard
start_web_dashboard || log_warning "Web Dashboard failed to start, continuing anyway..."

# Main loop
while true; do
    # Start bot
    start_bot
    
    # Monitor bot
    while true; do
        sleep 1
        CHECK_COUNTER=$((CHECK_COUNTER + 1))
        
        # Check if bot is still running
        if [ -f "$BOT_PID_FILE" ]; then
            BOT_PID=$(cat "$BOT_PID_FILE")
            if ! kill -0 "$BOT_PID" 2>/dev/null; then
                log_warning "Bot stopped unexpectedly"
                break
            fi
        else
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
            backup_database
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
        
        # Check web dashboard
        if [ -f "$WEB_PID_FILE" ]; then
            WEB_PID=$(cat "$WEB_PID_FILE")
            if ! kill -0 "$WEB_PID" 2>/dev/null; then
                log_warning "Web Dashboard stopped, restarting..."
                start_web_dashboard
            fi
        fi
    done
    
    update_status "Stopped"
    log_warning "Bot stopped, restarting in 5 seconds..."
    sleep 5
done
