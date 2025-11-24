"""
RPG System - Extended Items Data
Contains massive expansion of weapons, spells, and skills for the RPG system.
This file is separated from rpg_system.py for better maintainability.

Auto-generates variations to reach 500+ weapons and 800+ skills.
"""

import json

# Base weapon templates for generation
WEAPON_TYPES = [
    'Schwert', 'Axt', 'Speer', 'Dolch', 'Hammer', 'Stab', 'Bogen', 'Sense',
    'Klinge', 'Lanze', 'Keule', 'Morgenstern', 'Rapier', 'Säbel', 'Katana'
]

WEAPON_PREFIXES = [
    'Verfluchte', 'Gesegnete', 'Uralte', 'Magische', 'Kristall-', 'Schatten-',
    'Flammen-', 'Frost-', 'Blitz-', 'Gift-', 'Heilige', 'Dunkle', 'Ewige',
    'Mystische', 'Arkane', 'Göttliche', 'Dämonische', 'Titanische', 'Legendäre',
    'Verzauberte', 'Runen-', 'Drachen-', 'Engel-', 'Meister-', 'Königs-'
]

DAMAGE_TYPES = ['physical', 'fire', 'ice', 'lightning', 'poison', 'dark', 'light', 'magic', 'wind', 'earth', 'water']

