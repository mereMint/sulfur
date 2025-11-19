"""
Sulfur Bot - Detective/Murder Mystery Game Module
AI-generated murder mystery cases with suspect investigation.
"""

import discord
import random
import json
import hashlib
import asyncio
import mysql.connector
from datetime import datetime, timezone
from modules.logger_utils import bot_logger as logger


class MurderCase:
    """Represents a murder mystery case."""
    
    def __init__(self, case_data: dict):
        self.case_id = case_data.get('case_id', None)  # Database ID
        self.case_title = case_data.get('title', 'Mysterious Murder')
        self.case_description = case_data.get('description', '')
        self.location = case_data.get('location', '')
        self.victim = case_data.get('victim', '')
        self.suspects = case_data.get('suspects', [])  # List of suspect dicts
        self.murderer_index = case_data.get('murderer_index', 0)
        self.evidence = case_data.get('evidence', [])
        self.hints = case_data.get('hints', [])  # Hints/codes pointing to the murderer
        self.encrypted_messages = case_data.get('encrypted_messages', [])  # Puzzle elements
        self.difficulty = case_data.get('difficulty', 1)  # Difficulty level
    
    def get_suspect(self, index: int):
        """Get suspect details by index."""
        if 0 <= index < len(self.suspects):
            return self.suspects[index]
        return None
    
    def is_correct_murderer(self, index: int) -> bool:
        """Check if the selected suspect is the murderer."""
        return index == self.murderer_index


# --- Cipher and Puzzle Utilities ---

def caesar_cipher(text: str, shift: int = 3) -> str:
    """Encode text using Caesar cipher."""
    result = []
    for char in text:
        if char.isalpha():
            ascii_offset = 65 if char.isupper() else 97
            result.append(chr((ord(char) - ascii_offset + shift) % 26 + ascii_offset))
        else:
            result.append(char)
    return ''.join(result)


def reverse_cipher(text: str) -> str:
    """Reverse the text."""
    return text[::-1]


def atbash_cipher(text: str) -> str:
    """Encode using Atbash cipher (A=Z, B=Y, etc.)."""
    result = []
    for char in text:
        if char.isalpha():
            if char.isupper():
                result.append(chr(90 - (ord(char) - 65)))
            else:
                result.append(chr(122 - (ord(char) - 97)))
        else:
            result.append(char)
    return ''.join(result)


def create_puzzle_hint(hint_text: str, difficulty: int) -> dict:
    """Create encrypted puzzle from hint based on difficulty."""
    if difficulty <= 1:
        return {'type': 'plaintext', 'text': hint_text, 'cipher': None}
    
    ciphers = ['caesar', 'reverse', 'atbash'] if difficulty >= 3 else ['caesar', 'reverse']
    cipher_type = random.choice(ciphers)
    
    if cipher_type == 'caesar':
        shift = random.randint(1, 25)
        encrypted = caesar_cipher(hint_text, shift)
        hint = f"Caesar +{shift}" if difficulty <= 3 else "Verschiebungschiffre"
    elif cipher_type == 'reverse':
        encrypted = reverse_cipher(hint_text)
        hint = "Rückwärts" if difficulty <= 3 else "Spiegelschrift"
    else:
        encrypted = atbash_cipher(hint_text)
        hint = "Atbash" if difficulty <= 3 else "Alphabet-Code"
    
    return {
        'type': 'cipher',
        'encrypted': encrypted,
        'cipher': cipher_type,
        'hint': hint if difficulty <= 4 else None
    }


