# OpenLigaDB Integration Guide

## Overview

The Sulfur Discord Bot includes a comprehensive integration with the OpenLigaDB API, providing free access to football (soccer) data from German leagues without requiring an API key.

## Supported Leagues

| League ID | League Name | Country | Emoji |
|-----------|-------------|---------|-------|
| `bl1` | Bundesliga | Germany | 🇩🇪 |
| `bl2` | 2. Bundesliga | Germany | 🇩🇪 |
| `dfb` | DFB-Pokal | Germany | 🏆 |

## API Endpoints

The integration supports the following OpenLigaDB API endpoints:

### Match Data

| Method | Endpoint | Description |
|--------|----------|-------------|
| `get_matches(league_id, matchday)` | `/getmatchdata/{league}/{season}/{matchday}` | Get matches for a specific matchday |
| `get_matches_by_season(league_id, season)` | `/getmatchdata/{league}/{season}` | Get all matches for a season |
| `get_match(match_id)` | `/getmatchdata/{matchid}` | Get a specific match by ID |
| `get_upcoming_matches(league_id, num_matchdays)` | Multiple calls | Get matches from current and upcoming matchdays |

### League Information

| Method | Endpoint | Description |
|--------|----------|-------------|
| `get_current_matchday(league_id)` | `/getcurrentgroup/{league}` | Get the current matchday number |
| `get_available_groups(league_id, season)` | `/getavailablegroups/{league}/{season}` | Get all matchdays for a season |
| `get_available_leagues()` | `/getavailableleagues` | Get all available leagues |

### Team Data

| Method | Endpoint | Description |
|--------|----------|-------------|
| `get_available_teams(league_id, season)` | `/getavailableteams/{league}/{season}` | Get all teams in a league |
| `get_last_match_by_team(league_id, team_id)` | `/getlastmatchbyleagueteam/{leagueid}/{teamid}` | Get last match for a team |
| `get_next_match_by_team(league_id, team_id)` | `/getnextmatchbyleagueteam/{leagueid}/{teamid}` | Get next match for a team |

### Statistics

| Method | Endpoint | Description |
|--------|----------|-------------|
| `get_league_table(league_id, season)` | `/getbltable/{league}/{season}` | Get league standings |
| `get_goal_scorers(league_id, season)` | `/getgoalgetters/{league}/{season}` | Get top scorers |

## Usage Examples

### Basic Usage

```python
from modules.sport_betting import OpenLigaDBProvider

# Create provider instance
provider = OpenLigaDBProvider()

# Get current matchday
matchday = await provider.get_current_matchday("bl1")
print(f"Current Bundesliga matchday: {matchday}")

# Get matches for current matchday
matches = await provider.get_matches("bl1", matchday)
for match in matches:
    print(f"{match['home_team']} vs {match['away_team']}")

# Clean up
await provider.close()
```

### Using the Factory Pattern

```python
from modules.sport_betting import APIProviderFactory

# Get the OpenLigaDB provider through the factory
provider = APIProviderFactory.get_provider("openligadb")

# Use the provider
table = await provider.get_league_table("bl1")
for entry in table[:5]:
    print(f"{entry['position']}. {entry['team_name']} - {entry['points']} pts")
```

### Getting League Standings

```python
# Get current Bundesliga standings
standings = await provider.get_league_table("bl1")

for entry in standings:
    print(f"{entry['position']:2}. {entry['team_name']:25} "
          f"P:{entry['matches']:2} W:{entry['won']:2} D:{entry['draw']:2} L:{entry['lost']:2} "
          f"GD:{entry['goal_diff']:+3} Pts:{entry['points']:2}")
```

### Getting Top Scorers

```python
# Get Bundesliga top scorers
scorers = await provider.get_goal_scorers("bl1")

for scorer in scorers[:10]:
    print(f"{scorer['rank']:2}. {scorer['player_name']:25} - {scorer['goals']} goals")
```

## Data Formats

### Match Object

```python
{
    "id": "12345",
    "home_team": "FC Bayern München",
    "away_team": "Borussia Dortmund",
    "home_team_short": "FCB",
    "away_team_short": "BVB",
    "home_logo": "https://...",
    "away_logo": "https://...",
    "home_score": 2,
    "away_score": 1,
    "status": MatchStatus.FINISHED,
    "match_time": datetime(...),
    "matchday": 15,
    "league_id": "bl1",
    "provider": "openligadb"
}
```

### Team Object

```python
{
    "team_id": 40,
    "team_name": "FC Bayern München",
    "short_name": "Bayern",
    "team_icon_url": "https://...",
    "team_group_name": ""
}
```

### Standings Entry

```python
{
    "position": 1,
    "team_id": 40,
    "team_name": "FC Bayern München",
    "short_name": "Bayern",
    "team_icon_url": "https://...",
    "matches": 15,
    "won": 12,
    "draw": 2,
    "lost": 1,
    "goals": 45,
    "goals_against": 12,
    "goal_diff": 33,
    "points": 38
}
```

### Top Scorer Entry

```python
{
    "rank": 1,
    "player_id": 123,
    "player_name": "Harry Kane",
    "goals": 15,
    "team_id": 40,
    "team_name": "FC Bayern München"
}
```

## Caching

The integration includes built-in caching to minimize API calls:

| Data Type | Cache Duration |
|-----------|----------------|
| Match data | 5 minutes |
| Current matchday | 30 minutes |
| League table | 1 hour |
| Teams | 24 hours |

You can clear the cache manually:

```python
from modules.sport_betting import clear_api_cache, get_api_cache_stats

# Clear all cached data
clear_api_cache()

# Get cache statistics
stats = get_api_cache_stats()
print(f"Cache entries: {stats['total_entries']}")
```

## Error Handling

The provider includes robust error handling:

- **Retry logic**: Failed requests are retried up to 3 times with exponential backoff
- **Rate limiting**: Requests are spaced 0.3 seconds apart to avoid overwhelming the API
- **Timeout handling**: Requests timeout after 15 seconds
- **Graceful degradation**: Returns empty lists/None instead of raising exceptions

## Season Calculation

The season year is automatically calculated based on the current date:

- If the current month is August or later, the season year is the current year
- If the current month is before August, the season year is the previous year

For example (if current date is November):
- November 2024 → Season 2024 (2024/2025)
- March 2024 → Season 2023 (2023/2024)
- August 2024 → Season 2024 (2024/2025)

## Discord Bot Commands

The sport betting feature is accessible through the `/sportbets` command, which provides:

- League selection
- Match viewing with odds
- Bet placement (winner, over/under, BTTS)
- Bet history and statistics
- Leaderboards

See the main bot documentation for more details on using the betting commands.

## API Documentation

Official OpenLigaDB API documentation: https://api.openligadb.de/index.html

## Troubleshooting

### Common Issues

1. **No matches returned**: The API might not have data for future matchdays yet
2. **Empty standings**: Check if the season has started
3. **Network errors**: Ensure the bot has internet access to api.openligadb.de

### Debugging

Enable debug logging to see API calls:

```python
import logging
logging.getLogger("modules.sport_betting").setLevel(logging.DEBUG)
```
