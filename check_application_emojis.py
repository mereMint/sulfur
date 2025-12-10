#!/usr/bin/env python3
"""
Test script to check application emojis and verify emoji system setup.
This helps diagnose emoji display issues.
"""

import asyncio
import os
import sys
import json
import discord
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_application_emojis():
    """Test application emoji fetching and display."""
    
    # Setup Discord client
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
    
    @client.event
    async def on_ready():
        print(f"✓ Logged in as {client.user}")
        print(f"  User ID: {client.user.id}")
        print()
        
        try:
            # Fetch application emojis
            print("Fetching application emojis...")
            app_emojis = await client.fetch_application_emojis()
            
            print(f"\n{'='*60}")
            print(f"APPLICATION EMOJIS ({len(app_emojis)} total)")
            print(f"{'='*60}\n")
            
            if not app_emojis:
                print("⚠️  No application emojis found!")
                print("   The bot needs emojis uploaded to its application.")
                print("   Visit: https://discord.com/developers/applications")
                print("   Select your bot → Emojis → Upload emojis")
            else:
                for emoji in app_emojis:
                    emoji_type = "Animated" if emoji.animated else "Static"
                    print(f"• {emoji.name:<25} ({emoji_type})")
                    print(f"  ID: {emoji.id}")
                    print(f"  Short format:  :{emoji.name}:")
                    if emoji.animated:
                        print(f"  Full format:   <a:{emoji.name}:{emoji.id}>")
                    else:
                        print(f"  Full format:   <:{emoji.name}:{emoji.id}>")
                    print()
            
            # Load configured emojis from server_emojis.json
            config_path = "config/server_emojis.json"
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    emoji_config = json.load(f)
                    configured_emojis = emoji_config.get('emojis', {})
                
                print(f"\n{'='*60}")
                print(f"CONFIGURED EMOJIS ({len(configured_emojis)} total)")
                print(f"{'='*60}\n")
                
                # Check which configured emojis exist
                app_emoji_names = {e.name for e in app_emojis}
                missing = []
                found = []
                
                for emoji_name in configured_emojis.keys():
                    if emoji_name in app_emoji_names:
                        found.append(emoji_name)
                        print(f"✓ {emoji_name:<25} (EXISTS in application emojis)")
                    else:
                        missing.append(emoji_name)
                        print(f"✗ {emoji_name:<25} (MISSING from application emojis)")
                
                print(f"\n{'='*60}")
                print(f"SUMMARY")
                print(f"{'='*60}")
                print(f"✓ Found: {len(found)}")
                print(f"✗ Missing: {len(missing)}")
                
                if missing:
                    print(f"\n⚠️  WARNING: {len(missing)} configured emojis are missing!")
                    print("   These emojis need to be uploaded to the bot's application.")
                    print("   Until then, the AI won't be able to use them properly.")
                    print(f"\n   Missing emojis: {', '.join(missing)}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await client.close()
    
    # Get bot token
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        print("❌ Error: DISCORD_BOT_TOKEN not found in environment")
        print("   Create a .env file with your bot token")
        return
    
    # Validate token format
    token = token.strip()
    if not token:
        print("❌ Error: Bot token is empty")
        return
    
    # Basic token format validation (Discord tokens have specific structure)
    if len(token) < 50:
        print("⚠️  Warning: Token seems too short (Discord bot tokens are typically 59+ characters)")
        print("   The token may be invalid or incomplete")
    
    # Run bot
    try:
        await client.start(token)
    except discord.LoginFailure:
        print("❌ Error: Invalid bot token")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("="*60)
    print("SULFUR BOT - APPLICATION EMOJI TESTER")
    print("="*60)
    print()
    
    asyncio.run(test_application_emojis())
