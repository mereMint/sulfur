# Twitch Bot Setup Guide

This guide will help you set up and configure the Sulfur Twitch bot integration.

## Features

✅ **Chat Monitoring** - Monitor and log all chat messages
✅ **Custom Commands** - Create unlimited custom commands with cooldowns
✅ **User Tracking** - Track user activity, first seen times, and statistics
✅ **Spam Protection** - Automatic spam detection and filtering
✅ **Auto Shoutout** - Welcome new followers automatically
✅ **Stream Status** - Track viewer count, uptime, and stream status
✅ **Dashboard Control** - Full configuration via web dashboard
✅ **Modular Design** - Enable/disable features independently

## Prerequisites

1. **Twitch Account for Your Bot**
   - Create a separate Twitch account for your bot
   - Example: If your channel is `mychannel`, create `mychannel_bot`

2. **OAuth Token**
   - Visit https://twitchapps.com/tmi/
   - Log in with your **bot account** (not your main account!)
   - Copy the OAuth token (starts with `oauth:`)
   - Keep this token secret!

3. **(Optional) Twitch Developer Application**
   - For advanced features (follower tracking, stream status)
   - Go to https://dev.twitch.tv/console
   - Create a new application
   - Copy the **Client ID** and **Client Secret**

## Quick Setup

### 1. Access the Dashboard

1. Open the Sulfur Dashboard in your browser
2. Navigate to **External > Twitch** from the top menu
3. You should see the Twitch Bot configuration page

### 2. Configure Basic Settings

In the **Setup** tab, fill in:

