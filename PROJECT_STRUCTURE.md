# Sulfur Discord Bot - Project Structure

## Quick Start
To start the bot, run **one** of these from the root directory:
- **Windows**: `.\maintain_bot.ps1`
- **Linux/Termux**: `./maintain_bot.sh`

## Directory Structure

```
sulfur/
├── bot.py                    # Main bot entry point
├── maintain_bot.ps1          # Windows maintenance script (START HERE)
├── maintain_bot.sh           # Linux maintenance script (START HERE)
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables (API keys, tokens)
│
├── config/                   # Configuration files
│   ├── config.json          # Bot configuration
│   ├── system_prompt.txt    # AI system prompt
│   ├── bot_status.json      # Runtime status file
│   └── database_sync.sql    # Database sync file
│
├── modules/                  # Python modules
│   ├── api_helpers.py       # API interaction helpers
│   ├── db_helpers.py        # Database operations
│   ├── logger_utils.py      # Logging utilities
│   ├── economy.py           # Economy system
│   ├── level_system.py      # XP and leveling
│   ├── voice_manager.py     # Voice channel management
│   ├── werwolf.py           # Werwolf game logic
│   ├── controls.py          # Bot control functions
│   └── fake_user.py         # Testing utilities
│
├── web/                      # Web dashboard
│   ├── web_dashboard.py     # Flask web server
│   ├── index.html           # Dashboard home
│   ├── config.html          # Configuration page
│   ├── database.html        # Database viewer
│   ├── ai_usage.html        # AI usage stats
│   └── layout.html          # Base template
│
├── scripts/                  # Utility scripts
│   ├── start_bot.ps1        # Windows bot starter
│   ├── start_bot.sh         # Linux bot starter
│   ├── shared_functions.ps1 # PowerShell helpers
│   ├── shared_functions.sh  # Bash helpers
│   ├── bootstrapper.ps1     # Windows setup
│   ├── bootstrapper.sh      # Linux setup
│   ├── setup_firewall.ps1   # Windows firewall config
│   ├── check_errors.ps1     # Error detection
│   ├── check_errors_simple.ps1  # Simple error check
│   └── cleanup_old_files.ps1    # Log cleanup
│
├── docs/                     # Documentation
│   ├── README.md            # Main documentation
│   ├── LOGGING_IMPROVEMENTS.md   # Logging system guide
│   ├── ERROR_CHECKING_GUIDE.md   # Error detection guide
│   ├── STARTUP_GUIDE.md     # Startup instructions
│   ├── STARTUP_CHECKLIST.md # Quick reference
│   ├── README_STARTUP.md    # Startup help
│   ├── FIXES_APPLIED.md     # Applied fixes log
│   └── CONFIG_DOCUMENTATION.md   # Config file docs
│
├── logs/                     # Log files
│   ├── session_*.log        # Main session logs
│   └── session_*_web.log    # Web dashboard logs
│
├── backups/                  # Database backups
│   └── sulfur_bot_backup_*.sql
│
└── venv/                     # Python virtual environment
    └── (Python packages)
```

## Important Files

### Start Here
- `maintain_bot.ps1` / `maintain_bot.sh` - Main entry point, handles auto-restart and updates
- `.env` - **REQUIRED**: Contains API keys and database credentials
- `config/config.json` - Bot configuration (channels, modules, settings)

### Core Bot
- `bot.py` - Main Discord bot application
- `modules/` - All bot functionality split into logical modules
- `web/web_dashboard.py` - Web interface on http://localhost:5000

### Configuration
All config files are now in `config/`:
- `config.json` - Main bot settings
- `system_prompt.txt` - AI personality and behavior
- `bot_status.json` - Runtime status (auto-generated)
- `database_sync.sql` - Database export (auto-generated)

### Logs
- `logs/session_*.log` - Main bot logs with timestamps
- `logs/session_*_web.log` - Web dashboard logs
- Logs are automatically created and rotated

## Usage

### Starting the Bot
```powershell
# Windows
.\maintain_bot.ps1

# Linux/Termux
./maintain_bot.sh
```

### Accessing Web Dashboard
Once started, visit: http://localhost:5000

### Checking for Errors
```powershell
# Windows
.\scripts\check_errors_simple.ps1

# Or detailed check
.\scripts\check_errors.ps1
```

### Cleaning Old Files
```powershell
.\scripts\cleanup_old_files.ps1
```

## File Organization Rules

### Root Directory (Keep Clean!)
Only essential files:
- `bot.py` - Main entry point
- `maintain_bot.ps1` / `.sh` - Startup scripts
- `requirements.txt` - Dependencies
- `.env` - Credentials
- `.gitignore`, `.gitattributes` - Git config

Everything else goes in folders!

### Adding New Files

**Python modules** → `modules/`
- Database functions
- API helpers
- Game logic
- Utilities

**Web files** → `web/`
- HTML templates
- Web dashboard code
- Static assets

**Scripts** → `scripts/`
- PowerShell utilities
- Bash utilities
- Setup scripts

**Configuration** → `config/`
- JSON configs
- Text configs
- Runtime status

**Documentation** → `docs/`
- Markdown files
- Guides
- Changelogs

## Development

### Import Paths
When importing from modules, use:
```python
from modules.db_helpers import init_db_pool
from modules.logger_utils import bot_logger
```

### Adding New Modules
1. Create file in `modules/`
2. Import in `bot.py`: `from modules.your_module import YourClass`
3. Document in `docs/` if complex

### Web Dashboard Development
- Templates in `web/` (HTML files)
- Access with `template_folder='.'` in Flask
- Logs in `../logs/` relative to `web/`

## Troubleshooting

**Import errors after reorganization?**
- Update imports to use `modules.` prefix
- Check paths in `config/` instead of root

**Web dashboard 404 errors?**
- Templates are in `web/` folder
- Flask configured with `template_folder='.'`

**Bot can't find config.json?**
- Now at `config/config.json`
- Updated in bot.py load_config()

**Scripts can't find each other?**
- Use `$PSScriptRoot` (PowerShell) or `$(dirname "$0")` (Bash)
- All helper scripts in `scripts/` folder

## Benefits of This Structure

✅ **Cleaner root** - Only startup files visible
✅ **Organized** - Related files grouped together  
✅ **Scalable** - Easy to add new modules
✅ **Professional** - Standard project layout
✅ **Maintainable** - Find files quickly
✅ **Git-friendly** - Clear .gitignore rules

---

**Last Updated**: 2025-11-16
**Structure Version**: 2.0
