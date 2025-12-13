# API Fallback System

## Overview

The Sulfur Discord bot now includes an automatic API fallback system that seamlessly switches between Gemini and OpenAI APIs when quota limits are reached or services become unavailable.

## How It Works

### Automatic Fallback

When the bot encounters an HTTP 429 (Resource Exhausted) error from one API provider, it automatically attempts to use the alternative provider:

- **Gemini → OpenAI**: If Gemini quota is exhausted, the bot falls back to OpenAI
- **OpenAI → Gemini**: If OpenAI quota is exhausted, the bot falls back to Gemini

### Transparent to Users

The fallback happens automatically and transparently. Users will receive their AI responses without interruption, even when one provider hits quota limits.

### Logging

All fallback events are logged with appropriate severity levels:
- `INFO`: Normal API operations
- `WARNING`: Quota exhaustion detected, attempting fallback
- `ERROR`: Fallback attempt failed

Example log output:
```
[2025-12-13 18:11:37] [API] [WARNING] [Chat API] Gemini quota exhausted (429), attempting fallback to OpenAI
[Chat API] Gemini quota exhausted, falling back to OpenAI...
[2025-12-13 18:11:37] [API] [INFO] [Chat API] Successfully fell back to OpenAI after Gemini quota exhaustion
```

## Affected Functions

The fallback system is implemented in all API helper functions:

1. **`get_chat_response()`** - Main chat functionality
2. **`get_relationship_summary_from_api()`** - User relationship summaries
3. **`get_werwolf_tts_message()`** - Werwolf game TTS messages
4. **`get_random_names()`** - Random name generation for Werwolf bots
5. **`get_wrapped_summary_from_api()`** - Wrapped feature summaries
6. **`get_game_details_from_api()`** - Game information retrieval
7. **`get_vision_analysis()`** - Image analysis with vision models
8. **`get_ai_response_with_model()`** - Direct model invocation

## Configuration

### Requirements

For the fallback system to work, you need:

1. **Both API keys configured** in `.env`:
   ```
   GEMINI_API_KEY=your_gemini_key_here
   OPENAI_API_KEY=your_openai_key_here
   ```

2. **Primary provider set** in `config/config.json`:
   ```json
   {
     "api": {
       "provider": "gemini",  // or "openai"
       ...
     }
   }
   ```

### Single API Key Setup

If you only have one API key configured:
- The bot will attempt to use that provider exclusively
- Fallback will not occur if the quota is exhausted
- Users will see an error message indicating quota exhaustion

## Error Handling

### Both APIs Available

When both API keys are configured and one fails:
```
Primary API (Gemini) → 429 Error → Fallback to OpenAI → Success ✓
```

### Both APIs Unavailable

If both APIs fail, users receive an informative error message:
```
"Beide APIs sind nicht verfügbar. Gemini: Quota erschöpft. OpenAI: [error details]"
```

### Single API Configuration

If only one API key is configured and quota is exhausted:
```
"Gemini API-Quota erschöpft (Status: 429). Versuche es später erneut oder verwende einen anderen Provider."
```

## Rate Limits

### Gemini API

Different models have different rate limits:
- **gemini-2.0-flash-exp**: 10 RPM (requests per minute)
- **gemini-2.5-flash**: Higher limits (check Google Cloud Console)
- **gemini-1.5-pro**: Higher limits (check Google Cloud Console)

### OpenAI API

Rate limits depend on your OpenAI tier:
- **Free tier**: 3 RPM
- **Tier 1**: 60 RPM
- **Tier 2+**: Higher limits

Check [OpenAI Rate Limits](https://platform.openai.com/docs/guides/rate-limits) for details.

## Monitoring

### Check API Usage

View API usage statistics in the web dashboard:
1. Navigate to `http://localhost:5000/ai_dashboard`
2. View token usage by model
3. Monitor fallback events in the logs

### Log Files

All API events are logged to:
- `logs/session_*.log` - Main bot logs
- Console output when running the bot directly

## Testing

The fallback system has been thoroughly tested with automated tests:

```bash
python3 test_api_fallback.py
```

Test coverage includes:
- ✅ Gemini quota exhaustion → OpenAI fallback
- ✅ OpenAI quota exhaustion → Gemini fallback
- ✅ Both APIs down error handling

## Troubleshooting

### Fallback Not Working

1. **Check API keys**: Ensure both `GEMINI_API_KEY` and `OPENAI_API_KEY` are set in `.env`
2. **Verify configuration**: Check that `config/config.json` has valid API settings
3. **Check logs**: Look for fallback warnings in the logs
4. **Restart bot**: After changing `.env`, restart the bot to reload configuration

### Frequent Fallbacks

If you see frequent fallbacks to the alternative provider:

1. **Upgrade your API tier**: Consider upgrading your API plan for higher limits
2. **Switch primary provider**: Change the primary provider in `config/config.json`
3. **Rate limit implementation**: The bot doesn't currently implement rate limiting - this could be added if needed

### Performance Impact

Fallback adds minimal latency:
- Detection: ~0ms (checks HTTP status code)
- Fallback attempt: +1-2 seconds (new API connection)
- Total user impact: Usually under 2 seconds

## Future Improvements

Potential enhancements to the fallback system:

1. **Rate limiting**: Implement client-side rate limiting to prevent quota exhaustion
2. **Retry logic**: Add exponential backoff for transient errors
3. **Provider health monitoring**: Track provider reliability and automatically adjust primary provider
4. **Cost optimization**: Route requests based on cost and quota availability
5. **Multiple fallback layers**: Support for additional providers (Anthropic Claude, etc.)

## Summary

The API fallback system provides:
- ✅ Automatic failover when quota limits are reached
- ✅ Transparent to end users
- ✅ Comprehensive error handling
- ✅ Detailed logging for debugging
- ✅ Support for all AI-powered features
- ✅ Zero configuration required (works with existing setup)

This ensures the bot remains responsive even when API quotas are exhausted, providing a better experience for Discord users.
