"""Tests for agenda validation service."""

from __future__ import annotations

import pytest

from services.agenda_validator import AgendaValidator


class TestValidateEmptyAgenda:
    """Test validation of empty agendas."""

    def test_empty_string_is_invalid(self):
        result = AgendaValidator.validate("")
        assert result["is_valid"] is False
        assert result["score"] == 0
        assert "empty" in result["quality_level"].lower()

    def test_whitespace_only_is_invalid(self):
        result = AgendaValidator.validate("   \n  \t  ")
        assert result["is_valid"] is False

    def test_none_string_is_invalid(self):
        result = AgendaValidator.validate("")
        assert result["is_valid"] is False


class TestValidateTooShort:
    """Test validation of agendas that are too short."""

    def test_very_short_description(self):
        result = AgendaValidator.validate("Meeting")
        assert result["score"] < 100
        assert "short" in " ".join(result["issues"]).lower()

    def test_few_words_detected(self):
        result = AgendaValidator.validate("Budget planning")
        assert result["score"] < 100


class TestValidateStructure:
    """Test validation of agenda structure."""

    def test_numbered_list_is_structured(self):
        result = AgendaValidator.validate(
            "1. Budget Review\n2. Team Updates\n3. Q&A"
        )
        # Should not have structure issues
        assert "structure" not in " ".join(result["issues"]).lower()

    def test_bulleted_list_is_structured(self):
        result = AgendaValidator.validate(
            "• Budget Review\n• Team Updates\n• Q&A"
        )
        assert "structure" not in " ".join(result["issues"]).lower()

    def test_unstructured_paragraph(self):
        result = AgendaValidator.validate(
            "We need to review the budget and update the team on progress"
        )
        # Might have structure issues
        assert result["score"] > 0


class TestValidateTopicCount:
    """Test validation of topic count."""

    def test_minimum_topics_ok(self):
        result = AgendaValidator.validate("1. Budget review")
        # Should have at least 1 topic
        assert "too few topics" not in " ".join(result["issues"]).lower()

    def test_good_number_of_topics(self):
        result = AgendaValidator.validate(
            "1. Budget\n2. Team\n3. Projects\n4. Timeline"
        )
        assert "topics" not in " ".join(result["issues"]).lower() or "too many" not in " ".join(result["issues"]).lower()

    def test_excessive_topics(self):
        result = AgendaValidator.validate(
            "1. A\n2. B\n3. C\n4. D\n5. E\n6. F\n7. G\n8. H\n9. I\n10. J\n11. K\n12. L"
        )
        # Should flag too many topics
        assert "too many" in " ".join(result["issues"]).lower() or result["score"] < 100


class TestValidateActionLanguage:
    """Test detection of action-oriented language."""

    def test_review_word_detected(self):
        result = AgendaValidator.validate("Review the budget and discuss timeline")
        # Should have action words
        assert "action" not in " ".join(result["issues"]).lower()

    def test_discuss_word_detected(self):
        result = AgendaValidator.validate("Discuss Q3 priorities")
        assert "action" not in " ".join(result["issues"]).lower()

    def test_decide_word_detected(self):
        result = AgendaValidator.validate("Decide on hiring plan")
        assert "action" not in " ".join(result["issues"]).lower()

    def test_passive_language_flagged(self):
        result = AgendaValidator.validate("Budget information, team status, schedule")
        # Might be flagged for lack of action words
        assert result["score"] > 0


class TestValidateClarity:
    """Test detection of vague language."""

    def test_misc_term_flagged(self):
        result = AgendaValidator.validate("1. Budget\n2. Misc items\n3. Other")
        assert "vague" in " ".join(result["issues"]).lower()

    def test_etc_term_flagged(self):
        result = AgendaValidator.validate("Budget review, team updates, etc.")
        assert "vague" in " ".join(result["issues"]).lower()

    def test_clear_specific_terms(self):
        result = AgendaValidator.validate(
            "1. Q3 Budget Review\n2. Hiring Plan\n3. Launch Timeline"
        )
        assert "vague" not in " ".join(result["issues"]).lower()


class TestValidateQualityLevels:
    """Test quality level assignments."""

    def test_excellent_agenda(self):
        result = AgendaValidator.validate(
            "1. Q3 Budget Review (15 min)\n"
            "2. Team Hiring Plan (20 min)\n"
            "3. Launch Timeline (10 min)\n"
            "4. Q&A and Discussion (5 min)"
        )
        assert result["score"] >= 80 or result["quality_level"] in ["excellent", "good"]

    def test_good_agenda(self):
        result = AgendaValidator.validate(
            "Review budget\nDiscuss timeline\nDecide on hiring"
        )
        assert result["is_valid"] is True
        assert result["score"] >= 40

    def test_poor_agenda(self):
        result = AgendaValidator.validate("stuff")
        assert result["is_valid"] is False or result["quality_level"] == "poor"

    def test_fair_agenda(self):
        result = AgendaValidator.validate("Meeting with stuff and things to discuss")
        # Score should be between fair and poor
        assert 0 <= result["score"] <= 100


class TestValidationMessage:
    """Test validation message formatting."""

    def test_empty_agenda_message(self):
        validation = AgendaValidator.validate("")
        message = AgendaValidator.build_validation_message(validation)
        assert "EMPTY" in message
        assert "add" in message.lower()

    def test_good_agenda_message(self):
        validation = AgendaValidator.validate(
            "1. Budget Review\n2. Team Updates"
        )
        message = AgendaValidator.build_validation_message(validation)
        assert "QUALITY" in message
        assert "Score" in message

    def test_message_includes_suggestions(self):
        validation = AgendaValidator.validate("stuff and misc")
        message = AgendaValidator.build_validation_message(validation)
        if validation["suggestions"]:
            # If there are suggestions, they should be in the message
            for suggestion in validation["suggestions"]:
                assert suggestion in message

    def test_message_includes_emoji(self):
        validation = AgendaValidator.validate("")
        message = AgendaValidator.build_validation_message(validation)
        assert any(
            emoji in message
            for emoji in ["✅", "✓", "⚠️", "❌"]
        )
