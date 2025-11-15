import asyncio
import aiohttp
import json
from abc import ABC, abstractmethod

# This file is created to resolve a circular import between bot.py and werwolf.py.
# It centralizes all functions that make calls to the Google Gemini API.

# --- NEW: Generic API error messages ---
API_ERROR_FALLBACK = "Ayo, mein Gehirn hat gerade einen Bluescreen. Die API antwortet nicht. :KMS:"
API_ERROR_INVALID_RESPONSE = "My brain just farted. Got no response. Try again?"
API_ERROR_SAFETY_BLOCK = "Nah, can't talk about that, fam. (Blocked by safety filters)"

# --- NEW: Abstract Base Class for API Providers ---
class AIProvider(ABC):
    def __init__(self, api_key, config):
        self.api_key = api_key
        self.config = config

    @abstractmethod
    async def get_chat_response(self, history, user_prompt, author_name, system_prompt):
        pass

    @abstractmethod
    async def get_werwolf_tts_message(self, prompt):
        pass

    @abstractmethod
    async def get_random_names(self, count):
        pass

    @abstractmethod
    async def get_relationship_summary(self, history, user_name, old_summary):
        pass

    @abstractmethod
    async def get_wrapped_summary(self, user_name, stats):
        pass

# --- NEW: Factory function to get the right provider ---
def get_api_provider(config, gemini_key, openai_key):
    """Returns an instance of the configured AI provider."""
    provider_name = config.get('api', {}).get('provider', 'gemini').lower()
    if provider_name == 'openai':
        return OpenAIProvider(openai_key, config)
    # Default to Gemini
    return GeminiProvider(gemini_key, config)

# --- Wrapper functions that will be called from bot.py ---

async def get_chat_response(history, user_prompt, author_name, system_prompt, config, gemini_key, openai_key):
    provider = get_api_provider(config, gemini_key, openai_key)
    return await provider.get_chat_response(history, user_prompt, author_name, system_prompt)

async def get_werwolf_tts_message(prompt, config, gemini_key, openai_key):
    provider = get_api_provider(config, gemini_key, openai_key)
    return await provider.get_werwolf_tts_message(prompt)

async def get_random_names(count, db_helpers, config, gemini_key, openai_key):
    """Gets a list of random German names for bot players, with DB caching."""
    # --- REFACTORED: Use database as the primary source for names ---
    min_pool_size = config['modules']['werwolf']['min_name_pool_size']
    current_pool_size = await db_helpers.get_bot_name_pool_count()

    if current_pool_size < min_pool_size:
        print(f"Werwolf name pool is low ({current_pool_size}). Refilling from API...")
        provider = get_api_provider(config, gemini_key, openai_key)
        new_names_from_api = await provider.get_random_names(50)
        if new_names_from_api:
            await db_helpers.add_bot_names_to_pool(new_names_from_api)

    names_from_db = await db_helpers.get_and_remove_bot_names(count)
    if len(names_from_db) == count:
        print(f"  -> Fetched {count} bot names from the database pool.")
        return names_from_db

    print("  -> Warning: DB name pool was empty or failed. Falling back to direct API call for names.")
    provider = get_api_provider(config, gemini_key, openai_key)
    return await provider.get_random_names(count)

async def get_relationship_summary_from_api(history, user_name, old_summary, config, gemini_key, openai_key):
    provider = get_api_provider(config, gemini_key, openai_key)
    return await provider.get_relationship_summary(history, user_name, old_summary)

async def get_wrapped_summary_from_api(user_name, stats, config, gemini_key, openai_key):
    provider = get_api_provider(config, gemini_key, openai_key)
    return await provider.get_wrapped_summary(user_name, stats)


