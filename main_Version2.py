"""
Voice AI Study Planner + Focus Tracker

Main entry point for the application.

This system allows students to:
1. Speak tasks via Telegram voice messages
2. AI automatically parses and schedules them
3. Laptop sends reminders when task time arrives
4. Camera monitors focus during study sessions

Usage:
    python main.py             # Start the full system
    python main.py --bot       # Start only the Telegram bot
    python main.py --focus     # Start only the focus tracker
    python main.py --schedule  # Show today's schedule
"""

import argparse
import logging
import signal
import sys
import threading
from datetime import datetime

from config.settings import LOG_LEVEL


def setup_logging() -> None:
    """Configure application-wide logging."""
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("study_planner.log", mode="a"),
        ],
    )


def print_banner() -> None:
    """Print a welcome banner."""
    banner = """
    ╔══════════════════════════════════════════════════╗
    ║   🎙️  Voice AI Study Planner + Focus Tracker    ║
    ║                                                  ║
    ║   Speak your tasks. AI plans your day.           ║
    ║   Camera keeps you focused.                      ║
    ║                                                  ║
    ║   100% Free & Open Source                        ║
    ╚══════════════════════════════════════════════════╝
    """
    print(banner)
    print(f"    📅 {datetime.now().strftime('%A, %B %d, %Y %H:%M')}")
    print()


def run_bot_mode() -> None:
    """Run only the Telegram bot."""
    from voice_bot.telegram_bot import run_telegram_bot

    logger = logging.getLogger(__name__)
    logger.info("Starting in BOT mode...")
    print("🤖 Starting Telegram bot...")
    print("   Send a voice message to your bot to add tasks!")
    print("   Press Ctrl+C to stop.\n")
    run_telegram_bot()


def run_focus_mode(task_id: int = None) -> None:
    """Run only the focus tracker."""
    from focus_tracker.camera_focus import run_focus_tracker

    logger = logging.getLogger(__name__)
    logger.info("Starting in FOCUS mode...")
    print("👁️ Starting focus tracker...")
    print("   Look at your screen to stay focused!")
    print("   Press 'q' in the camera window to stop.\n")
    run_focus_tracker(task_id=task_id)


def show_schedule() -> None:
    """Display today's schedule."""
    from database.db_manager import DatabaseManager

    db = DatabaseManager()
    schedule = db.get_today_schedule()
    pending = db.get_pending_tasks()

    print("\n📅 TODAY'S SCHEDULE")
    print("=" * 50)

    if schedule:
        for entry in schedule:
            status = "✅" if entry["completed"] else "⏰"
            print(
                f"  {status} {entry['start_time']} - {entry['end_time']}: "
                f"{entry['task_name']} (P{entry['priority']})"
            )
    else:
        print("  No tasks scheduled for today.")

    print(f"\n📋 PENDING TASKS ({len(pending)} total)")
    print("=" * 50)

    priority_emoji = {1: "🔴", 2: "🟠", 3: "🟡", 4: "🟢"}
    for task in pending:
        emoji = priority_emoji.get(task["priority"], "⚪")
        print(
            f"  {emoji} [{task['category']}] {task['task_name']} "
            f"— Due: {task['deadline'] or 'unset'}"
        )

    if not pending:
        print("  All caught up! 🎉")

    # Focus stats
    stats = db.get_focus_stats(days=7)
    if stats["total_sessions"] > 0:
        print(f"\n📊 FOCUS STATS (Past 7 Days)")
        print("=" * 50)
        print(f"  Sessions: {stats['total_sessions']}")
        print(f"  Avg Focus: {stats['avg_focus_pct']:.1f}%")
        total_hours = (stats["total_focused"] + stats["total_distracted"]) / 3600
        print(f"  Total Time: {total_hours:.1f} hours")

    print()


def run_full_system() -> None:
    """
    Run the complete system: bot + scheduler + reminder checker.

    The Telegram bot runs in a thread, while the main thread
    handles scheduling and periodic checks.
    """
    from voice_bot.telegram_bot import run_telegram_bot
    from database.db_manager import DatabaseManager
    from scheduler.task_scheduler import TaskScheduler
    from notifications.notify import send_notification

    logger = logging.getLogger(__name__)
    logger.info("Starting FULL system...")

    print("🚀 Starting full system...")
    print("   📱 Telegram bot: Active")
    print("   ⏰ Task scheduler: Active")
    print("   🔔 Reminder system: Active")
    print()
    print("   The focus tracker runs separately:")
    print("   python main.py --focus")
    print()
    print("   Press Ctrl+C to stop everything.\n")

    # Initialize components
    scheduler = TaskScheduler()
    db = DatabaseManager()

    # Start the Telegram bot in a background thread
    bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    bot_thread.start()

    # Handle graceful shutdown
    def shutdown(signum, frame):
        logger.info("Shutdown signal received")
        print("\n\n👋 Shutting down gracefully...")
        scheduler.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Send startup notification
    send_notification(
        title="🎙️ Study Planner Active",
        message="Your voice AI study planner is running!",
    )

    # Keep main thread alive
    bot_thread.join()


def main() -> None:
    """Parse arguments and run the appropriate mode."""
    setup_logging()
    print_banner()

    parser = argparse.ArgumentParser(
        description="Voice AI Study Planner + Focus Tracker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python main.py             # Full system (bot + scheduler + reminders)
    python main.py --bot       # Telegram bot only
    python main.py --focus     # Focus tracker only
    python main.py --focus 5   # Focus tracker for task ID 5
    python main.py --schedule  # Show today's schedule
        """,
    )
    parser.add_argument(
        "--bot", action="store_true", help="Run only the Telegram bot"
    )
    parser.add_argument(
        "--focus",
        nargs="?",
        const=True,
        default=False,
        help="Run only the focus tracker (optionally pass task ID)",
    )
    parser.add_argument(
        "--schedule", action="store_true", help="Show today's schedule and exit"
    )

    args = parser.parse_args()

    if args.schedule:
        show_schedule()
    elif args.bot:
        run_bot_mode()
    elif args.focus is not False:
        task_id = int(args.focus) if args.focus is not True else None
        run_focus_mode(task_id=task_id)
    else:
        run_full_system()


if __name__ == "__main__":
    main()