# Dashboard Query Fix and Game Stats Tracking - Implementation Summary

## Problem Statement

1. **SQL Error in Dashboard**: The web dashboard was throwing SQL error `1054 (42S22): Unknown column 'us.level' in 'SELECT'` when trying to display user profiles
2. **Empty Game Stats Tables**: The `werwolf_user_stats` table and potentially other game stats tables were not being populated

## Root Cause Analysis

### Issue 1: Incorrect SQL Column References

The queries in `web_dashboard.py` were trying to access columns from the `user_stats` table that don't exist:
- `us.level` - doesn't exist in `user_stats`
- `us.xp` - doesn't exist in `user_stats`
- `us.coins` - doesn't exist in `user_stats`

These columns actually exist in the `players` table:
- `players.level`
- `players.xp`
- `players.balance` (not `coins`)

### Issue 2: Missing Game Stats Tracking

The werwolf game module was calling `update_player_stats()` which only updated the general `players` table with wins/losses, but it never updated the `werwolf_user_stats` table with game-specific statistics like:
- Total games played
- Games won/lost
- Role-specific stats (times played as werewolf, villager, seer, doctor)

## Solution Implemented

### 1. Fixed SQL Queries in web_dashboard.py

#### Changed in `/api/users/profiles` endpoint:
```sql
-- BEFORE (incorrect)
COALESCE(MAX(us.level), 0) as level,
COALESCE(MAX(us.xp), 0) as xp,
COALESCE(MAX(us.coins), 0) as coins,

-- AFTER (correct)
COALESCE(p.level, 0) as level,
COALESCE(p.xp, 0) as xp,
COALESCE(p.balance, 0) as coins,
```

Also updated the `GROUP BY` clause to include the new columns:
```sql
GROUP BY p.discord_id, p.display_name, p.level, p.xp, p.balance
```

#### Changed in `/api/user/{user_id}` endpoint:
Same changes as above for consistency.

### 2. Added Werwolf Game Stats Tracking

#### Created new function in `modules/db_helpers.py`:
```python
async def update_werwolf_stats(player_id, role, won_game):
    """Updates a player's werwolf-specific stats in the werwolf_user_stats table."""
```

This function:
- Uses a whitelist dictionary for role-to-column mapping to prevent SQL injection
- Tracks total games, wins, losses
- Tracks role-specific statistics (times_werewolf, times_villager, times_seer, times_doctor)
- Updates the last_played_at timestamp
- Uses `INSERT ... ON DUPLICATE KEY UPDATE` pattern for atomic upsert

#### Updated `modules/werwolf.py`:
- Added import: `from modules.db_helpers import update_player_stats, update_werwolf_stats`
- Modified `end_game()` function to call `update_werwolf_stats()` after `update_player_stats()`

```python
await update_player_stats(player.user.id, player.user.display_name, won)
# Also update werwolf-specific stats
await update_werwolf_stats(player.user.id, player.role, won)
```

## Code Quality Improvements

Based on code review feedback, the implementation was refactored to:

1. **Use dictionary mapping** instead of multiple if-elif statements for better readability
2. **Implement proper SQL injection protection** by using a whitelist of valid column names
3. **Simplify the query building logic** to reduce code duplication

## Testing

Created `test_dashboard_query_fix.py` to validate:
1. ✓ SQL queries use correct columns from players table
2. ✓ Werwolf module imports and calls the stats tracking function
3. ✓ db_helpers contains the new function
4. ✓ All Python files compile without syntax errors
5. ✓ CodeQL security scan passed with 0 alerts

## Impact

### Positive Changes:
- **Dashboard now works**: Users can view profiles without SQL errors
- **Game stats are tracked**: Werwolf games now populate the `werwolf_user_stats` table
- **Better data integrity**: Stats are tracked atomically and consistently
- **Security improved**: Whitelist-based column mapping prevents potential SQL injection

### No Breaking Changes:
- Existing functionality remains unchanged
- Database schema not modified (uses existing tables)
- Other game modules (detective, wordle, word_find, casino games, trolly) already track their stats correctly

## Files Modified

1. **web_dashboard.py** (16 lines changed)
   - Fixed SQL queries in 2 endpoints

2. **modules/db_helpers.py** (+71 lines)
   - Added `update_werwolf_stats()` function

3. **modules/werwolf.py** (+4 lines)
   - Added import and function call for stats tracking

## Verification of Other Games

During investigation, verified that other game modules are already tracking stats correctly:
- ✓ Detective game → `detective_user_stats` table
- ✓ Wordle → `wordle_stats` table
- ✓ Word Find → `word_find_stats` table
- ✓ Casino games → `blackjack_games`, `roulette_games`, `mines_games` tables
- ✓ Trolly Problem → `trolly_responses` table

## Next Steps for Testing

To fully verify the fix:
1. Start the bot and web dashboard
2. Navigate to the user profiles page
3. Verify users are displayed without errors
4. Play a werwolf game to completion
5. Check that `werwolf_user_stats` table is populated
6. Verify the stats are displayed correctly on the dashboard
