"""Unit tests for services/participant_tracker.py."""

import pytest

from services.participant_tracker import ParticipantTracker, ParticipantStats


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_tracker_with_two_speakers() -> ParticipantTracker:
    """Returns a tracker with Alice (high) and Bob (low) contributions."""
    pt = ParticipantTracker()
    # Alice speaks 60 words (across 3 segments)
    for i in range(3):
        pt.record_segment("Alice", "one two three four five six seven eight nine ten", "2026-03-29T10:00:0%dZ" % i)
    # Bob speaks 5 words (1 segment) — clearly below 0.5× expected share
    pt.record_segment("Bob", "hello world bob yes okay", "2026-03-29T10:00:10Z")
    return pt


# ---------------------------------------------------------------------------
# record_segment
# ---------------------------------------------------------------------------

class TestRecordSegment:
    def test_word_count_accumulates(self):
        pt = ParticipantTracker()
        pt.record_segment("Alice", "hello world")
        pt.record_segment("Alice", "how are you")
        assert pt._stats["Alice"].word_count == 5

    def test_segment_count_accumulates(self):
        pt = ParticipantTracker()
        pt.record_segment("Alice", "hello world")
        pt.record_segment("Alice", "bye world")
        assert pt._stats["Alice"].segment_count == 2

    def test_none_speaker_becomes_unknown(self):
        pt = ParticipantTracker()
        pt.record_segment(None, "some text")
        assert "Unknown" in pt._stats

    def test_empty_speaker_becomes_unknown(self):
        pt = ParticipantTracker()
        pt.record_segment("", "some text")
        assert "Unknown" in pt._stats

    def test_first_seen_set_on_first_call(self):
        pt = ParticipantTracker()
        pt.record_segment("Alice", "hi", timestamp="2026-01-01T10:00:00Z")
        assert pt._stats["Alice"].first_seen == "2026-01-01T10:00:00Z"

    def test_last_seen_updates_to_latest_timestamp(self):
        pt = ParticipantTracker()
        pt.record_segment("Alice", "hi", timestamp="2026-01-01T10:00:00Z")
        pt.record_segment("Alice", "bye", timestamp="2026-01-01T10:05:00Z")
        pt.record_segment("Alice", "mid", timestamp="2026-01-01T10:02:00Z")  # older
        assert pt._stats["Alice"].last_seen == "2026-01-01T10:05:00Z"

    def test_first_seen_not_overwritten(self):
        pt = ParticipantTracker()
        pt.record_segment("Alice", "first", timestamp="2026-01-01T09:00:00Z")
        pt.record_segment("Alice", "second", timestamp="2026-01-01T10:00:00Z")
        assert pt._stats["Alice"].first_seen == "2026-01-01T09:00:00Z"

    def test_punctuation_not_counted_as_words(self):
        pt = ParticipantTracker()
        pt.record_segment("Alice", "Hello, world! How are you?")
        # "Hello", "world", "How", "are", "you" → 5 words
        assert pt._stats["Alice"].word_count == 5

    def test_multiple_speakers_tracked_independently(self):
        pt = ParticipantTracker()
        pt.record_segment("Alice", "one two three")
        pt.record_segment("Bob", "four five")
        assert pt._stats["Alice"].word_count == 3
        assert pt._stats["Bob"].word_count == 2


# ---------------------------------------------------------------------------
# get_participation_level
# ---------------------------------------------------------------------------

class TestGetParticipationLevel:
    def test_high_participation(self):
        pt = _make_tracker_with_two_speakers()
        # Alice=30 words, total=35 → share ≈86% vs expected 50% → 86/50 ≈ 1.7× > 1.5× → High
        assert pt.get_participation_level("Alice") == "High"

    def test_low_participation(self):
        pt = _make_tracker_with_two_speakers()
        # Alice=30 words, Bob=5 words, total=35 → Bob share ≈14% vs expected 50%
        # 14/50 ≈ 0.28× < 0.5× → Low
        assert pt.get_participation_level("Bob") == "Low"

    def test_medium_participation(self):
        pt = ParticipantTracker()
        # Three participants, roughly equal
        pt.record_segment("Alice", " ".join(["word"] * 40))
        pt.record_segment("Bob", " ".join(["word"] * 30))
        pt.record_segment("Carol", " ".join(["word"] * 30))
        # Alice: 40/100 = 40%, expected 33% → 40/33 ≈ 1.2× < 1.5× → Medium
        assert pt.get_participation_level("Alice") == "Medium"

    def test_unknown_speaker_returns_low(self):
        pt = ParticipantTracker()
        assert pt.get_participation_level("Nobody") == "Low"

    def test_zero_total_words_returns_low(self):
        pt = ParticipantTracker()
        pt._stats["Alice"] = ParticipantStats(name="Alice", word_count=0)
        assert pt.get_participation_level("Alice") == "Low"


# ---------------------------------------------------------------------------
# get_all_stats
# ---------------------------------------------------------------------------

class TestGetAllStats:
    def test_sorted_by_word_count_desc(self):
        pt = _make_tracker_with_two_speakers()
        stats = pt.get_all_stats()
        assert stats[0].name == "Alice"
        assert stats[1].name == "Bob"

    def test_empty_tracker_returns_empty_list(self):
        pt = ParticipantTracker()
        assert pt.get_all_stats() == []


# ---------------------------------------------------------------------------
# get_total_words
# ---------------------------------------------------------------------------

class TestGetTotalWords:
    def test_total_words_summed(self):
        pt = ParticipantTracker()
        pt.record_segment("Alice", "one two three")
        pt.record_segment("Bob", "four five")
        assert pt.get_total_words() == 5

    def test_empty_tracker_returns_zero(self):
        assert ParticipantTracker().get_total_words() == 0


# ---------------------------------------------------------------------------
# get_participant_names
# ---------------------------------------------------------------------------

class TestGetParticipantNames:
    def test_names_ordered_by_word_count(self):
        pt = _make_tracker_with_two_speakers()
        names = pt.get_participant_names()
        assert names[0] == "Alice"
        assert names[1] == "Bob"


# ---------------------------------------------------------------------------
# to_dict
# ---------------------------------------------------------------------------

class TestToDict:
    def test_contains_expected_keys(self):
        pt = ParticipantTracker()
        pt.record_segment("Alice", "hello world", "2026-01-01T10:00:00Z")
        result = pt.to_dict()
        assert "Alice" in result
        entry = result["Alice"]
        for key in ("name", "word_count", "segment_count", "word_share_pct",
                    "participation_level", "first_seen", "last_seen"):
            assert key in entry, f"Missing key: {key}"

    def test_word_share_pct_sums_to_100(self):
        pt = ParticipantTracker()
        pt.record_segment("Alice", " ".join(["a"] * 60))
        pt.record_segment("Bob", " ".join(["b"] * 40))
        d = pt.to_dict()
        total_share = round(d["Alice"]["word_share_pct"] + d["Bob"]["word_share_pct"], 1)
        assert total_share == 100.0

    def test_name_preserved_exactly(self):
        pt = ParticipantTracker()
        pt.record_segment("Kaustubh Sharma", "hello world")
        d = pt.to_dict()
        assert "Kaustubh Sharma" in d
        assert d["Kaustubh Sharma"]["name"] == "Kaustubh Sharma"
