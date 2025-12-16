# --- NEW: Accept LogFile path from maintain_bot.ps1 ---
param(
    [string]$LogFile
)

# --- NEW: Import shared functions ---
. "$PSScriptRoot\shared_functions.ps1"

# Ensure we run all subsequent relative paths from the project root (parent of scripts)
Push-Location (Join-Path $PSScriptRoot '..')

# --- NEW: Load environment variables from .env file ---
if (Test-Path -Path ".env") {
    Get-Content .env | ForEach-Object {
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

# If LogFile is not passed, create a new one (for standalone execution)
$IsStandalone = [string]::IsNullOrEmpty($LogFile)

# --- NEW: Setup Logging ---
# Logging is now handled by the parent maintain_bot.ps1 script via job output redirection.
if ($IsStandalone) {
    $logDir = Join-Path -Path $PSScriptRoot -ChildPath "..\logs"
    if (-not (Test-Path -Path $logDir -PathType Container)) {
        New-Item -ItemType Directory -Path $logDir | Out-Null
    }
    $logTimestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
    $LogFile = Join-Path -Path $logDir -ChildPath "bot_session_${logTimestamp}.log"
}

# --- REFACTORED: Define paths and database connection details at the top ---
$xamppPath = "C:\xampp" # Centralize the XAMPP path for easy configuration
$mysqlBinPath = Join-Path -Path $xamppPath -ChildPath "mysql\bin"
$mysqlStartScript = Join-Path -Path $xamppPath -ChildPath "mysql_start.bat"
$mysqldumpPath = Join-Path -Path $mysqlBinPath -ChildPath "mysqldump.exe"

$syncFile = Join-Path -Path $PSScriptRoot -ChildPath "..\config\database_sync.sql"
$dbName = "sulfur_bot"
$dbUser = "sulfur_bot_user"

# --- FIX: Register an action to export the database on script exit (needs variables defined above) ---
# --- FIX: Use Set-Content with explicit UTF8 encoding to prevent file corruption ---
# --- FIX: Use utf8NoBOM to prevent null characters in the SQL file ---
# --- FIX: Pass variables via MessageData to ensure they're in scope when event fires ---
Register-EngineEvent -SourceIdentifier PowerShell.Exiting -MessageData @{
    mysqldumpPath = $mysqldumpPath
    dbUser = $dbUser
    dbName = $dbName
    syncFile = $syncFile
} -Action {
    $data = $event.MessageData
    & $data.mysqldumpPath --user=$data.dbUser --host=localhost --default-character-set=utf8mb4 $data.dbName | Set-Content -Path $data.syncFile -Encoding utf8
    Write-Host "Database exported to $($data.syncFile) for synchronization."
} | Out-Null

Write-Host "Checking for updates from the repository..."
Write-Host "  -> Discarding local changes to use remote files (public repo mode)..."

# For public repos: Always use remote files via reset
git fetch origin 2>&1 | Out-Null
git reset --hard origin/main 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    git reset --hard origin/master 2>&1 | Out-Null
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Updated to latest version" -ForegroundColor Green
} else {
    Write-Host "Note: Update had issues, but continuing anyway..." -ForegroundColor Yellow
}

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

# --- Setup and use a Python Virtual Environment ---
$pythonExecutable = Invoke-VenvSetup -ScriptRoot $PSScriptRoot

# --- REFACTORED: Check if MySQL is already running ---
$mysqlProcess = Get-Process -Name "mysqld" -ErrorAction SilentlyContinue
if (-not $mysqlProcess) {
    Write-Host "MySQL not running. Starting XAMPP MySQL server..."
    if (Test-Path -Path $mysqlStartScript) {
        Start-Process -FilePath $mysqlStartScript -NoNewWindow
    } else {
        Write-Host "WARNING: MySQL start script not found at $mysqlStartScript" -ForegroundColor Yellow
    }
} else {
    Write-Host "MySQL server is already running."
}
Start-Sleep -Seconds 5 # Give the database a moment to initialize before the bot connects.

Write-Host "Backing up the database..."
$backupDir = Join-Path -Path (Get-Location) -ChildPath "backups"

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
# UTF-8 output settings to avoid mojibake (ä, ö, ü etc.)
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

try {
    # Use Start-Process for cleaner exit code capture and proper redirection
    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $pythonExecutable
    $startInfo.Arguments = '-u -X utf8 bot.py'
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError  = $true
    $startInfo.UseShellExecute = $false
    $startInfo.WorkingDirectory = (Get-Location).Path
    $process = [System.Diagnostics.Process]::Start($startInfo)
    $stdOut = $process.StandardOutput
    $stdErr = $process.StandardError
    # Stream output to log file in real time
    while (-not $process.HasExited) {
        while (-not $stdOut.EndOfStream) { $line = $stdOut.ReadLine(); if ($line) { Add-Content -Path $LogFile -Value $line -Encoding utf8 } }
        while (-not $stdErr.EndOfStream) { $line = $stdErr.ReadLine(); if ($line) { Add-Content -Path $LogFile -Value $line -Encoding utf8 } }
        Start-Sleep -Milliseconds 200
    }
    # Flush remaining lines
    while (-not $stdOut.EndOfStream) { $line = $stdOut.ReadLine(); if ($line) { Add-Content -Path $LogFile -Value $line -Encoding utf8 } }
    while (-not $stdErr.EndOfStream) { $line = $stdErr.ReadLine(); if ($line) { Add-Content -Path $LogFile -Value $line -Encoding utf8 } }
    $pythonExitCode = $process.ExitCode
} catch {
    Write-Host "Error starting bot: $_" -ForegroundColor Red
    Write-Host $_.Exception.Message
    $pythonExitCode = 1
} finally {
    # Dispose process object to prevent resource leaks
    if($process) {
        try {
            $process.Close()
            $process.Dispose()
        } catch {}
    }
}

# --- NEW: Pause on error to allow copying logs ---
# --- FIX: Use $pipelinestatus to get the correct exit code from the python process, not Tee-Object ---
# --- REFACTORED: Use the ExitCode property from the process object for clarity ---
if ($pythonExitCode -ne 0) {
    Write-Host "--------------------------------------------------------" -ForegroundColor Red
    Write-Host "The bot process exited with an error (Exit Code: $pythonExitCode)." -ForegroundColor Red
    Write-Host "Check the log file for details: $LogFile" -ForegroundColor Yellow
    if ($IsStandalone) { Write-Host "The script is paused. Press Enter to close this window." -ForegroundColor Yellow; Read-Host }
}

Pop-Location