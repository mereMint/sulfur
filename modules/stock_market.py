"""
Sulfur Bot - Stock Market System
A fun, fast-paced stock trading game with realistic behavior.
"""

import discord
import random
import asyncio
from datetime import datetime, timezone, timedelta
from modules.logger_utils import bot_logger as logger


# Stock categories with different volatility
STOCK_CATEGORIES = {
    'tech': {'volatility': 0.08, 'trend_strength': 0.6},
    'crypto': {'volatility': 0.15, 'trend_strength': 0.4},
    'blue_chip': {'volatility': 0.03, 'trend_strength': 0.8},
    'meme': {'volatility': 0.20, 'trend_strength': 0.2},
    'commodity': {'volatility': 0.05, 'trend_strength': 0.7},
    'fund': {'volatility': 0.02, 'trend_strength': 0.9}  # NEW: Safe funds category
}

# Initial stock list
DEFAULT_STOCKS = [
    {'symbol': 'SULF', 'name': 'Sulfur Technologies', 'category': 'tech', 'price': 100.0},
    {'symbol': 'DSCRD', 'name': 'Discord Inc', 'category': 'tech', 'price': 250.0},
    {'symbol': 'BTCN', 'name': 'Bitcoin Corp', 'category': 'crypto', 'price': 50000.0},
    {'symbol': 'MEME', 'name': 'Meme Stock LLC', 'category': 'meme', 'price': 5.0},
    {'symbol': 'GOLD', 'name': 'Gold Standard', 'category': 'commodity', 'price': 1800.0},
    {'symbol': 'APPL', 'name': 'Apple Corp', 'category': 'blue_chip', 'price': 175.0},
    {'symbol': 'TSLA', 'name': 'Tesla Motors', 'category': 'tech', 'price': 220.0},
    {'symbol': 'DOGE', 'name': 'Dogecoin Fund', 'category': 'crypto', 'price': 0.15},
    {'symbol': 'GME', 'name': 'GameStop', 'category': 'meme', 'price': 25.0},
    {'symbol': 'OIL', 'name': 'Crude Oil ETF', 'category': 'commodity', 'price': 80.0},
    # Game-influenced stocks
    {'symbol': 'WOLF', 'name': 'Werwolf Inc', 'category': 'meme', 'price': 50.0},
    {'symbol': 'BOOST', 'name': 'Boost Corporation', 'category': 'tech', 'price': 120.0},
    {'symbol': 'COLOR', 'name': 'Color Dynamics Ltd', 'category': 'blue_chip', 'price': 85.0},
    {'symbol': 'GAMBL', 'name': 'Gambling Industries', 'category': 'meme', 'price': 35.0},
    # NEW: More stocks
    {'symbol': 'AMZN', 'name': 'Amazon Corp', 'category': 'tech', 'price': 145.0},
    {'symbol': 'GOOGL', 'name': 'Google Inc', 'category': 'tech', 'price': 138.0},
    {'symbol': 'MSFT', 'name': 'Microsoft Corp', 'category': 'blue_chip', 'price': 378.0},
    {'symbol': 'NVDA', 'name': 'Nvidia Corp', 'category': 'tech', 'price': 480.0},
    {'symbol': 'META', 'name': 'Meta Platforms', 'category': 'tech', 'price': 325.0},
    {'symbol': 'NFLX', 'name': 'Netflix Inc', 'category': 'tech', 'price': 475.0},
    {'symbol': 'ETH', 'name': 'Ethereum Fund', 'category': 'crypto', 'price': 2500.0},
    {'symbol': 'SHIB', 'name': 'Shiba Inu Coin', 'category': 'meme', 'price': 0.000025},
    {'symbol': 'SILV', 'name': 'Silver ETF', 'category': 'commodity', 'price': 24.0},
    {'symbol': 'PLAT', 'name': 'Platinum Fund', 'category': 'commodity', 'price': 950.0},
    {'symbol': 'COCO', 'name': 'Cocoa Commodity', 'category': 'commodity', 'price': 3.50},
    {'symbol': 'COFF', 'name': 'Coffee Futures', 'category': 'commodity', 'price': 2.10},
    # NEW: Safe Funds
    {'symbol': 'SFND', 'name': 'Stability Fund', 'category': 'fund', 'price': 1000.0},
    {'symbol': 'BOND', 'name': 'Bond Index Fund', 'category': 'fund', 'price': 500.0},
    {'symbol': 'DIVD', 'name': 'Dividend Growth Fund', 'category': 'fund', 'price': 750.0},
    {'symbol': 'BALN', 'name': 'Balanced Fund', 'category': 'fund', 'price': 600.0},
    {'symbol': 'GLBL', 'name': 'Global Index Fund', 'category': 'fund', 'price': 850.0},
]


