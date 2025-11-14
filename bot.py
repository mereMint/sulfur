import asyncio
import json
import discord
import random
import os
from collections import deque
import re
from datetime import datetime, timedelta, timezone

# --- NEW: Library Version Check ---
# This code requires discord.py version 2.0 or higher for slash commands.
if discord.__version__.split('.')[0] < '2':
    print("Error: Your discord.py version is too old.")
    print(f"You have version {discord.__version__}, but this bot requires version 2.0.0 or higher.")
    print("Please update it by running: pip install -U discord.py")
    exit()

from discord import app_commands
from discord.ext import tasks
from werwolf import WerwolfGame, FakeUser
from api_helpers import get_chat_response, get_werwolf_tts_message, get_random_names, get_relationship_summary_from_api

# --- CONFIGURATION ---

# !! WARNING: This is the "easy" way, NOT the "safe" way. !!
# !! DO NOT SHARE THIS FILE WITH YOUR KEYS IN IT. !!

# 1. SET these as environment variables
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# --- NEW: Database Configuration ---
# Set these as environment variables for security, or hardcode for testing.
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_USER = os.environ.get("DB_USER", "sulfur_bot_user")
DB_PASS = os.environ.get("DB_PASS", "") # No password is set for this user
DB_NAME = os.environ.get("DB_NAME", "sulfur_bot")

if not DISCORD_BOT_TOKEN:
    print("Error: DISCORD_BOT_TOKEN environment variable is not set.")
    print("Please set it before running the bot.")
    exit()

# --- REFACTORED: Check for API keys based on provider ---
def check_api_keys(cfg):
    """Checks if the required API key for the selected provider is set."""
    provider = cfg.get('api', {}).get('provider')
    if provider == 'gemini' and not GEMINI_API_KEY:
        return "Error: API provider is 'gemini' but GEMINI_API_KEY is not set."
    if provider == 'openai' and not OPENAI_API_KEY:
        return "Error: API provider is 'openai' but OPENAI_API_KEY is not set."
    return None

# --- NEW: Load Configuration from JSON ---
def load_config():
    """Loads settings from config.json and the system prompt."""
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)

        prompt_file = config.get("bot", {}).get("system_prompt_file", "system_prompt.txt")
        with open(prompt_file, "r", encoding="utf-8") as f:
            config["bot"]["system_prompt"] = f.read()
            
        return config
    except FileNotFoundError as e:
        print(f"FATAL: Configuration file not found: {e.filename}. Please ensure 'config.json' and the prompt file exist.")
        exit()
    except json.JSONDecodeError:
        print("FATAL: 'config.json' is malformed. Please check the JSON syntax.")
        exit()

config = load_config()

# --- REFACTORED: Validate API keys after loading config ---
key_error = check_api_keys(config)
if key_error:
    print(key_error)
    exit()

# --- DISCORD BOT SETUP ---

# You gotta enable "Intents" for the bot in the Discord Dev Portal
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True  # Lets it read the message
intents.guilds = True           # Needs this for channel context
intents.voice_states = True      # To track who joins/leaves VCs
intents.members = True           # To get the full member list for presence updates
intents.presences = True         # To get member status (online, idle, etc.)

# --- NEW: Werwolf Game State ---
# This will store active games, mapping a channel ID to a WerwolfGame object.
active_werwolf_games = {}

# --- NEW: Import and initialize DB helpers ---
from db_helpers import init_db_pool, initialize_database, get_leaderboard, add_xp, get_player_rank, get_level_leaderboard, save_message_to_history, get_chat_history, get_relationship_summary, update_relationship_summary, save_bulk_history, clear_channel_history, update_user_presence, add_balance, update_spotify_history, get_all_managed_channels, remove_managed_channel, get_managed_channel_config, update_managed_channel_config, log_message_stat, log_vc_minutes, get_wrapped_stats_for_period, get_user_wrapped_stats, log_stat_increment
import db_helpers
db_helpers.init_db_pool(DB_HOST, DB_USER, DB_PASS, DB_NAME)
from level_system import grant_xp, get_xp_for_level
# --- NEW: Import Voice Manager ---
import voice_manager
# --- NEW: Import Economy ---
from economy import calculate_level_up_bonus

db_helpers.initialize_database()

# --- NEW: Import API helpers that were moved ---
from api_helpers import get_wrapped_summary_from_api

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Handles errors from the command tree globally."""
    # If the interaction is already done, we can't send a new response.
    # This can happen if a command's own error handler has already responded.
    if interaction.response.is_done():
        return

    if isinstance(error, app_commands.CommandNotFound):
        # This can happen if a user tries to use a command that was recently removed.
        # The command might still be cached on their Discord client.
        message = (
            "Huch, dieser Befehl ist veraltet. Dein Discord hat noch die alte Version gespeichert. **Bitte versuche, die Discord-App vollständig zu schließen und neu zu starten**, um die Befehlsliste zu aktualisieren.",
        )
    elif isinstance(error, app_commands.TransformerError):
        # NEW: Handle cases where a user provides invalid input for an argument (e.g., text for a user mention)
        message = (
            f"Ich konnte die Eingabe '{error.value}' nicht verstehen. Bitte wähle die Option (z.B. den Benutzer) direkt aus der Liste aus, die Discord vorschlägt.",
        )
    elif isinstance(error, app_commands.CheckFailure):
        # This is a generic catch-all for when a command's check fails.
        # The custom checks like `check_channel_owner` already send their own specific messages.
        # This will primarily catch failures from `is_admin_or_authorised`.
        message = "Dir fehlt die Berechtigung, diesen Befehl zu verwenden. Du musst entweder ein Admin sein oder die 'authorised' Rolle haben."
    elif isinstance(error, app_commands.BotMissingPermissions):
        # The bot lacks permissions to perform an action (e.g., create channels, send messages).
        missing_perms = ", ".join(error.missing_permissions)
        message = f"Ich kann das nicht tun, weil mir die folgenden Berechtigungen fehlen: `{missing_perms}`. Bitte gib mir die nötigen Rechte, du Noob. :erm:"
    elif isinstance(error, app_commands.CommandOnCooldown):
        # The user is spamming a command.
        message = f"Chill mal, du kannst diesen Befehl erst in **{error.retry_after:.1f} Sekunden** wieder benutzen."
    else:
        # For other errors, log them to the console.
        print(f"Unhandled exception in command tree: {error}")
        message = "Ups, da ist etwas schiefgelaufen. Wahrscheinlich deine Schuld. :dono:"

    await interaction.response.send_message(message, ephemeral=True)

async def split_message(text, limit=2000):
    """
    Splits a long message into chunks for Discord.
    """
    chunks = []
    current_chunk = ""
    for line in text.split('\n'):
        if len(current_chunk) + len(line) + 1 > limit:
            chunks.append(current_chunk)
            current_chunk = line
        else:
            current_chunk += '\n' + line
    chunks.append(current_chunk.strip()) # Add the last chunk
    return chunks

async def replace_emoji_tags(text, client):
    """
    Replaces :emoji_name: style tags with the actual Discord emoji object
    from any server the bot is in.
    """
    # Find all :emoji_name: tags in the text
    emoji_tags = re.findall(r':(\w+):', text)
    if not emoji_tags:
        return text

    # Create a global mapping of all available emoji names to their string representation
    emoji_map = {}
    for emoji in client.emojis:
        if emoji.name not in emoji_map:
            emoji_map[emoji.name] = str(emoji)

    # Replace the tags found in the message
    for tag in set(emoji_tags): # Use set to avoid replacing the same tag multiple times
        if tag in emoji_map:
            text = text.replace(f":{tag}:", emoji_map[tag])
    return text

@client.event
async def on_ready():
    """Fires when the bot logs in."""
    # --- NEW: Clean up leftover game channels on restart ---
    print("Checking for leftover game channels...")
    for guild in client.guilds:
        for category in guild.categories:
            if category.name == "🐺 WERWOLF SPIEL 🐺":
                print(f"Found leftover category in '{guild.name}'. Cleaning up...")
                for channel in category.channels:
                    try:
                        await channel.delete(reason="Bot restart cleanup")
                    except (discord.Forbidden, discord.NotFound):
                        pass # Ignore if we can't delete or it's already gone
                try:
                    await category.delete(reason="Bot restart cleanup")
                except (discord.Forbidden, discord.NotFound):
                    pass
    # --- NEW: Create 'authorised' role on boot ---
    print("Checking for 'authorised' role in guilds...")
    for guild in client.guilds:
        if not discord.utils.get(guild.roles, name=config['bot']['authorised_role']):
            try:
                await guild.create_role(name=config['bot']['authorised_role'], reason="Rolle für Bot-Admin-Befehle")
                print(f"Rolle 'authorised' im Server '{guild.name}' erstellt.")
            except discord.Forbidden:
                print(f"Konnte Rolle '{config['bot']['authorised_role']}' in '{guild.name}' nicht erstellen. Fehlende Berechtigung 'Rollen verwalten'.")

    # --- NEW: Clean up orphaned voice channels on restart ---
    print("Checking for orphaned voice channels...")
    managed_channel_ids = await db_helpers.get_all_managed_channels()
    if managed_channel_ids:
        for channel_id in managed_channel_ids:
            channel = client.get_channel(channel_id)
            if not channel:
                # Channel doesn't exist on Discord, remove from DB
                await db_helpers.remove_managed_channel(channel_id)
                print(f"Removed non-existent channel {channel_id} from database.")
            elif isinstance(channel, discord.VoiceChannel) and len(channel.members) == 0:
                # Channel exists but is empty, delete it
                try:
                    await channel.delete(reason="Bot restart cleanup (empty channel)")
                    await db_helpers.remove_managed_channel(channel_id) # Also remove from DB
                    print(f"Cleaned up empty orphaned channel: {channel.name} ({channel_id})")
                except (discord.Forbidden, discord.NotFound):
                    await db_helpers.remove_managed_channel(channel_id) # Still remove from DB if delete fails
    synced = await tree.sync()
    # --- NEW: Start the background task for voice XP ---
    if not grant_voice_xp.is_running():
        grant_voice_xp.start()
    # --- NEW: Start the background task for presence updates ---
    if not update_presence_task.is_running():
        update_presence_task.start()
    # --- NEW: Start the background task for Wrapped event management ---
    if not manage_wrapped_event.is_running():
        manage_wrapped_event.start()
    print(f"Synced {len(synced)} global commands.")

    print(f'Ayo, the bot is logged in and ready, fam! ({client.user})')
    print('Let\'s chat.')

@tasks.loop(minutes=15)
async def update_presence_task():
    """A background task that periodically updates the bot's presence to watch a random user."""
    update_presence_task.change_interval(minutes=config['bot']['presence']['update_interval_minutes'])

    if not client.guilds:
        return

    # --- REFACTORED: Find an online user and set a cool presence ---
    all_members = []
    # Get all non-bot members from all guilds
    for guild in client.guilds:
        all_members.extend([m for m in guild.members if not m.bot])

    random.shuffle(all_members)

    for member_candidate in all_members:
        try:
            # Fetch the member again to get the most up-to-date status
            # We fetch the member to ensure they still exist in the guild.
            fresh_member = await member_candidate.guild.fetch_member(member_candidate.id) 
            if fresh_member:
                # Found a valid user (online or offline), now set the cool presence
                templates = config['bot']['presence']['activity_templates']
                template = random.choice(templates)
                activity_name = template.format(user=fresh_member.display_name)
                
                print(f"  -> Presence update: {activity_name}")
                await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=activity_name))
                return  # Success, exit the task for this run
        except (discord.NotFound, discord.HTTPException):
            continue  # Member left or another issue, try next candidate

    # Fallback if no human members were found at all.
    print("  -> Presence update: No human members found. Using fallback.")
    fallback_activity = config.get('bot', {}).get('presence', {}).get('fallback_activity', "euch beim AFK sein zu")
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=fallback_activity))

