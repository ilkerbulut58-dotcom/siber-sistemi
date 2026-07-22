from types import SimpleNamespace
from pathlib import Path
from uuid import uuid4

import pytest

from app.benchmark.fixtures import load_fixture
from app.services.benchmark_matching_service import match_findings


def expected(key: str, *, required: bool = True, alternatives: list[str] | None = None):
    return SimpleNamespace(
        id=uuid4(), expected_key=key, accepted_alternative_keys=alternatives or [],
        category=None, affected_location=None, detection_required=required,
    )


def finding(*, key: str, rule: str | None = None):
    return SimpleNamespace(
        id=uuid4(), correlation_key=key, source_rule_id=rule,
        fingerprint="abc", affected_url=None, title="finding",
    )


def test_matches_alternative_key_and_calculates_metrics():
    records, metrics = match_findings([expected("missing-csp", alternatives=["zap-missing-csp"])], [finding(key="zap-missing-csp")])
    assert records[0].classification == "true_positive"
    assert metrics.precision == metrics.recall == metrics.f1_score == 1.0


def test_counts_false_negative_false_positive_and_duplicate():
    item = expected("missing-csp")
    records, metrics = match_findings([item, expected("missing-hsts")], [finding(key="missing-csp"), finding(key="missing-csp"), finding(key="other")])
    assert metrics.true_positive_count == 1
    assert metrics.false_negative_count == 1
    assert metrics.duplicate_count == 1
    assert metrics.false_positive_count == 1


def test_fixture_loader_rejects_external_manifest(tmp_path: Path):
    external = tmp_path / "target.yaml"
    external.write_text("target: x\ntarget_type: web\ntarget_reference: http://x\nexpected_findings: []")
    with pytest.raises(ValueError):
        load_fixture(external, fixtures_root=Path(__file__).parent)
