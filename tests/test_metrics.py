"""Tests for meeting efficiency metrics."""

from __future__ import annotations

import pytest

from services.metrics import MeetingMetrics


class TestAdherenceScore:
    """Test agenda adherence score computation."""

    def test_perfect_adherence_no_deviations(self):
        score = MeetingMetrics.compute_adherence_score(
            deviation_count=0.0,
            total_cycles=10,
        )
        assert score == 100.0

    def test_poor_adherence_many_deviations(self):
        score = MeetingMetrics.compute_adherence_score(
            deviation_count=20.0,
            total_cycles=10,
        )
        assert score == 0.0

    def test_moderate_adherence_some_deviations(self):
        score = MeetingMetrics.compute_adherence_score(
            deviation_count=5.0,
            total_cycles=10,
        )
        assert 70 < score < 80

    def test_tangential_discussion_half_deviation(self):
        score = MeetingMetrics.compute_adherence_score(
            deviation_count=0.5,
            total_cycles=1,
        )
        assert score >= 75

    def test_zero_cycles_returns_neutral(self):
        score = MeetingMetrics.compute_adherence_score(
            deviation_count=0.0,
            total_cycles=0,
        )
        assert score == 50.0

    def test_score_clamped_between_0_and_100(self):
        score = MeetingMetrics.compute_adherence_score(
            deviation_count=100.0,
            total_cycles=1,
        )
        assert 0 <= score <= 100


class TestRedundancyScore:
    """Test redundancy (repetition) score computation."""

    def test_no_redundancy_if_not_detected(self):
        score = MeetingMetrics.compute_redundancy_score(
            repetition_detected=False,
            repetition_count=0,
            total_topics_discussed=5,
        )
        assert score == 0.0

    def test_high_redundancy_if_detected(self):
        score = MeetingMetrics.compute_redundancy_score(
            repetition_detected=True,
            repetition_count=5,
            total_topics_discussed=5,
        )
        assert score == 100.0

    def test_partial_redundancy(self):
        score = MeetingMetrics.compute_redundancy_score(
            repetition_detected=True,
            repetition_count=2,
            total_topics_discussed=5,
        )
        assert score == 40.0

    def test_zero_topics_returns_neutral_if_detected(self):
        score = MeetingMetrics.compute_redundancy_score(
            repetition_detected=True,
            repetition_count=0,
            total_topics_discussed=0,
        )
        assert score == 50.0

    def test_zero_topics_returns_zero_if_not_detected(self):
        score = MeetingMetrics.compute_redundancy_score(
            repetition_detected=False,
            repetition_count=0,
            total_topics_discussed=0,
        )
        assert score == 0.0

    def test_score_clamped_at_100(self):
        score = MeetingMetrics.compute_redundancy_score(
            repetition_detected=True,
            repetition_count=100,
            total_topics_discussed=5,
        )
        assert score <= 100.0


class TestDecisionRate:
    """Test decision rate computation."""

    def test_one_decision_in_one_hour(self):
        rate = MeetingMetrics.compute_decision_rate(
            decisions=["Decision 1"],
            meeting_duration_minutes=60.0,
        )
        assert rate == pytest.approx(1.0)

    def test_two_decisions_in_thirty_minutes(self):
        rate = MeetingMetrics.compute_decision_rate(
            decisions=["Decision 1", "Decision 2"],
            meeting_duration_minutes=30.0,
        )
        assert rate == pytest.approx(4.0)

    def test_no_decisions_zero_rate(self):
        rate = MeetingMetrics.compute_decision_rate(
            decisions=[],
            meeting_duration_minutes=60.0,
        )
        assert rate == 0.0

    def test_zero_duration_zero_rate(self):
        rate = MeetingMetrics.compute_decision_rate(
            decisions=["Decision 1"],
            meeting_duration_minutes=0.0,
        )
        assert rate == 0.0

    def test_multiple_decisions(self):
        rate = MeetingMetrics.compute_decision_rate(
            decisions=[f"Decision {i}" for i in range(10)],
            meeting_duration_minutes=120.0,
        )
        assert rate == pytest.approx(5.0)


