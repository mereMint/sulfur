"""
RPG Combat Enhancements Module
Adds strategic elements, animations, and entertainment features to the RPG combat system.

Features:
- Combat commentary and dramatic messages
- Combo system and momentum tracking
- Enemy telegraph system (attack warnings)
- Close-call dramatic moments
- Special finishing move triggers
- Visual health bar animations
- Weakness/resistance indicators
"""

import random
from typing import Dict, List, Tuple, Optional

# =============================================================================
# CONSTANTS
# =============================================================================
MAX_RAGE = 100  # Maximum rage meter value
MAX_COMBO_DISPLAY = 15  # Maximum combo count for visual display

# =============================================================================
# COMBAT COMMENTARY SYSTEM
# Dramatic messages that add excitement to combat
# =============================================================================

ATTACK_VERBS = {
    'physical': ['schlägt zu', 'trifft', 'attackiert', 'greift an', 'stürmt', 'prügelt'],
    'fire': ['verbrennt', 'entflammt', 'versengt', 'lodert auf', 'entfesselt Flammen'],
    'ice': ['vereist', 'gefriert', 'kühlt', 'friert ein', 'entfesselt Frost'],
    'lightning': ['elektrisiert', 'blitzt', 'donnert', 'schockt', 'zerschmettert'],
    'dark': ['verfinstert', 'verschlingt', 'verdunkelt', 'korrumpiert', 'verdirbt'],
    'light': ['erleuchtet', 'strahlt', 'blendet', 'segnet', 'reinigt'],
    'poison': ['vergiftet', 'zersetzt', 'verseucht', 'infiziert', 'kontaminiert'],
    'magic': ['verzaubert', 'transformiert', 'beschwört', 'manifestiert', 'kanalisiert']
}

CRITICAL_MESSAGES = [
    "🔥 **VERHEEREND!** Ein perfekter Treffer!",
    "⚡ **VERNICHTEND!** Der Angriff trifft direkt ins Schwarze!",
    "💫 **MEISTERHAFT!** Ein Schlag von unglaublicher Präzision!",
    "🌟 **BRILLANT!** Die Attacke entfesselt ungeahnte Kraft!",
    "⭐ **EPISCH!** Ein legendärer Treffer!",
    "🎯 **PERFEKT!** Dieser Schlag wird in die Geschichte eingehen!",
    "💥 **BRUTAL!** Ein Angriff von roher Gewalt!",
    "🔱 **GÖTTLICH!** Die Macht der Götter fließt durch dich!"
]

NEAR_DEATH_MESSAGES = [
    "😰 *Du spürst das Gewicht deiner Verletzungen...*",
    "💔 *Dein Herz schlägt unregelmäßig... aber du kämpfst weiter!*",
    "🩸 *Blut tropft auf den Boden, doch dein Wille bleibt ungebrochen!*",
    "⚠️ *Gefahr! Deine Lebensenergie schwindet!*",
    "🔮 *Ein Flüstern ruft dich... widerstehe dem Tod!*"
]

VICTORY_CELEBRATIONS = [
    "🎊 **TRIUMPHIERT!**",
    "🏆 **GLORREICHER SIEG!**",
    "⚔️ **MEISTER DES KAMPFES!**",
    "👑 **CHAMPION!**",
    "🌟 **LEGENDÄR!**",
    "🎉 **BEZWINGER!**"
]

CLOSE_CALL_MESSAGES = [
    "😱 *Das war knapp! Du überlebst mit nur {hp} HP!*",
    "💨 *Im letzten Moment ausgewichen - noch {hp} HP übrig!*",
    "🛡️ *Gerade noch geblockt! {hp} HP verbleiben!*",
    "⚡ *Der Todeshauch streift dich - {hp} HP halten dich am Leben!*",
    "🔮 *Das Schicksal meint es gut mit dir - {hp} HP übrig!*"
]

COMBO_MESSAGES = {
    3: ("🔥 3er Kombo!", "Du baust Momentum auf!"),
    5: ("⚡ 5er Kombo!", "Deine Angriffe werden stärker!"),
    7: ("💫 7er Kombo!", "Unaufhaltsam!"),
    10: ("🌟 10er MEGA-KOMBO!", "Du bist in der Zone!"),
    15: ("👑 15er ULTRA-KOMBO!", "LEGENDÄRER KRIEGER!")
}

