"""
Sulfur Bot - Sport Betting Module
Advanced betting system for football matches with support for multiple leagues and APIs.

Supported APIs:
- OpenLigaDB (default, free, no API key required) - Bundesliga, 2. Bundesliga, DFB-Pokal
- Football-Data.org (free tier with API key) - Bundesliga, Champions League, etc.
- Sportmonks (paid) - Extensive coverage

The system is designed to be easily extensible for other sports and leagues.
"""

import discord
import aiohttp
import asyncio
import json
import random
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
from modules.logger_utils import bot_logger as logger


# ============================================================================
# ENUMS AND CONSTANTS
# ============================================================================

class MatchStatus(Enum):
    """Status of a football match."""
    SCHEDULED = "scheduled"
    LIVE = "live"
    FINISHED = "finished"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"


class BetType(Enum):
    """Types of bets available."""
    MATCH_WINNER = "winner"  # 1X2 - Home/Draw/Away
    OVER_UNDER = "over_under"  # Over/Under goals
    BOTH_TEAMS_SCORE = "btts"  # Both teams to score


class BetOutcome(Enum):
    """Possible outcomes for a bet."""
    HOME = "home"
    DRAW = "draw"
    AWAY = "away"
    OVER = "over"
    UNDER = "under"
    YES = "yes"
    NO = "no"


# League configurations with display info
LEAGUES = {
    "bl1": {
        "name": "Bundesliga",
        "country": "Germany",
        "emoji": "🇩🇪",
        "api_id": "bl1",
        "provider": "openligadb"
    },
    "bl2": {
        "name": "2. Bundesliga",
        "country": "Germany",
        "emoji": "🇩🇪",
        "api_id": "bl2",
        "provider": "openligadb"
    },
    "dfb": {
        "name": "DFB-Pokal",
        "country": "Germany",
        "emoji": "🏆",
        "api_id": "dfb",
        "provider": "openligadb"
    },
    "cl": {
        "name": "Champions League",
        "country": "Europe",
        "emoji": "🏆",
        "api_id": "CL",
        "provider": "football_data"
    },
    "pl": {
        "name": "Premier League",
        "country": "England",
        "emoji": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
        "api_id": "PL",
        "provider": "football_data"
    },
    "la_liga": {
        "name": "La Liga",
        "country": "Spain",
        "emoji": "🇪🇸",
        "api_id": "PD",
        "provider": "football_data"
    },
    "serie_a": {
        "name": "Serie A",
        "country": "Italy",
        "emoji": "🇮🇹",
        "api_id": "SA",
        "provider": "football_data"
    }
}


# ============================================================================
# API PROVIDER BASE CLASS
# ============================================================================

