"""Celery application configuration (Phase 4+)."""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "siber",
    broker=str(settings.redis_url),
    backend=str(settings.redis_url),
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,
    task_soft_time_limit=540,
    worker_prefetch_multiplier=1,
    imports=(
        "app.tasks.scan_tasks",
        "app.tasks.monitoring_tasks",
        "app.tasks.ai_tasks",
        "app.tasks.asm_tasks",
        "app.mobile.tasks.mobile_tasks",
    ),
    task_routes={
        "siber.run_scan_job": {"queue": "scans"},
        "siber.check_scheduled_scans": {"queue": "monitoring"},
        "siber.recover_stale_scans": {"queue": "monitoring"},
        "siber.enrich_scan_findings": {"queue": "monitoring"},
        "siber.run_asm_discovery": {"queue": "scans"},
        "siber.run_mobile_analysis": {"queue": settings.mobile_analysis_queue},
    },
    beat_schedule={
        "check-scheduled-scans": {
            "task": "siber.check_scheduled_scans",
            "schedule": 300.0,
        },
        "recover-stale-scans": {
            "task": "siber.recover_stale_scans",
            "schedule": 120.0,
        },
    },
)
