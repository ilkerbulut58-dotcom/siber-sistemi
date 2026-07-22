"""Validated repository fixture manifests; never accepts operator-supplied targets."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator


class ExpectedFindingFixture(BaseModel):
    expected_key: str
    title: str
    category: str | None = None
    severity: str
    affected_location: str | None = None
    description: str | None = None
    detection_required: bool = True
    accepted_alternative_keys: list[str] = Field(default_factory=list)


class BenchmarkFixture(BaseModel):
    target: str
    target_type: str
    target_reference: str
    environment: str = "benchmark"
    expected_findings: list[ExpectedFindingFixture]

    @field_validator("target_type")
    @classmethod
    def known_target_type(cls, value: str) -> str:
        if value not in {"web", "api", "android"}:
            raise ValueError("target_type must be web, api, or android")
        return value


def load_fixture(path: Path, *, fixtures_root: Path) -> BenchmarkFixture:
    """Read only a manifest committed beneath the trusted fixture root."""
    resolved_root = fixtures_root.resolve()
    resolved_path = path.resolve()
    if resolved_root not in resolved_path.parents:
        raise ValueError("Benchmark manifests must be loaded from the repository fixture root.")
    with resolved_path.open(encoding="utf-8") as stream:
        payload = yaml.safe_load(stream)
    return BenchmarkFixture.model_validate(payload)
