"""Persistent meeting history store for cross-meeting progress tracking.

Meetings are stored as JSON files under a configurable directory.
Files are named  <safe_meeting_id>_<UTC_timestamp>.json  so that all
previous sessions for the same meeting ID can be retrieved and compared.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Default location: a hidden folder next to the project root
_DEFAULT_HISTORY_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".meeting_history",
)


def _safe_id(meeting_id: str) -> str:
    """Convert an arbitrary meeting ID to a filesystem-safe prefix."""
    return re.sub(r"[^a-zA-Z0-9_-]", "_", meeting_id)[:80]


# Import re at module level (used by _safe_id)
import re


class HistoryStore:
    """Save and retrieve per-meeting JSON summaries from disk.

    Each file represents one completed meeting session.
    The store is keyed by *meeting_id*; all files whose name starts with
    ``safe(meeting_id)_`` are considered part of the same meeting series.
    """

    def __init__(self, history_dir: str = _DEFAULT_HISTORY_DIR) -> None:
        self.history_dir = history_dir
        os.makedirs(history_dir, exist_ok=True)
        logger.debug("HistoryStore initialised at %s", history_dir)

    # ------------------------------------------------------------------
    # Writing
    # ------------------------------------------------------------------

    def save_meeting(self, meeting_id: str, summary_data: dict) -> str:
        """Persist *summary_data* for *meeting_id*.

        Returns the full path of the saved file.
        summary_data is augmented with ``meeting_id`` and ``saved_at`` before
        writing so downstream readers always have that context.
        """
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
        filename = f"{_safe_id(meeting_id)}_{ts}.json"
        filepath = os.path.join(self.history_dir, filename)

        payload = dict(summary_data)  # shallow copy — do NOT mutate caller's dict
        payload.setdefault("meeting_id", meeting_id)
        payload.setdefault("saved_at", ts)

        try:
            with open(filepath, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, ensure_ascii=False)
            logger.info("Meeting history saved → %s", filepath)
        except OSError:
            logger.exception("Failed to save meeting history to %s", filepath)

        return filepath

    # ------------------------------------------------------------------
    # Reading
    # ------------------------------------------------------------------

    def get_previous_meetings(
        self, meeting_id: str, limit: int = 5
    ) -> list[dict]:
        """Return up to *limit* previous meeting summaries in chronological order.

        Only files whose name starts with ``safe(meeting_id)_`` are returned.
        An empty list is returned if no history exists.
        """
        prefix = _safe_id(meeting_id) + "_"
        matches: list[tuple[str, dict]] = []

        try:
            for fname in sorted(os.listdir(self.history_dir)):
                if fname.startswith(prefix) and fname.endswith(".json"):
                    fpath = os.path.join(self.history_dir, fname)
                    try:
                        with open(fpath, encoding="utf-8") as fh:
                            matches.append((fname, json.load(fh)))
                    except (OSError, json.JSONDecodeError):
                        logger.warning("Could not read history file %s", fpath)
        except OSError:
            logger.exception("Could not list history directory %s", self.history_dir)

        # Return most-recent `limit` entries (files are sorted alphabetically
        # which equals chronological because of the timestamp suffix)
        recent = matches[-limit:] if len(matches) > limit else matches
        return [data for _, data in recent]
