# Termux Debugging Guide for Message Reply Issues

## Quick Diagnosis Commands

If your bot shows as online but doesn't reply to messages, run these commands:

```bash
cd ~/sulfur

# 1. Check if bot is actually running
pgrep -af bot.py

# 2. Watch live logs (in a new Termux session)
tail -f logs/session_*.log

# 3. Check environment variables
cat .env | grep -E "DISCORD_BOT_TOKEN|GEMINI_API_KEY"

# 4. Test database connection
mariadb -u sulfur_bot_user sulfur_bot -e "SELECT 1;"

# 5. Check bot instance lock
cat bot_instance.lock
echo "Current PID: $$"
```

## Understanding the New Debug Logs

With the recent updates, the bot now provides comprehensive logging. Here's what to look for:

### 1. Normal Message Flow (Working Bot)

When everything works correctly, you should see logs like this:

```
[MSG] Received from TestUser in #general: 'sulf hello'...
[GUILD] Guild message from TestUser in #general
[TRIGGER] Chatbot trigger check: pinged=False, name_used=True, final=True
[TRIGGER] Bot names in config: ['sulf', 'sulfur']
[TRIGGER] Message words: ['sulf', 'hello']
[TRIGGER] Chatbot TRIGGERED - running chatbot handler
[CHATBOT] === Starting chatbot handler for TestUser in #general ===
[CHATBOT] Cleaned user prompt: 'hello'
[CHATBOT] Fetching chat history...
[CHATBOT] Got 10 messages from history
[CHATBOT] Calling AI API...
[AI] Getting relationship summary...
[AI] Using provider 'gemini' for user 'TestUser'
[AI] Making API request...
[Chat API] Provider: gemini, History: 10 messages
[Chat API] Cleaned history to 8 alternating messages
[Chat API] Added user prompt: 'hello'...
[Chat API] Gemini model: gemini-2.5-flash
[Chat API] Prepared 11 content items for API call
[Chat API] Sending request to Gemini API...
[Gemini API] Making request to model 'gemini-2.5-flash'...
[Gemini API] Session created, sending POST request
[Gemini API] Sending POST request with timeout=30...
[Gemini API] Got response with status 200
[Gemini API] Success - received 145 character response
[Chat API] Gemini response received successfully
[AI] Response from 'gemini': SUCCESS
[CHATBOT] Response received - saving and sending...
[CHATBOT] Processing emoji tags...
[CHATBOT] Sending response chunks to channel...
[CHATBOT] === Response sent successfully to TestUser ===
```

### 2. Diagnosing Common Issues

#### Issue: No [MSG] Log Appears

**Symptoms:**
- Bot is online but no `[MSG]` logs appear when you send messages
- No activity in logs at all

**Possible Causes:**
1. **Message Content Intent Not Enabled**
   - Go to Discord Developer Portal → Your Bot → Bot Settings
   - Enable "Message Content Intent" under Privileged Gateway Intents
   - Restart bot: `touch ~/sulfur/restart.flag`

2. **Bot is a Secondary Instance**
   - You'll see: `[GUARD] SECONDARY_INSTANCE is True - this is a secondary instance`
   - Fix: `rm -f ~/sulfur/bot_instance.lock && touch ~/sulfur/restart.flag`

#### Issue: [MSG] Appears but [TRIGGER] Shows "NOT triggered"

**Symptoms:**
```
[MSG] Received from TestUser in #general: 'hello'...
[GUILD] Guild message from TestUser in #general
[TRIGGER] Chatbot trigger check: pinged=False, name_used=False, final=False
[TRIGGER] Chatbot NOT triggered - continuing to XP processing
```

**Cause:** Bot trigger words not detected

**Solutions:**
1. Check bot names in config:
   ```bash
   cat config/config.json | grep -A 3 '"names"'
   ```
   Should show:
   ```json
   "names": [
     "sulf",
     "sulfur"
   ]
   ```

2. Use bot name in message: `sulf hello` or `sulfur help`

3. Or mention the bot: `@YourBotName hello`

