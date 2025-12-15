"""
Bot Mind Module - Placeholder for bot consciousness and mood system

This module provides stub implementations for the bot mind/consciousness features
that are referenced in the codebase but not yet fully implemented.
"""

import random
from modules.logger_utils import bot_logger as logger
from enum import Enum
from datetime import datetime, timezone
from typing import List, Dict, Any, Callable, Optional


class Mood(Enum):
    """Bot mood states."""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    BORED = "bored"
    EXCITED = "excited"
    CURIOUS = "curious"
    SARCASTIC = "sarcastic"
    CONTEMPLATIVE = "contemplative"
    ANNOYED = "annoyed"


class Activity(Enum):
    """Bot activity states."""
    IDLE = "idle"
    CHATTING = "chatting"
    THINKING = "thinking"
    PLAYING_GAME = "playing_game"
    LISTENING = "listening"


class BotMind:
    """
    Represents the bot's consciousness state.
    Tracks mood, energy, boredom, and current thoughts.
    """
    
    def __init__(self):
        self.current_mood = Mood.NEUTRAL
        self.current_activity = Activity.IDLE
        self.energy_level = 1.0  # 0.0 to 1.0
        self.boredom_level = 0.0  # 0.0 to 1.0
        self.interests: List[str] = []
        self.thoughts: List[str] = []
        self.recent_thoughts: List[Dict[str, Any]] = []  # Detailed thought history with timestamps
        self.current_thought: str = "Nichts Besonderes..."
        self.last_thought_time = datetime.now(timezone.utc)
        self.last_activity_time = datetime.now(timezone.utc)
        self._server_activity: Dict[int, datetime] = {}
        # Personality traits (0.0 to 1.0 scale)
        self.personality_traits: Dict[str, float] = {
            'sarcasm': 0.6,
            'humor': 0.7,
            'curiosity': 0.8,
            'helpfulness': 0.9,
            'sass': 0.5
        }
    
    def update_mood(self, mood: Mood, reason: str = None):
        """Update the bot's current mood."""
        self.current_mood = mood
        if reason:
            logger.info(f"Bot mood changed to {mood.value}: {reason}")
    
    def update_activity(self, activity: Activity):
        """Update the bot's current activity."""
        self.current_activity = activity
        self.last_activity_time = datetime.now(timezone.utc)
    
    def update_server_activity(self, guild_id: int):
        """Track activity in a server."""
        self._server_activity[guild_id] = datetime.now(timezone.utc)
        # Reduce boredom when there's activity
        self.boredom_level = max(0.0, self.boredom_level - 0.05)
    
    def add_interest(self, interest: str):
        """Add a new interest to the bot."""
        if interest not in self.interests:
            self.interests.append(interest)
            # Keep only last 10 interests
            self.interests = self.interests[-10:]
    
    def think(self, thought: str):
        """Add a thought to the bot's thought log."""
        self.thoughts.append(thought)
        # Keep only last 20 thoughts
        self.thoughts = self.thoughts[-20:]
        # Update current thought
        self.current_thought = thought
        self.last_thought_time = datetime.now(timezone.utc)
        # Add to detailed recent thoughts with timestamp
        self.recent_thoughts.append({
            'thought': thought,
            'mood': self.current_mood.value,
            'time': self.last_thought_time.isoformat()
        })
        # Keep only last 50 detailed thoughts
        self.recent_thoughts = self.recent_thoughts[-50:]
    
    def observe_user_activity(self, guild_id: int, user_id: int, activity_type: str):
        """Observe user activity for learning."""
        # Placeholder - would track user patterns in real implementation
        self.update_server_activity(guild_id)


# Global bot mind instance
bot_mind = BotMind()


def get_mind_state_api() -> Dict[str, Any]:
    """
    Get the current mind state for API/display purposes.
    
    Returns:
        Dictionary with current mind state
    """
    return {
        'mood': bot_mind.current_mood.value,
        'activity': bot_mind.current_activity.value,
        'energy_level': bot_mind.energy_level,
        'boredom_level': bot_mind.boredom_level,
        'interests': bot_mind.interests.copy(),
        'thoughts': bot_mind.thoughts[-5:] if bot_mind.thoughts else [],
        'current_thought': bot_mind.current_thought,
        'last_thought_time': bot_mind.last_thought_time.isoformat() if bot_mind.last_thought_time else datetime.now(timezone.utc).isoformat(),
        'recent_thoughts': bot_mind.recent_thoughts[-20:] if bot_mind.recent_thoughts else [],
        'personality_traits': bot_mind.personality_traits.copy()
    }


def get_mood_description() -> str:
    """Get a human-readable description of the current mood."""
    mood_descriptions = {
        Mood.NEUTRAL: "Ausgeglichen und bereit",
        Mood.HAPPY: "Gut gelaunt und freundlich",
        Mood.BORED: "Gelangweilt und unterstimuliert",
        Mood.EXCITED: "Aufgeregt und enthusiastisch",
        Mood.CURIOUS: "Neugierig und interessiert",
        Mood.SARCASTIC: "Sarkastisch und witzig",
        Mood.CONTEMPLATIVE: "Nachdenklich und philosophisch",
        Mood.ANNOYED: "Leicht genervt"
    }
    return mood_descriptions.get(bot_mind.current_mood, "Unbekannt")


def get_activity_description() -> str:
    """Get a human-readable description of the current activity."""
    activity_descriptions = {
        Activity.IDLE: "Nichts Besonderes",
        Activity.CHATTING: "Im Gespräch",
        Activity.THINKING: "Nachdenken",
        Activity.PLAYING_GAME: "Spiele spielen",
        Activity.LISTENING: "Zuhören"
    }
    return activity_descriptions.get(bot_mind.current_activity, "Unbekannt")


def get_state_summary() -> str:
    """Get a brief summary of the bot's current state."""
    mood = bot_mind.current_mood.value
    energy = bot_mind.energy_level
    boredom = bot_mind.boredom_level
    
    if energy < 0.3:
        energy_desc = "müde"
    elif energy > 0.7:
        energy_desc = "energiegeladen"
    else:
        energy_desc = "normal"
    
    if boredom > 0.7:
        boredom_desc = ", gelangweilt"
    elif boredom > 0.4:
        boredom_desc = ", etwas gelangweilt"
    else:
        boredom_desc = ""
    
    return f"Stimmung: {mood.title()}, Energie: {energy_desc}{boredom_desc}"


async def generate_random_thought(
    context: str, 
    get_chat_response: Callable, 
    config: Dict[str, Any], 
    gemini_key: Optional[str], 
    openai_key: Optional[str]
) -> str:
    """
    Generate a random thought using AI.
    
    Args:
        context: Context for thought generation
        get_chat_response: Function to call AI
        config: Bot configuration
        gemini_key: Gemini API key
        openai_key: OpenAI API key
    
    Returns:
        Generated thought as string
    """
    # Placeholder - would generate AI thought in real implementation
    thoughts = [
        "Ich frage mich, was die Leute gerade machen...",
        "Vielleicht sollte ich mal was Sarkastisches sagen.",
        "Diese Konversation war interessant.",
        "Ich könnte mal wieder jemanden roasten.",
        "Wie wäre es mit einem Spiel?",
    ]
    return random.choice(thoughts)
