"""Passive regex scan on public HTML/JS responses for leaked secrets."""

from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

import httpx

from app.scanners.base import RawFinding

logger = logging.getLogger(__name__)

PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "aws-access-key",
        re.compile(r"AKIA[0-9A-Z]{16}"),
        "high",
    ),
    (
        "generic-api-key",
        re.compile(r"(?i)(api[_-]?key|apikey|secret[_-]?key)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
        "medium",
    ),
    (
        "private-key-block",
        re.compile(r"-----BEGIN (RSA |EC )?PRIVATE KEY-----"),
        "critical",
    ),
]


async def scan_response_secrets(target_url: str) -> list[RawFinding]:
    findings: list[RawFinding] = []
    parsed = urlparse(target_url)
    if not parsed.scheme or not parsed.netloc:
        return []

    urls_to_check = [target_url]
    for extra in ("/main.js", "/app.js", "/static/js/main.js"):
        urls_to_check.append(f"{parsed.scheme}://{parsed.netloc}{extra}")

    async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
        for url in urls_to_check:
            try:
                response = await client.get(url)
            except httpx.HTTPError:
                continue
            if response.status_code >= 400:
                continue
            body = response.text[:200_000]
            for rule_id, pattern, severity in PATTERNS:
                if pattern.search(body):
                    findings.append(
                        RawFinding(
                            source_tool="code_scan",
                            source_rule_id=f"secret-pattern-{rule_id}",
                            title=f"Possible secret pattern in public response ({rule_id})",
                            description=f"Pattern matched in response from {url}. Manual review required.",
                            severity=severity,
                            affected_url=url,
                            remediation="Rotate exposed secret and remove from client-side code.",
                            evidence={"pattern": rule_id},
                        )
                    )
                    break

    return findings
