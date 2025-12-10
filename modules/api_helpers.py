import aiohttp
import json
from collections import deque
from datetime import datetime, timezone

# --- NEW: Import structured logging ---
from modules.logger_utils import api_logger as logger

# --- Constants ---
GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
OPENAI_API_BASE_URL = "https://api.openai.com/v1/chat/completions"

# --- REFACTORED: Centralized Gemini API call logic ---
async def _call_gemini_api(payload, model_name, api_key, timeout):
    """
    A centralized function to handle all calls to the Gemini API.
    Returns: (response_text, error, usage_metadata)
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
                        return response_text, None, (input_tokens, output_tokens)
                    else:
                        # This happens if the response was blocked for safety or other reasons.
                        error_reason = data.get('promptFeedback', {}).get('blockReason', 'UNKNOWN')
                        if not error_reason:
                             error_reason = data.get('candidates', [{}])[0].get('finishReason', 'UNKNOWN')
                        logger.warning(f"[Gemini API] No content in response. Finish Reason: {error_reason}")
                        logger.debug(f"[Gemini API] Full API response: {data}")
                        print(f"[Gemini API] Error: No content in response. Finish Reason: {error_reason}")
                        print(f"[Gemini API] Full API response: {data}")
                        return None, f"Meine Antwort wurde blockiert (Grund: {error_reason}). Versuchs mal anders zu formulieren.", (0, 0)
                else:
                    # --- NEW: Add specific diagnostic for 404 errors ---
                    if response.status == 404:
                        error_text = await response.text()
                        logger.error(f"[Gemini API] 404 Error: {error_text}")
                        print(f"[Gemini API] Error (Status 404): {error_text}")
                        return None, f"Modell '{model_name}' nicht gefunden (404). **Überprüfe, ob die 'Generative Language API' in deinem Google Cloud Projekt aktiviert ist und dein API-Schlüssel die Berechtigung dafür hat.**", (0, 0)
                    error_text = await response.text()
                    logger.error(f"[Gemini API] HTTP {response.status}: {error_text}")
                    print(f"[Gemini API] Error (Status {response.status}): {error_text}")
                    return None, f"Ich habe einen Fehler vom Server erhalten (Status: {response.status}). Wahrscheinlich ist die API down oder dein Key ist ungültig.", (0, 0)
    except aiohttp.ClientError as e:
        logger.error(f"[Gemini API] Network error: {e}", exc_info=True)
        print(f"[Gemini API] Network error: {e}")
        return None, f"Netzwerkfehler beim Erreichen der Gemini API: {str(e)}", (0, 0)
    except Exception as e:
        logger.error(f"[Gemini API] Exception: {e}", exc_info=True)
        print(f"[Gemini API] An exception occurred while calling Gemini API: {e}")
        return None, "Ich konnte die AI nicht erreichen. Überprüfe die Internetverbindung oder die API-Keys.", (0, 0)

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
    final_history_for_api.append({"role": "user", "parts": [{"text": f"User '{user_display_name}' said: {user_prompt}"}]})
    logger.debug(f"[Chat API] Added current user prompt to history")
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
        response_text, error, usage_data = await _call_gemini_api(payload, model, gemini_key, timeout)
        
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

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

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
        summary, error, usage_data = await _call_gemini_api(payload, model, gemini_key, timeout)
        
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

        payload = {
            "model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens
        }

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
        tts_text, _, usage_data = await _call_gemini_api(payload, model, gemini_key, timeout)
        
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
        payload = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}

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
            new_names_text, error, usage_data = await _call_gemini_api(payload, model, gemini_key, timeout)
            
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
            payload = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}

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
    """Generates a personalized, insightful summary for the Wrapped feature."""
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
        summary, error, usage_data = await _call_gemini_api(payload, model, gemini_key, timeout)
        
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
        payload = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}

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
            response_text, error, usage_data = await _call_gemini_api(payload, model, gemini_key, timeout)
            
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
        
        response_text, error, usage_data = await _call_gemini_api(payload, vision_model, gemini_key, timeout)
        
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
            "max_tokens": 1024
        }
        
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
        
        response_text, error, usage_data = await _call_gemini_api(payload, model_name, gemini_key, timeout)
        
        # Log API usage
        input_tokens, output_tokens = usage_data
        if input_tokens > 0 or output_tokens > 0:
            from modules.db_helpers import log_api_usage
            await log_api_usage(model_name, input_tokens, output_tokens)
        
        return response_text, error
        
    elif model_name.startswith('gpt') or model_name.startswith('o'):
        # OpenAI models (including o1, o3 reasoning models)
        messages = []
        
        # o1 and o3 models don't support system prompts or temperature
        is_reasoning_model = model_name.startswith('o1') or model_name.startswith('o3')
        
        if system_prompt and not is_reasoning_model:
            messages.append({"role": "system", "content": system_prompt})
        elif system_prompt and is_reasoning_model:
            # For reasoning models, include system prompt as part of user message
            prompt = f"{system_prompt}\n\n{prompt}"
        
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": model_name,
            "messages": messages,
            "max_tokens": 2048
        }
        
        # Only add temperature for non-reasoning models
        if not is_reasoning_model:
            payload["temperature"] = temperature
        
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
    Generates a description and usage context for an emoji using vision AI.
    """
    prompt = f"""Analyze this emoji named "{emoji_name}".
    
Provide:
1. A brief description of what the emoji depicts (1-2 sentences)
2. When and how this emoji should be used in conversation (2-3 examples)
3. The emotional tone or context it conveys

Format your response as JSON:
{{
    "description": "...",
    "usage_context": "...",
    "emotional_tone": "..."
}}"""
    
    response, error = await get_vision_analysis(emoji_url, prompt, config, gemini_key, openai_key)
    
    if error:
        return None, error
    
    try:
        # Try to parse the JSON response
        import json
        data = json.loads(response)
        return data, None
    except json.JSONDecodeError:
        # If not valid JSON, return the raw response
        return {"description": response, "usage_context": "General use", "emotional_tone": "Neutral"}, None