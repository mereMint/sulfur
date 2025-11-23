"""
Sulfur Bot - RPG System Module (Foundation)
Core RPG system with combat, items, skills, and progression.
"""

import discord
import random
import json
from datetime import datetime, timezone
from typing import Optional, Dict, List, Tuple
from modules.logger_utils import bot_logger as logger


# Status Effects - Applied during combat
# These can be used by both players (via items/skills) and monsters (via abilities)
STATUS_EFFECTS = {
    'burn': {
        'name': 'Brennen', 
        'emoji': '🔥', 
        'dmg_per_turn': 5, 
        'duration': 3,
        'description': 'Nimmt 5 Schaden pro Runde für 3 Runden'
    },
    'poison': {
        'name': 'Vergiftung', 
        'emoji': '🧪', 
        'dmg_per_turn': 7, 
        'duration': 4,
        'description': 'Nimmt 7 Schaden pro Runde für 4 Runden'
    },
    'darkness': {
        'name': 'Dunkelheit', 
        'emoji': '🌑', 
        'acc_reduction': 0.3, 
        'duration': 2,
        'description': 'Reduziert Trefferchance um 30% für 2 Runden'
    },
    'light': {
        'name': 'Licht', 
        'emoji': '✨', 
        'acc_bonus': 0.2, 
        'duration': 3,
        'description': 'Erhöht Trefferchance um 20% für 3 Runden'
    },
    'static': {
        'name': 'Statisch', 
        'emoji': '⚡', 
        'paralyze_chance': 0.3, 
        'duration': 2,
        'description': '30% Chance pro Runde gelähmt zu werden für 2 Runden'
    },
    'freeze': {
        'name': 'Gefroren', 
        'emoji': '❄️', 
        'immobilize': True, 
        'duration': 1,
        'description': 'Kann für 1 Runde nicht handeln'
    },
    'heal': {
        'name': 'Regeneration', 
        'emoji': '💚', 
        'heal_per_turn': 10, 
        'duration': 3,
        'description': 'Heilt 10 HP pro Runde für 3 Runden'
    },
    'shield': {
        'name': 'Schild', 
        'emoji': '🛡️', 
        'dmg_reduction': 0.5, 
        'duration': 2,
        'description': 'Reduziert eingehenden Schaden um 50% für 2 Runden'
    },
    'rage': {
        'name': 'Wut', 
        'emoji': '😡', 
        'atk_bonus': 0.5, 
        'def_reduction': 0.3, 
        'duration': 2,
        'description': 'Erhöht Angriff um 50%, reduziert Verteidigung um 30% für 2 Runden'
    }
}

# Monster Abilities - Special abilities that can be assigned to monsters
# These are triggered during combat and can apply status effects or modify combat
MONSTER_ABILITIES = {
    'fire_breath': {
        'name': 'Feueratem',
        'emoji': '🔥',
        'description': 'Speit Flammen und verursacht brennenden Schaden',
        'effect_type': 'status',
        'status_effect': 'burn',
        'trigger_chance': 0.3
    },
    'poison_spit': {
        'name': 'Giftspeier',
        'emoji': '🧪',
        'description': 'Spuckt Gift und vergiftet das Ziel',
        'effect_type': 'status',
        'status_effect': 'poison',
        'trigger_chance': 0.25
    },
    'shadow_cloak': {
        'name': 'Schattenumhang',
        'emoji': '🌑',
        'description': 'Hüllt sich in Schatten und erschwert das Treffen',
        'effect_type': 'status',
        'status_effect': 'darkness',
        'trigger_chance': 0.2
    },
    'lightning_strike': {
        'name': 'Blitzschlag',
        'emoji': '⚡',
        'description': 'Schlägt mit Blitzen zu und kann lähmen',
        'effect_type': 'status',
        'status_effect': 'static',
        'trigger_chance': 0.3
    },
    'frost_nova': {
        'name': 'Frostnova',
        'emoji': '❄️',
        'description': 'Erzeugt eisige Kälte und friert das Ziel ein',
        'effect_type': 'status',
        'status_effect': 'freeze',
        'trigger_chance': 0.15
    },
    'battle_roar': {
        'name': 'Kriegsschrei',
        'emoji': '😡',
        'description': 'Brüllt wütend und erhöht die eigene Stärke',
        'effect_type': 'status',
        'status_effect': 'rage',
        'trigger_chance': 0.25
    },
    'regeneration': {
        'name': 'Regeneration',
        'emoji': '💚',
        'description': 'Heilt sich selbst über mehrere Runden',
        'effect_type': 'status',
        'status_effect': 'heal',
        'trigger_chance': 0.2
    },
    'armor_up': {
        'name': 'Panzerung',
        'emoji': '🛡️',
        'description': 'Verstärkt die Rüstung und reduziert Schaden',
        'effect_type': 'status',
        'status_effect': 'shield',
        'trigger_chance': 0.2
    },
    'critical_strike': {
        'name': 'Kritischer Schlag',
        'emoji': '💥',
        'description': 'Führt einen verheerenden kritischen Angriff aus',
        'effect_type': 'damage_boost',
        'damage_multiplier': 2.5,
        'trigger_chance': 0.2
    },
    'life_drain': {
        'name': 'Lebensentzug',
        'emoji': '🩸',
        'description': 'Stiehlt Leben vom Ziel und heilt sich selbst',
        'effect_type': 'lifesteal',
        'lifesteal_percent': 0.5,
        'trigger_chance': 0.25
    }
}

# Skill Tree System
# Players can unlock passive abilities and active skills using skill points
SKILL_TREE = {
    # Warrior Path - Focuses on strength and defense
    'warrior': {
        'name': 'Krieger',
        'emoji': '⚔️',
        'description': 'Meister des Nahkampfs und der Verteidigung',
        'skills': {
            'heavy_strike': {
                'name': 'Schwerer Schlag',
                'type': 'passive',
                'description': '+10% Schaden mit Waffen',
                'cost': 1,
                'requires': None,
                'effect': {'damage_bonus': 0.10}
            },
            'iron_skin': {
                'name': 'Eisenhaut',
                'type': 'passive',
                'description': '+5 Verteidigung',
                'cost': 1,
                'requires': None,
                'effect': {'defense_bonus': 5}
            },
            'berserker': {
                'name': 'Berserker',
                'type': 'passive',
                'description': '+20% Schaden, -10% Verteidigung',
                'cost': 2,
                'requires': 'heavy_strike',
                'effect': {'damage_bonus': 0.20, 'defense_penalty': 0.10}
            },
            'shield_master': {
                'name': 'Schildmeister',
                'type': 'passive',
                'description': '+15 Verteidigung, +10% HP',
                'cost': 2,
                'requires': 'iron_skin',
                'effect': {'defense_bonus': 15, 'health_bonus': 0.10}
            },
            'battle_cry': {
                'name': 'Schlachtruf',
                'type': 'active',
                'description': 'Erhöht Angriff für 3 Runden',
                'cost': 2,
                'requires': 'berserker',
                'effect': {'attack_buff': 0.30, 'duration': 3}
            }
        }
    },
    
    # Rogue Path - Focuses on dexterity and critical hits
    'rogue': {
        'name': 'Schurke',
        'emoji': '🗡️',
        'description': 'Meister der Geschicklichkeit und kritischen Treffer',
        'skills': {
            'swift_strikes': {
                'name': 'Schnelle Schläge',
                'type': 'passive',
                'description': '+5 Geschwindigkeit',
                'cost': 1,
                'requires': None,
                'effect': {'speed_bonus': 5}
            },
            'keen_eye': {
                'name': 'Scharfes Auge',
                'type': 'passive',
                'description': '+10% Kritische Trefferchance',
                'cost': 1,
                'requires': None,
                'effect': {'crit_chance_bonus': 0.10}
            },
            'assassin': {
                'name': 'Assassine',
                'type': 'passive',
                'description': '+25% Kritischer Schaden',
                'cost': 2,
                'requires': 'keen_eye',
                'effect': {'crit_damage_bonus': 0.25}
            },
            'shadow_step': {
                'name': 'Schattenschritt',
                'type': 'passive',
                'description': '+15% Ausweichen',
                'cost': 2,
                'requires': 'swift_strikes',
                'effect': {'dodge_bonus': 0.15}
            },
            'backstab': {
                'name': 'Meucheln',
                'type': 'active',
                'description': 'Garantierter kritischer Treffer',
                'cost': 3,
                'requires': 'assassin',
                'effect': {'guaranteed_crit': True, 'crit_multiplier': 2.0}
            }
        }
    },
    
    # Mage Path - Focuses on magic and special effects
    'mage': {
        'name': 'Magier',
        'emoji': '🔮',
        'description': 'Meister der arkanen Künste und Elemente',
        'skills': {
            'arcane_power': {
                'name': 'Arkane Kraft',
                'type': 'passive',
                'description': '+15% Skill-Schaden',
                'cost': 1,
                'requires': None,
                'effect': {'skill_damage_bonus': 0.15}
            },
            'mana_shield': {
                'name': 'Manaschild',
                'type': 'passive',
                'description': '+10% Schadensreduzierung',
                'cost': 1,
                'requires': None,
                'effect': {'damage_reduction': 0.10}
            },
            'elemental_master': {
                'name': 'Elementarmeister',
                'type': 'passive',
                'description': '+30% Elementarschaden',
                'cost': 2,
                'requires': 'arcane_power',
                'effect': {'elemental_damage_bonus': 0.30}
            },
            'arcane_barrier': {
                'name': 'Arkane Barriere',
                'type': 'passive',
                'description': '+20% Schadensreduzierung',
                'cost': 2,
                'requires': 'mana_shield',
                'effect': {'damage_reduction': 0.20}
            },
            'meteor': {
                'name': 'Meteor',
                'type': 'active',
                'description': 'Gewaltiger Elementarschaden',
                'cost': 3,
                'requires': 'elemental_master',
                'effect': {'base_damage': 80, 'element': 'fire'}
            }
        }
    }
}

