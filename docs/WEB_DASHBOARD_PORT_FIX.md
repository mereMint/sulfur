# Web Dashboard Port 5000 Restart Loop Fix

## Problem Description

The Sulfur Discord Bot's web dashboard was entering an infinite restart loop when the maintenance script (`maintain_bot.sh`) attempted to start it. The logs showed a pattern like this:

```
[2025-11-18 06:21:37] [WEB] Starting Web Dashboard...
[2025-11-18 06:21:39] [✓] Web Dashboard running at http://localhost:5000 (PID: 23294)
[2025-11-18 06:21:39] [!] Web Dashboard stopped, restarting...
[2025-11-18 06:21:39] [WEB] Starting Web Dashboard...
[2025-11-18 06:21:41] [✓] Web Dashboard running at http://localhost:5000 (PID: 23380)
[2025-11-18 06:21:42] [!] Web Dashboard stopped, restarting...
```

The web dashboard log indicated that port 5000 was already in use by another process, causing the web dashboard to fail immediately after starting.

## Root Cause

The `start_web_dashboard()` function in `maintain_bot.sh` did not check if port 5000 was available before attempting to start the web dashboard. When a previous instance failed to shut down cleanly, or another process was using the port, the new instance would crash immediately, triggering the restart logic in an infinite loop.

## Solution

### 1. Port Availability Detection

Added `check_port_available()` function that uses multiple methods to detect if a port is in use:

```bash
check_port_available() {
    local port=$1
    
    # Method 1: lsof (most reliable)
    if command -v lsof >/dev/null 2>&1; then
        if lsof -ti:$port >/dev/null 2>&1; then
            return 1  # Port is in use
        fi
    fi
    
    # Method 2: netstat (fallback)
    if command -v netstat >/dev/null 2>&1; then
        if netstat -tuln 2>/dev/null | grep -q ":$port "; then
            return 1  # Port is in use
        fi
    fi
    
    # Method 3: ss (modern Linux)
    if command -v ss >/dev/null 2>&1; then
        if ss -tuln 2>/dev/null | grep -q ":$port "; then
            return 1  # Port is in use
        fi
    fi
    
    # Method 4: nc (last resort)
    if command -v nc >/dev/null 2>&1; then
        if nc -z 127.0.0.1 $port 2>/dev/null; then
            return 1  # Port is in use
        fi
    fi
    
    return 0  # Port is available
}
```

### 2. Port Cleanup

Added `free_port()` function that safely kills processes using the port:

```bash
free_port() {
    local port=$1
    log_warning "Attempting to free port $port..."
    
    # Find PIDs using the port
    local pids=""
    if command -v lsof >/dev/null 2>&1; then
        pids=$(lsof -ti:$port 2>/dev/null)
    elif command -v fuser >/dev/null 2>&1; then
        pids=$(fuser $port/tcp 2>/dev/null | sed 's/^ *//')
    fi
    
    if [ -n "$pids" ]; then
        for pid in $pids; do
            # Graceful shutdown first (TERM signal)
            kill -TERM "$pid" 2>/dev/null
            
            # Wait up to 3 seconds
            local wait_count=0
            while [ $wait_count -lt 3 ]; do
                if ! kill -0 "$pid" 2>/dev/null; then
                    break
                fi
                sleep 1
                wait_count=$((wait_count + 1))
            done
            
            # Force kill if still running
            if kill -0 "$pid" 2>/dev/null; then
                kill -9 "$pid" 2>/dev/null
            fi
        done
        
        # Wait for port to be released
        sleep 2
    fi
}
```

### 3. Pre-flight Check in Web Dashboard Startup

Modified `start_web_dashboard()` to check and free the port before starting:

```bash
start_web_dashboard() {
    log_web "Starting Web Dashboard..."
    
    # Check if port 5000 is available
    if ! check_port_available 5000; then
        log_warning "Port 5000 is already in use"
        
        # Try to free the port
        if ! free_port 5000; then
            log_error "Failed to free port 5000. Web Dashboard cannot start."
            return 1
        fi
    fi
    
    # ... rest of function
}
```

### 4. Enhanced Error Messages

#### In `web_dashboard.py`:

Added explicit port availability check with helpful error messages:

```python
# Check if port 5000 is available before starting
import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    sock.bind(('0.0.0.0', 5000))
    sock.close()
    print("[Web Dashboard] Port 5000 is available")
except OSError as e:
    if e.errno == 98 or e.errno == 48:  # Address already in use
        print(f"[Web Dashboard] FATAL ERROR: Port 5000 is already in use")
        print(f"[Web Dashboard] To find the process: lsof -ti:5000")
        print(f"[Web Dashboard] To kill it: kill -9 $(lsof -ti:5000)")
        exit(1)
```

#### In `maintain_bot.sh`:

Enhanced restart logic to show error logs before retrying:

```bash
# Show the last error from web log before restarting
if [ -f "$WEB_LOG" ] && [ $WEB_RESTART_COUNT -gt 0 ]; then
    log_warning "Last error from Web Dashboard log:"
    tail -n 20 "$WEB_LOG" | grep -i -E "error|exception|traceback|failed|port.*in use" \
        | tail -n 5 | sed 's/^/  | /' | tee -a "$MAIN_LOG"
fi
```

## Testing

### Unit Tests

1. **Port Detection Test**: Verified `check_port_available()` works with lsof, netstat, ss, and nc
2. **Port Cleanup Test**: Verified `free_port()` successfully kills processes and frees ports
3. **Python Socket Test**: Verified Python socket binding error detection

### Integration Tests

1. Started dummy HTTP server on port 5000
2. Verified port detection functions correctly identify it
3. Verified port cleanup functions successfully terminate it
4. Verified port is free after cleanup

All tests passed successfully.

## Benefits

1. **Prevents Restart Loops**: Web dashboard won't restart repeatedly if port is occupied
2. **Automatic Recovery**: Automatically cleans up orphaned processes using port 5000
3. **Better Diagnostics**: Clear error messages help users troubleshoot issues
4. **Graceful Shutdown**: Attempts TERM signal before forcing KILL
5. **Multiple Fallbacks**: Uses multiple tools (lsof, netstat, ss, nc) for maximum compatibility

## Manual Intervention

If automatic cleanup fails, users can manually free the port:

```bash
# Find processes using port 5000
lsof -ti:5000

# Kill the process
kill -9 $(lsof -ti:5000)

# Or use fuser (alternative)
fuser -k 5000/tcp
```

## Compatibility

- **Linux**: Tested with lsof, netstat, ss, nc
- **Termux (Android)**: Compatible with Termux environment
- **macOS**: Should work (errno 48 for port in use)
- **WSL**: Should work (same as Linux)

## Files Modified

1. `maintain_bot.sh`:
   - Added `check_port_available()` function
   - Added `free_port()` function
   - Modified `start_web_dashboard()` to check/free port
   - Enhanced restart logging

2. `web_dashboard.py`:
   - Added socket binding check before starting server
   - Enhanced error messages for port conflicts

## Future Improvements

1. Make port number configurable via environment variable
2. Add retry logic with exponential backoff
3. Add monitoring/alerting for repeated failures
4. Consider using Unix domain sockets as alternative to TCP port
