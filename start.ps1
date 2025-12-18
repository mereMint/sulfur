# Simple Windows Starter for Sulfur Bot
# Usage: Right-click > Run with PowerShell, or execute in terminal

param(
    [switch]$NoBackup
)

$ErrorActionPreference = 'Stop'
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "             Sulfur Discord Bot - Starter                  " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Check if MySQL/MariaDB is running
Write-Host "Checking MySQL/MariaDB status..." -ForegroundColor Yellow
$mysqlProcess = Get-Process mysqld,mariadbd -ErrorAction SilentlyContinue | Select-Object -First 1

if ($mysqlProcess) {
    Write-Host "+ OK MySQL/MariaDB is running (PID: $($mysqlProcess.Id))" -ForegroundColor Green
} else {
    Write-Host "- ERR MySQL/MariaDB is not running" -ForegroundColor Red
    Write-Host "" 
    Write-Host "Attempting to start MySQL/MariaDB..." -ForegroundColor Yellow
    
    # Try XAMPP first
    $xamppMysqlStart = "C:\xampp\mysql_start.bat"
    if (Test-Path $xamppMysqlStart) {
        Write-Host "  Found XAMPP, starting MySQL..." -ForegroundColor Cyan
        try {
            Start-Process -FilePath $xamppMysqlStart -WindowStyle Hidden -Wait
            Start-Sleep -Seconds 3
            $mysqlProcess = Get-Process mysqld,mariadbd -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($mysqlProcess) {
                Write-Host "+ OK MySQL started successfully" -ForegroundColor Green
            } else {
                Write-Host "! WARN MySQL may not have started. Please check XAMPP Control Panel." -ForegroundColor Yellow
            }
        } catch {
            Write-Host "! WARN Could not start MySQL via XAMPP: $_" -ForegroundColor Yellow
        }
    } else {
        # Try Windows Service
        try {
            $mysqlService = Get-Service -Name "MySQL*","MariaDB*" -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($mysqlService) {
                Write-Host "  Starting $($mysqlService.Name) service..." -ForegroundColor Cyan
                Start-Service -Name $mysqlService.Name -ErrorAction Stop
                Start-Sleep -Seconds 3
                Write-Host "+ OK MySQL service started" -ForegroundColor Green
            } else {
                Write-Host "! WARN Could not find MySQL/MariaDB service" -ForegroundColor Yellow
                Write-Host "  Please start MySQL manually and run this script again." -ForegroundColor Gray
                Write-Host ""
                Write-Host "To install MySQL/MariaDB:" -ForegroundColor Cyan
                Write-Host "  1. Download XAMPP from https://www.apachefriends.org/" -ForegroundColor Gray
                Write-Host "  2. Or install MySQL from https://dev.mysql.com/downloads/installer/" -ForegroundColor Gray
                Write-Host ""
                Read-Host "Press Enter to continue anyway or Ctrl+C to exit"
            }
        } catch {
            Write-Host "! WARN Could not start MySQL service: $_" -ForegroundColor Yellow
            Write-Host "  Please start MySQL manually." -ForegroundColor Gray
            Read-Host "Press Enter to continue anyway or Ctrl+C to exit"
        }
    }
}
Write-Host ""

# ============================================================================
# Auto-install/Check Java
# ============================================================================
Write-Host "Checking Java installation..." -ForegroundColor Yellow
try {
    $javaVersion = & java -version 2>&1 | Out-String
    if ($LASTEXITCODE -eq 0 -and $javaVersion) {
        Write-Host "[OK] Java found: $($javaVersion.Split([Environment]::NewLine)[0])" -ForegroundColor Green
    } else {
        throw "Java not found"
    }
} catch {
    Write-Host "[!] Java not found" -ForegroundColor Yellow
    Write-Host "  Java is required for Minecraft server features" -ForegroundColor Gray
    Write-Host "  Download from: https://adoptium.net/temurin/releases/?version=21" -ForegroundColor Gray
    Write-Host "  Or use winget: winget install EclipseAdoptium.Temurin.21.JDK" -ForegroundColor Gray
}
Write-Host ""

# ============================================================================
# Auto-install/Check FFmpeg
# ============================================================================
Write-Host "Checking FFmpeg installation..." -ForegroundColor Yellow
try {
    $ffmpegVersion = & ffmpeg -version 2>&1 | Select-Object -First 1
    if ($LASTEXITCODE -eq 0 -and $ffmpegVersion) {
        Write-Host "[OK] FFmpeg found: $ffmpegVersion" -ForegroundColor Green
    } else {
        throw "FFmpeg not found"
    }
} catch {
    Write-Host "[!] FFmpeg not found" -ForegroundColor Yellow
    Write-Host "  FFmpeg is required for music/audio features" -ForegroundColor Gray
    Write-Host "  Download from: https://ffmpeg.org/download.html" -ForegroundColor Gray
    Write-Host "  Or use winget: winget install FFmpeg.FFmpeg" -ForegroundColor Gray
}
Write-Host ""

# Check if virtual environment exists and activate it
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    try {
        & "venv\Scripts\Activate.ps1"
        Write-Host "[OK] Virtual environment activated" -ForegroundColor Green
    } catch {
        Write-Host "[!] Could not activate virtual environment: $_" -ForegroundColor Yellow
        Write-Host "  Continuing anyway..." -ForegroundColor Gray
    }
    Write-Host ""
} elseif (-not (Test-Path "venv")) {
    Write-Host "Virtual environment not found. Creating one..." -ForegroundColor Yellow
    Write-Host "This may take a few minutes..." -ForegroundColor Gray
    Write-Host ""
    
    try {
        python -m venv venv
        Write-Host "[OK] Virtual environment created" -ForegroundColor Green
        
        & "venv\Scripts\Activate.ps1"
        Write-Host "[OK] Virtual environment activated" -ForegroundColor Green
        
        Write-Host ""
        Write-Host "Installing dependencies..." -ForegroundColor Yellow
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        Write-Host "[OK] Dependencies installed" -ForegroundColor Green
        Write-Host ""
    } catch {
        Write-Host "[X] Failed to set up virtual environment: $_" -ForegroundColor Red
        Write-Host "Continuing without virtual environment..." -ForegroundColor Yellow
        Write-Host ""
    }
}

$argsList = @()
if ($NoBackup) { $argsList += "-SkipDatabaseBackup" }

Write-Host "Starting maintenance script..." -ForegroundColor Cyan
Write-Host ""

# Run the enhanced maintenance script which also starts the Web Dashboard
$maintainScript = Join-Path $scriptPath "maintain_bot.ps1"
& powershell.exe -ExecutionPolicy Bypass -File $maintainScript @argsList