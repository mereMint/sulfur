# MySQL Root Password Reset Guide

## Problem
MySQL was installed but root password is unknown or not set properly.

## Solution 1: Reset Root Password (RECOMMENDED)

### Step 1: Stop MySQL Service (as Administrator)
```powershell
Stop-Service MySQL84
```

### Step 2: Create Temporary Init File
Create a file `C:\mysql-init.txt` with this content:
```sql
ALTER USER 'root'@'localhost' IDENTIFIED BY 'newpassword123';
```

### Step 3: Start MySQL with Init File (as Administrator)
```powershell
cd "C:\Program Files\MySQL\MySQL Server 8.4\bin"
.\mysqld.exe --init-file=C:\mysql-init.txt --console
```

Wait for "ready for connections" message, then press Ctrl+C

### Step 4: Delete Init File
```powershell
Remove-Item C:\mysql-init.txt
```

### Step 5: Start MySQL Normally
```powershell
Start-Service MySQL84
```

### Step 6: Run Setup with New Password
```powershell
cd C:\sulfur
python setup_database.py
```
When prompted, enter: `newpassword123`

---

## Solution 2: Reinstall MySQL (Clean Start)

### Step 1: Uninstall MySQL
```powershell
Stop-Service MySQL84
& "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqld.exe" --remove MySQL84
winget uninstall Oracle.MySQL
```

### Step 2: Remove Data Directories
```powershell
Remove-Item -Recurse -Force "C:\ProgramData\MySQL" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "C:\Program Files\MySQL" -ErrorAction SilentlyContinue
```

### Step 3: Reinstall MySQL
```powershell
winget install -e --id Oracle.MySQL --accept-source-agreements --accept-package-agreements
```

### Step 4: Initialize with No Password
```powershell
cd "C:\Program Files\MySQL\MySQL Server 8.4\bin"
.\mysqld.exe --initialize-insecure --console
.\mysqld.exe --install MySQL84
Start-Service MySQL84
```

### Step 5: Set Root Password
```powershell
.\mysql.exe -u root
```

In MySQL console:
```sql
ALTER USER 'root'@'localhost' IDENTIFIED BY 'yourpassword';
FLUSH PRIVILEGES;
EXIT;
```

### Step 6: Run Setup
```powershell
cd C:\sulfur
python setup_database.py
```

---

## Solution 3: Manual Database Setup

If you know the root password, run these commands directly:

### Step 1: Connect to MySQL
```powershell
cd "C:\Program Files\MySQL\MySQL Server 8.4\bin"
.\mysql.exe -u root -p
```

### Step 2: Execute SQL Commands
```sql
CREATE DATABASE IF NOT EXISTS sulfur_bot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
DROP USER IF EXISTS 'sulfur_bot_user'@'localhost';
CREATE USER 'sulfur_bot_user'@'localhost' IDENTIFIED BY '';
GRANT ALL PRIVILEGES ON sulfur_bot.* TO 'sulfur_bot_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### Step 3: Test Connection
```powershell
cd C:\sulfur
python test_db_connection.py
```

If it says "✅ Connection successful", you're ready!

---

## Quick Test Commands

### Check if MySQL is running
```powershell
Get-Service MySQL84
```

### Test root connection (with password)
```powershell
cd "C:\Program Files\MySQL\MySQL Server 8.4\bin"
.\mysql.exe -u root -p
```

### Test bot user connection (no password)
```powershell
cd "C:\Program Files\MySQL\MySQL Server 8.4\bin"
.\mysql.exe -u sulfur_bot_user sulfur_bot
```

---

## After Database is Set Up

1. Run migration:
   ```powershell
   python apply_migration.py
   ```

2. Check status:
   ```powershell
   python check_status.py
   ```

3. If everything is ✅, proceed to add slash commands and test!
