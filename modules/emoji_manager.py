"""
Emoji Management Module for Sulfur Discord Bot
Handles emoji analysis, caching, and AI integration
"""

import discord
import asyncio
import base64
import aiohttp
import json
import os
from modules.db_helpers import (
    save_emoji_description, 
    get_all_emoji_descriptions,
    get_emoji_description
)
from modules.api_helpers import get_emoji_description as analyze_emoji


def load_server_emojis():
    """
    Loads pre-configured server emojis from config/server_emojis.json.
    Returns a dictionary of emoji definitions.
    """
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "server_emojis.json")
    
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            print(f"[Emoji System] Warning: {config_path} not found")
            return {"emojis": {}}
    except Exception as e:
        print(f"[Emoji System] Error loading server emojis: {e}")
        return {"emojis": {}}


async def analyze_application_emojis(client, config, gemini_key, openai_key):
    """
    Analyzes all application emojis (bot's own emojis) and caches descriptions.
    This should run on bot startup.
    """
    print(f"[Emoji System] Starting application emoji analysis...")
    
    try:
        # Fetch application emojis (these are emojis uploaded to the bot application)
        app_emojis = await client.fetch_application_emojis()
        total_emojis = len(app_emojis)
        
        if total_emojis == 0:
            print("[Emoji System] No application emojis found.")
            return
        
        print(f"[Emoji System] Found {total_emojis} application emojis to analyze...")
        
        analyzed_count = 0
        skipped_count = 0
        error_count = 0
        
        for emoji in app_emojis:
            # Check if this emoji is already in the database
            existing = await get_emoji_description(str(emoji.id))
            
            if existing:
                print(f"[Emoji System] Skipping {emoji.name} (already analyzed)")
                skipped_count += 1
                continue
            
            # Analyze the emoji
            print(f"[Emoji System] Analyzing application emoji: {emoji.name} ({analyzed_count + 1}/{total_emojis})")
            
            try:
                # Get the emoji URL
                emoji_url = str(emoji.url)
                
                # Download and convert to base64 if needed
                async with aiohttp.ClientSession() as session:
                    async with session.get(emoji_url) as response:
                        if response.status == 200:
                            image_data = await response.read()
                            # For Gemini, we need base64
                            base64_image = base64.b64encode(image_data).decode('utf-8')
                            data_url = f"data:image/png;base64,{base64_image}"
                        else:
                            print(f"[Emoji System] Failed to download emoji {emoji.name}")
                            error_count += 1
                            continue
                
                # Analyze with vision AI
                result, error = await analyze_emoji(emoji.name, data_url, config, gemini_key, openai_key)
                
                if error:
                    print(f"[Emoji System] Error analyzing {emoji.name}: {error}")
                    error_count += 1
                    continue
                
                # Save to database
                description = result.get('description', 'Custom emoji')
                usage_context = result.get('usage_context', 'General use')
                
                success = await save_emoji_description(
                    emoji_id=str(emoji.id),
                    emoji_name=emoji.name,
                    description=description,
                    usage_context=usage_context,
                    image_url=emoji_url
                )
                
                if success:
                    analyzed_count += 1
                    print(f"[Emoji System] ✓ Saved description for {emoji.name}")
                else:
                    error_count += 1
                    print(f"[Emoji System] ✗ Failed to save {emoji.name}")
                
                # Rate limiting - wait a bit between API calls
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"[Emoji System] Exception analyzing {emoji.name}: {e}")
                error_count += 1
        
        print(f"\n[Emoji System] Application emoji analysis complete!")
        print(f"  - Analyzed: {analyzed_count}")
        print(f"  - Skipped (cached): {skipped_count}")
        print(f"  - Errors: {error_count}")
    except Exception as e:
        print(f"[Emoji System] Failed to fetch application emojis: {e}")


async def analyze_server_emojis(guild, config, gemini_key, openai_key):
    """
    Analyzes all custom emojis in a server and caches descriptions.
    This should run on bot startup.
    """
    print(f"[Emoji System] Starting emoji analysis for guild: {guild.name}")
    
    # Get all custom emojis
    emojis = guild.emojis
    total_emojis = len(emojis)
    
    if total_emojis == 0:
        print("[Emoji System] No custom emojis found in this guild.")
        return
    
    print(f"[Emoji System] Found {total_emojis} custom emojis to analyze...")
    
    analyzed_count = 0
    skipped_count = 0
    error_count = 0
    
    for emoji in emojis:
        # Check if this emoji is already in the database
        existing = await get_emoji_description(str(emoji.id))
        
        if existing:
            print(f"[Emoji System] Skipping {emoji.name} (already analyzed)")
            skipped_count += 1
            continue
        
        # Analyze the emoji
        print(f"[Emoji System] Analyzing emoji: {emoji.name} ({analyzed_count + 1}/{total_emojis})")
        
        try:
            # Get the emoji URL
            emoji_url = str(emoji.url)
            
            # Download and convert to base64 if needed
            async with aiohttp.ClientSession() as session:
                async with session.get(emoji_url) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        # For Gemini, we need base64
                        base64_image = base64.b64encode(image_data).decode('utf-8')
                        data_url = f"data:image/png;base64,{base64_image}"
                    else:
                        print(f"[Emoji System] Failed to download emoji {emoji.name}")
                        error_count += 1
                        continue
            
            # Analyze with vision AI
            result, error = await analyze_emoji(emoji.name, data_url, config, gemini_key, openai_key)
            
            if error:
                print(f"[Emoji System] Error analyzing {emoji.name}: {error}")
                error_count += 1
                continue
            
            # Save to database
            description = result.get('description', 'Custom emoji')
            usage_context = result.get('usage_context', 'General use')
            
            success = await save_emoji_description(
                emoji_id=str(emoji.id),
                emoji_name=emoji.name,
                description=description,
                usage_context=usage_context,
                image_url=emoji_url
            )
            
            if success:
                analyzed_count += 1
                print(f"[Emoji System] ✓ Saved description for {emoji.name}")
            else:
                error_count += 1
                print(f"[Emoji System] ✗ Failed to save {emoji.name}")
            
            # Rate limiting - wait a bit between API calls
            await asyncio.sleep(2)
            
        except Exception as e:
            print(f"[Emoji System] Exception analyzing {emoji.name}: {e}")
            error_count += 1
    
    print(f"\n[Emoji System] Analysis complete!")
    print(f"  - Analyzed: {analyzed_count}")
    print(f"  - Skipped (cached): {skipped_count}")
    print(f"  - Errors: {error_count}")


