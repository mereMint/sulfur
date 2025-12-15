"""
Sulfur Bot - Theme System Module
Handles user themes that customize the appearance of games and commands.
"""

import discord
from datetime import datetime, timezone
from modules.logger_utils import bot_logger as logger


# Theme definitions with customizations
THEMES = {
    'ocean': {
        'name': 'Ocean',
        'emoji': '🌊',
        'description': 'Deep blue ocean theme with waves and marine life',
        'price': 1500,
        'colors': {
            'primary': discord.Color.blue(),
            'success': discord.Color.from_rgb(0, 150, 200),
            'danger': discord.Color.from_rgb(0, 50, 100),
            'warning': discord.Color.from_rgb(100, 200, 255)
        },
        'game_assets': {
            'tower_name': '🌊 Wellen-Turm',
            'mines_safe': '🐚',  # Shell instead of white box
            'mines_bomb': '🦑',  # Squid instead of bomb
            'mines_revealed': '🐠',  # Fish instead of gem
            'roulette_wheel': '🌀',
            'profile_accent': '🌊'
        }
    },
    'sakura': {
        'name': 'Sakura',
        'emoji': '🌸',
        'description': 'Beautiful Japanese cherry blossom theme',
        'price': 2000,
        'colors': {
            'primary': discord.Color.from_rgb(255, 182, 193),
            'success': discord.Color.from_rgb(255, 105, 180),
            'danger': discord.Color.from_rgb(139, 0, 0),
            'warning': discord.Color.from_rgb(255, 228, 225)
        },
        'game_assets': {
            'tower_name': '🗼 Tokyo Tower',
            'mines_safe': '🌸',  # Cherry blossom
            'mines_bomb': '💣',
            'mines_revealed': '🌺',  # Hibiscus
            'roulette_wheel': '🎴',
            'profile_accent': '🌸'
        }
    },
    'forest': {
        'name': 'Forest',
        'emoji': '🌲',
        'description': 'Lush green forest theme with nature elements',
        'price': 1500,
        'colors': {
            'primary': discord.Color.green(),
            'success': discord.Color.from_rgb(34, 139, 34),
            'danger': discord.Color.from_rgb(139, 69, 19),
            'warning': discord.Color.from_rgb(154, 205, 50)
        },
        'game_assets': {
            'tower_name': '🌲 Waldturm',
            'mines_safe': '🍃',  # Leaf
            'mines_bomb': '🕷️',  # Spider
            'mines_revealed': '🍄',  # Mushroom
            'roulette_wheel': '🎯',
            'profile_accent': '🌲'
        }
    },
    'lucky_strike': {
        'name': 'Lucky Strike',
        'emoji': '🎰',
        'description': 'Glamorous casino theme with golden accents',
        'price': 2500,
        'colors': {
            'primary': discord.Color.gold(),
            'success': discord.Color.from_rgb(255, 215, 0),
            'danger': discord.Color.from_rgb(178, 34, 34),
            'warning': discord.Color.from_rgb(255, 140, 0)
        },
        'game_assets': {
            'tower_name': '🎰 Casino Tower',
            'mines_safe': '💎',  # Diamond
            'mines_bomb': '🎲',  # Dice
            'mines_revealed': '💰',  # Money bag
            'roulette_wheel': '🎰',
            'profile_accent': '🎰'
        }
    },
    'night_life': {
        'name': 'Night Life',
        'emoji': '🌃',
        'description': 'Dark neon-lit city theme',
        'price': 2000,
        'colors': {
            'primary': discord.Color.from_rgb(138, 43, 226),
            'success': discord.Color.from_rgb(0, 255, 255),
            'danger': discord.Color.from_rgb(255, 0, 255),
            'warning': discord.Color.from_rgb(147, 112, 219)
        },
        'game_assets': {
            'tower_name': '🌃 Wolkenkratzer',
            'mines_safe': '✨',  # Sparkles
            'mines_bomb': '💥',  # Explosion
            'mines_revealed': '⭐',  # Star
            'roulette_wheel': '🎡',
            'profile_accent': '🌃'
        }
    },
    'sunset': {
        'name': 'Sunset',
        'emoji': '🌅',
        'description': 'Warm sunset colors with orange and pink hues',
        'price': 1800,
        'colors': {
            'primary': discord.Color.orange(),
            'success': discord.Color.from_rgb(255, 165, 0),
            'danger': discord.Color.from_rgb(255, 69, 0),
            'warning': discord.Color.from_rgb(255, 228, 181)
        },
        'game_assets': {
            'tower_name': '🌅 Horizont-Turm',
            'mines_safe': '☀️',  # Sun
            'mines_bomb': '🌋',  # Volcano
            'mines_revealed': '🔆',  # Bright sun
            'roulette_wheel': '🎪',
            'profile_accent': '🌅'
        }
    },
    'cyberpunk': {
        'name': 'Cyberpunk',
        'emoji': '🌐',
        'description': 'Futuristic neon theme with electric colors',
        'price': 2500,
        'colors': {
            'primary': discord.Color.from_rgb(0, 255, 255),
            'success': discord.Color.from_rgb(57, 255, 20),
            'danger': discord.Color.from_rgb(255, 0, 110),
            'warning': discord.Color.from_rgb(255, 0, 255)
        },
        'game_assets': {
            'tower_name': '🌐 Cyber-Turm',
            'mines_safe': '🔋',  # Battery
            'mines_bomb': '⚡',  # Lightning
            'mines_revealed': '💠',  # Diamond with dot
            'roulette_wheel': '🎮',
            'profile_accent': '🌐'
        }
    },
    'steampunk': {
        'name': 'Steampunk',
        'emoji': '⚙️',
        'description': 'Victorian era mechanical theme with brass and copper',
        'price': 2200,
        'colors': {
            'primary': discord.Color.from_rgb(205, 127, 50),
            'success': discord.Color.from_rgb(184, 134, 11),
            'danger': discord.Color.from_rgb(139, 69, 19),
            'warning': discord.Color.from_rgb(218, 165, 32)
        },
        'game_assets': {
            'tower_name': '⚙️ Dampf-Turm',
            'mines_safe': '🔧',  # Wrench
            'mines_bomb': '💣',  # Bomb
            'mines_revealed': '⚙️',  # Gear
            'roulette_wheel': '🎡',
            'profile_accent': '⚙️'
        }
    },
    'arctic': {
        'name': 'Arctic',
        'emoji': '❄️',
        'description': 'Cool icy theme with winter blues and whites',
        'price': 1900,
        'colors': {
            'primary': discord.Color.from_rgb(173, 216, 230),
            'success': discord.Color.from_rgb(135, 206, 250),
            'danger': discord.Color.from_rgb(70, 130, 180),
            'warning': discord.Color.from_rgb(176, 224, 230)
        },
        'game_assets': {
            'tower_name': '❄️ Eis-Turm',
            'mines_safe': '⛄',  # Snowman
            'mines_bomb': '🌨️',  # Snow cloud
            'mines_revealed': '💎',  # Diamond
            'roulette_wheel': '🎿',
            'profile_accent': '❄️'
        }
    },
    'halloween': {
        'name': 'Halloween',
        'emoji': '🎃',
        'description': 'Spooky Halloween theme with orange and black',
        'price': 2100,
        'colors': {
            'primary': discord.Color.from_rgb(255, 140, 0),
            'success': discord.Color.from_rgb(255, 165, 0),
            'danger': discord.Color.from_rgb(139, 0, 0),
            'warning': discord.Color.from_rgb(255, 69, 0)
        },
        'game_assets': {
            'tower_name': '🎃 Spuk-Turm',
            'mines_safe': '🕷️',  # Spider
            'mines_bomb': '👻',  # Ghost
            'mines_revealed': '🦇',  # Bat
            'roulette_wheel': '🎭',
            'profile_accent': '🎃'
        }
    },
    'retro': {
        'name': 'Retro',
        'emoji': '📼',
        'description': 'Nostalgic 80s theme with vibrant retro colors',
        'price': 2000,
        'colors': {
            'primary': discord.Color.from_rgb(255, 20, 147),
            'success': discord.Color.from_rgb(0, 255, 255),
            'danger': discord.Color.from_rgb(255, 0, 255),
            'warning': discord.Color.from_rgb(255, 255, 0)
        },
        'game_assets': {
            'tower_name': '📼 Retro-Turm',
            'mines_safe': '📺',  # TV
            'mines_bomb': '💾',  # Floppy disk
            'mines_revealed': '🕹️',  # Joystick
            'roulette_wheel': '🎧',
            'profile_accent': '📼'
        }
    },
    'anime': {
        'name': 'Anime',
        'emoji': '🎌',
        'description': 'Japanese anime-inspired theme with vibrant colors',
        'price': 2200,
        'colors': {
            'primary': discord.Color.from_rgb(255, 105, 180),
            'success': discord.Color.from_rgb(0, 191, 255),
            'danger': discord.Color.from_rgb(255, 69, 0),
            'warning': discord.Color.from_rgb(255, 215, 0)
        },
        'game_assets': {
            'tower_name': '🗾 Anime Tower',
            'mines_safe': '⭐',
            'mines_bomb': '💥',
            'mines_revealed': '🌟',
            'roulette_wheel': '🎌',
            'profile_accent': '🎌',
            'anidle_accent': '📺',
            'songle_accent': '🎵'
        }
    },
    'galaxy': {
        'name': 'Galaxy',
        'emoji': '🌌',
        'description': 'Deep space theme with cosmic colors and stars',
        'price': 2300,
        'colors': {
            'primary': discord.Color.from_rgb(25, 25, 112),
            'success': discord.Color.from_rgb(138, 43, 226),
            'danger': discord.Color.from_rgb(75, 0, 130),
            'warning': discord.Color.from_rgb(255, 215, 0)
        },
        'game_assets': {
            'tower_name': '🌌 Galaxie-Turm',
            'mines_safe': '⭐',
            'mines_bomb': '☄️',
            'mines_revealed': '🌟',
            'roulette_wheel': '🪐',
            'profile_accent': '🌌',
            'slots_accent': '💫'
        }
    },
    'music': {
        'name': 'Music',
        'emoji': '🎵',
        'description': 'Musical theme for music lovers',
        'price': 1800,
        'colors': {
            'primary': discord.Color.from_rgb(148, 0, 211),
            'success': discord.Color.from_rgb(255, 20, 147),
            'danger': discord.Color.from_rgb(220, 20, 60),
            'warning': discord.Color.from_rgb(255, 165, 0)
        },
        'game_assets': {
            'tower_name': '🎵 Musik-Turm',
            'mines_safe': '🎶',
            'mines_bomb': '🔇',
            'mines_revealed': '🎤',
            'roulette_wheel': '🎹',
            'profile_accent': '🎵',
            'songle_accent': '🎧'
        }
    },
    'royal': {
        'name': 'Royal',
        'emoji': '👑',
        'description': 'Regal purple and gold theme fit for royalty',
        'price': 2500,
        'colors': {
            'primary': discord.Color.from_rgb(128, 0, 128),
            'success': discord.Color.from_rgb(255, 215, 0),
            'danger': discord.Color.from_rgb(139, 0, 0),
            'warning': discord.Color.from_rgb(218, 165, 32)
        },
        'game_assets': {
            'tower_name': '👑 Königsturm',
            'mines_safe': '💎',
            'mines_bomb': '⚔️',
            'mines_revealed': '👑',
            'roulette_wheel': '🏰',
            'profile_accent': '👑'
        }
    },
    'nature': {
        'name': 'Nature',
        'emoji': '🌿',
        'description': 'Fresh nature theme with earthy greens and browns',
        'price': 1600,
        'colors': {
            'primary': discord.Color.from_rgb(34, 139, 34),
            'success': discord.Color.from_rgb(50, 205, 50),
            'danger': discord.Color.from_rgb(139, 69, 19),
            'warning': discord.Color.from_rgb(255, 215, 0)
        },
        'game_assets': {
            'tower_name': '🌿 Natur-Turm',
            'mines_safe': '🌱',
            'mines_bomb': '🪨',
            'mines_revealed': '🌻',
            'roulette_wheel': '🌈',
            'profile_accent': '🌿'
        }
    },
    'fire': {
        'name': 'Fire',
        'emoji': '🔥',
        'description': 'Hot flame theme with blazing reds and oranges',
        'price': 2000,
        'colors': {
            'primary': discord.Color.from_rgb(255, 69, 0),
            'success': discord.Color.from_rgb(255, 140, 0),
            'danger': discord.Color.from_rgb(178, 34, 34),
            'warning': discord.Color.from_rgb(255, 215, 0)
        },
        'game_assets': {
            'tower_name': '🔥 Feuer-Turm',
            'mines_safe': '🔥',
            'mines_bomb': '💣',
            'mines_revealed': '✨',
            'roulette_wheel': '🌋',
            'profile_accent': '🔥'
        }
    }
}


