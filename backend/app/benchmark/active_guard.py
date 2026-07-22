"""Allowlist, budget, and safety guards for isolated active benchmark scans."""

from __future__ import annotations

import ipaddress
import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from urllib.parse import urlparse

import yaml

from app.benchmark.manifests import ALLOWED_TARGET_HOSTS, repo_benchmarks_root
from app.core.config import get_settings

ACTIVE_SCAN_ALLOWED_ENV = "BENCHMARK_ACTIVE_SCAN_ALLOWED"
KILL_SWITCH_ENV = "BENCHMARK_ACTIVE_KILL_SWITCH"

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
ACTIVE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH"})

METADATA_HOSTS = frozenset(
    {
        "169.254.169.254",
        "metadata.google.internal",
        "metadata.azure.com",
        "metadata.aws.internal",
        "metadata",
    }
)

DESTRUCTIVE_PATH_PATTERNS = (
    re.compile(r"/(?:delete|remove|destroy)(?:/|$)", re.I),
    re.compile(r"/(?:payment|checkout|billing|charge|pay(?:ment)?s?)(?:/|$)", re.I),
    re.compile(r"/(?:logout|signout|sign-out|log-out)(?:/|$)", re.I),
    re.compile(r"/(?:account|profile|user|users)/(?:delete|password|settings|update)(?:/|$)", re.I),
    re.compile(r"/rest/user/(?:\d+|login|logout)(?:/|$)", re.I),
    re.compile(r"/identity/api/v2/user/(?:\d+|password|logout)(?:/|$)", re.I),
)

REDIRECT_RISK_PATTERNS = (
    re.compile(r"^https?://", re.I),
    re.compile(r"^//"),
    re.compile(r"^javascript:", re.I),
    re.compile(r"^data:", re.I),
    re.compile(r"^file:", re.I),
    re.compile(r"@"),
)


@dataclass(frozen=True)
class AllowlistEntry:
    host: str
    port: int | None = None
    path_prefix: str = "/"
    methods: frozenset[str] = SAFE_METHODS


class ActiveBenchmarkGuardError(ValueError):
    """Raised when an active benchmark request violates lab safety rules."""


@dataclass
class ActiveBenchmarkGuard:
    """Tracks request budget and validates outbound active-scan traffic."""

    allowlist: tuple[AllowlistEntry, ...]
    request_count: int = field(default=0, init=False)

    def check_kill_switch(self) -> None:
        if os.environ.get(KILL_SWITCH_ENV, "").lower() in {"1", "true", "yes"}:
            raise ActiveBenchmarkGuardError("Active benchmark kill switch engaged")

    def validate_target_url(self, url: str) -> None:
        self.check_kill_switch()
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            raise ActiveBenchmarkGuardError(f"Scheme {parsed.scheme!r} is not allowed")
        if parsed.username or parsed.password:
            raise ActiveBenchmarkGuardError("Embedded credentials in target URLs are forbidden")
        hostname = parsed.hostname
        if not hostname:
            raise ActiveBenchmarkGuardError("Target URL must include a hostname")
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        self._assert_no_external_ip(hostname)
        self._assert_no_metadata(hostname)
        self._assert_no_redirect_risk(url)
        self._assert_host_allowed(hostname, port)
        path = parsed.path or "/"
        if self._is_destructive(path, "GET"):
            raise ActiveBenchmarkGuardError(f"Destructive target path blocked: {path}")

    def validate_request(self, *, url: str, method: str) -> None:
        self.check_kill_switch()
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            raise ActiveBenchmarkGuardError("Request URL must include a hostname")
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        path = parsed.path or "/"
        method_upper = method.upper()
        self._assert_no_external_ip(hostname)
        self._assert_no_metadata(hostname)
        self._assert_no_redirect_risk(url)
        if self._is_destructive(path, method_upper):
            raise ActiveBenchmarkGuardError(f"Destructive endpoint blocked: {method_upper} {path}")
        if not self._path_method_allowed(hostname, port, path, method_upper):
            raise ActiveBenchmarkGuardError(f"Request {method_upper} {path} is not allowlisted")
        settings = get_settings()
        if self.request_count >= settings.benchmark_active_request_budget:
            raise ActiveBenchmarkGuardError(
                f"Active benchmark request budget exhausted ({settings.benchmark_active_request_budget})"
            )
        self.request_count += 1

    def remaining_budget(self) -> int:
        settings = get_settings()
        return max(0, settings.benchmark_active_request_budget - self.request_count)

    def metrics(self) -> dict[str, int]:
        settings = get_settings()
        return {
            "request_count": self.request_count,
            "request_budget": settings.benchmark_active_request_budget,
            "remaining_budget": self.remaining_budget(),
        }

    def _assert_host_allowed(self, hostname: str, port: int) -> None:
        if not any(
            entry.host == hostname and (entry.port is None or entry.port == port)
            for entry in self.allowlist
        ):
            raise ActiveBenchmarkGuardError(
                f"Host {hostname!r}:{port} is not in the active benchmark allowlist"
            )

    def _path_method_allowed(self, hostname: str, port: int, path: str, method: str) -> bool:
        for entry in self.allowlist:
            if entry.host != hostname:
                continue
            if entry.port is not None and entry.port != port:
                continue
            if not path.startswith(entry.path_prefix):
                continue
            if method not in entry.methods:
                continue
            return True
        return False

    @staticmethod
    def _assert_no_external_ip(hostname: str) -> None:
        try:
            address = ipaddress.ip_address(hostname)
        except ValueError:
            return
        if not (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_reserved
        ):
            raise ActiveBenchmarkGuardError(f"External IP target blocked: {hostname}")

    @staticmethod
    def _assert_no_metadata(hostname: str) -> None:
        lowered = hostname.lower()
        if lowered in METADATA_HOSTS or lowered.endswith(".metadata.google.internal"):
            raise ActiveBenchmarkGuardError(f"Metadata endpoint blocked: {hostname}")

    @staticmethod
    def _assert_no_redirect_risk(url: str) -> None:
        parsed = urlparse(url)
        for part in parsed.query.lower().split("&") if parsed.query else []:
            _, _, candidate = part.partition("=")
            candidate = candidate or part
            for pattern in REDIRECT_RISK_PATTERNS:
                if pattern.search(candidate):
                    raise ActiveBenchmarkGuardError("Redirect or rebinding payload blocked in query")

    @staticmethod
    def _is_destructive(path: str, method: str) -> bool:
        if method.upper() in {"DELETE", "TRACE"}:
            return True
        return any(pattern.search(path) for pattern in DESTRUCTIVE_PATH_PATTERNS)


