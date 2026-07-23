"""Production SSRF and outbound URL guardrails for customer scans."""

from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urlparse

BLOCKED_SCHEMES = frozenset({"file", "ftp", "gopher", "dict", "ldap", "jar", "data", "javascript"})
METADATA_HOSTS = frozenset(
    {
        "169.254.169.254",
        "metadata.google.internal",
        "metadata.azure.com",
        "metadata.aws.internal",
        "metadata",
    }
)
BLOCKED_HOST_SUFFIXES = (".local", ".internal", ".localhost")
BLOCKED_HOST_NAMES = frozenset({"localhost", "localhost.localdomain"})
MAX_REDIRECTS = 5

# Decimal / hex / octal IPv4 bypass patterns in host strings.
_ENCODED_IP = re.compile(
    r"^(?:0x[0-9a-f]+|0[0-7]+|\d{1,10})$",
    re.I,
)


class UrlGuardError(ValueError):
    """Raised when a scan target URL violates outbound safety rules."""


def _parse_ip_literal(host: str) -> ipaddress._BaseAddress | None:
    candidate = host.strip()
    if _ENCODED_IP.match(candidate):
        try:
            if candidate.lower().startswith("0x"):
                return ipaddress.ip_address(int(candidate, 16))
            if candidate.startswith("0") and candidate != "0":
                return ipaddress.ip_address(int(candidate, 8))
            return ipaddress.ip_address(int(candidate, 10))
        except ValueError:
            return None
    if candidate.startswith("[") and candidate.endswith("]"):
        candidate = candidate[1:-1]
    try:
        return ipaddress.ip_address(candidate)
    except ValueError:
        return None


def is_blocked_ip(address: ipaddress._BaseAddress) -> bool:
    return bool(
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    )


def validate_hostname(host: str) -> None:
    lowered = host.lower().rstrip(".")
    if lowered in BLOCKED_HOST_NAMES:
        raise UrlGuardError(f"Blocked hostname: {host}")
    if lowered in METADATA_HOSTS or lowered.endswith(".metadata.google.internal"):
        raise UrlGuardError(f"Metadata endpoint blocked: {host}")
    if any(lowered.endswith(suffix) for suffix in BLOCKED_HOST_SUFFIXES):
        raise UrlGuardError(f"Internal hostname blocked: {host}")

    literal = _parse_ip_literal(host)
    if literal is not None:
        if isinstance(literal, ipaddress.IPv6Address) and literal.ipv4_mapped:
            literal = literal.ipv4_mapped
        if is_blocked_ip(literal):
            raise UrlGuardError(f"Blocked IP target: {host}")


def resolve_and_validate_host(host: str, *, port: int) -> None:
    """Resolve DNS and reject private/metadata addresses (DNS rebinding mitigation)."""
    validate_hostname(host)
    if _parse_ip_literal(host) is not None:
        return
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UrlGuardError(f"DNS resolution failed for {host}: {exc}") from exc
    if not infos:
        raise UrlGuardError(f"No DNS records for {host}")
    for info in infos:
        sockaddr = info[4]
        if not sockaddr:
            continue
        resolved = sockaddr[0]
        address = ipaddress.ip_address(resolved)
        if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
            address = address.ipv4_mapped
        if is_blocked_ip(address):
            raise UrlGuardError(f"DNS resolved to blocked address: {resolved}")


def validate_scan_url(url: str, *, resolve_dns: bool = True) -> str:
    """Validate a user-supplied scan URL before any outbound request."""
    parsed = urlparse(url.strip())
    scheme = (parsed.scheme or "").lower()
    if scheme not in {"http", "https"}:
        raise UrlGuardError(f"Scheme {scheme!r} is not allowed")
    if parsed.username or parsed.password:
        raise UrlGuardError("Embedded credentials in URLs are forbidden")
    hostname = parsed.hostname
    if not hostname:
        raise UrlGuardError("URL must include a hostname")
    port = parsed.port or (443 if scheme == "https" else 80)
    validate_hostname(hostname)
    if resolve_dns:
        resolve_and_validate_host(hostname, port=port)
    return url


def validate_redirect_target(url: str, *, resolve_dns: bool = True) -> None:
    validate_scan_url(url, resolve_dns=resolve_dns)
