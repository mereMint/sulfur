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
LEVEL_REWARD_MULTIPLIER = 0.1  # Multiplier for scaling rewards based on player level
RESPEC_COST_PER_POINT = 50  # Gold cost per skill point when resetting stats

# Loot system constants
LUCK_BONUS_MAX = 0.05  # Maximum luck bonus to drop rates (5%)
LUCK_BONUS_PER_LEVEL = 0.001  # Luck bonus gained per player level

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
                    is_quest_item BOOLEAN DEFAULT FALSE,
                    is_sellable BOOLEAN DEFAULT TRUE,
                    is_usable BOOLEAN DEFAULT TRUE,
                    quest_id VARCHAR(100) NULL,
                    INDEX idx_type (type),
                    INDEX idx_rarity (rarity),
                    INDEX idx_quest (is_quest_item)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
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


# Default Monsters with abilities and LOOT TABLES
# Loot tables define what items can drop from each monster category
# Format: {item_name: drop_rate} where drop_rate is 0.0-1.0
def get_base_monsters_data():
    """
    Returns the base monster data for database seeding.
    Called during database initialization to populate rpg_monsters table.
    """
    return [
    # ===== OVERWORLD MONSTERS (Level 1-10) =====
    # Tier 1: Beginners (Level 1-2)
    {'name': 'Schleimling', 'world': 'overworld', 'level': 1, 'health': 30, 'strength': 3, 'defense': 2, 'speed': 5, 'xp_reward': 15, 'gold_reward': 10, 'abilities': ['poison_spit'], 'loot_table': {'Schleim': 0.8, 'Kleiner Gifttrank': 0.3}},
    {'name': 'Ratte', 'world': 'overworld', 'level': 1, 'health': 25, 'strength': 2, 'defense': 1, 'speed': 8, 'xp_reward': 12, 'gold_reward': 8, 'abilities': ['savage_bite'], 'loot_table': {'Rattenschwanz': 0.7, 'Krankheit (Quest)': 0.1}},
    {'name': 'Kleiner Goblin', 'world': 'overworld', 'level': 1, 'health': 28, 'strength': 4, 'defense': 2, 'speed': 6, 'xp_reward': 14, 'gold_reward': 12, 'abilities': ['critical_strike'], 'loot_table': {'Goblin-Ohr': 0.6, 'Rostige Münze': 0.4}},
    
    {'name': 'Goblin', 'world': 'overworld', 'level': 2, 'health': 45, 'strength': 5, 'defense': 3, 'speed': 6, 'xp_reward': 25, 'gold_reward': 20, 'abilities': ['critical_strike'], 'loot_table': {'Goblin-Ohr': 0.75, 'Kleiner Beutel': 0.3}},
    {'name': 'Riesenkäfer', 'world': 'overworld', 'level': 2, 'health': 40, 'strength': 4, 'defense': 5, 'speed': 4, 'xp_reward': 22, 'gold_reward': 18, 'abilities': ['armor_up'], 'loot_table': {'Käferpanzer': 0.7, 'Chitin': 0.5}},
    {'name': 'Wildschwein', 'world': 'overworld', 'level': 2, 'health': 50, 'strength': 6, 'defense': 3, 'speed': 7, 'xp_reward': 24, 'gold_reward': 22, 'abilities': ['savage_bite', 'battle_roar'], 'loot_table': {'Schweineleder': 0.8, 'Wildfleisch': 0.9, 'Stoßzahn': 0.4}},
    
    # Tier 2: Adventurers (Level 3-5)
    {'name': 'Wilder Wolf', 'world': 'overworld', 'level': 3, 'health': 60, 'strength': 7, 'defense': 4, 'speed': 10, 'xp_reward': 35, 'gold_reward': 25, 'abilities': ['savage_bite', 'crippling_strike'], 'loot_table': {'Wolfszahn': 0.75, 'Wolfsfell': 0.6, 'Wolfsherz (Quest)': 0.2}},
    {'name': 'Banditen-Schütze', 'world': 'overworld', 'level': 3, 'health': 55, 'strength': 8, 'defense': 3, 'speed': 9, 'xp_reward': 38, 'gold_reward': 30, 'abilities': ['hunters_focus', 'expose_weakness'], 'loot_table': {'Gestohlene Münzen': 0.9, 'Bogen': 0.3, 'Kopfgeld-Marke': 0.5}},
    {'name': 'Giftige Spinne', 'world': 'overworld', 'level': 3, 'health': 50, 'strength': 6, 'defense': 3, 'speed': 11, 'xp_reward': 32, 'gold_reward': 20, 'abilities': ['poison_spit', 'enfeeble'], 'loot_table': {'Spinnengift': 0.8, 'Spinnenseide': 0.7, 'Spinnenauge': 0.4}},
    
    {'name': 'Skelett-Krieger', 'world': 'overworld', 'level': 4, 'health': 70, 'strength': 9, 'defense': 6, 'speed': 7, 'xp_reward': 50, 'gold_reward': 35, 'abilities': ['armor_up', 'stunning_blow'], 'loot_table': {'Knochen': 0.9, 'Alter Schild': 0.4, 'Verfluchter Schädel': 0.2}},
    {'name': 'Zombie', 'world': 'overworld', 'level': 4, 'health': 80, 'strength': 10, 'defense': 5, 'speed': 4, 'xp_reward': 48, 'gold_reward': 30, 'abilities': ['life_drain', 'poison_spit'], 'loot_table': {'Verfaultes Fleisch': 0.95, 'Zombie-Gehirn': 0.3, 'Seuche (Quest)': 0.15}},
    {'name': 'Waldschamane', 'world': 'overworld', 'level': 4, 'health': 65, 'strength': 11, 'defense': 4, 'speed': 8, 'xp_reward': 52, 'gold_reward': 38, 'abilities': ['dark_curse', 'regeneration'], 'loot_table': {'Kräuter': 0.8, 'Schamanenstab': 0.25, 'Zauberperle': 0.4}},
    
    {'name': 'Ork-Schläger', 'world': 'overworld', 'level': 5, 'health': 90, 'strength': 12, 'defense': 8, 'speed': 6, 'xp_reward': 65, 'gold_reward': 50, 'abilities': ['battle_roar', 'critical_strike', 'stunning_blow'], 'loot_table': {'Ork-Zahn': 0.7, 'Schwere Rüstung': 0.3, 'Kriegstrophäe': 0.4}},
    {'name': 'Harpyie', 'world': 'overworld', 'level': 5, 'health': 75, 'strength': 10, 'defense': 5, 'speed': 14, 'xp_reward': 62, 'gold_reward': 45, 'abilities': ['shadow_step', 'terrifying_roar'], 'loot_table': {'Harpyienfeder': 0.85, 'Kralle': 0.6, 'Luftessenz': 0.3}},
    {'name': 'Steingolem', 'world': 'overworld', 'level': 5, 'health': 110, 'strength': 13, 'defense': 15, 'speed': 3, 'xp_reward': 68, 'gold_reward': 48, 'abilities': ['stone_skin', 'armor_up'], 'loot_table': {'Steinstück': 0.9, 'Magischer Kern': 0.25, 'Edelstein': 0.4}},
    
    # Tier 3: Veterans (Level 6-8)
    {'name': 'Dunkler Magier', 'world': 'overworld', 'level': 6, 'health': 80, 'strength': 15, 'defense': 5, 'speed': 9, 'xp_reward': 80, 'gold_reward': 60, 'abilities': ['shadow_cloak', 'life_drain', 'dark_curse'], 'loot_table': {'Dunkle Essenz': 0.7, 'Zauberbuch': 0.35, 'Mystischer Stab': 0.25}},
    {'name': 'Werwolf', 'world': 'overworld', 'level': 6, 'health': 95, 'strength': 14, 'defense': 7, 'speed': 13, 'xp_reward': 85, 'gold_reward': 55, 'abilities': ['berserk_fury', 'savage_bite', 'regeneration'], 'loot_table': {'Wolfszahn': 0.8, 'Mondfell': 0.5, 'Fluch-Token (Quest)': 0.2}},
    {'name': 'Sumpfschreiter', 'world': 'overworld', 'level': 6, 'health': 85, 'strength': 12, 'defense': 6, 'speed': 10, 'xp_reward': 78, 'gold_reward': 58, 'abilities': ['poison_spit', 'crippling_strike', 'enfeeble'], 'loot_table': {'Giftige Schlange': 0.7, 'Sumpfkraut': 0.8, 'Seltene Pflanze': 0.3}},
    
    {'name': 'Troll', 'world': 'overworld', 'level': 7, 'health': 120, 'strength': 16, 'defense': 12, 'speed': 4, 'xp_reward': 100, 'gold_reward': 75, 'abilities': ['regeneration', 'armor_up', 'last_stand'], 'loot_table': {'Trollblut': 0.65, 'Trollhaut': 0.5, 'Regenerationsstein': 0.3}},
    {'name': 'Banshee', 'world': 'overworld', 'level': 7, 'health': 90, 'strength': 17, 'defense': 6, 'speed': 12, 'xp_reward': 95, 'gold_reward': 70, 'abilities': ['terrifying_roar', 'mind_blast', 'dark_curse'], 'loot_table': {'Geistessenz': 0.7, 'Verlorene Seele': 0.4, 'Mystisches Tuch': 0.35}},
    {'name': 'Minotaurus', 'world': 'overworld', 'level': 7, 'health': 130, 'strength': 18, 'defense': 10, 'speed': 7, 'xp_reward': 105, 'gold_reward': 80, 'abilities': ['critical_strike', 'battle_roar', 'stunning_blow'], 'loot_table': {'Minotaurus-Horn': 0.6, 'Starkes Leder': 0.7, 'Labyrinth-Schlüssel': 0.25}},
    
    {'name': 'Geist', 'world': 'overworld', 'level': 8, 'health': 100, 'strength': 18, 'defense': 8, 'speed': 12, 'xp_reward': 120, 'gold_reward': 85, 'abilities': ['shadow_cloak', 'life_drain', 'shadow_step'], 'loot_table': {'Ekto plasma': 0.75, 'Geisterkette': 0.4, 'Verfluchtes Medaillon': 0.3}},
    {'name': 'Elementar (Erde)', 'world': 'overworld', 'level': 8, 'health': 140, 'strength': 16, 'defense': 18, 'speed': 5, 'xp_reward': 115, 'gold_reward': 90, 'abilities': ['stone_skin', 'armor_up', 'stunning_blow'], 'loot_table': {'Erdkristall': 0.7, 'Elementarstein': 0.5, 'Geokern': 0.35}},
    {'name': 'Riesenspinne', 'world': 'overworld', 'level': 8, 'health': 105, 'strength': 15, 'defense': 8, 'speed': 14, 'xp_reward': 118, 'gold_reward': 88, 'abilities': ['poison_spit', 'enfeeble', 'expose_weakness'], 'loot_table': {'Riesengift': 0.8, 'Robuste Seide': 0.7, 'Spinnenbein': 0.5}},
    
    # Tier 4: Elite (Level 9-10)
    {'name': 'Oger', 'world': 'overworld', 'level': 9, 'health': 150, 'strength': 20, 'defense': 15, 'speed': 5, 'xp_reward': 150, 'gold_reward': 100, 'abilities': ['battle_roar', 'critical_strike', 'regeneration', 'last_stand'], 'loot_table': {'Oger-Fleisch': 0.8, 'Großer Knochen': 0.7, 'Kraftamulett': 0.3}},
    {'name': 'Vampir', 'world': 'overworld', 'level': 9, 'health': 130, 'strength': 19, 'defense': 10, 'speed': 15, 'xp_reward': 145, 'gold_reward': 110, 'abilities': ['vampiric_aura', 'life_drain', 'shadow_cloak'], 'loot_table': {'Vampirzahn': 0.65, 'Blutphiole': 0.5, 'Mondring': 0.35}},
    {'name': 'Chimäre', 'world': 'overworld', 'level': 9, 'health': 145, 'strength': 21, 'defense': 12, 'speed': 11, 'xp_reward': 155, 'gold_reward': 105, 'abilities': ['fire_breath', 'poison_spit', 'critical_strike'], 'loot_table': {'Chimären-Schuppe': 0.7, 'Dreiköpfige Klaue': 0.4, 'Hybridessenz': 0.3}},
    
    {'name': 'Drache (Jung)', 'world': 'overworld', 'level': 10, 'health': 180, 'strength': 25, 'defense': 18, 'speed': 10, 'xp_reward': 200, 'gold_reward': 150, 'abilities': ['fire_breath', 'critical_strike', 'time_warp'], 'loot_table': {'Drachenschuppe': 0.8, 'Drachenzahn': 0.6, 'Kleine Drachenessenz': 0.4, 'Drachenherzstück (Quest)': 0.15}},
    {'name': 'Eisgolem', 'world': 'overworld', 'level': 10, 'health': 170, 'strength': 22, 'defense': 20, 'speed': 6, 'xp_reward': 190, 'gold_reward': 140, 'abilities': ['frost_nova', 'stone_skin', 'armor_up'], 'loot_table': {'Ewiges Eis': 0.75, 'Frostkristall': 0.6, 'Golem-Kern': 0.35}},
    {'name': 'Dunkler Ritter', 'world': 'overworld', 'level': 10, 'health': 165, 'strength': 24, 'defense': 22, 'speed': 9, 'xp_reward': 195, 'gold_reward': 145, 'abilities': ['dark_curse', 'armor_up', 'critical_strike', 'last_stand'], 'loot_table': {'Dunkle Rüstung': 0.5, 'Verfluchte Klinge': 0.35, 'Ritterorden-Abzeichen': 0.4}},
    
    # ===== UNDERWORLD MONSTERS (Level 11-25) =====
    # Tier 1: Underworld Initiates (Level 11-13)
    {'name': 'Imp', 'world': 'underworld', 'level': 11, 'health': 190, 'strength': 26, 'defense': 16, 'speed': 13, 'xp_reward': 250, 'gold_reward': 180, 'abilities': ['fire_breath', 'terrifying_roar'], 'loot_table': {'Imp-Horn': 0.7, 'Schwefelkristall': 0.6, 'Kleine Teufelsflamme': 0.4}},
    {'name': 'Höllenhündchen', 'world': 'underworld', 'level': 11, 'health': 185, 'strength': 27, 'defense': 15, 'speed': 16, 'xp_reward': 240, 'gold_reward': 175, 'abilities': ['fire_breath', 'savage_bite'], 'loot_table': {'Glühendes Fell': 0.75, 'Feuerzahn': 0.5, 'Ascheklaue': 0.4}},
    
    {'name': 'Dämon', 'world': 'underworld', 'level': 12, 'health': 220, 'strength': 30, 'defense': 20, 'speed': 12, 'xp_reward': 300, 'gold_reward': 200, 'abilities': ['fire_breath', 'life_drain', 'battle_roar'], 'loot_table': {'Dämonenhaut': 0.7, 'Höllenfeuer-Essenz': 0.5, 'Seelenedelstein': 0.3}},
    {'name': 'Knochenkönig', 'world': 'underworld', 'level': 12, 'health': 200, 'strength': 28, 'defense': 24, 'speed': 8, 'xp_reward': 290, 'gold_reward': 195, 'abilities': ['armor_up', 'dark_curse', 'regeneration'], 'loot_table': {'Uralter Knochen': 0.8, 'Knochenkrone': 0.35, 'Nekromantie-Siegel': 0.3}},
    {'name': 'Lavaelementar', 'world': 'underworld', 'level': 12, 'health': 210, 'strength': 29, 'defense': 18, 'speed': 10, 'xp_reward': 295, 'gold_reward': 190, 'abilities': ['fire_breath', 'berserk_fury'], 'loot_table': {'Lavagestein': 0.8, 'Feuerkern': 0.55, 'Obsidian': 0.45}},
    
    {'name': 'Schattendämon', 'world': 'underworld', 'level': 13, 'health': 215, 'strength': 31, 'defense': 19, 'speed': 14, 'xp_reward': 320, 'gold_reward': 210, 'abilities': ['shadow_cloak', 'dark_curse', 'vampiric_aura'], 'loot_table': {'Schattenherz': 0.65, 'Dunkle Materie': 0.5, 'Void-Kristall': 0.35}},
    {'name': 'Feuerdrache', 'world': 'underworld', 'level': 13, 'health': 240, 'strength': 33, 'defense': 22, 'speed': 11, 'xp_reward': 330, 'gold_reward': 220, 'abilities': ['fire_breath', 'critical_strike', 'time_warp'], 'loot_table': {'Feuerschuppe': 0.75, 'Drachenklaue': 0.6, 'Flammenherz': 0.4}},
    
    # Tier 2: Underworld Veterans (Level 14-17)
    {'name': 'Höllenhund', 'world': 'underworld', 'level': 14, 'health': 250, 'strength': 35, 'defense': 22, 'speed': 15, 'xp_reward': 400, 'gold_reward': 250, 'abilities': ['fire_breath', 'critical_strike', 'berserk_fury'], 'loot_table': {'Höllenpelz': 0.7, 'Glühende Klaue': 0.55, 'Inferno-Zahn': 0.4}},
    {'name': 'Dämonenfürst', 'world': 'underworld', 'level': 14, 'health': 260, 'strength': 36, 'defense': 24, 'speed': 13, 'xp_reward': 410, 'gold_reward': 260, 'abilities': ['fire_breath', 'dark_curse', 'battle_roar', 'last_stand'], 'loot_table': {'Fürstenkrone': 0.45, 'Dämonenflügel': 0.5, 'Höllische Essenz': 0.6}},
    
    {'name': 'Liche', 'world': 'underworld', 'level': 15, 'health': 230, 'strength': 38, 'defense': 20, 'speed': 10, 'xp_reward': 450, 'gold_reward': 280, 'abilities': ['dark_curse', 'death_mark', 'life_drain', 'regeneration'], 'loot_table': {'Phylakterium': 0.3, 'Unheilige Essenz': 0.65, 'Nekromantie-Buch': 0.4}},
    {'name': 'Blutgolem', 'world': 'underworld', 'level': 15, 'health': 280, 'strength': 37, 'defense': 26, 'speed': 7, 'xp_reward': 440, 'gold_reward': 270, 'abilities': ['regeneration', 'vampiric_aura', 'stone_skin'], 'loot_table': {'Geronnenes Blut': 0.8, 'Fleischklumpen': 0.7, 'Lebenskern': 0.35}},
    
    {'name': 'Schattenbestie', 'world': 'underworld', 'level': 16, 'health': 280, 'strength': 40, 'defense': 25, 'speed': 14, 'xp_reward': 500, 'gold_reward': 300, 'abilities': ['shadow_cloak', 'poison_spit', 'life_drain', 'shadow_step'], 'loot_table': {'Schattenfell': 0.7, 'Void-Kristall': 0.5, 'Schattenklaue': 0.45}},
    {'name': 'Höllentitan', 'world': 'underworld', 'level': 16, 'health': 320, 'strength': 42, 'defense': 30, 'speed': 6, 'xp_reward': 510, 'gold_reward': 310, 'abilities': ['critical_strike', 'stone_skin', 'battle_roar', 'last_stand'], 'loot_table': {'Titanenherz': 0.5, 'Titanstahl': 0.45, 'Urgestein': 0.6}},
    
    {'name': 'Succubus', 'world': 'underworld', 'level': 17, 'health': 270, 'strength': 41, 'defense': 23, 'speed': 16, 'xp_reward': 550, 'gold_reward': 330, 'abilities': ['life_drain', 'mind_blast', 'dark_curse', 'vampiric_aura'], 'loot_table': {'Verführerische Essenz': 0.6, 'Dämonisches Parfüm': 0.4, 'Seelenperle': 0.45}},
    {'name': 'Knochendrache', 'world': 'underworld', 'level': 17, 'health': 300, 'strength': 43, 'defense': 28, 'speed': 12, 'xp_reward': 560, 'gold_reward': 340, 'abilities': ['dark_curse', 'critical_strike', 'armor_up', 'terrifying_roar'], 'loot_table': {'Drachenknochen': 0.75, 'Untotes Herz': 0.5, 'Nekrotische Schuppe': 0.55}},
    
    # Tier 3: Underworld Elite (Level 18-21)
    {'name': 'Todesritter', 'world': 'underworld', 'level': 18, 'health': 320, 'strength': 45, 'defense': 30, 'speed': 11, 'xp_reward': 650, 'gold_reward': 400, 'abilities': ['frost_nova', 'armor_up', 'critical_strike', 'death_mark'], 'loot_table': {'Verfluchte Platte': 0.55, 'Frostschwert': 0.4, 'Todesritter-Siegel': 0.35}},
    {'name': 'Höllengolem', 'world': 'underworld', 'level': 18, 'health': 350, 'strength': 44, 'defense': 35, 'speed': 5, 'xp_reward': 640, 'gold_reward': 390, 'abilities': ['fire_breath', 'stone_skin', 'regeneration', 'last_stand'], 'loot_table': {'Magmakern': 0.6, 'Verstärkte Platte': 0.5, 'Unzerstörbarer Stein': 0.4}},
    
    {'name': 'Schattenlord', 'world': 'underworld', 'level': 19, 'health': 330, 'strength': 47, 'defense': 28, 'speed': 15, 'xp_reward': 700, 'gold_reward': 430, 'abilities': ['shadow_cloak', 'dark_curse', 'death_mark', 'vampiric_aura', 'shadow_step'], 'loot_table': {'Schattenthron-Fragment': 0.45, 'Herrschaftsring': 0.35, 'Dunkle Macht': 0.5}},
    {'name': 'Dämonenlord', 'world': 'underworld', 'level': 19, 'health': 340, 'strength': 48, 'defense': 32, 'speed': 13, 'xp_reward': 710, 'gold_reward': 440, 'abilities': ['fire_breath', 'battle_roar', 'critical_strike', 'berserk_fury', 'last_stand'], 'loot_table': {'Dämonenkrone': 0.4, 'Höllische Waffe': 0.45, 'Ewige Flamme': 0.5}},
    
    {'name': 'Drache (Erwachsen)', 'world': 'underworld', 'level': 20, 'health': 400, 'strength': 50, 'defense': 35, 'speed': 13, 'xp_reward': 800, 'gold_reward': 500, 'abilities': ['fire_breath', 'lightning_strike', 'critical_strike', 'regeneration', 'time_warp'], 'loot_table': {'Drachenschuppe': 0.8, 'Drachenklaue': 0.65, 'Drachenherz': 0.4, 'Drachenessenz': 0.3, 'Legendäre Schuppe (Quest)': 0.12}},
    {'name': 'Abgrundwächter', 'world': 'underworld', 'level': 20, 'health': 380, 'strength': 49, 'defense': 38, 'speed': 9, 'xp_reward': 790, 'gold_reward': 490, 'abilities': ['stone_skin', 'stunning_blow', 'armor_up', 'thorn_armor', 'last_stand'], 'loot_table': {'Wächterpanzer': 0.6, 'Abgrundstein': 0.55, 'Ewiger Wachposten': 0.35}},
    
    {'name': 'Erzlich', 'world': 'underworld', 'level': 21, 'health': 360, 'strength': 52, 'defense': 30, 'speed': 11, 'xp_reward': 850, 'gold_reward': 520, 'abilities': ['death_mark', 'dark_curse', 'life_drain', 'regeneration', 'arcane_barrier'], 'loot_table': {'Großes Phylakterium': 0.35, 'Meisterwerk der Nekromantie': 0.3, 'Seelensammler': 0.45}},
    {'name': 'Höllenfürst', 'world': 'underworld', 'level': 21, 'health': 370, 'strength': 53, 'defense': 33, 'speed': 14, 'xp_reward': 860, 'gold_reward': 530, 'abilities': ['fire_breath', 'berserk_fury', 'critical_strike', 'battle_roar', 'vampiric_aura'], 'loot_table': {'Fürstenzepter': 0.4, 'Höllenkrone': 0.35, 'Infernalische Essenz': 0.55}},
    
    # Tier 4: Underworld Champions (Level 22-25)
    {'name': 'Ur-Dämon', 'world': 'underworld', 'level': 22, 'health': 410, 'strength': 55, 'defense': 36, 'speed': 13, 'xp_reward': 950, 'gold_reward': 600, 'abilities': ['fire_breath', 'dark_curse', 'death_mark', 'critical_strike', 'berserk_fury', 'last_stand'], 'loot_table': {'Ur-Essenz': 0.5, 'Dämonisches Artefakt': 0.35, 'Herzdes Ur-Dämons (Quest)': 0.15}},
    {'name': 'Schattentitan', 'world': 'underworld', 'level': 22, 'health': 430, 'strength': 54, 'defense': 40, 'speed': 10, 'xp_reward': 940, 'gold_reward': 590, 'abilities': ['shadow_cloak', 'stone_skin', 'vampiric_aura', 'thorn_armor', 'last_stand'], 'loot_table': {'Titanischer Schatten': 0.45, 'Void-Titankern': 0.4, 'Schattenplatte': 0.5}},
    
    {'name': 'Blutdrache', 'world': 'underworld', 'level': 23, 'health': 450, 'strength': 58, 'defense': 38, 'speed': 14, 'xp_reward': 1050, 'gold_reward': 650, 'abilities': ['savage_bite', 'vampiric_aura', 'fire_breath', 'regeneration', 'critical_strike'], 'loot_table': {'Blutkristalschuppe': 0.65, 'Blutessenz': 0.6, 'Drachenblutstropfen (Quest)': 0.2}},
    {'name': 'Chaosritter', 'world': 'underworld', 'level': 23, 'health': 440, 'strength': 57, 'defense': 42, 'speed': 12, 'xp_reward': 1040, 'gold_reward': 640, 'abilities': ['dark_curse', 'critical_strike', 'armor_up', 'berserk_fury', 'last_stand'], 'loot_table': {'Chaosrüstung': 0.5, 'Verfluchtes Schwert': 0.45, 'Chaossiegel': 0.4}},
    
    {'name': 'Erzdämon', 'world': 'underworld', 'level': 24, 'health': 460, 'strength': 60, 'defense': 40, 'speed': 13, 'xp_reward': 1150, 'gold_reward': 700, 'abilities': ['fire_breath', 'death_mark', 'critical_strike', 'berserk_fury', 'vampiric_aura', 'last_stand'], 'loot_table': {'Erz-Essenz': 0.55, 'Dämonenkrone': 0.4, 'Höllenamulett': 0.45}},
    {'name': 'Todesengel', 'world': 'underworld', 'level': 24, 'health': 420, 'strength': 59, 'defense': 35, 'speed': 18, 'xp_reward': 1140, 'gold_reward': 690, 'abilities': ['death_mark', 'shadow_step', 'expose_weakness', 'dark_curse', 'hunters_focus'], 'loot_table': {'Engelschwinge (Dunkel)': 0.5, 'Todeshauch': 0.45, 'Seelensense': 0.4}},
    
    {'name': 'Drache (Alt)', 'world': 'underworld', 'level': 25, 'health': 500, 'strength': 65, 'defense': 45, 'speed': 15, 'xp_reward': 1300, 'gold_reward': 800, 'abilities': ['fire_breath', 'lightning_strike', 'frost_nova', 'critical_strike', 'regeneration', 'time_warp', 'last_stand'], 'loot_table': {'Uralte Drachenschuppe': 0.7, 'Drachenherz': 0.5, 'Große Drachenessenz': 0.4, 'Zeitkristall (Quest)': 0.15}},
    {'name': 'Höllenmonarch', 'world': 'underworld', 'level': 25, 'health': 480, 'strength': 63, 'defense': 43, 'speed': 14, 'xp_reward': 1280, 'gold_reward': 780, 'abilities': ['fire_breath', 'berserk_fury', 'battle_roar', 'critical_strike', 'arcane_barrier', 'last_stand'], 'loot_table': {'Monarchenkrone': 0.45, 'Zepter der Hölle': 0.4, 'Königssiegel': 0.35, 'Höllenstein (Quest)': 0.18}},
    
    # ===== SHADOWLANDS MONSTERS (Level 26-40) =====
    {'name': 'Schattenschleicher', 'world': 'shadowlands', 'level': 26, 'health': 520, 'strength': 66, 'defense': 42, 'speed': 20, 'xp_reward': 1400, 'gold_reward': 850, 'abilities': ['shadow_step', 'shadow_cloak', 'expose_weakness', 'savage_bite'], 'loot_table': {'Reiner Schatten': 0.7, 'Schattenklaue': 0.6, 'Finstere Essenz': 0.5}},
    {'name': 'Void-Bestie', 'world': 'shadowlands', 'level': 28, 'health': 560, 'strength': 70, 'defense': 45, 'speed': 18, 'xp_reward': 1600, 'gold_reward': 950, 'abilities': ['dark_curse', 'life_drain', 'vampiric_aura', 'berserk_fury'], 'loot_table': {'Void-Essenz': 0.75, 'Nichtsstein': 0.55, 'Abgrundherz': 0.45}},
    {'name': 'Schattentitan', 'world': 'shadowlands', 'level': 30, 'health': 600, 'strength': 75, 'defense': 55, 'speed': 12, 'xp_reward': 1850, 'gold_reward': 1100, 'abilities': ['stone_skin', 'shadow_cloak', 'critical_strike', 'thorn_armor', 'last_stand'], 'loot_table': {'Titanenschatten': 0.65, 'Schattentitanit': 0.5, 'Kolossales Herz': 0.4}},
    {'name': 'Schattendrache', 'world': 'shadowlands', 'level': 32, 'health': 650, 'strength': 80, 'defense': 58, 'speed': 16, 'xp_reward': 2100, 'gold_reward': 1250, 'abilities': ['shadow_cloak', 'fire_breath', 'critical_strike', 'time_warp', 'regeneration'], 'loot_table': {'Schattendrachenschuppe': 0.7, 'Schwarze Essenz': 0.6, 'Schattendrachenherz (Quest)': 0.2}},
    {'name': 'Void-Lord', 'world': 'shadowlands', 'level': 35, 'health': 700, 'strength': 88, 'defense': 62, 'speed': 17, 'xp_reward': 2500, 'gold_reward': 1500, 'abilities': ['death_mark', 'dark_curse', 'vampiric_aura', 'arcane_barrier', 'critical_strike', 'last_stand'], 'loot_table': {'Void-Lordkrone': 0.5, 'Nichtsessenz': 0.65, 'Leere-Artefakt (Quest)': 0.15}},
    {'name': 'Uralter Schatten', 'world': 'shadowlands', 'level': 38, 'health': 750, 'strength': 95, 'defense': 65, 'speed': 19, 'xp_reward': 2900, 'gold_reward': 1750, 'abilities': ['shadow_cloak', 'death_mark', 'shadow_step', 'dark_curse', 'vampiric_aura', 'petrifying_gaze'], 'loot_table': {'Urzeitschatten': 0.6, 'Ewige Finsternis': 0.5, 'Schattenherz (Quest)': 0.18}},
    {'name': 'Schattenkönig', 'world': 'shadowlands', 'level': 40, 'health': 850, 'strength': 105, 'defense': 75, 'speed': 20, 'xp_reward': 3500, 'gold_reward': 2100, 'abilities': ['shadow_cloak', 'death_mark', 'critical_strike', 'arcane_barrier', 'berserk_fury', 'time_warp', 'last_stand'], 'loot_table': {'Schattenkrone': 0.45, 'Königsschatten': 0.55, 'Schattenthron-Fragment (Quest)': 0.12}},
    
    # ===== FROZEN WASTES MONSTERS (Level 41-60) =====
    {'name': 'Frostwolf', 'world': 'frozen_wastes', 'level': 41, 'health': 900, 'strength': 108, 'defense': 70, 'speed': 25, 'xp_reward': 3800, 'gold_reward': 2250, 'abilities': ['frost_nova', 'savage_bite', 'crippling_strike'], 'loot_table': {'Frostwolfpelz': 0.75, 'Eisiger Zahn': 0.65, 'Winteressenz': 0.5}},
    {'name': 'Eisgolem', 'world': 'frozen_wastes', 'level': 43, 'health': 950, 'strength': 112, 'defense': 90, 'speed': 10, 'xp_reward': 4200, 'gold_reward': 2500, 'abilities': ['frost_nova', 'stone_skin', 'armor_up', 'thorn_armor'], 'loot_table': {'Ewiges Eis': 0.8, 'Frostkern': 0.6, 'Eisgolem-Herz': 0.45}},
    {'name': 'Frostdrache', 'world': 'frozen_wastes', 'level': 45, 'health': 1100, 'strength': 120, 'defense': 85, 'speed': 22, 'xp_reward': 4800, 'gold_reward': 2850, 'abilities': ['frost_nova', 'critical_strike', 'time_warp', 'regeneration', 'petrifying_gaze'], 'loot_table': {'Frostdrachenschuppe': 0.7, 'Eisherz': 0.55, 'Gefrorene Essenz (Quest)': 0.2}},
    {'name': 'Frosttitan', 'world': 'frozen_wastes', 'level': 48, 'health': 1200, 'strength': 130, 'defense': 100, 'speed': 15, 'xp_reward': 5500, 'gold_reward': 3300, 'abilities': ['frost_nova', 'stone_skin', 'critical_strike', 'stunning_blow', 'last_stand'], 'loot_table': {'Titaneneis': 0.65, 'Frosttitanit': 0.55, 'Winterkrone': 0.4}},
    {'name': 'Eiskönig', 'world': 'frozen_wastes', 'level': 50, 'health': 1300, 'strength': 140, 'defense': 95, 'speed': 18, 'xp_reward': 6200, 'gold_reward': 3750, 'abilities': ['frost_nova', 'death_mark', 'critical_strike', 'arcane_barrier', 'time_warp', 'last_stand'], 'loot_table': {'Eiskrone': 0.5, 'Winterszepter': 0.45, 'Gefrorener Thron (Quest)': 0.15}},
    {'name': 'Eiswyrm', 'world': 'frozen_wastes', 'level': 53, 'health': 1400, 'strength': 150, 'defense': 105, 'speed': 20, 'xp_reward': 7000, 'gold_reward': 4250, 'abilities': ['frost_nova', 'critical_strike', 'regeneration', 'vampiric_aura', 'petrifying_gaze'], 'loot_table': {'Eiswyrmschuppe': 0.7, 'Frostherz': 0.6, 'Ewiger Winter (Quest)': 0.18}},
    {'name': 'Frostphönix', 'world': 'frozen_wastes', 'level': 56, 'health': 1250, 'strength': 155, 'defense': 90, 'speed': 30, 'xp_reward': 7800, 'gold_reward': 4750, 'abilities': ['frost_nova', 'regeneration', 'time_warp', 'divine_blessing', 'shadow_step'], 'loot_table': {'Phönixfeder (Eis)': 0.65, 'Wiedergeburtsasche': 0.5, 'Frostessenz': 0.55}},
    {'name': 'Winterdrache (Uralter)', 'world': 'frozen_wastes', 'level': 60, 'health': 1600, 'strength': 170, 'defense': 120, 'speed': 25, 'xp_reward': 9500, 'gold_reward': 5800, 'abilities': ['frost_nova', 'critical_strike', 'time_warp', 'regeneration', 'arcane_barrier', 'petrifying_gaze', 'last_stand'], 'loot_table': {'Uralte Eisschuppe': 0.7, 'Drachenherz (Frost)': 0.5, 'Ewigkeitseis (Quest)': 0.12}},
    
    # ===== VOID MONSTERS (Level 61-100) =====
    {'name': 'Void-Wanderer', 'world': 'void', 'level': 61, 'health': 1700, 'strength': 175, 'defense': 115, 'speed': 28, 'xp_reward': 10500, 'gold_reward': 6400, 'abilities': ['death_mark', 'dark_curse', 'shadow_step', 'vampiric_aura'], 'loot_table': {'Void-Fragment': 0.75, 'Nichtsessenz': 0.7, 'Leerenkristall': 0.6}},
    {'name': 'Chaos-Bestie', 'world': 'void', 'level': 65, 'health': 1850, 'strength': 185, 'defense': 125, 'speed': 26, 'xp_reward': 12000, 'gold_reward': 7300, 'abilities': ['berserk_fury', 'critical_strike', 'dark_curse', 'death_mark', 'last_stand'], 'loot_table': {'Chaosherz': 0.7, 'Unordnung-Essenz': 0.65, 'Wahnsinnssplitter': 0.55}},
    {'name': 'Void-Titan', 'world': 'void', 'level': 70, 'health': 2200, 'strength': 200, 'defense': 150, 'speed': 20, 'xp_reward': 14500, 'gold_reward': 8900, 'abilities': ['stone_skin', 'critical_strike', 'arcane_barrier', 'thorn_armor', 'death_mark', 'last_stand'], 'loot_table': {'Void-Titankern': 0.65, 'Nichtsmetal': 0.6, 'Kolossale Leere': 0.5}},
    {'name': 'Ur-Drache', 'world': 'void', 'level': 75, 'health': 2500, 'strength': 220, 'defense': 160, 'speed': 30, 'xp_reward': 17500, 'gold_reward': 10800, 'abilities': ['fire_breath', 'frost_nova', 'lightning_strike', 'critical_strike', 'time_warp', 'regeneration', 'last_stand'], 'loot_table': {'Ur-Schuppe': 0.7, 'Ur-Drachenherz': 0.5, 'Zeitlose Essenz (Quest)': 0.15}},
    {'name': 'Void-Gott', 'world': 'void', 'level': 80, 'health': 2800, 'strength': 245, 'defense': 175, 'speed': 32, 'xp_reward': 21000, 'gold_reward': 13000, 'abilities': ['death_mark', 'dark_curse', 'arcane_barrier', 'petrifying_gaze', 'time_warp', 'vampiric_aura', 'last_stand'], 'loot_table': {'Göttliche Leere': 0.6, 'Gottessplitter': 0.45, 'Void-Krone (Quest)': 0.12}},
    {'name': 'Chaos-Drache', 'world': 'void', 'level': 85, 'health': 3000, 'strength': 265, 'defense': 185, 'speed': 33, 'xp_reward': 25000, 'gold_reward': 15500, 'abilities': ['fire_breath', 'dark_curse', 'berserk_fury', 'critical_strike', 'time_warp', 'regeneration', 'last_stand'], 'loot_table': {'Chaosschuppe': 0.65, 'Chaosdrachenherz': 0.5, 'Unendliche Kraft (Quest)': 0.15}},
    {'name': 'Ewigkeit', 'world': 'void', 'level': 90, 'health': 3500, 'strength': 290, 'defense': 200, 'speed': 35, 'xp_reward': 30000, 'gold_reward': 18500, 'abilities': ['time_warp', 'arcane_barrier', 'petrifying_gaze', 'death_mark', 'regeneration', 'divine_blessing', 'last_stand'], 'loot_table': {'Ewigkeitsfragment': 0.55, 'Zeitkristall': 0.5, 'Unendlichkeitsstein (Quest)': 0.1}},
    {'name': 'Urschöpfer', 'world': 'void', 'level': 95, 'health': 4000, 'strength': 320, 'defense': 220, 'speed': 38, 'xp_reward': 37000, 'gold_reward': 23000, 'abilities': ['fire_breath', 'frost_nova', 'lightning_strike', 'death_mark', 'arcane_barrier', 'time_warp', 'critical_strike', 'last_stand'], 'loot_table': {'Schöpfungsessenz': 0.5, 'Urmaterie': 0.45, 'Schöpferkrone (Quest)': 0.08}},
    {'name': 'Das Ende', 'world': 'void', 'level': 100, 'health': 5000, 'strength': 350, 'defense': 250, 'speed': 40, 'xp_reward': 50000, 'gold_reward': 30000, 'abilities': ['death_mark', 'dark_curse', 'petrifying_gaze', 'arcane_barrier', 'time_warp', 'berserk_fury', 'critical_strike', 'vampiric_aura', 'last_stand'], 'loot_table': {'Ende-Fragment': 0.4, 'Ultimative Leere': 0.35, 'Herzdes Endes (Quest)': 0.05, 'Göttliches Artefakt': 0.25}},
]


