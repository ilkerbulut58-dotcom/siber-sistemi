"""ASM attack surface discovery orchestrator — passive and safe only."""

from __future__ import annotations

import asyncio
import logging
from urllib.parse import urlparse

import httpx

from app.asm.types import DiscoveredAsset
from app.scanners.asm.cdn_waf_collector import detect_cdn_waf
from app.scanners.asm.dns_collector import collect_dns_records
from app.scanners.asm.http_collector import probe_http
from app.scanners.asm.subdomain_collector import discover_subdomains
from app.scanners.asm.tech_collector import detect_technologies
from app.scanners.asm.tls_collector import collect_tls_info

logger = logging.getLogger(__name__)


def _normalize_root(target_url: str) -> tuple[str, str]:
    parsed = urlparse(target_url if "://" in target_url else f"https://{target_url}")
    hostname = (parsed.hostname or target_url).lower().strip(".")
    scheme = parsed.scheme or "https"
    base_url = f"{scheme}://{hostname}"
    return hostname, base_url


async def discover_attack_surface(
    target_url: str,
    *,
    max_subdomains: int = 30,
    max_hosts_probe: int = 15,
) -> list[DiscoveredAsset]:
    root_domain, base_url = _normalize_root(target_url)
    assets: list[DiscoveredAsset] = []

    dns_records = await asyncio.to_thread(collect_dns_records, root_domain)
    root_asset = DiscoveredAsset(
        asset_type="domain",
        identifier=root_domain,
        url=base_url,
        metadata={"dns": dns_records},
        exposure_score=1.0,
    )
    assets.append(root_asset)

    for ip in dns_records.get("A", []) + dns_records.get("AAAA", []):
        assets.append(
            DiscoveredAsset(
                asset_type="ip",
                identifier=ip,
                parent_identifier=root_domain,
                metadata={"resolved_from": root_domain},
                exposure_score=0.9,
            )
        )

    subdomains = await discover_subdomains(root_domain, max_results=max_subdomains)
    hosts_to_probe = subdomains[:max_hosts_probe]

    async def _probe_host(host: str) -> DiscoveredAsset | None:
        host_url = f"https://{host}/"
        http_meta = await probe_http(host_url)
        if not http_meta.get("reachable"):
            if host == root_domain:
                return None
            return DiscoveredAsset(
                asset_type="subdomain" if host != root_domain else "domain",
                identifier=host,
                parent_identifier=root_domain if host != root_domain else None,
                url=host_url,
                status="inactive",
                metadata={"http": http_meta},
                exposure_score=0.6,
            )

        headers = http_meta.get("headers") or {}
        if not isinstance(headers, dict):
            headers = {}

        body_sample = ""
        try:
            async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
                resp = await client.get(host_url)
                body_sample = resp.text[:8000]
        except httpx.HTTPError:
            pass

        tls_info = await asyncio.to_thread(collect_tls_info, host)
        technologies = detect_technologies(headers, body_sample)
        cdn_waf = detect_cdn_waf(headers)

        host_dns = await asyncio.to_thread(collect_dns_records, host) if host != root_domain else {}

        asset_type = "subdomain" if host != root_domain else "domain"
        exposure = 1.0
        if asset_type == "subdomain":
            exposure = 1.15
        if any(t.get("name", "").lower() in ("admin", "staging", "dev", "test") for t in []):
            pass
        for prefix in ("admin.", "staging.", "dev.", "test."):
            if host.startswith(prefix):
                exposure = 1.35
                break

        metadata = {
            "http": http_meta,
            "tls": tls_info,
            "technologies": technologies,
            "cdn_waf": cdn_waf,
        }
        if host_dns:
            metadata["dns"] = host_dns

        return DiscoveredAsset(
            asset_type=asset_type,
            identifier=host,
            parent_identifier=root_domain if host != root_domain else None,
            url=host_url,
            metadata=metadata,
            exposure_score=exposure,
        )

    probe_results = await asyncio.gather(*(_probe_host(h) for h in hosts_to_probe))
    seen = {root_domain}
    for item in probe_results:
        if item is None:
            continue
        if item.identifier in seen:
            for idx, existing in enumerate(assets):
                if existing.identifier == item.identifier:
                    assets[idx] = item
                    break
        else:
            assets.append(item)
            seen.add(item.identifier)

    for host in subdomains:
        if host not in seen:
            assets.append(
                DiscoveredAsset(
                    asset_type="subdomain",
                    identifier=host,
                    parent_identifier=root_domain,
                    url=f"https://{host}/",
                    status="unknown",
                    metadata={"discovered_via": "passive_dns_or_ct"},
                    exposure_score=1.1,
                )
            )
            seen.add(host)

    return assets
