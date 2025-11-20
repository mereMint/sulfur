"""
Sulfur Bot - Gambling Games Module
Includes Blackjack, Roulette, Russian Roulette, and Mines.
"""

import discord
import random
from datetime import datetime, timezone
from modules.logger_utils import bot_logger as logger

# --- Blackjack ---

class BlackjackGame:
    """Handles a Blackjack game instance."""
    
    def __init__(self, player_id: int, bet: int):
        self.player_id = player_id
        self.bet = bet
        self.deck = self._create_deck()
        self.player_hand = []
        self.dealer_hand = []
        self.is_active = True
        self.player_stood = False
        
        # Deal initial cards
        self.player_hand.append(self._draw_card())
        self.dealer_hand.append(self._draw_card())
        self.player_hand.append(self._draw_card())
        self.dealer_hand.append(self._draw_card())
    
    def _create_deck(self):
        """Creates a shuffled deck of cards."""
        suits = ['♠️', '♥️', '♣️', '♦️']
        ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
        deck = [{'rank': rank, 'suit': suit} for suit in suits for rank in ranks]
        random.shuffle(deck)
        return deck
    
    def _draw_card(self):
        """Draws a card from the deck."""
        return self.deck.pop()
    
    def _calculate_hand_value(self, hand):
        """Calculates the value of a hand."""
        value = 0
        aces = 0
        
        for card in hand:
            rank = card['rank']
            if rank in ['J', 'Q', 'K']:
                value += 10
            elif rank == 'A':
                aces += 1
                value += 11
            else:
                value += int(rank)
        
        # Adjust for aces
        while value > 21 and aces > 0:
            value -= 10
            aces -= 1
        
        return value
    
    def hit(self):
        """Player draws a card."""
        if not self.is_active or self.player_stood:
            return False
        
        self.player_hand.append(self._draw_card())
        
        # Check for bust
        if self._calculate_hand_value(self.player_hand) > 21:
            self.is_active = False
        
        return True
    
    def stand(self):
        """Player stands, dealer plays."""
        if not self.is_active or self.player_stood:
            return False
        
        self.player_stood = True
        
        # Dealer draws until 17 or higher
        while self._calculate_hand_value(self.dealer_hand) < 17:
            self.dealer_hand.append(self._draw_card())
        
        self.is_active = False
        return True
    
    def get_result(self):
        """
        Returns the game result.
        Returns: (result, multiplier)
        result: 'win', 'lose', 'push', 'blackjack'
        multiplier: payout multiplier
        """
        player_value = self._calculate_hand_value(self.player_hand)
        dealer_value = self._calculate_hand_value(self.dealer_hand)
        
        # Player bust
        if player_value > 21:
            return 'lose', 0
        
        # Blackjack (only on initial 2 cards)
        if player_value == 21 and len(self.player_hand) == 2:
            if dealer_value == 21 and len(self.dealer_hand) == 2:
                return 'push', 1  # Both have blackjack
            return 'blackjack', 2.5
        
        # Dealer bust
        if dealer_value > 21:
            return 'win', 2
        
        # Compare values
        if player_value > dealer_value:
            return 'win', 2
        elif player_value < dealer_value:
            return 'lose', 0
        else:
            return 'push', 1
    
    def create_embed(self, show_dealer_card=False):
        """Creates a Discord embed for the game state."""
        embed = discord.Embed(
            title="🃏 Blackjack",
            color=discord.Color.green()
        )
        
        # Player hand
        player_cards = ' '.join([f"{c['rank']}{c['suit']}" for c in self.player_hand])
        player_value = self._calculate_hand_value(self.player_hand)
        embed.add_field(
            name=f"Your Hand ({player_value})",
            value=player_cards,
            inline=False
        )
        
        # Dealer hand
        if show_dealer_card or not self.is_active:
            dealer_cards = ' '.join([f"{c['rank']}{c['suit']}" for c in self.dealer_hand])
            dealer_value = self._calculate_hand_value(self.dealer_hand)
            embed.add_field(
                name=f"Dealer Hand ({dealer_value})",
                value=dealer_cards,
                inline=False
            )
        else:
            # Only show first card
            dealer_cards = f"{self.dealer_hand[0]['rank']}{self.dealer_hand[0]['suit']} 🂠"
            embed.add_field(
                name="Dealer Hand",
                value=dealer_cards,
                inline=False
            )
        
        embed.add_field(name="Bet", value=f"{self.bet} 🪙", inline=True)
        
        return embed


