import json
import os
import platform
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

# Setup logging
logger = logging.getLogger('WebDashboard')
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s'))
    logger.addHandler(handler)


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

# Initialize the database pool for the web dashboard
print(f"[Web Dashboard] Initializing database connection to {DB_HOST}:{DB_NAME}...")
db_helpers.init_db_pool(DB_HOST, DB_USER, DB_PASS, DB_NAME)
if not db_helpers.db_pool:
    print("[Web Dashboard] WARNING: Database pool failed to initialize. Some features may be unavailable.")
else:
    print("[Web Dashboard] Database pool initialized successfully.")

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

def safe_db_query(cursor, query, default=None, fetch_all=False):
    """
    Safely execute a database query with error handling.
    
    Args:
        cursor: Database cursor to execute query on
        query: SQL query string
        default: Default value to return on error (None, 0, [], etc.)
        fetch_all: If True, fetchall(); otherwise fetchone()
    
    Returns:
        Query result or default value on error
    """
    try:
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
        conn = db_helpers.db_pool.get_connection()
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
            table_data = cursor.fetchall()
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
        conn = db_helpers.db_pool.get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT usage_date, model_name, call_count, input_tokens, output_tokens FROM api_usage ORDER BY usage_date DESC, model_name ASC")
        usage_data = cursor.fetchall()
    except Exception as e:
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
            conn = db_helpers.db_pool.get_connection()
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
                ('ai_conversation_history', 'user_id'),
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


# --- RPG Admin Routes ---

@app.route('/rpg_admin', methods=['GET'])
def rpg_admin():
    """RPG Admin page for managing monsters, items, and settings."""
    return render_template('rpg_admin.html')


