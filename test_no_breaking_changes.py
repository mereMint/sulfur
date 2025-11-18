"""
Comprehensive test to ensure detective game changes don't break existing functionality.
"""

import sys

# Mock discord module
sys.modules['discord'] = type(sys)('discord')
sys.modules['discord.ext'] = type(sys)('discord.ext')

from modules import detective_game


def test_no_breaking_changes():
    """Comprehensive test to ensure no breaking changes."""
    print("=" * 60)
    print("COMPREHENSIVE NO-BREAKING-CHANGES TEST")
    print("=" * 60)
    
    # Test 1: Old case data (without hints) still works
    print("\n1. Testing backward compatibility (old cases without hints)...")
    old_case = detective_game.MurderCase({
        'title': 'Old Case',
        'description': 'Old description',
        'location': 'Old location',
        'victim': 'Old victim',
        'suspects': [
            {'name': 'S1', 'occupation': 'O1', 'alibi': 'A1', 'motive': 'M1', 'suspicious_details': 'D1'},
            {'name': 'S2', 'occupation': 'O2', 'alibi': 'A2', 'motive': 'M2', 'suspicious_details': 'D2'},
            {'name': 'S3', 'occupation': 'O3', 'alibi': 'A3', 'motive': 'M3', 'suspicious_details': 'D3'},
            {'name': 'S4', 'occupation': 'O4', 'alibi': 'A4', 'motive': 'M4', 'suspicious_details': 'D4'}
        ],
        'murderer_index': 2,
        'evidence': ['E1', 'E2', 'E3']
        # No hints - testing backward compatibility
    })
    assert old_case.case_title == 'Old Case'
    assert len(old_case.suspects) == 4
    assert old_case.murderer_index == 2
    assert old_case.hints == []  # Should default to empty list
    print("   ✓ Old cases without hints work correctly")
    
    # Test 2: New case data (with hints) works
    print("\n2. Testing new functionality (cases with hints)...")
    new_case = detective_game.MurderCase({
        'title': 'New Case',
        'description': 'New description',
        'location': 'New location',
        'victim': 'New victim',
        'suspects': [
            {'name': 'S1', 'occupation': 'O1', 'alibi': 'A1', 'motive': 'M1', 'suspicious_details': 'D1'},
            {'name': 'S2', 'occupation': 'O2', 'alibi': 'A2', 'motive': 'M2', 'suspicious_details': 'D2'},
            {'name': 'S3', 'occupation': 'O3', 'alibi': 'A3', 'motive': 'M3', 'suspicious_details': 'D3'},
            {'name': 'S4', 'occupation': 'O4', 'alibi': 'A4', 'motive': 'M4', 'suspicious_details': 'D4'}
        ],
        'murderer_index': 1,
        'evidence': ['E1', 'E2'],
        'hints': ['H1', 'H2', 'H3']
    })
    assert new_case.case_title == 'New Case'
    assert len(new_case.suspects) == 4
    assert new_case.murderer_index == 1
    assert len(new_case.hints) == 3
    print("   ✓ New cases with hints work correctly")
    
    # Test 3: MurderCase methods unchanged
    print("\n3. Testing MurderCase methods...")
    assert new_case.get_suspect(0) is not None
    assert new_case.get_suspect(0)['name'] == 'S1'
    assert new_case.get_suspect(10) is None  # Out of bounds
    assert new_case.is_correct_murderer(1) == True
    assert new_case.is_correct_murderer(0) == False
    print("   ✓ get_suspect() works correctly")
    print("   ✓ is_correct_murderer() works correctly")
    
    # Test 4: Fallback case works
    print("\n4. Testing fallback case...")
    fallback = detective_game.create_fallback_case()
    assert fallback.case_title is not None
    assert len(fallback.suspects) == 4
    assert len(fallback.evidence) >= 3
    assert len(fallback.hints) >= 2
    assert 0 <= fallback.murderer_index < len(fallback.suspects)
    print("   ✓ Fallback case has all required fields")
    print("   ✓ Fallback case includes hints")
    
    # Test 5: All suspects in fallback have required fields
    print("\n5. Testing suspect data structure...")
    for i, suspect in enumerate(fallback.suspects):
        assert 'name' in suspect, f"Suspect {i} missing 'name'"
        assert 'occupation' in suspect, f"Suspect {i} missing 'occupation'"
        assert 'alibi' in suspect, f"Suspect {i} missing 'alibi'"
        assert 'motive' in suspect, f"Suspect {i} missing 'motive'"
        assert 'suspicious_details' in suspect, f"Suspect {i} missing 'suspicious_details'"
    print("   ✓ All suspects have required fields")
    
    # Test 6: Evidence structure
    print("\n6. Testing evidence structure...")
    assert isinstance(fallback.evidence, list)
    assert all(isinstance(e, str) for e in fallback.evidence)
    print("   ✓ Evidence is a list of strings")
    
    # Test 7: Hints structure
    print("\n7. Testing hints structure...")
    assert isinstance(fallback.hints, list)
    assert all(isinstance(h, str) for h in fallback.hints)
    print("   ✓ Hints is a list of strings")
    
    print("\n" + "=" * 60)
    print("✓ ALL NO-BREAKING-CHANGES TESTS PASSED")
    print("=" * 60)
    print("\nCONFIRMATION:")
    print("- Old cases (without hints) still work ✓")
    print("- New cases (with hints) work correctly ✓")
    print("- All existing methods unchanged ✓")
    print("- Fallback case includes all fields ✓")
    print("- Data structures intact ✓")
    print("\n⚠️  NO BREAKING CHANGES DETECTED ⚠️")
    return True


if __name__ == '__main__':
    try:
        test_no_breaking_changes()
        sys.exit(0)
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
