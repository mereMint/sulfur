"""
Test that detective game fallback cases rotate and don't show the same case repeatedly.
"""

import sys
from pathlib import Path

# Mock discord module to allow testing without full bot setup
sys.modules['discord'] = type(sys)('discord')
sys.modules['discord.ext'] = type(sys)('discord.ext')

from modules import detective_game


def test_fallback_rotation():
    """Test that fallback cases rotate and aren't always the same."""
    print("Testing fallback case rotation...")
    
    # Generate 20 fallback cases
    cases = []
    titles = set()
    
    for i in range(20):
        case = detective_game.create_fallback_case()
        cases.append(case)
        titles.add(case.case_title)
    
    print(f"\nGenerated {len(cases)} fallback cases")
    print(f"Unique titles: {len(titles)}")
    print("\nTitles seen:")
    for title in sorted(titles):
        print(f"  - {title}")
    
    # We should see at least 3 different titles in 20 attempts
    assert len(titles) >= 3, f"Expected at least 3 unique titles, got {len(titles)}"
    
    # Verify that the old problematic case title might appear, but not exclusively
    old_case_title = "Der Fall des vergifteten Geschäftsmanns"
    
    # Count how many times each title appears
    title_counts = {}
    for case in cases:
        title_counts[case.case_title] = title_counts.get(case.case_title, 0) + 1
    
    print("\nTitle distribution:")
    for title, count in sorted(title_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(cases)) * 100
        print(f"  {title}: {count} times ({percentage:.1f}%)")
    
    # No single case should dominate (appear more than 60% of the time)
    for title, count in title_counts.items():
        percentage = (count / len(cases)) * 100
        assert percentage < 60, f"Case '{title}' appears too often ({percentage:.1f}%)"
    
    print("\n✓ Fallback cases rotate properly")
    print(f"✓ No single case dominates (all under 60%)")
    return True


def test_case_uniqueness():
    """Test that each fallback case has unique characteristics."""
    print("\nTesting case uniqueness...")
    
    # Generate all fallback cases
    cases_seen = set()
    unique_cases = []
    
    # Try to get all unique fallback cases (should be 5)
    for _ in range(50):
        case = detective_game.create_fallback_case()
        case_hash = detective_game.compute_case_hash({
            'title': case.case_title,
            'victim': case.victim,
            'murderer_index': case.murderer_index,
            'suspects': case.suspects
        })
        
        if case_hash not in cases_seen:
            cases_seen.add(case_hash)
            unique_cases.append(case)
    
    print(f"Found {len(unique_cases)} unique fallback cases")
    
    # Should have at least 4 unique fallback cases
    assert len(unique_cases) >= 4, f"Expected at least 4 unique cases, got {len(unique_cases)}"
    
    # Verify each case has different details
    for i, case in enumerate(unique_cases):
        print(f"\nCase {i+1}: {case.case_title}")
        print(f"  Victim: {case.victim}")
        print(f"  Location: {case.location}")
        print(f"  Murderer: {case.suspects[case.murderer_index]['name']}")
        print(f"  Suspects: {len(case.suspects)}")
        print(f"  Evidence: {len(case.evidence)}")
        print(f"  Hints: {len(case.hints)}")
    
    print("\n✓ Each fallback case has unique characteristics")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("DETECTIVE GAME ROTATION TESTS")
    print("=" * 60)
    
    all_passed = True
    
    try:
        test_fallback_rotation()
    except Exception as e:
        print(f"✗ Fallback rotation test failed: {e}")
        all_passed = False
    
    try:
        test_case_uniqueness()
    except Exception as e:
        print(f"✗ Case uniqueness test failed: {e}")
        all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL ROTATION TESTS PASSED")
        print("=" * 60)
        print("\nSUMMARY:")
        print("- Fallback cases rotate properly")
        print("- Multiple unique cases available")
        print("- No single case dominates")
        print("- Users will see variety even if AI generation fails")
        return 0
    else:
        print("✗ SOME TESTS FAILED")
        print("=" * 60)
        return 1


if __name__ == '__main__':
    sys.exit(main())
