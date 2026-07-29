"""Domain ownership verification."""

import re
import socket
from datetime import UTC, datetime, timedelta

import httpx

from app.core.security import generate_opaque_token
from app.schemas.domain import VerificationMethod
from app.security.hostname_auth import normalize_hostname

__all__ = [
    "build_instruction_fields",
    "build_instructions",
    "hostname_resolves",
    "new_verification_token",
    "normalize_hostname",
    "run_verification",
    "run_verification_detailed",
]

TOKEN_TTL_HOURS = 72
META_PATTERN = re.compile(
    r'<meta[^>]+name=["\']siber-verification["\'][^>]+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
META_PATTERN_ALT = re.compile(
    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']siber-verification["\']',
    re.IGNORECASE,
)


def build_instruction_fields(
    method: VerificationMethod, hostname: str, token: str
) -> dict[str, str | int | None]:
    """Structured verification fields for UI copy buttons."""
    if method == VerificationMethod.DNS_TXT:
        return {
            "dns_host": f"_siber-verify.{hostname}",
            "dns_value": f"siber-verify={token}",
            "ttl_recommendation_seconds": 300,
            "well_known_url": None,
            "well_known_content": None,
            "meta_tag_html": None,
        }
    if method == VerificationMethod.WELL_KNOWN_FILE:
        content = f"siber-verify={token}"
        return {
            "dns_host": None,
            "dns_value": None,
            "ttl_recommendation_seconds": None,
            "well_known_url": f"https://{hostname}/.well-known/siber-verification.txt",
            "well_known_content": content,
            "meta_tag_html": None,
        }
    return {
        "dns_host": None,
        "dns_value": None,
        "ttl_recommendation_seconds": None,
        "well_known_url": None,
        "well_known_content": None,
        "meta_tag_html": f'<meta name="siber-verification" content="{token}">',
    }


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


async def verify_dns_txt_detailed(hostname: str, token: str) -> tuple[bool, str | None]:
    record_name = f"_siber-verify.{hostname}"
    expected = f"siber-verify={token}"

    def _lookup() -> tuple[bool, str | None]:
        try:
            import dns.resolver

            answers = dns.resolver.resolve(record_name, "TXT")
            saw_record = False
            for rdata in answers:
                saw_record = True
                txt = b"".join(rdata.strings).decode("utf-8", errors="ignore")
                if txt.strip('"') == expected or expected in txt:
                    return True, None
            if saw_record:
                return False, "DNS_TOKEN_MISMATCH"
            return False, "DNS_RECORD_NOT_FOUND"
        except dns.resolver.NXDOMAIN:
            return False, "DNS_RECORD_NOT_FOUND"
        except dns.resolver.NoAnswer:
            return False, "DNS_RECORD_NOT_FOUND"
        except Exception:
            return False, "NETWORK_ERROR"

    import asyncio

    return await asyncio.to_thread(_lookup)


async def verify_dns_txt(hostname: str, token: str) -> bool:
    ok, _ = await verify_dns_txt_detailed(hostname, token)
    return ok


async def verify_well_known_detailed(hostname: str, token: str) -> tuple[bool, str | None]:
    url = f"https://{hostname}/.well-known/siber-verification.txt"
    expected = f"siber-verify={token}"
    saw_response = False
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(url)
            saw_response = True
            if response.status_code == 200:
                if expected in response.text.strip():
                    return True, None
    except Exception:
        if not saw_response:
            pass
    url_http = f"http://{hostname}/.well-known/siber-verification.txt"
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(url_http)
            if response.status_code == 200:
                if expected in response.text.strip():
                    return True, None
                return False, "WELL_KNOWN_CONTENT_MISMATCH"
            return False, "WELL_KNOWN_FILE_NOT_FOUND"
    except Exception:
        return False, "NETWORK_ERROR"


async def verify_well_known(hostname: str, token: str) -> bool:
    ok, _ = await verify_well_known_detailed(hostname, token)
    return ok


async def verify_meta_tag_detailed(hostname: str, token: str) -> tuple[bool, str | None]:
    saw_page = False
    for scheme in ("https", "http"):
        url = f"{scheme}://{hostname}/"
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.get(url)
                if response.status_code >= 400:
                    continue
                saw_page = True
                html = response.text
                for pattern in (META_PATTERN, META_PATTERN_ALT):
                    match = pattern.search(html)
                    if match and match.group(1).strip() == token:
                        return True, None
                    if match:
                        return False, "META_TAG_MISMATCH"
        except Exception:
            continue
    if saw_page:
        return False, "META_TAG_NOT_FOUND"
    return False, "NETWORK_ERROR"


async def verify_meta_tag(hostname: str, token: str) -> bool:
    ok, _ = await verify_meta_tag_detailed(hostname, token)
    return ok


async def run_verification_detailed(
    method: VerificationMethod, hostname: str, token: str
) -> tuple[bool, str | None]:
    if method == VerificationMethod.DNS_TXT:
        return await verify_dns_txt_detailed(hostname, token)
    if method == VerificationMethod.WELL_KNOWN_FILE:
        return await verify_well_known_detailed(hostname, token)
    return await verify_meta_tag_detailed(hostname, token)


async def run_verification(method: VerificationMethod, hostname: str, token: str) -> bool:
    ok, _ = await run_verification_detailed(method, hostname, token)
    return ok


def new_verification_token() -> tuple[str, datetime]:
    return generate_opaque_token(), datetime.now(UTC) + timedelta(hours=TOKEN_TTL_HOURS)


def hostname_resolves(hostname: str) -> bool:
    try:
        socket.getaddrinfo(hostname, None)
        return True
    except socket.gaierror:
        return False
