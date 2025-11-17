# Automated error checking script for Sulfur Discord Bot
# Run this before starting the bot to catch potential issues

Write-Host "`n" -NoNewline
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Sulfur Bot - Error Detection System     " -ForegroundColor Cyan
Write-Host "============================================`n" -ForegroundColor Cyan

$ErrorCount = 0
$WarningCount = 0

# === 1. Check Python Syntax ===
Write-Host "[1/7] Checking Python syntax..." -ForegroundColor Yellow
$syntaxErrors = @()
# Exclude venv, __pycache__, and .git directories to speed up
$pyFiles = Get-ChildItem -Recurse -Filter *.py -File | Where-Object { 
    $_.DirectoryName -notlike '*__pycache__*' -and 
    $_.DirectoryName -notlike '*\venv\*' -and 
    $_.DirectoryName -notlike '*\.git\*' -and
    $_.DirectoryName -notlike '*\backups\*'
}
$total = $pyFiles.Count
$current = 0
Write-Host "  Found $total Python files to check..." -ForegroundColor Gray
foreach ($file in $pyFiles) {
    $current++
    Write-Host "`r  Checking file $current/$total : $($file.Name)..." -NoNewline -ForegroundColor Gray
    $null = python -m py_compile $file.FullName 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""  # New line before error
        Write-Host "  ✗ Syntax error in: $($file.Name)" -ForegroundColor Red
        $syntaxErrors += $file.Name
        $ErrorCount++
    }
}
Write-Host ""  # New line after progress

if ($syntaxErrors.Count -eq 0) {
    Write-Host "  ??? No syntax errors detected" -ForegroundColor Green
} else {
    Write-Host "  ??? Syntax errors in:" -ForegroundColor Red
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
    "web_dashboard.py"
)

$missingFiles = @()
foreach ($file in $requiredFiles) {
    if (-not (Test-Path $file)) {
        $missingFiles += $file
        $ErrorCount++
    }
}

if ($missingFiles.Count -eq 0) {
    Write-Host "  ??? All required files present" -ForegroundColor Green
} else {
    Write-Host "  ??? Missing files:" -ForegroundColor Red
    $missingFiles | ForEach-Object { Write-Host "    - $_" -ForegroundColor Red }
}

# === 3. Check Config JSON Validity ===
Write-Host "`n[3/7] Validating config.json..." -ForegroundColor Yellow
if (Test-Path "config/config.json") {
    $configCheck = python -c "import json; json.load(open('config/config.json')); print('OK')" 2>&1
    if ($configCheck -match "OK") {
        Write-Host "  ??? Config JSON is valid" -ForegroundColor Green
        
        # Check for required config sections
        $configContent = Get-Content "config/config.json" -Raw | ConvertFrom-Json
        $requiredSections = @("bot", "api", "database", "modules")
        $missingSections = @()
        
        foreach ($section in $requiredSections) {
            if (-not $configContent.PSObject.Properties.Name -contains $section) {
                $missingSections += $section
                $WarningCount++
            }
        }
        
        if ($missingSections.Count -gt 0) {
            Write-Host "  ??? Missing config sections:" -ForegroundColor Yellow
            $missingSections | ForEach-Object { Write-Host "    - $_" -ForegroundColor Yellow }
        }
    } else {
        Write-Host "  ??? Config JSON is malformed" -ForegroundColor Red
        Write-Host "    $configCheck" -ForegroundColor Red
        $ErrorCount++
    }
} else {
    Write-Host "  ??? config/config.json not found" -ForegroundColor Red
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
        Write-Host "  ??? .env file contains required variables" -ForegroundColor Green
        
        # Validate token format
        if ($envContent -match 'DISCORD_BOT_TOKEN="?([^"]+)"?') {
            $tokenValue = $Matches[1]
            if ($tokenValue.Split('.').Count -ne 3) {
                Write-Host "  ??? Discord token may be malformed (should have 3 parts)" -ForegroundColor Yellow
                $WarningCount++
            }
        }
    } else {
        Write-Host "  ??? Missing environment variables:" -ForegroundColor Red
        $missingVars | ForEach-Object { Write-Host "    - $_" -ForegroundColor Red }
    }
} else {
    Write-Host "  ??? .env file not found" -ForegroundColor Red
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
$importCount = 0
foreach ($test in $importTests) {
    $importCount++
    Write-Host "  Testing import $importCount/$($importTests.Count): $($test.Name)..." -ForegroundColor Gray
    python -c "import $($test.Module)" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        $missingModules += $test.Name
        $ErrorCount++
    }
}

