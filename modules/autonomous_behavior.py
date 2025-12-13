"""
Autonomous Behavior Module for Sulfur Bot

This module enables the bot to autonomously initiate interactions with users,
including sending DMs, making voice calls, and other proactive behaviors.
"""

import asyncio
import json
import random
from datetime import datetime, timedelta
import discord
from typing import Optional, List, Dict, Any

from modules.logger_utils import bot_logger as logger
from modules.db_helpers import get_db_connection


# --- User Preference Functions ---

async def get_user_autonomous_settings(user_id: int) -> Dict[str, Any]:
    """Get user's autonomous behavior settings."""
    conn = get_db_connection()
    if not conn:
        # Default settings if database unavailable
        return {
            'allow_messages': True,
            'allow_calls': True,
            'last_contact': None,
            'frequency': 'normal'
        }
    
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT allow_autonomous_messages, allow_autonomous_calls, 
                   last_autonomous_contact, autonomous_contact_frequency
            FROM user_autonomous_settings
            WHERE user_id = %s
        """, (user_id,))
        result = cursor.fetchone()
        
        if result:
            return {
                'allow_messages': bool(result[0]),
                'allow_calls': bool(result[1]),
                'last_contact': result[2],
                'frequency': result[3]
            }
        
        # Default settings if not found
        return {
            'allow_messages': True,
            'allow_calls': True,
            'last_contact': None,
            'frequency': 'normal'
        }
    finally:
        cursor.close()
        conn.close()


async def update_user_autonomous_settings(
    user_id: int,
    allow_messages: Optional[bool] = None,
    allow_calls: Optional[bool] = None,
    frequency: Optional[str] = None
) -> bool:
    """Update user's autonomous behavior settings."""
    conn = get_db_connection()
    if not conn:
        logger.error(f"Could not connect to database to update autonomous settings for user {user_id}")
        return False
    
    cursor = conn.cursor()
    try:
        # Build update query dynamically
        updates = []
        params = []
        
        if allow_messages is not None:
            updates.append("allow_autonomous_messages = %s")
            params.append(allow_messages)
        
        if allow_calls is not None:
            updates.append("allow_autonomous_calls = %s")
            params.append(allow_calls)
        
        if frequency is not None:
            updates.append("autonomous_contact_frequency = %s")
            params.append(frequency)
        
        if not updates:
            return False
        
        params.append(user_id)
        query = f"""
            INSERT INTO user_autonomous_settings 
            (user_id, allow_autonomous_messages, allow_autonomous_calls, autonomous_contact_frequency)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE {', '.join(updates)}
        """
        
        # For INSERT, need all values
        insert_params = [
            user_id,
            allow_messages if allow_messages is not None else True,
            allow_calls if allow_calls is not None else True,
            frequency if frequency is not None else 'normal'
        ]
        
        cursor.execute(query, insert_params)
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error updating autonomous settings for user {user_id}: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


async def record_autonomous_contact(user_id: int):
    """Record that the bot has autonomously contacted a user."""
    conn = get_db_connection()
    if not conn:
        logger.error(f"Could not connect to database to record autonomous contact for user {user_id}")
        return
    
    cursor = conn.cursor()
    try:
        # Use INSERT...ON DUPLICATE KEY UPDATE to ensure record exists
        # This prevents the bug where UPDATE does nothing if no row exists
        cursor.execute("""
            INSERT INTO user_autonomous_settings 
            (user_id, last_autonomous_contact, allow_autonomous_messages, allow_autonomous_calls, autonomous_contact_frequency)
            VALUES (%s, CURRENT_TIMESTAMP, TRUE, TRUE, 'normal')
            ON DUPLICATE KEY UPDATE 
                last_autonomous_contact = CURRENT_TIMESTAMP
        """, (user_id,))
        conn.commit()
        logger.debug(f"Recorded autonomous contact for user {user_id}")
    except Exception as e:
        logger.error(f"Error recording autonomous contact for user {user_id}: {e}")
    finally:
        cursor.close()
        conn.close()


