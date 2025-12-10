# Emoji System Flow Documentation

## Overview
This document explains how the emoji system works end-to-end, ensuring emojis render correctly in Discord.

## The Problem We Solved
**Issue**: AI was generating invalid emoji formats like `:1352what:` instead of `:what:`, causing emojis not to render.

**Root Cause**: Chat history contained full Discord emoji format `<:name:id>`, and the AI learned to combine IDs with names incorrectly.

**Solution**: Convert all emojis to shortcode format `:name:` before sending to AI, then convert back to full format `<:name:id>` before sending to Discord.

## Complete Emoji Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    USER SENDS MESSAGE WITH EMOJI                    │
│                  "Hey <:what:1352> how are you?"                    │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     STORED IN DATABASE (chat_history)               │
│                  Content: "Hey <:what:1352> how are you?"           │
│                  (Full format preserved)                            │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│              RETRIEVED FOR AI CONTEXT (get_chat_history)            │
│              EMOJI CONVERSION APPLIED: <:name:id> → :name:          │
│                  Output: "Hey :what: how are you?"                  │
│                  (Shortcode format for AI)                          │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     AI RECEIVES SHORTCODE FORMAT                    │
│                     Learns to use: :what: :stare:                   │
│                  Never sees IDs, can't combine incorrectly          │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   AI GENERATES RESPONSE WITH SHORTCODE              │
│         "I'm good :what: how about you?"                            │
│         (AI only knows shortcode format)                            │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│              BOT CONVERTS TO FULL FORMAT (replace_emoji_tags)       │
│              EMOJI CONVERSION APPLIED: :name: → <:name:id>          │
│         Output: "I'm good <:what:1352> how about you?"              │
│         (Full format required by Discord)                           │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     SENT TO DISCORD AND RENDERED                    │
│         Discord sees: <:what:1352>                                  │
│         User sees: [emoji image] (properly rendered)                │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Functions

### 1. `_convert_emojis_to_shortcode()` (db_helpers.py)
**Purpose**: Converts full Discord emoji format to shortcode for AI training.

**Conversion**:
- `<:emoji_name:12345>` → `:emoji_name:`
- `<a:emoji_name:12345>` → `:emoji_name:` (animated)

**Used in**:
- `get_chat_history()` - converts history before AI sees it
- `get_conversation_context()` - converts context messages

**Example**:
```python
input = "Hey <:what:1352> there"
output = _convert_emojis_to_shortcode(input)
# output = "Hey :what: there"
```

### 2. `replace_emoji_tags()` (bot.py)
**Purpose**: Converts shortcode emoji format to full Discord format for rendering.

**Conversion**:
- `:emoji_name:` → `<:emoji_name:id>` (static)
- `:emoji_name:` → `<a:emoji_name:id>` (animated)

**Features**:
- Fetches application emojis from Discord
- Fetches guild emojis (if in server context)
- Prioritizes application emojis (work everywhere)
- Auto-downloads missing emojis (if configured)

**Used in**:
- Main chatbot response processing
- Wrapped summary generation
- Any AI-generated text before sending to Discord

**Example**:
```python
# AI generates: "I'm good :what: how about you?"
text = "I'm good :what: how about you?"
output = await replace_emoji_tags(text, client, guild)
# output = "I'm good <:what:1352> how about you?"
```

### 3. `sanitize_malformed_emojis()` (bot.py)
**Purpose**: Fixes malformed emoji patterns the AI might generate.

**Fixes**:
- `<<:name:id>id>` → `<:name:id>`
- `` `<:name:id>` `` → `<:name:id>` (removes backticks)
- `` `:name:` `` → `:name:` (removes backticks from shortcode)

**Called from**: `replace_emoji_tags()` before processing

### 4. `handle_unknown_emojis_in_message()` (bot_enhancements.py)
**Purpose**: Detects custom emojis in user messages and analyzes unknown ones.

**Features**:
- Detects `<:name:id>` and `<a:name:id>` patterns
- Checks database for existing emoji descriptions
- Analyzes new emojis with AI vision
- Auto-downloads to bot's application emojis
- Provides context to AI about emoji meanings

**Pattern**: `<a?:(\w+):(\d+)>`

## Emoji Types

### Application Emojis
- **Definition**: Emojis uploaded to the bot's application
- **Availability**: Work in ALL servers and DMs
- **Format**: `<:name:id>` or `<a:name:id>`
- **Managed by**: Bot application in Discord Developer Portal
- **Auto-download**: Bot can add new emojis to this collection

