"""Load and hash the pinned Nuclei template allowlist for benchmark lab runs."""

from __future__ import annotations

import hashlib
from functools import lru_cache

from app.benchmark.manifests import repo_benchmarks_root


@lru_cache(maxsize=1)
def load_nuclei_template_allowlist() -> frozenset[str]:
    return _load_allowlist_file("nuclei/template-allowlist.txt")


@lru_cache(maxsize=1)
def load_nuclei_active_template_allowlist() -> frozenset[str]:
    return _load_allowlist_file("nuclei/template-allowlist-active.txt")


def _load_allowlist_file(relative_path: str) -> frozenset[str]:
    path = repo_benchmarks_root() / relative_path
    if not path.is_file():
        return frozenset()
    ids: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        ids.add(stripped)
    return frozenset(ids)


def nuclei_allowlist_hash() -> str:
    allowlist = load_nuclei_template_allowlist()
    payload = "\n".join(sorted(allowlist)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def nuclei_active_allowlist_hash() -> str:
    allowlist = load_nuclei_active_template_allowlist()
    payload = "\n".join(sorted(allowlist)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
