"""
Speech-to-Text module using OpenAI Whisper (runs locally).

Whisper is a free, open-source speech recognition model from OpenAI.
It runs entirely on your machine — no API calls, no internet needed.

Model sizes and their trade-offs:
    - tiny   : ~39M params  | Fastest  | Lowest accuracy
    - base   : ~74M params  | Fast     | Good accuracy
    - small  : ~244M params | Moderate | Better accuracy
    - medium : ~769M params | Slow     | High accuracy
    - large  : ~1.5B params | Slowest  | Best accuracy

For most student tasks, "base" is sufficient and fast.
"""

import logging
import whisper
from config.settings import WHISPER_MODEL_SIZE

logger = logging.getLogger(__name__)

# Load the model once at module level (cached in memory)
# First run will download the model (~140MB for 'base')
_model = None


def _get_model() -> whisper.Whisper:
    """
    Lazy-load the Whisper model.

    The model is loaded once and cached for all subsequent calls.
    This avoids reloading on every transcription request.

    Returns:
        whisper.Whisper: The loaded Whisper model.
    """
    global _model
    if _model is None:
        logger.info(f"Loading Whisper model: '{WHISPER_MODEL_SIZE}'...")
        logger.info("(First run may take a minute to download the model)")
        _model = whisper.load_model(WHISPER_MODEL_SIZE)
        logger.info("Whisper model loaded successfully!")
    return _model


def transcribe_audio(audio_path: str) -> str:
    """
    Transcribe an audio file to text using Whisper.

    Args:
        audio_path: Path to the audio file (.ogg, .mp3, .wav, .m4a, etc.)
                    Whisper supports most common audio formats.

    Returns:
        str: The transcribed text, stripped of leading/trailing whitespace.
             Returns empty string if transcription fails.

    Example:
        >>> text = transcribe_audio("voice_message.ogg")
        >>> print(text)
        "Finish operating systems assignment tomorrow"
    """
    try:
        model = _get_model()

        logger.info(f"Transcribing audio: {audio_path}")

        # Whisper handles format conversion internally
        # fp16=False is needed for CPU-only machines (most laptops)
        result = model.transcribe(
            audio_path,
            fp16=False,  # Use FP32 for CPU compatibility
            language="en",  # Set to None for auto-detection
        )

        transcribed_text = result["text"].strip()
        logger.info(f"Transcription result: '{transcribed_text}'")

        return transcribed_text

    except FileNotFoundError:
        logger.error(f"Audio file not found: {audio_path}")
        return ""

    except Exception as e:
        logger.error(f"Transcription failed: {e}", exc_info=True)
        return ""


def transcribe_with_details(audio_path: str) -> dict:
    """
    Transcribe audio and return detailed results including segments.

    Useful for debugging or showing timestamps.

    Args:
        audio_path: Path to the audio file.

    Returns:
        dict: Contains 'text', 'segments', and 'language' keys.
    """
    try:
        model = _get_model()
        result = model.transcribe(audio_path, fp16=False, language="en")
        return {
            "text": result["text"].strip(),
            "segments": result.get("segments", []),
            "language": result.get("language", "unknown"),
        }
    except Exception as e:
        logger.error(f"Detailed transcription failed: {e}", exc_info=True)
        return {"text": "", "segments": [], "language": "unknown"}