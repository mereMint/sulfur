"""
Sulfur Bot - Word Service Module
Fetches random words from external APIs for word games.
"""

import aiohttp
import random
import asyncio
from modules.logger_utils import bot_logger as logger


# External word APIs
RANDOM_WORD_API = "https://random-word-api.herokuapp.com/word"
WORDNIK_API_BASE = "https://api.wordnik.com/v4/words.json/randomWords"


async def fetch_random_words_english(count=1, min_length=5, max_length=5):
    """
    Fetch random English words from external API.
    
    Args:
        count: Number of words to fetch
        min_length: Minimum word length
        max_length: Maximum word length
    
    Returns:
        List of words or empty list on failure
    """
    try:
        # Try random-word-api first
        url = f"{RANDOM_WORD_API}?number={count}&length={max_length}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    words = await response.json()
                    # Filter words by both min and max length (API may not respect min_length)
                    filtered = [w.lower() for w in words if min_length <= len(w) <= max_length and w.isalpha()]
                    logger.info(f"Fetched {len(filtered)} words from random-word-api")
                    return filtered
                else:
                    logger.warning(f"random-word-api returned status {response.status}")
    except asyncio.TimeoutError:
        logger.warning("Timeout fetching words from random-word-api")
    except Exception as e:
        logger.error(f"Error fetching words from random-word-api: {e}")
    
    # Fallback: Use a curated list if API fails
    logger.info("Using fallback word list")
    return get_fallback_english_words(count, min_length, max_length)


async def fetch_random_words_german(count=1, min_length=5, max_length=5):
    """
    Fetch random German words.
    Since German word APIs are limited, we use a curated fallback list.
    
    Args:
        count: Number of words to fetch
        min_length: Minimum word length
        max_length: Maximum word length
    
    Returns:
        List of words
    """
    # German word APIs are limited, so we use fallback
    logger.info("Using German fallback word list")
    return get_fallback_german_words(count, min_length, max_length)


