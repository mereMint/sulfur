#!/usr/bin/env python3
"""Test script for web dashboard API endpoints"""

import sys
import os
import json

# Set up path
sys.path.insert(0, '/home/runner/work/sulfur/sulfur')
os.chdir('/home/runner/work/sulfur/sulfur')

# Create necessary directories
os.makedirs('logs', exist_ok=True)
os.makedirs('config', exist_ok=True)

# Create a minimal bot_status.json
with open('config/bot_status.json', 'w') as f:
    json.dump({'status': 'Testing', 'message': 'Running tests'}, f)

# Import after path setup
from unittest.mock import Mock, patch, MagicMock

# Mock database operations
mock_conn = MagicMock()
mock_cursor = MagicMock()
mock_cursor.fetchall.return_value = []
mock_conn.cursor.return_value = mock_cursor

mock_pool = MagicMock()
mock_pool.get_connection.return_value = mock_conn

# Patch before importing web_dashboard
import modules.db_helpers as db_helpers
db_helpers.db_pool = mock_pool

import web_dashboard

# Test the enhanced API endpoint
def test_ai_usage_api():
    """Test the enhanced AI usage API with mock data"""
    print("\n=== Testing /api/ai-usage endpoint ===")
    
    # Mock data that would come from database
    mock_stats = [
        {
            'model_name': 'gemini-2.5-flash',
            'feature': 'chat',
            'total_calls': 150,
            'total_input_tokens': 5000,
            'total_output_tokens': 3000,
            'total_cost': 0.08
        },
        {
            'model_name': 'gemini-2.5-flash',
            'feature': 'werwolf',
            'total_calls': 50,
            'total_input_tokens': 2000,
            'total_output_tokens': 1500,
            'total_cost': 0.035
        },
        {
            'model_name': 'gpt-4o-mini',
            'feature': 'chat',
            'total_calls': 75,
            'total_input_tokens': 3000,
            'total_output_tokens': 2000,
            'total_cost': 0.15
        }
    ]
    
    # Mock the async function
    async def mock_get_stats(days):
        return mock_stats
    
    with patch('modules.db_helpers.get_ai_usage_stats', mock_get_stats):
        with web_dashboard.app.test_client() as client:
            response = client.get('/api/ai-usage?days=30')
            data = json.loads(response.data)
            
            print(f"Status: {response.status_code}")
            print(f"Response status: {data.get('status')}")
            
            if 'by_model' in data:
                print("\n✓ Data grouped by model:")
                for model, info in data['by_model'].items():
                    print(f"  - {model}: {info['calls']} calls, ${info['cost']:.4f}")
                    for feature, fdata in info['features'].items():
                        print(f"    └─ {feature}: {fdata['calls']} calls")
            
            if 'by_feature' in data:
                print("\n✓ Data grouped by feature:")
                for feature, info in data['by_feature'].items():
                    print(f"  - {feature}: {info['calls']} calls, ${info['cost']:.4f}")
            
            if 'summary' in data:
                print(f"\n✓ Summary:")
                print(f"  Total calls: {data['summary']['total_calls']}")
                print(f"  Total tokens: {data['summary']['total_tokens']}")
                print(f"  Total cost: ${data['summary']['total_cost']:.4f}")
            
            return response.status_code == 200

def test_maintenance_logs_api():
    """Test the maintenance logs API"""
    print("\n=== Testing /api/maintenance/logs endpoint ===")
    
    with web_dashboard.app.test_client() as client:
        response = client.get('/api/maintenance/logs')
        data = json.loads(response.data)
        
        print(f"Status: {response.status_code}")
        print(f"Response status: {data.get('status')}")
        print(f"Logs found: {len(data.get('logs', []))}")
        
        return response.status_code == 200

def test_bot_status_api():
    """Test the bot status API"""
    print("\n=== Testing /api/bot-status endpoint ===")
    
    with web_dashboard.app.test_client() as client:
        response = client.get('/api/bot-status')
        data = json.loads(response.data)
        
        print(f"Status: {response.status_code}")
        print(f"Bot status: {data.get('status')}")
        
        return response.status_code == 200

def test_control_buttons():
    """Test the control button endpoints"""
    print("\n=== Testing Control Button APIs ===")
    
    with web_dashboard.app.test_client() as client:
        # Test restart endpoint
        response = client.post('/api/restart-bot')
        data = json.loads(response.data)
        print(f"Restart API: {response.status_code} - {data.get('message', '')[:50]}")
        
        # Test stop endpoint  
        response = client.post('/api/stop-bot')
        data = json.loads(response.data)
        print(f"Stop API: {response.status_code} - {data.get('message', '')[:50]}")
        
        # Test sync-db endpoint
        response = client.post('/api/sync-db')
        data = json.loads(response.data)
        print(f"Sync DB API: {response.status_code} - {data.get('message', '')[:50]}")
        
        # Test update endpoint
        response = client.post('/api/update-bot')
        data = json.loads(response.data)
        print(f"Update API: {response.status_code} - {data.get('message', '')[:50]}")
        
        return True

if __name__ == '__main__':
    print("=" * 60)
    print("Web Dashboard API Test Suite")
    print("=" * 60)
    
    results = []
    
    try:
        results.append(("AI Usage API", test_ai_usage_api()))
    except Exception as e:
        print(f"✗ AI Usage API test failed: {e}")
        results.append(("AI Usage API", False))
    
    try:
        results.append(("Maintenance Logs API", test_maintenance_logs_api()))
    except Exception as e:
        print(f"✗ Maintenance Logs API test failed: {e}")
        results.append(("Maintenance Logs API", False))
    
    try:
        results.append(("Bot Status API", test_bot_status_api()))
    except Exception as e:
        print(f"✗ Bot Status API test failed: {e}")
        results.append(("Bot Status API", False))
    
    try:
        results.append(("Control Buttons", test_control_buttons()))
    except Exception as e:
        print(f"✗ Control Buttons test failed: {e}")
        results.append(("Control Buttons", False))
    
    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    sys.exit(0 if passed == total else 1)
