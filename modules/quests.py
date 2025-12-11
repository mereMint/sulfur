"""
Sulfur Bot - Quest System Module
Handles daily quests, monthly tracking, and special completion rewards.
"""

import discord
from datetime import datetime, timezone, timedelta
from modules.logger_utils import bot_logger as logger


# ============================================================================
# Quest Generation & Management
# ============================================================================

async def generate_daily_quests(db_helpers, user_id: int, config: dict):
    """
    Generates 3 daily quests for a user if they don't already have them.
    
    Args:
        db_helpers: Database helpers module
        user_id: Discord user ID
        config: Bot configuration
    
    Returns:
        List of quest dictionaries
    """
    try:
        today = datetime.now(timezone.utc).date()
        
        if not db_helpers.db_pool:
            logger.warning("Database pool not available in generate_daily_quests")
            return []
            
        cnx = db_helpers.db_pool.get_connection()
        if not cnx:
            logger.warning("Could not get DB connection in generate_daily_quests")
            return []
            
        cursor = cnx.cursor(dictionary=True)
        try:
            # Check if quests already exist for today
            cursor.execute(
                "SELECT * FROM daily_quests WHERE user_id = %s AND quest_date = %s",
                (user_id, today)
            )
            existing_quests = cursor.fetchall()
            
            if existing_quests:
                # Add reward information from config
                quest_config = config['modules']['economy']['quests']['quest_types']
                for quest in existing_quests:
                    quest_type = quest.get('quest_type')
                    if quest_type and quest_type in quest_config:
                        quest['reward'] = quest_config[quest_type]['reward']
                        quest['xp_reward'] = quest_config[quest_type].get('xp_reward', 0)
                return existing_quests
            
            # Generate 3 new quests
            quest_config = config['modules']['economy']['quests']['quest_types']
            available_quests = list(quest_config.keys())
            randomize_targets = config['modules']['economy']['quests'].get('randomize_targets', False)
            
            # Select 3 random quest types (or all if less than 3)
            import random
            selected_types = random.sample(available_quests, min(3, len(available_quests)))
            
            created_quests = []
            for quest_type in selected_types:
                quest_data = quest_config[quest_type]
                
                # Randomize target if enabled
                if randomize_targets and 'target_min' in quest_data and 'target_max' in quest_data:
                    target_min = quest_data['target_min']
                    target_max = quest_data['target_max']
                    target_step = quest_data.get('target_step', 5)
                    
                    # Generate random target in steps
                    steps = (target_max - target_min) // target_step + 1
                    target_value = target_min + (random.randint(0, steps - 1) * target_step)
                else:
                    target_value = quest_data['target']
                
                cursor.execute(
                    """
                    INSERT INTO daily_quests (user_id, quest_date, quest_type, target_value, current_progress)
                    VALUES (%s, %s, %s, %s, 0)
                    """,
                    (user_id, today, quest_type, target_value)
                )
                
                # Get the ID of the inserted quest
                quest_id = cursor.lastrowid
                
                created_quests.append({
                    'id': quest_id,
                    'quest_type': quest_type,
                    'target_value': target_value,
                    'reward': quest_data['reward'],
                    'xp_reward': quest_data.get('xp_reward', 0),
                    'current_progress': 0,
                    'completed': False,
                    'reward_claimed': False
                })
            
            cnx.commit()
            logger.info(f"Generated {len(created_quests)} daily quests for user {user_id}")
            return created_quests
        finally:
            cursor.close()
            cnx.close()
            
    except Exception as e:
        logger.error(f"Error generating daily quests: {e}", exc_info=True)
        return []


