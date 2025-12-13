# 🎵 Music Command - Visual Preview

## Command Structure

```
/music action:[Start|Stop|List] station_type:[lofi|nocopyright|ambient] station_index:0 use_spotify_mix:False
```

---

## Example: Browse Stations (`/music action:list`)

```
╔══════════════════════════════════════════════════════════╗
║  🎵 Music & Sounds Player                                ║
╠══════════════════════════════════════════════════════════╣
║  ## Wähle deine perfekte Atmosphäre                     ║
║  *Nutze `/music action:Start` um loszulegen!*           ║
║                                                          ║
║  🎧 Lofi Beats                                           ║
║  **`0`** 📚 Beats to Relax/Study                        ║
║  **`1`** 🎧 Beats to Sleep/Chill                        ║
║  *Perfekt zum Lernen und Entspannen*                    ║
║                                                          ║
║  🎵 No Copyright Music                                   ║
║  **`0`** 🎵 No Copyright Music                          ║
║  **`1`** 🎸 Royalty Free Music                          ║
║  *Sicher für Streams und Videos*                        ║
║                                                          ║
║  🌧️ Ambient Sounds                                       ║
║  **`0`** 🌧️ Rain Sounds                                 ║
║  **`1`** 🌊 Ocean Waves                                 ║
║  **`2`** 🔥 Fireplace Sounds                            ║
║  **`3`** ☕ Coffee Shop Ambience                        ║
║  **`4`** 🌳 Forest Sounds                               ║
║  *Natürliche Klänge für Fokus*                          ║
║                                                          ║
║  💡 Beispiele                                            ║
║  ```                                                     ║
║  /music action:Start station_type:lofi station_index:0  ║
║  /music action:Start station_type:ambient station_index:0
║  /music action:Start use_spotify_mix:True              ║
║  ```                                                     ║
║                                                          ║
║  ✨ Spotify Mix                                          ║
║  Setze `use_spotify_mix:True` für personalisierte       ║
║  Musik basierend auf deiner Spotify-History!            ║
║                                                          ║
║  👤 [User Avatar]                                        ║
║  Angefordert von Username                               ║
╚══════════════════════════════════════════════════════════╝
```

---

## Example: Start Music (`/music action:start station_type:lofi`)

```
╔══════════════════════════════════════════════════════════╗
║  🎧 Jetzt läuft                                          ║
╠══════════════════════════════════════════════════════════╣
║  ## 📚 Beats to Relax/Study                             ║
║  *Genieße deine Musik!*                                  ║
║                                                          ║
║  📍 Voice Channel        🎼 Kategorie                    ║
║  **General Voice**       **🎧 Lofi Beats**              ║
║  *3 Mitglieder*                                          ║
║                                                          ║
║  👤 Gestartet von                                        ║
║  **Username**                                            ║
║                                                          ║
║  ⏯️ Steuerung                                            ║
║  **Stop:** `/music action:Stop`                         ║
║  **Andere Station:** `/music action:list`               ║
║                                                          ║
║  🤖 Auto-Disconnect                                      ║
║  *Der Bot verlässt automatisch nach 2 Minuten,          ║
║   wenn er alleine ist*                                   ║
║                                                          ║
║  👤 [User Avatar]                                        ║
║  Viel Spaß! • Angefordert von Username                  ║
╚══════════════════════════════════════════════════════════╝
```

---

## Example: Spotify Mix (`/music action:start use_spotify_mix:True`)

```
╔══════════════════════════════════════════════════════════╗
║  🎧 Jetzt läuft                                          ║
╠══════════════════════════════════════════════════════════╣
║  ## 🎧 Username's Mix                                   ║
║  *Genieße deine Musik!*                                  ║
║                                                          ║
║  📍 Voice Channel        🎼 Kategorie                    ║
║  **Music Room**          **🎧 Personalisierter Mix**    ║
║  *2 Mitglieder*                                          ║
║                                                          ║
║  👤 Gestartet von                                        ║
║  **Username**                                            ║
║                                                          ║
║  🎯 Basierend auf                                        ║
║  *Song Title by Artist Name*                            ║
║  ▸ Dein meistgespielter Song!                           ║
║                                                          ║
║  ⏯️ Steuerung                                            ║
║  **Stop:** `/music action:Stop`                         ║
║  **Andere Station:** `/music action:list`               ║
║                                                          ║
║  🤖 Auto-Disconnect                                      ║
║  *Der Bot verlässt automatisch nach 2 Minuten,          ║
║   wenn er alleine ist*                                   ║
║                                                          ║
║  👤 [User Avatar]                                        ║
║  Viel Spaß! • Angefordert von Username                  ║
╚══════════════════════════════════════════════════════════╝
```

---

## Example: Stop Music (`/music action:stop`)

```
╔══════════════════════════════════════════════════════════╗
║  ⏹️ Musik gestoppt                                       ║
╠══════════════════════════════════════════════════════════╣
║  ## Playback beendet                                    ║
║  *Bis zum nächsten Mal!*                                 ║
║                                                          ║
║  📍 Verlassener Channel  👤 Gestoppt von                 ║
║  **General Voice**       **Username**                    ║
║                                                          ║
║  🎵 Erneut starten                                       ║
║  Nutze `/music action:Start` um wieder loszulegen!      ║
║                                                          ║
║  👤 [User Avatar]                                        ║
║  Auf Wiedersehen! • Username                            ║
╚══════════════════════════════════════════════════════════╝
```

