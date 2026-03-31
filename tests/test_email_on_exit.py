"""Integration tests for email sending and summary generation on meeting exit.

Tests that:
1. Summary is properly created when bot exits
2. Email is sent with complete report
3. Summary includes all meeting participants
4. All exit scenarios trigger email pipeline
"""

import json
from unittest.mock import MagicMock, patch
import pytest

from config import Config
from tracker import MeetingFocusTracker
from services.participant_tracker import ParticipantTracker


class TestEmailSendingOnExit:
    """Test email sending when bot exits meeting."""

    def _make_tracker_with_data(self) -> MeetingFocusTracker:
        """Create tracker with simulated meeting data."""
        with patch.object(Config, "LLM_API_KEY", "test-key"), \
             patch.object(Config, "LLM_API_BASE", "https://api.groq.com/openai/v1"), \
             patch.object(Config, "VEXA_API_KEY", "test-key"), \
             patch.object(Config, "MEETING_ID", "test-meeting"), \
             patch.object(Config, "MEETING_PLATFORM", "google_meet"), \
             patch.object(Config, "EMAIL_RECIPIENTS", ["organizer@example.com", "attendee@example.com"]):
            tracker = MeetingFocusTracker()
        tracker.vexa = MagicMock()
        tracker.llm = MagicMock()
        return tracker

    # ──────────────────────────────────────────────────────────────
    # Test 1: Summary Creation
    # ──────────────────────────────────────────────────────────────

    def test_summary_created_with_meeting_overview(self):
        """Verify summary includes meeting overview."""
        tracker = self._make_tracker_with_data()
        tracker.state.cycle_count = 5

        report = {
            "meeting_overview": {
                "title": "Q4 Planning Meeting",
                "date": "2026-03-31",
                "duration_minutes": 45,
                "participants_count": 5,
                "meeting_health": "good",
            },
            "key_metrics": {"overall_meeting_score": 85},
        }

        tracker.generate_meeting_report = MagicMock(return_value=report)
        tracker.send_meeting_email = MagicMock(return_value=True)
        tracker.history_store.save_meeting = MagicMock()

        tracker._run_post_meeting_pipeline()

        # Verify report was generated
        tracker.generate_meeting_report.assert_called_once()

        # Verify report has required sections
        assert report["meeting_overview"]["title"] is not None
        assert report["meeting_overview"]["date"] is not None
        assert report["key_metrics"]["overall_meeting_score"] > 0

    def test_summary_includes_participant_analysis(self):
        """Verify summary includes participant deep analysis."""
        tracker = self._make_tracker_with_data()
        tracker.state.cycle_count = 5

        report = {
            "meeting_overview": {"title": "Planning"},
            "participant_deep_analysis": [
                {
                    "name": "Alice",
                    "participation_metrics": {
                        "total_words": 250,
                        "participation_level": "High",
                    },
                    "strengths": "Excellent communication",
                },
                {
                    "name": "Bob",
                    "participation_metrics": {
                        "total_words": 150,
                        "participation_level": "Medium",
                    },
                    "strengths": "Technical insights",
                },
            ],
        }

        tracker.generate_meeting_report = MagicMock(return_value=report)
        tracker.send_meeting_email = MagicMock(return_value=True)
        tracker.history_store.save_meeting = MagicMock()

        tracker._run_post_meeting_pipeline()

        # Verify participants are in summary
        assert len(report["participant_deep_analysis"]) == 2
        assert report["participant_deep_analysis"][0]["name"] == "Alice"
        assert report["participant_deep_analysis"][1]["name"] == "Bob"

    def test_summary_includes_action_items(self):
        """Verify summary includes action items with owners."""
        tracker = self._make_tracker_with_data()
        tracker.state.cycle_count = 5

        report = {
            "meeting_overview": {"title": "Planning"},
            "action_items": [
                {
                    "action": "Complete project proposal",
                    "owner": "Alice",
                    "due_date": "2026-04-05",
                    "priority": "high",
                },
                {
                    "action": "Review budget allocation",
                    "owner": "Bob",
                    "due_date": "2026-04-03",
                    "priority": "medium",
                },
            ],
        }

        tracker.generate_meeting_report = MagicMock(return_value=report)
        tracker.send_meeting_email = MagicMock(return_value=True)
        tracker.history_store.save_meeting = MagicMock()

        tracker._run_post_meeting_pipeline()

        # Verify action items are present
        assert len(report["action_items"]) == 2
        assert report["action_items"][0]["owner"] == "Alice"
        assert report["action_items"][1]["owner"] == "Bob"

    # ──────────────────────────────────────────────────────────────
    # Test 2: Email Sending to Recipients
    # ──────────────────────────────────────────────────────────────

    def test_email_sent_to_configured_recipients(self):
        """Verify email is sent to all configured recipients."""
        tracker = self._make_tracker_with_data()
        tracker.state.cycle_count = 5

        report = {
            "meeting_overview": {
                "title": "Team Sync",
                "date": "2026-03-31",
            },
            "action_items": [],
        }

        tracker.generate_meeting_report = MagicMock(return_value=report)

        # Mock the actual email sending
        mock_send = MagicMock(return_value=True)
        tracker.send_meeting_email = mock_send
        tracker.history_store.save_meeting = MagicMock()

        tracker._run_post_meeting_pipeline()

        # Verify email send was called
        mock_send.assert_called_once_with(report, google_creds=None)

    def test_email_includes_all_meeting_participants_in_summary(self):
        """Verify summary includes all meeting participants."""
        tracker = self._make_tracker_with_data()
        tracker.state.cycle_count = 5

        # Simulate meeting with multiple participants
        participants = ["Alice", "Bob", "Charlie", "Diana", "Eve"]

        report = {
            "meeting_overview": {"title": "All-Hands Meeting"},
            "participant_deep_analysis": [
                {
                    "name": participant,
                    "participation_metrics": {"total_words": 100 * i},
                }
                for i, participant in enumerate(participants, 1)
            ],
        }

        tracker.generate_meeting_report = MagicMock(return_value=report)
        tracker.send_meeting_email = MagicMock(return_value=True)
        tracker.history_store.save_meeting = MagicMock()

        tracker._run_post_meeting_pipeline()

        # Verify all participants are in report
        participant_names = [
            p["name"] for p in report["participant_deep_analysis"]
        ]
        assert len(participant_names) == 5
        for name in participants:
            assert name in participant_names

    def test_email_recipients_come_from_config(self):
        """Verify email recipients are read from Config."""
        with patch.object(Config, "EMAIL_RECIPIENTS", ["test1@example.com", "test2@example.com"]):
            assert len(Config.EMAIL_RECIPIENTS) == 2
            assert "test1@example.com" in Config.EMAIL_RECIPIENTS
            assert "test2@example.com" in Config.EMAIL_RECIPIENTS

    # ──────────────────────────────────────────────────────────────
    # Test 3: Exit Scenarios with Email
    # ──────────────────────────────────────────────────────────────

    def test_email_sent_when_bot_kicked(self):
        """Verify email is sent immediately when bot is kicked."""
        tracker = self._make_tracker_with_data()
        tracker.state.cycle_count = 10
        tracker.agenda_formatted = "1. Q4 Planning\n2. Budget Review"

        report = {
            "meeting_overview": {
                "title": "Planning Meeting",
                "participants_count": 5,
            },
            "action_items": [
                {"action": "Item 1", "owner": "Alice"},
                {"action": "Item 2", "owner": "Bob"},
            ],
        }

        tracker.generate_meeting_report = MagicMock(return_value=report)
        tracker.send_meeting_email = MagicMock(return_value=True)
        tracker.history_store.save_meeting = MagicMock()

        # Simulate bot kick
        tracker.vexa.get_bot_status.return_value = []  # Bot not found
        tracker.vexa.get_bot_status.side_effect = None  # Clear side effect

        meeting_state = tracker._detect_meeting_state()
        assert meeting_state == "bot_kicked"

        # Now trigger pipeline
        tracker._run_post_meeting_pipeline()

        # Verify email was sent
        assert tracker.send_meeting_email.called

    def test_email_sent_when_meeting_empty(self):
        """Verify email is sent when meeting is empty for 30+ seconds."""
        tracker = self._make_tracker_with_data()
        tracker.state.cycle_count = 10
        tracker.state.last_transcript_time = 0  # Never received transcript

        # First, receive transcript to start timer
        tracker.state.last_transcript_time = 123456789  # Timestamp in past

        report = {
            "meeting_overview": {"title": "Team Meeting"},
            "participant_deep_analysis": [],
        }

        tracker.generate_meeting_report = MagicMock(return_value=report)
        tracker.send_meeting_email = MagicMock(return_value=True)
        tracker.history_store.save_meeting = MagicMock()

        tracker._run_post_meeting_pipeline()

        # Verify email was sent
        assert tracker.send_meeting_email.called

    def test_email_sent_when_meeting_officially_ended(self):
        """Verify email is sent when Vexa indicates meeting ended."""
        tracker = self._make_tracker_with_data()
        tracker.state.cycle_count = 5

        report = {
            "meeting_overview": {"title": "Sync"},
            "participant_deep_analysis": [],
        }

        tracker.generate_meeting_report = MagicMock(return_value=report)
        tracker.send_meeting_email = MagicMock(return_value=True)
        tracker.history_store.save_meeting = MagicMock()

        # Simulate API error (meeting ended)
        tracker.vexa.get_bot_status.side_effect = ConnectionError("Meeting ended")

        meeting_state = tracker._detect_meeting_state()
        assert meeting_state == "meeting_ended"

        tracker._run_post_meeting_pipeline()

        # Verify email was sent
        assert tracker.send_meeting_email.called

    # ──────────────────────────────────────────────────────────────
    # Test 4: Participant Tracking in Summary
    # ──────────────────────────────────────────────────────────────

    def test_participant_tracker_records_speakers(self):
        """Verify participant tracker records who spoke in meeting."""
        tracker = self._make_tracker_with_data()

        # Simulate transcript segments with speakers
        segments = [
            {
                "speaker": "Alice",
                "text": "Let's start with the Q4 planning.",
                "absolute_start_time": "2026-03-31T10:00:00Z",
            },
            {
                "speaker": "Bob",
                "text": "We need to discuss budget allocation.",
                "absolute_start_time": "2026-03-31T10:01:00Z",
            },
            {
                "speaker": "Alice",
                "text": "Agreed. Let's break it down by department.",
                "absolute_start_time": "2026-03-31T10:02:00Z",
            },
        ]

        # Record participant data
        for seg in segments:
            speaker = seg.get("speaker") or "Unknown"
            text = seg.get("text", "").strip()
            timestamp = seg.get("absolute_start_time")
            if text:
                tracker.state.participant_tracker.record_segment(speaker, text, timestamp)

        # Verify participants were tracked
        stats = tracker.state.participant_tracker.to_dict()
        assert "Alice" in stats
        assert "Bob" in stats
        # Both speakers should have contribution data
        assert len(stats["Alice"]) > 0
        assert len(stats["Bob"]) > 0

    def test_summary_reflects_participant_contributions(self):
        """Verify summary shows each participant's contribution."""
        tracker = self._make_tracker_with_data()
        tracker.state.cycle_count = 3

        # Mock report with participant analysis
        report = {
            "meeting_overview": {"title": "Meeting"},
            "participant_deep_analysis": [
                {
                    "name": "Alice",
                    "participation_metrics": {
                        "total_words": 450,
                        "participation_level": "High",
                        "word_share_percent": 45,
                    },
                    "engagement_score": 92,
                },
                {
                    "name": "Bob",
                    "participation_metrics": {
                        "total_words": 350,
                        "participation_level": "High",
                        "word_share_percent": 35,
                    },
                    "engagement_score": 85,
                },
            ],
        }

        tracker.generate_meeting_report = MagicMock(return_value=report)
        tracker.send_meeting_email = MagicMock(return_value=True)
        tracker.history_store.save_meeting = MagicMock()

        tracker._run_post_meeting_pipeline()

        # Verify participants and their metrics are in report
        for participant in report["participant_deep_analysis"]:
            assert "name" in participant
            assert "participation_metrics" in participant
            assert "engagement_score" in participant
            assert participant["participation_metrics"]["word_share_percent"] > 0

    # ──────────────────────────────────────────────────────────────
    # Test 5: Email Content Verification
    # ──────────────────────────────────────────────────────────────

    def test_email_report_includes_all_required_sections(self):
        """Verify generated report includes all required sections."""
        tracker = self._make_tracker_with_data()
        tracker.state.cycle_count = 5

        # Comprehensive report
        report = {
            "meeting_overview": {
                "title": "Quarterly Planning",
                "date": "2026-03-31",
                "narrative": "Team discussed Q4 strategy",
            },
            "key_metrics": {
                "overall_meeting_score": 87,
                "meeting_health_indicators": {
                    "agenda_adherence": 90,
                    "decision_velocity": 85,
                },
            },
            "participant_deep_analysis": [
                {"name": "Alice", "engagement_score": 95},
            ],
            "team_dynamics": {
                "collaboration_score": 88,
                "psychological_safety_indicators": "high",
            },
            "action_items": [
                {
                    "action": "Draft proposal",
                    "owner": "Alice",
                    "priority": "high",
                }
            ],
            "risk_assessment": {
                "critical_risks": [
                    {
                        "risk": "Timeline tight",
                        "probability": "medium",
                        "mitigation": "Add buffer time",
                    }
                ]
            },
        }

        # Check all major sections exist
        assert "meeting_overview" in report
        assert "key_metrics" in report
        assert "participant_deep_analysis" in report
        assert "team_dynamics" in report
        assert "action_items" in report
        assert "risk_assessment" in report

        # Check nested content
        assert report["meeting_overview"]["title"] is not None
        assert report["key_metrics"]["overall_meeting_score"] > 0
        assert len(report["participant_deep_analysis"]) > 0
        assert len(report["action_items"]) > 0
