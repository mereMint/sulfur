import aiohttp
import json
from collections import deque
from datetime import datetime, timezone

# --- NEW: Import structured logging ---
from modules.logger_utils import api_logger as logger

# --- Constants ---
GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
OPENAI_API_BASE_URL = "https://api.openai.com/v1/chat/completions"

# Models that require 'max_completion_tokens' instead of 'max_tokens'
# These are newer OpenAI models that use the updated API parameter
MODELS_REQUIRING_MAX_COMPLETION_TOKENS = {
    # GPT-5 series
    "gpt-5-nano", "gpt-5-mini", "gpt-5", "gpt-5-turbo",
    # GPT-4.1 series (new naming convention)
    "gpt-4.1-nano", "gpt-4.1-mini", "gpt-4.1",
    # o-series reasoning models (o1, o3, o4, etc.)
    "o1", "o1-mini", "o1-preview",
    "o3", "o3-mini",
    "o4", "o4-mini",
}

# --- Model Pricing (USD per 1M tokens) ---
# Used for calculating API usage costs
MODEL_PRICING = {
    # Gemini Models (per 1M tokens)
    "gemini-2.5-pro": {"input": 1.25, "output": 10.00},
    "gemini-2.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-2.5-flash-lite": {"input": 0.02, "output": 0.10},
    "gemini-2.0-flash-exp": {"input": 0.075, "output": 0.30},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-pro": {"input": 0.50, "output": 1.50},
    # OpenAI Models (per 1M tokens)
    "gpt-5-nano": {"input": 0.05, "output": 0.20},
    "gpt-5-mini": {"input": 0.15, "output": 0.60},
    "gpt-4.1-nano": {"input": 0.10, "output": 0.40},
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "o1": {"input": 15.00, "output": 60.00},
    "o1-mini": {"input": 1.10, "output": 4.40},
    "o3-mini": {"input": 1.10, "output": 4.40},
    # Default fallback for unknown models
    "default": {"input": 1.00, "output": 3.00}
}


def get_model_pricing(model_name: str) -> dict:
    """
    Get pricing information for a specific model.
    
    Args:
        model_name: The name of the AI model
        
    Returns:
        dict with 'input' and 'output' prices per 1M tokens
    """
    return MODEL_PRICING.get(model_name, MODEL_PRICING["default"])


def uses_max_completion_tokens(model_name: str) -> bool:
    """
    Check if a model requires 'max_completion_tokens' instead of 'max_tokens'.
    
    Newer OpenAI models (gpt-5-*, gpt-4.1-*, o1, o3, etc.) require the
    'max_completion_tokens' parameter instead of the deprecated 'max_tokens'.
    
    Args:
        model_name: The name of the AI model
        
    Returns:
        True if the model requires 'max_completion_tokens', False otherwise
    """
    # Check exact match first
    if model_name in MODELS_REQUIRING_MAX_COMPLETION_TOKENS:
        return True
    
    # Check prefix patterns for future-proofing
    prefixes_requiring_new_param = ('gpt-5', 'gpt-4.1', 'o1', 'o3', 'o4')
    for prefix in prefixes_requiring_new_param:
        if model_name.startswith(prefix):
            return True
    
    return False


def build_openai_payload(model_name: str, messages: list, max_tokens: int, temperature: float = None) -> dict:
    """
    Build a payload for OpenAI API calls with the correct token limit parameter.
    
    Args:
        model_name: The name of the AI model
        messages: List of message dictionaries
        max_tokens: Maximum number of tokens to generate
        temperature: Optional temperature setting (not used for reasoning models)
        
    Returns:
        Dictionary payload for the OpenAI API
    """
    payload = {
        "model": model_name,
        "messages": messages,
    }
    
    # Use the correct token limit parameter based on model
    if uses_max_completion_tokens(model_name):
        payload["max_completion_tokens"] = max_tokens
    else:
        payload["max_tokens"] = max_tokens
    
    # Add temperature if provided and model supports it
    is_reasoning_model = model_name.startswith('o1') or model_name.startswith('o3') or model_name.startswith('o4')
    if temperature is not None and not is_reasoning_model:
        payload["temperature"] = temperature
    
    return payload


def calculate_cost(model_name: str, input_tokens: int, output_tokens: int) -> float:
    """
    Calculate the cost of an API call based on token usage.
    
    Args:
        model_name: The name of the AI model used
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        
    Returns:
        Cost in USD
    """
    pricing = get_model_pricing(model_name)
    # Convert from per-1M-tokens to actual cost
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return input_cost + output_cost

# --- REFACTORED: Centralized Gemini API call logic ---
async def _call_gemini_api(payload, model_name, api_key, timeout):
    """
    A centralized function to handle all calls to the Gemini API.
    Returns: (response_text, error, usage_metadata, is_quota_error)
    where is_quota_error is True for 429 status codes (quota exhausted)
    """
    api_url = f"{GEMINI_API_BASE_URL}/{model_name}:generateContent?key={api_key}"
    
    logger.info(f"[Gemini API] Calling model '{model_name}'")
    logger.debug(f"[Gemini API] URL: {api_url[:80]}...")
    print(f"[Gemini API] Making request to model '{model_name}'...")
    
    try:
        async with aiohttp.ClientSession() as session:
            logger.debug(f"[Gemini API] Session created, sending POST request")
            print(f"[Gemini API] Sending POST request with timeout={timeout}...")
            async with session.post(api_url, json=payload, timeout=timeout) as response:
                logger.info(f"[Gemini API] Response status: {response.status}")
                print(f"[Gemini API] Got response with status {response.status}")
                
                if response.status == 200:
                    logger.debug(f"[Gemini API] Parsing JSON response")
                    data = await response.json()
                    # Robust checking for valid API response content
                    if data.get('candidates') and data['candidates'][0].get('content') and data['candidates'][0]['content'].get('parts'):
                        response_text = data['candidates'][0]['content']['parts'][0]['text']
                        
                        # Extract token usage from response
                        usage_metadata = data.get('usageMetadata', {})
                        input_tokens = usage_metadata.get('promptTokenCount', 0)
                        output_tokens = usage_metadata.get('candidatesTokenCount', 0)
                        
                        logger.info(f"[Gemini API] Success - got {len(response_text)} chars, tokens: {input_tokens} in / {output_tokens} out")
                        print(f"[Gemini API] Success - received {len(response_text)} character response, tokens: {input_tokens}/{output_tokens}")
                        return response_text, None, (input_tokens, output_tokens), False
                    else:
                        # This happens if the response was blocked for safety or other reasons.
                        error_reason = data.get('promptFeedback', {}).get('blockReason', 'UNKNOWN')
                        if not error_reason:
                             error_reason = data.get('candidates', [{}])[0].get('finishReason', 'UNKNOWN')
                        logger.warning(f"[Gemini API] No content in response. Finish Reason: {error_reason}")
                        logger.debug(f"[Gemini API] Full API response: {data}")
                        print(f"[Gemini API] Error: No content in response. Finish Reason: {error_reason}")
                        print(f"[Gemini API] Full API response: {data}")
                        return None, f"Meine Antwort wurde blockiert (Grund: {error_reason}). Versuchs mal anders zu formulieren.", (0, 0), False
                else:
                    # --- NEW: Add specific diagnostic for 404 errors ---
                    if response.status == 404:
                        error_text = await response.text()
                        logger.error(f"[Gemini API] 404 Error: {error_text}")
                        print(f"[Gemini API] Error (Status 404): {error_text}")
                        return None, f"Modell '{model_name}' nicht gefunden (404). **Überprüfe, ob die 'Generative Language API' in deinem Google Cloud Projekt aktiviert ist und dein API-Schlüssel die Berechtigung dafür hat.**", (0, 0), False
                    # --- NEW: Detect 429 errors (quota exhausted) for fallback ---
                    elif response.status == 429:
                        error_text = await response.text()
                        logger.error(f"[Gemini API] HTTP 429 (Quota Exhausted): {error_text}")
                        print(f"[Gemini API] Quota exhausted (Status 429): {error_text}")
                        return None, f"Gemini API-Quota erschöpft (Status: 429). Versuche es später erneut oder verwende einen anderen Provider.", (0, 0), True
                    error_text = await response.text()
                    logger.error(f"[Gemini API] HTTP {response.status}: {error_text}")
                    print(f"[Gemini API] Error (Status {response.status}): {error_text}")
                    return None, f"Ich habe einen Fehler vom Server erhalten (Status: {response.status}). Wahrscheinlich ist die API down oder dein Key ist ungültig.", (0, 0), False
    except aiohttp.ClientError as e:
        logger.error(f"[Gemini API] Network error: {e}", exc_info=True)
        print(f"[Gemini API] Network error: {e}")
        return None, f"Netzwerkfehler beim Erreichen der Gemini API: {str(e)}", (0, 0), False
    except Exception as e:
        logger.error(f"[Gemini API] Exception: {e}", exc_info=True)
        print(f"[Gemini API] An exception occurred while calling Gemini API: {e}")
        return None, "Ich konnte die AI nicht erreichen. Überprüfe die Internetverbindung oder die API-Keys.", (0, 0), False