async def get_emoji_context_for_ai(client=None):
    """
    Retrieves all emoji descriptions formatted for AI prompts.
    Only includes emojis that actually exist in the bot's application emoji collection.
    Combines pre-configured emojis from server_emojis.json with dynamically analyzed ones.
    Returns a string that can be included in the system prompt.
    
    Args:
        client: Discord client instance to fetch application emojis (optional but recommended)
    
    Note: This only includes application emojis (bot's own uploaded emojis) that work
    everywhere, not server-specific emojis. The replace_emoji_tags() function will handle
    guild-specific emoji restrictions at message send time.
    """
    # Get actual application emojis from Discord
    actual_app_emojis = {}
    if client:
        try:
            app_emojis = await client.fetch_application_emojis()
            actual_app_emojis = {emoji.name: emoji for emoji in app_emojis}
            print(f"[Emoji System] Found {len(actual_app_emojis)} application emojis for AI context")
        except Exception as e:
            print(f"[Emoji System] Warning: Could not fetch application emojis: {e}")
    
    # Load pre-configured server emojis
    server_emoji_config = load_server_emojis()
    configured_emojis = server_emoji_config.get('emojis', {})
    
    # Get dynamically analyzed emojis from database
    db_emojis = await get_all_emoji_descriptions()
    
    # Build list of emojis that actually exist
    verified_emojis = {}
    
    # First, add configured emojis that actually exist in application emojis
    for emoji_name, emoji_data in configured_emojis.items():
        if emoji_name in actual_app_emojis or not client:  # Include all if client not provided
            verified_emojis[emoji_name] = {
                'description': emoji_data.get('description', 'Custom emoji'),
                'usage': emoji_data.get('usage', 'General use'),
                'source': 'configured'
            }
        else:
            print(f"[Emoji System] Warning: Configured emoji '{emoji_name}' not found in application emojis")
    
    # Add database emojis that exist in application emojis
    for emoji in db_emojis:
        emoji_name = emoji['emoji_name']
        if emoji_name not in verified_emojis:  # Don't duplicate configured emojis
            if emoji_name in actual_app_emojis or not client:  # Include all if client not provided
                verified_emojis[emoji_name] = {
                    'description': emoji.get('description', 'Custom emoji'),
                    'usage': emoji.get('usage_context', 'General use'),
                    'source': 'discovered'
                }
    
    if not verified_emojis:
        return ""
    
    emoji_text = "\n\n**🎭 Your Emoji Arsenal:**\n"
    emoji_text += "You have custom emojis to express yourself! Use them naturally in conversations.\n"
    emoji_text += "**Format:** Just use :<emoji_name>: - NO backticks, NO quotes, NO other symbols!\n"
    emoji_text += "**When to use:** Enhance sarcasm, replace words, react emotionally, or add punch to your comebacks.\n"
    emoji_text += "**How much:** 1-3 emojis per message. Don't spam them.\n\n"
    
    # Separate configured and discovered emojis
    configured_list = {k: v for k, v in verified_emojis.items() if v['source'] == 'configured'}
    discovered_list = {k: v for k, v in verified_emojis.items() if v['source'] == 'discovered'}
    
    # Add configured emojis
    if configured_list:
        emoji_text += "**Available Emojis:**\n"
        for emoji_name, emoji_data in configured_list.items():
            description = emoji_data['description']
            usage = emoji_data['usage']
            emoji_text += f"- :{emoji_name}: - {description} | Best for: {usage}\n"
    
    # Add discovered emojis
    if discovered_list:
        if configured_list:
            emoji_text += "\n**Recently Discovered:**\n"
        else:
            emoji_text += "**Available Emojis:**\n"
        for emoji_name, emoji_data in discovered_list.items():
            description = emoji_data['description']
            usage = emoji_data['usage']
            emoji_text += f"- :{emoji_name}: - {description} | Best for: {usage}\n"
    
    emoji_text += "\n**Pro Tips:**\n"
    emoji_text += "- Mix emojis with text naturally (e.g., 'Alter :skull: das ist cringe')\n"
    emoji_text += "- Sometimes replace words with emojis for emphasis\n"
    emoji_text += "- Match emoji tone to your sarcasm level\n"
    emoji_text += "- Use recently discovered emojis to show you're paying attention\n"
    emoji_text += "- ONLY use emojis from the list above - don't make up emoji names!\n"
    
    return emoji_text


async def format_emoji_for_discord(emoji_id, emoji_name):
    """
    Formats an emoji ID and name into Discord's emoji format.
    """
    return f"<:{emoji_name}:{emoji_id}>"


async def get_emoji_by_name(emoji_name):
    """
    Retrieves an emoji from the database by its name.
    """
    emojis = await get_all_emoji_descriptions()
    
    for emoji in emojis:
        if emoji['emoji_name'].lower() == emoji_name.lower():
            return emoji
    
    return None
