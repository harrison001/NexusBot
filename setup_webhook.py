#!/usr/bin/env python3
"""
Telegram Bot Webhook 设置脚本
用于设置和管理Telegram bot的webhook
"""

import os
import asyncio
import argparse
from telegram import Bot

async def set_webhook(token: str, webhook_url: str, secret_token: str = None):
    """设置webhook"""
    bot = Bot(token=token)

    try:
        # 设置webhook
        if secret_token:
            result = await bot.set_webhook(url=webhook_url, secret_token=secret_token)
            print(f"✅ Webhook设置成功: {webhook_url} (with secret token)")
        else:
            result = await bot.set_webhook(url=webhook_url)
            print(f"✅ Webhook设置成功: {webhook_url} (no secret token)")

        if not result:
            print("❌ Webhook设置失败")

        # 获取webhook信息
        webhook_info = await bot.get_webhook_info()
        print(f"\n当前Webhook信息:")
        print(f"URL: {webhook_info.url}")
        print(f"待处理更新数: {webhook_info.pending_update_count}")
        print(f"最后错误日期: {webhook_info.last_error_date}")
        print(f"最后错误信息: {webhook_info.last_error_message}")

    except Exception as e:
        print(f"❌ 错误: {e}")

async def delete_webhook(token: str):
    """删除webhook（切换回polling模式）"""
    bot = Bot(token=token)

    try:
        result = await bot.delete_webhook()
        if result:
            print("✅ Webhook已删除，bot切换到polling模式")
        else:
            print("❌ 删除webhook失败")
    except Exception as e:
        print(f"❌ 错误: {e}")

async def get_webhook_info(token: str):
    """获取当前webhook信息"""
    bot = Bot(token=token)

    try:
        webhook_info = await bot.get_webhook_info()
        print("当前Webhook信息:")
        print(f"URL: {webhook_info.url or '未设置'}")
        print(f"待处理更新数: {webhook_info.pending_update_count}")
        print(f"最后错误日期: {webhook_info.last_error_date or '无'}")
        print(f"最后错误信息: {webhook_info.last_error_message or '无'}")
        print(f"最大连接数: {webhook_info.max_connections}")
        print(f"允许的更新类型: {webhook_info.allowed_updates or '全部'}")
    except Exception as e:
        print(f"❌ 错误: {e}")

def main():
    parser = argparse.ArgumentParser(description="Telegram Bot Webhook管理工具")
    parser.add_argument("action", choices=["set", "delete", "info"],
                       help="操作类型: set(设置), delete(删除), info(查看信息)")
    parser.add_argument("--token", help="Bot token (或设置BOT_TOKEN环境变量)")
    parser.add_argument("--url", help="Webhook URL (仅用于set操作)")
    parser.add_argument("--secret", help="Secret token for webhook verification (可选)")

    args = parser.parse_args()

    # 获取token
    token = args.token or os.getenv('BOT_TOKEN')
    if not token:
        print("❌ 请提供bot token (--token 参数或BOT_TOKEN环境变量)")
        return

    if args.action == "set":
        webhook_url = args.url or os.getenv('WEBHOOK_URL')
        if not webhook_url:
            print("❌ 请提供webhook URL (--url 参数或WEBHOOK_URL环境变量)")
            return

        if not webhook_url.startswith('https://'):
            print("❌ Webhook URL必须使用HTTPS协议")
            return

        secret_token = args.secret or os.getenv('WEBHOOK_SECRET_TOKEN')
        asyncio.run(set_webhook(token, webhook_url, secret_token))

    elif args.action == "delete":
        asyncio.run(delete_webhook(token))

    elif args.action == "info":
        asyncio.run(get_webhook_info(token))

if __name__ == "__main__":
    main()