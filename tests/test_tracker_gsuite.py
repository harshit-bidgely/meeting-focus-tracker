"""Tests for tracker G Suite export integration (_save_to_memory, _export_to_gmail, _export_to_google_drive)."""

from __future__ import annotations

from contextlib import ExitStack
from unittest.mock import MagicMock, patch, call

import pytest

from config import Config
from tracker import MeetingFocusTracker, MeetingState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tracker(
    meeting_id: str = "test-meet",
    google_creds=None,
    meeting_title: str = "Sprint Sync",
    attendees: list[str] | None = None,
) -> MeetingFocusTracker:
    """Create a tracker with mocked dependencies."""
    with patch.object(Config, "LLM_API_KEY", "test-key"), \
         patch.object(Config, "LLM_API_BASE", "https://api.groq.com/openai/v1"), \
         patch.object(Config, "VEXA_API_KEY", "test-key"), \
         patch.object(Config, "MEETING_ID", meeting_id), \
         patch.object(Config, "MEETING_PLATFORM", "google_meet"), \
         patch.object(Config, "DEVIATION_THRESHOLD", 2), \
         patch.object(Config, "ALERT_COOLDOWN", 180), \
         patch.object(Config, "POLL_INTERVAL", 1):
        tracker = MeetingFocusTracker(
            google_creds=google_creds,
            attendees=attendees,
            meeting_title=meeting_title,
        )
    tracker.vexa = MagicMock()
    tracker.llm = MagicMock()
    tracker.memory = MagicMock()
    return tracker


def _save_patches():
    """Create fresh patches for the _save_to_memory flow each time."""
    return [
        patch("tracker.save_meeting_to_thread", return_value="/tmp/test-thread/2026-03-30"),
        patch("tracker.find_matching_thread", return_value=None),
        patch("tracker.time.sleep"),
    ]

# Fake LLM summary response for _save_to_memory
FAKE_SUMMARY_DATA = {
    "title": "Sprint Sync — 2026-03-30",
    "summary": "Good meeting",
    "agenda_items": [
        {"number": 1, "topic": "Progress", "status": "completed",
         "key_points": ["On track"], "decisions": ["Ship feature X"],
         "action_items": ["Review PR"]}
    ],
    "overall_action_items": [
        {"owner": "Alice", "action": "Send report", "deadline": None}
    ],
    "focus_score": "on_track",
}


# ---------------------------------------------------------------------------
# Tests: constructor with G Suite params
# ---------------------------------------------------------------------------

class TestTrackerGSuiteInit:
    """Test that the tracker accepts and stores G Suite parameters."""

    def test_stores_google_creds(self):
        creds = MagicMock()
        tracker = _make_tracker(google_creds=creds)
        assert tracker.google_creds is creds

    def test_stores_meeting_title(self):
        tracker = _make_tracker(meeting_title="Important Meeting")
        assert tracker.meeting_title == "Important Meeting"

    def test_stores_attendees(self):
        tracker = _make_tracker(attendees=["alice@example.com", "bob@example.com"])
        assert tracker.attendees == ["alice@example.com", "bob@example.com"]

    def test_default_no_creds(self):
        tracker = _make_tracker()
        assert tracker.google_creds is None

    def test_default_empty_title(self):
        tracker = _make_tracker(meeting_title="")
        assert tracker.meeting_title == ""

    def test_default_no_attendees(self):
        tracker = _make_tracker(attendees=None)
        assert tracker.attendees == []


