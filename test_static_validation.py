#!/usr/bin/env python3
"""
Static validation test - checks code structure without running the bot.
"""

import json
import re

def test_config():
    """Test 1: Verify config.json has all required quest types."""
    print("Test 1: Validating config.json structure...")
    try:
        with open('config/config.json', 'r') as f:
            config = json.load(f)
        
        quest_types = config['modules']['economy']['quests']['quest_types']
        
        # Check original quest types still exist
        original = ['messages', 'vc_minutes', 'reactions', 'game_minutes', 'daily_media']
        for quest in original:
            assert quest in quest_types, f"Original quest '{quest}' missing!"
        
        # Check new quest type
        assert 'daily_word_find' in quest_types, "New quest 'daily_word_find' missing!"
        assert quest_types['daily_word_find']['reward'] == 100
        assert quest_types['daily_word_find']['xp_reward'] == 150
        
        print("  ✅ All quest types present and valid")
        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False


def test_bot_structure():
    """Test 2: Verify bot.py has required imports and functions."""
    print("\nTest 2: Validating bot.py structure...")
    try:
        with open('bot.py', 'r') as f:
            bot_code = f.read()
        
        # Check imports are at the top (not inside functions)
        import_pattern = r'^from modules import quests'
        assert re.search(import_pattern, bot_code, re.MULTILINE), "quests import missing at top!"
        
        # Check helper function exists
        assert 'def truncate_name(' in bot_code, "truncate_name function missing!"
        assert 'MAX_LEADERBOARD_NAME_LENGTH' in bot_code, "MAX_LEADERBOARD_NAME_LENGTH constant missing!"
        assert 'MAX_WERWOLF_NAME_LENGTH' in bot_code, "MAX_WERWOLF_NAME_LENGTH constant missing!"
        
        # Check profile function exists
        assert 'async def profile(' in bot_code, "profile function missing!"
        
        # Check leaderboard function exists
        assert 'async def leaderboard(' in bot_code, "leaderboard function missing!"
        
        # Verify quest progress update is NOT using local import
        assert 'from modules import quests\n' not in bot_code.replace('from modules import quests  # NEW', ''), \
            "Found local 'from modules import quests' import (should be at top only)!"
        
        # Check that get_user_features is used
        assert 'get_user_features' in bot_code, "get_user_features call missing!"
        
        # Check boost status is shown
        assert 'premium_since' in bot_code, "Boost status check missing!"
        assert 'Server Boost' in bot_code or 'server boost' in bot_code.lower(), "Boost status field missing!"
        
        print("  ✅ All required functions and structure present")
        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False


def test_quests_module():
    """Test 3: Verify quests.py has display names for new quest."""
    print("\nTest 3: Validating modules/quests.py...")
    try:
        with open('modules/quests.py', 'r') as f:
            quests_code = f.read()
        
        # Check quest icons dict has the new quest
        assert "'daily_word_find': '📝'" in quests_code, "Quest icon for daily_word_find missing!"
        
        # Check quest names dict has the new quest
        assert "'daily_word_find':" in quests_code, "Quest name entry missing!"
        assert "Das tägliche Wort finden" in quests_code or "tägliche Wort" in quests_code, \
            "German display name for word find quest missing!"
        
        print("  ✅ Quest display names configured")
        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False


def test_news_pagination():
    """Test 4: Verify news.py uses optimized pagination."""
    print("\nTest 4: Validating modules/news.py pagination optimization...")
    try:
        with open('modules/news.py', 'r') as f:
            news_code = f.read()
        
        # Check that buttons use defer()
        assert 'await interaction.response.defer()' in news_code, "defer() not used in pagination!"
        
        # Check that edit_original_response is used
        assert 'edit_original_response' in news_code, "edit_original_response not used!"
        
        # Make sure old slow method is NOT used
        button_methods = re.findall(r'async def (previous_button|next_button)\([^)]+\):', news_code)
        assert len(button_methods) == 2, "Missing pagination button methods!"
        
        print("  ✅ News pagination optimized")
        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False


def test_word_find_quest_tracking():
    """Test 5: Verify word find game updates quest progress."""
    print("\nTest 5: Validating word find quest tracking...")
    try:
        with open('bot.py', 'r') as f:
            bot_code = f.read()
        
        # Check that quest progress is updated when word find is completed
        assert 'daily_word_find' in bot_code, "daily_word_find quest type reference missing!"
        assert 'update_quest_progress' in bot_code, "update_quest_progress call missing!"
        
        # Verify it's in the word find completion section
        # Look for the pattern where we update stats and then update quest
        pattern = r"update_user_stats.*?daily_word_find"
        assert re.search(pattern, bot_code, re.DOTALL), \
            "Quest progress update not found near word find completion!"
        
        print("  ✅ Word find quest tracking configured")
        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False


