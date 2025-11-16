# Copilot Instructions for Sulfur Discord Bot

## Project Overview

Sulfur is a feature-rich Discord bot built with Python and discord.py 2.0+. It integrates AI capabilities (Gemini and OpenAI), includes mini-games (Werwolf), manages economy systems, and provides a comprehensive web dashboard for monitoring and administration.

## Technology Stack

- **Language**: Python 3.8+
- **Discord Library**: discord.py 2.0+
- **Database**: MySQL/MariaDB with mysql-connector-python
- **Web Framework**: Flask with Flask-SocketIO and Waitress
- **AI APIs**: Google Gemini API, OpenAI API
- **Environment**: dotenv for configuration

## Project Structure

```
sulfur/
├── bot.py                    # Main bot entry point - Discord bot initialization
├── web_dashboard.py          # Flask web dashboard server (port 5000)
├── maintain_bot.ps1/.sh      # Maintenance scripts with auto-restart
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables (API keys, tokens)
│
├── config/                   # Configuration files
│   ├── config.json          # Bot settings (models, channels, features)
│   ├── system_prompt.txt    # AI personality and behavior
│   └── bot_status.json      # Runtime status (auto-generated)
│
├── modules/                  # Python modules
│   ├── api_helpers.py       # AI API integration (Gemini/OpenAI)
│   ├── db_helpers.py        # Database operations and connection pooling
│   ├── logger_utils.py      # Structured logging utilities
│   ├── bot_enhancements.py  # AI conversation, vision, tracking
│   ├── emoji_manager.py     # Emoji analysis with AI vision
│   ├── economy.py           # Virtual currency system
│   ├── level_system.py      # XP and leveling mechanics
│   ├── voice_manager.py     # Voice channel management
│   ├── werwolf.py           # Werwolf game logic
│   └── controls.py          # Bot control functions
│
├── web/                      # Web dashboard templates
│   ├── index.html           # Main dashboard
│   ├── config.html          # Configuration editor
│   ├── database.html        # Database viewer
│   └── ai_dashboard.html    # AI usage statistics
│
├── scripts/                  # Utility scripts
│   ├── db_migrations/       # Database schema migrations
│   └── *.ps1/*.sh           # PowerShell and Bash utilities
│
├── logs/                     # Application logs (auto-generated)
└── backups/                  # Database backups (auto-generated)
```

## Coding Standards

### Python Style

- Follow PEP 8 naming conventions
- Use 4 spaces for indentation
- Use descriptive variable names (e.g., `user_id`, `api_response`)
- Add docstrings for functions and classes
- Use type hints where appropriate

### Import Organization

```python
# Standard library imports
import asyncio
import json
import os

# Third-party imports
import discord
from discord.ext import tasks

# Local imports
from modules.logger_utils import bot_logger as logger
from modules.db_helpers import init_db_pool
from modules.api_helpers import get_chat_response
```

### Error Handling

- Always use structured logging from `modules.logger_utils`
- Use try-except blocks for API calls and database operations
- Log errors with appropriate severity levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Provide user-friendly error messages in Discord responses

Example:
```python
from modules.logger_utils import bot_logger as logger

try:
    result = await api_call()
except Exception as e:
    logger.error(f"API call failed: {e}")
    await interaction.response.send_message("An error occurred. Please try again.")
```

## Discord Bot Specifics

### Commands

- Use discord.py 2.0+ slash commands with `@app_commands.command()`
- Prefer slash commands over traditional prefix commands
- Use `@app_commands.describe()` for parameter descriptions
- Group related commands using `app_commands.Group`

### Intents

Required intents are configured in bot.py:
- Message Content Intent (for reading messages)
- Server Members Intent (for member tracking)
- Presence Intent (for user status)

### Permissions

The bot requires these permissions:
- Send Messages
- Embed Links
- Attach Files
- Use External Emojis (for emoji management features)
- Manage Channels (for voice channel creation in Werwolf)

## Database Operations

### Connection Pooling

- Use `modules.db_helpers.get_db_connection()` for database operations
- Always use context managers for connections and cursors
- Connection pooling is handled automatically

Example:
```python
from modules.db_helpers import get_db_connection

async def query_user_data(user_id: int):
    async with get_db_connection() as (conn, cursor):
        await cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        return await cursor.fetchone()
```

### Schema Management

- Database migrations are in `scripts/db_migrations/`
- Tables are auto-created on first run when possible
- Use parameterized queries to prevent SQL injection
- Character set: utf8mb4 with utf8mb4_unicode_ci collation

## AI Integration

### Multi-Model Support

The bot supports multiple AI providers:
- **Gemini**: gemini-2.5-flash, gemini-2.0-flash-exp, gemini-1.5-pro
- **OpenAI**: gpt-4o, gpt-4o-mini, gpt-4-turbo

Configuration is in `config/config.json` under the `api` section.

### API Helpers

Use `modules.api_helpers` for AI interactions:
- `get_chat_response()` - Main chat function
- `get_relationship_summary_from_api()` - User relationship analysis
- `get_wrapped_summary_from_api()` - Yearly summary generation
- `get_game_details_from_api()` - Game content generation