# ---------------------------------------------------------------------------
# Tests: _export_to_google_drive
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="Google Drive export not yet implemented on tracker")
class TestExportToGoogleDrive:
    """Test Google Drive export logic in the tracker."""

    @patch("services.google_drive.GoogleDriveService")
    def test_exports_when_enabled_with_creds(self, mock_drive_cls):
        mock_drive = MagicMock()
        mock_drive.save_meeting_notes.return_value = "https://docs.google.com/doc/123"
        mock_drive_cls.return_value = mock_drive

        tracker = _make_tracker(google_creds=MagicMock())
        tracker.agenda_formatted = "1. Progress"

        with patch.object(Config, "ENABLE_GOOGLE_DRIVE", True):
            tracker._export_to_google_drive(
                "Sprint", "Summary", ["Decision 1"], ["Open 1"], 2
            )

        mock_drive.save_meeting_notes.assert_called_once_with(
            meeting_title="Sprint",
            agenda="1. Progress",
            summary="Summary",
            decisions=["Decision 1"],
            open_items=["Open 1"],
            deviation_count=2,
        )

    def test_skips_when_disabled(self):
        tracker = _make_tracker(google_creds=MagicMock())
        with patch.object(Config, "ENABLE_GOOGLE_DRIVE", False):
            tracker._export_to_google_drive("Sprint", "Summary", [], [], 0)

    def test_skips_when_no_creds(self):
        tracker = _make_tracker(google_creds=None)
        with patch.object(Config, "ENABLE_GOOGLE_DRIVE", True):
            tracker._export_to_google_drive("Sprint", "Summary", [], [], 0)

    @patch("services.google_drive.GoogleDriveService")
    def test_handles_drive_error_gracefully(self, mock_drive_cls):
        mock_drive_cls.side_effect = Exception("Drive API error")
        tracker = _make_tracker(google_creds=MagicMock())

        with patch.object(Config, "ENABLE_GOOGLE_DRIVE", True):
            tracker._export_to_google_drive("Sprint", "Summary", [], [], 0)


# ---------------------------------------------------------------------------
# Tests: _export_to_gmail
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="Gmail service export not yet implemented on tracker")
class TestExportToGmail:
    """Test Gmail export logic in the tracker."""

    @patch("services.gmail_service.GmailService")
    def test_sends_when_enabled_with_creds_and_attendees(self, mock_gmail_cls):
        mock_gmail = MagicMock()
        mock_gmail.send_meeting_summary.return_value = True
        mock_gmail_cls.return_value = mock_gmail

        tracker = _make_tracker(
            google_creds=MagicMock(),
            attendees=["alice@example.com"],
        )
        tracker.agenda_formatted = "1. Sprint progress"

        with patch.object(Config, "ENABLE_GMAIL_SUMMARY", True):
            tracker._export_to_gmail(
                "Sprint", "Summary", ["Decision"], ["Open item"], 1
            )

        mock_gmail.send_meeting_summary.assert_called_once_with(
            to_emails=["alice@example.com"],
            meeting_title="Sprint",
            agenda="1. Sprint progress",
            summary="Summary",
            decisions=["Decision"],
            open_items=["Open item"],
            deviation_count=1,
        )

    def test_skips_when_disabled(self):
        tracker = _make_tracker(
            google_creds=MagicMock(),
            attendees=["alice@example.com"],
        )
        with patch.object(Config, "ENABLE_GMAIL_SUMMARY", False):
            tracker._export_to_gmail("Sprint", "Summary", [], [], 0)

    def test_skips_when_no_creds(self):
        tracker = _make_tracker(
            google_creds=None,
            attendees=["alice@example.com"],
        )
        with patch.object(Config, "ENABLE_GMAIL_SUMMARY", True):
            tracker._export_to_gmail("Sprint", "Summary", [], [], 0)

    def test_skips_when_no_attendees(self):
        tracker = _make_tracker(
            google_creds=MagicMock(),
            attendees=[],
        )
        with patch.object(Config, "ENABLE_GMAIL_SUMMARY", True):
            tracker._export_to_gmail("Sprint", "Summary", [], [], 0)

    @patch("services.gmail_service.GmailService")
    def test_handles_gmail_error_gracefully(self, mock_gmail_cls):
        mock_gmail_cls.side_effect = Exception("Gmail API error")
        tracker = _make_tracker(
            google_creds=MagicMock(),
            attendees=["alice@example.com"],
        )
        with patch.object(Config, "ENABLE_GMAIL_SUMMARY", True):
            tracker._export_to_gmail("Sprint", "Summary", [], [], 0)