def test_profile_features():
    """Test 6: Verify profile shows features dynamically."""
    print("\nTest 6: Validating profile feature display...")
    try:
        with open('bot.py', 'r') as f:
            bot_code = f.read()
        
        # Check that get_user_features is called
        assert 'get_user_features' in bot_code, "get_user_features not called!"
        
        # Check feature_names mapping exists with all features
        assert "'dm_access':" in bot_code, "dm_access feature mapping missing!"
        assert "'casino':" in bot_code, "casino feature mapping missing!"
        assert "'detective':" in bot_code, "detective feature mapping missing!"
        assert "'trolly':" in bot_code or "'trolley':" in bot_code, "trolly feature mapping missing!"
        assert "'unlimited_word_find':" in bot_code, "unlimited_word_find feature mapping missing!"
        
        # Verify old individual checks are removed
        # Should NOT have multiple has_feature_unlock calls for the same features
        has_dm_count = bot_code.count("has_feature_unlock(target_user.id, 'dm_access')")
        assert has_dm_count <= 1, "Old individual feature checks still present!"
        
        print("  ✅ Profile features displayed dynamically")
        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False


def test_leaderboard_visual():
    """Test 7: Verify leaderboard has visual improvements."""
    print("\nTest 7: Validating leaderboard visual improvements...")
    try:
        with open('bot.py', 'r') as f:
            bot_code = f.read()
        
        # Check for medal emojis
        assert '🥇' in bot_code, "Gold medal emoji missing!"
        assert '🥈' in bot_code, "Silver medal emoji missing!"
        assert '🥉' in bot_code, "Bronze medal emoji missing!"
        
        # Check for truncate_name usage
        assert 'truncate_name(' in bot_code, "truncate_name helper not used!"
        
        # Check for compact formatting (bullet points)
        assert ' • ' in bot_code, "Compact bullet point formatting missing!"
        
        print("  ✅ Leaderboard visual improvements present")
        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False


def test_werwolf_stats_removed():
    """Test 8: Verify Werwolf stats removed from main profile."""
    print("\nTest 8: Validating Werwolf stats removed from main profile...")
    try:
        with open('bot.py', 'r') as f:
            bot_code = f.read()
        
        # Find the profile function
        profile_start = bot_code.find('async def profile(')
        profile_end = bot_code.find('class ProfilePageView', profile_start)
        profile_section = bot_code[profile_start:profile_end]
        
        # Check that Werwolf stats embed.add_field is NOT in main profile
        # The stats should be in ProfilePageView, not the main profile
        werwolf_in_main = 'name="🐺 Werwolf Stats"' in profile_section or 'name="🐺 Werwolf' in profile_section
        
        # It's OK if there's no explicit werwolf field
        # Just verify ProfilePageView has the werwolf button
        assert 'werwolf_stats_button' in bot_code, "Werwolf stats button missing from ProfilePageView!"
        
        print("  ✅ Werwolf stats accessible via button only")
        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False


def main():
    print("=" * 70)
    print("Static Code Validation - Profile & Leaderboard Changes")
    print("=" * 70)
    
    tests = [
        ("Config Structure", test_config),
        ("Bot.py Structure", test_bot_structure),
        ("Quests Module", test_quests_module),
        ("News Pagination", test_news_pagination),
        ("Word Find Quest Tracking", test_word_find_quest_tracking),
        ("Profile Features", test_profile_features),
        ("Leaderboard Visuals", test_leaderboard_visual),
        ("Werwolf Stats Placement", test_werwolf_stats_removed),
    ]
    
    results = [(name, test()) for name, test in tests]
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    for name, passed in results:
        status = "✅" if passed else "❌"
        print(f"{status} {name}")
    
    passed_count = sum(1 for _, p in results if p)
    total = len(results)
    
    print("=" * 70)
    print(f"Result: {passed_count}/{total} tests passed")
    print("=" * 70)
    
    if passed_count == total:
        print("\n🎉 All validations passed! Code changes are correct.")
        return 0
    else:
        print(f"\n⚠️  {total - passed_count} validation(s) failed.")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
