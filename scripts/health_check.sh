#!/bin/bash
# ==============================================================================
# Sulfur Bot - Health Check Script
# ==============================================================================
# Checks database connectivity and required tables
# Usage: bash scripts/health_check.sh
# ==============================================================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Change to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT" || exit 1

echo "============================================================================"
echo "  Sulfur Bot - Health Check"
echo "============================================================================"
echo ""

# Check Python availability
if ! command -v python3 >/dev/null 2>&1 && ! command -v python >/dev/null 2>&1; then
    echo -e "${RED}✗ Python not found${NC}"
    exit 1
fi

# Use venv python if available
if [ -f "venv/bin/python" ]; then
    PYTHON="venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON="python3"
else
    PYTHON="python"
fi

# Check database configuration
echo -n "Checking database configuration... "
if $PYTHON -c "
from modules.database_config import DatabaseConfig
try:
    config = DatabaseConfig.load()
    print('OK')
    exit(0)
except Exception as e:
    print(f'FAIL: {e}')
    exit(1)
" 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    echo ""
    echo "Database configuration is missing or invalid."
    echo "Run: bash scripts/setup_database_secure.sh"
    exit 1
fi

# Check database connection
echo -n "Checking database connection... "
if $PYTHON -c "
from modules.database_config import DatabaseConfig
import sys

try:
    # Try importing mysql connector
    try:
        import mysql.connector
        connector_available = True
    except ImportError:
        connector_available = False
    
    if connector_available:
        conn_params = DatabaseConfig.get_connection_params()
        conn = mysql.connector.connect(**conn_params)
        conn.close()
        print('OK')
        sys.exit(0)
    else:
        print('FAIL: mysql-connector-python not installed')
        sys.exit(1)
except Exception as e:
    print(f'FAIL: {e}')
    sys.exit(1)
" 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    echo ""
    echo "Cannot connect to database. Check that MariaDB/MySQL is running."
    exit 1
fi

# Check required tables
echo -n "Checking required tables... "
if $PYTHON -c "
from modules.database_config import DatabaseConfig
import mysql.connector
import sys

required_tables = [
    'user_stats',
    'user_economy',
    'feature_unlocks',
    'shop_purchases',
    'daily_quests',
    'gambling_stats',
    'transaction_history'
]

try:
    conn_params = DatabaseConfig.get_connection_params()
    conn = mysql.connector.connect(**conn_params)
    cursor = conn.cursor()
    
    missing_tables = []
    for table in required_tables:
        cursor.execute(f\"SHOW TABLES LIKE '{table}'\")
        if cursor.fetchone() is None:
            missing_tables.append(table)
    
    cursor.close()
    conn.close()
    
    if missing_tables:
        print(f'FAIL: Missing tables: {', '.join(missing_tables)}')
        sys.exit(1)
    else:
        print('OK')
        sys.exit(0)
except Exception as e:
    print(f'FAIL: {e}')
    sys.exit(1)
" 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    echo ""
    echo "Some required tables are missing."
    echo "Run: python apply_migration.py"
    exit 1
fi

# All checks passed
echo ""
echo -e "${GREEN}============================================================================${NC}"
echo -e "${GREEN}  ✓ All Health Checks Passed${NC}"
echo -e "${GREEN}============================================================================${NC}"
echo ""
exit 0