async def generate_murder_case(api_helpers, config: dict, gemini_api_key: str, openai_api_key: str):
    """
    Generate murder mystery case using FAST modular AI generation.
    Components generated separately and in parallel where possible.
    Much faster and more reliable than monolithic JSON generation.
    
    Returns:
        MurderCase object
    """
    import time
    import re
    
    logger.info("Starting FAST modular case generation")
    start_time = time.time()
    
    try:
        # Get model to use
        provider = config.get('api', {}).get('provider', 'gemini')
        if provider == 'gemini':
            model = config.get('api', {}).get('gemini', {}).get('utility_model', 'gemini-2.5-flash')
        else:
            model = config.get('api', {}).get('openai', {}).get('utility_model', 'gpt-4o-mini')
        
        # Random theme for variety
        themes = [
            "corporate intrigue", "family drama", "historical mystery", "art world scandal",
            "scientific research", "political conspiracy", "celebrity lifestyle",
            "underground crime", "high society", "academic rivalry", "tech startup",
            "restaurant secrets", "theater production", "sports competition",
            "museum heist", "literary world", "fashion industry", "music industry"
        ]
        theme = random.choice(themes)
        
        # Step 1: Generate title (fast, simple)
        title_prompt = f"Generiere einen spannenden deutschen Titel für einen Kriminalfall im Thema '{theme}'. Nur der Titel, nichts anderes. Format: 'Der Fall ...'"
        title, _ = await api_helpers.get_ai_response_with_model(
            title_prompt, model, config, gemini_api_key, openai_api_key, temperature=1.0
        )
        title = (title or "Der Fall des mysteriösen Todes").strip()[:100]
        logger.info(f"Generated title: {title}")
        
        # Step 2: Generate core components in parallel
        logger.info("Generating description, location, and victim in parallel...")
        
        desc_prompt = f"Beschreibe eine Mordszene für den Fall '{title}' (Thema: {theme}). 2-3 Sätze, lebendig und detailliert. Nur die Beschreibung, keine Titel."
        loc_prompt = f"Nenne einen spezifischen, interessanten Tatort für '{title}'. Ein Satz. Nur der Ort, z.B. 'Luxus-Penthouse am Hafen'"
        victim_prompt = f"Beschreibe das Opfer für '{title}': Name, Alter, Beruf. Ein Satz. Format: 'Name, Alter, Beruf'"
        
        results = await asyncio.gather(
            api_helpers.get_ai_response_with_model(desc_prompt, model, config, gemini_api_key, openai_api_key, temperature=0.9),
            api_helpers.get_ai_response_with_model(loc_prompt, model, config, gemini_api_key, openai_api_key, temperature=0.9),
            api_helpers.get_ai_response_with_model(victim_prompt, model, config, gemini_api_key, openai_api_key, temperature=0.9)
        )
        
        description = (results[0][0] or "Ein mysteriöser Mord.").strip()[:500]
        location = (results[1][0] or "Unbekannter Ort").strip()[:200]
        victim = (results[2][0] or "Unbekanntes Opfer").strip()[:200]
        
        logger.info(f"Generated core: desc={len(description)} chars, loc={len(location)} chars, victim={len(victim)} chars")
        
        # Step 3: Generate 4 suspects IN PARALLEL (huge time saver!)
        logger.info("Generating 4 suspects in parallel...")
        murderer_index = random.randint(0, 3)
        
        suspect_prompts = []
        for i in range(4):
            is_murderer = (i == murderer_index)
            role = "DER MÖRDER" if is_murderer else "UNSCHULDIG"
            prompt = f"""Generiere einen Verdächtigen für '{title}' ({role}).
JSON Format (NUR das JSON-Objekt):
{{
  "name": "Name",
  "occupation": "Beruf",
  "alibi": "Alibi-Behauptung",
  "motive": "Motiv für Mord",
  "suspicious_details": "Verdächtige Details"
}}
Mache {'diesen Verdächtigen schuldig' if is_murderer else 'diesen Verdächtigen unschuldig'}. Variiere Berufe und Hintergründe."""
            suspect_prompts.append(
                api_helpers.get_ai_response_with_model(prompt, model, config, gemini_api_key, openai_api_key, temperature=0.8)
            )
        
        suspect_results = await asyncio.gather(*suspect_prompts)
        
        # Parse suspects
        suspects = []
        for i, (result, _) in enumerate(suspect_results):
            if result:
                try:
                    # Clean and parse JSON
                    json_match = re.search(r'\{.*\}', result, re.DOTALL)
                    if json_match:
                        suspect = json.loads(json_match.group())
                        suspects.append(suspect)
                    else:
                        # Fallback suspect
                        suspects.append({
                            'name': f'Verdächtiger {i+1}',
                            'occupation': 'Unbekannt',
                            'alibi': 'Keine Angaben',
                            'motive': 'Unbekannt',
                            'suspicious_details': 'Keine Details'
                        })
                except:
                    # Fallback suspect
                    suspects.append({
                        'name': f'Verdächtiger {i+1}',
                        'occupation': 'Unbekannt',
                        'alibi': 'Keine Angaben',
                        'motive': 'Unbekannt',
                        'suspicious_details': 'Keine Details'
                    })
            else:
                # Fallback suspect
                suspects.append({
                    'name': f'Verdächtiger {i+1}',
                    'occupation': 'Unbekannt',
                    'alibi': 'Keine Angaben',
                    'motive': 'Unbekannt',
                    'suspicious_details': 'Keine Details'
                })
        
        logger.info(f"Generated {len(suspects)} suspects")
        
        # Step 4: Generate evidence
        logger.info("Generating evidence...")
        evidence_prompt = f"Liste 3-4 Beweisstücke für '{title}'. Format: emoji + kurze Beschreibung pro Zeile. Beispiel:\n🔪 Blutiges Messer\n📱 Gesendete SMS\n👣 Fußabdrücke"
        evidence_result, _ = await api_helpers.get_ai_response_with_model(
            evidence_prompt, model, config, gemini_api_key, openai_api_key, temperature=0.7
        )
        
        evidence = []
        if evidence_result:
            for line in evidence_result.strip().split('\n'):
                line = line.strip()
                if line and len(line) > 3:
                    evidence.append(line[:200])
        
        if len(evidence) < 3:
            evidence = [
                '🔍 Spuren am Tatort',
                '📋 Verdächtige Notiz',
                '💀 Forensische Beweise'
            ]
        
        logger.info(f"Generated {len(evidence)} evidence items")
        
        # Step 5: Generate hints pointing to murderer
        logger.info("Generating hints...")
        murderer_name = suspects[murderer_index].get('name', 'der Täter')
        hints_prompt = f"Gib 2-3 subtile Hinweise die auf '{murderer_name}' als Mörder deuten. Format: emoji + kurze Aussage pro Zeile."
        hints_result, _ = await api_helpers.get_ai_response_with_model(
            hints_prompt, model, config, gemini_api_key, openai_api_key, temperature=0.7
        )
        
        hints = []
        if hints_result:
            for line in hints_result.strip().split('\n'):
                line = line.strip()
                if line and len(line) > 3:
                    hints.append(line[:200])
        
        if len(hints) < 2:
            hints = [
                f'🔎 Wichtiger Hinweis auf {murderer_name}',
                f'💡 Verdächtiges Detail über {murderer_name}'
            ]
        
        logger.info(f"Generated {len(hints)} hints")
        
        # Build final case data
        case_data = {
            'title': title,
            'description': description,
            'location': location,
            'victim': victim,
            'suspects': suspects,
            'murderer_index': murderer_index,
            'evidence': evidence,
            'hints': hints,
            'encrypted_messages': []  # Added for puzzle support
        }
        
        elapsed = time.time() - start_time
        logger.info(f"Case generation completed in {elapsed:.1f}s (vs 120s+ old method)")
        
        return MurderCase(case_data)
        
    except Exception as e:
        logger.error(f"Error in fast case generation: {e}", exc_info=True)
        logger.info("Falling back to pre-defined case")
        return create_fallback_case()