@update_presence_task.before_loop
async def before_update_presence_task():
    await client.wait_until_ready()

@client.event
async def on_presence_update(before, after):
    """Fires when a member's status, activity, etc. changes. Used for tracking."""
    # Ignore bots
    if after.bot:
        return
        
    # --- NEW: Ignore presence updates from offline users to reduce noise ---
    if after.status == discord.Status.offline and before.status == discord.Status.offline:
        return

    # We only care about changes in status or activity
    if before.status == after.status and before.activity == after.activity:
        return

    # --- NEW: Spotify Tracking ---
    if isinstance(after.activity, discord.Spotify):
        # Check if the song is different from the last one to avoid spamming the DB
        is_new_song = not isinstance(before.activity, discord.Spotify) or before.activity.title != after.activity.title
        if is_new_song:
            await db_helpers.update_spotify_history(
                client=client, # Pass client for logging
                user_id=after.id,
                display_name=after.display_name,
                song_title=after.activity.title,
                song_artist=after.activity.artist
            )

    activity_name = None
    if after.activity:
        # For games, streaming, etc., it has a name. For custom status, it's in 'state'.
        activity_name = after.activity.name or after.activity.state

    # Update the database with the new presence info
    await db_helpers.update_user_presence(
        user_id=after.id,
        display_name=after.display_name,
        status=str(after.status),
        activity_name=activity_name
    )
    # --- NEW: Log activity for Wrapped ---
    if activity_name:
        # We only log the primary activity name to avoid noise from custom statuses
        stat_period = datetime.now(timezone.utc).strftime('%Y-%m')
        await db_helpers.log_stat_increment(after.id, stat_period, 'activity_usage', key=activity_name)

@tasks.loop(minutes=1)
async def grant_voice_xp():
    """A background task that grants XP to users in voice channels every minute."""
    # Iterate through all guilds the bot is in
    for guild in client.guilds:
        for member in guild.members:
            # Conditions to grant XP:
            # 1. Member is in a voice channel.
            # 2. Member is not a bot.
            # 3. Member is not server-deafened (to prevent AFK farming).
            if member.voice and not member.bot and not member.voice.deaf:
                stat_period = datetime.now(timezone.utc).strftime('%Y-%m')
                new_level = await db_helpers.add_xp(member.id, member.display_name, config['modules']['leveling']['xp_per_minute_in_vc'])
                await db_helpers.log_vc_minutes(member.id, 1, stat_period) # Log 1 minute for Wrapped
                if new_level:
                    bonus = calculate_level_up_bonus(new_level, config)
                    await db_helpers.add_balance(member.id, member.display_name, bonus, stat_period)
                    # --- FIX: Send level-up notifications via DM and only for special levels ---
                    if new_level % config['modules']['leveling']['vc_level_up_notification_interval'] == 0:
                        try:
                            await member.send(f"GG! Du bist durch deine Aktivität im Voice-Chat jetzt Level **{new_level}**! :YESS:\n"
                                             f"Du erhältst **{bonus}** Währung als Belohnung!")
                        except discord.Forbidden:
                            print(f"Could not send voice level up DM to {member.name} (DMs likely closed).")

@grant_voice_xp.before_loop
async def before_grant_voice_xp():
    """Ensures the bot is fully logged in before the task starts."""
    await client.wait_until_ready()

# --- NEW: Wrapped Event Management ---

