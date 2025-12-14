import json
import os
import platform
import re
import subprocess
import threading
import time
import logging
import asyncio
from flask import Flask, render_template, jsonify, request, flash, redirect, url_for
from flask_socketio import SocketIO, emit

# --- Local Imports ---
from modules import db_helpers
from modules.controls import stop_bot_processes, restart_bot, sync_database_changes, update_bot_from_git

# Setup logging - use the structured logger from logger_utils
from modules.logger_utils import web_logger as logger


# --- Helper function for async operations ---
def run_async(coro):
    """
    Helper to run async functions in sync Flask routes.
    Uses asyncio.run() which properly manages event loop lifecycle.
    """
    try:
        return asyncio.run(coro)
    except RuntimeError:
        # Fallback for environments where asyncio.run() isn't available
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


# --- Configuration ---

# Load environment variables for database connection
from dotenv import load_dotenv
load_dotenv()

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_USER = os.environ.get("DB_USER", "sulfur_bot_user")
DB_PASS = os.environ.get("DB_PASS", "")
DB_NAME = os.environ.get("DB_NAME", "sulfur_bot")

# Initialize the database pool for the web dashboard with retry logic
print("[Web Dashboard] Initializing database connection...")
logger.info("Initializing database connection...")

db_init_success = False
db_init_max_retries = 1  # Reduced from 3 to 1 for faster startup
db_init_retry_delay = 1  # Reduced from 3 to 1 second

for attempt in range(1, db_init_max_retries + 1):
    try:
        print(f"[Web Dashboard] Database connection attempt {attempt}/{db_init_max_retries} to {DB_HOST}:{DB_NAME}...")
        logger.info(f"Database connection attempt {attempt}/{db_init_max_retries} to {DB_HOST}:{DB_NAME}")
        
        if db_helpers.init_db_pool(DB_HOST, DB_USER, DB_PASS, DB_NAME):
            db_init_success = True
            print("[Web Dashboard] Database pool initialized successfully.")
            logger.info("Database pool initialized successfully")
            break
        else:
            print(f"[Web Dashboard] WARNING: Database pool initialization failed (attempt {attempt}/{db_init_max_retries})")
            logger.warning(f"Database pool initialization failed (attempt {attempt}/{db_init_max_retries})")
            
            if attempt < db_init_max_retries:
                wait_time = db_init_retry_delay
                print(f"[Web Dashboard] Retrying in {wait_time} seconds...")
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                
    except Exception as e:
        print(f"[Web Dashboard] ERROR: Database pool initialization error (attempt {attempt}/{db_init_max_retries}): {e}")
        logger.error(f"Database pool initialization error (attempt {attempt}/{db_init_max_retries}): {e}")
        
        if attempt < db_init_max_retries:
            wait_time = db_init_retry_delay
            print(f"[Web Dashboard] Retrying in {wait_time} seconds...")
            logger.info(f"Retrying in {wait_time} seconds...")
            time.sleep(wait_time)

if not db_init_success or not db_helpers.db_pool:
    print("=" * 70)
    print("[Web Dashboard] WARNING: Database pool failed to initialize after all retries")
    print("[Web Dashboard] Some dashboard features may be unavailable")
    print("[Web Dashboard] Please check database configuration and connectivity")
    print("=" * 70)
    logger.warning("Database pool failed to initialize - some features may be unavailable")

# --- Flask App Setup ---

# --- FIX: Point Flask to the 'web' folder where HTML templates live ---
# The project stores dashboard HTML in the web/ directory.
app = Flask(__name__, template_folder='web')
app.secret_key = os.urandom(24)  # Needed for flashing messages
socketio = SocketIO(app, async_mode='threading')

LOG_DIR = "logs"

def get_latest_log_file():
    """Finds the most recently created log file."""
    if not os.path.exists(LOG_DIR):
        return None
    log_files = [os.path.join(LOG_DIR, f) for f in os.listdir(LOG_DIR) if f.endswith('.log')]
    if not log_files:
        return None
    return max(log_files, key=os.path.getctime)


# --- Database Query Helpers ---

def safe_db_query(cursor, query, params=None, default=None, fetch_all=False):
    """
    Safely execute a database query with error handling.
    
    Args:
        cursor: Database cursor to execute query on
        query: SQL query string
        params: Query parameters (tuple or list) for parameterized queries
        default: Default value to return on error (None, 0, [], etc.)
        fetch_all: If True, fetchall(); otherwise fetchone()
    
    Returns:
        Query result or default value on error
    """
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        if fetch_all:
            return cursor.fetchall()
        else:
            return cursor.fetchone()
    except Exception as e:
        logger.warning(f"Query failed: {query[:80]}... Error: {e}")
        return default if default is not None else ([] if fetch_all else {})

def follow_log_file():
    """A generator function that yields new lines from the latest log file."""
    latest_log = None
    last_known_file = None
    file = None
    flag_check_interval = 2  # Check for flags every 2 seconds
    last_flag_check = time.time()

    while True:
        try:
            # Check for restart/stop flags and emit messages
            current_time = time.time()
            if current_time - last_flag_check >= flag_check_interval:
                if os.path.exists('restart.flag'):
                    socketio.emit('log_update', {'data': '\n<span style="color: #ffc107;">⚠️ RESTART SIGNAL DETECTED - Bot is restarting...</span>\n'}, namespace='/')
                if os.path.exists('stop.flag'):
                    socketio.emit('log_update', {'data': '\n<span style="color: #dc3545;">🛑 STOP SIGNAL DETECTED - Bot is shutting down...</span>\n'}, namespace='/')
                last_flag_check = current_time
            
            latest_log = get_latest_log_file()

            if latest_log != last_known_file:
                if file:
                    file.close()
                if latest_log:
                    socketio.emit('log_update', {'data': f'\n<span style="color: #0dcaf0;">--- Switched to new log file: {os.path.basename(latest_log)} ---</span>\n'}, namespace='/')
                    # --- FIX: Open with error handling for encoding issues ---
                    try:
                        file = open(latest_log, 'r', encoding='utf-8', errors='ignore')
                        # Go to the end of the file
                        file.seek(0, 2)
                    except (IOError, OSError) as e:
                        print(f"[Web Dashboard] Error opening log file {latest_log}: {e}")
                        file = None
                last_known_file = latest_log

            if file:
                try:
                    line = file.readline()
                    if not line:
                        time.sleep(0.1)
                        continue
                    
                    # Add feature badges to log lines
                    enhanced_line = line
                    line_lower = line.lower()
                    
                    # Check for feature keywords and add badges
                    if 'werwolf' in line_lower or 'werewolf' in line_lower:
                        enhanced_line = '<span class="badge bg-danger me-1">Werwolf</span>' + line
                    elif 'wrapped' in line_lower:
                        enhanced_line = '<span class="badge bg-success me-1">Wrapped</span>' + line
                    elif 'admin' in line_lower and ('command' in line_lower or 'slash' in line_lower):
                        enhanced_line = '<span class="badge bg-warning me-1">Admin</span>' + line
                    elif 'chat' in line_lower or 'conversation' in line_lower:
                        enhanced_line = '<span class="badge bg-info me-1">Chat</span>' + line
                    elif 'level' in line_lower or 'xp' in line_lower:
                        enhanced_line = '<span class="badge bg-primary me-1">Leveling</span>' + line
                    elif 'economy' in line_lower or 'coin' in line_lower:
                        enhanced_line = '<span class="badge bg-secondary me-1">Economy</span>' + line
                    
                    socketio.emit('log_update', {'data': enhanced_line}, namespace='/')
                except (IOError, OSError) as e:
                    print(f"[Web Dashboard] Error reading log file: {e}")
                    file = None
                    time.sleep(1)
            else:
                # No log file found, wait a bit before checking again
                time.sleep(1)
        except Exception as e:
            print(f"[Web Dashboard] Unexpected error in follow_log_file: {e}")
            time.sleep(1)

@socketio.on('connect')
def handle_connect():
    """Handles a new client connecting via WebSocket."""
    print("Client connected to WebSocket")
    emit('log_update', {'data': '--- Console stream connected ---\n'})

@app.route('/')
def index():
    """Renders the main dashboard page."""
    return render_template('index.html')

@app.route('/config', methods=['GET', 'POST'])
def config_editor():
    """Renders the config editor and handles saving changes."""
    config_path = 'config/config.json'
    if request.method == 'POST':
        try:
            # Get raw text from the form and parse it as JSON
            raw_config = request.form['config_text']
            parsed_config = json.loads(raw_config)
            
            # Write the formatted JSON back to the file
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(parsed_config, f, indent=2)
            
            flash('Configuration saved successfully!', 'success')
        except json.JSONDecodeError:
            flash('Error: Invalid JSON format. Changes were not saved.', 'danger')
        except Exception as e:
            flash(f'An error occurred: {e}', 'danger')
        return redirect(url_for('config_editor'))

    # For GET request
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_content = f.read()
    except FileNotFoundError:
        config_content = "{}"
        flash(f"Warning: '{config_path}' not found. A new one will be created on save.", 'warning')
    
    return render_template('config.html', config_content=config_content)


@app.route('/system_prompt', methods=['GET', 'POST'])
def system_prompt_editor():
    """Renders the system prompt editor and handles saving changes."""
    prompt_path = 'config/system_prompt.txt'
    if request.method == 'POST':
        try:
            # Get raw text from the form
            prompt_text = request.form['prompt_text']
            
            # Write the text back to the file
            with open(prompt_path, 'w', encoding='utf-8') as f:
                f.write(prompt_text)
            
            flash('System prompt saved successfully!', 'success')
        except Exception as e:
            flash(f'An error occurred: {e}', 'danger')
        return redirect(url_for('system_prompt_editor'))

    # For GET request
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt_content = f.read()
    except FileNotFoundError:
        prompt_content = ""
        flash(f"Warning: '{prompt_path}' not found. A new one will be created on save.", 'warning')
    
    return render_template('system_prompt.html', prompt_content=prompt_content)

@app.route('/database', methods=['GET'])
def database_viewer():
    """Renders the database viewer page with dynamic table selection."""
    selected_table = request.args.get('table', None)
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    
    all_tables = []
    table_data = None
    total_rows = 0
    total_pages = 0
    
    if not db_helpers.db_pool:
        return render_template('database.html', 
                             all_tables=[], 
                             selected_table=None, 
                             table_data=None,
                             error='Database pool not initialized')
    
    conn = None
    cursor = None
    try:
        # Get all tables
        conn = db_helpers.get_db_connection()
        if not conn:
            return render_template('database.html', 
                                 all_tables=[], 
                                 selected_table=None, 
                                 table_data=None,
                                 error='Failed to get database connection')
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SHOW TABLES")
        all_tables = [list(row.values())[0] for row in cursor.fetchall()]
        
        # If a table is selected, fetch its data
        if selected_table and selected_table in all_tables:
            # Get total row count
            cursor.execute(f"SELECT COUNT(*) as count FROM {selected_table}")
            total_rows = cursor.fetchone()['count']
            total_pages = (total_rows + per_page - 1) // per_page
            
            # Fetch paginated data
            offset = (page - 1) * per_page
            query = f"SELECT * FROM {selected_table} LIMIT {per_page} OFFSET {offset}"
            cursor.execute(query)
            raw_data = cursor.fetchall()
            # Convert Decimal values to int/float for proper JSON serialization in templates
            table_data = [db_helpers.convert_decimals(row) for row in raw_data]
    except Exception as e:
        logger.error(f"Error in database viewer: {e}")
        return render_template('database.html', 
                             all_tables=all_tables, 
                             selected_table=selected_table, 
                             table_data=None,
                             error=str(e))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return render_template('database.html', 
                         all_tables=all_tables, 
                         selected_table=selected_table, 
                         table_data=table_data,
                         total_rows=total_rows,
                         total_pages=total_pages,
                         current_page=page,
                         per_page=per_page)

@app.route('/ai_usage', methods=['GET'])
def ai_usage_viewer():
    """Renders the AI usage page."""
    if not db_helpers.db_pool:
        usage_data = [{'error': 'Database pool not initialized'}]
        return render_template('ai_usage.html', usage_data=usage_data)
    
    conn = None
    cursor = None
    try:
        conn = db_helpers.get_db_connection()
        if not conn:
            usage_data = [{'error': 'Failed to get database connection'}]
            return render_template('ai_usage.html', usage_data=usage_data)
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT usage_date, model_name, call_count, input_tokens, output_tokens FROM api_usage ORDER BY usage_date DESC, model_name ASC")
        raw_data = cursor.fetchall()
        # Convert Decimal values for proper JSON serialization
        usage_data = [db_helpers.convert_decimals(row) for row in raw_data]
    except Exception as e:
        logger.error(f"Error fetching AI usage: {e}")
        usage_data = [{'error': str(e)}]
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        
    return render_template('ai_usage.html', usage_data=usage_data)

