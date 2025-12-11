"""
Autonomous Behavior Module for Sulfur Bot

This module enables the bot to autonomously initiate interactions with users,
including sending DMs, making voice calls, and other proactive behaviors.
"""

import asyncio
import random
from datetime import datetime, timedelta
import discord
from typing import Optional, List, Dict, Any

from modules.logger_utils import bot_logger as logger
from modules.db_helpers import get_db_connection


# --- User Preference Functions ---

async def get_user_autonomous_settings(user_id: int) -> Dict[str, Any]:
    """Get user's autonomous behavior settings."""
    async with get_db_connection() as (conn, cursor):
        await cursor.execute("""
            SELECT allow_autonomous_messages, allow_autonomous_calls, 
                   last_autonomous_contact, autonomous_contact_frequency
            FROM user_autonomous_settings
            WHERE user_id = %s
        """, (user_id,))
        result = await cursor.fetchone()
        
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


async def update_user_autonomous_settings(
    user_id: int,
    allow_messages: Optional[bool] = None,
    allow_calls: Optional[bool] = None,
    frequency: Optional[str] = None
) -> bool:
    """Update user's autonomous behavior settings."""
    try:
        async with get_db_connection() as (conn, cursor):
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
            
            await cursor.execute(query, insert_params)
            await conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error updating autonomous settings for user {user_id}: {e}")
        return False


async def record_autonomous_contact(user_id: int):
    """Record that the bot has autonomously contacted a user."""
    try:
        async with get_db_connection() as (conn, cursor):
            await cursor.execute("""
                UPDATE user_autonomous_settings
                SET last_autonomous_contact = CURRENT_TIMESTAMP
                WHERE user_id = %s
            """, (user_id,))
            await conn.commit()
    except Exception as e:
        logger.error(f"Error recording autonomous contact for user {user_id}: {e}")


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
    try:
        async with get_db_connection() as (conn, cursor):
            import json
            await cursor.execute("""
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
            await conn.commit()
            return cursor.lastrowid
    except Exception as e:
        logger.error(f"Error logging autonomous action: {e}")
        return 0


async def update_action_response(action_id: int, user_responded: bool):
    """Update whether user responded to an autonomous action."""
    try:
        async with get_db_connection() as (conn, cursor):
            await cursor.execute("""
                UPDATE bot_autonomous_actions
                SET user_response = %s
                WHERE id = %s
            """, (user_responded, action_id))
            await conn.commit()
    except Exception as e:
        logger.error(f"Error updating action response: {e}")


# --- Decision Making ---

async def should_contact_user(user_id: int, member: discord.Member) -> bool:
    """
    Determine if the bot should autonomously contact a user.
    
    Returns True if:
    - User allows autonomous contact
    - Enough time has passed since last contact
    - User is currently online or was recently active
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
    
    # Check last contact time
    last_contact = settings['last_contact']
    if last_contact:
        time_since_contact = datetime.now() - last_contact
        if time_since_contact < timedelta(hours=cooldown_hours):
            return False
    
    # Check if user is online or was recently online
    if member.status == discord.Status.offline:
        return False
    
    return True


async def get_conversation_context(user_id: int, limit: int = 10) -> List[Dict]:
    """Get recent conversation context for a user."""
    try:
        async with get_db_connection() as (conn, cursor):
            await cursor.execute("""
                SELECT user_id, message, timestamp
                FROM chat_history
                WHERE user_id = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """, (user_id, limit))
            
            rows = await cursor.fetchall()
            return [
                {
                    'user_id': row[0],
                    'message': row[1],
                    'timestamp': row[2]
                }
                for row in rows
            ]
    except Exception as e:
        logger.error(f"Error getting conversation context: {e}")
        return []


async def generate_conversation_starter(
    user: discord.User,
    context: List[Dict],
    get_chat_response_func
) -> Optional[str]:
    """
    Generate a natural conversation starter using AI.
    
    Args:
        user: Discord user to message
        context: Recent conversation history
        get_chat_response_func: Function to call AI API
    """
    try:
        # Build context summary
        if context:
            recent_topics = "\n".join([
                f"- {msg['message'][:100]}"
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
        
        response = await get_chat_response_func(
            prompt=prompt,
            user_id=user.id,
            username=user.display_name
        )
        
        if response:
            # Clean up the response
            message = response.strip().strip('"').strip("'")
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
    try:
        import json
        async with get_db_connection() as (conn, cursor):
            # Get current memory
            await cursor.execute("""
                SELECT interests, usual_active_times, conversation_topics
                FROM user_memory_enhanced
                WHERE user_id = %s
            """, (user_id,))
            
            result = await cursor.fetchone()
            
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
            await cursor.execute("""
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
            await conn.commit()
    except Exception as e:
        logger.error(f"Error updating user memory: {e}")


async def get_user_memory(user_id: int) -> Dict[str, Any]:
    """Get enhanced memory data for a user."""
    try:
        import json
        async with get_db_connection() as (conn, cursor):
            await cursor.execute("""
                SELECT interests, usual_active_times, conversation_topics,
                       last_significant_interaction, interaction_frequency,
                       preferred_contact_method
                FROM user_memory_enhanced
                WHERE user_id = %s
            """, (user_id,))
            
            result = await cursor.fetchone()
            
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
