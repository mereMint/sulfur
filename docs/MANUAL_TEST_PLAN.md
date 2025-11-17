# Manual Test Plan

This document outlines manual tests to verify critical bot functionality.

## Test Environment Setup

1. Start bot: `.\maintain_bot.ps1`
2. Open Discord client
3. Open web dashboard: http://localhost:5000
4. Have at least 2 test users available

---

## Test 1: Voice Channel Creation (Voice Manager)

### Prerequisites
- Bot is running and online
- Test user is in a Discord server with the bot

### Steps
1. Join the "⚕ Join to Create" voice channel
2. Wait 250ms (automatic move delay)
3. Verify a new temporary voice channel was created
4. Verify user was moved to the new channel
5. Leave the voice channel
6. Wait 5 seconds (grace period)
7. Verify the temporary channel was deleted

### Expected Results
- ✅ Channel created with user's name
- ✅ User automatically moved to new channel
- ✅ Channel deleted after user leaves (5s grace period)
- ✅ No orphaned channels remain

### Database Verification
- Check `managed_voice_channels` table for proper tracking
- Verify channel cleanup on leave

---

## Test 2: Chatbot Trigger (AI Response)

### Prerequisites
- Bot is running with AI API configured
- Bot has "Read Messages" permission in test channel

### Test 2a: Direct Mention
1. In a text channel, send: `@Sulfur hello`
2. Wait for response

**Expected**: Bot responds with AI-generated message

### Test 2b: Reply to Bot
1. Find a previous bot message
2. Reply to it with any text
3. Wait for response

**Expected**: Bot responds contextually

### Test 2c: Conversation Context
1. Mention bot: `@Sulfur what's your favorite color?`
2. Wait for response
3. Within 2 minutes, mention bot again: `@Sulfur why did you choose that?`
4. Wait for response

**Expected**: Second response references the first conversation (context window)

### Test 2d: Image Analysis
1. Upload an image to the channel
2. Mention bot: `@Sulfur what do you see in this image?`
3. Wait for response

**Expected**: Bot uses vision model to analyze and describe the image

---

## Test 3: Multi-Instance Behavior

### Prerequisites
- Bot is running (instance 1)
- Secondary instance detection enabled

### Steps
1. Open a second terminal
2. Try to start bot again: `python bot.py`
3. Check console output
4. Send a message in Discord that would trigger the bot
5. Verify only ONE response is sent

### Expected Results
- ✅ Second instance detects PRIMARY_INSTANCE is running
- ✅ Second instance sets SECONDARY_INSTANCE=True
- ✅ Only primary instance responds to messages
- ✅ Console shows "SECONDARY INSTANCE" message

---

## Test 4: Shop System

### Test 4a: View Shop
1. Run command: `/shop view`
2. Verify shop embed appears with:
   - Color roles section (basic/premium/legendary)
   - Features section (dm_access, games_access, etc.)
   - Prices displayed correctly

**Expected**: Shop embed displays all items with prices

### Test 4b: Check Balance
1. Run command: `/balance`
2. Verify current balance is shown

**Expected**: Balance displayed in coins 🪙

### Test 4c: Buy Color Role
1. Run command: `/shop buy_color tier:basic`
2. Select a color from the dropdown
3. Verify:
   - Balance decreases by 500 coins
   - Color role is created and assigned
   - Success message shown

**Expected**: Color role purchased and applied

### Test 4d: Buy Feature
1. Run command: `/shop buy item:dm_access`
2. Verify:
   - Balance decreases by 2000 coins
   - Feature unlock added to database
   - Success message shown

**Expected**: Feature purchased successfully

### Test 4e: Transaction History
1. Run command: `/transactions limit:10`
2. Verify:
   - Previous shop purchases are listed
   - Transaction types, amounts, descriptions shown
   - Timestamps are correct

**Expected**: Transaction history displays correctly

---

## Test 5: Economy System

### Test 5a: Daily Reward
1. Run command: `/daily` (if implemented)
2. Verify reward is given
3. Try command again immediately
4. Verify cooldown message

**Expected**: Daily reward given once per day

### Test 5b: XP and Leveling
1. Send 10 messages in a channel
2. Wait 60 seconds between each (XP cooldown)
3. Check if level up occurs
4. Verify level up bonus is added to balance

**Expected**: XP gained, level up occurs, balance increased

---

## Test 6: Web Dashboard

### Test 6a: Main Dashboard
1. Open http://localhost:5000
2. Verify:
   - Live logs are streaming
   - Bot status is shown
   - No errors in browser console

**Expected**: Dashboard loads and shows live logs

