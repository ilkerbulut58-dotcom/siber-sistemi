"""Passive HTTP probe — single GET, headers only."""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

SECURITY_HEADER_NAMES = (
    "strict-transport-security",
    "x-content-type-options",
    "x-frame-options",
    "content-security-policy",
    "referrer-policy",
    "permissions-policy",
)


async def probe_http(url: str) -> dict[str, object]:
    result: dict[str, object] = {"url": url}
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(url)
            headers = {k.lower(): v for k, v in response.headers.items()}
            result["status_code"] = response.status_code
            result["final_url"] = str(response.url)
            result["headers"] = {
                k: headers[k]
                for k in (
                    "server",
                    "x-powered-by",
                    "x-generator",
                    "content-type",
                    "location",
                    *SECURITY_HEADER_NAMES,
                )
                if k in headers
            }
            result["security_headers"] = {
                name: headers.get(name) for name in SECURITY_HEADER_NAMES
            }
            result["reachable"] = True
    except httpx.HTTPError as exc:
        result["reachable"] = False
        result["error"] = str(exc)
        logger.debug("HTTP probe failed for %s: %s", url, exc)

    return result
