"""Ground-truth matching and metrics for isolated benchmark runs."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from app.models.benchmark import AutomationSupport, BenchmarkClassification
from app.models.finding import Finding

INFORMATIONAL_CORRELATION_KEYS = frozenset(
    {
        "info-modern-web-app",
        "generic.info-modern-web-app",
    }
)


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
    confirmed_false_positive_count: int = 0
    additional_valid_finding_count: int = 0
    ground_truth_gap_count: int = 0
    matcher_failure_count: int = 0
    unsupported_count: int = 0
    partial_true_positive_count: int = 0
    partial_false_negative_count: int = 0
    partial_recall: float = 0.0
    conditional_coverage_count: int = 0
    owasp_coverage_gap_count: int = 0
    informational_count: int = 0

    def as_dict(self) -> dict[str, float | int]:
        denominator = self.true_positive_count + self.confirmed_false_positive_count
        legacy_denominator = self.true_positive_count + self.false_positive_count
        return {
            **self.__dict__,
            "false_positive_rate": (
                self.confirmed_false_positive_count / denominator if denominator else 0.0
            ),
            "confirmed_false_positive_rate": (
                self.confirmed_false_positive_count / denominator if denominator else 0.0
            ),
            "legacy_false_positive_rate": (
                self.false_positive_count / legacy_denominator if legacy_denominator else 0.0
            ),
            "false_negative_rate": self.false_negative_count / self.expected_count if self.expected_count else 0.0,
            "duplicate_rate": self.duplicate_count / legacy_denominator if legacy_denominator else 0.0,
        }


def _automation_support(expected) -> str:
    value = getattr(expected, "automation_support", AutomationSupport.SUPPORTED) or AutomationSupport.SUPPORTED
    return str(value)


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


def _expected_keys(expected) -> set[str]:
    keys = {expected.expected_key.lower()}
    if expected.category:
        keys.add(expected.category.lower())
    keys.update(key.lower() for key in (expected.accepted_alternative_keys or []))
    return keys


def _matches(expected, finding: Finding) -> tuple[bool, str]:
    expected_keys = _expected_keys(expected)
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


def _relaxed_match(expected, finding: Finding) -> bool:
    if _matches(expected, finding)[0]:
        return True
    if expected.category and expected.category.lower() in (finding.title or "").lower():
        return True
    return expected.expected_key.lower() in (finding.title or "").lower()


def _is_informational_unmatched(finding: Finding) -> bool:
    severity = getattr(finding, "severity", None)
    source_tool = getattr(finding, "source_tool", None)
    correlation_key = getattr(finding, "correlation_key", None) or ""
    return correlation_key in INFORMATIONAL_CORRELATION_KEYS or (
        severity == "info" and source_tool in {"zap", "nuclei"}
    )


def _would_match(expected, finding: Finding) -> bool:
    return _relaxed_match(expected, finding)


def _is_duplicate_of_matched(finding: Finding, matched: list[Finding]) -> bool:
    for other in matched:
        if other.id == finding.id:
            continue
        if finding.correlation_key != other.correlation_key:
            continue
        if finding.fingerprint == other.fingerprint:
            return True
    return False


def match_findings(
    expected_findings: Iterable,
    actual_findings: Iterable[Finding],
    *,
    scanner_error_count: int = 0,
) -> tuple[list[MatchRecord], BenchmarkMetrics]:
    """Match expected findings; main P/R/F1 uses automation_support=supported only."""
    expected = list(expected_findings)
    actual = list(actual_findings)
    used_actual: set[object] = set()
    matched_findings: list[Finding] = []
    records: list[MatchRecord] = []
    tp = fn = legacy_fp = duplicates = 0
    confirmed_fp = additional_valid = gt_gap = matcher_failure = unsupported = 0
    partial_tp = partial_fn = conditional_coverage = owasp_gap = informational = 0

    measurable = [
        item
        for item in expected
        if _automation_support(item) in {AutomationSupport.SUPPORTED, AutomationSupport.PARTIALLY_SUPPORTED}
    ]
    for item in expected:
        if _automation_support(item) in {AutomationSupport.MANUAL_ONLY, AutomationSupport.UNSUPPORTED}:
            owasp_gap += 1
            records.append(
                MatchRecord(item.id, None, BenchmarkClassification.GROUND_TRUTH_MISSING, "coverage_gap")
            )

    for item in measurable:
        support = _automation_support(item)
        candidates = [
            (finding, reason)
            for finding in actual
            for matched, reason in [_matches(item, finding)]
            if matched
        ]
        primary = next(
            ((finding, reason) for finding, reason in candidates if finding.id not in used_actual),
            None,
        )
        if primary:
            finding, reason = primary
            used_actual.add(finding.id)
            matched_findings.append(finding)
            if support == AutomationSupport.SUPPORTED:
                if item.detection_required:
                    tp += 1
                    records.append(
                        MatchRecord(item.id, finding.id, BenchmarkClassification.TRUE_POSITIVE, reason)
                    )
                else:
                    additional_valid += 1
                    records.append(
                        MatchRecord(
                            item.id,
                            finding.id,
                            BenchmarkClassification.VALID_ADDITIONAL_FINDING,
                            reason,
                        )
                    )
            else:
                if item.detection_required:
                    partial_tp += 1
                    conditional_coverage += 1
                records.append(
                    MatchRecord(
                        item.id,
                        finding.id,
                        BenchmarkClassification.TRUE_POSITIVE,
                        f"partial:{reason}",
                    )
                )
            for duplicate, duplicate_reason in candidates:
                if duplicate.id != finding.id and duplicate.id not in used_actual:
                    used_actual.add(duplicate.id)
                    duplicates += 1
                    records.append(
                        MatchRecord(item.id, duplicate.id, BenchmarkClassification.DUPLICATE, duplicate_reason)
                    )
        elif item.detection_required:
            if support == AutomationSupport.SUPPORTED:
                fn += 1
                records.append(
                    MatchRecord(item.id, None, BenchmarkClassification.FALSE_NEGATIVE, "no_match")
                )
            else:
                partial_fn += 1
                records.append(
                    MatchRecord(item.id, None, BenchmarkClassification.FALSE_NEGATIVE, "partial_no_match")
                )

    fn_expected = [
        item
        for item in measurable
        if _automation_support(item) == AutomationSupport.SUPPORTED
        and item.detection_required
        and not any(
            record.expected_id == item.id
            and record.classification == BenchmarkClassification.TRUE_POSITIVE
            for record in records
        )
    ]

    unmatched = [finding for finding in actual if finding.id not in used_actual]
    for finding in unmatched:
        if any(_would_match(item, finding) for item in fn_expected):
            used_actual.add(finding.id)
            matcher_failure += 1
            legacy_fp += 1
            records.append(
                MatchRecord(None, finding.id, BenchmarkClassification.MATCHER_FAILURE, "matcher_failure")
            )
            continue

        if _is_duplicate_of_matched(finding, matched_findings):
            used_actual.add(finding.id)
            duplicates += 1
            records.append(
                MatchRecord(None, finding.id, BenchmarkClassification.DUPLICATE, "duplicate_unmatched")
            )
            continue

        if _is_informational_unmatched(finding):
            used_actual.add(finding.id)
            informational += 1
            records.append(
                MatchRecord(
                    None,
                    finding.id,
                    BenchmarkClassification.OUT_OF_SCOPE_INFORMATIONAL,
                    "informational",
                )
            )
            continue

        used_actual.add(finding.id)
        confirmed_fp += 1
        legacy_fp += 1
        records.append(
            MatchRecord(
                None,
                finding.id,
                BenchmarkClassification.CONFIRMED_FALSE_POSITIVE,
                "unmatched",
            )
        )

    required = sum(
        1
        for item in expected
        if _automation_support(item) == AutomationSupport.SUPPORTED and item.detection_required
    )
    partial_required = sum(
        1
        for item in expected
        if _automation_support(item) == AutomationSupport.PARTIALLY_SUPPORTED and item.detection_required
    )
    precision = tp / (tp + confirmed_fp) if tp + confirmed_fp else 0.0
    recall = tp / required if required else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    partial_recall = partial_tp / partial_required if partial_required else 0.0
    return records, BenchmarkMetrics(
        expected_count=required,
        true_positive_count=tp,
        false_negative_count=fn,
        false_positive_count=legacy_fp,
        duplicate_count=duplicates,
        scanner_error_count=scanner_error_count,
        precision=precision,
        recall=recall,
        f1_score=f1,
        confirmed_false_positive_count=confirmed_fp,
        additional_valid_finding_count=additional_valid,
        ground_truth_gap_count=gt_gap,
        matcher_failure_count=matcher_failure,
        unsupported_count=unsupported,
        partial_true_positive_count=partial_tp,
        partial_false_negative_count=partial_fn,
        partial_recall=partial_recall,
        conditional_coverage_count=conditional_coverage,
        owasp_coverage_gap_count=owasp_gap,
        informational_count=informational,
    )
