"""
Sulfur Bot - Horse Racing Game Module
Betting game where horses race and users can bet on winners.
"""

import discord
import random
import asyncio
from datetime import datetime, timezone
from modules.logger_utils import bot_logger as logger


# Horse data with names and emojis
HORSES = [
    {'name': 'Thunder', 'emoji': '🐎', 'color': discord.Color.dark_gold()},
    {'name': 'Lightning', 'emoji': '⚡', 'color': discord.Color.gold()},
    {'name': 'Storm', 'emoji': '🌩️', 'color': discord.Color.blue()},
    {'name': 'Blaze', 'emoji': '🔥', 'color': discord.Color.red()},
    {'name': 'Shadow', 'emoji': '🌑', 'color': discord.Color.dark_grey()},
    {'name': 'Spirit', 'emoji': '✨', 'color': discord.Color.purple()},
]

# Race track settings
RACE_LENGTH = 20  # Length of the race track
ANIMATION_FRAMES = 15  # Number of animation frames
FRAME_DELAY = 1.5  # Seconds between frames


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
        self.horses_count = min(max(horses_count, 2), 6)
        self.horses = HORSES[:self.horses_count]
        self.positions = [0] * self.horses_count  # Current positions
        self.finished = [False] * self.horses_count
        self.finish_order = []  # Order in which horses finish
        self.bets = {}  # {user_id: {'horse_index': int, 'amount': int}}
        self.is_racing = False
        self.is_betting_open = True
        self.created_at = datetime.now(timezone.utc)
    
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
    
    def get_odds(self, horse_index: int) -> float:
        """
        Calculate odds for a horse based on current bets.
        
        Args:
            horse_index: Index of the horse
        
        Returns:
            Odds multiplier (e.g., 2.5 means 2.5x payout)
        """
        # Count total bet on this horse
        horse_total = sum(
            bet['amount'] for bet in self.bets.values() 
            if bet['horse_index'] == horse_index
        )
        
        # Total pool
        total_pool = sum(bet['amount'] for bet in self.bets.values())
        
        if total_pool == 0 or horse_total == 0:
            return 2.0  # Default odds
        
        # Odds inversely proportional to bet amount
        # More popular horses have lower odds
        odds = (total_pool / horse_total) * 0.9  # House takes 10%
        
        # Clamp odds between 1.1x and 10x
        return max(1.1, min(10.0, odds))
    
    async def simulate_race(self):
        """
        Simulate the race progression.
        Updates positions for all horses.
        """
        self.is_racing = True
        self.is_betting_open = False
        
        while not all(self.finished):
            for i in range(self.horses_count):
                if not self.finished[i]:
                    # Random movement between 0-3 spaces
                    # Some horses have slight advantages (randomness)
                    move = random.randint(0, 3)
                    self.positions[i] += move
                    
                    # Check if finished
                    if self.positions[i] >= RACE_LENGTH:
                        self.positions[i] = RACE_LENGTH
                        self.finished[i] = True
                        self.finish_order.append(i)
            
            # Small delay for simulation
            await asyncio.sleep(0.1)
        
        return self.finish_order
    
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
            
            # Add horse name and position
            status = f"#{self.finish_order.index(i) + 1}" if i in self.finish_order else "Racing"
            line = f"{horse['name']:10} {track_str} {status}"
            lines.append(line)
        
        return '\n'.join(lines)
    
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
