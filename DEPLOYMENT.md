# Telegram Bot Deployment Guide

## 1. Environment Preparation

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Set Environment Variables
Create `.env` file:
```bash
cp .env.example .env
```

Edit `.env` file:
```
BOT_TOKEN=your_bot_token
WEBHOOK_URL=https://yourdomain.com
PORT=8001
WEBHOOK_SECRET_TOKEN=your_secret_token
WEBHOOK_VERIFY_IP=false
```

## 2. Local Development Mode (Polling)

For local testing only, no webhook setup needed:

```bash
# Delete existing webhook (if any)
python setup_webhook.py delete

# Run bot (polling mode)
python telegram_img2pdf_bot.py
```

## 3. Production Deployment Mode (Webhook)

### 3.1 Get Public Domain

You need a publicly accessible HTTPS domain. Options include:

- **Free Options**:
  - [ngrok](https://ngrok.com/): For temporary testing
  - [Heroku](https://heroku.com/): Free deployment
  - [Vercel](https://vercel.com/): Free deployment
  - [Railway](https://railway.app/): Free tier available

- **Paid Options**:
  - Cloud servers (AWS, Google Cloud, Azure)
  - VPS providers
  - Dedicated hosting

### 3.2 Using ngrok for Local Testing

```bash
# Install ngrok
# Download: https://ngrok.com/download

# Start FastAPI service
uvicorn telegram_img2pdf_bot:app --host 0.0.0.0 --port 8001

# In new terminal window, start ngrok
ngrok http 8001

# Copy the https URL provided by ngrok, e.g.: https://abc123.ngrok.io
```

### 3.3 Set Webhook

```bash
# Method 1: Using script
export BOT_TOKEN="your_bot_token"
export WEBHOOK_URL="https://abc123.ngrok.io"
python setup_webhook.py set

# Method 2: Manual specification
python setup_webhook.py set --token "your_bot_token" --url "https://abc123.ngrok.io/webhook"
```

### 3.4 Verify Webhook

```bash
# Check webhook status
python setup_webhook.py info

# Test health check
curl https://yourdomain.com/health

# Test bot response
# Send /start to your bot in Telegram
```

## 4. Cloud Service Deployment

### 4.1 Heroku Deployment

Create `Procfile`:
```
web: uvicorn telegram_img2pdf_bot:app --host 0.0.0.0 --port $PORT
```

Deployment commands:
```bash
# Login to Heroku
heroku login

# Create app
heroku create your-app-name

# Set environment variables
heroku config:set BOT_TOKEN="your_bot_token"
heroku config:set WEBHOOK_URL="https://your-app-name.herokuapp.com"

# Deploy
git add .
git commit -m "Deploy telegram bot"
git push heroku main

# Set webhook
python setup_webhook.py set --token "your_bot_token" --url "https://your-app-name.herokuapp.com/webhook"
```

### 4.2 PM2 Deployment (Recommended)

Install PM2:
```bash
npm install -g pm2
```

Start with PM2:
```bash
# Start the bot
pm2 start "uvicorn telegram_img2pdf_bot:app --host 0.0.0.0 --port 8001" --name telegram-img2pdf-bot

# Save PM2 configuration
pm2 save

# Setup auto-start on boot
pm2 startup
```

PM2 Management Commands:
```bash
# View logs
pm2 logs telegram-img2pdf-bot

# Monitor
pm2 monit

# Restart
pm2 restart telegram-img2pdf-bot

# Stop
pm2 stop telegram-img2pdf-bot

# Delete
pm2 delete telegram-img2pdf-bot
```

### 4.3 Cloud Server Deployment

```bash
# Install dependencies
pip install -r requirements.txt

# Using systemd service (alternative to PM2)
sudo nano /etc/systemd/system/telegram-bot.service
```

systemd service file content:
```ini
[Unit]
Description=Telegram Image to PDF Bot
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/your/bot
Environment=BOT_TOKEN=your_bot_token
Environment=WEBHOOK_URL=https://yourdomain.com
Environment=PORT=8001
ExecStart=/usr/local/bin/uvicorn telegram_img2pdf_bot:app --host 0.0.0.0 --port 8001
Restart=always

[Install]
WantedBy=multi-user.target
```

Start service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
sudo systemctl status telegram-bot
```

## 5. Nginx Reverse Proxy (Optional)

If using Nginx as reverse proxy:

```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;

    location / {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 6. Troubleshooting

### Check Webhook Status
```bash
python setup_webhook.py info
```

### Common Issues

1. **Webhook Setup Failed**
   - Ensure URL uses HTTPS protocol
   - Ensure server is accessible from public internet
   - Check firewall settings

2. **Bot Not Responding**
   - Check service logs: `pm2 logs telegram-img2pdf-bot` or `sudo journalctl -u telegram-bot -f`
   - Verify environment variable settings
   - Test health check endpoint

3. **Switch Back to Polling Mode**
   ```bash
   python setup_webhook.py delete
   python telegram_img2pdf_bot.py
   ```

4. **Memory Issues**
   - Monitor with: `pm2 monit`
   - Check for memory leaks in logs
   - Restart service if needed: `pm2 restart telegram-img2pdf-bot`

## 7. Monitoring and Logging

### View Logs
```bash
# PM2 logs
pm2 logs telegram-img2pdf-bot

# systemd service logs
sudo journalctl -u telegram-bot -f

# Real-time monitoring
pm2 monit
```

### Health Check
Regularly check `/health` endpoint to ensure service is running properly:

```bash
curl https://yourdomain.com/health
```

Expected response:
```json
{"status": "healthy"}
```

## 8. Security Considerations

### Environment Variables
- Never commit `.env` files to version control
- Use secure tokens and secrets
- Rotate tokens periodically

### Server Security
- Keep server updated
- Use firewall rules
- Enable HTTPS only
- Consider rate limiting

### Webhook Security
- Use `WEBHOOK_SECRET_TOKEN` for additional security
- Enable `WEBHOOK_VERIFY_IP=true` in production
- Monitor for suspicious requests

## 9. Performance Optimization

### Memory Management
- The bot includes automatic memory leak prevention
- Sessions are cleaned every 30 minutes
- Temporary files are automatically removed

### Scaling
- Use PM2 cluster mode for multiple instances:
  ```bash
  pm2 start ecosystem.config.js
  ```
- Consider load balancing for high traffic
- Monitor memory and CPU usage regularly