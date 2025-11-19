# Detective Game Enhancements - Implementation Summary

## Overview
This document describes the enhancements made to the detective game system to address the issues:
1. Cases being repeated instead of generating new ones
2. Need for case persistence and tracking
3. Progressive difficulty system
4. More interactive gameplay requiring investigation

## Problem Statement
- The `/detective` command was generating a new case each time but showing the same case
- No persistence of generated cases
- No tracking of which cases users had completed
- All information was presented immediately on a silver platter
- No difficulty progression or challenge scaling

## Solution Implemented

### 1. Database Schema (Migration 004)

Three new tables were added to support case persistence and progression:

#### `detective_cases`
Stores all generated murder mystery cases with:
- Case details (title, description, location, victim)
- Suspects, evidence, and hints (as JSON)
- Murderer index
- Difficulty level (1-5)
- Creation timestamp

#### `detective_user_progress`
Tracks individual user progress on cases:
- Which cases a user has started
- Which cases are completed
- Whether the case was solved correctly
- Start and completion timestamps

#### `detective_user_stats`
Maintains user statistics:
- Current difficulty level (1-5)
- Number of cases solved/failed
- Total cases played
- Last played timestamp

### 2. Case Management System

#### New Functions in `detective_game.py`

**`get_user_difficulty(db_helpers, user_id)`**
- Retrieves user's current difficulty level from database
- Creates new stats record if user is new (default difficulty 1)
- Returns difficulty level (1-5)

**`update_user_stats(db_helpers, user_id, solved)`**
- Updates user statistics after completing a case
- Increases difficulty by 1 if case was solved correctly (capped at 5)
- Tracks wins/losses and total games played
- Updates last played timestamp

**`save_case_to_db(db_helpers, case_data, difficulty)`**
- Saves a newly generated case to the database
- Serializes JSON fields (suspects, evidence, hints)
- Returns the case_id of the saved case

**`get_unsolved_case(db_helpers, user_id, difficulty)`**
- Queries for cases at user's difficulty that they haven't completed
- Returns a random unsolved case if available
- Returns None if no unsolved cases exist at that difficulty

**`mark_case_started(db_helpers, user_id, case_id)`**
- Records that a user has started a specific case
- Creates progress tracking entry

**`mark_case_completed(db_helpers, user_id, case_id, solved)`**
- Marks a case as completed
- Records whether it was solved correctly
- Sets completion timestamp

**`generate_case_with_difficulty(api_helpers, config, gemini_api_key, openai_api_key, difficulty)`**
- Generates a new murder case using AI
- Adjusts the AI prompt based on difficulty level:
  - **Level 1 (Easy)**: Obvious clues, straightforward hints
  - **Level 2 (Medium)**: Some deduction required, moderately clear hints
  - **Level 3 (Moderate-Hard)**: Subtle clues, coded/symbolic hints
  - **Level 4 (Hard)**: Cryptic clues, complex codes, red herrings
  - **Level 5 (Very Hard)**: Extremely cryptic, multiple misdirections, puzzle hints
- Sets difficulty field in case data

**`get_or_generate_case(db_helpers, api_helpers, config, gemini_api_key, openai_api_key, user_id)`**
- **Main entry point** for getting a case
- Gets user's current difficulty level
- Tries to find an unsolved case at that difficulty
- If found, returns the existing case
- If not found, generates a new case and saves it
- Ensures cases are reused before generating new ones

### 3. Bot Integration Changes

#### Updated `/detective` Command
```python
# Old behavior: Always generated a new case
case = await detective_game.generate_murder_case(...)

# New behavior: Reuses unsolved cases or generates new ones
case = await detective_game.get_or_generate_case(
    db_helpers, api_helpers, config, 
    GEMINI_API_KEY, OPENAI_API_KEY, user_id
)

# Mark case as started in database
if case.case_id:
    await detective_game.mark_case_started(db_helpers, user_id, case.case_id)
```

#### Enhanced Case Display (`DetectiveGameView.create_case_embed()`)

**Difficulty Display**
- Shows difficulty with star emoji (⭐ x difficulty level)
- Displays "Stufe X/5" to indicate progression

**Progressive Information Hiding**
- **Easy (1-2)**: All evidence and hints visible
- **Medium (3)**: Some evidence hidden, all hints visible
- **Hard (4-5)**: Most evidence and hints locked
  - Only 1 evidence item shown initially
  - Only 1 hint shown initially
  - Additional items unlocked through investigation

**Investigation Progress Tracking**
- Shows which suspects have been investigated
- Encourages investigation to unlock information

#### Enhanced Suspect Investigation (`DetectiveGameView.create_suspect_embed()`)