# Enemy telegraph messages - warns player of incoming powerful attacks
ENEMY_TELEGRAPH_MESSAGES = {
    'charging': [
        "⚠️ *{monster} sammelt Energie...*",
        "🔮 *{monster} beginnt zu glühen...*",
        "💨 *{monster} holt weit aus...*",
        "🎯 *{monster} fixiert dich mit wildem Blick...*"
    ],
    'special_incoming': [
        "⚡ **WARNUNG!** *{monster} bereitet eine Spezialattacke vor!*",
        "🔥 **VORSICHT!** *{monster} kanalisiert mächtige Energie!*",
        "💀 **GEFAHR!** *{monster} setzt zum vernichtenden Schlag an!*"
    ],
    'enraged': [
        "😤 *{monster} wird wütend! Stärke erhöht!*",
        "💢 *{monster} rastet aus! Angriffe werden stärker!*",
        "🔴 *{monster} ist im Berserker-Modus!*"
    ],
    'low_health': [
        "💀 *{monster} schwankt... der letzte Schlag?*",
        "🩸 *{monster} blutet stark... fast besiegt!*",
        "⚰️ *{monster} kämpft um sein Überleben!*"
    ]
}

# Special finishing move triggers
FINISHING_MOVE_TRIGGERS = [
    "💥 **FINISHER!** Du beendest den Kampf mit einem spektakulären Schlag!",
    "⚔️ **EXEKUTION!** Ein finaler, gnadenloser Hieb!",
    "🎯 **TODESSTOPP!** Du triffst die tödliche Schwachstelle!",
    "🌟 **ULTIMATUM!** Mit letzter Kraft besiegelst du den Sieg!",
    "👊 **K.O.!** Der finale Schlag hallt durch die Gegend!"
]

# =============================================================================
# MOMENTUM / RAGE SYSTEM
# Tracks consecutive actions and builds up power
# =============================================================================

def calculate_combo_bonus(combo_count: int) -> Tuple[float, str]:
    """
    Calculate damage bonus based on combo count.
    
    Returns:
        (damage_multiplier, message)
    """
    if combo_count >= 15:
        return (1.5, COMBO_MESSAGES[15])
    elif combo_count >= 10:
        return (1.35, COMBO_MESSAGES[10])
    elif combo_count >= 7:
        return (1.25, COMBO_MESSAGES[7])
    elif combo_count >= 5:
        return (1.15, COMBO_MESSAGES[5])
    elif combo_count >= 3:
        return (1.08, COMBO_MESSAGES[3])
    return (1.0, None)


def get_momentum_display(combo_count: int, rage_meter: int) -> str:
    """
    Create a visual display of the momentum/rage meters.
    
    Args:
        combo_count: Current combo counter
        rage_meter: Current rage level (0-MAX_RAGE)
    
    Returns:
        Formatted string showing the meters
    """
    lines = []
    
    # Combo display
    if combo_count > 0:
        combo_bar = "🔥" * min(combo_count, 15)
        if combo_count >= 10:
            lines.append(f"⚡ **KOMBO x{combo_count}** {combo_bar}")
        elif combo_count >= 5:
            lines.append(f"🔥 Kombo x{combo_count} {combo_bar}")
        elif combo_count >= 3:
            lines.append(f"✨ Kombo x{combo_count} {combo_bar}")
    
    # Rage meter display
    if rage_meter > 0:
        rage_filled = rage_meter // 10
        rage_empty = 10 - rage_filled
        rage_bar = "🟥" * rage_filled + "⬛" * rage_empty
        
        if rage_meter >= MAX_RAGE:
            lines.append(f"💢 **WUTMODUS BEREIT!** [{rage_bar}]")
        elif rage_meter >= 75:
            lines.append(f"😤 Wut: [{rage_bar}] {rage_meter}%")
        else:
            lines.append(f"😠 Wut: [{rage_bar}] {rage_meter}%")
    
    return "\n".join(lines)


# =============================================================================
# ENEMY TELEGRAPH SYSTEM
# Warns players about incoming powerful attacks
# =============================================================================

