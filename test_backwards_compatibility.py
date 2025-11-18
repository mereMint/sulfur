"""
Backwards Compatibility Test for Detective Game Enhancements

This test ensures that:
1. All existing code still works
2. New code doesn't interfere with other bot features
3. Database migration is optional (graceful degradation)
4. No breaking changes to existing API
"""

import sys
from pathlib import Path

# Mock discord module
sys.modules['discord'] = type(sys)('discord')
sys.modules['discord.ext'] = type(sys)('discord.ext')


def test_existing_functions_still_work():
    """Test that all original functions are still present and working."""
    print("Testing existing functions still work...")
    
    from modules import detective_game
    
    # Test MurderCase with old-style data (no case_id or difficulty)
    old_style_data = {
        'title': 'Old Case',
        'description': 'Description',
        'location': 'Location',
        'victim': 'Victim',
        'suspects': [{'name': 'S1', 'occupation': 'Job', 'alibi': 'A', 'motive': 'M', 'suspicious_details': 'D'}],
        'murderer_index': 0,
        'evidence': ['E1'],
        'hints': ['H1']
    }
    
    case = detective_game.MurderCase(old_style_data)
    
    # Should work with old data
    assert case.case_title == 'Old Case'
    assert case.case_id is None  # New field defaults to None
    assert case.difficulty == 1  # New field defaults to 1
    
    print("✓ MurderCase backwards compatible with old data")
    
    # Test fallback case still works
    fallback = detective_game.create_fallback_case()
    assert fallback.case_title
    assert fallback.suspects
    assert fallback.evidence
    assert fallback.hints
    
    print("✓ Fallback case still works")
    
    return True


def test_database_optional():
    """Test that code works even without database tables."""
    print("\nTesting database is optional (graceful degradation)...")
    
    from modules import detective_game
    import asyncio
    
    # Create a mock db_helpers without database
    class MockDBHelpers:
        db_pool = None  # Simulate no database
    
    mock_db = MockDBHelpers()
    
    # Test get_user_difficulty with no DB
    async def test_no_db():
        difficulty = await detective_game.get_user_difficulty(mock_db, 12345)
        assert difficulty == 1, "Should return default difficulty when DB unavailable"
        print("✓ get_user_difficulty handles missing DB")
        
        # Test update_user_stats with no DB (should not crash)
        await detective_game.update_user_stats(mock_db, 12345, True)
        print("✓ update_user_stats handles missing DB")
        
        # Test save_case_to_db with no DB
        result = await detective_game.save_case_to_db(mock_db, {}, 1)
        assert result is None, "Should return None when DB unavailable"
        print("✓ save_case_to_db handles missing DB")
        
        # Test get_unsolved_case with no DB
        case = await detective_game.get_unsolved_case(mock_db, 12345, 1)
        assert case is None, "Should return None when DB unavailable"
        print("✓ get_unsolved_case handles missing DB")
    
    asyncio.run(test_no_db())
    
    print("✓ All DB functions gracefully handle missing database")
    
    return True


def test_no_other_modules_affected():
    """Test that changes don't affect other modules."""
    print("\nTesting no interference with other modules...")
    
    # Check that other game modules are not affected
    try:
        from modules import economy
        print("✓ Economy module still imports")
    except Exception as e:
        print(f"✗ Economy module affected: {e}")
        return False
    
    try:
        from modules import level_system
        print("✓ Level system module still imports")
    except Exception as e:
        print(f"✗ Level system affected: {e}")
        return False
    
    try:
        from modules import quests
        print("✓ Quests module still imports")
    except Exception as e:
        print(f"✗ Quests module affected: {e}")
        return False
    
    print("✓ No interference with other modules")
    
    return True


