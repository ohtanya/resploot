#!/bin/bash

# Discord Bot Deployment Script
# Run this script on your VPS to deploy the bot

echo "Deploying Discord Channel Reset Bot..."

# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Python3 and pip if not already installed
sudo apt install python3 python3-pip python3-venv git -y

# Clone the repository (update this if you want to use a different directory)
DEPLOY_DIR="/home/$USER/discord-bot"
if [ -d "$DEPLOY_DIR" ]; then
    echo "Directory exists, pulling latest changes..."
    cd "$DEPLOY_DIR"
    git pull
else
    echo "Cloning repository..."
    git clone https://github.com/ohtanya/resploot.git "$DEPLOY_DIR"
    cd "$DEPLOY_DIR"
fi

# Create virtual environment
python3 -m venv venv

# Activate virtual environment and install dependencies
source venv/bin/activate
pip install -r requirements.txt

echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Create .env file: cp .env.example .env"
echo "2. Edit .env and add your Discord bot token: nano .env"
echo "3. Update the GUILD_ID in bot.py with your server ID if needed"
echo "4. Test the bot: source venv/bin/activate && python3 bot.py"
echo ""
echo "To set up as a systemd service (runs automatically):"
echo "5. Edit discord-bot.service and replace YOUR_USERNAME with your actual username"
echo "6. sudo cp discord-bot.service /etc/systemd/system/"
echo "7. sudo systemctl daemon-reload"
echo "8. sudo systemctl enable discord-bot.service"
echo "9. sudo systemctl start discord-bot.service"
echo "10. Check status: sudo systemctl status discord-bot.service"
