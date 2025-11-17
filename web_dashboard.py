import json
import os
import platform
import subprocess
import threading
import time
from flask import Flask, render_template, jsonify, request, flash, redirect, url_for
from flask_socketio import SocketIO, emit

# --- Local Imports ---
from modules import db_helpers
from modules.controls import stop_bot_processes, restart_bot, sync_database_changes, update_bot_from_git

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

@app.route('/database', methods=['GET'])
def database_viewer():
    """Renders the database viewer page."""
    tables_to_show = ['players', 'user_monthly_stats', 'managed_voice_channels', 'chat_history', 'api_usage']
    table_data = {}
    if not db_helpers.db_pool:
        for table_name in tables_to_show:
            table_data[table_name] = [{'error': 'Database pool not initialized'}]
        return render_template('database.html', table_data=table_data)
    
    for table_name in tables_to_show:
        conn = None
        cursor = None
        try:
            query = f"SELECT * FROM {table_name} ORDER BY 1 DESC LIMIT 50"
            conn = db_helpers.db_pool.get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query)
            table_data[table_name] = cursor.fetchall()
        except Exception as e:
            table_data[table_name] = [{'error': str(e)}]
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
            
    return render_template('database.html', table_data=table_data)

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
    import asyncio
    
    try:
        # Get stats for different time periods
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        stats_7days = loop.run_until_complete(get_ai_usage_stats(7))
        stats_30days = loop.run_until_complete(get_ai_usage_stats(30))
        stats_all = loop.run_until_complete(get_ai_usage_stats(365))
        
        loop.close()
        
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
        import asyncio
        
        # Run async function in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        stats = loop.run_until_complete(get_ai_usage_stats(days))
        loop.close()
        
        # Group by model and feature for better display
        by_model = {}
        by_feature = {}
        total_calls = 0
        total_tokens = 0
        
        for stat in stats:
            model = stat.get('model_name', 'Unknown')
            feature = stat.get('feature', 'Unknown')
            calls = stat.get('total_calls', 0)
            input_tok = stat.get('total_input_tokens', 0)
            output_tok = stat.get('total_output_tokens', 0)
            cost = stat.get('total_cost', 0.0)
            
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
        print(f"Error fetching AI usage: {e}")
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
        import asyncio
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
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        registrations = loop.run_until_complete(fetch_stats())
        loop.close()
        
        return jsonify({'registrations': registrations})
    except Exception as e:
        print(f"[API] Error fetching wrapped stats: {e}")
        return jsonify({'error': str(e), 'registrations': []}), 500

@app.route('/api/level_leaderboard', methods=['GET'])
def api_level_leaderboard():
    """API endpoint to get level leaderboard."""
    try:
        import asyncio
        from modules.db_helpers import get_level_leaderboard
        
        async def fetch_leaderboard():
            leaderboard, error = await get_level_leaderboard()
            return leaderboard if not error else []
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        leaderboard = loop.run_until_complete(fetch_leaderboard())
        loop.close()
        
        return jsonify({'leaderboard': leaderboard})
    except Exception as e:
        print(f"[API] Error fetching level leaderboard: {e}")
        return jsonify({'error': str(e), 'leaderboard': []}), 500

@app.route('/api/ww_leaderboard', methods=['GET'])
def api_ww_leaderboard():
    """API endpoint to get Werwolf leaderboard."""
    try:
        import asyncio
        from modules.db_helpers import get_leaderboard
        
        async def fetch_leaderboard():
            leaderboard, error = await get_leaderboard()
            return leaderboard if not error else []
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        leaderboard = loop.run_until_complete(fetch_leaderboard())
        loop.close()
        
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
        # Reload config in the dashboard process
        global config_data
        with open('config/config.json', 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        # Signal bot to reload config (if running)
        try:
            with open('config/reload_config.flag', 'w') as f:
                f.write(str(time.time()))
        except:
            pass
        
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
        import asyncio
        from modules.db_helpers import clear_channel_history
        
        data = request.json
        channel_id = int(data.get('channel_id'))
        
        async def clear_history():
            deleted_count, error = await clear_channel_history(channel_id)
            if error:
                return {'success': False, 'message': f'Error: {error}'}
            return {'success': True, 'message': f'Deleted {deleted_count} messages'}
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(clear_history())
        loop.close()
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/admin/delete_memory', methods=['POST'])
def admin_delete_memory():
    """Delete bot memory for a user."""
    try:
        import asyncio
        from modules.db_helpers import update_relationship_summary
        
        data = request.json
        user_id = int(data.get('user_id'))
        
        async def delete_user_memory():
            await update_relationship_summary(user_id, None)
            return {'success': True, 'message': f'Memory deleted for user {user_id}'}
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(delete_user_memory())
        loop.close()
        
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
    try:
        # Use socketio.run() which handles both HTTP and WebSocket connections
        socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
    except Exception as e:
        print(f"[Web Dashboard] FATAL: Failed to start web server: {e}")
        import traceback
        traceback.print_exc()
        exit(1)