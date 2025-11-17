# Fix for maintain_bot.ps1 Background Process Issue

## Problem
The `maintain_bot.ps1` script doesn't properly kill the bot process even when cleanup handlers are triggered. The bot continues running in the background and cannot be stopped.

## Root Cause
Using `Start-Process` with `-WindowStyle Hidden` creates a detached process that:
1. Doesn't respond well to cleanup handlers
2. Orphans when the parent script exits
3. Continues running even after `Stop-Process` commands

## Solution

### Option 1: Use System.Diagnostics.Process (Recommended)
Replace the `Start-Bot` function with proper process management:

```powershell
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
    $startInfo.CreateNoWindow = $true  # Don't create a window, but keep process attached
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
        if($e.Data) {
            $script:botOutputFile.WriteLine($e.Data)
            $script:botOutputFile.Flush()
        }
    })
    
    $proc.add_ErrorDataReceived({
        param($sender, $e)
        if($e.Data) {
            $script:botErrorFile.WriteLine($e.Data)
            $script:botErrorFile.Flush()
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
```

### Option 2: Better Cleanup in trap Handler

Update the trap handler to properly close file handles and kill processes:

```powershell
trap {
    Write-Host 'Script terminated. Cleaning up...' -ForegroundColor Red
    
    # Close file handles first to release locks
    if($script:botOutputFile) {
        try {
            $script:botOutputFile.Close()
            $script:botOutputFile.Dispose()
        } catch {}
    }
    if($script:botErrorFile) {
        try {
            $script:botErrorFile.Close()
            $script:botErrorFile.Dispose()
        } catch {}
    }
    
    # Kill bot process using .NET method
    if($script:botProcess -and -not $script:botProcess.HasExited){
        Write-Host "Stopping bot process (PID: $($script:botProcess.Id))..." -ForegroundColor Yellow
        try {
            $script:botProcess.Kill()
            $script:botProcess.WaitForExit(5000)  # Wait up to 5 seconds
            $script:botProcess.Close()
        } catch {
            # Fallback to Stop-Process
            Stop-Process -Id $script:botProcess.Id -Force -ErrorAction SilentlyContinue
        }
    }
    
    # Stop web dashboard
    if($script:webDashboardJob){
        Write-Host 'Stopping Web Dashboard...' -ForegroundColor Yellow
        Stop-Job $script:webDashboardJob -ErrorAction SilentlyContinue
        Remove-Job $script:webDashboardJob -Force -ErrorAction SilentlyContinue
    }
    
    # Kill any remaining orphaned Python processes
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
    
    Update-BotStatus 'Shutdown'
    Write-Host 'Cleanup complete.' -ForegroundColor Green
    Stop-Transcript
    exit 0
}
```

### Option 3: Use Job Control (Alternative)

If the above doesn't work, use PowerShell jobs instead:

```powershell
function Start-Bot {
    Write-ColorLog 'Starting bot...' 'Cyan' '[BOT] '
    Update-BotStatus 'Starting...'
    $pythonExe='python'
    if(Test-Path 'venv\Scripts\python.exe'){
        $pythonExe='venv\Scripts\python.exe'
    }
    
    # Start as a job for better control
    $job = Start-Job -ScriptBlock {
        param($Python, $Root, $LogFile, $ErrFile)
        Set-Location $Root
        & $Python -u bot.py 2>&1 | Tee-Object -FilePath $LogFile
    } -ArgumentList $pythonExe, $PSScriptRoot, $botLogFile, ($botLogFile -replace '\.log$','_errors.log')
    
    Start-Sleep -Seconds 2
    
    # Get the actual Python process ID
    $childProcs = Get-CimInstance Win32_Process | Where-Object {
        $_.ParentProcessId -eq $job.Id -and $_.Name -like 'python*'
    }
    
    if($childProcs) {
        $pythonPid = $childProcs[0].ProcessId
        Update-BotStatus 'Running' $pythonPid
        Write-ColorLog "Bot started (PID: $pythonPid, Job ID: $($job.Id))" 'Green' '[BOT] '
        
        # Return both job and process info
        return @{
            Job = $job
            ProcessId = $pythonPid
            Process = Get-Process -Id $pythonPid
        }
    }
    
    return $null
}
```

## Testing the Fix

1. Apply one of the solutions above
2. Start the bot: `.\maintain_bot.ps1`
3. Verify bot is running in Discord
4. Test cleanup:
   - Press `Ctrl+C` in the PowerShell window
   - OR create `stop.flag` file
5. Check Task Manager for orphaned `python.exe` processes
6. Verify all processes are terminated

## Additional Recommendations

1. **Add process tracking**: Store PIDs in a file for cleanup even after script restart
2. **Use job objects**: Windows job objects provide guaranteed cleanup
3. **Add timeout**: Kill processes forcefully if graceful shutdown takes too long
4. **Monitor orphans**: Add periodic orphan detection and cleanup

## Manual Cleanup (Emergency)

If processes are still stuck:

```powershell
# Kill all Python processes from the bot directory
Get-Process python* | Where-Object {
    try {
        $_.Path -like "*sulfur*"
    } catch {
        $false
    }
} | Stop-Process -Force

# Or by process ID (check Task Manager)
Stop-Process -Id <PID> -Force
```

## Implementation Status

- [ ] Update Start-Bot function with System.Diagnostics.Process
- [ ] Update trap handler with proper cleanup
- [ ] Update stop.flag handler
- [ ] Update restart.flag handler
- [ ] Test Ctrl+C cleanup
- [ ] Test stop.flag cleanup
- [ ] Test restart.flag cleanup
- [ ] Verify no orphaned processes remain
