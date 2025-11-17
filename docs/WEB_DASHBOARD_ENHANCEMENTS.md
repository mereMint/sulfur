# Web Dashboard Enhancement - Feature Documentation

## Overview
This document describes the enhancements made to the Sulfur Bot Web Dashboard to improve monitoring, analytics, and control capabilities.

## New Features

### 1. Enhanced AI Analytics Tab

**Location**: Main Dashboard → AI Analytics Tab

**Features**:
- **Token Usage by Model**: Displays AI usage grouped by model name
- **Expandable Details**: Click on any model row to see feature breakdown
- **Metrics Displayed**:
  - Total API calls per model
  - Input tokens (separate)
  - Output tokens (separate)
  - Estimated cost in USD
  - Breakdown by feature (chat, werwolf, wrapped, etc.)

**API Endpoint**: `GET /api/ai-usage?days=30`

**Response Structure**:
```json
{
  "status": "success",
  "by_model": {
    "gemini-2.5-flash": {
      "calls": 200,
      "input_tokens": 7000,
      "output_tokens": 4500,
      "cost": 0.115,
      "features": {
        "chat": {"calls": 150, "input_tokens": 5000, ...},
        "werwolf": {"calls": 50, "input_tokens": 2000, ...}
      }
    }
  },
  "by_feature": { ... },
  "summary": {
    "total_calls": 275,
    "total_tokens": 16500,
    "total_cost": 0.265
  }
}
```

**How to Use**:
1. Navigate to main dashboard
2. Click on "AI Analytics" tab
3. View summary cards for total calls and tokens
4. Click on any model row (blue background) to expand/collapse feature details
5. Tab auto-loads data when opened

---

### 2. Maintenance Activity Tab

**Location**: Main Dashboard → Maintenance Tab

**Features**:
- Displays recent maintenance script activity
- Shows last 5 maintenance log files
- Highlights key activities:
  - Git updates (green)
  - Backups (blue/cyan)
  - Restarts (yellow/orange)
  - Errors (red)
- Manual refresh button

**API Endpoint**: `GET /api/maintenance/logs`

**Response Structure**:
```json
{
  "status": "success",
  "logs": [
    {
      "filename": "maintenance_2025-11-17_23-00-00.log",
      "timestamp": "2025-11-17_23-00-00",
      "activities": [
        "[2025-11-17 23:00:01] Checking for updates...",
        "[2025-11-17 23:00:05] Git pull completed",
        "[2025-11-17 23:15:00] Database backup created"
      ]
    }
  ]
}
```

**How to Use**:
1. Click on "Maintenance" tab
2. View recent maintenance operations
3. Click "Refresh" to reload latest logs
4. Color coding helps identify activity types

---

### 3. Enhanced Live Console with Bot Output Categories

**Location**: Main Dashboard → Live Console Tab

**New Features**:
- **Feature Badges**: Logs automatically tagged with colored badges
  - 🔵 Chat - Blue badge
  - 🔴 Werwolf - Red badge
  - 🟢 Wrapped - Green badge
  - 🟡 Admin - Yellow badge
  - 🔷 Leveling - Primary badge
  - ⚫ Economy - Secondary badge

- **Triple Filtering System**:
  1. **Log Level Filter**: All, Info, Warnings, Errors
  2. **Feature Filter**: All, Chat, Werwolf, Wrapped, Admin
  3. **Text Search**: Real-time search box

- **Enhanced Controls**:
  - Pause/Resume log streaming
  - Clear console
  - Auto-scroll toggle
  - Search box for text filtering

**How to Use**:
1. **Filter by Level**: Click level buttons (All, Info, Warning, Error)
2. **Filter by Feature**: Click feature buttons (Chat, Werwolf, etc.)
3. **Search**: Type in search box for instant filtering
4. **Combine Filters**: All three filters work together
   - Example: Show only "Error" level logs for "Werwolf" feature containing "timeout"

