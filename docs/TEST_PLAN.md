# Test Plan for Sulfur Bot Updates
# Date: November 16, 2025

## 1. Werwolf Game Fixes

### Test Case 1.1: Game Startup with Players
**Steps:**
1. Use `/ww start` in a text channel
2. Have multiple users join the voice lobby
3. Wait for auto-start or click "Sofort starten"
4. Verify game starts with all lobby members

**Expected Result:**
- All users in lobby are added to the game
- Game starts successfully
- Roles are assigned correctly
- No "Niemand ist beigetreten" error

### Test Case 1.2: Game Startup with Only Starter
**Steps:**
1. Use `/ww start` in a text channel
2. Don't have anyone join the lobby (or leave before start)
3. Wait for auto-start timer

**Expected Result:**
- If configured with `default_target_players`, bots fill the game
- If not configured for bots and no players, game cancels with message
- Channels are cleaned up properly

### Test Case 1.3: Lobby Cleanup After Game
**Steps:**
1. Start and complete a full Werwolf game
2. Let the game end naturally (wolves or villagers win)
3. Observe cleanup process

**Expected Result:**
- Game summary is posted to original channel
- All game channels (text, voice) are deleted
- Category is deleted
- No error messages in logs
- No orphaned channels remain

### Test Case 1.4: Lobby Cleanup on Early Exit
**Steps:**
1. Start a Werwolf game
2. Have all players leave the voice channel mid-game
3. Observe cleanup process

**Expected Result:**
- Game detects empty VC
- Sends "Alle Spieler haben den Voice-Channel verlassen" message
- Cleans up all channels and category
- Game is removed from active games list

## 2. Wrapped Opt-In System

### Test Case 2.1: Register for Wrapped
**Steps:**
1. Use `/wrapped-register` command
2. Check response

**Expected Result:**
- Success message with green embed
- Explanation of Wrapped features
- User is added to `wrapped_registrations` table

### Test Case 2.2: Check Wrapped Status (Registered)
**Steps:**
1. Register with `/wrapped-register`
2. Use `/wrapped-status` command

**Expected Result:**
- Shows "registered" status with green embed
- Displays next Wrapped timing info

### Test Case 2.3: Unregister from Wrapped
**Steps:**
1. Register with `/wrapped-register`
2. Use `/wrapped-unregister` command
3. Check response

**Expected Result:**
- Success message with orange embed
- User's `opted_out` flag is set to TRUE in database

### Test Case 2.4: Check Wrapped Status (Unregistered)
**Steps:**
1. Unregister or never register
2. Use `/wrapped-status` command

**Expected Result:**
- Shows "not registered" status with red embed
- Prompts to use `/wrapped-register`

### Test Case 2.5: Wrapped Distribution (Integration Test)
**Steps:**
1. Have some users register, some not
2. Wait for next Wrapped distribution date (or manually trigger)
3. Check who receives Wrapped DMs

**Expected Result:**
- Only registered users (opted_out = FALSE) receive Wrapped
- Unregistered users receive nothing
- No errors in logs

## 3. Database Migration

### Test Case 3.1: Run Migration
**Steps:**
1. Connect to MySQL database
2. Run `scripts/migrations/add_wrapped_opt_in.sql`
3. Verify table creation

**Expected Result:**
- `wrapped_registrations` table is created
- Columns: `user_id`, `username`, `registered_at`, `opted_out`, `last_updated`
- Indexes on `opted_out` and `registered_at`

**SQL to verify:**
```sql
SHOW CREATE TABLE wrapped_registrations;
SELECT * FROM wrapped_registrations;
```

## 4. General Bot Functionality

### Test Case 4.1: Bot Startup
**Steps:**
1. Start the bot with `python bot.py`
2. Check logs for errors

**Expected Result:**
- No import errors
- Database connection successful
- All slash commands sync properly
- No syntax errors

### Test Case 4.2: Import Validation
**Steps:**
1. Run Python syntax check: `python -m py_compile bot.py`
2. Run syntax check on modules: `python -m py_compile modules/werwolf.py modules/db_helpers.py`

**Expected Result:**
- No compilation errors
- All imports resolve correctly

## 5. PowerShell Script Fixes

### Test Case 5.1: Run Error Check Script
**Steps:**
1. Run `.\check_errors.ps1` in PowerShell
2. Check for script analyzer warnings

**Expected Result:**
- No "variable assigned but never used" warnings
- No "automatic variable" warnings
- Script runs without errors

## Testing Checklist

- [ ] Test Case 1.1: Game Startup with Players
- [ ] Test Case 1.2: Game Startup with Only Starter
- [ ] Test Case 1.3: Lobby Cleanup After Game
- [ ] Test Case 1.4: Lobby Cleanup on Early Exit
- [ ] Test Case 2.1: Register for Wrapped
- [ ] Test Case 2.2: Check Wrapped Status (Registered)
- [ ] Test Case 2.3: Unregister from Wrapped
- [ ] Test Case 2.4: Check Wrapped Status (Unregistered)
- [ ] Test Case 2.5: Wrapped Distribution
- [ ] Test Case 3.1: Run Migration
- [ ] Test Case 4.1: Bot Startup
- [ ] Test Case 4.2: Import Validation
- [ ] Test Case 5.1: Run Error Check Script

## Notes

- All tests should be performed in a development/test Discord server first
- Database backups should be taken before running migrations
- Monitor bot logs during all tests for unexpected errors
- Check Discord rate limits when testing multiple commands rapidly
