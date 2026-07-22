"""Collect pinned lab scanner versions for benchmark runs."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
from typing import Any

import httpx

from app.benchmark.manifests import repo_benchmarks_root
from app.core.config import get_settings

logger = logging.getLogger(__name__)

NUCLEI_IMAGE_VERSION = "3.3.7"


def _load_images_lock() -> dict[str, Any]:
    lock_path = repo_benchmarks_root() / "docker" / "images.lock.json"
    with lock_path.open(encoding="utf-8") as stream:
        return json.load(stream)


def _lock_entry(name: str) -> dict[str, Any] | None:
    images = _load_images_lock().get("images", {})
    entry = images.get(name)
    return entry if isinstance(entry, dict) else None


async def _zap_version(base_url: str) -> str | None:
    try:
        async with httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=10.0) as client:
            response = await client.get("/JSON/core/view/version/")
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:
        logger.info("ZAP version probe failed at %s: %s", base_url, exc)
        return None
    version = payload.get("version")
    return str(version) if version else None


async def _nuclei_version() -> str | None:
    nuclei_bin = shutil.which("nuclei")
    if nuclei_bin is None:
        return None
    try:
        process = await asyncio.create_subprocess_exec(
            nuclei_bin,
            "-version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=15.0)
    except Exception as exc:
        logger.info("Nuclei version probe failed: %s", exc)
        return None
    line = stdout.decode().strip().splitlines()
    return line[0] if line else None


async def collect_lab_scanner_versions() -> dict[str, Any]:
    """Return scanner metadata for realistic benchmark lab runs."""
    settings = get_settings()
    versions: dict[str, Any] = {"app": settings.app_version}

    zap_lock = _lock_entry("zaproxy-stable")
    if zap_lock:
        versions["zap_image"] = f"{zap_lock['image']}:{zap_lock['tag']}"
        versions["zap_image_digest"] = zap_lock.get("digest")

    nuclei_lock = _lock_entry("nuclei")
    if nuclei_lock:
        versions["nuclei_version"] = nuclei_lock.get("tag", NUCLEI_IMAGE_VERSION)
        versions["nuclei_templates_path"] = os.environ.get("NUCLEI_TEMPLATES", "/opt/nuclei-templates")

    if settings.zap_enabled:
        zap_version = await _zap_version(settings.zap_api_url)
        versions["zap"] = zap_version or "unreachable"
    else:
        versions["zap"] = "disabled"

    nuclei_version = await _nuclei_version()
    if nuclei_version:
        versions["nuclei"] = nuclei_version

    return versions
