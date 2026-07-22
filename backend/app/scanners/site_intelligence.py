"""Collect passive site intelligence (DNS, TLS, HTTP, well-known files)."""

from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from app.scanners.asm.cdn_waf_collector import detect_cdn_waf
from app.scanners.asm.dns_collector import collect_dns_records
from app.scanners.asm.http_collector import probe_http
from app.scanners.asm.tech_collector import detect_technologies
from app.scanners.asm.tls_collector import collect_tls_info

logger = logging.getLogger(__name__)

WELL_KNOWN_PATHS = (
    "/robots.txt",
    "/.well-known/security.txt",
    "/security.txt",
    "/sitemap.xml",
)


def _parse_email_security(txt_records: list[str]) -> dict[str, Any]:
    spf = [r for r in txt_records if r.lower().startswith("v=spf1")]
    dmarc = [r for r in txt_records if r.lower().startswith("v=dmarc1")]
    dkim = [r for r in txt_records if r.lower().startswith("v=dkim1") or "dkim" in r.lower()]
    return {
        "spf_present": bool(spf),
        "dmarc_present": bool(dmarc),
        "dkim_hints": len(dkim),
        "spf_record": spf[0][:200] if spf else None,
        "dmarc_record": dmarc[0][:200] if dmarc else None,
    }


def _extract_title(html: str) -> str | None:
    match = re.search(r"<title[^>]*>([^<]{1,200})</title>", html, re.IGNORECASE)
    return match.group(1).strip() if match else None


async def _redirect_chain(url: str) -> list[dict[str, Any]]:
    chain: list[dict[str, Any]] = []
    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=False) as client:
            current = url
            for _ in range(8):
                response = await client.get(current)
                entry = {
                    "url": current,
                    "status_code": response.status_code,
                }
                chain.append(entry)
                if response.status_code not in (301, 302, 307, 308):
                    break
                location = response.headers.get("location")
                if not location:
                    break
                current = urljoin(current, location)
    except httpx.HTTPError as exc:
        chain.append({"url": url, "error": str(exc)})
    return chain


async def _fetch_well_known(base_url: str) -> dict[str, Any]:
    results: dict[str, Any] = {}
    parsed = urlparse(base_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        for path in WELL_KNOWN_PATHS:
            url = f"{origin}{path}"
            try:
                response = await client.get(url)
            except httpx.HTTPError:
                results[path] = {"found": False}
                continue
            if response.status_code >= 400:
                results[path] = {"found": False, "status_code": response.status_code}
                continue
            text = response.text[:4000]
            results[path] = {
                "found": True,
                "status_code": response.status_code,
                "preview": text[:500],
                "size": len(response.text),
            }
    return results


def _parse_cookies(set_cookie_headers: list[str]) -> list[dict[str, Any]]:
    cookies: list[dict[str, Any]] = []
    for header in set_cookie_headers:
        parts = [p.strip() for p in header.split(";")]
        if not parts:
            continue
        name_value = parts[0]
        name = name_value.split("=")[0] if "=" in name_value else name_value
        flags = {p.split("=")[0].lower(): True for p in parts[1:] if p}
        cookies.append(
            {
                "name": name,
                "secure": "secure" in flags,
                "httponly": "httponly" in flags,
                "samesite": next(
                    (p.split("=", 1)[1] for p in parts[1:] if p.lower().startswith("samesite=")),
                    None,
                ),
            }
        )
    return cookies


async def collect_site_intelligence(target_url: str) -> dict[str, Any]:
    parsed = urlparse(target_url if "://" in target_url else f"https://{target_url}")
    hostname = (parsed.hostname or target_url).lower().strip(".")
    base_url = f"{parsed.scheme or 'https'}://{hostname}"

    dns = collect_dns_records(hostname)
    tls = collect_tls_info(hostname)
    http = await probe_http(base_url if target_url.endswith("/") else f"{base_url}/")

    body_sample = ""
    set_cookies: list[str] = []
    page_title: str | None = None
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(target_url)
            body_sample = response.text[:12000]
            page_title = _extract_title(body_sample)
            raw_cookies = [
                value for key, value in response.headers.multi_items() if key.lower() == "set-cookie"
            ]
            set_cookies = raw_cookies
    except httpx.HTTPError as exc:
        logger.debug("Site intelligence body fetch failed: %s", exc)

    headers = http.get("headers") if isinstance(http.get("headers"), dict) else {}
    technologies = detect_technologies(headers, body_sample)
    cdn_waf = detect_cdn_waf(headers) if headers else []

    txt_records = list(dns.get("TXT", []))

    well_known = await _fetch_well_known(base_url)
    redirect_chain = await _redirect_chain(target_url)

    return {
        "target_url": target_url,
        "hostname": hostname,
        "dns": dns,
        "tls": tls,
        "http": http,
        "technologies": technologies,
        "cdn_waf": cdn_waf,
        "email_security": _parse_email_security(txt_records),
        "well_known": well_known,
        "redirect_chain": redirect_chain,
        "cookies": _parse_cookies(set_cookies),
        "page_title": page_title,
    }
