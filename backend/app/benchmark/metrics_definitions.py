"""Canonical benchmark metric definitions for Faz 11.5 audit and release reporting."""

from __future__ import annotations

METRIC_DEFINITIONS: dict[str, dict[str, str]] = {
    "true_positive_count": {
        "class": "true_positive",
        "definition": (
            "Supported ground-truth item with detection_required=True matched to exactly one actual finding."
        ),
        "precision_recall": "included_in_numerator_and_precision_denominator",
    },
    "false_negative_count": {
        "class": "false_negative",
        "definition": (
            "Supported ground-truth item with detection_required=True with no matching actual finding."
        ),
        "precision_recall": "included_in_recall_denominator_only",
    },
    "confirmed_false_positive_count": {
        "class": "confirmed_false_positive",
        "definition": (
            "Actual finding with no ground-truth match, not duplicate, not informational, not matcher failure."
        ),
        "precision_recall": "included_in_precision_denominator_only",
    },
    "valid_additional_finding_count": {
        "class": "valid_additional_finding",
        "definition": (
            "Supported ground-truth item with detection_required=False matched to an actual finding."
        ),
        "precision_recall": "excluded_from_precision_and_recall",
    },
    "informational_count": {
        "class": "informational",
        "definition": (
            "Unmatched actual finding classified as out-of-scope informational (info severity or known info keys)."
        ),
        "precision_recall": "excluded_from_precision_and_recall",
    },
    "duplicate_count": {
        "class": "duplicate",
        "definition": (
            "Extra actual finding for an already-matched expected item, or duplicate of a matched finding."
        ),
        "precision_recall": "excluded_from_precision_and_recall",
    },
    "matcher_failure_count": {
        "class": "matcher_failure",
        "definition": (
            "Unmatched actual finding that would match a false-negative expected item under relaxed matching."
        ),
        "precision_recall": "excluded_from_precision; included_in_legacy_false_positive_count",
    },
    "partial_recall": {
        "class": "partial_coverage",
        "definition": "Recall for partially_supported expected items only.",
        "precision_recall": "separate_metric_not_mixed_with_main_recall",
    },
    "owasp_coverage_gap_count": {
        "class": "ground_truth_gap",
        "definition": "Expected items marked manual_only or unsupported (automation cannot cover).",
        "precision_recall": "excluded_from_precision_and_recall",
    },
}

PRECISION_FORMULA = "true_positive_count / (true_positive_count + confirmed_false_positive_count)"
RECALL_FORMULA = "true_positive_count / required_supported_detection_required_count"
F1_FORMULA = "harmonic_mean(precision, recall)"

EXCLUDED_FROM_PRECISION = frozenset(
    {
        "duplicate",
        "informational",
        "valid_additional_finding",
        "matcher_failure",
        "ground_truth_gap",
        "partial_coverage",
    }
)

EXCLUDED_FROM_RECALL = frozenset(
    {
        "duplicate",
        "informational",
        "valid_additional_finding",
        "confirmed_false_positive",
        "matcher_failure",
        "ground_truth_gap",
        "partial_coverage",
    }
)


def precision_recall_inclusion_table() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for metric_key, meta in METRIC_DEFINITIONS.items():
        rows.append(
            {
                "metric": metric_key,
                "classification": meta["class"],
                "precision": "yes" if "precision_denominator" in meta["precision_recall"] or meta["precision_recall"].startswith("included_in_numerator") else "no",
                "recall": "yes" if "recall_denominator" in meta["precision_recall"] or "numerator_and" in meta["precision_recall"] else "no",
                "notes": meta["definition"],
            }
        )
    return rows