async def grant_temp_dm_access(user_id: int, duration_hours: int = 1):
    """
    Grant temporary DM access to a user for a specified duration.
    
    This is used when the bot autonomously messages a user, allowing them
    to reply without needing the DM access premium feature.
    
    Args:
        user_id: Discord user ID
        duration_hours: How long to grant access (default: 1 hour)
    """
    conn = get_db_connection()
    if not conn:
        logger.error(f"Could not connect to database to grant temp DM access for user {user_id}")
        return
    
    cursor = conn.cursor()
    try:
        expires_at = datetime.now() + timedelta(hours=duration_hours)
        cursor.execute("""
            INSERT INTO temp_dm_access (user_id, expires_at)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE 
                expires_at = VALUES(expires_at),
                granted_at = CURRENT_TIMESTAMP
        """, (user_id, expires_at))
        conn.commit()
        logger.info(f"Granted temporary DM access to user {user_id} for {duration_hours} hour(s)")
    except Exception as e:
        logger.error(f"Error granting temporary DM access to user {user_id}: {e}")
    finally:
        cursor.close()
        conn.close()


async def has_temp_dm_access(user_id: int) -> bool:
    """
    Check if a user has temporary DM access.
    
    Returns True if the user has unexpired temporary access.
    Also cleans up expired access automatically.
    """
    conn = get_db_connection()
    if not conn:
        logger.error(f"Could not connect to database to check temp DM access for user {user_id}")
        return False
    
    cursor = conn.cursor()
    try:
        # Check for valid temp access
        cursor.execute("""
            SELECT user_id 
            FROM temp_dm_access 
            WHERE user_id = %s AND expires_at > NOW()
        """, (user_id,))
        result = cursor.fetchone()
        
        has_access = result is not None
        
        # Clean up expired access for this user if found
        if not has_access:
            cursor.execute("""
                DELETE FROM temp_dm_access 
                WHERE user_id = %s AND expires_at <= NOW()
            """, (user_id,))
            conn.commit()
        
        return has_access
    except Exception as e:
        logger.error(f"Error checking temporary DM access for user {user_id}: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


async def cleanup_expired_temp_dm_access():
    """Clean up all expired temporary DM access entries."""
    conn = get_db_connection()
    if not conn:
        logger.error("Could not connect to database to cleanup expired temp DM access")
        return 0
    
    cursor = conn.cursor()
    try:
        cursor.execute("""
            DELETE FROM temp_dm_access 
            WHERE expires_at <= NOW()
        """)
        deleted = cursor.rowcount
        conn.commit()
        
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} expired temporary DM access entries")
        
        return deleted
    except Exception as e:
        logger.error(f"Error cleaning up expired temp DM access: {e}")
        return 0
    finally:
        cursor.close()
        conn.close()


# --- Action Logging ---

async def log_autonomous_action(
    action_type: str,
    target_user_id: int,
    guild_id: Optional[int] = None,
    action_reason: Optional[str] = None,
    context_data: Optional[Dict] = None,
    success: bool = True
) -> int:
    """Log an autonomous action taken by the bot."""
    conn = get_db_connection()
    if not conn:
        logger.error("Could not connect to database to log autonomous action")
        return 0
    
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO bot_autonomous_actions
            (action_type, target_user_id, guild_id, action_reason, context_data, success)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            action_type,
            target_user_id,
            guild_id,
            action_reason,
            json.dumps(context_data) if context_data else None,
            success
        ))
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        logger.error(f"Error logging autonomous action: {e}")
        return 0
    finally:
        cursor.close()
        conn.close()


