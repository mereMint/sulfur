"""
Sulfur Bot - Songle (Guess the Song) Game Module
A daily song guessing game where players listen to audio clips and guess the song.
"""

# Standard library imports
import asyncio
import json
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any

# Third-party imports
import discord

# Optional: yt_dlp for audio playback
try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False

# Local imports
from modules.logger_utils import bot_logger as logger

# Active games per user
active_songle_games: Dict[int, 'SongleGame'] = {}

# Daily play tracking
daily_plays: Dict[str, Dict[int, int]] = {}  # {date_str: {user_id: play_count}}

# Audio URL cache
_audio_url_cache: Dict[int, str] = {}  # {song_id: youtube_url}

# Cache for daily song
_daily_song_cache: Dict[str, dict] = {}
_last_cache_date: Optional[str] = None

# Song database - expanded collection of popular songs across different genres and eras
# For production, consider integrating with Spotify or Last.fm API
SONG_DATABASE = [
    # 2020s Hits
    {'id': 1, 'title': 'Blinding Lights', 'artist': 'The Weeknd', 'year': 2019, 'genre': 'Synth-pop', 'album': 'After Hours'},
    {'id': 2, 'title': 'Bad Guy', 'artist': 'Billie Eilish', 'year': 2019, 'genre': 'Electropop', 'album': 'When We All Fall Asleep'},
    {'id': 3, 'title': 'Watermelon Sugar', 'artist': 'Harry Styles', 'year': 2019, 'genre': 'Pop Rock', 'album': 'Fine Line'},
    {'id': 4, 'title': 'Levitating', 'artist': 'Dua Lipa', 'year': 2020, 'genre': 'Disco Pop', 'album': 'Future Nostalgia'},
    {'id': 5, 'title': 'Drivers License', 'artist': 'Olivia Rodrigo', 'year': 2021, 'genre': 'Pop', 'album': 'SOUR'},
    {'id': 6, 'title': 'Stay', 'artist': 'The Kid LAROI & Justin Bieber', 'year': 2021, 'genre': 'Pop', 'album': 'F*CK LOVE 3'},
    {'id': 7, 'title': 'Peaches', 'artist': 'Justin Bieber', 'year': 2021, 'genre': 'R&B', 'album': 'Justice'},
    {'id': 8, 'title': 'Save Your Tears', 'artist': 'The Weeknd', 'year': 2020, 'genre': 'Synth-pop', 'album': 'After Hours'},
    {'id': 9, 'title': 'Montero', 'artist': 'Lil Nas X', 'year': 2021, 'genre': 'Pop Rap', 'album': 'Montero'},
    {'id': 10, 'title': 'Good 4 U', 'artist': 'Olivia Rodrigo', 'year': 2021, 'genre': 'Pop Punk', 'album': 'SOUR'},
    {'id': 11, 'title': 'Heat Waves', 'artist': 'Glass Animals', 'year': 2020, 'genre': 'Indie Pop', 'album': 'Dreamland'},
    {'id': 12, 'title': 'Anti-Hero', 'artist': 'Taylor Swift', 'year': 2022, 'genre': 'Synth-pop', 'album': 'Midnights'},
    {'id': 13, 'title': 'As It Was', 'artist': 'Harry Styles', 'year': 2022, 'genre': 'Synth-pop', 'album': "Harry's House"},
    {'id': 14, 'title': 'About Damn Time', 'artist': 'Lizzo', 'year': 2022, 'genre': 'Disco', 'album': 'Special'},
    {'id': 15, 'title': 'Flowers', 'artist': 'Miley Cyrus', 'year': 2023, 'genre': 'Pop', 'album': 'Endless Summer Vacation'},
    # 2010s Hits
    {'id': 16, 'title': 'Shape of You', 'artist': 'Ed Sheeran', 'year': 2017, 'genre': 'Pop', 'album': '÷ (Divide)'},
    {'id': 17, 'title': 'Uptown Funk', 'artist': 'Mark Ronson ft. Bruno Mars', 'year': 2014, 'genre': 'Funk', 'album': 'Uptown Special'},
    {'id': 18, 'title': 'Despacito', 'artist': 'Luis Fonsi ft. Daddy Yankee', 'year': 2017, 'genre': 'Reggaeton', 'album': 'Vida'},
    {'id': 19, 'title': 'Old Town Road', 'artist': 'Lil Nas X', 'year': 2019, 'genre': 'Country Rap', 'album': '7 EP'},
    {'id': 20, 'title': 'Closer', 'artist': 'The Chainsmokers ft. Halsey', 'year': 2016, 'genre': 'EDM', 'album': 'Collage'},
    {'id': 21, 'title': 'Havana', 'artist': 'Camila Cabello', 'year': 2017, 'genre': 'Pop', 'album': 'Camila'},
    {'id': 22, 'title': 'Shallow', 'artist': 'Lady Gaga & Bradley Cooper', 'year': 2018, 'genre': 'Country Rock', 'album': 'A Star Is Born'},
    {'id': 23, 'title': 'Someone Like You', 'artist': 'Adele', 'year': 2011, 'genre': 'Soul', 'album': '21'},
    {'id': 24, 'title': 'Rolling in the Deep', 'artist': 'Adele', 'year': 2010, 'genre': 'Soul', 'album': '21'},
    {'id': 25, 'title': 'Happy', 'artist': 'Pharrell Williams', 'year': 2013, 'genre': 'Soul', 'album': 'G I R L'},
    {'id': 26, 'title': 'Royals', 'artist': 'Lorde', 'year': 2013, 'genre': 'Art Pop', 'album': 'Pure Heroine'},
    {'id': 27, 'title': 'Thinking Out Loud', 'artist': 'Ed Sheeran', 'year': 2014, 'genre': 'Pop Soul', 'album': 'x'},
    {'id': 28, 'title': 'Hello', 'artist': 'Adele', 'year': 2015, 'genre': 'Soul', 'album': '25'},
    {'id': 29, 'title': 'Sorry', 'artist': 'Justin Bieber', 'year': 2015, 'genre': 'Dancehall Pop', 'album': 'Purpose'},
    {'id': 30, 'title': 'Cant Stop the Feeling', 'artist': 'Justin Timberlake', 'year': 2016, 'genre': 'Disco Pop', 'album': 'Trolls'},
    {'id': 31, 'title': 'Hotline Bling', 'artist': 'Drake', 'year': 2015, 'genre': 'R&B', 'album': 'Views'},
    {'id': 32, 'title': 'Gangnam Style', 'artist': 'PSY', 'year': 2012, 'genre': 'K-Pop', 'album': 'PSY 6'},
    {'id': 33, 'title': 'Call Me Maybe', 'artist': 'Carly Rae Jepsen', 'year': 2011, 'genre': 'Pop', 'album': 'Kiss'},
    {'id': 34, 'title': 'Thrift Shop', 'artist': 'Macklemore & Ryan Lewis', 'year': 2012, 'genre': 'Hip Hop', 'album': 'The Heist'},
    {'id': 35, 'title': 'Get Lucky', 'artist': 'Daft Punk ft. Pharrell', 'year': 2013, 'genre': 'Disco', 'album': 'Random Access Memories'},
    # 2000s Hits
    {'id': 36, 'title': 'Crazy in Love', 'artist': 'Beyoncé ft. Jay-Z', 'year': 2003, 'genre': 'R&B', 'album': 'Dangerously in Love'},
    {'id': 37, 'title': 'Lose Yourself', 'artist': 'Eminem', 'year': 2002, 'genre': 'Hip Hop', 'album': '8 Mile'},
    {'id': 38, 'title': 'Hey Ya!', 'artist': 'OutKast', 'year': 2003, 'genre': 'Funk', 'album': 'Speakerboxxx/The Love Below'},
    {'id': 39, 'title': 'In Da Club', 'artist': '50 Cent', 'year': 2003, 'genre': 'Hip Hop', 'album': 'Get Rich or Die Tryin'},
    {'id': 40, 'title': 'Mr. Brightside', 'artist': 'The Killers', 'year': 2003, 'genre': 'Alternative Rock', 'album': 'Hot Fuss'},
    {'id': 41, 'title': 'Toxic', 'artist': 'Britney Spears', 'year': 2004, 'genre': 'Pop', 'album': 'In the Zone'},
    {'id': 42, 'title': 'Yeah!', 'artist': 'Usher ft. Lil Jon & Ludacris', 'year': 2004, 'genre': 'Crunk', 'album': 'Confessions'},
    {'id': 43, 'title': 'Hips Dont Lie', 'artist': 'Shakira ft. Wyclef Jean', 'year': 2006, 'genre': 'Latin Pop', 'album': 'Oral Fixation Vol. 2'},
    {'id': 44, 'title': 'Umbrella', 'artist': 'Rihanna ft. Jay-Z', 'year': 2007, 'genre': 'Pop R&B', 'album': 'Good Girl Gone Bad'},
    {'id': 45, 'title': 'Poker Face', 'artist': 'Lady Gaga', 'year': 2008, 'genre': 'Dance Pop', 'album': 'The Fame'},
    {'id': 46, 'title': 'I Gotta Feeling', 'artist': 'Black Eyed Peas', 'year': 2009, 'genre': 'Dance Pop', 'album': 'The E.N.D.'},
    {'id': 47, 'title': 'Single Ladies', 'artist': 'Beyoncé', 'year': 2008, 'genre': 'R&B', 'album': 'I Am... Sasha Fierce'},
    {'id': 48, 'title': 'Viva la Vida', 'artist': 'Coldplay', 'year': 2008, 'genre': 'Alternative Rock', 'album': 'Viva la Vida'},
    {'id': 49, 'title': 'Paper Planes', 'artist': 'M.I.A.', 'year': 2007, 'genre': 'Alternative Hip Hop', 'album': 'Kala'},
    {'id': 50, 'title': 'Bleeding Love', 'artist': 'Leona Lewis', 'year': 2007, 'genre': 'Pop', 'album': 'Spirit'},
    # 90s Hits
    {'id': 51, 'title': 'Smells Like Teen Spirit', 'artist': 'Nirvana', 'year': 1991, 'genre': 'Grunge', 'album': 'Nevermind'},
    {'id': 52, 'title': 'Wannabe', 'artist': 'Spice Girls', 'year': 1996, 'genre': 'Pop', 'album': 'Spice'},
    {'id': 53, 'title': 'No Diggity', 'artist': 'Blackstreet', 'year': 1996, 'genre': 'R&B', 'album': 'Another Level'},
    {'id': 54, 'title': 'Creep', 'artist': 'Radiohead', 'year': 1992, 'genre': 'Alternative Rock', 'album': 'Pablo Honey'},
    {'id': 55, 'title': 'Wonderwall', 'artist': 'Oasis', 'year': 1995, 'genre': 'Britpop', 'album': 'Morning Glory'},
    {'id': 56, 'title': 'Killing Me Softly', 'artist': 'Fugees', 'year': 1996, 'genre': 'Hip Hop', 'album': 'The Score'},
    {'id': 57, 'title': 'Baby One More Time', 'artist': 'Britney Spears', 'year': 1998, 'genre': 'Teen Pop', 'album': 'Baby One More Time'},
    {'id': 58, 'title': 'Iris', 'artist': 'Goo Goo Dolls', 'year': 1998, 'genre': 'Alternative Rock', 'album': 'Dizzy Up the Girl'},
    {'id': 59, 'title': 'Smooth', 'artist': 'Santana ft. Rob Thomas', 'year': 1999, 'genre': 'Latin Rock', 'album': 'Supernatural'},
    {'id': 60, 'title': 'Livin La Vida Loca', 'artist': 'Ricky Martin', 'year': 1999, 'genre': 'Latin Pop', 'album': 'Ricky Martin'},
    {'id': 61, 'title': 'Waterfalls', 'artist': 'TLC', 'year': 1994, 'genre': 'R&B', 'album': 'CrazySexyCool'},
    {'id': 62, 'title': 'I Want It That Way', 'artist': 'Backstreet Boys', 'year': 1999, 'genre': 'Pop', 'album': 'Millennium'},
    {'id': 63, 'title': 'Everybody', 'artist': 'Backstreet Boys', 'year': 1997, 'genre': 'Pop', 'album': 'Backstreets Back'},
    {'id': 64, 'title': 'Bitter Sweet Symphony', 'artist': 'The Verve', 'year': 1997, 'genre': 'Britpop', 'album': 'Urban Hymns'},
    {'id': 65, 'title': 'Mmmbop', 'artist': 'Hanson', 'year': 1997, 'genre': 'Pop Rock', 'album': 'Middle of Nowhere'},
    # 80s Classics
    {'id': 66, 'title': 'Billie Jean', 'artist': 'Michael Jackson', 'year': 1982, 'genre': 'Pop', 'album': 'Thriller'},
    {'id': 67, 'title': 'Thriller', 'artist': 'Michael Jackson', 'year': 1982, 'genre': 'Pop', 'album': 'Thriller'},
    {'id': 68, 'title': 'Beat It', 'artist': 'Michael Jackson', 'year': 1982, 'genre': 'Rock', 'album': 'Thriller'},
    {'id': 69, 'title': 'Sweet Child O Mine', 'artist': 'Guns N Roses', 'year': 1987, 'genre': 'Hard Rock', 'album': 'Appetite for Destruction'},
    {'id': 70, 'title': 'Welcome to the Jungle', 'artist': 'Guns N Roses', 'year': 1987, 'genre': 'Hard Rock', 'album': 'Appetite for Destruction'},
    {'id': 71, 'title': 'Livin on a Prayer', 'artist': 'Bon Jovi', 'year': 1986, 'genre': 'Rock', 'album': 'Slippery When Wet'},
    {'id': 72, 'title': 'Take On Me', 'artist': 'a-ha', 'year': 1985, 'genre': 'Synth-pop', 'album': 'Hunting High and Low'},
    {'id': 73, 'title': 'Every Breath You Take', 'artist': 'The Police', 'year': 1983, 'genre': 'Soft Rock', 'album': 'Synchronicity'},
    {'id': 74, 'title': 'Like a Prayer', 'artist': 'Madonna', 'year': 1989, 'genre': 'Pop', 'album': 'Like a Prayer'},
    {'id': 75, 'title': 'Material Girl', 'artist': 'Madonna', 'year': 1984, 'genre': 'Dance Pop', 'album': 'Like a Virgin'},
    {'id': 76, 'title': 'I Wanna Dance with Somebody', 'artist': 'Whitney Houston', 'year': 1987, 'genre': 'Dance Pop', 'album': 'Whitney'},
    {'id': 77, 'title': 'Girls Just Want to Have Fun', 'artist': 'Cyndi Lauper', 'year': 1983, 'genre': 'Pop', 'album': 'Shes So Unusual'},
    {'id': 78, 'title': 'Africa', 'artist': 'Toto', 'year': 1982, 'genre': 'Soft Rock', 'album': 'Toto IV'},
    {'id': 79, 'title': 'Dont Stop Believin', 'artist': 'Journey', 'year': 1981, 'genre': 'Arena Rock', 'album': 'Escape'},
    {'id': 80, 'title': 'Eye of the Tiger', 'artist': 'Survivor', 'year': 1982, 'genre': 'Hard Rock', 'album': 'Eye of the Tiger'},
    # 70s Classics
    {'id': 81, 'title': 'Bohemian Rhapsody', 'artist': 'Queen', 'year': 1975, 'genre': 'Rock', 'album': 'A Night at the Opera'},
    {'id': 82, 'title': 'We Will Rock You', 'artist': 'Queen', 'year': 1977, 'genre': 'Rock', 'album': 'News of the World'},
    {'id': 83, 'title': 'We Are the Champions', 'artist': 'Queen', 'year': 1977, 'genre': 'Rock', 'album': 'News of the World'},
    {'id': 84, 'title': 'Hotel California', 'artist': 'Eagles', 'year': 1977, 'genre': 'Rock', 'album': 'Hotel California'},
    {'id': 85, 'title': 'Stayin Alive', 'artist': 'Bee Gees', 'year': 1977, 'genre': 'Disco', 'album': 'Saturday Night Fever'},
    {'id': 86, 'title': 'Dancing Queen', 'artist': 'ABBA', 'year': 1976, 'genre': 'Disco', 'album': 'Arrival'},
    {'id': 87, 'title': 'Mamma Mia', 'artist': 'ABBA', 'year': 1975, 'genre': 'Pop', 'album': 'ABBA'},
    {'id': 88, 'title': 'Imagine', 'artist': 'John Lennon', 'year': 1971, 'genre': 'Soft Rock', 'album': 'Imagine'},
    {'id': 89, 'title': 'Stairway to Heaven', 'artist': 'Led Zeppelin', 'year': 1971, 'genre': 'Hard Rock', 'album': 'Led Zeppelin IV'},
    {'id': 90, 'title': 'Dream On', 'artist': 'Aerosmith', 'year': 1973, 'genre': 'Hard Rock', 'album': 'Aerosmith'},
    # German Hits
    {'id': 91, 'title': '99 Luftballons', 'artist': 'Nena', 'year': 1983, 'genre': 'New Wave', 'album': 'Nena'},
    {'id': 92, 'title': 'Du Hast', 'artist': 'Rammstein', 'year': 1997, 'genre': 'Industrial Metal', 'album': 'Sehnsucht'},
    {'id': 93, 'title': 'Engel', 'artist': 'Rammstein', 'year': 1997, 'genre': 'Industrial Metal', 'album': 'Sehnsucht'},
    {'id': 94, 'title': 'Durch den Monsun', 'artist': 'Tokio Hotel', 'year': 2005, 'genre': 'Pop Rock', 'album': 'Schrei'},
    {'id': 95, 'title': 'Major Tom', 'artist': 'Peter Schilling', 'year': 1982, 'genre': 'Synth-pop', 'album': 'Error in the System'},
    {'id': 96, 'title': 'Atemlos durch die Nacht', 'artist': 'Helene Fischer', 'year': 2013, 'genre': 'Schlager', 'album': 'Farbenspiel'},
    {'id': 97, 'title': 'An Tagen wie diesen', 'artist': 'Die Toten Hosen', 'year': 2012, 'genre': 'Punk Rock', 'album': 'Ballast der Republik'},
    {'id': 98, 'title': 'Zeig mir den Weg', 'artist': 'Revolverheld', 'year': 2014, 'genre': 'Pop Rock', 'album': 'Immer in Bewegung'},
    {'id': 99, 'title': 'Auf Uns', 'artist': 'Andreas Bourani', 'year': 2014, 'genre': 'Pop', 'album': 'Hey'},
    {'id': 100, 'title': 'Lieblingsmensch', 'artist': 'Namika', 'year': 2015, 'genre': 'Hip Hop', 'album': 'Nador'},
    # Anime/Game Soundtracks
    {'id': 101, 'title': 'Unravel', 'artist': 'TK from Ling tosite sigure', 'year': 2014, 'genre': 'J-Rock', 'album': 'Tokyo Ghoul OST'},
    {'id': 102, 'title': 'Gurenge', 'artist': 'LiSA', 'year': 2019, 'genre': 'J-Rock', 'album': 'Demon Slayer OST'},
    {'id': 103, 'title': 'Again', 'artist': 'YUI', 'year': 2009, 'genre': 'J-Rock', 'album': 'Fullmetal Alchemist OST'},
    {'id': 104, 'title': 'Crossing Field', 'artist': 'LiSA', 'year': 2012, 'genre': 'J-Pop', 'album': 'Sword Art Online OST'},
    {'id': 105, 'title': 'Blue Bird', 'artist': 'Ikimono-gakari', 'year': 2008, 'genre': 'J-Pop', 'album': 'Naruto OST'},
    {'id': 106, 'title': 'Silhouette', 'artist': 'KANA-BOON', 'year': 2014, 'genre': 'J-Rock', 'album': 'Naruto OST'},
    {'id': 107, 'title': 'The Rumbling', 'artist': 'SiM', 'year': 2022, 'genre': 'Metal', 'album': 'Attack on Titan OST'},
    {'id': 108, 'title': 'My War', 'artist': 'Shinsei Kamattechan', 'year': 2020, 'genre': 'J-Rock', 'album': 'Attack on Titan OST'},
    {'id': 109, 'title': 'Guren no Yumiya', 'artist': 'Linked Horizon', 'year': 2013, 'genre': 'J-Rock', 'album': 'Attack on Titan OST'},
    {'id': 110, 'title': 'A Cruel Angels Thesis', 'artist': 'Yoko Takahashi', 'year': 1995, 'genre': 'J-Pop', 'album': 'Neon Genesis Evangelion OST'},
    # K-Pop Hits
    {'id': 111, 'title': 'Dynamite', 'artist': 'BTS', 'year': 2020, 'genre': 'K-Pop', 'album': 'BE'},
    {'id': 112, 'title': 'Butter', 'artist': 'BTS', 'year': 2021, 'genre': 'K-Pop', 'album': 'Butter'},
    {'id': 113, 'title': 'Boy With Luv', 'artist': 'BTS ft. Halsey', 'year': 2019, 'genre': 'K-Pop', 'album': 'Map of the Soul: Persona'},
    {'id': 114, 'title': 'How You Like That', 'artist': 'BLACKPINK', 'year': 2020, 'genre': 'K-Pop', 'album': 'The Album'},
    {'id': 115, 'title': 'DDU-DU DDU-DU', 'artist': 'BLACKPINK', 'year': 2018, 'genre': 'K-Pop', 'album': 'Square Up'},
    {'id': 116, 'title': 'Kill This Love', 'artist': 'BLACKPINK', 'year': 2019, 'genre': 'K-Pop', 'album': 'Kill This Love'},
    {'id': 117, 'title': 'More', 'artist': 'K/DA', 'year': 2020, 'genre': 'K-Pop', 'album': 'ALL OUT'},
    {'id': 118, 'title': 'POP/STARS', 'artist': 'K/DA', 'year': 2018, 'genre': 'K-Pop', 'album': 'League of Legends Worlds'},
    {'id': 119, 'title': 'Fancy', 'artist': 'TWICE', 'year': 2019, 'genre': 'K-Pop', 'album': 'Fancy You'},
    {'id': 120, 'title': 'Psycho', 'artist': 'Red Velvet', 'year': 2019, 'genre': 'K-Pop', 'album': 'The ReVe Festival: Finale'},
    # EDM/Electronic
    {'id': 121, 'title': 'Wake Me Up', 'artist': 'Avicii', 'year': 2013, 'genre': 'EDM', 'album': 'True'},
    {'id': 122, 'title': 'Levels', 'artist': 'Avicii', 'year': 2011, 'genre': 'EDM', 'album': 'Levels'},
    {'id': 123, 'title': 'Titanium', 'artist': 'David Guetta ft. Sia', 'year': 2011, 'genre': 'EDM', 'album': 'Nothing but the Beat'},
    {'id': 124, 'title': 'Lean On', 'artist': 'Major Lazer & DJ Snake', 'year': 2015, 'genre': 'EDM', 'album': 'Peace Is the Mission'},
    {'id': 125, 'title': 'Faded', 'artist': 'Alan Walker', 'year': 2015, 'genre': 'EDM', 'album': 'Different World'},
    {'id': 126, 'title': 'Sandstorm', 'artist': 'Darude', 'year': 1999, 'genre': 'Trance', 'album': 'Before the Storm'},
    {'id': 127, 'title': 'Animals', 'artist': 'Martin Garrix', 'year': 2013, 'genre': 'Big Room House', 'album': 'Animals'},
    {'id': 128, 'title': 'Scary Monsters and Nice Sprites', 'artist': 'Skrillex', 'year': 2010, 'genre': 'Dubstep', 'album': 'Scary Monsters'},
    {'id': 129, 'title': 'Bangarang', 'artist': 'Skrillex', 'year': 2011, 'genre': 'Dubstep', 'album': 'Bangarang'},
    {'id': 130, 'title': 'Strobe', 'artist': 'deadmau5', 'year': 2009, 'genre': 'Progressive House', 'album': 'For Lack of a Better Name'},
    # Hip Hop/Rap
    {'id': 131, 'title': 'Sicko Mode', 'artist': 'Travis Scott', 'year': 2018, 'genre': 'Hip Hop', 'album': 'Astroworld'},
    {'id': 132, 'title': 'Gods Plan', 'artist': 'Drake', 'year': 2018, 'genre': 'Hip Hop', 'album': 'Scorpion'},
    {'id': 133, 'title': 'HUMBLE', 'artist': 'Kendrick Lamar', 'year': 2017, 'genre': 'Hip Hop', 'album': 'DAMN'},
    {'id': 134, 'title': 'Stronger', 'artist': 'Kanye West', 'year': 2007, 'genre': 'Hip Hop', 'album': 'Graduation'},
    {'id': 135, 'title': 'Gold Digger', 'artist': 'Kanye West ft. Jamie Foxx', 'year': 2005, 'genre': 'Hip Hop', 'album': 'Late Registration'},
    {'id': 136, 'title': 'Empire State of Mind', 'artist': 'Jay-Z ft. Alicia Keys', 'year': 2009, 'genre': 'Hip Hop', 'album': 'The Blueprint 3'},
    {'id': 137, 'title': 'Rockstar', 'artist': 'Post Malone ft. 21 Savage', 'year': 2017, 'genre': 'Hip Hop', 'album': 'Beerbongs & Bentleys'},
    {'id': 138, 'title': 'Sunflower', 'artist': 'Post Malone & Swae Lee', 'year': 2018, 'genre': 'Pop Rap', 'album': 'Spider-Man: Into the Spider-Verse'},
    {'id': 139, 'title': 'Lucid Dreams', 'artist': 'Juice WRLD', 'year': 2018, 'genre': 'Emo Rap', 'album': 'Goodbye & Good Riddance'},
    {'id': 140, 'title': 'SAD!', 'artist': 'XXXTENTACION', 'year': 2018, 'genre': 'Emo Rap', 'album': '?'},
    # Rock Classics
    {'id': 141, 'title': 'Back in Black', 'artist': 'AC/DC', 'year': 1980, 'genre': 'Hard Rock', 'album': 'Back in Black'},
    {'id': 142, 'title': 'Highway to Hell', 'artist': 'AC/DC', 'year': 1979, 'genre': 'Hard Rock', 'album': 'Highway to Hell'},
    {'id': 143, 'title': 'Thunderstruck', 'artist': 'AC/DC', 'year': 1990, 'genre': 'Hard Rock', 'album': 'The Razors Edge'},
    {'id': 144, 'title': 'Enter Sandman', 'artist': 'Metallica', 'year': 1991, 'genre': 'Heavy Metal', 'album': 'Metallica'},
    {'id': 145, 'title': 'Nothing Else Matters', 'artist': 'Metallica', 'year': 1991, 'genre': 'Heavy Metal', 'album': 'Metallica'},
    {'id': 146, 'title': 'Smoke on the Water', 'artist': 'Deep Purple', 'year': 1972, 'genre': 'Hard Rock', 'album': 'Machine Head'},
    {'id': 147, 'title': 'Iron Man', 'artist': 'Black Sabbath', 'year': 1970, 'genre': 'Heavy Metal', 'album': 'Paranoid'},
    {'id': 148, 'title': 'Paranoid', 'artist': 'Black Sabbath', 'year': 1970, 'genre': 'Heavy Metal', 'album': 'Paranoid'},
    {'id': 149, 'title': 'Free Bird', 'artist': 'Lynyrd Skynyrd', 'year': 1973, 'genre': 'Southern Rock', 'album': 'Pronounced Leh-nerd Skin-nerd'},
    {'id': 150, 'title': 'Sweet Home Alabama', 'artist': 'Lynyrd Skynyrd', 'year': 1974, 'genre': 'Southern Rock', 'album': 'Second Helping'},
]

