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
    Places the role just below the bot's top role so the color is always visible,
    regardless of what other roles the user has.
    
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
        
        # Find bot's highest role position to ensure we don't exceed it
        bot_member = guild.get_member(guild.me.id)
        bot_top_position = guild.me.top_role.position if bot_member else len(guild.roles) - 1
        
        # Determine target position for the new color role
        # Strategy: Place just below bot's top role so color is always visible
        # regardless of what other roles the user has
        # All color roles will be grouped together at this high position
        target_position = bot_top_position - 1
        
        # Ensure target position is at least 1 (position 0 is @everyone)
        target_position = max(1, target_position)
        
        # Create the role at a default position first
        role = await guild.create_role(
            name=role_name,
            color=discord_color,
            reason=f"Color role purchased by {member.name}"
        )
        
        # Move role to the target position (high in hierarchy for visibility)
        try:
            await role.edit(position=target_position)
            logger.info(f"Created color role '{role_name}' ({color}) for {member.name} at position {target_position} (below bot's role at {bot_top_position})")
        except discord.Forbidden:
            logger.error(f"Missing permissions to move color role to position {target_position}")
            # Keep at default position
        except discord.HTTPException as e:
            logger.warning(f"Failed to move role to position {target_position}: {e}")
        
        # Assign to member
        await member.add_roles(role)
        
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
    
    # Store equipped color in database
    await db_helpers.set_user_equipped_color(member.id, color)
    
    # --- NEW: Influence COLOR stock ---
    try:
        from modules import stock_market
        await stock_market.record_color_purchase(db_helpers, tier)
    except Exception as e:
        logger.error(f"Failed to record color stock influence: {e}")
    
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
        'casino': 'Casino Access',
        'detective': 'Detective Game',
        'trolly': 'Trolly Problem',
        'unlimited_word_find': 'Unlimited Word Find',
        'unlimited_wordle': 'Unlimited Wordle',
        'rpg_access': 'RPG System Access',
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
        'casino': 'Casino Access',
        'detective': 'Detective Game',
        'trolly': 'Trolly Problem',
        'unlimited_word_find': 'Unlimited Word Find',
        'unlimited_wordle': 'Unlimited Wordle',
        'rpg_access': 'RPG System Access',
        'werwolf_special_roles': 'Werwolf Special Roles',
        'custom_status': 'Custom Status'
    }
    
    for key, price in features.items():
        name = feature_names.get(key, key)
        feature_text += f"**{name}** - {price} {currency}\n"
    
    embed.add_field(name="✨ Feature Unlocks", value=feature_text, inline=False)
    
    embed.set_footer(text="Use /shopbuy to purchase items!")
    
    return embed


def create_color_selection_embed(tier: str, config: dict):
    """Creates an embed showing available colors for a tier."""
    colors = config['modules']['economy']['shop']['color_roles']
    color_map = {
        'basic': colors['basic_colors'],
        'premium': colors['premium_colors'],
        'legendary': colors['legendary_colors']
    }
    
    color_names_map = {
        'basic': colors.get('basic_color_names', []),
        'premium': colors.get('premium_color_names', []),
        'legendary': colors.get('legendary_color_names', [])
    }
    
    available_colors = color_map.get(tier, [])
    color_names = color_names_map.get(tier, [])
    price = colors['prices'][tier]
    currency = config['modules']['economy']['currency_symbol']
    
    embed = discord.Embed(
        title=f"🎨 {tier.capitalize()} Colors - {price} {currency}",
        description="Click a button below to select a color!",
        color=discord.Color.blue()
    )
    
    # Show color swatches with names
    color_display = ""
    for i, color in enumerate(available_colors, 1):
        # Get color name if available, otherwise use hex
        color_name = color_names[i-1] if i-1 < len(color_names) else color
        color_display += f"`{i}` - **{color_name}** `{color}`\n"
    
    embed.add_field(name="Available Colors", value=color_display, inline=False)
    
    return embed
