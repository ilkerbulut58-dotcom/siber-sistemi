"""AI remediation golden-set evaluation — human labels official, LLM auxiliary only."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import yaml

from app.benchmark.manifests import repo_benchmarks_root

LabelSource = Literal["human", "assistant_generated", "provisional"]
HUMAN_LABEL_SOURCE = "human"
ASSISTANT_LABEL_SOURCE = "assistant_generated"
PROVISIONAL_LABEL_SOURCE = "provisional"
RUBRIC_DIMENSIONS = (
    "technical_accuracy",
    "applicability",
    "security",
    "clarity",
    "tech_fit",
)


@dataclass(frozen=True)
class AiRemediationRubric:
    version: str
    name: str
    description: str
    dimensions: dict[str, dict[str, Any]]
    llm_eval_auxiliary: bool
    provisional_without_human_labels: bool


@dataclass(frozen=True)
class AiRemediationCase:
    case_id: str
    finding_key: str
    stack: str
    remediation_text: str
    label_source: LabelSource
    human_scores: dict[str, float] = field(default_factory=dict)
    llm_scores: dict[str, float] = field(default_factory=dict)
    notes: str | None = None


@dataclass(frozen=True)
class AiRemediationGoldenSet:
    version: str
    entries: list[AiRemediationCase]


@dataclass(frozen=True)
class AiRemediationCaseResult:
    case_id: str
    label_source: LabelSource
    provisional: bool
    official_scores: dict[str, float]
    auxiliary_llm_scores: dict[str, float]
    dimension_averages: dict[str, float | None]
    overall_score: float | None


@dataclass(frozen=True)
class AiRemediationEvalReport:
    status: str
    rubric_version: str
    golden_set_version: str
    human_labeled_count: int
    provisional_count: int
    assistant_generated_count: int
    llm_eval_auxiliary: bool
    dimension_averages: dict[str, float | None]
    overall_score: float | None
    case_results: list[AiRemediationCaseResult]
    message: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "rubric_version": self.rubric_version,
            "golden_set_version": self.golden_set_version,
            "human_labeled_count": self.human_labeled_count,
            "provisional_count": self.provisional_count,
            "assistant_generated_count": self.assistant_generated_count,
            "llm_eval_auxiliary": self.llm_eval_auxiliary,
            "dimension_averages": self.dimension_averages,
            "overall_score": self.overall_score,
            "case_results": [
                {
                    "case_id": item.case_id,
                    "label_source": item.label_source,
                    "provisional": item.provisional,
                    "official_scores": item.official_scores,
                    "auxiliary_llm_scores": item.auxiliary_llm_scores,
                    "dimension_averages": item.dimension_averages,
                    "overall_score": item.overall_score,
                }
                for item in self.case_results
            ],
            "message": self.message,
            "evaluated_at": datetime.now(UTC).isoformat(),
        }


def ai_remediation_root() -> Path:
    return repo_benchmarks_root() / "ai-remediation"


def load_rubric() -> AiRemediationRubric:
    path = ai_remediation_root() / "rubric.yaml"
    with path.open(encoding="utf-8") as stream:
        payload = yaml.safe_load(stream)
    return AiRemediationRubric(
        version=str(payload["version"]),
        name=str(payload["name"]),
        description=str(payload.get("description", "")),
        dimensions={
            key: {
                "weight": float(value["weight"]),
                "description": str(value.get("description", "")),
                "scale_min": float(value.get("scale_min", 1)),
                "scale_max": float(value.get("scale_max", 5)),
            }
            for key, value in (payload.get("dimensions") or {}).items()
        },
        llm_eval_auxiliary=bool(payload.get("llm_eval_auxiliary", True)),
        provisional_without_human_labels=bool(payload.get("provisional_without_human_labels", True)),
    )


def load_golden_set() -> AiRemediationGoldenSet:
    path = ai_remediation_root() / "golden-set.yaml"
    with path.open(encoding="utf-8") as stream:
        payload = yaml.safe_load(stream)
    entries = [
        AiRemediationCase(
            case_id=str(item["case_id"]),
            finding_key=str(item["finding_key"]),
            stack=str(item.get("stack", "generic")),
            remediation_text=str(item["remediation_text"]),
            label_source=str(item.get("label_source", PROVISIONAL_LABEL_SOURCE)),  # type: ignore[arg-type]
            human_scores={key: float(value) for key, value in (item.get("human_scores") or {}).items()},
            llm_scores={key: float(value) for key, value in (item.get("llm_scores") or {}).items()},
            notes=item.get("notes"),
        )
        for item in payload.get("entries") or []
    ]
    return AiRemediationGoldenSet(version=str(payload["version"]), entries=entries)


def _weighted_average(scores: dict[str, float], rubric: AiRemediationRubric) -> float | None:
    total_weight = 0.0
    weighted_sum = 0.0
    for dimension, config in rubric.dimensions.items():
        if dimension not in scores:
            continue
        weight = float(config["weight"])
        weighted_sum += scores[dimension] * weight
        total_weight += weight
    if total_weight == 0:
        return None
    return round(weighted_sum / total_weight, 3)


def evaluate_case(case: AiRemediationCase, rubric: AiRemediationRubric) -> AiRemediationCaseResult:
    official_scores = case.human_scores if case.label_source == HUMAN_LABEL_SOURCE else {}
    auxiliary_llm_scores = case.llm_scores if rubric.llm_eval_auxiliary else {}
    provisional = (
        rubric.provisional_without_human_labels
        and (case.label_source != HUMAN_LABEL_SOURCE or not official_scores)
    )

    dimension_averages = {
        dimension: official_scores.get(dimension)
        for dimension in RUBRIC_DIMENSIONS
        if dimension in rubric.dimensions
    }
    overall = _weighted_average(official_scores, rubric) if official_scores else None

    return AiRemediationCaseResult(
        case_id=case.case_id,
        label_source=case.label_source,
        provisional=provisional,
        official_scores=official_scores,
        auxiliary_llm_scores=auxiliary_llm_scores,
        dimension_averages=dimension_averages,
        overall_score=overall,
    )


def _aggregate_dimension_averages(
    results: list[AiRemediationCaseResult],
    *,
    official_only: bool,
) -> dict[str, float | None]:
    output: dict[str, float | None] = {}
    for dimension in RUBRIC_DIMENSIONS:
        values = [
            item.dimension_averages.get(dimension)
            for item in results
            if item.dimension_averages.get(dimension) is not None
            and (not official_only or (not item.provisional and item.official_scores))
        ]
        values = [value for value in values if value is not None]
        output[dimension] = round(sum(values) / len(values), 3) if values else None
    return output


def evaluate_ai_remediation() -> AiRemediationEvalReport:
    rubric = load_rubric()
    golden = load_golden_set()
    case_results = [evaluate_case(case, rubric) for case in golden.entries]

    official_results = [item for item in case_results if not item.provisional and item.official_scores]
    overall_scores = [item.overall_score for item in official_results if item.overall_score is not None]

    return AiRemediationEvalReport(
        status="completed",
        rubric_version=rubric.version,
        golden_set_version=golden.version,
        human_labeled_count=sum(1 for item in case_results if item.label_source == HUMAN_LABEL_SOURCE),
        provisional_count=sum(1 for item in case_results if item.provisional),
        assistant_generated_count=sum(
            1 for item in case_results if item.label_source == ASSISTANT_LABEL_SOURCE
        ),
        llm_eval_auxiliary=rubric.llm_eval_auxiliary,
        dimension_averages=_aggregate_dimension_averages(case_results, official_only=True),
        overall_score=round(sum(overall_scores) / len(overall_scores), 3) if overall_scores else None,
        case_results=case_results,
        message=(
            "Official remediation scores use human labels only; "
            "LLM scores are auxiliary and provisional cases are excluded from official aggregates."
        ),
    )


def write_ai_remediation_report(report: AiRemediationEvalReport, output_dir: Path | None = None) -> Path:
    root = output_dir or (repo_benchmarks_root() / "reports")
    root.mkdir(parents=True, exist_ok=True)
    path = root / "ai-remediation-benchmark.json"
    path.write_text(json.dumps(report.as_dict(), indent=2, default=str), encoding="utf-8")
    return path


def run_ai_remediation_eval_cli() -> int:
    report = evaluate_ai_remediation()
    path = write_ai_remediation_report(report)
    print(json.dumps(report.as_dict(), indent=2))
    print(f"Report written to {path}")
    return 0
