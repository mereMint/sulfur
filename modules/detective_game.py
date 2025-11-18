"""
Sulfur Bot - Detective/Murder Mystery Game Module
AI-generated murder mystery cases with suspect investigation.
"""

import discord
import random
import json
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
    prompt = """Generate a murder mystery case with the following structure (respond in German):

Create a JSON object with:
- title: A catchy case title (max 50 chars)
- description: Brief overview of the murder scene and circumstances (max 200 chars)
- location: Where the murder took place (max 40 chars)
- victim: Name and brief description of victim (max 80 chars)
- suspects: Array of exactly 4 suspects, each with:
  - name: Suspect's name
  - occupation: Their job/role
  - alibi: Their claimed whereabouts (max 80 chars)
  - motive: Potential reason for murder (max 80 chars)
  - suspicious_details: Clues that may point to or away from guilt (max 120 chars)
- murderer_index: Index (0-3) of which suspect is actually guilty
- evidence: Array of 3-4 pieces of evidence found at scene
- hints: Array of 2-3 subtle hints that point to the murderer (these should be codes, patterns, or clues)

Make the case:
1. Entertaining and intriguing but concise
2. Moderately difficult to solve (not obvious but solvable)
3. Include clever hints/codes that point to the murderer
4. Add tricky details that make other suspects also seem suspicious
5. Keep all text brief but engaging"""

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
            
        cursor = cnx.cursor()
        try:
            # Increment difficulty if solved, cap at 5
            if solved:
                cursor.execute(
                    """
                    INSERT INTO detective_user_stats 
                    (user_id, current_difficulty, cases_solved, total_cases_played, last_played_at)
                    VALUES (%s, 2, 1, 1, NOW())
                    ON DUPLICATE KEY UPDATE 
                        current_difficulty = LEAST(current_difficulty + 1, 5),
                        cases_solved = cases_solved + 1,
                        total_cases_played = total_cases_played + 1,
                        last_played_at = NOW()
                    """,
                    (user_id,)
                )
            else:
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
            
        cnx = db_helpers.db_pool.get_connection()
        if not cnx:
            logger.warning("Could not get DB connection in save_case_to_db")
            return None
            
        cursor = cnx.cursor()
        try:
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
            
            logger.info(f"Saved case to database with ID {case_id}, difficulty {difficulty}")
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
    
    prompt = f"""Generate a murder mystery case with the following structure (respond in German):

Create a JSON object with:
- title: A catchy case title (max 50 chars)
- description: Brief overview of the murder scene and circumstances (max 200 chars)
- location: Where the murder took place (max 40 chars)
- victim: Name and brief description of victim (max 80 chars)
- suspects: Array of exactly 4 suspects, each with:
  - name: Suspect's name
  - occupation: Their job/role
  - alibi: Their claimed whereabouts (max 80 chars)
  - motive: Potential reason for murder (max 80 chars)
  - suspicious_details: Clues that may point to or away from guilt (max 120 chars)
- murderer_index: Index (0-3) of which suspect is actually guilty
- evidence: Array of 3-4 pieces of evidence found at scene
- hints: Array of 2-3 hints that point to the murderer

DIFFICULTY LEVEL {difficulty}/5: {difficulty_desc}

Make the case:
1. Entertaining and intriguing but concise
2. Match the difficulty level specified above
3. Include hints/codes appropriate for the difficulty
4. Add red herrings that increase with difficulty
5. Keep all text brief but engaging"""

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
        
        # No unsolved case found, generate a new one
        logger.info(f"Generating new case for user {user_id} at difficulty {difficulty}")
        case = await generate_case_with_difficulty(
            api_helpers,
            config,
            gemini_api_key,
            openai_api_key,
            difficulty
        )
        
        # Save the case to database
        if hasattr(case, 'case_id') and case.case_id is None:
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
            case_id = await save_case_to_db(db_helpers, case_data, difficulty)
            case.case_id = case_id
        
        return case
        
    except Exception as e:
        logger.error(f"Error in get_or_generate_case: {e}", exc_info=True)
        return create_fallback_case()

    except Exception as e:
        logger.error(f"Error granting detective game reward: {e}", exc_info=True)
