"""Gmail API client for sending meeting reports via Google Gmail."""

from __future__ import annotations

import base64
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials as OAuth2Credentials
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class GmailClient:
    """Send emails using Google Gmail API."""

    def __init__(self, credentials):
        """Initialize Gmail client with OAuth credentials.

        Args:
            credentials: Google OAuth2 credentials object
        """
        self.credentials = credentials
        self.service = None
        self._init_service()

    def _init_service(self) -> None:
        """Initialize Gmail API service."""
        try:
            # Ensure credentials are fresh
            if self.credentials.expired and self.credentials.refresh_token:
                self.credentials.refresh(Request())

            self.service = build("gmail", "v1", credentials=self.credentials)
            logger.info("Gmail API service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Gmail API: {e}")
            raise

    def send_email(
        self,
        to_addresses: list[str],
        subject: str,
        html_content: str,
        text_content: str,
        sender: str | None = None,
    ) -> bool:
        """Send email via Gmail API.

        Args:
            to_addresses: List of recipient email addresses
            subject: Email subject
            html_content: HTML email body
            text_content: Plain text email body (fallback)
            sender: Sender email address (uses authenticated user's email if None)

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Create MIME message with both plain text and HTML parts
            message = MIMEMultipart("alternative")
            message["To"] = ", ".join(to_addresses)
            message["Subject"] = subject

            # Add plain text part (fallback)
            message.attach(MIMEText(text_content, "plain"))

            # Add HTML part (preferred)
            message.attach(MIMEText(html_content, "html"))

            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

            # Send via Gmail API
            send_message = {"raw": raw_message}
            result = self.service.users().messages().send(
                userId="me", body=send_message
            ).execute()

            logger.info(f"Email sent successfully. Message ID: {result.get('id')}")
            return True

        except HttpError as error:
            logger.error(f"Gmail API error: {error}")
            return False
        except RefreshError as error:
            logger.error(f"Failed to refresh credentials: {error}")
            return False
        except Exception as error:
            logger.error(f"Error sending email: {error}")
            return False

    def send_batch(
        self,
        recipients: dict[str, tuple[str, str, str]],
        subject: str,
        sender: str | None = None,
    ) -> dict[str, bool]:
        """Send emails to multiple recipients.

        Args:
            recipients: Dict mapping email -> (html_content, text_content, extra_subject)
            subject: Base subject line
            sender: Sender email

        Returns:
            Dict mapping email -> success boolean
        """
        results = {}
        for email, (html, text, extra_subject) in recipients.items():
            full_subject = f"{subject} {extra_subject}".strip()
            success = self.send_email([email], full_subject, html, text, sender)
            results[email] = success
        return results
