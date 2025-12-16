# ============================================================
# Sulfur Bot - Quick Setup Script for Windows
# ============================================================
# This script automates the entire setup process for first-time users
# Usage: Right-click > Run with PowerShell
# 
# Parameters:
#   -InstallDir "C:\path\to\install" - Custom installation directory
# ============================================================

param(
    [string]$InstallDir = ""
)

$ErrorActionPreference = 'Continue'

Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║         Sulfur Bot - Quick Setup Wizard (Windows)         ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Determine installation path
if ([string]::IsNullOrWhiteSpace($InstallDir)) {
    $scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
} else {
    $scriptPath = $InstallDir
    if (-not (Test-Path $scriptPath)) {
        Write-Host "Creating installation directory: $scriptPath" -ForegroundColor Yellow
        New-Item -ItemType Directory -Path $scriptPath -Force | Out-Null
    }
}
Set-Location $scriptPath

Write-Host "Installation directory: $scriptPath" -ForegroundColor Gray
Write-Host ""

# Step 1: Check Prerequisites
Write-Host "Step 1: Checking Prerequisites" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host ""

# Check Python
Write-Host "Checking Python..." -ForegroundColor Cyan
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python not found!" -ForegroundColor Red
    Write-Host "  Please install Python from https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "  Make sure to check 'Add Python to PATH' during installation" -ForegroundColor Yellow
    pause
    exit 1
}

# Check Git
Write-Host "Checking Git..." -ForegroundColor Cyan
try {
    $gitVersion = git --version 2>&1
    Write-Host "✓ Git found: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Git not found!" -ForegroundColor Red
    Write-Host "  Please install Git from https://git-scm.com/download/win" -ForegroundColor Yellow
    pause
    exit 1
}

# Check MySQL/MariaDB
Write-Host "Checking MySQL/MariaDB..." -ForegroundColor Cyan
$mysqlProcess = Get-Process mysqld,mariadbd -ErrorAction SilentlyContinue | Select-Object -First 1
if ($mysqlProcess) {
    Write-Host "✓ MySQL/MariaDB is running (PID: $($mysqlProcess.Id))" -ForegroundColor Green
} else {
    Write-Host "✗ MySQL/MariaDB is not running!" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Please start MySQL/MariaDB:" -ForegroundColor Yellow
    Write-Host "    - XAMPP: Open XAMPP Control Panel → Start MySQL" -ForegroundColor White
    Write-Host "    - MariaDB: Run 'net start MariaDB' as Administrator" -ForegroundColor White
    Write-Host "    - MySQL: Run 'net start MySQL' as Administrator" -ForegroundColor White
    Write-Host "    - Or: services.msc → Find MySQL/MariaDB → Start" -ForegroundColor White
    Write-Host ""
    $continue = Read-Host "Press Enter after starting MySQL/MariaDB (or 'q' to quit)"
    if ($continue -eq 'q') { exit 1 }
}

Write-Host ""

# Step 2: Check .env file
Write-Host "Step 2: Checking Configuration" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host ""

if (-not (Test-Path ".env")) {
    Write-Host "✗ .env file not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Creating .env file from template..." -ForegroundColor Yellow
    
    $envContent = @"
# Discord Bot Configuration
DISCORD_BOT_TOKEN=""

# AI API Keys (at least one required)
GEMINI_API_KEY=""
OPENAI_API_KEY=""

# Football Data API (for Sport Betting - Optional)
# Get from: https://www.football-data.org/client/register
# Enables: Champions League, Premier League, La Liga, Serie A, FIFA World Cup
FOOTBALL_DATA_API_KEY=""

# Database Configuration
DB_HOST="localhost"
DB_USER="sulfur_bot_user"
DB_PASS=""
DB_NAME="sulfur_bot"

# Bot Settings (Optional)
BOT_PREFIX="!"
"@
    
    $envContent | Out-File -FilePath ".env" -Encoding UTF8
    Write-Host "✓ Created .env template" -ForegroundColor Green
    Write-Host ""
    Write-Host "⚠ IMPORTANT: You need to fill in the .env file with your credentials!" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Required:" -ForegroundColor Cyan
    Write-Host "  1. DISCORD_BOT_TOKEN - Get from: https://discord.com/developers/applications" -ForegroundColor White
    Write-Host "  2. GEMINI_API_KEY - Get from: https://aistudio.google.com/" -ForegroundColor White
    Write-Host "     OR OPENAI_API_KEY - Get from: https://platform.openai.com/" -ForegroundColor White
    Write-Host ""
    Write-Host "Optional (for Sport Betting):" -ForegroundColor Cyan
    Write-Host "  3. FOOTBALL_DATA_API_KEY - Get from: https://www.football-data.org/" -ForegroundColor White
    Write-Host "     Enables: Champions League, Premier League, La Liga, Serie A, FIFA World Cup" -ForegroundColor White
    Write-Host ""
    
    # Open .env in notepad
    Write-Host "Opening .env file in Notepad..." -ForegroundColor Yellow
    Start-Process notepad.exe ".env"
    Write-Host ""
    Write-Host "Please edit the .env file and fill in your tokens/keys." -ForegroundColor Yellow
    $continue = Read-Host "Press Enter when done (or 'q' to quit)"
    if ($continue -eq 'q') { exit 1 }
}

