"""
Bot Enhancement Module
Integrates new features without modifying core bot.py heavily
Call these functions from appropriate places in bot.py
"""

import discord
import re
from modules.db_helpers import (
    save_conversation_context,
    get_conversation_context,
    track_ai_model_usage,
    clear_old_conversation_contexts,
    get_emoji_description,
    save_emoji_description
)
from modules.api_helpers import get_vision_analysis
from modules.emoji_manager import analyze_server_emojis, get_emoji_context_for_ai
import base64
import aiohttp

# --- NEW: Import structured logging ---
from modules.logger_utils import bot_logger as logger


async def handle_unknown_emojis_in_message(message, config, gemini_key, openai_key, client=None):
    """
    Detects custom emojis in a message and analyzes any unknown ones.
    Automatically adds new emojis to the bot's application emojis.
    Returns context about the emojis for the AI.
    
    Args:
        message: Discord message object
        config: Bot configuration
        gemini_key: Gemini API key
        openai_key: OpenAI API key
        client: Discord client (optional, for auto-downloading emojis)
    """
    # Pattern to match Discord custom emojis: <:emoji_name:emoji_id> or <a:emoji_name:emoji_id>
    emoji_pattern = r'<a?:(\w+):(\d+)>'
    matches = re.findall(emoji_pattern, message.content)
    
    if not matches:
        return None
    
    emoji_contexts = []
    
    for emoji_name, emoji_id in matches:
        # Check if we already have this emoji analyzed
        existing = await get_emoji_description(emoji_id)
        
        if existing:
            # We know this emoji, add its description to context
            emoji_contexts.append(f"Emoji :{emoji_name}: - {existing['description']}")
        else:
            # Unknown emoji - analyze it
            print(f"[Emoji Analysis] Analyzing unknown emoji: {emoji_name} (ID: {emoji_id})")
            
            # Construct emoji URL (Discord CDN)
            # Try .gif first for animated emojis, fallback to .png
            emoji_url_gif = f"https://cdn.discordapp.com/emojis/{emoji_id}.gif"
            emoji_url_png = f"https://cdn.discordapp.com/emojis/{emoji_id}.png"
            
            try:
                # Download and convert to base64
                async with aiohttp.ClientSession() as session:
                    # Try GIF first (for animated emojis)
                    async with session.get(emoji_url_gif) as response:
                        if response.status == 200:
                            image_data = await response.read()
                            emoji_url = emoji_url_gif
                            is_animated = True
                        else:
                            # Fallback to PNG
                            async with session.get(emoji_url_png) as response_png:
                                if response_png.status == 200:
                                    image_data = await response_png.read()
                                    emoji_url = emoji_url_png
                                    is_animated = False
                                else:
                                    print(f"[Emoji Analysis] Failed to download emoji {emoji_name} from CDN")
                                    emoji_contexts.append(f"Emoji :{emoji_name}: (download failed)")
                                    continue
                    
                    base64_image = base64.b64encode(image_data).decode('utf-8')
                    data_url = f"data:image/{'gif' if is_animated else 'png'};base64,{base64_image}"
                    
                    # Analyze with vision AI
                    from modules.api_helpers import get_emoji_description as analyze_emoji
                    result, error = await analyze_emoji(emoji_name, data_url, config, gemini_key, openai_key)
                    
                    if error:
                        print(f"[Emoji Analysis] Error analyzing {emoji_name}: {error}")
                        emoji_contexts.append(f"Emoji :{emoji_name}: (analysis failed)")
                    elif result:
                        # Save to database
                        description = result.get('description', 'Custom emoji')
                        usage_context = result.get('usage_context', 'General use')
                        
                        await save_emoji_description(
                            emoji_id=emoji_id,
                            emoji_name=emoji_name,
                            description=description,
                            usage_context=usage_context,
                            image_url=emoji_url
                        )
                        
                        emoji_contexts.append(f"Emoji :{emoji_name}: - {description}")
                        print(f"[Emoji Analysis] Saved description for {emoji_name}")
                        
                        # Auto-download emoji to bot's application emojis
                        if client:
                            try:
                                # Check if we already have this emoji as an application emoji
                                app_emojis = await client.fetch_application_emojis()
                                already_exists = any(e.name == emoji_name for e in app_emojis)
                                
                                if not already_exists:
                                    # Add to bot's application emojis
                                    new_emoji = await client.create_application_emoji(
                                        name=emoji_name,
                                        image=image_data
                                    )
                                    logger.info(f"Auto-added emoji '{emoji_name}' to bot's application emojis")
                                    print(f"[Emoji] ✓ Auto-added '{emoji_name}' to bot's emoji collection")
                                else:
                                    logger.debug(f"Emoji '{emoji_name}' already exists in application emojis")
                            except Exception as e:
                                logger.warning(f"Failed to auto-add emoji '{emoji_name}': {e}")
                                print(f"[Emoji] ✗ Could not auto-add '{emoji_name}': {e}")
            except Exception as e:
                print(f"[Emoji Analysis] Exception analyzing {emoji_name}: {e}")
                emoji_contexts.append(f"Emoji :{emoji_name}: (error)")
    
    if emoji_contexts:
        return "[Emoji Context: " + "; ".join(emoji_contexts) + "]"
    
    return None


