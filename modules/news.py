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


async def generate_news_article(db_helpers, api_helpers, config, gemini_key=None, openai_key=None):
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
            article = await create_article_with_ai(api_helpers, news_data, config, gemini_key, openai_key)
            
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
            LEFT JOIN players p ON gs.user_id = p.discord_id
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


async def create_article_with_ai(api_helpers, news_data, config, gemini_key=None, openai_key=None):
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
        
        # Call AI API with proper parameters
        # get_chat_response(history, user_prompt, user_display_name, system_prompt, config, gemini_key, openai_key)
        system_prompt = "Du bist ein professioneller Nachrichtenjournalist."
        response, error_message, _ = await api_helpers.get_chat_response(
            [], prompt, "News System", system_prompt, config, gemini_key, openai_key
        )
        
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
        'sports': discord.Color.from_rgb(30, 60, 90),
        'general': discord.Color.blue()
    }
    
    category_emojis = {
        'economy': '📈',
        'wrapped': '🎁',
        'leaderboard': '🏆',
        'gambling': '🎰',
        'sports': '🏆',
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


# ============================================================================
# SPORTS NEWS SYSTEM
# ============================================================================

# Discord embed character limits
EMBED_TITLE_LIMIT = 256
EMBED_DESCRIPTION_LIMIT = 4096
EMBED_FIELD_NAME_LIMIT = 256
EMBED_FIELD_VALUE_LIMIT = 1024
EMBED_TOTAL_LIMIT = 6000


def truncate_text(text: str, limit: int, suffix: str = "...") -> str:
    """Truncate text to fit within a character limit."""
    if len(text) <= limit:
        return text
    return text[:limit - len(suffix)] + suffix


async def gather_sports_news_data(db_helpers, cursor) -> dict:
    """Gather sports data for news generation."""
    sports_data = {
        'football': {
            'recent_matches': [],
            'upcoming_matches': [],
            'top_scorers': [],
            'league_table': [],
            'betting_activity': {}
        },
        'f1': {
            'recent_races': [],
            'upcoming_races': [],
            'standings': [],
            'key_moments': []
        },
        'motogp': {
            'recent_races': [],
            'upcoming_races': [],
            'standings': []
        },
        'betting_highlights': {
            'biggest_wins': [],
            'active_bettors': 0,
            'total_volume': 0
        },
        'timestamp': datetime.now(timezone.utc)
    }
    
    try:
        # Get recent finished football matches (last 7 days)
        cursor.execute("""
            SELECT match_id, home_team, away_team, home_score, away_score, 
                   league_id, match_time, status
            FROM sport_matches
            WHERE status = 'finished'
              AND match_time > DATE_SUB(NOW(), INTERVAL 7 DAY)
              AND league_id IN ('bl1', 'bl2', 'dfb', 'ucl', 'uel')
            ORDER BY match_time DESC
            LIMIT 10
        """)
        sports_data['football']['recent_matches'] = cursor.fetchall()
        
        # Get upcoming football matches
        cursor.execute("""
            SELECT match_id, home_team, away_team, odds_home, odds_draw, odds_away,
                   league_id, match_time
            FROM sport_matches
            WHERE status = 'scheduled'
              AND match_time > NOW()
              AND league_id IN ('bl1', 'bl2', 'dfb', 'ucl', 'uel')
            ORDER BY match_time ASC
            LIMIT 5
        """)
        sports_data['football']['upcoming_matches'] = cursor.fetchall()
        
        # Get F1 events
        cursor.execute("""
            SELECT match_id, home_team, away_team, match_time, status, league_id
            FROM sport_matches
            WHERE league_id = 'f1'
              AND match_time > DATE_SUB(NOW(), INTERVAL 7 DAY)
            ORDER BY match_time DESC
            LIMIT 5
        """)
        sports_data['f1']['recent_races'] = cursor.fetchall()
        
        # Get upcoming F1 races
        cursor.execute("""
            SELECT match_id, home_team, away_team, match_time
            FROM sport_matches
            WHERE league_id = 'f1'
              AND status = 'scheduled'
              AND match_time > NOW()
            ORDER BY match_time ASC
            LIMIT 3
        """)
        sports_data['f1']['upcoming_races'] = cursor.fetchall()
        
        # Get MotoGP events
        cursor.execute("""
            SELECT match_id, home_team, away_team, match_time, status
            FROM sport_matches
            WHERE league_id = 'motogp'
              AND match_time > DATE_SUB(NOW(), INTERVAL 7 DAY)
            ORDER BY match_time DESC
            LIMIT 5
        """)
        sports_data['motogp']['recent_races'] = cursor.fetchall()
        
        # Get upcoming MotoGP races
        cursor.execute("""
            SELECT match_id, home_team, away_team, match_time
            FROM sport_matches
            WHERE league_id = 'motogp'
              AND status = 'scheduled'
              AND match_time > NOW()
            ORDER BY match_time ASC
            LIMIT 3
        """)
        sports_data['motogp']['upcoming_races'] = cursor.fetchall()
        
        # Get betting highlights
        cursor.execute("""
            SELECT b.user_id, p.display_name, b.actual_payout, b.odds_at_bet,
                   m.home_team, m.away_team, m.league_id
            FROM sport_bets b
            JOIN sport_matches m ON b.match_id = m.match_id
            LEFT JOIN players p ON b.user_id = p.discord_id
            WHERE b.status = 'won'
              AND b.settled_at > DATE_SUB(NOW(), INTERVAL 24 HOUR)
            ORDER BY b.actual_payout DESC
            LIMIT 5
        """)
        sports_data['betting_highlights']['biggest_wins'] = cursor.fetchall()
        
        # Get betting activity stats
        cursor.execute("""
            SELECT COUNT(DISTINCT user_id) as active_bettors,
                   COUNT(*) as total_bets,
                   SUM(bet_amount) as total_volume
            FROM sport_bets
            WHERE created_at > DATE_SUB(NOW(), INTERVAL 24 HOUR)
        """)
        activity = cursor.fetchone()
        if activity:
            sports_data['betting_highlights']['active_bettors'] = activity['active_bettors'] or 0
            sports_data['betting_highlights']['total_volume'] = activity['total_volume'] or 0
        
    except Exception as e:
        logger.error(f"Error gathering sports news data: {e}", exc_info=True)
    
    return sports_data


async def generate_sports_news(db_helpers, api_helpers, config, gemini_key=None, openai_key=None):
    """Generate a sports-focused news article."""
    try:
        if not db_helpers.db_pool:
            return None
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return None
        
        cursor = conn.cursor(dictionary=True)
        try:
            sports_data = await gather_sports_news_data(db_helpers, cursor)
            
            # Check if we have any sports data to report
            has_data = (
                sports_data['football']['recent_matches'] or
                sports_data['football']['upcoming_matches'] or
                sports_data['f1']['recent_races'] or
                sports_data['motogp']['recent_races'] or
                sports_data['betting_highlights']['biggest_wins']
            )
            
            if not has_data:
                logger.info("No sports data to report")
                return None
            
            # Generate article
            article = await create_sports_article_with_ai(
                api_helpers, sports_data, config, gemini_key, openai_key
            )
            
            if article:
                # Save to database
                cursor.execute("""
                    INSERT INTO news_articles (title, content, category)
                    VALUES (%s, %s, %s)
                """, (
                    truncate_text(article['title'], 255),
                    article['content'],
                    'sports'
                ))
                conn.commit()
                logger.info(f"Generated sports news: {article['title']}")
                return article
            
            return create_fallback_sports_article(sports_data)
            
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        logger.error(f"Error generating sports news: {e}", exc_info=True)
        return None


async def create_sports_article_with_ai(api_helpers, sports_data, config, gemini_key=None, openai_key=None):
    """Use AI to create an engaging sports news article.
    
    Note: The prompt is in German as the bot primarily serves German-speaking users.
    The prompt template could be extracted to a config file for internationalization.
    """
    try:
        # Sports journalism prompt - German language for target audience
        # TODO: Consider moving to config file for easier maintenance
        prompt = """Du bist ein begeisterter Sportjournalist mit Leidenschaft für Fußball, Formel 1 und MotoGP.
Schreibe einen packenden Sportnachrichtenartikel (250-400 Wörter) basierend auf den folgenden Daten.
Verwende sportliche Metaphern, dramatische Formulierungen und bringe Emotionen rein!

WICHTIG: 
- Der TITEL muss die wichtigste Sportnachricht widerspiegeln
- Halte dich an die Fakten, aber mache sie spannend
- Erwähne alle Sportarten, zu denen es Daten gibt

Format: TITEL: [packender titel]\nINHALT: [artikel inhalt]

SPORTDATEN:\n\n"""
        
        # Add football data
        if sports_data['football']['recent_matches']:
            prompt += "⚽ FUSSBALL - LETZTE ERGEBNISSE:\n"
            for match in sports_data['football']['recent_matches'][:5]:
                home = match['home_team']
                away = match['away_team']
                score = f"{match['home_score']}:{match['away_score']}"
                prompt += f"  • {home} {score} {away}\n"
            prompt += "\n"
        
        if sports_data['football']['upcoming_matches']:
            prompt += "⚽ FUSSBALL - NÄCHSTE SPIELE:\n"
            for match in sports_data['football']['upcoming_matches'][:3]:
                home = match['home_team']
                away = match['away_team']
                match_time = match['match_time']
                if isinstance(match_time, datetime):
                    time_str = match_time.strftime("%d.%m. %H:%M")
                else:
                    time_str = str(match_time)
                prompt += f"  • {home} vs {away} ({time_str})\n"
            prompt += "\n"
        
        # Add F1 data
        if sports_data['f1']['recent_races'] or sports_data['f1']['upcoming_races']:
            prompt += "🏎️ FORMEL 1:\n"
            for race in sports_data['f1']['recent_races'][:2]:
                session = race.get('home_team', 'Race')
                circuit = race.get('away_team', 'Unknown')
                prompt += f"  • {session} @ {circuit}\n"
            for race in sports_data['f1']['upcoming_races'][:2]:
                session = race.get('home_team', 'Race')
                circuit = race.get('away_team', 'Unknown')
                match_time = race['match_time']
                if isinstance(match_time, datetime):
                    time_str = match_time.strftime("%d.%m.")
                else:
                    time_str = str(match_time)
                prompt += f"  • KOMMEND: {session} @ {circuit} ({time_str})\n"
            prompt += "\n"
        
        # Add MotoGP data
        if sports_data['motogp']['recent_races'] or sports_data['motogp']['upcoming_races']:
            prompt += "🏍️ MOTOGP:\n"
            for race in sports_data['motogp']['recent_races'][:2]:
                session = race.get('home_team', 'Race')
                circuit = race.get('away_team', 'Unknown')
                prompt += f"  • {session} @ {circuit}\n"
            for race in sports_data['motogp']['upcoming_races'][:2]:
                session = race.get('home_team', 'Race')
                circuit = race.get('away_team', 'Unknown')
                match_time = race['match_time']
                if isinstance(match_time, datetime):
                    time_str = match_time.strftime("%d.%m.")
                else:
                    time_str = str(match_time)
                prompt += f"  • KOMMEND: {session} @ {circuit} ({time_str})\n"
            prompt += "\n"
        
        # Add betting highlights
        if sports_data['betting_highlights']['biggest_wins']:
            prompt += "💰 WETT-HIGHLIGHTS:\n"
            for win in sports_data['betting_highlights']['biggest_wins'][:3]:
                name = win.get('display_name', 'Ein Wetter')
                payout = win.get('actual_payout', 0)
                odds = win.get('odds_at_bet', 1.0)
                prompt += f"  • {name}: {payout:,} Coins gewonnen @ {odds:.2f}x\n"
            prompt += f"\n  Aktive Wetter (24h): {sports_data['betting_highlights']['active_bettors']}\n"
            prompt += f"  Wettvolumen: {sports_data['betting_highlights']['total_volume']:,} Coins\n"
        
        prompt += "\nSchreibe einen packenden Artikel!"
        
        system_prompt = "Du bist ein professioneller Sportjournalist."
        response, error_message, _ = await api_helpers.get_chat_response(
            [], prompt, "Sports News", system_prompt, config, gemini_key, openai_key
        )
        
        if response:
            lines = response.split('\n', 1)
            if len(lines) >= 2:
                title = lines[0].replace('TITEL:', '').strip()
                content = lines[1].replace('INHALT:', '').strip()
                
                return {
                    'title': truncate_text(title, EMBED_TITLE_LIMIT - 5),
                    'content': truncate_text(content, EMBED_DESCRIPTION_LIMIT - 100),
                    'category': 'sports'
                }
        
        return None
        
    except Exception as e:
        logger.error(f"Error creating sports article with AI: {e}", exc_info=True)
        return None


def create_fallback_sports_article(sports_data) -> dict:
    """Create a sports article without AI."""
    title = "🏆 Sport Update: Aktuelle Ergebnisse & Vorschau"
    content = "**Die wichtigsten Sport-News auf einen Blick!**\n\n"
    
    # Football section
    if sports_data['football']['recent_matches']:
        content += "**⚽ Fußball-Ergebnisse:**\n"
        for match in sports_data['football']['recent_matches'][:4]:
            home = truncate_text(match['home_team'], 20)
            away = truncate_text(match['away_team'], 20)
            score = f"{match['home_score']}:{match['away_score']}"
            content += f"• **{home}** {score} **{away}**\n"
        content += "\n"
    
    if sports_data['football']['upcoming_matches']:
        content += "**📅 Nächste Spiele:**\n"
        for match in sports_data['football']['upcoming_matches'][:3]:
            home = truncate_text(match['home_team'], 18)
            away = truncate_text(match['away_team'], 18)
            match_time = match['match_time']
            if isinstance(match_time, datetime):
                time_str = match_time.strftime("%d.%m. %H:%M")
            else:
                time_str = str(match_time)[:16]
            content += f"• {home} vs {away} ({time_str})\n"
        content += "\n"
    
    # F1 section
    if sports_data['f1']['upcoming_races']:
        content += "**🏎️ Formel 1:**\n"
        for race in sports_data['f1']['upcoming_races'][:2]:
            session = race.get('home_team', 'Race')
            circuit = race.get('away_team', 'Unknown')
            content += f"• {session} @ {circuit}\n"
        content += "\n"
    
    # MotoGP section
    if sports_data['motogp']['upcoming_races']:
        content += "**🏍️ MotoGP:**\n"
        for race in sports_data['motogp']['upcoming_races'][:2]:
            session = race.get('home_team', 'Race')
            circuit = race.get('away_team', 'Unknown')
            content += f"• {session} @ {circuit}\n"
        content += "\n"
    
    # Betting highlights
    if sports_data['betting_highlights']['biggest_wins']:
        content += "**💰 Top-Gewinne heute:**\n"
        for win in sports_data['betting_highlights']['biggest_wins'][:2]:
            name = win.get('display_name', 'Anonymer Wetter')
            payout = win.get('actual_payout', 0)
            content += f"🎉 **{name}**: {payout:,} Coins\n"
    
    return {
        'title': truncate_text(title, EMBED_TITLE_LIMIT - 5),
        'content': truncate_text(content, EMBED_DESCRIPTION_LIMIT - 100),
        'category': 'sports'
    }


async def get_sports_news(db_helpers, limit: int = 5) -> list:
    """Get latest sports news articles."""
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
                WHERE category = 'sports'
                ORDER BY created_at DESC
                LIMIT %s
            """, (limit,))
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error getting sports news: {e}", exc_info=True)
        return []


def create_sports_news_embed(article: dict, show_header: bool = True) -> discord.Embed:
    """Create a newspaper-style embed for sports news."""
    # Newspaper-style colors
    embed = discord.Embed(
        title=f"📰 {article['title']}" if show_header else article['title'],
        description=article['content'],
        color=discord.Color.from_rgb(30, 60, 90)  # Dark blue newspaper style
    )
    
    # Add newspaper header
    if show_header:
        embed.set_author(
            name="🏆 SULFUR SPORTS DAILY",
            icon_url=None
        )
    
    # Format timestamp nicely
    created_at = article.get('created_at')
    if created_at:
        if isinstance(created_at, datetime):
            date_str = created_at.strftime("%d. %B %Y • %H:%M")
        else:
            date_str = str(created_at)
        embed.set_footer(text=f"📅 {date_str}")
    
    return embed


def create_sports_overview_embed(sports_data: dict, user_balance: int = 0) -> discord.Embed:
    """Create a newspaper-style overview of all sports."""
    embed = discord.Embed(
        title="📰 SULFUR SPORTS DAILY",
        description="**Die wichtigsten Sportnachrichten auf einen Blick**\n━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        color=discord.Color.from_rgb(30, 60, 90)
    )
    
    # Football section
    football_text = ""
    if sports_data.get('football', {}).get('upcoming_matches'):
        for match in sports_data['football']['upcoming_matches'][:3]:
            home = truncate_text(str(match.get('home_team', 'TBD')), 15)
            away = truncate_text(str(match.get('away_team', 'TBD')), 15)
            football_text += f"⚽ {home} vs {away}\n"
    if not football_text:
        football_text = "*Keine anstehenden Spiele*"
    
    embed.add_field(
        name="⚽ Fußball",
        value=truncate_text(football_text, EMBED_FIELD_VALUE_LIMIT - 10),
        inline=True
    )
    
    # F1 section
    f1_text = ""
    if sports_data.get('f1', {}).get('upcoming_races'):
        for race in sports_data['f1']['upcoming_races'][:2]:
            session = truncate_text(str(race.get('home_team', 'Race')), 20)
            circuit = truncate_text(str(race.get('away_team', 'Circuit')), 15)
            f1_text += f"🏎️ {session}\n   @ {circuit}\n"
    if not f1_text:
        f1_text = "*Keine anstehenden Rennen*"
    
    embed.add_field(
        name="🏎️ Formel 1",
        value=truncate_text(f1_text, EMBED_FIELD_VALUE_LIMIT - 10),
        inline=True
    )
    
    # MotoGP section
    motogp_text = ""
    if sports_data.get('motogp', {}).get('upcoming_races'):
        for race in sports_data['motogp']['upcoming_races'][:2]:
            session = truncate_text(str(race.get('home_team', 'Race')), 20)
            circuit = truncate_text(str(race.get('away_team', 'Circuit')), 15)
            motogp_text += f"🏍️ {session}\n   @ {circuit}\n"
    if not motogp_text:
        motogp_text = "*Keine anstehenden Rennen*"
    
    embed.add_field(
        name="🏍️ MotoGP",
        value=truncate_text(motogp_text, EMBED_FIELD_VALUE_LIMIT - 10),
        inline=True
    )
    
    # Betting highlights
    betting_text = ""
    highlights = sports_data.get('betting_highlights', {})
    if highlights.get('biggest_wins'):
        betting_text += "**🏆 Top-Gewinne:**\n"
        for win in highlights['biggest_wins'][:2]:
            name = truncate_text(str(win.get('display_name', 'Anonym')), 12)
            payout = win.get('actual_payout', 0)
            betting_text += f"• {name}: {payout:,}🪙\n"
    
    if highlights.get('active_bettors'):
        betting_text += f"\n👥 {highlights['active_bettors']} aktive Wetter"
    
    if betting_text:
        embed.add_field(
            name="💰 Wett-Highlights",
            value=truncate_text(betting_text, EMBED_FIELD_VALUE_LIMIT - 10),
            inline=False
        )
    
    # User balance
    if user_balance > 0:
        embed.add_field(
            name="💼 Dein Guthaben",
            value=f"**{user_balance:,}** 🪙",
            inline=True
        )
    
    embed.set_footer(text="📰 Sulfur Sports Daily • Aktualisiert alle 6 Stunden")
    
    return embed


class SportsNewsPaginationView(discord.ui.View):
    """Multi-page sports news view with tabs."""
    
    def __init__(self, db_helpers, user_id: int, sports_data: dict = None, articles: list = None):
        super().__init__(timeout=300)
        self.db_helpers = db_helpers
        self.user_id = user_id
        self.sports_data = sports_data or {}
        self.articles = articles or []
        self.current_tab = "overview"  # overview, football, f1, motogp, articles
        self.current_page = 0
        self._update_buttons()
    
    def _update_buttons(self):
        """Update button states."""
        # Enable/disable based on current tab
        pass
    
    def get_current_embed(self) -> discord.Embed:
        """Get embed for current tab."""
        if self.current_tab == "overview":
            return create_sports_overview_embed(self.sports_data)
        elif self.current_tab == "articles" and self.articles:
            article = self.articles[min(self.current_page, len(self.articles) - 1)]
            embed = create_sports_news_embed(article)
            embed.set_footer(text=f"Artikel {self.current_page + 1}/{len(self.articles)}")
            return embed
        elif self.current_tab == "football":
            return self._create_football_embed()
        elif self.current_tab == "f1":
            return self._create_f1_embed()
        elif self.current_tab == "motogp":
            return self._create_motogp_embed()
        
        return create_sports_overview_embed(self.sports_data)
    
    def _create_football_embed(self) -> discord.Embed:
        """Create detailed football news embed."""
        embed = discord.Embed(
            title="⚽ Fußball News",
            description="Aktuelle Ergebnisse und anstehende Spiele",
            color=discord.Color.green()
        )
        
        football = self.sports_data.get('football', {})
        
        if football.get('recent_matches'):
            results_text = ""
            for match in football['recent_matches'][:5]:
                home = truncate_text(str(match['home_team']), 18)
                away = truncate_text(str(match['away_team']), 18)
                score = f"{match['home_score']}:{match['away_score']}"
                results_text += f"**{home}** {score} **{away}**\n"
            embed.add_field(
                name="📊 Letzte Ergebnisse",
                value=truncate_text(results_text, EMBED_FIELD_VALUE_LIMIT) or "Keine Daten",
                inline=False
            )
        
        if football.get('upcoming_matches'):
            upcoming_text = ""
            for match in football['upcoming_matches'][:5]:
                home = truncate_text(str(match['home_team']), 15)
                away = truncate_text(str(match['away_team']), 15)
                match_time = match.get('match_time')
                if isinstance(match_time, datetime):
                    time_str = match_time.strftime("%d.%m. %H:%M")
                else:
                    time_str = str(match_time)[:16]
                
                # Show odds
                odds_home = match.get('odds_home', 2.0)
                odds_away = match.get('odds_away', 3.0)
                upcoming_text += f"**{home}** vs **{away}**\n"
                upcoming_text += f"   📅 {time_str} | 📊 {odds_home:.2f} - {odds_away:.2f}\n"
            
            embed.add_field(
                name="📅 Nächste Spiele",
                value=truncate_text(upcoming_text, EMBED_FIELD_VALUE_LIMIT) or "Keine Spiele",
                inline=False
            )
        
        return embed
    
    def _create_f1_embed(self) -> discord.Embed:
        """Create detailed F1 news embed."""
        embed = discord.Embed(
            title="🏎️ Formula 1 News",
            description="Aktuelle Rennen und Sessions",
            color=discord.Color.red()
        )
        
        f1 = self.sports_data.get('f1', {})
        
        if f1.get('upcoming_races'):
            races_text = ""
            for race in f1['upcoming_races'][:5]:
                session = race.get('home_team', 'Race')
                circuit = race.get('away_team', 'Unknown')
                match_time = race.get('match_time')
                if isinstance(match_time, datetime):
                    time_str = match_time.strftime("%d.%m. %H:%M")
                else:
                    time_str = str(match_time)[:16]
                races_text += f"🏁 **{session}**\n"
                races_text += f"   📍 {circuit}\n"
                races_text += f"   📅 {time_str}\n\n"
            
            embed.add_field(
                name="🏁 Kommende Sessions",
                value=truncate_text(races_text, EMBED_FIELD_VALUE_LIMIT) or "Keine Daten",
                inline=False
            )
        
        # Add some F1 info
        embed.add_field(
            name="ℹ️ Wetten verfügbar",
            value="Wette auf Rennsieger und Podiumsplätze!\nNutze `/sportbets` zum Wetten.",
            inline=False
        )
        
        return embed
    
    def _create_motogp_embed(self) -> discord.Embed:
        """Create detailed MotoGP news embed."""
        embed = discord.Embed(
            title="🏍️ MotoGP News",
            description="Aktuelle Rennen und Grand Prix",
            color=discord.Color.orange()
        )
        
        motogp = self.sports_data.get('motogp', {})
        
        if motogp.get('upcoming_races'):
            races_text = ""
            for race in motogp['upcoming_races'][:5]:
                session = race.get('home_team', 'Race')
                circuit = race.get('away_team', 'Unknown')
                match_time = race.get('match_time')
                if isinstance(match_time, datetime):
                    time_str = match_time.strftime("%d.%m.")
                else:
                    time_str = str(match_time)[:10]
                races_text += f"🏁 **{session}**\n"
                races_text += f"   📍 {circuit}\n"
                races_text += f"   📅 {time_str}\n\n"
            
            embed.add_field(
                name="🏁 Kommende Grand Prix",
                value=truncate_text(races_text, EMBED_FIELD_VALUE_LIMIT) or "Keine Daten",
                inline=False
            )
        
        return embed
    
    @discord.ui.button(label="📰 Übersicht", style=discord.ButtonStyle.primary, row=0)
    async def overview_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Das ist nicht deine Ansicht!", ephemeral=True)
            return
        
        self.current_tab = "overview"
        await interaction.response.edit_message(embed=self.get_current_embed(), view=self)
    
    @discord.ui.button(label="⚽ Fußball", style=discord.ButtonStyle.secondary, row=0)
    async def football_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Das ist nicht deine Ansicht!", ephemeral=True)
            return
        
        self.current_tab = "football"
        await interaction.response.edit_message(embed=self.get_current_embed(), view=self)
    
    @discord.ui.button(label="🏎️ F1", style=discord.ButtonStyle.secondary, row=0)
    async def f1_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Das ist nicht deine Ansicht!", ephemeral=True)
            return
        
        self.current_tab = "f1"
        await interaction.response.edit_message(embed=self.get_current_embed(), view=self)
    
    @discord.ui.button(label="🏍️ MotoGP", style=discord.ButtonStyle.secondary, row=0)
    async def motogp_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Das ist nicht deine Ansicht!", ephemeral=True)
            return
        
        self.current_tab = "motogp"
        await interaction.response.edit_message(embed=self.get_current_embed(), view=self)
    
    @discord.ui.button(label="📜 Artikel", style=discord.ButtonStyle.success, row=1)
    async def articles_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Das ist nicht deine Ansicht!", ephemeral=True)
            return
        
        if not self.articles:
            await interaction.response.send_message("Keine Artikel verfügbar.", ephemeral=True)
            return
        
        self.current_tab = "articles"
        self.current_page = 0
        await interaction.response.edit_message(embed=self.get_current_embed(), view=self)
    
    @discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary, row=1)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Das ist nicht deine Ansicht!", ephemeral=True)
            return
        
        if self.current_tab == "articles" and self.current_page > 0:
            self.current_page -= 1
            await interaction.response.edit_message(embed=self.get_current_embed(), view=self)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label="▶️", style=discord.ButtonStyle.secondary, row=1)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Das ist nicht deine Ansicht!", ephemeral=True)
            return
        
        if self.current_tab == "articles" and self.current_page < len(self.articles) - 1:
            self.current_page += 1
            await interaction.response.edit_message(embed=self.get_current_embed(), view=self)
        else:
            await interaction.response.defer()


