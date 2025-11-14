# This script acts as a watcher to maintain the Sulfur bot.
# It starts the bot and then checks for updates from the Git repository every minute.
# If updates are found, it automatically restarts the bot.

# To run it:
# 1. Open PowerShell
# 2. Navigate to this directory (cd c:\sulfur)
# 3. Run the script with: .\maintain_bot.ps1

Write-Host "--- Sulfur Bot Maintenance Watcher ---"

while ($true) {
    Write-Host "Starting the bot process..."
    # Start the main bot script as a background job.
    # This allows the watcher to continue running while the bot is active.
    $botJob = Start-Job -ScriptBlock { 
        # We need to pass environment variables to the job's scope
        $env:DISCORD_BOT_TOKEN = $using:env:DISCORD_BOT_TOKEN
        $env:GEMINI_API_KEY = $using:env:GEMINI_API_KEY
        $env:OPENAI_API_KEY = $using:env:OPENAI_API_KEY
        & .\start_bot.ps1 
    }

    Write-Host "Bot is running in the background (Job ID: $($botJob.Id)). Checking for updates every 60 seconds."

    while ($botJob.State -eq 'Running') {
        Start-Sleep -Seconds 30

        # Fetch the latest changes from the remote repository
        git remote update
        $status = git status -uno

        if ($status -like "*Your branch is behind*") {
            Write-Host "New version found in the repository! Restarting the bot to apply updates..."
            Stop-Job -Job $botJob # Stop the bot
            break # Exit the inner loop to allow the outer loop to restart it
        }
    }

    Write-Host "Bot process stopped. It will be restarted shortly..."
    Start-Sleep -Seconds 5 # Brief pause before restarting
}