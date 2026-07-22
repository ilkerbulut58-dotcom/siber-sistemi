"""Start/stop closed-network benchmark Docker fixtures."""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import httpx

from app.benchmark.manifests import ALLOWED_DOCKER_SERVICES, repo_benchmarks_root

REALISTIC_STARTUP_SECONDS = 120
REALISTIC_HEALTH_SECONDS = 120


def _repo_root() -> Path:
    return repo_benchmarks_root().parent


def _compose_file(*, realistic: bool = False) -> Path:
    if realistic:
        return _repo_root() / "docker-compose.realistic.yml"
    return _repo_root() / "docker-compose.benchmark.yml"


def _compose_profile(*, realistic: bool = False) -> str:
    return "realistic" if realistic else "benchmark"


def _benchmark_ca_path() -> Path | None:
    env_path = os.environ.get("BENCHMARK_CA_CERT_PATH", "").strip()
    if env_path:
        path = Path(env_path)
        if path.is_file():
            return path
    default = repo_benchmarks_root() / "docker" / "realistic" / "certs" / "ca.crt"
    return default if default.is_file() else None


def _httpx_verify():
    ca_path = _benchmark_ca_path()
    if ca_path is not None:
        return str(ca_path)
    return True


def is_realistic_service(service_name: str) -> bool:
    return service_name.startswith("benchmark-juice") or service_name.startswith("benchmark-crapi")


def start_services(
    service_names: list[str],
    *,
    timeout_seconds: int = 90,
    realistic: bool = False,
) -> None:
    unknown = set(service_names) - ALLOWED_DOCKER_SERVICES
    if unknown:
        raise ValueError(f"Refusing to start unknown services: {sorted(unknown)}")
    if not service_names:
        return
    if realistic:
        timeout_seconds = max(timeout_seconds, REALISTIC_STARTUP_SECONDS)
    cmd = [
        "docker",
        "compose",
        "-f",
        str(_compose_file(realistic=realistic)),
        "--profile",
        _compose_profile(realistic=realistic),
        "up",
        "-d",
        *service_names,
    ]
    subprocess.run(cmd, check=True, cwd=_repo_root())
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if all(_docker_running(name, realistic=realistic) for name in service_names):
            return
        time.sleep(2)
    raise TimeoutError(f"Docker services did not start within {timeout_seconds}s: {service_names}")


def stop_services(service_names: list[str] | None = None, *, realistic: bool = False) -> None:
    cmd = [
        "docker",
        "compose",
        "-f",
        str(_compose_file(realistic=realistic)),
        "--profile",
        _compose_profile(realistic=realistic),
        "down",
        "-v",
    ]
    subprocess.run(cmd, check=False, cwd=_repo_root())


def wait_for_health(url: str, *, timeout_seconds: int = 60) -> None:
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None
    verify = _httpx_verify()
    while time.time() < deadline:
        try:
            response = httpx.get(url, timeout=5.0, follow_redirects=True, verify=verify)
            if response.status_code < 500:
                return
        except Exception as exc:  # noqa: BLE001 — health polling
            last_error = exc
        time.sleep(2)
    raise TimeoutError(f"Fixture health check failed for {url}: {last_error}")


def _docker_running(service_name: str, *, realistic: bool = False) -> bool:
    result = subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            str(_compose_file(realistic=realistic)),
            "--profile",
            _compose_profile(realistic=realistic),
            "ps",
            "-q",
            service_name,
        ],
        capture_output=True,
        text=True,
        cwd=_repo_root(),
    )
    return bool(result.stdout.strip())


def load_images_lock() -> dict:
    lock_path = repo_benchmarks_root() / "docker" / "images.lock.json"
    with lock_path.open(encoding="utf-8") as stream:
        return json.load(stream)
