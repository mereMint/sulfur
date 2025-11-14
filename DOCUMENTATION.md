# Sulfur Bot - Dokumentation

## Inhaltsverzeichnis
1.  [Projektübersicht](#projektübersicht)
2.  [Features](#features)
3.  [Installation und Einrichtung](#installation-und-einrichtung)
    -   [Windows (Standard)](#windows-standard)
    -   [Android (via Termux)](#android-via-termux)
4.  [Verwendung (Befehle)](#verwendung-befehle)
5.  [Projektstruktur](#projektstruktur)
6.  [Dateibeschreibungen](#dateibeschreibungen)
7.  [Backup und Wiederherstellung](#backup-und-wiederherstellung)
7.  [Werwolf-Spielablauf](#werwolf-spielablauf)

---

## Projektübersicht

Sulfur ist ein multifunktionaler Discord-Bot, der entwickelt wurde, um die Interaktion auf einem Server durch eine Kombination aus Unterhaltung und nützlichen Tools zu verbessern. Er verfügt über eine KI-gesteuerte Chat-Persönlichkeit, ein vollautomatisches Werwolf-Spiel, ein globales Level- und Wirtschaftssystem und dynamische Sprachkanäle.

---

## Features

-   **KI-Chatbot**: Eine freche Gen-Z-Persönlichkeit namens "Sulf", die auf Erwähnungen reagiert und sich durch Chat-Verläufe an Beziehungen zu Benutzern "erinnert".
-   **Werwolf-Spiel**: Ein vollautomatisches Werwolf-Spiel mit verschiedenen Rollen, Bot-Gegnern und atmosphärischen TTS-Ansagen.
-   **Level- & Wirtschaftssystem**: Benutzer verdienen XP und Währung durch Chat- und Sprachaktivität.
-   **Dynamische Sprachkanäle**: Ein "Join to Create"-System, das es Benutzern ermöglicht, temporäre, private Sprachkanäle zu erstellen und zu verwalten.
-   **Datenpersistenz**: Alle Benutzerdaten (Level, Stats, Chat-Verlauf etc.) werden in einer MySQL/MariaDB-Datenbank gespeichert.

---

## Installation und Einrichtung

### Windows (Standard)

**Voraussetzungen:**
-   Python 3.10 oder neuer
-   XAMPP mit Apache und MySQL

**Schritte:**

1.  **Discord Bot-Einstellungen:**
    -   Gehe zum [Discord Developer Portal](https://discord.com/developers/applications).
    -   Wähle deine Bot-Anwendung aus und gehe zum Tab "Bot".
    -   Scrolle nach unten zu "Privileged Gateway Intents" und **aktiviere** die folgenden beiden Optionen:
        -   `PRESENCE INTENT`
        -   `SERVER MEMBERS INTENT`
1.  **Python-Bibliotheken installieren:**
    ```powershell
    pip install discord.py mysql-connector-python aiohttp
    ```
2.  **Datenbank einrichten:**
    -   Starte Apache und MySQL im XAMPP Control Panel.
    -   Öffne phpMyAdmin (Admin-Button neben MySQL).
    -   Erstelle eine neue Datenbank namens `sulfur_bot`.
    -   Erstelle einen neuen Benutzer (`sulfur_bot_user`, Host: `localhost`) ohne Passwort.
    -   Gib diesem Benutzer globale Berechtigungen (`Check all`).
3.  **Bot konfigurieren:**
    -   Öffne die `start_bot.ps1`-Datei.
    -   Trage deine API-Schlüssel für `DISCORD_BOT_TOKEN` und `GEMINI_API_KEY` ein.
4.  **Bot starten:**
    -   Öffne PowerShell, navigiere zum Projektordner (`cd c:\sulfur`) und führe das Skript aus:
    > **Wichtig:** Benutze das `maintain_bot.ps1`-Skript. Es startet den Bot und sucht automatisch jede Minute nach Updates.
    ```powershell
    .\maintain_bot.ps1
    ```

### Android (via Termux)

**Diese Anleitung ist der empfohlene Weg, um den Bot 24/7 stromsparend laufen zu lassen.**

**Voraussetzungen:**
-   Die **Termux**-App. **WICHTIG:** Installiere sie über **F-Droid**, da die Version im Google Play Store veraltet ist und nicht mehr funktioniert.
-   Ein GitHub-Account, um das Projekt zu verwalten (empfohlen).

**Schritte:**

1.  **Schritt 1: Termux-Umgebung einrichten**
    Öffne Termux und führe die folgenden Befehle aus, um die Basis-Software zu installieren:
    ```bash
    # Pakete aktualisieren
    pkg update && pkg upgrade

    # Notwendige Software installieren (python, git, mariadb für die DB, nano als Texteditor)
    pkg install python git mariadb nano

    # Python-Bibliotheken installieren
    pip install discord.py mysql-connector-python aiohttp
    ```

2.  **Schritt 2: Datenbank einrichten**
    MariaDB (eine MySQL-Variante) muss initialisiert und konfiguriert werden:
    ```bash
    # Datenbankverzeichnis initialisieren
    mysql_install_db

    # Datenbankserver im Hintergrund starten
    mysqld_safe -u root &
    ```
    Verbinde dich nun mit dem Datenbankserver, um die Datenbank und den Benutzer für den Bot zu erstellen:
    ```bash
    mysql -u root # Öffnet die MariaDB-Konsole
    ```
    Führe in der MariaDB-Konsole die folgenden SQL-Befehle einzeln aus:
    ```sql
    CREATE DATABASE sulfur_bot;
    CREATE USER 'sulfur_bot_user'@'localhost' IDENTIFIED BY '';
    GRANT ALL PRIVILEGES ON sulfur_bot.* TO 'sulfur_bot_user'@'localhost';
    FLUSH PRIVILEGES;
    EXIT; -- Verlässt die MariaDB-Konsole
    ```

3.  **Schritt 3: Bot-Code herunterladen**
    Der beste Weg, den Code zu verwalten, ist über `git`. Lade den Code aus deinem GitHub-Repository:
    ```bash
    # Lade das Repository von GitHub herunter
    git clone https://github.com/mereMint/sulfur.git sulfur

    # Wechsle in den neu erstellten Ordner
    cd sulfur
    ```

4.  **Schritt 4: Bot konfigurieren**
    Die API-Schlüssel werden in der `start_bot.sh`-Datei gesetzt. Benutze den `nano`-Editor, um sie zu bearbeiten:
    ```bash
    nano start_bot.sh
    ```
    -   Navigiere mit den Pfeiltasten zu den Zeilen `export GEMINI_API_KEY="..."` und `export OPENAI_API_KEY="..."`.
    -   Trage deine Schlüssel zwischen den Anführungszeichen ein.
    -   Speichere die Änderungen mit `STRG + O` (und drücke Enter), dann schließe `nano` mit `STRG + X`.

5.  **Schritt 5: Bot starten**
    ```bash
    # Mache das Start-Skript ausführbar (nur beim ersten Mal nötig)
    chmod +x start_bot.sh

    # Führe das Skript aus, um den Bot zu starten
    ./start_bot.sh
    ```
    Um den Bot dauerhaft im Hintergrund laufen zu lassen (auch wenn die App geschlossen ist), halte die Termux-Benachrichtigung in der Android-Statusleiste gedrückt und wähle "Acquire wakelock".

---

### Code auf Termux aktualisieren

Das `start_bot.sh`-Skript sucht beim Start automatisch nach Updates. Für eine vollautomatische Wartung, die den Bot bei neuen Updates selbstständig neustartet, solltest du das `maintain_bot.sh`-Skript verwenden.

**Anleitung für automatische Wartung mit `tmux`:**
1.  `pkg install tmux`
2.  `tmux new -s sulfur`
3.  Mache das Wartungsskript ausführbar: `chmod +x maintain_bot.sh`
4.  Starte das Wartungsskript: `./maintain_bot.sh`
4.  Verlasse die `tmux`-Sitzung mit `STRG + B`, dann `D`. Der Bot läuft nun im Hintergrund weiter.

---

## Verwendung (Befehle)

-   **Chatbot**: Erwähne den Bot (`@Sulfur`) oder schreibe seinen Namen (`sulf`, `sulfur`), um mit ihm zu chatten.
-   `/rank [user]`: Zeigt Level, XP und Server-Rang eines Benutzers an.
-   `/leaderboard`: Zeigt die Top 10 der aktivsten Benutzer nach Level an.
-   `/stats`: Zeigt das Leaderboard für das Werwolf-Spiel an (Siege/Niederlagen).
-   `/summary [user]`: Zeigt die vom Bot generierte "Meinung" über einen Benutzer an.

#### Werwolf-Befehle (`/ww`)
-   `/ww start [ziel_spieler]`: Startet ein neues Spiel.
> **Hinweis:** Aktionen während der Nacht (kill, see, heal, etc.) werden per Direktnachricht (DM) an den Bot gesendet.
#### Sprachkanal-Befehle (`/voice`)
-   `/voice setup`: (Admin) Erstellt den "Join to Create"-Kanal.
-   `/voice clearall`: (Admin) **GEFAHR!** Löscht alle Sprachkanäle auf dem Server.
-   `/voice config name <name>`: (Channel-Besitzer) Benennt den eigenen Kanal um.
-   `/voice config limit <zahl>`: (Channel-Besitzer) Setzt ein Benutzerlimit.
-   `/voice config lock`/`unlock`: (Channel-Besitzer) Macht den Kanal privat/öffentlich.
-   `/voice config permit`/`unpermit <user>`: (Channel-Besitzer) Erteilt/entzieht einem Benutzer die Beitrittserlaubnis.

#### Admin-Befehle (`/admin`)
*Benötigt Admin-Rechte oder die "authorised"-Rolle.*
-   `/admin save_history [limit]`: Speichert den Chatverlauf eines Kanals in der Datenbank.
-   `/admin clear_history`: Löscht den gespeicherten Verlauf für einen Kanal.

---

## Projektstruktur

Das Projekt ist in mehrere Module aufgeteilt, um die Verantwortlichkeiten klar zu trennen:

-   `bot.py`: Der Haupteinstiegspunkt. Handhabt die Discord-Client-Verbindung, Event-Listener und die Registrierung von Befehlen.
-   `werwolf.py`: Enthält die gesamte Spiellogik und Zustandsverwaltung für das Werwolf-Spiel.
-   `api_helpers.py`: Zentralisiert alle API-Aufrufe an Google Gemini.
-   `db_helpers.py`: Verwaltet alle Datenbankinteraktionen.
-   `voice_manager.py`: Enthält die Logik für die dynamischen Sprachkanäle.
-   `level_system.py` & `economy.py`: Enthält die Logik für das Level- und Wirtschaftssystem.
-   `fake_user.py`: Stellt eine Mock-Benutzerklasse für Bot-Spieler bereit.
-   `start_bot.ps1`: Ein Skript zum einfachen Starten des Bots unter Windows.
-   `start_bot.sh`: Ein Skript zum einfachen Starten des Bots auf Android (Termux).

---

## Dateibeschreibungen

### `bot.py`

**Hauptverantwortlichkeiten:**
-   **Konfiguration & Start**: Lädt API-Schlüssel aus Umgebungsvariablen und startet den Discord-Client.
-   **Event-Handling**:
    -   `on_ready()`: Führt beim Start Bereinigungsroutinen für verwaiste Kanäle aus und startet Hintergrund-Tasks.
    -   `on_message()`: Löst die Chatbot-Funktionalität und das XP-System aus.
    -   `on_voice_state_update()`: Delegiert an den `voice_manager` und die Werwolf-Lobby-Logik.
    -   `on_presence_update()`: Verfolgt Benutzeraktivitäten und Spotify-Songs.
-   **Slash-Befehle**: Definiert und registriert alle Benutzerbefehle (`/ww`, `/voice`, `/rank` etc.).
-   **Hintergrund-Tasks**: `grant_voice_xp` und `update_presence_task` laufen periodisch, um XP zu vergeben und den Bot-Status zu aktualisieren.

### `werwolf.py`

-   **`WerwolfPlayer`**: Eine Datenklasse, die einen Spieler repräsentiert. Sie speichert das `discord.User`-Objekt (oder `FakeUser`), die zugewiesene Rolle, den Lebensstatus und Trank-Informationen für die Hexe.
-   **`WerwolfGame`**: Eine komplexe Zustandsmaschine, die ein Spiel von Anfang bis Ende verwaltet.
-   **`VotingView`**: Eine `discord.ui.View`-Unterklasse, die die interaktive Abstimmungsoberfläche während der Tagesphase erstellt.

### `api_helpers.py`

-   **`get_gemini_response()`**: Erstellt die Anfrage für die allgemeine Chatbot-Funktionalität. Fügt den System-Prompt und den Chat-Verlauf hinzu, um der KI Kontext und Persönlichkeit zu geben.
-   **`get_werwolf_tts_message()`**: Verwendet einen speziellen Prompt, um Gemini anzuweisen, als unheimlicher Spielleiter zu agieren und eine kurze, thematische Ansage für ein Spielereignis zu generieren.
-   **`get_random_names()`**: Bittet Gemini um eine JSON-formatierte Liste altmodischer deutscher Namen, die für die Bot-Gegner verwendet werden.
-   **`get_relationship_summary_from_gemini()`**: Analysiert einen Chatverlauf, um die "Meinung" des Bots über einen Benutzer zu aktualisieren.

### `fake_user.py`

-   **`FakeUser`**: Simuliert ein `discord.User`-Objekt. Dies ist notwendig, damit die `WerwolfGame`-Logik Bot-Spieler und menschliche Spieler weitgehend gleich behandeln kann (z. B. beim Hinzufügen zu `game.players`, beim Zuweisen von Rollen).

### `start_bot.ps1`

Ein PowerShell-Skript für Windows-Benutzer, das Umgebungsvariablen setzt, den XAMPP MySQL-Server startet, eine Datenbanksicherung erstellt und dann den Bot ausführt.

---

## Werwolf-Spielablauf

1.  **Start**: Ein Benutzer führt `/ww start` aus.
2.  **Spielbeginn**: Nach 15 Sekunden.
    -   Rollen werden zugewiesen und per DM verteilt.
    -   Ein privater Thread für Werwölfe wird erstellt.
3.  **Nachtphase**:
    -   Spieler werden stummgeschaltet.
    -   Spezialrollen nutzen ihre Fähigkeiten über Slash-Befehle.
    -   Die Phase endet, wenn alle Aktionen ausgeführt wurden.
4.  **Tagesphase**:
    -   Die Stummschaltung wird aufgehoben.
    -   Die Opfer der Nacht werden enthüllt.
    -   Eine interaktive Abstimmung über Buttons startet.
5.  **Abstimmung**:
    -   Die Abstimmung endet nach einer Zeit, bei einer Mehrheit oder wenn alle abgestimmt haben.
    -   Der Spieler mit den meisten Stimmen wird gelyncht.
6.  **Schleifenende**:
    -   Wenn keine Fraktion gewonnen hat, beginnt die nächste Nacht.
7.  **Spielende**:
    -   Die Gewinner werden bekannt gegeben und Statistiken gespeichert.
    -   Alle temporären Spiel-Kanäle werden automatisch gelöscht.

---

## Backup und Wiederherstellung

### Automatisches Backup

Jedes Mal, wenn der Bot mit dem `start_bot.ps1`-Skript gestartet wird, wird automatisch eine Sicherung der `sulfur_bot`-Datenbank erstellt. Diese Sicherungen werden als `.sql`-Dateien mit Zeitstempel im Ordner `c:\sulfur\backups\` gespeichert.

### Manuelle Wiederherstellung

Um die Datenbank aus einer Sicherungsdatei wiederherzustellen, führe die folgenden Schritte aus:

1.  Stelle sicher, dass dein MySQL-Server über das XAMPP Control Panel läuft.
2.  Öffne phpMyAdmin und lösche alle Tabellen in deiner `sulfur_bot`-Datenbank (oder lösche und erstelle die Datenbank neu).
3.  Gehe zum Tab "Importieren".
4.  Klicke auf "Datei auswählen" und wähle die `.sql`-Sicherungsdatei aus dem `c:\sulfur\backups\`-Ordner, die du wiederherstellen möchtest.
5.  Scrolle nach unten und klicke auf "Importieren", um den Vorgang zu starten.