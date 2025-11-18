"""
Sulfur Bot - Economy System Module
Handles currency, balances, transactions, and daily rewards.
"""

from datetime import datetime, timezone, timedelta
from modules.logger_utils import bot_logger as logger


def calculate_level_up_bonus(level, config):
    """Calculates the currency bonus for reaching a new level."""
    return level * config['modules']['economy']['level_up_bonus_multiplier']


async def get_balance(db_helpers, user_id: int):
    """
    Gets the current balance for a user.
    
    Args:
        db_helpers: Database helpers module
        user_id: Discord user ID
    
    Returns:
        int: Current balance
    """
    try:
        if not db_helpers.db_pool:
            logger.warning("Database pool not available in get_balance")
            return 0
            
        cnx = db_helpers.db_pool.get_connection()
        if not cnx:
            logger.warning("Could not get DB connection in get_balance")
            return 0
            
        cursor = cnx.cursor(dictionary=True)
        try:
            # Get balance from user_stats table
            stat_period = datetime.now(timezone.utc).strftime('%Y-%m')
            cursor.execute(
                "SELECT balance FROM user_stats WHERE user_id = %s AND stat_period = %s",
                (user_id, stat_period)
            )
            result = cursor.fetchone()
            
            if result:
                return result['balance'] or 0
            
            # User doesn't exist, return starting balance
            return 0
        finally:
            cursor.close()
            cnx.close()
    except Exception as e:
        logger.error(f"Error getting balance for user {user_id}: {e}", exc_info=True)
        return 0


async def grant_daily_reward(db_helpers, user_id: int, display_name: str, config: dict):
    """
    Grants daily reward to a user if eligible.
    
    Args:
        db_helpers: Database helpers module
        user_id: Discord user ID
        display_name: User's display name
        config: Bot configuration
    
    Returns:
        (success, amount, message) tuple
    """
    try:
        if not db_helpers.db_pool:
            logger.warning("Database pool not available in grant_daily_reward")
            return False, 0, "Database connection error."
            
        cnx = db_helpers.db_pool.get_connection()
        if not cnx:
            logger.warning("Could not get DB connection in grant_daily_reward")
            return False, 0, "Database connection error."
            
        cursor = cnx.cursor(dictionary=True)
        try:
            # Check last daily claim
            cursor.execute(
                "SELECT last_daily_claim FROM user_economy WHERE user_id = %s",
                (user_id,)
            )
            result = cursor.fetchone()
            
            now = datetime.now(timezone.utc)
            can_claim = True
            
            if result and result['last_daily_claim']:
                last_claim = result['last_daily_claim']
                if isinstance(last_claim, str):
                    last_claim = datetime.fromisoformat(last_claim.replace('Z', '+00:00'))
                
                # Check if 24 hours have passed
                if (now - last_claim).total_seconds() < 86400:
                    time_left = 86400 - (now - last_claim).total_seconds()
                    hours = int(time_left // 3600)
                    minutes = int((time_left % 3600) // 60)
                    return False, 0, f"You already claimed today! Come back in {hours}h {minutes}m."
            
            # Grant reward
            amount = config['modules']['economy']['daily_reward']
            stat_period = now.strftime('%Y-%m')
            
            await db_helpers.add_balance(user_id, display_name, amount, config, stat_period)
            
            # Update last claim time
            cursor.execute(
                """
                INSERT INTO user_economy (user_id, last_daily_claim)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE last_daily_claim = %s
                """,
                (user_id, now, now)
            )
            cnx.commit()
            
            currency = config['modules']['economy']['currency_symbol']
            return True, amount, f"Daily reward claimed! +{amount} {currency}"
        finally:
            cursor.close()
            cnx.close()
            
    except Exception as e:
        logger.error(f"Error granting daily reward: {e}", exc_info=True)
        return False, 0, "An error occurred while claiming your daily reward."


async def transfer_currency(db_helpers, from_user_id: int, to_user_id: int, amount: int, from_name: str, to_name: str, config: dict):
    """
    Transfer currency between users.
    
    Args:
        db_helpers: Database helpers module
        from_user_id: Sender's user ID
        to_user_id: Receiver's user ID
        amount: Amount to transfer
        from_name: Sender's display name
        to_name: Receiver's display name
        config: Bot configuration
    
    Returns:
        (success, message) tuple
    """
    if amount <= 0:
        return False, "Amount must be positive!"
    
    if from_user_id == to_user_id:
        return False, "You can't send money to yourself!"
    
    try:
        # Check sender balance
        balance = await get_balance(db_helpers, from_user_id)
        if balance < amount:
            currency = config['modules']['economy']['currency_symbol']
            return False, f"Insufficient funds! You have {balance} {currency} but need {amount}."
        
        # Perform transfer
        stat_period = datetime.now(timezone.utc).strftime('%Y-%m')
        
        await db_helpers.add_balance(from_user_id, from_name, -amount, config, stat_period)
        await db_helpers.add_balance(to_user_id, to_name, amount, config, stat_period)
        
        currency = config['modules']['economy']['currency_symbol']
        return True, f"Successfully transferred {amount} {currency} to {to_name}!"
        
    except Exception as e:
        logger.error(f"Error transferring currency: {e}", exc_info=True)
        return False, "An error occurred during the transfer."


async def get_leaderboard(db_helpers, limit: int = 10):
    """
    Gets the currency leaderboard.
    
    Args:
        db_helpers: Database helpers module
        limit: Number of top users to return
    
    Returns:
        List of (user_id, display_name, balance) tuples
    """
    try:
        if not db_helpers.db_pool:
            logger.warning("Database pool not available in get_leaderboard")
            return []
            
        cnx = db_helpers.db_pool.get_connection()
        if not cnx:
            logger.warning("Could not get DB connection in get_leaderboard")
            return []
            
        cursor = cnx.cursor(dictionary=True)
        try:
            stat_period = datetime.now(timezone.utc).strftime('%Y-%m')
            cursor.execute(
                """
                SELECT user_id, display_name, balance
                FROM user_stats
                WHERE stat_period = %s
                ORDER BY balance DESC
                LIMIT %s
                """,
                (stat_period, limit)
            )
            results = cursor.fetchall()
            return [(r['user_id'], r['display_name'], r['balance']) for r in results]
        finally:
            cursor.close()
            cnx.close()
    except Exception as e:
        logger.error(f"Error getting leaderboard: {e}", exc_info=True)
        return []
