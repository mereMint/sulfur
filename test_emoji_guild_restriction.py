#!/usr/bin/env python3
"""
Test suite for emoji guild restriction fix
Tests that the bot only uses accessible emojis (application emojis + guild-specific emojis)
"""

import re
import sys
from unittest.mock import Mock, AsyncMock, MagicMock

# Define the sanitize_malformed_emojis function for testing
def sanitize_malformed_emojis(text):
    """
    Fixes malformed emoji patterns that the AI might generate.
    Handles both static (<:name:id>) and animated (<a:name:id>) emojis.
    """
    text = re.sub(r'<<(a?):(\w+):(\d+)>\3>', r'<\1:\2:\3>', text)
    text = re.sub(r'<<(a?):(\w+):(\d+)>>', r'<\1:\2:\3>', text)
    text = re.sub(r'<(a?):(\w+):(\d+)>\3', r'<\1:\2:\3>', text)
    text = re.sub(r'(?<!`)`<(a?):(\w+):(\d+)>`(?!`)', r'<\1:\2:\3>', text)
    text = re.sub(r'(?<!`)`:(\w+):`(?!`)', r':\1:', text)
    return text


async def replace_emoji_tags(text, client, guild=None):
    """
    Replaces :emoji_name: tags with full Discord emoji format <:emoji_name:emoji_id>.
    Keeps existing full format emojis unchanged.
    Prioritizes application emojis (bot's own emojis) over server emojis.
    
    Args:
        text: The text containing emoji tags to replace
        client: The Discord client instance
        guild: Optional guild context. If provided, only uses emojis from this guild + application emojis.
               If None (DM context), only uses application emojis.
    
    This prevents the bot from using emojis from other servers that users cannot see.
    """
    # First, sanitize any malformed emoji patterns
    text = sanitize_malformed_emojis(text)
    
    # Find all :emoji_name: tags that are NOT already in full format
    emoji_tags = re.findall(r'(?<!<)(?<!<a):(\w+):', text)
    
    if not emoji_tags:
        return text

    emoji_map = {}
    
    # Only add server emojis if a guild context is provided
    if guild:
        for emoji in guild.emojis:
            if emoji.name not in emoji_map:
                emoji_map[emoji.name] = emoji
            emoji_map[emoji.name.lower()] = emoji
    
    # Always prioritize application emojis (they work everywhere)
    try:
        app_emojis = await client.fetch_application_emojis()
        for emoji in app_emojis:
            emoji_map[emoji.name] = emoji
            emoji_map[emoji.name.lower()] = emoji
    except Exception as e:
        print(f"Could not fetch application emojis: {e}")

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


def create_mock_emoji(name, emoji_id, animated=False):
    """Helper to create a mock Discord emoji object"""
    emoji = Mock()
    emoji.name = name
    emoji.id = emoji_id
    emoji.animated = animated
    return emoji


async def test_emoji_guild_restriction():
    """Test that emojis are restricted based on guild context"""
    
    print("Testing Emoji Guild Restriction Fix")
    print("=" * 80)
    
    test_cases = []
    
    # Setup mock data
    # Application emojis (bot's own - work everywhere)
    app_emoji1 = create_mock_emoji("dono", 111111)
    app_emoji2 = create_mock_emoji("gege", 222222)
    
    # Guild A emojis
    guild_a_emoji1 = create_mock_emoji("server_a_smile", 333333)
    guild_a_emoji2 = create_mock_emoji("server_a_wave", 444444)
    
    # Guild B emojis (should NOT be used when in Guild A)
    guild_b_emoji1 = create_mock_emoji("server_b_heart", 555555)
    guild_b_emoji2 = create_mock_emoji("server_b_fire", 666666)
    
    # Create mock client
    client = Mock()
    client.fetch_application_emojis = AsyncMock(return_value=[app_emoji1, app_emoji2])
    
    # Create mock guilds
    guild_a = Mock()
    guild_a.emojis = [guild_a_emoji1, guild_a_emoji2]
    
    guild_b = Mock()
    guild_b.emojis = [guild_b_emoji1, guild_b_emoji2]
    
    # Test 1: In Guild A context - should use app emojis + Guild A emojis only
    test_cases.append({
        "name": "Guild A context - uses Guild A emoji",
        "input": "Hello :server_a_smile:",
        "expected": "Hello <:server_a_smile:333333>",
        "guild": guild_a,
        "client": client,
    })
    
    # Test 2: In Guild A context - should NOT use Guild B emoji
    test_cases.append({
        "name": "Guild A context - cannot use Guild B emoji",
        "input": "Hello :server_b_heart:",
        "expected": "Hello :server_b_heart:",  # Should remain unchanged
        "guild": guild_a,
        "client": client,
    })
    
    # Test 3: In Guild A context - should use application emoji
    test_cases.append({
        "name": "Guild A context - uses application emoji",
        "input": "Hello :dono:",
        "expected": "Hello <:dono:111111>",
        "guild": guild_a,
        "client": client,
    })
    
    # Test 4: In DM context (no guild) - should only use application emojis
    test_cases.append({
        "name": "DM context - uses application emoji",
        "input": "Hello :gege:",
        "expected": "Hello <:gege:222222>",
        "guild": None,
        "client": client,
    })
    
    # Test 5: In DM context - should NOT use any server emoji
    test_cases.append({
        "name": "DM context - cannot use server emoji",
        "input": "Hello :server_a_smile:",
        "expected": "Hello :server_a_smile:",  # Should remain unchanged
        "guild": None,
        "client": client,
    })
    
    # Test 6: Multiple emojis - mixed accessible and inaccessible
    test_cases.append({
        "name": "Guild A - mixed emojis",
        "input": "Hi :dono: and :server_a_wave: but not :server_b_fire:",
        "expected": "Hi <:dono:111111> and <:server_a_wave:444444> but not :server_b_fire:",
        "guild": guild_a,
        "client": client,
    })
    
    # Test 7: Already formatted emojis should remain unchanged
    test_cases.append({
        "name": "Already formatted emojis unchanged",
        "input": "Already formatted: <:test:999999>",
        "expected": "Already formatted: <:test:999999>",
        "guild": guild_a,
        "client": client,
    })
    
    # Run tests
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_cases, 1):
        result = await replace_emoji_tags(test["input"], test["client"], test["guild"])
        
        status = "✓ PASS" if result == test["expected"] else "✗ FAIL"
        
        print(f"\nTest {i}: {test['name']}")
        print(f"  Status:   {status}")
        print(f"  Input:    '{test['input']}'")
        print(f"  Expected: '{test['expected']}'")
        print(f"  Got:      '{result}'")
        
        if result == test["expected"]:
            passed += 1
        else:
            failed += 1
    
    # Summary
    print("\n" + "=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 80)
    
    return failed == 0


if __name__ == "__main__":
    import asyncio
    success = asyncio.run(test_emoji_guild_restriction())
    sys.exit(0 if success else 1)
