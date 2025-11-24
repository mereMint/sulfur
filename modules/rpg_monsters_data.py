"""
RPG System - Monster Data
Contains base monster data for database seeding.
This file stores hardcoded monster data that is used to populate the database on first run.

The generation function is called by rpg_system.py during database initialization.
"""


def get_base_monsters_data():
    """
    Returns the base monster data for database seeding.
    Called during database initialization to populate rpg_monsters table.
    """
    return [
    # ===== OVERWORLD MONSTERS (Level 1-10) =====
    # Tier 1: Beginners (Level 1-2)
    {'name': 'Schleimling', 'world': 'overworld', 'level': 1, 'health': 30, 'strength': 3, 'defense': 2, 'speed': 5, 'xp_reward': 15, 'gold_reward': 10, 'abilities': ['poison_spit'], 'loot_table': {'Schleim': 0.8, 'Kleiner Gifttrank': 0.3}},
    {'name': 'Ratte', 'world': 'overworld', 'level': 1, 'health': 25, 'strength': 2, 'defense': 1, 'speed': 8, 'xp_reward': 12, 'gold_reward': 8, 'abilities': ['savage_bite'], 'loot_table': {'Rattenschwanz': 0.7, 'Krankheit (Quest)': 0.1}},
    {'name': 'Kleiner Goblin', 'world': 'overworld', 'level': 1, 'health': 28, 'strength': 4, 'defense': 2, 'speed': 6, 'xp_reward': 14, 'gold_reward': 12, 'abilities': ['critical_strike'], 'loot_table': {'Goblin-Ohr': 0.6, 'Rostige Münze': 0.4}},
    
    {'name': 'Goblin', 'world': 'overworld', 'level': 2, 'health': 45, 'strength': 5, 'defense': 3, 'speed': 6, 'xp_reward': 25, 'gold_reward': 20, 'abilities': ['critical_strike'], 'loot_table': {'Goblin-Ohr': 0.75, 'Kleiner Beutel': 0.3}},
    {'name': 'Riesenkäfer', 'world': 'overworld', 'level': 2, 'health': 40, 'strength': 4, 'defense': 5, 'speed': 4, 'xp_reward': 22, 'gold_reward': 18, 'abilities': ['armor_up'], 'loot_table': {'Käferpanzer': 0.7, 'Chitin': 0.5}},
    {'name': 'Wildschwein', 'world': 'overworld', 'level': 2, 'health': 50, 'strength': 6, 'defense': 3, 'speed': 7, 'xp_reward': 24, 'gold_reward': 22, 'abilities': ['savage_bite', 'battle_roar'], 'loot_table': {'Schweineleder': 0.8, 'Wildfleisch': 0.9, 'Stoßzahn': 0.4}},
    
    # Tier 2: Adventurers (Level 3-5)
    {'name': 'Wilder Wolf', 'world': 'overworld', 'level': 3, 'health': 60, 'strength': 7, 'defense': 4, 'speed': 10, 'xp_reward': 35, 'gold_reward': 25, 'abilities': ['savage_bite', 'crippling_strike'], 'loot_table': {'Wolfszahn': 0.75, 'Wolfsfell': 0.6, 'Wolfsherz (Quest)': 0.2}},
    {'name': 'Banditen-Schütze', 'world': 'overworld', 'level': 3, 'health': 55, 'strength': 8, 'defense': 3, 'speed': 9, 'xp_reward': 38, 'gold_reward': 30, 'abilities': ['hunters_focus', 'expose_weakness'], 'loot_table': {'Gestohlene Münzen': 0.9, 'Bogen': 0.3, 'Kopfgeld-Marke': 0.5}},
    {'name': 'Giftige Spinne', 'world': 'overworld', 'level': 3, 'health': 50, 'strength': 6, 'defense': 3, 'speed': 11, 'xp_reward': 32, 'gold_reward': 20, 'abilities': ['poison_spit', 'enfeeble'], 'loot_table': {'Spinnengift': 0.8, 'Spinnenseide': 0.7, 'Spinnenauge': 0.4}},
    
    {'name': 'Skelett-Krieger', 'world': 'overworld', 'level': 4, 'health': 70, 'strength': 9, 'defense': 6, 'speed': 7, 'xp_reward': 50, 'gold_reward': 35, 'abilities': ['armor_up', 'stunning_blow'], 'loot_table': {'Knochen': 0.9, 'Alter Schild': 0.4, 'Verfluchter Schädel': 0.2}},
    {'name': 'Zombie', 'world': 'overworld', 'level': 4, 'health': 80, 'strength': 10, 'defense': 5, 'speed': 4, 'xp_reward': 48, 'gold_reward': 30, 'abilities': ['life_drain', 'poison_spit'], 'loot_table': {'Verfaultes Fleisch': 0.95, 'Zombie-Gehirn': 0.3, 'Seuche (Quest)': 0.15}},
    {'name': 'Waldschamane', 'world': 'overworld', 'level': 4, 'health': 65, 'strength': 11, 'defense': 4, 'speed': 8, 'xp_reward': 52, 'gold_reward': 38, 'abilities': ['dark_curse', 'regeneration'], 'loot_table': {'Kräuter': 0.8, 'Schamanenstab': 0.25, 'Zauberperle': 0.4}},
    
    {'name': 'Ork-Schläger', 'world': 'overworld', 'level': 5, 'health': 90, 'strength': 12, 'defense': 8, 'speed': 6, 'xp_reward': 65, 'gold_reward': 50, 'abilities': ['battle_roar', 'critical_strike', 'stunning_blow'], 'loot_table': {'Ork-Zahn': 0.7, 'Schwere Rüstung': 0.3, 'Kriegstrophäe': 0.4}},
    {'name': 'Harpyie', 'world': 'overworld', 'level': 5, 'health': 75, 'strength': 10, 'defense': 5, 'speed': 14, 'xp_reward': 62, 'gold_reward': 45, 'abilities': ['shadow_step', 'terrifying_roar'], 'loot_table': {'Harpyienfeder': 0.85, 'Kralle': 0.6, 'Luftessenz': 0.3}},
    {'name': 'Steingolem', 'world': 'overworld', 'level': 5, 'health': 110, 'strength': 13, 'defense': 15, 'speed': 3, 'xp_reward': 68, 'gold_reward': 48, 'abilities': ['stone_skin', 'armor_up'], 'loot_table': {'Steinstück': 0.9, 'Magischer Kern': 0.25, 'Edelstein': 0.4}},
    
    # Tier 3: Veterans (Level 6-8)
    {'name': 'Dunkler Magier', 'world': 'overworld', 'level': 6, 'health': 80, 'strength': 15, 'defense': 5, 'speed': 9, 'xp_reward': 80, 'gold_reward': 60, 'abilities': ['shadow_cloak', 'life_drain', 'dark_curse'], 'loot_table': {'Dunkle Essenz': 0.7, 'Zauberbuch': 0.35, 'Mystischer Stab': 0.25}},
    {'name': 'Werwolf', 'world': 'overworld', 'level': 6, 'health': 95, 'strength': 14, 'defense': 7, 'speed': 13, 'xp_reward': 85, 'gold_reward': 55, 'abilities': ['berserk_fury', 'savage_bite', 'regeneration'], 'loot_table': {'Wolfszahn': 0.8, 'Mondfell': 0.5, 'Fluch-Token (Quest)': 0.2}},
    {'name': 'Sumpfschreiter', 'world': 'overworld', 'level': 6, 'health': 85, 'strength': 12, 'defense': 6, 'speed': 10, 'xp_reward': 78, 'gold_reward': 58, 'abilities': ['poison_spit', 'crippling_strike', 'enfeeble'], 'loot_table': {'Giftige Schlange': 0.7, 'Sumpfkraut': 0.8, 'Seltene Pflanze': 0.3}},
    
    {'name': 'Troll', 'world': 'overworld', 'level': 7, 'health': 120, 'strength': 16, 'defense': 12, 'speed': 4, 'xp_reward': 100, 'gold_reward': 75, 'abilities': ['regeneration', 'armor_up', 'last_stand'], 'loot_table': {'Trollblut': 0.65, 'Trollhaut': 0.5, 'Regenerationsstein': 0.3}},
    {'name': 'Banshee', 'world': 'overworld', 'level': 7, 'health': 90, 'strength': 17, 'defense': 6, 'speed': 12, 'xp_reward': 95, 'gold_reward': 70, 'abilities': ['terrifying_roar', 'mind_blast', 'dark_curse'], 'loot_table': {'Geistessenz': 0.7, 'Verlorene Seele': 0.4, 'Mystisches Tuch': 0.35}},
    {'name': 'Minotaurus', 'world': 'overworld', 'level': 7, 'health': 130, 'strength': 18, 'defense': 10, 'speed': 7, 'xp_reward': 105, 'gold_reward': 80, 'abilities': ['critical_strike', 'battle_roar', 'stunning_blow'], 'loot_table': {'Minotaurus-Horn': 0.6, 'Starkes Leder': 0.7, 'Labyrinth-Schlüssel': 0.25}},
    
    {'name': 'Geist', 'world': 'overworld', 'level': 8, 'health': 100, 'strength': 18, 'defense': 8, 'speed': 12, 'xp_reward': 120, 'gold_reward': 85, 'abilities': ['shadow_cloak', 'life_drain', 'shadow_step'], 'loot_table': {'Ektoplasma': 0.75, 'Geisterkette': 0.4, 'Verfluchtes Medaillon': 0.3}},
    {'name': 'Elementar (Erde)', 'world': 'overworld', 'level': 8, 'health': 140, 'strength': 16, 'defense': 18, 'speed': 5, 'xp_reward': 115, 'gold_reward': 90, 'abilities': ['stone_skin', 'armor_up', 'stunning_blow'], 'loot_table': {'Erdkristall': 0.7, 'Elementarstein': 0.5, 'Geokern': 0.35}},
    {'name': 'Riesenspinne', 'world': 'overworld', 'level': 8, 'health': 105, 'strength': 15, 'defense': 8, 'speed': 14, 'xp_reward': 118, 'gold_reward': 88, 'abilities': ['poison_spit', 'enfeeble', 'expose_weakness'], 'loot_table': {'Riesengift': 0.8, 'Robuste Seide': 0.7, 'Spinnenbein': 0.5}},
    
    # Tier 4: Elite (Level 9-10)
    {'name': 'Oger', 'world': 'overworld', 'level': 9, 'health': 150, 'strength': 20, 'defense': 15, 'speed': 5, 'xp_reward': 150, 'gold_reward': 100, 'abilities': ['battle_roar', 'critical_strike', 'regeneration', 'last_stand'], 'loot_table': {'Oger-Fleisch': 0.8, 'Großer Knochen': 0.7, 'Kraftamulett': 0.3}},
    {'name': 'Vampir', 'world': 'overworld', 'level': 9, 'health': 130, 'strength': 19, 'defense': 10, 'speed': 15, 'xp_reward': 145, 'gold_reward': 110, 'abilities': ['vampiric_aura', 'life_drain', 'shadow_cloak'], 'loot_table': {'Vampirzahn': 0.65, 'Blutphiole': 0.5, 'Mondring': 0.35}},
    {'name': 'Chimäre', 'world': 'overworld', 'level': 9, 'health': 145, 'strength': 21, 'defense': 12, 'speed': 11, 'xp_reward': 155, 'gold_reward': 105, 'abilities': ['fire_breath', 'poison_spit', 'critical_strike'], 'loot_table': {'Chimären-Schuppe': 0.7, 'Dreiköpfige Klaue': 0.4, 'Hybridessenz': 0.3}},
    
    {'name': 'Drache (Jung)', 'world': 'overworld', 'level': 10, 'health': 180, 'strength': 25, 'defense': 18, 'speed': 10, 'xp_reward': 200, 'gold_reward': 150, 'abilities': ['fire_breath', 'critical_strike', 'time_warp'], 'loot_table': {'Drachenschuppe': 0.8, 'Drachenzahn': 0.6, 'Kleine Drachenessenz': 0.4, 'Drachenherzstück (Quest)': 0.15}},
    {'name': 'Eisgolem', 'world': 'overworld', 'level': 10, 'health': 170, 'strength': 22, 'defense': 20, 'speed': 6, 'xp_reward': 190, 'gold_reward': 140, 'abilities': ['frost_nova', 'stone_skin', 'armor_up'], 'loot_table': {'Ewiges Eis': 0.75, 'Frostkristall': 0.6, 'Golem-Kern': 0.35}},
    {'name': 'Dunkler Ritter', 'world': 'overworld', 'level': 10, 'health': 165, 'strength': 24, 'defense': 22, 'speed': 9, 'xp_reward': 195, 'gold_reward': 145, 'abilities': ['dark_curse', 'armor_up', 'critical_strike', 'last_stand'], 'loot_table': {'Dunkle Rüstung': 0.5, 'Verfluchte Klinge': 0.35, 'Ritterorden-Abzeichen': 0.4}},
    
    # ===== UNDERWORLD MONSTERS (Level 11-25) =====
    # Tier 1: Underworld Initiates (Level 11-13)
    {'name': 'Imp', 'world': 'underworld', 'level': 11, 'health': 190, 'strength': 26, 'defense': 16, 'speed': 13, 'xp_reward': 250, 'gold_reward': 180, 'abilities': ['fire_breath', 'terrifying_roar'], 'loot_table': {'Imp-Horn': 0.7, 'Schwefelkristall': 0.6, 'Kleine Teufelsflamme': 0.4}},
    {'name': 'Höllenhündchen', 'world': 'underworld', 'level': 11, 'health': 185, 'strength': 27, 'defense': 15, 'speed': 16, 'xp_reward': 240, 'gold_reward': 175, 'abilities': ['fire_breath', 'savage_bite'], 'loot_table': {'Glühendes Fell': 0.75, 'Feuerzahn': 0.5, 'Ascheklaue': 0.4}},
    
    {'name': 'Dämon', 'world': 'underworld', 'level': 12, 'health': 220, 'strength': 30, 'defense': 20, 'speed': 12, 'xp_reward': 300, 'gold_reward': 200, 'abilities': ['fire_breath', 'life_drain', 'battle_roar'], 'loot_table': {'Dämonenhaut': 0.7, 'Höllenfeuer-Essenz': 0.5, 'Seelenedelstein': 0.3}},
    {'name': 'Knochenkönig', 'world': 'underworld', 'level': 12, 'health': 200, 'strength': 28, 'defense': 24, 'speed': 8, 'xp_reward': 290, 'gold_reward': 195, 'abilities': ['armor_up', 'dark_curse', 'regeneration'], 'loot_table': {'Uralter Knochen': 0.8, 'Knochenkrone': 0.35, 'Nekromantie-Siegel': 0.3}},
    {'name': 'Lavaelementar', 'world': 'underworld', 'level': 12, 'health': 210, 'strength': 29, 'defense': 18, 'speed': 10, 'xp_reward': 295, 'gold_reward': 190, 'abilities': ['fire_breath', 'berserk_fury'], 'loot_table': {'Lavagestein': 0.8, 'Feuerkern': 0.55, 'Obsidian': 0.45}},
    
    {'name': 'Schattendämon', 'world': 'underworld', 'level': 13, 'health': 215, 'strength': 31, 'defense': 19, 'speed': 14, 'xp_reward': 320, 'gold_reward': 210, 'abilities': ['shadow_cloak', 'dark_curse', 'vampiric_aura'], 'loot_table': {'Schattenherz': 0.65, 'Dunkle Materie': 0.5, 'Void-Kristall': 0.35}},
    {'name': 'Feuerdrache', 'world': 'underworld', 'level': 13, 'health': 240, 'strength': 33, 'defense': 22, 'speed': 11, 'xp_reward': 330, 'gold_reward': 220, 'abilities': ['fire_breath', 'critical_strike', 'time_warp'], 'loot_table': {'Feuerschuppe': 0.75, 'Drachenklaue': 0.6, 'Flammenherz': 0.4}},
    
    # Tier 2: Underworld Veterans (Level 14-17)
    {'name': 'Höllenhund', 'world': 'underworld', 'level': 14, 'health': 250, 'strength': 35, 'defense': 22, 'speed': 15, 'xp_reward': 400, 'gold_reward': 250, 'abilities': ['fire_breath', 'critical_strike', 'berserk_fury'], 'loot_table': {'Höllenpelz': 0.7, 'Glühende Klaue': 0.55, 'Inferno-Zahn': 0.4}},
    {'name': 'Dämonenfürst', 'world': 'underworld', 'level': 14, 'health': 260, 'strength': 36, 'defense': 24, 'speed': 13, 'xp_reward': 410, 'gold_reward': 260, 'abilities': ['fire_breath', 'dark_curse', 'battle_roar', 'last_stand'], 'loot_table': {'Fürstenkrone': 0.45, 'Dämonenflügel': 0.5, 'Höllische Essenz': 0.6}},
    
    {'name': 'Liche', 'world': 'underworld', 'level': 15, 'health': 230, 'strength': 38, 'defense': 20, 'speed': 10, 'xp_reward': 450, 'gold_reward': 280, 'abilities': ['dark_curse', 'death_mark', 'life_drain', 'regeneration'], 'loot_table': {'Phylakterium': 0.3, 'Unheilige Essenz': 0.65, 'Nekromantie-Buch': 0.4}},
    {'name': 'Blutgolem', 'world': 'underworld', 'level': 15, 'health': 280, 'strength': 37, 'defense': 26, 'speed': 7, 'xp_reward': 440, 'gold_reward': 270, 'abilities': ['regeneration', 'vampiric_aura', 'stone_skin'], 'loot_table': {'Geronnenes Blut': 0.8, 'Fleischklumpen': 0.7, 'Lebenskern': 0.35}},
    
    {'name': 'Schattenbestie', 'world': 'underworld', 'level': 16, 'health': 280, 'strength': 40, 'defense': 25, 'speed': 14, 'xp_reward': 500, 'gold_reward': 300, 'abilities': ['shadow_cloak', 'poison_spit', 'life_drain', 'shadow_step'], 'loot_table': {'Schattenfell': 0.7, 'Void-Kristall': 0.5, 'Schattenklaue': 0.45}},
    {'name': 'Höllentitan', 'world': 'underworld', 'level': 16, 'health': 320, 'strength': 42, 'defense': 30, 'speed': 6, 'xp_reward': 510, 'gold_reward': 310, 'abilities': ['critical_strike', 'stone_skin', 'battle_roar', 'last_stand'], 'loot_table': {'Titanenherz': 0.5, 'Titanstahl': 0.45, 'Urgestein': 0.6}},
    
    {'name': 'Succubus', 'world': 'underworld', 'level': 17, 'health': 270, 'strength': 41, 'defense': 23, 'speed': 16, 'xp_reward': 550, 'gold_reward': 330, 'abilities': ['life_drain', 'mind_blast', 'dark_curse', 'vampiric_aura'], 'loot_table': {'Verführerische Essenz': 0.6, 'Dämonisches Parfüm': 0.4, 'Seelenperle': 0.45}},
    {'name': 'Knochendrache', 'world': 'underworld', 'level': 17, 'health': 300, 'strength': 43, 'defense': 28, 'speed': 12, 'xp_reward': 560, 'gold_reward': 340, 'abilities': ['dark_curse', 'critical_strike', 'armor_up', 'terrifying_roar'], 'loot_table': {'Drachenknochen': 0.75, 'Untotes Herz': 0.5, 'Nekrotische Schuppe': 0.55}},
    
    # Tier 3: Underworld Elite (Level 18-21)
    {'name': 'Todesritter', 'world': 'underworld', 'level': 18, 'health': 320, 'strength': 45, 'defense': 30, 'speed': 11, 'xp_reward': 650, 'gold_reward': 400, 'abilities': ['frost_nova', 'armor_up', 'critical_strike', 'death_mark'], 'loot_table': {'Verfluchte Platte': 0.55, 'Frostschwert': 0.4, 'Todesritter-Siegel': 0.35}},
    {'name': 'Höllengolem', 'world': 'underworld', 'level': 18, 'health': 350, 'strength': 44, 'defense': 35, 'speed': 5, 'xp_reward': 640, 'gold_reward': 390, 'abilities': ['fire_breath', 'stone_skin', 'regeneration', 'last_stand'], 'loot_table': {'Magmakern': 0.6, 'Verstärkte Platte': 0.5, 'Unzerstörbarer Stein': 0.4}},
    
    {'name': 'Schattenlord', 'world': 'underworld', 'level': 19, 'health': 330, 'strength': 47, 'defense': 28, 'speed': 15, 'xp_reward': 700, 'gold_reward': 430, 'abilities': ['shadow_cloak', 'dark_curse', 'death_mark', 'vampiric_aura', 'shadow_step'], 'loot_table': {'Schattenthron-Fragment': 0.45, 'Herrschaftsring': 0.35, 'Dunkle Macht': 0.5}},
    {'name': 'Dämonenlord', 'world': 'underworld', 'level': 19, 'health': 340, 'strength': 48, 'defense': 32, 'speed': 13, 'xp_reward': 710, 'gold_reward': 440, 'abilities': ['fire_breath', 'battle_roar', 'critical_strike', 'berserk_fury', 'last_stand'], 'loot_table': {'Dämonenkrone': 0.4, 'Höllische Waffe': 0.45, 'Ewige Flamme': 0.5}},
    
    {'name': 'Drache (Erwachsen)', 'world': 'underworld', 'level': 20, 'health': 400, 'strength': 50, 'defense': 35, 'speed': 13, 'xp_reward': 800, 'gold_reward': 500, 'abilities': ['fire_breath', 'lightning_strike', 'critical_strike', 'regeneration', 'time_warp'], 'loot_table': {'Drachenschuppe': 0.8, 'Drachenklaue': 0.65, 'Drachenherz': 0.4, 'Drachenessenz': 0.3, 'Legendäre Schuppe (Quest)': 0.12}},
    {'name': 'Abgrundwächter', 'world': 'underworld', 'level': 20, 'health': 380, 'strength': 49, 'defense': 38, 'speed': 9, 'xp_reward': 790, 'gold_reward': 490, 'abilities': ['stone_skin', 'stunning_blow', 'armor_up', 'thorn_armor', 'last_stand'], 'loot_table': {'Wächterpanzer': 0.6, 'Abgrundstein': 0.55, 'Ewiger Wachposten': 0.35}},
    
    {'name': 'Erzlich', 'world': 'underworld', 'level': 21, 'health': 360, 'strength': 52, 'defense': 30, 'speed': 11, 'xp_reward': 850, 'gold_reward': 520, 'abilities': ['death_mark', 'dark_curse', 'life_drain', 'regeneration', 'arcane_barrier'], 'loot_table': {'Großes Phylakterium': 0.35, 'Meisterwerk der Nekromantie': 0.3, 'Seelensammler': 0.45}},
    {'name': 'Höllenfürst', 'world': 'underworld', 'level': 21, 'health': 370, 'strength': 53, 'defense': 33, 'speed': 14, 'xp_reward': 860, 'gold_reward': 530, 'abilities': ['fire_breath', 'berserk_fury', 'critical_strike', 'battle_roar', 'vampiric_aura'], 'loot_table': {'Fürstenzepter': 0.4, 'Höllenkrone': 0.35, 'Infernalische Essenz': 0.55}},
    
    # Tier 4: Underworld Champions (Level 22-25)
    {'name': 'Ur-Dämon', 'world': 'underworld', 'level': 22, 'health': 410, 'strength': 55, 'defense': 36, 'speed': 13, 'xp_reward': 950, 'gold_reward': 600, 'abilities': ['fire_breath', 'dark_curse', 'death_mark', 'critical_strike', 'berserk_fury', 'last_stand'], 'loot_table': {'Ur-Essenz': 0.5, 'Dämonisches Artefakt': 0.35, 'Herz des Ur-Dämons (Quest)': 0.15}},
    {'name': 'Schattentitan', 'world': 'underworld', 'level': 22, 'health': 430, 'strength': 54, 'defense': 40, 'speed': 10, 'xp_reward': 940, 'gold_reward': 590, 'abilities': ['shadow_cloak', 'stone_skin', 'vampiric_aura', 'thorn_armor', 'last_stand'], 'loot_table': {'Titanischer Schatten': 0.45, 'Void-Titankern': 0.4, 'Schattenplatte': 0.5}},
    
    {'name': 'Blutdrache', 'world': 'underworld', 'level': 23, 'health': 450, 'strength': 58, 'defense': 38, 'speed': 14, 'xp_reward': 1050, 'gold_reward': 650, 'abilities': ['savage_bite', 'vampiric_aura', 'fire_breath', 'regeneration', 'critical_strike'], 'loot_table': {'Blutkristalschuppe': 0.65, 'Blutessenz': 0.6, 'Drachenblutstropfen (Quest)': 0.2}},
    {'name': 'Chaosritter', 'world': 'underworld', 'level': 23, 'health': 440, 'strength': 57, 'defense': 42, 'speed': 12, 'xp_reward': 1040, 'gold_reward': 640, 'abilities': ['dark_curse', 'critical_strike', 'armor_up', 'berserk_fury', 'last_stand'], 'loot_table': {'Chaosrüstung': 0.5, 'Verfluchtes Schwert': 0.45, 'Chaossiegel': 0.4}},
    
    {'name': 'Erzdämon', 'world': 'underworld', 'level': 24, 'health': 460, 'strength': 60, 'defense': 40, 'speed': 13, 'xp_reward': 1150, 'gold_reward': 700, 'abilities': ['fire_breath', 'death_mark', 'critical_strike', 'berserk_fury', 'vampiric_aura', 'last_stand'], 'loot_table': {'Erz-Essenz': 0.55, 'Dämonenkrone': 0.4, 'Höllenamulett': 0.45}},
    {'name': 'Todesengel', 'world': 'underworld', 'level': 24, 'health': 420, 'strength': 59, 'defense': 35, 'speed': 18, 'xp_reward': 1140, 'gold_reward': 690, 'abilities': ['death_mark', 'shadow_step', 'expose_weakness', 'dark_curse', 'hunters_focus'], 'loot_table': {'Engelschwinge (Dunkel)': 0.5, 'Todeshauch': 0.45, 'Seelensense': 0.4}},
    
    {'name': 'Drache (Alt)', 'world': 'underworld', 'level': 25, 'health': 500, 'strength': 65, 'defense': 45, 'speed': 15, 'xp_reward': 1300, 'gold_reward': 800, 'abilities': ['fire_breath', 'lightning_strike', 'frost_nova', 'critical_strike', 'regeneration', 'time_warp', 'last_stand'], 'loot_table': {'Uralte Drachenschuppe': 0.7, 'Drachenherz': 0.5, 'Große Drachenessenz': 0.4, 'Zeitkristall (Quest)': 0.15}},
    {'name': 'Höllenmonarch', 'world': 'underworld', 'level': 25, 'health': 480, 'strength': 63, 'defense': 43, 'speed': 14, 'xp_reward': 1280, 'gold_reward': 780, 'abilities': ['fire_breath', 'berserk_fury', 'battle_roar', 'critical_strike', 'arcane_barrier', 'last_stand'], 'loot_table': {'Monarchenkrone': 0.45, 'Zepter der Hölle': 0.4, 'Königssiegel': 0.35, 'Höllenstein (Quest)': 0.18}},
    
    # ===== SHADOWLANDS MONSTERS (Level 26-40) =====
    {'name': 'Schattenschleicher', 'world': 'shadowlands', 'level': 26, 'health': 520, 'strength': 66, 'defense': 42, 'speed': 20, 'xp_reward': 1400, 'gold_reward': 850, 'abilities': ['shadow_step', 'shadow_cloak', 'expose_weakness', 'savage_bite'], 'loot_table': {'Reiner Schatten': 0.7, 'Schattenklaue': 0.6, 'Finstere Essenz': 0.5}},
    {'name': 'Void-Bestie', 'world': 'shadowlands', 'level': 28, 'health': 560, 'strength': 70, 'defense': 45, 'speed': 18, 'xp_reward': 1600, 'gold_reward': 950, 'abilities': ['dark_curse', 'life_drain', 'vampiric_aura', 'berserk_fury'], 'loot_table': {'Void-Essenz': 0.75, 'Nichtsstein': 0.55, 'Abgrundherz': 0.45}},
    {'name': 'Schattentitan', 'world': 'shadowlands', 'level': 30, 'health': 600, 'strength': 75, 'defense': 55, 'speed': 12, 'xp_reward': 1850, 'gold_reward': 1100, 'abilities': ['stone_skin', 'shadow_cloak', 'critical_strike', 'thorn_armor', 'last_stand'], 'loot_table': {'Titanenschatten': 0.65, 'Schattentitanit': 0.5, 'Kolossales Herz': 0.4}},
    {'name': 'Schattendrache', 'world': 'shadowlands', 'level': 32, 'health': 650, 'strength': 80, 'defense': 58, 'speed': 16, 'xp_reward': 2100, 'gold_reward': 1250, 'abilities': ['shadow_cloak', 'fire_breath', 'critical_strike', 'time_warp', 'regeneration'], 'loot_table': {'Schattendrachenschuppe': 0.7, 'Schwarze Essenz': 0.6, 'Schattendrachenherz (Quest)': 0.2}},
    {'name': 'Void-Lord', 'world': 'shadowlands', 'level': 35, 'health': 700, 'strength': 88, 'defense': 62, 'speed': 17, 'xp_reward': 2500, 'gold_reward': 1500, 'abilities': ['death_mark', 'dark_curse', 'vampiric_aura', 'arcane_barrier', 'critical_strike', 'last_stand'], 'loot_table': {'Void-Lordkrone': 0.5, 'Nichtsessenz': 0.65, 'Leere-Artefakt (Quest)': 0.15}},
    {'name': 'Uralter Schatten', 'world': 'shadowlands', 'level': 38, 'health': 750, 'strength': 95, 'defense': 65, 'speed': 19, 'xp_reward': 2900, 'gold_reward': 1750, 'abilities': ['shadow_cloak', 'death_mark', 'shadow_step', 'dark_curse', 'vampiric_aura', 'petrifying_gaze'], 'loot_table': {'Urzeitschatten': 0.6, 'Ewige Finsternis': 0.5, 'Schattenherz (Quest)': 0.18}},
    {'name': 'Schattenkönig', 'world': 'shadowlands', 'level': 40, 'health': 850, 'strength': 105, 'defense': 75, 'speed': 20, 'xp_reward': 3500, 'gold_reward': 2100, 'abilities': ['shadow_cloak', 'death_mark', 'critical_strike', 'arcane_barrier', 'berserk_fury', 'time_warp', 'last_stand'], 'loot_table': {'Schattenkrone': 0.45, 'Königsschatten': 0.55, 'Schattenthron-Fragment (Quest)': 0.12}},
    
    # ===== FROZEN WASTES MONSTERS (Level 41-60) =====
    {'name': 'Frostwolf', 'world': 'frozen_wastes', 'level': 41, 'health': 900, 'strength': 108, 'defense': 70, 'speed': 25, 'xp_reward': 3800, 'gold_reward': 2250, 'abilities': ['frost_nova', 'savage_bite', 'crippling_strike'], 'loot_table': {'Frostwolfpelz': 0.75, 'Eisiger Zahn': 0.65, 'Winteressenz': 0.5}},
    {'name': 'Eisgolem', 'world': 'frozen_wastes', 'level': 43, 'health': 950, 'strength': 112, 'defense': 90, 'speed': 10, 'xp_reward': 4200, 'gold_reward': 2500, 'abilities': ['frost_nova', 'stone_skin', 'armor_up', 'thorn_armor'], 'loot_table': {'Ewiges Eis': 0.8, 'Frostkern': 0.6, 'Eisgolem-Herz': 0.45}},
    {'name': 'Frostdrache', 'world': 'frozen_wastes', 'level': 45, 'health': 1100, 'strength': 120, 'defense': 85, 'speed': 22, 'xp_reward': 4800, 'gold_reward': 2850, 'abilities': ['frost_nova', 'critical_strike', 'time_warp', 'regeneration', 'petrifying_gaze'], 'loot_table': {'Frostdrachenschuppe': 0.7, 'Eisherz': 0.55, 'Gefrorene Essenz (Quest)': 0.2}},
    {'name': 'Frosttitan', 'world': 'frozen_wastes', 'level': 48, 'health': 1200, 'strength': 130, 'defense': 100, 'speed': 15, 'xp_reward': 5500, 'gold_reward': 3300, 'abilities': ['frost_nova', 'stone_skin', 'critical_strike', 'stunning_blow', 'last_stand'], 'loot_table': {'Titaneneis': 0.65, 'Frosttitanit': 0.55, 'Winterkrone': 0.4}},
    {'name': 'Eiskönig', 'world': 'frozen_wastes', 'level': 50, 'health': 1300, 'strength': 140, 'defense': 95, 'speed': 18, 'xp_reward': 6200, 'gold_reward': 3750, 'abilities': ['frost_nova', 'death_mark', 'critical_strike', 'arcane_barrier', 'time_warp', 'last_stand'], 'loot_table': {'Eiskrone': 0.5, 'Winterszepter': 0.45, 'Gefrorener Thron (Quest)': 0.15}},
    {'name': 'Eiswyrm', 'world': 'frozen_wastes', 'level': 53, 'health': 1400, 'strength': 150, 'defense': 105, 'speed': 20, 'xp_reward': 7000, 'gold_reward': 4250, 'abilities': ['frost_nova', 'critical_strike', 'regeneration', 'vampiric_aura', 'petrifying_gaze'], 'loot_table': {'Eiswyrmschuppe': 0.7, 'Frostherz': 0.6, 'Ewiger Winter (Quest)': 0.18}},
    {'name': 'Frostphönix', 'world': 'frozen_wastes', 'level': 56, 'health': 1250, 'strength': 155, 'defense': 90, 'speed': 30, 'xp_reward': 7800, 'gold_reward': 4750, 'abilities': ['frost_nova', 'regeneration', 'time_warp', 'divine_blessing', 'shadow_step'], 'loot_table': {'Phönixfeder (Eis)': 0.65, 'Wiedergeburtsasche': 0.5, 'Frostessenz': 0.55}},
    {'name': 'Winterdrache (Uralter)', 'world': 'frozen_wastes', 'level': 60, 'health': 1600, 'strength': 170, 'defense': 120, 'speed': 25, 'xp_reward': 9500, 'gold_reward': 5800, 'abilities': ['frost_nova', 'critical_strike', 'time_warp', 'regeneration', 'arcane_barrier', 'petrifying_gaze', 'last_stand'], 'loot_table': {'Uralte Eisschuppe': 0.7, 'Drachenherz (Frost)': 0.5, 'Ewigkeitseis (Quest)': 0.12}},
    
    # ===== VOID MONSTERS (Level 61-100) =====
    {'name': 'Void-Wanderer', 'world': 'void', 'level': 61, 'health': 1700, 'strength': 175, 'defense': 115, 'speed': 28, 'xp_reward': 10500, 'gold_reward': 6400, 'abilities': ['death_mark', 'dark_curse', 'shadow_step', 'vampiric_aura'], 'loot_table': {'Void-Fragment': 0.75, 'Nichtsessenz': 0.7, 'Leerenkristall': 0.6}},
    {'name': 'Chaos-Bestie', 'world': 'void', 'level': 65, 'health': 1850, 'strength': 185, 'defense': 125, 'speed': 26, 'xp_reward': 12000, 'gold_reward': 7300, 'abilities': ['berserk_fury', 'critical_strike', 'dark_curse', 'death_mark', 'last_stand'], 'loot_table': {'Chaosherz': 0.7, 'Unordnung-Essenz': 0.65, 'Wahnsinnssplitter': 0.55}},
    {'name': 'Void-Titan', 'world': 'void', 'level': 70, 'health': 2200, 'strength': 200, 'defense': 150, 'speed': 20, 'xp_reward': 14500, 'gold_reward': 8900, 'abilities': ['stone_skin', 'critical_strike', 'arcane_barrier', 'thorn_armor', 'death_mark', 'last_stand'], 'loot_table': {'Void-Titankern': 0.65, 'Nichtsmetal': 0.6, 'Kolossale Leere': 0.5}},
    {'name': 'Ur-Drache', 'world': 'void', 'level': 75, 'health': 2500, 'strength': 220, 'defense': 160, 'speed': 30, 'xp_reward': 17500, 'gold_reward': 10800, 'abilities': ['fire_breath', 'frost_nova', 'lightning_strike', 'critical_strike', 'time_warp', 'regeneration', 'last_stand'], 'loot_table': {'Ur-Schuppe': 0.7, 'Ur-Drachenherz': 0.5, 'Zeitlose Essenz (Quest)': 0.15}},
    {'name': 'Void-Gott', 'world': 'void', 'level': 80, 'health': 2800, 'strength': 245, 'defense': 175, 'speed': 32, 'xp_reward': 21000, 'gold_reward': 13000, 'abilities': ['death_mark', 'dark_curse', 'arcane_barrier', 'petrifying_gaze', 'time_warp', 'vampiric_aura', 'last_stand'], 'loot_table': {'Göttliche Leere': 0.6, 'Gottessplitter': 0.45, 'Void-Krone (Quest)': 0.12}},
    {'name': 'Chaos-Drache', 'world': 'void', 'level': 85, 'health': 3000, 'strength': 265, 'defense': 185, 'speed': 33, 'xp_reward': 25000, 'gold_reward': 15500, 'abilities': ['fire_breath', 'dark_curse', 'berserk_fury', 'critical_strike', 'time_warp', 'regeneration', 'last_stand'], 'loot_table': {'Chaosschuppe': 0.65, 'Chaosdrachenherz': 0.5, 'Unendliche Kraft (Quest)': 0.15}},
    {'name': 'Ewigkeit', 'world': 'void', 'level': 90, 'health': 3500, 'strength': 290, 'defense': 200, 'speed': 35, 'xp_reward': 30000, 'gold_reward': 18500, 'abilities': ['time_warp', 'arcane_barrier', 'petrifying_gaze', 'death_mark', 'regeneration', 'divine_blessing', 'last_stand'], 'loot_table': {'Ewigkeitsfragment': 0.55, 'Zeitkristall': 0.5, 'Unendlichkeitsstein (Quest)': 0.1}},
    {'name': 'Urschöpfer', 'world': 'void', 'level': 95, 'health': 4000, 'strength': 320, 'defense': 220, 'speed': 38, 'xp_reward': 37000, 'gold_reward': 23000, 'abilities': ['fire_breath', 'frost_nova', 'lightning_strike', 'death_mark', 'arcane_barrier', 'time_warp', 'critical_strike', 'last_stand'], 'loot_table': {'Schöpfungsessenz': 0.5, 'Urmaterie': 0.45, 'Schöpferkrone (Quest)': 0.08}},
    {'name': 'Das Ende', 'world': 'void', 'level': 100, 'health': 5000, 'strength': 350, 'defense': 250, 'speed': 40, 'xp_reward': 50000, 'gold_reward': 30000, 'abilities': ['death_mark', 'dark_curse', 'petrifying_gaze', 'arcane_barrier', 'time_warp', 'berserk_fury', 'critical_strike', 'vampiric_aura', 'last_stand'], 'loot_table': {'Ende-Fragment': 0.4, 'Ultimative Leere': 0.35, 'Herz des Endes (Quest)': 0.05, 'Göttliches Artefakt': 0.25}},
]


# Log when module is imported (for debugging)
if __name__ != '__main__':
    try:
        from modules.logger_utils import bot_logger as logger
        logger.debug("RPG Monsters Data module loaded - monster data ready")
    except:
        pass  # Logger not available yet