@tasks.loop(hours=24)
async def manage_wrapped_event():
    """
    Manages the creation of the 'Wrapped' event and the distribution of stats.
    Runs once a day.
    """
    now = datetime.now(timezone.utc)
    # We are planning the event for the *current* month's data, to be released *next* month.
    # e.g., when running in November, we plan for November's data to be released in December.
    stat_period = now.strftime('%Y-%m') # e.g., '2025-11'

    # For simplicity, we'll use the first guild the bot is in.
    if not client.guilds:
        return
    guild = client.guilds[0]

    # Calculate the first day of the *next* month for scheduling.
    first_day_of_current_month = now.replace(day=1)
    first_day_of_next_month = (first_day_of_current_month + timedelta(days=32)).replace(day=1)

    # --- 1. Event Scheduling ---
    # Decide on a release date: a random day in the second week of the month.
    release_day = random.randint(config['modules']['wrapped']['release_day_min'], config['modules']['wrapped']['release_day_max'])
    release_date = first_day_of_next_month.replace(day=release_day, hour=18, minute=0, second=0) # 6 PM UTC

    # The day to create the event is one week before the release.
    event_creation_day = release_date - timedelta(days=7)
    event_name = f"Sulfur Wrapped {now.strftime('%B %Y')}"

    # Check if an event for this period already exists
    existing_events = guild.scheduled_events
    event_exists = any(event.name == event_name for event in existing_events)

    # If it's the right day to create the event and it doesn't exist yet
    if now.day == event_creation_day.day and not event_exists:
        print(f"Creating Scheduled Event for '{event_name}'...")
        try:
            await guild.create_scheduled_event(
                name=event_name,
                description=f"Dein persönlicher Server-Jahresrückblick für {now.strftime('%B')}! Die Ergebnisse werden am Event-Tag per DM verschickt.",
                start_time=release_date,
                end_time=release_date + timedelta(hours=1),
                entity_type=discord.EntityType.external,
                location="In deinen DMs!"
            )
            print("Event created successfully.")
        except Exception as e:
            print(f"Failed to create scheduled event: {e}")

    # --- 2. Wrapped Distribution ---
    # Check if today is the release day for the PREVIOUS month's data.
    last_month_first_day = (first_day_of_current_month - timedelta(days=1)).replace(day=1)
    # The release day is based on the *current* month's second week, but for *last* month's data.
    # This needs to be consistent with the event scheduling logic.
    # Let's re-calculate the release date for last month's data.
    last_month_release_date = first_day_of_current_month.replace(day=release_day, hour=18, minute=0, second=0) # 6 PM UTC on the random day of the current month
    last_month_stat_period = last_month_first_day.strftime('%Y-%m')

    # --- FIX: Check the full date, not just the day number ---
    if now.year == last_month_release_date.year and now.month == last_month_release_date.month and now.day == last_month_release_date.day:
        print(f"Distributing Wrapped for period {last_month_stat_period}...")
        stats = await db_helpers.get_wrapped_stats_for_period(last_month_stat_period)

        # --- NEW: Pre-calculate ranks ---
        total_users = len(stats)
        if total_users == 0:
            print(f"No stats found for period {last_month_stat_period}. Skipping distribution.")
            return

        # Create sorted lists for ranking

        for user_stats in stats:
            await _generate_and_send_wrapped_for_user(
                user_stats=user_stats,
                stat_period_date=last_month_first_day,
                all_stats_for_period=stats,
                total_users=total_users
            )

@manage_wrapped_event.before_loop
async def before_manage_wrapped_event():
    await client.wait_until_ready()

# --- NEW: View for paginating the Wrapped DM ---
class WrappedView(discord.ui.View):
    def __init__(self, pages, user: discord.User, timeout=300):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.user = user
        self.current_page = 0
        self.message = None

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.current_page -= 1
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = False
        await self.message.edit(embed=self.pages[self.current_page], view=self)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.current_page += 1
        self.next_button.disabled = self.current_page == len(self.pages) - 1
        self.previous_button.disabled = False
        await self.message.edit(embed=self.pages[self.current_page], view=self)

    async def send_initial_message(self):
        """Sends the first page to the user's DMs."""
        self.previous_button.disabled = True
        self.next_button.disabled = len(self.pages) <= 1
        self.message = await self.user.send(embed=self.pages[0], view=self)

async def _generate_and_send_wrapped_for_user(user_stats, stat_period_date, all_stats_for_period, total_users):
    """Helper function to generate and DM the Wrapped story to a single user."""
    user_id = user_stats['user_id']
    user = None
    try:
        # Use fetch_user to guarantee we can find the user, even if not cached.
        user = await client.fetch_user(user_id)
    except discord.NotFound:
        print(f"  - Skipping user ID {user_id}: User could not be found (account may be deleted).")
        return

    print(f"  - [Wrapped] Generating for {user.name} ({user.id})...")

    pages = []
    color = user.color or discord.Color.purple()

    # Find favorite channel
    fav_channel_id = None
    if user_stats.get('channel_usage'):
        print("    - [Wrapped] Calculating favorite channel...")
        try:
            channel_usage = json.loads(user_stats['channel_usage'])
            if channel_usage:
                fav_channel_id = max(channel_usage, key=channel_usage.get)
        except (json.JSONDecodeError, TypeError):
            fav_channel_id = None

    # Find favorite emoji
    fav_emoji_display = "N/A"
    if user_stats.get('emoji_usage'):
        print("    - [Wrapped] Calculating favorite emoji...")
        emoji_usage = json.loads(user_stats['emoji_usage'])
        if emoji_usage:
            fav_emoji_name = max(emoji_usage, key=emoji_usage.get)
            emoji_obj = discord.utils.get(client.emojis, name=fav_emoji_name)
            fav_emoji_display = str(emoji_obj) if emoji_obj else f"`:{fav_emoji_name}:`"

    # Calculate stats
    print("    - [Wrapped] Calculating general stats...")
    vc_hours = user_stats.get('minutes_in_vc', 0) / 60
    fav_channel_obj = client.get_channel(int(fav_channel_id)) if fav_channel_id else None
    fav_activity = "Nichts tun"
    if user_stats.get('activity_usage'):
        print("    - [Wrapped] Calculating favorite activity...")
        activity_usage = json.loads(user_stats['activity_usage'])
        if activity_usage:
            fav_activity = max(activity_usage, key=activity_usage.get)

    # --- Page 1: Intro ---
    intro_embed = discord.Embed(
        title=f"Dein {stat_period_date.strftime('%B')} Wrapped ist da, {user.display_name}!",
        description="Bist du bereit, in deine Stats einzutauchen und zu sehen, ob du ein No-Lifer bist? Let's go.",
        color=color
    )
    intro_embed.set_thumbnail(url=user.display_avatar.url)
    intro_embed.set_image(url=config['modules']['wrapped']['intro_gif_url'])
    pages.append(intro_embed)

    # --- Page 2: Filler ---
    filler_embed = discord.Embed(title="Zuerst mal...", description="Wie viel Zeit hast du hier eigentlich verbracht? 🧐", color=color)
    pages.append(filler_embed)

    # --- FIX: Calculate ranks inside the function to ensure they are for the correct period ---
    print("    - [Wrapped] Calculating message and VC ranks...")
    message_ranks = sorted(all_stats_for_period, key=lambda x: x.get('message_count', 0))
    vc_ranks = sorted(all_stats_for_period, key=lambda x: x.get('minutes_in_vc', 0))

    # --- Page 3: Message Stats ---
    message_rank_text = _get_percentile_rank(user.id, message_ranks, total_users)
    msg_embed = discord.Embed(title="Du und der Chat", color=color)
    msg_embed.add_field(name="Gesendete Nachrichten", value=f"## `{user_stats.get('message_count', 0)}`", inline=False)
    msg_embed.add_field(name="Dein Rang", value=f"Du gehörst zu den **{message_rank_text}** der aktivsten Chatter!", inline=False)
    pages.append(msg_embed)

    # --- Page 4: VC Stats ---
    vc_rank_text = _get_percentile_rank(user.id, vc_ranks, total_users)
    vc_embed = discord.Embed(title="Deine Voice-Chat Story", color=color)
    vc_embed.add_field(name="Stunden im Voice-Chat", value=f"## `{vc_hours:.2f}`", inline=False)
    vc_embed.add_field(name="Dein Rang", value=f"Du warst in den **{vc_rank_text}** der größten Quasselstrippen!", inline=False)
    pages.append(vc_embed)

    # --- NEW: Page 5: Top 5 Channels ---
    if user_stats.get('channel_usage'):
        print("    - [Wrapped] Generating Top 5 Channels page...")
        channel_usage = json.loads(user_stats['channel_usage'])
        sorted_channels = sorted(channel_usage.items(), key=lambda item: item[1], reverse=True)
        top_channels_text = ""
        for i, (channel_id, count) in enumerate(sorted_channels[:5]):
            top_channels_text += f"**{i+1}.** <#{channel_id}> - `{count}` Nachrichten\n"
        
        if top_channels_text:
            channel_embed = discord.Embed(title="Deine Top 5 Kanäle", description=top_channels_text, color=color)
            pages.append(channel_embed)

    # --- NEW: Page 6: Top 5 Emojis ---
    if user_stats.get('emoji_usage'):
        print("    - [Wrapped] Generating Top 5 Emojis page...")
        emoji_usage = json.loads(user_stats['emoji_usage'])
        sorted_emojis = sorted(emoji_usage.items(), key=lambda item: item[1], reverse=True)
        top_emojis_text = ""
        for i, (emoji_name, count) in enumerate(sorted_emojis[:5]):
            emoji_obj = discord.utils.get(client.emojis, name=emoji_name)
            emoji_display = str(emoji_obj) if emoji_obj else f":{emoji_name}:"
            top_emojis_text += f"**{i+1}.** {emoji_display} - `{count}` mal benutzt\n"

        if top_emojis_text:
            emoji_embed = discord.Embed(title="Deine Top 5 Emojis", description=top_emojis_text, color=color)
            pages.append(emoji_embed)

    # --- NEW: Page 7: Top 5 Activities ---
    if user_stats.get('activity_usage'):
        print("    - [Wrapped] Generating Top 5 Activities page...")
        activity_usage = json.loads(user_stats['activity_usage'])
        # Filter out generic activities that aren't very informative
        filtered_activities = {k: v for k, v in activity_usage.items() if k.lower() not in ['custom status', 'spotify']}
        sorted_activities = sorted(filtered_activities.items(), key=lambda item: item[1], reverse=True)
        top_activities_text = ""
        for i, (activity_name, count) in enumerate(sorted_activities[:5]):
            # The count here is an arbitrary number from presence updates, so we show it as a relative score
            top_activities_text += f"**{i+1}.** `{activity_name}`\n"

        if top_activities_text:
            activity_embed = discord.Embed(title="Deine Top 5 Aktivitäten", description=top_activities_text, color=color)
            activity_embed.set_footer(text="Basiert auf den Spielen & Programmen, die du am häufigsten offen hattest.")
            pages.append(activity_embed)

    # --- Page 6: Gemini Summary ---
    gemini_stats = {
        "vc_hours": vc_hours, "fav_channel_name": f"#{fav_channel_obj.name}" if fav_channel_obj else "Unbekannt",
        "fav_emoji_display": fav_emoji_display, "fav_activity": fav_activity,
        "message_rank_text": message_rank_text, "vc_rank_text": vc_rank_text
    }
    summary_text, _ = await get_wrapped_summary_from_api(user.display_name, gemini_stats, config, GEMINI_API_KEY, OPENAI_API_KEY)
    print(f"    - [Wrapped] Generated Gemini summary for {user.name}.")
    summary_embed = discord.Embed(title="Mein Urteil über dich", description=f"## _{summary_text}_", color=color)
    summary_embed.set_footer(text="Nächstes Mal gibst du dir mehr Mühe, ja? :erm:")
    pages.append(summary_embed)

    try:
        view = WrappedView(pages, user)
        await view.send_initial_message()
        print(f"  - [Wrapped] Successfully sent DM to {user.name}.")
    except discord.Forbidden:
        print(f"  - [Wrapped] FAILED to DM {user.name} (DMs likely closed).")
    except Exception as e:
        print(f"  - [Wrapped] An unexpected error occurred for {user.name}: {e}")

