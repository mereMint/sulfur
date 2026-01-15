#!/usr/bin/env python3
"""
Sulfur Bot - Automated Database Setup Script

This script provides a fully automated, intelligent database setup that:
- Detects and starts MariaDB/MySQL if not running
- Creates database and user with secure credentials
- Runs all migrations in correct order
- Handles errors gracefully with rollback support
- Works on Linux, Termux, and Windows
- Provides detailed progress feedback
"""

import os
import sys
import time
import subprocess
import json
import secrets
import string
import shutil
from pathlib import Path
from typing import Optional, Tuple, List

try:
    import mysql.connector
    from mysql.connector import Error as MySQLError
except ImportError:
    print("=" * 70)
    print("ERROR: mysql-connector-python not installed")
    print("=" * 70)
    print()
    print("Install it with: pip install mysql-connector-python")
    print("Or: pip install -r requirements.txt")
    print()
    sys.exit(1)

# ==============================================================================
# Configuration
# ==============================================================================

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
CONFIG_DIR = PROJECT_ROOT / "config"
CONFIG_FILE = CONFIG_DIR / "database.json"
MIGRATIONS_DIR = SCRIPT_DIR / "db_migrations"

DB_NAME = os.environ.get("DB_NAME", "sulfur_bot")
DB_USER = os.environ.get("DB_USER", "sulfur_bot_user")
DB_HOST = os.environ.get("DB_HOST", "localhost")

# MariaDB 10.4+ privilege bitmask constant
# This grants: SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, RELOAD, SHUTDOWN,
# PROCESS, FILE, REFERENCES, INDEX, ALTER, SHOW DATABASES, SUPER, CREATE TEMPORARY TABLES,
# LOCK TABLES, EXECUTE, REPLICATION SLAVE, REPLICATION CLIENT, CREATE VIEW, SHOW VIEW,
# CREATE ROUTINE, ALTER ROUTINE, CREATE USER, EVENT, TRIGGER
MARIADB_ALL_PRIVILEGES_BITMASK = 1073741823

# Validate database and user names to prevent SQL injection
# Only allow alphanumeric characters and underscores
def _validate_identifier(name: str, identifier_type: str) -> bool:
    """Validate that an identifier contains only safe characters."""
    import re
    if not re.match(r'^[a-zA-Z0-9_]+$', name):
        print_error(f"Invalid {identifier_type}: {name}")
        print_error("Only alphanumeric characters and underscores are allowed.")
        return False
    if len(name) > 64:  # MySQL identifier max length
        print_error(f"{identifier_type} too long (max 64 characters)")
        return False
    return True

# Detect environment
IS_TERMUX = os.path.exists("/data/data/com.termux")
IS_WINDOWS = sys.platform == "win32"

# ==============================================================================
# Colors and Output
# ==============================================================================

class Colors:
    if sys.stdout.isatty() and not IS_WINDOWS:
        GREEN = '\033[92m'
        RED = '\033[91m'
        YELLOW = '\033[93m'
        BLUE = '\033[94m'
        CYAN = '\033[96m'
        BOLD = '\033[1m'
        RESET = '\033[0m'
    else:
        GREEN = RED = YELLOW = BLUE = CYAN = BOLD = RESET = ''

def print_header(text: str):
    print()
    print(f"{Colors.CYAN}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}{text.center(70)}{Colors.RESET}")
    print(f"{Colors.CYAN}{'=' * 70}{Colors.RESET}")
    print()

def print_success(text: str):
    print(f"{Colors.GREEN}[OK] {text}{Colors.RESET}")

def print_error(text: str):
    print(f"{Colors.RED}[ERROR] {text}{Colors.RESET}")

def print_warning(text: str):
    print(f"{Colors.YELLOW}[WARNING] {text}{Colors.RESET}")

def print_info(text: str):
    print(f"{Colors.CYAN}[INFO] {text}{Colors.RESET}")

def print_step(text: str):
    print(f"{Colors.BLUE}[STEP] {text}{Colors.RESET}")

# ==============================================================================
# Database Server Management
# ==============================================================================

