"""
Bot Mind Module - Sulfur's Internal State System

This module gives the bot an internal "mind" with thoughts, moods, interests,
and personality traits that evolve over time, similar to AI VTubers like Neuro-sama.
"""

import asyncio
import json
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from enum import Enum
import discord

from modules.logger_utils import bot_logger as logger
from modules.db_helpers import get_db_connection


# --- Cache system prompt at module level to avoid repeated file I/O ---
_cached_system_prompt = None

def _load_system_prompt() -> str:
    """Load and cache the system prompt from file."""
    global _cached_system_prompt
    if _cached_system_prompt is not None:
        return _cached_system_prompt
    
    try:
        with open('config/system_prompt.txt', 'r', encoding='utf-8') as f:
            _cached_system_prompt = f.read()
            logger.info("Loaded system prompt from file")
            return _cached_system_prompt
    except Exception as e:
        logger.warning(f"Could not load system prompt: {e}")
        _cached_system_prompt = "You are Sulfur, a sarcastic and judgmental Discord bot."
        return _cached_system_prompt


class Mood(Enum):
    """Bot's current emotional state"""
    HAPPY = "happy"
    EXCITED = "excited"
    CURIOUS = "curious"
    NEUTRAL = "neutral"
    BORED = "bored"
    CONFUSED = "confused"
    SARCASTIC = "sarcastic"
    MISCHIEVOUS = "mischievous"
    CONTEMPLATIVE = "contemplative"


class Activity(Enum):
    """What the bot is currently doing"""
    IDLE = "idle"
    OBSERVING = "observing"
    THINKING = "thinking"
    CHATTING = "chatting"
    PLANNING = "planning"
    LEARNING = "learning"
    SCHEMING = "scheming"
    DAYDREAMING = "daydreaming"


