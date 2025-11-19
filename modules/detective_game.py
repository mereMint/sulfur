"""
Sulfur Bot - Detective/Murder Mystery Game Module
AI-generated murder mystery cases with suspect investigation.
"""

import discord
import random
import json
import hashlib
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
        self.difficulty = case_data.get('difficulty', 1)  # Difficulty level
    
    def get_suspect(self, index: int):
        """Get suspect details by index."""
        if 0 <= index < len(self.suspects):
            return self.suspects[index]
        return None
    
    def is_correct_murderer(self, index: int) -> bool:
        """Check if the selected suspect is the murderer."""
        return index == self.murderer_index


async def generate_murder_case(api_helpers, config: dict, gemini_api_key: str, openai_api_key: str):
    """
    Generate a murder mystery case using AI with robust retry logic and fallback providers.
    
    This function implements:
    - Multiple retry attempts (up to 5)
    - Exponential backoff between retries
    - Extended timeout (120 seconds)
    - Fallback to alternative AI provider if primary fails
    - Improved JSON parsing with better error handling
    
    Returns:
        MurderCase object
    """
    import asyncio
    import time
    
    # Add timestamp and random elements to force unique generation
    timestamp = int(time.time())
    random_seed = random.randint(1000, 9999)
    
    # Random theme suggestions to encourage variety
    themes = [
        "corporate intrigue", "family drama", "historical mystery", "art world scandal",
        "scientific research gone wrong", "political conspiracy", "celebrity lifestyle",
        "underground crime", "high society scandal", "academic rivalry", "tech startup betrayal",
        "restaurant industry secrets", "theatrical production", "sports competition",
        "museum heist aftermath", "literary world", "fashion industry", "music industry"
    ]
    suggested_theme = random.choice(themes)
    
    prompt = f"""Generate a COMPLETELY UNIQUE and creative murder mystery case (respond in German).

IMPORTANT: This is request #{random_seed} at time {timestamp}. Each case MUST be completely different from any previous cases.

Suggested theme for THIS case: {suggested_theme}

Create a JSON object with:
- title: An engaging and original case title (NOT used before)
- description: Vivid overview of the murder scene and circumstances
- location: Where the murder took place (be creative and specific - use unusual locations)
- victim: Name and compelling description of the victim (unique name and background)
- suspects: Array of exactly 4 suspects, each with:
  - name: Suspect's name (make them memorable and diverse)
  - occupation: Their job/role (interesting and varied - avoid common jobs)
  - alibi: Their claimed whereabouts (detailed and plausible)
  - motive: Potential reason for murder (compelling and believable)
  - suspicious_details: Clues that may point to or away from guilt (intriguing and layered)
- murderer_index: Index (0-3) of which suspect is actually guilty (randomly vary this)
- evidence: Array of 3-5 pieces of evidence found at scene (be creative with forensic details)
- hints: Array of 2-4 subtle hints that point to the murderer (use codes, patterns, or creative clues)

Create a fresh, original case with:
1. Unique setting and circumstances (AVOID any clichés or common scenarios)
2. Diverse, interesting characters with depth and unusual backgrounds
3. Creative clues and red herrings
4. Unexpected plot elements and twists
5. Engaging storytelling that feels completely new
6. VARY the murderer - don't always make it the same suspect position

MANDATORY: Make this case completely different from typical detective stories!
Return ONLY valid JSON without any markdown formatting, code blocks, or additional text."""

    system_prompt = "You are a creative detective story writer. Return ONLY valid JSON, no additional text, no markdown code blocks, no backticks. Each case you generate MUST be completely unique and different from previous ones."

    # Configuration for retries
    max_attempts = 5
    base_timeout = 120  # Longer timeout for generation (2 minutes)
    
    # Determine primary and fallback providers
    primary_provider = config.get('api', {}).get('provider', 'gemini')
    fallback_provider = 'openai' if primary_provider == 'gemini' else 'gemini'
    
    # Get models for both providers
    gemini_model = config.get('api', {}).get('gemini', {}).get('utility_model', 'gemini-2.5-flash')
    openai_model = config.get('api', {}).get('openai', {}).get('utility_model', 'gpt-4o-mini')
    
    providers_to_try = [
        (primary_provider, gemini_model if primary_provider == 'gemini' else openai_model),
        (fallback_provider, gemini_model if fallback_provider == 'gemini' else openai_model)
    ]
    
    logger.info(f"Starting detective case generation with primary provider: {primary_provider}")
    
    # Try each provider
    for provider_name, model in providers_to_try:
        logger.info(f"Attempting generation with {provider_name} provider using model {model}")
        
        # Try multiple times with current provider
        for attempt in range(max_attempts):
            try:
                # Calculate backoff delay
                if attempt > 0:
                    backoff_delay = min(2 ** attempt, 16)  # Exponential backoff, max 16 seconds
                    logger.info(f"Retry attempt {attempt + 1}/{max_attempts} after {backoff_delay}s backoff")
                    await asyncio.sleep(backoff_delay)
                
                # Create a temporary config with extended timeout
                temp_config = config.copy()
                temp_config['api'] = config.get('api', {}).copy()
                temp_config['api']['timeout'] = base_timeout
                
                logger.info(f"Calling AI API (attempt {attempt + 1}/{max_attempts}, timeout={base_timeout}s)")
                
                # Make API call with HIGH temperature for creativity
                response, error = await api_helpers.get_ai_response_with_model(
                    prompt,
                    model,
                    temp_config,
                    gemini_api_key,
                    openai_api_key,
                    system_prompt=system_prompt,
                    temperature=1.2  # High temperature for maximum creativity and variety
                )
                
                if error:
                    logger.warning(f"API returned error on attempt {attempt + 1}: {error}")
                    continue  # Try again
                
                if not response:
                    logger.warning(f"API returned empty response on attempt {attempt + 1}")
                    continue  # Try again
                
                logger.info(f"Received response from AI API (length: {len(response)} chars)")
                
                # Parse the AI response with improved JSON extraction
                import json
                import re
                
                # Clean up response - remove markdown code blocks
                cleaned_response = response.strip()
                
                # Remove markdown code blocks if present
                if '```' in cleaned_response:
                    # Extract content between ```json and ``` or ``` and ```
                    code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', cleaned_response, re.DOTALL)
                    if code_block_match:
                        cleaned_response = code_block_match.group(1)
                        logger.debug("Extracted JSON from markdown code block")
                
                # Try to extract JSON object from response
                json_match = re.search(r'\{.*\}', cleaned_response, re.DOTALL)
                if not json_match:
                    logger.warning(f"No JSON object found in response (attempt {attempt + 1})")
                    logger.debug(f"Response preview: {cleaned_response[:200]}")
                    continue  # Try again
                
                json_str = json_match.group()
                logger.debug(f"Extracted JSON string (length: {len(json_str)} chars)")
                
                # Try to parse JSON
                try:
                    case_data = json.loads(json_str)
                except json.JSONDecodeError as je:
                    logger.warning(f"JSON parse error on attempt {attempt + 1}: {je}")
                    logger.debug(f"Failed JSON preview: {json_str[:200]}")
                    continue  # Try again
                
                # Validate required fields
                required_fields = ['title', 'description', 'location', 'victim', 'suspects', 'murderer_index', 'evidence', 'hints']
                missing_fields = [field for field in required_fields if field not in case_data]
                
                if missing_fields:
                    logger.warning(f"Missing required fields on attempt {attempt + 1}: {missing_fields}")
                    continue  # Try again
                
                # Validate suspects structure
                if not isinstance(case_data.get('suspects'), list) or len(case_data.get('suspects', [])) != 4:
                    logger.warning(f"Invalid suspects array on attempt {attempt + 1} (expected 4 suspects)")
                    continue  # Try again
                
                # Success! Return the generated case
                logger.info(f"Successfully generated case: {case_data.get('title', 'Unknown Title')}")
                return MurderCase(case_data)
                
            except Exception as e:
                logger.error(f"Exception during case generation attempt {attempt + 1}: {e}", exc_info=True)
                # Continue to next attempt
        
        # If we exhausted all attempts with this provider, log it
        logger.warning(f"Failed to generate case with {provider_name} after {max_attempts} attempts")
    
    # All attempts failed with both providers - use fallback
    logger.error(f"All generation attempts failed with both providers, using fallback case")
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
    Generate a murder mystery case using AI with specified difficulty level.
    
    This function implements:
    - Multiple retry attempts (up to 5)
    - Exponential backoff between retries
    - Extended timeout (120 seconds)
    - Fallback to alternative AI provider if primary fails
    - Improved JSON parsing with better error handling
    
    Args:
        api_helpers: API helpers module
        config: Bot configuration
        gemini_api_key: Gemini API key
        openai_api_key: OpenAI API key
        difficulty: Difficulty level (1-5)
    
    Returns:
        MurderCase object
    """
    import asyncio
    import time
    
    # Add timestamp and random elements to force unique generation
    timestamp = int(time.time())
    random_seed = random.randint(1000, 9999)
    
    # Random theme suggestions to encourage variety
    themes = [
        "corporate intrigue", "family drama", "historical mystery", "art world scandal",
        "scientific research gone wrong", "political conspiracy", "celebrity lifestyle",
        "underground crime", "high society scandal", "academic rivalry", "tech startup betrayal",
        "restaurant industry secrets", "theatrical production", "sports competition",
        "museum heist aftermath", "literary world", "fashion industry", "music industry"
    ]
    suggested_theme = random.choice(themes)
    
    # Adjust prompt based on difficulty
    difficulty_instructions = {
        1: "Easy: Make clues obvious and straightforward. All important information is clearly stated.",
        2: "Medium: Some clues require basic deduction. Hints are moderately clear.",
        3: "Moderate-Hard: Clues are subtle and require careful analysis. Hints may be coded or symbolic.",
        4: "Hard: Many red herrings. Clues are cryptic. Hints use complex codes or patterns.",
        5: "Very Hard: Extremely cryptic. Multiple layers of misdirection. Hints are puzzles themselves."
    }
    
    difficulty_desc = difficulty_instructions.get(difficulty, difficulty_instructions[1])
    
    prompt = f"""Generate a COMPLETELY UNIQUE and creative murder mystery case (respond in German).

