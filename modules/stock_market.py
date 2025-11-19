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
    'commodity': {'volatility': 0.05, 'trend_strength': 0.7}
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
]


async def initialize_stocks(db_helpers):
    """Initialize stock market with default stocks if not already done."""
    try:
        async with db_helpers.get_db_connection() as (conn, cursor):
            # Create stocks table if it doesn't exist
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS stocks (
                    symbol VARCHAR(10) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    category VARCHAR(20) NOT NULL,
                    current_price DECIMAL(15, 2) NOT NULL,
                    previous_price DECIMAL(15, 2) NOT NULL,
                    trend DECIMAL(5, 4) DEFAULT 0,
                    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    volume_today INT DEFAULT 0
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Create user portfolios table
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_portfolios (
                    user_id BIGINT NOT NULL,
                    stock_symbol VARCHAR(10) NOT NULL,
                    shares INT NOT NULL DEFAULT 0,
                    avg_buy_price DECIMAL(15, 2) NOT NULL,
                    last_transaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, stock_symbol),
                    FOREIGN KEY (stock_symbol) REFERENCES stocks(symbol) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Create stock history table for tracking
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    stock_symbol VARCHAR(10) NOT NULL,
                    price DECIMAL(15, 2) NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (stock_symbol) REFERENCES stocks(symbol) ON DELETE CASCADE,
                    INDEX idx_symbol_time (stock_symbol, timestamp)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            await conn.commit()
            
            # Check if stocks are already initialized
            await cursor.execute("SELECT COUNT(*) FROM stocks")
            result = await cursor.fetchone()
            
            if result[0] == 0:
                # Insert default stocks
                for stock in DEFAULT_STOCKS:
                    await cursor.execute("""
                        INSERT INTO stocks (symbol, name, category, current_price, previous_price, trend)
                        VALUES (%s, %s, %s, %s, %s, 0)
                    """, (stock['symbol'], stock['name'], stock['category'], stock['price'], stock['price']))
                
                await conn.commit()
                logger.info(f"Initialized stock market with {len(DEFAULT_STOCKS)} stocks")
            
    except Exception as e:
        logger.error(f"Error initializing stocks: {e}", exc_info=True)


async def update_stock_prices(db_helpers):
    """Update all stock prices with realistic market simulation."""
    try:
        async with db_helpers.get_db_connection() as (conn, cursor):
            # Get all stocks
            await cursor.execute("SELECT symbol, category, current_price, trend FROM stocks")
            stocks = await cursor.fetchall()
            
            for stock in stocks:
                symbol, category, current_price, trend = stock
                cat_data = STOCK_CATEGORIES.get(category, STOCK_CATEGORIES['tech'])
                
                # Calculate price change
                volatility = cat_data['volatility']
                trend_strength = cat_data['trend_strength']
                
                # Trend persistence (trending stocks continue trending)
                if abs(trend) > 0.02:
                    trend_factor = trend * trend_strength
                else:
                    trend_factor = 0
                
                # Random walk with trend
                random_factor = random.uniform(-volatility, volatility)
                price_change_pct = trend_factor + random_factor
                
                # Apply change
                new_price = current_price * (1 + price_change_pct)
                
                # Prevent negative or zero prices
                new_price = max(new_price, 0.01)
                
                # Update trend (with mean reversion)
                new_trend = (trend * 0.7) + (price_change_pct * 0.3)
                
                # Update stock
                await cursor.execute("""
                    UPDATE stocks 
                    SET previous_price = current_price,
                        current_price = %s,
                        trend = %s,
                        last_update = NOW(),
                        volume_today = 0
                    WHERE symbol = %s
                """, (new_price, new_trend, symbol))
                
                # Record history
                await cursor.execute("""
                    INSERT INTO stock_history (stock_symbol, price)
                    VALUES (%s, %s)
                """, (symbol, new_price))
            
            await conn.commit()
            logger.info(f"Updated {len(stocks)} stock prices")
            
    except Exception as e:
        logger.error(f"Error updating stock prices: {e}", exc_info=True)


async def get_stock(db_helpers, symbol: str):
    """Get stock information by symbol."""
    try:
        async with db_helpers.get_db_connection() as (conn, cursor):
            await cursor.execute("""
                SELECT symbol, name, category, current_price, previous_price, trend, volume_today, last_update
                FROM stocks WHERE symbol = %s
            """, (symbol.upper(),))
            return await cursor.fetchone()
    except Exception as e:
        logger.error(f"Error getting stock {symbol}: {e}", exc_info=True)
        return None


async def get_top_stocks(db_helpers, limit: int = 10):
    """Get top stocks by price change."""
    try:
        async with db_helpers.get_db_connection() as (conn, cursor):
            await cursor.execute("""
                SELECT symbol, name, current_price, previous_price,
                       ((current_price - previous_price) / previous_price * 100) as change_pct,
                       volume_today
                FROM stocks
                ORDER BY change_pct DESC
                LIMIT %s
            """, (limit,))
            return await cursor.fetchall()
    except Exception as e:
        logger.error(f"Error getting top stocks: {e}", exc_info=True)
        return []


async def get_user_portfolio(db_helpers, user_id: int):
    """Get user's stock portfolio."""
    try:
        async with db_helpers.get_db_connection() as (conn, cursor):
            await cursor.execute("""
                SELECT p.stock_symbol, s.name, p.shares, p.avg_buy_price, s.current_price,
                       ((s.current_price - p.avg_buy_price) / p.avg_buy_price * 100) as gain_pct,
                       (p.shares * s.current_price) as current_value
                FROM user_portfolios p
                JOIN stocks s ON p.stock_symbol = s.symbol
                WHERE p.user_id = %s AND p.shares > 0
                ORDER BY current_value DESC
            """, (user_id,))
            return await cursor.fetchall()
    except Exception as e:
        logger.error(f"Error getting portfolio for user {user_id}: {e}", exc_info=True)
        return []


async def buy_stock(db_helpers, user_id: int, symbol: str, shares: int, currency_system):
    """Buy stock shares."""
    try:
        symbol = symbol.upper()
        
        async with db_helpers.get_db_connection() as (conn, cursor):
            # Get stock info
            await cursor.execute("""
                SELECT current_price FROM stocks WHERE symbol = %s
            """, (symbol,))
            stock = await cursor.fetchone()
            
            if not stock:
                return False, "Stock nicht gefunden!"
            
            current_price = float(stock[0])
            total_cost = current_price * shares
            
            # Check if user has enough currency
            # This would integrate with the economy system
            user_balance = await db_helpers.get_balance(user_id)
            
            if user_balance < total_cost:
                return False, f"Nicht genug Geld! Benötigt: {total_cost:.2f}, Verfügbar: {user_balance:.2f}"
            
            # Deduct currency
            await db_helpers.add_balance(user_id, -total_cost)
            
            # Update or insert portfolio entry
            await cursor.execute("""
                SELECT shares, avg_buy_price FROM user_portfolios
                WHERE user_id = %s AND stock_symbol = %s
            """, (user_id, symbol))
            existing = await cursor.fetchone()
            
            if existing:
                old_shares, old_avg_price = existing
                new_shares = old_shares + shares
                new_avg_price = ((old_shares * old_avg_price) + (shares * current_price)) / new_shares
                
                await cursor.execute("""
                    UPDATE user_portfolios
                    SET shares = %s, avg_buy_price = %s, last_transaction = NOW()
                    WHERE user_id = %s AND stock_symbol = %s
                """, (new_shares, new_avg_price, user_id, symbol))
            else:
                await cursor.execute("""
                    INSERT INTO user_portfolios (user_id, stock_symbol, shares, avg_buy_price)
                    VALUES (%s, %s, %s, %s)
                """, (user_id, symbol, shares, current_price))
            
            # Update volume
            await cursor.execute("""
                UPDATE stocks SET volume_today = volume_today + %s WHERE symbol = %s
            """, (shares, symbol))
            
            await conn.commit()
            return True, f"Gekauft: {shares} Aktien von {symbol} für {total_cost:.2f}"
            
    except Exception as e:
        logger.error(f"Error buying stock: {e}", exc_info=True)
        return False, f"Fehler beim Kauf: {str(e)}"


async def sell_stock(db_helpers, user_id: int, symbol: str, shares: int):
    """Sell stock shares."""
    try:
        symbol = symbol.upper()
        
        async with db_helpers.get_db_connection() as (conn, cursor):
            # Check if user has shares
            await cursor.execute("""
                SELECT shares FROM user_portfolios
                WHERE user_id = %s AND stock_symbol = %s
            """, (user_id, symbol))
            portfolio = await cursor.fetchone()
            
            if not portfolio or portfolio[0] < shares:
                return False, "Nicht genug Aktien!"
            
            # Get current price
            await cursor.execute("""
                SELECT current_price FROM stocks WHERE symbol = %s
            """, (symbol,))
            stock = await cursor.fetchone()
            
            if not stock:
                return False, "Stock nicht gefunden!"
            
            current_price = float(stock[0])
            total_value = current_price * shares
            
            # Add currency
            await db_helpers.add_balance(user_id, total_value)
            
            # Update portfolio
            new_shares = portfolio[0] - shares
            
            if new_shares > 0:
                await cursor.execute("""
                    UPDATE user_portfolios
                    SET shares = %s, last_transaction = NOW()
                    WHERE user_id = %s AND stock_symbol = %s
                """, (new_shares, user_id, symbol))
            else:
                # Remove entry if no shares left
                await cursor.execute("""
                    DELETE FROM user_portfolios
                    WHERE user_id = %s AND stock_symbol = %s
                """, (user_id, symbol))
            
            # Update volume
            await cursor.execute("""
                UPDATE stocks SET volume_today = volume_today + %s WHERE symbol = %s
            """, (shares, symbol))
            
            await conn.commit()
            return True, f"Verkauft: {shares} Aktien von {symbol} für {total_value:.2f}"
            
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
