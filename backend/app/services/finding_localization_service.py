"""Bulguları Türkçeleştir ve Plesk çözüm rehberi ekle."""

from __future__ import annotations

from urllib.parse import urlparse

from app.data.finding_catalog_tr import SEVERITY_LABEL_TR, get_catalog_entry
from app.scanners.base import RawFinding


def extract_domain(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc or parsed.path.split("/")[0]
    return host.removeprefix("www.")


def localize_raw_finding(raw: RawFinding) -> RawFinding:
    """Scanner çıktısını Türkçe katalog ile zenginleştir (in-place)."""
    domain = extract_domain(raw.affected_url)
    entry = get_catalog_entry(raw.source_rule_id, domain)

    if entry:
        raw.title = entry["title_tr"]
        raw.description = entry["description_tr"]
        raw.remediation = entry["remediation_summary_tr"]
        raw.risk_explanation = entry["risk_explanation_tr"]
        raw.remediation_steps = entry["remediation_steps_tr"]
        raw.config_file_paths = entry["config_file_paths_tr"]
        raw.config_snippet = entry["config_snippet"]
        raw.evidence = {
            **(raw.evidence or {}),
            "severity_label_tr": SEVERITY_LABEL_TR.get(raw.severity, raw.severity),
            "hosting_hint": entry["hosting"],
        }
        return raw

    # Nuclei / bilinmeyen kurallar için genel Türkçe sarmalayıcı
    sev_tr = SEVERITY_LABEL_TR.get(raw.severity, raw.severity)
    if raw.source_tool == "nuclei":
        raw.risk_explanation = (
            f"Nuclei güvenlik şablonu '{raw.source_rule_id}' bir olası zafiyet veya "
            f"yapılandırma sorunu bildirdi. Önem: {sev_tr}."
        )
        raw.remediation_steps = [
            "Bulgu açıklamasını okuyun.",
            "Kaynak kod veya sunucu yapılandırmasını ilgili bileşen için kontrol edin.",
            "Düzeltmeyi test ortamında uygulayın, ardından SIBER'de yeniden tarayın.",
        ]
        raw.config_file_paths = [
            f"Plesk → {domain} → Apache & nginx Settings",
            "İlgili uygulama kaynak kodu (Git/FTP)",
        ]
    else:
        raw.risk_explanation = (
            f"{raw.title} — {sev_tr} önem derecesinde tespit edildi."
        )
        raw.remediation_steps = raw.remediation_steps or [
            "Teknik açıklamayı inceleyin.",
            "Sunucu veya uygulama yapılandırmasını güncelleyin.",
        ]

    raw.evidence = {
        **(raw.evidence or {}),
        "severity_label_tr": sev_tr,
        "original_title": raw.title if entry is None else None,
    }
    return raw
