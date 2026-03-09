"""
Centralized configuration for Voice AI Study Planner.

All settings are loaded from environment variables or use sensible defaults.
This module is imported by every other module so changes propagate everywhere.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()

# ──────────────────────────── Paths ────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATABASE_PATH = PROJECT_ROOT / "study_planner.db"
AUDIO_DOWNLOAD_DIR = PROJECT_ROOT / "temp_audio"

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
AUDIO_DOWNLOAD_DIR.mkdir(exist_ok=True)

# ──────────────────────────── Telegram ────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# ──────────────────────────── Whisper ────────────────────────────
# Model sizes: tiny, base, small, medium, large
# "base" is a good balance of speed and accuracy for most machines
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")

# ──────────────────────────── Ollama ────────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# ──────────────────────────── Scheduler ────────────────────────────
TIMETABLE_PATH = DATA_DIR / "weekly_timetable.json"
REMINDER_MINUTES_BEFORE = int(os.getenv("REMINDER_MINUTES_BEFORE", "30"))

# ──────────────────────────── Focus Tracker ────────────────────────────
# How many consecutive seconds of distraction before warning
DISTRACTION_THRESHOLD_SECONDS = int(os.getenv("DISTRACTION_THRESHOLD_SECONDS", "5"))
# Camera index (0 = default webcam)
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))

# ──────────────────────────── Logging ────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")