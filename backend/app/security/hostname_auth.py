"""Strict hostname parsing and authorization for scan targets."""

from __future__ import annotations

from urllib.parse import urlparse

from app.core.exceptions import AppError
from app.security.url_guard import UrlGuardError, validate_redirect_target, validate_scan_url


class HostnameAuthorizationError(ValueError):
    """Raised when a target hostname is not authorized for a verified domain."""


def normalize_hostname(hostname: str) -> str:
    """Normalize hostname: lowercase, strip trailing dot, IDNA punycode, no www prefix."""
    value = hostname.strip().lower().rstrip(".")
    if value.startswith("http://") or value.startswith("https://"):
        parsed = urlparse(value)
        value = (parsed.hostname or "").lower().rstrip(".")
    if not value:
        raise HostnameAuthorizationError("Hostname is required.")
    try:
        value = value.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise HostnameAuthorizationError(f"Invalid internationalized hostname: {hostname}") from exc
    if value.startswith("www."):
        value = value[4:]
    return value


def parse_target_hostname(target_url: str) -> str:
    """Extract and normalize hostname from a scan target URL."""
    parsed = urlparse(str(target_url).strip())
    if parsed.scheme not in {"http", "https"}:
        raise HostnameAuthorizationError(f"Unsupported URL scheme: {parsed.scheme!r}")
    if parsed.username or parsed.password:
        raise HostnameAuthorizationError("Embedded credentials in URLs are forbidden.")
    hostname = parsed.hostname
    if not hostname:
        raise HostnameAuthorizationError("URL must include a hostname.")
    return normalize_hostname(hostname)


def hostname_matches_verified_domain(
    target_hostname: str,
    verified_hostname: str,
    *,
    allow_subdomains: bool = False,
) -> bool:
    """Exact hostname match by default; optional explicit subdomain policy."""
    target = normalize_hostname(target_hostname)
    verified = normalize_hostname(verified_hostname)
    if target == verified:
        return True
    return bool(allow_subdomains and target.endswith(f".{verified}"))


def assert_target_authorized_for_domain(
    target_url: str,
    verified_hostname: str,
    *,
    allow_subdomains: bool = False,
) -> str:
    """Return normalized target hostname or raise."""
    target_host = parse_target_hostname(target_url)
    if not hostname_matches_verified_domain(
        target_host,
        verified_hostname,
        allow_subdomains=allow_subdomains,
    ):
        raise HostnameAuthorizationError(
            f"Target hostname {target_host!r} is not authorized for verified domain "
            f"{normalize_hostname(verified_hostname)!r}."
        )
    return target_host


def validate_scan_target_url(
    target_url: str,
    verified_hostname: str,
    *,
    allow_subdomains: bool = False,
    resolve_dns: bool = True,
) -> str:
    """Full pre-scan validation: URL guard + exact hostname authorization."""
    try:
        validate_scan_url(target_url, resolve_dns=resolve_dns)
    except UrlGuardError as exc:
        raise HostnameAuthorizationError(str(exc)) from exc
    return assert_target_authorized_for_domain(
        target_url,
        verified_hostname,
        allow_subdomains=allow_subdomains,
    )


def validate_redirect_for_domain(
    redirect_url: str,
    verified_hostname: str,
    *,
    allow_subdomains: bool = False,
    resolve_dns: bool = True,
) -> None:
    """Re-validate ownership and SSRF after redirects."""
    try:
        validate_redirect_target(redirect_url, resolve_dns=resolve_dns)
    except UrlGuardError as exc:
        raise HostnameAuthorizationError(str(exc)) from exc
    assert_target_authorized_for_domain(
        redirect_url,
        verified_hostname,
        allow_subdomains=allow_subdomains,
    )


def to_app_error(exc: HostnameAuthorizationError) -> AppError:
    return AppError("TARGET_MISMATCH", str(exc), status_code=400)