def create_fallback_case():
    """
    Create a fallback case if AI generation fails.
    Rotates through multiple pre-defined cases to ensure variety.
    """
    import time
    
    # Multiple fallback cases to rotate through
    fallback_cases = [
        {
            'title': 'Der Fall der verschwundenen Erbin',
            'description': 'Eine junge Erbin wurde in ihrem Penthouse tot aufgefunden. Ein seltsamer Geruch von Mandeln liegt in der Luft.',
            'location': 'Luxus-Penthouse am Hafen',
            'victim': 'Sophie Winterstein, 28, Millionenerbin',
            'suspects': [
                {
                    'name': 'Marcus Berger',
                    'occupation': 'Vermögensverwalter',
                    'alibi': 'Behauptet, beim Abendessen gewesen zu sein',
                    'motive': 'Verwaltete ihr Vermögen und hatte Zugriff auf ihre Konten',
                    'suspicious_details': 'Seine Fingerabdrücke sind auf einem Glas im Penthouse'
                },
                {
                    'name': 'Julia Hartmann',
                    'occupation': 'Beste Freundin',
                    'alibi': 'War angeblich im Fitnessstudio',
                    'motive': 'Sophie hatte vor, Julia aus ihrem Testament zu streichen',
                    'suspicious_details': 'Wurde gesehen, wie sie das Gebäude kurz vor dem Tod verließ'
                },
                {
                    'name': 'Viktor Krause',
                    'occupation': 'Ex-Verlobter',
                    'alibi': 'Zu Hause, keine Zeugen',
                    'motive': 'Wurde vor einem Monat verlassen, war sehr verbittert',
                    'suspicious_details': 'Hat Chemiekenntnisse aus seinem Studium'
                },
                {
                    'name': 'Anna Lehmann',
                    'occupation': 'Haushälterin',
                    'alibi': 'Hatte angeblich frei',
                    'motive': 'Wurde beschuldigt, gestohlen zu haben und sollte entlassen werden',
                    'suspicious_details': 'Kennt alle Zugangscodes und Gewohnheiten'
                }
            ],
            'murderer_index': 1,
            'evidence': [
                '💀 Spuren von Zyanid im Körper',
                '🔑 Keine Anzeichen eines gewaltsamen Einbruchs',
                '📱 Letzte SMS an Julia: "Wir müssen reden"',
                '💍 Zerbrochener Verlobungsring auf dem Boden'
            ],
            'hints': [
                '🏋️ Julias Fitnessstudio-Alibi kann nicht bestätigt werden',
                '📸 Überwachungskamera zeigt Julia mit einer verdächtigen Tasche',
                '💬 Ein Zeuge hörte Julia sagen: "Sie wird es bereuen"'
            ]
        },
        {
            'title': 'Der Fall des toten Chefkochs',
            'description': 'Ein renommierter Chefkoch wurde in seiner Restaurantküche tot aufgefunden. Ein Messer liegt neben ihm.',
            'location': 'Sternerestaurant "Le Gourmet"',
            'victim': 'Jean-Pierre Dubois, 45, Sternekoch',
            'suspects': [
                {
                    'name': 'Carla Rossi',
                    'occupation': 'Sous-Chef',
                    'alibi': 'War im Lagerraum Inventur machen',
                    'motive': 'Wurde ständig vom Chef erniedrigt und übergangen',
                    'suspicious_details': 'An ihrer Schürze sind Blutflecken'
                },
                {
                    'name': 'Oliver Schmitt',
                    'occupation': 'Restaurantbesitzer',
                    'alibi': 'War in seinem Büro mit Buchhaltung beschäftigt',
                    'motive': 'Der Koch wollte das Restaurant verlassen und ein eigenes eröffnen',
                    'suspicious_details': 'Hat eine Lebensversicherung auf den Koch abgeschlossen'
                },
                {
                    'name': 'Marina Kowalski',
                    'occupation': 'Ex-Freundin und Kellnerin',
                    'alibi': 'Bediente Gäste im Hauptraum',
                    'motive': 'Wurde von Jean-Pierre betrogen und verlassen',
                    'suspicious_details': 'Ihr Alibi lässt eine Lücke von 15 Minuten offen'
                },
                {
                    'name': 'Ricardo Mendez',
                    'occupation': 'Rivalisierender Koch',
                    'alibi': 'In seinem eigenen Restaurant',
                    'motive': 'Jean-Pierre hatte ihm einen Michelin-Stern "gestohlen"',
                    'suspicious_details': 'Wurde in der Nähe des Restaurants gesehen'
                }
            ],
            'murderer_index': 2,
            'evidence': [
                '🔪 Das Mordmesser gehört zur Restaurantküche',
                '🩸 Blutspritzer deuten auf einen Kampf hin',
                '📋 Eine Notiz: "Um 22:30 in der Küche - M."',
                '🎥 Überwachungskamera zeigt jemanden mit Kapuze'
            ],
            'hints': [
                '⏰ Marina hatte genau zur Tatzeit keine Gäste zu bedienen',
                '💔 In Marinas Spind wurde ein Brief mit Drohungen gefunden',
                '👗 An Marinas Kleidung wurden Blutspritzer entdeckt'
            ]
        },
        {
            'title': 'Der Fall des abgestürzten Professors',
            'description': 'Ein Professor wurde tot am Fuß der Universitätstreppe gefunden. Es sieht nach einem Sturz aus, aber Zweifel bleiben.',
            'location': 'Alte Universitätsbibliothek',
            'victim': 'Prof. Dr. Werner Stein, 58, Physikprofessor',
            'suspects': [
                {
                    'name': 'Dr. Sarah Klein',
                    'occupation': 'Kollegin und Konkurrentin',
                    'alibi': 'In ihrem Labor',
                    'motive': 'Beide konkurrierten um dieselbe Forschungsförderung',
                    'suspicious_details': 'Wurde auf der Treppe gesehen kurz vor dem Vorfall'
                },
                {
                    'name': 'Tim Bauer',
                    'occupation': 'Student',
                    'alibi': 'In der Mensa',
                    'motive': 'Drohte durchzufallen und würde sein Stipendium verlieren',
                    'suspicious_details': 'Hatte einen heftigen Streit mit dem Professor am Vortag'
                },
                {
                    'name': 'Elena Wagner',
                    'occupation': 'Ehefrau',
                    'alibi': 'Beim Einkaufen',
                    'motive': 'Entdeckte, dass ihr Mann eine Affäre hatte',
                    'suspicious_details': 'Ihr Einkaufsbeleg zeigt eine verdächtige Zeitlücke'
                },
                {
                    'name': 'Hans Müller',
                    'occupation': 'Hausmeister',
                    'alibi': 'Im Keller bei Reparaturen',
                    'motive': 'Der Professor beschwerte sich ständig über seine Arbeit',
                    'suspicious_details': 'Werkzeugspuren am Treppengeländer könnten seine sein'
                }
            ],
            'murderer_index': 3,
            'evidence': [
                '🔧 Lockere Schrauben am Treppengeländer',
                '👣 Keine Anzeichen von Kampf oder Abwehr',
                '📚 Wichtige Forschungsunterlagen fehlen',
                '🎓 Der Professor hatte kürzlich seinen Rücktritt angekündigt'
            ],
            'hints': [
                '🔨 Hans hatte Zugang zu Werkzeugen und Kenntnis der Gebäudestruktur',
                '😠 Mehrere Zeugen hörten Hans am Morgen schimpfen über den Professor',
                '🔍 In Hans\' Werkzeugkasten finden sich Schrauben, die zum Geländer passen'
            ]
        },
        {
            'title': 'Der Fall der ermordeten Galeristin',
            'description': 'Eine Kunstgaleristin wurde in ihrer Galerie erdrosselt aufgefunden. Ein wertvolles Gemälde fehlt.',
            'location': 'Moderne Kunstgalerie "Arthaus"',
            'victim': 'Isabella Richter, 42, Galeristin und Kunstsammlerin',
            'suspects': [
                {
                    'name': 'Leon Schwarz',
                    'occupation': 'Künstler',
                    'alibi': 'In seinem Atelier',
                    'motive': 'Isabella hatte seinen Vertrag nicht verlängert',
                    'suspicious_details': 'Fasern von seinen Handschuhen am Tatort gefunden'
                },
                {
                    'name': 'Patricia Gold',
                    'occupation': 'Kunsthändlerin und Rivalin',
                    'alibi': 'Bei einer Auktion',
                    'motive': 'Geschäftliche Rivalität um wertvolle Kunstwerke',
                    'suspicious_details': 'Das gestohlene Gemälde wurde bei ihr zum Verkauf angeboten'
                },
                {
                    'name': 'Max Krüger',
                    'occupation': 'Sicherheitschef',
                    'alibi': 'Angeblich seine Runde gedreht',
                    'motive': 'Isabella hatte Unregelmäßigkeiten in seiner Arbeit entdeckt',
                    'suspicious_details': 'Überwachungskameras waren genau zur Tatzeit ausgefallen'
                },
                {
                    'name': 'Diana Wolff',
                    'occupation': 'Assistentin',
                    'alibi': 'Beim Arzt',
                    'motive': 'Wurde als Haupterbin im Testament eingesetzt',
                    'suspicious_details': 'Ihr Arzttermin wurde abgesagt, sie wusste es angeblich nicht'
                }
            ],
            'murderer_index': 2,
            'evidence': [
                '🎨 Wertvolles Gemälde im Wert von 500.000€ fehlt',
                '🧣 Seidenschal wurde als Mordwaffe benutzt',
                '📹 Überwachungskameras waren 30 Minuten lang aus',
                '🔑 Keine Anzeichen eines Einbruchs von außen'
            ],
            'hints': [
                '💻 Max hatte die technischen Kenntnisse, die Kameras auszuschalten',
                '💰 Auf Max\' Konto wurde kürzlich eine große Summe eingezahlt',
                '🤝 Ein Zeuge sah Max das Gebäude kurz nach der Tatzeit verlassen mit einem großen Paket'
            ]
        },
        {
            'title': 'Der Fall des Toten im Weinkeller',
            'description': 'Ein Sommelier wurde in einem exklusiven Weinkeller erschlagen aufgefunden. Eine zerbrochene Weinflasche liegt dabei.',
            'location': 'Privater Weinkeller des "Château Noir"',
            'victim': 'François Laurent, 51, Meister-Sommelier',
            'suspects': [
                {
                    'name': 'Gustav Hartmann',
                    'occupation': 'Weinhandel-Besitzer',
                    'alibi': 'Im Geschäft mit Kunden',
                    'motive': 'François hatte herausgefunden, dass Gustav gefälschte Weine verkaufte',
                    'suspicious_details': 'Seine Schuhe haben Weinflecken, die zur Tatzeit passen'
                },
                {
                    'name': 'Claire Dubois',
                    'occupation': 'Weinexpertin und Kollegin',
                    'alibi': 'Bei einer Weinprobe in der Stadt',
                    'motive': 'François hatte sie bei einem wichtigen Wettbewerb bloßgestellt',
                    'suspicious_details': 'Ihr Fingerabdruck ist auf der zerbrochenen Flasche'
                },
                {
                    'name': 'Robert Klein',
                    'occupation': 'Weinbergbesitzer',
                    'alibi': 'Auf seinem Weingut',
                    'motive': 'François hatte seinen Wein schlecht bewertet, was zu Verlusten führte',
                    'suspicious_details': 'Wurde in der Nähe des Weinkellers gesehen'
                },
                {
                    'name': 'Marie Leclerc',
                    'occupation': 'Erbin und Sammlung-Besitzerin',
                    'alibi': 'Auf Geschäftsreise',
                    'motive': 'François wollte ihren Weinkeller aufgrund von Verstößen schließen',
                    'suspicious_details': 'Ihr Flugticket wurde storniert - sie war nie weg'
                }
            ],
            'murderer_index': 0,
            'evidence': [
                '🍷 Eine wertvolle Bordeaux-Flasche wurde als Waffe benutzt',
                '🔍 Weinflecken führen zur Tür',
                '📄 Notizen über gefälschte Weine in François\' Tasche',
                '⚖️ Ein Laborbericht über Weinanalysen liegt auf dem Tisch'
            ],
            'hints': [
                '🧪 Der Laborbericht zeigt, dass Gustav gefälschte Etiketten verwendete',
                '👞 Die Weinflecken auf Gustavs Schuhen stimmen mit der Tatzeit überein',
                '📞 Gustavs Handy zeigt, dass er zur Tatzeit in der Nähe war, nicht im Geschäft'
            ]
        }
    ]
    
    # Use timestamp and random to select a case, ensuring variety
    selection_seed = int(time.time()) + random.randint(0, 100)
    selected_case = fallback_cases[selection_seed % len(fallback_cases)]
    
    logger.info(f"Using fallback case: {selected_case['title']}")
    return MurderCase(selected_case)


