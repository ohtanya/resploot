#!/bin/bash

# Discord Bot + Pins Viewer Deployment Script with PM2
# Run this script on your VPS to deploy both the bot and web interface

echo "Deploying Discord Bot + Pins Viewer with PM2..."

# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Python3 and pip if not already installed
sudo apt install python3 python3-pip python3-venv git curl nginx -y

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

# Clone/update the repository
DEPLOY_DIR="/home/$USER/resploot"
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

# Create necessary directories
mkdir -p logs
mkdir -p pins_data

# Update ecosystem config with current user
sed "s/USER_PLACEHOLDER/$USER/g" ecosystem.config.json > ecosystem.config.temp.json
mv ecosystem.config.temp.json ecosystem.config.json

# Setup Nginx reverse proxy for pins viewer (optional but recommended)
echo "Setting up Nginx reverse proxy..."
sudo tee /etc/nginx/sites-available/pins-viewer > /dev/null <<EOF
server {
    listen 80;
    server_name your-domain.com;  # Replace with your domain or IP

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Security headers
        proxy_set_header X-Frame-Options DENY;
        proxy_set_header X-Content-Type-Options nosniff;
        proxy_set_header X-XSS-Protection "1; mode=block";
    }
}
EOF

# Enable the Nginx site (optional - user can decide)
echo ""
echo "Nginx configuration created at /etc/nginx/sites-available/pins-viewer"
echo "To enable it, run:"
echo "  sudo ln -sf /etc/nginx/sites-available/pins-viewer /etc/nginx/sites-enabled/"
echo "  sudo nginx -t && sudo systemctl reload nginx"
echo ""

# Setup firewall rules
echo "Setting up firewall rules..."
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
# Allow direct access to pins viewer port (optional)
sudo ufw allow 5001/tcp
echo "Firewall rules configured (not enabled automatically)"

echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Create .env file: cp .env.example .env"
echo "2. Edit .env and configure: nano .env"
echo "   - DISCORD_BOT_TOKEN=your_bot_token"
echo "   - PINS_VIEWER_PASSWORD=your_secure_password"
echo "   - FLASK_SECRET_KEY=your_flask_secret_key"
echo "3. Update the GUILD_ID in bot.py with your server ID if needed"
echo "4. Test the services:"
echo "   - Bot: source venv/bin/activate && python3 bot.py"
echo "   - Viewer: source venv/bin/activate && python3 pins_viewer.py"
echo ""
echo "To start with PM2:"
echo "5. pm2 start ecosystem.config.json"
echo "6. pm2 save  # Save the PM2 process list"
echo "7. pm2 startup  # Generate startup script (follow the instructions)"
echo ""
echo "Access your pins viewer at:"
echo "- Direct: http://your-server-ip:5001"
echo "- Via Nginx: http://your-domain.com (after enabling Nginx config)"
echo ""
echo "PM2 useful commands:"
echo "- pm2 status                # View running processes"
echo "- pm2 logs resploot-bot     # View bot logs"
echo "- pm2 logs pins-viewer      # View web interface logs"
echo "- pm2 restart resploot-bot  # Restart the bot"
echo "- pm2 restart pins-viewer   # Restart the web interface"
echo "- pm2 stop all              # Stop all services"
echo "- pm2 delete all            # Remove all from PM2"