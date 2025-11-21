# Werwolf Game Testing Checklist

This checklist helps verify all Werwolf game features work correctly after the bug fixes.

## Pre-Testing Setup

- [ ] Bot is running and connected to Discord
- [ ] Database is accessible
- [ ] Test server has appropriate permissions for bot
- [ ] At least one test account available (or use bot filling)

## Basic Game Flow Tests

### Test 1: Simple Game (2-4 Players)
- [ ] Start game with `/ww start`
- [ ] Join game via voice channel
- [ ] Verify roles assigned via DM
- [ ] Complete one night phase
  - [ ] Test Werwolf kill command: `kill <name>`
  - [ ] Test Seherin see command: `see <name>` (if present)
- [ ] Complete one day phase
  - [ ] Vote using buttons
  - [ ] Verify voting counts display correctly
  - [ ] Complete lynch or skip
- [ ] Verify game ends with correct winner
- [ ] Verify channels cleaned up

### Test 2: Medium Game (5-7 Players)
- [ ] Start game with 5-7 players
- [ ] Verify Jäger role appears (5+ players)
- [ ] Test Hexe potions (7+ players):
  - [ ] `heal` command
  - [ ] `poison <name>` command
- [ ] Test Dönerstopfer mute (9+ players)
- [ ] Test Jäger death ability:
  - [ ] Lynch or kill Jäger
  - [ ] Verify DM received with 60s timeout
  - [ ] Select target to take down

## New Role Tests (8+ Players)

### Test 3: Amor Role (8+ Players)
**Critical - Tests the bug fixes**

- [ ] Start game with 8+ players to trigger Amor
- [ ] Verify Amor receives role DM with instructions
- [ ] **Test human Amor:**
  - [ ] Send `love <name1> <name2>` via DM to bot
  - [ ] Verify both lovers receive DM notification
  - [ ] Verify game doesn't hang waiting for Amor
  - [ ] Kill one lover
  - [ ] Verify other lover dies from heartbreak
- [ ] **Test bot Amor:**
  - [ ] Start game with 1 player + bots (use `ziel_spieler: 8`)
  - [ ] Verify bot Amor selects lovers automatically
  - [ ] Check console logs for "Bot 'X' (Amor) is choosing lovers"
- [ ] **Test lover name parsing:**
  - [ ] Test with single-word names: `love Alice Bob`
  - [ ] Test with multi-word names: `love Alice Smith Bob Jones`
- [ ] Verify game transitions to day after Amor acts

### Test 4: Der Weiße Role (10+ Players)
- [ ] Start game with 10+ players
- [ ] Verify Der Weiße receives role DM
- [ ] **Test immunity:**
  - [ ] Werewolves attack Der Weiße
  - [ ] Verify message: "Der Weiße has survived!"
  - [ ] Immunity used, second attack kills
- [ ] **Test lynch penalty:**
  - [ ] Lynch Der Weiße during day
  - [ ] Verify penalty message appears
  - [ ] Test that Seherin/Hexe/Dönerstopfer lose powers
  - [ ] Verify abilities return error messages

## Edge Case Tests

### Test 5: Amor + Der Weiße Combination
- [ ] Start game with 10+ players
- [ ] Make Der Weiße one of the lovers
- [ ] Test immunity + lover death chain interaction
- [ ] Lynch Der Weiße who is a lover
- [ ] Verify other lover dies despite penalty

### Test 6: All Bots Game
- [ ] Start with 0 players, set `ziel_spieler: 10`
- [ ] Verify 10 bots added with random names
- [ ] Verify all bot roles act:
  - [ ] Bot Werwolf attacks
  - [ ] Bot Seherin investigates
  - [ ] Bot Hexe uses potions
  - [ ] Bot Dönerstopfer mutes
  - [ ] **Bot Amor selects lovers**
- [ ] Verify game completes automatically
- [ ] Verify stats NOT recorded for bots

### Test 7: Win Conditions
- [ ] All werewolves killed → Dorfbewohner win
- [ ] Werewolves equal/outnumber villagers → Werwölfe win
- [ ] Verify winning roles include:
  - [ ] AMOR counted as Dorfbewohner victory
  - [ ] DER_WEISSE counted as Dorfbewohner victory
- [ ] Check database for correct stats recording