def should_telegraph_attack(monster: dict, monster_health_pct: float, turn_count: int) -> Optional[str]:
    """
    Determine if the enemy should telegraph their next attack.
    
    Returns:
        Telegraph message or None
    """
    monster_name = monster.get('name', 'Das Monster')
    
    # Check for low health telegraphs
    if monster_health_pct < 0.15:
        return random.choice(ENEMY_TELEGRAPH_MESSAGES['low_health']).format(monster=monster_name)
    
    # Random special attack telegraph (every few turns)
    if turn_count > 0 and turn_count % 3 == 2:  # Will telegraph before turn 3, 6, 9, etc.
        if random.random() < 0.4:  # 40% chance to telegraph
            return random.choice(ENEMY_TELEGRAPH_MESSAGES['special_incoming']).format(monster=monster_name)
    
    # Random charging telegraph
    if random.random() < 0.15:  # 15% chance each turn
        return random.choice(ENEMY_TELEGRAPH_MESSAGES['charging']).format(monster=monster_name)
    
    return None


def get_enemy_enrage_message(monster: dict, monster_health_pct: float) -> Optional[str]:
    """
    Get enrage message when monster health drops to certain threshold.
    """
    monster_name = monster.get('name', 'Das Monster')
    
    # Trigger enrage at 30% health
    if 0.25 < monster_health_pct <= 0.30:
        return random.choice(ENEMY_TELEGRAPH_MESSAGES['enraged']).format(monster=monster_name)
    
    return None


# =============================================================================
# VISUAL HEALTH BAR SYSTEM
# Enhanced health bars with color gradients and status indicators
# =============================================================================

def create_animated_health_bar(current_hp: int, max_hp: int, bar_length: int = 10, is_player: bool = True) -> str:
    """
    Create an enhanced health bar with color-coded segments and animations.
    
    Args:
        current_hp: Current health points
        max_hp: Maximum health points
        bar_length: Length of the health bar
        is_player: True for player, False for monster
    
    Returns:
        Formatted health bar string
    """
    if max_hp <= 0:
        max_hp = 1
    
    percentage = max(0, min(100, (current_hp / max_hp) * 100))
    filled = int(bar_length * (percentage / 100))
    empty = bar_length - filled
    
    # Choose colors based on health percentage
    if percentage > 70:
        bar_char = "🟩"
        status_emoji = "💚"
    elif percentage > 40:
        bar_char = "🟨"
        status_emoji = "💛"
    elif percentage > 20:
        bar_char = "🟧"
        status_emoji = "🧡"
    else:
        bar_char = "🟥"
        status_emoji = "❤️‍🔥" if is_player else "💔"
    
    health_bar = bar_char * filled + "⬛" * empty
    
    # Add pulsing effect for low health
    if percentage <= 20:
        health_bar = f"⚠️{health_bar}⚠️"
    
    return f"{status_emoji} [{health_bar}] {current_hp}/{max_hp}"


def create_damage_animation(damage: int, is_critical: bool = False, damage_type: str = "physical") -> str:
    """
    Create animated damage text.
    
    Returns:
        Formatted damage animation string
    """
    # Get damage type emoji
    type_emojis = {
        'physical': '⚔️',
        'fire': '🔥',
        'ice': '❄️',
        'lightning': '⚡',
        'dark': '🌑',
        'light': '✨',
        'poison': '🧪',
        'magic': '🔮',
        'wind': '💨',
        'earth': '🪨',
        'water': '💧'
    }
    emoji = type_emojis.get(damage_type, '💥')
    
    if is_critical:
        # Big dramatic critical hit
        return f"**{emoji}💥 -{damage} 💥{emoji}**"
    elif damage >= 50:
        return f"**{emoji} -{damage}!**"
    elif damage >= 30:
        return f"{emoji} -{damage}"
    else:
        return f"-{damage}"


# =============================================================================
# CLOSE CALL DETECTION
# Dramatic moments when health gets dangerously low
# =============================================================================

