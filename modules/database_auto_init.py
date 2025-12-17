"""
Automatic Database Initialization Module

This module automatically initializes the database when the bot starts
if it hasn't been configured yet. It runs silently in the background
and provides helpful error messages if setup is needed.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional

# Import database config module
try:
    from modules.database_config import DatabaseConfig, DatabaseConfigError
except ImportError:
    # If module doesn't exist yet, define minimal fallback
    class DatabaseConfigError(Exception):
        pass

    class DatabaseConfig:
        @classmethod
        def is_configured(cls) -> bool:
            config_file = Path("config/database.json")
            return config_file.exists()


def check_database_configured() -> bool:
    """
    Check if database is configured and working

    Returns:
        True if database is ready, False otherwise
    """
    try:
        return DatabaseConfig.is_configured()
    except Exception:
        return False


def run_auto_setup() -> bool:
    """
    Run automatic database setup script

    Returns:
        True if setup succeeded, False otherwise
    """
    script_path = Path(__file__).parent.parent / "scripts" / "setup_database_auto.py"

    if not script_path.exists():
        return False

    try:
        # Run setup script
        result = subprocess.run(
            [sys.executable, str(script_path)],
            check=False,
            capture_output=False  # Show output to user
        )

        return result.returncode == 0

    except Exception as e:
        print(f"Auto-setup failed: {e}")
        return False


def ensure_database_ready(auto_setup: bool = False) -> bool:
    """
    Ensure database is configured and ready

    Args:
        auto_setup: If True, attempt automatic setup if not configured

    Returns:
        True if database is ready, False otherwise

    Raises:
        DatabaseConfigError: If database is not configured and auto_setup is False
    """
    # Check if already configured
    if check_database_configured():
        return True

    # If auto_setup enabled, try to set up automatically
    if auto_setup:
        print()
        print("=" * 70)
        print("Database not configured - running automatic setup")
        print("=" * 70)
        print()

        if run_auto_setup():
            print()
            print("=" * 70)
            print("✓ Database setup complete")
            print("=" * 70)
            print()
            return True
        else:
            print()
            print("=" * 70)
            print("✗ Automatic setup failed")
            print("=" * 70)
            print()

    # Not configured and auto-setup failed or disabled
    raise DatabaseConfigError(
        "Database is not configured.\n\n"
        "To set up the database, run ONE of these commands:\n\n"
        "  Option 1 (Recommended - Fully Automated):\n"
        "    python scripts/setup_database_auto.py\n\n"
        "  Option 2 (Secure with Password):\n"
        "    bash scripts/setup_database_secure.sh\n\n"
        "  Option 3 (Simple, No Password):\n"
        "    python setup_database.py\n\n"
        "Then run: python apply_migration.py --all\n"
    )


def get_setup_instructions() -> str:
    """
    Get user-friendly setup instructions

    Returns:
        Formatted string with setup instructions
    """
    return """
╔══════════════════════════════════════════════════════════════════╗
║                 DATABASE SETUP REQUIRED                          ║
╚══════════════════════════════════════════════════════════════════╝

The database has not been configured yet. Please run one of these:

  🚀 Option 1 (Recommended - Fully Automated):
     python scripts/setup_database_auto.py

  🔐 Option 2 (Secure Bash Script with Strong Password):
     bash scripts/setup_database_secure.sh

  📝 Option 3 (Simple Python Script, No Password):
     python setup_database.py
     python apply_migration.py --all

The automated script (Option 1) will:
  ✓ Check if MySQL/MariaDB is running
  ✓ Create database and user with secure password
  ✓ Run all migrations automatically
  ✓ Handle errors gracefully

After setup, start the bot with: python bot.py
"""


# Export main function for easy import
__all__ = ['ensure_database_ready', 'check_database_configured', 'get_setup_instructions']
