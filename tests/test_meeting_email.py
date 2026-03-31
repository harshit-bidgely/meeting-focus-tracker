"""Unit tests for prompts/meeting_email.py and services/email_formatter.py."""

import json

import pytest

from prompts.meeting_email import build_email_user_message
from services.email_formatter import format_email_html, format_email_text


# ---------------------------------------------------------------------------
# Fixtures — a minimal but complete email_data dict
# ---------------------------------------------------------------------------

MINIMAL_EMAIL_DATA = {
    "executive_summary": {
        "overview": "Team reviewed Q3 numbers and finalised the hiring plan.",
        "productive": True,
        "key_outcomes": ["Q3 revenue confirmed at 12% YoY", "Hiring plan approved for 5 engineers"],
    },
    "participant_contributions": [
        {
            "name": "Alice",
            "participation_level": "High",
            "contribution_type": "decision-making",
            "word_count": 300,
            "word_share_pct": 60.0,
            "notable_inputs": "Led Q3 discussion and proposed hiring timeline.",
            "engagement_flag": None,
        },
        {
            "name": "Bob",
            "participation_level": "Low",
            "contribution_type": "passive",
            "word_count": 50,
            "word_share_pct": 10.0,
            "notable_inputs": "Insufficient data",
            "engagement_flag": "Low engagement — spoke fewer than 50 words",
        },
    ],
    "efficiency_score": {
        "score": 72,
        "breakdown": {
            "participation_balance": 15,
            "time_utilization": 20,
            "progress_made": 22,
            "redundancy_penalty": 15,
        },
        "justification": "Good progress but imbalanced participation.",
    },
    "redundancy_analysis": {
        "repeated_topics": ["Q3 forecast mentioned twice"],
        "compared_to_history": "No previous meeting data available.",
        "added_new_value": True,
        "summary": "Mostly new content with minor repetition.",
    },
    "progress_tracking": {
        "status": "incremental",
        "moved_forward": ["Q3 review completed"],
        "remained_stuck": [],
        "repeated_without_progress": [],
        "comparison_note": "First meeting in this series.",
    },
    "minutes_of_meeting": {
        "date": "2026-03-29",
        "attendees": ["Alice", "Bob"],
        "agenda_items_covered": [
            {
                "item_number": 1,
                "title": "Q3 revenue review",
                "discussion_summary": "Team confirmed 12% YoY growth.",
                "outcome": "decided",
                "decisions": ["Accept Q3 numbers", "Share with board"],
            }
        ],
        "action_items": [
            {
                "action": "Send Q3 report to board",
                "owner": "Alice",
                "due_date": "2026-04-01",
                "priority": "high",
                "context": "Alice agreed to send the report after the meeting.",
            }
        ],
    },
    "actionable_insights": [
        "Encourage Bob to contribute more in future sessions.",
        "Set a strict agenda time box for each item.",
    ],
    "key_flags": {
        "low_engagement": ["Bob — 50 words, 10% share"],
        "dominating_speakers": [],
        "off_topic_periods": [],
        "inefficient_time": [],
        "notes": None,
    },
}

MEETING_META = {
    "meeting_id": "abc-defg-hij",
    "platform": "google_meet",
    "date": "2026-03-29",
    "total_cycles": 5,
}


# ---------------------------------------------------------------------------
# Tests for build_email_user_message
# ---------------------------------------------------------------------------

class TestBuildEmailUserMessage:
    def test_contains_agenda(self):
        msg = build_email_user_message(
            agenda="1. Q3 review\n2. Hiring plan",
            full_transcript="[Alice]: hello",
            participant_stats={"Alice": {"word_count": 1}},
            rolling_summary="Discussed Q3.",
            deviation_stats={"total_cycles": 3},
            previous_meetings=[],
            meeting_meta=MEETING_META,
        )
        assert "1. Q3 review" in msg
        assert "2. Hiring plan" in msg

    def test_contains_transcript(self):
        msg = build_email_user_message(
            agenda="1. Topic",
            full_transcript="[Alice]: specific transcript line",
            participant_stats={},
            rolling_summary="",
            deviation_stats={},
            previous_meetings=[],
            meeting_meta={},
        )
        assert "specific transcript line" in msg

    def test_previous_meetings_empty_shows_placeholder(self):
        msg = build_email_user_message(
            agenda="1. Topic",
            full_transcript="",
            participant_stats={},
            rolling_summary="",
            deviation_stats={},
            previous_meetings=[],
            meeting_meta={},
        )
        assert "No previous meeting data available" in msg

    def test_previous_meetings_serialised(self):
        prev = [{"meeting_id": "old-meet", "efficiency_score": {"score": 60}}]
        msg = build_email_user_message(
            agenda="",
            full_transcript="",
            participant_stats={},
            rolling_summary="",
            deviation_stats={},
            previous_meetings=prev,
            meeting_meta={},
        )
        assert "old-meet" in msg

    def test_empty_agenda_shows_placeholder(self):
        msg = build_email_user_message(
            agenda="",
            full_transcript="",
            participant_stats={},
            rolling_summary="",
            deviation_stats={},
            previous_meetings=[],
            meeting_meta={},
        )
        assert "No agenda available" in msg

    def test_participant_stats_serialised_as_json(self):
        stats = {"Alice": {"word_count": 150, "participation_level": "High"}}
        msg = build_email_user_message(
            agenda="1. Topic",
            full_transcript="",
            participant_stats=stats,
            rolling_summary="",
            deviation_stats={},
            previous_meetings=[],
            meeting_meta={},
        )
        assert '"word_count": 150' in msg


# ---------------------------------------------------------------------------
# Tests for format_email_html
# ---------------------------------------------------------------------------

