"""
Sulfur Bot - RPG System Module (Foundation)
Core RPG system with combat, items, skills, and progression.

NOTE: Items, skills, and monsters are stored in the DATABASE, not hardcoded.
The generation logic in rpg_items_data.py is used only to seed the database on first run.
"""

import discord
import random
import json
from datetime import datetime, timezone
from typing import Optional, Dict, List, Tuple
from modules.logger_utils import bot_logger as logger
from modules.rpg_items_data import EXTENDED_WEAPONS, EXTENDED_SKILLS


# Status Effects - Applied during combat
# These can be used by both players (via items/skills) and monsters (via abilities)
# NEW: Status effects can now STACK - multiple instances increase effectiveness
STATUS_EFFECTS = {
    'burn': {
        'name': 'Brennen', 
        'emoji': '🔥', 
        'dmg_per_turn': 5, 
        'duration': 3,
        'stackable': True,
        'max_stacks': 5,
        'description': 'Nimmt 5 Schaden pro Runde für 3 Runden (Stapelbar bis 5x)'
    },
    'poison': {
        'name': 'Vergiftung', 
        'emoji': '🧪', 
        'dmg_per_turn': 7, 
        'duration': 4,
        'stackable': True,
        'max_stacks': 3,
        'description': 'Nimmt 7 Schaden pro Runde für 4 Runden (Stapelbar bis 3x)'
    },
    'darkness': {
        'name': 'Dunkelheit', 
        'emoji': '🌑', 
        'acc_reduction': 0.3, 
        'duration': 2,
        'stackable': True,
        'max_stacks': 3,
        'description': 'Reduziert Trefferchance um 30% für 2 Runden (Stapelbar)'
    },
    'light': {
        'name': 'Licht', 
        'emoji': '✨', 
        'acc_bonus': 0.2, 
        'duration': 3,
        'stackable': True,
        'max_stacks': 3,
        'description': 'Erhöht Trefferchance um 20% für 3 Runden (Stapelbar)'
    },
    'static': {
        'name': 'Statisch', 
        'emoji': '⚡', 
        'paralyze_chance': 0.3, 
        'duration': 2,
        'stackable': True,
        'max_stacks': 3,
        'description': '30% Chance pro Runde gelähmt zu werden für 2 Runden (Stapelbar)'
    },
    'freeze': {
        'name': 'Gefroren', 
        'emoji': '❄️', 
        'immobilize': True, 
        'duration': 1,
        'stackable': False,
        'description': 'Kann für 1 Runde nicht handeln'
    },
    'heal': {
        'name': 'Regeneration', 
        'emoji': '💚', 
        'heal_per_turn': 10, 
        'duration': 3,
        'stackable': True,
        'max_stacks': 5,
        'description': 'Heilt 10 HP pro Runde für 3 Runden (Stapelbar bis 5x)'
    },
    'shield': {
        'name': 'Schild', 
        'emoji': '🛡️', 
        'dmg_reduction': 0.5, 
        'duration': 2,
        'stackable': False,
        'description': 'Reduziert eingehenden Schaden um 50% für 2 Runden'
    },
    'rage': {
        'name': 'Wut', 
        'emoji': '😡', 
        'atk_bonus': 0.5, 
        'def_reduction': 0.3, 
        'duration': 2,
        'stackable': True,
        'max_stacks': 3,
        'description': 'Erhöht Angriff um 50%, reduziert Verteidigung um 30% für 2 Runden (Stapelbar)'
    },
    # NEW TURN ORDER MANIPULATION EFFECTS
    'startled': {
        'name': 'Erschrocken',
        'emoji': '😨',
        'speed_reduction': 50,
        'duration': 1,
        'stackable': False,
        'turn_order_penalty': True,
        'description': 'Geschwindigkeit stark reduziert, handelt als letzter in der nächsten Runde'
    },
    'haste': {
        'name': 'Eile',
        'emoji': '💨',
        'speed_bonus': 30,
        'duration': 3,
        'stackable': True,
        'max_stacks': 2,
        'turn_order_bonus': True,
        'description': 'Erhöht Geschwindigkeit stark, handelt früher (Stapelbar bis 2x)'
    },
    'slow': {
        'name': 'Verlangsamt',
        'emoji': '🐌',
        'speed_reduction': 20,
        'duration': 3,
        'stackable': True,
        'max_stacks': 3,
        'description': 'Reduziert Geschwindigkeit, handelt später (Stapelbar)'
    },
    'stun': {
        'name': 'Betäubt',
        'emoji': '💫',
        'immobilize': True,
        'duration': 1,
        'stackable': False,
        'description': 'Kann für 1 Runde nicht handeln'
    },
    # NEW COMPLEX STATUS EFFECTS
    'bleed': {
        'name': 'Blutung',
        'emoji': '🩸',
        'dmg_per_turn': 8,
        'duration': 5,
        'stackable': True,
        'max_stacks': 10,
        'increases_on_move': True,
        'description': 'Nimmt 8 Schaden pro Runde für 5 Runden, erhöht bei Bewegung (Stapelbar bis 10x)'
    },
    'curse': {
        'name': 'Fluch',
        'emoji': '💀',
        'dmg_per_turn': 10,
        'acc_reduction': 0.2,
        'def_reduction': 0.2,
        'duration': 4,
        'stackable': True,
        'max_stacks': 2,
        'description': 'Nimmt 10 Schaden/Runde, -20% Trefferchance & Verteidigung (Stapelbar bis 2x)'
    },
    'barrier': {
        'name': 'Barriere',
        'emoji': '🔮',
        'dmg_reduction': 0.7,
        'duration': 2,
        'stackable': False,
        'absorb_amount': 100,
        'description': 'Absorbiert bis zu 100 Schaden, reduziert Schaden um 70%'
    },
    'berserk': {
        'name': 'Berserker',
        'emoji': '🔴',
        'atk_bonus': 0.8,
        'def_reduction': 0.5,
        'speed_bonus': 15,
        'duration': 3,
        'stackable': False,
        'description': '+80% Angriff, +15 Geschw., -50% Verteidigung für 3 Runden'
    },
    'fortify': {
        'name': 'Verstärkt',
        'emoji': '⛰️',
        'def_bonus': 0.6,
        'dmg_reduction': 0.3,
        'speed_reduction': 10,
        'duration': 3,
        'stackable': True,
        'max_stacks': 2,
        'description': '+60% Verteidigung, +30% Schadensred., -10 Geschw. (Stapelbar bis 2x)'
    },
    'weakness': {
        'name': 'Schwäche',
        'emoji': '💔',
        'atk_reduction': 0.4,
        'dmg_reduction': -0.2,
        'duration': 3,
        'stackable': True,
        'max_stacks': 3,
        'description': '-40% Angriff, nimmt 20% mehr Schaden (Stapelbar)'
    },
    'blessed': {
        'name': 'Gesegnet',
        'emoji': '🌟',
        'heal_per_turn': 15,
        'acc_bonus': 0.15,
        'crit_bonus': 0.1,
        'duration': 5,
        'stackable': False,
        'description': 'Heilt 15 HP/Runde, +15% Trefferchance, +10% Krit für 5 Runden'
    },
    'doomed': {
        'name': 'Verdammt',
        'emoji': '☠️',
        'dmg_per_turn': 15,
        'def_reduction': 0.3,
        'heal_reduction': 0.5,
        'duration': 3,
        'stackable': False,
        'description': 'Nimmt 15 Schaden/Runde, -30% Vert., -50% Heilung für 3 Runden'
    },
    'thorns': {
        'name': 'Dornen',
        'emoji': '🌹',
        'reflect_damage': 0.3,
        'duration': 4,
        'stackable': True,
        'max_stacks': 3,
        'description': 'Reflektiert 30% des erhaltenen Schadens (Stapelbar)'
    },
    'vulnerable': {
        'name': 'Verwundbar',
        'emoji': '🎯',
        'dmg_taken_increase': 0.5,
        'crit_chance_against': 0.2,
        'duration': 2,
        'stackable': True,
        'max_stacks': 2,
        'description': 'Nimmt 50% mehr Schaden, Gegner haben +20% Krit-Chance (Stapelbar)'
    },
    'evasive': {
        'name': 'Ausweichend',
        'emoji': '👻',
        'dodge_bonus': 0.3,
        'speed_bonus': 20,
        'duration': 3,
        'stackable': True,
        'max_stacks': 2,
        'description': '+30% Ausweichen, +20 Geschwindigkeit (Stapelbar bis 2x)'
    },
    'focus': {
        'name': 'Fokussiert',
        'emoji': '🎯',
        'acc_bonus': 0.4,
        'crit_bonus': 0.15,
        'duration': 3,
        'stackable': True,
        'max_stacks': 2,
        'description': '+40% Trefferchance, +15% Kritische Treffer (Stapelbar bis 2x)'
    },
    'confusion': {
        'name': 'Verwirrt',
        'emoji': '😵',
        'acc_reduction': 0.5,
        'friendly_fire_chance': 0.2,
        'duration': 2,
        'stackable': False,
        'description': '-50% Trefferchance, 20% Chance sich selbst zu treffen'
    },
    'petrify': {
        'name': 'Versteinert',
        'emoji': '🗿',
        'immobilize': True,
        'def_bonus': 1.0,
        'dmg_reduction': 0.8,
        'duration': 2,
        'stackable': False,
        'description': 'Kann nicht handeln, aber +100% Vert. & 80% Schadensred.'
    },
    'lifesteal': {
        'name': 'Lebensentzug',
        'emoji': '🧛',
        'lifesteal_percent': 0.4,
        'duration': 4,
        'stackable': True,
        'max_stacks': 3,
        'description': 'Heilt 40% des verursachten Schadens (Stapelbar)'
    }
}

