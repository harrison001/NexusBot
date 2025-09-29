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

# Load environment variables
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
        Thoroughly clean up session data and free all memory
        """
        # Clear image path list
        self.images.clear()

        # Delete temporary directory and all files
        if os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                logger.error(f"Error cleaning temporary directory: {e}")

        # Update last activity time to cleanup time
        self.last_activity = datetime.now()

class Img2PDFBot:
    def __init__(self):
        self.user_sessions: Dict[int, UserSession] = defaultdict(UserSession)
        self.supported_extensions = ['.png', '.jpeg', '.jpg']
        if HEIF_AVAILABLE:
            self.supported_extensions.extend(['.heic', '.heif'])

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        welcome_message = (
            "Welcome to the Image to PDF Bot! 📄\n\n"
            "How to use:\n"
            "1. Send one or multiple images to me\n"
            "2. Click the 'Generate PDF' button\n"
            "3. Receive the merged PDF file\n\n"
            f"Supported formats: {', '.join(self.supported_extensions)}\n\n"
            "Commands:\n"
            "/start - Show welcome message\n"
            "/help - Show help information\n"
            "/clear - Clear current images"
        )
        await update.message.reply_text(welcome_message)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = (
            "📖 Usage Help:\n\n"
            "1. Send images directly: Add images to current session\n"
            "2. Send multiple images: They will be arranged in sending order\n"
            "3. Generate PDF: Click button to merge all images into PDF\n"
            "4. Clear images: Use /clear command\n\n"
            "Important notes:\n"
            "• Images will be arranged in PDF in sending order\n"
            "• Supports transparent background images (auto-converted to white background)\n"
            "• Sessions will be automatically cleaned after 30 minutes of inactivity"
        )
        await update.message.reply_text(help_text)

    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        session = self.user_sessions[user_id]
        session.clear()
        await update.message.reply_text("✅ All images cleared. You can start sending images again.")

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
                [InlineKeyboardButton("📄 Generate PDF", callback_data="generate_pdf")],
                [InlineKeyboardButton("🗑️ Clear Images", callback_data="clear_images")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                f"✅ Image received! Currently have {len(session.images)} images.",
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error(f"Error processing image: {e}")
            await update.message.reply_text("❌ Error processing image, please try again.")

    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        session = self.user_sessions[user_id]

        document = update.message.document
        if not document.file_name:
            await update.message.reply_text("❌ Unable to recognize file type.")
            return

        _, ext = os.path.splitext(document.file_name.lower())
        if ext not in self.supported_extensions:
            await update.message.reply_text(
                f"❌ Unsupported file format. Supported formats: {', '.join(self.supported_extensions)}"
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
                [InlineKeyboardButton("📄 Generate PDF", callback_data="generate_pdf")],
                [InlineKeyboardButton("🗑️ Clear Images", callback_data="clear_images")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                f"✅ Image received! Currently have {len(session.images)} images.",
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error(f"Error processing document: {e}")
            await update.message.reply_text("❌ Error processing image, please try again.")

    def images_to_pdf(self, image_paths: List[str], pdf_path: str) -> bool:
        """
        Optimized PDF generation method to avoid memory leaks
        """
        images = []
        try:
            # Process images one by one with explicit memory management
            for image_path in image_paths:
                try:
                    with Image.open(image_path) as img:
                        # Convert color mode
                        if img.mode in ('RGBA', 'P', 'L') or img.mode != 'RGB':
                            # Create RGB copy
                            rgb_img = img.convert('RGB')
                            images.append(rgb_img)
                        else:
                            # Create copy to avoid file handle issues
                            rgb_img = img.copy()
                            images.append(rgb_img)
                except Exception as e:
                    logger.error(f"Cannot open image file {image_path}: {e}")
                    continue

            if not images:
                return False

            try:
                # Generate PDF
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
                logger.error(f"Error saving PDF: {e}")
                return False

        except Exception as e:
            logger.error(f"Error generating PDF: {e}")
            return False

        finally:
            # Explicitly clean up PIL objects
            for img in images:
                try:
                    img.close()
                except:
                    pass
            images.clear()

            # Force garbage collection
            gc.collect()

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        session = self.user_sessions[user_id]

        if query.data == "generate_pdf":
            if not session.images:
                await query.edit_message_text("❌ No images to convert. Please send images first.")
                return

            await query.edit_message_text("🔄 Generating PDF, please wait...")

            try:
                pdf_filename = f"images_to_pdf_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                pdf_path = os.path.join(session.temp_dir, pdf_filename)

                if self.images_to_pdf(session.images, pdf_path):
                    with open(pdf_path, 'rb') as pdf_file:
                        await context.bot.send_document(
                            chat_id=update.effective_chat.id,
                            document=pdf_file,
                            filename=pdf_filename,
                            caption=f"✅ PDF generated successfully! Contains {len(session.images)} images."
                        )

                    session.clear()
                    # Force garbage collection释放内存
                    gc.collect()
                    await query.edit_message_text("✅ PDF sent! Session cleared, you can send new images.")
                else:
                    await query.edit_message_text("❌ Failed to generate PDF, please try again.")

            except Exception as e:
                logger.error(f"Error sending PDF: {e}")
                await query.edit_message_text("❌ Error sending PDF, please try again.")

        elif query.data == "clear_images":
            session.clear()
            # Force garbage collection释放内存
            gc.collect()
            await query.edit_message_text("✅ All images cleared.")

    async def cleanup_old_sessions(self, context: ContextTypes.DEFAULT_TYPE):
        """
        Improved session cleanup mechanism with more aggressive memory release
        """
        cutoff_time = datetime.now() - timedelta(minutes=30)
        users_to_remove = []

        for user_id, session in self.user_sessions.items():
            if session.last_activity < cutoff_time:
                # Clean up session data and temporary files
                session.cleanup()
                users_to_remove.append(user_id)

        # Completely remove expired sessions from dictionary
        for user_id in users_to_remove:
            del self.user_sessions[user_id]

        # Execute garbage collection if sessions were cleaned
        if users_to_remove:
            gc.collect()
            # Get memory usage information
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            logger.info(f"Cleaned {len(users_to_remove)} expired sessions and freed memory, current memory usage: {memory_mb:.1f}MB")
        else:
            logger.info("No expired sessions to clean")

        # Log current active session count (for monitoring)
        logger.info(f"Current active sessions: {len(self.user_sessions)}")

# Global variables
app = FastAPI(title="Telegram Image to PDF Bot")
bot_instance = None
application = None

async def setup_bot():
    global bot_instance, application

    token = os.getenv('BOT_TOKEN')
    if not token:
        logger.error("Please set the BOT_TOKEN environment variable")
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

    logger.info("Bot initialization completed")

@app.on_event("startup")
async def startup_event():
    await setup_bot()

@app.on_event("shutdown")
async def shutdown_event():
    global application
    if application:
        await application.stop()
        await application.shutdown()

# Telegram official IP ranges
TELEGRAM_IP_RANGES = [
    ipaddress.ip_network("149.154.160.0/20"),
    ipaddress.ip_network("91.108.4.0/22"),
]

def verify_telegram_ip(client_ip: str) -> bool:
    """Verify if request comes from official Telegram IP"""
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

    # Verify IP address (check X-Forwarded-For if there's a proxy)
    client_ip = request.headers.get("X-Forwarded-For", request.client.host).split(",")[0].strip()

    # Enable IP verification in production environment
    webhook_verify_ip = os.getenv('WEBHOOK_VERIFY_IP', 'false').lower() == 'true'
    if webhook_verify_ip and not verify_telegram_ip(client_ip):
        logger.warning(f"Webhook request from unauthorized IP: {client_ip}")
        raise HTTPException(status_code=403, detail="Unauthorized IP")

    # Verify Secret Token (if set)
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