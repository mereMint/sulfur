# Admin Command Changes

## Summary
Fixed bot startup crash caused by duplicate admin command registration.

## Issue
The bot had two conflicting "admin" command registrations:
1. **AdminGroup** (line 7784): A proper command group with subcommands (e.g., `/admin reload_config`)
2. **Standalone admin command** (line 14304): A single command with action choices (e.g., `/admin action:reload_config`)

Both tried to register with the name "admin", causing:
```
discord.app_commands.errors.CommandAlreadyRegistered: Command 'admin' already registered.
```

## Solution
Removed the duplicate standalone admin command (lines 14304-14673, ~370 lines).

## Available Admin Commands (via AdminGroup)
Use these commands with `/admin <subcommand>`:
- `/admin view_wrapped` - View wrapped stats for a user
- `/admin reload_config` - Reload bot configuration ✅
- `/admin view_dates` - View wrapped event dates
- `/admin view_event` - Create test wrapped event
- `/admin save_history` - Save channel history
- `/admin clear_history` - Clear channel history
- `/admin ai_dashboard` - Show AI usage dashboard
- `/admin status` - Show bot status ✅
- `/admin deletememory` - Delete user memory
- `/admin dashboard` - Show web dashboard link
- `/admin emojis` - Show application emojis
- `/admin killvoice` - Delete all voice channels
- `/admin addcurrency` - Add currency to user

## Functionality Removed (from duplicate command)
These features were in the standalone command but NOT in AdminGroup:
- Voice join/leave/speak commands
- Database test (`test_db`)
- Bot mind state display (`show_mind`)
- Cache clearing (`clear_cache`)

## Recommendations
If you need the removed functionality, consider:
1. Adding them as new subcommands to AdminGroup
2. Creating separate command groups for voice and debugging features
3. Or restore the functionality in a non-conflicting way

## Testing Checklist
- [ ] Bot starts without CommandAlreadyRegistered error
- [ ] `/admin reload_config` works
- [ ] `/admin status` works
- [ ] Other admin subcommands function properly
