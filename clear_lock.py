#!/usr/bin/env python3
"""
Clear the bot instance lock file.
Use this if the bot won't start because it thinks another instance is running.
"""

import os
import sys

LOCK_FILE = "bot_instance.lock"

def main():
    if os.path.exists(LOCK_FILE):
        try:
            # Read the PID from the lock file
            with open(LOCK_FILE, 'r') as f:
                pid = f.read().strip()
            
            print(f"Found lock file with PID: {pid}")
            
            # Check if process is running
            try:
                if sys.platform == "win32":
                    import subprocess
                    result = subprocess.run(['tasklist', '/FI', f'PID eq {pid}'], 
                                          capture_output=True, text=True, timeout=5)
                    is_running = pid in result.stdout
                else:
                    os.kill(int(pid), 0)
                    is_running = True
            except (ProcessLookupError, PermissionError, ValueError, subprocess.TimeoutExpired):
                is_running = False  # Process doesn't exist or we can't check it
            
            if is_running:
                print(f"WARNING: Process {pid} is still running!")
                response = input("Do you want to remove the lock file anyway? (yes/no): ")
                if response.lower() not in ['yes', 'y']:
                    print("Aborted. Lock file not removed.")
                    return 1
            else:
                print(f"Process {pid} is not running (stale lock file)")
            
            # Remove the lock file
            os.remove(LOCK_FILE)
            print(f"✓ Lock file removed successfully")
            return 0
            
        except Exception as e:
            print(f"Error removing lock file: {e}")
            return 1
    else:
        print("No lock file found - nothing to do")
        return 0

if __name__ == "__main__":
    sys.exit(main())
