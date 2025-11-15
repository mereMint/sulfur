# Sulfur Bot

A multi-purpose, slightly arrogant Discord bot with a personality. Sulfur offers a range of features from an advanced AI chatbot to server games and management utilities.

## Features

- **Advanced AI Chatbot**: Responds to mentions and its name, with a persistent memory of conversations and relationships with users.
- **Dual AI Provider Support**: Automatically switches between Gemini and OpenAI APIs, with a daily usage counter and fallback mechanism.
- **Interactive AI Dashboard**: Admins can view API usage and switch AI models on the fly using the `/admin ai_dashboard` command.
- **Leveling System**: Users gain XP for sending messages and spending time in voice channels.
- **Economy System**: Users earn currency on level-up, which can be used for future shop features.
- **Werwolf (Werewolf) Game**: A fully integrated, automated game of Werewolf with roles, private threads, and TTS narration.
- **Dynamic Voice Channels**: A "Join to Create" system that lets users create their own temporary voice channels.
- **"Wrapped" Monthly Stats**: A Spotify-style monthly summary of user activity, delivered via DM.
- **And more**: User profiles, leaderboards, Spotify tracking, and various admin utilities.

---

## Installation & Setup Guide

This guide will walk you through setting up the Sulfur bot from scratch. For stable, 24/7 operation, the **Termux / Linux** setup is highly recommended.

### Prerequisites

- **Git**: For cloning the repository.
- **Python 3.11+**: The bot is built on Python.
- **MySQL Server**: A database is required for storing all data.
   - For **Windows**, it's recommended to use XAMPP.
   - For **Termux/Linux**, you can install `mariadb`.

---

### Step 1: Discord Bot Application Setup

Before you can run the code, you need to create a bot application in Discord.

1.  **Create the Application**:
    -   Go to the Discord Developer Portal and click **"New Application"**.
    -   Give your bot a name (e.g., "Sulfur") and agree to the terms.

2.  **Configure the Bot**:
    -   In the left-hand menu, go to the **"Bot"** tab.
    -   Under the "Privileged Gateway Intents" section, **enable all three intents**:
        -   `PRESENCE INTENT`
        -   `SERVER MEMBERS INTENT`
        -   `MESSAGE CONTENT INTENT`
    -   Click **"Save Changes"**.

3.  **Get Your Bot Token**:
    -   At the top of the "Bot" page, click **"Reset Token"**.
    -   Copy this token. You will need it in Step 3. **Do not share this token with anyone.**

4.  **Invite the Bot to Your Server**:
    -   In the left-hand menu, go to **"OAuth2" -> "URL Generator"**.
    -   In the "Scopes" box, check `bot` and `applications.commands`.
    -   In the "Bot Permissions" box that appears, check **`Administrator`**. This is the easiest way to ensure the bot has all the permissions it needs to function.
    -   Copy the generated URL at the bottom of the page, paste it into your browser, and invite the bot to your server.

---

### Step 2: Get the Code

Open your terminal or command prompt and clone the project.

> **Note for Termux/Linux users:** It is highly recommended to set up an SSH key for GitHub first (see the Termux guide below) and use the SSH clone URL. For a quick setup on Windows, the HTTPS URL is fine.

```sh
# Use this for Windows (HTTPS)
git clone https://github.com/mereMint/sulfur.git

# Or use this for Termux/Linux after setting up SSH (recommended)
# git clone git@github.com:mereMint/sulfur.git

cd sulfur
```

### 2. Create the Environment File

The bot uses a `.env` file to store secret keys. Create a file named `.env` in the `c:\sulfur` directory and paste the following content into it.

```env
# This file stores your secret API keys.
# DO NOT commit this file to your Git repository. Add it to your .gitignore file.
DISCORD_BOT_TOKEN="YOUR_DISCORD_BOT_TOKEN_HERE"
GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"
OPENAI_API_KEY="YOUR_OPENAI_API_KEY_HERE"
```

- **`DISCORD_BOT_TOKEN`**: Get this from the "Bot" page on your Discord Developer Portal.
- **`GEMINI_API_KEY`**: Get this from Google AI Studio.
- **`OPENAI_API_KEY`**: Get this from your OpenAI Dashboard.

### 3. Set up the Database

You need to create a database and a dedicated user for the bot.

1.  Access your MySQL server.
2.  Run the following SQL commands:

```sql
-- Create the database
CREATE DATABASE sulfur_bot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create a user for the bot
CREATE USER 'sulfur_bot_user'@'localhost' IDENTIFIED BY ''; -- No password for local use

-- Grant the user all privileges on the new database
GRANT ALL PRIVILEGES ON sulfur_bot.* TO 'sulfur_bot_user'@'localhost';

-- Apply the changes
FLUSH PRIVILEGES;
```

The bot will automatically create the necessary tables when it starts for the first time.

### 4. Run the Bot

The startup scripts will automatically install Python dependencies and start the bot.

#### On Windows:

Open PowerShell, navigate to the `c:\sulfur` directory, and run the maintenance script.

```powershell
.\maintain_bot.ps1
```

#### On Termux / Linux:

First, make the scripts executable. Then, run the maintenance script.

```sh
chmod +x maintain_bot.sh start_bot.sh
./maintain_bot.sh
```

The `maintain_bot` script acts as a watcher that will automatically restart the bot to apply updates from your Git repository.

---

## Configuration

Most of the bot's behavior can be customized by editing the `config.json` file. For a detailed explanation of every setting, please refer to the **CONFIG_DOCUMENTATION.md** file.