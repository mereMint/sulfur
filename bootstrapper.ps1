# This is a simple bootstrapper script.
# Its only purpose is to restart the main maintain_bot.ps1 script after it has updated itself.

# Wait for the old watcher process to exit completely.
Start-Sleep -Seconds 3

Write-Host "Bootstrapper: Restarting the updated maintenance watcher..."

# Execute the new version of the maintenance script in a new window and then this bootstrapper will exit.
Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", "& `"$PSScriptRoot\maintain_bot.ps1`""