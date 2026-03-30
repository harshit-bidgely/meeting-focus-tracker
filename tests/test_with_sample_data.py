"""Integration-style test that simulates 3 cycles of the tracker state machine.

Cycle 1: on_track     → counter stays 0, no alert
Cycle 2: off_topic    → counter goes to 1, no alert
Cycle 3: off_topic    → counter goes to 2, alert triggered

Mocks: VexaClient and LLMClient to avoid real API calls.
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from config import Config
from tracker import MeetingFocusTracker, MeetingState


# ---------------------------------------------------------------------------
# Fixtures for mocked LLM responses
# ---------------------------------------------------------------------------

AGENDA_RESPONSE = {
    "status": "extracted",
    "agenda": [
        {"number": 1, "topic": "Q3 revenue review", "time_estimate_minutes": 10},
        {"number": 2, "topic": "Hiring plan", "time_estimate_minutes": 15},
    ],
    "formatted": "1. Q3 revenue review (10 min)\n2. Hiring plan (15 min)",
}

CYCLE_1_ON_TRACK = {
    "current_topic": "Discussing Q3 revenue numbers",
    "mapped_agenda_item": 1,
    "deviation_level": "on_track",
    "confidence": 0.9,
    "reason": "Directly discussing Q3 revenue figures.",
    "suggestion": None,
    "updated_summary": "Narrative: Team began reviewing Q3 revenue.\n\n[1. Q3 revenue] in_progress: reviewing numbers",
    "current_agenda_item_number": 1,
}

CYCLE_2_OFF_TOPIC = {
    "current_topic": "Weekend football game discussion",
    "mapped_agenda_item": None,
    "deviation_level": "off_topic",
    "confidence": 0.95,
    "reason": "Discussing weekend sports, unrelated to any agenda item.",
    "suggestion": "Let's return to Q3 revenue review.",
    "updated_summary": "Narrative: Discussion drifted to weekend football.\n\n[1. Q3 revenue] in_progress: reviewing numbers",
    "current_agenda_item_number": 1,
}

CYCLE_3_OFF_TOPIC = {
    "current_topic": "Fantasy league picks",
    "mapped_agenda_item": None,
    "deviation_level": "off_topic",
    "confidence": 0.97,
    "reason": "Continued off-topic conversation about fantasy sports.",
    "suggestion": "Let's get back to the hiring plan discussion.",
    "updated_summary": "Narrative: Still off-topic with fantasy sports talk.\n\n[1. Q3 revenue] in_progress: reviewing numbers",
    "current_agenda_item_number": 1,
}

SAMPLE_TRANSCRIPT_SEGMENTS = [
    {
        "text": " Let's look at the Q3 numbers now",
        "speaker": "Alice",
        "absolute_start_time": "2026-03-29T10:00:05Z",
        "completed": True,
    },
    {
        "text": " Revenue is up twelve percent year over year",
        "speaker": "Bob",
        "absolute_start_time": "2026-03-29T10:00:15Z",
        "completed": True,
    },
]

SAMPLE_TRANSCRIPT_SEGMENTS_2 = [
    {
        "text": " Did you guys watch the game this weekend",
        "speaker": "Alice",
        "absolute_start_time": "2026-03-29T10:01:05Z",
        "completed": True,
    },
    {
        "text": " Yeah it was amazing, what a comeback",
        "speaker": "Bob",
        "absolute_start_time": "2026-03-29T10:01:15Z",
        "completed": True,
    },
]

SAMPLE_TRANSCRIPT_SEGMENTS_3 = [
    {
        "text": " I'm picking the top running back in my fantasy league",
        "speaker": "Alice",
        "absolute_start_time": "2026-03-29T10:02:05Z",
        "completed": True,
    },
    {
        "text": " Good call, he's been on fire this season",
        "speaker": "Bob",
        "absolute_start_time": "2026-03-29T10:02:15Z",
        "completed": True,
    },
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestTrackerStateMachine:
    """Test the state machine logic across 3 cycles."""

    def _make_tracker(self) -> MeetingFocusTracker:
        """Create a tracker with mocked VexaClient and LLMClient."""
        with patch.object(Config, "LLM_API_KEY", "test-key"), \
             patch.object(Config, "LLM_API_BASE", "https://api.groq.com/openai/v1"), \
             patch.object(Config, "VEXA_API_KEY", "test-key"), \
             patch.object(Config, "MEETING_PLATFORM", "google_meet"), \
             patch.object(Config, "DEVIATION_THRESHOLD", 2), \
             patch.object(Config, "ALERT_COOLDOWN", 180), \
             patch.object(Config, "POLL_INTERVAL", 1):
            tracker = MeetingFocusTracker(meeting_id="test-meeting")
        tracker.vexa = MagicMock()
        tracker.llm = MagicMock()
        return tracker

    def test_three_cycle_state_progression(self):
        """Cycle 1: on_track, Cycle 2: off_topic, Cycle 3: off_topic → alert."""
        tracker = self._make_tracker()

        # --- Agenda extraction ---
        tracker.llm.call.return_value = AGENDA_RESPONSE
        agenda = tracker.extract_agenda("Discuss Q3 revenue, hiring plan")
        assert "Q3 revenue" in agenda
        assert "Hiring plan" in agenda

        # --- Cycle 1: on_track ---
        tracker.vexa.get_transcript.return_value = {"segments": SAMPLE_TRANSCRIPT_SEGMENTS}
        tracker.llm.call.return_value = CYCLE_1_ON_TRACK

        new_text = tracker.fetch_new_transcript()
        assert "Q3 numbers" in new_text
        result = tracker.analyze(new_text)
        tracker.update_state(result)

        assert tracker.state.deviation_counter == 0
        assert tracker.state.current_agenda_item == 1
        assert "Q3 revenue" in tracker.state.rolling_summary
        assert not tracker.maybe_send_alert(result)

        # --- Cycle 2: off_topic ---
        tracker.vexa.get_transcript.return_value = {"segments": SAMPLE_TRANSCRIPT_SEGMENTS_2}
        tracker.llm.call.return_value = CYCLE_2_OFF_TOPIC

        new_text = tracker.fetch_new_transcript()
        result = tracker.analyze(new_text)
        tracker.update_state(result)

        assert tracker.state.deviation_counter == 1
        assert not tracker.maybe_send_alert(result)  # counter=1 < threshold=2

        # --- Cycle 3: off_topic → alert! ---
        tracker.vexa.get_transcript.return_value = {"segments": SAMPLE_TRANSCRIPT_SEGMENTS_3}
        tracker.llm.call.return_value = CYCLE_3_OFF_TOPIC

        new_text = tracker.fetch_new_transcript()
        result = tracker.analyze(new_text)
        tracker.update_state(result)

        assert tracker.state.deviation_counter == 2
        alert_sent = tracker.maybe_send_alert(result)
        assert alert_sent

        # Verify the chat was called with the right message format
        tracker.vexa.send_chat.assert_called_once()
        call_args = tracker.vexa.send_chat.call_args
        message = call_args[1]["text"] if "text" in call_args[1] else call_args[0][2]
        assert "\U0001f534" in message  # Red circle for off_topic
        assert "Suggestion" in message

    def test_on_track_resets_deviation_counter(self):
        """Going back on track should reset the counter to 0."""
        tracker = self._make_tracker()
        tracker.agenda_formatted = "1. Q3 revenue review"

        # Simulate 1 off_topic cycle
        tracker.llm.call.return_value = CYCLE_2_OFF_TOPIC
        tracker.vexa.get_transcript.return_value = {"segments": SAMPLE_TRANSCRIPT_SEGMENTS_2}
        new_text = tracker.fetch_new_transcript()
        result = tracker.analyze(new_text)
        tracker.update_state(result)
        assert tracker.state.deviation_counter == 1

        # Now go back on_track
        tracker.llm.call.return_value = CYCLE_1_ON_TRACK
        tracker.vexa.get_transcript.return_value = {"segments": SAMPLE_TRANSCRIPT_SEGMENTS}
        new_text = tracker.fetch_new_transcript()
        result = tracker.analyze(new_text)
        tracker.update_state(result)
        assert tracker.state.deviation_counter == 0  # Reset!

    def test_tangential_adds_half(self):
        """Tangential deviation should add 0.5 to the counter."""
        tracker = self._make_tracker()
        tracker.agenda_formatted = "1. Q3 revenue review"

        tangential_result = {
            "deviation_level": "tangential",
            "updated_summary": "drifting...",
            "current_agenda_item_number": 1,
        }
        tracker.update_state(tangential_result)
        assert tracker.state.deviation_counter == 0.5

        tracker.update_state(tangential_result)
        assert tracker.state.deviation_counter == 1.0

    def test_cooldown_prevents_repeated_alerts(self):
        """After an alert is sent, another alert within cooldown should be suppressed."""
        tracker = self._make_tracker()
        tracker.agenda_formatted = "1. Q3 revenue"
        tracker.state.deviation_counter = 2
        tracker.state.last_alert_time = time.time()  # Alert just sent

        result = CYCLE_3_OFF_TOPIC
        alert_sent = tracker.maybe_send_alert(result)
        assert not alert_sent  # Suppressed by cooldown

    def test_cooldown_expired_allows_alert(self):
        """After cooldown expires, a new alert should be sent."""
        tracker = self._make_tracker()
        tracker.agenda_formatted = "1. Q3 revenue"
        tracker.state.deviation_counter = 2
        # Set last alert time to 200 seconds ago (cooldown is 180)
        tracker.state.last_alert_time = time.time() - 200

        alert_sent = tracker.maybe_send_alert(CYCLE_3_OFF_TOPIC)
        assert alert_sent
        tracker.vexa.send_chat.assert_called_once()

    def test_alert_message_format_off_topic(self):
        """Off-topic alert should use red circle emoji."""
        tracker = self._make_tracker()
        tracker.state.deviation_counter = 2
        tracker.state.last_alert_time = 0

        tracker.maybe_send_alert(CYCLE_3_OFF_TOPIC)
        call_args = tracker.vexa.send_chat.call_args
        message = call_args[0][2]
        assert "\U0001f534 Off Topic:" in message
        assert "\U0001f4a1 Suggestion:" in message

    def test_alert_message_format_tangential(self):
        """Tangential alert should use yellow circle emoji."""
        tracker = self._make_tracker()
        tracker.state.deviation_counter = 2
        tracker.state.last_alert_time = 0

        tangential_result = {
            "deviation_level": "tangential",
            "reason": "Related but drifting from main topic.",
            "suggestion": "Focus on the agenda item.",
            "updated_summary": "",
            "current_agenda_item_number": 1,
        }
        tracker.maybe_send_alert(tangential_result)
        call_args = tracker.vexa.send_chat.call_args
        message = call_args[0][2]
        assert "\U0001f7e1 Drifting:" in message

    def test_no_agenda_found_exits_gracefully(self):
        """If no agenda is found, extract_agenda returns empty string."""
        tracker = self._make_tracker()
        tracker.llm.call.return_value = {
            "status": "no_agenda_found",
            "agenda": [],
            "formatted": "",
        }
        result = tracker.extract_agenda("Just a zoom link, no agenda")
        assert result == ""
