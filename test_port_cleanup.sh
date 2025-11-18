#!/bin/bash
# Test script for port cleanup functionality

echo "=== Port Cleanup Test ==="
echo ""

# Source the functions we need from maintain_bot.sh
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# Define minimal logging functions for testing
log_info() { echo "[INFO] $1"; }
log_warning() { echo "[WARN] $1"; }
log_error() { echo "[ERROR] $1"; }
log_success() { echo "[OK] $1"; }

# Source the port checking functions
# We'll extract just the functions we need

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
    
    return 0  # Port is available
}

echo "Test 1: Check if port 5000 is currently available"
if check_port_available 5000; then
    echo "✓ Port 5000 is available"
else
    echo "✗ Port 5000 is in use"
    
    # Show what's using it
    echo ""
    echo "Processes using port 5000:"
    if command -v lsof >/dev/null 2>&1; then
        lsof -i:5000 2>/dev/null || echo "  (none found with lsof)"
    fi
    
    if command -v ss >/dev/null 2>&1; then
        ss -tlnp 2>/dev/null | grep ":5000 " || echo "  (none found with ss)"
    fi
fi

echo ""
echo "Test 2: Start a simple HTTP server on port 5000 to simulate the problem"
python3 -m http.server 5000 >/dev/null 2>&1 &
TEST_SERVER_PID=$!
sleep 2

if check_port_available 5000; then
    echo "✗ Port check failed - port should be in use but reports as available"
    kill $TEST_SERVER_PID 2>/dev/null
    exit 1
else
    echo "✓ Port 5000 is correctly detected as in use"
    
    # Show what's using it
    echo ""
    echo "Process using port 5000:"
    if command -v lsof >/dev/null 2>&1; then
        lsof -i:5000 2>/dev/null | grep -v COMMAND
    fi
fi

echo ""
echo "Test 3: Kill the test server and verify port is freed"
kill $TEST_SERVER_PID 2>/dev/null
sleep 2

if check_port_available 5000; then
    echo "✓ Port 5000 is available after killing process"
else
    echo "✗ Port 5000 is still in use after killing process"
    
    # Show what's still using it
    if command -v lsof >/dev/null 2>&1; then
        lsof -i:5000 2>/dev/null
    fi
    
    # This might be TIME_WAIT, let's check
    if command -v ss >/dev/null 2>&1; then
        echo ""
        echo "Checking for TIME_WAIT connections:"
        ss -tan 2>/dev/null | grep ":5000 " | grep TIME-WAIT
    fi
fi

echo ""
echo "Test 4: Test Python socket binding (similar to web_dashboard.py)"
python3 << 'EOF'
import socket
import sys

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

try:
    sock.bind(('0.0.0.0', 5000))
    sock.close()
    print("✓ Python can bind to port 5000")
    sys.exit(0)
except OSError as e:
    print(f"✗ Python cannot bind to port 5000: {e}")
    sys.exit(1)
EOF

echo ""
echo "=== Test Complete ==="
