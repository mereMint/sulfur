# ============================================================
# Sulfur Bot - MySQL Setup Helper for Windows
# ============================================================
# This script helps set up MySQL for the Sulfur bot

Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║         Sulfur Bot - MySQL Setup Helper                   ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Check if MySQL/MariaDB is running
Write-Host "Checking MySQL/MariaDB status..." -ForegroundColor Yellow
$mysqlProcess = Get-Process mysqld,mariadbd -ErrorAction SilentlyContinue | Select-Object -First 1

if ($mysqlProcess) {
    Write-Host "✓ MySQL/MariaDB is running (PID: $($mysqlProcess.Id))" -ForegroundColor Green
} else {
    Write-Host "✗ MySQL/MariaDB is not running!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please start MySQL/MariaDB first:" -ForegroundColor Yellow
    Write-Host "  - If using XAMPP: Open XAMPP Control Panel and start MySQL" -ForegroundColor White
    Write-Host "  - If using MariaDB: Run 'net start MariaDB' (as Administrator)" -ForegroundColor White
    Write-Host "  - If using MySQL: Run 'net start MySQL' (as Administrator)" -ForegroundColor White
    Write-Host "  - Or: services.msc → Find MySQL/MariaDB → Start" -ForegroundColor White
    Write-Host ""
    $start = Read-Host "Press Enter after starting MySQL/MariaDB, or type 'skip' to exit"
    if ($start -eq 'skip') {
        exit 1
    }
}

# Check for mysql.exe or mariadb.exe
Write-Host ""
Write-Host "Looking for MySQL/MariaDB client..." -ForegroundColor Yellow

$mysqlPaths = @(
    "C:\Program Files\MariaDB 11.0\bin\mariadb.exe",
    "C:\Program Files\MariaDB 10.11\bin\mariadb.exe",
    "C:\Program Files\MariaDB 10.6\bin\mariadb.exe",
    "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe",
    "C:\Program Files\MySQL\MySQL Server 5.7\bin\mysql.exe",
    "C:\xampp\mysql\bin\mysql.exe",
    "C:\wamp64\bin\mysql\mysql8.0.27\bin\mysql.exe"
)

$mysqlExe = $null
foreach ($path in $mysqlPaths) {
    if (Test-Path $path) {
        $mysqlExe = $path
        break
    }
}

# Try to find mariadb or mysql in PATH
if (-not $mysqlExe) {
    $mysqlExe = (Get-Command mariadb -ErrorAction SilentlyContinue).Source
}
if (-not $mysqlExe) {
    $mysqlExe = (Get-Command mysql -ErrorAction SilentlyContinue).Source
}

if ($mysqlExe) {
    Write-Host "✓ Found client at: $mysqlExe" -ForegroundColor Green
} else {
    Write-Host "✗ Could not find mysql.exe or mariadb.exe" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please enter the full path to mysql.exe or mariadb.exe:" -ForegroundColor Yellow
    $mysqlExe = Read-Host "Path"
    if (-not (Test-Path $mysqlExe)) {
        Write-Host "✗ File not found. Exiting." -ForegroundColor Red
        exit 1
    }
}

# Run the setup script
Write-Host ""
Write-Host "Running database setup script..." -ForegroundColor Yellow
Write-Host "You will be prompted for the MySQL root password." -ForegroundColor White
Write-Host ""

try {
    # Get the SQL file path
    $sqlFile = Join-Path $PSScriptRoot "setup_database.sql"
    
    if (-not (Test-Path $sqlFile)) {
        Write-Host "✗ SQL file not found: $sqlFile" -ForegroundColor Red
        exit 1
    }
    
    # Read SQL content and execute
    $sqlContent = Get-Content $sqlFile -Raw
    
    Write-Host "Executing SQL commands..." -ForegroundColor Yellow
    $result = $sqlContent | & $mysqlExe -u root -p 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✓ Database setup complete!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Database credentials:" -ForegroundColor Cyan
        Write-Host "  Host: localhost" -ForegroundColor White
        Write-Host "  User: sulfur_bot_user" -ForegroundColor White
        Write-Host "  Password: (empty)" -ForegroundColor White
        Write-Host "  Database: sulfur_bot" -ForegroundColor White
        Write-Host ""
        Write-Host "These are already configured in your .env file." -ForegroundColor Gray
    } else {
        Write-Host ""
        Write-Host "✗ Setup failed. Error output:" -ForegroundColor Red
        Write-Host $result -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host ""
    Write-Host "✗ Error running setup: $_" -ForegroundColor Red
    exit 1
}

# Test the connection
Write-Host ""
Write-Host "Testing connection..." -ForegroundColor Yellow

try {
    $testResult = & $mysqlExe -u sulfur_bot_user sulfur_bot -e "SELECT 'Connection successful!' AS status;" 2>&1
    
    if ($testResult -match "Connection successful") {
        Write-Host "✓ Connection test passed!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Next steps:" -ForegroundColor Cyan
        Write-Host "1. Install dependencies: pip install -r requirements.txt" -ForegroundColor White
        Write-Host "2. Run setup test: python test_setup.py" -ForegroundColor White
        Write-Host "3. Start the bot: .\maintain_bot.ps1" -ForegroundColor White
    } else {
        Write-Host "✗ Connection test failed" -ForegroundColor Red
        Write-Host "Error: $testResult" -ForegroundColor Red
    }
} catch {
    Write-Host "✗ Connection test failed: $_" -ForegroundColor Red
}

Write-Host ""
