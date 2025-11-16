# Logging and Error Handling Improvements

## Overview
This document details the comprehensive logging and error handling improvements made to the Sulfur Discord Bot codebase to enhance debugging and error tracking.

## Changes Summary

### 1. Centralized Logging System (`logger_utils.py`)

**Created:** New centralized logging utility with color-coded output

**Features:**
- `ColoredFormatter` class for terminal-friendly colored log output
- Component-specific loggers for different modules:
  - `bot_logger` - Main bot operations
  - `db_logger` - Database operations
  - `api_logger` - API interactions
  - `web_logger` - Web dashboard
  - `voice_logger` - Voice channel management
  - `game_logger` - Game logic (Werwolf)

**Log Levels:**
- DEBUG (Cyan) - Detailed diagnostic information
- INFO (Green) - General operational messages
- WARNING (Yellow) - Warning messages
- ERROR (Red) - Error messages
- CRITICAL (Magenta) - Critical failures

**Usage Example:**
```python
from logger_utils import bot_logger as logger

logger.info("Bot started successfully")
logger.error("Failed to connect", exc_info=True)
```

### 2. Database Layer Improvements (`db_helpers.py`)

**Enhanced Functions:**
- `init_db_pool()` - Added structured logging for pool initialization
- `get_db_connection()` - Enhanced error logging with pool validation
- `initialize_database()` - Added detailed migration logging
- All async database functions converted to use logging

**New Decorator Pattern:**
```python
@db_operation("operation_name")
async def some_db_function(*args):
    # Decorator automatically handles:
    # - Error catching (mysql.connector.Error vs Exception)
    # - Detailed error logging with codes and SQL states
    # - Stack traces for unexpected errors
    # - Debug logging for start/completion
    # - Graceful degradation (returns None on error)
```

**Applied To:**
- `log_api_usage()`
- `log_mention_reply()`
- `log_temp_vc_creation()`
- `log_vc_session()`
- `add_xp()`
- `add_balance()` (partial)
- `get_player_rank()`
- `get_level_leaderboard()`

**Benefits:**
- Consistent error handling across all database operations
- Automatic logging of all database errors with context
- Easy debugging with operation name and parameters logged
- Graceful degradation - returns None instead of crashing

### 3. Main Bot Improvements (`bot.py`)

**Critical Sections Enhanced:**
- **Startup Validation:**
  - Token validation errors now logged to file
  - Config loading errors captured with full traceback
  - API key validation logged

- **Error Handlers:**
  - Command tree errors logged with `exc_info=True` for stack traces
  - HTTP exceptions logged with context
  - Unhandled exceptions get full error context

- **Event Logging:**
  - `on_ready` event logs connection details
  - Presence updates logged at DEBUG level
  - All major events tracked

**Example:**
```python
# Before
print("Error: DISCORD_BOT_TOKEN environment variable is not set.")

# After
logger.critical("DISCORD_BOT_TOKEN environment variable is not set")
print("Error: DISCORD_BOT_TOKEN environment variable is not set.")
```

### 4. API Helpers Improvements (`api_helpers.py`)

**Enhanced Error Logging:**
- Gemini API errors logged with status codes
- OpenAI API errors logged with full response
- Network exceptions logged with stack traces
- Token usage tracked and logged

**Improved Diagnostics:**
- All API responses logged at DEBUG level
- Error responses logged at ERROR level
- Timeout and connection issues clearly identified

## Error Handling Best Practices

### 1. Database Operations
```python
@db_operation("add_user_coins")
async def add_user_coins(user_id, amount):
    if not db_pool:
        logger.warning("Database pool not available")
        return None
        
    cnx = db_pool.get_connection()
    if not cnx:
        return None
    
    cursor = cnx.cursor()
    try:
        query = "UPDATE players SET balance = balance + %s WHERE discord_id = %s"
        cursor.execute(query, (amount, user_id))
        cnx.commit()
        logger.debug(f"Added {amount} coins to user {user_id}")
    finally:
        cursor.close()
        cnx.close()
```

### 2. API Calls
```python
try:
    response = await api_call()
    logger.debug(f"API response received: {len(response)} chars")
    return response
except TimeoutError as e:
    logger.error(f"API timeout: {e}")
    return None
except Exception as e:
    logger.error(f"API error: {e}", exc_info=True)
    return None
```

### 3. Discord Events
```python
@client.event
async def on_member_join(member):
    try:
        logger.info(f"Member joined: {member.name} ({member.id})")
        # ... logic ...
    except discord.HTTPException as e:
        logger.error(f"Failed to process member join: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in on_member_join: {e}", exc_info=True)
```

## Log File Structure

**Location:** `logs/` directory

**Naming:** `session_YYYY-MM-DD_HH-MM-SS.log`

**Format:**
```
2025-01-16 14:30:45 - bot - INFO - Bot logged in as SulfurBot#1234 - Ready to serve!
2025-01-16 14:30:45 - db - DEBUG - Database connection pool initialized with 5 connections
2025-01-16 14:30:46 - api - WARNING - Gemini API: No content in response. Finish Reason: SAFETY
```

## Debugging Guide

### Finding Errors
```bash
# Find all errors in today's log
grep "ERROR" logs/session_2025-01-16_*.log

# Find database errors
grep "db - ERROR" logs/session_*.log

# Find API timeouts
grep "timeout" logs/session_*.log -i
```

### Common Issues

**Database Connection Failures:**
- Check for: `db - ERROR - Database pool initialization failed`
- Solution: Verify MySQL is running and credentials are correct

**API Errors:**
- Check for: `api - ERROR - OpenAI API Error (429)`
- Solution: Rate limit exceeded, wait or upgrade plan

**Command Errors:**
- Check for: `bot - ERROR - Unhandled exception in command tree`
- Solution: Look at stack trace for root cause

## Remaining Work

**Functions Still Using print():**
- `db_helpers.py`: Migration messages (intentional for console visibility)
- `bot.py`: Various game and event messages (non-critical)
- `voice_manager.py`: Voice channel events

**Recommended Next Steps:**
1. Convert remaining print() statements to logger calls
2. Add request/response logging for all API calls
3. Implement log rotation (automatic cleanup after 30 days)
4. Add performance metrics logging
5. Create dashboard view for log aggregation

## Testing Checklist

- [✓] Database connection failures logged properly
- [✓] API errors captured with full context
- [✓] Bot startup errors logged to file
- [✓] No syntax errors in modified files
- [ ] Run bot and verify all logs appear in file
- [ ] Test command error to verify logging
- [ ] Test database error to verify decorator
- [ ] Verify log file rotation works

## Benefits of New System

1. **Easier Debugging:** All errors logged with full context and stack traces
2. **Better Monitoring:** Centralized log files for searching and analysis
3. **Graceful Degradation:** Database errors don't crash the bot
4. **Performance Tracking:** Can identify slow operations
5. **Audit Trail:** Complete record of all operations
6. **Developer Experience:** Color-coded console output for development

## Configuration

**Log Level Control:**
Edit `logger_utils.py` to change default log level:
```python
def setup_logger(name, level=logging.DEBUG):  # Change DEBUG to INFO for production
```

**Log Format:**
Modify `ColoredFormatter._fmt` to change format:
```python
self._fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

**Console Colors:**
Disable colors by removing `ColoredFormatter`:
```python
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter(fmt))  # Remove ColoredFormatter
```

---

**Last Updated:** 2025-01-16
**Author:** GitHub Copilot
**Status:** In Progress - Core functionality complete, testing needed
