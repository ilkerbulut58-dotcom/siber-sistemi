"""Report scope / scanner telemetry presentation for HTML and PDF."""

from __future__ import annotations

from app.i18n.report_strings import AUTH_SOURCE_LABELS, Locale, PROFILE_LABELS, SCANNER_STATUS_LABELS
from app.models.scan import ScanJob
from app.scanners.profile_registry import PROFILE_DISPLAY, profile_scope_note


def profile_label(scan_profile: str, locale: Locale) -> str:
    custom = PROFILE_DISPLAY.get(scan_profile, {}).get(locale)
    if custom:
        return custom
    return PROFILE_LABELS[locale].get(scan_profile, scan_profile)


def auth_source_label(raw: str | None, locale: Locale) -> str:
    if not raw:
        return "—"
    return AUTH_SOURCE_LABELS[locale].get(raw, raw)


def build_report_scope_context(scan: ScanJob, locale: Locale) -> dict:
    cfg = scan.scope_config or {}
    planned = cfg.get("planned_scope") or {}
    executed = cfg.get("executed_telemetry") or {}
    labels = _scope_labels(locale)

    scanner_rows: list[dict] = []
    for row in executed.get("scanner_runs") or []:
        status_key = row.get("status") or "unknown"
        scanner_rows.append(
            {
                "name": row.get("scanner_id", "—"),
                "status": SCANNER_STATUS_LABELS[locale].get(status_key, status_key),
                "status_key": status_key,
                "findings": row.get("finding_count", 0),
                "duration": _fmt_seconds(row.get("execution_seconds")),
                "version": row.get("scanner_version") or "—",
                "urls": row.get("urls_scanned") if row.get("urls_scanned") else labels["not_measured"],
                "controls": row.get(f"control_summary_{locale}") or row.get("control_summary_tr") or "—",
                "skip_reason": _skip_reason(row, locale),
            }
        )

    note = executed.get(f"profile_scope_note_{locale}") or profile_scope_note(scan.scan_profile, locale)
    code_status = executed.get("code_source_scan_status")
    code_status_label = _code_source_label(code_status, locale)

    planned_scanners = planned.get("planned_scanners") or []
    summary_rows = [
        {"label": labels["planned_profile"], "value": profile_label(scan.scan_profile, locale)},
        {"label": labels["auth_source"], "value": auth_source_label(planned.get("authorization_source") or scan.authorization_source, locale)},
        {"label": labels["planned_scanners"], "value": ", ".join(planned_scanners) if planned_scanners else "—"},
        {"label": labels["executed_completed"], "value": str(executed.get("scanner_runs_completed", "—"))},
        {"label": labels["executed_failed"], "value": str(executed.get("scanner_runs_failed_or_timed_out", "—"))},
        {
            "label": labels["executed_urls"],
            "value": (
                str(executed["unique_urls_scanned_sum"])
                if executed.get("unique_urls_scanned_sum") is not None
                else labels["not_measured"]
            ),
        },
        {"label": labels["executed_findings"], "value": str(executed.get("findings_persisted", scan.findings_count or "—"))},
    ]
    if code_status_label:
        summary_rows.append({"label": labels["code_source"], "value": code_status_label})

    return {
        "scope_summary_rows": summary_rows,
        "scanner_rows": scanner_rows,
        "profile_scope_note": note,
        "profile_label": profile_label(scan.scan_profile, locale),
    }


def _fmt_seconds(value: object) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):.2f}s"
    except (TypeError, ValueError):
        return "—"


def _skip_reason(row: dict, locale: Locale) -> str:
    if row.get("timeout_count"):
        return SCANNER_STATUS_LABELS[locale]["timeout"]
    if row.get("error_count"):
        return SCANNER_STATUS_LABELS[locale]["failed"]
    if row.get("status") == "not_run":
        return SCANNER_STATUS_LABELS[locale]["not_run"]
    return "—"


def _code_source_label(status: str | None, locale: Locale) -> str | None:
    if not status or status == "not_applicable":
        return None
    labels = _scope_labels(locale)
    if status == "not_supported_no_upload":
        return labels["code_source_not_supported"]
    return status


def _scope_labels(locale: Locale) -> dict[str, str]:
    if locale == "de":
        return {
            "planned_profile": "Geplant — Profil",
            "auth_source": "Autorisierung",
            "planned_scanners": "Geplante Scanner",
            "executed_completed": "Ausgeführt — abgeschlossen",
            "executed_failed": "Ausgeführt — fehlgeschlagen/Timeout",
            "executed_urls": "Ausgeführt — URLs",
            "executed_findings": "Ausgeführt — Befunde",
            "not_measured": "nicht gemessen",
            "code_source": "Quellcode-Upload",
            "code_source_not_supported": "Nicht unterstützt (kein Upload/Repo in diesem Profil)",
        }
    return {
        "planned_profile": "Planlanan — profil",
        "auth_source": "Yetki kaynağı",
        "planned_scanners": "Planlanan motorlar",
        "executed_completed": "Gerçekleşen — tamamlanan motor",
        "executed_failed": "Gerçekleşen — başarısız/zaman aşımı",
        "executed_urls": "Gerçekleşen — URL",
        "executed_findings": "Gerçekleşen — bulgu",
        "not_measured": "ölçülmedi",
        "code_source": "Kaynak kod yüklemesi",
        "code_source_not_supported": "Desteklenmiyor (bu profilde dosya/repo yüklemesi yok)",
    }