# --- Roulette ---

class RouletteGame:
    """Handles a Roulette game instance."""
    
    NUMBERS = list(range(37))  # 0-36
    RED = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
    BLACK = [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35]
    
    @staticmethod
    def spin():
        """Spins the wheel and returns the result."""
        return random.choice(RouletteGame.NUMBERS)
    
    @staticmethod
    def check_bet(number, bet_type, bet_value):
        """
        Checks if a bet wins.
        
        Args:
            number: The winning number
            bet_type: Type of bet (number, color, odd_even, high_low, dozen, column)
            bet_value: The value of the bet
        
        Returns:
            (won, multiplier)
        """
        # Straight number
        if bet_type == 'number':
            if number == bet_value:
                return True, 35
            return False, 0
        
        # Red or Black
        elif bet_type == 'color':
            if bet_value == 'red' and number in RouletteGame.RED:
                return True, 2
            elif bet_value == 'black' and number in RouletteGame.BLACK:
                return True, 2
            return False, 0
        
        # Odd or Even
        elif bet_type == 'odd_even':
            if number == 0:
                return False, 0
            if bet_value == 'odd' and number % 2 == 1:
                return True, 2
            elif bet_value == 'even' and number % 2 == 0:
                return True, 2
            return False, 0
        
        # High (19-36) or Low (1-18)
        elif bet_type == 'high_low':
            if number == 0:
                return False, 0
            if bet_value == 'high' and 19 <= number <= 36:
                return True, 2
            elif bet_value == 'low' and 1 <= number <= 18:
                return True, 2
            return False, 0
        
        return False, 0


# --- Russian Roulette ---

class RussianRouletteGame:
    """Handles a Russian Roulette game."""
    
    def __init__(self, player_id: int, entry_fee: int, reward_multiplier: int):
        self.player_id = player_id
        self.entry_fee = entry_fee
        self.reward_multiplier = reward_multiplier
        self.chamber = random.randint(1, 6)
        self.current_shot = 0
    
    def pull_trigger(self):
        """
        Pulls the trigger.
        
        Returns:
            (alive, won, reward)
        """
        self.current_shot += 1
        
        if self.current_shot == self.chamber:
            # Player dies
            return False, False, 0
        
        if self.current_shot == 6:
            # Player survived all shots
            reward = self.entry_fee * self.reward_multiplier
            return True, True, reward
        
        # Continue
        return True, False, 0


# --- Mines ---