def check_close_call(previous_hp: int, current_hp: int, max_hp: int) -> Optional[str]:
    """
    Check if this was a close call (near death experience).
    
    Returns:
        Dramatic close call message or None
    """
    # Survived with low HP
    if current_hp > 0 and current_hp <= max_hp * 0.15 and previous_hp > max_hp * 0.15:
        return random.choice(CLOSE_CALL_MESSAGES).format(hp=current_hp)
    
    # Survived a big hit
    damage_taken = previous_hp - current_hp
    if damage_taken > max_hp * 0.4 and current_hp > 0:
        return f"😱 *{damage_taken} Schaden! Das war ein brutaler Treffer!*"
    
    return None


def get_near_death_message(current_hp: int, max_hp: int) -> Optional[str]:
    """
    Get a dramatic message when player is near death.
    """
    if current_hp <= max_hp * 0.2 and current_hp > 0:
        return random.choice(NEAR_DEATH_MESSAGES)
    return None


# =============================================================================
# FINISHING MOVE SYSTEM
# Triggers special animations for killing blows
# =============================================================================

def check_finishing_move(monster_hp_before: int, monster_hp_after: int, damage_dealt: int, is_critical: bool) -> Optional[str]:
    """
    Check if this attack qualifies as a finishing move.
    
    Returns:
        Finishing move message or None
    """
    # Monster was killed
    if monster_hp_before > 0 and monster_hp_after <= 0:
        # Epic finishing conditions
        if is_critical:
            return random.choice(FINISHING_MOVE_TRIGGERS)
        elif damage_dealt > 50:
            return random.choice(FINISHING_MOVE_TRIGGERS)
        elif random.random() < 0.3:  # 30% chance for regular kills
            return random.choice(FINISHING_MOVE_TRIGGERS)
    
    return None


def get_victory_celebration() -> str:
    """Get a random victory celebration message."""
    return random.choice(VICTORY_CELEBRATIONS)


# =============================================================================
# COMBAT COMMENTARY GENERATOR
# Creates dynamic, context-aware combat messages
# =============================================================================

def generate_attack_commentary(
    attacker_name: str,
    target_name: str,
    damage: int,
    damage_type: str,
    is_player: bool = True,
    is_critical: bool = False,
    combo_count: int = 0
) -> str:
    """
    Generate dynamic combat commentary for attacks.
    
    Args:
        attacker_name: Name of the attacker
        target_name: Name of the target
        damage: Damage dealt
        damage_type: Type of damage
        is_player: True if player is attacking
        is_critical: True if critical hit
        combo_count: Current combo count
    
    Returns:
        Formatted attack message
    """
    verbs = ATTACK_VERBS.get(damage_type, ATTACK_VERBS['physical'])
    verb = random.choice(verbs)
    
    # Build the message
    if is_critical:
        prefix = random.choice(CRITICAL_MESSAGES)
        if is_player:
            return f"{prefix}\n⚔️ Du {verb} {target_name} für **{damage}** Schaden!"
        else:
            return f"{prefix}\n🗡️ {attacker_name} {verb} dich für **{damage}** Schaden!"
    
    # Combo messages - safely handle None combo_msg
    combo_bonus, combo_msg = calculate_combo_bonus(combo_count) if combo_count else (1.0, None)
    combo_text = ""
    if combo_msg and isinstance(combo_msg, tuple) and len(combo_msg) >= 2:
        combo_text = f"\n{combo_msg[0]} *{combo_msg[1]}*"
    
    if is_player:
        return f"⚔️ Du {verb} {target_name} für **{damage}** Schaden!{combo_text}"
    else:
        return f"🗡️ {attacker_name} {verb} dich für **{damage}** Schaden!"


# =============================================================================
# WEAKNESS/RESISTANCE DISPLAY
# Shows enemy vulnerabilities and strengths
# =============================================================================

ELEMENT_WEAKNESSES = {
    'fire': {'weak_to': ['water', 'ice'], 'strong_against': ['ice', 'earth'], 'emoji': '🔥'},
    'ice': {'weak_to': ['fire', 'lightning'], 'strong_against': ['water', 'earth'], 'emoji': '❄️'},
    'lightning': {'weak_to': ['earth'], 'strong_against': ['water', 'ice'], 'emoji': '⚡'},
    'water': {'weak_to': ['lightning', 'poison'], 'strong_against': ['fire', 'earth'], 'emoji': '💧'},
    'earth': {'weak_to': ['water', 'ice'], 'strong_against': ['lightning', 'poison'], 'emoji': '🪨'},
    'dark': {'weak_to': ['light'], 'strong_against': ['light'], 'emoji': '🌑'},
    'light': {'weak_to': ['dark'], 'strong_against': ['dark'], 'emoji': '✨'},
    'poison': {'weak_to': ['light', 'earth'], 'strong_against': ['water', 'earth'], 'emoji': '🧪'},
    'wind': {'weak_to': ['earth'], 'strong_against': ['fire'], 'emoji': '💨'}
}


