# Telegram Image to PDF Bot API Documentation

## Overview

This document describes the FastAPI-based webhook server that powers the Telegram Image to PDF Bot.

## Endpoints

### Health Check

**GET** `/`
- **Description**: Basic root endpoint
- **Response**:
  ```json
  {"message": "Telegram Image to PDF Bot is running"}
  ```

**GET** `/health`
- **Description**: Health check endpoint for monitoring
- **Response**:
  ```json
  {"status": "healthy"}
  ```

### Webhook

**POST** `/webhook`
- **Description**: Receives updates from Telegram
- **Headers**:
  - `X-Telegram-Bot-Api-Secret-Token` (optional): Secret token for webhook verification
- **Request Body**: Telegram Update object (JSON)
- **Response**:
  ```json
  {"status": "ok"}
  ```

## Security Features

### IP Verification
- Optionally verifies requests come from official Telegram IP ranges
- Controlled by `WEBHOOK_VERIFY_IP` environment variable
- Telegram IP ranges:
  - `149.154.160.0/20`
  - `91.108.4.0/22`

### Secret Token Validation
- Validates `X-Telegram-Bot-Api-Secret-Token` header if `WEBHOOK_SECRET_TOKEN` is set
- Provides additional security layer beyond IP verification

## Bot Commands

### User Commands

| Command | Description | Usage |
|---------|-------------|-------|
| `/start` | Show welcome message and bot instructions | `/start` |
| `/help` | Display detailed help information | `/help` |
| `/clear` | Clear all images from current session | `/clear` |

### Inline Buttons

| Button | Action | Description |
|--------|--------|-------------|
| =Ä Generate PDF | `generate_pdf` | Convert all images to PDF |
| =Ñ Clear Images | `clear_images` | Remove all images from session |

## Image Processing

### Supported Formats
- **Standard**: PNG, JPEG, JPG
- **HEIC/HEIF**: Supported if `pillow-heif` is installed
- **Transparency**: RGBA images auto-converted to RGB with white background

### Processing Flow
1. User uploads image(s)
2. Images stored in temporary directory with unique filenames
3. Session tracks images and metadata
4. On PDF generation, images processed in upload order
5. Temporary files cleaned up after processing

### File Naming
- Format: `image_{timestamp}_{uuid}{extension}`
- Prevents race conditions in concurrent uploads
- Unique across all users and sessions

## Session Management

### User Sessions
- Each user has independent session
- Sessions store:
  - List of uploaded image paths
  - Temporary directory path
  - Last activity timestamp
- Automatic cleanup after 30 minutes of inactivity

### Memory Management
- Explicit PIL object cleanup
- Garbage collection after operations
- Memory monitoring and logging
- Session data cleanup on expiration

## Error Handling

### Common Errors
- `403 Forbidden`: Invalid IP or secret token
- `400 Bad Request`: Invalid JSON in webhook request
- `503 Service Unavailable`: Bot not initialized

### User-Facing Errors
- Unsupported file format
- Image processing failures
- PDF generation errors
- File upload issues

## Monitoring

### Logging
- Structured logging with timestamps
- Log levels: INFO, ERROR, WARNING
- Memory usage tracking
- Session cleanup reporting

### Health Checks
- `/health` endpoint for external monitoring
- Memory usage monitoring
- Active session count tracking
- Webhook verification status

## Environment Configuration

### Required Variables
```bash
BOT_TOKEN=your_telegram_bot_token_here
```

### Optional Variables
```bash
PORT=8001                              # Server port (default: 8000)
WEBHOOK_URL=https://yourdomain.com     # Public webhook URL
WEBHOOK_SECRET_TOKEN=your_secret       # Webhook security token
WEBHOOK_VERIFY_IP=false               # Enable IP verification (default: false)
```

## Development vs Production

### Development Mode
- Uses polling instead of webhooks
- No public URL required
- Simpler setup for testing

### Production Mode
- Requires HTTPS webhook URL
- IP and token verification available
- Better performance for high volume
- Automatic restart capabilities with PM2

## Rate Limiting

Currently no built-in rate limiting. Consider implementing:
- Per-user request limits
- Global request limits
- Image size limits
- PDF generation frequency limits

## Scaling Considerations

### Single Instance
- Current implementation uses in-memory session storage
- Suitable for small to medium usage
- Memory efficient with cleanup

### Multi-Instance
- Would require external session storage (Redis, database)
- Load balancer needed for webhook distribution
- Shared temporary file storage required

## Troubleshooting

### Bot Not Responding
1. Check webhook status with Telegram API
2. Verify environment variables
3. Test health endpoint
4. Check application logs

### Memory Issues
1. Monitor with `pm2 monit`
2. Check session cleanup logs
3. Restart if memory usage excessive
4. Verify garbage collection working

### File Processing Issues
1. Check temporary directory permissions
2. Verify supported image formats
3. Monitor disk space usage
4. Check PIL/Pillow installation