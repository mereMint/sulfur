# Quick Fix Guide for Common Installation Errors

## Error: PyNaCl Build Failure on Termux

### Symptoms
```
subprocess.CalledProcessError: Command '[...]/configure', '--disable-shared' ...
ERROR: Failed building wheel for PyNaCl
```

### Quick Fix
```bash
# 1. Install build dependencies
pkg install build-essential binutils pkg-config libsodium clang

# 2. Set environment variable
export SODIUM_INSTALL=system

# 3. Clear cache and reinstall
pip cache purge
pip install --upgrade pip wheel setuptools
pip install -r requirements.txt
```

### Why This Happens
PyNaCl tries to compile libsodium from source, but the configure script fails on Termux/Android. The solution is to use the system-installed libsodium instead.

---

## Error: jiter Build Failure (OpenAI SDK)

### Symptoms
```
ERROR: Failed building wheel for jiter
note: This error originates from a subprocess, and is likely not a problem with pip.
```

### Quick Fix
**Don't install the OpenAI SDK!** It's not required for the bot to work.

The `requirements.txt` already excludes it. If you installed it manually:
```bash
pip uninstall openai jiter
```

The bot uses HTTP requests to call OpenAI API directly, so the SDK is not needed.

---

## Error: psutil Build Failure

### Symptoms
```
ERROR: Failed building wheel for psutil
```

### Quick Fix (Option 1 - Recommended)
Use Termux's pre-built psutil package:
```bash
pkg install python-psutil
```

### Quick Fix (Option 2)
Build with proper dependencies:
```bash
pkg install build-essential clang
pip install --no-cache-dir psutil
```

---

## Error: aiohttp Build Failure

### Symptoms
```
ERROR: Failed building wheel for aiohttp
```

### Quick Fix
```bash
# Install dependencies
pkg install build-essential clang libffi openssl

# Clear cache and reinstall
pip cache purge
pip install --no-cache-dir aiohttp
```

---

## Error: "No module named 'setuptools'"

### Quick Fix
```bash
pip install --upgrade pip setuptools wheel
```

---

## Error: "Permission denied" during installation

### Quick Fix
**NEVER use sudo in Termux!** Termux doesn't have sudo, and you don't need it.

Run all commands as a regular user:
```bash
# Wrong:
sudo pip install -r requirements.txt

# Correct:
pip install -r requirements.txt
```

---

## Error: "Command 'pkg' not found"

### Cause
You're not running this on Termux. This script is for Android/Termux only.

### Solution
Use the appropriate installation script for your platform:
- **Linux**: `bash scripts/install_linux.sh` or `bash scripts/quickinstall.sh`
- **Windows**: `powershell scripts/install_windows.ps1` or `scripts/quickinstall.ps1`
- **Termux**: `bash termux_quickstart.sh` or `bash scripts/install_termux.sh`

---

## Error: pip install times out or is very slow

### Quick Fix
```bash
# Use a faster mirror
pip install --upgrade pip
pip config set global.index-url https://pypi.org/simple
pip install -r requirements.txt
```

Or specify the mirror directly:
```bash
pip install -r requirements.txt -i https://pypi.org/simple
```

---

## Error: "ModuleNotFoundError: No module named 'X'" after installation

### Cause
Virtual environment is not activated.

### Quick Fix
```bash
cd ~/sulfur  # or wherever you installed the bot
source venv/bin/activate
python bot.py
```

To verify venv is active, your prompt should show `(venv)` at the beginning.

---

## Error: MySQL/MariaDB connection failed

### Quick Fix
```bash
# Check if MariaDB is running
pgrep -x mariadbd || pgrep -x mysqld

# If not running, start it:
mysqld_safe &

# Wait a few seconds, then test:
mysql -u root -e "SELECT 1"
```

---

## Error: "git clone" fails with authentication error

### Cause
Repository is private or you don't have access.

### Quick Fix (Option 1 - SSH Key)
```bash
# Generate SSH key
ssh-keygen -t ed25519 -f ~/.ssh/github

# Copy the public key
cat ~/.ssh/github.pub

# Add it to GitHub: https://github.com/settings/keys
```

### Quick Fix (Option 2 - Personal Access Token)
When git asks for password, use a Personal Access Token from:
https://github.com/settings/tokens

### Quick Fix (Option 3 - Fork the repo)
Fork the repository to your own GitHub account and clone your fork:
```bash
git clone https://github.com/YOUR_USERNAME/sulfur.git
```

---

## Nuclear Option: Start Fresh

If nothing works, completely remove and reinstall:

```bash
# 1. Remove virtual environment
cd ~/sulfur
rm -rf venv

# 2. Update Termux packages
pkg update && pkg upgrade

# 3. Install all build dependencies
pkg install build-essential binutils pkg-config libsodium clang python git

# 4. Recreate virtual environment
python -m venv venv
source venv/bin/activate

# 5. Install with environment variable
export SODIUM_INSTALL=system
pip install --upgrade pip wheel setuptools
pip cache purge
pip install -r requirements.txt
```

---

## Getting Help

If you still have issues after trying these fixes:

1. **Check the full error message** - often the real error is earlier in the output
2. **Verify your Python version**: `python --version` (should be 3.8+)
3. **Check Termux version**: `termux-info` or `pkg list-installed | grep termux`
4. **Read the logs** carefully - they often contain the solution
5. **Search for the specific error message** - others may have encountered it

### Automated Installation
The easiest way to avoid all these issues is to use the automated installation:
```bash
curl -sSL https://raw.githubusercontent.com/mereMint/sulfur/main/scripts/quickinstall.sh | bash
```

This handles all dependencies, environment variables, and common issues automatically.

---

*Last Updated: December 2024*
