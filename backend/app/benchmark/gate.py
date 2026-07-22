"""Regression gate evaluation for benchmark runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.config import get_settings


@dataclass
class GateOutcome:
    passed: bool
    exit_code: int
    warnings: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)


def evaluate_gate(
    *,
    metrics: dict[str, Any],
    baseline: dict[str, Any] | None,
    delta: dict[str, Any],
    scanner_failed: bool,
    duration_seconds: float | None,
    missed_critical: int,
) -> GateOutcome:
    settings = get_settings()
    mode = settings.benchmark_gate_mode
    warnings: list[str] = []
    failures: list[str] = []

    if scanner_failed:
        failures.append("Scanner pipeline failed completely")

    if missed_critical > 0:
        failures.append(f"Missed {missed_critical} critical required finding(s)")

    if baseline and delta.get("baseline_available"):
        recall_drop = -delta.get("recall_delta", 0)
        if recall_drop > settings.benchmark_recall_drop_limit:
            failures.append(
                f"Recall dropped by {recall_drop:.3f} vs baseline (limit {settings.benchmark_recall_drop_limit})"
            )

    fp_rate = metrics.get("false_positive_rate", 0)
    if fp_rate > settings.benchmark_max_false_positive_rate:
        failures.append(
            f"False positive rate {fp_rate:.3f} exceeds limit {settings.benchmark_max_false_positive_rate}"
        )

    if duration_seconds and duration_seconds > settings.benchmark_max_duration_seconds:
        message = (
            f"Duration {duration_seconds:.1f}s exceeds limit {settings.benchmark_max_duration_seconds}s"
        )
        if settings.benchmark_fail_on_duration:
            failures.append(message)
        else:
            warnings.append(message)

    if mode in {"off", "report"}:
        if scanner_failed:
            return GateOutcome(passed=False, exit_code=1, warnings=warnings, failures=failures)
        return GateOutcome(passed=True, exit_code=0, warnings=warnings + failures, failures=[])

    if mode == "enforce" and failures:
        return GateOutcome(passed=False, exit_code=1, warnings=warnings, failures=failures)
    return GateOutcome(passed=not failures, exit_code=0, warnings=warnings, failures=failures)
