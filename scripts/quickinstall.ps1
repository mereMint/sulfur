# ==============================================================================
# Sulfur Bot - One-Command Quick Installer for Windows
# ==============================================================================
# Run this script with:
#   irm https://raw.githubusercontent.com/mereMint/sulfur/main/scripts/quickinstall.ps1 | iex
# Or:
#   Set-ExecutionPolicy Bypass -Scope Process; .\scripts\quickinstall.ps1
# ==============================================================================

# Detect if running in non-interactive mode (piped input)
$INTERACTIVE = -not ([Console]::IsInputRedirected)

if (-not $INTERACTIVE) {
    Write-Host "Note: Running in non-interactive mode (piped from PowerShell)" -ForegroundColor Yellow
}

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

# Colors
function Write-ColorHost {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

function Write-Success { Write-ColorHost "✅ $args" "Green" }
function Write-Warning { Write-ColorHost "⚠️  $args" "Yellow" }
function Write-Error { Write-ColorHost "❌ $args" "Red" }
function Write-Info { Write-ColorHost "ℹ️  $args" "Cyan" }
function Write-Step { Write-ColorHost "→ $args" "Magenta" }

# Banner
Write-Host ""
Write-ColorHost "╔══════════════════════════════════════════════════════════════════╗" "Cyan"
Write-ColorHost "║                                                                  ║" "Cyan"
Write-ColorHost "║      ███████╗██╗   ██╗██╗     ███████╗██╗   ██╗██████╗          ║" "Cyan"
Write-ColorHost "║      ██╔════╝██║   ██║██║     ██╔════╝██║   ██║██╔══██╗         ║" "Cyan"
Write-ColorHost "║      ███████╗██║   ██║██║     █████╗  ██║   ██║██████╔╝         ║" "Cyan"
Write-ColorHost "║      ╚════██║██║   ██║██║     ██╔══╝  ██║   ██║██╔══██╗         ║" "Cyan"
Write-ColorHost "║      ███████║╚██████╔╝███████╗██║     ╚██████╔╝██║  ██║         ║" "Cyan"
Write-ColorHost "║      ╚══════╝ ╚═════╝ ╚══════╝╚═╝      ╚═════╝ ╚═╝  ╚═╝         ║" "Cyan"
Write-ColorHost "║                                                                  ║" "Cyan"
Write-ColorHost "║              🤖 Discord Bot Quick Installer                      ║" "Cyan"
Write-ColorHost "╚══════════════════════════════════════════════════════════════════╝" "Cyan"
Write-Host ""

Write-Success "Detected platform: Windows"
if ($isAdmin) {
    Write-Success "Running as Administrator"
} else {
    Write-Warning "Not running as Administrator. Some features may require elevation."
}

# Installation directory
$InstallDir = "$env:USERPROFILE\sulfur"

# Check for Chocolatey
function Install-Chocolatey {
    if (Get-Command choco -ErrorAction SilentlyContinue) {
        Write-Success "Chocolatey package manager found"
        return $true
    }
    
    Write-Step "Installing Chocolatey package manager..."
    try {
        Set-ExecutionPolicy Bypass -Scope Process -Force
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
        Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
        
        # Refresh environment
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
        
        Write-Success "Chocolatey installed"
        return $true
    }
    catch {
        Write-Error "Failed to install Chocolatey: $_"
        return $false
    }
}

# Check and install Python
function Install-Python {
    Write-Host ""
    Write-ColorHost "🐍 Checking Python installation..." "Blue"
    
    $python = Get-Command python -ErrorAction SilentlyContinue
    
    if ($python) {
        $version = & python --version 2>&1
        Write-Success "Python found: $version"
        return $true
    }
    
    Write-Step "Installing Python..."
    
    if (Get-Command choco -ErrorAction SilentlyContinue) {
        choco install python -y
        
        # Refresh environment
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
        
        Write-Success "Python installed via Chocolatey"
    }
    else {
        Write-Info "Please download Python from https://www.python.org/downloads/"
        Write-Info "Make sure to check 'Add Python to PATH' during installation"
        Start-Process "https://www.python.org/downloads/"
        if ($INTERACTIVE) {
            Read-Host "Press Enter after installing Python..."
        } else {
            Write-Host "Please install Python 3.8+ manually: https://www.python.org/downloads/" -ForegroundColor Yellow
        }
    }
    
    return (Get-Command python -ErrorAction SilentlyContinue) -ne $null
}

# Check and install Git
function Install-Git {
    Write-Host ""
    Write-ColorHost "📚 Checking Git installation..." "Blue"
    
    if (Get-Command git -ErrorAction SilentlyContinue) {
        $version = & git --version
        Write-Success $version
        return $true
    }
    
    Write-Step "Installing Git..."
    
    if (Get-Command choco -ErrorAction SilentlyContinue) {
        choco install git -y
        
        # Refresh environment
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
        
        Write-Success "Git installed"
    }
    else {
        Write-Info "Please download Git from https://git-scm.com/download/win"
        Start-Process "https://git-scm.com/download/win"
        if ($INTERACTIVE) {
            Read-Host "Press Enter after installing Git..."
        } else {
            Write-Host "Please install Git manually: https://git-scm.com/download/win" -ForegroundColor Yellow
        }
    }
    
    return (Get-Command git -ErrorAction SilentlyContinue) -ne $null
}

# Clone or update repository
function Setup-Repository {
    Write-Host ""
    Write-ColorHost "📁 Setting up repository..." "Blue"
    
    if (Test-Path $InstallDir) {
        Write-Info "Sulfur directory already exists at $InstallDir"
        if ($INTERACTIVE) {
            $update = Read-Host "Update to latest version? [Y/n]"
        } else {
            $update = "y"
            Write-Host "Updating to latest version (non-interactive mode)" -ForegroundColor Yellow
        }
        
        if ($update -ne "n" -and $update -ne "N") {
            Write-Step "Updating repository..."
            Set-Location $InstallDir
            
            # Reset any local changes to always use remote files (public repo)
            Write-Host "   Discarding local changes (using remote files)..." -ForegroundColor Yellow
            git fetch origin 2>&1 | Out-Null
            git reset --hard origin/main 2>&1 | Out-Null
            if($LASTEXITCODE -ne 0){
                git reset --hard origin/master 2>&1 | Out-Null
            }
            Write-Host "✅ Updated to latest version" -ForegroundColor Green
        }
    }
    else {
        Write-Step "Cloning Sulfur Bot repository..."
        git clone https://github.com/mereMint/sulfur.git $InstallDir
    }
    
    Set-Location $InstallDir
}

# Setup Python virtual environment
function Setup-VirtualEnv {
    Write-Host ""
    Write-ColorHost "🐍 Setting up Python environment..." "Blue"
    
    if (-not (Test-Path "venv")) {
        Write-Step "Creating virtual environment..."
        & python -m venv venv
        Write-Success "Virtual environment created"
    }
    else {
        Write-Success "Virtual environment already exists"
    }
    
    # Activate virtual environment
    Write-Step "Activating virtual environment..."
    & .\venv\Scripts\Activate.ps1
    
    # Upgrade pip
    Write-Step "Upgrading pip..."
    & python -m pip install --upgrade pip
    
    # Install dependencies
    Write-Step "Installing Python dependencies..."
    & pip install -r requirements.txt
    
    Write-Success "Python dependencies installed"
}

# Interactive setup wizard
function Run-SetupWizard {
    Write-Host ""
    Write-ColorHost "═══════════════════════════════════════════════════════════════" "Magenta"
    Write-ColorHost "                    📝 Configuration" "White"
    Write-ColorHost "═══════════════════════════════════════════════════════════════" "Magenta"
    Write-Host ""
    
    if ($INTERACTIVE) {
        $runWizard = Read-Host "Run the interactive setup wizard? [Y/n]"
    } else {
        $runWizard = "n"
        Write-Host "Skipping interactive setup wizard (non-interactive mode)" -ForegroundColor Yellow
    }
    
    if ($runWizard -ne "n" -and $runWizard -ne "N") {
        & .\venv\Scripts\Activate.ps1
        & python master_setup.py
    }
    else {
        Write-Host ""
        Write-Info "You can run the setup wizard later with:"
        Write-Host "  cd $InstallDir"
        Write-Host "  .\venv\Scripts\Activate.ps1"
        Write-Host "  python master_setup.py"
    }
}

# Create desktop shortcut
function Create-Shortcut {
    if (-not $INTERACTIVE) {
        Write-Host "Skipping desktop shortcut creation (non-interactive mode)" -ForegroundColor Yellow
        return
    }
    
    $createShortcut = Read-Host "Create desktop shortcut? [Y/n]"
    if ($createShortcut -eq "n" -or $createShortcut -eq "N") {
        return
    }
    
    try {
        $WshShell = New-Object -ComObject WScript.Shell
        $Desktop = [Environment]::GetFolderPath("Desktop")
        $Shortcut = $WshShell.CreateShortcut("$Desktop\Sulfur Bot.lnk")
        $Shortcut.TargetPath = "powershell.exe"
        $Shortcut.Arguments = "-ExecutionPolicy Bypass -Command `"cd '$InstallDir'; .\venv\Scripts\Activate.ps1; python bot.py`""
        $Shortcut.WorkingDirectory = $InstallDir
        $Shortcut.Description = "Start Sulfur Discord Bot"
        $Shortcut.Save()
        
        Write-Success "Desktop shortcut created"
    }
    catch {
        Write-Warning "Could not create shortcut: $_"
    }
}

# Print final instructions
function Show-FinalInstructions {
    Write-Host ""
    Write-ColorHost "═══════════════════════════════════════════════════════════════" "Green"
    Write-ColorHost "            ✅ Installation Complete!" "Green"
    Write-ColorHost "═══════════════════════════════════════════════════════════════" "Green"
    Write-Host ""
    Write-Info "📍 Installation directory: $InstallDir"
    Write-Host ""
    Write-Info "🚀 To start the bot:"
    Write-Host "   cd $InstallDir"
    Write-Host "   .\venv\Scripts\Activate.ps1"
    Write-Host "   python bot.py"
    Write-Host ""
    Write-Info "🌐 Web Dashboard: http://localhost:5000"
    Write-Host ""
    Write-Info "📚 Documentation:"
    Write-Host "   - README.md"
    Write-Host "   - docs\WIKI.md"
    Write-Host "   - docs\VPN_GUIDE.md"
    Write-Host ""
    Write-ColorHost "💡 Quick Tips:" "Yellow"
    Write-Host "   - Create a .env file with your Discord token"
    Write-Host "   - Start MySQL before running the bot"
    Write-Host "   - Use /help in Discord to see all commands"
    Write-Host ""
}

# Main installation
function Main {
    # Install Chocolatey if admin
    if ($isAdmin) {
        Install-Chocolatey | Out-Null
    }
    
    # Install core dependencies
    $hasPython = Install-Python
    if (-not $hasPython) {
        Write-Error "Python is required. Please install Python and try again."
        exit 1
    }
    
    Install-Git | Out-Null
    
    # Setup repository
    Setup-Repository
    
    # Setup virtual environment
    Setup-VirtualEnv
    
    # Run full Windows installer if available and in interactive mode
    if ($INTERACTIVE -and (Test-Path "scripts\install_windows.ps1")) {
        $runFull = Read-Host "Run full Windows installer (includes MySQL, Java, etc.)? [y/N]"
        if ($runFull -eq "y" -or $runFull -eq "Y") {
            & .\scripts\install_windows.ps1
        }
    } elseif (-not $INTERACTIVE -and (Test-Path "scripts\install_windows.ps1")) {
        Write-Host "Full Windows installer available (run manually: .\scripts\install_windows.ps1)" -ForegroundColor Cyan
    }

    # Interactive setup
    Run-SetupWizard
    
    # Create shortcut
    Create-Shortcut
    
    # Show final instructions
    Show-FinalInstructions
}

# Run main
Main
