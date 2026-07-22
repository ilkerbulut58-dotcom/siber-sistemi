"""Deterministic URL canonicalization shared by analysis and benchmark layers."""

from __future__ import annotations

from urllib.parse import parse_qsl, unquote, urlencode, urlparse, urlunparse


def canonicalize_url(url: str | None) -> str:
    """Normalize URL for stable dedup fingerprints."""
    if not url:
        return ""
    parsed = urlparse(url.strip())
    scheme = (parsed.scheme or "https").lower()
    host = (parsed.hostname or "").lower()
    if not host:
        return url.strip()

    port = parsed.port
    if port and ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        port = None

    path = unquote(parsed.path or "")
    path = "/" if path == "/" else (path.rstrip("/") or "/")

    query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
    query_pairs = sorted((unquote(k), unquote(v)) for k, v in query_pairs)
    query = urlencode(query_pairs, doseq=True)

    netloc = host if port is None else f"{host}:{port}"
    return urlunparse((scheme, netloc, path, "", query, ""))


def normalize_url(url: str | None) -> str:
    return canonicalize_url(url)
