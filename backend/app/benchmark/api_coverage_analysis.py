"""Root-cause analysis for API benchmark false negatives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

API_ACTIVE_REQUIRED_KEYS = frozenset(
    {
        "missing-header-content-security-policy",
        "missing-header-strict-transport-security",
        "server-disclosure",
        "permissive-cors",
    }
)


@dataclass(frozen=True)
class ApiFnRootCause:
    expected_key: str
    classification: str
    root_cause: str
    remediation: str


FN_ROOT_CAUSES: dict[str, ApiFnRootCause] = {
    "missing-header-content-security-policy": ApiFnRootCause(
        "missing-header-content-security-policy",
        "scanner_coverage_gap",
        "Active profile omitted passive_http header inspection; ZAP active may not emit CSP on root URL alone.",
        "Include passive_http in benchmark-active-api profile.",
    ),
    "missing-header-strict-transport-security": ApiFnRootCause(
        "missing-header-strict-transport-security",
        "scanner_coverage_gap",
        "Same as CSP — header checks require deterministic passive response inspection.",
        "Include passive_http in benchmark-active-api profile.",
    ),
    "server-disclosure": ApiFnRootCause(
        "server-disclosure",
        "matcher_failure",
        "Finding may be present as x-powered-by or generic ZAP alert with different correlation key.",
        "Extend matcher accepted_alternative_keys and header disclosure validators.",
    ),
    "permissive-cors": ApiFnRootCause(
        "permissive-cors",
        "request_generation_gap",
        "CORS requires OPTIONS preflight with Origin header; active ZAP/Nuclei alone may not probe CORS.",
        "Add api_surface_scanner CORS probe to active API profile.",
    ),
    "exposed-api-docs": ApiFnRootCause(
        "exposed-api-docs",
        "fixture_expectation_mismatch",
        "Pinned crAPI realistic proxy does not serve OpenAPI/Swagger at runtime; spec exists in upstream repo only.",
        "See openapi-runtime-evidence.md; scanner probes remain for targets that do expose specs.",
    ),
}


def analyze_api_false_negatives(missed_keys: list[str]) -> list[dict[str, Any]]:
    analysis: list[dict[str, Any]] = []
    for key in missed_keys:
        cause = FN_ROOT_CAUSES.get(
            key,
            ApiFnRootCause(
                key,
                "unsupported",
                "No mapped root-cause entry.",
                "Extend api_coverage analysis mapping.",
            ),
        )
        analysis.append(
            {
                "expected_key": cause.expected_key,
                "classification": cause.classification,
                "root_cause": cause.root_cause,
                "remediation": cause.remediation,
            }
        )
    return analysis


def expected_api_fn_report() -> dict[str, Any]:
    return {
        "required_keys": sorted(API_ACTIVE_REQUIRED_KEYS),
        "analysis": analyze_api_false_negatives(sorted(API_ACTIVE_REQUIRED_KEYS)),
        "coverage_dimensions": [
            "openapi_schema_discovery",
            "method_coverage_options",
            "authenticated_route_coverage",
            "request_generation",
            "matcher_failure",
            "scanner_coverage_gap",
        ],
    }
