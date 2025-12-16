# ============================================================
# Sulfur Discord Bot - Windows Installation Wizard
# ============================================================
# This wizard makes setting up the Sulfur bot a breeze!
# Features:
#   - Automated prerequisite detection and installation guidance
#   - Interactive .env configuration with validation
#   - MySQL/MariaDB setup and database initialization
#   - Virtual environment and dependency management
#   - Desktop shortcuts and easy startup
#   - Comprehensive error handling and troubleshooting
#
# Usage: Right-click > Run with PowerShell
# ============================================================

param(
    [switch]$SkipPrerequisites,
    [switch]$SkipDatabase,
    [switch]$SkipDependencies,
    [string]$InstallDir = ""
)

$ErrorActionPreference = 'Continue'

# Determine installation path
if ([string]::IsNullOrWhiteSpace($InstallDir)) {
    $script:InstallPath = Split-Path -Parent $MyInvocation.MyCommand.Path
} else {
    # User specified a custom install directory
    $script:InstallPath = $InstallDir
    if (-not (Test-Path $script:InstallPath)) {
        New-Item -ItemType Directory -Path $script:InstallPath -Force | Out-Null
    }
}
Set-Location $script:InstallPath

# Color scheme
$ColorHeader = "Cyan"
$ColorSuccess = "Green"
$ColorWarning = "Yellow"
$ColorError = "Red"
$ColorInfo = "White"
$ColorPrompt = "Cyan"

# Progress tracking
$script:SetupSteps = @{
    Prerequisites = $false
    Environment = $false
    Database = $false
    Dependencies = $false
    Testing = $false
    Shortcuts = $false
}

# Helper Functions
# ============================================================

function Write-Header {
    param([string]$Text)
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor $ColorHeader
    Write-Host "  $Text" -ForegroundColor $ColorHeader
    Write-Host "============================================================" -ForegroundColor $ColorHeader
    Write-Host ""
}

function Write-Step {
    param([string]$Text)
    Write-Host ""
    Write-Host "=> $Text" -ForegroundColor $ColorInfo
    Write-Host "------------------------------------------------------------" -ForegroundColor DarkGray
}

function Write-Success {
    param([string]$Text)
    Write-Host "  [OK] $Text" -ForegroundColor $ColorSuccess
}

function Write-Warning {
    param([string]$Text)
    Write-Host "  [!] $Text" -ForegroundColor $ColorWarning
}

function Write-Error {
    param([string]$Text)
    Write-Host "  [X] $Text" -ForegroundColor $ColorError
}

function Write-Info {
    param([string]$Text)
    Write-Host "  [i] $Text" -ForegroundColor $ColorInfo
}

function Read-YesNo {
    param(
        [string]$Prompt,
        [bool]$Default = $true
    )
    $defaultText = if ($Default) { "Y/n" } else { "y/N" }
    $response = Read-Host "$Prompt [$defaultText]"
    if ([string]::IsNullOrWhiteSpace($response)) {
        return $Default
    }
    return $response -match "^[Yy]"
}

