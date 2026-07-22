"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1 import (
    asm,
    auth,
    domains,
    findings,
    health,
    mobile,
    monitoring,
    organizations,
    platform,
    projects,
    quick_scan,
    scans,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(quick_scan.router)
api_router.include_router(users.router)
api_router.include_router(organizations.router)
api_router.include_router(projects.router)
api_router.include_router(domains.router)
api_router.include_router(scans.profiles_router)
api_router.include_router(scans.org_scans_router)
api_router.include_router(findings.router)
api_router.include_router(monitoring.router)
api_router.include_router(asm.router)
api_router.include_router(mobile.router)
api_router.include_router(platform.router)
