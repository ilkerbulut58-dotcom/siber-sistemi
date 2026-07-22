"""Limited passive same-origin crawl (GET only, no forms submitted)."""

from __future__ import annotations

import logging
import re
from urllib.parse import urldefrag, urljoin, urlparse

import httpx

from app.scanners.base import RawFinding

logger = logging.getLogger(__name__)

HREF_RE = re.compile(r"""href=["']([^"'#]+)["']""", re.IGNORECASE)
MAX_PAGES = 8


async def run_surface_crawl_passive(target_url: str) -> list[RawFinding]:
    parsed = urlparse(target_url)
    if not parsed.scheme or not parsed.hostname:
        return []

    origin = f"{parsed.scheme}://{parsed.netloc}"
    visited: set[str] = set()
    queue: list[str] = [target_url]
    findings: list[RawFinding] = []

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        while queue and len(visited) < MAX_PAGES:
            url = queue.pop(0)
            clean = urldefrag(url)[0]
            if clean in visited:
                continue
            visited.add(clean)

            try:
                response = await client.get(clean)
            except httpx.HTTPError as exc:
                if len(visited) == 1:
                    findings.append(
                        RawFinding(
                            source_tool="deep_scan",
                            source_rule_id="crawl-unreachable",
                            title="Page unreachable during surface crawl",
                            description=str(exc),
                            severity="medium",
                            affected_url=clean,
                        )
                    )
                continue

            if response.status_code >= 500:
                findings.append(
                    RawFinding(
                        source_tool="deep_scan",
                        source_rule_id="crawl-5xx",
                        title=f"Server error on crawled page ({response.status_code})",
                        description=f"GET {clean} returned HTTP {response.status_code}.",
                        severity="medium",
                        affected_url=clean,
                        evidence={"status_code": response.status_code},
                    )
                )

            if "text/html" not in response.headers.get("content-type", "").lower():
                continue

            for match in HREF_RE.findall(response.text[:100_000]):
                href = match.strip()
                if href.startswith(("mailto:", "tel:", "javascript:", "data:")):
                    continue
                next_url = urljoin(clean, href)
                next_parsed = urlparse(next_url)
                if (
                    next_parsed.netloc == parsed.netloc
                    and next_url not in visited
                    and len(queue) + len(visited) < MAX_PAGES
                ):
                    queue.append(next_url)

    logger.info("Surface crawl checked %s pages for %s", len(visited), origin)
    return findings