async def update_quest_progress(db_helpers, user_id: int, quest_type: str, increment: int = 1, config: dict = None):
    """
    Updates progress for a specific quest type.
    Auto-generates quests if they don't exist yet.
    
    Args:
        db_helpers: Database helpers module
        user_id: Discord user ID
        quest_type: Type of quest (messages, vc_minutes, reactions, game_minutes)
        increment: Amount to increment progress by
        config: Bot configuration (required for auto-generating quests)
    
    Returns:
        (quest_completed, reward_amount) tuple
    """
    try:
        today = datetime.now(timezone.utc).date()
        
        if not db_helpers.db_pool:
            logger.warning("Database pool not available in update_quest_progress")
            return False, 0
            
        cnx = db_helpers.db_pool.get_connection()
        if not cnx:
            logger.warning("Could not get DB connection in update_quest_progress")
            return False, 0
            
        cursor = cnx.cursor(dictionary=True)
        try:
            # Get current quest
            cursor.execute(
                """
                SELECT * FROM daily_quests 
                WHERE user_id = %s AND quest_date = %s AND quest_type = %s AND completed = FALSE
                """,
                (user_id, today, quest_type)
            )
            quest = cursor.fetchone()
            
            # If quest doesn't exist and we have config, try to generate quests
            if not quest and config:
                logger.info(f"Quest {quest_type} not found for user {user_id}, auto-generating daily quests")
                cursor.close()
                cnx.close()
                
                # Generate quests for this user
                generated_quests = await generate_daily_quests(db_helpers, user_id, config)
                
                # If generation failed, return early
                if not generated_quests:
                    logger.warning(f"Failed to auto-generate quests for user {user_id}")
                    return False, 0
                
                # Reconnect and try again
                cnx = db_helpers.db_pool.get_connection()
                if not cnx:
                    return False, 0
                cursor = cnx.cursor(dictionary=True)
                
                cursor.execute(
                    """
                    SELECT * FROM daily_quests 
                    WHERE user_id = %s AND quest_date = %s AND quest_type = %s AND completed = FALSE
                    """,
                    (user_id, today, quest_type)
                )
                quest = cursor.fetchone()
            
            if not quest:
                logger.debug(f"No quest of type {quest_type} found for user {user_id} on {today}")
                return False, 0
            
            # Update progress
            new_progress = quest['current_progress'] + increment
            cursor.execute(
                """
                UPDATE daily_quests
                SET current_progress = %s
                WHERE id = %s
                """,
                (new_progress, quest['id'])
            )
            
            # Check if quest completed
            if new_progress >= quest['target_value'] and not quest['completed']:
                cursor.execute(
                    """
                    UPDATE daily_quests
                    SET completed = TRUE
                    WHERE id = %s
                    """,
                    (quest['id'],)
                )
                cnx.commit()
                
                # Return completion status - reward will be claimed separately
                logger.info(f"Quest {quest_type} completed for user {user_id}")
                return True, 0  # Reward amount is 0 until claimed
            
            cnx.commit()
            return False, 0
        finally:
            cursor.close()
            cnx.close()
            
    except Exception as e:
        logger.error(f"Error updating quest progress: {e}", exc_info=True)
        return False, 0


async def claim_quest_reward(db_helpers, user_id: int, display_name: str, quest_id: int, config: dict):
    """
    Claims the reward for a completed quest.
    
    Args:
        db_helpers: Database helpers module
        user_id: Discord user ID
        display_name: User's display name
        quest_id: Quest ID to claim
        config: Bot configuration
    
    Returns:
        (success, reward_amount, xp_amount, message) tuple
    """
    try:
        if not db_helpers.db_pool:
            logger.warning("Database pool not available in claim_quest_reward")
            return False, 0, 0, "Database connection error."
            
        cnx = db_helpers.db_pool.get_connection()
        if not cnx:
            logger.warning("Could not get DB connection in claim_quest_reward")
            return False, 0, 0, "Database connection error."
            
        cursor = cnx.cursor(dictionary=True)
        try:
            # Get quest details - simplified query that works with all quest types
            cursor.execute(
                """
                SELECT * FROM daily_quests
                WHERE id = %s AND user_id = %s AND completed = TRUE AND reward_claimed = FALSE
                """,
                (quest_id, user_id)
            )
            quest = cursor.fetchone()
            
            if not quest:
                return False, 0, 0, "Quest not found, already claimed, or not completed."
            
            # Get reward amount from config
            quest_config = config['modules']['economy']['quests']['quest_types'].get(quest['quest_type'])
            if not quest_config:
                return False, 0, 0, "Invalid quest type."
            
            reward = quest_config['reward']
            xp_reward = quest_config.get('xp_reward', 0)
            
            # Mark as claimed
            cursor.execute(
                """
                UPDATE daily_quests
                SET reward_claimed = TRUE
                WHERE id = %s
                """,
                (quest_id,)
            )
            
            # Award currency
            stat_period = datetime.now(timezone.utc).strftime('%Y-%m')
            await db_helpers.add_balance(user_id, display_name, reward, config, stat_period)
            
            # Award XP if enabled
            if xp_reward > 0:
                try:
                    await db_helpers.add_xp(user_id, display_name, xp_reward, config, stat_period)
                except Exception as e:
                    logger.error(f"Error awarding quest XP: {e}", exc_info=True)
            
            cnx.commit()
            
            currency = config['modules']['economy']['currency_symbol']
            message = f"Quest reward claimed! +{reward} {currency}"
            if xp_reward > 0:
                message += f" +{xp_reward} XP"
            return True, reward, xp_reward, message
        finally:
            cursor.close()
            cnx.close()
            
    except Exception as e:
        logger.error(f"Error claiming quest reward: {e}", exc_info=True)
        return False, 0, 0, "An error occurred while claiming the reward."


