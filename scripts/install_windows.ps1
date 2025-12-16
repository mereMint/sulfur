# ==============================================================================
# Sulfur Bot - Windows Installation Script
# ==============================================================================
# This script installs all dependencies for Sulfur Bot on Windows
# including optional WireGuard VPN and Minecraft server support.
# Run this script as Administrator in PowerShell.
# ==============================================================================

param(
    [switch]$SkipJava,
    [switch]$SkipWireGuard,
    [switch]$SkipMySQL,
    [switch]$Force
)

# Detect if running in non-interactive mode (piped input)
$INTERACTIVE = -not ([Console]::IsInputRedirected)

if (-not $INTERACTIVE) {
    Write-Host "Note: Running in non-interactive mode (piped from PowerShell)" -ForegroundColor Yellow
}

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

# Header
Write-Host ""
Write-ColorHost "╔══════════════════════════════════════════════════════════════════╗" "Cyan"
Write-ColorHost "║              SULFUR BOT - WINDOWS INSTALLER                       ║" "Cyan"
Write-ColorHost "╚══════════════════════════════════════════════════════════════════╝" "Cyan"
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Warning "This script works best when run as Administrator."
    Write-Info "Some installations may require manual steps without admin rights."
    if ($INTERACTIVE) {
        $continue = Read-Host "Continue anyway? [Y/n]"
        if ($continue -eq "n" -or $continue -eq "N") {
            exit 0
        }
    } else {
        Write-Host "Continuing in non-interactive mode" -ForegroundColor Yellow
    }
}

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

