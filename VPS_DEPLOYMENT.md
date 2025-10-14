# VPS Deployment Guide

## Quick Deployment

### 1. On your VPS, run the deployment script:

```bash
curl -sSL https://raw.githubusercontent.com/ohtanya/resploot/main/deploy_full.sh | bash
```

Or manually:
```bash
git clone https://github.com/ohtanya/resploot.git
cd resploot
chmod +x deploy_full.sh
./deploy_full.sh
```

### 2. Configure environment variables:

```bash
cd resploot
cp .env.example .env
nano .env
```

Add your values:
```
DISCORD_BOT_TOKEN=your_bot_token_here
PINS_VIEWER_PASSWORD=your_secure_password_here
FLASK_SECRET_KEY=your_flask_secret_key_here
```

### 3. Start the services:

```bash
./manage.sh start
```

## Access Your Services

- **Pins Viewer**: http://your-server-ip:5001
- **Bot**: Runs in background via PM2

## Management Commands

```bash
./manage.sh start      # Start both services
./manage.sh stop       # Stop both services  
./manage.sh restart    # Restart both services
./manage.sh status     # Check PM2 status
./manage.sh logs       # View all logs
./manage.sh bot-logs   # View bot logs only
./manage.sh web-logs   # View web interface logs
./manage.sh update     # Pull updates and restart
./manage.sh backup     # Backup pins data
```

## Security Setup (Recommended)

### 1. Enable UFW Firewall:
```bash
sudo ufw enable
```

### 2. Setup Nginx Reverse Proxy (Optional):
```bash
sudo ln -sf /etc/nginx/sites-available/pins-viewer /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### 3. SSL Certificate with Let's Encrypt (Optional):
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## File Structure on VPS

```
/home/yourusername/resploot/
├── bot.py                 # Discord bot
├── pins_viewer.py         # Web interface
├── pins_data/            # Saved pins (JSON files)
├── logs/                 # PM2 logs
├── templates/            # Web interface templates
├── venv/                 # Python virtual environment
├── .env                  # Environment variables
├── manage.sh             # Management script
└── ecosystem.config.json # PM2 configuration
```

## Troubleshooting

### Check Service Status:
```bash
./manage.sh status
```

### View Logs:
```bash
./manage.sh logs           # All logs
./manage.sh bot-logs       # Bot only
./manage.sh web-logs       # Web interface only
```

### Restart Services:
```bash
./manage.sh restart
```

### Check Port Availability:
```bash
sudo netstat -tulpn | grep :5001
```

### Update Code:
```bash
./manage.sh update
```

## Port Configuration

- **5001**: Pins Viewer Web Interface
- **80**: Nginx (if configured)
- **443**: HTTPS (if SSL configured)

Make sure these ports are open in your VPS firewall/security groups.

## Daily Operations

1. **Check status**: `./manage.sh status`
2. **View recent logs**: `./manage.sh logs`
3. **Backup pins**: `./manage.sh backup`
4. **Update when needed**: `./manage.sh update`

Your Discord bot will automatically save pins to JSON files, and you can view them securely via the web interface!