class MinesGame:
    """Handles a Mines game instance."""
    
    def __init__(self, player_id: int, bet: int, grid_size: int = 5, mine_count: int = 5):
        self.player_id = player_id
        self.bet = bet
        self.grid_size = grid_size
        self.mine_count = mine_count
        self.grid = [[{'revealed': False, 'is_mine': False} for _ in range(grid_size)] for _ in range(grid_size)]
        self.revealed_count = 0
        self.is_active = True
        
        # Place mines
        positions = [(r, c) for r in range(grid_size) for c in range(grid_size)]
        mine_positions = random.sample(positions, mine_count)
        
        for row, col in mine_positions:
            self.grid[row][col]['is_mine'] = True
    
    def reveal(self, row: int, col: int):
        """
        Reveals a cell.
        
        Returns:
            (continue_game, hit_mine, current_multiplier)
        """
        if not self.is_active:
            return False, False, 0
        
        if self.grid[row][col]['revealed']:
            return True, False, self.get_current_multiplier()
        
        self.grid[row][col]['revealed'] = True
        
        if self.grid[row][col]['is_mine']:
            # Hit a mine - game over
            self.is_active = False
            return False, True, 0
        
        self.revealed_count += 1
        
        # Check if all safe cells revealed
        safe_cells = self.grid_size * self.grid_size - self.mine_count
        if self.revealed_count >= safe_cells:
            self.is_active = False
            return False, False, self.get_current_multiplier()
        
        return True, False, self.get_current_multiplier()
    
    def get_current_multiplier(self):
        """Calculates current win multiplier based on revealed cells."""
        if self.revealed_count == 0:
            return 1.0
        
        # Exponential growth based on risk
        safe_cells = self.grid_size * self.grid_size - self.mine_count
        progress = self.revealed_count / safe_cells
        
        # Multiplier increases exponentially
        multiplier = 1.0 + (progress ** 2) * 5
        return round(multiplier, 2)
    
    def cashout(self):
        """
        Cashes out current winnings.
        
        Returns:
            (winnings, multiplier)
        """
        if not self.is_active:
            return 0, 0
        
        multiplier = self.get_current_multiplier()
        winnings = int(self.bet * multiplier)
        self.is_active = False
        
        return winnings, multiplier
    
    def create_embed(self, show_mines=False):
        """Creates a Discord embed for the game."""
        embed = discord.Embed(
            title="💣 Mines",
            description=f"Grid: {self.grid_size}x{self.grid_size} | Mines: {self.mine_count}",
            color=discord.Color.orange()
        )
        
        # Build grid display
        grid_display = ""
        for row in self.grid:
            row_display = ""
            for cell in row:
                if cell['revealed']:
                    if cell['is_mine']:
                        row_display += "💣 "
                    else:
                        row_display += "💎 "
                elif show_mines and cell['is_mine']:
                    row_display += "💣 "
                else:
                    row_display += "⬜ "
            grid_display += row_display + "\n"
        
        embed.add_field(name="Grid", value=grid_display, inline=False)
        embed.add_field(name="Revealed", value=f"{self.revealed_count} safe cells", inline=True)
        embed.add_field(name="Multiplier", value=f"{self.get_current_multiplier()}x", inline=True)
        embed.add_field(name="Current Winnings", value=f"{int(self.bet * self.get_current_multiplier())} 🪙", inline=True)
        
        return embed


# --- Tower of Treasure ---