4. Check trigger logic in logs - look for:
   ```
   [TRIGGER] Bot names in config: ['sulf', 'sulfur']
   [TRIGGER] Message words: ['hello', 'world']
   ```
   The message words should contain one of the bot names for `is_name_used=True`

#### Issue: [TRIGGER] Shows "TRIGGERED" but No Response

**Symptoms:**
```
[TRIGGER] Chatbot TRIGGERED - running chatbot handler
[CHATBOT] === Starting chatbot handler for TestUser in #general ===
```
...then nothing else

**Possible Causes:**

1. **Database Connection Failed**
   - Check for errors fetching chat history
   - Test: `mariadb -u sulfur_bot_user sulfur_bot -e "SELECT * FROM chat_history LIMIT 1;"`

2. **API Key Missing or Invalid**
   ```bash
   # Check if keys exist
   grep GEMINI_API_KEY .env
   
   # Test Gemini API manually
   python -c "
   import os, asyncio, aiohttp
   from dotenv import load_dotenv
   load_dotenv()
   
   async def test():
       api_key = os.getenv('GEMINI_API_KEY')
       if not api_key:
           print('ERROR: GEMINI_API_KEY not found in .env')
           return
       url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}'
       payload = {'contents': [{'parts': [{'text': 'Hello'}]}]}
       async with aiohttp.ClientSession() as session:
           async with session.post(url, json=payload, timeout=10) as resp:
               print(f'Status: {resp.status}')
               data = await resp.json()
               print(f'Response: {data}')
   
   asyncio.run(test())
   "
   ```

#### Issue: Network Error in API Call

**Symptoms:**
```
[Gemini API] Making request to model 'gemini-2.5-flash'...
[Gemini API] Network error: Cannot connect to host generativelanguage.googleapis.com:443
[Chat API] Gemini call failed with error
[CHATBOT] Sending error to user: Netzwerkfehler beim Erreichen der Gemini API
```

**Solutions:**
1. Check internet connection:
   ```bash
   ping -c 3 8.8.8.8
   ping -c 3 generativelanguage.googleapis.com
   ```

2. Check DNS resolution:
   ```bash
   nslookup generativelanguage.googleapis.com
   ```

3. Try switching networks (WiFi <-> Mobile Data)

4. Termux may need storage permissions:
   ```bash
   termux-setup-storage
   ```

5. If on restrictive network, API may be blocked. Try:
   ```bash
   # Test HTTPS connectivity
   curl -I https://generativelanguage.googleapis.com
   ```

#### Issue: API Timeout

**Symptoms:**
```
[CHATBOT] Calling AI API...
[CHATBOT] [AI] Response for channel 123456789 timed out after 30 seconds.
```

**Solutions:**
1. Increase timeout in config:
   ```bash
   nano config/config.json
   # Find "timeout" under "api" section and increase to 60
   ```

2. Check network stability:
   ```bash
   # Run continuous ping test
   ping -i 1 8.8.8.8
   # Watch for packet loss
   ```

3. Termux power saving issues:
   - Long-press Termux notification → "Acquire Wake Lock"
   - Settings → Apps → Termux → Battery → Unrestricted

#### Issue: Message Deduplication (Repeats Ignored)

**Symptoms:**
- First message works, repeat of same message doesn't
- Logs show:
  ```
  [DEDUP] Duplicate message from TestUser within 3 seconds, skipping
  ```

**This is normal behavior!** The bot ignores:
- Same message sent within 3 seconds (prevents spam)
- Messages with the same ID (prevents double-processing)

**Solution:** Wait 3+ seconds before sending the same message again, or send a different message.

## Advanced Debugging

### Enable Full Debug Logging

1. Edit the logger in bot.py to show DEBUG level:
   ```bash
   nano bot.py
   # Find line with: logger.setLevel(logging.INFO)
   # Change to: logger.setLevel(logging.DEBUG)
   ```

2. Restart bot:
   ```bash
   touch restart.flag
   ```

3. You'll now see even more detailed logs including:
   - Full message content
   - Complete API payloads
   - Database query details
   - All internal function calls

