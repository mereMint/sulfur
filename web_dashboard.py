import json
import os
import platform
import subprocess
import threading
import time
from flask import Flask, render_template, jsonify, request, flash, redirect, url_for
from flask_socketio import SocketIO, emit

# --- Local Imports ---
import db_helpers
from controls import stop_bot_processes, restart_bot, sync_database_changes, update_bot_from_git

# --- Configuration ---

# Load environment variables for database connection
from dotenv import load_dotenv
load_dotenv()

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_USER = os.environ.get("DB_USER", "sulfur_bot_user")
DB_PASS = os.environ.get("DB_PASS", "")
DB_NAME = os.environ.get("DB_NAME", "sulfur_bot")

# Initialize the database pool for the web dashboard
db_helpers.init_db_pool(DB_HOST, DB_USER, DB_PASS, DB_NAME)

# --- Flask App Setup ---

# --- FIX: Specify the template folder to be the current directory ---
# By default, Flask looks for a 'templates' subfolder. Since the HTML files are in the root, we point it here.
app = Flask(__name__, template_folder='.')
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

    while True:
        latest_log = get_latest_log_file()

        if latest_log != last_known_file:
            if file:
                file.close()
            if latest_log:
                socketio.emit('log_update', {'data': f'\n--- Switched to new log file: {os.path.basename(latest_log)} ---\n'}, namespace='/')
                # --- FIX: Open with error handling for encoding issues ---
                file = open(latest_log, 'r', encoding='utf-8', errors='ignore')
                # Go to the end of the file
                file.seek(0, 2)
            last_known_file = latest_log

        if file:
            line = file.readline()
            if not line:
                time.sleep(0.1)
                continue
            socketio.emit('log_update', {'data': line}, namespace='/')
        else:
            # No log file found, wait a bit before checking again
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
    config_path = 'config.json'
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
    conn = None
    cursor = None
    for table_name in tables_to_show:
        try:
            query = f"SELECT * FROM {table_name} ORDER BY 1 DESC LIMIT 50"
            conn = db_helpers.db_pool.get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query)
            table_data[table_name] = cursor.fetchall()
        except Exception as e:
            table_data[table_name] = {'error': str(e)}
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
            
    return render_template('database.html', table_data=table_data)

@app.route('/ai_usage', methods=['GET'])
def ai_usage_viewer():
    """Renders the AI usage page."""
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

# --- API Endpoints for Bot Control ---

@app.route('/api/bot-status', methods=['GET'])
def api_bot_status():
    """API endpoint to get the current status of the bot."""
    status_file = 'bot_status.json'
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


if __name__ == '__main__':
    # Start the log following thread
    log_thread = threading.Thread(target=follow_log_file, daemon=True)
    log_thread.start()
    
    # --- REFACTORED: Use a production-ready WSGI server (waitress) instead of Flask's dev server ---
    # This is more stable and reliable for network access.
    from waitress import serve
    print("--- Starting Sulfur Bot Web Dashboard ---")
    print("--- Access it at http://localhost:5000 ---")
    serve(socketio.run(app), host='0.0.0.0', port=5000)