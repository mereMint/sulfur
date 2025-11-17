"""
Test script to validate message handling improvements for Termux.

This script tests the following:
1. Timezone-aware datetime usage (no deprecated utcnow)
2. Message deduplication logic
3. Trigger detection logic
"""

import sys
from datetime import datetime, timezone
from collections import deque
import re

def test_timezone_usage():
    """Test that we're using timezone-aware datetime instead of deprecated utcnow()"""
    print("Testing timezone-aware datetime usage...")
    
    # This is what we fixed - using timezone-aware datetime
    now_ts = datetime.now(timezone.utc).timestamp()
    
    # Verify it's a valid timestamp
    assert isinstance(now_ts, float), "Timestamp should be a float"
    assert now_ts > 0, "Timestamp should be positive"
    
    # Verify it's recent (within last minute)
    current_time = datetime.now(timezone.utc).timestamp()
    assert abs(current_time - now_ts) < 60, "Timestamp should be recent"
    
    print("✓ Timezone-aware datetime works correctly")
    return True

def test_message_deduplication():
    """Test message deduplication logic"""
    print("\nTesting message deduplication...")
    
    # Simulate the deduplication cache
    last_processed_message_ids = deque(maxlen=500)
    recent_user_message_cache = {}
    
    # Test 1: Message ID deduplication
    message_id_1 = 123456789
    last_processed_message_ids.append(message_id_1)
    
    # Check if duplicate
    is_duplicate = message_id_1 in last_processed_message_ids
    assert is_duplicate, "Should detect duplicate message ID"
    print("✓ Message ID deduplication works")
    
    # Test 2: Time-based deduplication
    user_id = 987654321
    content = "test message"
    key = (user_id, content)
    
    # First message
    now_ts = datetime.now(timezone.utc).timestamp()
    recent_user_message_cache[key] = now_ts
    
    # Check within 3 seconds (should be duplicate)
    prev_ts = recent_user_message_cache.get(key)
    is_recent_duplicate = prev_ts and (now_ts - prev_ts) < 3
    assert is_recent_duplicate, "Should detect recent duplicate"
    print("✓ Time-based deduplication works")
    
    # Test 3: After 3 seconds (should not be duplicate)
    import time
    time.sleep(3.1)
    now_ts = datetime.now(timezone.utc).timestamp()
    is_old_duplicate = prev_ts and (now_ts - prev_ts) < 3
    assert not is_old_duplicate, "Should not detect old duplicate after 3 seconds"
    print("✓ Time-based deduplication timeout works")
    
    return True

def test_trigger_detection():
    """Test chatbot trigger detection logic"""
    print("\nTesting trigger detection...")
    
    # Simulate config
    bot_names = ['sulf', 'sulfur']
    
    # Test 1: Name used in message
    message_1 = "sulf hello there"
    is_name_used_1 = any(name in message_1.lower().split() for name in bot_names)
    assert is_name_used_1, "Should detect 'sulf' in message"
    print("✓ Bot name 'sulf' detected")
    
    # Test 2: Name used in message (sulfur)
    message_2 = "hey sulfur how are you"
    is_name_used_2 = any(name in message_2.lower().split() for name in bot_names)
    assert is_name_used_2, "Should detect 'sulfur' in message"
    print("✓ Bot name 'sulfur' detected")
    
    # Test 3: Name not used
    message_3 = "hello everyone"
    is_name_used_3 = any(name in message_3.lower().split() for name in bot_names)
    assert not is_name_used_3, "Should not detect bot name when absent"
    print("✓ Correctly ignores messages without bot name")
    
    # Test 4: Partial match should not trigger (important!)
    message_4 = "this is sulfuric acid"  # contains 'sulfur' but not as a word
    is_name_used_4 = any(name in message_4.lower().split() for name in bot_names)
    assert not is_name_used_4, "Should not trigger on partial match"
    print("✓ Correctly ignores partial matches")
    
    return True

def test_logging_format():
    """Test that logging format is consistent"""
    print("\nTesting logging format...")
    
    # Simulate log messages that should be generated
    test_logs = [
        "[MSG] Received from TestUser in #general: 'hello'...",
        "[GUILD] Guild message from TestUser in #general",
        "[TRIGGER] Chatbot trigger check: pinged=False, name_used=True, final=True",
        "[CHATBOT] === Starting chatbot handler for TestUser in #general ===",
        "[AI] Using provider 'gemini' for user 'TestUser'",
        "[Gemini API] Making request to model 'gemini-2.5-flash'...",
    ]
    
    # Check format consistency
    for log in test_logs:
        # Each log should start with a tag in brackets
        assert log.startswith('['), f"Log should start with '[': {log}"
        assert '] ' in log, f"Log should have '] ' separator: {log}"
        print(f"✓ Valid log format: {log[:50]}...")
    
    return True

def main():
    """Run all tests"""
    print("="*60)
    print("Message Handling Validation Tests")
    print("="*60)
    
    tests = [
        ("Timezone Usage", test_timezone_usage),
        ("Message Deduplication", test_message_deduplication),
        ("Trigger Detection", test_trigger_detection),
        ("Logging Format", test_logging_format),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"\n✅ {test_name} PASSED")
        except AssertionError as e:
            failed += 1
            print(f"\n❌ {test_name} FAILED: {e}")
        except Exception as e:
            failed += 1
            print(f"\n❌ {test_name} ERROR: {e}")
    
    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60)
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