### Server/Guild Emojis
- **Definition**: Emojis specific to a Discord server
- **Availability**: Only work in that specific server
- **Format**: `<:name:id>` or `<a:name:id>`
- **Managed by**: Server administrators
- **Fallback**: Bot uses these if no application emoji exists

## Configuration

### Emoji System Initialization (on_ready event)
```python
emoji_context = await initialize_emoji_system(client, config, GEMINI_API_KEY, OPENAI_API_KEY)
if emoji_context:
    config['bot']['system_prompt'] += "\n\n" + emoji_context
```

### Emoji Context for AI
The AI receives information about available emojis in its system prompt:

```
**🎭 Your Emoji Arsenal:**
You have custom emojis to express yourself! Use them naturally in conversations.
**Format:** Just use :<emoji_name>: - NO backticks, NO quotes, NO other symbols!

**Available Emojis:**
- :what: - A confused expression | Best for: questioning or disbelief
- :stare: - An intense stare | Best for: awkward or intense moments
- :dono: - A donowall emote | Best for: blocking or rejecting something
...
```

## Testing

### Unit Tests
- `test_emoji_conversion.py` - Tests shortcode conversion
- `test_emoji_system_comprehensive.py` - Tests complete workflow
- `test_application_emoji_rendering.py` - Tests full format output

### Test Coverage
✓ Shortcode to full format conversion
✓ Full format to shortcode conversion
✓ Static emoji handling
✓ Animated emoji handling
✓ Multiple emojis in one message
✓ Malformed emoji sanitization
✓ Edge cases (no emojis, already converted, etc.)

## Discord Format Requirements

### Static Emoji
- **Format**: `<:emoji_name:emoji_id>`
- **Example**: `<:what:1352>`
- **Discord renders this as**: [emoji image]

### Animated Emoji
- **Format**: `<a:emoji_name:emoji_id>`
- **Example**: `<a:stare:6153>`
- **Discord renders this as**: [animated emoji image]

### Invalid Formats (won't render)
- `:emoji_name:` - Missing ID and brackets
- `:1352what:` - ID in wrong position
- `<:what:>` - Missing ID
- `<what:1352>` - Missing colon after <

## Error Handling

### Missing Emoji
If AI uses an emoji that doesn't exist:
1. `replace_emoji_tags()` looks up the emoji in application/guild emojis
2. If not found, attempts auto-download (if enabled and in guild context)
3. If still not found, logs debug message and leaves as shortcode
4. User sees `:emoji_name:` as text (not ideal, but safe)

### Database Connection Issues
- Functions return empty strings/lists if DB unavailable
- Graceful degradation - bot continues without history context

### API Rate Limits
- Emoji downloads are rate-limited (5 per 60 seconds)
- Prevents hitting Discord API limits

## Performance Considerations

### Caching
- Application emojis are fetched once per `replace_emoji_tags()` call
- Guild emojis are accessed from guild object (already cached by discord.py)
- Emoji descriptions stored in database for reuse

### Regex Efficiency
- Patterns are compiled once (module level)
- Use of negative lookbehind prevents double-processing
- Set() used to avoid processing duplicate emojis

## Troubleshooting

### Emojis not rendering
**Check**: Is the output in full format `<:name:id>`?
- Run validation: `validate_full_format_output(text)`
- Verify `replace_emoji_tags()` is being called

### AI using wrong emoji format
**Check**: Is chat history being sanitized?
- Verify `_convert_emojis_to_shortcode()` is working
- Check database retrieval functions

### Emoji shows as text
**Possible causes**:
1. Emoji doesn't exist in application/guild emojis
2. Emoji ID is incorrect
3. Format is invalid (missing brackets, colons, or ID)

### Auto-download not working
**Check**:
1. Bot has permission to create application emojis
2. Rate limit not exceeded (5 per minute)
3. Emoji name is valid (2-32 chars, alphanumeric + underscores)

## Future Improvements

### Potential Enhancements
- [ ] Emoji usage statistics
- [ ] Emoji recommendation based on context
- [ ] Multi-guild emoji preference learning
- [ ] Emoji synonym support (multiple names for same emoji)
- [ ] Batch emoji analysis on startup

## References

### Discord Documentation
- [Emoji Documentation](https://discord.com/developers/docs/resources/emoji)
- [Message Formatting](https://discord.com/developers/docs/reference#message-formatting)

### Code Locations
- `bot.py`: Lines 434-621 (sanitization, replacement)
- `modules/db_helpers.py`: Lines 1-9, 1459-1520 (conversion, history)
- `modules/bot_enhancements.py`: Lines 100-207 (detection, analysis)
- `modules/emoji_manager.py`: Lines 1-350 (management, AI context)