async def initialize_stocks(db_helpers):
    """Initialize stock market with default stocks if not already done."""
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
            # Create stocks table if it doesn't exist
            # Note: current_price uses DECIMAL(18, 8) to handle crypto with very small values (e.g., SHIB at 0.000025)
            # trend uses DECIMAL(6, 5) to allow values from -9.99999 to 9.99999 (normal trends are ±0.5)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stocks (
                    symbol VARCHAR(10) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    category VARCHAR(20) NOT NULL,
                    current_price DECIMAL(18, 8) NOT NULL,
                    previous_price DECIMAL(18, 8) NOT NULL,
                    trend DECIMAL(6, 5) DEFAULT 0,
                    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    volume_today INT DEFAULT 0,
                    game_influence_factor DECIMAL(6, 5) DEFAULT 0
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Migrate existing tables to new decimal precision if needed
            # This handles existing installations with the old DECIMAL(15, 2) and DECIMAL(5, 4) schema
            try:
                cursor.execute("""
                    ALTER TABLE stocks 
                    MODIFY COLUMN current_price DECIMAL(18, 8) NOT NULL,
                    MODIFY COLUMN previous_price DECIMAL(18, 8) NOT NULL,
                    MODIFY COLUMN trend DECIMAL(6, 5) DEFAULT 0,
                    MODIFY COLUMN game_influence_factor DECIMAL(6, 5) DEFAULT 0
                """)
            except Exception:
                pass  # Table might not exist yet or columns already have correct type
            
            try:
                cursor.execute("""
                    ALTER TABLE user_portfolios 
                    MODIFY COLUMN avg_buy_price DECIMAL(18, 8) NOT NULL
                """)
            except Exception:
                pass  # Table might not exist yet or column already has correct type
            
            try:
                cursor.execute("""
                    ALTER TABLE stock_history 
                    MODIFY COLUMN price DECIMAL(18, 8) NOT NULL
                """)
            except Exception:
                pass  # Table might not exist yet or column already has correct type
            
            # Create user portfolios table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_portfolios (
                    user_id BIGINT NOT NULL,
                    stock_symbol VARCHAR(10) NOT NULL,
                    shares INT NOT NULL DEFAULT 0,
                    avg_buy_price DECIMAL(18, 8) NOT NULL,
                    last_transaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, stock_symbol),
                    FOREIGN KEY (stock_symbol) REFERENCES stocks(symbol) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Create stock history table for tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    stock_symbol VARCHAR(10) NOT NULL,
                    price DECIMAL(18, 8) NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (stock_symbol) REFERENCES stocks(symbol) ON DELETE CASCADE,
                    INDEX idx_symbol_time (stock_symbol, timestamp)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            conn.commit()
            
            # Insert or update default stocks (allows adding new stocks without duplicating existing ones)
            stocks_added = 0
            stocks_updated = 0
            for stock in DEFAULT_STOCKS:
                cursor.execute("""
                    INSERT INTO stocks (symbol, name, category, current_price, previous_price, trend)
                    VALUES (%s, %s, %s, %s, %s, 0)
                    ON DUPLICATE KEY UPDATE 
                        name = VALUES(name),
                        category = VALUES(category)
                """, (stock['symbol'], stock['name'], stock['category'], stock['price'], stock['price']))
                
                # MySQL returns rowcount=1 for INSERT, rowcount=2 for UPDATE on DUPLICATE KEY
                if cursor.rowcount == 1:
                    stocks_added += 1
                elif cursor.rowcount == 2:
                    stocks_updated += 1
            
            conn.commit()
            
            if stocks_added > 0 or stocks_updated > 0:
                logger.info(f"Stock market initialized: {stocks_added} stocks added, {stocks_updated} stocks updated (total: {len(DEFAULT_STOCKS)} stocks)")
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        logger.error(f"Error initializing stocks: {e}", exc_info=True)


