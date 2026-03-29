from __future__ import annotations

import re
import logging

logger = logging.getLogger(__name__)


def _is_noise(text: str) -> bool:
    """Check if text is noise — all words are the same word repeated, or a single filler word."""
    words = re.findall(r"[a-zA-Z]+", text.lower())
    if not words:
        return True
    # Single word with no real content (e.g., "Dan," or "Hello.")
    if len(words) == 1:
        return True
    # Multiple words but all the same (e.g., "Dan, Dan, Dan")
    return len(set(words)) == 1


def _is_too_short(text: str) -> bool:
    """Check if text has fewer than 2 non-whitespace characters."""
    stripped = text.strip()
    return len(stripped) < 2


def clean_segments(
    segments: list[dict],
    after_timestamp: str | None = None,
) -> tuple[str, str | None]:
    """Clean raw Vexa transcript segments into formatted text.

    Processing:
    1. Filter segments after the given timestamp (only new ones).
    2. Skip segments with < 2 chars of text.
    3. Skip noise segments (all words are the same word repeated).
    4. Merge consecutive segments from the same speaker.
    5. Format as [Speaker]: text

    Returns:
        (cleaned_text, latest_timestamp_seen)
    """
    latest_timestamp: str | None = None

    # Step 1: filter by timestamp and collect valid segments
    filtered: list[dict] = []
    for seg in segments:
        ts = seg.get("absolute_start_time", "")
        text = seg.get("text", "")

        # Track latest timestamp across ALL segments (even filtered ones)
        if ts and (latest_timestamp is None or ts > latest_timestamp):
            latest_timestamp = ts

        # Filter by after_timestamp
        if after_timestamp and ts and ts <= after_timestamp:
            continue

        # Step 2: skip very short segments
        if _is_too_short(text):
            continue

        # Step 3: skip noise
        if _is_noise(text):
            continue

        speaker = seg.get("speaker") or "Unknown"
        filtered.append({"speaker": speaker, "text": text.strip()})

    if not filtered:
        return ("", latest_timestamp)

    # Step 4: merge consecutive same-speaker segments
    merged: list[dict] = [filtered[0]]
    for seg in filtered[1:]:
        if seg["speaker"] == merged[-1]["speaker"]:
            merged[-1]["text"] += " " + seg["text"]
        else:
            merged.append(seg)

    # Step 5: format output
    lines = [f"[{seg['speaker']}]: {seg['text']}" for seg in merged]
    return ("\n".join(lines), latest_timestamp)


def count_meaningful_words(text: str) -> int:
    """Count words in text, excluding [Speaker]: tags."""
    # Remove speaker tags like [Some Name]:
    cleaned = re.sub(r"\[.*?\]:", "", text)
    words = cleaned.split()
    return len(words)