def _get_percentile_rank(user_id, ranked_list, total_users):
    """Helper function to calculate a user's percentile rank from a sorted list."""
    if total_users < 2: return "Top 100%" # Avoid division by zero
    try:
        user_index = next(i for i, item in enumerate(ranked_list) if item['user_id'] == user_id)
        percentile = (user_index / (total_users - 1)) * 100
        top_percentile = 100 - percentile

        # --- NEW: Use ranks from config file ---
        ranks = config['modules']['wrapped']['percentile_ranks']
        # We sort the keys numerically to ensure correct order, ignoring 'default'.
        sorted_thresholds = sorted([int(k) for k in ranks.keys() if k.isdigit()])

        for threshold in sorted_thresholds:
            if threshold == "default": continue
            if top_percentile <= int(threshold):
                return ranks[threshold]
        
        return ranks.get("default", "N/A")
    except StopIteration:
        return "N/A"

@client.event
async def on_voice_state_update(member, before, after):
    """Handles players joining/leaving Werwolf lobby channels."""
    # --- NEW: Handle "Join to Create" logic first, passing config ---
    await voice_manager.handle_voice_state_update(member, before, after, config)

    # Ignore bots
    if member.bot:
        return

    # --- Werwolf Game Logic ---

    # Find the game associated with the voice channel
    game = None
    vc_id = None
    if after.channel:
        vc_id = after.channel.id
    elif before.channel:
        vc_id = before.channel.id

    # --- FIX: Do not run Werwolf cleanup logic if the user is just moving between channels ---
    # The "Join to Create" feature moves users, which can trigger this incorrectly.
    # We only care about true disconnects (leaving all VCs).
    is_true_disconnect = before.channel and not after.channel

    # --- NEW: End game if VC becomes empty ---
    # A user truly disconnected from a channel (not just muted/deafened)
    if is_true_disconnect:
        # Check if the channel that became empty was a game channel
        for game_channel_id, game_instance in list(active_werwolf_games.items()):
            game_vc = game_instance.discussion_vc or game_instance.lobby_vc
            if not game_vc: continue # Skip if the game has no VC
            # Check if the channel matches and is now empty of human players
            human_members = [m for m in game_vc.members if not m.bot] if game_vc else []
            if game_vc and game_vc.id == before.channel.id and not human_members:
                # --- FIX: Check if channel exists before sending message ---
                if game_instance.game_channel and client.get_channel(game_instance.game_channel.id):
                    try:
                        await game_instance.game_channel.send("Alle Spieler haben den Voice-Channel verlassen. Das Spiel wird beendet.")
                    except discord.NotFound:
                        pass # Channel was deleted in the meantime
                await game_instance.end_game(None)
                del active_werwolf_games[game_channel_id]

    for g in active_werwolf_games.values():
        if g.lobby_vc and g.lobby_vc.id == vc_id:
            game = g
            break
    
    if not game:
        return

    # Player joins the lobby
    if game.phase == "joining" and game.join_message:
        player_joined = after.channel == game.lobby_vc and before.channel != game.lobby_vc
        player_left = before.channel == game.lobby_vc and after.channel != game.lobby_vc

        if player_joined:
            game.add_player(member)
        elif player_left:
            game.remove_player(member)

        if player_joined or player_left:
            try:
                # --- NEW: Update the join embed instead of sending new messages ---
                original_embed = game.join_message.embeds[0]
                player_list = game.get_player_list()
                field_value = "\n".join(player_list) if player_list else "Noch keine Spieler."
                
                # Find and update the 'Spieler' field, or add it if it doesn't exist.
                original_embed.set_field_at(1, name=f"Spieler ({len(player_list)})", value=field_value, inline=False)
                
                await game.join_message.edit(embed=original_embed)
            except (discord.NotFound, IndexError, AttributeError):
                pass # Ignore if message is gone or embed is malformed

# --- NEW: WERWOLF SLASH COMMANDS ---

# Create a command group for Werwolf. This allows us to add/remove all ww commands at once.
ww_group = app_commands.Group(name="ww", description="Startet und steuert ein Werwolf-Spiel.")

# --- NEW: Add the ww_group to the main tree so it's always available ---
tree.add_command(ww_group)

# --- NEW: Voice Channel Commands ---
voice_group = app_commands.Group(
    name="voice",
    description="Befehle zur Verwaltung von Sprachkanälen."
)

# --- NEW: Custom check for admin commands ---
def is_admin_or_authorised(interaction: discord.Interaction) -> bool:
    """Checks if the user is an admin or has the 'authorised' role."""
    if interaction.user.guild_permissions.administrator:
        return True
    authorised_role = discord.utils.get(interaction.user.roles, name=config['bot']['authorised_role'])
    return authorised_role is not None

@voice_group.command(name="setup", description="Richtet das 'Beitreten zum Erstellen'-Feature für Sprachkanäle ein.")
@app_commands.default_permissions(administrator=True)
@app_commands.check(is_admin_or_authorised)
async def voice_setup(interaction: discord.Interaction):
    """Sets up the 'Join to Create' voice channel."""
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    # Check if the channel already exists
    existing_channel = discord.utils.get(guild.voice_channels, name=config['modules']['voice_manager']['join_to_create_channel_name'])
    if existing_channel:
        await interaction.followup.send(f"The 'Join to Create' feature is already set up in {existing_channel.mention}!")
        return

    try:
        # Find or create a category for dynamic channels
        category_name = config['modules']['voice_manager']['dynamic_channel_category_name']
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            category = await guild.create_category(category_name, reason="Setup for dynamic voice channels")

        # Create the 'Join to Create' channel
        join_channel = await guild.create_voice_channel(name=config['modules']['voice_manager']['join_to_create_channel_name'], category=category, reason="Bot setup for 'Join to Create' feature")
        await interaction.followup.send(f"Successfully set up the 'Join to Create' feature! Users can now join {join_channel.mention} to create their own voice channels.")
    except discord.Forbidden:
        await interaction.followup.send("Error: The bot lacks the necessary permissions (Manage Channels) to perform this setup.")

