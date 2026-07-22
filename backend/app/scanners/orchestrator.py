"""Run scanners based on scan profile."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable

from app.benchmark.active_guard import guard_for_profile
from app.benchmark.security import assert_scan_profile_allowed
from app.core.config import get_settings
from app.scanners.base import RawFinding
from app.scanners.execution_stats import (
    ScannerRunStats,
    pop_pending_scanner_enrich,
    record_scanner_stats,
    reset_scanner_stats,
)
from app.scanners.exposed_paths import scan_exposed_paths
from app.scanners.nuclei import run_nuclei_scan
from app.scanners.passive_http import run_passive_http_scan
from app.scanners.secret_patterns import scan_response_secrets
from app.scanners.sensitive_data import scan_sensitive_data
from app.scanners.surface_crawl import run_surface_crawl_passive
from app.scanners.zap_active import run_zap_active_scan
from app.scanners.zap_passive import run_zap_passive_scan

logger = logging.getLogger(__name__)

ScannerFn = Callable[..., Awaitable[list[RawFinding]]]


async def _run_named_scanner(name: str, coro: Awaitable[list[RawFinding]]) -> tuple[str, list[RawFinding]]:
    started = time.perf_counter()
    timeouts = 0
    errors = 0
    findings: list[RawFinding] = []
    try:
        findings = await coro
        return name, findings
    except asyncio.CancelledError:
        raise
    except TimeoutError:
        timeouts = 1
        logger.warning("Scanner %s timed out", name)
        return name, []
    except Exception as exc:
        errors = 1
        logger.warning("Scanner %s failed: %s", name, exc)
        return name, []
    finally:
        pending = pop_pending_scanner_enrich(name)
        record_scanner_stats(
            ScannerRunStats(
                scanner_name=name,
                finding_count=len(findings),
                execution_seconds=time.perf_counter() - started,
                timeout_count=timeouts or int(pending.get("timeout_count", 0)),
                error_count=errors or int(pending.get("error_count", 0)),
                scanner_version=pending.get("scanner_version"),
                urls_scanned=int(pending.get("urls_scanned", 0)),
                extra={
                    key: value
                    for key, value in pending.items()
                    if key
                    not in {
                        "finding_count",
                        "timeout_count",
                        "error_count",
                        "scanner_version",
                        "urls_scanned",
                    }
                },
            )
        )


async def _run_scanners_parallel(
    scanners: list[tuple[str, ScannerFn, dict]],
    *,
    timeout_seconds: float,
) -> list[RawFinding]:
    """Run independent scanners concurrently with a hard overall timeout."""
    if not scanners:
        return []

    tasks = [
        asyncio.create_task(_run_named_scanner(name, fn(**kwargs)), name=f"scanner:{name}")
        for name, fn, kwargs in scanners
    ]
    done, pending = await asyncio.wait(tasks, timeout=timeout_seconds)

    for task in pending:
        task.cancel()
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)
        logger.warning(
            "%s scanner(s) did not finish within %ss — using partial results",
            len(pending),
            timeout_seconds,
        )

    findings: list[RawFinding] = []
    for task in done:
        try:
            _, batch = task.result()
            findings.extend(batch)
        except Exception as exc:
            logger.warning("Scanner task result error: %s", exc)

    return findings


def _profile_timeout_seconds(profile: str) -> float:
    settings = get_settings()
    if profile in {"benchmark-active-web", "benchmark-active-api"}:
        return float(settings.benchmark_active_timeout_seconds)
    if profile == "deep":
        return float(settings.scan_timeout_deep_seconds)
    if profile == "code":
        return float(settings.scan_timeout_code_seconds)
    if profile == "safe":
        return float(settings.scan_timeout_safe_seconds)
    return float(settings.scan_timeout_safe_seconds)


async def run_scan_for_profile(target_url: str, profile: str) -> list[RawFinding]:
    assert_scan_profile_allowed(profile)
    reset_scanner_stats()
    timeout = _profile_timeout_seconds(profile)

    if profile == "safe":
        scanners: list[tuple[str, ScannerFn, dict]] = [
            ("passive_http", run_passive_http_scan, {"target_url": target_url}),
            ("sensitive_data", scan_sensitive_data, {"target_url": target_url}),
            ("zap", run_zap_passive_scan, {"target_url": target_url, "spider": False}),
            ("nuclei", run_nuclei_scan, {"target_url": target_url, "tags": "passive"}),
        ]
    elif profile == "deep":
        scanners = [
            ("passive_http", run_passive_http_scan, {"target_url": target_url}),
            ("sensitive_data", scan_sensitive_data, {"target_url": target_url}),
            ("surface_crawl", run_surface_crawl_passive, {"target_url": target_url}),
            ("exposed_paths", scan_exposed_paths, {"target_url": target_url}),
            (
                "zap",
                run_zap_passive_scan,
                {"target_url": target_url, "spider": True},
            ),
            (
                "nuclei",
                run_nuclei_scan,
                {"target_url": target_url, "tags": "misconfig,exposure,tech"},
            ),
        ]
    elif profile == "code":
        scanners = [
            ("passive_http", run_passive_http_scan, {"target_url": target_url}),
            ("sensitive_data", scan_sensitive_data, {"target_url": target_url}),
            ("exposed_paths", scan_exposed_paths, {"target_url": target_url}),
            ("secrets", scan_response_secrets, {"target_url": target_url}),
        ]
    elif profile in {"benchmark-active-web", "benchmark-active-api"}:
        guard = guard_for_profile(profile)
        guard.validate_target_url(target_url)
        scanners = [
            (
                "zap",
                run_zap_active_scan,
                {"target_url": target_url, "guard": guard, "max_children": 5},
            ),
            (
                "nuclei",
                run_nuclei_scan,
                {"target_url": target_url, "tags": "misconfig,exposure,tech", "guard": guard},
            ),
        ]
    else:
        scanners = [
            ("passive_http", run_passive_http_scan, {"target_url": target_url}),
            ("sensitive_data", scan_sensitive_data, {"target_url": target_url}),
        ]

    findings = await _run_scanners_parallel(scanners, timeout_seconds=timeout)
    logger.info(
        "Profile %s finished with %s findings for %s (timeout=%ss)",
        profile,
        len(findings),
        target_url,
        timeout,
    )
    return findings
