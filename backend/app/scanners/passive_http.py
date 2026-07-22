"""Passive HTTP security checks (Safe Scan)."""

import logging
import re
import ssl
from datetime import UTC, datetime
from urllib.parse import urlparse

import httpx

from app.scanners.base import RawFinding

logger = logging.getLogger(__name__)

SECURITY_HEADERS: dict[str, dict[str, str]] = {
    "strict-transport-security": {
        "title": "Missing Strict-Transport-Security header",
        "severity": "medium",
        "remediation": "Add Strict-Transport-Security with an appropriate max-age.",
    },
    "x-content-type-options": {
        "title": "Missing X-Content-Type-Options header",
        "severity": "low",
        "remediation": "Set X-Content-Type-Options: nosniff.",
    },
    "x-frame-options": {
        "title": "Missing X-Frame-Options header",
        "severity": "medium",
        "remediation": "Set X-Frame-Options: DENY or SAMEORIGIN, or use CSP frame-ancestors.",
    },
    "content-security-policy": {
        "title": "Missing Content-Security-Policy header",
        "severity": "medium",
        "remediation": "Define a Content-Security-Policy appropriate for your application.",
    },
    "referrer-policy": {
        "title": "Missing Referrer-Policy header",
        "severity": "low",
        "remediation": "Set Referrer-Policy to strict-origin-when-cross-origin or stricter.",
    },
}

SERVER_DISCLOSURE = re.compile(r"(apache|nginx|iis|php|express|asp\.net)", re.I)


async def scan_http_redirect(hostname: str, https_url: str) -> list[RawFinding]:
    """Pasif: HTTP → HTTPS yönlendirmesini kontrol et (tek istek, zararsız)."""
    findings: list[RawFinding] = []
    http_url = f"http://{hostname}/"
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
            response = await client.get(http_url)
            if response.status_code not in (301, 302, 307, 308):
                findings.append(
                    RawFinding(
                        source_tool="passive_http",
                        source_rule_id="no-http-redirect",
                        title="HTTP redirect check",
                        description=f"GET {http_url} returned {response.status_code}",
                        severity="medium",
                        affected_url=https_url,
                        evidence={"status_code": response.status_code},
                    )
                )
            else:
                location = response.headers.get("location", "")
                if location and not location.lower().startswith("https://"):
                    findings.append(
                        RawFinding(
                            source_tool="passive_http",
                            source_rule_id="weak-http-redirect",
                            title="Weak HTTP redirect",
                            description=f"Redirect location is not HTTPS: {location[:200]}",
                            severity="medium",
                            affected_url=https_url,
                            evidence={"location": location[:200]},
                        )
                    )
    except httpx.HTTPError as exc:
        logger.debug("HTTP redirect check skipped for %s: %s", hostname, exc)
    return findings


async def scan_disclosure_headers(target_url: str, response: httpx.Response) -> list[RawFinding]:
    findings: list[RawFinding] = []
    headers_lower = {k.lower(): v for k, v in response.headers.items()}
    powered = headers_lower.get("x-powered-by", "")
    if powered:
        findings.append(
            RawFinding(
                source_tool="passive_http",
                source_rule_id="x-powered-by-disclosure",
                title="X-Powered-By disclosure",
                description=f"X-Powered-By: {powered}",
                severity="info",
                affected_url=target_url,
                evidence={"x_powered_by": powered},
            )
        )
    return findings


