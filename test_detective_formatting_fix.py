#!/usr/bin/env python3
"""
Test suite for detective AI formatting fixes and puzzle enhancements.
Tests the new clean_ai_response function and expanded cipher variety.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.detective_game import (
    clean_ai_response,
    caesar_cipher,
    reverse_cipher,
    atbash_cipher,
    rot13_cipher,
    morse_code_cipher,
    binary_cipher,
    keyword_cipher,
    create_puzzle_hint
)


def test_clean_ai_response():
    """Test that clean_ai_response removes unwanted intro phrases."""
    print("Testing clean_ai_response function...")
    
    # Test case 1: Remove "Hier ist"
    input1 = "Hier ist: Der Beweis liegt im Detail"
    expected1 = "Der Beweis liegt im Detail"
    result1 = clean_ai_response(input1)
    assert result1 == expected1, f"Expected '{expected1}', got '{result1}'"
    print("✓ Test 1 passed: Removed 'Hier ist'")
    
    # Test case 2: Remove "Das sind"
    input2 = "Das sind die Hinweise: Wichtiger Beweis"
    expected2 = "Wichtiger Beweis"
    result2 = clean_ai_response(input2)
    assert result2 == expected2, f"Expected '{expected2}', got '{result2}'"
    print("✓ Test 2 passed: Removed 'Das sind'")
    
    # Test case 3: Remove "Hier sind ein paar Beispiele"
    input3 = "Hier sind ein paar Beispiele: Beweis 1\nBeweis 2"
    result3 = clean_ai_response(input3)
    assert not result3.startswith("Hier sind"), f"Failed to remove intro: '{result3}'"
    print("✓ Test 3 passed: Removed 'Hier sind ein paar Beispiele'")
    
    # Test case 4: Fix missing space after colon (formatting error)
    input4 = "Opfer:Hans Müller"
    expected4 = "Opfer: Hans Müller"
    result4 = clean_ai_response(input4)
    assert result4 == expected4, f"Expected '{expected4}', got '{result4}'"
    print("✓ Test 4 passed: Fixed missing space after colon")
    
    # Test case 5: No modification needed
    input5 = "Ein sauberer Text ohne Intro"
    expected5 = "Ein sauberer Text ohne Intro"
    result5 = clean_ai_response(input5)
    assert result5 == expected5, f"Expected '{expected5}', got '{result5}'"
    print("✓ Test 5 passed: Clean text unchanged")
    
    # Test case 6: Complex case with multiple issues
    input6 = "Hier sind die Beweise: Opfer:Herr SchwarzTodesart:Vergiftung"
    result6 = clean_ai_response(input6)
    assert "Hier sind" not in result6, f"Failed to remove 'Hier sind': '{result6}'"
    assert "Opfer: " in result6, f"Failed to fix 'Opfer:': '{result6}'"
    print(f"✓ Test 6 passed: Complex cleanup worked: '{result6}'")
    
    print("All clean_ai_response tests passed! ✓\n")


def test_cipher_variety():
    """Test that all cipher types work correctly."""
    print("Testing cipher variety...")
    
    test_text = "GEHEIMNIS"
    
    # Test Caesar cipher
    caesar_result = caesar_cipher(test_text, 3)
    assert caesar_result != test_text, "Caesar cipher should change the text"
    print(f"✓ Caesar cipher: {test_text} -> {caesar_result}")
    
    # Test ROT13 cipher
    rot13_result = rot13_cipher(test_text)
    assert rot13_result != test_text, "ROT13 should change the text"
    print(f"✓ ROT13 cipher: {test_text} -> {rot13_result}")
    
    # Test reverse cipher
    reverse_result = reverse_cipher(test_text)
    assert reverse_result == test_text[::-1], "Reverse cipher should reverse the text"
    print(f"✓ Reverse cipher: {test_text} -> {reverse_result}")
    
    # Test Atbash cipher
    atbash_result = atbash_cipher(test_text)
    assert atbash_result != test_text, "Atbash should change the text"
    print(f"✓ Atbash cipher: {test_text} -> {atbash_result}")
    
    # Test Morse code cipher
    morse_result = morse_code_cipher(test_text)
    assert "." in morse_result or "-" in morse_result, "Morse should contain dots or dashes"
    print(f"✓ Morse cipher: {test_text} -> {morse_result[:50]}...")
    
    # Test Binary cipher
    binary_result = binary_cipher(test_text)
    assert "0" in binary_result and "1" in binary_result, "Binary should contain 0s and 1s"
    print(f"✓ Binary cipher: {test_text} -> {binary_result[:50]}...")
    
    # Test Keyword cipher
    keyword_result = keyword_cipher(test_text, "SCHLUESSEL")
    assert keyword_result != test_text, "Keyword cipher should change the text"
    print(f"✓ Keyword cipher: {test_text} -> {keyword_result}")
    
    print("All cipher tests passed! ✓\n")


def test_puzzle_hint_variety():
    """Test that create_puzzle_hint uses varied ciphers."""
    print("Testing puzzle hint variety...")
    
    test_hint = "Der Täter war im Büro"
    
    # Test difficulty 1 (no encryption)
    puzzle1 = create_puzzle_hint(test_hint, 1)
    assert puzzle1['type'] == 'plaintext', "Difficulty 1 should use plaintext"
    print("✓ Difficulty 1: Uses plaintext (no cipher)")
    
    # Test difficulty 2 (basic ciphers)
    ciphers_used_d2 = set()
    for _ in range(20):  # Generate multiple to see variety
        puzzle2 = create_puzzle_hint(test_hint, 2)
        if puzzle2['type'] == 'cipher':
            ciphers_used_d2.add(puzzle2['cipher'])
    assert len(ciphers_used_d2) > 1, f"Difficulty 2 should use multiple cipher types, got: {ciphers_used_d2}"
    print(f"✓ Difficulty 2: Uses {len(ciphers_used_d2)} different cipher types: {ciphers_used_d2}")
    
    # Test difficulty 3 (more ciphers)
    ciphers_used_d3 = set()
    for _ in range(30):
        puzzle3 = create_puzzle_hint(test_hint, 3)
        if puzzle3['type'] == 'cipher':
            ciphers_used_d3.add(puzzle3['cipher'])
    assert len(ciphers_used_d3) >= 3, f"Difficulty 3 should use at least 3 cipher types, got: {ciphers_used_d3}"
    print(f"✓ Difficulty 3: Uses {len(ciphers_used_d3)} different cipher types: {ciphers_used_d3}")
    
    # Test difficulty 4 (all ciphers including complex ones)
    ciphers_used_d4 = set()
    for _ in range(50):
        puzzle4 = create_puzzle_hint(test_hint, 4)
        if puzzle4['type'] == 'cipher':
            ciphers_used_d4.add(puzzle4['cipher'])
    assert len(ciphers_used_d4) >= 4, f"Difficulty 4 should use at least 4 cipher types, got: {ciphers_used_d4}"
    print(f"✓ Difficulty 4: Uses {len(ciphers_used_d4)} different cipher types: {ciphers_used_d4}")
    
    # Check that we're not always using Caesar
    assert 'rot13' in ciphers_used_d4 or 'morse' in ciphers_used_d4 or 'binary' in ciphers_used_d4, \
        "Should include advanced ciphers at difficulty 4"
    print("✓ Advanced ciphers (ROT13, Morse, Binary, Keyword) are being used")
    
    print("All puzzle variety tests passed! ✓\n")


def test_formatting_fix_patterns():
    """Test specific formatting error patterns from the issue."""
    print("Testing specific formatting error patterns...")
    
    # Pattern 1: "Opfer: Herr SchwarzTodesart:"
    test1 = "Opfer:Herr SchwarzTodesart:Vergiftung"
    result1 = clean_ai_response(test1)
    # Should add space after colons before capital letters
    assert "Opfer: " in result1, f"Should fix 'Opfer:' -> 'Opfer: ', got: '{result1}'"
    print(f"✓ Fixed 'Opfer:XYZ' pattern: '{test1}' -> '{result1}'")
    
    # Pattern 2: Missing newlines between fields
    test2 = "Name:Hans MüllerAlter:45Beruf:Geschäftsmann"
    result2 = clean_ai_response(test2)
    # Should have better separation
    assert result2 != test2, f"Should improve formatting, got: '{result2}'"
    print(f"✓ Improved field separation: '{test2}' -> '{result2}'")
    
    # Pattern 3: "Das sind ein paar Beispiele..."
    test3 = "Das sind ein paar Beispiele: Beweis 1\nBeweis 2"
    result3 = clean_ai_response(test3)
    assert not result3.startswith("Das sind"), f"Should remove intro: '{result3}'"
    print(f"✓ Removed 'Das sind ein paar Beispiele': '{test3[:30]}...' -> '{result3[:30]}...'")
    
    print("All formatting fix pattern tests passed! ✓\n")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Detective AI Formatting and Puzzle Enhancement Tests")
    print("=" * 60 + "\n")
    
    try:
        test_clean_ai_response()
        test_cipher_variety()
        test_puzzle_hint_variety()
        test_formatting_fix_patterns()
        
        print("=" * 60)
        print("ALL TESTS PASSED! ✓✓✓")
        print("=" * 60)
        print("\nSummary:")
        print("✓ AI response cleanup working correctly")
        print("✓ All 7 cipher types functioning")
        print("✓ Puzzle variety significantly improved")
        print("✓ Formatting errors fixed")
        print("✓ No more 'Das sind ein paar Beispiele' intros")
        print("✓ No more Caesar-only puzzles")
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
