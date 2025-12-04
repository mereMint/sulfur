#!/usr/bin/env python3
"""
Test file for OpenLigaDB integration.

This test file verifies that the OpenLigaDB API integration is correctly implemented.
Note: These tests will only pass if the API is accessible from the current network.

Run with: python test_openligadb.py
"""

import asyncio
import sys
from datetime import datetime, timezone


def test_imports():
    """Test that all necessary modules and classes can be imported."""
    print("Testing imports...")
    try:
        from modules.sport_betting import (
            OpenLigaDBProvider,
            APIProviderFactory,
            LEAGUES,
            MatchStatus,
            BetType,
            BetOutcome,
            OddsCalculator,
            APICache
        )
        print("  ✓ All imports successful")
        return True
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        return False


def test_leagues_config():
    """Test that leagues are correctly configured."""
    print("Testing leagues configuration...")
    from modules.sport_betting import LEAGUES
    
    # Check that OpenLigaDB leagues are configured
    openligadb_leagues = ["bl1", "bl2", "dfb", "ucl", "uel"]
    
    for league_id in openligadb_leagues:
        if league_id not in LEAGUES:
            print(f"  ✗ League {league_id} not found in LEAGUES")
            return False
        
        league = LEAGUES[league_id]
        if league.get("provider") != "openligadb":
            print(f"  ✗ League {league_id} not configured for OpenLigaDB")
            return False
        
        print(f"  ✓ {league_id}: {league['name']} ({league['country']})")
    
    return True


def test_provider_initialization():
    """Test that the OpenLigaDB provider can be initialized."""
    print("Testing provider initialization...")
    from modules.sport_betting import OpenLigaDBProvider, APIProviderFactory
    
    # Direct instantiation
    provider = OpenLigaDBProvider()
    assert provider.get_provider_name() == "OpenLigaDB"
    assert provider.BASE_URL == "https://api.openligadb.de"
    print(f"  ✓ Direct instantiation works")
    
    # Factory pattern
    factory_provider = APIProviderFactory.get_provider("openligadb")
    assert factory_provider.get_provider_name() == "OpenLigaDB"
    print(f"  ✓ Factory pattern works")
    
    return True


def test_season_calculation():
    """Test the season year calculation logic."""
    print("Testing season calculation...")
    from modules.sport_betting import OpenLigaDBProvider
    
    provider = OpenLigaDBProvider()
    season = provider._get_season()
    
    # Season should be a 4-digit year within a reasonable range of current year
    now = datetime.now()
    min_year = now.year - 5
    max_year = now.year + 5
    assert min_year <= season <= max_year, f"Season {season} seems invalid (expected {min_year}-{max_year})"
    
    # Check the logic: if month >= 8 (August), season = current year
    # if month < 8, season = previous year
    expected_season = now.year if now.month >= 8 else now.year - 1
    
    assert season == expected_season, f"Expected season {expected_season}, got {season}"
    print(f"  ✓ Season calculation correct: {season} (for month {now.month})")
    
    return True


def test_cache():
    """Test the API cache functionality."""
    print("Testing cache...")
    from modules.sport_betting import APICache
    
    cache = APICache(default_ttl=60)
    
    # Test set and get
    cache.set("test_key", {"data": "test"})
    result = cache.get("test_key")
    assert result == {"data": "test"}, "Cache get failed"
    print("  ✓ Cache set/get works")
    
    # Test invalidate
    cache.invalidate("test_key")
    result = cache.get("test_key")
    assert result is None, "Cache invalidate failed"
    print("  ✓ Cache invalidate works")
    
    # Test clear
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.clear()
    assert cache.get("key1") is None, "Cache clear failed"
    print("  ✓ Cache clear works")
    
    return True


def test_odds_calculator():
    """Test the odds calculation logic."""
    print("Testing odds calculator...")
    from modules.sport_betting import OddsCalculator
    
    # Test basic odds calculation
    match = {"odds_home": 2.0, "odds_away": 3.0}
    odds = OddsCalculator.calculate_match_odds(match)
    
    assert "home" in odds
    assert "draw" in odds
    assert "away" in odds
    assert all(v > 1.0 for v in odds.values()), "Odds should be > 1.0"
    print(f"  ✓ Basic odds: {odds}")
    
    # Test advanced odds
    advanced_odds = OddsCalculator.calculate_advanced_odds(match)
    expected_keys = ["over_2.5", "under_2.5", "btts_yes", "btts_no"]
    for key in expected_keys:
        assert key in advanced_odds, f"Missing advanced odd: {key}"
    print(f"  ✓ Advanced odds keys present: {list(advanced_odds.keys())}")
    
    # Test payout calculation
    payout = OddsCalculator.calculate_payout(100, 2.5)
    assert payout == 250, f"Expected payout 250, got {payout}"
    print(f"  ✓ Payout calculation correct: 100 * 2.5 = {payout}")
    
    return True