async def initialize_default_monsters(db_helpers):
    """
    Initialize monsters in the database.
    Monsters are only generated once on first run, then loaded from database.
    """
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
                
                # Get monster data from the function defined in this file
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
                        except:
                            pass
                    if new_conn:
                        try:
                            new_conn.close()
                        except:
                            pass
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


async def roll_loot_drops(db_helpers, monster: dict, player_level: int) -> list:
    """
    Roll for loot drops from a defeated monster based on its loot table.
    
    Loot table format: {item_name: drop_rate}
    - item_name: String, can contain "(Quest)" suffix for quest items
    - drop_rate: Float 0.0-1.0 (probability of drop)
    
    Example: {'Wolfszahn': 0.75, 'Wolfsherz (Quest)': 0.20}
    
    Args:
        db_helpers: Database helpers module
        monster: Monster dictionary with loot_table field
        player_level: Player's level (affects drop rates slightly)
    
    Returns:
        List of item dictionaries that dropped: [{'name': str, 'drop_rate': float, 'is_quest_item': bool}]
    """
    try:
        loot_table = monster.get('loot_table', {})
        if not loot_table:
            return []
        
        dropped_items = []
        
        # Small luck bonus based on player level (configured by LUCK_BONUS constants)
        luck_bonus = min(LUCK_BONUS_MAX, player_level * LUCK_BONUS_PER_LEVEL)
        
        for item_name, base_drop_rate in loot_table.items():
            # Apply luck bonus
            drop_rate = min(1.0, base_drop_rate + luck_bonus)
            
            # Roll for drop
            if random.random() < drop_rate:
                dropped_items.append({
                    'name': item_name,
                    'drop_rate': base_drop_rate,
                    'is_quest_item': '(Quest)' in item_name
                })
        
        return dropped_items
    except Exception as e:
        logger.error(f"Error rolling loot drops: {e}", exc_info=True)
        return []