if ($missingModules.Count -eq 0) {
    Write-Host "  ??? All required Python packages installed" -ForegroundColor Green
} else {
    Write-Host "  ??? Missing Python packages:" -ForegroundColor Red
    $missingModules | ForEach-Object { Write-Host "    - $_" -ForegroundColor Red }
    Write-Host "    Run: pip install -r requirements.txt" -ForegroundColor Yellow
}

# === 6. Check for Common Code Issues ===
Write-Host "`n[6/7] Scanning for potential issues..." -ForegroundColor Yellow
Write-Host "  Searching for anti-patterns in code..." -ForegroundColor Gray
$antiPatterns = @{
    "except:\s*\n\s*pass" = "Bare except with pass (silent errors)"
    "except Exception:\s*\n\s*pass" = "Catching all exceptions silently"
    "TODO|FIXME|HACK" = "Unresolved TODO/FIXME/HACK comments"
}

$foundIssues = @()
foreach ($pattern in $antiPatterns.GetEnumerator()) {
    Write-Host "  Searching for: $($pattern.Value)..." -ForegroundColor Gray
    $searchResults = Select-String -Pattern $pattern.Key -Path *.py,modules\*.py,web\*.py -SimpleMatch:$false -ErrorAction SilentlyContinue
    if ($searchResults) {
        foreach ($match in $searchResults) {
            $foundIssues += @{
                File = $match.Filename
                Line = $match.LineNumber
                Issue = $pattern.Value
            }
            $WarningCount++
        }
    }
}

if ($foundIssues.Count -eq 0) {
    Write-Host "  ??? No common anti-patterns detected" -ForegroundColor Green
} else {
    Write-Host "  ??? Found potential issues:" -ForegroundColor Yellow
    $foundIssues | Select-Object -First 5 | ForEach-Object {
        Write-Host "    - $($_.File):$($_.Line) - $($_.Issue)" -ForegroundColor Yellow
    }
    if ($foundIssues.Count -gt 5) {
        Write-Host "    ... and $($foundIssues.Count - 5) more" -ForegroundColor Yellow
    }
}

# === 7. Check Database Connectivity (Optional) ===
Write-Host "`n[7/7] Testing database connection..." -ForegroundColor Yellow
if (Test-Path "modules/db_helpers.py") {
    # Simple check - just verify imports work
    $dbTest = python -c "from modules.db_helpers import init_db_pool; print('OK')" 2>&1
    
    if ($dbTest -match "OK") {
        Write-Host "  ??? Database helper imports successful" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ Database helper import failed" -ForegroundColor Yellow
        $WarningCount++
    }
} else {
    Write-Host "  ⚠ Skipping (modules/db_helpers.py not found)" -ForegroundColor Yellow
}

# === Summary ===
Write-Host "`n" -NoNewline
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "             Check Complete                " -ForegroundColor Cyan
Write-Host "============================================`n" -ForegroundColor Cyan

if ($ErrorCount -eq 0 -and $WarningCount -eq 0) {
    Write-Host "??? All checks passed! Bot is ready to start." -ForegroundColor Green
    exit 0
} elseif ($ErrorCount -eq 0) {
    Write-Host "??? $WarningCount warning(s) found, but no critical errors." -ForegroundColor Yellow
    Write-Host "  Bot can start, but please review warnings." -ForegroundColor Yellow
    exit 0
} else {
    Write-Host "??? $ErrorCount error(s) and $WarningCount warning(s) found." -ForegroundColor Red
    Write-Host "  Please fix errors before starting the bot." -ForegroundColor Red
    exit 1
}

