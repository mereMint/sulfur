# This script acts as a watcher to maintain the Sulfur bot.
# It starts the bot and then checks for updates from the Git repository every minute.
# If updates are found, it automatically restarts the bot.
#
# --- NEW: How to Stop ---
# To gracefully shut down the bot and this script, press the 'Q' key.
# The script will stop the bot, perform a final database commit if needed, and then exit.
#

# To run it:
# 1. Open PowerShell
# 2. Navigate to this directory (cd c:\sulfur)
# 3. Run the script with: .\maintain_bot.ps1

# --- NEW: Initialize process variables ---
$statusFile = Join-Path -Path $PSScriptRoot -ChildPath "config\bot_status.json"
$script:webDashboardJob = $null
$script:botProcess = $null

# --- NEW: Centralized Logging Setup ---
$logDir = Join-Path -Path $PSScriptRoot -ChildPath "logs"
if (-not (Test-Path -Path $logDir -PathType Container)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}
$logTimestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$logFile = Join-Path -Path $logDir -ChildPath "session_${logTimestamp}.log"

# Start logging all output from this script to the central log file.
Start-Transcript -Path $logFile -Append

# --- NEW: Trap to catch script termination (e.g., closing the window) ---
trap [System.Management.Automation.PipelineStoppedException] {
    Write-Host "Watcher window closed or script stopped. Cleaning up child processes..." -ForegroundColor Red
    # Gracefully stop child processes
    if ($script:botProcess) { Stop-Process -Id $script:botProcess.Id -Force -ErrorAction SilentlyContinue }
    if ($script:webDashboardJob) { 
        Stop-Job -Job $script:webDashboardJob -ErrorAction SilentlyContinue
        Remove-Job -Job $script:webDashboardJob -Force -ErrorAction SilentlyContinue
    }
    [System.IO.File]::WriteAllText($statusFile, (@{status = "Shutdown" } | ConvertTo-Json -Compress), ([System.Text.UTF8Encoding]::new($false)))
    Stop-Transcript
    exit 0
}

Write-Host "--- Sulfur Bot Maintenance Watcher ---"
Write-Host "Press 'Q' at any time to gracefully shut down the bot and exit." -ForegroundColor Yellow

# --- NEW: Import shared functions ---
. "$PSScriptRoot\scripts\shared_functions.ps1"

# --- NEW: Ensure the Python virtual environment and dependencies are ready ---
Write-Host "Checking Python virtual environment..."
$venvPython = Invoke-VenvSetup -ScriptRoot $PSScriptRoot
Write-Host "Python environment is ready."

# --- NEW: Define the file to watch for database changes ---
$dbSyncFile = "config\database_sync.sql"

# --- NEW: Function to start and verify the Web Dashboard ---
function Start-WebDashboard {
    param(
        [string]$PythonExecutable,
        [string]$LogFilePath
    )
    Write-Host "Starting the Web Dashboard as a background process..."
    
    # Create separate log file for web dashboard to avoid file locking issues
    $webLogFile = $LogFilePath -replace '\.log$', '_web.log'
    
    # --- FIX: Use background job with separate log file ---
    $webDashboardJob = Start-Job -ScriptBlock {
        param($PythonPath, $ScriptDir, $LogFile)
        Set-Location $ScriptDir
        & $PythonPath -u web\web_dashboard.py 2>&1 | Tee-Object -FilePath $LogFile -Append
    } -ArgumentList $PythonExecutable, $PSScriptRoot, $webLogFile
    
    Write-Host "Web Dashboard job started (Job ID: $($webDashboardJob.Id))"
    
    # Wait for the Web Dashboard to become available
    $maxRetries = 15
    $retryCount = 0
    $dashboardUrl = "http://localhost:5000"
    
    Write-Host "Waiting for the Web Dashboard to become available on $dashboardUrl..."
    while ($retryCount -lt $maxRetries) {
        Start-Sleep -Seconds 2
        
        # Check if port 5000 is open (more reliable than HTTP check)
        $connection = Test-NetConnection -ComputerName localhost -Port 5000 -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
        if ($connection -and $connection.TcpTestSucceeded) {
            Write-Host "Web Dashboard is now accessible at $dashboardUrl" -ForegroundColor Green
            return $webDashboardJob
        }
        
        # Check if job failed
        if ($webDashboardJob.State -eq 'Failed' -or $webDashboardJob.State -eq 'Stopped') {
            Write-Host "Web Dashboard job failed during startup. Check logs for error messages." -ForegroundColor Red
            Write-Host "Log file: $webLogFile" -ForegroundColor Yellow
            $jobOutput = Receive-Job -Job $webDashboardJob -ErrorAction SilentlyContinue
            if ($jobOutput) {
                Write-Host "Job output:" -ForegroundColor Yellow
                Write-Host $jobOutput -ForegroundColor Gray
            }
            Remove-Job -Job $webDashboardJob -Force
            return $null
        }
        
        $retryCount++
    }
    
    Write-Host "Web Dashboard did not start within the expected time." -ForegroundColor Yellow
    Write-Host "Continuing without web dashboard. Check log: $webLogFile" -ForegroundColor Yellow
    return $webDashboardJob
}