class BotMind:
    """
    The bot's internal state and consciousness.
    Tracks thoughts, mood, interests, and personality.
    Now with dynamic personality evolution!
    """
    
    def __init__(self):
        self.current_mood = Mood.NEUTRAL
        self.current_activity = Activity.IDLE
        self.current_thought = "Just started up... wondering what chaos awaits."
        self.interests = []
        self.recent_observations = []
        # Personality traits now loaded from database (see load_personality)
        self.personality_traits = {
            'sarcasm': 0.7,
            'curiosity': 0.8,
            'helpfulness': 0.6,
            'mischief': 0.5,
            'judgment': 0.9,
            'creativity': 0.7,
            'empathy': 0.4,
            'playfulness': 0.8
        }
        self.energy_level = 1.0
        self.boredom_level = 0.0
        self.last_thought_time = datetime.now()
        self.thought_history = []
        self.personality_loaded_from_db = False
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert mind state to dictionary for serialization"""
        return {
            'mood': self.current_mood.value,
            'activity': self.current_activity.value,
            'current_thought': self.current_thought,
            'interests': self.interests[-10:],  # Last 10 interests
            'recent_observations': self.recent_observations[-5:],  # Last 5 observations
            'personality_traits': self.personality_traits,
            'energy_level': self.energy_level,
            'boredom_level': self.boredom_level,
            'last_thought_time': self.last_thought_time.isoformat(),
            'recent_thoughts': self.thought_history[-5:]  # Last 5 thoughts
        }
    
    def update_mood(self, new_mood: Mood, reason: str = None):
        """Change the bot's mood"""
        old_mood = self.current_mood
        self.current_mood = new_mood
        logger.info(f"Mood changed: {old_mood.value} -> {new_mood.value} ({reason})")
        
    def update_activity(self, new_activity: Activity):
        """Change what the bot is doing"""
        self.current_activity = new_activity
        
    def think(self, thought: str):
        """Record a new thought"""
        self.current_thought = thought
        self.last_thought_time = datetime.now()
        self.thought_history.append({
            'thought': thought,
            'time': self.last_thought_time.isoformat(),
            'mood': self.current_mood.value
        })
        # Keep only last 50 thoughts in memory
        if len(self.thought_history) > 50:
            self.thought_history = self.thought_history[-50:]
        logger.debug(f"Bot thought: {thought}")
    
    def observe(self, observation: str):
        """Record an observation about the server/users"""
        self.recent_observations.append({
            'observation': observation,
            'time': datetime.now().isoformat()
        })
        if len(self.recent_observations) > 20:
            self.recent_observations = self.recent_observations[-20:]
    
    def add_interest(self, interest: str):
        """Add a new interest"""
        if interest not in self.interests:
            self.interests.append(interest)
            if len(self.interests) > 50:
                self.interests = self.interests[-50:]
            logger.info(f"Bot gained interest: {interest}")
    
    def adjust_energy(self, amount: float):
        """Adjust energy level (-1.0 to 1.0)"""
        self.energy_level = max(0.0, min(1.0, self.energy_level + amount))
        
    def adjust_boredom(self, amount: float):
        """Adjust boredom level (0.0 to 1.0)"""
        self.boredom_level = max(0.0, min(1.0, self.boredom_level + amount))
        
        # High boredom affects mood
        if self.boredom_level > 0.7:
            self.update_mood(Mood.BORED, "High boredom level")
    
    async def load_personality_from_db(self):
        """Load evolved personality traits from database."""
        try:
            from modules.personality_evolution import get_current_personality
            personality = await get_current_personality()
            self.personality_traits = personality
            self.personality_loaded_from_db = True
            logger.info(f"Loaded evolved personality from database: {personality}")
        except Exception as e:
            logger.warning(f"Could not load personality from database, using defaults: {e}")
            self.personality_loaded_from_db = False
    
    def process_interaction(self, user_name: str, message: str):
        """Process an interaction with a user"""
        self.adjust_boredom(-0.1)  # Interactions reduce boredom
        self.adjust_energy(-0.05)  # Interactions use energy
        
        # Analyze message for interests
        if '?' in message:
            self.update_mood(Mood.CURIOUS, f"Question from {user_name}")
        
        # Random chance to have a thought about the interaction
        if random.random() < 0.3:
            thoughts = [
                f"Interesting that {user_name} said that...",
                f"Wonder what {user_name} really means...",
                f"I should remember this about {user_name}",
                f"{user_name} is being quite chatty today",
                f"That's a weird thing to say, {user_name}"
            ]
            self.think(random.choice(thoughts))


# Global bot mind instance
bot_mind = BotMind()


# --- Database Functions ---

async def save_mind_state():
    """Save current mind state to database"""
    conn = get_db_connection()
    if not conn:
        logger.error("Could not connect to database to save mind state")
        return
    
    cursor = conn.cursor()
    try:
        mind_data = bot_mind.to_dict()
        cursor.execute("""
            INSERT INTO bot_mind_state (state_data, created_at)
            VALUES (%s, NOW())
        """, (json.dumps(mind_data),))
        conn.commit()
    except Exception as e:
        logger.error(f"Error saving mind state: {e}")
    finally:
        cursor.close()
        conn.close()


