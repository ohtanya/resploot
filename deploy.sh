#!/bin/bash

# Discord Bot Deployment Script with PM2
# Run this script on your VPS to deploy the bot

echo "Deploying Discord Channel Reset Bot with PM2..."

# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Python3 and pip if not already installed
sudo apt install python3 python3-pip python3-venv git curl -y

# Install Node.js and npm (required for PM2)
if ! command -v node &> /dev/null; then
    echo "Installing Node.js..."
    curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

# Install PM2 globally
if ! command -v pm2 &> /dev/null; then
    echo "Installing PM2..."
    sudo npm install -g pm2
fi

# Clone the repository
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

# Create logs directory
mkdir -p logs

# Update ecosystem config with current user
sed "s/USER_PLACEHOLDER/$USER/g" ecosystem.config.json > ecosystem.config.temp.json
mv ecosystem.config.temp.json ecosystem.config.json

echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Create .env file: cp .env.example .env"
echo "2. Edit .env and add your Discord bot token: nano .env"
echo "3. Update the GUILD_ID in bot.py with your server ID if needed"
echo "4. Test the bot: source venv/bin/activate && python3 bot.py"
echo ""
echo "To start with PM2:"
echo "5. pm2 start ecosystem.config.json"
echo "6. pm2 save  # Save the PM2 process list"
echo "7. pm2 startup  # Generate startup script (follow the instructions)"
echo ""
echo "PM2 useful commands:"
echo "- pm2 status           # View running processes"
echo "- pm2 logs discord-bot # View logs"
echo "- pm2 restart discord-bot # Restart the bot"
echo "- pm2 stop discord-bot # Stop the bot"
echo "- pm2 delete discord-bot # Remove from PM2"
