"""
Focus Timer Module for Sulfur Bot

Implements Pomodoro and custom timers with activity monitoring
to help users stay focused on their tasks.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import discord

from modules.logger_utils import bot_logger as logger
from modules.db_helpers import get_db_connection


# Active focus sessions (in-memory)
active_sessions: Dict[int, Dict[str, Any]] = {}


# --- Focus Session Management ---

async def start_focus_session(
    user_id: int,
    guild_id: int,
    session_type: str,
    duration_minutes: int
) -> Optional[int]:
    """Start a new focus session for a user."""
    try:
        # Check if user already has an active session
        if user_id in active_sessions:
            return None
        
        async with get_db_connection() as (conn, cursor):
            await cursor.execute("""
                INSERT INTO focus_sessions
                (user_id, guild_id, session_type, duration_minutes, start_time)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            """, (user_id, guild_id, session_type, duration_minutes))
            await conn.commit()
            session_id = cursor.lastrowid
            
            # Store in memory
            active_sessions[user_id] = {
                'session_id': session_id,
                'guild_id': guild_id,
                'type': session_type,
                'duration': duration_minutes,
                'start_time': datetime.now(),
                'end_time': datetime.now() + timedelta(minutes=duration_minutes),
                'distractions': 0
            }
            
            logger.info(f"Started focus session {session_id} for user {user_id}")
            return session_id
    except Exception as e:
        logger.error(f"Error starting focus session: {e}")
        return None


async def end_focus_session(user_id: int, completed: bool = True) -> bool:
    """End a focus session for a user."""
    try:
        if user_id not in active_sessions:
            return False
        
        session = active_sessions[user_id]
        session_id = session['session_id']
        
        async with get_db_connection() as (conn, cursor):
            await cursor.execute("""
                UPDATE focus_sessions
                SET end_time = CURRENT_TIMESTAMP,
                    completed = %s,
                    distractions_count = %s
                WHERE id = %s
            """, (completed, session['distractions'], session_id))
            await conn.commit()
        
        # Remove from memory
        del active_sessions[user_id]
        
        logger.info(f"Ended focus session {session_id} for user {user_id}, completed: {completed}")
        return True
    except Exception as e:
        logger.error(f"Error ending focus session: {e}")
        return False


async def get_active_session(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user's active focus session if any."""
    return active_sessions.get(user_id)


async def log_distraction(
    user_id: int,
    distraction_type: str,
    details: Optional[str] = None
) -> bool:
    """Log a distraction during a focus session."""
    try:
        if user_id not in active_sessions:
            return False
        
        session = active_sessions[user_id]
        session_id = session['session_id']
        session['distractions'] += 1
        
        async with get_db_connection() as (conn, cursor):
            await cursor.execute("""
                INSERT INTO focus_distractions
                (session_id, user_id, distraction_type, distraction_details)
                VALUES (%s, %s, %s, %s)
            """, (session_id, user_id, distraction_type, details))
            await conn.commit()
        
        logger.debug(f"Logged distraction for user {user_id}: {distraction_type}")
        return True
    except Exception as e:
        logger.error(f"Error logging distraction: {e}")
        return False


async def check_session_expired(user_id: int) -> bool:
    """Check if a user's focus session has expired."""
    if user_id not in active_sessions:
        return False
    
    session = active_sessions[user_id]
    return datetime.now() >= session['end_time']


# --- Activity Detection ---

async def detect_message_activity(user_id: int, channel_type: str) -> bool:
    """
    Detect if a message should count as a distraction.
    
    Returns True if this is a distraction (user is in focus mode).
    """
    if user_id not in active_sessions:
        return False
    
    # Only count messages in non-work channels as distractions
    # For simplicity, we'll log all messages during focus as potential distractions
    await log_distraction(user_id, 'message', f'Message in {channel_type} channel')
    return True


async def detect_game_activity(user_id: int, game_name: str) -> bool:
    """
    Detect if starting a game should count as a distraction.
    
    Returns True if this is a distraction (user is in focus mode).
    """
    if user_id not in active_sessions:
        return False
    
    # Games are usually distractions during focus
    await log_distraction(user_id, 'game', f'Started playing {game_name}')
    return True


