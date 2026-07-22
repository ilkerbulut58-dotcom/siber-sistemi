"""Build sanitized Finding API responses."""

from __future__ import annotations

from app.analysis.risk_engine import RISK_MODEL_VERSION, build_risk_breakdown
from app.analysis.types import AnalyzedFinding
from app.models.finding import Finding
from app.schemas.finding import FindingResponse, RiskBreakdownResponse
from app.security.evidence_sanitizer import sanitize_evidence_dict, sanitize_text


def _analyzed_from_finding(finding: Finding) -> AnalyzedFinding:
    return AnalyzedFinding(
        correlation_key=finding.correlation_key or finding.source_rule_id or "unknown",
        title=finding.title,
        description=finding.description or "",
        severity=finding.severity,
        affected_url=finding.affected_url or "",
        remediation=finding.remediation,
        confidence=finding.confidence or "medium",
        evidence=finding.evidence or {},
        source_tools=list(finding.source_tools or [finding.source_tool]),
        source_rule_ids=[finding.source_rule_id or ""],
        risk_explanation=finding.risk_explanation,
        remediation_steps=finding.remediation_steps,
        config_file_paths=finding.config_file_paths,
        config_snippet=finding.config_snippet,
        cvss_score=finding.cvss_score,
        verified_confidence=finding.confidence or "medium",
        verification_status=finding.verification_status or "unverified",
        verification_notes=finding.verification_notes,
        risk_score=finding.risk_score or 0.0,
    )


def resolve_risk_breakdown(finding: Finding) -> RiskBreakdownResponse | None:
    if finding.risk_breakdown and isinstance(finding.risk_breakdown, dict):
        return RiskBreakdownResponse.model_validate(finding.risk_breakdown)
    if finding.risk_score is None:
        return None
    analyzed = _analyzed_from_finding(finding)
    return RiskBreakdownResponse.model_validate(build_risk_breakdown(analyzed))


def to_finding_response(finding: Finding) -> FindingResponse:
    breakdown = resolve_risk_breakdown(finding)
    return FindingResponse(
        id=finding.id,
        organization_id=finding.organization_id,
        project_id=finding.project_id,
        scan_job_id=finding.scan_job_id,
        source_tool=finding.source_tool,
        source_rule_id=finding.source_rule_id,
        title=finding.title,
        description=sanitize_text(finding.description),
        affected_url=sanitize_text(finding.affected_url),
        severity=finding.severity,
        confidence=finding.confidence,
        correlation_key=finding.correlation_key,
        risk_score=finding.risk_score,
        cvss_score=finding.cvss_score,
        source_tools=finding.source_tools,
        verification_status=finding.verification_status,
        verification_notes=sanitize_text(finding.verification_notes),
        evidence=sanitize_evidence_dict(finding.evidence),
        status=finding.status,
        remediation=sanitize_text(finding.remediation),
        risk_explanation=sanitize_text(finding.risk_explanation),
        remediation_steps=(
            [sanitize_text(s) or s for s in finding.remediation_steps]
            if finding.remediation_steps
            else None
        ),
        config_file_paths=finding.config_file_paths,
        config_snippet=sanitize_text(finding.config_snippet),
        reviewer_notes=sanitize_text(finding.reviewer_notes),
        ai_summary=sanitize_text(finding.ai_summary),
        ai_remediation=sanitize_text(finding.ai_remediation),
        ai_confidence_label=finding.ai_confidence_label,
        risk_breakdown=breakdown,
        risk_model_version=finding.risk_model_version or RISK_MODEL_VERSION,
        asset_type=finding.asset_type,
        platform=finding.platform,
        masvs_category=finding.masvs_category,
        affected_component=sanitize_text(finding.affected_component),
        mobile_application_id=finding.mobile_application_id,
        first_seen_at=finding.first_seen_at,
        last_seen_at=finding.last_seen_at,
        created_at=finding.created_at,
        updated_at=finding.updated_at,
    )