async def update_stock_prices(db_helpers):
    """Update all stock prices with realistic market simulation."""
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
            # Get all stocks
            cursor.execute("SELECT symbol, category, current_price, trend, game_influence_factor FROM stocks")
            stocks = cursor.fetchall()
            
            for stock in stocks:
                symbol, category, current_price, trend, game_influence = stock
                current_price = float(current_price)
                trend = float(trend) if trend else 0
                game_influence = float(game_influence) if game_influence else 0
                
                cat_data = STOCK_CATEGORIES.get(category, STOCK_CATEGORIES['tech'])
                
                # Calculate price change
                volatility = cat_data['volatility']
                trend_strength = cat_data['trend_strength']
                
                # Trend persistence (trending stocks continue trending)
                if abs(trend) > 0.02:
                    trend_factor = trend * trend_strength
                else:
                    trend_factor = 0
                
                # Add game influence for special stocks
                # Game influence slowly decays over time
                trend_factor += game_influence * 0.3
                
                # Random walk with trend
                random_factor = random.uniform(-volatility, volatility)
                price_change_pct = trend_factor + random_factor
                
                # Apply change
                new_price = current_price * (1 + price_change_pct)
                
                # Prevent negative or zero prices
                # Use smaller minimum for crypto (SHIB can be 0.000025)
                new_price = max(new_price, 0.00000001)
                
                # Round to 8 decimal places to fit DECIMAL(18, 8) schema
                # This preserves precision for crypto with very small values
                new_price = round(new_price, 8)
                
                # Update trend (with mean reversion)
                new_trend = (trend * 0.7) + (price_change_pct * 0.3)
                
                # Clamp trend to reasonable bounds to prevent DECIMAL(5,4) overflow
                # DECIMAL(5,4) allows values from -9.9999 to 9.9999
                # Normal trends are around ±0.5, so ±1.0 provides safety margin
                new_trend = max(-1.0, min(1.0, new_trend))
                
                # Decay game influence
                new_game_influence = game_influence * 0.85
                
                # Update stock
                cursor.execute("""
                    UPDATE stocks 
                    SET previous_price = current_price,
                        current_price = %s,
                        trend = %s,
                        game_influence_factor = %s,
                        last_update = NOW(),
                        volume_today = 0
                    WHERE symbol = %s
                """, (new_price, new_trend, new_game_influence, symbol))
                
                # Record history
                cursor.execute("""
                    INSERT INTO stock_history (stock_symbol, price)
                    VALUES (%s, %s)
                """, (symbol, new_price))
            
            conn.commit()
            logger.info(f"Updated {len(stocks)} stock prices")
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        logger.error(f"Error updating stock prices: {e}", exc_info=True)


async def get_stock(db_helpers, symbol: str):
    """Get stock information by symbol."""
    try:
        if not db_helpers.db_pool:
            return None
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return None
        
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT symbol, name, category, current_price, previous_price, trend, volume_today, last_update
                FROM stocks WHERE symbol = %s
            """, (symbol.upper(),))
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error getting stock {symbol}: {e}", exc_info=True)
        return None


async def get_all_stocks(db_helpers, limit: int = 50):
    """Get all stocks from database."""
    try:
        if not db_helpers.db_pool:
            return []
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return []
        
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT symbol, name, category
                FROM stocks
                ORDER BY symbol ASC
                LIMIT %s
            """, (limit,))
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error getting all stocks: {e}", exc_info=True)
        return []


