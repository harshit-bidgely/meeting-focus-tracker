from __future__ import annotations

import json
import logging
import os
import re
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class MeetingMemory:
    """Local JSON-based storage for past meeting summaries with fuzzy matching."""

    def __init__(self, storage_path: str) -> None:
        self.storage_path = storage_path
        self.data: dict = {"meetings": []}
        self._load()

    def _load(self) -> None:
        """Load meeting history from disk."""
        if not os.path.exists(self.storage_path):
            return
        try:
            with open(self.storage_path, "r") as f:
                self.data = json.load(f)
            logger.info("Loaded %d past meetings from memory", len(self.data.get("meetings", [])))
        except (json.JSONDecodeError, OSError):
            logger.warning("Corrupted memory file, starting fresh")
            self.data = {"meetings": []}

    def _save(self) -> None:
        """Write meeting history to disk."""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        with open(self.storage_path, "w") as f:
            json.dump(self.data, f, indent=2)

    @staticmethod
    def _normalize(text: str) -> str:
        """Lowercase, strip punctuation, collapse whitespace."""
        text = text.lower()
        text = re.sub(r"[^\w\s]", "", text)
        return re.sub(r"\s+", " ", text).strip()

    def save_meeting(
        self,
        meeting_id: str,
        date: str,
        agenda_raw: str,
        agenda_items: list[str],
        final_summary: str,
        decisions: list[str],
        open_items: list[str],
        deviation_count: int,
    ) -> None:
        """Append a completed meeting to local storage."""
        record = {
            "meeting_id": meeting_id,
            "date": date,
            "agenda_raw": agenda_raw,
            "agenda_items": agenda_items,
            "final_summary": final_summary,
            "decisions": decisions,
            "open_items": open_items,
            "deviation_count": deviation_count,
        }
        self.data["meetings"].append(record)
        self._save()
        logger.info("Saved meeting %s to memory (%d total)", meeting_id, len(self.data["meetings"]))

    def find_related_meetings(
        self,
        current_agenda_items: list[str],
        max_results: int = 3,
        threshold: float = 0.55,
    ) -> list[dict]:
        """Find past meetings with similar agenda topics using fuzzy matching.

        Returns top matches sorted by relevance score.
        """
        if not current_agenda_items or not self.data["meetings"]:
            return []

        current_normalized = [self._normalize(item) for item in current_agenda_items]
        scored: list[tuple[float, dict]] = []

        for meeting in self.data["meetings"]:
            past_items = [self._normalize(item) for item in meeting.get("agenda_items", [])]
            if not past_items:
                continue

            # Score: sum of best match ratios for each current item
            total_score = 0.0
            match_count = 0
            for curr in current_normalized:
                best_ratio = max(
                    SequenceMatcher(None, curr, past).ratio()
                    for past in past_items
                )
                if best_ratio >= threshold:
                    total_score += best_ratio
                    match_count += 1

            if match_count > 0:
                scored.append((total_score, meeting))

        # Sort by score descending, return top N
        scored.sort(key=lambda x: x[0], reverse=True)
        return [meeting for _, meeting in scored[:max_results]]

    def build_context_summary(self, related_meetings: list[dict]) -> str:
        """Format related past meetings into a text block for LLM injection."""
        if not related_meetings:
            return ""

        lines = []
        for m in related_meetings:
            date = m.get("date", "Unknown date")[:10]
            summary = m.get("final_summary", "No summary available")
            decisions = m.get("decisions", [])
            open_items = m.get("open_items", [])

            lines.append(f"[{date}] Previous meeting:")
            lines.append(f"  Summary: {summary[:300]}")
            if decisions:
                lines.append(f"  Decisions: {'; '.join(decisions[:5])}")
            if open_items:
                lines.append(f"  Open items: {'; '.join(open_items[:5])}")
            lines.append("")

        return "\n".join(lines)
