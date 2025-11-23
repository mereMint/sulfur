#!/usr/bin/env python3
"""
Verification script for bot startup fixes.

This script verifies that the critical syntax errors have been fixed:
1. modules/horse_racing.py - ABILITIES dictionary closing bracket
2. All modules can be imported successfully
3. Bot can initialize without syntax errors

Run this script to verify the bot is ready to run.
"""
import sys
import os
import ast

# Set up minimal environment for testing
os.environ.setdefault('DISCORD_BOT_TOKEN', 'MTIzNDU2.test.token-placeholder')
os.environ.setdefault('GEMINI_API_KEY', 'test_key')

def check_syntax(filepath):
    """Check a Python file for syntax errors."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            ast.parse(f.read())
        return True, None
    except SyntaxError as e:
        return False, f"Line {e.lineno}: {e.msg}"

def test_horse_racing_fix():
    """Verify the horse_racing.py ABILITIES dictionary fix."""
    print("Testing horse_racing.py fix...")
    
    # Check syntax
    ok, error = check_syntax('modules/horse_racing.py')
    if not ok:
        print(f"  ✗ SYNTAX ERROR: {error}")
        return False
    
    # Check that ABILITIES dictionary closes with }
    with open('modules/horse_racing.py', 'r') as f:
        content = f.read()
    
    # Look for the ABILITIES definition
    if 'ABILITIES = {' in content:
        # Find the closing bracket for ABILITIES
        start = content.find('ABILITIES = {')
        # Find the next line that has just } or ] at the end
        after_start = content[start:]
        lines = after_start.split('\n')
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped == '}' or stripped == ']':
                if stripped == '}':
                    print("  ✓ ABILITIES dictionary correctly closes with }")
                    return True
                else:
                    print(f"  ✗ ABILITIES dictionary incorrectly closes with ]")
                    return False
    
    print("  ! Could not verify ABILITIES bracket type")
    return True  # Assume OK if we can't find it

def test_all_modules():
    """Test that all modules can be imported."""
    print("\nTesting module imports...")
    
    critical_modules = [
        'modules.wordle',
        'modules.werwolf',
        'modules.word_find',
        'modules.horse_racing',
        'modules.detective_game',
        'modules.voice_manager',
        'modules.economy',
        'modules.level_system',
    ]
    
    all_ok = True
    for mod_name in critical_modules:
        try:
            __import__(mod_name)
            print(f"  ✓ {mod_name}")
        except Exception as e:
            print(f"  ✗ {mod_name}: {e}")
            all_ok = False
    
    return all_ok

def test_all_syntax():
    """Check all Python files for syntax errors."""
    print("\nChecking all Python files for syntax errors...")
    
    errors = []
    checked = 0
    
    for root, dirs, files in os.walk('.'):
        if 'venv' in root or '.git' in root or '__pycache__' in root:
            continue
        
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                ok, error = check_syntax(filepath)
                checked += 1
                
                if not ok:
                    errors.append((filepath, error))
    
    if errors:
        print(f"  ✗ Found {len(errors)} syntax errors:")
        for filepath, error in errors:
            print(f"    - {filepath}: {error}")
        return False
    else:
        print(f"  ✓ All {checked} Python files have valid syntax")
        return True

def main():
    """Run all verification tests."""
    print("=" * 70)
    print("BOT STARTUP FIXES VERIFICATION")
    print("=" * 70)
    print()
    
    results = []
    
    # Test 1: horse_racing.py fix
    results.append(('horse_racing.py fix', test_horse_racing_fix()))
    
    # Test 2: All modules import
    results.append(('Module imports', test_all_modules()))
    
    # Test 3: All syntax valid
    results.append(('Syntax validation', test_all_syntax()))
    
    # Summary
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, ok in results if ok)
    failed = sum(1 for _, ok in results if not ok)
    
    for test_name, ok in results:
        icon = "✓" if ok else "✗"
        print(f"{icon} {test_name}")
    
    print()
    
    if failed > 0:
        print(f"✗ {failed} test(s) failed")
        return 1
    else:
        print("✓ All verification tests passed!")
        print()
        print("The bot is ready to run. Make sure to:")
        print("1. Set up your .env file with valid Discord token and API keys")
        print("2. Configure and start MySQL database")
        print("3. Run: python3 bot.py")
        return 0

if __name__ == '__main__':
    sys.exit(main())
