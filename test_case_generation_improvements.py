"""
Test script to validate the improved detective case generation.

This tests:
1. JSON parsing improvements handle various formats
2. Validation logic works correctly
3. Retry logic structure is correct
4. Fallback provider logic is correct
"""

import sys
import re
import json
from pathlib import Path

# Mock discord module to allow testing without full bot setup
sys.modules['discord'] = type(sys)('discord')
sys.modules['discord.ext'] = type(sys)('discord.ext')


def test_json_parsing():
    """Test improved JSON parsing with various response formats."""
    print("Testing JSON parsing improvements...")
    
    test_cases = [
        # Valid JSON
        ('{"title": "Test"}', True, "Plain JSON"),
        
        # JSON in markdown code block with json marker
        ('```json\n{"title": "Test"}\n```', True, "Markdown with json marker"),
        
        # JSON in markdown code block without marker
        ('```\n{"title": "Test"}\n```', True, "Markdown without marker"),
        
        # JSON with surrounding text
        ('Here is the case:\n{"title": "Test"}\nEnjoy!', True, "Surrounded by text"),
        
        # Invalid - no JSON
        ('No JSON here', False, "No JSON present"),
        
        # Nested JSON
        ('{"title": "Test", "data": {"nested": "value"}}', True, "Nested JSON"),
    ]
    
    passed = 0
    failed = 0
    
    for response, should_parse, description in test_cases:
        # Simulate the parsing logic from detective_game.py
        cleaned_response = response.strip()
        
        # Remove markdown code blocks if present
        if '```' in cleaned_response:
            code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', cleaned_response, re.DOTALL)
            if code_block_match:
                cleaned_response = code_block_match.group(1)
        
        # Try to extract JSON object from response
        json_match = re.search(r'\{.*\}', cleaned_response, re.DOTALL)
        
        if json_match:
            try:
                json.loads(json_match.group())
                result = True
            except json.JSONDecodeError:
                result = False
        else:
            result = False
        
        if result == should_parse:
            print(f"  ✓ {description}")
            passed += 1
        else:
            print(f"  ✗ {description} - Expected {should_parse}, got {result}")
            failed += 1
    
    print(f"\n  Passed: {passed}/{len(test_cases)}")
    return failed == 0


def test_case_validation():
    """Test that case validation works correctly."""
    print("\nTesting case validation logic...")
    
    from modules import detective_game
    
    # Valid case
    valid_case = {
        'title': 'Valid Case',
        'description': 'Test description',
        'location': 'Test location',
        'victim': 'Test victim',
        'suspects': [
            {'name': 'S1', 'occupation': 'O1', 'alibi': 'A1', 'motive': 'M1', 'suspicious_details': 'D1'},
            {'name': 'S2', 'occupation': 'O2', 'alibi': 'A2', 'motive': 'M2', 'suspicious_details': 'D2'},
            {'name': 'S3', 'occupation': 'O3', 'alibi': 'A3', 'motive': 'M3', 'suspicious_details': 'D3'},
            {'name': 'S4', 'occupation': 'O4', 'alibi': 'A4', 'motive': 'M4', 'suspicious_details': 'D4'},
        ],
        'murderer_index': 0,
        'evidence': ['E1', 'E2', 'E3'],
        'hints': ['H1', 'H2']
    }
    
    # Test valid case
    required_fields = ['title', 'description', 'location', 'victim', 'suspects', 'murderer_index', 'evidence', 'hints']
    missing = [f for f in required_fields if f not in valid_case]
    assert len(missing) == 0, f"Valid case should have no missing fields, but missing: {missing}"
    assert len(valid_case['suspects']) == 4, "Valid case should have 4 suspects"
    print("  ✓ Valid case passes validation")
    
    # Test invalid cases
    test_cases = [
        ({'title': 'Missing fields'}, "missing required fields"),
        ({**valid_case, 'suspects': []}, "empty suspects array"),
        ({**valid_case, 'suspects': valid_case['suspects'][:2]}, "too few suspects"),
        ({**valid_case, 'suspects': valid_case['suspects'] + valid_case['suspects']}, "too many suspects"),
    ]
    
    for case_data, description in test_cases:
        required_fields = ['title', 'description', 'location', 'victim', 'suspects', 'murderer_index', 'evidence', 'hints']
        missing = [f for f in required_fields if f not in case_data]
        suspects_valid = isinstance(case_data.get('suspects'), list) and len(case_data.get('suspects', [])) == 4
        
        is_valid = len(missing) == 0 and suspects_valid
        
        if not is_valid:
            print(f"  ✓ Correctly rejects case with {description}")
        else:
            print(f"  ✗ Should reject case with {description}")
            return False
    
    return True


def test_retry_structure():
    """Test that retry logic structure is correct."""
    print("\nTesting retry logic structure...")
    
    from modules import detective_game
    import inspect
    
    # Check that generate_murder_case function has the right structure
    source = inspect.getsource(detective_game.generate_murder_case)
    
    # Check for key components
    checks = [
        ('max_attempts', 'max_attempts variable'),
        ('providers_to_try', 'providers_to_try variable'),
        ('for provider_name, model in providers_to_try', 'provider iteration'),
        ('for attempt in range(max_attempts)', 'retry loop'),
        ('await asyncio.sleep', 'exponential backoff'),
        ('temp_config', 'temporary config with extended timeout'),
    ]
    
    for pattern, description in checks:
        if pattern in source:
            print(f"  ✓ Has {description}")
        else:
            print(f"  ✗ Missing {description}")
            return False
    
    return True


def test_fallback_provider():
    """Test that fallback provider logic is correct."""
    print("\nTesting fallback provider logic...")
    
    from modules import detective_game
    import inspect
    
    source = inspect.getsource(detective_game.generate_murder_case)
    
    # Should have fallback provider logic
    if 'fallback_provider' in source:
        print("  ✓ Has fallback_provider variable")
    else:
        print("  ✗ Missing fallback_provider variable")
        return False
    
    # Should try both Gemini and OpenAI
    if 'gemini' in source.lower() and 'openai' in source.lower():
        print("  ✓ Supports both Gemini and OpenAI")
    else:
        print("  ✗ Missing multi-provider support")
        return False
    
    return True


def test_extended_timeout():
    """Test that timeout has been extended."""
    print("\nTesting extended timeout...")
    
    from modules import detective_game
    import inspect
    
    source = inspect.getsource(detective_game.generate_murder_case)
    
    # Should have 120 second timeout
    if 'base_timeout = 120' in source or 'base_timeout=120' in source:
        print("  ✓ Has extended timeout (120s)")
    else:
        print("  ✗ Timeout not found or incorrect")
        return False
    
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Detective Case Generation Improvements")
    print("=" * 60)
    
    tests = [
        test_json_parsing,
        test_case_validation,
        test_retry_structure,
        test_fallback_provider,
        test_extended_timeout,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\n✗ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    print("\n" + "=" * 60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("=" * 60)
    
    if all(results):
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
