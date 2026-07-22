"""Quick scan API tests."""

import pytest
from httpx import AsyncClient

from app.core.config import get_settings


@pytest.mark.asyncio
async def test_quick_scan_creates_scan(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SKIP_DOMAIN_VERIFICATION", "true")
    get_settings.cache_clear()

    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "quickscan@example.com", "password": "SecurePass123!", "full_name": "Quick"},
    )
    assert reg.status_code == 201
    headers = {"Authorization": f"Bearer {reg.json()['data']['tokens']['access_token']}"}

    response = await client.post(
        "/api/v1/quick-scan",
        json={
            "target_url": "https://example.com",
            "scan_profile": "safe",
            "authorization_accepted": True,
        },
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["scan"]["target_url"] == "https://example.com/"
    assert body["data"]["scan"]["status"] in ("queued", "running", "completed")
