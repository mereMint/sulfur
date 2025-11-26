"""
Sulfur Bot - Sport Betting Discord UI Components (v2)
Improved user-friendly UI with win probabilities and consolidated betting flow.

Flow: Main Menu (highlighted games) → League Select → Match Details (with probabilities) → Bet Type → Place Bet
"""

import discord
from discord import ui
from discord.ui import View, Button, Select, Modal, TextInput
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime, timedelta

from modules.sport_betting import (
    LEAGUES, MatchStatus, BetOutcome, BetType,
    format_match_time, get_league_emoji, get_league_name,
    format_odds_display, get_outcome_emoji,
    get_upcoming_matches, get_match_from_db, place_bet,
    get_user_bets, get_user_betting_stats, get_betting_leaderboard,
    sync_league_matches, OddsCalculator
)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def odds_to_probability(odds: float) -> float:
    """Convert betting odds to implied probability percentage."""
    if odds <= 0:
        return 0.0
    return round((1 / odds) * 100, 1)


def create_probability_bar(probability: float, width: int = 10) -> str:
    """Create a visual probability bar."""
    filled = int((probability / 100) * width)
    empty = width - filled
    return "█" * filled + "░" * empty


def format_match_time_detailed(match_time) -> str:
    """Format match time with date and time."""
    if match_time is None:
        return "TBD"
    
    if isinstance(match_time, str):
        try:
            match_time = datetime.fromisoformat(match_time.replace("Z", "+00:00"))
        except ValueError:
            return match_time
    
    now = datetime.now()
    if match_time.tzinfo:
        now = datetime.now(match_time.tzinfo)
    
    delta = match_time - now
    
    if delta.days == 0:
        return f"🔴 Heute {match_time.strftime('%H:%M')}"
    elif delta.days == 1:
        return f"📅 Morgen {match_time.strftime('%H:%M')}"
    elif delta.days < 7:
        weekdays = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
        return f"📆 {weekdays[match_time.weekday()]} {match_time.strftime('%H:%M')}"
    else:
        return f"📅 {match_time.strftime('%d.%m. %H:%M')}"


def create_match_detail_embed(match: Dict, show_probabilities: bool = True) -> discord.Embed:
    """Create a detailed embed for a single match with win probabilities."""
    home_team = match.get("home_team", "Unknown")
    away_team = match.get("away_team", "Unknown")
    league_id = match.get("league_id", "bl1")
    match_time = match.get("match_time")
    matchday = match.get("matchday", "?")
    
    # Get odds
    odds_home = float(match.get("odds_home", 2.0))
    odds_draw = float(match.get("odds_draw", 3.5))
    odds_away = float(match.get("odds_away", 3.0))
    
    # Calculate probabilities
    prob_home = odds_to_probability(odds_home)
    prob_draw = odds_to_probability(odds_draw)
    prob_away = odds_to_probability(odds_away)
    
    # Normalize probabilities to 100%
    total_prob = prob_home + prob_draw + prob_away
    if total_prob > 0:
        prob_home = round((prob_home / total_prob) * 100, 1)
        prob_draw = round((prob_draw / total_prob) * 100, 1)
        prob_away = round((prob_away / total_prob) * 100, 1)
    
    embed = discord.Embed(
        title=f"⚽ {home_team} vs {away_team}",
        color=discord.Color.blue()
    )
    
    # League and time info
    league_name = get_league_name(league_id)
    league_emoji = get_league_emoji(league_id)
    time_str = format_match_time_detailed(match_time)
    
    embed.description = f"{league_emoji} **{league_name}** • Spieltag {matchday}\n{time_str}"
    
    if show_probabilities:
        # Win probabilities section
        embed.add_field(
            name="📊 Siegwahrscheinlichkeiten",
            value=(
                f"🏠 **{home_team}**\n"
                f"{create_probability_bar(prob_home)} {prob_home}%\n\n"
                f"🤝 **Unentschieden**\n"
                f"{create_probability_bar(prob_draw)} {prob_draw}%\n\n"
                f"✈️ **{away_team}**\n"
                f"{create_probability_bar(prob_away)} {prob_away}%"
            ),
            inline=False
        )
        
        # Odds section
        embed.add_field(
            name="💰 Quoten",
            value=(
                f"🏠 Heimsieg: **{odds_home:.2f}x**\n"
                f"🤝 Remis: **{odds_draw:.2f}x**\n"
                f"✈️ Auswärtssieg: **{odds_away:.2f}x**"
            ),
            inline=True
        )
        
        # Example payout
        embed.add_field(
            name="💎 Beispiel (100 🪙)",
            value=(
                f"🏠 → **{int(100 * odds_home)}** 🪙\n"
                f"🤝 → **{int(100 * odds_draw)}** 🪙\n"
                f"✈️ → **{int(100 * odds_away)}** 🪙"
            ),
            inline=True
        )
    
    match_id = match.get("match_id", match.get("id", "unknown"))
    embed.set_footer(text=f"Match ID: {match_id}")
    
    return embed


