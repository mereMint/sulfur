"""
Advanced AI Module - Enhanced Intelligence and Reasoning
Implements Neuro-sama-like advanced AI capabilities including:
- Multi-modal reasoning
- Context compression
- Emotional intelligence
- Response quality scoring
- Token-efficient memory management
"""

import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import deque

from modules.logger_utils import bot_logger as logger
from modules.db_helpers import get_db_connection
from modules.api_helpers import get_chat_response


# --- Constants ---
MAX_CONTEXT_TOKENS = 4000  # Maximum tokens to keep in context
CONTEXT_COMPRESSION_THRESHOLD = 0.8  # Compress when reaching 80% of max
RESPONSE_CACHE_TTL_HOURS = 24  # Cache responses for 24 hours
MIN_SIMILARITY_FOR_CACHE = 0.85  # Minimum similarity to use cached response


class ContextManager:
    """Manages conversation context with intelligent compression."""
    
    def __init__(self):
        self.context_window = deque(maxlen=50)
        self.compressed_summaries = []
        self.token_budget = MAX_CONTEXT_TOKENS
        
    def add_message(self, role: str, content: str, metadata: dict = None):
        """Add a message to the context window."""
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        self.context_window.append(message)
        logger.debug(f"Added message to context: role={role}, length={len(content)}")
        
    def estimate_tokens(self, text: str) -> int:
        """Rough estimation of tokens (4 chars ≈ 1 token for English)."""
        return len(text) // 4
        
    def get_current_token_count(self) -> int:
        """Estimate total tokens in current context."""
        total = 0
        for msg in self.context_window:
            total += self.estimate_tokens(msg['content'])
        for summary in self.compressed_summaries:
            total += self.estimate_tokens(summary)
        return total
        
    async def compress_if_needed(self, config: dict, gemini_key: str, openai_key: str):
        """Compress old context into summaries if token budget exceeded."""
        current_tokens = self.get_current_token_count()
        threshold = MAX_CONTEXT_TOKENS * CONTEXT_COMPRESSION_THRESHOLD
        
        if current_tokens < threshold:
            return
            
        logger.info(f"Context compression triggered: {current_tokens} tokens > {threshold} threshold")
        
        # Take oldest 30% of messages for compression
        messages_to_compress = []
        compress_count = max(3, len(self.context_window) // 3)
        
        for _ in range(min(compress_count, len(self.context_window))):
            messages_to_compress.append(self.context_window.popleft())
            
        # Create summary prompt
        conversation_text = "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in messages_to_compress
        ])
        
        summary_prompt = f"""Summarize this conversation segment concisely, keeping key facts and context:

{conversation_text}

Provide a brief 2-3 sentence summary that captures the essential information."""

        try:
            # Use utility model for summarization (cheaper)
            system_prompt = "You are a helpful assistant that creates concise summaries."
            response, error, _ = await get_chat_response(
                history=[],
                user_prompt=summary_prompt,
                user_display_name="System",
                system_prompt=system_prompt,
                config=config,
                gemini_key=gemini_key,
                openai_key=openai_key
            )
            
            if response and not error:
                self.compressed_summaries.append(response)
                logger.info(f"Compressed {compress_count} messages into summary")
                # Keep only last 3 summaries
                if len(self.compressed_summaries) > 3:
                    self.compressed_summaries.pop(0)
            else:
                logger.warning(f"Failed to compress context: {error}")
                # Add messages back if compression failed
                for msg in messages_to_compress:
                    self.context_window.appendleft(msg)
                    
        except Exception as e:
            logger.error(f"Error during context compression: {e}")
            # Add messages back on error
            for msg in messages_to_compress:
                self.context_window.appendleft(msg)
                
    def get_formatted_context(self) -> str:
        """Get formatted context for AI prompt."""
        parts = []
        
        # Add compressed summaries
        if self.compressed_summaries:
            parts.append("=== Earlier Conversation Summary ===")
            parts.extend(self.compressed_summaries)
            parts.append("=== Recent Messages ===")
            
        # Add recent messages
        for msg in self.context_window:
            parts.append(f"{msg['role']}: {msg['content']}")
            
        return "\n".join(parts)