async def get_top_stocks(db_helpers, limit: int = 10):
    """Get top stocks by price change."""
    try:
        if not db_helpers.db_pool:
            return []
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return []
        
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT symbol, name, current_price, previous_price,
                       ((current_price - previous_price) / previous_price * 100) as change_pct,
                       volume_today
                FROM stocks
                ORDER BY change_pct DESC
                LIMIT %s
            """, (limit,))
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error getting top stocks: {e}", exc_info=True)
        return []


async def get_user_portfolio(db_helpers, user_id: int):
    """Get user's stock portfolio."""
    try:
        if not db_helpers.db_pool:
            return []
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return []
        
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT p.stock_symbol, s.name, p.shares, p.avg_buy_price, s.current_price,
                       ((s.current_price - p.avg_buy_price) / p.avg_buy_price * 100) as gain_pct,
                       (p.shares * s.current_price) as current_value
                FROM user_portfolios p
                JOIN stocks s ON p.stock_symbol = s.symbol
                WHERE p.user_id = %s AND p.shares > 0
                ORDER BY current_value DESC
            """, (user_id,))
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error getting portfolio for user {user_id}: {e}", exc_info=True)
        return []


async def get_recent_trades(db_helpers, limit: int = 10):
    """Get recent stock trades from transaction history."""
    try:
        if not db_helpers.db_pool:
            return []
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return []
        
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT transaction_type, description, created_at, ABS(amount) as volume
                FROM transaction_history
                WHERE transaction_type IN ('stock_buy', 'stock_sell')
                ORDER BY created_at DESC
                LIMIT %s
            """, (limit,))
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error getting recent trades: {e}", exc_info=True)
        return []


async def get_stock_stats(db_helpers, symbol: str):
    """Get detailed statistics for a stock including 24h high/low."""
    try:
        if not db_helpers.db_pool:
            return None
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return None
        
        cursor = conn.cursor()
        try:
            # Get current stock info
            cursor.execute("""
                SELECT symbol, name, category, current_price, previous_price, trend, volume_today, last_update
                FROM stocks WHERE symbol = %s
            """, (symbol.upper(),))
            stock = cursor.fetchone()
            
            if not stock:
                return None
            
            # Get 24h high/low from history
            cursor.execute("""
                SELECT MAX(price) as high_24h, MIN(price) as low_24h
                FROM stock_history
                WHERE stock_symbol = %s
                AND timestamp > DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """, (symbol.upper(),))
            stats = cursor.fetchone()
            
            # Get active traders count
            cursor.execute("""
                SELECT COUNT(DISTINCT user_id) as active_traders
                FROM transaction_history
                WHERE description LIKE %s
                AND created_at > DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """, (f'%{symbol.upper()}%',))
            traders = cursor.fetchone()
            
            return {
                'stock': stock,
                'high_24h': stats[0] if stats else stock[3],
                'low_24h': stats[1] if stats else stock[3],
                'active_traders': traders[0] if traders else 0
            }
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error getting stock stats for {symbol}: {e}", exc_info=True)
        return None