def create_highlighted_matches_embed(matches: List[Dict], user_balance: int = 0) -> discord.Embed:
    """Create an embed showing highlighted upcoming matches."""
    embed = discord.Embed(
        title="⚽ Sport Betting",
        description=(
            "**Willkommen bei Sport Betting!**\n"
            "Wette auf echte Fußballspiele und gewinne Coins!\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**🔥 Kommende Top-Spiele:**"
        ),
        color=discord.Color.green()
    )
    
    # Add user balance
    embed.add_field(name="💰 Dein Guthaben", value=f"**{user_balance}** 🪙", inline=True)
    
    # Show up to 5 highlighted matches
    if matches:
        match_list = []
        for i, match in enumerate(matches[:5]):
            home_team = match.get("home_team", "Unknown")[:15]
            away_team = match.get("away_team", "Unknown")[:15]
            league_emoji = get_league_emoji(match.get("league_id", "bl1"))
            match_time = match.get("match_time")
            time_str = format_match_time_detailed(match_time)
            
            # Calculate favorite (lowest odds = highest probability) - consider draw too
            odds_home = float(match.get("odds_home", 2.0))
            odds_draw = float(match.get("odds_draw", 3.5))
            odds_away = float(match.get("odds_away", 3.0))
            
            if odds_home < odds_away and odds_home < odds_draw:
                favorite = f"⭐ {home_team}"
            elif odds_away < odds_home and odds_away < odds_draw:
                favorite = f"⭐ {away_team}"
            elif odds_draw <= odds_home and odds_draw <= odds_away:
                favorite = "🤝 Remis erwartet"
            else:
                favorite = "⚖️ Ausgeglichen"
            
            match_list.append(
                f"{league_emoji} **{home_team}** vs **{away_team}**\n"
                f"   └ {time_str} • {favorite}"
            )
        
        embed.add_field(
            name="📋 Nächste Spiele",
            value="\n\n".join(match_list) if match_list else "Keine Spiele gefunden",
            inline=False
        )
    else:
        embed.add_field(
            name="📋 Nächste Spiele",
            value="*Keine Spiele gefunden. Nutze 'Spiele aktualisieren' um Daten zu laden.*",
            inline=False
        )
    
    embed.set_footer(text="Wähle 'Liga wählen' um auf Spiele zu wetten!")
    
    return embed


# ============================================================================
# BET TYPE SELECTION VIEW
# ============================================================================

