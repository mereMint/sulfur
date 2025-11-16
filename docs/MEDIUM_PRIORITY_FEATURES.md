# Feature Implementation Guide - Medium Priority Features

## Overview
This document describes the newly implemented medium priority features and how to integrate them into the bot.

## Implemented Features

### 1. ✅ Wrapped Opt-In System
**Files Modified:**
- `modules/db_helpers.py` - Added wrapped registration functions
- `scripts/db_migrations/002_medium_priority_features.sql` - Database schema

**Database Functions Added:**
- `register_for_wrapped(user_id, username)` - Registers a user for Wrapped
- `unregister_from_wrapped(user_id)` - Opts user out of Wrapped
- `is_registered_for_wrapped(user_id)` - Checks registration status
- `get_wrapped_registrations()` - Gets all registered users

**Integration Required:**
Add these commands to `bot.py`:

```python
# In bot.py, add these imports
from modules.db_helpers import register_for_wrapped, unregister_from_wrapped, is_registered_for_wrapped

# Add command handlers (example using message commands)
async def handle_wrapped_register(message):
    success = await register_for_wrapped(message.author.id, message.author.display_name)
    if success:
        await message.reply("✅ You've been registered for Wrapped summaries!")
    else:
        await message.reply("❌ Failed to register. Please try again.")

async def handle_wrapped_unregister(message):
    success = await unregister_from_wrapped(message.author.id)
    if success:
        await message.reply("✅ You've been removed from Wrapped summaries.")
    else:
        await message.reply("❌ Failed to unregister. Please try again.")
```

### 2. ✅ AI Vision Support
**Files Modified:**
- `modules/api_helpers.py` - Added vision analysis functions

**New Functions:**
- `get_vision_analysis(image_url, prompt, config, gemini_key, openai_key)` - Analyzes images
- `get_emoji_description(emoji_name, emoji_url, config, gemini_key, openai_key)` - Analyzes emojis

**Integration Required:**
In `bot.py`, in the `on_message` handler, detect image attachments:

```python
# In on_message function, after checking if message should be processed
if message.attachments:
    for attachment in message.attachments:
        if attachment.content_type and attachment.content_type.startswith('image/'):
            # User sent an image
            image_url = attachment.url
            
            # Analyze the image
            from modules.api_helpers import get_vision_analysis
            analysis, error = await get_vision_analysis(
                image_url, 
                "Describe this image in detail.",
                config,
                GEMINI_API_KEY,
                OPENAI_API_KEY
            )
            
            if analysis:
                # Add image description to the prompt context
                user_prompt = f"[Image attached: {analysis}] {message.content}"
            else:
                user_prompt = f"[Image attached but analysis failed: {error}] {message.content}"
```

### 3. ✅ Emoji Management System
**Files Created:**
- `modules/emoji_manager.py` - Complete emoji management system

**New Functions:**
- `analyze_server_emojis(guild, config, gemini_key, openai_key)` - Analyzes all emojis (run on startup)
- `get_emoji_context_for_ai()` - Gets emoji descriptions for AI prompts
- `get_emoji_by_name(emoji_name)` - Retrieves specific emoji

**Integration Required:**
In `bot.py`, add to the `on_ready` event:

```python
@bot.event
async def on_ready():
    # ... existing code ...
    
    # Analyze emojis on startup (only once or periodically)
    from modules.emoji_manager import analyze_server_emojis, get_emoji_context_for_ai
    
    for guild in bot.guilds:
        logger.info(f"Analyzing emojis for guild: {guild.name}")
        await analyze_server_emojis(guild, config, GEMINI_API_KEY, OPENAI_API_KEY)
    
    # Get emoji context for AI
    emoji_context = await get_emoji_context_for_ai()
    
    # Add to system prompt
    if emoji_context:
        config['bot']['system_prompt'] += "\n\n" + emoji_context
```

### 4. ✅ Multi-Model Support
**Files Modified:**
- `modules/api_helpers.py` - Added model selection

**New Function:**
- `get_ai_response_with_model(prompt, model_name, config, gemini_key, openai_key, system_prompt)` - Use specific models

**Supported Models:**
- Gemini: `gemini-2.0-flash-exp`, `gemini-1.5-pro`, `gemini-2.5-flash`
- OpenAI: `gpt-4o`, `gpt-4-turbo`, `gpt-4`, `gpt-3.5-turbo`
- Claude: Planned (not yet implemented)