async def initialize_themes_table(db_helpers):
    """Initialize the themes table in the database."""
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
            # Table for user owned themes
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_themes (
                    user_id BIGINT NOT NULL,
                    theme_id VARCHAR(50) NOT NULL,
                    purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, theme_id),
                    INDEX idx_user (user_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Table for equipped themes
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_equipped_theme (
                    user_id BIGINT PRIMARY KEY,
                    theme_id VARCHAR(50),
                    equipped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_theme (theme_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            conn.commit()
            logger.info("Themes tables initialized successfully")
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error initializing themes tables: {e}", exc_info=True)


async def get_user_theme(db_helpers, user_id: int):
    """Get the currently equipped theme for a user."""
    try:
        if not db_helpers.db_pool:
            return None
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return None
        
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT theme_id FROM user_equipped_theme
                WHERE user_id = %s
            """, (user_id,))
            
            result = cursor.fetchone()
            if result and result['theme_id'] in THEMES:
                return result['theme_id']
            return None
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error getting user theme: {e}", exc_info=True)
        return None


async def get_user_owned_themes(db_helpers, user_id: int):
    """Get all themes owned by a user."""
    try:
        if not db_helpers.db_pool:
            return []
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return []
        
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT theme_id FROM user_themes
                WHERE user_id = %s
            """, (user_id,))
            
            results = cursor.fetchall()
            return [r['theme_id'] for r in results if r['theme_id'] in THEMES]
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error getting owned themes: {e}", exc_info=True)
        return []


async def purchase_theme(db_helpers, user_id: int, theme_id: str):
    """Purchase a theme for a user."""
    try:
        if theme_id not in THEMES:
            return False, "Theme not found!"
        
        if not db_helpers.db_pool:
            return False, "Database connection error."
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return False, "Database connection error."
        
        cursor = conn.cursor()
        try:
            # Check if already owned
            cursor.execute("""
                SELECT 1 FROM user_themes
                WHERE user_id = %s AND theme_id = %s
            """, (user_id, theme_id))
            
            if cursor.fetchone():
                return False, "You already own this theme!"
            
            # Add theme to owned themes
            cursor.execute("""
                INSERT INTO user_themes (user_id, theme_id)
                VALUES (%s, %s)
            """, (user_id, theme_id))
            
            conn.commit()
            return True, f"Successfully purchased {THEMES[theme_id]['name']} theme!"
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error purchasing theme: {e}", exc_info=True)
        return False, "An error occurred during purchase."


async def equip_theme(db_helpers, user_id: int, theme_id: str):
    """Equip a theme for a user."""
    try:
        if theme_id and theme_id not in THEMES:
            return False, "Theme not found!"
        
        if not db_helpers.db_pool:
            return False, "Database connection error."
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return False, "Database connection error."
        
        cursor = conn.cursor()
        try:
            # Check if user owns the theme (if not None)
            if theme_id:
                cursor.execute("""
                    SELECT 1 FROM user_themes
                    WHERE user_id = %s AND theme_id = %s
                """, (user_id, theme_id))
                
                if not cursor.fetchone():
                    return False, "You don't own this theme!"
            
            # Equip theme (or unequip if None)
            if theme_id:
                cursor.execute("""
                    INSERT INTO user_equipped_theme (user_id, theme_id, equipped_at)
                    VALUES (%s, %s, NOW())
                    ON DUPLICATE KEY UPDATE theme_id = %s, equipped_at = NOW()
                """, (user_id, theme_id, theme_id))
                message = f"Successfully equipped {THEMES[theme_id]['name']} theme!"
            else:
                cursor.execute("""
                    DELETE FROM user_equipped_theme WHERE user_id = %s
                """, (user_id,))
                message = "Theme unequipped!"
            
            conn.commit()
            return True, message
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error equipping theme: {e}", exc_info=True)
        return False, "An error occurred while equipping theme."


def get_theme_color(theme_id: str, color_type: str = 'primary'):
    """Get a specific color from a theme."""
    if theme_id and theme_id in THEMES:
        return THEMES[theme_id]['colors'].get(color_type, discord.Color.blue())
    return discord.Color.blue()


def get_theme_asset(theme_id: str, asset_name: str):
    """Get a specific asset/emoji from a theme."""
    if theme_id and theme_id in THEMES:
        return THEMES[theme_id]['game_assets'].get(asset_name, '⬜')
    
    # Default assets
    defaults = {
        'tower_name': '🗼 Tower of Treasure',
        'mines_safe': '⬜',
        'mines_bomb': '💣',
        'mines_revealed': '💎',
        'roulette_wheel': '🎰',
        'profile_accent': '⭐'
    }
    return defaults.get(asset_name, '⬜')


def apply_theme_to_embed(embed: discord.Embed, theme_id: str, color_type: str = 'primary'):
    """Apply theme color to an embed."""
    if theme_id and theme_id in THEMES:
        embed.color = THEMES[theme_id]['colors'].get(color_type, discord.Color.blue())
    return embed
