"""Redirect and SSRF guard checks for pilot simulation."""

from __future__ import annotations

import pytest

from app.security.url_guard import UrlGuardError, validate_scan_url


def test_10_redirect_target_blocked_for_private_ip() -> None:
    with pytest.raises(UrlGuardError):
        validate_scan_url("http://127.0.0.1:18080/", resolve_dns=False)

    with pytest.raises(UrlGuardError):
        validate_scan_url("http://169.254.169.254/latest/meta-data/", resolve_dns=False)
