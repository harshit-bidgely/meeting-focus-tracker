"""Meeting efficiency metrics computation.

Computes:
- Agenda adherence score (% of meeting on-track vs off-topic)
- Redundancy score (% of discussion that repeats past meetings)
- Decision rate (decisions per hour of meeting)
- Overall efficiency rating (0-100, with qualitative assessment)
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class MeetingMetrics:
    """Computes efficiency metrics for completed meetings."""

    @staticmethod
    def compute_adherence_score(
        deviation_count: float,
        total_cycles: int,
    ) -> float:
        """Compute agenda adherence score (0-100).

        Score based on how few off-topic deviations occurred.
        - deviation_count: cumulative deviations (each off-topic adds 1, tangential adds 0.5)
        - total_cycles: number of analysis cycles performed

        Returns: 0-100 (100 = perfect adherence, 0 = completely off-track)
        """
        if total_cycles == 0:
            return 50.0  # neutral if no data

        # More deviations = lower score
        # Max deviations before score hits 0: total_cycles * 2
        max_expected_deviations = total_cycles * 2.0
        if deviation_count >= max_expected_deviations:
            return 0.0

        score = (1.0 - (deviation_count / max_expected_deviations)) * 100.0
        return max(0.0, min(100.0, score))

    @staticmethod
    def compute_redundancy_score(
        repetition_detected: bool,
        repetition_count: int = 0,
        total_topics_discussed: int = 0,
    ) -> float:
        """Compute redundancy score (0-100).

        Measures how much of the meeting repeats past discussions.
        - repetition_detected: flag from LLM analysis
        - repetition_count: number of repeated topics
        - total_topics_discussed: total number of distinct topics

        Returns: 0-100 (0 = all new content, 100 = completely repetitive)
        """
        if total_topics_discussed == 0:
            return 50.0 if repetition_detected else 0.0

        # Calculate % of repeated topics
        if repetition_count == 0:
            redundancy_pct = 0.0
        else:
            redundancy_pct = (repetition_count / total_topics_discussed) * 100.0

        return min(100.0, redundancy_pct)

    @staticmethod
    def compute_decision_rate(
        decisions: list[str],
        meeting_duration_minutes: float,
    ) -> float:
        """Compute decision rate (decisions per hour).

        Returns: float representing decisions/hour
        """
        if meeting_duration_minutes == 0:
            return 0.0

        hours = meeting_duration_minutes / 60.0
        if hours == 0:
            return 0.0

        return len(decisions) / hours

    @staticmethod
    def compute_overall_efficiency(
        adherence_score: float,
        redundancy_score: float,
        decision_rate: float,
        max_expected_rate: float = 5.0,
    ) -> dict:
        """Compute overall efficiency score and rating.

        Combines adherence, redundancy, and decision rate into a single score.

        Returns dict with:
        {
            "score": 0-100,
            "rating": "excellent|good|fair|poor",
            "breakdown": {
                "adherence": float,
                "novelty": float,  (100 - redundancy)
                "productivity": float
            }
        }
        """
        # Normalize redundancy to novelty (100 - redundancy)
        novelty_score = 100.0 - redundancy_score

        # Normalize decision rate to 0-100
        # Max expected rate is 5 decisions/hour
        productivity_score = min(100.0, (decision_rate / max_expected_rate) * 100.0)

        # Weight the components
        # Adherence: 50% (staying on track is critical)
        # Novelty: 30% (new content is important)
        # Productivity: 20% (some meetings have fewer decisions)
        overall = (
            (adherence_score * 0.50) +
            (novelty_score * 0.30) +
            (productivity_score * 0.20)
        )

        # Clamp overall score to 0-100
        overall = max(0.0, min(100.0, overall))

        # Map to qualitative rating
        if overall >= 80:
            rating = "excellent"
        elif overall >= 60:
            rating = "good"
        elif overall >= 40:
            rating = "fair"
        else:
            rating = "poor"

        return {
            "score": round(overall, 1),
            "rating": rating,
            "breakdown": {
                "adherence": round(adherence_score, 1),
                "novelty": round(novelty_score, 1),
                "productivity": round(productivity_score, 1),
            },
        }

    @staticmethod
    def build_metrics_report(
        adherence_score: float,
        redundancy_score: float,
        decision_rate: float,
        overall: dict,
        decisions: list[str],
        open_items: list[str],
    ) -> str:
        """Build a human-readable metrics report."""
        report_lines = [
            "\nMEETING EFFICIENCY REPORT",
            "=" * 50,
            "",
            f"Overall Score: {overall['score']}/100 ({overall['rating'].upper()})",
            "",
            "Component Breakdown:",
            f"  Agenda Adherence: {overall['breakdown']['adherence']:.1f}%",
            f"    (focused on agenda vs off-topic)",
            f"  Novel Content: {overall['breakdown']['novelty']:.1f}%",
            f"    (new discussion vs repetition)",
            f"  Productivity: {overall['breakdown']['productivity']:.1f}%",
            f"    ({decision_rate:.2f} decisions/hour)",
            "",
            f"Decisions Made: {len(decisions)}",
            f"Open Items: {len(open_items)}",
            "=" * 50,
        ]
        return "\n".join(report_lines)