# --- NEW: Gemini Provider Implementation ---
class GeminiProvider(AIProvider):
    def _get_api_url(self):
        model = self.config['api']['gemini']['model']
        return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"

    async def get_chat_response(self, history, user_prompt, author_name, system_prompt):
        print(f"  -> Calling Gemini for chat response to '{author_name}'...")
        contextual_prompt = f"User '{author_name}' said: {user_prompt}"
        history.append({"role": "user", "parts": [{"text": contextual_prompt}]})

        payload = {
            "contents": list(history),
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "generationConfig": self.config['api']['gemini']['generation_config'],
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
        }

        headers = {"Content-Type": "application/json"}

        async with aiohttp.ClientSession() as session:
            try:
                api_url = self._get_api_url()
                async with session.post(api_url, json=payload, headers=headers) as resp:
                    if resp.status != 200:
                        print(f"API Error: {resp.status}")
                        text_data = await resp.text()
                        print(f"Response: {text_data}")
                        return None, f"Ayo, the API is buggin'. Status: {resp.status}"

                    data = await resp.json()

                    if "promptFeedback" in data and data["promptFeedback"]["blockReason"]:
                        block_reason = data["promptFeedback"]["blockReason"]
                        print(f"Blocked by safety: {block_reason}")
                        return None, API_ERROR_SAFETY_BLOCK

                    if not data.get("candidates"):
                        print(f"Invalid API response: {data}")
                        return None, API_ERROR_INVALID_RESPONSE

                    gemini_response_text = data["candidates"][0]["content"]["parts"][0]["text"]
                    history.append({"role": "model", "parts": [{"text": gemini_response_text}]})
                    return gemini_response_text, None

            except asyncio.TimeoutError:
                print("Error in get_gemini_response: API call timed out.")
                return None, API_ERROR_FALLBACK
            except Exception as e:
                print(f"Error in get_gemini_response: {e}")
                return None, "Ayo, my brain's buggin' right now. Something went wrong."
            finally:
                history.pop() # Always remove the prompt we added

    async def get_werwolf_tts_message(self, prompt):
        if not self.api_key:
            return prompt # Return the original prompt if no API URL is set
        
        char_limit = self.config['modules']['werwolf']['tts'].get('tts_char_limit', 150)
        full_prompt = f"Du bist der Spielleiter für ein Werwolf-Spiel. Gib eine kurze, atmosphärische, unheimliche Ansage für die folgende Situation. Die Antwort sollte nur der Satz sein, der per Text-to-Speech vorgelesen wird, ohne Anführungszeichen oder zusätzliche Erklärungen, und darf maximal {char_limit} Zeichen lang sein. Situation: {prompt}"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": full_prompt}]}],
            "generationConfig": self.config['api']['gemini']['utility_generation_config'],
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
            ]
        }
        headers = {"Content-Type": "application/json"}
        async with aiohttp.ClientSession() as session:
            try:
                api_url = self._get_api_url()
                async with session.post(api_url, json=payload, headers=headers) as resp:
                    if resp.status != 200:
                        print(f"Werwolf TTS API Error: {resp.status}")
                        text_data = await resp.text()
                        print(f"Response: {text_data}")
                        return prompt # Fallback to original prompt
                    data = await resp.json()

                    if "promptFeedback" in data and data["promptFeedback"]["blockReason"]:
                        block_reason = data["promptFeedback"]["blockReason"]
                        print(f"Werwolf TTS blocked by safety: {block_reason}")
                        return prompt

                    if not data.get("candidates"):
                        print(f"Invalid Werwolf TTS API response (no candidates): {data}")
                        return prompt

                    candidate = data["candidates"][0]
                    if not candidate.get("content") or not candidate["content"].get("parts"):
                        print(f"Invalid Werwolf TTS API response (no content/parts): {data}")
                        return prompt

                    # The final cleaning is now done in werwolf.py before sending.
                    return candidate["content"]["parts"][0]["text"].strip()
            except asyncio.TimeoutError:
                print("Error in get_werwolf_tts_message: API call timed out.")
                return prompt # Fallback to original prompt
            except Exception as e:
                print(f"Error in get_werwolf_tts_message: {e}")
                return prompt # Fallback to original prompt

    async def get_random_names(self, count):
        if not self.api_key or count <= 0:
            return [f"Bot_{i+1}" for i in range(count)]

        prompt = f'Gib mir eine Liste von {count} zufälligen, altmodischen deutschen Vornamen. Antworte NUR mit einem JSON-Objekt, das ein einzelnes Feld "names" enthält, welches ein Array von Strings ist. Beispiel: {{"names": ["Hans", "Gretel", "Klaus"]}}'
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 1.0, "maxOutputTokens": 1024},
        }
        headers = {"Content-Type": "application/json"}

        timeout = aiohttp.ClientTimeout(total=self.config['api']['timeout'])
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                api_url = self._get_api_url()
                async with session.post(api_url, json=payload, headers=headers) as resp:
                    if resp.status != 200:
                        print(f"Bot name API Error: {resp.status}")
                        print(f"Response: {await resp.text()}")
                        return [f"Bot_{i+1}" for i in range(count)]

                    data = await resp.json()

                    if not data.get("candidates"):
                        print(f"Invalid bot name API response (no candidates): {data}")
                        return [f"Bot_{i+1}" for i in range(count)]

                    candidate = data["candidates"][0]
                    if not candidate.get("content") or not candidate["content"].get("parts"):
                        print(f"Invalid bot name API response (no content/parts): {data}")
                        return [f"Bot_{i+1}" for i in range(count)]

                    text_content = candidate["content"]["parts"][0]["text"]
                    clean_data = text_content.strip().replace("```json", "").replace("```", "")
                    
                    try:
                        names_data = json.loads(clean_data)
                        # Check if we got a list of names and it's not empty
                        if isinstance(names_data, dict) and "names" in names_data and isinstance(names_data["names"], list) and names_data["names"]:
                            return names_data["names"][:count]
                        else:
                            print(f"Bot name JSON is malformed or the 'names' list is empty: {clean_data}")
                    except json.JSONDecodeError:
                        print(f"Failed to decode JSON from bot name response. Cleaned data: {clean_data}")

            except asyncio.TimeoutError:
                print("Error in get_random_names: API call timed out.")
            except Exception as e:
                print(f"Error in get_random_names: {e}")
        
        return [f"Bot_{i+1}" for i in range(count)]

    async def get_relationship_summary(self, history, user_name, old_summary):
        if not self.api_key:
            return None, "API URL not set."

        history_text = "\n".join([f"{msg['role']}: {msg['parts'][0]['text']}" for msg in history])

        prompt = f"""
        Du bist Sulfur, eine KI mit einer bestimmten Persönlichkeit. Basierend auf dem folgenden Chatverlauf und deiner bisherigen Meinung, fasse deine aktuelle Beziehung oder Meinung zu dem Benutzer '{user_name}' in 1-2 Sätzen zusammen. Sprich in der Ich-Form aus deiner Sicht.

        Deine bisherige Meinung war: "{old_summary or 'Noch keine Meinung.'}"

        Jüngster Chatverlauf:
        ---
        {history_text}
        ---

        Deine neue, zusammengefasste Meinung über '{user_name}':
        """

        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": self.config['api']['gemini']['utility_generation_config'],
        }
        headers = {"Content-Type": "application/json"}

        timeout = aiohttp.ClientTimeout(total=self.config['api']['timeout'])
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                api_url = self._get_api_url()
                async with session.post(api_url, json=payload, headers=headers) as resp:
                    if resp.status != 200:
                        return None, f"API Error: {resp.status}"
                    data = await resp.json()
                    if not data.get("candidates"):
                        return None, "Invalid API response."
                    
                    summary = data["candidates"][0]["content"]["parts"][0]["text"]
                    return summary.strip(), None
            except asyncio.TimeoutError:
                print("Error in get_relationship_summary_from_gemini: API call timed out.")
                return None, "Exception during API call (timeout)."
            except Exception as e:
                print(f"Error in get_relationship_summary_from_gemini: {e}")
                return None, "Exception during API call."

    async def get_wrapped_summary(self, user_name, stats):
        if not self.api_key:
            return "Puh, deine Stats waren so... existent, dass meiner KI das Hirn geschmolzen ist. Konnte nichts Witziges dazu finden.", None

        # --- REFACTORED: Conditionally build the stats text to avoid showing "N/A" ---
        stats_lines = [
            f"- Nachrichten gesendet: {stats.get('message_count', 0)} (Durchschnitt: {stats.get('avg_message_count', 0):.0f})",
            f"- Stunden im Voice Chat: {stats.get('vc_hours', 0.0):.1f} (Durchschnitt: {stats.get('avg_vc_hours', 0.0):.1f})",
            f"- Nachrichten-Rang: {stats.get('message_rank_text', 'N/A')}",
            f"- Voice-Chat-Rang: {stats.get('vc_rank_text', 'N/A')}"
        ]
        if 'fav_activity' in stats:
            stats_lines.append(f"- Deine Top-Aktivität (neben Discord): {stats['fav_activity']}")
        if 'top_game' in stats:
            stats_lines.append(f"- Dein Top-Game: {stats['top_game']}")
        if 'top_song' in stats:
            stats_lines.append(f"- Dein Top-Song (nach Hörzeit): {stats['top_song']}")
        
        stats_text = "\n".join(stats_lines)

        prompt = f"""
        Du bist Sulfur (kurz Sulf), eine KI mit einer frechen Gen-Z-Persönlichkeit, die gerne Leute aufzieht. Du erstellst eine personalisierte, witzige und sarkastische "Wrapped"-Zusammenfassung (2-3 Sätze) für den Benutzer '{user_name}'.
        Sprich in der Ich-Form aus deiner Sicht und direkt an den Benutzer. Benutze deutschen Gen-Z-Slang, aber übertreib es nicht.

        Hier sind die Statistiken des Benutzers für den letzten Monat:
        {stats_text}

        Deine Aufgabe ist es, eine unterhaltsame, leicht fiese Zusammenfassung zu schreiben.
        - Vergleiche die Stats des Nutzers mit dem Durchschnitt. Wenn sie weit darüber liegen, mach dich lustig, dass er keine Hobbys hat. Wenn sie weit darunter liegen, erwähne, dass er anscheinend ein Leben hat.
        - Beziehe dich auf den Top-Song oder das Top-Game, wenn es interessant ist.
        - Sei kreativ und nicht repetitiv.
        Beispiel (Top 10%): "Yo {user_name}, Top 10% bei den Nachrichten? Touch grass, dude. Du bist ja mehr online als ich."
        Beispiel (Bottom 50%): "Hey {user_name}, deine Stats sind so low, ich dachte du wärst ein Geist. Aber hey, immerhin hast du anscheinend ein Leben außerhalb von Discord, im Gegensatz zu manch anderen hier."
        """

        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": self.config['api']['gemini']['utility_generation_config'],
        }
        headers = {"Content-Type": "application/json"}

        timeout = aiohttp.ClientTimeout(total=self.config['api']['timeout'])
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                api_url = self._get_api_url()
                async with session.post(api_url, json=payload, headers=headers) as resp:
                    if resp.status != 200:
                        return "Meine KI hat gerade einen Bluescreen, weil die API nicht antwortet. Frag später nochmal.", f"API Error: {resp.status}"
                    data = await resp.json()
                    if not data.get("candidates"):
                        return "Meine KI hat gerade einen Bluescreen, weil die API nicht antwortet. Frag später nochmal.", "Invalid API response."
                    
                    summary = data["candidates"][0]["content"]["parts"][0]["text"]
                    return summary.strip(), None
            except asyncio.TimeoutError:
                print("Error in get_wrapped_summary_from_gemini: API call timed out.")
                return "Meine KI hat gerade einen Bluescreen, weil die API nicht antwortet. Frag später nochmal.", "Exception during API call (timeout)."
            except Exception as e:
                print(f"Error in get_wrapped_summary_from_gemini: {e}")
                return "Meine KI hat gerade einen Bluescreen, weil die API nicht antwortet. Frag später nochmal.", "Exception during API call."

