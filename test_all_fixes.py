#!/usr/bin/env python3
"""
Test script to verify all fixes are working correctly.
Tests:
1. update_user_presence signature compatibility
2. Detective game graceful handling of missing case_hash
3. TTS configuration values
"""

import sys
import json
import inspect
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_update_user_presence_signature():
    """Test that update_user_presence has the correct signature."""
    print("=" * 60)
    print("Test 1: update_user_presence signature")
    print("=" * 60)
    
    try:
        from modules import db_helpers
        
        # Get the function signature
        sig = inspect.signature(db_helpers.update_user_presence)
        params = list(sig.parameters.keys())
        
        expected_params = ['user_id', 'display_name', 'status', 'activity_name']
        
        print(f"Expected parameters: {expected_params}")
        print(f"Actual parameters: {params}")
        
        if params == expected_params:
            print("✓ PASS: update_user_presence has correct signature")
            return True
        else:
            print("✗ FAIL: Parameter mismatch")
            return False
            
    except Exception as e:
        print(f"✗ FAIL: {e}")
        return False


def test_detective_game_imports():
    """Test that detective_game imports mysql.connector correctly."""
    print("\n" + "=" * 60)
    print("Test 2: Detective game mysql.connector import")
    print("=" * 60)
    
    try:
        from modules import detective_game
        
        # Check if mysql.connector is imported
        if hasattr(detective_game, 'mysql'):
            print("✓ PASS: mysql.connector imported in detective_game")
            return True
        else:
            print("✗ FAIL: mysql.connector not found in detective_game")
            return False
            
    except Exception as e:
        print(f"✗ FAIL: {e}")
        return False


def test_detective_functions_exist():
    """Test that detective game functions handle errors gracefully."""
    print("\n" + "=" * 60)
    print("Test 3: Detective game error handling functions")
    print("=" * 60)
    
    try:
        from modules import detective_game
        
        # Check functions exist
        functions = [
            'check_case_exists',
            'save_case_to_db',
            'get_existing_case_by_hash',
            'compute_case_hash'
        ]
        
        all_exist = True
        for func_name in functions:
            if hasattr(detective_game, func_name):
                print(f"  ✓ {func_name} exists")
            else:
                print(f"  ✗ {func_name} missing")
                all_exist = False
        
        if all_exist:
            print("✓ PASS: All detective game functions exist")
            return True
        else:
            print("✗ FAIL: Some functions missing")
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
        # Read the api_helpers.py file
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
        
        if all_found:
            print("✓ PASS: TTS prompt is in German")
            return True
        else:
            print("✗ FAIL: TTS prompt missing German keywords")
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
        ]
        
        all_exist = True
        for file_path in files:
            full_path = base_path / file_path
            if full_path.exists():
                print(f"  ✓ {file_path} exists")
            else:
                print(f"  ✗ {file_path} missing")
                all_exist = False
        
        if all_exist:
            print("✓ PASS: All migration files exist")
            return True
        else:
            print("✗ FAIL: Some migration files missing")
            return False
            
    except Exception as e:
        print(f"✗ FAIL: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("SULFUR BOT FIX VERIFICATION TESTS")
    print("=" * 60)
    
    tests = [
        test_update_user_presence_signature,
        test_detective_game_imports,
        test_detective_functions_exist,
        test_tts_configuration,
        test_tts_prompt_language,
        test_migration_files_exist,
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"\n✗ Test failed with exception: {e}")
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
        return 0
    else:
        print(f"\n✗ {total - passed} TEST(S) FAILED")
        return 1


if __name__ == '__main__':
    sys.exit(main())
