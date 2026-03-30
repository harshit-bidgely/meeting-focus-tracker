"""Tests for the Google Calendar service."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest

from services.google_calendar import GoogleCalendarService, CalendarEvent


# ---------------------------------------------------------------------------
# Fixtures: sample Google Calendar API event data
# ---------------------------------------------------------------------------

def _make_event(
    event_id: str = "evt-1",
    summary: str = "Q3 Strategy Sync",
    description: str = "1. Revenue review\n2. Hiring plan",
    start_offset_minutes: int = -30,
    end_offset_minutes: int = 30,
    meet_id: str | None = "abc-defg-hij",
    attendees: list[dict] | None = None,
    all_day: bool = False,
) -> dict:
    """Build a fake Google Calendar API event dict."""
    now = datetime.now(timezone.utc)
    start = now + timedelta(minutes=start_offset_minutes)
    end = now + timedelta(minutes=end_offset_minutes)

    if attendees is None:
        attendees = [
            {"email": "alice@example.com", "self": False},
            {"email": "bob@example.com", "self": False},
            {"email": "me@example.com", "self": True},
        ]

    event = {
        "id": event_id,
        "summary": summary,
        "description": description,
        "attendees": attendees,
    }

    if all_day:
        event["start"] = {"date": start.strftime("%Y-%m-%d")}
        event["end"] = {"date": end.strftime("%Y-%m-%d")}
    else:
        event["start"] = {"dateTime": start.isoformat()}
        event["end"] = {"dateTime": end.isoformat()}

    if meet_id:
        event["conferenceData"] = {
            "entryPoints": [
                {"entryPointType": "video", "uri": f"https://meet.google.com/{meet_id}"}
            ]
        }

    return event


def _make_service(events: list[dict]) -> GoogleCalendarService:
    """Create a GoogleCalendarService with a mocked API backend."""
    mock_creds = MagicMock()
    with patch("services.google_calendar.build") as mock_build:
        mock_api = MagicMock()
        mock_build.return_value = mock_api

        mock_list = MagicMock()
        mock_list.execute.return_value = {"items": events}
        mock_api.events.return_value.list.return_value = mock_list

        service = GoogleCalendarService(mock_creds)
        # Re-assign to use the mock after __init__
        service.service = mock_api
    return service


# ---------------------------------------------------------------------------
# Tests: _extract_meet_id
# ---------------------------------------------------------------------------

class TestExtractMeetId:
    """Test Google Meet ID extraction from various event formats."""

    def test_extract_from_conference_data(self):
        event = {
            "conferenceData": {
                "entryPoints": [
                    {"entryPointType": "video", "uri": "https://meet.google.com/abc-defg-hij"}
                ]
            }
        }
        assert GoogleCalendarService._extract_meet_id(event) == "abc-defg-hij"

    def test_extract_from_hangout_link(self):
        event = {"hangoutLink": "https://meet.google.com/xyz-abcd-efg"}
        assert GoogleCalendarService._extract_meet_id(event) == "xyz-abcd-efg"

    def test_extract_from_description(self):
        event = {"description": "Join at https://meet.google.com/pqr-stuv-wxy for the call"}
        assert GoogleCalendarService._extract_meet_id(event) == "pqr-stuv-wxy"

    def test_conference_data_takes_priority(self):
        """conferenceData should be checked before hangoutLink."""
        event = {
            "conferenceData": {
                "entryPoints": [
                    {"entryPointType": "video", "uri": "https://meet.google.com/aaa-bbbb-ccc"}
                ]
            },
            "hangoutLink": "https://meet.google.com/xxx-yyyy-zzz",
        }
        assert GoogleCalendarService._extract_meet_id(event) == "aaa-bbbb-ccc"

    def test_no_meet_link_returns_none(self):
        event = {"description": "Just a regular meeting, no video link"}
        assert GoogleCalendarService._extract_meet_id(event) is None

    def test_empty_event_returns_none(self):
        assert GoogleCalendarService._extract_meet_id({}) is None

    def test_invalid_meet_url_format_returns_none(self):
        """Meet IDs must match the 3-4-3 letter pattern."""
        event = {"hangoutLink": "https://meet.google.com/invalid-format"}
        assert GoogleCalendarService._extract_meet_id(event) is None

    def test_multiple_entry_points(self):
        """Should find the Meet link among multiple entry points."""
        event = {
            "conferenceData": {
                "entryPoints": [
                    {"entryPointType": "phone", "uri": "tel:+1-555-0123"},
                    {"entryPointType": "video", "uri": "https://meet.google.com/abc-defg-hij"},
                ]
            }
        }
        assert GoogleCalendarService._extract_meet_id(event) == "abc-defg-hij"


# ---------------------------------------------------------------------------
# Tests: _parse_event
# ---------------------------------------------------------------------------

class TestParseEvent:
    """Test raw event parsing into CalendarEvent dataclass."""

    def _get_service(self) -> GoogleCalendarService:
        mock_creds = MagicMock()
        with patch("services.google_calendar.build"):
            return GoogleCalendarService(mock_creds)

    def test_parse_normal_event(self):
        service = self._get_service()
        event = _make_event()
        parsed = service._parse_event(event)

        assert parsed is not None
        assert parsed.event_id == "evt-1"
        assert parsed.summary == "Q3 Strategy Sync"
        assert parsed.description == "1. Revenue review\n2. Hiring plan"
        assert parsed.meet_id == "abc-defg-hij"

    def test_parse_all_day_event_returns_none(self):
        """All-day events don't have dateTime, should return None."""
        service = self._get_service()
        event = _make_event(all_day=True)
        assert service._parse_event(event) is None

    def test_parse_attendees_excludes_self(self):
        """Self-attendee should be filtered out."""
        service = self._get_service()
        event = _make_event()
        parsed = service._parse_event(event)

        assert len(parsed.attendees) == 2
        assert "me@example.com" not in parsed.attendees
        assert "alice@example.com" in parsed.attendees
        assert "bob@example.com" in parsed.attendees

    def test_parse_event_no_attendees(self):
        service = self._get_service()
        event = _make_event(attendees=[])
        parsed = service._parse_event(event)
        assert parsed.attendees == []

    def test_parse_event_no_meet_id(self):
        service = self._get_service()
        event = _make_event(meet_id=None)
        parsed = service._parse_event(event)
        assert parsed.meet_id is None

    def test_parse_missing_summary_defaults(self):
        service = self._get_service()
        event = _make_event()
        del event["summary"]
        parsed = service._parse_event(event)
        assert parsed.summary == "Untitled Meeting"

    def test_parse_missing_description_defaults(self):
        service = self._get_service()
        event = _make_event()
        del event["description"]
        parsed = service._parse_event(event)
        assert parsed.description == ""


