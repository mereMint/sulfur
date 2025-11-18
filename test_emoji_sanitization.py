#!/usr/bin/env python3
"""
Test suite for emoji sanitization fix
Tests the sanitize_malformed_emojis function with various emoji formats
"""

import re
import sys

# Define the function directly to avoid importing the whole bot
def sanitize_malformed_emojis(text):
    """
    Fixes malformed emoji patterns that the AI might generate.
    Handles both static (<:name:id>) and animated (<a:name:id>) emojis.
    Examples: <<:name:id>id> -> <:name:id>, <<a:name:id>id> -> <a:name:id>
    """
    # Fix pattern like <<:emoji_name:emoji_id>emoji_id> or <<a:emoji_name:emoji_id>emoji_id>
    text = re.sub(r'<<(a?):(\w+):(\d+)>\3>', r'<\1:\2:\3>', text)
    # Fix pattern like <<:emoji_name:emoji_id>> or <<a:emoji_name:emoji_id>>
    text = re.sub(r'<<(a?):(\w+):(\d+)>>', r'<\1:\2:\3>', text)
    # Fix pattern like <:emoji_name:emoji_id>emoji_id or <a:emoji_name:emoji_id>emoji_id (trailing ID)
    text = re.sub(r'<(a?):(\w+):(\d+)>\3', r'<\1:\2:\3>', text)
    return text

def test_sanitize_malformed_emojis():
    """Test the sanitize_malformed_emojis function with comprehensive test cases"""
    
    test_cases = [
        # Static emojis - malformed patterns that should be fixed
        {
            "name": "Static emoji: double-wrapped with trailing ID",
            "input": "<<:6153stare:1440047093044482142>1440047093044482142>",
            "expected": "<:6153stare:1440047093044482142>",
        },
        {
            "name": "Static emoji: double-wrapped without trailing ID",
            "input": "<<:6153stare:1440047093044482142>>",
            "expected": "<:6153stare:1440047093044482142>",
        },
        {
            "name": "Static emoji: correct format with trailing ID",
            "input": "<:6153stare:1440047093044482142>1440047093044482142",
            "expected": "<:6153stare:1440047093044482142>",
        },
        
        # Animated emojis - malformed patterns that should be fixed
        {
            "name": "Animated emoji: double-wrapped with trailing ID",
            "input": "<<a:animated:123456789>123456789>",
            "expected": "<a:animated:123456789>",
        },
        {
            "name": "Animated emoji: double-wrapped without trailing ID",
            "input": "<<a:animated:123456789>>",
            "expected": "<a:animated:123456789>",
        },
        {
            "name": "Animated emoji: correct format with trailing ID",
            "input": "<a:animated:123456789>123456789",
            "expected": "<a:animated:123456789>",
        },
        
        # Already correct formats - should NOT be modified
        {
            "name": "Static emoji: already correct",
            "input": "<:correct:999>",
            "expected": "<:correct:999>",
        },
        {
            "name": "Animated emoji: already correct",
            "input": "<a:correct_animated:999>",
            "expected": "<a:correct_animated:999>",
        },
        
        # Multiple emojis in text
        {
            "name": "Multiple static emojis: mixed malformed and correct",
            "input": "Hello <<:emoji1:111>111> world <:emoji2:222> test",
            "expected": "Hello <:emoji1:111> world <:emoji2:222> test",
        },
        {
            "name": "Multiple animated emojis: all malformed",
            "input": "Test <<a:emoji1:111>111> and <<a:emoji2:222>222>",
            "expected": "Test <a:emoji1:111> and <a:emoji2:222>",
        },
        {
            "name": "Mixed static and animated: all malformed",
            "input": "<<:static:111>111> and <<a:animated:222>222>",
            "expected": "<:static:111> and <a:animated:222>",
        },
        
        # Edge cases
        {
            "name": "No emojis in text",
            "input": "Just plain text with no emojis",
            "expected": "Just plain text with no emojis",
        },
        {
            "name": "Emoji name with numbers",
            "input": "<<:emoji123test:456789>456789>",
            "expected": "<:emoji123test:456789>",
        },
        {
            "name": "Empty string",
            "input": "",
            "expected": "",
        },
    ]
    
    passed = 0
    failed = 0
    
    print("=" * 80)
    print("EMOJI SANITIZATION TEST SUITE")
    print("=" * 80)
    print()
    
    for i, test in enumerate(test_cases, 1):
        result = sanitize_malformed_emojis(test["input"])
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
    success = test_sanitize_malformed_emojis()
    sys.exit(0 if success else 1)
