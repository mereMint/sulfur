# Quick Reference: Port 5000 Fix

## What Was Fixed
Web dashboard could not restart due to "Port 5000 already in use" error.

## Why It Happened
- Previous process left port in TIME_WAIT state (60s on Linux)
- Port check used SO_REUSEADDR (passed)
- Flask binding didn't use SO_REUSEADDR (failed)

## The Solution
1. Configure Flask socket with SO_REUSEADDR + SO_REUSEPORT
2. Add retry logic (5 attempts, exponential backoff)
3. Improve maintenance script port handling

## Key Changes
- `web_dashboard.py`: Added socket options and retry logic
- `maintain_bot.sh`: Distinguish active processes from TIME_WAIT
- Tests: Automated validation scripts

## Testing
```bash
# Run tests
python3 test_port_reuse.py
python3 test_web_dashboard_restart.py

# Manual test
./maintain_bot.sh
# Press Ctrl+C
./maintain_bot.sh  # Should start immediately
```

## If Issues Persist
```bash
# Check what's using port 5000
lsof -i:5000
ss -tlnp | grep :5000

# Kill process manually
kill -9 $(lsof -ti:5000)
```

## Technical Details
See `docs/WEB_DASHBOARD_PORT_FIX.md` for full explanation.
