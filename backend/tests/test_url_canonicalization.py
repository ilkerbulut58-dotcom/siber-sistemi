"""URL canonicalization tests."""

from __future__ import annotations

from app.utils.url_canonicalization import canonicalize_url


def test_trailing_slash_and_default_port():
    assert canonicalize_url("HTTPS://Example.com:443/path/") == "https://example.com/path"


def test_sorted_query_params():
    assert (
        canonicalize_url("https://example.com/x?b=2&a=1")
        == canonicalize_url("https://example.com/x?a=1&b=2")
    )


def test_fragment_removed():
    assert canonicalize_url("https://example.com/path#section") == "https://example.com/path"
