# Sulfur Bot

Big brother is helpful but always watching.

Sulfur is a sophisticated, multi-purpose Discord bot with a unique, sassy Gen-Z personality. It's designed to be a central part of a server community, offering everything from entertainment and games to detailed activity tracking and administration. Powered by modern AI and packed with features, Sulfur keeps your server engaging and lively.

## ✨ Features

- **🤖 AI Chatbot**: Engage in conversations with Sulfur by mentioning it. Powered by either Gemini or OpenAI, it has a configurable personality and remembers past interactions to build "relationships" with users.
- **🐺 Werwolf Game**: A fully automated, voice-based game of Werwolf (Mafia). The bot handles roles, night actions, voting, and TTS announcements, creating an immersive experience.
- **📈 Activity Tracking & `/wrapped`**: Like Spotify Wrapped, but for your Discord server! At the end of each month, users receive a personalized summary of their activity, including:
  - Message and voice chat statistics compared to the server average.
  - Top games played, with leaderboards.
  - Top Spotify songs and artists, with total listening time.
  - An AI-generated witty summary of their monthly activity.
- **🎤 Join to Create Voice Channel**: A "Join to Create" channel that lets users generate their own temporary voice channels, which they can then configure with commands like `/voice config name` and `/voice config lock`.
- **💰 Leveling & Economy**: Users gain XP and currency for sending messages and spending time in voice channels.
- **📊 Profiles & Leaderboards**: A suite of commands to show off stats:
  - `/profile`: Displays a user's level, balance, and game stats.
  - `/rank`: Shows a user's level progress and global rank.
  - `/spotify`: Shows a user's all-time top Spotify songs and artists.
  - `/leaderboard`: A global leaderboard for levels and XP.
- **🔄 Auto-Update & Maintenance**: Includes robust maintenance scripts for both Windows and Linux (Termux) that automatically pull the latest code from Git and restart the bot, ensuring it's always up-to-date.
- **💾 Database Sync**: A built-in, controlled mechanism to synchronize the bot's database between different host machines (e.g., a laptop and a phone) using Git.

## 🚀 Setup and Installation

Follow these steps to get your own instance of Sulfur running.

### Prerequisites

- **Python 3.12+**
- **Git**
- **A MySQL-compatible database**:
  - **Windows**: XAMPP is recommended as it provides MariaDB (a MySQL fork).
  - **Termux/Linux**: MariaDB (`pkg install mariadb`).

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd sulfur
```

### 2. Install Dependencies

Install the required Python libraries using the `requirements.txt` file.

```bash
pip install -r requirements.txt
```

### 3. Database Setup

The bot needs a database and a dedicated user to access it.

1.  Start your MySQL/MariaDB server.
2.  Connect to the database shell (e.g., using `mysql -u root -p` or the XAMPP shell).
3.  Run the following SQL commands:

    ```sql
    CREATE DATABASE sulfur_bot;
    CREATE USER 'sulfur_bot_user'@'localhost' IDENTIFIED BY ''; -- No password for local use
    GRANT ALL PRIVILEGES ON sulfur_bot.* TO 'sulfur_bot_user'@'localhost';
    FLUSH PRIVILEGES;
    EXIT;
    ```

### 4. Configuration

The bot is configured through environment variables set in the startup scripts (`start_bot.sh` and `start_bot.ps1`).

1.  **API Keys**: Open `start_bot.sh` (for Termux/Linux) or `start_bot.ps1` (for Windows) and fill in your API keys:
    - `DISCORD_BOT_TOKEN`: Your bot's token from the Discord Developer Portal.
    - `GEMINI_API_KEY`: Your Google AI Studio API key.
    - `OPENAI_API_KEY`: Your OpenAI API key.

2.  **`config.json`**: This file controls the bot's behavior, personality, and features. Review and customize the settings as needed. For example, you can change the AI provider from `openai` to `gemini`.

3.  **Windows Path (if using XAMPP)**: In `start_bot.ps1`, ensure the `$mysqldumpPath` and `$mysqlPath` variables point to the correct location within your XAMPP installation directory.

### 5. Running the Bot

The bot includes startup scripts for easy execution and maintenance scripts for automatic updates.

#### On Windows (PowerShell)

- **To run directly**:
  ```powershell
  .\start_bot.ps1
  ```
- **For automatic updates**:
  ```powershell
  .\maintain_bot.ps1
  ```

#### On Termux / Linux

First, make the scripts executable:
```bash
chmod +x ./start_bot.sh
chmod +x ./maintain_bot.sh
```

- **To run directly**:
  ```bash
  ./start_bot.sh
  ```
- **For automatic updates (recommended)**: Run inside a `tmux` session to keep it active in the background.
  ```bash
  # Start a new session named 'sulfur'
  tmux new -s sulfur

  # Run the maintenance script inside the session
  ./maintain_bot.sh

  # Detach from the session by pressing CTRL+B, then D
  ```

## 🗃️ Database Synchronization

The bot supports a manual, one-way database synchronization process between devices. This is useful for transferring your bot's data from your phone to your laptop, or vice-versa.

**Workflow to sync from Device A to Device B:**

1.  **On Device A (Source):**
    - Stop the bot. This will automatically trigger an export of the current database state to a file named `database_sync.sql`.
    - Commit and push this file to your Git repository:
      ```bash
      git add database_sync.sql
      git commit -m "Sync database from Device A"
      git push
      ```

2.  **On Device B (Destination):**
    - Start the bot using `start_bot.sh` or `start_bot.ps1`.
    - The script will automatically pull the latest changes. It will detect the updated `database_sync.sql` file and import its contents, overwriting the local database with the state from Device A.

> **⚠️ Warning:** This is a destructive, one-way sync. The database on the destination device will be completely replaced. Always be sure of the direction you want to sync. The `database_sync.sql` file is a text-based SQL dump and is safe for Git, but can become large.

## 🛠️ Usage

Interact with the bot using its slash commands. Here are a few key commands to get started:

- `/profile`: View your user profile.
- `/rank`: Check your server rank and level progress.
- `/spotify`: See your personal Spotify listening stats.
- `/ww start`: Start a new game of Werwolf.
- `/voice setup`: (Admin) Set up the "Join to Create" voice channel.
- **Chat**: Mention the bot (`@Sulfur`) in a channel or send it a DM to start a conversation.