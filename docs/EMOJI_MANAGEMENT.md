# Emoji Management Guide

## Overview

Sulfur bot uses **Application Emojis** - these are emojis uploaded directly to the bot's application that work everywhere (all servers and DMs), unlike server-specific emojis.

## Understanding the Problem

When emojis appear as text (e.g., `:shrug:` or `:6461shrug:`) instead of rendering as images, it means:
1. The AI is trying to use an emoji that doesn't exist in the bot's application emoji collection
2. The emoji name in `config/server_emojis.json` doesn't match any uploaded application emoji
3. The emoji hasn't been uploaded to the bot's application yet

## How Application Emojis Work

### What are Application Emojis?
- Emojis uploaded directly to the Discord bot application (not to individual servers)
- Work everywhere: all servers where the bot is present AND in DMs
- Limited to 50 emojis per bot
- Managed through the Discord Developer Portal

### Format
- **Short format**: `:emoji_name:` (used by AI)
- **Full format**: `<:emoji_name:emoji_id>` (Discord's internal format)
- **Animated**: `<a:emoji_name:emoji_id>`

## Setting Up Emojis

### Step 1: Upload Emojis to Bot Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Select your bot application
3. Click on "Emojis" in the left sidebar
4. Click "Upload Emoji"
5. Choose an emoji file (PNG, JPG, or GIF for animated)
6. Give it a name (this is what the AI will use)
7. Click "Save"

**Important**: The emoji name must match what's in your `config/server_emojis.json` file!

### Step 2: Configure Emojis

Edit `config/server_emojis.json` to tell the AI about the emojis:

```json
{
  "emojis": {
    "dono": {
      "description": "a donowall emote",
      "usage": "when blocking or rejecting something"
    },
    "YESS": {
      "description": "a guy that does a thumbs up",
      "usage": "to approve or agree with something"
    }
  }
}
```

**Note**: Only configure emojis that actually exist in your application emoji collection!

### Step 3: Verify Setup

Use the diagnostic tools to check your setup:

#### Option 1: Admin Command (In Discord)
```
/admin emojis
```
This shows:
- ✅ Configured emojis that exist
- ⚠️ Configured emojis that are missing
- 📦 Unconfigured application emojis

#### Option 2: Test Script (Command Line)
```bash
python3 test_application_emojis.py
```
This provides detailed information about:
- All application emojis with their IDs
- Short and full format examples
- Missing configured emojis
- Comprehensive status report

## Troubleshooting

### Issue: Emojis showing as text (`:emoji_name:`)

**Diagnosis**: The emoji doesn't exist in the application emoji collection.

**Solutions**:
1. Upload the emoji to the bot's application (see Step 1 above)
2. Remove it from `config/server_emojis.json` if you don't want to use it
3. Run `/admin emojis` to verify which emojis are missing

### Issue: Bot can use emoji in one server but not another

**Diagnosis**: The emoji is a server-specific emoji, not an application emoji.

**Solution**: 
1. Download the emoji from the server where it works
2. Upload it as an application emoji (see Step 1 above)
3. The bot will then be able to use it everywhere

### Issue: AI using wrong emoji names

**Diagnosis**: The AI is being told about emojis that don't actually exist.

**Solution**: 
1. Run `/admin emojis` to see which configured emojis are missing
2. Either upload those emojis OR remove them from `config/server_emojis.json`
3. Restart the bot to reload the emoji context

### Issue: Hit the 50 emoji limit

**Solutions**:
1. Remove unused emojis from the application
2. Prioritize the most important emojis
3. Consider which emojis the AI uses most frequently
4. Remove duplicates or very similar emojis

## How the Emoji System Works

### At Bot Startup
1. Bot fetches all application emojis from Discord
2. Loads configured emojis from `config/server_emojis.json`
3. **Verifies** configured emojis actually exist in application collection
4. Tells AI only about emojis that actually exist
5. AI can now use these emojis in responses

### When AI Generates a Response
1. AI uses short format (`:emoji_name:`)
2. Bot's `replace_emoji_tags()` function converts to full format
3. Searches in this order:
   - Application emojis (highest priority - work everywhere)
   - Current server emojis (if in a server context)
4. If emoji found: Converts to `<:emoji_name:emoji_id>`
5. If not found: Stays as `:emoji_name:` (shows as text)

### Auto-Download System
When the bot sees a NEW emoji in a message:
1. Analyzes the emoji with AI vision
2. Stores description in database
3. Attempts to download and add to application emojis
4. If successful, emoji becomes available for AI to use

**Limitations**:
- Only works if bot is in the server where emoji originates
- Limited to 50 application emojis total
- Subject to Discord rate limits

## Best Practices

### Emoji Names
- Use clear, descriptive names
- Avoid numbers at the start if possible (`:shrug:` not `:6461shrug:`)
- Keep names short and memorable
- Use lowercase for consistency

### Configuration
- Only configure emojis you've actually uploaded
- Keep descriptions accurate and helpful
- Update usage context to guide AI behavior
- Remove unused emoji configs

### Maintenance
- Periodically run `/admin emojis` to check status
- Remove old or unused application emojis
- Keep `config/server_emojis.json` in sync with actual emojis
- Monitor bot startup logs for emoji-related warnings

## Commands Reference

### Admin Commands
- `/admin emojis` - View all application emojis and their status
- `/admin reload_config` - Reload emoji configuration from file

### Test Scripts
- `python3 test_application_emojis.py` - Detailed emoji diagnostic tool

## Example Workflow

### Adding a New Emoji

1. **Find or create the emoji image**
   - Must be PNG, JPG, or GIF (for animated)
   - Max 256KB file size
   - Recommended: 128x128 pixels

2. **Upload to Discord**
   ```
   Discord Developer Portal → Your Bot → Emojis → Upload Emoji
   Name: "poggers"
   File: poggers.png
   ```

3. **Add to configuration**
   ```json
   {
     "emojis": {
       "poggers": {
         "description": "excited and happy face",
         "usage": "when something amazing happens"
       }
     }
   }
   ```

4. **Restart bot**
   ```bash
   # The bot will detect and load the new emoji configuration
   ```

5. **Verify**
   ```
   /admin emojis
   # Should show "poggers" in the ✅ Configured Emojis section
   ```

6. **Test**
   - Have a conversation with the bot
   - The AI should now be able to use `:poggers:` naturally
   - It will render as an actual emoji image, not text

## Technical Details

### Files Involved
- `modules/emoji_manager.py` - Core emoji management logic
- `modules/bot_enhancements.py` - Emoji system initialization
- `bot.py` - Emoji tag replacement and auto-download
- `config/server_emojis.json` - Emoji configuration
- `emoji_descriptions` (database table) - AI-analyzed emoji cache

### Database Schema
```sql
CREATE TABLE emoji_descriptions (
    emoji_id BIGINT PRIMARY KEY,
    emoji_name VARCHAR(255) NOT NULL,
    description TEXT,
    usage_context TEXT,
    image_url TEXT,
    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Key Functions
- `get_emoji_context_for_ai(client)` - Builds emoji list for AI
- `replace_emoji_tags(text, client, guild)` - Converts `:name:` to `<:name:id>`
- `auto_download_emoji(emoji_name, guild, client)` - Downloads new emojis
- `analyze_application_emojis(client, config, gemini_key, openai_key)` - AI analysis

## FAQ

**Q: Why not use server emojis instead?**
A: Server emojis only work in that specific server. Application emojis work everywhere, including DMs.

**Q: Can I have more than 50 emojis?**
A: No, Discord limits bots to 50 application emojis. Choose wisely!

**Q: Do I need to restart the bot after uploading a new emoji?**
A: Yes, the bot caches emoji information at startup. Restart or use `/admin reload_config`.

**Q: Why are some emojis in my config missing?**
A: They haven't been uploaded to the bot's application yet. Use `/admin emojis` to see which ones.

**Q: Can I use emojis from other servers?**
A: The bot can auto-download them IF it's in that server. They'll be added to application emojis.

## Support

If you're still having issues:
1. Run `test_application_emojis.py` for detailed diagnostics
2. Check bot startup logs for emoji-related errors
3. Verify emoji names match exactly between config and uploaded emojis
4. Ensure you haven't hit the 50 emoji limit
5. Check Discord Developer Portal to see your application emojis
