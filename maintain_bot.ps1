<# Replaced with fixed process management variant. See maintain_bot_fixed.ps1 history for prior content. #>
# ==============================================================================
# Sulfur Bot - Maintenance Script (Fixed Process Management)
# ==============================================================================
param([switch]$SkipDatabaseBackup)
$ErrorActionPreference='Continue'
$statusFile=Join-Path $PSScriptRoot 'config\bot_status.json'
$logDir=Join-Path $PSScriptRoot 'logs'
if(-not(Test-Path $logDir)){New-Item -ItemType Directory -Path $logDir|Out-Null}
$ts=Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'
$logFile=Join-Path $logDir "maintenance_$ts.log"
$botLogFile=Join-Path $logDir "bot_$ts.log"
Start-Transcript -Path $logFile -Append | Out-Null

# Cleanup function
function Invoke-Cleanup {
    Write-Host 'Cleaning up processes...' -ForegroundColor Yellow
    
    # Close file handles
    if($script:botOutputFile) {
        try {
            $script:botOutputFile.Close()
            $script:botOutputFile.Dispose()
        } catch {}
        $script:botOutputFile = $null
    }
    if($script:botErrorFile) {
        try {
            $script:botErrorFile.Close()
            $script:botErrorFile.Dispose()
        } catch {}
        $script:botErrorFile = $null
    }
    
    # Kill bot process
    if($script:botProcess) {
        if(-not $script:botProcess.HasExited){
            Write-Host "Stopping bot process (PID: $($script:botProcess.Id))..." -ForegroundColor Yellow
            try {
                $script:botProcess.Kill()
                $script:botProcess.WaitForExit(5000)
            } catch {
                Stop-Process -Id $script:botProcess.Id -Force -ErrorAction SilentlyContinue
            }
        }
        try { $script:botProcess.Close() } catch {}
        $script:botProcess = $null
    }
    
    # Stop web dashboard
    if($script:webDashboardJob){
        Write-Host 'Stopping Web Dashboard...' -ForegroundColor Yellow
        Stop-Job $script:webDashboardJob -ErrorAction SilentlyContinue
        Remove-Job $script:webDashboardJob -Force -ErrorAction SilentlyContinue
        $script:webDashboardJob = $null
    }
    
    # Kill orphaned Python processes from this directory
    $orphans = Get-Process -Name python* -ErrorAction SilentlyContinue | Where-Object {
        try {
            $_.Path -and ($_.Path -like "*$PSScriptRoot*")
        } catch {
            $false
        }
    }
    if($orphans){
        Write-Host "Cleaning up $($orphans.Count) orphaned Python processes..." -ForegroundColor Yellow
        $orphans | ForEach-Object {
            try {
                $_.Kill()
                $_.WaitForExit(2000)
            } catch {
                Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
            }
        }
    }
}

# Register cleanup handler for Ctrl+C and script termination
trap {
    Write-Host 'Script terminated. Running cleanup...' -ForegroundColor Red
    if ($_) {
        try {
            Write-Host ("Error: {0}" -f ($_.Exception.Message)) -ForegroundColor Red
            if ($_.Exception) { Write-Host ($_.Exception.ToString()) -ForegroundColor DarkRed }
            if ($_.ScriptStackTrace) { Write-Host '--- StackTrace ---' -ForegroundColor DarkYellow; Write-Host $_.ScriptStackTrace }
        } catch {}
    }
    Invoke-Cleanup
    Update-BotStatus 'Shutdown'
    Write-Host 'Cleanup complete.' -ForegroundColor Green
    Stop-Transcript
    exit 1
}

# Also register an exit handler
$null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action {
    Invoke-Cleanup
}

function Write-ColorLog {
    param([string]$Message,[string]$Color='White',[string]$Prefix='')
    $t=Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    Write-Host "[$t] $Prefix$Message" -ForegroundColor $Color
}