class TowerOfTreasureGame:
    """Handles a Tower of Treasure game instance."""
    
    def __init__(self, player_id: int, bet: int, difficulty: int = 1, max_floors: int = 10):
        self.player_id = player_id
        self.bet = bet
        self.difficulty = difficulty  # 1-4
        self.max_floors = max_floors
        self.current_floor = 0
        self.is_active = True
        self.total_columns = 4
        
        # Difficulty determines how many columns are safe vs bombs
        # diff 1: 3 safe, 1 bomb
        # diff 2: 2 safe, 2 bombs
        # diff 3: 1 safe, 3 bombs
        # diff 4: 0-1 safe (random), 3-4 bombs (very hard)
        self.safe_columns = max(1, 4 - difficulty)
        if difficulty >= 4:
            self.safe_columns = random.choice([0, 1])
        
        # Generate floors
        self.floors = []
        for _ in range(max_floors):
            floor = self._generate_floor()
            self.floors.append(floor)
    
    def _generate_floor(self):
        """Generate a floor with random safe/bomb distribution."""
        columns = [False] * self.total_columns  # False = bomb, True = safe
        safe_positions = random.sample(range(self.total_columns), self.safe_columns)
        for pos in safe_positions:
            columns[pos] = True
        return columns
    
    def choose_column(self, column: int):
        """
        Choose a column to climb.
        
        Args:
            column: Column index (0-3)
        
        Returns:
            (alive, reached_top, reward)
        """
        if not self.is_active or column < 0 or column >= self.total_columns:
            return False, False, 0
        
        current_floor_data = self.floors[self.current_floor]
        
        if current_floor_data[column]:
            # Safe column - climb up
            self.current_floor += 1
            
            # Check if reached the top
            if self.current_floor >= self.max_floors:
                self.is_active = False
                reward = self.calculate_reward()
                return True, True, reward
            
            # Continue climbing
            return True, False, 0
        else:
            # Hit a bomb - game over
            self.is_active = False
            return False, False, 0
    
    def cashout(self):
        """
        Cash out current progress.
        
        Returns:
            (reward, multiplier)
        """
        if not self.is_active or self.current_floor == 0:
            return 0, 0
        
        reward = self.calculate_reward()
        self.is_active = False
        return reward, reward / self.bet if self.bet > 0 else 0
    
    def calculate_reward(self):
        """Calculate reward based on floors climbed and difficulty."""
        if self.current_floor == 0:
            return 0
        
        # Base multiplier increases with each floor
        # Higher difficulty = higher rewards
        base_multiplier = 1.0 + (self.current_floor * 0.3 * self.difficulty)
        
        # Bonus for reaching the top
        if self.current_floor >= self.max_floors:
            base_multiplier *= 2
        
        reward = int(self.bet * base_multiplier)
        return reward
    
    def get_progress_percentage(self):
        """Get progress as percentage."""
        return int((self.current_floor / self.max_floors) * 100)
    
    def create_embed(self, show_bombs=False):
        """Creates a Discord embed for the game."""
        embed = discord.Embed(
            title="🗼 Tower of Treasure",
            description=f"Difficulty: {'⭐' * self.difficulty} | Floor: {self.current_floor}/{self.max_floors}",
            color=discord.Color.gold()
        )
        
        # Show current floor visualization
        floor_display = ""
        
        # Show the next 3 floors (or remaining floors)
        floors_to_show = min(3, self.max_floors - self.current_floor)
        start_floor = self.current_floor
        
        for i in range(floors_to_show, -1, -1):
            floor_num = start_floor + i
            if floor_num >= self.max_floors:
                continue
                
            if floor_num == self.current_floor:
                floor_display += f"**Floor {floor_num + 1}** ⬅️ You are here\n"
                if not show_bombs:
                    floor_display += "🏛️ " * self.total_columns + "\n"
                else:
                    floor_data = self.floors[floor_num]
                    for col in floor_data:
                        floor_display += "✅ " if col else "💣 "
                    floor_display += "\n"
            elif floor_num > self.current_floor:
                floor_display += f"Floor {floor_num + 1}\n"
                floor_display += "🏛️ " * self.total_columns + "\n"
        
        if floor_display:
            embed.add_field(name="🗼 Tower", value=floor_display, inline=False)
        
        # Progress bar
        progress = self.get_progress_percentage()
        bar_length = 10
        filled = int((progress / 100) * bar_length)
        bar = '█' * filled + '░' * (bar_length - filled)
        
        embed.add_field(
            name="Progress",
            value=f"{bar} {progress}%",
            inline=False
        )
        
        # Difficulty info
        difficulty_names = {
            1: "Easy (3 safe, 1 bomb)",
            2: "Medium (2 safe, 2 bombs)",
            3: "Hard (1 safe, 3 bombs)",
            4: "Extreme (0-1 safe, 3-4 bombs)"
        }
        embed.add_field(
            name="Difficulty",
            value=difficulty_names.get(self.difficulty, "Unknown"),
            inline=True
        )
        
        # Current potential reward
        if self.current_floor > 0:
            current_reward = self.calculate_reward()
            embed.add_field(
                name="Current Prize",
                value=f"{current_reward} 🪙",
                inline=True
            )
        
        embed.add_field(name="Bet", value=f"{self.bet} 🪙", inline=True)
        
        if self.current_floor >= self.max_floors:
            embed.set_footer(text="🎉 You've reached the top! Congratulations!")
        elif not self.is_active and self.current_floor == 0:
            embed.set_footer(text="💥 Game Over! You hit a bomb on the first floor!")
        elif not self.is_active:
            embed.set_footer(text=f"💥 Game Over! You made it to floor {self.current_floor}!")
        else:
            embed.set_footer(text="Choose a column to climb or cash out!")
        
        return embed
