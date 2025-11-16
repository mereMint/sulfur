# Automated error checking script for Sulfur Discord Bot (Fast Version)

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "  Sulfur Bot - Error Detection System     " -ForegroundColor Cyan
Write-Host "============================================`n" -ForegroundColor Cyan

$ErrorCount = 0
$WarningCount = 0

# === 1. Check Python Syntax ===
Write-Host "[1/7] Checking Python syntax..." -ForegroundColor Yellow
$syntaxErrors = @()
# Only check project files, exclude venv and backups
$pyFiles = @(
    "bot.py",
    "modules\*.py",
    "web\*.py",
    "scripts\*.py"
) | ForEach-Object { Get-ChildItem -Path $_ -ErrorAction SilentlyContinue } | Where-Object { $_.Extension -eq '.py' }

Write-Host "  Checking $($pyFiles.Count) Python files..." -ForegroundColor Gray
foreach ($file in $pyFiles) {
    python -m py_compile $file.FullName 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        $syntaxErrors += $file.Name
        $ErrorCount++
    }
}

if ($syntaxErrors.Count -eq 0) {
    Write-Host "  âœ“ No syntax errors detected" -ForegroundColor Green
} else {
    Write-Host "  âœ— Syntax errors in:" -ForegroundColor Red
    $syntaxErrors | ForEach-Object { Write-Host "    - $_" -ForegroundColor Red }
}

# === 2. Check Critical Files Exist ===
Write-Host "`n[2/7] Checking required files..." -ForegroundColor Yellow
$requiredFiles = @(
    "bot.py",
    "config/config.json",
    "config/system_prompt.txt",
    ".env",
    "requirements.txt",
    "modules/db_helpers.py",
    "modules/api_helpers.py",
    "web/web_dashboard.py"
)

$missingFiles = @()
foreach ($file in $requiredFiles) {
    if (-not (Test-Path $file)) {
        $missingFiles += $file
        $ErrorCount++
    }
}

if ($missingFiles.Count -eq 0) {
    Write-Host "  âœ“ All required files present" -ForegroundColor Green
} else {
    Write-Host "  âœ— Missing files:" -ForegroundColor Red
    $missingFiles | ForEach-Object { Write-Host "    - $_" -ForegroundColor Red }
}

# === 3. Check Config JSON Validity ===
Write-Host "`n[3/7] Validating config.json..." -ForegroundColor Yellow
if (Test-Path "config/config.json") {
    try {
        $configContent = Get-Content "config/config.json" -Raw | ConvertFrom-Json
        Write-Host "  âœ“ Config JSON is valid" -ForegroundColor Green
        
        # Check for required config sections
        $requiredSections = @("bot", "api", "database", "modules")
        $missingSections = @()
        
        foreach ($section in $requiredSections) {
            if (-not $configContent.PSObject.Properties.Name -contains $section) {
                $missingSections += $section
                $WarningCount++
            }
        }
        
        if ($missingSections.Count -gt 0) {
            Write-Host "  âš  Missing config sections:" -ForegroundColor Yellow
            $missingSections | ForEach-Object { Write-Host "    - $_" -ForegroundColor Yellow }
        }
    } catch {
        Write-Host "  âœ— Config JSON is malformed" -ForegroundColor Red
        $ErrorCount++
    }
} else {
    Write-Host "  âœ— config/config.json not found" -ForegroundColor Red
    $ErrorCount++
}

# === 4. Check .env File ===
Write-Host "`n[4/7] Validating .env file..." -ForegroundColor Yellow
if (Test-Path ".env") {
    $envContent = Get-Content .env -Raw
    $requiredEnvVars = @("DISCORD_BOT_TOKEN")
    $missingVars = @()
    
    foreach ($var in $requiredEnvVars) {
        if ($envContent -notmatch "$var=") {
            $missingVars += $var
            $ErrorCount++
        }
    }
    
    if ($missingVars.Count -eq 0) {
        Write-Host "  âœ“ .env file contains required variables" -ForegroundColor Green
        
        # Validate token format
        if ($envContent -match 'DISCORD_BOT_TOKEN="?([^"]+)"?') {
            $tokenValue = $Matches[1]
            if ($tokenValue.Split('.').Count -ne 3) {
                Write-Host "  âš  Discord token may be malformed (should have 3 parts)" -ForegroundColor Yellow
                $WarningCount++
            }
        }
    } else {
        Write-Host "  âœ— Missing environment variables:" -ForegroundColor Red
        $missingVars | ForEach-Object { Write-Host "    - $_" -ForegroundColor Red }
    }
} else {
    Write-Host "  âœ— .env file not found" -ForegroundColor Red
    $ErrorCount++
}

# === 5. Check Python Imports ===
Write-Host "`n[5/7] Testing Python imports..." -ForegroundColor Yellow
$importTests = @(
    @{ Module = "discord"; Name = "discord.py" },
    @{ Module = "mysql.connector"; Name = "mysql-connector-python" },
    @{ Module = "flask"; Name = "Flask" },
    @{ Module = "aiohttp"; Name = "aiohttp" }
)

$missingModules = @()
foreach ($test in $importTests) {
    python -c "import $($test.Module)" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        $missingModules += $test.Name
        $ErrorCount++
    }
}

if ($missingModules.Count -eq 0) {
    Write-Host "  âœ“ All required Python packages installed" -ForegroundColor Green
} else {
    Write-Host "  âœ— Missing Python packages:" -ForegroundColor Red
    $missingModules | ForEach-Object { Write-Host "    - $_" -ForegroundColor Red }
    Write-Host "    Run: pip install -r requirements.txt" -ForegroundColor Yellow
}

# === 6. Check for Common Code Issues ===
Write-Host "`n[6/7] Scanning for potential issues..." -ForegroundColor Yellow
Write-Host "  (Skipped for speed - run full check_errors.ps1 for detailed scan)" -ForegroundColor Gray

# === 7. Check Database Connectivity ===
Write-Host "`n[7/7] Testing database connection..." -ForegroundColor Yellow
if (Test-Path "modules/db_helpers.py") {
    $dbTest = python -c "from modules.db_helpers import init_db_pool; print('OK')" 2>&1
    
    if ($dbTest -match "OK") {
        Write-Host "  âœ“ Database helper imports successful" -ForegroundColor Green
    } else {
        Write-Host "  âš  Database helper import failed" -ForegroundColor Yellow
        $WarningCount++
    }
} else {
    Write-Host "  âš  Skipping (modules/db_helpers.py not found)" -ForegroundColor Yellow
}

# === Summary ===
Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "             Check Complete                " -ForegroundColor Cyan
Write-Host "============================================`n" -ForegroundColor Cyan

if ($ErrorCount -eq 0 -and $WarningCount -eq 0) {
    Write-Host "âœ“ All checks passed! Bot is ready to start." -ForegroundColor Green
    exit 0
} elseif ($ErrorCount -eq 0) {
    Write-Host "âš  $WarningCount warning(s) found, but no critical errors." -ForegroundColor Yellow
    Write-Host "  Bot can start, but please review warnings." -ForegroundColor Yellow
    exit 0
} else {
    Write-Host "âœ— $ErrorCount error(s) and $WarningCount warning(s) found." -ForegroundColor Red
    Write-Host "  Please fix errors before starting the bot." -ForegroundColor Red
    exit 1
}

