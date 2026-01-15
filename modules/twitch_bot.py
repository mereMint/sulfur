"""
Twitch Bot Module for Sulfur Bot

Modular Twitch integration with:
- Chat monitoring and response
- Custom commands
- User tracking and follows
- Auto category changing
- Stream metadata management

Requires aiohttp package: pip install aiohttp
"""

import asyncio
import json
import os
import re
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable, Any, Tuple, TYPE_CHECKING
from collections import defaultdict

# Try to import aiohttp - it's required for Twitch API calls
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

# For type checking only (when aiohttp is not installed)
if TYPE_CHECKING:
    import aiohttp

# For Twitch IRC connection
import socket
import ssl as ssl_module

from modules.logger_utils import get_logger

logger = get_logger('twitch')

# Log if aiohttp is not available
if not AIOHTTP_AVAILABLE:
    logger.warning("aiohttp is not installed. Twitch bot functionality will be limited.")
    logger.warning("To enable full Twitch bot features, install aiohttp: pip install aiohttp")

# ==============================================================================
# Configuration and Constants
# ==============================================================================

TWITCH_CONFIG_FILE = "config/twitch_config.json"
TWITCH_STATE_FILE = "config/twitch_state.json"
TWITCH_COMMANDS_FILE = "config/twitch_commands.json"

# Twitch IRC servers
TWITCH_IRC_SERVER = "irc.chat.twitch.tv"
TWITCH_IRC_PORT = 6697  # SSL port

# Twitch API endpoints
TWITCH_API_BASE = "https://api.twitch.tv/helix"
TWITCH_AUTH_URL = "https://id.twitch.tv/oauth2/token"

# Default configuration
DEFAULT_CONFIG = {
    "enabled": False,
    "channel": "",  # Twitch channel to join (without #)
    "bot_username": "",  # Bot's Twitch username
    "oauth_token": "",  # OAuth token (get from https://twitchapps.com/tmi/)
    "client_id": "",  # Twitch application client ID
    "client_secret": "",  # Twitch application client secret

    # Features
    "features": {
        "chat_monitoring": True,
        "commands": True,
        "user_tracking": True,
        "follows_tracking": True,
        "auto_category": False,
        "spam_protection": True,
        "auto_shoutout": True
    },

    # Auto category changing settings
    "auto_category": {
        "enabled": False,
        "check_interval": 60,  # Check every 60 seconds
        "image_folder": "twitch_images",  # Folder to scan for category images
        "confidence_threshold": 0.7  # Minimum confidence for category detection
    },

    # Spam protection
    "spam_protection": {
        "max_messages_per_minute": 20,
        "timeout_duration": 120,  # seconds
        "link_protection": True,
        "caps_protection": True
    },

    # Auto shoutout
    "auto_shoutout": {
        "enabled": False,
        "message": "Welcome @{username}! Check out their stream at https://twitch.tv/{username}"
    }
}

# Default commands
DEFAULT_COMMANDS = {
    "!discord": {
        "response": "Join our Discord: https://discord.gg/your-server",
        "enabled": True,
        "cooldown": 30,
        "mod_only": False
    },
    "!commands": {
        "response": "Available commands: !discord, !uptime, !lurk, !followage",
        "enabled": True,
        "cooldown": 60,
        "mod_only": False
    },
    "!lurk": {
        "response": "Thanks for lurking @{user}! Enjoy the stream!",
        "enabled": True,
        "cooldown": 300,
        "mod_only": False
    },
    "!uptime": {
        "response": "Stream has been live for {uptime}",
        "enabled": True,
        "cooldown": 30,
        "mod_only": False
    }
}

# ==============================================================================
# State Management
# ==============================================================================

