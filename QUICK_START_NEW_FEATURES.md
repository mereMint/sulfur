# Quick Start Guide - New Features

This guide helps you quickly test the newly implemented features.

---

## 1. Start the Bot with Fixed Maintenance Script

### Option A: Use the Fixed Version (Recommended)
```powershell
.\maintain_bot_fixed.ps1
```

### Option B: Use Original (if you haven't tested the fix yet)
```powershell
.\maintain_bot.ps1
```

**Verify bot is running:**
- Check Discord - bot should be online
- Open http://localhost:5000 - dashboard should show live logs

---

## 2. Test Shop System

### View the Shop
In Discord:
```
/shop view
```
**Expected**: Embed showing color roles and features with prices

### Check Your Balance
```
/balance
```
**Expected**: Shows current balance (default: 1000 🪙 for new users)

### Buy a Color Role
```
/shop buy_color tier:basic
```
1. Select a color from the dropdown
2. Verify role is created and applied
3. Check balance decreased by 500 🪙

### Buy a Feature
```
/shop buy item:games_access
```
**Expected**: 
- Balance decreases by 1,500 🪙
- Feature unlock added to database
- Success message displayed

### View Transaction History
```
/transactions limit:10
```
**Expected**: Shows your recent shop purchases with details

---

## 3. Test AI Dashboard Enhancements

### Open the Dashboard
Browser: http://localhost:5000/ai_dashboard

**Check for:**
- ✅ Summary cards at top (Total Calls, Total Tokens, Estimated Cost)
- ✅ Last 7 Days section with:
  - Summary by Model table
  - Summary by Feature table
  - Detailed breakdown
- ✅ Last 30 Days section with:
  - Cost by Model cards
  - Detailed table
- ✅ All Time statistics

**Trigger some AI usage first:**
```
@Sulfur hello, how are you?
```
Then refresh the dashboard to see updated stats.

---

## 4. Test Bot Cleanup (maintain_bot_fixed.ps1)

### Test Graceful Stop
In PowerShell where bot is running:
```powershell
# Press 'Q' key
```
**OR** create a stop flag:
```powershell
New-Item -ItemType File -Path stop.flag
```

**Expected:**
- Bot shuts down gracefully
- All Python processes are killed
- No orphaned python.exe in Task Manager

### Test Graceful Restart
Create a restart flag:
```powershell
New-Item -ItemType File -Path restart.flag
```

**Expected:**
- Bot shuts down
- Bot restarts automatically
- Discord status goes offline then online

### Verify No Orphans
After stopping, check Task Manager:
```powershell
Get-Process python* | Where-Object { $_.Path -like "*sulfur*" }
```
**Expected**: No results (all processes cleaned up)

---

## 5. Test Database Transaction Logging

### Check Transaction History in Database
Web dashboard: http://localhost:5000/database

1. Select table: `transaction_history`
2. Verify your shop purchases are logged
3. Check fields:
   - user_id (your Discord ID)
   - transaction_type: "shop_purchase"
   - amount (negative for purchases)
   - balance_after
   - description (e.g., "Purchased basic color role")

---

## 6. Quick Verification Checklist

Run through this checklist to verify everything works:

- [ ] Bot starts without errors
- [ ] `/shop view` displays correctly
- [ ] `/balance` shows current balance
- [ ] Can purchase color role with `/shop buy_color`
- [ ] Can purchase feature with `/shop buy`
- [ ] `/transactions` shows purchase history
- [ ] AI dashboard shows model/feature grouping
- [ ] AI dashboard shows cost summaries
- [ ] Bot stops cleanly with 'Q' or stop.flag
- [ ] Bot restarts cleanly with restart.flag
- [ ] No orphaned python.exe processes after stop
- [ ] Transactions logged in database

---

## Troubleshooting

### Shop Commands Not Showing
- Wait 1-2 minutes after bot start (commands sync to Discord)
- Try `/` in Discord to trigger command autocomplete
- Check bot logs for errors

### Transaction Not Logged
- Check database connection in logs
- Verify `transaction_history` table exists
- Run: `python test_db_connection.py`

### Bot Won't Stop
- Use Task Manager to find python.exe PID
- Kill manually: `Stop-Process -Id <PID> -Force`
- Report issue for further debugging

### AI Dashboard Not Loading
- Check web dashboard is running (http://localhost:5000)
- Check for database connection errors
- Verify `ai_model_usage` table exists

### Color Role Not Applied
- Check bot has "Manage Roles" permission
- Ensure bot's role is higher than created role
- Check logs for permission errors

---

## Next Steps

After verifying everything works:

1. **Read the documentation:**
   - `IMPLEMENTATION_SUMMARY_2025-11-17.md` - Overview of all changes
   - `docs/MANUAL_TEST_PLAN.md` - Comprehensive test suite
   - `docs/ADMIN_COMMANDS_AUDIT.md` - Dashboard migration plan

2. **Run manual tests:**
   - Follow test plan for thorough validation
   - Document any issues found
   - Create test results log

3. **Consider dashboard improvements:**
   - Add "Reload Config" button
   - Create user management page
   - Add bot control panel

4. **Deploy to production:**
   - Use `maintain_bot_fixed.ps1` as default
   - Update documentation
   - Announce new features to users

---

## Support

If you encounter issues:

1. Check `logs/` directory for error messages
2. Review relevant documentation
3. Check Discord bot permissions
4. Verify database connection
5. Test with minimal configuration

For critical issues:
- Create `stop.flag` to stop bot
- Check Task Manager for stuck processes
- Review error logs in `logs/session_*.log`
