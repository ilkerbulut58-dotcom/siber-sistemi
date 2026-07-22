"""CLI entrypoint for closed-network benchmark suites."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

from app.benchmark.baseline import compute_delta, load_baseline
from app.benchmark.docker_control import (
    REALISTIC_HEALTH_SECONDS,
    REALISTIC_STARTUP_SECONDS,
    start_services,
    stop_services,
    wait_for_health,
)
from app.benchmark.fixtures import filter_fixture_subset, load_subset
from app.benchmark.gate import evaluate_gate
from app.benchmark.manifests import (
    ACTIVE_REALISTIC_SUITES,
    ALLOWED_SUITES,
    REALISTIC_PASSIVE_SUITES,
    load_ground_truth,
    load_suite_manifest,
    repo_benchmarks_root,
)
from app.benchmark.reports import build_report_payload, write_reports
from app.benchmark.scanner_versions import collect_lab_scanner_versions
from app.benchmark.security import assert_suite_runnable, is_realistic_suite
from app.core.config import get_settings
from app.core.database import async_session_factory
from app.models.benchmark import (
    BenchmarkFindingMatch,
    BenchmarkResult,
    BenchmarkRun,
    BenchmarkRunStatus,
    ExpectedFinding,
)
from app.models.finding import Finding
from app.models.scan import ScanJob, ScanStatus
from app.scanners.base import RawFinding
from app.schemas.scan import ScanCreate
from app.services.benchmark_fixture_sync_service import BenchmarkFixtureSyncService
from app.services.benchmark_workspace_service import BenchmarkWorkspaceService
from app.services.scan_service import ScanService, run_scan_job


def _git_commit() -> str | None:
    env_sha = os.environ.get("GITHUB_SHA", "").strip()
    if env_sha:
        return env_sha
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=repo_benchmarks_root().parent,
        )
        return result.stdout.strip()
    except Exception:
        return None


def _build_fixture_apk(script_relative: str) -> tuple[Path, str, str]:
    root = repo_benchmarks_root()
    script = (root / script_relative).resolve()
    if root.resolve() not in script.parents:
        raise ValueError("Artifact script path traversal blocked")
    subprocess.run([sys.executable, str(script)], check=True, cwd=script.parent)
    apk_path = script.parent / "fixture.apk"
    if not apk_path.is_file():
        raise FileNotFoundError(apk_path)
    digest = hashlib.sha256(apk_path.read_bytes()).hexdigest()
    meta_path = apk_path.with_suffix(".json")
    source_hash = ""
    if meta_path.is_file():
        import json

        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        source_hash = str(meta.get("fixture_source_hash") or "")
    if not source_hash:
        sys.path.insert(0, str(script.parent))
        try:
            from build_fixture_apk import fixture_source_hash

            source_hash = fixture_source_hash()
        finally:
            sys.path.pop(0)
    return apk_path, digest, source_hash


def _result_metrics(result: BenchmarkResult) -> dict:
    breakdown = result.breakdown or {}
    return {
        "true_positive_count": result.true_positive_count,
        "false_negative_count": result.false_negative_count,
        "confirmed_false_positive_count": breakdown.get("confirmed_false_positive_count", 0),
        "additional_valid_finding_count": breakdown.get("additional_valid_finding_count", 0),
        "duplicate_count": result.duplicate_count,
        "matcher_failure_count": breakdown.get("matcher_failure_count", 0),
        "scanner_error_count": result.scanner_error_count,
        "precision": result.precision,
        "recall": result.recall,
        "f1_score": result.f1_score,
        "duration_seconds": None,
    }


def _delta_for_result(result: BenchmarkResult, suite: str, *, duration_seconds: float | None) -> dict:
    metrics = _result_metrics(result)
    metrics["duration_seconds"] = duration_seconds
    return compute_delta(metrics, load_baseline(suite))


async def _run_web_or_api_target(
    *,
    suite: str,
    suite_manifest,
    target_manifest,
    fixture_set: str,
    write_baseline: bool,
    subset: str | None = None,
) -> int:
    settings = get_settings()
    active = suite in ACTIVE_REALISTIC_SUITES
    realistic = suite in REALISTIC_PASSIVE_SUITES or active
    started_services = list(target_manifest.docker_services)
    exit_code = 0
    suite_timeout = settings.benchmark_realistic_active_suite_timeout_seconds if active else (
        settings.benchmark_realistic_suite_timeout_seconds if suite in REALISTIC_PASSIVE_SUITES
        else settings.benchmark_max_duration_seconds
    )
    if active:
        os.environ["BENCHMARK_ACTIVE_SCAN_ALLOWED"] = "true"
        get_settings.cache_clear()
    try:
        if started_services:
            start_services(
                started_services,
                timeout_seconds=REALISTIC_STARTUP_SECONDS if realistic else 90,
                realistic=realistic,
            )
        if target_manifest.health_url:
            wait_for_health(
                target_manifest.health_url,
                timeout_seconds=REALISTIC_HEALTH_SECONDS if realistic else 60,
            )
        ground_truth = load_ground_truth(target_manifest.ground_truth)
        if subset:
            subset_path = target_manifest.subset_manifest or f"fixtures/{suite}/subset-{subset}.yaml"
            subset_manifest = load_subset(
                (repo_benchmarks_root() / subset_path).resolve(),
                fixtures_root=repo_benchmarks_root(),
            )
            ground_truth = filter_fixture_subset(ground_truth, subset_manifest)

        async def _execute() -> int:
            async with async_session_factory() as db:
                workspace = BenchmarkWorkspaceService(db)
                organization, project, actor = await workspace.ensure_workspace()
                hostname = target_manifest.hostname or "benchmark.local"
                domain = await workspace.ensure_domain(organization, project, hostname)
                benchmark_target = await BenchmarkFixtureSyncService(db).sync_target(target_manifest, ground_truth)
                await db.commit()

                scanner_versions = await collect_lab_scanner_versions()
                run = BenchmarkRun(
                    benchmark_target_id=benchmark_target.id,
                    app_version=settings.app_version,
                    git_commit=_git_commit(),
                    scan_profile=target_manifest.scan_profile or "safe",
                    fixture_set=fixture_set if not subset else f"{fixture_set}-{subset}",
                    status=BenchmarkRunStatus.RUNNING,
                    started_at=datetime.now(UTC),
                    scanner_versions=scanner_versions,
                )
                db.add(run)
                await db.flush()

                scan = await ScanService(db).create(
                    organization.id,
                    ScanCreate(
                        project_id=project.id,
                        domain_id=domain.id,
                        scan_profile=target_manifest.scan_profile or "safe",
                        target_url=target_manifest.target_url,
                        authorization_accepted=True,
                    ),
                    actor=actor,
                )
                run.scan_id = scan.id
                await db.commit()
                run_id = run.id
                scan_id = scan.id

            await run_scan_job(scan_id, async_session_factory)

            async with async_session_factory() as db:
                run = (await db.execute(select(BenchmarkRun).where(BenchmarkRun.id == run_id))).scalar_one()
                scan = (await db.execute(select(ScanJob).where(ScanJob.id == scan_id))).scalar_one()
                if scan.status != ScanStatus.COMPLETED:
                    run.status = BenchmarkRunStatus.FAILED
                    run.error_log = scan.error_log or f"Scan ended with status {scan.status}"
                    await db.commit()
                    return 1

                result = (
                    await db.execute(select(BenchmarkResult).where(BenchmarkResult.benchmark_run_id == run.id))
                ).scalar_one_or_none()
                if result is None:
                    return 1

                metrics = result.breakdown or {}
                missed = await _missed_findings(db, run.id)
                false_positives = await _false_positive_rules(db, run.id)
                raw_findings = await _raw_findings_from_scan(db, scan.id)
                from app.benchmark.customer_validation import build_customer_validation_artifact

                validation_artifact = build_customer_validation_artifact(raw_findings)
                customer_validation = {
                    "raw_finding_count": validation_artifact.raw_finding_count,
                    "customer_visible_count": validation_artifact.customer_visible_count,
                    "by_visibility": validation_artifact.by_visibility,
                    "suppression_count": len(validation_artifact.suppressions),
                    "suppressions": validation_artifact.suppressions[:20],
                }
                api_coverage = None
                if active and "api" in suite:
                    from app.scanners.api_surface_scanner import api_coverage_metrics

                    api_coverage = api_coverage_metrics(raw_findings)
                    missed_keys = [item.get("expected_key") for item in missed if item.get("expected_key")]
                    from app.benchmark.api_coverage_analysis import analyze_api_false_negatives

                    api_coverage["false_negative_analysis"] = analyze_api_false_negatives(
                        [key for key in missed_keys if key]
                    )
                delta = _delta_for_result(result, suite, duration_seconds=run.duration_seconds)
                result.previous_delta = delta
                missed_critical = sum(
                    1 for item in missed if item.get("severity") == "critical" and item.get("detection_required")
                )
                gate = evaluate_gate(
                    metrics=metrics,
                    baseline=load_baseline(suite),
                    delta=delta,
                    scanner_failed=False,
                    duration_seconds=run.duration_seconds,
                    missed_critical=missed_critical,
                )
                payload = build_report_payload(
                    suite=suite,
                    fixture_version=suite_manifest.version,
                    ground_truth_version=suite_manifest.version,
                    git_commit=run.git_commit,
                    scanner_versions=run.scanner_versions,
                    metrics={
                        "expected_count": result.expected_count,
                        "true_positive_count": result.true_positive_count,
                        "false_negative_count": result.false_negative_count,
                        "false_positive_count": result.false_positive_count,
                        "duplicate_count": result.duplicate_count,
                        "scanner_error_count": result.scanner_error_count,
                        "precision": result.precision,
                        "recall": result.recall,
                        "f1_score": result.f1_score,
                        **metrics,
                    },
                    missed_findings=missed,
                    false_positive_rules=false_positives,
                    baseline_delta=delta,
                    duration_seconds=run.duration_seconds,
                    scanner_errors=[run.error_log] if run.error_log else [],
                    subset=subset,
                    realistic=realistic,
                    active=active,
                    customer_validation=customer_validation,
                    api_coverage=api_coverage,
                )
                json_path, html_path = write_reports(run_id=str(run.id), payload=payload)
                if write_baseline:
                    from app.benchmark.baseline import suite_metrics_payload
                    from app.benchmark.baseline import write_baseline as persist_baseline

                    persist_baseline(
                        suite,
                        {
                            **suite_metrics_payload(
                                run_id=str(run.id),
                                metrics={
                                    "true_positive_count": result.true_positive_count,
                                    "false_negative_count": result.false_negative_count,
                                    "confirmed_false_positive_count": metrics.get("confirmed_false_positive_count", 0),
                                    "additional_valid_finding_count": metrics.get("additional_valid_finding_count", 0),
                                    "duplicate_count": result.duplicate_count,
                                    "matcher_failure_count": metrics.get("matcher_failure_count", 0),
                                    "scanner_error_count": result.scanner_error_count,
                                    "precision": result.precision,
                                    "recall": result.recall,
                                    "f1_score": result.f1_score,
                                },
                                duration_seconds=run.duration_seconds,
                            ),
                            "fixture_version": suite_manifest.version,
                            "ground_truth_version": suite_manifest.version,
                            "git_commit": run.git_commit,
                            "scanner_versions": run.scanner_versions,
                        },
                    )
                await db.commit()
                print(f"Benchmark report: {json_path}")
                print(f"Benchmark report: {html_path}")
                print(
                    f"TP={result.true_positive_count} FN={result.false_negative_count} "
                    f"confirmed_FP={metrics.get('confirmed_false_positive_count', result.false_positive_count)} "
                    f"requests={metrics.get('request_count', 0)} "
                    f"additional={metrics.get('additional_valid_finding_count', 0)} "
                    f"informational={metrics.get('informational_count', 0)} "
                    f"partial_R={metrics.get('partial_recall', 0):.3f} "
                    f"gaps={metrics.get('owasp_coverage_gap_count', 0)} "
                    f"dup={result.duplicate_count} matcher_fail={metrics.get('matcher_failure_count', 0)} "
                    f"zap_findings={metrics.get('zap_finding_count', 0)} "
                    f"nuclei_findings={metrics.get('nuclei_finding_count', 0)} "
                    f"P={result.precision:.3f} R={result.recall:.3f} F1={result.f1_score:.3f}"
                )
                scanner_metrics = metrics.get("scanner_metrics") or {}
                for tool, tool_metrics in scanner_metrics.items():
                    print(
                        f"scanner[{tool}] findings={tool_metrics.get('finding_count', 0)} "
                        f"seconds={tool_metrics.get('execution_seconds', 0)} "
                        f"timeouts={tool_metrics.get('timeout_count', 0)} "
                        f"errors={tool_metrics.get('error_count', 0)} "
                        f"version={tool_metrics.get('scanner_version')}"
                    )
                return gate.exit_code

        try:
            exit_code = await asyncio.wait_for(_execute(), timeout=suite_timeout)
        except TimeoutError:
            print(f"Suite {suite} timed out after {suite_timeout}s (scanner_error)", file=sys.stderr)
            exit_code = 1
    finally:
        if started_services:
            stop_services(started_services, realistic=realistic)
    return exit_code


async def _missed_findings(db, run_id: UUID) -> list[dict]:
    rows = await db.execute(
        select(ExpectedFinding, BenchmarkFindingMatch)
        .join(BenchmarkFindingMatch, BenchmarkFindingMatch.expected_finding_id == ExpectedFinding.id)
        .where(
            BenchmarkFindingMatch.benchmark_run_id == run_id,
            BenchmarkFindingMatch.classification == "false_negative",
        )
    )
    return [
        {
            "expected_key": expected.expected_key,
            "title": expected.title,
            "severity": expected.severity,
            "detection_required": expected.detection_required,
        }
        for expected, _match in rows.all()
    ]


async def _raw_findings_from_scan(db, scan_id: UUID) -> list[RawFinding]:
    rows = await db.execute(select(Finding).where(Finding.scan_job_id == scan_id))
    raw: list[RawFinding] = []
    for finding in rows.scalars().all():
        raw.append(
            RawFinding(
                source_tool=finding.source_tool,
                source_rule_id=finding.source_rule_id or finding.correlation_key or "unknown",
                title=finding.title,
                description=finding.description or finding.title,
                severity=finding.severity,
                affected_url=finding.affected_url or "",
                remediation=finding.remediation,
                confidence=finding.confidence or "medium",
                evidence=dict(finding.evidence or {}),
            )
        )
    return raw


async def _false_positive_rules(db, run_id: UUID) -> list[dict]:
    rows = await db.execute(
        select(Finding, BenchmarkFindingMatch)
        .join(BenchmarkFindingMatch, BenchmarkFindingMatch.finding_id == Finding.id)
        .where(
            BenchmarkFindingMatch.benchmark_run_id == run_id,
            BenchmarkFindingMatch.classification.in_(
                {
                    "false_positive",
                    "confirmed_false_positive",
                    "matcher_failure",
                    "ground_truth_missing",
                    "unsupported",
                }
            ),
        )
    )
    return [
        {
            "source_rule_id": finding.source_rule_id,
            "title": finding.title,
            "correlation_key": finding.correlation_key,
            "classification": match.classification,
        }
        for finding, match in rows.all()
    ]


async def _run_android_target(*, suite: str, suite_manifest, target_manifest, fixture_set: str, write_baseline: bool) -> int:
    settings = get_settings()
    apk_path, sha256, source_hash = _build_fixture_apk(target_manifest.artifact_script or "")
    benchmark_storage = Path(settings.benchmark_storage_path)
    benchmark_storage.mkdir(parents=True, exist_ok=True)
    os.environ["MOBILE_STORAGE_PATH"] = str(benchmark_storage)
    get_settings.cache_clear()

    ground_truth = load_ground_truth(target_manifest.ground_truth)
    async with async_session_factory() as db:
        workspace = BenchmarkWorkspaceService(db)
        organization, project, actor = await workspace.ensure_workspace()
        benchmark_target = await BenchmarkFixtureSyncService(db).sync_target(target_manifest, ground_truth)
        run = BenchmarkRun(
            benchmark_target_id=benchmark_target.id,
            app_version=settings.app_version,
            git_commit=_git_commit(),
            fixture_set=fixture_set,
            status=BenchmarkRunStatus.RUNNING,
            started_at=datetime.now(UTC),
            scanner_versions={
                "app": settings.app_version,
                "fixture_version": suite_manifest.version,
                "fixture_source_hash": source_hash,
                "fixture_apk_sha256": sha256,
            },
        )
        db.add(run)
        await db.flush()

        from app.mobile.services.mobile_service import MobileService

        app, _duplicate = await MobileService(db).upload_apk(
            organization.id,
            project.id,
            filename="fixture.apk",
            data=apk_path.read_bytes(),
            environment="benchmark",
            actor=actor,
        )
        run.mobile_application_id = app.id
        await db.commit()
        await MobileService(db).run_analysis(app.id)

        run = (await db.execute(select(BenchmarkRun).where(BenchmarkRun.id == run.id))).scalar_one()
        result = (
            await db.execute(select(BenchmarkResult).where(BenchmarkResult.benchmark_run_id == run.id))
        ).scalar_one_or_none()
        if result is None:
            return 1
        metrics = result.breakdown or {}
        delta = _delta_for_result(result, suite, duration_seconds=run.duration_seconds)
        result.previous_delta = delta
        payload = build_report_payload(
            suite=suite,
            fixture_version=suite_manifest.version,
            ground_truth_version=suite_manifest.version,
            git_commit=run.git_commit,
            scanner_versions=run.scanner_versions,
            metrics={
                "expected_count": result.expected_count,
                "true_positive_count": result.true_positive_count,
                "false_negative_count": result.false_negative_count,
                "false_positive_count": result.false_positive_count,
                "duplicate_count": result.duplicate_count,
                "scanner_error_count": result.scanner_error_count,
                "precision": result.precision,
                "recall": result.recall,
                "f1_score": result.f1_score,
                **metrics,
            },
            missed_findings=await _missed_findings(db, run.id),
            false_positive_rules=await _false_positive_rules(db, run.id),
            baseline_delta=delta,
            duration_seconds=run.duration_seconds,
            scanner_errors=[run.error_log] if run.error_log else [],
        )
        write_reports(run_id=str(run.id), payload=payload)
        if write_baseline:
            from app.benchmark.baseline import suite_metrics_payload, write_baseline

            write_baseline(
                suite,
                {
                    **suite_metrics_payload(
                        run_id=str(run.id),
                        metrics={
                            "true_positive_count": result.true_positive_count,
                            "false_negative_count": result.false_negative_count,
                            "confirmed_false_positive_count": metrics.get("confirmed_false_positive_count", 0),
                            "additional_valid_finding_count": metrics.get("additional_valid_finding_count", 0),
                            "duplicate_count": result.duplicate_count,
                            "matcher_failure_count": metrics.get("matcher_failure_count", 0),
                            "scanner_error_count": result.scanner_error_count,
                            "precision": result.precision,
                            "recall": result.recall,
                            "f1_score": result.f1_score,
                        },
                        duration_seconds=run.duration_seconds,
                    ),
                    "fixture_version": suite_manifest.version,
                    "ground_truth_version": suite_manifest.version,
                    "git_commit": run.git_commit,
                    "scanner_versions": run.scanner_versions,
                },
            )
        await db.commit()
        gate = evaluate_gate(
            metrics=metrics,
            baseline=load_baseline(suite),
            delta=delta,
            scanner_failed=run.status == BenchmarkRunStatus.FAILED,
            duration_seconds=run.duration_seconds,
            missed_critical=0,
        )
        return gate.exit_code


async def run_suite(suite: str, *, write_baseline: bool = False, subset: str | None = None) -> int:
    assert_suite_runnable(suite)
    os.environ.setdefault("SKIP_DOMAIN_VERIFICATION", "true")
    if is_realistic_suite(suite):
        os.environ.setdefault("BENCHMARK_LAB_ISOLATED", "true")
        if suite in ACTIVE_REALISTIC_SUITES:
            os.environ.setdefault("BENCHMARK_ACTIVE_REALISTIC_ENABLED", "true")
            os.environ["BENCHMARK_ACTIVE_SCAN_ALLOWED"] = "true"
        ca_default = repo_benchmarks_root() / "docker" / "realistic" / "certs" / "ca.crt"
        if ca_default.is_file():
            os.environ.setdefault("BENCHMARK_CA_CERT_PATH", str(ca_default))
    get_settings.cache_clear()
    manifest = load_suite_manifest(suite)
    if manifest.blocked:
        raise ValueError(f"Suite {suite!r} is blocked in this release")
    settings = get_settings()
    job_timeout = (
        settings.benchmark_realistic_active_job_timeout_seconds
        if suite in ACTIVE_REALISTIC_SUITES
        else settings.benchmark_realistic_job_timeout_seconds
        if suite in REALISTIC_PASSIVE_SUITES
        else None
    )

    async def _run_all() -> int:
        exit_code = 0
        for target in manifest.targets:
            if target.blocked:
                raise ValueError(f"Target {target.name!r} is blocked in this release")
            if target.target_type in {"web", "api"}:
                code = await _run_web_or_api_target(
                    suite=suite,
                    suite_manifest=manifest,
                    target_manifest=target,
                    fixture_set=manifest.fixture_set,
                    write_baseline=write_baseline,
                    subset=subset,
                )
            elif target.target_type == "android":
                code = await _run_android_target(
                    suite=suite,
                    suite_manifest=manifest,
                    target_manifest=target,
                    fixture_set=manifest.fixture_set,
                    write_baseline=write_baseline,
                )
            else:
                raise ValueError(f"Unsupported target type {target.target_type}")
            exit_code = max(exit_code, code)
        return exit_code

    if job_timeout:
        try:
            return await asyncio.wait_for(_run_all(), timeout=job_timeout)
        except TimeoutError:
            print(f"Benchmark job timed out after {job_timeout}s (scanner_error)", file=sys.stderr)
            return 1
    return await _run_all()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SIBER benchmark runner")
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run", help="Run an allowlisted benchmark suite")
    run_parser.add_argument("--suite", required=True, help="Allowlisted suite name")
    run_parser.add_argument("--subset", default=None, help="Optional subset manifest suffix (e.g. main)")
    run_parser.add_argument("--write-baseline", action="store_true")
    sub.add_parser("blind", help="Run blind benchmark evaluation (requires BLIND_GROUND_TRUTH_SECRET)")
    sub.add_parser("risk-eval", help="Run Risk Engine golden-set evaluation")
    sub.add_parser("ai-remediation-eval", help="Run AI remediation golden-set evaluation")
    sub.add_parser("metrics-audit", help="Print metric definitions and Risk Engine confusion table")
    sub.add_parser("release-gates", help="Evaluate MVP release gates (report-only)")
    args = parser.parse_args(argv)
    if args.command == "run":
        if args.suite not in ALLOWED_SUITES:
            print("Suite is not allowlisted", file=sys.stderr)
            return 2
        try:
            return asyncio.run(run_suite(args.suite, write_baseline=args.write_baseline, subset=args.subset))
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
    if args.command == "blind":
        from app.benchmark.blind import run_blind_benchmark_cli

        return run_blind_benchmark_cli()
    if args.command == "risk-eval":
        from app.benchmark.risk_eval import run_risk_eval_cli

        return run_risk_eval_cli()
    if args.command == "ai-remediation-eval":
        from app.benchmark.ai_remediation_eval import run_ai_remediation_eval_cli

        return run_ai_remediation_eval_cli()
    if args.command == "metrics-audit":
        import json

        from app.benchmark.metrics_audit import risk_engine_confusion_table
        from app.benchmark.metrics_definitions import (
            METRIC_DEFINITIONS,
            precision_recall_inclusion_table,
        )

        payload = {
            "metric_definitions": METRIC_DEFINITIONS,
            "precision_recall_inclusion": precision_recall_inclusion_table(),
            "risk_engine_confusion": risk_engine_confusion_table(),
        }
        print(json.dumps(payload, indent=2))
        return 0
    if args.command == "release-gates":
        import json

        from app.benchmark.baseline import (
            load_realistic_active_baseline,
            load_realistic_baseline_v11,
        )
        from app.benchmark.release_gates import evaluate_release_gates, write_release_gate_report

        passive = load_realistic_baseline_v11()
        active = load_realistic_active_baseline()
        report = evaluate_release_gates(
            passive_web=(passive or {}).get("suites", {}).get("web-realistic-passive"),
            passive_api=(passive or {}).get("suites", {}).get("api-realistic-passive"),
            active_web=(active or {}).get("suites", {}).get("web-realistic-active"),
            active_api=(active or {}).get("suites", {}).get("api-realistic-active"),
            blind_validation_passed=None,
        )
        path = write_release_gate_report(report)
        print(json.dumps(report.as_dict(), indent=2))
        print(f"Report written to {path}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
