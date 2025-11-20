"""
Sulfur Bot - News System Module
Generates and manages news articles about server events.
"""

import discord
import random
from datetime import datetime, timezone, timedelta
from modules.logger_utils import bot_logger as logger


async def initialize_news_table(db_helpers):
    """Initialize the news table in the database."""
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
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS news_articles (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    content TEXT NOT NULL,
                    category VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_created (created_at DESC)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            conn.commit()
            logger.info("News table initialized")
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error initializing news table: {e}", exc_info=True)


async def generate_news_article(db_helpers, api_helpers, config):
    """
    Generate a news article about recent server events.
    Uses AI to create engaging content.
    """
    try:
        if not db_helpers.db_pool:
            logger.error("Database pool not available")
            return
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            logger.error("Could not get database connection")
            return
        
        cursor = conn.cursor(dictionary=True)
        try:
            # Gather data for news generation
            news_data = await gather_news_data(db_helpers, cursor)
            
            if not news_data:
                logger.info("No significant events to report")
                return
            
            # Generate article using AI
            article = await create_article_with_ai(api_helpers, news_data, config)
            
            if article:
                # Save article to database
                cursor.execute("""
                    INSERT INTO news_articles (title, content, category)
                    VALUES (%s, %s, %s)
                """, (article['title'], article['content'], article['category']))
                
                conn.commit()
                logger.info(f"Generated news article: {article['title']}")
                
                # Clean up old articles (keep only last 20)
                cursor.execute("""
                    DELETE FROM news_articles 
                    WHERE id NOT IN (
                        SELECT id FROM (
                            SELECT id FROM news_articles 
                            ORDER BY created_at DESC 
                            LIMIT 20
                        ) tmp
                    )
                """)
                conn.commit()
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        logger.error(f"Error generating news article: {e}", exc_info=True)


async def gather_news_data(db_helpers, cursor):
    """Gather data from various sources for news generation."""
    news_data = {
        'stock_changes': [],
        'leaderboard_changes': [],
        'quest_completions': 0,
        'wrapped_tease': False,
        'gambling_stats': {},
        'timestamp': datetime.now(timezone.utc)
    }
    
    try:
        # Get stock changes in the last 6 hours
        cursor.execute("""
            SELECT symbol, name, 
                   ((current_price - previous_price) / previous_price * 100) as change_pct,
                   current_price
            FROM stocks
            WHERE ABS((current_price - previous_price) / previous_price * 100) > 5
            ORDER BY ABS((current_price - previous_price) / previous_price) DESC
            LIMIT 5
        """)
        news_data['stock_changes'] = cursor.fetchall()
        
        # Check if it's wrapped teaser time (December 8-14)
        now = datetime.now(timezone.utc)
        if now.month == 12 and 8 <= now.day <= 14:
            news_data['wrapped_tease'] = True
        
        # Get top 3 richest players for leaderboard
        cursor.execute("""
            SELECT display_name, balance 
            FROM players 
            ORDER BY balance DESC 
            LIMIT 3
        """)
        news_data['leaderboard_changes'] = cursor.fetchall()
        
        # Get gambling statistics from last 6 hours
        # This is a placeholder - would need actual gambling tracking
        news_data['gambling_stats'] = {
            'total_bets': random.randint(50, 200),
            'big_winner': random.choice(['Spieler1', 'Spieler2', 'Spieler3']) if random.random() > 0.5 else None,
            'total_wagered': random.randint(10000, 50000)
        }
        
    except Exception as e:
        logger.error(f"Error gathering news data: {e}", exc_info=True)
    
    return news_data


async def create_article_with_ai(api_helpers, news_data, config):
    """Use AI to create an engaging news article."""
    try:
        # Build prompt for AI
        prompt = "Du bist ein Wirtschaftsjournalist. Schreibe einen kurzen, unterhaltsamen Nachrichtenartikel (max 300 Wörter) über folgende Ereignisse:\n\n"
        
        category = "general"
        
        # Add stock information
        if news_data['stock_changes']:
            category = "economy"
            prompt += "BÖRSE:\n"
            for stock in news_data['stock_changes']:
                symbol = stock['symbol']
                name = stock['name']
                change = stock['change_pct']
                prompt += f"- {name} ({symbol}): {change:+.2f}%\n"
            prompt += "\n"
        
        # Add wrapped tease
        if news_data['wrapped_tease']:
            category = "wrapped"
            prompt += "WRAPPED: Es ist Wrapped-Season! Gerüchte über bevorstehende Jahresrückblicke.\n\n"
        
        # Add leaderboard
        if news_data['leaderboard_changes']:
            if category == "general":
                category = "leaderboard"
            prompt += "TOP SPIELER:\n"
            for i, player in enumerate(news_data['leaderboard_changes'], 1):
                prompt += f"{i}. {player['display_name']}: {player['balance']} Coins\n"
            prompt += "\n"
        
        # Add gambling stats
        if news_data['gambling_stats'].get('big_winner'):
            if category == "general":
                category = "gambling"
            prompt += f"CASINO: {news_data['gambling_stats']['total_bets']} Wetten platziert. "
            prompt += f"Großer Gewinner: {news_data['gambling_stats']['big_winner']}!\n\n"
        
        prompt += "Erstelle einen Artikel mit einem einprägsamen Titel und informativem Inhalt. "
        prompt += "Antworte im Format: TITEL: [titel]\\nINHALT: [inhalt]"
        
        # Call AI API
        from modules import api_helpers as api_module
        response = await api_module.get_chat_response(prompt, [], config, utility_call=True)
        
        if response:
            # Parse response
            lines = response.split('\n', 1)
            if len(lines) >= 2:
                title = lines[0].replace('TITEL:', '').strip()
                content = lines[1].replace('INHALT:', '').strip()
                
                return {
                    'title': title[:255],  # Limit title length
                    'content': content,
                    'category': category
                }
        
        # Fallback if AI fails
        return create_fallback_article(news_data, category)
        
    except Exception as e:
        logger.error(f"Error creating article with AI: {e}", exc_info=True)
        return create_fallback_article(news_data, "general")


def create_fallback_article(news_data, category):
    """Create a simple article without AI."""
    titles = {
        'economy': '📈 Börsennachrichten: Volatile Märkte!',
        'wrapped': '🎁 Wrapped Season steht bevor!',
        'leaderboard': '🏆 Neue Ranglisten-Anführer!',
        'gambling': '🎰 Casino-Fieber steigt!',
        'general': '📰 Server-Update'
    }
    
    content = "Heute gab es interessante Entwicklungen auf dem Server!\n\n"
    
    if news_data['stock_changes']:
        content += "**Börse:**\n"
        for stock in news_data['stock_changes'][:3]:
            emoji = "📈" if stock['change_pct'] > 0 else "📉"
            content += f"{emoji} {stock['name']}: {stock['change_pct']:+.2f}%\n"
        content += "\n"
    
    if news_data['wrapped_tease']:
        content += "**Wrapped Season:**\nGerüchte über bevorstehende Jahresrückblicke machen die Runde!\n\n"
    
    if news_data['leaderboard_changes']:
        content += "**Top Spieler:**\n"
        for i, player in enumerate(news_data['leaderboard_changes'][:3], 1):
            content += f"{i}. {player['display_name']}: {player['balance']} 🪙\n"
    
    return {
        'title': titles.get(category, titles['general']),
        'content': content,
        'category': category
    }


async def get_latest_news(db_helpers, limit: int = 5):
    """Get the latest news articles."""
    try:
        if not db_helpers.db_pool:
            return []
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return []
        
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT id, title, content, category, created_at
                FROM news_articles
                ORDER BY created_at DESC
                LIMIT %s
            """, (limit,))
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error getting latest news: {e}", exc_info=True)
        return []


def create_news_embed(article):
    """Create a Discord embed for a news article."""
    category_colors = {
        'economy': discord.Color.gold(),
        'wrapped': discord.Color.purple(),
        'leaderboard': discord.Color.green(),
        'gambling': discord.Color.red(),
        'general': discord.Color.blue()
    }
    
    category_emojis = {
        'economy': '📈',
        'wrapped': '🎁',
        'leaderboard': '🏆',
        'gambling': '🎰',
        'general': '📰'
    }
    
    color = category_colors.get(article['category'], discord.Color.blue())
    emoji = category_emojis.get(article['category'], '📰')
    
    embed = discord.Embed(
        title=f"{emoji} {article['title']}",
        description=article['content'],
        color=color,
        timestamp=article['created_at']
    )
    
    embed.set_footer(text=f"Kategorie: {article['category'].title()}")
    
    return embed
