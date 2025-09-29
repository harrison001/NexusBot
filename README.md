# Telegram Image to PDF Bot

This is a Telegram bot that can receive images sent by users and merge them into PDF files.

## Features

- Supports multiple image formats: PNG, JPEG, JPG, HEIC, HEIF
- Supports batch image processing
- Automatically arranges images in sending order
- Supports transparent background images (auto-converted to white background)
- User session management (automatically cleaned after 30 minutes)
- User-friendly English interface
- Memory leak prevention and optimization
- Race condition protection for concurrent uploads

## Installation and Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Create Telegram Bot

1. Find [@BotFather](https://t.me/botfather) in Telegram
2. Send `/newbot` command
3. Follow prompts to set bot name and username
4. Get your bot token

### 3. Set Environment Variables

Create `.env` file:

```bash
cp .env.example .env
```

Edit `.env` file and fill in your bot token:

```
BOT_TOKEN=your_telegram_bot_token_here
PORT=8001
WEBHOOK_URL=https://yourdomain.com
WEBHOOK_SECRET_TOKEN=your_secret_token_here
WEBHOOK_VERIFY_IP=false
```

Or set environment variables directly:

```bash
export BOT_TOKEN=your_telegram_bot_token_here
```

### 4. Run the Bot

#### Local Development (Polling Mode)
```bash
python telegram_img2pdf_bot.py
```

#### Production (Webhook Mode)
```bash
uvicorn telegram_img2pdf_bot:app --host 0.0.0.0 --port 8001
```

#### Using PM2 (Recommended for Production)
```bash
pm2 start "uvicorn telegram_img2pdf_bot:app --host 0.0.0.0 --port 8001" --name telegram-img2pdf-bot
```

## Usage

1. Find your bot in Telegram
2. Send `/start` command to begin
3. Send one or multiple images
4. Click "Generate PDF" button
5. Receive the merged PDF file

## Supported Commands

- `/start` - Show welcome message
- `/help` - Show help information
- `/clear` - Clear all images from current session

## Important Notes

- Images will be arranged in PDF in the order they were sent
- Each user's session is managed independently
- Sessions are automatically cleaned after 30 minutes of inactivity
- Supports image files sent as documents
- Memory optimized with automatic garbage collection
- Unique filename generation prevents race conditions

## Project Structure

```
telegram_bot/
├── telegram_img2pdf_bot.py    # Main program file
├── requirements.txt           # Project dependencies
├── .env                      # Environment variables
├── README.md                 # Documentation
├── DEPLOYMENT.md            # Deployment guide
└── .env.example             # Environment variables example
```

## Technical Implementation

- Uses `python-telegram-bot` library for Telegram API
- Uses `Pillow` for image format conversion
- Uses `pillow-heif` for HEIC format support
- Uses `FastAPI` for webhook server
- Implements user session management and temporary file cleanup
- Supports inline keyboard interaction
- Memory leak prevention with explicit PIL object management
- Concurrent processing protection with UUID-based file naming

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `BOT_TOKEN` | Telegram bot token | Yes | - |
| `PORT` | Server port | No | 8000 |
| `WEBHOOK_URL` | Public webhook URL | No | - |
| `WEBHOOK_SECRET_TOKEN` | Webhook security token | No | - |
| `WEBHOOK_VERIFY_IP` | Verify Telegram IPs | No | false |

## Security Features

- Webhook IP verification (optional)
- Secret token validation
- Temporary file auto-cleanup
- Session isolation per user
- Memory leak prevention