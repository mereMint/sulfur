# Content Generation Guide - RPG System

This guide helps with generating monsters and content for the Sulfur Bot RPG system.

## Status Effects

Status effects can be applied during combat and last for multiple turns:

| Effect | Emoji | Description | Mechanics |
|--------|-------|-------------|-----------|
| **Brennen** (Burn) | 🔥 | Sets target on fire | 5 damage/turn for 3 turns |
| **Vergiftung** (Poison) | 🧪 | Poisons target | 7 damage/turn for 4 turns |
| **Dunkelheit** (Darkness) | 🌑 | Obscures vision | -30% accuracy for 2 turns |
| **Licht** (Light) | ✨ | Illuminates battlefield | +20% accuracy for 3 turns |
| **Statisch** (Static) | ⚡ | Electric charge | 30% paralyze chance/turn for 2 turns |
| **Gefroren** (Freeze) | ❄️ | Freezes solid | Cannot act for 1 turn |
| **Regeneration** (Heal) | 💚 | Gradual healing | +10 HP/turn for 3 turns |
| **Schild** (Shield) | 🛡️ | Protective barrier | -50% damage taken for 2 turns |
| **Wut** (Rage) | 😡 | Berserker fury | +50% attack, -30% defense for 2 turns |

## Monster Abilities

Abilities are special attacks that can trigger during combat:

### Damage/Status Abilities

| Ability | Emoji | Effect | Trigger % | Description |
|---------|-------|--------|-----------|-------------|
| **Feueratem** (Fire Breath) | 🔥 | Applies Burn | 30% | Breathes flames at target |
| **Giftspeier** (Poison Spit) | 🧪 | Applies Poison | 25% | Spits venomous projectile |
| **Schattenumhang** (Shadow Cloak) | 🌑 | Applies Darkness | 20% | Shrouds in shadows |
| **Blitzschlag** (Lightning Strike) | ⚡ | Applies Static | 30% | Calls down lightning |
| **Frostnova** (Frost Nova) | ❄️ | Applies Freeze | 15% | Erupts with freezing cold |

### Buff/Debuff Abilities

| Ability | Emoji | Effect | Trigger % | Description |
|---------|-------|--------|-----------|-------------|
| **Kriegsschrei** (Battle Roar) | 😡 | Self: Applies Rage | 25% | Roars to increase power |
| **Regeneration** | 💚 | Self: Applies Heal | 20% | Regenerates health |
| **Panzerung** (Armor Up) | 🛡️ | Self: Applies Shield | 20% | Hardens defenses |

### Special Abilities

| Ability | Emoji | Effect | Trigger % | Description |
|---------|-------|--------|-----------|-------------|
| **Kritischer Schlag** (Critical Strike) | 💥 | 2.5x damage | 20% | Devastating critical hit |
| **Lebensentzug** (Life Drain) | 🩸 | Steals 50% damage as HP | 25% | Drains life force |

## Monster Stat Guidelines

When creating monsters, stats vary ±15-20% from base values:

### Base Stat Ranges by Level

| Level Range | Health | Strength | Defense | Speed |
|-------------|--------|----------|---------|-------|
| 1-3 | 30-60 | 3-7 | 2-4 | 5-10 |
| 4-6 | 70-90 | 9-15 | 5-8 | 6-9 |
| 7-9 | 100-150 | 16-20 | 8-15 | 4-12 |
| 10-12 | 180-220 | 25-30 | 18-20 | 10-12 |
| 13-16 | 250-280 | 35-40 | 22-25 | 14-15 |
| 17-20 | 320-400 | 45-50 | 30-35 | 11-13 |

**Note**: Actual stats in encounters will vary by ±15-20% from these base values.

## Assigning Abilities to Monsters

When creating monsters, choose 1-4 abilities based on theme:

### Fire/Dragon Theme
- `fire_breath` (primary)
- `critical_strike` (common for strong monsters)
- `battle_roar` (optional)

### Poison/Toxin Theme
- `poison_spit` (primary)
- `shadow_cloak` (stealth)
- `regeneration` (optional)

### Ice/Frost Theme
- `frost_nova` (primary)
- `armor_up` (defensive)
- `critical_strike` (optional)

### Electric/Lightning Theme
- `lightning_strike` (primary)
- `critical_strike` (optional)

### Dark/Shadow Theme
- `shadow_cloak` (primary)
- `life_drain` (primary)
- `poison_spit` (optional)

### Tank/Heavy Theme
- `armor_up` (primary)
- `battle_roar` (primary)
- `regeneration` (primary)
- `critical_strike` (optional)

### Fast/Agile Theme
- `critical_strike` (primary)
- `battle_roar` (optional)

## Example Monster Definitions

```python
# Low-level poison monster
{
    'name': 'Giftkröte',
    'world': 'overworld',
    'level': 2,
    'health': 40,
    'strength': 4,
    'defense': 2,
    'speed': 8,
    'xp_reward': 20,
    'gold_reward': 15,
    'abilities': ['poison_spit']
}

# Mid-level ice monster
{
    'name': 'Frostwächter',
    'world': 'overworld',
    'level': 7,
    'health': 110,
    'strength': 14,
    'defense': 16,
    'speed': 6,
    'xp_reward': 90,
    'gold_reward': 70,
    'abilities': ['frost_nova', 'armor_up']
}

# High-level dragon
{
    'name': 'Uralter Drache',
    'world': 'underworld',
    'level': 25,
    'health': 500,
    'strength': 60,
    'defense': 40,
    'speed': 15,
    'xp_reward': 1200,
    'gold_reward': 800,
    'abilities': ['fire_breath', 'lightning_strike', 'critical_strike', 'regeneration']
}
```

## Reward Guidelines

- **XP Reward**: Level × 10 to Level × 20
- **Gold Reward**: Level × 5 to Level × 15
- Higher level monsters should give proportionally more rewards

## Adding Monsters to Database

Use the RPG admin commands or add to `DEFAULT_MONSTERS` list in `modules/rpg_system.py`:

```python
DEFAULT_MONSTERS = [
    {
        'name': 'Monster Name',
        'world': 'overworld' or 'underworld',
        'level': 1-50,
        'health': base_hp,
        'strength': base_str,
        'defense': base_def,
        'speed': base_spd,
        'xp_reward': xp,
        'gold_reward': gold,
        'abilities': ['ability1', 'ability2']  # 1-4 abilities
    },
    # ... more monsters
]
```

## Tips for Content Generation

1. **Theme Consistency**: Choose abilities that match monster theme
2. **Balance**: More abilities = higher challenge = better rewards
3. **Variety**: Mix different ability types for interesting encounters
4. **Progression**: Higher level monsters should have more/stronger abilities
5. **Stat Variation**: Remember stats vary ±15-20% in actual encounters

## Available Ability Keys

For quick reference when assigning abilities:
- `fire_breath`
- `poison_spit`
- `shadow_cloak`
- `lightning_strike`
- `frost_nova`
- `battle_roar`
- `regeneration`
- `armor_up`
- `critical_strike`
- `life_drain`
