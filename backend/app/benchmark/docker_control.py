"""Start/stop closed-network benchmark Docker fixtures."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

import httpx

from app.benchmark.manifests import ALLOWED_DOCKER_SERVICES, repo_benchmarks_root


def _compose_file() -> Path:
    return repo_benchmarks_root().parent / "docker-compose.benchmark.yml"


def start_services(service_names: list[str], *, timeout_seconds: int = 90) -> None:
    unknown = set(service_names) - ALLOWED_DOCKER_SERVICES
    if unknown:
        raise ValueError(f"Refusing to start unknown services: {sorted(unknown)}")
    if not service_names:
        return
    cmd = [
        "docker",
        "compose",
        "-f",
        str(_compose_file()),
        "--profile",
        "benchmark",
        "up",
        "-d",
        *service_names,
    ]
    subprocess.run(cmd, check=True, cwd=_compose_file().parent)
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if all(_docker_running(name) for name in service_names):
            return
        time.sleep(2)
    raise TimeoutError(f"Docker services did not start within {timeout_seconds}s: {service_names}")


def stop_services(service_names: list[str] | None = None) -> None:
    cmd = [
        "docker",
        "compose",
        "-f",
        str(_compose_file()),
        "--profile",
        "benchmark",
        "down",
        "-v",
    ]
    subprocess.run(cmd, check=False, cwd=_compose_file().parent)


def wait_for_health(url: str, *, timeout_seconds: int = 60) -> None:
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            response = httpx.get(url, timeout=5.0, follow_redirects=True)
            if response.status_code < 500:
                return
        except Exception as exc:  # noqa: BLE001 — health polling
            last_error = exc
        time.sleep(2)
    raise TimeoutError(f"Fixture health check failed for {url}: {last_error}")


def _docker_running(service_name: str) -> bool:
    result = subprocess.run(
        ["docker", "compose", "-f", str(_compose_file()), "--profile", "benchmark", "ps", "-q", service_name],
        capture_output=True,
        text=True,
        cwd=_compose_file().parent,
    )
    return bool(result.stdout.strip())
