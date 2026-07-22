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
from app.benchmark.docker_control import start_services, stop_services, wait_for_health
from app.benchmark.gate import evaluate_gate
from app.benchmark.manifests import load_ground_truth, load_suite_manifest, repo_benchmarks_root
from app.benchmark.reports import build_report_payload, write_reports
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


def _build_fixture_apk(script_relative: str) -> tuple[Path, str]:
    root = repo_benchmarks_root()
    script = (root / script_relative).resolve()
    if root.resolve() not in script.parents:
        raise ValueError("Artifact script path traversal blocked")
    subprocess.run([sys.executable, str(script)], check=True, cwd=script.parent)
    apk_path = script.parent / "fixture.apk"
    if not apk_path.is_file():
        raise FileNotFoundError(apk_path)
    digest = hashlib.sha256(apk_path.read_bytes()).hexdigest()
    return apk_path, digest


async def _run_web_or_api_target(
    *,
    suite: str,
    suite_manifest,
    target_manifest,
    fixture_set: str,
    write_baseline: bool,
) -> int:
    settings = get_settings()
    started_services = list(target_manifest.docker_services)
    exit_code = 0
    try:
        if started_services:
            start_services(started_services)
        if target_manifest.health_url:
            wait_for_health(target_manifest.health_url)
        ground_truth = load_ground_truth(target_manifest.ground_truth)
        async with async_session_factory() as db:
            workspace = BenchmarkWorkspaceService(db)
            organization, project, actor = await workspace.ensure_workspace()
            hostname = target_manifest.hostname or "benchmark.local"
            domain = await workspace.ensure_domain(organization, project, hostname)
            benchmark_target = await BenchmarkFixtureSyncService(db).sync_target(target_manifest, ground_truth)
            await db.commit()

            run = BenchmarkRun(
                benchmark_target_id=benchmark_target.id,
                app_version=settings.app_version,
                git_commit=_git_commit(),
                scan_profile=target_manifest.scan_profile or "safe",
                fixture_set=fixture_set,
                status=BenchmarkRunStatus.RUNNING,
                started_at=datetime.now(UTC),
                scanner_versions={"app": settings.app_version},
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

        await run_scan_job(scan.id, async_session_factory)

        async with async_session_factory() as db:
            run = (await db.execute(select(BenchmarkRun).where(BenchmarkRun.id == run.id))).scalar_one()
            scan = (await db.execute(select(ScanJob).where(ScanJob.id == run.scan_id))).scalar_one()
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
            baseline = load_baseline(suite)
            delta = compute_delta(
                {
                    "precision": result.precision,
                    "recall": result.recall,
                    "f1_score": result.f1_score,
                    "false_negative_count": result.false_negative_count,
                    "duration_seconds": run.duration_seconds,
                },
                baseline,
            )
            result.previous_delta = delta
            missed_critical = sum(
                1 for item in missed if item.get("severity") == "critical" and item.get("detection_required")
            )
            gate = evaluate_gate(
                metrics=metrics,
                baseline=baseline,
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
            )
            json_path, html_path = write_reports(run_id=str(run.id), payload=payload)
            if write_baseline:
                write_baseline(
                    suite,
                    {
                        "run_id": str(run.id),
                        "precision": result.precision,
                        "recall": result.recall,
                        "f1_score": result.f1_score,
                        "false_negative_count": result.false_negative_count,
                        "duration_seconds": run.duration_seconds,
                    },
                )
            await db.commit()
            print(f"Benchmark report: {json_path}")
            print(f"Benchmark report: {html_path}")
            print(
                f"TP={result.true_positive_count} FN={result.false_negative_count} "
                f"confirmed_FP={metrics.get('confirmed_false_positive_count', result.false_positive_count)} "
                f"additional={metrics.get('additional_valid_finding_count', 0)} "
                f"dup={result.duplicate_count} matcher_fail={metrics.get('matcher_failure_count', 0)} "
                f"P={result.precision:.3f} R={result.recall:.3f} F1={result.f1_score:.3f}"
            )
            exit_code = gate.exit_code
    finally:
        if started_services:
            stop_services(started_services)
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
    apk_path, sha256 = _build_fixture_apk(target_manifest.artifact_script or "")
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
            scanner_versions={"app": settings.app_version, "fixture_apk_sha256": sha256},
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
        payload = build_report_payload(
            suite=suite,
            fixture_version=suite_manifest.version,
            ground_truth_version=suite_manifest.version,
            git_commit=run.git_commit,
            scanner_versions=run.scanner_versions,
            metrics=result.breakdown or {},
            missed_findings=await _missed_findings(db, run.id),
            false_positive_rules=await _false_positive_rules(db, run.id),
            baseline_delta=compute_delta({"recall": result.recall, "precision": result.precision, "f1_score": result.f1_score, "false_negative_count": result.false_negative_count, "duration_seconds": run.duration_seconds}, load_baseline(suite)),
            duration_seconds=run.duration_seconds,
            scanner_errors=[run.error_log] if run.error_log else [],
        )
        write_reports(run_id=str(run.id), payload=payload)
        if write_baseline:
            write_baseline(suite, {"run_id": str(run.id), "recall": result.recall, "precision": result.precision, "f1_score": result.f1_score, "false_negative_count": result.false_negative_count, "duration_seconds": run.duration_seconds})
        await db.commit()
        gate = evaluate_gate(metrics=result.breakdown or {}, baseline=load_baseline(suite), delta={}, scanner_failed=run.status == BenchmarkRunStatus.FAILED, duration_seconds=run.duration_seconds, missed_critical=0)
        return gate.exit_code


async def run_suite(suite: str, *, write_baseline: bool = False) -> int:
    os.environ.setdefault("SKIP_DOMAIN_VERIFICATION", "true")
    get_settings.cache_clear()
    manifest = load_suite_manifest(suite)
    exit_code = 0
    for target in manifest.targets:
        if target.target_type in {"web", "api"}:
            code = await _run_web_or_api_target(
                suite=suite,
                suite_manifest=manifest,
                target_manifest=target,
                fixture_set=manifest.fixture_set,
                write_baseline=write_baseline,
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SIBER benchmark runner")
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run", help="Run an allowlisted benchmark suite")
    run_parser.add_argument("--suite", required=True, help="Allowlisted suite name")
    run_parser.add_argument("--write-baseline", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "run":
        if args.suite not in {"web-smoke", "api-smoke", "android-smoke"}:
            print("Suite is not allowlisted", file=sys.stderr)
            return 2
        return asyncio.run(run_suite(args.suite, write_baseline=args.write_baseline))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
