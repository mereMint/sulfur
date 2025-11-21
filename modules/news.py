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
        'stock_trading_activity': {},
        'market_sentiment': {},
        'timestamp': datetime.now(timezone.utc)
    }
    
    try:
        # Get stock changes in the last 6 hours
        cursor.execute("""
            SELECT symbol, name, 
                   ((current_price - previous_price) / previous_price * 100) as change_pct,
                   current_price, previous_price, volume_today, category
            FROM stocks
            WHERE ABS((current_price - previous_price) / previous_price * 100) > 3
            ORDER BY ABS((current_price - previous_price) / previous_price) DESC
            LIMIT 8
        """)
        news_data['stock_changes'] = cursor.fetchall()
        
        # Get stock trading activity from last 24 hours
        cursor.execute("""
            SELECT COUNT(*) as trades, SUM(ABS(amount)) as volume
            FROM transaction_history
            WHERE transaction_type IN ('stock_buy', 'stock_sell')
            AND created_at > DATE_SUB(NOW(), INTERVAL 24 HOUR)
        """)
        activity = cursor.fetchone()
        if activity:
            news_data['stock_trading_activity'] = {
                'trades': activity['trades'] or 0,
                'volume': float(activity['volume'] or 0)
            }
        
        # Get market sentiment (ratio of buys vs sells)
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN transaction_type = 'stock_buy' THEN 1 ELSE 0 END) as buys,
                SUM(CASE WHEN transaction_type = 'stock_sell' THEN 1 ELSE 0 END) as sells
            FROM transaction_history
            WHERE transaction_type IN ('stock_buy', 'stock_sell')
            AND created_at > DATE_SUB(NOW(), INTERVAL 6 HOUR)
        """)
        sentiment = cursor.fetchone()
        if sentiment and (sentiment['buys'] or 0) + (sentiment['sells'] or 0) > 0:
            total = (sentiment['buys'] or 0) + (sentiment['sells'] or 0)
            buy_ratio = (sentiment['buys'] or 0) / total if total > 0 else 0.5
            news_data['market_sentiment'] = {
                'buys': sentiment['buys'] or 0,
                'sells': sentiment['sells'] or 0,
                'buy_ratio': buy_ratio
            }
        
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
        
        # Get gambling statistics from last 24 hours (real data)
        cursor.execute("""
            SELECT 
                COUNT(*) as total_games,
                SUM(total_wagered) as total_wagered,
                SUM(total_won) as total_won
            FROM gambling_stats
            WHERE last_played > DATE_SUB(NOW(), INTERVAL 24 HOUR)
        """)
        gambling_data = cursor.fetchone()
        
        # Get biggest winner from last 24 hours
        cursor.execute("""
            SELECT gs.user_id, p.display_name, gs.biggest_win
            FROM gambling_stats gs
            LEFT JOIN players p ON gs.user_id = p.user_id
            WHERE gs.last_played > DATE_SUB(NOW(), INTERVAL 24 HOUR)
            AND gs.biggest_win IS NOT NULL
            ORDER BY gs.biggest_win DESC
            LIMIT 1
        """)
        winner_data = cursor.fetchone()
        
        news_data['gambling_stats'] = {
            'total_bets': gambling_data['total_games'] or 0 if gambling_data else 0,
            'big_winner': winner_data['display_name'] if winner_data and winner_data.get('display_name') else None,
            'biggest_win': winner_data['biggest_win'] if winner_data and winner_data.get('biggest_win') else 0,
            'total_wagered': int(gambling_data['total_wagered'] or 0) if gambling_data else 0,
            'total_won': int(gambling_data['total_won'] or 0) if gambling_data else 0
        }
        
    except Exception as e:
        logger.error(f"Error gathering news data: {e}", exc_info=True)
    
    return news_data


async def create_article_with_ai(api_helpers, news_data, config):
    """Use AI to create an engaging news article with context-aware headline."""
    try:
        # Build prompt for AI with emphasis on generating contextual headlines
        prompt = """Du bist ein charismatischer Wirtschaftsjournalist mit einem Hang zu dramatischen Geschichten. 
Schreibe einen unterhaltsamen, spannenden Nachrichtenartikel (200-400 Wörter) über die folgenden Ereignisse.
Verwende lebendige Metaphern, dramatische Formulierungen und mache die Zahlen lebendig!

WICHTIG: Der TITEL muss die wichtigste Entwicklung widerspiegeln (z.B. bei großen Börsen-Verlusten: "Gambling Industries Reports huge decline on Players, Company Reports a -14% recession")

Format: TITEL: [einprägsamer, kontextbasierter titel]\nINHALT: [artikel inhalt]

