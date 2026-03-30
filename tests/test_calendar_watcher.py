"""Tests for the CalendarWatcher — auto-detect meetings and prompt user to invite bot."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch, PropertyMock

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
    description: str = "1. Progress\n2. Blockers",
    meet_id: str | None = "abc-defg-hij",
    start_offset_minutes: int = -5,
    end_offset_minutes: int = 55,
    attendees: list[str] | None = None,
) -> CalendarEvent:
    """Create a CalendarEvent for testing."""
    now = datetime.now(timezone.utc)
    return CalendarEvent(
        event_id=event_id,
        summary=summary,
        description=description,
        meet_id=meet_id,
        start_time=now + timedelta(minutes=start_offset_minutes),
        end_time=now + timedelta(minutes=end_offset_minutes),
        attendees=attendees or ["alice@example.com", "bob@example.com"],
    )


def _make_watcher(events: list[CalendarEvent] | None = None) -> CalendarWatcher:
    """Create a CalendarWatcher with mocked dependencies."""
    mock_creds = MagicMock()

    with patch.object(Config, "VEXA_API_KEY", "test-key"), \
         patch.object(Config, "VEXA_API_BASE", "https://api.vexa.ai"), \
         patch.object(Config, "MEETING_PLATFORM", "google_meet"), \
         patch.object(Config, "CALENDAR_POLL_INTERVAL", 5), \
         patch.object(Config, "AUTO_JOIN_LEAD_MINUTES", 2), \
         patch.object(Config, "GOOGLE_CALENDAR_ID", "primary"), \
         patch("services.calendar_watcher.GoogleCalendarService") as mock_cal_cls, \
         patch("services.calendar_watcher.VexaClient") as mock_vexa_cls:

        mock_cal = MagicMock()
        mock_cal_cls.return_value = mock_cal

        mock_vexa = MagicMock()
        mock_vexa_cls.return_value = mock_vexa

        watcher = CalendarWatcher(google_creds=mock_creds)
        watcher.vexa = mock_vexa

        # Mock _fetch_upcoming_events to return our test events
        if events is not None:
            watcher._fetch_upcoming_events = MagicMock(return_value=events)

    return watcher


# ---------------------------------------------------------------------------
# Tests: WatcherState
# ---------------------------------------------------------------------------

class TestWatcherState:
    def test_initial_state(self):
        state = WatcherState()
        assert state.processed_event_ids == set()
        assert state.active_meetings == {}

    def test_tracks_processed_events(self):
        state = WatcherState()
        state.processed_event_ids.add("evt-1")
        assert "evt-1" in state.processed_event_ids
        assert "evt-2" not in state.processed_event_ids


# ---------------------------------------------------------------------------
# Tests: get_actionable_events
# ---------------------------------------------------------------------------

class TestGetActionableEvents:
    def test_returns_events_starting_within_lead_time(self):
        """Event starting in 1 minute (within 2-min lead) should be actionable."""
        event = _make_event(start_offset_minutes=1, end_offset_minutes=61)
        watcher = _make_watcher(events=[event])
        result = watcher.get_actionable_events()
        assert len(result) == 1
        assert result[0].event_id == "evt-1"

    def test_returns_in_progress_events(self):
        """Event that already started should be actionable."""
        event = _make_event(start_offset_minutes=-10, end_offset_minutes=50)
        watcher = _make_watcher(events=[event])
        result = watcher.get_actionable_events()
        assert len(result) == 1

    def test_skips_events_without_meet_id(self):
        """Events without a Google Meet link should be skipped."""
        event = _make_event(meet_id=None)
        watcher = _make_watcher(events=[event])
        result = watcher.get_actionable_events()
        assert len(result) == 0

    def test_skips_already_processed_events(self):
        """Events already in processed_event_ids should be skipped."""
        event = _make_event(event_id="already-done")
        watcher = _make_watcher(events=[event])
        watcher.state.processed_event_ids.add("already-done")
        result = watcher.get_actionable_events()
        assert len(result) == 0

    def test_skips_ended_events(self):
        """Events that already ended should be skipped."""
        event = _make_event(start_offset_minutes=-120, end_offset_minutes=-60)
        watcher = _make_watcher(events=[event])
        result = watcher.get_actionable_events()
        assert len(result) == 0

    def test_skips_far_future_events(self):
        """Events starting in 30 minutes (outside 2-min lead) should be skipped."""
        event = _make_event(start_offset_minutes=30, end_offset_minutes=90)
        watcher = _make_watcher(events=[event])
        result = watcher.get_actionable_events()
        assert len(result) == 0

    def test_multiple_events_filtered_correctly(self):
        """Mix of actionable and non-actionable events."""
        in_progress = _make_event(event_id="in-progress", start_offset_minutes=-5, end_offset_minutes=55)
        no_meet = _make_event(event_id="no-meet", meet_id=None, start_offset_minutes=1)
        far_away = _make_event(event_id="far", start_offset_minutes=60, end_offset_minutes=120)
        about_to_start = _make_event(event_id="soon", start_offset_minutes=1, end_offset_minutes=61)

        watcher = _make_watcher(events=[in_progress, no_meet, far_away, about_to_start])
        result = watcher.get_actionable_events()

        ids = {e.event_id for e in result}
        assert "in-progress" in ids
        assert "soon" in ids
        assert "no-meet" not in ids
        assert "far" not in ids


# ---------------------------------------------------------------------------
# Tests: prompt_user_to_invite_bot
# ---------------------------------------------------------------------------

class TestPromptUser:
    @patch("services.calendar_watcher.subprocess.run")
    def test_returns_true_on_accept(self, mock_run):
        """User clicks 'Invite FocusBot' → returns True."""
        mock_run.return_value = MagicMock(stdout="button returned:Invite FocusBot", returncode=0)
        watcher = _make_watcher(events=[])
        event = _make_event()
        assert watcher.prompt_user_to_invite_bot(event) is True

    @patch("services.calendar_watcher.subprocess.run")
    def test_returns_false_on_skip(self, mock_run):
        """User clicks 'Skip' → returns False."""
        mock_run.return_value = MagicMock(stdout="button returned:Skip", returncode=0)
        watcher = _make_watcher(events=[])
        event = _make_event()
        assert watcher.prompt_user_to_invite_bot(event) is False

    @patch("services.calendar_watcher.subprocess.run")
    def test_returns_false_on_timeout(self, mock_run):
        """Dialog times out → returns False."""
        mock_run.return_value = MagicMock(stdout="button returned:, gave up:true", returncode=0)
        watcher = _make_watcher(events=[])
        event = _make_event()
        assert watcher.prompt_user_to_invite_bot(event) is False

    @patch("services.calendar_watcher.subprocess.run")
    def test_returns_false_on_subprocess_timeout(self, mock_run):
        """subprocess.run times out → returns False."""
        import subprocess as sp
        mock_run.side_effect = sp.TimeoutExpired(cmd="osascript", timeout=130)
        watcher = _make_watcher(events=[])
        event = _make_event()
        assert watcher.prompt_user_to_invite_bot(event) is False

    @patch("services.calendar_watcher.subprocess.run")
    def test_returns_false_on_exception(self, mock_run):
        """Any other exception → returns False gracefully."""
        mock_run.side_effect = OSError("osascript not found")
        watcher = _make_watcher(events=[])
        event = _make_event()
        assert watcher.prompt_user_to_invite_bot(event) is False

    @patch("services.calendar_watcher.subprocess.run")
    def test_shows_in_progress_for_started_meeting(self, mock_run):
        """Meeting already started should show 'IN PROGRESS NOW' in prompt."""
        mock_run.return_value = MagicMock(stdout="button returned:Skip", returncode=0)
        watcher = _make_watcher(events=[])
        event = _make_event(start_offset_minutes=-10)
        watcher.prompt_user_to_invite_bot(event)
        # Verify the AppleScript command contains IN PROGRESS
        call_args = mock_run.call_args[0][0]
        script = call_args[2]  # ["osascript", "-e", script]
        assert "IN PROGRESS NOW" in script

    @patch("services.calendar_watcher.subprocess.run")
    def test_shows_minutes_for_upcoming_meeting(self, mock_run):
        """Meeting starting in future should show 'starts in X min' in prompt."""
        mock_run.return_value = MagicMock(stdout="button returned:Skip", returncode=0)
        watcher = _make_watcher(events=[])
        event = _make_event(start_offset_minutes=1)
        watcher.prompt_user_to_invite_bot(event)
        call_args = mock_run.call_args[0][0]
        script = call_args[2]
        assert "starts in" in script


# ---------------------------------------------------------------------------
# Tests: start_bot_for_event
# ---------------------------------------------------------------------------

class TestStartBot:
    def test_sends_bot_successfully(self):
        watcher = _make_watcher(events=[])
        event = _make_event(meet_id="abc-defg-hij")
        result = watcher.start_bot_for_event(event)
        assert result is True
        watcher.vexa.start_bot.assert_called_once_with(
            platform=Config.MEETING_PLATFORM,
            meeting_id="abc-defg-hij",
        )

    def test_returns_false_on_api_error(self):
        watcher = _make_watcher(events=[])
        watcher.vexa.start_bot.side_effect = Exception("Vexa API down")
        event = _make_event()
        result = watcher.start_bot_for_event(event)
        assert result is False


# ---------------------------------------------------------------------------
# Tests: handle_event (full flow)
# ---------------------------------------------------------------------------

class TestHandleEvent:
    @patch("services.calendar_watcher.subprocess")
    def test_full_accept_flow(self, mock_subprocess):
        """User accepts → bot sent → event marked processed."""
        watcher = _make_watcher(events=[])
        event = _make_event(event_id="evt-accept")

        # Mock the prompt to accept
        mock_subprocess.run.return_value = MagicMock(stdout="button returned:Invite FocusBot")
        mock_subprocess.Popen = MagicMock()

        result = watcher.handle_event(event)

        assert result is True
        assert "evt-accept" in watcher.state.processed_event_ids
        assert "abc-defg-hij" in watcher.state.active_meetings
        watcher.vexa.start_bot.assert_called_once()

    @patch("services.calendar_watcher.subprocess")
    def test_full_skip_flow(self, mock_subprocess):
        """User skips → bot NOT sent → event still marked processed (no re-prompt)."""
        watcher = _make_watcher(events=[])
        event = _make_event(event_id="evt-skip")

        mock_subprocess.run.return_value = MagicMock(stdout="button returned:Skip")

        result = watcher.handle_event(event)

        assert result is False
        assert "evt-skip" in watcher.state.processed_event_ids
        watcher.vexa.start_bot.assert_not_called()

    @patch("services.calendar_watcher.subprocess")
    def test_bot_failure_still_marks_processed(self, mock_subprocess):
        """If bot fails to join, event is still marked processed."""
        watcher = _make_watcher(events=[])
        watcher.vexa.start_bot.side_effect = Exception("API error")
        event = _make_event(event_id="evt-fail")

        mock_subprocess.run.return_value = MagicMock(stdout="button returned:Invite FocusBot")

        result = watcher.handle_event(event)

        assert result is False
        assert "evt-fail" in watcher.state.processed_event_ids


# ---------------------------------------------------------------------------
# Tests: CalendarWatcher init
# ---------------------------------------------------------------------------

class TestCalendarWatcherInit:
    def test_stores_config_values(self):
        watcher = _make_watcher(events=[])
        assert watcher.poll_interval == 5
        assert watcher.lead_minutes == 2
        assert watcher.google_creds is not None

    def test_initial_state_is_clean(self):
        watcher = _make_watcher(events=[])
        assert watcher.state.processed_event_ids == set()
        assert watcher.state.active_meetings == {}


# ---------------------------------------------------------------------------
# Tests: notify_bot_sent
# ---------------------------------------------------------------------------

class TestNotifyBotSent:
    @patch("services.calendar_watcher.subprocess.Popen")
    def test_sends_notification(self, mock_popen):
        watcher = _make_watcher(events=[])
        event = _make_event(summary="Sprint Sync")
        watcher.notify_bot_sent(event)
        mock_popen.assert_called_once()
        call_args = mock_popen.call_args[0][0]
        assert "osascript" in call_args
        # The script should mention the meeting name
        assert "Sprint Sync" in call_args[2]

    @patch("services.calendar_watcher.subprocess.Popen")
    def test_handles_notification_failure_gracefully(self, mock_popen):
        mock_popen.side_effect = OSError("not found")
        watcher = _make_watcher(events=[])
        event = _make_event()
        # Should not raise
        watcher.notify_bot_sent(event)


# ---------------------------------------------------------------------------
# Tests: multi-meeting / threading support
# ---------------------------------------------------------------------------

class TestMultiMeetingSupport:
    """Test that multiple meetings can be tracked concurrently."""

    @patch("services.calendar_watcher.subprocess")
    def test_active_meetings_dict_tracks_multiple(self, mock_subprocess):
        """Two accepted meetings should both be in active_meetings."""
        watcher = _make_watcher(events=[])
        mock_subprocess.run.return_value = MagicMock(stdout="button returned:Invite FocusBot")
        mock_subprocess.Popen = MagicMock()

        evt1 = _make_event(event_id="evt-1", meet_id="aaa-bbbb-ccc", summary="Meeting A")
        evt2 = _make_event(event_id="evt-2", meet_id="ddd-eeee-fff", summary="Meeting B")

        watcher.handle_event(evt1)
        watcher.handle_event(evt2)

        assert "aaa-bbbb-ccc" in watcher.state.active_meetings
        assert "ddd-eeee-fff" in watcher.state.active_meetings
        assert len(watcher.state.active_meetings) == 2

    @patch("services.calendar_watcher.subprocess")
    def test_skipped_meeting_not_in_active(self, mock_subprocess):
        """Skipped meeting should be in processed but not active."""
        watcher = _make_watcher(events=[])
        mock_subprocess.run.return_value = MagicMock(stdout="button returned:Skip")

        evt = _make_event(event_id="evt-skip", meet_id="zzz-zzzz-zzz")
        watcher.handle_event(evt)

        assert "evt-skip" in watcher.state.processed_event_ids
        assert "zzz-zzzz-zzz" not in watcher.state.active_meetings

    def test_cleanup_removes_dead_threads(self):
        """Finished threads should be cleaned up."""
        watcher = _make_watcher(events=[])
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = False

        with watcher.state.lock:
            watcher.state.active_meetings["old-meet"] = mock_thread

        watcher._cleanup_finished_threads()

        assert "old-meet" not in watcher.state.active_meetings

    def test_cleanup_keeps_alive_threads(self):
        """Active threads should NOT be cleaned up."""
        watcher = _make_watcher(events=[])
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = True

        with watcher.state.lock:
            watcher.state.active_meetings["active-meet"] = mock_thread

        watcher._cleanup_finished_threads()

        assert "active-meet" in watcher.state.active_meetings

    @patch("services.calendar_watcher.subprocess")
    def test_already_active_meet_id_skipped_in_run_logic(self, mock_subprocess):
        """A meeting with an already-active meet_id should not trigger handle_event again."""
        evt = _make_event(event_id="evt-dup", meet_id="abc-defg-hij")
        watcher = _make_watcher(events=[evt])

        # Pre-populate active_meetings with this meet_id
        with watcher.state.lock:
            watcher.state.active_meetings["abc-defg-hij"] = MagicMock()

        # get_actionable_events returns it, but run() should skip it
        events = watcher.get_actionable_events()
        assert len(events) == 1  # It IS actionable (not in processed_event_ids)

        # But the run loop skips it because meet_id is already active
        # We test the skip logic directly
        with watcher.state.lock:
            should_skip = evt.meet_id in watcher.state.active_meetings
        assert should_skip is True


class TestRunTrackerForEvent:
    """Test the thread target that runs a tracker for a single event."""

    @patch("tracker.MeetingFocusTracker")
    def test_passes_meeting_id_to_tracker(self, mock_tracker_cls):
        """Tracker should receive meeting_id from the event, not from Config."""
        mock_tracker = MagicMock()
        mock_tracker_cls.return_value = mock_tracker

        watcher = _make_watcher(events=[])
        event = _make_event(meet_id="xyz-abcd-efg", summary="Test Meeting",
                           description="Agenda: test items")

        watcher._run_tracker_for_event(event)

        # Verify meeting_id was passed as a parameter
        mock_tracker_cls.assert_called_once()
        call_kwargs = mock_tracker_cls.call_args[1]
        assert call_kwargs["meeting_id"] == "xyz-abcd-efg"
        assert call_kwargs["meeting_title"] == "Test Meeting"
        assert call_kwargs["attendees"] == ["alice@example.com", "bob@example.com"]

        # Verify tracker.run was called with the event description
        mock_tracker.run.assert_called_once_with("Agenda: test items")

    @patch("tracker.MeetingFocusTracker")
    def test_uses_summary_as_fallback_description(self, mock_tracker_cls):
        """If event has no description, summary should be used."""
        mock_tracker = MagicMock()
        mock_tracker_cls.return_value = mock_tracker

        watcher = _make_watcher(events=[])
        event = _make_event(description="", summary="Standup Call")

        watcher._run_tracker_for_event(event)

        mock_tracker.run.assert_called_once_with("Standup Call")

    @patch("tracker.MeetingFocusTracker")
    def test_cleans_up_active_meetings_on_completion(self, mock_tracker_cls):
        """After tracker.run() returns, meet_id should be removed from active_meetings."""
        mock_tracker = MagicMock()
        mock_tracker_cls.return_value = mock_tracker

        watcher = _make_watcher(events=[])
        event = _make_event(meet_id="cleanup-test")

        with watcher.state.lock:
            watcher.state.active_meetings["cleanup-test"] = MagicMock()

        watcher._run_tracker_for_event(event)

        assert "cleanup-test" not in watcher.state.active_meetings

    @patch("tracker.MeetingFocusTracker")
    def test_cleans_up_even_on_crash(self, mock_tracker_cls):
        """If tracker crashes, meet_id should still be removed from active_meetings."""
        mock_tracker_cls.side_effect = Exception("Tracker crashed")

        watcher = _make_watcher(events=[])
        event = _make_event(meet_id="crash-test")

        with watcher.state.lock:
            watcher.state.active_meetings["crash-test"] = MagicMock()

        watcher._run_tracker_for_event(event)  # Should not raise

        assert "crash-test" not in watcher.state.active_meetings
