"""Participant-level contribution tracking across transcript cycles."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ParticipantStats:
    """Accumulated stats for a single meeting participant."""

    name: str
    word_count: int = 0
    segment_count: int = 0
    first_seen: str | None = None
    last_seen: str | None = None


class ParticipantTracker:
    """Tracks speaking contributions per participant throughout a meeting.

    Records are built from raw Vexa segments (before noise filtering) so that
    even short/filtered segments count toward presence detection.
    """

    def __init__(self) -> None:
        self._stats: dict[str, ParticipantStats] = {}

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_segment(
        self,
        speaker: str,
        text: str,
        timestamp: str | None = None,
    ) -> None:
        """Accumulate a single transcript segment for *speaker*.

        speaker   : normalised speaker name (caller should substitute None → "Unknown")
        text      : raw segment text (speaker tags not present here)
        timestamp : absolute_start_time string from Vexa, used for first/last seen
        """
        speaker = speaker.strip() if speaker else "Unknown"
        if speaker not in self._stats:
            self._stats[speaker] = ParticipantStats(name=speaker)

        stats = self._stats[speaker]

        # Count meaningful words (real words only, ignore punctuation tokens)
        words = re.findall(r"[a-zA-Z0-9']+", text)
        stats.word_count += len(words)
        stats.segment_count += 1

        if timestamp:
            if stats.first_seen is None:
                stats.first_seen = timestamp
            # Keep the latest timestamp seen for this participant
            if stats.last_seen is None or timestamp > stats.last_seen:
                stats.last_seen = timestamp

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def get_all_stats(self) -> list[ParticipantStats]:
        """Return stats for all tracked participants, sorted by word_count desc."""
        return sorted(self._stats.values(), key=lambda s: s.word_count, reverse=True)

    def get_participation_level(self, speaker: str) -> str:
        """Return 'High' / 'Medium' / 'Low' relative to the group average.

        Thresholds (based on speaker's share of total words):
          High   : ≥ 1.5× expected share
          Medium : ≥ 0.5× expected share
          Low    : < 0.5× expected share
        """
        if speaker not in self._stats:
            return "Low"

        total_words = sum(s.word_count for s in self._stats.values())
        if total_words == 0:
            return "Low"

        n = len(self._stats)
        expected_share = 1.0 / n if n > 0 else 1.0
        speaker_share = self._stats[speaker].word_count / total_words

        if speaker_share >= expected_share * 1.5:
            return "High"
        if speaker_share >= expected_share * 0.5:
            return "Medium"
        return "Low"

    def get_total_words(self) -> int:
        """Total spoken words across all participants."""
        return sum(s.word_count for s in self._stats.values())

    def get_participant_names(self) -> list[str]:
        """Ordered list of participant names (highest word count first)."""
        return [s.name for s in self.get_all_stats()]

    def to_dict(self) -> dict[str, dict]:
        """Serialise to a plain dict suitable for JSON storage or LLM context."""
        total = self.get_total_words()
        result: dict[str, dict] = {}
        for name, stats in self._stats.items():
            share = round(stats.word_count / total * 100, 1) if total else 0.0
            result[name] = {
                "name": stats.name,
                "word_count": stats.word_count,
                "segment_count": stats.segment_count,
                "word_share_pct": share,
                "participation_level": self.get_participation_level(name),
                "first_seen": stats.first_seen,
                "last_seen": stats.last_seen,
            }
        return result
