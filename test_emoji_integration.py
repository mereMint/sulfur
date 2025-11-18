#!/usr/bin/env python3
"""
Integration test for emoji sanitization in context
Tests that the fix works with actual Discord-like message flows
"""

import re

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

# Simulate AI-generated responses with emoji issues
test_scenarios = [
    {
        "name": "AI response with static emoji issue",
        "input": "Hey! Das ist cool <<:thumbsup:123456789>123456789>",
        "expected": "Hey! Das ist cool <:thumbsup:123456789>",
    },
    {
        "name": "AI response with animated emoji issue",
        "input": "Haha! <<a:laughing:987654321>987654321> Das ist lustig!",
        "expected": "Haha! <a:laughing:987654321> Das ist lustig!",
    },
    {
        "name": "AI response with mixed emojis",
        "input": "<<:wave:111>111> Hallo! <<a:party:222>222> Let's celebrate!",
        "expected": "<:wave:111> Hallo! <a:party:222> Let's celebrate!",
    },
    {
        "name": "AI response with correct emojis (should not change)",
        "input": "Good job <:star:999> and <a:celebrate:888> well done!",
        "expected": "Good job <:star:999> and <a:celebrate:888> well done!",
    },
    {
        "name": "Complex message with multiple issues",
        "input": "Check this out <<:emoji1:111>111> and <<a:emoji2:222>222> also <:emoji3:333> works!",
        "expected": "Check this out <:emoji1:111> and <a:emoji2:222> also <:emoji3:333> works!",
    },
    {
        "name": "German text with emojis (real use case)",
        "input": "Guten Tag! <<:6153stare:1440047093044482142>1440047093044482142> Was geht?",
        "expected": "Guten Tag! <:6153stare:1440047093044482142> Was geht?",
    },
]

print("=" * 80)
print("EMOJI SANITIZATION INTEGRATION TEST")
print("=" * 80)
print()

passed = 0
failed = 0

for i, scenario in enumerate(test_scenarios, 1):
    result = sanitize_malformed_emojis(scenario["input"])
    success = result == scenario["expected"]
    
    if success:
        passed += 1
        status = "✓ PASS"
    else:
        failed += 1
        status = "✗ FAIL"
    
    print(f"Scenario {i}: {scenario['name']}")
    print(f"  Status:   {status}")
    if not success:
        print(f"  Input:    {scenario['input']!r}")
        print(f"  Expected: {scenario['expected']!r}")
        print(f"  Got:      {result!r}")
    print()

print("=" * 80)
print(f"RESULTS: {passed}/{len(test_scenarios)} scenarios passed")
print("=" * 80)

# Verify backward compatibility - existing patterns still work
print("\nBACKWARD COMPATIBILITY CHECK:")
backward_compat_tests = [
    ("<<:old:123>123>", "<:old:123>"),  # Old static pattern
    ("<<:old:123>>", "<:old:123>"),      # Old static pattern variant
    ("<:old:123>123", "<:old:123>"),    # Old trailing ID pattern
]

compat_passed = 0
for old_input, old_expected in backward_compat_tests:
    result = sanitize_malformed_emojis(old_input)
    if result == old_expected:
        compat_passed += 1
        print(f"  ✓ {old_input!r} → {result!r}")
    else:
        print(f"  ✗ {old_input!r} → {result!r} (expected {old_expected!r})")

print(f"\nBackward compatibility: {compat_passed}/{len(backward_compat_tests)} patterns still work")

if failed == 0 and compat_passed == len(backward_compat_tests):
    print("\n✅ All tests passed! Fix is working correctly.")
    exit(0)
else:
    print("\n❌ Some tests failed!")
    exit(1)
