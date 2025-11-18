# Web Dashboard Port 5000 Conflict Fix - Implementation Summary

## Problem Statement

The web dashboard was experiencing a crash loop due to port 5000 being already in use. The issue manifested as:

1. Web dashboard starts and immediately crashes with "Port 5000 is already in use"
2. Maintenance script detects the crash and tries to restart after a cooldown
3. The same error occurs, creating an endless crash loop
4. Users see repeated error messages in logs but cannot access the web dashboard

### Root Cause Analysis

The issue was caused by:

1. **Insufficient port cleanup** - The `free_port()` function didn't retry or wait long enough for ports in TIME_WAIT state
2. **No process detection** - Error messages didn't show which process was blocking the port
3. **Race conditions** - Port cleanup happened too early, and the port could be re-occupied before the web dashboard started
4. **Limited error context** - Both the shell script and Python code had minimal error reporting

## Solution Overview

We implemented a comprehensive fix with three main components:

### 1. Enhanced Port Detection and Cleanup (maintain_bot.sh)

#### New `show_port_info()` Function
- Shows detailed information about processes using a port
- Uses lsof, ss, or netstat (whichever is available)
- Displays process command lines for easier debugging
- Detects TIME_WAIT connections

#### Improved `free_port()` Function
- **Retry logic**: Up to 3 attempts to free the port
- **Exponential backoff**: 2s, 4s, 6s between attempts
- **Better process detection**: Shows process command and PID
- **Graceful shutdown**: Tries SIGTERM first, then SIGKILL
- **Verification**: Checks port availability after each attempt
- **TIME_WAIT detection**: Identifies and handles ports in TIME_WAIT state

#### Enhanced `start_web_dashboard()` Function
- **Stale PID cleanup**: Removes PID files for dead processes
- **Pre-start port check**: Always checks port availability before starting
- **Multiple cleanup attempts**: Calls `free_port()` with retry limit
- **Double verification**: Confirms port is free before launching dashboard
- **Better error reporting**: Shows which process is blocking and why startup failed
- **Detailed logging**: Logs each step of the startup process

### 2. Better Error Reporting (web_dashboard.py)

#### New `find_process_on_port()` Function
- Attempts to identify which process is using port 5000
- Uses lsof, ss, or netstat with subprocess calls
- Returns process information for display in error messages
- Has timeout protection to avoid hanging

#### Enhanced Port Checking
- **SO_REUSEADDR**: Sets socket option for better cleanup
- **Process detection**: Shows blocking process in error messages
- **Better context**: Provides actionable troubleshooting steps
- **Multiple detection methods**: Falls back through lsof → ss → netstat

### 3. Testing Infrastructure

Created `test_port_cleanup.sh` to verify:
- Port availability detection works correctly
- Port in-use detection works correctly
- Port cleanup after process termination
- Python socket binding behavior

## Technical Details

### Port Cleanup State Machine

```
1. Check if port is available
   ├─ Available → Proceed to start
   └─ In use → Go to step 2

2. Identify processes using port
   ├─ PIDs found → Go to step 3
   └─ No PIDs (TIME_WAIT) → Wait and retry

3. Terminate processes (attempt N of 3)
   ├─ Send SIGTERM, wait 3s
   ├─ Send SIGKILL if still alive
   └─ Wait 2*N seconds

4. Verify port is free
   ├─ Free → Success
   └─ Still in use → Retry from step 2 (if attempts remain)
```

### Exponential Backoff Strategy

| Attempt | Wait After Kill | Total Wait Time |
|---------|----------------|-----------------|
| 1       | 2 seconds      | 2 seconds       |
| 2       | 4 seconds      | 6 seconds       |
| 3       | 6 seconds      | 12 seconds      |

This ensures adequate time for:
- Graceful process shutdown
- Port release from kernel
- TIME_WAIT expiration (if applicable)

## Code Changes

### maintain_bot.sh

1. **Lines 419-451**: Added `show_port_info()` function
2. **Lines 453-520**: Rewrote `free_port()` with retry logic
3. **Lines 522-755**: Enhanced `start_web_dashboard()` function

### web_dashboard.py

1. **Lines 766-801**: Added `find_process_on_port()` function
2. **Lines 776-807**: Enhanced port checking and error reporting

## Testing Results

The test script (`test_port_cleanup.sh`) successfully verified:

✓ Port 5000 availability detection  
✓ Port in-use detection with active server  
✓ Port cleanup after process termination  
✓ Python socket binding with SO_REUSEADDR  

All tests passed successfully.

## Security Considerations

- **CodeQL Analysis**: Passed with 0 alerts
- **Command Injection**: All subprocess calls use proper quoting
- **Process Signals**: Graceful SIGTERM before SIGKILL
- **Timeout Protection**: Subprocess calls have timeout limits
- **Permission Checks**: No privilege escalation required

## Benefits

1. **Reliability**: Automatic recovery from port conflicts
2. **Debuggability**: Clear error messages showing what's blocking the port
3. **Robustness**: Handles edge cases like TIME_WAIT and stale PIDs
4. **User Experience**: Provides actionable troubleshooting steps
5. **Maintenance**: Reduced need for manual intervention

## Usage

The fix is automatic and requires no user action. If port conflicts occur:

1. The maintenance script will automatically detect and free the port
2. Error messages will show which process was blocking
3. Up to 3 automatic retry attempts with increasing delays
4. Clear logging of each step for troubleshooting

## Recommendations

1. **Monitor logs** for recurring port conflicts (may indicate another issue)
2. **Check for rogue processes** if conflicts persist after 3 retries
3. **Verify network configuration** if TIME_WAIT states are common
4. **Consider port randomization** if port 5000 conflicts are frequent

## Future Enhancements

Potential improvements for future versions:

1. Make port configurable via environment variable
2. Add automatic port selection if 5000 is persistently unavailable
3. Implement health checks to detect zombie processes earlier
4. Add metrics for port conflict frequency
5. Create alerting for repeated failures

## Files Modified

- `maintain_bot.sh` - Enhanced port cleanup and web dashboard startup
- `web_dashboard.py` - Improved error reporting and process detection
- `test_port_cleanup.sh` - New test script for verification

## Compatibility

- **Linux**: Full support (tested)
- **Termux**: Full support
- **macOS**: Compatible (different errno codes handled)
- **Dependencies**: Uses standard Unix utilities (lsof, ss, netstat)

## Rollback Plan

If issues arise, revert to previous version:
```bash
git checkout HEAD~1 maintain_bot.sh web_dashboard.py
```

The old behavior can be restored by removing retry logic from `free_port()`.

---

**Status**: ✅ Complete and Tested  
**Security**: ✅ CodeQL Passed (0 alerts)  
**Testing**: ✅ All tests passed  
**Documentation**: ✅ Complete
