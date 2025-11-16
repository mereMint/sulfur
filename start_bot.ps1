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
        # Match lines with KEY=VALUE format
        if ($_ -match "^\s*([\w.-]+)\s*=\s*(.*)") {
            $key = $matches[1]
            # --- FIX: Trim whitespace and remove surrounding quotes from the value ---
            $value = $matches[2].Trim()
            if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
                $value = $value.Substring(1, $value.Length - 2)
            }
            [System.Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
}

# --- NEW: Setup Logging ---
# --- REFACTORED: Use relative paths for portability ---
$logDir = Join-Path -Path $PSScriptRoot -ChildPath "logs"
if (-not (Test-Path -Path $logDir -PathType Container)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
    Write-Host "Created logs directory at $logDir"
}

$logTimestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$logFile = Join-Path -Path $logDir -ChildPath "bot_session_${logTimestamp}.log"

Write-Host "Logging this session to: $logFile"

# --- REFACTORED: Define paths and database connection details at the top ---
$xamppPath = "C:\xampp" # Centralize the XAMPP path for easy configuration
$mysqlBinPath = Join-Path -Path $xamppPath -ChildPath "mysql\bin"
$mysqlStartScript = Join-Path -Path $xamppPath -ChildPath "mysql_start.bat"
$mysqldumpPath = Join-Path -Path $mysqlBinPath -ChildPath "mysqldump.exe"

$syncFile = Join-Path -Path $PSScriptRoot -ChildPath "database_sync.sql"
$dbName = "sulfur_bot"
$dbUser = "sulfur_bot_user"

# --- FIX: Register an action to export the database on script exit (needs variables defined above) ---
# --- FIX: Use Set-Content with explicit UTF8 encoding to prevent file corruption ---
# --- FIX: Use utf8NoBOM to prevent null characters in the SQL file ---
Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action {
    & $mysqldumpPath --user=$dbUser --host=localhost --default-character-set=utf8mb4 $dbName | Set-Content -Path $syncFile -Encoding utf8
    Write-Host "Database exported to $syncFile for synchronization."
} | Out-Null

Write-Host "Checking for updates from the repository..."
Write-Host "  -> Stashing local changes to avoid conflicts..."
git stash | Out-Null

# --- FIX: Check for errors during git pull ---
Write-Host "  -> Pulling latest version from the repository..."
git pull
if ($LASTEXITCODE -ne 0) {
    Write-Host "--------------------------------------------------------" -ForegroundColor Red
    Write-Host "Error: 'git pull' failed. The script cannot continue." -ForegroundColor Red
    Write-Host "Please check your internet connection and git status, then try again." -ForegroundColor Yellow
    Read-Host "Press Enter to exit."
    exit 1
}

Write-Host "  -> Re-applying stashed local changes..."
git stash pop | Out-Null
Write-Host "Update check complete."

# --- NEW: Check if the sync file was updated and import it ---
# --- DISABLED: The automatic database import is disabled to prevent accidental data loss. ---
# The database_sync.sql file will still be pulled, but must be imported manually if needed.
# if (($oldHead -ne $newHead) -and (git diff --name-only $oldHead $newHead | Select-String -Pattern $syncFile)) {
#     Write-Host "Database sync file has been updated. Importing new data..."
#     Get-Content $syncFile | & $mysqlPath --user=$dbUser --host=localhost --default-character-set=utf8mb4 $dbName
#     Write-Host "Database import complete."
# }

# --- NEW: Check for Python executable before proceeding ---
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "--------------------------------------------------------" -ForegroundColor Red
    Write-Host "Error: 'python' command not found." -ForegroundColor Red
    Write-Host "Please ensure Python is installed and its location is in your system's PATH environment variable." -ForegroundColor Yellow
    Read-Host "Press Enter to exit."
    exit 1
}

# --- NEW: Function to ensure Python Virtual Environment is set up ---
function Ensure-Venv {
    param(
        [string]$ScriptRoot
    )
    $venvPath = Join-Path -Path $ScriptRoot -ChildPath "venv"
    $pythonExecutable = Join-Path -Path $venvPath -ChildPath "Scripts\python.exe"

    if (-not (Test-Path -Path $pythonExecutable)) {
        Write-Host "Python virtual environment not found. Creating one now..." -ForegroundColor Yellow
        python -m venv $venvPath
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Failed to create the Python virtual environment. Please check your Python installation." -ForegroundColor Red
            Read-Host "Press Enter to exit."
            exit 1
        }
    }

    Write-Host "Installing/updating Python dependencies from requirements.txt..."
    & $pythonExecutable -m pip install -r requirements.txt
    Write-Host "Dependencies are up to date."

    return $pythonExecutable
}

# --- Setup and use a Python Virtual Environment ---
$pythonExecutable = Ensure-Venv -ScriptRoot $PSScriptRoot

# --- REFACTORED: Check if MySQL is already running ---
$mysqlProcess = Get-Process -Name "mysqld" -ErrorAction SilentlyContinue
if (-not $mysqlProcess) {
    Write-Host "MySQL not running. Starting XAMPP MySQL server..."
    Start-Process -FilePath $mysqlStartScript
} else {
    Write-Host "MySQL server is already running."
}
Start-Sleep -Seconds 5 # Give the database a moment to initialize before the bot connects.

Write-Host "Backing up the database..."
$backupDir = Join-Path -Path $PSScriptRoot -ChildPath "backups"

# Create backup directory if it doesn't exist
if (-not (Test-Path -Path $backupDir -PathType Container)) {
    New-Item -ItemType Directory -Path $backupDir | Out-Null
}

$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$backupFile = Join-Path -Path $backupDir -ChildPath "${dbName}_backup_${timestamp}.sql"
# --- FIX: Use Set-Content with explicit UTF8 encoding to prevent file corruption ---
& $mysqldumpPath --user=$dbUser --host=localhost --default-character-set=utf8mb4 $dbName | Set-Content -Path $backupFile -Encoding utf8
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
& $pythonExecutable -u -X utf8 bot.py *>&1 | Tee-Object -FilePath $logFile -Append

# --- NEW: Pause on error to allow copying logs ---
# --- FIX: Use $pipelinestatus to get the correct exit code from the python process, not Tee-Object ---
# $LASTEXITCODE is automatically populated with the exit code of the last native command (python.exe).
# A non-zero exit code indicates an error.
$pythonExitCode = $LASTEXITCODE

# A non-zero exit code indicates an error.
if ($pythonExitCode -ne 0) {
    Write-Host "--------------------------------------------------------" -ForegroundColor Red
    Write-Host "The bot process exited with an error (Exit Code: $pythonExitCode)." -ForegroundColor Red
    Write-Host "The script is paused. Press Enter to close this window." -ForegroundColor Yellow
    Read-Host
}