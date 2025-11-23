"""
Sulfur Bot - Horse Racing Game Module
Betting game where horses race and users can bet on winners.
"""

import discord
import random
import asyncio
from datetime import datetime, timezone
from modules.logger_utils import bot_logger as logger


# Configuration
HOUSE_EDGE = 0.05  # 5% house edge (reduced for better payouts)
SIMULATED_BETS_MIN = 5  # Minimum number of simulated bets
SIMULATED_BETS_MAX = 15  # Maximum number of simulated bets
SIMULATED_BET_MIN = 10  # Minimum simulated bet amount
SIMULATED_BET_MAX = 100  # Maximum simulated bet amount

# Horse data with names, emojis, and abilities
# Includes horses inspired by Umamusume Pretty Derby (based on real racehorses)
HORSES = [
    # Original horses
    {'name': 'Thunder', 'emoji': '🐎', 'color': discord.Color.dark_gold()},
    {'name': 'Lightning', 'emoji': '⚡', 'color': discord.Color.gold()},
    {'name': 'Storm', 'emoji': '🌩️', 'color': discord.Color.blue()},
    {'name': 'Blaze', 'emoji': '🔥', 'color': discord.Color.red()},
    {'name': 'Shadow', 'emoji': '🌑', 'color': discord.Color.dark_grey()},
    {'name': 'Spirit', 'emoji': '✨', 'color': discord.Color.purple()},
    
    # Umamusume-inspired horses (based on real legendary racehorses)
    {'name': 'Special Week', 'emoji': '🏆', 'color': discord.Color.from_rgb(255, 182, 193)},
    {'name': 'Silence Suzuka', 'emoji': '🌸', 'color': discord.Color.from_rgb(255, 105, 180)},
    {'name': 'Tokai Teio', 'emoji': '👑', 'color': discord.Color.from_rgb(138, 43, 226)},
    {'name': 'Maruzensky', 'emoji': '🌟', 'color': discord.Color.from_rgb(0, 191, 255)},
    {'name': 'Oguri Cap', 'emoji': '🎩', 'color': discord.Color.from_rgb(72, 61, 139)},
    {'name': 'Gold Ship', 'emoji': '🚢', 'color': discord.Color.from_rgb(255, 215, 0)},
    {'name': 'Vodka', 'emoji': '💎', 'color': discord.Color.from_rgb(148, 0, 211)},
    {'name': 'Daiwa Scarlet', 'emoji': '🔴', 'color': discord.Color.from_rgb(220, 20, 60)},
    {'name': 'Taiki Shuttle', 'emoji': '🚀', 'color': discord.Color.from_rgb(30, 144, 255)},
    {'name': 'Mejiro McQueen', 'emoji': '🎭', 'color': discord.Color.from_rgb(75, 0, 130)},
    {'name': 'Rice Shower', 'emoji': '🌾', 'color': discord.Color.from_rgb(144, 238, 144)},
    {'name': 'El Condor Pasa', 'emoji': '🦅', 'color': discord.Color.from_rgb(184, 134, 11)},
    {'name': 'Grass Wonder', 'emoji': '🍀', 'color': discord.Color.from_rgb(34, 139, 34)},
    {'name': 'Haru Urara', 'emoji': '🌺', 'color': discord.Color.from_rgb(255, 20, 147)},
    {'name': 'Super Creek', 'emoji': '💧', 'color': discord.Color.from_rgb(0, 206, 209)},
    {'name': 'T.M. Opera O', 'emoji': '🎵', 'color': discord.Color.from_rgb(75, 0, 130)},
    {'name': 'Narita Brian', 'emoji': '⭐', 'color': discord.Color.from_rgb(255, 140, 0)},
    {'name': 'Symboli Rudolf', 'emoji': '🦌', 'color': discord.Color.from_rgb(139, 0, 0)},
    {'name': 'Air Groove', 'emoji': '🎸', 'color': discord.Color.from_rgb(106, 90, 205)},
    {'name': 'Agnes Tachyon', 'emoji': '⚗️', 'color': discord.Color.from_rgb(123, 104, 238)},
]