def get_fallback_english_words(count=1, min_length=5, max_length=5):
    """
    Get fallback English words when API is unavailable.
    
    Args:
        count: Number of words to return
        min_length: Minimum word length
        max_length: Maximum word length
    
    Returns:
        List of words
    """
    # Extensive fallback word list for English
    fallback_words = [
        # 5-letter words
        'about', 'above', 'abuse', 'actor', 'acute', 'admit', 'adopt', 'adult', 'after', 'again',
        'agent', 'agree', 'ahead', 'alarm', 'album', 'alert', 'align', 'alike', 'alive', 'allow',
        'alone', 'along', 'alter', 'angel', 'anger', 'angle', 'angry', 'apart', 'apple', 'apply',
        'arena', 'argue', 'arise', 'array', 'aside', 'asset', 'audio', 'avoid', 'awake', 'award',
        'aware', 'badly', 'baker', 'bases', 'basic', 'beach', 'began', 'begin', 'being', 'bench',
        'billy', 'birth', 'black', 'blade', 'blame', 'blank', 'blast', 'bleed', 'blend', 'bless',
        'blind', 'block', 'blood', 'bloom', 'blues', 'board', 'boast', 'boost', 'booth', 'bound',
        'brain', 'brand', 'brave', 'bread', 'break', 'breed', 'brief', 'bring', 'broad', 'broke',
        'brown', 'build', 'built', 'buyer', 'cabin', 'cable', 'calif', 'calm', 'camel', 'candy',
        'canoe', 'cargo', 'carry', 'carve', 'catch', 'cause', 'cedar', 'chain', 'chair', 'chaos',
        'charm', 'chart', 'chase', 'cheap', 'cheat', 'check', 'cheek', 'cheer', 'chess', 'chest',
        'chief', 'child', 'china', 'chips', 'chose', 'civil', 'claim', 'clamp', 'clash', 'class',
        'clean', 'clear', 'click', 'cliff', 'climb', 'cling', 'clock', 'clone', 'close', 'cloth',
        'cloud', 'coach', 'coast', 'coral', 'couch', 'could', 'count', 'coupe', 'court', 'cover',
        'crack', 'craft', 'crane', 'crash', 'crazy', 'cream', 'creek', 'creep', 'crest', 'crime',
        'crisp', 'cross', 'crowd', 'crown', 'crude', 'crush', 'curve', 'cycle', 'daily', 'daisy',
        'dance', 'dated', 'dealt', 'death', 'debut', 'decay', 'decor', 'delay', 'delta', 'dense',
        'depth', 'devil', 'doing', 'donor', 'doubt', 'dough', 'dozen', 'draft', 'drain', 'drama',
        'drank', 'drawn', 'dread', 'dream', 'dress', 'dried', 'drill', 'drink', 'drive', 'drown',
        'drums', 'drunk', 'dying', 'eager', 'eagle', 'early', 'earth', 'eight', 'elite', 'empty',
        'enemy', 'enjoy', 'enter', 'entry', 'equal', 'error', 'erupt', 'event', 'every', 'exact',
        'exist', 'extra', 'faint', 'fairy', 'faith', 'false', 'fancy', 'fatal', 'fault', 'favor',
        'feast', 'fence', 'ferry', 'fever', 'fiber', 'field', 'fiery', 'fifth', 'fifty', 'fight',
        'final', 'first', 'fixed', 'flame', 'flash', 'fleet', 'flesh', 'float', 'flood', 'floor',
        'flour', 'fluid', 'flush', 'focal', 'focus', 'force', 'forge', 'forth', 'forty', 'forum',
        'found', 'frame', 'frank', 'fraud', 'fresh', 'fried', 'front', 'frost', 'fruit', 'fully',
        'funny', 'giant', 'given', 'gland', 'glass', 'globe', 'glory', 'glove', 'going', 'grace',
        'grade', 'grain', 'grand', 'grant', 'grape', 'graph', 'grasp', 'grass', 'grave', 'great',
        'greed', 'green', 'greet', 'grief', 'grill', 'grind', 'gross', 'group', 'grove', 'grown',
        'guard', 'guess', 'guest', 'guide', 'guild', 'guilt', 'habit', 'happy', 'harsh', 'hasty',
        'hatch', 'haunt', 'haven', 'heart', 'heavy', 'hedge', 'hence', 'henry', 'horse', 'hotel',
        'house', 'human', 'humor', 'ideal', 'image', 'imply', 'index', 'inner', 'input', 'irony',
        'issue', 'ivory', 'japan', 'jimmy', 'joint', 'joker', 'jones', 'judge', 'juice', 'juicy',
        'knife', 'knock', 'known', 'label', 'labor', 'laden', 'large', 'laser', 'later', 'laugh',
        'layer', 'lease', 'least', 'leave', 'ledge', 'legal', 'lemon', 'level', 'lever', 'lewis',
        'light', 'limit', 'linen', 'links', 'liver', 'lives', 'local', 'lodge', 'logic', 'loose',
        'lower', 'loyal', 'lucky', 'lunch', 'lying', 'magic', 'major', 'maker', 'maple', 'march',
        'maria', 'marry', 'match', 'mayor', 'meant', 'media', 'melon', 'mercy', 'merge', 'merit',
        'merry', 'metal', 'midst', 'might', 'minor', 'minus', 'mixed', 'model', 'moist', 'money',
        'month', 'moral', 'mount', 'mouse', 'mouth', 'movie', 'music', 'needy', 'nerve', 'never',
        'newly', 'night', 'noble', 'noise', 'north', 'notch', 'noted', 'novel', 'nurse', 'occur',
        'ocean', 'offer', 'often', 'olive', 'onion', 'orbit', 'order', 'organ', 'other', 'ought',
        'outer', 'paint', 'panel', 'panic', 'paper', 'party', 'patch', 'pause', 'peace', 'peach',
        'pearl', 'pedal', 'penny', 'peter', 'phase', 'phone', 'photo', 'piano', 'piece', 'pilot',
        'pitch', 'pizza', 'place', 'plain', 'plane', 'plant', 'plate', 'plaza', 'plead', 'pluck',
        'point', 'poker', 'polar', 'poppy', 'porch', 'pouch', 'pound', 'power', 'press', 'price',
        'pride', 'prime', 'print', 'prior', 'prism', 'prize', 'probe', 'prone', 'proof', 'proud',
        'prove', 'proxy', 'prune', 'pulse', 'pupil', 'purse', 'queen', 'query', 'quest', 'queue',
        'quick', 'quiet', 'quilt', 'quite', 'quota', 'quote', 'radio', 'rainy', 'raise', 'rally',
        'ranch', 'range', 'rapid', 'ratio', 'razor', 'reach', 'react', 'ready', 'realm', 'rebel',
        'refer', 'reign', 'relax', 'relay', 'reply', 'rider', 'ridge', 'rifle', 'right', 'rigid',
        'rinse', 'risen', 'risky', 'rival', 'river', 'roast', 'robin', 'rocky', 'roger', 'roman',
        'rouge', 'rough', 'round', 'route', 'rover', 'royal', 'rugby', 'ruler', 'rumor', 'rural',
        'rusty', 'salty', 'sandy', 'sauce', 'sauna', 'scale', 'scare', 'scarf', 'scene', 'scent',
        'scope', 'score', 'scout', 'scrap', 'screw', 'scrub', 'seize', 'sense', 'serve', 'setup',
        'seven', 'shack', 'shade', 'shaft', 'shake', 'shaky', 'shall', 'shame', 'shape', 'share',
        'shark', 'sharp', 'shave', 'shelf', 'shell', 'shift', 'shine', 'shiny', 'shirt', 'shock',
        'shoot', 'shore', 'short', 'shout', 'shown', 'shred', 'shrug', 'shut', 'siege', 'sight',
        'sigma', 'silky', 'silly', 'since', 'sixth', 'sixty', 'sized', 'skate', 'skill', 'skirt',
        'skull', 'slate', 'slave', 'sleek', 'sleep', 'sleet', 'slice', 'slide', 'slope', 'small',
        'smart', 'smash', 'smell', 'smile', 'smith', 'smoke', 'smoky', 'snack', 'snake', 'sneak',
        'sober', 'solar', 'solid', 'solve', 'sonic', 'sorry', 'sound', 'south', 'space', 'spare',
        'spark', 'speak', 'spear', 'speed', 'spell', 'spend', 'spent', 'spice', 'spicy', 'spike',
        'spill', 'spine', 'spirit', 'split', 'spoke', 'spoon', 'sport', 'spray', 'squad', 'stack',
        'staff', 'stage', 'stain', 'stair', 'stake', 'stale', 'stamp', 'stand', 'stark', 'start',
        'state', 'steak', 'steam', 'steel', 'steep', 'steer', 'stern', 'stick', 'stiff', 'still',
        'sting', 'stock', 'stole', 'stone', 'stood', 'stool', 'stoop', 'store', 'storm', 'story',
        'stout', 'stove', 'strap', 'straw', 'stray', 'strip', 'stuck', 'study', 'stuff', 'stump',
        'stung', 'stunt', 'style', 'sugar', 'suite', 'sunny', 'super', 'surge', 'swamp', 'swear',
        'sweat', 'sweep', 'sweet', 'swept', 'swift', 'swing', 'swirl', 'sword', 'table', 'taken',
        'taste', 'tasty', 'teach', 'tempo', 'tense', 'tenth', 'tepee', 'terms', 'thank', 'theft',
        'their', 'theme', 'there', 'these', 'thick', 'thief', 'thing', 'think', 'third', 'thorn',
        'those', 'three', 'threw', 'throw', 'thumb', 'thump', 'tiger', 'tight', 'timer', 'timid',
        'title', 'toast', 'today', 'token', 'tonic', 'tooth', 'topic', 'torch', 'total', 'touch',
        'tough', 'tower', 'toxic', 'trace', 'track', 'tract', 'trade', 'trail', 'train', 'trait',
        'trash', 'tread', 'treat', 'trend', 'trial', 'tribe', 'trick', 'tried', 'trout', 'truce',
        'truck', 'truly', 'trump', 'trunk', 'trust', 'truth', 'tulip', 'tumor', 'tunic', 'turbo',
        'tweed', 'tweet', 'twice', 'twine', 'twins', 'twist', 'tying', 'uncle', 'under', 'undue',
        'unfed', 'unify', 'union', 'unite', 'unity', 'unlit', 'until', 'unwed', 'upper', 'upset',
        'urban', 'urged', 'usage', 'usher', 'usual', 'utter', 'vague', 'valid', 'value', 'valve',
        'vapor', 'vault', 'venom', 'venue', 'verse', 'video', 'vigor', 'villa', 'vinyl', 'viola',
        'viper', 'viral', 'visit', 'vital', 'vivid', 'vocal', 'vodka', 'vogue', 'voice', 'vouch',
        'vowel', 'wager', 'wagon', 'waist', 'waive', 'waltz', 'waste', 'watch', 'water', 'waver',
        'weary', 'weave', 'wedge', 'weedy', 'weigh', 'weird', 'wheat', 'wheel', 'where', 'which',
        'while', 'whine', 'white', 'whole', 'whose', 'widen', 'widow', 'width', 'wield', 'witch',
        'woman', 'women', 'world', 'worm', 'worry', 'worse', 'worst', 'worth', 'would', 'wound',
        'wrath', 'wreck', 'wrist', 'write', 'wrong', 'wrote', 'yacht', 'yearn', 'yeast', 'yield',
        'young', 'yours', 'youth', 'zebra', 'zesty'
    ]
    
    # Filter by length
    filtered = [w for w in fallback_words if min_length <= len(w) <= max_length]
    
    # Return random selection
    if len(filtered) <= count:
        return filtered
    return random.sample(filtered, count)


