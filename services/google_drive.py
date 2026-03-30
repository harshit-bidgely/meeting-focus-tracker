"""Google Drive integration.

Saves meeting notes as Google Docs in the user's Drive,
organized in a dedicated folder.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)

FOLDER_NAME = "Meeting Focus Tracker Notes"


class GoogleDriveService:
    """Creates and manages meeting note documents in Google Drive."""

    def __init__(self, credentials: Credentials) -> None:
        self.drive_service = build("drive", "v3", credentials=credentials)
        self.docs_service = build("docs", "v1", credentials=credentials)
        self._folder_id: str | None = None

    def save_meeting_notes(
        self,
        meeting_title: str,
        agenda: str,
        summary: str,
        decisions: list[str],
        open_items: list[str],
        deviation_count: int,
    ) -> str | None:
        """Create a Google Doc with meeting notes and return its URL.

        Returns the document URL, or None on failure.
        """
        try:
            folder_id = self._get_or_create_folder()
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            doc_title = f"{meeting_title} - {date_str}"

            # Create blank doc in the folder
            file_metadata = {
                "name": doc_title,
                "mimeType": "application/vnd.google-apps.document",
                "parents": [folder_id],
            }
            doc_file = self.drive_service.files().create(
                body=file_metadata,
                fields="id, webViewLink",
            ).execute()

            doc_id = doc_file["id"]
            doc_url = doc_file["webViewLink"]

            # Build document content
            requests = self._build_doc_content(
                meeting_title, date_str, agenda, summary, decisions, open_items, deviation_count
            )

            self.docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={"requests": requests},
            ).execute()

            logger.info("Meeting notes saved to Google Drive: %s", doc_url)
            return doc_url

        except Exception:
            logger.exception("Failed to save meeting notes to Google Drive")
            return None

    def _get_or_create_folder(self) -> str:
        """Get or create the 'Meeting Focus Tracker Notes' folder in Drive."""
        if self._folder_id:
            return self._folder_id

        # Search for existing folder
        query = (
            f"name = '{FOLDER_NAME}' and "
            "mimeType = 'application/vnd.google-apps.folder' and "
            "trashed = false"
        )
        result = self.drive_service.files().list(
            q=query, spaces="drive", fields="files(id)"
        ).execute()

        files = result.get("files", [])
        if files:
            self._folder_id = files[0]["id"]
            logger.debug("Found existing folder: %s", self._folder_id)
            return self._folder_id

        # Create folder
        metadata = {
            "name": FOLDER_NAME,
            "mimeType": "application/vnd.google-apps.folder",
        }
        folder = self.drive_service.files().create(
            body=metadata, fields="id"
        ).execute()

        self._folder_id = folder["id"]
        logger.info("Created Drive folder '%s': %s", FOLDER_NAME, self._folder_id)
        return self._folder_id

    @staticmethod
    def _build_doc_content(
        meeting_title: str,
        date_str: str,
        agenda: str,
        summary: str,
        decisions: list[str],
        open_items: list[str],
        deviation_count: int,
    ) -> list[dict]:
        """Build a list of Google Docs API requests to populate the document."""
        # Google Docs API inserts text at an index. We build content bottom-up
        # and insert at index 1 (after the implicit newline).
        sections = []

        # Title
        sections.append(f"{meeting_title}\n")
        sections.append(f"Date: {date_str}\n\n")

        # Agenda
        sections.append("Agenda\n")
        sections.append(f"{agenda}\n\n")

        # Summary
        sections.append("Summary\n")
        sections.append(f"{summary}\n\n")

        # Decisions
        if decisions:
            sections.append("Decisions Made\n")
            for d in decisions:
                sections.append(f"  - {d}\n")
            sections.append("\n")

        # Open Items
        if open_items:
            sections.append("Open Items\n")
            for item in open_items:
                sections.append(f"  - {item}\n")
            sections.append("\n")

        # Focus Score
        sections.append(f"Focus Score: {deviation_count} off-topic deviations detected\n")

        # Build insert requests
        full_text = "".join(sections)
        requests = [
            {
                "insertText": {
                    "location": {"index": 1},
                    "text": full_text,
                }
            }
        ]

        # Style the title as HEADING_1
        title_len = len(sections[0])
        requests.append({
            "updateParagraphStyle": {
                "range": {"startIndex": 1, "endIndex": 1 + title_len},
                "paragraphStyle": {"namedStyleType": "HEADING_1"},
                "fields": "namedStyleType",
            }
        })

        # Style section headers as HEADING_2
        idx = 1
        for section in sections:
            if section in ("Agenda\n", "Summary\n", "Decisions Made\n", "Open Items\n"):
                requests.append({
                    "updateParagraphStyle": {
                        "range": {"startIndex": idx, "endIndex": idx + len(section)},
                        "paragraphStyle": {"namedStyleType": "HEADING_2"},
                        "fields": "namedStyleType",
                    }
                })
            idx += len(section)

        return requests