# Special abilities that can trigger during race
ABILITIES = {
    'speed_boost': {
        'name': 'Speed Boost',
        'emoji': '💨',
        'description': 'Gains extra speed!',
        'bonus_move': 2
    },
    'turbo': {
        'name': 'Turbo',
        'emoji': '⚡',
        'description': 'Lightning fast acceleration!',
        'bonus_move': 3
    },
    'comeback': {
        'name': 'Comeback',
        'emoji': '🔥',
        'description': 'Comeback from behind!',
        'bonus_move': 4,
        'requires_behind': True  # Only triggers when behind
    },
    'steady': {
        'name': 'Steady Pace',
        'emoji': '🎯',
        'description': 'Consistent performance',
        'bonus_move': 1,
        'always_triggers': True
    },
    'sprint': {
        'name': 'Final Sprint',
        'emoji': '🏃',
        'description': 'Sprint to the finish!',
        'bonus_move': 3,
        'requires_near_end': True  # Only triggers near finish line
    },
    'stumble': {
        'name': 'Stumble',
        'emoji': '💢',
        'description': 'Lost footing!',
        'bonus_move': -1,
        'is_negative': True
    },
    'leaders_edge': {
        'name': "Leader's Edge",
        'emoji': '👑',
        'description': 'Maintaining the lead!',
        'bonus_move': 2,
        'requires_leading': True  # Only triggers when in lead
    }
}

# Race track settings
RACE_LENGTH = 20  # Length of the race track
ANIMATION_FRAMES = 15  # Number of animation frames
FRAME_DELAY = 1.5  # Seconds between frames
ABILITY_TRIGGER_CHANCE = 0.3  # 30% chance per turn to trigger an ability

# Display settings for mobile compatibility
MAX_HORSE_NAME_LENGTH = 12  # Maximum characters before truncation
TRUNCATED_NAME_LENGTH = 11  # Length to truncate to (leaving room for ellipsis)


