# ==============================================================================
# Sulfur Bot - Maintenance Script (Refactored Minimal)
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
trap {
    Write-Host 'Script terminated. Cleaning up...' -ForegroundColor Red
    if($script:botProcess){
        Stop-Process -Id $script:botProcess.Id -Force -ErrorAction SilentlyContinue
    }
    if($script:webDashboardJob){
        Stop-Job $script:webDashboardJob -ErrorAction SilentlyContinue
        Remove-Job $script:webDashboardJob -Force -ErrorAction SilentlyContinue
    }
    Update-BotStatus 'Shutdown'
    Stop-Transcript
    exit 0
}

function Write-ColorLog {
    param([string]$Message,[string]$Color='White',[string]$Prefix='')
    $t=Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    Write-Host "[$t] $Prefix$Message" -ForegroundColor $Color
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
        # Try mariadb-dump first, then mysqldump
        $dumpCmd=$null
        if(Get-Command mariadb-dump -ErrorAction SilentlyContinue){
            $dumpCmd='mariadb-dump'
        }elseif(Get-Command mysqldump -ErrorAction SilentlyContinue){
            $dumpCmd='mysqldump'
        }
        
        $user=$env:DB_USER
        if(-not $user){$user='sulfur_bot_user'}
        $pass=$env:DB_PASS
        if(-not $pass){$pass=''}
        $db=$env:DB_NAME
        if(-not $db){$db='sulfur_bot'}
        $backupDir=Join-Path $PSScriptRoot 'backups'
        if(-not(Test-Path $backupDir)){New-Item -ItemType Directory -Path $backupDir|Out-Null}
        $backupFile=Join-Path $backupDir "sulfur_bot_backup_$(Get-Date -Format 'yyyy-MM-dd_HH-mm-ss').sql"
        $syncFile=Join-Path $PSScriptRoot 'config\database_sync.sql'
        
        if($dumpCmd){
            if($pass){
                & $dumpCmd -u $user -p$pass $db > $backupFile 2>$null
                & $dumpCmd -u $user -p$pass $db > $syncFile 2>$null
            } else {
                & $dumpCmd -u $user $db > $backupFile 2>$null
                & $dumpCmd -u $user $db > $syncFile 2>$null
            }
        } else {
            'mysqldump/mariadb-dump not found; placeholder backup entry.' | Out-File -FilePath $backupFile
        }
        if(Test-Path $backupFile){
            $fileSize=(Get-Item $backupFile).Length
            if($fileSize -gt 500){
                Write-ColorLog "Backup created: $backupFile ($fileSize bytes)" 'Green' '[DB] '
                Write-ColorLog "Sync file updated: $syncFile" 'Green' '[DB] '
            } else {
                Write-ColorLog "Backup failed (file too small: $fileSize bytes)" 'Red' '[DB] '
                return $false
            }
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
        Write-ColorLog "Backup error: $_" 'Red' '[DB] '
        return $false
    }
}

function Invoke-GitCommit {
    param([string]$Message='chore: Auto-commit from maintenance script')
    Write-ColorLog 'Checking for changes...' 'Cyan' '[GIT] '
    $hasChanges=$false
    $syncFile='config\database_sync.sql'
    
    # Check if database sync file exists and has changes
    if(Test-Path $syncFile){
        $gitStatus=git status --porcelain $syncFile 2>$null
        if($gitStatus){
            $hasChanges=$true
            Write-ColorLog 'Database sync file has changes' 'Cyan' '[GIT] '
        }
    }
    
    # Check for any other changes
    $allStatus=git status --porcelain 2>$null
    if($allStatus){
        $hasChanges=$true
    }
    
    if($hasChanges){
        Write-ColorLog 'Changes detected, committing...' 'Yellow' '[GIT] '
        try {
            git add -A 2>&1 | Out-Null
            git commit -m $Message 2>&1 | Out-Null
            if($LASTEXITCODE -eq 0){
                git push 2>&1 | Out-Null
                if($LASTEXITCODE -eq 0){
                    Write-ColorLog 'Changes committed & pushed' 'Green' '[GIT] '
                    return $true
                } else {
                    Write-ColorLog 'Git push failed' 'Red' '[GIT] '
                    return $false
                }
            } else {
                Write-ColorLog 'Git commit failed (no changes or error)' 'Yellow' '[GIT] '
                return $false
            }
        } catch {
            Write-ColorLog "Git operation failed: $_" 'Red' '[GIT] '
            return $false
        }
    } else {
        Write-ColorLog 'No changes to commit' 'Gray' '[GIT] '
        return $false
    }
}

