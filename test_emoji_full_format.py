#!/usr/bin/env python3
"""
Test to verify that emojis are kept in full format and short format is converted to full format
"""

import re


def sanitize_malformed_emojis(text):
    """
    Fixes malformed emoji patterns that the AI might generate.
    Handles both static (<:name:id>) and animated (<a:name:id>) emojis.
    """
    # Fix pattern like <<:emoji_name:emoji_id>emoji_id> or <<a:emoji_name:emoji_id>emoji_id>
    text = re.sub(r'<<(a?):(\w+):(\d+)>\3>', r'<\1:\2:\3>', text)
    # Fix pattern like <<:emoji_name:emoji_id>> or <<a:emoji_name:emoji_id>>
    text = re.sub(r'<<(a?):(\w+):(\d+)>>', r'<\1:\2:\3>', text)
    # Fix pattern like <:emoji_name:emoji_id>emoji_id or <a:emoji_name:emoji_id>emoji_id (trailing ID)
    text = re.sub(r'<(a?):(\w+):(\d+)>\3', r'<\1:\2:\3>', text)
    # Remove single backticks around full emoji format (inline code), but not triple backticks (code blocks)
    text = re.sub(r'(?<!`)`<(a?):(\w+):(\d+)>`(?!`)', r'<\1:\2:\3>', text)
    # Remove single backticks around short emoji format too
    text = re.sub(r'(?<!`)`:(\w+):`(?!`)', r':\1:', text)
    return text


# Mock emoji object
class MockEmoji:
    def __init__(self, name, emoji_id, animated=False):
        self.name = name
        self.id = emoji_id
        self.animated = animated


async def replace_emoji_tags_mock(text, emoji_list):
    """
    Mock version of replace_emoji_tags for testing
    """
    # First, sanitize any malformed emoji patterns
    text = sanitize_malformed_emojis(text)
    
    # Find all :emoji_name: tags that are NOT already in full format
    # Use negative lookbehind to exclude <:name: and <a:name:
    emoji_tags = re.findall(r'(?<!<)(?<!<a):(\w+):', text)
    
    if not emoji_tags:
        return text

    # Build emoji map
    emoji_map = {}
    for emoji in emoji_list:
        emoji_map[emoji.name] = emoji
        emoji_map[emoji.name.lower()] = emoji

    # Convert :emoji_name: to full format <:emoji_name:emoji_id>
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


async def test_emoji_format():
    """Test that emojis are properly formatted for Discord"""
    
    # Create mock emojis
    emojis = [
        MockEmoji("6158_PepeLaugh", "692690874295123988"),
        MockEmoji("14029999iq", "1440047023456911370"),
        MockEmoji("stare", "1440047093044482142"),
        MockEmoji("animated_wave", "999888777666", animated=True),
    ]
    
    test_cases = [
        {
            "name": "Full format emoji should remain unchanged",
            "input": "Here is the emote: <:6158_PepeLaugh:692690874295123988>",
            "expected": "Here is the emote: <:6158_PepeLaugh:692690874295123988>",
        },
        {
            "name": "Short format should be converted to full format",
            "input": "Here is the emote: :6158_PepeLaugh:",
            "expected": "Here is the emote: <:6158_PepeLaugh:692690874295123988>",
        },
        {
            "name": "Multiple short format emojis",
            "input": "Test :stare: and :14029999iq: emojis",
            "expected": "Test <:stare:1440047093044482142> and <:14029999iq:1440047023456911370> emojis",
        },
        {
            "name": "Mixed short and full format",
            "input": ":6158_PepeLaugh: and <:stare:1440047093044482142>",
            "expected": "<:6158_PepeLaugh:692690874295123988> and <:stare:1440047093044482142>",
        },
        {
            "name": "Malformed emoji with trailing ID",
            "input": "<:14029999iq:1440047023456911370>1440047023456911370",
            "expected": "<:14029999iq:1440047023456911370>",
        },
        {
            "name": "Double-wrapped malformed emoji",
            "input": "<<:14029999iq:1440047023456911370>1440047023456911370>",
            "expected": "<:14029999iq:1440047023456911370>",
        },
        {
            "name": "Emoji with backticks should have backticks removed",
            "input": "Test `<:6158_PepeLaugh:692690874295123988>` emoji",
            "expected": "Test <:6158_PepeLaugh:692690874295123988> emoji",
        },
        {
            "name": "Short format with backticks converted to full format",
            "input": "Test `:6158_PepeLaugh:` emoji",
            "expected": "Test <:6158_PepeLaugh:692690874295123988> emoji",
        },
        {
            "name": "Animated emoji short format to full format",
            "input": "Wave :animated_wave: at you",
            "expected": "Wave <a:animated_wave:999888777666> at you",
        },
        {
            "name": "Animated emoji full format stays unchanged",
            "input": "Wave <a:animated_wave:999888777666> at you",
            "expected": "Wave <a:animated_wave:999888777666> at you",
        },
    ]
    
    print("=" * 80)
    print("EMOJI FULL FORMAT TEST SUITE")
    print("=" * 80)
    print()
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_cases, 1):
        result = await replace_emoji_tags_mock(test["input"], emojis)
        success = result == test["expected"]
        
        if success:
            passed += 1
            status = "✓ PASS"
        else:
            failed += 1
            status = "✗ FAIL"
        
        print(f"Test {i}: {test['name']}")
        print(f"  Status:   {status}")
        print(f"  Input:    {test['input']!r}")
        print(f"  Expected: {test['expected']!r}")
        print(f"  Got:      {result!r}")
        
        if not success:
            print(f"  ERROR: Output does not match expected!")
        
        print()
    
    print("=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed out of {passed + failed} tests")
    print("=" * 80)
    
    return failed == 0


if __name__ == "__main__":
    import asyncio
    import sys
    
    success = asyncio.run(test_emoji_format())
    sys.exit(0 if success else 1)
