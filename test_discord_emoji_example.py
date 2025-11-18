#!/usr/bin/env python3
"""
Test that matches the example from the requirement:

@bot.command()
async def emoji(ctx):
    # Just slap the whole ID inside the quotes
    await ctx.send("Here is the emote: <:6158_PepeLaugh:692690874295123988>")
    
This test verifies that emojis in the full format are kept as-is.
"""

import re


def sanitize_malformed_emojis(text):
    """Same function from bot.py"""
    text = re.sub(r'<<(a?):(\w+):(\d+)>\3>', r'<\1:\2:\3>', text)
    text = re.sub(r'<<(a?):(\w+):(\d+)>>', r'<\1:\2:\3>', text)
    text = re.sub(r'<(a?):(\w+):(\d+)>\3', r'<\1:\2:\3>', text)
    text = re.sub(r'(?<!`)`<(a?):(\w+):(\d+)>`(?!`)', r'<\1:\2:\3>', text)
    text = re.sub(r'(?<!`)`:(\w+):`(?!`)', r':\1:', text)
    return text


class MockEmoji:
    """Mock emoji object for testing"""
    def __init__(self, name, emoji_id, animated=False):
        self.name = name
        self.id = emoji_id
        self.animated = animated


async def replace_emoji_tags_mock(text, emoji_list):
    """Mock version matching the actual implementation in bot.py"""
    # First, sanitize any malformed emoji patterns
    text = sanitize_malformed_emojis(text)
    
    # Find all :emoji_name: tags that are NOT already in full format
    emoji_tags = re.findall(r'(?<!<)(?<!<a):(\w+):', text)
    
    if not emoji_tags:
        return text

    # Build emoji map
    emoji_map = {}
    for emoji in emoji_list:
        emoji_map[emoji.name] = emoji
        emoji_map[emoji.name.lower()] = emoji

    # Convert :emoji_name: to full format
    replaced_count = 0
    for tag in set(emoji_tags):
        emoji_obj = None
        
        if tag in emoji_map:
            emoji_obj = emoji_map[tag]
        elif tag.lower() in emoji_map:
            emoji_obj = emoji_map[tag.lower()]
        
        if emoji_obj:
            old_format = f":{tag}:"
            if hasattr(emoji_obj, 'animated') and emoji_obj.animated:
                new_format = f"<a:{emoji_obj.name}:{emoji_obj.id}>"
            else:
                new_format = f"<:{emoji_obj.name}:{emoji_obj.id}>"
            text = text.replace(old_format, new_format)
            replaced_count += 1
    
    return text


async def test_discord_example():
    """
    Test the exact example from the requirement.
    The requirement shows that full format emojis should be kept as-is.
    """
    print("=" * 80)
    print("DISCORD EMOJI EXAMPLE TEST")
    print("=" * 80)
    print()
    
    # Create mock emoji
    emojis = [
        MockEmoji("6158_PepeLaugh", "692690874295123988"),
    ]
    
    # Test 1: Full format should be kept as-is (the requirement example)
    print("Test 1: Full format emoji (from requirement example)")
    input_text = "Here is the emote: <:6158_PepeLaugh:692690874295123988>"
    expected = "Here is the emote: <:6158_PepeLaugh:692690874295123988>"
    
    result = await replace_emoji_tags_mock(input_text, emojis)
    
    print(f"  Input:    {input_text!r}")
    print(f"  Expected: {expected!r}")
    print(f"  Got:      {result!r}")
    
    if result == expected:
        print("  ✅ PASS - Full format emoji is kept unchanged!")
    else:
        print("  ❌ FAIL - Emoji was modified!")
        return False
    
    print()
    
    # Test 2: AI-generated short format should be converted to full format
    print("Test 2: AI-generated short format")
    input_text = "Here is the emote: :6158_PepeLaugh:"
    expected = "Here is the emote: <:6158_PepeLaugh:692690874295123988>"
    
    result = await replace_emoji_tags_mock(input_text, emojis)
    
    print(f"  Input:    {input_text!r}")
    print(f"  Expected: {expected!r}")
    print(f"  Got:      {result!r}")
    
    if result == expected:
        print("  ✅ PASS - Short format converted to full format!")
    else:
        print("  ❌ FAIL - Conversion didn't work!")
        return False
    
    print()
    print("=" * 80)
    print("✅ ALL TESTS PASSED!")
    print()
    print("Summary:")
    print("  - Full format emojis <:name:id> are kept unchanged")
    print("  - Short format emojis :name: are converted to full format")
    print("  - Discord will display both correctly as custom emojis")
    print("=" * 80)
    
    return True


if __name__ == "__main__":
    import asyncio
    import sys
    
    success = asyncio.run(test_discord_example())
    sys.exit(0 if success else 1)
