"""Passive API surface checks for isolated benchmark lab (CORS, OpenAPI discovery)."""

from __future__ import annotations

import json
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
    "/api/openapi.json",
    "/identity/api/openapi.json",
    "/community/api/openapi.json",
    "/workshop/api/openapi.json",
    "/workshop/api/schema/",
    "/workshop/api/swagger/",
)

# crAPI routes @CrossOrigin controllers and common API entry points (via benchmark-crapi-proxy).
CRAPI_CORS_PATHS = (
    "/identity/api/auth/login",
    "/identity/api/auth/signup",
    "/community/api/v2/community/posts",
    "/workshop/api/shop/products",
)


def _openapi_body_matches(body: str, content_type: str) -> bool:
    sample = body[:4000].lower()
    if "openapi" in sample or "swagger" in sample:
        return True
    if "application/json" in content_type.lower() or sample.lstrip().startswith("{"):
        try:
            payload = json.loads(body[:200_000])
        except json.JSONDecodeError:
            return False
        if isinstance(payload, dict):
            if payload.get("openapi") or payload.get("swagger"):
                return True
            paths = payload.get("paths")
            return isinstance(paths, dict) and len(paths) > 0
    return "text/html" in content_type.lower() and ("swagger-ui" in sample or "swagger ui" in sample)


async def scan_cors_policy(
    target_url: str,
    client: httpx.AsyncClient,
    *,
    request_method: str = "POST",
) -> list[RawFinding]:
    findings: list[RawFinding] = []
    origin = "https://evil-benchmark-origin.example"
    for method in ("OPTIONS", "GET"):
        try:
            headers = {"Origin": origin}
            if method == "OPTIONS":
                headers["Access-Control-Request-Method"] = request_method
            response = await client.request(method, target_url, headers=headers)
            allow_origin = response.headers.get("access-control-allow-origin", "")
            if allow_origin in {"*", origin}:
                findings.append(
                    RawFinding(
                        source_tool="passive_http",
                        source_rule_id="permissive-cors",
                        title="Permissive CORS configuration",
                        description=(
                            f"{method} {target_url} reflects Origin with "
                            f"Access-Control-Allow-Origin: {allow_origin}"
                        ),
                        severity="medium",
                        affected_url=target_url,
                        remediation="Restrict CORS to trusted origins; avoid wildcard with credentials.",
                        confidence="high",
                        evidence={
                            "allow_origin": allow_origin,
                            "request_origin": origin,
                            "status_code": response.status_code,
                            "http_method": method,
                            "validator": "cors_preflight_response",
                        },
                    )
                )
                break
        except httpx.HTTPError as exc:
            logger.debug("CORS check skipped for %s (%s): %s", target_url, method, exc)
    return findings


async def scan_openapi_exposure(base_url: str, client: httpx.AsyncClient) -> list[RawFinding]:
    findings: list[RawFinding] = []
    discovered: list[str] = []
    origin = _site_origin(base_url)
    for path in OPENAPI_PATHS:
        url = urljoin(origin.rstrip("/") + "/", path.lstrip("/"))
        try:
            response = await client.get(url, headers={"Accept": "application/json, text/html;q=0.9"})
            if response.status_code != 200:
                continue
            content_type = response.headers.get("content-type", "")
            if _openapi_body_matches(response.text, content_type):
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


def _crapi_probe_paths(target_url: str) -> tuple[list[str], list[str]]:
    """Return CORS and OpenAPI probe URLs for crAPI realistic proxy targets."""
    origin = _site_origin(target_url)
    parsed = urlparse(origin)
    if parsed.hostname != "benchmark-crapi-proxy":
        return [target_url], []
    cors_urls = [urljoin(origin.rstrip("/") + "/", path.lstrip("/")) for path in CRAPI_CORS_PATHS]
    if target_url not in cors_urls:
        cors_urls.insert(0, target_url)
    cors_urls.insert(1, origin)
    return cors_urls, []


async def run_api_surface_scan(target_url: str) -> list[RawFinding]:
    findings: list[RawFinding] = []
    origin = _site_origin(target_url)
    cors_urls, _ = _crapi_probe_paths(target_url)
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, verify=_httpx_verify()) as client:
            for probe_url in dict.fromkeys(cors_urls):
                request_method = "POST" if "/auth/" in probe_url else "GET"
                findings.extend(await scan_cors_policy(probe_url, client, request_method=request_method))
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
