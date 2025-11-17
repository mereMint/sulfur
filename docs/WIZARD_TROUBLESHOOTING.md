# Installation Wizard Troubleshooting Guide

## Common Issues and Solutions

### Issue: "Cannot run scripts" or "Execution Policy" error

**Error Message:**
```
.\install_wizard.ps1 : File cannot be loaded because running scripts is disabled on this system.
```

**Solution 1 (Recommended):**
Run PowerShell as Administrator and execute:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Solution 2 (Quick Fix):**
Use the bypass flag:
```powershell
powershell -ExecutionPolicy Bypass -File .\install_wizard.ps1
```

**Solution 3 (Easiest):**
Double-click `INSTALL.bat` instead - it automatically bypasses the policy.

---

### Issue: Wizard crashes immediately

**Possible Causes:**
1. PowerShell version too old
2. Missing .NET Framework
3. Corrupted script download

**Solutions:**

**Check PowerShell version:**
```powershell
$PSVersionTable.PSVersion
```
Should be 5.1 or higher. Update if needed from Microsoft.

**Verify script integrity:**
```powershell
# Check file size (should be ~26KB)
(Get-Item .\install_wizard.ps1).Length

# Re-download if corrupted
git checkout install_wizard.ps1
```

**Try running in different PowerShell:**
```powershell
# Try Windows PowerShell (not PowerShell Core)
powershell.exe -ExecutionPolicy Bypass -File .\install_wizard.ps1
```

---

### Issue: "Python not found" even though Python is installed

**Cause:** Python not in PATH

**Solution:**

**Option 1: Reinstall Python**
1. Download Python from python.org
2. **IMPORTANT:** Check "Add Python to PATH" during installation
3. Complete installation
4. Restart PowerShell
5. Run wizard again

**Option 2: Add Python to PATH manually**
```powershell
# Find Python installation
Get-ChildItem C:\ -Recurse -Filter python.exe -ErrorAction SilentlyContinue | Select-Object FullName

# Add to PATH (replace with your Python path)
$env:Path += ";C:\Users\YourName\AppData\Local\Programs\Python\Python311"

# Make it permanent
[Environment]::SetEnvironmentVariable("Path", $env:Path, [System.EnvironmentVariableTarget]::User)
```

**Option 3: Use full Python path**
Edit the wizard and replace `python` with full path like:
```powershell
C:\Users\YourName\AppData\Local\Programs\Python\Python311\python.exe
```

---

### Issue: MySQL/MariaDB detection fails

**Error:** "MySQL/MariaDB is not running"

**Solution 1: Start MySQL Service**
```powershell
# Check available services
Get-Service -Name "MySQL*","MariaDB*"

# Start the service (run as Administrator)
Start-Service -Name "MySQL84"  # Replace with your service name
```

**Solution 2: Start XAMPP MySQL**
1. Open XAMPP Control Panel
2. Click "Start" next to MySQL
3. Wait for it to turn green
4. Run wizard again

**Solution 3: Check if MySQL is actually running**
```powershell
# Check for MySQL processes
Get-Process mysqld,mariadbd -ErrorAction SilentlyContinue
```

If no process found, MySQL isn't running or isn't installed.

---

### Issue: Database setup fails

**Error:** "Database setup failed" or connection errors

**Common Causes & Solutions:**

**Wrong root password:**
- The wizard will prompt for MySQL root password
- If you don't know it, see MYSQL_PASSWORD_RESET.md
- For XAMPP, root password is usually empty (just press Enter)

**Database already exists:**
- The wizard will detect this
- It will ask if you want to reinitialize
- Choose "No" if you want to keep existing data

**User creation fails:**
```sql
-- Run this manually in MySQL:
DROP USER IF EXISTS 'sulfur_bot_user'@'localhost';
CREATE USER 'sulfur_bot_user'@'localhost' IDENTIFIED BY '';
GRANT ALL PRIVILEGES ON sulfur_bot.* TO 'sulfur_bot_user'@'localhost';
FLUSH PRIVILEGES;
```

**MySQL command-line not found:**
The wizard looks for MySQL in common locations. If it can't find it:
```powershell
# Find mysql.exe
Get-ChildItem C:\ -Recurse -Filter mysql.exe -ErrorAction SilentlyContinue | Select-Object FullName

# When prompted, enter the full path to mysql.exe
```

---

### Issue: Dependency installation fails

**Error:** "Failed to install dependencies"

**Common Causes & Solutions:**

**No internet connection:**
- Check your internet connection
- Try again when connected

**Firewall blocking pip:**
- Temporarily disable firewall
- Or add exception for Python and pip

**Corrupted package cache:**
```powershell
# Clear pip cache
pip cache purge

# Upgrade pip
python -m pip install --upgrade pip

# Try again
pip install -r requirements.txt
```

**Specific package fails:**
Some packages might fail on certain systems. The wizard continues anyway, and the bot might still work without them.

