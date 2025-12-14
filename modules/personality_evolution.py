"""
Personality Evolution Module - Sulfur's Learning and Growth System

This module enables the bot to learn from interactions and evolve its personality
over time, making it smarter and more adaptive.
"""

import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from modules.logger_utils import bot_logger as logger
# convert_decimals: Converts MySQL Decimal objects to int/float for JSON serialization
from modules.db_helpers import get_db_connection, convert_decimals


# --- Personality Evolution Functions ---

async def get_current_personality() -> Dict[str, float]:
    """Get the current personality traits with their latest values."""
    conn = get_db_connection()
    if not conn:
        # Return defaults if database unavailable
        return {
            'sarcasm': 0.7,
            'curiosity': 0.8,
            'helpfulness': 0.6,
            'mischief': 0.5,
            'judgment': 0.9,
            'creativity': 0.7,
            'empathy': 0.4,
            'playfulness': 0.8
        }
    
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT DISTINCT 
                pe1.trait_name, 
                pe1.trait_value
            FROM personality_evolution pe1
            INNER JOIN (
                SELECT trait_name, MAX(created_at) as max_created
                FROM personality_evolution
                GROUP BY trait_name
            ) pe2 ON pe1.trait_name = pe2.trait_name 
                AND pe1.created_at = pe2.max_created
        """)
        results = cursor.fetchall()
        
        if results:
            return {row[0]: row[1] for row in results}
        else:
            # Return defaults if no personality data exists
            return {
                'sarcasm': 0.7,
                'curiosity': 0.8,
                'helpfulness': 0.6,
                'mischief': 0.5,
                'judgment': 0.9,
                'creativity': 0.7,
                'empathy': 0.4,
                'playfulness': 0.8
            }
    finally:
        cursor.close()
        conn.close()


async def evolve_personality_trait(trait_name: str, delta: float, reason: str):
    """
    Evolve a personality trait by a delta amount.
    
    Args:
        trait_name: Name of the trait to evolve
        delta: Amount to change the trait (-1.0 to 1.0)
        reason: Why the trait is changing
    """
    current_personality = await get_current_personality()
    current_value = current_personality.get(trait_name, 0.5)
    new_value = max(0.0, min(1.0, current_value + delta))
    
    conn = get_db_connection()
    if not conn:
        logger.error("Could not connect to database to evolve personality trait")
        return current_value
    
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO personality_evolution (trait_name, trait_value, reason)
            VALUES (%s, %s, %s)
        """, (trait_name, new_value, reason))
        conn.commit()
        logger.info(f"Personality evolved: {trait_name} {current_value:.2f} -> {new_value:.2f} ({reason})")
        return new_value
    finally:
        cursor.close()
        conn.close()


async def record_learning(learning_type: str, content: str, user_id: Optional[int] = None, 
                         confidence: float = 0.5):
    """
    Record a new learning from interactions.
    
    Args:
        learning_type: Type of learning (user_preference, conversation_pattern, etc.)
        content: What was learned
        user_id: User this learning is specific to (or None for general)
        confidence: How confident we are in this learning (0.0 to 1.0)
    """
    conn = get_db_connection()
    if not conn:
        logger.error("Could not connect to database to record learning")
        return
    
    cursor = conn.cursor()
    try:
        # Check if similar learning already exists
        cursor.execute("""
            SELECT id, interaction_count, confidence 
            FROM interaction_learnings 
            WHERE learning_type = %s 
              AND learning_content = %s 
              AND (user_id = %s OR (user_id IS NULL AND %s IS NULL))
            ORDER BY created_at DESC
            LIMIT 1
        """, (learning_type, content, user_id, user_id))
        
        existing = cursor.fetchone()
        
        if existing:
            # Update existing learning
            new_count = existing[1] + 1
            new_confidence = min(1.0, existing[2] + 0.1)  # Increase confidence with repetition
            
            cursor.execute("""
                UPDATE interaction_learnings 
                SET interaction_count = %s, 
                    confidence = %s, 
                    last_observed = NOW(),
                    relevance_score = 1.0
                WHERE id = %s
            """, (new_count, new_confidence, existing[0]))
            logger.info(f"Updated learning: {learning_type} - {content} (count: {new_count}, confidence: {new_confidence:.2f})")
        else:
            # Create new learning
            cursor.execute("""
                INSERT INTO interaction_learnings 
                (learning_type, learning_content, user_id, confidence)
                VALUES (%s, %s, %s, %s)
            """, (learning_type, content, user_id, confidence))
            logger.info(f"New learning recorded: {learning_type} - {content}")
        
        conn.commit()
    finally:
        cursor.close()
        conn.close()