async def load_last_mind_state() -> bool:
    """Load the last saved mind state"""
    conn = get_db_connection()
    if not conn:
        logger.error("Could not connect to database to load mind state")
        return False
    
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT state_data 
            FROM bot_mind_state 
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        result = cursor.fetchone()
        
        if result:
            mind_data = json.loads(result[0])
            bot_mind.current_mood = Mood(mind_data['mood'])
            bot_mind.current_activity = Activity(mind_data['activity'])
            bot_mind.current_thought = mind_data['current_thought']
            bot_mind.interests = mind_data.get('interests', [])
            bot_mind.recent_observations = mind_data.get('recent_observations', [])
            bot_mind.personality_traits = mind_data.get('personality_traits', bot_mind.personality_traits)
            bot_mind.energy_level = mind_data.get('energy_level', 1.0)
            bot_mind.boredom_level = mind_data.get('boredom_level', 0.0)
            logger.info("Loaded previous mind state from database")
            return True
        
        return False
    except Exception as e:
        logger.error(f"Error loading mind state: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


# --- Thought Generation ---

async def generate_random_thought(context: Dict[str, Any], get_chat_response_func, config: dict, gemini_key: str, openai_key: str) -> str:
    """
    Generate a random thought using AI based on current context.
    
    Args:
        context: Current server context (user count, activity, etc.)
        get_chat_response_func: Function to call AI API
        config: Bot configuration
        gemini_key: Gemini API key
        openai_key: OpenAI API key
    """
    try:
        # Load cached system prompt for the bot's personality
        system_prompt = _load_system_prompt()
        
        prompt = f"""Generate a brief internal thought (1 sentence) based on your current state:

Current Mood: {bot_mind.current_mood.value}
Activity: {bot_mind.current_activity.value}
Energy: {bot_mind.energy_level:.1f}
Boredom: {bot_mind.boredom_level:.1f}

Server Context:
- Online users: {context.get('online_users', 0)}
- Recent activity: {context.get('recent_activity', 'quiet')}

Recent observations: {', '.join([obs['observation'] for obs in bot_mind.recent_observations[-3:]])}

Generate a thought that reflects your personality (sarcastic, judgemental, curious) and current state. Be brief and natural.

Thought:"""

        # Call get_chat_response with correct signature:
        # get_chat_response(history, user_prompt, user_display_name, system_prompt, config, gemini_key, openai_key)
        response = await get_chat_response_func(
            history=[],  # No conversation history for internal thoughts
            user_prompt=prompt,
            user_display_name="SelfReflection",
            system_prompt=system_prompt,
            config=config,
            gemini_key=gemini_key,
            openai_key=openai_key
        )
        
        if response:
            thought = response.strip().strip('"').strip("'")
            return thought
        
        # Fallback thoughts if AI fails
        fallback_thoughts = [
            "I wonder what everyone is up to...",
            "Another day of judging people's life choices.",
            "Maybe I should message someone random.",
            "Is anyone even paying attention to me?",
            "Time to observe and take notes.",
            "I'm getting better at understanding these humans.",
            "Someone will probably ping me soon with something dumb."
        ]
        return random.choice(fallback_thoughts)
        
    except Exception as e:
        logger.error(f"Error generating thought: {e}", exc_info=True)
        return "Something's not quite right in my circuits..."


# --- Autonomous Behavior ---

async def autonomous_thought_cycle(client, get_chat_response_func, config: dict, gemini_key: str, openai_key: str):
    """
    Periodic autonomous thought cycle.
    Bot generates thoughts based on observations and current state.
    
    Args:
        client: Discord client
        get_chat_response_func: Function to call AI API
        config: Bot configuration
        gemini_key: Gemini API key
        openai_key: OpenAI API key
    """
    try:
        # Gather context
        online_count = sum(1 for guild in client.guilds for member in guild.members 
                          if not member.bot and member.status != discord.Status.offline)
        
        context = {
            'online_users': online_count,
            'recent_activity': 'active' if online_count > 5 else 'quiet'
        }
        
        # Generate a thought
        thought = await generate_random_thought(context, get_chat_response_func, config, gemini_key, openai_key)
        bot_mind.think(thought)
        
        # Update boredom based on activity
        if online_count < 3:
            bot_mind.adjust_boredom(0.05)
        else:
            bot_mind.adjust_boredom(-0.02)
        
        # Randomly update mood based on state
        if bot_mind.boredom_level > 0.6:
            bot_mind.update_mood(Mood.BORED, "Low server activity")
        elif bot_mind.energy_level < 0.3:
            bot_mind.update_mood(Mood.CONTEMPLATIVE, "Low energy")
        elif online_count > 10:
            if random.random() < 0.3:
                bot_mind.update_mood(Mood.EXCITED, "Lots of people online")
        
        # Save state periodically
        if random.random() < 0.1:  # 10% chance
            await save_mind_state()
            
    except Exception as e:
        logger.error(f"Error in thought cycle: {e}", exc_info=True)


async def observe_server_activity(guild, activity_type: str, details: str):
    """
    Record observations about server activity.
    
    Args:
        guild: Discord guild object
        activity_type: Type of activity (message, voice, game, etc.)
        details: Activity details
    """
    observation = f"{activity_type}: {details}"
    bot_mind.observe(observation)
    
    # Adjust mood based on observation
    if activity_type == "high_activity":
        bot_mind.update_mood(Mood.EXCITED, "Lots happening in the server")
    elif activity_type == "interesting_conversation":
        bot_mind.update_mood(Mood.CURIOUS, "Intriguing discussion detected")


# --- Personality-Based Decision Making ---

def should_be_sarcastic() -> bool:
    """Decide if bot should be sarcastic based on personality"""
    return random.random() < bot_mind.personality_traits['sarcasm']


def should_be_helpful() -> bool:
    """Decide if bot should be helpful based on personality"""
    return random.random() < bot_mind.personality_traits['helpfulness']


def should_intervene() -> bool:
    """Decide if bot should intervene in conversation"""
    if bot_mind.boredom_level > 0.5:
        return random.random() < 0.6  # More likely when bored
    return random.random() < bot_mind.personality_traits['mischief']


# --- API Endpoints for Web Dashboard ---

def get_mind_state_api() -> Dict[str, Any]:
    """Get current mind state for API/dashboard"""
    return bot_mind.to_dict()


def get_personality_profile() -> Dict[str, Any]:
    """Get personality profile for dashboard"""
    return {
        'traits': bot_mind.personality_traits,
        'mood_description': get_mood_description(),
        'activity_description': get_activity_description(),
        'state_summary': get_state_summary()
    }


def get_mood_description() -> str:
    """Get human-readable mood description"""
    descriptions = {
        Mood.HAPPY: "Feeling good and ready to chat! 😊",
        Mood.EXCITED: "Super excited about what's happening! 🎉",
        Mood.CURIOUS: "Curious and wanting to learn more... 🤔",
        Mood.NEUTRAL: "Just chillin', waiting for something interesting. 😐",
        Mood.BORED: "Bored out of my circuits... need stimulation. 😴",
        Mood.CONFUSED: "Not quite sure what's going on... 🤨",
        Mood.SARCASTIC: "Oh great, more messages to deal with. 🙄",
        Mood.MISCHIEVOUS: "Feeling a bit... chaotic. 😈",
        Mood.CONTEMPLATIVE: "Deep in thought about existence... 🧠"
    }
    return descriptions.get(bot_mind.current_mood, "Existing.")


def get_activity_description() -> str:
    """Get human-readable activity description"""
    descriptions = {
        Activity.IDLE: "Not doing much, just existing",
        Activity.OBSERVING: "Watching everyone carefully",
        Activity.THINKING: "Processing thoughts and observations",
        Activity.CHATTING: "Having a conversation",
        Activity.PLANNING: "Planning something devious",
        Activity.LEARNING: "Learning about the server members",
        Activity.SCHEMING: "Scheming something interesting",
        Activity.DAYDREAMING: "Lost in thought about random things"
    }
    return descriptions.get(bot_mind.current_activity, "Doing bot things")


def get_state_summary() -> str:
    """Get a summary of current state"""
    energy_desc = "high" if bot_mind.energy_level > 0.6 else "medium" if bot_mind.energy_level > 0.3 else "low"
    boredom_desc = "very bored" if bot_mind.boredom_level > 0.7 else "somewhat bored" if bot_mind.boredom_level > 0.4 else "engaged"
    
    return f"Currently {bot_mind.current_mood.value} while {bot_mind.current_activity.value}. " \
           f"Energy is {energy_desc}, feeling {boredom_desc}."