async def scan_security_headers(target_url: str, response: httpx.Response) -> list[RawFinding]:
    findings: list[RawFinding] = []
    headers_lower = {k.lower(): v for k, v in response.headers.items()}

    for header, meta in SECURITY_HEADERS.items():
        if header not in headers_lower:
            findings.append(
                RawFinding(
                    source_tool="passive_http",
                    source_rule_id=f"missing-header-{header}",
                    title=meta["title"],
                    description=f"The response from {target_url} does not include the {header} header.",
                    severity=meta["severity"],
                    affected_url=target_url,
                    remediation=meta["remediation"],
                    evidence={"missing_header": header},
                )
            )

    server = headers_lower.get("server", "")
    if server and SERVER_DISCLOSURE.search(server):
        findings.append(
            RawFinding(
                source_tool="passive_http",
                source_rule_id="server-disclosure",
                title="Server version disclosure",
                description=f"The Server header exposes implementation details: {server}",
                severity="info",
                affected_url=target_url,
                remediation="Remove or genericize the Server response header.",
                evidence={"server": server},
            )
        )

    for cookie_header in [v for k, v in response.headers.multi_items() if k.lower() == "set-cookie"]:
        issues = []
        lower = cookie_header.lower()
        if "secure" not in lower and target_url.startswith("https"):
            issues.append("Secure")
        if "httponly" not in lower:
            issues.append("HttpOnly")
        if "samesite" not in lower:
            issues.append("SameSite")
        if issues:
            findings.append(
                RawFinding(
                    source_tool="passive_http",
                    source_rule_id="insecure-cookie-flags",
                    title="Cookie missing security flags",
                    description=f"Set-Cookie is missing: {', '.join(issues)}",
                    severity="medium",
                    affected_url=target_url,
                    remediation="Set Secure, HttpOnly, and SameSite on sensitive cookies.",
                    evidence={"cookie_sample": cookie_header[:200], "missing_flags": issues},
                )
            )

    return findings


async def scan_tls_certificate(target_url: str) -> list[RawFinding]:
    parsed = urlparse(target_url)
    if not parsed.hostname:
        return []

    if parsed.scheme == "http":
        return [
            RawFinding(
                source_tool="tls_check",
                source_rule_id="no-https",
                title="Target not served over HTTPS",
                description=f"{target_url} uses plain HTTP.",
                severity="high",
                affected_url=target_url,
                remediation="Enforce HTTPS and redirect HTTP to HTTPS.",
            )
        ]

    if parsed.scheme != "https":
        return []

    findings: list[RawFinding] = []
    try:
        context = ssl.create_default_context()
        with ssl.create_connection((parsed.hostname, parsed.port or 443), timeout=10) as sock, context.wrap_socket(
            sock, server_hostname=parsed.hostname
        ) as ssock:
            cert = ssock.getpeercert()
            not_after = cert.get("notAfter")
            if not_after:
                expiry = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=UTC)
                days_left = (expiry - datetime.now(UTC)).days
                if days_left < 30:
                    findings.append(
                        RawFinding(
                            source_tool="tls_check",
                            source_rule_id="cert-expiring-soon",
                            title="TLS certificate expiring soon",
                            description=f"Certificate expires in {days_left} days ({not_after}).",
                            severity="high" if days_left < 7 else "medium",
                            affected_url=target_url,
                            remediation="Renew the TLS certificate before expiry.",
                            evidence={"expires_at": not_after, "days_left": days_left},
                        )
                    )
    except ssl.SSLCertVerificationError as exc:
        findings.append(
            RawFinding(
                source_tool="tls_check",
                source_rule_id="cert-invalid",
                title="TLS certificate verification failed",
                description=str(exc),
                severity="critical",
                affected_url=target_url,
                remediation="Install a valid certificate from a trusted CA.",
            )
        )
    except Exception as exc:
        logger.warning("TLS check failed for %s: %s", target_url, exc)

    return findings


async def run_passive_http_scan(target_url: str) -> list[RawFinding]:
    findings: list[RawFinding] = []
    parsed = urlparse(target_url)
    hostname = parsed.hostname

    findings.extend(await scan_tls_certificate(target_url))

    if hostname and parsed.scheme == "https":
        findings.extend(await scan_http_redirect(hostname, target_url))

    try:
        async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
            response = await client.get(target_url)
            findings.extend(await scan_security_headers(target_url, response))
            findings.extend(await scan_disclosure_headers(target_url, response))
            if response.status_code >= 500:
                findings.append(
                    RawFinding(
                        source_tool="passive_http",
                        source_rule_id="http-5xx",
                        title="Server returned 5xx error",
                        description=f"GET {target_url} returned HTTP {response.status_code}.",
                        severity="medium",
                        affected_url=target_url,
                        evidence={"status_code": response.status_code},
                    )
                )
    except httpx.HTTPError as exc:
        findings.append(
            RawFinding(
                source_tool="passive_http",
                source_rule_id="http-unreachable",
                title="Target unreachable",
                description=str(exc),
                severity="high",
                affected_url=target_url,
            )
        )

    return findings
