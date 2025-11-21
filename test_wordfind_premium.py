#!/usr/bin/env python3
"""
Test script to verify word find premium features work correctly.
This tests the new premium game functionality and share feature.
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the word_find module
import modules.word_find as word_find

def test_share_text_creation():
    """Test that share text is created correctly without spoiling the word"""
    print("Testing share text creation...")
    print("=" * 60)
    
    # Mock attempts data
    mock_attempts = [
        {'attempt_number': 1, 'guess': 'test1', 'similarity_score': 15.5},
        {'attempt_number': 2, 'guess': 'test2', 'similarity_score': 45.2},
        {'attempt_number': 3, 'guess': 'test3', 'similarity_score': 68.7},
        {'attempt_number': 4, 'guess': 'test4', 'similarity_score': 85.3},
        {'attempt_number': 5, 'guess': 'correct', 'similarity_score': 100.0},
    ]
    
    # Test daily game share (won)
    print("\n1. Testing daily game share (won)...")
    share_text = word_find.create_share_text(mock_attempts, True, 'daily')
    print(share_text)
    
    # Verify the text doesn't contain the actual guesses
    assert 'test1' not in share_text, "Share text should not contain actual guesses"
    assert 'test2' not in share_text, "Share text should not contain actual guesses"
    assert 'correct' not in share_text, "Share text should not contain actual guesses"
    assert '✅' in share_text, "Share text should show success emoji for won game"
    assert '5/20' in share_text, "Share text should show attempt count"
    print("   ✓ Daily game share text is correct and doesn't spoil")
    
    # Test premium game share (won)
    print("\n2. Testing premium game share (won)...")
    share_text = word_find.create_share_text(mock_attempts, True, 'premium')
    print(share_text)
    assert 'Premium' in share_text, "Premium game share should be labeled"
    assert '✅' in share_text, "Share text should show success emoji for won game"
    print("   ✓ Premium game share text is correct")
    
    # Test failed game share
    mock_failed_attempts = [
        {'attempt_number': i, 'guess': f'test{i}', 'similarity_score': 20 + i * 3}
        for i in range(1, 21)
    ]
    
    print("\n3. Testing failed game share...")
    share_text = word_find.create_share_text(mock_failed_attempts, False, 'daily')
    print(share_text)
    assert '❌' in share_text, "Share text should show failure emoji for lost game"
    assert '20/20' in share_text, "Share text should show all attempts used"
    print("   ✓ Failed game share text is correct")
    
    # Verify emoji pattern is correct
    print("\n4. Testing emoji pattern...")
    # First attempt: 15.5% (< 20) should be ⬛
    # Second: 45.2% (40-60) should be 🟦
    # Third: 68.7% (60-80) should be 🟨
    # Fourth: 85.3% (>= 80) should be 🟧
    # Fifth: 100% should be 🟩
    expected_emojis = ['⬛', '🟦', '🟨', '🟧', '🟩']
    share_text_lines = share_text.split('\n')
    emoji_line = None
    for line in share_text_lines:
        if any(emoji in line for emoji in expected_emojis):
            emoji_line = line
            break
    
    if emoji_line:
        for emoji in expected_emojis:
            assert emoji in emoji_line, f"Expected emoji {emoji} not found in pattern"
        print(f"   ✓ Emoji pattern is correct: {emoji_line}")
    
    print("\n" + "=" * 60)
    print("All share text tests passed! ✓")
    return True


def test_word_similarity():
    """Test word similarity calculation"""
    print("\nTesting word similarity calculation...")
    print("=" * 60)
    
    # Test exact match
    similarity = word_find.calculate_word_similarity("haus", "haus")
    assert similarity == 100.0, f"Exact match should be 100%, got {similarity}"
    print(f"   ✓ Exact match: {similarity}%")
    
    # Test completely different words
    similarity = word_find.calculate_word_similarity("haus", "xyz")
    assert similarity < 50, f"Different words should have low similarity, got {similarity}"
    print(f"   ✓ Different words: {similarity}%")
    
    # Test similar words
    similarity = word_find.calculate_word_similarity("haus", "maus")
    assert 50 < similarity < 100, f"Similar words should have medium similarity, got {similarity}"
    print(f"   ✓ Similar words: {similarity}%")
    
    # Test case insensitivity
    similarity1 = word_find.calculate_word_similarity("HAUS", "haus")
    similarity2 = word_find.calculate_word_similarity("haus", "haus")
    assert similarity1 == similarity2 == 100.0, "Case should not matter"
    print(f"   ✓ Case insensitive: {similarity1}%")
    
    print("\n" + "=" * 60)
    print("All similarity tests passed! ✓")
    return True


def test_game_embed_creation():
    """Test game embed creation with different game types"""
    print("\nTesting game embed creation...")
    print("=" * 60)
    
    word_data = {
        'id': 1,
        'word': 'testword',
        'difficulty': 'medium'
    }
    
    attempts = []
    max_attempts = 20
    user_stats = {
        'total_games': 10,
        'total_wins': 7,
        'current_streak': 3,
        'best_streak': 5,
        'total_attempts': 80
    }
    
    # Test daily game embed
    print("\n1. Testing daily game embed...")
    embed = word_find.create_game_embed(word_data, attempts, max_attempts, user_stats, 'daily')
    assert "Tägliches" in embed.title, "Daily game should have 'Tägliches' in title"
    print(f"   ✓ Daily game embed title: {embed.title}")
    
    # Test premium game embed
    print("\n2. Testing premium game embed...")
    embed = word_find.create_game_embed(word_data, attempts, max_attempts, user_stats, 'premium')
    assert "Premium" in embed.title, "Premium game should have 'Premium' in title"
    print(f"   ✓ Premium game embed title: {embed.title}")
    
    print("\n" + "=" * 60)
    print("All embed tests passed! ✓")
    return True


if __name__ == "__main__":
    print("Starting Word Find Premium Features Tests")
    print("=" * 60)
    
    try:
        # Run all tests
        test_share_text_creation()
        test_word_similarity()
        test_game_embed_creation()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        sys.exit(0)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