def is_mysql_running() -> bool:
    """Check if MySQL/MariaDB server is running"""
    try:
        # Try to connect without database
        conn = mysql.connector.connect(
            host=DB_HOST,
            user="root",
            password="",
            connection_timeout=2
        )
        conn.close()
        return True
    except MySQLError:
        return False

def start_mysql_server() -> bool:
    """Attempt to start MySQL/MariaDB server"""
    print_step("Attempting to start MySQL/MariaDB server...")

    if IS_WINDOWS:
        # Windows: Try to start MySQL service
        try:
            subprocess.run(["net", "start", "MySQL"],
                         capture_output=True, check=False)
            time.sleep(3)
            return is_mysql_running()
        except Exception:
            return False

    elif IS_TERMUX:
        # Termux: Start mariadbd-safe or mysqld_safe in background
        # Use $PREFIX environment variable for proper path
        prefix = os.environ.get("PREFIX", "/data/data/com.termux/files/usr")
        datadir = f"{prefix}/var/lib/mysql"
        
        # Try multiple startup commands in order of preference
        startup_commands = [
            ["mysqld_safe", f"--datadir={datadir}"],
            ["mariadbd-safe", f"--datadir={datadir}"],
            ["mysqld_safe"],  # Try without explicit datadir
            ["mariadbd-safe"],
        ]
        
        for cmd in startup_commands:
            try:
                # Check if the command exists using shutil.which (more efficient, no subprocess)
                cmd_name = cmd[0]
                if shutil.which(cmd_name) is None:
                    continue  # Command not found, try next
                
                print_info(f"Starting with {cmd_name}...")
                subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                
                # Wait for server to start (up to 15 seconds)
                for i in range(15):
                    time.sleep(1)
                    if is_mysql_running():
                        return True
                
                # If we got here, the command ran but server didn't start
                # Try next command
            except Exception:
                continue
        
        return False

    else:
        # Linux: Try systemctl
        try:
            for service in ["mariadb", "mysql"]:
                result = subprocess.run(
                    ["sudo", "systemctl", "start", service],
                    capture_output=True,
                    check=False
                )
                if result.returncode == 0:
                    time.sleep(3)
                    if is_mysql_running():
                        return True
        except Exception:
            pass

        return False

# ==============================================================================
# Password Generation
# ==============================================================================