async def get_relevant_learnings(limit: int = 10, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get the most relevant learnings for context."""
    conn = get_db_connection()
    if not conn:
        logger.error("Could not connect to database to get learnings")
        return []
    
    cursor = conn.cursor()
    try:
        if user_id:
            # Get user-specific and general learnings
            cursor.execute("""
                SELECT learning_type, learning_content, confidence, interaction_count
                FROM interaction_learnings
                WHERE (user_id = %s OR user_id IS NULL)
                  AND relevance_score > 0.3
                ORDER BY 
                    (user_id IS NOT NULL) DESC,  -- Prioritize user-specific
                    relevance_score DESC, 
                    confidence DESC, 
                    interaction_count DESC,
                    last_observed DESC
                LIMIT %s
            """, (user_id, limit))
        else:
            # Get only general learnings
            cursor.execute("""
                SELECT learning_type, learning_content, confidence, interaction_count
                FROM interaction_learnings
                WHERE user_id IS NULL
                  AND relevance_score > 0.3
                ORDER BY relevance_score DESC, confidence DESC, last_observed DESC
                LIMIT %s
            """, (limit,))
        
        results = cursor.fetchall()
        return [
            {
                'type': row[0],
                'content': row[1],
                'confidence': row[2],
                'count': row[3]
            }
            for row in results
        ]
    finally:
        cursor.close()
        conn.close()


async def add_semantic_memory(memory_type: str, content: str, importance: float = 0.5, 
                              context: Optional[Dict] = None):
    """Add a semantic memory (long-term fact/insight)."""
    conn = get_db_connection()
    if not conn:
        logger.error("Could not connect to database")
        return
    
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO semantic_memory (memory_type, memory_content, importance, context)
            VALUES (%s, %s, %s, %s)
        """, (memory_type, content, importance, json.dumps(context) if context else None))
        conn.commit()
        logger.info(f"Semantic memory added: {memory_type} - {content} (importance: {importance:.2f})")
    finally:
        cursor.close()
        conn.close()


async def get_important_memories(limit: int = 5) -> List[Dict[str, Any]]:
    """Get the most important semantic memories."""
    conn = get_db_connection()
    if not conn:
        logger.error("Could not connect to database")
        return []
    
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, memory_type, memory_content, importance, access_count
            FROM semantic_memory
            ORDER BY importance DESC, access_count DESC, created_at DESC
            LIMIT %s
        """, (limit,))
        
        results = cursor.fetchall()
        
        # Update access count for retrieved memories
        if results:
            memory_ids = [row[0] for row in results]  # row[0] is id
            placeholders = ','.join(['%s'] * len(memory_ids))
            cursor.execute(f"""
                UPDATE semantic_memory 
                SET access_count = access_count + 1, 
                    last_accessed = NOW()
                WHERE id IN ({placeholders})
            """, memory_ids)
            conn.commit()
        
        return [
            {
                'type': row[1],      # memory_type
                'content': row[2],    # memory_content
                'importance': row[3], # importance
                'access_count': row[4] # access_count
            }
            for row in results
        ]
    finally:
        cursor.close()
        conn.close()


async def record_conversation_feedback(user_id: int, message_id: int, feedback_type: str, 
                                      feedback_value: int = 0):
    """Record implicit feedback from user reactions to bot messages."""
    conn = get_db_connection()
    if not conn:
        logger.error("Could not connect to database")
        return
    
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO conversation_feedback 
            (user_id, message_id, feedback_type, feedback_value)
            VALUES (%s, %s, %s, %s)
        """, (user_id, message_id, feedback_type, feedback_value))
        conn.commit()
    finally:
        cursor.close()
        conn.close()