## Integration Tests

### Test 8: Multi-Game Management
- [ ] Start game in Channel A
- [ ] Start second game in Channel B (should work)
- [ ] Verify games don't interfere with each other
- [ ] End both games
- [ ] Verify both cleanup correctly

### Test 9: Cleanup & Error Handling
- [ ] Start game then cancel (leave VC before start)
- [ ] Verify channels deleted
- [ ] Test DM failures (user has DMs disabled)
- [ ] Test player disconnect during game
- [ ] Test bot restart during game
- [ ] Verify cleanup task removes stale categories

### Test 10: Voice Channel Management
- [ ] Verify players muted/deafened at night
- [ ] Verify players unmuted during day
- [ ] Verify dead players unmuted (can talk to ghosts)
- [ ] Verify Dönerstopfer target stays muted during day

## Command Tests

### Test 11: All Night Commands
- [ ] `kill <name>` - Werwolf
- [ ] `see <name>` - Seherin
- [ ] `heal` - Hexe
- [ ] `poison <name>` - Hexe
- [ ] `mute <name>` - Dönerstopfer
- [ ] `love <name1> <name2>` - **Amor (NEW)**

### Test 12: Command Validation
- [ ] Wrong role tries command → Error message
- [ ] Ability already used → Error message
- [ ] Invalid player name → Error message
- [ ] Command during wrong phase → Error message
- [ ] Amor after night 1 → Already chosen message

## Performance Tests

### Test 13: Large Game (15+ Players with Bots)
- [ ] Start with `ziel_spieler: 15`
- [ ] Verify performance is acceptable
- [ ] Check TTS timing works correctly
- [ ] Verify voting scales properly
- [ ] Check cleanup handles large category

## Regression Tests

### Test 14: Existing Features Still Work
- [ ] `/ww rules` - Shows role descriptions
- [ ] Werwolf thread for wolf communication
- [ ] TTS announcements work
- [ ] Event log displays correctly
- [ ] Game state embed updates
- [ ] Stock market integration (WOLF stock)
- [ ] XP/level system integration

## Bug-Specific Tests

### Test 15: Verify Bug Fixes
**These tests directly verify the fixes made:**

- [ ] **Bug 1 - Amor command parser:**
  - [ ] Test `love Alice Bob` works
  - [ ] Test `love Alice Smith Bob Jones` works
  - [ ] Test `love InvalidName1 InvalidName2` shows error
  - [ ] Verify `lover_target` attribute set correctly

- [ ] **Bug 2 - Night end check:**
  - [ ] Game with Amor on night 1 waits for love action
  - [ ] Game with Amor on night 2+ doesn't wait
  - [ ] Game transitions to day after Amor acts
  - [ ] No infinite hang with Amor present

- [ ] **Bug 3 - Bot Amor:**
  - [ ] Bot-only game completes night 1
  - [ ] Check logs show bot Amor acted
  - [ ] Verify two bots become lovers
  - [ ] Lover death chain works with bot lovers

- [ ] **Bug 4 - Win stats:**
  - [ ] Amor on winning team gets win recorded
  - [ ] Der Weiße on winning team gets win recorded
  - [ ] Check database `werwolf_stats` table

## Console Log Checks

During testing, monitor console for:
- [ ] `[WW] Starting game setup...`
- [ ] `[WW] Roles assigned: {...}`
- [ ] `[WW] Bot 'X' (Amor) is choosing lovers...` ← **New**
- [ ] `[WW] All night actions are complete. Transitioning to day...`
- [ ] No Python errors or stack traces
- [ ] No hanging/frozen states

## Final Validation

- [ ] All critical bugs verified fixed
- [ ] No new bugs introduced
- [ ] Performance acceptable
- [ ] All features from IMPLEMENTATION_SUMMARY.md verified
- [ ] Ready for production deployment

---

## Notes

- Tests marked with 🔴 **Critical** must pass
- Tests with bot players require `ziel_spieler` parameter
- Some tests require multiple Discord accounts or patience with bot timings
- Check `/home/runner/work/sulfur/sulfur/logs/` for detailed logs

## Issues Found During Testing

_Document any issues discovered here:_

| Test # | Issue Description | Severity | Status |
|--------|------------------|----------|--------|
| | | | |