**Dynamic Information Reveal**
- Shows full suspect details (occupation, alibi, motive, suspicious details)
- **For difficulty 3+**: Reveals additional evidence after investigating 2+ suspects
- **For difficulty 4+**: Unlocks additional hints as more suspects are investigated
- Shows progress indicator for remaining investigations

**Progression Feedback**
- "Untersuche weitere X Verdächtige für mehr Hinweise!"
- "Alle Verdächtigen untersucht. Zeit für eine Anklage!"

#### Updated Accusation System (`DetectiveAccusationView._make_accusation()`)

**Database Tracking**
```python
# Mark case as completed
if self.case.case_id:
    await detective_game.mark_case_completed(db_helpers, user_id, case_id, is_correct)

# Update user stats and difficulty
await detective_game.update_user_stats(db_helpers, user_id, is_correct)
```

**Difficulty Progression Notification**
- If difficulty increased after solving, shows:
  - "🎯 Schwierigkeitsgrad erhöht!"
  - "Nächster Fall: Stufe X/5"
- Motivates players to improve

### 4. MurderCase Class Updates

Added fields to the `MurderCase` class:
- `case_id`: Database ID (None for fallback cases)
- `difficulty`: Difficulty level (1-5)

These fields are preserved when loading from database.

## Usage Flow

### First Time Player
1. User runs `/detective`
2. System gets user difficulty (defaults to 1 for new users)
3. No unsolved cases exist, so AI generates a new Level 1 case
4. Case is saved to database
5. Case is marked as "started" for the user
6. User sees easy case with all information visible

### Returning Player (Unsolved Cases)
1. User runs `/detective`
2. System finds an unsolved Level 2 case (from previous session or other users)
3. Returns the existing case (no AI generation needed)
4. User continues from where they left off

### Progressing Player
1. User solves a Level 2 case correctly
2. System marks case as completed and solved
3. Difficulty increases from 2 to 3
4. Next time, system looks for Level 3 cases
5. If none exist, generates harder Level 3 case with:
   - More cryptic hints
   - Hidden evidence
   - More red herrings

### Investigation Gameplay
1. User starts a Level 4 case
2. Only sees: basic info, 1 evidence item, 1 hint
3. User investigates Suspect #1 - sees their details
4. User investigates Suspect #2 - unlocks additional evidence
5. User investigates Suspect #3 - unlocks another hint
6. User must deduce from all gathered information

## Database Migration

To apply the migration:

```bash
# Using Python script
python apply_migration.py scripts/db_migrations/004_detective_game_cases.sql

# Or using MySQL directly
mysql -u sulfur_bot_user -p sulfur_bot < scripts/db_migrations/004_detective_game_cases.sql
```

## Benefits

### For Users
1. **Case Variety**: Reuses existing cases, reducing repetition
2. **Progressive Challenge**: Difficulty scales with skill
3. **Interactive Investigation**: Must work for information
4. **Sense of Progress**: See difficulty level increase
5. **Replayability**: Can replay unsolved cases

### For the Bot
1. **Resource Efficiency**: Reuses cases instead of generating new ones every time
2. **Better AI Usage**: Only generates when needed
3. **Data Tracking**: Statistics on user engagement
4. **Scalability**: Case pool grows over time

### For Developers
1. **Database-backed**: Persistent storage of cases
2. **Extensible**: Easy to add new difficulty levels or case types
3. **Testable**: Clear separation of concerns
4. **Maintainable**: Well-documented functions

## Testing

Two test suites validate the implementation:

### `test_detective_game.py`
- Tests original functionality (backwards compatibility)
- Validates MurderCase class
- Checks API call structure

### `test_detective_enhancements.py`
- Tests new database functions
- Validates difficulty progression
- Checks case persistence logic
- Verifies bot integration

Both test suites pass successfully.

## Configuration

No configuration changes required. The system uses existing economy settings:

```json
"detective": {
    "reward_correct": 500,
    "reward_wrong": 0
}
```

Rewards remain the same across all difficulty levels (though this could be enhanced in the future).

## Future Enhancements

Potential improvements:
1. **Difficulty-based Rewards**: Higher rewards for harder cases
2. **Case Categories**: Different types of mysteries (murder, theft, conspiracy)
3. **Multiplayer**: Cooperative case solving
4. **Time Limits**: Bonus for solving quickly
5. **Leaderboards**: Top detectives by difficulty or cases solved
6. **Case Ratings**: Users can rate cases, affecting reuse priority
7. **Custom Cases**: Users could submit their own cases
8. **Hint System**: Spend currency to get additional hints

## Summary

This enhancement transforms the detective game from a simple one-off experience into a progressive, engaging system that:
- Solves the repetition problem through case persistence
- Adds challenge through difficulty progression
- Makes gameplay more interactive through information hiding
- Tracks user progress and statistics
- Provides a foundation for future enhancements