@app.route('/ai_dashboard', methods=['GET'])
def ai_dashboard():
    """Renders the AI usage dashboard with statistics and charts."""
    from modules.db_helpers import get_ai_usage_stats
    
    try:
        # Get stats for different time periods
        stats_7days = run_async(get_ai_usage_stats(7))
        stats_30days = run_async(get_ai_usage_stats(30))
        stats_all = run_async(get_ai_usage_stats(365))
        
        # Calculate totals
        total_calls = sum(stat['total_calls'] for stat in stats_all)
        total_tokens = sum(stat['total_input_tokens'] + stat['total_output_tokens'] for stat in stats_all)
        total_cost = sum(stat['total_cost'] for stat in stats_all)
        
        return render_template('ai_dashboard.html',
                             stats_7days=stats_7days,
                             stats_30days=stats_30days,
                             stats_all=stats_all,
                             total_calls=total_calls,
                             total_tokens=total_tokens,
                             total_cost=total_cost)
    except Exception as e:
        print(f"Error loading AI dashboard: {e}")
        return render_template('ai_dashboard.html',
                             stats_7days=[],
                             stats_30days=[],
                             stats_all=[],
                             total_calls=0,
                             total_tokens=0,
                             total_cost=0,
                             error=str(e))

# --- API Endpoints for Bot Control ---

@app.route('/api/bot-status', methods=['GET'])
def api_bot_status():
    """API endpoint to get the current status of the bot."""
    status_file = 'config/bot_status.json'
    try:
        if os.path.exists(status_file):
            # --- FIX: Use utf-8-sig to handle potential BOM from PowerShell ---
            with open(status_file, 'r', encoding='utf-8-sig') as f:
                return jsonify(json.load(f))
        else:
            return jsonify({'status': 'Unknown', 'message': 'Status file not found.'})
    except Exception as e:
        return jsonify({'status': 'Error', 'message': str(e)}), 500

@app.route('/api/sync-db', methods=['POST'])
def api_sync_db():
    """API endpoint to trigger database synchronization."""
    try:
        message = sync_database_changes()
        return jsonify({'status': 'success', 'message': message})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/update-bot', methods=['POST'])
def api_update_bot():
    """API endpoint to trigger a git pull."""
    try:
        message = update_bot_from_git()
        return jsonify({'status': 'success', 'message': message})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/restart-bot', methods=['POST'])
def api_restart_bot():
    """API endpoint to restart the bot."""
    # This is now handled by creating a flag file that the maintenance script detects.
    # This is more reliable than trying to find and kill/restart processes from Python.
    try:
        with open('restart.flag', 'w') as f:
            f.write('1')
        message = "Restart signal sent to the maintenance script. The bot will restart shortly."
        print(message)
        return jsonify({'status': 'success', 'message': message})
    except Exception as e:
        error_message = f"Failed to create restart flag: {e}"
        print(error_message)
        return jsonify({'status': 'error', 'message': error_message}), 500

@app.route('/api/stop-bot', methods=['POST'])
def api_stop_bot():
    """API endpoint to stop the bot and maintenance scripts."""
    try:
        message = stop_bot_processes()
        return jsonify({'status': 'success', 'message': message})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/ai-usage', methods=['GET'])
