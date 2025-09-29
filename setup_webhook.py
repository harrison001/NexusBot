#!/usr/bin/env python3
"""
Telegram Bot Webhook Setup Script
Used to set up and manage Telegram bot webhooks
"""

import os
import asyncio
import argparse
from telegram import Bot

async def set_webhook(token: str, webhook_url: str, secret_token: str = None):
    """Set webhook"""
    bot = Bot(token=token)

    try:
        # Set webhook
        if secret_token:
            result = await bot.set_webhook(url=webhook_url, secret_token=secret_token)
            print(f"✅ Webhook set successfully: {webhook_url} (with secret token)")
        else:
            result = await bot.set_webhook(url=webhook_url)
            print(f"✅ Webhook set successfully: {webhook_url} (no secret token)")

        if not result:
            print("❌ Failed to set webhook")

        # Get webhook information
        webhook_info = await bot.get_webhook_info()
        print(f"\nCurrent Webhook Information:")
        print(f"URL: {webhook_info.url}")
        print(f"Pending updates: {webhook_info.pending_update_count}")
        print(f"Last error date: {webhook_info.last_error_date}")
        print(f"Last error message: {webhook_info.last_error_message}")

    except Exception as e:
        print(f"❌ Error: {e}")

async def delete_webhook(token: str):
    """Delete webhook (switch back to polling mode)"""
    bot = Bot(token=token)

    try:
        result = await bot.delete_webhook()
        if result:
            print("✅ Webhook deleted, bot switched to polling mode")
        else:
            print("❌ Failed to delete webhook")
    except Exception as e:
        print(f"❌ Error: {e}")

async def get_webhook_info(token: str):
    """Get current webhook information"""
    bot = Bot(token=token)

    try:
        webhook_info = await bot.get_webhook_info()
        print("Current Webhook Information:")
        print(f"URL: {webhook_info.url or 'Not set'}")
        print(f"Pending updates: {webhook_info.pending_update_count}")
        print(f"Last error date: {webhook_info.last_error_date or 'None'}")
        print(f"Last error message: {webhook_info.last_error_message or 'None'}")
        print(f"Max connections: {webhook_info.max_connections}")
        print(f"Allowed updates: {webhook_info.allowed_updates or 'All'}")
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    parser = argparse.ArgumentParser(description="Telegram Bot Webhook Management Tool")
    parser.add_argument("action", choices=["set", "delete", "info"],
                       help="Action type: set (configure), delete (remove), info (view information)")
    parser.add_argument("--token", help="Bot token (or set BOT_TOKEN environment variable)")
    parser.add_argument("--url", help="Webhook URL (only for set operation)")
    parser.add_argument("--secret", help="Secret token for webhook verification (optional)")

    args = parser.parse_args()

    # Get token
    token = args.token or os.getenv('BOT_TOKEN')
    if not token:
        print("❌ Please provide bot token (--token parameter or BOT_TOKEN environment variable)")
        return

    if args.action == "set":
        webhook_url = args.url or os.getenv('WEBHOOK_URL')
        if not webhook_url:
            print("❌ Please provide webhook URL (--url parameter or WEBHOOK_URL environment variable)")
            return

        if not webhook_url.startswith('https://'):
            print("❌ Webhook URL must use HTTPS protocol")
            return

        secret_token = args.secret or os.getenv('WEBHOOK_SECRET_TOKEN')
        asyncio.run(set_webhook(token, webhook_url, secret_token))

    elif args.action == "delete":
        asyncio.run(delete_webhook(token))

    elif args.action == "info":
        asyncio.run(get_webhook_info(token))

if __name__ == "__main__":
    main()