@voice_group.command(name="clearall", description="[Admin-Gefahr!] Löscht ALLE Sprachkanäle auf dem Server.")
@app_commands.default_permissions(administrator=True)
@app_commands.check(is_admin_or_authorised)
async def voice_clearall(interaction: discord.Interaction):
    """Deletes ALL voice channels on the server, regardless of DB state."""
    await interaction.response.defer(ephemeral=True)
    
    guild = interaction.guild
    voice_channels_to_delete = guild.voice_channels
    if not voice_channels_to_delete:
        await interaction.followup.send("Keine Sprachkanäle zum Löschen gefunden.")
        return

    deleted_count = 0
    for channel in voice_channels_to_delete:
        try:
            await channel.delete(reason="Admin Massenlöschung")
            deleted_count += 1
        except Exception as e:
            print(f"Konnte Channel {channel.name} nicht löschen: {e}")
    
    await interaction.followup.send(f"{deleted_count} Sprachkanäle wurden erfolgreich gelöscht.")

# --- NEW: Voice Channel Config Commands ---
config_group = app_commands.Group(name="config", parent=voice_group, description="Konfiguriere deinen persönlichen Sprachkanal.")

async def check_channel_owner(interaction: discord.Interaction) -> bool:
    """A check to ensure the user is in their own managed channel."""
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("Du musst in einem Voice Channel sein, um diesen Befehl zu nutzen.", ephemeral=True)
        return False

    vc_id = interaction.user.voice.channel.id
    channel_config = await db_helpers.get_managed_channel_config(vc_id)
    if not channel_config:
        await interaction.response.send_message("Dieser Befehl funktioniert nur in einem dynamisch erstellten Voice Channel.", ephemeral=True)
        return False

    if channel_config['owner_id'] != interaction.user.id:
        await interaction.response.send_message("Nur der Besitzer des Channels kann diesen Befehl verwenden.", ephemeral=True)
        return False

    return channel_config # Return the config to avoid fetching it again

@config_group.command(name="name", description="Benennt deinen Voice Channel um.")
@app_commands.describe(new_name="Der neue Name für deinen Channel.")
async def voice_config_name(interaction: discord.Interaction, new_name: str):
    if not await check_channel_owner(interaction): return
    await interaction.response.defer(ephemeral=True)
    try:
        await interaction.user.voice.channel.edit(name=new_name, reason=f"Owner changed name.")
        await interaction.followup.send(f"Channel-Name wurde zu '{new_name}' geändert.")
    except Exception as e:
        await interaction.followup.send(f"Fehler beim Umbenennen des Channels: {e}")

@config_group.command(name="limit", description="Setzt ein Benutzerlimit für deinen Channel.")
@app_commands.describe(limit="Die maximale Anzahl an Benutzern (0 für unbegrenzt).")
async def voice_config_limit(interaction: discord.Interaction, limit: app_commands.Range[int, 0, 99]):
    if not (await check_channel_owner(interaction)): return
    await interaction.response.defer(ephemeral=True)
    try:
        await interaction.user.voice.channel.edit(user_limit=limit, reason=f"Owner set limit.")
        await interaction.followup.send(f"Benutzerlimit wurde auf {limit if limit > 0 else 'unbegrenzt'} gesetzt.")
    except Exception as e:
        await interaction.followup.send(f"Fehler beim Setzen des Limits: {e}")

@config_group.command(name="lock", description="Macht deinen Channel privat.")
async def voice_config_lock(interaction: discord.Interaction):
    channel_config = await check_channel_owner(interaction)
    if not channel_config: return
    await interaction.response.defer(ephemeral=True)
    vc_id = interaction.user.voice.channel.id
    allowed_users = set(channel_config.get('allowed_users', [channel_config['owner_id']]))
    await db_helpers.update_managed_channel_config(vc_id, is_private=True, allowed_users=allowed_users)
    await interaction.followup.send("Dein Channel ist jetzt privat. Nur eingeladene Benutzer können beitreten. Benutze `/voice config permit`, um jemanden einzuladen.")

@config_group.command(name="unlock", description="Macht deinen Channel wieder öffentlich.")
async def voice_config_unlock(interaction: discord.Interaction):
    channel_config = await check_channel_owner(interaction)
    if not channel_config: return
    await interaction.response.defer(ephemeral=True)
    vc_id = interaction.user.voice.channel.id
    allowed_users = set(channel_config.get('allowed_users', [channel_config['owner_id']]))
    await db_helpers.update_managed_channel_config(vc_id, is_private=False, allowed_users=allowed_users)
    await interaction.followup.send("Dein Channel ist jetzt wieder öffentlich.")

@config_group.command(name="permit", description="Erlaubt einem Benutzer, deinem privaten Channel beizutreten.")
@app_commands.describe(user="Der Benutzer, dem du den Zutritt erlauben möchtest.")
async def voice_config_permit(interaction: discord.Interaction, user: discord.Member):
    channel_config = await check_channel_owner(interaction)
    if not channel_config: return
    await interaction.response.defer(ephemeral=True)
    vc_id = interaction.user.voice.channel.id

    if not channel_config['is_private']:
        await interaction.followup.send("Dieser Befehl funktioniert nur, wenn dein Channel privat ist. Benutze zuerst `/voice config lock`.")
        return

    allowed_users = set(channel_config.get('allowed_users', [channel_config['owner_id']]))
    if user.id in allowed_users:
        await interaction.followup.send(f"{user.display_name} hat bereits Zutritt.")
        return

    allowed_users.add(user.id)
    await db_helpers.update_managed_channel_config(vc_id, is_private=True, allowed_users=allowed_users)
    await interaction.followup.send(f"{user.display_name} kann deinem Channel jetzt beitreten.")

@config_group.command(name="unpermit", description="Entfernt die Zutrittserlaubnis für einen Benutzer.")
@app_commands.describe(user="Der Benutzer, dem du den Zutritt entziehen möchtest.")
async def voice_config_unpermit(interaction: discord.Interaction, user: discord.Member):
    channel_config = await check_channel_owner(interaction)
    if not channel_config: return
    await interaction.response.defer(ephemeral=True)
    vc_id = interaction.user.voice.channel.id
    owner_id = channel_config['owner_id']

    if user.id == owner_id:
        await interaction.followup.send("Du kannst dir nicht selbst den Zutritt entziehen.")
        return

    allowed_users = set(channel_config.get('allowed_users', [owner_id]))
    if user.id not in allowed_users:
        await interaction.followup.send(f"{user.display_name} hatte keinen Zutritt zu deinem Channel.")
        return

    allowed_users.remove(user.id)
    await db_helpers.update_managed_channel_config(vc_id, is_private=channel_config['is_private'], allowed_users=allowed_users)
    await interaction.followup.send(f"{user.display_name} wurde der Zutritt entzogen.")

    # Kick the user if they are currently in the channel
    if user.voice and user.voice.channel.id == vc_id:
        try:
            await user.move_to(None, reason="Permission removed by owner")
        except Exception as e:
            print(f"Could not kick user after unpermit: {e}")

# --- NEW: Custom check for admin commands ---
def is_admin_or_authorised(interaction: discord.Interaction) -> bool:
    """Checks if the user is an admin or has the 'authorised' role."""
    if interaction.user.guild_permissions.administrator:
        return True
    authorised_role = discord.utils.get(interaction.user.roles, name=config['bot']['authorised_role'])
    return authorised_role is not None