async def log_game_result(db_helpers, user_id: int, display_name: str, won: bool):
    """
    Log detective game result to database.
    
    Args:
        db_helpers: Database helpers module
        user_id: Discord user ID
        display_name: User's display name
        won: Whether the user won
    """
    try:
        if not db_helpers.db_pool:
            logger.warning("Database pool not available in log_game_result")
            return
            
        cnx = db_helpers.db_pool.get_connection()
        if not cnx:
            logger.warning("Could not get DB connection in log_game_result")
            return
            
        cursor = cnx.cursor()
        try:
            # Update player stats
            stat_period = datetime.now(timezone.utc).strftime('%Y-%m')
            
            # Log to user_stats
            cursor.execute(
                """
                INSERT INTO user_stats (user_id, stat_period, games_played, games_won)
                VALUES (%s, %s, 1, %s)
                ON DUPLICATE KEY UPDATE 
                    games_played = games_played + 1,
                    games_won = games_won + %s
                """,
                (user_id, stat_period, 1 if won else 0, 1 if won else 0)
            )
            
            cnx.commit()
            logger.info(f"Logged detective game result for user {user_id}: {'won' if won else 'lost'}")
        finally:
            cursor.close()
            cnx.close()
            
    except Exception as e:
        logger.error(f"Error logging detective game result: {e}", exc_info=True)


async def grant_reward(db_helpers, user_id: int, display_name: str, amount: int, config: dict):
    """
    Grant currency reward for solving the case.
    
    Args:
        db_helpers: Database helpers module
        user_id: Discord user ID
        display_name: User's display name
        amount: Reward amount
        config: Bot configuration
    """
    try:
        stat_period = datetime.now(timezone.utc).strftime('%Y-%m')
        await db_helpers.add_balance(
            user_id,
            display_name,
            amount,
            config,
            stat_period
        )
        
        # Log transaction
        new_balance = await db_helpers.get_balance(user_id)
        await db_helpers.log_transaction(
            user_id,
            'detective_game',
            amount,
            new_balance,
            'Solved murder mystery case'
        )
        
        logger.info(f"Granted {amount} currency to user {user_id} for solving detective case")
        
    except Exception as e:
        logger.error(f"Error granting detective game reward: {e}", exc_info=True)


