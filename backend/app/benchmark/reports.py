"""JSON and HTML benchmark quality reports."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.benchmark.manifests import repo_benchmarks_root
from app.core.config import get_settings


def reports_dir() -> Path:
    path = repo_benchmarks_root() / "reports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_reports(
    *,
    run_id: str,
    payload: dict[str, Any],
) -> tuple[Path, Path]:
    json_path = reports_dir() / f"{run_id}.json"
    html_path = reports_dir() / f"{run_id}.html"
    json_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    html_path.write_text(_render_html(payload), encoding="utf-8")
    return json_path, html_path


def _render_html(payload: dict[str, Any]) -> str:
    metrics = payload.get("metrics", {})
    rows = "".join(
        f"<tr><td>{key}</td><td>{value}</td></tr>"
        for key, value in metrics.items()
    )
    missed = payload.get("missed_findings", [])
    missed_rows = "".join(
        f"<li>{item.get('expected_key')} — {item.get('title')}</li>" for item in missed
    )
    return f"""<!DOCTYPE html>
<html lang="tr"><head><meta charset="utf-8"><title>Benchmark Report</title>
<style>body{{font-family:Segoe UI,sans-serif;background:#0b1220;color:#e5e7eb;padding:2rem}}
table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #334155;padding:.5rem}}</style>
</head><body>
<h1>Detection Quality Report</h1>
<p>Suite: {payload.get('suite')} · Commit: {payload.get('git_commit')} · Version: {payload.get('app_version')}</p>
<h2>Metrics</h2><table>{rows}</table>
<h2>Missed findings</h2><ul>{missed_rows or '<li>None</li>'}</ul>
<p>Generated at {datetime.now(UTC).isoformat()}</p>
</body></html>"""


def build_report_payload(
    *,
    suite: str,
    fixture_version: str,
    ground_truth_version: str,
    git_commit: str | None,
    scanner_versions: dict[str, Any] | None,
    metrics: dict[str, Any],
    missed_findings: list[dict[str, Any]],
    false_positive_rules: list[dict[str, Any]],
    baseline_delta: dict[str, Any] | None,
    duration_seconds: float | None,
    scanner_errors: list[str],
) -> dict[str, Any]:
    settings = get_settings()
    return {
        "suite": suite,
        "app_version": settings.app_version,
        "git_commit": git_commit,
        "fixture_version": fixture_version,
        "ground_truth_version": ground_truth_version,
        "scanner_versions": scanner_versions or {},
        "metrics": metrics,
        "missed_findings": missed_findings,
        "false_positive_rules": false_positive_rules,
        "baseline_delta": baseline_delta,
        "duration_seconds": duration_seconds,
        "scanner_errors": scanner_errors,
        "generated_at": datetime.now(UTC).isoformat(),
    }