**Implementation Details**:
- Badges are added in real-time as logs stream
- Keywords detected: werwolf, wrapped, admin, chat, level, economy
- Filtering is client-side for instant response
- All filters are combinable

---

### 4. Verified Control Buttons

**Location**: Main Dashboard → Bot Status & Controls

All buttons tested and functional:

1. **Restart Bot** ✅
   - Creates `restart.flag` file
   - Maintenance script detects and restarts bot
   - Response time: ~15 seconds

2. **Stop Bot** ✅
   - Creates `stop.flag` file
   - Stops bot and maintenance script
   - Clean shutdown

3. **Update from Git** ✅
   - Triggers git pull
   - Updates codebase
   - Creates restart flag

4. **Sync DB** ✅
   - Syncs database schema
   - Handled by maintenance script

**API Endpoints**:
- `POST /api/restart-bot`
- `POST /api/stop-bot`
- `POST /api/update-bot`
- `POST /api/sync-db`

---

### 5. Additional API Endpoints

**Recent Logs API**:
```
GET /api/logs/recent?level=error&limit=100
```
Returns recent log entries with filtering

**AI Dashboard Page**:
```
GET /ai_dashboard
```
Full-page AI analytics with charts and detailed statistics

---

## Usage Examples

### Example 1: Find All Werwolf Errors
1. Go to Live Console tab
2. Click "Errors" button (log level)
3. Click "Werwolf" button (feature)
4. View only Werwolf-related errors

### Example 2: Monitor AI Costs
1. Go to AI Analytics tab
2. View summary cards for total cost
3. Click on any model to see feature breakdown
4. Identify which features are most expensive

### Example 3: Check Maintenance History
1. Go to Maintenance tab
2. Scroll through recent maintenance logs
3. Look for green-colored git updates
4. Verify backup completion (cyan/blue)

### Example 4: Search for Specific User Activity
1. Go to Live Console
2. Type username in search box
3. Optionally filter by feature (e.g., "Chat")
4. View all activity for that user

---

## Technical Implementation

### Backend Changes (web_dashboard.py)
1. Enhanced `/api/ai-usage` endpoint with grouping logic
2. Added `/api/maintenance/logs` endpoint
3. Added `/api/logs/recent` endpoint
4. Enhanced log streaming with feature badge injection
5. All control button endpoints verified

### Frontend Changes (web/index.html)
1. Updated AI Analytics tab with expandable tables
2. Added new Maintenance tab
3. Enhanced console with dual filter system
4. Added search functionality
5. Improved responsive layout

### Database Integration
- Uses existing `ai_model_usage` table
- No schema changes required
- Queries optimized for grouping

---

## Testing

All features tested with:
- Mock database connections
- Flask test client
- Real web dashboard startup
- API endpoint verification

Test Results: ✅ 4/4 tests passed
- AI Usage API ✅
- Maintenance Logs API ✅
- Bot Status API ✅
- Control Buttons ✅

---

## Browser Compatibility

Tested with modern browsers supporting:
- ES6 JavaScript
- CSS Flexbox
- Bootstrap 5
- WebSocket connections

---

## Performance Notes

- Log filtering is client-side (instant)
- AI analytics loaded on-demand when tab opened
- Maintenance logs limited to last 5 files
- Console limited to 500 lines for performance
- WebSocket for efficient real-time updates

---

## Security Considerations

- No sensitive data exposed in logs
- Control buttons use flag files (safe)
- No direct process manipulation
- Database credentials from environment variables
- All API endpoints have error handling

---

## Future Enhancements

Possible additions:
- Export logs to file
- AI cost charts/graphs
- Real-time user activity feed
- Advanced log filtering (regex)
- Dashboard themes
- Mobile-responsive improvements

---

## Support

For issues or questions:
1. Check maintenance logs for errors
2. Verify bot status is "Running"
3. Check browser console for JavaScript errors
4. Review API endpoint responses

---

Last Updated: 2025-11-17
