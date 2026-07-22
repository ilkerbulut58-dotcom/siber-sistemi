"""Per-scanner execution telemetry for benchmark lab runs."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import asdict, dataclass, field
from typing import Any

_scanner_stats: ContextVar[list[ScannerRunStats] | None] = ContextVar("scanner_run_stats", default=None)
_pending_enrich: ContextVar[dict[str, dict[str, Any]] | None] = ContextVar("scanner_pending_enrich", default=None)


@dataclass
class ScannerRunStats:
    scanner_name: str
    finding_count: int = 0
    execution_seconds: float = 0.0
    timeout_count: int = 0
    error_count: int = 0
    scanner_version: str | None = None
    urls_scanned: int = 0
    extra: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _stats_bucket() -> list[ScannerRunStats]:
    bucket = _scanner_stats.get()
    if bucket is None:
        bucket = []
        _scanner_stats.set(bucket)
    return bucket


def _pending_bucket() -> dict[str, dict[str, Any]]:
    bucket = _pending_enrich.get()
    if bucket is None:
        bucket = {}
        _pending_enrich.set(bucket)
    return bucket


def set_pending_scanner_enrich(scanner_name: str, **fields: Any) -> None:
    _pending_bucket()[scanner_name] = fields


def pop_pending_scanner_enrich(scanner_name: str) -> dict[str, Any]:
    return _pending_bucket().pop(scanner_name, {})


def reset_scanner_stats() -> None:
    _scanner_stats.set([])
    _pending_enrich.set({})


def record_scanner_stats(stats: ScannerRunStats) -> None:
    _stats_bucket().append(stats)


def get_scanner_stats() -> list[ScannerRunStats]:
    return list(_scanner_stats.get() or [])


def enrich_scanner_stats(scanner_name: str, **fields: Any) -> None:
    for item in reversed(_stats_bucket()):
        if item.scanner_name != scanner_name:
            continue
        for key, value in fields.items():
            if hasattr(item, key) and key != "extra":
                setattr(item, key, value)
            else:
                item.extra[key] = value
        break


def scanner_stats_as_metrics() -> dict[str, dict[str, Any]]:
    """Map scanner_name -> benchmark report fields."""
    metrics: dict[str, dict[str, Any]] = {}
    for item in get_scanner_stats():
        key = item.scanner_name
        metrics[key] = {
            "finding_count": item.finding_count,
            "execution_seconds": round(item.execution_seconds, 3),
            "timeout_count": item.timeout_count,
            "error_count": item.error_count,
            "scanner_version": item.scanner_version,
            "urls_scanned": item.urls_scanned,
            **item.extra,
        }
    return metrics