@app.route('/api/rpg/stats', methods=['GET'])
def rpg_stats():
    """Get RPG statistics."""
    try:
        if not db_helpers.db_pool:
            return jsonify({'error': 'Database not available'}), 500
        
        conn = db_helpers.db_pool.get_connection()
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
        
        conn = db_helpers.db_pool.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        if request.method == 'GET':
            # Get all items
            cursor.execute("""
                SELECT id, name, type, rarity, description, damage, damage_type, 
                       price, required_level, durability, effects
                FROM rpg_items
                ORDER BY required_level ASC, name ASC
            """)
            items = cursor.fetchall()
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
        
        conn = db_helpers.db_pool.get_connection()
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
        
        conn = db_helpers.db_pool.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        if request.method == 'GET':
            # Get all monsters
            cursor.execute("""
                SELECT id, name, world, level, health, strength, defense, speed, 
                       xp_reward, gold_reward, loot_table, spawn_rate
                FROM rpg_monsters
                ORDER BY world ASC, level ASC, name ASC
            """)
            monsters = cursor.fetchall()
            cursor.close()
            conn.close()
            return jsonify(monsters)
        
        elif request.method == 'POST':
            # Create new monster
            data = request.json
            
            cursor.execute("""
                INSERT INTO rpg_monsters 
                (name, world, level, health, strength, defense, speed, xp_reward, gold_reward)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                data['name'],
                data['world'],
                data['level'],
                data['health'],
                data['strength'],
                data['defense'],
                data['speed'],
                data['xp_reward'],
                data['gold_reward']
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
        
        conn = db_helpers.db_pool.get_connection()
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
            conn = db_helpers.db_pool.get_connection()
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
        
        conn = db_helpers.db_pool.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Total coins in circulation (using balance column)
            result = safe_db_query(cursor, "SELECT COALESCE(SUM(balance), 0) as total_coins FROM user_stats")
            total_coins = result.get('total_coins', 0) if result else 0
            
            # Total users with coins
            result = safe_db_query(cursor, "SELECT COUNT(DISTINCT user_id) as total_users FROM user_stats WHERE balance > 0")
            total_users = result.get('total_users', 0) if result else 0
            
            # Average coins per user
            avg_coins = total_coins / total_users if total_users > 0 else 0
            
            # Richest users - check if display_name column exists
            richest_users = safe_db_query(cursor, """
                SELECT user_id, display_name, balance as coins 
                FROM user_stats 
                WHERE balance > 0 
                ORDER BY balance DESC 
                LIMIT 10
            """, default=[], fetch_all=True)
            
            # If display_name column doesn't exist, fall back to simpler query
            if not richest_users:
                richest_users = safe_db_query(cursor, """
                    SELECT user_id, balance as coins 
                    FROM user_stats 
                    WHERE balance > 0 
                    ORDER BY balance DESC 
                    LIMIT 10
                """, default=[], fetch_all=True)
            
            # Recent transactions - use transaction_history table if it exists
            recent_transactions = safe_db_query(cursor, """
                SELECT th.*, us.display_name, us.username 
                FROM transaction_history th
                LEFT JOIN (
                    SELECT user_id, display_name, username, stat_period
                    FROM user_stats
                    WHERE stat_period = DATE_FORMAT(NOW(), '%Y-%m')
                ) us ON th.user_id = us.user_id
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
        
        conn = db_helpers.db_pool.get_connection()
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
        
        conn = db_helpers.db_pool.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("""
                SELECT symbol, name, category, current_price, previous_price,
                       trend, last_update, volume_today, game_influence_factor
                FROM stocks
                ORDER BY symbol ASC
            """)
            stocks = cursor.fetchall()
            
            # Convert Decimal to float for JSON serialization
            for stock in stocks:
                for key in ['current_price', 'previous_price', 'trend', 'game_influence_factor']:
                    if stock.get(key) is not None:
                        stock[key] = float(stock[key])
            
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
        
        conn = db_helpers.db_pool.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("""
                SELECT * FROM stocks WHERE symbol = %s
            """, (symbol,))
            stock = cursor.fetchone()
            
            if not stock:
                return jsonify({'error': 'Stock not found'}), 404
            
            # Convert Decimal to float
            for key in ['current_price', 'previous_price', 'trend', 'game_influence_factor']:
                if stock.get(key) is not None:
                    stock[key] = float(stock[key])
            
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
        
        conn = db_helpers.db_pool.get_connection()
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
        
        conn = db_helpers.db_pool.get_connection()
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
                params.append(float(data['trend']))
            
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
        
        conn = db_helpers.db_pool.get_connection()
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
        
        conn = db_helpers.db_pool.get_connection()
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
            
            # Detective stats
            detective_games = safe_query("SELECT COUNT(*) as total_games FROM detective_games")
            detective_players = safe_query("SELECT COUNT(DISTINCT user_id) as total_players FROM detective_user_stats")
            
            stats['detective'] = {
                'total_games': detective_games,
                'total_players': detective_players
            }
            
            # Wordle stats  
            wordle_games = safe_query("SELECT COUNT(*) as total_games FROM wordle_games WHERE completed = TRUE")
            wordle_players = safe_query("SELECT COUNT(DISTINCT user_id) as total_players FROM wordle_games")
            
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
            
            # Casino games
            blackjack_games = safe_query("SELECT COUNT(*) as total_games FROM blackjack_games")
            roulette_games = safe_query("SELECT COUNT(*) as total_games FROM roulette_games")
            mines_games = safe_query("SELECT COUNT(*) as total_games FROM mines_games")
            
            stats['casino'] = {
                'blackjack_games': blackjack_games,
                'roulette_games': roulette_games,
                'mines_games': mines_games
            }
            
            # Horse Racing stats
            horseracing_games = safe_query("SELECT COUNT(*) as total_games FROM horse_racing_games")
            horseracing_players = safe_query("SELECT COUNT(DISTINCT user_id) as total_players FROM horse_racing_bets")
            
            stats['horseracing'] = {
                'total_games': horseracing_games,
                'total_players': horseracing_players
            }
            
            # Trolly Problem stats
            trolly_games = safe_query("SELECT COUNT(*) as total_games FROM trolly_problem_choices")
            trolly_players = safe_query("SELECT COUNT(DISTINCT user_id) as total_players FROM trolly_problem_choices")
            
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


@app.route('/api/games/<game_type>/leaderboard', methods=['GET'])
def game_leaderboard(game_type):
    """Get leaderboard for a specific game."""
    try:
        if not db_helpers.db_pool:
            return jsonify({'error': 'Database not available'}), 500
        
        conn = db_helpers.db_pool.get_connection()
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
                leaderboard = safe_db_query(cursor, """
                    SELECT user_id, COUNT(*) as games_won,
                           AVG(attempts) as avg_attempts
                    FROM wordle_games
                    WHERE completed = TRUE AND won = TRUE
                    GROUP BY user_id
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
    """Get system health metrics."""
    try:
        import psutil
        import os
        
        # Get current process
        process = psutil.Process(os.getpid())
        
        # Memory usage
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        
        # CPU usage
        cpu_percent = process.cpu_percent(interval=0.1)
        
        # System-wide stats
        system_memory = psutil.virtual_memory()
        system_cpu = psutil.cpu_percent(interval=0.1)
        
        # Disk usage
        disk = psutil.disk_usage('/')
        
        # Database health and size
        db_healthy = False
        db_pool_size = 0
        db_size_mb = 0
        if db_helpers.db_pool:
            try:
                conn = db_helpers.db_pool.get_connection()
                if conn:
                    db_healthy = True
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
                            db_size_mb = float(result['size_mb'])
                    except Exception as e:
                        logger.warning(f"Could not get database size: {e}")
                    
                    cursor.close()
                    conn.close()
                    db_pool_size = db_helpers.db_pool.pool_size if hasattr(db_helpers.db_pool, 'pool_size') else 5
            except Exception as e:
                logger.warning(f"Database health check failed: {e}")
        
        # Check for errors in recent logs
        error_count = 0
        warning_count = 0
        latest_log = get_latest_log_file()
        if latest_log and os.path.exists(latest_log):
            try:
                with open(latest_log, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    recent_lines = lines[-1000:] if len(lines) > 1000 else lines
                    for line in recent_lines:
                        line_lower = line.lower()
                        if 'error' in line_lower and not 'no error' in line_lower:
                            error_count += 1
                        elif 'warning' in line_lower:
                            warning_count += 1
            except Exception as e:
                logger.error(f"Error reading log file: {e}")
        
        # Bot uptime (from status file)
        uptime_seconds = 0
        bot_status = 'Unknown'
        try:
            if os.path.exists('config/bot_status.json'):
                with open('config/bot_status.json', 'r', encoding='utf-8-sig') as f:
                    status_data = json.load(f)
                    bot_status = status_data.get('status', 'Unknown')
                    if 'timestamp' in status_data:
                        from datetime import datetime
                        status_time = datetime.fromisoformat(status_data['timestamp'].replace('Z', '+00:00'))
                        now = datetime.now(status_time.tzinfo)
                        uptime_seconds = (now - status_time).total_seconds()
        except Exception as e:
            logger.warning(f"Error reading bot status: {e}")
        
        return jsonify({
            'process': {
                'memory_mb': round(memory_mb, 2),
                'cpu_percent': round(cpu_percent, 2),
                'uptime_seconds': uptime_seconds
            },
            'system': {
                'memory_percent': system_memory.percent,
                'memory_used_gb': round(system_memory.used / 1024 / 1024 / 1024, 2),
                'memory_total_gb': round(system_memory.total / 1024 / 1024 / 1024, 2),
                'cpu_percent': round(system_cpu, 2),
                'disk_percent': disk.percent,
                'disk_used_gb': round(disk.used / 1024 / 1024 / 1024, 2),
                'disk_total_gb': round(disk.total / 1024 / 1024 / 1024, 2)
            },
            'database': {
                'healthy': db_healthy,
                'pool_size': db_pool_size,
                'size_mb': db_size_mb
            },
            'logs': {
                'error_count': error_count,
                'warning_count': warning_count
            },
            'bot_status': bot_status
        })
    except ImportError:
        return jsonify({
            'error': 'psutil not installed',
            'message': 'Install psutil for system metrics: pip install psutil'
        }), 500
    except Exception as e:
        logger.error(f"Error getting system health: {e}")
        return jsonify({'error': str(e)}), 500


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
        
        # Use asyncio.run() for better event loop management
        stats_30days = asyncio.run(get_ai_usage_stats(30))
        
        # Calculate totals
        total_calls = sum(stat['total_calls'] for stat in stats_30days)
        total_input_tokens = sum(stat['total_input_tokens'] for stat in stats_30days)
        total_output_tokens = sum(stat['total_output_tokens'] for stat in stats_30days)
        total_cost = sum(stat['total_cost'] for stat in stats_30days)
        
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