### Monitor Logs in Real-Time

Open two Termux sessions:

**Session 1 - Run Bot:**
```bash
cd ~/sulfur
source venv/bin/activate
python bot.py
```

**Session 2 - Watch Logs:**
```bash
cd ~/sulfur
tail -f logs/session_*.log | grep -E "\[MSG\]|\[TRIGGER\]|\[CHATBOT\]|\[API\]"
```

### Save Debug Session

```bash
# Capture full debug session
cd ~/sulfur
source venv/bin/activate
python bot.py 2>&1 | tee debug_session.log
```

Then send the `debug_session.log` file when asking for help.

### Check API Usage Stats

```bash
# Connect to database
mariadb -u sulfur_bot_user sulfur_bot

# Check API usage
SELECT * FROM api_usage WHERE usage_date = CURDATE();

# Check if hitting Gemini daily limit
SELECT SUM(call_count) as total_calls 
FROM api_usage 
WHERE usage_date = CURDATE() 
AND model_name LIKE 'gemini%';
```

## Quick Fixes Checklist

Before asking for help, verify:

- [ ] Message Content Intent enabled in Discord Developer Portal
- [ ] Bot invited with proper scopes and permissions
- [ ] `.env` file exists with valid DISCORD_BOT_TOKEN (no quotes)
- [ ] `.env` file has valid GEMINI_API_KEY
- [ ] MariaDB is running: `pgrep mysqld || pgrep mariadbd`
- [ ] No stale lock file: `rm -f bot_instance.lock`
- [ ] Virtual environment activated: `source venv/bin/activate`
- [ ] All dependencies installed: `pip install -r requirements.txt`
- [ ] Bot trigger words configured in config.json
- [ ] Network connectivity working: `ping 8.8.8.8`
- [ ] Wake lock acquired (long-press Termux notification)
- [ ] Battery optimization disabled for Termux

## Common Log Patterns

### Pattern: Everything Works
```
[MSG] Received → [TRIGGER] TRIGGERED → [CHATBOT] Starting → [AI] Using provider → [Gemini API] Success → [CHATBOT] Response sent
```

### Pattern: Trigger Not Detected
```
[MSG] Received → [TRIGGER] NOT triggered → [No chatbot execution]
```
**Fix:** Use bot name or mention in message

### Pattern: Database Issue
```
[MSG] Received → [TRIGGER] TRIGGERED → [CHATBOT] Starting → [ERROR] Database connection failed
```
**Fix:** Start MariaDB, check credentials

### Pattern: Network Issue
```
[MSG] Received → [TRIGGER] TRIGGERED → [CHATBOT] Starting → [Gemini API] Network error
```
**Fix:** Check internet, DNS, firewall

### Pattern: API Key Issue
```
[MSG] Received → [TRIGGER] TRIGGERED → [CHATBOT] Starting → [Gemini API] HTTP 403/401
```
**Fix:** Verify GEMINI_API_KEY in .env, check API quota

## Getting Help

When reporting issues, include:

1. **System Info:**
   ```bash
   python -V
   echo $TERMUX_VERSION
   uname -m
   ```

2. **Recent Logs (last 50 lines with filters):**
   ```bash
   tail -n 50 logs/session_*.log | grep -E "\[MSG\]|\[TRIGGER\]|\[CHATBOT\]|\[API\]|\[ERROR\]"
   ```

3. **Configuration Check:**
   ```bash
   cat config/config.json | grep -A 5 '"names"'
   cat .env | grep -E "^[A-Z]" | sed 's/=.*/=***/'  # Hides sensitive values
   ```

4. **Package Versions:**
   ```bash
   source venv/bin/activate
   pip list | grep -E "discord|aiohttp|mysql"
   ```

5. **Database Status:**
   ```bash
   pgrep mysqld && echo "MariaDB running" || echo "MariaDB NOT running"
   mariadb -u sulfur_bot_user sulfur_bot -e "SHOW TABLES;"
   ```

This information will help diagnose the issue much faster!
