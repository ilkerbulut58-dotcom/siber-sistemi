"""Scan profile definitions: planned scanners, scope notes, and labels."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScannerDefinition:
    id: str
    control_summary_tr: str
    control_summary_de: str


SCANNER_DEFINITIONS: dict[str, ScannerDefinition] = {
    "passive_http": ScannerDefinition(
        id="passive_http",
        control_summary_tr="HTTP/TLS başlıkları, yönlendirme, çerez ve sertifika süresi",
        control_summary_de="HTTP/TLS-Header, Weiterleitungen, Cookies, Zertifikatslaufzeit",
    ),
    "sensitive_data": ScannerDefinition(
        id="sensitive_data",
        control_summary_tr="Yanıtta hassas veri kalıpları (pasif)",
        control_summary_de="Sensible Datenmuster in Antworten (passiv)",
    ),
    "zap": ScannerDefinition(
        id="zap",
        control_summary_tr="OWASP ZAP pasif/aktif tarama",
        control_summary_de="OWASP ZAP passiv/aktiv",
    ),
    "nuclei": ScannerDefinition(
        id="nuclei",
        control_summary_tr="Nuclei şablon taraması (etiket filtreli)",
        control_summary_de="Nuclei-Vorlagen (Tag-Filter)",
    ),
    "surface_crawl": ScannerDefinition(
        id="surface_crawl",
        control_summary_tr="Sınırlı yüzey tarama (pasif keşif)",
        control_summary_de="Begrenztes Oberflächen-Crawling (passiv)",
    ),
    "exposed_paths": ScannerDefinition(
        id="exposed_paths",
        control_summary_tr="Bilinen açık dosya/yol kontrolleri (HTTP)",
        control_summary_de="Bekannte offene Pfade/Dateien (HTTP)",
    ),
    "secrets": ScannerDefinition(
        id="secrets",
        control_summary_tr="Yanıt gövdelerinde gizli anahtar kalıpları",
        control_summary_de="Secret-Muster in Antwortkörpern",
    ),
    "api_surface": ScannerDefinition(
        id="api_surface",
        control_summary_tr="API yüzey keşfi (benchmark)",
        control_summary_de="API-Oberflächenerkennung (Benchmark)",
    ),
}

PROFILE_PLANNED_SCANNERS: dict[str, list[str]] = {
    "safe": ["passive_http", "sensitive_data", "zap", "nuclei"],
    "deep": [
        "passive_http",
        "sensitive_data",
        "surface_crawl",
        "exposed_paths",
        "zap",
        "nuclei",
    ],
    "code": ["passive_http", "sensitive_data", "exposed_paths", "secrets"],
    "benchmark-active-web": ["passive_http", "zap"],
    "benchmark-active-api": ["passive_http", "api_surface", "zap"],
}

PROFILE_SCOPE_NOTES: dict[str, dict[str, str]] = {
    "code": {
        "tr": (
            "Bu profil yüklenen kaynak kodu veya arşiv taramaz; yalnızca hedef URL üzerinden "
            "HTTP/TLS, açık yol ve yanıt içi gizli kalıp kontrolleri yapar."
        ),
        "de": (
            "Dieses Profil scannt keine hochgeladenen Quellarchive; es prüft nur über die Ziel-URL "
            "HTTP/TLS, offene Pfade und Secret-Muster in Antworten."
        ),
    },
}

PROFILE_DISPLAY: dict[str, dict[str, str]] = {
    "safe": {"tr": "Güvenli Tarama", "de": "Sicherer Scan"},
    "deep": {"tr": "Derin Tarama", "de": "Tiefenscan"},
    "code": {
        "tr": "HTTP yüzey ve dosya yolu taraması",
        "de": "HTTP-Oberflächen- und Pfadscan",
    },
}


def planned_scanner_ids(profile: str) -> list[str]:
    if profile in PROFILE_PLANNED_SCANNERS:
        return list(PROFILE_PLANNED_SCANNERS[profile])
    return ["passive_http", "sensitive_data"]


def profile_scope_note(profile: str, locale: str) -> str | None:
    notes = PROFILE_SCOPE_NOTES.get(profile)
    if not notes:
        return None
    return notes.get("de" if locale == "de" else "tr")
