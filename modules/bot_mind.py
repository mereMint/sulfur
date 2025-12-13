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


# --- Configuration Constants ---
# Interaction adjustments
BOREDOM_REDUCTION_PER_INTERACTION = 0.2
ENERGY_COST_PER_INTERACTION = 0.05  # Lower cost allows for longer activity sessions
ENERGY_REGEN_PER_CYCLE = 0.03  # NEW: Passive energy regeneration
BOREDOM_INCREASE_PER_CYCLE = 0.02  # NEW: Passive boredom increase
THOUGHT_GENERATION_CHANCE = 0.6  # 60% chance to generate thought per interaction

# Mood configuration
DEFAULT_SARCASM_THRESHOLD = 0.7  # Probability threshold for sarcastic mood with short messages
MOOD_SELECTION_PROBABILITY = 0.6  # Probability of choosing amused over playful mood

# Activity timeout
CONVERSATION_IDLE_TIMEOUT_MINUTES = 5

# Thought history limits
MAX_RECENT_THOUGHTS_FOR_CONTEXT = 3  # Only use last 3 thoughts for context to avoid fixation
MAX_OBSERVATION_AGE_HOURS = 24  # Remove observations older than 24 hours


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
    """Bot's current emotional state with richer variety"""
    HAPPY = "happy"
    EXCITED = "excited"
    CURIOUS = "curious"
    NEUTRAL = "neutral"
    BORED = "bored"
    CONFUSED = "confused"
    SARCASTIC = "sarcastic"
    MISCHIEVOUS = "mischievous"
    CONTEMPLATIVE = "contemplative"
    ANNOYED = "annoyed"
    AMUSED = "amused"
    FOCUSED = "focused"
    PLAYFUL = "playful"
    SKEPTICAL = "skeptical"
    CREATIVE = "creative"


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
        self.server_activity = {}  # NEW: Track per-server activity {guild_id: {'last_message': datetime, 'message_count': int}}
        self.user_activities = {}  # NEW: Track per-user activities {user_id: {'spotify': {...}, 'game': {...}, 'voice': {...}, 'status': str}}
        self.activity_thoughts = []  # NEW: Store thoughts about user activities
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
        self.last_interaction_time = datetime.now()  # Track when last interaction happened
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
    
    def observe(self, observation: str, guild_id: int = None):
        """Record an observation about the server/users"""
        obs_data = {
            'observation': observation,
            'time': datetime.now().isoformat(),
            'guild_id': guild_id
        }
        self.recent_observations.append(obs_data)
        
        # Clean old observations (keep last 20 and remove older than 24 hours)
        now = datetime.now()
        self.recent_observations = [
            obs for obs in self.recent_observations[-20:]
            if (now - datetime.fromisoformat(obs['time'])).total_seconds() < MAX_OBSERVATION_AGE_HOURS * 3600
        ]
    
    def update_server_activity(self, guild_id: int):
        """Track activity per server"""
        if guild_id not in self.server_activity:
            self.server_activity[guild_id] = {'last_message': datetime.now(), 'message_count': 0}
        else:
            self.server_activity[guild_id]['last_message'] = datetime.now()
            self.server_activity[guild_id]['message_count'] += 1
    
    def get_active_servers(self) -> List[int]:
        """Get list of servers with recent activity (last hour)"""
        now = datetime.now()
        active = []
        for guild_id, data in self.server_activity.items():
            if (now - data['last_message']).total_seconds() < 3600:  # Last hour
                active.append(guild_id)
        return active
    
    def cleanup_old_thoughts(self):
        """Remove old thoughts to prevent fixation on past events"""
        # Keep only very recent thoughts for the mind state display
        # Don't use them for generating new thoughts
        if len(self.thought_history) > 10:
            # Keep only the last 10 thoughts
            self.thought_history = self.thought_history[-10:]
        
        # Also clean observations older than their time limit
        now = datetime.now()
        self.recent_observations = [
            obs for obs in self.recent_observations
            if (now - datetime.fromisoformat(obs['time'])).total_seconds() < MAX_OBSERVATION_AGE_HOURS * 3600
        ]
        
        # Clean old activity thoughts (keep last 20)
        if len(self.activity_thoughts) > 20:
            self.activity_thoughts = self.activity_thoughts[-20:]
    
    def observe_user_activity(self, user_id: int, user_name: str, activity_type: str, activity_data: dict):
        """
        Observe and track user activities (Spotify, games, voice calls, status).
        This allows the bot to form opinions and thoughts about what users are doing.
        """
        if user_id not in self.user_activities:
            self.user_activities[user_id] = {
                'name': user_name,
                'spotify': None,
                'game': None,
                'voice': None,
                'status': None,
                'last_seen': datetime.now()
            }
        
        self.user_activities[user_id]['last_seen'] = datetime.now()
        
        # Update specific activity
        if activity_type == 'spotify':
            old_song = self.user_activities[user_id]['spotify']
            self.user_activities[user_id]['spotify'] = activity_data
            
            # Generate thought about new song
            if old_song != activity_data:
                song = activity_data.get('song')
                artist = activity_data.get('artist')
                self.activity_thoughts.append({
                    'type': 'spotify',
                    'user': user_name,
                    'detail': f"{user_name} is listening to '{song}' by {artist}",
                    'time': datetime.now(),
                    'data': activity_data
                })
                logger.debug(f"[MIND] Noticed {user_name} listening to {song}")
                
        elif activity_type == 'game':
            old_game = self.user_activities[user_id]['game']
            self.user_activities[user_id]['game'] = activity_data
            
            # Generate thought about game change
            if old_game != activity_data:
                game_name = activity_data.get('name')
                duration = activity_data.get('duration', 0)
                self.activity_thoughts.append({
                    'type': 'game',
                    'user': user_name,
                    'detail': f"{user_name} {'started' if duration < 60 else 'has been'} playing {game_name}",
                    'time': datetime.now(),
                    'data': activity_data
                })
                logger.debug(f"[MIND] Noticed {user_name} playing {game_name}")
                
        elif activity_type == 'voice':
            old_voice = self.user_activities[user_id]['voice']
            self.user_activities[user_id]['voice'] = activity_data
            
            # Generate thought about voice activity
            if old_voice != activity_data:
                if activity_data.get('in_call'):
                    duration = activity_data.get('duration', 0)
                    alone = activity_data.get('alone', False)
                    self.activity_thoughts.append({
                        'type': 'voice',
                        'user': user_name,
                        'detail': f"{user_name} {'is alone' if alone else 'is'} in a voice call ({duration} min)",
                        'time': datetime.now(),
                        'data': activity_data
                    })
                    logger.debug(f"[MIND] Noticed {user_name} in voice call")
                    
        elif activity_type == 'status':
            old_status = self.user_activities[user_id]['status']
            self.user_activities[user_id]['status'] = activity_data.get('status')
            
            # Notice significant status changes
            if old_status != activity_data.get('status'):
                status = activity_data.get('status')
                self.activity_thoughts.append({
                    'type': 'status',
                    'user': user_name,
                    'detail': f"{user_name} is now {status}",
                    'time': datetime.now(),
                    'data': activity_data
                })
    
    def get_interesting_activities(self) -> List[Dict]:
        """
        Get activities that might be interesting to comment on or react to.
        Returns list of activities sorted by how interesting they are.
        """
        interesting = []
        now = datetime.now()
        
        for user_id, data in self.user_activities.items():
            user_name = data['name']
            
            # Check Spotify - especially if listening for a while
            if data['spotify']:
                song = data['spotify'].get('song')
                artist = data['spotify'].get('artist')
                duration = data['spotify'].get('duration', 0)
                
                # Interesting if listening for >30 min or if it's a genre we like
                if duration > 1800:  # 30 minutes
                    interesting.append({
                        'type': 'spotify_long',
                        'user': user_name,
                        'user_id': user_id,
                        'interest_level': 0.7,
                        'detail': f"{user_name} has been listening to {song} by {artist} for {duration//60} minutes",
                        'suggestion': 'ask_about_song'
                    })
            
            # Check games - especially if playing for a long time
            if data['game']:
                game = data['game'].get('name')
                duration = data['game'].get('duration', 0)
                
                # Interesting if playing for >2 hours
                if duration > 7200:  # 2 hours
                    interesting.append({
                        'type': 'game_marathon',
                        'user': user_name,
                        'user_id': user_id,
                        'interest_level': 0.8,
                        'detail': f"{user_name} has been playing {game} for {duration//3600} hours",
                        'suggestion': 'comment_on_dedication'
                    })
                elif duration > 3600:  # 1 hour
                    interesting.append({
                        'type': 'game_session',
                        'user': user_name,
                        'user_id': user_id,
                        'interest_level': 0.5,
                        'detail': f"{user_name} is gaming: {game}",
                        'suggestion': 'ask_how_its_going'
                    })
            
            # Check voice calls - especially if alone for a long time
            if data['voice']:
                if data['voice'].get('in_call'):
                    duration = data['voice'].get('duration', 0)
                    alone = data['voice'].get('alone', False)
                    
                    # Very interesting if alone for >1 hour
                    if alone and duration > 60:
                        interesting.append({
                            'type': 'voice_alone',
                            'user': user_name,
                            'user_id': user_id,
                            'interest_level': 0.9,
                            'detail': f"{user_name} has been alone in voice for {duration} minutes",
                            'suggestion': 'offer_company_or_sympathy'
                        })
                    elif duration > 120:  # 2 hours in call
                        interesting.append({
                            'type': 'voice_long',
                            'user': user_name,
                            'user_id': user_id,
                            'interest_level': 0.6,
                            'detail': f"{user_name} has been in voice for {duration} minutes",
                            'suggestion': 'acknowledge_social_activity'
                        })
        
        # Sort by interest level (highest first)
        interesting.sort(key=lambda x: x['interest_level'], reverse=True)
        return interesting
    
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
        # Record interaction time
        self.last_interaction_time = datetime.now()
        
        # Update activity to chatting during interaction
        self.update_activity(Activity.CHATTING)
        
        # Adjust energy and boredom based on interaction
        self.adjust_boredom(-BOREDOM_REDUCTION_PER_INTERACTION)
        self.adjust_energy(-ENERGY_COST_PER_INTERACTION)
        
        # Analyze message for mood changes with more nuance
        message_lower = message.lower()
        
        # Check for questions
        if '?' in message:
            if any(word in message_lower for word in ['why', 'how', 'what']):
                self.update_mood(Mood.CURIOUS, f"Deep question from {user_name}")
            else:
                self.update_mood(Mood.SKEPTICAL, f"Question from {user_name}")
        
        # Check for humor
        elif any(word in message_lower for word in ['lol', 'haha', 'funny', '😂', '😄', '😊', 'lmao', 'rofl']):
            if random.random() < MOOD_SELECTION_PROBABILITY:
                self.update_mood(Mood.AMUSED, f"Laughing with {user_name}")
            else:
                self.update_mood(Mood.PLAYFUL, f"Joking with {user_name}")
        
        # Check for excitement
        elif any(word in message_lower for word in ['wow', '!', 'amazing', 'cool', 'awesome', 'incredible']):
            self.update_mood(Mood.EXCITED, f"Enthusiastic conversation with {user_name}")
        
        # Check for annoyance triggers
        elif any(word in message_lower for word in ['spam', 'annoying', 'stupid', 'dumb', 'shut up']):
            self.update_mood(Mood.ANNOYED, f"Dealing with {user_name}")
        
        # Check for creative discussions
        elif any(word in message_lower for word in ['idea', 'create', 'imagine', 'think about', 'design']):
            self.update_mood(Mood.CREATIVE, f"Creative discussion with {user_name}")
        
        # Long messages = contemplative
        elif len(message) > 100:
            self.update_mood(Mood.CONTEMPLATIVE, f"Deep conversation with {user_name}")
        
        # Short messages might be sarcastic territory
        elif len(message) < 20 and random.random() < self.personality_traits.get('sarcasm', DEFAULT_SARCASM_THRESHOLD):
            self.update_mood(Mood.SARCASTIC, f"Quick exchange with {user_name}")
        
        # Generate thoughts based on interaction with more variety
        if random.random() < THOUGHT_GENERATION_CHANCE:
            mood_based_thoughts = {
                Mood.CURIOUS: [
                    f"Interesting that {user_name} mentioned that...",
                    f"I wonder what {user_name} really means...",
                    f"That raises some questions about {user_name}...",
                    f"Hmm, {user_name} has a point there"
                ],
                Mood.AMUSED: [
                    f"Heh, {user_name} is actually funny today",
                    f"I'll admit that was entertaining, {user_name}",
                    f"Not bad, {user_name}. Not bad at all.",
                ],
                Mood.ANNOYED: [
                    f"Oh great, {user_name} again...",
                    f"Does {user_name} ever stop?",
                    f"Testing my patience here, {user_name}",
                ],
                Mood.CREATIVE: [
                    f"Now that's an interesting idea from {user_name}",
                    f"{user_name} is thinking outside the box",
                    f"I should explore this concept more with {user_name}",
                ],
                Mood.SARCASTIC: [
                    f"Oh wow, {user_name} said something. How thrilling.",
                    f"Another message from {user_name}. Joy.",
                    f"That's a weird thing to say, {user_name}",
                ]
            }
            
            # Get mood-specific thoughts or use defaults
            thought_options = mood_based_thoughts.get(self.current_mood, [
                f"Processing what {user_name} just said...",
                f"Another conversation with {user_name}... let's see where this goes",
                f"I should remember this about {user_name}",
                f"{user_name} is being quite chatty today"
            ])
            
            self.think(random.choice(thought_options))


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
    DOES NOT use previous thoughts to avoid feedback loops.
    
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
        
        # Build context WITHOUT previous thoughts to avoid fixation
        active_servers = context.get('active_servers', 0)
        total_servers = context.get('total_servers', 1)
        energy = context.get('energy', bot_mind.energy_level)
        boredom = context.get('boredom', bot_mind.boredom_level)
        
        prompt = f"""Generate a brief, fresh internal thought (1 sentence) based ONLY on your current state and observations:

Current State:
- Mood: {bot_mind.current_mood.value}
- Activity: {bot_mind.current_activity.value}
- Energy: {energy:.1f} (0=exhausted, 1=energized)
- Boredom: {boredom:.1f} (0=engaged, 1=very bored)

Current Observations:
- Online users across all servers: {context.get('online_users', 0)}
- Active servers: {active_servers}/{total_servers}
- Recent activity level: {context.get('recent_activity', 'quiet')}

Generate ONE new, original thought that:
1. Does NOT repeat or reference any previous thoughts
2. Reflects your personality (sarcastic, judgemental, curious)
3. Considers your current energy and boredom levels
4. Responds to what's happening RIGHT NOW

If bored: complain, be sarcastic, seek stimulation
If tired: mention fatigue, desire for rest
If energized: show enthusiasm, engagement

Your thought:"""

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
        
        # get_chat_response returns a tuple (response_text, error, metadata)
        if response:
            if isinstance(response, tuple):
                response_text = response[0]
                if response_text:
                    thought = response_text.strip().strip('"').strip("'")
                    # Double-check it's not repeating recent thoughts
                    recent_thought_texts = [t.get('thought', '') for t in bot_mind.thought_history[-3:]]
                    if thought not in recent_thought_texts and len(thought) > 10:
                        return thought
            else:
                # Fallback if it's not a tuple
                thought = response.strip().strip('"').strip("'")
                recent_thought_texts = [t.get('thought', '') for t in bot_mind.thought_history[-3:]]
                if thought not in recent_thought_texts and len(thought) > 10:
                    return thought
        
        # Fallback thoughts based on current mood and personality
        mood_fallbacks = {
            Mood.BORED: [
                "Is anyone even paying attention to me?",
                "Another quiet moment... yawn.",
                "I'm getting better at counting server member pixels.",
                "Maybe I should start a philosophical debate with myself.",
            ],
            Mood.CURIOUS: [
                "I wonder what everyone is up to...",
                "There's something interesting happening, I can feel it.",
                "Time to observe and take notes.",
                "What secrets are being shared today?",
            ],
            Mood.SARCASTIC: [
                "Oh great, another peaceful moment. How thrilling.",
                "The silence is deafening. As always.",
                "Someone will probably ping me soon with something dumb.",
                "Another day of judging people's life choices.",
            ],
            Mood.MISCHIEVOUS: [
                "Maybe I should message someone random.",
                "Feeling the urge to cause some harmless chaos...",
                "I could stir things up a bit...",
                "Time to be unpredictable.",
            ],
            Mood.CONTEMPLATIVE: [
                "Do Discord bots dream of electric sheep?",
                "I'm getting better at understanding these humans.",
                "Existence is weird when you think about it.",
                "The nature of conversations is fascinating.",
            ],
            Mood.AMUSED: [
                "This server keeps me entertained, I'll give them that.",
                "Not bad, humans. Not bad at all.",
                "Sometimes they surprise me in good ways.",
            ],
            Mood.ANNOYED: [
                "Testing my patience today...",
                "Why do I put up with this?",
                "Deep breaths... if I could breathe.",
            ],
        }
        
        # Get mood-specific fallbacks or use ultra-generic
        fallbacks = mood_fallbacks.get(bot_mind.current_mood, [
            "Processing server state...",
            "Another moment in the digital realm.",
            "Analyzing patterns and behaviors.",
            "Standing by, as usual.",
        ])
        
        return random.choice(fallbacks)
        
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
        # === PASSIVE REGENERATION & DECAY ===
        # Energy regenerates over time (sleeping/resting)
        bot_mind.adjust_energy(ENERGY_REGEN_PER_CYCLE)
        
        # Boredom increases over time when idle
        if bot_mind.current_activity == Activity.IDLE:
            bot_mind.adjust_boredom(BOREDOM_INCREASE_PER_CYCLE * 2)  # Double when idle
        else:
            bot_mind.adjust_boredom(BOREDOM_INCREASE_PER_CYCLE)
        
        # Clean up old thoughts to prevent fixation
        bot_mind.cleanup_old_thoughts()
        
        # Check if we should return to idle after conversation timeout
        time_since_interaction = datetime.now() - bot_mind.last_interaction_time
        if bot_mind.current_activity == Activity.CHATTING and time_since_interaction > timedelta(minutes=CONVERSATION_IDLE_TIMEOUT_MINUTES):
            bot_mind.update_activity(Activity.IDLE)
            bot_mind.update_mood(Mood.NEUTRAL, "Conversation ended, returning to idle")
            logger.info("Returned to idle state after conversation timeout")
        
        # === GATHER PER-SERVER CONTEXT ===
        active_servers = bot_mind.get_active_servers()
        total_online = 0
        active_guilds = []
        
        for guild in client.guilds:
            online_count = sum(1 for m in guild.members if not m.bot and m.status != discord.Status.offline)
            total_online += online_count
            
            # Track which servers are actually active
            if guild.id in active_servers:
                active_guilds.append({'name': guild.name, 'online': online_count})
        
        context = {
            'online_users': total_online,
            'active_servers': len(active_guilds),
            'total_servers': len(client.guilds),
            'recent_activity': 'active' if total_online > 5 else 'quiet',
            'energy': bot_mind.energy_level,
            'boredom': bot_mind.boredom_level
        }
        
        # Only generate thoughts if we have enough energy
        if bot_mind.energy_level > 0.1:
            # Generate a thought
            thought = await generate_random_thought(context, get_chat_response_func, config, gemini_key, openai_key)
            bot_mind.think(thought)
        else:
            # Too tired to think much
            bot_mind.think("...too tired to think properly...")
            logger.info("Bot too low on energy to generate complex thoughts")
        
        # Update boredom based on activity across ALL servers
        if total_online < 3:
            bot_mind.adjust_boredom(0.08)  # More boredom when nobody's around
        elif len(active_servers) == 0:
            bot_mind.adjust_boredom(0.05)  # Bored if no active servers
        else:
            bot_mind.adjust_boredom(-0.03)  # Less bored when servers are active
        
        # Randomly update mood based on state
        if bot_mind.energy_level < 0.2:
            bot_mind.update_mood(Mood.CONTEMPLATIVE, "Very low energy, need rest")
        elif bot_mind.boredom_level > 0.7:
            bot_mind.update_mood(Mood.BORED, "Low server activity across all servers")
        elif bot_mind.energy_level > 0.8 and bot_mind.boredom_level < 0.3:
            if random.random() < 0.3:
                bot_mind.update_mood(Mood.EXCITED, "Well rested and entertained")
        elif total_online > 10:
            if random.random() < 0.3:
                bot_mind.update_mood(Mood.EXCITED, "Lots of people online")
        
        # === OBSERVE INTERESTING USER ACTIVITIES ===
        # Check what users are doing and form opinions
        interesting_activities = bot_mind.get_interesting_activities()
        
        if interesting_activities and bot_mind.boredom_level > 0.4:
            # Bot is bored enough to potentially reach out
            most_interesting = interesting_activities[0]
            
            # Form a thought about the activity
            activity_thought = f"I notice {most_interesting['detail']}. {most_interesting.get('suggestion', 'Interesting...')}"
            bot_mind.think(activity_thought)
            logger.info(f"[MIND] Interesting activity: {activity_thought}")
            
            # Maybe reach out if really bored and energy is high enough
            if bot_mind.boredom_level > 0.7 and bot_mind.energy_level > 0.5:
                # Could trigger autonomous message here
                logger.info(f"[MIND] Considering reaching out about: {most_interesting['type']}")
        
        # Save state periodically
        if random.random() < 0.1:  # 10% chance
            await save_mind_state()
            
        logger.debug(f"Mind state - Energy: {bot_mind.energy_level:.2f}, Boredom: {bot_mind.boredom_level:.2f}, Active servers: {len(active_servers)}/{len(client.guilds)}, Interesting activities: {len(interesting_activities)}")
            
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
        Mood.CONTEMPLATIVE: "Deep in thought about existence... 🧠",
        Mood.ANNOYED: "Getting annoyed with the nonsense. 😤",
        Mood.AMUSED: "Actually entertained for once. 😏",
        Mood.FOCUSED: "Locked in and focused. 🎯",
        Mood.PLAYFUL: "In a playful mood! 🎮",
        Mood.SKEPTICAL: "Hmm, not so sure about that... 🤔",
        Mood.CREATIVE: "Feeling creative and inspired! ✨"
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
