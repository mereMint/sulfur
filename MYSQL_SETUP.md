# MySQL Setup Guide for Sulfur Bot

## Current Status
✅ MySQL 8.4 installed at: `C:\Program Files\MySQL\MySQL Server 8.4`
❌ MySQL service not yet configured (requires Administrator privileges)

## Option 1: Set Up MySQL Service (Recommended)

### Step 1: Run PowerShell as Administrator
1. Right-click PowerShell icon
2. Select "Run as Administrator"

### Step 2: Install MySQL Service
```powershell
cd "C:\Program Files\MySQL\MySQL Server 8.4\bin"
.\mysqld.exe --install MySQL84
```

### Step 3: Initialize MySQL Data Directory (if needed)
```powershell
.\mysqld.exe --initialize-insecure --console
```

### Step 4: Start MySQL Service
```powershell
Start-Service MySQL84
```

### Step 5: Set Root Password
```powershell
.\mysql.exe -u root
```

Then in MySQL console:
```sql
ALTER USER 'root'@'localhost' IDENTIFIED BY 'your_password_here';
FLUSH PRIVILEGES;
EXIT;
```

### Step 6: Create Sulfur Bot Database User
```powershell
.\mysql.exe -u root -p
```

Then in MySQL console:
```sql
CREATE DATABASE sulfur_bot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'sulfur_bot_user'@'localhost' IDENTIFIED BY 'your_bot_password';
GRANT ALL PRIVILEGES ON sulfur_bot.* TO 'sulfur_bot_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### Step 7: Update .env File
Edit `c:\sulfur\.env` and set:
```
DB_HOST=localhost
DB_USER=sulfur_bot_user
DB_PASS=your_bot_password
DB_NAME=sulfur_bot
```

### Step 8: Run Database Migration
```powershell
cd C:\sulfur
python apply_migration.py
```

---

## Option 2: Use SQLite (Temporary Testing)

If you want to test the features without setting up MySQL, you can temporarily use SQLite:

### Step 1: Install SQLite Package
```powershell
pip install aiosqlite
```

### Step 2: Create SQLite Adapter
This would require modifying `modules/db_helpers.py` to support SQLite, which is more complex.

**Recommendation:** Use Option 1 with MySQL as it's already configured throughout the codebase.

---

## Option 3: Use Existing Database (If Available)

If you already have MySQL running elsewhere or want to use a remote database:

### Update .env
```
DB_HOST=your_host_or_ip
DB_PORT=3306
DB_USER=sulfur_bot_user
DB_PASS=your_password
DB_NAME=sulfur_bot
```

---

## Verification Commands

### Check if MySQL Service is Running
```powershell
Get-Service MySQL84
```

### Check if Port 3306 is Listening
```powershell
Test-NetConnection -ComputerName localhost -Port 3306
```

### Test Database Connection
```powershell
cd "C:\Program Files\MySQL\MySQL Server 8.4\bin"
.\mysql.exe -u sulfur_bot_user -p sulfur_bot
```

### Check Tables After Migration
```sql
USE sulfur_bot;
SHOW TABLES;
```

Expected tables:
- user_economy
- feature_unlocks
- shop_purchases
- daily_quests
- daily_quest_completions
- monthly_milestones
- gambling_stats
- transaction_history
- color_roles
- chat_bounties
- (and existing tables from previous migrations)

---

## Troubleshooting

### "Service Cannot Be Found"
- MySQL service not installed → Run Step 2 in Option 1 as Administrator

### "Access Denied for user"
- Password incorrect → Check .env file matches database user password
- User doesn't exist → Run Step 6 in Option 1

### "Can't connect to MySQL server on 'localhost:3306'"
- MySQL not running → `Start-Service MySQL84`
- Port blocked → Check Windows Firewall

### "Unknown database 'sulfur_bot'"
- Database not created → Run Step 6 in Option 1

---

## Quick Start (After MySQL is Running)

```powershell
# 1. Verify MySQL is running
Get-Service MySQL84

# 2. Run migration
python apply_migration.py

# 3. Start the bot
python bot.py
```

---

## Next Steps After MySQL Setup

See `TESTING_GUIDE.md` for:
- Adding slash commands to bot.py
- Testing economy system (balance, daily, pay, baltop)
- Testing shop system (color roles, feature unlocks)
- Testing gambling games (blackjack, roulette, mines, russian roulette)
- Testing quest system (daily/monthly quests with rewards)
