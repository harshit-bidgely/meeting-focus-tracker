"""Meeting memory backed by SQLite — single source of truth for queries.

The thread_store writes human-readable dirs; this module handles all queries.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "meetings.db")


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_id TEXT NOT NULL,
            date TEXT NOT NULL,
            agenda_raw TEXT NOT NULL,
            agenda_items TEXT NOT NULL DEFAULT '[]',
            final_summary TEXT NOT NULL DEFAULT '',
            decisions TEXT NOT NULL DEFAULT '[]',
            open_items TEXT NOT NULL DEFAULT '[]',
            deviation_count INTEGER DEFAULT 0,
            thread_id TEXT,
            summary_json TEXT DEFAULT '{}',
            transcript_path TEXT
        )
    """)
    conn.commit()
    return conn


class MeetingMemory:
    """SQLite-backed storage for past meeting summaries with fuzzy matching."""

    def __init__(self, storage_path: str = None) -> None:
        # storage_path kept for interface compat but ignored — we use DB_PATH
        self.conn = _get_conn()
        self._migrate_from_json(storage_path)

    def _migrate_from_json(self, json_path: str | None) -> None:
        """One-time migration: if old JSON file exists and DB is empty, import it."""
        if not json_path or not os.path.exists(json_path):
            return
        count = self.conn.execute("SELECT COUNT(*) FROM meetings").fetchone()[0]
        if count > 0:
            return
        try:
            with open(json_path) as f:
                data = json.load(f)
            for m in data.get("meetings", []):
                self._insert(m)
            logger.info("Migrated %d meetings from JSON to SQLite", len(data.get("meetings", [])))
        except Exception:
            logger.warning("Could not migrate old JSON meeting history")

    def _insert(self, record: dict) -> None:
        self.conn.execute(
            """INSERT INTO meetings
               (meeting_id, date, agenda_raw, agenda_items, final_summary,
                decisions, open_items, deviation_count, thread_id, summary_json, transcript_path)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record.get("meeting_id", ""),
                record.get("date", ""),
                record.get("agenda_raw", ""),
                json.dumps(record.get("agenda_items", [])),
                record.get("final_summary", ""),
                json.dumps(record.get("decisions", [])),
                json.dumps(record.get("open_items", [])),
                record.get("deviation_count", 0),
                record.get("thread_id"),
                json.dumps(record.get("summary_json", {})),
                record.get("transcript_path"),
            ),
        )
        self.conn.commit()

    @staticmethod
    def _normalize(text: str) -> str:
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
        thread_id: str = None,
        summary_json: dict = None,
        transcript_path: str = None,
    ) -> None:
        """Save a completed meeting."""
        self._insert({
            "meeting_id": meeting_id,
            "date": date,
            "agenda_raw": agenda_raw,
            "agenda_items": agenda_items,
            "final_summary": final_summary,
            "decisions": decisions,
            "open_items": open_items,
            "deviation_count": deviation_count,
            "thread_id": thread_id,
            "summary_json": summary_json or {},
            "transcript_path": transcript_path,
        })
        logger.info("Saved meeting %s to DB", meeting_id)

    def find_related_meetings(
        self,
        current_agenda_items: list[str],
        max_results: int = 3,
        threshold: float = 0.55,
    ) -> list[dict]:
        """Find past meetings with similar agenda topics using fuzzy matching."""
        if not current_agenda_items:
            return []

        rows = self.conn.execute("SELECT * FROM meetings ORDER BY date ASC").fetchall()
        current_normalized = [self._normalize(item) for item in current_agenda_items]
        scored = []

        for row in rows:
            past_items = [self._normalize(item) for item in json.loads(row["agenda_items"])]
            if not past_items:
                continue
            total_score = 0.0
            match_count = 0
            for curr in current_normalized:
                best_ratio = max(SequenceMatcher(None, curr, past).ratio() for past in past_items)
                if best_ratio >= threshold:
                    total_score += best_ratio
                    match_count += 1
            if match_count > 0:
                scored.append((total_score, _row_to_dict(row)))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored[:max_results]]

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

    # --- Query methods ---

    def get_all_meetings(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM meetings ORDER BY date ASC").fetchall()
        return [_row_to_dict(r) for r in rows]

    def get_meetings_by_thread(self, thread_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM meetings WHERE thread_id = ? ORDER BY date ASC", (thread_id,)
        ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def get_meeting_by_id(self, meeting_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM meetings WHERE meeting_id = ? ORDER BY date ASC", (meeting_id,)
        ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def search_decisions(self, keyword: str) -> list[dict]:
        """Search across all meetings for decisions containing keyword."""
        rows = self.conn.execute(
            "SELECT * FROM meetings WHERE decisions LIKE ? ORDER BY date ASC",
            (f"%{keyword}%",)
        ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def search_summaries(self, keyword: str) -> list[dict]:
        """Full-text search across summaries."""
        rows = self.conn.execute(
            "SELECT * FROM meetings WHERE final_summary LIKE ? OR agenda_raw LIKE ? ORDER BY date ASC",
            (f"%{keyword}%", f"%{keyword}%")
        ).fetchall()
        return [_row_to_dict(r) for r in rows]


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["agenda_items"] = json.loads(d["agenda_items"])
    d["decisions"] = json.loads(d["decisions"])
    d["open_items"] = json.loads(d["open_items"])
    d["summary_json"] = json.loads(d.get("summary_json") or "{}")
    return d