async def add_loot_to_inventory(db_helpers, user_id: int, loot_items: list):
    """
    Add dropped loot items to player's inventory.
    Creates quest items as needed in the rpg_items table.
    
    Args:
        db_helpers: Database helpers module
        user_id: Player's user ID
        loot_items: List of loot item dictionaries
    
    Returns:
        Success boolean and message
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
                is_quest = loot.get('is_quest_item', False)
                
                # Check if item exists in rpg_items
                cursor.execute("""
                    SELECT id FROM rpg_items WHERE name = %s LIMIT 1
                """, (item_name,))
                
                item_row = cursor.fetchone()
                
                if not item_row:
                    # Create the item as a quest/sellable item
                    cursor.execute("""
                        INSERT INTO rpg_items 
                        (name, type, rarity, description, price, is_quest_item, is_usable, is_sellable)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        item_name,
                        'quest_item' if is_quest else 'material',
                        'common',
                        f'Dropped by {loot.get("monster_name", "monster")}',
                        QUEST_ITEM_BASE_PRICE if is_quest else random.randint(MATERIAL_ITEM_MIN_PRICE, MATERIAL_ITEM_MAX_PRICE),
                        is_quest,
                        False,  # Not usable in combat
                        True    # Can be sold (quest items usually can't be sold, but keeping flexible)
                    ))
                    item_id = cursor.lastrowid
                else:
                    item_id = item_row['id']
                
                # Add to inventory
                cursor.execute("""
                    INSERT INTO rpg_inventory (user_id, item_id, item_type, quantity)
                    VALUES (%s, %s, %s, 1)
                    ON DUPLICATE KEY UPDATE quantity = quantity + 1
                """, (user_id, item_id, 'quest_item' if is_quest else 'material'))
                
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


