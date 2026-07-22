"""Ground-truth matching and metrics for isolated benchmark runs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.models.benchmark import BenchmarkClassification
from app.models.finding import Finding


@dataclass(frozen=True)
class MatchRecord:
    expected_id: object | None
    finding_id: object | None
    classification: str
    reason: str


@dataclass(frozen=True)
class BenchmarkMetrics:
    expected_count: int
    true_positive_count: int
    false_negative_count: int
    false_positive_count: int
    duplicate_count: int
    scanner_error_count: int
    precision: float
    recall: float
    f1_score: float

    def as_dict(self) -> dict[str, float | int]:
        denominator = self.true_positive_count + self.false_positive_count
        return {
            **self.__dict__,
            "false_positive_rate": self.false_positive_count / denominator if denominator else 0.0,
            "false_negative_rate": self.false_negative_count / self.expected_count if self.expected_count else 0.0,
            "duplicate_rate": self.duplicate_count / denominator if denominator else 0.0,
        }


def _finding_keys(finding: Finding) -> set[str]:
    keys = {
        value.lower()
        for value in (
            finding.correlation_key,
            finding.source_rule_id,
            finding.fingerprint,
        )
        if value
    }
    source_tools = getattr(finding, "source_tools", None)
    if source_tools:
        for tool in source_tools:
            if isinstance(tool, str):
                keys.add(tool.lower())
    return keys


def _matches(expected, finding: Finding) -> tuple[bool, str]:
    expected_keys = {expected.expected_key.lower()}
    if expected.category:
        expected_keys.add(expected.category.lower())
    expected_keys.update(key.lower() for key in (expected.accepted_alternative_keys or []))
    keys = _finding_keys(finding)
    if expected_keys & keys:
        return True, "key"
    if expected.category and finding.correlation_key == expected.category:
        return True, "category"
    if (
        expected.affected_location
        and finding.affected_url
        and finding.affected_url.rstrip("/") == expected.affected_location.rstrip("/")
        and expected.category
        and expected.category.lower() in (finding.title or "").lower()
    ):
        return True, "location_and_category"
    return False, ""


def match_findings(
    expected_findings: Iterable,
    actual_findings: Iterable[Finding],
    *,
    scanner_error_count: int = 0,
) -> tuple[list[MatchRecord], BenchmarkMetrics]:
    """Match each required expected finding once; extra matches are duplicates/FPs."""
    expected = list(expected_findings)
    actual = list(actual_findings)
    used_actual: set[object] = set()
    records: list[MatchRecord] = []
    tp = fn = fp = duplicates = 0

    for item in expected:
        candidates = [(finding, reason) for finding in actual for matched, reason in [_matches(item, finding)] if matched]
        primary = next(((finding, reason) for finding, reason in candidates if finding.id not in used_actual), None)
        if primary:
            finding, reason = primary
            used_actual.add(finding.id)
            if item.detection_required:
                tp += 1
            records.append(MatchRecord(item.id, finding.id, BenchmarkClassification.TRUE_POSITIVE, reason))
            for duplicate, duplicate_reason in candidates:
                if duplicate.id != finding.id and duplicate.id not in used_actual:
                    used_actual.add(duplicate.id)
                    duplicates += 1
                    records.append(
                        MatchRecord(item.id, duplicate.id, BenchmarkClassification.DUPLICATE, duplicate_reason)
                    )
        elif item.detection_required:
            fn += 1
            records.append(MatchRecord(item.id, None, BenchmarkClassification.FALSE_NEGATIVE, "no_match"))

    for finding in actual:
        if finding.id not in used_actual:
            fp += 1
            records.append(MatchRecord(None, finding.id, BenchmarkClassification.FALSE_POSITIVE, "unmatched"))

    required = sum(1 for item in expected if item.detection_required)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / required if required else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return records, BenchmarkMetrics(required, tp, fn, fp, duplicates, scanner_error_count, precision, recall, f1)