### Vision Support

- Images are automatically detected in `handle_image_attachment()`
- Vision models are used when images are present
- Image descriptions are cached for context

### Conversation Context

- 2-minute conversation windows track context
- Stored in `conversation_context` database table
- Auto-cleanup of old contexts via periodic task

## Web Dashboard

### Development

- Flask app is in `web_dashboard.py`
- Templates are in `web/` directory
- Uses Waitress WSGI server for production
- WebSocket support via Flask-SocketIO for real-time updates

### Endpoints

- `/` - Main dashboard with live logs
- `/config` - Configuration editor
- `/database` - Database viewer
- `/ai_usage` - AI usage statistics API
- `/ai_dashboard` - AI analytics page

## Environment Variables

Required in `.env`:
```
DISCORD_BOT_TOKEN=<your_token>
DB_HOST=localhost
DB_USER=sulfur_bot_user
DB_PASS=<password>
DB_NAME=sulfur_bot
GEMINI_API_KEY=<api_key>
OPENAI_API_KEY=<api_key>  # Optional
BOT_PREFIX=!              # Optional, default is !
OWNER_ID=<discord_user_id>  # Optional
```

## Testing and Development

### No Formal Test Suite

- This project does not have a formal unit testing framework
- Manual testing is performed via Discord interactions
- Test bot behavior in a development Discord server

### Development Workflow

1. Make changes in a feature branch
2. Test manually in a Discord server
3. Check logs in `logs/` directory for errors
4. Use web dashboard at http://localhost:5000 for monitoring
5. Verify database changes with `web/database.html`

### Error Checking

Use the provided error checking scripts:
```powershell
# Windows
.\check_errors.ps1

# Linux/Termux
./check_errors.sh
```

## Maintenance Scripts

### Auto-Update System

- Scripts check for git updates every 60 seconds
- Auto-restart bot when changes are detected
- Commits local changes every 5 minutes

### Auto-Backup

- Database backups every 30 minutes
- Stored in `backups/` directory
- Keeps last 10 backups

### Control Flags

- `restart.flag` - Gracefully restart bot
- `stop.flag` - Gracefully stop bot

## Adding New Features

### New Discord Commands

1. Add command in appropriate module or `bot.py`
2. Use `@app_commands.command()` decorator
3. Add to command group if related to existing features
4. Update documentation in comments

### New Modules

1. Create file in `modules/` directory
2. Import in `bot.py`
3. Follow existing module patterns
4. Use structured logging from `logger_utils`

### Database Schema Changes

1. Create migration SQL file in `scripts/db_migrations/`
2. Apply migration: `mysql -u sulfur_bot_user -p sulfur_bot < migration.sql`
3. Update `db_helpers.py` if adding new helper functions

### Configuration Changes

1. Update `config/config.json` for new settings
2. Add defaults in `bot.py` when loading config
3. Document in `docs/CONFIG_DOCUMENTATION.md`

## Common Patterns

### Async/Await

All Discord and database operations are asynchronous:
```python
@app_commands.command()
async def my_command(interaction: discord.Interaction):
    await interaction.response.defer()  # For long operations
    result = await some_async_function()
    await interaction.followup.send(result)
```

### Embed Messages

Use embeds for rich formatting:
```python
embed = discord.Embed(
    title="Title",
    description="Description",
    color=discord.Color.blue()
)
embed.add_field(name="Field", value="Value")
await interaction.response.send_message(embed=embed)
```

### Permission Checks

```python
@app_commands.command()
@app_commands.checks.has_permissions(administrator=True)
async def admin_command(interaction: discord.Interaction):
    # Command implementation
```

## Troubleshooting

### Common Issues

1. **Module Import Errors**: Ensure virtual environment is activated
2. **Database Connection**: Verify MySQL is running and credentials are correct
3. **Discord Token**: Check `.env` file and ensure no extra quotes/spaces
4. **Port 5000 in Use**: Change port in `web_dashboard.py` if needed

### Logging

Check logs for debugging:
- Main bot logs: `logs/session_*.log`
- Web dashboard logs: `logs/session_*_web.log`
- Log level can be adjusted in `modules/logger_utils.py`

## Security Considerations

- Never commit `.env` file (included in `.gitignore`)
- Use parameterized SQL queries to prevent injection
- Validate user input before database operations
- Keep API keys in environment variables only
- Rate limit AI API calls to avoid excessive costs

## Resources

- **Discord.py Documentation**: https://discordpy.readthedocs.io/
- **Discord Developer Portal**: https://discord.com/developers/applications
- **Project Documentation**: See `docs/` directory
- **TODO List**: See `TODO.md` for planned features
- **Project Structure Guide**: See `PROJECT_STRUCTURE.md`

## Platform-Specific Notes

### Windows
- Use PowerShell scripts (`.ps1`)
- Run `maintain_bot.ps1` for auto-restart
- Virtual environment: `.\venv\Scripts\Activate.ps1`

### Linux/Termux
- Use Bash scripts (`.sh`)
- Run `maintain_bot.sh` for auto-restart
- Virtual environment: `source venv/bin/activate`
- Termux: May need to use `mysqld_safe &` to start MySQL