IMPORTANT: This is request #{random_seed} at time {timestamp}. Each case MUST be completely different from any previous cases.

Suggested theme for THIS case: {suggested_theme}

Create a JSON object with:
- title: An engaging and original case title (NOT used before)
- description: Vivid overview of the murder scene and circumstances
- location: Where the murder took place (be creative and specific - use unusual locations)
- victim: Name and compelling description of the victim (unique name and background)
- suspects: Array of exactly 4 suspects, each with:
  - name: Suspect's name (make them memorable and diverse)
  - occupation: Their job/role (interesting and varied - avoid common jobs)
  - alibi: Their claimed whereabouts (detailed and plausible)
  - motive: Potential reason for murder (compelling and believable)
  - suspicious_details: Clues that may point to or away from guilt (intriguing and layered)
- murderer_index: Index (0-3) of which suspect is actually guilty (randomly vary this)
- evidence: Array of 3-5 pieces of evidence found at scene (creative forensic details)
- hints: Array of 2-4 hints that point to the murderer (match difficulty level)

DIFFICULTY LEVEL {difficulty}/5: {difficulty_desc}

Create a fresh, original case with:
1. Unique setting and circumstances matching the difficulty (AVOID clichés)
2. Diverse, interesting characters with depth and unusual backgrounds
3. Creative clues and red herrings appropriate for difficulty
4. Unexpected plot elements and twists
5. Engaging storytelling that feels completely new
6. Varied themes - make each case feel distinctly different
7. VARY the murderer - don't always make it the same suspect position

