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
    """
    api_url = f"{GEMINI_API_BASE_URL}/{model_name}:generateContent?key={api_key}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=payload, timeout=timeout) as response:
                if response.status == 200:
                    data = await response.json()
                    # Robust checking for valid API response content
                    if data.get('candidates') and data['candidates'][0].get('content') and data['candidates'][0]['content'].get('parts'):
                        return data['candidates'][0]['content']['parts'][0]['text'], None
                    else:
                        # This happens if the response was blocked for safety or other reasons.
                        error_reason = data.get('promptFeedback', {}).get('blockReason', 'UNKNOWN')
                        if not error_reason:
                             error_reason = data.get('candidates', [{}])[0].get('finishReason', 'UNKNOWN')
                        logger.warning(f"Gemini API: No content in response. Finish Reason: {error_reason}")
                        logger.debug(f"Full API response: {data}")
                        print(f"Gemini API Error: No content in response. Finish Reason: {error_reason}")
                        print(f"Full API response: {data}")
                        return None, f"Meine Antwort wurde blockiert (Grund: {error_reason}). Versuchs mal anders zu formulieren."
                else:
                    # --- NEW: Add specific diagnostic for 404 errors ---
                    if response.status == 404:
                        error_text = await response.text()
                        print(f"Gemini API Error (Status 404): {error_text}")
                        return None, f"Modell '{model_name}' nicht gefunden (404). **Überprüfe, ob die 'Generative Language API' in deinem Google Cloud Projekt aktiviert ist und dein API-Schlüssel die Berechtigung dafür hat.**"
                    error_text = await response.text()
                    print(f"Gemini API Error (Status {response.status}): {error_text}")
                    return None, f"Ich habe einen Fehler vom Server erhalten (Status: {response.status}). Wahrscheinlich ist die API down oder dein Key ist ungültig."
    except Exception as e:
        logger.error(f"Exception calling Gemini API: {e}", exc_info=True)
        print(f"An exception occurred while calling Gemini API: {e}")
        return None, "Ich konnte die AI nicht erreichen. Überprüfe die Internetverbindung oder die API-Keys."

async def get_chat_response(history, user_prompt, user_display_name, system_prompt, config, gemini_key, openai_key):
    """
    Gets a chat response from the configured AI provider (Gemini or OpenAI).
    This function now correctly builds the Gemini URL with the model from the config.
    """
    provider = config.get('api', {}).get('provider', 'gemini')
    timeout = config.get('api', {}).get('timeout', 30)

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

    # Add the current user prompt to the history for this specific API call
    final_history_for_api.append({"role": "user", "parts": [{"text": f"User '{user_display_name}' said: {user_prompt}"}]})

    if provider == 'gemini':
        # --- FIX: Dynamically build the URL with the model from config ---
        model = config.get('api', {}).get('gemini', {}).get('model', 'gemini-2.5-flash')
        generation_config = config.get('api', {}).get('gemini', {}).get('generation_config', {})
        
        # --- FIX: Prepend system prompt to contents instead of using system_instruction ---
        # This is more compatible with newer models like gemini-1.5-flash.
        final_contents = [{"role": "user", "parts": [{"text": system_prompt}]}, {"role": "model", "parts": [{"text": "Understood."}]}] + final_history_for_api
        
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
        
        response_text, error = await _call_gemini_api(payload, model, gemini_key, timeout)
        if response_text:
            # --- FIX: Return the updated history instead of modifying it in-place ---
            final_history_for_api.append({"role": "model", "parts": [{"text": response_text}]})
        # The `history` object passed from bot.py is no longer modified.
        return response_text, error, final_history_for_api

    elif provider == 'openai':
        model = config.get('api', {}).get('openai', {}).get('chat_model', 'gpt-4o-mini')
        temperature = config.get('api', {}).get('openai', {}).get('chat_temperature', 0.7)
        max_tokens = config.get('api', {}).get('openai', {}).get('chat_max_tokens', 2048)

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
    Based on the following chat history with '{user_display_name}', update my relationship summary with them.
    My previous summary was: "{old_summary if old_summary else 'None'}"
    The chat history is:
    ---
    {json.dumps(history, indent=2)}
    ---
    Based on this new conversation, write a new, concise, one-sentence summary of my relationship with {user_display_name} from my perspective.
    The summary should be in the first person (e.g., "I think he's funny," "I find her annoying," "We seem to get along well.").
    Do not add any extra text, just the single sentence summary.
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
        summary, error = await _call_gemini_api(payload, model, gemini_key, timeout)
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
                        return data['choices'][0]['message']['content'].strip(), None
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
    You are the narrator for a game of Werewolf.
    The following event just happened: "{event_text}"
    Your task is to create a very short, dramatic, single-sentence announcement for this event that can be read by a Text-to-Speech (TTS) engine.
    Keep it under 150 characters. Do not use markdown.
    Example: If the event is "The villagers have decided to lynch Steve", you could say "The mob has chosen its victim. Steve is to be lynched."
    
    Generate the TTS sentence for the event: "{event_text}"
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
        tts_text, _ = await _call_gemini_api(payload, model, gemini_key, timeout)
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
                        return data['choices'][0]['message']['content'].strip().replace("*", "")
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
            new_names_text, error = await _call_gemini_api(payload, model, gemini_key, timeout)
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
    """Generates a personalized, slightly insulting summary for the Wrapped feature."""
    provider = config.get('api', {}).get('provider', 'gemini')
    timeout = config.get('api', {}).get('timeout', 30)
    
    prompt = f"""
    You are Sulfur, a bot with a slightly arrogant and judgmental personality.
    A user named '{user_display_name}' just received their monthly stats summary ("Wrapped").
    Here are their stats: {json.dumps(stats)}
    Based on these stats, write a short, funny, one-sentence "verdict" or judgment about them. Be a little bit of a troll.
    Examples: "Wow, {stats.get('vc_hours', 0)} hours in VC? Do you ever see the sun?", "Your top song was {stats.get('top_song', 'something weird')}, I'm judging you so hard right now."
    Your verdict should be a single, concise sentence.
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
        summary, error = await _call_gemini_api(payload, model, gemini_key, timeout)
        return summary.strip() if summary else "You survived another month, I guess.", error

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
                        return data['choices'][0]['message']['content'].strip(), None
                    else:
                        print(f"OpenAI API Error (get_wrapped_summary): {await response.text()}")
                        return "You did... stuff. Congrats?", f"API Error {response.status}"
        except Exception as e:
            return "My brain is melting, can't think of a verdict.", str(e)

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
            response_text, error = await _call_gemini_api(payload, model, gemini_key, timeout)
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
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": image_url  # This should be base64 encoded image data
                        }
                    } if image_url.startswith('data:') else {"image_url": {"url": image_url}}
                ]
            }],
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 1024,
            }
        }
        
        response_text, error = await _call_gemini_api(payload, vision_model, gemini_key, timeout)
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
                        return data['choices'][0]['message']['content'], None
                    else:
                        error_text = await response.text()
                        print(f"OpenAI Vision API Error: {error_text}")
                        return None, f"Vision API Error: {response.status}"
        except Exception as e:
            print(f"Exception calling OpenAI Vision API: {e}")
            return None, str(e)
    
    return None, "Unsupported provider for vision"


# --- Multi-Model Support ---

async def get_ai_response_with_model(prompt, model_name, config, gemini_key, openai_key, system_prompt=None):
    """
    Gets a response from a specific AI model.
    Supports: gemini-2.0-flash-exp, gemini-1.5-pro, gpt-4o, gpt-4-turbo, claude-3-opus, etc.
    """
    timeout = config.get('api', {}).get('timeout', 30)
    
    # Determine provider from model name
    if model_name.startswith('gemini'):
        # Gemini models
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 2048,
            }
        }
        
        if system_prompt:
            payload["contents"].insert(0, {
                "parts": [{"text": system_prompt}]
            })
        
        response_text, error = await _call_gemini_api(payload, model_name, gemini_key, timeout)
        return response_text, error
        
    elif model_name.startswith('gpt'):
        # OpenAI models
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2048
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
                async with session.post(OPENAI_API_BASE_URL, json=payload, headers=headers, timeout=timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data['choices'][0]['message']['content'], None
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