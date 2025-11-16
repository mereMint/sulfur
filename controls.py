import subprocess
import os
import platform

def _run_command(command):
    """Runs a command and returns its output."""
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True, shell=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Error executing command:\n{e.stdout}\n{e.stderr}"

def sync_database_changes():
    """
    Adds, commits, and pushes the database_sync.sql file.
    This is a safe, isolated action.
    """
    print("Web Dashboard: Syncing database changes...")
    # Check for changes first
    status_output = _run_command("git status --porcelain database_sync.sql")
    if not status_output:
        return "No database changes to sync."

    _run_command("git add database_sync.sql")
    _run_command('git commit -m "chore: Sync database schema via web dashboard"')
    push_output = _run_command("git push")
    return f"Database changes synced successfully.\n{push_output}"

def update_bot_from_git():
    """
    Runs git pull to update the bot.
    This is a safe, isolated action.
    """
    print("Web Dashboard: Pulling latest updates...")
    return _run_command("git pull")

def restart_bot():
    """
    Creates a 'restart.flag' file.
    The maintain_bot script will detect this file, stop the current bot process,
    and start a new one in the next loop iteration.
    """
    print("Web Dashboard: Signaling bot for restart...")
    with open("restart.flag", "w") as f:
        f.write("restart")
    return "Restart signal sent. The bot will restart on the next maintenance cycle (within ~15 seconds)."

def stop_bot_processes():
    """
    Creates a 'stop.flag' file.
    The maintain_bot script will detect this file, stop all processes,
    and exit cleanly.
    """
    print("Web Dashboard: Signaling for full shutdown...")
    with open("stop.flag", "w") as f:
        f.write("stop")
    return "Shutdown signal sent. The maintenance script and bot will stop completely."