- **Twitch Channel Name**: Your channel name (without the #)
  - Example: `mychannel`
- **Bot Username**: Your bot's Twitch username
  - Example: `mychannel_bot`
- **OAuth Token**: Paste the token from twitchapps.com
  - Example: `oauth:abc123def456...`

### 3. (Optional) Add API Credentials

For advanced features, add:

- **Client ID**: From Twitch Developer Console
- **Client Secret**: From Twitch Developer Console

These enable:
- Follower tracking
- Stream status monitoring
- Viewer count updates

### 4. Enable the Bot

1. Check the **Enable Twitch Bot** checkbox
2. Click **Save Configuration**
3. Click the **Start Bot** button at the top

✅ The bot should now connect to your channel!

## Features Configuration

### Chat Monitoring
- Logs all chat messages
- Tracks user activity
- Monitors chatters

### Custom Commands
- Use variables: `{user}`, `{username}`, `{uptime}`
- Set cooldowns (in seconds)
- Enable/disable individually

**Example Commands:**
```
!discord
Response: Join our Discord: https://discord.gg/your-server
Cooldown: 30s

!lurk
Response: Thanks for lurking @{user}! Enjoy the stream!
Cooldown: 300s

!uptime
Response: Stream has been live for {uptime}
Cooldown: 30s
```

### Spam Protection

Automatically detects and filters:
- **Message Rate**: Max messages per minute per user
- **Excessive Caps**: Messages with too many CAPITAL LETTERS
- **Link Spam**: Unwanted URLs in chat

Configure in the **Features** tab.

### Auto Shoutout

Automatically welcome new followers with a customizable message.

## Dashboard Usage

### Starting the Bot

1. Go to **External > Twitch**
2. Ensure configuration is saved
3. Click **Start Bot**
4. Status should change to "Running"

### Stopping the Bot

1. Click **Stop Bot**
2. Status changes to "Stopped"

### Adding Commands

1. Go to the **Commands** tab
2. Click **Add Command**
3. Fill in:
   - Command (e.g., `!discord`)
   - Response
   - Cooldown (seconds)
   - Enable/Disable
4. Click **Add Command**

### Viewing Statistics

Go to the **Statistics** tab to see:
- Total messages processed
- Commands executed
- Unique chatters
- Stream uptime

## Advanced Configuration

### File Locations

All configuration is stored in JSON files:

```
config/
  ├── twitch_config.json      # Main configuration
  ├── twitch_commands.json    # Custom commands
  └── twitch_state.json       # Persistent state (followers, etc.)
```

### Manual Configuration

You can edit `config/twitch_config.json` directly:

```json
{
  "enabled": true,
  "channel": "your_channel",
  "bot_username": "your_bot",
  "oauth_token": "oauth:your_token",
  "client_id": "your_client_id",
  "client_secret": "your_client_secret",
  "features": {
    "chat_monitoring": true,
    "commands": true,
    "user_tracking": true,
    "follows_tracking": true,
    "auto_category": false,
    "spam_protection": true,
    "auto_shoutout": true
  },
  "spam_protection": {
    "max_messages_per_minute": 20,
    "timeout_duration": 120,
    "link_protection": true,
    "caps_protection": true
  }
}
```

### Command Variables

Use these variables in command responses:

- `{user}` or `{username}` - The user who triggered the command
- `{uptime}` - Current stream uptime

Example:
```
Command: !hello
Response: Welcome @{user} to the stream!
```

## Troubleshooting

### Bot Won't Connect

**Issue:** Bot status stays "Stopped" or shows an error

**Solutions:**
1. **Check OAuth Token**
   - Make sure it starts with `oauth:`
   - Regenerate at https://twitchapps.com/tmi/
   - Use the **bot account**, not your main account

2. **Check Username**
   - Must match the account used for OAuth
   - Case doesn't matter (lowercase recommended)

3. **Check Channel Name**
   - Don't include the `#` symbol
   - Use your exact Twitch username

### Commands Not Working

**Issue:** Bot is running but commands don't respond

**Solutions:**
1. **Check Features Tab**
   - Ensure "Custom Commands" is enabled

2. **Check Command Settings**
   - Command must be enabled
   - Check cooldown hasn't been exceeded

3. **Check Bot Connection**
   - Verify bot status shows "Running"
   - Check that "Stream Status" shows correct info

### No Stream Status Updates

**Issue:** Stream status always shows "Offline" or no viewer count

**Solution:**
- Add **Client ID** and **Client Secret** in Setup tab
- These are required for Twitch API access
- Get them from https://dev.twitch.tv/console

### High Spam Protection

**Issue:** Bot is blocking legitimate messages

**Solution:**
1. Go to **Features** tab
2. Adjust spam protection settings:
   - Increase `max_messages_per_minute`
   - Disable `link_protection` if needed
   - Disable `caps_protection` if needed

## Security Best Practices

🔒 **Never Share Your OAuth Token**
- Treat it like a password
- Regenerate if compromised

🔒 **Never Share Client Secret**
- Keep it secret in configuration
- Don't commit to public repositories

🔒 **Use a Separate Bot Account**
- Don't use your main account's OAuth
- Easier to manage permissions

🔒 **Regularly Regenerate Tokens**
- Regenerate OAuth monthly
- Update configuration after regeneration

## API Endpoints

For advanced users and integrations:

```bash
# Get bot status
GET /api/twitch/status

# Start bot
POST /api/twitch/start

# Stop bot
POST /api/twitch/stop

# Update configuration
POST /api/twitch/config
Body: {"channel": "newchannel", "enabled": true}

# Add command
POST /api/twitch/command/add
Body: {"command": "!test", "response": "Hello!", "cooldown": 30}

# Delete command
POST /api/twitch/command/delete
Body: {"command": "!test"}

# Update features
POST /api/twitch/features
Body: {"spam_protection": true, "auto_shoutout": false}
```

## Planned Features

🚧 **Coming Soon:**
- Auto category changing from game images
- Raid/host detection and responses
- Bits/subscription alerts
- Chat games and mini-games
- Viewer rewards integration
- Multi-channel support
- Advanced analytics

## Support

If you encounter issues:

1. Check the **Console** tab in the dashboard for errors
2. Review the logs in `logs/` directory
3. Ensure your configuration is correct
4. Try regenerating your OAuth token
5. Restart the bot from the dashboard

## Example Workflow

Here's a complete setup example:

1. **Create Bot Account**
   - Main channel: `coolgamer123`
   - Bot account: `coolgamer123_bot`

2. **Get OAuth Token**
   - Go to https://twitchapps.com/tmi/
   - Log in as `coolgamer123_bot`
   - Copy token: `oauth:abc123def456...`

3. **Configure Dashboard**
   - Channel: `coolgamer123`
   - Bot Username: `coolgamer123_bot`
   - OAuth: `oauth:abc123def456...`
   - Enable bot: ✅

4. **Add Commands**
   - `!discord` → "Join us: https://discord.gg/mycommunity"
   - `!twitter` → "Follow on Twitter: @coolgamer123"
   - `!uptime` → "Stream uptime: {uptime}"

5. **Start Bot**
   - Click "Start Bot"
   - Verify status: "Running" ✅

6. **Test**
   - Type `!discord` in chat
   - Bot should respond!

## Conclusion

The Sulfur Twitch bot provides powerful automation for your stream while being easy to configure through the web dashboard. All features are modular and can be enabled/disabled as needed.

Happy streaming! 🎮✨
