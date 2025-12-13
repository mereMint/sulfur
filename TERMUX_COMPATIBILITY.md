# Termux Compatibility Checklist

## ✅ Verified Working

### Dependencies (requirements.txt)
- ✅ **No Rust compilation required** - Removed `openai` and `google-generativeai` SDKs
- ✅ **All packages install via pip** on Termux/aarch64/Python 3.12
- ✅ **Core dependencies:**
  - `discord.py` - Discord bot library
  - `mysql-connector-python` - Database driver
  - `aiohttp` - HTTP client (for AI APIs)
  - `python-dotenv` - Environment variables
  - `Flask` + `Flask-SocketIO` - Web dashboard
  - `waitress` - WSGI server

### API Integration (modules/api_helpers.py)
- ✅ **HTTP-based API calls** - No SDK imports, pure `aiohttp`
- ✅ **Gemini API** - Direct REST calls to `generativelanguage.googleapis.com`
- ✅ **OpenAI API** - Direct REST calls to `api.openai.com`
- ✅ **Vision support** - Works via HTTP image analysis

### Database (MariaDB)
- ✅ **MariaDB support** - Full compatibility in all scripts
- ✅ **Auto-detection** - `_db_client()` picks `mariadb` or `mysql` command
- ✅ **Process detection** - Checks both `mysqld` and `mariadbd`
- ✅ **Readiness checks** - SQL ping (`SELECT 1`) before proceeding
- ✅ **Connection pooling** - Works with both MySQL and MariaDB

### Scripts

#### termux_quickstart.sh
- ✅ **Storage setup** - `termux-setup-storage` for external access
- ✅ **Package installation** - Bulk install with warnings tolerance
- ✅ **SSH wizard** - Interactive key generation, GitHub verification
- ✅ **MariaDB startup** - `mysqld_safe &` with 30s readiness wait
- ✅ **Database creation** - Auto-creates `sulfur_bot` and user
- ✅ **Virtual environment** - Creates venv, installs deps
- ✅ **Configuration** - Interactive `.env` setup
- ✅ **Verification** - Runs `verify_termux_setup.sh`
- ✅ **Startup helper** - Generates `start_sulfur.sh`

#### maintain_bot.sh
- ✅ **Environment detection** - Checks `$TERMUX_VERSION`
- ✅ **Process management** - Uses `pgrep` with `ps aux` fallback
- ✅ **MariaDB handling** - Prefers `mariadb-dump`, falls back to `mysqldump`
- ✅ **Python environment** - Auto-detects `venv/bin/python`
- ✅ **Auto-restart** - Monitors bot, restarts on crash
- ✅ **Auto-backup** - Database dumps every 30min (or `--no-backup`)
- ✅ **Auto-commit** - Git commits every 5min
- ✅ **Auto-update** - Checks remote, pulls updates
- ✅ **Crash detection** - Pauses after 5 quick crashes
- ✅ **Preflight check** - Validates `.env` token before start
- ✅ **Environment bootstrap** - Creates venv and installs deps if missing

#### start.sh
- ✅ **Termux detection** - Sets `PYTHON_CMD=python` for Termux
- ✅ **MariaDB auto-start** - `mysqld_safe &` if not running
- ✅ **Virtual environment** - Creates if missing, activates
- ✅ **Dependency install** - Runs `pip install -r requirements.txt` on first run

#### verify_termux_setup.sh
- ✅ **Command checks** - Verifies `python`, `git`, `mariadb`, `ssh`
- ✅ **Process checks** - Confirms MariaDB is running
- ✅ **File checks** - Validates `.env`, `config/config.json`, `venv/`
- ✅ **Database checks** - Tests connection, lists tables
- ✅ **Python checks** - Verifies `import discord, flask, mysql.connector`

### Test Files

#### test_setup.py
- ✅ **No SDK imports** - Uses `aiohttp` for API tests
- ✅ **Gemini test** - HTTP POST to Gemini API
- ✅ **OpenAI test** - HTTP POST to OpenAI API
- ✅ **Async support** - `asyncio.run()` for tests

### Documentation

#### TERMUX_GUIDE.md
- ✅ **F-Droid warning** - Recommends F-Droid over Play Store
- ✅ **SSH wizard** - Documents interactive setup
- ✅ **Private repo flows** - Fork or PAT instructions
- ✅ **MariaDB commands** - Simplified `mysqld_safe &`
- ✅ **Wake lock** - Battery optimization guidance
- ✅ **Troubleshooting** - PAT, SSH, MariaDB issues

#### README.md
- ✅ **One-line install** - Git clone + quickstart command
- ✅ **Termux section** - Quick start instructions
- ✅ **Private repo note** - Fork/PAT requirements

## 🔧 Termux-Specific Features

### Wake Lock Support
- **Acquire wake lock** - Long-press Termux notification
- **Battery optimization** - Disable for Termux in Android settings
- **Screen off** - Bot runs with screen off if wake lock active

