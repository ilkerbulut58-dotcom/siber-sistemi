"""Customer-visible finding validation layer (does not mutate benchmark raw results)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.scanners.base import RawFinding


class CustomerVisibility(StrEnum):
    CONFIRMED = "confirmed"
    HIGH_CONFIDENCE = "high_confidence"
    NEEDS_REVIEW = "needs_review"
    INFORMATIONAL = "informational"


@dataclass(frozen=True)
class ValidationDecision:
    visibility: CustomerVisibility
    reason: str
    validators_passed: list[str] = field(default_factory=list)
    validators_failed: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CustomerFindingView:
    source_tool: str
    source_rule_id: str
    title: str
    severity: str
    affected_url: str
    visibility: CustomerVisibility
    validation_reason: str
    validators_passed: list[str]
    child_evidence: dict[str, Any] = field(default_factory=dict)
    raw_finding_index: int = 0


@dataclass(frozen=True)
class ValidationArtifact:
    raw_finding_count: int
    customer_visible_count: int
    by_visibility: dict[str, int]
    suppressions: list[dict[str, Any]]
    findings: list[CustomerFindingView]


def _has_header_evidence(raw: RawFinding) -> bool:
    evidence = raw.evidence or {}
    return bool(evidence.get("missing_header") or evidence.get("allow_origin") or evidence.get("server"))


def _has_openapi_evidence(raw: RawFinding) -> bool:
    evidence = raw.evidence or {}
    paths = evidence.get("discovered_paths")
    return isinstance(paths, list) and len(paths) > 0


def _has_dedup_evidence(raw: RawFinding) -> bool:
    evidence = raw.evidence or {}
    return bool(evidence.get("dedup_fingerprint"))


def validate_raw_finding(raw: RawFinding) -> ValidationDecision:
    validators_passed: list[str] = []
    rule = raw.source_rule_id.lower()
    confidence = (raw.confidence or "medium").lower()
    severity = (raw.severity or "info").lower()

    if rule.startswith("missing-header-") and _has_header_evidence(raw):
        validators_passed.append("header_evidence")
        return ValidationDecision(
            CustomerVisibility.CONFIRMED,
            "Missing security header confirmed by response inspection.",
            validators_passed=validators_passed,
        )

    if rule == "permissive-cors" and _has_header_evidence(raw):
        validators_passed.extend(["cors_preflight_response", "header_evidence"])
        return ValidationDecision(
            CustomerVisibility.CONFIRMED,
            "Permissive CORS confirmed by reproducible OPTIONS preflight.",
            validators_passed=validators_passed,
        )

    if rule == "exposed-api-docs" and _has_openapi_evidence(raw):
        validators_passed.append("openapi_body_signature")
        return ValidationDecision(
            CustomerVisibility.CONFIRMED,
            "OpenAPI/Swagger exposure confirmed by body signature.",
            validators_passed=validators_passed,
        )

    if rule in {"server-disclosure", "x-powered-by-disclosure"} and _has_header_evidence(raw):
        validators_passed.append("header_evidence")
        return ValidationDecision(
            CustomerVisibility.HIGH_CONFIDENCE,
            "Header disclosure confirmed; lower customer impact.",
            validators_passed=validators_passed,
        )

    if severity == "info":
        return ValidationDecision(
            CustomerVisibility.INFORMATIONAL,
            "Informational severity excluded from customer risk aggregates.",
            validators_passed=["informational_severity"],
        )

    if confidence == "high" and _has_dedup_evidence(raw):
        validators_passed.append("scanner_confidence")
        return ValidationDecision(
            CustomerVisibility.HIGH_CONFIDENCE,
            "High scanner confidence with canonical dedup fingerprint.",
            validators_passed=validators_passed,
        )

    if confidence in {"medium", "high"}:
        return ValidationDecision(
            CustomerVisibility.NEEDS_REVIEW,
            "Insufficient independent validator evidence for automatic customer publication.",
            validators_failed=["independent_validator_missing"],
        )

    return ValidationDecision(
        CustomerVisibility.NEEDS_REVIEW,
        "Low confidence finding requires manual review before customer publication.",
        validators_failed=["low_confidence"],
    )


def build_customer_validation_artifact(raw_findings: list[RawFinding]) -> ValidationArtifact:
    views: list[CustomerFindingView] = []
    suppressions: list[dict[str, Any]] = []
    by_visibility: dict[str, int] = {
        CustomerVisibility.CONFIRMED: 0,
        CustomerVisibility.HIGH_CONFIDENCE: 0,
        CustomerVisibility.NEEDS_REVIEW: 0,
        CustomerVisibility.INFORMATIONAL: 0,
    }

    for index, raw in enumerate(raw_findings):
        decision = validate_raw_finding(raw)
        by_visibility[decision.visibility] += 1
        child_evidence = {}
        if raw.evidence:
            if raw.evidence.get("affected_endpoints"):
                child_evidence["affected_endpoints"] = raw.evidence["affected_endpoints"]
            if raw.evidence.get("instance_count"):
                child_evidence["instance_count"] = raw.evidence["instance_count"]
        views.append(
            CustomerFindingView(
                source_tool=raw.source_tool,
                source_rule_id=raw.source_rule_id,
                title=raw.title,
                severity=raw.severity,
                affected_url=raw.affected_url,
                visibility=decision.visibility,
                validation_reason=decision.reason,
                validators_passed=list(decision.validators_passed),
                child_evidence=child_evidence,
                raw_finding_index=index,
            )
        )
        if decision.visibility in {CustomerVisibility.NEEDS_REVIEW, CustomerVisibility.INFORMATIONAL}:
            suppressions.append(
                {
                    "source_rule_id": raw.source_rule_id,
                    "affected_url": raw.affected_url,
                    "visibility": decision.visibility,
                    "reason": decision.reason,
                    "validators_failed": decision.validators_failed,
                }
            )

    customer_visible = by_visibility[CustomerVisibility.CONFIRMED] + by_visibility[CustomerVisibility.HIGH_CONFIDENCE]
    return ValidationArtifact(
        raw_finding_count=len(raw_findings),
        customer_visible_count=customer_visible,
        by_visibility={key.value: value for key, value in by_visibility.items()},
        suppressions=suppressions,
        findings=views,
    )


def compute_customer_visible_metrics(
    *,
    true_positive_count: int,
    false_negative_count: int,
    raw_findings: list[RawFinding],
) -> dict[str, float | int]:
    """Precision/recall using customer-publication visibility (confirmed + high-confidence only)."""
    artifact = build_customer_validation_artifact(raw_findings)
    visible = artifact.customer_visible_count
    customer_confirmed_fp = max(0, visible - true_positive_count)
    precision_denom = true_positive_count + customer_confirmed_fp
    recall_denom = true_positive_count + false_negative_count
    precision = true_positive_count / precision_denom if precision_denom else 0.0
    recall = true_positive_count / recall_denom if recall_denom else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {
        "true_positive_count": true_positive_count,
        "false_negative_count": false_negative_count,
        "customer_visible_count": visible,
        "customer_confirmed_false_positive_count": customer_confirmed_fp,
        "customer_needs_review_count": artifact.by_visibility.get("needs_review", 0),
        "customer_informational_count": artifact.by_visibility.get("informational", 0),
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1_score": round(f1, 3),
    }
