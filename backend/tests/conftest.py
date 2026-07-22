"""Pytest configuration and shared fixtures."""

import os

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "sqlite+aiosqlite:///:memory:",
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("ENVIRONMENT", "development")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import Base, async_session_factory, engine
from app.main import create_app
from app.models import MobileApplication, ScanProfile  # noqa: F401 — register ORM metadata
from app.models.benchmark import (  # noqa: F401
    BenchmarkFindingMatch,
    BenchmarkResult,
    BenchmarkRun,
    BenchmarkTarget,
    ExpectedFinding,
)

get_settings.cache_clear()


@pytest.fixture(autouse=True)
def reset_settings_cache() -> None:
    """Prevent cross-test pollution when individual tests override env-backed settings."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


TABLES = [
    "benchmark_finding_matches",
    "benchmark_results",
    "benchmark_runs",
    "expected_findings",
    "benchmark_targets",
    "mobile_applications",
    "monitoring_events",
    "scan_schedules",
    "finding_history",
    "findings",
    "assets",
    "asm_discovery_jobs",
    "authorization_acceptances",
    "scan_jobs",
    "target_site_profiles",
    "scan_profiles",
    "domain_verifications",
    "domains",
    "projects",
    "audit_logs",
    "organization_members",
    "organizations",
    "refresh_tokens",
    "password_reset_tokens",
    "email_verification_tokens",
    "users",
]

SCAN_PROFILES = [
    ("safe", "Safe Scan", "Passive checks for production targets."),
    ("deep", "Deep Scan", "Active testing for staging environments."),
    ("code", "Code Scan", "Repository and dependency analysis."),
]


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _seed_scan_profiles() -> None:
    async with async_session_factory() as session:
        for name, display_name, description in SCAN_PROFILES:
            session.add(
                ScanProfile(
                    name=name,
                    display_name=display_name,
                    description=description,
                    is_active=True,
                    tools={"tools": [name]},
                )
            )
        await session.commit()


@pytest_asyncio.fixture(autouse=True)
async def clean_database() -> None:
    async with engine.begin() as conn:
        dialect = conn.dialect.name
        if dialect == "sqlite":
            await conn.execute(text("PRAGMA foreign_keys = OFF"))
            for table in TABLES:
                await conn.execute(text(f"DELETE FROM {table}"))
            await conn.execute(text("PRAGMA foreign_keys = ON"))
        else:
            for table in TABLES:
                await conn.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
    await _seed_scan_profiles()
    yield


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session():
    async with async_session_factory() as session:
        yield session
        await session.rollback()
