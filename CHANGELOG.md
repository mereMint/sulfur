# Changelog - November 16, 2025

## High Priority Bug Fixes & Features

### 🐺 Werwolf Game Fixes

#### Fixed: Game Startup & Player Detection
**Problem:** Game was not detecting players correctly and would fail to start with "Niemand ist beigetreten" error even when players were in the lobby.

**Solution:**
- Added game starter to player list immediately upon game creation
- Enhanced player detection by scanning lobby VC members before game start
- Improved player count validation to support 1+ players (with bot filling)

**Files Changed:**
- `bot.py` - Lines 2040-2055 (ww_start function)
- `bot.py` - Line 2046 (added `game.add_player(author)`)

#### Fixed: Lobby Cleanup After Game Ends
**Problem:** Game channels and category were not being deleted properly after game completion, leaving orphaned channels.

**Solution:**
- Improved error handling in cleanup process
- Added specific exception handling for NotFound and Forbidden errors
- Better logging for cleanup debugging

**Files Changed:**
- `modules/werwolf.py` - Lines 620-642 (end_game function)
- Added proper exception handling for Discord API errors
- Improved category deletion with better error messages

#### Fixed: Config Parameter Bug
**Problem:** `end_game()` was being called without config parameter in some cases, causing crashes.

**Solution:**
- Made config parameter optional in end_game method
- Added checks for config existence before using it
- Prevented stat recording when game is cancelled before start

**Files Changed:**
- `modules/werwolf.py` - Lines 598-625
- `bot.py` - Line 2088 (updated end_game call)

### 📊 Wrapped Opt-In System

#### New Feature: User Registration for Wrapped
**Description:** Users can now opt-in to receive monthly Wrapped summaries instead of everyone receiving them automatically.

**New Commands:**
- `/wrapped-register` - Register to receive Wrapped summaries
- `/wrapped-unregister` - Opt-out of Wrapped summaries  
- `/wrapped-status` - Check your registration status

**Benefits:**
- Respects user privacy and preferences
- Reduces bot DM spam for uninterested users
- Better user experience with clear opt-in process

**Files Changed:**
- `bot.py` - Lines 2006-2086 (new commands)
- `bot.py` - Lines 723-738 (updated distribution logic)
- `bot.py` - Line 137 (added new imports)

**Database Changes:**
- New table: `wrapped_registrations`
- Fields: `user_id`, `username`, `registered_at`, `opted_out`, `last_updated`
- Migration script: `scripts/migrations/add_wrapped_opt_in.sql`

**New Database Functions:**
- `register_for_wrapped(user_id, username)` - Register user
- `unregister_from_wrapped(user_id)` - Unregister user
- `is_registered_for_wrapped(user_id)` - Check status
- `get_wrapped_registrations()` - Get all registered users

**Files Changed:**
- `modules/db_helpers.py` - Lines 1204-1302 (new functions)

### 🛠️ PowerShell Script Analyzer Fixes

#### Fixed: Script Analyzer Warnings in check_errors.ps1
**Problems:**
- Unused variable `$output`
- Unused variable `$result`
- Overwriting automatic variable `$matches`

**Solutions:**
- Replaced `$output =` with `$null =` for py_compile calls
- Removed unused `$result` assignment, using pipeline instead
- Renamed `$matches` to `$searchResults` to avoid conflicts

**Files Changed:**
- `check_errors.ps1` - Lines 16, 136, 161

### 📝 Documentation Updates

**New Files:**
- `TODO.md` - Comprehensive feature roadmap
- `docs/TEST_PLAN.md` - Detailed testing procedures
- `scripts/migrations/add_wrapped_opt_in.sql` - Database migration

## Summary of Changes

### Files Modified: 4
1. `bot.py` - Werwolf fixes, Wrapped opt-in commands
2. `modules/werwolf.py` - Game cleanup improvements
3. `modules/db_helpers.py` - Wrapped registration functions
4. `check_errors.ps1` - Script analyzer fixes

### Files Created: 3
1. `TODO.md` - Feature planning
2. `docs/TEST_PLAN.md` - Testing documentation
3. `scripts/migrations/add_wrapped_opt_in.sql` - Database schema

### Database Schema Changes: 1
- New table: `wrapped_registrations` with proper indexes

## Migration Steps

1. **Database Migration:**
   ```bash
   mysql -u sulfur_bot_user -p sulfur_bot < scripts/migrations/add_wrapped_opt_in.sql
   ```

2. **Restart Bot:**
   ```bash
   python bot.py
   ```

3. **Sync Slash Commands:**
   Commands will auto-sync on bot restart. Verify with:
   - `/wrapped-register`
   - `/wrapped-unregister`
   - `/wrapped-status`

4. **Test Werwolf:**
   - Use `/ww start` in a test channel
   - Verify player detection works
   - Complete a game and verify cleanup

## Known Issues & Future Work

See `TODO.md` for complete roadmap. Priority items:
- AI Vision support for images
- Emoji management with AI descriptions
- Multi-model AI support
- Conversation follow-up system
- AI dashboard admin command
- Web dashboard expansion

## Breaking Changes

**None** - All changes are backwards compatible.

## Notes

- Wrapped distribution will only send to registered users starting from the next scheduled distribution
- Existing game functionality is preserved with improvements
- No config file changes required
- Fully tested for syntax errors (no Python or PowerShell errors)