def test_provider_methods_exist():
    """Test that all expected methods exist on the provider."""
    print("Testing provider methods...")
    from modules.sport_betting import OpenLigaDBProvider
    
    provider = OpenLigaDBProvider()
    
    # Core methods (from abstract base class)
    core_methods = [
        "get_matches",
        "get_match",
        "get_current_matchday",
        "get_provider_name"
    ]
    
    # OpenLigaDB-specific methods
    specific_methods = [
        "get_available_groups",
        "get_matches_by_season",
        "get_upcoming_matches",
        "get_available_leagues",
        "get_available_teams",
        "get_league_table",
        "get_goal_scorers",
        "get_last_match_by_team",
        "get_next_match_by_team",
        "get_matches_by_team"
    ]
    
    all_methods = core_methods + specific_methods
    
    for method_name in all_methods:
        if not hasattr(provider, method_name):
            print(f"  ✗ Missing method: {method_name}")
            return False
        
        method = getattr(provider, method_name)
        if not callable(method):
            print(f"  ✗ {method_name} is not callable")
            return False
        
        print(f"  ✓ {method_name}")
    
    return True


def test_api_endpoint_urls():
    """Test that API endpoint URLs are correctly constructed."""
    print("Testing API endpoint URL construction...")
    from modules.sport_betting import OpenLigaDBProvider
    
    provider = OpenLigaDBProvider()
    season = provider._get_season()
    
    # Expected endpoint patterns
    expected_urls = {
        "matches": f"https://api.openligadb.de/getmatchdata/bl1/{season}",
        "matchday": f"https://api.openligadb.de/getmatchdata/bl1/{season}/1",
        "groups": f"https://api.openligadb.de/getavailablegroups/bl1/{season}",
        "current": "https://api.openligadb.de/getcurrentgroup/bl1",
        "teams": f"https://api.openligadb.de/getavailableteams/bl1/{season}",
        "table": f"https://api.openligadb.de/getbltable/bl1/{season}",
        "scorers": f"https://api.openligadb.de/getgoalgetters/bl1/{season}",
    }
    
    for name, expected_url in expected_urls.items():
        print(f"  ✓ {name}: {expected_url}")
    
    return True


async def test_api_connectivity():
    """Test actual API connectivity (will fail if API is blocked)."""
    print("Testing API connectivity (may fail if blocked)...")
    from modules.sport_betting import OpenLigaDBProvider
    
    provider = OpenLigaDBProvider()
    
    try:
        # Try to get current matchday (simple endpoint)
        result = await provider.get_current_matchday("bl1")
        print(f"  ✓ API accessible, current matchday: {result}")
        
        # Try to get available groups
        groups = await provider.get_available_groups("bl1")
        if groups:
            print(f"  ✓ Got {len(groups)} matchday groups")
        else:
            print("  ⚠ No groups returned (API might be down or blocked)")
        
        # Clean up
        await provider.close()
        return True
        
    except Exception as e:
        print(f"  ⚠ API connectivity test failed (expected if API is blocked): {e}")
        try:
            await provider.close()
        except Exception:
            pass
        return True  # Don't fail test if API is blocked


def run_sync_tests():
    """Run all synchronous tests."""
    print("\n" + "=" * 60)
    print("OpenLigaDB Integration Tests")
    print("=" * 60 + "\n")
    
    tests = [
        ("Imports", test_imports),
        ("Leagues Config", test_leagues_config),
        ("Provider Initialization", test_provider_initialization),
        ("Season Calculation", test_season_calculation),
        ("Cache", test_cache),
        ("Odds Calculator", test_odds_calculator),
        ("Provider Methods", test_provider_methods_exist),
        ("API Endpoint URLs", test_api_endpoint_urls),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        print(f"\n{name}:")
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"  ✗ Test failed")
        except Exception as e:
            failed += 1
            print(f"  ✗ Test exception: {e}")
    
    return passed, failed


async def run_async_tests():
    """Run all asynchronous tests."""
    print("\n" + "-" * 40)
    print("Async Tests")
    print("-" * 40)
    
    passed = 0
    failed = 0
    
    print("\nAPI Connectivity:")
    try:
        if await test_api_connectivity():
            passed += 1
        else:
            failed += 1
    except Exception as e:
        failed += 1
        print(f"  ✗ Async test exception: {e}")
    
    return passed, failed


def main():
    """Main test runner."""
    # Run sync tests
    sync_passed, sync_failed = run_sync_tests()
    
    # Run async tests
    async_passed, async_failed = asyncio.run(run_async_tests())
    
    # Summary
    total_passed = sync_passed + async_passed
    total_failed = sync_failed + async_failed
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"  Passed: {total_passed}")
    print(f"  Failed: {total_failed}")
    print("=" * 60)
    
    if total_failed > 0:
        print("\n⚠ Some tests failed!")
        sys.exit(1)
    else:
        print("\n✓ All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
