"""Unit tests for services/history_store.py."""

import json
import os
import tempfile

import pytest

from services.history_store import HistoryStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_store(tmp_path):
    """Return a HistoryStore backed by a temp directory."""
    return HistoryStore(history_dir=str(tmp_path))


SAMPLE_SUMMARY = {
    "executive_summary": {"overview": "Good meeting", "productive": True, "key_outcomes": ["Done X"]},
    "participant_contributions": [],
    "efficiency_score": {"score": 75},
}


# ---------------------------------------------------------------------------
# save_meeting
# ---------------------------------------------------------------------------

class TestSaveMeeting:
    def test_creates_json_file(self, tmp_store, tmp_path):
        tmp_store.save_meeting("abc-meet-123", SAMPLE_SUMMARY)
        files = list(tmp_path.glob("*.json"))
        assert len(files) == 1

    def test_file_contains_meeting_id(self, tmp_store, tmp_path):
        tmp_store.save_meeting("my-meeting", SAMPLE_SUMMARY)
        fpath = next(tmp_path.glob("*.json"))
        data = json.loads(fpath.read_text())
        assert data["meeting_id"] == "my-meeting"

    def test_file_contains_saved_at(self, tmp_store, tmp_path):
        tmp_store.save_meeting("my-meeting", SAMPLE_SUMMARY)
        fpath = next(tmp_path.glob("*.json"))
        data = json.loads(fpath.read_text())
        assert "saved_at" in data

    def test_original_dict_not_mutated(self, tmp_store):
        original = {"key": "value"}
        tmp_store.save_meeting("test", original)
        assert "meeting_id" not in original
        assert "saved_at" not in original

    def test_file_name_starts_with_safe_meeting_id(self, tmp_store, tmp_path):
        tmp_store.save_meeting("abc-defg-hij", SAMPLE_SUMMARY)
        files = list(tmp_path.glob("*.json"))
        assert len(files) == 1
        assert files[0].name.startswith("abc-defg-hij_")

    def test_special_chars_in_meeting_id_sanitised(self, tmp_store, tmp_path):
        tmp_store.save_meeting("abc/def:ghi", SAMPLE_SUMMARY)
        files = list(tmp_path.glob("*.json"))
        assert len(files) == 1
        # No slashes or colons in filename
        assert "/" not in files[0].name
        assert ":" not in files[0].name

    def test_returns_filepath_string(self, tmp_store):
        path = tmp_store.save_meeting("my-meeting", SAMPLE_SUMMARY)
        assert isinstance(path, str)
        assert os.path.isfile(path)


# ---------------------------------------------------------------------------
# get_previous_meetings
# ---------------------------------------------------------------------------

class TestGetPreviousMeetings:
    def test_empty_when_no_history(self, tmp_store):
        result = tmp_store.get_previous_meetings("no-such-meeting")
        assert result == []

    def test_returns_saved_meeting(self, tmp_store):
        tmp_store.save_meeting("test-meet", SAMPLE_SUMMARY)
        results = tmp_store.get_previous_meetings("test-meet")
        assert len(results) == 1
        assert results[0]["meeting_id"] == "test-meet"

    def test_chronological_order(self, tmp_store):
        """Older entries should come first."""
        for i in range(3):
            data = {"index": i}
            tmp_store.save_meeting("ordered-meet", data)
        results = tmp_store.get_previous_meetings("ordered-meet")
        assert len(results) == 3
        indices = [r["index"] for r in results]
        assert indices == sorted(indices)

    def test_limit_respected(self, tmp_store):
        for _ in range(10):
            tmp_store.save_meeting("big-series", SAMPLE_SUMMARY)
        results = tmp_store.get_previous_meetings("big-series", limit=3)
        assert len(results) == 3

    def test_different_meeting_ids_isolated(self, tmp_store):
        tmp_store.save_meeting("meeting-A", {"name": "A"})
        tmp_store.save_meeting("meeting-B", {"name": "B"})
        results_a = tmp_store.get_previous_meetings("meeting-A")
        assert len(results_a) == 1
        assert results_a[0]["name"] == "A"

    def test_returns_most_recent_when_limited(self, tmp_store):
        for i in range(5):
            tmp_store.save_meeting("series", {"seq": i})
        results = tmp_store.get_previous_meetings("series", limit=2)
        # Should be the last 2 (seq 3 and 4)
        seqs = [r["seq"] for r in results]
        assert seqs == [3, 4]


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_nonexistent_history_dir_handled_gracefully(self, tmp_path):
        """get_previous_meetings on a fresh (empty) store returns []."""
        store = HistoryStore(history_dir=str(tmp_path / "fresh"))
        result = store.get_previous_meetings("any-id")
        assert result == []

    def test_corrupted_json_file_skipped(self, tmp_store, tmp_path):
        """A corrupted JSON file should be skipped without crashing."""
        # Write a valid file first
        tmp_store.save_meeting("corrupt-test", SAMPLE_SUMMARY)
        # Write a corrupted file with the correct prefix
        bad_file = tmp_path / "corrupt-test_20260101T000000Z.json"
        bad_file.write_text("{not valid json")
        results = tmp_store.get_previous_meetings("corrupt-test")
        # Only the valid file should be returned
        assert len(results) == 1