function Test-AdminPrivileges {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Open-URL {
    param([string]$URL)
    Start-Process $URL
    Write-Info "Opened in your browser: $URL"
}

# Welcome Screen
# ============================================================

Clear-Host
Write-Header "Welcome to Sulfur Discord Bot Setup Wizard"

Write-Host "This wizard will guide you through setting up the Sulfur Discord Bot." -ForegroundColor $ColorInfo
Write-Host "The process includes:" -ForegroundColor $ColorInfo
Write-Host ""
Write-Host "  1. Checking and installing prerequisites" -ForegroundColor Gray
Write-Host "  2. Configuring your bot settings" -ForegroundColor Gray
Write-Host "  3. Installing dependencies" -ForegroundColor Gray
Write-Host "  4. Setting up the database" -ForegroundColor Gray
Write-Host "  5. Testing the setup" -ForegroundColor Gray
Write-Host "  6. Creating shortcuts for easy access" -ForegroundColor Gray
Write-Host ""
Write-Host "Estimated time: 10-15 minutes (depending on download speeds)" -ForegroundColor DarkGray
Write-Host ""

# Ask for custom installation path if not already specified via parameter
if ([string]::IsNullOrWhiteSpace($InstallDir)) {
    Write-Host ""
    Write-Host "Installation Path Configuration" -ForegroundColor $ColorPrompt
    Write-Host "Current path: $script:InstallPath" -ForegroundColor Gray
    Write-Host ""
    
    if (Read-YesNo "Use current directory as installation path?" -Default $true) {
        Write-Success "Using current directory: $script:InstallPath"
    } else {
        $customPath = Read-Host "Enter custom installation path (or press Enter to cancel)"
        if (-not [string]::IsNullOrWhiteSpace($customPath)) {
            $customPath = $customPath.Trim().Trim('"').Trim("'")
            if (-not (Test-Path $customPath)) {
                Write-Info "Creating directory: $customPath"
                New-Item -ItemType Directory -Path $customPath -Force | Out-Null
            }
            $script:InstallPath = $customPath
            Set-Location $script:InstallPath
            Write-Success "Installation path set to: $script:InstallPath"
        } else {
            Write-Info "Keeping current directory: $script:InstallPath"
        }
    }
    Write-Host ""
}

if (!(Read-YesNo "Ready to begin?")) {
    Write-Host ""
    Write-Warning "Setup cancelled. You can run this wizard again anytime."
    exit 0
}

# Step 1: Check Prerequisites
# ============================================================

if (!$SkipPrerequisites) {
    Write-Header "Step 1: Checking Prerequisites"
    
    $allPrereqsMet = $true
    
    # Check Python
    Write-Step "Checking Python..."
    try {
        $pythonVersion = python --version 2>&1 | Out-String
        if ($pythonVersion -match "Python (\d+)\.(\d+)") {
            $major = [int]$matches[1]
            $minor = [int]$matches[2]
            if ($major -ge 3 -and $minor -ge 8) {
                Write-Success "Python $major.$minor detected - Compatible"
            } else {
                Write-Warning "Python $major.$minor detected - Version 3.8+ recommended"
                if (Read-YesNo "Continue anyway?") {
                    Write-Success "Continuing with current Python version"
                } else {
                    $allPrereqsMet = $false
                }
            }
        }
    } catch {
        Write-Error "Python not found!"
        Write-Info "Python 3.8+ is required to run the bot."
        Write-Host ""
        if (Read-YesNo "Would you like to download Python now?") {
            Open-URL "https://www.python.org/downloads/"
            Write-Host ""
            Write-Warning "Please install Python, then run this wizard again."
            Write-Warning "IMPORTANT: Check 'Add Python to PATH' during installation!"
            exit 1
        }
        $allPrereqsMet = $false
    }
    
    # Check Git
    Write-Step "Checking Git..."
    try {
        $gitVersion = git --version 2>&1 | Out-String
        Write-Success "Git detected - $($gitVersion.Trim())"
    } catch {
        Write-Error "Git not found!"
        Write-Info "Git is required for auto-updates and maintenance features."
        Write-Host ""
        if (Read-YesNo "Would you like to download Git now?") {
            Open-URL "https://git-scm.com/download/win"
            Write-Host ""
            Write-Warning "Please install Git, then run this wizard again."
            exit 1
        }
        Write-Warning "Continuing without Git - Auto-updates will not work"
    }
    
    # Check MySQL/MariaDB
    Write-Step "Checking MySQL/MariaDB..."
    $mysqlProcess = Get-Process mysqld,mariadbd -ErrorAction SilentlyContinue | Select-Object -First 1
    
    if ($mysqlProcess) {
        Write-Success "MySQL/MariaDB is running (PID: $($mysqlProcess.Id))"
    } else {
        Write-Warning "MySQL/MariaDB is not running"
        Write-Info "The bot requires MySQL or MariaDB for data storage."
        Write-Host ""
        
        # Try to start MySQL service
        $mysqlService = Get-Service -Name "MySQL*","MariaDB*" -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($mysqlService) {
            Write-Info "Found $($mysqlService.Name) service"
            if (Read-YesNo "Would you like to start it now?") {
                try {
                    Start-Service -Name $mysqlService.Name -ErrorAction Stop
                    Start-Sleep -Seconds 3
                    $mysqlProcess = Get-Process mysqld,mariadbd -ErrorAction SilentlyContinue | Select-Object -First 1
                    if ($mysqlProcess) {
                        Write-Success "MySQL/MariaDB started successfully"
                    } else {
                        Write-Warning "Service started but process not detected"
                    }
                } catch {
                    Write-Error "Failed to start MySQL service: $_"
                    Write-Warning "You may need administrator privileges"
                }
            }
        } else {
            Write-Warning "No MySQL/MariaDB installation detected"
            Write-Host ""
            Write-Info "You can install:"
            Write-Host "  1. XAMPP (easiest for beginners) - https://www.apachefriends.org/" -ForegroundColor Gray
            Write-Host "  2. MySQL Server - https://dev.mysql.com/downloads/installer/" -ForegroundColor Gray
            Write-Host "  3. MariaDB - https://mariadb.org/download/" -ForegroundColor Gray
            Write-Host ""
            
            if (Read-YesNo "Would you like to open the XAMPP download page?") {
                Open-URL "https://www.apachefriends.org/"
            }
            
            Write-Host ""
            Write-Warning "Please install and start MySQL/MariaDB, then run this wizard again."
            exit 1
        }
    }
    
    # Summary
    if ($allPrereqsMet) {
        Write-Host ""
        Write-Success "All prerequisites are met!"
        $script:SetupSteps.Prerequisites = $true
    } else {
        Write-Host ""
        Write-Error "Some prerequisites are missing. Please install them and run this wizard again."
        exit 1
    }
}

# Step 2: Configure Environment (.env file)
# ============================================================

Write-Header "Step 2: Bot Configuration"

$envPath = Join-Path $script:InstallPath ".env"
$envExamplePath = Join-Path $script:InstallPath ".env.example"

if (Test-Path $envPath) {
    Write-Info "Found existing .env file"
    if (!(Read-YesNo "Would you like to reconfigure it?")) {
        Write-Success "Using existing configuration"
        $script:SetupSteps.Environment = $true
    } else {
        Remove-Item $envPath -Force
    }
}

if (!(Test-Path $envPath)) {
    Write-Step "Creating .env configuration..."
    Write-Host ""
    Write-Info "We'll need a few pieces of information to configure your bot:"
    Write-Host ""
    
    # Discord Bot Token
    Write-Host "  1. Discord Bot Token" -ForegroundColor $ColorPrompt
    Write-Host "     Get it from: https://discord.com/developers/applications" -ForegroundColor DarkGray
    Write-Host ""
    if (Read-YesNo "     Open Discord Developer Portal now?") {
        Open-URL "https://discord.com/developers/applications"
        Write-Host ""
        Write-Info "Steps to get your bot token:"
        Write-Host "     â€¢ Click 'New Application' (or select existing)" -ForegroundColor DarkGray
        Write-Host "     â€¢ Go to 'Bot' section -> 'Reset Token' -> Copy" -ForegroundColor DarkGray
        Write-Host "     â€¢ Enable these intents:" -ForegroundColor DarkGray
        Write-Host "       - Message Content Intent" -ForegroundColor DarkGray
        Write-Host "       - Server Members Intent" -ForegroundColor DarkGray
        Write-Host "       - Presence Intent" -ForegroundColor DarkGray
        Write-Host ""
    }
    
    $discordToken = ""
    while ([string]::IsNullOrWhiteSpace($discordToken)) {
        $discordToken = Read-Host "     Enter your Discord Bot Token"
        if ([string]::IsNullOrWhiteSpace($discordToken)) {
            Write-Warning "Token cannot be empty!"
        }
    }
    
    Write-Host ""
    
    # Gemini API Key
    Write-Host "  2. Gemini API Key (Recommended - Has free tier)" -ForegroundColor $ColorPrompt
    Write-Host "     Get it from: https://aistudio.google.com/apikey" -ForegroundColor DarkGray
    Write-Host ""
    if (Read-YesNo "     Open Google AI Studio now?") {
        Open-URL "https://aistudio.google.com/apikey"
        Write-Host ""
        Write-Info "Click 'Create API Key' and copy it"
        Write-Host ""
    }
    
    $geminiKey = Read-Host "     Enter your Gemini API Key (or press Enter to skip)"
    Write-Host ""
    
    # OpenAI API Key
    Write-Host "  3. OpenAI API Key (Optional - Paid service)" -ForegroundColor $ColorPrompt
    Write-Host "     Get it from: https://platform.openai.com/api-keys" -ForegroundColor DarkGray
    Write-Host ""
    
    $openaiKey = ""
    if ([string]::IsNullOrWhiteSpace($geminiKey)) {
        Write-Warning "No Gemini key provided. OpenAI key is required."
        while ([string]::IsNullOrWhiteSpace($openaiKey)) {
            if (Read-YesNo "     Open OpenAI API Keys page?") {
                Open-URL "https://platform.openai.com/api-keys"
                Write-Host ""
            }
            $openaiKey = Read-Host "     Enter your OpenAI API Key"
            if ([string]::IsNullOrWhiteSpace($openaiKey)) {
                Write-Warning "At least one AI API key is required!"
            }
        }
    } else {
        $openaiKey = Read-Host "     Enter your OpenAI API Key (or press Enter to skip)"
    }
    
    Write-Host ""
    
    # Football-Data.org API Key
    Write-Host "  4. Football-Data.org API Key (Optional - For Sport Betting)" -ForegroundColor $ColorPrompt
    Write-Host "     Get it from: https://www.football-data.org/client/register" -ForegroundColor DarkGray
    Write-Host "     Free tier available - Enables: Champions League, Premier League, World Cup" -ForegroundColor DarkGray
    Write-Host ""
    if (Read-YesNo "     Open Football-Data.org registration page?") {
        Open-URL "https://www.football-data.org/client/register"
        Write-Host ""
    }
    $footballDataKey = Read-Host "     Enter your Football-Data.org API Key (or press Enter to skip)"
    
    Write-Host ""
    
    # Database Configuration
    Write-Host "  5. Database Configuration" -ForegroundColor $ColorPrompt
    Write-Host ""
    $dbHost = Read-Host "     Database Host (default: localhost)"
    if ([string]::IsNullOrWhiteSpace($dbHost)) { $dbHost = "localhost" }
    
    $dbUser = Read-Host "     Database User (default: sulfur_bot_user)"
    if ([string]::IsNullOrWhiteSpace($dbUser)) { $dbUser = "sulfur_bot_user" }
    
    $dbPass = Read-Host "     Database Password (default: empty)"
    
    $dbName = Read-Host "     Database Name (default: sulfur_bot)"
    if ([string]::IsNullOrWhiteSpace($dbName)) { $dbName = "sulfur_bot" }
    
    Write-Host ""
    
    # Optional: Bot Prefix
    $botPrefix = Read-Host "  6. Bot Command Prefix (default: !)"
    if ([string]::IsNullOrWhiteSpace($botPrefix)) { $botPrefix = "!" }
    
    # Optional: Owner ID
    Write-Host ""
    Write-Info "Your Discord User ID (optional - for owner-only commands)"
    Write-Info "To find it: Enable Developer Mode in Discord -> Right-click your name -> Copy ID"
    $ownerId = Read-Host "  7. Your Discord User ID (or press Enter to skip)"
    
    # Create .env file
    Write-Host ""
    Write-Step "Creating .env file..."
    
    $envContent = @"
# ============================================================
# Sulfur Discord Bot - Configuration
# Generated by Installation Wizard
# ============================================================

# Discord Bot Token
DISCORD_BOT_TOKEN="$discordToken"

# AI API Keys
GEMINI_API_KEY="$geminiKey"
OPENAI_API_KEY="$openaiKey"

# Football Data API (for Sport Betting)
# Enables: Champions League, Premier League, La Liga, Serie A, FIFA World Cup
FOOTBALL_DATA_API_KEY="$footballDataKey"

# Database Configuration
DB_HOST=$dbHost
DB_USER=$dbUser
DB_PASS=$dbPass
DB_NAME=$dbName

# Bot Settings
BOT_PREFIX=$botPrefix
$(if (![string]::IsNullOrWhiteSpace($ownerId)) { "OWNER_ID=$ownerId" } else { "# OWNER_ID=" })

# Advanced Settings (optional)
# LOG_LEVEL=INFO
# WEB_DASHBOARD_PORT=5000
# DB_POOL_SIZE=5
"@
    
    $envContent | Out-File -FilePath $envPath -Encoding UTF8 -NoNewline
    Write-Success "Configuration saved to .env"
    $script:SetupSteps.Environment = $true
}

# Step 3: Install Dependencies
# ============================================================

if (!$SkipDependencies) {
    Write-Header "Step 3: Installing Dependencies"
    
    # Check for virtual environment
    $venvPath = Join-Path $script:InstallPath "venv"
    $venvActivate = Join-Path $venvPath "Scripts\Activate.ps1"
    
    if (!(Test-Path $venvPath)) {
        Write-Step "Creating Python virtual environment..."
        Write-Info "This keeps bot dependencies separate from your system Python"
        Write-Host ""
        
        try {
            python -m venv venv
            if ($LASTEXITCODE -eq 0) {
                Write-Success "Virtual environment created"
            } else {
                Write-Warning "Failed to create virtual environment"
                Write-Info "Continuing without virtual environment..."
            }
        } catch {
            Write-Warning "Could not create virtual environment: $_"
            Write-Info "Continuing without virtual environment..."
        }
    } else {
        Write-Success "Virtual environment already exists"
    }
    
    # Activate virtual environment
    if (Test-Path $venvActivate) {
        Write-Step "Activating virtual environment..."
        try {
            & $venvActivate
            Write-Success "Virtual environment activated"
        } catch {
            Write-Warning "Could not activate virtual environment: $_"
        }
    }
    
    # Install dependencies
    Write-Step "Installing Python dependencies..."
    Write-Info "This may take a few minutes depending on your internet connection..."
    Write-Host ""
    
    $requirementsPath = Join-Path $script:InstallPath "requirements.txt"
    if (Test-Path $requirementsPath) {
        try {
            # Upgrade pip first
            Write-Host "  Upgrading pip..." -ForegroundColor DarkGray
            python -m pip install --upgrade pip --quiet 2>&1 | Out-Null
            
            # Install requirements
            Write-Host "  Installing packages..." -ForegroundColor DarkGray
            pip install -r requirements.txt
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host ""
                Write-Success "All dependencies installed successfully"
                $script:SetupSteps.Dependencies = $true
            } else {
                Write-Host ""
                Write-Warning "Some dependencies may have failed to install"
                Write-Info "The bot might still work, but some features may be unavailable"
                if (!(Read-YesNo "Continue anyway?")) {
                    exit 1
                }
            }
        } catch {
            Write-Error "Failed to install dependencies: $_"
            if (!(Read-YesNo "Continue anyway?")) {
                exit 1
            }
        }
    } else {
        Write-Error "requirements.txt not found!"
        Write-Warning "Cannot install dependencies"
    }
}

