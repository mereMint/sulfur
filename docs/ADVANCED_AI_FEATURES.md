# Advanced AI & Voice Call Features - Implementation Guide

This document describes the advanced AI intelligence and voice call features that have been added to make Sulfur more like Neuro-sama.

## 🧠 Advanced AI Intelligence

### Context Management
The bot now uses intelligent context management with:
- **Sliding Window Context**: Maintains recent conversation history
- **Smart Compression**: Automatically compresses old messages into summaries when token budget is exceeded
- **Token Budget Tracking**: Monitors and optimizes token usage to reduce API costs

### Emotional Intelligence
- Analyzes sentiment of user messages
- Detects emotional context (happy, sad, angry, anxious, confused)
- Adjusts responses based on emotional flow of conversation

### Response Optimization
- **Response Caching**: Caches similar queries to save API calls
- **Chain-of-Thought Reasoning**: Uses advanced reasoning for complex queries
- **Context-Aware Responses**: Combines text, vision, and conversation history

### How It Works
```python
from modules.advanced_ai import get_advanced_ai_response

# Get an AI response with all advanced features
response, error, metadata = await get_advanced_ai_response(
    prompt="Your question here",
    user_id=user.id,
    channel_id=channel.id,
    username=user.display_name,
    config=config,
    gemini_key=GEMINI_API_KEY,
    openai_key=OPENAI_API_KEY,
    system_prompt=SYSTEM_PROMPT,
    use_cache=True
)

# metadata contains:
# - cached: Whether response came from cache
# - compressed: Whether context was compressed
# - reasoning_used: Whether chain-of-thought was used
# - tokens_saved: Estimated tokens saved
```

## 🎙️ Voice Call Capabilities

### Features
- **Voice Call Initiation**: Bot can initiate voice calls with users
- **Real-time Transcription**: Converts speech to text using Whisper API or Google Speech Recognition
- **Voice Conversations**: Full voice-to-text-to-AI-to-TTS pipeline
- **Call Management**: Automatic timeout handling and statistics tracking

### Voice Call Flow
1. Bot joins user's voice channel
2. User speaks → Audio is recorded
3. Audio → Transcribed to text (Whisper API)
4. Text → Processed by AI
5. AI response → Converted to speech (TTS)
6. Speech → Played in voice channel

### Usage
```python
from modules.voice_conversation import initiate_voice_call, speak_in_call

# Initiate a voice call
call_state = await initiate_voice_call(user, config)

if call_state:
    # Speak in the call
    await speak_in_call(call_state, "Hello! I'm in your voice channel!")
    
    # Voice input is automatically transcribed and processed
```

