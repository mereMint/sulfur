# Web Dashboard Visual Guide

## Dashboard Layout

### Main Dashboard Page (index.html)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    SULFUR BOT WEB DASHBOARD                              │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────────────────┬──────────────────────────────────┐  │
│  │ Bot Status & Controls          │  Quick Settings                  │  │
│  ├────────────────────────────────┤                                  │  │
│  │ Status: Running [●]            │  AI Model:                       │  │
│  │                                │  Provider: [Gemini ▼]           │  │
│  │ [↻ Restart] [■ Stop]          │  Model: [gemini-2.5-flash ▼]    │  │
│  │ [⬇ Update] [💾 Sync DB]        │  [Apply Model Change]           │  │
│  │                                │                                  │  │
│  └────────────────────────────────┤  Temperature: 0.7                │  │
│                                   │  [-----|------] 0.7              │  │
│  ┌─ Tabs ────────────────────────┐│                                  │  │
│  │ [Live Console] [AI Analytics]  ││  Quick Links:                   │  │
│  │ [Maintenance] [Wrapped]        ││  [⚙ Config] [📊 DB] [📈 AI]     │  │
│  │ [Leaderboard] [Admin]          ││                                  │  │
│  ├────────────────────────────────┤│  System Info:                   │  │
│  │                                ││  PID: 12345                     │  │
│  │ === LIVE CONSOLE TAB ===       ││  Last Update: 2025-11-17 23:00  │  │
│  │                                ││  Current Model: gemini/2.5-flash│  │
│  │ Log Level:                     ││                                  │  │
│  │ [All] [Info] [Warning] [Error] │└──────────────────────────────────┘  │
│  │                                │                                      │
│  │ Feature:                       │                                      │
│  │ [All] [Chat] [Werwolf]        │                                      │
│  │ [Wrapped] [Admin]             │                                      │
│  │                                │                                      │
│  │ [Search: ________] [⏸ Pause]  │                                      │
│  │ [Clear] [Auto-scroll: ON]     │                                      │
│  │                                │                                      │
│  │ ┌─ Console Output ──────────┐ │                                      │
│  │ │ [Chat] User logged in     │ │                                      │
│  │ │ [Werwolf] Game started    │ │                                      │
│  │ │ [INFO] Bot ready          │ │                                      │
│  │ │ [Chat] Message sent       │ │                                      │
│  │ │ [Admin] Config reloaded   │ │                                      │
│  │ │ [Wrapped] Stats generated │ │                                      │
│  │ │ ...                        │ │                                      │
│  │ └────────────────────────────┘ │                                      │
│  └────────────────────────────────┘                                      │
└──────────────────────────────────────────────────────────────────────────┘
```

## AI Analytics Tab

```
┌──────────────────────────────────────────────────────────────────────────┐
│ AI Usage Statistics                                                      │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │ Total Calls  │  │ Total Tokens │  │ Total Cost   │                  │
│  │   1,250      │  │   45,000     │  │  $1.23       │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
│                                                                          │
│  Model / Feature    Calls   Input Tokens   Output Tokens   Cost (USD)  │
│  ───────────────────────────────────────────────────────────────────────│
│  📊 gemini-2.5-flash  800     25,000         15,000        $0.80       │
│    ↳ chat            600     20,000         12,000        $0.64       │
│    ↳ werwolf         150      4,000          2,500        $0.13       │
│    ↳ wrapped          50      1,000            500        $0.03       │
│                                                                          │
│  📊 gpt-4o-mini       450     12,000          8,000        $0.43       │
│    ↳ chat            400     11,000          7,500        $0.39       │
│    ↳ admin            50      1,000            500        $0.04       │
│                                                                          │
│  💡 Click on a model row to expand/collapse feature details             │
└──────────────────────────────────────────────────────────────────────────┘
```

## Maintenance Tab

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Maintenance Script Activity                                              │
├──────────────────────────────────────────────────────────────────────────┤
│ View recent maintenance operations, git updates, backups, and restarts   │
│                                                                          │
│  [↻ Refresh]                                                             │
│                                                                          │
│  ┌─ maintenance_2025-11-17_23-00-00.log ───────────────────────────────┐│
│  │ 2025-11-17_23-00-00                                                  ││
│  ├──────────────────────────────────────────────────────────────────────┤│
│  │ [2025-11-17 23:00:01] Starting maintenance script                   ││
│  │ [2025-11-17 23:00:02] Checking for updates...                       ││
│  │ [2025-11-17 23:00:05] Git pull completed (green)                    ││
│  │ [2025-11-17 23:15:00] Creating database backup... (cyan)            ││
│  │ [2025-11-17 23:15:03] Backup saved to backups/ (cyan)               ││
│  │ [2025-11-17 23:16:00] Restart signal detected (yellow)              ││
│  │ [2025-11-17 23:16:02] Stopping bot process... (yellow)              ││
│  │ [2025-11-17 23:16:05] Bot restarted successfully (yellow)           ││
│  └──────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  ┌─ maintenance_2025-11-17_22-00-00.log ───────────────────────────────┐│
│  │ 2025-11-17_22-00-00                                                  ││
│  ├──────────────────────────────────────────────────────────────────────┤│
│  │ [2025-11-17 22:00:01] Starting maintenance script                   ││
│  │ [2025-11-17 22:00:02] Checking for updates...                       ││
│  │ [2025-11-17 22:00:05] No updates available                          ││
│  │ ...                                                                  ││
│  └──────────────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────────┘
```