# Item Rarities
RARITIES = ['common', 'uncommon', 'rare', 'epic', 'legendary']
RARITY_COLORS = {
    'common': discord.Color.light_grey(),
    'uncommon': discord.Color.green(),
    'rare': discord.Color.blue(),
    'epic': discord.Color.purple(),
    'legendary': discord.Color.gold()
}

# Worlds
WORLDS = {
    'overworld': {'name': 'Oberwelt', 'min_level': 1, 'max_level': 10},
    'underworld': {'name': 'Unterwelt', 'min_level': 10, 'max_level': 50}
}

# Game Balance Constants
BASE_STAT_VALUE = 10  # Base value for all stats (strength, dexterity, defense, speed)
LEVEL_REWARD_MULTIPLIER = 0.1  # Multiplier for scaling rewards based on player level
RESPEC_COST_PER_POINT = 50  # Gold cost per skill point when resetting stats


async def initialize_rpg_tables(db_helpers):
    """Initialize RPG system tables."""
    try:
        if not db_helpers.db_pool:
            logger.error("Database pool not available")
            return
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return
        
        cursor = conn.cursor()
        try:
            # Player profiles
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rpg_players (
                    user_id BIGINT PRIMARY KEY,
                    level INT DEFAULT 1,
                    xp BIGINT DEFAULT 0,
                    health INT DEFAULT 100,
                    max_health INT DEFAULT 100,
                    strength INT DEFAULT 10,
                    dexterity INT DEFAULT 10,
                    defense INT DEFAULT 10,
                    speed INT DEFAULT 10,
                    skill_points INT DEFAULT 0,
                    world VARCHAR(50) DEFAULT 'overworld',
                    gold BIGINT DEFAULT 100,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_adventure TIMESTAMP NULL,
                    INDEX idx_level (level),
                    INDEX idx_world (world)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Inventory
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rpg_inventory (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    item_id INT NOT NULL,
                    item_type VARCHAR(50) NOT NULL,
                    quantity INT DEFAULT 1,
                    UNIQUE KEY unique_user_item (user_id, item_id, item_type),
                    INDEX idx_user (user_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Equipment
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rpg_equipped (
                    user_id BIGINT PRIMARY KEY,
                    weapon_id INT NULL,
                    skill1_id INT NULL,
                    skill2_id INT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Skill tree unlocks
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rpg_skill_tree (
                    user_id BIGINT NOT NULL,
                    skill_path VARCHAR(50) NOT NULL,
                    skill_key VARCHAR(100) NOT NULL,
                    unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, skill_path, skill_key),
                    INDEX idx_user (user_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Items/Weapons/Skills master table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rpg_items (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    type VARCHAR(50) NOT NULL,
                    rarity VARCHAR(20) DEFAULT 'common',
                    description TEXT,
                    effects JSON,
                    damage INT DEFAULT 0,
                    damage_type VARCHAR(50) NULL,
                    durability INT DEFAULT 100,
                    price INT DEFAULT 100,
                    required_level INT DEFAULT 1,
                    created_by BIGINT NULL,
                    INDEX idx_type (type),
                    INDEX idx_rarity (rarity)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Monsters
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rpg_monsters (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    world VARCHAR(50) DEFAULT 'overworld',
                    level INT DEFAULT 1,
                    health INT DEFAULT 50,
                    strength INT DEFAULT 5,
                    defense INT DEFAULT 5,
                    speed INT DEFAULT 5,
                    xp_reward INT DEFAULT 10,
                    gold_reward INT DEFAULT 10,
                    loot_table JSON,
                    spawn_rate FLOAT DEFAULT 1.0,
                    abilities JSON,
                    INDEX idx_world (world),
                    INDEX idx_level (level)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Monster abilities reference table (for documentation and easy access)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rpg_monster_abilities (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    ability_key VARCHAR(50) UNIQUE NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    effect_type VARCHAR(50),
                    effect_value JSON,
                    INDEX idx_ability_key (ability_key)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            conn.commit()
            logger.info("RPG tables initialized successfully")
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error initializing RPG tables: {e}", exc_info=True)


async def get_player_profile(db_helpers, user_id: int):
    """Get or create player profile."""
    try:
        if not db_helpers.db_pool:
            return None
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return None
        
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM rpg_players WHERE user_id = %s", (user_id,))
            player = cursor.fetchone()
            
            if not player:
                # Create new player
                cursor.execute("""
                    INSERT INTO rpg_players (user_id) VALUES (%s)
                """, (user_id,))
                conn.commit()
                
                cursor.execute("SELECT * FROM rpg_players WHERE user_id = %s", (user_id,))
                player = cursor.fetchone()
            
            return player
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error getting player profile: {e}", exc_info=True)
        return None


def calculate_xp_for_level(level: int) -> int:
    """Calculate XP required for a level."""
    # Cap at level 100 to prevent extreme calculations
    capped_level = min(level, 100)
    return int(100 * (1.5 ** (capped_level - 1)))


async def gain_xp(db_helpers, user_id: int, xp_amount: int):
    """Award XP and handle level ups."""
    try:
        player = await get_player_profile(db_helpers, user_id)
        if not player:
            return None
        
        new_xp = player['xp'] + xp_amount
        current_level = player['level']
        new_level = current_level
        skill_points_gained = 0
        
        # Check for level ups
        while new_xp >= calculate_xp_for_level(new_level + 1):
            new_level += 1
            skill_points_gained += 5
        
        # Update player
        conn = db_helpers.db_pool.get_connection()
        cursor = conn.cursor()
        
        if new_level > current_level:
            # Level up! Increase stats
            hp_increase = 20 * (new_level - current_level)
            cursor.execute("""
                UPDATE rpg_players 
                SET level = %s, xp = %s, skill_points = skill_points + %s,
                    max_health = max_health + %s, health = max_health + %s
                WHERE user_id = %s
            """, (new_level, new_xp, skill_points_gained, hp_increase, hp_increase, user_id))
        else:
            cursor.execute("""
                UPDATE rpg_players SET xp = %s WHERE user_id = %s
            """, (new_xp, user_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return {
            'leveled_up': new_level > current_level,
            'old_level': current_level,
            'new_level': new_level,
            'skill_points': skill_points_gained
        }
    except Exception as e:
        logger.error(f"Error gaining XP: {e}", exc_info=True)
        return None


# Default Monsters with abilities
DEFAULT_MONSTERS = [
    # Overworld monsters (Level 1-10)
    {'name': 'Schleimling', 'world': 'overworld', 'level': 1, 'health': 30, 'strength': 3, 'defense': 2, 'speed': 5, 'xp_reward': 15, 'gold_reward': 10, 'abilities': ['poison_spit']},
    {'name': 'Goblin', 'world': 'overworld', 'level': 2, 'health': 45, 'strength': 5, 'defense': 3, 'speed': 6, 'xp_reward': 25, 'gold_reward': 20, 'abilities': ['critical_strike']},
    {'name': 'Wilder Wolf', 'world': 'overworld', 'level': 3, 'health': 60, 'strength': 7, 'defense': 4, 'speed': 10, 'xp_reward': 35, 'gold_reward': 25, 'abilities': ['battle_roar']},
    {'name': 'Skelett-Krieger', 'world': 'overworld', 'level': 4, 'health': 70, 'strength': 9, 'defense': 6, 'speed': 7, 'xp_reward': 50, 'gold_reward': 35, 'abilities': ['armor_up']},
    {'name': 'Ork-Schläger', 'world': 'overworld', 'level': 5, 'health': 90, 'strength': 12, 'defense': 8, 'speed': 6, 'xp_reward': 65, 'gold_reward': 50, 'abilities': ['battle_roar', 'critical_strike']},
    {'name': 'Dunkler Magier', 'world': 'overworld', 'level': 6, 'health': 80, 'strength': 15, 'defense': 5, 'speed': 9, 'xp_reward': 80, 'gold_reward': 60, 'abilities': ['shadow_cloak', 'life_drain']},
    {'name': 'Troll', 'world': 'overworld', 'level': 7, 'health': 120, 'strength': 16, 'defense': 12, 'speed': 4, 'xp_reward': 100, 'gold_reward': 75, 'abilities': ['regeneration', 'armor_up']},
    {'name': 'Geist', 'world': 'overworld', 'level': 8, 'health': 100, 'strength': 18, 'defense': 8, 'speed': 12, 'xp_reward': 120, 'gold_reward': 85, 'abilities': ['shadow_cloak', 'life_drain']},
    {'name': 'Oger', 'world': 'overworld', 'level': 9, 'health': 150, 'strength': 20, 'defense': 15, 'speed': 5, 'xp_reward': 150, 'gold_reward': 100, 'abilities': ['battle_roar', 'critical_strike', 'regeneration']},
    {'name': 'Drache (Jung)', 'world': 'overworld', 'level': 10, 'health': 180, 'strength': 25, 'defense': 18, 'speed': 10, 'xp_reward': 200, 'gold_reward': 150, 'abilities': ['fire_breath', 'critical_strike']},
    
    # Underworld monsters (Level 10+)
    {'name': 'Dämon', 'world': 'underworld', 'level': 12, 'health': 220, 'strength': 30, 'defense': 20, 'speed': 12, 'xp_reward': 300, 'gold_reward': 200, 'abilities': ['fire_breath', 'life_drain', 'battle_roar']},
    {'name': 'Höllenhund', 'world': 'underworld', 'level': 14, 'health': 250, 'strength': 35, 'defense': 22, 'speed': 15, 'xp_reward': 400, 'gold_reward': 250, 'abilities': ['fire_breath', 'critical_strike']},
    {'name': 'Schattenbestie', 'world': 'underworld', 'level': 16, 'health': 280, 'strength': 40, 'defense': 25, 'speed': 14, 'xp_reward': 500, 'gold_reward': 300, 'abilities': ['shadow_cloak', 'poison_spit', 'life_drain']},
    {'name': 'Todesritter', 'world': 'underworld', 'level': 18, 'health': 320, 'strength': 45, 'defense': 30, 'speed': 11, 'xp_reward': 650, 'gold_reward': 400, 'abilities': ['frost_nova', 'armor_up', 'critical_strike']},
    {'name': 'Drache (Erwachsen)', 'world': 'underworld', 'level': 20, 'health': 400, 'strength': 50, 'defense': 35, 'speed': 13, 'xp_reward': 800, 'gold_reward': 500, 'abilities': ['fire_breath', 'lightning_strike', 'critical_strike', 'regeneration']},
]


async def initialize_default_monsters(db_helpers):
    """Initialize default monsters in the database."""
    try:
        if not db_helpers.db_pool:
            return
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return
        
        cursor = conn.cursor()
        try:
            # Check if monsters exist
            cursor.execute("SELECT COUNT(*) FROM rpg_monsters")
            count = cursor.fetchone()[0]
            
            if count == 0:
                # Insert default monsters with abilities
                for monster in DEFAULT_MONSTERS:
                    abilities_json = json.dumps(monster.get('abilities', []))
                    cursor.execute("""
                        INSERT INTO rpg_monsters 
                        (name, world, level, health, strength, defense, speed, xp_reward, gold_reward, abilities)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (monster['name'], monster['world'], monster['level'], monster['health'],
                          monster['strength'], monster['defense'], monster['speed'],
                          monster['xp_reward'], monster['gold_reward'], abilities_json))
                
                conn.commit()
                logger.info(f"Initialized {len(DEFAULT_MONSTERS)} default monsters")
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error initializing default monsters: {e}", exc_info=True)


async def get_random_monster(db_helpers, player_level: int, world: str):
    """
    Get a random monster appropriate for player level and world.
    Monster stats are varied by ±10-20% from base values for variety.
    """
    try:
        if not db_helpers.db_pool:
            return None
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return None
        
        cursor = conn.cursor(dictionary=True)
        try:
            # Get monsters within 2 levels of player
            min_level = max(1, player_level - 1)
            max_level = player_level + 2
            
            cursor.execute("""
                SELECT * FROM rpg_monsters
                WHERE world = %s AND level BETWEEN %s AND %s
                ORDER BY RAND()
                LIMIT 1
            """, (world, min_level, max_level))
            
            monster = cursor.fetchone()
            
            if monster:
                # Add stat variations (±15-20% from base stats)
                # Note: Variation is asymmetric - monsters can be 15% weaker or 20% stronger
                # This makes encounters slightly more challenging on average
                variation_min = 0.85  # -15%
                variation_max = 1.20  # +20%
                
                # Store original stats as 'base_stats' before variation
                monster['base_health'] = monster['health']
                monster['base_strength'] = monster['strength']
                monster['base_defense'] = monster['defense']
                monster['base_speed'] = monster['speed']
                
                # Apply random variations to each stat
                monster['health'] = int(monster['health'] * random.uniform(variation_min, variation_max))
                monster['strength'] = int(monster['strength'] * random.uniform(variation_min, variation_max))
                monster['defense'] = int(monster['defense'] * random.uniform(variation_min, variation_max))
                monster['speed'] = int(monster['speed'] * random.uniform(variation_min, variation_max))
                
                # Store max health for combat
                monster['max_health'] = monster['health']
                
                # Parse abilities JSON if present
                if monster.get('abilities'):
                    if isinstance(monster['abilities'], str):
                        monster['abilities'] = json.loads(monster['abilities'])
                else:
                    monster['abilities'] = []
                
                logger.debug(f"Generated monster: {monster['name']} (Level {monster['level']}) with varied stats")
            
            return monster
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error getting random monster: {e}", exc_info=True)
        return None


def calculate_damage(attacker_str: int, defender_def: int, attacker_dex: int, is_ai: bool = False, player_health_pct: float = 1.0) -> dict:
    """
    Calculate damage with dodge/miss/crit mechanics.
    Enhanced AI makes smarter decisions based on situation.
    
    Args:
        attacker_str: Attacker's strength
        defender_def: Defender's defense
        attacker_dex: Attacker's dexterity
        is_ai: Whether this is an AI attacker (for smarter behavior)
        player_health_pct: Player's current health percentage (for AI decision-making)
    
    Returns:
        dict with 'damage', 'hit', 'crit', 'dodged' keys
    """
    result = {
        'damage': 0,
        'hit': False,
        'crit': False,
        'dodged': False
    }
    
    # Base hit chance: 85% + (dex / 100)
    hit_chance = 0.85 + (attacker_dex / 100.0)
    
    # AI gets bonus accuracy when player is low health (aggressive finish)
    if is_ai and player_health_pct < 0.3:
        hit_chance += 0.1
    
    hit_chance = min(0.95, hit_chance)  # Cap at 95%
    
    # Check if attack hits
    if random.random() > hit_chance:
        result['dodged'] = True
        return result
    
    result['hit'] = True
    
    # Calculate base damage
    base_damage = attacker_str - (defender_def // 2)
    base_damage = max(1, base_damage)  # Minimum 1 damage
    
    # Add variance (80% - 120%)
    variance = random.uniform(0.8, 1.2)
    damage = int(base_damage * variance)
    
    # Critical hit chance: 10% + (dex / 200)
    crit_chance = 0.10 + (attacker_dex / 200.0)
    
    # AI has higher crit chance when player is low health
    if is_ai and player_health_pct < 0.3:
        crit_chance += 0.15
    
    crit_chance = min(0.30, crit_chance)  # Cap at 30%
    
    if random.random() < crit_chance:
        result['crit'] = True
        damage = int(damage * 1.5)  # 150% damage on crit
    
    result['damage'] = damage
    return result


async def start_adventure(db_helpers, user_id: int, continue_chain: bool = False):
    """
    Start an adventure encounter (combat or non-combat).
    
    Args:
        continue_chain: If True, allows continuing an adventure chain
    """
    try:
        player = await get_player_profile(db_helpers, user_id)
        if not player:
            return None, "Profil konnte nicht geladen werden.", None
        
        # Check cooldown only if not continuing a chain
        if not continue_chain and player['last_adventure']:
            last_adv = player['last_adventure']
            
            # Convert to datetime with UTC timezone if needed
            if isinstance(last_adv, str):
                # Parse ISO format string
                last_adv = datetime.fromisoformat(last_adv.replace('Z', '+00:00'))
            elif isinstance(last_adv, datetime):
                # Ensure it has timezone info (assume UTC if not specified)
                if last_adv.tzinfo is None:
                    last_adv = last_adv.replace(tzinfo=timezone.utc)
            else:
                # Unknown type, log and skip cooldown check
                logger.warning(f"Unknown last_adventure type: {type(last_adv)}")
                last_adv = None
            
            if last_adv:
                # Calculate cooldown - ensure both datetimes have timezone info
                now = datetime.now(timezone.utc)
                cooldown = now - last_adv
                cooldown_seconds = cooldown.total_seconds()
                
                logger.debug(f"Adventure cooldown check: now={now}, last={last_adv}, diff={cooldown_seconds}s")
                
                if cooldown_seconds < 120:  # 2 minutes
                    remaining = 120 - int(cooldown_seconds)
                    return None, f"Du musst noch {remaining} Sekunden warten!", None
        
        # Check if player has enough health
        if player['health'] < player['max_health'] * 0.2:  # Less than 20% health
            return None, "Du bist zu schwach! Heile dich zuerst.", None
        
        # Update last adventure time only if starting a new chain
        if not continue_chain:
            conn = db_helpers.db_pool.get_connection()
            cursor = conn.cursor()
            # Use UTC_TIMESTAMP() to ensure consistent UTC time storage
            cursor.execute("""
                UPDATE rpg_players SET last_adventure = UTC_TIMESTAMP() WHERE user_id = %s
            """, (user_id,))
            conn.commit()
            cursor.close()
            conn.close()
        
        # 70% chance for combat, 30% for non-combat event
        encounter_type = 'combat' if random.random() < 0.7 else 'event'
        
        if encounter_type == 'combat':
            # Get a random monster
            monster = await get_random_monster(db_helpers, player['level'], player['world'])
            if not monster:
                return None, "Kein Monster gefunden.", None
            
            # Track that this is part of an adventure (for chain support)
            monster['can_continue'] = random.random() < 0.4  # 40% chance to continue adventure
            return monster, None, 'combat'
        else:
            # Generate non-combat event
            event = generate_adventure_event(player)
            event['can_continue'] = random.random() < 0.3  # 30% chance to continue after event
            return event, None, 'event'
            
    except Exception as e:
        logger.error(f"Error starting adventure: {e}", exc_info=True)
        return None, "Ein Fehler ist aufgetreten.", None


def generate_adventure_event(player: dict) -> dict:
    """Generate a random non-combat adventure event."""
    events = [
        {
            'type': 'treasure',
            'title': '💎 Versteckte Schatzkiste!',
            'description': 'Du entdeckst eine alte Schatzkiste am Wegrand!',
            'gold_reward': random.randint(50, 200),
            'xp_reward': random.randint(20, 50),
        },
        {
            'type': 'merchant',
            'title': '🎒 Reisender Händler',
            'description': 'Ein freundlicher Händler bietet dir einen Handel an. Er gibt dir etwas Gold für deine Hilfe.',
            'gold_reward': random.randint(30, 100),
            'xp_reward': random.randint(10, 30),
        },
        {
            'type': 'shrine',
            'title': '✨ Mystischer Schrein',
            'description': 'Du findest einen alten Schrein, der deine Wunden heilt.',
            'heal_amount': random.randint(20, 50),
            'xp_reward': random.randint(15, 40),
        },
        {
            'type': 'puzzle',
            'title': '🧩 Altes Rätsel',
            'description': 'Du stolperst über eine alte Steintafel mit einem Rätsel. Nach einigem Nachdenken löst du es!',
            'gold_reward': random.randint(75, 150),
            'xp_reward': random.randint(30, 60),
        },
        {
            'type': 'npc',
            'title': '👤 Hilfsbedürftiger Reisender',
            'description': 'Ein Reisender braucht Hilfe und belohnt dich dafür.',
            'gold_reward': random.randint(40, 120),
            'xp_reward': random.randint(25, 55),
        },
        {
            'type': 'fountain',
            'title': '⛲ Magischer Brunnen',
            'description': 'Du findest einen magischen Brunnen. Das Wasser stärkt dich!',
            'heal_amount': random.randint(30, 70),
            'xp_reward': random.randint(20, 45),
        },
        {
            'type': 'cave',
            'title': '🕳️ Verborgene Höhle',
            'description': 'Du entdeckst eine versteckte Höhle mit wertvollen Kristallen!',
            'gold_reward': random.randint(100, 250),
            'xp_reward': random.randint(35, 70),
        },
        {
            'type': 'ruins',
            'title': '🏛️ Alte Ruinen',
            'description': 'In den Ruinen einer vergessenen Zivilisation findest du Artefakte.',
            'gold_reward': random.randint(80, 180),
            'xp_reward': random.randint(40, 65),
        },
        {
            'type': 'training',
            'title': '⚔️ Kampftraining',
            'description': 'Ein erfahrener Krieger bietet dir Training an. Du lernst viel!',
            'xp_reward': random.randint(60, 100),
        },
        {
            'type': 'blessing',
            'title': '🌟 Göttlicher Segen',
            'description': 'Ein Gott gewährt dir seinen Segen! Du fühlst dich gestärkt.',
            'heal_amount': random.randint(50, 100),
            'gold_reward': random.randint(50, 150),
            'xp_reward': random.randint(45, 80),
        },
    ]
    
    # Select random event
    event = random.choice(events).copy()
    
    # Scale rewards based on player level
    level_multiplier = 1 + (player['level'] * LEVEL_REWARD_MULTIPLIER)
    if 'gold_reward' in event:
        event['gold_reward'] = int(event['gold_reward'] * level_multiplier)
    if 'xp_reward' in event:
        event['xp_reward'] = int(event['xp_reward'] * level_multiplier)
    if 'heal_amount' in event:
        event['heal_amount'] = min(event['heal_amount'], player['max_health'] - player['health'])
    
    return event


async def claim_adventure_event(db_helpers, user_id: int, event: dict):
    """Claim rewards from a non-combat adventure event."""
    try:
        if not db_helpers.db_pool:
            return False, "Datenbank nicht verfügbar"
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return False, "Datenbankverbindung fehlgeschlagen"
        
        cursor = conn.cursor()
        try:
            # Award gold
            if 'gold_reward' in event:
                cursor.execute("""
                    UPDATE rpg_players SET gold = gold + %s WHERE user_id = %s
                """, (event['gold_reward'], user_id))
            
            # Award XP
            if 'xp_reward' in event:
                xp_result = await gain_xp(db_helpers, user_id, event['xp_reward'])
                event['leveled_up'] = xp_result and xp_result.get('leveled_up', False)
                event['new_level'] = xp_result.get('new_level') if event.get('leveled_up') else None
            
            # Heal player
            if 'heal_amount' in event and event['heal_amount'] > 0:
                cursor.execute("""
                    UPDATE rpg_players SET health = LEAST(health + %s, max_health) WHERE user_id = %s
                """, (event['heal_amount'], user_id))
            
            conn.commit()
            return True, "Belohnungen erhalten!"
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error claiming adventure event: {e}", exc_info=True)
        return False, str(e)


async def get_combat_timeline(player: dict, monster: dict) -> list:
    """
    Calculate combat turn order based on speed.
    Returns a list of combatants in order from fastest to slowest.
    
    Returns:
        List of dicts with 'name', 'speed', 'type' (player/monster), 'emoji'
    """
    timeline = [
        {
            'name': 'You',
            'speed': player['speed'],
            'type': 'player',
            'emoji': '🛡️',
            'health_pct': (player['health'] / player['max_health']) * 100
        },
        {
            'name': monster['name'],
            'speed': monster['speed'],
            'type': 'monster',
            'emoji': '👹',
            'health_pct': (monster['health'] / monster.get('max_health', monster['health'])) * 100
        }
    ]
    
    # Sort by speed (highest first)
    timeline.sort(key=lambda x: x['speed'], reverse=True)
    
    return timeline


async def process_combat_turn(db_helpers, user_id: int, monster: dict, action: str):
    """
    Process a single combat turn.
    
    Args:
        action: 'attack', 'run', or item/skill usage
    
    Returns:
        dict with combat results
    """
    try:
        player = await get_player_profile(db_helpers, user_id)
        if not player:
            return {'error': 'Profil konnte nicht geladen werden.'}
        
        result = {
            'player_action': action,
            'player_damage': 0,
            'monster_damage': 0,
            'player_health': player['health'],
            'monster_health': monster['health'],
            'combat_over': False,
            'player_won': False,
            'rewards': None,
            'messages': []
        }
        
        # Player's turn
        if action == 'attack':
            dmg_result = calculate_damage(
                player['strength'],
                monster['defense'],
                player['dexterity']
            )
            
            if dmg_result['dodged']:
                result['messages'].append("❌ Dein Angriff wurde ausgewichen!")
            elif dmg_result['crit']:
                result['player_damage'] = dmg_result['damage']
                result['messages'].append(f"💥 **KRITISCHER TREFFER!** Du fügst {dmg_result['damage']} Schaden zu!")
            else:
                result['player_damage'] = dmg_result['damage']
                result['messages'].append(f"⚔️ Du fügst {dmg_result['damage']} Schaden zu!")
            
            monster['health'] -= result['player_damage']
        
        elif action == 'run':
            # 50% chance to run, higher with more dex
            run_chance = 0.50 + (player['dexterity'] / 200.0)
            run_chance = min(0.90, run_chance)
            
            if random.random() < run_chance:
                result['combat_over'] = True
                result['messages'].append("🏃 Du bist erfolgreich geflohen!")
                return result
            else:
                result['messages'].append("❌ Flucht gescheitert!")
        
        # Check if monster is defeated
        if monster['health'] <= 0:
            result['combat_over'] = True
            result['player_won'] = True
            
            # Award XP and gold
            xp_result = await gain_xp(db_helpers, user_id, monster['xp_reward'])
            
            # Award gold
            conn = db_helpers.db_pool.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE rpg_players SET gold = gold + %s WHERE user_id = %s
            """, (monster['gold_reward'], user_id))
            conn.commit()
            cursor.close()
            conn.close()
            
            result['rewards'] = {
                'xp': monster['xp_reward'],
                'gold': monster['gold_reward'],
                'leveled_up': xp_result['leveled_up'] if xp_result else False,
                'new_level': xp_result['new_level'] if xp_result and xp_result['leveled_up'] else None
            }
            
            msg = f"🎉 **{monster['name']} besiegt!**\n"
            msg += f"💰 +{monster['gold_reward']} Gold\n"
            msg += f"⭐ +{monster['xp_reward']} XP"
            if result['rewards']['leveled_up']:
                msg += f"\n\n🎊 **LEVEL UP!** Du bist jetzt Level {result['rewards']['new_level']}!"
            result['messages'].append(msg)
            
            return result
        
        # Monster's turn (if still alive and player didn't run)
        if not result['combat_over']:
            # Calculate player health percentage for AI decision-making
            player_health_pct = player['health'] / player['max_health']
            
            dmg_result = calculate_damage(
                monster['strength'],
                player['defense'],
                monster['speed'],
                is_ai=True,
                player_health_pct=player_health_pct
            )
            
            if dmg_result['dodged']:
                result['messages'].append(f"✨ Du bist dem Angriff von {monster['name']} ausgewichen!")
            elif dmg_result['crit']:
                result['monster_damage'] = dmg_result['damage']
                result['messages'].append(f"💀 **KRITISCHER TREFFER!** {monster['name']} fügt dir {dmg_result['damage']} Schaden zu!")
            else:
                result['monster_damage'] = dmg_result['damage']
                result['messages'].append(f"🗡️ {monster['name']} fügt dir {dmg_result['damage']} Schaden zu!")
            
            # Update player health
            new_health = max(0, player['health'] - result['monster_damage'])
            result['player_health'] = new_health
            
            conn = db_helpers.db_pool.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE rpg_players SET health = %s WHERE user_id = %s
            """, (new_health, user_id))
            conn.commit()
            cursor.close()
            conn.close()
            
            # Check if player is defeated
            if new_health <= 0:
                result['combat_over'] = True
                result['player_won'] = False
                result['messages'].append("💀 **Du wurdest besiegt!** Du wirst zum Dorf zurückgebracht.")
                
                # Restore half health
                conn = db_helpers.db_pool.get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE rpg_players SET health = max_health / 2 WHERE user_id = %s
                """, (user_id,))
                conn.commit()
                cursor.close()
                conn.close()
        
        result['monster_health'] = monster['health']
        return result
        
    except Exception as e:
        logger.error(f"Error processing combat turn: {e}", exc_info=True)
        return {'error': str(e)}


# Default Shop Items - Expanded (100+ items)
DEFAULT_SHOP_ITEMS = [
    # ===== COMMON WEAPONS (Level 1-3) =====
    {'name': 'Rostiges Schwert', 'type': 'weapon', 'rarity': 'common', 'description': 'Ein altes, rostiges Schwert', 'damage': 15, 'damage_type': 'physical', 'price': 50, 'required_level': 1},
    {'name': 'Holzstab', 'type': 'weapon', 'rarity': 'common', 'description': 'Ein einfacher Holzstab', 'damage': 12, 'damage_type': 'physical', 'price': 40, 'required_level': 1},
    {'name': 'Kurzschwert', 'type': 'weapon', 'rarity': 'common', 'description': 'Ein kleines, aber scharfes Schwert', 'damage': 18, 'damage_type': 'physical', 'price': 60, 'required_level': 1},
    {'name': 'Steinaxt', 'type': 'weapon', 'rarity': 'common', 'description': 'Eine primitive Steinaxt', 'damage': 14, 'damage_type': 'physical', 'price': 45, 'required_level': 1},
    {'name': 'Wurfmesser', 'type': 'weapon', 'rarity': 'common', 'description': 'Kleine Wurfmesser', 'damage': 16, 'damage_type': 'physical', 'price': 55, 'required_level': 1},
    {'name': 'Holzkeule', 'type': 'weapon', 'rarity': 'common', 'description': 'Eine schwere Holzkeule', 'damage': 17, 'damage_type': 'physical', 'price': 48, 'required_level': 1},
    {'name': 'Dolch', 'type': 'weapon', 'rarity': 'common', 'description': 'Ein einfacher Dolch', 'damage': 13, 'damage_type': 'physical', 'price': 42, 'required_level': 1},
    {'name': 'Speer', 'type': 'weapon', 'rarity': 'common', 'description': 'Ein Holzspeer mit Eisenspitze', 'damage': 16, 'damage_type': 'physical', 'price': 52, 'required_level': 2},
    {'name': 'Kurzbogen', 'type': 'weapon', 'rarity': 'common', 'description': 'Ein kleiner Bogen', 'damage': 15, 'damage_type': 'physical', 'price': 58, 'required_level': 2},
    {'name': 'Streitkolben', 'type': 'weapon', 'rarity': 'common', 'description': 'Ein schwerer Kolben', 'damage': 19, 'damage_type': 'physical', 'price': 65, 'required_level': 3},
    
    # ===== UNCOMMON WEAPONS (Level 3-6) =====
    {'name': 'Stahlschwert', 'type': 'weapon', 'rarity': 'uncommon', 'description': 'Ein gut geschmiedetes Stahlschwert', 'damage': 25, 'damage_type': 'physical', 'price': 200, 'required_level': 3},
    {'name': 'Kampfaxt', 'type': 'weapon', 'rarity': 'uncommon', 'description': 'Eine schwere Kampfaxt', 'damage': 30, 'damage_type': 'physical', 'price': 250, 'required_level': 4},
    {'name': 'Langbogen', 'type': 'weapon', 'rarity': 'uncommon', 'description': 'Ein präziser Langbogen', 'damage': 22, 'damage_type': 'physical', 'price': 180, 'required_level': 3},
    {'name': 'Kriegshammer', 'type': 'weapon', 'rarity': 'uncommon', 'description': 'Ein zweihändiger Hammer', 'damage': 32, 'damage_type': 'physical', 'price': 270, 'required_level': 5},
    {'name': 'Rapier', 'type': 'weapon', 'rarity': 'uncommon', 'description': 'Ein schnelles Rapier', 'damage': 23, 'damage_type': 'physical', 'price': 190, 'required_level': 4},
    {'name': 'Glefe', 'type': 'weapon', 'rarity': 'uncommon', 'description': 'Eine lange Stangenwaffe', 'damage': 26, 'damage_type': 'physical', 'price': 210, 'required_level': 4},
    {'name': 'Zweihänder', 'type': 'weapon', 'rarity': 'uncommon', 'description': 'Ein riesiges Schwert', 'damage': 28, 'damage_type': 'physical', 'price': 230, 'required_level': 5},
    {'name': 'Armbrust', 'type': 'weapon', 'rarity': 'uncommon', 'description': 'Eine kraftvolle Armbrust', 'damage': 24, 'damage_type': 'physical', 'price': 195, 'required_level': 4},
    {'name': 'Katana', 'type': 'weapon', 'rarity': 'uncommon', 'description': 'Ein scharfes Katana', 'damage': 27, 'damage_type': 'physical', 'price': 220, 'required_level': 5},
    {'name': 'Streitaxt', 'type': 'weapon', 'rarity': 'uncommon', 'description': 'Eine zweischneidige Streitaxt', 'damage': 29, 'damage_type': 'physical', 'price': 240, 'required_level': 5},
    {'name': 'Säbel', 'type': 'weapon', 'rarity': 'uncommon', 'description': 'Ein gebogener Säbel', 'damage': 24, 'damage_type': 'physical', 'price': 200, 'required_level': 4},
    {'name': 'Morgenstern', 'type': 'weapon', 'rarity': 'uncommon', 'description': 'Eine Keule mit Spitzen', 'damage': 31, 'damage_type': 'physical', 'price': 260, 'required_level': 6},
    
    # ===== RARE WEAPONS (Level 6-10) =====
    {'name': 'Flammenschwert', 'type': 'weapon', 'rarity': 'rare', 'description': 'Ein mit Flammen verzaubertes Schwert', 'damage': 40, 'damage_type': 'fire', 'price': 500, 'required_level': 6},
    {'name': 'Frosthammer', 'type': 'weapon', 'rarity': 'rare', 'description': 'Ein eiskalter Kriegshammer', 'damage': 45, 'damage_type': 'ice', 'price': 550, 'required_level': 7},
    {'name': 'Giftdolch', 'type': 'weapon', 'rarity': 'rare', 'description': 'Ein mit Gift beschichteter Dolch', 'damage': 35, 'damage_type': 'poison', 'price': 450, 'required_level': 5},
    {'name': 'Donnerspeer', 'type': 'weapon', 'rarity': 'rare', 'description': 'Ein Speer der Blitze schleudert', 'damage': 42, 'damage_type': 'lightning', 'price': 520, 'required_level': 7},
    {'name': 'Schattenklinge', 'type': 'weapon', 'rarity': 'rare', 'description': 'Eine Klinge aus purer Dunkelheit', 'damage': 38, 'damage_type': 'dark', 'price': 480, 'required_level': 6},
    {'name': 'Lichtbogen', 'type': 'weapon', 'rarity': 'rare', 'description': 'Ein Bogen aus heiligem Licht', 'damage': 36, 'damage_type': 'light', 'price': 470, 'required_level': 6},
    {'name': 'Windsäbel', 'type': 'weapon', 'rarity': 'rare', 'description': 'Ein Säbel schnell wie der Wind', 'damage': 39, 'damage_type': 'wind', 'price': 490, 'required_level': 7},
    {'name': 'Erdenhammer', 'type': 'weapon', 'rarity': 'rare', 'description': 'Ein Hammer der Erde bebt', 'damage': 44, 'damage_type': 'earth', 'price': 540, 'required_level': 8},
    {'name': 'Seelensense', 'type': 'weapon', 'rarity': 'rare', 'description': 'Eine Sense die Seelen erntet', 'damage': 41, 'damage_type': 'dark', 'price': 510, 'required_level': 7},
    {'name': 'Kristallstab', 'type': 'weapon', 'rarity': 'rare', 'description': 'Ein magischer Kristallstab', 'damage': 37, 'damage_type': 'magic', 'price': 475, 'required_level': 6},
    {'name': 'Runenschwert', 'type': 'weapon', 'rarity': 'rare', 'description': 'Ein mit Runen verziertes Schwert', 'damage': 43, 'damage_type': 'magic', 'price': 530, 'required_level': 8},
    {'name': 'Drachenklauen', 'type': 'weapon', 'rarity': 'rare', 'description': 'Klauen aus Drachenzähnen', 'damage': 40, 'damage_type': 'fire', 'price': 505, 'required_level': 8},
    
    # ===== EPIC WEAPONS (Level 10+) =====
    {'name': 'Blitzklinge', 'type': 'weapon', 'rarity': 'epic', 'description': 'Eine mit Blitzen geladene Klinge', 'damage': 60, 'damage_type': 'lightning', 'price': 1000, 'required_level': 10},
    {'name': 'Heilige Lanze', 'type': 'weapon', 'rarity': 'epic', 'description': 'Eine von Licht durchdrungene Lanze', 'damage': 55, 'damage_type': 'light', 'price': 950, 'required_level': 9},
    {'name': 'Chaosschwert', 'type': 'weapon', 'rarity': 'epic', 'description': 'Ein Schwert aus reinem Chaos', 'damage': 65, 'damage_type': 'dark', 'price': 1100, 'required_level': 11},
    {'name': 'Phönixbogen', 'type': 'weapon', 'rarity': 'epic', 'description': 'Ein Bogen der wie ein Phönix brennt', 'damage': 58, 'damage_type': 'fire', 'price': 980, 'required_level': 10},
    {'name': 'Leviathan', 'type': 'weapon', 'rarity': 'epic', 'description': 'Ein Dreizack der Meerestiefe', 'damage': 62, 'damage_type': 'water', 'price': 1050, 'required_level': 11},
    {'name': 'Excalibur', 'type': 'weapon', 'rarity': 'legendary', 'description': 'Das legendäre Schwert', 'damage': 80, 'damage_type': 'light', 'price': 2000, 'required_level': 15},
    {'name': 'Mjölnir', 'type': 'weapon', 'rarity': 'legendary', 'description': 'Der Hammer des Donnergottes', 'damage': 85, 'damage_type': 'lightning', 'price': 2200, 'required_level': 16},
    {'name': 'Gramfang', 'type': 'weapon', 'rarity': 'legendary', 'description': 'Die Klinge des Drachentöters', 'damage': 82, 'damage_type': 'fire', 'price': 2100, 'required_level': 15},
    
    # ===== HEALING SKILLS =====
    {'name': 'Kleine Heilung', 'type': 'skill', 'rarity': 'common', 'description': 'Heilt 30 HP', 'price': 100, 'required_level': 2, 'effects': json.dumps({'heal': 30})},
    {'name': 'Mittlere Heilung', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Heilt 60 HP', 'price': 250, 'required_level': 5, 'effects': json.dumps({'heal': 60})},
    {'name': 'Große Heilung', 'type': 'skill', 'rarity': 'rare', 'description': 'Heilt 100 HP', 'price': 500, 'required_level': 8, 'effects': json.dumps({'heal': 100})},
    {'name': 'Regeneration', 'type': 'skill', 'rarity': 'rare', 'description': 'Heilt über 3 Runden', 'price': 450, 'required_level': 7, 'effects': json.dumps({'regen': 3})},
    {'name': 'Göttliche Heilung', 'type': 'skill', 'rarity': 'epic', 'description': 'Heilt 150 HP sofort', 'price': 800, 'required_level': 10, 'effects': json.dumps({'heal': 150})},
    {'name': 'Lebenselixier', 'type': 'skill', 'rarity': 'epic', 'description': 'Regeneriert 50 HP pro Runde für 3 Runden', 'price': 900, 'required_level': 12, 'effects': json.dumps({'regen': 3, 'heal_per_turn': 50})},
    
    # ===== FIRE ATTACK SKILLS =====
    {'name': 'Feuerball', 'type': 'skill', 'rarity': 'common', 'description': 'Wirft einen Feuerball', 'damage': 20, 'damage_type': 'fire', 'price': 100, 'required_level': 2, 'effects': json.dumps({'burn': 0.3})},
    {'name': 'Feuersturm', 'type': 'skill', 'rarity': 'epic', 'description': 'Ein verheerender Feuersturm', 'damage': 70, 'damage_type': 'fire', 'price': 1000, 'required_level': 10, 'effects': json.dumps({'burn': 0.6})},
    {'name': 'Flammenwelle', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Welle aus Flammen', 'damage': 30, 'damage_type': 'fire', 'price': 250, 'required_level': 4, 'effects': json.dumps({'burn': 0.4})},
    {'name': 'Inferno', 'type': 'skill', 'rarity': 'rare', 'description': 'Entfesselt ein Inferno', 'damage': 55, 'damage_type': 'fire', 'price': 650, 'required_level': 9, 'effects': json.dumps({'burn': 0.5})},
    {'name': 'Meteorregen', 'type': 'skill', 'rarity': 'epic', 'description': 'Ruft brennende Meteore', 'damage': 75, 'damage_type': 'fire', 'price': 1100, 'required_level': 11, 'effects': json.dumps({'burn': 0.7})},
    
    # ===== ICE/FROST SKILLS =====
    {'name': 'Eissturm', 'type': 'skill', 'rarity': 'rare', 'description': 'Entfesselt einen Eissturm', 'damage': 50, 'damage_type': 'ice', 'price': 550, 'required_level': 8, 'effects': json.dumps({'freeze': 0.5})},
    {'name': 'Frostlanze', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Schießt eine Eislanze', 'damage': 28, 'damage_type': 'ice', 'price': 220, 'required_level': 4, 'effects': json.dumps({'freeze': 0.3})},
    {'name': 'Eiswand', 'type': 'skill', 'rarity': 'rare', 'description': 'Erschafft schützende Eiswand', 'price': 480, 'required_level': 7, 'effects': json.dumps({'shield': 3, 'defense_bonus': 20})},
    {'name': 'Frosthauch', 'type': 'skill', 'rarity': 'common', 'description': 'Kalter Hauch', 'damage': 18, 'damage_type': 'ice', 'price': 110, 'required_level': 3, 'effects': json.dumps({'freeze': 0.2})},
    {'name': 'Gletscherspalte', 'type': 'skill', 'rarity': 'epic', 'description': 'Spaltet die Erde mit Eis', 'damage': 65, 'damage_type': 'ice', 'price': 950, 'required_level': 10, 'effects': json.dumps({'freeze': 0.6})},
    
    # ===== LIGHTNING SKILLS =====
    {'name': 'Blitzstoß', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Schleudert einen Blitz', 'damage': 35, 'damage_type': 'lightning', 'price': 300, 'required_level': 5, 'effects': json.dumps({'static': 0.4})},
    {'name': 'Kettenlblitz', 'type': 'skill', 'rarity': 'rare', 'description': 'Blitz der springt', 'damage': 48, 'damage_type': 'lightning', 'price': 580, 'required_level': 8, 'effects': json.dumps({'static': 0.5})},
    {'name': 'Donnerschlag', 'type': 'skill', 'rarity': 'common', 'description': 'Elektrischer Schlag', 'damage': 22, 'damage_type': 'lightning', 'price': 130, 'required_level': 3, 'effects': json.dumps({'static': 0.3})},
    {'name': 'Gewittersturm', 'type': 'skill', 'rarity': 'epic', 'description': 'Beschwört Gewittersturm', 'damage': 68, 'damage_type': 'lightning', 'price': 1000, 'required_level': 11, 'effects': json.dumps({'static': 0.7})},
    
    # ===== DARK/SHADOW SKILLS =====
    {'name': 'Schattenpfeil', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Pfeil aus Schatten', 'damage': 32, 'damage_type': 'dark', 'price': 270, 'required_level': 5, 'effects': json.dumps({'darkness': 0.4})},
    {'name': 'Seelenraub', 'type': 'skill', 'rarity': 'rare', 'description': 'Stiehlt Lebensenergie', 'damage': 45, 'damage_type': 'dark', 'price': 600, 'required_level': 9, 'effects': json.dumps({'lifesteal': 0.5})},
    {'name': 'Dunkler Puls', 'type': 'skill', 'rarity': 'common', 'description': 'Welle dunkler Energie', 'damage': 24, 'damage_type': 'dark', 'price': 140, 'required_level': 3, 'effects': json.dumps({'darkness': 0.3})},
    {'name': 'Schattenumarmung', 'type': 'skill', 'rarity': 'epic', 'description': 'Verschlingt in Schatten', 'damage': 72, 'damage_type': 'dark', 'price': 1150, 'required_level': 12, 'effects': json.dumps({'darkness': 0.7, 'lifesteal': 0.3})},
    
    # ===== LIGHT/HOLY SKILLS =====
    {'name': 'Heiliges Licht', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Strahlendes Licht', 'damage': 30, 'damage_type': 'light', 'price': 260, 'required_level': 4, 'effects': json.dumps({'light': 0.3})},
    {'name': 'Göttlicher Zorn', 'type': 'skill', 'rarity': 'rare', 'description': 'Göttliche Strafe', 'damage': 52, 'damage_type': 'light', 'price': 620, 'required_level': 9, 'effects': json.dumps({'light': 0.5})},
    {'name': 'Lichtstrahl', 'type': 'skill', 'rarity': 'common', 'description': 'Strahl göttlichen Lichts', 'damage': 26, 'damage_type': 'light', 'price': 150, 'required_level': 3, 'effects': json.dumps({'light': 0.2})},
    {'name': 'Himmlisches Gericht', 'type': 'skill', 'rarity': 'epic', 'description': 'Endgültiges Urteil', 'damage': 78, 'damage_type': 'light', 'price': 1200, 'required_level': 13, 'effects': json.dumps({'light': 0.8})},
    
    # ===== DEFENSIVE SKILLS =====
    {'name': 'Schildwall', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Erhöht die Verteidigung für 2 Runden', 'price': 250, 'required_level': 4, 'effects': json.dumps({'shield': 2})},
    {'name': 'Ausweichen', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Erhöht Ausweichen-Chance für 2 Runden', 'price': 200, 'required_level': 3, 'effects': json.dumps({'dodge_boost': 2})},
    {'name': 'Eisenhaut', 'type': 'skill', 'rarity': 'rare', 'description': 'Drastisch erhöhte Verteidigung für 3 Runden', 'price': 500, 'required_level': 7, 'effects': json.dumps({'ironSkin': 3})},
    {'name': 'Manarüstung', 'type': 'skill', 'rarity': 'rare', 'description': 'Magische Rüstung', 'price': 550, 'required_level': 8, 'effects': json.dumps({'mana_shield': 3, 'magic_defense': 30})},
    {'name': 'Unverwundbarkeit', 'type': 'skill', 'rarity': 'epic', 'description': 'Kurzzeitige Unverwundbarkeit', 'price': 900, 'required_level': 11, 'effects': json.dumps({'invulnerable': 1})},
    {'name': 'Spiegelschild', 'type': 'skill', 'rarity': 'epic', 'description': 'Reflektiert Angriffe', 'price': 850, 'required_level': 10, 'effects': json.dumps({'reflect': 2, 'reflect_damage': 0.5})},
    
    # ===== BUFF SKILLS =====
    {'name': 'Geschwindigkeitsschub', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Erhöht Geschwindigkeit für 3 Runden', 'price': 220, 'required_level': 4, 'effects': json.dumps({'speed_boost': 3})},
    {'name': 'Berserker-Wut', 'type': 'skill', 'rarity': 'rare', 'description': 'Erhöht Angriff, senkt Verteidigung', 'price': 400, 'required_level': 6, 'effects': json.dumps({'rage': 1})},
    {'name': 'Konzentration', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Erhöht kritische Trefferchance', 'price': 280, 'required_level': 5, 'effects': json.dumps({'crit_boost': 3})},
    {'name': 'Kriegsrausch', 'type': 'skill', 'rarity': 'rare', 'description': 'Massiv erhöhter Angriff', 'price': 520, 'required_level': 8, 'effects': json.dumps({'attack_boost': 3, 'damage_bonus': 0.5})},
    {'name': 'Fokus', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Erhöht Genauigkeit', 'price': 240, 'required_level': 4, 'effects': json.dumps({'accuracy_boost': 3})},
    {'name': 'Kampfgeist', 'type': 'skill', 'rarity': 'epic', 'description': 'Alle Stats erhöht', 'price': 950, 'required_level': 11, 'effects': json.dumps({'all_stats_boost': 2, 'stat_bonus': 0.3})},
    
    # ===== DEBUFF SKILLS =====
    {'name': 'Gift werfen', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Vergiftet den Gegner', 'damage': 15, 'damage_type': 'poison', 'price': 180, 'required_level': 3, 'effects': json.dumps({'poison': 0.5})},
    {'name': 'Blenden', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Verringert Genauigkeit des Gegners', 'price': 150, 'required_level': 3, 'effects': json.dumps({'darkness': 0.6})},
    {'name': 'Verlangsamen', 'type': 'skill', 'rarity': 'common', 'description': 'Reduziert Gegner-Geschwindigkeit', 'price': 120, 'required_level': 2, 'effects': json.dumps({'slow': 0.4})},
    {'name': 'Schwächen', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Senkt Angriff des Gegners', 'price': 200, 'required_level': 4, 'effects': json.dumps({'weaken': 3, 'attack_reduction': 0.3})},
    {'name': 'Fluch', 'type': 'skill', 'rarity': 'rare', 'description': 'Verflucht den Gegner', 'price': 450, 'required_level': 7, 'effects': json.dumps({'curse': 3, 'all_stats_reduction': 0.2})},
    {'name': 'Lähmung', 'type': 'skill', 'rarity': 'rare', 'description': 'Lähmt den Gegner', 'price': 500, 'required_level': 8, 'effects': json.dumps({'paralyze': 0.7, 'stun': 1})},
    
    # ===== UTILITY/SPECIAL SKILLS =====
    {'name': 'Teleportation', 'type': 'skill', 'rarity': 'rare', 'description': 'Teleportiert aus dem Kampf', 'price': 600, 'required_level': 9, 'effects': json.dumps({'escape': 1.0})},
    {'name': 'Zeitverzerrung', 'type': 'skill', 'rarity': 'epic', 'description': 'Verzerrt die Zeit', 'price': 1000, 'required_level': 12, 'effects': json.dumps({'time_stop': 1, 'extra_turn': True})},
    {'name': 'Manaentzug', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Entzieht Gegner Energie', 'damage': 25, 'damage_type': 'magic', 'price': 230, 'required_level': 4, 'effects': json.dumps({'mana_drain': 0.3})},
    {'name': 'Gegenangriff', 'type': 'skill', 'rarity': 'rare', 'description': 'Konter bei Angriffen', 'price': 480, 'required_level': 7, 'effects': json.dumps({'counter': 3, 'counter_damage': 0.8})},
    {'name': 'Doppelangriff', 'type': 'skill', 'rarity': 'epic', 'description': 'Greift zweimal an', 'price': 850, 'required_level': 10, 'effects': json.dumps({'double_attack': 2})},
]



async def initialize_shop_items(db_helpers):
    """Initialize default shop items in the database."""
    try:
        if not db_helpers.db_pool:
            return
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return
        
        cursor = conn.cursor()
        try:
            # Check if items exist
            cursor.execute("SELECT COUNT(*) FROM rpg_items WHERE created_by IS NULL")
            count = cursor.fetchone()[0]
            
            if count == 0:
                # Insert default items
                for item in DEFAULT_SHOP_ITEMS:
                    cursor.execute("""
                        INSERT INTO rpg_items 
                        (name, type, rarity, description, damage, damage_type, price, required_level, effects)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (item['name'], item['type'], item['rarity'], item['description'],
                          item.get('damage', 0), item.get('damage_type'), item['price'],
                          item['required_level'], item.get('effects')))
                
                conn.commit()
                logger.info(f"Initialized {len(DEFAULT_SHOP_ITEMS)} default shop items")
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error initializing shop items: {e}", exc_info=True)


async def get_shop_items(db_helpers, player_level: int):
    """Get shop items available for player level."""
    try:
        if not db_helpers.db_pool:
            return []
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return []
        
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT * FROM rpg_items
                WHERE required_level <= %s AND created_by IS NULL
                ORDER BY required_level ASC, price ASC
            """, (player_level,))
            
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error getting shop items: {e}", exc_info=True)
        return []


async def purchase_item(db_helpers, user_id: int, item_id: int):
    """Purchase an item from the shop."""
    try:
        if not db_helpers.db_pool:
            return False, "Datenbank nicht verfügbar"
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return False, "Datenbankverbindung fehlgeschlagen"
        
        cursor = conn.cursor(dictionary=True)
        try:
            # Get item
            cursor.execute("SELECT * FROM rpg_items WHERE id = %s", (item_id,))
            item = cursor.fetchone()
            
            if not item:
                return False, "Item nicht gefunden"
            
            # Get player
            cursor.execute("SELECT * FROM rpg_players WHERE user_id = %s", (user_id,))
            player = cursor.fetchone()
            
            if not player:
                return False, "Spieler nicht gefunden"
            
            # Check level requirement
            if player['level'] < item['required_level']:
                return False, f"Level {item['required_level']} benötigt"
            
            # Check gold
            if player['gold'] < item['price']:
                return False, "Nicht genug Gold"
            
            # Add to inventory
            cursor.execute("""
                INSERT INTO rpg_inventory (user_id, item_id, item_type, quantity)
                VALUES (%s, %s, %s, 1)
                ON DUPLICATE KEY UPDATE quantity = quantity + 1
            """, (user_id, item_id, item['type']))
            
            # Deduct gold
            cursor.execute("""
                UPDATE rpg_players SET gold = gold - %s WHERE user_id = %s
            """, (item['price'], user_id))
            
            conn.commit()
            return True, "Item gekauft"
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error purchasing item: {e}", exc_info=True)
        return False, "Fehler beim Kauf"


async def sell_item(db_helpers, user_id: int, item_id: int, quantity: int = 1):
    """Sell an item from inventory for 50% of its shop price."""
    try:
        if not db_helpers.db_pool:
            return False, "Datenbank nicht verfügbar"
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return False, "Datenbankverbindung fehlgeschlagen"
        
        cursor = conn.cursor(dictionary=True)
        try:
            # Check if player has item in inventory
            cursor.execute("""
                SELECT i.quantity, it.name, it.price
                FROM rpg_inventory i
                JOIN rpg_items it ON i.item_id = it.id
                WHERE i.user_id = %s AND i.item_id = %s
            """, (user_id, item_id))
            
            inventory_item = cursor.fetchone()
            
            if not inventory_item:
                return False, "Item nicht im Inventar"
            
            if inventory_item['quantity'] < quantity:
                return False, f"Nicht genug Items (hast {inventory_item['quantity']})"
            
            # Calculate sell price (50% of shop price)
            sell_price = int(inventory_item['price'] * 0.5 * quantity)
            
            # Remove from inventory
            new_quantity = inventory_item['quantity'] - quantity
            if new_quantity > 0:
                cursor.execute("""
                    UPDATE rpg_inventory
                    SET quantity = %s
                    WHERE user_id = %s AND item_id = %s
                """, (new_quantity, user_id, item_id))
            else:
                cursor.execute("""
                    DELETE FROM rpg_inventory
                    WHERE user_id = %s AND item_id = %s
                """, (user_id, item_id))
            
            # Add gold
            cursor.execute("""
                UPDATE rpg_players SET gold = gold + %s WHERE user_id = %s
            """, (sell_price, user_id))
            
            conn.commit()
            return True, f"Verkauft {quantity}x {inventory_item['name']} für {sell_price} Gold"
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error selling item: {e}", exc_info=True)
        return False, "Fehler beim Verkauf"


async def get_player_inventory(db_helpers, user_id: int):
    """Get player's inventory with item details."""
    try:
        if not db_helpers.db_pool:
            return []
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return []
        
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT i.*, it.name, it.type, it.rarity, it.damage, it.description, it.price, 
                       it.durability as max_durability, it.effects
                FROM rpg_inventory i
                JOIN rpg_items it ON i.item_id = it.id
                WHERE i.user_id = %s
                ORDER BY it.rarity DESC, it.name ASC
            """, (user_id,))
            
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error getting inventory: {e}", exc_info=True)
        return []


async def get_equipped_items(db_helpers, user_id: int):
    """Get player's equipped items."""
    try:
        if not db_helpers.db_pool:
            return {}
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return {}
        
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM rpg_equipped WHERE user_id = %s", (user_id,))
            result = cursor.fetchone()
            
            if not result:
                # Create empty equipped row
                cursor.execute("INSERT INTO rpg_equipped (user_id) VALUES (%s)", (user_id,))
                conn.commit()
                return {'user_id': user_id, 'weapon_id': None, 'skill1_id': None, 'skill2_id': None}
            
            return result
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error getting equipped items: {e}", exc_info=True)
        return {}


async def get_item_by_id(db_helpers, item_id: int):
    """Get item by ID."""
    try:
        if not db_helpers.db_pool or not item_id:
            return None
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return None
        
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM rpg_items WHERE id = %s", (item_id,))
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error getting item: {e}", exc_info=True)
        return None


async def equip_item(db_helpers, user_id: int, item_id: int, item_type: str):
    """Equip an item."""
    try:
        if not db_helpers.db_pool:
            return False
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        try:
            # Check if player has item
            cursor.execute("""
                SELECT 1 FROM rpg_inventory WHERE user_id = %s AND item_id = %s
            """, (user_id, item_id))
            
            if not cursor.fetchone():
                return False
            
            # Equip item
            if item_type == 'weapon':
                cursor.execute("""
                    INSERT INTO rpg_equipped (user_id, weapon_id)
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE weapon_id = %s
                """, (user_id, item_id, item_id))
            elif item_type == 'skill':
                # Try slot 1 first, then slot 2
                cursor.execute("SELECT skill1_id, skill2_id FROM rpg_equipped WHERE user_id = %s", (user_id,))
                result = cursor.fetchone()
                
                if not result or result[0] is None:
                    # Slot 1 is empty, equip there
                    cursor.execute("""
                        INSERT INTO rpg_equipped (user_id, skill1_id)
                        VALUES (%s, %s)
                        ON DUPLICATE KEY UPDATE skill1_id = %s
                    """, (user_id, item_id, item_id))
                elif result[1] is None:
                    # Slot 1 is filled but slot 2 is empty, equip to slot 2
                    # We know row exists at this point, so just UPDATE
                    cursor.execute("""
                        UPDATE rpg_equipped SET skill2_id = %s WHERE user_id = %s
                    """, (item_id, user_id))
                else:
                    # Both slots are full, replace slot 2
                    cursor.execute("""
                        UPDATE rpg_equipped SET skill2_id = %s WHERE user_id = %s
                    """, (item_id, user_id))
            
            conn.commit()
            return True
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error equipping item: {e}", exc_info=True)
        return False


async def heal_player(db_helpers, user_id: int, cost: int):
    """Heal player to full health."""
    try:
        if not db_helpers.db_pool:
            return False
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE rpg_players 
                SET health = max_health, gold = gold - %s
                WHERE user_id = %s AND gold >= %s
            """, (cost, user_id, cost))
            
            conn.commit()
            return cursor.rowcount > 0
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error healing player: {e}", exc_info=True)
        return False


async def apply_blessing(db_helpers, user_id: int, blessing_type: str, cost: int):
    """Apply a temporary blessing to player."""
    try:
        if not db_helpers.db_pool:
            return False
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        try:
            # Deduct gold
            cursor.execute("""
                UPDATE rpg_players 
                SET gold = gold - %s
                WHERE user_id = %s AND gold >= %s
            """, (cost, user_id, cost))
            
            if cursor.rowcount == 0:
                return False
            
            # TODO: Store blessing in a separate table with expiration
            # For now, just deduct the gold
            
            conn.commit()
            return True
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error applying blessing: {e}", exc_info=True)
        return False


async def allocate_skill_point(db_helpers, user_id: int, stat_name: str):
    """Allocate a skill point to a specific stat at the temple."""
    try:
        if not db_helpers.db_pool:
            return False, "Datenbank nicht verfügbar"
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return False, "Datenbankverbindung fehlgeschlagen"
        
        cursor = conn.cursor(dictionary=True)
        try:
            # Get player
            cursor.execute("SELECT * FROM rpg_players WHERE user_id = %s", (user_id,))
            player = cursor.fetchone()
            
            if not player:
                return False, "Spieler nicht gefunden"
            
            # Check if player has skill points
            if player['skill_points'] <= 0:
                return False, "Keine Skillpunkte verfügbar"
            
            # Validate stat name against whitelist and use safe mapping
            stat_mapping = {
                'strength': 'strength',
                'dexterity': 'dexterity',
                'defense': 'defense',
                'speed': 'speed'
            }
            
            if stat_name not in stat_mapping:
                return False, "Ungültiger Stat"
            
            # Use the validated stat name from mapping (safe from SQL injection)
            safe_stat = stat_mapping[stat_name]
            
            # Allocate point - using CASE statement to avoid SQL injection
            cursor.execute("""
                UPDATE rpg_players 
                SET strength = CASE WHEN %s = 'strength' THEN strength + 1 ELSE strength END,
                    dexterity = CASE WHEN %s = 'dexterity' THEN dexterity + 1 ELSE dexterity END,
                    defense = CASE WHEN %s = 'defense' THEN defense + 1 ELSE defense END,
                    speed = CASE WHEN %s = 'speed' THEN speed + 1 ELSE speed END,
                    skill_points = skill_points - 1
                WHERE user_id = %s
            """, (safe_stat, safe_stat, safe_stat, safe_stat, user_id))
            
            conn.commit()
            return True, f"{stat_name.capitalize()} um 1 erhöht"
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error allocating skill point: {e}", exc_info=True)
        return False, str(e)


async def reset_skill_points(db_helpers, user_id: int, cost: int):
    try:
        if not db_helpers.db_pool:
            return False
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor(dictionary=True)
        try:
            # Get current stats
            cursor.execute("""
                SELECT strength, dexterity, defense, speed, skill_points, gold
                FROM rpg_players WHERE user_id = %s
            """, (user_id,))
            
            player = cursor.fetchone()
            if not player:
                return False
            
            # Check if player has enough gold
            if player['gold'] < cost:
                return False
            
            # Calculate points to return
            points_to_return = (
                (player['strength'] - BASE_STAT_VALUE) +
                (player['dexterity'] - BASE_STAT_VALUE) +
                (player['defense'] - BASE_STAT_VALUE) +
                (player['speed'] - BASE_STAT_VALUE)
            )
            
            # Reset stats to base and add skill points
            cursor.execute("""
                UPDATE rpg_players 
                SET strength = %s, dexterity = %s, defense = %s, speed = %s,
                    skill_points = skill_points + %s,
                    gold = gold - %s
                WHERE user_id = %s
            """, (BASE_STAT_VALUE, BASE_STAT_VALUE, BASE_STAT_VALUE, BASE_STAT_VALUE, points_to_return, cost, user_id))
            
            conn.commit()
            return True
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error resetting skill points: {e}", exc_info=True)
        return False


async def get_unlocked_skills(db_helpers, user_id: int):
    """Get all unlocked skills from the skill tree for a user."""
    try:
        if not db_helpers.db_pool:
            return {}
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return {}
        
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT skill_path, skill_key, unlocked_at
                FROM rpg_skill_tree
                WHERE user_id = %s
                ORDER BY unlocked_at ASC
            """, (user_id,))
            
            skills = cursor.fetchall()
            
            # Organize by path
            unlocked = {}
            for skill in skills:
                path = skill['skill_path']
                if path not in unlocked:
                    unlocked[path] = []
                unlocked[path].append(skill['skill_key'])
            
            return unlocked
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error getting unlocked skills: {e}", exc_info=True)
        return {}


async def unlock_skill(db_helpers, user_id: int, skill_path: str, skill_key: str):
    """
    Unlock a skill from the skill tree.
    
    Args:
        user_id: User ID
        skill_path: Path in skill tree ('warrior', 'rogue', 'mage')
        skill_key: Skill identifier within the path
    
    Returns:
        (success, message) tuple
    """
    try:
        if not db_helpers.db_pool:
            return False, "Datenbank nicht verfügbar"
        
        # Validate skill exists
        if skill_path not in SKILL_TREE:
            return False, "Ungültiger Skill-Pfad"
        
        if skill_key not in SKILL_TREE[skill_path]['skills']:
            return False, "Skill nicht gefunden"
        
        skill = SKILL_TREE[skill_path]['skills'][skill_key]
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return False, "Datenbankverbindung fehlgeschlagen"
        
        cursor = conn.cursor(dictionary=True)
        try:
            # Get player
            cursor.execute("SELECT * FROM rpg_players WHERE user_id = %s", (user_id,))
            player = cursor.fetchone()
            
            if not player:
                return False, "Spieler nicht gefunden"
            
            # Check if player has enough skill points
            if player['skill_points'] < skill['cost']:
                return False, f"Nicht genug Skillpunkte (benötigt: {skill['cost']}, verfügbar: {player['skill_points']})"
            
            # Get unlocked skills
            unlocked = await get_unlocked_skills(db_helpers, user_id)
            path_unlocked = unlocked.get(skill_path, [])
            
            # Check if already unlocked
            if skill_key in path_unlocked:
                return False, "Skill bereits freigeschaltet"
            
            # Check prerequisites
            if skill['requires'] and skill['requires'] not in path_unlocked:
                required_skill = SKILL_TREE[skill_path]['skills'][skill['requires']]
                return False, f"Benötigt: {required_skill['name']}"
            
            # Unlock skill
            cursor.execute("""
                INSERT INTO rpg_skill_tree (user_id, skill_path, skill_key)
                VALUES (%s, %s, %s)
            """, (user_id, skill_path, skill_key))
            
            # Deduct skill points
            cursor.execute("""
                UPDATE rpg_players
                SET skill_points = skill_points - %s
                WHERE user_id = %s
            """, (skill['cost'], user_id))
            
            conn.commit()
            return True, f"**{skill['name']}** freigeschaltet!"
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error unlocking skill: {e}", exc_info=True)
        return False, str(e)


async def reset_skill_tree(db_helpers, user_id: int, cost: int):
    """Reset entire skill tree and refund skill points."""
    try:
        if not db_helpers.db_pool:
            return False, "Datenbank nicht verfügbar"
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return False, "Datenbankverbindung fehlgeschlagen"
        
        cursor = conn.cursor(dictionary=True)
        try:
            # Get player
            cursor.execute("SELECT gold FROM rpg_players WHERE user_id = %s", (user_id,))
            player = cursor.fetchone()
            
            if not player:
                return False, "Spieler nicht gefunden"
            
            # Check if player has enough gold
            if player['gold'] < cost:
                return False, f"Nicht genug Gold (benötigt: {cost})"
            
            # Get all unlocked skills to calculate refund
            cursor.execute("""
                SELECT st.skill_path, st.skill_key
                FROM rpg_skill_tree st
                WHERE st.user_id = %s
            """, (user_id,))
            
            unlocked_skills = cursor.fetchall()
            
            # Calculate total skill points to refund
            points_to_refund = 0
            for skill_row in unlocked_skills:
                skill = SKILL_TREE[skill_row['skill_path']]['skills'][skill_row['skill_key']]
                points_to_refund += skill['cost']
            
            # Delete all unlocked skills
            cursor.execute("""
                DELETE FROM rpg_skill_tree WHERE user_id = %s
            """, (user_id,))
            
            # Refund skill points and deduct gold
            cursor.execute("""
                UPDATE rpg_players
                SET skill_points = skill_points + %s,
                    gold = gold - %s
                WHERE user_id = %s
            """, (points_to_refund, cost, user_id))
            
            conn.commit()
            return True, f"Skill-Baum zurückgesetzt! {points_to_refund} Skillpunkte zurückerhalten."
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error resetting skill tree: {e}", exc_info=True)
        return False, str(e)


async def create_custom_item(db_helpers, name: str, item_type: str, rarity: str, description: str, 
                            damage: int = 0, price: int = 100, required_level: int = 1, created_by: int = None, effects: dict = None):
    """Create a custom item (admin function)."""
    try:
        if not db_helpers.db_pool:
            return False, "Datenbank nicht verfügbar"
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return False, "Datenbankverbindung fehlgeschlagen"
        
        cursor = conn.cursor()
        try:
            # Convert effects dict to JSON string if provided
            effects_json = json.dumps(effects) if effects else None
            
            cursor.execute("""
                INSERT INTO rpg_items 
                (name, type, rarity, description, damage, price, required_level, created_by, effects)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (name, item_type, rarity, description, damage, price, required_level, created_by, effects_json))
            
            conn.commit()
            item_id = cursor.lastrowid
            return True, item_id
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error creating custom item: {e}", exc_info=True)
        return False, str(e)


