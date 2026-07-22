"""Domain ownership verification."""

import re
import socket
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

import httpx

from app.core.security import generate_opaque_token
from app.schemas.domain import VerificationMethod

TOKEN_TTL_HOURS = 72
META_PATTERN = re.compile(
    r'<meta[^>]+name=["\']siber-verification["\'][^>]+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
META_PATTERN_ALT = re.compile(
    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']siber-verification["\']',
    re.IGNORECASE,
)


def normalize_hostname(hostname: str) -> str:
    value = hostname.strip().lower()
    if value.startswith("http://") or value.startswith("https://"):
        value = urlparse(value).netloc or value
    return value.removeprefix("www.")


def build_instructions(method: VerificationMethod, hostname: str, token: str) -> list[str]:
    if method == VerificationMethod.DNS_TXT:
        return [
            f"DNS panelinize gidin ve {hostname} için TXT kaydı ekleyin.",
            f"Host/Name: _siber-verify.{hostname}",
            f"Value: siber-verify={token}",
            "Kayıt yayıldıktan sonra 'Doğrula' butonuna basın (5-30 dk sürebilir).",
        ]
    if method == VerificationMethod.WELL_KNOWN_FILE:
        return [
            f"https://{hostname}/.well-known/siber-verification.txt dosyasını oluşturun.",
            f"Dosya içeriği yalnızca şu satır olmalı: siber-verify={token}",
            "Dosya herkese açık erişilebilir olmalı.",
        ]
    return [
        f"https://{hostname}/ ana sayfasının <head> bölümüne meta etiket ekleyin:",
        f'<meta name="siber-verification" content="{token}">',
        "Sayfa kaydedildikten sonra doğrulamayı çalıştırın.",
    ]


async def verify_dns_txt(hostname: str, token: str) -> bool:
    record_name = f"_siber-verify.{hostname}"
    expected = f"siber-verify={token}"

    def _lookup() -> bool:
        try:
            import dns.resolver

            answers = dns.resolver.resolve(record_name, "TXT")
            for rdata in answers:
                txt = b"".join(rdata.strings).decode("utf-8", errors="ignore")
                if txt.strip('"') == expected or expected in txt:
                    return True
        except Exception:
            return False
        return False

    import asyncio

    return await asyncio.to_thread(_lookup)


async def verify_well_known(hostname: str, token: str) -> bool:
    url = f"https://{hostname}/.well-known/siber-verification.txt"
    expected = f"siber-verify={token}"
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(url)
            if response.status_code == 200:
                return expected in response.text.strip()
    except Exception:
        pass
    url_http = f"http://{hostname}/.well-known/siber-verification.txt"
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(url_http)
            if response.status_code == 200:
                return expected in response.text.strip()
    except Exception:
        pass
    return False


async def verify_meta_tag(hostname: str, token: str) -> bool:
    for scheme in ("https", "http"):
        url = f"{scheme}://{hostname}/"
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.get(url)
                if response.status_code >= 400:
                    continue
                html = response.text
                for pattern in (META_PATTERN, META_PATTERN_ALT):
                    match = pattern.search(html)
                    if match and match.group(1).strip() == token:
                        return True
        except Exception:
            continue
    return False


async def run_verification(method: VerificationMethod, hostname: str, token: str) -> bool:
    if method == VerificationMethod.DNS_TXT:
        return await verify_dns_txt(hostname, token)
    if method == VerificationMethod.WELL_KNOWN_FILE:
        return await verify_well_known(hostname, token)
    return await verify_meta_tag(hostname, token)


def new_verification_token() -> tuple[str, datetime]:
    return generate_opaque_token(), datetime.now(UTC) + timedelta(hours=TOKEN_TTL_HOURS)


def hostname_resolves(hostname: str) -> bool:
    try:
        socket.getaddrinfo(hostname, None)
        return True
    except socket.gaierror:
        return False
