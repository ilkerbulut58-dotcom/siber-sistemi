"""MVP release gate evaluation for Faz 11.5 (report-only; does not mutate baselines)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.benchmark.manifests import repo_benchmarks_root


@dataclass(frozen=True)
class ReleaseGate:
    gate_id: str
    description: str
    threshold: float | int | bool
    actual: float | int | bool
    passed: bool
    root_cause: str | None = None


@dataclass(frozen=True)
class ReleaseGateReport:
    status: str
    ready_for: str
    gates: list[ReleaseGate]
    blockers: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "ready_for": self.ready_for,
            "blockers": self.blockers,
            "gates": [
                {
                    "gate_id": gate.gate_id,
                    "description": gate.description,
                    "threshold": gate.threshold,
                    "actual": gate.actual,
                    "passed": gate.passed,
                    "root_cause": gate.root_cause,
                }
                for gate in self.gates
            ],
        }


def _gate(
    gate_id: str,
    description: str,
    *,
    threshold: float | int | bool,
    actual: float | int | bool,
    comparator: str,
    root_cause: str | None = None,
) -> ReleaseGate:
    if comparator == "gte":
        passed = float(actual) >= float(threshold)
    elif comparator == "lte":
        passed = float(actual) <= float(threshold)
    elif comparator == "eq":
        passed = actual == threshold
    else:
        passed = False
    return ReleaseGate(
        gate_id=gate_id,
        description=description,
        threshold=threshold,
        actual=actual,
        passed=passed,
        root_cause=None if passed else root_cause,
    )


def evaluate_release_gates(
    *,
    passive_web: dict[str, Any] | None = None,
    passive_api: dict[str, Any] | None = None,
    active_web: dict[str, Any] | None = None,
    active_api: dict[str, Any] | None = None,
    customer_variance_pct: float | None = None,
    external_request_count: int = 0,
    blind_validation_passed: bool | None = None,
    risk_official_human_only: bool = True,
    ai_official_human_only: bool = True,
) -> ReleaseGateReport:
    gates: list[ReleaseGate] = []

    if passive_web:
        gates.append(
            _gate(
                "passive_web_precision",
                "Passive web precision",
                threshold=0.80,
                actual=passive_web.get("precision", 0),
                comparator="gte",
                root_cause="Confirmed false positives or matcher gaps on web passive subset.",
            )
        )
        gates.append(
            _gate(
                "passive_web_recall",
                "Passive web recall",
                threshold=0.70,
                actual=passive_web.get("recall", 0),
                comparator="gte",
                root_cause="Required web passive detections still missing.",
            )
        )
    if passive_api:
        gates.append(
            _gate(
                "passive_api_precision",
                "Passive API precision",
                threshold=0.80,
                actual=passive_api.get("precision", 0),
                comparator="gte",
            )
        )
        gates.append(
            _gate(
                "passive_api_recall",
                "Passive API recall",
                threshold=0.70,
                actual=passive_api.get("recall", 0),
                comparator="gte",
            )
        )
    if active_web:
        gates.append(
            _gate(
                "active_web_precision",
                "Active web precision",
                threshold=0.70,
                actual=active_web.get("precision", 0),
                comparator="gte",
                root_cause="ZAP active duplicate/noise inflating confirmed FP count.",
            )
        )
        gates.append(
            _gate(
                "active_web_recall",
                "Active web recall",
                threshold=0.70,
                actual=active_web.get("recall", 0),
                comparator="gte",
            )
        )
    if active_api:
        gates.append(
            _gate(
                "active_api_precision",
                "Active API precision",
                threshold=0.70,
                actual=active_api.get("precision", 0),
                comparator="gte",
            )
        )
        gates.append(
            _gate(
                "active_api_recall",
                "Active API recall",
                threshold=0.60,
                actual=active_api.get("recall", 0),
                comparator="gte",
                root_cause="API surface discovery or auth/state coverage gaps.",
            )
        )
    if customer_variance_pct is not None:
        gates.append(
            _gate(
                "customer_visible_variance",
                "Customer-visible finding run-to-run variance",
                threshold=5.0,
                actual=customer_variance_pct,
                comparator="lte",
                root_cause="Canonical dedup or spider completion still non-deterministic.",
            )
        )
    gates.append(
        _gate(
            "external_request_count",
            "External/destructive request count",
            threshold=0,
            actual=external_request_count,
            comparator="eq",
            root_cause="Active guard allowed outbound requests outside allowlist.",
        )
    )
    if blind_validation_passed is not None:
        gates.append(
            _gate(
                "blind_validation",
                "Blind holdout validation",
                threshold=True,
                actual=blind_validation_passed,
                comparator="eq",
                root_cause="BLIND_GROUND_TRUTH_SECRET not configured or holdout mismatch.",
            )
        )
    gates.append(
        _gate(
            "risk_human_labels_only",
            "Risk Engine official scores use human labels only",
            threshold=True,
            actual=risk_official_human_only,
            comparator="eq",
        )
    )
    gates.append(
        _gate(
            "ai_human_labels_only",
            "AI remediation official scores use human labels only",
            threshold=True,
            actual=ai_official_human_only,
            comparator="eq",
        )
    )

    blockers = [f"{gate.gate_id}: {gate.root_cause}" for gate in gates if not gate.passed and gate.root_cause]
    all_passed = all(gate.passed for gate in gates)
    if all_passed:
        ready_for = "closed_pilot"
        status = "ready"
    elif any(gate.passed for gate in gates):
        ready_for = "internal_alpha"
        status = "not_ready"
    else:
        ready_for = "internal_alpha"
        status = "not_ready"

    return ReleaseGateReport(status=status, ready_for=ready_for, gates=gates, blockers=blockers)


def write_release_gate_report(report: ReleaseGateReport, output_dir: Path | None = None) -> Path:
    root = output_dir or (repo_benchmarks_root() / "reports")
    root.mkdir(parents=True, exist_ok=True)
    path = root / "release-gates-mvp.json"
    path.write_text(json.dumps(report.as_dict(), indent=2), encoding="utf-8")
    return path