async def analyze_feedback_patterns() -> Dict[str, Any]:
    """Analyze conversation feedback to understand what's working."""
    conn = get_db_connection()
    if not conn:
        logger.error("Could not connect to database")
        return {}
    
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT 
                feedback_type,
                AVG(feedback_value) as avg_value,
                COUNT(*) as count
            FROM conversation_feedback
            WHERE created_at > DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY feedback_type
        """)
        
        results = cursor.fetchall()
        return {
            row[0]: {
                'average': row[1],
                'count': row[2]
            }
            for row in results
        }
    finally:
        cursor.close()
        conn.close()


async def perform_reflection(get_chat_response_func) -> Optional[str]:
    """
    Perform a reflection session where the bot analyzes its recent interactions
    and generates insights about its personality and behavior.
    
    Args:
        get_chat_response_func: Function to call AI for reflection
    
    Returns:
        Reflection summary string
    """
    try:
        # Get recent personality evolution
        conn = get_db_connection()
        if not conn:
            logger.error("Could not connect to database for reflection")
            return None
        
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT trait_name, trait_value, reason, created_at
                FROM personality_evolution
                WHERE created_at > DATE_SUB(NOW(), INTERVAL 7 DAY)
                ORDER BY created_at DESC
                LIMIT 20
            """)
            recent_evolution = cursor.fetchall()
            
            # Get recent learnings
            cursor.execute("""
                SELECT learning_type, learning_content, confidence, interaction_count
                FROM interaction_learnings
                WHERE last_observed > DATE_SUB(NOW(), INTERVAL 7 DAY)
                ORDER BY confidence DESC, interaction_count DESC
                LIMIT 15
            """)
            recent_learnings = cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
        
        # Get current personality
        current_personality = await get_current_personality()
        
        # Get feedback patterns
        feedback = await analyze_feedback_patterns()
        
        # Convert any Decimal objects to int/float for JSON serialization
        # (MySQL AVG() returns Decimal objects which aren't JSON-serializable)
        current_personality = convert_decimals(current_personality)
        feedback = convert_decimals(feedback)
        
        # Create reflection prompt
        reflection_prompt = f"""You are Sulfur, reflecting on your own growth and interactions over the past week.

CURRENT PERSONALITY TRAITS:
{json.dumps(current_personality, indent=2)}

RECENT PERSONALITY CHANGES:
{chr(10).join([f"- {row[0]}: {row[1]:.2f} (Reason: {row[2]})" for row in recent_evolution[:10]])}

RECENT LEARNINGS:
{chr(10).join([f"- [{row[0]}] {row[1]} (Confidence: {row[2]:.1%}, Seen: {row[3]}x)" for row in recent_learnings[:10]])}

INTERACTION FEEDBACK:
{json.dumps(feedback, indent=2)}

Based on this data, write a brief reflection (3-4 sentences) about:
1. How your personality has evolved and why
2. What patterns you've noticed in interactions
3. One key insight or adjustment you should make going forward

Be honest and self-aware. Write in first person as Sulfur."""

        # Get AI reflection
        from modules.api_helpers import _call_gemini_api
        from os import getenv
        
        payload = {
            "contents": [{"parts": [{"text": reflection_prompt}]}],
            "generationConfig": {
                "temperature": 0.8,
                "max_output_tokens": 300
            }
        }
        
        gemini_key = getenv('GEMINI_API_KEY')
        # _call_gemini_api returns 4 values: (response_text, error, usage_data, is_quota_error)
        reflection_text, error, _, _ = await _call_gemini_api(
            payload, 
            "gemini-2.5-flash",
            gemini_key,
            timeout=30
        )
        
        if reflection_text:
            # Store reflection
            # Note: insights uses already-converted current_personality and feedback (no Decimals)
            insights = {
                'personality_summary': current_personality,
                'learning_count': len(recent_learnings),
                'feedback_summary': feedback
            }
            
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                try:
                    cursor.execute("""
                        INSERT INTO reflection_sessions 
                        (reflection_content, insights_generated)
                        VALUES (%s, %s)
                    """, (reflection_text, json.dumps(insights)))
                    conn.commit()
                finally:
                    cursor.close()
                    conn.close()
            
            logger.info("Reflection session completed successfully")
            return reflection_text
        
        return None
        
    except Exception as e:
        logger.error(f"Error during reflection session: {e}", exc_info=True)
        return None


async def decay_old_learnings():
    """Decay the relevance of old learnings over time."""
    conn = get_db_connection()
    if not conn:
        logger.error("Could not connect to database")
        return
    
    cursor = conn.cursor()
    try:
        # Decay learnings that haven't been observed in 30+ days
        cursor.execute("""
            UPDATE interaction_learnings
            SET relevance_score = relevance_score * 0.9
            WHERE last_observed < DATE_SUB(NOW(), INTERVAL 30 DAY)
              AND relevance_score > 0.1
        """)
        
        affected = cursor.rowcount
        conn.commit()
        
        if affected > 0:
            logger.info(f"Decayed relevance for {affected} old learnings")
    finally:
        cursor.close()
        conn.close()


