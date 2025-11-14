# This script sets the necessary environment variables and starts the Sulfur bot.
# To run it:
# 1. Open PowerShell
# 2. Navigate to this directory (cd c:\sulfur)
# 3. Run the script with: .\start_bot.ps1

# --- NEW: Setup Logging ---
$logDir = "C:\sulfur\logs"
if (-not (Test-Path -Path $logDir -PathType Container)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
    Write-Host "Created logs directory at $logDir"
}

$logTimestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$logFile = Join-Path -Path $logDir -ChildPath "startup_log_${logTimestamp}.txt"

Write-Host "Logging this session to: $logFile"
Start-Transcript -Path $logFile

Write-Host "Setting environment variables for the bot..."
$env:DISCORD_BOT_TOKEN="MTQzODU5NTUzNjE1MTM4MDAxOA.GwuLkF.NYHg6QXtQfhGIPK6SRA8TxDo4-wOtJrTzn00EU"
$env:GEMINI_API_KEY="AIzaSyD7h08ULN7KXhYCFFiIa6MPEbN_TnL5COU"
$env:OPENAI_API_KEY="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" # <-- ADD YOUR OPENAI KEY HERE

Write-Host "Checking for updates from the repository..."
Write-Host "  -> Stashing local changes to avoid conflicts..."
git stash
Write-Host "  -> Pulling latest version from the repository..."
git pull
Write-Host "  -> Re-applying stashed local changes..."
git stash pop
Write-Host "Update check complete."

Write-Host "Starting XAMPP MySQL server..."
# The default path for XAMPP is C:\xampp. If yours is different, please update the path below.
# Use Start-Process to run MySQL in the background without blocking the script.
Start-Process -FilePath "C:\xampp\mysql_start.bat"
Start-Sleep -Seconds 5 # Give the database a moment to initialize before the bot connects.

Write-Host "Backing up the database..."
$backupDir = "C:\sulfur\backups"
$mysqldumpPath = "C:\xampp\mysql\bin\mysqldump.exe"
$dbName = "sulfur_bot"
$dbUser = "sulfur_bot_user"

# Create backup directory if it doesn't exist
if (-not (Test-Path -Path $backupDir -PathType Container)) {
    New-Item -ItemType Directory -Path $backupDir | Out-Null
}

$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$backupFile = Join-Path -Path $backupDir -ChildPath "${dbName}_backup_${timestamp}.sql"
& $mysqldumpPath --user=$dbUser --host=localhost $dbName > $backupFile
Write-Host "Backup created successfully at $backupFile"

# --- NEW: Clean up old backups ---
Write-Host "Cleaning up old backups (older than 7 days)..."
$cleanupDate = (Get-Date).AddDays(-7)
Get-ChildItem -Path $backupDir -Filter "*.sql" | Where-Object { $_.LastWriteTime -lt $cleanupDate } | ForEach-Object {
    Write-Host "  - Deleting old backup: $($_.Name)"
    Remove-Item -Path $_.FullName -Force
}
Write-Host "Cleanup complete."

Write-Host "Starting the bot... (Press CTRL+C to stop)"
python ./bot.py