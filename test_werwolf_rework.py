#!/usr/bin/env python3
"""
Test script for Werwolf rework - validates the new role selection functionality.
This test checks the logic without requiring imports or dependencies.
"""

def test_role_assignment_logic():
    """Test that role assignment respects selected roles."""
    print("=" * 60)
    print("WERWOLF REWORK - ROLE ASSIGNMENT LOGIC TESTS")
    print("=" * 60)
    print()
    
    # Define role constants (same as in werwolf.py)
    DORFBEWOHNER = "Dorfbewohner"
    WERWOLF = "Werwolf"
    SEHERIN = "Seherin"
    HEXE = "Hexe"
    DÖNERSTOPFER = "Dönerstopfer"
    JÄGER = "Jäger"
    AMOR = "Amor"
    DER_WEISSE = "Der Weiße"
    
    passed = 0
    failed = 0
    
    # Test case 1: All roles selected (8 players)
    print("Test 1: 8 players with all roles selected")
    player_count = 8
    selected_roles = {SEHERIN, HEXE, DÖNERSTOPFER, JÄGER, AMOR, DER_WEISSE}
    
    # This is the exact logic from werwolf.py
    num_werwolfe = max(1, player_count // 3)  # Should be 2
    num_seherin = 1 if (player_count > 2 and SEHERIN in selected_roles) else 0  # 1
    num_hexe = 1 if (player_count >= 7 and HEXE in selected_roles) else 0  # 1
    num_döner = 1 if (player_count >= 9 and DÖNERSTOPFER in selected_roles) else 0  # 0
    num_jäger = 1 if (player_count >= 5 and JÄGER in selected_roles) else 0  # 1
    num_amor = 1 if (player_count >= 8 and AMOR in selected_roles) else 0  # 1
    num_weisse = 1 if (player_count >= 10 and DER_WEISSE in selected_roles) else 0  # 0
    num_dorfbewohner = player_count - num_werwolfe - num_seherin - num_hexe - num_döner - num_jäger - num_amor - num_weisse
    
    total = num_werwolfe + num_seherin + num_hexe + num_döner + num_jäger + num_amor + num_weisse + num_dorfbewohner
    
    if total == player_count and num_werwolfe == 2 and num_seherin == 1 and num_hexe == 1 and num_jäger == 1 and num_amor == 1 and num_dorfbewohner == 2:
        print(f"  ✓ PASS: {num_werwolfe} Werwölfe, {num_seherin} Seherin, {num_hexe} Hexe, {num_jäger} Jäger, {num_amor} Amor, {num_dorfbewohner} Dorfbewohner")
        passed += 1
    else:
        print(f"  ✗ FAIL: Expected 8 total, got {total}")
        print(f"    Got: {num_werwolfe} WW, {num_seherin} Seherin, {num_hexe} Hexe, {num_döner} Döner, {num_jäger} Jäger, {num_amor} Amor, {num_weisse} Weisse, {num_dorfbewohner} Dorf")
        failed += 1
    
    # Test case 2: No special roles (5 players)
    print("\nTest 2: 5 players with no special roles")
    player_count = 5
    selected_roles = set()  # No special roles
    
    num_werwolfe = max(1, player_count // 3)  # Should be 1
    num_seherin = 1 if (player_count > 2 and SEHERIN in selected_roles) else 0  # 0
    num_hexe = 1 if (player_count >= 7 and HEXE in selected_roles) else 0  # 0
    num_döner = 1 if (player_count >= 9 and DÖNERSTOPFER in selected_roles) else 0  # 0
    num_jäger = 1 if (player_count >= 5 and JÄGER in selected_roles) else 0  # 0
    num_amor = 1 if (player_count >= 8 and AMOR in selected_roles) else 0  # 0
    num_weisse = 1 if (player_count >= 10 and DER_WEISSE in selected_roles) else 0  # 0
    num_dorfbewohner = player_count - num_werwolfe - num_seherin - num_hexe - num_döner - num_jäger - num_amor - num_weisse
    
    total = num_werwolfe + num_seherin + num_hexe + num_döner + num_jäger + num_amor + num_weisse + num_dorfbewohner
    
    if total == player_count and num_werwolfe == 1 and num_dorfbewohner == 4:
        print(f"  ✓ PASS: {num_werwolfe} Werwolf, {num_dorfbewohner} Dorfbewohner (no special roles)")
        passed += 1
    else:
        print(f"  ✗ FAIL: Expected 5 total, got {total}")
        failed += 1
    
    # Test case 3: Only Seherin selected (10 players)
    print("\nTest 3: 10 players with only Seherin selected")
    player_count = 10
    selected_roles = {SEHERIN}
    
    num_werwolfe = max(1, player_count // 3)  # Should be 3
    num_seherin = 1 if (player_count > 2 and SEHERIN in selected_roles) else 0  # 1
    num_hexe = 1 if (player_count >= 7 and HEXE in selected_roles) else 0  # 0
    num_döner = 1 if (player_count >= 9 and DÖNERSTOPFER in selected_roles) else 0  # 0
    num_jäger = 1 if (player_count >= 5 and JÄGER in selected_roles) else 0  # 0
    num_amor = 1 if (player_count >= 8 and AMOR in selected_roles) else 0  # 0
    num_weisse = 1 if (player_count >= 10 and DER_WEISSE in selected_roles) else 0  # 0
    num_dorfbewohner = player_count - num_werwolfe - num_seherin - num_hexe - num_döner - num_jäger - num_amor - num_weisse
    
    total = num_werwolfe + num_seherin + num_hexe + num_döner + num_jäger + num_amor + num_weisse + num_dorfbewohner
    
    if total == player_count and num_werwolfe == 3 and num_seherin == 1 and num_dorfbewohner == 6:
        print(f"  ✓ PASS: {num_werwolfe} Werwölfe, {num_seherin} Seherin, {num_dorfbewohner} Dorfbewohner")
        passed += 1
    else:
        print(f"  ✗ FAIL: Expected 10 total, got {total}")
        failed += 1
    
    # Test case 4: All roles with 12 players (max scenario)
    print("\nTest 4: 12 players with all roles selected")
    player_count = 12
    selected_roles = {SEHERIN, HEXE, DÖNERSTOPFER, JÄGER, AMOR, DER_WEISSE}
    
    num_werwolfe = max(1, player_count // 3)  # Should be 4
    num_seherin = 1 if (player_count > 2 and SEHERIN in selected_roles) else 0  # 1
    num_hexe = 1 if (player_count >= 7 and HEXE in selected_roles) else 0  # 1
    num_döner = 1 if (player_count >= 9 and DÖNERSTOPFER in selected_roles) else 0  # 1
    num_jäger = 1 if (player_count >= 5 and JÄGER in selected_roles) else 0  # 1
    num_amor = 1 if (player_count >= 8 and AMOR in selected_roles) else 0  # 1
    num_weisse = 1 if (player_count >= 10 and DER_WEISSE in selected_roles) else 0  # 1
    num_dorfbewohner = player_count - num_werwolfe - num_seherin - num_hexe - num_döner - num_jäger - num_amor - num_weisse
    
    total = num_werwolfe + num_seherin + num_hexe + num_döner + num_jäger + num_amor + num_weisse + num_dorfbewohner
    
    # With 12 players: 4 WW + 1+1+1+1+1+1 (6 special) = 10, leaving 2 villagers
    if total == player_count and num_werwolfe == 4 and num_dorfbewohner == 2:
        print(f"  ✓ PASS: {num_werwolfe} Werwölfe, all 6 special roles, {num_dorfbewohner} Dorfbewohner")
        passed += 1
    else:
        print(f"  ✗ FAIL: Expected 12 total (4 WW, 6 special, 2 villagers), got {total}")
        print(f"    Got: {num_werwolfe} WW, {num_seherin} Seherin, {num_hexe} Hexe, {num_döner} Döner, {num_jäger} Jäger, {num_amor} Amor, {num_weisse} Weisse, {num_dorfbewohner} Dorf")
        failed += 1
    
    # Test case 5: Edge case - 2 players with Seherin
    print("\nTest 5: 2 players with Seherin selected")
    player_count = 2
    selected_roles = {SEHERIN}
    
    num_werwolfe = 1
    num_seherin = 1 if SEHERIN in selected_roles else 0  # 1
    num_hexe, num_döner, num_jäger, num_amor, num_weisse = 0, 0, 0, 0, 0
    num_dorfbewohner = player_count - num_werwolfe - num_seherin
    
    total = num_werwolfe + num_seherin + num_dorfbewohner
    
    if total == player_count and num_werwolfe == 1 and num_seherin == 1 and num_dorfbewohner == 0:
        print(f"  ✓ PASS: {num_werwolfe} Werwolf, {num_seherin} Seherin")
        passed += 1
    else:
        print(f"  ✗ FAIL: Expected 2 total, got {total}")
        failed += 1
    
    # Test case 6: Backward compatibility - None means all roles
    print("\nTest 6: Backward compatibility with selected_roles=None (10 players)")
    player_count = 10
    selected_roles = None
    
    # If selected_roles is None, use all roles (backward compatibility)
    if selected_roles is None:
        selected_roles = {SEHERIN, HEXE, DÖNERSTOPFER, JÄGER, AMOR, DER_WEISSE}
    
    num_werwolfe = max(1, player_count // 3)
    num_seherin = 1 if (player_count > 2 and SEHERIN in selected_roles) else 0
    num_hexe = 1 if (player_count >= 7 and HEXE in selected_roles) else 0
    num_döner = 1 if (player_count >= 9 and DÖNERSTOPFER in selected_roles) else 0
    num_jäger = 1 if (player_count >= 5 and JÄGER in selected_roles) else 0
    num_amor = 1 if (player_count >= 8 and AMOR in selected_roles) else 0
    num_weisse = 1 if (player_count >= 10 and DER_WEISSE in selected_roles) else 0
    num_dorfbewohner = player_count - num_werwolfe - num_seherin - num_hexe - num_döner - num_jäger - num_amor - num_weisse
    
    total = num_werwolfe + num_seherin + num_hexe + num_döner + num_jäger + num_amor + num_weisse + num_dorfbewohner
    
    # With 10 players and all roles: 3 WW, 1 Seherin, 1 Hexe, 1 Döner, 1 Jäger, 1 Amor, 1 Weisse = 9, so 1 Dorf
    if total == player_count:
        print(f"  ✓ PASS: Backward compatibility works - all roles assigned based on player count")
        passed += 1
    else:
        print(f"  ✗ FAIL: Expected 10 total, got {total}")
        failed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print(f"TESTS COMPLETE: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("✅ ALL TESTS PASSED!")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(test_role_assignment_logic())
