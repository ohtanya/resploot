# Discord Pins Viewer - Password Protected Web Interface

This web interface allows you to view Discord pins that have been saved during channel resets in a secure, password-protected environment.

## Features

- 🔐 **Password Protection** - Secure access to your saved pins
- 🔍 **Search Functionality** - Search through all pins by content or author
- 📱 **Responsive Design** - Works on desktop and mobile
- 📊 **Rich Display** - Shows messages, attachments, embeds, and reactions
- 📅 **Archive Management** - View pins organized by channel and reset date

## Setup

1. **Configure Passwords** (IMPORTANT!)
   
   Edit your `.env` file and change these values:
   ```
   PINS_VIEWER_PASSWORD=your_secure_password
   FLASK_SECRET_KEY=your_secret_key_for_sessions
   ```

2. **Install Dependencies**
   ```bash
   pip install flask flask-session
   ```

3. **Start the Web Interface**
   ```bash
   ./start_pins_viewer.sh
   ```
   
   Or manually:
   ```bash
   python pins_viewer.py
   ```

4. **Access the Interface**
   - Open your browser to: http://localhost:5000
   - Enter your password to access the pins

## How It Works

1. **Bot Integration**: Your Discord bot now saves pins to JSON files in the `pins_data/` directory whenever a channel is reset
2. **Web Interface**: The Flask web app reads these JSON files and displays them in a user-friendly format
3. **Security**: Password protection ensures only authorized users can view the pins

## File Structure

```
pins_data/
  ├── channel-name_20241014_143022.json    # Pins from channel reset
  ├── another-channel_20241014_150000.json
  └── ...

templates/
  ├── base.html        # Base template
  ├── login.html       # Login page
  ├── index.html       # Main pins list
  └── view_pins.html   # Individual pin archive viewer
```

## Security Notes

- The web interface runs locally (127.0.0.1:5000) by default
- All data is stored locally in JSON files
- Session-based authentication with configurable password
- No external network access required

## Troubleshooting

### "Import flask could not be resolved"
Make sure you've installed Flask:
```bash
pip install flask flask-session
```

### "No pins saved yet"
This means no channel resets with pins have occurred yet. The bot will automatically save pins when channels are reset.

### Password not working
Check your `.env` file and make sure `PINS_VIEWER_PASSWORD` is set to your desired password.

## Customization

You can modify the web interface by editing:
- `pins_viewer.py` - Main Flask application
- `templates/*.html` - HTML templates for styling and layout
- Change the port by modifying the `app.run()` call in `pins_viewer.py`