# ---------------------------------------------------------------------------
# Tests: get_current_or_next_event
# ---------------------------------------------------------------------------

class TestGetCurrentOrNextEvent:
    """Test event selection logic (in-progress preferred, then next upcoming)."""

    def test_returns_in_progress_event(self):
        """Should prefer an event that is currently in progress."""
        in_progress = _make_event(
            event_id="in-progress",
            start_offset_minutes=-30,
            end_offset_minutes=30,
        )
        upcoming = _make_event(
            event_id="upcoming",
            start_offset_minutes=60,
            end_offset_minutes=120,
        )
        service = _make_service([in_progress, upcoming])
        result = service.get_current_or_next_event()

        assert result is not None
        assert result.event_id == "in-progress"

    def test_returns_next_upcoming_when_none_in_progress(self):
        """When no event is in progress, return the next upcoming one."""
        upcoming = _make_event(
            event_id="next-up",
            start_offset_minutes=10,
            end_offset_minutes=70,
        )
        service = _make_service([upcoming])
        result = service.get_current_or_next_event()

        assert result is not None
        assert result.event_id == "next-up"

    def test_returns_none_when_no_events(self):
        service = _make_service([])
        assert service.get_current_or_next_event() is None

    def test_skips_all_day_events(self):
        """All-day events should be skipped."""
        all_day = _make_event(all_day=True, event_id="all-day")
        service = _make_service([all_day])
        assert service.get_current_or_next_event() is None


# ---------------------------------------------------------------------------
# Tests: get_event_by_meet_id
# ---------------------------------------------------------------------------

class TestGetEventByMeetId:
    """Test meeting lookup by Google Meet code."""

    def test_finds_matching_event(self):
        event = _make_event(meet_id="abc-defg-hij")
        service = _make_service([event])
        result = service.get_event_by_meet_id("abc-defg-hij")

        assert result is not None
        assert result.meet_id == "abc-defg-hij"

    def test_returns_none_when_no_match(self):
        event = _make_event(meet_id="abc-defg-hij")
        service = _make_service([event])
        assert service.get_event_by_meet_id("zzz-zzzz-zzz") is None

    def test_returns_none_for_empty_events(self):
        service = _make_service([])
        assert service.get_event_by_meet_id("abc-defg-hij") is None


# ---------------------------------------------------------------------------
# Tests: CalendarEvent dataclass
# ---------------------------------------------------------------------------

class TestCalendarEvent:
    """Test the CalendarEvent dataclass."""

    def test_fields(self):
        now = datetime.now(timezone.utc)
        event = CalendarEvent(
            event_id="test",
            summary="Test Meeting",
            description="Agenda here",
            meet_id="abc-defg-hij",
            start_time=now,
            end_time=now + timedelta(hours=1),
            attendees=["alice@example.com"],
        )
        assert event.event_id == "test"
        assert event.summary == "Test Meeting"
        assert event.meet_id == "abc-defg-hij"
        assert len(event.attendees) == 1