# Verify .env has required fields
Write-Host "Verifying .env configuration..." -ForegroundColor Cyan
$envContent = Get-Content ".env" -Raw
$hasDiscordToken = $envContent -match 'DISCORD_BOT_TOKEN=".+"'
$hasGeminiKey = $envContent -match 'GEMINI_API_KEY=".+"'
$hasOpenAIKey = $envContent -match 'OPENAI_API_KEY=".+"'

if (-not $hasDiscordToken) {
    Write-Host "✗ DISCORD_BOT_TOKEN not set in .env" -ForegroundColor Red
    Write-Host "  Get your token from: https://discord.com/developers/applications" -ForegroundColor Yellow
    pause
    exit 1
}

if (-not $hasGeminiKey -and -not $hasOpenAIKey) {
    Write-Host "✗ No AI API key set in .env" -ForegroundColor Red
    Write-Host "  You need either GEMINI_API_KEY or OPENAI_API_KEY" -ForegroundColor Yellow
    Write-Host "  Gemini: https://aistudio.google.com/" -ForegroundColor Yellow
    Write-Host "  OpenAI: https://platform.openai.com/" -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host "✓ Configuration looks good" -ForegroundColor Green
Write-Host ""

# Step 3: Set up virtual environment
Write-Host "Step 3: Setting Up Python Virtual Environment" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host ""

if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    python -m venv venv
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Virtual environment created" -ForegroundColor Green
    } else {
        Write-Host "✗ Failed to create virtual environment" -ForegroundColor Red
        pause
        exit 1
    }
} else {
    Write-Host "✓ Virtual environment already exists" -ForegroundColor Green
}

Write-Host "Activating virtual environment..." -ForegroundColor Cyan
try {
    & "venv\Scripts\Activate.ps1"
    Write-Host "✓ Virtual environment activated" -ForegroundColor Green
} catch {
    Write-Host "⚠ Could not activate virtual environment: $_" -ForegroundColor Yellow
    Write-Host "  Continuing anyway..." -ForegroundColor Gray
}

Write-Host ""

# Step 4: Install dependencies
Write-Host "Step 4: Installing Python Dependencies" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host ""

Write-Host "Upgrading pip..." -ForegroundColor Cyan
python -m pip install --upgrade pip --quiet

Write-Host "Installing dependencies from requirements.txt..." -ForegroundColor Cyan
Write-Host "(This may take a few minutes...)" -ForegroundColor Gray
pip install -r requirements.txt

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ All dependencies installed" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to install some dependencies" -ForegroundColor Red
    Write-Host "  Please check the error messages above" -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host ""

# Step 5: Set up database
Write-Host "Step 5: Setting Up Database" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host ""

Write-Host "Running database setup script..." -ForegroundColor Cyan
& "$scriptPath\setup_mysql.ps1"

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Database setup failed" -ForegroundColor Red
    pause
    exit 1
}

Write-Host ""

# Step 6: Run tests
Write-Host "Step 6: Testing Setup" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host ""

Write-Host "Running setup verification..." -ForegroundColor Cyan
python test_setup.py

Write-Host ""

# Step 7: Final instructions
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                    Setup Complete! 🎉                      ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "1. Customize bot personality:" -ForegroundColor White
Write-Host "   - Edit config\system_prompt.txt" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Configure bot settings:" -ForegroundColor White
Write-Host "   - Edit config\config.json" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Invite bot to your Discord server:" -ForegroundColor White
Write-Host "   - Go to: https://discord.com/developers/applications" -ForegroundColor Gray
Write-Host "   - Select your application → OAuth2 → URL Generator" -ForegroundColor Gray
Write-Host "   - Select scopes: bot, applications.commands" -ForegroundColor Gray
Write-Host "   - Select permissions: Administrator (or specific permissions)" -ForegroundColor Gray
Write-Host "   - Copy and open the generated URL" -ForegroundColor Gray
Write-Host ""
Write-Host "4. Start the bot:" -ForegroundColor White
Write-Host "   - Run: .\start.ps1" -ForegroundColor Gray
Write-Host "   - Or double-click: start.bat" -ForegroundColor Gray
Write-Host ""
Write-Host "Web Dashboard will be available at: http://localhost:5000" -ForegroundColor Cyan
Write-Host ""

$start = Read-Host "Would you like to start the bot now? (y/n)"
if ($start -eq 'y' -or $start -eq 'Y') {
    Write-Host ""
    Write-Host "Starting bot..." -ForegroundColor Cyan
    & "$scriptPath\start.ps1"
} else {
    Write-Host ""
    Write-Host "You can start the bot later by running: .\start.ps1" -ForegroundColor Yellow
    Write-Host ""
}