def get_weakness_indicator(monster_element: str, player_damage_type: str) -> Tuple[float, str]:
    """
    Check if player's attack exploits monster weakness.
    
    Returns:
        (damage_multiplier, message)
    """
    if not monster_element or monster_element == 'physical':
        return (1.0, "")
    
    element_data = ELEMENT_WEAKNESSES.get(monster_element)
    if not element_data:
        return (1.0, "")
    
    if player_damage_type in element_data.get('weak_to', []):
        return (1.3, f"✨ **SCHWÄCHE!** {player_damage_type.upper()} ist super effektiv!")
    elif player_damage_type in element_data.get('strong_against', []):
        return (0.7, f"🛡️ *Resistenz... {player_damage_type} ist weniger effektiv.*")
    
    return (1.0, "")


def get_monster_element_display(monster: dict) -> str:
    """
    Get the element indicator for a monster.
    """
    abilities = monster.get('abilities', [])
    
    # Detect element from abilities
    element = None
    if 'fire_breath' in abilities:
        element = 'fire'
    elif 'frost_nova' in abilities:
        element = 'ice'
    elif 'lightning_strike' in abilities:
        element = 'lightning'
    elif 'poison_spit' in abilities:
        element = 'poison'
    elif any(a in abilities for a in ['shadow_cloak', 'dark_curse', 'death_mark']):
        element = 'dark'
    elif 'divine_blessing' in abilities:
        element = 'light'
    
    if element and element in ELEMENT_WEAKNESSES:
        emoji = ELEMENT_WEAKNESSES[element]['emoji']
        return f"{emoji} Element: {element.capitalize()}"
    
    return ""


# =============================================================================
# COMBAT STATE ENHANCEMENT
# Additional state tracking for enhanced combat
# =============================================================================

def create_enhanced_combat_state() -> dict:
    """
    Create an enhanced combat state with additional tracking.
    """
    return {
        'player_effects': {},
        'monster_effects': {},
        'turn_count': 0,
        'player_defending': False,
        # New enhancements
        'combo_count': 0,
        'player_rage': 0,  # 0-100
        'monster_enraged': False,
        'last_player_damage': 0,
        'last_monster_damage': 0,
        'total_player_damage': 0,
        'total_monster_damage': 0,
        'critical_hits_player': 0,
        'critical_hits_monster': 0,
        'dodges_player': 0,
        'dodges_monster': 0,
        'abilities_used': [],
        'close_calls': 0
    }