class TestOverallEfficiency:
    """Test overall efficiency score and rating."""

    def test_excellent_rating_high_scores(self):
        result = MeetingMetrics.compute_overall_efficiency(
            adherence_score=95.0,
            redundancy_score=5.0,
            decision_rate=5.0,
        )
        assert result["score"] >= 80
        assert result["rating"] == "excellent"

    def test_good_rating_moderate_scores(self):
        result = MeetingMetrics.compute_overall_efficiency(
            adherence_score=75.0,
            redundancy_score=25.0,
            decision_rate=3.0,
        )
        assert 60 <= result["score"] < 80
        assert result["rating"] == "good"

    def test_fair_rating_mixed_scores(self):
        result = MeetingMetrics.compute_overall_efficiency(
            adherence_score=60.0,
            redundancy_score=40.0,
            decision_rate=2.0,
        )
        assert 40 <= result["score"] < 60
        assert result["rating"] == "fair"

    def test_poor_rating_low_scores(self):
        result = MeetingMetrics.compute_overall_efficiency(
            adherence_score=30.0,
            redundancy_score=70.0,
            decision_rate=0.5,
        )
        assert result["score"] < 40
        assert result["rating"] == "poor"

    def test_breakdown_keys_present(self):
        result = MeetingMetrics.compute_overall_efficiency(
            adherence_score=80.0,
            redundancy_score=20.0,
            decision_rate=3.0,
        )
        assert "adherence" in result["breakdown"]
        assert "novelty" in result["breakdown"]
        assert "productivity" in result["breakdown"]

    def test_breakdown_novelty_is_inverse_of_redundancy(self):
        result = MeetingMetrics.compute_overall_efficiency(
            adherence_score=80.0,
            redundancy_score=30.0,
            decision_rate=3.0,
        )
        # Novelty should be 100 - redundancy
        assert result["breakdown"]["novelty"] == pytest.approx(70.0)

    def test_breakdown_productivity_normalized(self):
        result = MeetingMetrics.compute_overall_efficiency(
            adherence_score=80.0,
            redundancy_score=20.0,
            decision_rate=5.0,  # max expected
        )
        # Productivity should be at 100 for decision_rate=5
        assert result["breakdown"]["productivity"] == pytest.approx(100.0)

    def test_breakdown_productivity_below_max(self):
        result = MeetingMetrics.compute_overall_efficiency(
            adherence_score=80.0,
            redundancy_score=20.0,
            decision_rate=2.5,  # half of 5
        )
        # Productivity should be at 50
        assert result["breakdown"]["productivity"] == pytest.approx(50.0)

    def test_score_clamped_between_0_and_100(self):
        result = MeetingMetrics.compute_overall_efficiency(
            adherence_score=200.0,  # over 100
            redundancy_score=-50.0,  # under 0
            decision_rate=1000.0,  # very high
        )
        assert 0 <= result["score"] <= 100


class TestMetricsReport:
    """Test human-readable metrics report generation."""

    def test_report_includes_overall_score(self):
        overall = {
            "score": 85.5,
            "rating": "excellent",
            "breakdown": {
                "adherence": 90.0,
                "novelty": 80.0,
                "productivity": 85.0,
            },
        }
        report = MeetingMetrics.build_metrics_report(
            adherence_score=90.0,
            redundancy_score=20.0,
            decision_rate=4.0,
            overall=overall,
            decisions=["Decision 1", "Decision 2"],
            open_items=["Item A"],
        )
        assert "85.5" in report
        assert "excellent" in report.lower()

    def test_report_includes_breakdown(self):
        overall = {
            "score": 75.0,
            "rating": "good",
            "breakdown": {
                "adherence": 75.0,
                "novelty": 80.0,
                "productivity": 70.0,
            },
        }
        report = MeetingMetrics.build_metrics_report(
            adherence_score=75.0,
            redundancy_score=20.0,
            decision_rate=3.0,
            overall=overall,
            decisions=["Decision 1"],
            open_items=["Item A", "Item B"],
        )
        assert "75.0" in report  # adherence
        assert "80.0" in report  # novelty
        assert "70.0" in report  # productivity

    def test_report_includes_decision_count(self):
        overall = {
            "score": 70.0,
            "rating": "good",
            "breakdown": {
                "adherence": 70.0,
                "novelty": 70.0,
                "productivity": 70.0,
            },
        }
        report = MeetingMetrics.build_metrics_report(
            adherence_score=70.0,
            redundancy_score=30.0,
            decision_rate=3.0,
            overall=overall,
            decisions=["A", "B", "C"],
            open_items=["X", "Y"],
        )
        assert "3" in report  # Decisions Made: 3
        assert "2" in report  # Open Items: 2

    def test_report_is_formatted(self):
        overall = {
            "score": 65.0,
            "rating": "good",
            "breakdown": {
                "adherence": 65.0,
                "novelty": 70.0,
                "productivity": 60.0,
            },
        }
        report = MeetingMetrics.build_metrics_report(
            adherence_score=65.0,
            redundancy_score=30.0,
            decision_rate=3.0,
            overall=overall,
            decisions=[],
            open_items=[],
        )
        assert "=" in report
        assert "EFFICIENCY" in report.upper()