async def get_user_difficulty(db_helpers, user_id: int) -> int:
    """
    Get user's current difficulty level.
    
    Args:
        db_helpers: Database helpers module
        user_id: Discord user ID
    
    Returns:
        Current difficulty level (1-5)
    """
    try:
        if not db_helpers.db_pool:
            logger.warning("Database pool not available in get_user_difficulty")
            return 1
            
        cnx = db_helpers.db_pool.get_connection()
        if not cnx:
            logger.warning("Could not get DB connection in get_user_difficulty")
            return 1
            
        cursor = cnx.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT current_difficulty FROM detective_user_stats
                WHERE user_id = %s
                """,
                (user_id,)
            )
            result = cursor.fetchone()
            
            if result:
                return result['current_difficulty']
            else:
                # Create new user stats record
                cursor.execute(
                    """
                    INSERT INTO detective_user_stats (user_id, current_difficulty)
                    VALUES (%s, 1)
                    """,
                    (user_id,)
                )
                cnx.commit()
                return 1
                
        finally:
            cursor.close()
            cnx.close()
            
    except Exception as e:
        logger.error(f"Error getting user difficulty: {e}", exc_info=True)
        return 1


async def update_user_stats(db_helpers, user_id: int, solved: bool):
    """
    Update user stats after completing a case.
    Difficulty increases every 10 cases solved.
    
    Args:
        db_helpers: Database helpers module
        user_id: Discord user ID
        solved: Whether the user correctly solved the case
    """
    try:
        if not db_helpers.db_pool:
            logger.warning("Database pool not available in update_user_stats")
            return
            
        cnx = db_helpers.db_pool.get_connection()
        if not cnx:
            logger.warning("Could not get DB connection in update_user_stats")
            return
            
        cursor = cnx.cursor(dictionary=True)
        try:
            # First get current stats
            cursor.execute(
                """
                SELECT current_difficulty, cases_solved, cases_at_current_difficulty
                FROM detective_user_stats
                WHERE user_id = %s
                """,
                (user_id,)
            )
            current_stats = cursor.fetchone()
            
            if solved:
                if current_stats:
                    cases_at_difficulty = current_stats.get('cases_at_current_difficulty', 0)
                    current_difficulty = current_stats.get('current_difficulty', 1)
                    
                    # Increment cases at current difficulty
                    cases_at_difficulty += 1
                    
                    # Check if user should level up (10 cases at current difficulty)
                    new_difficulty = current_difficulty
                    if cases_at_difficulty >= 10 and current_difficulty < 5:
                        new_difficulty = current_difficulty + 1
                        cases_at_difficulty = 0  # Reset counter for new difficulty
                        logger.info(f"User {user_id} leveled up to difficulty {new_difficulty}")
                    
                    cursor.execute(
                        """
                        UPDATE detective_user_stats
                        SET current_difficulty = %s,
                            cases_solved = cases_solved + 1,
                            total_cases_played = total_cases_played + 1,
                            cases_at_current_difficulty = %s,
                            last_played_at = NOW()
                        WHERE user_id = %s
                        """,
                        (new_difficulty, cases_at_difficulty, user_id)
                    )
                else:
                    # New user
                    cursor.execute(
                        """
                        INSERT INTO detective_user_stats 
                        (user_id, current_difficulty, cases_solved, total_cases_played, cases_at_current_difficulty, last_played_at)
                        VALUES (%s, 1, 1, 1, 1, NOW())
                        """,
                        (user_id,)
                    )
            else:
                # Failed case - increment total played but don't change difficulty
                cursor.execute(
                    """
                    INSERT INTO detective_user_stats 
                    (user_id, current_difficulty, cases_failed, total_cases_played, last_played_at)
                    VALUES (%s, 1, 1, 1, NOW())
                    ON DUPLICATE KEY UPDATE 
                        cases_failed = cases_failed + 1,
                        total_cases_played = total_cases_played + 1,
                        last_played_at = NOW()
                    """,
                    (user_id,)
                )
            
            cnx.commit()
            logger.info(f"Updated detective stats for user {user_id}: solved={solved}")
            
        finally:
            cursor.close()
            cnx.close()
            
    except Exception as e:
        logger.error(f"Error updating user stats: {e}", exc_info=True)


def compute_case_hash(case_data: dict) -> str:
    """
    Compute a hash for a case to ensure uniqueness.
    Hash is based on title, victim, suspects names, and murderer.
    """
    # Create a canonical string representation
    hash_components = [
        case_data.get('title', ''),
        case_data.get('victim', ''),
        str(case_data.get('murderer_index', 0)),
    ]
    
    # Add suspect names
    suspects = case_data.get('suspects', [])
    for suspect in suspects:
        hash_components.append(suspect.get('name', ''))
    
    # Combine and hash
    combined = '|'.join(hash_components).lower()
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()


async def check_case_exists(db_helpers, case_hash: str) -> bool:
    """
    Check if a case with this hash already exists.
    
    Args:
        db_helpers: Database helpers module
        case_hash: SHA256 hash of case
    
    Returns:
        True if case exists, False otherwise
    """
    try:
        if not db_helpers.db_pool:
            return False
            
        cnx = db_helpers.db_pool.get_connection()
        if not cnx:
            return False
            
        cursor = cnx.cursor()
        try:
            cursor.execute(
                """
                SELECT COUNT(*) FROM detective_cases
                WHERE case_hash = %s
                """,
                (case_hash,)
            )
            count = cursor.fetchone()[0]
            return count > 0
            
        finally:
            cursor.close()
            cnx.close()
            
    except mysql.connector.errors.ProgrammingError as e:
        # Handle case where case_hash column doesn't exist yet
        if "Unknown column 'case_hash'" in str(e):
            logger.warning("case_hash column not found in detective_cases table. Please run migration.")
            return False
        logger.error(f"Error checking case existence: {e}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"Error checking case existence: {e}", exc_info=True)
        return False


async def save_case_to_db(db_helpers, case_data: dict, difficulty: int) -> int:
    """
    Save a generated case to the database.
    
    Args:
        db_helpers: Database helpers module
        case_data: Dictionary with case information
        difficulty: Difficulty level (1-5)
    
    Returns:
        case_id of the saved case, or None if failed
    """
    try:
        if not db_helpers.db_pool:
            logger.warning("Database pool not available in save_case_to_db")
            return None
        
        # Compute hash for uniqueness check
        case_hash = compute_case_hash(case_data)
        
        # Check if case already exists
        if await check_case_exists(db_helpers, case_hash):
            logger.warning(f"Case with hash {case_hash[:8]}... already exists, skipping save")
            return None
            
        cnx = db_helpers.db_pool.get_connection()
        if not cnx:
            logger.warning("Could not get DB connection in save_case_to_db")
            return None
            
        cursor = cnx.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO detective_cases 
                (title, description, location, victim, suspects, murderer_index, evidence, hints, difficulty, case_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    case_data.get('title', ''),
                    case_data.get('description', ''),
                    case_data.get('location', ''),
                    case_data.get('victim', ''),
                    json.dumps(case_data.get('suspects', [])),
                    case_data.get('murderer_index', 0),
                    json.dumps(case_data.get('evidence', [])),
                    json.dumps(case_data.get('hints', [])),
                    difficulty,
                    case_hash
                )
            )
            cnx.commit()
            case_id = cursor.lastrowid
            
            logger.info(f"Saved new unique case to database with ID {case_id}, difficulty {difficulty}, hash {case_hash[:8]}...")
            return case_id
            
        finally:
            cursor.close()
            cnx.close()
            
    except mysql.connector.errors.ProgrammingError as e:
        # Handle case where case_hash column doesn't exist yet
        if "Unknown column 'case_hash'" in str(e):
            logger.warning("case_hash column not found. Saving case without hash. Please run migration.")
            # Try saving without case_hash
            try:
                cnx = db_helpers.db_pool.get_connection()
                if not cnx:
                    return None
                cursor = cnx.cursor()
                cursor.execute(
                    """
                    INSERT INTO detective_cases 
                    (title, description, location, victim, suspects, murderer_index, evidence, hints, difficulty)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        case_data.get('title', ''),
                        case_data.get('description', ''),
                        case_data.get('location', ''),
                        case_data.get('victim', ''),
                        json.dumps(case_data.get('suspects', [])),
                        case_data.get('murderer_index', 0),
                        json.dumps(case_data.get('evidence', [])),
                        json.dumps(case_data.get('hints', [])),
                        difficulty
                    )
                )
                cnx.commit()
                case_id = cursor.lastrowid
                cursor.close()
                cnx.close()
                logger.info(f"Saved case to database with ID {case_id}, difficulty {difficulty} (without hash)")
                return case_id
            except Exception as fallback_error:
                logger.error(f"Error saving case without hash: {fallback_error}", exc_info=True)
                return None
        logger.error(f"Error saving case to database: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Error saving case to database: {e}", exc_info=True)
        return None