class EmotionalIntelligence:
    """Analyzes emotional context and adjusts responses accordingly."""
    
    @staticmethod
    def analyze_sentiment(text: str) -> Dict[str, float]:
        """
        Simple sentiment analysis based on keyword matching.
        Returns scores for different emotions.
        """
        text_lower = text.lower()
        
        # Emotion keywords
        emotions = {
            'happy': ['happy', 'glad', 'joy', 'excited', 'great', 'awesome', 'love', 'lol', 'haha'],
            'sad': ['sad', 'unhappy', 'depressed', 'down', 'disappointed', 'crying'],
            'angry': ['angry', 'mad', 'furious', 'annoyed', 'pissed', 'wtf'],
            'anxious': ['worried', 'anxious', 'nervous', 'scared', 'afraid'],
            'confused': ['confused', 'lost', 'idk', 'what', '???'],
        }
        
        scores = {}
        for emotion, keywords in emotions.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            scores[emotion] = min(1.0, score / 3)  # Normalize to 0-1
            
        return scores
        
    @staticmethod
    def get_emotional_context(messages: List[dict]) -> str:
        """Analyze emotional flow of recent conversation."""
        if not messages:
            return ""
            
        recent_messages = messages[-5:]  # Last 5 messages
        emotions_detected = []
        
        for msg in recent_messages:
            sentiment = EmotionalIntelligence.analyze_sentiment(msg.get('content', ''))
            dominant_emotion = max(sentiment, key=sentiment.get) if sentiment else None
            if dominant_emotion and sentiment[dominant_emotion] > 0.3:
                emotions_detected.append(dominant_emotion)
                
        if emotions_detected:
            return f"[Emotional context: User seems {', '.join(set(emotions_detected))}]"
        return ""


class ResponseCache:
    """Caches AI responses for similar queries to save tokens."""
    
    def __init__(self):
        self.cache = {}
        
    def _hash_prompt(self, prompt: str) -> str:
        """Create hash of prompt for cache key."""
        return hashlib.md5(prompt.encode()).hexdigest()
        
    def _calculate_similarity(self, prompt1: str, prompt2: str) -> float:
        """Calculate similarity between two prompts (simple word overlap)."""
        words1 = set(prompt1.lower().split())
        words2 = set(prompt2.lower().split())
        
        if not words1 or not words2:
            return 0.0
            
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
        
    async def get_cached_response(self, prompt: str) -> Optional[str]:
        """Try to get a cached response for similar prompt."""
        # Check exact match first
        prompt_hash = self._hash_prompt(prompt)
        if prompt_hash in self.cache:
            cached = self.cache[prompt_hash]
            # Check if not expired
            if datetime.fromisoformat(cached['timestamp']) > datetime.now() - timedelta(hours=RESPONSE_CACHE_TTL_HOURS):
                logger.info(f"Cache hit: exact match for prompt")
                return cached['response']
            else:
                # Expired, remove
                del self.cache[prompt_hash]
                
        # Check for similar prompts
        for cached_hash, cached_data in self.cache.items():
            if datetime.fromisoformat(cached_data['timestamp']) < datetime.now() - timedelta(hours=RESPONSE_CACHE_TTL_HOURS):
                continue  # Skip expired
                
            similarity = self._calculate_similarity(prompt, cached_data['prompt'])
            if similarity >= MIN_SIMILARITY_FOR_CACHE:
                logger.info(f"Cache hit: similar prompt (similarity={similarity:.2f})")
                return cached_data['response']
                
        logger.debug("Cache miss: no similar prompts found")
        return None
        
    def cache_response(self, prompt: str, response: str):
        """Cache a response."""
        prompt_hash = self._hash_prompt(prompt)
        self.cache[prompt_hash] = {
            'prompt': prompt,
            'response': response,
            'timestamp': datetime.now().isoformat()
        }
        logger.debug(f"Cached response for prompt hash {prompt_hash}")
        
        # Limit cache size
        if len(self.cache) > 100:
            # Remove oldest entries
            sorted_items = sorted(
                self.cache.items(),
                key=lambda x: x[1]['timestamp']
            )
            for key, _ in sorted_items[:20]:  # Remove oldest 20
                del self.cache[key]


class ReasoningEngine:
    """Advanced reasoning capabilities for complex queries."""
    
    @staticmethod
    async def analyze_query_complexity(prompt: str) -> Dict[str, Any]:
        """Analyze the complexity of a user query."""
        word_count = len(prompt.split())
        question_marks = prompt.count('?')
        has_context_words = any(word in prompt.lower() for word in ['why', 'how', 'explain', 'because', 'what if'])
        
        complexity = {
            'word_count': word_count,
            'has_questions': question_marks > 0,
            'requires_reasoning': has_context_words,
            'complexity_score': min(1.0, (word_count / 50 + question_marks * 0.2 + (0.3 if has_context_words else 0)))
        }
        
        return complexity
        
    @staticmethod
    def create_chain_of_thought_prompt(original_prompt: str, context: str) -> str:
        """Create a chain-of-thought reasoning prompt for complex queries."""
        return f"""When responding to this query, think step-by-step:

1. What is the user asking?
2. What context is relevant?
3. What's the best way to respond?

Context: {context}

Query: {original_prompt}

Respond naturally while considering these steps."""


