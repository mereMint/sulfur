import asyncio
import discord
from datetime import datetime, timezone
from collections import deque
from discord.ui import View, Button
from modules.api_helpers import get_werwolf_tts_message, get_random_names
import re
from modules.fake_user import FakeUser
import random
from modules.db_helpers import update_player_stats
from modules import stock_market


# --- Roles ---
DORFBEWOHNER = "Dorfbewohner"
WERWOLF = "Werwolf"
SEHERIN = "Seherin"
HEXE = "Hexe"
DÖNERSTOPFER = "Dönerstopfer"
JÄGER = "Jäger"
AMOR = "Amor"  # Cupid - creates lovers
DER_WEISSE = "Der Weiße"  # The White - can survive one werewolf attack

# Mapping of feature unlock names to role names for ownership checking
ROLE_UNLOCK_MAPPING = [
    ('werwolf_role_seherin', SEHERIN),
    ('werwolf_role_hexe', HEXE),
    ('werwolf_role_dönerstopfer', DÖNERSTOPFER),
    ('werwolf_role_jäger', JÄGER),
    ('werwolf_role_amor', AMOR),
    ('werwolf_role_der_weisse', DER_WEISSE)
]

# Helper function to get available roles for a user
async def get_available_werwolf_roles(user_id, db_helpers):
    """Get roles available based on what the user owns.
    
    Args:
        user_id: Discord user ID
        db_helpers: Database helpers module
        
    Returns:
        List of role names (strings) that the user has unlocked
    """
    available_roles = []
    
    # Check each special role
    for feature_name, role_name in ROLE_UNLOCK_MAPPING:
        has_role = await db_helpers.has_feature_unlock(user_id, feature_name)
        if has_role:
            available_roles.append(role_name)
    
    return available_roles


