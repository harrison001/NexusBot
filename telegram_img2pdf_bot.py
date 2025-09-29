import os
import logging
import tempfile
import shutil
import uuid
import time
import gc
import psutil
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List
from PIL import Image
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIF_AVAILABLE = True
except ImportError:
    HEIF_AVAILABLE = False

from fastapi import FastAPI, Request, BackgroundTasks, HTTPException, Header
import ipaddress
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
import asyncio

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class UserSession:
    def __init__(self):
        self.images: List[str] = []
        self.temp_dir = tempfile.mkdtemp()
        self.last_activity = datetime.now()

    def add_image(self, image_path: str):
        self.images.append(image_path)
        self.last_activity = datetime.now()

    def clear(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        self.images.clear()
        self.temp_dir = tempfile.mkdtemp()
        self.last_activity = datetime.now()

    def cleanup(self):
        """
        彻底清理会话数据，释放所有内存
        """
        # 清理图片路径列表
        self.images.clear()

        # 删除临时目录及所有文件
        if os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                logger.error(f"清理临时目录时出错: {e}")

        # 更新最后活动时间为清理时间
        self.last_activity = datetime.now()

class Img2PDFBot:
    def __init__(self):
        self.user_sessions: Dict[int, UserSession] = defaultdict(UserSession)
        self.supported_extensions = ['.png', '.jpeg', '.jpg']
        if HEIF_AVAILABLE:
            self.supported_extensions.extend(['.heic', '.heif'])

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        welcome_message = (
            "欢迎使用图片转PDF机器人！📄\n\n"
            "使用方法:\n"
            "1. 发送一张或多张图片给我\n"
            "2. 点击'生成PDF'按钮\n"
            "3. 接收合并后的PDF文件\n\n"
            f"支持的格式: {', '.join(self.supported_extensions)}\n\n"
            "命令:\n"
            "/start - 显示欢迎信息\n"
            "/help - 显示帮助信息\n"
            "/clear - 清空当前图片"
        )
        await update.message.reply_text(welcome_message)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = (
            "📖 使用帮助:\n\n"
            "1. 直接发送图片: 将图片添加到当前会话\n"
            "2. 发送多张图片: 按发送顺序排列\n"
            "3. 生成PDF: 点击按钮将所有图片合并为PDF\n"
            "4. 清空图片: 使用 /clear 命令\n\n"
            "注意事项:\n"
            "• 图片会按发送顺序排列在PDF中\n"
            "• 支持透明背景图片（自动转换为白色背景）\n"
            "• 会话会在30分钟无活动后自动清理"
        )
        await update.message.reply_text(help_text)

    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        session = self.user_sessions[user_id]
        session.clear()
        await update.message.reply_text("✅ 已清空所有图片，可以重新开始发送图片。")

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        session = self.user_sessions[user_id]

        try:
            photo = update.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)

            file_extension = '.jpg'
            if file.file_path:
                _, ext = os.path.splitext(file.file_path)
                if ext.lower() in self.supported_extensions:
                    file_extension = ext

            # Use timestamp and UUID to ensure unique filename and avoid race conditions
            unique_id = f"{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
            image_path = os.path.join(
                session.temp_dir,
                f"image_{unique_id}{file_extension}"
            )

            await file.download_to_drive(image_path)
            session.add_image(image_path)

            keyboard = [
                [InlineKeyboardButton("📄 生成PDF", callback_data="generate_pdf")],
                [InlineKeyboardButton("🗑️ 清空图片", callback_data="clear_images")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                f"✅ 图片已接收！当前共有 {len(session.images)} 张图片。",
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error(f"处理图片时出错: {e}")
            await update.message.reply_text("❌ 处理图片时出错，请重试。")

    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        session = self.user_sessions[user_id]

        document = update.message.document
        if not document.file_name:
            await update.message.reply_text("❌ 无法识别文件类型。")
            return

        _, ext = os.path.splitext(document.file_name.lower())
        if ext not in self.supported_extensions:
            await update.message.reply_text(
                f"❌ 不支持的文件格式。支持的格式: {', '.join(self.supported_extensions)}"
            )
            return

        try:
            file = await context.bot.get_file(document.file_id)
            # Use timestamp and UUID to ensure unique filename and avoid race conditions
            unique_id = f"{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
            image_path = os.path.join(
                session.temp_dir,
                f"image_{unique_id}{ext}"
            )

            await file.download_to_drive(image_path)
            session.add_image(image_path)

            keyboard = [
                [InlineKeyboardButton("📄 生成PDF", callback_data="generate_pdf")],
                [InlineKeyboardButton("🗑️ 清空图片", callback_data="clear_images")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                f"✅ 图片已接收！当前共有 {len(session.images)} 张图片。",
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error(f"处理文档时出错: {e}")
            await update.message.reply_text("❌ 处理图片时出错，请重试。")

    def images_to_pdf(self, image_paths: List[str], pdf_path: str) -> bool:
        """
        优化的PDF生成方法，避免内存泄漏
        """
        images = []
        try:
            # 逐个处理图片，显式管理内存
            for image_path in image_paths:
                try:
                    with Image.open(image_path) as img:
                        # 转换颜色模式
                        if img.mode in ('RGBA', 'P', 'L') or img.mode != 'RGB':
                            # 创建RGB副本
                            rgb_img = img.convert('RGB')
                            images.append(rgb_img)
                        else:
                            # 创建副本以避免文件句柄问题
                            rgb_img = img.copy()
                            images.append(rgb_img)
                except Exception as e:
                    logger.error(f"无法打开图像文件 {image_path}: {e}")
                    continue

            if not images:
                return False

            try:
                # 生成PDF
                if len(images) == 1:
                    images[0].save(pdf_path, resolution=100.0, optimize=True)
                else:
                    images[0].save(
                        pdf_path,
                        save_all=True,
                        append_images=images[1:],
                        resolution=100.0,
                        optimize=True
                    )

                return True

            except Exception as e:
                logger.error(f"保存PDF时出错: {e}")
                return False

        except Exception as e:
            logger.error(f"生成PDF时出错: {e}")
            return False

        finally:
            # 显式清理PIL对象
            for img in images:
                try:
                    img.close()
                except:
                    pass
            images.clear()

            # 强制垃圾回收
            gc.collect()

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        session = self.user_sessions[user_id]

        if query.data == "generate_pdf":
            if not session.images:
                await query.edit_message_text("❌ 没有图片可以转换。请先发送图片。")
                return

            await query.edit_message_text("🔄 正在生成PDF，请稍候...")

            try:
                pdf_filename = f"images_to_pdf_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                pdf_path = os.path.join(session.temp_dir, pdf_filename)

                if self.images_to_pdf(session.images, pdf_path):
                    with open(pdf_path, 'rb') as pdf_file:
                        await context.bot.send_document(
                            chat_id=update.effective_chat.id,
                            document=pdf_file,
                            filename=pdf_filename,
                            caption=f"✅ PDF生成完成！包含 {len(session.images)} 张图片。"
                        )

                    session.clear()
                    # 强制垃圾回收释放内存
                    gc.collect()
                    await query.edit_message_text("✅ PDF已发送！会话已清空，可以发送新的图片。")
                else:
                    await query.edit_message_text("❌ 生成PDF失败，请重试。")

            except Exception as e:
                logger.error(f"发送PDF时出错: {e}")
                await query.edit_message_text("❌ 发送PDF时出错，请重试。")

        elif query.data == "clear_images":
            session.clear()
            # 强制垃圾回收释放内存
            gc.collect()
            await query.edit_message_text("✅ 已清空所有图片。")

    async def cleanup_old_sessions(self, context: ContextTypes.DEFAULT_TYPE):
        """
        改进的会话清理机制，更积极地释放内存
        """
        cutoff_time = datetime.now() - timedelta(minutes=30)
        users_to_remove = []

        for user_id, session in self.user_sessions.items():
            if session.last_activity < cutoff_time:
                # 清理会话数据和临时文件
                session.cleanup()
                users_to_remove.append(user_id)

        # 从字典中完全删除过期会话
        for user_id in users_to_remove:
            del self.user_sessions[user_id]

        # 如果清理了会话，执行垃圾回收
        if users_to_remove:
            gc.collect()
            # 获取内存使用情况
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            logger.info(f"清理了 {len(users_to_remove)} 个过期会话并释放内存，当前内存使用: {memory_mb:.1f}MB")
        else:
            logger.info("没有过期会话需要清理")

        # 记录当前活跃会话数量（用于监控）
        logger.info(f"当前活跃会话数: {len(self.user_sessions)}")

# Global variables
app = FastAPI(title="Telegram Image to PDF Bot")
bot_instance = None
application = None

async def setup_bot():
    global bot_instance, application

    token = os.getenv('BOT_TOKEN')
    if not token:
        logger.error("请设置环境变量 BOT_TOKEN")
        raise ValueError("BOT_TOKEN environment variable is required")

    bot_instance = Img2PDFBot()
    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", bot_instance.start))
    application.add_handler(CommandHandler("help", bot_instance.help_command))
    application.add_handler(CommandHandler("clear", bot_instance.clear_command))
    application.add_handler(MessageHandler(filters.PHOTO, bot_instance.handle_photo))
    application.add_handler(MessageHandler(filters.Document.ALL, bot_instance.handle_document))
    application.add_handler(CallbackQueryHandler(bot_instance.button_callback))

    job_queue = application.job_queue
    job_queue.run_repeating(bot_instance.cleanup_old_sessions, interval=300, first=300)

    await application.initialize()
    await application.start()

    webhook_url = os.getenv('WEBHOOK_URL')
    if webhook_url:
        webhook_secret = os.getenv('WEBHOOK_SECRET_TOKEN')
        if webhook_secret:
            await application.bot.set_webhook(
                url=f"{webhook_url}/webhook",
                secret_token=webhook_secret
            )
            logger.info(f"Webhook set to: {webhook_url}/webhook (with secret token)")
        else:
            await application.bot.set_webhook(url=f"{webhook_url}/webhook")
            logger.info(f"Webhook set to: {webhook_url}/webhook (no secret token)")

    logger.info("Bot初始化完成")

@app.on_event("startup")
async def startup_event():
    await setup_bot()

@app.on_event("shutdown")
async def shutdown_event():
    global application
    if application:
        await application.stop()
        await application.shutdown()

# Telegram官方IP段
TELEGRAM_IP_RANGES = [
    ipaddress.ip_network("149.154.160.0/20"),
    ipaddress.ip_network("91.108.4.0/22"),
]

def verify_telegram_ip(client_ip: str) -> bool:
    """验证请求是否来自Telegram官方IP"""
    try:
        ip = ipaddress.ip_address(client_ip)
        return any(ip in network for network in TELEGRAM_IP_RANGES)
    except ValueError:
        return False

@app.post("/webhook")
async def webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_telegram_bot_api_secret_token: str = Header(None)
):
    global application

    if not application:
        raise HTTPException(status_code=503, detail="Bot not initialized")

    # 验证IP地址 (如果有代理，检查X-Forwarded-For)
    client_ip = request.headers.get("X-Forwarded-For", request.client.host).split(",")[0].strip()

    # 在生产环境中启用IP验证
    webhook_verify_ip = os.getenv('WEBHOOK_VERIFY_IP', 'false').lower() == 'true'
    if webhook_verify_ip and not verify_telegram_ip(client_ip):
        logger.warning(f"Webhook request from unauthorized IP: {client_ip}")
        raise HTTPException(status_code=403, detail="Unauthorized IP")

    # 验证Secret Token (如果设置了)
    webhook_secret = os.getenv('WEBHOOK_SECRET_TOKEN')
    if webhook_secret and x_telegram_bot_api_secret_token != webhook_secret:
        logger.warning(f"Webhook request with invalid secret token from IP: {client_ip}")
        raise HTTPException(status_code=403, detail="Invalid secret token")

    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)

        if update:
            background_tasks.add_task(process_update, update)

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=400, detail="Invalid request data")

async def process_update(update: Update):
    global application
    await application.process_update(update)

@app.get("/")
async def root():
    return {"message": "Telegram Image to PDF Bot is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

def main():
    import uvicorn
    port = int(os.getenv('PORT', 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == '__main__':
    main()