"""
Desktop Notification System using Plyer.

Sends native desktop notifications on macOS and Linux.
Used to remind the user when a scheduled task is about to start.

On macOS: Uses Notification Center
On Linux: Uses libnotify (install: sudo apt install libnotify-bin)
"""

import logging
import platform
from plyer import notification

logger = logging.getLogger(__name__)


def send_notification(
    title: str = "📌 Study Planner",
    message: str = "You have an upcoming task!",
    timeout: int = 10,
) -> None:
    """
    Send a desktop notification.

    Args:
        title: Notification title.
        message: Notification body text.
        timeout: How long the notification stays visible (seconds).
                 Note: macOS ignores this value.

    Example:
        >>> send_notification(
        ...     title="📌 Task Starting Soon!",
        ...     message="OS Assignment starts in 30 minutes",
        ...     timeout=15
        ... )
    """
    try:
        notification.notify(
            title=title,
            message=message,
            timeout=timeout,
            app_name="Study Planner",
        )
        logger.info(f"Notification sent: {title} — {message}")
    except Exception as e:
        # Notifications are non-critical; log and continue
        logger.warning(f"Failed to send notification: {e}")

        # Fallback: print to console
        _console_fallback(title, message)


def send_focus_warning(status: str = "distracted") -> None:
    """
    Send a focus-related warning notification.

    Args:
        status: Current focus status ('distracted', 'away', 'drowsy').
    """
    messages = {
        "distracted": (
            "😠 Stay Focused!",
            "You seem distracted. Look at your screen and keep working!",
        ),
        "away": (
            "👋 Where Did You Go?",
            "Your face is not detected. Come back to your desk!",
        ),
        "drowsy": (
            "😴 Wake Up!",
            "You look tired. Take a short break and come back refreshed!",
        ),
    }

    title, message = messages.get(
        status, ("⚠️ Focus Check", "Please stay focused on your task.")
    )
    send_notification(title=title, message=message, timeout=5)


def send_session_summary(
    focused_minutes: int,
    distracted_minutes: int,
    focus_percentage: float,
) -> None:
    """
    Send a summary notification at the end of a focus session.

    Args:
        focused_minutes: Total minutes focused.
        distracted_minutes: Total minutes distracted.
        focus_percentage: Focus percentage (0-100).
    """
    # Choose emoji based on performance
    if focus_percentage >= 80:
        emoji = "🌟"
        grade = "Excellent!"
    elif focus_percentage >= 60:
        emoji = "👍"
        grade = "Good job!"
    elif focus_percentage >= 40:
        emoji = "😐"
        grade = "Could be better"
    else:
        emoji = "😞"
        grade = "Needs improvement"

    message = (
        f"{grade}\n"
        f"⏱️ Focused: {focused_minutes} min\n"
        f"😶 Distracted: {distracted_minutes} min\n"
        f"📊 Focus: {focus_percentage:.0f}%"
    )

    send_notification(
        title=f"{emoji} Focus Session Complete",
        message=message,
        timeout=15,
    )


def _console_fallback(title: str, message: str) -> None:
    """Print notification to console when desktop notifications fail."""
    system = platform.system()
    logger.info(f"Console fallback ({system}): [{title}] {message}")
    print(f"\n{'='*50}")
    print(f"🔔 {title}")
    print(f"   {message}")
    print(f"{'='*50}\n")