async def get_user_quests(db_helpers, user_id: int, config: dict):
    """
    Gets all quests for a user for today.
    
    Args:
        db_helpers: Database helpers module
        user_id: Discord user ID
        config: Bot configuration
    
    Returns:
        List of quest dictionaries with progress
    """
    try:
        today = datetime.now(timezone.utc).date()
        
        if not db_helpers.db_pool:
            logger.warning("Database pool not available in get_user_quests")
            return []
            
        cnx = db_helpers.db_pool.get_connection()
        if not cnx:
            logger.warning("Could not get DB connection in get_user_quests")
            return []
            
        cursor = cnx.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT * FROM daily_quests
                WHERE user_id = %s AND quest_date = %s
                ORDER BY quest_type
                """,
                (user_id, today)
            )
            quests = cursor.fetchall()
            
            # Add reward amounts from config
            quest_config = config['modules']['economy']['quests']['quest_types']
            for quest in quests:
                quest_type_config = quest_config.get(quest['quest_type'], {})
                quest['reward'] = quest_type_config.get('reward', 0)
                quest['xp_reward'] = quest_type_config.get('xp_reward', 0)
            
            return quests
        finally:
            cursor.close()
            cnx.close()
            
    except Exception as e:
        logger.error(f"Error getting user quests: {e}", exc_info=True)
        return []


async def check_all_quests_completed(db_helpers, user_id: int):
    """
    Checks if all 3 daily quests are completed for today.
    
    Args:
        db_helpers: Database helpers module
        user_id: Discord user ID
    
    Returns:
        (all_completed, completed_count, total_count) tuple
    """
    try:
        today = datetime.now(timezone.utc).date()
        
        if not db_helpers.db_pool:
            logger.warning("Database pool not available in check_all_quests_completed")
            return False, 0, 0
            
        cnx = db_helpers.db_pool.get_connection()
        if not cnx:
            logger.warning("Could not get DB connection in check_all_quests_completed")
            return False, 0, 0
            
        cursor = cnx.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT COUNT(*) as total, SUM(completed) as completed
                FROM daily_quests
                WHERE user_id = %s AND quest_date = %s
                """,
                (user_id, today)
            )
            result = cursor.fetchone()
            
            total = result['total'] or 0
            completed = result['completed'] or 0
            
            all_completed = total > 0 and total == completed
            return all_completed, completed, total
        finally:
            cursor.close()
            cnx.close()
            
    except Exception as e:
        logger.error(f"Error checking quest completion: {e}", exc_info=True)
        return False, 0, 0


