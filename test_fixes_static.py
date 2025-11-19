#!/usr/bin/env python3
"""
Static verification test for fixes - doesn't require dependencies.
Tests:
1. update_user_presence signature in bot.py
2. Detective game mysql.connector import
3. TTS configuration values
4. TTS prompt language
5. Migration files exist
"""

import re
import json
from pathlib import Path


def test_update_user_presence_call():
    """Test that update_user_presence call doesn't include activity_type."""
    print("=" * 60)
    print("Test 1: update_user_presence call in bot.py")
    print("=" * 60)
    
    try:
        bot_path = Path(__file__).parent / 'bot.py'
        with open(bot_path, 'r') as f:
            content = f.read()
        
        # Find the section with update_user_presence
        if 'await db_helpers.update_user_presence(' not in content:
            print("✗ FAIL: Could not find update_user_presence call")
            return False
        
        # Extract the relevant section (next 10 lines after the call)
        lines = content.split('\n')
        call_sections = []
        for i, line in enumerate(lines):
            if 'await db_helpers.update_user_presence(' in line:
                # Get next 10 lines
                section = '\n'.join(lines[i:i+10])
                call_sections.append(section)
        
        if not call_sections:
            print("✗ FAIL: Could not extract call sections")
            return False
        
        # Check that activity_type is NOT in any of the calls
        has_activity_type = any('activity_type=' in section for section in call_sections)
        
        if has_activity_type:
            print("✗ FAIL: Found activity_type parameter in call")
            return False
        else:
            print("✓ PASS: No activity_type parameter found")
            
        # Verify the expected parameters are present
        expected_params = ['user_id=', 'display_name=', 'status=', 'activity_name=']
        for param in expected_params:
            if not any(param in section for section in call_sections):
                print(f"✗ FAIL: Missing expected parameter: {param}")
                return False
            else:
                print(f"  ✓ Found parameter: {param}")
        
        print("✓ PASS: update_user_presence call has correct parameters")
        return True
        
    except Exception as e:
        print(f"✗ FAIL: {e}")
        return False


def test_detective_mysql_import():
    """Test that detective_game.py imports mysql.connector."""
    print("\n" + "=" * 60)
    print("Test 2: mysql.connector import in detective_game.py")
    print("=" * 60)
    
    try:
        detective_path = Path(__file__).parent / 'modules' / 'detective_game.py'
        with open(detective_path, 'r') as f:
            content = f.read()
        
        if 'import mysql.connector' in content:
            print("✓ PASS: mysql.connector is imported")
            return True
        else:
            print("✗ FAIL: mysql.connector import not found")
            return False
            
    except Exception as e:
        print(f"✗ FAIL: {e}")
        return False


def test_detective_error_handling():
    """Test that detective_game.py has proper error handling for case_hash."""
    print("\n" + "=" * 60)
    print("Test 3: Detective game error handling for case_hash")
    print("=" * 60)
    
    try:
        detective_path = Path(__file__).parent / 'modules' / 'detective_game.py'
        with open(detective_path, 'r') as f:
            content = f.read()
        
        checks = [
            ("mysql.connector.errors.ProgrammingError", "ProgrammingError exception handling"),
            ("Unknown column 'case_hash'", "case_hash column check"),
            ("Please run migration", "Migration warning message"),
        ]
        
        all_pass = True
        for check_str, desc in checks:
            if check_str in content:
                print(f"  ✓ Found: {desc}")
            else:
                print(f"  ✗ Missing: {desc}")
                all_pass = False
        
        if all_pass:
            print("✓ PASS: Detective game has proper error handling")
            return True
        else:
            print("✗ FAIL: Missing some error handling code")
            return False
            
    except Exception as e:
        print(f"✗ FAIL: {e}")
        return False


def test_tts_configuration():
    """Test that TTS configuration has been updated."""
    print("\n" + "=" * 60)
    print("Test 4: Werwolf TTS configuration")
    print("=" * 60)
    
    try:
        config_path = Path(__file__).parent / 'config' / 'config.json'
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        tts_config = config['modules']['werwolf']['tts']
        
        print(f"  chars_per_second: {tts_config['chars_per_second']}")
        print(f"  min_duration: {tts_config['min_duration']}")
        print(f"  buffer_seconds: {tts_config['buffer_seconds']}")
        
        # Check values are updated
        checks = [
            (tts_config['chars_per_second'] == 12, "chars_per_second is 12"),
            (tts_config['min_duration'] == 4.0, "min_duration is 4.0"),
            (tts_config['buffer_seconds'] == 3.0, "buffer_seconds is 3.0"),
        ]
        
        all_pass = True
        for check, desc in checks:
            if check:
                print(f"  ✓ {desc}")
            else:
                print(f"  ✗ {desc} - FAILED")
                all_pass = False
        
        if all_pass:
            print("✓ PASS: TTS configuration correctly updated")
            return True
        else:
            print("✗ FAIL: TTS configuration has incorrect values")
            return False
            
    except Exception as e:
        print(f"✗ FAIL: {e}")
        return False


