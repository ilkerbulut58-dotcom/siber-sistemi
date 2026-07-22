"""Validated repository fixture manifests; never accepts operator-supplied targets."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator

AutomationSupportLiteral = Literal["supported", "partially_supported", "manual_only", "unsupported"]


class FrameworkRef(BaseModel):
    framework: str
    control: str


class ExpectedFindingFixture(BaseModel):
    expected_key: str
    title: str
    category: str | None = None
    severity: str
    affected_location: str | None = None
    description: str | None = None
    detection_required: bool = True
    accepted_alternative_keys: list[str] = Field(default_factory=list)
    automation_support: AutomationSupportLiteral = "supported"
    framework_refs: list[FrameworkRef] = Field(default_factory=list)

    @field_validator("automation_support")
    @classmethod
    def validate_automation_support(cls, value: str) -> str:
        allowed = {"supported", "partially_supported", "manual_only", "unsupported"}
        if value not in allowed:
            raise ValueError(f"automation_support must be one of {sorted(allowed)}")
        return value


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


class BenchmarkSubset(BaseModel):
    expected_keys: list[str] = Field(default_factory=list)

    @field_validator("expected_keys")
    @classmethod
    def max_five_keys(cls, keys: list[str]) -> list[str]:
        if len(keys) > 5:
            raise ValueError("subset may contain at most 5 expected keys")
        return keys


def load_fixture(path: Path, *, fixtures_root: Path) -> BenchmarkFixture:
    resolved_root = fixtures_root.resolve()
    resolved_path = path.resolve()
    if resolved_root not in resolved_path.parents:
        raise ValueError("Benchmark manifests must be loaded from the repository fixture root.")
    with resolved_path.open(encoding="utf-8") as stream:
        payload = yaml.safe_load(stream)
    return BenchmarkFixture.model_validate(payload)


def load_subset(path: Path, *, fixtures_root: Path) -> BenchmarkSubset:
    resolved_root = fixtures_root.resolve()
    resolved_path = path.resolve()
    if resolved_root not in resolved_path.parents:
        raise ValueError("Benchmark subset manifests must be loaded from the repository fixture root.")
    with resolved_path.open(encoding="utf-8") as stream:
        payload = yaml.safe_load(stream)
    return BenchmarkSubset.model_validate(payload)


def filter_fixture_subset(fixture: BenchmarkFixture, subset: BenchmarkSubset) -> BenchmarkFixture:
    keys = set(subset.expected_keys)
    filtered = [item for item in fixture.expected_findings if item.expected_key in keys]
    missing = keys - {item.expected_key for item in filtered}
    if missing:
        raise ValueError(f"Subset references unknown expected keys: {sorted(missing)}")
    return fixture.model_copy(update={"expected_findings": filtered})
