# Web Dashboard Port Conflict Fix

## Problem

The web dashboard was constantly restarting with errors indicating that port 5000 was already in use. This created an infinite restart loop where:

1. Web dashboard tries to start on port 5000
2. Port is already occupied by a previous instance
3. Dashboard fails to start with "Address already in use" error
4. Maintenance script detects the crash and tries to restart
5. Loop repeats indefinitely

## Root Causes

1. **Orphaned processes**: Previous web dashboard processes weren't properly cleaned up on crash or shutdown
2. **No port conflict detection**: The script didn't check if port 5000 was free before starting
3. **Infinite restart loops**: No crash detection to prevent repeated restart attempts
4. **Poor error messages**: Generic errors didn't indicate the port conflict issue

## Solution

### 1. Port Cleanup Function

Added `cleanup_port_5000()` function in `maintain_bot.sh` that:
- Detects processes using port 5000 using `lsof`, `ss`, or `netstat`
- Identifies if the process is a Python process (old dashboard instance)
- Kills the old process and verifies port is free
- Provides clear error messages if port can't be freed

### 2. Pre-Start Port Check

Updated `start_web_dashboard()` to:
- Call `cleanup_port_5000()` before starting the dashboard
- Show last 10 lines of web log on failure for debugging
- Fail gracefully if port can't be freed

### 3. Crash Detection

Implemented crash detection to prevent infinite restart loops:
- Tracks how long dashboard runs before crashing
- If it crashes within 10 seconds, 3 times in a row:
  - Shows last 30 lines from web dashboard log
  - Pauses restarts for 60 seconds
  - Resets crash counter after pause
- Prevents system resource exhaustion from rapid restarts

### 4. Better Error Messages

Updated `web_dashboard.py` to:
- Specifically catch `OSError` for "Address already in use"
- Display clear error message indicating port conflict
- Exit with proper error code for maintenance script

### 5. Cleanup on Shutdown

Enhanced `cleanup()` function to:
- Call `cleanup_port_5000()` during shutdown
- Ensure port is free for next start
- Prevent orphaned processes

## Files Changed

1. **maintain_bot.sh**
   - Added `cleanup_port_5000()` function
   - Updated `start_web_dashboard()` to check port first
   - Added web dashboard crash detection
   - Enhanced cleanup() to free port 5000
   - Added variables: `WEB_CRASH_COUNT`, `WEB_CRASH_THRESHOLD`

2. **web_dashboard.py**
   - Added specific OSError handling for port conflicts
   - Better error messages
   - Proper exit codes

## Testing

All changes were validated with integration tests:
- ✅ Port cleanup function works with real processes
- ✅ Crash detection prevents infinite loops
- ✅ Scripts have valid syntax
- ✅ Error messages are clear and actionable

## Usage

No changes required for normal usage. The fix is automatic and transparent:

1. **Clean start**: Port is checked and cleaned before starting
2. **After crash**: Port is automatically freed and dashboard restarts
3. **Repeated crashes**: System pauses, shows logs, and waits before retry
4. **Shutdown**: Port is cleaned up for next start

## Manual Port Cleanup (if needed)

If you need to manually free port 5000:

```bash
# Find process using port 5000
lsof -ti:5000

# Kill the process
kill -9 $(lsof -ti:5000)
```

Or use the built-in cleanup:
```bash
# The maintenance script will automatically clean it on next start
./maintain_bot.sh
```

## Logs

When port conflicts occur, you'll see messages like:

```
[WEB] Checking if port 5000 is already in use...
[!] Port 5000 is in use by PID: 12345
[!] Killing old web dashboard process (PID: 12345)...
[✓] Port 5000 is now available
[WEB] Starting Web Dashboard...
[✓] Web Dashboard running at http://localhost:5000 (PID: 12346)
```

If crashes occur repeatedly:
```
[!] Web Dashboard stopped, checking if it's crashing repeatedly...
[!] Web Dashboard crash #1 (ran for only 2 seconds)
[!] Web Dashboard crash #2 (ran for only 1 seconds)
[!] Web Dashboard crash #3 (ran for only 1 seconds)
[✗] Web Dashboard is crashing repeatedly (3 times)
[✗] Last 30 lines from web dashboard log:
  [Web Dashboard] FATAL ERROR: Port 5000 is already in use!
  ...
[!] Pausing web dashboard restarts for 60 seconds...
```

## Troubleshooting

### Port still in use after cleanup

If port 5000 is still occupied by a non-Python process:

1. Find what's using it:
   ```bash
   lsof -i:5000
   ```

2. Stop that service or change the web dashboard port in `web_dashboard.py`:
   ```python
   socketio.run(app, host='0.0.0.0', port=5001, ...)  # Changed from 5000 to 5001
   ```

### Dashboard keeps crashing

Check the web dashboard log for errors:
```bash
tail -f logs/web_*.log
```

Common issues:
- Missing Python dependencies: `pip install -r requirements.txt`
- Database connection issues: Check MySQL is running
- File permission issues: Ensure web/ directory is readable

## Benefits

1. **Reliability**: Dashboard starts successfully even after crashes
2. **Self-healing**: Automatically cleans up orphaned processes
3. **Resource protection**: Prevents infinite restart loops
4. **Better diagnostics**: Clear error messages for troubleshooting
5. **Termux compatible**: Works on all platforms (Linux, Termux, etc.)
