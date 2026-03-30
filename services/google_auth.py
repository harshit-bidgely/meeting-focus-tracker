"""Google OAuth2 authentication helper.

Handles the OAuth2 flow for Google Workspace APIs (Calendar, Gmail, Drive).
Stores tokens locally so users only need to authenticate once.
"""

from __future__ import annotations

import logging
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

logger = logging.getLogger(__name__)

# Scopes required for Calendar (read), Gmail (send), and Drive (file create)
SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/drive.file",
]

DEFAULT_CREDENTIALS_FILE = "credentials.json"
DEFAULT_TOKEN_FILE = "token.json"


def get_google_credentials(
    credentials_file: str = DEFAULT_CREDENTIALS_FILE,
    token_file: str = DEFAULT_TOKEN_FILE,
) -> Credentials:
    """Load or create Google OAuth2 credentials.

    On first run, opens a browser for the user to authorize.
    Subsequent runs reuse the saved token.

    Args:
        credentials_file: Path to the OAuth2 client secrets JSON downloaded
                          from Google Cloud Console.
        token_file: Path where the refresh/access token is cached.

    Returns:
        Valid Google OAuth2 Credentials object.

    Raises:
        FileNotFoundError: If credentials_file does not exist.
    """
    if not os.path.exists(credentials_file):
        raise FileNotFoundError(
            f"Google OAuth credentials file not found: {credentials_file}\n"
            "Download it from Google Cloud Console > APIs & Services > Credentials.\n"
            "See README for setup instructions."
        )

    creds: Credentials | None = None

    # Try to load existing token
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        logger.debug("Loaded cached Google token from %s", token_file)

    # Refresh or re-authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired Google token")
            creds.refresh(Request())
        else:
            logger.info("Starting Google OAuth2 authorization flow")
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save token for next run
        with open(token_file, "w") as f:
            f.write(creds.to_json())
        logger.info("Google token saved to %s", token_file)

    return creds