async def update_action_response(action_id: int, user_responded: bool):
    """Update whether user responded to an autonomous action."""
    conn = get_db_connection()
    if not conn:
        logger.error(f"Could not connect to database to update action response for action {action_id}")
        return
    
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE bot_autonomous_actions
            SET user_response = %s
            WHERE id = %s
        """, (user_responded, action_id))
        conn.commit()
    except Exception as e:
        logger.error(f"Error updating action response: {e}")
    finally:
        cursor.close()
        conn.close()


# --- Decision Making ---

async def should_contact_user(user_id: int, member: discord.Member, min_cooldown_hours: int = 1) -> bool:
    """
    Determine if the bot should autonomously contact a user.
    
    Returns True if:
    - User allows autonomous contact
    - Enough time has passed since last contact (minimum 1 hour)
    - User is currently online or was recently active
    
    Args:
        user_id: Discord user ID
        member: Discord member object
        min_cooldown_hours: Minimum hours to wait between ANY contact (default: 1 hour)
    """
    settings = await get_user_autonomous_settings(user_id)
    
    # Check if user allows autonomous messages
    if not settings['allow_messages']:
        return False
    
    # Check frequency settings
    frequency = settings['frequency']
    if frequency == 'none':
        return False
    
    # Calculate cooldown based on frequency
    cooldown_hours = {
        'low': 72,      # 3 days
        'normal': 24,   # 1 day
        'high': 8       # 8 hours
    }.get(frequency, 24)
    
    # Check last contact time with minimum cooldown
    # The bot will ALWAYS wait at least min_cooldown_hours (default 1 hour)
    # regardless of frequency settings
    last_contact = settings['last_contact']
    if last_contact:
        time_since_contact = datetime.now() - last_contact
        
        # Enforce minimum cooldown (e.g., 1 hour) to prevent spam
        if time_since_contact < timedelta(hours=min_cooldown_hours):
            return False
        
        # Then check the frequency-based cooldown
        if time_since_contact < timedelta(hours=cooldown_hours):
            return False
    
    # Check if user is online or was recently online
    if member.status == discord.Status.offline:
        return False
    
    return True


async def get_conversation_context(user_id: int, limit: int = 10) -> List[Dict]:
    """Get recent conversation context for a user."""
    conn = get_db_connection()
    if not conn:
        logger.error(f"Could not connect to database to get conversation context for user {user_id}")
        return []
    
    cursor = conn.cursor()
    try:
        # Note: chat_history table doesn't have user_id, we get the context from DM channel
        # For autonomous messaging, we might not have history yet, so this is acceptable
        cursor.execute("""
            SELECT channel_id, role, content, created_at
            FROM chat_history
            WHERE channel_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (user_id, limit))  # Using user_id as channel_id for DMs
        
        rows = cursor.fetchall()
        return [
            {
                'channel_id': row[0],
                'role': row[1],
                'message': row[2],
                'timestamp': row[3]
            }
            for row in rows
        ]
    except Exception as e:
        logger.error(f"Error getting conversation context: {e}")
        return []
    finally:
        cursor.close()
        conn.close()


async def generate_conversation_starter(
    user: discord.User,
    context: List[Dict],
    get_chat_response_func,
    system_prompt: str = None,
    config: dict = None,
    gemini_key: str = None,
    openai_key: str = None
) -> Optional[str]:
    """
    Generate a natural conversation starter using AI.
    
    Args:
        user: Discord user to message
        context: Recent conversation history
        get_chat_response_func: Function to call AI API
        system_prompt: System prompt for AI
        config: Bot configuration
        gemini_key: Gemini API key
        openai_key: OpenAI API key
    """
    try:
        # Build context summary
        if context:
            recent_topics = "\n".join([
                f"- {msg.get('message', '')[:100]}"
                for msg in context[:3]
            ])
        else:
            recent_topics = "No recent conversation history"
        
        prompt = f"""You are Sulfur, an autonomous Discord bot. You want to naturally reach out to {user.display_name}.

Recent conversation topics:
{recent_topics}

Generate a brief, friendly, and natural message to start a conversation. The message should:
- Be casual and friendly
- Reference something from recent conversations if available
- Ask an open-ended question or share something interesting
- Be 1-2 sentences max
- Feel genuine, not forced

Message:"""
        
        # Use provided system prompt or default
        if not system_prompt:
            system_prompt = "You are Sulfur, a friendly and autonomous Discord bot."
        
        # Use provided config or minimal default
        if not config:
            config = {'api': {'provider': 'gemini', 'timeout': 30}}
        
        response = await get_chat_response_func(
            history=[],  # No history for autonomous starter
            user_prompt=prompt,
            user_display_name=user.display_name,
            system_prompt=system_prompt,
            config=config,
            gemini_key=gemini_key,
            openai_key=openai_key
        )
        
        if response:
            # Response might be a tuple (text, error, metadata) or just text
            if isinstance(response, tuple):
                message = response[0]  # Get text from tuple
            else:
                message = response
            
            # Clean up the response
            if message:
                message = message.strip().strip('"').strip("'")
                return message
        
        return None
    except Exception as e:
        logger.error(f"Error generating conversation starter: {e}")
        return None