---

## Example: Error - Not in Voice (`/music action:start`)

```
╔══════════════════════════════════════════════════════════╗
║  ❌ Nicht in Voice-Channel                              ║
╠══════════════════════════════════════════════════════════╣
║  Du musst in einem Voice-Channel sein, um Musik zu      ║
║  hören!                                                  ║
║                                                          ║
║  💡 Tipp                                                 ║
║  Trete einem Voice-Channel bei und versuche es erneut.  ║
╚══════════════════════════════════════════════════════════╝
```

---

## Example: Error - No Spotify History

```
╔══════════════════════════════════════════════════════════╗
║  📊 Keine Spotify-History                               ║
╠══════════════════════════════════════════════════════════╣
║  Ich konnte keine Spotify-Hördaten für dich finden!    ║
║                                                          ║
║  📝 Wie es funktioniert                                  ║
║  • Höre Musik auf Spotify mit Discord geöffnet         ║
║  • Der Bot speichert automatisch deine Lieblingssongs   ║
║  • Danach kannst du personalisierte Mixes erstellen!    ║
║                                                          ║
║  💡 Alternative                                          ║
║  Nutze stattdessen eine unserer vorgefertigten          ║
║  Stationen! Verwende `/music action:list` um alle       ║
║  Optionen zu sehen.                                      ║
╚══════════════════════════════════════════════════════════╝
```

---

## Design Features

### Visual Elements
- ✅ **Markdown Headers**: ## for prominence
- ✅ **Bold Text**: ** ** for emphasis
- ✅ **Italic Text**: * * for subtlety
- ✅ **Code Blocks**: ``` ``` for commands
- ✅ **Inline Code**: ` ` for values
- ✅ **Emojis**: Contextual icons throughout
- ✅ **User Avatars**: Thumbnails on embeds
- ✅ **Custom Colors**: Per-user preferences

### Layout Structure
- **Title**: Large header with emoji
- **Description**: Markdown formatted subtitle
- **Fields**: Structured info sections
  - Inline fields: Side-by-side info
  - Block fields: Full-width sections
- **Footer**: User attribution with avatar

### Color Scheme
- **Primary**: User's custom color (from shop)
- **Success**: Purple/Blue for active playback
- **Error**: Red for problems
- **Info**: Blue for informational
- **Warning**: Orange for warnings

### User Experience
- **Ephemeral**: All messages private to user
- **Clear Hierarchy**: Headers → Fields → Footer
- **Helpful Errors**: Solutions included
- **Examples**: Code blocks show usage
- **Consistency**: Same style across all responses

---

## Comparison: Old vs New

### Old `/lofi` Command
```
╔═══════════════════════════════════╗
║  🎵 Lofi Music Player             ║
╠═══════════════════════════════════╣
║  Jetzt läuft: Beats to Relax/Study║
║                                   ║
║  📍 Channel                        ║
║  General Voice                    ║
║                                   ║
║  ⏯️ Steuerung                     ║
║  Nutze /lofi action:Stop          ║
║                                   ║
║  Viel Spaß beim Entspannen! 🎧   ║
╚═══════════════════════════════════╝
```

### New `/music` Command
```
╔══════════════════════════════════════════════════════════╗
║  🎧 Jetzt läuft                                          ║
╠══════════════════════════════════════════════════════════╣
║  ## 📚 Beats to Relax/Study                             ║
║  *Genieße deine Musik!*                                  ║
║                                                          ║
║  📍 Voice Channel        🎼 Kategorie                    ║
║  **General Voice**       **🎧 Lofi Beats**              ║
║  *3 Mitglieder*                                          ║
║                                                          ║
║  👤 Gestartet von                                        ║
║  **Username**                                            ║
║                                                          ║
║  ⏯️ Steuerung                                            ║
║  **Stop:** `/music action:Stop`                         ║
║  **Andere Station:** `/music action:list`               ║
║                                                          ║
║  🤖 Auto-Disconnect                                      ║
║  *Der Bot verlässt automatisch nach 2 Minuten,          ║
║   wenn er alleine ist*                                   ║
║                                                          ║
║  👤 [User Avatar]                                        ║
║  Viel Spaß! • Angefordert von Username                  ║
╚══════════════════════════════════════════════════════════╝
```

### Improvements
1. ✅ **Markdown formatting** for better hierarchy
2. ✅ **User avatar** for personalization
3. ✅ **Member count** for context
4. ✅ **Inline fields** for compact layout
5. ✅ **More information** without clutter
6. ✅ **Auto-disconnect** notification
7. ✅ **Better structure** with clear sections
8. ✅ **Custom colors** per user
9. ✅ **Contextual emojis** for station types
10. ✅ **Professional look** matching modern Discord bots

---

## Technical Notes

### Embed Colors
- Retrieved via `get_user_embed_color(user_id, config)`
- Falls back to default if user has no custom color
- Stored in database from shop purchases

### Ephemeral Messages
- `ephemeral=True` on all followup responses
- Keeps server channels clean
- Private to command user only

### Error Handling
- Every error has a helpful embed
- Solutions provided where applicable
- Consistent error format

### Station Emojis
```python
type_emojis = {
    "lofi": "🎧",
    "nocopyright": "🎵",
    "ambient": "🌧️",
    "spotify_mix": "🎧"
}
```

---

This visual design creates a modern, professional, and user-friendly experience that matches the style of other commands in the Sulfur bot! 🚀