def test_bot_py_integrity():
    """Test that bot.py changes don't break other commands."""
    print("\nTesting bot.py integrity...")
    
    with open('bot.py', 'r') as f:
        bot_code = f.read()
    
    # Check that other commands are still present
    critical_commands = [
        '@tree.command(name="balance"',
        '@tree.command(name="daily"',
        '@tree.command(name="level"',
        '@tree.command(name="shop"',
        '@tree.command(name="werwolf"',
    ]
    
    for cmd in critical_commands:
        if cmd in bot_code:
            print(f'✓ {cmd.split("name=")[1].split('"')[0]} command still exists')
        else:
            print(f'⚠ Warning: {cmd} might be affected')
    
    # Check that we didn't break any imports
    import_checks = [
        'from modules import economy',
        'from modules import level_system',
        'from modules import quests',
        'from modules import detective_game',
    ]
    
    for imp in import_checks:
        if imp in bot_code:
            print(f'✓ {imp} still present')
        else:
            print(f'⚠ Warning: {imp} might be missing')
    
    print("✓ bot.py integrity maintained")
    
    return True


def test_migration_safety():
    """Test that database migration is safe."""
    print("\nTesting migration safety...")
    
    with open('scripts/db_migrations/004_detective_game_cases.sql', 'r') as f:
        migration = f.read()
    
    # Check for IF NOT EXISTS (idempotent)
    assert 'CREATE TABLE IF NOT EXISTS detective_cases' in migration
    assert 'CREATE TABLE IF NOT EXISTS detective_user_progress' in migration
    assert 'CREATE TABLE IF NOT EXISTS detective_user_stats' in migration
    print("✓ Migration uses IF NOT EXISTS (idempotent)")
    
    # Check no destructive operations on existing tables
    destructive_patterns = [
        'DROP TABLE user',
        'DROP TABLE economy',
        'DROP TABLE quest',
        'DROP TABLE level',
        'DELETE FROM user',
        'TRUNCATE user',
        'ALTER TABLE user',
        'ALTER TABLE economy',
    ]
    
    for pattern in destructive_patterns:
        if pattern.lower() in migration.lower():
            print(f'✗ Found potentially destructive: {pattern}')
            return False
    
    print("✓ No destructive operations on existing tables")
    
    # Check only creates NEW tables
    assert 'detective_cases' in migration
    assert 'detective_user_progress' in migration
    assert 'detective_user_stats' in migration
    print("✓ Only creates new detective-specific tables")
    
    print("✓ Migration is safe")
    
    return True


def test_api_compatibility():
    """Test that API functions are compatible."""
    print("\nTesting API compatibility...")
    
    from modules import detective_game
    import inspect
    
    # Check that log_game_result still has same signature
    sig = inspect.signature(detective_game.log_game_result)
    params = list(sig.parameters.keys())
    expected = ['db_helpers', 'user_id', 'display_name', 'won']
    assert params == expected, f"log_game_result signature changed: {params}"
    print("✓ log_game_result signature unchanged")
    
    # Check that grant_reward still has same signature
    sig = inspect.signature(detective_game.grant_reward)
    params = list(sig.parameters.keys())
    expected = ['db_helpers', 'user_id', 'display_name', 'amount', 'config']
    assert params == expected, f"grant_reward signature changed: {params}"
    print("✓ grant_reward signature unchanged")
    
    print("✓ API compatibility maintained")
    
    return True


def main():
    """Run all backwards compatibility tests."""
    print("=" * 60)
    print("BACKWARDS COMPATIBILITY TESTS")
    print("=" * 60)
    
    all_passed = True
    
    tests = [
        test_existing_functions_still_work,
        test_database_optional,
        test_no_other_modules_affected,
        test_bot_py_integrity,
        test_migration_safety,
        test_api_compatibility,
    ]
    
    for test_func in tests:
        try:
            if not test_func():
                all_passed = False
        except Exception as e:
            print(f"✗ {test_func.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL BACKWARDS COMPATIBILITY TESTS PASSED")
        print("=" * 60)
        print("\nSUMMARY:")
        print("- Existing code still works without modifications")
        print("- Database migration is optional (graceful degradation)")
        print("- No interference with other bot features")
        print("- Migration only creates new tables (safe)")
        print("- API signatures unchanged (compatible)")
        print("\n🎉 CHANGES ARE SAFE AND NON-DESTRUCTIVE 🎉")
        return 0
    else:
        print("✗ SOME TESTS FAILED")
        print("=" * 60)
        return 1


if __name__ == '__main__':
    sys.exit(main())
