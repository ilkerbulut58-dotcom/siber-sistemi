"""Blind benchmark ground truth — encrypted artifact only, no plaintext in repo."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import yaml

from app.benchmark.fixtures import BenchmarkFixture
from app.benchmark.manifests import repo_benchmarks_root
from app.services.benchmark_matching_service import match_findings

BLIND_SECRET_ENV = "BLIND_GROUND_TRUTH_SECRET"
MAGIC = b"SIBER-BLIND1"
PBKDF2_ITERATIONS = 200_000


@dataclass(frozen=True)
class BlindPublicMetadata:
    version: str
    name: str
    description: str
    artifact_file: str
    artifact_sha256: str
    ground_truth_version: str
    expected_finding_count: int
    fixture_reference: dict[str, str]
    encryption: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BlindBenchmarkResult:
    status: str
    skip_reason: str | None = None
    metadata: dict[str, Any] | None = None
    metrics: dict[str, Any] | None = None
    message: str | None = None

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"status": self.status}
        if self.skip_reason:
            payload["skip_reason"] = self.skip_reason
        if self.message:
            payload["message"] = self.message
        if self.metadata:
            payload["metadata"] = self.metadata
        if self.metrics:
            payload["metrics"] = self.metrics
        return payload


def blind_root() -> Path:
    return repo_benchmarks_root() / "blind"


def metadata_path() -> Path:
    return blind_root() / "metadata.yaml"


def load_public_metadata() -> BlindPublicMetadata:
    """Load public blind benchmark metadata — never exposes ground truth."""
    path = metadata_path()
    if not path.is_file():
        raise FileNotFoundError(f"Blind metadata missing: {path}")
    with path.open(encoding="utf-8") as stream:
        payload = yaml.safe_load(stream)
    return BlindPublicMetadata(
        version=str(payload["version"]),
        name=str(payload["name"]),
        description=str(payload.get("description", "")),
        artifact_file=str(payload["artifact_file"]),
        artifact_sha256=str(payload["artifact_sha256"]),
        ground_truth_version=str(payload["ground_truth_version"]),
        expected_finding_count=int(payload["expected_finding_count"]),
        fixture_reference=dict(payload.get("fixture_reference") or {}),
        encryption=dict(payload.get("encryption") or {}),
    )


def artifact_path(metadata: BlindPublicMetadata | None = None) -> Path:
    meta = metadata or load_public_metadata()
    path = (blind_root() / meta.artifact_file).resolve()
    root = blind_root().resolve()
    if root not in path.parents:
        raise ValueError("Blind artifact path traversal blocked")
    return path


def verify_artifact_hash(path: Path, expected_sha256: str) -> bool:
    if not path.is_file():
        return False
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return hmac.compare_digest(digest, expected_sha256.lower())


def _derive_key(secret: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha256",
        secret.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
        dklen=32,
    )


def _keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    stream = bytearray()
    counter = 0
    while len(stream) < length:
        block = hmac.new(key, nonce + counter.to_bytes(4, "big"), hashlib.sha256).digest()
        stream.extend(block)
        counter += 1
    return bytes(stream[:length])


def seal_ground_truth(
    secret: str,
    yaml_text: str,
    *,
    salt: bytes | None = None,
    nonce: bytes | None = None,
) -> bytes:
    """Seal plaintext ground truth for CI storage. Not for developer workflows."""
    salt = salt or os.urandom(16)
    nonce = nonce or os.urandom(16)
    key = _derive_key(secret, salt)
    plaintext = yaml_text.encode("utf-8")
    ciphertext = bytes(a ^ b for a, b in zip(plaintext, _keystream(key, nonce, len(plaintext)), strict=True))
    mac = hmac.new(key, salt + nonce + ciphertext, hashlib.sha256).digest()
    return MAGIC + salt + nonce + ciphertext + mac


def _open_ground_truth(secret: str, blob: bytes) -> str:
    if not blob.startswith(MAGIC):
        raise ValueError("Unknown blind artifact format")
    body = blob[len(MAGIC) :]
    if len(body) < 32 + 32:
        raise ValueError("Blind artifact truncated")
    salt = body[:16]
    nonce = body[16:32]
    mac = body[-32:]
    ciphertext = body[32:-32]
    key = _derive_key(secret, salt)
    expected_mac = hmac.new(key, salt + nonce + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(mac, expected_mac):
        raise ValueError("Blind artifact authentication failed")
    plaintext = bytes(
        a ^ b for a, b in zip(ciphertext, _keystream(key, nonce, len(ciphertext)), strict=True)
    )
    return plaintext.decode("utf-8")


def _resolve_secret(secret: str | None = None) -> str | None:
    value = (secret if secret is not None else os.environ.get(BLIND_SECRET_ENV, "")).strip()
    return value or None


def try_load_blind_fixture(secret: str | None = None) -> tuple[BenchmarkFixture | None, str | None]:
    """Decrypt blind ground truth when secret is available; otherwise return skip reason."""
    resolved = _resolve_secret(secret)
    if not resolved:
        return None, "secret_missing"

    metadata = load_public_metadata()
    path = artifact_path(metadata)
    if not verify_artifact_hash(path, metadata.artifact_sha256):
        return None, "artifact_hash_mismatch"

    try:
        yaml_text = _open_ground_truth(resolved, path.read_bytes())
    except ValueError:
        return None, "decrypt_failed"

    fixture = load_fixture_from_yaml(yaml_text)
    return fixture, None


def load_fixture_from_yaml(yaml_text: str) -> BenchmarkFixture:
    payload = yaml.safe_load(yaml_text)
    return BenchmarkFixture.model_validate(payload)


def public_metadata_dict(metadata: BlindPublicMetadata | None = None) -> dict[str, Any]:
    meta = metadata or load_public_metadata()
    return {
        "version": meta.version,
        "name": meta.name,
        "description": meta.description,
        "artifact_file": meta.artifact_file,
        "artifact_sha256": meta.artifact_sha256,
        "ground_truth_version": meta.ground_truth_version,
        "expected_finding_count": meta.expected_finding_count,
        "fixture_reference": meta.fixture_reference,
        "encryption": meta.encryption,
    }


def evaluate_blind_benchmark(
    findings: list[Any],
    *,
    secret: str | None = None,
) -> BlindBenchmarkResult:
    """Run blind benchmark evaluation. Skips safely when secret is unavailable."""
    try:
        metadata = load_public_metadata()
    except FileNotFoundError as exc:
        return BlindBenchmarkResult(
            status="skipped",
            skip_reason="metadata_missing",
            message=str(exc),
        )

    public_meta = public_metadata_dict(metadata)
    fixture, skip_reason = try_load_blind_fixture(secret)
    if fixture is None:
        messages = {
            "secret_missing": (
                "BLIND_GROUND_TRUTH_SECRET is not configured; blind validation skipped "
                "without producing synthetic results."
            ),
            "artifact_hash_mismatch": "Encrypted artifact hash does not match public metadata.",
            "decrypt_failed": "Blind ground truth could not be authenticated or decrypted.",
        }
        return BlindBenchmarkResult(
            status="skipped",
            skip_reason=skip_reason,
            metadata=public_meta,
            message=messages.get(skip_reason or "", "Blind benchmark skipped."),
        )

    expected = list(fixture.expected_findings)
    expected_records = [
        SimpleNamespace(
            id=uuid4(),
            expected_key=item.expected_key,
            accepted_alternative_keys=item.accepted_alternative_keys,
            category=item.category,
            affected_location=item.affected_location,
            detection_required=item.detection_required,
            automation_support=item.automation_support,
        )
        for item in expected
    ]
    matches, metrics = match_findings(expected_records, findings)
    return BlindBenchmarkResult(
        status="completed",
        metadata=public_meta,
        metrics={
            **metrics.as_dict(),
            "match_count": len(matches),
            "evaluated_at": datetime.now(UTC).isoformat(),
            "ground_truth_version": metadata.ground_truth_version,
        },
        message="Blind benchmark completed against decrypted holdout ground truth.",
    )


def write_blind_report(result: BlindBenchmarkResult, output_dir: Path | None = None) -> Path:
    root = output_dir or (repo_benchmarks_root() / "reports")
    root.mkdir(parents=True, exist_ok=True)
    path = root / "blind-benchmark.json"
    path.write_text(json.dumps(result.as_dict(), indent=2, default=str), encoding="utf-8")
    return path


def run_blind_benchmark_cli(*, secret: str | None = None, findings: list[Any] | None = None) -> int:
    """CLI entrypoint — always exits 0 on skip; exit 1 only on unexpected failure."""
    import asyncio

    resolved = _resolve_secret(secret)
    if findings is None and resolved:
        target_url = os.environ.get("BLIND_BENCHMARK_TARGET_URL", "http://127.0.0.1:18080/")
        try:
            findings = asyncio.run(collect_blind_findings(target_url))
        except Exception as exc:
            result = BlindBenchmarkResult(
                status="failed",
                skip_reason="scan_failed",
                message=f"Blind benchmark scan failed: {exc}",
            )
            report_path = write_blind_report(result)
            print(json.dumps(result.as_dict(), indent=2))
            print(f"Report written to {report_path}", file=os.sys.stderr)
            return 1

    result = evaluate_blind_benchmark(findings or [], secret=secret)
    report_path = write_blind_report(result)
    print(json.dumps(result.as_dict(), indent=2))
    print(f"Report written to {report_path}")
    if result.status == "skipped":
        print(result.message or "Blind benchmark skipped.", file=os.sys.stderr)
        return 0
    return 0


async def collect_blind_findings(target_url: str) -> list[Any]:
    """Run the public web-smoke safe scan profile and map results for blind holdout matching."""
    from app.analysis.correlation_engine import correlate_findings
    from app.scanners.orchestrator import run_scan_for_profile

    raw_findings = await run_scan_for_profile(target_url, "safe")
    correlated = correlate_findings(raw_findings)
    findings: list[Any] = []
    for item in correlated:
        findings.append(
            SimpleNamespace(
                id=uuid4(),
                correlation_key=item.correlation_key,
                source_rule_id=item.source_rule_ids[0] if item.source_rule_ids else item.correlation_key,
                fingerprint=f"{item.correlation_key}:{item.affected_url}",
                affected_url=item.affected_url,
                title=item.title,
                source_tool=item.source_tools[0] if item.source_tools else "unknown",
                severity=item.severity,
                source_tools=item.source_tools,
            )
        )
    return findings