# Check Python
function Install-Python {
    Write-Host ""
    Write-ColorHost "🐍 Checking Python installation..." "Blue"
    
    $python = Get-Command python -ErrorAction SilentlyContinue
    
    if ($python) {
        $version = & python --version 2>&1
        Write-Success "Python found: $version"
        
        # Check version
        $versionNum = $version -replace "Python ", ""
        $major, $minor = $versionNum.Split('.')[0..1]
        
        if ([int]$major -lt 3 -or ([int]$major -eq 3 -and [int]$minor -lt 8)) {
            Write-Warning "Python 3.8+ is required. Current: $versionNum"
            return $false
        }
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

# Check Git
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

# Check MySQL
function Install-MySQL {
    if ($SkipMySQL) {
        Write-Info "Skipping MySQL installation"
        return $true
    }
    
    Write-Host ""
    Write-ColorHost "🗄️  Checking MySQL installation..." "Blue"
    
    $mysql = Get-Command mysql -ErrorAction SilentlyContinue
    
    if ($mysql) {
        Write-Success "MySQL found"
        return $true
    }
    
    # Check for MySQL service
    $service = Get-Service -Name "MySQL*" -ErrorAction SilentlyContinue
    if ($service) {
        Write-Success "MySQL service found: $($service.Name)"
        return $true
    }
    
    Write-Step "MySQL not found"
    
    if (-not $INTERACTIVE) {
        Write-Host "Skipping MySQL installation (non-interactive mode)" -ForegroundColor Yellow
        return $false
    }
    
    $install = Read-Host "Install MySQL? [Y/n]"
    if ($install -eq "n" -or $install -eq "N") {
        Write-Info "Skipping MySQL. You can install it later."
        return $false
    }
    
    if (Get-Command choco -ErrorAction SilentlyContinue) {
        Write-Step "Installing MySQL via Chocolatey..."
        choco install mysql -y
        
        # Refresh environment
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    }
    else {
        Write-Info "Please download MySQL from https://dev.mysql.com/downloads/installer/"
        Start-Process "https://dev.mysql.com/downloads/installer/"
        if ($INTERACTIVE) {
            Read-Host "Press Enter after installing MySQL..."
        }
    }
    
    return (Get-Command mysql -ErrorAction SilentlyContinue) -ne $null
}

# Check Java
function Install-Java {
    if ($SkipJava) {
        Write-Info "Skipping Java installation"
        return $true
    }
    
    Write-Host ""
    Write-ColorHost "☕ Checking Java installation..." "Blue"
    
    $java = Get-Command java -ErrorAction SilentlyContinue
    
    if ($java) {
        $version = & java -version 2>&1 | Select-Object -First 1
        Write-Success "Java found: $version"
        
        # Extract major version
        if ($version -match 'version "(\d+)') {
            $major = [int]$Matches[1]
            if ($major -lt 17) {
                Write-Warning "Java $major found but Java 17+ recommended for Minecraft"
            }
            else {
                return $true
            }
        }
    }
    
    if (-not $INTERACTIVE) {
        Write-Host "Skipping Java installation (non-interactive mode)" -ForegroundColor Yellow
        return $false
    }
    
    $install = Read-Host "Install Java 21 for Minecraft server? [Y/n]"
    if ($install -eq "n" -or $install -eq "N") {
        return $false
    }
    
    if (Get-Command choco -ErrorAction SilentlyContinue) {
        Write-Step "Installing Temurin JDK 21 via Chocolatey..."
        choco install temurin21 -y
        
        # Refresh environment
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
        
        Write-Success "Java 21 installed"
    }
    else {
        Write-Info "Please download Java 21 from https://adoptium.net/"
        Start-Process "https://adoptium.net/"
        if ($INTERACTIVE) {
            Read-Host "Press Enter after installing Java..."
        }
    }
    
    return (Get-Command java -ErrorAction SilentlyContinue) -ne $null
}

# Check WireGuard
function Install-WireGuard {
    if ($SkipWireGuard) {
        Write-Info "Skipping WireGuard installation"
        return $true
    }
    
    Write-Host ""
    Write-ColorHost "🔐 Checking WireGuard installation..." "Blue"
    
    $wg = Get-Command wg -ErrorAction SilentlyContinue
    $wgExe = Test-Path "C:\Program Files\WireGuard\wg.exe"
    
    if ($wg -or $wgExe) {
        Write-Success "WireGuard found"
        return $true
    }
    
    if (-not $INTERACTIVE) {
        Write-Host "Skipping WireGuard installation (non-interactive mode)" -ForegroundColor Yellow
        return $false
    }
    
    $install = Read-Host "Install WireGuard VPN? [y/N]"
    if ($install -ne "y" -and $install -ne "Y") {
        return $false
    }
    
    if (Get-Command choco -ErrorAction SilentlyContinue) {
        Write-Step "Installing WireGuard via Chocolatey..."
        choco install wireguard -y
        Write-Success "WireGuard installed"
    }
    else {
        Write-Info "Please download WireGuard from https://www.wireguard.com/install/"
        Start-Process "https://www.wireguard.com/install/"
        if ($INTERACTIVE) {
            Read-Host "Press Enter after installing WireGuard..."
        }
    }
    
    return $true
}

# Install FFmpeg
function Install-FFmpeg {
    Write-Host ""
    Write-ColorHost "🎬 Checking FFmpeg installation..." "Blue"
    
    if (Get-Command ffmpeg -ErrorAction SilentlyContinue) {
        Write-Success "FFmpeg found"
        return $true
    }
    
    Write-Step "Installing FFmpeg..."
    
    if (Get-Command choco -ErrorAction SilentlyContinue) {
        choco install ffmpeg -y
        
        # Refresh environment
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
        
        Write-Success "FFmpeg installed"
    }
    else {
        Write-Warning "FFmpeg not found. Voice features may not work."
        Write-Info "Install manually from https://ffmpeg.org/download.html"
    }
    
    return $true
}

# Setup Python virtual environment
function Setup-VirtualEnv {
    Write-Host ""
    Write-ColorHost "🐍 Setting up Python virtual environment..." "Blue"
    
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

# Run setup wizard
function Run-SetupWizard {
    Write-Host ""
    Write-ColorHost "🧙 Running setup wizard..." "Blue"
    
    & .\venv\Scripts\Activate.ps1
    & python master_setup.py
}

# Create shortcut
function Create-Shortcut {
    if (-not $INTERACTIVE) {
        Write-Host "Skipping desktop shortcut creation (non-interactive mode)" -ForegroundColor Yellow
        return
    }
    
    $createShortcut = Read-Host "Create desktop shortcut? [Y/n]"
    if ($createShortcut -eq "n" -or $createShortcut -eq "N") {
        return
    }
    
    $WshShell = New-Object -ComObject WScript.Shell
    $Desktop = [Environment]::GetFolderPath("Desktop")
    $Shortcut = $WshShell.CreateShortcut("$Desktop\Sulfur Bot.lnk")
    $Shortcut.TargetPath = "powershell.exe"
    $Shortcut.Arguments = "-ExecutionPolicy Bypass -File `"$PWD\scripts\start_bot.ps1`""
    $Shortcut.WorkingDirectory = $PWD
    $Shortcut.Description = "Start Sulfur Discord Bot"
    $Shortcut.Save()
    
    Write-Success "Desktop shortcut created"
}

# Main installation
function Main {
    # Install Chocolatey first for easier package management
    $hasChoco = Install-Chocolatey
    
    # Install core dependencies
    $hasPython = Install-Python
    if (-not $hasPython) {
        Write-Error "Python is required. Please install Python and try again."
        exit 1
    }
    
    Install-Git
    Install-MySQL
    Install-Java
    Install-WireGuard
    Install-FFmpeg
    
    # Setup virtual environment
    Setup-VirtualEnv
    
    Write-Host ""
    Write-ColorHost "════════════════════════════════════════════════════════════════" "Green"
    Write-ColorHost "✅ Installation complete!" "Green"
    Write-ColorHost "════════════════════════════════════════════════════════════════" "Green"
    
    # Run setup wizard
    if ($INTERACTIVE) {
        $runWizard = Read-Host "Run the setup wizard now? [Y/n]"
        if ($runWizard -ne "n" -and $runWizard -ne "N") {
            Run-SetupWizard
        }
    } else {
        Write-Host "Setup wizard available: python master_setup.py" -ForegroundColor Cyan
    }
    
    Create-Shortcut
    
    Write-Host ""
    Write-ColorHost "Next steps:" "Cyan"
    Write-Host "  1. Activate the virtual environment: .\venv\Scripts\Activate.ps1"
    Write-Host "  2. Run the setup wizard: python master_setup.py"
    Write-Host "  3. Start the bot: python bot.py"
    Write-Host "  4. Access the dashboard: http://localhost:5000"
}

# Run main
Main
