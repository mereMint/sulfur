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
    Generate a murder mystery case using AI with a single API call.
    
    Returns:
        MurderCase object
    """
    prompt = """Generate a unique and creative murder mystery case (respond in German):

Create a JSON object with:
- title: An engaging and original case title
- description: Vivid overview of the murder scene and circumstances
- location: Where the murder took place (be creative and specific)
- victim: Name and compelling description of the victim
- suspects: Array of exactly 4 suspects, each with:
  - name: Suspect's name (make them memorable)
  - occupation: Their job/role (interesting and varied)
  - alibi: Their claimed whereabouts (detailed and plausible)
  - motive: Potential reason for murder (compelling and believable)
  - suspicious_details: Clues that may point to or away from guilt (intriguing and layered)
- murderer_index: Index (0-3) of which suspect is actually guilty
- evidence: Array of 3-5 pieces of evidence found at scene (be creative with forensic details)
- hints: Array of 2-4 subtle hints that point to the murderer (use codes, patterns, or creative clues)

Create a fresh, original case with:
1. Unique setting and circumstances (avoid clichés)
2. Diverse, interesting characters with depth
3. Creative clues and red herrings
4. Unexpected plot elements
5. Engaging storytelling that feels new each time
6. Varied themes (corporate intrigue, family drama, historical mystery, etc.)

Be creative and vary your approach - each case should feel completely different!"""

    try:
        # Use the proper API function with a specific model
        # Get the utility model from config
        provider = config.get('api', {}).get('provider', 'gemini')
        if provider == 'gemini':
            model = config.get('api', {}).get('gemini', {}).get('utility_model', 'gemini-2.0-flash-exp')
        else:
            model = config.get('api', {}).get('openai', {}).get('utility_model', 'gpt-4o-mini')
        
        # Make a single API call
        response, error = await api_helpers.get_ai_response_with_model(
            prompt,
            model,
            config,
            gemini_api_key,
            openai_api_key,
            system_prompt="You are a creative detective story writer. Return ONLY valid JSON, no additional text."
        )
        
        if error or not response:
            logger.error(f"Error from AI API: {error}")
            return create_fallback_case()
        
        # Parse the AI response
        import json
        import re
        
        # Try to extract JSON from response
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            case_data = json.loads(json_match.group())
            return MurderCase(case_data)
        else:
            logger.error("Could not parse AI response for murder case")
            return create_fallback_case()
            
    except Exception as e:
        logger.error(f"Error generating murder case: {e}", exc_info=True)
        return create_fallback_case()


def create_fallback_case():
    """Create a simple fallback case if AI generation fails."""
    case_data = {
        'title': 'Der Fall des vergifteten Geschäftsmanns',
        'description': 'Ein wohlhabender Geschäftsmann wurde tot in seinem Büro aufgefunden. Eine vergiftete Tasse Kaffee steht auf seinem Schreibtisch.',
        'location': 'Luxusbüro im Stadtzentrum',
        'victim': 'Heinrich Müller, 52, erfolgreicher Immobilienmagnat',
        'suspects': [
            {
                'name': 'Eva Schmidt',
                'occupation': 'Persönliche Assistentin',
                'alibi': 'War angeblich beim Mittagessen',
                'motive': 'Wurde kürzlich in einem Streit über Gehalt gesehen',
                'suspicious_details': 'Hat Zugang zum Büro und kennt seine Kaffee-Gewohnheiten'
            },
            {
                'name': 'Thomas Wagner',
                'occupation': 'Geschäftspartner',
                'alibi': 'In einem Meeting mit anderen Kollegen',
                'motive': 'Gerüchte über finanzielle Unstimmigkeiten',
                'suspicious_details': 'Wurde nervös, als nach dem Kaffee gefragt wurde'
            },
            {
                'name': 'Lisa Becker',
                'occupation': 'Ex-Frau',
                'alibi': 'War zu Hause, keine Zeugen',
                'motive': 'Bitterer Scheidungsstreit um Vermögen',
                'suspicious_details': 'Wurde in der Nähe des Büros gesehen'
            },
            {
                'name': 'Dr. Klaus Fischer',
                'occupation': 'Hausarzt',
                'alibi': 'In seiner Praxis',
                'motive': 'Keine offensichtlichen',
                'suspicious_details': 'Hat Zugang zu Gift und medizinischem Wissen'
            }
        ],
        'murderer_index': 0,
        'evidence': [
            '☕ Vergiftete Kaffeetasse auf dem Schreibtisch',
            '🔑 Keine Anzeichen von Einbruch',
            '📋 Notiz über geplante Gehaltssenkungen',
            '💊 Spuren eines seltenen Gifts im Kaffee'
        ],
        'hints': [
            '🔍 Die Kaffeetasse hatte Lippenstiftspuren - Eva trägt denselben Farbton',
            '📝 Eine Notiz mit Evas Handschrift wurde im Papierkorb gefunden',
            '⏰ Eva war die letzte Person, die das Büro vor dem Tod betrat'
        ]
    }
    return MurderCase(case_data)


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
    
    Args:
        api_helpers: API helpers module
        config: Bot configuration
        gemini_api_key: Gemini API key
        openai_api_key: OpenAI API key
        difficulty: Difficulty level (1-5)
    
    Returns:
        MurderCase object
    """
    # Adjust prompt based on difficulty
    difficulty_instructions = {
        1: "Easy: Make clues obvious and straightforward. All important information is clearly stated.",
        2: "Medium: Some clues require basic deduction. Hints are moderately clear.",
        3: "Moderate-Hard: Clues are subtle and require careful analysis. Hints may be coded or symbolic.",
        4: "Hard: Many red herrings. Clues are cryptic. Hints use complex codes or patterns.",
        5: "Very Hard: Extremely cryptic. Multiple layers of misdirection. Hints are puzzles themselves."
    }
    
    difficulty_desc = difficulty_instructions.get(difficulty, difficulty_instructions[1])
    
    prompt = f"""Generate a unique and creative murder mystery case (respond in German):

Create a JSON object with:
- title: An engaging and original case title
- description: Vivid overview of the murder scene and circumstances
- location: Where the murder took place (be creative and specific)
- victim: Name and compelling description of the victim
- suspects: Array of exactly 4 suspects, each with:
  - name: Suspect's name (make them memorable)
  - occupation: Their job/role (interesting and varied)
  - alibi: Their claimed whereabouts (detailed and plausible)
  - motive: Potential reason for murder (compelling and believable)
  - suspicious_details: Clues that may point to or away from guilt (intriguing and layered)
- murderer_index: Index (0-3) of which suspect is actually guilty
- evidence: Array of 3-5 pieces of evidence found at scene (creative forensic details)
- hints: Array of 2-4 hints that point to the murderer (match difficulty level)

DIFFICULTY LEVEL {difficulty}/5: {difficulty_desc}

Create a fresh, original case with:
1. Unique setting and circumstances matching the difficulty
2. Diverse, interesting characters with depth
3. Creative clues and red herrings appropriate for difficulty
4. Unexpected plot elements
5. Engaging storytelling that feels new each time
6. Varied themes (corporate intrigue, family drama, historical mystery, etc.)

Be creative and vary your approach - avoid repeating previous scenarios!"""

    try:
        # Use the proper API function with a specific model
        provider = config.get('api', {}).get('provider', 'gemini')
        if provider == 'gemini':
            model = config.get('api', {}).get('gemini', {}).get('utility_model', 'gemini-2.0-flash-exp')
        else:
            model = config.get('api', {}).get('openai', {}).get('utility_model', 'gpt-4o-mini')
        
        # Make a single API call
        response, error = await api_helpers.get_ai_response_with_model(
            prompt,
            model,
            config,
            gemini_api_key,
            openai_api_key,
            system_prompt="You are a creative detective story writer. Return ONLY valid JSON, no additional text."
        )
        
        if error or not response:
            logger.error(f"Error from AI API: {error}")
            return create_fallback_case()
        
        # Parse the AI response
        import re
        
        # Try to extract JSON from response
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            case_data = json.loads(json_match.group())
            case_data['difficulty'] = difficulty
            return MurderCase(case_data)
        else:
            logger.error("Could not parse AI response for murder case")
            return create_fallback_case()
            
    except Exception as e:
        logger.error(f"Error generating murder case: {e}", exc_info=True)
        return create_fallback_case()


