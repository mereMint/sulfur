# Autonomous Messaging and Voice Call Fixes - Summary

## Issues Identified

Based on the logs provided, there were three main issues:

1. **Autonomous messaging on every restart**: Bot was sending DMs to users immediately after restart, even if they were recently contacted
2. **TTS failures**: edge-tts service was failing with `NoAudioReceived` errors, preventing voice calls from working
3. **Bot restarts**: Bot was receiving SIGTERM and restarting, triggering issue #1

## Root Causes

### 1. Autonomous Messaging Bug
**Problem**: The `record_autonomous_contact()` function in `modules/autonomous_behavior.py` was using `UPDATE` to record when a user was contacted. However, if no row existed for that user_id, the UPDATE would succeed but affect 0 rows, meaning the last_autonomous_contact was never recorded.

**Result**: After a bot restart, the autonomous messaging task would run and see no last_autonomous_contact for users, thinking they had never been messaged before.

### 2. No Startup Delay
**Problem**: The autonomous messaging task would start checking immediately after the bot came online, without any delay.

**Result**: Even if the database issue was fixed, the task could still message users shortly after restart if boredom level was high.

### 3. TTS Service Unavailable
**Problem**: The edge-tts service (Microsoft's text-to-speech service) was intermittently unavailable or experiencing network issues.

**Result**: Voice calls would fail to generate audio, falling back to text messages. The existing retry logic and fallback were working correctly, but there was no diagnostic to identify when the service was unavailable at startup.

## Fixes Implemented

### Fix 1: Database Record Bug ✅
**File**: `modules/autonomous_behavior.py`
**Change**: Modified `record_autonomous_contact()` to use `INSERT...ON DUPLICATE KEY UPDATE` instead of just `UPDATE`

```python
async def record_autonomous_contact(user_id: int):
    """Record that the bot has autonomously contacted a user."""
    # ... connection setup ...
    cursor.execute("""
        INSERT INTO user_autonomous_settings 
        (user_id, last_autonomous_contact, allow_autonomous_messages, allow_autonomous_calls, autonomous_contact_frequency)
        VALUES (%s, CURRENT_TIMESTAMP, TRUE, TRUE, 'normal')
        ON DUPLICATE KEY UPDATE 
            last_autonomous_contact = CURRENT_TIMESTAMP
    """, (user_id,))
```

**Impact**: Now properly records the last contact time, ensuring cooldown periods are respected even after bot restarts.

### Fix 2: Startup Delay ✅
**Files**: 
- `bot.py` - Modified `before_autonomous_messaging_task()` 
- `config/config.json` - Added `startup_delay_minutes` setting

**Changes**:
```python
@autonomous_messaging_task.before_loop
async def before_autonomous_messaging_task():
    await client.wait_until_ready()
    # Wait additional time after startup before first autonomous check
    # This prevents messaging users immediately on bot restart
    startup_delay_minutes = config.get('modules', {}).get('autonomous_behavior', {}).get('startup_delay_minutes', 10)
    logger.info(f"Autonomous messaging task will start after {startup_delay_minutes} minute startup delay")
    await asyncio.sleep(startup_delay_minutes * 60)
```

Config addition:
```json
"autonomous_behavior": {
  ...
  "startup_delay_minutes": 10,
  ...
}
```

**Impact**: The autonomous messaging task now waits 10 minutes after bot startup before checking for users to message. This gives the bot time to stabilize and ensures users aren't spammed on every restart.

### Fix 3: TTS Connectivity Test ✅
**File**: `modules/voice_tts.py`
**Change**: Added `test_tts_connectivity()` function to verify edge-tts service is working at startup

```python
async def test_tts_connectivity() -> bool:
    """
    Test if edge-tts service is accessible and working.
    
    Returns:
        True if TTS is working, False otherwise
    """
    if not EDGE_TTS_AVAILABLE:
        logger.warning("edge-tts is not installed")
        return False
    
    try:
        # Try to generate a very short test audio
        test_text = "Test"
        # ... generate test TTS with timeout ...
        
        if os.path.exists(test_file) and os.path.getsize(test_file) > 0:
            logger.info("TTS connectivity test passed")
            return True
        else:
            logger.warning("TTS connectivity test failed - no audio generated")
            return False
            
    except asyncio.TimeoutError:
        logger.warning("TTS connectivity test timed out - edge-tts service may be unreachable")
        return False
    except Exception as e:
        logger.warning(f"TTS connectivity test failed: {e}")
        return False
```

**File**: `bot.py`
**Change**: Added TTS connectivity test during voice dependency check

```python
if voice_deps.get('edge_tts'):
    print("  ✅ edge-tts: Available")
    # Test TTS connectivity
    print("  ⏳ Testing edge-tts connectivity...")
    try:
        tts_working = await voice_tts.test_tts_connectivity()
        if tts_working:
            print("  ✅ edge-tts service: Online and working")
        else:
            print("  ⚠️  edge-tts service: Connectivity issues detected")
            print("     Voice calls may not work properly until edge-tts service is accessible")
    except Exception as e:
        print(f"  ⚠️  Could not test edge-tts connectivity: {e}")
```

**Impact**: Bot now tests TTS connectivity at startup and warns if the service is unavailable. This helps diagnose issues early and sets expectations for voice call functionality.

## Bot Restart Behavior

The SIGTERM signals seen in the logs are **expected behavior** from the maintenance script (`maintain_bot.sh`):

1. **During updates**: When git updates are detected, the script sends SIGTERM to gracefully shut down the bot (line 1322)
2. **On manual stop**: When user presses Ctrl+C, cleanup sends SIGTERM (line 143)

This is not a crash - it's a controlled restart. The real issue was that these restarts would trigger immediate autonomous messaging, which is now fixed.

## Testing Recommendations

1. **Test autonomous messaging cooldown**:
   - Restart the bot after it has sent an autonomous message to a user
   - Wait for the 10 minute startup delay to pass
   - Verify that the user is not messaged again within their cooldown period (default 1 hour minimum)

2. **Test TTS connectivity**:
   - Check startup logs for TTS connectivity test results
   - If edge-tts service is down, verify that voice calls fall back to text messages
   - When service is up, verify voice calls work properly

3. **Test startup delay**:
   - Restart the bot
   - Check logs to confirm "Autonomous messaging task will start after 10 minute startup delay" message
   - Verify that autonomous messaging doesn't happen until after the delay

## Configuration Options

New configuration option in `config/config.json`:

```json
{
  "modules": {
    "autonomous_behavior": {
      "startup_delay_minutes": 10,  // NEW: Delay before first autonomous check after restart
      "min_dm_cooldown_hours": 1,   // Minimum time between any contacts (prevents spam)
      "min_cooldown_hours": 24,     // User-specific cooldown based on frequency setting
      "boredom_threshold": 0.3      // Bot must be this bored to initiate contact
    }
  }
}
```

You can adjust `startup_delay_minutes` to a different value if needed:
- Shorter (e.g., 5 minutes) for faster autonomous behavior after restart
- Longer (e.g., 30 minutes) to ensure bot is fully stable before any autonomous actions

## Edge-TTS Service Issues

The `NoAudioReceived` errors are caused by Microsoft's edge-tts service being temporarily unavailable or experiencing network issues. This is outside our control, but the bot now:

1. ✅ Detects the issue at startup with connectivity test
2. ✅ Retries TTS generation up to 3 times with exponential backoff
3. ✅ Falls back to alternative voice if primary voice fails
4. ✅ Sends text message to user if all TTS attempts fail
5. ✅ Logs detailed error information for debugging

If edge-tts continues to be unreliable, consider:
- Using a different TTS service (e.g., Google Cloud TTS, AWS Polly)
- Self-hosting a TTS solution (e.g., Coqui TTS)
- Implementing a cache for commonly used phrases

## Summary

All three issues have been addressed:

1. ✅ **Autonomous messaging on restart**: Fixed by correcting database record bug and adding startup delay
2. ✅ **TTS failures**: Improved diagnostics and verification that existing error handling is working
3. ✅ **Bot restarts**: Confirmed as expected behavior; autonomous messaging no longer triggers immediately

The bot should now behave correctly:
- Users will not be spammed with autonomous messages after restarts
- Voice calls will properly indicate when TTS service is unavailable
- Autonomous messaging respects cooldown periods across restarts
