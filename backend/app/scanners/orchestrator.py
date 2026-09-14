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
    scanner_stats_as_metrics,
    set_profile_execution_snapshot,
)
from app.scanners.profile_registry import (
    SCANNER_DEFINITIONS,
    planned_scanner_ids,
    profile_scope_note,
)
from app.scanners.exposed_paths import scan_exposed_paths
from app.scanners.nuclei import run_nuclei_scan
from app.scanners.passive_http import run_passive_http_scan
from app.scanners.secret_patterns import scan_response_secrets
from app.scanners.sensitive_data import scan_sensitive_data
from app.scanners.surface_crawl import run_surface_crawl_passive
from app.scanners.zap_active import run_zap_active_scan
from app.scanners.findings_header_enrich import enrich_findings_with_observed_headers
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
        name = (task.get_name() or "").removeprefix("scanner:")
        if name:
            record_scanner_stats(
                ScannerRunStats(
                    scanner_name=name,
                    finding_count=0,
                    timeout_count=1,
                )
            )
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
        return float(settings.benchmark_realistic_active_suite_timeout_seconds)
    if profile == "deep":
        return float(settings.scan_timeout_deep_seconds)
    if profile == "code":
        return float(settings.scan_timeout_code_seconds)
    if profile == "safe":
        return float(settings.scan_timeout_safe_seconds)
    return float(settings.scan_timeout_safe_seconds)


async def run_scan_for_profile(
    target_url: str,
    profile: str,
    *,
    verified_hostname: str | None = None,
    allow_subdomains: bool = False,
) -> list[RawFinding]:
    assert_scan_profile_allowed(profile)
    reset_scanner_stats()
    timeout = _profile_timeout_seconds(profile)

    passive_kwargs = {
        "target_url": target_url,
        "verified_hostname": verified_hostname,
        "allow_subdomains": allow_subdomains,
    }

    if profile == "safe":
        scanners: list[tuple[str, ScannerFn, dict]] = [
            ("passive_http", run_passive_http_scan, passive_kwargs),
            ("sensitive_data", scan_sensitive_data, {"target_url": target_url}),
            ("zap", run_zap_passive_scan, {"target_url": target_url, "spider": False}),
            ("nuclei", run_nuclei_scan, {"target_url": target_url, "tags": "passive"}),
        ]
    elif profile == "deep":
        scanners = [
            ("passive_http", run_passive_http_scan, passive_kwargs),
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
            ("passive_http", run_passive_http_scan, passive_kwargs),
            ("sensitive_data", scan_sensitive_data, {"target_url": target_url}),
            ("exposed_paths", scan_exposed_paths, {"target_url": target_url}),
            ("secrets", scan_response_secrets, {"target_url": target_url}),
        ]
    elif profile in {"benchmark-active-web", "benchmark-active-api"}:
        guard = guard_for_profile(profile)
        guard.validate_target_url(target_url)
        from app.scanners.passive_http import BENCHMARK_API_HEADER_SCOPE, BENCHMARK_WEB_HEADER_SCOPE

        header_scope = (
            BENCHMARK_WEB_HEADER_SCOPE if profile == "benchmark-active-web" else BENCHMARK_API_HEADER_SCOPE
        )
        scanners = [
            (
                "passive_http",
                run_passive_http_scan,
                {"target_url": target_url, "header_scope": header_scope},
            ),
        ]
        if profile == "benchmark-active-api":
            from app.scanners.api_surface_scanner import run_api_surface_scan

            scanners.append(("api_surface", run_api_surface_scan, {"target_url": target_url}))
        scanners.append(
            (
                "zap",
                run_zap_active_scan,
                {
                    "target_url": target_url,
                    "guard": guard,
                    "max_children": 5,
                    "benchmark_profile": profile,
                },
            )
        )
    else:
        scanners = [
            ("passive_http", run_passive_http_scan, passive_kwargs),
            ("sensitive_data", scan_sensitive_data, {"target_url": target_url}),
        ]

    planned = planned_scanner_ids(profile)
    findings = await _run_scanners_parallel(scanners, timeout_seconds=timeout)
    metrics = scanner_stats_as_metrics()
    passive = metrics.get("passive_http") or {}
    headers = passive.get("observed_headers") or passive.get("extra", {}).get("observed_headers")
    if isinstance(headers, dict):
        findings = enrich_findings_with_observed_headers(findings, headers)

    scanner_runs: list[dict] = []
    for sid in planned:
        m = metrics.get(sid) or {}
        if m.get("timeout_count"):
            status = "timeout"
        elif m.get("error_count"):
            status = "failed"
        elif sid in metrics:
            status = "completed"
        else:
            status = "not_run"
        defn = SCANNER_DEFINITIONS.get(sid)
        scanner_runs.append(
            {
                "scanner_id": sid,
                "status": status,
                "finding_count": m.get("finding_count", 0),
                "execution_seconds": m.get("execution_seconds"),
                "scanner_version": m.get("scanner_version"),
                "urls_scanned": m.get("urls_scanned"),
                "timeout_count": m.get("timeout_count", 0),
                "error_count": m.get("error_count", 0),
                "control_summary_tr": defn.control_summary_tr if defn else sid,
                "control_summary_de": defn.control_summary_de if defn else sid,
            }
        )

    set_profile_execution_snapshot(
        {
            "profile": profile,
            "planned_scanners": planned,
            "scanner_runs": scanner_runs,
            "code_source_scan_status": (
                "not_supported_no_upload" if profile == "code" else "not_applicable"
            ),
            "profile_scope_note_tr": profile_scope_note(profile, "tr"),
            "profile_scope_note_de": profile_scope_note(profile, "de"),
        }
    )

    logger.info(
        "Profile %s finished with %s findings for %s (timeout=%ss)",
        profile,
        len(findings),
        target_url,
        timeout,
    )
    return findings
