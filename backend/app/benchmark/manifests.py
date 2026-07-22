"""Allowlisted benchmark suite manifests — no operator-supplied targets."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator

from app.benchmark.fixtures import BenchmarkFixture, load_fixture

SMOKE_SUITES = frozenset({"web-smoke", "api-smoke", "android-smoke"})
REALISTIC_PASSIVE_SUITES = frozenset({"web-realistic-passive", "api-realistic-passive"})
ACTIVE_REALISTIC_SUITES = frozenset({"web-realistic-active", "api-realistic-active"})
ALLOWED_SUITES = SMOKE_SUITES | REALISTIC_PASSIVE_SUITES | ACTIVE_REALISTIC_SUITES

SMOKE_DOCKER_SERVICES = frozenset({"benchmark-web", "benchmark-api"})
REALISTIC_DOCKER_SERVICES = frozenset(
    {
        "benchmark-juice-shop",
        "benchmark-juice-proxy",
        "benchmark-crapi-web",
        "benchmark-crapi-identity",
        "benchmark-crapi-community",
        "benchmark-crapi-workshop",
        "benchmark-crapi-mailhog",
        "benchmark-crapi-postgres",
        "benchmark-crapi-mongo",
        "benchmark-crapi-proxy",
    }
)
ALLOWED_DOCKER_SERVICES = SMOKE_DOCKER_SERVICES | REALISTIC_DOCKER_SERVICES

SMOKE_TARGET_HOSTS = frozenset(
    {
        "127.0.0.1",
        "localhost",
        "benchmark-web",
        "benchmark-api",
    }
)
REALISTIC_TARGET_HOSTS = frozenset(
    {
        "benchmark-juice-proxy",
        "benchmark-crapi-proxy",
        "benchmark-juice-shop",
        "benchmark-crapi-web",
    }
)
ALLOWED_TARGET_HOSTS = SMOKE_TARGET_HOSTS | REALISTIC_TARGET_HOSTS


class SuiteTargetManifest(BaseModel):
    name: str
    target_type: str
    scan_profile: str | None = "safe"
    docker_services: list[str] = Field(default_factory=list)
    health_url: str | None = None
    target_url: str | None = None
    hostname: str | None = None
    artifact_script: str | None = None
    ground_truth: str
    subset_manifest: str | None = None
    blocked: bool = False

    @field_validator("docker_services")
    @classmethod
    def validate_services(cls, services: list[str]) -> list[str]:
        unknown = set(services) - ALLOWED_DOCKER_SERVICES
        if unknown:
            raise ValueError(f"Unknown docker service(s): {sorted(unknown)}")
        return services

    @field_validator("target_url", "health_url")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        if value is None:
            return value
        from urllib.parse import urlparse

        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("Only http/https fixture URLs are allowed")
        if parsed.hostname not in ALLOWED_TARGET_HOSTS:
            raise ValueError(f"Target host {parsed.hostname!r} is not allowlisted")
        if parsed.username or parsed.password:
            raise ValueError("Embedded credentials in fixture URLs are forbidden")
        return value


class BenchmarkSuiteManifest(BaseModel):
    suite: str
    version: str
    fixture_set: str = "smoke"
    description: str | None = None
    targets: list[SuiteTargetManifest]
    blocked: bool = False

    @field_validator("suite")
    @classmethod
    def validate_suite(cls, value: str) -> str:
        if value not in ALLOWED_SUITES:
            raise ValueError(f"Suite {value!r} is not allowlisted")
        return value


def repo_benchmarks_root() -> Path:
    module_root = Path(__file__).resolve()
    container_layout = module_root.parents[2] / "benchmarks"
    repo_layout = module_root.parents[3] / "benchmarks"
    if container_layout.is_dir():
        return container_layout
    return repo_layout


def load_suite_manifest(suite: str) -> BenchmarkSuiteManifest:
    if suite not in ALLOWED_SUITES:
        raise ValueError(f"Suite {suite!r} is not allowlisted")
    root = repo_benchmarks_root()
    path = (root / "manifests" / f"{suite}.yaml").resolve()
    if root.resolve() not in path.parents:
        raise ValueError("Manifest path traversal blocked")
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open(encoding="utf-8") as stream:
        payload = yaml.safe_load(stream)
    manifest = BenchmarkSuiteManifest.model_validate(payload)
    if manifest.suite != suite:
        raise ValueError("Manifest suite name mismatch")
    return manifest


def load_ground_truth(relative_path: str) -> BenchmarkFixture:
    root = repo_benchmarks_root()
    resolved = (root / relative_path).resolve()
    if root.resolve() not in resolved.parents:
        raise ValueError("Ground truth path traversal blocked")
    return load_fixture(resolved, fixtures_root=root)
