"""Sanitize sensitive finding evidence before persistence and API responses."""

from __future__ import annotations

import copy
import re
from typing import Any

from app.ai.data_masker import SENSITIVE_HEADER_NAMES, _redact_text

SESSION_TOKEN_PATTERN = re.compile(
    r"(?i)(session[_-]?id|sess|phpsessid|connect\.sid)\s*[:=]\s*\S+"
)
BEARER_PATTERN = re.compile(r"(?i)bearer\s+[A-Za-z0-9\-._~+/]+=*")

SENSITIVE_EVIDENCE_KEYS = frozenset(
    {
        "cookie_sample",
        "authorization",
        "set-cookie",
        "cookie",
        "session",
        "token",
        "api_key",
        "secret",
        "password",
        "private_key",
        "credentials",
    }
)


def sanitize_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = _redact_text(value)
    text = SESSION_TOKEN_PATTERN.sub(r"\1=[REDACTED]", text)
    text = BEARER_PATTERN.sub("Bearer [REDACTED]", text)
    return text


def sanitize_evidence_dict(evidence: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return a deep-copied, redacted evidence dict safe for storage and API."""
    if not evidence:
        return None

    result: dict[str, Any] = {}
    for key, value in evidence.items():
        key_lower = str(key).lower()
        if key_lower in SENSITIVE_EVIDENCE_KEYS or key_lower in SENSITIVE_HEADER_NAMES:
            result[key] = "[REDACTED]"
            continue
        if key_lower == "headers" and isinstance(value, dict):
            result[key] = {
                str(hk): (
                    "[REDACTED]"
                    if str(hk).lower() in SENSITIVE_HEADER_NAMES
                    else sanitize_text(str(hv))
                )
                for hk, hv in value.items()
            }
            continue
        if isinstance(value, str):
            result[key] = sanitize_text(value)
        elif isinstance(value, dict):
            nested = sanitize_evidence_dict(value)
            if nested:
                result[key] = nested
        elif isinstance(value, list):
            result[key] = [
                sanitize_text(str(v)) if isinstance(v, str) else v for v in value
            ]
        else:
            result[key] = value
    return result


def sanitize_history_details(details: dict[str, Any] | None) -> dict[str, Any] | None:
    if not details:
        return None
    cleaned = copy.deepcopy(details)
    for key in list(cleaned.keys()):
        if isinstance(cleaned[key], str):
            cleaned[key] = sanitize_text(cleaned[key])
        elif isinstance(cleaned[key], dict):
            cleaned[key] = sanitize_evidence_dict(cleaned[key]) or {}
    return cleaned
