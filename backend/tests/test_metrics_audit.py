"""Metric audit tests."""

from __future__ import annotations

from app.benchmark.metrics_audit import compare_precision_recall, risk_engine_confusion_table
from app.services.benchmark_matching_service import BenchmarkMetrics


def test_compare_precision_recall_shows_legacy_delta():
    metrics = BenchmarkMetrics(
        expected_count=5,
        true_positive_count=3,
        false_negative_count=2,
        false_positive_count=4,
        duplicate_count=1,
        scanner_error_count=0,
        precision=0.6,
        recall=0.6,
        f1_score=0.6,
        confirmed_false_positive_count=2,
        matcher_failure_count=2,
    )
    payload = compare_precision_recall(metrics)
    assert payload["current"]["precision"] == 0.6
    assert payload["legacy_comparison"]["legacy_fp_includes_matcher_failures"] == 2


def test_risk_confusion_table_documents_divergence():
    table = risk_engine_confusion_table()
    assert table["summary"]["root_cause"]
    assert table["confusion_table"]
