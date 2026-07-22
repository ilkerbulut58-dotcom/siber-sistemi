"""MVP release gate reporting tests."""

from __future__ import annotations

from app.benchmark.release_gates import evaluate_release_gates


def test_not_ready_when_thresholds_missed():
    report = evaluate_release_gates(
        passive_web={"precision": 0.5, "recall": 0.6},
        active_web={"precision": 0.1, "recall": 0.6},
        customer_variance_pct=12.0,
        external_request_count=0,
        blind_validation_passed=False,
    )
    assert report.status == "not_ready"
    assert report.blockers
    assert any(gate.gate_id == "passive_web_precision" for gate in report.gates)


def test_external_request_gate_fails_on_nonzero():
    report = evaluate_release_gates(external_request_count=2)
    gate = next(item for item in report.gates if item.gate_id == "external_request_count")
    assert gate.passed is False
