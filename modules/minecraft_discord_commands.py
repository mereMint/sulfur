"""
Minecraft and VPN Discord Commands for Sulfur Bot

Provides:
- /minecraft - User registration for Minecraft server (one account per user)
- /mcstart, /mcstop, /mcrestart - Admin server control
- /mcstatus - Server status for everyone
- /mcwhitelist - Admin whitelist management
- /vpn - Admin VPN management and connection info
"""

import discord
from discord import app_commands
from discord.ext import tasks
from typing import Optional, List
from datetime import datetime, timezone
import asyncio

from modules.logger_utils import bot_logger as logger


# ==============================================================================
# Database Helpers for Minecraft
# ==============================================================================

async def get_minecraft_account(db_helpers, discord_user_id: int) -> Optional[dict]:
    """Get the linked Minecraft account for a Discord user (one per user)."""
    if not db_helpers.db_pool:
        return None
    
    conn = None
    cursor = None
    try:
        conn = db_helpers.get_db_connection()
        if not conn:
            return None
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM minecraft_players 
            WHERE discord_user_id = %s
            LIMIT 1
        """, (discord_user_id,))
        
        return cursor.fetchone()
    except Exception as e:
        logger.error(f"Error getting Minecraft account: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


async def get_pending_join_request(db_helpers, discord_user_id: int) -> Optional[dict]:
    """Get pending join request for a user."""
    if not db_helpers.db_pool:
        return None
    
    conn = None
    cursor = None
    try:
        conn = db_helpers.get_db_connection()
        if not conn:
            return None
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM minecraft_join_requests 
            WHERE discord_user_id = %s AND status = 'pending'
            ORDER BY requested_at DESC
            LIMIT 1
        """, (discord_user_id,))
        
        return cursor.fetchone()
    except Exception as e:
        logger.error(f"Error getting join request: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


async def create_join_request(db_helpers, discord_user_id: int, minecraft_username: str) -> tuple[bool, str]:
    """
    Create a new join request. Enforces one Minecraft account per Discord user.
    
    Returns:
        Tuple of (success, message)
    """
    if not db_helpers.db_pool:
        return False, "Database not available"
    
    conn = None
    cursor = None
    try:
        conn = db_helpers.get_db_connection()
        if not conn:
            return False, "Database connection failed"
        
        cursor = conn.cursor(dictionary=True)
        
        # Check if user already has a linked account
        cursor.execute("""
            SELECT minecraft_username FROM minecraft_players 
            WHERE discord_user_id = %s
        """, (discord_user_id,))
        existing = cursor.fetchone()
        
        if existing:
            return False, f"Du hast bereits einen verknüpften Minecraft-Account: **{existing['minecraft_username']}**. Jeder Discord-Nutzer kann nur einen Minecraft-Account haben."
        
        # Check if user already has a pending request
        cursor.execute("""
            SELECT minecraft_username FROM minecraft_join_requests 
            WHERE discord_user_id = %s AND status = 'pending'
        """, (discord_user_id,))
        pending = cursor.fetchone()
        
        if pending:
            return False, f"Du hast bereits eine ausstehende Anfrage für: **{pending['minecraft_username']}**. Bitte warte auf die Bearbeitung durch einen Admin."
        
        # Check if this Minecraft username is already linked to another Discord user
        cursor.execute("""
            SELECT discord_user_id FROM minecraft_players 
            WHERE LOWER(minecraft_username) = LOWER(%s)
        """, (minecraft_username,))
        username_taken = cursor.fetchone()
        
        if username_taken:
            return False, f"Der Minecraft-Name **{minecraft_username}** ist bereits mit einem anderen Discord-Account verknüpft."
        
        # Create the join request
        cursor.execute("""
            INSERT INTO minecraft_join_requests 
            (discord_user_id, minecraft_username, status, requested_at)
            VALUES (%s, %s, 'pending', NOW())
            ON DUPLICATE KEY UPDATE 
            minecraft_username = VALUES(minecraft_username),
            status = 'pending',
            requested_at = NOW()
        """, (discord_user_id, minecraft_username))
        
        conn.commit()
        return True, f"Anfrage für **{minecraft_username}** wurde erstellt. Ein Admin wird sie prüfen."
        
    except Exception as e:
        logger.error(f"Error creating join request: {e}")
        return False, f"Fehler beim Erstellen der Anfrage: {e}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


async def get_all_pending_requests(db_helpers) -> List[dict]:
    """Get all pending join requests."""
    if not db_helpers.db_pool:
        return []
    
    conn = None
    cursor = None
    try:
        conn = db_helpers.get_db_connection()
        if not conn:
            return []
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM minecraft_join_requests 
            WHERE status = 'pending'
            ORDER BY requested_at ASC
        """)
        
        return cursor.fetchall()
    except Exception as e:
        logger.error(f"Error getting pending requests: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


async def approve_join_request(
    db_helpers, 
    request_id: int, 
    admin_id: int,
    minecraft_server
) -> tuple[bool, str, Optional[int]]:
    """
    Approve a join request and add to whitelist.
    
    Returns:
        Tuple of (success, message, discord_user_id)
    """
    if not db_helpers.db_pool:
        return False, "Database not available", None
    
    conn = None
    cursor = None
    try:
        conn = db_helpers.get_db_connection()
        if not conn:
            return False, "Database connection failed", None
        
        cursor = conn.cursor(dictionary=True)
        
        # Get the request
        cursor.execute("""
            SELECT * FROM minecraft_join_requests 
            WHERE id = %s AND status = 'pending'
        """, (request_id,))
        request = cursor.fetchone()
        
        if not request:
            return False, "Anfrage nicht gefunden oder bereits bearbeitet", None
        
        discord_user_id = request['discord_user_id']
        mc_username = request['minecraft_username']
        
        # Update request status
        cursor.execute("""
            UPDATE minecraft_join_requests 
            SET status = 'approved', processed_at = NOW(), processed_by = %s
            WHERE id = %s
        """, (admin_id, request_id))
        
        # Create player entry (one account per Discord user)
        cursor.execute("""
            INSERT INTO minecraft_players 
            (discord_user_id, minecraft_username, whitelisted, first_joined)
            VALUES (%s, %s, TRUE, NOW())
            ON DUPLICATE KEY UPDATE 
            minecraft_username = VALUES(minecraft_username),
            whitelisted = TRUE
        """, (discord_user_id, mc_username))
        
        conn.commit()
        
        # Add to server whitelist if running
        if minecraft_server.is_server_running():
            await minecraft_server.add_to_whitelist(mc_username)
        
        return True, f"**{mc_username}** wurde zur Whitelist hinzugefügt!", discord_user_id
        
    except Exception as e:
        logger.error(f"Error approving request: {e}")
        return False, f"Fehler: {e}", None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


async def reject_join_request(db_helpers, request_id: int, admin_id: int, reason: str = None) -> tuple[bool, str, Optional[int]]:
    """
    Reject a join request.
    
    Returns:
        Tuple of (success, message, discord_user_id)
    """
    if not db_helpers.db_pool:
        return False, "Database not available", None
    
    conn = None
    cursor = None
    try:
        conn = db_helpers.get_db_connection()
        if not conn:
            return False, "Database connection failed", None
        
        cursor = conn.cursor(dictionary=True)
        
        # Get the request
        cursor.execute("""
            SELECT * FROM minecraft_join_requests 
            WHERE id = %s AND status = 'pending'
        """, (request_id,))
        request = cursor.fetchone()
        
        if not request:
            return False, "Anfrage nicht gefunden oder bereits bearbeitet", None
        
        discord_user_id = request['discord_user_id']
        
        # Update request status
        cursor.execute("""
            UPDATE minecraft_join_requests 
            SET status = 'rejected', processed_at = NOW(), processed_by = %s, notes = %s
            WHERE id = %s
        """, (admin_id, reason, request_id))
        
        conn.commit()
        
        return True, f"Anfrage abgelehnt.", discord_user_id
        
    except Exception as e:
        logger.error(f"Error rejecting request: {e}")
        return False, f"Fehler: {e}", None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ==============================================================================
# VPN Connection Tutorial
# ==============================================================================

def get_vpn_tutorial_embed(server_endpoint: str, client_config: str = None) -> discord.Embed:
    """Create an embed with VPN connection instructions."""
    embed = discord.Embed(
        title="🔐 VPN Verbindungsanleitung",
        description="Um auf den Minecraft-Server zugreifen zu können, musst du dich mit unserem VPN verbinden.",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="📥 Schritt 1: WireGuard installieren",
        value=(
            "**Windows/Mac:** [wireguard.com/install](https://www.wireguard.com/install/)\n"
            "**Android:** [Play Store](https://play.google.com/store/apps/details?id=com.wireguard.android)\n"
            "**iOS:** [App Store](https://apps.apple.com/app/wireguard/id1441195209)"
        ),
        inline=False
    )
    
    embed.add_field(
        name="📋 Schritt 2: Konfiguration importieren",
        value=(
            "1. Öffne WireGuard\n"
            "2. Klicke auf 'Tunnel hinzufügen' oder '+'\n"
            "3. Importiere die Konfigurationsdatei (wird per DM gesendet)"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🔌 Schritt 3: Verbinden",
        value=(
            "1. Aktiviere den VPN-Tunnel in WireGuard\n"
            "2. Warte bis 'Handshake' angezeigt wird\n"
            "3. Du bist jetzt verbunden!"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🎮 Schritt 4: Minecraft Server beitreten",
        value=f"Server-Adresse: `{server_endpoint}`",
        inline=False
    )
    
    embed.set_footer(text="Bei Problemen wende dich an einen Admin.")
    
    return embed


# ==============================================================================
# Discord UI Components
# ==============================================================================

class MinecraftJoinModal(discord.ui.Modal, title="Minecraft Server beitreten"):
    """Modal for users to enter their Minecraft username."""
    
    minecraft_name = discord.ui.TextInput(
        label="Dein Minecraft-Name",
        placeholder="z.B. Steve123",
        min_length=3,
        max_length=16,
        required=True
    )
    
    def __init__(self, db_helpers):
        super().__init__()
        self.db_helpers = db_helpers
    
    async def on_submit(self, interaction: discord.Interaction):
        username = self.minecraft_name.value.strip()
        
        # Validate username format (Minecraft usernames are 3-16 chars, alphanumeric + underscore)
        import re
        if not re.match(r'^[a-zA-Z0-9_]{3,16}$', username):
            await interaction.response.send_message(
                "❌ Ungültiger Minecraft-Name! Erlaubt sind nur Buchstaben, Zahlen und Unterstriche (3-16 Zeichen).",
                ephemeral=True
            )
            return
        
        success, message = await create_join_request(self.db_helpers, interaction.user.id, username)
        
        if success:
            embed = discord.Embed(
                title="✅ Anfrage gesendet!",
                description=message,
                color=discord.Color.green()
            )
            embed.add_field(
                name="Nächste Schritte",
                value="Ein Admin wird deine Anfrage prüfen. Du wirst per DM benachrichtigt, sobald sie bearbeitet wurde.",
                inline=False
            )
        else:
            embed = discord.Embed(
                title="❌ Anfrage fehlgeschlagen",
                description=message,
                color=discord.Color.red()
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class WhitelistRequestView(discord.ui.View):
    """View for admins to approve/reject whitelist requests."""
    
    def __init__(self, db_helpers, minecraft_server, request_id: int, mc_username: str, discord_user_id: int):
        super().__init__(timeout=None)
        self.db_helpers = db_helpers
        self.minecraft_server = minecraft_server
        self.request_id = request_id
        self.mc_username = mc_username
        self.discord_user_id = discord_user_id
    
    @discord.ui.button(label="✅ Genehmigen", style=discord.ButtonStyle.success)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check admin permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Nur Admins können Anfragen bearbeiten.", ephemeral=True)
            return
        
        success, message, user_id = await approve_join_request(
            self.db_helpers, 
            self.request_id, 
            interaction.user.id,
            self.minecraft_server
        )
        
        if success:
            # Update the message
            embed = discord.Embed(
                title="✅ Anfrage genehmigt",
                description=f"**{self.mc_username}** wurde zur Whitelist hinzugefügt.",
                color=discord.Color.green()
            )
            embed.add_field(name="Bearbeitet von", value=interaction.user.mention)
            
            # Disable buttons
            for child in self.children:
                child.disabled = True
            
            await interaction.response.edit_message(embed=embed, view=self)
            
            # Notify the user
            if user_id:
                try:
                    user = await interaction.client.fetch_user(user_id)
                    
                    # Send approval notification with VPN tutorial
                    approval_embed = discord.Embed(
                        title="🎉 Minecraft-Anfrage genehmigt!",
                        description=f"Dein Minecraft-Account **{self.mc_username}** wurde zur Whitelist hinzugefügt!",
                        color=discord.Color.green()
                    )
                    
                    await user.send(embed=approval_embed)
                    
                    # Send VPN tutorial
                    # Get server endpoint from config
                    server_endpoint = "10.0.0.1:25565"  # Default, should come from config
                    vpn_embed = get_vpn_tutorial_embed(server_endpoint)
                    await user.send(embed=vpn_embed)
                    
                except discord.Forbidden:
                    await interaction.followup.send(
                        f"⚠️ Konnte {self.mc_username} nicht per DM benachrichtigen (DMs geschlossen).",
                        ephemeral=True
                    )
        else:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)
    
    @discord.ui.button(label="❌ Ablehnen", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check admin permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Nur Admins können Anfragen bearbeiten.", ephemeral=True)
            return
        
        success, message, user_id = await reject_join_request(
            self.db_helpers, 
            self.request_id, 
            interaction.user.id,
            "Anfrage abgelehnt"
        )
        
        if success:
            embed = discord.Embed(
                title="❌ Anfrage abgelehnt",
                description=f"Anfrage für **{self.mc_username}** wurde abgelehnt.",
                color=discord.Color.red()
            )
            embed.add_field(name="Bearbeitet von", value=interaction.user.mention)
            
            for child in self.children:
                child.disabled = True
            
            await interaction.response.edit_message(embed=embed, view=self)
            
            # Notify user
            if user_id:
                try:
                    user = await interaction.client.fetch_user(user_id)
                    reject_embed = discord.Embed(
                        title="❌ Minecraft-Anfrage abgelehnt",
                        description=f"Deine Anfrage für **{self.mc_username}** wurde leider abgelehnt.",
                        color=discord.Color.red()
                    )
                    reject_embed.add_field(
                        name="Was tun?",
                        value="Kontaktiere einen Admin für weitere Informationen."
                    )
                    await user.send(embed=reject_embed)
                except discord.Forbidden:
                    pass
        else:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)


# ==============================================================================
# Command Registration Functions
# ==============================================================================

def register_minecraft_commands(tree: app_commands.CommandTree, db_helpers, minecraft_server, config, wireguard_manager=None):
    """
    Register all Minecraft and VPN related commands.
    
    Args:
        tree: The Discord command tree
        db_helpers: Database helpers module
        minecraft_server: Minecraft server module
        config: Bot configuration
        wireguard_manager: Optional WireGuard manager module
    """
    
    # Admin check decorator
    def is_admin():
        async def predicate(interaction: discord.Interaction) -> bool:
            if interaction.user.guild_permissions.administrator:
                return True
            # Check for authorised role
            authorised_role_name = config.get('bot', {}).get('authorised_role', 'authorised')
            authorised_role = discord.utils.get(interaction.guild.roles, name=authorised_role_name)
            if authorised_role and authorised_role in interaction.user.roles:
                return True
            return False
        return app_commands.check(predicate)
    
    # ==========================================================================
    # /minecraft - User command to join the server
    # ==========================================================================
    
    @tree.command(name="minecraft", description="🎮 Tritt dem Minecraft-Server bei!")
    async def minecraft_command(interaction: discord.Interaction):
        """User command to request Minecraft server access."""
        
        # Check if user already has an account
        existing = await get_minecraft_account(db_helpers, interaction.user.id)
        
        if existing:
            embed = discord.Embed(
                title="🎮 Dein Minecraft-Account",
                description=f"Du bist bereits registriert als: **{existing['minecraft_username']}**",
                color=discord.Color.green()
            )
            
            if existing.get('whitelisted'):
                embed.add_field(
                    name="✅ Status",
                    value="Du bist auf der Whitelist!",
                    inline=True
                )
                
                # Show server status
                if minecraft_server.is_server_running():
                    status = minecraft_server.get_server_status()
                    embed.add_field(
                        name="🟢 Server Online",
                        value=f"Spieler: {status.get('player_count', 0)}/{config.get('modules', {}).get('minecraft', {}).get('max_players', 20)}",
                        inline=True
                    )
                else:
                    embed.add_field(
                        name="🔴 Server Offline",
                        value="Der Server ist momentan nicht aktiv.",
                        inline=True
                    )
            else:
                embed.add_field(
                    name="⏳ Status",
                    value="Warte auf Whitelist-Genehmigung",
                    inline=True
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check for pending request
        pending = await get_pending_join_request(db_helpers, interaction.user.id)
        
        if pending:
            embed = discord.Embed(
                title="⏳ Anfrage ausstehend",
                description=f"Du hast bereits eine Anfrage für **{pending['minecraft_username']}** gestellt.",
                color=discord.Color.orange()
            )
            embed.add_field(
                name="Status",
                value="Ein Admin wird deine Anfrage bald bearbeiten.",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Show join modal
        modal = MinecraftJoinModal(db_helpers)
        await interaction.response.send_modal(modal)
    
    # ==========================================================================
    # /mcstatus - Server status (everyone)
    # ==========================================================================
    
    @tree.command(name="mcstatus", description="📊 Zeige den Minecraft-Server Status")
    async def mcstatus_command(interaction: discord.Interaction):
        """Show Minecraft server status."""
        await interaction.response.defer(ephemeral=True)
        
        mc_config = config.get('modules', {}).get('minecraft', {})
        
        if not mc_config.get('enabled', True):
            await interaction.followup.send("❌ Der Minecraft-Server ist deaktiviert.", ephemeral=True)
            return
        
        status = minecraft_server.get_server_status()
        install_status = minecraft_server.get_installation_status()
        
        if status.get('running'):
            embed = discord.Embed(
                title="🟢 Minecraft Server Online",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="🔴 Minecraft Server Offline",
                color=discord.Color.red()
            )
        
        # Server info
        embed.add_field(
            name="🎮 Server",
            value=f"{install_status.get('server_type', 'Unknown')} {install_status.get('server_version', '')}",
            inline=True
        )
        
        embed.add_field(
            name="👥 Spieler",
            value=f"{status.get('player_count', 0)}/{mc_config.get('max_players', 20)}",
            inline=True
        )
        
        if status.get('uptime'):
            embed.add_field(
                name="⏱️ Uptime",
                value=status['uptime'],
                inline=True
            )
        
        # Online players
        players = status.get('players', [])
        if players:
            embed.add_field(
                name="🎮 Online",
                value=", ".join(players[:10]) + ("..." if len(players) > 10 else ""),
                inline=False
            )
        
        # Schedule info
        schedule = mc_config.get('schedule', {})
        mode = schedule.get('mode', 'always')
        schedule_text = {
            'always': '24/7',
            'timed': f"{schedule.get('start_hour', 6)}:00 - {schedule.get('end_hour', 22)}:00",
            'weekdays_only': 'Nur Werktags',
            'weekends_only': 'Nur Wochenende'
        }.get(mode, mode)
        
        embed.add_field(
            name="🕐 Zeitplan",
            value=schedule_text,
            inline=True
        )
        
        # Last backup
        last_backup = status.get('last_backup')
        if last_backup:
            embed.add_field(
                name="💾 Letztes Backup",
                value=last_backup.get('timestamp', 'Unbekannt'),
                inline=True
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    # ==========================================================================
    # /mcstart - Admin command to start server
    # ==========================================================================
    
    @tree.command(name="mcstart", description="🟢 [Admin] Starte den Minecraft-Server")
    @is_admin()
    async def mcstart_command(interaction: discord.Interaction):
        """Admin command to start the Minecraft server."""
        await interaction.response.defer(ephemeral=True)
        
        if minecraft_server.is_server_running():
            await interaction.followup.send("⚠️ Der Server läuft bereits!", ephemeral=True)
            return
        
        mc_config = config.get('modules', {}).get('minecraft', {})
        success, message = await minecraft_server.start_server(mc_config)
        
        if success:
            embed = discord.Embed(
                title="🟢 Server gestartet",
                description=message,
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="❌ Start fehlgeschlagen",
                description=message,
                color=discord.Color.red()
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    # ==========================================================================
    # /mcstop - Admin command to stop server
    # ==========================================================================
    
    @tree.command(name="mcstop", description="🔴 [Admin] Stoppe den Minecraft-Server")
    @app_commands.describe(
        warn_time="Warnzeit in Minuten vor dem Stoppen (Standard: 5)"
    )
    @is_admin()
    async def mcstop_command(interaction: discord.Interaction, warn_time: int = 5):
        """Admin command to stop the Minecraft server."""
        await interaction.response.defer(ephemeral=True)
        
        if not minecraft_server.is_server_running():
            await interaction.followup.send("⚠️ Der Server läuft nicht!", ephemeral=True)
            return
        
        # Send warning to players
        await minecraft_server.send_command(f"say §c[Server] §fServer wird in {warn_time} Minuten heruntergefahren!")
        
        embed = discord.Embed(
            title="⏳ Server-Stopp eingeleitet",
            description=f"Spieler werden gewarnt. Server stoppt in {warn_time} Minuten.",
            color=discord.Color.orange()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        # Wait and stop
        await asyncio.sleep(warn_time * 60)
        
        if minecraft_server.is_server_running():
            success, message = await minecraft_server.stop_server(notify_players=True)
            
            # Send result to admin
            try:
                if success:
                    await interaction.user.send(f"✅ Minecraft-Server gestoppt: {message}")
                else:
                    await interaction.user.send(f"❌ Server-Stopp fehlgeschlagen: {message}")
            except discord.Forbidden:
                pass
    
    # ==========================================================================
    # /mcrestart - Admin command to restart server
    # ==========================================================================
    
    @tree.command(name="mcrestart", description="🔄 [Admin] Starte den Minecraft-Server neu")
    @is_admin()
    async def mcrestart_command(interaction: discord.Interaction):
        """Admin command to restart the Minecraft server."""
        await interaction.response.defer(ephemeral=True)
        
        mc_config = config.get('modules', {}).get('minecraft', {})
        success, message = await minecraft_server.restart_server(mc_config, notify_players=True)
        
        if success:
            embed = discord.Embed(
                title="🔄 Server neugestartet",
                description=message,
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="❌ Neustart fehlgeschlagen",
                description=message,
                color=discord.Color.red()
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    # ==========================================================================
    # /mcwhitelist - Admin whitelist management
    # ==========================================================================
    
    mc_whitelist_group = app_commands.Group(name="mcwhitelist", description="[Admin] Minecraft Whitelist verwalten")
    
    @mc_whitelist_group.command(name="pending", description="Zeige ausstehende Beitrittsanfragen")
    @is_admin()
    async def whitelist_pending(interaction: discord.Interaction):
        """Show pending whitelist requests."""
        await interaction.response.defer(ephemeral=True)
        
        requests = await get_all_pending_requests(db_helpers)
        
        if not requests:
            await interaction.followup.send("✅ Keine ausstehenden Anfragen.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="📋 Ausstehende Whitelist-Anfragen",
            description=f"{len(requests)} Anfrage(n) warten auf Bearbeitung",
            color=discord.Color.blue()
        )
        
        for req in requests[:10]:  # Limit to 10
            try:
                user = await interaction.client.fetch_user(req['discord_user_id'])
                user_info = f"{user.name} ({user.mention})"
            except Exception:
                user_info = f"User ID: {req['discord_user_id']}"
            
            embed.add_field(
                name=f"🎮 {req['minecraft_username']}",
                value=f"Discord: {user_info}\nAngefragt: {req['requested_at']}",
                inline=False
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        # Send individual buttons for each request
        for req in requests[:5]:  # Limit buttons
            try:
                user = await interaction.client.fetch_user(req['discord_user_id'])
                user_name = user.name
            except Exception:
                user_name = f"User {req['discord_user_id']}"
            
            view = WhitelistRequestView(
                db_helpers, 
                minecraft_server, 
                req['id'], 
                req['minecraft_username'],
                req['discord_user_id']
            )
            
            await interaction.followup.send(
                f"**{req['minecraft_username']}** von {user_name}",
                view=view,
                ephemeral=True
            )
    
    @mc_whitelist_group.command(name="add", description="Füge einen Spieler direkt zur Whitelist hinzu")
    @app_commands.describe(
        minecraft_name="Minecraft-Username",
        discord_user="Discord-Nutzer (optional)"
    )
    @is_admin()
    async def whitelist_add(
        interaction: discord.Interaction, 
        minecraft_name: str,
        discord_user: Optional[discord.Member] = None
    ):
        """Directly add a player to whitelist."""
        await interaction.response.defer(ephemeral=True)
        
        success, message = await minecraft_server.add_to_whitelist(minecraft_name)
        
        if success:
            # If Discord user provided, link the account
            if discord_user:
                conn = db_helpers.get_db_connection()
                if conn:
                    cursor = conn.cursor()
                    try:
                        cursor.execute("""
                            INSERT INTO minecraft_players 
                            (discord_user_id, minecraft_username, whitelisted)
                            VALUES (%s, %s, TRUE)
                            ON DUPLICATE KEY UPDATE 
                            minecraft_username = VALUES(minecraft_username),
                            whitelisted = TRUE
                        """, (discord_user.id, minecraft_name))
                        conn.commit()
                    finally:
                        cursor.close()
                        conn.close()
            
            embed = discord.Embed(
                title="✅ Zur Whitelist hinzugefügt",
                description=f"**{minecraft_name}** wurde hinzugefügt.",
                color=discord.Color.green()
            )
            
            if discord_user:
                embed.add_field(name="Verknüpft mit", value=discord_user.mention)
                
                # Send notification to user
                try:
                    await discord_user.send(
                        embed=discord.Embed(
                            title="🎉 Minecraft Whitelist",
                            description=f"Du wurdest zum Minecraft-Server hinzugefügt!\nDein Account: **{minecraft_name}**",
                            color=discord.Color.green()
                        )
                    )
                    # Also send VPN tutorial
                    vpn_embed = get_vpn_tutorial_embed("10.0.0.1:25565")
                    await discord_user.send(embed=vpn_embed)
                except discord.Forbidden:
                    pass
        else:
            embed = discord.Embed(
                title="❌ Fehler",
                description=message,
                color=discord.Color.red()
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @mc_whitelist_group.command(name="remove", description="Entferne einen Spieler von der Whitelist")
    @app_commands.describe(minecraft_name="Minecraft-Username")
    @is_admin()
    async def whitelist_remove(interaction: discord.Interaction, minecraft_name: str):
        """Remove a player from whitelist."""
        await interaction.response.defer(ephemeral=True)
        
        success, message = await minecraft_server.remove_from_whitelist(minecraft_name)
        
        if success:
            embed = discord.Embed(
                title="✅ Von Whitelist entfernt",
                description=f"**{minecraft_name}** wurde entfernt.",
                color=discord.Color.orange()
            )
        else:
            embed = discord.Embed(
                title="❌ Fehler",
                description=message,
                color=discord.Color.red()
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    tree.add_command(mc_whitelist_group)
    
    # ==========================================================================
    # /vpn - Admin VPN management
    # ==========================================================================
    
    if wireguard_manager:
        vpn_group = app_commands.Group(name="vpn", description="[Admin] VPN-Verwaltung")
        
        @vpn_group.command(name="status", description="Zeige VPN-Status")
        @is_admin()
        async def vpn_status(interaction: discord.Interaction):
            """Show VPN status."""
            await interaction.response.defer(ephemeral=True)
            
            status = await wireguard_manager.get_interface_status()
            
            if status.get('active'):
                embed = discord.Embed(
                    title="🟢 VPN aktiv",
                    color=discord.Color.green()
                )
                
                embed.add_field(
                    name="Public Key",
                    value=f"`{status.get('public_key', 'N/A')[:20]}...`",
                    inline=False
                )
                
                embed.add_field(
                    name="Port",
                    value=str(status.get('listen_port', 51820)),
                    inline=True
                )
                
                peers = status.get('peers', [])
                embed.add_field(
                    name="Verbundene Clients",
                    value=str(len(peers)),
                    inline=True
                )
                
                # Show connected peers
                for peer in peers[:5]:
                    endpoint = peer.get('endpoint', 'Unbekannt')
                    handshake = peer.get('latest_handshake', 'Nie')
                    embed.add_field(
                        name=f"Client: {peer.get('public_key', '?')[:10]}...",
                        value=f"Endpoint: {endpoint}\nLetzter Handshake: {handshake}",
                        inline=False
                    )
            else:
                embed = discord.Embed(
                    title="🔴 VPN nicht aktiv",
                    description=status.get('error', 'Interface nicht gefunden'),
                    color=discord.Color.red()
                )
                
                if not wireguard_manager.is_wireguard_installed():
                    embed.add_field(
                        name="Installation",
                        value=wireguard_manager.get_installation_instructions(),
                        inline=False
                    )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        
        @vpn_group.command(name="tutorial", description="Zeige VPN-Verbindungsanleitung")
        @is_admin()
        async def vpn_tutorial(interaction: discord.Interaction):
            """Show VPN connection tutorial."""
            mc_config = config.get('modules', {}).get('minecraft', {})
            server_endpoint = f"10.0.0.1:{mc_config.get('port', 25565)}"
            
            embed = get_vpn_tutorial_embed(server_endpoint)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        @vpn_group.command(name="setup", description="VPN-Server einrichten")
        @app_commands.describe(
            endpoint="Öffentliche IP oder Domain des Servers"
        )
        @is_admin()
        async def vpn_setup(interaction: discord.Interaction, endpoint: str):
            """Set up VPN server."""
            await interaction.response.defer(ephemeral=True)
            
            result = await wireguard_manager.setup_wireguard_server(
                server_endpoint=endpoint,
                server_address="10.0.0.1/24",
                listen_port=51820
            )
            
            if result.get('success'):
                embed = discord.Embed(
                    title="✅ VPN-Server konfiguriert",
                    description="WireGuard-Server wurde eingerichtet!",
                    color=discord.Color.green()
                )
                
                embed.add_field(
                    name="Public Key",
                    value=f"`{result.get('public_key', 'N/A')}`",
                    inline=False
                )
                
                embed.add_field(
                    name="Endpoint",
                    value=result.get('endpoint', 'N/A'),
                    inline=True
                )
                
                embed.add_field(
                    name="Nächste Schritte",
                    value="1. Starte den VPN mit `/vpn start`\n2. Füge Clients hinzu mit `/vpn addclient`",
                    inline=False
                )
            else:
                embed = discord.Embed(
                    title="❌ Setup fehlgeschlagen",
                    description=result.get('error', 'Unbekannter Fehler'),
                    color=discord.Color.red()
                )
                
                if result.get('instructions'):
                    embed.add_field(
                        name="Installation",
                        value=result['instructions'],
                        inline=False
                    )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        
        @vpn_group.command(name="addclient", description="Neuen VPN-Client hinzufügen")
        @app_commands.describe(
            name="Name für den Client",
            user="Discord-Nutzer für den Client (optional)"
        )
        @is_admin()
        async def vpn_addclient(
            interaction: discord.Interaction, 
            name: str,
            user: Optional[discord.Member] = None
        ):
            """Add a new VPN client."""
            await interaction.response.defer(ephemeral=True)
            
            # Get server config
            import json
            config_path = 'config/wireguard/vpn_config.json'
            
            try:
                with open(config_path, 'r') as f:
                    vpn_config = json.load(f)
            except FileNotFoundError:
                await interaction.followup.send(
                    "❌ VPN nicht konfiguriert. Führe zuerst `/vpn setup` aus.",
                    ephemeral=True
                )
                return
            
            # Generate client number for IP assignment
            peers = vpn_config.get('peers', [])
            client_num = len(peers) + 2  # Start from .2 (server is .1)
            client_address = f"10.0.0.{client_num}/32"
            
            # Add client
            result = await wireguard_manager.add_client(
                client_name=name,
                client_address=client_address,
                server_public_key=vpn_config.get('public_key', ''),
                server_endpoint=vpn_config.get('endpoint', '')
            )
            
            if result.get('success'):
                embed = discord.Embed(
                    title="✅ Client hinzugefügt",
                    description=f"Client **{name}** wurde erstellt.",
                    color=discord.Color.green()
                )
                
                embed.add_field(
                    name="VPN-Adresse",
                    value=result.get('address', 'N/A'),
                    inline=True
                )
                
                # Save updated config
                peers.append({
                    'name': name,
                    'public_key': result.get('public_key'),
                    'address': client_address,
                    'discord_user_id': user.id if user else None
                })
                vpn_config['peers'] = peers
                
                with open(config_path, 'w') as f:
                    json.dump(vpn_config, f, indent=2)
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                
                # Send config to user if specified
                if user:
                    try:
                        config_content = result.get('config_content', '')
                        
                        # Send tutorial
                        tutorial_embed = get_vpn_tutorial_embed(vpn_config.get('endpoint', ''))
                        await user.send(embed=tutorial_embed)
                        
                        # Send config file
                        import io
                        config_file = io.StringIO(config_content)
                        await user.send(
                            "📄 Hier ist deine VPN-Konfigurationsdatei:",
                            file=discord.File(
                                io.BytesIO(config_content.encode()),
                                filename=f"sulfur_vpn_{name}.conf"
                            )
                        )
                        
                        await interaction.followup.send(
                            f"✅ Konfiguration wurde an {user.mention} gesendet.",
                            ephemeral=True
                        )
                    except discord.Forbidden:
                        await interaction.followup.send(
                            f"⚠️ Konnte Konfiguration nicht an {user.mention} senden (DMs geschlossen).",
                            ephemeral=True
                        )
            else:
                embed = discord.Embed(
                    title="❌ Fehler",
                    description=result.get('error', 'Unbekannter Fehler'),
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
        
        @vpn_group.command(name="start", description="VPN-Interface starten")
        @is_admin()
        async def vpn_start(interaction: discord.Interaction):
            """Start the VPN interface."""
            await interaction.response.defer(ephemeral=True)
            
            success, message = await wireguard_manager.start_interface()
            
            if success:
                embed = discord.Embed(
                    title="✅ VPN gestartet",
                    description=message,
                    color=discord.Color.green()
                )
            else:
                embed = discord.Embed(
                    title="❌ Start fehlgeschlagen",
                    description=message,
                    color=discord.Color.red()
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        
        @vpn_group.command(name="stop", description="VPN-Interface stoppen")
        @is_admin()
        async def vpn_stop(interaction: discord.Interaction):
            """Stop the VPN interface."""
            await interaction.response.defer(ephemeral=True)
            
            success, message = await wireguard_manager.stop_interface()
            
            if success:
                embed = discord.Embed(
                    title="✅ VPN gestoppt",
                    description=message,
                    color=discord.Color.orange()
                )
            else:
                embed = discord.Embed(
                    title="❌ Stopp fehlgeschlagen",
                    description=message,
                    color=discord.Color.red()
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        
        tree.add_command(vpn_group)
    
    logger.info("Minecraft and VPN commands registered")
