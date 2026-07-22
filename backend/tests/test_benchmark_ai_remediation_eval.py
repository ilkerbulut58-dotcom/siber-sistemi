"""Phase 11.4 AI remediation benchmark tests."""

from __future__ import annotations

from app.benchmark.ai_remediation_eval import (
    ASSISTANT_LABEL_SOURCE,
    HUMAN_LABEL_SOURCE,
    PROVISIONAL_LABEL_SOURCE,
    evaluate_ai_remediation,
    load_golden_set,
    load_rubric,
)


def test_rubric_dimensions_present():
    rubric = load_rubric()
    golden = load_golden_set()
    assert rubric.llm_eval_auxiliary is True
    assert rubric.provisional_without_human_labels is True
    assert set(rubric.dimensions) == {
        "technical_accuracy",
        "applicability",
        "security",
        "clarity",
        "tech_fit",
    }
    assert len(golden.entries) >= 25


def test_official_scores_use_human_labels_only():
    report = evaluate_ai_remediation()
    assert report.human_labeled_count == 25
    assert report.provisional_count >= 1
    assert report.overall_score is not None

    human_cases = [item for item in report.case_results if item.label_source == HUMAN_LABEL_SOURCE]
    assert len(human_cases) == 25
    assert all(not item.provisional for item in human_cases)
    assert all(item.official_scores for item in human_cases)


def test_provisional_and_assistant_cases_are_marked_correctly():
    report = evaluate_ai_remediation()
    provisional = [item for item in report.case_results if item.provisional]
    assert any(item.label_source == PROVISIONAL_LABEL_SOURCE for item in provisional)

    assistant = [item for item in report.case_results if item.label_source == ASSISTANT_LABEL_SOURCE]
    assert len(assistant) == 1
    assert assistant[0].provisional is True
    assert assistant[0].official_scores == {}
    assert assistant[0].auxiliary_llm_scores
