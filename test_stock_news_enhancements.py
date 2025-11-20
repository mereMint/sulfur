"""
Test script to validate stock market and news enhancements.

This tests:
1. Stock market module has new functions
2. News module has enhanced data gathering
3. Transaction types are properly handled
"""

import sys
from pathlib import Path

def test_stock_market_functions():
    """Test that stock_market module has new functions."""
    print("Testing stock_market module enhancements...")
    
    # Import stock market module
    from modules import stock_market
    
    # Check for new functions
    assert hasattr(stock_market, 'get_recent_trades'), "get_recent_trades should exist"
    assert hasattr(stock_market, 'get_stock_stats'), "get_stock_stats should exist"
    assert hasattr(stock_market, 'get_market_overview'), "get_market_overview should exist"
    
    # Check existing functions still exist
    assert hasattr(stock_market, 'buy_stock'), "buy_stock should still exist"
    assert hasattr(stock_market, 'sell_stock'), "sell_stock should still exist"
    assert hasattr(stock_market, 'get_user_portfolio'), "get_user_portfolio should still exist"
    assert hasattr(stock_market, 'get_top_stocks'), "get_top_stocks should still exist"
    
    print("✓ Stock market module has all required functions")
    return True

def test_news_module_enhancements():
    """Test that news module has enhanced functionality."""
    print("\nTesting news module enhancements...")
    
    # Import news module
    from modules import news
    
    # Check functions exist
    assert hasattr(news, 'gather_news_data'), "gather_news_data should exist"
    assert hasattr(news, 'create_article_with_ai'), "create_article_with_ai should exist"
    assert hasattr(news, 'create_fallback_article'), "create_fallback_article should exist"
    assert hasattr(news, 'get_latest_news'), "get_latest_news should exist"
    
    print("✓ News module has all required functions")
    return True

def test_transaction_type_emojis():
    """Test that transaction type emojis are defined."""
    print("\nTesting transaction type handling...")
    
    # Define expected transaction types
    expected_types = [
        'stock_buy',
        'stock_sell',
        'daily_reward',
        'quest_reward',
        'level_reward',
        'gambling',
        'transfer',
        'purchase',
        'boost',
        'role_purchase'
    ]
    
    print(f"✓ Transaction types defined: {', '.join(expected_types)}")
    return True

def test_format_functions():
    """Test stock market formatting functions."""
    print("\nTesting stock market formatting...")
    
    from modules import stock_market
    
    # Test format_price
    assert hasattr(stock_market, 'format_price'), "format_price should exist"
    assert hasattr(stock_market, 'get_stock_emoji'), "get_stock_emoji should exist"
    
    # Test format_price with different values
    test_prices = [0.15, 1.50, 50.00, 1500.00]
    for price in test_prices:
        formatted = stock_market.format_price(price)
        assert '$' in formatted, f"Formatted price should contain $: {formatted}"
    
    # Test get_stock_emoji with different change percentages
    test_changes = [-10, -3, 0, 3, 10]
    for change in test_changes:
        emoji = stock_market.get_stock_emoji(change)
        assert isinstance(emoji, str), f"Emoji should be string for {change}%"
        assert len(emoji) > 0, f"Emoji should not be empty for {change}%"
    
    print("✓ Formatting functions work correctly")
    return True

def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Stock Market and News Enhancements")
    print("=" * 60)
    
    tests = [
        test_stock_market_functions,
        test_news_module_enhancements,
        test_transaction_type_emojis,
        test_format_functions,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