def generate_secure_password(length: int = 48) -> str:
    """Generate a cryptographically secure password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

# ==============================================================================
# Termux Skip-Grant-Tables Setup
# ==============================================================================

def setup_termux_with_skip_grant_tables() -> Tuple[bool, str]:
    """
    Set up MariaDB on Termux using skip-grant-tables mode.
    
    This approach:
    1. Stops any running MariaDB instance
    2. Starts MariaDB with --skip-grant-tables
    3. Creates database and user via global_priv table
    4. Restarts MariaDB normally
    
    Returns:
        Tuple of (success, db_password or error message)
    """
    print_step("Using Termux skip-grant-tables approach...")
    
    # Validate DB_NAME and DB_USER before using them
    if not _validate_identifier(DB_NAME, "database name"):
        return False, f"Invalid database name: {DB_NAME}"
    if not _validate_identifier(DB_USER, "username"):
        return False, f"Invalid username: {DB_USER}"
    
    prefix = os.environ.get("PREFIX", "/data/data/com.termux/files/usr")
    datadir = f"{prefix}/var/lib/mysql"
    
    # Generate password for bot user
    db_password = generate_secure_password()
    
    try:
        # Step 1: Stop any running MariaDB
        print_info("Stopping any running MariaDB instance...")
        subprocess.run(["pkill", "-9", "-f", "mariadbd"], 
                      capture_output=True, check=False)
        subprocess.run(["pkill", "-9", "-f", "mysqld"], 
                      capture_output=True, check=False)
        time.sleep(2)
        
        # Step 2: Initialize database if needed
        if not os.path.exists(datadir) or not os.listdir(datadir):
            print_info("Initializing MariaDB database...")
            result = subprocess.run(["mysql_install_db"], 
                                   capture_output=True, check=False)
            if result.returncode != 0:
                # Try mariadb-install-db
                subprocess.run(["mariadb-install-db"], 
                              capture_output=True, check=False)
            time.sleep(2)
        
        # Step 3: Start MariaDB with skip-grant-tables
        print_info("Starting MariaDB with skip-grant-tables...")
        
        # Find the correct daemon command
        daemon_cmd = None
        for cmd in ["mariadbd-safe", "mysqld_safe"]:
            if shutil.which(cmd):
                daemon_cmd = cmd
                break
        
        if not daemon_cmd:
            return False, "Could not find mariadbd-safe or mysqld_safe"
        
        # Start with skip-grant-tables
        process = subprocess.Popen(
            [daemon_cmd, "--skip-grant-tables", f"--datadir={datadir}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Wait for server to start
        print_info("Waiting for server to start...")
        for i in range(15):
            time.sleep(1)
            try:
                # Try to connect without password
                test_conn = mysql.connector.connect(
                    host="localhost",
                    user="root",
                    password="",
                    connection_timeout=2
                )
                test_conn.close()
                print_success("MariaDB started with skip-grant-tables")
                break
            except MySQLError:
                continue
        else:
            return False, "Failed to start MariaDB with skip-grant-tables"
        
        # Step 4: Set up database and user via global_priv
        print_info("Setting up database and user...")
        
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            charset='utf8mb4'
        )
        cursor = conn.cursor()
        
        # Create database (DB_NAME already validated)
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
                      f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print_info(f"Database '{DB_NAME}' created")
        
        # Check what user management method to use
        # MariaDB 10.4+ uses global_priv instead of mysql.user
        cursor.execute("SHOW TABLES FROM mysql LIKE 'global_priv'")
        uses_global_priv = cursor.fetchone() is not None
        
        if uses_global_priv:
            # Use global_priv table (MariaDB 10.4+)
            print_info("Using global_priv table (MariaDB 10.4+)...")
            
            # For Termux, use mysql_native_password with empty password
            # This allows the bot to connect without a password while still being secure (localhost only)
            priv_json = f'{{"access":{MARIADB_ALL_PRIVILEGES_BITMASK},"plugin":"mysql_native_password","authentication_string":""}}'
            
            # Use parameterized query for user insertion
            # Note: MariaDB global_priv table requires specific column handling
            cursor.execute("""
                INSERT INTO mysql.global_priv (Host, User, Priv) 
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE Priv = VALUES(Priv)
            """, ('localhost', DB_USER, priv_json))
        else:
            # Use traditional mysql.user table
            print_info("Using mysql.user table (older MariaDB)...")
            
            # Drop existing user if exists
            try:
                cursor.execute(f"DROP USER IF EXISTS '{DB_USER}'@'localhost'")
            except MySQLError:
                pass
            
            # Create user (without password in skip-grant-tables mode)
            cursor.execute(f"CREATE USER '{DB_USER}'@'localhost'")
            cursor.execute(f"GRANT ALL PRIVILEGES ON `{DB_NAME}`.* TO '{DB_USER}'@'localhost'")
        
        cursor.execute("FLUSH PRIVILEGES")
        conn.commit()
        cursor.close()
        conn.close()
        
        print_success(f"User '{DB_USER}' created with full privileges")
        
        # Step 5: Restart MariaDB normally
        print_info("Restarting MariaDB without skip-grant-tables...")
        subprocess.run(["pkill", "-9", "-f", "mariadbd"], 
                      capture_output=True, check=False)
        subprocess.run(["pkill", "-9", "-f", "mysqld"], 
                      capture_output=True, check=False)
        time.sleep(2)
        
        # Start normally
        process = subprocess.Popen(
            [daemon_cmd, f"--datadir={datadir}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Wait for normal start
        for i in range(15):
            time.sleep(1)
            try:
                # Try to connect as the new user
                test_conn = mysql.connector.connect(
                    host="localhost",
                    user=DB_USER,
                    password="",  # Empty password in Termux
                    database=DB_NAME,
                    connection_timeout=2
                )
                test_conn.close()
                print_success("MariaDB restarted successfully")
                # Return empty password for Termux (no password auth)
                return True, ""
            except MySQLError:
                continue
        
        return False, "Failed to restart MariaDB normally"
        
    except Exception as e:
        print_error(f"Termux setup failed: {e}")
        return False, str(e)


# ==============================================================================
# Database Setup
# ==============================================================================

def create_database_and_user(root_password: str = "") -> Tuple[bool, str]:
    """Create database and user with secure password"""
    print_step(f"Creating database '{DB_NAME}' and user '{DB_USER}'...")

    # Generate secure password for bot user
    db_password = generate_secure_password()

    try:
        # Connect as root
        conn = mysql.connector.connect(
            host=DB_HOST,
            user="root",
            password=root_password,
            charset='utf8mb4'
        )
        cursor = conn.cursor()

        # Create database
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
                      f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print_info(f"Database '{DB_NAME}' created")

        # Drop existing user if exists
        cursor.execute(f"DROP USER IF EXISTS '{DB_USER}'@'{DB_HOST}'")

        # Create new user with password
        cursor.execute(f"CREATE USER '{DB_USER}'@'{DB_HOST}' "
                      f"IDENTIFIED BY '{db_password}'")

        # Grant privileges
        cursor.execute(f"GRANT ALL PRIVILEGES ON `{DB_NAME}`.* "
                      f"TO '{DB_USER}'@'{DB_HOST}'")
        cursor.execute("FLUSH PRIVILEGES")

        cursor.close()
        conn.close()

        print_success(f"User '{DB_USER}' created with secure password")

        return True, db_password

    except MySQLError as e:
        print_error(f"Database creation failed: {e}")
        return False, ""

# ==============================================================================
# Configuration Management
# ==============================================================================

def save_config(password: str) -> bool:
    """Save database configuration to JSON file and update .env"""
    print_step(f"Saving configuration to {CONFIG_FILE}...")

    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        # Detect socket path
        if IS_TERMUX:
            socket = "/data/data/com.termux/files/usr/var/run/mysqld/mysqld.sock"
        else:
            socket = "/var/run/mysqld/mysqld.sock"

        config = {
            "host": DB_HOST,
            "user": DB_USER,
            "password": password,
            "database": DB_NAME,
            "socket": socket,
            "charset": "utf8mb4"
        }

        # Write config file
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)

        # Set secure permissions (owner read/write only)
        CONFIG_FILE.chmod(0o600)

        print_success("Configuration saved with secure permissions (600)")
        
        # Also update .env file for compatibility with scripts
        print_step("Updating .env file with database credentials...")
        env_file = PROJECT_ROOT / ".env"
        
        # Read existing .env content
        env_lines = []
        if env_file.exists():
            with open(env_file, 'r') as f:
                env_lines = f.readlines()
        
        # Update or add database credentials
        db_vars = {
            'DB_HOST': DB_HOST,
            'DB_USER': DB_USER,
            'DB_PASS': password,
            'DB_NAME': DB_NAME
        }
        
        # Track which variables were updated
        updated_vars = set()
        
        # Update existing lines in a single pass
        for i, line in enumerate(env_lines):
            stripped = line.strip()
            # Skip comments and empty lines
            if not stripped or stripped.startswith('#'):
                continue
            
            # Check if this line sets a DB variable using startswith check
            # Split on first '=' to get variable name
            if '=' in stripped:
                var_name = stripped.split('=', 1)[0]
                if var_name in db_vars:
                    # Update this line
                    env_lines[i] = f'{var_name}={db_vars[var_name]}\n'
                    updated_vars.add(var_name)
        
        # Add any variables that weren't in the file
        for var_name, var_value in db_vars.items():
            if var_name not in updated_vars:
                env_lines.append(f'{var_name}={var_value}\n')
        
        # Write back to .env
        with open(env_file, 'w') as f:
            f.writelines(env_lines)
        
        # Set secure permissions on .env
        env_file.chmod(0o600)
        
        print_success(".env file updated with database credentials")
        return True

    except Exception as e:
        print_error(f"Failed to save configuration: {e}")
        return False

def test_connection() -> bool:
    """Test database connection with saved credentials"""
    print_step("Testing database connection...")

    try:
        if not CONFIG_FILE.exists():
            print_error("Configuration file not found")
            return False

        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)

        conn = mysql.connector.connect(
            host=config['host'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            charset=config.get('charset', 'utf8mb4')
        )

        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        conn.close()

        print_success("Database connection successful")
        return True

    except Exception as e:
        print_error(f"Connection test failed: {e}")
        return False

# ==============================================================================
# Migration Management
# ==============================================================================

def parse_sql_statements(sql_content: str) -> List[str]:
    """
    Parse SQL content into individual statements, properly handling DELIMITER blocks.
    
    This handles stored procedures that use custom delimiters like $$ or //.
    """
    statements = []
    current_statement = []
    in_delimiter_block = False
    custom_delimiter = '$$'  # Default custom delimiter
    
    for line in sql_content.split('\n'):
        stripped = line.strip()
        upper_stripped = stripped.upper()
        
        # Handle DELIMITER commands
        if upper_stripped.startswith('DELIMITER'):
            parts = stripped.split()
            if len(parts) >= 2:
                new_delimiter = parts[1]
                if new_delimiter == ';':
                    # Ending delimiter block
                    in_delimiter_block = False
                else:
                    # Starting delimiter block
                    in_delimiter_block = True
                    custom_delimiter = new_delimiter
            continue
        
        # Skip empty lines and comments (but keep them in procedure bodies)
        if not in_delimiter_block:
            if not stripped or stripped.startswith('--') or stripped.startswith('#'):
                continue
            # Skip single-line multi-line comments
            if stripped.startswith('/*') and stripped.endswith('*/'):
                continue
        
        current_statement.append(line)
        
        # Check for statement end
        if in_delimiter_block:
            # In delimiter block, look for custom delimiter (e.g., $$, //)
            if stripped.endswith(custom_delimiter):
                # Remove the custom delimiter from the end
                stmt = '\n'.join(current_statement)
                stmt = stmt.rstrip()
                if stmt.endswith(custom_delimiter):
                    stmt = stmt[:-len(custom_delimiter)].rstrip()
                if stmt.strip():
                    statements.append(stmt)
                current_statement = []
        else:
            # Normal mode, look for semicolon
            if stripped.endswith(';'):
                stmt = '\n'.join(current_statement)
                if stmt.strip().rstrip(';').strip():
                    statements.append(stmt)
                current_statement = []
    
    # Handle any remaining statement
    if current_statement:
        stmt = '\n'.join(current_statement).strip()
        if stmt:
            statements.append(stmt)
    
    return statements

def run_migrations() -> bool:
    """Run all database migrations"""
    print_step("Running database migrations...")

    try:
        # Load config
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)

        # Connect to database
        conn = mysql.connector.connect(
            host=config['host'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            charset=config.get('charset', 'utf8mb4'),
            autocommit=False
        )

        cursor = conn.cursor()

        # Create migration tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                migration_name VARCHAR(255) UNIQUE NOT NULL,
                applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_migration_name (migration_name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        conn.commit()

        # Get all migration files
        migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

        if not migration_files:
            print_warning("No migration files found")
            return True

        applied_count = 0
        skipped_count = 0

        for migration_file in migration_files:
            migration_name = migration_file.name

            # Check if already applied
            cursor.execute(
                "SELECT COUNT(*) FROM schema_migrations WHERE migration_name = %s",
                (migration_name,)
            )
            if cursor.fetchone()[0] > 0:
                skipped_count += 1
                continue

            # Read and execute migration
            print_info(f"Applying: {migration_name}")

            try:
                with open(migration_file, 'r', encoding='utf-8') as f:
                    sql_content = f.read()

                # Parse SQL statements properly handling DELIMITER blocks
                statements = parse_sql_statements(sql_content)

                # Execute each statement
                for statement in statements:
                    if statement.strip():
                        try:
                            cursor.execute(statement)
                        except MySQLError as e:
                            # Ignore "already exists" errors
                            if 'already exists' not in str(e).lower():
                                raise

                # Record migration
                cursor.execute(
                    "INSERT INTO schema_migrations (migration_name) VALUES (%s)",
                    (migration_name,)
                )
                conn.commit()

                applied_count += 1
                print_success(f"Applied: {migration_name}")

            except Exception as e:
                conn.rollback()
                print_error(f"Failed to apply {migration_name}: {e}")
                cursor.close()
                conn.close()
                return False

        cursor.close()
        conn.close()

        print()
        print_success(f"Migrations complete: {applied_count} applied, {skipped_count} skipped")
        return True

    except Exception as e:
        print_error(f"Migration failed: {e}")
        return False

# ==============================================================================
# Main Setup Flow
# ==============================================================================

def main():
    """Main setup flow"""
    print_header("Sulfur Bot - Automated Database Setup")

    # Step 1: Check if already configured
    if CONFIG_FILE.exists():
        print_info(f"Configuration file found: {CONFIG_FILE}")
        if test_connection():
            print_success("Database is already configured and working!")

            # Automatically run migrations
            print()
            print_step("Running migrations automatically...")
            if run_migrations():
                print_header("[OK] Setup Complete!")
                return 0
            else:
                print_header("[ERROR] Migration Failed")
                return 1
        else:
            print_warning("Existing configuration doesn't work, reconfiguring...")
            CONFIG_FILE.unlink(missing_ok=True)

    # Step 2: Ensure MySQL is running
    print_step("Checking MySQL/MariaDB server...")
    if not is_mysql_running():
        print_warning("MySQL/MariaDB is not running")
        if not start_mysql_server():
            print_error("Failed to start MySQL/MariaDB automatically")
            print()
            print("Please start MySQL/MariaDB manually:")
            if IS_WINDOWS:
                print("  net start MySQL")
            elif IS_TERMUX:
                print("  mariadbd-safe --datadir=/data/data/com.termux/files/usr/var/lib/mysql &")
            else:
                print("  sudo systemctl start mariadb")
            print()
            return 1
        print_success("MySQL/MariaDB started successfully")
    else:
        print_success("MySQL/MariaDB is running")

    # Step 3: Try to connect with root (auto-detect password)
    print()
    print_step("Auto-detecting MySQL root credentials...")
    root_password = ""
    use_skip_grant_tables = False

    # Try empty password first (most common in dev/termux)
    try:
        test_conn = mysql.connector.connect(
            host=DB_HOST,
            user="root",
            password="",
            connection_timeout=2
        )
        test_conn.close()
        print_success("Connected with empty root password")
    except MySQLError:
        # Try common default passwords
        for pwd in ["root", "password", "mysql", "mariadb"]:
            try:
                test_conn = mysql.connector.connect(
                    host=DB_HOST,
                    user="root",
                    password=pwd,
                    connection_timeout=2
                )
                test_conn.close()
                root_password = pwd
                print_success(f"Connected with default root password")
                break
            except MySQLError:
                continue
        else:
            # Couldn't auto-detect
            if IS_TERMUX:
                # On Termux, try skip-grant-tables approach
                print_warning("Could not connect to MariaDB with root password")
                print_info("Attempting Termux skip-grant-tables setup...")
                use_skip_grant_tables = True
            else:
                # Ask user for password on other platforms
                print_warning("Could not auto-detect root password")
                print_info("Enter MySQL root password (press Enter if no password):")
                root_password = input("> ").strip()

    # Step 4: Create database and user
    print()
    
    if use_skip_grant_tables and IS_TERMUX:
        # Use special Termux approach
        success, db_password = setup_termux_with_skip_grant_tables()
    else:
        # Use standard approach
        success, db_password = create_database_and_user(root_password)
    if not success:
        print_header("[ERROR] Setup Failed")
        return 1

    # Step 5: Save configuration
    print()
    if not save_config(db_password):
        print_header("[ERROR] Setup Failed")
        return 1

    # Step 6: Test connection
    print()
    if not test_connection():
        print_header("[ERROR] Setup Failed")
        return 1

    # Step 7: Run migrations
    print()
    if not run_migrations():
        print_header("[ERROR] Setup Failed")
        return 1

    # Success!
    print_header("[OK] Database Setup Complete!")
    print()
    print(f"{Colors.BOLD}Configuration:{Colors.RESET}")
    print(f"  Database: {DB_NAME}")
    print(f"  User:     {DB_USER}")
    print(f"  Host:     {DB_HOST}")
    print(f"  Password: (stored securely in {CONFIG_FILE})")
    print()
    print(f"{Colors.BOLD}Next steps:{Colors.RESET}")
    print("  1. Start the bot: python bot.py")
    print("  2. Access dashboard: http://localhost:5000")
    print()

    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print()
        print_warning("Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print()
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