class HorseRace:
    """Manages a single horse race instance."""
    
    def __init__(self, race_id: int, horses_count: int = 6):
        """
        Initialize a horse race.
        
        Args:
            race_id: Unique race identifier
            horses_count: Number of horses in the race (2-6)
        """
        self.race_id = race_id
        # Ensure horses_count doesn't exceed available horses
        max_horses = min(len(HORSES), 6)
        self.horses_count = min(max(horses_count, 2), max_horses)
        # Randomly select horses from the full pool
        self.horses = random.sample(HORSES, self.horses_count)
        self.positions = [0] * self.horses_count  # Current positions
        self.finished = [False] * self.horses_count
        self.finish_order = []  # Order in which horses finish
        self.bets = {}  # {user_id: {'horse_index': int, 'amount': int}}
        self.simulated_bets = []  # List of simulated bets for better odds
        self.is_racing = False
        self.is_betting_open = True
        self.created_at = datetime.now(timezone.utc)
        self.ability_log = []  # Track ability triggers for display
        self.horse_abilities = {}  # Track which abilities each horse can use
    
    def place_bet(self, user_id: int, horse_index: int, amount: int) -> tuple:
        """
        Place a bet on a horse.
        
        Args:
            user_id: Discord user ID
            horse_index: Index of the horse to bet on (0-based)
            amount: Bet amount
        
        Returns:
            (success, message) tuple
        """
        if not self.is_betting_open:
            return False, "Die Wetten sind geschlossen!"
        
        if self.is_racing:
            return False, "Das Rennen läuft bereits!"
        
        if horse_index < 0 or horse_index >= self.horses_count:
            return False, "Ungültiges Pferd!"
        
        if amount <= 0:
            return False, "Wetteinsatz muss positiv sein!"
        
        # Update or place bet
        self.bets[user_id] = {
            'horse_index': horse_index,
            'amount': amount
        }
        
        horse_name = self.horses[horse_index]['name']
        return True, f"Wette platziert: {amount} 🪙 auf {horse_name}!"
    
    def add_simulated_bets(self):
        """
        Add simulated bets to make the race more exciting and improve payouts.
        This simulates other players betting on horses.
        """
        num_bets = random.randint(SIMULATED_BETS_MIN, SIMULATED_BETS_MAX)
        
        for _ in range(num_bets):
            horse_index = random.randint(0, self.horses_count - 1)
            amount = random.randint(SIMULATED_BET_MIN, SIMULATED_BET_MAX)
            
            self.simulated_bets.append({
                'horse_index': horse_index,
                'amount': amount
            })
        
        logger.info(f"Added {num_bets} simulated bets to race {self.race_id}")
    
    def get_odds(self, horse_index: int) -> float:
        """
        Calculate odds for a horse based on current bets (including simulated bets).
        
        Args:
            horse_index: Index of the horse
        
        Returns:
            Odds multiplier (e.g., 2.5 means 2.5x payout)
        """
        # Count total bet on this horse (player bets + simulated bets)
        horse_total = sum(
            bet['amount'] for bet in self.bets.values() 
            if bet['horse_index'] == horse_index
        )
        horse_total += sum(
            bet['amount'] for bet in self.simulated_bets
            if bet['horse_index'] == horse_index
        )
        
        # Total pool (player bets + simulated bets)
        total_pool = sum(bet['amount'] for bet in self.bets.values())
        total_pool += sum(bet['amount'] for bet in self.simulated_bets)
        
        if total_pool == 0 or horse_total == 0:
            return 2.5  # Default odds when no bets
        
        # Odds inversely proportional to bet amount
        # More popular horses have lower odds
        odds = (total_pool / horse_total) * (1 - HOUSE_EDGE)
        
        # Clamp odds between 1.2x and 15x (increased from 10x for better payouts)
        return max(1.2, min(15.0, odds))
    
    async def simulate_race(self):
        """
        Simulate the race progression with special abilities.
        Updates positions for all horses.
        """
        self.is_racing = True
        self.is_betting_open = False
        
        while not all(self.finished):
            for i in range(self.horses_count):
                if not self.finished[i]:
                    # Base random movement between 1-3 spaces
                    base_move = random.randint(1, 3)
                    bonus_move = 0
                    triggered_ability = None
                    
                    # Check if horse can trigger an ability
                    if random.random() < ABILITY_TRIGGER_CHANCE:
                        # Get available abilities based on position
                        available_abilities = self._get_available_abilities(i)
                        
                        if available_abilities:
                            # Randomly select an ability
                            ability_key = random.choice(available_abilities)
                            ability = ABILITIES[ability_key]
                            bonus_move = ability['bonus_move']
                            triggered_ability = ability
                            
                            # Log the ability trigger
                            horse_name = self.horses[i]['name']
                            self.ability_log.append({
                                'horse': horse_name,
                                'horse_index': i,
                                'ability': ability,
                                'position': self.positions[i]
                            })
                    
                    # Calculate total movement
                    total_move = max(0, base_move + bonus_move)
                    self.positions[i] += total_move
                    
                    # Check if finished
                    if self.positions[i] >= RACE_LENGTH:
                        self.positions[i] = RACE_LENGTH
                        self.finished[i] = True
                        self.finish_order.append(i)
            
            # Small delay for simulation
            await asyncio.sleep(0.1)
        
        return self.finish_order
    
    def _get_available_abilities(self, horse_index: int) -> list:
        """
        Get list of abilities that can trigger for this horse based on current position.
        
        Args:
            horse_index: Index of the horse
        
        Returns:
            List of ability keys that can trigger
        """
        available = []
        current_pos = self.positions[horse_index]
        
        # Determine position relative to other horses
        # Count horses ahead of this one (handling ties)
        horses_ahead = sum(1 for pos in self.positions if pos > current_pos)
        horse_rank = horses_ahead + 1  # 1-based rank
        
        is_leading = horse_rank <= 2  # Top 2 positions
        is_behind = horse_rank >= self.horses_count - 1  # Bottom 2 positions (rank N-1 or N)
        is_near_end = current_pos >= (RACE_LENGTH * 0.7)  # In last 30% of race
        
        for ability_key, ability in ABILITIES.items():
            can_trigger = True
            
            # Check position requirements
            if ability.get('requires_leading') and not is_leading:
                can_trigger = False
            
            if ability.get('requires_behind') and not is_behind:
                can_trigger = False
            
            if ability.get('requires_near_end') and not is_near_end:
                can_trigger = False
            
            if can_trigger:
                available.append(ability_key)
        
        return available
    
    def get_race_visual(self) -> str:
        """
        Generate ASCII visualization of the race.
        
        Returns:
            String representation of the race track
        """
        lines = []
        
        for i, horse in enumerate(self.horses):
            # Create track
            position = min(self.positions[i], RACE_LENGTH)
            track = ['─'] * RACE_LENGTH
            
            # Place horse
            if position < RACE_LENGTH:
                track[position] = horse['emoji']
            else:
                track[RACE_LENGTH - 1] = horse['emoji']
            
            # Add finish line
            track_str = ''.join(track) + '🏁'
            
            # Truncate long horse names to fit on mobile
            horse_name = horse['name']
            if len(horse_name) > MAX_HORSE_NAME_LENGTH:
                horse_name = horse_name[:TRUNCATED_NAME_LENGTH] + '…'
            
            # Add horse name and position
            status = f"#{self.finish_order.index(i) + 1}" if i in self.finish_order else "Racing"
            # Use fixed-width formatting with truncated name for better mobile display
            line = f"{horse_name:<{MAX_HORSE_NAME_LENGTH}} {track_str} {status}"
            lines.append(line)
        
        # Wrap in code block for monospace formatting on mobile
        return '```\n' + '\n'.join(lines) + '\n```'
    
    def get_ability_summary(self) -> str:
        """
        Get a summary of abilities triggered during the race.
        
        Returns:
            Formatted string of ability triggers
        """
        if not self.ability_log:
            return "No special abilities triggered during this race."
        
        # Group abilities by horse
        summary_lines = []
        horses_with_abilities = {}
        
        for log_entry in self.ability_log:
            horse = log_entry['horse']
            ability = log_entry['ability']
            
            if horse not in horses_with_abilities:
                horses_with_abilities[horse] = []
            
            horses_with_abilities[horse].append(ability)
        
        summary_lines.append("**Special Abilities Triggered:**")
        for horse, abilities in horses_with_abilities.items():
            ability_names = [f"{a['emoji']} {a['name']}" for a in abilities]
            summary_lines.append(f"• {horse}: {', '.join(ability_names)}")
        
        return '\n'.join(summary_lines)
    
    def calculate_payouts(self, db_helpers=None) -> dict:
        """
        Calculate payouts for all bettors.
        
        Returns:
            Dictionary of {user_id: payout_amount}
        """
        payouts = {}
        
        if not self.finish_order:
            return payouts
        
        winner_index = self.finish_order[0]
        winner_odds = self.get_odds(winner_index)
        
        for user_id, bet in self.bets.items():
            if bet['horse_index'] == winner_index:
                # Winner! Calculate payout
                payout = int(bet['amount'] * winner_odds)
                payouts[user_id] = payout
            else:
                # Loser
                payouts[user_id] = 0
        
        return payouts


