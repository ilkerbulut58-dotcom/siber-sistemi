"""OWASP ZAP passive scan integration (no active attack scans)."""

from __future__ import annotations

import asyncio
import logging
import time

import httpx

from app.core.config import get_settings
from app.scanners.base import RawFinding

logger = logging.getLogger(__name__)

RISK_MAP = {
    "high": "high",
    "medium": "medium",
    "low": "low",
    "informational": "info",
    "info": "info",
}


async def run_zap_passive_scan(
    target_url: str,
    *,
    spider: bool = False,
    max_children: int = 8,
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
        return await asyncio.wait_for(
            _run_zap_passive_scan_impl(
                base_url,
                target_url,
                spider=spider,
                max_children=max_children,
            ),
            timeout=float(settings.zap_scan_timeout_seconds),
        )
    except TimeoutError:
        logger.warning("ZAP scan hard timeout (%ss) for %s", settings.zap_scan_timeout_seconds, target_url)
        return []
    except Exception as exc:
        logger.warning("ZAP passive scan failed for %s: %s", target_url, exc)
        return []


async def _run_zap_passive_scan_impl(
    base_url: str,
    target_url: str,
    *,
    spider: bool,
    max_children: int,
) -> list[RawFinding]:
    session_name = f"siber-{int(time.time())}"
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        await _api_get(client, "/JSON/core/action/newSession/", name=session_name, overwrite="true")
        await _api_get(client, "/JSON/core/action/accessUrl/", url=target_url)

        if spider:
            scan_id = await _start_spider(client, target_url, max_children=max_children)
            if scan_id is not None:
                await _wait_spider(client, scan_id)

        await _wait_passive_scan(client)
        alerts = await _fetch_alerts(client, target_url)

    findings = _alerts_to_findings(alerts)
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


def _alerts_to_findings(alerts: list[dict]) -> list[RawFinding]:
    findings: list[RawFinding] = []
    seen: set[tuple[str, str, str]] = set()

    for alert in alerts:
        plugin_id = str(alert.get("pluginId") or alert.get("pluginid") or "unknown")
        name = str(alert.get("name") or alert.get("alert") or plugin_id)
        url = str(alert.get("url") or "")
        key = (plugin_id, url, name)
        if key in seen:
            continue
        seen.add(key)

        risk = RISK_MAP.get(str(alert.get("risk") or "info").lower(), "info")
        findings.append(
            RawFinding(
                source_tool="zap",
                source_rule_id=f"zap-{plugin_id}",
                title=name,
                description=str(alert.get("description") or name),
                severity=risk,
                affected_url=url or str(alert.get("uri") or ""),
                remediation=str(alert.get("solution") or "") or None,
                confidence=str(alert.get("confidence") or "medium").lower(),
                evidence={
                    "plugin_id": plugin_id,
                    "cwe_id": alert.get("cweid"),
                    "wasc_id": alert.get("wascid"),
                    "param": alert.get("param"),
                    "evidence": alert.get("evidence"),
                },
            )
        )

    return findings
