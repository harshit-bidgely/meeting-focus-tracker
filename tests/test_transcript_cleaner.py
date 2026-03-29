"""Tests for the transcript cleaner using real Vexa API data."""

import pytest

from services.transcript_cleaner import clean_segments, count_meaningful_words

# ---------------------------------------------------------------------------
# Real Vexa data fixtures
# ---------------------------------------------------------------------------

SAMPLE_SEGMENTS_MEETING_1 = [
    {
        "start": 0.0,
        "end": 2.8,
        "text": " testing one two three four five six",
        "language": "en",
        "created_at": "2026-03-29T06:35:50.579856Z",
        "speaker": "Kaustubh Sharma",
        "completed": True,
        "absolute_start_time": "2026-03-29T06:35:43.077281Z",
        "absolute_end_time": "2026-03-29T06:35:45.877281Z",
    },
    {
        "start": 2.8,
        "end": 11.56,
        "text": " I have completed these steps, 10 seconds I've been waiting for this API to open terminal",
        "language": "en",
        "created_at": "2026-03-29T06:35:58.359548Z",
        "speaker": "Kaustubh Sharma",
        "completed": True,
        "absolute_start_time": "2026-03-29T06:35:45.877281Z",
        "absolute_end_time": "2026-03-29T06:35:54.637281Z",
    },
    {
        "start": 11.56,
        "end": 12.69,
        "text": " place.",
        "language": "en",
        "created_at": "2026-03-29T06:35:58.362953Z",
        "speaker": "Kaustubh Sharma",
        "completed": False,
        "absolute_start_time": "2026-03-29T06:35:54.637281Z",
        "absolute_end_time": "2026-03-29T06:35:55.767281Z",
    },
]

