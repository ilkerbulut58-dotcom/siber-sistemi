"""OWASP ZAP passive scan integration (no active attack scans)."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import time

import httpx

from app.core.config import get_settings
from app.scanners.base import RawFinding
from app.scanners.execution_stats import set_pending_scanner_enrich

logger = logging.getLogger(__name__)

RISK_MAP = {
    "high": "high",
    "medium": "medium",
    "low": "low",
    "informational": "info",
    "info": "info",
}


def zap_session_name(prefix: str, target_url: str) -> str:
    """Deterministic ZAP session name for repeatable benchmark runs."""
    digest = hashlib.sha256(target_url.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


async def run_zap_passive_scan(
    target_url: str,
    *,
    spider: bool = False,
    max_children: int = 8,
    benchmark_profile: str | None = None,
) -> list[RawFinding]:
    settings = get_settings()
    if not settings.zap_enabled:
        logger.info("ZAP disabled — skipping")
        return []

    base_url = settings.zap_api_url.rstrip("/")
    if not await _zap_reachable(base_url):
        logger.info("ZAP not reachable at %s — skipping", base_url)
        return []

    try:
        findings = await asyncio.wait_for(
            _run_zap_passive_scan_impl(
                base_url,
                target_url,
                spider=spider,
                max_children=max_children,
                benchmark_profile=benchmark_profile,
            ),
            timeout=float(settings.zap_scan_timeout_seconds),
        )
        version = await _zap_version(base_url)
        set_pending_scanner_enrich(
            "zap",
            finding_count=len(findings),
            scanner_version=version,
            urls_scanned=1,
            target_url=target_url,
        )
        return findings
    except TimeoutError:
        logger.warning("ZAP scan hard timeout (%ss) for %s", settings.zap_scan_timeout_seconds, target_url)
        set_pending_scanner_enrich("zap", timeout_count=1, urls_scanned=1, target_url=target_url)
        return []
    except Exception as exc:
        logger.warning("ZAP passive scan failed for %s: %s", target_url, exc)
        set_pending_scanner_enrich("zap", error_count=1, urls_scanned=1, target_url=target_url)
        return []


async def _zap_version(base_url: str) -> str | None:
    try:
        async with httpx.AsyncClient(base_url=base_url, timeout=5.0) as client:
            response = await client.get("/JSON/core/view/version/")
            if response.status_code == 200:
                return str(response.json().get("version") or "")
    except Exception:
        return None
    return None


async def _run_zap_passive_scan_impl(
    base_url: str,
    target_url: str,
    *,
    spider: bool,
    max_children: int,
    benchmark_profile: str | None = None,
) -> list[RawFinding]:
    session_name = zap_session_name("siber", target_url)
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        await _reset_zap_lab_state(client)
        await _api_get(client, "/JSON/core/action/newSession/", name=session_name, overwrite="true")
        await _api_get(client, "/JSON/core/action/accessUrl/", url=target_url)

        if spider:
            scan_id = await _start_spider(client, target_url, max_children=max_children)
            if scan_id is not None:
                await _wait_spider(client, scan_id)

        await _wait_passive_scan(client)
        alerts = await _fetch_alerts(client, target_url)

    findings = _alerts_to_findings(alerts, benchmark_profile=benchmark_profile)
    logger.info("ZAP passive found %s issues for %s (spider=%s)", len(findings), target_url, spider)
    return findings


async def _zap_reachable(base_url: str) -> bool:
    try:
        async with httpx.AsyncClient(base_url=base_url, timeout=5.0) as client:
            response = await client.get("/JSON/core/view/version/")
            return response.status_code == 200 and response.json().get("version")
    except Exception:
        return False


async def _api_get(client: httpx.AsyncClient, path: str, **params: str | int) -> dict:
    response = await client.get(path, params={k: str(v) for k, v in params.items()})
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, dict) and payload.get("Result") == "ERROR":
        raise RuntimeError(str(payload.get("Message") or "ZAP API error"))
    return payload


async def _start_spider(
    client: httpx.AsyncClient,
    target_url: str,
    *,
    max_children: int,
    max_depth: int = 3,
) -> str | None:
    payload = await _api_get(
        client,
        "/JSON/spider/action/scan/",
        url=target_url,
        maxChildren=str(max_children),
        maxDepth=str(max_depth),
        subtreeOnly="true",
    )
    scan_id = payload.get("scan")
    return str(scan_id) if scan_id is not None else None


async def _wait_spider(client: httpx.AsyncClient, scan_id: str) -> None:
    settings = get_settings()
    deadline = time.time() + settings.zap_spider_wait_seconds
    last_progress = -1
    stalled_rounds = 0
    while time.time() < deadline:
        payload = await _api_get(client, "/JSON/spider/view/status/", scanId=scan_id)
        progress = int(str(payload.get("status", "100")))
        if progress >= 100:
            return
        if progress == last_progress:
            stalled_rounds += 1
            if stalled_rounds >= 5:
                logger.warning("ZAP spider stalled at %s%% for scan %s", progress, scan_id)
                return
        else:
            stalled_rounds = 0
            last_progress = progress
        await asyncio.sleep(2)
    logger.warning("ZAP spider timed out for scan %s", scan_id)


async def _wait_passive_scan(client: httpx.AsyncClient) -> None:
    settings = get_settings()
    deadline = time.time() + settings.zap_passive_wait_seconds
    idle_rounds = 0
    last_remaining: int | None = None
    stalled_rounds = 0

    await asyncio.sleep(2)

    while time.time() < deadline:
        payload = await _api_get(client, "/JSON/pscan/view/recordsToScan/")
        remaining = int(str(payload.get("recordsToScan", "0")))
        if remaining == 0:
            idle_rounds += 1
            if idle_rounds >= 2:
                return
        else:
            idle_rounds = 0
            if remaining == last_remaining:
                stalled_rounds += 1
                if stalled_rounds >= 5:
                    logger.warning(
                        "ZAP passive queue stalled at %s records — continuing with partial results",
                        remaining,
                    )
                    return
            else:
                stalled_rounds = 0
            last_remaining = remaining
        await asyncio.sleep(2)
    logger.warning("ZAP passive scan queue did not drain in time")


async def _reset_zap_lab_state(client: httpx.AsyncClient) -> None:
    """Stop in-flight ZAP work and clear alerts so shared daemon state does not leak between runs."""
    if os.environ.get("BENCHMARK_LAB_ISOLATED") != "true":
        return
    for path in (
        "/JSON/ascan/action/stopAllScans/",
        "/JSON/spider/action/stopAllScans/",
        "/JSON/core/action/deleteAllAlerts/",
    ):
        try:
            await _api_get(client, path)
        except Exception as exc:
            logger.debug("ZAP reset step %s skipped: %s", path, exc)


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


def _alerts_to_findings(
    alerts: list[dict],
    *,
    benchmark_profile: str | None = None,
) -> list[RawFinding]:
    from app.benchmark.alert_dedup import (
        collapse_groups_by_plugin_id,
        filter_zap_alerts_by_plugin_allowlist,
        group_zap_alerts,
        grouped_alerts_to_raw_findings,
    )
    from app.benchmark.zap_allowlist import zap_allowlist_for_profile

    allowlist = zap_allowlist_for_profile(benchmark_profile) if benchmark_profile else None
    if allowlist is not None:
        before = len(alerts)
        alerts = filter_zap_alerts_by_plugin_allowlist(alerts, allowlist)
        logger.info(
            "ZAP benchmark allowlist (%s) kept %s/%s alerts",
            benchmark_profile,
            len(alerts),
            before,
        )

    groups = group_zap_alerts(alerts)
    if allowlist is not None:
        groups = collapse_groups_by_plugin_id(groups)
    return grouped_alerts_to_raw_findings(groups, risk_map=RISK_MAP)
