"""
AI Task Parser using Ollama (local LLM).

This module sends transcribed text to a locally running LLM
(via Ollama) to extract structured task information.

The LLM identifies:
    - Task name: What needs to be done
    - Priority: How urgent it is (1=highest, 4=lowest)
    - Deadline: When it's due
    - Category: What type of task it is

Priority Rules:
    1 (HIGH)   : Assignments with close deadlines, exams tomorrow
    2 (MEDIUM) : Exams, quizzes, presentations coming up
    3 (LOW)    : Personal projects, reading, general study
    4 (MINIMAL): Optional tasks, nice-to-haves

No paid APIs are used. Everything runs locally on your machine.
"""

import json
import logging
import re
from datetime import datetime

import requests

from config.settings import OLLAMA_BASE_URL, OLLAMA_MODEL

logger = logging.getLogger(__name__)

# The prompt template tells the LLM exactly what we want
TASK_EXTRACTION_PROMPT = """You are a task extraction assistant for a student study planner.
Given a student's spoken task description, extract structured information.

Today's date is: {today}

RULES:
- Extract the task name (short, clear description)
- Determine priority (1=highest, 4=lowest):
  * Priority 1: Assignment submissions, urgent deadlines (today/tomorrow)
  * Priority 2: Exams, quizzes, presentations (within the week)
  * Priority 3: Personal projects, regular study sessions
  * Priority 4: Optional reading, exploration, nice-to-haves
- Parse the deadline into YYYY-MM-DD format when possible
  * "today" → {today}
  * "tomorrow" → the next day
  * "tonight" → {today}
  * "next Monday" → calculate the actual date
  * If unclear, use "unspecified"
- Determine category: one of [assignment, exam, project, study, reading, personal, other]

INPUT: "{user_input}"

Respond ONLY with valid JSON in this exact format, nothing else:
{{"task": "short task description", "priority": 1, "deadline": "YYYY-MM-DD", "category": "assignment"}}
"""


def parse_task(text: str) -> dict:
    """
    Parse a natural language task description into structured data.

    Sends the text to a local Ollama LLM and extracts task fields.

    Args:
        text: The transcribed voice message or typed text.
              Example: "Finish operating systems assignment tomorrow"

    Returns:
        dict: Structured task data with keys:
            - task (str): Short task description
            - priority (int): 1-4 priority level
            - deadline (str): Date in YYYY-MM-DD or "unspecified"
            - category (str): Task category

    Example:
        >>> parse_task("Finish OS assignment tomorrow")
        {
            "task": "Finish OS assignment",
            "priority": 1,
            "deadline": "2026-03-10",
            "category": "assignment"
        }
    """
    today = datetime.now().strftime("%Y-%m-%d")
    prompt = TASK_EXTRACTION_PROMPT.format(today=today, user_input=text)

    try:
        # Call local Ollama API
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Low temperature for consistent output
                    "num_predict": 200,  # Limit response length
                },
            },
            timeout=60,  # LLM can take a moment
        )
        response.raise_for_status()

        result = response.json()
        raw_response = result.get("response", "").strip()
        logger.info(f"LLM raw response: {raw_response}")

        # Extract JSON from the response
        parsed = _extract_json(raw_response)

        # Validate and sanitize the parsed data
        validated = _validate_task(parsed, text)
        logger.info(f"Validated task: {validated}")

        return validated

    except requests.ConnectionError:
        logger.error(
            "Cannot connect to Ollama! "
            "Make sure Ollama is running: 'ollama serve'"
        )
        # Fallback: return a basic task without AI parsing
        return _fallback_parse(text)

    except requests.Timeout:
        logger.error("Ollama request timed out. The model may be loading.")
        return _fallback_parse(text)

    except Exception as e:
        logger.error(f"Task parsing failed: {e}", exc_info=True)
        return _fallback_parse(text)


def _extract_json(text: str) -> dict:
    """
    Extract a JSON object from LLM response text.

    LLMs sometimes add extra text around the JSON.
    This function finds and parses the JSON portion.

    Args:
        text: Raw LLM response string.

    Returns:
        dict: Parsed JSON data.

    Raises:
        ValueError: If no valid JSON found in the text.
    """
    # Try direct JSON parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON within the text using regex
    json_pattern = r'\{[^{}]*\}'
    matches = re.findall(json_pattern, text)

    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue

    raise ValueError(f"No valid JSON found in LLM response: {text}")


def _validate_task(parsed: dict, original_text: str) -> dict:
    """
    Validate and sanitize parsed task data.

    Ensures all required fields exist and have valid values.

    Args:
        parsed: Raw parsed dict from LLM.
        original_text: Original user input for fallback.

    Returns:
        dict: Validated task data.
    """
    # Ensure task name exists
    task_name = parsed.get("task", original_text)
    if not task_name or len(task_name.strip()) == 0:
        task_name = original_text

    # Validate priority (must be 1-4)
    priority = parsed.get("priority", 3)
    try:
        priority = int(priority)
        priority = max(1, min(4, priority))  # Clamp to 1-4
    except (ValueError, TypeError):
        priority = 3

    # Validate deadline
    deadline = parsed.get("deadline", "unspecified")
    if deadline and deadline != "unspecified":
        # Try to validate the date format
        try:
            datetime.strptime(deadline, "%Y-%m-%d")
        except ValueError:
            deadline = "unspecified"

    # Validate category
    valid_categories = [
        "assignment", "exam", "project",
        "study", "reading", "personal", "other",
    ]
    category = parsed.get("category", "other").lower()
    if category not in valid_categories:
        category = "other"

    return {
        "task": task_name.strip(),
        "priority": priority,
        "deadline": deadline,
        "category": category,
    }


def _fallback_parse(text: str) -> dict:
    """
    Simple rule-based fallback when the LLM is unavailable.

    Uses keyword matching to guess priority and category.

    Args:
        text: Original user input text.

    Returns:
        dict: Best-effort parsed task data.
    """
    logger.warning("Using fallback parser (LLM unavailable)")

    text_lower = text.lower()
    today = datetime.now().strftime("%Y-%m-%d")

    # Determine priority from keywords
    priority = 3  # Default
    if any(kw in text_lower for kw in ["assignment", "submit", "due", "deadline"]):
        priority = 1
    elif any(kw in text_lower for kw in ["exam", "quiz", "test", "presentation"]):
        priority = 2
    elif any(kw in text_lower for kw in ["project", "build", "create"]):
        priority = 3

    # Determine category from keywords
    category = "other"
    if any(kw in text_lower for kw in ["assignment", "homework", "submit"]):
        category = "assignment"
    elif any(kw in text_lower for kw in ["exam", "quiz", "test"]):
        category = "exam"
    elif any(kw in text_lower for kw in ["project", "build"]):
        category = "project"
    elif any(kw in text_lower for kw in ["study", "review", "revise"]):
        category = "study"
    elif any(kw in text_lower for kw in ["read", "chapter", "book"]):
        category = "reading"

    # Determine deadline from keywords
    deadline = "unspecified"
    if any(kw in text_lower for kw in ["today", "tonight"]):
        deadline = today
    elif "tomorrow" in text_lower:
        from datetime import timedelta
        deadline = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    return {
        "task": text.strip(),
        "priority": priority,
        "deadline": deadline,
        "category": category,
    }