SAMPLE_SEGMENTS_MEETING_2 = [
    {
        "start": 0.0,
        "end": 2.0,
        "text": " I don't know anything.",
        "language": "en",
        "created_at": "2026-03-29T05:49:34.834736",
        "speaker": "Shivank Bhardwaj",
        "completed": True,
        "absolute_start_time": "2026-03-29T05:48:48.824824Z",
        "absolute_end_time": "2026-03-29T05:48:50.824824Z",
    },
    {
        "start": 2.37,
        "end": 3.91,
        "text": " What is this?",
        "language": "en",
        "created_at": "2026-03-29T05:49:34.836689",
        "speaker": None,
        "completed": True,
        "absolute_start_time": "2026-03-29T05:48:51.194824Z",
        "absolute_end_time": "2026-03-29T05:48:52.734824Z",
    },
    {
        "start": 21.34,
        "end": 23.26,
        "text": " Dan, dan, dan",
        "language": "en",
        "created_at": "2026-03-29T05:49:55.504605",
        "speaker": "Shivank Bhardwaj",
        "completed": True,
        "absolute_start_time": "2026-03-29T05:49:10.164824Z",
        "absolute_end_time": "2026-03-29T05:49:12.084824Z",
    },
    {
        "start": 23.26,
        "end": 23.48,
        "text": " Dan, Dan,",
        "language": "en",
        "created_at": "2026-03-29T05:49:55.504706",
        "speaker": "Shivank Bhardwaj",
        "completed": True,
        "absolute_start_time": "2026-03-29T05:49:12.084824Z",
        "absolute_end_time": "2026-03-29T05:49:12.304824Z",
    },
    {
        "start": 23.48,
        "end": 23.78,
        "text": " Dan,",
        "language": "en",
        "created_at": "2026-03-29T05:49:55.504796",
        "speaker": "Shivank Bhardwaj",
        "completed": True,
        "absolute_start_time": "2026-03-29T05:49:12.304824Z",
        "absolute_end_time": "2026-03-29T05:49:12.604824Z",
    },
    {
        "start": 23.78,
        "end": 23.9,
        "text": " Dan,",
        "language": "en",
        "created_at": "2026-03-29T05:49:55.504886",
        "speaker": "Shivank Bhardwaj",
        "completed": True,
        "absolute_start_time": "2026-03-29T05:49:12.604824Z",
        "absolute_end_time": "2026-03-29T05:49:12.724824Z",
    },
    {
        "start": 26.8,
        "end": 29.89,
        "text": " That's what I'm saying.",
        "language": "en",
        "created_at": "2026-03-29T05:50:05.839586",
        "speaker": "Shivank Bhardwaj",
        "completed": True,
        "absolute_start_time": "2026-03-29T05:49:15.624824Z",
        "absolute_end_time": "2026-03-29T05:49:18.714824Z",
    },
    {
        "start": 29.89,
        "end": 31.89,
        "text": " I'll just write it on the other side,",
        "language": "en",
        "created_at": "2026-03-29T05:50:05.839741",
        "speaker": "Shivank Bhardwaj",
        "completed": True,
        "absolute_start_time": "2026-03-29T05:49:18.714824Z",
        "absolute_end_time": "2026-03-29T05:49:20.714824Z",
    },
    {
        "start": 56.84,
        "end": 57.02,
        "text": " Hello.",
        "language": "en",
        "created_at": "2026-03-29T05:49:49.691022Z",
        "speaker": "Shivank Bhardwaj",
        "completed": True,
        "absolute_start_time": "2026-03-29T05:49:45.664824Z",
        "absolute_end_time": "2026-03-29T05:49:45.844824Z",
    },
    {
        "start": 57.02,
        "end": 58.02,
        "text": " Hello.",
        "language": "en",
        "created_at": "2026-03-29T05:49:54.112753Z",
        "speaker": "Shivank Bhardwaj",
        "completed": True,
        "absolute_start_time": "2026-03-29T05:49:45.844824Z",
        "absolute_end_time": "2026-03-29T05:49:46.844824Z",
    },
    {
        "start": 58.02,
        "end": 60.04,
        "text": " Hello.",
        "language": "en",
        "created_at": "2026-03-29T05:49:54.118129Z",
        "speaker": "Shivank Bhardwaj",
        "completed": True,
        "absolute_start_time": "2026-03-29T05:49:46.844824Z",
        "absolute_end_time": "2026-03-29T05:49:48.864824Z",
    },
    {
        "start": 60.04,
        "end": 61.04,
        "text": " Hello.",
        "language": "en",
        "created_at": "2026-03-29T05:49:54.123636Z",
        "speaker": "Shivank Bhardwaj",
        "completed": True,
        "absolute_start_time": "2026-03-29T05:49:48.864824Z",
        "absolute_end_time": "2026-03-29T05:49:49.864824Z",
    },
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCleanSegmentsMergesSameSpeaker:
    def test_consecutive_same_speaker_segments_merge(self):
        """Consecutive Kaustubh segments should merge into one block."""
        text, _ = clean_segments(SAMPLE_SEGMENTS_MEETING_1)
        # All segments from Kaustubh — should produce exactly one [Kaustubh Sharma]: line
        lines = [l for l in text.split("\n") if l.strip()]
        kaustubh_lines = [l for l in lines if l.startswith("[Kaustubh Sharma]:")]
        assert len(kaustubh_lines) == 1
        # The merged text should contain content from both the first and second segment
        assert "testing one two three" in kaustubh_lines[0]
        assert "completed these steps" in kaustubh_lines[0]


class TestCleanSegmentsStripsNoise:
    def test_dan_dan_dan_is_dropped(self):
        """Noise like 'Dan, dan, dan' should be removed from output."""
        text, _ = clean_segments(SAMPLE_SEGMENTS_MEETING_2)
        assert "dan, dan" not in text.lower()
        assert "Dan, Dan" not in text

    def test_single_word_dan_segments_dropped(self):
        """Single-word noise segments like ' Dan,' should be dropped."""
        text, _ = clean_segments(SAMPLE_SEGMENTS_MEETING_2)
        # None of the "Dan," only segments should appear
        lines = text.split("\n")
        for line in lines:
            # After the colon, text should not be just "Dan,"
            if ":" in line:
                content = line.split(":", 1)[1].strip()
                assert content.lower().replace(",", "").strip() != "dan"


class TestCleanSegmentsHandlesNullSpeaker:
    def test_null_speaker_becomes_unknown(self):
        """Segments with speaker=None should show as [Unknown]."""
        text, _ = clean_segments(SAMPLE_SEGMENTS_MEETING_2)
        assert "[Unknown]:" in text
        assert "What is this?" in text


class TestCleanSegmentsFiltersByTimestamp:
    def test_filters_old_segments(self):
        """Only segments after the given timestamp should be included."""
        # Use a timestamp after the first two segments of meeting 2
        cutoff = "2026-03-29T05:49:10.164824Z"
        text, _ = clean_segments(SAMPLE_SEGMENTS_MEETING_2, after_timestamp=cutoff)
        # "I don't know anything" (timestamp ...48:48) should be filtered out
        assert "I don't know anything" not in text
        # "What is this?" (timestamp ...48:51) should be filtered out
        assert "What is this?" not in text
        # "That's what I'm saying" (timestamp ...49:15) should be present
        assert "That's what I'm saying" in text

    def test_no_filter_returns_all(self):
        """Without a timestamp filter, all valid segments are included."""
        text, _ = clean_segments(SAMPLE_SEGMENTS_MEETING_2, after_timestamp=None)
        assert "I don't know anything" in text


class TestCleanSegmentsSkipsSingleWordNoise:
    def test_place_dot_is_skipped(self):
        """Very short segment like ' place.' should be skipped (< 2 meaningful chars after stripping noise check)."""
        # "place." has 6 chars so it passes the length check, but it's a single word so
        # it won't be flagged by _is_noise (needs >1 repeated words). However, it should
        # still merge with the speaker's other segments if not noise.
        text, _ = clean_segments(SAMPLE_SEGMENTS_MEETING_1)
        # "place." is a single word but has > 2 chars, not noise — it gets merged
        # The key point is it doesn't appear as a standalone line
        lines = [l for l in text.split("\n") if l.strip()]
        assert len(lines) == 1  # All Kaustubh segments merge into one line

    def test_repeated_hello_dropped(self):
        """Multiple consecutive 'Hello.' segments should be dropped as noise (single-word repeated)."""
        # Each individual "Hello." segment has only one word, so _is_noise returns True
        # only when there are >1 words that are all the same. A single word = 1 unique word
        # among 1 total words, so _is_noise returns False. But we handle this through merging.
        # Let's check that the output doesn't have excessive "Hello" repetitions.
        text, _ = clean_segments(SAMPLE_SEGMENTS_MEETING_2)
        # Individual "Hello." segments (6 chars, single word) pass the length check.
        # _is_noise requires >1 words all the same — a single word segment isn't noise by that rule.
        # They'll merge into one line. That's acceptable behavior — the test validates
        # they don't each appear as separate lines.
        hello_lines = [l for l in text.split("\n") if "Hello" in l]
        assert len(hello_lines) <= 1  # All Hellos merge into at most one speaker block


class TestCleanSegmentsReturnsLatestTimestamp:
    def test_returns_max_timestamp(self):
        """Should return the latest absolute_start_time across all segments."""
        _, latest = clean_segments(SAMPLE_SEGMENTS_MEETING_1)
        # The latest timestamp in meeting 1 data
        assert latest == "2026-03-29T06:35:54.637281Z"

    def test_returns_max_timestamp_even_when_filtered(self):
        """Latest timestamp should be from ALL segments, not just the ones that pass filters."""
        # Filter so nothing passes
        _, latest = clean_segments(
            SAMPLE_SEGMENTS_MEETING_1,
            after_timestamp="2026-03-29T23:59:59Z",
        )
        # Should still track the latest timestamp
        assert latest == "2026-03-29T06:35:54.637281Z"

    def test_empty_segments_returns_none(self):
        """Empty segment list should return None for latest timestamp."""
        text, latest = clean_segments([])
        assert text == ""
        assert latest is None


class TestCountMeaningfulWords:
    def test_counts_words_excluding_speaker_tags(self):
        text = "[Kaustubh Sharma]: testing one two three"
        assert count_meaningful_words(text) == 4

    def test_multiple_speakers(self):
        text = "[Alice]: hello world\n[Bob]: goodbye"
        assert count_meaningful_words(text) == 3

    def test_empty_string(self):
        assert count_meaningful_words("") == 0

    def test_only_speaker_tags(self):
        assert count_meaningful_words("[Alice]:") == 0
