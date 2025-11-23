#!/usr/bin/env python3
"""
Verification script for game fixes:
1. WordFind difficulty error fix
2. Wordle expanded word validation
3. Horse racing mobile formatting
"""

import sys
import discord
from modules import word_find, wordle, horse_racing


def test_wordfind_difficulty_fix():
    """Test that WordFind difficulty variable is always accessible."""
    print("=" * 60)
    print("TEST 1: WordFind Difficulty Variable Fix")
    print("=" * 60)
    
    # Test with difficulty present
    word_data = {'word': 'computer', 'difficulty': 'hard', 'id': 1}
    try:
        embed = word_find.create_game_embed(word_data, [], 20, None, 'daily', None)
        assert 'HARD' in embed.description, "Difficulty should be in description"
        print("✓ PASS: WordFind embed with difficulty='hard' created successfully")
    except Exception as e:
        print(f"✗ FAIL: Error creating embed with difficulty: {e}")
        return False
    
    # Test with difficulty missing (should default to 'medium')
    word_data_no_diff = {'word': 'test', 'id': 1}
    try:
        embed = word_find.create_game_embed(word_data_no_diff, [], 20, None, 'daily', None)
        assert 'MEDIUM' in embed.description, "Should default to medium difficulty"
        print("✓ PASS: WordFind embed without difficulty defaults to 'medium'")
    except Exception as e:
        print(f"✗ FAIL: Error creating embed without difficulty: {e}")
        return False
    
    # Test with premium game type
    word_data_premium = {'word': 'premium', 'difficulty': 'easy', 'id': 2}
    try:
        embed = word_find.create_game_embed(word_data_premium, [], 20, None, 'premium', None)
        assert 'Premium Spiel' in embed.title, "Should show premium in title"
        assert 'EASY' in embed.description, "Difficulty should be in description"
        print("✓ PASS: WordFind premium game embed created successfully")
    except Exception as e:
        print(f"✗ FAIL: Error creating premium embed: {e}")
        return False
    
    print("\n✓ All WordFind difficulty tests passed!\n")
    return True


def test_wordle_expanded_validation():
    """Test that Wordle accepts more valid words now."""
    print("=" * 60)
    print("TEST 2: Wordle Expanded Word Validation")
    print("=" * 60)
    
    # Get validation sets
    de_valid = wordle.get_wordle_words('de')
    en_valid = wordle.get_wordle_words('en')
    
    # Get solution lists (should be smaller)
    de_solutions = wordle.get_wordle_words_list('de')
    en_solutions = wordle.get_wordle_words_list('en')
    
    print(f"German words - Solutions: {len(de_solutions)}, Valid guesses: {len(de_valid)}")
    print(f"English words - Solutions: {len(en_solutions)}, Valid guesses: {len(en_valid)}")
    
    # Verify expansion worked
    if len(de_valid) <= len(de_solutions):
        print(f"✗ FAIL: German validation set not expanded")
        return False
    print(f"✓ PASS: German validation expanded by {len(de_valid) - len(de_solutions)} words")
    
    if len(en_valid) <= len(en_solutions):
        print(f"✗ FAIL: English validation set not expanded")
        return False
    print(f"✓ PASS: English validation expanded by {len(en_valid) - len(en_solutions)} words")
    
    # Test common German words that should now be valid
    test_german_words = ['leben', 'liebe', 'freie', 'woche', 'macht']
    passed = 0
    for word in test_german_words:
        if word in de_valid:
            print(f"  ✓ German word '{word}' is valid")
            passed += 1
        else:
            print(f"  - German word '{word}' not in validation set")
    
    if passed >= 3:
        print(f"✓ PASS: {passed}/{len(test_german_words)} common German words are valid")
    else:
        print(f"✗ FAIL: Only {passed}/{len(test_german_words)} German words valid")
        return False
    
    # Test common English words
    test_english_words = ['house', 'mouse', 'tower', 'power', 'happy', 'world']
    passed = 0
    for word in test_english_words:
        if word in en_valid:
            print(f"  ✓ English word '{word}' is valid")
            passed += 1
        else:
            print(f"  - English word '{word}' not in validation set")
    
    if passed >= 5:
        print(f"✓ PASS: {passed}/{len(test_english_words)} common English words are valid")
    else:
        print(f"✗ FAIL: Only {passed}/{len(test_english_words)} English words valid")
        return False
    
    print("\n✓ All Wordle validation tests passed!\n")
    return True


def test_horse_racing_mobile_formatting():
    """Test that horse racing handles long names correctly."""
    print("=" * 60)
    print("TEST 3: Horse Racing Mobile Formatting")
    print("=" * 60)
    
    # Create a race with some horses
    race = horse_racing.HorseRace(1, 4)
    
    # Replace one horse with a very long name
    long_name_horse = {
        'name': 'Super Long Horse Name That Exceeds Limits',
        'emoji': '🐴',
        'color': discord.Color.gold()
    }
    race.horses[0] = long_name_horse
    
    # Set some positions
    race.positions = [5, 12, 18, 8]
    race.finished = [False, False, True, False]
    race.finish_order = [2]
    
    # Generate visual
    try:
        visual = race.get_race_visual()
        print("Race visual generated successfully:")
        print(visual)
        
        # Verify it's wrapped in code blocks
        if not visual.startswith('```') or not visual.endswith('```'):
            print("✗ FAIL: Visual should be wrapped in code blocks for mobile")
            return False
        print("✓ PASS: Visual wrapped in code blocks for monospace display")
        
        # Verify long name is truncated (should contain ellipsis)
        if '…' not in visual.split('\n')[1]:  # First horse line
            print("✗ FAIL: Long horse name should be truncated with ellipsis")
            return False
        print("✓ PASS: Long horse name truncated with ellipsis")
        
        # Verify all lines are present
        lines = visual.strip('`\n').split('\n')
        if len(lines) != 4:  # 4 horses
            print(f"✗ FAIL: Expected 4 horse lines, got {len(lines)}")
            return False
        print(f"✓ PASS: All {len(lines)} horse lines present")
        
    except Exception as e:
        print(f"✗ FAIL: Error generating race visual: {e}")
        return False
    
    print("\n✓ All horse racing tests passed!\n")
    return True


def main():
    """Run all verification tests."""
    print("\n" + "=" * 60)
    print("VERIFICATION TESTS FOR GAME FIXES")
    print("=" * 60 + "\n")
    
    tests = [
        ("WordFind Difficulty Fix", test_wordfind_difficulty_fix),
        ("Wordle Validation Expansion", test_wordle_expanded_validation),
        ("Horse Racing Mobile Format", test_horse_racing_mobile_formatting),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ EXCEPTION in {name}: {e}\n")
            results.append((name, False))
    
    # Summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Fixes verified successfully.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
