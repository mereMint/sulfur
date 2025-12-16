"""
Secure Database Configuration Manager for Sulfur Bot

This module handles loading and validation of database credentials
from a secure configuration file with proper permission checking.

Usage:
    from modules.database_config import DatabaseConfig
    
    # Get connection parameters
    conn_params = DatabaseConfig.get_connection_params()
    conn = pymysql.connect(**conn_params)
    
    # Or load raw config
    config = DatabaseConfig.load()
"""

import json
import os
import stat
from pathlib import Path
from typing import Dict, Optional


class DatabaseConfigError(Exception):
    """Raised when there's an issue with database configuration"""
    pass


class DatabaseConfig:
    """Secure database configuration manager"""
    
    # Configuration file location
    CONFIG_FILE = "config/database.json"
    
    # Fallback to .env if config file doesn't exist
    ENABLE_ENV_FALLBACK = True
    
    @classmethod
    def load(cls) -> Dict[str, str]:
        """
        Load database configuration securely
        
        Returns:
            Dict with keys: host, user, password, database, socket, charset
            
        Raises:
            DatabaseConfigError: If config file is missing, has wrong permissions,
                                or is missing required fields
        """
        config_path = Path(cls.CONFIG_FILE)
        
        # Check if config file exists
        if not config_path.exists():
            if cls.ENABLE_ENV_FALLBACK:
                # Try to load from environment variables as fallback
                return cls._load_from_env()
            else:
                raise DatabaseConfigError(
                    f"Database config not found: {cls.CONFIG_FILE}\n"
                    f"Run: bash scripts/setup_database_secure.sh"
                )
        
        # Verify file permissions (should be 0600 - owner read/write only)
        file_stat = config_path.stat()
        file_mode = stat.S_IMODE(file_stat.st_mode)
        
        # Check if group or others can read/write/execute (security risk)
        insecure_bits = (stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP |  # Group permissions
                         stat.S_IROTH | stat.S_IWOTH | stat.S_IXOTH)   # Other permissions
        if file_mode & insecure_bits:
            raise DatabaseConfigError(
                f"Insecure permissions on {cls.CONFIG_FILE}\n"
                f"Current: {oct(file_mode)}, Expected: 0600\n"
                f"Fix: chmod 600 {cls.CONFIG_FILE}"
            )
        
        # Load JSON configuration
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            raise DatabaseConfigError(
                f"Invalid JSON in {cls.CONFIG_FILE}: {e}"
            )
        except Exception as e:
            raise DatabaseConfigError(
                f"Failed to read {cls.CONFIG_FILE}: {e}"
            )
        
        # Validate required fields
        required = ['host', 'user', 'password', 'database']
        missing = [f for f in required if f not in config]
        if missing:
            raise DatabaseConfigError(
                f"Missing required fields in {cls.CONFIG_FILE}: {', '.join(missing)}"
            )
        
        # Ensure password is a string (can be empty)
        if not isinstance(config['password'], str):
            config['password'] = str(config['password'])
        
        return config
    
    @classmethod
    def _load_from_env(cls) -> Dict[str, str]:
        """
        Load database configuration from environment variables
        This is a fallback for when config file doesn't exist yet
        
        Returns:
            Dict with database configuration
        """
        # Try to load .env file if dotenv is available
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass
        
        # Detect environment for socket path
        if os.path.exists('/data/data/com.termux') or os.environ.get('TERMUX_VERSION'):
            prefix = os.environ.get('PREFIX', '/data/data/com.termux/files/usr')
            default_socket = f"{prefix}/var/run/mysqld/mysqld.sock"
        else:
            default_socket = '/var/run/mysqld/mysqld.sock'
        
        config = {
            'host': os.environ.get('DB_HOST', 'localhost'),
            'user': os.environ.get('DB_USER', 'sulfur_bot_user'),
            'password': os.environ.get('DB_PASS', ''),
            'database': os.environ.get('DB_NAME', 'sulfur_bot'),
            'socket': os.environ.get('DB_SOCKET', default_socket),
            'charset': 'utf8mb4'
        }
        
        # Validate that we have non-empty user and database
        if not config['user']:
            raise DatabaseConfigError(
                "DB_USER environment variable is empty or not set\n"
                "Please set it in .env file or run: bash scripts/setup_database_secure.sh"
            )
        
        if not config['database']:
            raise DatabaseConfigError(
                "DB_NAME environment variable is empty or not set\n"
                "Please set it in .env file or run: bash scripts/setup_database_secure.sh"
            )
        
        return config
    
    @classmethod
    def save(cls, config: Dict[str, str]) -> None:
        """
        Save database configuration securely
        
        Args:
            config: Dictionary with database configuration
            
        Raises:
            DatabaseConfigError: If save fails
        """
        config_path = Path(cls.CONFIG_FILE)
        
        # Create directory if it doesn't exist
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write configuration
        try:
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            raise DatabaseConfigError(
                f"Failed to write {cls.CONFIG_FILE}: {e}"
            )
        
        # Set secure permissions (owner read/write only)
        try:
            config_path.chmod(0o600)
        except Exception as e:
            raise DatabaseConfigError(
                f"Failed to set permissions on {cls.CONFIG_FILE}: {e}"
            )
    
    @classmethod
    def get_connection_params(cls) -> Dict[str, str]:
        """
        Get parameters suitable for database connection
        
        Returns:
            Dict with connection parameters for mysql.connector or pymysql
            
        Usage:
            import mysql.connector
            conn = mysql.connector.connect(**DatabaseConfig.get_connection_params())
        """
        config = cls.load()
        
        # Build connection parameters
        params = {
            'host': config['host'],
            'user': config['user'],
            'password': config['password'],
            'database': config['database'],
            'charset': config.get('charset', 'utf8mb4'),
            'autocommit': True
        }
        
        # Add socket if specified and file exists
        if 'socket' in config and os.path.exists(config['socket']):
            params['unix_socket'] = config['socket']
        
        return params
    
    @classmethod
    def is_configured(cls) -> bool:
        """
        Check if database is configured
        
        Returns:
            True if config file exists and is valid, False otherwise
        """
        try:
            cls.load()
            return True
        except DatabaseConfigError:
            return False
    
    @classmethod
    def get_safe_display_config(cls) -> Dict[str, str]:
        """
        Get configuration with password masked for safe display
        
        Returns:
            Dict with password masked as '***'
        """
        try:
            config = cls.load()
            safe_config = config.copy()
            if safe_config.get('password'):
                safe_config['password'] = '***'
            return safe_config
        except DatabaseConfigError:
            return {}


# Convenience function for backward compatibility
def get_connection_params():
    """Get database connection parameters - convenience wrapper"""
    return DatabaseConfig.get_connection_params()


# For testing/debugging
if __name__ == "__main__":
    try:
        config = DatabaseConfig.load()
        print("✓ Configuration loaded successfully")
        print(f"  Database: {config['database']}")
        print(f"  User: {config['user']}")
        print(f"  Host: {config['host']}")
        print(f"  Password: {'(set)' if config['password'] else '(empty)'}")
    except DatabaseConfigError as e:
        print(f"✗ Configuration error: {e}")
