"""Passive checks for accidentally exposed sensitive files (safe GET only)."""

from __future__ import annotations

import logging
import re
from urllib.parse import urljoin, urlparse

import httpx

from app.scanners.base import RawFinding

logger = logging.getLogger(__name__)

# path, severity, rule_id, content hint (optional substring to reduce false positives)
SENSITIVE_PATHS: list[tuple[str, str, str, str | None]] = [
    (".env", "high", "exposed-env-file", "="),
    (".git/HEAD", "high", "exposed-git-head", "ref:"),
    (".git/config", "high", "exposed-git-config", "[core]"),
    ("wp-config.php.bak", "high", "exposed-wp-config-bak", "DB_"),
    ("backup.zip", "medium", "exposed-backup-zip", "PK"),
    ("config.php.bak", "medium", "exposed-config-bak", "<?"),
    (".htaccess", "info", "exposed-htaccess", None),
]


def _content_matches(path: str, hint: str | None, body: str, raw: bytes, content_type: str) -> bool:
    lowered = body.lower()
    if "<html" in lowered or "<!doctype" in lowered:
        return False

    if path == ".env":
        matches = re.findall(r"^[A-Z_][A-Z0-9_]*\s*=", body, re.M)
        return len(matches) >= 2 and "text/html" not in content_type.lower()

    if hint is None:
        return True
    if hint == "PK":
        return raw[:2] == b"PK"
    return hint in body


async def scan_exposed_paths(target_url: str) -> list[RawFinding]:
    parsed = urlparse(target_url)
    if not parsed.scheme or not parsed.netloc:
        return []

    base = f"{parsed.scheme}://{parsed.netloc}"
    findings: list[RawFinding] = []

    async with httpx.AsyncClient(timeout=12.0, follow_redirects=False) as client:
        for path, severity, rule_id, hint in SENSITIVE_PATHS:
            url = urljoin(base + "/", path.lstrip("/"))
            try:
                response = await client.get(url)
            except httpx.HTTPError:
                continue

            if response.status_code != 200:
                continue

            body = response.text[:5000]
            content_type = response.headers.get("content-type", "")
            if not _content_matches(path, hint, body, response.content, content_type):
                continue

            title = (
                f"Public config file accessible: {path}"
                if path == ".htaccess"
                else f"Sensitive path exposed: {path}"
            )
            sev = severity

            findings.append(
                RawFinding(
                    source_tool="code_scan",
                    source_rule_id=rule_id,
                    title=title,
                    description=f"GET {url} returned HTTP 200 with accessible content.",
                    severity=sev,
                    affected_url=url,
                    remediation="Remove public access or move file outside web root.",
                    evidence={
                        "path": path,
                        "status_code": 200,
                        "content_length": len(response.content),
                    },
                )
            )

    logger.info("Exposed path scan found %s items for %s", len(findings), base)
    return findings