async def get_or_generate_case(db_helpers, api_helpers, config: dict, gemini_api_key: str, openai_api_key: str, user_id: int):
    """
    Get an unsolved case for the user or generate a new one.
    Ensures that generated cases are unique.
    
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
        
        # Try to find an unsolved case at this difficulty
        case = await get_unsolved_case(db_helpers, user_id, difficulty)
        
        if case:
            logger.info(f"Found existing unsolved case {case.case_id} for user {user_id} at difficulty {difficulty}")
            return case
        
        # No unsolved case found, generate a new unique one
        logger.info(f"Generating new case for user {user_id} at difficulty {difficulty}")
        
        # Try up to 3 times to generate a unique case
        max_attempts = 3
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
            
            # Check if this case is unique
            case_hash = compute_case_hash(case_data)
            if not await check_case_exists(db_helpers, case_hash):
                # Unique case found, save it
                case_id = await save_case_to_db(db_helpers, case_data, difficulty)
                if case_id:
                    case.case_id = case_id
                    logger.info(f"Generated and saved unique case {case_id} for user {user_id}")
                    return case
            else:
                logger.info(f"Generated duplicate case (attempt {attempt + 1}/{max_attempts}), retrying...")
        
        # If all attempts failed, use fallback
        logger.warning(f"Could not generate unique case after {max_attempts} attempts, using fallback")
        return create_fallback_case()
        
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
