"""Mask sensitive data before sending findings to LLM providers."""

from __future__ import annotations

import re
from typing import Any

JWT_PATTERN = re.compile(r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
API_KEY_PATTERN = re.compile(
    r"(?i)(api[_-]?key|secret|password|token|authorization)\s*[:=]\s*\S+"
)
SENSITIVE_HEADER_NAMES = frozenset(
    {"authorization", "cookie", "set-cookie", "x-api-key", "x-auth-token"}
)
MAX_TEXT_LENGTH = 4000
MAX_EVIDENCE_LENGTH = 1500


def _redact_text(value: str) -> str:
    text = JWT_PATTERN.sub("[REDACTED_JWT]", value)
    text = API_KEY_PATTERN.sub(r"\1=[REDACTED]", text)
    if len(text) > MAX_TEXT_LENGTH:
        return text[:MAX_TEXT_LENGTH] + "…[truncated]"
    return text


def mask_text(value: str | None) -> str | None:
    if value is None:
        return None
    return _redact_text(value)


def mask_evidence(evidence: dict[str, Any] | None) -> str | None:
    if not evidence:
        return None

    parts: list[str] = []
    headers = evidence.get("headers")
    if isinstance(headers, dict):
        for name, header_value in headers.items():
            if str(name).lower() in SENSITIVE_HEADER_NAMES:
                parts.append(f"{name}: [REDACTED]")
            else:
                parts.append(f"{name}: {_redact_text(str(header_value))}")

    for key in ("detail", "message", "note", "path"):
        if key in evidence and evidence[key]:
            parts.append(f"{key}: {_redact_text(str(evidence[key]))}")

    if not parts:
        raw = _redact_text(str(evidence))
        return raw[:MAX_EVIDENCE_LENGTH]

    summary = " | ".join(parts)
    return summary[:MAX_EVIDENCE_LENGTH]
