#!/usr/bin/env python3
"""Seed deterministic closed-pilot simulation tenants (local/test/staging only).

This script does NOT create real customer accounts or scan external targets.
It uses lab hostnames under pilot-sim.example.com resolved in isolated benchmark mode.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

ALLOWED_ENVIRONMENTS = frozenset({"local", "development", "dev", "test", "testing", "staging"})


def _guard_environment() -> None:
    env = os.environ.get("ENVIRONMENT", "development").strip().lower()
    if env == "production":
        print(
            "Refusing to seed closed pilot simulation: ENVIRONMENT=production is not allowed.",
            file=sys.stderr,
        )
        sys.exit(1)
    if env not in ALLOWED_ENVIRONMENTS:
        print(
            f"Refusing to seed closed pilot simulation: ENVIRONMENT={env!r} "
            f"is not in {sorted(ALLOWED_ENVIRONMENTS)}.",
            file=sys.stderr,
        )
        sys.exit(1)


async def _seed() -> None:
    from httpx import ASGITransport, AsyncClient

    from app.core.config import get_settings
    from app.core.database import Base, engine
    from app.main import create_app
    from app.models import MobileApplication, ScanProfile  # noqa: F401
    from app.models.benchmark import (  # noqa: F401
        BenchmarkFindingMatch,
        BenchmarkResult,
        BenchmarkRun,
        BenchmarkTarget,
        ExpectedFinding,
    )
    from tests.pilot.fixtures import PILOT_SIM_PASSWORD, PilotWorld, build_pilot_world

    os.environ.setdefault("BENCHMARK_LAB_ISOLATED", "true")
    get_settings.cache_clear()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        from app.core.database import async_session_factory

        async with async_session_factory() as db:
            world: PilotWorld = await build_pilot_world(client, db)

    await _print_summary(world)


async def _print_summary(world) -> None:
    from tests.pilot.fixtures import PILOT_SIM_PASSWORD

    print("Closed pilot simulation seed complete.")
    print(f"Platform admin: {world.platform_admin.email if world.platform_admin else 'n/a'}")
    print(f"Password (all sim users): {PILOT_SIM_PASSWORD}")
    print("")
    for key, tenant in sorted(world.tenants.items()):
        print(
            f"Tenant {key}: org={tenant.org_id} hostname={tenant.hostname} "
            f"verified={tenant.domain_verified} quota={tenant.pilot_scan_quota} "
            f"kill_switch={tenant.scans_disabled} pilot_end={tenant.pilot_ends_at}"
        )
        print(f"  owner={tenant.owner.email} analyst={tenant.analyst.email} viewer={tenant.viewer.email}")


def main() -> None:
    _guard_environment()
    asyncio.run(_seed())


if __name__ == "__main__":
    main()