def _load_allowlist_file(relative_path: str) -> tuple[AllowlistEntry, ...]:
    root = repo_benchmarks_root()
    path = (root / relative_path).resolve()
    if root.resolve() not in path.parents:
        raise ValueError("Active allowlist path traversal blocked")
    if not path.is_file():
        raise FileNotFoundError(path)
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    entries: list[AllowlistEntry] = []
    for item in payload.get("entries") or []:
        host = str(item["host"])
        if host not in ALLOWED_TARGET_HOSTS:
            raise ValueError(f"Allowlist host {host!r} is not globally allowlisted")
        methods = frozenset(str(value).upper() for value in (item.get("methods") or SAFE_METHODS))
        entries.append(
            AllowlistEntry(
                host=host,
                port=item.get("port"),
                path_prefix=str(item.get("path_prefix") or "/"),
                methods=methods,
            )
        )
    if not entries:
        raise ValueError(f"Active allowlist {relative_path!r} has no entries")
    return tuple(entries)


@lru_cache(maxsize=4)
def load_web_active_allowlist() -> tuple[AllowlistEntry, ...]:
    return _load_allowlist_file("active-allowlists/web-juice-proxy.yaml")


@lru_cache(maxsize=4)
def load_api_active_allowlist() -> tuple[AllowlistEntry, ...]:
    return _load_allowlist_file("active-allowlists/api-crapi-proxy.yaml")


def guard_for_profile(profile: str) -> ActiveBenchmarkGuard:
    if profile == "benchmark-active-web":
        return ActiveBenchmarkGuard(load_web_active_allowlist())
    if profile == "benchmark-active-api":
        return ActiveBenchmarkGuard(load_api_active_allowlist())
    raise ValueError(f"No active benchmark allowlist for profile {profile!r}")


def active_scan_execution_allowed() -> bool:
    settings = get_settings()
    if not settings.benchmark_active_realistic_enabled:
        return False
    if os.environ.get("BENCHMARK_LAB_ISOLATED") != "true":
        return False
    if os.environ.get("BENCHMARK_LAB_CONTAINER_MODE") != "true":
        return False
    return os.environ.get(ACTIVE_SCAN_ALLOWED_ENV, "").lower() in {"1", "true", "yes"}


def zap_exclude_regexes() -> list[str]:
    return [
        ".*(?:delete|remove|destroy|payment|checkout|billing|logout|signout).*",
        ".*/rest/user/\\d+.*",
        ".*/identity/api/v2/user/\\d+.*",
    ]
