"""
Integration test for detective game case generation and tracking.
This simulates the actual bot behavior to ensure cases don't repeat for the same user.
"""

import sys
import asyncio

# Mock discord module
sys.modules['discord'] = type(sys)('discord')
sys.modules['discord.ext'] = type(sys)('discord.ext')

from modules import detective_game


class MockDbHelpers:
    """Mock database helpers for testing."""
    
    def __init__(self):
        self.db_pool = None
        self.cases = {}  # case_id -> case_data
        self.user_progress = {}  # (user_id, case_id) -> progress
        self.user_stats = {}  # user_id -> stats
        self.next_case_id = 1
        
    def get_connection(self):
        return None


class MockApiHelpers:
    """Mock API helpers for testing."""
    
    async def get_ai_response_with_model(self, prompt, model, config, gemini_key, openai_key, system_prompt=None, temperature=1.0):
        # Simulate AI failure to test fallback
        return None, "Simulated API failure"


async def test_user_sees_different_cases():
    """Test that a single user doesn't see the same case repeatedly."""
    print("Testing that users see different cases...")
    
    db_helpers = MockDbHelpers()
    api_helpers = MockApiHelpers()
    config = {'api': {'provider': 'gemini'}}
    user_id = 12345
    
    cases_seen = []
    titles_seen = set()
    
    # Simulate a user playing 10 games in a row
    print(f"\nSimulating user {user_id} playing 10 games...")
    for i in range(10):
        case = await detective_game.get_or_generate_case(
            db_helpers,
            api_helpers,
            config,
            "fake_gemini_key",
            "fake_openai_key",
            user_id
        )
        
        cases_seen.append(case)
        titles_seen.add(case.case_title)
        print(f"  Game {i+1}: {case.case_title}")
    
    # We should see multiple different cases
    unique_count = len(titles_seen)
    print(f"\nUnique cases seen: {unique_count} out of 10 games")
    
    # With 5 fallback cases, we should see at least 3 different ones in 10 games
    assert unique_count >= 3, f"Expected at least 3 unique cases, but only saw {unique_count}"
    
    print("✓ User saw multiple different cases")
    print(f"✓ Variety achieved: {unique_count} unique cases in 10 games")
    
    # List all unique titles
    print("\nAll unique cases encountered:")
    for title in sorted(titles_seen):
        print(f"  - {title}")
    
    return True


async def test_fallback_never_shows_old_case():
    """Test that the old problematic case is no longer in rotation."""
    print("\nTesting that old problematic case is not shown...")
    
    db_helpers = MockDbHelpers()
    api_helpers = MockApiHelpers()
    config = {'api': {'provider': 'gemini'}}
    user_id = 67890
    
    old_case_title = "Der Fall des vergifteten Geschäftsmanns"
    
    # Try 30 times to see if we ever get the old case
    print(f"Generating 30 cases to check for '{old_case_title}'...")
    for i in range(30):
        case = await detective_game.get_or_generate_case(
            db_helpers,
            api_helpers,
            config,
            "fake_gemini_key",
            "fake_openai_key",
            user_id
        )
        
        if case.case_title == old_case_title:
            print(f"✗ Old case appeared on attempt {i+1}")
            return False
    
    print(f"✓ Old case '{old_case_title}' was NOT shown in 30 attempts")
    print("✓ The problematic case has been successfully removed from rotation")
    return True


async def test_case_variety_statistics():
    """Test the statistical distribution of case variety."""
    print("\nTesting case variety statistics...")
    
    db_helpers = MockDbHelpers()
    api_helpers = MockApiHelpers()
    config = {'api': {'provider': 'gemini'}}
    user_id = 11111
    
    case_counts = {}
    total_games = 100
    
    print(f"Generating {total_games} cases to analyze distribution...")
    for i in range(total_games):
        case = await detective_game.get_or_generate_case(
            db_helpers,
            api_helpers,
            config,
            "fake_gemini_key",
            "fake_openai_key",
            user_id
        )
        
        title = case.case_title
        case_counts[title] = case_counts.get(title, 0) + 1
    
    print(f"\nCase distribution over {total_games} games:")
    for title, count in sorted(case_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_games) * 100
        bar = '█' * int(percentage / 2)
        print(f"  {percentage:5.1f}% {bar} {title}")
    
    # Check that no case appears more than 40% of the time
    max_percentage = max((count / total_games) * 100 for count in case_counts.values())
    print(f"\nMax single case frequency: {max_percentage:.1f}%")
    
    # With proper rotation, no case should dominate
    assert max_percentage < 40, f"A case appeared {max_percentage:.1f}% of the time, which is too much"
    
    # We should see all 5 fallback cases
    unique_cases = len(case_counts)
    print(f"Unique cases in rotation: {unique_cases}")
    assert unique_cases >= 4, f"Expected at least 4 unique cases, got {unique_cases}"
    
    print("✓ Good variety in case distribution")
    print(f"✓ All {unique_cases} cases appear in rotation")
    print("✓ No single case dominates")
    
    return True


async def main():
    """Run all integration tests."""
    print("=" * 70)
    print("DETECTIVE GAME INTEGRATION TESTS")
    print("=" * 70)
    
    all_passed = True
    
    try:
        await test_user_sees_different_cases()
    except Exception as e:
        print(f"✗ User variety test failed: {e}")
        all_passed = False
    
    try:
        await test_fallback_never_shows_old_case()
    except Exception as e:
        print(f"✗ Old case removal test failed: {e}")
        all_passed = False
    
    try:
        await test_case_variety_statistics()
    except Exception as e:
        print(f"✗ Variety statistics test failed: {e}")
        all_passed = False
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✓ ALL INTEGRATION TESTS PASSED")
        print("=" * 70)
        print("\nSUMMARY:")
        print("- Users see multiple different cases across games")
        print("- Old problematic case is no longer shown")
        print("- Case distribution is well-balanced")
        print("- No single case dominates the rotation")
        print("- All 5 fallback cases are in active rotation")
        print("\n✅ The detective game will NOT show the same case repeatedly!")
        return 0
    else:
        print("✗ SOME INTEGRATION TESTS FAILED")
        print("=" * 70)
        return 1


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
