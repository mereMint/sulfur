"""
Sulfur Bot - Sport Betting Discord UI Components
User-friendly views, buttons, and modals for sport betting.
"""

import discord
from discord import ui
from discord.ui import View, Button, Select, Modal, TextInput
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime

from modules.sport_betting import (
    LEAGUES, FREE_LEAGUES, MatchStatus, BetOutcome,
    format_match_time, get_league_emoji, get_league_name,
    format_odds_display, get_outcome_emoji,
    create_match_embed, create_bet_embed, create_stats_embed,
    create_matches_list_embed, create_leaderboard_embed,
    get_upcoming_matches, get_match_from_db, place_bet,
    get_user_bets, get_user_betting_stats, get_betting_leaderboard,
    sync_league_matches
)


# ============================================================================
# LEAGUE SELECT DROPDOWN
# ============================================================================

class LeagueSelect(Select):
    """Dropdown to select a league."""
    
    def __init__(self, callback_func: Callable):
        options = []
        for league_id, config in LEAGUES.items():
            options.append(discord.SelectOption(
                label=config["name"],
                value=league_id,
                emoji=config["emoji"],
                description=f"{config['country']} - {config['provider'].replace('_', ' ').title()}"
            ))
        
        super().__init__(
            placeholder="🏟️ Liga auswählen...",
            options=options,
            min_values=1,
            max_values=1
        )
        self._callback_func = callback_func
    
    async def callback(self, interaction: discord.Interaction):
        await self._callback_func(interaction, self.values[0])


class LeagueSelectView(View):
    """View containing the league select dropdown."""
    
    def __init__(self, callback_func: Callable, timeout: float = 180.0):
        super().__init__(timeout=timeout)
        self.add_item(LeagueSelect(callback_func))


# ============================================================================
# MATCH LIST VIEW WITH PAGINATION
# ============================================================================