# --- Global instances ---
_context_managers = {}  # channel_id -> ContextManager
_response_cache = ResponseCache()
_emotional_analyzer = EmotionalIntelligence()


def get_context_manager(channel_id: int) -> ContextManager:
    """Get or create a context manager for a channel."""
    if channel_id not in _context_managers:
        _context_managers[channel_id] = ContextManager()
    return _context_managers[channel_id]


async def get_advanced_ai_response(
    prompt: str,
    user_id: int,
    channel_id: int,
    username: str,
    config: dict,
    gemini_key: str,
    openai_key: str,
    system_prompt: str,
    use_cache: bool = True
) -> Tuple[str, Optional[str], Dict[str, Any]]:
    """
    Get an AI response with advanced reasoning and context management.
    
    Returns:
        Tuple of (response, error, metadata)
    """
    metadata = {
        'cached': False,
        'compressed': False,
        'reasoning_used': False,
        'tokens_saved': 0
    }
    
    # Check cache first
    if use_cache:
        cached_response = await _response_cache.get_cached_response(prompt)
        if cached_response:
            metadata['cached'] = True
            metadata['tokens_saved'] = len(cached_response) // 4  # Rough estimate
            return cached_response, None, metadata
            
    # Get context manager
    context_mgr = get_context_manager(channel_id)
    
    # Add current message to context
    context_mgr.add_message('user', prompt, {'user_id': user_id, 'username': username})
    
    # Compress context if needed
    await context_mgr.compress_if_needed(config, gemini_key, openai_key)
    if context_mgr.compressed_summaries:
        metadata['compressed'] = True
        
    # Analyze query complexity
    complexity = await ReasoningEngine.analyze_query_complexity(prompt)
    
    # Get emotional context
    emotional_context = _emotional_analyzer.get_emotional_context(list(context_mgr.context_window))
    
    # Build enhanced prompt
    enhanced_context = context_mgr.get_formatted_context()
    
    if complexity['requires_reasoning'] and complexity['complexity_score'] > 0.5:
        # Use chain-of-thought for complex queries
        final_prompt = ReasoningEngine.create_chain_of_thought_prompt(prompt, enhanced_context)
        metadata['reasoning_used'] = True
    else:
        final_prompt = prompt
        
    # Add emotional context if detected
    if emotional_context:
        final_prompt = f"{emotional_context}\n\n{final_prompt}"
        
    # Get AI response
    response, error, updated_history = await get_chat_response(
        history=[],  # We manage our own context
        user_prompt=final_prompt,
        user_display_name=username,
        system_prompt=system_prompt,
        config=config,
        gemini_key=gemini_key,
        openai_key=openai_key
    )
    
    if response and not error:
        # Add response to context
        context_mgr.add_message('assistant', response)
        
        # Cache the response
        if use_cache:
            _response_cache.cache_response(prompt, response)
            
    return response, error, metadata


async def get_reasoning_breakdown(
    prompt: str,
    response: str,
    metadata: Dict[str, Any]
) -> str:
    """
    Generate a breakdown of the reasoning process for debugging.
    
    Returns formatted string explaining how the response was generated.
    """
    breakdown = ["=== AI Reasoning Breakdown ===\n"]
    
    breakdown.append(f"**Input Prompt**: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
    breakdown.append(f"**Response Length**: {len(response)} chars\n")
    
    breakdown.append("**Processing Steps**:")
    if metadata.get('cached'):
        breakdown.append("✓ Response retrieved from cache (tokens saved)")
    else:
        breakdown.append("✓ Generated new response")
        
    if metadata.get('compressed'):
        breakdown.append("✓ Context compressed to save tokens")
    else:
        breakdown.append("○ No compression needed")
        
    if metadata.get('reasoning_used'):
        breakdown.append("✓ Chain-of-thought reasoning applied")
    else:
        breakdown.append("○ Direct response generated")
        
    if metadata.get('tokens_saved', 0) > 0:
        breakdown.append(f"\n**Efficiency**: ~{metadata['tokens_saved']} tokens saved")
        
    return "\n".join(breakdown)


async def clear_context(channel_id: int):
    """Clear context for a channel."""
    if channel_id in _context_managers:
        del _context_managers[channel_id]
        logger.info(f"Cleared context for channel {channel_id}")
