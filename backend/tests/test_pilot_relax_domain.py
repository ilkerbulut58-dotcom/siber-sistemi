"""Pilot/expert relaxed domain verification (no DNS proof)."""

from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient

from app.core.config import get_settings


@pytest.mark.asyncio
@patch("app.services.domain_service.hostname_resolves", return_value=False)
async def test_pilot_relax_auto_verifies_without_dns(
    _mock: AsyncMock,
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SKIP_DOMAIN_VERIFICATION", "true")
    get_settings.cache_clear()

    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "relax-owner@example.com", "password": "SecurePass123!", "full_name": "Owner"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['data']['tokens']['access_token']}"}
    org = (await client.post("/api/v1/organizations", json={"name": "Relax Org"}, headers=headers)).json()[
        "data"
    ]
    project = (
        await client.post(
            f"/api/v1/organizations/{org['id']}/projects",
            json={"name": "Site", "environment": "staging"},
            headers=headers,
        )
    ).json()["data"]

    add = await client.post(
        f"/api/v1/organizations/{org['id']}/projects/{project['id']}/domains",
        json={"hostname": "no-dns-unresolvable.invalid", "method": "dns_txt"},
        headers=headers,
    )
    assert add.status_code == 201, add.text
    domain = add.json()["data"]
    assert domain["is_verified"] is True

    verify = await client.post(
        f"/api/v1/organizations/{org['id']}/projects/{project['id']}/domains/{domain['id']}/verify",
        headers=headers,
    )
    assert verify.status_code == 200, verify.text
    assert verify.json()["data"]["verified"] is True
    assert verify.json()["data"]["failure_code"] is None

    monkeypatch.delenv("SKIP_DOMAIN_VERIFICATION", raising=False)
    get_settings.cache_clear()
