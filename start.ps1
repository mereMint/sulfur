# Simple Windows Starter for Sulfur Bot
# Usage: Right-click > Run with PowerShell, or execute in terminal

param(
    [switch]$NoBackup
)

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

Write-Host "Starting Sulfur maintenance (Windows)..." -ForegroundColor Cyan

$argsList = @()
if ($NoBackup) { $argsList += "-SkipDatabaseBackup" }

# Run the enhanced maintenance script which also starts the Web Dashboard
& powershell.exe -ExecutionPolicy Bypass -File "$scriptPath\maintain_bot.ps1" @argsList