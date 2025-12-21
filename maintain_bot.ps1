# ==============================================================================
# Sulfur Bot - Maintenance Script (Fixed Process Management)
# ==============================================================================
# PUBLIC REPO MODE (Default):
# - SkipCommit=true (no auto-commits)
# - Local changes are DISCARDED on updates
# - Always uses remote files (git reset --hard)
# - No merge conflicts
#
# To enable legacy commit mode: run with -EnableCommit flag
# ==============================================================================
param(
    [switch]$SkipDatabaseBackup,
    [switch]$EnableCommit
)

# Default to skip commits (public repo mode)
$script:SkipCommit = -not $EnableCommit
$ErrorActionPreference='Continue'
$statusFile=Join-Path $PSScriptRoot 'config\bot_status.json'
$logDir=Join-Path $PSScriptRoot 'logs'
if(-not(Test-Path $logDir)){New-Item -ItemType Directory -Path $logDir|Out-Null}
$ts=Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'
$logFile=Join-Path $logDir "maintenance_$ts.log"
$botLogFile=Join-Path $logDir "bot_$ts.log"
Start-Transcript -Path $logFile -Append | Out-Null

# Update loop prevention
$script:lastPulledCommit = ""
$script:updateLoopCount = 0
$script:maxUpdateLoopCount = 3
$script:updateLoopResetSeconds = 300  # 5 minutes
$script:lastUpdateTime = [datetime]::MinValue

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
                # Try graceful shutdown first (SIGTERM equivalent)
                $script:botProcess.Kill($false)  # Don't force entire process tree
                if(-not $script:botProcess.WaitForExit(5000)){
                    # If still running after 5 seconds, force kill
                    Write-Host "Bot didn't stop gracefully, force killing..." -ForegroundColor Yellow
                    $script:botProcess.Kill($true)  # Force entire process tree
                    $script:botProcess.WaitForExit(2000)
                }
            } catch {
                # Fallback to Stop-Process
                Write-Host "Using Stop-Process as fallback..." -ForegroundColor Yellow
                Stop-Process -Id $script:botProcess.Id -Force -ErrorAction SilentlyContinue
            }
        }
        try { $script:botProcess.Close() } catch {}
        $script:botProcess = $null
    }
    
    # Also search for any bot.py processes that might have escaped
    $botProcesses = Get-Process -Name python* -ErrorAction SilentlyContinue | Where-Object {
        try {
            $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)" -ErrorAction SilentlyContinue).CommandLine
            $cmdLine -and ($cmdLine -like "*bot.py*")
        } catch {
            $false
        }
    }
    
    if($botProcesses){
        Write-Host "Found $($botProcesses.Count) orphaned bot process(es) to kill..." -ForegroundColor Yellow
        $botProcesses | ForEach-Object {
            try {
                Write-Host "  Killing orphaned bot PID: $($_.Id)" -ForegroundColor Yellow
                $_.Kill()
                $_.WaitForExit(2000)
            } catch {
                Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
            }
        }
    }
    
    # Stop web dashboard
    if($script:webDashboardJob){
        Write-Host 'Stopping Web Dashboard...' -ForegroundColor Yellow
        
        # First, try to kill any Python processes running web_dashboard.py
        $webProcesses = Get-Process -Name python* -ErrorAction SilentlyContinue | Where-Object {
            try {
                $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)" -ErrorAction SilentlyContinue).CommandLine
                $cmdLine -and ($cmdLine -like "*web_dashboard.py*")
            } catch {
                $false
            }
        }
        
        if($webProcesses){
            Write-Host "Found $($webProcesses.Count) web dashboard process(es) to kill..." -ForegroundColor Yellow
            $webProcesses | ForEach-Object {
                try {
                    Write-Host "  Killing web dashboard PID: $($_.Id)" -ForegroundColor Yellow
                    $_.Kill()
                    $_.WaitForExit(3000)
                } catch {
                    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
                }
            }
        }
        
        # Then stop the PowerShell job
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
    
    # Remove bot instance lock file to prevent "Secondary Instance" issues
    $lockFile = Join-Path $PSScriptRoot 'bot_instance.lock'
    if(Test-Path $lockFile){
        try {
            Remove-Item $lockFile -Force -ErrorAction Stop
            Write-Host "Removed bot instance lock file" -ForegroundColor Green
        } catch {
            Write-Host "Warning: Could not remove bot instance lock file: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }
}

# Register cleanup handler for Ctrl+C and script termination
# Only trap terminating errors, not all errors
trap {
    # Check if this is actually a terminating error
    if ($_.Exception -is [System.Management.Automation.PipelineStoppedException]) {
        # This is Ctrl+C or similar - run cleanup
        Write-Host 'Script interrupted. Running cleanup...' -ForegroundColor Red
        Invoke-Cleanup
        Update-BotStatus 'Shutdown'
        Write-Host 'Cleanup complete.' -ForegroundColor Green
        Stop-Transcript
        exit 1
    }
    elseif ($Error[0].CategoryInfo.Category -eq 'OperationStopped') {
        # Pipeline stopped - run cleanup
        Write-Host 'Script stopped. Running cleanup...' -ForegroundColor Red
        Invoke-Cleanup
        Update-BotStatus 'Shutdown'
        Write-Host 'Cleanup complete.' -ForegroundColor Green
        Stop-Transcript
        exit 1
    }
    else {
        # Non-terminating error - just log it and continue
        if ($_) {
            try {
                Write-Host ("Non-terminating error: {0}" -f ($_.Exception.Message)) -ForegroundColor Yellow
            } catch {}
        }
        # Don't call cleanup - let the script continue
        continue
    }
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

function Test-OptionalApiKeys {
    Write-ColorLog 'Checking optional API keys...' 'Cyan' '[CONFIG] '
    
    $envPath = Join-Path $PSScriptRoot '.env'
    if(-not (Test-Path $envPath)){
        return
    }
    
    $warnings = 0
    $envLines = Get-Content -Path $envPath -ErrorAction SilentlyContinue
    
    # Helper function to extract key value
    function Get-EnvValue {
        param([string]$KeyName)
        $line = $envLines | Where-Object { $_ -match "^\s*$KeyName\s*=" } | Select-Object -First 1
        if($line){
            return ($line -replace '^[^=]*=','').Trim().Trim('"','''')
        }
        return $null
    }
    
    # Check for GEMINI_API_KEY or OPENAI_API_KEY (at least one is needed for AI)
    $geminiKey = Get-EnvValue 'GEMINI_API_KEY'
    $openaiKey = Get-EnvValue 'OPENAI_API_KEY'
    
    $geminiValid = -not [string]::IsNullOrWhiteSpace($geminiKey) -and $geminiKey -ne 'your_gemini_api_key_here'
    $openaiValid = -not [string]::IsNullOrWhiteSpace($openaiKey) -and $openaiKey -ne 'your_openai_api_key_here'
    
    if(-not $geminiValid -and -not $openaiValid){
        Write-ColorLog "No AI API key configured (GEMINI_API_KEY or OPENAI_API_KEY)" 'Yellow' '[CONFIG] '
        Write-ColorLog "AI chat features will not work without an API key" 'Yellow' '[CONFIG] '
        Write-ColorLog "  Get a free Gemini key: https://aistudio.google.com/apikey" 'White' '[CONFIG] '
        $warnings++
    }
    
    # Check for LASTFM_API_KEY (optional, for enhanced music features)
    $lastfmKey = Get-EnvValue 'LASTFM_API_KEY'
    $lastfmValid = -not [string]::IsNullOrWhiteSpace($lastfmKey) -and $lastfmKey -ne 'your_lastfm_api_key_here'
    
    if(-not $lastfmValid){
        Write-ColorLog "LASTFM_API_KEY not configured (optional)" 'White' '[CONFIG] '
        Write-ColorLog "  Last.fm API enhances music recommendations and Songle song variety" 'White' '[CONFIG] '
        Write-ColorLog "  Get a free key: https://www.last.fm/api/account/create" 'White' '[CONFIG] '
    } else {
        Write-ColorLog "LASTFM_API_KEY is configured" 'Green' '[CONFIG] '
    }
    
    # Check for FOOTBALL_DATA_API_KEY (optional, for sports betting)
    $footballKey = Get-EnvValue 'FOOTBALL_DATA_API_KEY'
    $footballValid = -not [string]::IsNullOrWhiteSpace($footballKey) -and $footballKey -ne 'your_football_data_api_key_here'
    
    if(-not $footballValid){
        Write-ColorLog "FOOTBALL_DATA_API_KEY not configured (optional)" 'White' '[CONFIG] '
        Write-ColorLog "  Required for international league betting (Premier League, La Liga, etc.)" 'White' '[CONFIG] '
        Write-ColorLog "  German leagues work without this key (via OpenLigaDB)" 'White' '[CONFIG] '
    } else {
        Write-ColorLog "FOOTBALL_DATA_API_KEY is configured" 'Green' '[CONFIG] '
    }
    
    if($warnings -gt 0){
        Write-ColorLog "Some features may be limited. Configure API keys in .env or via the web dashboard" 'Yellow' '[CONFIG] '
        Write-ColorLog "Web dashboard: http://localhost:5000/api_keys" 'White' '[CONFIG] '
    }
}

function Test-JavaVersion {
    Write-ColorLog 'Checking Java 21 for Minecraft support...' 'Cyan' '[JAVA] '
    
    try {
        $javaVersion = java -version 2>&1 | Out-String
        if ($javaVersion -match "version `"?(\d+)") {
            $javaMajor = [int]$matches[1]
            if ($javaMajor -ge 21) {
                Write-ColorLog "Java $javaMajor is installed" 'Green' '[JAVA] '
                return $true
            } else {
                Write-ColorLog "Java $javaMajor found - Java 21 recommended for Minecraft 1.21+" 'Yellow' '[JAVA] '
                Write-ColorLog "Download from: https://adoptium.net/temurin/releases/?version=21" 'White' '[JAVA] '
                return $true  # Still allow bot to run
            }
        }
    } catch {
        Write-ColorLog "Java not found (optional for Minecraft server)" 'Yellow' '[JAVA] '
        Write-ColorLog "Install Java 21 for Minecraft: https://adoptium.net/temurin/releases/?version=21" 'White' '[JAVA] '
    }
    return $false
}

function Test-FFmpegInstallation {
    Write-ColorLog 'Checking FFmpeg installation...' 'Cyan' '[FFMPEG] '
    try {
        $ffmpegVersion = ffmpeg -version 2>&1 | Select-Object -First 1
        if ($ffmpegVersion) {
            Write-ColorLog "FFmpeg is installed: $ffmpegVersion" 'Green' '[FFMPEG] '
            return $true
        }
    } catch {
        Write-ColorLog "FFmpeg not found" 'Yellow' '[FFMPEG] '
        Write-ColorLog "FFmpeg is required for music/audio features" 'White' '[FFMPEG] '
        Write-ColorLog "Download from: https://ffmpeg.org/download.html" 'White' '[FFMPEG] '
        Write-ColorLog "Or use winget: winget install FFmpeg.FFmpeg" 'White' '[FFMPEG] '
        return $false
    }
    return $false
}

function Update-BotStatus {
    param([string]$Status,[int]$BotProcessId=0)
    $statusData=@{status=$Status;timestamp=(Get-Date).ToUniversalTime().ToString('o')}
    if($BotProcessId -gt 0){$statusData.pid=$BotProcessId}
    [IO.File]::WriteAllText($statusFile,($statusData|ConvertTo-Json -Compress),[Text.UTF8Encoding]::new($false))
}

function Test-DatabaseServer {
    Write-ColorLog 'Checking database server status...' 'Cyan' '[DB] '
    
    # Find MySQL/MariaDB client
    $mysqlCmd = $null
    if (Get-Command mysql -ErrorAction SilentlyContinue) {
        $mysqlCmd = 'mysql'
    } elseif (Get-Command mariadb -ErrorAction SilentlyContinue) {
        $mysqlCmd = 'mariadb'
    } else {
        Write-ColorLog 'MySQL/MariaDB client not found' 'Red' '[DB] '
        return $false
    }
    
    # Test connection
    $user = $env:DB_USER
    if (-not $user) { $user = 'sulfur_bot_user' }
    $pass = $env:DB_PASS
    
    try {
        if ($pass) {
            $testResult = & $mysqlCmd -u $user -p"$pass" -e "SELECT 1;" 2>&1
        } else {
            $testResult = & $mysqlCmd -u $user -e "SELECT 1;" 2>&1
        }
        
        if ($LASTEXITCODE -eq 0) {
            Write-ColorLog 'Database server is running and accessible' 'Green' '[DB] '
            return $true
        }
    } catch {
        # Connection failed
    }
    
    Write-ColorLog 'Database server is not accessible' 'Yellow' '[DB] '
    return $false
}

function Start-DatabaseServer {
    Write-ColorLog 'Attempting to start database server...' 'Cyan' '[DB] '
    
    # Check if MySQL service exists and try to start it
    $mysqlService = Get-Service -Name 'MySQL*' -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($mysqlService) {
        if ($mysqlService.Status -eq 'Running') {
            Write-ColorLog 'MySQL service is already running' 'Green' '[DB] '
            return $true
        }
        
        try {
            Write-ColorLog "Starting $($mysqlService.Name) service..." 'Cyan' '[DB] '
            Start-Service $mysqlService.Name -ErrorAction Stop
            Start-Sleep -Seconds 2
            
            $mysqlService.Refresh()
            if ($mysqlService.Status -eq 'Running') {
                Write-ColorLog 'MySQL service started successfully' 'Green' '[DB] '
                return $true
            }
        } catch {
            Write-ColorLog "Failed to start MySQL service: $($_.Exception.Message)" 'Yellow' '[DB] '
        }
    }
    
    # Try MariaDB service
    $mariadbService = Get-Service -Name 'MariaDB*' -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($mariadbService) {
        if ($mariadbService.Status -eq 'Running') {
            Write-ColorLog 'MariaDB service is already running' 'Green' '[DB] '
            return $true
        }
        
        try {
            Write-ColorLog "Starting $($mariadbService.Name) service..." 'Cyan' '[DB] '
            Start-Service $mariadbService.Name -ErrorAction Stop
            Start-Sleep -Seconds 2
            
            $mariadbService.Refresh()
            if ($mariadbService.Status -eq 'Running') {
                Write-ColorLog 'MariaDB service started successfully' 'Green' '[DB] '
                return $true
            }
        } catch {
            Write-ColorLog "Failed to start MariaDB service: $($_.Exception.Message)" 'Yellow' '[DB] '
        }
    }
    
    Write-ColorLog 'Failed to start database server' 'Red' '[DB] '
    Write-ColorLog 'Please start the database server manually:' 'Yellow' '[DB] '
    Write-ColorLog '  - Start-Service MySQL80 (or your MySQL/MariaDB service name)' 'White' '[DB] '
    Write-ColorLog '  - Or use MySQL Workbench or similar GUI tool' 'White' '[DB] '
    return $false
}

function Start-DatabaseServerIfNeeded {
    Write-ColorLog 'Ensuring database server is running...' 'Cyan' '[DB] '
    
    # First check if it's already running
    if (Test-DatabaseServer) {
        return $true
    }
    
    # If not running, try to start it
    Write-ColorLog 'Database server is not running, attempting to start...' 'Yellow' '[DB] '
    if (Start-DatabaseServer) {
        # Verify it's now accessible
        Start-Sleep -Seconds 1
        if (Test-DatabaseServer) {
            Write-ColorLog 'Database server started and verified' 'Green' '[DB] '
            return $true
        }
    }
    
    Write-ColorLog 'Could not ensure database server is running' 'Red' '[DB] '
    Write-ColorLog 'Bot may experience database connection issues' 'Yellow' '[DB] '
    return $false
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
        $pass=$env:DB_PASS
        
        $backupDir=Join-Path $PSScriptRoot 'backups'
        if(-not(Test-Path $backupDir)){New-Item -ItemType Directory -Path $backupDir|Out-Null}
        $backupFile=Join-Path $backupDir "sulfur_bot_backup_$(Get-Date -Format 'yyyy-MM-dd_HH-mm-ss').sql"
        
        if($dumpCmd){
            # Check if password is actually set (not empty or whitespace)
            if([string]::IsNullOrWhiteSpace($pass)){
                # No password - try without password
                & $dumpCmd -u $user $db > $backupFile 2>$null
            } else {
                # Has password - use it
                & $dumpCmd -u $user -p$pass $db > $backupFile 2>$null
            }
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
            Write-ColorLog 'Note: If the database user has no password, backups can be created manually' 'Yellow' '[DB] '
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
            
            foreach($procId in $pids){
                try {
                    $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
                    if($proc){
                        Write-ColorLog "Stopping process $procId ($($proc.ProcessName))..." 'Yellow' '[WEB] '
                        Stop-Process -Id $procId -Force -ErrorAction Stop
                        Start-Sleep -Seconds 2
                    }
                } catch {
                    Write-ColorLog "Failed to stop process ${procId}: $($_.Exception.Message)" 'Red' '[WEB] '
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

# ==============================================================================
# Database Migration and Dependency Functions
# ==============================================================================

function Run-DatabaseMigrations {
    Write-ColorLog 'Checking for pending database migrations...' 'Cyan' '[DB] '
    
    if(-not (Test-Path 'scripts\db_migrations')){
        Write-ColorLog 'No migrations directory found, skipping' 'Yellow' '[DB] '
        return
    }
    
    # Get MySQL command
    $mysqlCmd = $null
    if(Get-Command mysql -ErrorAction SilentlyContinue){
        $mysqlCmd = 'mysql'
    } elseif(Get-Command mariadb -ErrorAction SilentlyContinue){
        $mysqlCmd = 'mariadb'
    } else {
        Write-ColorLog 'MySQL/MariaDB client not found, cannot run migrations' 'Red' '[DB] '
        return
    }
    
    $dbUser = $env:DB_USER
    if(-not $dbUser){$dbUser = 'sulfur_bot_user'}
    $dbName = $env:DB_NAME
    if(-not $dbName){$dbName = 'sulfur_bot'}
    $dbPass = $env:DB_PASS
    
    # Create migration tracking table
    $createTable = @"
CREATE TABLE IF NOT EXISTS schema_migrations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    migration_name VARCHAR(255) UNIQUE NOT NULL,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_migration_name (migration_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"@
    
    if($dbPass){
        $createTable | & $mysqlCmd -u $dbUser -p"$dbPass" $dbName 2>$null
    } else {
        $createTable | & $mysqlCmd -u $dbUser $dbName 2>$null
    }
    
    # Find and apply migrations
    $migrationsRun = 0
    Get-ChildItem 'scripts\db_migrations\*.sql' -ErrorAction SilentlyContinue | ForEach-Object {
        $migrationName = $_.Name
        
        # Check if already applied
        $checkQuery = "SELECT COUNT(*) FROM schema_migrations WHERE migration_name = '$migrationName'"
        if($dbPass){
            $alreadyApplied = & $mysqlCmd -u $dbUser -p"$dbPass" $dbName -sN -e $checkQuery 2>$null
        } else {
            $alreadyApplied = & $mysqlCmd -u $dbUser $dbName -sN -e $checkQuery 2>$null
        }
        
        if($alreadyApplied -eq '0'){
            Write-ColorLog "Applying migration: $migrationName" 'Cyan' '[DB] '
            
            # Run migration
            if($dbPass){
                Get-Content $_.FullName | & $mysqlCmd -u $dbUser -p"$dbPass" $dbName 2>$null
            } else {
                Get-Content $_.FullName | & $mysqlCmd -u $dbUser $dbName 2>$null
            }
            
            if($LASTEXITCODE -eq 0){
                # Mark as applied
                $insertQuery = "INSERT INTO schema_migrations (migration_name) VALUES ('$migrationName')"
                if($dbPass){
                    $insertQuery | & $mysqlCmd -u $dbUser -p"$dbPass" $dbName 2>$null
                } else {
                    $insertQuery | & $mysqlCmd -u $dbUser $dbName 2>$null
                }
                Write-ColorLog "Migration applied: $migrationName" 'Green' '[DB] '
                $migrationsRun++
            } else {
                Write-ColorLog "Failed to apply migration: $migrationName" 'Red' '[DB] '
            }
        }
    }
    
    if($migrationsRun -eq 0){
        Write-ColorLog 'No pending migrations found' 'Green' '[DB] '
    } else {
        Write-ColorLog "Applied $migrationsRun migration(s)" 'Green' '[DB] '
    }
}

function Test-RequiredDependencies {
    Write-ColorLog 'Checking required Python dependencies...' 'Cyan' '[DEPS] '
    
    $pythonExe = 'python'
    if(Test-Path 'venv\Scripts\python.exe'){
        $pythonExe = 'venv\Scripts\python.exe'
    }
    
    $pipExe = $pythonExe -replace 'python\.exe$','pip.exe'
    
    # Check if requirements.txt exists
    if(-not (Test-Path 'requirements.txt')){
        Write-ColorLog 'requirements.txt not found!' 'Red' '[DEPS] '
        return $false
    }
    
    # Create a marker file to track last requirements install
    $reqMarker = '.last_requirements_install'
    $reqHash = (Get-FileHash -Path 'requirements.txt' -Algorithm MD5).Hash
    $needInstall = $false
    
    # Check if requirements changed or marker doesn't exist
    if(-not (Test-Path $reqMarker)){
        $needInstall = $true
    } else {
        $lastHash = Get-Content $reqMarker -ErrorAction SilentlyContinue
        if($reqHash -ne $lastHash){
            Write-ColorLog 'requirements.txt has changed, updating dependencies...' 'Yellow' '[DEPS] '
            $needInstall = $true
        }
    }
    
    # Also check if critical dependencies are missing
    $criticalPackages = @('discord', 'flask', 'flask_socketio', 'mysql')
    $missingPackages = @()
    
    foreach($package in $criticalPackages){
        $checkCmd = "import $package"
        $result = & $pythonExe -c $checkCmd 2>$null
        if($LASTEXITCODE -ne 0){
            $missingPackages += $package
            $needInstall = $true
        }
    }
    
    if($missingPackages.Count -gt 0){
        Write-ColorLog "Missing critical packages: $($missingPackages -join ', ')" 'Yellow' '[DEPS] '
    }
    
    # Install/update if needed
    if($needInstall){
        Write-ColorLog 'Installing/updating Python dependencies from requirements.txt...' 'Cyan' '[DEPS] '
        
        # Upgrade pip first
        & $pythonExe -m pip install --upgrade pip 2>&1 | Out-Null
        
        # Try normal install first
        $installOutput = & $pipExe install -r requirements.txt 2>&1
        if($LASTEXITCODE -eq 0){
            Write-ColorLog 'Dependencies installed successfully' 'Green' '[DEPS] '
            Set-Content -Path $reqMarker -Value $reqHash
        } else {
            Write-ColorLog 'First install attempt failed; retrying without cache...' 'Yellow' '[DEPS] '
            $installOutput = & $pipExe install -r requirements.txt --no-cache-dir 2>&1
            if($LASTEXITCODE -eq 0){
                Write-ColorLog 'Dependencies installed successfully (no cache)' 'Green' '[DEPS] '
                Set-Content -Path $reqMarker -Value $reqHash
            } else {
                Write-ColorLog 'Failed to install Python dependencies' 'Red' '[DEPS] '
                Write-ColorLog 'Last 10 lines of pip output:' 'Yellow' '[DEPS] '
                $installOutput | Select-Object -Last 10 | ForEach-Object {
                    Write-ColorLog "  $_" 'White' '[DEPS] '
                }
                
                Write-ColorLog 'Trying to install critical packages individually...' 'Yellow' '[DEPS] '
                $criticalPkgNames = @('discord.py', 'Flask', 'Flask-SocketIO', 'mysql-connector-python')
                foreach($pkg in $criticalPkgNames){
                    Write-ColorLog "Installing $pkg..." 'Cyan' '[DEPS] '
                    & $pipExe install $pkg 2>&1 | Out-Null
                    if($LASTEXITCODE -eq 0){
                        Write-ColorLog "  $pkg installed" 'Green' '[DEPS] '
                    } else {
                        Write-ColorLog "  Failed to install $pkg" 'Red' '[DEPS] '
                    }
                }
                return $false
            }
        }
    } else {
        Write-ColorLog 'Python dependencies are up to date' 'Green' '[DEPS] '
    }
    
    # Final verification - check for all required packages
    $allPresent = $true
    foreach($package in $criticalPackages){
        $checkCmd = "import $package"
        $result = & $pythonExe -c $checkCmd 2>$null
        if($LASTEXITCODE -ne 0){
            Write-ColorLog "Missing required package: $package" 'Red' '[DEPS] '
            $allPresent = $false
        }
    }
    
    if(-not $allPresent){
        Write-ColorLog 'Some required packages are still missing!' 'Red' '[DEPS] '
        Write-ColorLog 'Please try manually: pip install -r requirements.txt' 'Yellow' '[DEPS] '
        return $false
    }
    
    Write-ColorLog 'All required dependencies are installed' 'Green' '[DEPS] '
    return $true
}

function Install-OptionalDependencies {
    Write-ColorLog 'Checking optional dependencies for advanced features...' 'Cyan' '[DEPS] '
    
    $pythonExe = 'python'
    if(Test-Path 'venv\Scripts\python.exe'){
        $pythonExe = 'venv\Scripts\python.exe'
    }
    
    # Check for edge-tts
    $hasTTS = & $pythonExe -c "import edge_tts" 2>$null
    if($LASTEXITCODE -ne 0){
        Write-ColorLog 'edge-tts not installed (optional for voice features)' 'Yellow' '[DEPS] '
        Write-ColorLog 'Installing edge-tts...' 'Cyan' '[DEPS] '
        & $pythonExe -m pip install edge-tts 2>$null
        if($LASTEXITCODE -eq 0){
            Write-ColorLog 'edge-tts installed successfully' 'Green' '[DEPS] '
        } else {
            Write-ColorLog 'Failed to install edge-tts (optional)' 'Yellow' '[DEPS] '
        }
    } else {
        Write-ColorLog 'edge-tts is installed' 'Green' '[DEPS] '
    }
    
    # Check for SpeechRecognition
    $hasSR = & $pythonExe -c "import speech_recognition" 2>$null
    if($LASTEXITCODE -ne 0){
        Write-ColorLog 'SpeechRecognition not installed (optional for voice features)' 'Yellow' '[DEPS] '
        Write-ColorLog 'Installing SpeechRecognition...' 'Cyan' '[DEPS] '
        & $pythonExe -m pip install SpeechRecognition 2>$null
        if($LASTEXITCODE -eq 0){
            Write-ColorLog 'SpeechRecognition installed successfully' 'Green' '[DEPS] '
        } else {
            Write-ColorLog 'Failed to install SpeechRecognition (optional)' 'Yellow' '[DEPS] '
        }
    } else {
        Write-ColorLog 'SpeechRecognition is installed' 'Green' '[DEPS] '
    }
    
    Write-ColorLog 'Optional dependencies check complete' 'Green' '[DEPS] '
}

# ==============================================================================
# Bot Start Function
# ==============================================================================

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
    
    try {
        # Setup output redirection
        $script:botOutputFile = [System.IO.StreamWriter]::new($botLogFile, $true)
        $script:botErrorFile = [System.IO.StreamWriter]::new($botErrFile, $true)
        
        $proc.add_OutputDataReceived({
            param($processObject, $e)
            if($e.Data -and $script:botOutputFile) {
                try {
                    $script:botOutputFile.WriteLine($e.Data)
                    $script:botOutputFile.Flush()
                } catch {}
            }
        })
        
        $proc.add_ErrorDataReceived({
            param($processObject, $e)
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
    } catch {
        # Close file handles on error
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
        throw
    }
}

function Test-ForUpdates {
    Write-ColorLog 'Checking for updates...' 'Gray' '[UPDATE] '
    try {
        git remote update 2>&1 | Out-Null
        $status=git status -uno
        if($status -like '*Your branch is behind*'){
            # Check for update loop prevention
            $timeSinceUpdate = (Get-Date) - $script:lastUpdateTime
            
            # Reset loop counter if enough time has passed
            if($timeSinceUpdate.TotalSeconds -gt $script:updateLoopResetSeconds){
                $script:updateLoopCount = 0
            }
            
            # Check if we're in an update loop
            if($script:updateLoopCount -ge $script:maxUpdateLoopCount){
                Write-ColorLog "Update loop detected! Skipping update to prevent infinite loop." 'Yellow' '[UPDATE] '
                Write-ColorLog "Last $($script:maxUpdateLoopCount) updates happened within $($script:updateLoopResetSeconds) seconds." 'Yellow' '[UPDATE] '
                return $false
            }
            
            # Check if we've already pulled this commit
            $remoteCommit = (git rev-parse '@{u}' 2>$null) | Out-String
            $remoteCommit = $remoteCommit.Trim()
            if($remoteCommit -eq $script:lastPulledCommit -and $script:lastPulledCommit -ne ""){
                Write-ColorLog "Already pulled commit $remoteCommit, skipping to prevent loop" 'Yellow' '[UPDATE] '
                return $false
            }
            
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
    
    # Track update loop prevention
    $script:updateLoopCount++
    $script:lastUpdateTime = Get-Date
    
    # For public repos: Reset local changes instead of committing
    if($script:SkipCommit){
        # Check if there are local changes
        $hasLocalChanges = git diff-index --quiet HEAD -- 2>$null
        if($LASTEXITCODE -ne 0){
            Write-ColorLog 'Local changes detected - discarding them before update' 'Yellow' '[UPDATE] '
            Write-ColorLog 'Changes will be discarded to use remote files (public repo mode)' 'Yellow' '[UPDATE] '
            
            # Show what's being reset
            git status --short 2>&1 | Select-Object -First 5 | ForEach-Object { Write-ColorLog "  $_" 'Gray' '[GIT] ' }
            
            # Reset to match remote exactly
            git fetch origin 2>&1 | Out-Null
            git reset --hard origin/main 2>&1 | Out-Null
            if($LASTEXITCODE -ne 0){
                git reset --hard origin/master 2>&1 | Out-Null
            }
            
            Write-ColorLog 'Local changes discarded - using remote files' 'Green' '[UPDATE] '
        }
    } else {
        # Legacy mode: Commit local changes before update (only if explicitly enabled)
        Invoke-GitCommit 'chore: Auto-commit before update'
    }
    
    git fetch 2>&1 | Out-Null
    $changedFiles=git diff --name-only HEAD...origin/main 2>$null
    if(-not $changedFiles){ $changedFiles=git diff --name-only HEAD...origin/master 2>$null }
    
    # Track remote commit
    $remoteCommit = (git rev-parse '@{u}' 2>$null) | Out-String
    $remoteCommit = $remoteCommit.Trim()
    
    if($changedFiles -like '*maintain_bot.ps1*' -or $changedFiles -like '*maintain_bot_fixed.ps1*'){
        Write-ColorLog 'Maintenance script updated; restarting...' 'Magenta' '[UPDATE] '
        
        # For public repos, use hard reset to always match remote
        if($script:SkipCommit){
            git reset --hard $remoteCommit 2>&1 | Out-Null
        } else {
            # Legacy mode with rebase/merge
            git pull --rebase 2>&1 | Out-Null
            if($LASTEXITCODE -ne 0){
                Write-ColorLog 'Rebase failed, trying merge with --no-ff...' 'Yellow' '[UPDATE] '
                git rebase --abort 2>&1 | Out-Null
                git pull --no-rebase 2>&1 | Out-Null
                if($LASTEXITCODE -ne 0){
                    Write-ColorLog 'Standard merge failed, trying explicit --no-ff merge...' 'Yellow' '[UPDATE] '
                    git merge --no-ff origin/main 2>&1 | Out-Null
                    if($LASTEXITCODE -ne 0){
                        git merge --no-ff origin/master 2>&1 | Out-Null
                    }
                }
            }
        }
        $script:lastPulledCommit = (git rev-parse '@' 2>$null) | Out-String
        $script:lastPulledCommit = $script:lastPulledCommit.Trim()
        Invoke-Cleanup
        Start-Process powershell.exe -ArgumentList "-File `"$PSScriptRoot\maintain_bot.ps1`""
        Stop-Transcript
        exit 0
    }
    # Normal update - use hard reset for public repos to avoid merge conflicts
    if($script:SkipCommit){
        # Always use remote files - no merge conflicts
        git reset --hard $remoteCommit 2>&1 | Out-Null
        Write-ColorLog 'Files updated to remote version (hard reset)' 'Green' '[UPDATE] '
    } else {
        # Legacy mode: Use rebase to avoid merge conflicts when local commits exist
        git pull --rebase 2>&1 | Out-Null
        if($LASTEXITCODE -ne 0){
            Write-ColorLog 'Rebase failed, trying merge with --no-ff...' 'Yellow' '[UPDATE] '
            git rebase --abort 2>&1 | Out-Null
            git pull --no-rebase 2>&1 | Out-Null
            if($LASTEXITCODE -ne 0){
                Write-ColorLog 'Standard merge failed, trying explicit --no-ff merge...' 'Yellow' '[UPDATE] '
                git merge --no-ff origin/main 2>&1 | Out-Null
                if($LASTEXITCODE -ne 0){
                    git merge --no-ff origin/master 2>&1 | Out-Null
                    if($LASTEXITCODE -ne 0){
                        Write-ColorLog 'All merge strategies failed - manual intervention may be required' 'Red' '[UPDATE] '
                        Write-ColorLog 'Continuing with current code...' 'Yellow' '[UPDATE] '
                    }
                }
            }
        }
    }
    
    # Track the pulled commit to prevent update loops
    $script:lastPulledCommit = (git rev-parse '@' 2>$null) | Out-String
    $script:lastPulledCommit = $script:lastPulledCommit.Trim()
    if($script:lastPulledCommit -and $script:lastPulledCommit.Length -gt 0){
        $shortCommit = $script:lastPulledCommit.Substring(0, [Math]::Min(8, $script:lastPulledCommit.Length))
        Write-ColorLog "Updated to commit: $shortCommit" 'Green' '[UPDATE] '
    } else {
        Write-ColorLog "Updated to latest commit" 'Green' '[UPDATE] '
    }
    
    # Check Java 21 for Minecraft support
    Test-JavaVersion | Out-Null
    
    # Check FFmpeg installation
    Test-FFmpegInstallation | Out-Null
    
    # Initialize/update database tables after pulling updates with retry logic
    Write-ColorLog 'Updating database tables and applying migrations...' 'Cyan' '[UPDATE] '
    
    $pythonExe = 'python'
    if (Test-Path 'venv\Scripts\python.exe') {
        $pythonExe = 'venv\Scripts\python.exe'
    }
    
    # Run database initialization and apply migrations
    $dbInitScript = @"
from modules.db_helpers import init_db_pool, initialize_database, apply_pending_migrations
import os
import sys
from dotenv import load_dotenv

load_dotenv()
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_USER = os.environ.get('DB_USER', 'sulfur_bot_user')
DB_PASS = os.environ.get('DB_PASS', '')
DB_NAME = os.environ.get('DB_NAME', 'sulfur_bot')

try:
    # Initialize database pool with retry logic
    print(f'Initializing database pool: {DB_USER}@{DB_HOST}/{DB_NAME}')
    if not init_db_pool(DB_HOST, DB_USER, DB_PASS, DB_NAME):
        print('ERROR: Failed to initialize database pool')
        sys.exit(1)
    print('Database pool initialized')
    
    # Create base tables with retry logic
    print('Initializing database tables...')
    if not initialize_database():
        print('ERROR: Failed to initialize database tables')
        sys.exit(1)
    print('Database tables initialized successfully')
    
    # Apply any pending migrations
    print('Checking for pending migrations...')
    applied_count, errors = apply_pending_migrations()
    if applied_count > 0:
        print(f'Applied {applied_count} new database migrations')
    if errors:
        print(f'WARNING: {len(errors)} migration errors occurred')
        for error in errors:
            print(f'  - {error}')
        # Don't exit on migration errors, just warn
        print('Continuing despite migration errors...')
    else:
        print('All database migrations up to date')
    
    sys.exit(0)
except Exception as e:
    print(f'ERROR: Database update failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"@
    
    $dbUpdateSuccess = $false
    $dbMaxAttempts = 5
    for ($dbAttempt = 1; $dbAttempt -le $dbMaxAttempts; $dbAttempt++) {
        try {
            Write-ColorLog "Database update attempt $dbAttempt/$dbMaxAttempts..." 'Cyan' '[UPDATE] '
            
            $output = & $pythonExe -c $dbInitScript 2>&1
            if ($LASTEXITCODE -eq 0) {
                if ($output) {
                    $output | ForEach-Object { Write-ColorLog $_ 'White' '[DB] ' }
                }
                Write-ColorLog 'Database tables and migrations updated successfully' 'Green' '[UPDATE] '
                $dbUpdateSuccess = $true
                break
            } else {
                Write-ColorLog "Database update attempt $dbAttempt failed (exit code: $LASTEXITCODE)" 'Yellow' '[UPDATE] '
                if ($output) {
                    Write-ColorLog 'Last error output:' 'Yellow' '[UPDATE] '
                    $output | Select-Object -Last 5 | ForEach-Object { Write-ColorLog "  $_" 'White' '[UPDATE] ' }
                }
                
                if ($dbAttempt -lt $dbMaxAttempts) {
                    $waitTime = 5 * $dbAttempt
                    Write-ColorLog "Retrying in $waitTime seconds..." 'Cyan' '[UPDATE] '
                    Start-Sleep -Seconds $waitTime
                }
            }
        } catch {
            Write-ColorLog "Database update attempt $dbAttempt error: $($_.Exception.Message)" 'Yellow' '[UPDATE] '
            
            if ($dbAttempt -lt $dbMaxAttempts) {
                $waitTime = 5 * $dbAttempt
                Write-ColorLog "Retrying in $waitTime seconds..." 'Cyan' '[UPDATE] '
                Start-Sleep -Seconds $waitTime
            }
        }
    }
    
    if (-not $dbUpdateSuccess) {
        Write-ColorLog 'WARNING: Database update failed after all retries' 'Yellow' '[UPDATE] '
        Write-ColorLog 'Bot may experience database issues' 'Yellow' '[UPDATE] '
    }
    
    Write-ColorLog 'Update complete' 'Green' '[UPDATE] '
    (Get-Date).ToUniversalTime().ToString('o') | Out-File -FilePath 'last_update.txt' -Encoding utf8
    
    # Restart web dashboard after update if it's not running
    Write-ColorLog 'Checking web dashboard status after update...' 'Cyan' '[UPDATE] '
    $webIsRunning = $false
    
    # Check both job state and actual process state
    if($script:webDashboardJob){
        $jobRunning = (Get-Job -Id $script:webDashboardJob.Id -ErrorAction SilentlyContinue) -and $script:webDashboardJob.State -eq 'Running'
        
        # Also verify the Python process is actually running
        $processRunning = $false
        if($jobRunning){
            $webProcesses = Get-Process -Name python* -ErrorAction SilentlyContinue | Where-Object {
                try {
                    $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)" -ErrorAction SilentlyContinue).CommandLine
                    $cmdLine -and ($cmdLine -like "*web_dashboard.py*")
                } catch {
                    $false
                }
            }
            if($webProcesses){
                $processRunning = $true
            }
        }
        
        if($jobRunning -and $processRunning){
            Write-ColorLog 'Web Dashboard is still running' 'Green' '[WEB] '
            $webIsRunning = $true
        }
    }
    
    if(-not $webIsRunning){
        Write-ColorLog 'Web Dashboard is not running, attempting to restart...' 'Yellow' '[WEB] '
        
        # Clean up the old job if it exists
        if($script:webDashboardJob){
            Remove-Job $script:webDashboardJob -Force -ErrorAction SilentlyContinue
            $script:webDashboardJob = $null
        }
        
        try {
            $script:webDashboardJob = Start-WebDashboard
            if($script:webDashboardJob){
                Write-ColorLog 'Web Dashboard restarted successfully after update' 'Green' '[WEB] '
            } else {
                Write-ColorLog 'Web Dashboard failed to restart after update' 'Yellow' '[WEB] '
            }
        } catch {
            Write-ColorLog "Web Dashboard restart error: $($_.Exception.Message)" 'Yellow' '[WEB] '
            $script:webDashboardJob = $null
        }
    }
}

# ==================== MAIN LOOP ====================
Write-Host '=== Sulfur Discord Bot - Maintenance System v2.1 [Fixed] ===' -ForegroundColor Cyan
Write-Host ''
Write-ColorLog "Press 'Q' to shutdown" 'Yellow'
Write-Host ''

if(-not $SkipDatabaseBackup){
    Invoke-DatabaseBackup
}

# Ensure database server is running
try {
    Start-DatabaseServerIfNeeded | Out-Null
} catch {
    Write-ColorLog "Warning: Database server check error: $($_.Exception.Message)" 'Yellow'
}

# Run database initialization and migrations on startup with retry logic
Write-ColorLog 'Initializing database and applying migrations...' 'Cyan' '[DB] '

$pythonExe = 'python'
if (Test-Path 'venv\Scripts\python.exe') {
    $pythonExe = 'venv\Scripts\python.exe'
}

$dbStartupScript = @"
from modules.db_helpers import init_db_pool, initialize_database, apply_pending_migrations
import os
import sys
from dotenv import load_dotenv

load_dotenv()
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_USER = os.environ.get('DB_USER', 'sulfur_bot_user')
DB_PASS = os.environ.get('DB_PASS', '')
DB_NAME = os.environ.get('DB_NAME', 'sulfur_bot')

try:
    # Initialize database pool with retry logic
    print(f'Initializing database pool: {DB_USER}@{DB_HOST}/{DB_NAME}')
    if not init_db_pool(DB_HOST, DB_USER, DB_PASS, DB_NAME):
        print('ERROR: Failed to initialize database pool')
        sys.exit(1)
    print('Database pool initialized successfully')
    
    # Create base tables with retry logic
    print('Initializing database tables...')
    if not initialize_database():
        print('ERROR: Failed to initialize database tables')
        sys.exit(1)
    print('Database tables initialized successfully')
    
    # Apply any pending migrations
    print('Checking for pending migrations...')
    applied_count, errors = apply_pending_migrations()
    if applied_count > 0:
        print(f'Applied {applied_count} new database migrations')
    if errors:
        print(f'WARNING: {len(errors)} migration errors occurred')
        for error in errors:
            print(f'  - {error}')
        # Don't exit on migration errors, just warn
        print('Continuing despite migration errors...')
    else:
        print('All database migrations up to date')
    
    sys.exit(0)
except Exception as e:
    print(f'ERROR: Database initialization failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"@

$dbInitSuccess = $false
$dbMaxAttempts = 5
for ($attempt = 1; $attempt -le $dbMaxAttempts; $attempt++) {
    try {
        Write-ColorLog "Database initialization attempt $attempt/$dbMaxAttempts..." 'Cyan' '[DB] '
        
        $output = & $pythonExe -c $dbStartupScript 2>&1
        if ($LASTEXITCODE -eq 0) {
            if ($output) {
                $output | ForEach-Object { Write-ColorLog $_ 'White' '[DB] ' }
            }
            Write-ColorLog 'Database ready - tables and migrations up to date' 'Green' '[DB] '
            $dbInitSuccess = $true
            break
        } else {
            Write-ColorLog "Database initialization attempt $attempt failed (exit code: $LASTEXITCODE)" 'Yellow' '[DB] '
            if ($output) {
                Write-ColorLog 'Last error output:' 'Yellow' '[DB] '
                $output | Select-Object -Last 5 | ForEach-Object { Write-ColorLog "  $_" 'White' '[DB] ' }
            }
            
            if ($attempt -lt $dbMaxAttempts) {
                $waitTime = 5 * $attempt
                Write-ColorLog "Retrying in $waitTime seconds..." 'Cyan' '[DB] '
                Start-Sleep -Seconds $waitTime
            }
        }
    } catch {
        Write-ColorLog "Database initialization attempt $attempt error: $($_.Exception.Message)" 'Yellow' '[DB] '
        
        if ($attempt -lt $dbMaxAttempts) {
            $waitTime = 5 * $attempt
            Write-ColorLog "Retrying in $waitTime seconds..." 'Cyan' '[DB] '
            Start-Sleep -Seconds $waitTime
        }
    }
}

if (-not $dbInitSuccess) {
    Write-ColorLog '=' * 70 'Red'
    Write-ColorLog 'WARNING: Database initialization failed after all retries' 'Red' '[DB] '
    Write-ColorLog 'Bot will start anyway, but database features will be unavailable' 'Yellow' '[DB] '
    Write-ColorLog 'Please check:' 'Yellow' '[DB] '
    Write-ColorLog '  1. Database server is running (MySQL/MariaDB service)' 'White' '[DB] '
    Write-ColorLog '  2. Database credentials in .env are correct' 'White' '[DB] '
    Write-ColorLog '  3. Database sulfur_bot exists' 'White' '[DB] '
    Write-ColorLog '  4. User sulfur_bot_user has proper permissions' 'White' '[DB] '
    Write-ColorLog '=' * 70 'Red'
}

# Run advanced AI database migrations
Run-DatabaseMigrations

# Check and install required dependencies
if(-not (Test-RequiredDependencies)){
    Write-ColorLog '=' * 70 'Red'
    Write-ColorLog 'WARNING: Some required dependencies are missing!' 'Red' '[DEPS] '
    Write-ColorLog 'Bot may not start correctly. Please check the errors above.' 'Yellow' '[DEPS] '
    Write-ColorLog '=' * 70 'Red'
    Write-ColorLog 'Waiting 10 seconds before continuing...' 'Yellow' '[DEPS] '
    Start-Sleep -Seconds 10
}

# Install optional dependencies for voice features
Install-OptionalDependencies

# Check optional API keys and show warnings (non-blocking)
Test-OptionalApiKeys

try {
    $script:webDashboardJob=Start-WebDashboard
    if(-not $script:webDashboardJob){
        Write-ColorLog 'Warning: Web Dashboard failed to start' 'Yellow'
    }
} catch {
    Write-ColorLog "Warning: Web Dashboard startup error: $($_.Exception.Message)" 'Yellow'
    $script:webDashboardJob = $null
}

# ==============================================================================
# Minecraft Server Auto-Start Function
# ==============================================================================

function Start-MinecraftServer {
    Write-ColorLog 'Checking Minecraft server auto-start configuration...' 'Cyan'
    
    # Find Python executable
    $pythonExe = $null
    if(Test-Path 'venv\Scripts\python.exe'){
        $pythonExe = 'venv\Scripts\python.exe'
    } elseif(Get-Command python -ErrorAction SilentlyContinue){
        $pythonExe = 'python'
    } elseif(Get-Command python3 -ErrorAction SilentlyContinue){
        $pythonExe = 'python3'
    }
    
    if(-not $pythonExe){
        Write-ColorLog 'Python not found, cannot check Minecraft configuration' 'Yellow'
        return $false
    }
    
    # Check if Minecraft is enabled and boot_with_bot is true
    $checkScript = @"
import json
import sys
try:
    with open('config/config.json', 'r') as f:
        config = json.load(f)
    
    # Check if minecraft feature is enabled
    minecraft_enabled = config.get('features', {}).get('minecraft_server', False)
    
    # Check if boot_with_bot is enabled in minecraft config
    boot_with_bot = config.get('modules', {}).get('minecraft', {}).get('boot_with_bot', False)
    
    if minecraft_enabled and boot_with_bot:
        sys.exit(0)  # Start server
    else:
        sys.exit(1)  # Don't start server
except Exception as e:
    print(f'Error checking config: {e}')
    sys.exit(1)
"@
    
    try {
        $result = & $pythonExe -c $checkScript 2>&1
        if($LASTEXITCODE -eq 0){
            Write-ColorLog 'Minecraft server auto-start is enabled' 'Cyan'
            Write-ColorLog 'Starting Minecraft server...' 'Cyan'
            
            # Start server using Python module
            $startScript = @"
import asyncio
import json
import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Import minecraft module
try:
    from modules import minecraft_server as mc
    from modules.logger_utils import bot_logger as logger
except ImportError as e:
    print(f'ERROR: Failed to import minecraft_server module: {e}')
    sys.exit(1)

async def start_mc_server():
    try:
        # Load config
        with open('config/config.json', 'r') as f:
            config = json.load(f)
        
        mc_config = config.get('modules', {}).get('minecraft', {})
        
        # Check if server is already running
        if mc.is_server_running():
            print('Minecraft server is already running')
            return True
        
        # Start the server
        print('Starting Minecraft server...')
        success, message = await mc.start_server(mc_config)
        
        if success:
            print(f'Minecraft server started successfully: {message}')
            return True
        else:
            print(f'Failed to start Minecraft server: {message}')
            return False
            
    except Exception as e:
        print(f'ERROR: Failed to start Minecraft server: {e}')
        import traceback
        traceback.print_exc()
        return False

# Run the async function
try:
    result = asyncio.run(start_mc_server())
    sys.exit(0 if result else 1)
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"@
            
            $startResult = & $pythonExe -c $startScript 2>&1
            if($LASTEXITCODE -eq 0){
                Write-ColorLog 'Minecraft server started successfully' 'Green'
                return $true
            } else {
                Write-ColorLog 'Failed to start Minecraft server (check logs for details)' 'Yellow'
                Write-ColorLog 'You can start it manually via the web dashboard at http://localhost:5000/minecraft' 'Cyan'
                if($startResult){
                    Write-Host $startResult
                }
                return $false
            }
        } else {
            Write-ColorLog 'Minecraft server auto-start is disabled (feature not enabled or boot_with_bot=false)' 'Gray'
            Write-ColorLog 'Enable it in config.json: features.minecraft_server=true and modules.minecraft.boot_with_bot=true' 'Gray'
            return $false
        }
    } catch {
        Write-ColorLog "Error checking Minecraft configuration: $($_.Exception.Message)" 'Yellow'
        return $false
    }
}

# Start Minecraft server if configured
try {
    Start-MinecraftServer | Out-Null
} catch {
    Write-ColorLog "Minecraft server auto-start error: $($_.Exception.Message)" 'Yellow'
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
            
            # Kill process and ensure it's terminated
            if($script:botProcess -and -not $script:botProcess.HasExited){
                try {
                    $script:botProcess.Kill()
                    if(-not $script:botProcess.WaitForExit(5000)) {
                        Stop-Process -Id $script:botProcess.Id -Force -ErrorAction SilentlyContinue
                    }
                } catch {
                    Stop-Process -Id $script:botProcess.Id -Force -ErrorAction SilentlyContinue
                }
            }
            
            # Dispose process object
            if($script:botProcess) {
                try {
                    $script:botProcess.Close()
                    $script:botProcess.Dispose()
                } catch {}
                $script:botProcess = $null
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
