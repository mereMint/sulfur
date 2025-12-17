"""
Centralized logging utility for the Sulfur Bot project.
Provides consistent, structured logging across all components.
"""
import logging
import sys
from datetime import datetime
from pathlib import Path

# Color codes for terminal output
class LogColors:
    RESET = '\033[0m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    GRAY = '\033[90m'

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels"""
    
    COLORS = {
        'DEBUG': LogColors.GRAY,
        'INFO': LogColors.BLUE,
        'WARNING': LogColors.YELLOW,
        'ERROR': LogColors.RED,
        'CRITICAL': LogColors.MAGENTA
    }
    
    def format(self, record):
        # Add color to level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{LogColors.RESET}"
        return super().format(record)

def setup_logger(name, log_file=None, level=logging.INFO):
    """
    Set up a logger with consistent formatting.
    
    Args:
        name: Logger name (typically module name)
        log_file: Optional file path for file logging
        level: Logging level (default: INFO)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_format = ColoredFormatter(
        '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        # Create logs directory if it doesn't exist
        log_dir = Path(log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_format = logging.Formatter(
            '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    
    return logger

def log_function_call(logger, func_name, **kwargs):
    """Log a function call with its parameters"""
    params = ', '.join(f"{k}={v}" for k, v in kwargs.items())
    logger.debug(f"→ {func_name}({params})")

def log_database_operation(logger, operation, table, success=True, error=None):
    """Log database operations with consistent format"""
    if success:
        logger.debug(f"[DB] {operation} on {table}: SUCCESS")
    else:
        logger.error(f"[DB] {operation} on {table}: FAILED - {error}")

def log_api_call(logger, provider, model, success=True, error=None, tokens=None):
    """Log API calls with consistent format"""
    if success:
        token_info = f" (tokens: {tokens})" if tokens else ""
        logger.info(f"[API] {provider}/{model}: SUCCESS{token_info}")
    else:
        logger.error(f"[API] {provider}/{model}: FAILED - {error}")

def log_discord_event(logger, event_name, details=None):
    """Log Discord events with consistent format"""
    detail_str = f": {details}" if details else ""
    logger.info(f"[Discord] {event_name}{detail_str}")

def log_error_with_context(logger, error, context):
    """
    Log an error with full context information.
    
    Args:
        logger: Logger instance
        error: Exception object
        context: Dictionary with context information
    """
    logger.error(f"Error occurred: {type(error).__name__}: {str(error)}")
    for key, value in context.items():
        logger.error(f"  Context - {key}: {value}")
    
    # Log traceback if available
    import traceback
    logger.error(f"Traceback:\n{traceback.format_exc()}")

# Create default loggers for each component with file output
# Generate session-based log file names
session_timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

# Create separate log files for bot, web, and general session
bot_log_file = f'logs/bot_{session_timestamp}.log'
web_log_file = f'logs/web_{session_timestamp}.log'
session_log_file = f'logs/session_{session_timestamp}.log'
minecraft_log_file = f'logs/minecraft_{session_timestamp}.log'
vpn_log_file = f'logs/vpn_{session_timestamp}.log'

bot_logger = setup_logger('Bot', log_file=bot_log_file)
db_logger = setup_logger('Database', log_file=bot_log_file)  # DB logs go to bot log
api_logger = setup_logger('API', log_file=bot_log_file)  # API logs go to bot log
web_logger = setup_logger('WebDashboard', log_file=web_log_file)
voice_logger = setup_logger('VoiceManager', log_file=bot_log_file)
game_logger = setup_logger('WerwolfGame', log_file=bot_log_file)
minecraft_logger = setup_logger('Minecraft', log_file=minecraft_log_file)
vpn_logger = setup_logger('VPN', log_file=vpn_log_file)