def get_fallback_german_words(count=1, min_length=5, max_length=5):
    """
    Get fallback German words.
    
    Args:
        count: Number of words to return
        min_length: Minimum word length
        max_length: Maximum word length
    
    Returns:
        List of words
    """
    # Extensive fallback word list for German
    fallback_words = [
        # 5-letter words
        'apfel', 'bauer', 'brief', 'brust', 'dampf', 'decke', 'draht', 'eisen', 'engel', 'ernte',
        'essen', 'fahne', 'feuer', 'fisch', 'fluss', 'forst', 'frost', 'gabel', 'geist', 'hafen',
        'hagel', 'haken', 'halle', 'hirte', 'hitze', 'honig', 'hotel', 'insel', 'kabel', 'kampf',
        'kanal', 'kanne', 'karte', 'kasse', 'kette', 'klang', 'kleid', 'klein', 'knopf', 'kraft',
        'kranz', 'kreis', 'kreuz', 'krieg', 'krone', 'kugel', 'kunst', 'laden', 'lampe', 'lanze',
        'leder', 'leine', 'licht', 'lippe', 'liste', 'macht', 'maler', 'markt', 'maske', 'masse',
        'mauer', 'menge', 'milch', 'motor', 'musik', 'nabel', 'nacht', 'nadel', 'nagel', 'narbe',
        'nebel', 'orden', 'pfeil', 'pferd', 'pflug', 'platz', 'punkt', 'rasen', 'rasse', 'rauch',
        'recht', 'regal', 'regen', 'reich', 'reihe', 'reise', 'riese', 'sache', 'samen', 'scham',
        'schar', 'schuh', 'segel', 'segen', 'seide', 'seife', 'seite', 'sense', 'sonne', 'sorge',
        'spalt', 'spatz', 'speck', 'spiel', 'sporn', 'staat', 'stadt', 'stahl', 'stamm', 'stand',
        'staub', 'stein', 'stern', 'stich', 'stier', 'stirn', 'stock', 'stoff', 'stolz', 'strom',
        'stube', 'stuck', 'stufe', 'stuhl', 'sturm', 'stutz', 'sucht', 'sumpf', 'tafel', 'tanne',
        'tasse', 'taube', 'teich', 'thron', 'tinte', 'tisch', 'titel', 'trank', 'traum', 'treib',
        'treue', 'trieb', 'tritt', 'tropf', 'trost', 'truhe', 'trupp', 'unruh', 'vater', 'vogel',
        'wache', 'wachs', 'waffe', 'wagen', 'wange', 'wanne', 'watte', 'weber', 'weide', 'weihe',
        'weise', 'welle', 'wesen', 'weste', 'wicht', 'wiege', 'wiese', 'wille', 'wisch', 'witwe',
        'wolke', 'wolle', 'wonne', 'wucht', 'wunde', 'zange', 'zeche', 'zeile', 'ziege', 'zuber',
        'zucht', 'zunge', 'zwang', 'zweck', 'zweig', 'zwerg', 'zwirn', 'abort', 'abweg', 'achse',
        'adler', 'ahorn', 'allee', 'altar', 'amber', 'ambos', 'amsel', 'anker', 'anzug', 'armut',
        'arsch', 'asche', 'assel', 'astat', 'atern', 'athen', 'atlas', 'atoll', 'audit', 'affen',
        'bahre', 'balge', 'balke', 'bande', 'bange', 'barke', 'barte', 'bauch', 'beere', 'beige',
        'beine', 'beleg', 'beruf', 'beule', 'biene', 'biest', 'binde', 'binse', 'birke', 'birne',
        'bisse', 'blase', 'blatt', 'bleib', 'blick', 'blitz', 'bogen', 'bohne', 'boote', 'borke',
        'brand', 'braut', 'breit', 'brett', 'bruch', 'buche', 'buden', 'buhne', 'bunde', 'bunge',
        'bunse', 'burgh', 'burse', 'butter', 'chaos', 'couch', 'damen', 'daune', 'degen', 'deich',
        'diele', 'diebe', 'diele', 'diwan', 'dolch', 'dorne', 'drang', 'dreck', 'droge', 'druck',
        'dunst', 'ebene', 'echse', 'efere', 'eggen', 'eiche', 'eifer', 'eigen', 'eilte', 'eimer',
        'einst', 'elend', 'elfen', 'elite', 'emmer', 'engel', 'ephe', 'erben', 'erlen', 'erpel',
        'esche', 'espan', 'ester', 'etage', 'ethos', 'euter', 'fabel', 'fachs', 'faden', 'fahrt',
        'falke', 'falle', 'falte', 'farbe', 'faser', 'faust', 'feder', 'feige', 'feile', 'felde',
        'felle', 'ferse', 'feste', 'fette', 'fiber', 'ficus', 'filet', 'filme', 'filze', 'finke',
        'firma', 'first', 'flach', 'flagg', 'flaum', 'fleck', 'flehe', 'flieg', 'flink', 'flirt',
        'flora', 'flote', 'flugs', 'fluor', 'fohre', 'folge', 'folie', 'forke', 'forum', 'foyer',
        'frage', 'frass', 'fraud', 'freie', 'fremd', 'frett', 'freud', 'fried', 'fries', 'front',
        'fruhe', 'fuchs', 'fuhre', 'fulle', 'funke', 'furke', 'furst', 'futter', 'ganze', 'garde',
        'garne', 'gasse', 'gauch', 'gaule', 'gebet', 'geben', 'geiße', 'geige', 'genie', 'genre',
        'gerbe', 'gerte', 'geste', 'gilbe', 'gilde', 'gipfe', 'gitter', 'glanz', 'gleis', 'glied',
        'glocke', 'gluck', 'gnade', 'gnome', 'gorge', 'gosse', 'gotte', 'grabe', 'grade', 'gramm',
        'grant', 'graue', 'greif', 'griff', 'grill', 'grimm', 'grind', 'grippe', 'groß', 'grube',
        'gruft', 'grund', 'grune', 'gummi', 'gunst', 'gurke', 'gurte', 'hacke', 'hafen', 'hafte',
        'halde', 'halme', 'halse', 'hamme', 'handel', 'hange', 'hanke', 'harfe', 'harke', 'harst',
        'harte', 'haube', 'hauch', 'haufe', 'haupt', 'haurn', 'haxe', 'hecke', 'hefen', 'hefte',
        'hegen', 'heide', 'heile', 'heine', 'heise', 'heize', 'helle', 'hemd', 'henne', 'herde',
        'hering', 'heros', 'hesse', 'hetze', 'heuer', 'heute', 'hexer', 'hiebe', 'hieße', 'hilfe',
        'hirse', 'hisse', 'hobel', 'hocke', 'hofen', 'hoher', 'hohle', 'holde', 'holle', 'hopfe',
        'horde', 'horne', 'horst', 'hosen', 'hotel', 'hufte', 'hugel', 'hulse', 'hunde', 'hunne',
        'huppe', 'hurde', 'husar', 'huste', 'hutte', 'hydra', 'hyane', 'idiot', 'igele', 'iltis',
        'imame', 'imker', 'immer', 'index', 'india', 'innen', 'innig', 'irden', 'irren', 'islam',
        'jacob', 'jaden', 'jager', 'jahre', 'jeans', 'jeeps', 'jemne', 'jenes', 'joche', 'joker',
        'jolle', 'joule', 'jubel', 'judas', 'juden', 'junge', 'juror', 'kabel', 'kafer', 'kaise',
        'kakao', 'kalbe', 'kalke', 'kamme', 'kanne', 'kante', 'kappe', 'karat', 'karst', 'karus',
        'kasen', 'kaste', 'kasus', 'katze', 'kegel', 'kehle', 'keile', 'keime', 'keine', 'kelle',
        'kelch', 'kelte', 'kerne', 'kerze', 'keuch', 'keule', 'kicht', 'kieme', 'kiese', 'kinde',
        'kinos', 'kippe', 'klaft', 'klamm', 'klapp', 'klare', 'klang', 'klaue', 'klebe', 'klotz',
        'kluge', 'klump', 'knabe', 'knall', 'knauf', 'knech', 'knete', 'knick', 'knopp', 'knorr',
        'knote', 'koben', 'kobra', 'koche', 'kohle', 'kokon', 'kolbe', 'kolik', 'kolme', 'komet',
        'komma', 'konig', 'kopfe', 'korbe', 'korke', 'korne', 'korps', 'krake', 'krams', 'krank',
        'krapp', 'kratz', 'kraut', 'krebs', 'kreme', 'krepp', 'kreta', 'krieg', 'krill', 'krume',
        'kufen', 'kuche', 'kugel', 'kuhle', 'kulte', 'kunde', 'kunft', 'kunst', 'kuppe', 'kurse',
        'kurve', 'kurze', 'kusse', 'kuste', 'labor', 'lache', 'lacke', 'lagen', 'lager', 'laich',
        'laien', 'laken', 'lakme', 'lampe', 'lande', 'lange', 'lappe', 'laren', 'larme', 'larve',
        'laser', 'lasse', 'lasso', 'lauch', 'laude', 'lauer', 'lauge', 'laune', 'lause', 'laute',
        'laval', 'leben', 'leber', 'lecke', 'leere', 'legen', 'lehme', 'lehne', 'leibe', 'leich',
        'leide', 'leier', 'leihe', 'leime', 'leine', 'leise', 'leite', 'lemma', 'lemur', 'lende',
        'lepra', 'lesen', 'letze', 'leuch', 'leute', 'level', 'liane', 'licht', 'liebe', 'liede',
        'liege', 'ligel', 'liger', 'lilie', 'limes', 'linde', 'linie', 'linke', 'linse', 'liste',
        'liter', 'litze', 'lobby', 'loche', 'locke', 'loden', 'lofel', 'loffl', 'logge', 'logik',
        'lohne', 'lokal', 'lombe', 'loren', 'lotus', 'lotze', 'loven', 'luchs', 'lucke', 'luder',
        'lugen', 'lumen', 'lumme', 'lunge', 'lunte', 'lupfe', 'luppe', 'lurch', 'luste', 'luxus',
        'lyrik', 'macke', 'maden', 'magen', 'mager', 'magie', 'magma', 'mahne', 'mahre', 'maien',
        'mails', 'makel', 'maler', 'malta', 'malve', 'mamba', 'manna', 'manor', 'manch', 'mange',
        'manie', 'manko', 'manna', 'manne', 'manor', 'manse', 'maple', 'mappa', 'marke', 'marne',
        'marok', 'marre', 'masen', 'masse', 'maste', 'match', 'mater', 'mathe', 'matte', 'mauel',
        'mauer', 'mauke', 'mause', 'mazen', 'medal', 'media', 'meere', 'mehle', 'meile', 'meine',
        'meise', 'melde', 'memel', 'memen', 'menge', 'mensa', 'mensc', 'merde', 'merit', 'merke',
        'messe', 'metal', 'meter', 'metro', 'mette', 'metze', 'meute', 'miene', 'miete', 'milbe',
        'milde', 'miliz', 'mimik', 'minen', 'minor', 'minus', 'misch', 'mixte', 'modal', 'model',
        'modem', 'moder', 'mogel', 'mohre', 'mokka', 'molch', 'molke', 'molle', 'monat', 'monde',
        'moped', 'mopse', 'moral', 'morda', 'morge', 'morse', 'mosel', 'moser', 'motel', 'motte',
        'motze', 'muhen', 'muhle', 'mulde', 'mulle', 'mumie', 'munde', 'munze', 'musen', 'musik',
        'muste', 'muter', 'mynhe', 'mythe', 'nabel', 'nach', 'nacke', 'nadir', 'nagel', 'nahen',
        'naher', 'nahme', 'nahre', 'naife', 'nasal', 'nasse', 'natur', 'nebel', 'necke', 'neger',
        'nehme', 'neide', 'neige', 'nelle', 'nenne', 'nerfe', 'nerve', 'nesse', 'neste', 'nette',
        'netze', 'neuer', 'neume', 'niche', 'nicht', 'nicke', 'niece', 'niere', 'niete', 'nisse',
        'niste', 'nivel', 'noble', 'nonne', 'norde', 'norme', 'noten', 'notiz', 'novum', 'nusse',
        'nutze', 'nylon', 'nymph', 'oasen', 'obere', 'obhut', 'objek', 'obole', 'ochse', 'odems',
        'odien', 'offen', 'offne', 'ohren', 'oktan', 'oleum', 'olive', 'omega', 'onkel', 'opale',
        'opern', 'opfer', 'opium', 'optik', 'orakel', 'orals', 'orbit', 'orden', 'ordre', 'orgel',
        'orgie', 'orkan', 'ornat', 'ornit', 'orpel', 'oscar', 'otter', 'ovale', 'ozean', 'pacht',
        'packe', 'padre', 'pagen', 'pakte', 'palas', 'palet', 'palme', 'panel', 'panik', 'panne',
        'pansen', 'panth', 'panze', 'papel', 'papie', 'pappa', 'papst', 'paris', 'parse', 'parte',
        'party', 'passt', 'pasta', 'paste', 'paten', 'pater', 'pause', 'pecho', 'pedal', 'pegel',
        'peile', 'peine', 'pelle', 'pelte', 'pelze', 'penne', 'pense', 'perle', 'peron', 'perse',
        'perso', 'pesto', 'pfade', 'pfahl', 'pfalz', 'pfand', 'pfann', 'pfaue', 'pfeif', 'pfeil',
        'pferd', 'pfiff', 'pfing', 'pflug', 'pfote', 'pfuhl', 'phase', 'piano', 'picks', 'pieps',
        'piert', 'pieta', 'piezo', 'pilge', 'pille', 'pilot', 'pilze', 'pinne', 'pinse', 'piole',
        'pique', 'pirat', 'piste', 'pixel', 'pizza', 'place', 'plaid', 'plane', 'plank', 'plans',
        'plant', 'plast', 'platt', 'platz', 'plena', 'plexe', 'plock', 'plots', 'plump', 'pocke',
        'poden', 'poets', 'poise', 'pokal', 'poker', 'polar', 'polen', 'polio', 'polis', 'polka',
        'polle', 'polot', 'polst', 'pomme', 'poren', 'porta', 'poser', 'posse', 'poste', 'poten',
        'potte', 'power', 'prall', 'prams', 'prane', 'praxi', 'preis', 'press', 'priem', 'prima',
        'prinz', 'prise', 'probe', 'profi', 'prost', 'protz', 'proxy', 'prunk', 'psalm', 'pseud',
        'pudel', 'puder', 'puffs', 'pulla', 'pulle', 'pulli', 'pulpe', 'pulse', 'pumps', 'punkt',
        'punte', 'puppe', 'puren', 'purge', 'purka', 'putte', 'putze', 'quack', 'quade', 'quaek',
        'quake', 'quant', 'quark', 'quart', 'quarz', 'quass', 'quelle', 'quere', 'quese', 'queue',
        'quick', 'quirl', 'quitt', 'quole', 'quota', 'quote', 'raabe', 'raben', 'rache', 'radar',
        'radau', 'rader', 'radio', 'radle', 'radon', 'raffe', 'ragee', 'ragen', 'rahme', 'rakau',
        'rakel', 'raket', 'ralle', 'ramme', 'rampe', 'ramsc', 'ranch', 'rande', 'range', 'rangs',
        'ranke', 'ranke', 'rappe', 'rarst', 'rasch', 'rasen', 'rasse', 'raste', 'raten', 'raume',
        'raune', 'raupe', 'rausc', 'razia', 'reale', 'rebbe', 'recke', 'recte', 'reden', 'reder',
        'reede', 'regal', 'regel', 'regen', 'reger', 'regie', 'regle', 'regne', 'rehab', 'rehen',
        'reich', 'reide', 'reihe', 'reime', 'reine', 'reise', 'reite', 'rekla', 'relais', 'relie',
        'remix', 'renke', 'renne', 'rente', 'repro', 'reset', 'reste', 'resum', 'retro', 'rette',
        'reuse', 'reute', 'rexer', 'rezen', 'rhein', 'rhyth', 'riale', 'ribbe', 'riche', 'ricke',
        'riefe', 'riege', 'riege', 'rieme', 'riese', 'riete', 'riffe', 'rille', 'rinde', 'ringe',
        'rinne', 'rippe', 'risse', 'riten', 'ritte', 'ritze', 'rival', 'river', 'robin', 'robot',
        'rodeo', 'roden', 'roger', 'rogue', 'rohre', 'rokko', 'rolle', 'roman', 'romer', 'rondo',
        'ronne', 'ronte', 'roque', 'rosel', 'rosen', 'roste', 'roten', 'roter', 'rotor', 'rotte',
        'route', 'rowdy', 'royal', 'rubel', 'rubin', 'rucke', 'rudel', 'ruder', 'rufen', 'ruger',
        'ruhen', 'ruhig', 'ruhme', 'ruhre', 'ruine', 'rulle', 'rumme', 'rumpe', 'runde', 'runen',
        'rupfe', 'russe', 'rusze', 'ruten', 'rutil', 'saale', 'saale', 'sabel', 'sache', 'sacke',
        'sacks', 'safar', 'safte', 'sagen', 'sager', 'saide', 'saiga', 'saite', 'salat', 'salbe',
        'salig', 'salin', 'salme', 'salon', 'salop', 'salpe', 'salto', 'salut', 'salve', 'salze',
        'samba', 'samen', 'samig', 'samst', 'sanat', 'sande', 'sanft', 'sanga', 'sanka', 'sanse',
        'santo', 'sanus', 'saone', 'sapfe', 'sappe', 'sarge', 'saris', 'satan', 'saten', 'satin',
        'satir', 'satte', 'satze', 'sauce', 'sauen', 'sauer', 'sauge', 'saule', 'sauna', 'saure',
        'sause', 'saxe', 'schal', 'schar', 'schau', 'schef', 'scheu', 'schib', 'schif', 'schmu',
        'schon', 'schor', 'schub', 'schuh', 'schul', 'schur', 'schuss', 'scoop', 'score', 'scout',
        'seele', 'segel', 'segen', 'sehen', 'seher', 'sehne', 'seide', 'seien', 'seife', 'seige',
        'seile', 'seine', 'seism', 'seite', 'sekre', 'sekte', 'selbig', 'selbe', 'selek', 'selen',
        'selig', 'sella', 'selle', 'selma', 'selts', 'semel', 'semit', 'senat', 'sende', 'senfe',
        'senge', 'senke', 'senna', 'sense', 'sepie', 'serbe', 'serie', 'serum', 'serve', 'servo',
        'sesse', 'setze', 'seuch', 'seufe', 'sexte', 'sexus', 'sezen', 'shalt', 'shame', 'shape',
        'share', 'shark', 'sharp', 'shave', 'shear', 'sheep', 'sheet', 'shelf', 'shell', 'shift',
        'shine', 'shirt', 'shive', 'shock', 'shoot', 'shore', 'short', 'shout', 'shown', 'shrimp'
    ]
    
    # Filter by length
    filtered = [w for w in fallback_words if min_length <= len(w) <= max_length]
    
    # Return random selection
    if len(filtered) <= count:
        return filtered
    return random.sample(filtered, count)


async def get_random_word(language='en', min_length=5, max_length=5):
    """
    Get a single random word.
    
    Args:
        language: 'en' or 'de'
        min_length: Minimum word length
        max_length: Maximum word length
    
    Returns:
        Single word string
    """
    if language == 'de':
        words = await fetch_random_words_german(1, min_length, max_length)
    else:
        words = await fetch_random_words_english(1, min_length, max_length)
    
    return words[0] if words else None


async def get_random_words(count=1, language='en', min_length=5, max_length=5):
    """
    Get multiple random words.
    
    Args:
        count: Number of words to fetch
        language: 'en' or 'de'
        min_length: Minimum word length
        max_length: Maximum word length
    
    Returns:
        List of words
    """
    if language == 'de':
        return await fetch_random_words_german(count, min_length, max_length)
    else:
        return await fetch_random_words_english(count, min_length, max_length)