class BetTypeModal(Modal):
    """Modal for entering bet amount after selecting bet type."""
    
    def __init__(self, match: Dict, bet_type: str, outcome: str, odds: float, 
                 db_helpers, balance_check_func, balance_deduct_func=None):
        outcome_labels = {
            "home": "Heimsieg",
            "draw": "Unentschieden", 
            "away": "Auswärtssieg",
            "over_2.5": "Über 2.5 Tore",
            "under_2.5": "Unter 2.5 Tore",
            "btts_yes": "Beide Teams treffen",
            "btts_no": "Nicht beide treffen"
        }
        label = outcome_labels.get(outcome, outcome)
        
        super().__init__(title=f"🎫 Wette: {label}")
        self.match = match
        self.bet_type = bet_type
        self.outcome = outcome
        self.odds = odds
        self.db_helpers = db_helpers
        self.balance_check_func = balance_check_func
        self.balance_deduct_func = balance_deduct_func
        
        prob = odds_to_probability(odds)
        
        self.amount_input = TextInput(
            label=f"Einsatz ({odds:.2f}x • {prob}% Chance)",
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
                self.bet_type,
                self.outcome,
                amount,
                self.odds
            )
            
            if success:
                if self.balance_deduct_func:
                    await self.balance_deduct_func(user_id, interaction.user.display_name, -amount)
                
                home_team = self.match.get("home_team", "Unknown")
                away_team = self.match.get("away_team", "Unknown")
                potential_payout = int(amount * self.odds)
                prob = odds_to_probability(self.odds)
                
                outcome_labels = {
                    "home": f"🏠 {home_team} gewinnt",
                    "draw": "🤝 Unentschieden",
                    "away": f"✈️ {away_team} gewinnt",
                    "over_2.5": "⬆️ Über 2.5 Tore",
                    "under_2.5": "⬇️ Unter 2.5 Tore",
                    "btts_yes": "✅ Beide Teams treffen",
                    "btts_no": "❌ Nicht beide treffen"
                }
                
                embed = discord.Embed(
                    title="✅ Wette platziert!",
                    color=discord.Color.green()
                )
                
                embed.add_field(
                    name="⚽ Spiel",
                    value=f"**{home_team}** vs **{away_team}**",
                    inline=False
                )
                embed.add_field(
                    name="🎯 Dein Tipp",
                    value=outcome_labels.get(self.outcome, self.outcome),
                    inline=True
                )
                embed.add_field(
                    name="📊 Quote",
                    value=f"**{self.odds:.2f}x** ({prob}%)",
                    inline=True
                )
                embed.add_field(
                    name="💰 Einsatz",
                    value=f"**{amount}** 🪙",
                    inline=True
                )
                embed.add_field(
                    name="💎 Möglicher Gewinn",
                    value=f"**{potential_payout}** 🪙",
                    inline=True
                )
                
                new_balance = balance - amount
                embed.set_footer(text=f"Neues Guthaben: {new_balance} 🪙")
                
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message(f"❌ {message}", ephemeral=True)
                
        except ValueError:
            await interaction.response.send_message(
                "❌ Bitte gib eine gültige Zahl ein!",
                ephemeral=True
            )


