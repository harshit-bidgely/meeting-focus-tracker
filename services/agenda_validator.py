"""Pre-meeting agenda quality validation.

Validates calendar event descriptions and suggests improvements
if agendas are missing, vague, or incomplete.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


class AgendaValidator:
    """Validates agenda quality and provides improvement suggestions."""

    # Quality factors
    MIN_LENGTH_CHARS = 20
    MIN_DISTINCT_WORDS = 5
    MIN_TOPICS = 1
    MAX_TOPICS = 10

    @staticmethod
    def validate(description: str) -> dict:
        """Validate agenda description and return quality assessment.

        Returns:
        {
            "is_valid": bool,
            "score": 0-100,
            "issues": [list of problems found],
            "suggestions": [list of suggestions],
            "quality_level": "excellent|good|fair|poor|empty"
        }
        """
        if not description or not description.strip():
            return {
                "is_valid": False,
                "score": 0,
                "issues": ["Agenda is empty"],
                "suggestions": ["Add a clear agenda to the event description"],
                "quality_level": "empty",
            }

        issues = []
        suggestions = []
        score = 100

        # Check 1: Length
        if len(description.strip()) < AgendaValidator.MIN_LENGTH_CHARS:
            issues.append(f"Agenda is too short (< {AgendaValidator.MIN_LENGTH_CHARS} chars)")
            score -= 30
            suggestions.append("Add more detail to make the agenda clearer")

        # Check 2: Word count
        words = description.split()
        if len(words) < AgendaValidator.MIN_DISTINCT_WORDS:
            issues.append(f"Agenda has too few words (< {AgendaValidator.MIN_DISTINCT_WORDS})")
            score -= 25
            suggestions.append("Include specific topic names and discussion points")

        # Check 3: Numbered or bulleted items (structure)
        has_structure = bool(
            re.search(r"^\s*[\d\.\-\*\+•]\s", description, re.MULTILINE)
        )
        if not has_structure:
            # Check for comma-separated or sentence-based topics
            sentences = re.split(r"[.!?]", description)
            if len(sentences) < 2:
                issues.append("Agenda lacks clear structure (no bullets, numbers, or clear topic separation)")
                score -= 15
                suggestions.append("Use bullet points or numbered list for clarity: '1. Topic\\n2. Topic'")

        # Check 4: Topic count
        # Estimate number of topics
        potential_topics = len(re.split(r"[,;•\n]", description))
        if potential_topics < AgendaValidator.MIN_TOPICS:
            issues.append(f"Agenda has too few topics (< {AgendaValidator.MIN_TOPICS})")
            score -= 10
            suggestions.append("Add at least 1-2 discussion topics")
        elif potential_topics > AgendaValidator.MAX_TOPICS:
            issues.append(f"Agenda has too many topics (> {AgendaValidator.MAX_TOPICS})")
            score -= 10
            suggestions.append("Consider consolidating topics or splitting into multiple meetings")

        # Check 5: Action-oriented language
        action_words = [
            "review", "discuss", "decide", "plan", "update", "presentation",
            "brainstorm", "align", "approve", "vote", "present", "share",
            "feedback", "define", "outline", "schedule", "identify"
        ]
        has_action_words = any(
            word in description.lower()
            for word in action_words
        )
        if not has_action_words:
            issues.append("Agenda lacks action-oriented language")
            score -= 10
            suggestions.append("Use action verbs: 'Review', 'Discuss', 'Decide', 'Plan', etc.")

        # Check 6: Clarity and specificity
        vague_terms = [
            "misc", "other", "etc", "stuff", "things", "stuff",
            "random", "miscellaneous", "general discussion"
        ]
        has_vague = any(
            term in description.lower()
            for term in vague_terms
        )
        if has_vague:
            issues.append("Agenda contains vague terms")
            score -= 15
            suggestions.append("Replace vague terms with specific topics (avoid 'misc', 'other', 'etc')")

        # Determine quality level
        if score >= 80:
            quality_level = "excellent"
        elif score >= 60:
            quality_level = "good"
        elif score >= 40:
            quality_level = "fair"
        else:
            quality_level = "poor"

        # Add general suggestions if score is low
        if score < 60 and not suggestions:
            suggestions.append("Consider adding: topic names, expected outcomes, time allocation per item")
            suggestions.append("Example format: '1. Budget Review (15 min)\\n2. Team Updates (10 min)\\n3. Q&A (5 min)'")

        return {
            "is_valid": score >= 40,
            "score": max(0, min(100, score)),
            "issues": issues,
            "suggestions": suggestions[:3],  # limit to 3 suggestions
            "quality_level": quality_level,
        }

    @staticmethod
    def build_validation_message(validation: dict) -> str:
        """Build a human-readable validation report."""
        lines = []

        if validation["quality_level"] == "empty":
            lines.append("❌ AGENDA IS EMPTY")
            lines.append("━" * 50)
            lines.append("Please add a clear agenda to the event description.")
            lines.append("Include specific topics to discuss and expected outcomes.")
            lines.append("")
            lines.append("Example agenda:")
            lines.append("  1. Q3 Budget Review (15 min)")
            lines.append("  2. Team Headcount Planning (20 min)")
            lines.append("  3. Timeline & Next Steps (10 min)")
            return "\n".join(lines)

        quality_emoji = {
            "excellent": "✅",
            "good": "✓",
            "fair": "⚠️",
            "poor": "❌",
        }.get(validation["quality_level"], "?")

        lines.append(f"{quality_emoji} AGENDA QUALITY: {validation['quality_level'].upper()}")
        lines.append("━" * 50)
        lines.append(f"Quality Score: {validation['score']}/100")
        lines.append("")

        if validation["issues"]:
            lines.append("Issues Found:")
            for issue in validation["issues"]:
                lines.append(f"  • {issue}")
            lines.append("")

        if validation["suggestions"]:
            lines.append("Suggestions:")
            for i, suggestion in enumerate(validation["suggestions"], 1):
                lines.append(f"  {i}. {suggestion}")

        return "\n".join(lines)
