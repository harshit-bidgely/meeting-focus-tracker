"""Google Chat integration.

Posts meeting summaries to Google Chat spaces based on meeting participants.
Uses service account authentication and discovers spaces where participants are members.
"""

from __future__ import annotations

import logging
from typing import Any

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials

logger = logging.getLogger(__name__)


class GoogleChatService:
    """Posts meeting summaries to Google Chat spaces."""

    SCOPES = [
        "https://www.googleapis.com/auth/chat.bot",
        "https://www.googleapis.com/auth/chat.spaces",
    ]

    def __init__(self, credentials: Credentials | ServiceAccountCredentials) -> None:
        """Initialize with Google service account credentials.

        Args:
            credentials: Google OAuth2 or Service Account credentials
        """
        self.credentials = credentials
        self.chat_api = build("chat", "v1", credentials=credentials)
        self._space_members: dict[str, list[str]] = {}

    @classmethod
    def from_credentials_file(cls, credentials_file: str) -> GoogleChatService:
        """Create service from service account credentials file.

        Args:
            credentials_file: Path to Google service account JSON file

        Returns:
            Initialized GoogleChatService instance

        Raises:
            FileNotFoundError: If credentials file not found
            ValueError: If credentials file is invalid
        """
        try:
            credentials = ServiceAccountCredentials.from_service_account_file(
                credentials_file, scopes=cls.SCOPES
            )
            return cls(credentials)
        except FileNotFoundError as e:
            logger.error("Credentials file not found: %s", credentials_file)
            raise
        except ValueError as e:
            logger.error("Invalid credentials file format: %s", credentials_file)
            raise

    def discover_and_cache_spaces(self) -> None:
        """Query Chat API for all accessible spaces and cache members.

        Calls spaces.list() and for each space, fetches the member list.
        Caches results in self._space_members:
        {
            "spaces/ABC123": ["user1@org.com", "user2@org.com", ...],
            "spaces/DEF456": ["user3@org.com", ...],
        }

        Handles errors gracefully - logs and continues on failures.
        """
        try:
            # Get all accessible spaces
            spaces_response = (
                self.chat_api.spaces().list().execute()
            )

            spaces = spaces_response.get("spaces", [])
            logger.info("Discovered %d accessible Chat spaces", len(spaces))

            # For each space, fetch and cache members
            for space in spaces:
                space_id = space.get("name")
                if not space_id:
                    logger.warning("Space missing 'name' field, skipping")
                    continue

                try:
                    members_response = (
                        self.chat_api.spaces()
                        .members()
                        .list(parent=space_id)
                        .execute()
                    )

                    members = members_response.get("members", [])
                    member_emails = []

                    for member in members:
                        try:
                            member_obj = member.get("member")
                            if member_obj and isinstance(member_obj, dict):
                                email = member_obj.get("email")
                                if email:
                                    member_emails.append(email.lower())
                        except (AttributeError, TypeError):
                            logger.debug("Skipping malformed member object")
                            continue

                    if member_emails:
                        self._space_members[space_id] = member_emails
                        logger.debug(
                            "Cached %d members for space %s",
                            len(member_emails),
                            space_id,
                        )

                except Exception as e:
                    logger.warning("Failed to fetch members for space %s: %s", space_id, e)
                    continue

        except Exception as e:
            logger.error("Failed to discover Chat spaces: %s", e)

    def post_meeting_summary(
        self,
        meeting_title: str,
        participants: list[str],
        decisions: list[str],
        open_items: list[str],
        drive_url: str | None = None,
    ) -> dict[str, Any]:
        """Post meeting summary to spaces where participants are members.

        Args:
            meeting_title: Title of the meeting
            participants: List of attendee email addresses
            decisions: List of key decisions made
            open_items: List of action items/open items
            drive_url: URL to full meeting notes in Google Drive (optional)

        Returns:
            {
                "success": bool,
                "spaces_posted": list[str],  # Space IDs where posted
                "spaces_found": int,         # Total matching spaces
                "error": str | None          # Error message if occurred
            }
        """
        matching_spaces = self._find_matching_spaces(participants)

        result = {
            "success": True,
            "spaces_posted": [],
            "spaces_found": len(matching_spaces),
            "error": None,
        }

        if not matching_spaces:
            logger.info(
                "No Chat spaces found matching %d participants", len(participants)
            )
            return result

        logger.info("Found %d spaces for %d participants", len(matching_spaces), len(participants))

        # Build message once
        message = self._build_smart_card(
            meeting_title=meeting_title,
            decisions=decisions,
            open_items=open_items,
            drive_url=drive_url,
        )

        # Post to each matching space
        for space_id in matching_spaces:
            try:
                response = (
                    self.chat_api.spaces()
                    .messages()
                    .create(
                        parent=space_id,
                        body={"cardsV2": [{"cardId": "meeting-summary", "card": message}]},
                    )
                    .execute()
                )

                result["spaces_posted"].append(space_id)
                logger.info("Posted meeting summary to space: %s", space_id)

            except Exception as e:
                logger.warning("Failed to post to space %s: %s", space_id, e)
                result["success"] = False
                if not result["error"]:
                    result["error"] = f"Failed to post to space {space_id}: {str(e)}"
                continue

        if result["spaces_posted"]:
            logger.info(
                "Successfully posted to %d/%d spaces",
                len(result["spaces_posted"]),
                len(matching_spaces),
            )

        return result

    def _find_matching_spaces(self, participants: list[str]) -> list[str]:
        """Find spaces where meeting participants are members.

        A space matches if at least one participant is a member.

        Args:
            participants: List of attendee email addresses

        Returns:
            List of space IDs where at least one participant is a member
        """
        if not participants or not self._space_members:
            return []

        # Normalize participant emails to lowercase
        participant_emails = set(email.lower() for email in participants if email)

        matching = []
        for space_id, space_members in self._space_members.items():
            # Check if any participant is in this space
            space_member_set = set(m.lower() for m in space_members if m)
            if participant_emails & space_member_set:  # intersection
                matching.append(space_id)

        return matching

    def _build_smart_card(
        self,
        meeting_title: str,
        decisions: list[str],
        open_items: list[str],
        drive_url: str | None = None,
    ) -> dict[str, Any]:
        """Build a Google Chat smart card message.

        Args:
            meeting_title: Title of the meeting
            decisions: List of key decisions
            open_items: List of action items
            drive_url: Link to full meeting notes (optional)

        Returns:
            Google Chat smart card dictionary
        """
        sections = []

        # Title section
        title_section = {
            "header": f"📋 {meeting_title}",
            "widgets": [],
        }

        # Decisions section
        if decisions:
            decisions_text = "\n".join(f"• {d}" for d in decisions if d)
            title_section["widgets"].append(
                {
                    "textParagraph": {
                        "text": f"<b>Key Decisions:</b>\n{decisions_text}"
                    }
                }
            )

        sections.append(title_section)

        # Action items section
        if open_items:
            actions_text = "\n".join(f"• {item}" for item in open_items if item)
            sections.append(
                {
                    "header": "Action Items",
                    "widgets": [
                        {
                            "textParagraph": {
                                "text": actions_text
                            }
                        }
                    ],
                }
            )

        # Footer with link to full summary
        footer_widgets = []
        if drive_url:
            footer_widgets.append(
                {
                    "buttonList": {
                        "buttons": [
                            {
                                "text": "View Full Summary",
                                "onClick": {
                                    "openLink": {
                                        "url": drive_url
                                    }
                                },
                            }
                        ]
                    }
                }
            )

        if footer_widgets:
            sections.append(
                {
                    "widgets": footer_widgets
                }
            )

        # Build the complete smart card
        card = {
            "sections": sections
        }

        return card
