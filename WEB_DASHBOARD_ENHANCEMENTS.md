# Web Dashboard Enhancement Documentation

## Overview
This document describes the major enhancements made to the Sulfur Bot web dashboard to make it more advanced, useful, and comprehensive.

## New Features

### 1. RPG Skill Tree Visualization
**Location**: `/rpg_admin` → Skills tab

**Features**:
- Visual display of all three skill paths (Warrior, Rogue, Mage)
- Interactive skill cards showing:
  - Skill name and type (active/passive)
  - Description
  - Cost in skill points
  - Prerequisites
- Click on any skill to see detailed modal with:
  - Full effects breakdown
  - Path information
  - Dependency tree
- Topological sorting ensures skills display in proper dependency order

**API Endpoint**: `GET /api/rpg/skill_tree`

### 2. Economy Dashboard
**Location**: `/economy`

**Features**:
- Real-time economy statistics:
  - Total coins in circulation
  - Active users with wealth
  - Average wealth per user
  - Market capitalization
- Top 10 richest users leaderboard
- Transaction activity breakdown (7 days):
  - By transaction type
  - Total count and volume
- Recent transactions viewer (last 20)
- Stock market overview (if available):
  - All stocks with current prices
  - Top stock holders
- Auto-refresh every 30 seconds
- Beautiful gold-themed UI

**API Endpoints**:
- `GET /api/economy/stats` - Main economy statistics
- `GET /api/economy/stocks` - Stock market data

### 3. Games Dashboard
**Location**: `/games`

**Features**:
- Game statistics for all mini-games:
  - Werwolf: Total games and players
  - Detective: Total cases and players
  - Wordle: Total games and players
  - Casino: Breakdown by game type
- Interactive leaderboards:
  - Detective: Cases solved, accuracy, streaks
  - Wordle: Games won, average attempts
- Casino breakdown:
  - Blackjack games played
  - Roulette games played
  - Mines games played
- Auto-refresh every minute

**API Endpoints**:
- `GET /api/games/stats` - Overall game statistics
- `GET /api/games/<game_type>/leaderboard` - Game-specific leaderboards

### 4. Enhanced Database Viewer
**Location**: `/database`

**Features**:
- **Data Export**:
  - Export to CSV format
  - Export to JSON format
  - Respects current search filter
- **Search & Filter**:
  - Real-time search across all columns
  - Instant results without page reload
- **Column Sorting**:
  - Click column headers to sort
  - Smart sorting (numbers vs strings)
  - Visual sort direction indicators
- **Better UI**:
  - Sticky table headers
  - Improved pagination controls
  - Better mobile responsiveness
  - Color-coded data

### 5. System Health Dashboard
**Location**: `/system`

**Features**:
- **Bot Status**:
  - Current status with color coding
  - Uptime tracking
  - Visual health indicator
- **Memory Monitoring**:
  - Process memory usage
  - System memory usage
  - Progress bars with thresholds
- **CPU Monitoring**:
  - Process CPU usage
  - System-wide CPU usage
- **Disk Usage**:
  - Storage consumption
  - Available space
  - Warning thresholds
- **Database Health**:
  - Connection status
  - Pool size information
- **API Usage (30 days)**:
  - Total API calls
  - Total tokens consumed
  - Estimated cost
  - Current provider
- **Log Analytics**:
  - Error count from recent logs
  - Warning count
- Auto-refresh every 10 seconds

**API Endpoints**:
- `GET /api/system/health` - System metrics
- `GET /api/system/api_quotas` - API usage and quotas

**Requirements**: Requires `psutil` package for system monitoring

### 6. Enhanced Main Dashboard
**Location**: `/` (Home)

**Features**:
- **Quick Stats Cards**:
  - Bot status
  - AI calls (30 days)
  - Total wealth in economy
  - Total games played
- Auto-refreshing metrics
- Better visual hierarchy
- Color-coded status indicators

## Technical Implementation

### New Dependencies
- `psutil` - For system metrics (optional, graceful degradation if not available)

### Database Tables Used
- `user_stats` - User economy data
- `transactions` - Economy transactions
- `stocks`, `stocks_owned` - Stock market
- `werwolf_games`, `werwolf_user_stats` - Werwolf game data
- `detective_games`, `detective_user_stats` - Detective game data
- `wordle_games` - Wordle game data
- `blackjack_games`, `roulette_games`, `mines_games` - Casino games
- `api_usage` - AI API usage tracking
- All RPG tables - For skill tree and items

### API Enhancements
All new API endpoints follow REST conventions:
- Return JSON responses
- Include error handling
- Use appropriate HTTP status codes
- Support pagination where applicable

### Frontend Technologies
- Bootstrap 5.3.3 for UI components
- Bootstrap Icons 1.11.x
- Vanilla JavaScript (no additional frameworks)
- Socket.IO for real-time log streaming
- Client-side export functionality (no server load)

## Navigation Updates

New navigation items added to main menu:
1. **Economy** (`/economy`) - Economy dashboard
2. **Games** (`/games`) - Games statistics
3. **System** (`/system`) - System health monitoring

All navigation items maintain active state highlighting and responsive design.

## Performance Considerations

### Auto-Refresh Intervals
- Main dashboard quick stats: 30 seconds
- Bot status: 5 seconds
- System health: 10 seconds
- Economy stats: 30 seconds
- Games stats: 60 seconds

### Optimization
- Client-side filtering and sorting (no server load)
- Pagination for large datasets
- Lazy loading of tab content
- Efficient database queries with LIMIT clauses
- Connection pooling for database access

## User Experience Improvements

1. **Consistent Theming**: All new pages use the existing dark theme with gradient accents
2. **Visual Feedback**: Progress bars, color coding, and icons for better data visualization
3. **Responsive Design**: All pages work on mobile, tablet, and desktop
4. **Accessibility**: Proper ARIA labels and semantic HTML
5. **Loading States**: Spinners and skeleton screens for better UX

## Future Enhancements

Potential additions for future iterations:
- User management dashboard
- Advanced charts and graphs (Chart.js integration)
- Real-time notifications system
- Custom dashboard widgets
- Data visualization for trends over time
- Export scheduler for regular backups
- More granular user permissions

## Troubleshooting

### System Health Shows Error
- Ensure `psutil` is installed: `pip install psutil`
- Check if the bot has appropriate permissions

### Database Export Not Working
- Check browser console for errors
- Ensure table has data
- Try with a smaller dataset first

### Stats Not Loading
- Check database connection
- Verify tables exist and have data
- Check browser console for API errors
- Ensure maintenance scripts aren't blocking database access

## Conclusion

These enhancements transform the web dashboard from a basic monitoring tool into a comprehensive administration and analytics platform, providing valuable insights into all aspects of the bot's operation.
