# Sulfur Bot  सल्फर

A multi-purpose Discord bot with a Gen-Z personality, a full-fledged Werewolf game, dynamic voice channels, and much more.

## Overview

Sulfur is a multifunctional Discord bot designed to enhance server interaction through a combination of entertainment and useful tools. It features an AI-driven chat personality, a fully automated Werewolf game, a global leveling and economy system, and dynamic voice channels.

## ✨ Key Features

-   **AI Chatbot**: A sassy Gen-Z personality named "Sulf" who responds to mentions and "remembers" relationships with users through chat history. Supports both Google Gemini and OpenAI.
-   **Werewolf Game**: A fully automated Werewolf game with various roles, bot opponents, and atmospheric TTS announcements.
-   **Leveling & Economy System**: Users earn XP and currency through chat and voice activity.
-   **Dynamic Voice Channels**: A "Join to Create" system that allows users to create and manage temporary, private voice channels.
-   **"Wrapped" Monthly Stats**: A Spotify-style monthly summary of each user's server activity, delivered via a personalized DM.
-   **Data Persistence**: All user data (levels, stats, chat history, etc.) is stored in a MySQL/MariaDB database.

## 🚀 Getting Started

To get the bot running on your own server, you'll need Python, a MySQL database (like MariaDB via XAMPP or Termux), and API keys for Discord and your chosen AI provider.

For detailed, step-by-step instructions for both Windows and Android (Termux), please see the full **[DOCUMENTATION.md](DOCUMENTATION.md)**.

## 🤖 Commands

Here are a few of the main commands. For a complete list, check the [documentation](DOCUMENTATION.md#verwendung-befehle).

-   **Chat**: Mention the bot (`@Sulfur`) or use its name (`sulf`) to start a conversation.
-   `/rank [user]`: Check a user's server level and rank.
-   `/leaderboard`: Display the top 10 most active users.
-   `/ww start`: Start a new game of Werewolf.
-   `/voice setup`: (Admin) Set up the "Join to Create" voice channel feature.

## 🛠️ Tech Stack

-   **Language**: Python 3.10+
-   **Library**: discord.py
-   **Database**: MySQL / MariaDB
-   **AI**: Modular support for Google Gemini and OpenAI