### Auto-Start (Termux:Boot)
- **Boot script** - `~/.termux/boot/sulfur.sh`
- **MariaDB start** - Waits for DB before bot
- **Background run** - Uses `nohup` for persistent execution

### Storage Access
- **termux-setup-storage** - Access to `/sdcard` and external storage
- **Backup location** - Can save to external storage

### Clipboard Integration
- **SSH key copy** - `termux-clipboard-set` in SSH wizard
- **Easy key sharing** - One-tap copy to add to GitHub

## 🚨 Known Limitations

### Package Build Issues (SOLVED)
- ❌ **openai SDK** - Requires Rust (`jiter` dependency) - REMOVED
- ❌ **google-generativeai SDK** - Requires Rust (`pydantic-core`) - REMOVED
- ⚠️ **PyNaCl** - Requires native C compilation - OPTIONAL (voice features disabled without it)
- ✅ **Solution** - Bot uses HTTP for AI APIs; PyNaCl is optional and only needed for voice features

### System Differences
- ⚠️ **No systemd** - Use `mysqld_safe &` instead of service commands
- ⚠️ **No sudo** - Termux runs as user, no root needed
- ⚠️ **Different paths** - `$PREFIX` instead of `/usr`, handled automatically

### Performance
- ⚠️ **Memory limits** - Shared with Android apps; use lighter AI models
- ⚠️ **Battery drain** - Keep device charging for 24/7 operation
- ⚠️ **Network** - Needs stable WiFi or mobile data

## 📝 Quick Start (One Command)

```bash
pkg update && pkg install -y git && git clone --depth 1 https://github.com/YOUR_USERNAME/sulfur.git sulfur && cd sulfur && bash termux_quickstart.sh
```

**Replace `YOUR_USERNAME`** with your GitHub username (or use fork).

## 🔍 Verification Commands

```bash
# Check Python environment
python -c "import discord, flask, flask_socketio, aiohttp, mysql.connector; print('OK')"

# Check MariaDB
pgrep -x mysqld || pgrep -x mariadbd

# Test MariaDB connection
mariadb -u sulfur_bot_user sulfur_bot -e "SELECT 1;"

# Check virtual environment
source venv/bin/activate
pip list | grep -E "discord|flask|aiohttp|mysql"

# Run full verification
bash verify_termux_setup.sh
```

## 🆘 Troubleshooting

### Bot crashes with "ModuleNotFoundError: No module named 'discord'"
**Cause:** Virtual environment not activated or dependencies not installed  
**Fix:**
```bash
cd ~/sulfur
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### "pydantic-core" or "jiter" build fails
**Cause:** Trying to install removed SDKs  
**Fix:** Pull latest code; `requirements.txt` no longer includes them
```bash
git pull
pip install -r requirements.txt
```

### MariaDB not detected
**Cause:** Process detection or readiness check fails  
**Fix:**
```bash
# Start MariaDB manually
mysqld_safe &
sleep 10

# Test connection
mariadb -u root -e "SELECT 1;"

# Check if running
pgrep -x mysqld || pgrep -x mariadbd
```

### SSH clone fails with "403"
**Cause:** Private repo without SSH key or PAT  
**Fix:** Run SSH wizard or use PAT
```bash
# Option 1: SSH wizard (in quickstart)
bash termux_quickstart.sh

# Option 2: Use PAT when prompted
# Create at https://github.com/settings/tokens (repo scope)
```

### Wake lock not working
**Cause:** Notification settings or battery optimization  
**Fix:**
1. Long-press Termux notification → "Acquire Wake Lock"
2. Settings → Apps → Termux → Battery → Unrestricted
3. Disable "Adaptive Battery" for Termux

## ✅ Final Checklist

Before reporting issues, verify:

- [ ] Termux from F-Droid (not Play Store)
- [ ] Storage permissions granted (`termux-setup-storage`)
- [ ] MariaDB installed and running (`pkg install mariadb`)
- [ ] Virtual environment activated (`source venv/bin/activate`)
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file has Discord token and API keys
- [ ] MariaDB database created (`sulfur_bot`)
- [ ] Wake lock acquired (notification)
- [ ] Battery optimization disabled
- [ ] Latest code pulled (`git pull`)

## 🎯 Expected Behavior

When everything works:
1. Bot appears online in Discord
2. Web dashboard accessible at `http://localhost:5000`
3. Bot responds to mentions and commands
4. No crash loops in logs
5. MariaDB connection stable
6. Auto-restart on updates

## 📞 Support

If issues persist after verification:
1. Check `~/sulfur/logs/bot_*.log` for errors
2. Run `bash verify_termux_setup.sh` and share output
3. Share Python version: `python -V`
4. Share Termux version: `echo $TERMUX_VERSION`
5. Share architecture: `uname -m`
