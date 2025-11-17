# Quest System Testing Guide

This document provides a comprehensive testing guide for the newly implemented quest system in Sulfur Bot.

## Overview

The quest system has been fully integrated with slash commands and automatic progress tracking. This guide will help you test all features to ensure they work correctly.

## Prerequisites

1. **Database Migration**: Ensure the economy migration has been applied:
   ```bash
   python apply_migration.py scripts/db_migrations/003_economy_and_shop.sql
   ```

2. **Bot Running**: The bot must be running and connected to Discord

3. **Test User**: You need a Discord account to test with

## Feature Testing Checklist

### 1. Quest Generation and Display

**Command**: `/quests`

**Expected Behavior**:
- [ ] First use generates 3 random daily quests
- [ ] Each quest shows:
  - Quest type icon (💬, 🎤, 👍, or 🎮)
  - Quest name
  - Progress bar (e.g., ██████░░░░ 60%)
  - Current progress vs target (e.g., 30/50)
  - Reward amount
  - Completion status
- [ ] Footer shows completion status (X/3 completed)
- [ ] Embed uses gold color for active quests

**Test Steps**:
1. Run `/quests` for the first time today
2. Verify 3 quests are generated
3. Run `/quests` again - should show same quests, not generate new ones

### 2. Quest Progress Tracking

#### A. Message Quest (💬 Send Messages)

**Target**: 50 messages (default config)

**Test Steps**:
1. Check current progress with `/quests`
2. Send several messages in any text channel
3. Wait a few seconds
4. Run `/quests` again
5. Verify progress increased

**Expected**: Progress bar updates, counter increments

#### B. Voice Chat Quest (🎤 Voice Chat Time)

**Target**: 30 minutes (default config)

**Test Steps**:
1. Check current progress with `/quests`
2. Join a voice channel (unmuted and undeafened)
3. Wait at least 1 minute (progress updates every minute)
4. Run `/quests`
5. Verify progress increased by at least 1

**Expected**: Progress increments by 1 every minute in VC

#### C. Reaction Quest (👍 React to Messages)

**Target**: 20 reactions (default config)

**Test Steps**:
1. Check current progress with `/quests`
2. Add reactions to several messages (any emoji)
3. Run `/quests` again
4. Verify progress increased

**Expected**: Each reaction adds 1 to progress

#### D. Game Quest (🎮 Play Games)

**Target**: 15 minutes (default config)

**Test Steps**:
1. Check current progress with `/quests`
2. Start playing a game (Discord must detect it as "Playing X")
3. Play for a few minutes
4. Stop the game or change games
5. Run `/quests`
6. Verify progress increased

**Expected**: Progress updates when game session ends (minimum 1 minute sessions counted)

### 3. Quest Completion and Claiming

**Command**: `/questclaim`

#### A. Single Quest Claim

**Test Steps**:
1. Complete at least one quest (100% progress)
2. Run `/questclaim`
3. Check response

**Expected**:
- [ ] Success message shows number of quests claimed
- [ ] Total reward amount displayed with currency symbol
- [ ] Balance increases by reward amount

#### B. All Quests Completed - Daily Bonus

**Test Steps**:
1. Complete all 3 quests
2. Run `/questclaim`

**Expected**:
- [ ] Individual quest rewards claimed
- [ ] **Daily Bonus** section appears in response
- [ ] Bonus amount: 500 coins (default config)
- [ ] Total includes bonus

#### C. Already Claimed Detection

**Test Steps**:
1. Complete and claim a quest
2. Run `/questclaim` again

**Expected**:
- [ ] Message: "❌ Du hast keine abgeschlossenen Quests zum Einsammeln."

### 4. Monthly Progress Tracking

**Command**: `/monthly`

**Expected Display**:
- [ ] Current month name (e.g., "November 2025")
- [ ] Completion days / Total days in month (e.g., 5/30)
- [ ] Progress bar (20 characters wide)
- [ ] Milestone list with status:
  - ✅ for reached milestones
  - 🔒 for locked milestones
- [ ] Milestone details:
  - 7 Days - Weekly Warrior: 1000 🪙
  - 14 Days - Fortnight Champion: 2500 🪙
  - 21 Days - Three-Week Legend: 5000 🪙
  - 30 Days - Monthly Master: 10000 🪙

### 5. Monthly Milestone Rewards

**Automatic Grant**: Milestones are automatically granted when claiming quests after completing all daily quests

**Test Steps**:
1. Complete all 3 quests on multiple days (simulate by testing over several days)
2. After reaching 7, 14, 21, or 30 completion days, run `/questclaim`
3. Check for milestone reward in response

**Expected**:
- [ ] 🏆 Section appears in claim response
- [ ] Milestone name displayed (e.g., "Weekly Warrior")
- [ ] Completion days shown (e.g., "7 days")
- [ ] Reward amount displayed
- [ ] Balance increases by milestone reward + quest rewards

