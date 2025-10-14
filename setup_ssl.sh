#!/bin/bash

# Generate self-signed SSL certificate for pins viewer
# This will remove the "not secure" warning but browsers will show a certificate warning

echo "Generating self-signed SSL certificate..."

# Create SSL directory
sudo mkdir -p /etc/ssl/pins-viewer

# Generate private key and certificate
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/pins-viewer/key.pem \
    -out /etc/ssl/pins-viewer/cert.pem \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=your-server-ip"

# Update Nginx configuration for HTTPS
sudo tee /etc/nginx/sites-available/pins-viewer-ssl > /dev/null <<EOF
server {
    listen 80;
    server_name _;
    return 301 https://\$server_name:443\$request_uri;
}

server {
    listen 443 ssl;
    server_name _;

    ssl_certificate /etc/ssl/pins-viewer/cert.pem;
    ssl_certificate_key /etc/ssl/pins-viewer/key.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

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

# Enable SSL site
sudo ln -sf /etc/nginx/sites-available/pins-viewer-ssl /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/pins-viewer  # Remove HTTP-only version

# Test and reload Nginx
sudo nginx -t && sudo systemctl reload nginx

# Open HTTPS port
sudo ufw allow 443/tcp

echo "SSL certificate generated!"
echo "Access your pins viewer at: https://your-server-ip"
echo "Note: Browsers will show a certificate warning for self-signed certificates."
echo "Click 'Advanced' -> 'Proceed to site' to continue."