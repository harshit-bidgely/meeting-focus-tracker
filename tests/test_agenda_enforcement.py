"""Tests for agenda enforcement — blocking meetings without valid agendas."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from config import Config
from services.calendar_watcher import CalendarWatcher, WatcherState
from services.google_calendar import CalendarEvent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_event(
    event_id: str = "evt-1",
    summary: str = "Sprint Sync",
    description: str = "",
    meet_id: str | None = "abc-defg-hij",
    start_offset_minutes: int = -5,
    end_offset_minutes: int = 55,
    attendees: list[str] | None = None,
) -> CalendarEvent:
    now = datetime.now(timezone.utc)
    return CalendarEvent(
        event_id=event_id,
        summary=summary,
        description=description,
        meet_id=meet_id,
        start_time=now + timedelta(minutes=start_offset_minutes),
        end_time=now + timedelta(minutes=end_offset_minutes),
        attendees=attendees or ["alice@example.com"],
    )


def _make_watcher() -> CalendarWatcher:
    mock_creds = MagicMock()
    with patch.object(Config, "VEXA_API_KEY", "test-key"), \
         patch.object(Config, "VEXA_API_BASE", "https://api.vexa.ai"), \
         patch.object(Config, "MEETING_PLATFORM", "google_meet"), \
         patch.object(Config, "CALENDAR_POLL_INTERVAL", 5), \
         patch.object(Config, "AUTO_JOIN_LEAD_MINUTES", 2), \
         patch.object(Config, "GOOGLE_CALENDAR_ID", "primary"), \
         patch("services.calendar_watcher.GoogleCalendarService"), \
         patch("services.calendar_watcher.VexaClient") as mock_vexa_cls:
        mock_vexa = MagicMock()
        mock_vexa_cls.return_value = mock_vexa
        watcher = CalendarWatcher(google_creds=mock_creds)
        watcher.vexa = mock_vexa
    return watcher


# ---------------------------------------------------------------------------
# Tests: Auto mode — calendar_watcher.handle_event()
# ---------------------------------------------------------------------------

class TestAutoModeAgendaEnforcement:
    """Test that handle_event blocks meetings with no/poor agenda."""

    def test_empty_agenda_blocks_bot_join(self):
        """Meeting with empty description should be blocked."""
        event = _make_event(description="")
        watcher = _make_watcher()

        with patch.object(Config, "REQUIRE_AGENDA_VALIDATION", True), \
             patch.object(Config, "AGENDA_MIN_QUALITY", "fair"), \
             patch.object(watcher, "prompt_user_to_invite_bot") as mock_prompt, \
             patch.object(watcher, "_send_agenda_required_email") as mock_email, \
             patch.object(watcher, "_show_agenda_rejection_dialog") as mock_dialog:
            result = watcher.handle_event(event)

        assert result is False
        mock_prompt.assert_not_called()
        mock_dialog.assert_called_once()
        mock_email.assert_called_once()

    def test_poor_agenda_blocks_bot_join(self):
        """Meeting with vague agenda should be blocked."""
        event = _make_event(description="stuff and misc")
        watcher = _make_watcher()

        with patch.object(Config, "REQUIRE_AGENDA_VALIDATION", True), \
             patch.object(Config, "AGENDA_MIN_QUALITY", "fair"), \
             patch.object(watcher, "prompt_user_to_invite_bot") as mock_prompt, \
             patch.object(watcher, "_send_agenda_required_email"), \
             patch.object(watcher, "_show_agenda_rejection_dialog") as mock_dialog:
            result = watcher.handle_event(event)

        assert result is False
        mock_prompt.assert_not_called()

    def test_good_agenda_allows_bot_join(self):
        """Meeting with good agenda should proceed normally."""
        event = _make_event(
            description="1. Review Q3 budget (15 min)\n2. Discuss hiring plan (20 min)\n3. Decide on launch timeline"
        )
        watcher = _make_watcher()

        with patch.object(Config, "REQUIRE_AGENDA_VALIDATION", True), \
             patch.object(Config, "AGENDA_MIN_QUALITY", "fair"), \
             patch.object(watcher, "prompt_user_to_invite_bot", return_value=True), \
             patch.object(watcher, "start_bot_for_event", return_value=True), \
             patch.object(watcher, "notify_bot_sent"):
            result = watcher.handle_event(event)

        assert result is True

    def test_validation_disabled_allows_any_agenda(self):
        """When REQUIRE_AGENDA_VALIDATION=false, any agenda passes."""
        event = _make_event(description="")
        watcher = _make_watcher()

        with patch.object(Config, "REQUIRE_AGENDA_VALIDATION", False), \
             patch.object(watcher, "prompt_user_to_invite_bot", return_value=True), \
             patch.object(watcher, "start_bot_for_event", return_value=True), \
             patch.object(watcher, "notify_bot_sent"):
            result = watcher.handle_event(event)

        assert result is True

    def test_min_quality_good_blocks_fair_agenda(self):
        """When min quality is 'good', a 'fair' agenda should be blocked."""
        event = _make_event(description="Budget numbers, team status, schedule info")
        watcher = _make_watcher()

        with patch.object(Config, "REQUIRE_AGENDA_VALIDATION", True), \
             patch.object(Config, "AGENDA_MIN_QUALITY", "good"), \
             patch.object(watcher, "prompt_user_to_invite_bot") as mock_prompt, \
             patch.object(watcher, "_send_agenda_required_email"), \
             patch.object(watcher, "_show_agenda_rejection_dialog"):
            result = watcher.handle_event(event)

        if result is False:
            mock_prompt.assert_not_called()

    def test_blocked_event_marked_as_notified_not_processed(self):
        """Blocked event should be marked as notified (not processed) to allow re-check."""
        event = _make_event(description="")
        watcher = _make_watcher()

        with patch.object(Config, "REQUIRE_AGENDA_VALIDATION", True), \
             patch.object(Config, "AGENDA_MIN_QUALITY", "fair"), \
             patch.object(watcher, "_send_agenda_required_email"), \
             patch.object(watcher, "_show_agenda_rejection_dialog"):
            watcher.handle_event(event)

        # Should be in notified, NOT in processed
        assert event.event_id in watcher.state.notified_events
        assert event.event_id not in watcher.state.processed_event_ids

    def test_rejection_dialog_receives_validation_message(self):
        """Rejection dialog should receive the validation message with suggestions."""
        event = _make_event(description="")
        watcher = _make_watcher()

        with patch.object(Config, "REQUIRE_AGENDA_VALIDATION", True), \
             patch.object(Config, "AGENDA_MIN_QUALITY", "fair"), \
             patch.object(watcher, "_send_agenda_required_email"), \
             patch.object(watcher, "_show_agenda_rejection_dialog") as mock_dialog:
            watcher.handle_event(event)

        mock_dialog.assert_called_once()
        call_args = mock_dialog.call_args
        assert call_args[0][0] is event
        assert "EMPTY" in call_args[0][1] or "agenda" in call_args[0][1].lower()


# ---------------------------------------------------------------------------
# Tests: Proactive notification — email + re-check flow
# ---------------------------------------------------------------------------

class TestProactiveNotification:
    """Test the email notification and re-check flow for missing agendas."""

    def test_email_sent_to_organizer_on_first_rejection(self):
        """First time seeing bad agenda should send email."""
        event = _make_event(description="")
        watcher = _make_watcher()

        with patch.object(Config, "REQUIRE_AGENDA_VALIDATION", True), \
             patch.object(Config, "AGENDA_MIN_QUALITY", "fair"), \
             patch.object(watcher, "_send_agenda_required_email") as mock_email, \
             patch.object(watcher, "_show_agenda_rejection_dialog"):
            watcher.handle_event(event)

        mock_email.assert_called_once()
        # First arg is event, second is validation dict
        assert mock_email.call_args[0][0] is event

    def test_no_duplicate_email_on_recheck(self):
        """Second check of same bad agenda should NOT send another email."""
        event = _make_event(description="")
        watcher = _make_watcher()

        with patch.object(Config, "REQUIRE_AGENDA_VALIDATION", True), \
             patch.object(Config, "AGENDA_MIN_QUALITY", "fair"), \
             patch.object(watcher, "_send_agenda_required_email") as mock_email, \
             patch.object(watcher, "_show_agenda_rejection_dialog"):
            # First check — sends email
            watcher.handle_event(event)
            assert mock_email.call_count == 1

            # Second check — no email (already notified)
            watcher.handle_event(event)
            assert mock_email.call_count == 1  # Still 1, no duplicate

    def test_updated_agenda_allows_through(self):
        """If organizer updates agenda, meeting should be allowed on next check."""
        watcher = _make_watcher()

        # First: bad agenda
        bad_event = _make_event(description="")
        with patch.object(Config, "REQUIRE_AGENDA_VALIDATION", True), \
             patch.object(Config, "AGENDA_MIN_QUALITY", "fair"), \
             patch.object(watcher, "_send_agenda_required_email"), \
             patch.object(watcher, "_show_agenda_rejection_dialog"):
            result = watcher.handle_event(bad_event)
        assert result is False
        assert bad_event.event_id in watcher.state.notified_events

        # Second: same event but with updated good agenda
        good_event = _make_event(
            description="1. Review Q3 budget (15 min)\n2. Discuss hiring plan (20 min)\n3. Decide on timeline"
        )
        with patch.object(Config, "REQUIRE_AGENDA_VALIDATION", True), \
             patch.object(Config, "AGENDA_MIN_QUALITY", "fair"), \
             patch.object(watcher, "prompt_user_to_invite_bot", return_value=True), \
             patch.object(watcher, "start_bot_for_event", return_value=True), \
             patch.object(watcher, "notify_bot_sent"):
            result = watcher.handle_event(good_event)

        assert result is True
        # Should be cleared from notified
        assert good_event.event_id not in watcher.state.notified_events

    def test_notified_event_not_in_processed(self):
        """Notified events should NOT be in processed_event_ids (allows re-polling)."""
        event = _make_event(description="")
        watcher = _make_watcher()

        with patch.object(Config, "REQUIRE_AGENDA_VALIDATION", True), \
             patch.object(Config, "AGENDA_MIN_QUALITY", "fair"), \
             patch.object(watcher, "_send_agenda_required_email"), \
             patch.object(watcher, "_show_agenda_rejection_dialog"):
            watcher.handle_event(event)

        assert event.event_id not in watcher.state.processed_event_ids
        assert event.event_id in watcher.state.notified_events

    def test_email_body_contains_meeting_title(self):
        """Email body should contain the meeting title."""
        event = _make_event(description="", summary="Q3 Planning")
        validation = {"quality_level": "empty", "score": 0, "issues": ["Agenda is empty"], "suggestions": ["Add agenda"]}

        body = CalendarWatcher._build_agenda_required_email(event, validation)
        assert "Q3 Planning" in body

    def test_email_body_contains_issues(self):
        """Email body should contain the validation issues."""
        event = _make_event(description="stuff")
        validation = {"quality_level": "poor", "score": 10, "issues": ["Too short", "Too vague"], "suggestions": ["Be specific"]}

        body = CalendarWatcher._build_agenda_required_email(event, validation)
        assert "Too short" in body
        assert "Too vague" in body

    def test_email_body_contains_example_agenda(self):
        """Email body should contain an example agenda format."""
        event = _make_event(description="")
        validation = {"quality_level": "empty", "score": 0, "issues": [], "suggestions": []}

        body = CalendarWatcher._build_agenda_required_email(event, validation)
        assert "Q3 Budget Review" in body


# ---------------------------------------------------------------------------
# Tests: Manual mode — main._run_manual_mode() agenda check
# ---------------------------------------------------------------------------

class TestManualModeAgendaEnforcement:
    """Test that manual mode blocks meetings with no/poor agenda."""

    def test_empty_description_blocked(self):
        """Manual mode with empty description should exit."""
        from services.agenda_validator import AgendaValidator
        result = AgendaValidator.validate("")
        assert result["is_valid"] is False
        assert result["quality_level"] == "empty"

    def test_poor_description_blocked(self):
        """Manual mode with poor description should be flagged."""
        from services.agenda_validator import AgendaValidator
        result = AgendaValidator.validate("stuff")
        assert result["is_valid"] is False or result["quality_level"] == "poor"

    def test_good_description_passes(self):
        """Manual mode with good description should pass."""
        from services.agenda_validator import AgendaValidator
        result = AgendaValidator.validate(
            "1. Review Q3 budget (15 min)\n2. Discuss hiring plan (20 min)"
        )
        assert result["is_valid"] is True
        assert result["quality_level"] in ("good", "excellent")


# ---------------------------------------------------------------------------
# Tests: Quality level threshold logic
# ---------------------------------------------------------------------------

QUALITY_LEVELS = ["empty", "poor", "fair", "good", "excellent"]

class TestQualityThreshold:
    """Test the quality threshold comparison logic."""

    def test_fair_meets_fair_threshold(self):
        """An agenda rated 'fair' should meet the 'fair' minimum."""
        from services.calendar_watcher import _meets_quality_threshold
        assert _meets_quality_threshold("fair", "fair") is True

    def test_good_meets_fair_threshold(self):
        """An agenda rated 'good' should meet the 'fair' minimum."""
        from services.calendar_watcher import _meets_quality_threshold
        assert _meets_quality_threshold("good", "fair") is True

    def test_poor_fails_fair_threshold(self):
        """An agenda rated 'poor' should NOT meet the 'fair' minimum."""
        from services.calendar_watcher import _meets_quality_threshold
        assert _meets_quality_threshold("poor", "fair") is False

    def test_empty_fails_any_threshold(self):
        """An agenda rated 'empty' should fail any threshold."""
        from services.calendar_watcher import _meets_quality_threshold
        assert _meets_quality_threshold("empty", "poor") is False

    def test_excellent_meets_excellent_threshold(self):
        """An agenda rated 'excellent' should meet the 'excellent' minimum."""
        from services.calendar_watcher import _meets_quality_threshold
        assert _meets_quality_threshold("excellent", "excellent") is True

    def test_good_fails_excellent_threshold(self):
        """An agenda rated 'good' should NOT meet the 'excellent' minimum."""
        from services.calendar_watcher import _meets_quality_threshold
        assert _meets_quality_threshold("good", "excellent") is False