async def handle_image_attachment(message, config, gemini_key, openai_key):
    """
    Processes image attachments and returns analysis for AI context.
    Call this in on_message before sending to chatbot.
    """
    if not message.attachments:
        return None
    
    for attachment in message.attachments:
        if attachment.content_type and attachment.content_type.startswith('image/'):
            try:
                # Download image
                async with aiohttp.ClientSession() as session:
                    async with session.get(attachment.url) as response:
                        if response.status == 200:
                            image_data = await response.read()
                            base64_image = base64.b64encode(image_data).decode('utf-8')
                            data_url = f"data:{attachment.content_type};base64,{base64_image}"
                            
                            # Analyze image
                            analysis, error = await get_vision_analysis(
                                data_url,
                                "Describe this image in detail for conversation context.",
                                config,
                                gemini_key,
                                openai_key
                            )
                            
                            if analysis:
                                return f"[Image Description: {analysis}]"
                            else:
                                return f"[Image attached but analysis failed: {error}]"
            except Exception as e:
                print(f"Error analyzing image: {e}")
                return "[Image attached but could not be analyzed]"
    
    return None


async def is_contextual_conversation(channel_id: int, user_id: int, message_content: str, bot_names: list, max_age_seconds: int = 120) -> tuple[bool, dict]:
    """
    Determines if a message is likely part of an ongoing conversation with the bot.
    Optimized for speed - only checks user context, not channel-wide context.
    
    Args:
        channel_id: The Discord channel ID
        user_id: The message author's Discord user ID
        message_content: The content of the message
        bot_names: List of bot names to check for partial matches
        max_age_seconds: Maximum age of context to consider (default 2 minutes)
    
    Returns:
        Tuple of (is_trigger, context_dict)
    """
    # Quick exit for long messages (unlikely follow-ups)
    word_count = len(message_content.split())
    if word_count > 30:
        return False, {}
    
    # Check if user had recent conversation with bot
    user_context = await get_conversation_context(user_id, channel_id)
    
    if not user_context or user_context['seconds_ago'] > max_age_seconds:
        return False, {}
    
    seconds_ago = user_context['seconds_ago']
    msg_lower = message_content.lower().strip()
    
    # Very recent (< 60s): treat short messages as follow-ups
    if seconds_ago <= 60 and word_count <= 20:
        return True, {'type': 'recent', 'seconds_ago': seconds_ago}
    
    # Recent (60-120s): check for conversational patterns
    if seconds_ago <= 120:
        # Question or continuation indicators
        if '?' in msg_lower or any(w in msg_lower for w in ['warum', 'wieso', 'wie', 'was', 'und du', 'aber']):
            return True, {'type': 'question', 'seconds_ago': seconds_ago}
        
        # Short affirmative/negative responses
        if word_count <= 5:
            quick_responses = {'ja', 'nein', 'ok', 'okay', 'klar', 'stimmt', 'genau', 'nö', 'nice', 'lol', 'haha', 'danke', 'echt', 'krass'}
            first_word = msg_lower.split()[0].rstrip('!?.,') if msg_lower else ''
            if first_word in quick_responses:
                return True, {'type': 'response', 'seconds_ago': seconds_ago}
    
    return False, {}


async def get_enriched_user_context(user_id: int, display_name: str, db_helpers_module) -> str:
    """
    Builds a compact context string about the user for the AI.
    Optimized for minimal tokens while providing useful context.
    
    Args:
        user_id: The Discord user ID
        display_name: The user's display name
        db_helpers_module: The db_helpers module for database access
    
    Returns:
        A short context string or empty string
    """
    try:
        # Get player profile (single DB query)
        profile, error = await db_helpers_module.get_player_profile(user_id)
        if not profile or error:
            return ""
        
        parts = []
        
        # Basic stats (compact)
        level = profile.get('level', 1)
        if level > 1:
            parts.append(f"Lv{level}")
        
        # Last activity (useful for conversation)
        activity = profile.get('last_activity_name')
        if activity:
            parts.append(f"spielt: {activity[:20]}")
        
        if parts:
            return f" [{' | '.join(parts)}]"
    
    except Exception:
        pass  # Fail silently - context is optional
    
    return ""


async def enhance_prompt_with_context(user_id, channel_id, user_prompt):
    """
    Enhances user prompt with recent conversation context if within 2 minutes.
    Call this before sending prompt to AI.
    """
    context = await get_conversation_context(user_id, channel_id)
    
    if context and context['seconds_ago'] <= 120:
        # Add context to prompt in a way that doesn't confuse the AI
        # Just inform the AI about recent context without making it look like multiple messages
        enhanced_prompt = f"""[Context: You recently talked with this user {context['seconds_ago']} seconds ago about: "{context['last_user_message'][:100]}..." - Keep this in mind for continuity]

{user_prompt}"""
        return enhanced_prompt, True
    
    return user_prompt, False