# Monster Abilities - Special abilities that can be assigned to monsters
# These are triggered during combat and can apply status effects or modify combat
# AI uses these strategically based on situation (health, buffs, etc.)
MONSTER_ABILITIES = {
    # BASIC ELEMENTAL ABILITIES
    'fire_breath': {
        'name': 'Feueratem',
        'emoji': '🔥',
        'description': 'Speit Flammen und verursacht brennenden Schaden',
        'effect_type': 'status',
        'status_effect': 'burn',
        'trigger_chance': 0.3,
        'ai_condition': 'always'
    },
    'poison_spit': {
        'name': 'Giftspeier',
        'emoji': '🧪',
        'description': 'Spuckt Gift und vergiftet das Ziel',
        'effect_type': 'status',
        'status_effect': 'poison',
        'trigger_chance': 0.25,
        'ai_condition': 'always'
    },
    'shadow_cloak': {
        'name': 'Schattenumhang',
        'emoji': '🌑',
        'description': 'Hüllt sich in Schatten und erschwert das Treffen',
        'effect_type': 'status',
        'status_effect': 'darkness',
        'trigger_chance': 0.2,
        'ai_condition': 'player_high_accuracy'
    },
    'lightning_strike': {
        'name': 'Blitzschlag',
        'emoji': '⚡',
        'description': 'Schlägt mit Blitzen zu und kann lähmen',
        'effect_type': 'status',
        'status_effect': 'static',
        'trigger_chance': 0.3,
        'ai_condition': 'always'
    },
    'frost_nova': {
        'name': 'Frostnova',
        'emoji': '❄️',
        'description': 'Erzeugt eisige Kälte und friert das Ziel ein',
        'effect_type': 'status',
        'status_effect': 'freeze',
        'trigger_chance': 0.15,
        'ai_condition': 'player_high_speed'
    },
    
    # TACTICAL ABILITIES (AI uses strategically)
    'battle_roar': {
        'name': 'Kriegsschrei',
        'emoji': '😡',
        'description': 'Brüllt wütend und erhöht die eigene Stärke',
        'effect_type': 'self_buff',
        'status_effect': 'rage',
        'trigger_chance': 0.25,
        'ai_condition': 'low_health_or_start'
    },
    'regeneration': {
        'name': 'Regeneration',
        'emoji': '💚',
        'description': 'Heilt sich selbst über mehrere Runden',
        'effect_type': 'self_buff',
        'status_effect': 'heal',
        'trigger_chance': 0.2,
        'ai_condition': 'low_health'
    },
    'armor_up': {
        'name': 'Panzerung',
        'emoji': '🛡️',
        'description': 'Verstärkt die Rüstung und reduziert Schaden',
        'effect_type': 'self_buff',
        'status_effect': 'shield',
        'trigger_chance': 0.2,
        'ai_condition': 'player_high_damage'
    },
    
    # DAMAGE ABILITIES
    'critical_strike': {
        'name': 'Kritischer Schlag',
        'emoji': '💥',
        'description': 'Führt einen verheerenden kritischen Angriff aus',
        'effect_type': 'damage_boost',
        'damage_multiplier': 2.5,
        'trigger_chance': 0.2,
        'ai_condition': 'always'
    },
    'life_drain': {
        'name': 'Lebensentzug',
        'emoji': '🩸',
        'description': 'Stiehlt Leben vom Ziel und heilt sich selbst',
        'effect_type': 'lifesteal',
        'lifesteal_percent': 0.5,
        'trigger_chance': 0.25,
        'ai_condition': 'low_health'
    },
    
    # NEW TURN ORDER MANIPULATION ABILITIES
    'terrifying_roar': {
        'name': 'Schrecklicher Schrei',
        'emoji': '😱',
        'description': 'Erschreckt den Gegner, der langsamer wird',
        'effect_type': 'status',
        'status_effect': 'startled',
        'trigger_chance': 0.2,
        'ai_condition': 'player_faster'
    },
    'time_warp': {
        'name': 'Zeitverzerrung',
        'emoji': '⏰',
        'description': 'Verzerrt die Zeit und wird schneller',
        'effect_type': 'self_buff',
        'status_effect': 'haste',
        'trigger_chance': 0.2,
        'ai_condition': 'player_faster'
    },
    'crippling_strike': {
        'name': 'Verkrüppelnder Schlag',
        'emoji': '🦴',
        'description': 'Verlangsamt den Gegner mit einem Schlag',
        'effect_type': 'status',
        'status_effect': 'slow',
        'trigger_chance': 0.25,
        'ai_condition': 'always'
    },
    'stunning_blow': {
        'name': 'Betäubender Schlag',
        'emoji': '💫',
        'description': 'Betäubt den Gegner für eine Runde',
        'effect_type': 'status',
        'status_effect': 'stun',
        'trigger_chance': 0.15,
        'ai_condition': 'player_low_health'
    },
    
    # NEW COMPLEX ABILITIES
    'savage_bite': {
        'name': 'Wilder Biss',
        'emoji': '🦷',
        'description': 'Beißt zu und verursacht starke Blutung',
        'effect_type': 'status',
        'status_effect': 'bleed',
        'trigger_chance': 0.3,
        'ai_condition': 'always'
    },
    'dark_curse': {
        'name': 'Dunkler Fluch',
        'emoji': '💀',
        'description': 'Verflucht den Gegner mit dunkler Magie',
        'effect_type': 'status',
        'status_effect': 'curse',
        'trigger_chance': 0.2,
        'ai_condition': 'player_high_stats'
    },
    'arcane_barrier': {
        'name': 'Arkane Barriere',
        'emoji': '🔮',
        'description': 'Erschafft eine magische Schutzbarriere',
        'effect_type': 'self_buff',
        'status_effect': 'barrier',
        'trigger_chance': 0.15,
        'ai_condition': 'low_health'
    },
    'berserk_fury': {
        'name': 'Rasende Wut',
        'emoji': '🔴',
        'description': 'Verfällt in Berserker-Wut',
        'effect_type': 'self_buff',
        'status_effect': 'berserk',
        'trigger_chance': 0.2,
        'ai_condition': 'low_health'
    },
    'stone_skin': {
        'name': 'Steinhaut',
        'emoji': '⛰️',
        'description': 'Verhärtet die Haut zu Stein',
        'effect_type': 'self_buff',
        'status_effect': 'fortify',
        'trigger_chance': 0.2,
        'ai_condition': 'player_high_damage'
    },
    'enfeeble': {
        'name': 'Schwächen',
        'emoji': '💔',
        'description': 'Schwächt den Gegner erheblich',
        'effect_type': 'status',
        'status_effect': 'weakness',
        'trigger_chance': 0.25,
        'ai_condition': 'player_high_damage'
    },
    'divine_blessing': {
        'name': 'Göttlicher Segen',
        'emoji': '🌟',
        'description': 'Segnet sich selbst mit göttlicher Kraft',
        'effect_type': 'self_buff',
        'status_effect': 'blessed',
        'trigger_chance': 0.15,
        'ai_condition': 'low_health'
    },
    'death_mark': {
        'name': 'Todeszeichen',
        'emoji': '☠️',
        'description': 'Markiert den Gegner für den Tod',
        'effect_type': 'status',
        'status_effect': 'doomed',
        'trigger_chance': 0.2,
        'ai_condition': 'player_low_health'
    },
    'thorn_armor': {
        'name': 'Dornenrüstung',
        'emoji': '🌹',
        'description': 'Bedeckt sich mit schmerzhaften Dornen',
        'effect_type': 'self_buff',
        'status_effect': 'thorns',
        'trigger_chance': 0.2,
        'ai_condition': 'player_high_damage'
    },
    'expose_weakness': {
        'name': 'Schwäche Aufdecken',
        'emoji': '🎯',
        'description': 'Deckt Schwachstellen des Gegners auf',
        'effect_type': 'status',
        'status_effect': 'vulnerable',
        'trigger_chance': 0.25,
        'ai_condition': 'always'
    },
    'shadow_step': {
        'name': 'Schattenschritt',
        'emoji': '👻',
        'description': 'Wird schwer zu treffen',
        'effect_type': 'self_buff',
        'status_effect': 'evasive',
        'trigger_chance': 0.2,
        'ai_condition': 'player_high_accuracy'
    },
    'hunters_focus': {
        'name': 'Jägerfokus',
        'emoji': '🎯',
        'description': 'Fokussiert sich auf das Ziel',
        'effect_type': 'self_buff',
        'status_effect': 'focus',
        'trigger_chance': 0.2,
        'ai_condition': 'always'
    },
    'mind_blast': {
        'name': 'Geistesstoß',
        'emoji': '😵',
        'description': 'Verwirrt den Geist des Gegners',
        'effect_type': 'status',
        'status_effect': 'confusion',
        'trigger_chance': 0.15,
        'ai_condition': 'player_high_accuracy'
    },
    'petrifying_gaze': {
        'name': 'Versteinernder Blick',
        'emoji': '🗿',
        'description': 'Versteinert den Gegner kurzzeitig',
        'effect_type': 'status',
        'status_effect': 'petrify',
        'trigger_chance': 0.1,
        'ai_condition': 'player_low_health'
    },
    'vampiric_aura': {
        'name': 'Vampirische Aura',
        'emoji': '🧛',
        'description': 'Umgibt sich mit lebensentziehender Aura',
        'effect_type': 'self_buff',
        'status_effect': 'lifesteal',
        'trigger_chance': 0.2,
        'ai_condition': 'low_health'
    },
    
    # MULTI-HIT ABILITIES
    'flurry': {
        'name': 'Hagel',
        'emoji': '🌪️',
        'description': 'Schnelle Serie von Angriffen',
        'effect_type': 'multi_hit',
        'hit_count': 3,
        'damage_per_hit': 0.4,
        'trigger_chance': 0.2,
        'ai_condition': 'always'
    },
    'whirlwind_attack': {
        'name': 'Wirbelwindangriff',
        'emoji': '🌀',
        'description': 'Wirbelt herum und greift mehrfach an',
        'effect_type': 'multi_hit',
        'hit_count': 2,
        'damage_per_hit': 0.6,
        'trigger_chance': 0.25,
        'ai_condition': 'always'
    },
    
    # UTILITY ABILITIES
    'cleanse': {
        'name': 'Reinigung',
        'emoji': '✨',
        'description': 'Entfernt negative Statuseffekte',
        'effect_type': 'cleanse',
        'trigger_chance': 0.2,
        'ai_condition': 'has_debuff'
    },
    'enrage': {
        'name': 'Wutanfall',
        'emoji': '😤',
        'description': 'Wird vor Wut rasend, wenn verletzt',
        'effect_type': 'triggered',
        'status_effect': 'berserk',
        'trigger_condition': 'below_50_hp',
        'trigger_chance': 1.0,
        'ai_condition': 'low_health'
    },
    'last_stand': {
        'name': 'Letztes Gefecht',
        'emoji': '⚔️',
        'description': 'Kämpft verzweifelt, wenn dem Tod nahe',
        'effect_type': 'triggered',
        'status_effect': 'berserk',
        'damage_boost': 1.5,
        'trigger_condition': 'below_25_hp',
        'trigger_chance': 1.0,
        'ai_condition': 'critical_health'
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
            'strength_training': {
                'name': 'Krafttraining',
                'type': 'stat',
                'description': '+5 Stärke',
                'cost': 1,
                'requires': None,
                'effect': {'strength': 5}
            },
            'defense_training': {
                'name': 'Verteidigungstraining',
                'type': 'stat',
                'description': '+5 Verteidigung',
                'cost': 1,
                'requires': None,
                'effect': {'defense': 5}
            },
            'power_strike': {
                'name': 'Machtschlag',
                'type': 'skill',
                'description': 'Fügt 150% Waffenschaden zu',
                'cost': 2,
                'requires': 'strength_training',
                'effect': {'damage_multiplier': 1.5, 'cooldown': 2}
            },
            'shield_bash': {
                'name': 'Schildstoß',
                'type': 'skill',
                'description': 'Betäubt den Gegner für 1 Runde und fügt Schaden zu',
                'cost': 2,
                'requires': 'defense_training',
                'effect': {'damage': 30, 'stun_duration': 1, 'cooldown': 3}
            },
            'fortified_stance': {
                'name': 'Verstärkte Haltung',
                'type': 'stat',
                'description': '+10 Verteidigung, +20 Max HP',
                'cost': 2,
                'requires': 'defense_training',
                'effect': {'defense': 10, 'max_health': 20}
            },
            'battle_rage': {
                'name': 'Kampfwut',
                'type': 'skill',
                'description': 'Erhöht Stärke um 15 für 3 Runden',
                'cost': 3,
                'requires': 'power_strike',
                'effect': {'strength_buff': 15, 'duration': 3, 'cooldown': 4}
            },
            'whirlwind': {
                'name': 'Wirbelwind',
                'type': 'skill',
                'description': 'Angriff der 200% Schaden verursacht',
                'cost': 3,
                'requires': 'power_strike',
                'effect': {'damage_multiplier': 2.0, 'cooldown': 3}
            }
        }
    },
    
    # Rogue Path - Focuses on dexterity and critical hits
    'rogue': {
        'name': 'Schurke',
        'emoji': '🗡️',
        'description': 'Meister der Geschicklichkeit und kritischen Treffer',
        'skills': {
            'agility_training': {
                'name': 'Beweglichkeitstraining',
                'type': 'stat',
                'description': '+5 Geschwindigkeit',
                'cost': 1,
                'requires': None,
                'effect': {'speed': 5}
            },
            'dexterity_training': {
                'name': 'Geschicklichkeitstraining',
                'type': 'stat',
                'description': '+5 Geschicklichkeit',
                'cost': 1,
                'requires': None,
                'effect': {'dexterity': 5}
            },
            'rapid_strike': {
                'name': 'Schneller Schlag',
                'type': 'skill',
                'description': 'Zwei schnelle Angriffe mit je 75% Schaden',
                'cost': 2,
                'requires': 'agility_training',
                'effect': {'hits': 2, 'damage_multiplier': 0.75, 'cooldown': 2}
            },
            'evasion': {
                'name': 'Ausweichen',
                'type': 'skill',
                'description': 'Weicht dem nächsten Angriff aus',
                'cost': 2,
                'requires': 'agility_training',
                'effect': {'dodge_next': True, 'cooldown': 3}
            },
            'precision_strike': {
                'name': 'Präzisionsschlag',
                'type': 'stat',
                'description': '+8 Geschicklichkeit',
                'cost': 2,
                'requires': 'dexterity_training',
                'effect': {'dexterity': 8}
            },
            'backstab': {
                'name': 'Meucheln',
                'type': 'skill',
                'description': 'Kritischer Angriff mit 250% Schaden',
                'cost': 3,
                'requires': 'rapid_strike',
                'effect': {'damage_multiplier': 2.5, 'guaranteed_crit': True, 'cooldown': 4}
            },
            'shadow_dance': {
                'name': 'Schattentanz',
                'type': 'skill',
                'description': 'Erhöht Geschwindigkeit um 20 für 2 Runden',
                'cost': 3,
                'requires': 'evasion',
                'effect': {'speed_buff': 20, 'duration': 2, 'cooldown': 4}
            }
        }
    },
    
    # Mage Path - Focuses on magic and special effects
    'mage': {
        'name': 'Magier',
        'emoji': '🔮',
        'description': 'Meister der arkanen Künste und Elemente',
        'skills': {
            'intelligence_training': {
                'name': 'Intelligenztraining',
                'type': 'stat',
                'description': '+5 Stärke (Magie nutzt Stärke für Schaden)',
                'cost': 1,
                'requires': None,
                'effect': {'strength': 5}
            },
            'vitality_training': {
                'name': 'Vitalitätstraining',
                'type': 'stat',
                'description': '+15 Max HP',
                'cost': 1,
                'requires': None,
                'effect': {'max_health': 15}
            },
            'fireball': {
                'name': 'Feuerball',
                'type': 'skill',
                'description': 'Feuert einen Feuerball der 120% magischen Schaden verursacht',
                'cost': 2,
                'requires': 'intelligence_training',
                'effect': {'damage_multiplier': 1.2, 'element': 'fire', 'cooldown': 2}
            },
            'frost_bolt': {
                'name': 'Frostblitz',
                'type': 'skill',
                'description': 'Verursacht 100% Schaden und verlangsamt Gegner',
                'cost': 2,
                'requires': 'intelligence_training',
                'effect': {'damage_multiplier': 1.0, 'slow_duration': 2, 'element': 'ice', 'cooldown': 2}
            },
            'arcane_intellect': {
                'name': 'Arkane Intelligenz',
                'type': 'stat',
                'description': '+8 Stärke, +10 Max HP',
                'cost': 2,
                'requires': 'intelligence_training',
                'effect': {'strength': 8, 'max_health': 10}
            },
            'chain_lightning': {
                'name': 'Kettenblitz',
                'type': 'skill',
                'description': 'Blitz der 180% Schaden verursacht',
                'cost': 3,
                'requires': 'fireball',
                'effect': {'damage_multiplier': 1.8, 'element': 'lightning', 'cooldown': 3}
            },
            'meteor_strike': {
                'name': 'Meteorschlag',
                'type': 'skill',
                'description': 'Gewaltiger Meteor der 300% Schaden verursacht',
                'cost': 3,
                'requires': 'arcane_intellect',
                'effect': {'damage_multiplier': 3.0, 'element': 'fire', 'cooldown': 5}
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

# Worlds - Progressive difficulty with better loot
WORLDS = {
    'overworld': {
        'name': 'Oberwelt', 
        'min_level': 1, 
        'max_level': 10,
        'description': 'Grüne Wiesen und dichte Wälder',
        'loot_multiplier': 1.0
    },
    'underworld': {
        'name': 'Unterwelt', 
        'min_level': 10, 
        'max_level': 25,
        'description': 'Feurige Höhlen und dunkle Abgründe',
        'loot_multiplier': 1.5
    },
    'shadowlands': {
        'name': 'Schattenland',
        'min_level': 25,
        'max_level': 40,
        'description': 'Reich der ewigen Dunkelheit',
        'loot_multiplier': 2.0
    },
    'frozen_wastes': {
        'name': 'Frostöde',
        'min_level': 40,
        'max_level': 60,
        'description': 'Eisige Tundra voller Gefahren',
        'loot_multiplier': 2.5
    },
    'void': {
        'name': 'Die Leere',
        'min_level': 60,
        'max_level': 100,
        'description': 'Jenseits von Raum und Zeit',
        'loot_multiplier': 3.0
    }
}

# Game Balance Constants
BASE_STAT_VALUE = 10  # Base value for all stats (strength, dexterity, defense, speed)
DEFAULT_DEXTERITY = 10  # Default dexterity value when not specified
LEVEL_REWARD_MULTIPLIER = 0.1  # Multiplier for scaling rewards based on player level
RESPEC_COST_PER_POINT = 50  # Gold cost per skill point when resetting stats

# Loot system constants
LUCK_BONUS_MAX = 0.05  # Maximum luck bonus to drop rates (5%)
LUCK_BONUS_PER_LEVEL = 0.001  # Luck bonus gained per player level
DEFAULT_DROP_RATE = 0.1  # Default drop rate (10%) for items without explicit rate

# Quest item constants
QUEST_ITEM_BASE_PRICE = 5  # Base gold value for quest items
MATERIAL_ITEM_MIN_PRICE = 10  # Minimum price for material items
MATERIAL_ITEM_MAX_PRICE = 50  # Maximum price for material items


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
                    uses_remaining INT DEFAULT NULL,
                    UNIQUE KEY unique_user_item (user_id, item_id, item_type),
                    INDEX idx_user (user_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Add uses_remaining column if it doesn't exist (migration)
            try:
                cursor.execute("""
                    ALTER TABLE rpg_inventory ADD COLUMN IF NOT EXISTS uses_remaining INT DEFAULT NULL
                """)
            except Exception:
                pass  # Column might already exist
            
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
                    max_uses INT DEFAULT NULL,
                    price INT DEFAULT 100,
                    required_level INT DEFAULT 1,
                    created_by BIGINT NULL,
                    is_quest_item BOOLEAN DEFAULT FALSE,
                    is_sellable BOOLEAN DEFAULT TRUE,
                    is_usable BOOLEAN DEFAULT TRUE,
                    quest_id VARCHAR(100) NULL,
                    INDEX idx_type (type),
                    INDEX idx_rarity (rarity),
                    INDEX idx_quest (is_quest_item)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Add max_uses column if it doesn't exist (migration)
            try:
                cursor.execute("""
                    ALTER TABLE rpg_items ADD COLUMN IF NOT EXISTS max_uses INT DEFAULT NULL
                """)
            except Exception:
                pass  # Column might already exist
            
            # Daily shop rotation - stores which items are available each day
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rpg_daily_shop (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    shop_date DATE NOT NULL UNIQUE,
                    item_ids JSON NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_date (shop_date)
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
            # First update max_health, then set health to new max_health (capped properly)
            cursor.execute("""
                UPDATE rpg_players 
                SET level = %s, xp = %s, skill_points = skill_points + %s,
                    max_health = max_health + %s, 
                    health = LEAST(health + %s, max_health + %s)
                WHERE user_id = %s
            """, (new_level, new_xp, skill_points_gained, hp_increase, hp_increase, hp_increase, user_id))
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


# Default Monsters with abilities and LOOT TABLES
# Loot tables define what items can drop from each monster category
# Format: {item_name: drop_rate} where drop_rate is 0.0-1.0
# Monster data is now stored in rpg_monsters_data.py module (following the same pattern as items)


async def initialize_default_monsters(db_helpers):
    """
    Initialize monsters in the database.
    Monsters are only generated once on first run, then loaded from database.
    """
    # Import monster data from separate module (lazy import to avoid circular dependencies)
    from modules.rpg_monsters_data import get_base_monsters_data
    
    try:
        if not db_helpers.db_pool:
            logger.warning("Database pool not available for monster initialization")
            return
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            logger.warning("Could not get database connection for monster initialization")
            return
        
        cursor = conn.cursor()
        try:
            # Check if monsters exist
            cursor.execute("SELECT COUNT(*) FROM rpg_monsters")
            count = cursor.fetchone()[0]
            
            logger.info(f"Found {count} monsters in database")
            
            # Initialize if we have NO monsters or fewer than expected minimum (20)
            # This ensures initialization happens on first run or after database reset
            if count < 20:
                if count == 0:
                    logger.warning("No monsters found in database! Initializing for the first time...")
                else:
                    logger.warning(f"Only {count} monsters found (expected at least 20). Re-initializing...")
                
                # Get monster data from the imported module
                all_monsters = get_base_monsters_data()
                logger.info(f"Generated {len(all_monsters)} monsters for seeding")
                
                # Clear existing monsters first if reinitializing
                if count > 0:
                    cursor.execute("DELETE FROM rpg_monsters")
                    logger.info(f"Cleared {count} existing monsters for reinitializing")
                
                # Insert all monsters with abilities and loot tables
                inserted = 0
                failed = 0
                for monster in all_monsters:
                    try:
                        abilities_json = json.dumps(monster.get('abilities', []))
                        loot_table_json = json.dumps(monster.get('loot_table', {}))
                        cursor.execute("""
                            INSERT INTO rpg_monsters 
                            (name, world, level, health, strength, defense, speed, xp_reward, gold_reward, abilities, loot_table)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            monster['name'], 
                            monster['world'], 
                            monster['level'], 
                            monster['health'],
                            monster['strength'], 
                            monster['defense'], 
                            monster['speed'],
                            monster['xp_reward'], 
                            monster['gold_reward'], 
                            abilities_json, 
                            loot_table_json
                        ))
                        inserted += 1
                    except Exception as e:
                        failed += 1
                        if failed <= 5:  # Only log first 5 failures
                            logger.warning(f"Failed to insert monster {monster.get('name', 'Unknown')}: {e}")
                
                conn.commit()
                logger.info(f"Successfully initialized {inserted} monsters with loot tables ({failed} failed)")
            else:
                logger.info(f"Monsters already initialized ({count} monsters)")
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
            
            # Fallback 1: Try wider level range in same world
            if not monster:
                logger.warning(f"No monster found for world={world}, level {min_level}-{max_level}. Trying wider range...")
                cursor.execute("""
                    SELECT * FROM rpg_monsters
                    WHERE world = %s
                    ORDER BY RAND()
                    LIMIT 1
                """, (world,))
                monster = cursor.fetchone()
            
            # Fallback 2: Try any world with similar level
            if not monster:
                logger.warning(f"No monster found in world={world}. Trying any world with similar level...")
                cursor.execute("""
                    SELECT * FROM rpg_monsters
                    WHERE level BETWEEN %s AND %s
                    ORDER BY RAND()
                    LIMIT 1
                """, (min_level, max_level))
                monster = cursor.fetchone()
            
            # Fallback 3: Get ANY monster
            if not monster:
                logger.error("No monsters found with level criteria. Getting ANY monster...")
                cursor.execute("""
                    SELECT * FROM rpg_monsters
                    ORDER BY RAND()
                    LIMIT 1
                """)
                monster = cursor.fetchone()
            
            # If still no monster, database is empty - try to initialize
            if not monster:
                logger.error("No monsters in database at all! Attempting to initialize...")
                new_conn = None
                new_cursor = None
                try:
                    cursor.close()
                    conn.close()
                    await initialize_default_monsters(db_helpers)
                    
                    # Try one more time
                    new_conn = db_helpers.db_pool.get_connection()
                    if not new_conn:
                        logger.error("Failed to get database connection after initialization")
                        return None
                    
                    new_cursor = new_conn.cursor(dictionary=True)
                    new_cursor.execute("""
                        SELECT * FROM rpg_monsters
                        ORDER BY RAND()
                        LIMIT 1
                    """)
                    monster = new_cursor.fetchone()
                    
                    # Update conn and cursor references for cleanup in finally block
                    conn = new_conn
                    cursor = new_cursor
                    
                    if not monster:
                        logger.error("Failed to initialize monsters! Database may have issues.")
                        return None
                except Exception as init_error:
                    logger.error(f"Error during monster initialization: {init_error}", exc_info=True)
                    # Clean up the new connection if it was created
                    if new_cursor:
                        try:
                            new_cursor.close()
                        except Exception as e:
                            logger.debug(f"Error closing cursor during cleanup: {e}")
                    if new_conn:
                        try:
                            new_conn.close()
                        except Exception as e:
                            logger.debug(f"Error closing connection during cleanup: {e}")
                    return None
            
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
                
                # Parse loot table JSON if present
                if monster.get('loot_table'):
                    if isinstance(monster['loot_table'], str):
                        monster['loot_table'] = json.loads(monster['loot_table'])
                else:
                    monster['loot_table'] = {}
                
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
    
    Uses a balanced damage formula where:
    - Defense reduces damage by a percentage (damage reduction formula)
    - Higher defense = more damage reduction, but never fully negates damage
    - Critical hits deal bonus damage
    
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
    
    # NEW BALANCED DAMAGE FORMULA:
    # Defense provides percentage-based damage reduction using diminishing returns
    # Formula: damage = attack * (100 / (100 + defense))
    # This means:
    #   - 0 defense = 100% damage taken
    #   - 50 defense = ~67% damage taken (33% reduction)
    #   - 100 defense = 50% damage taken (50% reduction)
    #   - 200 defense = ~33% damage taken (67% reduction)
    # Defense is never fully negated but always meaningful
    
    # Base damage is the attacker's strength
    base_damage = attacker_str
    
    # Apply defense reduction (diminishing returns formula)
    defense_multiplier = 100.0 / (100.0 + defender_def)
    damage_after_defense = base_damage * defense_multiplier
    
    # Ensure minimum damage of 1 (glancing blow)
    damage_after_defense = max(1.0, damage_after_defense)
    
    # Add variance (70% - 130% for more unpredictable combat)
    variance = random.uniform(0.70, 1.30)
    damage = int(damage_after_defense * variance)
    
    # Critical hit chance: 10% + (dex / 200)
    crit_chance = 0.10 + (attacker_dex / 200.0)
    
    # AI has higher crit chance when player is low health
    if is_ai and player_health_pct < 0.3:
        crit_chance += 0.15
    
    crit_chance = min(0.30, crit_chance)  # Cap at 30%
    
    if random.random() < crit_chance:
        result['crit'] = True
        damage = int(damage * 1.75)  # 175% damage on crit (up from 150%)
    
    # Ensure minimum damage of 1
    result['damage'] = max(1, damage)
    return result


async def roll_loot_drops(db_helpers, monster: dict, player_level: int) -> list:
    """
    Roll for loot drops from a defeated monster based on its loot table.
    
    Loot table format: {item_name: drop_rate} or {item_name: {"rate": float, "type": "weapon"|"skill"|"material"}}
    - item_name: String, can contain "(Quest)" suffix for quest items
    - drop_rate: Float 0.0-1.0 (probability of drop) OR dict with rate and type
    
    Example: 
      {'Wolfszahn': 0.75, 'Wolfsherz (Quest)': 0.20}
      {'Rostiges Schwert': {"rate": 0.1, "type": "weapon"}, 'Feuerball': {"rate": 0.05, "type": "skill"}}
    
    Args:
        db_helpers: Database helpers module
        monster: Monster dictionary with loot_table field
        player_level: Player's level (affects drop rates slightly)
    
    Returns:
        List of item dictionaries that dropped
    """
    try:
        loot_table = monster.get('loot_table', {})
        if not loot_table:
            return []
        
        # Parse loot_table if it's a JSON string
        if isinstance(loot_table, str):
            try:
                loot_table = json.loads(loot_table)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse loot_table JSON: {loot_table[:100]}...")
                return []
        
        dropped_items = []
        
        # Small luck bonus based on player level (configured by LUCK_BONUS constants)
        luck_bonus = min(LUCK_BONUS_MAX, player_level * LUCK_BONUS_PER_LEVEL)
        
        for item_name, drop_info in loot_table.items():
            # Handle both simple float and dict formats
            if isinstance(drop_info, dict):
                base_drop_rate = drop_info.get('rate', DEFAULT_DROP_RATE)
                item_type = drop_info.get('type', 'material')
            else:
                base_drop_rate = float(drop_info) if drop_info else DEFAULT_DROP_RATE
                item_type = 'quest_item' if '(Quest)' in item_name else 'material'
            
            # Apply luck bonus
            drop_rate = min(1.0, base_drop_rate + luck_bonus)
            
            # Roll for drop
            if random.random() < drop_rate:
                dropped_items.append({
                    'name': item_name,
                    'drop_rate': base_drop_rate,
                    'item_type': item_type,
                    'is_quest_item': '(Quest)' in item_name or item_type == 'quest_item'
                })
        
        return dropped_items
    except Exception as e:
        logger.error(f"Error rolling loot drops: {e}", exc_info=True)
        return []


async def add_loot_to_inventory(db_helpers, user_id: int, loot_items: list, monster_name: str = "Monster"):
    """
    Add dropped loot items to player's inventory.
    Supports weapons, skills, and materials. Creates items as needed.
    
    Args:
        db_helpers: Database helpers module
        user_id: Player's user ID
        loot_items: List of loot item dictionaries
        monster_name: Name of the monster that dropped the loot
    
    Returns:
        Success boolean and list of added item names
    """
    try:
        if not db_helpers.db_pool or not loot_items:
            return True, []
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return False, []
        
        cursor = conn.cursor(dictionary=True)
        added_items = []
        
        try:
            for loot in loot_items:
                item_name = loot['name']
                item_type = loot.get('item_type', 'material')
                is_quest = loot.get('is_quest_item', False)
                
                # Check if item exists in rpg_items
                cursor.execute("""
                    SELECT id, type FROM rpg_items WHERE name = %s LIMIT 1
                """, (item_name,))
                
                item_row = cursor.fetchone()
                
                if item_row:
                    item_id = item_row['id']
                    actual_type = item_row['type']
                else:
                    # Create the item based on its type
                    if item_type in ('weapon', 'skill'):
                        # For weapons/skills dropped as loot, create with basic stats
                        # These are typically monster-specific variants
                        rarity = 'uncommon'  # Loot drops are at least uncommon
                        damage = 15 if item_type == 'weapon' else 20 if item_type == 'skill' else 0
                        price = 100 if item_type == 'weapon' else 80
                        
                        cursor.execute("""
                            INSERT INTO rpg_items 
                            (name, type, rarity, description, damage, price, is_quest_item, is_usable, is_sellable, required_level)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            item_name,
                            item_type,
                            rarity,
                            f'Von {monster_name} erbeutet',
                            damage,
                            price,
                            False,
                            True,  # Usable in combat
                            True,  # Can be sold
                            1      # Level 1 requirement for loot
                        ))
                    else:
                        # Material or quest item
                        cursor.execute("""
                            INSERT INTO rpg_items 
                            (name, type, rarity, description, price, is_quest_item, is_usable, is_sellable)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            item_name,
                            'quest_item' if is_quest else 'material',
                            'common',
                            f'Von {monster_name} erbeutet',
                            QUEST_ITEM_BASE_PRICE if is_quest else random.randint(MATERIAL_ITEM_MIN_PRICE, MATERIAL_ITEM_MAX_PRICE),
                            is_quest,
                            False,  # Not usable in combat
                            not is_quest  # Quest items can't be sold
                        ))
                    item_id = cursor.lastrowid
                    actual_type = item_type
                
                # Add to inventory
                cursor.execute("""
                    INSERT INTO rpg_inventory (user_id, item_id, item_type, quantity)
                    VALUES (%s, %s, %s, 1)
                    ON DUPLICATE KEY UPDATE quantity = quantity + 1
                """, (user_id, item_id, actual_type))
                
                added_items.append(item_name)
            
            conn.commit()
            return True, added_items
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error adding loot to inventory: {e}", exc_info=True)
        return False, []


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
        
        # Initialize level up tracking - always set these to avoid KeyError
        event['leveled_up'] = False
        event['new_level'] = None
        
        # Process XP first (this uses its own database connection)
        # Do this BEFORE opening our connection to avoid nested connections
        xp_reward = event.get('xp_reward', 0)
        if xp_reward and xp_reward > 0:
            xp_result = await gain_xp(db_helpers, user_id, xp_reward)
            if xp_result:
                event['leveled_up'] = xp_result.get('leveled_up', False)
                if event['leveled_up']:
                    event['new_level'] = xp_result.get('new_level')
        
        # Now handle gold and healing with a single connection
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return False, "Datenbankverbindung fehlgeschlagen"
        
        cursor = conn.cursor()
        try:
            # Award gold
            gold_reward = event.get('gold_reward', 0)
            if gold_reward and gold_reward > 0:
                cursor.execute("""
                    UPDATE rpg_players SET gold = gold + %s WHERE user_id = %s
                """, (gold_reward, user_id))
            
            # Heal player
            heal_amount = event.get('heal_amount', 0)
            if heal_amount and heal_amount > 0:
                cursor.execute("""
                    UPDATE rpg_players SET health = LEAST(health + %s, max_health) WHERE user_id = %s
                """, (heal_amount, user_id))
            
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


def check_ai_condition(condition: str, monster: dict, player: dict, combat_state: dict) -> bool:
    """
    Check if an AI condition is met for ability usage.
    
    Args:
        condition: The AI condition string
        monster: Monster dictionary
        player: Player dictionary  
        combat_state: Current combat state with status effects
    
    Returns:
        True if condition is met
    """
    # Prevent division by zero with safe defaults
    monster_max_health = monster.get('max_health', monster['health']) or 1
    player_max_health = player.get('max_health', 100) or 1
    monster_health_pct = monster['health'] / monster_max_health
    player_health_pct = player['health'] / player_max_health
    
    if condition == 'always':
        return True
    elif condition == 'low_health':
        return monster_health_pct < 0.5
    elif condition == 'critical_health':
        return monster_health_pct < 0.25
    elif condition == 'low_health_or_start':
        return monster_health_pct < 0.5 or combat_state.get('turn_count', 0) <= 1
    elif condition == 'player_low_health':
        return player_health_pct < 0.3
    elif condition == 'player_high_damage':
        return player['strength'] > monster['strength'] * 1.2
    elif condition == 'player_faster':
        return player['speed'] > monster['speed']
    elif condition == 'player_high_accuracy':
        return player.get('dexterity', DEFAULT_DEXTERITY) > monster.get('speed', 10)
    elif condition == 'player_high_stats':
        player_total = player['strength'] + player['defense'] + player['speed']
        monster_total = monster['strength'] + monster['defense'] + monster['speed']
        return player_total > monster_total * 1.1
    elif condition == 'has_debuff':
        # Check if monster has any negative status effects
        monster_effects = combat_state.get('monster_effects', {})
        debuff_types = ['burn', 'poison', 'darkness', 'slow', 'weakness', 'curse', 'bleed', 'doomed']
        return any(effect in monster_effects for effect in debuff_types)
    else:
        return True


def try_monster_ability(monster: dict, player: dict, combat_state: dict) -> Optional[dict]:
    """
    Try to use a monster ability based on AI conditions.
    
    Returns:
        Ability data if triggered, None otherwise
    """
    abilities = monster.get('abilities', [])
    if not abilities:
        return None
    
    # Shuffle abilities to add variety
    shuffled_abilities = list(abilities)
    random.shuffle(shuffled_abilities)
    
    for ability_key in shuffled_abilities:
        ability = MONSTER_ABILITIES.get(ability_key)
        if not ability:
            continue
        
        # Check AI condition
        condition = ability.get('ai_condition', 'always')
        if not check_ai_condition(condition, monster, player, combat_state):
            continue
        
        # Check trigger chance
        trigger_chance = ability.get('trigger_chance', 0.2)
        if random.random() < trigger_chance:
            return {'key': ability_key, **ability}
    
    return None


def apply_status_effect(target_effects: dict, effect_key: str, stacks: int = 1) -> Tuple[bool, str]:
    """
    Apply a status effect to a target.
    
    Args:
        target_effects: Dictionary of current status effects on target
        effect_key: The status effect key
        stacks: Number of stacks to apply
    
    Returns:
        (success, message) tuple
    """
    effect = STATUS_EFFECTS.get(effect_key)
    if not effect:
        return False, ""
    
    if effect_key in target_effects:
        # Already has effect - check if stackable
        if effect.get('stackable', False):
            current_stacks = target_effects[effect_key].get('stacks', 1)
            max_stacks = effect.get('max_stacks', 3)
            new_stacks = min(current_stacks + stacks, max_stacks)
            if new_stacks > current_stacks:
                target_effects[effect_key]['stacks'] = new_stacks
                target_effects[effect_key]['duration'] = effect['duration']  # Refresh duration
                return True, f"{effect['emoji']} {effect['name']} verstärkt! (x{new_stacks})"
            else:
                return False, ""  # Max stacks reached
        else:
            # Refresh duration for non-stackable
            target_effects[effect_key]['duration'] = effect['duration']
            return True, f"{effect['emoji']} {effect['name']} erneuert!"
    else:
        # Apply new effect
        target_effects[effect_key] = {
            'duration': effect['duration'],
            'stacks': stacks
        }
        return True, f"{effect['emoji']} {effect['name']} angewendet!"


def process_status_effects(target_effects: dict, target_health: int, max_health: int, target_name: str) -> Tuple[int, List[str]]:
    """
    Process status effects at the start of a turn.
    
    Args:
        target_effects: Dictionary of status effects on target
        target_health: Current health
        max_health: Maximum health
        target_name: Name for messages
    
    Returns:
        (health_change, messages) tuple
    """
    messages = []
    health_change = 0
    effects_to_remove = []
    
    for effect_key, effect_data in target_effects.items():
        effect = STATUS_EFFECTS.get(effect_key)
        if not effect:
            effects_to_remove.append(effect_key)
            continue
        
        stacks = effect_data.get('stacks', 1)
        
        # Apply damage over time
        if 'dmg_per_turn' in effect:
            dot_damage = effect['dmg_per_turn'] * stacks
            health_change -= dot_damage
            messages.append(f"{effect['emoji']} {target_name} nimmt {dot_damage} {effect['name']}-Schaden!")
        
        # Apply healing over time
        if 'heal_per_turn' in effect:
            heal = min(effect['heal_per_turn'] * stacks, max_health - target_health)
            if heal > 0:
                health_change += heal
                messages.append(f"{effect['emoji']} {target_name} heilt {heal} HP durch {effect['name']}!")
        
        # Decrement duration
        effect_data['duration'] -= 1
        if effect_data['duration'] <= 0:
            effects_to_remove.append(effect_key)
            messages.append(f"{effect['emoji']} {effect['name']} endet!")
    
    # Remove expired effects
    for key in effects_to_remove:
        target_effects.pop(key, None)
    
    return health_change, messages


def is_immobilized(target_effects: dict) -> Tuple[bool, str]:
    """
    Check if target is immobilized by status effects.
    
    Returns:
        (is_immobilized, reason_message) tuple
    """
    for effect_key, effect_data in target_effects.items():
        effect = STATUS_EFFECTS.get(effect_key)
        if effect and effect.get('immobilize', False):
            return True, f"{effect['emoji']} {effect['name']} verhindert Aktionen!"
    
    # Check for static/paralysis
    if 'static' in target_effects:
        effect = STATUS_EFFECTS['static']
        stacks = target_effects['static'].get('stacks', 1)
        paralyze_chance = effect.get('paralyze_chance', 0.3) * stacks
        if random.random() < paralyze_chance:
            return True, f"⚡ Statisch paralysiert!"
    
    return False, ""


def get_effective_stats(base_stats: dict, effects: dict) -> dict:
    """
    Calculate effective stats with status effect modifiers.
    
    Args:
        base_stats: Base stats dictionary
        effects: Active status effects
    
    Returns:
        Modified stats dictionary
    """
    stats = base_stats.copy()
    
    for effect_key, effect_data in effects.items():
        effect = STATUS_EFFECTS.get(effect_key)
        if not effect:
            continue
        
        stacks = effect_data.get('stacks', 1)
        
        # Attack modifiers
        if 'atk_bonus' in effect:
            bonus = effect['atk_bonus'] * stacks
            stats['strength'] = int(stats.get('strength', 10) * (1 + bonus))
        if 'atk_reduction' in effect:
            reduction = effect['atk_reduction'] * stacks
            stats['strength'] = max(1, int(stats.get('strength', 10) * (1 - reduction)))
        
        # Defense modifiers
        if 'def_bonus' in effect:
            bonus = effect['def_bonus'] * stacks
            stats['defense'] = int(stats.get('defense', 10) * (1 + bonus))
        if 'def_reduction' in effect:
            reduction = effect['def_reduction'] * stacks
            stats['defense'] = max(0, int(stats.get('defense', 10) * (1 - reduction)))
        
        # Speed modifiers
        if 'speed_bonus' in effect:
            stats['speed'] = stats.get('speed', 10) + int(effect['speed_bonus'] * stacks)
        if 'speed_reduction' in effect:
            stats['speed'] = max(1, stats.get('speed', 10) - int(effect['speed_reduction'] * stacks))
    
    return stats


async def process_combat_turn(db_helpers, user_id: int, monster: dict, action: str, skill_data: dict = None, combat_state: dict = None):
    """
    Process a single combat turn with strategic AI and status effects.
    
    Args:
        action: 'attack', 'run', 'skill', or 'defend'
        skill_data: Skill item data when action is 'skill'
        combat_state: Current combat state with status effects (optional)
    
    Returns:
        dict with combat results
    """
    try:
        player = await get_player_profile(db_helpers, user_id)
        if not player:
            return {'error': 'Profil konnte nicht geladen werden.'}
        
        # Get equipped weapon for damage boost
        equipped = await get_equipped_items(db_helpers, user_id)
        weapon_damage_bonus = 0
        if equipped and equipped.get('weapon_id'):
            weapon = await get_item_by_id(db_helpers, equipped['weapon_id'])
            if weapon:
                weapon_damage_bonus = weapon.get('damage', 0)
        
        # Get skill tree stat bonuses
        skill_tree_bonuses = await calculate_skill_tree_bonuses(db_helpers, user_id)
        
        # Initialize combat state if not provided
        if combat_state is None:
            combat_state = {
                'player_effects': {},
                'monster_effects': {},
                'turn_count': 0
            }
        
        combat_state['turn_count'] = combat_state.get('turn_count', 0) + 1
        
        result = {
            'player_action': action,
            'player_damage': 0,
            'monster_damage': 0,
            'player_health': player['health'],
            'monster_health': monster['health'],
            'combat_over': False,
            'player_won': False,
            'rewards': None,
            'messages': [],
            'combat_state': combat_state,  # Return updated combat state
            'monster_ability_used': None,
            'status_applied': [],
            'weapon_bonus': weapon_damage_bonus,  # Track weapon bonus for display
            'skill_tree_bonuses': skill_tree_bonuses  # Track skill tree bonuses
        }
        
        # Calculate effective strength including weapon bonus AND skill tree bonuses
        effective_strength = player['strength'] + weapon_damage_bonus + skill_tree_bonuses.get('strength', 0)
        
        # Get effective stats with status modifiers (including weapon bonus and skill tree bonuses)
        player_stats = get_effective_stats({
            'strength': effective_strength,
            'defense': player['defense'] + skill_tree_bonuses.get('defense', 0),
            'speed': player['speed'] + skill_tree_bonuses.get('speed', 0),
            'dexterity': player.get('dexterity', DEFAULT_DEXTERITY) + skill_tree_bonuses.get('dexterity', 0)
        }, combat_state.get('player_effects', {}))
        
        monster_stats = get_effective_stats({
            'strength': monster['strength'],
            'defense': monster['defense'],
            'speed': monster['speed']
        }, combat_state.get('monster_effects', {}))
        
        # Determine turn order based on speed
        player_goes_first = player_stats['speed'] >= monster_stats['speed']
        
        # Process status effects at turn start for both combatants
        player_effect_change, player_effect_msgs = process_status_effects(
            combat_state.get('player_effects', {}),
            player['health'],
            player['max_health'],
            "Du"
        )
        monster_effect_change, monster_effect_msgs = process_status_effects(
            combat_state.get('monster_effects', {}),
            monster['health'],
            monster.get('max_health', monster['health']),
            monster['name']
        )
        
        # Apply status effect damage/healing
        if player_effect_change != 0:
            player['health'] = max(0, min(player['max_health'], player['health'] + player_effect_change))
            result['player_health'] = player['health']
            result['messages'].extend(player_effect_msgs)
        
        if monster_effect_change != 0:
            monster['health'] = max(0, monster['health'] + monster_effect_change)
            result['monster_health'] = monster['health']
            result['messages'].extend(monster_effect_msgs)
        
        # Check if someone died from status effects
        if player['health'] <= 0:
            result['combat_over'] = True
            result['player_won'] = False
            result['messages'].append("💀 **Du wurdest durch Statuseffekte besiegt!**")
            # Restore half health
            conn = db_helpers.db_pool.get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE rpg_players SET health = FLOOR(max_health / 2) WHERE user_id = %s", (user_id,))
            conn.commit()
            cursor.close()
            conn.close()
            return result
        
        if monster['health'] <= 0:
            result['combat_over'] = True
            result['player_won'] = True
            result['messages'].append(f"🎉 **{monster['name']} durch Statuseffekte besiegt!**")
            # Award rewards
            xp_result = await gain_xp(db_helpers, user_id, monster['xp_reward'])
            conn = db_helpers.db_pool.get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE rpg_players SET gold = gold + %s WHERE user_id = %s", (monster['gold_reward'], user_id))
            conn.commit()
            cursor.close()
            conn.close()
            result['rewards'] = {
                'xp': monster['xp_reward'],
                'gold': monster['gold_reward'],
                'leveled_up': xp_result['leveled_up'] if xp_result else False,
                'new_level': xp_result['new_level'] if xp_result and xp_result['leveled_up'] else None
            }
            return result
        
        # Check if player is immobilized
        player_immobilized, immob_msg = is_immobilized(combat_state.get('player_effects', {}))
        if player_immobilized and action != 'run':
            result['messages'].append(f"⚠️ {immob_msg}")
            action = 'skip'  # Force skip turn
        
        # Define player action function
        def do_player_action():
            nonlocal action
            if action == 'skip':
                result['messages'].append("⏭️ Du kannst dich nicht bewegen!")
                return
            
            if action == 'attack':
                dmg_result = calculate_damage(
                    player_stats['strength'],
                    monster_stats['defense'],
                    player_stats.get('dexterity', DEFAULT_DEXTERITY)
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
            
            elif action == 'defend':
                # Defensive stance - reduce incoming damage
                combat_state['player_defending'] = True
                result['messages'].append("🛡️ Du nimmst eine defensive Haltung ein!")
            
            elif action == 'skill':
                if not skill_data:
                    result['messages'].append("❌ Kein Skill ausgewählt!")
                else:
                    skill_name = skill_data.get('name', 'Unknown Skill')
                    skill_damage = skill_data.get('damage', 0)
                    
                    effects_json = skill_data.get('effects')
                    effects = {}
                    if effects_json:
                        try:
                            if isinstance(effects_json, str):
                                effects = json.loads(effects_json)
                            elif isinstance(effects_json, dict):
                                effects = effects_json
                        except Exception:
                            pass
                    
                    if skill_damage > 0:
                        dmg_result = calculate_damage(
                            skill_damage,
                            monster_stats['defense'],
                            player_stats.get('dexterity', DEFAULT_DEXTERITY)
                        )
                        
                        if dmg_result['crit']:
                            result['player_damage'] = dmg_result['damage']
                            result['messages'].append(f"✨💥 **{skill_name}** - KRITISCHER TREFFER! {dmg_result['damage']} Schaden!")
                        else:
                            result['player_damage'] = dmg_result['damage']
                            result['messages'].append(f"✨ **{skill_name}** fügt {dmg_result['damage']} Schaden zu!")
                        
                        monster['health'] -= result['player_damage']
                    
                    # Apply healing
                    if effects.get('heal'):
                        heal_amount = int(effects['heal'])
                        new_health = min(player['max_health'], player['health'] + heal_amount)
                        actual_heal = new_health - player['health']
                        if actual_heal > 0:
                            player['health'] = new_health
                            result['player_health'] = new_health
                            result['messages'].append(f"💚 **{skill_name}** heilt dich um {actual_heal} HP!")
                    
                    # Apply status effects from skill
                    status_effects_to_apply = ['burn', 'freeze', 'poison', 'static', 'darkness', 'slow', 'weakness', 'curse']
                    for effect_key in status_effects_to_apply:
                        if effects.get(effect_key):
                            # Check if effect triggers (based on the effect value as probability)
                            trigger_chance = float(effects[effect_key]) if isinstance(effects[effect_key], (int, float)) else 0.5
                            if random.random() < trigger_chance:
                                success, msg = apply_status_effect(combat_state.setdefault('monster_effects', {}), effect_key)
                                if success and msg:
                                    result['messages'].append(f"→ {msg}")
                                    result['status_applied'].append(effect_key)
            
            elif action == 'run':
                run_chance = 0.50 + (player_stats.get('dexterity', DEFAULT_DEXTERITY) / 200.0)
                run_chance = min(0.90, run_chance)
                
                if random.random() < run_chance:
                    result['combat_over'] = True
                    result['messages'].append("🏃 Du bist erfolgreich geflohen!")
                else:
                    result['messages'].append("❌ Flucht gescheitert!")
        
        # Define monster action function
        def do_monster_action():
            if monster['health'] <= 0:
                return
            
            # Check if monster is immobilized
            monster_immobilized, monster_immob_msg = is_immobilized(combat_state.get('monster_effects', {}))
            if monster_immobilized:
                result['messages'].append(f"🎯 {monster['name']}: {monster_immob_msg}")
                return
            
            # Try to use an ability
            ability = try_monster_ability(monster, player, combat_state)
            
            if ability:
                result['monster_ability_used'] = ability
                ability_emoji = ability.get('emoji', '⚡')
                ability_name = ability.get('name', 'Spezialfähigkeit')
                
                result['messages'].append(f"\n🔥 **{monster['name']} benutzt {ability_emoji} {ability_name}!**")
                
                effect_type = ability.get('effect_type')
                
                if effect_type == 'status':
                    # Apply status effect to player
                    status_effect = ability.get('status_effect')
                    if status_effect:
                        success, msg = apply_status_effect(combat_state.setdefault('player_effects', {}), status_effect)
                        if success and msg:
                            result['messages'].append(f"→ {msg}")
                
                elif effect_type == 'self_buff':
                    # Apply buff to monster
                    status_effect = ability.get('status_effect')
                    if status_effect:
                        success, msg = apply_status_effect(combat_state.setdefault('monster_effects', {}), status_effect)
                        if success and msg:
                            result['messages'].append(f"→ {monster['name']}: {msg}")
                
                elif effect_type == 'damage_boost':
                    # Enhanced damage attack
                    multiplier = ability.get('damage_multiplier', 2.0)
                    boosted_strength = int(monster_stats['strength'] * multiplier)
                    
                    dmg_result = calculate_damage(
                        boosted_strength,
                        player_stats['defense'],
                        monster_stats['speed'],
                        is_ai=True,
                        player_health_pct=player['health'] / player['max_health']
                    )
                    
                    if not dmg_result['dodged']:
                        damage = dmg_result['damage']
                        result['monster_damage'] += damage
                        crit_text = " 💀**KRITISCH!**" if dmg_result['crit'] else ""
                        result['messages'].append(f"→ {ability_emoji} Fügt {damage} verstärkten Schaden zu!{crit_text}")
                    else:
                        result['messages'].append("→ Du weichst dem verstärkten Angriff aus!")
                    return  # Ability replaces normal attack
                
                elif effect_type == 'lifesteal':
                    # Damage + heal
                    lifesteal_pct = ability.get('lifesteal_percent', 0.5)
                    
                    dmg_result = calculate_damage(
                        monster_stats['strength'],
                        player_stats['defense'],
                        monster_stats['speed'],
                        is_ai=True,
                        player_health_pct=player['health'] / player['max_health']
                    )
                    
                    if not dmg_result['dodged']:
                        damage = dmg_result['damage']
                        result['monster_damage'] += damage
                        heal_amount = int(damage * lifesteal_pct)
                        monster['health'] = min(monster.get('max_health', monster['health']), monster['health'] + heal_amount)
                        result['messages'].append(f"→ {ability_emoji} Fügt {damage} Schaden zu und heilt {heal_amount} HP!")
                    return  # Ability replaces normal attack
                
                elif effect_type == 'multi_hit':
                    # Multiple attacks
                    hit_count = ability.get('hit_count', 2)
                    damage_per_hit = ability.get('damage_per_hit', 0.5)
                    
                    total_damage = 0
                    hits = 0
                    for _ in range(hit_count):
                        dmg_result = calculate_damage(
                            int(monster_stats['strength'] * damage_per_hit),
                            player_stats['defense'],
                            monster_stats['speed'],
                            is_ai=True,
                            player_health_pct=player['health'] / player['max_health']
                        )
                        if not dmg_result['dodged']:
                            total_damage += dmg_result['damage']
                            hits += 1
                    
                    if total_damage > 0:
                        result['monster_damage'] += total_damage
                        result['messages'].append(f"→ {ability_emoji} Trifft {hits}x für insgesamt {total_damage} Schaden!")
                    return  # Ability replaces normal attack
                
                elif effect_type == 'cleanse':
                    # Remove debuffs from monster
                    monster_effects = combat_state.get('monster_effects', {})
                    debuff_types = ['burn', 'poison', 'darkness', 'slow', 'weakness', 'curse', 'bleed']
                    removed = []
                    for debuff in debuff_types:
                        if debuff in monster_effects:
                            del monster_effects[debuff]
                            removed.append(STATUS_EFFECTS[debuff]['emoji'])
                    if removed:
                        result['messages'].append(f"→ Entfernt: {' '.join(removed)}")
                    return  # Don't also do normal attack
            
            # Normal attack (if no ability used or ability doesn't replace attack)
            if not ability or ability.get('effect_type') not in ['damage_boost', 'lifesteal', 'multi_hit', 'cleanse']:
                # Check if player is defending
                defense_multiplier = 0.5 if combat_state.get('player_defending') else 1.0
                
                dmg_result = calculate_damage(
                    monster_stats['strength'],
                    int(player_stats['defense'] / defense_multiplier) if defense_multiplier < 1 else player_stats['defense'],
                    monster_stats['speed'],
                    is_ai=True,
                    player_health_pct=player['health'] / player['max_health']
                )
                
                if dmg_result['dodged']:
                    result['messages'].append(f"✨ Du bist dem Angriff von {monster['name']} ausgewichen!")
                else:
                    damage = int(dmg_result['damage'] * defense_multiplier)
                    result['monster_damage'] += damage
                    if dmg_result['crit']:
                        result['messages'].append(f"💀 **KRITISCHER TREFFER!** {monster['name']} fügt dir {damage} Schaden zu!")
                    else:
                        result['messages'].append(f"🗡️ {monster['name']} fügt dir {damage} Schaden zu!")
                    
                    if combat_state.get('player_defending'):
                        result['messages'].append("🛡️ Deine Verteidigung reduziert den Schaden!")
            
            # Reset defending state
            combat_state['player_defending'] = False
        
        # Execute turns based on speed order
        if player_goes_first:
            result['messages'].append("**⚡ Du bist schneller!**\n")
            do_player_action()
            
            # Check if monster defeated after player action
            if monster['health'] <= 0:
                result['combat_over'] = True
                result['player_won'] = True
            elif not result['combat_over']:
                result['messages'].append("")  # Add spacing
                do_monster_action()
        else:
            result['messages'].append(f"**⚡ {monster['name']} ist schneller!**\n")
            do_monster_action()
            
            # Apply monster damage before player action
            if result['monster_damage'] > 0:
                player['health'] = max(0, player['health'] - result['monster_damage'])
                result['player_health'] = player['health']
                
                if player['health'] <= 0:
                    result['combat_over'] = True
                    result['player_won'] = False
                    result['messages'].append("💀 **Du wurdest besiegt!**")
            
            if not result['combat_over']:
                result['messages'].append("")  # Add spacing
                do_player_action()
        
        # Final health updates
        if not result['combat_over']:
            # Update player health in DB
            new_health = max(0, player['health'] - result['monster_damage']) if player_goes_first else player['health']
            result['player_health'] = new_health
            
            conn = db_helpers.db_pool.get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("UPDATE rpg_players SET health = %s WHERE user_id = %s", (new_health, user_id))
                conn.commit()
            finally:
                cursor.close()
                conn.close()
            
            if new_health <= 0:
                result['combat_over'] = True
                result['player_won'] = False
                result['messages'].append("💀 **Du wurdest besiegt!** Du wirst zum Dorf zurückgebracht.")
                
                conn = db_helpers.db_pool.get_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE rpg_players SET health = FLOOR(max_health / 2) WHERE user_id = %s", (user_id,))
                conn.commit()
                cursor.close()
                conn.close()
        
        # Check monster defeat and handle rewards
        if monster['health'] <= 0 and not result.get('player_won'):
            result['combat_over'] = True
            result['player_won'] = True
            
            xp_result = await gain_xp(db_helpers, user_id, monster['xp_reward'])
            
            conn = db_helpers.db_pool.get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE rpg_players SET gold = gold + %s WHERE user_id = %s", (monster['gold_reward'], user_id))
            conn.commit()
            cursor.close()
            conn.close()
            
            # Roll for loot drops
            player_profile = await get_player_profile(db_helpers, user_id)
            player_level = player_profile['level'] if player_profile else 1
            loot_drops = await roll_loot_drops(db_helpers, monster, player_level)
            loot_names = []
            
            if loot_drops:
                success, loot_names = await add_loot_to_inventory(db_helpers, user_id, loot_drops, monster['name'])
            
            result['rewards'] = {
                'xp': monster['xp_reward'],
                'gold': monster['gold_reward'],
                'leveled_up': xp_result['leveled_up'] if xp_result else False,
                'new_level': xp_result['new_level'] if xp_result and xp_result['leveled_up'] else None,
                'loot': loot_names
            }
            
            msg = f"\n🎉 **{monster['name']} besiegt!**\n"
            msg += f"💰 +{monster['gold_reward']} Gold\n"
            msg += f"⭐ +{monster['xp_reward']} XP"
            if loot_names:
                msg += f"\n📦 **Loot:** {', '.join(loot_names)}"
            if result['rewards']['leveled_up']:
                msg += f"\n\n🎊 **LEVEL UP!** Du bist jetzt Level {result['rewards']['new_level']}!"
            result['messages'].append(msg)
        
        result['monster_health'] = monster['health']
        return result
        
    except Exception as e:
        logger.error(f"Error processing combat turn: {e}", exc_info=True)
        return {'error': str(e)}


# Default Shop Items - Expanded (100+ items)
# BALANCED: Weapons add to strength, skills use direct damage
DEFAULT_SHOP_ITEMS = [
    # ===== COMMON WEAPONS (Level 1-3) - Add +4-7 to strength =====
    {'name': 'Rostiges Schwert', 'type': 'weapon', 'rarity': 'common', 'description': 'Ein altes, rostiges Schwert', 'damage': 5, 'damage_type': 'physical', 'price': 50, 'required_level': 1},
    {'name': 'Holzstab', 'type': 'weapon', 'rarity': 'common', 'description': 'Ein einfacher Holzstab', 'damage': 4, 'damage_type': 'physical', 'price': 40, 'required_level': 1},
    {'name': 'Kurzschwert', 'type': 'weapon', 'rarity': 'common', 'description': 'Ein kleines, aber scharfes Schwert', 'damage': 6, 'damage_type': 'physical', 'price': 60, 'required_level': 1},
    {'name': 'Steinaxt', 'type': 'weapon', 'rarity': 'common', 'description': 'Eine primitive Steinaxt', 'damage': 5, 'damage_type': 'physical', 'price': 45, 'required_level': 1},
    {'name': 'Wurfmesser', 'type': 'weapon', 'rarity': 'common', 'description': 'Kleine Wurfmesser', 'damage': 5, 'damage_type': 'physical', 'price': 55, 'required_level': 1},
    {'name': 'Holzkeule', 'type': 'weapon', 'rarity': 'common', 'description': 'Eine schwere Holzkeule', 'damage': 6, 'damage_type': 'physical', 'price': 48, 'required_level': 1},
    {'name': 'Dolch', 'type': 'weapon', 'rarity': 'common', 'description': 'Ein einfacher Dolch', 'damage': 4, 'damage_type': 'physical', 'price': 42, 'required_level': 1},
    {'name': 'Speer', 'type': 'weapon', 'rarity': 'common', 'description': 'Ein Holzspeer mit Eisenspitze', 'damage': 6, 'damage_type': 'physical', 'price': 52, 'required_level': 2},
    {'name': 'Kurzbogen', 'type': 'weapon', 'rarity': 'common', 'description': 'Ein kleiner Bogen', 'damage': 5, 'damage_type': 'physical', 'price': 58, 'required_level': 2},
    {'name': 'Streitkolben', 'type': 'weapon', 'rarity': 'common', 'description': 'Ein schwerer Kolben', 'damage': 7, 'damage_type': 'physical', 'price': 65, 'required_level': 3},
    
    # ===== UNCOMMON WEAPONS (Level 3-6) - Add +7-11 to strength =====
    {'name': 'Stahlschwert', 'type': 'weapon', 'rarity': 'uncommon', 'description': 'Ein gut geschmiedetes Stahlschwert', 'damage': 8, 'damage_type': 'physical', 'price': 200, 'required_level': 3},
    {'name': 'Kampfaxt', 'type': 'weapon', 'rarity': 'uncommon', 'description': 'Eine schwere Kampfaxt', 'damage': 10, 'damage_type': 'physical', 'price': 250, 'required_level': 4},
    {'name': 'Langbogen', 'type': 'weapon', 'rarity': 'uncommon', 'description': 'Ein präziser Langbogen', 'damage': 8, 'damage_type': 'physical', 'price': 180, 'required_level': 3},
    {'name': 'Kriegshammer', 'type': 'weapon', 'rarity': 'uncommon', 'description': 'Ein zweihändiger Hammer', 'damage': 11, 'damage_type': 'physical', 'price': 270, 'required_level': 5},
    {'name': 'Rapier', 'type': 'weapon', 'rarity': 'uncommon', 'description': 'Ein schnelles Rapier', 'damage': 8, 'damage_type': 'physical', 'price': 190, 'required_level': 4},
    {'name': 'Glefe', 'type': 'weapon', 'rarity': 'uncommon', 'description': 'Eine lange Stangenwaffe', 'damage': 9, 'damage_type': 'physical', 'price': 210, 'required_level': 4},
    {'name': 'Zweihänder', 'type': 'weapon', 'rarity': 'uncommon', 'description': 'Ein riesiges Schwert', 'damage': 10, 'damage_type': 'physical', 'price': 230, 'required_level': 5},
    {'name': 'Armbrust', 'type': 'weapon', 'rarity': 'uncommon', 'description': 'Eine kraftvolle Armbrust', 'damage': 9, 'damage_type': 'physical', 'price': 195, 'required_level': 4},
    {'name': 'Katana', 'type': 'weapon', 'rarity': 'uncommon', 'description': 'Ein scharfes Katana', 'damage': 9, 'damage_type': 'physical', 'price': 220, 'required_level': 5},
    {'name': 'Streitaxt', 'type': 'weapon', 'rarity': 'uncommon', 'description': 'Eine zweischneidige Streitaxt', 'damage': 10, 'damage_type': 'physical', 'price': 240, 'required_level': 5},
    {'name': 'Säbel', 'type': 'weapon', 'rarity': 'uncommon', 'description': 'Ein gebogener Säbel', 'damage': 8, 'damage_type': 'physical', 'price': 200, 'required_level': 4},
    {'name': 'Morgenstern', 'type': 'weapon', 'rarity': 'uncommon', 'description': 'Eine Keule mit Spitzen', 'damage': 11, 'damage_type': 'physical', 'price': 260, 'required_level': 6},
    
    # ===== RARE WEAPONS (Level 6-10) - Add +12-18 to strength =====
    {'name': 'Flammenschwert', 'type': 'weapon', 'rarity': 'rare', 'description': 'Ein mit Flammen verzaubertes Schwert', 'damage': 14, 'damage_type': 'fire', 'price': 500, 'required_level': 6},
    {'name': 'Frosthammer', 'type': 'weapon', 'rarity': 'rare', 'description': 'Ein eiskalter Kriegshammer', 'damage': 16, 'damage_type': 'ice', 'price': 550, 'required_level': 7},
    {'name': 'Giftdolch', 'type': 'weapon', 'rarity': 'rare', 'description': 'Ein mit Gift beschichteter Dolch', 'damage': 12, 'damage_type': 'poison', 'price': 450, 'required_level': 5},
    {'name': 'Donnerspeer', 'type': 'weapon', 'rarity': 'rare', 'description': 'Ein Speer der Blitze schleudert', 'damage': 15, 'damage_type': 'lightning', 'price': 520, 'required_level': 7},
    {'name': 'Schattenklinge', 'type': 'weapon', 'rarity': 'rare', 'description': 'Eine Klinge aus purer Dunkelheit', 'damage': 13, 'damage_type': 'dark', 'price': 480, 'required_level': 6},
    {'name': 'Lichtbogen', 'type': 'weapon', 'rarity': 'rare', 'description': 'Ein Bogen aus heiligem Licht', 'damage': 13, 'damage_type': 'light', 'price': 470, 'required_level': 6},
    {'name': 'Windsäbel', 'type': 'weapon', 'rarity': 'rare', 'description': 'Ein Säbel schnell wie der Wind', 'damage': 14, 'damage_type': 'wind', 'price': 490, 'required_level': 7},
    {'name': 'Erdenhammer', 'type': 'weapon', 'rarity': 'rare', 'description': 'Ein Hammer der Erde bebt', 'damage': 16, 'damage_type': 'earth', 'price': 540, 'required_level': 8},
    {'name': 'Seelensense', 'type': 'weapon', 'rarity': 'rare', 'description': 'Eine Sense die Seelen erntet', 'damage': 15, 'damage_type': 'dark', 'price': 510, 'required_level': 7},
    {'name': 'Kristallstab', 'type': 'weapon', 'rarity': 'rare', 'description': 'Ein magischer Kristallstab', 'damage': 14, 'damage_type': 'magic', 'price': 475, 'required_level': 6},
    {'name': 'Runenschwert', 'type': 'weapon', 'rarity': 'rare', 'description': 'Ein mit Runen verziertes Schwert', 'damage': 16, 'damage_type': 'magic', 'price': 530, 'required_level': 8},
    {'name': 'Drachenklauen', 'type': 'weapon', 'rarity': 'rare', 'description': 'Klauen aus Drachenzähnen', 'damage': 15, 'damage_type': 'fire', 'price': 505, 'required_level': 8},
    
    # ===== EPIC WEAPONS (Level 10+) - Add +20-28 to strength =====
    {'name': 'Blitzklinge', 'type': 'weapon', 'rarity': 'epic', 'description': 'Eine mit Blitzen geladene Klinge', 'damage': 22, 'damage_type': 'lightning', 'price': 1000, 'required_level': 10},
    {'name': 'Heilige Lanze', 'type': 'weapon', 'rarity': 'epic', 'description': 'Eine von Licht durchdrungene Lanze', 'damage': 20, 'damage_type': 'light', 'price': 950, 'required_level': 9},
    {'name': 'Chaosschwert', 'type': 'weapon', 'rarity': 'epic', 'description': 'Ein Schwert aus reinem Chaos', 'damage': 24, 'damage_type': 'dark', 'price': 1100, 'required_level': 11},
    {'name': 'Phönixbogen', 'type': 'weapon', 'rarity': 'epic', 'description': 'Ein Bogen der wie ein Phönix brennt', 'damage': 21, 'damage_type': 'fire', 'price': 980, 'required_level': 10},
    {'name': 'Leviathan', 'type': 'weapon', 'rarity': 'epic', 'description': 'Ein Dreizack der Meerestiefe', 'damage': 23, 'damage_type': 'water', 'price': 1050, 'required_level': 11},
    # ===== LEGENDARY WEAPONS - Add +30-40 to strength =====
    {'name': 'Excalibur', 'type': 'weapon', 'rarity': 'legendary', 'description': 'Das legendäre Schwert', 'damage': 35, 'damage_type': 'light', 'price': 2000, 'required_level': 15},
    {'name': 'Mjölnir', 'type': 'weapon', 'rarity': 'legendary', 'description': 'Der Hammer des Donnergottes', 'damage': 38, 'damage_type': 'lightning', 'price': 2200, 'required_level': 16},
    {'name': 'Gramfang', 'type': 'weapon', 'rarity': 'legendary', 'description': 'Die Klinge des Drachentöters', 'damage': 36, 'damage_type': 'fire', 'price': 2100, 'required_level': 15},
    
    # ===== HEALING SKILLS =====
    {'name': 'Kleine Heilung', 'type': 'skill', 'rarity': 'common', 'description': 'Heilt 30 HP', 'price': 100, 'required_level': 2, 'effects': json.dumps({'heal': 30})},
    {'name': 'Mittlere Heilung', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Heilt 60 HP', 'price': 250, 'required_level': 5, 'effects': json.dumps({'heal': 60})},
    {'name': 'Große Heilung', 'type': 'skill', 'rarity': 'rare', 'description': 'Heilt 100 HP', 'price': 500, 'required_level': 8, 'effects': json.dumps({'heal': 100})},
    {'name': 'Regeneration', 'type': 'skill', 'rarity': 'rare', 'description': 'Heilt über 3 Runden', 'price': 450, 'required_level': 7, 'effects': json.dumps({'regen': 3})},
    {'name': 'Göttliche Heilung', 'type': 'skill', 'rarity': 'epic', 'description': 'Heilt 150 HP sofort', 'price': 800, 'required_level': 10, 'effects': json.dumps({'heal': 150})},
    {'name': 'Lebenselixier', 'type': 'skill', 'rarity': 'epic', 'description': 'Regeneriert 50 HP pro Runde für 3 Runden', 'price': 900, 'required_level': 12, 'effects': json.dumps({'regen': 3, 'heal_per_turn': 50})},
    
    # ===== FIRE ATTACK SKILLS - BALANCED =====
    # Skills now competitive with basic attacks (STR 10 + weapon 4-40 = 14-50 total)
    {'name': 'Feuerball', 'type': 'skill', 'rarity': 'common', 'description': 'Wirft einen Feuerball', 'damage': 22, 'damage_type': 'fire', 'price': 100, 'required_level': 2, 'effects': json.dumps({'burn': 0.3})},
    {'name': 'Feuersturm', 'type': 'skill', 'rarity': 'epic', 'description': 'Ein verheerender Feuersturm', 'damage': 75, 'damage_type': 'fire', 'price': 1000, 'required_level': 10, 'effects': json.dumps({'burn': 0.6})},
    {'name': 'Flammenwelle', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Welle aus Flammen', 'damage': 38, 'damage_type': 'fire', 'price': 250, 'required_level': 4, 'effects': json.dumps({'burn': 0.4})},
    {'name': 'Inferno', 'type': 'skill', 'rarity': 'rare', 'description': 'Entfesselt ein Inferno', 'damage': 58, 'damage_type': 'fire', 'price': 650, 'required_level': 9, 'effects': json.dumps({'burn': 0.5})},
    {'name': 'Meteorregen', 'type': 'skill', 'rarity': 'epic', 'description': 'Ruft brennende Meteore', 'damage': 82, 'damage_type': 'fire', 'price': 1100, 'required_level': 11, 'effects': json.dumps({'burn': 0.7})},
    
    # ===== ICE/FROST SKILLS - BALANCED =====
    {'name': 'Eissturm', 'type': 'skill', 'rarity': 'rare', 'description': 'Entfesselt einen Eissturm', 'damage': 55, 'damage_type': 'ice', 'price': 550, 'required_level': 8, 'effects': json.dumps({'freeze': 0.5})},
    {'name': 'Frostlanze', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Schießt eine Eislanze', 'damage': 35, 'damage_type': 'ice', 'price': 220, 'required_level': 4, 'effects': json.dumps({'freeze': 0.3})},
    {'name': 'Eiswand', 'type': 'skill', 'rarity': 'rare', 'description': 'Erschafft schützende Eiswand', 'price': 480, 'required_level': 7, 'effects': json.dumps({'shield': 3, 'defense_bonus': 20})},
    {'name': 'Frosthauch', 'type': 'skill', 'rarity': 'common', 'description': 'Kalter Hauch', 'damage': 20, 'damage_type': 'ice', 'price': 110, 'required_level': 3, 'effects': json.dumps({'freeze': 0.2})},
    {'name': 'Gletscherspalte', 'type': 'skill', 'rarity': 'epic', 'description': 'Spaltet die Erde mit Eis', 'damage': 70, 'damage_type': 'ice', 'price': 950, 'required_level': 10, 'effects': json.dumps({'freeze': 0.6})},
    
    # ===== LIGHTNING SKILLS - BALANCED =====
    {'name': 'Blitzstoß', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Schleudert einen Blitz', 'damage': 42, 'damage_type': 'lightning', 'price': 300, 'required_level': 5, 'effects': json.dumps({'static': 0.4})},
    {'name': 'Kettenlblitz', 'type': 'skill', 'rarity': 'rare', 'description': 'Blitz der springt', 'damage': 55, 'damage_type': 'lightning', 'price': 580, 'required_level': 8, 'effects': json.dumps({'static': 0.5})},
    {'name': 'Donnerschlag', 'type': 'skill', 'rarity': 'common', 'description': 'Elektrischer Schlag', 'damage': 25, 'damage_type': 'lightning', 'price': 130, 'required_level': 3, 'effects': json.dumps({'static': 0.3})},
    {'name': 'Gewittersturm', 'type': 'skill', 'rarity': 'epic', 'description': 'Beschwört Gewittersturm', 'damage': 72, 'damage_type': 'lightning', 'price': 1000, 'required_level': 11, 'effects': json.dumps({'static': 0.7})},
    
    # ===== DARK/SHADOW SKILLS - BALANCED =====
    {'name': 'Schattenpfeil', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Pfeil aus Schatten', 'damage': 40, 'damage_type': 'dark', 'price': 270, 'required_level': 5, 'effects': json.dumps({'darkness': 0.4})},
    {'name': 'Seelenraub', 'type': 'skill', 'rarity': 'rare', 'description': 'Stiehlt Lebensenergie', 'damage': 52, 'damage_type': 'dark', 'price': 600, 'required_level': 9, 'effects': json.dumps({'lifesteal': 0.5})},
    {'name': 'Dunkler Puls', 'type': 'skill', 'rarity': 'common', 'description': 'Welle dunkler Energie', 'damage': 28, 'damage_type': 'dark', 'price': 140, 'required_level': 3, 'effects': json.dumps({'darkness': 0.3})},
    {'name': 'Schattenumarmung', 'type': 'skill', 'rarity': 'epic', 'description': 'Verschlingt in Schatten', 'damage': 78, 'damage_type': 'dark', 'price': 1150, 'required_level': 12, 'effects': json.dumps({'darkness': 0.7, 'lifesteal': 0.3})},
    
    # ===== LIGHT/HOLY SKILLS - BALANCED =====
    {'name': 'Heiliges Licht', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Strahlendes Licht', 'damage': 38, 'damage_type': 'light', 'price': 260, 'required_level': 4, 'effects': json.dumps({'light': 0.3})},
    {'name': 'Göttlicher Zorn', 'type': 'skill', 'rarity': 'rare', 'description': 'Göttliche Strafe', 'damage': 58, 'damage_type': 'light', 'price': 620, 'required_level': 9, 'effects': json.dumps({'light': 0.5})},
    {'name': 'Lichtstrahl', 'type': 'skill', 'rarity': 'common', 'description': 'Strahl göttlichen Lichts', 'damage': 30, 'damage_type': 'light', 'price': 150, 'required_level': 3, 'effects': json.dumps({'light': 0.2})},
    {'name': 'Himmlisches Gericht', 'type': 'skill', 'rarity': 'epic', 'description': 'Endgültiges Urteil', 'damage': 85, 'damage_type': 'light', 'price': 1200, 'required_level': 13, 'effects': json.dumps({'light': 0.8})},
    
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
    {'name': 'Gift werfen', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Vergiftet den Gegner', 'damage': 20, 'damage_type': 'poison', 'price': 180, 'required_level': 3, 'effects': json.dumps({'poison': 0.5})},
    {'name': 'Blenden', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Verringert Genauigkeit des Gegners', 'price': 150, 'required_level': 3, 'effects': json.dumps({'darkness': 0.6})},
    {'name': 'Verlangsamen', 'type': 'skill', 'rarity': 'common', 'description': 'Reduziert Gegner-Geschwindigkeit', 'price': 120, 'required_level': 2, 'effects': json.dumps({'slow': 0.4})},
    {'name': 'Schwächen', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Senkt Angriff des Gegners', 'price': 200, 'required_level': 4, 'effects': json.dumps({'weaken': 3, 'attack_reduction': 0.3})},
    {'name': 'Fluch', 'type': 'skill', 'rarity': 'rare', 'description': 'Verflucht den Gegner', 'price': 450, 'required_level': 7, 'effects': json.dumps({'curse': 3, 'all_stats_reduction': 0.2})},
    {'name': 'Lähmung', 'type': 'skill', 'rarity': 'rare', 'description': 'Lähmt den Gegner', 'price': 500, 'required_level': 8, 'effects': json.dumps({'paralyze': 0.7, 'stun': 1})},
    
    # ===== UTILITY/SPECIAL SKILLS =====
    {'name': 'Teleportation', 'type': 'skill', 'rarity': 'rare', 'description': 'Teleportiert aus dem Kampf', 'price': 600, 'required_level': 9, 'effects': json.dumps({'escape': 1.0})},
    {'name': 'Zeitverzerrung', 'type': 'skill', 'rarity': 'epic', 'description': 'Verzerrt die Zeit', 'price': 1000, 'required_level': 12, 'effects': json.dumps({'time_stop': 1, 'extra_turn': True})},
    {'name': 'Manaentzug', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Entzieht Gegner Energie', 'damage': 32, 'damage_type': 'magic', 'price': 230, 'required_level': 4, 'effects': json.dumps({'mana_drain': 0.3})},
    {'name': 'Gegenangriff', 'type': 'skill', 'rarity': 'rare', 'description': 'Konter bei Angriffen', 'price': 480, 'required_level': 7, 'effects': json.dumps({'counter': 3, 'counter_damage': 0.8})},
    {'name': 'Doppelangriff', 'type': 'skill', 'rarity': 'epic', 'description': 'Greift zweimal an', 'price': 850, 'required_level': 10, 'effects': json.dumps({'double_attack': 2})},
]

# Merge extended items from rpg_items_data module
DEFAULT_SHOP_ITEMS.extend(EXTENDED_WEAPONS)
DEFAULT_SHOP_ITEMS.extend(EXTENDED_SKILLS)

logger.info(f"Loaded {len(DEFAULT_SHOP_ITEMS)} total shop items (base + extended)")


async def initialize_shop_items(db_helpers):
    """
    Initialize shop items in the database using generation logic.
    Imports and uses the generation functions from rpg_items_data module.
    Items are only generated once on first run, then loaded from database.
    """
    try:
        if not db_helpers.db_pool:
            logger.warning("Database pool not available for shop items initialization")
            return
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            logger.warning("Could not get database connection for shop items initialization")
            return
        
        cursor = conn.cursor()
        try:
            # Check if items exist (created_by IS NULL means default/generated items)
            cursor.execute("SELECT COUNT(*) FROM rpg_items WHERE created_by IS NULL")
            count = cursor.fetchone()[0]
            
            logger.info(f"Found {count} default RPG items in database")
            
            # Initialize if we have NO items or fewer than expected minimum (100)
            # This ensures initialization happens on first run or after database reset
            if count < 100:
                if count == 0:
                    logger.warning("No items found in database! Initializing for the first time...")
                else:
                    logger.warning(f"Only {count} items found (expected at least 100). Re-initializing...")
                
                # Import generation function (lazy import to avoid circular dependencies)
                from modules.rpg_items_data import get_all_items_for_seeding
                
                # Generate all items (handcrafted + programmatic)
                all_items = get_all_items_for_seeding()
                logger.info(f"Generated {len(all_items)} items for seeding")
                
                # Clear existing default items first if reinitializing
                if count > 0:
                    cursor.execute("DELETE FROM rpg_items WHERE created_by IS NULL")
                    logger.info(f"Cleared {count} existing default items for reinitializing")
                
                # Insert all items into database
                inserted = 0
                failed = 0
                for item in all_items:
                    try:
                        cursor.execute("""
                            INSERT INTO rpg_items 
                            (name, type, rarity, description, damage, damage_type, price, required_level, effects)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            item['name'], 
                            item['type'], 
                            item['rarity'], 
                            item['description'],
                            item.get('damage', 0), 
                            item.get('damage_type'), 
                            item['price'],
                            item['required_level'], 
                            item.get('effects')
                        ))
                        inserted += 1
                    except Exception as e:
                        failed += 1
                        if failed <= 5:  # Only log first 5 failures
                            logger.warning(f"Failed to insert item {item.get('name', 'Unknown')}: {e}")
                
                conn.commit()
                logger.info(f"Successfully initialized {inserted} shop items in database ({failed} failed)")
            else:
                logger.info(f"Shop items already initialized ({count} items)")
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error initializing shop items: {e}", exc_info=True)


async def get_daily_shop_items(db_helpers, player_level: int):
    """
    Get shop items for today's daily rotation.
    Shop changes every 24 hours with a random selection of items.
    
    Returns:
        List of items available in today's shop
    """
    try:
        if not db_helpers.db_pool:
            return []
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return []
        
        cursor = conn.cursor(dictionary=True)
        try:
            today = datetime.now(timezone.utc).date()
            
            # Check if we have today's shop
            cursor.execute("""
                SELECT item_ids FROM rpg_daily_shop WHERE shop_date = %s
            """, (today,))
            
            shop_row = cursor.fetchone()
            
            if shop_row:
                # Shop exists for today, load those items
                item_ids = json.loads(shop_row['item_ids'])
                
                if item_ids:
                    placeholders = ','.join(['%s'] * len(item_ids))
                    cursor.execute(f"""
                        SELECT * FROM rpg_items
                        WHERE id IN ({placeholders}) AND required_level <= %s
                        ORDER BY rarity, price ASC
                    """, (*item_ids, player_level))
                    
                    return cursor.fetchall()
                else:
                    return []
            
            else:
                # Generate new shop for today
                logger.info(f"Generating new daily shop for {today}")
                
                # Get all available items for the player level
                cursor.execute("""
                    SELECT id, rarity FROM rpg_items
                    WHERE created_by IS NULL AND required_level <= %s AND is_quest_item = FALSE
                """, (player_level,))
                
                all_items = cursor.fetchall()
                
                # If no items found for player level, try without level restriction
                if not all_items:
                    logger.warning(f"No items found for player level {player_level}. Trying all items...")
                    cursor.execute("""
                        SELECT id, rarity FROM rpg_items
                        WHERE created_by IS NULL AND is_quest_item = FALSE
                    """)
                    all_items = cursor.fetchall()
                
                # If still no items, try to initialize items
                if not all_items:
                    logger.error("No items in database! Attempting to initialize...")
                    new_conn = None
                    new_cursor = None
                    try:
                        cursor.close()
                        conn.close()
                        await initialize_shop_items(db_helpers)
                        
                        # Try again after initialization
                        new_conn = db_helpers.db_pool.get_connection()
                        if not new_conn:
                            logger.error("Failed to get database connection after initialization")
                            return []
                        
                        new_cursor = new_conn.cursor(dictionary=True)
                        new_cursor.execute("""
                            SELECT id, rarity FROM rpg_items
                            WHERE created_by IS NULL AND is_quest_item = FALSE
                        """)
                        all_items = new_cursor.fetchall()
                        
                        # Update conn and cursor references for cleanup in finally block
                        conn = new_conn
                        cursor = new_cursor
                        
                        if not all_items:
                            logger.error("Failed to initialize items! Database may have issues.")
                            return []
                    except Exception as init_error:
                        logger.error(f"Error during item initialization: {init_error}", exc_info=True)
                        # Clean up the new connection if it was created
                        if new_cursor:
                            try:
                                new_cursor.close()
                            except Exception as e:
                                logger.debug(f"Error closing cursor during cleanup: {e}")
                        if new_conn:
                            try:
                                new_conn.close()
                            except Exception as e:
                                logger.debug(f"Error closing connection during cleanup: {e}")
                        return []
                
                # Select items by rarity for balanced shop
                # 10 common, 6 uncommon, 4 rare, 2 epic, 1 legendary
                rarity_quotas = {
                    'common': 10,
                    'uncommon': 6,
                    'rare': 4,
                    'epic': 2,
                    'legendary': 1
                }
                
                selected_ids = []
                items_by_rarity = {}
                
                # Group items by rarity
                for item in all_items:
                    rarity = item['rarity']
                    if rarity not in items_by_rarity:
                        items_by_rarity[rarity] = []
                    items_by_rarity[rarity].append(item['id'])
                
                # Randomly select from each rarity
                for rarity, quota in rarity_quotas.items():
                    if rarity in items_by_rarity:
                        available = items_by_rarity[rarity]
                        count = min(quota, len(available))
                        selected_ids.extend(random.sample(available, count))
                
                # Save today's shop
                cursor.execute("""
                    INSERT INTO rpg_daily_shop (shop_date, item_ids)
                    VALUES (%s, %s)
                """, (today, json.dumps(selected_ids)))
                
                conn.commit()
                
                # Return the selected items
                if selected_ids:
                    placeholders = ','.join(['%s'] * len(selected_ids))
                    cursor.execute(f"""
                        SELECT * FROM rpg_items
                        WHERE id IN ({placeholders})
                        ORDER BY rarity, price ASC
                    """, tuple(selected_ids))
                    
                    return cursor.fetchall()
                else:
                    return []
                
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error getting daily shop items: {e}", exc_info=True)
        return []


async def get_shop_items(db_helpers, player_level: int):
    """
    Get shop items available for player level.
    Now uses daily rotation system - shop changes every 24 hours.
    """
    return await get_daily_shop_items(db_helpers, player_level)


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
            
            # Check if player already owns this item (prevent double-buy for unique items like weapons/skills)
            if item['type'] in ('weapon', 'skill'):
                cursor.execute("""
                    SELECT quantity FROM rpg_inventory 
                    WHERE user_id = %s AND item_id = %s
                """, (user_id, item_id))
                existing = cursor.fetchone()
                if existing and existing['quantity'] > 0:
                    return False, "Du besitzt dieses Item bereits!"
            
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
            # Check if player has item in inventory with full item details
            cursor.execute("""
                SELECT i.quantity, it.name, it.price, it.type, it.is_quest_item, it.is_sellable
                FROM rpg_inventory i
                JOIN rpg_items it ON i.item_id = it.id
                WHERE i.user_id = %s AND i.item_id = %s
            """, (user_id, item_id))
            
            inventory_item = cursor.fetchone()
            
            if not inventory_item:
                return False, "Item nicht im Inventar"
            
            # Check if item is a quest item (cannot be sold)
            if inventory_item.get('is_quest_item', False):
                return False, "Quest-Items können nicht verkauft werden!"
            
            # Check if item is explicitly marked as non-sellable
            if inventory_item.get('is_sellable') is False:
                return False, "Dieses Item kann nicht verkauft werden!"
            
            if inventory_item['quantity'] < quantity:
                return False, f"Nicht genug Items (hast {inventory_item['quantity']})"
            
            # Check if item is currently equipped (weapons and skills)
            if inventory_item['type'] in ('weapon', 'skill'):
                cursor.execute("SELECT weapon_id, skill1_id, skill2_id FROM rpg_equipped WHERE user_id = %s", (user_id,))
                equipped = cursor.fetchone()
                if equipped:
                    if inventory_item['type'] == 'weapon' and equipped['weapon_id'] == item_id:
                        # Unequip weapon before selling
                        cursor.execute("UPDATE rpg_equipped SET weapon_id = NULL WHERE user_id = %s", (user_id,))
                    elif inventory_item['type'] == 'skill':
                        if equipped['skill1_id'] == item_id:
                            cursor.execute("UPDATE rpg_equipped SET skill1_id = NULL WHERE user_id = %s", (user_id,))
                        if equipped['skill2_id'] == item_id:
                            cursor.execute("UPDATE rpg_equipped SET skill2_id = NULL WHERE user_id = %s", (user_id,))
            
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


async def equip_item(db_helpers, user_id: int, item_id: int, item_type: str, slot: int = None):
    """Equip an item.
    
    Args:
        db_helpers: Database helper module
        user_id: User ID
        item_id: Item ID to equip
        item_type: Type of item ('weapon' or 'skill')
        slot: For skills, specify slot 1 or 2. If None, auto-assigns to first empty slot.
    """
    try:
        if not db_helpers.db_pool:
            return False
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor(dictionary=True)
        try:
            # Check if player has item
            cursor.execute("""
                SELECT 1 FROM rpg_inventory WHERE user_id = %s AND item_id = %s
            """, (user_id, item_id))
            
            if not cursor.fetchone():
                return False
            
            # Ensure player has an equipped row
            cursor.execute("SELECT * FROM rpg_equipped WHERE user_id = %s", (user_id,))
            equipped_row = cursor.fetchone()
            
            if not equipped_row:
                # Create the row first
                cursor.execute("INSERT INTO rpg_equipped (user_id) VALUES (%s)", (user_id,))
                conn.commit()
                equipped_row = {'weapon_id': None, 'skill1_id': None, 'skill2_id': None}
            
            # Equip item based on type
            if item_type == 'weapon':
                cursor.execute("""
                    UPDATE rpg_equipped SET weapon_id = %s WHERE user_id = %s
                """, (item_id, user_id))
            elif item_type == 'skill':
                # Check current equipped skills
                skill1_id = equipped_row.get('skill1_id')
                skill2_id = equipped_row.get('skill2_id')
                
                # Don't equip the same skill twice (unless explicitly changing slots)
                if skill1_id == item_id and slot != 2:
                    # Already in slot 1, don't change
                    conn.commit()
                    return True
                if skill2_id == item_id and slot != 1:
                    # Already in slot 2, don't change
                    conn.commit()
                    return True
                
                # If a specific slot is requested, use that slot
                if slot == 1:
                    cursor.execute("""
                        UPDATE rpg_equipped SET skill1_id = %s WHERE user_id = %s
                    """, (item_id, user_id))
                elif slot == 2:
                    cursor.execute("""
                        UPDATE rpg_equipped SET skill2_id = %s WHERE user_id = %s
                    """, (item_id, user_id))
                else:
                    # Auto-assign: first empty slot, then replace slot 2
                    if skill1_id is None:
                        cursor.execute("""
                            UPDATE rpg_equipped SET skill1_id = %s WHERE user_id = %s
                        """, (item_id, user_id))
                    elif skill2_id is None:
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


async def recharge_skills(db_helpers, user_id: int, cost: int):
    """Recharge all skill uses to maximum at the temple."""
    try:
        if not db_helpers.db_pool:
            return False, "Datenbank nicht verfügbar"
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return False, "Datenbankverbindung fehlgeschlagen"
        
        cursor = conn.cursor(dictionary=True)
        try:
            # Check player gold
            cursor.execute("SELECT gold FROM rpg_players WHERE user_id = %s", (user_id,))
            player = cursor.fetchone()
            
            if not player:
                return False, "Spieler nicht gefunden"
            
            if player['gold'] < cost:
                return False, f"Nicht genug Gold! Du brauchst {cost} Gold."
            
            # Find all skills in inventory with max_uses and recharge them
            cursor.execute("""
                SELECT i.id, i.item_id, it.max_uses
                FROM rpg_inventory i
                JOIN rpg_items it ON i.item_id = it.id
                WHERE i.user_id = %s AND it.type = 'skill' AND it.max_uses IS NOT NULL
            """, (user_id,))
            
            skills_to_recharge = cursor.fetchall()
            
            if not skills_to_recharge:
                return False, "Keine Skills mit begrenzten Nutzungen gefunden."
            
            # Recharge all skills
            recharged_count = 0
            for skill in skills_to_recharge:
                cursor.execute("""
                    UPDATE rpg_inventory 
                    SET uses_remaining = %s
                    WHERE user_id = %s AND item_id = %s
                """, (skill['max_uses'], user_id, skill['item_id']))
                recharged_count += cursor.rowcount
            
            # Deduct gold
            cursor.execute("""
                UPDATE rpg_players SET gold = gold - %s WHERE user_id = %s
            """, (cost, user_id))
            
            conn.commit()
            return True, f"{recharged_count} Skills wurden vollständig aufgeladen!"
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error recharging skills: {e}", exc_info=True)
        return False, "Fehler beim Aufladen"


async def use_skill_charge(db_helpers, user_id: int, skill_id: int):
    """
    Use one charge of a skill. Returns whether the skill can still be used.
    
    Returns:
        (can_use, remaining_uses) - can_use is True if skill can be used (infinite or has charges)
    """
    try:
        if not db_helpers.db_pool:
            return True, None  # Assume skill can be used if no DB
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return True, None
        
        cursor = conn.cursor(dictionary=True)
        try:
            # Check if skill has max_uses
            cursor.execute("""
                SELECT it.max_uses, i.uses_remaining
                FROM rpg_inventory i
                JOIN rpg_items it ON i.item_id = it.id
                WHERE i.user_id = %s AND i.item_id = %s
            """, (user_id, skill_id))
            
            result = cursor.fetchone()
            
            if not result:
                return True, None  # Skill not found, assume usable
            
            max_uses = result.get('max_uses')
            
            # If no max_uses, skill has infinite uses
            if max_uses is None:
                return True, None
            
            uses_remaining = result.get('uses_remaining')
            
            # Initialize uses if not set
            if uses_remaining is None:
                uses_remaining = max_uses
            
            if uses_remaining <= 0:
                return False, 0  # No charges remaining
            
            # Decrement uses
            new_uses = uses_remaining - 1
            cursor.execute("""
                UPDATE rpg_inventory SET uses_remaining = %s
                WHERE user_id = %s AND item_id = %s
            """, (new_uses, user_id, skill_id))
            
            conn.commit()
            return True, new_uses
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error using skill charge: {e}", exc_info=True)
        return True, None  # Assume usable on error


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


async def calculate_skill_tree_bonuses(db_helpers, user_id: int) -> dict:
    """
    Calculate total stat bonuses from unlocked skill tree skills.
    
    Only 'stat' type skills provide permanent bonuses.
    'skill' type skills are active abilities used in combat.
    
    Args:
        db_helpers: Database helpers module
        user_id: The user ID to calculate bonuses for
    
    Returns:
        dict: Stat bonuses with keys 'strength', 'dexterity', 'defense', 'speed', 'max_health'
              All values are integers.
    """
    bonuses = {
        'strength': 0,
        'dexterity': 0,
        'defense': 0,
        'speed': 0,
        'max_health': 0
    }
    
    try:
        unlocked = await get_unlocked_skills(db_helpers, user_id)
        
        if not unlocked:
            return bonuses
        
        # Iterate through all unlocked skills and sum up stat bonuses
        for path_key, skill_keys in unlocked.items():
            if path_key not in SKILL_TREE:
                continue
            
            path_skills = SKILL_TREE[path_key]['skills']
            
            for skill_key in skill_keys:
                if skill_key not in path_skills:
                    continue
                
                skill = path_skills[skill_key]
                
                # Only process 'stat' type skills for permanent bonuses
                if skill.get('type') != 'stat':
                    continue
                
                effect = skill.get('effect', {})
                
                # Add each stat bonus (ensure integer conversion)
                for stat_name, bonus_value in effect.items():
                    if stat_name in bonuses:
                        # Ensure bonus_value is an integer
                        try:
                            bonuses[stat_name] += int(bonus_value)
                        except (ValueError, TypeError):
                            logger.warning(f"Invalid bonus value for {stat_name}: {bonus_value}")
        
        logger.debug(f"Calculated skill tree bonuses for user {user_id}: {bonuses}")
        return bonuses
        
    except Exception as e:
        logger.error(f"Error calculating skill tree bonuses: {e}", exc_info=True)
        return bonuses


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