class TwitchState:
    """Manage Twitch bot state"""

    def __init__(self):
        self.connected = False
        self.channel_joined = False
        self.stream_live = False
        self.stream_start_time = None
        self.viewer_count = 0
        self.followers = []
        self.chatters = set()
        self.message_count = 0
        self.command_count = 0

        # User tracking
        self.user_messages = defaultdict(list)  # username -> [timestamps]
        self.user_first_seen = {}  # username -> timestamp

        # Command cooldowns
        self.command_cooldowns = {}  # command -> last_used_time

        self.load_state()

    def load_state(self):
        """Load state from file"""
        if os.path.exists(TWITCH_STATE_FILE):
            try:
                with open(TWITCH_STATE_FILE, 'r') as f:
                    data = json.load(f)

                # Restore stream state
                self.stream_live = data.get('stream_live', False)
                if data.get('stream_start_time'):
                    self.stream_start_time = datetime.fromisoformat(data['stream_start_time'])

                # Restore tracking data
                self.followers = data.get('followers', [])
                self.user_first_seen = data.get('user_first_seen', {})

                logger.info(f"Loaded Twitch state: {len(self.followers)} followers tracked")
            except Exception as e:
                logger.error(f"Failed to load Twitch state: {e}")

    def save_state(self):
        """Save state to file"""
        try:
            os.makedirs(os.path.dirname(TWITCH_STATE_FILE), exist_ok=True)

            data = {
                'stream_live': self.stream_live,
                'stream_start_time': self.stream_start_time.isoformat() if self.stream_start_time else None,
                'followers': self.followers[-1000:],  # Keep last 1000 followers
                'user_first_seen': dict(list(self.user_first_seen.items())[-1000:]),  # Last 1000 users
                'last_updated': datetime.now(timezone.utc).isoformat()
            }

            with open(TWITCH_STATE_FILE, 'w') as f:
                json.dump(data, f, indent=2)

            logger.debug("Twitch state saved")
        except Exception as e:
            logger.error(f"Failed to save Twitch state: {e}")

# ==============================================================================
# Configuration Management
# ==============================================================================

