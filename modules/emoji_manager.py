"""
Emoji Management Module for Sulfur Discord Bot
Handles emoji analysis, caching, and AI integration
"""

import discord
import asyncio
import base64
import aiohttp
from modules.db_helpers import (
    save_emoji_description, 
    get_all_emoji_descriptions,
    get_emoji_description
)
from modules.api_helpers import get_emoji_description as analyze_emoji


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


async def get_emoji_context_for_ai():
    """
    Retrieves all emoji descriptions formatted for AI prompts.
    Returns a string that can be included in the system prompt.
    """
    emojis = await get_all_emoji_descriptions()
    
    if not emojis:
        return ""
    
    emoji_text = "\n\n**Available Custom Emojis:**\n"
    emoji_text += "You can use these custom emojis in your responses:\n\n"
    
    for emoji in emojis:
        emoji_text += f"- `<:{emoji['emoji_name']}:{emoji['emoji_id']}>` - {emoji['description']}\n"
        emoji_text += f"  Usage: {emoji['usage_context']}\n"
    
    emoji_text += "\nUse these emojis naturally in your responses when appropriate!"
    
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
