"""Customer-visible finding validation layer (does not mutate benchmark raw results)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.analysis.correlation_rules import resolve_correlation_key, secret_identity_token
from app.scanners.base import RawFinding
from app.utils.url_canonicalization import canonicalize_url

# Header and site-wide misconfigurations are target-scoped, not URL-instance scoped.
_SITE_WIDE_CORRELATION_KEYS = frozenset(
    {
        "server-disclosure",
        "x-powered-by-disclosure",
        "permissive-cors",
        "info-modern-web-app",
    }
)

_SOURCE_TOOL_PRIORITY = {
    "passive_http": 0,
    "zap": 1,
    "nuclei": 2,
    "code_scan": 3,
    "deep_scan": 4,
    "tls_check": 5,
}

_CONFIDENCE_RANK = {"high": 3, "medium": 2, "low": 1}


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
    return bool(
        evidence.get("missing_header")
        or evidence.get("allow_origin")
        or evidence.get("server")
        or evidence.get("x_powered_by")
    )


def _has_openapi_evidence(raw: RawFinding) -> bool:
    evidence = raw.evidence or {}
    paths = evidence.get("discovered_paths")
    return isinstance(paths, list) and len(paths) > 0


def _has_dedup_evidence(raw: RawFinding) -> bool:
    evidence = raw.evidence or {}
    return bool(evidence.get("dedup_fingerprint"))


def _normalized_confidence(raw: RawFinding) -> str:
    return (raw.confidence or "medium").lower()


def _confidence_rank(confidence: str) -> int:
    return _CONFIDENCE_RANK.get(confidence.lower(), 0)


def _is_site_wide_correlation(correlation_key: str) -> bool:
    return correlation_key.startswith("missing-header-") or correlation_key in _SITE_WIDE_CORRELATION_KEYS


def _customer_validation_group_key(raw: RawFinding) -> str:
    correlation_key = resolve_correlation_key(raw.source_tool, raw.source_rule_id, raw.title)
    secret_token = secret_identity_token(correlation_key, raw.evidence)
    if secret_token:
        return f"{correlation_key}:{secret_token}"
    if _is_site_wide_correlation(correlation_key):
        return correlation_key
    return f"{correlation_key}:{canonicalize_url(raw.affected_url)}"


def _merge_evidence(items: list[RawFinding]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    affected_endpoints: set[str] = set()
    instance_count = 0
    for item in items:
        evidence = item.evidence or {}
        for key, value in evidence.items():
            if key == "affected_endpoints" and isinstance(value, list):
                affected_endpoints.update(str(url) for url in value if url)
            elif key == "instance_count":
                instance_count += int(value or 0)
            elif key not in merged or not merged[key]:
                merged[key] = value
        if item.affected_url:
            affected_endpoints.add(canonicalize_url(item.affected_url))
    if affected_endpoints:
        merged["affected_endpoints"] = sorted(affected_endpoints)
    if instance_count > 0:
        merged["instance_count"] = instance_count
    return merged


def _pick_validation_primary(items: list[RawFinding]) -> RawFinding:
    for preferred in _SOURCE_TOOL_PRIORITY:
        for item in items:
            if item.source_tool == preferred:
                return item
    return items[0]


def _best_confidence(items: list[RawFinding]) -> str:
    ranked = sorted(items, key=lambda item: _confidence_rank(_normalized_confidence(item)), reverse=True)
    return _normalized_confidence(ranked[0])


def _canonical_representative_url(items: list[RawFinding]) -> str:
    urls = sorted({canonicalize_url(item.affected_url) for item in items if item.affected_url})
    return urls[0] if urls else items[0].affected_url


def _merge_findings_for_validation(items: list[RawFinding]) -> RawFinding:
    ordered = sorted(
        items,
        key=lambda item: (
            _SOURCE_TOOL_PRIORITY.get(item.source_tool, 99),
            canonicalize_url(item.affected_url),
            item.source_rule_id,
        ),
    )
    primary = _pick_validation_primary(ordered)
    merged_evidence = _merge_evidence(ordered)
    return RawFinding(
        source_tool=primary.source_tool,
        source_rule_id=primary.source_rule_id,
        title=primary.title,
        description=primary.description,
        severity=primary.severity,
        affected_url=_canonical_representative_url(ordered),
        remediation=primary.remediation,
        confidence=_best_confidence(ordered),
        evidence=merged_evidence,
        risk_explanation=primary.risk_explanation,
        remediation_steps=primary.remediation_steps,
        config_file_paths=primary.config_file_paths,
        config_snippet=primary.config_snippet,
    )


def _group_findings_for_validation(raw_findings: list[RawFinding]) -> list[tuple[str, RawFinding, list[RawFinding]]]:
    buckets: dict[str, list[RawFinding]] = {}
    for raw in raw_findings:
        buckets.setdefault(_customer_validation_group_key(raw), []).append(raw)
    grouped: list[tuple[str, RawFinding, list[RawFinding]]] = []
    for group_key in sorted(buckets):
        members = buckets[group_key]
        grouped.append((group_key, _merge_findings_for_validation(members), members))
    return grouped


def _group_has_passive_http_header_confirmation(items: list[RawFinding]) -> bool:
    return any(
        item.source_tool == "passive_http"
        and item.source_rule_id.lower().startswith("missing-header-")
        and _normalized_confidence(item) in {"high", "medium"}
        for item in items
    )


def validate_raw_finding(raw: RawFinding, *, group_members: list[RawFinding] | None = None) -> ValidationDecision:
    validators_passed: list[str] = []
    rule = raw.source_rule_id.lower()
    confidence = _normalized_confidence(raw)
    severity = (raw.severity or "info").lower()
    members = group_members or [raw]
    passive_http_header_confirmed = _group_has_passive_http_header_confirmation(members)

    if rule.startswith("missing-header-") and (
        _has_header_evidence(raw)
        or (raw.source_tool == "passive_http" and confidence in {"high", "medium"})
        or passive_http_header_confirmed
    ):
        validators_passed.append(
            "header_evidence"
            if _has_header_evidence(raw)
            else "scanner_response_inspection"
        )
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

    grouped = _group_findings_for_validation(raw_findings)
    for index, (_group_key, merged, members) in enumerate(grouped):
        decision = validate_raw_finding(merged, group_members=members)
        by_visibility[decision.visibility] += 1
        child_evidence = {}
        if merged.evidence:
            if merged.evidence.get("affected_endpoints"):
                child_evidence["affected_endpoints"] = merged.evidence["affected_endpoints"]
            if merged.evidence.get("instance_count"):
                child_evidence["instance_count"] = merged.evidence["instance_count"]
        views.append(
            CustomerFindingView(
                source_tool=merged.source_tool,
                source_rule_id=merged.source_rule_id,
                title=merged.title,
                severity=merged.severity,
                affected_url=merged.affected_url,
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
                    "source_rule_id": merged.source_rule_id,
                    "affected_url": merged.affected_url,
                    "visibility": decision.visibility,
                    "reason": decision.reason,
                    "validators_failed": decision.validators_failed,
                }
            )

    suppressions.sort(key=lambda item: (item["source_rule_id"], item["affected_url"], item["visibility"]))
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


def canonical_validation_snapshot(raw_findings: list[RawFinding]) -> dict[str, Any]:
    """Deterministic JSON-serializable snapshot for order-independence regression tests."""
    artifact = build_customer_validation_artifact(raw_findings)
    return {
        "customer_visible_count": artifact.customer_visible_count,
        "by_visibility": artifact.by_visibility,
        "findings": [
            {
                "source_rule_id": view.source_rule_id,
                "affected_url": view.affected_url,
                "visibility": view.visibility.value,
                "validation_reason": view.validation_reason,
                "validators_passed": view.validators_passed,
                "child_evidence": view.child_evidence,
            }
            for view in artifact.findings
        ],
        "suppressions": artifact.suppressions,
    }
