"""Passive subdomain discovery — CT logs + limited DNS checks on authorized domain only."""

from __future__ import annotations

import logging
from urllib.parse import quote

import dns.resolver
import httpx

logger = logging.getLogger(__name__)

# Small passive wordlist — not aggressive brute force
COMMON_SUBDOMAINS = (
    "www",
    "mail",
    "api",
    "admin",
    "dev",
    "staging",
    "test",
    "cdn",
    "static",
    "app",
    "portal",
    "blog",
    "shop",
    "m",
    "mobile",
)


async def discover_subdomains(root_domain: str, *, max_results: int = 30) -> list[str]:
    found: set[str] = set()
    found.add(root_domain)

    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            url = f"https://crt.sh/?q={quote(f'%.{root_domain}')}&output=json"
            response = await client.get(url)
            if response.status_code == 200:
                for entry in response.json():
                    name = str(entry.get("name_value", "")).lower()
                    for part in name.split("\n"):
                        part = part.strip().lstrip("*.")
                        if part.endswith(f".{root_domain}") or part == root_domain:
                            if part.count(".") <= root_domain.count(".") + 1:
                                found.add(part)
        except Exception as exc:
            logger.debug("crt.sh lookup failed for %s: %s", root_domain, exc)

    resolver = dns.resolver.Resolver()
    resolver.lifetime = 5.0
    for sub in COMMON_SUBDOMAINS:
        candidate = f"{sub}.{root_domain}"
        try:
            resolver.resolve(candidate, "A")
            found.add(candidate)
        except Exception:
            try:
                resolver.resolve(candidate, "AAAA")
                found.add(candidate)
            except Exception:
                continue

    sorted_hosts = sorted(found)
    return sorted_hosts[:max_results]