class RoleToggleButton(discord.ui.Button):
    """Toggle button for individual roles in the role selection UI."""
    
    def __init__(self, role_name):
        """Initialize a role toggle button.
        
        Args:
            role_name: The name of the role (e.g., 'Seherin', 'Hexe')
        """
        self.role_name = role_name
        self.is_selected = True  # All roles start as selected
        
        # Map role names to emojis for better UX
        role_emojis = {
            SEHERIN: "🔮",
            HEXE: "🧪",
            DÖNERSTOPFER: "🌯",
            JÄGER: "🏹",
            AMOR: "💘",
            DER_WEISSE: "⚪"
        }
        
        emoji = role_emojis.get(role_name, "⭐")
        
        super().__init__(
            label=f"{emoji} {role_name}",
            style=discord.ButtonStyle.primary,
            custom_id=f"role_{role_name}"
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Handle button click to toggle role selection."""
        # Only the game starter can toggle roles
        if interaction.user.id != self.view.starter_id:
            await interaction.response.send_message(
                "Nur der Spielersteller kann Rollen auswählen!",
                ephemeral=True
            )
            return
        
        # Toggle the selection state
        self.is_selected = not self.is_selected
        
        # Update button style to reflect state
        self.style = discord.ButtonStyle.primary if self.is_selected else discord.ButtonStyle.secondary
        
        # Update the view's selected roles set
        if self.is_selected:
            self.view.selected_roles.add(self.role_name)
        else:
            self.view.selected_roles.discard(self.role_name)
        
        # Update the embed to show current selection
        await self.view.update_selection_message(interaction)


class WerwolfRoleSelectionView(discord.ui.View):
    """Allow game creator to select which roles to include in the game."""
    
    def __init__(self, starter_id, available_roles, game_instance):
        """Initialize the role selection view.
        
        Args:
            starter_id: Discord user ID of the game starter
            available_roles: List of role names the user has unlocked
            game_instance: The WerwolfGame instance
        """
        super().__init__(timeout=120)  # 2 minutes to select roles
        self.starter_id = starter_id
        self.selected_roles = set(available_roles)  # All selected by default
        self.game_instance = game_instance
        self.message = None  # Will store the message for updating
        
        # Create toggle buttons for each available role
        for role in available_roles:
            self.add_item(RoleToggleButton(role))
    
    @discord.ui.button(label="✅ Spiel starten", style=discord.ButtonStyle.success, row=4)
    async def start_game_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Start the game with the selected roles."""
        # Only the game starter can start the game
        if interaction.user.id != self.starter_id:
            await interaction.response.send_message(
                "Nur der Spielersteller kann das Spiel starten!",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        # Disable all buttons to prevent multiple starts
        for item in self.children:
            item.disabled = True
        
        # Update message to show selection is locked
        if self.message:
            embed = self.message.embeds[0]
            embed.color = discord.Color.green()
            embed.set_footer(text="Rollenauswahl abgeschlossen! Das Spiel startet...")
            await self.message.edit(embed=embed, view=self)
        
        # Proceed with game start
        self.stop()
    
    @discord.ui.button(label="❌ Abbrechen", style=discord.ButtonStyle.danger, row=4)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel the game setup."""
        # Only the game starter can cancel
        if interaction.user.id != self.starter_id:
            await interaction.response.send_message(
                "Nur der Spielersteller kann das Spiel abbrechen!",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        # Mark as cancelled
        self.selected_roles = None
        self.stop()
    
    async def update_selection_message(self, interaction: discord.Interaction):
        """Update the embed to show current role selection."""
        selected_count = len(self.selected_roles)
        
        # Build list of selected and unselected roles
        selected_list = []
        unselected_list = []
        
        for item in self.children:
            if isinstance(item, RoleToggleButton):
                if item.is_selected:
                    selected_list.append(f"✅ {item.role_name}")
                else:
                    unselected_list.append(f"❌ {item.role_name}")
        
        embed = discord.Embed(
            title="🐺 Werwolf Rollen-Auswahl",
            description="Wähle, welche Rollen in diesem Spiel verfügbar sein sollen.\n"
                       "Grüne Buttons = Ausgewählt | Graue Buttons = Nicht ausgewählt",
            color=discord.Color.blue()
        )
        
        if selected_list:
            embed.add_field(
                name=f"Ausgewählte Rollen ({selected_count})",
                value="\n".join(selected_list),
                inline=False
            )
        
        if unselected_list:
            embed.add_field(
                name="Nicht ausgewählte Rollen",
                value="\n".join(unselected_list),
                inline=False
            )
        
        embed.set_footer(text="Werwölfe und Dorfbewohner sind immer dabei!")
        
        # Update the view
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def on_timeout(self):
        """Handle timeout - start game with current selection."""
        if self.message and self.selected_roles is not None:
            embed = self.message.embeds[0]
            embed.color = discord.Color.orange()
            embed.set_footer(text="Zeit abgelaufen! Das Spiel startet mit der aktuellen Auswahl...")
            
            for item in self.children:
                item.disabled = True
            
            try:
                await self.message.edit(embed=embed, view=self)
            except (discord.NotFound, discord.HTTPException):
                # Message was deleted or Discord API error - ignore
                pass


class WerwolfPlayer:
    """Represents a player in the game."""
    def __init__(self, user):
        self.user = user
        self.role = None
        self.has_healing_potion = False
        self.has_kill_potion = False
        self.is_alive = True
        self.voted_for = None # For day voting
        self.lover_id = None  # NEW: For Amor role - ID of lover
        self.weisse_immunity_used = False  # NEW: For Der Weiße role - whether immunity was used

class WerwolfGame:
    """Manages the state and logic of a single Werwolf game."""

    def __init__(self, game_channel, starter, original_channel, bot_client=None):
        self.api_url = None # Will be set from bot.py
        self.game_channel = game_channel # This is now the dedicated text channel
        self.starter = starter
        self.original_channel = original_channel # Channel where game was started
        self.bot_client = bot_client # Reference to the bot client for wait_for
        self.players = {} # Maps user.id to WerwolfPlayer object
        self.phase = "joining" # joining -> night -> day
        self.day_number = 0
        self.night_votes = {} # {voter_id: target_id}
        self.lobby_vc = None # This will become the main discussion VC
        self.category = None # The category holding the game channels
        self.discussion_vc = None
        self.werwolf_thread = None
        self.voting_view = None # Will hold the voting message/view
        self.seer_choice = None
        self.hexe_heal_target_id = None
        self.hexe_poison_target_id = None
        self.döner_mute_target_id = None
        self.seer_findings = {} # NEW: To store what the seer has seen
        self.join_message = None # The initial "join game" message
        self.game_state_message = None # The main message to be updated
        self.night_end_task = None # To manage the night timeout
        self.event_log = deque(maxlen=10) # Log of recent game events for the embed
        
        # NEW: Amor and Der Weiße state
        self.amor_has_chosen = False  # Whether Amor has selected lovers
        self.lovers = []  # List of two player IDs who are in love
        self.villagers_lost_powers = False  # Whether Der Weiße was burned at stake

        self.config = None # Will be set when the game starts
        self.gemini_api_key = None
        self.openai_api_key = None
        self.db_helpers = None # Will be set when the game starts

    async def _get_provider(self):
        """Determines the current API provider based on usage."""
        if self.config['api']['provider'] != 'gemini':
            return self.config['api']['provider']
        
        usage = await self.db_helpers.get_gemini_usage()
        return 'openai' if usage >= 250 else 'gemini'

    async def _increment_usage_if_gemini(self, provider):
        """Increments the Gemini usage counter if it was used."""
        if provider == 'gemini':
            await self.db_helpers.increment_gemini_usage()

    def _calculate_tts_duration(self, text: str) -> float:
        """Estimates the speaking duration of a text in seconds."""
        if not text:
            return 2.0 # Default duration
        
        # Use configurable values for TTS timing
        tts_config = self.config['modules']['werwolf']['tts']
        chars_per_second = tts_config.get('chars_per_second', 12)
        min_duration = tts_config.get('min_duration', 4.0)
        buffer_seconds = tts_config.get('buffer_seconds', 3.0)

        char_count = len(text)
        
        duration_seconds = char_count / chars_per_second
        
        return max(min_duration, duration_seconds) + buffer_seconds

    async def log_event(self, event_text: str, send_tts: bool = False):
        """Adds an event to the log and optionally sends a TTS message."""
        self.event_log.append(event_text)
        
        tts_task = None
        if send_tts:
            # Send and delete TTS to keep chat clean
            provider_to_use = await self._get_provider()
            temp_config = self.config.copy()
            temp_config['api']['provider'] = provider_to_use

            tts_content_from_api = await get_werwolf_tts_message(event_text, temp_config, self.gemini_api_key, self.openai_api_key)
            await self._increment_usage_if_gemini(provider_to_use)
            clean_tts_content = re.sub(r'[\*_`~]', '', tts_content_from_api)
            
            try:
                msg = await self.game_channel.send(clean_tts_content, tts=True)
                # Create a task to delete the message after the TTS duration
                delete_delay = self._calculate_tts_duration(clean_tts_content)
                tts_task = asyncio.create_task(asyncio.sleep(delete_delay)) # This task will be awaited
                asyncio.create_task(msg.delete(delay=delete_delay)) # This runs in the background
            except (discord.NotFound, discord.Forbidden):
                pass  # Ignore if we can't send the message
        
        # If a TTS message was sent, wait for its duration before the game continues.
        if tts_task:
            await tts_task

    async def send_temp_message(self, content: str, delay: int = 10):
        """Sends a message to the game channel and deletes it after a delay."""
        try:
            msg = await self.game_channel.send(content)
            await asyncio.sleep(delay)
            await msg.delete()
        except (discord.NotFound, discord.Forbidden):
            pass # Ignore if message is already gone or permissions fail

    async def update_game_state_embed(self, status_text: str = None, view: discord.ui.View = None):
        """Creates or updates the main game state embed."""
        if self.phase in ["joining", "finished", "stopping"]:
            return

        title = "🐺 Werwolf"
        color = discord.Color(int(self.config.get('bot', {}).get('embed_color', '#7289DA').lstrip('#'), 16))

        if self.phase == "night":
            title = f"🌙 Werwolf - Nacht {self.day_number}"
            color = discord.Color.dark_blue()
        elif self.phase == "day":
            title = f"☀️ Werwolf - Tag {self.day_number}"
            color = discord.Color.gold()
        elif self.phase == "finished":
            title = f"🏁 Werwolf - Spiel beendet"
            color = discord.Color.green()
        
        description = status_text or (self.event_log[-1] if self.event_log else "Das Spiel beginnt...")

        embed = discord.Embed(title=title, description=description, color=color)
        
        alive_players = self.get_alive_players()
        if alive_players:
            # Format player list with emojis
            player_list = []
            for p in alive_players:
                player_emoji = "🤖" if self.is_bot_player(p) else "👤"
                player_list.append(f"{player_emoji} {p.user.display_name}")
            embed.add_field(
                name=f"💚 Lebende Spieler ({len(alive_players)})", 
                value="\n".join(player_list), 
                inline=False
            )
        
        # Add the event log to the embed with better formatting
        if self.event_log:
            log_text = "\n".join(f"• {msg}" for msg in reversed(self.event_log))
            # Truncate if too long (Discord limit is 1024 characters per field)
            if len(log_text) > 1000:
                log_text = log_text[:997] + "..."
            embed.add_field(name="📜 Letzte Ereignisse", value=log_text, inline=False)
        
        # During the day, add vote counts
        if self.phase == "day" and self.voting_view:
            leaderboard = self.voting_view.get_leaderboard_text()
            embed.add_field(name="🗳️ Aktuelle Stimmen", value=leaderboard, inline=False)

        # Add footer with helpful info
        if self.phase == "night":
            embed.set_footer(text="🌙 Die Nacht ist hereingebrochen. Spezielle Rollen agieren jetzt...")
        elif self.phase == "day":
            embed.set_footer(text="☀️ Der Tag ist angebrochen. Diskutiert und stimmt ab!")

        # If a view is not explicitly passed, use the one from the game object or an empty one
        if view is None and self.phase != "finished":
            view = self.voting_view or View.from_message(self.game_state_message) if self.game_state_message else discord.ui.View()

        if self.game_state_message:
            try:
                await self.game_state_message.edit(embed=embed, view=view)
            except discord.NotFound:
                self.game_state_message = await self.game_channel.send(embed=embed, view=view)
        else:
            self.game_state_message = await self.game_channel.send(embed=embed, view=view)


    def add_player(self, user):
        """Adds a player to the game during the joining phase."""
        if self.phase != "joining":
            return "Sorry, das Spiel hat schon angefangen."
        if user.id in self.players:
            return "Du bist schon im Spiel, du Horst."
        
        self.players[user.id] = WerwolfPlayer(user)
        return f"{user.display_name} ist dem Spiel beigetreten! Aktuelle Spieler: {len(self.players)}"

    def remove_player(self, user):
        """Removes a player from the game during the joining phase."""
        if self.phase != "joining":
            return None # Can't remove players after game starts
        if user.id in self.players:
            del self.players[user.id]
            return f"{user.display_name} hat die Lobby verlassen."
        return None

    def get_player_list(self):
        """Returns a list of display names of current players."""
        return [p.user.display_name for p in self.players.values()]

    def get_alive_players(self):
        """Returns a list of alive WerwolfPlayer objects."""
        return [p for p in self.players.values() if p.is_alive]

    def get_player_by_name(self, name_or_id):
        """Finds an alive player by their display name (case-insensitive) or ID."""
        name_lower = str(name_or_id).lower()
        for player in self.get_alive_players():
            if str(player.user.id) == name_lower or player.user.display_name.lower() == name_lower:
                return player
        return None
    async def start_game(self, config, gemini_key, openai_key, db_helpers, ziel_spieler=None, selected_roles=None):
        """Assigns roles and starts the first night.
        
        Args:
            config: Bot configuration
            gemini_key: Gemini API key
            openai_key: OpenAI API key
            db_helpers: Database helpers module
            ziel_spieler: Target number of players (bots will fill if needed)
            selected_roles: Set/list of role names to include (special roles only)
        """
        if self.phase != "joining":
            return "Das Spiel läuft bereits."
        
        self.config = config # Store config for later use
        self.gemini_api_key = gemini_key
        self.openai_api_key = openai_key
        self.db_helpers = db_helpers

        player_count = len(self.players)
        if player_count < 1:
            return "Es sind keine Spieler im Spiel."

        print("  [WW] Starting game setup...")
        # --- NEW: Handle bot filling inside the game logic ---
        target_players = ziel_spieler or self.config['modules']['werwolf'].get('default_target_players')
        if target_players and len(self.players) < target_players:
            bots_to_add = target_players - len(self.players)
            if bots_to_add > 0:
                await self.send_temp_message(f"Das Spiel wird mit Bots auf {target_players} Spieler aufgefüllt. Füge {bots_to_add} Bot-Gegner hinzu...", delay=10)
                provider_to_use = await self._get_provider()
                temp_config = self.config.copy()
                temp_config['api']['provider'] = provider_to_use

                bot_names = await get_random_names(bots_to_add, db_helpers, temp_config, self.gemini_api_key, self.openai_api_key)
                await self._increment_usage_if_gemini(provider_to_use)
                await asyncio.sleep(2)
                for name in bot_names:
                    bot_name = name
                    # Check for name collisions, though unlikely
                    if any(p.user.display_name == bot_name for p in self.players.values()):
                        bot_name += "+"
                    fake_user = FakeUser(name=bot_name)
                    self.add_player(fake_user)
        
        player_count = len(self.players) # Recalculate after adding bots

        # --- Role Assignment ---
        # If selected_roles is None, use all roles (backward compatibility)
        # If selected_roles is provided, only use those special roles
        if selected_roles is None:
            # Default behavior - include all roles based on player count
            selected_roles = {SEHERIN, HEXE, DÖNERSTOPFER, JÄGER, AMOR, DER_WEISSE}
        
        # Calculate how many of each role based on player count
        # These calculations determine the maximum for each role
        if player_count == 1:
            num_werwolfe = 1
            num_seherin, num_hexe, num_döner, num_jäger, num_amor, num_weisse = 0, 0, 0, 0, 0, 0
        elif player_count == 2:
            num_werwolfe = 1
            num_seherin = 1 if SEHERIN in selected_roles else 0
            num_hexe, num_döner, num_jäger, num_amor, num_weisse = 0, 0, 0, 0, 0
        else:
            num_werwolfe = max(1, player_count // 3)
            # Only assign role if it's in selected_roles
            num_seherin = 1 if (player_count > 2 and SEHERIN in selected_roles) else 0
            num_hexe = 1 if (player_count >= 7 and HEXE in selected_roles) else 0
            num_döner = 1 if (player_count >= 9 and DÖNERSTOPFER in selected_roles) else 0
            num_jäger = 1 if (player_count >= 5 and JÄGER in selected_roles) else 0
            num_amor = 1 if (player_count >= 8 and AMOR in selected_roles) else 0
            num_weisse = 1 if (player_count >= 10 and DER_WEISSE in selected_roles) else 0
        
        num_dorfbewohner = player_count - num_werwolfe - num_seherin - num_hexe - num_döner - num_jäger - num_amor - num_weisse

        roles = ([WERWOLF] * num_werwolfe + [SEHERIN] * num_seherin + [HEXE] * num_hexe + 
                 [DÖNERSTOPFER] * num_döner + [JÄGER] * num_jäger + [AMOR] * num_amor + 
                 [DER_WEISSE] * num_weisse + [DORFBEWOHNER] * num_dorfbewohner)
        random.shuffle(roles)

        player_objects = list(self.players.values())
        for i, player in enumerate(player_objects):
            player.role = roles[i]

        print(f"  [WW] Roles assigned: { {p.user.display_name: p.role for p in player_objects} }")
        # --- DM Roles to Players ---
        werwolfe_team = []
        for player in player_objects:
            if player.role == WERWOLF:
                # This is a WerwolfPlayer object
                werwolfe_team.append(player)

        print("  [WW] Sending role DMs to players...")
        for player in player_objects:
            try:
                role_message = f"Du bist {player.role}."
                if player.role == WERWOLF:
                    # Tell werewolves who their teammates are
                    other_werwolfe = [p.user.display_name for p in werwolfe_team if p.user.id != player.user.id]
                    if other_werwolfe:
                        role_message += f"\nDeine Werwolf-Kollegen sind: {', '.join(other_werwolfe)}."
                    else:
                        role_message += "\nDu bist der einzige Werwolf."
                elif player.role == HEXE:
                    player.has_healing_potion = True
                    player.has_kill_potion = True
                    role_message += "\nDu hast einen Heiltrank und einen Gifttrank."
                elif player.role == JÄGER:
                    role_message += "\nStirbt der Jäger, darfst du noch eine Person mit in den Tod nehmen."
                elif player.role == AMOR:
                    role_message += "\nDu darfst in der ersten Nacht zwei Spieler auswählen, die sich ineinander verlieben. Stirbt einer, stirbt auch der andere."
                    role_message += "\nSende `love <name1> <name2>` per DM, um zwei Verliebte zu wählen."
                elif player.role == DER_WEISSE:
                    role_message += "\nDu kannst einen Werwolf-Angriff überleben. Aber Vorsicht: Wirst du am Tag gelyncht, verlieren alle Dorfbewohner ihre Fähigkeiten!"
                
                await player.user.send(role_message)
            except discord.Forbidden:
                await self.game_channel.send(f"Konnte {player.user.mention} keine DM schicken. Stell sicher, dass du DMs vom Server erlaubst!")

        # --- Create private thread for werewolves ---
        if werwolfe_team:
            print("  [WW] Creating private thread for werewolves...")
            try:
                self.werwolf_thread = await self.game_channel.create_thread(name=self.config['modules']['werwolf']['wolf_thread_name'], type=discord.ChannelType.private_thread)
                # --- FIX: Only add real users to the thread ---
                for wolf_player in [p for p in werwolfe_team if not self.is_bot_player(p)]:
                    await self.werwolf_thread.add_user(wolf_player.user)
                await self.werwolf_thread.send("Willkommen, Werwölfe! Beratet euch hier und schickt mir eure Entscheidung als DM mit `kill <name>`.")
            except discord.HTTPException as e:
                await self.game_channel.send(f"Fehler beim Erstellen des Werwolf-Threads: {e}. Das Spiel wird fortgesetzt, aber die Werwölfe müssen den Bot per DM für Aktionen nutzen.")

        # --- NEW: Delete the initial join message ---
        if self.join_message:
            try:
                await self.join_message.delete()
            except (discord.NotFound, discord.Forbidden):
                pass # Message might already be gone

        print("  [WW] Starting first night...")
        await self.log_event("Rollen wurden per DM verteilt. Das Spiel beginnt!")
        # --- FIX: Set discussion_vc immediately so deafening works on Night 1 ---
        if self.lobby_vc:
            self.discussion_vc = self.lobby_vc
        await self.start_night()
        return None # No error message

    def is_bot_player(self, player):
        """Checks if a player is a bot-controlled player."""
        return isinstance(player.user, FakeUser)


    async def start_night(self):
        """Starts the night phase."""
        self.day_number += 1
        self.phase = "night"
        self.night_votes = {}
        self.seer_choice = None
        self.hexe_heal_target_id = None
        self.hexe_poison_target_id = None
        self.döner_mute_target_id = None
        self.seer_findings = {} # Reset seer findings each night
        # Cancel any previous night end task
        if self.night_end_task:
            self.night_end_task.cancel()

        # Deafen all players in the discussion voice channel
        if self.discussion_vc:
            # This message is now sent via TTS and doesn't need to be in the embed
            print(f"  [WW] Muting/deafening {len(self.discussion_vc.members)} members in VC...")
            # await self.update_game_state_embed("Alle im Voice-Channel werden für die Nacht stummgeschaltet.")
            for member in self.discussion_vc.members: # Iterate through all members in the channel
                player = self.players.get(member.id)
                if player and player.is_alive:
                    # Mute and deafen living players
                    await member.edit(mute=True, deafen=True, reason="Nachtphase beginnt")
                elif player and not player.is_alive:
                    # Unmute and undeafen dead players (ghosts)
                    await member.edit(mute=False, deafen=False, reason="Geister können nachts reden")

        await self.log_event(f"Nacht {self.day_number} beginnt. Alle schlafen ein.", send_tts=True)

        # --- MODIFIED: Ensure player list is shown at night start ---
        await self.update_game_state_embed(status_text="Die Nacht bricht herein. Besondere Rollen, schickt mir jetzt eure Aktionen als DM (private Nachricht).\n- **Werwolf**: `kill <name>`\n- **Seherin**: `see <name>`\n- **Hexe**: `heal` oder `poison <name>`\n- **Dönerstopfer**: `mute <name>`")

        # --- Bot Night Actions ---
        print("  [WW] Processing bot night actions...")
        await asyncio.sleep(1) # Small delay for realism

        # --- NEW: Bot actions are now processed in a logical order ---
        # 1. Seer acts first to gather information.
        # 2. Wolves act next.
        # 3. Witch acts last, using information from the night's events.
        bot_players = [p for p in self.get_alive_players() if self.is_bot_player(p)]
        human_wolf_exists = any(p for p in self.get_alive_players() if p.role == WERWOLF and not self.is_bot_player(p))

        # --- FIX: Process each bot role independently to prevent logic errors ---
        # Bot Seer
        bot_seer = next((p for p in bot_players if p.role == SEHERIN), None)
        if bot_seer:
            print(f"    - Bot '{bot_seer.user.display_name}' (Seherin) is choosing a target...")
            targets = [p for p in self.get_alive_players() if p.user.id != bot_seer.user.id]
            if targets:
                target = random.choice(targets)
                self.seer_findings[target.user.id] = target.role
                await self.handle_night_action(bot_seer, "see", target, self.config, self.gemini_api_key, self.openai_api_key)

        # Bot Wolf (only acts if no human wolves are alive)
        bot_wolf = next((p for p in bot_players if p.role == WERWOLF), None)
        if bot_wolf and not human_wolf_exists:
            print(f"    - Bot '{bot_wolf.user.display_name}' (Werwolf) is choosing a target...")
            targets = [p for p in self.get_alive_players() if p.role != WERWOLF]
            if targets:
                target = random.choice(targets)
                await self.handle_night_action(bot_wolf, "kill", target, self.config, self.gemini_api_key, self.openai_api_key)
        
        # --- NEW: Process Dönerstopfer action after Seer/Wolf ---
        bot_doner = next((p for p in bot_players if p.role == DÖNERSTOPFER), None)
        if bot_doner:
            print(f"    - Bot '{bot_doner.user.display_name}' (Dönerstopfer) is choosing a target...")
            targets = [p for p in self.get_alive_players() if p.user.id != bot_doner.user.id]
            if targets:
                target = random.choice(targets)
                await self.handle_night_action(bot_doner, "mute", target, self.config, self.gemini_api_key, self.openai_api_key)

        # --- NEW: Process Hexe action last ---
        bot_hexe = next((p for p in bot_players if p.role == HEXE), None)
        if bot_hexe:
            wolf_victim_id = next(iter(self.night_votes.values()), None)
            if wolf_victim_id and bot_hexe.has_healing_potion:
                wolf_victim = self.players.get(wolf_victim_id)
                if wolf_victim and self.seer_findings.get(wolf_victim.user.id) != WERWOLF:
                    await self.handle_night_action(bot_hexe, "heal", None, self.config, self.gemini_api_key, self.openai_api_key)
            elif bot_hexe.has_kill_potion:
                known_wolves = [p_id for p_id, role in self.seer_findings.items() if role == WERWOLF]
                if known_wolves:
                    target_to_poison = self.players.get(random.choice(known_wolves))
                    if target_to_poison and target_to_poison.is_alive:
                        await self.handle_night_action(bot_hexe, "poison", target_to_poison, self.config, self.gemini_api_key, self.openai_api_key)

        # --- NEW: Bot Amor action (only on first night) ---
        bot_amor = next((p for p in bot_players if p.role == AMOR), None)
        if bot_amor and self.day_number == 1 and not self.amor_has_chosen:
            print(f"    - Bot '{bot_amor.user.display_name}' (Amor) is choosing lovers...")
            # Choose two random players (excluding Amor itself)
            potential_lovers = [p for p in self.get_alive_players() if p.user.id != bot_amor.user.id]
            if len(potential_lovers) >= 2:
                lovers = random.sample(potential_lovers, 2)
                lover1, lover2 = lovers[0], lovers[1]
                # Set the lover_target attribute that handle_night_action expects
                lover1.lover_target = lover2
                await self.handle_night_action(bot_amor, "love", lover1, self.config, self.gemini_api_key, self.openai_api_key)

        # The night now ends only when all special roles have acted.

    async def handle_night_action(self, author_player, command, target_player, config, gemini_key, openai_key):
        """Handles a night action from a player (kill or see)."""
        if self.phase != "night":
            return "Es ist nicht Nacht."
        if not author_player.is_alive:
            return "Tote können nichts tun."

        if command == "kill":
            if author_player.role != WERWOLF:
                return "Nur Werwölfe können töten."
            if target_player.role == WERWOLF:
                return "Du kannst nicht einen anderen Werwolf fressen, du Kannibale."
            
            # For simplicity, the first wolf's vote counts.
            self.night_votes[author_player.user.id] = target_player.user.id
            
            # Announce vote in wolf chat if it exists
            if self.werwolf_thread:
                await self.werwolf_thread.send(f"{author_player.user.display_name} hat für den Tod von **{target_player.user.display_name}** gestimmt. Das Schicksal ist besiegelt.")
            await author_player.user.send(f"Du hast für den Tod von {target_player.user.display_name} gestimmt.") # Also confirm in DM
            print(f"  [WW] {author_player.user.display_name} (Werwolf) voted to kill {target_player.user.display_name}.")
            
            # Inform the witch if one exists and is human
            hexe_player = next((p for p in self.get_alive_players() if p.role == HEXE and not self.is_bot_player(p)), None)
            if hexe_player:
                potion_status = "Du hast noch deinen Heiltrank." if hexe_player.has_healing_potion else "Du hast deinen Heiltrank bereits benutzt."
                await hexe_player.user.send(f"Die Werwölfe haben **{target_player.user.display_name}** als Opfer gewählt. Möchtest du deinen Heiltrank benutzen? `/ww heal`. {potion_status}")

            return await self.check_night_end() # Check if other roles are done

        if command == "see":
            if author_player.role != SEHERIN:
                return "Nur die Seherin kann die Rolle von jemandem sehen."
            if self.villagers_lost_powers:
                return "Der Weiße wurde gelyncht! Du hast deine Fähigkeiten verloren."
            if self.seer_choice:
                return "Du hast deine Fähigkeit für diese Nacht schon benutzt."
            
            self.seer_choice = target_player
            print(f"  [WW] {author_player.user.display_name} (Seherin) saw {target_player.user.display_name} ({target_player.role}).")
            await author_player.user.send(f"Du siehst, dass {target_player.user.display_name} ein(e) {target_player.role} ist.")
            
            return await self.check_night_end()

        if command == "heal":
            if author_player.role != HEXE:
                return "Nur die Hexe kann heilen."
            if self.villagers_lost_powers:
                return "Der Weiße wurde gelyncht! Du hast deine Fähigkeiten verloren."
            if not author_player.has_healing_potion:
                return "Du hast deinen Heiltrank schon benutzt."
            
            author_player.has_healing_potion = False
            self.hexe_heal_target_id = "used" # Mark as used, even if no victim LAGER
            print(f"  [WW] {author_player.user.display_name} (Hexe) used the healing potion.")
            return await self.check_night_end()

        if command == "poison":
            if author_player.role != HEXE:
                return "Nur die Hexe kann vergiften."
            if self.villagers_lost_powers:
                return "Der Weiße wurde gelyncht! Du hast deine Fähigkeiten verloren."
            if not author_player.has_kill_potion:
                return "Du hast deinen Gifttrank schon benutzt."
            if not target_player:
                return "Du musst ein Ziel für deinen Gifttrank angeben."
            
            author_player.has_kill_potion = False
            self.hexe_poison_target_id = target_player.user.id
            print(f"  [WW] {author_player.user.display_name} (Hexe) used the poison potion on {target_player.user.display_name}.")
            return await self.check_night_end()
        
        if command == "love":
            # NEW: Amor selecting lovers
            if author_player.role != AMOR:
                return "Nur Amor kann Verliebte wählen."
            if self.amor_has_chosen:
                return "Du hast bereits zwei Verliebte ausgewählt."
            if not target_player or not hasattr(target_player, 'lover_target'):
                return "Du musst zwei Spieler auswählen. Nutze: `love <name1> <name2>`"
            
            # target_player will have .lover_target set from parsing
            lover1 = target_player
            lover2 = getattr(target_player, 'lover_target', None)
            
            if not lover2:
                return "Du musst zwei verschiedene Spieler auswählen."
            if lover1.user.id == lover2.user.id:
                return "Die beiden Verliebten müssen verschiedene Spieler sein."
            
            # Set up lovers
            self.lovers = [lover1.user.id, lover2.user.id]
            lover1.lover_id = lover2.user.id
            lover2.lover_id = lover1.user.id
            self.amor_has_chosen = True
            
            print(f"  [WW] {author_player.user.display_name} (Amor) made {lover1.user.display_name} and {lover2.user.display_name} fall in love.")
            await author_player.user.send(f"Du hast {lover1.user.display_name} und {lover2.user.display_name} zu Verliebten gemacht.")
            
            # Inform the lovers
            try:
                await lover1.user.send(f"💘 Du hast dich in {lover2.user.display_name} verliebt! Ihr gewinnt nur zusammen.")
                await lover2.user.send(f"💘 Du hast dich in {lover1.user.display_name} verliebt! Ihr gewinnt nur zusammen.")
            except discord.Forbidden:
                pass
            
            return await self.check_night_end()

        if command == "mute":
            if author_player.role != DÖNERSTOPFER:
                return "Nur der Dönerstopfer kann jemanden stummschalten."
            if self.villagers_lost_powers:
                return "Der Weiße wurde gelyncht! Du hast deine Fähigkeiten verloren."
            if self.döner_mute_target_id:
                return "Du hast deine Fähigkeit für diese Nacht schon benutzt."
            if not target_player:
                return "Du musst ein Ziel zum Stummschalten angeben."
            self.döner_mute_target_id = target_player.user.id
            print(f"  [WW] {author_player.user.display_name} (Dönerstopfer) muted {target_player.user.display_name}.")
            return await self.check_night_end()

    async def check_night_end(self):
        """Checks if all night actions are done and transitions to day if so."""
        # If already transitioning, do nothing.
        if self.phase != "night":
            return

        alive_players = self.get_alive_players()
        num_werwolfe = len([p for p in alive_players if p.role == WERWOLF])
        
        # Check if human players with special roles have acted
        human_seer = next((p for p in alive_players if p.role == SEHERIN and not self.is_bot_player(p)), None)
        human_hexe = next((p for p in alive_players if p.role == HEXE and not self.is_bot_player(p)), None)
        human_döner = next((p for p in alive_players if p.role == DÖNERSTOPFER and not self.is_bot_player(p)), None)
        human_amor = next((p for p in alive_players if p.role == AMOR and not self.is_bot_player(p)), None)
        
        # Conditions to end night:
        # All human special roles must have acted (or not exist)
        seer_done = self.seer_choice is not None or not human_seer
        wolves_done = len(self.night_votes) >= 1 or num_werwolfe == 0
        # Hexe is done if they used a potion OR have no potions left
        hexe_done = (self.hexe_heal_target_id or self.hexe_poison_target_id or 
                    (human_hexe and not human_hexe.has_healing_potion and not human_hexe.has_kill_potion) or 
                    not human_hexe)
        döner_done = self.döner_mute_target_id is not None or not human_döner
        # Amor is done if they've chosen lovers OR if it's not the first night OR they don't exist
        amor_done = self.amor_has_chosen or self.day_number > 1 or not human_amor

        
        if seer_done and wolves_done and hexe_done and döner_done and amor_done:
            # Prevent this from being called multiple times by a race condition
            if self.phase == "day_transition":
                return
            print("  [WW] All night actions are complete. Transitioning to day...")
            self.phase = "day_transition" # Prevents this from being called multiple times
            await self.start_day()
        return None # Return None if the night doesn't end yet

    async def start_day(self):
        """Starts the day phase, revealing the night's victim."""
        self.phase = "day"
        self.voting_view = None # Clear the old view
        
        wolf_victim = None
        # Simple vote counting: just take the first vote.
        if self.night_votes:
            victim_id = list(self.night_votes.values())[0]
            wolf_victim = self.players.get(victim_id)
            print(f"  [WW] Night victim chosen: {wolf_victim.user.display_name if wolf_victim else 'None'}.")

        await self.log_event("Der Morgen dämmert und die Dorfbewohner versammeln sich.", send_tts=True)
        await asyncio.sleep(self.config['modules']['werwolf']['pacing']['after_morning_announcement'])

        # Resolve night events
        healed = False
        if wolf_victim and self.hexe_heal_target_id:
            healed = True
            print("  [WW] Victim was healed by the witch.")
        
        # --- NEW: Check if victim is Der Weiße with immunity ---
        weisse_saved = False
        if wolf_victim and not healed and wolf_victim.role == DER_WEISSE and not wolf_victim.weisse_immunity_used:
            weisse_saved = True
            wolf_victim.weisse_immunity_used = True
            print(f"  [WW] Der Weiße {wolf_victim.user.display_name} survived werewolf attack (immunity used).")

        # Announce wolf victim (or lack thereof)
        if wolf_victim and not healed and not weisse_saved:
            event = f"Ein schrecklicher Fund wurde gemacht. **{wolf_victim.user.display_name}** wurde getötet. Er/Sie war ein(e) **{wolf_victim.role}**."
            await self.log_event(event, send_tts=True)
            await self.kill_player(wolf_victim, "von den Werwölfen getötet")
            await asyncio.sleep(self.config['modules']['werwolf']['pacing']['after_victim_reveal'])
        else:
            event = "Wie durch ein Wunder ist in dieser Nacht niemand durch die Werwölfe gestorben."
            if healed:
                event += " Die Hexe hat ihr Werk vollbracht."
            elif weisse_saved:
                event += " Der Weiße hat überlebt!"
            await self.log_event(event, send_tts=True)
            await asyncio.sleep(self.config['modules']['werwolf']['pacing']['after_no_victim_announcement'])

        # Announce Hexe's poison victim
        if self.hexe_poison_target_id:
            poison_victim = self.players.get(self.hexe_poison_target_id)
            print(f"  [WW] Witch poison target: {poison_victim.user.display_name if poison_victim else 'None'}.")
            if poison_victim and poison_victim.is_alive:
                event = f"Ein weiteres Opfer wurde gefunden! **{poison_victim.user.display_name}** wurde von der Hexe vergiftet! Er/Sie war ein(e) **{poison_victim.role}**."
                await self.log_event(event, send_tts=True)
                await self.kill_player(poison_victim, "von der Hexe vergiftet")
                await asyncio.sleep(self.config['modules']['werwolf']['pacing']['after_victim_reveal'])

        # Check for win condition
        winner = self.check_win_condition()
        if winner:
            await self.end_game(self.config, winner_team=winner)
            return

        # On day 1, rename the lobby to the discussion channel. On subsequent days, undeafen.
        if self.day_number == 1 and self.lobby_vc:
            try:
                self.discussion_vc = self.lobby_vc
                await self.discussion_vc.edit(name=self.config['modules']['werwolf']['discussion_channel_name'], reason="Spielphase: Tag")
                await self.send_temp_message(f"Die Diskussion findet jetzt in {self.discussion_vc.mention} statt!", delay=15)
            except Exception as e:
                await self.game_channel.send(f"Konnte den Voice-Channel nicht umbenennen: {e}")
        
        if self.discussion_vc:
            # Undeafen alive players
            print("  [WW] Unmuting/undeafening players for the day phase...")
            for member in self.discussion_vc.members: # Iterate through all members
                player = self.players.get(member.id)
                if player and player.is_alive: # Only undeafen living players
                    await member.edit(mute=False, deafen=False, reason="Tagesphase beginnt")
                elif player and not player.is_alive:
                    # Mute dead players so they can't influence discussion
                    await member.edit(mute=True, deafen=False, reason="Geister sind tagsüber stumm")
        
        # Mute the Dönerstopfer's target
        if self.döner_mute_target_id:
            mute_target_player = self.players.get(self.döner_mute_target_id)
            if mute_target_player and mute_target_player.is_alive and self.discussion_vc:
                print(f"  [WW] Muting Dönerstopfer target: {mute_target_player.user.display_name}.")
                member_to_mute = self.discussion_vc.guild.get_member(mute_target_player.user.id)
                if member_to_mute and member_to_mute.voice:
                    await member_to_mute.edit(mute=True, reason="Vom Dönerstopfer gestopft")
                    await self.log_event(f"**{mute_target_player.user.display_name}** wurde vom Dönerstopfer für diesen Tag das Maul gestopft!", send_tts=True)


        # --- NEW: Start interactive voting process ---
        print("  [WW] Starting day voting process.")
        self.voting_view = VotingView(self, timeout=self.config['modules']['werwolf']['day_vote_timeout_seconds'])
        await self.voting_view.start_voting()
        
        # --- Bot Day Actions ---
        print("  [WW] Processing bot day votes...")
        # Bots now vote immediately and sequentially
        for player in self.get_alive_players():
            if self.is_bot_player(player):
                # --- NEW: Smarter bot voting logic ---
                # Bots will tend to vote for players who already have votes (bandwagon effect).
                # This makes them seem more decisive and less random.
                
                # Get current vote counts, excluding the bot's own potential vote
                vote_counts = self.voting_view.get_vote_counts()
                
                # Create a weighted list of potential targets
                potential_targets = []
                for p in self.get_alive_players():
                    if p.user.id == player.user.id: continue # Can't vote for self
                    # Each player gets one entry by default.
                    # For each vote they already have, they get 3 extra entries, making them a more likely target.
                    weight = 1 + (vote_counts.get(p.user.id, 0) * 3)
                    potential_targets.extend([p] * weight)

                if potential_targets:
                    target = random.choice(potential_targets)
                    self.handle_day_vote(player, target) # Register the vote
                    await self.voting_view.update_message() # Update the view to show the new vote
                    await asyncio.sleep(random.uniform(0.5, 1.5)) # Stagger bot votes
        # After all bots have voted, check if the voting can end early
        await self.voting_view.check_if_all_voted()


    def handle_day_vote(self, author_player, target_player):
        """Handles a player's vote during the day."""
        if self.phase != "day":
            return "Ihr könnt nur während des Tages abstimmen."
        if not author_player.is_alive:
            return "Tote können nicht abstimmen."
        if not target_player.is_alive:
            return "Du kannst nicht für einen Toten abstimmen."

        author_player.voted_for = target_player.user.id
        return f"{author_player.user.display_name} stimmt für **{target_player.user.display_name}**."

    def handle_skip_vote(self, author_player):
        author_player.voted_for = "skip"
        return f"{author_player.user.display_name} hat dafür gestimmt, den Tag zu überspringen."
        
    async def check_lynch(self, force_lynch_id=None):
        """Checks if a player has enough votes to be lynched."""
        alive_players = self.get_alive_players()
        votes_needed = len(alive_players) // 2 + 1

        vote_counts = {}
        for p in alive_players:
            if p.voted_for:
                vote_counts[p.voted_for] = vote_counts.get(p.voted_for, 0) + 1

        # Check for skip vote majority
        skip_votes = vote_counts.get("skip", 0)
        if skip_votes >= votes_needed:
            await self.skip_lynch()
            return True # Day was skipped

        # Check for a forced lynch from the timeout handler
        if force_lynch_id:
            lynched_player = self.players.get(force_lynch_id)
            if lynched_player:
                await self.process_lynch(lynched_player)
                return True

        # Check if any player has reached the vote threshold
        for target_id, count in vote_counts.items():
            if target_id == "skip":
                continue
            if count >= votes_needed:
                lynched_player = self.players.get(target_id)
                if lynched_player:
                    await self.process_lynch(lynched_player)
                    return True # A lynch happened

        return False # No lynch yet

    async def process_lynch(self, lynched_player):
        """Helper function to process a successful lynch."""
        event = f"Der Mob hat entschieden! **{lynched_player.user.display_name}** wird gelyncht! Er/Sie war ein(e) **{lynched_player.role}**."
        await self.log_event(event, send_tts=True)
        
        # --- NEW: Check if Der Weiße was lynched - penalty for villagers ---
        if lynched_player.role == DER_WEISSE and not self.villagers_lost_powers:
            self.villagers_lost_powers = True
            penalty_event = "⚠️ KATASTROPHE! Der Weiße wurde gelyncht! Alle Dorfbewohner verlieren ihre Spezialfähigkeiten!"
            await self.log_event(penalty_event, send_tts=True)
            # Note: The powers are disabled by checking self.villagers_lost_powers in ability usage
        
        await self.kill_player(lynched_player, "vom Mob gelyncht")
        await asyncio.sleep(self.config['modules']['werwolf']['pacing']['after_lynch_reveal'])
        await self.update_game_state_embed()

        for p in self.get_alive_players():
            p.voted_for = None

        await self.start_night_if_game_continues()

    async def process_lynch_votes(self):
        """Processes the final votes at the end of the day and lynches the player with the most votes."""
        vote_counts = {}
        for p in self.get_alive_players():
            if p.voted_for:
                vote_counts[p.voted_for] = vote_counts.get(p.voted_for, 0) + 1

        if not vote_counts:
            return False # No votes were cast

        # Find the player(s) with the most votes
        # Exclude 'skip' from this calculation
        player_votes = {k: v for k, v in vote_counts.items() if k != 'skip'}
        if not player_votes:
            return False # Only skip votes were cast

        max_votes = max(player_votes.values())
        most_voted_ids = [uid for uid, count in player_votes.items() if count == max_votes]

        # If there's a tie, no one is lynched
        if len(most_voted_ids) > 1:
            voted_names = [self.players[uid].user.display_name for uid in most_voted_ids]
            event = f"Es gab einen Stimmengleichstand zwischen **{', '.join(voted_names)}**. Niemand wird gelyncht."
            await self.log_event(event, send_tts=True)
            return False # Return False to indicate no lynch happened, but message was sent
        elif len(most_voted_ids) == 0:
             # This happens if only skip votes were cast
             return False

        # Lynch the player
        lynched_player_id = most_voted_ids[0]
        lynched_player = self.players.get(lynched_player_id)
        await self.process_lynch(lynched_player)
        return True

    async def start_night_if_game_continues(self):
        """Checks win condition and starts the night if the game is not over."""
        winner = self.check_win_condition()
        if winner:
            await self.end_game(self.config, winner_team=winner)
        else:
            await self.start_night()

    async def skip_lynch(self):
        """Handles the logic when a day is skipped."""
        event = "Die Dorfbewohner konnten sich nicht einigen und beschließen, niemanden zu lynchen."
        await self.log_event(event, send_tts=True)

        await self.update_game_state_embed()
        for p in self.get_alive_players():
            p.voted_for = None
        await self.start_night_if_game_continues()

    async def kill_player(self, player_to_kill, reason):
        """Handles all logic for a player's death."""
        if not player_to_kill.is_alive:
            return

        player_to_kill.is_alive = False

        # --- NEW: Handle lover death chain ---
        if player_to_kill.lover_id:
            lover_id = player_to_kill.lover_id
            lover = self.players.get(lover_id)
            if lover and lover.is_alive:
                await self.log_event(f"💔 {lover.user.display_name} stirbt aus Liebeskummer!", send_tts=True)
                lover.is_alive = False
                # Note: Lover's Jäger ability doesn't trigger from lover death

        # --- NEW: Handle Jäger's death ability ---
        if player_to_kill.role == JÄGER and not self.is_bot_player(player_to_kill):
            await self.log_event(f"Der Jäger {player_to_kill.user.display_name} ist gestorben! Er darf noch jemanden mit in den Tod nehmen.")
            try:
                alive_players = self.get_alive_players()
                target_options = [p.user.display_name for p in alive_players if p.user.id != player_to_kill.user.id]
                
                if target_options:
                    await player_to_kill.user.send(
                        f"Du wurdest {reason}! Als Jäger darfst du noch eine Person mit in den Tod nehmen.\n"
                        f"Schreibe den Namen der Person, die du mitnehmen möchtest:\n"
                        f"Verfügbare Ziele: {', '.join(target_options)}\n\n"
                        f"Du hast 60 Sekunden Zeit."
                    )
                    
                    def check(m):
                        return m.author.id == player_to_kill.user.id and isinstance(m.channel, discord.DMChannel)
                    
                    try:
                        msg = await self.bot_client.wait_for('message', timeout=60.0, check=check)
                        target_name = msg.content.strip()
                        
                        # Find the target player
                        target_player = None
                        for p in alive_players:
                            if p.user.display_name.lower() == target_name.lower():
                                target_player = p
                                break
                        
                        if target_player:
                            await self.log_event(f"💀 Der Jäger {player_to_kill.user.display_name} nimmt {target_player.user.display_name} mit in den Tod!", send_tts=True)
                            target_player.is_alive = False
                            
                            # Unmute the target if they're in voice
                            if self.discussion_vc and not self.is_bot_player(target_player):
                                member = self.discussion_vc.guild.get_member(target_player.user.id)
                                if member and member.voice and member.voice.channel == self.discussion_vc:
                                    try:
                                        await member.edit(mute=False, deafen=False, reason="Vom Jäger getötet")
                                    except (discord.Forbidden, discord.HTTPException):
                                        pass
                        else:
                            await player_to_kill.user.send(f"Ziel '{target_name}' nicht gefunden. Keine Aktion durchgeführt.")
                            await self.log_event(f"Der Jäger {player_to_kill.user.display_name} konnte niemanden mitnehmen.")
                    except asyncio.TimeoutError:
                        await player_to_kill.user.send("⏰ Zeit abgelaufen! Du konntest niemanden mitnehmen.")
                        await self.log_event(f"Der Jäger {player_to_kill.user.display_name} hat seine Chance verpasst.")
            except discord.Forbidden:
                await self.log_event(f"Der Jäger {player_to_kill.user.display_name} konnte keine DM erhalten für seine letzte Aktion.")

        # --- REFACTORED: Unmute dead players so they can talk at night ---
        if self.discussion_vc and not self.is_bot_player(player_to_kill):
            member = self.discussion_vc.guild.get_member(player_to_kill.user.id)
            if member and member.voice and member.voice.channel == self.discussion_vc:
                try:
                    # Unmute and undeafen the player so they can talk with other ghosts
                    await member.edit(mute=False, deafen=False, reason=f"Im Spiel getötet ({reason})")
                except (discord.Forbidden, discord.HTTPException):
                    print(f"Failed to unmute {member.display_name} after death.")

        # Send the role list to the dead player
        if not self.is_bot_player(player_to_kill):
            role_list_message = "**Das Spiel geht weiter! Hier sind die Rollen der verbleibenden Spieler:**\n"
            all_players = sorted(self.players.values(), key=lambda p: p.user.display_name)
            for p in all_players:
                status = "Lebend" if p.is_alive else "Tot"
                role_list_message += f"- {p.user.display_name}: {p.role} ({status})\n"
            try:
                await player_to_kill.user.send(role_list_message)
            except discord.Forbidden:
                pass # Can't send DMs to this user

    def check_win_condition(self):
        """Checks if a team has won."""
        alive_players = self.get_alive_players()
        num_werwolfe = len([p for p in alive_players if p.role == WERWOLF])
        num_villagers = len([p for p in alive_players if p.role != WERWOLF])

        if num_werwolfe == 0:
            return "Dorfbewohner"
        if num_werwolfe >= num_villagers:
            return "Werwölfe"
        return None

    async def end_game(self, config, winner_team=None, winner_message=None):
        """Ends the game and announces the winner."""
        if self.phase == "stopping" or self.phase == "finished":
            return # Already in the process of stopping
        self.phase = "stopping"

        # --- NEW: Record stats in the database ---
        if winner_team and config:
            winning_roles = []
            if winner_team == "Dorfbewohner":
                winning_roles = [DORFBEWOHNER, SEHERIN, HEXE, DÖNERSTOPFER, JÄGER, AMOR, DER_WEISSE]
            elif winner_team == "Werwölfe":
                winning_roles = [WERWOLF]

            # Count roles bought for stock influence
            roles_bought = sum(1 for p in self.players.values() if p.role in [SEHERIN, HEXE, DÖNERSTOPFER, JÄGER] and not self.is_bot_player(p))
            
            for player in self.players.values():
                # Don't record stats for bot players
                if self.is_bot_player(player):
                    continue
                
                won = player.role in winning_roles
                try:
                    await update_player_stats(player.user.id, player.user.display_name, won)
                except Exception as e:
                    # Log the error but continue cleanup — DB may be down on Termux or elsewhere
                    print(f"  [WW] Warning: failed to update stats for {player.user.display_name} ({player.user.id}): {e}")
                    import traceback
                    traceback.print_exc()
            
            # --- NEW: Influence WOLF stock based on game activity ---
            try:
                from modules import db_helpers
                num_players = len([p for p in self.players.values() if not self.is_bot_player(p)])
                await stock_market.record_werwolf_activity(db_helpers, num_players, roles_bought)
            except Exception as e:
                print(f"  [WW] Warning: failed to record stock influence: {e}")
                
        elif not config:
            # Game was cancelled before it truly started, no stats to record
            pass

        if winner_team:
            winner_message = f"Das Spiel ist vorbei! Die **{winner_team}** haben gewonnen!"
        elif not winner_message:
            winner_message = "Das Spiel wurde beendet."

        # --- NEW: Post summary to original channel ---
        if self.original_channel and config:
            embed_color = discord.Color(int(config.get('bot', {}).get('embed_color', '#7289DA').lstrip('#'), 16))
            summary_embed = discord.Embed(title="Werwolf - Spielzusammenfassung", description=winner_message, color=embed_color)
            player_roles = []
            for p in self.players.values():
                player_roles.append(f"**{p.user.display_name}**: {p.role}")
            summary_embed.add_field(name="Spieler und Rollen", value="\n".join(player_roles), inline=False)
            try:
                await self.original_channel.send(embed=summary_embed)
            except (discord.Forbidden, discord.HTTPException):
                print(f"Could not send summary to original channel {self.original_channel.id}")

        self.phase = "finished" # Mark as finished before cleanup

        # --- FIX: Unmute and undeafen all players before cleanup ---
        if self.discussion_vc:
            print(f"  [WW] Unmuting/undeafening all players before game end...")
            for member in self.discussion_vc.members:
                try:
                    await member.edit(mute=False, deafen=False, reason="Spiel beendet")
                    print(f"    - Unmuted/undeafened {member.display_name}")
                except (discord.Forbidden, discord.HTTPException) as e:
                    print(f"    - Could not unmute/undeafen {member.display_name}: {e}")

        # Delete the entire category, which cleans up all channels within it.
        if self.category:
            print(f"  [WW] Cleaning up game category '{self.category.name}' ({self.category.id})...")
            try:
                # --- FIX: Fetch the category again to get an up-to-date channel list.
                # This prevents race conditions where the channel list is stale.
                fresh_category = await self.game_channel.guild.fetch_channel(self.category.id)
                if fresh_category:
                    # Create a list of deletion tasks with channel names to run concurrently
                    deletion_tasks = []
                    channel_names = []
                    for channel in fresh_category.channels:
                        print(f"    - Queuing deletion for channel: {channel.name}")
                        channel_names.append(channel.name)
                        deletion_tasks.append(channel.delete(reason="Spielende"))
                    # Wait for all channel deletions to complete, catching exceptions
                    results = await asyncio.gather(*deletion_tasks, return_exceptions=True)
                    # Log any errors that occurred during deletion
                    for i, result in enumerate(results):
                        if isinstance(result, Exception):
                            channel_name = channel_names[i] if i < len(channel_names) else 'unknown'
                            print(f"    - Error deleting channel '{channel_name}': {result}")
                
                # Now, delete the category itself
                await fresh_category.delete(reason="Spielende")
                print(f"  [WW] Successfully cleaned up category.")
            except discord.NotFound:
                print(f"  [WW] Category already deleted, skipping cleanup.")
            except discord.Forbidden:
                print(f"  [WW] Missing permissions to delete category.")
            except Exception as e:
                print(f"  [WW] Error during category cleanup: {e}")
                import traceback
                traceback.print_exc()

        # The game object will be deleted from the main bot file.

# --- NEW: Interactive Voting View ---

class VotingView(View):
    def __init__(self, game: WerwolfGame, timeout=60.0):
        super().__init__(timeout=timeout)
        self.game = game
        self.message = None

        # Create a button for each alive player
        for player in self.game.get_alive_players():
            button = Button(label=player.user.display_name, custom_id=str(player.user.id))
            button.callback = self.button_callback
            self.add_item(button)
        
        # Add a skip button
        skip_button = Button(label="Abstimmung überspringen", style=discord.ButtonStyle.secondary, custom_id="skip_vote")
        skip_button.callback = self.skip_callback
        self.add_item(skip_button)

    def get_message_content(self):
        """Generates the text content for the voting message."""
        status = "Wer soll gelyncht werden? Stimmt jetzt ab!\n"
        if self.timeout is not None and self.timeout > 0:
            status += f"Verbleibende Zeit: **{int(self.timeout)} Sekunden**\n"
        else:
            status += "Die Zeit ist abgelaufen!\n"
        
        status += "\n" + self.get_leaderboard_text()
        return status

    async def on_timeout(self):
        """Called when the view times out (60 seconds)."""
        if self.game.phase != "day":
            return # Game has already moved on

        # Disable all buttons
        for item in self.children:
            item.disabled = True
        await self.update_message() # Update one last time to show disabled state
        
        lynch_happened = await self.game.process_lynch_votes()
        if not lynch_happened:
            await self.game.log_event("Die Zeit ist um! Der Mob konnte sich nicht entscheiden. Die Nacht bricht herein.", send_tts=True)
            await self.game.start_night_if_game_continues()

    async def start_voting(self):
        """Attaches the voting view to the main game state embed."""
        self.game.voting_view = self # Link view to game
        await self.game.update_game_state_embed(status_text="Wer soll gelyncht werden? Stimmt jetzt ab!", view=self)
        self.message = self.game.game_state_message
        asyncio.get_running_loop().create_task(self.update_timer())

    async def update_message(self):
        """Updates the game state embed with new voting content."""
        if self.game.game_state_message:
            status = self.get_message_content()
            await self.game.update_game_state_embed(status_text="Wer soll gelyncht werden? Stimmt jetzt ab!", view=self)

    def get_leaderboard_text(self):
        """Generates the text for the current vote counts."""
        vote_counts = {}
        for p in self.game.get_alive_players():
            if p.voted_for:
                vote_counts[p.voted_for] = vote_counts.get(p.voted_for, 0) + 1
        
        if not vote_counts:
            return "🔸 Noch keine Stimmen."
        
        # Sort by vote count (descending)
        sorted_votes = sorted(vote_counts.items(), key=lambda x: x[1], reverse=True)
        
        leaderboard_lines = []
        for uid, count in sorted_votes:
            player_name = self.game.players[uid].user.display_name if uid != 'skip' else '⏭️ Überspringen'
            # Use emoji indicators for vote counts
            vote_bar = "🔴" * count
            leaderboard_lines.append(f"{vote_bar} **{player_name}**: {count} Stimme(n)")
        
        return "\n".join(leaderboard_lines)

    def get_vote_counts(self):
        """Helper to get a dictionary of vote counts."""
        vote_counts = {}
        for p in self.game.get_alive_players():
            if p.voted_for:
                vote_counts[p.voted_for] = vote_counts.get(p.voted_for, 0) + 1
        return vote_counts


    async def update_timer(self):
        """Periodically updates the timer on the message."""
        while self.timeout > 0:
            await asyncio.sleep(5)
            if self.is_finished() or self.game.phase != "day":
                return
            self.timeout -= 5
            await self.update_message()

    async def button_callback(self, interaction: discord.Interaction):
        voter_player = self.game.players.get(interaction.user.id)
        target_player = self.game.players.get(int(interaction.data['custom_id']))

        if not voter_player or not voter_player.is_alive:
            await interaction.response.send_message("Du bist nicht im Spiel oder bereits tot.", ephemeral=True)
            return

        response = self.game.handle_day_vote(voter_player, target_player)
        await interaction.response.send_message(response, ephemeral=True) # Send confirmation privately
        await self.update_message()
        
        # Check for majority lynch first
        lynch_happened = await self.game.check_lynch()
        if not lynch_happened:
            # If no majority, check if everyone has voted
            await self.check_if_all_voted()

    async def skip_callback(self, interaction: discord.Interaction):
        voter_player = self.game.players.get(interaction.user.id)
        if not voter_player or not voter_player.is_alive:
            await interaction.response.send_message("Du bist nicht im Spiel oder bereits tot.", ephemeral=True)
            return

        response = self.game.handle_skip_vote(voter_player)
        await interaction.response.send_message(response, ephemeral=True)
        await self.update_message()
        
        lynch_happened = await self.game.check_lynch()
        if not lynch_happened:
            await self.check_if_all_voted()

    async def check_if_all_voted(self):
        """If all living players have voted, end the voting phase early."""
        alive_players = self.game.get_alive_players()
        voted_players = [p for p in alive_players if p.voted_for is not None]
        if len(voted_players) == len(alive_players):
            if self.is_finished():
                return # Already stopped and processed

            self.stop() # Stop the view from accepting new inputs

            # Disable all buttons
            for item in self.children:
                item.disabled = True
            await self.update_message()

            await self.game.log_event("Alle haben abgestimmt! Die Stimmen werden ausgezählt...", send_tts=True)
            lynch_happened = await self.game.process_lynch_votes()
            if not lynch_happened:
                await self.game.log_event("Der Mob konnte sich nicht entscheiden. Die Nacht bricht herein.", send_tts=True)
                await self.game.start_night_if_game_continues()