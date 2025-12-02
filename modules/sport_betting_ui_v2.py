"""
Sulfur Bot - Sport Betting Discord UI Components (v2)
Improved user-friendly UI with win probabilities and consolidated betting flow.

Flow: Main Menu (highlighted games) → League Select → Match Details (with probabilities) → Bet Type → Place Bet
"""

import discord
from discord import ui
from discord.ui import View, Button, Select, Modal, TextInput
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime, timedelta, timezone

from modules.sport_betting import (
    LEAGUES, MatchStatus, BetOutcome, BetType,
    format_match_time, get_league_emoji, get_league_name,
    format_odds_display, get_outcome_emoji,
    get_upcoming_matches, get_recent_matches, get_match_from_db, place_bet,
    get_user_bets, get_user_betting_stats, get_betting_leaderboard,
    sync_league_matches, OddsCalculator, place_combo_bet, get_user_combo_bets
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


# Constants
SECONDS_IN_DAY = 86400

# German timezone handling
GERMAN_TZ = None
try:
    from zoneinfo import ZoneInfo
    try:
        GERMAN_TZ = ZoneInfo("Europe/Berlin")
    except KeyError:
        # ZoneInfoNotFoundError (a subclass of KeyError) is raised when
        # the tzdata package is not installed (common on Termux/Android)
        pass
except ImportError:
    # zoneinfo module not available (Python < 3.9)
    pass


def format_match_time_detailed(match_time) -> str:
    """Format match time with date and time in German local time."""
    if match_time is None:
        return "TBD"
    
    if isinstance(match_time, str):
        try:
            match_time = datetime.fromisoformat(match_time.replace("Z", "+00:00"))
        except ValueError:
            return match_time
    
    # Handle timezone-naive datetimes from database by treating them as UTC
    if match_time.tzinfo is None:
        match_time = match_time.replace(tzinfo=timezone.utc)
    
    now = datetime.now(timezone.utc)
    delta = match_time - now
    
    # Convert to German local time for display
    if GERMAN_TZ:
        local_time = match_time.astimezone(GERMAN_TZ)
    else:
        # Fallback: approximate CET/CEST (UTC+1 in winter, UTC+2 in summer)
        # Simple DST approximation: summer is roughly April-October
        month = match_time.month
        offset_hours = 2 if 4 <= month <= 10 else 1
        local_time = match_time + timedelta(hours=offset_hours)
    
    if delta.days == 0 and delta.total_seconds() >= 0:
        return f"🔴 Heute {local_time.strftime('%H:%M')}"
    elif delta.days == 1 or (delta.days == 0 and -SECONDS_IN_DAY < delta.total_seconds() < 0):
        return f"📅 Morgen {local_time.strftime('%H:%M')}"
    elif 0 < delta.days < 7:
        weekdays = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
        return f"📆 {weekdays[local_time.weekday()]} {local_time.strftime('%H:%M')}"
    elif delta.days >= 7:
        return f"📅 {local_time.strftime('%d.%m. %H:%M')}"
    else:
        # Match is in the past
        return f"📅 {local_time.strftime('%d.%m. %H:%M')}"


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


def create_advanced_bet_embed(match: Dict, bet_category: str = "over_under") -> discord.Embed:
    """Create an embed for advanced bet type selection."""
    home_team = match.get("home_team", "Unknown")
    away_team = match.get("away_team", "Unknown")
    league_id = match.get("league_id", "bl1")
    
    # Calculate advanced odds
    advanced_odds = OddsCalculator.calculate_advanced_odds(match)
    
    embed = discord.Embed(
        title=f"⚽ {home_team} vs {away_team}",
        color=discord.Color.gold()
    )
    
    league_name = get_league_name(league_id)
    league_emoji = get_league_emoji(league_id)
    
    if bet_category == "over_under":
        embed.description = f"{league_emoji} **{league_name}**\n\n📊 **Tore & BTTS Wetten**"
        
        embed.add_field(
            name="⚽ Über/Unter Tore",
            value=(
                f"⬆️ **Über 1.5** → {advanced_odds.get('over_1.5', 1.35):.2f}x\n"
                f"⬇️ **Unter 1.5** → {advanced_odds.get('under_1.5', 3.20):.2f}x\n"
                f"⬆️ **Über 2.5** → {advanced_odds.get('over_2.5', 1.90):.2f}x\n"
                f"⬇️ **Unter 2.5** → {advanced_odds.get('under_2.5', 1.90):.2f}x\n"
                f"⬆️ **Über 3.5** → {advanced_odds.get('over_3.5', 2.80):.2f}x\n"
                f"⬇️ **Unter 3.5** → {advanced_odds.get('under_3.5', 1.45):.2f}x"
            ),
            inline=True
        )
        
        embed.add_field(
            name="⚽ Beide Teams treffen (BTTS)",
            value=(
                f"✅ **Ja** → {advanced_odds.get('btts_yes', 1.75):.2f}x\n"
                f"❌ **Nein** → {advanced_odds.get('btts_no', 2.10):.2f}x"
            ),
            inline=True
        )
        
    elif bet_category == "goal_diff":
        embed.description = f"{league_emoji} **{league_name}**\n\n📊 **Tordifferenz Wetten**\n\n*Wette auf den Sieg mit X+ Toren Vorsprung*"
        
        embed.add_field(
            name=f"🏠 {home_team} gewinnt mit...",
            value=(
                f"**+1 Tor** → {advanced_odds.get('home_diff_1', 2.1):.2f}x\n"
                f"**+2 Tore** → {advanced_odds.get('home_diff_2', 4.0):.2f}x\n"
                f"**+3 Tore** → {advanced_odds.get('home_diff_3', 7.0):.2f}x"
            ),
            inline=True
        )
        
        embed.add_field(
            name=f"✈️ {away_team} gewinnt mit...",
            value=(
                f"**+1 Tor** → {advanced_odds.get('away_diff_1', 3.15):.2f}x\n"
                f"**+2 Tore** → {advanced_odds.get('away_diff_2', 6.0):.2f}x\n"
                f"**+3 Tore** → {advanced_odds.get('away_diff_3', 10.5):.2f}x"
            ),
            inline=True
        )
    
    embed.set_footer(text="Wähle deine Wette aus den Buttons unten!")
    return embed


def create_highlighted_matches_embed(matches: List[Dict], user_balance: int = 0) -> discord.Embed:
    """Create an embed showing highlighted upcoming matches."""
    embed = discord.Embed(
        title="⚽ Sport Betting",
        description=(
            "**Willkommen bei Sport Betting!**\n"
            "Wette auf echte Fußballspiele und gewinne Coins!\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━"
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
            match_status = match.get("status", "scheduled")
            
            # Get score if available
            home_score = match.get("home_score", 0)
            away_score = match.get("away_score", 0)
            
            # Determine status display
            if match_status == "finished":
                status_text = f"🏁 **{home_score}:{away_score}** (Beendet)"
            elif match_status == "live":
                status_text = f"🔴 **{home_score}:{away_score}** LIVE"
            else:
                time_str = format_match_time_detailed(match_time)
                # Calculate favorite (lowest odds = highest probability)
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
                status_text = f"{time_str} • {favorite}"
            
            match_list.append(
                f"{league_emoji} **{home_team}** vs **{away_team}**\n"
                f"└ {status_text}"
            )
        
        embed.add_field(
            name="🔥 Kommende Spiele",
            value="\n\n".join(match_list) if match_list else "Keine Spiele gefunden",
            inline=False
        )
    else:
        embed.add_field(
            name="🔥 Kommende Spiele",
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
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ {message}", ephemeral=True)
                
        except ValueError:
            await interaction.response.send_message(
                "❌ Bitte gib eine gültige Zahl ein!",
                ephemeral=True
            )


class AdvancedBetSelectView(View):
    """View for selecting advanced bet types (Over/Under, BTTS, Goal Difference)."""
    
    def __init__(self, match: Dict, db_helpers, balance_check_func,
                 balance_deduct_func=None, timeout: float = 300.0):
        super().__init__(timeout=timeout)
        self.match = match
        self.db_helpers = db_helpers
        self.balance_check_func = balance_check_func
        self.balance_deduct_func = balance_deduct_func
        
        # Calculate advanced odds
        self.advanced_odds = OddsCalculator.calculate_advanced_odds(match)
    
    @ui.button(label="⬆️ Über 2.5 Tore", style=discord.ButtonStyle.success, row=0)
    async def bet_over_2_5(self, interaction: discord.Interaction, button: Button):
        modal = BetTypeModal(
            self.match, "over_under_2.5", "over", self.advanced_odds.get("over_2.5", 1.90),
            self.db_helpers, self.balance_check_func, self.balance_deduct_func
        )
        await interaction.response.send_modal(modal)
    
    @ui.button(label="⬇️ Unter 2.5 Tore", style=discord.ButtonStyle.danger, row=0)
    async def bet_under_2_5(self, interaction: discord.Interaction, button: Button):
        modal = BetTypeModal(
            self.match, "over_under_2.5", "under", self.advanced_odds.get("under_2.5", 1.90),
            self.db_helpers, self.balance_check_func, self.balance_deduct_func
        )
        await interaction.response.send_modal(modal)
    
    @ui.button(label="⬆️ Über 1.5 Tore", style=discord.ButtonStyle.success, row=1)
    async def bet_over_1_5(self, interaction: discord.Interaction, button: Button):
        modal = BetTypeModal(
            self.match, "over_under_1.5", "over", self.advanced_odds.get("over_1.5", 1.35),
            self.db_helpers, self.balance_check_func, self.balance_deduct_func
        )
        await interaction.response.send_modal(modal)
    
    @ui.button(label="⬇️ Unter 1.5 Tore", style=discord.ButtonStyle.danger, row=1)
    async def bet_under_1_5(self, interaction: discord.Interaction, button: Button):
        modal = BetTypeModal(
            self.match, "over_under_1.5", "under", self.advanced_odds.get("under_1.5", 3.20),
            self.db_helpers, self.balance_check_func, self.balance_deduct_func
        )
        await interaction.response.send_modal(modal)
    
    @ui.button(label="⬆️ Über 3.5 Tore", style=discord.ButtonStyle.success, row=2)
    async def bet_over_3_5(self, interaction: discord.Interaction, button: Button):
        modal = BetTypeModal(
            self.match, "over_under_3.5", "over", self.advanced_odds.get("over_3.5", 2.80),
            self.db_helpers, self.balance_check_func, self.balance_deduct_func
        )
        await interaction.response.send_modal(modal)
    
    @ui.button(label="⬇️ Unter 3.5 Tore", style=discord.ButtonStyle.danger, row=2)
    async def bet_under_3_5(self, interaction: discord.Interaction, button: Button):
        modal = BetTypeModal(
            self.match, "over_under_3.5", "under", self.advanced_odds.get("under_3.5", 1.45),
            self.db_helpers, self.balance_check_func, self.balance_deduct_func
        )
        await interaction.response.send_modal(modal)
    
    @ui.button(label="✅ Beide Teams treffen", style=discord.ButtonStyle.primary, row=3)
    async def bet_btts_yes(self, interaction: discord.Interaction, button: Button):
        modal = BetTypeModal(
            self.match, "btts", "yes", self.advanced_odds.get("btts_yes", 1.75),
            self.db_helpers, self.balance_check_func, self.balance_deduct_func
        )
        await interaction.response.send_modal(modal)
    
    @ui.button(label="❌ Nicht beide treffen", style=discord.ButtonStyle.secondary, row=3)
    async def bet_btts_no(self, interaction: discord.Interaction, button: Button):
        modal = BetTypeModal(
            self.match, "btts", "no", self.advanced_odds.get("btts_no", 2.10),
            self.db_helpers, self.balance_check_func, self.balance_deduct_func
        )
        await interaction.response.send_modal(modal)
    
    @ui.button(label="⬅️ Zurück", style=discord.ButtonStyle.secondary, row=4)
    async def go_back(self, interaction: discord.Interaction, button: Button):
        # Go back to the main bet type selection
        embed = create_match_detail_embed(self.match, show_probabilities=True)
        view = BetTypeSelectView(
            self.match, self.db_helpers, self.balance_check_func, self.balance_deduct_func
        )
        await interaction.response.edit_message(embed=embed, view=view)


class GoalDiffBetView(View):
    """View for selecting goal difference bets."""
    
    def __init__(self, match: Dict, db_helpers, balance_check_func,
                 balance_deduct_func=None, timeout: float = 300.0):
        super().__init__(timeout=timeout)
        self.match = match
        self.db_helpers = db_helpers
        self.balance_check_func = balance_check_func
        self.balance_deduct_func = balance_deduct_func
        
        # Calculate advanced odds
        self.advanced_odds = OddsCalculator.calculate_advanced_odds(match)
        
        home_team = match.get("home_team", "Heim")[:10]
        away_team = match.get("away_team", "Auswärts")[:10]
        
        # Update button labels with team names
        self.bet_home_diff_1.label = f"🏠 {home_team} +1"
        self.bet_away_diff_1.label = f"✈️ {away_team} +1"
        self.bet_home_diff_2.label = f"🏠 {home_team} +2"
        self.bet_away_diff_2.label = f"✈️ {away_team} +2"
        self.bet_home_diff_3.label = f"🏠 {home_team} +3"
        self.bet_away_diff_3.label = f"✈️ {away_team} +3"
    
    @ui.button(label="🏠 Heim +1", style=discord.ButtonStyle.primary, row=0)
    async def bet_home_diff_1(self, interaction: discord.Interaction, button: Button):
        modal = BetTypeModal(
            self.match, "goal_diff_1", "home_diff_1", self.advanced_odds.get("home_diff_1", 2.1),
            self.db_helpers, self.balance_check_func, self.balance_deduct_func
        )
        await interaction.response.send_modal(modal)
    
    @ui.button(label="✈️ Auswärts +1", style=discord.ButtonStyle.primary, row=0)
    async def bet_away_diff_1(self, interaction: discord.Interaction, button: Button):
        modal = BetTypeModal(
            self.match, "goal_diff_1", "away_diff_1", self.advanced_odds.get("away_diff_1", 3.15),
            self.db_helpers, self.balance_check_func, self.balance_deduct_func
        )
        await interaction.response.send_modal(modal)
    
    @ui.button(label="🏠 Heim +2", style=discord.ButtonStyle.success, row=1)
    async def bet_home_diff_2(self, interaction: discord.Interaction, button: Button):
        modal = BetTypeModal(
            self.match, "goal_diff_2", "home_diff_2", self.advanced_odds.get("home_diff_2", 4.0),
            self.db_helpers, self.balance_check_func, self.balance_deduct_func
        )
        await interaction.response.send_modal(modal)
    
    @ui.button(label="✈️ Auswärts +2", style=discord.ButtonStyle.success, row=1)
    async def bet_away_diff_2(self, interaction: discord.Interaction, button: Button):
        modal = BetTypeModal(
            self.match, "goal_diff_2", "away_diff_2", self.advanced_odds.get("away_diff_2", 6.0),
            self.db_helpers, self.balance_check_func, self.balance_deduct_func
        )
        await interaction.response.send_modal(modal)
    
    @ui.button(label="🏠 Heim +3", style=discord.ButtonStyle.danger, row=2)
    async def bet_home_diff_3(self, interaction: discord.Interaction, button: Button):
        modal = BetTypeModal(
            self.match, "goal_diff_3", "home_diff_3", self.advanced_odds.get("home_diff_3", 7.0),
            self.db_helpers, self.balance_check_func, self.balance_deduct_func
        )
        await interaction.response.send_modal(modal)
    
    @ui.button(label="✈️ Auswärts +3", style=discord.ButtonStyle.danger, row=2)
    async def bet_away_diff_3(self, interaction: discord.Interaction, button: Button):
        modal = BetTypeModal(
            self.match, "goal_diff_3", "away_diff_3", self.advanced_odds.get("away_diff_3", 10.5),
            self.db_helpers, self.balance_check_func, self.balance_deduct_func
        )
        await interaction.response.send_modal(modal)
    
    @ui.button(label="⬅️ Zurück", style=discord.ButtonStyle.secondary, row=3)
    async def go_back(self, interaction: discord.Interaction, button: Button):
        # Go back to the main bet type selection
        embed = create_match_detail_embed(self.match, show_probabilities=True)
        view = BetTypeSelectView(
            self.match, self.db_helpers, self.balance_check_func, self.balance_deduct_func
        )
        await interaction.response.edit_message(embed=embed, view=view)


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
    
    @ui.button(label="⚽ Tore (Über/Unter)", style=discord.ButtonStyle.success, row=1)
    async def show_over_under(self, interaction: discord.Interaction, button: Button):
        """Show Over/Under and BTTS bet options."""
        embed = create_advanced_bet_embed(self.match, "over_under")
        view = AdvancedBetSelectView(
            self.match, self.db_helpers, self.balance_check_func, self.balance_deduct_func
        )
        await interaction.response.edit_message(embed=embed, view=view)
    
    @ui.button(label="📊 Tordifferenz", style=discord.ButtonStyle.success, row=1)
    async def show_goal_diff(self, interaction: discord.Interaction, button: Button):
        """Show goal difference bet options."""
        embed = create_advanced_bet_embed(self.match, "goal_diff")
        view = GoalDiffBetView(
            self.match, self.db_helpers, self.balance_check_func, self.balance_deduct_func
        )
        await interaction.response.edit_message(embed=embed, view=view)
    
    @ui.button(label="⬅️ Zurück", style=discord.ButtonStyle.danger, row=2)
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
# COMBO BET BUILDER
# ============================================================================

class ComboBetSelection:
    """Represents a single selection in a combo bet."""
    def __init__(self, match: Dict, bet_type: str, bet_outcome: str, odds: float):
        self.match = match
        self.match_id = match.get("match_id", match.get("id"))
        self.bet_type = bet_type
        self.bet_outcome = bet_outcome
        self.odds = odds
    
    def to_dict(self) -> Dict:
        return {
            "match_id": self.match_id,
            "bet_type": self.bet_type,
            "bet_outcome": self.bet_outcome,
            "odds": self.odds
        }
    
    def get_display_name(self) -> str:
        """Get a human-readable name for this selection."""
        home_team = self.match.get("home_team", "Heim")[:12]
        away_team = self.match.get("away_team", "Auswärts")[:12]
        
        outcome_names = {
            "home": f"🏠 {home_team}",
            "draw": "🤝 Remis",
            "away": f"✈️ {away_team}",
            "over": "⬆️ Über",
            "under": "⬇️ Unter",
            "yes": "✅ Ja",
            "no": "❌ Nein",
            "home_diff_1": f"🏠 {home_team} +1",
            "home_diff_2": f"🏠 {home_team} +2",
            "home_diff_3": f"🏠 {home_team} +3",
            "away_diff_1": f"✈️ {away_team} +1",
            "away_diff_2": f"✈️ {away_team} +2",
            "away_diff_3": f"✈️ {away_team} +3",
        }
        
        return f"{home_team} vs {away_team}: {outcome_names.get(self.bet_outcome, self.bet_outcome)} @ {self.odds:.2f}x"


# In-memory storage for combo bet selections during the building phase.
# NOTE: This is intentionally stored in memory rather than the database because:
# 1. Selections are temporary and only used while actively building a combo bet
# 2. Once a combo bet is placed, it's persisted to the database (sport_combo_bets table)
# 3. If the bot restarts, users simply need to rebuild their combo - this is acceptable UX
# 4. For high-availability deployments, consider moving to Redis or database-backed sessions
_combo_selections: Dict[int, List[ComboBetSelection]] = {}


def get_user_combo_selections(user_id: int) -> List[ComboBetSelection]:
    """Get the current combo bet selections for a user."""
    return _combo_selections.get(user_id, [])


def add_combo_selection(user_id: int, selection: ComboBetSelection) -> bool:
    """Add a selection to a user's combo bet. Returns False if max selections reached."""
    if user_id not in _combo_selections:
        _combo_selections[user_id] = []
    
    # Max 10 selections
    if len(_combo_selections[user_id]) >= 10:
        return False
    
    # Check if this match is already in the combo (different bet types allowed)
    _combo_selections[user_id].append(selection)
    return True


def remove_combo_selection(user_id: int, index: int) -> bool:
    """Remove a selection from a user's combo bet by index."""
    if user_id not in _combo_selections:
        return False
    
    if 0 <= index < len(_combo_selections[user_id]):
        _combo_selections[user_id].pop(index)
        return True
    return False


def clear_combo_selections(user_id: int):
    """Clear all combo bet selections for a user."""
    _combo_selections[user_id] = []


def get_combo_total_odds(user_id: int) -> float:
    """Calculate total odds for a user's combo bet."""
    selections = get_user_combo_selections(user_id)
    if not selections:
        return 0.0
    
    total = 1.0
    for s in selections:
        total *= s.odds
    return round(total, 2)


class ComboBetAmountModal(Modal):
    """Modal for entering combo bet amount."""
    
    def __init__(self, db_helpers, user_id: int, balance_check_func, balance_deduct_func=None):
        total_odds = get_combo_total_odds(user_id)
        selections = get_user_combo_selections(user_id)
        
        super().__init__(title=f"🎰 Kombiwette ({len(selections)} Auswahlen)")
        self.db_helpers = db_helpers
        self.user_id = user_id
        self.balance_check_func = balance_check_func
        self.balance_deduct_func = balance_deduct_func
        self.total_odds = total_odds
        
        self.amount_input = TextInput(
            label=f"Einsatz (Gesamtquote: {total_odds:.2f}x)",
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
            
            balance = await self.balance_check_func(self.user_id)
            
            if balance < amount:
                await interaction.response.send_message(
                    f"❌ Nicht genug Geld! Du hast **{balance}** 🪙, brauchst aber **{amount}** 🪙.",
                    ephemeral=True
                )
                return
            
            selections = get_user_combo_selections(self.user_id)
            if len(selections) < 2:
                await interaction.response.send_message(
                    "❌ Eine Kombiwette braucht mindestens 2 Auswahlen!",
                    ephemeral=True
                )
                return
            
            # Place the combo bet
            selection_dicts = [s.to_dict() for s in selections]
            success, message = await place_combo_bet(
                self.db_helpers,
                self.user_id,
                selection_dicts,
                amount
            )
            
            if success:
                if self.balance_deduct_func:
                    await self.balance_deduct_func(self.user_id, interaction.user.display_name, -amount)
                
                potential_payout = int(amount * self.total_odds)
                
                embed = discord.Embed(
                    title="✅ Kombiwette platziert!",
                    color=discord.Color.green()
                )
                
                # List all selections
                selection_text = "\n".join([f"• {s.get_display_name()}" for s in selections])
                embed.add_field(
                    name=f"🎯 {len(selections)} Auswahlen",
                    value=selection_text[:1024],
                    inline=False
                )
                embed.add_field(name="💰 Einsatz", value=f"**{amount}** 🪙", inline=True)
                embed.add_field(name="📊 Gesamtquote", value=f"**{self.total_odds:.2f}x**", inline=True)
                embed.add_field(name="💎 Möglicher Gewinn", value=f"**{potential_payout}** 🪙", inline=True)
                
                # Clear selections after successful bet
                clear_combo_selections(self.user_id)
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ {message}", ephemeral=True)
                
        except ValueError:
            await interaction.response.send_message(
                "❌ Bitte gib eine gültige Zahl ein!",
                ephemeral=True
            )


class ComboBetBuilderView(View):
    """View for building a combo bet with multiple selections."""
    
    def __init__(self, db_helpers, user_id: int, balance_check_func, 
                 balance_deduct_func=None, timeout: float = 600.0):
        super().__init__(timeout=timeout)
        self.db_helpers = db_helpers
        self.user_id = user_id
        self.balance_check_func = balance_check_func
        self.balance_deduct_func = balance_deduct_func
        self._update_button_states()
    
    def _update_button_states(self):
        """Update button states based on current selections."""
        selections = get_user_combo_selections(self.user_id)
        self.place_combo.disabled = len(selections) < 2
        self.clear_selections.disabled = len(selections) == 0
    
    def get_embed(self) -> discord.Embed:
        """Create embed showing current combo bet selections."""
        selections = get_user_combo_selections(self.user_id)
        total_odds = get_combo_total_odds(self.user_id)
        
        embed = discord.Embed(
            title="🎰 Kombiwette Builder",
            description=(
                "Füge mehrere Wetten zu einer Kombiwette zusammen!\n"
                "Alle Tipps müssen richtig sein, um zu gewinnen.\n"
                "Die Quoten werden multipliziert.\n\n"
                f"**Aktuelle Auswahlen:** {len(selections)}/10"
            ),
            color=discord.Color.purple()
        )
        
        if selections:
            selection_text = ""
            for i, s in enumerate(selections, 1):
                selection_text += f"**{i}.** {s.get_display_name()}\n"
            
            embed.add_field(
                name="📋 Deine Auswahlen",
                value=selection_text[:1024] if selection_text else "Keine",
                inline=False
            )
            
            embed.add_field(
                name="📊 Gesamtquote",
                value=f"**{total_odds:.2f}x**",
                inline=True
            )
            
            embed.add_field(
                name="💎 Bei 100 🪙 Einsatz",
                value=f"**{int(100 * total_odds)}** 🪙 Gewinn",
                inline=True
            )
        else:
            embed.add_field(
                name="📋 Deine Auswahlen",
                value="*Noch keine Auswahlen. Füge Wetten über 'Liga wählen' hinzu!*",
                inline=False
            )
        
        embed.set_footer(text="Mindestens 2 Auswahlen für eine Kombiwette | Max. 10 Auswahlen")
        return embed
    
    @ui.button(label="🏟️ Liga wählen", style=discord.ButtonStyle.primary, row=0)
    async def select_league(self, interaction: discord.Interaction, button: Button):
        async def on_league_select(inter: discord.Interaction, league_id: str):
            await inter.response.defer()
            
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
            
            view = ComboMatchSelectView(
                matches, self.db_helpers, self.user_id, 
                self.balance_check_func, self.balance_deduct_func, league_id
            )
            await inter.followup.edit_message(
                message_id=inter.message.id,
                embed=view.get_embed(),
                view=view
            )
        
        view = LeagueSelectView(on_league_select)
        await interaction.response.edit_message(embed=view.get_embed(), view=view)
    
    @ui.button(label="🎰 Kombiwette platzieren", style=discord.ButtonStyle.success, row=0)
    async def place_combo(self, interaction: discord.Interaction, button: Button):
        selections = get_user_combo_selections(self.user_id)
        if len(selections) < 2:
            await interaction.response.send_message(
                "❌ Du brauchst mindestens 2 Auswahlen für eine Kombiwette!",
                ephemeral=True
            )
            return
        
        modal = ComboBetAmountModal(
            self.db_helpers, self.user_id, 
            self.balance_check_func, self.balance_deduct_func
        )
        await interaction.response.send_modal(modal)
    
    @ui.button(label="🗑️ Alle löschen", style=discord.ButtonStyle.danger, row=0)
    async def clear_selections(self, interaction: discord.Interaction, button: Button):
        clear_combo_selections(self.user_id)
        self._update_button_states()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)
    
    @ui.button(label="⬅️ Zurück zum Hauptmenü", style=discord.ButtonStyle.secondary, row=1)
    async def go_back(self, interaction: discord.Interaction, button: Button):
        # Get matches and balance for main view
        matches = await get_upcoming_matches(self.db_helpers, None, limit=5)
        balance = await self.balance_check_func(interaction.user.id)
        
        embed = create_highlighted_matches_embed(matches, balance)
        view = SportBetsMainView(
            self.db_helpers, self.balance_check_func, self.balance_deduct_func
        )
        await interaction.response.edit_message(embed=embed, view=view)


class ComboMatchSelectView(View):
    """View for selecting a match to add to combo bet."""
    
    def __init__(self, matches: List[Dict], db_helpers, user_id: int,
                 balance_check_func, balance_deduct_func=None, 
                 league_id: str = None, timeout: float = 300.0):
        super().__init__(timeout=timeout)
        self.db_helpers = db_helpers
        self.user_id = user_id
        self.balance_check_func = balance_check_func
        self.balance_deduct_func = balance_deduct_func
        self.league_id = league_id
        self.matches = matches
        
        if matches:
            self.add_item(ComboMatchSelectDropdown(
                matches, db_helpers, user_id, 
                balance_check_func, balance_deduct_func
            ))
    
    def get_embed(self) -> discord.Embed:
        league_name = get_league_name(self.league_id) if self.league_id else "Alle Ligen"
        league_emoji = get_league_emoji(self.league_id) if self.league_id else "⚽"
        
        selections = get_user_combo_selections(self.user_id)
        total_odds = get_combo_total_odds(self.user_id)
        
        embed = discord.Embed(
            title=f"{league_emoji} {league_name} - Spiel für Kombi auswählen",
            description=f"**Aktuelle Kombi:** {len(selections)} Auswahlen | Quote: {total_odds:.2f}x",
            color=discord.Color.purple()
        )
        
        return embed


class ComboMatchSelectDropdown(Select):
    """Dropdown to select a match for combo bet."""
    
    def __init__(self, matches: List[Dict], db_helpers, user_id: int,
                 balance_check_func, balance_deduct_func=None):
        self.matches_dict = {}
        self.db_helpers = db_helpers
        self.user_id = user_id
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
            
            options.append(discord.SelectOption(
                label=f"{home_team} vs {away_team}"[:100],
                value=match_id,
                description=f"{time_str}"[:100],
                emoji="⚽"
            ))
        
        if not options:
            options = [discord.SelectOption(label="Keine Spiele", value="none")]
        
        super().__init__(
            placeholder="⚽ Spiel für Kombi auswählen...",
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
        view = ComboBetTypeSelectView(
            match, self.db_helpers, self.user_id,
            self.balance_check_func, self.balance_deduct_func
        )
        
        await interaction.response.edit_message(embed=embed, view=view)


class ComboBetTypeSelectView(View):
    """View for selecting bet type to add to combo."""
    
    def __init__(self, match: Dict, db_helpers, user_id: int, balance_check_func,
                 balance_deduct_func=None, timeout: float = 300.0):
        super().__init__(timeout=timeout)
        self.match = match
        self.db_helpers = db_helpers
        self.user_id = user_id
        self.balance_check_func = balance_check_func
        self.balance_deduct_func = balance_deduct_func
        
        # Get odds
        self.odds_home = float(match.get("odds_home", 2.0))
        self.odds_draw = float(match.get("odds_draw", 3.5))
        self.odds_away = float(match.get("odds_away", 3.0))
        self.advanced_odds = OddsCalculator.calculate_advanced_odds(match)
        
        home_team = match.get("home_team", "Heim")[:10]
        away_team = match.get("away_team", "Auswärts")[:10]
        
        self.add_home.label = f"🏠 {home_team}"
        self.add_away.label = f"✈️ {away_team}"
    
    async def _add_selection(self, interaction: discord.Interaction, bet_type: str, outcome: str, odds: float):
        selection = ComboBetSelection(self.match, bet_type, outcome, odds)
        
        if add_combo_selection(self.user_id, selection):
            # Go back to combo builder
            view = ComboBetBuilderView(
                self.db_helpers, self.user_id,
                self.balance_check_func, self.balance_deduct_func
            )
            await interaction.response.edit_message(embed=view.get_embed(), view=view)
        else:
            await interaction.response.send_message(
                "❌ Maximal 10 Auswahlen erlaubt!",
                ephemeral=True
            )
    
    @ui.button(label="🏠 Heim", style=discord.ButtonStyle.primary, row=0)
    async def add_home(self, interaction: discord.Interaction, button: Button):
        await self._add_selection(interaction, "winner", "home", self.odds_home)
    
    @ui.button(label="🤝 Remis", style=discord.ButtonStyle.secondary, row=0)
    async def add_draw(self, interaction: discord.Interaction, button: Button):
        await self._add_selection(interaction, "winner", "draw", self.odds_draw)
    
    @ui.button(label="✈️ Auswärts", style=discord.ButtonStyle.primary, row=0)
    async def add_away(self, interaction: discord.Interaction, button: Button):
        await self._add_selection(interaction, "winner", "away", self.odds_away)
    
    @ui.button(label="⬆️ Über 2.5", style=discord.ButtonStyle.success, row=1)
    async def add_over_2_5(self, interaction: discord.Interaction, button: Button):
        await self._add_selection(interaction, "over_under_2.5", "over", self.advanced_odds.get("over_2.5", 1.90))
    
    @ui.button(label="⬇️ Unter 2.5", style=discord.ButtonStyle.danger, row=1)
    async def add_under_2_5(self, interaction: discord.Interaction, button: Button):
        await self._add_selection(interaction, "over_under_2.5", "under", self.advanced_odds.get("under_2.5", 1.90))
    
    @ui.button(label="✅ BTTS Ja", style=discord.ButtonStyle.success, row=1)
    async def add_btts_yes(self, interaction: discord.Interaction, button: Button):
        await self._add_selection(interaction, "btts", "yes", self.advanced_odds.get("btts_yes", 1.75))
    
    @ui.button(label="⬅️ Zurück zur Kombi", style=discord.ButtonStyle.secondary, row=2)
    async def go_back(self, interaction: discord.Interaction, button: Button):
        view = ComboBetBuilderView(
            self.db_helpers, self.user_id,
            self.balance_check_func, self.balance_deduct_func
        )
        await interaction.response.edit_message(embed=view.get_embed(), view=view)


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
        
        # Get fresh upcoming matches (only scheduled future games)
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
    
    @ui.button(label="🎰 Kombiwette", style=discord.ButtonStyle.success, row=2)
    async def combo_bet(self, interaction: discord.Interaction, button: Button):
        """Open the combo bet builder."""
        view = ComboBetBuilderView(
            self.db_helpers, interaction.user.id,
            self.balance_check_func, self.balance_deduct_func
        )
        await interaction.response.edit_message(embed=view.get_embed(), view=view)
    
    @ui.button(label="❓ Hilfe", style=discord.ButtonStyle.secondary, row=2)
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
            "4️⃣ Wähle deinen Tipp\n"
            "5️⃣ Gib deinen Einsatz ein\n"
            "6️⃣ Warte auf das Spielergebnis!"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🎯 Wettarten",
        value=(
            "**Basis:**\n"
            "🏠 Heimsieg | 🤝 Remis | ✈️ Auswärtssieg\n\n"
            "**Erweitert:**\n"
            "⬆️⬇️ Über/Unter 1.5, 2.5, 3.5 Tore\n"
            "✅❌ Beide Teams treffen (BTTS)\n"
            "📊 Tordifferenz (+1, +2, +3)"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🎰 Kombiwetten",
        value=(
            "Kombiniere mehrere Tipps zu einer Wette!\n"
            "• Mindestens 2 Auswahlen\n"
            "• Maximal 10 Auswahlen\n"
            "• Quoten werden **multipliziert**\n"
            "• Alle Tipps müssen richtig sein"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🔔 Benachrichtigungen",
        value=(
            "Du erhältst **30 Min vor Spielbeginn**\n"
            "eine Erinnerung per DM!"
        ),
        inline=True
    )
    
    embed.add_field(
        name="📊 Quoten verstehen",
        value=(
            "Quote 2.50x bei 100 🪙\n"
            "→ Gewinn: **250** 🪙"
        ),
        inline=True
    )
    
    embed.add_field(
        name="🏟️ Verfügbare Ligen",
        value=(
            "🇩🇪 Bundesliga, 2. Bundesliga\n"
            "🏆 DFB-Pokal, Champions League\n"
            "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League & mehr"
        ),
        inline=False
    )
    
    return embed