class TestFormatEmailHtml:
    def test_returns_string(self):
        html = format_email_html(MINIMAL_EMAIL_DATA, MEETING_META)
        assert isinstance(html, str)

    def test_contains_doctype(self):
        html = format_email_html(MINIMAL_EMAIL_DATA, MEETING_META)
        assert "<!DOCTYPE html>" in html

    def test_contains_participant_names(self):
        html = format_email_html(MINIMAL_EMAIL_DATA, MEETING_META)
        assert "Alice" in html
        assert "Bob" in html

    def test_contains_meeting_id(self):
        html = format_email_html(MINIMAL_EMAIL_DATA, MEETING_META)
        assert "abc-defg-hij" in html

    def test_executive_summary_section_present(self):
        html = format_email_html(MINIMAL_EMAIL_DATA, MEETING_META)
        assert "Executive Summary" in html

    def test_participant_contribution_section_present(self):
        html = format_email_html(MINIMAL_EMAIL_DATA, MEETING_META)
        assert "Participant Contribution" in html

    def test_efficiency_score_present(self):
        html = format_email_html(MINIMAL_EMAIL_DATA, MEETING_META)
        assert "72" in html  # the score value

    def test_action_items_owner_present(self):
        html = format_email_html(MINIMAL_EMAIL_DATA, MEETING_META)
        assert "Alice" in html
        assert "Send Q3 report to board" in html

    def test_key_flags_section_present(self):
        html = format_email_html(MINIMAL_EMAIL_DATA, MEETING_META)
        assert "Key Flags" in html

    def test_empty_data_does_not_raise(self):
        html = format_email_html({}, {})
        assert isinstance(html, str)
        assert "<!DOCTYPE html>" in html

    def test_html_escaping_prevents_xss(self):
        """Injected script tags in data must be escaped."""
        evil_data = dict(MINIMAL_EMAIL_DATA)
        evil_data["executive_summary"] = {
            "overview": "<script>alert('xss')</script>",
            "productive": False,
            "key_outcomes": [],
        }
        html = format_email_html(evil_data, MEETING_META)
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_mom_section_present(self):
        html = format_email_html(MINIMAL_EMAIL_DATA, MEETING_META)
        assert "Minutes of Meeting" in html

    def test_progress_tracking_section_present(self):
        html = format_email_html(MINIMAL_EMAIL_DATA, MEETING_META)
        assert "Progress Tracking" in html


# ---------------------------------------------------------------------------
# Tests for format_email_text
# ---------------------------------------------------------------------------

class TestFormatEmailText:
    def test_returns_string(self):
        text = format_email_text(MINIMAL_EMAIL_DATA, MEETING_META)
        assert isinstance(text, str)

    def test_no_html_tags(self):
        text = format_email_text(MINIMAL_EMAIL_DATA, MEETING_META)
        assert "<" not in text
        assert ">" not in text

    def test_contains_participant_names(self):
        text = format_email_text(MINIMAL_EMAIL_DATA, MEETING_META)
        assert "Alice" in text
        assert "Bob" in text

    def test_contains_section_headers(self):
        text = format_email_text(MINIMAL_EMAIL_DATA, MEETING_META)
        for header in ["EXECUTIVE SUMMARY", "PARTICIPANT CONTRIBUTION",
                       "EFFICIENCY SCORE", "MINUTES OF MEETING", "KEY FLAGS"]:
            assert header in text.upper(), f"Missing section: {header}"

    def test_action_items_with_owner(self):
        text = format_email_text(MINIMAL_EMAIL_DATA, MEETING_META)
        assert "Alice" in text
        assert "Send Q3 report to board" in text

    def test_empty_data_does_not_raise(self):
        text = format_email_text({}, {})
        assert isinstance(text, str)

    def test_no_html_flags_in_empty_flags(self):
        data = dict(MINIMAL_EMAIL_DATA)
        data["key_flags"] = {
            "low_engagement": [],
            "dominating_speakers": [],
            "off_topic_periods": [],
            "inefficient_time": [],
            "notes": None,
        }
        text = format_email_text(data, MEETING_META)
        assert "No significant flags" in text


# ---------------------------------------------------------------------------
# Integration: tracker state flows into email
# ---------------------------------------------------------------------------

class TestTrackerIntegrationWithEmail:
    """Verify that tracker.MeetingState fields feed the email pipeline correctly."""

    def test_participant_tracker_to_dict_used_in_email_message(self):
        from services.participant_tracker import ParticipantTracker

        pt = ParticipantTracker()
        pt.record_segment("Shivank Bhardwaj", "hello world test")
        stats = pt.to_dict()
        msg = build_email_user_message(
            agenda="1. Topic",
            full_transcript="[Shivank Bhardwaj]: hello world test",
            participant_stats=stats,
            rolling_summary="",
            deviation_stats={"total_cycles": 1, "on_track_cycles": 1,
                             "tangential_cycles": 0, "off_topic_cycles": 0},
            previous_meetings=[],
            meeting_meta={"meeting_id": "test", "platform": "google_meet",
                          "date": "2026-03-29", "total_cycles": 1},
        )
        # Exact name must appear in the message
        assert "Shivank Bhardwaj" in msg

    def test_full_transcript_lines_in_message(self):
        lines = [
            "[Alice]: Let's look at Q3",
            "[Bob]: Revenue is up 12 percent",
        ]
        msg = build_email_user_message(
            agenda="1. Q3 review",
            full_transcript="\n".join(lines),
            participant_stats={},
            rolling_summary="",
            deviation_stats={},
            previous_meetings=[],
            meeting_meta={},
        )
        assert "Let's look at Q3" in msg
        assert "Revenue is up 12 percent" in msg