MANDATORY: Make this case completely different from typical detective stories and any previous cases!
Return ONLY valid JSON without any markdown formatting, code blocks, or additional text."""

    system_prompt = "You are a creative detective story writer. Return ONLY valid JSON, no additional text, no markdown code blocks, no backticks. Each case you generate MUST be completely unique and different from previous ones."

    # Configuration for retries
    max_attempts = 5
    base_timeout = 120  # Longer timeout for generation (2 minutes)
    
    # Determine primary and fallback providers
    primary_provider = config.get('api', {}).get('provider', 'gemini')
    fallback_provider = 'openai' if primary_provider == 'gemini' else 'gemini'
    
    # Get models for both providers
    gemini_model = config.get('api', {}).get('gemini', {}).get('utility_model', 'gemini-2.5-flash')
    openai_model = config.get('api', {}).get('openai', {}).get('utility_model', 'gpt-4o-mini')
    
    providers_to_try = [
        (primary_provider, gemini_model if primary_provider == 'gemini' else openai_model),
        (fallback_provider, gemini_model if fallback_provider == 'gemini' else openai_model)
    ]
    
    logger.info(f"Starting detective case generation (difficulty {difficulty}) with primary provider: {primary_provider}")
    
    # Try each provider
    for provider_name, model in providers_to_try:
        logger.info(f"Attempting generation with {provider_name} provider using model {model}")
        
        # Try multiple times with current provider
        for attempt in range(max_attempts):
            try:
                # Calculate backoff delay
                if attempt > 0:
                    backoff_delay = min(2 ** attempt, 16)  # Exponential backoff, max 16 seconds
                    logger.info(f"Retry attempt {attempt + 1}/{max_attempts} after {backoff_delay}s backoff")
                    await asyncio.sleep(backoff_delay)
                
                # Create a temporary config with extended timeout
                temp_config = config.copy()
                temp_config['api'] = config.get('api', {}).copy()
                temp_config['api']['timeout'] = base_timeout
                
                logger.info(f"Calling AI API (attempt {attempt + 1}/{max_attempts}, timeout={base_timeout}s)")
                
                # Make API call with HIGH temperature for creativity
                response, error = await api_helpers.get_ai_response_with_model(
                    prompt,
                    model,
                    temp_config,
                    gemini_api_key,
                    openai_api_key,
                    system_prompt=system_prompt,
                    temperature=1.2  # High temperature for maximum creativity and variety
                )
                
                if error:
                    logger.warning(f"API returned error on attempt {attempt + 1}: {error}")
                    continue  # Try again
                
                if not response:
                    logger.warning(f"API returned empty response on attempt {attempt + 1}")
                    continue  # Try again
                
                logger.info(f"Received response from AI API (length: {len(response)} chars)")
                
                # Parse the AI response with improved JSON extraction
                import json
                import re
                
                # Clean up response - remove markdown code blocks
                cleaned_response = response.strip()
                
                # Remove markdown code blocks if present
                if '```' in cleaned_response:
                    # Extract content between ```json and ``` or ``` and ```
                    code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', cleaned_response, re.DOTALL)
                    if code_block_match:
                        cleaned_response = code_block_match.group(1)
                        logger.debug("Extracted JSON from markdown code block")
                
                # Try to extract JSON object from response
                json_match = re.search(r'\{.*\}', cleaned_response, re.DOTALL)
                if not json_match:
                    logger.warning(f"No JSON object found in response (attempt {attempt + 1})")
                    logger.debug(f"Response preview: {cleaned_response[:200]}")
                    continue  # Try again
                
                json_str = json_match.group()
                logger.debug(f"Extracted JSON string (length: {len(json_str)} chars)")
                
                # Try to parse JSON
                try:
                    case_data = json.loads(json_str)
                except json.JSONDecodeError as je:
                    logger.warning(f"JSON parse error on attempt {attempt + 1}: {je}")
                    logger.debug(f"Failed JSON preview: {json_str[:200]}")
                    continue  # Try again
                
                # Validate required fields
                required_fields = ['title', 'description', 'location', 'victim', 'suspects', 'murderer_index', 'evidence', 'hints']
                missing_fields = [field for field in required_fields if field not in case_data]
                
                if missing_fields:
                    logger.warning(f"Missing required fields on attempt {attempt + 1}: {missing_fields}")
                    continue  # Try again
                
                # Validate suspects structure
                if not isinstance(case_data.get('suspects'), list) or len(case_data.get('suspects', [])) != 4:
                    logger.warning(f"Invalid suspects array on attempt {attempt + 1} (expected 4 suspects)")
                    continue  # Try again
                
                # Add difficulty to case data
                case_data['difficulty'] = difficulty
                
                # Success! Return the generated case
                logger.info(f"Successfully generated case (difficulty {difficulty}): {case_data.get('title', 'Unknown Title')}")
                return MurderCase(case_data)
                
            except Exception as e:
                logger.error(f"Exception during case generation attempt {attempt + 1}: {e}", exc_info=True)
                # Continue to next attempt
        
        # If we exhausted all attempts with this provider, log it
        logger.warning(f"Failed to generate case with {provider_name} after {max_attempts} attempts")
    
    # All attempts failed with both providers - use fallback
    logger.error(f"All generation attempts failed with both providers, using fallback case")
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