# Clip durations for each attempt
CLIP_DURATIONS = [3, 5, 10, 20, 40]  # seconds


async def initialize_songle_tables(db_helpers):
    """Initialize the Songle game tables in the database."""
    try:
        if not db_helpers.db_pool:
            logger.error("Database pool not available for Songle initialization")
            return
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            logger.error("Could not get database connection for Songle")
            return
        
        cursor = conn.cursor()
        try:
            # Table for daily song
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS songle_daily (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    song_id INT NOT NULL,
                    song_data JSON NOT NULL,
                    date DATE NOT NULL,
                    UNIQUE KEY unique_date (date),
                    INDEX idx_date (date)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Table for user games/stats
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS songle_games (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    song_id INT NOT NULL,
                    game_type ENUM('daily', 'premium') DEFAULT 'daily',
                    guesses INT DEFAULT 0,
                    won BOOLEAN DEFAULT FALSE,
                    completed BOOLEAN DEFAULT FALSE,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP NULL,
                    INDEX idx_user_id (user_id),
                    INDEX idx_date (started_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            conn.commit()
            logger.info("Songle tables initialized successfully")
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error initializing Songle tables: {e}", exc_info=True)


async def save_daily_song_to_db(db_helpers, song: dict) -> bool:
    """Save today's daily song to the database."""
    try:
        if not db_helpers.db_pool:
            return False
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        try:
            today = datetime.now(timezone.utc).date()
            song_id = song.get('id')
            song_json = json.dumps(song, ensure_ascii=False)
            
            cursor.execute("""
                INSERT INTO songle_daily (song_id, song_data, date)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    song_id = VALUES(song_id),
                    song_data = VALUES(song_data)
            """, (song_id, song_json, today))
            
            conn.commit()
            logger.info(f"Saved daily song to database: {song.get('title')} by {song.get('artist')}")
            return True
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error saving daily song to database: {e}", exc_info=True)
        return False


async def get_daily_song_from_db(db_helpers) -> Optional[dict]:
    """Get today's daily song from the database."""
    try:
        if not db_helpers.db_pool:
            return None
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return None
        
        cursor = conn.cursor(dictionary=True)
        try:
            today = datetime.now(timezone.utc).date()
            
            cursor.execute("""
                SELECT song_data FROM songle_daily WHERE date = %s
            """, (today,))
            
            row = cursor.fetchone()
            if row and row.get('song_data'):
                song_data = row['song_data']
                if isinstance(song_data, str):
                    return json.loads(song_data)
                return song_data
            
            return None
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error getting daily song from database: {e}", exc_info=True)
        return None


async def record_songle_game(db_helpers, user_id: int, song_id: int, guesses: int, won: bool, game_type: str = 'daily'):
    """Record a completed Songle game to the database."""
    try:
        if not db_helpers.db_pool:
            return False
        
        conn = db_helpers.db_pool.get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO songle_games (user_id, song_id, game_type, guesses, won, completed, completed_at)
                VALUES (%s, %s, %s, %s, %s, TRUE, NOW())
            """, (user_id, song_id, game_type, guesses, won))
            
            conn.commit()
            logger.info(f"Recorded Songle game for user {user_id}: {'won' if won else 'lost'} in {guesses} guesses")
            return True
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error recording Songle game: {e}", exc_info=True)
        return False


class SongleGame:
    """Handles a Songle game instance."""
    
    MAX_GUESSES = 5
    
    def __init__(self, player_id: int, target_song: dict, is_premium: bool = False):
        self.player_id = player_id
        self.target_song = target_song
        self.is_premium = is_premium
        self.guesses: List[dict] = []
        self.is_active = True
        self.won = False
        self.started_at = datetime.now(timezone.utc)
    
    @property
    def attempts(self) -> int:
        return len(self.guesses)
    
    @property
    def remaining_guesses(self) -> int:
        return self.MAX_GUESSES - self.attempts
    
    @property
    def current_clip_duration(self) -> int:
        """Get the clip duration for the current attempt."""
        if self.attempts >= len(CLIP_DURATIONS):
            return CLIP_DURATIONS[-1]
        return CLIP_DURATIONS[self.attempts]
    
    def get_hints_for_attempt(self) -> List[str]:
        """Get hints that should be revealed based on current attempt count."""
        hints = []
        
        # More hints with each attempt
        if self.attempts >= 1:
            hints.append(f"Year: {self.target_song['year']}")
        if self.attempts >= 2:
            hints.append(f"Genre: {self.target_song['genre']}")
        if self.attempts >= 3:
            hints.append(f"Album: {self.target_song['album']}")
        if self.attempts >= 4:
            # First letter of artist
            first_letter = self.target_song['artist'][0]
            hints.append(f"Artist starts with: {first_letter}")
        
        return hints
    
    def check_guess(self, guess: str) -> dict:
        """Check if the guess is correct."""
        if not self.is_active:
            return {'error': 'Game is not active'}
        
        if self.attempts >= self.MAX_GUESSES:
            self.is_active = False
            return {'error': 'No more guesses remaining'}
        
        # Normalize strings for comparison
        guess_lower = guess.lower().strip()
        title_lower = self.target_song['title'].lower()
        artist_lower = self.target_song['artist'].lower()
        
        # Check for matches
        title_match = guess_lower in title_lower or title_lower in guess_lower
        artist_match = guess_lower in artist_lower or artist_lower in guess_lower
        
        # Exact match or close enough
        is_correct = title_match or (guess_lower == title_lower) or (
            # Check if they guessed "artist - title" format
            f"{artist_lower} - {title_lower}" in guess_lower or
            f"{title_lower} - {artist_lower}" in guess_lower or
            f"{title_lower} by {artist_lower}" in guess_lower
        )
        
        result = {
            'guess': guess,
            'is_correct': is_correct,
            'attempt': self.attempts + 1
        }
        
        self.guesses.append(result)
        
        if is_correct:
            self.won = True
            self.is_active = False
        elif self.attempts >= self.MAX_GUESSES:
            self.is_active = False
        
        return result
    
    def create_embed(self, last_result: Optional[dict] = None, embed_color: int = 0x00ff41) -> discord.Embed:
        """Create an embed showing the current game state."""
        embed = discord.Embed(
            title="Songle - Guess the Song",
            color=embed_color
        )
        
        if self.won:
            embed.color = 0x00ff00
            embed.description = f"Correct! You got it in {self.attempts} attempt(s)!"
            embed.add_field(
                name="The Song",
                value=f"**{self.target_song['title']}** by {self.target_song['artist']}",
                inline=False
            )
        elif not self.is_active:
            embed.color = 0xff0000
            embed.description = "Game Over!"
            embed.add_field(
                name="The Song Was",
                value=f"**{self.target_song['title']}** by {self.target_song['artist']}",
                inline=False
            )
        else:
            embed.description = f"🎵 Guess the song using the hints below!\nAttempt {self.attempts + 1}/{self.MAX_GUESSES}"
            
            # Audio preview info
            clip_duration = self.current_clip_duration
            embed.add_field(
                name="🔊 Audio Preview",
                value=f"Click the **Listen** button to hear a {clip_duration}s clip!\nJoin a voice channel first.",
                inline=False
            )
            
            # Show hints
            hints = self.get_hints_for_attempt()
            if hints:
                embed.add_field(
                    name="💡 Hints",
                    value="\n".join(hints),
                    inline=False
                )
            
            embed.add_field(
                name="Remaining Guesses",
                value=str(self.remaining_guesses),
                inline=True
            )
            
            # Show previous guesses
            if self.guesses:
                guess_text = "\n".join([
                    f"{i+1}. {g['guess']} - [X]" 
                    for i, g in enumerate(self.guesses)
                ])
                embed.add_field(
                    name="Previous Guesses",
                    value=guess_text,
                    inline=False
                )
        
        embed.set_footer(text="Use /songle guess <song name> to guess | /songle skip to skip")
        
        return embed


async def get_daily_song(db_helpers=None) -> dict:
    """Get today's daily song challenge. Uses database for persistence."""
    global _daily_song_cache, _last_cache_date
    
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    # Check memory cache first
    if _last_cache_date == today and today in _daily_song_cache:
        logger.debug(f"Returning cached daily song for {today}")
        return _daily_song_cache[today]
    
    # Try to get from database
    if db_helpers:
        song = await get_daily_song_from_db(db_helpers)
        if song:
            logger.info(f"Loaded daily song from database: {song.get('title')}")
            _daily_song_cache = {today: song}
            _last_cache_date = today
            return song
    
    # Generate new daily song if not in database
    # Use the day as seed for reproducible daily song
    random.seed(today)
    song = random.choice(SONG_DATABASE)
    random.seed()  # Reset seed
    
    _daily_song_cache = {today: song}
    _last_cache_date = today
    
    # Save to database for persistence
    if db_helpers:
        await save_daily_song_to_db(db_helpers, song)
    
    logger.info(f"Generated new daily song: {song.get('title')} by {song.get('artist')}")
    return song


def get_random_song() -> dict:
    """Get a random song from the database (for premium users)."""
    song = random.choice(SONG_DATABASE)
    logger.info(f"Selected random song for premium game: {song.get('title')} by {song.get('artist')}")
    return song


def can_play_daily(user_id: int, is_premium: bool = False) -> tuple[bool, str]:
    """Check if user can play today's daily challenge."""
    if is_premium:
        return True, "Premium user - unlimited plays"
    
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    if today not in daily_plays:
        daily_plays[today] = {}
    
    plays = daily_plays[today].get(user_id, 0)
    
    if plays >= 1:
        return False, "You've already played today's Songle challenge. Get Premium for unlimited plays!"
    
    return True, ""


def record_daily_play(user_id: int):
    """Record that a user played the daily challenge."""
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    if today not in daily_plays:
        daily_plays[today] = {}
    
    daily_plays[today][user_id] = daily_plays[today].get(user_id, 0) + 1


def search_songs(query: str) -> List[dict]:
    """Search for songs matching the query."""
    query_lower = query.lower()
    results = []
    
    for song in SONG_DATABASE:
        if (query_lower in song['title'].lower() or 
            query_lower in song['artist'].lower()):
            results.append(song)
    
    return results[:5]  # Limit results


async def get_song_youtube_url(song: dict) -> Optional[str]:
    """
    Get a YouTube URL for a song to play as audio.
    Uses lofi_player's YouTube search functionality.
    
    Args:
        song: Song dictionary with 'title' and 'artist'
    
    Returns:
        YouTube URL or None if not found
    """
    try:
        from modules import lofi_player
        
        song_id = song.get('id')
        
        # Check cache first
        if song_id and song_id in _audio_url_cache:
            return _audio_url_cache[song_id]
        
        # Search YouTube for the song
        url = await lofi_player.search_youtube_song(
            song['title'], 
            song['artist'],
            filter_shorts=True,
            skip_remixes=True
        )
        
        # Cache the result
        if url and song_id:
            _audio_url_cache[song_id] = url
        
        return url
        
    except Exception as e:
        logger.error(f"Error getting YouTube URL for song: {e}")
        return None


async def play_song_clip(
    voice_client,
    song: dict,
    duration_seconds: int = 5,
    guild_id: int = None
) -> bool:
    """
    Play a short clip of a song in a voice channel.
    
    Args:
        voice_client: Discord voice client (connected)
        song: Song dictionary with 'title' and 'artist'
        duration_seconds: How many seconds of the song to play
        guild_id: Guild ID for session tracking
    
    Returns:
        True if clip played successfully, False otherwise
    """
    try:
        from modules import lofi_player
        
        # Check for required dependency
        if not YT_DLP_AVAILABLE:
            logger.error("yt-dlp not installed - run `pip install yt-dlp` to enable audio clips")
            return False
        
        if not voice_client or not voice_client.is_connected():
            logger.warning("Voice client not connected for Songle clip")
            return False
        
        # Get YouTube URL for the song
        url = await get_song_youtube_url(song)
        if not url:
            logger.warning(f"Could not find YouTube URL for: {song.get('title')} by {song.get('artist')}")
            return False
        
        # Stop any current playback
        if voice_client.is_playing():
            voice_client.stop()
            await asyncio.sleep(0.2)
        
        # Play the song clip with robust error handling
        try:
            with yt_dlp.YoutubeDL(lofi_player.YDL_OPTIONS) as ydl:
                info = await asyncio.to_thread(ydl.extract_info, url, download=False)
                if not info:
                    logger.error(f"No info returned for URL: {url}")
                    return False
                audio_url = lofi_player.extract_audio_url(info)
                
                if not audio_url:
                    logger.error("Could not extract audio URL for Songle clip")
                    return False
        except Exception as yt_error:
            # Handle YouTube errors (video unavailable, etc.)
            error_str = str(yt_error).lower()
            if 'unavailable' in error_str or 'private' in error_str or 'removed' in error_str:
                logger.warning(f"Video unavailable for song: {song.get('title')} - {yt_error}")
            else:
                logger.error(f"yt-dlp error for song: {song.get('title')} - {yt_error}")
            return False
        
        # Create audio source
        try:
            audio_source = discord.FFmpegPCMAudio(audio_url, **lofi_player.FFMPEG_OPTIONS)
        except Exception as ffmpeg_error:
            logger.error(f"FFmpeg error creating audio source: {ffmpeg_error}")
            return False
        
        # Play the clip
        try:
            voice_client.play(audio_source)
        except Exception as play_error:
            logger.error(f"Error playing audio: {play_error}")
            return False
        
        # Wait for the clip duration, then stop
        await asyncio.sleep(duration_seconds)
        
        if voice_client.is_playing():
            voice_client.stop()
        
        logger.info(f"Played {duration_seconds}s clip of: {song.get('title')}")
        return True
        
    except Exception as e:
        logger.error(f"Error playing Songle clip: {e}", exc_info=True)
        return False


async def join_and_play_clip(
    interaction,
    song: dict,
    duration_seconds: int = 5
) -> tuple:
    """
    Join the user's voice channel and play a song clip.
    
    Args:
        interaction: Discord interaction (for getting user's voice channel)
        song: Song dictionary with 'title' and 'artist'
        duration_seconds: How many seconds of the song to play
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        from modules import lofi_player
        
        # Check if user is in a voice channel
        if not interaction.user.voice or not interaction.user.voice.channel:
            return (False, "You need to be in a voice channel to hear the clip!")
        
        voice_channel = interaction.user.voice.channel
        
        # Join the voice channel
        voice_client = await lofi_player.join_voice_channel(voice_channel)
        if not voice_client:
            return (False, "Could not join your voice channel. Check my permissions!")
        
        # Play the clip
        success = await play_song_clip(
            voice_client,
            song,
            duration_seconds,
            interaction.guild.id
        )
        
        if success:
            return (True, f"Playing {duration_seconds}s clip...")
        else:
            return (False, "Could not play the audio clip. The song might not be available on YouTube.")
        
    except Exception as e:
        logger.error(f"Error in join_and_play_clip: {e}", exc_info=True)
        return (False, f"Error: {str(e)}")
