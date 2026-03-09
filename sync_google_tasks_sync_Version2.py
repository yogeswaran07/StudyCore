"""
Optional Google Tasks Sync module.

This module provides one-way sync from the local database to Google Tasks.
It uses the Google Tasks API with OAuth2 authentication.

⚠️ THIS IS ENTIRELY OPTIONAL. The system works fully without it.

To use this module:
1. Go to https://console.cloud.google.com/
2. Create a new project
3. Enable the "Google Tasks API"
4. Create OAuth 2.0 credentials (Desktop application)
5. Download the credentials JSON file
6. Save it as config/google_credentials.json

First run will open a browser for authentication.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Path to Google OAuth credentials
CREDENTIALS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "google_credentials.json"
)
TOKEN_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "google_token.json"
)

# Google API scopes needed
SCOPES = ["https://www.googleapis.com/auth/tasks"]


def is_google_sync_available() -> bool:
    """
    Check if Google Tasks sync is configured.

    Returns:
        bool: True if credentials file exists.
    """
    available = os.path.exists(CREDENTIALS_PATH)
    if not available:
        logger.info(
            "Google Tasks sync not configured. "
            "Place google_credentials.json in config/ to enable."
        )
    return available


def sync_task_to_google(task_name: str, deadline: str = "", notes: str = "") -> Optional[str]:
    """
    Sync a single task to Google Tasks.

    Args:
        task_name: The task title.
        deadline: Due date in YYYY-MM-DD format.
        notes: Optional notes for the task.

    Returns:
        str or None: Google Task ID if successful, None otherwise.
    """
    if not is_google_sync_available():
        return None

    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        # Authenticate
        creds = None
        if os.path.exists(TOKEN_PATH):
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_PATH, SCOPES
                )
                creds = flow.run_local_server(port=0)
            # Save token for next time
            with open(TOKEN_PATH, "w") as token:
                token.write(creds.to_json())

        # Build the service
        service = build("tasks", "v1", credentials=creds)

        # Create the task
        task_body = {"title": task_name}
        if notes:
            task_body["notes"] = notes
        if deadline and deadline != "unspecified":
            task_body["due"] = f"{deadline}T00:00:00.000Z"

        result = service.tasks().insert(
            tasklist="@default", body=task_body
        ).execute()

        logger.info(f"Synced to Google Tasks: {result.get('id')}")
        return result.get("id")

    except ImportError:
        logger.warning(
            "Google API libraries not installed. "
            "Run: pip install google-api-python-client "
            "google-auth-httplib2 google-auth-oauthlib"
        )
        return None
    except Exception as e:
        logger.error(f"Google Tasks sync failed: {e}")
        return None