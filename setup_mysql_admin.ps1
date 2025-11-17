# MySQL Database Setup Script for Sulfur Bot
# Run this in PowerShell AS ADMINISTRATOR

Write-Host "=== Sulfur Bot MySQL Setup ===" -ForegroundColor Cyan
Write-Host ""

# Add MySQL to PATH for this session
$mysqlBin = "C:\Program Files\MySQL\MySQL Server 8.4\bin"
if (Test-Path $mysqlBin) {
    $env:PATH = "$mysqlBin;$env:PATH"
    Write-Host "✅ MySQL found at: $mysqlBin" -ForegroundColor Green
} else {
    Write-Host "❌ MySQL not found at expected location" -ForegroundColor Red
    exit 1
}

# Check if running as admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "⚠️  Running without admin privileges" -ForegroundColor Yellow
    Write-Host "   Some operations may require administrator access" -ForegroundColor Yellow
}

# Check if MySQL service is running
Write-Host "Checking MySQL service..." -ForegroundColor Yellow
$service = Get-Service -Name MySQL84 -ErrorAction SilentlyContinue

if ($null -eq $service) {
    Write-Host "❌ MySQL84 service not found!" -ForegroundColor Red
    Write-Host "Installing MySQL service..." -ForegroundColor Yellow
    & "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqld.exe" --install MySQL84
    Write-Host "Starting MySQL service..." -ForegroundColor Yellow
    Start-Service MySQL84
    Start-Sleep -Seconds 3
} elseif ($service.Status -ne "Running") {
    Write-Host "Starting MySQL service..." -ForegroundColor Yellow
    Start-Service MySQL84
    Start-Sleep -Seconds 3
}

Write-Host "✅ MySQL service is running" -ForegroundColor Green
Write-Host ""

# Prompt for root password
Write-Host "=== MySQL Root Login ===" -ForegroundColor Cyan
Write-Host "Enter your MySQL root password (or press Enter to try without password):" -ForegroundColor Yellow
$rootPasswordSecure = Read-Host "Root password" -AsSecureString
$BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($rootPasswordSecure)
$rootPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
[System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($BSTR)

# Create SQL commands file
$sqlCommands = @"
-- Create database
CREATE DATABASE IF NOT EXISTS sulfur_bot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Drop old user if exists (to fix authentication issues)
DROP USER IF EXISTS 'sulfur_bot_user'@'localhost';

-- Create user with no password (matching .env file)
CREATE USER 'sulfur_bot_user'@'localhost' IDENTIFIED WITH caching_sha2_password BY '';

-- Grant privileges
GRANT ALL PRIVILEGES ON sulfur_bot.* TO 'sulfur_bot_user'@'localhost';
FLUSH PRIVILEGES;

-- Show success message
SELECT '✅ Database and user created successfully!' AS Status;
"@

$sqlFile = "$env:TEMP\sulfur_setup.sql"
$sqlCommands | Out-File -FilePath $sqlFile -Encoding UTF8

Write-Host ""
Write-Host "=== Creating Database and User ===" -ForegroundColor Cyan

try {
    # Execute SQL commands
    if ([string]::IsNullOrEmpty($rootPassword)) {
        Write-Host "Trying connection without password..." -ForegroundColor Yellow
        $output = Get-Content $sqlFile | & mysql -u root 2>&1
    } else {
        Write-Host "Trying connection with password..." -ForegroundColor Yellow
        $output = Get-Content $sqlFile | & mysql -u root "--password=$rootPassword" 2>&1
    }
    
    $output | Out-String | Write-Host
    
    # Check for errors
    $errorLines = $output | Where-Object { $_ -match "ERROR" }
    if ($errorLines) {
        Write-Host "❌ MySQL errors:" -ForegroundColor Red
        $errorLines | ForEach-Object { Write-Host "   $_" -ForegroundColor Red }
        throw "SQL execution failed"
    } else {
        Write-Host "✅ Database and user created" -ForegroundColor Green
    }
    
    Write-Host ""
    Write-Host "=== Verifying Setup ===" -ForegroundColor Cyan
    
    # Test connection
    $testSql = "SELECT 'Connection successful!' AS Result;"
    $testSqlFile = "$env:TEMP\test_connection.sql"
    $testSql | Out-File -FilePath $testSqlFile -Encoding UTF8
    
    Get-Content $testSqlFile | & mysql -u sulfur_bot_user sulfur_bot 2>&1 | Out-String | Write-Host
    
    Write-Host ""
    Write-Host "✅ MySQL setup complete!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. cd C:\sulfur" -ForegroundColor White
    Write-Host "  2. python apply_migration.py" -ForegroundColor White
    Write-Host "  3. python bot.py" -ForegroundColor White
    Write-Host ""
    
} catch {
    Write-Host "❌ Error during setup: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Manual setup required. See MYSQL_SETUP.md" -ForegroundColor Yellow
} finally {
    # Cleanup temp files
    Remove-Item -Path $sqlFile -ErrorAction SilentlyContinue
    Remove-Item -Path $testSqlFile -ErrorAction SilentlyContinue
    Remove-Item -Path "$env:TEMP\mysql_output.txt" -ErrorAction SilentlyContinue
    Remove-Item -Path "$env:TEMP\mysql_error.txt" -ErrorAction SilentlyContinue
}

Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
