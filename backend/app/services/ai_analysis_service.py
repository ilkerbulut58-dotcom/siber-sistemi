"""Finding AI enrichment — rule-based fallback + LLM (Phase 8)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.ai.data_masker import mask_evidence, mask_text
from app.ai.providers.factory import get_ai_provider
from app.ai.schemas import FindingAnalysisPayload
from app.data.finding_catalog_tr import SEVERITY_LABEL_TR
from app.models.finding import Finding

logger = logging.getLogger(__name__)


def enrich_finding_rule_based(finding: Finding) -> None:
    """Immediate rule-based enrichment so scans always have baseline AI fields."""
    sev_tr = SEVERITY_LABEL_TR.get(finding.severity, finding.severity)

    if finding.risk_explanation:
        finding.ai_summary = (
            f"{finding.title} — {sev_tr} risk. {finding.risk_explanation}"
        )
    else:
        finding.ai_summary = (
            f"{finding.title} — {sev_tr} önem derecesinde bir güvenlik bulgusu."
        )

    steps = finding.remediation_steps or []
    paths = finding.config_file_paths or []
    parts: list[str] = []

    if finding.remediation:
        parts.append(finding.remediation)

    if steps:
        parts.append("Adımlar: " + " → ".join(steps[:3]))

    if finding.config_snippet:
        parts.append(f"Eklenecek yapılandırma:\n{finding.config_snippet}")

    if paths:
        parts.append("Dosya/konum: " + paths[0])

    finding.ai_remediation = "\n\n".join(parts) if parts else (
        "İlgili yapılandırmayı gözden geçirin ve test ortamında doğrulayın."
    )
    finding.ai_confidence_label = "unverified"


def enrich_finding(finding: Finding) -> None:
    """Sync hook used during finding persistence — never blocks on network."""
    enrich_finding_rule_based(finding)


def build_analysis_payload(finding: Finding) -> FindingAnalysisPayload:
    return FindingAnalysisPayload(
        title=mask_text(finding.title) or finding.title,
        severity=finding.severity,
        affected_url=mask_text(finding.affected_url),
        correlation_key=finding.correlation_key,
        risk_score=finding.risk_score,
        cvss_score=finding.cvss_score,
        confidence=finding.confidence,
        verification_status=finding.verification_status,
        source_tools=list(finding.source_tools or []),
        risk_explanation=mask_text(finding.risk_explanation),
        remediation=mask_text(finding.remediation),
        remediation_steps=[mask_text(step) or step for step in (finding.remediation_steps or [])],
        config_snippet=mask_text(finding.config_snippet),
        config_file_paths=list(finding.config_file_paths or []),
        evidence_summary=mask_evidence(finding.evidence),
    )


async def enrich_finding_with_llm(finding: Finding) -> bool:
    """Call LLM provider; return True when AI fields were updated."""
    provider = get_ai_provider()
    if provider is None:
        return False

    payload = build_analysis_payload(finding)
    try:
        result = await provider.analyze_finding(payload)
    except Exception as exc:
        logger.warning("LLM enrichment failed for finding %s: %s", finding.id, exc)
        return False

    finding.ai_summary = result.summary
    finding.ai_remediation = result.remediation
    finding.ai_confidence_label = result.confidence_label
    return True


async def enrich_findings_with_llm(findings: list[Finding]) -> dict[str, Any]:
    """Batch LLM enrichment with bounded concurrency."""
    from app.core.config import get_settings

    settings = get_settings()
    provider = get_ai_provider()
    if provider is None or not findings:
        return {"total": len(findings), "enriched": 0, "skipped": len(findings)}

    semaphore = asyncio.Semaphore(max(1, settings.ai_max_concurrency))
    enriched = 0

    async def _one(finding: Finding) -> None:
        nonlocal enriched
        async with semaphore:
            if await enrich_finding_with_llm(finding):
                enriched += 1

    await asyncio.gather(*(_one(f) for f in findings))
    return {"total": len(findings), "enriched": enriched, "skipped": len(findings) - enriched}