# Step 4: Database Setup
# ============================================================

if (!$SkipDatabase) {
    Write-Header "Step 4: Database Setup"
    
    Write-Info "We'll now set up the MySQL/MariaDB database for the bot."
    Write-Host ""
    
    # Check if database already exists
    Write-Step "Checking database status..."
    
    $dbExists = $false
    try {
        # Try to connect to the database
        $pythonScript = @"
import mysql.connector
import os
from dotenv import load_dotenv
load_dotenv()
try:
    conn = mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'sulfur_bot_user'),
        password=os.getenv('DB_PASS', ''),
        database=os.getenv('DB_NAME', 'sulfur_bot'),
        connection_timeout=5
    )
    conn.close()
    print('EXISTS')
except:
    print('NOT_EXISTS')
"@
        $testResult = python -c $pythonScript 2>&1
        $dbExists = $testResult -match "EXISTS"
    } catch {
        $dbExists = $false
    }
    
    if ($dbExists) {
        Write-Success "Database connection successful - Database already configured"
        if (!(Read-YesNo "Would you like to reinitialize the database? (This will reset data)")) {
            Write-Info "Skipping database setup"
            $script:SetupSteps.Database = $true
        } else {
            $dbExists = $false
        }
    }
    
    if (!$dbExists) {
        Write-Step "Setting up database..."
        
        # Check if setup_wizard.py exists
        $wizardPath = Join-Path $script:InstallPath "setup_wizard.py"
        if (Test-Path $wizardPath) {
            Write-Info "Running database setup wizard..."
            Write-Host ""
            
            try {
                python $wizardPath
                if ($LASTEXITCODE -eq 0) {
                    Write-Host ""
                    Write-Success "Database setup completed successfully"
                    
                    # Run migrations
                    Write-Step "Applying database migrations..."
                    $migrationPath = Join-Path $script:InstallPath "apply_migration.py"
                    if (Test-Path $migrationPath) {
                        python $migrationPath
                        if ($LASTEXITCODE -eq 0) {
                            Write-Success "Database tables created"
                        } else {
                            Write-Warning "Migration had issues but continuing..."
                        }
                    }
                    
                    $script:SetupSteps.Database = $true
                } else {
                    Write-Error "Database setup failed"
                    Write-Warning "Please check the error messages above"
                    if (!(Read-YesNo "Continue anyway?")) {
                        exit 1
                    }
                }
            } catch {
                Write-Error "Failed to run database setup: $_"
                Write-Warning "You may need to set up the database manually"
                if (!(Read-YesNo "Continue anyway?")) {
                    exit 1
                }
            }
        } else {
            Write-Warning "Database setup wizard not found"
            Write-Info "You can set up the database manually using setup_mysql.ps1"
        }
    }
}

