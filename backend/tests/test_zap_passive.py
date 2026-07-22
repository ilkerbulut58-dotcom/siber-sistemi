"""ZAP passive scanner tests."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.scanners.zap_passive import _alerts_to_findings, run_zap_passive_scan


def test_alerts_to_findings_deduplicates() -> None:
    alerts = [
        {
            "pluginId": "10021",
            "name": "Missing Header",
            "risk": "Low",
            "url": "https://example.com/",
            "description": "X-Frame-Options missing",
            "solution": "Set header",
        },
        {
            "pluginId": "10021",
            "name": "Missing Header",
            "risk": "Low",
            "url": "https://example.com/",
            "description": "duplicate",
        },
    ]
    findings = _alerts_to_findings(alerts)
    assert len(findings) == 1
    assert findings[0].source_tool == "zap"
    assert findings[0].source_rule_id == "zap-10021"
    assert findings[0].severity == "low"


@pytest.mark.asyncio
async def test_zap_skips_when_unreachable() -> None:
    with patch("app.scanners.zap_passive._zap_reachable", new_callable=AsyncMock, return_value=False):
        findings = await run_zap_passive_scan("https://example.com")
    assert findings == []


@pytest.mark.asyncio
async def test_zap_passive_scan_parses_alerts() -> None:
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    async def fake_api_get(_client, path: str, **params: str | int) -> dict:
        if path.endswith("newSession/"):
            return {"Result": "OK"}
        if path.endswith("accessUrl/"):
            return {"Result": "OK"}
        if path.endswith("recordsToScan/"):
            return {"recordsToScan": "0"}
        if path.endswith("alerts/"):
            return {
                "alerts": [
                    {
                        "pluginId": "10020",
                        "name": "X-Frame-Options Header Not Set",
                        "risk": "Medium",
                        "url": "https://example.com/",
                        "description": "Clickjacking protection missing",
                        "solution": "Set X-Frame-Options",
                    }
                ]
            }
        return {}

    with (
        patch("app.scanners.zap_passive._zap_reachable", new_callable=AsyncMock, return_value=True),
        patch("httpx.AsyncClient", return_value=mock_client),
        patch("app.scanners.zap_passive._api_get", side_effect=fake_api_get),
    ):
        findings = await run_zap_passive_scan("https://example.com", spider=False)

    assert len(findings) == 1
    assert findings[0].title == "X-Frame-Options Header Not Set"
    assert findings[0].severity == "medium"