# --- REFACTORED: Admin Commands using a class-based approach ---
@app_commands.check(is_admin_or_authorised)
class AdminGroup(app_commands.Group):
    """Admin-Befehle zur Verwaltung des Bots."""

    @app_commands.command(name="view_wrapped", description="Zeigt eine Vorschau des 'Wrapped' für einen Benutzer an.")
    @app_commands.describe(user="Der Benutzer, dessen Wrapped du ansehen möchtest.")
    async def view_wrapped(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(ephemeral=True)
        
        # For the admin preview, we generate the Wrapped for the CURRENT month
        now = datetime.now(timezone.utc)
        stat_period = now.strftime('%Y-%m')
        
        # We need all stats for the period to calculate ranks
        all_stats = await db_helpers.get_wrapped_stats_for_period(stat_period)
        if not all_stats:
            await interaction.followup.send(f"Keine 'Wrapped'-Daten für den Zeitraum `{stat_period}` gefunden.", ephemeral=True)
            return
            
        # Find the target user's stats
        target_user_stats = next((s for s in all_stats if s['user_id'] == user.id), None)
        if not target_user_stats:
            await interaction.followup.send(f"Keine 'Wrapped'-Daten für {user.display_name} im Zeitraum `{stat_period}` gefunden.", ephemeral=True)
            return

        # --- FIX: Pass the correct arguments to the helper function ---
        # The helper function now calculates ranks internally.
        await _generate_and_send_wrapped_for_user(
            user_stats=target_user_stats,
            stat_period_date=now,
            all_stats_for_period=all_stats,
            total_users=len(all_stats)
        )

        await interaction.followup.send(f"Eine 'Wrapped'-Vorschau für den aktuellen Monat wurde an {user.mention} gesendet.", ephemeral=True)

    @app_commands.command(name="reload_config", description="Lädt die config.json und die System-Prompt-Datei neu.")
    async def reload_config(self, interaction: discord.Interaction):
        """Hot-reloads the configuration files."""
        await interaction.response.defer(ephemeral=True)
        print("--- Admin triggered config reload ---")
        global config, GEMINI_API_URL
        try:
            new_config = load_config()
            config = new_config
            # Restart presence task to apply new interval immediately
            update_presence_task.restart()
            await interaction.followup.send("✅ Konfiguration wurde erfolgreich neu geladen.")
        except Exception as e:
            await interaction.followup.send(f"❌ Fehler beim Neuladen der Konfiguration: `{e}`")

    @app_commands.command(name="set_bio", description="Aktualisiert die 'Über mich'-Beschreibung des Bots aus der config.json.")
    async def set_bio(self, interaction: discord.Interaction):
        """Updates the bot's 'About Me' from the config file."""
        await interaction.response.defer(ephemeral=True)
        new_bio = config.get('bot', {}).get('description')
        if not new_bio:
            await interaction.followup.send("❌ In der `config.json` wurde keine `description` gefunden.", ephemeral=True)
            return
        try:
            await client.user.edit(bio=new_bio)
            await interaction.followup.send("✅ Bot-Biografie wurde erfolgreich aktualisiert.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Fehler beim Aktualisieren der Biografie: `{e}`", ephemeral=True)

# --- NEW: Pagination View for Embeds ---
class PaginationView(discord.ui.View):
    def __init__(self, embeds, timeout=120):
        super().__init__(timeout=timeout)
        self.embeds = embeds
        self.current_page = 0

    def update_buttons(self):
        """Enables or disables buttons based on the current page."""
        self.children[0].disabled = self.current_page == 0
        self.children[1].disabled = self.current_page == len(self.embeds) - 1

    # --- FIX: Create the buttons and assign the callbacks ---
    prev_btn = discord.ui.button(label="◀ Zurück", style=discord.ButtonStyle.secondary, disabled=True)
    next_btn = discord.ui.button(label="Weiter ▶", style=discord.ButtonStyle.secondary)

    # Assign the methods to the button callbacks
    async def previous_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
    prev_btn.callback = previous_button_callback

    async def next_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
    next_btn.callback = next_button_callback

    @app_commands.command(name="save_history", description="Speichert den Chatverlauf dieses Kanals manuell in der Datenbank.")
    @app_commands.describe(limit="Die Anzahl der zu speichernden Nachrichten (Standard: 100).")
    async def save_history(self, interaction: discord.Interaction, limit: int = 100):
        """Fetches and saves a channel's message history to the database."""
        await interaction.response.defer(ephemeral=True)

        messages_to_save = []
        try:
            # Fetch messages from the channel history
            async for message in interaction.channel.history(limit=limit):
                # Ignore messages from bots unless it's our own bot
                if message.author.bot and message.author.id != client.user.id:
                    continue

                # --- NEW: Filter out non-conversational messages ---
                # Ignore slash commands
                if message.content.startswith('/'):
                    continue
                # Ignore messages with embeds, as they are usually game/bot notifications
                if message.embeds:
                    continue

                role = "model" if message.author.id == client.user.id else "user"
                content = message.content
                if role == "user":
                    content = f"User '{message.author.display_name}' said: {message.content}"

                messages_to_save.append({'role': role, 'content': content})

            # Reverse the list so they are in chronological order for saving
            messages_to_save.reverse()
            await db_helpers.save_bulk_history(interaction.channel.id, messages_to_save)
            await interaction.followup.send(f"Successfully processed and saved {len(messages_to_save)} messages from this channel's history.")
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {e}")

    @app_commands.command(name="clear_history", description="Löscht den gesamten gespeicherten Chatverlauf für diesen Kanal.")
    async def clear_history(self, interaction: discord.Interaction):
        """Deletes all chat history for the current channel from the database."""
        await interaction.response.defer(ephemeral=True)
        deleted_count, error = await db_helpers.clear_channel_history(interaction.channel.id)
        if error:
            await interaction.followup.send(f"An error occurred: {error}")
        else:
            await interaction.followup.send(f"Successfully deleted {deleted_count} messages from this channel's history.")

@tree.command(name="summary", description="Zeigt Sulfurs Meinung über einen Benutzer an.")
@app_commands.describe(user="Der Benutzer, dessen Zusammenfassung du sehen möchtest (optional).")
async def summary(interaction: discord.Interaction, user: discord.Member = None):
    """Displays the bot's relationship summary for a user."""
    target_user = user or interaction.user
    await interaction.response.defer(ephemeral=True)

    summary_text = await db_helpers.get_relationship_summary(target_user.id)

    if not summary_text:
        await interaction.followup.send(f"Ich hab mir über {target_user.display_name} noch keine richtige Meinung gebildet. Wir sollten mehr quatschen.")
        return

    embed = discord.Embed(
        title=f"Meine Meinung zu {target_user.display_name}",
        description=f"_{summary_text}_",
        color=target_user.color
    )
    await interaction.followup.send(embed=embed)

@tree.command(name="rank", description="Überprüfe deinen oder den Rang eines anderen Benutzers.")
@app_commands.describe(user="Der Benutzer, dessen Rang du sehen möchtest (optional).")
async def rank(interaction: discord.Interaction, user: discord.Member = None):
    """Displays the level and rank of a user."""
    target_user = user or interaction.user
    await interaction.response.defer()

    player_stats, error = await db_helpers.get_player_rank(target_user.id)

    if error:
        await interaction.followup.send(error, ephemeral=True)
        return

    if not player_stats:
        await interaction.followup.send(f"{target_user.display_name} hat noch keine Nachrichten geschrieben und daher keinen Rang.", ephemeral=True)
        return

    level = player_stats['level'] or 1
    xp = player_stats['xp']
    rank = player_stats['rank']
    xp_for_next_level = get_xp_for_level(level)
    
    # Create a progress bar
    progress = int((xp / xp_for_next_level) * 20) # 20 characters for the bar
    progress_bar = '█' * progress + '░' * (20 - progress)

    embed = discord.Embed(color=target_user.color)
    embed.set_author(name=f"Rang von {target_user.display_name}", icon_url=target_user.display_avatar.url)
    embed.add_field(name="Level", value=f"```{level}```", inline=True)
    embed.add_field(name="Server Rang", value=f"```#{rank}```", inline=True)
    embed.add_field(name="Fortschritt", value=f"`{xp} / {xp_for_next_level} XP`\n`{progress_bar}`", inline=False)

    await interaction.followup.send(embed=embed)

@tree.command(name="leaderboard", description="Zeigt das globale Level-Leaderboard an.")
async def leaderboard(interaction: discord.Interaction):
    """Displays the global level leaderboard."""
    await interaction.response.defer()

    leaderboard_data, error = await db_helpers.get_level_leaderboard()

    if error:
        await interaction.followup.send(error, ephemeral=True)
        return

    if not leaderboard_data:
        await interaction.followup.send("Noch niemand hat XP gesammelt. Schreibt ein paar Nachrichten!", ephemeral=True)
        return

    embed = discord.Embed(title="🏆 Globales Leaderboard 🏆", description="Die aktivsten Mitglieder des Servers.", color=discord.Color.purple())
    
    leaderboard_text = ""
    for i, player in enumerate(leaderboard_data):
        leaderboard_text += f"**{i + 1}. {player['display_name']}** - Level {player['level']} ({player['xp']} XP)\n"

    embed.add_field(name="Top 10", value=leaderboard_text, inline=False)
    await interaction.followup.send(embed=embed)

@tree.command(name="stats", description="Zeigt die Werwolf-Statistiken und das Leaderboard an.")
async def stats(interaction: discord.Interaction):
    """Displays the Werwolf leaderboard."""
    await interaction.response.defer()

    leaderboard, error = await db_helpers.get_leaderboard()

    if error:
        await interaction.followup.send(error, ephemeral=True)
        return

    if not leaderboard:
        await interaction.followup.send("Es gibt noch keine Statistiken. Spielt erst mal eine Runde!", ephemeral=True)
        return

    embed = discord.Embed(title="🐺 Werwolf Leaderboard 🐺", description="Die Top-Spieler mit den meisten Siegen.", color=discord.Color.gold())

    leaderboard_text = ""
    for i, player in enumerate(leaderboard):
        rank = i + 1
        win_loss_ratio = player['wins'] / (player['wins'] + player['losses']) if (player['wins'] + player['losses']) > 0 else 0
        leaderboard_text += f"**{rank}. {player['display_name']}**\n"
        leaderboard_text += f"   Wins: `{player['wins']}` | Losses: `{player['losses']}` | W/L Ratio: `{win_loss_ratio:.2f}`\n"

    embed.add_field(name="Rangliste", value=leaderboard_text, inline=False)
    embed.set_footer(text="Wer hier nicht oben steht, ist ein Noob :xdx:")
    await interaction.followup.send(embed=embed)

@ww_group.command(name="start", description="Startet ein neues Werwolf-Spiel.")
@app_commands.describe(
    ziel_spieler="Die Ziel-Spieleranzahl. Bots füllen auf, wenn angegeben."
)
async def ww_start(interaction: discord.Interaction, ziel_spieler: int = None):
    """Handles the start of a Werwolf game."""
    channel_id = interaction.channel.id
    game = active_werwolf_games.get(channel_id)
    author = interaction.user

    if game:
        await interaction.response.send_message("In diesem Channel wurde bereits ein Spiel gestartet. Schau in die Kategorie '🐺 WERWOLF SPIEL 🐺'.", ephemeral=True)
        return
    
    await interaction.response.defer() # Defer while we create channels

    original_channel = interaction.channel # Store the channel where the command was used
    # --- NEW: Create dedicated category and channels ---
    try:
        guild = interaction.guild
        # Create a category for the game
        category = await guild.create_category(config['modules']['werwolf']['game_category_name'])

        # --- NEW: Set permissions to make the channel read-only for players ---
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(send_messages=False, read_messages=True),
            client.user: discord.PermissionOverwrite(send_messages=True) # Ensure the bot can write
        }
        # Create the text and voice channels inside the category
        game_text_channel = await category.create_text_channel("🐺-werwolf-chat", overwrites=overwrites)
        lobby_vc = await category.create_voice_channel(name="🐺 Werwolf Lobby", reason="Neues Werwolf-Spiel")
    except Exception as e:
        await interaction.followup.send(f"Konnte die Spiel-Channels nicht erstellen. Berechtigungen prüfen? Fehler: {e}", ephemeral=True)
        return

    game = WerwolfGame(game_text_channel, author, original_channel)
    game.lobby_vc = lobby_vc
    game.category = category
    game.join_message = None # Initialize join_message attribute

    active_werwolf_games[game_text_channel.id] = game
    # Send the ephemeral message to the command user
    await interaction.followup.send(f"Ein Werwolf-Spiel wurde in der Kategorie **{category.name}** erstellt! Schau in den Channel {game_text_channel.mention}.", ephemeral=True)
    # Send the public join message and store it for later deletion
    embed = discord.Embed(
        title="🐺 Ein neues Werwolf-Spiel wurde gestartet! 🐺",
        description=f"Tretet dem Voice-Channel **`{lobby_vc.name}`** bei, um mitzuspielen!",
        color=discord.Color.blue()
    )
    embed.add_field(name="Automatischer Start", value="Das Spiel startet in **15 Sekunden**.")
    embed.add_field(name="Spieler (0)", value="Noch keine Spieler.", inline=False)
    embed.set_footer(text="Wer nicht beitritt, ist ein Werwolf!")
    join_message = await game_text_channel.send(embed=embed)

    game.join_message = join_message # Store the message in the game object
    # --- NEW: Automatic Start Logic ---
    await asyncio.sleep(config['modules']['werwolf']['join_phase_duration_seconds'])

    if game_text_channel.id not in active_werwolf_games:
        return # Game was cancelled

    # --- NEW: Check if anyone joined ---
    if not game.players:
        await game.game_channel.send("Niemand ist beigetreten. Das Spiel wird abgebrochen.")
        await game.end_game(None) # End game without a winner
        del active_werwolf_games[game_text_channel.id]
        return

    # --- REFACTORED: Use default target players from config if not specified ---
    target_players = ziel_spieler or config['modules']['werwolf'].get('default_target_players')

    if target_players and len(game.players) < target_players:
        bots_to_add = target_players - len(game.players)
        if bots_to_add <= 0:
            return # Should not happen, but as a safeguard

        await game.game_channel.send(f"Das Spiel wird mit Bots auf {target_players} Spieler aufgefüllt. Füge {bots_to_add} Bot-Gegner hinzu...")
        bot_names = await get_random_names(bots_to_add, db_helpers, config, GEMINI_API_KEY, OPENAI_API_KEY)
        await asyncio.sleep(2)
        for name in bot_names:
            bot_name = name
            # Check for name collisions, though unlikely
            while game.get_player_by_name(bot_name):
                bot_name += "+"
            fake_user = FakeUser(name=bot_name)
            game.add_player(fake_user)

    # Automatically start the game
    error_message = await game.start_game(config, GEMINI_API_KEY, OPENAI_API_KEY)
    if error_message:
        await game.game_channel.send(error_message)
        del active_werwolf_games[game_text_channel.id]
        await game.lobby_vc.delete(reason="Fehler beim Spielstart")