## Feature Badges in Console

The console now displays colored badges for easy identification:

```
Console Output with Badges:

[Chat] 2025-11-17 15:30:45 | User @john sent message in #general
      ^^^^
      Blue badge

[Werwolf] 2025-11-17 15:31:12 | Game started in #game-room
          ^^^^^^^^
          Red badge

[Wrapped] 2025-11-17 15:32:00 | Monthly stats generated for user @jane
          ^^^^^^^
          Green badge

[Admin] 2025-11-17 15:32:30 | Configuration reloaded
        ^^^^^
        Yellow badge

[Leveling] 2025-11-17 15:33:00 | User @bob reached level 15
           ^^^^^^^^
           Primary badge

[Economy] 2025-11-17 15:33:45 | User @alice purchased item
          ^^^^^^^
          Secondary badge
```

## Filtering Examples

### Example 1: View Only Werwolf Errors
```
Filters Applied:
- Log Level: [Error]
- Feature: [Werwolf]
- Search: (empty)

Result: Shows only error-level logs with Werwolf badge
```

### Example 2: Search for Specific User in Chat
```
Filters Applied:
- Log Level: [All]
- Feature: [Chat]
- Search: "@john"

Result: Shows all Chat feature logs mentioning @john
```

### Example 3: Find All Admin Commands
```
Filters Applied:
- Log Level: [All]
- Feature: [Admin]
- Search: "command"

Result: Shows all Admin feature logs containing "command"
```

## Color Coding

### Feature Badges
- **Chat**: Blue (`bg-info`)
- **Werwolf**: Red (`bg-danger`)
- **Wrapped**: Green (`bg-success`)
- **Admin**: Yellow (`bg-warning`)
- **Leveling**: Primary Blue (`bg-primary`)
- **Economy**: Gray (`bg-secondary`)

### Maintenance Activities
- **Git Updates**: Green text
- **Backups**: Cyan/Blue text
- **Restarts**: Yellow/Orange text
- **Errors**: Red text

## Button States

### Control Buttons
- **Default**: Outlined style
- **Success**: Green fill when action succeeds
- **Error**: Red fill when action fails
- **Active**: Solid color for active filters

### Filter Buttons
- **Active**: Solid background
- **Inactive**: Outlined style

## Responsive Design

The dashboard adjusts for different screen sizes:

**Desktop (≥1200px)**:
- Two-column layout
- All features visible
- Full button text

**Tablet (768px - 1199px)**:
- Single column layout
- Stacked components
- Abbreviated button text

**Mobile (<768px)**:
- Vertical stacking
- Icon-only buttons
- Collapsible sections

## Loading States

### AI Analytics Tab
```
┌──────────────────────────────────┐
│                                  │
│        ⟳ Loading...              │
│                                  │
└──────────────────────────────────┘
```

### Data Loaded
```
┌──────────────────────────────────┐
│  Total Calls: 1,250              │
│  [Table with data]               │
└──────────────────────────────────┘
```

## WebSocket Status

Connection indicator in console:
- ✅ Connected: Green indicator
- ⚠️ Connecting: Yellow indicator
- ❌ Disconnected: Red indicator

```
Console Status: [✅ Connected] Auto-scroll: ON
```

## Summary

The enhanced web dashboard provides:
1. **Visual Organization**: Color-coded badges and activities
2. **Powerful Filtering**: Triple-filter system for precise log viewing
3. **Real-time Updates**: WebSocket streaming with feature detection
4. **Comprehensive Analytics**: Detailed AI usage breakdown by model and feature
5. **Maintenance Visibility**: Track script activities and operations
6. **Full Control**: All bot control buttons functional and tested

All features work together seamlessly for efficient bot monitoring and management.
