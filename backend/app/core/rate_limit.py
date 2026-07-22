"""Redis-backed limits for sensitive public API operations."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass

from fastapi import Request

from app.core.config import get_settings
from app.core.redis import get_redis

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int = 0


def _rule_for_request(request: Request) -> tuple[str, int, int] | None:
    """Return (bucket, maximum requests, window seconds) for protected routes."""
    path = request.url.path
    settings = get_settings()

    if path in {
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/refresh",
        "/api/v1/auth/forgot-password",
        "/api/v1/auth/reset-password",
    }:
        return ("auth", settings.auth_rate_limit_per_minute, 60)
    if request.method == "POST" and path.endswith("/mobile/applications"):
        return ("upload", settings.upload_rate_limit_per_hour, 3600)
    if request.method == "POST" and path.endswith("/retest"):
        return ("retest", settings.retest_rate_limit_per_hour, 3600)
    return None


async def check_rate_limit(request: Request) -> RateLimitDecision | None:
    """Atomically consume a rate-limit token for sensitive routes.

    Limits are disabled in local development by default. In production, Redis
    errors reject sensitive requests rather than silently removing protection.
    """
    settings = get_settings()
    if not settings.rate_limit_enabled:
        return None

    rule = _rule_for_request(request)
    if rule is None:
        return None

    bucket, maximum, window_seconds = rule
    peer_ip = request.client.host if request.client else "unknown"
    if peer_ip in settings.trusted_proxy_ips:
        peer_ip = request.headers.get("X-Forwarded-For", peer_ip).split(",", 1)[0].strip()
    client_hash = hashlib.sha256(peer_ip.encode("utf-8")).hexdigest()[:24]
    key = f"siber:rate:{bucket}:{client_hash}"

    try:
        redis = await get_redis()
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window_seconds)
        ttl = await redis.ttl(key)
    except Exception:
        logger.exception("Rate-limit backend unavailable for %s", bucket)
        if settings.environment == "production":
            return RateLimitDecision(allowed=False, retry_after_seconds=60)
        return None

    if count > maximum:
        return RateLimitDecision(allowed=False, retry_after_seconds=max(ttl, 1))
    return RateLimitDecision(allowed=True, retry_after_seconds=max(ttl, 0))
