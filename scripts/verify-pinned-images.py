#!/usr/bin/env python3
"""Verify benchmark Docker images are pinned by tag+digest (no :latest)."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

LATEST_PATTERN = re.compile(r":latest\b|@latest\b", re.IGNORECASE)
DIGEST_PATTERN = re.compile(r"^sha256:[a-f0-9]{64}$")
PLACEHOLDER_PATTERN = re.compile(r"PLACEHOLDER", re.IGNORECASE)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_lock() -> dict:
    lock_path = repo_root() / "benchmarks" / "docker" / "images.lock.json"
    with lock_path.open(encoding="utf-8") as stream:
        return json.load(stream)


def verify_lock(payload: dict) -> list[str]:
    errors: list[str] = []
    images = payload.get("images")
    if not isinstance(images, dict) or not images:
        errors.append("images.lock.json must contain a non-empty 'images' object")
        return errors

    for name, entry in images.items():
        if not isinstance(entry, dict):
            errors.append(f"{name}: entry must be an object")
            continue
        image = entry.get("image")
        tag = entry.get("tag")
        digest = entry.get("digest")
        if not image or not isinstance(image, str):
            errors.append(f"{name}: missing 'image'")
        if not tag or not isinstance(tag, str):
            errors.append(f"{name}: missing 'tag'")
        elif tag.lower() == "latest":
            errors.append(f"{name}: tag 'latest' is forbidden")
        if not digest or not isinstance(digest, str):
            errors.append(f"{name}: missing 'digest'")
        elif PLACEHOLDER_PATTERN.search(digest):
            errors.append(f"{name}: digest is a PLACEHOLDER")
        elif not DIGEST_PATTERN.match(digest):
            errors.append(f"{name}: digest must be sha256:<64 hex chars>")

        ref = f"{image}:{tag}@{digest}" if image and tag and digest else ""
        if ref and LATEST_PATTERN.search(ref):
            errors.append(f"{name}: reference must not use latest")

    return errors


def verify_compose_files(root: Path) -> list[str]:
    errors: list[str] = []
    compose_files = [
        root / "docker-compose.realistic.yml",
        root / "docker-compose.realistic.debug.yml",
    ]
    for path in compose_files:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if LATEST_PATTERN.search(text):
            errors.append(f"{path.name}: contains forbidden :latest reference")
        if "PLACEHOLDER" in text:
            errors.append(f"{path.name}: contains PLACEHOLDER digest")
    return errors


def main() -> int:
    root = repo_root()
    lock = load_lock()
    errors = verify_lock(lock)
    errors.extend(verify_compose_files(root))
    if errors:
        for item in errors:
            print(f"ERROR: {item}", file=sys.stderr)
        return 1
    print(f"OK: verified {len(lock.get('images', {}))} pinned images")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
