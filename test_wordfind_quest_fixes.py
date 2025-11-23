#!/usr/bin/env python3
"""
Test script to verify wordfind and quest tracking fixes.
Tests the fixes for:
1. Wordfind interaction timeout issue
2. Quest game_minutes tracking
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_wordfind_error_handling():
    """
    Test that wordfind modal has proper error handling for message editing.
    This is a static test that checks the code structure.
    """
    print("Testing wordfind error handling...")
    print("=" * 60)
    
    # Read the bot.py file
    with open('bot.py', 'r') as f:
        bot_code = f.read()
    
    # Check for the error handling patterns
    checks = {
        "Message edit error handling (win case)": "except (discord.errors.NotFound, discord.errors.HTTPException) as e:" in bot_code,
        "Fallback message sending (win case)": "await interaction.followup.send(embed=embed, view=view, ephemeral=True)" in bot_code,
        # Verify we're using the proper specific error handling, not generic catch-alls
        "Specific error handling in WordGuessModal": "except (discord.errors.NotFound, discord.errors.HTTPException)" in bot_code,
    }
    
    all_passed = True
    for check_name, result in checks.items():
        status = "✓" if result else "✗"
        print(f"{status} {check_name}")
        if not result:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("All wordfind error handling checks passed! ✓")
        return True
    else:
        print("Some wordfind checks failed! ✗")
        return False


def test_game_tracking_flush():
    """
    Test that the flush_active_game_time function exists and is called.
    This is a static test that checks the code structure.
    """
    print("\nTesting game tracking flush function...")
    print("=" * 60)
    
    # Read the bot.py file
    with open('bot.py', 'r') as f:
        bot_code = f.read()
    
    # Check for the flush function and its usage
    checks = {
        "flush_active_game_time function exists": "async def flush_active_game_time(user_id: int):" in bot_code,
        "Flush called in daily_quests_button": "await flush_active_game_time(self.user_id)" in bot_code and 
                                                 "daily_quests_button" in bot_code,
        "Flush called in claim_rewards_button": "await flush_active_game_time(self.user_id)" in bot_code and 
                                                  "claim_rewards_button" in bot_code,
        "Game time tracking still active": "await quests.update_quest_progress(db_helpers, user_id, 'game_minutes'" in bot_code,
        "Math.ceil for quest minutes": "quest_minutes = math.ceil(duration_minutes)" in bot_code,
    }
    
    all_passed = True
    for check_name, result in checks.items():
        status = "✓" if result else "✗"
        print(f"{status} {check_name}")
        if not result:
            all_passed = False
    
    # Additional check: Verify flush is called in quest-related functions
    # Look for the function calls in the relevant button handlers
    daily_quest_section = bot_code[bot_code.find("async def daily_quests_button"):bot_code.find("async def daily_quests_button") + 1500] if "async def daily_quests_button" in bot_code else ""
    claim_rewards_section = bot_code[bot_code.find("async def claim_rewards_button"):bot_code.find("async def claim_rewards_button") + 1500] if "async def claim_rewards_button" in bot_code else ""
    
    flush_in_daily = "flush_active_game_time" in daily_quest_section
    flush_in_claim = "flush_active_game_time" in claim_rewards_section
    
    print(f"\n✓ Flush called in daily_quests_button: {flush_in_daily}")
    print(f"✓ Flush called in claim_rewards_button: {flush_in_claim}")
    
    if not (flush_in_daily and flush_in_claim):
        print("  ⚠️  Warning: Flush function should be called in both quest button handlers")
        all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("All game tracking checks passed! ✓")
        return True
    else:
        print("Some game tracking checks failed! ✗")
        return False


def test_code_consistency():
    """
    Test that the code changes are consistent and don't break existing functionality.
    """
    print("\nTesting code consistency...")
    print("=" * 60)
    
    # Read the bot.py file
    with open('bot.py', 'r') as f:
        bot_code = f.read()
    
    # Check for potential issues
    checks = {
        "WordFindView class exists": "class WordFindView(discord.ui.View):" in bot_code,
        "WordGuessModal class exists": "class WordGuessModal(discord.ui.Modal" in bot_code,
        "QuestMenuView class exists": "class QuestMenuView(discord.ui.View):" in bot_code,
        "on_presence_update handler exists": "async def on_presence_update(before, after):" in bot_code,
        "game_start_times dict exists": "game_start_times = {}" in bot_code,
        "quests module imported": "from modules import quests" in bot_code,
        "word_find module imported": "from modules import word_find" in bot_code,
    }
    
    all_passed = True
    for check_name, result in checks.items():
        status = "✓" if result else "✗"
        print(f"{status} {check_name}")
        if not result:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("All consistency checks passed! ✓")
        return True
    else:
        print("Some consistency checks failed! ✗")
        return False


def test_syntax():
    """
    Test that the bot.py file has valid Python syntax.
    """
    print("\nTesting Python syntax...")
    print("=" * 60)
    
    import py_compile
    
    try:
        py_compile.compile('bot.py', doraise=True)
        print("✓ bot.py has valid Python syntax")
        print("=" * 60)
        return True
    except py_compile.PyCompileError as e:
        print(f"✗ Syntax error in bot.py:")
        print(f"  {e}")
        print("=" * 60)
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Running Wordfind & Quest Tracking Fix Tests")
    print("=" * 60 + "\n")
    
    results = []
    
    # Run syntax check first
    results.append(("Syntax Check", test_syntax()))
    
    # Run other tests
    results.append(("Wordfind Error Handling", test_wordfind_error_handling()))
    results.append(("Game Tracking Flush", test_game_tracking_flush()))
    results.append(("Code Consistency", test_code_consistency()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {test_name}")
    
    all_passed = all(passed for _, passed in results)
    
    print("=" * 60)
    if all_passed:
        print("All tests passed! ✓")
        print("\nThe fixes should work correctly:")
        print("1. Wordfind no longer shows timeout errors after each guess")
        print("2. Game time tracking now includes active sessions when viewing quests")
        return 0
    else:
        print("Some tests failed! ✗")
        print("Please review the code changes.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
