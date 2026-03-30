"""Lightweight text similarity — no external deps, pure Python cosine."""
from __future__ import annotations

import math
import re
from collections import Counter

_STOPWORDS = frozenset(
    "the a an is was were be been being have has had do does did will would shall "
    "should can could may might must and or but if then else when where how what "
    "which who whom this that these those it its in on at to for of with by from "
    "as not no nor so yet also very".split()
)


def _tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w for w in words if w not in _STOPWORDS and len(w) > 1]


def cosine_similarity(vec_a: Counter, vec_b: Counter) -> float:
    if not vec_a or not vec_b:
        return 0.0
    keys = set(vec_a) | set(vec_b)
    dot = sum(vec_a.get(k, 0) * vec_b.get(k, 0) for k in keys)
    mag_a = math.sqrt(sum(v * v for v in vec_a.values()))
    mag_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def text_similarity(text_a: str, text_b: str) -> float:
    return cosine_similarity(Counter(_tokenize(text_a)), Counter(_tokenize(text_b)))


def generate_thread_insight(meetings: list[dict]) -> dict:
    """Analyze a series of meetings on the same topic thread."""
    if len(meetings) < 2:
        return {"total_meetings": len(meetings), "repetition_pct": 0, "insight": "Not enough meetings to analyze."}

    pair_scores = []
    all_decisions = set()
    topic_counts: Counter = Counter()

    for m in meetings:
        for item in m.get("agenda_items", []):
            topic_counts[item] += 1
        for d in m.get("decisions", []):
            all_decisions.add(d)

    for i in range(1, len(meetings)):
        prev = meetings[i - 1].get("final_summary", "")
        curr = meetings[i].get("final_summary", "")
        pair_scores.append(text_similarity(prev, curr))

    avg = sum(pair_scores) / len(pair_scores) if pair_scores else 0.0
    repeated = [t for t, c in topic_counts.items() if c > 1]
    pct = round(avg * 100)

    if avg >= 0.7:
        insight = f"HIGH repetition ({pct}%) across {len(meetings)} meetings. Same topics without resolution."
    elif avg >= 0.4:
        insight = f"Moderate continuity ({pct}% overlap). {len(all_decisions)} decisions made across {len(meetings)} meetings."
    else:
        insight = f"Healthy progression ({pct}% overlap). Each meeting covers new ground."

    return {
        "total_meetings": len(meetings),
        "repetition_pct": pct,
        "repeated_topics": repeated,
        "total_decisions": len(all_decisions),
        "consecutive_scores": [round(s, 3) for s in pair_scores],
        "insight": insight,
    }
