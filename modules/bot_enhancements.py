"""
Bot Enhancement Module
Integrates new features without modifying core bot.py heavily
Call these functions from appropriate places in bot.py
"""

import discord
from modules.db_helpers import (
    save_conversation_context,
    get_conversation_context,
    track_ai_model_usage,
    clear_old_conversation_contexts
)
from modules.api_helpers import get_vision_analysis
from modules.emoji_manager import analyze_server_emojis, get_emoji_context_for_ai
import base64
import aiohttp


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


async def enhance_prompt_with_context(user_id, channel_id, user_prompt):
    """
    Enhances user prompt with recent conversation context if within 2 minutes.
    Call this before sending prompt to AI.
    """
    context = await get_conversation_context(user_id, channel_id)
    
    if context and context['seconds_ago'] <= 120:
        # Add context to prompt
        enhanced_prompt = f"""[Previous conversation context from {context['seconds_ago']} seconds ago:
User: {context['last_user_message']}
Assistant: {context['last_bot_response']}]

Current message: {user_prompt}"""
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
    Analyzes server emojis and caches descriptions.
    Call this in on_ready event.
    Set force_reanalyze=True to re-analyze all emojis (expensive!)
    """
    print("[Bot Enhancement] Initializing emoji system...")
    
    if not config.get('features', {}).get('emoji_analysis_on_startup', False) and not force_reanalyze:
        print("[Bot Enhancement] Emoji analysis disabled in config. Skipping...")
        return None
    
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