**Virtual environment issues:**
```powershell
# Remove and recreate venv
Remove-Item -Recurse -Force venv
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

### Issue: API key validation fails

**Error:** "API test failed" or "Invalid API key"

**Discord Bot Token:**
- Make sure you copied the entire token
- No spaces before or after
- Regenerate token if it's old (Discord Developer Portal → Bot → Reset Token)
- Ensure all required intents are enabled

**Gemini API Key:**
- Verify at https://aistudio.google.com/apikey
- Check if you're in a supported region
- Ensure API is enabled for your Google Cloud project
- Check quota limits

**OpenAI API Key:**
- Verify at https://platform.openai.com/api-keys
- Check if billing is set up (OpenAI requires payment method)
- Verify you have credits/balance
- Check if key has correct permissions

**Test manually:**
```powershell
# Test environment variables
Get-Content .env | Select-String "DISCORD_BOT_TOKEN|GEMINI_API_KEY|OPENAI_API_KEY"

# Run test script
python test_setup.py
```

---

### Issue: Shortcuts don't work

**Desktop shortcuts not created:**
- Wizard needs permission to create files on desktop
- Run as Administrator if getting permission errors
- Check if Desktop path is accessible

**Shortcut doesn't start bot:**
```powershell
# Check shortcut target
$shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut("$env:USERPROFILE\Desktop\Start Sulfur Bot.lnk")
$shortcut.TargetPath
$shortcut.Arguments
```

**Manual shortcut creation:**
1. Right-click desktop → New → Shortcut
2. Location: `powershell.exe`
3. Arguments: `-ExecutionPolicy Bypass -NoExit -File "C:\path\to\sulfur\start.ps1"`
4. Name it "Start Sulfur Bot"

---

### Issue: Wizard freezes or hangs

**During prerequisite check:**
- Press Ctrl+C to cancel
- Run with skip flag: `.\install_wizard.ps1 -SkipPrerequisites`

**During dependency installation:**
- This can take 5-10 minutes depending on internet speed
- Watch for download progress
- If truly frozen (no activity for 15+ minutes), Ctrl+C and retry

**During database setup:**
- Might be waiting for MySQL password input
- Check if a prompt is hidden behind other windows
- Or MySQL server is slow to respond

---

### Issue: "Setup verification found issues"

**After wizard completes but test_setup.py reports problems:**

Review the specific failures:

**Environment variables not set:**
- Check .env file exists
- Ensure no syntax errors in .env
- Reload environment: restart PowerShell

**Config files invalid:**
- Check config/config.json is valid JSON
- Check config/system_prompt.txt exists and has content

**Database connection fails:**
- Verify MySQL is running
- Test manually: `mysql -u sulfur_bot_user sulfur_bot`
- Check credentials in .env match database

**API connectivity fails:**
- Check firewall isn't blocking
- Verify internet connection
- Test API keys in browser/API testing tool

---

### Issue: Want to run wizard again

**To rerun entire setup:**
```powershell
# Delete configuration
Remove-Item .env -Force

# Run wizard again
.\install_wizard.ps1
```

**To rerun specific parts:**
```powershell
# Only database setup
python setup_wizard.py

# Only dependency installation
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Only testing
python test_setup.py
```

---

## Advanced Troubleshooting

### Enable Verbose Logging

Edit `install_wizard.ps1` and change:
```powershell
$ErrorActionPreference = 'Continue'
```
to
```powershell
$ErrorActionPreference = 'Continue'
$VerbosePreference = 'Continue'
```

### Check What's Installed

```powershell
# Python packages
pip list

# Services
Get-Service -Name "MySQL*","MariaDB*"

# Processes
Get-Process python,mysqld,mariadbd

# Environment variables
Get-ChildItem Env: | Where-Object Name -match "DISCORD|GEMINI|OPENAI|DB_"
```

### Manual Verification Checklist

- [ ] Python installed and in PATH
- [ ] Git installed
- [ ] MySQL/MariaDB running
- [ ] .env file exists with all required keys
- [ ] Database 'sulfur_bot' exists
- [ ] User 'sulfur_bot_user' exists with permissions
- [ ] Virtual environment created (venv folder exists)
- [ ] Dependencies installed (check venv/Lib/site-packages/)
- [ ] test_setup.py runs without errors

---

## Getting Help

If you've tried these solutions and still have issues:

1. **Check the full README:** [README.md](../README.md)
2. **Review setup guide:** [INSTALL_WINDOWS.md](../INSTALL_WINDOWS.md)
3. **Look at manual setup:** [SETUP.md](../SETUP.md)
4. **Open GitHub issue:** Provide:
   - Error messages (full output)
   - Windows version
   - Python version (`python --version`)
   - PowerShell version (`$PSVersionTable.PSVersion`)
   - What step failed
   - What you've tried

---

## Prevention Tips

To avoid issues:

✅ **Run as Administrator** when possible
✅ **Disable antivirus temporarily** during installation
✅ **Use latest Windows updates**
✅ **Have stable internet connection**
✅ **Close other applications** that might use ports
✅ **Follow prompts carefully** - don't skip without reading

---

Remember: The wizard is designed to be forgiving. Most warnings are okay to continue through. Only hard errors (red ✗) require attention before proceeding.
