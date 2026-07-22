"""Finding localization tests."""

import pytest

from app.data.finding_catalog_tr import SEVERITY_LABEL_TR
from app.scanners.base import RawFinding
from app.services.finding_localization_service import localize_raw_finding


def test_localize_hsts_finding_turkish():
    raw = RawFinding(
        source_tool="passive_http",
        source_rule_id="missing-header-strict-transport-security",
        title="Missing Strict-Transport-Security header",
        description="English description",
        severity="medium",
        affected_url="https://turbridge.de/",
    )
    localize_raw_finding(raw)
    assert "HSTS" in raw.title or "HTTPS" in raw.title
    assert raw.risk_explanation
    assert raw.remediation_steps
    assert raw.config_snippet
    assert any("turbridge.de" in p for p in (raw.config_file_paths or []))
    assert raw.evidence.get("severity_label_tr") == SEVERITY_LABEL_TR["medium"]