# --- Start the Web Dashboard for the first time ---
$script:webDashboardJob = Start-WebDashboard -PythonExecutable $venvPython -LogFilePath $logFile
if (-not $script:webDashboardJob) {
    Write-Host "Failed to start the Web Dashboard. Exiting." -ForegroundColor Red
    Stop-Transcript
    exit 1
}

# --- Function to check if a process is running ---
function Test-ProcessRunning {
    param(
        [int]$ProcessId
    )
    return $null -ne (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)
}

# --- Function to gracefully stop a process ---
function Stop-ProcessGracefully {
    param([int]$ProcessId)
    if (Test-ProcessRunning -ProcessId $ProcessId) {
        Stop-Process -Id $ProcessId -Force
    }
}

# --- NEW: Function to receive and log job output ---
function Receive-JobOutput {
    param(
        [System.Management.Automation.Job]$Job,
        [string]$LogFilePath
    )
    while ($Job.HasMoreData) {
        $output = Receive-Job -Job $Job -Keep
        $output | Add-Content -Path $LogFilePath -Encoding utf8
    }
}

while ($true) {
    [System.IO.File]::WriteAllText($statusFile, (@{status = "Starting..." } | ConvertTo-Json -Compress), ([System.Text.UTF8Encoding]::new($false)))
    Write-Host "Starting the bot process..."
    # --- FINAL FIX: Use Start-Process to launch the bot in a new window. ---
    # The start_bot.ps1 script itself will handle logging its output to the file we provide.
    $botCommand = "& `"$PSScriptRoot\\scripts\\start_bot.ps1`" -LogFile `"$logFile`""
    $script:botProcess = Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", $botCommand -PassThru

    [System.IO.File]::WriteAllText($statusFile, (@{status = "Running"; pid = $script:botProcess.Id } | ConvertTo-Json -Compress), ([System.Text.UTF8Encoding]::new($false)))
    Write-Host "Bot is running in a new window (Process ID: $($script:botProcess.Id)). Checking for updates every 60 seconds."

    # --- NEW: Counter for periodic checks ---
    $checkCounter = 0
    $checkIntervalSeconds = 15

    while (Test-ProcessRunning -ProcessId $script:botProcess.Id) {
        # --- Receive any output from the web dashboard job ---
        if ($script:webDashboardJob -and $script:webDashboardJob.HasMoreData) {
            Receive-Job -Job $script:webDashboardJob | Out-Null
        }
        
        # --- Check for shutdown key press ---
        if ([System.Console]::KeyAvailable) {
            $key = [System.Console]::ReadKey($true) # $true hides the key press from the console
            if ($key.Key -eq 'Q') {
                Write-Host "Shutdown key ('Q') pressed. Stopping bot and exiting..." -ForegroundColor Yellow
                # --- FIX: Use the correct variable and command ---
                if ($script:botProcess) { Stop-Process -Id $script:botProcess.Id -Force }
                # The start_bot script's exit trap handles the DB dump. Give it a moment.
                Start-Sleep -Seconds 2

                # Check for and commit any final database changes
                if (git status --porcelain | Select-String -Pattern $dbSyncFile) {
                    Write-Host "Final database changes detected. Committing and pushing..." -ForegroundColor Cyan
                    git add $dbSyncFile
                    git commit -m "chore: Sync database schema on shutdown"
                    git push
                }

                Write-Host "Shutdown complete."
                [System.IO.File]::WriteAllText($statusFile, (@{status = "Shutdown" } | ConvertTo-Json -Compress), ([System.Text.UTF8Encoding]::new($false)))
                if ($script:webDashboardJob) { 
                    Stop-Job -Job $script:webDashboardJob -ErrorAction SilentlyContinue
                    Remove-Job -Job $script:webDashboardJob -Force -ErrorAction SilentlyContinue
                }
                Stop-Transcript
                exit 0
            }
        }

        # --- NEW: Check for control flags from web dashboard ---
        if (Test-Path -Path "stop.flag") {
            Write-Host "Stop signal received from web dashboard. Shutting down..." -ForegroundColor Yellow
            if ($script:botProcess) { Stop-Process -Id $script:botProcess.Id -Force }
            Start-Sleep -Seconds 2
            Remove-Item "stop.flag" -ErrorAction SilentlyContinue
            # Final DB commit
            if (git status --porcelain | Select-String -Pattern $dbSyncFile) {
                git add $dbSyncFile; git commit -m "chore: Sync database schema on shutdown"; git push
            }
            [System.IO.File]::WriteAllText($statusFile, (@{status = "Shutdown" } | ConvertTo-Json -Compress), ([System.Text.UTF8Encoding]::new($false)))
            if ($script:webDashboardJob) {
                Stop-Job -Job $script:webDashboardJob -ErrorAction SilentlyContinue
                Remove-Job -Job $script:webDashboardJob -Force -ErrorAction SilentlyContinue
            }
            Stop-Transcript
            exit 0
        }
        if (Test-Path -Path "restart.flag") {
            Write-Host "Restart signal received from web dashboard. Restarting bot..." -ForegroundColor Yellow
            Remove-Item "restart.flag" -ErrorAction SilentlyContinue
            [System.IO.File]::WriteAllText($statusFile, (@{status = "Restarting..." } | ConvertTo-Json -Compress), ([System.Text.UTF8Encoding]::new($false)))
            Stop-Process -Id $script:botProcess.Id -Force
            break # Break inner loop to trigger restart
        }

        # --- REFACTORED: Use a short sleep and a counter for responsiveness ---
        Start-Sleep -Seconds 1
        $checkCounter++

        # Only run the expensive update check every $checkIntervalSeconds
        if ($checkCounter -ge $checkIntervalSeconds) {
            # --- Log the time of the update check ---
            # --- NEW: Check if the web dashboard is still running, restart if not ---
            if ($script:webDashboardJob.State -ne 'Running') {
                Write-Host "Web Dashboard job is not running. Attempting to restart..." -ForegroundColor Yellow
                $script:webDashboardJob = Start-WebDashboard -PythonExecutable $venvPython -LogFilePath $logFile
            }

            (Get-Date).ToUniversalTime().ToString("o") | Out-File -FilePath "last_check.txt" -Encoding utf8

            # Fetch the latest changes from the remote repository
            git remote update
            $status = git status -uno

            if ($status -like "*Your branch is behind*") {
                [System.IO.File]::WriteAllText($statusFile, (@{status = "Updating..." } | ConvertTo-Json -Compress), ([System.Text.UTF8Encoding]::new($false)))
                Write-Host "New version found in the repository! Restarting the bot to apply updates..."
                # Create the flag file to signal the bot to go idle
                New-Item -Path "update_pending.flag" -ItemType File -Force | Out-Null
                Stop-Process -Id $script:botProcess.Id -Force # Stop the bot
                Start-Sleep -Seconds 2 # Give it a moment for the exit trap to run
                
                # --- NEW: Commit database changes before pulling ---
                if (git status --porcelain | Select-String -Pattern $dbSyncFile) {
                    Write-Host "Database changes detected. Committing and pushing before update..." -ForegroundColor Cyan
                    git add $dbSyncFile
                    git commit -m "chore: Sync database schema before update"
                    git push
                }

                # --- REFACTORED: Self-update logic ---
                # Check if the watcher script itself is being updated.
                git fetch
                $changed_files = git diff --name-only HEAD...origin/main
                $watcher_updated = $changed_files -like "*maintain_bot.ps1*"

                if ($watcher_updated) {
                    Write-Host "Watcher script has been updated! Rebooting the entire watcher system..." -ForegroundColor Magenta
                    if ($script:webDashboardProcess) { Stop-Process -Id $script:webDashboardProcess.Id -Force -ErrorAction SilentlyContinue }
                    # Start the bootstrapper to restart the watcher, then exit this old instance.
                    Start-Process powershell.exe -ArgumentList "-File `"$($PSScriptRoot)\bootstrapper.ps1`""
                    Stop-Transcript
                    exit 0
                }

                Write-Host "Pulling latest changes from git..."
                git pull

                # --- Log the time of the successful update ---
                (Get-Date).ToUniversalTime().ToString("o") | Out-File -FilePath "last_update.txt" -Encoding utf8
                Remove-Item -Path "update_pending.flag" -ErrorAction SilentlyContinue # Clean up the flag
                break # Exit the inner loop to allow the outer loop to restart it
            }
            # Reset the counter after a check
            $checkCounter = 0
        }
    }

    # --- NEW: Clean up the finished job before restarting ---
    # No longer using jobs for the main processes, so this is not needed.

    [System.IO.File]::WriteAllText($statusFile, (@{status = "Stopped" } | ConvertTo-Json -Compress), ([System.Text.UTF8Encoding]::new($false)))
    Write-Host "Bot process stopped. It will be restarted shortly..."
    Start-Sleep -Seconds 5 # Brief pause before restarting
}