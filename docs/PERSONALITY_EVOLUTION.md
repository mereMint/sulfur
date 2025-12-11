# AI Personality Evolution System

## Overview

The Sulfur bot now features a comprehensive **Personality Evolution System** that enables the AI to learn from interactions and evolve its personality over time, making it progressively smarter and more adaptive.

## Key Features

### 1. **Dynamic Personality Traits**
The bot's personality is no longer static. It evolves based on interactions:
- **Sarcasm** (0.0 - 1.0): How sarcastic the bot is
- **Curiosity** (0.0 - 1.0): How interested/questioning it is
- **Helpfulness** (0.0 - 1.0): How much it tries to assist
- **Mischief** (0.0 - 1.0): How playful/chaotic it is
- **Judgment** (0.0 - 1.0): How critical/judgmental it is
- **Creativity** (0.0 - 1.0): How creative in responses
- **Empathy** (0.0 - 1.0): How empathetic/caring
- **Playfulness** (0.0 - 1.0): How fun/lighthearted

### 2. **Learning System**
The bot learns from every interaction:
- **Conversation Patterns**: Identifies common patterns (questions, topics, etc.)
- **User Preferences**: Learns individual user communication styles
- **Topic Interests**: Tracks what topics users engage with
- **Response Effectiveness**: Learns from user reactions (👍, ❤️, etc.)

### 3. **Semantic Memory**
Long-term memory system for important information:
- **Facts**: Important things to remember
- **Preferences**: User and server preferences
- **Relationships**: Key relationship insights
- **Events**: Memorable events
- **Insights**: Self-generated insights

### 4. **Self-Reflection**
The bot periodically analyzes its own behavior:
- **Daily Reflections**: AI-powered self-analysis every 24 hours
- **Growth Tracking**: Monitors personality evolution
- **Pattern Recognition**: Identifies what works and what doesn't
- **Adaptive Learning**: Adjusts behavior based on insights

### 5. **Feedback Learning**
Implicit learning from user reactions:
- **Positive Reactions** (👍, ❤️, 🔥, 😂, 🎉): Increase helpfulness and playfulness
- **Negative Reactions** (👎, 😐, 😒, 🙄): Adjust sarcasm and approach
- **No Reaction**: Neutral data point

## How It Works

### Interaction Flow

```
User Message → Bot Processing → Response
      ↓
Learning Extraction
      ↓
┌─────────────────────────┐
│  Pattern Detection      │
│  - Topics               │
│  - Communication Style  │
│  - User Preferences     │
└─────────────────────────┘
      ↓
┌─────────────────────────┐
│  Personality Evolution  │
│  - Trait Adjustments    │
│  - Learning Storage     │
│  - Memory Consolidation │
└─────────────────────────┘
      ↓
┌─────────────────────────┐
│  Enhanced Context       │
│  - Evolved Personality  │
│  - Recent Learnings     │
│  - Important Memories   │
└─────────────────────────┘
      ↓
Future Responses Are Smarter!
```

### Context Enhancement

Every AI response now includes:

```
=== EVOLVED PERSONALITY STATE ===
Your personality traits have evolved through interactions:
- Judgment: 90% (very high)
- Playfulness: 80% (high)
- Curiosity: 80% (high)
- Creativity: 70% (high)
- Sarcasm: 68% (high)
...

=== RECENT LEARNINGS ===
Things you've learned from interactions:
- [topic_interest] User 123456 shows interest in gaming (You're confident, seen 5x)
- [conversation_pattern] Users often ask questions - be ready (You're fairly sure, seen 12x)
- [user_preference] User 789012 prefers short, quick exchanges (You're observed, seen 3x)

=== IMPORTANT MEMORIES ===
Key things you remember:
- [fact] The server has a weekly game night on Fridays
- [preference] Most users prefer German responses with occasional English slang
- [insight] Being too sarcastic can backfire - balance is key

=== BEHAVIORAL GUIDANCE ===
- You tend to be quite sarcastic - embrace it but keep it fun
- Your curiosity is high - ask questions and show genuine interest
- You enjoy a bit of mischief - have fun with it
```

## Database Schema

### Tables Created

1. **`personality_evolution`**
   - Tracks all personality trait changes over time
   - Each change includes reason and timestamp
   - Enables analysis of personality drift

2. **`interaction_learnings`**
   - Stores patterns learned from conversations
   - Confidence scores increase with repetition
   - Relevance scores decay over time (30 days)
   - User-specific and general learnings

3. **`semantic_memory`**
   - Long-term memory storage
   - Importance weighting
   - Access tracking (frequently used memories stay relevant)

4. **`reflection_sessions`**
   - Bot's self-analysis records
   - Insights generated from reflection
   - Personality adjustments made

5. **`conversation_feedback`**
   - User reactions to bot messages
   - Implicit learning data
   - Tracks positive/negative patterns

## Periodic Tasks

### 1. Personality Maintenance (Every 6 hours)
- Decays old learnings (relevance score reduction)
- Normalizes extreme personality traits
- Prevents runaway evolution

### 2. Daily Reflection (Every 24 hours)
- AI analyzes its own evolution
- Generates insights about what's working
- Identifies patterns in interactions
- Suggests personality adjustments

### 3. Bot Mind State (Every 30 minutes)
- Updates mood and activity
- Generates thoughts
- Observes server activity
- **NEW**: Loads evolved personality from database

## Configuration

No additional configuration needed! The system works automatically once the database migration is run.

### Optional Tuning

In `modules/personality_evolution.py`, you can adjust:

