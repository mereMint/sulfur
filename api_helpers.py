import aiohttp
import json
from collections import deque
from datetime import datetime, timezone

# --- Constants ---
GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1/models"
OPENAI_API_BASE_URL = "https://api.openai.com/v1/chat/completions"

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
    for msg in history:
        # Skip if the role is the same as the last one
        if msg.get('role') == last_role:
            continue
        clean_history.append(msg)
        last_role = msg.get('role')

    # Ensure the history starts with a 'user' role
    while clean_history and clean_history[0].get('role') != 'user':
        clean_history.popleft()

    history = list(clean_history)

    # Add the current user prompt to the history for the API call
    history.append({"role": "user", "parts": [{"text": f"User '{user_display_name}' said: {user_prompt}"}]})

    if provider == 'gemini':
        # --- FIX: Dynamically build the URL with the model from config ---
        model = config.get('api', {}).get('gemini', {}).get('model', 'gemini-1.5-flash-latest')
        api_url = f"{GEMINI_API_BASE_URL}/{model}:generateContent?key={gemini_key}"
        
        generation_config = config.get('api', {}).get('gemini', {}).get('generation_config', {})
        
        payload = {
            "contents": history,
            "generationConfig": generation_config,
            "systemInstruction": {
                "role": "system",
                "parts": [{"text": system_prompt}]
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, json=payload, timeout=timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        response_text = data['candidates'][0]['content']['parts'][0]['text']
                        # Add the bot's response to the history for future context
                        history.append({"role": "model", "parts": [{"text": response_text}]})
                        return response_text, None
                    else:
                        error_text = await response.text()
                        print(f"Gemini API Error (Status {response.status}): {error_text}")
                        return None, f"Ich habe einen Fehler vom Server erhalten (Status: {response.status}). Wahrscheinlich ist die API down oder dein Key ist ungültig."
        except Exception as e:
            print(f"An exception occurred while calling Gemini API: {e}")
            return None, "Ich konnte die AI nicht erreichen. Überprüfe die Internetverbindung oder die API-Keys."

    elif provider == 'openai':
        model = config.get('api', {}).get('openai', {}).get('chat_model', 'gpt-4o-mini')
        temperature = config.get('api', {}).get('openai', {}).get('chat_temperature', 0.7)
        max_tokens = config.get('api', {}).get('openai', {}).get('chat_max_tokens', 2048)

        headers = {"Authorization": f"Bearer {openai_key}"}
        
        # Convert Gemini history format to OpenAI format
        messages = [{"role": "system", "content": system_prompt}]
        for item in history:
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
                        # Add the bot's response to the history for future context
                        history.append({"role": "model", "parts": [{"text": response_text}]})
                        return response_text, None
                    else:
                        error_text = await response.text()
                        print(f"OpenAI API Error (Status {response.status}): {error_text}")
                        return None, f"Ich habe einen Fehler vom OpenAI-Server erhalten (Status: {response.status})."
        except Exception as e:
            print(f"An exception occurred while calling OpenAI API: {e}")
            return None, "Ich konnte die OpenAI-AI nicht erreichen. Überprüfe die Internetverbindung oder die API-Keys."

    return None, "Ungültiger API-Provider in der Konfiguration."


async def get_relationship_summary_from_api(history, user_display_name, old_summary, config, gemini_key, openai_key):
    """Generates a new relationship summary based on chat history."""
    provider = config.get('api', {}).get('provider', 'gemini')
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
        model = config.get('api', {}).get('gemini', {}).get('utility_model', config.get('api', {}).get('gemini', {}).get('model', 'gemini-1.5-flash-latest'))
        api_url = f"{GEMINI_API_BASE_URL}/{model}:generateContent?key={gemini_key}"
        generation_config = config.get('api', {}).get('gemini', {}).get('utility_generation_config', {})
        payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": generation_config}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, json=payload, timeout=timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data['candidates'][0]['content']['parts'][0]['text'].strip(), None
                    return None, f"API Error {response.status}"
        except Exception as e:
            return None, str(e)
    # (OpenAI fallback could be added here if needed)
    return None, "Utility function only supports Gemini for now."

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
        model = config.get('api', {}).get('gemini', {}).get('utility_model', config.get('api', {}).get('gemini', {}).get('model', 'gemini-1.5-flash-latest'))
        api_url = f"{GEMINI_API_BASE_URL}/{model}:generateContent?key={gemini_key}"
        generation_config = config.get('api', {}).get('gemini', {}).get('utility_generation_config', {})
        payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": generation_config}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, json=payload, timeout=timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data['candidates'][0]['content']['parts'][0]['text'].strip().replace("*", "")
                    return event_text # Fallback to the original text
        except Exception:
            return event_text # Fallback
    return event_text # Fallback

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
            model = config.get('api', {}).get('gemini', {}).get('utility_model', config.get('api', {}).get('gemini', {}).get('model', 'gemini-1.5-flash-latest'))
            api_url = f"{GEMINI_API_BASE_URL}/{model}:generateContent?key={gemini_key}"
            generation_config = config.get('api', {}).get('gemini', {}).get('utility_generation_config', {})
            payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": generation_config}
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(api_url, json=payload, timeout=timeout) as response:
                        if response.status == 200:
                            data = await response.json()
                            new_names_text = data['candidates'][0]['content']['parts'][0]['text']
                            new_names = [name.strip() for name in new_names_text.split(',')]
                            await db_helpers.add_bot_names_to_pool(new_names)
                            # Now fetch the names we just added
                            names.extend(await db_helpers.get_and_remove_bot_names(needed))
            except Exception as e:
                print(f"  [WW] Failed to fetch new names from API: {e}")

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
        model = config.get('api', {}).get('gemini', {}).get('utility_model', config.get('api', {}).get('gemini', {}).get('model', 'gemini-1.5-flash-latest'))
        api_url = f"{GEMINI_API_BASE_URL}/{model}:generateContent?key={gemini_key}"
        generation_config = config.get('api', {}).get('gemini', {}).get('utility_generation_config', {})
        payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": generation_config}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, json=payload, timeout=timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data['candidates'][0]['content']['parts'][0]['text'].strip(), None
                    return "You survived another month, I guess.", f"API Error {response.status}"
        except Exception as e:
            return "My brain is melting, can't think of a verdict.", str(e)
            
    return "You did... stuff. Congrats?", "OpenAI not configured for this."