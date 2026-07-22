"""Optional Nuclei integration (runs when binary is available)."""

import asyncio
import json
import logging
import shutil

from app.core.config import get_settings
from app.scanners.base import RawFinding

logger = logging.getLogger(__name__)

SEVERITY_MAP = {
    "info": "info",
    "low": "low",
    "medium": "medium",
    "high": "high",
    "critical": "critical",
    "unknown": "info",
}


async def run_nuclei_scan(target_url: str, *, tags: str = "passive") -> list[RawFinding]:
    nuclei_bin = shutil.which("nuclei")
    if nuclei_bin is None:
        logger.info("Nuclei not installed — skipping nuclei scan")
        return []

    settings = get_settings()
    timeout = float(settings.nuclei_timeout_seconds)

    cmd = [
        nuclei_bin,
        "-u",
        target_url,
        "-tags",
        tags,
        "-severity",
        "info,low,medium,high,critical",
        "-jsonl",
        "-silent",
        "-no-color",
        "-timeout",
        "5",
        "-rate-limit",
        "50",
        "-max-host-error",
        "5",
    ]

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
            return []
    except TimeoutError:
        logger.warning("Nuclei scan timed out after %ss for %s", timeout, target_url)
        if proc is not None and proc.returncode is None:
            proc.kill()
            await proc.wait()
        return []
    except Exception as exc:
        logger.warning("Nuclei scan failed: %s", exc)
        if proc is not None and proc.returncode is None:
            proc.kill()
            await proc.wait()
        return []

    findings: list[RawFinding] = []
    for line in stdout.decode().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONError:
            continue

        template_id = item.get("template-id") or item.get("templateID") or "unknown"
        info = item.get("info") or {}
        severity = SEVERITY_MAP.get(str(info.get("severity", "info")).lower(), "info")
        matched = item.get("matched-at") or item.get("host") or target_url

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

    logger.info("Nuclei found %s issues for %s", len(findings), target_url)
    return findings
