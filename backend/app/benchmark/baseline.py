"""Persist and compare smoke benchmark baselines on disk."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.benchmark.manifests import REALISTIC_PASSIVE_SUITES, repo_benchmarks_root

SMOKE_BASELINE_NAME = "smoke-v1.1.0"
SMOKE_BASELINE_FILENAME = f"{SMOKE_BASELINE_NAME}.json"
REALISTIC_BASELINE_NAME = "realistic-passive-v1.0.0"
REALISTIC_BASELINE_FILENAME = f"{REALISTIC_BASELINE_NAME}.json"
REALISTIC_BASELINE_V11_NAME = "realistic-passive-v1.1.0-zap-nuclei"
REALISTIC_BASELINE_V11_FILENAME = f"{REALISTIC_BASELINE_V11_NAME}.json"


def smoke_baseline_path() -> Path:
    path = repo_benchmarks_root() / "baselines" / SMOKE_BASELINE_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def realistic_baseline_path() -> Path:
    path = repo_benchmarks_root() / "baselines" / REALISTIC_BASELINE_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_smoke_baseline() -> dict[str, Any] | None:
    path = smoke_baseline_path()
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def realistic_baseline_v11_path() -> Path:
    path = repo_benchmarks_root() / "baselines" / REALISTIC_BASELINE_V11_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_realistic_baseline_v11() -> dict[str, Any] | None:
    path = realistic_baseline_v11_path()
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_realistic_baseline() -> dict[str, Any] | None:
    path = realistic_baseline_path()
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _suite_baseline_payload(root: dict[str, Any], suite: str) -> dict[str, Any] | None:
    suite_data = root.get("suites", {}).get(suite)
    if suite_data is None:
        return None
    return {
        **suite_data,
        "baseline_name": root.get("baseline_name"),
        "baseline_type": root.get("baseline_type"),
        "fixture_version": root.get("fixture_version"),
        "ground_truth_version": root.get("ground_truth_version"),
        "git_commit": root.get("git_commit"),
        "scanner_versions": root.get("scanner_versions"),
        "scope": root.get("scope"),
        "subset": root.get("subset"),
        "image_digests": root.get("image_digests"),
        "fixture_startup_seconds": root.get("fixture_startup_seconds"),
    }


def load_baseline(suite: str) -> dict[str, Any] | None:
    """Return suite metrics merged with baseline metadata."""
    if suite in REALISTIC_PASSIVE_SUITES:
        realistic = load_realistic_baseline_v11() or load_realistic_baseline()
        if realistic is None:
            return None
        return _suite_baseline_payload(realistic, suite)

    smoke = load_smoke_baseline()
    if smoke is None:
        return None
    return _suite_baseline_payload(smoke, suite)


def suite_metrics_payload(
    *,
    run_id: str,
    metrics: dict[str, Any],
    duration_seconds: float | None,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "true_positive_count": metrics.get("true_positive_count", 0),
        "false_negative_count": metrics.get("false_negative_count", 0),
        "confirmed_false_positive_count": metrics.get("confirmed_false_positive_count", 0),
        "additional_valid_finding_count": metrics.get("additional_valid_finding_count", 0),
        "duplicate_count": metrics.get("duplicate_count", 0),
        "matcher_failure_count": metrics.get("matcher_failure_count", 0),
        "scanner_error_count": metrics.get("scanner_error_count", 0),
        "precision": metrics.get("precision", 0.0),
        "recall": metrics.get("recall", 0.0),
        "f1_score": metrics.get("f1_score", 0.0),
        "duration_seconds": duration_seconds,
    }


def write_smoke_baseline(payload: dict[str, Any]) -> Path:
    path = smoke_baseline_path()
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return path


def write_realistic_baseline_v11(payload: dict[str, Any]) -> Path:
    path = realistic_baseline_v11_path()
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return path


def write_baseline(suite: str, payload: dict[str, Any]) -> Path:
    """Update one suite entry inside the tracked smoke baseline file."""
    smoke = load_smoke_baseline() or {
        "baseline_name": SMOKE_BASELINE_NAME,
        "baseline_type": "deterministic_smoke",
        "description": (
            "Controlled smoke fixture coverage only. "
            "Does not represent general real-world product security accuracy."
        ),
        "fixture_version": payload.get("fixture_version", "1.1.0"),
        "ground_truth_version": payload.get("ground_truth_version", "1.1.0"),
        "scope": ["web-smoke", "api-smoke", "android-smoke"],
        "created_at": datetime.now(UTC).isoformat(),
        "git_commit": payload.get("git_commit"),
        "scanner_versions": payload.get("scanner_versions", {}),
        "suites": {},
    }
    suites = dict(smoke.get("suites") or {})
    suites[suite] = {key: value for key, value in payload.items() if key not in {"fixture_version", "ground_truth_version", "git_commit", "scanner_versions"}}
    smoke["suites"] = suites
    if payload.get("git_commit"):
        smoke["git_commit"] = payload["git_commit"]
    if payload.get("scanner_versions"):
        smoke["scanner_versions"] = payload["scanner_versions"]
    return write_smoke_baseline(smoke)


def compute_delta(current: dict[str, Any], baseline: dict[str, Any] | None) -> dict[str, Any]:
    if baseline is None:
        return {"baseline_available": False}
    return {
        "baseline_available": True,
        "baseline_name": baseline.get("baseline_name"),
        "baseline_type": baseline.get("baseline_type"),
        "baseline_run_id": baseline.get("run_id"),
        "precision_delta": current.get("precision", 0) - baseline.get("precision", 0),
        "recall_delta": current.get("recall", 0) - baseline.get("recall", 0),
        "f1_delta": current.get("f1_score", 0) - baseline.get("f1_score", 0),
        "duration_delta": (current.get("duration_seconds") or 0) - (baseline.get("duration_seconds") or 0),
        "new_false_negatives": max(
            0,
            current.get("false_negative_count", 0) - baseline.get("false_negative_count", 0),
        ),
        "new_confirmed_false_positives": max(
            0,
            current.get("confirmed_false_positive_count", 0)
            - baseline.get("confirmed_false_positive_count", 0),
        ),
        "matcher_failure_delta": max(
            0,
            current.get("matcher_failure_count", 0) - baseline.get("matcher_failure_count", 0),
        ),
        "resolved_false_negatives": max(
            0,
            baseline.get("false_negative_count", 0) - current.get("false_negative_count", 0),
        ),
    }