# ---------------------------------------------------------------------------
# Tests: _save_to_memory with G Suite exports
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="_save_to_memory with G Suite exports not yet implemented")
class TestSaveToMemoryWithGSuite:
    """Test that _save_to_memory triggers G Suite exports."""

    def test_calls_drive_and_gmail_exports(self):
        tracker = _make_tracker(
            google_creds=MagicMock(),
            meeting_title="Sprint Sync",
            attendees=["alice@example.com"],
        )
        tracker.state.rolling_summary = "Good progress on sprint items"
        tracker.state.deviation_counter = 1
        tracker.agenda_formatted = "1. Sprint progress"
        tracker.agenda_items = ["Sprint progress"]
        tracker.meeting_id = "test-meet"

        # LLM returns proper summary data
        tracker.llm.call.return_value = FAKE_SUMMARY_DATA

        with ExitStack() as stack:
            mock_drive = stack.enter_context(patch.object(tracker, "_export_to_google_drive"))
            mock_gmail = stack.enter_context(patch.object(tracker, "_export_to_gmail"))
            mock_chat = stack.enter_context(patch.object(tracker, "_export_to_google_chat"))
            for p in _save_patches():
                stack.enter_context(p)
            tracker._save_to_memory()

        # Memory should be saved
        tracker.memory.save_meeting.assert_called_once()

        # All exports should be called
        mock_drive.assert_called_once()
        mock_gmail.assert_called_once()
        mock_chat.assert_called_once()

        # Check title falls back correctly
        drive_call_args = mock_drive.call_args
        assert drive_call_args[0][0] == "Sprint Sync"

    def test_uses_meeting_id_as_fallback_title(self):
        tracker = _make_tracker(
            google_creds=MagicMock(),
            meeting_title="",  # No title
        )
        tracker.state.rolling_summary = "Summary"
        tracker.state.deviation_counter = 0
        tracker.agenda_formatted = "Agenda"
        tracker.agenda_items = []
        tracker.meeting_id = "abc-defg-hij"

        tracker.llm.call.return_value = FAKE_SUMMARY_DATA

        with ExitStack() as stack:
            mock_drive = stack.enter_context(patch.object(tracker, "_export_to_google_drive"))
            mock_gmail = stack.enter_context(patch.object(tracker, "_export_to_gmail"))
            stack.enter_context(patch.object(tracker, "_export_to_google_chat"))
            for p in _save_patches():
                stack.enter_context(p)
            tracker._save_to_memory()

        drive_call_args = mock_drive.call_args
        assert drive_call_args[0][0] == "Meeting abc-defg-hij"

    def test_extracts_decisions_from_llm_summary(self):
        """Decisions and action items should be extracted from the LLM summary structure."""
        tracker = _make_tracker()
        tracker.state.rolling_summary = "Good meeting"
        tracker.state.deviation_counter = 0
        tracker.agenda_formatted = "1. Hiring\n2. Budget"
        tracker.agenda_items = ["Hiring", "Budget"]
        tracker.meeting_id = "test"

        tracker.llm.call.return_value = {
            "title": "Hiring & Budget Review",
            "summary": "Good discussion",
            "agenda_items": [
                {"number": 1, "topic": "Hiring", "status": "completed",
                 "key_points": [], "decisions": ["Hire 3 engineers"],
                 "action_items": ["Post job listings"]},
                {"number": 2, "topic": "Budget", "status": "partial",
                 "key_points": [], "decisions": ["Cut marketing spend"],
                 "action_items": ["Prepare Q4 forecast"]},
            ],
            "overall_action_items": [
                {"owner": "Bob", "action": "Review budget sheet", "deadline": None}
            ],
            "focus_score": "mostly_focused",
        }

        with ExitStack() as stack:
            stack.enter_context(patch.object(tracker, "_export_to_google_drive"))
            stack.enter_context(patch.object(tracker, "_export_to_gmail"))
            stack.enter_context(patch.object(tracker, "_export_to_google_chat"))
            for p in _save_patches():
                stack.enter_context(p)
            tracker._save_to_memory()

        save_call = tracker.memory.save_meeting.call_args
        decisions = save_call[1]["decisions"]
        open_items = save_call[1]["open_items"]

        assert "Hire 3 engineers" in decisions
        assert "Cut marketing spend" in decisions
        assert "Post job listings" in open_items
        assert "Prepare Q4 forecast" in open_items
        assert "Review budget sheet" in open_items
