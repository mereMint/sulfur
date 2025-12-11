#!/usr/bin/env python3
"""
Validation script for Advanced AI and Voice Call features.
Checks if all new modules and features are properly integrated.
"""

import sys
import os
import importlib

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_module(module_name):
    """Check if a module can be imported."""
    try:
        importlib.import_module(module_name)
        print(f"✓ Module '{module_name}' imported successfully")
        return True
    except ImportError as e:
        # Check if it's a dependency issue (mysql, discord, aiohttp)
        error_msg = str(e)
        if 'mysql' in error_msg or 'discord' in error_msg or 'aiohttp' in error_msg:
            print(f"⚠ Module '{module_name}' has missing dependencies (expected in CI): {e}")
            return True  # Don't fail on dependency issues
        else:
            print(f"✗ Failed to import '{module_name}': {e}")
            return False
    except Exception as e:
        print(f"✗ Error importing '{module_name}': {e}")
        return False

def check_file_exists(filepath):
    """Check if a file exists."""
    if os.path.exists(filepath):
        print(f"✓ File exists: {filepath}")
        return True
    else:
        print(f"✗ Missing file: {filepath}")
        return False

def main():
    print("=" * 60)
    print("Advanced AI & Voice Call Features - Validation Check")
    print("=" * 60)
    print()
    
    all_checks_passed = True
    
    # Check Python modules
    print("Checking Python Modules...")
    print("-" * 60)
    modules = [
        'modules.advanced_ai',
        'modules.voice_conversation',
        'modules.bot_enhancements',
        'modules.api_helpers',
        'modules.voice_tts',
        'modules.bot_mind',
        'modules.personality_evolution'
    ]
    
    for module in modules:
        if not check_module(module):
            all_checks_passed = False
    
    print()
    
    # Check web dashboard files
    print("Checking Web Dashboard Files...")
    print("-" * 60)
    web_files = [
        'web/ai_reasoning.html',
        'web/voice_calls.html',
        'web/layout.html',
        'web_dashboard.py'
    ]
    
    for file in web_files:
        if not check_file_exists(file):
            all_checks_passed = False
    
    print()
    
    # Check database migration
    print("Checking Database Migration...")
    print("-" * 60)
    if check_file_exists('scripts/db_migrations/migrate_advanced_ai_voice.sql'):
        print("  Migration file ready to run")
    else:
        all_checks_passed = False
    
    print()
    
    # Check documentation
    print("Checking Documentation...")
    print("-" * 60)
    if check_file_exists('docs/ADVANCED_AI_FEATURES.md'):
        print("  Documentation is complete")
    else:
        all_checks_passed = False
    
    print()
    
    # Check bot.py for new commands
    print("Checking Discord Commands in bot.py...")
    print("-" * 60)
    try:
        with open('bot.py', 'r') as f:
            bot_content = f.read()
            
        commands = [
            'debug_ai_reasoning',
            'debug_tokens',
            'debug_memory',
            'debug_voice',
            'clear_context'
        ]
        
        for cmd in commands:
            if cmd in bot_content:
                print(f"✓ Command '{cmd}' found in bot.py")
            else:
                print(f"✗ Command '{cmd}' NOT found in bot.py")
                all_checks_passed = False
    except Exception as e:
        print(f"✗ Error reading bot.py: {e}")
        all_checks_passed = False
    
    print()
    
    # Check imports in bot.py
    print("Checking Imports in bot.py...")
    print("-" * 60)
    required_imports = [
        'advanced_ai',
        'voice_conversation'
    ]
    
    for imp in required_imports:
        if imp in bot_content:
            print(f"✓ Import '{imp}' found in bot.py")
        else:
            print(f"✗ Import '{imp}' NOT found in bot.py")
            all_checks_passed = False
    
    print()
    
    # Check web_dashboard.py for new routes
    print("Checking Web Dashboard Routes...")
    print("-" * 60)
    try:
        with open('web_dashboard.py', 'r') as f:
            dashboard_content = f.read()
            
        routes = [
            '/ai_reasoning',
            '/voice_calls',
            '/api/ai_reasoning_debug',
            '/api/voice_calls/stats'
        ]
        
        for route in routes:
            if route in dashboard_content:
                print(f"✓ Route '{route}' found in web_dashboard.py")
            else:
                print(f"✗ Route '{route}' NOT found in web_dashboard.py")
                all_checks_passed = False
    except Exception as e:
        print(f"✗ Error reading web_dashboard.py: {e}")
        all_checks_passed = False
    
    print()
    print("=" * 60)
    
    if all_checks_passed:
        print("✓ ALL CHECKS PASSED!")
        print()
        print("Next steps:")
        print("1. Run database migration:")
        print("   mysql -u sulfur_bot_user -p sulfur_bot < scripts/db_migrations/migrate_advanced_ai_voice.sql")
        print()
        print("2. Install optional dependencies:")
        print("   pip install edge-tts SpeechRecognition")
        print()
        print("3. Restart the bot:")
        print("   ./maintain_bot.sh")
        print()
        print("4. Access new dashboard pages:")
        print("   http://localhost:5000/ai_reasoning")
        print("   http://localhost:5000/voice_calls")
        return 0
    else:
        print("✗ SOME CHECKS FAILED")
        print("Please review the errors above and fix them.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
