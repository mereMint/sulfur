# This script sets the necessary environment variables and starts the Sulfur bot.
# To run it:
# 1. Open PowerShell
# 2. Navigate to this directory (cd c:\sulfur)
# 3. Run the script with: .\start_bot.ps1

# --- FIX: Set the working directory to the script's location ---
# This ensures that relative paths for files like .env and bot.py work correctly.
Set-Location -Path $PSScriptRoot

# --- NEW: Load environment variables from .env file ---
if (Test-Path -Path ".env") {
    Get-Content .\.env | ForEach-Object {
        if ($_ -match "^\s*([\w.-]+)\s*=\s*(.*)") {
            [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
        }
    }
}

# --- NEW: Setup Logging ---
$logDir = "C:\sulfur\logs"
if (-not (Test-Path -Path $logDir -PathType Container)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
    Write-Host "Created logs directory at $logDir"
}

$logTimestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$logFile = Join-Path -Path $logDir -ChildPath "startup_log_${logTimestamp}.txt"

Write-Host "Logging this session to: $logFile"

# --- REFACTORED: Define sync file and database connection details at the top ---
$syncFile = "C:\sulfur\database_sync.sql"
$mysqldumpPath = "C:\xampp\mysql\bin\mysqldump.exe"
$mysqlPath = "C:\xampp\mysql\bin\mysql.exe"
$dbName = "sulfur_bot"
$dbUser = "sulfur_bot_user"

# --- FIX: Register an action to export the database on script exit (needs variables defined above) ---
Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action { & $mysqldumpPath --user=$dbUser --host=localhost --default-character-set=utf8mb4 $dbName > $syncFile; Write-Host "Database exported to $syncFile for synchronization." } | Out-Null

Write-Host "Checking for updates from the repository..."
Write-Host "  -> Stashing local changes to avoid conflicts..."
git stash | Out-Null
# --- NEW: Get the commit hash before pulling ---
$oldHead = git rev-parse HEAD
Write-Host "  -> Pulling latest version from the repository..."
git pull | Out-Null
# --- NEW: Get the commit hash after pulling ---
$newHead = git rev-parse HEAD
Write-Host "  -> Re-applying stashed local changes..."
git stash pop | Out-Null
Write-Host "Update check complete."

# --- NEW: Install/update Python dependencies ---
Write-Host "Installing/updating Python dependencies from requirements.txt..."
# Using python -m pip is more robust than just 'pip'
python -m pip install -r requirements.txt
Write-Host "Dependencies are up to date."

# --- NEW: Check if the sync file was updated and import it ---
if (($oldHead -ne $newHead) -and (git diff --name-only $oldHead $newHead | Select-String -Pattern $syncFile)) {
    Write-Host "Database sync file has been updated. Importing new data..."
    Get-Content $syncFile | & $mysqlPath --user=$dbUser --host=localhost --default-character-set=utf8mb4 $dbName
    Write-Host "Database import complete."
}

# --- REFACTORED: Check if MySQL is already running ---
$mysqlProcess = Get-Process -Name "mysqld" -ErrorAction SilentlyContinue
if (-not $mysqlProcess) {
    Write-Host "MySQL not running. Starting XAMPP MySQL server..."
    Start-Process -FilePath "C:\xampp\mysql_start.bat"
} else {
    Write-Host "MySQL server is already running."
}
Start-Sleep -Seconds 5 # Give the database a moment to initialize before the bot connects.

Write-Host "Backing up the database..."
$backupDir = "C:\sulfur\backups"

# Create backup directory if it doesn't exist
if (-not (Test-Path -Path $backupDir -PathType Container)) {
    New-Item -ItemType Directory -Path $backupDir | Out-Null
}

$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$backupFile = Join-Path -Path $backupDir -ChildPath "${dbName}_backup_${timestamp}.sql"
& $mysqldumpPath --user=$dbUser --host=localhost --default-character-set=utf8mb4 $dbName > $backupFile
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
# --- FIX: Use Start-Process for more reliable execution in the same window ---
# The -u flag forces python's output to be unbuffered, ensuring logs appear immediately.

# --- REFACTORED: Call python directly and use Tee-Object to capture all output to the log file ---
# This is the PowerShell equivalent of `2>&1 | tee -a` in bash.
python -u bot.py *>&1 | Tee-Object -FilePath $logFile -Append

# --- NEW: Pause on error to allow copying logs ---
# --- FIX: Use $pipelinestatus to get the correct exit code from the python process, not Tee-Object ---
$pythonExitCode = 1 # Default to 1 (error) if the pipeline fails to populate the variable
if ($pipelinestatus -and $pipelinestatus.Count -gt 0) {
    $pythonExitCode = $pipelinestatus[0]
}

# A non-zero exit code indicates an error.
if ($LASTEXITCODE -ne 0 -or ($pythonExitCode -ne 0 -and $null -ne $pythonExitCode)) {
    Write-Host "--------------------------------------------------------" -ForegroundColor Red
    Write-Host "The bot process exited with an error (Exit Code: $pythonExitCode)." -ForegroundColor Red
    Write-Host "The script is paused. Press Enter to close this window." -ForegroundColor Yellow
    Read-Host
}