# Step 5: Test Setup
# ============================================================

Write-Header "Step 5: Testing Setup"

Write-Info "Running setup verification..."
Write-Host ""

$testSetupPath = Join-Path $script:InstallPath "test_setup.py"
if (Test-Path $testSetupPath) {
    try {
        python $testSetupPath
        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Success "Setup verification passed!"
            $script:SetupSteps.Testing = $true
        } else {
            Write-Host ""
            Write-Warning "Setup verification found some issues"
            Write-Info "Review the messages above and fix any problems"
            if (!(Read-YesNo "Continue anyway?")) {
                exit 1
            }
        }
    } catch {
        Write-Warning "Could not run setup verification: $_"
    }
} else {
    Write-Warning "test_setup.py not found - skipping verification"
}

# Step 6: Create Shortcuts
# ============================================================

Write-Header "Step 6: Creating Shortcuts"

if (Read-YesNo "Would you like to create desktop shortcuts?") {
    Write-Step "Creating shortcuts..."
    
    $WshShell = New-Object -comObject WScript.Shell
    $desktopPath = [Environment]::GetFolderPath("Desktop")
    
    # Start Bot Shortcut - Now runs maintain_bot.ps1 directly for proper startup
    try {
        $shortcutPath = Join-Path $desktopPath "Start Sulfur Bot.lnk"
        $shortcut = $WshShell.CreateShortcut($shortcutPath)
        $shortcut.TargetPath = "powershell.exe"
        # Run maintain_bot.ps1 directly - this starts the database, web dashboard, and bot together
        $shortcut.Arguments = "-ExecutionPolicy Bypass -NoExit -File `"$(Join-Path $script:InstallPath 'maintain_bot.ps1')`""
        $shortcut.WorkingDirectory = $script:InstallPath
        $shortcut.Description = "Start Sulfur Discord Bot with Database and Web Dashboard"
        $shortcut.IconLocation = "powershell.exe,0"
        $shortcut.Save()
        Write-Success "Created 'Start Sulfur Bot' shortcut on desktop"
        Write-Info "This shortcut starts the bot with the maintenance script (includes database & web dashboard)"
    } catch {
        Write-Warning "Could not create start shortcut: $_"
    }
    
    # Web Dashboard Shortcut
    try {
        $shortcutPath = Join-Path $desktopPath "Sulfur Web Dashboard.lnk"
        $shortcut = $WshShell.CreateShortcut($shortcutPath)
        $shortcut.TargetPath = "http://localhost:5000"
        $shortcut.Description = "Open Sulfur Bot Web Dashboard"
        $shortcut.Save()
        Write-Success "Created 'Sulfur Web Dashboard' shortcut on desktop"
    } catch {
        Write-Warning "Could not create dashboard shortcut: $_"
    }
    
    # Installation Folder Shortcut
    try {
        $shortcutPath = Join-Path $desktopPath "Sulfur Bot Folder.lnk"
        $shortcut = $WshShell.CreateShortcut($shortcutPath)
        $shortcut.TargetPath = $script:InstallPath
        $shortcut.Description = "Open Sulfur Bot installation folder"
        $shortcut.Save()
        Write-Success "Created 'Sulfur Bot Folder' shortcut on desktop"
    } catch {
        Write-Warning "Could not create folder shortcut: $_"
    }
    
    $script:SetupSteps.Shortcuts = $true
}

# Completion Summary
# ============================================================

Write-Header "Setup Complete! ðŸŽ‰"

Write-Host "Congratulations! Your Sulfur Discord Bot is ready to use!" -ForegroundColor $ColorSuccess
Write-Host ""

# Show completed steps
Write-Host "Setup Summary:" -ForegroundColor $ColorInfo
Write-Host "â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”" -ForegroundColor DarkGray
foreach ($step in $script:SetupSteps.Keys | Sort-Object) {
    $status = if ($script:SetupSteps[$step]) { "[OK]" } else { "[ ]" }
    $color = if ($script:SetupSteps[$step]) { $ColorSuccess } else { $ColorWarning }
    Write-Host "  $status $step" -ForegroundColor $color
}
Write-Host ""

# Next steps
Write-Host "Next Steps:" -ForegroundColor $ColorPrompt
Write-Host ""
Write-Host "  1. Invite the bot to your Discord server:" -ForegroundColor $ColorInfo
Write-Host "     â€¢ Go to: https://discord.com/developers/applications" -ForegroundColor DarkGray
Write-Host "     â€¢ Select your application -> OAuth2 -> URL Generator" -ForegroundColor DarkGray
Write-Host "     â€¢ Select scopes: bot, applications.commands" -ForegroundColor DarkGray
Write-Host "     â€¢ Select permissions: Administrator (or specific permissions)" -ForegroundColor DarkGray
Write-Host "     â€¢ Copy and open the generated URL" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  2. Customize your bot:" -ForegroundColor $ColorInfo
Write-Host "     â€¢ Edit config\system_prompt.txt for personality" -ForegroundColor DarkGray
Write-Host "     â€¢ Edit config\config.json for settings" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  3. Start the bot:" -ForegroundColor $ColorInfo
Write-Host "     â€¢ Double-click 'Start Sulfur Bot' on your desktop" -ForegroundColor DarkGray
Write-Host "     â€¢ Or run: .\start.ps1 or .\start.bat" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  4. Monitor the bot:" -ForegroundColor $ColorInfo
Write-Host "     â€¢ Web Dashboard: http://localhost:5000" -ForegroundColor DarkGray
Write-Host "     â€¢ Logs are in the 'logs' folder" -ForegroundColor DarkGray
Write-Host ""

# Offer to start now
if (Read-YesNo "Would you like to start the bot now?") {
    Write-Host ""
    Write-Info "Starting Sulfur Bot..."
    Write-Host ""
    
    $startScript = Join-Path $script:InstallPath "start.ps1"
    if (Test-Path $startScript) {
        & powershell.exe -ExecutionPolicy Bypass -NoExit -File $startScript
    } else {
        Write-Error "start.ps1 not found!"
        Write-Info "You can start the bot manually later"
    }
} else {
    Write-Host ""
    Write-Info "You can start the bot anytime by running start.ps1 or using the desktop shortcut"
    Write-Host ""
    Write-Host "Thank you for using Sulfur Discord Bot!" -ForegroundColor $ColorSuccess
    Write-Host ""
    Write-Host "Press any key to exit..." -ForegroundColor DarkGray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