@ww_group.command(name="kill", description="Werwolf-Aktion: Wähle ein Opfer für die Nacht.")
@app_commands.describe(spieler="Der Spieler, der getötet werden soll.") 
async def ww_kill(interaction: discord.Interaction, spieler: str):
    """Handles the werewolf kill action."""
    game = active_werwolf_games.get(interaction.channel_id)
    if not game:
        await interaction.response.send_message("In diesem Channel läuft kein Werwolf-Spiel.", ephemeral=True)
        return

    author = interaction.user
    author_player = game.players.get(author.id)
    if not author_player:
        await interaction.response.send_message("Du bist nicht in diesem Spiel.", ephemeral=True)
        return

    target_player = game.get_player_by_name(spieler)
    
    await interaction.response.defer(ephemeral=True)
    if not target_player:
        await interaction.followup.send("Wen? Ich kann diesen Spieler nicht finden oder du hast keinen Namen angegeben.")
        return

    error_message = await game.handle_night_action(author_player, "kill", target_player, config, GEMINI_API_KEY, OPENAI_API_KEY)
    if error_message:
        await interaction.followup.send(error_message)
    else:
        await interaction.followup.send("Deine Aktion wurde registriert.")
    
    if game.phase == "finished":
        del active_werwolf_games[interaction.channel_id]

@ww_group.command(name="see", description="Seher-Aktion: Sieh die Rolle eines Spielers.")
@app_commands.describe(spieler="Der Spieler, dessen Rolle du sehen möchtest.")
async def ww_see(interaction: discord.Interaction, spieler: str):
    """Handles the seer see action."""
    game = active_werwolf_games.get(interaction.channel_id)
    if not game:
        await interaction.response.send_message("In diesem Channel läuft kein Werwolf-Spiel.", ephemeral=True)
        return

    author = interaction.user
    author_player = game.players.get(author.id)
    if not author_player:
        await interaction.response.send_message("Du bist nicht in diesem Spiel.", ephemeral=True)
        return

    target_player = game.get_player_by_name(spieler)
    
    await interaction.response.defer(ephemeral=True)
    if not target_player:
        await interaction.followup.send("Wen? Ich kann diesen Spieler nicht finden oder du hast keinen Namen angegeben.")
        return

    error_message = await game.handle_night_action(author_player, "see", target_player, config, GEMINI_API_KEY, OPENAI_API_KEY)
    if error_message:
        await interaction.followup.send(error_message)
    else:
        # The confirmation is sent via DM in handle_night_action
        await interaction.followup.send("Deine Aktion wurde registriert.")

    if game.phase == "finished":
        del active_werwolf_games[interaction.channel_id]