async def detect_media_activity(user_id: int, activity_name: str, is_music: bool = False) -> bool:
    """
    Detect if media consumption should count as a distraction.
    
    Returns True if this is a distraction (user is in focus mode).
    Music is typically allowed during focus.
    """
    if user_id not in active_sessions:
        return False
    
    # Music/Spotify is usually okay during focus
    if is_music:
        return False
    
    # Videos/streaming are distractions
    await log_distraction(user_id, 'video', f'Watching {activity_name}')
    return True


# --- Statistics ---

async def get_user_focus_stats(user_id: int, days: int = 7) -> Dict[str, Any]:
    """Get user's focus session statistics."""
    try:
        async with get_db_connection() as (conn, cursor):
            # Total sessions
            await cursor.execute("""
                SELECT COUNT(*), 
                       SUM(CASE WHEN completed THEN 1 ELSE 0 END),
                       SUM(duration_minutes),
                       SUM(distractions_count)
                FROM focus_sessions
                WHERE user_id = %s 
                AND start_time >= DATE_SUB(CURRENT_TIMESTAMP, INTERVAL %s DAY)
            """, (user_id, days))
            
            result = await cursor.fetchone()
            
            if result:
                return {
                    'total_sessions': result[0] or 0,
                    'completed_sessions': result[1] or 0,
                    'total_minutes': result[2] or 0,
                    'total_distractions': result[3] or 0,
                    'completion_rate': (result[1] / result[0] * 100) if result[0] > 0 else 0
                }
            
            return {
                'total_sessions': 0,
                'completed_sessions': 0,
                'total_minutes': 0,
                'total_distractions': 0,
                'completion_rate': 0
            }
    except Exception as e:
        logger.error(f"Error getting focus stats: {e}")
        return {}


async def get_leaderboard(guild_id: Optional[int] = None, limit: int = 10) -> list:
    """Get focus time leaderboard."""
    try:
        async with get_db_connection() as (conn, cursor):
            if guild_id:
                await cursor.execute("""
                    SELECT user_id, 
                           SUM(duration_minutes) as total_minutes,
                           COUNT(*) as sessions,
                           SUM(CASE WHEN completed THEN 1 ELSE 0 END) as completed
                    FROM focus_sessions
                    WHERE guild_id = %s
                    AND start_time >= DATE_SUB(CURRENT_TIMESTAMP, INTERVAL 30 DAY)
                    GROUP BY user_id
                    ORDER BY total_minutes DESC
                    LIMIT %s
                """, (guild_id, limit))
            else:
                await cursor.execute("""
                    SELECT user_id, 
                           SUM(duration_minutes) as total_minutes,
                           COUNT(*) as sessions,
                           SUM(CASE WHEN completed THEN 1 ELSE 0 END) as completed
                    FROM focus_sessions
                    WHERE start_time >= DATE_SUB(CURRENT_TIMESTAMP, INTERVAL 30 DAY)
                    GROUP BY user_id
                    ORDER BY total_minutes DESC
                    LIMIT %s
                """, (limit,))
            
            rows = await cursor.fetchall()
            return [
                {
                    'user_id': row[0],
                    'total_minutes': row[1],
                    'sessions': row[2],
                    'completed': row[3]
                }
                for row in rows
            ]
    except Exception as e:
        logger.error(f"Error getting focus leaderboard: {e}")
        return []


# --- Pomodoro Presets ---

POMODORO_PRESETS = {
    'short': {
        'name': 'Short Pomodoro',
        'work': 25,
        'break': 5,
        'description': 'Classic 25min work, 5min break'
    },
    'long': {
        'name': 'Long Pomodoro',
        'work': 50,
        'break': 10,
        'description': '50min work, 10min break'
    },
    'ultra': {
        'name': 'Ultra Focus',
        'work': 90,
        'break': 15,
        'description': '90min deep work, 15min break'
    },
    'sprint': {
        'name': 'Quick Sprint',
        'work': 15,
        'break': 3,
        'description': '15min sprint, 3min break'
    }
}


def get_pomodoro_preset(preset_name: str) -> Optional[Dict[str, Any]]:
    """Get a Pomodoro preset by name."""
    return POMODORO_PRESETS.get(preset_name.lower())


def list_pomodoro_presets() -> Dict[str, Dict[str, Any]]:
    """Get all available Pomodoro presets."""
    return POMODORO_PRESETS