### Test 6b: AI Dashboard
1. Navigate to http://localhost:5000/ai_dashboard
2. Verify:
   - Summary cards show totals (calls, tokens, cost)
   - Last 7 days stats shown with model/feature grouping
   - Last 30 days stats shown with cost breakdown
   - All-time stats displayed

**Expected**: AI usage data displays with proper grouping

### Test 6c: Config Editor
1. Navigate to http://localhost:5000/config
2. View current configuration
3. Make a small change (e.g., currency symbol)
4. Save changes
5. Reload bot config (or restart bot)
6. Verify change took effect

**Expected**: Config changes persist and apply

### Test 6d: Database Viewer
1. Navigate to http://localhost:5000/database
2. Select `users` table
3. Verify user data displays
4. Select `transaction_history` table
5. Verify shop transactions are logged

**Expected**: Database tables display correctly

---

## Test 7: Werwolf Game

### Prerequisites
- At least 6 users needed (can use alt accounts or bots)

### Steps
1. Run command: `/werwolf start target_players:6`
2. Have 5 other users run `/werwolf join`
3. Wait for join phase to complete
4. Verify:
   - Category "🐺 WERWOLF SPIEL 🐺" created
   - Discussion channel created
   - Roles assigned (Werwolf, Dorfbewohner, etc.)
   - Game starts properly

**Expected**: Game initializes and runs through phases

---

## Test 8: Bot Control & Maintenance

### Test 8a: Graceful Restart
1. Create file: `restart.flag` in bot directory
2. Wait 1-2 seconds
3. Verify:
   - Bot shuts down gracefully
   - Bot restarts automatically
   - Discord status goes offline then online

**Expected**: Bot restarts without errors

### Test 8b: Graceful Stop
1. Create file: `stop.flag` in bot directory
2. Wait 1-2 seconds
3. Verify:
   - Bot shuts down gracefully
   - Bot does NOT restart
   - Discord status goes offline

**Expected**: Bot stops and stays stopped

### Test 8c: Database Backup
1. Let bot run for 30+ minutes
2. Check `backups/` directory
3. Verify backup file exists with timestamp

**Expected**: Automatic backups created every 30 minutes

### Test 8d: Git Auto-Commit
1. Make a change to a tracked file
2. Wait 5 minutes
3. Check `git log`
4. Verify auto-commit occurred

**Expected**: Changes committed automatically

---

## Test 9: Error Handling

### Test 9a: Invalid Command Parameters
1. Run: `/shop buy item:invalid_item`
2. Verify error message is user-friendly

**Expected**: Graceful error handling

### Test 9b: Insufficient Balance
1. Run: `/shop buy_color tier:legendary` (if balance < 2500)
2. Verify error message about insufficient funds

**Expected**: Error message explains the issue

### Test 9c: API Failure Simulation
1. Temporarily set invalid API key in `.env`
2. Restart bot
3. Try to trigger AI response
4. Check logs for error handling

**Expected**: Bot handles API errors gracefully

---

## Test 10: Performance & Stability

### Test 10a: Load Test
1. Send 50 messages rapidly in a channel
2. Verify bot doesn't crash
3. Check memory usage in Task Manager

**Expected**: Bot handles load without crashing

### Test 10b: Long-Running Stability
1. Let bot run for 24 hours
2. Monitor logs for errors
3. Verify no memory leaks
4. Check database connection pool

**Expected**: Bot runs stable for extended periods

---

## Post-Test Cleanup

1. Stop the bot: Create `stop.flag`
2. Clean up test data:
   - Remove test user balances
   - Clear test transactions
   - Remove test color roles
3. Restore original `.env` if changed
4. Delete any test files created

---

## Test Results Log

Create a test results file after running tests:

```
# Test Results - [DATE]

## Test 1: Voice Channel Creation
- Status: [PASS/FAIL]
- Notes: [Any issues or observations]

## Test 2: Chatbot Trigger
- 2a Direct Mention: [PASS/FAIL]
- 2b Reply: [PASS/FAIL]
- 2c Context: [PASS/FAIL]
- 2d Image Analysis: [PASS/FAIL]
- Notes: [...]

[Continue for all tests...]
```

---

## Critical Issues Checklist

Before deployment, ensure:
- [ ] No crash loops on startup
- [ ] Bot responds to commands
- [ ] Database connections stable
- [ ] Voice channels create/delete properly
- [ ] Shop purchases work and log transactions
- [ ] Web dashboard accessible
- [ ] AI API calls succeed
- [ ] Multi-instance detection works
- [ ] Graceful shutdown works
- [ ] Auto-backup works
