"""Tests for the Google Drive service."""

from __future__ import annotations

from unittest.mock import MagicMock, patch, call

import pytest

from services.google_drive import GoogleDriveService, FOLDER_NAME


# ---------------------------------------------------------------------------
# Helper to create a GoogleDriveService with mocked APIs
# ---------------------------------------------------------------------------

def _make_drive_service(
    existing_folder_id: str | None = None,
    doc_id: str = "doc-123",
    doc_url: str = "https://docs.google.com/document/d/doc-123/edit",
) -> tuple[GoogleDriveService, MagicMock, MagicMock]:
    """Create a GoogleDriveService with mocked Drive and Docs APIs."""
    mock_creds = MagicMock()

    mock_drive_api = MagicMock()
    mock_docs_api = MagicMock()

    with patch("services.google_drive.build") as mock_build:
        def build_side_effect(api, version, credentials):
            if api == "drive":
                return mock_drive_api
            elif api == "docs":
                return mock_docs_api
            return MagicMock()

        mock_build.side_effect = build_side_effect
        service = GoogleDriveService(mock_creds)

    # Mock folder search
    if existing_folder_id:
        mock_drive_api.files.return_value.list.return_value.execute.return_value = {
            "files": [{"id": existing_folder_id}]
        }
    else:
        mock_drive_api.files.return_value.list.return_value.execute.return_value = {
            "files": []
        }
        mock_drive_api.files.return_value.create.return_value.execute.return_value = {
            "id": "new-folder-id",
        }

    # Mock doc creation (override for file create with fields containing webViewLink)
    def create_side_effect(body, fields="id"):
        if "webViewLink" in fields:
            return MagicMock(execute=MagicMock(return_value={
                "id": doc_id,
                "webViewLink": doc_url,
            }))
        return MagicMock(execute=MagicMock(return_value={"id": "new-folder-id"}))

    mock_drive_api.files.return_value.create.side_effect = create_side_effect

    # Mock docs batchUpdate
    mock_docs_api.documents.return_value.batchUpdate.return_value.execute.return_value = {}

    return service, mock_drive_api, mock_docs_api


# ---------------------------------------------------------------------------
# Tests: _get_or_create_folder
# ---------------------------------------------------------------------------

class TestGetOrCreateFolder:
    """Test Drive folder creation and reuse."""

    def test_creates_new_folder_when_not_exists(self):
        service, mock_drive, _ = _make_drive_service(existing_folder_id=None)
        folder_id = service._get_or_create_folder()
        assert folder_id == "new-folder-id"

    def test_reuses_existing_folder(self):
        service, mock_drive, _ = _make_drive_service(existing_folder_id="existing-folder-42")
        folder_id = service._get_or_create_folder()
        assert folder_id == "existing-folder-42"

    def test_caches_folder_id(self):
        service, mock_drive, _ = _make_drive_service(existing_folder_id="cached-id")
        # First call
        service._get_or_create_folder()
        # Second call should use cached value, not call API again
        service._get_or_create_folder()

        # list should only be called once (on first lookup)
        assert mock_drive.files.return_value.list.return_value.execute.call_count == 1


# ---------------------------------------------------------------------------
# Tests: _build_doc_content
# ---------------------------------------------------------------------------

