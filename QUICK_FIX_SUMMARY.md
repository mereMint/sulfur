# Web Dashboard Port 5000 Fix - Quick Reference

## Problem
Web dashboard was restarting in an infinite loop with error:
```
[!] Web Dashboard stopped, restarting...
Port 5000 is already in use by another program or process
```

## Solution
Added automatic port detection and cleanup before starting web dashboard.

## What Changed

### 1. `maintain_bot.sh`
- **New function**: `check_port_available(port)` - Detects if port is in use
- **New function**: `free_port(port)` - Kills processes using the port
- **Modified**: `start_web_dashboard()` - Now checks and frees port 5000 before starting

### 2. `web_dashboard.py`
- Added port availability check before binding
- Enhanced error messages with troubleshooting instructions

## How It Works

Before starting the web dashboard, the script now:

1. ✅ Checks if port 5000 is available
2. ✅ If occupied, finds the process using it
3. ✅ Attempts graceful shutdown (TERM signal)
4. ✅ Forces kill if needed (KILL signal)
5. ✅ Waits for port to be freed
6. ✅ Starts web dashboard on clean port

## Testing

All tests passed:
- ✅ Port detection works correctly
- ✅ Port cleanup terminates processes
- ✅ Web dashboard starts successfully
- ✅ No restart loop occurs

## Manual Fix (if needed)

If the automatic fix doesn't work, you can manually free port 5000:

```bash
# Find what's using port 5000
lsof -ti:5000

# Kill it
kill -9 $(lsof -ti:5000)

# Or use fuser (alternative)
fuser -k 5000/tcp
```

## Files Modified

- `maintain_bot.sh` - Port management functions
- `web_dashboard.py` - Port check before starting
- `docs/WEB_DASHBOARD_PORT_FIX.md` - Detailed documentation

## Deployment

Simply pull the latest changes and run:
```bash
git pull
./maintain_bot.sh
```

The fix will automatically handle any port conflicts.

## Future Updates

The web dashboard will now:
- ✅ Never enter restart loops due to port conflicts
- ✅ Automatically clean up orphaned processes
- ✅ Provide clear error messages
- ✅ Work reliably on Termux, Linux, macOS, WSL

---

**Status**: ✅ **COMPLETE AND TESTED**

For detailed technical information, see `docs/WEB_DASHBOARD_PORT_FIX.md`