class BetTypeSelectView(View):
    """View for selecting bet type on a match with detailed info."""
    
    def __init__(self, match: Dict, db_helpers, balance_check_func, 
                 balance_deduct_func=None, timeout: float = 300.0):
        super().__init__(timeout=timeout)
        self.match = match
        self.db_helpers = db_helpers
        self.balance_check_func = balance_check_func
        self.balance_deduct_func = balance_deduct_func
        
        # Get odds
        self.odds_home = float(match.get("odds_home", 2.0))
        self.odds_draw = float(match.get("odds_draw", 3.5))
        self.odds_away = float(match.get("odds_away", 3.0))
        
        # Calculate probabilities
        prob_home = odds_to_probability(self.odds_home)
        prob_draw = odds_to_probability(self.odds_draw)
        prob_away = odds_to_probability(self.odds_away)
        
        # Normalize
        total = prob_home + prob_draw + prob_away
        if total > 0:
            prob_home = round((prob_home / total) * 100)
            prob_draw = round((prob_draw / total) * 100)
            prob_away = round((prob_away / total) * 100)
        
        home_team = match.get("home_team", "Heim")[:12]
        away_team = match.get("away_team", "Auswärts")[:12]
        
        # Update button labels with probabilities
        self.bet_home.label = f"🏠 {home_team} ({prob_home}%)"
        self.bet_draw.label = f"🤝 Remis ({prob_draw}%)"
        self.bet_away.label = f"✈️ {away_team} ({prob_away}%)"
    
    @ui.button(label="🏠 Heimsieg", style=discord.ButtonStyle.primary, row=0)
    async def bet_home(self, interaction: discord.Interaction, button: Button):
        modal = BetTypeModal(
            self.match, "winner", "home", self.odds_home,
            self.db_helpers, self.balance_check_func, self.balance_deduct_func
        )
        await interaction.response.send_modal(modal)
    
    @ui.button(label="🤝 Remis", style=discord.ButtonStyle.secondary, row=0)
    async def bet_draw(self, interaction: discord.Interaction, button: Button):
        modal = BetTypeModal(
            self.match, "winner", "draw", self.odds_draw,
            self.db_helpers, self.balance_check_func, self.balance_deduct_func
        )
        await interaction.response.send_modal(modal)
    
    @ui.button(label="✈️ Auswärtssieg", style=discord.ButtonStyle.primary, row=0)
    async def bet_away(self, interaction: discord.Interaction, button: Button):
        modal = BetTypeModal(
            self.match, "winner", "away", self.odds_away,
            self.db_helpers, self.balance_check_func, self.balance_deduct_func
        )
        await interaction.response.send_modal(modal)
    
    @ui.button(label="⬅️ Zurück", style=discord.ButtonStyle.danger, row=1)
    async def go_back(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(
            content="Wähle ein anderes Spiel oder kehre zum Hauptmenü zurück.",
            embed=None,
            view=None
        )


# ============================================================================
# MATCH SELECT VIEW
# ============================================================================

class MatchSelectDropdown(Select):
    """Dropdown to select a match from a league."""
    
    def __init__(self, matches: List[Dict], db_helpers, balance_check_func, balance_deduct_func=None):
        self.matches_dict = {}
        self.db_helpers = db_helpers
        self.balance_check_func = balance_check_func
        self.balance_deduct_func = balance_deduct_func
        
        options = []
        for match in matches[:25]:
            match_id = str(match.get("match_id", match.get("id")))
            self.matches_dict[match_id] = match
            
            home_team = match.get("home_team", "Unknown")[:18]
            away_team = match.get("away_team", "Unknown")[:18]
            match_time = match.get("match_time")
            
            time_str = format_match_time_detailed(match_time)
            
            # Show probability of favorite (considering draw as well)
            odds_home = float(match.get("odds_home", 2.0))
            odds_draw = float(match.get("odds_draw", 3.5))
            odds_away = float(match.get("odds_away", 3.0))
            prob_home = odds_to_probability(odds_home)
            prob_draw = odds_to_probability(odds_draw)
            prob_away = odds_to_probability(odds_away)
            
            # Determine favorite (highest probability)
            if prob_home > prob_away and prob_home > prob_draw:
                fav_text = f"⭐{home_team} {prob_home:.0f}%"
            elif prob_away > prob_home and prob_away > prob_draw:
                fav_text = f"⭐{away_team} {prob_away:.0f}%"
            elif prob_draw >= prob_home and prob_draw >= prob_away:
                fav_text = f"🤝 Remis {prob_draw:.0f}%"
            else:
                fav_text = "⚖️ Ausgeglichen"
            
            options.append(discord.SelectOption(
                label=f"{home_team} vs {away_team}"[:100],
                value=match_id,
                description=f"{time_str[:50]} • {fav_text[:40]}"[:100],
                emoji="⚽"
            ))
        
        if not options:
            options = [discord.SelectOption(label="Keine Spiele", value="none")]
        
        super().__init__(
            placeholder="⚽ Spiel auswählen...",
            options=options,
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
        
        embed = create_match_detail_embed(match, show_probabilities=True)
        view = BetTypeSelectView(
            match, self.db_helpers, self.balance_check_func, self.balance_deduct_func
        )
        
        await interaction.response.edit_message(embed=embed, view=view)


class MatchSelectView(View):
    """View with match selection dropdown."""
    
    def __init__(self, matches: List[Dict], db_helpers, balance_check_func, 
                 balance_deduct_func=None, league_id: str = None, timeout: float = 300.0):
        super().__init__(timeout=timeout)
        self.league_id = league_id
        self.db_helpers = db_helpers
        
        if matches:
            self.add_item(MatchSelectDropdown(matches, db_helpers, balance_check_func, balance_deduct_func))
    
    def get_embed(self) -> discord.Embed:
        league_name = get_league_name(self.league_id) if self.league_id else "Alle Ligen"
        league_emoji = get_league_emoji(self.league_id) if self.league_id else "⚽"
        
        embed = discord.Embed(
            title=f"{league_emoji} {league_name} - Spiele",
            description=(
                "Wähle ein Spiel aus dem Dropdown, um Details zu sehen und zu wetten.\n\n"
                "**Tipp:** Die Prozentangabe zeigt die Siegchance des Favoriten."
            ),
            color=discord.Color.blue()
        )
        
        return embed


# ============================================================================
# LEAGUE SELECT VIEW
# ============================================================================

class LeagueSelectDropdown(Select):
    """Dropdown to select a league."""
    
    def __init__(self, on_select_callback: Callable):
        self.on_select_callback = on_select_callback
        
        options = []
        for league_id, config in LEAGUES.items():
            options.append(discord.SelectOption(
                label=config["name"],
                value=league_id,
                emoji=config["emoji"],
                description=f"{config['country']} • {config['provider'].replace('_', ' ').title()}"
            ))
        
        super().__init__(
            placeholder="🏟️ Liga auswählen...",
            options=options,
            min_values=1,
            max_values=1
        )
    
    async def callback(self, interaction: discord.Interaction):
        await self.on_select_callback(interaction, self.values[0])


class LeagueSelectView(View):
    """View for selecting a league."""
    
    def __init__(self, on_select_callback: Callable, timeout: float = 180.0):
        super().__init__(timeout=timeout)
        self.add_item(LeagueSelectDropdown(on_select_callback))
    
    def get_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🏟️ Liga auswählen",
            description=(
                "Wähle eine Liga aus, um die kommenden Spiele zu sehen.\n\n"
                "**Kostenlose Ligen (OpenLigaDB):**\n"
                "🇩🇪 Bundesliga, 2. Bundesliga, DFB-Pokal\n\n"
                "**Premium Ligen (API-Key erforderlich):**\n"
                "🏆 Champions League, Premier League, World Cup"
            ),
            color=discord.Color.blue()
        )
        return embed


# ============================================================================
# USER BETS VIEW
# ============================================================================

class UserBetsView(View):
    """View for displaying user's bets with filtering."""
    
    def __init__(self, db_helpers, user_id: int, user_name: str, 
                 bets: List[Dict], filter_status: Optional[str] = None,
                 page: int = 1, per_page: int = 5, timeout: float = 300.0):
        super().__init__(timeout=timeout)
        self.db_helpers = db_helpers
        self.user_id = user_id
        self.user_name = user_name
        self.bets = bets
        self.filter_status = filter_status
        self.page = page
        self.per_page = per_page
        self.total_pages = max(1, (len(bets) + per_page - 1) // per_page)
        
        self._update_buttons()
    
    def _update_buttons(self):
        self.prev_button.disabled = self.page <= 1
        self.next_button.disabled = self.page >= self.total_pages
    
    def get_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"🎫 Wetten von {self.user_name}",
            color=discord.Color.purple()
        )
        
        if not self.bets:
            embed.description = "Du hast noch keine Wetten platziert."
            return embed
        
        start = (self.page - 1) * self.per_page
        end = start + self.per_page
        page_bets = self.bets[start:end]
        
        for bet in page_bets:
            status_emoji = {"pending": "⏳", "won": "✅", "lost": "❌"}.get(bet.get("status"), "❓")
            outcome_emoji = get_outcome_emoji(bet.get("bet_outcome", ""))
            
            match_info = f"{bet.get('home_team', '?')} vs {bet.get('away_team', '?')}"
            bet_info = (
                f"{outcome_emoji} {bet.get('bet_outcome', '?').title()}\n"
                f"💰 {bet.get('bet_amount', 0)} 🪙 @ {bet.get('odds_at_bet', 0):.2f}x\n"
                f"💎 Möglicher Gewinn: {bet.get('potential_payout', 0)} 🪙"
            )
            
            embed.add_field(
                name=f"{status_emoji} {match_info}"[:256],
                value=bet_info,
                inline=False
            )
        
        filter_text = f" ({self.filter_status})" if self.filter_status else " (Alle)"
        embed.set_footer(text=f"Seite {self.page}/{self.total_pages}{filter_text}")
        
        return embed
    
    @ui.button(label="◀️", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: Button):
        if self.page > 1:
            self.page -= 1
            self._update_buttons()
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
    
    @ui.button(label="▶️", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if self.page < self.total_pages:
            self.page += 1
            self._update_buttons()
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
    
    @ui.button(label="⏳ Ausstehend", style=discord.ButtonStyle.primary, row=1)
    async def filter_pending(self, interaction: discord.Interaction, button: Button):
        self.bets = await get_user_bets(self.db_helpers, self.user_id, "pending")
        self.filter_status = "pending"
        self.page = 1
        self.total_pages = max(1, (len(self.bets) + self.per_page - 1) // self.per_page)
        self._update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)
    
    @ui.button(label="✅ Gewonnen", style=discord.ButtonStyle.success, row=1)
    async def filter_won(self, interaction: discord.Interaction, button: Button):
        self.bets = await get_user_bets(self.db_helpers, self.user_id, "won")
        self.filter_status = "won"
        self.page = 1
        self.total_pages = max(1, (len(self.bets) + self.per_page - 1) // self.per_page)
        self._update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)
    
    @ui.button(label="❌ Verloren", style=discord.ButtonStyle.danger, row=1)
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

class SportBetsMainView(View):
    """Main menu view for sport betting with highlighted games."""
    
    def __init__(self, db_helpers, balance_check_func, balance_deduct_func=None, timeout: float = 300.0):
        super().__init__(timeout=timeout)
        self.db_helpers = db_helpers
        self.balance_check_func = balance_check_func
        self.balance_deduct_func = balance_deduct_func
    
    @ui.button(label="🏟️ Liga wählen", style=discord.ButtonStyle.primary, row=0)
    async def select_league(self, interaction: discord.Interaction, button: Button):
        async def on_league_select(inter: discord.Interaction, league_id: str):
            await inter.response.defer()
            
            # Sync and get matches
            await sync_league_matches(self.db_helpers, league_id)
            matches = await get_upcoming_matches(self.db_helpers, league_id, limit=25)
            
            if not matches:
                await inter.followup.edit_message(
                    message_id=inter.message.id,
                    content=f"❌ Keine Spiele in {get_league_name(league_id)} gefunden.",
                    embed=None,
                    view=self
                )
                return
            
            view = MatchSelectView(
                matches, self.db_helpers, self.balance_check_func, 
                self.balance_deduct_func, league_id
            )
            await inter.followup.edit_message(
                message_id=inter.message.id,
                embed=view.get_embed(),
                view=view
            )
        
        view = LeagueSelectView(on_league_select)
        await interaction.response.edit_message(embed=view.get_embed(), view=view)
    
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
    
    @ui.button(label="🔄 Aktualisieren", style=discord.ButtonStyle.primary, row=1)
    async def sync_matches(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        
        # Sync free leagues
        free_leagues = ["bl1", "bl2", "dfb"]
        synced_total = 0
        
        for league_id in free_leagues:
            synced = await sync_league_matches(self.db_helpers, league_id)
            synced_total += synced
        
        # Get fresh highlighted matches
        matches = await get_upcoming_matches(self.db_helpers, None, limit=5)
        balance = await self.balance_check_func(interaction.user.id)
        
        embed = create_highlighted_matches_embed(matches, balance)
        embed.add_field(
            name="✅ Aktualisiert",
            value=f"**{synced_total}** Spiele synchronisiert.",
            inline=False
        )
        
        await interaction.followup.edit_message(
            message_id=interaction.message.id,
            embed=embed,
            view=self
        )
    
    @ui.button(label="❓ Hilfe", style=discord.ButtonStyle.secondary, row=1)
    async def show_help(self, interaction: discord.Interaction, button: Button):
        embed = create_help_embed()
        await interaction.response.edit_message(embed=embed, view=self)


# ============================================================================
# HELPER EMBEDS
# ============================================================================

def create_stats_embed(stats: Optional[Dict], user_name: str) -> discord.Embed:
    """Create stats embed for user betting statistics."""
    embed = discord.Embed(
        title=f"📊 Wettstatistiken - {user_name}",
        color=discord.Color.gold()
    )
    
    if not stats:
        embed.description = "Noch keine Statistiken vorhanden."
        return embed
    
    total_bets = stats.get("total_bets", 0)
    total_wins = stats.get("total_wins", 0)
    total_losses = stats.get("total_losses", 0)
    total_wagered = stats.get("total_wagered", 0)
    total_won = stats.get("total_won", 0)
    total_lost = stats.get("total_lost", 0)
    biggest_win = stats.get("biggest_win", 0)
    current_streak = stats.get("current_streak", 0)
    best_streak = stats.get("best_streak", 0)
    
    win_rate = (total_wins / total_bets * 100) if total_bets > 0 else 0
    profit = total_won - total_lost
    
    embed.add_field(
        name="🎯 Wetten",
        value=f"Gesamt: **{total_bets}**\n✅ Gewonnen: **{total_wins}**\n❌ Verloren: **{total_losses}**",
        inline=True
    )
    
    embed.add_field(
        name="📈 Bilanz",
        value=f"Eingesetzt: **{total_wagered}** 🪙\nGewonnen: **{total_won}** 🪙\nProfit: **{profit:+d}** 🪙",
        inline=True
    )
    
    embed.add_field(
        name="🏆 Rekorde",
        value=f"Gewinnrate: **{win_rate:.1f}%**\nGrößter Gewinn: **{biggest_win}** 🪙\nBeste Serie: **{best_streak}** 🔥",
        inline=True
    )
    
    if current_streak > 0:
        embed.set_footer(text=f"🔥 Aktuelle Siegesserie: {current_streak}")
    
    return embed


def create_leaderboard_embed(leaderboard: List[Dict]) -> discord.Embed:
    """Create leaderboard embed."""
    embed = discord.Embed(
        title="🏆 Sport Betting - Bestenliste",
        description="Die besten Wetter nach Gewinn",
        color=discord.Color.gold()
    )
    
    if not leaderboard:
        embed.add_field(name="📋", value="Noch keine Daten vorhanden.", inline=False)
        return embed
    
    medals = ["🥇", "🥈", "🥉"]
    
    for i, entry in enumerate(leaderboard[:10]):
        medal = medals[i] if i < 3 else f"**{i+1}.**"
        name = entry.get("display_name", f"User {entry.get('user_id', '?')}")
        profit = entry.get("total_won", 0) - entry.get("total_lost", 0)
        wins = entry.get("total_wins", 0)
        
        embed.add_field(
            name=f"{medal} {name}",
            value=f"💰 {profit:+d} 🪙 • {wins} Siege",
            inline=False
        )
    
    return embed


def create_help_embed() -> discord.Embed:
    """Create help embed for sport betting."""
    embed = discord.Embed(
        title="❓ Sport Betting - Hilfe",
        description="So funktioniert das Wetten auf Fußballspiele!",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="📋 Ablauf",
        value=(
            "1️⃣ Wähle eine Liga aus\n"
            "2️⃣ Wähle ein Spiel aus der Liste\n"
            "3️⃣ Sieh dir die Siegchancen an\n"
            "4️⃣ Wähle deinen Tipp (Heim/Remis/Auswärts)\n"
            "5️⃣ Gib deinen Einsatz ein\n"
            "6️⃣ Warte auf das Spielergebnis!"
        ),
        inline=False
    )
    
    embed.add_field(
        name="📊 Quoten verstehen",
        value=(
            "Die **Quote** zeigt deinen möglichen Gewinn.\n"
            "Die **Prozentangabe** zeigt die Siegchance.\n\n"
            "**Beispiel:** Quote 2.50x bei 100 🪙\n"
            "→ Möglicher Gewinn: **250** 🪙"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🎯 Wettarten",
        value=(
            "🏠 **Heimsieg** - Das Heimteam gewinnt\n"
            "🤝 **Remis** - Unentschieden\n"
            "✈️ **Auswärtssieg** - Das Auswärtsteam gewinnt"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🏟️ Verfügbare Ligen",
        value=(
            "**Kostenlos:**\n"
            "🇩🇪 Bundesliga, 2. Bundesliga, DFB-Pokal\n\n"
            "**Mit API-Key:**\n"
            "🏆 Champions League, Premier League\n"
            "🇪🇸 La Liga, 🇮🇹 Serie A, 🏆 World Cup"
        ),
        inline=False
    )
    
    return embed
