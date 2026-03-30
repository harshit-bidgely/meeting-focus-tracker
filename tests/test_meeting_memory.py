"""Tests for cross-meeting memory and repetition detection."""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from services.meeting_memory import MeetingMemory
from prompts.repetition_detector import build_repetition_suffix


class TestMeetingMemory:
    """Test local JSON storage and fuzzy matching."""

    def _make_memory(self, tmp_path: str) -> MeetingMemory:
        path = os.path.join(tmp_path, "test_history.json")
        return MeetingMemory(storage_path=path)

    def test_save_and_load(self, tmp_path):
        mem = self._make_memory(str(tmp_path))
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
        # Reload from disk
        mem2 = MeetingMemory(storage_path=mem.storage_path)
        assert len(mem2.data["meetings"]) == 1
        assert mem2.data["meetings"][0]["meeting_id"] == "abc-123"

    def test_fuzzy_match_similar_agenda(self, tmp_path):
        """'Q3 Sales Strategy' should match 'Q3 Sales Planning'."""
        mem = self._make_memory(str(tmp_path))
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

    def test_fuzzy_match_exact(self, tmp_path):
        """Exact same agenda text should match."""
        mem = self._make_memory(str(tmp_path))
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

    def test_no_match_unrelated(self, tmp_path):
        """Unrelated agendas should not match."""
        mem = self._make_memory(str(tmp_path))
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

    def test_empty_memory_returns_empty(self, tmp_path):
        mem = self._make_memory(str(tmp_path))
        related = mem.find_related_meetings(["Anything"])
        assert related == []

    def test_max_results_limit(self, tmp_path):
        mem = self._make_memory(str(tmp_path))
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

    def test_build_context_summary_format(self, tmp_path):
        mem = self._make_memory(str(tmp_path))
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

    def test_corrupted_file_handled(self, tmp_path):
        path = os.path.join(str(tmp_path), "bad.json")
        with open(path, "w") as f:
            f.write("not valid json{{{")
        mem = MeetingMemory(storage_path=path)
        assert mem.data == {"meetings": []}


class TestRepetitionSuffix:
    def test_empty_context_returns_empty(self):
        assert build_repetition_suffix("") == ""
        assert build_repetition_suffix("  ") == ""

    def test_non_empty_context_returns_block(self):
        result = build_repetition_suffix("Some past meeting context")
        assert "PAST MEETING CONTEXT" in result
        assert "Some past meeting context" in result
        assert "REPETITION" in result