async def process_combat_turn(db_helpers, user_id: int, monster: dict, action: str, skill_data: dict = None):
    """
    Process a single combat turn.
    
    Args:
        action: 'attack', 'run', or 'skill'
        skill_data: Skill item data when action is 'skill'
    
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
        
        elif action == 'skill':
            # Handle skill usage
            if not skill_data:
                result['messages'].append("❌ Kein Skill ausgewählt!")
            else:
                skill_name = skill_data.get('name', 'Unknown Skill')
                skill_damage = skill_data.get('damage', 0)
                
                # Parse effects if they exist
                effects_json = skill_data.get('effects')
                effects = {}
                if effects_json:
                    try:
                        if isinstance(effects_json, str):
                            effects = json.loads(effects_json)
                        elif isinstance(effects_json, dict):
                            effects = effects_json
                    except:
                        pass
                
                # Apply skill damage
                if skill_damage > 0:
                    # Skills have higher base damage but can still crit
                    dmg_result = calculate_damage(
                        skill_damage,
                        monster['defense'],
                        player['dexterity']
                    )
                    
                    if dmg_result['crit']:
                        result['player_damage'] = dmg_result['damage']
                        result['messages'].append(f"✨💥 **{skill_name}** - KRITISCHER TREFFER! {dmg_result['damage']} Schaden!")
                    else:
                        result['player_damage'] = dmg_result['damage']
                        result['messages'].append(f"✨ **{skill_name}** fügt {dmg_result['damage']} Schaden zu!")
                    
                    monster['health'] -= result['player_damage']
                
                # Apply healing effects
                if effects.get('heal'):
                    heal_amount = int(effects['heal'])
                    new_health = min(player['max_health'], player['health'] + heal_amount)
                    actual_heal = new_health - player['health']
                    if actual_heal > 0:
                        result['player_health'] = new_health
                        result['messages'].append(f"💚 **{skill_name}** heilt dich um {actual_heal} HP!")
                        
                        # Update player health immediately
                        conn = db_helpers.db_pool.get_connection()
                        cursor = conn.cursor()
                        try:
                            cursor.execute("""
                                UPDATE rpg_players SET health = %s WHERE user_id = %s
                            """, (new_health, user_id))
                            conn.commit()
                        finally:
                            cursor.close()
                            conn.close()
                
                # Additional effect messages
                if effects.get('burn') and skill_damage > 0:
                    result['messages'].append("🔥 Der Gegner brennt!")
                if effects.get('freeze') and skill_damage > 0:
                    result['messages'].append("❄️ Der Gegner ist eingefroren!")
                if effects.get('poison') and skill_damage > 0:
                    result['messages'].append("🧪 Der Gegner ist vergiftet!")
                if effects.get('static') and skill_damage > 0:
                    result['messages'].append("⚡ Der Gegner ist gelähmt!")
        
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
            try:
                cursor.execute("""
                    UPDATE rpg_players SET health = %s WHERE user_id = %s
                """, (new_health, user_id))
                conn.commit()
            finally:
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
                            except:
                                pass
                        if new_conn:
                            try:
                                new_conn.close()
                            except:
                                pass
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


