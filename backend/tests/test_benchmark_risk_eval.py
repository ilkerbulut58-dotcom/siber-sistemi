"""Phase 11.4 Risk Engine benchmark tests."""

from __future__ import annotations

from app.benchmark.risk_eval import (
    ASSISTANT_LABEL_SOURCE,
    HUMAN_LABEL_SOURCE,
    evaluate_risk_engine,
    load_golden_set,
    load_rubric,
)


def test_rubric_and_golden_set_load():
    rubric = load_rubric()
    golden = load_golden_set()
    assert rubric.version == "1.0.0"
    assert "severity_band_compliance" in rubric.metrics
    assert len(golden.entries) >= 3


def test_official_metrics_exclude_assistant_generated_labels():
    report = evaluate_risk_engine()
    assert report.official_label_source == HUMAN_LABEL_SOURCE
    assert report.human_labeled_count == 2
    assert report.assistant_generated_count == 1
    assert report.provisional_count == 1
    assert report.severity_band_compliance_rate is not None
    assert report.severity_agreement_rate is not None
    assert report.false_severity_rate is not None

    assistant_cases = [
        item for item in report.case_results if item.label_source == ASSISTANT_LABEL_SOURCE
    ]
    assert len(assistant_cases) == 1
    assert assistant_cases[0].included_in_official_metrics is False
    assert assistant_cases[0].severity_agreement is None


def test_human_cases_are_included_in_official_metrics():
    report = evaluate_risk_engine()
    human_cases = [item for item in report.case_results if item.included_in_official_metrics]
    assert len(human_cases) == 2
    assert all(item.severity_agreement is not None for item in human_cases)
    assert all(item.severity_band_compliance is not None for item in human_cases)