class TwitchConfig:
    """Manage Twitch bot configuration"""

    def __init__(self):
        self.config = DEFAULT_CONFIG.copy()
        self.commands = DEFAULT_COMMANDS.copy()
        self.load()

    def load(self):
        """Load configuration from file"""
        # Load main config
        if os.path.exists(TWITCH_CONFIG_FILE):
            try:
                with open(TWITCH_CONFIG_FILE, 'r') as f:
                    loaded = json.load(f)
                    self.config.update(loaded)
                logger.info("Loaded Twitch configuration")
            except Exception as e:
                logger.error(f"Failed to load Twitch config: {e}")

        # Load commands
        if os.path.exists(TWITCH_COMMANDS_FILE):
            try:
                with open(TWITCH_COMMANDS_FILE, 'r') as f:
                    self.commands = json.load(f)
                logger.info(f"Loaded {len(self.commands)} Twitch commands")
            except Exception as e:
                logger.error(f"Failed to load Twitch commands: {e}")

    def save(self):
        """Save configuration to file"""
        try:
            os.makedirs(os.path.dirname(TWITCH_CONFIG_FILE), exist_ok=True)

            # Save main config
            with open(TWITCH_CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=2)

            # Save commands
            with open(TWITCH_COMMANDS_FILE, 'w') as f:
                json.dump(self.commands, f, indent=2)

            logger.info("Twitch configuration saved")
            return True
        except Exception as e:
            logger.error(f"Failed to save Twitch config: {e}")
            return False

    def get(self, key: str, default=None):
        """Get configuration value"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            value = value.get(k, default)
            if value is None:
                return default
        return value

    def set(self, key: str, value: Any):
        """Set configuration value"""
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
        self.save()

# ==============================================================================
# Twitch Bot Core
# ==============================================================================

class TwitchBot:
    """Main Twitch Bot class"""

    def __init__(self):
        self.config = TwitchConfig()
        self.state = TwitchState()

        # IRC connection
        self.irc_socket = None
        self.running = False
        self.reader = None
        self.writer = None

        # API session (requires aiohttp)
        self.api_session: Optional['aiohttp.ClientSession'] = None
        self.access_token = None

        # Event callbacks
        self.message_callbacks: List[Callable] = []
        self.command_callbacks: Dict[str, Callable] = {}

        # Background tasks
        self.tasks = []

    async def start(self) -> Tuple[bool, str]:
        """Start the Twitch bot"""
        if not self.config.get('enabled'):
            return False, "Twitch bot is disabled in configuration"

        if self.running:
            return False, "Twitch bot is already running"

        # Validate configuration
        if not self.config.get('channel'):
            return False, "Twitch channel not configured"

        if not self.config.get('oauth_token'):
            return False, "OAuth token not configured"

        if not self.config.get('bot_username'):
            return False, "Bot username not configured"

        try:
            self.running = True

            # Initialize API session
            await self._init_api_session()

            # Connect to Twitch IRC
            success, message = await self._connect_irc()
            if not success:
                self.running = False
                return False, message

            # Start background tasks
            self._start_background_tasks()

            logger.info(f"Twitch bot started for channel: {self.config.get('channel')}")
            return True, "Twitch bot started successfully"

        except Exception as e:
            logger.error(f"Failed to start Twitch bot: {e}", exc_info=True)
            self.running = False
            return False, str(e)

    async def stop(self) -> Tuple[bool, str]:
        """Stop the Twitch bot"""
        if not self.running:
            return False, "Twitch bot is not running"

        try:
            self.running = False

            # Cancel background tasks
            for task in self.tasks:
                task.cancel()

            # Disconnect from IRC
            if self.writer:
                self.writer.close()
                await self.writer.wait_closed()

            # Close API session
            if self.api_session:
                await self.api_session.close()

            # Save state
            self.state.save_state()

            logger.info("Twitch bot stopped")
            return True, "Twitch bot stopped successfully"

        except Exception as e:
            logger.error(f"Error stopping Twitch bot: {e}")
            return False, str(e)

    async def _init_api_session(self):
        """Initialize Twitch API session"""
        if not AIOHTTP_AVAILABLE:
            logger.warning("aiohttp not available - Twitch API features disabled")
            logger.warning("Install aiohttp with: pip install aiohttp")
            return

        self.api_session = aiohttp.ClientSession()

        # Get access token if client credentials are provided
        if self.config.get('client_id') and self.config.get('client_secret'):
            await self._get_access_token()

    async def _get_access_token(self):
        """Get Twitch API access token"""
        if not self.api_session:
            logger.debug("API session not available, skipping access token retrieval")
            return

        try:
            params = {
                'client_id': self.config.get('client_id'),
                'client_secret': self.config.get('client_secret'),
                'grant_type': 'client_credentials'
            }

            async with self.api_session.post(TWITCH_AUTH_URL, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.access_token = data.get('access_token')
                    logger.info("Obtained Twitch API access token")
                else:
                    logger.warning(f"Failed to get access token: {resp.status}")
        except Exception as e:
            logger.error(f"Error getting access token: {e}")

    async def _connect_irc(self) -> Tuple[bool, str]:
        """Connect to Twitch IRC"""
        try:
            # Create SSL context
            ssl_context = ssl_module.create_default_context()

            # Connect to Twitch IRC
            self.reader, self.writer = await asyncio.open_connection(
                TWITCH_IRC_SERVER,
                TWITCH_IRC_PORT,
                ssl=ssl_context
            )

            # Authenticate
            oauth_token = self.config.get('oauth_token')
            if not oauth_token.startswith('oauth:'):
                oauth_token = f'oauth:{oauth_token}'

            username = self.config.get('bot_username').lower()

            self.writer.write(f"PASS {oauth_token}\r\n".encode())
            self.writer.write(f"NICK {username}\r\n".encode())
            await self.writer.drain()

            # Request capabilities
            self.writer.write(b"CAP REQ :twitch.tv/membership\r\n")
            self.writer.write(b"CAP REQ :twitch.tv/tags\r\n")
            self.writer.write(b"CAP REQ :twitch.tv/commands\r\n")
            await self.writer.drain()

            # Join channel
            channel = self.config.get('channel').lower()
            if not channel.startswith('#'):
                channel = f'#{channel}'

            self.writer.write(f"JOIN {channel}\r\n".encode())
            await self.writer.drain()

            self.state.connected = True
            self.state.channel_joined = True

            # Start message reader
            asyncio.create_task(self._read_messages())

            logger.info(f"Connected to Twitch IRC and joined {channel}")
            return True, f"Connected to {channel}"

        except Exception as e:
            logger.error(f"Failed to connect to Twitch IRC: {e}")
            return False, str(e)

    async def _read_messages(self):
        """Read and process messages from Twitch IRC"""
        while self.running:
            try:
                line = await self.reader.readline()
                if not line:
                    logger.warning("Connection closed by Twitch")
                    break

                message = line.decode('utf-8', errors='ignore').strip()

                # Handle PING
                if message.startswith('PING'):
                    pong = message.replace('PING', 'PONG')
                    self.writer.write(f"{pong}\r\n".encode())
                    await self.writer.drain()
                    continue

                # Process message
                await self._process_message(message)

            except Exception as e:
                if self.running:
                    logger.error(f"Error reading IRC message: {e}")
                break

        logger.info("IRC message reader stopped")

    async def _process_message(self, raw_message: str):
        """Process a Twitch IRC message"""
        try:
            # Parse PRIVMSG
            if 'PRIVMSG' in raw_message:
                # Extract username and message
                match = re.search(r':(\w+)!\w+@\w+\.tmi\.twitch\.tv PRIVMSG #\w+ :(.+)', raw_message)
                if match:
                    username = match.group(1)
                    message = match.group(2)

                    # Track user
                    self._track_user(username)

                    # Update state
                    self.state.message_count += 1
                    self.state.chatters.add(username)

                    # Check for spam
                    if self.config.get('features.spam_protection') and self._is_spam(username, message):
                        logger.info(f"Spam detected from {username}: {message[:50]}")
                        return

                    # Call message callbacks
                    for callback in self.message_callbacks:
                        try:
                            await callback(username, message)
                        except Exception as e:
                            logger.error(f"Error in message callback: {e}")

                    # Check for commands
                    if message.startswith('!'):
                        await self._handle_command(username, message)

        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def _track_user(self, username: str):
        """Track user activity"""
        now = time.time()

        # Track first seen
        if username not in self.state.user_first_seen:
            self.state.user_first_seen[username] = now

        # Track message times (for spam detection)
        self.state.user_messages[username].append(now)

        # Keep only recent messages (last 60 seconds)
        cutoff = now - 60
        self.state.user_messages[username] = [
            t for t in self.state.user_messages[username] if t > cutoff
        ]

    def _is_spam(self, username: str, message: str) -> bool:
        """Check if message is spam"""
        spam_config = self.config.get('spam_protection', {})

        # Check message rate
        max_per_minute = spam_config.get('max_messages_per_minute', 20)
        recent_messages = len(self.state.user_messages.get(username, []))
        if recent_messages > max_per_minute:
            return True

        # Check for excessive caps
        if spam_config.get('caps_protection', True):
            if len(message) > 10 and sum(1 for c in message if c.isupper()) / len(message) > 0.7:
                return True

        # Check for links (if not allowed)
        if spam_config.get('link_protection', True):
            if re.search(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', message):
                return True

        return False

    async def _handle_command(self, username: str, message: str):
        """Handle a command"""
        try:
            parts = message.split()
            command = parts[0].lower()
            args = parts[1:] if len(parts) > 1 else []

            # Check if command exists
            if command not in self.config.commands:
                return

            cmd_config = self.config.commands[command]

            # Check if enabled
            if not cmd_config.get('enabled', True):
                return

            # Check cooldown
            cooldown = cmd_config.get('cooldown', 0)
            if cooldown > 0:
                last_used = self.state.command_cooldowns.get(command, 0)
                if time.time() - last_used < cooldown:
                    return

            # Update cooldown
            self.state.command_cooldowns[command] = time.time()
            self.state.command_count += 1

            # Format response
            response = cmd_config.get('response', '')
            response = response.replace('{user}', username)
            response = response.replace('{username}', username)

            # Add uptime if needed
            if '{uptime}' in response:
                uptime = self._get_uptime()
                response = response.replace('{uptime}', uptime)

            # Send response
            await self.send_message(response)

            logger.info(f"Command {command} executed by {username}")

        except Exception as e:
            logger.error(f"Error handling command: {e}")

    def _get_uptime(self) -> str:
        """Get stream uptime"""
        if not self.state.stream_live or not self.state.stream_start_time:
            return "Stream is offline"

        delta = datetime.now(timezone.utc) - self.state.stream_start_time
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60
        return f"{hours}h {minutes}m"

    async def send_message(self, message: str):
        """Send a message to the chat"""
        if not self.writer:
            return

        try:
            channel = self.config.get('channel').lower()
            if not channel.startswith('#'):
                channel = f'#{channel}'

            self.writer.write(f"PRIVMSG {channel} :{message}\r\n".encode())
            await self.writer.drain()

            logger.debug(f"Sent message: {message}")
        except Exception as e:
            logger.error(f"Error sending message: {e}")

    def _start_background_tasks(self):
        """Start background tasks"""
        # Stream status checker
        task = asyncio.create_task(self._check_stream_status())
        self.tasks.append(task)

        # State saver
        task = asyncio.create_task(self._periodic_state_save())
        self.tasks.append(task)

        # Auto category changer (if enabled)
        if self.config.get('auto_category.enabled'):
            task = asyncio.create_task(self._auto_category_updater())
            self.tasks.append(task)

    async def _check_stream_status(self):
        """Periodically check stream status"""
        while self.running:
            try:
                await asyncio.sleep(60)  # Check every minute

                if not self.access_token or not self.api_session:
                    continue

                # Get stream info from API
                channel = self.config.get('channel')
                headers = {
                    'Client-ID': self.config.get('client_id'),
                    'Authorization': f'Bearer {self.access_token}'
                }

                url = f"{TWITCH_API_BASE}/streams?user_login={channel}"
                async with self.api_session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        streams = data.get('data', [])

                        was_live = self.state.stream_live
                        self.state.stream_live = len(streams) > 0

                        if self.state.stream_live:
                            if not was_live:
                                # Stream just went live
                                self.state.stream_start_time = datetime.now(timezone.utc)
                                logger.info("Stream went live!")

                            # Update viewer count
                            self.state.viewer_count = streams[0].get('viewer_count', 0)
                        else:
                            if was_live:
                                # Stream just ended
                                logger.info("Stream ended")
                                self.state.stream_start_time = None
                                self.state.viewer_count = 0

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error checking stream status: {e}")

    async def _periodic_state_save(self):
        """Periodically save state"""
        while self.running:
            try:
                await asyncio.sleep(300)  # Save every 5 minutes
                self.state.save_state()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error saving state: {e}")

    async def _auto_category_updater(self):
        """Auto update stream category based on images"""
        while self.running:
            try:
                interval = self.config.get('auto_category.check_interval', 60)
                await asyncio.sleep(interval)

                # TODO: Implement image-based category detection
                # This would use computer vision to detect game/category from screenshots
                logger.debug("Auto category update check (not yet implemented)")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in auto category updater: {e}")

    # Public API methods

    def is_running(self) -> bool:
        """Check if bot is running"""
        return self.running

    def get_status(self) -> Dict[str, Any]:
        """Get bot status"""
        return {
            'running': self.running,
            'connected': self.state.connected,
            'channel': self.config.get('channel'),
            'stream_live': self.state.stream_live,
            'viewer_count': self.state.viewer_count,
            'uptime': self._get_uptime() if self.state.stream_live else None,
            'chatters': len(self.state.chatters),
            'message_count': self.state.message_count,
            'command_count': self.state.command_count,
            'followers_tracked': len(self.state.followers)
        }

    def add_command(self, command: str, response: str, cooldown: int = 30, mod_only: bool = False):
        """Add a custom command"""
        if not command.startswith('!'):
            command = f'!{command}'

        self.config.commands[command] = {
            'response': response,
            'enabled': True,
            'cooldown': cooldown,
            'mod_only': mod_only
        }
        self.config.save()

    def remove_command(self, command: str):
        """Remove a command"""
        if not command.startswith('!'):
            command = f'!{command}'

        if command in self.config.commands:
            del self.config.commands[command]
            self.config.save()

    def get_commands(self) -> Dict[str, Any]:
        """Get all commands"""
        return self.config.commands

# ==============================================================================
# Global Instance
# ==============================================================================

_twitch_bot_instance: Optional[TwitchBot] = None

def get_twitch_bot() -> TwitchBot:
    """Get global Twitch bot instance"""
    global _twitch_bot_instance
    if _twitch_bot_instance is None:
        _twitch_bot_instance = TwitchBot()
    return _twitch_bot_instance

async def start_twitch_bot() -> Tuple[bool, str]:
    """Start the Twitch bot"""
    bot = get_twitch_bot()
    return await bot.start()

async def stop_twitch_bot() -> Tuple[bool, str]:
    """Stop the Twitch bot"""
    bot = get_twitch_bot()
    return await bot.stop()

def get_twitch_status() -> Dict[str, Any]:
    """Get Twitch bot status"""
    bot = get_twitch_bot()
    return bot.get_status()
