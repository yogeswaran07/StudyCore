"""
Telegram Bot module for Voice AI Study Planner.

This bot listens for voice messages from the user, downloads the audio,
transcribes it using Whisper, parses the task using the local LLM,
schedules it, and confirms back to the user.
"""

import logging
import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config.settings import TELEGRAM_BOT_TOKEN, AUDIO_DOWNLOAD_DIR
from speech.speech_to_text import transcribe_audio
from ai_parser.task_parser import parse_task
from database.db_manager import DatabaseManager
from scheduler.task_scheduler import TaskScheduler

logger = logging.getLogger(__name__)

# Initialize shared resources
db = DatabaseManager()
scheduler = TaskScheduler()


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command — greet the user."""
    welcome_message = (
        "🎙️ *Voice AI Study Planner*\n\n"
        "Welcome! I help you manage your study tasks using voice.\n\n"
        "📌 *How to use:*\n"
        "1. Send me a voice message describing your task\n"
        "   Example: _'Finish OS assignment by tomorrow'_\n"
        "2. I'll understand it, prioritize it, and schedule it\n"
        "3. You'll get reminders on your laptop!\n\n"
        "📋 *Commands:*\n"
        "/start — Show this message\n"
        "/tasks — List all your pending tasks\n"
        "/today — Show today's schedule\n"
        "/clear — Clear all completed tasks\n"
        "/help — Get help\n\n"
        "Just send a voice message to get started! 🚀"
    )
    await update.message.reply_text(welcome_message, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /help command."""
    help_text = (
        "🆘 *Help*\n\n"
        "Send a voice message like:\n"
        "• _'Study for math exam on Friday'_\n"
        "• _'Complete database project tonight'_\n"
        "• _'Read chapter 5 of algorithms book'_\n\n"
        "I will:\n"
        "✅ Convert your speech to text\n"
        "✅ Detect the task, priority, and deadline\n"
        "✅ Schedule it in your free time\n"
        "✅ Remind you on your laptop\n"
        "✅ Track your focus while you work"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /tasks command — list all pending tasks."""
    tasks = db.get_pending_tasks()

    if not tasks:
        await update.message.reply_text("✅ No pending tasks! You're all caught up. 🎉")
        return

    # Build a formatted task list
    lines = ["📋 *Your Pending Tasks:*\n"]
    priority_emoji = {1: "🔴", 2: "🟠", 3: "🟡", 4: "🟢"}

    for task in tasks:
        emoji = priority_emoji.get(task["priority"], "⚪")
        deadline_str = task["deadline"] if task["deadline"] else "No deadline"
        lines.append(
            f"{emoji} *{task['task_name']}*\n"
            f"   Priority: {task['priority']} | "
            f"Deadline: {deadline_str} | "
            f"Category: {task['category']}\n"
        )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def today_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /today command — show today's scheduled tasks."""
    schedule = db.get_today_schedule()

    if not schedule:
        await update.message.reply_text("📅 Nothing scheduled for today!")
        return

    lines = ["📅 *Today's Schedule:*\n"]
    for entry in schedule:
        lines.append(
            f"⏰ {entry['start_time']} - {entry['end_time']}: "
            f"*{entry['task_name']}*"
        )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def clear_completed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /clear command — remove completed tasks."""
    count = db.clear_completed_tasks()
    await update.message.reply_text(f"🗑️ Cleared {count} completed task(s).")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle incoming voice messages.

    Flow:
    1. Download the voice .ogg file
    2. Transcribe with Whisper
    3. Parse with LLM
    4. Store in database
    5. Schedule the task
    6. Confirm to user
    """
    await update.message.reply_text("🎧 Received your voice message! Processing...")

    try:
        # Step 1: Download audio file
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)
        audio_path = os.path.join(AUDIO_DOWNLOAD_DIR, f"{voice.file_id}.ogg")
        await file.download_to_drive(audio_path)
        logger.info(f"Downloaded voice message to {audio_path}")

        # Step 2: Transcribe audio to text
        await update.message.reply_text("📝 Transcribing your voice...")
        transcribed_text = transcribe_audio(audio_path)
        logger.info(f"Transcription: {transcribed_text}")

        if not transcribed_text or transcribed_text.strip() == "":
            await update.message.reply_text(
                "❌ Could not understand the audio. Please try again."
            )
            return

        await update.message.reply_text(f"✅ I heard: _{transcribed_text}_", parse_mode="Markdown")

        # Step 3: Parse task with AI
        await update.message.reply_text("🤖 Analyzing your task...")
        parsed_task = parse_task(transcribed_text)
        logger.info(f"Parsed task: {parsed_task}")

        if not parsed_task or "task" not in parsed_task:
            await update.message.reply_text(
                "❌ Could not understand the task. Please try again with more detail."
            )
            return

        # Step 4: Store in database
        task_id = db.add_task(
            task_name=parsed_task["task"],
            priority=parsed_task.get("priority", 3),
            deadline=parsed_task.get("deadline", ""),
            category=parsed_task.get("category", "general"),
        )
        logger.info(f"Task saved with ID: {task_id}")

        # Step 5: Schedule the task
        scheduled_slot = scheduler.schedule_task(task_id, parsed_task)

        # Step 6: Confirm to user
        priority_labels = {1: "🔴 HIGH", 2: "🟠 MEDIUM", 3: "🟡 LOW", 4: "🟢 MINIMAL"}
        priority_label = priority_labels.get(parsed_task.get("priority", 3), "⚪ UNKNOWN")

        schedule_info = ""
        if scheduled_slot:
            schedule_info = (
                f"\n📅 *Scheduled:* {scheduled_slot['day']} "
                f"{scheduled_slot['start_time']} - {scheduled_slot['end_time']}"
            )

        confirmation = (
            f"✅ *Task Added Successfully!*\n\n"
            f"📌 *Task:* {parsed_task['task']}\n"
            f"⚡ *Priority:* {priority_label}\n"
            f"📆 *Deadline:* {parsed_task.get('deadline', 'Not specified')}\n"
            f"🏷️ *Category:* {parsed_task.get('category', 'General')}"
            f"{schedule_info}\n\n"
            f"💡 You'll get a reminder on your laptop before the task starts!"
        )
        await update.message.reply_text(confirmation, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error processing voice message: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Something went wrong: {str(e)}\nPlease try again."
        )

    finally:
        # Clean up downloaded audio file
        if os.path.exists(audio_path):
            os.remove(audio_path)
            logger.debug(f"Cleaned up audio file: {audio_path}")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle text messages as an alternative to voice.

    Users can also type their tasks directly.
    """
    text = update.message.text

    if not text or text.strip() == "":
        return

    await update.message.reply_text("📝 Processing your text task...")

    try:
        # Parse with AI
        parsed_task = parse_task(text)
        logger.info(f"Parsed text task: {parsed_task}")

        if not parsed_task or "task" not in parsed_task:
            await update.message.reply_text(
                "❌ Could not understand the task. Try something like:\n"
                "_'Finish math homework by Friday'_",
                parse_mode="Markdown",
            )
            return

        # Store and schedule
        task_id = db.add_task(
            task_name=parsed_task["task"],
            priority=parsed_task.get("priority", 3),
            deadline=parsed_task.get("deadline", ""),
            category=parsed_task.get("category", "general"),
        )

        scheduled_slot = scheduler.schedule_task(task_id, parsed_task)

        priority_labels = {1: "🔴 HIGH", 2: "🟠 MEDIUM", 3: "🟡 LOW", 4: "🟢 MINIMAL"}
        priority_label = priority_labels.get(parsed_task.get("priority", 3), "⚪ UNKNOWN")

        schedule_info = ""
        if scheduled_slot:
            schedule_info = (
                f"\n📅 *Scheduled:* {scheduled_slot['day']} "
                f"{scheduled_slot['start_time']} - {scheduled_slot['end_time']}"
            )

        confirmation = (
            f"✅ *Task Added!*\n\n"
            f"📌 *Task:* {parsed_task['task']}\n"
            f"⚡ *Priority:* {priority_label}\n"
            f"📆 *Deadline:* {parsed_task.get('deadline', 'Not specified')}\n"
            f"🏷️ *Category:* {parsed_task.get('category', 'General')}"
            f"{schedule_info}"
        )
        await update.message.reply_text(confirmation, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error processing text message: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Error: {str(e)}")


def run_telegram_bot() -> None:
    """
    Initialize and run the Telegram bot.

    This is the main entry point for the bot process.
    It sets up all handlers and starts polling for updates.
    """
    if not TELEGRAM_BOT_TOKEN:
        logger.error(
            "TELEGRAM_BOT_TOKEN not set! "
            "Please add it to your .env file. "
            "Get a token from @BotFather on Telegram."
        )
        raise ValueError("TELEGRAM_BOT_TOKEN is required")

    logger.info("Starting Telegram bot...")

    # Build the application
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("tasks", list_tasks))
    app.add_handler(CommandHandler("today", today_schedule))
    app.add_handler(CommandHandler("clear", clear_completed))

    # Register message handlers
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Start the bot
    logger.info("Bot is running! Send a voice message to get started.")
    app.run_polling(drop_pending_updates=True)