#!/usr/bin/env python3
"""
Verification test for the emoji formatting fix.
Tests the exact issue described in the problem statement.
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
    # Remove single backticks around emoji patterns (inline code), but not triple backticks (code blocks)
    text = re.sub(r'(?<!`)`<(a?):(\w+):(\d+)>`(?!`)', r'<\1:\2:\3>', text)
    return text


def test_problem_statement_issue():
    """
    Test the exact issue from the problem statement:
    Input: <<:14029999iq:1440047023456911370>1440047023456911370>
    Expected: <:14029999iq:1440047023456911370>
    """
    print("=" * 70)
    print("EMOJI FIX VERIFICATION - PROBLEM STATEMENT TEST")
    print("=" * 70)
    print()
    
    # The exact pattern from the problem statement
    problem_input = "<<:14029999iq:1440047023456911370>1440047023456911370>"
    expected_output = "<:14029999iq:1440047023456911370>"
    
    print("Testing the EXACT issue from problem statement:")
    print(f"  Input:    {problem_input!r}")
    print(f"  Expected: {expected_output!r}")
    
    result = sanitize_malformed_emojis(problem_input)
    
    print(f"  Got:      {result!r}")
    
    if result == expected_output:
        print("  ✅ FIXED! Emoji is now correctly formatted.")
    else:
        print("  ❌ FAILED! Emoji still malformed.")
        return False
    
    print()
    
    # Test with backticks (Discord code formatting issue)
    print("Testing with backticks (Discord code formatting):")
    backtick_input = f"`{problem_input}`"
    expected_backtick = expected_output  # Backticks should be removed
    
    print(f"  Input:    {backtick_input!r}")
    print(f"  Expected: {expected_backtick!r}")
    
    result_backtick = sanitize_malformed_emojis(backtick_input)
    
    print(f"  Got:      {result_backtick!r}")
    
    if result_backtick == expected_backtick:
        print("  ✅ FIXED! Backticks removed, Discord won't render as code.")
    else:
        print("  ❌ FAILED! Backticks not properly handled.")
        return False
    
    print()
    
    # Test variations
    print("Testing variations of the issue:")
    test_cases = [
        # Problem statement pattern
        ("<<:14029999iq:1440047023456911370>1440047023456911370>", 
         "<:14029999iq:1440047023456911370>"),
        
        # With backticks (code formatting)
        ("`<<:14029999iq:1440047023456911370>1440047023456911370>`", 
         "<:14029999iq:1440047023456911370>"),
        
        # Already correct format (should not change)
        ("<:14029999iq:1440047023456911370>", 
         "<:14029999iq:1440047023456911370>"),
        
        # Double wrapped only
        ("<<:14029999iq:1440047023456911370>>", 
         "<:14029999iq:1440047023456911370>"),
        
        # Trailing ID only
        ("<:14029999iq:1440047023456911370>1440047023456911370", 
         "<:14029999iq:1440047023456911370>"),
        
        # In sentence context
        ("Hello `<<:14029999iq:1440047023456911370>1440047023456911370>` world!", 
         "Hello <:14029999iq:1440047023456911370> world!"),
    ]
    
    all_passed = True
    for i, (test_input, expected) in enumerate(test_cases, 1):
        result = sanitize_malformed_emojis(test_input)
        status = "✅" if result == expected else "❌"
        
        if result != expected:
            all_passed = False
        
        print(f"  {status} Test {i}: {test_input[:50]!r}... → {result[:50]!r}")
    
    print()
    print("=" * 70)
    
    if all_passed:
        print("✅ ALL TESTS PASSED - EMOJI FORMATTING ISSUE FIXED!")
        print()
        print("Summary of fixes:")
        print("  1. Double brackets removed: <<:name:id>> → <:name:id>")
        print("  2. Trailing IDs removed: <:name:id>id → <:name:id>")
        print("  3. Backticks removed: `<:name:id>` → <:name:id>")
        print("  4. Discord code formatting prevented (no backticks)")
        print()
        print("The emoji will now display correctly in Discord as:")
        print(f"  {expected_output}")
        print()
        return True
    else:
        print("❌ SOME TESTS FAILED")
        return False


if __name__ == "__main__":
    import sys
    success = test_problem_statement_issue()
    sys.exit(0 if success else 1)