def update_combat_stats(
    combat_state: dict,
    player_damage: int = 0,
    monster_damage: int = 0,
    player_crit: bool = False,
    monster_crit: bool = False,
    player_dodged: bool = False,
    monster_dodged: bool = False,
    ability_used: str = None
) -> dict:
    """
    Update combat statistics in the enhanced state.
    """
    # Update damage tracking
    if player_damage > 0:
        combat_state['combo_count'] += 1
        combat_state['last_player_damage'] = player_damage
        combat_state['total_player_damage'] += player_damage
        # Build rage on hit
        combat_state['player_rage'] = min(MAX_RAGE, combat_state['player_rage'] + 5)
    else:
        # Reset combo on miss
        if not player_dodged:
            combat_state['combo_count'] = 0
    
    if monster_damage > 0:
        combat_state['last_monster_damage'] = monster_damage
        combat_state['total_monster_damage'] += monster_damage
        # Build rage when taking damage
        combat_state['player_rage'] = min(MAX_RAGE, combat_state['player_rage'] + monster_damage // 5)
    
    # Track crits
    if player_crit:
        combat_state['critical_hits_player'] += 1
    if monster_crit:
        combat_state['critical_hits_monster'] += 1
    
    # Track dodges
    if player_dodged:
        combat_state['dodges_player'] += 1
    if monster_dodged:
        combat_state['dodges_monster'] += 1
    
    # Track abilities
    if ability_used:
        combat_state['abilities_used'].append(ability_used)
    
    return combat_state


# =============================================================================
# COMBAT SUMMARY GENERATOR
# Creates end-of-combat statistics
# =============================================================================

def generate_combat_summary(combat_state: dict, player_won: bool, monster_name: str) -> str:
    """
    Generate a detailed combat summary at the end of battle.
    """
    lines = []
    
    if player_won:
        lines.append(f"\n{get_victory_celebration()}")
        lines.append(f"*{monster_name} wurde bezwungen!*")
    else:
        lines.append("\n💀 **NIEDERLAGE...**")
        lines.append(f"*{monster_name} war zu stark...*")
    
    lines.append("\n**━━━ Kampfstatistiken ━━━**")
    
    # Damage stats
    total_player_dmg = combat_state.get('total_player_damage', 0)
    total_monster_dmg = combat_state.get('total_monster_damage', 0)
    lines.append(f"⚔️ Schaden verursacht: **{total_player_dmg}**")
    lines.append(f"🩸 Schaden erhalten: **{total_monster_dmg}**")
    
    # Performance stats
    crits = combat_state.get('critical_hits_player', 0)
    if crits > 0:
        lines.append(f"💥 Kritische Treffer: **{crits}**")
    
    dodges = combat_state.get('dodges_player', 0)
    if dodges > 0:
        lines.append(f"✨ Ausgewichen: **{dodges}**")
    
    # Highest combo
    highest_combo = combat_state.get('combo_count', 0)
    if highest_combo >= 5:
        lines.append(f"🔥 Höchste Kombo: **{highest_combo}x**")
    
    # Close calls
    close_calls = combat_state.get('close_calls', 0)
    if close_calls > 0:
        lines.append(f"😱 Knappe Momente: **{close_calls}**")
    
    # Turn count
    turns = combat_state.get('turn_count', 0)
    lines.append(f"⏱️ Runden: **{turns}**")
    
    return "\n".join(lines)


# =============================================================================
# LOOT CELEBRATION
# Special animations for rare loot drops
# =============================================================================

LOOT_CELEBRATIONS = {
    'common': ["📦 Loot erhalten!"],
    'uncommon': ["📦✨ Guter Loot!"],
    'rare': ["📦🌟 Seltener Loot!", "🎁 Ein seltener Fund!"],
    'epic': ["📦⭐ **EPISCHER LOOT!**", "🏆 **JACKPOT!** Episches Item!"],
    'legendary': [
        "📦👑 **LEGENDÄRER LOOT!!!**",
        "🌟🏆🌟 **UNFASSBAR! LEGENDÄRES ITEM GEFUNDEN!**",
        "🎊👑🎊 **DIE GÖTTER LÄCHELN DIR ZU! LEGENDÄR!**"
    ]
}


def get_loot_celebration(rarity: str, item_name: str) -> str:
    """
    Get a celebration message for loot drops based on rarity.
    """
    celebrations = LOOT_CELEBRATIONS.get(rarity.lower(), LOOT_CELEBRATIONS['common'])
    return f"{random.choice(celebrations)}\n**{item_name}** erhalten!"


# =============================================================================
# RAGE MODE ACTIVATION
# Special state when rage meter is full
# =============================================================================

def check_rage_activation(combat_state: dict) -> Tuple[bool, str]:
    """
    Check if rage mode can be activated.
    
    Returns:
        (can_activate, message)
    """
    rage = combat_state.get('player_rage', 0)
    
    if rage >= MAX_RAGE:
        return (True, "💢🔥 **WUTMODUS VERFÜGBAR!** Dein nächster Angriff verursacht 50% mehr Schaden!")
    
    return (False, "")


def consume_rage(combat_state: dict) -> Tuple[float, str]:
    """
    Consume rage for a powerful attack.
    
    Returns:
        (damage_multiplier, message)
    """
    if combat_state.get('player_rage', 0) >= MAX_RAGE:
        combat_state['player_rage'] = 0
        return (1.5, "💢💥 **WUTAUSBRUCH!** Du entfesselst deine angestaute Wut!")
    
    return (1.0, "")
