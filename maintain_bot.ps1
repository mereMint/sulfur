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
    Invoke-Cleanup
    Update-BotStatus 'Shutdown'
    Write-Host 'Cleanup complete.' -ForegroundColor Green
    Stop-Transcript
    exit 0
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
        Write-ColorLog "Preflight check failed: $_" 'Red'
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
        Write-ColorLog "Backup error: $_" 'Red' '[DB] '
        return $false
    }
}

function Invoke-GitCommit {
    param([string]$Message='chore: Auto-commit from maintenance script')
    Write-ColorLog 'Checking for changes...' 'Cyan' '[GIT] '
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
        try {
            git add -A
            git commit -m $Message
            git push
            Write-ColorLog 'Changes committed & pushed' 'Green' '[GIT] '
            return $true
        } catch {
            Write-ColorLog "Git commit failed: $_" 'Red' '[GIT] '
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
Write-Host '╔════════════════════════════════════════════════════════════╗' -ForegroundColor Cyan
Write-Host '║    Sulfur Discord Bot - Maintenance System v2.1 (Fixed)   ║' -ForegroundColor Cyan
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
$consecutiveQuickCrashes=0
$quickCrashSeconds=10
$quickCrashThreshold=5

while($true){
    if(-not (Test-Preflight)){
        Write-ColorLog "Preflight failed. Fix issues above, then press Enter to retry..." 'Yellow'
        Read-Host | Out-Null
        continue
    }

    $script:botProcess=Start-Bot
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
        
        if(Test-Path 'stop.flag'){
            Write-ColorLog 'Stop flag detected' 'Yellow'
            Remove-Item 'stop.flag' -ErrorAction SilentlyContinue
            Invoke-Cleanup
            Invoke-DatabaseBackup
            Invoke-GitCommit 'chore: Auto-commit on stop'
            Update-BotStatus 'Shutdown'
            Stop-Transcript
            exit 0
        }
        
        if(Test-Path 'restart.flag'){
            Write-ColorLog 'Restart flag detected' 'Yellow'
            Remove-Item 'restart.flag' -ErrorAction SilentlyContinue
            
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
        
        if($script:webDashboardJob -and $script:webDashboardJob.State -ne 'Running'){
            Write-ColorLog 'Web Dashboard stopped; restarting...' 'Yellow' '[WEB] '
            $script:webDashboardJob=Start-WebDashboard
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
