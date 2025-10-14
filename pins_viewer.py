#!/usr/bin/env python3
"""
Discord Pins Viewer - Password-protected web interface for viewing saved pins
"""

import os
import json
import glob
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps

# Configuration
PINS_DATA_DIR = "pins_data"
PASSWORD = os.getenv("PINS_VIEWER_PASSWORD", "your_secure_password_here")  # Change this!
SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "change-this-secret-key-in-production")

app = Flask(__name__)
app.secret_key = SECRET_KEY

def login_required(f):
    """Decorator to require login for protected routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'authenticated' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def load_all_pins():
    """Load all pin files from the pins_data directory"""
    pins_files = []
    
    if not os.path.exists(PINS_DATA_DIR):
        return pins_files
    
    # Get all JSON files in the pins directory
    json_files = glob.glob(os.path.join(PINS_DATA_DIR, "*.json"))
    
    for file_path in sorted(json_files, reverse=True):  # Most recent first
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                data['filename'] = os.path.basename(file_path)
                data['file_path'] = file_path
                pins_files.append(data)
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
    
    return pins_files

@app.route('/')
@login_required
def index():
    """Main page showing all saved pins"""
    pins_files = load_all_pins()
    return render_template('index.html', pins_files=pins_files)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        password = request.form.get('password')
        if password == PASSWORD:
            session['authenticated'] = True
            return redirect(url_for('index'))
        else:
            flash('Invalid password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.clear()
    return redirect(url_for('login'))

@app.route('/view/<filename>')
@login_required
def view_pins(filename):
    """View pins from a specific file"""
    file_path = os.path.join(PINS_DATA_DIR, filename)
    
    if not os.path.exists(file_path) or not filename.endswith('.json'):
        flash('Pin file not found', 'error')
        return redirect(url_for('index'))
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return render_template('view_pins.html', data=data, filename=filename)
    except Exception as e:
        flash(f'Error loading pin file: {e}', 'error')
        return redirect(url_for('index'))

@app.route('/api/search')
@login_required
def search_pins():
    """API endpoint for searching pins"""
    query = request.args.get('q', '').lower()
    if not query:
        return jsonify([])
    
    results = []
    pins_files = load_all_pins()
    
    for file_data in pins_files:
        for pin in file_data.get('pins', []):
            # Search in content and author name
            if (query in pin.get('content', '').lower() or 
                query in pin.get('author', {}).get('name', '').lower()):
                
                result = {
                    'channel': file_data['channel_name'],
                    'filename': file_data['filename'],
                    'reset_date': file_data['reset_timestamp'],
                    'pin': pin
                }
                results.append(result)
    
    return jsonify(results[:50])  # Limit to 50 results

if __name__ == '__main__':
    # Create templates directory and files if they don't exist
    os.makedirs('templates', exist_ok=True)
    
    # Check if running in production
    is_production = os.getenv('FLASK_ENV') == 'production'
    
    print("Discord Pins Viewer")
    print("==================")
    print(f"Mode: {'Production' if is_production else 'Development'}")
    print(f"Password: {PASSWORD}")
    print(f"Pins directory: {PINS_DATA_DIR}")
    print("")
    print("Starting web server...")
    print("Access at: http://localhost:5001")
    if not is_production:
        print("Press Ctrl+C to stop")
    
    app.run(debug=not is_production, host='0.0.0.0' if is_production else '127.0.0.1', port=5001)