```python
# Evolution rates
await evolve_personality_trait('helpfulness', 0.01, 'reason')  # ±0.01 per adjustment

# Learning confidence thresholds
confidence=0.5  # Default confidence for new learnings

# Decay rates
relevance_score = relevance_score * 0.9  # 10% decay after 30 days

# Normalization thresholds
if value > 0.95:  # Too high
if value < 0.05:  # Too low
```

## Usage Examples

### Monitor Personality Evolution

```python
# Get current personality
personality = await get_current_personality()
print(personality)
# {'sarcasm': 0.72, 'curiosity': 0.85, ...}
```

### View Recent Learnings

```python
# Get learnings for a specific user
learnings = await get_relevant_learnings(limit=10, user_id=123456)
for learning in learnings:
    print(f"{learning['type']}: {learning['content']}")
```

### Access Semantic Memories

```python
# Get important memories
memories = await get_important_memories(limit=5)
for memory in memories:
    print(f"{memory['type']}: {memory['content']} (importance: {memory['importance']})")
```

## Admin Commands

View the bot's mental state (includes personality):
```
/mind
```

This will show:
- Current mood and activity
- Personality traits with percentages
- Recent thoughts
- Energy and boredom levels

## Monitoring & Debugging

### Logs to Watch

```
[INFO] Personality evolved: sarcasm 0.70 -> 0.72 (Positive reaction to response about: ...)
[INFO] New learning recorded: topic_interest - User 123 shows interest in gaming
[INFO] Semantic memory added: insight - Being too sarcastic can backfire
[INFO] Reflection completed: I've noticed my sarcasm has increased...
[INFO] Personality maintenance completed
```

### Database Queries

Check personality evolution:
```sql
SELECT trait_name, trait_value, reason, created_at 
FROM personality_evolution 
ORDER BY created_at DESC 
LIMIT 20;
```

View learnings:
```sql
SELECT learning_type, learning_content, confidence, interaction_count 
FROM interaction_learnings 
WHERE relevance_score > 0.5 
ORDER BY confidence DESC, interaction_count DESC 
LIMIT 10;
```

Recent reflections:
```sql
SELECT reflection_content, created_at 
FROM reflection_sessions 
ORDER BY created_at DESC 
LIMIT 5;
```

## Migration

Run the database migration:
```bash
mysql -u sulfur_bot_user -p sulfur_bot < scripts/db_migrations/016_personality_evolution.sql
```

This will:
- Create all 5 new tables
- Insert initial personality trait values
- Set up proper indexes for performance

## Benefits

### For Users
- **More Natural Conversations**: Bot adapts to individual communication styles
- **Better Memory**: Bot remembers preferences and patterns
- **Evolving Personality**: Bot grows and changes based on community

### For the Bot
- **Self-Improvement**: Learns what works and adjusts accordingly
- **Context Awareness**: Richer understanding of users and topics
- **Personality Depth**: More nuanced, human-like personality

### For Developers
- **Data-Driven**: Evolution is tracked and analyzable
- **Configurable**: Easy to tune evolution rates and thresholds
- **Extensible**: Easy to add new learning types or traits

## Troubleshooting

### Personality Not Evolving
- Check logs for learning events
- Verify database migration ran successfully
- Ensure tasks are running (personality_maintenance_task, reflection_task)

### Too Much/Too Little Evolution
Adjust evolution deltas in `learn_from_interaction()`:
```python
# Current: ±0.01 per interaction
await evolve_personality_trait('helpfulness', 0.01, 'reason')

# Faster evolution: ±0.05
await evolve_personality_trait('helpfulness', 0.05, 'reason')

# Slower evolution: ±0.005
await evolve_personality_trait('helpfulness', 0.005, 'reason')
```

### Old Learnings Not Decaying
Check the maintenance task is running:
```python
if not personality_maintenance_task.is_running():
    personality_maintenance_task.start()
```

### Reflection Not Working
- Ensure Gemini API key is valid
- Check reflection_task is running
- Verify there's enough interaction data (reflection needs at least a few interactions)

## Future Enhancements

Potential additions:
- **Mood-Based Evolution**: Different moods lead to different learning patterns
- **User-Specific Personalities**: Different personality for different users
- **Community Trends**: Learn from overall server patterns
- **Emotional Intelligence**: Better understanding of emotional context
- **Multi-Modal Learning**: Learn from images, voice, etc.
- **Personality Templates**: Save/load personality states
- **A/B Testing**: Test different personalities and learn which works best

## Technical Details

### Learning Confidence System
- Initial confidence: 0.5 (50%)
- Each observation: +0.1 confidence (max 1.0)
- Used to weight learnings in prompts

### Relevance Decay
- Old learnings (30+ days): -10% relevance
- Minimum relevance: 0.1 (10%)
- Learnings below 0.3 relevance are excluded from context

### Personality Normalization
- Traits above 0.95: -0.05 adjustment
- Traits below 0.05: +0.05 adjustment
- Prevents extreme values that could break personality

### Memory Access Tracking
- Each memory access: +1 to access_count
- Frequently accessed memories have higher priority
- Unused memories naturally fade in importance

## Credits

Developed to address the issue: "the ai isn't smarter it writes just like the time it didn't have the new mind features also make it's personality and being evolve from itself and by interactions"

This system makes the AI genuinely smarter by:
1. Learning from every interaction
2. Evolving personality based on what works
3. Building semantic memory of important information
4. Self-reflecting to identify improvement areas
5. Providing rich, evolved context to every response

The bot is now truly adaptive and grows with the community!
