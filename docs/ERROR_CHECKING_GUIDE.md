# Error Detection and Prevention Checklist

## Quick Error Check Commands

### Check for Syntax Errors
```powershell
# Check Python syntax in all files
Get-ChildItem -Filter *.py | ForEach-Object { python -m py_compile $_.FullName }

# Check specific files
python -m py_compile bot.py
python -m py_compile db_helpers.py
python -m py_compile web_dashboard.py
```

### Check for Import Errors
```powershell
# Test imports without running bot
python -c "import bot; import db_helpers; import api_helpers; import voice_manager; import web_dashboard; print('All imports OK')"
```

### Check Database Connection
```powershell
# Test database connectivity
python -c "from db_helpers import init_db_pool; import asyncio; asyncio.run(init_db_pool()); print('Database pool OK')"
```

### Check Configuration
```powershell
# Validate config.json
python -c "import json; f=open('config.json'); json.load(f); print('Config JSON valid')"
```

## Common Error Patterns to Check

### 1. Database Errors

**Pattern:** Database pool not initialized
```python
# BAD - No pool check
async def get_data():
    cnx = db_pool.get_connection()  # Crash if pool is None
    
# GOOD - With check
async def get_data():
    if not db_pool:
        logger.warning("Database pool not available")
        return None
    cnx = db_pool.get_connection()
    if not cnx:
        return None
```

**Pattern:** Connection not closed
```python
# BAD - Connection leak
async def query():
    cnx = db_pool.get_connection()
    cursor = cnx.cursor()
    cursor.execute("SELECT * FROM players")
    return cursor.fetchall()  # Never closes connection!
    
# GOOD - With finally
async def query():
    cnx = db_pool.get_connection()
    if not cnx:
        return None
    cursor = cnx.cursor()
    try:
        cursor.execute("SELECT * FROM players")
        return cursor.fetchall()
    finally:
        cursor.close()
        cnx.close()
```

**Pattern:** SQL injection vulnerability
```python
# BAD - SQL injection possible
query = f"SELECT * FROM players WHERE discord_id = {user_id}"
cursor.execute(query)

# GOOD - Parameterized query
query = "SELECT * FROM players WHERE discord_id = %s"
cursor.execute(query, (user_id,))
```

### 2. API Errors

**Pattern:** No timeout specified
```python
# BAD - Can hang forever
async with session.post(url, json=payload) as response:
    ...
    
# GOOD - With timeout
async with session.post(url, json=payload, timeout=30) as response:
    ...
```

**Pattern:** API errors not logged
```python
# BAD - Silent failure
try:
    response = await api_call()
except Exception:
    return None
    
# GOOD - Logged error
try:
    response = await api_call()
except Exception as e:
    logger.error(f"API call failed: {e}", exc_info=True)
    return None
```

**Pattern:** Rate limit not handled
```python
# BAD - No rate limit handling
if response.status == 429:
    return None
    
# GOOD - Log and inform
if response.status == 429:
    logger.warning(f"Rate limited by API. Retry after: {response.headers.get('Retry-After')}")
    return None, "Rate limit exceeded"
```

### 3. Discord API Errors

**Pattern:** Missing permission check
```python
# BAD - No permission check
await channel.send("Hello")

# GOOD - Check permissions
if channel.permissions_for(guild.me).send_messages:
    await channel.send("Hello")
else:
    logger.warning(f"No permission to send in {channel.name}")
```

**Pattern:** DM failures not handled
```python
# BAD - Crash on DM closed
await user.send("Hello")

# GOOD - Handle DM failure
try:
    await user.send("Hello")
except discord.Forbidden:
    logger.info(f"Cannot DM {user.name} (DMs closed)")
```

**Pattern:** Missing await on async functions
```python
# BAD - Forgot await
result = some_async_function()  # Returns coroutine, not result!

# GOOD - With await
result = await some_async_function()
```

### 4. Configuration Errors

**Pattern:** Missing config key
```python
# BAD - KeyError if missing
value = config['modules']['economy']['starting_balance']

# GOOD - With get and default
value = config.get('modules', {}).get('economy', {}).get('starting_balance', 1000)
```

**Pattern:** Invalid config type
```python
# BAD - No type validation
timeout = config['api']['timeout']  # Could be string!
await sleep(timeout)  # TypeError

# GOOD - With validation
timeout = int(config.get('api', {}).get('timeout', 30))
await sleep(timeout)
```

### 5. File I/O Errors

**Pattern:** File not found not handled
```python
# BAD - Crashes if file missing
with open("config.json") as f:
    data = json.load(f)
    
# GOOD - Handle missing file
try:
    with open("config.json") as f:
        data = json.load(f)
except FileNotFoundError:
    logger.critical("config.json not found")
    exit(1)
```

**Pattern:** Encoding issues
```python
# BAD - Default encoding (system-dependent)
with open("file.txt") as f:
    content = f.read()
    
# GOOD - Explicit UTF-8
with open("file.txt", encoding="utf-8") as f:
    content = f.read()
```

## Automated Error Checks

### Pre-Commit Checks
Create `check_errors.ps1`:
```powershell
# Automated error checking script
Write-Host "Checking for errors..." -ForegroundColor Cyan

# 1. Check Python syntax
Write-Host "`n[1/5] Checking Python syntax..." -ForegroundColor Yellow
$syntaxErrors = 0
Get-ChildItem -Filter *.py | ForEach-Object {
    python -m py_compile $_.FullName 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ✗ Syntax error in $($_.Name)" -ForegroundColor Red
        $syntaxErrors++
    }
}
if ($syntaxErrors -eq 0) {
    Write-Host "  ✓ No syntax errors" -ForegroundColor Green
}

