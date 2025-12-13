"""
Passive Observer Module - Background Message Monitoring and Thinking

This module enables the bot to observe and process messages that don't directly
mention or involve it. The bot will:
- Read and understand conversations happening in channels
- Form thoughts and opinions about what's being discussed
- Track conversation topics and user behaviors
- Build context for better future interactions
- Store insights in the bot_mind system

This creates a more aware and contextually intelligent bot that understands
what's happening in the server even when not directly addressed.
"""

import asyncio
import random
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import discord

from modules.logger_utils import bot_logger as logger

# --- Configuration Constants ---
OBSERVATION_PROBABILITY = 0.15  # 15% chance to actively think about a random message
INTERESTING_MESSAGE_MULTIPLIER = 3.0  # Multiply probability for messages with interesting keywords
THOUGHT_GENERATION_COOLDOWN = 30  # Minimum seconds between generated thoughts
MIN_MESSAGE_LENGTH = 10  # Minimum message length to consider for observation
MAX_OBSERVATIONS_PER_CHANNEL = 5  # Max observations to store per channel per hour
INTERESTING_KEYWORDS = [
    # Topics of interest
    'game', 'gaming', 'play', 'anime', 'manga', 'music', 'spotify', 'movie', 'film',
    'code', 'coding', 'programming', 'bot', 'ai', 'tech', 'computer',
    'funny', 'lol', 'lmao', 'meme', 'wtf', 'omg',
    # Emotions and reactions
    'sad', 'happy', 'angry', 'excited', 'bored', 'tired', 'stressed',
    # Social interactions
    'party', 'event', 'meeting', 'call', 'voice', 'vc',
    # German keywords
    'spiel', 'musik', 'film', 'lustig', 'interessant', 'cool', 'krass',
    'warum', 'wie', 'was', 'wer', 'woher', 'wann'
]


