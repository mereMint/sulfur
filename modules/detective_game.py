"""
Sulfur Bot - Detective/Murder Mystery Game Module
AI-generated murder mystery cases with suspect investigation.
"""

import discord
import random
from datetime import datetime, timezone
from modules.logger_utils import bot_logger as logger


class MurderCase:
    """Represents a murder mystery case."""
    
    def __init__(self, case_data: dict):
        self.case_title = case_data.get('title', 'Mysterious Murder')
        self.case_description = case_data.get('description', '')
        self.location = case_data.get('location', '')
        self.victim = case_data.get('victim', '')
        self.suspects = case_data.get('suspects', [])  # List of suspect dicts
        self.murderer_index = case_data.get('murderer_index', 0)
        self.evidence = case_data.get('evidence', [])
        self.hints = case_data.get('hints', [])  # Hints/codes pointing to the murderer
    
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