class MatchListView(View):
    """View for displaying matches with pagination and betting buttons."""
    
    def __init__(self, db_helpers, matches: List[Dict], league_id: Optional[str] = None,
                 page: int = 1, per_page: int = 5, timeout: float = 300.0):
        super().__init__(timeout=timeout)
        self.db_helpers = db_helpers
        self.matches = matches
        self.league_id = league_id
        self.page = page
        self.per_page = per_page
        self.total_pages = max(1, (len(matches) + per_page - 1) // per_page)
        
        self._update_buttons()
    
    def _get_page_matches(self) -> List[Dict]:
        """Get matches for the current page."""
        start = (self.page - 1) * self.per_page
        end = start + self.per_page
        return self.matches[start:end]
    
    def _update_buttons(self):
        """Update button states based on current page."""
        self.prev_button.disabled = self.page <= 1
        self.next_button.disabled = self.page >= self.total_pages
    
    def get_embed(self) -> discord.Embed:
        """Get the embed for the current page."""
        page_matches = self._get_page_matches()
        return create_matches_list_embed(page_matches, self.league_id, self.page, self.total_pages)
    
    @ui.button(label="◀️ Zurück", style=discord.ButtonStyle.secondary, custom_id="prev")
    async def prev_button(self, interaction: discord.Interaction, button: Button):
        if self.page > 1:
            self.page -= 1
            self._update_buttons()
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
        else:
            await interaction.response.defer()
    
    @ui.button(label="Weiter ▶️", style=discord.ButtonStyle.secondary, custom_id="next")
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if self.page < self.total_pages:
            self.page += 1
            self._update_buttons()
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
        else:
            await interaction.response.defer()
    
    @ui.button(label="🔄 Aktualisieren", style=discord.ButtonStyle.primary, custom_id="refresh")
    async def refresh_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        
        # Refresh match data
        if self.league_id:
            await sync_league_matches(self.db_helpers, self.league_id)
            self.matches = await get_upcoming_matches(self.db_helpers, self.league_id, limit=50)
        else:
            self.matches = await get_upcoming_matches(self.db_helpers, limit=50)
        
        self.total_pages = max(1, (len(self.matches) + self.per_page - 1) // self.per_page)
        self.page = min(self.page, self.total_pages)
        self._update_buttons()
        
        await interaction.followup.edit_message(
            message_id=interaction.message.id,
            embed=self.get_embed(),
            view=self
        )


# ============================================================================
# BET PLACEMENT VIEW
# ============================================================================

class BetModal(Modal):
    """Modal for entering bet amount."""
    
    def __init__(self, match: Dict, outcome: str, odds: float, db_helpers, balance_check_func, balance_deduct_func=None):
        super().__init__(title="🎫 Wette platzieren")
        self.match = match
        self.outcome = outcome
        self.odds = odds
        self.db_helpers = db_helpers
        self.balance_check_func = balance_check_func
        self.balance_deduct_func = balance_deduct_func
        
        outcome_names = {"home": "Heimsieg", "draw": "Unentschieden", "away": "Auswärtssieg"}
        
        self.amount_input = TextInput(
            label=f"Einsatz für {outcome_names.get(outcome, outcome)} ({odds:.2f}x)",
            placeholder="z.B. 100",
            min_length=1,
            max_length=10,
            required=True
        )
        self.add_item(self.amount_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = int(self.amount_input.value)
            if amount <= 0:
                await interaction.response.send_message(
                    "❌ Der Einsatz muss positiv sein!",
                    ephemeral=True
                )
                return
            
            # Check balance
            user_id = interaction.user.id
            balance = await self.balance_check_func(user_id)
            
            if balance < amount:
                await interaction.response.send_message(
                    f"❌ Nicht genug Geld! Du hast **{balance}** 🪙, brauchst aber **{amount}** 🪙.",
                    ephemeral=True
                )
                return
            
            # Place the bet
            match_id = self.match.get("match_id", self.match.get("id"))
            success, message = await place_bet(
                self.db_helpers,
                user_id,
                match_id,
                "winner",
                self.outcome,
                amount,
                self.odds
            )
            
            if success:
                # Deduct balance using the provided callback
                if self.balance_deduct_func:
                    await self.balance_deduct_func(user_id, interaction.user.display_name, -amount)
                
                # Create confirmation embed
                embed = discord.Embed(
                    title="✅ Wette platziert!",
                    color=discord.Color.green()
                )
                
                home_team = self.match.get("home_team", "Unknown")
                away_team = self.match.get("away_team", "Unknown")
                outcome_names = {"home": "Heimsieg", "draw": "Unentschieden", "away": "Auswärtssieg"}
                potential_payout = int(amount * self.odds)
                
                embed.add_field(name="⚽ Spiel", value=f"{home_team} vs {away_team}", inline=False)
                embed.add_field(name="🎯 Tipp", value=f"{get_outcome_emoji(self.outcome)} {outcome_names.get(self.outcome)}", inline=True)
                embed.add_field(name="💰 Einsatz", value=f"{amount} 🪙", inline=True)
                embed.add_field(name="📊 Quote", value=f"{self.odds:.2f}x", inline=True)
                embed.add_field(name="💎 Möglicher Gewinn", value=f"**{potential_payout}** 🪙", inline=True)
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ {message}", ephemeral=True)
                
        except ValueError:
            await interaction.response.send_message(
                "❌ Bitte gib eine gültige Zahl ein!",
                ephemeral=True
            )


class BetPlacementView(View):
    """View for placing a bet on a match."""
    
    def __init__(self, match: Dict, db_helpers, balance_check_func, balance_deduct_func=None, timeout: float = 300.0):
        super().__init__(timeout=timeout)
        self.match = match
        self.db_helpers = db_helpers
        self.balance_check_func = balance_check_func
        self.balance_deduct_func = balance_deduct_func
        
        # Get odds
        self.odds_home = float(match.get("odds_home", 2.0))
        self.odds_draw = float(match.get("odds_draw", 3.5))
        self.odds_away = float(match.get("odds_away", 3.0))
    
    @ui.button(label="🏠 Heimsieg", style=discord.ButtonStyle.primary, row=0)
    async def bet_home(self, interaction: discord.Interaction, button: Button):
        modal = BetModal(self.match, "home", self.odds_home, self.db_helpers, self.balance_check_func, self.balance_deduct_func)
        await interaction.response.send_modal(modal)
    
    @ui.button(label="🤝 Unentschieden", style=discord.ButtonStyle.secondary, row=0)
    async def bet_draw(self, interaction: discord.Interaction, button: Button):
        modal = BetModal(self.match, "draw", self.odds_draw, self.db_helpers, self.balance_check_func, self.balance_deduct_func)
        await interaction.response.send_modal(modal)
    
    @ui.button(label="✈️ Auswärtssieg", style=discord.ButtonStyle.primary, row=0)
    async def bet_away(self, interaction: discord.Interaction, button: Button):
        modal = BetModal(self.match, "away", self.odds_away, self.db_helpers, self.balance_check_func, self.balance_deduct_func)
        await interaction.response.send_modal(modal)
    
    @ui.button(label="❌ Abbrechen", style=discord.ButtonStyle.danger, row=1)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(
            content="Wette abgebrochen.",
            embed=None,
            view=None
        )


# ============================================================================
# USER BETS VIEW
# ============================================================================

class UserBetsView(View):
    """View for displaying user's bets with filtering."""
    
    def __init__(self, db_helpers, user_id: int, user_name: str, 
                 bets: List[Dict], filter_status: Optional[str] = None,
                 timeout: float = 300.0):
        super().__init__(timeout=timeout)
        self.db_helpers = db_helpers
        self.user_id = user_id
        self.user_name = user_name
        self.bets = bets
        self.filter_status = filter_status
        self.page = 1
        self.per_page = 5
        self.total_pages = max(1, (len(bets) + self.per_page - 1) // self.per_page)
        
        self._update_buttons()
    
    def _get_page_bets(self) -> List[Dict]:
        """Get bets for the current page."""
        start = (self.page - 1) * self.per_page
        end = start + self.per_page
        return self.bets[start:end]
    
    def _update_buttons(self):
        """Update button states."""
        self.prev_button.disabled = self.page <= 1
        self.next_button.disabled = self.page >= self.total_pages
    
    def get_embed(self) -> discord.Embed:
        """Create embed showing user's bets."""
        page_bets = self._get_page_bets()
        
        filter_text = ""
        if self.filter_status:
            filter_text = f" ({self.filter_status.title()})"
        
        embed = discord.Embed(
            title=f"🎫 Meine Wetten{filter_text}",
            color=discord.Color.blue()
        )
        
        if not page_bets:
            embed.description = "Keine Wetten gefunden."
            return embed
        
        for bet in page_bets:
            status = bet.get("status", "pending")
            status_emoji = get_outcome_emoji(status)
            
            home_team = bet.get("home_team", "Unknown")
            away_team = bet.get("away_team", "Unknown")
            outcome = bet.get("bet_outcome", "home")
            outcome_names = {"home": "Heim", "draw": "X", "away": "Auswärts"}
            
            amount = bet.get("bet_amount", 0)
            odds = bet.get("odds_at_bet", 1.0)
            
            if status == "pending":
                payout_text = f"Pot. Gewinn: {bet.get('potential_payout', 0)} 🪙"
            else:
                payout_text = f"Auszahlung: {bet.get('actual_payout', 0)} 🪙"
            
            field_value = (
                f"🎯 **{outcome_names.get(outcome, outcome)}** @ {odds:.2f}x\n"
                f"💰 Einsatz: {amount} 🪙 | {payout_text}"
            )
            
            # Add result if match is finished
            if bet.get("match_status") == "finished":
                field_value += f"\n🏁 Ergebnis: {bet.get('home_score', 0)} : {bet.get('away_score', 0)}"
            
            embed.add_field(
                name=f"{status_emoji} {home_team} vs {away_team}",
                value=field_value,
                inline=False
            )
        
        embed.set_footer(text=f"Seite {self.page}/{self.total_pages}")
        return embed
    
    @ui.button(label="◀️", style=discord.ButtonStyle.secondary, custom_id="prev")
    async def prev_button(self, interaction: discord.Interaction, button: Button):
        if self.page > 1:
            self.page -= 1
            self._update_buttons()
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
        else:
            await interaction.response.defer()
    
    @ui.button(label="▶️", style=discord.ButtonStyle.secondary, custom_id="next")
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if self.page < self.total_pages:
            self.page += 1
            self._update_buttons()
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
        else:
            await interaction.response.defer()
    
    @ui.button(label="Alle", style=discord.ButtonStyle.primary)
    async def filter_all(self, interaction: discord.Interaction, button: Button):
        self.bets = await get_user_bets(self.db_helpers, self.user_id, None)
        self.filter_status = None
        self.page = 1
        self.total_pages = max(1, (len(self.bets) + self.per_page - 1) // self.per_page)
        self._update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)
    
    @ui.button(label="⏳ Offen", style=discord.ButtonStyle.secondary)
    async def filter_pending(self, interaction: discord.Interaction, button: Button):
        self.bets = await get_user_bets(self.db_helpers, self.user_id, "pending")
        self.filter_status = "pending"
        self.page = 1
        self.total_pages = max(1, (len(self.bets) + self.per_page - 1) // self.per_page)
        self._update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)
    
    @ui.button(label="✅ Gewonnen", style=discord.ButtonStyle.success)
    async def filter_won(self, interaction: discord.Interaction, button: Button):
        self.bets = await get_user_bets(self.db_helpers, self.user_id, "won")
        self.filter_status = "won"
        self.page = 1
        self.total_pages = max(1, (len(self.bets) + self.per_page - 1) // self.per_page)
        self._update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)
    
    @ui.button(label="❌ Verloren", style=discord.ButtonStyle.danger)
    async def filter_lost(self, interaction: discord.Interaction, button: Button):
        self.bets = await get_user_bets(self.db_helpers, self.user_id, "lost")
        self.filter_status = "lost"
        self.page = 1
        self.total_pages = max(1, (len(self.bets) + self.per_page - 1) // self.per_page)
        self._update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)


# ============================================================================
# MAIN MENU VIEW
# ============================================================================

class SportBettingMainView(View):
    """Main menu view for sport betting."""
    
    def __init__(self, db_helpers, timeout: float = 300.0):
        super().__init__(timeout=timeout)
        self.db_helpers = db_helpers
    
    @ui.button(label="⚽ Spiele anzeigen", style=discord.ButtonStyle.primary, row=0)
    async def show_matches(self, interaction: discord.Interaction, button: Button):
        # Show league selection
        async def on_league_select(inter: discord.Interaction, league_id: str):
            await inter.response.defer()
            
            # Sync and get matches
            await sync_league_matches(self.db_helpers, league_id)
            matches = await get_upcoming_matches(self.db_helpers, league_id, limit=50)
            
            view = MatchListView(self.db_helpers, matches, league_id)
            await inter.followup.edit_message(
                message_id=inter.message.id,
                embed=view.get_embed(),
                view=view
            )
        
        view = LeagueSelectView(on_league_select)
        embed = discord.Embed(
            title="🏟️ Liga auswählen",
            description="Wähle eine Liga aus, um die kommenden Spiele zu sehen.",
            color=discord.Color.blue()
        )
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    @ui.button(label="🎫 Meine Wetten", style=discord.ButtonStyle.secondary, row=0)
    async def show_my_bets(self, interaction: discord.Interaction, button: Button):
        user_id = interaction.user.id
        bets = await get_user_bets(self.db_helpers, user_id)
        
        view = UserBetsView(self.db_helpers, user_id, interaction.user.display_name, bets)
        await interaction.response.edit_message(embed=view.get_embed(), view=view)
    
    @ui.button(label="📊 Statistiken", style=discord.ButtonStyle.secondary, row=0)
    async def show_stats(self, interaction: discord.Interaction, button: Button):
        user_id = interaction.user.id
        stats = await get_user_betting_stats(self.db_helpers, user_id)
        
        embed = create_stats_embed(stats, interaction.user.display_name)
        await interaction.response.edit_message(embed=embed, view=self)
    
    @ui.button(label="🏆 Bestenliste", style=discord.ButtonStyle.success, row=1)
    async def show_leaderboard(self, interaction: discord.Interaction, button: Button):
        leaderboard = await get_betting_leaderboard(self.db_helpers)
        embed = create_leaderboard_embed(leaderboard)
        await interaction.response.edit_message(embed=embed, view=self)
    
    @ui.button(label="🔄 Spiele aktualisieren", style=discord.ButtonStyle.primary, row=1)
    async def sync_matches(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        
        # Sync only free leagues (OpenLigaDB)
        synced_total = 0
        
        for league_id in FREE_LEAGUES:
            synced = await sync_league_matches(self.db_helpers, league_id)
            synced_total += synced
        
        embed = discord.Embed(
            title="✅ Spieldaten aktualisiert",
            description=f"**{synced_total}** Spiele synchronisiert.",
            color=discord.Color.green()
        )
        
        await interaction.followup.edit_message(
            message_id=interaction.message.id,
            embed=embed,
            view=self
        )


# ============================================================================
# QUICK BET SELECT VIEW
# ============================================================================

class QuickBetMatchSelect(Select):
    """Dropdown to select a match for quick betting."""
    
    def __init__(self, matches: List[Dict], db_helpers, balance_check_func, balance_deduct_func=None):
        self.matches_dict = {match.get("match_id", match.get("id")): match for match in matches}
        self.db_helpers = db_helpers
        self.balance_check_func = balance_check_func
        self.balance_deduct_func = balance_deduct_func
        
        options = []
        for match in matches[:25]:  # Discord limit is 25 options
            match_id = match.get("match_id", match.get("id"))
            home_team = match.get("home_team", "Unknown")
            away_team = match.get("away_team", "Unknown")
            match_time = match.get("match_time")
            
            if isinstance(match_time, str):
                try:
                    match_time = datetime.fromisoformat(match_time.replace("Z", "+00:00"))
                except ValueError:
                    match_time = None
            
            time_str = format_match_time(match_time) if match_time else "TBD"
            league_emoji = get_league_emoji(match.get("league_id", "bl1"))
            
            options.append(discord.SelectOption(
                label=f"{home_team[:20]} vs {away_team[:20]}"[:100],
                value=str(match_id),
                description=f"{time_str}",
                emoji=league_emoji
            ))
        
        super().__init__(
            placeholder="⚽ Spiel auswählen...",
            options=options if options else [discord.SelectOption(label="Keine Spiele", value="none")],
            min_values=1,
            max_values=1
        )
    
    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("Keine Spiele verfügbar!", ephemeral=True)
            return
        
        match = self.matches_dict.get(self.values[0])
        if not match:
            await interaction.response.send_message("Spiel nicht gefunden!", ephemeral=True)
            return
        
        embed = create_match_embed(match, show_odds=True)
        view = BetPlacementView(match, self.db_helpers, self.balance_check_func, self.balance_deduct_func)
        
        await interaction.response.edit_message(embed=embed, view=view)


class QuickBetView(View):
    """View for quick betting with match selection."""
    
    def __init__(self, matches: List[Dict], db_helpers, balance_check_func, balance_deduct_func=None, timeout: float = 300.0):
        super().__init__(timeout=timeout)
        self.balance_deduct_func = balance_deduct_func
        if matches:
            self.add_item(QuickBetMatchSelect(matches, db_helpers, balance_check_func, balance_deduct_func))


# ============================================================================
# HELP VIEW
# ============================================================================

def create_help_embed() -> discord.Embed:
    """Create help embed for sport betting."""
    embed = discord.Embed(
        title="⚽ Sport Betting - Hilfe",
        description="Wette auf Fußballspiele und gewinne Coins!",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="📋 Befehle",
        value=(
            "**/football** - Hauptmenü öffnen\n"
            "**/football matches [liga]** - Spiele anzeigen\n"
            "**/football bet <match_id>** - Auf ein Spiel wetten\n"
            "**/football mybets** - Meine Wetten anzeigen\n"
            "**/football stats** - Wettstatistiken\n"
            "**/football leaderboard** - Bestenliste\n"
            "**/football sync** - Spieldaten aktualisieren"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🎯 Wettarten",
        value=(
            "🏠 **Heimsieg (1)** - Das Heimteam gewinnt\n"
            "🤝 **Unentschieden (X)** - Das Spiel endet unentschieden\n"
            "✈️ **Auswärtssieg (2)** - Das Auswärtsteam gewinnt"
        ),
        inline=False
    )
    
    embed.add_field(
        name="📊 Quoten",
        value=(
            "Die Quoten zeigen deinen möglichen Gewinn.\n"
            "**Beispiel:** Quote 2.50x bei 100 🪙 Einsatz = 250 🪙 Gewinn"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🏆 Verfügbare Ligen",
        value=(
            "🇩🇪 **Bundesliga** (OpenLigaDB - Kostenlos)\n"
            "🇩🇪 **2. Bundesliga** (OpenLigaDB - Kostenlos)\n"
            "🏆 **DFB-Pokal** (OpenLigaDB - Kostenlos)\n"
            "🏆 **Champions League** (API-Key erforderlich)\n"
            "🏴󠁧󠁢󠁥󠁮󠁧󠁿 **Premier League** (API-Key erforderlich)\n"
            "🏆 **FIFA World Cup** (API-Key erforderlich)"
        ),
        inline=False
    )
    
    return embed