function Test-Preflight {
    $envPath = Join-Path $PSScriptRoot '.env'
    if(-not (Test-Path $envPath)){
        Write-ColorLog "Missing .env file. Create one or copy .env.example" 'Red'
        return $false
    }
    try{
        $envLines = Get-Content -Path $envPath -ErrorAction Stop
        $tokenLine = $envLines | Where-Object { $_ -match '^\s*DISCORD_BOT_TOKEN\s*=\s*' } | Select-Object -First 1
        if(-not $tokenLine){
            Write-ColorLog "DISCORD_BOT_TOKEN not found in .env" 'Red'
            return $false
        }
        $token = ($tokenLine -replace '^[^=]*=','').Trim().Trim('"','''')
        if([string]::IsNullOrWhiteSpace($token)){
            Write-ColorLog "DISCORD_BOT_TOKEN is empty in .env" 'Red'
            return $false
        }
        $parts = $token.Split('.')
        if($parts.Count -ne 3){
            Write-ColorLog "DISCORD_BOT_TOKEN appears malformed (expected 3 parts)" 'Red'
            return $false
        }
    } catch {
        Write-ColorLog "Preflight check failed: $($_.Exception.Message)" 'Red'
        return $false
    }
    return $true
}

function Update-BotStatus {
    param([string]$Status,[int]$BotProcessId=0)
    $statusData=@{status=$Status;timestamp=(Get-Date).ToUniversalTime().ToString('o')}
    if($BotProcessId -gt 0){$statusData.pid=$BotProcessId}
    [IO.File]::WriteAllText($statusFile,($statusData|ConvertTo-Json -Compress),[Text.UTF8Encoding]::new($false))
}

function Invoke-DatabaseBackup {
    Write-ColorLog 'Creating database backup...' 'Cyan' '[DB] '
    try {
        $dumpCmd=$null
        if(Get-Command mariadb-dump -ErrorAction SilentlyContinue){
            $dumpCmd='mariadb-dump'
        }elseif(Get-Command mysqldump -ErrorAction SilentlyContinue){
            $dumpCmd='mysqldump'
        }
        
        $user=$env:DB_USER
        if(-not $user){$user='sulfur_bot_user'}
        $db=$env:DB_NAME
        if(-not $db){$db='sulfur_bot'}
        $backupDir=Join-Path $PSScriptRoot 'backups'
        if(-not(Test-Path $backupDir)){New-Item -ItemType Directory -Path $backupDir|Out-Null}
        $backupFile=Join-Path $backupDir "sulfur_bot_backup_$(Get-Date -Format 'yyyy-MM-dd_HH-mm-ss').sql"
        
        if($dumpCmd){
            & $dumpCmd -u $user $db > $backupFile 2>$null
        } else {
            'mysqldump/mariadb-dump not found; placeholder backup entry.' | Out-File -FilePath $backupFile
        }
        if(Test-Path $backupFile){
            Write-ColorLog "Backup created: $backupFile" 'Green' '[DB] '
            $allBackups=Get-ChildItem $backupDir -Filter *.sql | Sort-Object LastWriteTime -Descending
            if($allBackups.Count -gt 10){
                $allBackups|Select-Object -Skip 10 | Remove-Item -Force
                Write-ColorLog 'Pruned old backups (kept 10)' 'Yellow' '[DB] '
            }
            return $true
        } else {
            Write-ColorLog 'Backup failed' 'Red' '[DB] '
            return $false
        }
    } catch {
        Write-ColorLog "Backup error: $($_.Exception.Message)" 'Red' '[DB] '
        return $false
    }
}

function Invoke-GitCommit {
    param([string]$Message='chore: Auto-commit from maintenance script')
    Write-ColorLog 'Checking for changes...' 'Cyan' '[GIT] '
    
    # Check if git user is configured
    $gitUser = git config user.name 2>$null
    $gitEmail = git config user.email 2>$null
    
    if([string]::IsNullOrWhiteSpace($gitUser) -or [string]::IsNullOrWhiteSpace($gitEmail)){
        Write-ColorLog 'Git user not configured, setting default values...' 'Yellow' '[GIT] '
        git config user.name "Sulfur Bot Maintenance" 2>&1 | Out-Null
        git config user.email "sulfur-bot@localhost" 2>&1 | Out-Null
    }
    
    $hasChanges=$false
    $syncFile='config\database_sync.sql'
    if(Test-Path $syncFile){
        if(git status --porcelain $syncFile){
            $hasChanges=$true
        }
    }
    if(git status --porcelain){
        $hasChanges=$true
    }
    if($hasChanges){
        Write-ColorLog 'Changes detected, committing...' 'Yellow' '[GIT] '
        
        # Stage all changes
        git add -A 2>&1 | Out-Null
        if($LASTEXITCODE -ne 0){
            Write-ColorLog "Git add failed (exit code: $LASTEXITCODE)" 'Red' '[GIT] '
            return $false
        }
        
        # Commit changes
        git commit -m $Message 2>&1 | Out-Null
        if($LASTEXITCODE -ne 0){
            Write-ColorLog "Git commit failed (exit code: $LASTEXITCODE)" 'Red' '[GIT] '
            return $false
        }
        
        # Try to push changes
        git push 2>&1 | Out-Null
        if($LASTEXITCODE -ne 0){
            Write-ColorLog "Git push failed (exit code: $LASTEXITCODE) - commits are local only" 'Yellow' '[GIT] '
            Write-ColorLog "Changes committed locally (push failed - check credentials/network)" 'Yellow' '[GIT] '
            return $true  # Return true since commit succeeded, even if push failed
        }
        
        Write-ColorLog 'Changes committed & pushed' 'Green' '[GIT] '
        return $true
    } else {
        Write-ColorLog 'No changes to commit' 'Gray' '[GIT] '
        return $false
    }
}

function Test-PortAvailable {
    param([int]$Port)
    try {
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Any, $Port)
        $listener.Start()
        $listener.Stop()
        return $true
    } catch {
        return $false
    }
}

function Clear-Port {
    param([int]$Port)
    Write-ColorLog "Attempting to free port $Port..." 'Yellow' '[WEB] '
    
    try {
        # Find processes using the port
        $connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
        if($connections){
            $pids = $connections | Select-Object -ExpandProperty OwningProcess -Unique
            Write-ColorLog "Found processes using port ${Port}: $($pids -join ', ')" 'Yellow' '[WEB] '
            
            foreach($pid in $pids){
                try {
                    $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
                    if($proc){
                        Write-ColorLog "Stopping process $pid ($($proc.ProcessName))..." 'Yellow' '[WEB] '
                        Stop-Process -Id $pid -Force -ErrorAction Stop
                        Start-Sleep -Seconds 2
                    }
                } catch {
                    Write-ColorLog "Failed to stop process ${pid}: $($_.Exception.Message)" 'Red' '[WEB] '
                }
            }
            
            # Verify port is now free
            Start-Sleep -Seconds 2
            if(Test-PortAvailable $Port){
                Write-ColorLog "Port $Port is now available" 'Green' '[WEB] '
                return $true
            } else {
                Write-ColorLog "Port $Port is still in use after cleanup" 'Red' '[WEB] '
                return $false
            }
        } else {
            Write-ColorLog "No processes found using port $Port" 'Yellow' '[WEB] '
            return $true
        }
    } catch {
        Write-ColorLog "Port cleanup failed: $($_.Exception.Message)" 'Red' '[WEB] '
        return $false
    }
}

function Start-WebDashboard {
    Write-ColorLog 'Starting Web Dashboard...' 'Cyan' '[WEB] '
    
    # Check if port 5000 is available
    if(-not (Test-PortAvailable 5000)){
        Write-ColorLog 'Port 5000 is already in use' 'Yellow' '[WEB] '
        
        # Try to free the port
        if(-not (Clear-Port 5000)){
            Write-ColorLog 'Failed to free port 5000. Web Dashboard cannot start.' 'Red' '[WEB] '
            Write-ColorLog 'You may need to manually kill processes using port 5000' 'Yellow' '[WEB] '
            return $null
        }
    }
    
    # Check if Flask dependencies are installed
    $pythonExe='python'
    if(Test-Path 'venv\Scripts\python.exe'){
        $pythonExe='venv\Scripts\python.exe'
    }
    
    # Verify Flask is installed
    $flaskCheck = & $pythonExe -c "import flask, flask_socketio; print('ok')" 2>$null
    if($LASTEXITCODE -ne 0 -or $flaskCheck -ne 'ok'){
        Write-ColorLog 'Flask dependencies not installed, attempting to install...' 'Yellow' '[WEB] '
        $pipExe = $pythonExe -replace 'python\.exe$','pip.exe'
        if(Test-Path $pipExe){
            & $pipExe install -r requirements.txt 2>&1 | Out-Null
            if($LASTEXITCODE -ne 0){
                Write-ColorLog 'Failed to install Flask dependencies. Web Dashboard cannot start.' 'Red' '[WEB] '
                return $null
            }
        } else {
            Write-ColorLog 'pip not found. Cannot install dependencies.' 'Red' '[WEB] '
            return $null
        }
    }
    
    $webLog=$logFile -replace '\.log$','_web.log'
    $job=Start-Job -ScriptBlock {
        param($Python,$Root,$Log)
        Set-Location $Root
        & $Python -u web_dashboard.py 2>&1 | Tee-Object -FilePath $Log -Append
    } -ArgumentList $pythonExe,$PSScriptRoot,$webLog

    $maxTries=20
    for($i=0; $i -lt $maxTries; $i++){
        Start-Sleep 2
        try {
            $resp = Invoke-WebRequest -Uri 'http://127.0.0.1:5000/' -Method Head -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
            if($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500){
                Write-ColorLog 'Web Dashboard running at http://localhost:5000' 'Green' '[WEB] '
                return $job
            }
        } catch {
            try {
                $ok = Test-NetConnection -ComputerName 127.0.0.1 -Port 5000 -InformationLevel Quiet -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
                if($ok){
                    Write-ColorLog 'Web Dashboard TCP port open at http://localhost:5000' 'Green' '[WEB] '
                    return $job
                }
            } catch {}
        }

        if($job.State -in 'Failed','Stopped'){
            Write-ColorLog 'Web Dashboard process died during startup' 'Red' '[WEB] '
            
            # Check if it was due to port conflict
            if(Test-Path $webLog){
                $lastLines = Get-Content $webLog -Tail 20 -ErrorAction SilentlyContinue
                if($lastLines -match 'Port 5000 is already in use|Address already in use'){
                    Write-ColorLog 'Port 5000 conflict detected - attempting emergency cleanup...' 'Red' '[WEB] '
                    Clear-Port 5000
                }
                Write-ColorLog 'Last 10 lines from web dashboard log:' 'Yellow' '[WEB] '
                Get-Content $webLog -Tail 10 -ErrorAction SilentlyContinue | ForEach-Object { Write-Host "  | $_" }
            }
            
            Remove-Job $job -Force -ErrorAction SilentlyContinue
            return $null
        }
    }
    Write-ColorLog 'Web Dashboard start timeout' 'Yellow' '[WEB] '
    return $job
}

function Start-Bot {
    Write-ColorLog 'Starting bot...' 'Cyan' '[BOT] '
    Update-BotStatus 'Starting...'
    $pythonExe='python'
    if(Test-Path 'venv\Scripts\python.exe'){
        $pythonExe='venv\Scripts\python.exe'
    }
    $botErrFile = $botLogFile -replace '\.log$','_errors.log'
    
    # Use System.Diagnostics.Process for better control
    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $pythonExe
    $startInfo.Arguments = '-u bot.py'
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.WorkingDirectory = $PSScriptRoot
    
    # Create process
    $proc = New-Object System.Diagnostics.Process
    $proc.StartInfo = $startInfo
    $proc.EnableRaisingEvents = $true
    
    # Setup output redirection
    $script:botOutputFile = [System.IO.StreamWriter]::new($botLogFile, $true)
    $script:botErrorFile = [System.IO.StreamWriter]::new($botErrFile, $true)
    
    $proc.add_OutputDataReceived({
        param($sender, $e)
        if($e.Data -and $script:botOutputFile) {
            try {
                $script:botOutputFile.WriteLine($e.Data)
                $script:botOutputFile.Flush()
            } catch {}
        }
    })
    
    $proc.add_ErrorDataReceived({
        param($sender, $e)
        if($e.Data -and $script:botErrorFile) {
            try {
                $script:botErrorFile.WriteLine($e.Data)
                $script:botErrorFile.Flush()
            } catch {}
        }
    })
    
    [void]$proc.Start()
    $proc.BeginOutputReadLine()
    $proc.BeginErrorReadLine()
    
    Start-Sleep -Seconds 2
    Update-BotStatus 'Running' $proc.Id
    Write-ColorLog "Bot started (PID: $($proc.Id))" 'Green' '[BOT] '
    return $proc
}

function Test-ForUpdates {
    Write-ColorLog 'Checking for updates...' 'Gray' '[UPDATE] '
    try {
        git remote update 2>&1 | Out-Null
        $status=git status -uno
        if($status -like '*Your branch is behind*'){
            Write-ColorLog 'Updates available!' 'Yellow' '[UPDATE] '
            return $true
        }
        return $false
    } catch {
        Write-ColorLog "Update check failed: $($_.Exception.Message)" 'Red' '[UPDATE] '
        return $false
    }
}

function Invoke-Update {
    Write-ColorLog 'Applying updates...' 'Cyan' '[UPDATE] '
    Update-BotStatus 'Updating...'
    Invoke-GitCommit 'chore: Auto-commit before update'
    git fetch 2>&1 | Out-Null
    $changedFiles=git diff --name-only HEAD...origin/main
    if($changedFiles -like '*maintain_bot.ps1*' -or $changedFiles -like '*maintain_bot_fixed.ps1*'){
        Write-ColorLog 'Maintenance script updated; restarting...' 'Magenta' '[UPDATE] '
        git pull
        Invoke-Cleanup
        Start-Process powershell.exe -ArgumentList "-File `"$PSScriptRoot\maintain_bot.ps1`""
        Stop-Transcript
        exit 0
    }
    git pull
    Write-ColorLog 'Update complete' 'Green' '[UPDATE] '
    (Get-Date).ToUniversalTime().ToString('o') | Out-File -FilePath 'last_update.txt' -Encoding utf8
}

# ==================== MAIN LOOP ====================
Write-Host '=== Sulfur Discord Bot - Maintenance System v2.1 [Fixed] ===' -ForegroundColor Cyan
Write-Host ''
Write-ColorLog "Press 'Q' to shutdown" 'Yellow'
Write-Host ''

if(-not $SkipDatabaseBackup){
    Invoke-DatabaseBackup
}

try {
    $script:webDashboardJob=Start-WebDashboard
    if(-not $script:webDashboardJob){
        Write-ColorLog 'Warning: Web Dashboard failed to start' 'Yellow'
    }
} catch {
    Write-ColorLog "Warning: Web Dashboard startup error: $($_.Exception.Message)" 'Yellow'
    $script:webDashboardJob = $null
}

# Web dashboard restart tracking
$webRestartCount = 0
$webRestartThreshold = 3
$webRestartCooldown = 30  # seconds
$lastWebRestart = $null

$check=0
$updateEvery=60
$backupEvery=1800
$commitEvery=300
$consecutiveQuickCrashes=0
$quickCrashSeconds=10
$quickCrashThreshold=5

while($true){
    if(-not (Test-Preflight)){
        Write-ColorLog "Preflight failed. Fix issues above, then press Enter to retry..." 'Yellow'
        Read-Host | Out-Null
        continue
    }

    try {
        $script:botProcess=Start-Bot
    } catch {
        Write-ColorLog "Failed to start bot: $($_.Exception.Message)" 'Red'
        Write-ColorLog "Waiting 10 seconds before retry..." 'Yellow'
        Start-Sleep 10
        continue
    }
    
    if(-not $script:botProcess) {
        Write-ColorLog "Bot process not created, retrying in 10 seconds..." 'Yellow'
        Start-Sleep 10
        continue
    }
    
    $botStartTime = Get-Date
    
    while($script:botProcess -and -not $script:botProcess.HasExited){
        Start-Sleep 1
        $check++
        
        try {
            if([Console]::KeyAvailable){
                $key=[Console]::ReadKey($true)
                if($key.Key -eq 'Q'){
                    Write-ColorLog 'Shutdown requested' 'Yellow'
                    Invoke-Cleanup
                    Invoke-DatabaseBackup
                    Invoke-GitCommit 'chore: Auto-commit on shutdown'
                    Update-BotStatus 'Shutdown'
                    Stop-Transcript
                    exit 0
                }
            }
        } catch {}
        
        if(Test-Path (Join-Path $PSScriptRoot 'stop.flag')){
            Write-ColorLog 'Stop flag detected' 'Yellow'
            Remove-Item (Join-Path $PSScriptRoot 'stop.flag') -ErrorAction SilentlyContinue
            Invoke-Cleanup
            Invoke-DatabaseBackup
            Invoke-GitCommit 'chore: Auto-commit on stop'
            Update-BotStatus 'Shutdown'
            Stop-Transcript
            exit 0
        }
        
        if(Test-Path (Join-Path $PSScriptRoot 'restart.flag')){
            Write-ColorLog 'Restart flag detected' 'Yellow'
            Remove-Item (Join-Path $PSScriptRoot 'restart.flag') -ErrorAction SilentlyContinue
            
            # Close file handles first
            if($script:botOutputFile) {
                try {
                    $script:botOutputFile.Close()
                    $script:botOutputFile.Dispose()
                } catch {}
                $script:botOutputFile = $null
            }
            if($script:botErrorFile) {
                try {
                    $script:botErrorFile.Close()
                    $script:botErrorFile.Dispose()
                } catch {}
                $script:botErrorFile = $null
            }
            
            # Kill process
            if($script:botProcess -and -not $script:botProcess.HasExited){
                try {
                    $script:botProcess.Kill()
                    $script:botProcess.WaitForExit(3000)
                } catch {
                    Stop-Process -Id $script:botProcess.Id -Force -ErrorAction SilentlyContinue
                }
            }
            break
        }
        
        if($check % $commitEvery -eq 0){
            Invoke-GitCommit 'chore: Auto-commit database changes'
        }
        
        if($check % $backupEvery -eq 0){
            Invoke-DatabaseBackup
        }
        
        if($check % $updateEvery -eq 0){
            (Get-Date).ToUniversalTime().ToString('o') | Out-File -FilePath 'last_check.txt' -Encoding utf8
            if(Test-ForUpdates){
                Write-ColorLog 'Stopping bot for update...' 'Yellow' '[UPDATE] '
                Invoke-Cleanup
                Invoke-Update
                break
            }
        }
        
        if($script:webDashboardJob -and (Get-Job -Id $script:webDashboardJob.Id -ErrorAction SilentlyContinue) -and $script:webDashboardJob.State -ne 'Running'){
            $currentTime = Get-Date
            
            # Calculate time since last restart
            if($lastWebRestart){
                $timeSinceLastRestart = [int]($currentTime - $lastWebRestart).TotalSeconds
            } else {
                $timeSinceLastRestart = 999999  # Large number for first time
            }
            
            # Check if we've hit the restart threshold
            if($webRestartCount -ge $webRestartThreshold){
                if($timeSinceLastRestart -lt 300){
                    # Multiple restarts in 5 minutes - something is wrong
                    Write-ColorLog "Web Dashboard has crashed $webRestartCount times. Giving up on auto-restart." 'Red' '[WEB] '
                    Write-ColorLog "Please check the web dashboard logs for errors and fix the issue manually." 'Yellow' '[WEB] '
                    $webRestartCount++  # Increment to prevent further attempts
                } else {
                    # It's been a while, reset the counter
                    Write-ColorLog "Resetting web dashboard restart counter (last restart was ${timeSinceLastRestart}s ago)" 'Yellow' '[WEB] '
                    $webRestartCount = 0
                }
            }
            
            # Only try to restart if under threshold and cooldown has passed
            if($webRestartCount -lt $webRestartThreshold){
                if($timeSinceLastRestart -ge $webRestartCooldown){
                    Write-ColorLog "Web Dashboard stopped, restarting... (attempt $($webRestartCount + 1)/$webRestartThreshold)" 'Yellow' '[WEB] '
                    
                    $lastWebRestart = $currentTime
                    $webRestartCount++
                    
                    # Clean up the old job
                    Remove-Job $script:webDashboardJob -Force -ErrorAction SilentlyContinue
                    
                    # Try to restart
                    $script:webDashboardJob = Start-WebDashboard
                    if($script:webDashboardJob){
                        Write-ColorLog 'Web Dashboard restarted successfully' 'Green' '[WEB] '
                        $webRestartCount = 0  # Reset counter on success
                    } else {
                        Write-ColorLog 'Failed to restart Web Dashboard' 'Red' '[WEB] '
                    }
                } else {
                    $waitTime = $webRestartCooldown - $timeSinceLastRestart
                    Write-ColorLog "Web Dashboard stopped, but waiting ${waitTime}s before retry (cooldown period)" 'Yellow' '[WEB] '
                }
            }
        }
    }
    
    Update-BotStatus 'Stopped'
    $botStopTime = Get-Date
    $runSeconds = [int]($botStopTime - $botStartTime).TotalSeconds
    if($runSeconds -lt $quickCrashSeconds){
        $consecutiveQuickCrashes++
    } else {
        $consecutiveQuickCrashes=0
    }

    if($consecutiveQuickCrashes -ge $quickCrashThreshold){
        Write-ColorLog "Bot is crashing quickly ($consecutiveQuickCrashes times). Pausing restarts." 'Red'
        Write-ColorLog "Showing last 50 lines of bot log to help debug:" 'Yellow'
        try{
            if(Test-Path $botLogFile){
                Get-Content $botLogFile -Tail 50 | ForEach-Object { Write-Host $_ }
            }
            $errFile = $botLogFile -replace '\.log$','_errors.log'
            if(Test-Path $errFile){
                Write-ColorLog "--- stderr (last 50) ---" 'Gray'
                Get-Content $errFile -Tail 50 | ForEach-Object { Write-Host $_ }
            }
        } catch {}
        Write-ColorLog "Fix the configuration (e.g., token in .env), then press Enter to retry." 'Yellow'
        Read-Host | Out-Null
        $consecutiveQuickCrashes=0
        continue
    }

    Write-ColorLog 'Bot stopped; restarting in 5s...' 'Yellow'
    Start-Sleep 5
}
