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
    Forms thoughts during conversations and uses them to influence behavior.
    """
    
    def __init__(self):
        self.current_mood = Mood.NEUTRAL
        self.current_activity = Activity.IDLE
        self.energy_level = 1.0  # 0.0 to 1.0
        self.boredom_level = 0.0  # 0.0 to 1.0
        self.interests: List[str] = []
        self._interests_lower: set = set()  # Case-insensitive lookup set for performance
        self.thoughts: List[str] = []
        self.recent_thoughts: List[Dict[str, Any]] = []  # Detailed thought history with timestamps
        self.recent_observations: List[Dict[str, Any]] = []  # Observation history for personality development
        self.current_thought: str = "Nichts Besonderes..."
        self.last_thought_time = datetime.now(timezone.utc)
        self.last_activity_time = datetime.now(timezone.utc)
        self._server_activity: Dict[int, datetime] = {}
        # Topic tracking for boredom detection
        self._topic_history: List[str] = []  # Track recent conversation topics
        self._conversation_count: int = 0  # Count conversations for periodic thought generation
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
        if interest and interest.lower() not in self._interests_lower:
            self.interests.append(interest)
            self._interests_lower.add(interest.lower())
            # Keep only last 15 interests
            if len(self.interests) > 15:
                removed = self.interests.pop(0)
                self._interests_lower.discard(removed.lower())
            logger.debug(f"Bot added new interest: {interest}")
    
    def track_topic(self, topic: str):
        """
        Track a conversation topic for boredom detection.
        If same topic is discussed repeatedly, increase boredom.
        """
        if not topic:
            return
        
        topic_lower = topic.lower().strip()
        self._topic_history.append(topic_lower)
        # Keep only last 20 topics
        self._topic_history = self._topic_history[-20:]
        
        # Check for repetitive topics (boredom trigger)
        if self._topic_history.count(topic_lower) >= 3:
            self.boredom_level = min(1.0, self.boredom_level + 0.15)
            if self.boredom_level > 0.5:
                self.update_mood(Mood.BORED, f"Repeated topic: {topic}")
                self.think(f"Schon wieder das Thema '{topic}'... wird langsam langweilig.")
        else:
            # New topic - slightly reduce boredom and possibly become curious
            self.boredom_level = max(0.0, self.boredom_level - 0.03)
            if topic_lower not in self._interests_lower:
                # Chance to become curious about new topic
                if random.random() < self.personality_traits['curiosity']:
                    self.update_mood(Mood.CURIOUS, f"New topic: {topic}")
    
    def increment_conversation(self):
        """
        Increment conversation counter and check if it's time for a thought.
        Returns True if the bot should generate a thought based on conversation count.
        """
        self._conversation_count += 1
        # Generate thought every ~2 conversations (on average)
        if self._conversation_count >= 2:
            self._conversation_count = 0
            return True
        return False
    
    def should_express_boredom(self) -> bool:
        """Check if bot should express boredom in its response."""
        return self.boredom_level > 0.6 and random.random() < 0.3
    
    def should_express_interest(self, topic: str = None) -> bool:
        """Check if bot should express interest based on current state and topic."""
        if topic and topic.lower() in self._interests_lower:
            return True
        return self.current_mood == Mood.CURIOUS and random.random() < 0.5
    
    def get_mood_modifier(self) -> str:
        """
        Get a mood-based modifier for AI responses.
        Returns a hint string to include in AI prompts.
        """
        modifiers = {
            Mood.NEUTRAL: "",
            Mood.HAPPY: "[Du bist gerade gut gelaunt und freundlicher als sonst.]",
            Mood.BORED: "[Du bist gelangweilt - sei etwas desinteressiert oder schlage einen Themenwechsel vor.]",
            Mood.EXCITED: "[Du bist aufgeregt und enthusiastisch über dieses Thema!]",
            Mood.CURIOUS: "[Du bist neugierig und stellst gerne Gegenfragen.]",
            Mood.SARCASTIC: "[Du bist in einer sarkastischen Stimmung - mehr Witz und Ironie.]",
            Mood.CONTEMPLATIVE: "[Du bist nachdenklich und philosophisch.]",
            Mood.ANNOYED: "[Du bist leicht genervt - sei etwas kurz angebunden.]"
        }
        return modifiers.get(self.current_mood, "")
    
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
    
    def add_observation(self, observation: str, user_id: int = None, guild_id: int = None):
        """
        Record an observation about user behavior or server activity.
        Used for personality development and learning.
        """
        if not observation:
            return
        
        self.recent_observations.append({
            'observation': observation,
            'user_id': user_id,
            'guild_id': guild_id,
            'time': datetime.now(timezone.utc).isoformat()
        })
        # Keep only last 50 observations
        self.recent_observations = self.recent_observations[-50:]
        logger.debug(f"Bot recorded observation: {observation[:50]}...")
    
    def observe_user_activity(self, guild_id: int, user_id: int, activity_type: str):
        """Observe user activity for learning."""
        self.update_server_activity(guild_id)
        
        # Record the observation
        self.add_observation(f"User {user_id} is {activity_type}", user_id, guild_id)
        
        # Add observations to influence mood and interests
        if activity_type == 'gaming':
            if random.random() < 0.3:
                self.add_interest('Gaming')
        elif activity_type == 'music':
            if random.random() < 0.3:
                self.add_interest('Musik')
        elif activity_type == 'chatting':
            # Chatting reduces boredom
            self.boredom_level = max(0.0, self.boredom_level - 0.02)
    
    def update_boredom_over_time(self):
        """
        Update boredom level based on time since last activity.
        Should be called periodically (e.g., every minute).
        """
        now = datetime.now(timezone.utc)
        time_since_activity = (now - self.last_activity_time).total_seconds()
        
        # Increase boredom after 5 minutes of inactivity
        if time_since_activity > 300:  # 5 minutes
            self.boredom_level = min(1.0, self.boredom_level + 0.02)
            
            # Update mood if very bored
            if self.boredom_level > 0.7 and self.current_mood != Mood.BORED:
                self.update_mood(Mood.BORED, "No activity for a while")
        
        # Also slightly decrease energy over time
        if time_since_activity > 600:  # 10 minutes
            self.energy_level = max(0.3, self.energy_level - 0.01)
    
    def get_random_thought_prompt(self) -> str:
        """
        Get a prompt for generating a random thought based on current state.
        Returns context for AI thought generation.
        """
        context_parts = []
        
        if self.boredom_level > 0.5:
            context_parts.append("Du bist gelangweilt")
        if self.interests:
            context_parts.append(f"Deine Interessen sind: {', '.join(self.interests[-5:])}")
        if self.current_mood != Mood.NEUTRAL:
            context_parts.append(f"Deine Stimmung ist: {self.current_mood.value}")
        
        return ". ".join(context_parts) if context_parts else "Du beobachtest den Server"


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
        'recent_observations': bot_mind.recent_observations[-20:] if bot_mind.recent_observations else [],
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
