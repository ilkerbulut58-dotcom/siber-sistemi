"""Parallel orchestrator and timeout behavior."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.scanners.base import RawFinding
from app.scanners.orchestrator import run_scan_for_profile


@pytest.mark.asyncio
async def test_safe_profile_runs_scanners_in_parallel() -> None:
    started: list[str] = []
    release = asyncio.Event()

    async def slow_scanner(name: str) -> list[RawFinding]:
        started.append(name)
        await release.wait()
        return [
            RawFinding(
                source_tool=name,
                source_rule_id=f"{name}-1",
                title=f"{name} finding",
                description="test",
                severity="info",
                affected_url="https://example.com",
            )
        ]

    async def passive_mock(**_kwargs) -> list[RawFinding]:
        return await slow_scanner("passive_http")

    async def zap_mock(**_kwargs) -> list[RawFinding]:
        return await slow_scanner("zap")

    async def nuclei_mock(**_kwargs) -> list[RawFinding]:
        return await slow_scanner("nuclei")

    with (
        patch(
            "app.scanners.orchestrator.run_passive_http_scan",
            side_effect=passive_mock,
        ),
        patch(
            "app.scanners.orchestrator.run_zap_passive_scan",
            side_effect=zap_mock,
        ),
        patch(
            "app.scanners.orchestrator.run_nuclei_scan",
            side_effect=nuclei_mock,
        ),
    ):
        task = asyncio.create_task(run_scan_for_profile("https://example.com", "safe"))
        await asyncio.sleep(0.05)
        assert len(started) == 3
        release.set()
        findings = await task

    assert len(findings) == 3


@pytest.mark.asyncio
async def test_safe_profile_returns_partial_results_on_timeout() -> None:
    fast = [
        RawFinding(
            source_tool="passive_http",
            source_rule_id="fast",
            title="Fast",
            description="done",
            severity="info",
            affected_url="https://example.com",
        )
    ]

    async def never_finishes(**_kwargs) -> list[RawFinding]:
        await asyncio.sleep(3600)
        return []

    with (
        patch(
            "app.scanners.orchestrator.run_passive_http_scan",
            new_callable=AsyncMock,
            return_value=fast,
        ),
        patch(
            "app.scanners.orchestrator.run_zap_passive_scan",
            side_effect=never_finishes,
        ),
        patch(
            "app.scanners.orchestrator.run_nuclei_scan",
            side_effect=never_finishes,
        ),
        patch("app.scanners.orchestrator._profile_timeout_seconds", return_value=0.2),
    ):
        findings = await run_scan_for_profile("https://example.com", "safe")

    assert len(findings) == 1
    assert findings[0].source_rule_id == "fast"