# --- Enhanced Memory Functions ---

async def update_user_memory(
    user_id: int,
    interests: Optional[List[str]] = None,
    active_times: Optional[List[int]] = None,
    topics: Optional[List[str]] = None
):
    """Update enhanced user memory for better autonomous decisions."""
    conn = get_db_connection()
    if not conn:
        logger.error(f"Could not connect to database to update user memory for user {user_id}")
        return
    
    cursor = conn.cursor()
    try:
        # Get current memory
        cursor.execute("""
            SELECT interests, usual_active_times, conversation_topics
            FROM user_memory_enhanced
            WHERE user_id = %s
        """, (user_id,))
        
        result = cursor.fetchone()
        
        if result:
            current_interests = json.loads(result[0]) if result[0] else []
            current_times = json.loads(result[1]) if result[1] else []
            current_topics = json.loads(result[2]) if result[2] else []
        else:
            current_interests = []
            current_times = []
            current_topics = []
        
        # Merge new data
        if interests:
            current_interests = list(set(current_interests + interests))[-20:]  # Keep last 20
        
        if active_times:
            current_times = list(set(current_times + active_times))[-24:]  # Keep last 24 hours
        
        if topics:
            current_topics = list(set(topics + current_topics))[:30]  # Keep most recent 30
        
        # Update database
        cursor.execute("""
            INSERT INTO user_memory_enhanced
            (user_id, interests, usual_active_times, conversation_topics, last_significant_interaction)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON DUPLICATE KEY UPDATE
                interests = VALUES(interests),
                usual_active_times = VALUES(usual_active_times),
                conversation_topics = VALUES(conversation_topics),
                last_significant_interaction = CURRENT_TIMESTAMP
        """, (
            user_id,
            json.dumps(current_interests),
            json.dumps(current_times),
            json.dumps(current_topics)
        ))
        conn.commit()
    except Exception as e:
        logger.error(f"Error updating user memory: {e}")
    finally:
        cursor.close()
        conn.close()


async def get_user_memory(user_id: int) -> Dict[str, Any]:
    """Get enhanced memory data for a user."""
    conn = get_db_connection()
    if not conn:
        logger.error(f"Could not connect to database to get user memory for user {user_id}")
        return {
            'interests': [],
            'active_times': [],
            'topics': [],
            'last_interaction': None,
            'frequency': 0.0,
            'preferred_method': 'text'
        }
    
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT interests, usual_active_times, conversation_topics,
                   last_significant_interaction, interaction_frequency,
                   preferred_contact_method
            FROM user_memory_enhanced
            WHERE user_id = %s
        """, (user_id,))
        
        result = cursor.fetchone()
        
        if result:
            return {
                'interests': json.loads(result[0]) if result[0] else [],
                'active_times': json.loads(result[1]) if result[1] else [],
                'topics': json.loads(result[2]) if result[2] else [],
                'last_interaction': result[3],
                'frequency': result[4],
                'preferred_method': result[5]
            }
        
        return {
            'interests': [],
            'active_times': [],
            'topics': [],
            'last_interaction': None,
            'frequency': 0.0,
            'preferred_method': 'text'
        }
    except Exception as e:
        logger.error(f"Error getting user memory: {e}")
        return {}
    finally:
        cursor.close()
        conn.close()
