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


# Status Effects
STATUS_EFFECTS = {
    'burn': {'name': 'Brennen', 'emoji': '🔥', 'dmg_per_turn': 5, 'duration': 3},
    'poison': {'name': 'Vergiftung', 'emoji': '🧪', 'dmg_per_turn': 7, 'duration': 4},
    'darkness': {'name': 'Dunkelheit', 'emoji': '🌑', 'acc_reduction': 0.3, 'duration': 2},
    'light': {'name': 'Licht', 'emoji': '✨', 'acc_bonus': 0.2, 'duration': 3},
    'static': {'name': 'Statisch', 'emoji': '⚡', 'paralyze_chance': 0.3, 'duration': 2},
    'freeze': {'name': 'Gefroren', 'emoji': '❄️', 'immobilize': True, 'duration': 1},
    'heal': {'name': 'Regeneration', 'emoji': '💚', 'heal_per_turn': 10, 'duration': 3},
    'shield': {'name': 'Schild', 'emoji': '🛡️', 'dmg_reduction': 0.5, 'duration': 2},
    'rage': {'name': 'Wut', 'emoji': '😡', 'atk_bonus': 0.5, 'def_reduction': 0.3, 'duration': 2}
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
                    INDEX idx_world (world),
                    INDEX idx_level (level)
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


# Default Monsters
DEFAULT_MONSTERS = [
    # Overworld monsters (Level 1-10)
    {'name': 'Schleimling', 'world': 'overworld', 'level': 1, 'health': 30, 'strength': 3, 'defense': 2, 'speed': 5, 'xp_reward': 15, 'gold_reward': 10},
    {'name': 'Goblin', 'world': 'overworld', 'level': 2, 'health': 45, 'strength': 5, 'defense': 3, 'speed': 6, 'xp_reward': 25, 'gold_reward': 20},
    {'name': 'Wilder Wolf', 'world': 'overworld', 'level': 3, 'health': 60, 'strength': 7, 'defense': 4, 'speed': 10, 'xp_reward': 35, 'gold_reward': 25},
    {'name': 'Skelett-Krieger', 'world': 'overworld', 'level': 4, 'health': 70, 'strength': 9, 'defense': 6, 'speed': 7, 'xp_reward': 50, 'gold_reward': 35},
    {'name': 'Ork-Schläger', 'world': 'overworld', 'level': 5, 'health': 90, 'strength': 12, 'defense': 8, 'speed': 6, 'xp_reward': 65, 'gold_reward': 50},
    {'name': 'Dunkler Magier', 'world': 'overworld', 'level': 6, 'health': 80, 'strength': 15, 'defense': 5, 'speed': 9, 'xp_reward': 80, 'gold_reward': 60},
    {'name': 'Troll', 'world': 'overworld', 'level': 7, 'health': 120, 'strength': 16, 'defense': 12, 'speed': 4, 'xp_reward': 100, 'gold_reward': 75},
    {'name': 'Geist', 'world': 'overworld', 'level': 8, 'health': 100, 'strength': 18, 'defense': 8, 'speed': 12, 'xp_reward': 120, 'gold_reward': 85},
    {'name': 'Oger', 'world': 'overworld', 'level': 9, 'health': 150, 'strength': 20, 'defense': 15, 'speed': 5, 'xp_reward': 150, 'gold_reward': 100},
    {'name': 'Drache (Jung)', 'world': 'overworld', 'level': 10, 'health': 180, 'strength': 25, 'defense': 18, 'speed': 10, 'xp_reward': 200, 'gold_reward': 150},
    
    # Underworld monsters (Level 10+)
    {'name': 'Dämon', 'world': 'underworld', 'level': 12, 'health': 220, 'strength': 30, 'defense': 20, 'speed': 12, 'xp_reward': 300, 'gold_reward': 200},
    {'name': 'Höllenhund', 'world': 'underworld', 'level': 14, 'health': 250, 'strength': 35, 'defense': 22, 'speed': 15, 'xp_reward': 400, 'gold_reward': 250},
    {'name': 'Schattenbestie', 'world': 'underworld', 'level': 16, 'health': 280, 'strength': 40, 'defense': 25, 'speed': 14, 'xp_reward': 500, 'gold_reward': 300},
    {'name': 'Todesritter', 'world': 'underworld', 'level': 18, 'health': 320, 'strength': 45, 'defense': 30, 'speed': 11, 'xp_reward': 650, 'gold_reward': 400},
    {'name': 'Drache (Erwachsen)', 'world': 'underworld', 'level': 20, 'health': 400, 'strength': 50, 'defense': 35, 'speed': 13, 'xp_reward': 800, 'gold_reward': 500},
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
                # Insert default monsters
                for monster in DEFAULT_MONSTERS:
                    cursor.execute("""
                        INSERT INTO rpg_monsters 
                        (name, world, level, health, strength, defense, speed, xp_reward, gold_reward)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (monster['name'], monster['world'], monster['level'], monster['health'],
                          monster['strength'], monster['defense'], monster['speed'],
                          monster['xp_reward'], monster['gold_reward']))
                
                conn.commit()
                logger.info(f"Initialized {len(DEFAULT_MONSTERS)} default monsters")
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error initializing default monsters: {e}", exc_info=True)


async def get_random_monster(db_helpers, player_level: int, world: str):
    """Get a random monster appropriate for player level and world."""
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
            
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error getting random monster: {e}", exc_info=True)
        return None


def calculate_damage(attacker_str: int, defender_def: int, attacker_dex: int) -> dict:
    """
    Calculate damage with dodge/miss/crit mechanics.
    
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
    crit_chance = min(0.30, crit_chance)  # Cap at 30%
    
    if random.random() < crit_chance:
        result['crit'] = True
        damage = int(damage * 1.5)  # 150% damage on crit
    
    result['damage'] = damage
    return result


async def start_adventure(db_helpers, user_id: int):
    """Start an adventure encounter."""
    try:
        player = await get_player_profile(db_helpers, user_id)
        if not player:
            return None, "Profil konnte nicht geladen werden."
        
        # Check cooldown (2 minutes between adventures)
        if player['last_adventure']:
            last_adv = player['last_adventure']
            if isinstance(last_adv, str):
                last_adv = datetime.fromisoformat(last_adv.replace('Z', '+00:00'))
            elif last_adv.tzinfo is None:
                last_adv = last_adv.replace(tzinfo=timezone.utc)
            
            cooldown = datetime.now(timezone.utc) - last_adv
            if cooldown.total_seconds() < 120:  # 2 minutes
                remaining = 120 - int(cooldown.total_seconds())
                return None, f"Du musst noch {remaining} Sekunden warten!"
        
        # Check if player has enough health
        if player['health'] < player['max_health'] * 0.2:  # Less than 20% health
            return None, "Du bist zu schwach! Heile dich zuerst."
        
        # Get a random monster
        monster = await get_random_monster(db_helpers, player['level'], player['world'])
        if not monster:
            return None, "Kein Monster gefunden."
        
        # Update last adventure time
        conn = db_helpers.db_pool.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE rpg_players SET last_adventure = NOW() WHERE user_id = %s
        """, (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        return monster, None
    except Exception as e:
        logger.error(f"Error starting adventure: {e}", exc_info=True)
        return None, "Ein Fehler ist aufgetreten."


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
            dmg_result = calculate_damage(
                monster['strength'],
                player['defense'],
                monster['speed']
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


# Default Shop Items
DEFAULT_SHOP_ITEMS = [
    # Common Weapons
    {'name': 'Rostiges Schwert', 'type': 'weapon', 'rarity': 'common', 'description': 'Ein altes, rostiges Schwert', 'damage': 15, 'damage_type': 'physical', 'price': 50, 'required_level': 1},
    {'name': 'Holzstab', 'type': 'weapon', 'rarity': 'common', 'description': 'Ein einfacher Holzstab', 'damage': 12, 'damage_type': 'physical', 'price': 40, 'required_level': 1},
    
    # Uncommon Weapons
    {'name': 'Stahlschwert', 'type': 'weapon', 'rarity': 'uncommon', 'description': 'Ein gut geschmiedetes Stahlschwert', 'damage': 25, 'damage_type': 'physical', 'price': 200, 'required_level': 3},
    {'name': 'Kampfaxt', 'type': 'weapon', 'rarity': 'uncommon', 'description': 'Eine schwere Kampfaxt', 'damage': 30, 'damage_type': 'physical', 'price': 250, 'required_level': 4},
    
    # Rare Weapons
    {'name': 'Flammenschwert', 'type': 'weapon', 'rarity': 'rare', 'description': 'Ein mit Flammen verzaubertes Schwert', 'damage': 40, 'damage_type': 'fire', 'price': 500, 'required_level': 6},
    {'name': 'Frosthammer', 'type': 'weapon', 'rarity': 'rare', 'description': 'Ein eiskalter Kriegshammer', 'damage': 45, 'damage_type': 'ice', 'price': 550, 'required_level': 7},
    
    # Epic Weapons
    {'name': 'Blitzklinge', 'type': 'weapon', 'rarity': 'epic', 'description': 'Eine mit Blitzen geladene Klinge', 'damage': 60, 'damage_type': 'lightning', 'price': 1000, 'required_level': 10},
    
    # Common Skills
    {'name': 'Feuerball', 'type': 'skill', 'rarity': 'common', 'description': 'Wirft einen Feuerball', 'damage': 20, 'damage_type': 'fire', 'price': 100, 'required_level': 2, 'effects': json.dumps({'burn': 0.3})},
    {'name': 'Heilung', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Heilt den Spieler', 'price': 150, 'required_level': 3, 'effects': json.dumps({'heal': 30})},
    
    # Uncommon Skills
    {'name': 'Blitzstoß', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Schleudert einen Blitz', 'damage': 35, 'damage_type': 'lightning', 'price': 300, 'required_level': 5, 'effects': json.dumps({'static': 0.4})},
    {'name': 'Schildwall', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Erhöht die Verteidigung', 'price': 250, 'required_level': 4, 'effects': json.dumps({'shield': 1})},
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


async def get_player_inventory(db_helpers, user_id: int):
    """Get player's inventory."""
    try:
        if not db_helpers.db_pool:
            return []
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return []
        
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT i.*, it.name, it.type, it.rarity, it.damage, it.description
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
                    cursor.execute("""
                        INSERT INTO rpg_equipped (user_id, skill1_id)
                        VALUES (%s, %s)
                        ON DUPLICATE KEY UPDATE skill1_id = %s
                    """, (user_id, item_id, item_id))
                else:
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


async def create_custom_item(db_helpers, name: str, item_type: str, rarity: str, description: str, 
                            damage: int = 0, price: int = 100, required_level: int = 1, created_by: int = None):
    """Create a custom item (admin function)."""
    try:
        if not db_helpers.db_pool:
            return False, "Datenbank nicht verfügbar"
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return False, "Datenbankverbindung fehlgeschlagen"
        
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO rpg_items 
                (name, type, rarity, description, damage, price, required_level, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (name, item_type, rarity, description, damage, price, required_level, created_by))
            
            conn.commit()
            item_id = cursor.lastrowid
            return True, item_id
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error creating custom item: {e}", exc_info=True)
        return False, str(e)