**Note**: Each milestone can only be claimed once per month

### 6. Daily Reset Mechanism

**Reset Time**: Midnight UTC (configurable via `daily_reset_hour` in config.json)

**Test Steps**:
1. Complete some quests before midnight UTC
2. Wait until after midnight UTC
3. Run `/quests`

**Expected**:
- [ ] New set of 3 random quests generated
- [ ] All progress reset to 0
- [ ] Previous day's completed quests no longer claimable

### 7. Edge Cases and Error Handling

#### A. No Quests Yet

**Test**: Run `/questclaim` before generating quests

**Expected**: Error message about no quests

#### B. Quest Progress Overflow

**Test**: Complete a quest with more actions than required (e.g., send 60 messages when target is 50)

**Expected**: 
- [ ] Progress caps at target
- [ ] Quest marked as completed
- [ ] Extra actions don't cause errors

#### C. Concurrent Claims

**Test**: Try to claim the same quest reward multiple times quickly

**Expected**: Only one claim succeeds due to database transaction safety

#### D. User Has DMs Disabled

**Test**: Have a user with DMs disabled complete quests

**Expected**: Quest notifications fail silently without errors

## Performance Validation

### Database Query Efficiency

**Monitor**:
- [ ] Quest generation is fast (< 1 second)
- [ ] Progress updates don't cause lag
- [ ] `/quests` command responds quickly even with many users

### Memory Usage

**Monitor**:
- [ ] No memory leaks from quest tracking
- [ ] Event handlers clean up properly

## Configuration Validation

Check `config/config.json` settings:

```json
"quests": {
  "enabled": true,
  "daily_reset_hour": 0,
  "quest_types": {
    "messages": {"target": 50, "reward": 200},
    "vc_minutes": {"target": 30, "reward": 250},
    "reactions": {"target": 20, "reward": 150},
    "game_minutes": {"target": 15, "reward": 300}
  }
}
```

**Verify**:
- [ ] All 4 quest types exist
- [ ] Targets are reasonable
- [ ] Rewards match in-game economy

## Database Validation

**Verify Tables Exist**:
```sql
SHOW TABLES LIKE '%quest%';
```

**Expected Tables**:
- `daily_quests`
- `daily_quest_completions`
- `monthly_milestones`

**Check Quest Data**:
```sql
SELECT * FROM daily_quests WHERE user_id = YOUR_USER_ID;
```

**Expected Columns**:
- id, user_id, quest_date, quest_type, target_value, current_progress, completed, reward_claimed

## Integration Testing

### With Economy System

**Test**:
1. Check balance before claiming: `/balance`
2. Claim quest rewards: `/questclaim`
3. Check balance after: `/balance`

**Expected**: Balance increases by exact reward amount

### With Level System

**Test**: Quest progress and XP gain should work independently

**Expected**: 
- [ ] Sending messages grants XP AND increases message quest progress
- [ ] Voice chat grants XP AND increases VC quest progress

### With Transaction History

**Test**: Check `/transactions` after claiming quest rewards

**Expected**: 
- [ ] Quest reward appears as transaction
- [ ] Transaction type labeled appropriately
- [ ] Amount matches claimed reward

## Troubleshooting

### Quests Not Generating

**Check**:
1. Database tables exist
2. Config has `quests.enabled: true`
3. User is not a bot
4. Bot has database connection

### Progress Not Updating

**Check**:
1. Event handlers are running
2. No errors in bot logs
3. User is performing correct action (e.g., not muted in VC)
4. Quest is not already completed

### Rewards Not Claiming

**Check**:
1. Quest is marked as completed
2. Reward not already claimed
3. Database connection is active
4. User balance table exists

## Success Criteria

All features pass when:
- ✅ All 3 slash commands work correctly
- ✅ All 4 quest types track progress automatically
- ✅ Rewards claim properly with correct amounts
- ✅ Daily reset works at configured time
- ✅ Monthly milestones grant correctly
- ✅ No errors in bot logs during testing
- ✅ Database queries are efficient
- ✅ Edge cases handled gracefully

## Security Summary

✅ **CodeQL Scan**: No security vulnerabilities found
✅ **SQL Injection**: All queries use parameterized statements
✅ **Input Validation**: User IDs validated, quest types validated
✅ **Transaction Safety**: Reward claims use database transactions
✅ **Error Handling**: All exceptions caught and logged

## Notes for Future Testing

1. **Long-term Testing**: Monitor quest system over multiple days to ensure daily reset works consistently
2. **Load Testing**: Test with multiple users claiming quests simultaneously
3. **Monthly Boundary**: Test monthly milestone tracking across month boundaries (e.g., November to December)
4. **Time Zone Issues**: Verify UTC handling for daily reset works for all users regardless of their timezone

## Reporting Issues

If you find any issues during testing, report:
1. What command/action was performed
2. Expected vs actual behavior
3. Any error messages in bot logs
4. User ID and timestamp
5. Database state (if applicable)
