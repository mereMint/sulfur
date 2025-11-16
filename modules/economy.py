def calculate_level_up_bonus(level, config):
    """Calculates the currency bonus for reaching a new level."""
    return level * config['modules']['economy']['level_up_bonus_multiplier']