async def get_market_overview(db_helpers):
    """Get overall market statistics."""
    try:
        if not db_helpers.db_pool:
            return None
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return None
        
        cursor = conn.cursor()
        try:
            # Get market stats
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_stocks,
                    SUM(volume_today) as total_volume,
                    AVG(((current_price - previous_price) / previous_price * 100)) as avg_change
                FROM stocks
            """)
            market = cursor.fetchone()
            
            # Get trading activity
            cursor.execute("""
                SELECT COUNT(*) as trades_24h
                FROM transaction_history
                WHERE transaction_type IN ('stock_buy', 'stock_sell')
                AND created_at > DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """)
            activity = cursor.fetchone()
            
            return {
                'total_stocks': market[0] if market else 0,
                'total_volume': market[1] if market else 0,
                'avg_change': float(market[2]) if market and market[2] else 0,
                'trades_24h': activity[0] if activity else 0
            }
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error getting market overview: {e}", exc_info=True)
        return None


async def buy_stock(db_helpers, user_id: int, symbol: str, shares: int, currency_system):
    """Buy stock shares."""
    try:
        symbol = symbol.upper()
        
        # Get stock info first (synchronous)
        if not db_helpers.db_pool:
            return False, "Datenbankverbindung nicht verfügbar!"
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return False, "Datenbankverbindung fehlgeschlagen!"
        
        cursor = conn.cursor()
        try:
            # Get stock info
            cursor.execute("""
                SELECT current_price FROM stocks WHERE symbol = %s
            """, (symbol,))
            stock = cursor.fetchone()
            
            if not stock:
                return False, "Stock nicht gefunden!"
            
            current_price = float(stock[0])
            total_cost = current_price * shares
            
            # Check if user has enough currency
            user_balance = await db_helpers.get_balance(user_id)
            
            if user_balance < total_cost:
                return False, f"Nicht genug Geld! Benötigt: {total_cost:.2f}, Verfügbar: {user_balance:.2f}"
            
            # Deduct currency (this handles the players table)
            cursor.execute("SELECT display_name FROM players WHERE discord_id = %s", (user_id,))
            player_row = cursor.fetchone()
            display_name = player_row[0] if player_row else f"User{user_id}"
            
            # Update balance directly
            cursor.execute("""
                UPDATE players SET balance = balance - %s WHERE discord_id = %s
            """, (total_cost, user_id))
            
            # Update or insert portfolio entry
            cursor.execute("""
                SELECT shares, avg_buy_price FROM user_portfolios
                WHERE user_id = %s AND stock_symbol = %s
            """, (user_id, symbol))
            existing = cursor.fetchone()
            
            if existing:
                old_shares, old_avg_price = existing
                new_shares = old_shares + shares
                new_avg_price = ((old_shares * float(old_avg_price)) + (shares * current_price)) / new_shares
                
                cursor.execute("""
                    UPDATE user_portfolios
                    SET shares = %s, avg_buy_price = %s, last_transaction = NOW()
                    WHERE user_id = %s AND stock_symbol = %s
                """, (new_shares, new_avg_price, user_id, symbol))
            else:
                cursor.execute("""
                    INSERT INTO user_portfolios (user_id, stock_symbol, shares, avg_buy_price)
                    VALUES (%s, %s, %s, %s)
                """, (user_id, symbol, shares, current_price))
            
            # Update volume
            cursor.execute("""
                UPDATE stocks SET volume_today = volume_today + %s WHERE symbol = %s
            """, (shares, symbol))
            
            # Get new balance for transaction log
            cursor.execute("SELECT balance FROM players WHERE discord_id = %s", (user_id,))
            new_balance = cursor.fetchone()[0]
            
            # Log transaction
            cursor.execute("""
                INSERT INTO transaction_history (user_id, transaction_type, amount, balance_after, description)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, 'stock_buy', -total_cost, new_balance, f"Gekauft: {shares}x {symbol} @ {format_price(current_price)}"))
            
            conn.commit()
            return True, f"Gekauft: {shares} Aktien von {symbol} für {total_cost:.2f}"
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        logger.error(f"Error buying stock: {e}", exc_info=True)
        return False, f"Fehler beim Kauf: {str(e)}"


