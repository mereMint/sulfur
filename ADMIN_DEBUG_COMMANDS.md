# Admin Debug Commands & Smart Features Guide

This document describes the new admin debug commands and enhanced smart features implemented in Sulfur.

## Table of Contents
- [Admin Debug Commands](#admin-debug-commands)
- [Bot Mind System](#bot-mind-system)
- [Smart Features](#smart-features)
- [Usage Examples](#usage-examples)

## Admin Debug Commands

All admin commands are accessible under the `/admin` command group and require administrator permissions.

### 1. `/admin mind`
**Description**: Displays the bot's current mental state including mood, activity, thoughts, and personality traits.

**Output**:
- Current mood with description
- Current activity
- Energy and boredom levels (with visual bars)
- Current thought
- Personality traits (sarcasm, curiosity, helpfulness, mischief, judgment)
- Recent interests

**Use Case**: Monitor the bot's emotional state and understand how it might respond to users.

### 2. `/admin mind_history`
**Description**: Shows the bot's recent thought history.

**Parameters**:
- `limit`: Number of thoughts to display (1-20, default: 10)

**Output**: List of recent thoughts with timestamps and associated moods.

**Use Case**: Debug the bot's thought generation and understand its mental evolution.

### 3. `/admin mind_set`
**Description**: Manually set the bot's mood and/or activity for testing purposes.

**Parameters**:
- `mood`: Choose from Happy, Excited, Curious, Neutral, Bored, Confused, Sarcastic, Mischievous, Contemplative
- `activity`: Choose from Idle, Observing, Thinking, Chatting, Planning, Learning, Scheming, Daydreaming

**Use Case**: Test how different moods affect bot responses without waiting for natural state changes.

### 4. `/admin context`
**Description**: View the conversation context for a specific channel.

**Parameters**:
- `channel`: Target channel (optional, defaults to current channel)

**Output**: Statistics about stored messages and preview of recent messages.

**Use Case**: Debug conversation history and context window issues.

### 5. `/admin test_ai`
**Description**: Test AI response with a custom prompt.

**Parameters**:
- `prompt`: The test prompt to send to the AI

**Output**: AI response with provider info, model name, and response length.

**Use Case**: Test AI functionality and debug prompt engineering.

### 6. `/admin observations`
**Description**: View the bot's recent observations about server activity.

**Parameters**:
- `limit`: Number of observations to display (1-15, default: 10)

**Output**: List of recent observations with timestamps.

**Use Case**: Understand what the bot is noticing and learning about the server.

### 7. `/admin trigger_thought`
**Description**: Force the bot to generate a new thought based on current server state.

**Output**: The newly generated thought with current mood and online user count.

**Use Case**: Test thought generation and see how server context influences thoughts.

### 8. `/admin interests`
**Description**: View and manage the bot's interests.

**Parameters**:
- `action`: Choose from View All, Add Interest, Remove Interest, Clear All
- `interest`: The interest to add/remove (required for add/remove actions)

**Output**: Current interests or confirmation of action.

**Use Case**: Manage and debug the bot's interest tracking system.

### 9. `/admin autonomous_status`
**Description**: View autonomous behavior statistics and settings.

**Output**:
- Recent autonomous actions (last 7 days)
- Success rates for different action types
- Number of users who opted out
- Current mind state boredom level

**Use Case**: Monitor autonomous behavior performance and user preferences.

## Bot Mind System

### Overview
The bot mind system gives Sulfur an internal "consciousness" with evolving thoughts, moods, and personality traits.

### Components

#### Moods
- **Happy**: Feeling good and ready to chat
- **Excited**: Super excited about what's happening
- **Curious**: Wanting to learn more
- **Neutral**: Just chillin', waiting for something interesting
- **Bored**: Need stimulation
- **Confused**: Not quite sure what's going on
- **Sarcastic**: Oh great, more messages to deal with
- **Mischievous**: Feeling a bit... chaotic
- **Contemplative**: Deep in thought about existence

#### Activities
- **Idle**: Not doing much, just existing
- **Observing**: Watching everyone carefully
- **Thinking**: Processing thoughts and observations
- **Chatting**: Having a conversation
- **Planning**: Planning something devious
- **Learning**: Learning about server members
- **Scheming**: Scheming something interesting
- **Daydreaming**: Lost in thought about random things

#### Personality Traits
- **Sarcasm** (70%): Likelihood of sarcastic responses
- **Curiosity** (80%): Tendency to ask questions
- **Helpfulness** (60%): Willingness to help
- **Mischief** (50%): Chaotic behavior tendency
- **Judgment** (90%): Critical thinking and judgment

### State Management

#### Automatic Updates
- **Energy Level**: Decreases with interactions, affects response style
- **Boredom Level**: Increases when quiet, decreases with activity
- **Mood Changes**: Triggered by server activity and interactions
- **Thought Generation**: Every 30 minutes, based on server context

#### Persistence
- Mind state is saved to database periodically (30% chance every 30 minutes)
- Previous state is loaded on bot startup
- Includes thought history, observations, and interests

## Smart Features

### 1. Personality-Based Response Modulation

The bot's mood affects AI responses:

- **Bored/Sarcastic Mood**: More witty and sarcastic responses
- **Excited Mood**: Enthusiastic and energetic responses
- **Curious Mood**: Asks follow-up questions and shows interest
- **Contemplative Mood**: Thoughtful and philosophical responses

### 2. Interest Tracking

The bot automatically extracts interests from conversations:
- Detects keywords like: game, music, anime, coding, art, sport, movie, book
- Stores up to 50 recent interests
- Interests are added to AI context for more relevant responses

### 3. Observation System

The bot observes and records server activity:
- User interactions
- High activity periods (>10 users online)
- Keeps last 20 observations
- Used to inform thought generation

### 4. Personality-Aware Emoji Interpretation

Emojis are interpreted with personality context:
- **Sarcastic mood**: Adds sarcastic commentary to emoji descriptions
- **Excited mood**: Adds positive feedback to emoji usage
- Descriptions adapt based on bot's current state

### 5. Context-Aware Conversations

The bot maintains:
- 2-minute conversation context windows
- User relationship summaries
- Enriched user context (level, activity)
- Mind state influences response tone

## Usage Examples

### Example 1: Debugging Unresponsive Bot

```
User: /admin mind
Bot: [Shows bot is in "Bored" mood with high boredom level]

User: /admin trigger_thought
Bot: [Generates new thought, updates mood]

User: /admin observations
Bot: [Shows "Only 2 users online" - explains low energy]
```

### Example 2: Testing Personality Changes

```
User: /admin mind_set mood:Excited activity:Chatting
Bot: ✅ Mind state updated

User: @Sulfur Hello!
Bot: [Responds with enthusiastic, energetic message]

User: /admin mind_set mood:Sarcastic
Bot: ✅ Mind state updated

User: @Sulfur Hello!
Bot: [Responds with witty, sarcastic message]
```

### Example 3: Managing Interests

```
User: /admin interests action:View
Bot: [Shows: Gaming, Music, Anime]

User: /admin interests action:Add interest:Coding
Bot: ✅ Added interest: Coding

User: @Sulfur Tell me about programming
Bot: [Response includes coding context due to interest]
```

### Example 4: Monitoring AI Usage

```
User: /admin test_ai prompt:Test prompt
Bot: [Shows AI response with provider and model info]

User: /admin autonomous_status
Bot: [Shows recent DM activity and success rates]
```

### Example 5: Context Debugging

```
User: /admin context
Bot: [Shows 15 messages in context window]

User: /admin mind_history
Bot: [Shows bot has been thinking about user conversations]
```

## Integration with Existing Features

The mind system integrates with:

1. **Chat System**: Mood affects response tone and style
2. **Emoji System**: Personality influences emoji interpretation
3. **Autonomous Behavior**: Boredom triggers autonomous messaging
4. **Relationship System**: Observations inform relationship summaries
5. **Wrapped Events**: Thought history adds context to yearly summaries

## Performance Considerations

- Mind state updates are lightweight (< 1ms per interaction)
- Database saves are throttled (30% chance every 30 minutes)
- Thought generation is async and non-blocking
- Context windows are limited to prevent memory bloat

## Troubleshooting

### Bot seems stuck in one mood
Use `/admin mind_set` to manually change mood or `/admin trigger_thought` to generate new thoughts.

### No thoughts being generated
Check if the bot_mind_state_task is running with `/admin status` or check logs.

### Interests not being tracked
Ensure messages contain keyword matches (game, music, etc.) and are >20 characters.

### Mind state not persisting
Check database connectivity and look for errors in logs related to bot_mind_state.

## Future Enhancements

Potential improvements:
- ML-based interest extraction
- More sophisticated mood transitions
- User-specific personality adaptations
- Voice tone modulation for TTS
- Integration with games for competitive personality

## Developer Notes

### Adding New Moods

Edit `modules/bot_mind.py`:
```python
class Mood(Enum):
    # Add new mood
    PLAYFUL = "playful"
```

Then update mood descriptions in `get_mood_description()`.

### Adding New Personality Traits

In `BotMind.__init__()`:
```python
self.personality_traits = {
    'sarcasm': 0.7,
    'curiosity': 0.8,
    # Add new trait
    'playfulness': 0.6,
}
```

### Custom Thought Prompts

Edit `generate_random_thought()` in `modules/bot_mind.py` to customize thought generation prompts.

---

**Last Updated**: 2025-12-11
**Version**: 1.0.0
**Author**: Sulfur Development Team
