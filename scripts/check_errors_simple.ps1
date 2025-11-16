# Automated error checking script for Sulfur Discord Bot
# Run this before starting the bot to catch potential issues

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "  Sulfur Bot - Error Detection System     " -ForegroundColor Cyan
Write-Host "============================================`n" -ForegroundColor Cyan

$ErrorCount = 0
$WarningCount = 0

# === 1. Check Python Syntax ===
Write-Host "[1/6] Checking Python syntax..." -ForegroundColor Yellow
$syntaxErrors = @()
Get-ChildItem -Filter *.py -File | ForEach-Object {
    python -m py_compile $_.FullName 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        $syntaxErrors += $_.Name
        $ErrorCount++
    }
}

if ($syntaxErrors.Count -eq 0) {
    Write-Host "  ✓ No syntax errors detected" -ForegroundColor Green
} else {
    Write-Host "  ✗ Syntax errors in:" -ForegroundColor Red
    $syntaxErrors | ForEach-Object { Write-Host "    - $_" -ForegroundColor Red }
}

# === 2. Check Critical Files Exist ===
Write-Host "`n[2/6] Checking required files..." -ForegroundColor Yellow
$requiredFiles = @("bot.py", "config.json", "system_prompt.txt", ".env", "requirements.txt", "db_helpers.py")

$missingFiles = @()
foreach ($file in $requiredFiles) {
    if (-not (Test-Path $file)) {
        $missingFiles += $file
        $ErrorCount++
    }
}

if ($missingFiles.Count -eq 0) {
    Write-Host "  ✓ All required files present" -ForegroundColor Green
} else {
    Write-Host "  ✗ Missing files:" -ForegroundColor Red
    $missingFiles | ForEach-Object { Write-Host "    - $_" -ForegroundColor Red }
}

# === 3. Check Config JSON Validity ===
Write-Host "`n[3/6] Validating config.json..." -ForegroundColor Yellow
if (Test-Path "config.json") {
    try {
        $configContent = Get-Content "config.json" -Raw | ConvertFrom-Json
        Write-Host "  ✓ Config JSON is valid" -ForegroundColor Green
    }
    catch {
        Write-Host "  ✗ Config JSON is malformed" -ForegroundColor Red
        $ErrorCount++
    }
}
else {
    Write-Host "  ✗ config.json not found" -ForegroundColor Red
    $ErrorCount++
}

# === 4. Check .env File ===
Write-Host "`n[4/6] Validating .env file..." -ForegroundColor Yellow
if (Test-Path ".env") {
    $envContent = Get-Content .env -Raw
    if ($envContent -match "DISCORD_BOT_TOKEN=") {
        Write-Host "  ✓ .env file contains DISCORD_BOT_TOKEN" -ForegroundColor Green
    }
    else {
        Write-Host "  ✗ .env missing DISCORD_BOT_TOKEN" -ForegroundColor Red
        $ErrorCount++
    }
}
else {
    Write-Host "  ✗ .env file not found" -ForegroundColor Red
    $ErrorCount++
}

# === 5. Check Python Imports ===
Write-Host "`n[5/6] Testing Python imports..." -ForegroundColor Yellow
$importTests = @("discord", "mysql.connector", "flask", "aiohttp")
$missingModules = @()

foreach ($module in $importTests) {
    python -c "import $module" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        $missingModules += $module
        $ErrorCount++
    }
}

if ($missingModules.Count -eq 0) {
    Write-Host "  ✓ All required Python packages installed" -ForegroundColor Green
}
else {
    Write-Host "  ✗ Missing Python packages:" -ForegroundColor Red
    $missingModules | ForEach-Object { Write-Host "    - $_" -ForegroundColor Red }
    Write-Host "    Run: pip install -r requirements.txt" -ForegroundColor Yellow
}

# === 6. Check Logger Utils ===
Write-Host "`n[6/6] Testing logger_utils..." -ForegroundColor Yellow
if (Test-Path "logger_utils.py") {
    python -c "from logger_utils import bot_logger; print('OK')" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Logger utils working correctly" -ForegroundColor Green
    }
    else {
        Write-Host "  ⚠ Logger utils import failed" -ForegroundColor Yellow
        $WarningCount++
    }
}
else {
    Write-Host "  ⚠ logger_utils.py not found" -ForegroundColor Yellow
    $WarningCount++
}

# === Summary ===
Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "             Check Complete                " -ForegroundColor Cyan
Write-Host "============================================`n" -ForegroundColor Cyan

if ($ErrorCount -eq 0 -and $WarningCount -eq 0) {
    Write-Host "All checks passed! Bot is ready to start." -ForegroundColor Green
    exit 0
}
elseif ($ErrorCount -eq 0) {
    Write-Host "$WarningCount warning(s) found, but no critical errors." -ForegroundColor Yellow
    Write-Host "Bot can start, but please review warnings." -ForegroundColor Yellow
    exit 0
}
else {
    Write-Host "$ErrorCount error(s) and $WarningCount warning(s) found." -ForegroundColor Red
    Write-Host "Please fix errors before starting the bot." -ForegroundColor Red
    exit 1
}
