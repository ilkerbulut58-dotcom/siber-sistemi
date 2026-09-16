"""Shared outbound HTTP client for customer-target scanners.

Production Docker often resolves AAAA records first. Dual-stack sites such as
ig-lb.de then fail immediately on IPv6 ("Network is unreachable") and httpx
can classify that as a generic HTTPError. Scan traffic prefers IPv4 and only
falls back to the default dual-stack path when IPv4 cannot connect.
"""

from __future__ import annotations

import logging
import os
import socket
import ssl
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

SCAN_USER_AGENT = "Mozilla/5.0 (compatible; SIBER-Scanner/1.0; +https://siber.cloudnira.com)"
_IPV4_BIND = ("0.0.0.0", 0)


def _benchmark_ca_path() -> Path | None:
    env_path = os.environ.get("BENCHMARK_CA_CERT_PATH", "").strip()
    if env_path:
        path = Path(env_path)
        if path.is_file():
            return path
    default = (
        Path(__file__).resolve().parents[3]
        / "benchmarks"
        / "docker"
        / "realistic"
        / "certs"
        / "ca.crt"
    )
    return default if default.is_file() else None


def scan_ssl_context() -> ssl.SSLContext:
    """System trust store plus optional lab CA (never replace public CAs)."""
    context = ssl.create_default_context()
    ca_path = _benchmark_ca_path()
    if ca_path is not None:
        context.load_verify_locations(cafile=str(ca_path))
    return context


def _httpx_verify() -> ssl.SSLContext:
    return scan_ssl_context()


def is_tls_error(exc: BaseException) -> bool:
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, ssl.SSLError):
            return True
        text = str(current).lower()
        if "certificate verify failed" in text or "sslcertverificationerror" in text:
            return True
        if "ssl:" in text and "certificate" in text:
            return True
        current = current.__cause__ or current.__context__
    return False


def http_error_evidence(exc: BaseException) -> dict[str, Any]:
    return {
        "evidence_type": "http_error",
        "error_type": type(exc).__name__,
        "error_message": str(exc)[:500],
        "connect_preference": "ipv4-first",
    }


def open_tcp_socket(host: str, port: int, timeout: float) -> socket.socket:
    """Open TCP, binding IPv4 first so dual-stack hosts are not stuck on AAAA."""
    try:
        return socket.create_connection((host, port), timeout=timeout, source_address=_IPV4_BIND)
    except OSError as exc:
        logger.debug("IPv4 bind connect failed for %s:%s (%s); retrying default", host, port, exc)
        return socket.create_connection((host, port), timeout=timeout)


class IPv4PreferTransport(httpx.AsyncBaseTransport):
    """Try IPv4-only sockets first, then the default dual-stack pool."""

    def __init__(self, *, verify: ssl.SSLContext | str | bool = True, retries: int = 1) -> None:
        super().__init__()
        self._ipv4 = httpx.AsyncHTTPTransport(
            verify=verify,
            retries=retries,
            local_address="0.0.0.0",
        )
        self._any = httpx.AsyncHTTPTransport(verify=verify, retries=retries)

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        try:
            return await self._ipv4.handle_async_request(request)
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            logger.debug("IPv4 connect failed for %s (%s); retrying dual-stack", request.url, exc)
            return await self._any.handle_async_request(request)

    async def aclose(self) -> None:
        await self._ipv4.aclose()
        await self._any.aclose()


def scan_async_client(
    *,
    timeout: float | httpx.Timeout,
    follow_redirects: bool = True,
    verify: ssl.SSLContext | str | bool | None = None,
) -> httpx.AsyncClient:
    if verify is None:
        verify = _httpx_verify()
    return httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=follow_redirects,
        headers={
            "User-Agent": SCAN_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
        transport=IPv4PreferTransport(verify=verify, retries=1),
    )