async def get_unsolved_case(db_helpers, user_id: int, difficulty: int):
    """
    Get an unsolved case for the user at their difficulty level.
    
    Args:
        db_helpers: Database helpers module
        user_id: Discord user ID
        difficulty: Desired difficulty level
    
    Returns:
        MurderCase object or None if no unsolved cases exist
    """
    try:
        if not db_helpers.db_pool:
            logger.warning("Database pool not available in get_unsolved_case")
            return None
            
        cnx = db_helpers.db_pool.get_connection()
        if not cnx:
            logger.warning("Could not get DB connection in get_unsolved_case")
            return None
            
        cursor = cnx.cursor(dictionary=True)
        try:
            # Find a case at this difficulty that the user hasn't completed
            cursor.execute(
                """
                SELECT c.* FROM detective_cases c
                LEFT JOIN detective_user_progress p ON c.case_id = p.case_id AND p.user_id = %s
                WHERE c.difficulty = %s AND (p.completed IS NULL OR p.completed = FALSE)
                ORDER BY RAND()
                LIMIT 1
                """,
                (user_id, difficulty)
            )
            result = cursor.fetchone()
            
            if result:
                # Parse JSON fields
                case_data = {
                    'case_id': result['case_id'],
                    'title': result['title'],
                    'description': result['description'],
                    'location': result['location'],
                    'victim': result['victim'],
                    'suspects': json.loads(result['suspects']),
                    'murderer_index': result['murderer_index'],
                    'evidence': json.loads(result['evidence']),
                    'hints': json.loads(result['hints']),
                    'difficulty': result['difficulty']
                }
                return MurderCase(case_data)
            
            return None
            
        finally:
            cursor.close()
            cnx.close()
            
    except Exception as e:
        logger.error(f"Error getting unsolved case: {e}", exc_info=True)
        return None


async def mark_case_started(db_helpers, user_id: int, case_id: int):
    """
    Mark a case as started by a user.
    
    Args:
        db_helpers: Database helpers module
        user_id: Discord user ID
        case_id: Case ID
    """
    try:
        if not db_helpers.db_pool:
            logger.warning("Database pool not available in mark_case_started")
            return
            
        cnx = db_helpers.db_pool.get_connection()
        if not cnx:
            logger.warning("Could not get DB connection in mark_case_started")
            return
            
        cursor = cnx.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO detective_user_progress (user_id, case_id, completed, solved)
                VALUES (%s, %s, FALSE, FALSE)
                ON DUPLICATE KEY UPDATE started_at = NOW()
                """,
                (user_id, case_id)
            )
            cnx.commit()
            logger.info(f"Marked case {case_id} as started for user {user_id}")
            
        finally:
            cursor.close()
            cnx.close()
            
    except Exception as e:
        logger.error(f"Error marking case as started: {e}", exc_info=True)


async def has_user_seen_case(db_helpers, user_id: int, case_id: int) -> bool:
    """
    Check if a user has already seen/played a specific case.
    
    Args:
        db_helpers: Database helpers module
        user_id: Discord user ID
        case_id: Case ID
    
    Returns:
        True if user has seen the case, False otherwise
    """
    try:
        if not db_helpers.db_pool:
            return False
            
        cnx = db_helpers.db_pool.get_connection()
        if not cnx:
            return False
            
        cursor = cnx.cursor()
        try:
            cursor.execute(
                """
                SELECT COUNT(*) FROM detective_user_progress
                WHERE user_id = %s AND case_id = %s
                """,
                (user_id, case_id)
            )
            count = cursor.fetchone()[0]
            return count > 0
            
        finally:
            cursor.close()
            cnx.close()
            
    except Exception as e:
        logger.error(f"Error checking if user has seen case: {e}", exc_info=True)
        return False


async def get_existing_case_by_hash(db_helpers, case_hash: str, user_id: int):
    """
    Get an existing case by its hash if the user hasn't seen it.
    
    Args:
        db_helpers: Database helpers module
        case_hash: SHA256 hash of case
        user_id: Discord user ID
    
    Returns:
        MurderCase object or None
    """
    try:
        if not db_helpers.db_pool:
            return None
            
        cnx = db_helpers.db_pool.get_connection()
        if not cnx:
            return None
            
        cursor = cnx.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT * FROM detective_cases
                WHERE case_hash = %s
                LIMIT 1
                """,
                (case_hash,)
            )
            result = cursor.fetchone()
            
            if result:
                # Parse JSON fields
                case_data = {
                    'case_id': result['case_id'],
                    'title': result['title'],
                    'description': result['description'],
                    'location': result['location'],
                    'victim': result['victim'],
                    'suspects': json.loads(result['suspects']),
                    'murderer_index': result['murderer_index'],
                    'evidence': json.loads(result['evidence']),
                    'hints': json.loads(result['hints']),
                    'difficulty': result['difficulty']
                }
                return MurderCase(case_data)
            
            return None
            
        finally:
            cursor.close()
            cnx.close()
            
    except mysql.connector.errors.ProgrammingError as e:
        # Handle case where case_hash column doesn't exist yet
        if "Unknown column 'case_hash'" in str(e):
            logger.warning("case_hash column not found in get_existing_case_by_hash. Please run migration.")
            return None
        logger.error(f"Error getting existing case by hash: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Error getting existing case by hash: {e}", exc_info=True)
        return None


