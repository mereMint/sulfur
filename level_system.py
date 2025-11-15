"""
Manages the leveling system, including XP calculation and granting.
"""
import time
from collections import defaultdict

# Cooldown-Management: Speichert den Zeitstempel der letzten XP-Vergabe pro Benutzer
user_xp_cooldowns = defaultdict(float)

def get_default_config():
    """Returns the default configuration for the leveling system."""
    return {
        "leveling_system": {
            "xp_per_message": 15,
            "xp_per_voice_minute": 5,
            "xp_cooldown_seconds": 60
        }
    }

async def grant_xp(user_id, username, add_xp_func, config):
    """
    Grants XP to a user if they are not on cooldown.
    Returns the new level if the user leveled up, otherwise None.
    """
    cooldown_seconds = config['modules']['leveling']['xp_cooldown_seconds']
    current_time = time.time()

    # Überprüfen, ob der Cooldown abgelaufen ist
    if current_time - user_xp_cooldowns[user_id] > cooldown_seconds:
        # Cooldown ist vorbei, XP vergeben und Zeitstempel aktualisieren
        user_xp_cooldowns[user_id] = current_time
        xp_to_add = config['modules']['leveling']['xp_per_message']
        
        # Die eigentliche Datenbankoperation wird über die `add_xp_func` aufgerufen
        new_level = await add_xp_func(user_id, username, xp_to_add)
        return new_level

    # Benutzer ist noch im Cooldown
    return None