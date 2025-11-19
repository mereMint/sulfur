"""
Sulfur Bot - Personalized Trolly Problem Feature
Generates personalized ethical dilemmas based on user data.
"""

import discord
import json
from datetime import datetime, timezone
from modules.logger_utils import bot_logger as logger


class TrollyProblem:
    """Represents a trolly problem dilemma."""
    
    def __init__(self, problem_data: dict):
        self.problem_id = problem_data.get('problem_id', None)
        self.scenario = problem_data.get('scenario', '')
        self.option_a = problem_data.get('option_a', '')
        self.option_b = problem_data.get('option_b', '')
        self.personalization_level = problem_data.get('personalization_level', 'generic')


async def generate_trolly_problem(api_helpers, config: dict, gemini_api_key: str, openai_api_key: str, user_data: dict = None):
    """
    Generate a trolly problem using AI, optionally personalized with user data.
    
    Args:
        api_helpers: API helpers module
        config: Bot configuration
        gemini_api_key: Gemini API key
        openai_api_key: OpenAI API key
        user_data: Optional dictionary with user information for personalization
    
    Returns:
        TrollyProblem object
    """
    personalization_level = "generic"
    
    # Build personalization context
    personalization_context = ""
    if user_data and any([
        user_data.get('favorite_game'),
        user_data.get('favorite_song'),
        user_data.get('server_bestie'),
        user_data.get('most_used_emoji')
    ]):
        personalization_level = "personalized"
        personalization_context = "\n\nPersonalize this dilemma using the following information about the user:\n"
        
        if user_data.get('favorite_game'):
            personalization_context += f"- Favorite game: {user_data['favorite_game']}\n"
        if user_data.get('favorite_song'):
            personalization_context += f"- Favorite song: {user_data['favorite_song']}\n"
        if user_data.get('server_bestie'):
            personalization_context += f"- Best friend on server: {user_data['server_bestie']}\n"
        if user_data.get('most_used_emoji'):
            personalization_context += f"- Most used emoji: {user_data['most_used_emoji']}\n"
        if user_data.get('display_name'):
            personalization_context += f"- User's name: {user_data['display_name']}\n"
        
        personalization_context += "\nIncorporate these details naturally into the scenario to make it feel personal and relevant."
    
    prompt = f"""Generate a trolley problem ethical dilemma (respond in German).

Create a JSON object with:
- scenario: A detailed description of the trolley problem situation (max 300 chars)
- option_a: First choice the user can make (max 100 chars)
- option_b: Second choice the user can make (max 100 chars)

Make the dilemma:
1. Thought-provoking and genuinely difficult to choose
2. Morally ambiguous with no clear "right" answer
3. Creative and unexpected (not the classic trolley problem)
4. Engaging and relevant to modern life or gaming culture
5. Include real stakes and consequences for both choices{personalization_context}

The dilemma should be dark, humorous, or absurd in true Discord bot fashion, but still philosophically interesting."""

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
            system_prompt="You are a creative philosophy professor who designs ethical dilemmas. Return ONLY valid JSON, no additional text."
        )
        
        if error or not response:
            logger.error(f"Error from AI API: {error}")
            return create_fallback_trolly()
        
        # Parse the AI response
        import re
        
        # Try to extract JSON from response
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            problem_data = json.loads(json_match.group())
            problem_data['personalization_level'] = personalization_level
            return TrollyProblem(problem_data)
        else:
            logger.error("Could not parse AI response for trolly problem")
            return create_fallback_trolly()
            
    except Exception as e:
        logger.error(f"Error generating trolly problem: {e}", exc_info=True)
        return create_fallback_trolly()


def create_fallback_trolly():
    """Create a simple fallback trolly problem if AI generation fails."""
    problem_data = {
        'scenario': 'Ein außer Kontrolle geratener Einkaufswagen rast auf eine Gruppe von fünf AFK-Spielern zu. Du kannst eine Weiche umstellen, um den Wagen auf ein anderes Gleis zu lenken, wo nur ein einzelner Tryhard steht. Was tust du?',
        'option_a': 'Nichts tun - die 5 AFK-Spieler werden getroffen',
        'option_b': 'Weiche umstellen - der Tryhard wird getroffen',
        'personalization_level': 'generic'
    }
    return TrollyProblem(problem_data)