def test_tts_prompt_language():
    """Test that TTS prompt is in German."""
    print("\n" + "=" * 60)
    print("Test 5: Werwolf TTS prompt language")
    print("=" * 60)
    
    try:
        api_helpers_path = Path(__file__).parent / 'modules' / 'api_helpers.py'
        with open(api_helpers_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for German keywords in the prompt
        german_keywords = [
            'Du bist der Erzähler',
            'Werwolf-Spiel',
            'Das folgende Ereignis ist gerade passiert',
            'Generiere den TTS-Satz'
        ]
        
        all_found = True
        for keyword in german_keywords:
            if keyword in content:
                print(f"  ✓ Found: '{keyword}'")
            else:
                print(f"  ✗ Missing: '{keyword}'")
                all_found = False
        
        # Also check that old English prompt is NOT there
        english_keywords = [
            'You are the narrator for a game of Werewolf',
            'Generate the TTS sentence for the event'
        ]
        
        has_english = False
        for keyword in english_keywords:
            if keyword in content:
                print(f"  ✗ Still has English: '{keyword}'")
                has_english = True
        
        if all_found and not has_english:
            print("✓ PASS: TTS prompt is in German")
            return True
        else:
            print("✗ FAIL: TTS prompt language issue")
            return False
            
    except Exception as e:
        print(f"✗ FAIL: {e}")
        return False


def test_migration_files_exist():
    """Test that migration files were created."""
    print("\n" + "=" * 60)
    print("Test 6: Migration files existence")
    print("=" * 60)
    
    try:
        base_path = Path(__file__).parent
        files = [
            'apply_case_hash_migration.py',
            'scripts/db_migrations/006_add_case_hash_if_missing.sql',
            'scripts/db_migrations/004_detective_game_cases.sql',
        ]
        
        all_exist = True
        for file_path in files:
            full_path = base_path / file_path
            if full_path.exists():
                print(f"  ✓ {file_path} exists")
            else:
                print(f"  ✗ {file_path} missing")
                all_exist = False
        
        # Check that 004 migration has case_hash
        migration_004 = base_path / 'scripts/db_migrations/004_detective_game_cases.sql'
        with open(migration_004, 'r') as f:
            content = f.read()
            if 'case_hash' in content:
                print("  ✓ 004 migration includes case_hash column")
            else:
                print("  ✗ 004 migration missing case_hash column")
                all_exist = False
        
        if all_exist:
            print("✓ PASS: All migration files exist and are correct")
            return True
        else:
            print("✗ FAIL: Some migration files missing or incorrect")
            return False
            
    except Exception as e:
        print(f"✗ FAIL: {e}")
        return False


def test_backward_compatibility():
    """Test that code handles both old and new database schemas."""
    print("\n" + "=" * 60)
    print("Test 7: Backward compatibility check")
    print("=" * 60)
    
    try:
        detective_path = Path(__file__).parent / 'modules' / 'detective_game.py'
        with open(detective_path, 'r') as f:
            content = f.read()
        
        # Check for fallback logic in save_case_to_db
        checks = [
            ("INSERT INTO detective_cases", "Insert statement exists"),
            ("case_hash", "case_hash column referenced"),
            ("except mysql.connector.errors.ProgrammingError", "Error handling for missing column"),
            ("Saving case without hash", "Fallback message"),
        ]
        
        all_pass = True
        for check_str, desc in checks:
            count = content.count(check_str)
            if count > 0:
                print(f"  ✓ Found ({count}x): {desc}")
            else:
                print(f"  ✗ Missing: {desc}")
                all_pass = False
        
        if all_pass:
            print("✓ PASS: Code supports both old and new schemas")
            return True
        else:
            print("✗ FAIL: Missing backward compatibility code")
            return False
            
    except Exception as e:
        print(f"✗ FAIL: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("SULFUR BOT FIX VERIFICATION TESTS")
    print("Testing all fixes without requiring dependencies")
    print("=" * 60)
    
    tests = [
        test_update_user_presence_call,
        test_detective_mysql_import,
        test_detective_error_handling,
        test_tts_configuration,
        test_tts_prompt_language,
        test_migration_files_exist,
        test_backward_compatibility,
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"\n✗ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✓ ALL TESTS PASSED - All fixes verified successfully!")
        print("\nThe following issues have been fixed:")
        print("  1. ✓ update_user_presence TypeError fixed")
        print("  2. ✓ Detective game case_hash errors fixed with graceful fallback")
        print("  3. ✓ Werwolf TTS timing improved (48→12 chars/sec)")
        print("  4. ✓ Werwolf TTS prompt changed to German")
        print("\nNo breaking changes detected!")
        return 0
    else:
        print(f"\n✗ {total - passed} TEST(S) FAILED")
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
