"""API surface scanner origin URL tests."""

from __future__ import annotations

from app.scanners.api_surface_scanner import _site_origin


def test_site_origin_strips_path_for_openapi_discovery():
    assert _site_origin("https://benchmark-crapi-proxy/health") == "https://benchmark-crapi-proxy"