async def grant_daily_completion_bonus(db_helpers, user_id: int, display_name: str, config: dict):
    """
    Grants bonus reward for completing all daily quests.
    
    Args:
        db_helpers: Database helpers module
        user_id: Discord user ID
        display_name: User's display name
        config: Bot configuration
    
    Returns:
        (success, bonus_amount, xp_amount) tuple
    """
    try:
        today = datetime.now(timezone.utc).date()
        
        if not db_helpers.db_pool:
            logger.warning("Database pool not available in grant_daily_completion_bonus")
            return False, 0, 0
            
        cnx = db_helpers.db_pool.get_connection()
        if not cnx:
            logger.warning("Could not get DB connection in grant_daily_completion_bonus")
            return False, 0, 0
            
        cursor = cnx.cursor(dictionary=True)
        try:
            # Check if already claimed bonus today
            cursor.execute(
                """
                SELECT bonus_claimed FROM daily_quest_completions
                WHERE user_id = %s AND completion_date = %s
                """,
                (user_id, today)
            )
            result = cursor.fetchone()
            
            if result and result['bonus_claimed']:
                return False, 0, 0
            
            # Get bonus amounts from config
            bonus_config = config['modules']['economy']['quests'].get('daily_completion_bonus', {})
            bonus = bonus_config.get('currency', 300)
            xp_bonus = bonus_config.get('xp', 500)
            
            # Grant currency bonus
            stat_period = datetime.now(timezone.utc).strftime('%Y-%m')
            await db_helpers.add_balance(user_id, display_name, bonus, config, stat_period)
            
            # Grant XP bonus
            if xp_bonus > 0:
                try:
                    await db_helpers.add_xp(user_id, display_name, xp_bonus, config, stat_period)
                except Exception as e:
                    logger.error(f"Error awarding daily completion XP bonus: {e}", exc_info=True)
            
            # Mark as claimed
            cursor.execute(
                """
                INSERT INTO daily_quest_completions (user_id, completion_date, bonus_claimed)
                VALUES (%s, %s, TRUE)
                ON DUPLICATE KEY UPDATE bonus_claimed = TRUE
                """,
                (user_id, today)
            )
            
            cnx.commit()
            logger.info(f"Granted daily completion bonus of {bonus} + {xp_bonus} XP to user {user_id}")
            return True, bonus, xp_bonus
        finally:
            cursor.close()
            cnx.close()
            
    except Exception as e:
        logger.error(f"Error granting completion bonus: {e}", exc_info=True)
        return False, 0, 0


# ============================================================================
# Monthly Quest Tracking
# ============================================================================

async def get_monthly_completion_count(db_helpers, user_id: int):
    """
    Gets the number of days this month where all quests were completed.
    
    Args:
        db_helpers: Database helpers module
        user_id: Discord user ID
    
    Returns:
        (completion_days, total_days_in_month) tuple
    """
    try:
        now = datetime.now(timezone.utc)
        first_day = now.replace(day=1)
        
        # Calculate last day of current month
        if now.month == 12:
            last_day = now.replace(year=now.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            last_day = now.replace(month=now.month + 1, day=1) - timedelta(days=1)
        
        if not db_helpers.db_pool:
            logger.warning("Database pool not available in get_monthly_completion_count")
            return 0, 0
            
        cnx = db_helpers.db_pool.get_connection()
        if not cnx:
            logger.warning("Could not get DB connection in get_monthly_completion_count")
            return 0, 0
            
        cursor = cnx.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT COUNT(DISTINCT completion_date) as completion_days
                FROM daily_quest_completions
                WHERE user_id = %s 
                AND completion_date >= %s 
                AND completion_date <= %s
                AND bonus_claimed = TRUE
                """,
                (user_id, first_day.date(), last_day.date())
            )
            result = cursor.fetchone()
            
            completion_days = result['completion_days'] or 0
            total_days = last_day.day
            
            return completion_days, total_days
        finally:
            cursor.close()
            cnx.close()
            
    except Exception as e:
        logger.error(f"Error getting monthly completion count: {e}", exc_info=True)
        return 0, 0


async def grant_monthly_milestone_reward(db_helpers, user_id: int, display_name: str, completion_days: int, config: dict):
    """
    Grants milestone rewards for completing quests multiple days in a month.
    
    Milestones:
    - 7 days: 1000 coins
    - 14 days: 2500 coins
    - 21 days: 5000 coins
    - 30 days: 10000 coins + special reward
    
    Args:
        db_helpers: Database helpers module
        user_id: Discord user ID
        display_name: User's display name
        completion_days: Number of days completed this month
        config: Bot configuration
    
    Returns:
        (milestone_reached, reward_amount, milestone_name) tuple
    """
    milestones = {
        7: (1000, "Weekly Warrior"),
        14: (2500, "Fortnight Champion"),
        21: (5000, "Three-Week Legend"),
        30: (10000, "Monthly Master")
    }
    
    try:
        now = datetime.now(timezone.utc)
        month_key = now.strftime('%Y-%m')
        
        if not db_helpers.db_pool:
            logger.warning("Database pool not available in grant_monthly_milestone_reward")
            return False, 0, None
            
        cnx = db_helpers.db_pool.get_connection()
        if not cnx:
            logger.warning("Could not get DB connection in grant_monthly_milestone_reward")
            return False, 0, None
            
        cursor = cnx.cursor(dictionary=True)
        try:
            # Check which milestones have been claimed this month
            cursor.execute(
                """
                SELECT milestone_day FROM monthly_milestones
                WHERE user_id = %s AND month_key = %s
                """,
                (user_id, month_key)
            )
            claimed_milestones = {row['milestone_day'] for row in cursor.fetchall()}
            
            # Find the highest unclaimed milestone
            for days, (reward, name) in sorted(milestones.items(), reverse=True):
                if completion_days >= days and days not in claimed_milestones:
                    # Grant reward
                    stat_period = month_key
                    await db_helpers.add_balance(user_id, display_name, reward, config, stat_period)
                    
                    # Mark milestone as claimed
                    cursor.execute(
                        """
                        INSERT INTO monthly_milestones (user_id, month_key, milestone_day, reward_amount)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (user_id, month_key, days, reward)
                    )
                    
                    cnx.commit()
                    logger.info(f"Granted {name} milestone ({days} days) reward of {reward} to user {user_id}")
                    return True, reward, name
            
            return False, 0, None
        finally:
            cursor.close()
            cnx.close()
            
    except Exception as e:
        logger.error(f"Error granting monthly milestone: {e}", exc_info=True)
        return False, 0, None


