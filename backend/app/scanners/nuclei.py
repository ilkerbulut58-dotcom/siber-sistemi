"""Optional Nuclei integration (runs when binary is available)."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
from typing import TYPE_CHECKING

from app.benchmark.nuclei_allowlist import (
    load_nuclei_active_template_allowlist,
    load_nuclei_template_allowlist,
)
from app.core.config import get_settings
from app.scanners.base import RawFinding
from app.scanners.execution_stats import set_pending_scanner_enrich

if TYPE_CHECKING:
    from app.benchmark.active_guard import ActiveBenchmarkGuard

logger = logging.getLogger(__name__)

SEVERITY_MAP = {
    "info": "info",
    "low": "low",
    "medium": "medium",
    "high": "high",
    "critical": "critical",
    "unknown": "info",
}


def _benchmark_lab_mode() -> bool:
    return os.environ.get("BENCHMARK_LAB_ISOLATED") == "true"


async def run_nuclei_scan(
    target_url: str,
    *,
    tags: str = "passive",
    guard: ActiveBenchmarkGuard | None = None,
) -> list[RawFinding]:
    nuclei_bin = shutil.which("nuclei")
    if nuclei_bin is None:
        logger.info("Nuclei not installed — skipping nuclei scan")
        set_pending_scanner_enrich("nuclei", error_count=1, skipped="binary_missing")
        return []

    settings = get_settings()
    timeout = float(
        settings.benchmark_active_timeout_seconds if guard else settings.nuclei_timeout_seconds
    )
    if guard is not None:
        guard.validate_target_url(target_url)
        guard.validate_request(url=target_url, method="GET")
        allowlist = load_nuclei_active_template_allowlist()
    elif _benchmark_lab_mode():
        allowlist = load_nuclei_template_allowlist()
    else:
        allowlist = frozenset()

    cmd = [
        nuclei_bin,
        "-u",
        target_url,
        "-severity",
        "info,low,medium,high,critical",
        "-jsonl",
        "-silent",
        "-no-color",
        "-timeout",
        "5",
        "-rate-limit",
        str(min(50, settings.benchmark_active_concurrency_limit * 10)),
        "-max-host-error",
        "5",
    ]
    if allowlist:
        for template_id in sorted(allowlist):
            cmd.extend(["-id", template_id])
    else:
        cmd.extend(["-tags", tags])

    version = await _nuclei_version(nuclei_bin)
    proc: asyncio.subprocess.Process | None = None
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        if proc.returncode not in (0, 1):
            logger.warning("Nuclei exited %s: %s", proc.returncode, stderr.decode()[:500])
            set_pending_scanner_enrich(
                "nuclei",
                error_count=1,
                scanner_version=version,
                urls_scanned=1,
                allowlist_size=len(allowlist),
                stderr=stderr.decode()[:200],
                scan_mode="active" if guard else "passive",
                **(guard.metrics() if guard else {}),
            )
            return []
    except TimeoutError:
        logger.warning("Nuclei scan timed out after %ss for %s", timeout, target_url)
        if proc is not None and proc.returncode is None:
            proc.kill()
            await proc.wait()
        set_pending_scanner_enrich(
            "nuclei",
            timeout_count=1,
            scanner_version=version,
            urls_scanned=1,
            allowlist_size=len(allowlist),
            scan_mode="active" if guard else "passive",
            **(guard.metrics() if guard else {}),
        )
        return []
    except Exception as exc:
        logger.warning("Nuclei scan failed: %s", exc)
        if proc is not None and proc.returncode is None:
            proc.kill()
            await proc.wait()
        set_pending_scanner_enrich(
            "nuclei",
            error_count=1,
            scanner_version=version,
            urls_scanned=1,
            allowlist_size=len(allowlist),
            scan_mode="active" if guard else "passive",
            **(guard.metrics() if guard else {}),
        )
        return []

    findings: list[RawFinding] = []
    template_ids: set[str] = set()
    for line in stdout.decode().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue

        template_id = item.get("template-id") or item.get("templateID") or "unknown"
        if allowlist and str(template_id) not in allowlist:
            continue
        template_ids.add(str(template_id))
        info = item.get("info") or {}
        severity = SEVERITY_MAP.get(str(info.get("severity", "info")).lower(), "info")
        matched = item.get("matched-at") or item.get("host") or target_url
        if guard is not None:
            try:
                guard.validate_request(url=str(matched), method="GET")
            except Exception:
                continue

        findings.append(
            RawFinding(
                source_tool="nuclei",
                source_rule_id=str(template_id),
                title=str(info.get("name") or template_id),
                description=str(info.get("description") or info.get("name") or template_id),
                severity=severity,
                affected_url=str(matched),
                remediation=str(info.get("remediation") or "") or None,
                confidence="medium",
                evidence={"matcher": item.get("matcher-name"), "type": item.get("type")},
            )
        )

    set_pending_scanner_enrich(
        "nuclei",
        finding_count=len(findings),
        scanner_version=version,
        urls_scanned=1,
        allowlist_size=len(allowlist),
        template_ids=sorted(template_ids),
        scan_mode="active" if guard else "passive",
        **(guard.metrics() if guard else {}),
    )
    logger.info(
        "Nuclei found %s issues for %s (allowlist=%s templates=%s)",
        len(findings),
        target_url,
        len(allowlist),
        sorted(template_ids),
    )
    return findings


async def _nuclei_version(nuclei_bin: str) -> str | None:
    try:
        proc = await asyncio.create_subprocess_exec(
            nuclei_bin,
            "-version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10.0)
        line = stdout.decode().strip().splitlines()
        return line[0] if line else None
    except Exception:
        return None
