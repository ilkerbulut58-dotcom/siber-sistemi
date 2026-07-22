"""Deep and code scan profile tests."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.core.config import get_settings
from app.scanners.orchestrator import run_scan_for_profile


@pytest.mark.asyncio
async def test_deep_profile_runs_extended_checks() -> None:
    passive = [
        type("F", (), {"source_rule_id": "missing-header-csp"})(),
    ]
    crawl = [
        type("F", (), {"source_rule_id": "crawl-5xx"})(),
    ]
    exposed = [
        type("F", (), {"source_rule_id": "exposed-env-file"})(),
    ]

    with (
        patch(
            "app.scanners.orchestrator.run_passive_http_scan",
            new_callable=AsyncMock,
            return_value=passive,
        ) as mock_passive,
        patch(
            "app.scanners.orchestrator.run_surface_crawl_passive",
            new_callable=AsyncMock,
            return_value=crawl,
        ) as mock_crawl,
        patch(
            "app.scanners.orchestrator.scan_exposed_paths",
            new_callable=AsyncMock,
            return_value=exposed,
        ) as mock_exposed,
        patch(
            "app.scanners.orchestrator.run_nuclei_scan",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_nuclei,
        patch(
            "app.scanners.orchestrator.run_zap_passive_scan",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_zap,
    ):
        findings = await run_scan_for_profile("https://example.com", "deep")

    mock_passive.assert_awaited_once()
    mock_crawl.assert_awaited_once()
    mock_exposed.assert_awaited_once()
    mock_zap.assert_awaited_once()
    mock_nuclei.assert_awaited_once()
    assert len(findings) == 3


@pytest.mark.asyncio
async def test_code_profile_runs_code_checks() -> None:
    with (
        patch(
            "app.scanners.orchestrator.run_passive_http_scan",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_passive,
        patch(
            "app.scanners.orchestrator.scan_exposed_paths",
            new_callable=AsyncMock,
            return_value=[type("F", (), {"source_rule_id": "exposed-git-head"})()],
        ) as mock_exposed,
        patch(
            "app.scanners.orchestrator.scan_response_secrets",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_secrets,
        patch(
            "app.scanners.orchestrator.run_nuclei_scan",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_nuclei,
    ):
        findings = await run_scan_for_profile("https://example.com", "code")

    mock_passive.assert_awaited_once()
    mock_exposed.assert_awaited_once()
    mock_secrets.assert_awaited_once()
    mock_nuclei.assert_not_called()
    assert len(findings) == 1


@pytest.mark.asyncio
async def test_quick_scan_deep_profile(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SKIP_DOMAIN_VERIFICATION", "true")
    get_settings.cache_clear()

    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "deep@example.com", "password": "SecurePass123!", "full_name": "Deep User"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['data']['tokens']['access_token']}"}

    with patch("app.services.domain_service.hostname_resolves", return_value=True):
        response = await client.post(
            "/api/v1/quick-scan",
            json={
                "target_url": "https://deep.example.com",
                "scan_profile": "deep",
                "authorization_accepted": True,
            },
            headers=headers,
        )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["scan"]["scan_profile"] == "deep"
    assert data["scan"]["status"] == "queued"


@pytest.mark.asyncio
async def test_quick_scan_code_profile(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SKIP_DOMAIN_VERIFICATION", "true")
    get_settings.cache_clear()

    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "code@example.com", "password": "SecurePass123!", "full_name": "Code User"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['data']['tokens']['access_token']}"}

    with patch("app.services.domain_service.hostname_resolves", return_value=True):
        response = await client.post(
            "/api/v1/quick-scan",
            json={
                "target_url": "https://code.example.com",
                "scan_profile": "code",
                "authorization_accepted": True,
            },
            headers=headers,
        )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["scan"]["scan_profile"] == "code"
    assert data["scan"]["status"] == "queued"
