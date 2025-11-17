import json

try:
    with open('config/config.json', 'r') as f:
        config = json.load(f)
    
    print("✅ config.json is valid JSON")
    
    # Check economy configuration
    economy = config.get('modules', {}).get('economy', {})
    print(f"✅ Economy enabled: {economy.get('enabled', False)}")
    print(f"✅ Currency: {economy.get('currency_symbol', '?')} {economy.get('currency_name', 'Unknown')}")
    
    # Check quest configuration
    quests = economy.get('quests', {})
    quest_types = quests.get('quest_types', {})
    print(f"✅ Quest types defined: {len(quest_types)}")
    for qtype, qdata in quest_types.items():
        print(f"   - {qtype}: target={qdata.get('target')}, reward={qdata.get('reward')}")
    
    # Check shop configuration
    shop = economy.get('shop', {})
    print(f"✅ Shop tiers: {len(shop.get('color_roles', {}))}")
    print(f"✅ Features: {len(shop.get('features', {}))}")
    
    # Check games configuration
    games = economy.get('games', {})
    print(f"✅ Games configured: {len(games)}")
    
    print("\n✅ All configuration validated successfully!")
    
except json.JSONDecodeError as e:
    print(f"❌ Invalid JSON: {e}")
except Exception as e:
    print(f"❌ Error: {e}")
