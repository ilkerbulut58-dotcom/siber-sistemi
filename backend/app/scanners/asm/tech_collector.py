"""Passive technology detection from HTTP response."""

from __future__ import annotations

import re

CMS_PATTERNS: list[tuple[str, str, re.Pattern[str]]] = [
    ("cms", "WordPress", re.compile(r"wp-content|wp-includes|wordpress", re.I)),
    ("cms", "Drupal", re.compile(r"drupal|sites/default", re.I)),
    ("cms", "Joomla", re.compile(r"joomla|/components/com_", re.I)),
    ("framework", "React", re.compile(r"react-root|__NEXT_DATA__|/_next/", re.I)),
    ("framework", "Vue.js", re.compile(r"vue\.js|data-v-", re.I)),
    ("framework", "Angular", re.compile(r"ng-version|angular", re.I)),
    ("framework", "Next.js", re.compile(r"__NEXT_DATA__|/_next/", re.I)),
    ("framework", "Laravel", re.compile(r"laravel_session", re.I)),
    ("framework", "Express", re.compile(r"X-Powered-By:\s*Express", re.I)),
]


def detect_technologies(
    headers: dict[str, str],
    body_sample: str = "",
) -> list[dict[str, str]]:
    technologies: list[dict[str, str]] = []
    seen: set[str] = set()

    server = headers.get("server", "")
    if server:
        technologies.append({"category": "web_server", "name": server.split("/")[0].strip(), "source": "header"})
        seen.add(server.lower())

    powered_by = headers.get("x-powered-by", "")
    if powered_by and powered_by.lower() not in seen:
        technologies.append({"category": "platform", "name": powered_by, "source": "header"})
        seen.add(powered_by.lower())

    generator = headers.get("x-generator", "")
    if generator:
        technologies.append({"category": "cms", "name": generator, "source": "header"})

    combined = body_sample[:8000]
    for category, name, pattern in CMS_PATTERNS:
        if pattern.search(combined) or pattern.search(str(headers)):
            key = f"{category}:{name}"
            if key not in seen:
                technologies.append({"category": category, "name": name, "source": "passive"})
                seen.add(key)

    return technologies