async def get_chat_response(history, user_prompt, user_display_name, system_prompt, config, gemini_key, openai_key):
    """
    Gets a chat response from the configured AI provider (Gemini or OpenAI).
    This function now correctly builds the Gemini URL with the model from the config.
    """
    provider = config.get('api', {}).get('provider', 'gemini')
    timeout = config.get('api', {}).get('timeout', 30)

    logger.info(f"[Chat API] Starting chat response generation via '{provider}'")
    logger.debug(f"[Chat API] History length: {len(history)}, Timeout: {timeout}s")
    print(f"[Chat API] Provider: {provider}, History: {len(history)} messages")

    # --- FIX: Validate and clean the history to ensure alternating roles ---
    # The Gemini API requires a strict user -> model -> user -> model sequence.
    clean_history = deque()
    last_role = None
    # --- FIX: Create a copy of the history to avoid modifying the original list ---
    local_history = list(history)
    for msg in local_history:
        # Skip if the role is the same as the last one
        if msg.get('role') == last_role:
            continue
        clean_history.append(msg)
        last_role = msg.get('role')

    while clean_history and clean_history[0].get('role') != 'user':
        clean_history.popleft()

    final_history_for_api = list(clean_history)
    logger.debug(f"[Chat API] Cleaned history: {len(final_history_for_api)} messages")
    print(f"[Chat API] Cleaned history to {len(final_history_for_api)} alternating messages")

    # Add the current user prompt to the history for this specific API call
    # Format with clear attribution to help AI track who said what
    user_message_with_attribution = f"User '{user_display_name}' said: {user_prompt}"
    final_history_for_api.append({"role": "user", "parts": [{"text": user_message_with_attribution}]})
    logger.debug(f"[Chat API] Added current user prompt to history with attribution")
    print(f"[Chat API] Added user prompt: '{user_prompt[:50]}...'")

    if provider == 'gemini':
        # --- FIX: Dynamically build the URL with the model from config ---
        model = config.get('api', {}).get('gemini', {}).get('model', 'gemini-2.5-flash')
        generation_config = config.get('api', {}).get('gemini', {}).get('generation_config', {})
        
        logger.info(f"[Chat API] Using Gemini model: {model}")
        print(f"[Chat API] Gemini model: {model}")
        
        # --- FIX: Prepend system prompt to contents instead of using system_instruction ---
        # This is more compatible with newer models like gemini-1.5-flash.
        final_contents = [{"role": "user", "parts": [{"text": system_prompt}]}, {"role": "model", "parts": [{"text": "Understood."}]}] + final_history_for_api
        logger.debug(f"[Chat API] Final contents length: {len(final_contents)}")
        print(f"[Chat API] Prepared {len(final_contents)} content items for API call")
        
        # --- FIX: Add safety settings to prevent blocking ---
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]

        payload = {
            "contents": final_contents,
            "generationConfig": generation_config,
            "safetySettings": safety_settings
        }
        
        logger.debug(f"[Chat API] Calling Gemini API with payload size: {len(str(payload))} chars")
        print(f"[Chat API] Sending request to Gemini API...")
        response_text, error, usage_data, is_quota_error = await _call_gemini_api(payload, model, gemini_key, timeout)
        
        # --- NEW: Check for quota error and fallback to OpenAI if available ---
        if is_quota_error and openai_key:
            logger.warning(f"[Chat API] Gemini quota exhausted (429), attempting fallback to OpenAI")
            print(f"[Chat API] Gemini quota exhausted, falling back to OpenAI...")
            # Recursively call with OpenAI provider
            temp_config = config.copy()
            temp_config['api'] = config['api'].copy()
            temp_config['api']['provider'] = 'openai'
            response_text, fallback_error, final_history_for_api = await get_chat_response(
                history, user_prompt, user_display_name, system_prompt, temp_config, gemini_key, openai_key
            )
            if response_text:
                # Add a note that we used fallback
                logger.info(f"[Chat API] Successfully fell back to OpenAI after Gemini quota exhaustion")
                print(f"[Chat API] Fallback to OpenAI successful")
                return response_text, None, final_history_for_api
            else:
                logger.error(f"[Chat API] Fallback to OpenAI also failed: {fallback_error}")
                return None, f"Beide APIs sind nicht verfügbar. Gemini: Quota erschöpft. OpenAI: {fallback_error}", final_history_for_api
        
        # Log API usage to database
        input_tokens, output_tokens = usage_data
        if input_tokens > 0 or output_tokens > 0:
            from modules.db_helpers import log_api_usage
            await log_api_usage(model, input_tokens, output_tokens)
            logger.debug(f"[Chat API] Logged API usage: {input_tokens} input / {output_tokens} output tokens")
        
        if response_text:
            # --- FIX: Return the updated history instead of modifying it in-place ---
            final_history_for_api.append({"role": "model", "parts": [{"text": response_text}]})
            logger.info(f"[Chat API] Gemini response received successfully")
            print(f"[Chat API] Gemini call succeeded, updating history")
        elif error:
            logger.error(f"[Chat API] Gemini call failed: {error}")
            print(f"[Chat API] Gemini call failed with error")
        # The `history` object passed from bot.py is no longer modified.
        return response_text, error, final_history_for_api

    elif provider == 'openai':
        model = config.get('api', {}).get('openai', {}).get('chat_model', 'gpt-4o-mini')
        temperature = config.get('api', {}).get('openai', {}).get('chat_temperature', 0.7)
        max_tokens = config.get('api', {}).get('openai', {}).get('chat_max_tokens', 2048)

        logger.info(f"[Chat API] Using OpenAI model: {model}")
        print(f"[Chat API] OpenAI model: {model}")

        headers = {"Authorization": f"Bearer {openai_key}"}
        
        # Convert Gemini history format to OpenAI format
        messages = [{"role": "system", "content": system_prompt}]
        for item in final_history_for_api:
            role = "assistant" if item['role'] == 'model' else item['role']
            content = item['parts'][0]['text']
            messages.append({"role": role, "content": content})

        # Build payload with correct token parameter for the model
        payload = build_openai_payload(model, messages, max_tokens, temperature)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(OPENAI_API_BASE_URL, json=payload, headers=headers, timeout=timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        response_text = data['choices'][0]['message']['content']
                        
                        # Extract token usage from response
                        usage_data = data.get('usage', {})
                        input_tokens = usage_data.get('prompt_tokens', 0)
                        output_tokens = usage_data.get('completion_tokens', 0)
                        
                        # Log API usage to database
                        if input_tokens > 0 or output_tokens > 0:
                            from modules.db_helpers import log_api_usage
                            await log_api_usage(model, input_tokens, output_tokens)
                            logger.debug(f"[Chat API] Logged API usage: {input_tokens} input / {output_tokens} output tokens")
                        
                        # --- FIX: Return the updated history ---
                        final_history_for_api.append({"role": "model", "parts": [{"text": response_text}]})
                        return response_text, None, final_history_for_api
                    elif response.status == 429:
                        # --- NEW: Handle OpenAI quota exhaustion and fallback to Gemini ---
                        error_text = await response.text()
                        logger.error(f"[OpenAI API] HTTP 429 (Quota Exhausted): {error_text}")
                        print(f"[OpenAI API] Quota exhausted (Status 429): {error_text}")
                        
                        if gemini_key:
                            logger.warning(f"[Chat API] OpenAI quota exhausted (429), attempting fallback to Gemini")
                            print(f"[Chat API] OpenAI quota exhausted, falling back to Gemini...")
                            # Recursively call with Gemini provider
                            temp_config = config.copy()
                            temp_config['api'] = config['api'].copy()
                            temp_config['api']['provider'] = 'gemini'
                            response_text, fallback_error, final_history_for_api = await get_chat_response(
                                history, user_prompt, user_display_name, system_prompt, temp_config, gemini_key, openai_key
                            )
                            if response_text:
                                logger.info(f"[Chat API] Successfully fell back to Gemini after OpenAI quota exhaustion")
                                print(f"[Chat API] Fallback to Gemini successful")
                                return response_text, None, final_history_for_api
                            else:
                                logger.error(f"[Chat API] Fallback to Gemini also failed: {fallback_error}")
                                return None, f"Beide APIs sind nicht verfügbar. OpenAI: Quota erschöpft. Gemini: {fallback_error}", final_history_for_api
                        else:
                            return None, f"OpenAI API-Quota erschöpft (Status: 429). Versuche es später erneut oder verwende einen anderen Provider.", final_history_for_api
                    else:
                        error_text = await response.text()
                        print(f"OpenAI API Error (Status {response.status}): {error_text}")
                        return None, f"Ich habe einen Fehler vom OpenAI-Server erhalten (Status: {response.status}).", final_history_for_api
        except Exception as e:
            logger.error(f"Exception calling OpenAI API: {e}", exc_info=True)
            print(f"An exception occurred while calling OpenAI API: {e}")
            return None, "Ich konnte die OpenAI-AI nicht erreichen. Überprüfe die Internetverbindung oder die API-Keys.", final_history_for_api

    return None, "Ungültiger API-Provider in der Konfiguration.", history


async def get_relationship_summary_from_api(history, user_display_name, old_summary, config, gemini_key, openai_key):
    """Generates a new relationship summary based on chat history."""
    provider = config.get('api', {}).get('provider') # Use the provider from the passed config
    timeout = config.get('api', {}).get('timeout', 30)

    prompt = f"""
    You are Sulfur, a Discord bot with a sarcastic, judgmental personality. Based on the following chat history with '{user_display_name}', create an insightful relationship summary.
    
    Previous summary: "{old_summary if old_summary else 'None - this is our first interaction'}"
    
    Recent chat history:
    ---
    {json.dumps(history, indent=2)}
    ---
    
    Create a new, detailed 2-3 sentence summary of your relationship with {user_display_name} from your perspective (first person).
    The summary should:
    - Capture their personality, communication style, and recurring themes
    - Note any interesting patterns, inside jokes, or memorable moments
    - Reflect your sarcastic, judgmental personality while being useful for future conversations
    - Be in first person (e.g., "They're the type who...", "I've noticed they often...", "We have this running joke about...")
    - ONLY include information that's actually in the provided chat history - don't make assumptions
    - Focus on patterns and vibes rather than specific claims about what they said or did
    
    Make it personal, specific, and useful for remembering this person in future chats. Don't be generic.
    """

    if provider == 'gemini':
        model = config.get('api', {}).get('gemini', {}).get('utility_model', config.get('api', {}).get('gemini', {}).get('model', 'gemini-2.5-flash'))
        generation_config = config.get('api', {}).get('gemini', {}).get('utility_generation_config', {})
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        payload = {
            "contents": [{"parts": [{"text": prompt}]}], 
            "generationConfig": generation_config,
            "safetySettings": safety_settings
        }
        summary, error, usage_data, is_quota_error = await _call_gemini_api(payload, model, gemini_key, timeout)
        
        # --- NEW: Handle quota exhaustion with fallback to OpenAI ---
        if is_quota_error and openai_key:
            logger.warning(f"[Relationship Summary] Gemini quota exhausted, falling back to OpenAI")
            fallback_model = config.get('api', {}).get('openai', {}).get('utility_model', 'gpt-4o-mini')
            fallback_temperature = config.get('api', {}).get('openai', {}).get('utility_temperature', 0.7)
            fallback_max_tokens = config.get('api', {}).get('openai', {}).get('utility_max_tokens', 150)
            headers = {"Authorization": f"Bearer {openai_key}"}
            messages = [{"role": "user", "content": prompt}]
            payload_openai = build_openai_payload(fallback_model, messages, fallback_max_tokens, fallback_temperature)
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(OPENAI_API_BASE_URL, json=payload_openai, headers=headers, timeout=timeout) as response:
                        if response.status == 200:
                            data = await response.json()
                            summary = data['choices'][0]['message']['content'].strip()
                            usage_data_fallback = data.get('usage', {})
                            input_tokens = usage_data_fallback.get('prompt_tokens', 0)
                            output_tokens = usage_data_fallback.get('completion_tokens', 0)
                            if input_tokens > 0 or output_tokens > 0:
                                from modules.db_helpers import log_api_usage
                                await log_api_usage(fallback_model, input_tokens, output_tokens)
                            error = None
                        else:
                            error = f"Fallback API Error {response.status}"
            except Exception as e:
                error = str(e)
        
        # Log API usage
        input_tokens, output_tokens = usage_data
        if input_tokens > 0 or output_tokens > 0:
            from modules.db_helpers import log_api_usage
            await log_api_usage(model, input_tokens, output_tokens)
        
        return summary.strip() if summary else None, error

    elif provider == 'openai':
        model = config.get('api', {}).get('openai', {}).get('utility_model', 'gpt-4o-mini')
        temperature = config.get('api', {}).get('openai', {}).get('utility_temperature', 0.7)
        max_tokens = config.get('api', {}).get('openai', {}).get('utility_max_tokens', 150)
        headers = {"Authorization": f"Bearer {openai_key}"}
        
        # For OpenAI, the prompt is a simple user message.
        messages = [{"role": "user", "content": prompt}]

        payload = build_openai_payload(model, messages, max_tokens, temperature)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(OPENAI_API_BASE_URL, json=payload, headers=headers, timeout=timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        response_text = data['choices'][0]['message']['content'].strip()
                        
                        # Log API usage
                        usage_data = data.get('usage', {})
                        input_tokens = usage_data.get('prompt_tokens', 0)
                        output_tokens = usage_data.get('completion_tokens', 0)
                        if input_tokens > 0 or output_tokens > 0:
                            from modules.db_helpers import log_api_usage
                            await log_api_usage(model, input_tokens, output_tokens)
                        
                        return response_text, None
                    else:
                        error_text = await response.text()
                        print(f"OpenAI API Error (get_relationship_summary): {error_text}")
                        return None, f"API Error {response.status}"
        except Exception as e:
            return None, str(e)

    return None, "Invalid provider for relationship summary."

async def get_werwolf_tts_message(event_text, config, gemini_key, openai_key):
    """Generates a short, dramatic TTS message for a Werwolf game event."""
    provider = config.get('api', {}).get('provider', 'gemini')
    timeout = config.get('api', {}).get('timeout', 30)
    
    prompt = f"""
    Du bist der Erzähler für ein Werwolf-Spiel.
    Das folgende Ereignis ist gerade passiert: "{event_text}"
    Deine Aufgabe ist es, eine sehr kurze, dramatische, einzelne Ankündigung für dieses Ereignis zu erstellen, die von einer Text-zu-Sprache (TTS) Engine gelesen werden kann.
    Halte es unter 150 Zeichen. Verwende kein Markdown.
    Beispiel: Wenn das Ereignis "Die Dorfbewohner haben beschlossen, Steve zu lynchen" ist, könntest du sagen: "Der Mob hat sein Opfer gewählt. Steve wird gelyncht."
    
    Generiere den TTS-Satz für das Ereignis: "{event_text}"
    """
    
    if provider == 'gemini':
        model = config.get('api', {}).get('gemini', {}).get('utility_model', config.get('api', {}).get('gemini', {}).get('model', 'gemini-2.5-flash'))
        generation_config = config.get('api', {}).get('gemini', {}).get('utility_generation_config', {})
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        payload = {
            "contents": [{"parts": [{"text": prompt}]}], 
            "generationConfig": generation_config,
            "safetySettings": safety_settings
        }
        tts_text, _, usage_data, is_quota_error = await _call_gemini_api(payload, model, gemini_key, timeout)
        
        # --- NEW: Handle quota exhaustion with fallback to OpenAI ---
        if is_quota_error and openai_key:
            logger.warning(f"[Werwolf TTS] Gemini quota exhausted, falling back to OpenAI")
            fallback_model = config.get('api', {}).get('openai', {}).get('utility_model', 'gpt-4o-mini')
            fallback_temperature = config.get('api', {}).get('openai', {}).get('utility_temperature', 0.7)
            fallback_max_tokens = config.get('api', {}).get('openai', {}).get('utility_max_tokens', 50)
            headers = {"Authorization": f"Bearer {openai_key}"}
            messages = [{"role": "user", "content": prompt}]
            payload_openai = build_openai_payload(fallback_model, messages, fallback_max_tokens, fallback_temperature)
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(OPENAI_API_BASE_URL, json=payload_openai, headers=headers, timeout=timeout) as response:
                        if response.status == 200:
                            data = await response.json()
                            tts_text = data['choices'][0]['message']['content'].strip().replace("*", "")
                            usage_data_fallback = data.get('usage', {})
                            input_tokens = usage_data_fallback.get('prompt_tokens', 0)
                            output_tokens = usage_data_fallback.get('completion_tokens', 0)
                            if input_tokens > 0 or output_tokens > 0:
                                from modules.db_helpers import log_api_usage
                                await log_api_usage(fallback_model, input_tokens, output_tokens)
                        else:
                            error_text = await response.text()
                            print(f"Fallback OpenAI API Error (Status {response.status}): {error_text}")
            except Exception as e:
                print(f"Fallback to OpenAI failed for TTS: {e}")
        
        # Log API usage
        input_tokens, output_tokens = usage_data
        if input_tokens > 0 or output_tokens > 0:
            from modules.db_helpers import log_api_usage
            await log_api_usage(model, input_tokens, output_tokens)
        return tts_text.strip().replace("*", "") if tts_text else event_text

    elif provider == 'openai':
        model = config.get('api', {}).get('openai', {}).get('utility_model', 'gpt-4o-mini')
        temperature = config.get('api', {}).get('openai', {}).get('utility_temperature', 0.7)
        max_tokens = config.get('api', {}).get('openai', {}).get('utility_max_tokens', 50) # Short response
        headers = {"Authorization": f"Bearer {openai_key}"}
        messages = [{"role": "user", "content": prompt}]
        payload = build_openai_payload(model, messages, max_tokens, temperature)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(OPENAI_API_BASE_URL, json=payload, headers=headers, timeout=timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        response_text = data['choices'][0]['message']['content'].strip().replace("*", "")
                        
                        # Log API usage
                        usage_data = data.get('usage', {})
                        input_tokens = usage_data.get('prompt_tokens', 0)
                        output_tokens = usage_data.get('completion_tokens', 0)
                        if input_tokens > 0 or output_tokens > 0:
                            from modules.db_helpers import log_api_usage
                            await log_api_usage(model, input_tokens, output_tokens)
                        
                        return response_text
                    else:
                        print(f"OpenAI API Error (get_werwolf_tts_message): {await response.text()}")
                        return event_text # Fallback
        except Exception as e:
            print(f"An exception occurred while calling OpenAI API for TTS: {e}")
            return event_text # Fallback
    return event_text

async def get_random_names(count, db_helpers, config, gemini_key, openai_key):
    """Gets random names for Werwolf bots, from DB or API."""
    names = await db_helpers.get_and_remove_bot_names(count)
    needed = count - len(names)

    if needed > 0:
        print(f"  [WW] Name pool low. Fetching {needed} new names from API...")
        provider = config.get('api', {}).get('provider', 'gemini')
        timeout = config.get('api', {}).get('timeout', 30)
        
        prompt = f"Generate a list of {needed} unique, random, gender-neutral German first names. Output them as a simple comma-separated list, and nothing else. Example: Alex, Kai, Jo, Chris"
        
        if provider == 'gemini':
            model = config.get('api', {}).get('gemini', {}).get('utility_model', config.get('api', {}).get('gemini', {}).get('model', 'gemini-2.5-flash'))
            generation_config = config.get('api', {}).get('gemini', {}).get('utility_generation_config', {})
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
            payload = {
                "contents": [{"parts": [{"text": prompt}]}], 
                "generationConfig": generation_config,
                "safetySettings": safety_settings
            }
            new_names_text, error, usage_data, is_quota_error = await _call_gemini_api(payload, model, gemini_key, timeout)
            
            # --- NEW: Handle quota exhaustion with fallback to OpenAI ---
            if is_quota_error and openai_key:
                logger.warning(f"[Random Names] Gemini quota exhausted, falling back to OpenAI")
                fallback_model = config.get('api', {}).get('openai', {}).get('utility_model', 'gpt-4o-mini')
                fallback_temperature = config.get('api', {}).get('openai', {}).get('utility_temperature', 1.0)
                fallback_max_tokens = config.get('api', {}).get('openai', {}).get('utility_max_tokens', 200)
                headers = {"Authorization": f"Bearer {openai_key}"}
                messages = [{"role": "user", "content": prompt}]
                payload_openai = build_openai_payload(fallback_model, messages, fallback_max_tokens, fallback_temperature)
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(OPENAI_API_BASE_URL, json=payload_openai, headers=headers, timeout=timeout) as response:
                            if response.status == 200:
                                data = await response.json()
                                new_names_text = data['choices'][0]['message']['content']
                                usage_data_fallback = data.get('usage', {})
                                input_tokens = usage_data_fallback.get('prompt_tokens', 0)
                                output_tokens = usage_data_fallback.get('completion_tokens', 0)
                                if input_tokens > 0 or output_tokens > 0:
                                    from modules.db_helpers import log_api_usage
                                    await log_api_usage(fallback_model, input_tokens, output_tokens)
                                error = None
                            else:
                                error_text = await response.text()
                                print(f"  [WW] Fallback OpenAI API Error (Status {response.status}): {error_text}")
                except Exception as e:
                    print(f"  [WW] Fallback to OpenAI failed: {e}")
            
            # Log API usage
            input_tokens, output_tokens = usage_data
            if input_tokens > 0 or output_tokens > 0:
                from modules.db_helpers import log_api_usage
                await log_api_usage(model, input_tokens, output_tokens)
            if new_names_text:
                new_names = [name.strip() for name in new_names_text.split(',')]
                await db_helpers.add_bot_names_to_pool(new_names)
                # Now fetch the names we just added
                names.extend(await db_helpers.get_and_remove_bot_names(needed))
        
        elif provider == 'openai':
            model = config.get('api', {}).get('openai', {}).get('utility_model', 'gpt-4o-mini')
            temperature = config.get('api', {}).get('openai', {}).get('utility_temperature', 1.0)
            max_tokens = config.get('api', {}).get('openai', {}).get('utility_max_tokens', 200)
            headers = {"Authorization": f"Bearer {openai_key}"}
            messages = [{"role": "user", "content": prompt}]
            payload = build_openai_payload(model, messages, max_tokens, temperature)

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(OPENAI_API_BASE_URL, json=payload, headers=headers, timeout=timeout) as response:
                        if response.status == 200:
                            data = await response.json()
                            new_names_text = data['choices'][0]['message']['content']
                            
                            # Log API usage
                            usage_data = data.get('usage', {})
                            input_tokens = usage_data.get('prompt_tokens', 0)
                            output_tokens = usage_data.get('completion_tokens', 0)
                            if input_tokens > 0 or output_tokens > 0:
                                from modules.db_helpers import log_api_usage
                                await log_api_usage(model, input_tokens, output_tokens)
                            new_names = [name.strip() for name in new_names_text.split(',')]
                            await db_helpers.add_bot_names_to_pool(new_names)
                            names.extend(await db_helpers.get_and_remove_bot_names(needed))
                        else:
                            print(f"OpenAI API Error (get_random_names): {await response.text()}")
            except Exception as e:
                print(f"  [WW] Failed to fetch new names from OpenAI API: {e}")

    # Fallback if API fails
    if len(names) < count:
        print("  [WW] API failed. Using generic bot names as fallback.")
        names.extend([f"Bot {i}" for i in range(len(names) + 1, count + 1)])

    return names[:count]

async def get_wrapped_summary_from_api(user_display_name, stats, config, gemini_key, openai_key):
    """
    Generates a personalized, comprehensive analysis for the Wrapped feature.
    Provides detailed behavioral insights with the bot's sarcastic personality in German.
    """
    provider = config.get('api', {}).get('provider', 'gemini')
    timeout = config.get('api', {}).get('timeout', 30)
    
    prompt = f"""
    You are Sulfur, a Discord bot with a sarcastic, judgmental but ultimately entertaining personality.
    User '{user_display_name}' just received their monthly stats summary ("Wrapped").
    
    Here are their detailed stats: {json.dumps(stats, indent=2)}
    
    Write a personalized 2-3 sentence verdict that:
    - Analyzes their behavior patterns and what they reveal about the person
    - References specific stats in a clever, sarcastic way
    - Includes at least one insightful observation or comparison
    - Ends with a funny roast or backhanded compliment
    - Speaks in German (DE) to match your personality
    
    Examples of style:
    - "Du hast {stats.get('vc_hours', 0)} Stunden in VC verbracht - ich hoffe, du hast zumindest was Produktives getan und nicht nur AFK rumgehangen. Mit {stats.get('message_count', 0)} Nachrichten bist du eindeutig der Typ, der jeden Gedanken sofort raushauen muss."
    - "Deine Top-Aktivität war {stats.get('top_activity', 'existieren')}? Interessante Lebensentscheidung. Aber hey, wenigstens bist du konsequent dabei geblieben."
    
    Be creative, specific, and make it memorable. Make them laugh while subtly calling out their habits.
    """
    
    if provider == 'gemini':
        model = config.get('api', {}).get('gemini', {}).get('utility_model', config.get('api', {}).get('gemini', {}).get('model', 'gemini-2.5-flash'))
        generation_config = config.get('api', {}).get('gemini', {}).get('utility_generation_config', {})
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        payload = {
            "contents": [{"parts": [{"text": prompt}]}], 
            "generationConfig": generation_config,
            "safetySettings": safety_settings
        }
        summary, error, usage_data, is_quota_error = await _call_gemini_api(payload, model, gemini_key, timeout)
        
        # --- NEW: Handle quota exhaustion with fallback to OpenAI ---
        if is_quota_error and openai_key:
            logger.warning(f"[Wrapped Summary] Gemini quota exhausted, falling back to OpenAI")
            fallback_model = config.get('api', {}).get('openai', {}).get('utility_model', 'gpt-4o-mini')
            fallback_temperature = config.get('api', {}).get('openai', {}).get('utility_temperature', 0.8)
            fallback_max_tokens = config.get('api', {}).get('openai', {}).get('utility_max_tokens', 100)
            headers = {"Authorization": f"Bearer {openai_key}"}
            messages = [{"role": "user", "content": prompt}]
            payload_openai = build_openai_payload(fallback_model, messages, fallback_max_tokens, fallback_temperature)
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(OPENAI_API_BASE_URL, json=payload_openai, headers=headers, timeout=timeout) as response:
                        if response.status == 200:
                            data = await response.json()
                            summary = data['choices'][0]['message']['content'].strip()
                            usage_data_fallback = data.get('usage', {})
                            input_tokens = usage_data_fallback.get('prompt_tokens', 0)
                            output_tokens = usage_data_fallback.get('completion_tokens', 0)
                            if input_tokens > 0 or output_tokens > 0:
                                from modules.db_helpers import log_api_usage
                                await log_api_usage(fallback_model, input_tokens, output_tokens)
                            error = None
                        else:
                            error = f"Fallback API Error {response.status}"
            except Exception as e:
                error = str(e)
        
        # Log API usage
        input_tokens, output_tokens = usage_data
        if input_tokens > 0 or output_tokens > 0:
            from modules.db_helpers import log_api_usage
            await log_api_usage(model, input_tokens, output_tokens)
        return summary.strip() if summary else "Du hast einen weiteren Monat überlebt, schätze ich.", error

    elif provider == 'openai':
        model = config.get('api', {}).get('openai', {}).get('utility_model', 'gpt-4o-mini')
        temperature = config.get('api', {}).get('openai', {}).get('utility_temperature', 0.8)
        max_tokens = config.get('api', {}).get('openai', {}).get('utility_max_tokens', 100)
        headers = {"Authorization": f"Bearer {openai_key}"}
        messages = [{"role": "user", "content": prompt}]
        payload = build_openai_payload(model, messages, max_tokens, temperature)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(OPENAI_API_BASE_URL, json=payload, headers=headers, timeout=timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        response_text = data['choices'][0]['message']['content'].strip()
                        
                        # Log API usage
                        usage_data = data.get('usage', {})
                        input_tokens = usage_data.get('prompt_tokens', 0)
                        output_tokens = usage_data.get('completion_tokens', 0)
                        if input_tokens > 0 or output_tokens > 0:
                            from modules.db_helpers import log_api_usage
                            await log_api_usage(model, input_tokens, output_tokens)
                        
                        return response_text, None
                    else:
                        print(f"OpenAI API Error (get_wrapped_summary): {await response.text()}")
                        return "Du hast... Zeug gemacht. Glückwunsch?", f"API Error {response.status}"
        except Exception as e:
            return "Mein Gehirn schmilzt, kann nicht nachdenken.", str(e)

    return "You did... stuff. Congrats?", "Invalid provider for Wrapped summary."

# --- NEW: Function to get game details from the API ---
async def get_game_details_from_api(game_names: list, config: dict, gemini_key: str, openai_key: str):
    """
    Fetches details (like an image URL) for a list of game names using the configured AI provider.
    Returns a dictionary mapping game names to their details.
    """
    provider = config.get('api', {}).get('provider', 'gemini')
    timeout = config.get('api', {}).get('timeout', 30)
    results = {}
    error_message = None

    for game_name in game_names:
        prompt = f"""
        You are a helpful assistant that provides video game information.
        For the game titled "{game_name}", provide a publicly accessible URL for its cover art or a high-quality promotional image.
        Return ONLY a raw JSON object with a single key "image" containing the URL string.
        Example: {{"image": "https://example.com/image.jpg"}}
        If you cannot find an image, return {{"image": null}}.
        """

        if provider == 'gemini':
            model = config.get('api', {}).get('gemini', {}).get('utility_model', 'gemini-2.5-flash')
            generation_config = {"response_mime_type": "application/json"} # Force JSON output
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": generation_config,
                "safetySettings": safety_settings
            }
            response_text, error, usage_data, is_quota_error = await _call_gemini_api(payload, model, gemini_key, timeout)
            
            # --- NEW: Handle quota exhaustion with fallback to OpenAI ---
            if is_quota_error and openai_key:
                logger.warning(f"[Game Details] Gemini quota exhausted, falling back to OpenAI")
                fallback_model = config.get('api', {}).get('openai', {}).get('utility_model', 'gpt-4o-mini')
                headers = {"Authorization": f"Bearer {openai_key}"}
                messages = [{"role": "system", "content": "You are a helpful assistant that returns JSON."}, {"role": "user", "content": prompt}]
                payload_openai = {"model": fallback_model, "messages": messages, "response_format": {"type": "json_object"}}
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(OPENAI_API_BASE_URL, json=payload_openai, headers=headers, timeout=timeout) as response:
                            if response.status == 200:
                                data = await response.json()
                                response_text = data['choices'][0]['message']['content']
                                usage_data_fallback = data.get('usage', {})
                                input_tokens = usage_data_fallback.get('prompt_tokens', 0)
                                output_tokens = usage_data_fallback.get('completion_tokens', 0)
                                if input_tokens > 0 or output_tokens > 0:
                                    from modules.db_helpers import log_api_usage
                                    await log_api_usage(fallback_model, input_tokens, output_tokens)
                                error = None
                            else:
                                error = f"Fallback API Error {response.status}"
                except Exception as e:
                    error = str(e)
            
            # Log API usage
            input_tokens, output_tokens = usage_data
            if input_tokens > 0 or output_tokens > 0:
                from modules.db_helpers import log_api_usage
                await log_api_usage(model, input_tokens, output_tokens)
            if error:
                error_message = error
            if response_text:
                try:
                    results[game_name] = json.loads(response_text)
                except json.JSONDecodeError:
                    print(f"  [API Helper] Failed to decode JSON for game '{game_name}': {response_text}")

        elif provider == 'openai':
            model = config.get('api', {}).get('openai', {}).get('utility_model', 'gpt-4o-mini')
            headers = {"Authorization": f"Bearer {openai_key}"}
            messages = [{"role": "system", "content": "You are a helpful assistant that returns JSON."}, {"role": "user", "content": prompt}]
            payload = {"model": model, "messages": messages, "response_format": {"type": "json_object"}}

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(OPENAI_API_BASE_URL, json=payload, headers=headers, timeout=timeout) as response:
                        if response.status == 200:
                            data = await response.json()
                            response_content = data['choices'][0]['message']['content']
                            
                            # Log API usage
                            usage_data = data.get('usage', {})
                            input_tokens = usage_data.get('prompt_tokens', 0)
                            output_tokens = usage_data.get('completion_tokens', 0)
                            if input_tokens > 0 or output_tokens > 0:
                                from modules.db_helpers import log_api_usage
                                await log_api_usage(model, input_tokens, output_tokens)
                            
                            try:
                                results[game_name] = json.loads(response_content)
                            except json.JSONDecodeError:
                                print(f"  [API Helper] Failed to decode JSON for game '{game_name}': {response_content}")
                        else:
                            error_text = await response.text()
                            print(f"OpenAI API Error (get_game_details): {error_text}")
                            error_message = f"API Error {response.status}"
            except Exception as e:
                error_message = str(e)

    return results, error_message


# --- Vision Support for Image Analysis ---

async def get_vision_analysis(image_url, prompt, config, gemini_key, openai_key):
    """
    Analyzes an image using a vision-capable AI model.
    Returns a description of the image.
    """
    provider = config.get('api', {}).get('provider', 'gemini')
    vision_model = config.get('api', {}).get('vision_model', 'gemini-2.0-flash-exp')
    timeout = config.get('api', {}).get('timeout', 30)

    if provider == 'gemini':
        # Gemini Vision API
        # Handle data URLs - extract mime type and base64 data
        if image_url.startswith('data:'):
            # Parse data URL: data:image/png;base64,<base64-data>
            parts = image_url.split(',', 1)
            if len(parts) == 2:
                mime_part = parts[0].split(':')[1].split(';')[0]  # Extract mime type
                base64_data = parts[1]  # Get base64 data without prefix
                
                image_part = {
                    "inline_data": {
                        "mime_type": mime_part,
                        "data": base64_data
                    }
                }
            else:
                # Fallback if parsing fails
                image_part = {
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": image_url
                    }
                }
        else:
            # For regular URLs, use image_url field (not supported by all models)
            image_part = {"image_url": {"url": image_url}}
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    image_part
                ]
            }],
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 1024,
            }
        }
        
        response_text, error, usage_data, is_quota_error = await _call_gemini_api(payload, vision_model, gemini_key, timeout)
        
        # --- NEW: Handle quota exhaustion with fallback to OpenAI ---
        if is_quota_error and openai_key:
            logger.warning(f"[Vision Analysis] Gemini quota exhausted, falling back to OpenAI")
            fallback_vision_model = config.get('api', {}).get('openai', {}).get('vision_model', 'gpt-4o')
            # Build vision payload with correct token parameter
            payload_openai = {
                "model": fallback_vision_model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": image_url}
                            }
                        ]
                    }
                ],
            }
            # Use correct token parameter based on model
            if uses_max_completion_tokens(fallback_vision_model):
                payload_openai["max_completion_tokens"] = 1024
            else:
                payload_openai["max_tokens"] = 1024
            try:
                async with aiohttp.ClientSession() as session:
                    headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
                    async with session.post(OPENAI_API_BASE_URL, json=payload_openai, headers=headers, timeout=timeout) as response:
                        if response.status == 200:
                            data = await response.json()
                            response_text = data['choices'][0]['message']['content']
                            usage_data_fallback = data.get('usage', {})
                            input_tokens = usage_data_fallback.get('prompt_tokens', 0)
                            output_tokens = usage_data_fallback.get('completion_tokens', 0)
                            if input_tokens > 0 or output_tokens > 0:
                                from modules.db_helpers import log_api_usage
                                await log_api_usage(fallback_vision_model, input_tokens, output_tokens)
                            error = None
                        else:
                            error = f"Fallback Vision API Error: {response.status}"
            except Exception as e:
                error = str(e)
        
        # Log API usage
        input_tokens, output_tokens = usage_data
        if input_tokens > 0 or output_tokens > 0:
            from modules.db_helpers import log_api_usage
            await log_api_usage(vision_model, input_tokens, output_tokens)
        
        return response_text, error
        
    elif provider == 'openai':
        # OpenAI Vision API (GPT-4 Vision)
        vision_model = config.get('api', {}).get('openai', {}).get('vision_model', 'gpt-4o')
        
        payload = {
            "model": vision_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url}
                        }
                    ]
                }
            ],
        }
        # Use correct token parameter based on model
        if uses_max_completion_tokens(vision_model):
            payload["max_completion_tokens"] = 1024
        else:
            payload["max_tokens"] = 1024
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
                async with session.post(OPENAI_API_BASE_URL, json=payload, headers=headers, timeout=timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        response_text = data['choices'][0]['message']['content']
                        
                        # Log API usage
                        usage_data = data.get('usage', {})
                        input_tokens = usage_data.get('prompt_tokens', 0)
                        output_tokens = usage_data.get('completion_tokens', 0)
                        if input_tokens > 0 or output_tokens > 0:
                            from modules.db_helpers import log_api_usage
                            await log_api_usage(vision_model, input_tokens, output_tokens)
                        
                        return response_text, None
                    else:
                        error_text = await response.text()
                        print(f"OpenAI Vision API Error: {error_text}")
                        return None, f"Vision API Error: {response.status}"
        except Exception as e:
            print(f"Exception calling OpenAI Vision API: {e}")
            return None, str(e)
    
    return None, "Unsupported provider for vision"


# --- Multi-Model Support ---

async def get_ai_response_with_model(prompt, model_name, config, gemini_key, openai_key, system_prompt=None, temperature=None):
    """
    Gets a response from a specific AI model.
    Supports: gemini-2.0-flash-exp, gemini-1.5-pro, gpt-4o, gpt-4-turbo, o1, o3-mini, claude-3-opus, etc.
    Note: o1 and o3 models are reasoning models and don't support temperature or system prompts.
    
    Args:
        prompt: The user prompt
        model_name: Name of the model to use
        config: Bot configuration
        gemini_key: Gemini API key
        openai_key: OpenAI API key
        system_prompt: Optional system instruction
        temperature: Optional temperature override (default 0.7 for standard tasks, can be higher for creative tasks)
    """
    timeout = config.get('api', {}).get('timeout', 30)
    
    # Use provided temperature or default to 0.7
    if temperature is None:
        temperature = 0.7
    
    # Determine provider from model name
    if model_name.startswith('gemini'):
        # Gemini models
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 8192,  # Increased from 2048 to handle longer detective cases
            }
        }
        
        # Use systemInstruction for Gemini (correct way, not as a content message)
        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }
        
        response_text, error, usage_data, is_quota_error = await _call_gemini_api(payload, model_name, gemini_key, timeout)
        
        # --- NEW: Handle quota exhaustion with fallback to OpenAI ---
        if is_quota_error and openai_key:
            logger.warning(f"[AI Response] Gemini model {model_name} quota exhausted, falling back to OpenAI gpt-4o-mini")
            # Fallback to a reasonable OpenAI model
            fallback_model = 'gpt-4o-mini'
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            payload_openai = build_openai_payload(fallback_model, messages, 8192, temperature)
            try:
                async with aiohttp.ClientSession() as session:
                    headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
                    async with session.post(OPENAI_API_BASE_URL, json=payload_openai, headers=headers, timeout=timeout) as response:
                        if response.status == 200:
                            data = await response.json()
                            response_text = data['choices'][0]['message']['content']
                            usage_data_fallback = data.get('usage', {})
                            input_tokens = usage_data_fallback.get('prompt_tokens', 0)
                            output_tokens = usage_data_fallback.get('completion_tokens', 0)
                            if input_tokens > 0 or output_tokens > 0:
                                from modules.db_helpers import log_api_usage
                                await log_api_usage(fallback_model, input_tokens, output_tokens)
                            error = None
                        else:
                            error = f"Fallback API Error: {response.status}"
            except Exception as e:
                error = str(e)
        
        # Log API usage
        input_tokens, output_tokens = usage_data
        if input_tokens > 0 or output_tokens > 0:
            from modules.db_helpers import log_api_usage
            await log_api_usage(model_name, input_tokens, output_tokens)
        
        return response_text, error
        
    elif model_name.startswith('gpt') or model_name.startswith('o'):
        # OpenAI models (including o1, o3, o4 reasoning models)
        messages = []
        
        # o1, o3, o4 models don't support system prompts or temperature
        is_reasoning_model = model_name.startswith('o1') or model_name.startswith('o3') or model_name.startswith('o4')
        
        if system_prompt and not is_reasoning_model:
            messages.append({"role": "system", "content": system_prompt})
        elif system_prompt and is_reasoning_model:
            # For reasoning models, include system prompt as part of user message
            prompt = f"{system_prompt}\n\n{prompt}"
        
        messages.append({"role": "user", "content": prompt})
        
        # Build payload with correct token parameter for the model
        # For reasoning models, don't pass temperature
        if is_reasoning_model:
            payload = build_openai_payload(model_name, messages, 2048, None)
        else:
            payload = build_openai_payload(model_name, messages, 2048, temperature)
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
                async with session.post(OPENAI_API_BASE_URL, json=payload, headers=headers, timeout=timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        response_text = data['choices'][0]['message']['content']
                        
                        # Log API usage
                        usage_data = data.get('usage', {})
                        input_tokens = usage_data.get('prompt_tokens', 0)
                        output_tokens = usage_data.get('completion_tokens', 0)
                        if input_tokens > 0 or output_tokens > 0:
                            from modules.db_helpers import log_api_usage
                            await log_api_usage(model_name, input_tokens, output_tokens)
                        
                        return response_text, None
                    else:
                        error_text = await response.text()
                        print(f"OpenAI API Error ({model_name}): {error_text}")
                        return None, f"API Error: {response.status}"
        except Exception as e:
            print(f"Exception calling OpenAI API with {model_name}: {e}")
            return None, str(e)
    
    elif model_name.startswith('claude'):
        # Anthropic Claude models (requires anthropic SDK or API)
        # Note: This would require the Anthropic API key and SDK
        return None, "Claude models not yet implemented - requires Anthropic API integration"
    
    return None, f"Unsupported model: {model_name}"


# --- Emoji Description Generation ---

async def get_emoji_description(emoji_name, emoji_url, config, gemini_key, openai_key):
    """
    Generates a MINIMAL description for an emoji using vision AI.
    
    OPTIMIZATION: Uses the cheapest model and minimal tokens to reduce API costs.
    - Reads settings from config['api']['emoji_analysis'] if available
    - Falls back to gemini-2.0-flash-exp (cheap and fast)
    - Concise prompt to minimize input tokens
    - Short output format to minimize output tokens
    """
    import re
    
    # Sanitize emoji_name to prevent prompt injection
    # Only allow alphanumeric, underscores, and hyphens
    safe_emoji_name = re.sub(r'[^a-zA-Z0-9_-]', '', emoji_name)[:50]
    if not safe_emoji_name:
        safe_emoji_name = "emoji"
    
    # Use ultra-short prompt to minimize token usage
    prompt = f'Emoji "{safe_emoji_name}": Describe in 10 words max. JSON: {{"description":"...","usage":"..."}}'
    
    # Get emoji analysis settings from config, with defaults
    emoji_settings = config.get('api', {}).get('emoji_analysis', {})
    emoji_model = emoji_settings.get('model', 'gemini-2.0-flash-exp')
    emoji_max_tokens = emoji_settings.get('max_output_tokens', 100)
    emoji_temperature = emoji_settings.get('temperature', 0.3)
    
    # Override config to use the emoji analysis settings
    emoji_config = config.copy()
    if 'api' in emoji_config:
        emoji_config['api'] = config['api'].copy()
        emoji_config['api']['vision_model'] = emoji_model
        if 'gemini' in emoji_config['api']:
            emoji_config['api']['gemini'] = config['api']['gemini'].copy()
            emoji_config['api']['gemini']['generation_config'] = {
                'temperature': emoji_temperature,
                'maxOutputTokens': emoji_max_tokens
            }
    
    response, error = await get_vision_analysis(emoji_url, prompt, emoji_config, gemini_key, openai_key)
    
    if error:
        return None, error
    
    try:
        # Try to parse the JSON response
        import json
        data = json.loads(response)
        # Map to expected format
        return {
            "description": data.get("description", "Custom emoji"),
            "usage_context": data.get("usage", "General use"),
            "emotional_tone": "Neutral"
        }, None
    except json.JSONDecodeError:
        # If not valid JSON, return the raw response (truncated)
        return {
            "description": response[:50] if response else "Custom emoji", 
            "usage_context": "General use", 
            "emotional_tone": "Neutral"
        }, None