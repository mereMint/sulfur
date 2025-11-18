#!/usr/bin/env python3
"""
Test script to verify database null handling works correctly.
This tests that the bot can handle database connection failures gracefully.
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the db_helpers module
import modules.db_helpers as db_helpers

async def test_null_db_pool():
    """Test that functions handle null db_pool gracefully"""
    print("Testing database null handling...")
    print("=" * 60)
    
    # Ensure db_pool is None to simulate failure
    db_helpers.db_pool = None
    print(f"db_pool set to: {db_helpers.db_pool}")
    
    test_results = []
    
    # Test critical chat functions
    print("\n1. Testing save_message_to_history with null db_pool...")
    try:
        await db_helpers.save_message_to_history(12345, "user", "test message")
        print("   ✓ Function returned without crashing")
        test_results.append(("save_message_to_history", True))
    except Exception as e:
        print(f"   ✗ Function crashed: {e}")
        test_results.append(("save_message_to_history", False))
    
    print("\n2. Testing get_chat_history with null db_pool...")
    try:
        history = await db_helpers.get_chat_history(12345, 10)
        assert history == [], f"Expected empty list, got {history}"
        print(f"   ✓ Function returned empty list: {history}")
        test_results.append(("get_chat_history", True))
    except Exception as e:
        print(f"   ✗ Function crashed: {e}")
        test_results.append(("get_chat_history", False))
    
    print("\n3. Testing get_relationship_summary with null db_pool...")
    try:
        summary = await db_helpers.get_relationship_summary(12345)
        assert summary is None, f"Expected None, got {summary}"
        print(f"   ✓ Function returned None: {summary}")
        test_results.append(("get_relationship_summary", True))
    except Exception as e:
        print(f"   ✗ Function crashed: {e}")
        test_results.append(("get_relationship_summary", False))
    
    print("\n4. Testing update_relationship_summary with null db_pool...")
    try:
        await db_helpers.update_relationship_summary(12345, "test summary")
        print("   ✓ Function returned without crashing")
        test_results.append(("update_relationship_summary", True))
    except Exception as e:
        print(f"   ✗ Function crashed: {e}")
        test_results.append(("update_relationship_summary", False))
    
    print("\n5. Testing save_bulk_history with null db_pool...")
    try:
        messages = [{"role": "user", "content": "test"}]
        await db_helpers.save_bulk_history(12345, messages)
        print("   ✓ Function returned without crashing")
        test_results.append(("save_bulk_history", True))
    except Exception as e:
        print(f"   ✗ Function crashed: {e}")
        test_results.append(("save_bulk_history", False))
    
    print("\n6. Testing clear_channel_history with null db_pool...")
    try:
        deleted, error = await db_helpers.clear_channel_history(12345)
        assert deleted == 0, f"Expected 0 deleted, got {deleted}"
        assert error is not None, f"Expected error message, got None"
        print(f"   ✓ Function returned (0, error): ({deleted}, '{error}')")
        test_results.append(("clear_channel_history", True))
    except Exception as e:
        print(f"   ✗ Function crashed: {e}")
        test_results.append(("clear_channel_history", False))
    
    print("\n7. Testing get_owned_channel with null db_pool...")
    try:
        channel = await db_helpers.get_owned_channel(12345, 67890)
        assert channel is None, f"Expected None, got {channel}"
        print(f"   ✓ Function returned None: {channel}")
        test_results.append(("get_owned_channel", True))
    except Exception as e:
        print(f"   ✗ Function crashed: {e}")
        test_results.append(("get_owned_channel", False))
    
    print("\n8. Testing add_managed_channel with null db_pool...")
    try:
        await db_helpers.add_managed_channel(12345, 67890, 11111)
        print("   ✓ Function returned without crashing")
        test_results.append(("add_managed_channel", True))
    except Exception as e:
        print(f"   ✗ Function crashed: {e}")
        test_results.append(("add_managed_channel", False))
    
    print("\n9. Testing log_message_stat with null db_pool...")
    try:
        await db_helpers.log_message_stat(12345, 67890, ["emoji1"], "2024-01")
        print("   ✓ Function returned without crashing")
        test_results.append(("log_message_stat", True))
    except Exception as e:
        print(f"   ✗ Function crashed: {e}")
        test_results.append(("log_message_stat", False))
    
    print("\n10. Testing get_player_profile with null db_pool...")
    try:
        profile, error = await db_helpers.get_player_profile(12345)
        assert profile is None, f"Expected None profile, got {profile}"
        assert error is not None, f"Expected error message, got None"
        print(f"   ✓ Function returned (None, error): (None, '{error}')")
        test_results.append(("get_player_profile", True))
    except Exception as e:
        print(f"   ✗ Function crashed: {e}")
        test_results.append(("get_player_profile", False))
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    
    for func_name, result in test_results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {func_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Database null handling works correctly.")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(test_null_db_pool())
    sys.exit(exit_code)
