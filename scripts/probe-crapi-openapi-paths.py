#!/usr/bin/env python3
"""Probe crAPI realistic proxy for runtime OpenAPI/Swagger exposure (Faz 12.1 evidence)."""

from __future__ import annotations

import json
import os
import ssl
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE = os.environ.get("CRAPI_PROBE_BASE_URL", "https://benchmark-crapi-proxy")
CA_PATH = os.environ.get("BENCHMARK_CA_CERT_PATH", str(ROOT / "benchmarks" / "docker" / "realistic" / "certs" / "ca.crt"))

OPENAPI_PATHS = (
    "/openapi.json",
    "/swagger.json",
    "/swagger/v1/swagger.json",
    "/api-docs",
    "/docs",
    "/v3/api-docs",
    "/v3/api-docs.yaml",
    "/swagger-ui.html",
    "/swagger-ui/index.html",
    "/api/openapi.json",
    "/identity/api/openapi.json",
    "/identity/api/v3/api-docs",
    "/identity/api/swagger-ui/index.html",
    "/community/api/openapi.json",
    "/workshop/api/openapi.json",
    "/workshop/api/schema/",
    "/workshop/api/swagger/",
)


def _ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ca = Path(CA_PATH)
    if ca.is_file():
        ctx.load_verify_locations(cafile=str(ca))
    else:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _openapi_signature(body: str, content_type: str) -> bool:
    sample = body[:4000].lower()
    if "openapi" in sample or "swagger" in sample:
        return True
    if "application/json" in content_type.lower() or sample.lstrip().startswith("{"):
        try:
            payload = json.loads(body[:200_000])
        except json.JSONDecodeError:
            return False
        if isinstance(payload, dict):
            if payload.get("openapi") or payload.get("swagger"):
                return True
            paths = payload.get("paths")
            return isinstance(paths, dict) and len(paths) > 0
    return "text/html" in content_type.lower() and ("swagger-ui" in sample or "swagger ui" in sample)


def probe_path(base_url: str, path: str) -> dict:
    url = f"{base_url.rstrip('/')}{path}"
    record = {"path": path, "url": url, "status_code": None, "content_type": "", "openapi_signature": False, "error": None}
    try:
        request = Request(url, headers={"Accept": "application/json, text/html;q=0.9"})
        with urlopen(request, timeout=15, context=_ssl_context()) as response:
            body = response.read(200_000).decode("utf-8", errors="replace")
            record["status_code"] = response.status
            record["content_type"] = response.headers.get("Content-Type", "")
            record["openapi_signature"] = _openapi_signature(body, record["content_type"])
            record["body_sample"] = body[:200]
    except HTTPError as exc:
        record["status_code"] = exc.code
        record["error"] = str(exc.reason)
    except URLError as exc:
        record["error"] = str(exc.reason)
    except Exception as exc:
        record["error"] = str(exc)
    return record


from urllib.parse import urlparse


def _origin(base_url: str) -> str:
    parsed = urlparse(base_url)
    if not parsed.scheme or not parsed.netloc:
        return base_url.rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}"


def main() -> int:
    base = _origin(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASE)
    results = [probe_path(base, path) for path in OPENAPI_PATHS]
    exposed = [item for item in results if item.get("openapi_signature")]
    payload = {
        "base_url": base,
        "paths_probed": len(results),
        "openapi_exposed_count": len(exposed),
        "runtime_openapi_exposed": len(exposed) > 0,
        "exposed_paths": [item["path"] for item in exposed],
        "results": results,
    }
    print(json.dumps(payload, indent=2))
    return 0 if len(exposed) > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