class TestBuildDocContent:
    """Test Google Docs API request generation."""

    def test_returns_insert_text_request(self):
        requests = GoogleDriveService._build_doc_content(
            "Sprint Sync", "2026-03-30", "1. Progress", "Good meeting", [], [], 0
        )
        # First request should be insertText
        assert requests[0]["insertText"]["location"]["index"] == 1
        text = requests[0]["insertText"]["text"]
        assert "Sprint Sync" in text
        assert "2026-03-30" in text
        assert "1. Progress" in text
        assert "Good meeting" in text

    def test_includes_heading_styles(self):
        requests = GoogleDriveService._build_doc_content(
            "Meeting", "2026-03-30", "Agenda", "Summary", [], [], 0
        )
        # Should have HEADING_1 for title and HEADING_2 for sections
        heading_types = [
            r.get("updateParagraphStyle", {}).get("paragraphStyle", {}).get("namedStyleType")
            for r in requests
            if "updateParagraphStyle" in r
        ]
        assert "HEADING_1" in heading_types
        assert "HEADING_2" in heading_types

    def test_includes_decisions_when_present(self):
        requests = GoogleDriveService._build_doc_content(
            "Meeting", "2026-03-30", "Agenda", "Summary",
            ["Hire engineers", "Cut budget"], [], 0
        )
        text = requests[0]["insertText"]["text"]
        assert "Decisions Made" in text
        assert "Hire engineers" in text
        assert "Cut budget" in text

    def test_includes_open_items_when_present(self):
        requests = GoogleDriveService._build_doc_content(
            "Meeting", "2026-03-30", "Agenda", "Summary",
            [], ["Review proposal", "Send report"], 0
        )
        text = requests[0]["insertText"]["text"]
        assert "Open Items" in text
        assert "Review proposal" in text

    def test_no_decisions_section_when_empty(self):
        requests = GoogleDriveService._build_doc_content(
            "Meeting", "2026-03-30", "Agenda", "Summary", [], [], 0
        )
        text = requests[0]["insertText"]["text"]
        assert "Decisions Made" not in text

    def test_no_open_items_section_when_empty(self):
        requests = GoogleDriveService._build_doc_content(
            "Meeting", "2026-03-30", "Agenda", "Summary", [], [], 0
        )
        text = requests[0]["insertText"]["text"]
        assert "Open Items" not in text

    def test_includes_focus_score(self):
        requests = GoogleDriveService._build_doc_content(
            "Meeting", "2026-03-30", "Agenda", "Summary", [], [], 7
        )
        text = requests[0]["insertText"]["text"]
        assert "7 off-topic deviations" in text

    def test_heading2_for_agenda_and_summary(self):
        """Agenda and Summary should be styled as HEADING_2."""
        requests = GoogleDriveService._build_doc_content(
            "Meeting", "2026-03-30", "Agenda text", "Summary text", [], [], 0
        )
        heading2_sections = []
        for r in requests:
            style = r.get("updateParagraphStyle", {})
            if style.get("paragraphStyle", {}).get("namedStyleType") == "HEADING_2":
                heading2_sections.append(r)
        # At least Agenda and Summary headers
        assert len(heading2_sections) >= 2


# ---------------------------------------------------------------------------
# Tests: save_meeting_notes
# ---------------------------------------------------------------------------

class TestSaveMeetingNotes:
    """Test end-to-end meeting note creation."""

    def test_returns_doc_url_on_success(self):
        service, _, _ = _make_drive_service(
            existing_folder_id="folder-1",
            doc_url="https://docs.google.com/document/d/abc/edit",
        )
        url = service.save_meeting_notes(
            meeting_title="Sprint Sync",
            agenda="1. Progress\n2. Blockers",
            summary="Good discussion",
            decisions=["Ship feature X"],
            open_items=["Review Y"],
            deviation_count=1,
        )
        assert url == "https://docs.google.com/document/d/abc/edit"

    def test_returns_none_on_api_error(self):
        service, mock_drive, _ = _make_drive_service(existing_folder_id="folder-1")
        # Make the list call (for folder lookup) raise
        mock_drive.files.return_value.list.return_value.execute.side_effect = Exception("API down")
        # Reset the cached folder_id to force a lookup
        service._folder_id = None

        url = service.save_meeting_notes(
            meeting_title="Sprint",
            agenda="Agenda",
            summary="Summary",
            decisions=[],
            open_items=[],
            deviation_count=0,
        )
        assert url is None

    def test_calls_docs_batch_update(self):
        service, _, mock_docs = _make_drive_service(existing_folder_id="folder-1")
        service.save_meeting_notes(
            meeting_title="Sprint",
            agenda="Agenda",
            summary="Summary",
            decisions=[],
            open_items=[],
            deviation_count=0,
        )
        mock_docs.documents.return_value.batchUpdate.assert_called_once()


class TestFolderName:
    def test_folder_name_constant(self):
        assert FOLDER_NAME == "Meeting Focus Tracker Notes"
