# ==============================================================================
# Sulfur Bot - Enhanced Maintenance Script for Windows
# ==============================================================================
# Features:
# - Auto-start bot and web dashboard
# - Check for updates every minute
# - Auto-commit database changes every 5 minutes
# - Auto-backup database every 30 minutes
# - Auto-restart on updates
# - Self-update capability
# - Graceful shutdown with 'Q' key
# ==============================================================================

param(
    [switch]$SkipDatabaseBackup = $false
)

# Initialize
$ErrorActionPreference = "Stop"
$statusFile = Join-Path -Path $PSScriptRoot -ChildPath "config\bot_status.json"
$script:webDashboardJob = $null
$script:botProcess = $null

# Logging setup
$logDir = Join-Path -Path $PSScriptRoot -ChildPath "logs"
if (-not (Test-Path -Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}
$logTimestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$logFile = Join-Path -Path $logDir -ChildPath "maintenance_${logTimestamp}.log"
$botLogFile = Join-Path -Path $logDir -ChildPath "bot_${logTimestamp}.log"

Start-Transcript -Path $logFile -Append

# Trap for graceful shutdown
trap {
    Write-Host "Script terminated. Cleaning up..." -ForegroundColor Red
    if ($script:botProcess) { Stop-Process -Id $script:botProcess.Id -Force -ErrorAction SilentlyContinue }
    if ($script:webDashboardJob) { 
        Stop-Job -Job $script:webDashboardJob -ErrorAction SilentlyContinue
        Remove-Job -Job $script:webDashboardJob -Force -ErrorAction SilentlyContinue
    }
    Update-BotStatus "Shutdown"
    Stop-Transcript
    exit 0
}

# Functions
function Write-ColorLog {
    param(
        [string]$Message,
        [string]$Color = "White",
        [string]$Prefix = ""
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $fullMessage = "[$timestamp] $Prefix$Message"
    Write-Host $fullMessage -ForegroundColor $Color
}

function Update-BotStatus {
    param([string]$Status, [int]$Pid = 0)
    
    $statusData = @{
        status = $Status
        timestamp = (Get-Date).ToUniversalTime().ToString("o")
    }
    
    if ($Pid -gt 0) {
        $statusData.pid = $Pid
    }
    
    [System.IO.File]::WriteAllText(
        $statusFile,
        ($statusData | ConvertTo-Json -Compress),
        ([System.Text.UTF8Encoding]::new($false))
    )
}

function Invoke-DatabaseBackup {
    Write-ColorLog "Creating database backup..." "Cyan" "[DB] "
    
    try {
        # Check if MySQL is accessible
        $mysqlCmd = "mysqldump"
        $dbUser = $env:DB_USER
        if (-not $dbUser) { $dbUser = "sulfur_bot_user" }
        
        $dbName = $env:DB_NAME
        if (-not $dbName) { $dbName = "sulfur_bot" }
        
        $backupDir = Join-Path -Path $PSScriptRoot -ChildPath "backups"
        if (-not (Test-Path -Path $backupDir)) {
            New-Item -ItemType Directory -Path $backupDir | Out-Null
        }
        
        $backupFile = Join-Path -Path $backupDir -ChildPath "sulfur_bot_backup_$(Get-Date -Format 'yyyy-MM-dd_HH-mm-ss').sql"
        
        # Create backup
        & $mysqlCmd -u $dbUser $dbName > $backupFile 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-ColorLog "Database backup created: $backupFile" "Green" "[DB] "
            
            # Keep only last 10 backups
            $backups = Get-ChildItem -Path $backupDir -Filter "*.sql" | Sort-Object -Property LastWriteTime -Descending
            if ($backups.Count -gt 10) {
                $backups | Select-Object -Skip 10 | Remove-Item -Force
                Write-ColorLog "Cleaned up old backups (kept last 10)" "Yellow" "[DB] "
            }
            
            return $true
        } else {
            Write-ColorLog "Database backup failed" "Red" "[DB] "
            return $false
        }
    } catch {
        Write-ColorLog "Database backup error: $_" "Red" "[DB] "
        return $false
    }
}

function Invoke-GitCommit {
    param([string]$Message = "chore: Auto-commit from maintenance script")
    
    Write-ColorLog "Checking for changes to commit..." "Cyan" "[GIT] "
    
    # Check for database sync file
    $dbSyncFile = "config\database_sync.sql"
    $hasChanges = $false
    
    if (Test-Path $dbSyncFile) {
        $gitStatus = git status --porcelain $dbSyncFile
        if ($gitStatus) {
            $hasChanges = $true
        }
    }
    
    # Also check for any other uncommitted changes
    $allChanges = git status --porcelain
    if ($allChanges) {
        $hasChanges = $true
    }
    
    if ($hasChanges) {
        Write-ColorLog "Changes detected, committing..." "Yellow" "[GIT] "
        
        try {
            git add -A
            git commit -m $Message
            git push
            
            Write-ColorLog "Changes committed and pushed" "Green" "[GIT] "
            return $true
        } catch {
            Write-ColorLog "Git commit failed: $_" "Red" "[GIT] "
            return $false
        }
    } else {
        Write-ColorLog "No changes to commit" "Gray" "[GIT] "
        return $false
    }
}

function Start-WebDashboard {
    Write-ColorLog "Starting Web Dashboard..." "Cyan" "[WEB] "
    
    # Find Python executable
    $pythonExe = "python"
    if (Test-Path "venv\Scripts\python.exe") {
        $pythonExe = "venv\Scripts\python.exe"
    }
    
    $webLogFile = $logFile -replace '\.log$', '_web.log'
    
    $webJob = Start-Job -ScriptBlock {
        param($PythonPath, $ScriptDir, $LogFile)
        Set-Location $ScriptDir
        & $PythonPath -u web_dashboard.py 2>&1 | Tee-Object -FilePath $LogFile -Append
    } -ArgumentList $pythonExe, $PSScriptRoot, $webLogFile
    
    # Wait for dashboard to start
    $retries = 0
    $maxRetries = 15
    
    while ($retries -lt $maxRetries) {
        Start-Sleep -Seconds 2
        
        $connection = Test-NetConnection -ComputerName localhost -Port 5000 -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
        if ($connection -and $connection.TcpTestSucceeded) {
            Write-ColorLog "Web Dashboard running at http://localhost:5000" "Green" "[WEB] "
            return $webJob
        }
        
        if ($webJob.State -eq 'Failed' -or $webJob.State -eq 'Stopped') {
            Write-ColorLog "Web Dashboard failed to start" "Red" "[WEB] "
            Remove-Job -Job $webJob -Force
            return $null
        }
        
        $retries++
    }
    
    Write-ColorLog "Web Dashboard start timeout" "Yellow" "[WEB] "
    return $webJob
}

function Start-Bot {
    Write-ColorLog "Starting bot..." "Cyan" "[BOT] "
    
    Update-BotStatus "Starting..."
    
    # Find Python executable
    $pythonExe = "python"
    if (Test-Path "venv\Scripts\python.exe") {
        $pythonExe = "venv\Scripts\python.exe"
    }
    
    $botCommand = "& `"$pythonExe`" -u bot.py 2>&1 | Tee-Object -FilePath `"$botLogFile`" -Append"
    $process = Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", $botCommand -PassThru
    
    Update-BotStatus "Running" $process.Id
    Write-ColorLog "Bot started (PID: $($process.Id))" "Green" "[BOT] "
    
    return $process
}

function Test-ForUpdates {
    Write-ColorLog "Checking for updates..." "Gray" "[UPDATE] "
    
    try {
        git remote update 2>&1 | Out-Null
        $status = git status -uno
        
        if ($status -like "*Your branch is behind*") {
            Write-ColorLog "Updates available!" "Yellow" "[UPDATE] "
            return $true
        }
        
        return $false
    } catch {
        Write-ColorLog "Update check failed: $_" "Red" "[UPDATE] "
        return $false
    }
}

function Invoke-Update {
    Write-ColorLog "Applying updates..." "Cyan" "[UPDATE] "
    
    Update-BotStatus "Updating..."
    
    # Commit any pending changes first
    Invoke-GitCommit "chore: Auto-commit before update"
    
    # Check if maintain_bot.ps1 is being updated
    git fetch 2>&1 | Out-Null
    $changedFiles = git diff --name-only HEAD...origin/main
    $watcherUpdated = $changedFiles -like "*maintain_bot.ps1*"
    
    if ($watcherUpdated) {
        Write-ColorLog "Maintenance script will be updated - restarting watcher..." "Magenta" "[UPDATE] "
        
        # Pull updates
        git pull
        
        # Stop web dashboard
        if ($script:webDashboardJob) {
            Stop-Job -Job $script:webDashboardJob -ErrorAction SilentlyContinue
            Remove-Job -Job $script:webDashboardJob -Force -ErrorAction SilentlyContinue
        }
        
        # Restart this script
        Start-Process powershell.exe -ArgumentList "-File `"$PSScriptRoot\maintain_bot.ps1`""
        Stop-Transcript
        exit 0
    }
    
    # Normal update
    git pull
    
    Write-ColorLog "Update complete" "Green" "[UPDATE] "
    (Get-Date).ToUniversalTime().ToString("o") | Out-File -FilePath "last_update.txt" -Encoding utf8
}

# ==================== MAIN LOOP ====================

Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║       Sulfur Discord Bot - Maintenance System v2.0        ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-ColorLog "Press 'Q' at any time to gracefully shutdown" "Yellow"
Write-Host ""

# Initial database backup
if (-not $SkipDatabaseBackup) {
    Invoke-DatabaseBackup
}

# Start web dashboard
$script:webDashboardJob = Start-WebDashboard
if (-not $script:webDashboardJob) {
    Write-ColorLog "Warning: Web Dashboard failed to start, continuing anyway..." "Yellow"
}

# Main loop
$checkCounter = 0
$checkInterval = 60  # Check for updates every 60 seconds
$backupInterval = 1800  # Backup database every 30 minutes
$commitInterval = 300  # Auto-commit every 5 minutes

while ($true) {
    # Start bot
    $script:botProcess = Start-Bot
    
    # Monitor bot
    while ($script:botProcess -and (Get-Process -Id $script:botProcess.Id -ErrorAction SilentlyContinue)) {
        Start-Sleep -Seconds 1
        $checkCounter++
        
        # Check for shutdown key
        if ([System.Console]::KeyAvailable) {
            $key = [System.Console]::ReadKey($true)
            if ($key.Key -eq 'Q') {
                Write-ColorLog "Shutdown requested" "Yellow"
                
                Stop-Process -Id $script:botProcess.Id -Force
                Start-Sleep -Seconds 2
                
                Invoke-DatabaseBackup
                Invoke-GitCommit "chore: Auto-commit on shutdown"
                
                Update-BotStatus "Shutdown"
                if ($script:webDashboardJob) {
                    Stop-Job -Job $script:webDashboardJob -ErrorAction SilentlyContinue
                    Remove-Job -Job $script:webDashboardJob -Force -ErrorAction SilentlyContinue
                }
                
                Stop-Transcript
                exit 0
            }
        }
        
        # Check for control flags
        if (Test-Path "stop.flag") {
            Write-ColorLog "Stop flag detected" "Yellow"
            Remove-Item "stop.flag" -ErrorAction SilentlyContinue
            
            Stop-Process -Id $script:botProcess.Id -Force
            Start-Sleep -Seconds 2
            
            Invoke-DatabaseBackup
            Invoke-GitCommit "chore: Auto-commit on stop"
            
            Update-BotStatus "Shutdown"
            if ($script:webDashboardJob) {
                Stop-Job -Job $script:webDashboardJob -ErrorAction SilentlyContinue
                Remove-Job -Job $script:webDashboardJob -Force -ErrorAction SilentlyContinue
            }
            
            Stop-Transcript
            exit 0
        }
        
        if (Test-Path "restart.flag") {
            Write-ColorLog "Restart flag detected" "Yellow"
            Remove-Item "restart.flag" -ErrorAction SilentlyContinue
            
            Stop-Process -Id $script:botProcess.Id -Force
            break
        }
        
        # Periodic tasks
        if ($checkCounter % $commitInterval -eq 0) {
            Invoke-GitCommit "chore: Auto-commit database changes"
        }
        
        if ($checkCounter % $backupInterval -eq 0) {
            Invoke-DatabaseBackup
        }
        
        if ($checkCounter % $checkInterval -eq 0) {
            (Get-Date).ToUniversalTime().ToString("o") | Out-File -FilePath "last_check.txt" -Encoding utf8
            
            if (Test-ForUpdates) {
                Write-ColorLog "Stopping bot for update..." "Yellow" "[UPDATE] "
                Stop-Process -Id $script:botProcess.Id -Force
                Start-Sleep -Seconds 2
                
                Invoke-Update
                break  # Restart bot with new code
            }
        }
        
        # Check web dashboard
        if ($script:webDashboardJob -and $script:webDashboardJob.State -ne 'Running') {
            Write-ColorLog "Web Dashboard stopped, restarting..." "Yellow" "[WEB] "
            $script:webDashboardJob = Start-WebDashboard
        }
    }
    
    Update-BotStatus "Stopped"
    Write-ColorLog "Bot stopped, restarting in 5 seconds..." "Yellow"
    Start-Sleep -Seconds 5
}