**Integration Example:**
```python
# Use a specific model
from modules.api_helpers import get_ai_response_with_model

response, error = await get_ai_response_with_model(
    "Explain quantum computing",
    "gpt-4o",  # or "gemini-2.0-flash-exp"
    config,
    GEMINI_API_KEY,
    OPENAI_API_KEY,
    system_prompt="You are a physics expert."
)
```

### 5. ✅ Conversation Follow-Up System
**Files Modified:**
- `modules/db_helpers.py` - Added conversation context functions
- `scripts/db_migrations/002_medium_priority_features.sql` - Database schema

**New Functions:**
- `save_conversation_context(user_id, channel_id, last_user_message, last_bot_response)` - Saves context
- `get_conversation_context(user_id, channel_id)` - Gets recent context (within 2 minutes)
- `clear_old_conversation_contexts()` - Cleanup task

**Integration Required:**
In `bot.py`, modify the AI chat response handler:

```python
from modules.db_helpers import save_conversation_context, get_conversation_context

# Before getting AI response
context = await get_conversation_context(message.author.id, message.channel.id)

if context:
    # Add previous context to the prompt
    user_prompt = f"""Previous context (from {context['seconds_ago']} seconds ago):
User: {context['last_user_message']}
Bot: {context['last_bot_response']}

Current message: {message.content}"""
else:
    user_prompt = message.content

# After getting AI response
await save_conversation_context(
    message.author.id,
    message.channel.id,
    message.content,
    ai_response
)
```

Add a cleanup task:

```python
@tasks.loop(minutes=10)
async def cleanup_old_contexts():
    """Cleans up old conversation contexts."""
    from modules.db_helpers import clear_old_conversation_contexts
    await clear_old_conversation_contexts()

# In on_ready:
cleanup_old_contexts.start()
```

### 6. ✅ AI Model Usage Tracking
**Files Modified:**
- `modules/db_helpers.py` - Added tracking functions

**New Functions:**
- `track_ai_model_usage(model_name, feature, input_tokens, output_tokens, cost)` - Track usage
- `get_ai_usage_stats(days)` - Get statistics

**Integration Required:**
After each AI API call, track usage:

```python
from modules.db_helpers import track_ai_model_usage

# After getting AI response
await track_ai_model_usage(
    model_name="gemini-2.0-flash-exp",
    feature="chat",
    input_tokens=prompt_tokens,
    output_tokens=completion_tokens,
    cost=calculated_cost
)
```

## Database Migration

Run the migration script to create the new tables:

```bash
# Connect to MySQL
mysql -u sulfur_bot_user -p sulfur_bot

# Run the migration
source scripts/db_migrations/002_medium_priority_features.sql;
```

Or using Python:

```python
python scripts/run_migration.py scripts/db_migrations/002_medium_priority_features.sql
```

## Testing Checklist

- [ ] Test Wrapped registration/unregistration
- [ ] Test image analysis with vision AI
- [ ] Test emoji analysis on bot startup
- [ ] Test conversation follow-up (within 2 minutes)
- [ ] Test multi-model selection
- [ ] Verify AI usage tracking in database
- [ ] Check web dashboard displays AI usage stats

## Configuration Updates

Add to `config/config.json`:

```json
{
  "api": {
    "provider": "gemini",
    "vision_model": "gemini-2.0-flash-exp",
    "gemini": {
      "model": "gemini-2.0-flash-exp",
      "vision_model": "gemini-2.0-flash-exp"
    },
    "openai": {
      "model": "gpt-4o",
      "vision_model": "gpt-4o"
    }
  },
  "features": {
    "vision_enabled": true,
    "emoji_analysis_on_startup": true,
    "conversation_followup": true,
    "track_ai_usage": true
  }
}
```

## Next Steps

1. Run database migration
2. Integrate features into bot.py following examples above
3. Test each feature individually
4. Monitor logs for any errors
5. Update web dashboard to show AI usage stats

## Notes

- Emoji analysis can be expensive (vision AI calls for each emoji)
- Consider running emoji analysis manually or on a schedule, not every startup
- Conversation context is automatically cleaned up after 5 minutes
- Vision analysis requires appropriate API keys and model access
