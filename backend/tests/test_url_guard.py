"""Production URL guard tests."""

from __future__ import annotations

import pytest

from app.security.url_guard import UrlGuardError, validate_scan_url


def test_blocks_localhost():
    with pytest.raises(UrlGuardError):
        validate_scan_url("http://localhost/", resolve_dns=False)


def test_blocks_metadata_ip():
    with pytest.raises(UrlGuardError):
        validate_scan_url("http://169.254.169.254/latest/meta-data/", resolve_dns=False)


def test_blocks_file_scheme():
    with pytest.raises(UrlGuardError):
        validate_scan_url("file:///etc/passwd", resolve_dns=False)


def test_blocks_decimal_ip_bypass():
    with pytest.raises(UrlGuardError):
        validate_scan_url("http://2130706433/", resolve_dns=False)


def test_allows_public_https_without_dns():
    validate_scan_url("https://example.com/path", resolve_dns=False)
