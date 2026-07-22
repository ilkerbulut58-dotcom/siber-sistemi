"""OpenAI-compatible chat completions provider."""

from __future__ import annotations

import json
import logging

import httpx

from app.ai.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from app.ai.providers.base import AIProvider
from app.ai.schemas import AIAnalysisResult, FindingAnalysisPayload

logger = logging.getLogger(__name__)


class OpenAIProvider(AIProvider):
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str,
        timeout_seconds: float,
    ) -> None:
        self._api_key = api_key.strip()
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    async def analyze_finding(self, payload: FindingAnalysisPayload) -> AIAnalysisResult:
        user_prompt = USER_PROMPT_TEMPLATE.format(
            payload=json.dumps(payload.model_dump(exclude_none=True), ensure_ascii=False, indent=2)
        )

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model,
                    "temperature": 0.2,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                },
            )
            response.raise_for_status()
            body = response.json()

        content = body["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        return AIAnalysisResult.model_validate(parsed)