# ============================================================================
# Quest UI Helpers
# ============================================================================

def create_quests_embed(quests: list, user_name: str, config: dict):
    """Creates a Discord embed showing daily quests."""
    # Count completed quests
    completed_count = sum(1 for q in quests if q.get('completed', False))
    total_count = len(quests)
    
    # Determine color based on progress
    if completed_count == total_count:
        embed_color = discord.Color.gold()
    elif completed_count > 0:
        embed_color = discord.Color.blue()
    else:
        embed_color = discord.Color.greyple()
    
    embed = discord.Embed(
        title=f"📋 Tägliche Quests - {user_name}",
        description=f"**Fortschritt:** {completed_count}/{total_count} Quests abgeschlossen\n✨ Schließe alle Quests ab für einen Bonus!",
        color=embed_color
    )
    
    quest_icons = {
        'messages': '💬',
        'vc_minutes': '🎤',
        'reactions': '👍',
        'game_minutes': '🎮',
        'daily_media': '📸',
        'daily_word_find': '📝',
        'daily_word_attempt': '🔤',
        'check_news': '📰',
        'check_portfolio': '📈',
        'watch_horses': '🐎'
    }
    
    quest_names = {
        'messages': 'Nachrichten senden',
        'vc_minutes': 'Voice Chat',
        'reactions': 'Reaktionen geben',
        'game_minutes': 'Spiele spielen',
        'daily_media': 'Medien teilen',
        'daily_word_find': 'Das tägliche Wort finden',
        'daily_word_attempt': 'Tägliches Wort versuchen',
        'check_news': 'Nachrichten prüfen',
        'check_portfolio': 'Portfolio prüfen',
        'watch_horses': 'Pferderennen ansehen'
    }
    
    for i, quest in enumerate(quests, 1):
        quest_type = quest['quest_type']
        icon = quest_icons.get(quest_type, '❓')
        name = quest_names.get(quest_type, quest_type)
        
        progress = quest['current_progress']
        target = quest['target_value']
        completed = quest['completed']
        claimed = quest.get('reward_claimed', False)
        
        # Progress bar with better visualization
        percentage = min(100, int((progress / target) * 100))
        bar_length = 12
        filled = int((percentage / 100) * bar_length)
        bar = '█' * filled + '░' * (bar_length - filled)
        
        # Status with emojis
        if claimed:
            status_emoji = "✅"
            status_text = "Belohnung abgeholt"
        elif completed:
            status_emoji = "🎉"
            status_text = "Abgeschlossen!"
        elif percentage >= 75:
            status_emoji = "🔥"
            status_text = f"{bar} {percentage}%"
        elif percentage >= 50:
            status_emoji = "⚡"
            status_text = f"{bar} {percentage}%"
        else:
            status_emoji = "📊"
            status_text = f"{bar} {percentage}%"
        
        currency = config['modules']['economy']['currency_symbol']
        reward = quest.get('reward', 0)
        xp_reward = quest.get('xp_reward', 0)
        
        reward_text = f"{reward} {currency}"
        if xp_reward > 0:
            reward_text += f" + ⭐ {xp_reward} XP"
        
        quest_value = f"**Fortschritt:** {progress}/{target}\n"
        quest_value += f"{status_emoji} **Status:** {status_text}\n"
        quest_value += f"🎁 **Belohnung:** {reward_text}"
        
        embed.add_field(
            name=f"{icon} **{name}**",
            value=quest_value,
            inline=False
        )
    
    # Add bonus info at the bottom
    bonus_config = config['modules']['economy']['quests'].get('daily_completion_bonus', {})
    bonus_currency = bonus_config.get('currency', 300)
    bonus_xp = bonus_config.get('xp', 500)
    
    if completed_count == total_count:
        embed.add_field(
            name="🎊 Tagesbonus verfügbar!",
            value=f"Alle Quests abgeschlossen! Hole dir **{bonus_currency} {currency} + ⭐ {bonus_xp} XP**!",
            inline=False
        )
    else:
        embed.add_field(
            name="💎 Tagesbonus",
            value=f"Schließe alle Quests ab: **{bonus_currency} {currency} + ⭐ {bonus_xp} XP**",
            inline=False
        )
    
    return embed


