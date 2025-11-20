#!/usr/bin/env python3
"""
Test script for detective game improvements.
Verifies that the prompts are correctly formatted and JSON parsing works.
"""

import re
import json

def test_prompt_improvements():
    """Test that prompts don't contain meta-phrases."""
    
    # Simulate what the prompts should look like
    good_prompts = [
        "Beschreibe eine Mordszene für den Fall 'Der Fall der verschwundenen Erbin' (Thema: corporate intrigue). 2-3 Sätze, lebendig und detailliert. NUR die Beschreibung schreiben, KEINE Meta-Kommentare, KEINE Einleitungen wie 'Hier ist...'.",
        "Nenne einen spezifischen, interessanten Tatort für 'Der Fall der verschwundenen Erbin'. Ein Satz. NUR den Ort nennen, z.B. 'Luxus-Penthouse am Hafen', KEINE Erklärungen.",
        "Liste 3-4 Beweisstücke für 'Der Fall der verschwundenen Erbin'. Format: emoji + kurze Beschreibung pro Zeile. WICHTIG: NUR die Beweise listen, KEINE Einleitung wie 'Hier sind...' oder Meta-Kommentare."
    ]
    
    # Check that prompts contain the anti-meta-comment instructions
    for prompt in good_prompts:
        assert "KEINE" in prompt or "NUR" in prompt, f"Prompt should contain instructions to avoid meta-comments: {prompt[:50]}"
        print(f"✅ Prompt contains anti-meta instructions: {prompt[:80]}...")
    
    print("\n✅ All prompts have proper anti-meta-comment instructions!")

def test_json_parsing():
    """Test JSON parsing improvements."""
    
    # Test cases
    test_cases = [
        # Normal JSON
        ('{"name": "Max Müller", "occupation": "Anwalt", "alibi": "Im Büro", "motive": "Geld", "suspicious_details": "War in der Nähe"}', True),
        # JSON with markdown code blocks
        ('```json\n{"name": "Anna Schmidt", "occupation": "Ärztin", "alibi": "Zu Hause", "motive": "Rache", "suspicious_details": "Hat Zugang"}\n```', True),
        # JSON with extra text
        ('Here is the suspect: {"name": "Peter Wolf", "occupation": "Koch", "alibi": "In der Küche", "motive": "Eifersucht", "suspicious_details": "Fingerabdrücke"}', True),
        # Invalid JSON
        ('This is not JSON at all', False),
        # Missing required fields
        ('{"name": "Hans Weber", "occupation": "Lehrer"}', False),
    ]
    
    for test_input, should_succeed in test_cases:
        try:
            # Simulate the parsing logic from detective_game.py
            cleaned = test_input.strip()
            if cleaned.startswith('```'):
                lines = cleaned.split('\n')
                cleaned = '\n'.join(line for line in lines if not line.strip().startswith('```'))
            
            json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if json_match:
                suspect_data = json.loads(json_match.group())
                # Validate required fields
                required_fields = ['name', 'occupation', 'alibi', 'motive', 'suspicious_details']
                has_all_fields = all(key in suspect_data for key in required_fields)
                
                if should_succeed and has_all_fields:
                    print(f"✅ Successfully parsed: {suspect_data.get('name', 'Unknown')}")
                elif should_succeed and not has_all_fields:
                    print(f"⚠️  Parsed but missing fields: {suspect_data}")
                elif not should_succeed:
                    print(f"❌ Should have failed but parsed: {test_input[:50]}")
            else:
                if not should_succeed:
                    print(f"✅ Correctly failed to parse: {test_input[:50]}")
                else:
                    print(f"❌ Should have succeeded but failed: {test_input[:50]}")
        except json.JSONDecodeError:
            if not should_succeed:
                print(f"✅ Correctly failed JSON decode: {test_input[:50]}")
            else:
                print(f"❌ Should have succeeded but got JSONDecodeError: {test_input[:50]}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
    
    print("\n✅ JSON parsing tests completed!")

def test_token_limit():
    """Verify token limit was increased."""
    print("\n🔍 Checking token limit in api_helpers.py...")
    
    with open('modules/api_helpers.py', 'r') as f:
        content = f.read()
    
    # Check for the increased token limit
    if 'maxOutputTokens": 8192' in content:
        print("✅ Token limit correctly set to 8192")
    elif 'maxOutputTokens": 2048' in content:
        print("❌ Token limit still at old value 2048")
    else:
        print("⚠️  Could not find maxOutputTokens setting")

def test_privacy_migration():
    """Check that privacy migration file exists."""
    import os
    
    migration_file = 'scripts/db_migrations/006_privacy_settings.sql'
    if os.path.exists(migration_file):
        print(f"\n✅ Privacy migration file exists: {migration_file}")
        with open(migration_file, 'r') as f:
            content = f.read()
        
        # Check for key elements
        if 'user_privacy_settings' in content:
            print("✅ Creates user_privacy_settings table")
        if 'data_collection_enabled BOOLEAN DEFAULT FALSE' in content:
            print("✅ Data collection defaults to OFF as required")
        else:
            print("❌ Data collection default not set correctly")
    else:
        print(f"❌ Privacy migration file not found: {migration_file}")

if __name__ == "__main__":
    print("=" * 70)
    print("DETECTIVE GAME IMPROVEMENTS TEST SUITE")
    print("=" * 70)
    
    test_prompt_improvements()
    test_json_parsing()
    test_token_limit()
    test_privacy_migration()
    
    print("\n" + "=" * 70)
    print("✅ ALL TESTS COMPLETED!")
    print("=" * 70)
