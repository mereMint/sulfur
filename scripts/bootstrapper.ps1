# This is a bootstrapper script.
# Its purpose is to handle the self-update process of the maintenance watcher.

# Wait for the old watcher process to exit completely.
Start-Sleep -Seconds 3

Write-Host "Bootstrapper: Pulling latest changes to finalize update..."
git fetch origin 2>&1 | Out-Null
git reset --hard origin/main 2>&1 | Out-Null
if($LASTEXITCODE -ne 0){
    git reset --hard origin/master 2>&1 | Out-Null
}

Write-Host "Bootstrapper: Restarting the updated maintenance watcher..."
# Execute the new version of the maintenance script in a new window, and then this bootstrapper will exit.
Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", "& `"$PSScriptRoot\maintain_bot.ps1`""