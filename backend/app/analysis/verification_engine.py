"""Passive-only verification for correlated findings."""

from __future__ import annotations

import logging
import ssl
from urllib.parse import urlparse

import httpx

from app.analysis.correlation_rules import normalize_url
from app.analysis.types import AnalyzedFinding, CorrelatedFinding

logger = logging.getLogger(__name__)

HEADER_CHECKS: dict[str, str] = {
    "missing-header-strict-transport-security": "strict-transport-security",
    "missing-header-x-content-type-options": "x-content-type-options",
    "missing-header-x-frame-options": "x-frame-options",
    "missing-header-content-security-policy": "content-security-policy",
    "missing-header-referrer-policy": "referrer-policy",
}


async def verify_findings(
    target_url: str,
    correlated: list[CorrelatedFinding],
) -> list[AnalyzedFinding]:
    analyzed: list[AnalyzedFinding] = []
    cached_holder: dict = {"response": None}

    for finding in correlated:
        result = AnalyzedFinding(
            correlation_key=finding.correlation_key,
            title=finding.title,
            description=finding.description,
            severity=finding.severity,
            affected_url=finding.affected_url,
            remediation=finding.remediation,
            confidence=finding.confidence,
            evidence=dict(finding.evidence),
            source_tools=list(finding.source_tools),
            source_rule_ids=list(finding.source_rule_ids),
            raw_sources=list(finding.raw_sources),
            risk_explanation=finding.risk_explanation,
            remediation_steps=finding.remediation_steps,
            config_file_paths=finding.config_file_paths,
            config_snippet=finding.config_snippet,
            cvss_score=finding.cvss_score,
            exposure_score=_exposure_score(finding.affected_url or target_url),
        )

        verified_confidence, status, notes = await _verify_one(
            finding,
            target_url,
            cached_holder,
        )
        result.verified_confidence = verified_confidence
        result.verification_status = status
        result.verification_notes = notes
        result.confidence = verified_confidence
        analyzed.append(result)

    return analyzed


async def _verify_one(
    finding: CorrelatedFinding,
    target_url: str,
    cached_holder: dict,
) -> tuple[str, str, str | None]:
    key = finding.correlation_key
    url = finding.affected_url or target_url

    try:
        if key in HEADER_CHECKS:
            return await _verify_missing_header(url, key, cached_holder, finding)

        if key == "no-http-redirect" or key == "weak-http-redirect":
            return await _verify_http_redirect(url)

        if key.startswith("cert-") or key == "no-https":
            return await _verify_tls(url, key)

        if key.startswith("exposed-"):
            return await _verify_exposed_path(url, finding)

        if len(finding.source_tools) >= 2:
            return "medium", "correlated", "Birden fazla tarayıcı aynı bulguyu raporladı."

        return finding.confidence, "unverified", "Pasif doğrulama kuralı tanımlı değil."
    except Exception as exc:
        logger.debug("Verification skipped for %s: %s", key, exc)
        return finding.confidence, "unverified", f"Doğrulama atlandı: {exc}"


async def _get_response(url: str, cached_holder: dict) -> httpx.Response | None:
    if cached_holder.get("response") is not None:
        return cached_holder["response"]
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            response = await client.get(url)
            cached_holder["response"] = response
            return response
    except httpx.HTTPError:
        return None


async def _verify_missing_header(
    url: str,
    key: str,
    cached_holder: dict,
    finding: CorrelatedFinding,
) -> tuple[str, str, str | None]:
    header_name = HEADER_CHECKS[key]
    response = await _get_response(url, cached_holder)
    if response is None:
        return finding.confidence, "unverified", "Hedef yanıt vermedi."

    headers_lower = {k.lower(): v for k, v in response.headers.items()}
    if header_name not in headers_lower:
        boost = "high" if len(finding.source_tools) >= 2 else "medium"
        return boost, "verified", f"Pasif doğrulama: {header_name} başlığı hâlâ eksik."

    return "low", "inconclusive", f"Pasif doğrulama: {header_name} başlığı artık mevcut."


async def _verify_http_redirect(url: str) -> tuple[str, str, str | None]:
    parsed = urlparse(url)
    if not parsed.hostname:
        return "low", "unverified", None
    http_url = f"http://{parsed.hostname}/"
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
            response = await client.get(http_url)
        if response.status_code in (301, 302, 307, 308):
            location = response.headers.get("location", "")
            if location.lower().startswith("https://"):
                return "low", "inconclusive", "HTTP artık HTTPS'e yönlendiriyor."
            return "medium", "verified", "HTTP yönlendirmesi zayıf veya HTTPS değil."
        return "medium", "verified", f"HTTP yönlendirme yok (status {response.status_code})."
    except httpx.HTTPError as exc:
        return "low", "unverified", str(exc)


async def _verify_tls(url: str, key: str) -> tuple[str, str, str | None]:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        if key == "no-https":
            return "high", "verified", "Hedef hâlâ HTTPS kullanmıyor."
        return "low", "unverified", None
    try:
        context = ssl.create_default_context()
        with ssl.create_connection((parsed.hostname, parsed.port or 443), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=parsed.hostname):
                pass
        if key == "cert-invalid":
            return "low", "inconclusive", "Sertifika artık geçerli görünüyor."
        return "medium", "verified", "TLS sorunu pasif doğrulamayla teyit edildi."
    except ssl.SSLError:
        return "high", "verified", "TLS sertifika doğrulaması başarısız."
    except OSError as exc:
        return "low", "unverified", str(exc)


async def _verify_exposed_path(url: str, finding: CorrelatedFinding) -> tuple[str, str, str | None]:
    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=False) as client:
            response = await client.get(url)
        if response.status_code == 200:
            return "high", "verified", "Hassas dosya hâlâ HTTP 200 döndürüyor."
        return "low", "inconclusive", f"Artık erişilemiyor (HTTP {response.status_code})."
    except httpx.HTTPError as exc:
        return "low", "inconclusive", str(exc)


def _exposure_score(url: str) -> float:
    parsed = urlparse(url)
    if parsed.scheme == "https":
        return 1.0
    if parsed.scheme == "http":
        return 0.85
    return 0.7
