"""
Test script to validate the detective game fix.

This tests:
1. MurderCase class handles hints properly
2. Fallback case has all required fields including hints
3. The generate_murder_case function structure is correct
"""

import sys
import asyncio
from pathlib import Path

# Mock discord module to allow testing without full bot setup
sys.modules['discord'] = type(sys)('discord')
sys.modules['discord.ext'] = type(sys)('discord.ext')


def test_murder_case_with_hints():
    """Test that MurderCase class handles hints field."""
    print("Testing MurderCase class with hints...")
    
    from modules import detective_game
    
    # Create a test case with hints
    case_data = {
        'title': 'Test Case',
        'description': 'A test murder case',
        'location': 'Test Location',
        'victim': 'Test Victim',
        'suspects': [
            {
                'name': 'Suspect 1',
                'occupation': 'Job 1',
                'alibi': 'Alibi 1',
                'motive': 'Motive 1',
                'suspicious_details': 'Details 1'
            }
        ],
        'murderer_index': 0,
        'evidence': ['Evidence 1', 'Evidence 2'],
        'hints': ['Hint 1', 'Hint 2', 'Hint 3']
    }
    
    case = detective_game.MurderCase(case_data)
    
    # Verify all fields (note: description is stored as case_description)
    assert case.case_title == 'Test Case', "Title should match"
    assert case.case_description == 'A test murder case', "Description should match"
    assert len(case.suspects) == 1, "Should have 1 suspect"
    assert len(case.evidence) == 2, "Should have 2 evidence items"
    assert len(case.hints) == 3, "Should have 3 hints"
    assert case.hints[0] == 'Hint 1', "First hint should match"
    
    print("✓ MurderCase handles hints correctly")
    return True


def test_fallback_case():
    """Test that fallback case has all required fields including hints."""
    print("\nTesting fallback case...")
    
    from modules import detective_game
    
    case = detective_game.create_fallback_case()
    
    # Verify all fields exist (note: description is stored as case_description)
    assert hasattr(case, 'case_title'), "Should have case_title"
    assert hasattr(case, 'case_description'), "Should have case_description"
    assert hasattr(case, 'location'), "Should have location"
    assert hasattr(case, 'victim'), "Should have victim"
    assert hasattr(case, 'suspects'), "Should have suspects"
    assert hasattr(case, 'murderer_index'), "Should have murderer_index"
    assert hasattr(case, 'evidence'), "Should have evidence"
    assert hasattr(case, 'hints'), "Should have hints"
    
    # Verify hints content
    assert len(case.hints) > 0, "Should have at least one hint"
    assert isinstance(case.hints, list), "Hints should be a list"
    
    # Verify suspects count
    assert len(case.suspects) == 4, "Should have exactly 4 suspects"
    
    # Verify evidence count
    assert 3 <= len(case.evidence) <= 4, "Should have 3-4 evidence items"
    
    print(f"✓ Fallback case has all required fields")
    print(f"  - {len(case.suspects)} suspects")
    print(f"  - {len(case.evidence)} evidence items")
    print(f"  - {len(case.hints)} hints")
    return True


def test_api_call_structure():
    """Test that the API call structure is correct."""
    print("\nTesting API call structure...")
    
    import inspect
    from modules import detective_game
    
    # Get the source code of generate_murder_case
    source = inspect.getsource(detective_game.generate_murder_case)
    
    # Verify it's NOT calling get_game_details_from_api
    assert 'get_game_details_from_api' not in source, \
        "Should NOT use get_game_details_from_api (causes looping bug)"
    
    # Verify it IS calling get_ai_response_with_model
    assert 'get_ai_response_with_model' in source, \
        "Should use get_ai_response_with_model for single API call"
    
    # Verify it has hints in the prompt
    assert 'hints' in source, "Prompt should mention hints"
    
    print("✓ API call structure is correct")
    print("  - Uses get_ai_response_with_model (single call)")
    print("  - Does NOT use get_game_details_from_api (looping bug)")
    print("  - Includes hints in prompt")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("DETECTIVE GAME FIX - VALIDATION TESTS")
    print("=" * 60)
    
    all_passed = True
    
    try:
        test_murder_case_with_hints()
    except Exception as e:
        print(f"✗ MurderCase hints test failed: {e}")
        all_passed = False
    
    try:
        test_fallback_case()
    except Exception as e:
        print(f"✗ Fallback case test failed: {e}")
        all_passed = False
    
    try:
        test_api_call_structure()
    except Exception as e:
        print(f"✗ API call structure test failed: {e}")
        all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        print("\nSUMMARY:")
        print("- MurderCase class properly handles hints field")
        print("- Fallback case includes all required fields with hints")
        print("- API call uses get_ai_response_with_model (single call)")
        print("- Fixed the looping bug from get_game_details_from_api")
        return 0
    else:
        print("✗ SOME TESTS FAILED")
        print("=" * 60)
        return 1


if __name__ == '__main__':
    sys.exit(main())