### Configuration
Voice calls are configured in `config.json`:
```json
{
  "modules": {
    "autonomous_behavior": {
      "allow_voice_calls": true,
      "voice_call_probability": 0.1
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

## 🔧 Debug Commands

### `/debug_ai_reasoning <prompt>`
Shows the AI's thought process for a query:
- Input analysis
- Context compression status
- Reasoning method used
- Token usage
- Response preview

### `/debug_tokens`
Displays detailed token usage statistics:
- Current context token count
- Token budget and usage percentage
- API usage by model (last 24h)
- Compression statistics

### `/debug_memory`
Shows the bot's memory state:
- Active context windows
- Response cache statistics
- Recent conversation activity
- Learning statistics
- Personality evolution events

### `/debug_voice`
Displays voice call information:
- Active voice calls
- Call duration and details
- All-time statistics
- Average and longest call duration

### `/clear_context [channel]`
Clears the conversation context for a channel:
- Removes all stored context
- Frees up memory
- Useful for starting fresh conversations

## 📊 Web Dashboard Pages

### AI Reasoning Debug (`/ai_reasoning`)
Real-time visualization of:
- Token budget and usage
- API usage statistics
- Recent reasoning processes
- Active context window
- Performance metrics
- Cache hit rates

### Voice Calls Dashboard (`/voice_calls`)
Monitor voice call activity:
- Active voice calls
- Call duration and participants
- All-time statistics
- Call history chart
- Success rates

## 🗄️ Database Tables

Run the migration to create required tables:
```bash
mysql -u sulfur_bot_user -p sulfur_bot < scripts/db_migrations/migrate_advanced_ai_voice.sql
```

### New Tables
- `voice_call_stats` - Voice call history and statistics
- `api_usage_log` - Enhanced AI API usage logging
- `conversation_context` - Conversation context storage
- `personality_evolution` - Personality trait evolution
- `interaction_learnings` - Bot learning from interactions
- `bot_autonomous_actions` - Autonomous behavior tracking
- `user_autonomous_settings` - User preferences for autonomous features

## 🚀 Getting Started

### 1. Install Dependencies
```bash
pip install edge-tts SpeechRecognition aiohttp
```

### 2. Run Database Migration
```bash
mysql -u sulfur_bot_user -p sulfur_bot < scripts/db_migrations/migrate_advanced_ai_voice.sql
```

### 3. Configure Bot
Edit `config/config.json` to enable voice features:
```json
{
  "modules": {
    "autonomous_behavior": {
      "allow_voice_calls": true
    },
    "voice_tts": {
      "enabled": true
    }
  }
}
```

### 4. Add OpenAI API Key (Optional)
For Whisper transcription, add to `.env`:
```
OPENAI_API_KEY=your_key_here
```

### 5. Restart Bot
```bash
./maintain_bot.sh
```

## 📈 Token Optimization

### Context Compression
- Automatically triggered when context reaches 80% of token budget
- Compresses oldest 30% of messages into summaries
- Keeps last 3 summaries for long-term context

### Response Caching
- Caches responses for 24 hours
- Uses similarity matching (85% threshold)
- Saves tokens on similar queries
- Automatic cache cleanup

### Best Practices
1. Use `clear_context` command to reset heavy contexts
2. Monitor token usage with `/debug_tokens`
3. Review compression events in logs
4. Adjust `MAX_CONTEXT_TOKENS` if needed (default: 4000)

## 🔍 Monitoring & Analytics

### Check AI Performance
```bash
# View AI reasoning debug page
http://localhost:5000/ai_reasoning

# View voice call stats
http://localhost:5000/voice_calls
```

### Discord Commands
```
/debug_ai_reasoning prompt:Test query
/debug_tokens
/debug_memory
/debug_voice
```

## 🛠️ Troubleshooting

### Voice Calls Not Working
1. Check if TTS is available:
   ```bash
   pip install edge-tts
   ```
2. Verify voice channel permissions
3. Check logs for errors
4. Ensure `allow_voice_calls` is `true` in config

### High Token Usage
1. Use `/debug_tokens` to analyze usage
2. Clear old contexts with `/clear_context`
3. Review compression settings
4. Check for context leaks in logs

### Context Not Compressing
1. Verify token budget settings
2. Check compression threshold (80%)
3. Review logs for compression events
4. Ensure database connectivity

## 📝 Example Usage Scenarios

### Scenario 1: Complex Query with Reasoning
User asks a complex question → Bot uses chain-of-thought reasoning → Provides detailed answer

### Scenario 2: Voice Conversation
Bot calls user → User speaks → Bot transcribes → AI processes → Bot responds with voice

### Scenario 3: Token Optimization
Context grows large → Auto-compression triggers → Old messages summarized → Token budget maintained

## 🔐 Security Considerations

- Never expose API keys in logs
- Voice recordings are not permanently stored
- Context is channel-specific
- User can opt-out of autonomous features
- All database queries use parameterized statements

## 📚 Additional Resources

- [Main README](../README.md)
- [Configuration Guide](CONFIG_DOCUMENTATION.md)
- [Database Schema](../setup_database.sql)
- [Project Structure](PROJECT_STRUCTURE.md)

## 🤝 Contributing

To add new AI features:
1. Add logic to `modules/advanced_ai.py`
2. Create debug command in `bot.py`
3. Add web dashboard page in `web/`
4. Update this documentation

## 📄 License

Same as main project - see parent directory.
