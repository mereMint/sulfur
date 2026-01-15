"""
Sulfur Bot - Urban Dictionary Module
Fetches slang definitions from Urban Dictionary API.
"""

import aiohttp
import asyncio
from modules.logger_utils import bot_logger as logger


# Urban Dictionary API endpoint
URBAN_DICTIONARY_API = "https://api.urbandictionary.com/v0/define"

# API timeout in seconds
API_TIMEOUT = 10


async def search_urban_dictionary(term: str) -> dict:
    """
    Search for a term on Urban Dictionary.
    
    Args:
        term: The slang term to look up
    
    Returns:
        Dictionary with:
        - 'found': bool - whether the term was found
        - 'word': str - the word searched
        - 'definition': str - the top definition
        - 'example': str - usage example
        - 'thumbs_up': int - upvotes
        - 'thumbs_down': int - downvotes
        - 'author': str - who wrote the definition
        - 'permalink': str - link to the definition
        - 'all_definitions': list - all definitions found (up to 5)
    """
    result = {
        'found': False,
        'word': term,
        'definition': None,
        'example': None,
        'thumbs_up': 0,
        'thumbs_down': 0,
        'author': None,
        'permalink': None,
        'all_definitions': []
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            params = {'term': term}
            async with session.get(
                URBAN_DICTIONARY_API, 
                params=params, 
                timeout=aiohttp.ClientTimeout(total=API_TIMEOUT)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    definitions = data.get('list', [])
                    
                    if definitions:
                        # Get the top definition (most upvoted)
                        top_def = definitions[0]
                        result['found'] = True
                        result['word'] = top_def.get('word', term)
                        result['definition'] = _clean_text(top_def.get('definition', ''))
                        result['example'] = _clean_text(top_def.get('example', ''))
                        result['thumbs_up'] = top_def.get('thumbs_up', 0)
                        result['thumbs_down'] = top_def.get('thumbs_down', 0)
                        result['author'] = top_def.get('author', 'Unknown')
                        result['permalink'] = top_def.get('permalink', '')
                        
                        # Get up to 5 definitions for variety
                        for i, defn in enumerate(definitions[:5]):
                            result['all_definitions'].append({
                                'definition': _clean_text(defn.get('definition', '')),
                                'example': _clean_text(defn.get('example', '')),
                                'thumbs_up': defn.get('thumbs_up', 0),
                                'thumbs_down': defn.get('thumbs_down', 0),
                                'author': defn.get('author', 'Unknown')
                            })
                        
                        logger.info(f"Urban Dictionary: Found {len(definitions)} definitions for '{term}'")
                    else:
                        logger.debug(f"Urban Dictionary: No definitions found for '{term}'")
                else:
                    logger.warning(f"Urban Dictionary API returned status {response.status}")
                    
    except asyncio.TimeoutError:
        logger.warning(f"Timeout searching Urban Dictionary for '{term}'")
    except Exception as e:
        logger.error(f"Error searching Urban Dictionary for '{term}': {e}")
    
    return result


def _clean_text(text: str) -> str:
    """
    Clean Urban Dictionary text by removing brackets used for links.
    Urban Dictionary uses [word] to create links, we just want the word.
    
    Args:
        text: Raw text from Urban Dictionary
    
    Returns:
        Cleaned text with brackets removed
    """
    if not text:
        return ""
    # Remove [ and ] characters used for hyperlinks
    return text.replace('[', '').replace(']', '')


async def get_random_word() -> dict:
    """
    Get a random word from Urban Dictionary.
    
    Returns:
        Dictionary with word details or None if failed
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.urbandictionary.com/v0/random",
                timeout=aiohttp.ClientTimeout(total=API_TIMEOUT)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    definitions = data.get('list', [])
                    
                    if definitions:
                        top_def = definitions[0]
                        return {
                            'found': True,
                            'word': top_def.get('word', ''),
                            'definition': _clean_text(top_def.get('definition', '')),
                            'example': _clean_text(top_def.get('example', '')),
                            'thumbs_up': top_def.get('thumbs_up', 0),
                            'thumbs_down': top_def.get('thumbs_down', 0),
                            'author': top_def.get('author', 'Unknown'),
                            'permalink': top_def.get('permalink', '')
                        }
    except Exception as e:
        logger.error(f"Error getting random Urban Dictionary word: {e}")
    
    return {'found': False, 'word': None}


async def format_urban_definition(term: str, include_example: bool = True, max_length: int = 500) -> str:
    """
    Get a formatted Urban Dictionary definition suitable for Discord.
    
    Args:
        term: The term to look up
        include_example: Whether to include usage example
        max_length: Maximum length of the definition text
    
    Returns:
        Formatted string with the definition, or error message if not found
    """
    result = await search_urban_dictionary(term)
    
    if not result['found']:
        return f"Kein Urban Dictionary Eintrag für '{term}' gefunden. Entweder ist das Wort zu normal oder zu weird selbst für Urban Dictionary."
    
    # Truncate definition if too long
    definition = result['definition']
    if len(definition) > max_length:
        definition = definition[:max_length-3] + "..."
    
    output = f"**{result['word']}**\n{definition}"
    
    if include_example and result['example']:
        example = result['example']
        if len(example) > 200:
            example = example[:197] + "..."
        output += f"\n\n*Beispiel:* {example}"
    
    # Add rating
    output += f"\n\n👍 {result['thumbs_up']} | 👎 {result['thumbs_down']}"
    
    return output


async def get_definition_for_ai(term: str) -> str:
    """
    Get a short Urban Dictionary definition formatted for AI context.
    This is what gets injected into the AI's context when it needs to look up a word.
    
    Args:
        term: The term to look up
    
    Returns:
        Short definition string for AI context, or empty string if not found
    """
    result = await search_urban_dictionary(term)
    
    if not result['found']:
        return ""
    
    # Keep it short for AI context - just the core meaning
    definition = result['definition']
    if len(definition) > 200:
        definition = definition[:197] + "..."
    
    return f"[Urban Dictionary: '{result['word']}' = {definition}]"