function Start-WebDashboard {
    Write-ColorLog 'Starting Web Dashboard...' 'Cyan' '[WEB] '
    $pythonExe='python'
    if(Test-Path 'venv\Scripts\python.exe'){
        $pythonExe='venv\Scripts\python.exe'
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
            # Prefer an HTTP HEAD check to avoid ping dependency or ICMP issues
            $resp = Invoke-WebRequest -Uri 'http://127.0.0.1:5000/' -Method Head -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
            if($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500){
                Write-ColorLog 'Web Dashboard running at http://localhost:5000' 'Green' '[WEB] '
                return $job
            }
        } catch {
            # Fallback to a quick TCP probe
            try {
                $ok = Test-NetConnection -ComputerName 127.0.0.1 -Port 5000 -InformationLevel Quiet -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
                if($ok){
                    Write-ColorLog 'Web Dashboard TCP port open at http://localhost:5000' 'Green' '[WEB] '
                    return $job
                }
            } catch {}
        }

        if($job.State -in 'Failed','Stopped'){
            Write-ColorLog 'Web Dashboard failed to start' 'Red' '[WEB] '
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
    # Use Start-Process without output redirection to avoid process detachment issues
    # The bot will write to its own log files via the logger_utils module
    $proc=Start-Process -FilePath $pythonExe -ArgumentList @('-u','bot.py') -PassThru -WindowStyle Hidden
    Start-Sleep -Seconds 2 # Give the process time to start
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
        Write-ColorLog "Update check failed: $_" 'Red' '[UPDATE] '
        return $false
    }
}

function Invoke-Update {
    Write-ColorLog 'Applying updates...' 'Cyan' '[UPDATE] '
    Update-BotStatus 'Updating...'
    Invoke-GitCommit 'chore: Auto-commit before update'
    git fetch 2>&1 | Out-Null
    $changedFiles=git diff --name-only HEAD...origin/main
    if($changedFiles -like '*maintain_bot.ps1*'){
        Write-ColorLog 'Maintenance script updated; restarting...' 'Magenta' '[UPDATE] '
        git pull
        if($script:webDashboardJob){
            Stop-Job $script:webDashboardJob -ErrorAction SilentlyContinue
            Remove-Job $script:webDashboardJob -Force -ErrorAction SilentlyContinue
        }
        Start-Process powershell.exe -ArgumentList "-File `"$PSScriptRoot\maintain_bot.ps1`""
        Stop-Transcript
        exit 0
    }
    git pull
    Write-ColorLog 'Update complete' 'Green' '[UPDATE] '
    (Get-Date).ToUniversalTime().ToString('o') | Out-File -FilePath 'last_update.txt' -Encoding utf8
}

# ==================== MAIN LOOP ====================
Write-Host '╔════════════════════════════════════════════════════════════╗' -ForegroundColor Cyan
Write-Host '║       Sulfur Discord Bot - Maintenance System v2.0        ║' -ForegroundColor Cyan
Write-Host '╚════════════════════════════════════════════════════════════╝' -ForegroundColor Cyan
Write-Host ''
Write-ColorLog "Press 'Q' to shutdown" 'Yellow'
Write-Host ''

if(-not $SkipDatabaseBackup){
    Invoke-DatabaseBackup
}

$script:webDashboardJob=Start-WebDashboard
if(-not $script:webDashboardJob){
    Write-ColorLog 'Warning: Web Dashboard failed to start' 'Yellow'
}

$check=0
$updateEvery=60
$backupEvery=1800
$commitEvery=300

while($true){
    $script:botProcess=Start-Bot
    while($script:botProcess -and (Get-Process -Id $script:botProcess.Id -ErrorAction SilentlyContinue)){
        Start-Sleep 1
        $check++
        
        try {
            if([Console]::KeyAvailable){
                $key=[Console]::ReadKey($true)
                if($key.Key -eq 'Q'){
                    Write-ColorLog 'Shutdown requested' 'Yellow'
                    Stop-Process -Id $script:botProcess.Id -Force
                    Start-Sleep 2
                    Invoke-DatabaseBackup
                    Invoke-GitCommit 'chore: Auto-commit on shutdown'
                    Update-BotStatus 'Shutdown'
                    if($script:webDashboardJob){
                        Stop-Job $script:webDashboardJob -ErrorAction SilentlyContinue
                        Remove-Job $script:webDashboardJob -Force -ErrorAction SilentlyContinue
                    }
                    Stop-Transcript
                    exit 0
                }
            }
        } catch {
            # Ignore console access errors when running in background
        }
        
        if(Test-Path 'stop.flag'){
            Write-ColorLog 'Stop flag detected' 'Yellow'
            Remove-Item 'stop.flag' -ErrorAction SilentlyContinue
            Stop-Process -Id $script:botProcess.Id -Force
            Start-Sleep 2
            Invoke-DatabaseBackup
            Invoke-GitCommit 'chore: Auto-commit on stop'
            Update-BotStatus 'Shutdown'
            if($script:webDashboardJob){
                Stop-Job $script:webDashboardJob -ErrorAction SilentlyContinue
                Remove-Job $script:webDashboardJob -Force -ErrorAction SilentlyContinue
            }
            Stop-Transcript
            exit 0
        }
        
        if(Test-Path 'restart.flag'){
            Write-ColorLog 'Restart flag detected' 'Yellow'
            Remove-Item 'restart.flag' -ErrorAction SilentlyContinue
            Stop-Process -Id $script:botProcess.Id -Force
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
                Stop-Process -Id $script:botProcess.Id -Force
                Start-Sleep 2
                Invoke-Update
                break
            }
        }
        
        if($script:webDashboardJob -and $script:webDashboardJob.State -ne 'Running'){
            Write-ColorLog 'Web Dashboard stopped; restarting...' 'Yellow' '[WEB] '
            $script:webDashboardJob=Start-WebDashboard
        }
    }
    
    Update-BotStatus 'Stopped'
    Write-ColorLog 'Bot stopped; restarting in 5s...' 'Yellow'
    Start-Sleep 5
}