async def initialize_horse_racing_table(db_helpers):
    """Initialize horse racing tables in the database."""
    try:
        if not db_helpers.db_pool:
            logger.error("Database pool not available")
            return
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            logger.error("Could not get database connection")
            return
        
        cursor = conn.cursor()
        try:
            # Table for race history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS horse_racing_history (
                    race_id INT AUTO_INCREMENT PRIMARY KEY,
                    winner_horse_index INT NOT NULL,
                    winner_name VARCHAR(50) NOT NULL,
                    total_bets INT DEFAULT 0,
                    total_pool BIGINT DEFAULT 0,
                    num_bettors INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_created (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Table for user bets
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS horse_racing_bets (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    race_id INT NOT NULL,
                    user_id BIGINT NOT NULL,
                    horse_index INT NOT NULL,
                    horse_name VARCHAR(50) NOT NULL,
                    bet_amount BIGINT NOT NULL,
                    payout BIGINT DEFAULT 0,
                    won BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_user (user_id),
                    INDEX idx_race (race_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Table for user stats
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS horse_racing_stats (
                    user_id BIGINT PRIMARY KEY,
                    total_races INT DEFAULT 0,
                    total_wins INT DEFAULT 0,
                    total_bet BIGINT DEFAULT 0,
                    total_won BIGINT DEFAULT 0,
                    best_payout BIGINT DEFAULT 0,
                    win_streak INT DEFAULT 0,
                    best_streak INT DEFAULT 0,
                    INDEX idx_wins (total_wins)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            conn.commit()
            logger.info("Horse racing tables initialized successfully")
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error initializing horse racing tables: {e}", exc_info=True)


async def save_race_result(db_helpers, race: HorseRace, payouts: dict):
    """
    Save race results to database.
    
    Args:
        db_helpers: Database helpers module
        race: HorseRace instance
        payouts: Dictionary of payouts
    """
    try:
        if not db_helpers.db_pool:
            return
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return
        
        cursor = conn.cursor()
        try:
            # Get winner info
            winner_index = race.finish_order[0]
            winner_name = race.horses[winner_index]['name']
            total_pool = sum(bet['amount'] for bet in race.bets.values())
            
            # Insert race history
            cursor.execute("""
                INSERT INTO horse_racing_history 
                (winner_horse_index, winner_name, total_bets, total_pool, num_bettors)
                VALUES (%s, %s, %s, %s, %s)
            """, (winner_index, winner_name, len(race.bets), total_pool, len(race.bets)))
            
            race_id = cursor.lastrowid
            
            # Insert individual bets
            for user_id, bet in race.bets.items():
                horse_name = race.horses[bet['horse_index']]['name']
                payout = payouts.get(user_id, 0)
                won = payout > 0
                
                cursor.execute("""
                    INSERT INTO horse_racing_bets
                    (race_id, user_id, horse_index, horse_name, bet_amount, payout, won)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (race_id, user_id, bet['horse_index'], horse_name, 
                      bet['amount'], payout, won))
                
                # Update user stats
                cursor.execute("""
                    INSERT INTO horse_racing_stats 
                    (user_id, total_races, total_wins, total_bet, total_won, best_payout)
                    VALUES (%s, 1, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        total_races = total_races + 1,
                        total_wins = total_wins + %s,
                        total_bet = total_bet + %s,
                        total_won = total_won + %s,
                        best_payout = GREATEST(best_payout, %s)
                """, (user_id, 1 if won else 0, bet['amount'], payout, payout,
                      1 if won else 0, bet['amount'], payout, payout))
            
            conn.commit()
            logger.info(f"Saved race {race_id} results")
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error saving race results: {e}", exc_info=True)


async def get_user_stats(db_helpers, user_id: int) -> dict:
    """
    Get horse racing stats for a user.
    
    Args:
        db_helpers: Database helpers module
        user_id: Discord user ID
    
    Returns:
        Dictionary with stats or None
    """
    try:
        if not db_helpers.db_pool:
            return None
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return None
        
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT * FROM horse_racing_stats
                WHERE user_id = %s
            """, (user_id,))
            
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error getting user stats: {e}", exc_info=True)
        return None
