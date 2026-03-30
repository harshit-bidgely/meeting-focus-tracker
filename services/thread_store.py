"""Structured local storage: meetings grouped into threads by agenda.

Directory layout:
    meeting_data/threads/{thread_slug}/{date_HHMMSS}/summary.json
    meeting_data/threads/{thread_slug}/{date_HHMMSS}/transcript.txt
    meeting_data/threads/{thread_slug}/thread.json   ← index
"""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "meeting_data", "threads")


def _slugify(text: str, max_len: int = 50) -> str:
    """Turn agenda text into a filesystem-safe slug."""
    text = text.lower().split("\n")[0]  # first line only
    text = re.sub(r"^\d+\.\s*", "", text)  # strip leading number
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:max_len].rstrip("-")


def _load_thread(thread_dir: str) -> dict:
    path = os.path.join(thread_dir, "thread.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def _save_thread(thread_dir: str, data: dict) -> None:
    os.makedirs(thread_dir, exist_ok=True)
    path = os.path.join(thread_dir, "thread.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _agenda_similarity(a: str, b: str) -> float:
    """Compare two agenda strings using SequenceMatcher."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def find_matching_thread(agenda: str, threshold: float = 0.5) -> str | None:
    """Find an existing thread directory whose agenda matches. Returns thread_dir or None."""
    if not os.path.exists(BASE_DIR):
        return None
    best_score = 0.0
    best_dir = None
    for name in os.listdir(BASE_DIR):
        thread_dir = os.path.join(BASE_DIR, name)
        if not os.path.isdir(thread_dir):
            continue
        meta = _load_thread(thread_dir)
        if not meta:
            continue
        score = _agenda_similarity(agenda, meta.get("agenda", ""))
        if score > best_score:
            best_score = score
            best_dir = thread_dir
    if best_score >= threshold:
        return best_dir
    return None


def save_meeting_to_thread(
    meeting_id: str,
    agenda: str,
    agenda_items: list[str],
    summary: dict,
    transcript: str,
    rolling_summary: str,
) -> str:
    """Save a meeting into its thread. Creates thread if none exists.

    Returns the path to the meeting directory.
    """
    # Find or create thread
    thread_dir = find_matching_thread(agenda)
    if thread_dir:
        meta = _load_thread(thread_dir)
        logger.info("Adding to existing thread: %s", os.path.basename(thread_dir))
    else:
        slug = _slugify(agenda) or f"meeting-{meeting_id}"
        thread_dir = os.path.join(BASE_DIR, slug)
        meta = {
            "thread_id": slug,
            "agenda": agenda,
            "agenda_items": agenda_items,
            "created_at": datetime.now().isoformat(),
            "meetings": [],
        }
        logger.info("Creating new thread: %s", slug)

    # Create meeting subdirectory
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    meeting_dir = os.path.join(thread_dir, ts)
    os.makedirs(meeting_dir, exist_ok=True)

    # Save summary
    summary_path = os.path.join(meeting_dir, "summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    # Save transcript
    transcript_path = os.path.join(meeting_dir, "transcript.txt")
    with open(transcript_path, "w") as f:
        f.write(transcript if transcript.strip() else "(no transcript captured)")

    # Update thread index
    meeting_entry = {
        "date": datetime.now().isoformat(),
        "meeting_id": meeting_id,
        "folder": ts,
        "summary_file": "summary.json",
        "transcript_file": "transcript.txt",
        "title": summary.get("title", rolling_summary[:80] if rolling_summary else "Untitled"),
        "focus_score": summary.get("focus_score", None),
        "decisions": summary.get("decisions", []),
    }
    meta["meetings"].append(meeting_entry)
    meta["last_updated"] = datetime.now().isoformat()
    meta["meeting_count"] = len(meta["meetings"])
    _save_thread(thread_dir, meta)

    logger.info("Meeting saved to %s", meeting_dir)
    return meeting_dir


def get_thread_meetings(thread_dir: str) -> list[dict]:
    """Load all meetings from a thread for analysis."""
    meta = _load_thread(thread_dir)
    if not meta:
        return []
    return meta.get("meetings", [])


def get_all_threads() -> list[dict]:
    """Return metadata for all threads."""
    if not os.path.exists(BASE_DIR):
        return []
    threads = []
    for name in sorted(os.listdir(BASE_DIR)):
        thread_dir = os.path.join(BASE_DIR, name)
        meta = _load_thread(thread_dir)
        if meta:
            meta["_dir"] = thread_dir
            threads.append(meta)
    return threads