def api_ai_usage():
    """API endpoint to get AI usage statistics with detailed breakdown."""
    try:
        days = int(request.args.get('days', 30))
        
        # Import here to avoid circular import
        from modules.db_helpers import get_ai_usage_stats
        from decimal import Decimal
        
        # Run async function in sync context
        stats = run_async(get_ai_usage_stats(days))
        
        # Group by model and feature for better display
        by_model = {}
        by_feature = {}
        total_calls = 0
        total_tokens = 0
        
        for stat in stats:
            model = stat.get('model_name', 'Unknown')
            feature = stat.get('feature', 'Unknown')
            calls = int(stat.get('total_calls', 0))
            input_tok = int(stat.get('total_input_tokens', 0))
            output_tok = int(stat.get('total_output_tokens', 0))
            cost = float(stat.get('total_cost', 0.0)) if isinstance(stat.get('total_cost', 0.0), (Decimal, int, float, str)) else 0.0
            
            # Aggregate by model
            if model not in by_model:
                by_model[model] = {'calls': 0, 'input_tokens': 0, 'output_tokens': 0, 'cost': 0.0, 'features': {}}
            by_model[model]['calls'] += calls
            by_model[model]['input_tokens'] += input_tok
            by_model[model]['output_tokens'] += output_tok
            by_model[model]['cost'] += cost
            by_model[model]['features'][feature] = {
                'calls': calls,
                'input_tokens': input_tok,
                'output_tokens': output_tok,
                'cost': cost
            }
            
            # Aggregate by feature
            if feature not in by_feature:
                by_feature[feature] = {'calls': 0, 'cost': 0.0, 'models': {}}
            by_feature[feature]['calls'] += calls
            by_feature[feature]['cost'] += cost
            by_feature[feature]['models'][model] = calls
            
            total_calls += calls
            total_tokens += input_tok + output_tok
        
        return jsonify({
            'status': 'success',
            'data': stats,
            'by_model': by_model,
            'by_feature': by_feature,
            'summary': {
                'total_calls': total_calls,
                'total_tokens': total_tokens,
                'total_cost': sum(m['cost'] for m in by_model.values())
            },
            'period_days': days
        })
    except Exception as e:
        logger.error(f"Error fetching AI usage: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/config', methods=['GET'])
def api_get_config():
    """API endpoint to get current configuration."""
    try:
        with open('config/config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        return jsonify({'status': 'success', 'config': config})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/config/model', methods=['POST'])
def api_change_model():
    """API endpoint to change the AI model."""
    try:
        data = request.get_json()
        provider = data.get('provider')
        model = data.get('model')
        
        if not provider or not model:
            return jsonify({'status': 'error', 'message': 'Provider and model are required'}), 400
        
        # Load current config
        with open('config/config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Update the configuration
        config['api']['provider'] = provider
        if provider == 'gemini':
            config['api']['gemini']['model'] = model
        elif provider == 'openai':
            config['api']['openai']['chat_model'] = model
        
        # Save updated config
        with open('config/config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        
        return jsonify({
            'status': 'success',
            'message': f'Model changed to {provider}/{model}. Restart bot to apply changes.'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/config/setting', methods=['POST'])
def api_update_setting():
    """API endpoint to update a specific config setting."""
    try:
        data = request.get_json()
        path = data.get('path')  # e.g., "api.gemini.generation_config.temperature"
        value = data.get('value')
        
        if not path:
            return jsonify({'status': 'error', 'message': 'Path is required'}), 400
        
        # Load current config
        with open('config/config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Navigate and update the nested value
        keys = path.split('.')
        current = config
        for key in keys[:-1]:
            current = current[key]
        current[keys[-1]] = value
        
        # Save updated config
        with open('config/config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        
        return jsonify({
            'status': 'success',
            'message': f'Setting {path} updated successfully.'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/wrapped_stats', methods=['GET'])
def api_wrapped_stats():
    """API endpoint to get wrapped registration statistics."""
    try:
        from modules.db_helpers import get_wrapped_registrations, get_user_wrapped_stats
        from datetime import datetime
        
        async def fetch_stats():
            registrations = await get_wrapped_registrations()
            stat_period = datetime.now().strftime('%Y-%m')
            
            # Add stats for each registered user
            for user in registrations:
                stats = await get_user_wrapped_stats(user['user_id'], stat_period)
                user['message_count'] = stats.get('message_count', 0) if stats else 0
                user['vc_minutes'] = stats.get('minutes_in_vc', 0) if stats else 0
            
            return registrations
        
        # Run async function
        registrations = run_async(fetch_stats())
        
        return jsonify({'registrations': registrations})
    except Exception as e:
        print(f"[API] Error fetching wrapped stats: {e}")
        return jsonify({'error': str(e), 'registrations': []}), 500

@app.route('/api/level_leaderboard', methods=['GET'])
def api_level_leaderboard():
    """API endpoint to get level leaderboard."""
    try:
        from modules.db_helpers import get_level_leaderboard
        
        async def fetch_leaderboard():
            leaderboard, error = await get_level_leaderboard()
            return leaderboard if not error else []
        
        leaderboard = run_async(fetch_leaderboard())
        
        return jsonify({'leaderboard': leaderboard})
    except Exception as e:
        print(f"[API] Error fetching level leaderboard: {e}")
        return jsonify({'error': str(e), 'leaderboard': []}), 500

@app.route('/api/ww_leaderboard', methods=['GET'])
def api_ww_leaderboard():
    """API endpoint to get Werwolf leaderboard."""
    try:
        from modules.db_helpers import get_leaderboard
        
        async def fetch_leaderboard():
            leaderboard, error = await get_leaderboard()
            return leaderboard if not error else []
        
        leaderboard = run_async(fetch_leaderboard())
        
        return jsonify({'leaderboard': leaderboard})
    except Exception as e:
        print(f"[API] Error fetching werwolf leaderboard: {e}")
        return jsonify({'error': str(e), 'leaderboard': []}), 500


# ========== Activity Feed Routes ==========

@app.route('/activity', methods=['GET'])
def activity_page():
    """Renders the activity feed page showing recent bot activity."""
    return render_template('activity.html')


@app.route('/api/activity/recent', methods=['GET'])
def api_recent_activity():
    """API endpoint to get recent bot activity from various sources."""
    try:
        limit = int(request.args.get('limit', 50))
        activity_type = request.args.get('type', 'all')
        
        if not db_helpers.db_pool:
            return jsonify({'error': 'Database not available', 'activities': []}), 500
        
        conn = db_helpers.get_db_connection()
        if not conn:
            logger.error("Failed to get database connection")
            return jsonify({'error': 'Failed to get database connection'}), 500
        cursor = conn.cursor(dictionary=True)
        activities = []
        
        try:
            # Validate and sanitize limit (must be positive integer, max 100)
            limit = max(1, min(100, int(limit)))
            
            # Get recent AI activity from ai_model_usage (aggregated by day)
            if activity_type in ['all', 'ai']:
                ai_activity = safe_db_query(cursor, """
                    SELECT 
                        'ai_chat' as activity_type,
                        NULL as user_id,
                        NULL as channel_id,
                        CONCAT(model_name, ': ', call_count, ' calls, ', feature) as preview,
                        usage_date as activity_time,
                        'AI Chat' as category
                    FROM ai_model_usage
                    ORDER BY usage_date DESC
                    LIMIT %s
                """, params=(limit,), default=[], fetch_all=True)
                activities.extend(ai_activity or [])
            
            # Get recent economy transactions
            if activity_type in ['all', 'economy']:
                econ_activity = safe_db_query(cursor, """
                    SELECT 
                        'transaction' as activity_type,
                        user_id,
                        NULL as channel_id,
                        CONCAT(transaction_type, ': ', amount, ' coins') as preview,
                        created_at as activity_time,
                        'Economy' as category
                    FROM transaction_history
                    ORDER BY created_at DESC
                    LIMIT %s
                """, params=(limit,), default=[], fetch_all=True)
                activities.extend(econ_activity or [])
            
            # Get recent game activity - Detective
            if activity_type in ['all', 'games']:
                detective_activity = safe_db_query(cursor, """
                    SELECT 
                        'game_detective' as activity_type,
                        user_id,
                        NULL as channel_id,
                        CONCAT('Cases solved: ', cases_solved) as preview,
                        last_played_at as activity_time,
                        'Detective Game' as category
                    FROM detective_user_stats
                    WHERE last_played_at IS NOT NULL
                    ORDER BY last_played_at DESC
                    LIMIT %s
                """, params=(limit,), default=[], fetch_all=True)
                activities.extend(detective_activity or [])
            
            # Get recent casino games - Blackjack
            if activity_type in ['all', 'games']:
                blackjack_activity = safe_db_query(cursor, """
                    SELECT 
                        'game_blackjack' as activity_type,
                        user_id,
                        NULL as channel_id,
                        CONCAT('Bet: ', bet_amount, ' | Result: ', result) as preview,
                        played_at as activity_time,
                        'Blackjack' as category
                    FROM blackjack_games
                    WHERE played_at IS NOT NULL
                    ORDER BY played_at DESC
                    LIMIT %s
                """, params=(limit,), default=[], fetch_all=True)
                activities.extend(blackjack_activity or [])
            
            # Get recent user level ups from user_stats
            if activity_type in ['all', 'leveling']:
                level_activity = safe_db_query(cursor, """
                    SELECT 
                        'level_up' as activity_type,
                        user_id,
                        NULL as channel_id,
                        CONCAT('Level ', level, ' (', xp, ' XP)') as preview,
                        updated_at as activity_time,
                        'Leveling' as category
                    FROM user_stats
                    WHERE stat_period = DATE_FORMAT(NOW(), '%Y-%m')
                    AND level > 1
                    ORDER BY updated_at DESC
                    LIMIT %s
                """, params=(limit,), default=[], fetch_all=True)
                activities.extend(level_activity or [])
            
            # Get user display names
            user_ids = list(set([a.get('user_id') for a in activities if a.get('user_id')]))
            user_names = {}
            if user_ids:
                # Get from players table using parameterized IN clause
                # Note: placeholders is safe as it only contains '%s' characters
                # The actual user_ids are passed as parameters to prevent SQL injection
                placeholders = ','.join(['%s'] * len(user_ids))
                cursor.execute(
                    f"SELECT discord_id, display_name FROM players WHERE discord_id IN ({placeholders})",
                    tuple(user_ids)
                )
                for row in cursor.fetchall():
                    user_names[row['discord_id']] = row['display_name']
            
            # Add display names to activities
            for activity in activities:
                uid = activity.get('user_id')
                activity['display_name'] = user_names.get(uid, f'User {uid}') if uid else 'Unknown'
                # Convert datetime to string for JSON
                if activity.get('activity_time'):
                    activity['activity_time'] = str(activity['activity_time'])
            
            # Sort by time (most recent first)
            activities.sort(key=lambda x: x.get('activity_time', ''), reverse=True)
            activities = activities[:limit]
            
            return jsonify({
                'status': 'success',
                'activities': activities,
                'count': len(activities)
            })
            
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        logger.error(f"Error fetching recent activity: {e}")
        return jsonify({'error': str(e), 'activities': []}), 500


@app.route('/api/activity/stats', methods=['GET'])
def api_activity_stats():
    """API endpoint to get activity statistics."""
    try:
        if not db_helpers.db_pool:
            return jsonify({'error': 'Database not available'}), 500
        
        conn = db_helpers.get_db_connection()
        if not conn:
            logger.error("Failed to get database connection")
            return jsonify({'error': 'Failed to get database connection'}), 500
        cursor = conn.cursor(dictionary=True)
        
        try:
            stats = {
                'today': {},
                'week': {},
                'total': {}
            }
            
            # AI calls today - use ai_model_usage table
            result = safe_db_query(cursor, """
                SELECT COALESCE(SUM(call_count), 0) as count FROM ai_model_usage 
                WHERE usage_date = CURDATE()
            """)
            stats['today']['ai_chats'] = result.get('count', 0) if result else 0
            
            # Transactions today  
            result = safe_db_query(cursor, """
                SELECT COUNT(*) as count FROM transaction_history 
                WHERE DATE(created_at) = CURDATE()
            """)
            stats['today']['transactions'] = result.get('count', 0) if result else 0
            
            # Games played today - query each table individually to handle missing tables
            # Using explicit queries for each table (no string interpolation) for security
            games_count = 0
            # Blackjack games
            result = safe_db_query(cursor, """
                SELECT COUNT(*) as count FROM blackjack_games 
                WHERE DATE(played_at) = CURDATE()
            """)
            if result and result.get('count'):
                games_count += int(result.get('count', 0))
            # Roulette games
            result = safe_db_query(cursor, """
                SELECT COUNT(*) as count FROM roulette_games 
                WHERE DATE(played_at) = CURDATE()
            """)
            if result and result.get('count'):
                games_count += int(result.get('count', 0))
            # Mines games
            result = safe_db_query(cursor, """
                SELECT COUNT(*) as count FROM mines_games 
                WHERE DATE(played_at) = CURDATE()
            """)
            if result and result.get('count'):
                games_count += int(result.get('count', 0))
            stats['today']['games'] = games_count
            
            # Active users today - use ai_model_usage table instead of non-existent ai_conversation_history
            result = safe_db_query(cursor, """
                SELECT COALESCE(SUM(call_count), 0) as count FROM ai_model_usage 
                WHERE usage_date = CURDATE()
            """)
            stats['today']['active_users'] = result.get('count', 0) if result else 0
            
            # Total counts - use ai_model_usage table
            result = safe_db_query(cursor, "SELECT COALESCE(SUM(call_count), 0) as count FROM ai_model_usage")
            stats['total']['ai_chats'] = result.get('count', 0) if result else 0
            
            result = safe_db_query(cursor, "SELECT COUNT(*) as count FROM transaction_history")
            stats['total']['transactions'] = result.get('count', 0) if result else 0
            
            result = safe_db_query(cursor, "SELECT COUNT(*) as count FROM players")
            stats['total']['users'] = result.get('count', 0) if result else 0
            
            return jsonify({
                'status': 'success',
                'stats': stats
            })
            
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        logger.error(f"Error fetching activity stats: {e}")
        return jsonify({'error': str(e)}), 500

def restart_bot():
    """Creates a flag file to signal the maintenance script to restart the bot."""
    with open('restart.flag', 'w') as f:
        f.write('1')
    return "Restart signal sent. The bot will be restarted by the maintenance script."

def stop_bot_processes():
    """Creates a flag file to signal the maintenance script to stop everything."""
    with open('stop.flag', 'w') as f:
        f.write('1')
    return "Stop signal sent. All bot-related processes will be shut down by the maintenance script."

def update_bot_from_git():
    """Triggers a git pull. The maintenance script will handle the restart."""
    # The maintenance script automatically pulls, so we just need to trigger a restart.
    return restart_bot()

def sync_database_changes():
    """This is now handled automatically by the bot scripts on shutdown/restart."""
    return "Database synchronization is handled automatically by the start/maintenance scripts. Trigger a restart to sync."


# ========== Admin API Endpoints ==========

@app.route('/api/admin/reload_config', methods=['POST'])
def admin_reload_config():
    """Reload bot configuration."""
    try:
        # Reload config in the dashboard process (just verify it's valid)
        with open('config/config.json', 'r', encoding='utf-8') as f:
            _ = json.load(f)  # Just validate the JSON is parseable
        
        # Signal bot to reload config (if running)
        try:
            with open('config/reload_config.flag', 'w') as f:
                f.write(str(time.time()))
        except IOError as e:
            print(f"[Web Dashboard] Could not create reload_config.flag: {e}")
        
        return jsonify({'success': True, 'message': 'Config reloaded successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/admin/save_history', methods=['POST'])
def admin_save_history():
    """Save chat history - requires bot to be running."""
    return jsonify({
        'success': False, 
        'message': 'This feature requires direct bot access. Use the Discord slash command /admin save_history instead.'
    }), 501

@app.route('/api/admin/clear_history', methods=['POST'])
def admin_clear_history():
    """Clear chat history for a channel."""
    try:
        from modules.db_helpers import clear_channel_history
        
        data = request.json
        channel_id = int(data.get('channel_id'))
        
        async def clear_history():
            deleted_count, error = await clear_channel_history(channel_id)
            if error:
                return {'success': False, 'message': f'Error: {error}'}
            return {'success': True, 'message': f'Deleted {deleted_count} messages'}
        
        result = run_async(clear_history())
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/admin/delete_memory', methods=['POST'])
def admin_delete_memory():
    """Delete bot memory for a user."""
    try:
        from modules.db_helpers import update_relationship_summary
        
        data = request.json
        user_id = int(data.get('user_id'))
        
        async def delete_user_memory():
            await update_relationship_summary(user_id, None)
            return {'success': True, 'message': f'Memory deleted for user {user_id}'}
        
        result = run_async(delete_user_memory())
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/admin/wrapped_dates', methods=['GET'])
def admin_wrapped_dates():
    """Get next wrapped event dates."""
    try:
        from datetime import datetime, timezone, timedelta
        
        # Load config
        with open('config/config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Calculate dates
        now = datetime.now(timezone.utc)
        first_day_of_current_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_first_day = (first_day_of_current_month - timedelta(days=1)).replace(day=1)
        stat_period = last_month_first_day.strftime('%Y-%m')
        
        event_creation_offset = config.get('wrapped', {}).get('event_creation_offset', 1)
        release_offset = config.get('wrapped', {}).get('release_offset', 3)
        
        event_creation_date = first_day_of_current_month + timedelta(days=event_creation_offset)
        release_date = first_day_of_current_month + timedelta(days=release_offset)
        
        return jsonify({
            'success': True,
            'stat_period': stat_period,
            'event_creation_date': event_creation_date.isoformat(),
            'release_date': release_date.isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/admin/create_test_event', methods=['POST'])
def admin_create_test_event():
    """Create test event - requires bot access."""
    return jsonify({
        'success': False,
        'message': 'This feature requires direct bot access. Use the Discord slash command /admin view_event instead.'
    }), 501

@app.route('/api/admin/preview_wrapped', methods=['POST'])
def admin_preview_wrapped():
    """Send wrapped preview - requires bot access."""
    return jsonify({
        'success': False,
        'message': 'This feature requires direct bot access. Use the Discord slash command /admin view_wrapped instead.'
    }), 501

@app.route('/api/admin/delete_user_data', methods=['POST'])
def admin_delete_user_data():
    """Delete all data for a specific user from the database."""
    try:
        
        data = request.json
        user_id = int(data.get('user_id'))
        confirm = data.get('confirm', False)
        
        if not confirm:
            return jsonify({
                'success': False,
                'message': 'Confirmation required. Set confirm=true to proceed with deletion.'
            }), 400
        
        if not db_helpers.db_pool:
            return jsonify({
                'success': False,
                'message': 'Database pool not initialized'
            }), 500
        
        conn = None
        cursor = None
        deleted_tables = []
        
        try:
            conn = db_helpers.get_db_connection()
            if not conn:
                logger.error("Failed to get database connection")
                return jsonify({'error': 'Failed to get database connection'}), 500
            cursor = conn.cursor()
            
            # List of tables to delete user data from
            tables_to_clean = [
                ('user_stats', 'user_id'),
                ('user_privacy_settings', 'user_id'),
                ('detective_user_stats', 'user_id'),
                ('detective_user_progress', 'user_id'),
                ('trolly_problem_responses', 'user_id'),
                ('transactions', 'user_id'),
                ('user_quests', 'user_id'),
                ('user_items', 'user_id'),
                ('user_portfolios', 'user_id'),
                ('blackjack_games', 'user_id'),
                ('roulette_games', 'user_id'),
                ('mines_games', 'user_id'),
                ('russian_roulette_games', 'user_id'),
                ('werwolf_user_stats', 'user_id'),
                ('ai_model_usage', 'user_id'),
                ('conversation_context', 'user_id'),
                ('user_relationships', 'user_id'),
                ('wrapped_events', 'user_id'),
                ('wrapped_registrations', 'user_id')
            ]
            
            for table, id_column in tables_to_clean:
                try:
                    # Check if table exists
                    cursor.execute(f"SHOW TABLES LIKE '{table}'")
                    if cursor.fetchone():
                        cursor.execute(f"DELETE FROM {table} WHERE {id_column} = %s", (user_id,))
                        deleted_count = cursor.rowcount
                        if deleted_count > 0:
                            deleted_tables.append(f"{table} ({deleted_count} rows)")
                except Exception as e:
                    logger.warning(f"Could not delete from {table}: {e}")
            
            conn.commit()
            
            logger.info(f"Deleted all data for user {user_id} from {len(deleted_tables)} tables")
            
            return jsonify({
                'success': True,
                'message': f'Successfully deleted all data for user {user_id}',
                'deleted_from': deleted_tables,
                'user_id': user_id
            })
            
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
                
    except ValueError:
        return jsonify({
            'success': False,
            'message': 'Invalid user_id. Must be a number.'
        }), 400
    except Exception as e:
        logger.error(f"Error deleting user data: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/maintenance/logs', methods=['GET'])
def api_maintenance_logs():
    """Get recent maintenance script activity."""
    try:
        # Get the most recent maintenance log files
        log_files = []
        if os.path.exists(LOG_DIR):
            all_logs = [f for f in os.listdir(LOG_DIR) if f.startswith('maintenance_') and f.endswith('.log')]
            all_logs.sort(reverse=True)
            log_files = all_logs[:5]  # Get last 5 maintenance logs
        
        logs_data = []
        for log_file in log_files:
            log_path = os.path.join(LOG_DIR, log_file)
            try:
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    # Extract key activities
                    activities = []
                    for line in content.split('\n'):
                        if any(keyword in line.lower() for keyword in ['restart', 'update', 'backup', 'commit', 'pull', 'stopped', 'started']):
                            activities.append(line.strip())
                    
                    logs_data.append({
                        'filename': log_file,
                        'timestamp': log_file.replace('maintenance_', '').replace('.log', ''),
                        'activities': activities[:20]  # Limit to 20 most recent activities
                    })
            except Exception as e:
                print(f"Error reading log file {log_file}: {e}")
        
        return jsonify({
            'status': 'success',
            'logs': logs_data
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/logs/recent', methods=['GET'])
def api_recent_logs():
    """Get recent log entries with filtering."""
    try:
        level = request.args.get('level', 'all')
        limit = int(request.args.get('limit', 100))
        
        latest_log = get_latest_log_file()
        if not latest_log:
            return jsonify({'status': 'success', 'logs': []})
        
        logs = []
        with open(latest_log, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            # Get last N lines
            recent_lines = lines[-limit:] if len(lines) > limit else lines
            
            for line in recent_lines:
                line_lower = line.lower()
                # Filter by level
                if level != 'all':
                    if level == 'error' and 'error' not in line_lower:
                        continue
                    elif level == 'warning' and 'warning' not in line_lower:
                        continue
                    elif level == 'info' and 'info' not in line_lower:
                        continue
                
                logs.append(line.strip())
        
        return jsonify({
            'status': 'success',
            'logs': logs,
            'count': len(logs)
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ========== Logs Viewer Routes ==========

@app.route('/logs', methods=['GET'])
def logs_page():
    """Renders the logs viewer page showing all available log files."""
    return render_template('logs.html')


@app.route('/api/logs/files', methods=['GET'])
def api_log_files():
    """API endpoint to list all available log files."""
    try:
        if not os.path.exists(LOG_DIR):
            return jsonify({'status': 'success', 'files': []})
        
        log_files = []
        for f in os.listdir(LOG_DIR):
            if f.endswith('.log'):
                file_path = os.path.join(LOG_DIR, f)
                try:
                    stat = os.stat(file_path)
                    log_files.append({
                        'name': f,
                        'size': stat.st_size,
                        'modified': stat.st_mtime,
                        'modified_str': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_mtime))
                    })
                except OSError:
                    continue
        
        # Sort by modification time, most recent first
        log_files.sort(key=lambda x: x['modified'], reverse=True)
        
        return jsonify({
            'status': 'success',
            'files': log_files,
            'count': len(log_files)
        })
    except Exception as e:
        logger.error(f"Error listing log files: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/logs/content/<filename>', methods=['GET'])
def api_log_content(filename):
    """API endpoint to get the content of a specific log file."""
    try:
        # Validate filename to prevent directory traversal attacks
        # Only allow alphanumeric, underscore, and .log extension (no hyphens)
        if not re.match(r'^[a-zA-Z0-9_]+\.log$', filename):
            return jsonify({'status': 'error', 'message': 'Invalid filename'}), 400
        
        file_path = os.path.join(LOG_DIR, filename)
        
        # Ensure the resolved path is still within LOG_DIR
        real_path = os.path.realpath(file_path)
        real_log_dir = os.path.realpath(LOG_DIR)
        if not real_path.startswith(real_log_dir):
            return jsonify({'status': 'error', 'message': 'Invalid file path'}), 400
        
        if not os.path.exists(file_path):
            return jsonify({'status': 'error', 'message': 'File not found'}), 404
        
        # Get optional parameters
        lines = request.args.get('lines', type=int, default=1000)
        offset = request.args.get('offset', type=int, default=0)
        
        # Limit lines to reasonable max
        lines = min(lines, 5000)
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
            total_lines = len(all_lines)
            
            # If offset is 0, get the last N lines
            if offset == 0:
                content = all_lines[-lines:] if total_lines > lines else all_lines
                start_line = max(0, total_lines - lines)
            else:
                # Get lines starting from offset
                content = all_lines[offset:offset + lines]
                start_line = offset
        
        return jsonify({
            'status': 'success',
            'filename': filename,
            'content': ''.join(content),
            'total_lines': total_lines,
            'start_line': start_line,
            'lines_returned': len(content)
        })
    except Exception as e:
        logger.error(f"Error reading log file {filename}: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


# --- RPG Admin Routes ---

@app.route('/rpg_admin', methods=['GET'])
def rpg_admin():
    """RPG Admin page for managing monsters, items, and settings."""
    return render_template('rpg_admin.html')


@app.route('/api/rpg/verify', methods=['GET'])
def verify_rpg_data():
    """Verify RPG data exists and is properly initialized."""
    try:
        if not db_helpers.db_pool:
            return jsonify({'error': 'Database not available'}), 500
        
        conn = db_helpers.get_db_connection()
        if not conn:
            logger.error("Failed to get database connection")
            return jsonify({'error': 'Failed to get database connection'}), 500
        cursor = conn.cursor(dictionary=True)
        
        try:
            verification = {}
            
            # Check items
            cursor.execute("SELECT COUNT(*) as count FROM rpg_items WHERE created_by IS NULL")
            verification['default_items'] = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM rpg_items")
            verification['total_items'] = cursor.fetchone()['count']
            
            # Check monsters
            cursor.execute("SELECT COUNT(*) as count FROM rpg_monsters")
            verification['monsters'] = cursor.fetchone()['count']
            
            # Check players
            cursor.execute("SELECT COUNT(*) as count FROM rpg_players")
            verification['players'] = cursor.fetchone()['count']
            
            # Check today's shop
            from datetime import datetime, timezone
            today = datetime.now(timezone.utc).date()
            cursor.execute("SELECT COUNT(*) as count FROM rpg_daily_shop WHERE shop_date = %s", (today,))
            verification['todays_shop'] = cursor.fetchone()['count']
            
            # Determine status
            status = 'ok'
            messages = []
            
            if verification['default_items'] < 100:
                status = 'warning'
                messages.append(f"Only {verification['default_items']} default items (expected 100+). Reinitialize needed.")
            
            if verification['monsters'] < 20:
                status = 'warning'
                messages.append(f"Only {verification['monsters']} monsters (expected 20+). Reinitialize needed.")
            
            if verification['default_items'] == 0:
                status = 'error'
                messages.append("No default items found. Please restart bot to initialize.")
            
            if verification['monsters'] == 0:
                status = 'error'
                messages.append("No monsters found. Please restart bot to initialize.")
            
            return jsonify({
                'status': status,
                'verification': verification,
                'messages': messages
            })
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error verifying RPG data: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/rpg/stats', methods=['GET'])
def rpg_stats():
    """Get RPG statistics."""
    try:
        if not db_helpers.db_pool:
            return jsonify({'error': 'Database not available'}), 500
        
        conn = db_helpers.get_db_connection()
        if not conn:
            logger.error("Failed to get database connection")
            return jsonify({'error': 'Failed to get database connection'}), 500
        cursor = conn.cursor()
        
        try:
            # Get total players
            cursor.execute("SELECT COUNT(*) FROM rpg_players")
            total_players = cursor.fetchone()[0]
            
            # Get total monsters
            cursor.execute("SELECT COUNT(*) FROM rpg_monsters")
            total_monsters = cursor.fetchone()[0]
            
            # Get total items
            cursor.execute("SELECT COUNT(*) FROM rpg_items")
            total_items = cursor.fetchone()[0]
            
            # Get total gold in circulation
            cursor.execute("SELECT SUM(gold) FROM rpg_players")
            total_gold = cursor.fetchone()[0] or 0
            # Convert Decimal to int for JSON serialization
            total_gold = int(total_gold) if total_gold else 0
            
            return jsonify({
                'total_players': total_players,
                'total_monsters': total_monsters,
                'total_items': total_items,
                'total_gold': int(total_gold)
            })
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error getting RPG stats: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/rpg/items', methods=['GET', 'POST'])
def rpg_items():
    """Get all items or create a new item."""
    try:
        if not db_helpers.db_pool:
            return jsonify({'error': 'Database not available'}), 500
        
        conn = db_helpers.get_db_connection()
        if not conn:
            logger.error("Failed to get database connection")
            return jsonify({'error': 'Failed to get database connection'}), 500
        cursor = conn.cursor(dictionary=True)
        
        if request.method == 'GET':
            # Get all items
            cursor.execute("""
                SELECT id, name, type, rarity, description, damage, damage_type, 
                       price, required_level, durability, effects
                FROM rpg_items
                ORDER BY required_level ASC, name ASC
            """)
            raw_items = cursor.fetchall()
            # Convert Decimal values for JSON serialization
            items = [db_helpers.convert_decimals(item) for item in raw_items]
            cursor.close()
            conn.close()
            return jsonify(items)
        
        elif request.method == 'POST':
            # Create new item
            data = request.json
            
            cursor.execute("""
                INSERT INTO rpg_items 
                (name, type, rarity, description, damage, damage_type, price, required_level, effects)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                data['name'],
                data['type'],
                data['rarity'],
                data['description'],
                data.get('damage', 0),
                data.get('damage_type'),
                data['price'],
                data['required_level'],
                data.get('effects')
            ))
            
            conn.commit()
            item_id = cursor.lastrowid
            cursor.close()
            conn.close()
            
            return jsonify({'success': True, 'id': item_id}), 201
            
    except Exception as e:
        logger.error(f"Error with RPG items: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/rpg/items/<int:item_id>', methods=['DELETE'])
def delete_rpg_item(item_id):
    """Delete an item."""
    try:
        if not db_helpers.db_pool:
            return jsonify({'error': 'Database not available'}), 500
        
        conn = db_helpers.get_db_connection()
        if not conn:
            logger.error("Failed to get database connection")
            return jsonify({'error': 'Failed to get database connection'}), 500
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM rpg_items WHERE id = %s", (item_id,))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error deleting RPG item: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/rpg/monsters', methods=['GET', 'POST'])
def rpg_monsters():
    """Get all monsters or create a new monster."""
    try:
        if not db_helpers.db_pool:
            return jsonify({'error': 'Database not available'}), 500
        
        conn = db_helpers.get_db_connection()
        if not conn:
            logger.error("Failed to get database connection")
            return jsonify({'error': 'Failed to get database connection'}), 500
        cursor = conn.cursor(dictionary=True)
        
        if request.method == 'GET':
            # Get all monsters
            cursor.execute("""
                SELECT id, name, world, level, health, strength, defense, speed, 
                       xp_reward, gold_reward, loot_table, spawn_rate, abilities
                FROM rpg_monsters
                ORDER BY world ASC, level ASC, name ASC
            """)
            raw_monsters = cursor.fetchall()
            # Convert Decimal values for JSON serialization
            monsters = [db_helpers.convert_decimals(monster) for monster in raw_monsters]
            cursor.close()
            conn.close()
            return jsonify(monsters)
        
        elif request.method == 'POST':
            # Create new monster
            data = request.json
            
            # Handle optional abilities and loot_table as JSON
            abilities_json = json.dumps(data.get('abilities', []))
            loot_table_json = json.dumps(data.get('loot_table', {}))
            
            cursor.execute("""
                INSERT INTO rpg_monsters 
                (name, world, level, health, strength, defense, speed, xp_reward, gold_reward, abilities, loot_table)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                data['name'],
                data['world'],
                data['level'],
                data['health'],
                data['strength'],
                data['defense'],
                data['speed'],
                data['xp_reward'],
                data['gold_reward'],
                abilities_json,
                loot_table_json
            ))
            
            conn.commit()
            monster_id = cursor.lastrowid
            cursor.close()
            conn.close()
            
            return jsonify({'success': True, 'id': monster_id}), 201
            
    except Exception as e:
        logger.error(f"Error with RPG monsters: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/rpg/monsters/<int:monster_id>', methods=['DELETE'])
def delete_rpg_monster(monster_id):
    """Delete a monster."""
    try:
        if not db_helpers.db_pool:
            return jsonify({'error': 'Database not available'}), 500
        
        conn = db_helpers.get_db_connection()
        if not conn:
            logger.error("Failed to get database connection")
            return jsonify({'error': 'Failed to get database connection'}), 500
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM rpg_monsters WHERE id = %s", (monster_id,))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error deleting RPG monster: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/rpg/init_monsters', methods=['POST'])
def init_rpg_monsters():
    """Reinitialize default monsters."""
    try:
        # Import RPG system to access default monsters
        from modules import rpg_system
        
        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        # First ensure tables exist, then initialize monsters
        loop.run_until_complete(rpg_system.initialize_rpg_tables(db_helpers))
        loop.run_until_complete(rpg_system.initialize_default_monsters(db_helpers))
        loop.close()
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error reinitializing monsters: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/rpg/init_items', methods=['POST'])
def init_rpg_items():
    """Reinitialize default shop items."""
    try:
        # Import RPG system to access default items
        from modules import rpg_system
        
        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        # First ensure tables exist, then initialize items
        loop.run_until_complete(rpg_system.initialize_rpg_tables(db_helpers))
        loop.run_until_complete(rpg_system.initialize_shop_items(db_helpers))
        loop.close()
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error reinitializing items: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/rpg/skill_tree', methods=['GET'])
def get_skill_tree():
    """Get the complete skill tree configuration."""
    try:
        from modules import rpg_system
        
        # Return the skill tree structure
        return jsonify(rpg_system.SKILL_TREE)
    except Exception as e:
        logger.error(f"Error getting skill tree: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/rpg/skill_tree/save', methods=['POST'])
def save_skill_tree():
    """Save the complete skill tree configuration to a JSON file."""
    try:
        from modules import rpg_system
        import json
        
        data = request.json
        
        # Validate the structure
        if not isinstance(data, dict):
            return jsonify({'error': 'Invalid skill tree structure'}), 400
        
        # Update in-memory skill tree
        rpg_system.SKILL_TREE.clear()
        rpg_system.SKILL_TREE.update(data)
        
        # Save to a config file for persistence
        config_path = 'config/skill_tree_config.json'
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Skill tree configuration saved to {config_path}")
        return jsonify({'success': True, 'message': 'Skill tree saved successfully'})
    except Exception as e:
        logger.error(f"Error saving skill tree: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/rpg/skill_tree/load', methods=['POST'])
def load_skill_tree():
    """Load skill tree configuration from file."""
    try:
        from modules import rpg_system
        import json
        
        config_path = 'config/skill_tree_config.json'
        
        if not os.path.exists(config_path):
            return jsonify({'error': 'No saved skill tree configuration found'}), 404
        
        with open(config_path, 'r', encoding='utf-8') as f:
            saved_tree = json.load(f)
        
        # Update in-memory skill tree
        rpg_system.SKILL_TREE.clear()
        rpg_system.SKILL_TREE.update(saved_tree)
        
        logger.info("Skill tree configuration loaded from file")
        return jsonify({'success': True, 'message': 'Skill tree loaded successfully', 'data': saved_tree})
    except Exception as e:
        logger.error(f"Error loading skill tree: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/rpg/skill_tree/<path_key>', methods=['PUT'])
def update_skill_tree_path(path_key):
    """Update a skill tree path configuration."""
    try:
        from modules import rpg_system
        
        if path_key not in rpg_system.SKILL_TREE:
            return jsonify({'error': 'Invalid path'}), 404
        
        data = request.json
        
        # Update the skill tree in memory
        if 'name' in data:
            rpg_system.SKILL_TREE[path_key]['name'] = data['name']
        if 'description' in data:
            rpg_system.SKILL_TREE[path_key]['description'] = data['description']
        if 'emoji' in data:
            rpg_system.SKILL_TREE[path_key]['emoji'] = data['emoji']
        
        return jsonify({'success': True, 'message': 'Skill tree path updated'})
    except Exception as e:
        logger.error(f"Error updating skill tree path: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/rpg/skill_tree/<path_key>/<skill_key>', methods=['PUT'])
def update_skill(path_key, skill_key):
    """Update a specific skill in the skill tree."""
    try:
        from modules import rpg_system
        
        if path_key not in rpg_system.SKILL_TREE:
            return jsonify({'error': 'Invalid path'}), 404
        
        if skill_key not in rpg_system.SKILL_TREE[path_key]['skills']:
            return jsonify({'error': 'Invalid skill'}), 404
        
        data = request.json
        skill = rpg_system.SKILL_TREE[path_key]['skills'][skill_key]
        
        # Update skill properties
        if 'name' in data:
            skill['name'] = data['name']
        if 'description' in data:
            skill['description'] = data['description']
        if 'cost' in data:
            skill['cost'] = int(data['cost'])
        if 'type' in data:
            skill['type'] = data['type']
        if 'requires' in data:
            skill['requires'] = data['requires']
        if 'effect' in data:
            skill['effect'] = data['effect']
        
        return jsonify({'success': True, 'message': 'Skill updated'})
    except Exception as e:
        logger.error(f"Error updating skill: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/rpg/skill_tree/<path_key>/skills', methods=['POST'])
def add_skill_to_path(path_key):
    """Add a new skill to a path."""
    try:
        from modules import rpg_system
        
        if path_key not in rpg_system.SKILL_TREE:
            return jsonify({'error': 'Invalid path'}), 404
        
        data = request.json
        
        # Validate required fields
        if 'skill_key' not in data or 'name' not in data or 'description' not in data:
            return jsonify({'error': 'Missing required fields'}), 400
        
        skill_key = data['skill_key']
        
        # Check if skill already exists
        if skill_key in rpg_system.SKILL_TREE[path_key]['skills']:
            return jsonify({'error': 'Skill already exists'}), 400
        
        # Create new skill
        rpg_system.SKILL_TREE[path_key]['skills'][skill_key] = {
            'name': data['name'],
            'type': data.get('type', 'passive'),
            'description': data['description'],
            'cost': int(data.get('cost', 1)),
            'requires': data.get('requires'),
            'effect': data.get('effect', {})
        }
        
        return jsonify({'success': True, 'message': f'Skill {skill_key} added to {path_key}'})
    except Exception as e:
        logger.error(f"Error adding skill: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/rpg/skill_tree/<path_key>/<skill_key>', methods=['DELETE'])
def delete_skill(path_key, skill_key):
    """Delete a skill from a path."""
    try:
        from modules import rpg_system
        
        if path_key not in rpg_system.SKILL_TREE:
            return jsonify({'error': 'Invalid path'}), 404
        
        if skill_key not in rpg_system.SKILL_TREE[path_key]['skills']:
            return jsonify({'error': 'Skill not found'}), 404
        
        # Delete the skill
        del rpg_system.SKILL_TREE[path_key]['skills'][skill_key]
        
        return jsonify({'success': True, 'message': f'Skill {skill_key} deleted'})
    except Exception as e:
        logger.error(f"Error deleting skill: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/rpg/player/reset', methods=['POST'])
def reset_rpg_player():
    """Reset a player's RPG data to fresh start."""
    try:
        data = request.json
        
        # Validate input
        if not data or 'user_id' not in data:
            return jsonify({
                'success': False,
                'message': 'user_id is required'
            }), 400
        
        # Validate and convert user_id to integer
        try:
            user_id = int(data.get('user_id'))
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'message': 'user_id must be a valid integer'
            }), 400
        
        confirm = data.get('confirm', False)
        
        if not confirm:
            return jsonify({
                'success': False,
                'message': 'Confirmation required. Set confirm=true to proceed with reset.'
            }), 400
        
        if not db_helpers.db_pool:
            return jsonify({
                'success': False,
                'message': 'Database pool not initialized'
            }), 500
        
        conn = None
        cursor = None
        deleted_tables = []
        
        try:
            conn = db_helpers.get_db_connection()
            if not conn:
                logger.error("Failed to get database connection")
                return jsonify({'error': 'Failed to get database connection'}), 500
            cursor = conn.cursor()
            
            # Pre-defined queries for each table to prevent SQL injection
            DELETE_QUERIES = {
                'rpg_players': "DELETE FROM rpg_players WHERE user_id = %s",
                'rpg_inventory': "DELETE FROM rpg_inventory WHERE user_id = %s",
                'rpg_equipped': "DELETE FROM rpg_equipped WHERE user_id = %s",
                'rpg_skill_tree': "DELETE FROM rpg_skill_tree WHERE user_id = %s"
            }
            
            for table_name, delete_query in DELETE_QUERIES.items():
                try:
                    # Check if table exists
                    cursor.execute("SHOW TABLES LIKE %s", (table_name,))
                    if cursor.fetchone():
                        # Delete user data using pre-defined query
                        cursor.execute(delete_query, (user_id,))
                        affected = cursor.rowcount
                        if affected > 0:
                            deleted_tables.append(f"{table_name} ({affected} rows)")
                except Exception as e:
                    logger.warning(f"Error clearing {table_name}: {e}")
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': f'RPG data cleared for user {user_id}',
                'tables_cleared': deleted_tables
            })
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    except Exception as e:
        logger.error(f"Error resetting RPG player: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ========== Economy Dashboard APIs ==========

@app.route('/economy', methods=['GET'])
def economy_dashboard():
    """Renders the economy dashboard page."""
    return render_template('economy.html')


@app.route('/api/economy/stats', methods=['GET'])
def economy_stats():
    """Get overall economy statistics."""
    try:
        if not db_helpers.db_pool:
            return jsonify({'error': 'Database not available'}), 500
        
        conn = db_helpers.get_db_connection()
        if not conn:
            logger.error("Failed to get connection for economy_stats")
            return jsonify({'error': 'Failed to get database connection'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Total coins in circulation (from players table which stores actual balances)
            cursor.execute("SELECT COALESCE(SUM(balance), 0) as total_coins FROM players WHERE balance > 0")
            result = cursor.fetchone()
            total_coins = int(result.get('total_coins', 0)) if result else 0
            
            # Total users with coins
            cursor.execute("SELECT COUNT(*) as total_users FROM players WHERE balance > 0")
            result = cursor.fetchone()
            total_users = result.get('total_users', 0) if result else 0
            
            # Average coins per user
            avg_coins = total_coins / total_users if total_users > 0 else 0
            
            # Richest users from players table
            cursor.execute("""
                SELECT discord_id as user_id, display_name, balance as coins 
                FROM players 
                WHERE balance > 0 
                ORDER BY balance DESC 
                LIMIT 10
            """)
            raw_richest = cursor.fetchall() or []
            # Convert Decimal values for JSON serialization
            richest_users = [db_helpers.convert_decimals(user) for user in raw_richest]
            
            # Recent transactions - use transaction_history table if it exists
            recent_transactions = safe_db_query(cursor, """
                SELECT th.*, p.display_name
                FROM transaction_history th
                LEFT JOIN players p ON th.user_id = p.discord_id
                ORDER BY th.created_at DESC 
                LIMIT 20
            """, default=[], fetch_all=True)
            
            # Transaction volume by type
            transaction_types = safe_db_query(cursor, """
                SELECT transaction_type, COUNT(*) as count, SUM(amount) as total_amount
                FROM transaction_history
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                GROUP BY transaction_type
                ORDER BY total_amount DESC
            """, default=[], fetch_all=True)
            
            return jsonify({
                'total_coins': int(total_coins),
                'total_users': total_users,
                'avg_coins': round(avg_coins, 2),
                'richest_users': richest_users or [],
                'recent_transactions': recent_transactions or [],
                'transaction_types': transaction_types or []
            })
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error getting economy stats: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/economy/stocks', methods=['GET'])
def economy_stocks():
    """Get stock market data."""
    from decimal import Decimal
    
    try:
        if not db_helpers.db_pool:
            return jsonify({'error': 'Database not available'}), 500
        
        conn = db_helpers.get_db_connection()
        if not conn:
            logger.error("Failed to get connection for economy_stocks")
            return jsonify({'error': 'Failed to get database connection'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Get all stocks with calculated change percentage
            stocks = safe_db_query(cursor, """
                SELECT symbol, name, category, current_price, previous_price, trend,
                       last_update, volume_today,
                       CASE 
                           WHEN previous_price > 0 
                           THEN ((current_price - previous_price) / previous_price) * 100
                           ELSE 0
                       END as change_percent,
                       volume_today as volume
                FROM stocks
                ORDER BY symbol ASC
            """, default=[], fetch_all=True)
            
            # Convert Decimal to float for JSON serialization
            for stock in stocks:
                for key in ['current_price', 'previous_price', 'trend', 'change_percent']:
                    if stock.get(key) is not None:
                        if isinstance(stock[key], Decimal):
                            stock[key] = float(stock[key])
            
            # Get top stock holders - join with current month's user_stats
            top_holders = safe_db_query(cursor, """
                SELECT p.stock_symbol as symbol, p.user_id, p.shares as quantity, 
                       u.display_name, u.username, s.current_price
                FROM user_portfolios p
                LEFT JOIN (
                    SELECT user_id, display_name, username, stat_period
                    FROM user_stats
                    WHERE stat_period = DATE_FORMAT(NOW(), '%Y-%m')
                ) u ON p.user_id = u.user_id
                JOIN stocks s ON p.stock_symbol = s.symbol
                WHERE p.shares > 0
                ORDER BY (p.shares * s.current_price) DESC
                LIMIT 20
            """, default=[], fetch_all=True)
            
            return jsonify({
                'stocks': stocks or [],
                'top_holders': top_holders or []
            })
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error getting stock data: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/stocks', methods=['GET'])
def stocks_page():
    """Renders the stock market management page."""
    return render_template('stocks.html')


@app.route('/api/stocks', methods=['GET'])
def api_get_stocks():
    """Get all stocks with current prices."""
    try:
        if not db_helpers.db_pool:
            return jsonify({'error': 'Database not available'}), 500
        
        conn = db_helpers.get_db_connection()
        if not conn:
            logger.error("Failed to get database connection")
            return jsonify({'error': 'Failed to get database connection'}), 500
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("""
                SELECT symbol, name, category, current_price, previous_price,
                       trend, last_update, volume_today, game_influence_factor
                FROM stocks
                ORDER BY symbol ASC
            """)
            raw_stocks = cursor.fetchall()
            
            # Convert Decimal values for JSON serialization using utility function
            stocks = [db_helpers.convert_decimals(stock) for stock in raw_stocks]
            
            return jsonify({'stocks': stocks})
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error getting stocks: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/stocks/<symbol>', methods=['GET'])
def api_get_stock(symbol):
    """Get details for a specific stock."""
    try:
        if not db_helpers.db_pool:
            return jsonify({'error': 'Database not available'}), 500
        
        conn = db_helpers.get_db_connection()
        if not conn:
            logger.error("Failed to get database connection")
            return jsonify({'error': 'Failed to get database connection'}), 500
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("""
                SELECT * FROM stocks WHERE symbol = %s
            """, (symbol,))
            raw_stock = cursor.fetchone()
            
            if not raw_stock:
                return jsonify({'error': 'Stock not found'}), 404
            
            # Convert Decimal values for JSON serialization
            stock = db_helpers.convert_decimals(raw_stock)
            
            return jsonify(stock)
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error getting stock {symbol}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/stocks', methods=['POST'])
def api_create_stock():
    """Create a new stock."""
    try:
        if not db_helpers.db_pool:
            return jsonify({'error': 'Database not available'}), 500
        
        data = request.get_json()
        symbol = data.get('symbol', '').upper()
        name = data.get('name')
        category = data.get('category')
        price = float(data.get('price', 100.0))
        
        if not symbol or not name or not category:
            return jsonify({'error': 'Missing required fields'}), 400
        
        if len(symbol) > 10:
            return jsonify({'error': 'Symbol too long (max 10 characters)'}), 400
        
        conn = db_helpers.get_db_connection()
        if not conn:
            logger.error("Failed to get database connection")
            return jsonify({'error': 'Failed to get database connection'}), 500
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO stocks (symbol, name, category, current_price, previous_price)
                VALUES (%s, %s, %s, %s, %s)
            """, (symbol, name, category, price, price))
            conn.commit()
            
            return jsonify({'message': 'Stock created successfully', 'symbol': symbol})
        except Exception as e:
            conn.rollback()
            if 'Duplicate entry' in str(e):
                return jsonify({'error': 'Stock with this symbol already exists'}), 409
            raise
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error creating stock: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/stocks/<symbol>', methods=['PUT'])
def api_update_stock(symbol):
    """Update an existing stock."""
    try:
        if not db_helpers.db_pool:
            return jsonify({'error': 'Database not available'}), 500
        
        data = request.get_json()
        
        conn = db_helpers.get_db_connection()
        if not conn:
            logger.error("Failed to get database connection")
            return jsonify({'error': 'Failed to get database connection'}), 500
        cursor = conn.cursor()
        
        try:
            # Build update query dynamically based on provided fields
            updates = []
            params = []
            
            if 'name' in data:
                updates.append("name = %s")
                params.append(data['name'])
            
            if 'category' in data:
                updates.append("category = %s")
                params.append(data['category'])
            
            if 'current_price' in data:
                # Update previous price to current price first
                cursor.execute("SELECT current_price FROM stocks WHERE symbol = %s", (symbol,))
                result = cursor.fetchone()
                if result:
                    updates.append("previous_price = current_price")
                
                updates.append("current_price = %s")
                params.append(float(data['current_price']))
            
            if 'trend' in data:
                updates.append("trend = %s")
                # Clamp trend to ±1.0 to prevent DECIMAL(5,4) overflow
                # DECIMAL(5,4) allows values from -9.9999 to 9.9999
                trend_value = max(-1.0, min(1.0, float(data['trend'])))
                params.append(trend_value)
            
            if 'game_influence_factor' in data:
                updates.append("game_influence_factor = %s")
                params.append(float(data['game_influence_factor']))
            
            if not updates:
                return jsonify({'error': 'No fields to update'}), 400
            
            params.append(symbol)
            query = f"UPDATE stocks SET {', '.join(updates)} WHERE symbol = %s"
            
            cursor.execute(query, params)
            conn.commit()
            
            if cursor.rowcount == 0:
                return jsonify({'error': 'Stock not found'}), 404
            
            return jsonify({'message': 'Stock updated successfully'})
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error updating stock {symbol}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/stocks/<symbol>', methods=['DELETE'])
def api_delete_stock(symbol):
    """Delete a stock."""
    try:
        if not db_helpers.db_pool:
            return jsonify({'error': 'Database not available'}), 500
        
        conn = db_helpers.get_db_connection()
        if not conn:
            logger.error("Failed to get database connection")
            return jsonify({'error': 'Failed to get database connection'}), 500
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM stocks WHERE symbol = %s", (symbol,))
            conn.commit()
            
            if cursor.rowcount == 0:
                return jsonify({'error': 'Stock not found'}), 404
            
            return jsonify({'message': 'Stock deleted successfully'})
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error deleting stock {symbol}: {e}")
        return jsonify({'error': str(e)}), 500


# ========== Games Dashboard APIs ==========

@app.route('/games', methods=['GET'])
def games_dashboard():
    """Renders the games dashboard page."""
    return render_template('games.html')


@app.route('/api/games/stats', methods=['GET'])
def games_stats():
    """Get overall games statistics."""
    try:
        if not db_helpers.db_pool:
            return jsonify({'error': 'Database not available'}), 500
        
        conn = db_helpers.get_db_connection()
        if not conn:
            logger.error("Failed to get connection for games_stats")
            return jsonify({'error': 'Failed to get database connection'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        stats = {}
        
        try:
            # Helper function to safely query tables
            def safe_query(query, default=0):
                try:
                    cursor.execute(query)
                    result = cursor.fetchone()
                    return result[list(result.keys())[0]] if result else default
                except Exception as e:
                    logger.warning(f"Query failed: {query[:50]}... Error: {e}")
                    return default
            
            # Werwolf stats - use werwolf_user_stats which tracks game participation
            werwolf_games = safe_query("SELECT COUNT(*) as total_games FROM werwolf_user_stats")
            werwolf_players = safe_query("SELECT COUNT(DISTINCT user_id) as total_players FROM werwolf_user_stats")
            
            stats['werwolf'] = {
                'total_games': werwolf_games,
                'total_players': werwolf_players
            }
            
            # Detective stats - use detective_user_progress for games count
            detective_games = safe_query("SELECT COUNT(*) as total_games FROM detective_user_progress")
            detective_players = safe_query("SELECT COUNT(DISTINCT user_id) as total_players FROM detective_user_stats")
            
            stats['detective'] = {
                'total_games': detective_games,
                'total_players': detective_players
            }
            
            # Wordle stats - use wordle_stats table which tracks all games
            wordle_games = safe_query("SELECT COALESCE(SUM(total_games), 0) as total_games FROM wordle_stats")
            wordle_players = safe_query("SELECT COUNT(*) as total_players FROM wordle_stats WHERE total_games > 0")
            
            stats['wordle'] = {
                'total_games': wordle_games,
                'total_players': wordle_players
            }
            
            # Word Find stats
            wordfind_games = safe_query("SELECT COUNT(*) as total_games FROM word_find_stats")
            wordfind_players = safe_query("SELECT COUNT(DISTINCT user_id) as total_players FROM word_find_stats")
            
            stats['wordfind'] = {
                'total_games': wordfind_games,
                'total_players': wordfind_players
            }
            
            # Casino games - get total count for display
            blackjack_games = safe_query("SELECT COUNT(*) as total_games FROM blackjack_games")
            blackjack_players = safe_query("SELECT COUNT(DISTINCT user_id) as total_players FROM blackjack_games")
            
            roulette_games = safe_query("SELECT COUNT(*) as total_games FROM roulette_games")
            roulette_players = safe_query("SELECT COUNT(DISTINCT user_id) as total_players FROM roulette_games")
            
            mines_games = safe_query("SELECT COUNT(*) as total_games FROM mines_games")
            mines_players = safe_query("SELECT COUNT(DISTINCT user_id) as total_players FROM mines_games")
            
            stats['casino'] = {
                'blackjack': {
                    'total_games': blackjack_games,
                    'total_players': blackjack_players
                },
                'roulette': {
                    'total_games': roulette_games,
                    'total_players': roulette_players
                },
                'mines': {
                    'total_games': mines_games,
                    'total_players': mines_players
                },
                'total_games': blackjack_games + roulette_games + mines_games
            }
            
            # Horse Racing stats
            horseracing_games = safe_query("SELECT COUNT(*) as total_games FROM horse_racing_games")
            horseracing_players = safe_query("SELECT COUNT(DISTINCT user_id) as total_players FROM horse_racing_bets")
            
            stats['horseracing'] = {
                'total_games': horseracing_games,
                'total_players': horseracing_players
            }
            
            # Trolly Problem stats - use trolly_responses instead of trolly_problem_choices
            trolly_games = safe_query("SELECT COUNT(*) as total_games FROM trolly_responses")
            trolly_players = safe_query("SELECT COUNT(DISTINCT user_id) as total_players FROM trolly_responses")
            
            stats['trolly'] = {
                'total_games': trolly_games,
                'total_players': trolly_players
            }
            
            return jsonify(stats)
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error getting games stats: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/verify/tables', methods=['GET'])
def verify_all_tables():
    """Verify all critical database tables exist."""
    try:
        if not db_helpers.db_pool:
            return jsonify({'error': 'Database not available'}), 500
        
        conn = db_helpers.get_db_connection()
        if not conn:
            logger.error("Failed to get database connection")
            return jsonify({'error': 'Failed to get database connection'}), 500
        cursor = conn.cursor()
        
        try:
            # Get all tables
            cursor.execute("SHOW TABLES")
            all_tables = [row[0] for row in cursor.fetchall()]
            
            # Critical tables that should exist
            critical_tables = {
                'word_find': ['word_find_daily', 'word_find_attempts', 'word_find_stats', 'word_find_premium_games'],
                'rpg': ['rpg_players', 'rpg_items', 'rpg_monsters', 'rpg_inventory', 'rpg_equipped', 'rpg_daily_shop'],
                'economy': ['user_stats', 'transaction_history'],
                'ai': ['ai_model_usage'],
                'games': ['wordle_games', 'detective_user_stats']
            }
            
            verification = {}
            missing_tables = []
            
            for category, tables in critical_tables.items():
                verification[category] = {
                    'expected': len(tables),
                    'found': 0,
                    'missing': []
                }
                
                for table in tables:
                    if table in all_tables:
                        verification[category]['found'] += 1
                    else:
                        verification[category]['missing'].append(table)
                        missing_tables.append(table)
            
            status = 'ok' if not missing_tables else 'error'
            
            return jsonify({
                'status': status,
                'total_tables': len(all_tables),
                'verification': verification,
                'missing_tables': missing_tables,
                'all_tables': all_tables
            })
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error verifying tables: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/games/<game_type>/leaderboard', methods=['GET'])
def game_leaderboard(game_type):
    """Get leaderboard for a specific game."""
    try:
        if not db_helpers.db_pool:
            return jsonify({'error': 'Database not available'}), 500
        
        conn = db_helpers.get_db_connection()
        if not conn:
            logger.error("Failed to get database connection")
            return jsonify({'error': 'Failed to get database connection'}), 500
        cursor = conn.cursor(dictionary=True)
        
        try:
            if game_type == 'detective':
                # Use LEFT JOIN with current month's user_stats
                # Note: streak and best_streak are set to 0 as these columns don't exist
                # in detective_user_stats table (streak tracking not yet implemented)
                leaderboard = safe_db_query(cursor, """
                    SELECT u.display_name, u.username, d.user_id,
                           d.cases_solved, d.total_cases_played as total_cases, 
                           ROUND(d.cases_solved * 100.0 / NULLIF(d.total_cases_played, 0), 2) as accuracy,
                           0 as streak, 0 as best_streak
                    FROM detective_user_stats d
                    LEFT JOIN (
                        SELECT user_id, display_name, username, stat_period
                        FROM user_stats
                        WHERE stat_period = DATE_FORMAT(NOW(), '%Y-%m')
                    ) u ON d.user_id = u.user_id
                    ORDER BY d.cases_solved DESC, accuracy DESC
                    LIMIT 50
                """, default=[], fetch_all=True)
            elif game_type == 'wordle':
                # Join with user_stats to get display names
                leaderboard = safe_db_query(cursor, """
                    SELECT w.user_id, u.display_name, u.username,
                           COUNT(*) as games_won,
                           AVG(w.attempts) as avg_attempts
                    FROM wordle_games w
                    LEFT JOIN (
                        SELECT user_id, display_name, username
                        FROM user_stats
                        WHERE stat_period = DATE_FORMAT(NOW(), '%Y-%m')
                    ) u ON w.user_id = u.user_id
                    WHERE w.completed = TRUE AND w.won = TRUE
                    GROUP BY w.user_id, u.display_name, u.username
                    ORDER BY games_won DESC, avg_attempts ASC
                    LIMIT 50
                """, default=[], fetch_all=True)
            else:
                return jsonify({'error': 'Invalid game type'}), 400
            
            return jsonify({'leaderboard': leaderboard or []})
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error getting game leaderboard: {e}")
        return jsonify({'error': str(e)}), 500


# ========== System Health APIs ==========

@app.route('/system', methods=['GET'])
def system_dashboard():
    """Renders the system health dashboard page."""
    return render_template('system.html')


@app.route('/api/system/health', methods=['GET'])
def system_health():
    """Get system health metrics with Termux compatibility."""
    try:
        import os
        
        # Try to import psutil, but provide fallbacks if not available
        try:
            import psutil
            psutil_available = True
        except ImportError:
            psutil_available = False
            logger.warning("psutil not available - using fallback methods")
        
        # Initialize response with defaults
        response = {
            'process': {
                'memory_mb': 0,
                'cpu_percent': 0,
                'uptime_seconds': 0
            },
            'system': {
                'memory_percent': 0,
                'memory_used_gb': 0,
                'memory_total_gb': 0,
                'cpu_percent': 0,
                'disk_percent': 0,
                'disk_used_gb': 0,
                'disk_total_gb': 0
            },
            'database': {
                'healthy': False,
                'pool_size': 0,
                'size_mb': 0
            },
            'logs': {
                'error_count': 0,
                'warning_count': 0
            },
            'bot_status': 'Unknown',
            'platform': platform.system()
        }
        
        # Get process metrics if psutil is available
        if psutil_available:
            try:
                process = psutil.Process(os.getpid())
                
                # Memory usage
                try:
                    memory_info = process.memory_info()
                    response['process']['memory_mb'] = round(memory_info.rss / 1024 / 1024, 2)
                except Exception as e:
                    logger.warning(f"Could not get process memory: {e}")
                
                # CPU usage
                try:
                    cpu_percent = process.cpu_percent(interval=0.1)
                    response['process']['cpu_percent'] = round(cpu_percent, 2)
                except Exception as e:
                    logger.warning(f"Could not get process CPU: {e}")
                
                # System-wide memory stats
                try:
                    system_memory = psutil.virtual_memory()
                    response['system']['memory_percent'] = round(system_memory.percent, 2)
                    response['system']['memory_used_gb'] = round(system_memory.used / 1024 / 1024 / 1024, 2)
                    response['system']['memory_total_gb'] = round(system_memory.total / 1024 / 1024 / 1024, 2)
                except Exception as e:
                    logger.warning(f"Could not get system memory: {e}")
                
                # System-wide CPU stats
                try:
                    system_cpu = psutil.cpu_percent(interval=0.1)
                    response['system']['cpu_percent'] = round(system_cpu, 2)
                except Exception as e:
                    logger.warning(f"Could not get system CPU: {e}")
                
                # Disk usage
                try:
                    disk = psutil.disk_usage('/')
                    response['system']['disk_percent'] = round(disk.percent, 2)
                    response['system']['disk_used_gb'] = round(disk.used / 1024 / 1024 / 1024, 2)
                    response['system']['disk_total_gb'] = round(disk.total / 1024 / 1024 / 1024, 2)
                except Exception as e:
                    logger.warning(f"Could not get disk usage: {e}")
            except Exception as e:
                logger.warning(f"Error getting psutil metrics: {e}")
        else:
            # Fallback: Try to get basic info from /proc (Linux/Termux)
            try:
                # Get memory info from /proc/meminfo
                if os.path.exists('/proc/meminfo'):
                    with open('/proc/meminfo', 'r') as f:
                        meminfo = f.read()
                        for line in meminfo.split('\n'):
                            if line.startswith('MemTotal:'):
                                total_kb = int(line.split()[1])
                                response['system']['memory_total_gb'] = round(total_kb / 1024 / 1024, 2)
                            elif line.startswith('MemAvailable:'):
                                available_kb = int(line.split()[1])
                                total = response['system']['memory_total_gb'] * 1024 * 1024  # Convert back to KB
                                if total > 0:
                                    used_kb = total - available_kb
                                    response['system']['memory_used_gb'] = round(used_kb / 1024 / 1024, 2)
                                    response['system']['memory_percent'] = round((used_kb / total) * 100, 2)
            except Exception as e:
                logger.warning(f"Fallback memory reading failed: {e}")
            
            try:
                # Get disk info using df command (works on Termux)
                import subprocess
                result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:
                        parts = lines[1].split()
                        if len(parts) >= 5:
                            # Parse size (e.g., "20G" -> 20)
                            try:
                                total_str = parts[1].rstrip('GMK')
                                used_str = parts[2].rstrip('GMK')
                                percent_str = parts[4].rstrip('%')
                                
                                response['system']['disk_total_gb'] = float(total_str) if 'G' in parts[1] else float(total_str) / 1024
                                response['system']['disk_used_gb'] = float(used_str) if 'G' in parts[2] else float(used_str) / 1024
                                response['system']['disk_percent'] = float(percent_str)
                            except Exception as e:
                                logger.warning(f"Could not parse df output: {e}")
            except Exception as e:
                logger.warning(f"Fallback disk reading failed: {e}")
        
        # Database health and size
        if db_helpers.db_pool:
            try:
                conn = db_helpers.get_db_connection()
                if conn:
                    response['database']['healthy'] = True
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute("SELECT 1")
                    
                    # Get database size
                    try:
                        cursor.execute("""
                            SELECT 
                                ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) as size_mb
                            FROM information_schema.tables
                            WHERE table_schema = DATABASE()
                        """)
                        result = cursor.fetchone()
                        if result and result.get('size_mb'):
                            response['database']['size_mb'] = float(result['size_mb'])
                    except Exception as e:
                        logger.warning(f"Could not get database size: {e}")
                    
                    cursor.close()
                    conn.close()
                    response['database']['pool_size'] = db_helpers.db_pool.pool_size if hasattr(db_helpers.db_pool, 'pool_size') else 5
            except Exception as e:
                logger.warning(f"Database health check failed: {e}")
        
        # Check for errors in recent logs
        latest_log = get_latest_log_file()
        if latest_log and os.path.exists(latest_log):
            try:
                with open(latest_log, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    recent_lines = lines[-1000:] if len(lines) > 1000 else lines
                    for line in recent_lines:
                        line_lower = line.lower()
                        if 'error' in line_lower and not 'no error' in line_lower:
                            response['logs']['error_count'] += 1
                        elif 'warning' in line_lower:
                            response['logs']['warning_count'] += 1
            except Exception as e:
                logger.error(f"Error reading log file: {e}")
        
        # Bot uptime (from status file)
        try:
            if os.path.exists('config/bot_status.json'):
                with open('config/bot_status.json', 'r', encoding='utf-8-sig') as f:
                    status_data = json.load(f)
                    response['bot_status'] = status_data.get('status', 'Unknown')
                    if 'timestamp' in status_data:
                        from datetime import datetime
                        try:
                            status_time = datetime.fromisoformat(status_data['timestamp'].replace('Z', '+00:00'))
                            now = datetime.now(status_time.tzinfo) if status_time.tzinfo else datetime.now()
                            response['process']['uptime_seconds'] = int((now - status_time).total_seconds())
                        except Exception as e:
                            logger.warning(f"Could not calculate uptime: {e}")
        except Exception as e:
            logger.warning(f"Error reading bot status: {e}")
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error getting system health: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'message': 'System health check failed',
            'platform': platform.system(),
            'process': {'memory_mb': 0, 'cpu_percent': 0, 'uptime_seconds': 0},
            'system': {'memory_percent': 0, 'memory_used_gb': 0, 'memory_total_gb': 0, 'cpu_percent': 0, 'disk_percent': 0, 'disk_used_gb': 0, 'disk_total_gb': 0},
            'database': {'healthy': False, 'pool_size': 0, 'size_mb': 0},
            'logs': {'error_count': 0, 'warning_count': 0},
            'bot_status': 'Error'
        }), 200  # Return 200 even on error so frontend can display partial data


@app.route('/api/system/api_quotas', methods=['GET'])
def api_quotas():
    """Get API usage quotas and limits."""
    try:
        # Load config for API limits
        config = {}
        try:
            with open('config/config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            logger.warning(f"Error loading config: {e}")
        
        # Get AI usage for current month
        from modules.db_helpers import get_ai_usage_stats
        
        # Use run_async helper for better event loop management
        stats_30days = run_async(get_ai_usage_stats(30)) or []
        
        # Calculate totals (handle Decimal types)
        from decimal import Decimal
        total_calls = sum(int(stat.get('total_calls', 0) or 0) for stat in stats_30days)
        total_input_tokens = sum(int(stat.get('total_input_tokens', 0) or 0) for stat in stats_30days)
        total_output_tokens = sum(int(stat.get('total_output_tokens', 0) or 0) for stat in stats_30days)
        total_cost = sum(float(stat.get('total_cost', 0) or 0) if not isinstance(stat.get('total_cost'), Decimal) else float(stat.get('total_cost', 0)) for stat in stats_30days)
        
        # API limits from config or defaults
        # Note: These are general estimates - check your API provider's documentation for exact limits
        provider = config.get('api', {}).get('provider', 'unknown')
        gemini_limit = config.get('api', {}).get('gemini', {}).get('rate_limit_rpm', 1500)
        openai_limit = config.get('api', {}).get('openai', {}).get('rate_limit_rpd', 10000)
        
        return jsonify({
            'current_usage': {
                'total_calls_30d': total_calls,
                'total_tokens_30d': total_input_tokens + total_output_tokens,
                'total_cost_30d': round(total_cost, 2)
            },
            'limits': {
                'gemini_rpm': gemini_limit,
                'openai_rpd': openai_limit,
                'note': 'Limits are estimates. Verify with your API provider.'
            },
            'provider': provider
        })
    except Exception as e:
        logger.error(f"Error getting API quotas: {e}")
        return jsonify({'error': str(e)}), 500


# --- NEW: Advanced AI Debug API Endpoints ---

@app.route('/ai_reasoning', methods=['GET'])
def ai_reasoning_page():
    """Render AI reasoning debug page."""
    return render_template('ai_reasoning.html')

@app.route('/voice_calls', methods=['GET'])
def voice_calls_page():
    """Render voice calls dashboard page."""
    return render_template('voice_calls.html')

@app.route('/api/ai_reasoning_debug', methods=['GET'])
def api_ai_reasoning_debug():
    """API endpoint for AI reasoning debug data."""
    try:
        from modules import advanced_ai
        
        # Get context manager for a sample channel (or all channels)
        # For now, we'll aggregate data from all active contexts
        context_data = {
            'current_tokens': 0,
            'max_tokens': 4000,
            'compressed_summaries': 0,
            'context_messages': 0,
            'api_usage': [],
            'recent_reasoning': [],
            'context_window': [],
            'cache_hit_rate': 0,
            'avg_response_time': 0,
            'tokens_saved': 0,
            'complex_queries': 0,
            'cot_used': 0,
            'compressions': 0
        }
        
        # Get API usage from database
        async def get_api_stats():
            async with db_helpers.get_db_connection() as (conn, cursor):
                await cursor.execute("""
                    SELECT 
                        model_name,
                        SUM(input_tokens) as input_tokens,
                        SUM(output_tokens) as output_tokens,
                        COUNT(*) as call_count
                    FROM api_usage_log
                    WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                    GROUP BY model_name
                    ORDER BY input_tokens + output_tokens DESC
                    LIMIT 5
                """)
                results = await cursor.fetchall()
                return [{
                    'model': row[0],
                    'input_tokens': row[1],
                    'output_tokens': row[2],
                    'total_tokens': row[1] + row[2],
                    'calls': row[3]
                } for row in results]
        
        api_usage = run_async(get_api_stats())
        context_data['api_usage'] = api_usage
        
        # Get sample context data (from first active channel if any)
        if advanced_ai._context_managers:
            first_channel = list(advanced_ai._context_managers.keys())[0]
            context_mgr = advanced_ai._context_managers[first_channel]
            
            context_data['current_tokens'] = context_mgr.get_current_token_count()
            context_data['max_tokens'] = context_mgr.token_budget
            context_data['compressed_summaries'] = len(context_mgr.compressed_summaries)
            context_data['context_messages'] = len(context_mgr.context_window)
            
            # Get recent messages from context window
            context_data['context_window'] = [
                {
                    'role': msg['role'],
                    'content': msg['content'][:200],  # Truncate for display
                    'timestamp': msg.get('timestamp', 'Unknown')
                }
                for msg in list(context_mgr.context_window)[-10:]  # Last 10 messages
            ]
        
        # Mock data for reasoning (would come from logging in production)
        # TODO: Replace with actual logging system that tracks reasoning events
        context_data['cache_hit_rate'] = 0  # Placeholder
        context_data['avg_response_time'] = 0  # Placeholder
        context_data['tokens_saved'] = 0  # Placeholder
        context_data['complex_queries'] = 0  # Placeholder
        context_data['cot_used'] = 0  # Placeholder
        context_data['compressions'] = 0  # Placeholder
        
        return jsonify(context_data)
        
    except Exception as e:
        logger.error(f"Error getting AI reasoning debug data: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/voice_calls/stats', methods=['GET'])
def api_voice_call_stats():
    """API endpoint for voice call statistics."""
    try:
        from modules import voice_conversation
        
        async def get_voice_stats():
            # Get active calls
            active_calls = voice_conversation.get_all_active_calls()
            
            # Get overall statistics
            stats = await voice_conversation.get_voice_call_stats()
            
            return {
                'active_calls': len(active_calls),
                'active_call_details': [
                    {
                        'user_id': call.user.id,
                        'user_name': call.user.display_name,
                        'channel_name': call.channel.name,
                        'duration': call.get_duration(),
                        'messages': len(call.conversation_history)
                    }
                    for call in active_calls
                ],
                'total_stats': stats
            }
        
        voice_stats = run_async(get_voice_stats())
        return jsonify(voice_stats)
        
    except Exception as e:
        logger.error(f"Error getting voice call stats: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


# --- NEW: Music Dashboard Routes ---

@app.route('/music_dashboard', methods=['GET'])
def music_dashboard_page():
    """Render music dashboard page."""
    return render_template('music_dashboard.html')


@app.route('/api/music/status', methods=['GET'])
def api_music_status():
    """API endpoint for current music playback status."""
    try:
        from modules import lofi_player
        
        # Get active sessions from lofi_player
        active_sessions = lofi_player.active_sessions
        
        now_playing = None
        queue = []
        stats = {
            'total_songs_played': 0,
            'queue_length': 0,
            'listening_time_today_minutes': 0,
            'active_sessions': len(active_sessions)
        }
        
        # Get info from first active session if any
        if active_sessions:
            guild_id = list(active_sessions.keys())[0]
            session = active_sessions[guild_id]
            
            # Get current song
            current_song = lofi_player.get_current_song(guild_id)
            if current_song:
                voice_client = session.get('voice_client')
                now_playing = {
                    'title': current_song.get('title', 'Unknown'),
                    'artist': current_song.get('artist', 'Unknown Artist'),
                    'guild_name': voice_client.guild.name if voice_client and voice_client.guild else 'Unknown',
                    'channel_name': voice_client.channel.name if voice_client and voice_client.channel else 'Unknown',
                    'listeners': len(voice_client.channel.members) if voice_client and voice_client.channel else 0,
                    'elapsed_seconds': 0,  # Would need tracking
                    'duration_seconds': 0  # Would need from video info
                }
            
            # Get queue
            queue = lofi_player.get_queue_preview(guild_id, count=10)
            stats['queue_length'] = lofi_player.get_queue_length(guild_id)
        
        # Get total songs played from database
        if db_helpers.db_pool:
            conn = None
            cursor = None
            try:
                conn = db_helpers.get_db_connection()
                if conn:
                    cursor = conn.cursor(dictionary=True)
                    
                    # Get total songs played
                    result = safe_db_query(cursor, """
                        SELECT COUNT(*) as count FROM music_history
                    """)
                    stats['total_songs_played'] = result.get('count', 0) if result else 0
                    
                    # Get listening time today
                    result = safe_db_query(cursor, """
                        SELECT COALESCE(SUM(duration_minutes), 0) as minutes 
                        FROM listening_time 
                        WHERE DATE(listened_at) = CURDATE()
                    """)
                    stats['listening_time_today_minutes'] = int(result.get('minutes', 0) or 0) if result else 0
                    
            except Exception as e:
                logger.error(f"Error querying music stats: {e}")
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()
        
        # Get recent songs
        recent_songs = []
        if db_helpers.db_pool:
            conn = None
            cursor = None
            try:
                conn = db_helpers.get_db_connection()
                if conn:
                    cursor = conn.cursor(dictionary=True)
                    recent = safe_db_query(cursor, """
                        SELECT song_title as title, song_artist as artist, album, played_at 
                        FROM music_history 
                        ORDER BY played_at DESC 
                        LIMIT 10
                    """, fetch_all=True)
                    if recent:
                        for song in recent:
                            recent_songs.append({
                                'title': song.get('title', 'Unknown'),
                                'artist': song.get('artist', 'Unknown Artist'),
                                'album': song.get('album', 'Unknown Album'),
                                'played_at': str(song.get('played_at', ''))
                            })
            except Exception as e:
                logger.error(f"Error querying recent songs: {e}")
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()
        
        return jsonify({
            'now_playing': now_playing,
            'queue': queue,
            'recent_songs': recent_songs,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting music status: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/music/top', methods=['GET'])
def api_music_top():
    """API endpoint for top songs and artists."""
    try:
        if not db_helpers.db_pool:
            return jsonify({'error': 'Database not available'}), 500
        
        conn = None
        cursor = None
        try:
            conn = db_helpers.get_db_connection()
            if not conn:
                return jsonify({'error': 'Failed to get database connection'}), 500
            
            cursor = conn.cursor(dictionary=True)
            
            # Get top songs
            top_songs = safe_db_query(cursor, """
                SELECT song_title as title, song_artist as artist, album, COUNT(*) as play_count
                FROM music_history
                WHERE played_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                GROUP BY song_title, song_artist, album
                ORDER BY play_count DESC
                LIMIT 10
            """, fetch_all=True)
            
            # Get top artists
            top_artists = safe_db_query(cursor, """
                SELECT song_artist as artist, COUNT(*) as play_count
                FROM music_history
                WHERE played_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                AND song_artist IS NOT NULL AND song_artist != ''
                GROUP BY song_artist
                ORDER BY play_count DESC
                LIMIT 10
            """, fetch_all=True)
            
            return jsonify({
                'top_songs': top_songs or [],
                'top_artists': top_artists or []
            })
            
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        
    except Exception as e:
        logger.error(f"Error getting top music: {e}")
        return jsonify({'error': str(e)}), 500


# --- NEW: User Profiles Routes ---

@app.route('/user_profiles', methods=['GET'])
def user_profiles_page():
    """Render user profiles page."""
    return render_template('user_profiles.html')


@app.route('/api/users/profiles', methods=['GET'])
def api_users_profiles():
    """API endpoint to get all user profiles."""
    try:
        if not db_helpers.db_pool:
            return jsonify({'error': 'Database not available', 'users': []}), 500
        
        conn = None
        cursor = None
        try:
            conn = db_helpers.get_db_connection()
            if not conn:
                return jsonify({'error': 'Failed to get database connection', 'users': []}), 500
            
            cursor = conn.cursor(dictionary=True)
            
            # Get user profiles with stats
            users = safe_db_query(cursor, """
                SELECT 
                    p.discord_id as user_id,
                    p.display_name,
                    p.premium_user as is_premium,
                    COALESCE(us.level, 0) as level,
                    COALESCE(us.xp, 0) as xp,
                    COALESCE(us.coins, 0) as coins,
                    COALESCE(us.message_count, 0) as message_count,
                    (SELECT COUNT(*) FROM music_history mh WHERE mh.user_id = p.discord_id) as songs_played
                FROM players p
                LEFT JOIN user_stats us ON p.discord_id = us.user_id 
                    AND us.stat_period = DATE_FORMAT(NOW(), '%Y-%m')
                ORDER BY 
                    COALESCE(us.level, 0) DESC, 
                    COALESCE(us.xp, 0) DESC,
                    p.display_name ASC
                LIMIT 500
            """, fetch_all=True, default=[])
            
            # Convert to proper format
            users_list = []
            for user in (users or []):
                users_list.append({
                    'user_id': user.get('user_id'),
                    'display_name': user.get('display_name', 'Unknown'),
                    'avatar_url': None,  # Could fetch from Discord API
                    'is_premium': bool(user.get('is_premium')),
                    'level': int(user.get('level', 0) or 0),
                    'xp': int(user.get('xp', 0) or 0),
                    'coins': int(user.get('coins', 0) or 0),
                    'message_count': int(user.get('message_count', 0) or 0),
                    'songs_played': int(user.get('songs_played', 0) or 0)
                })
            
            return jsonify({
                'users': users_list,
                'count': len(users_list)
            })
            
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        
    except Exception as e:
        logger.error(f"Error getting user profiles: {e}")
        return jsonify({'error': str(e), 'users': []}), 500


@app.route('/api/users/profile/<int:user_id>', methods=['GET'])
def api_user_profile(user_id):
    """API endpoint to get detailed user profile."""
    try:
        if not db_helpers.db_pool:
            return jsonify({'error': 'Database not available'}), 500
        
        conn = None
        cursor = None
        try:
            conn = db_helpers.get_db_connection()
            if not conn:
                return jsonify({'error': 'Failed to get database connection'}), 500
            
            cursor = conn.cursor(dictionary=True)
            
            # Get user info
            user_info = safe_db_query(cursor, """
                SELECT 
                    p.discord_id as user_id,
                    p.display_name,
                    p.premium_user as is_premium,
                    COALESCE(us.level, 0) as level,
                    COALESCE(us.xp, 0) as xp,
                    COALESCE(us.coins, 0) as coins,
                    COALESCE(us.message_count, 0) as message_count,
                    COALESCE(us.minutes_in_vc, 0) as vc_minutes
                FROM players p
                LEFT JOIN user_stats us ON p.discord_id = us.user_id 
                    AND us.stat_period = DATE_FORMAT(NOW(), '%Y-%m')
                WHERE p.discord_id = %s
            """, params=(user_id,))
            
            if not user_info:
                return jsonify({'error': 'User not found'}), 404
            
            # Get favorite songs
            favorite_songs = safe_db_query(cursor, """
                SELECT title, artist, COUNT(*) as play_count
                FROM music_history
                WHERE user_id = %s
                GROUP BY title, artist
                ORDER BY play_count DESC
                LIMIT 5
            """, params=(user_id,), fetch_all=True)
            
            # Get total listening time
            listening_time = safe_db_query(cursor, """
                SELECT COALESCE(SUM(duration_minutes), 0) as total_minutes
                FROM listening_time
                WHERE user_id = %s
            """, params=(user_id,))
            
            # Format response
            user_profile = {
                'user_id': user_info.get('user_id'),
                'display_name': user_info.get('display_name', 'Unknown'),
                'avatar_url': None,
                'is_premium': bool(user_info.get('is_premium')),
                'level': int(user_info.get('level', 0) or 0),
                'xp': int(user_info.get('xp', 0) or 0),
                'coins': int(user_info.get('coins', 0) or 0),
                'message_count': int(user_info.get('message_count', 0) or 0),
                'songs_played': len(favorite_songs) if favorite_songs else 0,
                'listening_time_minutes': int(listening_time.get('total_minutes', 0) or 0) if listening_time else 0,
                'favorite_songs': [
                    {
                        'title': song.get('title', 'Unknown'),
                        'artist': song.get('artist', 'Unknown'),
                        'play_count': int(song.get('play_count', 0) or 0)
                    }
                    for song in (favorite_songs or [])
                ]
            }
            
            return jsonify({'user': user_profile})
            
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Start the log following thread
    log_thread = threading.Thread(target=follow_log_file, daemon=True)
    log_thread.start()
    print("[Web Dashboard] Log streaming thread started.")
    
    # --- REFACTORED: Use SocketIO's built-in run method which works better with websockets ---
    # Note: host='0.0.0.0' allows access from network (required for Termux/Android access from other devices)
    print("[Web Dashboard] --- Starting Sulfur Bot Web Dashboard ---")
    print("[Web Dashboard] --- Access it at http://localhost:5000 ---")
    print("[Web Dashboard] --- Or from network: http://YOUR_IP:5000 ---")
    
    import socket
    
    def find_process_on_port(port):
        """Try to identify which process is using a port."""
        try:
            import subprocess
            # Try lsof first
            result = subprocess.run(['lsof', '-i', f':{port}'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout:
                return result.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass  # lsof not available or timed out
        
        try:
            # Try ss
            result = subprocess.run(['ss', '-tlnp'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout:
                for line in result.stdout.split('\n'):
                    if f':{port}' in line:
                        return line
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass  # ss not available or timed out
        
        try:
            # Try netstat
            result = subprocess.run(['netstat', '-tulnp'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout:
                for line in result.stdout.split('\n'):
                    if f':{port}' in line:
                        return line
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass  # netstat not available or timed out
        
        return None
    
    def cleanup_port(port):
        """Kill processes using the specified port (excluding ourselves)."""
        import subprocess
        import os
        killed_any = False
        our_pid = os.getpid()
        
        # TERMUX FIX: Don't aggressively kill processes on startup
        # Let the maintenance script handle cleanup instead
        # This prevents race conditions where we kill ourselves during restart
        print(f"[Web Dashboard] Checking for processes on port {port}...")
        
        # Try lsof (if available)
        try:
            result = subprocess.run(['lsof', '-ti', f':{port}'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid_str in pids:
                    try:
                        pid = int(pid_str.strip())
                        # Don't kill ourselves!
                        if pid == our_pid:
                            print(f"[Web Dashboard] Skipping our own PID {pid}")
                            continue
                        # CRITICAL FIX: On Termux, don't kill other processes during startup
                        # The maintenance script should have already cleaned up
                        print(f"[Web Dashboard] Found process {pid} on port {port}, but not killing it")
                        print(f"[Web Dashboard] If this causes issues, the maintenance script will handle cleanup")
                    except (ValueError, subprocess.TimeoutExpired):
                        pass
        except FileNotFoundError:
            print(f"[Web Dashboard] lsof not available (Termux?), skipping port check")
        except Exception as e:
            print(f"[Web Dashboard] Error checking port: {e}")
        
        # Don't try fuser on Termux - it's often not available and can cause hangs
        
        if killed_any:
            print(f"[Web Dashboard] Waiting 3 seconds for port to be released...")
            time.sleep(3)  # Give OS more time to release the port
        
        return killed_any
    
    # Retry logic with exponential backoff for port binding issues
    # Termux needs more retries due to slower socket cleanup
    max_retries = 10  # Increased from 5 for Termux compatibility
    retry_delay = 1  # Start with 1 second (faster initial retry)
    
    # TERMUX FIX: Don't proactively kill processes on startup
    # This was causing crash loops because the maintenance script restarts us immediately
    # The maintenance script should handle cleanup before starting us
    print("[Web Dashboard] Port cleanup is handled by maintenance script")
    print("[Web Dashboard] Proceeding with startup...")
    
    for attempt in range(max_retries):
        try:
            # Use socketio.run() which handles both HTTP and WebSocket connections
            if attempt > 0:
                print(f"[Web Dashboard] Retry attempt {attempt + 1}/{max_retries} after {retry_delay}s delay...")
                time.sleep(retry_delay)
                
                # Exponential backoff, but cap at 8 seconds
                retry_delay = min(retry_delay * 1.5, 8)
            
            print("[Web Dashboard] Starting Flask-SocketIO server...")
            
            # FIX: Properly configure socket options for Flask-SocketIO with threading backend
            # The threading backend uses werkzeug's built-in server, so we need to patch it correctly
            import werkzeug.serving
            
            # Store original function to avoid multiple wrapping
            if not hasattr(werkzeug.serving, '_original_make_server'):
                werkzeug.serving._original_make_server = werkzeug.serving.make_server
            
            def make_server_with_reuse(*args, **kwargs):
                """Wrapper to set SO_REUSEADDR and SO_REUSEPORT on the server socket."""
                server = werkzeug.serving._original_make_server(*args, **kwargs)
                
                # Set SO_REUSEADDR to allow binding to ports in TIME_WAIT state
                server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                print("[Web Dashboard] SO_REUSEADDR enabled on server socket")
                
                # Set SO_REUSEPORT if available (Linux 3.9+, helps with rapid restarts)
                try:
                    server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                    print("[Web Dashboard] SO_REUSEPORT enabled on server socket")
                except (AttributeError, OSError) as e:
                    print(f"[Web Dashboard] SO_REUSEPORT not available: {e}")
                
                return server
            
            werkzeug.serving.make_server = make_server_with_reuse
            
            # Start the server
            socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
            break  # Success, exit retry loop
            
        except OSError as e:
            if e.errno == 98 or e.errno == 48 or 'Address already in use' in str(e):  # Address already in use
                print(f"[Web Dashboard] Port 5000 is in use (attempt {attempt + 1}/{max_retries})")
                print(f"[Web Dashboard] Error details: {e}")
                
                if attempt == 0:
                    # Only show detailed diagnostics on first attempt
                    process_info = find_process_on_port(5000)
                    if process_info:
                        print(f"[Web Dashboard] Process using port 5000:")
                        for line in str(process_info).split('\n')[:10]:  # Limit output
                            if line.strip():
                                print(f"[Web Dashboard]   {line}")
                
                # Don't try to clean up port - let it happen naturally
                if attempt < max_retries - 1:
                    print(f"[Web Dashboard] Will retry after {retry_delay}s delay...")
                else:
                    # Final attempt failed
                    print(f"[Web Dashboard] FATAL ERROR: Port 5000 is still in use after {max_retries} attempts")
                    print(f"[Web Dashboard] The maintenance script should have cleaned up the port")
                    print(f"[Web Dashboard] This process will exit and the maintenance script will restart it")
                    import traceback
                    traceback.print_exc()
                    exit(1)
                # Continue to next retry
            else:
                print(f"[Web Dashboard] FATAL: Server startup failed with error: {e}")
                import traceback
                traceback.print_exc()
                exit(1)
                
        except Exception as e:
            print(f"[Web Dashboard] FATAL: Failed to start web server: {e}")
            import traceback
            traceback.print_exc()
            exit(1)