"""OWASP ZAP active scan integration for isolated benchmark lab only."""

from __future__ import annotations

import asyncio
import logging
import time

import httpx

from app.benchmark.active_guard import ActiveBenchmarkGuard, zap_exclude_regexes
from app.core.config import get_settings
from app.scanners.base import RawFinding
from app.scanners.execution_stats import set_pending_scanner_enrich
from app.scanners.zap_passive import _alerts_to_findings, _api_get, _zap_reachable, _zap_version

logger = logging.getLogger(__name__)


async def run_zap_active_scan(
    target_url: str,
    *,
    guard: ActiveBenchmarkGuard,
    max_children: int = 5,
) -> list[RawFinding]:
    settings = get_settings()
    if not settings.zap_enabled:
        logger.info("ZAP disabled — skipping active scan")
        return []

    guard.validate_target_url(target_url)
    base_url = settings.zap_api_url.rstrip("/")
    if not await _zap_reachable(base_url):
        logger.info("ZAP not reachable at %s — skipping active scan", base_url)
        return []

    try:
        findings = await asyncio.wait_for(
            _run_zap_active_scan_impl(
                base_url,
                target_url,
                guard=guard,
                max_children=max_children,
            ),
            timeout=float(settings.benchmark_active_timeout_seconds),
        )
        version = await _zap_version(base_url)
        guard_metrics = guard.metrics()
        set_pending_scanner_enrich(
            "zap",
            finding_count=len(findings),
            scanner_version=version,
            urls_scanned=1,
            target_url=target_url,
            scan_mode="active",
            **guard_metrics,
        )
        return findings
    except TimeoutError:
        logger.warning(
            "ZAP active scan hard timeout (%ss) for %s",
            settings.benchmark_active_timeout_seconds,
            target_url,
        )
        set_pending_scanner_enrich(
            "zap",
            timeout_count=1,
            urls_scanned=1,
            target_url=target_url,
            scan_mode="active",
            **guard.metrics(),
        )
        return []
    except Exception as exc:
        logger.warning("ZAP active scan failed for %s: %s", target_url, exc)
        set_pending_scanner_enrich(
            "zap",
            error_count=1,
            urls_scanned=1,
            target_url=target_url,
            scan_mode="active",
            **guard.metrics(),
        )
        return []


async def _run_zap_active_scan_impl(
    base_url: str,
    target_url: str,
    *,
    guard: ActiveBenchmarkGuard,
    max_children: int,
) -> list[RawFinding]:
    session_name = f"siber-active-{int(time.time())}"
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        await _api_get(client, "/JSON/core/action/newSession/", name=session_name, overwrite="true")
        await _configure_scope(client, target_url)
        guard.validate_request(url=target_url, method="GET")
        await _api_get(client, "/JSON/core/action/accessUrl/", url=target_url, followRedirects="false")

        spider_id = await _start_spider(client, target_url, max_children=max_children)
        if spider_id is not None:
            await _wait_spider(client, spider_id)

        active_id = await _start_active_scan(client, target_url)
        if active_id is not None:
            await _wait_active_scan(client, active_id)

        await _wait_passive_queue(client)
        alerts = await _fetch_alerts(client, target_url)

    findings = _alerts_to_findings(alerts)
    logger.info("ZAP active found %s issues for %s", len(findings), target_url)
    return findings


async def _configure_scope(client: httpx.AsyncClient, target_url: str) -> None:
    await _api_get(client, "/JSON/core/action/excludeFromProxy/", regex=".*metadata.*")
    await _api_get(client, "/JSON/core/action/excludeFromProxy/", regex=".*169\\.254\\.169\\.254.*")
    for pattern in zap_exclude_regexes():
        await _api_get(client, "/JSON/spider/action/excludeFromScan/", regex=pattern)
        await _api_get(client, "/JSON/ascan/action/excludeFromScan/", regex=pattern)
    await _api_get(
        client,
        "/JSON/context/action/newContext/",
        contextName=f"benchmark-{int(time.time())}",
    )
    await _api_get(client, "/JSON/context/action/includeInContext/", contextName="Default Context", regex=f"{target_url}.*")


async def _start_spider(
    client: httpx.AsyncClient,
    target_url: str,
    *,
    max_children: int,
) -> str | None:
    payload = await _api_get(
        client,
        "/JSON/spider/action/scan/",
        url=target_url,
        maxChildren=str(max_children),
        subtreeOnly="true",
    )
    scan_id = payload.get("scan")
    return str(scan_id) if scan_id is not None else None


async def _wait_spider(client: httpx.AsyncClient, scan_id: str) -> None:
    settings = get_settings()
    deadline = time.time() + min(settings.zap_spider_wait_seconds, settings.benchmark_active_timeout_seconds // 2)
    while time.time() < deadline:
        payload = await _api_get(client, "/JSON/spider/view/status/", scanId=scan_id)
        if int(str(payload.get("status", "100"))) >= 100:
            return
        await asyncio.sleep(2)
    logger.warning("ZAP active spider timed out for scan %s", scan_id)


async def _start_active_scan(client: httpx.AsyncClient, target_url: str) -> str | None:
    payload = await _api_get(
        client,
        "/JSON/ascan/action/scan/",
        url=target_url,
        recurse="true",
        inScopeOnly="true",
    )
    scan_id = payload.get("scan")
    return str(scan_id) if scan_id is not None else None


async def _wait_active_scan(client: httpx.AsyncClient, scan_id: str) -> None:
    settings = get_settings()
    deadline = time.time() + settings.benchmark_active_timeout_seconds
    while time.time() < deadline:
        payload = await _api_get(client, "/JSON/ascan/view/status/", scanId=scan_id)
        if int(str(payload.get("status", "100"))) >= 100:
            return
        await asyncio.sleep(3)
    logger.warning("ZAP active scan timed out for scan %s", scan_id)
    await _api_get(client, "/JSON/ascan/action/stop/", scanId=scan_id)


async def _wait_passive_queue(client: httpx.AsyncClient) -> None:
    settings = get_settings()
    deadline = time.time() + min(settings.zap_passive_wait_seconds, 30)
    while time.time() < deadline:
        payload = await _api_get(client, "/JSON/pscan/view/recordsToScan/")
        if int(str(payload.get("recordsToScan", "0"))) == 0:
            return
        await asyncio.sleep(2)


async def _fetch_alerts(client: httpx.AsyncClient, target_url: str) -> list[dict]:
    payload = await _api_get(
        client,
        "/JSON/core/view/alerts/",
        baseurl=target_url,
        start="0",
        count="5000",
    )
    alerts = payload.get("alerts") or []
    return alerts if isinstance(alerts, list) else []
