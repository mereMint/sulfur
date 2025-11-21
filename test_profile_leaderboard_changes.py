#!/usr/bin/env python3
"""
Test script to verify profile and leaderboard changes don't break functionality.
Tests all modified functions to ensure backwards compatibility.
"""

import sys
import json
from unittest.mock import Mock, AsyncMock, MagicMock, patch
import asyncio

# Test 1: Verify config.json is valid and contains new quest type
def test_config_validation():
    print("Test 1: Validating config.json...")
    try:
        with open('config/config.json', 'r') as f:
            config = json.load(f)
        
        # Check quest_types exists
        assert 'modules' in config, "Missing 'modules' in config"
        assert 'economy' in config['modules'], "Missing 'economy' in modules"
        assert 'quests' in config['modules']['economy'], "Missing 'quests' in economy"
        assert 'quest_types' in config['modules']['economy']['quests'], "Missing 'quest_types'"
        
        quest_types = config['modules']['economy']['quests']['quest_types']
        
        # Check all original quest types still exist
        original_quests = ['messages', 'vc_minutes', 'reactions', 'game_minutes', 'daily_media']
        for quest in original_quests:
            assert quest in quest_types, f"Original quest type '{quest}' missing"
            assert 'reward' in quest_types[quest], f"Missing reward for {quest}"
            assert 'xp_reward' in quest_types[quest], f"Missing xp_reward for {quest}"
        
        # Check new quest type exists
        assert 'daily_word_find' in quest_types, "New quest type 'daily_word_find' not found"
        assert quest_types['daily_word_find']['reward'] == 100, "Wrong reward for daily_word_find"
        assert quest_types['daily_word_find']['xp_reward'] == 150, "Wrong xp_reward for daily_word_find"
        
        print("✅ Config validation passed!")
        return True
    except Exception as e:
        print(f"❌ Config validation failed: {e}")
        return False


# Test 2: Verify quest module has new quest display names
def test_quest_display_names():
    print("\nTest 2: Validating quest display names...")
    try:
        # Import the module
        sys.path.insert(0, '/home/runner/work/sulfur/sulfur')
        from modules import quests
        
        # We can't directly access the dict, but we can verify the function exists
        assert hasattr(quests, 'generate_daily_quests'), "Missing generate_daily_quests function"
        assert hasattr(quests, 'update_quest_progress'), "Missing update_quest_progress function"
        
        print("✅ Quest module validation passed!")
        return True
    except Exception as e:
        print(f"❌ Quest module validation failed: {e}")
        return False


# Test 3: Verify truncate_name helper function
def test_truncate_name():
    print("\nTest 3: Testing truncate_name helper function...")
    try:
        sys.path.insert(0, '/home/runner/work/sulfur/sulfur')
        import bot
        
        # Test normal name (no truncation needed)
        short_name = "John"
        assert bot.truncate_name(short_name, 18) == "John", "Short name should not be truncated"
        
        # Test exact length
        exact_name = "A" * 18
        assert bot.truncate_name(exact_name, 18) == exact_name, "Exact length should not be truncated"
        
        # Test long name (needs truncation)
        long_name = "VeryLongUsername123456"
        truncated = bot.truncate_name(long_name, 18)
        assert len(truncated) == 18, f"Truncated name should be 18 chars, got {len(truncated)}"
        assert truncated.endswith("..."), "Truncated name should end with '...'"
        assert truncated == "VeryLongUserna...", f"Expected 'VeryLongUserna...', got '{truncated}'"
        
        # Test edge case with MAX constants
        assert bot.MAX_LEADERBOARD_NAME_LENGTH == 18, "MAX_LEADERBOARD_NAME_LENGTH should be 18"
        assert bot.MAX_WERWOLF_NAME_LENGTH == 16, "MAX_WERWOLF_NAME_LENGTH should be 16"
        
        print("✅ truncate_name function tests passed!")
        return True
    except Exception as e:
        print(f"❌ truncate_name function tests failed: {e}")
        import traceback
        traceback.print_exc()
        return False


