"""IPv4-first scan HTTP client and unreachable classification."""

from __future__ import annotations

import ssl
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.scanners.passive_http import run_passive_http_scan
from app.scanners.scan_http_client import (
    IPv4PreferTransport,
    _httpx_verify,
    http_error_evidence,
    is_tls_error,
    open_tcp_socket,
    scan_async_client,
)


def test_httpx_verify_keeps_system_trust_store():
    verify = _httpx_verify()
    assert isinstance(verify, ssl.SSLContext)
    assert verify.verify_mode == ssl.CERT_REQUIRED


@pytest.mark.asyncio
async def test_scan_client_uses_ipv4_prefer_transport():
    async with scan_async_client(timeout=5.0, verify=True) as client:
        assert isinstance(client._transport, IPv4PreferTransport)
        assert client.headers["user-agent"].startswith("Mozilla/5.0 (compatible; SIBER-Scanner/")


def test_open_tcp_socket_tries_ipv4_bind_first():
    sock = MagicMock()
    with patch("app.scanners.scan_http_client.socket.create_connection", return_value=sock) as conn:
        assert open_tcp_socket("ig-lb.de", 443, 10) is sock
    assert conn.call_args.kwargs["source_address"] == ("0.0.0.0", 0)


def test_open_tcp_socket_falls_back_without_ipv4_bind():
    sock = MagicMock()
    with patch(
        "app.scanners.scan_http_client.socket.create_connection",
        side_effect=[OSError("Cannot assign requested address"), sock],
    ) as conn:
        assert open_tcp_socket("example.com", 443, 10) is sock
    assert conn.call_count == 2
    assert conn.call_args_list[1].kwargs.get("source_address") is None


def test_is_tls_error_detects_wrapped_certificate_failure():
    request = httpx.Request("GET", "https://ig-lb.de/")
    exc = httpx.ConnectError("[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed", request=request)
    assert is_tls_error(exc) is True
    assert is_tls_error(httpx.ConnectError("Network is unreachable", request=request)) is False


@pytest.mark.asyncio
async def test_ipv4_prefer_falls_back_to_dual_stack_on_connect_error():
    request = httpx.Request("GET", "https://ig-lb.de/")
    ok = httpx.Response(200, request=request)
    transport = IPv4PreferTransport(verify=True)
    transport._ipv4 = AsyncMock()
    transport._ipv4.handle_async_request = AsyncMock(
        side_effect=httpx.ConnectError("Network is unreachable", request=request)
    )
    transport._any = AsyncMock()
    transport._any.handle_async_request = AsyncMock(return_value=ok)

    response = await transport.handle_async_request(request)

    assert response.status_code == 200
    transport._any.handle_async_request.assert_awaited_once_with(request)


@pytest.mark.asyncio
async def test_passive_http_reachable_site_is_not_unreachable():
    response = httpx.Response(
        200,
        headers={"server": "Apache/2.4.68 (Unix)"},
        request=httpx.Request("GET", "https://ig-lb.de/"),
    )
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=response)
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False

    with (
        patch("app.scanners.passive_http.scan_async_client", return_value=mock_client),
        patch("app.scanners.passive_http.scan_tls_certificate", new_callable=AsyncMock, return_value=[]),
        patch("app.scanners.passive_http.scan_http_redirect", new_callable=AsyncMock, return_value=[]),
    ):
        findings = await run_passive_http_scan("https://ig-lb.de/")

    assert not any(item.source_rule_id == "http-unreachable" for item in findings)
    assert any(item.source_rule_id == "server-disclosure" for item in findings)


@pytest.mark.asyncio
async def test_passive_http_connect_error_records_unreachable_evidence():
    request = httpx.Request("GET", "https://ig-lb.de/")
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Network is unreachable", request=request))
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False

    with (
        patch("app.scanners.passive_http.scan_async_client", return_value=mock_client),
        patch("app.scanners.passive_http.scan_tls_certificate", new_callable=AsyncMock, return_value=[]),
        patch("app.scanners.passive_http.scan_http_redirect", new_callable=AsyncMock, return_value=[]),
    ):
        findings = await run_passive_http_scan("https://ig-lb.de/")

    unreachable = [item for item in findings if item.source_rule_id == "http-unreachable"]
    assert len(unreachable) == 1
    assert unreachable[0].evidence["error_type"] == "ConnectError"
    assert unreachable[0].evidence["connect_preference"] == "ipv4-first"
    assert http_error_evidence(httpx.ConnectError("x", request=request))["evidence_type"] == "http_error"


@pytest.mark.asyncio
async def test_passive_http_tls_error_is_not_unreachable():
    request = httpx.Request("GET", "https://ig-lb.de/")
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(
        side_effect=httpx.ConnectError(
            "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed",
            request=request,
        )
    )
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False

    with (
        patch("app.scanners.passive_http.scan_async_client", return_value=mock_client),
        patch("app.scanners.passive_http.scan_tls_certificate", new_callable=AsyncMock, return_value=[]),
        patch("app.scanners.passive_http.scan_http_redirect", new_callable=AsyncMock, return_value=[]),
    ):
        findings = await run_passive_http_scan("https://ig-lb.de/")

    assert not any(item.source_rule_id == "http-unreachable" for item in findings)
    assert any(item.source_rule_id == "cert-invalid" for item in findings)