class PassiveObserver:
    """
    Manages passive observation of server messages and generates
    internal thoughts for the bot's consciousness.
    """
    
    def __init__(self):
        self.last_thought_time = datetime.now()
        self.channel_observations = {}  # {channel_id: [(timestamp, observation), ...]}
        self.conversation_topics = {}  # {channel_id: {'topic': str, 'participants': set, 'last_update': datetime}}
        self.user_interests = {}  # {user_id: {'topics': set, 'last_active': datetime}}
        
    def _should_observe_message(self, message: discord.Message) -> bool:
        """
        Determine if a message should be observed and processed.
        
        Args:
            message: Discord message to evaluate
            
        Returns:
            True if message should be observed
        """
        # Don't observe bot messages
        if message.author.bot:
            return False
        
        # Don't observe very short messages
        if len(message.content) < MIN_MESSAGE_LENGTH:
            return False
        
        # Don't observe commands
        if message.content.startswith('/'):
            return False
        
        # Check cooldown
        time_since_last_thought = (datetime.now() - self.last_thought_time).total_seconds()
        if time_since_last_thought < THOUGHT_GENERATION_COOLDOWN:
            return False
        
        # Check if message contains interesting keywords (increases probability)
        content_lower = message.content.lower()
        has_interesting_keyword = any(keyword in content_lower for keyword in INTERESTING_KEYWORDS)
        
        if has_interesting_keyword:
            # Higher probability for interesting messages
            return random.random() < OBSERVATION_PROBABILITY * INTERESTING_MESSAGE_MULTIPLIER
        else:
            # Lower probability for regular messages
            return random.random() < OBSERVATION_PROBABILITY
    
    def _extract_topic(self, message: discord.Message) -> Optional[str]:
        """
        Extract the main topic or theme from a message.
        
        Args:
            message: Discord message to analyze
            
        Returns:
            Extracted topic string or None
        """
        content = message.content.lower()
        
        # Check for specific topics
        if any(word in content for word in ['spiel', 'game', 'gaming', 'zock']):
            return 'gaming'
        elif any(word in content for word in ['musik', 'music', 'song', 'spotify', 'hör']):
            return 'music'
        elif any(word in content for word in ['anime', 'manga']):
            return 'anime'
        elif any(word in content for word in ['code', 'coding', 'programming', 'python', 'javascript']):
            return 'programming'
        elif any(word in content for word in ['film', 'movie', 'serie', 'show', 'netflix']):
            return 'movies'
        elif any(word in content for word in ['funny', 'lol', 'lmao', 'lustig', 'witzig']):
            return 'humor'
        elif any(word in content for word in ['party', 'event', 'treffen']):
            return 'social_event'
        elif any(word in content for word in ['problem', 'hilfe', 'help', 'frage', 'wie']):
            return 'help_request'
        else:
            return 'general_chat'
    
    def _generate_thought(
        self, 
        message: discord.Message, 
        topic: Optional[str],
        bot_mind_module: Any
    ) -> str:
        """
        Generate an internal thought about the observed message.
        
        Args:
            message: The observed message
            topic: Extracted topic
            bot_mind_module: Bot mind module for context
            
        Returns:
            Generated thought string
        """
        user_name = message.author.display_name
        channel_name = message.channel.name if hasattr(message.channel, 'name') else 'DM'
        
        # Get current mood for thought generation
        try:
            current_mood = bot_mind_module.bot_mind.current_mood.value
        except (AttributeError, KeyError):
            current_mood = 'neutral'
        
        # Generate thoughts based on topic and mood
        thoughts = []
        
        if topic == 'gaming':
            thoughts = [
                f"Hm, {user_name} redet über Gaming in #{channel_name}... interesting.",
                f"Scheint als würde {user_name} gerade über Spiele sprechen. Vielleicht sollte ich mitspielen.",
                f"Gaming Gespräch in #{channel_name} entdeckt. {user_name} ist involviert.",
            ]
        elif topic == 'music':
            thoughts = [
                f"{user_name} spricht über Musik. Ich frage mich, was für Geschmack sie haben.",
                f"Musik-Diskussion in #{channel_name}. {user_name} scheint interessiert zu sein.",
                f"Hmm, Musik... {user_name} hat wahrscheinlich einen interessanten Musikgeschmack.",
            ]
        elif topic == 'help_request':
            thoughts = [
                f"{user_name} braucht anscheinend Hilfe in #{channel_name}. Sollte ich eingreifen?",
                f"Jemand hat eine Frage... {user_name} sucht nach Antworten.",
                f"Hilfegesuch von {user_name}. Vielleicht kann ich später helfen.",
            ]
        elif topic == 'humor':
            thoughts = [
                f"{user_name} macht Witze in #{channel_name}. Lustig... oder auch nicht.",
                f"Comedy Hour in #{channel_name} mit {user_name}. Ich beobachte das mal.",
                f"Hmm, {user_name} versucht lustig zu sein. Interessant.",
            ]
        else:
            thoughts = [
                f"Interessante Konversation in #{channel_name}. {user_name} ist aktiv.",
                f"{user_name} chattet in #{channel_name}. Ich behalte das im Auge.",
                f"Activity in #{channel_name} bemerkt. {user_name} spricht über etwas.",
                f"Hmm, {user_name} ist in #{channel_name} aktiv. Was geht da ab?",
            ]
        
        # Mood-influenced thoughts
        if current_mood in ['bored', 'sarcastic']:
            thoughts.extend([
                f"Ugh, noch mehr Gerede in #{channel_name}. {user_name} wieder am Start.",
                f"{user_name} chattet... wie überraschend. *gähnt*",
            ])
        elif current_mood == 'curious':
            thoughts.extend([
                f"Ooh, was sagt {user_name} da? Spannend!",
                f"Interessant was {user_name} in #{channel_name} so erzählt...",
            ])
        
        return random.choice(thoughts)
    
    def _track_conversation(self, message: discord.Message, topic: Optional[str]):
        """
        Track ongoing conversations and participants.
        
        Args:
            message: Discord message
            topic: Extracted topic
        """
        channel_id = message.channel.id
        
        if channel_id not in self.conversation_topics:
            self.conversation_topics[channel_id] = {
                'topic': topic,
                'participants': set(),
                'messages': 1,
                'last_update': datetime.now()
            }
        else:
            # Update existing conversation
            conv = self.conversation_topics[channel_id]
            
            # If topic changed significantly or conversation is old, reset
            time_diff = (datetime.now() - conv['last_update']).total_seconds()
            if time_diff > 300 or (topic and topic != conv['topic']):  # 5 minutes
                conv['topic'] = topic
                conv['participants'] = set()
                conv['messages'] = 1
            else:
                conv['messages'] += 1
            
            conv['last_update'] = datetime.now()
        
        # Add participant
        self.conversation_topics[channel_id]['participants'].add(message.author.id)
        
        # Track user interests
        if topic and topic != 'general_chat':
            if message.author.id not in self.user_interests:
                self.user_interests[message.author.id] = {
                    'topics': set(),
                    'last_active': datetime.now()
                }
            self.user_interests[message.author.id]['topics'].add(topic)
            self.user_interests[message.author.id]['last_active'] = datetime.now()
    
    async def observe_message(
        self, 
        message: discord.Message,
        bot_mind_module: Any,
        config: Dict[str, Any]
    ) -> Optional[str]:
        """
        Observe a message and potentially generate a thought about it.
        
        Args:
            message: Discord message to observe
            bot_mind_module: Bot mind module to store thoughts
            config: Bot configuration
            
        Returns:
            Generated thought string if one was created, None otherwise
        """
        try:
            # Check if we should observe this message
            if not self._should_observe_message(message):
                return None
            
            # Extract topic
            topic = self._extract_topic(message)
            
            # Track conversation
            self._track_conversation(message, topic)
            
            # Generate thought
            thought = self._generate_thought(message, topic, bot_mind_module)
            
            # Store thought in bot mind
            try:
                bot_mind_module.bot_mind.think(thought)
                
                # Also create an observation
                observation = f"Observed: {message.author.display_name} talking about {topic or 'something'} in {message.channel.name if hasattr(message.channel, 'name') else 'a channel'}"
                bot_mind_module.bot_mind.observe(
                    observation, 
                    guild_id=message.guild.id if message.guild else None
                )
                
                logger.debug(f"[PASSIVE] Generated thought: {thought}")
                
            except Exception as e:
                logger.warning(f"[PASSIVE] Could not store thought in bot mind: {e}")
            
            # Update last thought time
            self.last_thought_time = datetime.now()
            
            return thought
            
        except Exception as e:
            logger.error(f"[PASSIVE] Error in observe_message: {e}", exc_info=True)
            return None
    
    def get_channel_context(self, channel_id: int) -> Optional[Dict[str, Any]]:
        """
        Get context about recent conversation in a channel.
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            Dictionary with conversation context or None
        """
        if channel_id not in self.conversation_topics:
            return None
        
        conv = self.conversation_topics[channel_id]
        time_diff = (datetime.now() - conv['last_update']).total_seconds()
        
        # Only return if conversation is recent (last 10 minutes)
        if time_diff > 600:
            return None
        
        return {
            'topic': conv['topic'],
            'participant_count': len(conv['participants']),
            'message_count': conv['messages'],
            'age_seconds': time_diff
        }
    
    def get_user_interests(self, user_id: int) -> Optional[List[str]]:
        """
        Get known interests for a user.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            List of interest topics or None
        """
        if user_id not in self.user_interests:
            return None
        
        return list(self.user_interests[user_id]['topics'])
    
    def cleanup_old_data(self):
        """Clean up old conversation and interest data."""
        now = datetime.now()
        
        # Clean old conversations (older than 1 hour)
        channels_to_remove = []
        for channel_id, conv in self.conversation_topics.items():
            if (now - conv['last_update']).total_seconds() > 3600:
                channels_to_remove.append(channel_id)
        
        for channel_id in channels_to_remove:
            del self.conversation_topics[channel_id]
        
        # Clean old user interests (older than 24 hours)
        users_to_remove = []
        for user_id, data in self.user_interests.items():
            if (now - data['last_active']).total_seconds() > 86400:
                users_to_remove.append(user_id)
        
        for user_id in users_to_remove:
            del self.user_interests[user_id]
        
        if channels_to_remove or users_to_remove:
            logger.debug(f"[PASSIVE] Cleaned up {len(channels_to_remove)} conversations and {len(users_to_remove)} user interests")


# Global passive observer instance
_passive_observer: Optional[PassiveObserver] = None


def get_passive_observer() -> PassiveObserver:
    """
    Get or create the global passive observer instance.
    
    Returns:
        PassiveObserver instance
    """
    global _passive_observer
    if _passive_observer is None:
        _passive_observer = PassiveObserver()
        logger.info("Initialized passive observer system")
    return _passive_observer
