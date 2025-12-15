"""
Autonomous Behavior Module - Autonomous bot features for user interactions

This module provides autonomous behavior features that allow the bot to
initiate conversations, make calls, and interact with users based on
its own decision-making, like the Neuro-sama AI.
"""

from modules.logger_utils import bot_logger as logger
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

# In-memory store for temporary DM access (user_id -> expiry timestamp)
_temp_dm_access: Dict[int, datetime] = {}

# In-memory store for user settings (would be database in production)
# Format: {user_id: {'allow_messages': bool, 'allow_calls': bool, 'frequency': str, 'last_contact': datetime}}
_user_settings: Dict[int, Dict[str, Any]] = {}

# Default frequency options
FREQUENCY_OPTIONS = {
    'none': timedelta(days=365),  # Never (effectively)
    'low': timedelta(days=3),      # Every 3 days
    'normal': timedelta(days=1),   # Daily
    'high': timedelta(hours=8)     # Every 8 hours
}


async def has_temp_dm_access(user_id: int) -> bool:
    """
    Check if a user has temporary DM access (e.g., after bot initiated conversation).
    
    Args:
        user_id: Discord user ID
    
    Returns:
        True if user has temporary access, False otherwise
    """
    if user_id not in _temp_dm_access:
        return False
    
    expiry = _temp_dm_access[user_id]
    now = datetime.now(timezone.utc)
    
    if now > expiry:
        # Access expired, remove it
        del _temp_dm_access[user_id]
        return False
    
    return True


async def grant_temp_dm_access(user_id: int, duration_minutes: int = 30):
    """
    Grant temporary DM access to a user.
    
    Args:
        user_id: Discord user ID
        duration_minutes: How long the access should last
    """
    expiry = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)
    _temp_dm_access[user_id] = expiry
    logger.info(f"Granted temporary DM access to user {user_id} for {duration_minutes} minutes")


async def get_user_autonomous_settings(user_id: int) -> dict:
    """
    Get user's autonomous behavior settings.
    
    Args:
        user_id: Discord user ID
    
    Returns:
        Dictionary with user settings including:
        - allow_messages: bool - Whether bot can send autonomous messages
        - allow_calls: bool - Whether bot can make voice calls
        - frequency: str - Contact frequency ('none', 'low', 'normal', 'high')
        - last_contact: datetime - Last time bot autonomously contacted user
        - dm_enabled: bool - Alias for allow_messages (backward compatibility)
        - voice_call_enabled: bool - Alias for allow_calls (backward compatibility)
        - notifications_enabled: bool - Whether notifications are enabled
        - quiet_hours_start: int - Start hour for quiet hours (None for disabled)
        - quiet_hours_end: int - End hour for quiet hours (None for disabled)
    """
    if user_id in _user_settings:
        settings = _user_settings[user_id].copy()
    else:
        # Default settings - enabled by default for opt-out model
        settings = {
            'allow_messages': True,
            'allow_calls': False,  # Calls disabled by default
            'frequency': 'normal',
            'last_contact': None,
            'quiet_hours_start': None,
            'quiet_hours_end': None
        }
    
    # Add backward compatibility aliases
    settings['dm_enabled'] = settings.get('allow_messages', True)
    settings['voice_call_enabled'] = settings.get('allow_calls', False)
    settings['notifications_enabled'] = True
    
    return settings


async def update_user_autonomous_settings(
    user_id: int, 
    allow_messages: Optional[bool] = None,
    allow_calls: Optional[bool] = None,
    frequency: Optional[str] = None,
    quiet_hours_start: Optional[int] = None,
    quiet_hours_end: Optional[int] = None
) -> bool:
    """
    Update autonomous behavior settings for a user.
    
    Args:
        user_id: Discord user ID
        allow_messages: Whether bot can send autonomous messages
        allow_calls: Whether bot can make voice calls
        frequency: Contact frequency ('none', 'low', 'normal', 'high')
        quiet_hours_start: Start hour for quiet hours (0-23)
        quiet_hours_end: End hour for quiet hours (0-23)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        if user_id not in _user_settings:
            _user_settings[user_id] = {
                'allow_messages': True,
                'allow_calls': False,
                'frequency': 'normal',
                'last_contact': None,
                'quiet_hours_start': None,
                'quiet_hours_end': None
            }
        
        if allow_messages is not None:
            _user_settings[user_id]['allow_messages'] = allow_messages
            logger.info(f"Updated allow_messages={allow_messages} for user {user_id}")
        
        if allow_calls is not None:
            _user_settings[user_id]['allow_calls'] = allow_calls
            logger.info(f"Updated allow_calls={allow_calls} for user {user_id}")
        
        if frequency is not None and frequency in FREQUENCY_OPTIONS:
            _user_settings[user_id]['frequency'] = frequency
            logger.info(f"Updated frequency={frequency} for user {user_id}")
        
        if quiet_hours_start is not None:
            _user_settings[user_id]['quiet_hours_start'] = quiet_hours_start
        
        if quiet_hours_end is not None:
            _user_settings[user_id]['quiet_hours_end'] = quiet_hours_end
        
        return True
        
    except Exception as e:
        logger.error(f"Error updating autonomous settings for user {user_id}: {e}")
        return False


async def record_contact(user_id: int):
    """
    Record that the bot has autonomously contacted a user.
    
    Args:
        user_id: Discord user ID
    """
    if user_id not in _user_settings:
        _user_settings[user_id] = {
            'allow_messages': True,
            'allow_calls': False,
            'frequency': 'normal',
            'last_contact': None,
            'quiet_hours_start': None,
            'quiet_hours_end': None
        }
    
    _user_settings[user_id]['last_contact'] = datetime.now(timezone.utc)
    logger.debug(f"Recorded autonomous contact with user {user_id}")


async def can_contact_user(user_id: int) -> bool:
    """
    Check if the bot can autonomously contact a user based on their settings
    and last contact time.
    
    Args:
        user_id: Discord user ID
    
    Returns:
        True if bot can contact user, False otherwise
    """
    settings = await get_user_autonomous_settings(user_id)
    
    # Check if messages are allowed
    if not settings.get('allow_messages', True):
        return False
    
    # Check frequency
    frequency = settings.get('frequency', 'normal')
    if frequency == 'none':
        return False
    
    # Check last contact
    last_contact = settings.get('last_contact')
    if last_contact:
        cooldown = FREQUENCY_OPTIONS.get(frequency, timedelta(days=1))
        next_allowed = last_contact + cooldown
        if datetime.now(timezone.utc) < next_allowed:
            return False
    
    # Check quiet hours
    quiet_start = settings.get('quiet_hours_start')
    quiet_end = settings.get('quiet_hours_end')
    if quiet_start is not None and quiet_end is not None:
        current_hour = datetime.now(timezone.utc).hour
        if quiet_start <= current_hour < quiet_end:
            return False
    
    return True


async def cleanup_expired_temp_access():
    """
    Clean up expired temporary DM access entries.
    Called periodically by maintenance tasks.
    """
    now = datetime.now(timezone.utc)
    expired_users = [uid for uid, expiry in _temp_dm_access.items() if now > expiry]
    
    for uid in expired_users:
        del _temp_dm_access[uid]
    
    if expired_users:
        logger.debug(f"Cleaned up {len(expired_users)} expired temporary DM access entries")
