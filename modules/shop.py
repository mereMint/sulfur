"""
Sulfur Bot - Shop System Module
Handles purchases for color roles, features, and unlocks.
"""

import discord
from datetime import datetime, timezone
from modules.logger_utils import bot_logger as logger

# --- Color Role Management ---

async def create_color_role(guild: discord.Guild, member: discord.Member, color: str, role_name: str = None):
    """
    Creates a custom color role for a member.
    
    Args:
        guild: Discord guild
        member: Member to give the role to
        color: Hex color code (e.g., "#FF0000")
        role_name: Optional custom name for the role
    
    Returns:
        (role, error) tuple
    """
    try:
        # Convert hex to discord.Color
        color_int = int(color.replace("#", ""), 16)
        discord_color = discord.Color(color_int)
        
        # Default name if not provided
        if not role_name:
            role_name = f"Color-{member.name}"
        
        # Create the role just above the member's highest role
        position = member.top_role.position + 1
        
        role = await guild.create_role(
            name=role_name,
            color=discord_color,
            reason=f"Color role purchased by {member.name}"
        )
        
        # Move role to proper position
        await role.edit(position=position)
        
        # Assign to member
        await member.add_roles(role)
        
        logger.info(f"Created color role '{role_name}' ({color}) for {member.name}")
        return role, None
        
    except discord.Forbidden:
        return None, "Bot doesn't have permission to create roles."
    except discord.HTTPException as e:
        return None, f"Failed to create role: {str(e)}"
    except Exception as e:
        logger.error(f"Error creating color role: {e}", exc_info=True)
        return None, f"An error occurred: {str(e)}"


async def remove_existing_color_role(member: discord.Member):
    """
    Removes existing color roles from a member (roles starting with 'Color-').
    
    Args:
        member: Discord member
    
    Returns:
        Number of roles removed
    """
    removed = 0
    try:
        for role in member.roles:
            if role.name.startswith("Color-"):
                await member.remove_roles(role)
                # Delete the role if no one else has it
                if len(role.members) == 0:
                    await role.delete(reason="Color role no longer in use")
                removed += 1
        
        return removed
    except Exception as e:
        logger.error(f"Error removing color roles: {e}", exc_info=True)
        return 0


async def purchase_color_role(db_helpers, member: discord.Member, color: str, tier: str, price: int, config: dict):
    """
    Purchase a color role.
    
    Args:
        db_helpers: Database helpers module
        member: Discord member
        color: Hex color code
        tier: Color tier (basic/premium/legendary)
        price: Cost of the color
        config: Bot configuration
    
    Returns:
        (success, message, role) tuple
    """
    # Check balance
    stat_period = datetime.now(timezone.utc).strftime('%Y-%m')
    balance = await db_helpers.get_balance(member.id)
    
    if balance < price:
        return False, f"Insufficient funds! You need {price} {config['modules']['economy']['currency_symbol']} but only have {balance}.", None
    
    # Remove existing color role
    await remove_existing_color_role(member)
    
    # Create new role
    role, error = await create_color_role(member.guild, member, color)
    
    if error:
        return False, f"Failed to create color role: {error}", None
    
    # Deduct balance and log transaction
    new_balance = await db_helpers.add_balance(member.id, member.display_name, -price, config, stat_period)
    await db_helpers.log_transaction(
        member.id,
        'shop_purchase',
        -price,
        new_balance,
        f"Purchased {tier} color role ({color})"
    )
    
    currency = config['modules']['economy']['currency_symbol']
    return True, f"Successfully purchased {tier} color role for {price} {currency}!", role


# --- Feature Unlocks ---

async def purchase_feature(db_helpers, member: discord.Member, feature: str, price: int, config: dict):
    """
    Purchase a feature unlock.
    
    Args:
        db_helpers: Database helpers module
        member: Discord member
        feature: Feature name (dm_access, games_access, etc.)
        price: Cost of the feature
        config: Bot configuration
    
    Returns:
        (success, message) tuple
    """
    # Check if already owned
    has_feature = await db_helpers.has_feature_unlock(member.id, feature)
    if has_feature:
        return False, f"You already own this feature!"
    
    # Check balance
    stat_period = datetime.now(timezone.utc).strftime('%Y-%m')
    balance = await db_helpers.get_balance(member.id)
    
    if balance < price:
        currency = config['modules']['economy']['currency_symbol']
        return False, f"Insufficient funds! You need {price} {currency} but only have {balance}."
    
    # Deduct balance and log transaction
    new_balance = await db_helpers.add_balance(member.id, member.display_name, -price, config, stat_period)
    await db_helpers.log_transaction(
        member.id,
        'shop_purchase',
        -price,
        new_balance,
        f"Purchased feature: {feature}"
    )
    
    # Grant feature
    await db_helpers.add_feature_unlock(member.id, feature)
    
    currency = config['modules']['economy']['currency_symbol']
    feature_names = {
        'dm_access': 'DM Access',
        'games_access': 'Games Access',
        'werwolf_special_roles': 'Werwolf Special Roles',
        'custom_status': 'Custom Status'
    }
    
    feature_display = feature_names.get(feature, feature)
    return True, f"Successfully purchased {feature_display} for {price} {currency}!"


# --- Shop UI Helpers ---

def create_shop_embed(config: dict):
    """Creates the main shop embed."""
    embed = discord.Embed(
        title="🛒 Sulfur Shop",
        description="Purchase colors, features, and unlocks!",
        color=discord.Color.blue()
    )
    
    currency = config['modules']['economy']['currency_symbol']
    shop_config = config['modules']['economy']['shop']
    
    # Color Roles
    if shop_config['color_roles']['enabled']:
        prices = shop_config['color_roles']['prices']
        color_text = f"**Basic Colors** - {prices['basic']} {currency}\n"
        color_text += f"**Premium Colors** - {prices['premium']} {currency}\n"
        color_text += f"**Legendary Colors** - {prices['legendary']} {currency}"
        embed.add_field(name="🎨 Color Roles", value=color_text, inline=False)
    
    # Features
    features = shop_config['features']
    feature_text = ""
    feature_names = {
        'dm_access': 'DM Access',
        'games_access': 'Games Access',
        'werwolf_special_roles': 'Werwolf Special Roles',
        'custom_status': 'Custom Status'
    }
    
    for key, price in features.items():
        name = feature_names.get(key, key)
        feature_text += f"**{name}** - {price} {currency}\n"
    
    embed.add_field(name="✨ Feature Unlocks", value=feature_text, inline=False)
    
    embed.set_footer(text="Use /shop buy to purchase items!")
    
    return embed


def create_color_selection_embed(tier: str, config: dict):
    """Creates an embed showing available colors for a tier."""
    colors = config['modules']['economy']['shop']['color_roles']
    color_map = {
        'basic': colors['basic_colors'],
        'premium': colors['premium_colors'],
        'legendary': colors['legendary_colors']
    }
    
    available_colors = color_map.get(tier, [])
    price = colors['prices'][tier]
    currency = config['modules']['economy']['currency_symbol']
    
    embed = discord.Embed(
        title=f"🎨 {tier.capitalize()} Colors - {price} {currency}",
        description="Click a button below to select a color!",
        color=discord.Color.blue()
    )
    
    # Show color swatches
    color_display = ""
    for i, color in enumerate(available_colors, 1):
        color_display += f"`{i}` - {color}\n"
    
    embed.add_field(name="Available Colors", value=color_display, inline=False)
    
    return embed