class FootballAPIProvider(ABC):
    """Abstract base class for football data API providers."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    @abstractmethod
    async def get_matches(self, league_id: str, matchday: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get matches for a league."""
        pass
    
    @abstractmethod
    async def get_match(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific match by ID."""
        pass
    
    @abstractmethod
    async def get_current_matchday(self, league_id: str) -> int:
        """Get the current matchday for a league."""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the name of the API provider."""
        pass


# ============================================================================
# OPENLIGADB PROVIDER (FREE, NO API KEY)
# ============================================================================

class OpenLigaDBProvider(FootballAPIProvider):
    """
    OpenLigaDB API provider - completely free, no API key required.
    Supports German leagues: Bundesliga, 2. Bundesliga, DFB-Pokal
    API Documentation: https://www.openligadb.de/
    """
    
    BASE_URL = "https://api.openligadb.de"
    
    def get_provider_name(self) -> str:
        return "OpenLigaDB"
    
    def _get_season(self) -> int:
        """Get the current football season year."""
        now = datetime.now()
        # Football season starts in August
        if now.month >= 8:
            return now.year
        return now.year - 1
    
    async def get_matches(self, league_id: str, matchday: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get matches from OpenLigaDB."""
        try:
            session = await self.get_session()
            season = self._get_season()
            
            if matchday:
                url = f"{self.BASE_URL}/getmatchdata/{league_id}/{season}/{matchday}"
            else:
                # Get current matchday
                url = f"{self.BASE_URL}/getmatchdata/{league_id}"
            
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status != 200:
                    logger.error(f"OpenLigaDB API error: {response.status}")
                    return []
                
                data = await response.json()
                return self._parse_matches(data)
                
        except asyncio.TimeoutError:
            logger.error("OpenLigaDB API timeout")
            return []
        except Exception as e:
            logger.error(f"OpenLigaDB API error: {e}", exc_info=True)
            return []
    
    async def get_match(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific match by ID."""
        try:
            session = await self.get_session()
            url = f"{self.BASE_URL}/getmatchdata/{match_id}"
            
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                matches = self._parse_matches([data] if isinstance(data, dict) else data)
                return matches[0] if matches else None
                
        except Exception as e:
            logger.error(f"Error getting match {match_id}: {e}", exc_info=True)
            return None
    
    async def get_current_matchday(self, league_id: str) -> int:
        """Get the current matchday for a league."""
        try:
            session = await self.get_session()
            season = self._get_season()
            url = f"{self.BASE_URL}/getcurrentgroup/{league_id}"
            
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status != 200:
                    return 1
                
                data = await response.json()
                return data.get("groupOrderID", 1)
                
        except Exception as e:
            logger.error(f"Error getting current matchday: {e}", exc_info=True)
            return 1
    
    def _parse_matches(self, data: List[Dict]) -> List[Dict[str, Any]]:
        """Parse OpenLigaDB match data into standardized format."""
        matches = []
        
        for match in data:
            try:
                # Parse match time
                match_time_str = match.get("matchDateTime") or match.get("matchDateTimeUTC")
                if match_time_str:
                    try:
                        match_time = datetime.fromisoformat(match_time_str.replace("Z", "+00:00"))
                    except ValueError:
                        match_time = datetime.now(timezone.utc)
                else:
                    match_time = datetime.now(timezone.utc)
                
                # Determine match status
                is_finished = match.get("matchIsFinished", False)
                now = datetime.now(timezone.utc)
                
                if is_finished:
                    status = MatchStatus.FINISHED
                elif match_time <= now <= match_time + timedelta(hours=2):
                    status = MatchStatus.LIVE
                else:
                    status = MatchStatus.SCHEDULED
                
                # Get scores
                match_results = match.get("matchResults", [])
                home_score = 0
                away_score = 0
                
                for result in match_results:
                    if result.get("resultTypeID") == 2:  # Final result
                        home_score = result.get("pointsTeam1", 0)
                        away_score = result.get("pointsTeam2", 0)
                        break
                
                team1 = match.get("team1", {})
                team2 = match.get("team2", {})
                
                parsed_match = {
                    "id": str(match.get("matchID")),
                    "home_team": team1.get("teamName", "Unknown"),
                    "away_team": team2.get("teamName", "Unknown"),
                    "home_team_short": team1.get("shortName", team1.get("teamName", "UNK")[:3].upper()),
                    "away_team_short": team2.get("shortName", team2.get("teamName", "UNK")[:3].upper()),
                    "home_logo": team1.get("teamIconUrl"),
                    "away_logo": team2.get("teamIconUrl"),
                    "home_score": home_score,
                    "away_score": away_score,
                    "status": status,
                    "match_time": match_time,
                    "matchday": match.get("group", {}).get("groupOrderID", 1),
                    "league_id": match.get("leagueShortcut", "bl1"),
                    "provider": "openligadb"
                }
                
                matches.append(parsed_match)
                
            except Exception as e:
                logger.error(f"Error parsing match: {e}", exc_info=True)
                continue
        
        return matches


# ============================================================================
# FOOTBALL-DATA.ORG PROVIDER (FREE TIER WITH API KEY)
# ============================================================================

class FootballDataProvider(FootballAPIProvider):
    """
    Football-Data.org API provider.
    Free tier: 10 requests/minute, limited competitions.
    Requires API key (free registration).
    """
    
    BASE_URL = "https://api.football-data.org/v4"
    
    def get_provider_name(self) -> str:
        return "Football-Data.org"
    
    async def get_matches(self, league_id: str, matchday: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get matches from Football-Data.org."""
        if not self.api_key:
            logger.warning("Football-Data.org API key not configured")
            return []
        
        try:
            session = await self.get_session()
            headers = {"X-Auth-Token": self.api_key}
            
            url = f"{self.BASE_URL}/competitions/{league_id}/matches"
            params = {}
            if matchday:
                params["matchday"] = matchday
            
            async with session.get(url, headers=headers, params=params, 
                                   timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status != 200:
                    logger.error(f"Football-Data.org API error: {response.status}")
                    return []
                
                data = await response.json()
                return self._parse_matches(data.get("matches", []), league_id)
                
        except Exception as e:
            logger.error(f"Football-Data.org API error: {e}", exc_info=True)
            return []
    
    async def get_match(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific match by ID."""
        if not self.api_key:
            return None
        
        try:
            session = await self.get_session()
            headers = {"X-Auth-Token": self.api_key}
            url = f"{self.BASE_URL}/matches/{match_id}"
            
            async with session.get(url, headers=headers,
                                   timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                matches = self._parse_matches([data], data.get("competition", {}).get("code", ""))
                return matches[0] if matches else None
                
        except Exception as e:
            logger.error(f"Error getting match {match_id}: {e}", exc_info=True)
            return None
    
    async def get_current_matchday(self, league_id: str) -> int:
        """Get the current matchday for a league."""
        if not self.api_key:
            return 1
        
        try:
            session = await self.get_session()
            headers = {"X-Auth-Token": self.api_key}
            url = f"{self.BASE_URL}/competitions/{league_id}"
            
            async with session.get(url, headers=headers,
                                   timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status != 200:
                    return 1
                
                data = await response.json()
                return data.get("currentSeason", {}).get("currentMatchday", 1)
                
        except Exception as e:
            logger.error(f"Error getting current matchday: {e}", exc_info=True)
            return 1
    
    def _parse_matches(self, data: List[Dict], league_id: str) -> List[Dict[str, Any]]:
        """Parse Football-Data.org match data into standardized format."""
        matches = []
        
        status_mapping = {
            "SCHEDULED": MatchStatus.SCHEDULED,
            "TIMED": MatchStatus.SCHEDULED,
            "IN_PLAY": MatchStatus.LIVE,
            "PAUSED": MatchStatus.LIVE,
            "FINISHED": MatchStatus.FINISHED,
            "POSTPONED": MatchStatus.POSTPONED,
            "CANCELLED": MatchStatus.CANCELLED
        }
        
        for match in data:
            try:
                match_time_str = match.get("utcDate")
                if match_time_str:
                    match_time = datetime.fromisoformat(match_time_str.replace("Z", "+00:00"))
                else:
                    match_time = datetime.now(timezone.utc)
                
                status_str = match.get("status", "SCHEDULED")
                status = status_mapping.get(status_str, MatchStatus.SCHEDULED)
                
                score = match.get("score", {})
                full_time = score.get("fullTime", {})
                
                home_team = match.get("homeTeam", {})
                away_team = match.get("awayTeam", {})
                
                parsed_match = {
                    "id": str(match.get("id")),
                    "home_team": home_team.get("name", "Unknown"),
                    "away_team": away_team.get("name", "Unknown"),
                    "home_team_short": home_team.get("tla", home_team.get("name", "UNK")[:3].upper()),
                    "away_team_short": away_team.get("tla", away_team.get("name", "UNK")[:3].upper()),
                    "home_logo": home_team.get("crest"),
                    "away_logo": away_team.get("crest"),
                    "home_score": full_time.get("home") or 0,
                    "away_score": full_time.get("away") or 0,
                    "status": status,
                    "match_time": match_time,
                    "matchday": match.get("matchday", 1),
                    "league_id": league_id.lower(),
                    "provider": "football_data"
                }
                
                matches.append(parsed_match)
                
            except Exception as e:
                logger.error(f"Error parsing match: {e}", exc_info=True)
                continue
        
        return matches


# ============================================================================
# API PROVIDER FACTORY
# ============================================================================

class APIProviderFactory:
    """Factory for creating API providers."""
    
    _providers: Dict[str, FootballAPIProvider] = {}
    _api_keys: Dict[str, str] = {}
    
    @classmethod
    def configure(cls, provider_name: str, api_key: Optional[str] = None):
        """Configure an API provider with credentials."""
        cls._api_keys[provider_name] = api_key
        # Clear cached provider to recreate with new key
        if provider_name in cls._providers:
            del cls._providers[provider_name]
    
    @classmethod
    def get_provider(cls, provider_name: str) -> FootballAPIProvider:
        """Get or create an API provider instance."""
        if provider_name not in cls._providers:
            api_key = cls._api_keys.get(provider_name)
            
            if provider_name == "openligadb":
                cls._providers[provider_name] = OpenLigaDBProvider()
            elif provider_name == "football_data":
                cls._providers[provider_name] = FootballDataProvider(api_key)
            else:
                # Default to OpenLigaDB (free, no key required)
                cls._providers[provider_name] = OpenLigaDBProvider()
        
        return cls._providers[provider_name]
    
    @classmethod
    async def close_all(cls):
        """Close all provider sessions."""
        for provider in cls._providers.values():
            await provider.close()
        cls._providers.clear()


# ============================================================================
# ODDS CALCULATOR
# ============================================================================

class OddsCalculator:
    """
    Calculate betting odds based on match data and betting patterns.
    Uses a simplified model for fair odds calculation.
    """
    
    # House edge (5%)
    HOUSE_EDGE = 0.05
    
    @staticmethod
    def calculate_match_odds(match: Dict[str, Any], total_bets: Dict[str, int] = None) -> Dict[str, float]:
        """
        Calculate odds for a match based on team names and betting pool.
        Returns odds for home win, draw, and away win.
        """
        # Base odds (will be adjusted by betting pool)
        # In a real system, these would come from historical data
        base_home = 2.0
        base_draw = 3.5
        base_away = 3.0
        
        # If we have betting data, adjust odds based on pool
        if total_bets:
            total_pool = sum(total_bets.values())
            if total_pool > 0:
                home_pool = total_bets.get("home", 0)
                draw_pool = total_bets.get("draw", 0)
                away_pool = total_bets.get("away", 0)
                
                # Adjust odds inversely to bet distribution
                if home_pool > 0:
                    base_home = max(1.1, (total_pool / home_pool) * (1 - OddsCalculator.HOUSE_EDGE))
                if draw_pool > 0:
                    base_draw = max(1.1, (total_pool / draw_pool) * (1 - OddsCalculator.HOUSE_EDGE))
                if away_pool > 0:
                    base_away = max(1.1, (total_pool / away_pool) * (1 - OddsCalculator.HOUSE_EDGE))
        
        # Add some randomness for variety (±10%)
        variation = 0.1
        base_home *= random.uniform(1 - variation, 1 + variation)
        base_draw *= random.uniform(1 - variation, 1 + variation)
        base_away *= random.uniform(1 - variation, 1 + variation)
        
        return {
            "home": round(base_home, 2),
            "draw": round(base_draw, 2),
            "away": round(base_away, 2)
        }
    
    @staticmethod
    def calculate_payout(bet_amount: int, odds: float) -> int:
        """Calculate potential payout for a bet."""
        return int(bet_amount * odds)


# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

async def initialize_sport_betting_tables(db_helpers):
    """Initialize all sport betting database tables."""
    try:
        if not db_helpers.db_pool:
            logger.error("Database pool not available")
            return False
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            logger.error("Could not get database connection")
            return False
        
        cursor = conn.cursor()
        try:
            # Table for cached matches
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sport_matches (
                    match_id VARCHAR(64) PRIMARY KEY,
                    league_id VARCHAR(32) NOT NULL,
                    provider VARCHAR(32) NOT NULL,
                    home_team VARCHAR(128) NOT NULL,
                    away_team VARCHAR(128) NOT NULL,
                    home_team_short VARCHAR(8),
                    away_team_short VARCHAR(8),
                    home_score INT DEFAULT 0,
                    away_score INT DEFAULT 0,
                    status VARCHAR(32) NOT NULL DEFAULT 'scheduled',
                    match_time DATETIME NOT NULL,
                    matchday INT DEFAULT 1,
                    odds_home DECIMAL(5,2) DEFAULT 2.00,
                    odds_draw DECIMAL(5,2) DEFAULT 3.50,
                    odds_away DECIMAL(5,2) DEFAULT 3.00,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_league (league_id),
                    INDEX idx_status (status),
                    INDEX idx_match_time (match_time)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Table for user bets
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sport_bets (
                    bet_id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    match_id VARCHAR(64) NOT NULL,
                    bet_type VARCHAR(32) NOT NULL,
                    bet_outcome VARCHAR(32) NOT NULL,
                    bet_amount BIGINT NOT NULL,
                    odds_at_bet DECIMAL(5,2) NOT NULL,
                    potential_payout BIGINT NOT NULL,
                    status VARCHAR(32) NOT NULL DEFAULT 'pending',
                    actual_payout BIGINT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    settled_at TIMESTAMP NULL,
                    INDEX idx_user (user_id),
                    INDEX idx_match (match_id),
                    INDEX idx_status (status),
                    INDEX idx_created (created_at),
                    FOREIGN KEY (match_id) REFERENCES sport_matches(match_id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Table for betting statistics
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sport_betting_stats (
                    user_id BIGINT PRIMARY KEY,
                    total_bets INT DEFAULT 0,
                    total_wins INT DEFAULT 0,
                    total_losses INT DEFAULT 0,
                    total_wagered BIGINT DEFAULT 0,
                    total_won BIGINT DEFAULT 0,
                    total_lost BIGINT DEFAULT 0,
                    biggest_win BIGINT DEFAULT 0,
                    current_streak INT DEFAULT 0,
                    best_streak INT DEFAULT 0,
                    favorite_league VARCHAR(32),
                    last_bet_at TIMESTAMP NULL,
                    INDEX idx_wins (total_wins),
                    INDEX idx_wagered (total_wagered)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Table for match bet pools (for dynamic odds)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sport_bet_pools (
                    match_id VARCHAR(64) PRIMARY KEY,
                    pool_home BIGINT DEFAULT 0,
                    pool_draw BIGINT DEFAULT 0,
                    pool_away BIGINT DEFAULT 0,
                    total_bettors INT DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (match_id) REFERENCES sport_matches(match_id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            conn.commit()
            logger.info("Sport betting tables initialized successfully")
            return True
            
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        logger.error(f"Error initializing sport betting tables: {e}", exc_info=True)
        return False


async def get_or_update_match(db_helpers, match_data: Dict[str, Any]) -> bool:
    """Insert or update a match in the database."""
    try:
        if not db_helpers.db_pool:
            return False
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        try:
            # Calculate odds
            odds = OddsCalculator.calculate_match_odds(match_data)
            
            cursor.execute("""
                INSERT INTO sport_matches 
                (match_id, league_id, provider, home_team, away_team, home_team_short, 
                 away_team_short, home_score, away_score, status, match_time, matchday,
                 odds_home, odds_draw, odds_away)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    home_score = VALUES(home_score),
                    away_score = VALUES(away_score),
                    status = VALUES(status),
                    match_time = VALUES(match_time),
                    odds_home = VALUES(odds_home),
                    odds_draw = VALUES(odds_draw),
                    odds_away = VALUES(odds_away)
            """, (
                match_data["id"],
                match_data["league_id"],
                match_data["provider"],
                match_data["home_team"],
                match_data["away_team"],
                match_data.get("home_team_short", ""),
                match_data.get("away_team_short", ""),
                match_data.get("home_score", 0),
                match_data.get("away_score", 0),
                match_data["status"].value,
                match_data["match_time"],
                match_data.get("matchday", 1),
                odds["home"],
                odds["draw"],
                odds["away"]
            ))
            
            conn.commit()
            return True
            
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        logger.error(f"Error updating match: {e}", exc_info=True)
        return False


async def get_upcoming_matches(db_helpers, league_id: Optional[str] = None, limit: int = 10) -> List[Dict]:
    """Get upcoming matches that can be bet on."""
    try:
        if not db_helpers.db_pool:
            return []
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return []
        
        cursor = conn.cursor(dictionary=True)
        try:
            if league_id:
                cursor.execute("""
                    SELECT * FROM sport_matches 
                    WHERE status = 'scheduled' AND league_id = %s AND match_time > NOW()
                    ORDER BY match_time ASC
                    LIMIT %s
                """, (league_id, limit))
            else:
                cursor.execute("""
                    SELECT * FROM sport_matches 
                    WHERE status = 'scheduled' AND match_time > NOW()
                    ORDER BY match_time ASC
                    LIMIT %s
                """, (limit,))
            
            return cursor.fetchall()
            
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        logger.error(f"Error getting upcoming matches: {e}", exc_info=True)
        return []


async def get_match_from_db(db_helpers, match_id: str) -> Optional[Dict]:
    """Get a specific match from the database."""
    try:
        if not db_helpers.db_pool:
            return None
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return None
        
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM sport_matches WHERE match_id = %s", (match_id,))
            return cursor.fetchone()
            
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        logger.error(f"Error getting match: {e}", exc_info=True)
        return None


async def place_bet(db_helpers, user_id: int, match_id: str, bet_type: str, 
                    bet_outcome: str, amount: int, odds: float) -> Tuple[bool, str]:
    """Place a bet on a match."""
    try:
        if not db_helpers.db_pool:
            return False, "Database nicht verfügbar"
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return False, "Datenbankverbindung fehlgeschlagen"
        
        cursor = conn.cursor(dictionary=True)
        try:
            # Check if match is still open for betting
            cursor.execute("""
                SELECT * FROM sport_matches 
                WHERE match_id = %s AND status = 'scheduled' AND match_time > NOW()
            """, (match_id,))
            match = cursor.fetchone()
            
            if not match:
                return False, "Dieses Spiel ist nicht mehr für Wetten verfügbar"
            
            # Check if user already has a bet on this match
            cursor.execute("""
                SELECT bet_id FROM sport_bets 
                WHERE user_id = %s AND match_id = %s AND status = 'pending'
            """, (user_id, match_id))
            existing_bet = cursor.fetchone()
            
            if existing_bet:
                return False, "Du hast bereits eine Wette auf dieses Spiel platziert"
            
            # Calculate potential payout
            potential_payout = OddsCalculator.calculate_payout(amount, odds)
            
            # Insert bet
            cursor.execute("""
                INSERT INTO sport_bets 
                (user_id, match_id, bet_type, bet_outcome, bet_amount, odds_at_bet, potential_payout)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (user_id, match_id, bet_type, bet_outcome, amount, odds, potential_payout))
            
            # Update bet pool - use whitelist for column names to prevent SQL injection
            pool_columns = {"home": "pool_home", "draw": "pool_draw", "away": "pool_away"}
            pool_column = pool_columns.get(bet_outcome)
            if pool_column:
                cursor.execute(f"""
                    INSERT INTO sport_bet_pools (match_id, {pool_column}, total_bettors)
                    VALUES (%s, %s, 1)
                    ON DUPLICATE KEY UPDATE
                        {pool_column} = {pool_column} + %s,
                        total_bettors = total_bettors + 1
                """, (match_id, amount, amount))
            
            # Update user stats
            cursor.execute("""
                INSERT INTO sport_betting_stats (user_id, total_bets, total_wagered, last_bet_at)
                VALUES (%s, 1, %s, NOW())
                ON DUPLICATE KEY UPDATE
                    total_bets = total_bets + 1,
                    total_wagered = total_wagered + %s,
                    last_bet_at = NOW()
            """, (user_id, amount, amount))
            
            conn.commit()
            return True, f"Wette platziert! Potentieller Gewinn: {potential_payout} 🪙"
            
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        logger.error(f"Error placing bet: {e}", exc_info=True)
        return False, f"Fehler beim Platzieren der Wette: {str(e)}"


async def get_user_bets(db_helpers, user_id: int, status: Optional[str] = None, 
                        limit: int = 20) -> List[Dict]:
    """Get bets for a user."""
    try:
        if not db_helpers.db_pool:
            return []
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return []
        
        cursor = conn.cursor(dictionary=True)
        try:
            if status:
                cursor.execute("""
                    SELECT b.*, m.home_team, m.away_team, m.home_score, m.away_score,
                           m.match_time, m.status as match_status, m.league_id
                    FROM sport_bets b
                    JOIN sport_matches m ON b.match_id = m.match_id
                    WHERE b.user_id = %s AND b.status = %s
                    ORDER BY b.created_at DESC
                    LIMIT %s
                """, (user_id, status, limit))
            else:
                cursor.execute("""
                    SELECT b.*, m.home_team, m.away_team, m.home_score, m.away_score,
                           m.match_time, m.status as match_status, m.league_id
                    FROM sport_bets b
                    JOIN sport_matches m ON b.match_id = m.match_id
                    WHERE b.user_id = %s
                    ORDER BY b.created_at DESC
                    LIMIT %s
                """, (user_id, limit))
            
            return cursor.fetchall()
            
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        logger.error(f"Error getting user bets: {e}", exc_info=True)
        return []


async def get_user_betting_stats(db_helpers, user_id: int) -> Optional[Dict]:
    """Get betting statistics for a user."""
    try:
        if not db_helpers.db_pool:
            return None
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return None
        
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM sport_betting_stats WHERE user_id = %s", (user_id,))
            return cursor.fetchone()
            
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        logger.error(f"Error getting betting stats: {e}", exc_info=True)
        return None


async def settle_match_bets(db_helpers, match_id: str, home_score: int, away_score: int) -> int:
    """
    Settle all bets for a finished match.
    Returns the number of bets settled.
    """
    try:
        if not db_helpers.db_pool:
            return 0
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return 0
        
        cursor = conn.cursor(dictionary=True)
        try:
            # Determine match outcome
            if home_score > away_score:
                winning_outcome = "home"
            elif home_score < away_score:
                winning_outcome = "away"
            else:
                winning_outcome = "draw"
            
            # Get all pending bets for this match
            cursor.execute("""
                SELECT * FROM sport_bets 
                WHERE match_id = %s AND status = 'pending'
            """, (match_id,))
            bets = cursor.fetchall()
            
            settled_count = 0
            
            for bet in bets:
                bet_outcome = bet["bet_outcome"]
                user_id = bet["user_id"]
                bet_amount = bet["bet_amount"]
                potential_payout = bet["potential_payout"]
                
                if bet_outcome == winning_outcome:
                    # Winner!
                    actual_payout = potential_payout
                    status = "won"
                    
                    # Update user stats
                    cursor.execute("""
                        UPDATE sport_betting_stats 
                        SET total_wins = total_wins + 1,
                            total_won = total_won + %s,
                            biggest_win = GREATEST(biggest_win, %s),
                            current_streak = current_streak + 1,
                            best_streak = GREATEST(best_streak, current_streak + 1)
                        WHERE user_id = %s
                    """, (actual_payout, actual_payout, user_id))
                else:
                    # Loser
                    actual_payout = 0
                    status = "lost"
                    
                    # Update user stats
                    cursor.execute("""
                        UPDATE sport_betting_stats 
                        SET total_losses = total_losses + 1,
                            total_lost = total_lost + %s,
                            current_streak = 0
                        WHERE user_id = %s
                    """, (bet_amount, user_id))
                
                # Update bet status
                cursor.execute("""
                    UPDATE sport_bets 
                    SET status = %s, actual_payout = %s, settled_at = NOW()
                    WHERE bet_id = %s
                """, (status, actual_payout, bet["bet_id"]))
                
                settled_count += 1
            
            # Update match status
            cursor.execute("""
                UPDATE sport_matches 
                SET status = 'finished', home_score = %s, away_score = %s
                WHERE match_id = %s
            """, (home_score, away_score, match_id))
            
            conn.commit()
            return settled_count
            
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        logger.error(f"Error settling bets: {e}", exc_info=True)
        return 0


async def get_betting_leaderboard(db_helpers, limit: int = 10) -> List[Dict]:
    """Get the top bettors by winnings."""
    try:
        if not db_helpers.db_pool:
            return []
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return []
        
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT s.*, p.display_name
                FROM sport_betting_stats s
                LEFT JOIN players p ON s.user_id = p.discord_id
                WHERE s.total_bets > 0
                ORDER BY (s.total_won - s.total_lost) DESC
                LIMIT %s
            """, (limit,))
            
            return cursor.fetchall()
            
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        logger.error(f"Error getting leaderboard: {e}", exc_info=True)
        return []


# ============================================================================
# MATCH DATA SYNC
# ============================================================================

async def sync_league_matches(db_helpers, league_id: str) -> int:
    """
    Sync matches from API to database for a league.
    Returns number of matches synced.
    """
    league_config = LEAGUES.get(league_id)
    if not league_config:
        logger.warning(f"Unknown league: {league_id}")
        return 0
    
    provider = APIProviderFactory.get_provider(league_config["provider"])
    
    try:
        matches = await provider.get_matches(league_config["api_id"])
        
        synced = 0
        for match in matches:
            match["league_id"] = league_id
            if await get_or_update_match(db_helpers, match):
                synced += 1
        
        logger.info(f"Synced {synced} matches for {league_config['name']}")
        return synced
        
    except Exception as e:
        logger.error(f"Error syncing matches for {league_id}: {e}", exc_info=True)
        return 0


async def sync_all_leagues(db_helpers) -> Dict[str, int]:
    """Sync matches for all configured leagues."""
    results = {}
    
    for league_id in LEAGUES.keys():
        results[league_id] = await sync_league_matches(db_helpers, league_id)
        # Small delay to avoid rate limiting
        await asyncio.sleep(1)
    
    return results


# ============================================================================
# UI HELPER FUNCTIONS
# ============================================================================

def format_match_time(match_time: datetime) -> str:
    """Format match time for display."""
    if isinstance(match_time, str):
        match_time = datetime.fromisoformat(match_time.replace("Z", "+00:00"))
    
    # Convert to local time display (German format)
    return match_time.strftime("%d.%m. %H:%M")


def get_league_emoji(league_id: str) -> str:
    """Get emoji for a league."""
    return LEAGUES.get(league_id, {}).get("emoji", "⚽")


def get_league_name(league_id: str) -> str:
    """Get display name for a league."""
    return LEAGUES.get(league_id, {}).get("name", league_id.upper())


def format_odds_display(odds: float) -> str:
    """Format odds for display."""
    return f"{odds:.2f}x"


def get_outcome_emoji(outcome: str) -> str:
    """Get emoji for a bet outcome."""
    emojis = {
        "home": "🏠",
        "draw": "🤝",
        "away": "✈️",
        "won": "✅",
        "lost": "❌",
        "pending": "⏳"
    }
    return emojis.get(outcome, "❓")


def create_match_embed(match: Dict, show_odds: bool = True) -> discord.Embed:
    """Create an embed for displaying a match."""
    league_id = match.get("league_id", "bl1")
    league_emoji = get_league_emoji(league_id)
    league_name = get_league_name(league_id)
    
    home_team = match.get("home_team", "Unknown")
    away_team = match.get("away_team", "Unknown")
    
    # Title with league
    embed = discord.Embed(
        title=f"{league_emoji} {home_team} vs {away_team}",
        color=discord.Color.green()
    )
    
    # Match info
    match_time = match.get("match_time")
    if isinstance(match_time, str):
        match_time = datetime.fromisoformat(match_time.replace("Z", "+00:00"))
    
    status = match.get("status", "scheduled")
    if isinstance(status, MatchStatus):
        status = status.value
    
    if status == "finished":
        embed.color = discord.Color.greyple()
        score_text = f"**{match.get('home_score', 0)} : {match.get('away_score', 0)}**"
        embed.add_field(name="🏁 Endergebnis", value=score_text, inline=False)
    elif status == "live":
        embed.color = discord.Color.red()
        score_text = f"**{match.get('home_score', 0)} : {match.get('away_score', 0)}**"
        embed.add_field(name="🔴 LIVE", value=score_text, inline=False)
    else:
        embed.add_field(name="⏰ Anstoß", value=format_match_time(match_time), inline=True)
    
    embed.add_field(name="🏆 Liga", value=league_name, inline=True)
    
    if match.get("matchday"):
        embed.add_field(name="📅 Spieltag", value=str(match.get("matchday")), inline=True)
    
    # Show odds if available and match is upcoming
    if show_odds and status == "scheduled":
        odds_home = match.get("odds_home", 2.0)
        odds_draw = match.get("odds_draw", 3.5)
        odds_away = match.get("odds_away", 3.0)
        
        odds_text = (
            f"🏠 **Heim**: {format_odds_display(odds_home)}\n"
            f"🤝 **Unentschieden**: {format_odds_display(odds_draw)}\n"
            f"✈️ **Auswärts**: {format_odds_display(odds_away)}"
        )
        embed.add_field(name="📊 Quoten", value=odds_text, inline=False)
    
    embed.set_footer(text=f"Match ID: {match.get('match_id', match.get('id', 'N/A'))}")
    
    return embed


def create_bet_embed(bet: Dict, user_display_name: str) -> discord.Embed:
    """Create an embed for displaying a bet."""
    status = bet.get("status", "pending")
    
    # Color based on status
    if status == "won":
        color = discord.Color.gold()
        status_emoji = "✅"
    elif status == "lost":
        color = discord.Color.red()
        status_emoji = "❌"
    else:
        color = discord.Color.blue()
        status_emoji = "⏳"
    
    embed = discord.Embed(
        title=f"{status_emoji} Wettschein",
        color=color
    )
    
    # Match info
    home_team = bet.get("home_team", "Unknown")
    away_team = bet.get("away_team", "Unknown")
    embed.add_field(
        name="⚽ Spiel",
        value=f"{home_team} vs {away_team}",
        inline=False
    )
    
    # Bet details
    outcome = bet.get("bet_outcome", "home")
    outcome_names = {"home": "Heimsieg", "draw": "Unentschieden", "away": "Auswärtssieg"}
    
    embed.add_field(
        name="🎯 Tipp",
        value=f"{get_outcome_emoji(outcome)} {outcome_names.get(outcome, outcome)}",
        inline=True
    )
    
    embed.add_field(
        name="💰 Einsatz",
        value=f"{bet.get('bet_amount', 0)} 🪙",
        inline=True
    )
    
    embed.add_field(
        name="📊 Quote",
        value=format_odds_display(bet.get("odds_at_bet", 1.0)),
        inline=True
    )
    
    if status == "pending":
        embed.add_field(
            name="💎 Pot. Gewinn",
            value=f"{bet.get('potential_payout', 0)} 🪙",
            inline=True
        )
    else:
        embed.add_field(
            name="💵 Auszahlung",
            value=f"{bet.get('actual_payout', 0)} 🪙",
            inline=True
        )
    
    # Match result if settled
    match_status = bet.get("match_status", "scheduled")
    if match_status == "finished":
        embed.add_field(
            name="🏁 Ergebnis",
            value=f"{bet.get('home_score', 0)} : {bet.get('away_score', 0)}",
            inline=True
        )
    
    return embed


def create_stats_embed(stats: Dict, user_display_name: str) -> discord.Embed:
    """Create an embed for displaying user betting statistics."""
    embed = discord.Embed(
        title=f"📊 Wettstatistik - {user_display_name}",
        color=discord.Color.blue()
    )
    
    if not stats:
        embed.description = "Noch keine Wetten platziert!"
        return embed
    
    total_bets = stats.get("total_bets", 0)
    total_wins = stats.get("total_wins", 0)
    total_losses = stats.get("total_losses", 0)
    total_wagered = stats.get("total_wagered", 0)
    total_won = stats.get("total_won", 0)
    total_lost = stats.get("total_lost", 0)
    
    # Win rate
    win_rate = (total_wins / total_bets * 100) if total_bets > 0 else 0
    
    # Profit/Loss
    profit = total_won - total_lost
    profit_emoji = "📈" if profit >= 0 else "📉"
    
    embed.add_field(
        name="🎫 Wetten",
        value=f"Gesamt: **{total_bets}**\nGewonnen: **{total_wins}** ✅\nVerloren: **{total_losses}** ❌",
        inline=True
    )
    
    embed.add_field(
        name="📊 Statistiken",
        value=f"Gewinnrate: **{win_rate:.1f}%**\nStreak: **{stats.get('current_streak', 0)}** 🔥\nBest: **{stats.get('best_streak', 0)}**",
        inline=True
    )
    
    embed.add_field(
        name="💰 Finanzen",
        value=f"Eingesetzt: **{total_wagered}** 🪙\nGewonnen: **{total_won}** 🪙\n{profit_emoji} Bilanz: **{profit:+d}** 🪙",
        inline=True
    )
    
    if stats.get("biggest_win", 0) > 0:
        embed.add_field(
            name="🏆 Größter Gewinn",
            value=f"**{stats.get('biggest_win', 0)}** 🪙",
            inline=True
        )
    
    return embed


def create_leaderboard_embed(leaderboard: List[Dict]) -> discord.Embed:
    """Create an embed for the betting leaderboard."""
    embed = discord.Embed(
        title="🏆 Wett-Bestenliste",
        description="Top-Wetter nach Gewinn",
        color=discord.Color.gold()
    )
    
    if not leaderboard:
        embed.description = "Noch keine Daten verfügbar!"
        return embed
    
    medals = ["🥇", "🥈", "🥉"]
    
    for i, entry in enumerate(leaderboard[:10]):
        medal = medals[i] if i < 3 else f"`{i + 1}.`"
        name = entry.get("display_name", f"User {entry.get('user_id', 'Unknown')}")
        profit = entry.get("total_won", 0) - entry.get("total_lost", 0)
        win_rate = (entry.get("total_wins", 0) / entry.get("total_bets", 1)) * 100
        
        value = f"Bilanz: **{profit:+d}** 🪙 | Gewinnrate: **{win_rate:.0f}%**"
        embed.add_field(
            name=f"{medal} {name}",
            value=value,
            inline=False
        )
    
    return embed


def create_matches_list_embed(matches: List[Dict], league_id: Optional[str] = None, page: int = 1, total_pages: int = 1) -> discord.Embed:
    """Create an embed showing a list of matches."""
    if league_id:
        league_name = get_league_name(league_id)
        league_emoji = get_league_emoji(league_id)
        title = f"{league_emoji} {league_name} - Kommende Spiele"
    else:
        title = "⚽ Kommende Spiele"
    
    embed = discord.Embed(
        title=title,
        color=discord.Color.blue()
    )
    
    if not matches:
        embed.description = "Keine kommenden Spiele gefunden.\n\nVersuche `/football sync` um Spieldaten zu aktualisieren."
        return embed
    
    for i, match in enumerate(matches[:5], start=1):  # Show max 5 per page
        home_team = match.get("home_team", "Unknown")
        away_team = match.get("away_team", "Unknown")
        match_time = match.get("match_time")
        match_id = match.get("match_id", "N/A")
        
        # Format time
        if isinstance(match_time, str):
            try:
                match_time = datetime.fromisoformat(match_time.replace("Z", "+00:00"))
            except ValueError:
                match_time = None
        
        time_str = format_match_time(match_time) if match_time else "TBD"
        
        # Get odds
        odds_home = match.get("odds_home", 2.0)
        odds_draw = match.get("odds_draw", 3.5)
        odds_away = match.get("odds_away", 3.0)
        
        match_league = match.get("league_id", "bl1")
        match_emoji = get_league_emoji(match_league)
        
        field_value = (
            f"⏰ **{time_str}**\n"
            f"📊 `1: {odds_home:.2f}` | `X: {odds_draw:.2f}` | `2: {odds_away:.2f}`\n"
            f"🆔 `{match_id}`"
        )
        
        embed.add_field(
            name=f"{match_emoji} {home_team} vs {away_team}",
            value=field_value,
            inline=False
        )
    
    embed.set_footer(text=f"Seite {page}/{total_pages} • Nutze /bet <match_id> <einsatz> <tipp> zum Wetten")
    
    return embed
