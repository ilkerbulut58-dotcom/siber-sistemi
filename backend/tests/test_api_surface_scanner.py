"""API surface scanner tests."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.scanners.api_surface_scanner import (
    _openapi_body_matches,
    _site_origin,
    run_api_surface_scan,
    scan_cors_policy,
    scan_openapi_exposure,
)


def test_site_origin_strips_path_for_openapi_discovery():
    assert _site_origin("https://benchmark-crapi-proxy/health") == "https://benchmark-crapi-proxy"


def test_openapi_body_matches_json_spec():
    body = json.dumps({"openapi": "3.0.1", "paths": {"/health": {}}})
    assert _openapi_body_matches(body, "application/json")


def test_openapi_body_matches_rejects_unrelated_json():
    body = json.dumps({"keys": [{"kty": "RSA"}]})
    assert not _openapi_body_matches(body, "application/json")


@pytest.mark.asyncio
async def test_scan_cors_policy_detects_reflected_origin():
    response = MagicMock()
    response.headers = {"access-control-allow-origin": "https://evil-benchmark-origin.example"}
    response.status_code = 204
    client = AsyncMock()
    client.request = AsyncMock(return_value=response)

    findings = await scan_cors_policy(
        "https://benchmark-crapi-proxy/identity/api/auth/login",
        client,
        request_method="POST",
    )
    assert len(findings) == 1
    assert findings[0].source_rule_id == "permissive-cors"


@pytest.mark.asyncio
async def test_scan_openapi_exposure_detects_spec():
    response = MagicMock()
    response.status_code = 200
    response.headers = {"content-type": "application/json"}
    response.text = json.dumps({"openapi": "3.0.1", "paths": {"/identity/api/auth/login": {}}})
    client = AsyncMock()
    client.get = AsyncMock(return_value=response)

    findings = await scan_openapi_exposure("https://benchmark-crapi-proxy/health", client)
    assert len(findings) == 1
    assert findings[0].source_rule_id == "exposed-api-docs"


@pytest.mark.asyncio
async def test_run_api_surface_scan_probes_crapi_identity_route():
    cors_response = MagicMock()
    cors_response.headers = {"access-control-allow-origin": "*"}
    cors_response.status_code = 204

    missing_response = MagicMock()
    missing_response.status_code = 404
    missing_response.headers = {}
    missing_response.text = ""

    async def fake_request(method, url, headers=None):
        if method == "OPTIONS" and url.endswith("/identity/api/auth/login"):
            return cors_response
        return missing_response

    client = AsyncMock()
    client.request = AsyncMock(side_effect=fake_request)
    client.get = AsyncMock(return_value=missing_response)

    with patch("app.scanners.api_surface_scanner.httpx.AsyncClient") as client_cls:
        client_cls.return_value.__aenter__.return_value = client
        findings = await run_api_surface_scan("https://benchmark-crapi-proxy/health")

    cors = [item for item in findings if item.source_rule_id == "permissive-cors"]
    assert len(cors) == 1