async def mark_case_completed(db_helpers, user_id: int, case_id: int, solved: bool):
    """
    Mark a case as completed by a user.
    
    Args:
        db_helpers: Database helpers module
        user_id: Discord user ID
        case_id: Case ID
        solved: Whether the user correctly solved the case
    """
    try:
        if not db_helpers.db_pool:
            logger.warning("Database pool not available in mark_case_completed")
            return
            
        cnx = db_helpers.db_pool.get_connection()
        if not cnx:
            logger.warning("Could not get DB connection in mark_case_completed")
            return
            
        cursor = cnx.cursor()
        try:
            cursor.execute(
                """
                UPDATE detective_user_progress 
                SET completed = TRUE, solved = %s, completed_at = NOW()
                WHERE user_id = %s AND case_id = %s
                """,
                (solved, user_id, case_id)
            )
            cnx.commit()
            logger.info(f"Marked case {case_id} as completed for user {user_id}, solved={solved}")
            
        finally:
            cursor.close()
            cnx.close()
            
    except Exception as e:
        logger.error(f"Error marking case as completed: {e}", exc_info=True)


async def generate_case_with_difficulty(api_helpers, config: dict, gemini_api_key: str, openai_api_key: str, difficulty: int):
    """
    Generate murder mystery with difficulty-based puzzles and ciphers.
    Uses fast modular generation approach.
    
    Args:
        api_helpers: API helpers module
        config: Bot configuration
        gemini_api_key: Gemini API key
        openai_api_key: OpenAI API key
        difficulty: Difficulty level (1-5)
    
    Returns:
        MurderCase object with difficulty-appropriate puzzles
    """
    import time
    import re
    
    logger.info(f"Starting case generation with difficulty {difficulty}")
    start_time = time.time()
    
    try:
        # Get model
        provider = config.get('api', {}).get('provider', 'gemini')
        if provider == 'gemini':
            model = config.get('api', {}).get('gemini', {}).get('utility_model', 'gemini-2.5-flash')
        else:
            model = config.get('api', {}).get('openai', {}).get('utility_model', 'gpt-4o-mini')
        
        # Theme selection
        themes = [
            "corporate intrigue", "family drama", "art scandal", "science mystery",
            "political conspiracy", "celebrity crime", "underground world",
            "high society", "academic rivalry", "tech betrayal", "restaurant secrets",
            "theater drama", "sports scandal", "museum theft", "fashion crime"
        ]
        theme = random.choice(themes)
        
        # Difficulty descriptions
        diff_desc = {
            1: "einfach, klare Hinweise",
            2: "mittel, einige versteckte Hinweise",
            3: "mittelschwer, subtile Hinweise mit Codes",
            4: "schwer, verschlüsselte Hinweise",
            5: "sehr schwer, komplexe Rätsel"
        }
        complexity = diff_desc.get(difficulty, diff_desc[1])
        
        # Generate title
        title_prompt = f"Deutscher Krimi-Titel für Thema '{theme}', Schwierigkeit {difficulty}/5. Nur Titel. Format: 'Der Fall ...'"
        title, _ = await api_helpers.get_ai_response_with_model(
            title_prompt, model, config, gemini_api_key, openai_api_key, temperature=1.0
        )
        title = (title or f"Der Fall {theme}").strip()[:100]
        
        # Parallel generation of core components
        desc_prompt = f"Mordszene '{title}', {complexity}. 2-3 Sätze."
        loc_prompt = f"Tatort für '{title}'. Ein Satz, spezifisch und ungewöhnlich."
        victim_prompt = f"Opfer für '{title}': Name, Alter, Beruf. Ein Satz."
        
        core_results = await asyncio.gather(
            api_helpers.get_ai_response_with_model(desc_prompt, model, config, gemini_api_key, openai_api_key, temperature=0.9),
            api_helpers.get_ai_response_with_model(loc_prompt, model, config, gemini_api_key, openai_api_key, temperature=0.9),
            api_helpers.get_ai_response_with_model(victim_prompt, model, config, gemini_api_key, openai_api_key, temperature=0.9)
        )
        
        description = (core_results[0][0] or "Mysteriöser Mord").strip()[:500]
        location = (core_results[1][0] or "Unbekannter Ort").strip()[:200]
        victim = (core_results[2][0] or "Unbekanntes Opfer").strip()[:200]
        
        # Generate suspects in parallel
        murderer_index = random.randint(0, 3)
        suspect_tasks = []
        
        for i in range(4):
            is_guilty = (i == murderer_index)
            status = "SCHULDIG" if is_guilty else "UNSCHULDIG"
            s_prompt = f"""Verdächtiger #{i+1} für '{title}' ({status}).
JSON:
{{
  "name": "Name",
  "occupation": "Beruf (interessant, variiert)",
  "alibi": "Alibi",
  "motive": "Motiv",
  "suspicious_details": "Details"
}}
{'Mache schuldig mit subtilen Hinweisen' if is_guilty else 'Unschuldig aber verdächtig'}."""
            suspect_tasks.append(
                api_helpers.get_ai_response_with_model(s_prompt, model, config, gemini_api_key, openai_api_key, temperature=0.8)
            )
        
        suspect_results = await asyncio.gather(*suspect_tasks)
        
        # Parse suspects
        suspects = []
        for i, (res, _) in enumerate(suspect_results):
            if res:
                try:
                    match = re.search(r'\{.*\}', res, re.DOTALL)
                    if match:
                        suspects.append(json.loads(match.group()))
                        continue
                except:
                    pass
            # Fallback
            suspects.append({
                'name': f'Person {i+1}',
                'occupation': 'Unbekannt',
                'alibi': 'Keine Angabe',
                'motive': 'Unklar',
                'suspicious_details': 'Keine'
            })
        
        # Generate evidence
        ev_prompt = f"3-4 Beweise für '{title}'. Format: emoji + Text, eine pro Zeile."
        ev_res, _ = await api_helpers.get_ai_response_with_model(
            ev_prompt, model, config, gemini_api_key, openai_api_key, temperature=0.7
        )
        
        evidence = []
        if ev_res:
            for line in ev_res.strip().split('\n'):
                if line.strip() and len(line.strip()) > 3:
                    evidence.append(line.strip()[:200])
        
        if len(evidence) < 3:
            evidence = ['🔍 Tatortspuren', '📋 Verdächtige Notizen', '💀 Forensik']
        
        # Generate hints with puzzle support
        murderer_name = suspects[murderer_index].get('name', 'Täter')
        hints_prompt = f"2-3 Hinweise auf '{murderer_name}' als Mörder. Schwierigkeit {difficulty}/5. Format: emoji + Hinweis pro Zeile."
        hints_res, _ = await api_helpers.get_ai_response_with_model(
            hints_prompt, model, config, gemini_api_key, openai_api_key, temperature=0.7
        )
        
        raw_hints = []
        if hints_res:
            for line in hints_res.strip().split('\n'):
                if line.strip() and len(line.strip()) > 3:
                    raw_hints.append(line.strip()[:200])
        
        if len(raw_hints) < 2:
            raw_hints = [f'🔎 Hinweis auf {murderer_name}', f'💡 Detail über {murderer_name}']
        
        # Add encryption for difficulty 3+
        hints = []
        encrypted_messages = []
        
        for hint in raw_hints:
            if difficulty >= 3 and random.random() < 0.5:  # 50% chance to encrypt hint
                puzzle = create_puzzle_hint(hint, difficulty)
                encrypted_messages.append(puzzle)
                cipher_info = f"🔐 Verschlüsselte Nachricht"
                if puzzle.get('hint'):
                    cipher_info += f" ({puzzle['hint']})"
                cipher_info += f": {puzzle['encrypted']}"
                hints.append(cipher_info)
            else:
                hints.append(hint)
        
        # Build case
        case_data = {
            'title': title,
            'description': description,
            'location': location,
            'victim': victim,
            'suspects': suspects,
            'murderer_index': murderer_index,
            'evidence': evidence,
            'hints': hints,
            'encrypted_messages': encrypted_messages,
            'difficulty': difficulty
        }
        
        elapsed = time.time() - start_time
        logger.info(f"Difficulty {difficulty} case generated in {elapsed:.1f}s")
        
        return MurderCase(case_data)
        
    except Exception as e:
        logger.error(f"Error in difficulty case generation: {e}", exc_info=True)
        logger.info("Falling back to pre-defined case")
        return create_fallback_case()