def generate_weapon_variations():
    """Generate hundreds of weapon variations programmatically."""
    weapons = []
    item_id = 1000  # Start from 1000 to avoid conflicts
    
    for level_tier in range(1, 26):  # Levels 1-25
        for prefix in WEAPON_PREFIXES[:level_tier]:
            for weapon_type in WEAPON_TYPES[:min(len(WEAPON_TYPES), 3 + level_tier // 2)]:
                rarity = 'common' if level_tier < 5 else 'uncommon' if level_tier < 10 else 'rare' if level_tier < 15 else 'epic' if level_tier < 20 else 'legendary'
                damage_type = DAMAGE_TYPES[level_tier % len(DAMAGE_TYPES)]
                
                base_damage = 10 + (level_tier * 3)
                price = 40 + (level_tier * 20) + (50 if rarity == 'uncommon' else 100 if rarity == 'rare' else 200 if rarity == 'epic' else 400)
                
                weapons.append({
                    'name': f'{prefix} {weapon_type}',
                    'type': 'weapon',
                    'rarity': rarity,
                    'description': f'Eine {prefix.lower()} {weapon_type.lower()}',
                    'damage': base_damage + (5 if rarity == 'uncommon' else 10 if rarity == 'rare' else 20 if rarity == 'epic' else 30),
                    'damage_type': damage_type,
                    'price': price,
                    'required_level': level_tier
                })
                
                item_id += 1
                
                # Limit to prevent too many
                if len(weapons) >= 400:
                    return weapons
    
    return weapons

def generate_skill_variations():
    """Generate hundreds of skill variations programmatically."""
    skills = []
    
    # Spell categories
    spell_bases = [
        ('Feuer', 'fire', 'Feuerzauber'),
        ('Eis', 'ice', 'Eiszauber'),
        ('Blitz', 'lightning', 'Blitzzauber'),
        ('Schatten', 'dark', 'Schattenzauber'),
        ('Licht', 'light', 'Lichtzauber'),
        ('Gift', 'poison', 'Giftzauber'),
        ('Wind', 'wind', 'Windzauber'),
        ('Erde', 'earth', 'Erdzauber'),
        ('Wasser', 'water', 'Wasserzauber'),
        ('Chaos', 'dark', 'Chaoszauber'),
        ('Heilig', 'light', 'Heiligzauber'),
        ('Natur', 'earth', 'Naturzauber'),
    ]
    
    spell_levels = [
        ('Schwach', 1, 15, 80, 0.2),
        ('Leicht', 2, 22, 140, 0.3),
        ('Mittel', 4, 35, 250, 0.4),
        ('Stark', 6, 48, 450, 0.5),
        ('Mächtig', 8, 62, 650, 0.6),
        ('Gewaltig', 10, 75, 900, 0.7),
        ('Ultimativ', 13, 95, 1400, 0.8),
        ('Göttlich', 16, 110, 1800, 0.85),
    ]
    
    # Generate damage spells
    for base_name, element, desc in spell_bases:
        for level_name, req_level, damage, price, effect_chance in spell_levels:
            rarity = 'common' if req_level < 3 else 'uncommon' if req_level < 6 else 'rare' if req_level < 10 else 'epic' if req_level < 15 else 'legendary'
            
            skills.append({
                'name': f'{level_name}er {base_name}',
                'type': 'skill',
                'rarity': rarity,
                'description': f'{desc} ({level_name})',
                'damage': damage,
                'damage_type': element,
                'price': price,
                'required_level': req_level,
                'effects': json.dumps({element: effect_chance})
            })
    
    # Generate buff/debuff skills
    buff_types = [
        ('Stärke', 'attack_boost', 3, 'damage_bonus'),
        ('Geschwindigkeit', 'speed_boost', 3, None),
        ('Verteidigung', 'defense_boost', 3, 'defense_bonus'),
        ('Präzision', 'accuracy_boost', 3, 'crit_bonus'),
        ('Ausdauer', 'stamina_boost', 3, 'max_health'),
        ('Agilität', 'agility_boost', 3, 'dodge_bonus'),
        ('Macht', 'power_boost', 3, 'damage_bonus'),
        ('Weisheit', 'wisdom_boost', 3, None),
    ]
    
    for buff_name, buff_key, duration, bonus_key in buff_types:
        for tier in range(1, 12):
            req_level = tier * 2
            price = 100 + (tier * 100)
            rarity = 'common' if tier < 3 else 'uncommon' if tier < 5 else 'rare' if tier < 8 else 'epic' if tier < 10 else 'legendary'
            
            effects = {buff_key: duration}
            if bonus_key:
                effects[bonus_key] = 0.1 * tier
            
            skills.append({
                'name': f'{buff_name} Stufe {tier}',
                'type': 'skill',
                'rarity': rarity,
                'description': f'Erhöht {buff_name}',
                'price': price,
                'required_level': req_level,
                'effects': json.dumps(effects)
            })
    
    # Generate healing skills
    for tier in range(1, 16):
        heal_amount = 20 + (tier * 15)
        req_level = tier
        price = 80 + (tier * 60)
        rarity = 'common' if tier < 4 else 'uncommon' if tier < 7 else 'rare' if tier < 10 else 'epic' if tier < 13 else 'legendary'
        
        skills.append({
            'name': f'Heilung Stufe {tier}',
            'type': 'skill',
            'rarity': rarity,
            'description': f'Heilt {heal_amount} HP',
            'price': price,
            'required_level': req_level,
            'effects': json.dumps({'heal': heal_amount})
        })
    
    # Generate debuff skills
    debuff_types = [
        ('Schwächung', 'weaken', 'attack_reduction'),
        ('Verlangsamung', 'slow', 'speed_reduction'),
        ('Verwirrung', 'confusion', 'accuracy_reduction'),
        ('Furcht', 'fear', 'defense_reduction'),
    ]
    
    for debuff_name, debuff_key, penalty_key in debuff_types:
        for tier in range(1, 10):
            req_level = tier * 2
            price = 120 + (tier * 90)
            rarity = 'common' if tier < 3 else 'uncommon' if tier < 5 else 'rare' if tier < 7 else 'epic'
            
            effects = {debuff_key: 2 + tier, penalty_key: 0.1 * tier}
            
            skills.append({
                'name': f'{debuff_name} Stufe {tier}',
                'type': 'skill',
                'rarity': rarity,
                'description': f'Schwächt Gegner ({debuff_name})',
                'price': price,
                'required_level': req_level,
                'effects': json.dumps(effects)
            })
    
    # Generate combo/special skills
    special_types = [
        ('Doppelschlag', 'double_attack', 2),
        ('Dreifachschlag', 'triple_attack', True),
        ('Kettenzauber', 'chain_cast', 3),
        ('Flächenangriff', 'aoe_attack', 2),
        ('Präzisionsschlag', 'precision_strike', 1.5),
        ('Kritischer Fokus', 'crit_focus', 0.3),
    ]
    
    for special_name, special_key, value in special_types:
        for tier in range(1, 8):
            req_level = 3 + (tier * 2)
            price = 200 + (tier * 150)
            rarity = 'uncommon' if tier < 3 else 'rare' if tier < 5 else 'epic'
            
            skills.append({
                'name': f'{special_name} {tier}',
                'type': 'skill',
                'rarity': rarity,
                'description': f'Spezialfähigkeit: {special_name}',
                'price': price,
                'required_level': req_level,
                'effects': json.dumps({special_key: value})
            })
    
    return skills

# ===== EXTENDED WEAPONS =====
# Adding 400+ more weapons to reach ~500 total

EXTENDED_WEAPONS = [
    # ===== COMMON TIER 2 WEAPONS (Level 2-4) =====
    {'name': 'Bauernforke', 'type': 'weapon', 'rarity': 'common', 'description': 'Eine einfache Bauernforke', 'damage': 14, 'damage_type': 'physical', 'price': 44, 'required_level': 2},
    {'name': 'Jagdmesser', 'type': 'weapon', 'rarity': 'common', 'description': 'Ein praktisches Jagdmesser', 'damage': 15, 'damage_type': 'physical', 'price': 47, 'required_level': 2},
    {'name': 'Eisenstab', 'type': 'weapon', 'rarity': 'common', 'description': 'Ein robuster Eisenstab', 'damage': 16, 'damage_type': 'physical', 'price': 50, 'required_level': 2},
    {'name': 'Kurzlanze', 'type': 'weapon', 'rarity': 'common', 'description': 'Eine kurze Lanze', 'damage': 17, 'damage_type': 'physical', 'price': 53, 'required_level': 3},
    {'name': 'Tomahawk', 'type': 'weapon', 'rarity': 'common', 'description': 'Eine werfbare Tomahawk-Axt', 'damage': 18, 'damage_type': 'physical', 'price': 56, 'required_level': 3},
    {'name': 'Sichel', 'type': 'weapon', 'rarity': 'common', 'description': 'Eine scharfe Sichel', 'damage': 16, 'damage_type': 'physical', 'price': 51, 'required_level': 3},
    {'name': 'Steinbrecher', 'type': 'weapon', 'rarity': 'common', 'description': 'Ein schwerer Steinbrecher-Hammer', 'damage': 20, 'damage_type': 'physical', 'price': 63, 'required_level': 4},
    {'name': 'Kurzsäbel', 'type': 'weapon', 'rarity': 'common', 'description': 'Ein gebogener Kurzsäbel', 'damage': 19, 'damage_type': 'physical', 'price': 60, 'required_level': 4},
    
    # ===== UNCOMMON TIER 2 WEAPONS (Level 5-8) =====
    {'name': 'Silberdolch', 'type': 'weapon', 'rarity': 'uncommon', 'description': 'Ein mit Silber beschichteter Dolch', 'damage': 24, 'damage_type': 'physical', 'price': 195, 'required_level': 5},
    {'name': 'Bronzeschwert', 'type': 'weapon', 'rarity': 'uncommon', 'description': 'Ein klassisches Bronzeschwert', 'damage': 25, 'damage_type': 'physical', 'price': 205, 'required_level': 5},
    {'name': 'Partisan', 'type': 'weapon', 'rarity': 'uncommon', 'description': 'Eine verzierte Stangenwaffe', 'damage': 27, 'damage_type': 'physical', 'price': 215, 'required_level': 6},
    {'name': 'Halberd', 'type': 'weapon', 'rarity': 'uncommon', 'description': 'Eine vielseitige Halberd', 'damage': 28, 'damage_type': 'physical', 'price': 225, 'required_level': 6},
    {'name': 'Großschwert', 'type': 'weapon', 'rarity': 'uncommon', 'description': 'Ein zweihändiges Großschwert', 'damage': 30, 'damage_type': 'physical', 'price': 245, 'required_level': 7},
    {'name': 'Kriegslanze', 'type': 'weapon', 'rarity': 'uncommon', 'description': 'Eine schwere Kriegslanze', 'damage': 29, 'damage_type': 'physical', 'price': 235, 'required_level': 7},
    {'name': 'Kampfstab', 'type': 'weapon', 'rarity': 'uncommon', 'description': 'Ein verstärkter Kampfstab', 'damage': 26, 'damage_type': 'physical', 'price': 210, 'required_level': 6},
    {'name': 'Reiterbogen', 'type': 'weapon', 'rarity': 'uncommon', 'description': 'Ein kompakter Reiterbogen', 'damage': 25, 'damage_type': 'physical', 'price': 200, 'required_level': 6},
    {'name': 'Zweihandaxt', 'type': 'weapon', 'rarity': 'uncommon', 'description': 'Eine massive Zweihandaxt', 'damage': 31, 'damage_type': 'physical', 'price': 255, 'required_level': 7},
    {'name': 'Falchion', 'type': 'weapon', 'rarity': 'uncommon', 'description': 'Ein gebogenes Einhandschwert', 'damage': 26, 'damage_type': 'physical', 'price': 208, 'required_level': 6},
    {'name': 'Bardiche', 'type': 'weapon', 'rarity': 'uncommon', 'description': 'Eine lange Axt mit Klinge', 'damage': 29, 'damage_type': 'physical', 'price': 238, 'required_level': 7},
    {'name': 'Estoc', 'type': 'weapon', 'rarity': 'uncommon', 'description': 'Ein schweres Stoßschwert', 'damage': 27, 'damage_type': 'physical', 'price': 218, 'required_level': 6},
    {'name': 'Kettenmorgenstern', 'type': 'weapon', 'rarity': 'uncommon', 'description': 'Ein Morgenstern an einer Kette', 'damage': 30, 'damage_type': 'physical', 'price': 248, 'required_level': 7},
    {'name': 'Kompositbogen', 'type': 'weapon', 'rarity': 'uncommon', 'description': 'Ein verstärkter Kompositbogen', 'damage': 26, 'damage_type': 'physical', 'price': 212, 'required_level': 6},
    
    # ===== RARE ELEMENTAL WEAPONS EXPANSION (Level 6-12) =====
    {'name': 'Eisschwert', 'type': 'weapon', 'rarity': 'rare', 'description': 'Eine Klinge aus purem Eis', 'damage': 41, 'damage_type': 'ice', 'price': 515, 'required_level': 8},
    {'name': 'Giftstachel', 'type': 'weapon', 'rarity': 'rare', 'description': 'Ein mit tödlichem Gift beschichteter Stachel', 'damage': 37, 'damage_type': 'poison', 'price': 485, 'required_level': 7},
    {'name': 'Donnerspieß', 'type': 'weapon', 'rarity': 'rare', 'description': 'Ein von Blitzen umgebener Spieß', 'damage': 43, 'damage_type': 'lightning', 'price': 525, 'required_level': 8},
    {'name': 'Erdenhammer (Groß)', 'type': 'weapon', 'rarity': 'rare', 'description': 'Ein gewaltiger Hammer der Erde', 'damage': 46, 'damage_type': 'earth', 'price': 550, 'required_level': 9},
    {'name': 'Heiliger Stab', 'type': 'weapon', 'rarity': 'rare', 'description': 'Ein Stab voller heiliger Energie', 'damage': 39, 'damage_type': 'light', 'price': 495, 'required_level': 7},
    {'name': 'Verderbensklinge', 'type': 'weapon', 'rarity': 'rare', 'description': 'Eine von Dunkelheit umhüllte Klinge', 'damage': 40, 'damage_type': 'dark', 'price': 505, 'required_level': 7},
    {'name': 'Wasserlanze', 'type': 'weapon', 'rarity': 'rare', 'description': 'Eine fließende Lanze aus Wasser', 'damage': 38, 'damage_type': 'water', 'price': 490, 'required_level': 7},
    {'name': 'Sturmklinge', 'type': 'weapon', 'rarity': 'rare', 'description': 'Ein Schwert getragen von Winden', 'damage': 41, 'damage_type': 'wind', 'price': 512, 'required_level': 8},
    {'name': 'Lavahammer', 'type': 'weapon', 'rarity': 'rare', 'description': 'Ein glühend heißer Lavahammer', 'damage': 45, 'damage_type': 'fire', 'price': 545, 'required_level': 9},
    {'name': 'Nachtklinge', 'type': 'weapon', 'rarity': 'rare', 'description': 'Eine Klinge schwarz wie die Nacht', 'damage': 42, 'damage_type': 'dark', 'price': 518, 'required_level': 8},
    {'name': 'Sternenbrecher', 'type': 'weapon', 'rarity': 'rare', 'description': 'Ein Hammer der Sterne', 'damage': 44, 'damage_type': 'light', 'price': 535, 'required_level': 9},
    {'name': 'Giftfänger', 'type': 'weapon', 'rarity': 'rare', 'description': 'Eine tropfende Giftklinge', 'damage': 39, 'damage_type': 'poison', 'price': 498, 'required_level': 7},
    {'name': 'Eislanze', 'type': 'weapon', 'rarity': 'rare', 'description': 'Eine gefrorene Lanze', 'damage': 43, 'damage_type': 'ice', 'price': 528, 'required_level': 8},
    {'name': 'Blitzhacke', 'type': 'weapon', 'rarity': 'rare', 'description': 'Eine von Elektrizität durchzogene Hacke', 'damage': 44, 'damage_type': 'lightning', 'price': 532, 'required_level': 9},
    
    # ===== EPIC WEAPONS EXPANSION (Level 10-15) =====
    {'name': 'Titanklinge', 'type': 'weapon', 'rarity': 'epic', 'description': 'Eine Klinge geschmiedet von Titanen', 'damage': 63, 'damage_type': 'physical', 'price': 1050, 'required_level': 11},
    {'name': 'Drachenschwert', 'type': 'weapon', 'rarity': 'epic', 'description': 'Ein Schwert aus Drachenknochen', 'damage': 61, 'damage_type': 'fire', 'price': 1020, 'required_level': 11},
    {'name': 'Void-Sense', 'type': 'weapon', 'rarity': 'epic', 'description': 'Eine Sense aus der Leere', 'damage': 64, 'damage_type': 'dark', 'price': 1080, 'required_level': 12},
    {'name': 'Himmelsbogen', 'type': 'weapon', 'rarity': 'epic', 'description': 'Ein Bogen der Götter', 'damage': 59, 'damage_type': 'light', 'price': 995, 'required_level': 10},
    {'name': 'Sturmhammer', 'type': 'weapon', 'rarity': 'epic', 'description': 'Ein Hammer voller Sturmkraft', 'damage': 66, 'damage_type': 'lightning', 'price': 1120, 'required_level': 12},
    {'name': 'Frostfänger', 'type': 'weapon', 'rarity': 'epic', 'description': 'Ein eiskaltes Schwert', 'damage': 60, 'damage_type': 'ice', 'price': 1010, 'required_level': 11},
    {'name': 'Seelenbrecher', 'type': 'weapon', 'rarity': 'epic', 'description': 'Eine Waffe die Seelen zerstört', 'damage': 62, 'damage_type': 'dark', 'price': 1040, 'required_level': 11},
    {'name': 'Flammenzorn', 'type': 'weapon', 'rarity': 'epic', 'description': 'Ein loderndes Großschwert', 'damage': 65, 'damage_type': 'fire', 'price': 1100, 'required_level': 12},
    {'name': 'Lichtbringer', 'type': 'weapon', 'rarity': 'epic', 'description': 'Eine strahlende Lanze', 'damage': 61, 'damage_type': 'light', 'price': 1025, 'required_level': 11},
    {'name': 'Chaoshammer', 'type': 'weapon', 'rarity': 'epic', 'description': 'Ein Hammer reinen Chaos', 'damage': 67, 'damage_type': 'dark', 'price': 1140, 'required_level': 13},
    
    # ===== LEGENDARY WEAPONS EXPANSION (Level 15-25) =====
    {'name': 'Durandal', 'type': 'weapon', 'rarity': 'legendary', 'description': 'Das unzerbrechliche Schwert', 'damage': 84, 'damage_type': 'light', 'price': 2150, 'required_level': 16},
    {'name': 'Gáe Bolg', 'type': 'weapon', 'rarity': 'legendary', 'description': 'Der verfluchte Speer', 'damage': 83, 'damage_type': 'dark', 'price': 2120, 'required_level': 16},
    {'name': 'Kusanagi', 'type': 'weapon', 'rarity': 'legendary', 'description': 'Das grasschneidende Schwert', 'damage': 81, 'damage_type': 'wind', 'price': 2080, 'required_level': 15},
    {'name': 'Gungnir', 'type': 'weapon', 'rarity': 'legendary', 'description': 'Odins Speer', 'damage': 86, 'damage_type': 'lightning', 'price': 2250, 'required_level': 17},
    {'name': 'Joyeuse', 'type': 'weapon', 'rarity': 'legendary', 'description': 'Das Schwert Karls des Großen', 'damage': 82, 'damage_type': 'light', 'price': 2105, 'required_level': 16},
    {'name': 'Tyrfing', 'type': 'weapon', 'rarity': 'legendary', 'description': 'Das Schicksalsschwert', 'damage': 85, 'damage_type': 'dark', 'price': 2220, 'required_level': 17},
    {'name': 'Rhongomyniad', 'type': 'weapon', 'rarity': 'legendary', 'description': 'Die Lanze am Ende der Welt', 'damage': 88, 'damage_type': 'light', 'price': 2350, 'required_level': 18},
    {'name': 'Naegling', 'type': 'weapon', 'rarity': 'legendary', 'description': 'Beowulfs Schwert', 'damage': 83, 'damage_type': 'physical', 'price': 2130, 'required_level': 16},
    {'name': 'Harpe', 'type': 'weapon', 'rarity': 'legendary', 'description': 'Perseus\' Sichelschwert', 'damage': 84, 'damage_type': 'light', 'price': 2180, 'required_level': 17},
    {'name': 'Caladbolg', 'type': 'weapon', 'rarity': 'legendary', 'description': 'Das Regenbogenschwert', 'damage': 87, 'damage_type': 'magic', 'price': 2300, 'required_level': 18},
    {'name': 'Ascalon', 'type': 'weapon', 'rarity': 'legendary', 'description': 'Die Drachentöter-Lanze', 'damage': 86, 'damage_type': 'fire', 'price': 2270, 'required_level': 17},
    {'name': 'Dainsleif', 'type': 'weapon', 'rarity': 'legendary', 'description': 'Das Schwert das niemals fehlt', 'damage': 85, 'damage_type': 'dark', 'price': 2240, 'required_level': 17},
    {'name': 'Shamshir-e Zomorrodnegar', 'type': 'weapon', 'rarity': 'legendary', 'description': 'Der smaragdgrüne Säbel', 'damage': 83, 'damage_type': 'magic', 'price': 2140, 'required_level': 16},
    {'name': 'Gan Jiang und Mo Ye', 'type': 'weapon', 'rarity': 'legendary', 'description': 'Die Zwillingsklingen', 'damage': 84, 'damage_type': 'physical', 'price': 2190, 'required_level': 17},
    {'name': 'Fragarach', 'type': 'weapon', 'rarity': 'legendary', 'description': 'Der Antworter', 'damage': 88, 'damage_type': 'wind', 'price': 2330, 'required_level': 18},
    {'name': 'Carnwennan', 'type': 'weapon', 'rarity': 'legendary', 'description': 'Arthurs Dolch', 'damage': 79, 'damage_type': 'dark', 'price': 1980, 'required_level': 15},
    {'name': 'Claíomh Solais', 'type': 'weapon', 'rarity': 'legendary', 'description': 'Das Schwert des Lichts', 'damage': 87, 'damage_type': 'light', 'price': 2295, 'required_level': 18},
    {'name': 'Hrunting', 'type': 'weapon', 'rarity': 'legendary', 'description': 'Das unfehlbare Schwert', 'damage': 82, 'damage_type': 'water', 'price': 2110, 'required_level': 16},
    {'name': 'Ame-no-Habakiri', 'type': 'weapon', 'rarity': 'legendary', 'description': 'Der Schlangentöter', 'damage': 85, 'damage_type': 'lightning', 'price': 2235, 'required_level': 17},
    {'name': 'Sword of Goujian', 'type': 'weapon', 'rarity': 'legendary', 'description': 'Das zeitlose Schwert', 'damage': 81, 'damage_type': 'magic', 'price': 2090, 'required_level': 15},
]

# ===== EXTENDED SKILLS =====
# Adding 700+ more skills to reach ~800 total

EXTENDED_SKILLS = [
    # ===== MORE HEALING SKILLS =====
    {'name': 'Heilende Berührung', 'type': 'skill', 'rarity': 'common', 'description': 'Sanfte Heilung', 'price': 90, 'required_level': 1, 'effects': json.dumps({'heal': 25})},
    {'name': 'Lebenskraft', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Heilt 50 HP', 'price': 220, 'required_level': 4, 'effects': json.dumps({'heal': 50})},
    {'name': 'Erneuerung', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Heilt 70 HP', 'price': 280, 'required_level': 6, 'effects': json.dumps({'heal': 70})},
    {'name': 'Wiederherstellung', 'type': 'skill', 'rarity': 'rare', 'description': 'Heilt 90 HP', 'price': 480, 'required_level': 7, 'effects': json.dumps({'heal': 90})},
    {'name': 'Vollständige Heilung', 'type': 'skill', 'rarity': 'rare', 'description': 'Heilt 120 HP', 'price': 550, 'required_level': 9, 'effects': json.dumps({'heal': 120})},
    {'name': 'Lebensflut', 'type': 'skill', 'rarity': 'epic', 'description': 'Heilt 140 HP', 'price': 780, 'required_level': 10, 'effects': json.dumps({'heal': 140})},
    {'name': 'Heilige Gnade', 'type': 'skill', 'rarity': 'epic', 'description': 'Heilt 170 HP', 'price': 950, 'required_level': 12, 'effects': json.dumps({'heal': 170})},
    {'name': 'Wunder', 'type': 'skill', 'rarity': 'legendary', 'description': 'Heilt 200 HP', 'price': 1500, 'required_level': 14, 'effects': json.dumps({'heal': 200})},
    {'name': 'Auferstehung', 'type': 'skill', 'rarity': 'legendary', 'description': 'Vollständige Heilung', 'price': 2000, 'required_level': 16, 'effects': json.dumps({'heal': 999})},
    
    # ===== FIRE ATTACK SKILLS EXPANSION =====
    {'name': 'Feuerpfeil', 'type': 'skill', 'rarity': 'common', 'description': 'Schießt einen Feuerpfeil', 'damage': 18, 'damage_type': 'fire', 'price': 95, 'required_level': 2, 'effects': json.dumps({'burn': 0.25})},
    {'name': 'Flammenklinge', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Umhüllt Waffe mit Feuer', 'damage': 28, 'damage_type': 'fire', 'price': 240, 'required_level': 4, 'effects': json.dumps({'burn': 0.35})},
    {'name': 'Feuerschlag', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Ein brennender Schlag', 'damage': 32, 'damage_type': 'fire', 'price': 270, 'required_level': 5, 'effects': json.dumps({'burn': 0.4})},
    {'name': 'Höll enfeuer', 'type': 'skill', 'rarity': 'rare', 'description': 'Entfesselt Höllenfeuer', 'damage': 50, 'damage_type': 'fire', 'price': 600, 'required_level': 8, 'effects': json.dumps({'burn': 0.5})},
    {'name': 'Feuerexplosion', 'type': 'skill', 'rarity': 'rare', 'description': 'Explodierende Flammen', 'damage': 58, 'damage_type': 'fire', 'price': 680, 'required_level': 9, 'effects': json.dumps({'burn': 0.55})},
    {'name': 'Phönixflamme', 'type': 'skill', 'rarity': 'epic', 'description': 'Flammen eines Phönix', 'damage': 72, 'damage_type': 'fire', 'price': 1050, 'required_level': 11, 'effects': json.dumps({'burn': 0.65})},
    {'name': 'Sonneneruption', 'type': 'skill', 'rarity': 'epic', 'description': 'Macht der Sonne', 'damage': 78, 'damage_type': 'fire', 'price': 1180, 'required_level': 12, 'effects': json.dumps({'burn': 0.7})},
    {'name': 'Armageddon', 'type': 'skill', 'rarity': 'legendary', 'description': 'Ultimative Feuermagie', 'damage': 95, 'damage_type': 'fire', 'price': 1800, 'required_level': 15, 'effects': json.dumps({'burn': 0.8})},
    
    # ===== ICE/FROST SKILLS EXPANSION =====
    {'name': 'Eisnadeln', 'type': 'skill', 'rarity': 'common', 'description': 'Schießt Eisnadeln', 'damage': 16, 'damage_type': 'ice', 'price': 105, 'required_level': 2, 'effects': json.dumps({'freeze': 0.2})},
    {'name': 'Frostbiss', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Eisiger Biss', 'damage': 26, 'damage_type': 'ice', 'price': 210, 'required_level': 3, 'effects': json.dumps({'freeze': 0.25})},
    {'name': 'Eisschild', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Erschafft Eisschild', 'price': 260, 'required_level': 5, 'effects': json.dumps({'shield': 2, 'defense_bonus': 15})},
    {'name': 'Frostschock', 'type': 'skill', 'rarity': 'rare', 'description': 'Schockierender Frost', 'damage': 48, 'damage_type': 'ice', 'price': 570, 'required_level': 8, 'effects': json.dumps({'freeze': 0.45})},
    {'name': 'Eisberg', 'type': 'skill', 'rarity': 'rare', 'description': 'Beschwört Eisberg', 'damage': 52, 'damage_type': 'ice', 'price': 620, 'required_level': 9, 'effects': json.dumps({'freeze': 0.5})},
    {'name': 'Ewiger Winter', 'type': 'skill', 'rarity': 'epic', 'description': 'Unendlicher Winter', 'damage': 68, 'damage_type': 'ice', 'price': 1000, 'required_level': 11, 'effects': json.dumps({'freeze': 0.6})},
    {'name': 'Absolute Null', 'type': 'skill', 'rarity': 'legendary', 'description': 'Absoluter Nullpunkt', 'damage': 92, 'damage_type': 'ice', 'price': 1750, 'required_level': 15, 'effects': json.dumps({'freeze': 0.75})},
    
    # ===== LIGHTNING SKILLS EXPANSION =====
    {'name': 'Funken', 'type': 'skill', 'rarity': 'common', 'description': 'Kleine Funken', 'damage': 20, 'damage_type': 'lightning', 'price': 120, 'required_level': 2, 'effects': json.dumps({'static': 0.25})},
    {'name': 'Blitzpfeil', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Schneller Blitzpfeil', 'damage': 33, 'damage_type': 'lightning', 'price': 290, 'required_level': 5, 'effects': json.dumps({'static': 0.35})},
    {'name': 'Blitzschlag (Skill)', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Direkter Blitzschlag', 'damage': 38, 'damage_type': 'lightning', 'price': 320, 'required_level': 6, 'effects': json.dumps({'static': 0.4})},
    {'name': 'Blitzeinschlag', 'type': 'skill', 'rarity': 'rare', 'description': 'Mächtiger Blitzeinschlag', 'damage': 51, 'damage_type': 'lightning', 'price': 610, 'required_level': 9, 'effects': json.dumps({'static': 0.5})},
    {'name': 'Donnerdonner', 'type': 'skill', 'rarity': 'rare', 'description': 'Doppelter Donner', 'damage': 56, 'damage_type': 'lightning', 'price': 670, 'required_level': 10, 'effects': json.dumps({'static': 0.55})},
    {'name': 'Blitzsalve', 'type': 'skill', 'rarity': 'epic', 'description': 'Mehrere Blitze', 'damage': 70, 'damage_type': 'lightning', 'price': 1080, 'required_level': 12, 'effects': json.dumps({'static': 0.65})},
    {'name': 'Göttlicher Blitz', 'type': 'skill', 'rarity': 'legendary', 'description': 'Blitz der Götter', 'damage': 94, 'damage_type': 'lightning', 'price': 1820, 'required_level': 16, 'effects': json.dumps({'static': 0.75})},
    
    # ===== DARK/SHADOW SKILLS EXPANSION =====
    {'name': 'Schattenhauch', 'type': 'skill', 'rarity': 'common', 'description': 'Dunkler Hauch', 'damage': 22, 'damage_type': 'dark', 'price': 135, 'required_level': 2, 'effects': json.dumps({'darkness': 0.25})},
    {'name': 'Dunkelheit', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Umhüllt in Dunkelheit', 'damage': 30, 'damage_type': 'dark', 'price': 260, 'required_level': 4, 'effects': json.dumps({'darkness': 0.35})},
    {'name': 'Schattenklinge (Skill)', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Klinge aus Schatten', 'damage': 34, 'damage_type': 'dark', 'price': 285, 'required_level': 5, 'effects': json.dumps({'darkness': 0.4})},
    {'name': 'Void-Schlag', 'type': 'skill', 'rarity': 'rare', 'description': 'Schlag aus der Leere', 'damage': 47, 'damage_type': 'dark', 'price': 590, 'required_level': 8, 'effects': json.dumps({'lifesteal': 0.4})},
    {'name': 'Schattenriss', 'type': 'skill', 'rarity': 'rare', 'description': 'Reißt Schatten', 'damage': 53, 'damage_type': 'dark', 'price': 640, 'required_level': 9, 'effects': json.dumps({'darkness': 0.5, 'lifesteal': 0.3})},
    {'name': 'Abgrund', 'type': 'skill', 'rarity': 'epic', 'description': 'Öffnet den Abgrund', 'damage': 74, 'damage_type': 'dark', 'price': 1160, 'required_level': 12, 'effects': json.dumps({'darkness': 0.65, 'lifesteal': 0.4})},
    {'name': 'Schwarzes Loch', 'type': 'skill', 'rarity': 'legendary', 'description': 'Erschafft schwarzes Loch', 'damage': 98, 'damage_type': 'dark', 'price': 1900, 'required_level': 16, 'effects': json.dumps({'darkness': 0.8, 'lifesteal': 0.5})},
    
    # ===== LIGHT/HOLY SKILLS EXPANSION =====
    {'name': 'Lichtblitz', 'type': 'skill', 'rarity': 'common', 'description': 'Schneller Lichtblitz', 'damage': 24, 'damage_type': 'light', 'price': 145, 'required_level': 2, 'effects': json.dumps({'light': 0.15})},
    {'name': 'Heiliger Schlag', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Göttlicher Schlag', 'damage': 29, 'damage_type': 'light', 'price': 250, 'required_level': 4, 'effects': json.dumps({'light': 0.25})},
    {'name': 'Lichtsäule', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Säule heiligen Lichts', 'damage': 35, 'damage_type': 'light', 'price': 295, 'required_level': 5, 'effects': json.dumps({'light': 0.35})},
    {'name': 'Sonnenstrahl', 'type': 'skill', 'rarity': 'rare', 'description': 'Strahl der Sonne', 'damage': 54, 'damage_type': 'light', 'price': 650, 'required_level': 9, 'effects': json.dumps({'light': 0.5})},
    {'name': 'Heiliges Feuer', 'type': 'skill', 'rarity': 'rare', 'description': 'Reinigendes Feuer', 'damage': 49, 'damage_type': 'light', 'price': 595, 'required_level': 8, 'effects': json.dumps({'light': 0.45})},
    {'name': 'Göttliche Lanze', 'type': 'skill', 'rarity': 'epic', 'description': 'Lanze der Götter', 'damage': 76, 'damage_type': 'light', 'price': 1190, 'required_level': 13, 'effects': json.dumps({'light': 0.7})},
    {'name': 'Jüngstes Gericht', 'type': 'skill', 'rarity': 'legendary', 'description': 'Endgültiges Urteil', 'damage': 100, 'damage_type': 'light', 'price': 1950, 'required_level': 17, 'effects': json.dumps({'light': 0.85})},
    
    # ===== DEFENSIVE SKILLS EXPANSION =====
    {'name': 'Blockhaltung', 'type': 'skill', 'rarity': 'common', 'description': 'Erhöht Verteidigung', 'price': 180, 'required_level': 3, 'effects': json.dumps({'shield': 1})},
    {'name': 'Schutzschild', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Magischer Schild', 'price': 270, 'required_level': 5, 'effects': json.dumps({'shield': 2, 'defense_bonus': 12})},
    {'name': 'Bastion', 'type': 'skill', 'rarity': 'rare', 'description': 'Unüberwindliche Verteidigung', 'price': 520, 'required_level': 8, 'effects': json.dumps({'shield': 3, 'defense_bonus': 25})},
    {'name': 'Festung', 'type': 'skill', 'rarity': 'rare', 'description': 'Wird zur Festung', 'price': 580, 'required_level': 9, 'effects': json.dumps({'ironSkin': 3, 'defense_bonus': 30})},
    {'name': 'Göttlicher Schutz', 'type': 'skill', 'rarity': 'epic', 'description': 'Schutz der Götter', 'price': 920, 'required_level': 11, 'effects': json.dumps({'invulnerable': 1, 'shield': 2})},
    {'name': 'Unzerstörbar', 'type': 'skill', 'rarity': 'legendary', 'description': 'Totale Unzerstörbarkeit', 'price': 1700, 'required_level': 14, 'effects': json.dumps({'invulnerable': 2})},
    
    # ===== BUFF SKILLS EXPANSION =====
    {'name': 'Schnelligkeit', 'type': 'skill', 'rarity': 'common', 'description': 'Erhöht Geschwindigkeit leicht', 'price': 190, 'required_level': 3, 'effects': json.dumps({'speed_boost': 2})},
    {'name': 'Stärkung', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Erhöht Angriff', 'price': 260, 'required_level': 4, 'effects': json.dumps({'attack_boost': 2, 'damage_bonus': 0.3})},
    {'name': 'Kriegstrance', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Kampfrausch', 'price': 290, 'required_level': 5, 'effects': json.dumps({'rage': 1, 'attack_boost': 2})},
    {'name': 'Tödliche Präzision', 'type': 'skill', 'rarity': 'rare', 'description': 'Extrem hohe Genauigkeit', 'price': 470, 'required_level': 7, 'effects': json.dumps({'accuracy_boost': 3, 'crit_boost': 2})},
    {'name': 'Ultimative Macht', 'type': 'skill', 'rarity': 'epic', 'description': 'Maximale Stärke', 'price': 880, 'required_level': 10, 'effects': json.dumps({'all_stats_boost': 3, 'stat_bonus': 0.5})},
    {'name': 'Göttliche Stärke', 'type': 'skill', 'rarity': 'legendary', 'description': 'Kraft der Götter', 'price': 1650, 'required_level': 14, 'effects': json.dumps({'all_stats_boost': 4, 'stat_bonus': 0.8})},
    
    # ===== DEBUFF SKILLS EXPANSION =====
    {'name': 'Gifthauch', 'type': 'skill', 'rarity': 'common', 'description': 'Vergiftet leicht', 'damage': 12, 'damage_type': 'poison', 'price': 110, 'required_level': 2, 'effects': json.dumps({'poison': 0.4})},
    {'name': 'Schwachpunkt', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Findet Schwachstelle', 'price': 230, 'required_level': 4, 'effects': json.dumps({'weaken': 2, 'attack_reduction': 0.25})},
    {'name': 'Dunkler Fluch (Skill)', 'type': 'skill', 'rarity': 'rare', 'description': 'Mächtiger Fluch', 'price': 490, 'required_level': 8, 'effects': json.dumps({'curse': 3, 'all_stats_reduction': 0.25})},
    {'name': 'Verkrüppelung', 'type': 'skill', 'rarity': 'rare', 'description': 'Verkrüppelt Gegner', 'price': 530, 'required_level': 9, 'effects': json.dumps({'paralyze': 0.8, 'speed_reduction': 30})},
    {'name': 'Totale Schwächung', 'type': 'skill', 'rarity': 'epic', 'description': 'Maximale Schwächung', 'price': 860, 'required_level': 11, 'effects': json.dumps({'weaken': 4, 'attack_reduction': 0.5})},
    {'name': 'Vernichtungsfluch', 'type': 'skill', 'rarity': 'legendary', 'description': 'Ultimativer Fluch', 'price': 1620, 'required_level': 14, 'effects': json.dumps({'curse': 5, 'all_stats_reduction': 0.4})},
    
    # ===== UTILITY/SPECIAL SKILLS EXPANSION =====
    {'name': 'Blinzeln', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Kurzer Teleport', 'price': 340, 'required_level': 5, 'effects': json.dumps({'dodge_boost': 2})},
    {'name': 'Zeitsprung', 'type': 'skill', 'rarity': 'rare', 'description': 'Springt in der Zeit', 'price': 720, 'required_level': 10, 'effects': json.dumps({'extra_turn': True})},
    {'name': 'Vampirschlag', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Stiehlt Leben', 'damage': 27, 'damage_type': 'magic', 'price': 250, 'required_level': 4, 'effects': json.dumps({'lifesteal': 0.4})},
    {'name': 'Reflexschild', 'type': 'skill', 'rarity': 'rare', 'description': 'Reflektiert Schaden', 'price': 560, 'required_level': 9, 'effects': json.dumps({'reflect': 3, 'reflect_damage': 0.6})},
    {'name': 'Wirbelschlag', 'type': 'skill', 'rarity': 'uncommon', 'description': 'Kreisender Angriff', 'price': 310, 'required_level': 5, 'effects': json.dumps({'double_attack': 1})},
    {'name': 'Dreifachschlag', 'type': 'skill', 'rarity': 'rare', 'description': 'Drei schnelle Schläge', 'price': 650, 'required_level': 10, 'effects': json.dumps({'triple_attack': True})},
    {'name': 'Perfekter Konter', 'type': 'skill', 'rarity': 'epic', 'description': 'Kontert perfekt', 'price': 940, 'required_level': 12, 'effects': json.dumps({'counter': 4, 'counter_damage': 1.0})},
    {'name': 'Zeitstop', 'type': 'skill', 'rarity': 'legendary', 'description': 'Stoppt die Zeit', 'price': 2100, 'required_level': 18, 'effects': json.dumps({'time_stop': 2, 'extra_turn': True})},
]

# Generate massive variations programmatically
GENERATED_WEAPONS = generate_weapon_variations()
GENERATED_SKILLS = generate_skill_variations()

# Double the skills by creating elemental variants
ELEMENTAL_VARIANTS = []
for skill in GENERATED_SKILLS[:len(GENERATED_SKILLS)//2]:  # Take half
    if 'damage_type' in skill:
        # Create variants with different elements
        for element in ['fire', 'ice', 'lightning', 'dark', 'light']:
            if skill['damage_type'] != element:
                variant = skill.copy()
                variant['name'] = f"{skill['name']} ({element.capitalize()})"
                variant['damage_type'] = element
                variant['price'] = int(skill['price'] * 1.1)
                ELEMENTAL_VARIANTS.append(variant)
                if len(ELEMENTAL_VARIANTS) >= 500:
                    break
        if len(ELEMENTAL_VARIANTS) >= 500:
            break

GENERATED_SKILLS.extend(ELEMENTAL_VARIANTS)

# Combine all weapons and skills
EXTENDED_WEAPONS.extend(GENERATED_WEAPONS)
EXTENDED_SKILLS.extend(GENERATED_SKILLS)

print(f"RPG Items Data Loaded:")
print(f"  - {len(EXTENDED_WEAPONS)} total weapons")
print(f"  - {len(EXTENDED_SKILLS)} total skills")
