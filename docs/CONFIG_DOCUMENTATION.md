# Sulfur Bot Configuration Documentation

> **Note:** Many API settings, such as the active provider and model, can now be changed in real-time using the `/admin ai_dashboard` command in Discord. Changes made there will be saved back to your `config.json` file automatically.

---

This file explains all the available settings in `config.json`. You can modify these values to customize the bot's behavior.

---

## `bot`

This section contains general settings for the bot's identity and core behavior.

- **`names`**: A list of names that will trigger the chatbot in a server channel (e.g., "Hey sulf, what's up?").
- **`authorised_role`**: The name of the role that grants users permission to use admin commands (e.g., `/admin reload_config`).
- **`embed_color`**: The default hexadecimal color code for the embeds the bot sends (e.g., for `/rank` and `/leaderboard`).
- **`system_prompt_file`**: The path to the text file that contains the bot's main personality and instructions for the AI.
- **`description`**: A general description for the bot. (Note: This setting is not currently used in the code but can be kept for future features).

### `bot.presence`

Controls the bot's "Watching..." status in Discord.

- **`update_interval_minutes`**: How often (in minutes) the bot changes its status to watch a new random user.
- **`activity_templates`**: A list of phrases to use for the status. Use `{user}` as a placeholder for the random user's name.
- **`fallback_activity`**: The status text to display if no other users are found on the server.

### `bot.chat`

Settings related to the chatbot's conversational behavior.

- **`max_history_messages`**: The maximum number of past messages from a channel to send to the AI for context. A higher number gives more context but costs more.
- **`empty_ping_response`**: The message the bot sends if it is mentioned (@Sulfur) with no other text.
- **`relationship_update_interval`**: How many back-and-forth exchanges with a user before the AI updates its internal "relationship summary" about that user. For example, a value of `5` means an update happens after 10 total messages (5 from the user, 5 from the bot).

---

## `api`

Configuration for the AI model providers (Gemini and OpenAI).

- **`provider`**: The preferred API to use. Set to `"gemini"` to use Gemini first and fall back to OpenAI, or `"openai"` to only use OpenAI.
- **`timeout`**: The maximum time (in seconds) to wait for a response from the AI before giving up.

### `api.gemini`

- **`model`**: The specific Gemini model to use for all tasks (e.g., `gemini-2.5-flash`).
- **`generation_config`**: Settings for standard chat conversations.
  - `temperature`: Controls creativity. Higher is more random (e.g., 0.9), lower is more predictable (e.g., 0.2).
  - `top_k`: A sampling method. Best to leave as is unless you know what you're doing.
  - `max_output_tokens`: The maximum length of a response from the AI.
- **`utility_generation_config`**: AI settings for background tasks like generating summaries or bot names.

### `api.openai`

- **`chat_model`**: The OpenAI model to use for chat when Gemini is unavailable (e.g., `gpt-4o-mini`).
- **`utility_model`**: The OpenAI model for background tasks.
- **`chat_temperature` / `chat_max_tokens`**: Temperature and max length for OpenAI chat responses.
- **`utility_temperature` / `utility_max_tokens`**: Temperature and max length for OpenAI utility tasks.

---

## `modules`

Settings for the bot's various features and modules.

### `modules.leveling`

- **`xp_per_message`**: Amount of XP granted for sending a message in a server.
- **`xp_per_minute_in_vc`**: Amount of XP granted for each minute spent in a voice channel (not muted or deafened).
- **`xp_cooldown_seconds`**: How many seconds a user must wait after sending a message before they can earn XP from another message.
- **`vc_level_up_notification_interval`**: How often to notify a user about leveling up from voice channel activity. A value of `5` means they get a DM on levels 5, 10, 15, etc.

### `modules.economy`

- **`starting_balance`**: The amount of currency a new user starts with.
- **`level_up_bonus_multiplier`**: Determines the currency reward on level-up. The reward is `new_level * multiplier`.

### `modules.voice_manager`

Settings for the "Join to Create" voice channel feature.

- **`join_to_create_channel_name`**: The name of the voice channel that users join to create their own temporary channel.
- **`dynamic_channel_category_name`**: The name of the category where new temporary voice channels will be created.
- **`creation_move_delay_ms`**: A small delay (in milliseconds) to wait before moving the user to their new channel. Helps prevent Discord API race conditions.
- **`empty_channel_delete_grace_period_seconds`**: How long an empty temporary channel will exist before being automatically deleted.

### `modules.werwolf`

Configuration for the Werewolf game.

- **`game_category_name`**: The name of the category created to hold the game's text and voice channels.
- **`min_name_pool_size`**: The minimum number of bot names that should be in the database. If the count falls below this, the bot will ask the AI for more.
- **`day_vote_timeout_seconds`**: How long (in seconds) players have to vote during the day phase before votes are tallied automatically.
- **`join_phase_duration_seconds`**: How long the initial joining phase lasts before the game starts automatically.
- **`discussion_channel_name`**: The name the "Lobby" voice channel is renamed to once the game starts.
- **`wolf_thread_name`**: The name of the private thread created for the werewolves to conspire in.
- **`default_target_players`**: If the `/ww start` command is used without specifying a player count, the game will be filled with bots to reach this number.

#### `modules.werwolf.tts`

Controls the Text-To-Speech narrator for the Werewolf game.

- **`chars_per_second`**: Used to estimate how long a TTS message will take to read. Adjust if the narrator speaks faster or slower.
- **`min_duration`**: The minimum duration (in seconds) to wait for any TTS message, even very short ones.
- **`buffer_seconds`**: Extra time added to the calculated TTS duration to ensure it finishes before the game continues.
- **`tts_char_limit`**: The maximum number of characters a game event can have to be eligible for TTS narration.

#### `modules.werwolf.pacing`

Controls the dramatic pauses (in seconds) during the Werewolf game's announcements.

- **`after_morning_announcement`**: Pause after "The morning dawns...".
- **`after_victim_reveal`**: Pause after a victim is announced.
- **`after_no_victim_announcement`**: Pause after announcing that nobody died.
- **`after_lynch_reveal`**: Pause after a player is lynched.

### `modules.wrapped`

Settings for the monthly "Sulfur Wrapped" user statistics summary.

- **`release_day_min` / `release_day_max`**: The range of days in the month when the Wrapped event can be scheduled. A random day between these two values (e.g., 8 and 14) will be chosen.
- **`intro_gif_url`**: A URL to a GIF to be used on the intro page of the Wrapped summary.
- **`percentile_ranks`**: The titles given to users based on their percentile ranking.
  - `"1"`: Title for users in the top 1%.
  - `"10"`: Title for users in the top 10%.
  - `"25"`: Title for users in the top 25%.
  - `"50"`: Title for users in the top 50%.
  - `"default"`: Title for everyone else.