# 2. Check for common anti-patterns
Write-Host "`n[2/5] Checking for anti-patterns..." -ForegroundColor Yellow
$patterns = @{
    "db_pool.get_connection\(\)" = "Missing pool check"
    "print\(f\"Error" = "Using print instead of logger"
    "except:\s*$" = "Bare except clause"
    "pass\s*$" = "Empty except block"
}

foreach ($pattern in $patterns.GetEnumerator()) {
    $matches = Select-String -Pattern $pattern.Key -Path *.py
    if ($matches) {
        Write-Host "  ⚠ Found: $($pattern.Value)" -ForegroundColor Yellow
        $matches | ForEach-Object { Write-Host "    - $($_.Filename):$($_.LineNumber)" }
    }
}

# 3. Check imports
Write-Host "`n[3/5] Checking imports..." -ForegroundColor Yellow
python -c "import bot; import db_helpers; import api_helpers; import voice_manager" 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ All imports successful" -ForegroundColor Green
} else {
    Write-Host "  ✗ Import errors detected" -ForegroundColor Red
}

# 4. Check config validity
Write-Host "`n[4/5] Checking config.json..." -ForegroundColor Yellow
python -c "import json; json.load(open('config.json'))" 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Config JSON valid" -ForegroundColor Green
} else {
    Write-Host "  ✗ Config JSON invalid" -ForegroundColor Red
}

# 5. Check .env file
Write-Host "`n[5/5] Checking .env file..." -ForegroundColor Yellow
if (Test-Path .env) {
    $envContent = Get-Content .env -Raw
    if ($envContent -match "DISCORD_BOT_TOKEN=") {
        Write-Host "  ✓ .env file exists with token" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ .env missing DISCORD_BOT_TOKEN" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ✗ .env file not found" -ForegroundColor Red
}

Write-Host "`nError check complete!" -ForegroundColor Cyan
```

### Usage
```powershell
# Run before starting bot
.\check_errors.ps1

# If all checks pass, start bot
.\maintain_bot.ps1
```

## Runtime Error Monitoring

### Check Logs for Errors
```powershell
# Find all ERROR level logs
Get-Content logs\session_*.log | Select-String "ERROR"

# Find critical errors
Get-Content logs\session_*.log | Select-String "CRITICAL"

# Find database errors
Get-Content logs\session_*.log | Select-String "db - ERROR"

# Find API errors
Get-Content logs\session_*.log | Select-String "api - ERROR"

# Count errors by type
Get-Content logs\session_*.log | Select-String "ERROR" | Group-Object {$_ -replace '^.*ERROR - ', ''} | Sort-Object Count -Descending
```

### Live Error Monitoring
```powershell
# Watch for new errors in real-time
Get-Content logs\session_*.log -Wait -Tail 50 | Select-String "ERROR|CRITICAL" --Context 2
```

## Error Prevention Guidelines

### 1. Always Validate Input
```python
def validate_user_id(user_id):
    if not isinstance(user_id, int):
        raise TypeError(f"user_id must be int, got {type(user_id)}")
    if user_id < 0:
        raise ValueError(f"user_id must be positive, got {user_id}")
    return True
```

### 2. Use Type Hints
```python
async def add_xp(user_id: int, amount: int) -> Optional[int]:
    """
    Add XP to user.
    
    Args:
        user_id: Discord user ID
        amount: XP amount to add
        
    Returns:
        New level if leveled up, None otherwise
    """
```

### 3. Document Error Cases
```python
async def get_player_data(user_id: int) -> Tuple[Optional[dict], Optional[str]]:
    """
    Get player data from database.
    
    Returns:
        (data, error) where:
        - If successful: (dict with player data, None)
        - If user not found: (None, "User not found")
        - If db error: (None, "Database error")
    """
```

### 4. Use Defensive Programming
```python
# Always check None
if result is None:
    logger.warning("Unexpected None result")
    return default_value
    
# Always validate ranges
if amount <= 0:
    logger.error(f"Invalid amount: {amount}")
    return False
    
# Always check types
if not isinstance(config, dict):
    logger.critical(f"Config must be dict, got {type(config)}")
    exit(1)
```

## Testing for Errors

### Unit Test Example
```python
import pytest
from db_helpers import add_xp

@pytest.mark.asyncio
async def test_add_xp_invalid_amount():
    """Test that negative XP raises error"""
    with pytest.raises(ValueError):
        await add_xp(user_id=123, amount=-100)

@pytest.mark.asyncio
async def test_add_xp_no_database():
    """Test that missing database returns None"""
    # Simulate no database
    db_helpers.db_pool = None
    result = await add_xp(user_id=123, amount=100)
    assert result is None
```

### Integration Test
```python
async def test_full_workflow():
    """Test complete user flow"""
    # 1. Create user
    result = await add_user(user_id=999, name="Test")
    assert result is not None
    
    # 2. Add XP
    new_level = await add_xp(user_id=999, amount=100)
    assert new_level is not None
    
    # 3. Check rank
    rank_data, error = await get_player_rank(user_id=999)
    assert error is None
    assert rank_data['xp'] == 100
```

---

**Last Updated:** 2025-01-16
**Purpose:** Comprehensive error detection and prevention guide
**Status:** Complete
