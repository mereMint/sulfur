#!/usr/bin/env python
"""
Quick setup verification script for Sulfur Bot
Tests database, API connectivity, and configuration
"""
import os
import sys
import json
from dotenv import load_dotenv

# Load environment
load_dotenv()

def test_env_vars():
    """Check if all required environment variables are set"""
    print("=" * 60)
    print("TESTING ENVIRONMENT VARIABLES")
    print("=" * 60)
    
    required = {
        "DISCORD_BOT_TOKEN": "Discord Bot Token",
        "GEMINI_API_KEY": "Gemini API Key (or OPENAI_API_KEY)",
    }
    
    optional = {
        "OPENAI_API_KEY": "OpenAI API Key",
        "DB_HOST": "Database Host (default: localhost)",
        "DB_USER": "Database User (default: sulfur_bot_user)",
        "DB_PASS": "Database Password (default: empty)",
        "DB_NAME": "Database Name (default: sulfur_bot)",
        "BOT_PREFIX": "Bot Prefix (default: !)",
        "OWNER_ID": "Bot Owner Discord ID"
    }
    
    issues = []
    
    for var, desc in required.items():
        value = os.getenv(var)
        if value:
            print(f"✓ {var}: {desc} - SET")
        else:
            print(f"✗ {var}: {desc} - MISSING")
            issues.append(f"Missing required: {var}")
    
    # Check that at least one API key is set
    if not os.getenv("GEMINI_API_KEY") and not os.getenv("OPENAI_API_KEY"):
        print(f"✗ No AI API key found - need GEMINI_API_KEY or OPENAI_API_KEY")
        issues.append("Missing AI API key")
    
    print()
    for var, desc in optional.items():
        value = os.getenv(var)
        if value:
            print(f"  {var}: {desc} - SET")
        else:
            print(f"  {var}: {desc} - using default")
    
    return issues

def test_config_files():
    """Check if config files exist and are valid"""
    print("\n" + "=" * 60)
    print("TESTING CONFIGURATION FILES")
    print("=" * 60)
    
    issues = []
    
    # Check config.json
    config_path = "config/config.json"
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            print(f"✓ {config_path} - Valid JSON")
            print(f"  Provider: {config.get('api', {}).get('provider', 'unknown')}")
            print(f"  Bot names: {config.get('bot', {}).get('names', [])}")
        except json.JSONDecodeError as e:
            print(f"✗ {config_path} - Invalid JSON: {e}")
            issues.append(f"Invalid JSON in {config_path}")
    else:
        print(f"✗ {config_path} - NOT FOUND")
        issues.append(f"Missing {config_path}")
    
    # Check system_prompt.txt
    prompt_path = "config/system_prompt.txt"
    if os.path.exists(prompt_path):
        with open(prompt_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        if content:
            print(f"✓ {prompt_path} - Present ({len(content)} chars)")
        else:
            print(f"✗ {prompt_path} - Empty")
            issues.append("System prompt is empty")
    else:
        print(f"✗ {prompt_path} - NOT FOUND")
        issues.append(f"Missing {prompt_path}")
    
    return issues

def test_database():
    """Test database connectivity"""
    print("\n" + "=" * 60)
    print("TESTING DATABASE CONNECTION")
    print("=" * 60)
    
    issues = []
    
    try:
        import mysql.connector
        
        DB_HOST = os.getenv("DB_HOST", "localhost")
        DB_USER = os.getenv("DB_USER", "sulfur_bot_user")
        DB_PASS = os.getenv("DB_PASS", "")
        DB_NAME = os.getenv("DB_NAME", "sulfur_bot")
        
        print(f"Connecting to: {DB_USER}@{DB_HOST}/{DB_NAME}")
        
        try:
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASS,
                database=DB_NAME,
                connection_timeout=5
            )
            print("✓ Database connection successful")
            
            cursor = conn.cursor()
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"✓ Found {len(tables)} tables:")
            for table in tables:
                print(f"  - {table[0]}")
            
            cursor.close()
            conn.close()
            
        except mysql.connector.Error as err:
            print(f"✗ Database connection failed: {err}")
            print(f"  Error code: {err.errno}")
            issues.append(f"Database error: {err}")
            
            if err.errno == 2003:
                print("  → MySQL server is not running or not accessible")
                issues.append("MySQL server not running")
            elif err.errno == 1045:
                print("  → Authentication failed - check credentials")
                issues.append("Database authentication failed")
            elif err.errno == 1049:
                print("  → Database does not exist")
                issues.append(f"Database '{DB_NAME}' does not exist")
    
    except ImportError:
        print("✗ mysql-connector-python not installed")
        issues.append("Missing mysql-connector-python package")
    
    return issues

def test_api_connectivity():
    """Test API connectivity"""
    print("\n" + "=" * 60)
    print("TESTING API CONNECTIVITY")
    print("=" * 60)
    
    issues = []
    
    # Test Gemini
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        print("Testing Gemini API...")
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content("Say 'API test successful' in exactly those words.")
            print(f"✓ Gemini API working")
            print(f"  Response: {response.text[:100]}")
        except ImportError:
            print("✗ google-generativeai package not installed")
            issues.append("Missing google-generativeai package")
        except Exception as e:
            print(f"✗ Gemini API failed: {e}")
            issues.append(f"Gemini API error: {e}")
    else:
        print("  Gemini API key not set - skipping")
    
    # Test OpenAI
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        print("\nTesting OpenAI API...")
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Say 'API test successful' in exactly those words."}],
                max_tokens=50
            )
            print(f"✓ OpenAI API working")
            print(f"  Response: {response.choices[0].message.content[:100]}")
        except ImportError:
            print("✗ openai package not installed")
            issues.append("Missing openai package")
        except Exception as e:
            print(f"✗ OpenAI API failed: {e}")
            issues.append(f"OpenAI API error: {e}")
    else:
        print("  OpenAI API key not set - skipping")
    
    return issues

def main():
    """Run all tests"""
    print("\n🔍 SULFUR BOT - SETUP VERIFICATION\n")
    
    all_issues = []
    
    # Run tests
    all_issues.extend(test_env_vars())
    all_issues.extend(test_config_files())
    all_issues.extend(test_database())
    all_issues.extend(test_api_connectivity())
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if not all_issues:
        print("✓ All checks passed! Bot is ready to run.")
        return 0
    else:
        print(f"✗ Found {len(all_issues)} issue(s):\n")
        for i, issue in enumerate(all_issues, 1):
            print(f"{i}. {issue}")
        print("\nPlease fix these issues before starting the bot.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
