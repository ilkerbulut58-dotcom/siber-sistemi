"""AI provider factory."""

from __future__ import annotations

from functools import lru_cache

from app.ai.providers.base import AIProvider
from app.ai.providers.openai_provider import OpenAIProvider
from app.core.config import get_settings


@lru_cache
def get_ai_provider() -> AIProvider | None:
    settings = get_settings()
    if not settings.ai_enabled:
        return None

    if settings.ai_provider == "openai":
        provider = OpenAIProvider(
            api_key=settings.openai_api_key,
            model=settings.ai_model,
            base_url=settings.ai_base_url,
            timeout_seconds=settings.ai_timeout_seconds,
        )
        return provider if provider.is_configured else None

    return None
