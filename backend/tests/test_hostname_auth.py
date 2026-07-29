"""Strict hostname authorization tests."""

from __future__ import annotations

import pytest

from app.security.hostname_auth import (
    HostnameAuthorizationError,
    assert_target_authorized_for_domain,
    hostname_matches_verified_domain,
    normalize_hostname,
    parse_target_hostname,
    validate_scan_target_url,
)
from app.security.url_guard import UrlGuardError


def test_exact_hostname_match():
    assert hostname_matches_verified_domain("example.com", "example.com")


def test_uppercase_and_trailing_dot():
    assert hostname_matches_verified_domain("Example.COM.", "example.com")


def test_suffix_attack_blocked():
    assert not hostname_matches_verified_domain("verified.com.evil.tld", "verified.com")


def test_prefix_attack_blocked():
    assert not hostname_matches_verified_domain("evil-verified.com", "verified.com")


def test_subdomain_not_allowed_by_default():
    assert not hostname_matches_verified_domain("app.verified.com", "verified.com")


def test_subdomain_allowed_when_policy_enabled():
    assert hostname_matches_verified_domain(
        "app.verified.com",
        "verified.com",
        allow_subdomains=True,
    )


def test_userinfo_url_rejected():
    with pytest.raises(HostnameAuthorizationError, match="Embedded credentials"):
        parse_target_hostname("https://user:pass@verified.com/path")


def test_userinfo_in_hostname_rejected():
    with pytest.raises(HostnameAuthorizationError):
        parse_target_hostname("https://verified.com@evil.tld/")


def test_alternate_port_same_host():
    assert_target_authorized_for_domain("https://verified.com:8443/", "verified.com")


def test_wrong_port_host_blocked():
    with pytest.raises(HostnameAuthorizationError):
        assert_target_authorized_for_domain("https://evil.tld:443/", "verified.com")


def test_validate_scan_target_blocks_private():
    with pytest.raises(HostnameAuthorizationError):
        validate_scan_target_url(
            "http://127.0.0.1/",
            "example.com",
            resolve_dns=False,
        )


def test_punycode_normalization():
    # unicode domain encodes to punycode
    normalized = normalize_hostname(" münchen.de ".strip())
    assert "xn--" in normalized or normalized == "münchen.de".encode("idna").decode("ascii")


def test_decimal_ip_blocked_in_url_guard():
    with pytest.raises((HostnameAuthorizationError, UrlGuardError)):
        validate_scan_target_url("http://2130706433/", "example.com", resolve_dns=False)