EREIGNISSE:\n\n"""
        
        category = "general"
        
        # Add stock information with more detail
        if news_data['stock_changes']:
            category = "economy"
            prompt += "📊 BÖRSENGESCHEHEN:\n"
            for stock in news_data['stock_changes']:
                symbol = stock['symbol']
                name = stock['name']
                change = stock['change_pct']
                current = stock['current_price']
                previous = stock['previous_price']
                volume = stock['volume_today']
                cat = stock['category']
                
                trend = "explodiert" if change > 10 else "steigt rasant" if change > 5 else "wächst" if change > 0 else "fällt" if change > -5 else "stürzt ab" if change > -10 else "kollabiert"
                prompt += f"- {name} ({symbol}, {cat}): {trend} um {abs(change):.2f}% (von {previous:.2f} auf {current:.2f}), Volumen: {volume}\n"
            prompt += "\n"
        
        # Add market sentiment and activity
        if news_data.get('stock_trading_activity', {}).get('trades', 0) > 0:
            trades = news_data['stock_trading_activity']['trades']
            volume = news_data['stock_trading_activity']['volume']
            prompt += f"💹 HANDELSAKTIVITÄT: {trades} Transaktionen im Wert von {volume:.0f} Coins in den letzten 24 Stunden.\n\n"
        
        if news_data.get('market_sentiment'):
            sentiment = news_data['market_sentiment']
            buy_ratio = sentiment['buy_ratio']
            mood = "bullish (sehr optimistisch)" if buy_ratio > 0.65 else "bearish (pessimistisch)" if buy_ratio < 0.35 else "neutral"
            prompt += f"📈 MARKTSTIMMUNG: {mood} - {sentiment['buys']} Käufe vs {sentiment['sells']} Verkäufe\n\n"
        
        # Add wrapped tease
        if news_data['wrapped_tease']:
            category = "wrapped"
            prompt += "🎁 WRAPPED SEASON: Die Jahresrückblicke stehen vor der Tür! Spekulationen über spektakuläre Statistiken.\n\n"
        
        # Add leaderboard
        if news_data['leaderboard_changes']:
            if category == "general":
                category = "leaderboard"
            prompt += "🏆 REICHSTEN SPIELER:\n"
            for i, player in enumerate(news_data['leaderboard_changes'], 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
                prompt += f"{medal} {player['display_name']}: {player['balance']:,} Coins\n"
            prompt += "\n"
        
        # Add gambling stats with improved context
        gambling_stats = news_data['gambling_stats']
        if gambling_stats.get('total_bets', 0) > 0:
            if category == "general":
                category = "gambling"
            
            # Calculate net profit/loss for context
            net_change = gambling_stats.get('total_won', 0) - gambling_stats.get('total_wagered', 0)
            change_pct = (net_change / gambling_stats['total_wagered'] * 100) if gambling_stats.get('total_wagered', 0) > 0 else 0
            
            prompt += f"🎰 CASINO (letzte 24h):\n"
            prompt += f"- Spiele gespielt: {gambling_stats['total_bets']}\n"
            prompt += f"- Gesamteinsatz: {gambling_stats['total_wagered']:,} Coins\n"
            prompt += f"- Gesamt ausgezahlt: {gambling_stats.get('total_won', 0):,} Coins\n"
            prompt += f"- Spieler-Bilanz: {change_pct:+.1f}% ({'Gewinn' if net_change > 0 else 'Verlust'})\n"
            
            if gambling_stats.get('big_winner'):
                prompt += f"- Größter Gewinner: {gambling_stats['big_winner']} ({gambling_stats.get('biggest_win', 0):,} Coins)\n"
            prompt += "\n"
        
        prompt += "\nSchreibe einen packenden Artikel mit einem kreativen Titel und dramatischem, aber informativem Inhalt!"
        
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
        'economy': '📈 Börsennachrichten: Volatile Märkte bewegen die Gemüter!',
        'wrapped': '🎁 Wrapped Season steht bevor!',
        'leaderboard': '🏆 Neue Ranglisten-Anführer erobern die Spitze!',
        'gambling': '🎰 Casino-Fieber erreicht neue Höhen!',
        'general': '📰 Server-Update: Spannende Entwicklungen!'
    }
    
    content = "**Heute gab es interessante Entwicklungen auf dem Server!**\n\n"
    
    # Enhanced stock information
    if news_data['stock_changes']:
        content += "**📊 Börsengeschehen:**\n"
        for stock in news_data['stock_changes'][:5]:
            emoji = "🚀" if stock['change_pct'] > 5 else "📈" if stock['change_pct'] > 0 else "📉" if stock['change_pct'] > -5 else "💥"
            content += f"{emoji} **{stock['name']}** ({stock['symbol']}): {stock['change_pct']:+.2f}%\n"
            content += f"   {stock['previous_price']:.2f} → {stock['current_price']:.2f} | Vol: {stock['volume_today']}\n"
        content += "\n"
    
    # Market activity
    if news_data.get('stock_trading_activity', {}).get('trades', 0) > 0:
        trades = news_data['stock_trading_activity']['trades']
        volume = news_data['stock_trading_activity']['volume']
        content += f"**💹 Handelsaktivität:** {trades} Trades, Volumen: {volume:.0f} 🪙\n\n"
    
    # Market sentiment
    if news_data.get('market_sentiment'):
        sentiment = news_data['market_sentiment']
        buy_ratio = sentiment['buy_ratio']
        mood_emoji = "🟢" if buy_ratio > 0.6 else "🔴" if buy_ratio < 0.4 else "🟡"
        mood_text = "Bullish" if buy_ratio > 0.6 else "Bearish" if buy_ratio < 0.4 else "Neutral"
        content += f"**📈 Marktstimmung:** {mood_emoji} {mood_text} ({sentiment['buys']} Käufe / {sentiment['sells']} Verkäufe)\n\n"
    
    if news_data['wrapped_tease']:
        content += "**🎁 Wrapped Season:**\nGerüchte über bevorstehende Jahresrückblicke machen die Runde! Bereitet euch auf spektakuläre Statistiken vor!\n\n"
    
    if news_data['leaderboard_changes']:
        content += "**🏆 Top Spieler:**\n"
        medals = ["🥇", "🥈", "🥉"]
        for i, player in enumerate(news_data['leaderboard_changes'][:3], 0):
            medal = medals[i] if i < 3 else f"{i+1}."
            content += f"{medal} **{player['display_name']}**: {player['balance']:,} 🪙\n"
        content += "\n"
    
    gambling_stats = news_data['gambling_stats']
    if gambling_stats.get('total_bets', 0) > 0:
        content += f"**🎰 Casino (24h):** {gambling_stats['total_bets']} Spiele\n"
        
        net_change = gambling_stats.get('total_won', 0) - gambling_stats.get('total_wagered', 0)
        if net_change != 0:
            change_pct = (net_change / gambling_stats['total_wagered'] * 100) if gambling_stats.get('total_wagered', 0) > 0 else 0
            emoji = "📈" if net_change > 0 else "📉"
            content += f"{emoji} Spieler-Bilanz: {change_pct:+.1f}%\n"
        
        if gambling_stats.get('big_winner'):
            content += f"🏆 Größter Gewinner: **{gambling_stats['big_winner']}** ({gambling_stats.get('biggest_win', 0):,} 🪙) 🎉\n"
        content += "\n"
    
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


class NewsPaginationView(discord.ui.View):
    """Pagination view for news articles with max 5 articles."""
    
    def __init__(self, articles: list, user_id: int):
        super().__init__(timeout=300)
        self.articles = articles[:5]  # Limit to max 5 articles
        self.user_id = user_id
        self.current_page = 0
        self._update_buttons()
    
    def _update_buttons(self):
        """Update button states based on current page."""
        # Disable previous button if on first page
        self.previous_button.disabled = (self.current_page == 0)
        # Disable next button if on last page
        self.next_button.disabled = (self.current_page >= len(self.articles) - 1)
    
    def get_current_embed(self):
        """Get the embed for the current page."""
        article = self.articles[self.current_page]
        embed = create_news_embed(article)
        embed.set_footer(text=f"Artikel {self.current_page + 1}/{len(self.articles)} • {article['category'].title()}")
        return embed
    
    @discord.ui.button(label="◀️ Zurück", style=discord.ButtonStyle.secondary, custom_id="news_prev")
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to previous article."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Das ist nicht deine Ansicht!", ephemeral=True)
            return
        
        # Defer for faster response
        await interaction.response.defer()
        
        self.current_page = max(0, self.current_page - 1)
        self._update_buttons()
        await interaction.edit_original_response(embed=self.get_current_embed(), view=self)
    
    @discord.ui.button(label="Weiter ▶️", style=discord.ButtonStyle.secondary, custom_id="news_next")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to next article."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Das ist nicht deine Ansicht!", ephemeral=True)
            return
        
        # Defer for faster response
        await interaction.response.defer()
        
        self.current_page = min(len(self.articles) - 1, self.current_page + 1)
        self._update_buttons()
        await interaction.edit_original_response(embed=self.get_current_embed(), view=self)

