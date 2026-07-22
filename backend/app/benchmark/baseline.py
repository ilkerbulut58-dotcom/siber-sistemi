"""Persist and compare benchmark baselines on disk."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.benchmark.manifests import repo_benchmarks_root


def baseline_path(suite: str) -> Path:
    path = repo_benchmarks_root() / "baselines" / f"{suite}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_baseline(suite: str) -> dict[str, Any] | None:
    path = baseline_path(suite)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_baseline(suite: str, payload: dict[str, Any]) -> Path:
    path = baseline_path(suite)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return path


def compute_delta(current: dict[str, Any], baseline: dict[str, Any] | None) -> dict[str, Any]:
    if baseline is None:
        return {"baseline_available": False}
    return {
        "baseline_available": True,
        "baseline_run_id": baseline.get("run_id"),
        "previous_run_id": baseline.get("previous_run_id"),
        "precision_delta": current.get("precision", 0) - baseline.get("precision", 0),
        "recall_delta": current.get("recall", 0) - baseline.get("recall", 0),
        "f1_delta": current.get("f1_score", 0) - baseline.get("f1_score", 0),
        "duration_delta": (current.get("duration_seconds") or 0) - (baseline.get("duration_seconds") or 0),
        "new_false_negatives": max(0, current.get("false_negative_count", 0) - baseline.get("false_negative_count", 0)),
        "resolved_false_negatives": max(0, baseline.get("false_negative_count", 0) - current.get("false_negative_count", 0)),
    }
