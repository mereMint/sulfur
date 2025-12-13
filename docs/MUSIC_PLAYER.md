# Music Player Enhancement Documentation

## Overview

The music player has been significantly enhanced to provide a richer experience with multiple station types, auto-disconnect functionality, and personalized Spotify-based stations.

## Command: `/music`

The new `/music` command replaces the old `/lofi` command (which is still available for backward compatibility).

### Basic Usage

```
/music action:Start station_type:lofi station_index:0
```

### Parameters

- **action** (required): What to do
  - `▶️ Start` - Start playing music
  - `⏹️ Stop` - Stop music and leave voice channel
  - `📋 Liste alle Stationen` - List all available stations

- **station_type** (optional): Type of music/sounds to play
  - `🎧 Lofi Beats` - Relaxing lofi hip-hop beats
  - `🎵 No Copyright Music` - Royalty-free music for streaming
  - `🌧️ Ambient Sounds` - Natural and ambient soundscapes

- **station_index** (optional, default: 0): Which station of that type to play
  - `0` = first station
  - `1` = second station, etc.

- **use_spotify_mix** (optional, default: False): Use your Spotify listening history
  - When `True`, creates a personalized station based on your most played songs
  - Requires that you've listened to Spotify while Discord is running

### Examples

#### List all stations
```
/music action:list
```

#### Play first lofi station
```
/music action:Start station_type:lofi station_index:0
```

#### Play rain sounds
```
/music action:Start station_type:ambient station_index:0
```

#### Play personalized Spotify mix
```
/music action:Start use_spotify_mix:True
```

#### Stop playback
```
/music action:Stop
```

## Available Stations

### 🎧 Lofi Beats (2 stations)
- `0` - 📚 Beats to Relax/Study
- `1` - 🎧 Beats to Sleep/Chill

### 🎵 No Copyright Music (2 stations)
- `0` - 🎵 No Copyright Music
- `1` - 🎸 Royalty Free Music

### 🌧️ Ambient Sounds (5 stations)
- `0` - 🌧️ Rain Sounds
- `1` - 🌊 Ocean Waves
- `2` - 🔥 Fireplace Sounds
- `3` - ☕ Coffee Shop Ambience
- `4` - 🌳 Forest Sounds

## Features

### 1. Ephemeral Messages
All messages from the music player are now **ephemeral** (only visible to you). This keeps the chat clean and prevents spam.

### 2. Auto-Disconnect
The bot will automatically leave the voice channel if it's alone for more than **2 minutes**. This prevents the bot from staying in empty channels indefinitely.

**How it works:**
- When you leave the channel, a 2-minute timer starts
- If someone else joins within 2 minutes, the timer is cancelled
- If no one joins, the bot stops playback and leaves
- The timer is also cancelled if you manually stop playback

### 3. Spotify Mix
If you've been listening to Spotify while Discord is running, the bot can create a personalized music station based on your listening history!

**Requirements:**
- You must have listened to Spotify with Discord open
- The bot tracks your Spotify activity automatically
- Your most played songs are used to generate the mix

**Usage:**
```
/music action:Start use_spotify_mix:True
```

The station will be named "🎧 {YourUsername}'s Mix" and will play music similar to your top songs.

### 4. Multiple Station Types
Choose from three categories of audio:
- **Lofi Beats**: Perfect for studying, working, or relaxing
- **No Copyright Music**: Safe for streaming without copyright claims
- **Ambient Sounds**: Natural soundscapes for focus or relaxation

## Backward Compatibility

The old `/lofi` command still works for users who are used to it:

```
/lofi action:Start stream:0
```

However, it now shows a message encouraging users to try the new `/music` command with more options.

## Technical Details

### Auto-Disconnect Implementation
- Tracks active sessions per guild
- Uses asyncio tasks for timer management
- Integrates with voice state update handler
- Cancels timers when users join/rejoin
- Cleans up sessions on disconnect

### Spotify Mix Generation
- Reads from the `spotify_history` column in the players table
- Sorts songs by play count
- Uses top song for YouTube search
- Creates a dynamic station URL

### Station Management
- Stations are defined in `modules/lofi_player.py`
- Easy to add new stations by editing `MUSIC_STATIONS` dictionary
- Each station has: name, URL, and type

### File Changes
- `modules/lofi_player.py` - Enhanced with new features
- `bot.py` - New `/music` command and voice state handler integration
- Auto-disconnect logic runs in background

## Adding New Stations

To add a new station, edit `modules/lofi_player.py` and add to the `MUSIC_STATIONS` dictionary:

```python
"ambient": [
    # ... existing stations ...
    {
        "name": "🌙 Night Sounds",
        "url": "https://www.youtube.com/watch?v=YOUR_VIDEO_ID",
        "type": "ambient"
    }
]
```

You can also add new categories:

```python
MUSIC_STATIONS = {
    "lofi": [...],
    "nocopyright": [...],
    "ambient": [...],
    "jazz": [  # New category
        {
            "name": "🎷 Smooth Jazz",
            "url": "https://www.youtube.com/watch?v=YOUR_VIDEO_ID",
            "type": "jazz"
        }
    ]
}
```

Then add the category to the command choices in `bot.py`:

```python
@app_commands.choices(station_type=[
    app_commands.Choice(name="🎧 Lofi Beats", value="lofi"),
    app_commands.Choice(name="🎵 No Copyright Music", value="nocopyright"),
    app_commands.Choice(name="🌧️ Ambient Sounds", value="ambient"),
    app_commands.Choice(name="🎷 Jazz", value="jazz")  # New choice
])
```

## Troubleshooting

### "Fehler beim Starten der Musik!"
- Make sure `yt-dlp` is installed: `pip install yt-dlp`
- Make sure FFmpeg is installed on your system
- Check that the bot has permission to join voice channels

### "Keine Spotify-History gefunden!"
- You need to listen to Spotify with Discord open
- The bot tracks your Spotify activity automatically
- Wait a few minutes after listening, then try again

### Bot doesn't auto-disconnect
- The timer is 2 minutes - be patient
- Check that the bot is actually alone in the channel
- Other bots don't count as "users" for this purpose

### Can't hear anything
- Make sure you're in the same voice channel as the bot
- Check your Discord audio settings
- Try stopping and restarting playback

## Future Enhancements (Planned)

- **Audio Mixing**: Play multiple stations at once with volume control
  - Example: Quiet lofi beats + rain sounds
  - Volume sliders for each source
  - Note: Framework is in place but requires additional FFmpeg integration work
  - Current limitation: discord.py's FFmpegPCMAudio only supports single URL source
  
- **Custom Playlists**: Save your favorite station combinations

- **More Stations**: Additional music genres and ambient sounds

- **Volume Control**: Adjust bot's volume without affecting other audio

## Known Limitations

- **Multi-Station Mixing**: The `create_mixed_audio_source()` and `play_mixed_stations()` functions exist but are currently experimental. Discord.py's FFmpegPCMAudio class is designed for single audio sources. Proper multi-source mixing would require custom FFmpeg piping or alternative approaches.

- **Station URLs**: Some YouTube streams may occasionally be unavailable or change. If a station doesn't work, try a different one.

## See Also

- `/focus` - Pomodoro timer (pairs well with music)
- Main documentation: `README.md`
- Configuration: `config/config.json`
