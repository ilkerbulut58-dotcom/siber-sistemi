"""Metric audit utilities: old vs new comparisons and Risk Engine confusion tables."""

from __future__ import annotations

from typing import Any

from app.benchmark.metrics_definitions import (
    EXCLUDED_FROM_PRECISION,
    EXCLUDED_FROM_RECALL,
    PRECISION_FORMULA,
    RECALL_FORMULA,
)
from app.benchmark.risk_eval import (
    evaluate_case,
    load_golden_set,
    load_rubric,
    severity_band_for_score,
)
from app.services.benchmark_matching_service import BenchmarkMetrics, match_findings


def compare_precision_recall(metrics: BenchmarkMetrics) -> dict[str, Any]:
    """Show legacy vs current precision/recall without changing stored metrics."""
    tp = metrics.true_positive_count
    confirmed_fp = metrics.confirmed_false_positive_count
    legacy_fp = metrics.false_positive_count
    required = metrics.expected_count

    current_precision = metrics.precision
    current_recall = metrics.recall
    legacy_precision = tp / (tp + legacy_fp) if tp + legacy_fp else 0.0

    return {
        "formulas": {
            "precision": PRECISION_FORMULA,
            "recall": RECALL_FORMULA,
        },
        "excluded_from_precision": sorted(EXCLUDED_FROM_PRECISION),
        "excluded_from_recall": sorted(EXCLUDED_FROM_RECALL),
        "current": {
            "precision": current_precision,
            "recall": current_recall,
            "f1_score": metrics.f1_score,
            "denominator_precision": tp + confirmed_fp,
            "denominator_recall": required,
        },
        "legacy_comparison": {
            "precision_if_legacy_fp": legacy_precision,
            "precision_delta": current_precision - legacy_precision,
            "legacy_fp_includes_matcher_failures": metrics.matcher_failure_count,
        },
        "counts": metrics.as_dict(),
    }


def risk_engine_confusion_table() -> dict[str, Any]:
    """Explain why severity_agreement=1.0 can coexist with band_compliance=0.0."""
    rubric = load_rubric()
    golden = load_golden_set()
    rows: list[dict[str, Any]] = []
    for case in golden.entries:
        result = evaluate_case(case, rubric)
        predicted_band = severity_band_for_score(rubric, result.predicted_risk_score)
        rows.append(
            {
                "case_id": case.case_id,
                "label_source": case.label_source,
                "input_severity": case.severity,
                "human_severity": case.human_severity,
                "reference_severity": case.human_severity or case.severity,
                "predicted_risk_score": round(result.predicted_risk_score, 2),
                "predicted_severity_band": predicted_band,
                "expected_score_band": f"{case.expected_risk_score_min}-{case.expected_risk_score_max}",
                "severity_agreement": result.severity_agreement,
                "severity_band_compliance": result.severity_band_compliance,
                "false_severity": result.false_severity,
                "explanation": (
                    "Agreement previously compared input severity to itself; "
                    "band compliance compares computed score to expected numeric band."
                ),
            }
        )

    official = [row for row in rows if row["label_source"] == "human"]
    return {
        "summary": {
            "severity_agreement_rate_old_logic": "1.0 when predicted_severity=input_severity",
            "severity_band_compliance_rate": (
                sum(1 for row in official if row["severity_band_compliance"]) / len(official)
                if official
                else None
            ),
            "root_cause": (
                "Severity agreement used case.severity as predicted severity instead of "
                "the band derived from calculate_risk_score(); band compliance uses numeric score ranges."
            ),
        },
        "confusion_table": rows,
    }


def audit_match_sample(expected: list, actual: list) -> dict[str, Any]:
    records, metrics = match_findings(expected, actual)
    return {
        "comparison": compare_precision_recall(metrics),
        "classification_counts": {
            record.classification: sum(1 for item in records if item.classification == record.classification)
            for record in records
        },
    }