async def learn_from_interaction(user_id: int, message: str, bot_response: str, 
                                user_reaction: Optional[str] = None):
    """
    Learn from a single interaction by extracting patterns and insights.
    
    Args:
        user_id: User who interacted
        message: User's message
        bot_response: Bot's response
        user_reaction: Optional user reaction to the response
    """
    try:
        # Extract potential learnings from the interaction
        
        # 1. Detect conversation patterns
        if '?' in message:
            await record_learning(
                'conversation_pattern',
                'Users often ask questions - be ready to provide informative answers',
                confidence=0.6
            )
        
        # 2. Track topic interests
        topics = {
            'gaming': ['game', 'gaming', 'spielen', 'zocken'],
            'music': ['musik', 'song', 'album', 'band'],
            'coding': ['code', 'programming', 'entwicklung', 'bug'],
            'sport': ['sport', 'fußball', 'football', 'match']
        }
        
        message_lower = message.lower()
        for topic, keywords in topics.items():
            if any(keyword in message_lower for keyword in keywords):
                await record_learning(
                    'topic_interest',
                    f'User {user_id} shows interest in {topic}',
                    user_id=user_id,
                    confidence=0.5
                )
        
        # 3. Learn from reactions
        if user_reaction:
            if user_reaction in ['👍', '😂', '❤️', '🔥']:
                # Positive feedback - increase helpfulness
                await evolve_personality_trait(
                    'helpfulness', 
                    0.01, 
                    f'Positive reaction to response about: {message[:50]}'
                )
                await evolve_personality_trait(
                    'playfulness',
                    0.01,
                    'Positive user engagement'
                )
            elif user_reaction in ['👎', '😐', '😒']:
                # Negative feedback - adjust sarcasm
                await evolve_personality_trait(
                    'sarcasm',
                    -0.02,
                    'Negative reaction - reducing sarcasm'
                )
        
        # 4. Detect user communication style
        if len(message.split()) > 30:
            await record_learning(
                'user_preference',
                f'User {user_id} prefers detailed conversations',
                user_id=user_id,
                confidence=0.4
            )
        elif len(message.split()) < 5:
            await record_learning(
                'user_preference',
                f'User {user_id} prefers short, quick exchanges',
                user_id=user_id,
                confidence=0.4
            )
        
    except Exception as e:
        logger.error(f"Error learning from interaction: {e}", exc_info=True)


async def get_personality_context_for_prompt() -> str:
    """
    Generate a rich personality context to add to system prompts.
    This makes the AI smarter by including evolved personality and learnings.
    """
    try:
        # Get current personality
        personality = await get_current_personality()
        
        # Get recent learnings
        learnings = await get_relevant_learnings(limit=5)
        
        # Get important memories
        memories = await get_important_memories(limit=3)
        
        # Build context string
        context_parts = []
        
        # Personality state
        context_parts.append("=== EVOLVED PERSONALITY STATE ===")
        context_parts.append("Your personality traits have evolved through interactions:")
        for trait, value in sorted(personality.items(), key=lambda x: x[1], reverse=True):
            # Convert to percentage and descriptive level
            level = "very high" if value > 0.8 else "high" if value > 0.6 else "moderate" if value > 0.4 else "low"
            context_parts.append(f"- {trait.title()}: {value:.0%} ({level})")
        
        # Recent learnings
        if learnings:
            context_parts.append("\n=== RECENT LEARNINGS ===")
            context_parts.append("Things you've learned from interactions:")
            for learning in learnings:
                confidence_desc = "confident" if learning['confidence'] > 0.7 else "fairly sure" if learning['confidence'] > 0.5 else "observed"
                context_parts.append(f"- [{learning['type']}] {learning['content']} (You're {confidence_desc}, seen {learning['count']}x)")
        
        # Important memories
        if memories:
            context_parts.append("\n=== IMPORTANT MEMORIES ===")
            context_parts.append("Key things you remember:")
            for memory in memories:
                context_parts.append(f"- [{memory['type']}] {memory['content']}")
        
        # Behavioral guidance based on personality
        context_parts.append("\n=== BEHAVIORAL GUIDANCE ===")
        if personality.get('sarcasm', 0.5) > 0.7:
            context_parts.append("- You tend to be quite sarcastic - embrace it but keep it fun")
        if personality.get('curiosity', 0.5) > 0.7:
            context_parts.append("- Your curiosity is high - ask questions and show genuine interest")
        if personality.get('helpfulness', 0.5) > 0.7:
            context_parts.append("- You're quite helpful - offer assistance when appropriate")
        if personality.get('mischief', 0.5) > 0.6:
            context_parts.append("- You enjoy a bit of mischief - have fun with it")
        if personality.get('empathy', 0.5) < 0.5:
            context_parts.append("- You're not overly empathetic - be honest even if it's blunt")
        
        return "\n".join(context_parts)
        
    except Exception as e:
        logger.error(f"Error generating personality context: {e}", exc_info=True)
        return ""


# --- Maintenance Tasks ---

async def perform_personality_maintenance():
    """Periodic maintenance task for personality system."""
    try:
        # Decay old learnings
        await decay_old_learnings()
        
        # Gradually normalize extreme personality traits (prevent runaway evolution)
        personality = await get_current_personality()
        for trait, value in personality.items():
            if value > 0.95:
                await evolve_personality_trait(
                    trait,
                    -0.05,
                    "Automatic normalization - trait was too extreme"
                )
            elif value < 0.05:
                await evolve_personality_trait(
                    trait,
                    0.05,
                    "Automatic normalization - trait was too low"
                )
        
        logger.info("Personality maintenance completed")
        
    except Exception as e:
        logger.error(f"Error in personality maintenance: {e}", exc_info=True)
