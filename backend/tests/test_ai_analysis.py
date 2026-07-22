"""Tests for AI analysis layer (Phase 8)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.ai.data_masker import mask_evidence, mask_text
from app.ai.providers.factory import get_ai_provider
from app.ai.schemas import AIAnalysisResult
from app.core.config import get_settings
from app.models.finding import Finding
from app.services.ai_analysis_service import (
    build_analysis_payload,
    enrich_finding_rule_based,
    enrich_finding_with_llm,
)


@pytest.fixture(autouse=True)
def clear_ai_caches() -> None:
    get_settings.cache_clear()
    get_ai_provider.cache_clear()


def test_mask_text_redacts_jwt() -> None:
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIn0.sig"
    assert "[REDACTED_JWT]" in mask_text(f"Bearer {token}")  # type: ignore[arg-type]


def test_mask_evidence_redacts_sensitive_headers() -> None:
    summary = mask_evidence(
        {
            "headers": {
                "Authorization": "Bearer secret",
                "X-Frame-Options": "DENY",
            }
        }
    )
    assert summary is not None
    assert "[REDACTED]" in summary
    assert "DENY" in summary


def test_rule_based_enrichment_sets_unverified() -> None:
    finding = Finding(
        id=uuid4(),
        organization_id=uuid4(),
        project_id=uuid4(),
        scan_job_id=uuid4(),
        source_tool="passive_http",
        title="Missing HSTS",
        severity="medium",
        fingerprint="abc",
        risk_explanation="HTTPS zorunluluğu yok.",
        remediation="HSTS başlığı ekleyin.",
    )
    enrich_finding_rule_based(finding)
    assert finding.ai_summary
    assert "Missing HSTS" in finding.ai_summary
    assert finding.ai_confidence_label == "unverified"


@pytest.mark.asyncio
async def test_llm_enrichment_updates_fields() -> None:
    finding = Finding(
        id=uuid4(),
        organization_id=uuid4(),
        project_id=uuid4(),
        scan_job_id=uuid4(),
        source_tool="passive_http",
        title="Missing HSTS",
        severity="medium",
        fingerprint="abc",
        risk_explanation="HTTPS zorunluluğu yok.",
    )

    mock_result = AIAnalysisResult(
        summary="HSTS eksikliği orta seviye bir risk oluşturur.",
        remediation="1. Plesk panelinden HSTS etkinleştirin.",
        confidence_label="verified",
    )

    mock_provider = AsyncMock()
    mock_provider.analyze_finding = AsyncMock(return_value=mock_result)

    with patch("app.services.ai_analysis_service.get_ai_provider", return_value=mock_provider):
        ok = await enrich_finding_with_llm(finding)

    assert ok is True
    assert finding.ai_summary == mock_result.summary
    assert finding.ai_remediation == mock_result.remediation
    assert finding.ai_confidence_label == "verified"


@pytest.mark.asyncio
async def test_llm_enrichment_falls_back_on_error() -> None:
    finding = Finding(
        id=uuid4(),
        organization_id=uuid4(),
        project_id=uuid4(),
        scan_job_id=uuid4(),
        source_tool="passive_http",
        title="Missing HSTS",
        severity="medium",
        fingerprint="abc",
        ai_summary="existing",
        ai_confidence_label="unverified",
    )

    mock_provider = AsyncMock()
    mock_provider.analyze_finding = AsyncMock(side_effect=RuntimeError("API down"))

    with patch("app.services.ai_analysis_service.get_ai_provider", return_value=mock_provider):
        ok = await enrich_finding_with_llm(finding)

    assert ok is False
    assert finding.ai_summary == "existing"


def test_build_analysis_payload_masks_evidence() -> None:
    finding = Finding(
        id=uuid4(),
        organization_id=uuid4(),
        project_id=uuid4(),
        scan_job_id=uuid4(),
        source_tool="passive_http",
        title="Test",
        severity="low",
        fingerprint="abc",
        evidence={"headers": {"Cookie": "session=secret123"}},
    )
    payload = build_analysis_payload(finding)
    assert payload.evidence_summary
    assert "[REDACTED]" in payload.evidence_summary


@pytest.mark.asyncio
async def test_dispatch_skips_when_ai_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_ENABLED", "false")
    get_settings.cache_clear()

    from app.services.ai_dispatch import dispatch_ai_enrichment

    with patch("app.tasks.ai_tasks.enrich_scan_findings_task") as mock_task:
        await dispatch_ai_enrichment(uuid4())
        mock_task.delay.assert_not_called()
