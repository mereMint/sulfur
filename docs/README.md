<div align="center">
  <img src="https://raw.githubusercontent.com/mereMint/sulfur/main/assets/sulfur_logo.png" alt="Sulfur Bot Logo" width="150"/>
  <h1>Sulfur Bot 🤖</h1>
  <p>
    A multi-purpose, slightly arrogant Discord bot with a strong personality. Sulfur offers a range of features from an advanced AI chatbot to server games and management utilities, all designed to feel like a "friend" in your server.
  </p>
  <p>
    <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python 3.11+">
    <img src="https://img.shields.io/badge/discord.py-v2.3.2-7289DA.svg" alt="discord.py">
    <img src="https://img.shields.io/badge/AI-Gemini_&_OpenAI-green.svg" alt="AI Powered">
  </p>
</div>

---

## ✨ Features

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

## 🚀 Installation Guide

This guide will walk you through setting up the Sulfur bot from scratch. For stable, 24/7 hosting, the **Termux/Linux** setup is highly recommended.

### Part 1: Prerequisites

First, ensure you have the necessary base software installed on your system.

<details>
<summary><strong>On Windows</strong></summary>

1.  **Git for Windows**: Download and install from git-scm.com.
2.  **Python**: Download and install Python 3.11+ from python.org. **Important**: During installation, check the box that says "Add Python to PATH".
3.  **XAMPP**: Download and install from apachefriends.org. This package provides the MySQL database server. After installation, open the XAMPP Control Panel and start the "Apache" and "MySQL" modules.

</details>

<details>
<summary><strong>On Termux (Android)</strong></summary>

Open Termux and run the following commands to install everything you need:

```sh
# Update package lists
pkg update && pkg upgrade

# Install required packages
pkg install git python mariadb tmux
```

</details>

<details>
<summary><strong>On Debian/Ubuntu Linux</strong></summary>

Open your terminal and run the following commands:

```sh
# Update package lists
sudo apt update && sudo apt upgrade

# Install required packages
sudo apt install git python3 python3-pip mariadb-server tmux
```

</details>

### Part 2: Discord Bot Setup

Before running the code, you must create a bot application in the Discord Developer Portal.

1.  **Create the Application**: Go to the Discord Developer Portal and click **"New Application"**. Give it a name and agree to the terms.
2.  **Configure the Bot**:
    *   Navigate to the **"Bot"** tab.
    *   Under **Privileged Gateway Intents**, enable all three intents: `PRESENCE INTENT`, `SERVER MEMBERS INTENT`, and `MESSAGE CONTENT INTENT`.
    *   Click **"Save Changes"**.
3.  **Get Your Bot Token**: At the top of the "Bot" page, click **"Reset Token"**. Copy this token immediately. **Do not share this token with anyone.**
4.  **Invite the Bot**:
    *   Go to **"OAuth2" -> "URL Generator"**.
    *   Select the scopes `bot` and `applications.commands`.
    *   In the "Bot Permissions" box that appears, select **`Administrator`**.
    *   Copy the generated URL, paste it into your browser, and invite the bot to your server.

### Part 3: Project Setup

Now, let's get the code and configure it.

1.  **Clone the Repository**
    Open your terminal (Git Bash on Windows, Termux on Android) and run:
    ```sh
    git clone https://github.com/mereMint/sulfur.git
    cd sulfur
    ```

2.  **Create the Environment File**
    The bot uses a `.env` file to store your secret keys. In the `sulfur` directory, create a file named `.env` and add the following, replacing the placeholder text with your actual keys.

    ```dotenv
    # This file stores your secret API keys.
    # It is already in .gitignore to prevent accidental commits.
    DISCORD_BOT_TOKEN="YOUR_DISCORD_BOT_TOKEN_HERE"
    GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"
    OPENAI_API_KEY="YOUR_OPENAI_API_KEY_HERE"
    ```
    - **`DISCORD_BOT_TOKEN`**: The token you got in Part 2.
    - **`GEMINI_API_KEY`**: Get this from Google AI Studio.
    - **`OPENAI_API_KEY`**: Get this from your OpenAI Dashboard.

3.  **Set up the Database**
    You need to create a database and a dedicated user for the bot.

    *   **On Windows**: Open the XAMPP Control Panel and click the "Shell" button.
    *   **On Termux/Linux**: Start the MySQL server by running `mysqld_safe --user=root &` (Termux) or `sudo systemctl start mariadb` (Linux).

    Then, access the MySQL command line by typing `mysql -u root`. Once inside, run the following SQL commands:

    ```sql
    -- Create the database with the correct character set
    CREATE DATABASE sulfur_bot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

    -- Create a user for the bot (no password needed for local hosting)
    CREATE USER 'sulfur_bot_user'@'localhost' IDENTIFIED BY '';

    -- Grant the user all privileges on the new database
    GRANT ALL PRIVILEGES ON sulfur_bot.* TO 'sulfur_bot_user'@'localhost';

    -- Apply the changes and exit
    FLUSH PRIVILEGES;
    EXIT;
    ```
    The bot will automatically create the necessary tables on its first run.

### Part 4: Running the Bot

The startup scripts (`start_bot.ps1` and `start_bot.sh`) are designed to handle everything: installing Python packages, backing up the database, and running the bot. The `maintain_bot` scripts act as a wrapper that provides auto-restarts on updates.

#### On Windows (for Development)

Simply open PowerShell, navigate to the `sulfur` directory, and run the maintenance script. This will open a new window for the bot.

```powershell
cd path\to\sulfur
.\maintain_bot.ps1
```

#### On Termux / Linux (for 24/7 Hosting)

To keep the bot running 24/7 even after you close the terminal, we will use **`tmux`**, a terminal multiplexer. The `maintain_bot.sh` script will then handle auto-restarts for updates inside this persistent session.

1.  **Make Scripts Executable**
    This only needs to be done once.
    ```sh
    chmod +x maintain_bot.sh start_bot.sh
    ```

2.  **Start a `tmux` Session**
    We'll create a new session named `sulfur`.
    ```sh
    tmux new -s sulfur
    ```
    Your terminal will clear and you are now inside the `tmux` session.

3.  **Run the Maintenance Script**
    Inside the `tmux` session, start the bot's watcher script.
    ```sh
    ./maintain_bot.sh
    ```
    You will see the bot's startup logs. It is now running and will automatically restart on updates.

4.  **Detach and Re-attach**
    You can now safely close Termux or your SSH client. The bot will continue running in the background.
    -   **To detach** from the session without stopping it, press `Ctrl+b` then `d`.
    -   **To re-attach** later to see the logs or stop the bot, open a new terminal and run: `tmux attach -t sulfur`

---

## ⚙️ Configuration

Most of the bot's behavior can be customized by editing the `config.json` file. For a detailed explanation of every setting, please refer to the **CONFIG_DOCUMENTATION.md** file.

Notes:
- The maintenance script writes status to `config/bot_status.json` for the web dashboard.
- The web dashboard is served by Waitress on port 5000; change the port in `web_dashboard.py` by editing the `serve(..., port=5000)` call if needed.