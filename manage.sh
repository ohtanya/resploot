#!/bin/bash

# Resploot Management Script
# Easy management of Discord bot and pins viewer

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

show_help() {
    echo "Resploot Management Script"
    echo "=========================="
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  start     - Start both bot and pins viewer"
    echo "  stop      - Stop both services"
    echo "  restart   - Restart both services"
    echo "  status    - Show PM2 status"
    echo "  logs      - Show logs for both services"
    echo "  bot-logs  - Show only bot logs"
    echo "  web-logs  - Show only pins viewer logs"
    echo "  update    - Pull latest code and restart"
    echo "  backup    - Backup pins data"
    echo "  help      - Show this help"
}

case "$1" in
    start)
        echo "Starting Discord bot and pins viewer..."
        pm2 start ecosystem.config.json
        pm2 save
        ;;
    stop)
        echo "Stopping services..."
        pm2 stop resploot-bot pins-viewer
        ;;
    restart)
        echo "Restarting services..."
        pm2 restart resploot-bot pins-viewer
        ;;
    status)
        pm2 status
        ;;
    logs)
        pm2 logs --lines 50
        ;;
    bot-logs)
        pm2 logs resploot-bot --lines 50
        ;;
    web-logs)
        pm2 logs pins-viewer --lines 50
        ;;
    update)
        echo "Updating code and restarting services..."
        git pull
        source venv/bin/activate
        pip install -r requirements.txt
        pm2 restart resploot-bot pins-viewer
        echo "Update complete!"
        ;;
    backup)
        BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
        echo "Creating backup in $BACKUP_DIR..."
        mkdir -p "$BACKUP_DIR"
        cp -r pins_data "$BACKUP_DIR/"
        cp -r logs "$BACKUP_DIR/"
        cp .env "$BACKUP_DIR/"
        echo "Backup created: $BACKUP_DIR"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac