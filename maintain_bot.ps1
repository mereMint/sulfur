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
$script:webDashboardProcess = $null
$script:botProcess = $null

# --- NEW: Trap to catch script termination (e.g., closing the window) ---
trap [System.Management.Automation.PipelineStoppedException] {
    Write-Host "Watcher window closed or script stopped. Cleaning up child processes..." -ForegroundColor Red
    # Gracefully stop child processes
    if ($script:botProcess) { Stop-Process -Id $script:botProcess.Id -Force -ErrorAction SilentlyContinue }
    if ($script:webDashboardProcess) { Stop-Process -Id $script:webDashboardProcess.Id -Force -ErrorAction SilentlyContinue }
    # Exit the script cleanly
    exit 0
}

Write-Host "--- Sulfur Bot Maintenance Watcher ---"
Write-Host "Press 'Q' at any time to gracefully shut down the bot and exit." -ForegroundColor Yellow

# --- NEW: Import shared functions ---
. "$PSScriptRoot\shared_functions.ps1"

# --- NEW: Ensure the Python virtual environment and dependencies are ready ---
Write-Host "Checking Python virtual environment..."
$venvPython = Invoke-VenvSetup -ScriptRoot $PSScriptRoot
Write-Host "Python environment is ready."

# --- NEW: Define the file to watch for database changes ---
$dbSyncFile = "database_sync.sql"

# --- NEW: Function to start and verify the Web Dashboard ---
function Start-WebDashboard {
    param(
        [string]$PythonExecutable
    )
    Write-Host "Starting the Web Dashboard in a new window..."
    $webDashboardCommand = "& `"$PythonExecutable`" -u web_dashboard.py"
    $webDashboardProcess = Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", $webDashboardCommand -PassThru
    Write-Host "Web Dashboard process started (Process ID: $($webDashboardProcess.Id))"

    Write-Host "Waiting for the Web Dashboard to become available on http://localhost:5000..." -ForegroundColor Gray
    $timeoutSeconds = 15
    $startTime = Get-Date
    $serverReady = $false

    while (((Get-Date) - $startTime).TotalSeconds -lt $timeoutSeconds) {
        if ($null -eq (Get-Process -Id $webDashboardProcess.Id -ErrorAction SilentlyContinue)) {
            Write-Host "Web Dashboard process terminated unexpectedly during startup. Check the new window for error messages." -ForegroundColor Red
            return $null
        }
        if (Test-NetConnection -ComputerName localhost -Port 5000 -WarningAction SilentlyContinue -ErrorAction SilentlyContinue) {
            $serverReady = $true
            break
        }
        Start-Sleep -Seconds 1
    }

    if (-not $serverReady) {
        Write-Host "Error: Web Dashboard did not become available within $timeoutSeconds seconds. Shutting down." -ForegroundColor Red
        Stop-Process -Id $webDashboardProcess.Id -Force -ErrorAction SilentlyContinue
        return $null
    }

    Write-Host "Web Dashboard is online and ready." -ForegroundColor Green
    return $webDashboardProcess
}

# --- Start the Web Dashboard for the first time ---
$script:webDashboardProcess = Start-WebDashboard -PythonExecutable $venvPython
if ($null -eq $script:webDashboardProcess) {
    Write-Host "Failed to start the Web Dashboard. Exiting." -ForegroundColor Red
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

while ($true) {
    Write-Host "Starting the bot process..."
    # Start the main bot script as a background job.
    # This allows the watcher to continue running while the bot is active.
    $script:botProcess = Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", "& `"$($PSScriptRoot)\start_bot.ps1`"" -PassThru

    Write-Host "Bot is running in a new window (Process ID: $($script:botProcess.Id)). Checking for updates every 60 seconds."

    # --- NEW: Counter for periodic checks ---
    $checkCounter = 0
    $checkIntervalSeconds = 15

    while (Test-ProcessRunning -ProcessId $script:botProcess.Id) {
        # --- Check for shutdown key press ---
        if ([System.Console]::KeyAvailable) {
            $key = [System.Console]::ReadKey($true) # $true hides the key press from the console
            if ($key.Key -eq 'Q') {
                Write-Host "Shutdown key ('Q') pressed. Stopping bot and exiting..." -ForegroundColor Yellow
                Stop-ProcessGracefully -ProcessId $script:botProcess.Id
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
                Stop-ProcessGracefully -ProcessId $script:webDashboardProcess.Id # Stop the web dashboard
                exit 0
            }
        }

        # --- NEW: Check for control flags from web dashboard ---
        if (Test-Path -Path "stop.flag") {
            Write-Host "Stop signal received from web dashboard. Shutting down..." -ForegroundColor Yellow
            Stop-ProcessGracefully -ProcessId $script:botProcess.Id
            Start-Sleep -Seconds 2
            Remove-Item "stop.flag" -ErrorAction SilentlyContinue
            # Final DB commit
            if (git status --porcelain | Select-String -Pattern $dbSyncFile) {
                git add $dbSyncFile; git commit -m "chore: Sync database schema on shutdown"; git push
            }
            Stop-ProcessGracefully -ProcessId $script:webDashboardProcess.Id # Stop the web dashboard
            exit 0
        }
        if (Test-Path -Path "restart.flag") {
            Write-Host "Restart signal received from web dashboard. Restarting bot..." -ForegroundColor Yellow
            Remove-Item "restart.flag" -ErrorAction SilentlyContinue
            # Setting status to trigger a restart in the outer loop
            $status = "*Your branch is behind*" 
        }

        # --- REFACTORED: Use a short sleep and a counter for responsiveness ---
        Start-Sleep -Seconds 1
        $checkCounter++

        # Only run the expensive update check every $checkIntervalSeconds
        if ($checkCounter -ge $checkIntervalSeconds) {
            # --- Log the time of the update check ---
            # --- NEW: Check if the web dashboard is still running, restart if not ---
            if ($null -eq (Get-Process -Id $script:webDashboardProcess.Id -ErrorAction SilentlyContinue)) {
                Write-Host "Web Dashboard process is not running. Attempting to restart..." -ForegroundColor Yellow
                $script:webDashboardProcess = Start-WebDashboard -PythonExecutable $venvPython
            }

            (Get-Date).ToUniversalTime().ToString("o") | Out-File -FilePath "last_check.txt" -Encoding utf8

            # Fetch the latest changes from the remote repository
            git remote update
            $status = git status -uno

            if ($status -like "*Your branch is behind*") {
                Write-Host "New version found in the repository! Restarting the bot to apply updates..."
                # Create the flag file to signal the bot to go idle
                New-Item -Path "update_pending.flag" -ItemType File -Force | Out-Null
                Stop-ProcessGracefully -ProcessId $script:botProcess.Id # Stop the bot
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
                    if ($script:webDashboardProcess) { Stop-ProcessGracefully -ProcessId $script:webDashboardProcess.Id }
                    # Start the bootstrapper to restart the watcher, then exit this old instance.
                    Start-Process powershell.exe -ArgumentList "-File `"$($PSScriptRoot)\bootstrapper.ps1`""
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

    Write-Host "Bot process stopped. It will be restarted shortly..."
    Start-Sleep -Seconds 5 # Brief pause before restarting
}