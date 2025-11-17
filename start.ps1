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