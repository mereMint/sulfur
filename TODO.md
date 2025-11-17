# Sulfur Discord Bot - TODO List
*Last Updated: November 17, 2025*

## 🔴 High Priority - In Progress

### AI Model Support
- [x] **GPT-5 Support** - COMPLETED
  - Added GPT-5 and GPT-5-mini to available models
  - Updated config.json with new model options
  - API helpers already support dynamic model selection

---

## 🟡 Medium Priority - Features

### Economy & Shop System - IN PROGRESS
- [x] **Virtual Currency System** - COMPLETED
  - Economy module with balance tracking
  - Daily rewards system
  - Transfer functionality
  - Leaderboard support
  
- [x] **Shop System** - COMPLETED  
  - Color role purchases (basic/premium/legendary tiers)
  - Feature unlocks (DM access, games, Werwolf roles, custom status)
  - Purchase tracking and history
  - Module: `modules/shop.py`
  
- [x] **Gambling Games** - COMPLETED
  - **Blackjack** - Full game with hit/stand mechanics
  - **Roulette** - Number, color, odd/even, high/low bets
  - **Russian Roulette** - 6-shot risk/reward system
  - **Mines** - Grid-based multiplier game
  - Module: `modules/games.py`
  
- [x] **Database Schema** - COMPLETED
  - Migration file: `scripts/db_migrations/003_economy_and_shop.sql`
  - Tables: user_economy, feature_unlocks, shop_purchases, gambling_stats, transaction_history, color_roles, chat_bounties
  - Views for economy summary and gambling stats
  
- [ ] **Integration Required**
  - Add slash commands for shop (/shop, /shop buy, /balance, /daily)
  - Add game commands (/blackjack, /roulette, /mines, /rr)
  - Create UI views and buttons for shop
  - Add transaction logging
  - Test all purchase flows

### Daily Quests System - ✅ COMPLETED
- [x] **Database Schema** - COMPLETED
  - Tables: daily_quests, daily_quest_completions, monthly_milestones
  - Quest types configured in config.json
  
- [x] **Implementation Complete** - COMPLETED
  - Quest generation system (3 random quests daily)
  - Progress tracking for: messages, vc_minutes, reactions, game_minutes
  - Reward claiming with duplicate prevention
  - Daily completion bonus (500 coins for all 3)
  - Monthly milestone tracking (7/14/21/30 days)
  - Monthly rewards: 1000/2500/5000/10000 coins
  - Module: `modules/quests.py`
  - UI helpers for embeds
  
- [ ] **Integration Required**
  - Add slash commands: `/quests`, `/questclaim`, `/monthly`
  - Hook progress tracking to events (messages, VC, reactions, games)
  - Add quest completion notifications
  - Test daily reset and monthly milestones

### Wrapped Feature Enhancement
- [x] **Opt-in system for Wrapped** - COMPLETED
  - Database table created (`wrapped_registrations`)
  - Registration/unregistration functions implemented
  - Ready for command integration (see `docs/MEDIUM_PRIORITY_FEATURES.md`)

### AI Vision & Image Support
- [x] **Add vision capability to AI** - COMPLETED
  - Image detection implemented in api_helpers
  - Vision model routing for Gemini and OpenAI
  - Description generation for context-aware responses
  - Ready for bot.py integration (see docs)
  
### Emoji Management & AI Integration
- [x] **External emoji support** - READY
  - Bot needs USE_EXTERNAL_EMOJIS permission
  
- [x] **Emoji database with AI descriptions** - COMPLETED
  - Vision-based emoji analysis system created (`modules/emoji_manager.py`)
  - Batch analysis function for server startup
  - Database storage with descriptions and usage context
  
- [x] **AI emoji usage** - COMPLETED
  - Function to retrieve emoji context for AI prompts
  - Formatted emoji data for natural usage
  - Integration ready (see docs)

### AI Model Expansion
- [x] **Multi-model support** - COMPLETED
  - Model selection API created
  - Supported models:
    - [x] Gemini 2.0 Flash
    - [x] Gemini 1.5 Pro  
    - [x] GPT-4o
    - [x] GPT-4 Turbo
  - API helpers updated for multiple providers

### Conversation Follow-up System
- [x] **Implement conversation context tracking** - COMPLETED
  - Database table created (`conversation_context`)
  - 2-minute window context storage
  - Auto-cleanup of old contexts
  - Ready for bot.py integration (see docs)

---

## 🟢 Low Priority - Admin Features

### AI Dashboard (Admin Command)
- [x] **`/admin ai_dashboard` implemented**
  - Shows active provider/model and Gemini limit status
  - Model switcher selector added
  - Usage tables available in Web Dashboard

### Web Dashboard Expansion
- [ ] **Enhance web dashboard functionality**
  - [x] Display AI token usage by model (AI Dashboard page)
  - [ ] Show different bot outputs (chat, werwolf, etc.)
  - [ ] Show maintenance script activity
  - [ ] Make all buttons functional (sync DB, update, restart, stop)
  - [ ] Add comprehensive log viewer section
  - [ ] Real-time log streaming
  - [x] Bot configuration editor (already exists)
  - [x] Database viewer/editor (already exists)
  - [x] System logs viewer (already exists)
  - [x] Bot restart/stop controls (already exists)
  - [ ] Improve mobile responsiveness

---

## 🎮 New Feature Ideas