def create_monthly_progress_embed(completion_days: int, total_days: int, user_name: str, config: dict):
    """Creates an embed showing monthly quest progress."""
    # Determine color based on progress
    percentage = int((completion_days / total_days) * 100) if total_days > 0 else 0
    
    if percentage >= 80:
        embed_color = discord.Color.gold()
    elif percentage >= 50:
        embed_color = discord.Color.blue()
    else:
        embed_color = discord.Color.greyple()
    
    embed = discord.Embed(
        title=f"📅 Monatlicher Quest-Fortschritt - {user_name}",
        description=f"**{completion_days}/{total_days} Tage** mit allen Quests abgeschlossen",
        color=embed_color
    )
    
    # Progress bar with better visualization
    bar_length = 20
    filled = int((percentage / 100) * bar_length)
    bar = '█' * filled + '░' * (bar_length - filled)
    
    progress_text = f"{bar}\n**{percentage}%** Monatsfortschritt"
    
    embed.add_field(
        name="📊 Fortschritt",
        value=progress_text,
        inline=False
    )
    
    # Milestones with enhanced display
    milestones = [
        (7, "1000", "Wöchentlicher Krieger", "🥉"),
        (14, "2500", "Zweiwöchiger Champion", "🥈"),
        (21, "5000", "Dreiwöchige Legende", "🥇"),
        (30, "10000", "Monatlicher Meister", "👑")
    ]
    
    currency = config['modules']['economy']['currency_symbol']
    
    milestones_text = ""
    for days, reward, name, medal in milestones:
        if completion_days >= days:
            status = "✅"
            style = "**"
        elif completion_days >= days - 3:
            status = "🔥"  # Close to milestone
            style = "*"
        else:
            status = "🔒"
            style = ""
        
        milestones_text += f"{status} {style}{medal} {days} Tage{style} - {name}\n"
        milestones_text += f"   💰 Belohnung: {reward} {currency}\n"
    
    embed.add_field(
        name="🏆 Meilensteine",
        value=milestones_text,
        inline=False
    )
    
    # Add motivational message
    if percentage >= 90:
        embed.set_footer(text="🌟 Unglaublich! Du bist fast jeden Tag dabei!")
    elif percentage >= 70:
        embed.set_footer(text="🔥 Großartig! Du bleibst konsequent dran!")
    elif percentage >= 50:
        embed.set_footer(text="💪 Gut gemacht! Du machst gute Fortschritte!")
    elif percentage >= 25:
        embed.set_footer(text="⭐ Weiter so! Jeder Tag zählt!")
    else:
        embed.set_footer(text="🎯 Fang an Quests zu erledigen für tolle Belohnungen!")
    
    return embed
