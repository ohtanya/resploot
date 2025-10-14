#!/bin/bash

echo "Discord Pins Viewer Setup"
echo "========================"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install requirements
echo "Installing requirements..."
pip install -r requirements.txt

# Check if .env file has been configured
if grep -q "change_this_secure_password" .env; then
    echo ""
    echo "⚠️  IMPORTANT: Please configure your passwords in .env file!"
    echo "   Edit .env and change:"
    echo "   - PINS_VIEWER_PASSWORD=your_secure_password"
    echo "   - FLASK_SECRET_KEY=your_secret_key"
    echo ""
    read -p "Press Enter to continue anyway, or Ctrl+C to stop and configure first..."
fi

# Create pins data directory
mkdir -p pins_data

echo ""
echo "Starting Discord Pins Viewer..."
echo "Access at: http://localhost:5001"
echo "Press Ctrl+C to stop"
echo ""

python pins_viewer.py