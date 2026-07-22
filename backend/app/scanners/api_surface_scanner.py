"""Passive API surface checks for isolated benchmark lab (CORS, OpenAPI discovery)."""

from __future__ import annotations

import logging
from urllib.parse import urljoin, urlparse, urlunparse

import httpx

from app.scanners.base import RawFinding
from app.scanners.passive_http import _httpx_verify

logger = logging.getLogger(__name__)

def _site_origin(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))


OPENAPI_PATHS = (
    "/openapi.json",
    "/swagger.json",
    "/swagger/v1/swagger.json",
    "/api-docs",
    "/docs",
    "/v3/api-docs",
    "/swagger-ui.html",
)


async def scan_cors_policy(target_url: str, client: httpx.AsyncClient) -> list[RawFinding]:
    findings: list[RawFinding] = []
    origin = "https://evil-benchmark-origin.example"
    try:
        response = await client.request(
            "OPTIONS",
            target_url,
            headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
        )
        allow_origin = response.headers.get("access-control-allow-origin", "")
        if allow_origin in {"*", origin}:
            findings.append(
                RawFinding(
                    source_tool="passive_http",
                    source_rule_id="permissive-cors",
                    title="Permissive CORS configuration",
                    description=(
                        f"OPTIONS {target_url} reflects Origin with Access-Control-Allow-Origin: {allow_origin}"
                    ),
                    severity="medium",
                    affected_url=target_url,
                    remediation="Restrict CORS to trusted origins; avoid wildcard with credentials.",
                    confidence="high",
                    evidence={
                        "allow_origin": allow_origin,
                        "request_origin": origin,
                        "status_code": response.status_code,
                        "validator": "cors_preflight_response",
                    },
                )
            )
    except httpx.HTTPError as exc:
        logger.debug("CORS check skipped for %s: %s", target_url, exc)
    return findings


async def scan_openapi_exposure(base_url: str, client: httpx.AsyncClient) -> list[RawFinding]:
    findings: list[RawFinding] = []
    discovered: list[str] = []
    origin = _site_origin(base_url)
    for path in OPENAPI_PATHS:
        url = urljoin(origin.rstrip("/") + "/", path.lstrip("/"))
        try:
            response = await client.get(url)
            if response.status_code != 200:
                continue
            body_sample = response.text[:400].lower()
            if "openapi" in body_sample or "swagger" in body_sample or "paths" in body_sample:
                discovered.append(url)
        except httpx.HTTPError:
            continue
    if discovered:
        findings.append(
            RawFinding(
                source_tool="passive_http",
                source_rule_id="exposed-api-docs",
                title="API documentation exposed",
                description=f"OpenAPI/Swagger documentation reachable at: {', '.join(discovered[:3])}",
                severity="medium",
                affected_url=discovered[0],
                remediation="Restrict API documentation to authenticated admin contexts.",
                confidence="high",
                evidence={
                    "discovered_paths": discovered,
                    "validator": "openapi_body_signature",
                },
            )
        )
    return findings


async def run_api_surface_scan(target_url: str) -> list[RawFinding]:
    findings: list[RawFinding] = []
    origin = _site_origin(target_url)
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, verify=_httpx_verify()) as client:
            for probe_url in dict.fromkeys([origin, target_url]):
                findings.extend(await scan_cors_policy(probe_url, client))
            findings.extend(await scan_openapi_exposure(origin, client))
    except httpx.HTTPError as exc:
        logger.warning("API surface scan failed for %s: %s", target_url, exc)
    return findings


def api_coverage_metrics(raw_findings: list[RawFinding]) -> dict[str, int | bool]:
    """Measure API benchmark coverage dimensions from raw scanner output."""
    tools = {item.source_tool for item in raw_findings}
    rule_ids = {item.source_rule_id for item in raw_findings}
    openapi_hit = any(item.source_rule_id == "exposed-api-docs" for item in raw_findings)
    cors_hit = any(item.source_rule_id == "permissive-cors" for item in raw_findings)
    header_hits = sum(1 for item in raw_findings if item.source_rule_id.startswith("missing-header-"))
    return {
        "scanner_tools_present": sorted(tools),
        "openapi_discovery": openapi_hit,
        "cors_probe": cors_hit,
        "header_checks": header_hits,
        "unique_rule_count": len(rule_ids),
        "method_coverage_options": "permissive-cors" in rule_ids,
    }