async def get_or_generate_case(db_helpers, api_helpers, config: dict, gemini_api_key: str, openai_api_key: str, user_id: int):
    """
    Get an unsolved case for the user or generate a new one.
    Prioritizes cases the user hasn't seen before.
    
    Args:
        db_helpers: Database helpers module
        api_helpers: API helpers module
        config: Bot configuration
        gemini_api_key: Gemini API key
        openai_api_key: OpenAI API key
        user_id: Discord user ID
    
    Returns:
        MurderCase object
    """
    try:
        # Get user's current difficulty
        difficulty = await get_user_difficulty(db_helpers, user_id)
        
        # Try to find an unsolved case at this difficulty that user hasn't seen
        case = await get_unsolved_case(db_helpers, user_id, difficulty)
        
        if case:
            logger.info(f"Found existing unsolved case {case.case_id} for user {user_id} at difficulty {difficulty}")
            return case
        
        # No unsolved case found, generate a new one
        logger.info(f"Generating new case for user {user_id} at difficulty {difficulty}")
        
        # Try up to 5 times to generate a case
        max_attempts = 5
        for attempt in range(max_attempts):
            case = await generate_case_with_difficulty(
                api_helpers,
                config,
                gemini_api_key,
                openai_api_key,
                difficulty
            )
            
            # Prepare case data for saving
            case_data = {
                'title': case.case_title,
                'description': case.case_description,
                'location': case.location,
                'victim': case.victim,
                'suspects': case.suspects,
                'murderer_index': case.murderer_index,
                'evidence': case.evidence,
                'hints': case.hints
            }
            
            # Check if this EXACT case already exists globally
            # We allow similar cases but not identical ones
            case_hash = compute_case_hash(case_data)
            exists = await check_case_exists(db_helpers, case_hash)
            
            if not exists:
                # New unique case - save it
                case_id = await save_case_to_db(db_helpers, case_data, difficulty)
                if case_id:
                    case.case_id = case_id
                    logger.info(f"Generated and saved unique case {case_id} (attempt {attempt + 1})")
                    return case
                else:
                    # Failed to save but continue trying
                    logger.warning(f"Failed to save case (attempt {attempt + 1}), retrying...")
            else:
                # This exact case exists, but we can still use it if USER hasn't seen it
                logger.info(f"Case already exists globally (attempt {attempt + 1}), checking if user has seen it...")
                
                # Try to fetch the existing case and check if user has played it
                existing_case = await get_existing_case_by_hash(db_helpers, case_hash, user_id)
                if existing_case and not await has_user_seen_case(db_helpers, user_id, existing_case.case_id):
                    logger.info(f"User hasn't seen this case yet, reusing case {existing_case.case_id}")
                    return existing_case
                else:
                    logger.info(f"User has already seen this case, generating another...")
        
        # If we couldn't generate after max attempts, try using any fallback
        logger.warning(f"Could not generate unique case after {max_attempts} attempts, using fallback rotation")
        fallback = create_fallback_case()
        
        # Try to save the fallback case too (with a special marker)
        fallback_data = {
            'title': fallback.case_title,
            'description': fallback.case_description,
            'location': fallback.location,
            'victim': fallback.victim,
            'suspects': fallback.suspects,
            'murderer_index': fallback.murderer_index,
            'evidence': fallback.evidence,
            'hints': fallback.hints
        }
        
        # Save fallback if it doesn't exist
        fallback_hash = compute_case_hash(fallback_data)
        if not await check_case_exists(db_helpers, fallback_hash):
            case_id = await save_case_to_db(db_helpers, fallback_data, difficulty)
            if case_id:
                fallback.case_id = case_id
        
        return fallback
        
    except Exception as e:
        logger.error(f"Error in get_or_generate_case: {e}", exc_info=True)
        return create_fallback_case()


async def get_user_detective_stats(db_helpers, user_id: int) -> dict:
    """
    Get comprehensive detective game statistics for a user.
    
    Args:
        db_helpers: Database helpers module
        user_id: Discord user ID
    
    Returns:
        Dictionary with detective stats or None
    """
    try:
        if not db_helpers.db_pool:
            return None
            
        cnx = db_helpers.db_pool.get_connection()
        if not cnx:
            return None
            
        cursor = cnx.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT 
                    current_difficulty,
                    cases_solved,
                    cases_failed,
                    total_cases_played,
                    cases_at_current_difficulty,
                    last_played_at
                FROM detective_user_stats
                WHERE user_id = %s
                """,
                (user_id,)
            )
            stats = cursor.fetchone()
            
            if not stats:
                return {
                    'current_difficulty': 1,
                    'cases_solved': 0,
                    'cases_failed': 0,
                    'total_cases_played': 0,
                    'cases_at_current_difficulty': 0,
                    'last_played_at': None,
                    'solve_rate': 0,
                    'progress_to_next_difficulty': 0
                }
            
            # Calculate derived stats
            total_cases = stats['total_cases_played']
            solve_rate = (stats['cases_solved'] / total_cases * 100) if total_cases > 0 else 0
            
            # Progress to next difficulty (out of 10 cases)
            progress_to_next = stats['cases_at_current_difficulty']
            
            return {
                'current_difficulty': stats['current_difficulty'],
                'cases_solved': stats['cases_solved'],
                'cases_failed': stats['cases_failed'],
                'total_cases_played': total_cases,
                'cases_at_current_difficulty': stats['cases_at_current_difficulty'],
                'last_played_at': stats['last_played_at'],
                'solve_rate': solve_rate,
                'progress_to_next_difficulty': progress_to_next
            }
            
        finally:
            cursor.close()
            cnx.close()
            
    except Exception as e:
        logger.error(f"Error getting detective stats: {e}", exc_info=True)
        return None