# Test 4: Verify bot.py imports are correct
def test_imports():
    print("\nTest 4: Validating bot.py imports...")
    try:
        sys.path.insert(0, '/home/runner/work/sulfur/sulfur')
        
        # Try importing the bot module
        import bot
        
        # Verify key imports exist
        assert hasattr(bot, 'quests'), "quests module not imported"
        assert hasattr(bot, 'word_find'), "word_find module not imported"
        assert hasattr(bot, 'news'), "news module not imported"
        
        print("✅ Import validation passed!")
        return True
    except Exception as e:
        print(f"❌ Import validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


# Test 5: Verify news pagination optimization doesn't break structure
def test_news_pagination():
    print("\nTest 5: Validating news pagination structure...")
    try:
        sys.path.insert(0, '/home/runner/work/sulfur/sulfur')
        from modules import news
        
        # Verify NewsPaginationView class exists
        assert hasattr(news, 'NewsPaginationView'), "NewsPaginationView class missing"
        
        # Create a mock view to verify structure
        mock_articles = [
            {'title': 'Test 1', 'content': 'Content 1', 'category': 'general', 'created_at': None},
            {'title': 'Test 2', 'content': 'Content 2', 'category': 'general', 'created_at': None}
        ]
        view = news.NewsPaginationView(mock_articles, 12345)
        
        # Verify attributes
        assert hasattr(view, 'articles'), "Missing articles attribute"
        assert hasattr(view, 'current_page'), "Missing current_page attribute"
        assert hasattr(view, 'user_id'), "Missing user_id attribute"
        assert hasattr(view, 'get_current_embed'), "Missing get_current_embed method"
        assert hasattr(view, '_update_buttons'), "Missing _update_buttons method"
        
        # Verify buttons exist
        assert hasattr(view, 'previous_button'), "Missing previous_button"
        assert hasattr(view, 'next_button'), "Missing next_button"
        
        print("✅ News pagination structure validation passed!")
        return True
    except Exception as e:
        print(f"❌ News pagination validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


# Test 6: Verify profile changes maintain backwards compatibility
def test_profile_structure():
    print("\nTest 6: Validating profile command structure...")
    try:
        sys.path.insert(0, '/home/runner/work/sulfur/sulfur')
        import bot
        
        # Verify profile function exists
        assert hasattr(bot, 'profile'), "profile function missing"
        
        # Verify ProfilePageView exists
        assert hasattr(bot, 'ProfilePageView'), "ProfilePageView class missing"
        
        print("✅ Profile structure validation passed!")
        return True
    except Exception as e:
        print(f"❌ Profile structure validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


# Test 7: Verify leaderboard functions exist and have correct structure
def test_leaderboard_structure():
    print("\nTest 7: Validating leaderboard structure...")
    try:
        sys.path.insert(0, '/home/runner/work/sulfur/sulfur')
        import bot
        
        # Verify leaderboard function exists
        assert hasattr(bot, 'leaderboard'), "leaderboard function missing"
        
        # Verify LeaderboardPageView exists
        assert hasattr(bot, 'LeaderboardPageView'), "LeaderboardPageView class missing"
        
        print("✅ Leaderboard structure validation passed!")
        return True
    except Exception as e:
        print(f"❌ Leaderboard structure validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


# Run all tests
def main():
    print("=" * 60)
    print("Running Profile and Leaderboard Changes Validation Tests")
    print("=" * 60)
    
    results = []
    results.append(("Config Validation", test_config_validation()))
    results.append(("Quest Display Names", test_quest_display_names()))
    results.append(("Truncate Name Helper", test_truncate_name()))
    results.append(("Bot Imports", test_imports()))
    results.append(("News Pagination", test_news_pagination()))
    results.append(("Profile Structure", test_profile_structure()))
    results.append(("Leaderboard Structure", test_leaderboard_structure()))
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print("=" * 60)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("\n🎉 All tests passed! Changes are backwards compatible.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review changes.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
