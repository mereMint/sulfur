#!/bin/bash
# ==============================================================================
# MariaDB Fix Script for Termux
# ==============================================================================
# This script diagnoses and fixes common MariaDB startup issues on Termux
#
# Usage: bash scripts/fix_mariadb_termux.sh
# ==============================================================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║          MariaDB Fix Script for Termux                     ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Set PREFIX
PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
DATADIR="$PREFIX/var/lib/mysql"
HOSTNAME=$(hostname)

echo -e "${YELLOW}[INFO]${NC} Checking MariaDB installation..."
echo ""

# Check if MariaDB is installed
if ! command -v mariadbd &> /dev/null && ! command -v mariadbd-safe &> /dev/null; then
    echo -e "${RED}[ERROR]${NC} MariaDB is not installed!"
    echo -e "${YELLOW}[FIX]${NC} Install it with: pkg install mariadb"
    exit 1
fi
echo -e "${GREEN}[OK]${NC} MariaDB is installed"

# Function to check if database is running (multiple methods)
is_db_running() {
    # Check by process name
    if pgrep -x mariadbd > /dev/null 2>&1 || pgrep -x mysqld > /dev/null 2>&1; then
        return 0
    fi
    # Check by partial match
    if pgrep -f "mariadbd" > /dev/null 2>&1 || pgrep -f "mysqld" > /dev/null 2>&1; then
        return 0
    fi
    # Check if port 3306 is in use
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

# Check if database is currently running
if is_db_running; then
    echo -e "${GREEN}[OK]${NC} MariaDB is already running!"
    echo ""
    echo -e "${CYAN}Testing connection...${NC}"
    if mariadb -u root -e "SELECT 1;" &>/dev/null; then
        echo -e "${GREEN}[OK]${NC} Database is accessible"

        # Check if sulfur_bot database exists
        echo ""
        echo -e "${CYAN}Checking if sulfur_bot database exists...${NC}"
        if mariadb -u root -e "USE sulfur_bot;" &>/dev/null; then
            echo -e "${GREEN}[OK]${NC} Database 'sulfur_bot' exists"
        else
            echo -e "${YELLOW}[WARN]${NC} Database 'sulfur_bot' does not exist"
            echo -e "${YELLOW}[FIX]${NC} Creating database and user..."

            mariadb -u root -e "CREATE DATABASE IF NOT EXISTS sulfur_bot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            mariadb -u root -e "CREATE USER IF NOT EXISTS 'sulfur_bot_user'@'localhost';"
            mariadb -u root -e "GRANT ALL PRIVILEGES ON sulfur_bot.* TO 'sulfur_bot_user'@'localhost';"
            mariadb -u root -e "FLUSH PRIVILEGES;"

            echo -e "${GREEN}[OK]${NC} Database 'sulfur_bot' and user created"
        fi

        # Check if user has proper permissions
        echo ""
        echo -e "${CYAN}Verifying user permissions...${NC}"
        if mariadb -u sulfur_bot_user -e "USE sulfur_bot; SELECT 1;" &>/dev/null; then
            echo -e "${GREEN}[OK]${NC} User 'sulfur_bot_user' can access the database"
        else
            echo -e "${YELLOW}[WARN]${NC} User 'sulfur_bot_user' cannot access database, fixing..."
            mariadb -u root -e "GRANT ALL PRIVILEGES ON sulfur_bot.* TO 'sulfur_bot_user'@'localhost';"
            mariadb -u root -e "FLUSH PRIVILEGES;"
            echo -e "${GREEN}[OK]${NC} Permissions fixed"
        fi

        echo ""
        echo -e "${GREEN}[SUCCESS]${NC} Database is ready! You can now run: bash maintain_bot.sh"
        exit 0
    else
        echo -e "${YELLOW}[WARN]${NC} Database running but not responding. May need more time."
        echo -e "${CYAN}Waiting 5 more seconds...${NC}"
        sleep 5
        if mariadb -u root -e "SELECT 1;" &>/dev/null; then
            echo -e "${GREEN}[OK]${NC} Database is now accessible"
            exit 0
        else
            echo -e "${YELLOW}[WARN]${NC} Database still not responding."
            echo -e "${YELLOW}[INFO]${NC} Port 3306 may be held by a zombie process."
            echo ""
            echo -e "${CYAN}Showing processes on port 3306:${NC}"
            if command -v ss > /dev/null 2>&1; then
                ss -tlnp 2>/dev/null | grep ":3306 " | sed 's/^/  /'
            fi
            if command -v lsof > /dev/null 2>&1; then
                lsof -i :3306 2>/dev/null | sed 's/^/  /'
            fi
            echo ""
            echo -e "${YELLOW}[FIX]${NC} Try killing all MariaDB processes:"
            echo "  pkill -9 -f mariadbd"
            echo "  pkill -9 -f mysqld"
            echo ""
            read -p "Kill all MariaDB processes now? (y/N) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                pkill -9 -f mariadbd 2>/dev/null || true
                pkill -9 -f mysqld 2>/dev/null || true
                sleep 2
                echo -e "${GREEN}[OK]${NC} Processes killed. Continuing with startup..."
            else
                exit 1
            fi
        fi
    fi
fi

echo -e "${YELLOW}[INFO]${NC} MariaDB is not running. Diagnosing issues..."
echo ""

# Check datadir
echo -e "${CYAN}Checking data directory: $DATADIR${NC}"
if [ ! -d "$DATADIR" ]; then
    echo -e "${YELLOW}[WARN]${NC} Data directory does not exist"
    echo -e "${YELLOW}[FIX]${NC} Creating data directory..."
    mkdir -p "$DATADIR"
fi

if [ ! -d "$DATADIR/mysql" ]; then
    echo -e "${YELLOW}[WARN]${NC} Database not initialized"
    echo -e "${YELLOW}[FIX]${NC} Initializing database..."
    if command -v mariadb-install-db &> /dev/null; then
        mariadb-install-db --datadir="$DATADIR"
    else
        mysql_install_db --datadir="$DATADIR"
    fi
    echo -e "${GREEN}[OK]${NC} Database initialized"
fi

echo ""
echo -e "${CYAN}Checking for stale files that prevent startup...${NC}"

# Check for stale socket
if [ -e "$DATADIR/mysql.sock" ]; then
    echo -e "${YELLOW}[FOUND]${NC} Stale socket file: $DATADIR/mysql.sock"
    echo -e "${YELLOW}[FIX]${NC} Removing stale socket..."
    rm -f "$DATADIR/mysql.sock"
    echo -e "${GREEN}[OK]${NC} Socket removed"
fi

# Check for stale PID file
PID_FILE="$DATADIR/$HOSTNAME.pid"
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE" 2>/dev/null)
    if [ -n "$OLD_PID" ] && ! kill -0 "$OLD_PID" 2>/dev/null; then
        echo -e "${YELLOW}[FOUND]${NC} Stale PID file: $PID_FILE (PID: $OLD_PID)"
        echo -e "${YELLOW}[FIX]${NC} Removing stale PID file..."
        rm -f "$PID_FILE"
        echo -e "${GREEN}[OK]${NC} PID file removed"
    fi
fi

# Check for aria log files (common cause of crashes after unclean shutdown)
if [ -f "$DATADIR/aria_log_control" ]; then
    echo -e "${YELLOW}[FOUND]${NC} Aria log control file (can cause startup failures)"
    echo -e "${YELLOW}[FIX]${NC} Backing up and removing aria log files..."

    BACKUP_DIR="$HOME/sulfur/backups/aria_backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR" 2>/dev/null
    cp "$DATADIR"/aria_log* "$BACKUP_DIR/" 2>/dev/null
    rm -f "$DATADIR"/aria_log* 2>/dev/null
    echo -e "${GREEN}[OK]${NC} Aria logs backed up to $BACKUP_DIR and removed"
fi

# Check for corrupted InnoDB log files
if [ -f "$DATADIR/ib_logfile0" ]; then
    IB_SIZE=$(stat -c%s "$DATADIR/ib_logfile0" 2>/dev/null || echo "0")
    if [ "$IB_SIZE" = "0" ]; then
        echo -e "${YELLOW}[FOUND]${NC} Corrupted ib_logfile (zero size)"
        echo -e "${YELLOW}[FIX]${NC} Removing corrupted InnoDB log files..."
        rm -f "$DATADIR"/ib_logfile* 2>/dev/null
        echo -e "${GREEN}[OK]${NC} InnoDB logs removed"
    fi
fi

# Check for lock files
if [ -f "$DATADIR/mysql.lock" ]; then
    echo -e "${YELLOW}[FOUND]${NC} Lock file: $DATADIR/mysql.lock"
    echo -e "${YELLOW}[FIX]${NC} Removing lock file..."
    rm -f "$DATADIR/mysql.lock"
    echo -e "${GREEN}[OK]${NC} Lock file removed"
fi

# Check disk space
echo ""
echo -e "${CYAN}Checking disk space...${NC}"
AVAIL_KB=$(df "$DATADIR" 2>/dev/null | tail -1 | awk '{print $4}')
if [ -n "$AVAIL_KB" ] && [ "$AVAIL_KB" -lt 102400 ]; then
    echo -e "${RED}[ERROR]${NC} Low disk space! Only $(($AVAIL_KB / 1024)) MB available"
    echo -e "${YELLOW}[FIX]${NC} Free up some space before starting MariaDB"
else
    echo -e "${GREEN}[OK]${NC} Sufficient disk space available"
fi

# Check permissions
echo ""
echo -e "${CYAN}Checking permissions...${NC}"
if [ ! -w "$DATADIR" ]; then
    echo -e "${RED}[ERROR]${NC} Cannot write to data directory!"
    echo -e "${YELLOW}[FIX]${NC} Fixing permissions..."
    chmod -R 700 "$DATADIR" 2>/dev/null
fi
echo -e "${GREEN}[OK]${NC} Permissions look good"

# Check MariaDB error log
ERR_LOG="$DATADIR/$HOSTNAME.err"
echo ""
echo -e "${CYAN}Checking MariaDB error log...${NC}"
if [ -f "$ERR_LOG" ]; then
    echo -e "${YELLOW}[INFO]${NC} Last 20 lines of error log:"
    echo "----------------------------------------"
    tail -20 "$ERR_LOG" | sed 's/^/  /'
    echo "----------------------------------------"
else
    echo -e "${YELLOW}[INFO]${NC} No error log found (first run?)"
fi

# Check if port 3306 is in use (zombie process)
echo ""
echo -e "${CYAN}Checking if port 3306 is already in use...${NC}"
PORT_IN_USE=false
if command -v ss > /dev/null 2>&1; then
    if ss -tlnp 2>/dev/null | grep -q ":3306 "; then
        PORT_IN_USE=true
    fi
elif command -v netstat > /dev/null 2>&1; then
    if netstat -tlnp 2>/dev/null | grep -q ":3306 "; then
        PORT_IN_USE=true
    fi
fi

if [ "$PORT_IN_USE" = true ]; then
    echo -e "${RED}[ERROR]${NC} Port 3306 is already in use!"
    echo -e "${YELLOW}[INFO]${NC} This is likely a zombie MariaDB process."
    echo ""
    echo -e "${CYAN}Finding processes using port 3306...${NC}"

    # Try to find the process
    if command -v ss > /dev/null 2>&1; then
        ss -tlnp 2>/dev/null | grep ":3306 " | sed 's/^/  /'
    fi

    # Get PIDs of mariadbd/mysqld processes
    MARIA_PIDS=$(pgrep -f "mariadbd" 2>/dev/null || true)
    MYSQL_PIDS=$(pgrep -f "mysqld" 2>/dev/null || true)
    ALL_PIDS="$MARIA_PIDS $MYSQL_PIDS"
    ALL_PIDS=$(echo "$ALL_PIDS" | tr ' ' '\n' | sort -u | tr '\n' ' ')

    if [ -n "$ALL_PIDS" ] && [ "$ALL_PIDS" != " " ]; then
        echo -e "${YELLOW}[INFO]${NC} Found MariaDB/MySQL PIDs: $ALL_PIDS"
        echo -e "${YELLOW}[FIX]${NC} Killing zombie processes..."
        for pid in $ALL_PIDS; do
            if [ -n "$pid" ]; then
                echo "  Killing PID $pid..."
                kill -9 "$pid" 2>/dev/null || true
            fi
        done
        sleep 3
        echo -e "${GREEN}[OK]${NC} Zombie processes killed"
    else
        echo -e "${YELLOW}[WARN]${NC} Could not find process holding port 3306"
        echo -e "${YELLOW}[INFO]${NC} Port may be in TIME_WAIT state, waiting 5 seconds..."
        sleep 5
    fi
fi

# Attempt to start MariaDB
echo ""
echo -e "${CYAN}Attempting to start MariaDB...${NC}"

# Try mariadbd-safe first
if command -v mariadbd-safe &> /dev/null; then
    echo -e "${YELLOW}[INFO]${NC} Starting mariadbd-safe..."
    mariadbd-safe --datadir="$DATADIR" &
    DB_PID=$!

    # Wait for startup
    echo -e "${YELLOW}[INFO]${NC} Waiting for MariaDB to start (up to 15 seconds)..."
    for i in {1..15}; do
        sleep 1
        if pgrep -x mariadbd > /dev/null 2>&1; then
            echo -e "${GREEN}[OK]${NC} MariaDB process is running!"

            # Wait a bit more for socket
            sleep 2

            if mariadb -u root -e "SELECT 1;" &>/dev/null; then
                echo -e "${GREEN}[SUCCESS]${NC} MariaDB is running and accepting connections!"
                echo ""
                echo -e "${CYAN}You can now run: bash maintain_bot.sh${NC}"
                exit 0
            else
                echo -e "${YELLOW}[WARN]${NC} MariaDB started but not accepting connections yet"
                echo -e "${YELLOW}[INFO]${NC} Wait a few more seconds and try: mariadb -u root"
                exit 0
            fi
        fi
        echo -n "."
    done
    echo ""

    # Check if process died
    if ! kill -0 "$DB_PID" 2>/dev/null && ! pgrep -x mariadbd > /dev/null 2>&1; then
        echo -e "${RED}[ERROR]${NC} MariaDB process died during startup"

        # Show what happened
        if [ -f "$ERR_LOG" ]; then
            echo ""
            echo -e "${YELLOW}[INFO]${NC} Recent errors from log:"
            echo "----------------------------------------"
            tail -30 "$ERR_LOG" | sed 's/^/  /'
            echo "----------------------------------------"
        fi
    fi
fi

# If we get here, normal start failed - try recovery mode
echo ""
echo -e "${YELLOW}[INFO]${NC} Normal start failed. Trying InnoDB recovery mode..."

if command -v mariadbd-safe &> /dev/null; then
    echo -e "${YELLOW}[INFO]${NC} Starting with --innodb-force-recovery=1..."
    mariadbd-safe --datadir="$DATADIR" --innodb-force-recovery=1 &

    sleep 10

    if pgrep -x mariadbd > /dev/null 2>&1; then
        echo -e "${GREEN}[OK]${NC} MariaDB started in recovery mode!"
        echo ""
        echo -e "${YELLOW}[IMPORTANT]${NC} Database is running in recovery mode."
        echo -e "${YELLOW}[NEXT STEPS]${NC}"
        echo "  1. Back up your data: mariadb-dump -u root --all-databases > backup.sql"
        echo "  2. Stop the server: pkill mariadbd"
        echo "  3. Reset the database: rm -rf $DATADIR && mariadb-install-db"
        echo "  4. Start fresh: mariadbd-safe &"
        echo "  5. Restore data: mariadb -u root < backup.sql"
        exit 0
    fi
fi

# Last resort - offer to reset
echo ""
echo -e "${RED}[FAILED]${NC} Could not start MariaDB with any method"
echo ""
echo -e "${YELLOW}[LAST RESORT]${NC} You may need to reset the database:"
echo ""
echo "  WARNING: This will DELETE all database data!"
echo ""
echo "  1. Stop any MariaDB processes: pkill -9 mariadbd"
echo "  2. Remove data directory: rm -rf $DATADIR"
echo "  3. Reinitialize: mariadb-install-db --datadir=$DATADIR"
echo "  4. Start: mariadbd-safe &"
echo "  5. Recreate sulfur database:"
echo "     mariadb -u root -e \"CREATE DATABASE sulfur_bot;\""
echo "     mariadb -u root -e \"CREATE USER 'sulfur_bot_user'@'localhost';\""
echo "     mariadb -u root -e \"GRANT ALL ON sulfur_bot.* TO 'sulfur_bot_user'@'localhost';\""
echo ""
echo -e "${CYAN}Full error log: cat $ERR_LOG${NC}"

exit 1
