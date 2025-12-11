# Autonomous Bot Features Documentation

This document describes the new autonomous features added to Sulfur Bot that enable more proactive and intelligent interactions with users.

## Table of Contents
- [Overview](#overview)
- [User Settings](#user-settings)
- [Focus Timer](#focus-timer)
- [Autonomous Messaging](#autonomous-messaging)
- [Voice TTS](#voice-tts)
- [Configuration](#configuration)
- [Database Schema](#database-schema)

## Overview

Sulfur Bot now includes autonomous capabilities that allow it to:
- **Proactively message users** based on relationship context and activity
- **Join voice channels** and communicate via text-to-speech
- **Monitor user activity** during focus sessions
- **Provide focus timers** with Pomodoro presets
- **Learn from interactions** to improve decision-making

## User Settings

Users can control how the bot interacts with them using the `/settings` command.

### Commands

#### `/settings`
Manage your preferences for autonomous bot features.

**Options:**
- `feature: view` - Display current settings
- `feature: messages` - Allow/disallow autonomous messages
- `feature: calls` - Allow/disallow autonomous voice calls

**Examples:**
```
/settings feature:view
/settings feature:messages enabled:on
/settings feature:calls enabled:off
```

### Privacy Controls

Users have full control over:
- **Autonomous Messages**: Whether the bot can DM them spontaneously
- **Autonomous Calls**: Whether the bot can join their voice channel
- **Contact Frequency**: How often the bot should reach out (low/normal/high/none)

All settings default to enabled but can be disabled at any time.

## Focus Timer

The focus timer helps users maintain concentration with activity monitoring and distraction alerts.

### Commands

#### `/focus`
Start a focus timer with optional Pomodoro presets.

**Presets:**
- **🍅 Kurz** (Short): 25 minutes work, 5 minutes break
- **🍅 Lang** (Long): 50 minutes work, 10 minutes break
- **🍅 Ultra**: 90 minutes work, 15 minutes break
- **🍅 Sprint**: 15 minutes work, 3 minutes break
- **⏱️ Eigene Zeit** (Custom): Specify your own duration
- **❌ Timer beenden** (Stop): End current timer

**Examples:**
```
/focus preset:short
/focus preset:custom minutes:45
/focus preset:stop
```

#### `/focusstats`
View your focus timer statistics.

**Parameters:**
- `days` (optional): Number of days to include (default: 7)

**Examples:**
```
/focusstats
/focusstats days:30
```

### Activity Monitoring

During an active focus session, the bot monitors:

1. **Messages**: Detects when you send messages in channels
2. **Games**: Detects when you start playing games
3. **Streaming**: Detects when you start streaming or watching videos
4. **Music**: Allows music (Spotify) as it doesn't count as a distraction

When a distraction is detected:
- A gentle reminder DM is sent
- The distraction is logged in your statistics
- You can continue or stop the timer

### Completion Notifications

When a focus timer completes:
1. **DM Notification**: Bot sends a completion message via DM
2. **Voice Notification**: If DMs are disabled and you're in a voice channel, bot joins and announces completion
3. **Statistics**: Session stats are saved including distractions

## Autonomous Messaging

The bot can now autonomously reach out to users to start conversations.

### How It Works

Every 2 hours, the autonomous messaging task runs:
1. Checks online members in all guilds
2. Selects up to 5 random candidates
3. For each candidate:
   - Checks if they allow autonomous messages
   - Checks cooldown period (default: 24 hours)
   - Analyzes recent conversation context
   - Generates a natural conversation starter using AI
   - Sends DM if all checks pass

### Decision Making

The bot considers:
- **User Preferences**: Only messages users who allow it
- **Cooldown**: Respects minimum time between contacts
- **Activity**: Prefers online users
- **Context**: Uses conversation history to make relevant messages
- **Frequency Limit**: Only messages 1 user per run to avoid spam

### Conversation Starters

AI-generated messages:
- Reference recent conversation topics
- Ask open-ended questions
- Feel natural and genuine
- Are 1-2 sentences max

## Voice TTS

The bot can join voice channels and communicate via text-to-speech.

### Features

- **Free TTS**: Uses edge-tts (no API keys required)
- **German Voice**: Male German voice (Killian Neural)
- **Voice Quality**: Natural-sounding speech
- **Conversation Logging**: All voice interactions are logged

### Voice Capabilities

The bot can:
1. **Join voice channels** where users are present
2. **Speak messages** using TTS
3. **Initiate voice calls** autonomously (if allowed by user)
4. **Announce focus timer completions** in voice

### Future: Transcription

Placeholder functions exist for:
- **Speech-to-text**: Transcribe user voice input
- **Speaker identification**: Identify who is speaking
- **Multi-speaker support**: Handle multiple people talking

These will be implemented with Whisper API or similar service.

## Configuration

### config.json Settings

```json
{
  "modules": {
    "autonomous_behavior": {
      "enabled": true,
      "messaging_interval_hours": 2,
      "max_users_per_run": 5,
      "min_cooldown_hours": 24,
      "allow_voice_calls": true,
      "voice_call_probability": 0.1
    },
    "focus_timer": {
      "enabled": true,
      "max_duration_minutes": 180,
      "reminder_on_distraction": true,
      "completion_notification_method": "dm_or_voice"
    },
    "voice_tts": {
      "enabled": true,
      "voice_id": "de-DE-KillianNeural",
      "rate": "+0%",
      "pitch": "+0Hz"
    }
  }
}
```

### Key Configuration Options

**Autonomous Behavior:**
- `messaging_interval_hours`: How often to check for users to message
- `max_users_per_run`: Maximum candidates to check per run
- `min_cooldown_hours`: Minimum hours between contacts
- `allow_voice_calls`: Enable/disable voice call feature
- `voice_call_probability`: Chance of voice call vs text message

**Focus Timer:**
- `max_duration_minutes`: Maximum allowed timer duration
- `reminder_on_distraction`: Send reminders when distractions detected
- `completion_notification_method`: How to notify on completion

**Voice TTS:**
- `voice_id`: Edge-TTS voice identifier
- `rate`: Speech rate adjustment
- `pitch`: Voice pitch adjustment

## Database Schema

### user_autonomous_settings
Stores user preferences for autonomous features.

```sql
CREATE TABLE user_autonomous_settings (
    user_id BIGINT PRIMARY KEY,
    allow_autonomous_messages BOOLEAN DEFAULT TRUE,
    allow_autonomous_calls BOOLEAN DEFAULT TRUE,
    last_autonomous_contact TIMESTAMP NULL,
    autonomous_contact_frequency VARCHAR(20) DEFAULT 'normal'
);
```

### focus_sessions
Tracks focus timer sessions.

```sql
CREATE TABLE focus_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    session_type VARCHAR(20) NOT NULL,
    duration_minutes INT NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NULL,
    completed BOOLEAN DEFAULT FALSE,
    distractions_count INT DEFAULT 0
);
```

### focus_distractions
Logs distractions during focus sessions.

```sql
CREATE TABLE focus_distractions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id INT NOT NULL,
    user_id BIGINT NOT NULL,
    distraction_type VARCHAR(50) NOT NULL,
    distraction_details TEXT NULL,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES focus_sessions(id)
);
```

### bot_autonomous_actions
Logs all autonomous actions by the bot.

```sql
CREATE TABLE bot_autonomous_actions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    action_type VARCHAR(50) NOT NULL,
    target_user_id BIGINT NOT NULL,
    guild_id BIGINT NULL,
    action_reason TEXT NULL,
    context_data JSON NULL,
    success BOOLEAN DEFAULT TRUE,
    user_response BOOLEAN NULL
);
```

### voice_conversations
Tracks voice conversation sessions.

```sql
CREATE TABLE voice_conversations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    session_start TIMESTAMP NOT NULL,
    session_end TIMESTAMP NULL,
    initiated_by VARCHAR(20) NOT NULL,
    participant_count INT DEFAULT 0
);
```

### voice_messages
Stores transcripts of voice messages.

```sql
CREATE TABLE voice_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    conversation_id INT NOT NULL,
    user_id BIGINT NOT NULL,
    speaker_name VARCHAR(255) NOT NULL,
    transcript TEXT NOT NULL,
    confidence FLOAT NULL,
    FOREIGN KEY (conversation_id) REFERENCES voice_conversations(id)
);
```

### user_memory_enhanced
Enhanced user memory for better autonomous decisions.

```sql
CREATE TABLE user_memory_enhanced (
    user_id BIGINT PRIMARY KEY,
    interests JSON NULL,
    usual_active_times JSON NULL,
    response_patterns JSON NULL,
    conversation_topics JSON NULL,
    last_significant_interaction TIMESTAMP NULL,
    interaction_frequency FLOAT DEFAULT 0.0,
    preferred_contact_method VARCHAR(20) DEFAULT 'text'
);
```

## Dependencies

### Required
- `edge-tts`: Free text-to-speech (no API key needed)
- `ffmpeg`: Audio playback (system dependency)

### Installation

```bash
pip install edge-tts
```

For FFmpeg:
- **Linux**: `apt-get install ffmpeg`
- **Windows**: Download from https://ffmpeg.org/
- **macOS**: `brew install ffmpeg`

## Best Practices

### For Server Owners
1. Inform users about autonomous features
2. Encourage users to set their preferences with `/settings`
3. Monitor bot behavior via logs
4. Adjust frequency settings if needed

### For Users
1. Use `/settings` to control bot contact
2. Try focus timers for productivity
3. Check `/focusstats` to track progress
4. Report any issues or unwanted behavior

## Troubleshooting

### Bot Not Sending Autonomous Messages
- Check if `autonomous_behavior.enabled` is true in config
- Verify users have autonomous messages enabled in `/settings`
- Check cooldown hasn't been reached
- Review logs for errors

### Focus Timer Not Working
- Ensure focus_timer is enabled in config
- Check database connection
- Verify migrations were applied
- Check bot permissions for DMs

### Voice TTS Not Working
- Install edge-tts: `pip install edge-tts`
- Install ffmpeg on system
- Check voice channel permissions
- Verify bot can connect to voice

### Activity Detection Issues
- Ensure presence intent is enabled
- Check on_presence_update handler is running
- Verify activity types are being detected
- Check logs for errors

## Future Improvements

Planned features:
- ✅ Autonomous messaging (implemented)
- ✅ Focus timer (implemented)
- ✅ Voice TTS (implemented)
- ⏳ Voice transcription (Whisper API)
- ⏳ Speaker identification
- ⏳ Multi-language support
- ⏳ More sophisticated decision algorithms
- ⏳ Machine learning for better timing
- ⏳ Emotion detection in voice
- ⏳ Context-aware voice responses

## Support

For issues, questions, or feature requests:
1. Check this documentation
2. Review bot logs
3. Check database for errors
4. Contact bot administrators
5. Open an issue on GitHub

## Credits

Developed as part of Sulfur Bot enhancements.
- TTS: edge-tts library
- Voice: discord.py voice support
- AI: Gemini/OpenAI APIs
