"""Tests for cross-meeting memory (SQLite-backed) and repetition detection."""

from __future__ import annotations

import os
import pytest

from services.meeting_memory import MeetingMemory, DB_PATH
from prompts.repetition_detector import build_repetition_suffix


@pytest.fixture(autouse=True)
def clean_db():
    """Remove the global DB before and after each test for isolation."""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    yield
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)


class TestMeetingMemory:
    """Test SQLite storage and fuzzy matching."""

    def _make_memory(self) -> MeetingMemory:
        return MeetingMemory()

    def test_save_and_load(self):
        mem = self._make_memory()
        mem.save_meeting(
            meeting_id="abc-123",
            date="2026-03-28T14:00:00",
            agenda_raw="1. Q3 Sales Strategy",
            agenda_items=["Q3 Sales Strategy"],
            final_summary="Discussed low revenue in June",
            decisions=["Focus on enterprise"],
            open_items=["Need pricing proposal"],
            deviation_count=2,
        )
        # Verify via query
        meetings = mem.get_all_meetings()
        assert len(meetings) == 1
        assert meetings[0]["meeting_id"] == "abc-123"
        assert meetings[0]["decisions"] == ["Focus on enterprise"]

    def test_fuzzy_match_similar_agenda(self):
        """'Q3 Sales Strategy' should match 'Q3 Sales Planning'."""
        mem = self._make_memory()
        mem.save_meeting(
            meeting_id="m1",
            date="2026-03-21",
            agenda_raw="1. Q3 Sales Strategy",
            agenda_items=["Q3 Sales Strategy"],
            final_summary="Discussed Q3 sales approach",
            decisions=[],
            open_items=[],
            deviation_count=0,
        )
        related = mem.find_related_meetings(["Q3 Sales Planning"], threshold=0.55)
        assert len(related) == 1
        assert related[0]["meeting_id"] == "m1"

    def test_fuzzy_match_exact(self):
        """Exact same agenda text should match."""
        mem = self._make_memory()
        mem.save_meeting(
            meeting_id="m1",
            date="2026-03-21",
            agenda_raw="1. Hiring Plan",
            agenda_items=["Hiring Plan"],
            final_summary="Discussed hiring backend engineers",
            decisions=["Hire 3 engineers"],
            open_items=[],
            deviation_count=0,
        )
        related = mem.find_related_meetings(["Hiring Plan"])
        assert len(related) == 1

    def test_no_match_unrelated(self):
        """Unrelated agendas should not match."""
        mem = self._make_memory()
        mem.save_meeting(
            meeting_id="m1",
            date="2026-03-21",
            agenda_raw="1. Q3 Sales Strategy",
            agenda_items=["Q3 Sales Strategy"],
            final_summary="Sales discussion",
            decisions=[],
            open_items=[],
            deviation_count=0,
        )
        related = mem.find_related_meetings(["Engineering Sprint Planning"], threshold=0.55)
        assert len(related) == 0

    def test_empty_memory_returns_empty(self):
        mem = self._make_memory()
        related = mem.find_related_meetings(["Anything"])
        assert related == []

    def test_max_results_limit(self):
        mem = self._make_memory()
        for i in range(5):
            mem.save_meeting(
                meeting_id=f"m{i}",
                date=f"2026-03-{20+i}",
                agenda_raw="1. Budget Review",
                agenda_items=["Budget Review"],
                final_summary=f"Discussion {i}",
                decisions=[],
                open_items=[],
                deviation_count=0,
            )
        related = mem.find_related_meetings(["Budget Review"], max_results=2)
        assert len(related) == 2

    def test_build_context_summary_format(self):
        mem = self._make_memory()
        meetings = [
            {
                "date": "2026-03-21T14:00:00",
                "final_summary": "Discussed Q3 strategy",
                "decisions": ["Focus on enterprise", "Hire SDRs"],
                "open_items": ["Need pricing proposal"],
            }
        ]
        ctx = mem.build_context_summary(meetings)
        assert "[2026-03-21]" in ctx
        assert "Discussed Q3 strategy" in ctx
        assert "Focus on enterprise" in ctx
        assert "Need pricing proposal" in ctx

    def test_search_decisions(self):
        mem = self._make_memory()
        mem.save_meeting(
            meeting_id="m1",
            date="2026-03-21",
            agenda_raw="1. Hiring",
            agenda_items=["Hiring"],
            final_summary="Discussed hiring",
            decisions=["Hire 3 backend engineers"],
            open_items=[],
            deviation_count=0,
        )
        results = mem.search_decisions("backend")
        assert len(results) == 1

    def test_search_summaries(self):
        mem = self._make_memory()
        mem.save_meeting(
            meeting_id="m1",
            date="2026-03-21",
            agenda_raw="1. Layoffs",
            agenda_items=["Layoffs"],
            final_summary="Discussed layoffs and severance packages",
            decisions=[],
            open_items=[],
            deviation_count=0,
        )
        results = mem.search_summaries("severance")
        assert len(results) == 1


class TestRepetitionSuffix:
    def test_empty_context_returns_empty(self):
        assert build_repetition_suffix("") == ""
        assert build_repetition_suffix("  ") == ""

    def test_non_empty_context_returns_block(self):
        result = build_repetition_suffix("Some past meeting context")
        assert "PAST MEETING CONTEXT" in result
        assert "Some past meeting context" in result
        assert "REPETITION" in result
