# Port Cleanup Fix - Quick Reference

## Problem
```
Web Dashboard tries to start
        ↓
Port 5000 already in use
        ↓
Dashboard crashes immediately
        ↓
Maintenance script detects crash
        ↓
Waits 30 seconds (cooldown)
        ↓
Tries to restart dashboard
        ↓
Port 5000 STILL in use
        ↓
CRASH LOOP ♻️
```

## Solution
```
Web Dashboard startup requested
        ↓
Check if port 5000 available
        ↓
    ┌───────┴───────┐
    │ Available?    │
    └───┬───────┬───┘
        │       │
       Yes     No
        │       │
        │       └──→ show_port_info()
        │              ↓
        │            Identify blocking process
        │              ↓
        │            free_port() with retries
        │              ↓
        │            ┌─────────────────┐
        │            │ Attempt 1 of 3  │
        │            │ - SIGTERM       │
        │            │ - Wait 3s       │
        │            │ - SIGKILL       │
        │            │ - Wait 2s       │
        │            └────────┬────────┘
        │                     │
        │            ┌────────┴────────┐
        │            │ Port free now?  │
        │            └────┬───────┬────┘
        │                Yes     No
        │                 │       │
        │                 │       └──→ Attempt 2 (wait 4s)
        │                 │              ↓
        │                 │            Attempt 3 (wait 6s)
        │                 │              ↓
        │                 │            Give up & report error
        │                 │
        └─────────────────┘
        │
Double-check port is free
        ↓
Start web dashboard process
        ↓
Monitor startup for 30 seconds
        ↓
    ┌───────┴───────┐
    │ Responding?   │
    └───┬───────┬───┘
       Yes     No
        │       │
    SUCCESS   Show error & retry
```

## Key Commands

### Find what's using port 5000
```bash
# Method 1: lsof (most detailed)
lsof -i:5000

# Method 2: ss (modern Linux)
ss -tlnp | grep :5000

# Method 3: netstat (legacy)
netstat -tulnp | grep :5000

# Method 4: fuser (simple)
fuser 5000/tcp
```

### Manual port cleanup
```bash
# Find and kill in one command
kill -9 $(lsof -ti:5000)

# Or step by step
lsof -ti:5000          # Get PID
kill -TERM <PID>       # Try graceful shutdown
sleep 3
kill -9 <PID>          # Force kill if still alive
```

### Check for TIME_WAIT
```bash
ss -tan | grep :5000 | grep TIME-WAIT
```

## Error Messages Decoded

### "Port 5000 is already in use"
**Cause**: Another process has port 5000 open  
**Fix**: Automatic (script will retry 3 times with increasing delays)

### "Port 5000 is still in use after cleanup attempt"
**Cause**: Process won't die or port stuck in TIME_WAIT  
**Fix**: Script will show which process and retry

### "No processes found using port 5000 (port might be in TIME_WAIT state)"
**Cause**: Port recently closed, kernel holding it for 60-120 seconds  
**Fix**: Script waits and retries automatically

### "Failed to free port 5000 after 3 attempts"
**Cause**: Persistent process or system issue  
**Action Required**: Check logs, kill process manually, or reboot

## Testing

Run the test script to verify functionality:
```bash
./test_port_cleanup.sh
```

Expected output:
```
✓ Port 5000 is available
✓ Port 5000 is correctly detected as in use
✓ Port 5000 is available after killing process
✓ Python can bind to port 5000
```

## Troubleshooting

### Web dashboard still won't start?

1. **Check the logs**:
   ```bash
   tail -50 logs/web_*.log | grep -i error
   ```

2. **Manually check port**:
   ```bash
   lsof -i:5000
   ```

3. **Force cleanup**:
   ```bash
   pkill -9 -f web_dashboard.py
   sleep 5
   ./maintain_bot.sh
   ```

4. **Check system limits**:
   ```bash
   ulimit -n  # Should be > 1024
   ```

5. **Verify Python dependencies**:
   ```bash
   venv/bin/python -c "import flask, flask_socketio"
   ```

### Multiple web dashboards running?

```bash
# Find all Python processes in this directory
ps aux | grep python | grep "$(pwd)"

# Kill all orphaned Python processes
pkill -9 -f "python.*$(pwd)"
```

### Port in TIME_WAIT state?

This is normal after killing a process. The kernel holds the port for 60-120 seconds.

**Option 1**: Wait (recommended)  
**Option 2**: Enable SO_REUSEADDR (already done in code)  
**Option 3**: Change to different port in web_dashboard.py

## Configuration

To change the web dashboard port (if 5000 conflicts):

1. Edit `web_dashboard.py`:
   ```python
   # Change this line (appears twice)
   socketio.run(app, host='0.0.0.0', port=5000, ...)
   # To:
   socketio.run(app, host='0.0.0.0', port=8080, ...)
   ```

2. Edit `maintain_bot.sh`:
   ```bash
   # Change all instances of 5000 to your new port
   check_port_available 5000  →  check_port_available 8080
   free_port 5000  →  free_port 8080
   ```

## Performance Notes

- Port cleanup adds 2-12 seconds to startup time (only when port is in use)
- Each retry attempt increases wait time: 2s → 4s → 6s
- Total maximum delay: ~15 seconds for 3 failed attempts
- Zero delay when port is available (normal case)

## Files Modified

| File | Changes | Purpose |
|------|---------|---------|
| `maintain_bot.sh` | +165 lines | Port cleanup logic |
| `web_dashboard.py` | +40 lines | Error reporting |
| `test_port_cleanup.sh` | +130 lines | Automated testing |
| `PORT_CLEANUP_FIX_SUMMARY.md` | New | Full documentation |
| `PORT_CLEANUP_QUICK_REF.md` | New | This file |

---

**Quick Help**: If the web dashboard won't start, check `logs/web_*.log` for the specific error, then use `lsof -i:5000` to see what's blocking the port.