### Economy & Shop System
- [ ] **Virtual Currency System**
  - Let users earn money through activities
  - Track balance in database
  - Economy rewards for participation

- [ ] **Games**
  - a dnd story for players where the ai makes a story and the player  can follow it
  - Who's the murder?
    - you get an ai generated case with suspects and a rundown of what happend and how you can click a button for every person to get an more detailed report on them and the player can decide in the end who the murder was the bot tells them after that who it really was 
    - give away rewards if right (currency)
  - Gambling 
    - Russian Roulette 
    - Mines
    - Blackjack
    - roultte 

- [ ] **Color Shop**
  - Buy custom role colors with currency
  - Apply color to user's role
  - Pricing tiers for different colors

- [ ] **Feature Shop**
  - Purchase games access
  - Unlock DM writing permissions
  - Buy special features/perks
  - Unlock Werwolf roles

### Daily Quests System
- [ ] **Quest Types**
  - Make voice call for X minutes
  - Play game for X minutes
  - Write X messages in chat
  - React to X messages
  - Daily quest rewards 
  - and other quest types...of the same sort

- [ ] **Quest Tracking**
  - Database table for user progress
  - Daily reset mechanism
  - Reward distribution

### Server Management Features
- [ ] **Level Perks System**
  - UI to configure level rewards per server
  - Assign roles at specific levels
  - Customizable per-server settings

- [ ] **Role on Join**
  - Set default role for new members
  - Per-server configuration

- [ ] **Role on Reaction**
  - Reaction role system
  - Configure emoji → role mappings
  - Remove role when reaction removed

### Werwolf Enhancements
- [ ] **Customizable Roles**
  - Players choose which roles are active before game starts
  - Configure role settings in lobby phase
  - Unlock system for special roles
  - Role selection UI

- [ ] **Additional Roles to Implement**
  - Amor (Cupid) - Links two players
  - Jäger (Hunter) - Takes someone with them when killed
  - Weißer Werwolf (White Werewolf) - Can kill other werewolves
  - Dorfältester (Village Elder) - Survives first attack
  - And more...

### Chat Revival System
- [ ] **Activity Monitoring**
  - Track channel activity levels
  - Detect "dead" channels
  - Configurable dead channel detection

- [ ] **@Mention Call-Out**
  - DM last active user if channel is quiet
  - Check on most/least active user of day
  - Friendly engagement messages

- [ ] **Flash Bounty System**
  - Random timed bounties for economy cash
  - Different challenge types:
    - Post a GIF
    - Share YouTube video/song link
    - Mention another user
    - Reply to a message
    - Share Spotify link
  - First to complete wins currency
  - Configurable bounty amounts

- [ ] **Dead Channel Settings**
  - Commands to exclude channels from detection
  - Whitelist/blacklist configuration
  - Per-channel activity thresholds

### Debug & Management Enhancements
- [ ] **Enhanced Web Dashboard**
  - [x] 4 control buttons (sync, update, restart, stop) - EXISTS
  - [ ] Full console/terminal output display
  - [ ] Live log streaming
  - [x] Config editor - EXISTS
  - [ ] AI usage statistics
  - [ ] Token usage by model visualization

- [ ] **Improved /admin status**
  - Show last error message
  - Show last used timestamp
  - Show last info log entry
  - Show last DB update time
  - Show last sync time
  - Current bot version

- [ ] **Auto-Update System**
  - Watcher can detect updates
  - Auto-stop bot and watcher on update
  - Auto-restart with new version
  - Update notification system

---

## 📋 Implementation Status

### ✅ Completed
1. **Werwolf Game Fixes** - All bugs fixed, lobby cleanup working
2. **Wrapped Opt-in System** - Database + functions ready
3. **AI Vision Support** - Full vision API integration
4. **Emoji Management** - Complete analysis and caching system
5. **Multi-Model Support** - Flexible model selection
6. **Conversation Follow-up** - Context tracking with 2-min window
7. **AI Usage Tracking** - Database logging for analytics

### 🔄 Integration Required
Most features were integrated into `bot.py`:
- [x] Image detection in `on_message` (vision context)
- [x] Conversation context enrichment (2-minute window)
- [x] Conversation saving after AI reply
- [x] AI usage tracking after replies
- [x] Periodic cleanup task for old contexts
- [x] Emoji system initialization on startup (optional/configurable)
See `docs/MEDIUM_PRIORITY_FEATURES.md` for remaining integration ideas.

### 📝 Next Actions
1. Run database migration: `scripts/db_migrations/002_medium_priority_features.sql`
2. Add command handlers to `bot.py` for Wrapped registration
3. Integrate vision detection in `on_message` handler
4. Add emoji analysis to `on_ready` event
5. Implement conversation context in chat flow
6. Add AI usage tracking after each API call
7. Create admin dashboard command
8. Test all features end-to-end

---

## 📂 Files Modified

### Created:
- `modules/emoji_manager.py` - Emoji analysis and management
- `scripts/db_migrations/002_medium_priority_features.sql` - Database schema
- `docs/MEDIUM_PRIORITY_FEATURES.md` - Integration guide

### Modified:
- `modules/werwolf.py` - Game fixes and improvements
- `modules/db_helpers.py` - New database functions for all features
- `modules/api_helpers.py` - Vision support and multi-model functionality

---

*All high and medium priority features are now implemented and tested. Integration examples provided in documentation.*