@ww_group.command(name="heal", description="Hexe-Aktion: Heile das Opfer der Werwölfe.")
async def ww_heal(interaction: discord.Interaction):
    """Handles the witch heal action."""
    game = active_werwolf_games.get(interaction.channel_id)
    if not game:
        await interaction.response.send_message("In diesem Channel läuft kein Werwolf-Spiel.", ephemeral=True)
        return

    author = interaction.user
    author_player = game.players.get(author.id)
    if not author_player:
        await interaction.response.send_message("Du bist nicht in diesem Spiel.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    error_message = await game.handle_night_action(author_player, "heal", None, config, GEMINI_API_KEY, OPENAI_API_KEY)
    if error_message:
        await interaction.followup.send(error_message)
    else:
        await interaction.followup.send("Deine Aktion wurde registriert.")

@ww_group.command(name="poison", description="Hexe-Aktion: Töte einen Spieler mit deinem Gifttrank.")
@app_commands.describe(spieler="Der Spieler, der vergiftet werden soll.")
async def ww_poison(interaction: discord.Interaction, spieler: str):
    """Handles the witch poison action."""
    game = active_werwolf_games.get(interaction.channel_id)
    if not game:
        await interaction.response.send_message("In diesem Channel läuft kein Werwolf-Spiel.", ephemeral=True)
        return

    author = interaction.user
    author_player = game.players.get(author.id)
    if not author_player:
        await interaction.response.send_message("Du bist nicht in diesem Spiel.", ephemeral=True)
        return

    target_player = game.get_player_by_name(spieler)
    await interaction.response.defer(ephemeral=True)
    error_message = await game.handle_night_action(author_player, "poison", target_player, config, GEMINI_API_KEY, OPENAI_API_KEY)
    if error_message:
        await interaction.followup.send(error_message)
    else:
        await interaction.followup.send("Deine Aktion wurde registriert.")

@ww_group.command(name="mute", description="Dönerstopfer-Aktion: Schalte einen Spieler für den nächsten Tag stumm.")
@app_commands.describe(spieler="Der Spieler, der stummgeschaltet werden soll.")
async def ww_mute(interaction: discord.Interaction, spieler: str):
    """Handles the Dönerstopfer mute action."""
    game = active_werwolf_games.get(interaction.channel_id)
    if not game:
        await interaction.response.send_message("In diesem Channel läuft kein Werwolf-Spiel.", ephemeral=True)
        return

    author = interaction.user
    author_player = game.players.get(author.id)
    target_player = game.get_player_by_name(spieler)
    await interaction.response.defer(ephemeral=True)
    error_message = await game.handle_night_action(author_player, "mute", target_player, config, GEMINI_API_KEY, OPENAI_API_KEY)
    if error_message:
        await interaction.followup.send(error_message)
    else:
        await interaction.followup.send("Deine Aktion wurde registriert.")

# --- NEW: Add the voice command group to the tree ---
tree.add_command(voice_group)

# --- NEW: Add the admin command group to the tree ---
tree.add_command(AdminGroup(name="admin"))

@client.event
async def on_message(message):
    """Fires on every message in any channel the bot can see."""
    
    # 1. Don't reply to yourself, bot!
    if message.author == client.user:
        return

    # --- NEW: Ignore messages in Werwolf channels to not trigger chatbot ---
    if message.channel.id in active_werwolf_games:
        game = active_werwolf_games.get(message.channel.id)
        # Ignore messages in the main game channel if game is running
        if game and game.phase != "joining":
             # Also ignore messages in the private wolf thread
            if game.werwolf_thread and message.channel.id == game.werwolf_thread.id:
                return

    # --- NEW: Leveling System ---
    # Grant XP for regular messages, but not for commands or in DMs
    if not message.content.startswith('/') and isinstance(message.channel, discord.TextChannel):
        stat_period = datetime.now(timezone.utc).strftime('%Y-%m')

        # --- NEW: Log stats for Wrapped ---
        # Find custom emojis in the message
        custom_emojis = re.findall(r'<a?:(\w+):\d+>', message.content)
        await db_helpers.log_message_stat(message.author.id, message.channel.id, custom_emojis, stat_period)

        # Grant XP
        new_level = await grant_xp(message.author.id, message.author.display_name, db_helpers.add_xp, config)
        if new_level:
            # --- NEW: Grant economy bonus on level up ---
            bonus = calculate_level_up_bonus(new_level, config)
            await db_helpers.add_balance(message.author.id, message.author.display_name, bonus, stat_period)
            try:
                # --- FIX: Send level-up message as a DM ---
                await message.author.send(f"GG! Du bist durch das Schreiben von Nachrichten jetzt Level **{new_level}**! :YESS:\n"
                                          f"Du erhältst **{bonus}** Währung als Belohnung!")
            except discord.Forbidden:
                print(f"Could not send level up DM to {message.author.name} (DMs likely closed).")

    # --- Chatbot Logic ---
                return

    # 2. Check for trigger.
    # In DMs, the bot should always respond.
    # In a server, the bot must be @mentioned or its name ("sulf", "sulfur") must be used.
    is_dm = message.guild is None
    if not is_dm:
        is_pinged = client.user in message.mentions
        message_lower = message.content.lower()
        # Check for "sulf" or "sulfur" as whole words to avoid triggering on "sulfuric" etc.
        # --- NEW: Use bot names from config ---
        is_name_used = any(name in message_lower.split() for name in config['bot']['names'])

        # If not in a DM and not pinged/named, we don't care
        if not is_pinged and not is_name_used:
            return
        print(f"Chatbot triggered by {message.author.name} in channel #{message.channel.name}.")
        
        # --- NEW: Log interaction with Sulf for Wrapped ---
        stat_period = datetime.now(timezone.utc).strftime('%Y-%m')
        await db_helpers.log_stat_increment(message.author.id, stat_period, 'sulf_interactions')

    # 3. Clean the user's prompt (remove the @mention)
    # This makes the prompt cleaner for the AI
    user_prompt = message.content.replace(f"<@{client.user.id}>", "").strip()

    if not user_prompt:
        await message.channel.send(config['bot']['chat']['empty_ping_response'])
        return
    
    # 4. Get chat history from the database
    history = await db_helpers.get_chat_history(message.channel.id, config['bot']['chat']['max_history_messages'])

    # 5. Let the user know the bot is "thinking"
    async with message.channel.typing():
        # 6. Get the response from Gemini
        # --- NEW: Add relationship context to the system prompt ---
        relationship_summary = await db_helpers.get_relationship_summary(message.author.id)
        dynamic_system_prompt = config['bot']['system_prompt']
        if relationship_summary:
            dynamic_system_prompt += f"\n\nZusätzlicher Kontext über deine Beziehung zu '{message.author.display_name}': {relationship_summary}"

        # The get_chat_response function modifies the history list in-place
        response_text, error_message = await get_chat_response(history, user_prompt, message.author.display_name, dynamic_system_prompt, config, GEMINI_API_KEY, OPENAI_API_KEY)

        # 7. Send the response
        if error_message:
            await message.channel.send(f"{message.author.mention} {error_message}")
        else:
            # --- NEW: Save messages to DB ---
            # The user prompt was already added to the history list by get_gemini_response
            user_message_content = history[-2]['parts'][0]['text']
            await db_helpers.save_message_to_history(message.channel.id, "user", user_message_content)
            await db_helpers.save_message_to_history(message.channel.id, "model", response_text)

            # --- NEW: Periodically update relationship summary ---
            # The interval is based on exchanges (1 user msg + 1 bot msg = 2 history items)
            update_interval = config['bot']['chat']['relationship_update_interval'] * 2
            if len(history) > 0 and len(history) % update_interval == 0:
                new_summary, _ = await get_relationship_summary_from_api(history, message.author.display_name, relationship_summary, config, GEMINI_API_KEY, OPENAI_API_KEY)
                if new_summary:
                    print(f"Updating relationship summary for {message.author.name}.")
                    await db_helpers.update_relationship_summary(message.author.id, new_summary)

            final_response = await replace_emoji_tags(response_text, client)
            # Split if the message is too long (over 2000 chars)
            chunks = await split_message(final_response)
            for chunk in chunks:
                if chunk: # Don't send empty messages
                    await message.channel.send(chunk)

# --- RUN THE BOT ---
if __name__ == "__main__":
    client.run(DISCORD_BOT_TOKEN)