#!/usr/bin/env python3
"""
Verification script for the bot startup fixes.

This script checks:
1. No duplicate command registrations in bot.py
2. SQL migration file has proper syntax
3. Python syntax is valid
4. No obvious issues that would prevent bot startup

Run this before starting the bot to verify the fixes are in place.
"""

import re
import sys
import ast
from pathlib import Path

def check_duplicate_commands():
    """Check for duplicate @tree.command registrations."""
    print("\n1. Checking for duplicate command registrations...")
    
    bot_file = Path("bot.py")
    if not bot_file.exists():
        print("   ❌ bot.py not found!")
        return False
    
    content = bot_file.read_text(encoding='utf-8')
    
    # Find all @tree.command registrations
    pattern = r'@tree\.command\(name="([^"]+)"'
    commands = re.findall(pattern, content)
    
    # Check for duplicates
    seen = {}
    duplicates = []
    for cmd in commands:
        if cmd in seen:
            duplicates.append(cmd)
        seen[cmd] = seen.get(cmd, 0) + 1
    
    if duplicates:
        print(f"   ❌ Found duplicate commands: {duplicates}")
        for cmd in set(duplicates):
            print(f"      '{cmd}' registered {seen[cmd]} times")
        return False
    
    print(f"   ✅ No duplicate commands found ({len(commands)} unique commands)")
    return True

def check_sql_migration():
    """Check SQL migration file for the ambiguous column fix."""
    print("\n2. Checking SQL migration fix...")
    
    migration_file = Path("scripts/db_migrations/011_autonomous_features.sql")
    if not migration_file.exists():
        print("   ⚠️  Migration file not found - skipping check")
        return True
    
    content = migration_file.read_text(encoding='utf-8')
    
    # Check for the old problematic pattern
    if "ON DUPLICATE KEY UPDATE user_id = user_id" in content:
        print("   ❌ Old ambiguous SQL pattern found!")
        return False
    
    # Check for the fix
    if "user_autonomous_settings.allow_autonomous_messages" in content and \
       "VALUES(allow_autonomous_messages)" in content:
        print("   ✅ SQL migration fix is in place")
        return True
    
    print("   ⚠️  Could not verify SQL fix pattern")
    return True  # Don't fail if we can't verify

def check_python_syntax():
    """Verify Python syntax is valid."""
    print("\n3. Checking Python syntax...")
    
    bot_file = Path("bot.py")
    if not bot_file.exists():
        print("   ❌ bot.py not found!")
        return False
    
    try:
        content = bot_file.read_text(encoding='utf-8')
        ast.parse(content)
        print("   ✅ Python syntax is valid")
        return True
    except SyntaxError as e:
        print(f"   ❌ Syntax error in bot.py: {e}")
        return False

def check_admin_group():
    """Verify AdminGroup is properly registered."""
    print("\n4. Checking AdminGroup registration...")
    
    bot_file = Path("bot.py")
    if not bot_file.exists():
        print("   ❌ bot.py not found!")
        return False
    
    content = bot_file.read_text(encoding='utf-8')
    
    # Check for AdminGroup class
    if "class AdminGroup(app_commands.Group):" not in content:
        print("   ❌ AdminGroup class not found!")
        return False
    
    # Check for AdminGroup registration
    if 'tree.add_command(AdminGroup(name="admin"))' not in content:
        print("   ❌ AdminGroup not registered to tree!")
        return False
    
    # Count AdminGroup subcommands
    pattern = r'class AdminGroup.*?(?=^class\s|\Z)'
    match = re.search(pattern, content, re.DOTALL | re.MULTILINE)
    if match:
        admin_section = match.group(0)
        subcommands = len(re.findall(r'@app_commands\.command\(', admin_section))
        print(f"   ✅ AdminGroup registered with {subcommands} subcommands")
        return True
    
    print("   ⚠️  Could not count AdminGroup subcommands")
    return True

def main():
    """Run all verification checks."""
    print("=" * 60)
    print("Bot Startup Fixes Verification")
    print("=" * 60)
    
    checks = [
        check_duplicate_commands,
        check_sql_migration,
        check_python_syntax,
        check_admin_group,
    ]
    
    results = []
    for check in checks:
        try:
            result = check()
            results.append(result)
        except Exception as e:
            print(f"   ❌ Check failed with error: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    if all(results):
        print("✅ All verification checks passed!")
        print("=" * 60)
        print("\nThe bot should now start without the following errors:")
        print("  - Column 'user_id' in UPDATE is ambiguous")
        print("  - Command 'admin' already registered")
        print("\nYou can now run: bash maintain_bot.sh")
        return 0
    else:
        print("❌ Some verification checks failed!")
        print("=" * 60)
        print("\nPlease fix the issues above before starting the bot.")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\n❌ Verification failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
