# This script acts as a watcher to maintain the Sulfur bot.
# It starts the bot and then checks for updates from the Git repository every minute.
# If updates are found, it automatically restarts the bot.

# To run it:
# 1. Open PowerShell
# 2. Navigate to this directory (cd c:\sulfur)
# 3. Run the script with: .\maintain_bot.ps1

Write-Host "--- Sulfur Bot Maintenance Watcher ---"

# --- NEW: Set environment variables in the top-level script ---
Write-Host "Setting environment variables for the bot session..."
$env:DISCORD_BOT_TOKEN="MTQzODU5NTUzNjE1MTM4MDAxOA.GwuLkF.NYHg6QXtQfhGIPK6SRA8TxDo4-wOtJrTzn00EU"
$env:GEMINI_API_KEY="AIzaSyD7h08ULN7KXhYCFFiIa6MPEbN_TnL5COU"
$env:OPENAI_API_KEY="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"

while ($true) {
    Write-Host "Starting the bot process..."
    # Start the main bot script as a background job.
    # This allows the watcher to continue running while the bot is active.
    $botJob = Start-Job -ScriptBlock { 
        & .\start_bot.ps1 
    }

    Write-Host "Bot is running in the background (Job ID: $($botJob.Id)). Checking for updates every 60 seconds."

    while ($botJob.State -eq 'Running') {
        Start-Sleep -Seconds 15

        # --- NEW: Log the time of the update check ---
        (Get-Date).ToUniversalTime().ToString("o") | Out-File -FilePath "last_check.txt" -Encoding utf8

        # Fetch the latest changes from the remote repository
        git remote update
        $status = git status -uno

        if ($status -like "*Your branch is behind*") {
            Write-Host "New version found in the repository! Restarting the bot to apply updates..."
            # Create the flag file to signal the bot to go idle
            New-Item -Path "update_pending.flag" -ItemType File -Force | Out-Null
            Stop-Job -Job $botJob # Stop the bot
            Write-Host "Pulling latest changes from git..."
            git pull
            # --- NEW: Log the time of the successful update ---
            (Get-Date).ToUniversalTime().ToString("o") | Out-File -FilePath "last_update.txt" -Encoding utf8
            Remove-Item -Path "update_pending.flag" -ErrorAction SilentlyContinue # Clean up the flag
            break # Exit the inner loop to allow the outer loop to restart it
        }
    }

    Write-Host "Bot process stopped. It will be restarted shortly..."
    Start-Sleep -Seconds 5 # Brief pause before restarting
}