# --- NEW: OpenAI Provider Implementation ---
class OpenAIProvider(AIProvider):
    def _get_headers(self):
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _convert_history_to_openai(self, history, system_prompt):
        """Converts Gemini history format to OpenAI format."""
        messages = [{"role": "system", "content": system_prompt}]
        for item in history:
            # Gemini: {"role": "user", "parts": [{"text": "Hello"}]}
            # OpenAI: {"role": "user", "content": "Hello"}
            role = item['role']
            if role == 'model':
                role = 'assistant'
            messages.append({"role": role, "content": item['parts'][0]['text']})
        return messages

    async def get_chat_response(self, history, user_prompt, author_name, system_prompt):
        print(f"  -> Calling OpenAI for chat response to '{author_name}'...")
        contextual_prompt = f"User '{author_name}' said: {user_prompt}"
        
        # Convert history and add the new prompt
        messages = self._convert_history_to_openai(history, system_prompt)
        messages.append({"role": "user", "content": contextual_prompt})

        payload = {
            "model": self.config['api']['openai']['chat_model'],
            "messages": messages,
            "temperature": self.config['api']['openai']['chat_temperature'],
            "max_tokens": self.config['api']['openai']['chat_max_tokens'],
        }
        
        api_url = "https://api.openai.com/v1/chat/completions"
        timeout = aiohttp.ClientTimeout(total=self.config['api']['timeout'])
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.post(api_url, json=payload, headers=self._get_headers()) as resp:
                    if resp.status != 200:
                        print(f"API Error: {resp.status}")
                        print(f"Response: {await resp.text()}")
                        return None, f"Ayo, the API is buggin'. Status: {resp.status}"

                    data = await resp.json()
                    
                    if not data.get("choices"):
                        return None, API_ERROR_INVALID_RESPONSE

                    choice = data["choices"][0]
                    if choice.get("finish_reason") == "content_filter":
                        return None, API_ERROR_SAFETY_BLOCK

                    response_text = choice["message"]["content"]
                    
                    # Update history in-place for the bot logic
                    history.append({"role": "user", "parts": [{"text": contextual_prompt}]})
                    history.append({"role": "model", "parts": [{"text": response_text}]})

                    return response_text, None
            except asyncio.TimeoutError:
                return None, API_ERROR_FALLBACK
            except Exception as e:
                print(f"Error in get_chat_response (OpenAI): {e}")
                return None, "Ayo, my brain's buggin' right now."

    async def get_werwolf_tts_message(self, prompt):
        # OpenAI TTS is a separate endpoint and model. We'll just use the chat model for this.
        print("  -> Calling OpenAI for Werwolf TTS message...")
        char_limit = self.config['modules']['werwolf']['tts'].get('tts_char_limit', 150)
        full_prompt = f"Du bist der Spielleiter für ein Werwolf-Spiel. Gib eine kurze, atmosphärische, unheimliche Ansage für die folgende Situation. Die Antwort sollte nur der Satz sein, der per Text-to-Speech vorgelesen wird, ohne Anführungszeichen oder zusätzliche Erklärungen, und darf maximal {char_limit} Zeichen lang sein. Situation: {prompt}"
        payload = {
            "model": self.config['api']['openai']['utility_model'],
            "messages": [{"role": "user", "content": full_prompt}],
            "temperature": self.config['api']['openai']['utility_temperature'],
            "max_tokens": self.config['api']['openai']['utility_max_tokens'],
        }
        api_url = "https://api.openai.com/v1/chat/completions"
        timeout = aiohttp.ClientTimeout(total=self.config['api']['timeout'])
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.post(api_url, json=payload, headers=self._get_headers()) as resp:
                    if resp.status != 200:
                        return prompt # Fallback
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"].strip()
            except Exception:
                return prompt # Fallback

    async def get_random_names(self, count):
        print(f"  -> Calling OpenAI for {count} random bot names...")
        prompt = f'Gib mir eine Liste von {count} zufälligen, altmodischen deutschen Vornamen. Antworte NUR mit einem JSON-Objekt, das ein einzelnes Feld "names" enthält, welches ein Array von Strings ist. Beispiel: {{"names": ["Hans", "Gretel", "Klaus"]}}'
        payload = {
            "model": self.config['api']['openai']['utility_model'],
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": 1.0,
        }
        api_url = "https://api.openai.com/v1/chat/completions"
        timeout = aiohttp.ClientTimeout(total=self.config['api']['timeout'])
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.post(api_url, json=payload, headers=self._get_headers()) as resp:
                    if resp.status != 200:
                        return [f"Bot_{i+1}" for i in range(count)]
                    data = await resp.json()
                    names_json = json.loads(data["choices"][0]["message"]["content"])
                    return names_json.get("names", [f"Bot_{i+1}" for i in range(count)])
            except Exception as e:
                print(f"Error in get_random_names (OpenAI): {e}")
                return [f"Bot_{i+1}" for i in range(count)]

    async def get_relationship_summary(self, history, user_name, old_summary):
        # This function is very similar for both providers, just different models/endpoints
        history_text = "\n".join([f"{msg['role']}: {msg['parts'][0]['text']}" for msg in history])
        prompt = f"Du bist Sulfur, eine KI mit einer bestimmten Persönlichkeit. Basierend auf dem folgenden Chatverlauf und deiner bisherigen Meinung, fasse deine aktuelle Beziehung oder Meinung zu dem Benutzer '{user_name}' in 1-2 Sätzen zusammen. Sprich in der Ich-Form aus deiner Sicht.\n\nDeine bisherige Meinung war: \"{old_summary or 'Noch keine Meinung.'}\"\n\nJüngster Chatverlauf:\n---\n{history_text}\n---\n\nDeine neue, zusammengefasste Meinung über '{user_name}':"
        payload = {"model": self.config['api']['openai']['utility_model'], "messages": [{"role": "user", "content": prompt}], "temperature": self.config['api']['openai']['utility_temperature'], "max_tokens": self.config['api']['openai']['utility_max_tokens']}
        api_url = "https://api.openai.com/v1/chat/completions"
        timeout = aiohttp.ClientTimeout(total=self.config['api']['timeout'])
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.post(api_url, json=payload, headers=self._get_headers()) as resp:
                    if resp.status != 200: return None, "API Error"
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"].strip(), None
            except Exception as e:
                return None, f"Exception: {e}"

    async def get_wrapped_summary(self, user_name, stats):
        # This is also very similar
        # --- REFACTORED: Conditionally build the stats text for OpenAI as well ---
        stats_lines = [
            f"Nachrichten: {stats.get('message_count', 0)} (Avg: {stats.get('avg_message_count', 0):.0f})",
            f"VC Stunden: {stats.get('vc_hours', 0.0):.1f} (Avg: {stats.get('avg_vc_hours', 0.0):.1f})",
            f"Nachrichten-Rang: {stats.get('message_rank_text', 'N/A')}",
            f"VC-Rang: {stats.get('vc_rank_text', 'N/A')}"
        ]
        if 'fav_activity' in stats: stats_lines.append(f"Top-Aktivität: {stats['fav_activity']}")
        if 'top_game' in stats: stats_lines.append(f"Top-Game: {stats['top_game']}")
        if 'top_song' in stats: stats_lines.append(f"Top-Song: {stats['top_song']}")
        
        stats_text = ", ".join(stats_lines)

        prompt = f"""
        Du bist Sulfur, eine freche Gen-Z KI. Schreibe eine kurze, witzige, leicht sarkastische 'Wrapped'-Zusammenfassung (2-3 Sätze) für den Benutzer '{user_name}' basierend auf diesen Stats: {stats_text}.
        Vergleiche die Stats mit dem Durchschnitt. Wenn der Rang hoch ist (z.B. Top 10%), mach dich lustig, dass er keine Hobbys hat. Wenn der Rang niedrig ist (z.B. Bottom 50%), erwähne, dass er anscheinend ein Leben hat. Beziehe dich auf den Top-Song oder das Top-Game, falls vorhanden.
        """
        payload = {"model": self.config['api']['openai']['utility_model'], "messages": [{"role": "user", "content": prompt}], "temperature": self.config['api']['openai']['utility_temperature'], "max_tokens": self.config['api']['openai']['utility_max_tokens']}
        api_url = "https://api.openai.com/v1/chat/completions"
        timeout = aiohttp.ClientTimeout(total=self.config['api']['timeout'])
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.post(api_url, json=payload, headers=self._get_headers()) as resp:
                    if resp.status != 200: return "Meine KI hat gerade einen Bluescreen.", "API Error"
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"].strip(), None
            except Exception as e:
                return "Meine KI hat gerade einen Bluescreen.", f"Exception: {e}"