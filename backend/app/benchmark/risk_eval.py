"""Risk Engine golden-set evaluation — human labels only for official metrics."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import yaml

from app.analysis.risk_engine import RISK_MODEL_VERSION, calculate_risk_score
from app.analysis.types import AnalyzedFinding
from app.benchmark.manifests import repo_benchmarks_root

LabelSource = Literal["human", "assistant_generated", "provisional"]
HUMAN_LABEL_SOURCE = "human"
ASSISTANT_LABEL_SOURCE = "assistant_generated"
PROVISIONAL_LABEL_SOURCE = "provisional"
OFFICIAL_LABEL_SOURCES = frozenset({HUMAN_LABEL_SOURCE})


@dataclass(frozen=True)
class RiskRubric:
    version: str
    name: str
    description: str
    risk_model_version: str
    severity_bands: dict[str, dict[str, float]]
    metrics: list[str]


@dataclass(frozen=True)
class RiskGoldenCase:
    case_id: str
    correlation_key: str
    title: str
    severity: str
    expected_risk_score_min: float
    expected_risk_score_max: float
    label_source: LabelSource
    human_severity: str | None = None
    source_tools: list[str] = field(default_factory=list)
    verified_confidence: str = "medium"
    verification_status: str = "verified"
    exposure_score: float = 1.0
    cvss_score: float | None = None
    notes: str | None = None


@dataclass(frozen=True)
class RiskGoldenSet:
    version: str
    entries: list[RiskGoldenCase]


@dataclass(frozen=True)
class RiskCaseResult:
    case_id: str
    label_source: LabelSource
    included_in_official_metrics: bool
    predicted_severity: str
    predicted_risk_score: float
    human_severity: str | None
    severity_agreement: bool | None
    severity_band_compliance: bool | None
    false_severity: bool | None
    expected_risk_score_min: float | None = None
    expected_risk_score_max: float | None = None


@dataclass(frozen=True)
class RiskEvalReport:
    status: str
    rubric_version: str
    golden_set_version: str
    risk_model_version: str
    official_label_source: str
    human_labeled_count: int
    assistant_generated_count: int
    provisional_count: int
    severity_band_compliance_rate: float | None
    severity_agreement_rate: float | None
    false_severity_rate: float | None
    case_results: list[RiskCaseResult]
    message: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "rubric_version": self.rubric_version,
            "golden_set_version": self.golden_set_version,
            "risk_model_version": self.risk_model_version,
            "official_label_source": self.official_label_source,
            "human_labeled_count": self.human_labeled_count,
            "assistant_generated_count": self.assistant_generated_count,
            "provisional_count": self.provisional_count,
            "severity_band_compliance_rate": self.severity_band_compliance_rate,
            "severity_agreement_rate": self.severity_agreement_rate,
            "false_severity_rate": self.false_severity_rate,
            "case_results": [
                {
                    "case_id": item.case_id,
                    "label_source": item.label_source,
                    "included_in_official_metrics": item.included_in_official_metrics,
                    "predicted_severity": item.predicted_severity,
                    "predicted_risk_score": item.predicted_risk_score,
                    "human_severity": item.human_severity,
                    "severity_agreement": item.severity_agreement,
                    "severity_band_compliance": item.severity_band_compliance,
                    "false_severity": item.false_severity,
                    "expected_risk_score_min": item.expected_risk_score_min,
                    "expected_risk_score_max": item.expected_risk_score_max,
                }
                for item in self.case_results
            ],
            "message": self.message,
            "evaluated_at": datetime.now(UTC).isoformat(),
        }


def risk_engine_root() -> Path:
    return repo_benchmarks_root() / "risk-engine"


def load_rubric() -> RiskRubric:
    path = risk_engine_root() / "rubric.yaml"
    with path.open(encoding="utf-8") as stream:
        payload = yaml.safe_load(stream)
    return RiskRubric(
        version=str(payload["version"]),
        name=str(payload["name"]),
        description=str(payload.get("description", "")),
        risk_model_version=str(payload.get("risk_model_version", RISK_MODEL_VERSION)),
        severity_bands={
            key: {"min": float(value["min"]), "max": float(value["max"])}
            for key, value in (payload.get("severity_bands") or {}).items()
        },
        metrics=list(payload.get("metrics") or []),
    )


def load_golden_set() -> RiskGoldenSet:
    path = risk_engine_root() / "golden-set.yaml"
    with path.open(encoding="utf-8") as stream:
        payload = yaml.safe_load(stream)
    entries = [
        RiskGoldenCase(
            case_id=str(item["case_id"]),
            correlation_key=str(item["correlation_key"]),
            title=str(item["title"]),
            severity=str(item["severity"]),
            expected_risk_score_min=float(item["expected_risk_score_min"]),
            expected_risk_score_max=float(item["expected_risk_score_max"]),
            label_source=str(item.get("label_source", PROVISIONAL_LABEL_SOURCE)),  # type: ignore[arg-type]
            human_severity=item.get("human_severity"),
            source_tools=list(item.get("source_tools") or []),
            verified_confidence=str(item.get("verified_confidence", "medium")),
            verification_status=str(item.get("verification_status", "verified")),
            exposure_score=float(item.get("exposure_score", 1.0)),
            cvss_score=item.get("cvss_score"),
            notes=item.get("notes"),
        )
        for item in payload.get("entries") or []
    ]
    return RiskGoldenSet(version=str(payload["version"]), entries=entries)


def severity_band_for_score(rubric: RiskRubric, score: float) -> str | None:
    for severity, bounds in rubric.severity_bands.items():
        if bounds["min"] <= score <= bounds["max"]:
            return severity
    return None


def _finding_from_case(case: RiskGoldenCase) -> AnalyzedFinding:
    return AnalyzedFinding(
        correlation_key=case.correlation_key,
        title=case.title,
        description=case.notes or case.title,
        severity=case.severity,
        affected_url="https://benchmark.example/",
        source_tools=case.source_tools,
        verified_confidence=case.verified_confidence,
        verification_status=case.verification_status,
        exposure_score=case.exposure_score,
        cvss_score=case.cvss_score,
    )


def evaluate_case(case: RiskGoldenCase, rubric: RiskRubric) -> RiskCaseResult:
    finding = _finding_from_case(case)
    predicted_score = calculate_risk_score(finding)
    predicted_severity = case.severity
    official = case.label_source in OFFICIAL_LABEL_SOURCES

    severity_agreement: bool | None = None
    severity_band_compliance: bool | None = None
    false_severity: bool | None = None

    if official:
        reference_severity = case.human_severity or case.severity
        severity_agreement = predicted_severity == reference_severity
        severity_band_compliance = (
            case.expected_risk_score_min <= predicted_score <= case.expected_risk_score_max
        )
        predicted_band = severity_band_for_score(rubric, predicted_score)
        reference_band = severity_band_for_score(
            rubric,
            (case.expected_risk_score_min + case.expected_risk_score_max) / 2,
        )
        false_severity = predicted_band != reference_band

    return RiskCaseResult(
        case_id=case.case_id,
        label_source=case.label_source,
        included_in_official_metrics=official,
        predicted_severity=predicted_severity,
        predicted_risk_score=predicted_score,
        human_severity=case.human_severity or (case.severity if official else None),
        severity_agreement=severity_agreement,
        severity_band_compliance=severity_band_compliance,
        false_severity=false_severity,
        expected_risk_score_min=case.expected_risk_score_min if official else None,
        expected_risk_score_max=case.expected_risk_score_max if official else None,
    )


def _rate(values: list[bool | None]) -> float | None:
    measured = [value for value in values if value is not None]
    if not measured:
        return None
    return sum(1 for value in measured if value) / len(measured)


def evaluate_risk_engine() -> RiskEvalReport:
    rubric = load_rubric()
    golden = load_golden_set()
    case_results = [evaluate_case(case, rubric) for case in golden.entries]

    official_results = [item for item in case_results if item.included_in_official_metrics]
    human_count = len(official_results)
    assistant_count = sum(1 for item in case_results if item.label_source == ASSISTANT_LABEL_SOURCE)
    provisional_count = sum(1 for item in case_results if item.label_source == PROVISIONAL_LABEL_SOURCE)

    return RiskEvalReport(
        status="completed",
        rubric_version=rubric.version,
        golden_set_version=golden.version,
        risk_model_version=rubric.risk_model_version,
        official_label_source=HUMAN_LABEL_SOURCE,
        human_labeled_count=human_count,
        assistant_generated_count=assistant_count,
        provisional_count=provisional_count,
        severity_band_compliance_rate=_rate([item.severity_band_compliance for item in official_results]),
        severity_agreement_rate=_rate([item.severity_agreement for item in official_results]),
        false_severity_rate=_rate([item.false_severity for item in official_results]),
        case_results=case_results,
        message=(
            "Official metrics include human-labeled cases only; "
            "assistant-generated labels are excluded from official scoring."
        ),
    )


def write_risk_eval_report(report: RiskEvalReport, output_dir: Path | None = None) -> Path:
    root = output_dir or (repo_benchmarks_root() / "reports")
    root.mkdir(parents=True, exist_ok=True)
    path = root / "risk-engine-benchmark.json"
    path.write_text(json.dumps(report.as_dict(), indent=2, default=str), encoding="utf-8")
    return path


def run_risk_eval_cli() -> int:
    report = evaluate_risk_engine()
    path = write_risk_eval_report(report)
    print(json.dumps(report.as_dict(), indent=2))
    print(f"Report written to {path}")
    return 0
