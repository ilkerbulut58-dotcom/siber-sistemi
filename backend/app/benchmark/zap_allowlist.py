"""Pinned ZAP passive plugin allowlists for isolated benchmark lab scans."""

from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

from app.benchmark.manifests import repo_benchmarks_root


def _load_allowlist_file(relative_path: str) -> frozenset[str]:
    path = (repo_benchmarks_root() / relative_path).resolve()
    root = repo_benchmarks_root().resolve()
    if root not in path.parents:
        raise ValueError("ZAP allowlist path traversal blocked")
    if not path.is_file():
        raise FileNotFoundError(path)
    plugins: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.split("#", 1)[0].strip()
        if stripped:
            plugins.add(stripped)
    if not plugins:
        raise ValueError(f"ZAP allowlist {relative_path!r} has no entries")
    return frozenset(plugins)


@lru_cache(maxsize=4)
def load_zap_web_active_allowlist() -> frozenset[str]:
    return _load_allowlist_file("zap/plugin-allowlist-web-active.txt")


@lru_cache(maxsize=4)
def load_zap_api_active_allowlist() -> frozenset[str]:
    return _load_allowlist_file("zap/plugin-allowlist-api-active.txt")


def zap_allowlist_for_profile(profile: str) -> frozenset[str] | None:
    if profile == "benchmark-active-web":
        return load_zap_web_active_allowlist()
    if profile == "benchmark-active-api":
        return load_zap_api_active_allowlist()
    return None


def zap_allowlist_hash(allowlist: frozenset[str]) -> str:
    payload = "\n".join(sorted(allowlist)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
