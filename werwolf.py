import asyncio
import discord
from collections import deque
from discord.ui import View, Button
from api_helpers import get_werwolf_tts_message, get_random_names
import re
from fake_user import FakeUser
import random
from db_helpers import update_player_stats

# --- Roles ---
DORFBEWOHNER = "Dorfbewohner"
WERWOLF = "Werwolf"
SEHERIN = "Seherin"
HEXE = "Hexe"
DÖNERSTOPFER = "Dönerstopfer"

class WerwolfPlayer:
    """Represents a player in the game."""
    def __init__(self, user):
        self.user = user
        self.role = None
        self.has_healing_potion = False
        self.has_kill_potion = False
        self.is_alive = True
        self.voted_for = None # For day voting

class WerwolfGame:
    """Manages the state and logic of a single Werwolf game."""

    def __init__(self, game_channel, starter, original_channel):
        self.api_url = None # Will be set from bot.py
        self.game_channel = game_channel # This is now the dedicated text channel
        self.starter = starter
        self.original_channel = original_channel # Channel where game was started
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

        self.config = None # Will be set when the game starts
        self.gemini_api_key = None
        self.openai_api_key = None
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
            tts_content_from_api = await get_werwolf_tts_message(event_text, self.config, self.gemini_api_key, self.openai_api_key)
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

        title = "Werwolf"
        color = discord.Color(int(self.config.get('bot', {}).get('embed_color', '#7289DA').lstrip('#'), 16))

        if self.phase == "night":
            title = f"Werwolf - Nacht {self.day_number}"
        elif self.phase == "day":
            title = f"Werwolf - Tag {self.day_number}"
        elif self.phase == "finished":
            title = f"Werwolf - Spiel beendet"
        description = status_text or (self.event_log[-1] if self.event_log else "Das Spiel beginnt...")

        embed = discord.Embed(title=title, description=description, color=color)
        alive_players = self.get_alive_players()
        if alive_players:
            embed.add_field(name=f"Lebende Spieler ({len(alive_players)})", value="\n".join([p.user.display_name for p in alive_players]), inline=False)
        
        # Add the event log to the embed
        if self.event_log:
            log_text = "\n".join(f"- {msg}" for msg in reversed(self.event_log))
            embed.add_field(name="Letzte Ereignisse", value=log_text, inline=False)
        # During the day, add vote counts
        if self.phase == "day" and self.voting_view:
            leaderboard = self.voting_view.get_leaderboard_text()
            embed.add_field(name="Aktuelle Stimmen", value=leaderboard, inline=False)

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

    def get_player_by_name(self, name):
        """Finds an alive player by their display name (case-insensitive)."""
        name_lower = name.lower()
        for player in self.get_alive_players():
            if player.user.display_name.lower() == name_lower:
                return player
        return None
    async def start_game(self, config, gemini_key, openai_key, db_helpers, ziel_spieler=None):
        """Assigns roles and starts the first night."""
        if self.phase != "joining":
            return "Das Spiel läuft bereits."
        
        self.config = config # Store config for later use
        self.gemini_api_key = gemini_key
        self.openai_api_key = openai_key

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
                bot_names = await get_random_names(bots_to_add, db_helpers, self.config, self.gemini_api_key, self.openai_api_key)
                await asyncio.sleep(2)
                for name in bot_names:
                    bot_name = name
                    # Check for name collisions, though unlikely
                    while self.get_player_by_name(bot_name):
                        bot_name += "+"
                    fake_user = FakeUser(name=bot_name)
                    self.add_player(fake_user)
        
        player_count = len(self.players) # Recalculate after adding bots

        # --- Role Assignment ---
        # Logic adjusted for small player counts
        if player_count == 1:
            num_werwolfe = 1
            num_seherin, num_hexe, num_döner = 0, 0, 0
        elif player_count == 2:
            num_werwolfe = 1
            num_seherin = 1
            num_hexe, num_döner = 0, 0
        else:
            num_werwolfe = max(1, player_count // 3)
            num_seherin = 1 if player_count > 2 else 0
            num_hexe = 1 if player_count >= 7 else 0
            num_döner = 1 if player_count >= 9 else 0
        
        num_dorfbewohner = player_count - num_werwolfe - num_seherin - num_hexe - num_döner

        roles = ([WERWOLF] * num_werwolfe + [SEHERIN] * num_seherin + [HEXE] * num_hexe + 
                 [DÖNERSTOPFER] * num_döner + [DORFBEWOHNER] * num_dorfbewohner)
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
        
        # Check if there's a human wolf
        human_wolf_exists = any(p for p in self.get_alive_players() if p.role == WERWOLF and not self.is_bot_player(p))

        # --- NEW: Bot actions are now processed in a logical order ---
        # 1. Seer acts first to gather information.
        # 2. Wolves act next.
        # 3. Witch acts last, using information from the night's events.
        for player in self.get_alive_players():
            if not self.is_bot_player(player):
                continue
            if player.role == WERWOLF:
                # If a human wolf exists, the bot does not act. The human decides.
                if human_wolf_exists:
                    continue
                print(f"    - Bot '{player.user.display_name}' (Werwolf) is choosing a target...")
                # Bot wolf picks a random non-wolf to kill
                targets = [p for p in self.get_alive_players() if p.role != WERWOLF]
                if targets:
                    target = random.choice(targets)
                    await self.handle_night_action(player, "kill", target, self.config, self.gemini_api_key, self.openai_api_key)
            elif player.role == SEHERIN:
                print(f"    - Bot '{player.user.display_name}' (Seherin) is choosing a target...")
                # Bot seer picks a random player to see (not themselves)
                targets = [p for p in self.get_alive_players() if p.user.id != player.user.id]
                if targets:
                    target = random.choice(targets)
                    # --- NEW: Seer bot now records its findings ---
                    self.seer_findings[target.user.id] = target.role
                    await self.handle_night_action(player, "see", target, self.config, self.gemini_api_key, self.openai_api_key)
        
        # --- NEW: Process Dönerstopfer action after Seer/Wolf ---
        for player in self.get_alive_players():
            if self.is_bot_player(player) and player.role == DÖNERSTOPFER:
                print(f"    - Bot '{player.user.display_name}' (Dönerstopfer) is choosing a target...")
                targets = [p for p in self.get_alive_players() if p.user.id != player.user.id]
                if targets:
                    target = random.choice(targets)
                    await self.handle_night_action(player, "mute", target, self.config, self.gemini_api_key, self.openai_api_key)

        # --- NEW: Process Hexe action last ---
        for player in self.get_alive_players():
            if self.is_bot_player(player) and player.role == HEXE:
                # Hexe decides whether to heal
                wolf_victim_id = next(iter(self.night_votes.values()), None)
                if wolf_victim_id and player.has_healing_potion:
                    wolf_victim = self.players.get(wolf_victim_id)
                    # Heal if the victim is not a known wolf
                    if wolf_victim and self.seer_findings.get(wolf_victim.user.id) != WERWOLF:
                        await self.handle_night_action(player, "heal", None, self.config, self.gemini_api_key, self.openai_api_key)
                # Hexe decides whether to poison
                elif player.has_kill_potion:
                    # Poison a known wolf
                    known_wolves = [p_id for p_id, role in self.seer_findings.items() if role == WERWOLF]
                    if known_wolves:
                        target_to_poison = self.players.get(random.choice(known_wolves))
                        if target_to_poison and target_to_poison.is_alive:
                            await self.handle_night_action(player, "poison", target_to_poison, self.config, self.gemini_api_key, self.openai_api_key)

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
            if self.seer_choice:
                return "Du hast deine Fähigkeit für diese Nacht schon benutzt."
            
            self.seer_choice = target_player
            print(f"  [WW] {author_player.user.display_name} (Seherin) saw {target_player.user.display_name} ({target_player.role}).")
            await author_player.user.send(f"Du siehst, dass {target_player.user.display_name} ein(e) {target_player.role} ist.")
            
            return await self.check_night_end()

        if command == "heal":
            if author_player.role != HEXE:
                return "Nur die Hexe kann heilen."
            if not author_player.has_healing_potion:
                return "Du hast deinen Heiltrank schon benutzt."
            
            author_player.has_healing_potion = False
            self.hexe_heal_target_id = "used" # Mark as used, even if no victim LAGER
            print(f"  [WW] {author_player.user.display_name} (Hexe) used the healing potion.")
            return await self.check_night_end()

        if command == "poison":
            if author_player.role != HEXE:
                return "Nur die Hexe kann vergiften."
            if not author_player.has_kill_potion:
                return "Du hast deinen Gifttrank schon benutzt."
            if not target_player:
                return "Du musst ein Ziel für deinen Gifttrank angeben."
            
            author_player.has_kill_potion = False
            self.hexe_poison_target_id = target_player.user.id
            print(f"  [WW] {author_player.user.display_name} (Hexe) used the poison potion on {target_player.user.display_name}.")
            return await self.check_night_end()

        if command == "mute":
            if author_player.role != DÖNERSTOPFER:
                return "Nur der Dönerstopfer kann jemanden stummschalten."
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
        
        # Conditions to end night:
        # All human special roles must have acted (or not exist)
        seer_done = self.seer_choice is not None or not human_seer
        wolves_done = len(self.night_votes) >= 1 or num_werwolfe == 0
        # Hexe is done if they used a potion OR have no potions left
        hexe_done = (self.hexe_heal_target_id or self.hexe_poison_target_id or 
                    (human_hexe and not human_hexe.has_healing_potion and not human_hexe.has_kill_potion) or 
                    not human_hexe)
        döner_done = self.döner_mute_target_id is not None or not human_döner

        
        if seer_done and wolves_done and hexe_done and döner_done:
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

        # Announce wolf victim (or lack thereof)
        if wolf_victim and not healed:
            event = f"Ein schrecklicher Fund wurde gemacht. **{wolf_victim.user.display_name}** wurde getötet. Er/Sie war ein(e) **{wolf_victim.role}**."
            await self.log_event(event, send_tts=True)
            await self.kill_player(wolf_victim, "von den Werwölfen getötet")
            await asyncio.sleep(self.config['modules']['werwolf']['pacing']['after_victim_reveal'])
        else:
            event = "Wie durch ein Wunder ist in dieser Nacht niemand durch die Werwölfe gestorben."
            if healed:
                event += " Die Hexe hat ihr Werk vollbracht."
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
        if self.phase == "stopping":
            return # Already in the process of stopping
        self.phase = "stopping"

        # --- NEW: Record stats in the database ---
        if winner_team:
            winning_roles = []
            if winner_team == "Dorfbewohner":
                winning_roles = [DORFBEWOHNER, SEHERIN, HEXE, DÖNERSTOPFER]
            elif winner_team == "Werwölfe":
                winning_roles = [WERWOLF]

            for player in self.players.values():
                # Don't record stats for bot players
                if self.is_bot_player(player):
                    continue
                
                won = player.role in winning_roles
                await update_player_stats(player.user.id, player.user.display_name, won)

        if winner_team:
            winner_message = f"Das Spiel ist vorbei! Die **{winner_team}** haben gewonnen!"
        elif not winner_message:
            winner_message = "Das Spiel wurde beendet."

        # --- NEW: Post summary to original channel ---
        if self.original_channel:
            embed_color = discord.Color(int(self.config.get('bot', {}).get('embed_color', '#7289DA').lstrip('#'), 16))
            summary_embed = discord.Embed(title="Werwolf - Spielzusammenfassung", description=winner_message, color=embed_color)
            player_roles = []
            for p in self.players.values():
                player_roles.append(f"**{p.user.display_name}**: {p.role}")
            summary_embed.add_field(name="Spieler und Rollen", value="\n".join(player_roles), inline=False)
            try:
                await self.original_channel.send(embed=summary_embed)
            except discord.Forbidden:
                print(f"Could not send summary to original channel {self.original_channel.id}")

        self.phase = "finished" # Mark as finished before cleanup

        # Delete the entire category, which cleans up all channels within it.
        if self.category:
            print(f"  [WW] Cleaning up game category '{self.category.name}' ({self.category.id})...")
            try:
                # --- FIX: Fetch the category again to get an up-to-date channel list.
                # This prevents race conditions where the channel list is stale.
                fresh_category = await self.game_channel.guild.fetch_channel(self.category.id)
                if fresh_category:
                    # Create a list of deletion tasks to run concurrently
                    deletion_tasks = []
                    for channel in fresh_category.channels:
                        print(f"    - Queuing deletion for channel: {channel.name}")
                        deletion_tasks.append(channel.delete(reason="Spielende"))
                    # Wait for all channel deletions to complete
                    await asyncio.gather(*deletion_tasks, return_exceptions=True)
                
                # Now, delete the category itself
                await fresh_category.delete(reason="Spielende")
                print(f"  [WW] Successfully cleaned up category.")
            except Exception as e:
                print(f"Fehler beim Aufräumen der Spiel-Kategorie: {e}")

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
        
        return "\n".join([f"**{self.game.players[uid].user.display_name if uid != 'skip' else 'Überspringen'}**: {count} Stimme(n)" for uid, count in vote_counts.items()]) or "Noch keine Stimmen."

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