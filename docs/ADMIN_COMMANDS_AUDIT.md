# Admin Commands Audit

This document audits all admin/utility commands for potential migration to the web dashboard.

## Commands Analysis

### Already Dashboard-Compatible
These commands could be migrated to the web dashboard:

1. **`/ai_dashboard`** - ✅ **MIGRATE TO DASHBOARD**
   - Shows AI API status and usage
   - Already has a web dashboard page at `/ai_dashboard`
   - Should be removed from Discord and only accessible via web
   - **Action**: Remove Discord command, keep only web version

2. **`/reload_config`** - ✅ **MIGRATE TO DASHBOARD**
   - Reloads config.json and system prompt
   - Could be a button on the config editor page
   - **Action**: Add "Reload Config" button to `/config` dashboard page

3. **`/status`** - ✅ **MIGRATE TO DASHBOARD**
   - Shows uptime, version, git commit
   - Could be on main dashboard page
   - **Action**: Add status section to main dashboard (`/`)

4. **`/save_history`** - ⚠️ **PARTIAL MIGRATION**
   - Saves channel history to database
   - Could add a feature in dashboard to manage history per channel
   - **Action**: Keep Discord command for convenience, add dashboard page for bulk management

5. **`/clear_history`** - ⚠️ **PARTIAL MIGRATION**
   - Clears channel history from database
   - Should be available in dashboard for safety
   - **Action**: Keep Discord command, add to dashboard with confirmation

### Keep as Discord Commands
These are better suited for Discord:

6. **`/view_wrapped`** - ❌ **KEEP IN DISCORD**
   - Admin-only preview of Wrapped for a user
   - Needs to send DMs to users
   - Better as Discord command for testing

7. **`/view_dates`** - ❌ **KEEP IN DISCORD**
   - Shows next Wrapped event dates
   - Quick reference for admins
   - Low complexity, fine in Discord

8. **`/view_event`** - ❌ **KEEP IN DISCORD**
   - Creates test Discord event
   - Must stay in Discord (creates Discord events)
   - Testing feature

9. **`/deletememory`** - ❌ **KEEP IN DISCORD**
   - Deletes relationship memory for a user
   - User-facing, not admin-only
   - Could be user self-service

10. **`/dashboard`** - ❌ **KEEP IN DISCORD**
    - Shows link to web dashboard
    - Entry point to dashboard
    - Must stay in Discord

## Migration Plan

### Priority 1: Remove Duplicate Commands
- Remove `/ai_dashboard` Discord command (already has web page)

### Priority 2: Add Dashboard Controls
- Add "Reload Config" button to config editor page
- Add bot status section to main dashboard
- Add channel history management page

### Priority 3: Future Enhancements
- Database viewer improvements
- User management interface
- Transaction history viewer
- Feature unlock management

## Web Dashboard Pages Needed

### Existing Pages
- ✅ `/` - Main dashboard with logs
- ✅ `/config` - Configuration editor
- ✅ `/database` - Database viewer
- ✅ `/ai_dashboard` - AI usage statistics

### New Pages to Add
- 🆕 `/history` - Channel history management
- 🆕 `/users` - User management (balances, features, stats)
- 🆕 `/transactions` - Transaction history viewer
- 🆕 `/bot_control` - Bot control panel (restart, stop, reload config)

## Implementation Notes

1. **Security**: All dashboard pages should check for authentication (not currently implemented)
2. **Real-time Updates**: Use WebSocket for live status updates
3. **Mobile Responsive**: Ensure all pages work on mobile devices
4. **Error Handling**: Proper error messages and validation
