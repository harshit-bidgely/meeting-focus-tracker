"""Tests for the Gmail service."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from services.gmail_service import GmailService


# ---------------------------------------------------------------------------
# Helper to create a GmailService with mocked API
# ---------------------------------------------------------------------------

def _make_gmail_service(send_succeeds: bool = True) -> tuple[GmailService, MagicMock]:
    """Create a GmailService with mocked Gmail API."""
    mock_creds = MagicMock()
    with patch("services.gmail_service.build") as mock_build:
        mock_api = MagicMock()
        mock_build.return_value = mock_api

        if send_succeeds:
            mock_api.users.return_value.messages.return_value.send.return_value.execute.return_value = {
                "id": "msg-123",
                "threadId": "thread-456",
            }
        else:
            mock_api.users.return_value.messages.return_value.send.return_value.execute.side_effect = (
                Exception("Gmail API error")
            )

        service = GmailService(mock_creds)
        service.service = mock_api
    return service, mock_api


# ---------------------------------------------------------------------------
# Tests: _build_email_body
# ---------------------------------------------------------------------------

class TestBuildEmailBody:
    """Test HTML email body generation."""

    def test_includes_meeting_title(self):
        body = GmailService._build_email_body(
            "Q3 Strategy", "1. Revenue", "Good discussion", [], [], 0
        )
        assert "Q3 Strategy" in body
        assert "Meeting Summary" in body

    def test_includes_agenda(self):
        body = GmailService._build_email_body(
            "Sprint", "1. Progress\n2. Blockers", "Summary text", [], [], 0
        )
        assert "1. Progress" in body
        assert "2. Blockers" in body

    def test_includes_summary(self):
        body = GmailService._build_email_body(
            "Sprint", "Agenda", "We discussed blockers in detail", [], [], 0
        )
        assert "We discussed blockers in detail" in body

    def test_includes_decisions(self):
        body = GmailService._build_email_body(
            "Sprint", "Agenda", "Summary",
            ["Hire 3 engineers", "Launch on Monday"], [], 0
        )
        assert "Decisions Made" in body
        assert "Hire 3 engineers" in body
        assert "Launch on Monday" in body

    def test_includes_open_items(self):
        body = GmailService._build_email_body(
            "Sprint", "Agenda", "Summary",
            [], ["Need pricing proposal", "Review Q4 budget"], 0
        )
        assert "Open Items" in body
        assert "Need pricing proposal" in body
        assert "Review Q4 budget" in body

    def test_no_decisions_section_when_empty(self):
        body = GmailService._build_email_body(
            "Sprint", "Agenda", "Summary", [], [], 0
        )
        assert "Decisions Made" not in body

    def test_no_open_items_section_when_empty(self):
        body = GmailService._build_email_body(
            "Sprint", "Agenda", "Summary", [], [], 0
        )
        assert "Open Items" not in body

    def test_includes_deviation_count(self):
        body = GmailService._build_email_body(
            "Sprint", "Agenda", "Summary", [], [], 5
        )
        assert "5" in body
        assert "off-topic" in body.lower()

    def test_html_structure(self):
        body = GmailService._build_email_body(
            "Meeting", "Agenda", "Summary", ["Decision 1"], ["Open 1"], 2
        )
        assert "<h2>" in body
        assert "<h3>" in body
        assert "<li>" in body
        assert "</div>" in body

    def test_newlines_converted_to_br(self):
        body = GmailService._build_email_body(
            "Meeting", "Line1\nLine2", "Summary1\nSummary2", [], [], 0
        )
        assert "<br>" in body


# ---------------------------------------------------------------------------
# Tests: send_meeting_summary
# ---------------------------------------------------------------------------

class TestSendMeetingSummary:
    """Test email sending logic."""

    def test_returns_false_for_empty_recipients(self):
        service, _ = _make_gmail_service()
        result = service.send_meeting_summary(
            to_emails=[],
            meeting_title="Sprint",
            agenda="1. Progress",
            summary="Good meeting",
            decisions=[],
            open_items=[],
            deviation_count=0,
        )
        assert result is False

    def test_sends_email_successfully(self):
        service, mock_api = _make_gmail_service(send_succeeds=True)
        result = service.send_meeting_summary(
            to_emails=["alice@example.com", "bob@example.com"],
            meeting_title="Q3 Review",
            agenda="1. Revenue\n2. Costs",
            summary="Reviewed revenue and costs",
            decisions=["Cut marketing spend"],
            open_items=["Need Q4 projections"],
            deviation_count=1,
        )
        assert result is True
        mock_api.users.return_value.messages.return_value.send.assert_called_once()

    def test_returns_false_on_api_error(self):
        service, _ = _make_gmail_service(send_succeeds=False)
        result = service.send_meeting_summary(
            to_emails=["alice@example.com"],
            meeting_title="Sprint",
            agenda="Agenda",
            summary="Summary",
            decisions=[],
            open_items=[],
            deviation_count=0,
        )
        assert result is False

    def test_send_uses_correct_user_id(self):
        service, mock_api = _make_gmail_service(send_succeeds=True)
        service.send_meeting_summary(
            to_emails=["alice@example.com"],
            meeting_title="Sprint",
            agenda="Agenda",
            summary="Summary",
            decisions=[],
            open_items=[],
            deviation_count=0,
        )
        mock_api.users.return_value.messages.return_value.send.assert_called_once()
        call_kwargs = mock_api.users.return_value.messages.return_value.send.call_args
        assert call_kwargs[1]["userId"] == "me"

    def test_email_subject_contains_title(self):
        """The raw email data should contain the meeting title in the subject."""
        service, mock_api = _make_gmail_service(send_succeeds=True)
        service.send_meeting_summary(
            to_emails=["alice@example.com"],
            meeting_title="Important Sync",
            agenda="Agenda",
            summary="Summary",
            decisions=[],
            open_items=[],
            deviation_count=0,
        )
        call_kwargs = mock_api.users.return_value.messages.return_value.send.call_args
        raw_body = call_kwargs[1]["body"]["raw"]
        # Decode the base64 raw email to verify subject
        import base64
        decoded = base64.urlsafe_b64decode(raw_body).decode("utf-8")
        assert "Meeting Summary: Important Sync" in decoded