async def sell_stock(db_helpers, user_id: int, symbol: str, shares: int):
    """Sell stock shares."""
    try:
        symbol = symbol.upper()
        
        if not db_helpers.db_pool:
            return False, "Datenbankverbindung nicht verfügbar!"
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return False, "Datenbankverbindung fehlgeschlagen!"
        
        cursor = conn.cursor()
        try:
            # Check if user has shares
            cursor.execute("""
                SELECT shares FROM user_portfolios
                WHERE user_id = %s AND stock_symbol = %s
            """, (user_id, symbol))
            portfolio = cursor.fetchone()
            
            if not portfolio or portfolio[0] < shares:
                return False, "Nicht genug Aktien!"
            
            # Get current price
            cursor.execute("""
                SELECT current_price FROM stocks WHERE symbol = %s
            """, (symbol,))
            stock = cursor.fetchone()
            
            if not stock:
                return False, "Stock nicht gefunden!"
            
            current_price = float(stock[0])
            total_value = current_price * shares
            
            # Add currency
            cursor.execute("""
                UPDATE players SET balance = balance + %s WHERE discord_id = %s
            """, (total_value, user_id))
            
            # Update portfolio
            new_shares = portfolio[0] - shares
            
            if new_shares > 0:
                cursor.execute("""
                    UPDATE user_portfolios
                    SET shares = %s, last_transaction = NOW()
                    WHERE user_id = %s AND stock_symbol = %s
                """, (new_shares, user_id, symbol))
            else:
                # Remove entry if no shares left
                cursor.execute("""
                    DELETE FROM user_portfolios
                    WHERE user_id = %s AND stock_symbol = %s
                """, (user_id, symbol))
            
            # Update volume
            cursor.execute("""
                UPDATE stocks SET volume_today = volume_today + %s WHERE symbol = %s
            """, (shares, symbol))
            
            # Get new balance for transaction log
            cursor.execute("SELECT balance FROM players WHERE discord_id = %s", (user_id,))
            new_balance = cursor.fetchone()[0]
            
            # Log transaction
            cursor.execute("""
                INSERT INTO transaction_history (user_id, transaction_type, amount, balance_after, description)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, 'stock_sell', total_value, new_balance, f"Verkauft: {shares}x {symbol} @ {format_price(current_price)}"))
            
            conn.commit()
            return True, f"Verkauft: {shares} Aktien von {symbol} für {total_value:.2f}"
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        logger.error(f"Error selling stock: {e}", exc_info=True)
        return False, f"Fehler beim Verkauf: {str(e)}"


def get_stock_emoji(change_pct: float) -> str:
    """Get emoji based on stock performance."""
    if change_pct > 5:
        return "🚀"
    elif change_pct > 2:
        return "📈"
    elif change_pct > 0:
        return "✅"
    elif change_pct > -2:
        return "📉"
    elif change_pct > -5:
        return "⚠️"
    else:
        return "💥"


def format_price(price: float) -> str:
    """Format price for display."""
    if price < 1:
        return f"${price:.4f}"
    elif price < 100:
        return f"${price:.2f}"
    else:
        return f"${price:,.2f}"


async def influence_stock_by_activity(db_helpers, stock_symbol: str, influence: float):
    """
    Influence a stock's price based on game activity.
    
    Args:
        db_helpers: Database helpers module
        stock_symbol: Stock symbol (e.g., 'WOLF', 'BOOST', 'COLOR', 'GAMBL')
        influence: Influence factor (-1.0 to 1.0) - positive = stock goes up, negative = stock goes down
    """
    try:
        if not db_helpers.db_pool:
            return
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return
        
        cursor = conn.cursor()
        try:
            # Clamp influence to reasonable bounds
            influence = max(-1.0, min(1.0, influence))
            
            # Update the game influence factor for the stock
            # This will be used in the next price update
            cursor.execute("""
                UPDATE stocks 
                SET game_influence_factor = game_influence_factor + %s
                WHERE symbol = %s
            """, (influence * 0.1, stock_symbol.upper()))  # Scale down the influence
            
            conn.commit()
            logger.debug(f"Applied influence {influence} to stock {stock_symbol}")
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error influencing stock {stock_symbol}: {e}", exc_info=True)


# Helper functions for specific game activities
async def record_werwolf_activity(db_helpers, num_players: int, roles_bought: int = 0):
    """Record Werwolf game activity and influence WOLF stock."""
    # More players and role purchases = positive influence
    influence = (num_players / 10.0) + (roles_bought * 0.2)
    await influence_stock_by_activity(db_helpers, 'WOLF', influence)


async def record_boost_purchase(db_helpers, boost_type: str, duration_hours: int):
    """Record boost purchase and influence BOOST stock."""
    # Longer boosts = more positive influence
    influence = duration_hours / 24.0
    await influence_stock_by_activity(db_helpers, 'BOOST', influence)


async def record_color_purchase(db_helpers, tier: str):
    """Record color role purchase and influence COLOR stock."""
    # Higher tiers = more influence
    tier_influence = {'basic': 0.3, 'premium': 0.6, 'legendary': 1.0}
    influence = tier_influence.get(tier, 0.5)
    await influence_stock_by_activity(db_helpers, 'COLOR', influence)


async def record_gambling_activity(db_helpers, bet_amount: float, won: bool, payout: float = 0):
    """Record gambling activity and influence GAMBL stock."""
    # Big losses = stock goes up (house wins)
    # Big wins = stock goes down (house loses)
    if won:
        influence = -(payout / 1000.0)  # Negative influence when players win big
    else:
        influence = bet_amount / 1000.0  # Positive influence when players lose
    
    influence = max(-0.5, min(0.5, influence))  # Limit the impact
    await influence_stock_by_activity(db_helpers, 'GAMBL', influence)
