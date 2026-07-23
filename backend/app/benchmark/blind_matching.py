"""Blind holdout matching — precision without penalizing valid out-of-holdout findings."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.models.benchmark import BenchmarkClassification
from app.services.benchmark_matching_service import (
    INFORMATIONAL_CORRELATION_KEYS,
    BenchmarkMetrics,
    MatchRecord,
    match_findings,
)

# Real passive security findings on web-smoke that may appear outside encrypted holdout keys.
BLIND_VALID_OUT_OF_HOLDOUT_KEYS = frozenset(
    {
        "missing-header-content-security-policy",
        "missing-header-strict-transport-security",
        "missing-header-x-content-type-options",
        "missing-header-x-frame-options",
        "missing-header-referrer-policy",
        "x-powered-by-disclosure",
        "server-disclosure",
        "insecure-cookie-flags",
        "no-https",
        "hardcoded-password",
        "db-connection-string",
        "generic-iban",
        "turkish-iban",
        "credit-card-number",
        "permissive-cors",
    }
)

BLIND_ZAP_NOISE_PREFIXES = ("generic.", "cross-domain-javascript")


def _is_blind_informational(finding: Any) -> bool:
    severity = getattr(finding, "severity", None)
    correlation_key = getattr(finding, "correlation_key", None) or ""
    if correlation_key in INFORMATIONAL_CORRELATION_KEYS:
        return True
    if severity == "info":
        return True
    return correlation_key.startswith(BLIND_ZAP_NOISE_PREFIXES)


def _is_valid_out_of_holdout(finding: Any, holdout_keys: set[str]) -> bool:
    correlation_key = (getattr(finding, "correlation_key", None) or "").lower()
    if correlation_key in holdout_keys:
        return False
    if correlation_key in BLIND_VALID_OUT_OF_HOLDOUT_KEYS:
        return True
    return correlation_key.startswith("missing-header-")


def _finding_by_id(actual: list[Any]) -> dict[Any, Any]:
    return {item.id: item for item in actual}


def match_blind_holdout_findings(
    expected_findings: Iterable,
    actual_findings: Iterable,
) -> tuple[list[MatchRecord], BenchmarkMetrics, list[dict[str, str]]]:
    """Match blind holdout GT; classify unmatched findings instead of treating all as FP."""
    expected = list(expected_findings)
    actual = list(actual_findings)
    holdout_keys = {item.expected_key.lower() for item in expected}

    records, metrics = match_findings(expected, actual)
    finding_map = _finding_by_id(actual)
    reclassified: list[dict[str, str]] = []

    updated_records: list[MatchRecord] = []
    confirmed_fp = 0
    additional_valid = 0
    informational = 0
    duplicates = 0
    tp = metrics.true_positive_count
    fn = metrics.false_negative_count

    for record in records:
        if record.classification != BenchmarkClassification.CONFIRMED_FALSE_POSITIVE:
            updated_records.append(record)
            if record.classification == BenchmarkClassification.DUPLICATE:
                duplicates += 1
            if record.classification == BenchmarkClassification.OUT_OF_SCOPE_INFORMATIONAL:
                informational += 1
            if record.classification == BenchmarkClassification.VALID_ADDITIONAL_FINDING:
                additional_valid += 1
            continue

        finding = finding_map.get(record.finding_id)
        if finding is None:
            updated_records.append(record)
            confirmed_fp += 1
            continue

        if _is_blind_informational(finding):
            updated_records.append(
                MatchRecord(record.expected_id, record.finding_id, BenchmarkClassification.OUT_OF_SCOPE_INFORMATIONAL, "blind_informational")
            )
            informational += 1
            reclassified.append(
                {
                    "correlation_key": getattr(finding, "correlation_key", ""),
                    "classification": "informational_noise",
                    "reason": "info_severity_or_zap_noise",
                }
            )
            continue

        if _is_valid_out_of_holdout(finding, holdout_keys):
            updated_records.append(
                MatchRecord(
                    record.expected_id,
                    record.finding_id,
                    BenchmarkClassification.VALID_ADDITIONAL_FINDING,
                    "blind_out_of_holdout_valid",
                )
            )
            additional_valid += 1
            reclassified.append(
                {
                    "correlation_key": getattr(finding, "correlation_key", ""),
                    "classification": "passive_noise",
                    "reason": "valid_security_finding_not_in_holdout",
                }
            )
            continue

        updated_records.append(record)
        confirmed_fp += 1
        reclassified.append(
            {
                "correlation_key": getattr(finding, "correlation_key", ""),
                "classification": "confirmed_false_positive",
                "reason": "unmatched_not_validated",
            }
        )

    precision = tp / (tp + confirmed_fp) if tp + confirmed_fp else 0.0
    required = metrics.expected_count
    recall = tp / required if required else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    adjusted = BenchmarkMetrics(
        expected_count=required,
        true_positive_count=tp,
        false_negative_count=fn,
        false_positive_count=confirmed_fp + additional_valid,
        duplicate_count=duplicates,
        scanner_error_count=metrics.scanner_error_count,
        precision=precision,
        recall=recall,
        f1_score=f1,
        confirmed_false_positive_count=confirmed_fp,
        additional_valid_finding_count=additional_valid,
        ground_truth_gap_count=metrics.ground_truth_gap_count,
        matcher_failure_count=metrics.matcher_failure_count,
        unsupported_count=metrics.unsupported_count,
        partial_true_positive_count=metrics.partial_true_positive_count,
        partial_false_negative_count=metrics.partial_false_negative_count,
        partial_recall=metrics.partial_recall,
        conditional_coverage_count=metrics.conditional_coverage_count,
        owasp_coverage_gap_count=metrics.owasp_coverage_gap_count,
        informational_count=informational,
    )
    return updated_records, adjusted, reclassified