async def save_ai_conversation(user_id, channel_id, user_message, bot_response):
    """
    Saves the conversation for future context.
    Call this after getting AI response.
    """
    await save_conversation_context(user_id, channel_id, user_message, bot_response)


async def track_api_call(model_name, feature, input_tokens=0, output_tokens=0):
    """
    Tracks AI API usage for analytics.
    Call this after each API call.
    
    Parameters:
    - model_name: e.g., "gemini-2.0-flash-exp", "gpt-4o"
    - feature: e.g., "chat", "werwolf_tts", "wrapped", "vision"
    - input_tokens: Number of input tokens used
    - output_tokens: Number of output tokens used
    """
    # Simple cost estimation (update these rates as needed)
    cost = 0.0
    
    if "gemini" in model_name.lower():
        # Gemini pricing (example: $0.001 per 1K tokens)
        cost = ((input_tokens + output_tokens) / 1000) * 0.001
    elif "gpt-4" in model_name.lower():
        # GPT-4 pricing (example: $0.03 per 1K input, $0.06 per 1K output)
        cost = (input_tokens / 1000) * 0.03 + (output_tokens / 1000) * 0.06
    elif "gpt-3.5" in model_name.lower():
        # GPT-3.5 pricing (example: $0.001 per 1K tokens)
        cost = ((input_tokens + output_tokens) / 1000) * 0.001
    
    await track_ai_model_usage(model_name, feature, input_tokens, output_tokens, cost)


async def initialize_emoji_system(client, config, gemini_key, openai_key, force_reanalyze=False):
    """
    Analyzes server emojis and application emojis, caching descriptions.
    Call this in on_ready event.
    Set force_reanalyze=True to re-analyze all emojis (expensive!)
    """
    print("[Bot Enhancement] Initializing emoji system...")
    
    if not config.get('features', {}).get('emoji_analysis_on_startup', False) and not force_reanalyze:
        print("[Bot Enhancement] Emoji analysis disabled in config. Skipping...")
        return None
    
    # Analyze application emojis first (bot's own emojis)
    try:
        from modules.emoji_manager import analyze_application_emojis
        await analyze_application_emojis(client, config, gemini_key, openai_key)
    except Exception as e:
        print(f"[Bot Enhancement] Failed to analyze application emojis: {e}")
    
    # Then analyze server emojis
    for guild in client.guilds:
        if force_reanalyze:
            print(f"[Bot Enhancement] Analyzing emojis for guild: {guild.name}")
            await analyze_server_emojis(guild, config, gemini_key, openai_key)
    
    # Get emoji context for AI
    emoji_context = await get_emoji_context_for_ai()
    print(f"[Bot Enhancement] Emoji system ready. {len(emoji_context)} characters of emoji data loaded.")
    
    return emoji_context


async def get_enhanced_system_prompt(base_prompt, include_emoji_context=False):
    """
    Enhances the system prompt with emoji context.
    Call this when building the system prompt.
    """
    if not include_emoji_context:
        return base_prompt
    
    emoji_context = await get_emoji_context_for_ai()
    
    if emoji_context:
        return base_prompt + "\n\n" + emoji_context
    
    return base_prompt


# Background task helper
async def cleanup_task(client):
    """
    Periodic cleanup task. Call this as a discord.ext.tasks loop.
    """
    await clear_old_conversation_contexts()
    print("[Bot Enhancement] Cleaned up old conversation contexts")


# Integration Example:
"""
In bot.py, add to on_ready:

from modules.bot_enhancements import initialize_emoji_system

@client.event
async def on_ready():
    # ... existing code ...
    
    # Initialize emoji system (optional, can be expensive)
    emoji_context = await initialize_emoji_system(client, config, GEMINI_API_KEY, OPENAI_API_KEY)
    if emoji_context:
        config['bot']['system_prompt'] += emoji_context


In bot.py, modify on_message / chatbot flow:

from modules.bot_enhancements import handle_image_attachment, enhance_prompt_with_context, save_ai_conversation, track_api_call

async def run_chatbot(message):
    # Check for images
    image_context = await handle_image_attachment(message, config, GEMINI_API_KEY, OPENAI_API_KEY)
    
    user_prompt = message.content
    if image_context:
        user_prompt = f"{image_context}\n{user_prompt}"
    
    # Enhance with conversation context
    user_prompt, has_context = await enhance_prompt_with_context(
        message.author.id,
        message.channel.id,
        user_prompt
    )
    
    # Get AI response (existing code)
    response_text, error, _ = await get_chat_response(...)
    
    # Save conversation
    await save_ai_conversation(message.author.id, message.channel.id, message.content, response_text)
    
    # Track usage
    await track_api_call("gemini-2.0-flash-exp", "chat", input_tokens=100, output_tokens=50)
    
    # Send response (existing code)
    await message.channel.send(response_text)


Add background cleanup task:

from discord.ext import tasks
from modules.bot_enhancements import cleanup_task

@tasks.loop(minutes=10)
async def periodic_cleanup():
    await cleanup_task(client)

@client.event
async def on_ready():
    # ... existing code ...
    periodic_cleanup.start()
"""