async def save_trolly_response(db_helpers, user_id: int, display_name: str, problem_id: int, chosen_option: str, scenario: str):
    """
    Save a user's response to a trolly problem.
    
    Args:
        db_helpers: Database helpers module
        user_id: Discord user ID
        display_name: User's display name
        problem_id: ID of the problem (None for generated problems)
        chosen_option: Which option the user chose ('a' or 'b')
        scenario: The scenario text for reference
    """
    try:
        if not db_helpers.db_pool:
            logger.warning("Database pool not available in save_trolly_response")
            return
            
        cnx = db_helpers.db_pool.get_connection()
        if not cnx:
            logger.warning("Could not get DB connection in save_trolly_response")
            return
            
        cursor = cnx.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO trolly_responses 
                (user_id, display_name, scenario_summary, chosen_option, responded_at)
                VALUES (%s, %s, %s, %s, NOW())
                """,
                (user_id, display_name, scenario[:200], chosen_option)
            )
            cnx.commit()
            logger.info(f"Saved trolly response for user {user_id}: chose option {chosen_option}")
            
        finally:
            cursor.close()
            cnx.close()
            
    except Exception as e:
        logger.error(f"Error saving trolly response: {e}", exc_info=True)


async def get_user_trolly_stats(db_helpers, user_id: int) -> dict:
    """
    Get statistics about a user's trolly problem responses.
    
    Args:
        db_helpers: Database helpers module
        user_id: Discord user ID
    
    Returns:
        Dictionary with stats or None
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
                    COUNT(*) as total_responses,
                    SUM(CASE WHEN chosen_option = 'a' THEN 1 ELSE 0 END) as chose_a,
                    SUM(CASE WHEN chosen_option = 'b' THEN 1 ELSE 0 END) as chose_b
                FROM trolly_responses
                WHERE user_id = %s
                """,
                (user_id,)
            )
            stats = cursor.fetchone()
            
            if not stats or stats['total_responses'] == 0:
                return {
                    'total_responses': 0,
                    'chose_a': 0,
                    'chose_b': 0,
                    'preference': None
                }
            
            # Determine preference
            preference = None
            if stats['chose_a'] > stats['chose_b']:
                preference = 'a'
            elif stats['chose_b'] > stats['chose_a']:
                preference = 'b'
            
            return {
                'total_responses': stats['total_responses'],
                'chose_a': stats['chose_a'],
                'chose_b': stats['chose_b'],
                'preference': preference
            }
            
        finally:
            cursor.close()
            cnx.close()
            
    except Exception as e:
        logger.error(f"Error getting trolly stats: {e}", exc_info=True)
        return None


async def gather_user_data_for_trolly(db_helpers, user_id: int, display_name: str) -> dict:
    """
    Gather user data that can be used to personalize trolly problems.
    
    Args:
        db_helpers: Database helpers module
        user_id: Discord user ID
        display_name: User's display name
    
    Returns:
        Dictionary with user data for personalization
    """
    try:
        user_data = {
            'display_name': display_name
        }
        
        if not db_helpers.db_pool:
            return user_data
            
        cnx = db_helpers.db_pool.get_connection()
        if not cnx:
            return user_data
            
        cursor = cnx.cursor(dictionary=True)
        try:
            # Get favorite game
            cursor.execute(
                """
                SELECT game_history FROM players
                WHERE discord_id = %s
                """,
                (user_id,)
            )
            result = cursor.fetchone()
            
            if result and result.get('game_history'):
                try:
                    game_history = json.loads(result['game_history'])
                    if game_history:
                        # Find most played game
                        most_played = max(game_history.items(), key=lambda x: x[1].get('total_minutes', 0))
                        user_data['favorite_game'] = most_played[0]
                except:
                    pass
            
            # Get current month for recent stats
            stat_period = datetime.now(timezone.utc).strftime('%Y-%m')
            
            # Get favorite song
            cursor.execute(
                """
                SELECT spotify_minutes FROM user_monthly_stats
                WHERE user_id = %s AND stat_period = %s
                """,
                (user_id, stat_period)
            )
            result = cursor.fetchone()
            
            if result and result.get('spotify_minutes'):
                try:
                    spotify_data = json.loads(result['spotify_minutes'])
                    if spotify_data:
                        most_played_song = max(spotify_data.items(), key=lambda x: x[1])
                        user_data['favorite_song'] = most_played_song[0]
                except:
                    pass
            
            # Get server bestie
            cursor.execute(
                """
                SELECT mention_reply_log FROM user_monthly_stats
                WHERE user_id = %s AND stat_period = %s
                """,
                (user_id, stat_period)
            )
            result = cursor.fetchone()
            
            if result and result.get('mention_reply_log'):
                try:
                    mention_data = json.loads(result['mention_reply_log'])
                    if mention_data:
                        bestie_id = max(mention_data.items(), key=lambda x: x[1])[0]
                        user_data['server_bestie_id'] = bestie_id
                except:
                    pass
            
            # Get most used emoji
            cursor.execute(
                """
                SELECT emoji_usage FROM user_monthly_stats
                WHERE user_id = %s AND stat_period = %s
                """,
                (user_id, stat_period)
            )
            result = cursor.fetchone()
            
            if result and result.get('emoji_usage'):
                try:
                    emoji_data = json.loads(result['emoji_usage'])
                    if emoji_data:
                        most_used_emoji = max(emoji_data.items(), key=lambda x: x[1])[0]
                        user_data['most_used_emoji'] = most_used_emoji
                except:
                    pass
            
            return user_data
            
        finally:
            cursor.close()
            cnx.close()
            
    except Exception as e:
        logger.error(f"Error gathering user data for trolly: {e}", exc_info=True)
        return {'display_name': display_name}
